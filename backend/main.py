"""SoundCheck API and static host.

Rooms live in memory: a game lasts minutes, and one Railway instance holds
every room. Supabase is the planned store once rooms need to outlive a deploy.
"""

from __future__ import annotations

import os
import secrets
import time
from pathlib import Path
from urllib.parse import urlencode

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import spotify
from .game import Room, new_code
from .samples import SAMPLES

app = FastAPI(title="SoundCheck")
rooms: dict[str, Room] = {}
pending_logins: dict[str, dict] = {}
# Two hours idle and a room is gone. A party game nobody touched since lunch
# is over, and memory is the only store.
ROOM_TTL = 2 * 60 * 60
LOGIN_TTL = 10 * 60


def _sweep() -> None:
    now = time.time()
    for code in [c for c, r in rooms.items() if now - r.touched > ROOM_TTL]:
        rooms.pop(code, None)
    for s in [s for s, v in pending_logins.items() if now - v["at"] > LOGIN_TTL]:
        pending_logins.pop(s, None)


def _room(code: str) -> Room:
    room = rooms.get(code.upper())
    if not room:
        raise HTTPException(404, "No room with that code. Check it and try again.")
    room.touched = time.time()
    return room


def _auth(room: Room, pid: str, key: str):
    p = room.players.get(pid)
    if not p or not secrets.compare_digest(p.key, key):
        raise HTTPException(403, "You're not in this room.")
    return p


def _host(room: Room, pid: str, key: str) -> None:
    _auth(room, pid, key)
    if room.host_id != pid:
        raise HTTPException(403, "Only the host can do that.")


def _fail(e: ValueError):
    raise HTTPException(400, str(e))


class Who(BaseModel):
    pid: str
    key: str


class Join(BaseModel):
    name: str


class Answer(Who):
    choice: str


@app.get("/api/health")
def health():
    return {"ok": True, "spotify": spotify.configured(), "rooms": len(rooms)}


@app.post("/api/rooms")
def create_room():
    _sweep()
    code = new_code(set(rooms))
    rooms[code] = Room(code=code)
    return {"code": code}


@app.get("/api/rooms/{code}")
def get_room(code: str, pid: str = "", key: str = ""):
    room = _room(code)
    me = pid if pid in room.players and secrets.compare_digest(room.players[pid].key, key) else None
    return room.view(me)


@app.post("/api/rooms/{code}/join-sample")
def join_sample(code: str, body: Join):
    room = _room(code)
    used = {p.profile.get("_sample") for p in room.players.values()}
    sample = next((s for s in SAMPLES if s["name"] not in used), SAMPLES[0])
    profile = {k: v for k, v in sample.items() if k != "name"} | {"_sample": sample["name"]}
    try:
        p = room.add_player(body.name, profile, "sample")
    except ValueError as e:
        _fail(e)
    return {"pid": p.id, "key": p.key}


@app.post("/api/rooms/{code}/bots")
def add_bots(code: str, body: Who):
    room = _room(code)
    _host(room, body.pid, body.key)
    used = {p.profile.get("_sample") for p in room.players.values()}
    added = 0
    for s in SAMPLES:
        if s["name"] in used or added >= 4:
            continue
        try:
            room.add_player(s["name"], {k: v for k, v in s.items() if k != "name"} | {"_sample": s["name"]}, "sample", is_bot=True)
        except ValueError:
            break
        added += 1
    return room.view(body.pid)


@app.post("/api/rooms/{code}/start")
def start(code: str, body: Who):
    room = _room(code)
    _host(room, body.pid, body.key)
    try:
        room.start()
    except ValueError as e:
        _fail(e)
    return room.view(body.pid)


@app.post("/api/rooms/{code}/answer")
def answer(code: str, body: Answer):
    room = _room(code)
    _auth(room, body.pid, body.key)
    try:
        room.answer(body.pid, body.choice)
    except ValueError as e:
        _fail(e)
    return room.view(body.pid)


@app.post("/api/rooms/{code}/next")
def next_step(code: str, body: Who):
    room = _room(code)
    _host(room, body.pid, body.key)
    room.next()
    return room.view(body.pid)


@app.post("/api/rooms/{code}/rematch")
def rematch(code: str, body: Who):
    room = _room(code)
    _host(room, body.pid, body.key)
    room.rematch()
    return room.view(body.pid)


@app.get("/api/login")
def login(room: str, name: str):
    _room(room)
    if not spotify.configured():
        raise HTTPException(503, "Spotify isn't set up on this server. Join with a sample profile.")
    _sweep()
    state = secrets.token_urlsafe(16)
    pending_logins[state] = {"room": room.upper(), "name": name[:20], "at": time.time()}
    return RedirectResponse(spotify.authorize_url(state))


@app.get("/callback")
async def callback(state: str = "", code: str = "", error: str = ""):
    pending = pending_logins.pop(state, None)
    if not pending:
        return RedirectResponse("/?" + urlencode({"error": "That sign-in expired. Try again."}))
    back = f"/room/{pending['room']}"
    if error or not code:
        return RedirectResponse(back + "?" + urlencode({"error": "Spotify sign-in was cancelled."}))
    try:
        token = await spotify.exchange(code)
        display, profile = await spotify.fetch_profile(token)
    except spotify.SpotifyError as e:
        msg = ("Spotify hasn't added this account to the app yet. Join with a sample profile for now."
               if str(e) == "not_registered" else "Couldn't read your Spotify. Try again.")
        return RedirectResponse(back + "?" + urlencode({"error": msg}))
    room = rooms.get(pending["room"])
    if not room:
        return RedirectResponse("/?" + urlencode({"error": "That room closed."}))
    try:
        p = room.add_player(pending["name"] or display or "Player", profile, "spotify")
    except ValueError as e:
        return RedirectResponse(back + "?" + urlencode({"error": str(e)}))
    return RedirectResponse(back + "?" + urlencode({"pid": p.id, "key": p.key}))


DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str, request: Request):
        f = DIST / path
        if path and f.is_file() and DIST in f.resolve().parents:
            return FileResponse(f)
        return FileResponse(DIST / "index.html")


def _load_env() -> None:
    env = Path(__file__).resolve().parent.parent / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))


_load_env()
