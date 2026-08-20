import streamlit as st
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
import os, hashlib

# -----------------------------
# Configuration
# -----------------------------
st.set_page_config(
    page_title="Boys Trip Olympics",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="collapsed",
)

USE_SUPABASE = False
try:
    from supabase import create_client
    if "SUPABASE_URL" in st.secrets and "SUPABASE_KEY" in st.secrets:
        sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
        USE_SUPABASE = True
except Exception:
    sb = None

LOCAL = Path("local_data")
LOCAL.mkdir(exist_ok=True)
PLAYERS_FILE = LOCAL / "players.csv"
EVENTS_FILE = LOCAL / "events.csv"
RESULTS_FILE = LOCAL / "results.csv"

# Fixed Roster
DEFAULT_PLAYERS = ["Jake", "Cam", "Ryan", "Patty", "Eli", "Nick"]
DEFAULT_EVENTS = [
    {"name": "Archery", "icon": "🏹", "description": "Bullseyes and pressure."},
    {"name": "Golf", "icon": "⛳", "description": "18 holes. One leaderboard."},
    {"name": "Chess", "icon": "♟️", "description": "Checkmate your competition."},
]

BASE_POINTS = {1: 6, 2: 5, 3: 4, 4: 3, 5: 2, 6: 1}

# -----------------------------
# Scoring Helper Logic
# -----------------------------
def calculate_points_from_places(places):
    """
    Calculates points for a list of 6 player finish positions,
    automatically splitting points in the event of ties.
    Example: places = [1, 1, 3, 4, 5, 6] -> [5.5, 5.5, 4.0, 3.0, 2.0, 1.0]
    """
    sorted_places = sorted(places)
    
    # Map each finish rank to its base point value
    rank_points = [BASE_POINTS[r] for r in range(1, len(places) + 1)]
    
    # Group ranks and calculate split averages for ties
    place_to_points = {}
    i = 0
    while i < len(sorted_places):
        val = sorted_places[i]
        count = sorted_places.count(val)
        sum_pts = sum(rank_points[i : i + count])
        avg_pts = sum_pts / count
        place_to_points[val] = avg_pts
        i += count

    return [place_to_points[p] for p in places]

# -----------------------------
# Styling
# -----------------------------
st.markdown("""
<style>
:root { --card: rgba(128,128,128,.10); }
.block-container { max-width: 1100px; padding-top: 1.2rem; padding-bottom: 4rem; }
.hero {
    padding: 1.5rem;
    border-radius: 28px;
    background: linear-gradient(135deg,#111827 0%,#312e81 55%,#4c1d95 100%);
    color: white;
    box-shadow: 0 15px 40px rgba(0,0,0,.18);
}
.hero h1 { font-size: clamp(2rem, 7vw, 4rem); margin: 0; line-height: .95; }
.hero p { opacity: .8; margin: .7rem 0 0; }
.card {
    padding: 1rem;
    border-radius: 20px;
    background: var(--card);
    border: 1px solid rgba(128,128,128,.22);
    margin-bottom: .75rem;
}
.rank { font-size: 1.45rem; font-weight: 800; }
.points { font-size: 1.15rem; font-weight: 750; }
.muted { opacity: .65; }
.podium {
    text-align: center;
    padding: 1rem .5rem;
    border-radius: 24px;
    background: var(--card);
    border: 1px solid rgba(128,128,128,.2);
}
.big-medal { font-size: 3rem; }
.big-name { font-size: 1.4rem; font-weight: 850; }
.big-points { font-size: 1.1rem; font-weight: 700; }
.event-card {
    min-height: 150px;
    padding: 1.1rem;
    border-radius: 22px;
    background: var(--card);
    border: 1px solid rgba(128,128,128,.2);
}
.event-icon { font-size: 2.4rem; }
.event-name { font-size: 1.2rem; font-weight: 800; }
.status { font-size: .85rem; opacity: .7; }
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Local fallback storage
# -----------------------------
def ensure_local():
    if not PLAYERS_FILE.exists():
        pd.DataFrame({"id": range(1, 7), "name": DEFAULT_PLAYERS}).to_csv(PLAYERS_FILE, index=False)
    else:
        # Guarantee local file updates single-letter initials to full names
        df = pd.read_csv(PLAYERS_FILE)
        if df.empty or df["name"].str.len().max() == 1:
            pd.DataFrame({"id": range(1, 7), "name": DEFAULT_PLAYERS}).to_csv(PLAYERS_FILE, index=False)

    if not EVENTS_FILE.exists():
        pd.DataFrame({
            "id": range(1, 4),
            "name": [x["name"] for x in DEFAULT_EVENTS],
            "icon": [x["icon"] for x in DEFAULT_EVENTS],
            "description": [x["description"] for x in DEFAULT_EVENTS]
        }).to_csv(EVENTS_FILE, index=False)
        
    if not RESULTS_FILE.exists():
        pd.DataFrame(columns=["id", "event_id", "player_id", "score", "points", "created_at"]).to_csv(RESULTS_FILE, index=False)

def local_players():
    ensure_local()
    return pd.read_csv(PLAYERS_FILE)

def local_events():
    ensure_local()
    return pd.read_csv(EVENTS_FILE)

def local_results():
    ensure_local()
    return pd.read_csv(RESULTS_FILE)

# -----------------------------
# Database adapter
# -----------------------------
def get_players():
    df = pd.DataFrame()
    if USE_SUPABASE:
        try:
            data = sb.table("players").select("*").order("id").execute().data
            if data:
                df = pd.DataFrame(data)
        except Exception as e:
            st.error(f"Supabase error fetching players: {e}")

    # Fallback to local file if database query fails or is empty
    if df.empty:
        df = local_players()

    # Guarantee required columns are present to prevent Pandas KeyErrors
    for col in ["id", "name"]:
        if col not in df.columns:
            df[col] = pd.Series(dtype="object")

    return df

def get_events():
    df = pd.DataFrame()
    if USE_SUPABASE:
        try:
            data = sb.table("events").select("*").order("id").execute().data
            if data:
                df = pd.DataFrame(data)
        except Exception as e:
            st.error(f"Supabase error fetching events: {e}")

    if df.empty:
        df = local_events()

    for col in ["id", "name", "icon", "description"]:
        if col not in df.columns:
            df[col] = pd.Series(dtype="object")

    return df

def get_results():
    df = pd.DataFrame()
    if USE_SUPABASE:
        try:
            data = sb.table("results").select("*").order("created_at").execute().data
            if data:
                df = pd.DataFrame(data)
        except Exception as e:
            st.error(f"Supabase error fetching results: {e}")

    if df.empty:
        df = local_results()

    for col in ["id", "event_id", "player_id", "score", "points", "created_at"]:
        if col not in df.columns:
            df[col] = pd.Series(dtype="object")

    return df

def add_event(name, icon, description):
    if USE_SUPABASE:
        sb.table("events").insert({"name": name, "icon": icon, "description": description}).execute()
    else:
        df = local_events()
        new_id = int(df["id"].max()) + 1 if len(df) and not df["id"].isna().all() else 1
        df.loc[len(df)] = [new_id, name, icon, description]
        df.to_csv(EVENTS_FILE, index=False)

def publish_event_results(event_id, player_places):
    """
    Publishes all six player places and calculated points simultaneously.
    """
    created = datetime.now(timezone.utc).isoformat()
    calculated_points = calculate_points_from_places([p["place"] for p in player_places])

    if USE_SUPABASE:
        records = [
            {
                "event_id": int(event_id),
                "player_id": int(p["player_id"]),
                "score": float(p["place"]), # Finish place stored in score column
                "points": float(pts),
                "created_at": created
            }
            for p, pts in zip(player_places, calculated_points)
        ]
        sb.table("results").insert(records).execute()
    else:
        df = local_results()
        current_id = int(df["id"].max()) if len(df) and not df["id"].isna().all() else 0
        for p, pts in zip(player_places, calculated_points):
            current_id += 1
            df.loc[len(df)] = [current_id, int(event_id), int(p["player_id"]), float(p["place"]), float(pts), created]
        df.to_csv(RESULTS_FILE, index=False)

def delete_event_results(event_id):
    if USE_SUPABASE:
        sb.table("results").delete().eq("event_id", int(event_id)).execute()
    else:
        df = local_results()
        df = df[df.event_id != int(event_id)]
        df.to_csv(RESULTS_FILE, index=False)

def password_ok(pwd):
    try:
        expected = st.secrets["ADMIN_PASSWORD"]
    except Exception:
        expected = os.environ.get("OLYMPICS_ADMIN_PASSWORD", "jakewins")
    return hashlib.sha256(pwd.encode()).hexdigest() == hashlib.sha256(expected.encode()).hexdigest()

def admin_login():
    st.subheader("🔐 Organizer Mode")
    st.caption("Only the organizer can change competition data.")
    pwd = st.text_input("Organizer password", type="password")
    if st.button("Unlock organizer controls", type="primary", use_container_width=True):
        if password_ok(pwd):
            st.session_state["admin"] = True
            st.rerun()
        else:
            st.error("Wrong password.")

# -----------------------------
# Data prep
# -----------------------------
players = get_players()
events = get_events()
results = get_results()

if not results.empty and "player_id" in results.columns and not results["player_id"].isna().all():
    merged = results.merge(players[["id", "name"]], left_on="player_id", right_on="id", suffixes=("", "_player"))
    merged = merged.merge(events[["id", "name", "icon"]], left_on="event_id", right_on="id", suffixes=("", "_event"))
    merged = merged.rename(columns={"name": "player", "name_event": "event", "icon": "event_icon"})
else:
    merged = pd.DataFrame(columns=["id", "event_id", "player_id", "score", "points", "created_at", "player", "event", "event_icon"])

# -----------------------------
# Header
# -----------------------------
st.markdown("""
<div class="hero">
  <h1>🏆 BOYS TRIP<br>OLYMPICS</h1>
  <p>Six competitors. Every event counts. One champion.</p>
</div>
""", unsafe_allow_html=True)

if USE_SUPABASE:
    st.caption("🟢 Live shared leaderboard")
else:
    st.warning("Local mode: results are stored on this device. Connect Supabase before sharing the app.")

tabs = st.tabs(["🏆 Standings", "🎯 Events", "📜 History", "🔐 Organizer"])

# -----------------------------
# Standings
# -----------------------------
with tabs[0]:
    totals = players[["id", "name"]].copy()
    if not merged.empty:
        pts = merged.groupby("player_id")["points"].sum().rename("points")
        totals = totals.merge(pts, left_on="id", right_index=True, how="left")
    else:
        totals["points"] = 0
    totals["points"] = totals["points"].fillna(0)
    totals = totals.sort_values(["points", "name"], ascending=[False, True]).reset_index(drop=True)

    st.subheader("🔥 The Race for Gold")
    if len(totals) >= 3:
        podium = st.columns(3)
        order = [1, 0, 2] if len(totals) >= 3 else list(range(len(totals)))
        medals = ["🥈", "🥇", "🥉"]
        for col, idx, medal in zip(podium, order, medals):
            r = totals.iloc[idx]
            with col:
                st.markdown(f"""
                <div class="podium">
                  <div class="big-medal">{medal}</div>
                  <div class="big-name">{r['name']}</div>
                  <div class="big-points">{r['points']:g} pts</div>
                </div>
                """, unsafe_allow_html=True)

    st.divider()
    leader = totals.iloc[0] if len(totals) else None
    if leader is not None:
        st.metric("🥇 Current Leader", leader["name"], f"{leader['points']:g} points")

    st.subheader("📊 Full Standings")
    max_points = max(float(totals["points"].max()), 1)
    for i, r in totals.iterrows():
        place = i + 1
        medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"#{place}"
        pct = min(float(r["points"]) / max_points, 1.0)
        st.markdown(
            f'<div class="card"><span class="rank">{medal} {r["name"]}</span>'
            f'<br><span class="points">{r["points"]:g} points</span></div>',
            unsafe_allow_html=True
        )
        st.progress(pct)

    if not merged.empty:
        st.subheader("⚔️ Points by Event")
        pivot = merged.pivot_table(index="player", columns="event", values="points", aggfunc="sum", fill_value=0)
        pivot["TOTAL"] = pivot.sum(axis=1)
        pivot = pivot.sort_values("TOTAL", ascending=False)
        st.dataframe(pivot, use_container_width=True)

# -----------------------------
# Events
# -----------------------------
with tabs[1]:
    st.subheader("🎯 The Events")
    cols = st.columns(2)
    for i, e in events.iterrows():
        er = merged[merged["event_id"] == e["id"]] if not merged.empty else pd.DataFrame()
        done = not er.empty
        winner = ""
        if done:
            latest = er.sort_values("created_at").drop_duplicates("player_id", keep="last")
            w = latest.sort_values("points", ascending=False).iloc[0]
            winner = f"🏅 {w['player']} leads with {w['points']:g} pts"
        with cols[i % 2]:
            st.markdown(f"""
            <div class="event-card">
              <div class="event-icon">{e['icon']}</div>
              <div class="event-name">{e['name']}</div>
              <div class="status">{'✅ Results entered' if done else '⏳ Awaiting results'}</div>
              <p class="muted">{e['description']}</p>
              <b>{winner}</b>
            </div>
            """, unsafe_allow_html=True)

# -----------------------------
# History
# -----------------------------
with tabs[2]:
    st.subheader("📜 Competition History")
    if merged.empty:
        st.info("No scores have been entered yet.")
    else:
        history = merged.sort_values("created_at", ascending=False)[
            ["event_icon", "event", "player", "score", "points", "created_at"]
        ].copy()
        history["score"] = history["score"].astype(int).astype(str) + " Place"
        history.columns = ["", "Event", "Player", "Finish", "Points", "Time"]
        st.dataframe(history, use_container_width=True, hide_index=True)

# -----------------------------
# Organizer
# -----------------------------
with tabs[3]:
    if not st.session_state.get("admin", False):
        admin_login()
    else:
        c1, c2 = st.columns([4, 1])
        with c1:
            st.success("Organizer controls unlocked.")
        with c2:
            if st.button("Lock"):
                st.session_state["admin"] = False
                st.rerun()

        st.subheader("➕ Add an Event")
        c1, c2 = st.columns([1, 3])
        with c1:
            icon = st.text_input("Icon", "🎯")
        with c2:
            name = st.text_input("Event name", placeholder="e.g. Beer Pong")
        description = st.text_input("Description", placeholder="Short description shown to everyone")
        if st.button("Add Event", type="primary", use_container_width=True):
            if name.strip():
                add_event(name.strip(), icon.strip() or "🎯", description.strip())
                st.success("Event added!")
                st.rerun()

        st.divider()
        st.subheader("📝 Enter Event Results")
        event_options = {f"{e['icon']} {e['name']}": e["id"] for _, e in events.iterrows()}

        if event_options:
            selected_event_label = st.selectbox("Select Event", list(event_options))
            selected_event_id = event_options[selected_event_label]

            # Prevent double publishing check
            already_published = not results.empty and (results["event_id"] == selected_event_id).any()

            if already_published:
                st.warning("⚠️ Results have already been published for this event. To re-enter or change results, delete the event results below.")
            else:
                st.write("Assign finishing place for each player (1st to 6th):")
                player_entries = []

                # Render selectboxes for each player
                for _, p in players.iterrows():
                    col1, col2 = st.columns([2, 2])
                    with col1:
                        st.markdown(f"**{p['name']}**")
                    with col2:
                        place = st.number_input(
                            f"Place for {p['name']}",
                            min_value=1,
                            max_value=len(players),
                            value=1,
                            key=f"place_{p['id']}",
                            label_visibility="collapsed"
                        )
                    player_entries.append({"player_id": p["id"], "name": p["name"], "place": place})

                # Calculate live preview points
                places_list = [p["place"] for p in player_entries]
                computed_pts = calculate_points_from_places(places_list)

                # Live Points Preview Block
                st.markdown("#### 👁️ Live Points Preview")
                preview_df = pd.DataFrame({
                    "Player": [p["name"] for p in player_entries],
                    "Place": [f"#{p['place']}" for p in player_entries],
                    "Points Awarded": computed_pts
                })
                st.dataframe(preview_df, use_container_width=True, hide_index=True)

                if st.button("💾 Publish Event Results", type="primary", use_container_width=True):
                    publish_event_results(selected_event_id, player_entries)
                    st.success("All 6 results published successfully to the leaderboard!")
                    st.rerun()

        st.divider()
        st.subheader("🗑️ Correct / Delete Event Results")
        if not merged.empty:
            published_events = merged[["event_id", "event_icon", "event"]].drop_duplicates()
            event_delete_options = {f"{r['event_icon']} {r['event']}": r["event_id"] for _, r in published_events.iterrows()}
            
            selected_del_event = st.selectbox("Select event to clear results", list(event_delete_options))
            if st.button("Delete Event Results", type="secondary", use_container_width=True):
                delete_event_results(event_delete_options[selected_del_event])
                st.success("Results cleared for event!")
                st.rerun()
        else:
            st.caption("No results published to clear.")

st.sidebar.caption("🏆 Boys Trip Olympics")
