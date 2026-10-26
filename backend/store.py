"""Room snapshots in Supabase.

The rooms table has row level security on and no policies, so the
publishable key alone reads nothing. The server goes through three
security-definer functions that check SUPABASE_ROOM_SECRET first.
Every call fails soft: a database blip costs persistence, never a game.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

import httpx

log = logging.getLogger("soundcheck.store")


def configured() -> bool:
    return all(os.environ.get(k) for k in ("SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_ROOM_SECRET"))


async def _rpc(fn: str, args: dict):
    url = f"{os.environ['SUPABASE_URL']}/rest/v1/rpc/{fn}"
    key = os.environ["SUPABASE_KEY"]
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(url, headers={"apikey": key, "Content-Type": "application/json"},
                         json={"secret": os.environ["SUPABASE_ROOM_SECRET"], **args})
    r.raise_for_status()
    return r.json() if r.content else None


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).isoformat()


async def save(state: dict) -> bool:
    if not configured():
        return True
    try:
        await _rpc("save_room", {"room_code": state["code"], "room_state": state})
        return True
    except httpx.HTTPError as e:
        log.warning("save %s failed: %s", state.get("code"), e)
        return False


async def load(since: float) -> list[dict]:
    if not configured():
        return []
    try:
        rows = await _rpc("load_rooms", {"since": _iso(since)})
        return [r["state"] for r in rows or []]
    except httpx.HTTPError as e:
        log.warning("load failed: %s", e)
        return []


async def prune(before: float) -> None:
    if not configured():
        return
    try:
        await _rpc("delete_rooms", {"before": _iso(before)})
    except httpx.HTTPError as e:
        log.warning("prune failed: %s", e)


async def request_access(email: str, name: str, room: str) -> bool:
    if not configured():
        return False
    try:
        await _rpc("request_access", {"req_email": email, "req_name": name, "req_room": room})
        return True
    except httpx.HTTPError as e:
        log.warning("request_access failed: %s", e)
        return False


async def list_access() -> list[dict]:
    if not configured():
        return []
    try:
        return await _rpc("list_access", {}) or []
    except httpx.HTTPError as e:
        log.warning("list_access failed: %s", e)
        return []


async def set_access(email: str, status: str) -> bool:
    if not configured():
        return False
    try:
        await _rpc("set_access", {"req_email": email, "new_status": status})
        return True
    except httpx.HTTPError as e:
        log.warning("set_access failed: %s", e)
        return False
