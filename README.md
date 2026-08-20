
# 🏆 Boys Trip Olympics — Shared Mobile App

This version is designed to be the **public-facing competition app** for six friends.

## What your buddies can do

- See the live leaderboard
- See the podium
- See the points race
- See points by event
- See all events and their status
- See competition history

They **cannot edit scores** through the app.

## What the organizer can do

From the Organizer tab, protected by a password:

- Add unlimited events
- Give events an emoji/icon
- Add an event description
- Rename players
- Enter results
- Publish points
- Delete/correct results

## Data persistence

The production version uses Supabase/Postgres. This means the six of you share one database rather than relying on files on the Streamlit server.

The app expects these Streamlit secrets:

- SUPABASE_URL
- SUPABASE_SERVICE_KEY
- ADMIN_PASSWORD

Never commit the service-role key to GitHub.

## Deploy

1. Create a GitHub repository.
2. Upload:
   - app.py
   - requirements.txt
   - supabase_schema.sql
3. Create a Supabase project and run `supabase_schema.sql`.
4. Deploy the GitHub repo to Streamlit Community Cloud.
5. Add the three secrets under the app's Secrets settings.
6. Give your friends the resulting `.streamlit.app` URL.
7. On iPhone, open the URL in Safari → Share → Add to Home Screen.

## Suggested app URL

Choose something memorable such as:

boys-trip-olympics.streamlit.app

(Availability depends on Streamlit's current subdomain rules.)

## Local test

```bash
pip install -r requirements.txt
streamlit run app.py
```

Without Supabase secrets, the app falls back to local CSV files for testing.

Default local organizer password: `change-me`

For any shared deployment, set ADMIN_PASSWORD in Streamlit Secrets.
