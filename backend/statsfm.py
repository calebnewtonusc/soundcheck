"""Listening history from a public stats.fm profile.

stats.fm signs people in with Spotify and kept Spotify's extended access,
which new apps can no longer get. Its public profile endpoints answer with
just a username: top tracks and artists per range, genres on each artist,
and recent plays with timestamps. No key, no user cap.

The endpoints are the ones stats.fm's own web app calls; they aren't a
published, versioned API, so every field read here is optional.
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx

API = "https://api.stats.fm/api/v1"
HEADERS = {"User-Agent": "SoundCheck/1.0 (https://github.com/calebnewtonusc/soundcheck)"}
# Images a profile may point at: Spotify's CDN, Apple's, and stats.fm's own.
IMAGE_HOSTS = ("https://i.scdn.co/", "https://is1-ssl.mzstatic.com/", "https://cdn.stats.fm/")
HANDLE = re.compile(r"^[A-Za-z0-9_.-]{2,64}$")


class StatsError(Exception):
    """A message a player can act on."""


def handle_from(text: str) -> str | None:
    """Accept a username, '@username', or any stats.fm profile link."""
    text = text.strip()
    m = re.search(r"stats\.fm/(?:user/)?([A-Za-z0-9_.-]+)", text)
    candidate = m.group(1) if m else text.lstrip("@")
    candidate = candidate.split("?")[0].strip("/")
    return candidate if HANDLE.match(candidate) else None


def _img(url: object) -> str | None:
    return url if isinstance(url, str) and url.startswith(IMAGE_HOSTS) else None


def _track(t: dict) -> dict:
    artists = t.get("artists") or [{}]
    albums = t.get("albums") or [{}]
    return {"name": str(t.get("name") or "?")[:200], "artist": str(artists[0].get("name") or "?")[:200],
            "image": _img(albums[0].get("image")), "year": None}


def _artist(a: dict) -> dict:
    return {"name": str(a.get("name") or "?")[:200], "genres": [str(g)[:40].lower() for g in (a.get("genres") or [])][:5],
            "image": _img(a.get("image"))}


def _hour(end_time: str, tz: ZoneInfo | None) -> int | None:
    try:
        dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    return dt.astimezone(tz).hour if tz else None


async def fetch(handle: str) -> tuple[str, str | None, dict]:
    """Return (display name, avatar, profile) or raise StatsError."""
    async with httpx.AsyncClient(base_url=API, headers=HEADERS, timeout=12) as c:
        r = await c.get(f"/users/{handle}")
        if r.status_code == 404:
            raise StatsError("Couldn't find that stats.fm profile. Check the username or paste your profile link.")
        if r.status_code != 200:
            raise StatsError("stats.fm didn't answer. Try again in a sec.")
        user = (r.json() or {}).get("item") or {}
        privacy = user.get("privacySettings") or {}
        if privacy.get("topTracks") is False or privacy.get("topArtists") is False:
            raise StatsError("Your stats.fm top tracks and artists are private. Turn them on in stats.fm settings, Privacy.")
        uid = user.get("id") or handle

        async def items(path: str) -> list[dict]:
            resp = await c.get(path)
            return (resp.json() or {}).get("items") or [] if resp.status_code == 200 else []

        ts, tl, as_, al, rp = await asyncio.gather(
            items(f"/users/{uid}/top/tracks?range=weeks&limit=20"),
            items(f"/users/{uid}/top/tracks?range=lifetime&limit=20"),
            items(f"/users/{uid}/top/artists?range=weeks&limit=20"),
            items(f"/users/{uid}/top/artists?range=lifetime&limit=20"),
            items(f"/users/{uid}/streams/recent?limit=50") if privacy.get("recentlyPlayed", True) else asyncio.sleep(0, result=[]),
        )
    try:
        tz = ZoneInfo(user["timezone"]) if user.get("timezone") else None
    except (ZoneInfoNotFoundError, ValueError):
        tz = None
    profile = {
        "top_tracks_short": [_track(i["track"]) for i in ts if i.get("track")],
        "top_tracks_long": [_track(i["track"]) for i in tl if i.get("track")],
        "top_artists_short": [_artist(i["artist"]) for i in as_ if i.get("artist")],
        "top_artists_long": [_artist(i["artist"]) for i in al if i.get("artist")],
        "recent": [{**_track(i["track"]), "hour": _hour(i.get("endTime", ""), tz)} for i in rp if i.get("track")],
    }
    if not profile["top_tracks_short"] and not profile["top_artists_long"]:
        raise StatsError("stats.fm doesn't have your listening yet. Give it a minute after signing up, then try again.")
    return str(user.get("displayName") or handle)[:40], _img(user.get("image")), profile
