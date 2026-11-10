# SoundCheck

Your friends. Their music. One very competitive quiz.

SoundCheck turns a group's Spotify listening history into a party quiz. Everyone joins a private room, connects Spotify, and answers questions only friends could get right: whose #1 song this month is "Espresso", who's in a brand new Kendrick phase, whose top genre is indie folk. The game ends on four game cards: Most Loyal Listener, Biggest Genre Switch, Top 0.5% Listener and Biggest Song Looper.

## How a game runs

1. The host starts a room and texts the link. The link keeps working for 30 days, so a friend group reuses it every week and builds season standings.
2. Everyone brings their taste: Connect Spotify through stats.fm (sign in there once with Spotify, paste the username back; no cap), quick picks (search and pick 3 to 5 artists and songs), an upload of their Spotify data export (read on their own phone, only the summary is sent), direct Spotify login (5 accounts while the app is in Spotify Development Mode, with an in-app request box and an admin page at /admin#key), or a sample listener.
3. The host picks a mode (Classic, Wrapped, Road trip, Decades, Genres), a length (5, 8 or 12) and optionally team mode or AI wording.
4. Questions come in two shapes: pick a friend ("Who's the biggest Drake fan in the room?") or pick an answer ("What's the last song Kaylie played?"). Right answers score 100 plus up to 50 for speed, and whoever a question is about gets 50 for every friend who got them right.
5. After each reveal everyone can react (CALLED IT, NO WAY, SUS, RESPECT). The report shows the four game cards, final scores, team results and a story-sized share card.
6. The game ends on three Soundtrack rounds. A moment drops ("PCH at sunset, windows down"), everyone picks a song from their own top songs (or searches Spotify for any song), and the room votes on the picks without knowing whose is whose. Each vote is 100. The reveal says who picked what, plays the winner, and calls out a pick nobody else in the room listens to (deep cut, +50), two picks from the same artist (taste twins), and how often the picker has played it lately. The last round is written from the group's own listening ("Pick Sam's walkout song, he's been deep in alternative r&b"): that friend sits out picking and judges alone, and their vote is worth 250. The host can turn the Soundtrack finale off in the lobby.
7. Rematch keeps the room, skips questions and moments the group has already seen, and updates the season table.

Soundtrack came out of five user interviews on 2026-11-09. People liked it more than the quiz 3 to 2, and the quiz's main knock was "a do one time and then like have an enjoyable night" game. Picking from your own songs fixes the two worries about it ("people don't always have something in their brain for this kind of thing", and a song nobody knows "ruins the vibe"), and anonymous picks bring the quiz's "wait, THAT'S yours?" reveal into every round.

Your taste is saved on your phone, so the next room is one tap ("Join as Caleb").

## Stack

React + Vite + Tailwind in `frontend/`, FastAPI in `backend/`, stats.fm public profiles and the Spotify Web API for listening data and catalog search, MusicBrainz for genres (Spotify stopped returning them in February 2026), Supabase for room snapshots, Claude for the optional question wording. Installable as a home screen app.

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
