"""SoundCheck API and static host.

Rooms live in memory on one instance and are mirrored to Supabase every few
seconds, so a deploy or restart picks every open game back up.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import re
import secrets
import time
from collections import defaultdict, deque
from pathlib import Path
from urllib.parse import urlencode

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


def _load_env() -> None:
    env = Path(__file__).resolve().parent.parent / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))


_load_env()

from . import ai, spotify, statsfm, store  # noqa: E402
from .game import MAX_PLAYERS, Room, new_code  # noqa: E402
from .samples import SAMPLES, sample_profile  # noqa: E402

# A room is a friend group's standing link: it keeps season standings and
# who's in, so it lives 30 days past its last game. Leaving deletes your data
# right away; an abandoned room's data goes when it expires.
ROOM_TTL = 30 * 24 * 60 * 60
LOGIN_TTL = 10 * 60
MAX_ROOMS = 2000
# Room creation per IP: 10 a minute covers a host restarting a few times and
# stops a script from walking the 331,776-code space.
CREATE_LIMIT, CREATE_WINDOW = 10, 60
SAVE_EVERY = 2.0
LOGIN_COOKIE = "sc_login"

rooms: dict[str, Room] = {}
saved_version: dict[str, int] = {}
pending_logins: dict[str, dict] = {}
creates: dict[str, deque] = defaultdict(deque)


PRUNE_EVERY = 5 * 60


async def _saver() -> None:
    last_prune = 0.0
    while True:
        await asyncio.sleep(SAVE_EVERY)
        now = time.time()
        for code, room in list(rooms.items()):
            room.tick()
            idle = now - room.touched
            if idle > ROOM_TTL or (not room.players and idle > EMPTY_ROOM_TTL):
                rooms.pop(code, None)
                saved_version.pop(code, None)
                continue
            if saved_version.get(code) != room.version:
                if await store.save(room.to_dict()):
                    saved_version[code] = room.version
        if now - last_prune > PRUNE_EVERY:
            last_prune = now
            await store.prune(now - ROOM_TTL)


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI):
    for d in await store.load(time.time() - ROOM_TTL):
        try:
            room = Room.from_dict(d)
        except (TypeError, KeyError):
            continue
        rooms[room.code] = room
        saved_version[room.code] = room.version
    task = asyncio.create_task(_saver())
    yield
    task.cancel()
    for room in rooms.values():
        await store.save(room.to_dict())


app = FastAPI(title="SoundCheck", lifespan=lifespan)


def _room(code: str, touch: bool = True) -> Room:
    room = rooms.get(code.upper())
    if not room:
        raise HTTPException(404, "No room with that code. Check it and try again.")
    if touch:
        room.touched = time.time()
    return room


def _ip(request: Request) -> str:
    # Railway's proxy appends the real client address as the last
    # X-Forwarded-For entry; anything before it is whatever the client sent.
    fwd = [x.strip() for x in request.headers.get("x-forwarded-for", "").split(",") if x.strip()]
    return fwd[-1] if fwd else (request.client.host if request.client else "?")


lookups: dict[str, deque] = defaultdict(deque)
# Members poll once a second; 150 a minute leaves room for a slow phone
# catching up, and stops a script walking the code space.
LOOKUP_LIMIT = 150
# A room nobody ever joined is gone after an hour, not 30 days.
EMPTY_ROOM_TTL = 60 * 60


def _auth(room: Room, pid: str, key: str):
    p = room.players.get(pid)
    if not p or not secrets.compare_digest(p.key, key):
        raise HTTPException(403, "You're not in this room.")
    return p


def _host(room: Room, pid: str, key: str) -> None:
    _auth(room, pid, key)
    if room.host_id != pid:
        raise HTTPException(403, "Only the host can do that.")


class Who(BaseModel):
    pid: str = Field(max_length=16)
    key: str = Field(max_length=64)


class Join(BaseModel):
    name: str = Field(max_length=40)
    recent: bool = True


class Answer(Who):
    choice: str = Field(max_length=16)


class Track(BaseModel):
    name: str = Field(max_length=200)
    artist: str = Field(max_length=200)
    image: str | None = Field(default=None, max_length=300)
    year: int | None = Field(default=None, ge=1900, le=2100)
    hour: int | None = Field(default=None, ge=0, le=23)


class Artist(BaseModel):
    name: str = Field(max_length=200)
    genres: list[str] = Field(default_factory=list, max_length=5)
    image: str | None = Field(default=None, max_length=300)


class Profile(BaseModel):
    top_tracks_short: list[Track] = Field(default_factory=list, max_length=50)
    top_tracks_long: list[Track] = Field(default_factory=list, max_length=50)
    top_artists_short: list[Artist] = Field(default_factory=list, max_length=50)
    top_artists_long: list[Artist] = Field(default_factory=list, max_length=50)
    recent: list[Track] = Field(default_factory=list, max_length=50)
    self_reported: bool = False


class JoinProfile(BaseModel):
    name: str = Field(max_length=40)
    source: str = Field(pattern="^(picks|export|spotify|sample|statsfm)$")
    avatar: str | None = Field(default=None, max_length=300)
    profile: Profile


class UpdateProfile(Who):
    source: str = Field(pattern="^(picks|export|spotify|sample|statsfm)$")
    profile: Profile


# Only known music CDNs: a profile is user-supplied, and every phone in the
# room loads these URLs.
IMAGE_HOST = statsfm.IMAGE_HOSTS


def _clean(profile: Profile) -> dict:
    d = profile.model_dump()
    for key in ("top_tracks_short", "top_tracks_long", "top_artists_short", "top_artists_long", "recent"):
        for item in d[key]:
            if item.get("image") and not item["image"].startswith(IMAGE_HOST):
                item["image"] = None
            if "genres" in item:
                item["genres"] = [g[:40].lower() for g in item["genres"]]
    return d


class Settings(Who):
    length: int | None = None
    mode: str | None = Field(default=None, max_length=16)
    teams: bool | None = None
    ai: bool | None = None


class React(Who):
    label: str = Field(max_length=16)


# Spotify Development Mode: 5 accounts per app, and the owner's is one.
SPOTIFY_SPOTS = 5
OWNER_SPOTS = 1
_spots = {"added": 0, "checked": 0.0}


async def _spots_left() -> int:
    if time.time() - _spots["checked"] > 60:
        rows = await store.list_access()
        _spots.update(added=sum(1 for r in rows if r.get("status") == "added"), checked=time.time())
    return max(0, SPOTIFY_SPOTS - OWNER_SPOTS - _spots["added"])


EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,120}\.[a-zA-Z]{2,}$")


class AccessRequest(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    email: str = Field(max_length=200)
    room: str = Field(default="", max_length=8)


requests_log: dict[str, deque] = defaultdict(deque)


@app.post("/api/spotify-access")
async def spotify_access(request: Request, body: AccessRequest):
    if not EMAIL.match(body.email.strip()):
        raise HTTPException(400, "That doesn't look like an email.")
    hits = requests_log[_ip(request)]
    now = time.time()
    while hits and now - hits[0] > 3600:
        hits.popleft()
    if len(hits) >= 20:
        raise HTTPException(429, "Already sent. Hang tight.")
    hits.append(now)
    if await _spots_left() <= 0:
        raise HTTPException(409, "Spotify sign-in is full for now. Quick picks works the same.")
    if not await store.request_access(body.email.strip(), body.name.strip(), body.room.upper()):
        raise HTTPException(503, "Couldn't save that. Try again in a sec.")
    return {"ok": True}


admin_fails: dict[str, deque] = defaultdict(deque)
# Ten wrong keys an hour per IP: plenty for a typo, nothing for guessing a
# 32-character random key.
ADMIN_FAIL_LIMIT = 10


def _admin(request: Request, key: str) -> None:
    fails = admin_fails[_ip(request)]
    now = time.time()
    while fails and now - fails[0] > 3600:
        fails.popleft()
    if len(fails) >= ADMIN_FAIL_LIMIT:
        raise HTTPException(429, "Too many tries.")
    want = os.environ.get("ADMIN_KEY", "")
    if len(want) < 32 or len(key) > 100 or not secrets.compare_digest(want, key):
        fails.append(now)
        raise HTTPException(404, "Not found.")


class AdminSet(BaseModel):
    key: str = Field(max_length=100)
    email: str = Field(max_length=200)
    status: str = Field(pattern="^(pending|added|declined)$")


@app.get("/api/admin/access")
async def admin_access(request: Request):
    # Header, not query string: query strings land in proxy and access logs.
    _admin(request, request.headers.get("x-admin-key", ""))
    rows = await store.list_access()
    added = sum(1 for r in rows if r.get("status") == "added")
    _spots.update(added=added, checked=time.time())
    return {"requests": rows, "spots_total": SPOTIFY_SPOTS, "spots_used": OWNER_SPOTS + added,
            "dashboard": f"https://developer.spotify.com/dashboard/{os.environ.get('SPOTIFY_CLIENT_ID', '')}/users"}


@app.post("/api/admin/access")
async def admin_set(request: Request, body: AdminSet):
    _admin(request, body.key)
    if not await store.set_access(body.email, body.status):
        raise HTTPException(503, "Couldn't save that.")
    _spots["checked"] = 0.0
    rows = await store.list_access()
    added = sum(1 for r in rows if r.get("status") == "added")
    return {"requests": rows, "spots_total": SPOTIFY_SPOTS, "spots_used": OWNER_SPOTS + added,
            "dashboard": f"https://developer.spotify.com/dashboard/{os.environ.get('SPOTIFY_CLIENT_ID', '')}/users"}


@app.get("/api/health")
async def health():
    return {"spotify_spots_left": await _spots_left() if spotify.configured() else 0,"ok": True, "spotify": spotify.configured(), "store": store.configured(), "ai": ai.configured(), "search": spotify.search_configured(), "rooms": len(rooms)}


@app.post("/api/rooms")
def create_room(request: Request):
    q = creates[_ip(request)]
    now = time.time()
    while q and now - q[0] > CREATE_WINDOW:
        q.popleft()
    if len(q) >= CREATE_LIMIT:
        raise HTTPException(429, "Too many rooms from here. Give it a minute.")
    if len(rooms) >= MAX_ROOMS:
        raise HTTPException(503, "SoundCheck is full right now. Try again soon.")
    try:
        code = new_code(set(rooms))
    except RuntimeError:
        raise HTTPException(503, "SoundCheck is full right now. Try again soon.")
    q.append(now)
    rooms[code] = Room(code=code)
    return {"code": code}


@app.get("/api/rooms/{code}")
def get_room(request: Request, code: str, pid: str = "", key: str = ""):
    now = time.time()
    room = rooms.get(code.upper())
    p = room.players.get(pid) if room else None
    if room and p and secrets.compare_digest(p.key, key):
        # Members are never limited: a room of friends on one dorm WiFi
        # shares an IP and polls once a second each (load test, 2026-10-26:
        # 100 players from one address hit the old per-IP cap in a minute).
        room.touched = now
        return room.view(pid)
    hits = lookups[_ip(request)]
    while hits and now - hits[0] > 60:
        hits.popleft()
    if len(hits) >= LOOKUP_LIMIT:
        raise HTTPException(429, "Slow down a sec.")
    hits.append(now)
    return _room(code, touch=False).public_view()


def _act(room: Room, fn, pid: str):
    try:
        fn()
    except ValueError as e:
        raise HTTPException(400, str(e))
    return room.view(pid)


@app.post("/api/rooms/{code}/join-sample")
def join_sample(code: str, body: Join):
    room = _room(code)
    used = {p.profile.get("_sample") for p in room.players.values()}
    sample = next((s for s in SAMPLES if s["name"] not in used), SAMPLES[0])
    profile = sample_profile(sample)
    if not body.recent:
        profile["recent"] = []
    try:
        p = room.add_player(body.name, profile, "sample")
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"pid": p.id, "key": p.key}


@app.post("/api/rooms/{code}/join-profile")
def join_profile(code: str, body: JoinProfile, background: BackgroundTasks):
    room = _room(code)
    profile = _clean(body.profile)
    if not profile["top_tracks_short"] and not profile["top_artists_long"]:
        raise HTTPException(400, "Pick at least a few artists or songs first.")
    avatar = body.avatar if body.avatar and body.avatar.startswith(IMAGE_HOST) else None
    try:
        p = room.add_player(body.name, profile, body.source, avatar=avatar)
    except ValueError as e:
        raise HTTPException(400, str(e))
    background.add_task(spotify.add_genres, profile)
    return {"pid": p.id, "key": p.key}


class JoinStats(BaseModel):
    name: str = Field(default="", max_length=40)
    handle: str = Field(min_length=2, max_length=200)


stats_lookups: dict[str, deque] = defaultdict(deque)


@app.post("/api/rooms/{code}/join-statsfm")
async def join_statsfm(request: Request, code: str, body: JoinStats, background: BackgroundTasks):
    room = _room(code)
    # Refuse before any outbound call: a full or started room costs nothing.
    if room.phase != "lobby":
        raise HTTPException(400, "This game already started. Wait for the rematch.")
    if len(room.players) >= MAX_PLAYERS:
        raise HTTPException(400, "This room is full.")
    handle = statsfm.handle_from(body.handle)
    if not handle:
        raise HTTPException(400, "Paste your stats.fm profile link or username.")
    hits = stats_lookups[_ip(request)]
    now = time.time()
    while hits and now - hits[0] > 60:
        hits.popleft()
    # A room on one WiFi connecting together: 30 a minute per IP.
    if len(hits) >= 30:
        raise HTTPException(429, "Give it a minute and try again.")
    hits.append(now)
    try:
        display, avatar, profile = await statsfm.fetch(handle)
    except statsfm.StatsError as e:
        raise HTTPException(400, str(e))
    except httpx.HTTPError:
        raise HTTPException(502, "stats.fm didn't answer. Try again in a sec.")
    try:
        p = room.add_player(body.name.strip() or display, profile, "statsfm", avatar=avatar)
    except ValueError as e:
        raise HTTPException(400, str(e))
    # Release years only feed decade questions; fill them after joining so
    # the player isn't waiting on ~20 catalog searches.
    background.add_task(spotify.add_years, profile)
    return {"pid": p.id, "key": p.key, "name": p.name, "avatar": avatar, "profile": profile, "handle": handle}


@app.post("/api/rooms/{code}/profile")
def update_profile(code: str, body: UpdateProfile, background: BackgroundTasks):
    room = _room(code)
    p = _auth(room, body.pid, body.key)
    if room.phase != "lobby":
        raise HTTPException(400, "Update your taste between games.")
    profile = _clean(body.profile)
    with room.lock:
        p.profile, p.source = profile, body.source
        room.version += 1
    background.add_task(spotify.add_genres, profile)
    return room.view(body.pid)


@app.post("/api/rooms/{code}/my-profile")
def my_profile(code: str, body: Who):
    """Hands a player their own profile so their phone can keep it for next time."""
    room = _room(code)
    p = _auth(room, body.pid, body.key)
    return {"name": p.name, "avatar": p.avatar, "source": p.source, "profile": p.profile}


searches: dict[str, deque] = defaultdict(deque)
# Per IP, and a whole room on one WiFi shares an IP: 12 friends each typing
# through ten picks at once is about 300 searches a minute.
SEARCH_LIMIT = 300


@app.get("/api/search")
async def search(request: Request, q: str, kind: str = "artist"):
    if kind not in ("artist", "track") or not q.strip() or len(q) > 80:
        raise HTTPException(400, "Search for an artist or a song.")
    if not spotify.search_configured():
        raise HTTPException(503, "Search isn't set up on this server.")
    hits = searches[_ip(request)]
    now = time.time()
    while hits and now - hits[0] > 60:
        hits.popleft()
    if len(hits) >= SEARCH_LIMIT:
        raise HTTPException(429, "Slow down a sec.")
    hits.append(now)
    try:
        return await spotify.search(q.strip(), kind)
    except (spotify.SpotifyError, httpx.HTTPError):
        raise HTTPException(502, "Spotify search hiccuped. Try again.")


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
            room.add_player(s["name"], sample_profile(s), "sample", is_bot=True)
        except ValueError:
            break
        added += 1
    if not added:
        raise HTTPException(400, "Every demo friend is already here.")
    return room.view(body.pid)


@app.post("/api/rooms/{code}/leave")
def leave(code: str, body: Who):
    room = _room(code)
    _auth(room, body.pid, body.key)
    return _act(room, lambda: room.remove_player(body.pid), body.pid)


@app.post("/api/rooms/{code}/kick/{target}")
def kick(code: str, target: str, body: Who):
    room = _room(code)
    _host(room, body.pid, body.key)
    if target == body.pid:
        raise HTTPException(400, "Use leave to remove yourself.")
    return _act(room, lambda: room.remove_player(target), body.pid)


@app.post("/api/rooms/{code}/settings")
def settings(code: str, body: Settings):
    room = _room(code)
    _host(room, body.pid, body.key)
    if body.ai and not ai.configured():
        raise HTTPException(400, "AI wording isn't set up on this server.")
    return _act(room, lambda: room.settings(body.length, body.mode, body.teams, body.ai), body.pid)


@app.post("/api/rooms/{code}/shuffle-teams")
def shuffle_teams(code: str, body: Who):
    room = _room(code)
    _host(room, body.pid, body.key)
    return _act(room, room.shuffle_teams, body.pid)


@app.post("/api/rooms/{code}/react")
def react(code: str, body: React):
    room = _room(code)
    _auth(room, body.pid, body.key)
    return _act(room, lambda: room.react(body.pid, body.label), body.pid)


@app.post("/api/rooms/{code}/start")
async def start(code: str, body: Who):
    room = _room(code)
    _host(room, body.pid, body.key)
    try:
        questions = room.prepare()
    except ValueError as e:
        raise HTTPException(400, str(e))
    if room.ai and ai.configured():
        names = [p.name for p in room.players.values()]
        entities = {a["name"] for p in room.players.values() for k in ("top_artists_long", "top_artists_short") for a in p.profile.get(k, [])}
        entities |= {g for p in room.players.values() for k in ("top_artists_long", "top_artists_short") for a in p.profile.get(k, []) for g in a.get("genres") or []}
        texts = [q.text for q in questions]
        keep = [[e for e in entities if e in t] + re.findall(r"\d+", t) for t in texts]
        for q, t in zip(questions, await ai.reword(texts, names, keep)):
            q.text = t
    return _act(room, lambda: room.begin(questions), body.pid)


@app.post("/api/rooms/{code}/answer")
def answer(code: str, body: Answer):
    room = _room(code)
    _auth(room, body.pid, body.key)
    return _act(room, lambda: room.answer(body.pid, body.choice), body.pid)


@app.post("/api/rooms/{code}/next")
def next_step(code: str, body: Who):
    room = _room(code)
    _host(room, body.pid, body.key)
    return _act(room, room.next, body.pid)


@app.post("/api/rooms/{code}/rematch")
def rematch(code: str, body: Who):
    room = _room(code)
    _host(room, body.pid, body.key)
    return _act(room, room.rematch, body.pid)


@app.get("/api/login")
def login(room: str, name: str, tz: int = 0, recent: int = 1):
    _room(room)
    if not spotify.configured():
        raise HTTPException(503, "Spotify isn't set up on this server. Join with a sample profile.")
    now = time.time()
    for s in [s for s, v in pending_logins.items() if now - v["at"] > LOGIN_TTL]:
        pending_logins.pop(s, None)
    state = secrets.token_urlsafe(16)
    nonce = secrets.token_urlsafe(16)
    pending_logins[state] = {"room": room.upper(), "name": name[:20], "tz": max(-840, min(840, tz)), "nonce": nonce, "at": now,
                             "recent": bool(recent)}
    res = RedirectResponse(spotify.authorize_url(state, include_recent=bool(recent)))
    # Ties the callback to the browser that started sign-in, so a stolen
    # callback link can't drop someone else's history into a room.
    res.set_cookie(LOGIN_COOKIE, nonce, max_age=LOGIN_TTL, httponly=True, samesite="lax",
                   secure=os.environ.get("SPOTIFY_REDIRECT_URI", "").startswith("https://"))
    return res


@app.get("/callback")
async def callback(request: Request, background: BackgroundTasks, state: str = "", code: str = "", error: str = ""):
    pending = pending_logins.pop(state, None)
    cookie = request.cookies.get(LOGIN_COOKIE, "")
    if not pending or not secrets.compare_digest(pending["nonce"], cookie):
        return _bounce("/", {"error": "That sign-in expired. Try again."})
    back = f"/room/{pending['room']}"
    if error or not code:
        return _bounce(back, {"error": "Spotify sign-in was cancelled."})
    try:
        token = await spotify.exchange(code)
        display, avatar, profile = await spotify.fetch_profile(token, pending["tz"], include_recent=pending["recent"])
    except spotify.SpotifyError as e:
        if str(e) == "not_registered":
            # Not on the app's allowlist yet: hand them the one-box request form.
            return _bounce(back, {"spotify": "not_registered", "name": pending["name"]})
        return _bounce(back, {"error": "Couldn't read your Spotify. Try again."})
    room = rooms.get(pending["room"])
    if not room:
        return _bounce("/", {"error": "That room closed."})
    if not profile["top_tracks_short"] and not profile["recent"]:
        return _bounce(back, {"error": "Your Spotify doesn't have enough listening yet. Join with a sample profile."})
    try:
        p = room.add_player(pending["name"] or display or "Player", profile, "spotify", avatar=avatar)
    except ValueError as e:
        return _bounce(back, {"error": str(e)})
    background.add_task(spotify.add_genres, profile)
    return _bounce(back, {"pid": p.id, "key": p.key})


def _bounce(path: str, params: dict) -> RedirectResponse:
    res = RedirectResponse(path + "?" + urlencode(params))
    res.delete_cookie(LOGIN_COOKIE)
    return res


DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        f = (DIST / path).resolve()
        if path and f.is_file() and DIST in f.parents:
            return FileResponse(f)
        return FileResponse(DIST / "index.html")
