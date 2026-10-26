# SoundCheck

Your friends. Their music. One very competitive quiz.

SoundCheck turns a group's Spotify listening history into a party quiz. Everyone joins a private room, connects Spotify, and answers questions only friends could get right: whose #1 song this month is "Espresso", who's in a brand new Kendrick phase, whose top genre is indie folk. The game ends on four game cards: Most Loyal Listener, Biggest Genre Switch, Top 0.5% Listener and Biggest Song Looper.

## How a game runs

1. The host starts a room and texts the link. The link keeps working for 30 days, so a friend group reuses it every week and builds season standings.
2. Everyone brings their taste one of four ways: quick picks (search and pick 3 to 5 artists and songs), an upload of their Spotify data export (read on their own phone, only the summary is sent), Spotify login (limited to 5 accounts while the app is in Spotify Development Mode), or a sample listener.
3. The host picks a mode (Classic, Wrapped, Road trip, Decades, Genres), a length (5, 8 or 12) and optionally team mode or AI wording.
4. Questions come in two shapes: pick a friend ("Who's the biggest Drake fan in the room?") or pick an answer ("What's the last song Kaylie played?"). Right answers score 100 plus up to 50 for speed, and whoever a question is about gets 50 for every friend who got them right.
5. After each reveal everyone can react (CALLED IT, NO WAY, SUS, RESPECT). The report shows the four game cards, final scores, team results and a story-sized share card.
6. Rematch keeps the room, skips questions the group has already seen, and updates the season table.

Your taste is saved on your phone, so the next room is one tap ("Join as Caleb").

## Stack

React + Vite + Tailwind in `frontend/`, FastAPI in `backend/`, Spotify Web API for login and catalog search, MusicBrainz for genres (Spotify stopped returning them in February 2026), Supabase for room snapshots, Claude for the optional question wording. Installable as a home screen app.

## Run it

```bash
cp .env.example .env    # fill in your Spotify app's client id and secret
uv venv && uv pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
.venv/bin/uvicorn backend.main:app --port 8888
```

Open http://127.0.0.1:8888. Spotify login needs `SPOTIFY_REDIRECT_URI` set and the same URI added to the Spotify app; without it the login option hides and quick picks, uploads and samples still work. Spotify Development Mode allows 5 signed-in accounts per app, and Extended Quota requires a registered business with 250k monthly users, which is why quick picks and uploads exist.

Tests: `.venv/bin/python -m pytest tests`

All glory to God! ✝️❤️
