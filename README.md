# SoundCheck

Your friends. Their music. One very competitive quiz.

SoundCheck turns a group's Spotify listening history into a party quiz. Everyone joins a private room, connects Spotify, and answers questions only friends could get right: whose #1 song this month is "Espresso", who's in a brand new Kendrick phase, whose top genre is indie folk. The game ends on four game cards: Most Loyal Listener, Biggest Genre Switch, Top 0.5% Listener and Biggest Song Looper.

## How a game runs

1. The host starts a room and shares the 4-letter code.
2. Each player connects Spotify, or joins with a sample profile.
3. SoundCheck reads top tracks, top artists and the last 50 plays once, writes 8 questions across songs, artists and genre, and drops the token.
4. Everyone picks a friend on their phone. A right answer is 100 points plus up to 50 for speed. The person a question is about gets 50 for every friend who got them right.
5. The report shows the game cards and final scores. Rematch keeps the room.

## Stack

React + Vite + Tailwind in `frontend/`, FastAPI in `backend/`, Spotify Web API. Rooms live in memory for now; Supabase is the planned store.

## Run it

```bash
cp .env.example .env    # fill in your Spotify app's client id and secret
uv venv && uv pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
.venv/bin/uvicorn backend.main:app --port 8888
```

Open http://127.0.0.1:8888. The Spotify app needs `http://127.0.0.1:8888/callback` as a Redirect URI. While the app is in Spotify Development Mode, only accounts added under User Management can sign in, so "Sample profile" and "Add demo friends" exist for playing without them.

Tests: `.venv/bin/python -m pytest tests`

All glory to God! ✝️❤️
