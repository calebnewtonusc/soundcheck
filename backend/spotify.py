"""Spotify sign-in and the one-time stats pull.

Authorization-code flow with the secret held on the server. The access token
is used once, right after sign-in, to read top items and recent plays, then
dropped. Nothing about the account is kept except the profile slice.

Since Spotify's February 2026 Development Mode changes, artist objects no
longer carry genres or popularity, so genres come from MusicBrainz tags.
"""

from __future__ import annotations

import asyncio
import base64
import os
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx

API = "https://api.spotify.com/v1"
# The two read-only scopes SoundCheck asks for. Recent plays are optional:
# a player who turns them off is asked for top items only.
SCOPE_TOP = "user-top-read"
SCOPE_RECENT = "user-read-recently-played"


class SpotifyError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def _env(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        raise SpotifyError(500, f"{name} is not set on the server.")
    return v


def configured() -> bool:
    return all(os.environ.get(k) for k in ("SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET", "SPOTIFY_REDIRECT_URI"))


def authorize_url(state: str, include_recent: bool = True) -> str:
    return "https://accounts.spotify.com/authorize?" + urlencode({
        "response_type": "code",
        "client_id": _env("SPOTIFY_CLIENT_ID"),
        "scope": f"{SCOPE_TOP} {SCOPE_RECENT}" if include_recent else SCOPE_TOP,
        "redirect_uri": _env("SPOTIFY_REDIRECT_URI"),
        "state": state,
        "show_dialog": "true",
    })


async def exchange(code: str) -> str:
    basic = base64.b64encode(f"{_env('SPOTIFY_CLIENT_ID')}:{_env('SPOTIFY_CLIENT_SECRET')}".encode()).decode()
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post("https://accounts.spotify.com/api/token", headers={"Authorization": f"Basic {basic}"}, data={
            "grant_type": "authorization_code", "code": code, "redirect_uri": _env("SPOTIFY_REDIRECT_URI"),
        })
    if r.status_code != 200:
        raise SpotifyError(r.status_code, f"Token exchange failed: {r.text[:200]}")
    return r.json()["access_token"]


def _image(images: list | None) -> str | None:
    """The ~300px image: big enough for a card, small enough for a phone."""
    if not images:
        return None
    by_size = sorted(images, key=lambda i: abs((i.get("width") or 300) - 300))
    return by_size[0].get("url")


def _track(t: dict) -> dict:
    artists = t.get("artists") or [{}]
    album = t.get("album") or {}
    date = album.get("release_date") or ""
    return {"name": t.get("name", "?"), "artist": artists[0].get("name", "?"), "image": _image(album.get("images")),
            "year": int(date[:4]) if date[:4].isdigit() else None}


def _artist(a: dict) -> dict:
    return {"name": a.get("name", "?"), "genres": a.get("genres") or [], "image": _image(a.get("images"))}


def _local_hour(played_at: str, tz_minutes: int) -> int | None:
    try:
        utc = datetime.fromisoformat(played_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    # The browser reports getTimezoneOffset(): minutes to ADD to local to get UTC.
    return (utc.astimezone(timezone.utc) - timedelta(minutes=tz_minutes)).hour


async def fetch_profile(token: str, tz_minutes: int = 0, include_recent: bool = True) -> tuple[str, str | None, dict]:
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(base_url=API, headers=headers, timeout=15) as c:
        async def get(path: str) -> dict:
            r = await c.get(path)
            if r.status_code == 403:
                raise SpotifyError(403, "not_registered")
            if r.status_code != 200:
                raise SpotifyError(r.status_code, f"{path}: {r.text[:200]}")
            return r.json()

        me, ts, tl, as_, al, rp = await asyncio.gather(
            get("/me"),
            get("/me/top/tracks?time_range=short_term&limit=20"),
            get("/me/top/tracks?time_range=long_term&limit=20"),
            get("/me/top/artists?time_range=short_term&limit=20"),
            get("/me/top/artists?time_range=long_term&limit=20"),
            get("/me/player/recently-played?limit=50") if include_recent else _empty(),
        )
    profile = {
        "top_tracks_short": [_track(t) for t in ts.get("items", [])],
        "top_tracks_long": [_track(t) for t in tl.get("items", [])],
        "top_artists_short": [_artist(a) for a in as_.get("items", [])],
        "top_artists_long": [_artist(a) for a in al.get("items", [])],
        "recent": [{**_track(i["track"]), "hour": _local_hour(i.get("played_at", ""), tz_minutes)}
                   for i in rp.get("items", []) if i.get("track")],
    }
    return me.get("display_name") or "", _image(me.get("images")), profile


async def _empty() -> dict:
    return {"items": []}


# --- genres from MusicBrainz -----------------------------------------------

MB = "https://musicbrainz.org/ws/2/artist/"
MB_HEADERS = {"User-Agent": "SoundCheck/1.0 (https://github.com/calebnewtonusc/soundcheck)"}
# MusicBrainz allows one request per second per client; past that it answers
# 503 and every lookup in the batch comes back empty.
MB_INTERVAL = 1.1
# Tags that describe a place, a decade or a habit rather than a sound.
NOT_GENRES = {
    "american", "british", "english", "canadian", "australian", "irish", "swedish", "korean", "japanese",
    "seen live", "usa", "uk", "us", "male vocalists", "female vocalists", "singer-songwriter", "producer",
    "2010s", "2020s", "2000s", "1990s", "00s", "10s", "20s", "rapper", "favorites", "spotify",
}
_genre_cache: dict[str, list[str]] = {}
_mb_lock = asyncio.Lock()
_mb_last = 0.0


async def genres_for(name: str) -> list[str]:
    global _mb_last
    if name in _genre_cache:
        return _genre_cache[name]
    async with _mb_lock:
        if name in _genre_cache:
            return _genre_cache[name]
        wait = MB_INTERVAL - (time.monotonic() - _mb_last)
        if wait > 0:
            await asyncio.sleep(wait)
        _mb_last = time.monotonic()
        tags: list[str] = []
        try:
            async with httpx.AsyncClient(timeout=8, headers=MB_HEADERS) as c:
                r = await c.get(MB, params={"query": f'artist:"{name}"', "limit": 1, "fmt": "json"})
            if r.status_code == 200:
                hits = r.json().get("artists") or []
                if hits and (hits[0].get("score") or 0) >= 90:
                    ranked = sorted(hits[0].get("tags") or [], key=lambda t: -(t.get("count") or 0))
                    tags = [t["name"].lower() for t in ranked if t.get("name") and t["name"].lower() not in NOT_GENRES][:3]
        except httpx.HTTPError:
            return []  # Not cached: a network blip shouldn't stick for the whole session.
        _genre_cache[name] = tags
        return tags


async def add_genres(profile: dict, limit: int = 8) -> None:
    """Fill genres on a player's top artists in place, newest-first priority."""
    seen: set[str] = set()
    for key in ("top_artists_long", "top_artists_short"):
        for a in profile.get(key, [])[:limit]:
            if a.get("genres") or a["name"] in seen:
                continue
            seen.add(a["name"])
            a["genres"] = await genres_for(a["name"])
    # Share results across both lists so short-term copies get them too.
    for key in ("top_artists_long", "top_artists_short"):
        for a in profile.get(key, []):
            if not a.get("genres") and a["name"] in _genre_cache:
                a["genres"] = _genre_cache[a["name"]]


# --- catalog search for quick picks ----------------------------------------
# Client-credentials calls act as the app, not a user, so they don't count
# toward Development Mode's 5-user allowlist.

_app_token: dict = {"value": "", "expires": 0.0}


async def _token() -> str:
    if _app_token["value"] and time.time() < _app_token["expires"]:
        return _app_token["value"]
    basic = base64.b64encode(f"{_env('SPOTIFY_CLIENT_ID')}:{_env('SPOTIFY_CLIENT_SECRET')}".encode()).decode()
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post("https://accounts.spotify.com/api/token", headers={"Authorization": f"Basic {basic}"},
                         data={"grant_type": "client_credentials"})
    r.raise_for_status()
    body = r.json()
    _app_token.update(value=body["access_token"], expires=time.time() + body.get("expires_in", 3600) - 60)
    return _app_token["value"]


def search_configured() -> bool:
    return bool(os.environ.get("SPOTIFY_CLIENT_ID") and os.environ.get("SPOTIFY_CLIENT_SECRET"))


async def search(q: str, kind: str) -> list[dict]:
    token = await _token()
    async with httpx.AsyncClient(timeout=10) as c:
        # Development Mode caps search at 10 results per page.
        r = await c.get(f"{API}/search", params={"q": q, "type": kind, "limit": 8},
                        headers={"Authorization": f"Bearer {token}"})
    if r.status_code != 200:
        raise SpotifyError(r.status_code, r.text[:200])
    items = r.json().get(kind + "s", {}).get("items", [])
    if kind == "artist":
        return [_artist(a) for a in items if a]
    return [_track(t) for t in items if t]
