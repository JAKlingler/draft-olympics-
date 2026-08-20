
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

DEFAULT_PLAYERS = ["J", "C", "R", "P", "E", "N"]
DEFAULT_EVENTS = [
    {"name": "Archery", "icon": "🏹", "description": "Bullseyes and pressure."},
    {"name": "Golf", "icon": "⛳", "description": "18 holes. One leaderboard."},
    {"name": "Chess", "icon": "♟️", "description": "Checkmate your competition."},
]

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
        pd.DataFrame({"id": range(1,7), "name": DEFAULT_PLAYERS}).to_csv(PLAYERS_FILE, index=False)
    if not EVENTS_FILE.exists():
        pd.DataFrame({
            "id": range(1,4),
            "name": [x["name"] for x in DEFAULT_EVENTS],
            "icon": [x["icon"] for x in DEFAULT_EVENTS],
            "description": [x["description"] for x in DEFAULT_EVENTS]
        }).to_csv(EVENTS_FILE, index=False)
    if not RESULTS_FILE.exists():
        pd.DataFrame(columns=["id","event_id","player_id","score","points","created_at"]).to_csv(RESULTS_FILE, index=False)

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
    if USE_SUPABASE:
        data = sb.table("players").select("*").eq("active", True).order("id").execute().data
        return pd.DataFrame(data)
    return local_players()

def get_events():
    if USE_SUPABASE:
        data = sb.table("events").select("*").order("id").execute().data
        return pd.DataFrame(data)
    return local_events()

def get_results():
    if USE_SUPABASE:
        data = sb.table("results").select("*").order("created_at").execute().data
        return pd.DataFrame(data)
    return local_results()

def add_event(name, icon, description):
    if USE_SUPABASE:
        sb.table("events").insert({"name":name, "icon":icon, "description":description}).execute()
    else:
        df = local_events()
        new_id = int(df["id"].max()) + 1 if len(df) else 1
        df.loc[len(df)] = [new_id, name, icon, description]
        df.to_csv(EVENTS_FILE, index=False)

def add_result(event_id, player_id, score, points):
    created = datetime.now(timezone.utc).isoformat()
    if USE_SUPABASE:
        sb.table("results").insert({
            "event_id": int(event_id),
            "player_id": int(player_id),
            "score": float(score),
            "points": float(points),
            "created_at": created
        }).execute()
    else:
        df = local_results()
        new_id = int(df["id"].max()) + 1 if len(df) else 1
        df.loc[len(df)] = [new_id, int(event_id), int(player_id), float(score), float(points), created]
        df.to_csv(RESULTS_FILE, index=False)

def delete_result(result_id):
    if USE_SUPABASE:
        sb.table("results").delete().eq("id", int(result_id)).execute()
    else:
        df = local_results()
        df = df[df.id != result_id]
        df.to_csv(RESULTS_FILE, index=False)

def rename_players(names):
    if USE_SUPABASE:
        for p, name in zip(get_players().to_dict("records"), names):
            sb.table("players").update({"name": name}).eq("id", int(p["id"])).execute()
    else:
        df = local_players()
        df["name"] = names
        df.to_csv(PLAYERS_FILE, index=False)

def password_ok(pwd):
    try:
        expected = st.secrets["ADMIN_PASSWORD"]
    except Exception:
        expected = os.environ.get("OLYMPICS_ADMIN_PASSWORD", "change-me")
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

if not results.empty:
    merged = results.merge(players[["id","name"]], left_on="player_id", right_on="id", suffixes=("","_player"))
    merged = merged.merge(events[["id","name","icon"]], left_on="event_id", right_on="id", suffixes=("","_event"))
    merged = merged.rename(columns={"name":"player","name_event":"event","icon":"event_icon"})
else:
    merged = pd.DataFrame(columns=["id","event_id","player_id","score","points","created_at","player","event","event_icon"])

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
    totals = players[["id","name"]].copy()
    if not merged.empty:
        pts = merged.groupby("player_id")["points"].sum().rename("points")
        totals = totals.merge(pts, left_on="id", right_index=True, how="left")
    else:
        totals["points"] = 0
    totals["points"] = totals["points"].fillna(0)
    totals = totals.sort_values(["points","name"], ascending=[False,True]).reset_index(drop=True)

    st.subheader("🔥 The Race for Gold")
    if len(totals) >= 3:
        podium = st.columns(3)
        order = [1,0,2] if len(totals) >= 3 else list(range(len(totals)))
        medals = ["🥈","🥇","🥉"]
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
        medal = ["🥇","🥈","🥉"][i] if i < 3 else f"#{place}"
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
            ["event_icon","event","player","score","points","created_at"]
        ].copy()
        history.columns = ["","Event","Player","Result","Points","Time"]
        st.dataframe(history, use_container_width=True, hide_index=True)

# -----------------------------
# Organizer
# -----------------------------
with tabs[3]:
    if not st.session_state.get("admin", False):
        admin_login()
    else:
        c1, c2 = st.columns([4,1])
        with c1:
            st.success("Organizer controls unlocked.")
        with c2:
            if st.button("Lock"):
                st.session_state["admin"] = False
                st.rerun()

        st.subheader("➕ Add an Event")
        c1,c2 = st.columns([1,3])
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
        st.subheader("📝 Enter Results")
        event_options = {f"{e['icon']} {e['name']}": e["id"] for _, e in events.iterrows()}
        player_options = {p["name"]: p["id"] for _, p in players.iterrows()}
        if event_options and player_options:
            selected_event = st.selectbox("Event", list(event_options))
            selected_player = st.selectbox("Player", list(player_options))
            score = st.number_input("Raw result / score", value=0.0, step=1.0)
            points = st.number_input("Olympics points", min_value=0.0, value=1.0, step=0.5)
            if st.button("💾 Publish Result", type="primary", use_container_width=True):
                add_result(event_options[selected_event], player_options[selected_player], score, points)
                st.success("Result published to the live leaderboard!")
                st.rerun()

        st.divider()
        st.subheader("👥 Player Names")
        names = [st.text_input(f"Player {i+1}", p["name"], key=f"name_{p['id']}") for i, p in players.iterrows()]
        if st.button("Save Player Names", use_container_width=True):
            rename_players([x.strip() for x in names])
            st.success("Player names updated.")
            st.rerun()

        st.divider()
        st.subheader("🗑️ Correct a Result")
        if not merged.empty:
            choices = {
                f"{r['event']} — {r['player']} — {r['points']:g} pts": r["id"]
                for _, r in merged.sort_values("created_at", ascending=False).iterrows()
            }
            selected = st.selectbox("Result to delete", list(choices))
            if st.button("Delete Selected Result"):
                delete_result(choices[selected])
                st.success("Result deleted.")
                st.rerun()
        else:
            st.caption("Nothing to delete yet.")

st.sidebar.caption("🏆 Boys Trip Olympics")
