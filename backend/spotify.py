"""Spotify sign-in and the one-time stats pull.

Authorization-code flow with the secret held on the server. The access token
is used once, right after sign-in, to read top items and recent plays, then
dropped. Nothing about the account is stored except the profile slice.
"""

from __future__ import annotations

import asyncio
import base64
import os
from urllib.parse import urlencode

import httpx

API = "https://api.spotify.com/v1"
SCOPES = "user-top-read user-read-recently-played"


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


def authorize_url(state: str) -> str:
    return "https://accounts.spotify.com/authorize?" + urlencode({
        "response_type": "code",
        "client_id": _env("SPOTIFY_CLIENT_ID"),
        "scope": SCOPES,
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


def _track(t: dict) -> dict:
    artists = t.get("artists") or [{}]
    return {"name": t.get("name", "?"), "artist": artists[0].get("name", "?")}


def _artist(a: dict) -> dict:
    # Development Mode responses can omit genres; questions skip what's missing.
    return {"name": a.get("name", "?"), "genres": a.get("genres") or []}


async def fetch_profile(token: str) -> tuple[str, dict]:
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
            get("/me/player/recently-played?limit=50"),
        )
    profile = {
        "top_tracks_short": [_track(t) for t in ts.get("items", [])],
        "top_tracks_long": [_track(t) for t in tl.get("items", [])],
        "top_artists_short": [_artist(a) for a in as_.get("items", [])],
        "top_artists_long": [_artist(a) for a in al.get("items", [])],
        "recent": [_track(i["track"]) for i in rp.get("items", []) if i.get("track")],
    }
    return me.get("display_name") or "", profile
