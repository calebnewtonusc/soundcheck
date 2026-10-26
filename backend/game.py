"""Rooms, question generation, scoring and the end-of-game cards.

A profile is the slice of a player's Spotify history the game needs:
top tracks and artists over the last 4 weeks (short) and the last year (long),
plus their last 50 plays. Tokens never reach this module.
"""

from __future__ import annotations

import random
import secrets
import string
import time
from collections import Counter
from dataclasses import dataclass, field

QUESTION_SECONDS = 20
QUESTIONS_PER_GAME = 8
MAX_PLAYERS = 12
# Points: 100 for a right answer plus up to 50 for speed. The person a question
# is about gets 50 for every friend who got them right, so being known pays.
BASE_POINTS = 100
SPEED_POINTS = 50
KNOWN_POINTS = 50

CATEGORIES = ["songs", "artists", "genre"]


def stats(profile: dict) -> dict:
    """Derive the facts questions and cards are built from."""
    short = profile.get("top_tracks_short") or []
    recent = profile.get("recent") or []
    artists_long = profile.get("top_artists_long") or []
    artists_short = profile.get("top_artists_short") or []

    loop_track, loop_count = None, 0
    if recent:
        (key, loop_count), = Counter((t["name"], t["artist"]) for t in recent).most_common(1)
        loop_track = {"name": key[0], "artist": key[1]}

    genres: Counter = Counter()
    for rank, artist in enumerate(artists_long[:20]):
        for g in artist.get("genres") or []:
            genres[g] += 20 - rank
    top_genre = genres.most_common(1)[0][0] if genres else None

    # Loyalty: how much of this month's top tracks belong to one artist.
    by_artist = Counter(t["artist"] for t in short)
    loyal_artist, loyal_n = by_artist.most_common(1)[0] if by_artist else (None, 0)
    loyalty = loyal_n / len(short) if short else 0.0

    # Era switch: how little this month's top artists overlap the year's.
    s_names = {a["name"] for a in artists_short[:10]}
    l_names = {a["name"] for a in artists_long[:10]}
    union = s_names | l_names
    switch = 1 - len(s_names & l_names) / len(union) if union else 0.0

    # Superfan: share of the last 50 plays going to their #1 artist of the year.
    top_artist = artists_long[0]["name"] if artists_long else None
    fan_plays = sum(1 for t in recent if t["artist"] == top_artist) if top_artist else 0

    return {
        "top_song": short[0] if short else None,
        "top_artist_year": top_artist,
        "top_artist_month": artists_short[0]["name"] if artists_short else None,
        "top_genre": top_genre,
        "loop_track": loop_track,
        "loop_count": loop_count,
        "loyal_artist": loyal_artist,
        "loyal_n": loyal_n,
        "loyal_total": len(short),
        "loyalty": loyalty,
        "switch": switch,
        "switch_from": next((a["name"] for a in artists_long if a["name"] not in s_names), None),
        "switch_to": next((a["name"] for a in artists_short if a["name"] not in l_names), None),
        "fan_artist": top_artist,
        "fan_plays": fan_plays,
        "recent_total": len(recent),
        "artist_names": {a["name"] for a in artists_long[:20]} | {a["name"] for a in artists_short[:20]},
        "top10_long": [a["name"] for a in artists_long[:10]],
    }


@dataclass
class Question:
    category: str
    text: str
    subject: str  # the player id the fact came from
    correct: list[str]  # every player the fact is true for
    explain: str


def _candidates(pid: str, name: str, s: dict, everyone: dict[str, dict]) -> list[tuple[str, str, callable, str]]:
    """Each candidate is (category, text, holds(stats) -> bool, explanation)."""
    out = []
    if s["top_song"]:
        t = s["top_song"]
        out.append((
            "songs",
            f"Whose #1 song this month is “{t['name']}” by {t['artist']}?",
            lambda x, t=t: x["top_song"] == t,
            f"{name}'s most played track over the last 4 weeks.",
        ))
    if s["loop_track"] and s["loop_count"] >= 3:
        t, n = s["loop_track"], s["loop_count"]
        out.append((
            "songs",
            f"Who played “{t['name']}” {n} times in their last {s['recent_total']} plays?",
            lambda x, t=t, n=n: x["loop_track"] == t and x["loop_count"] == n,
            f"{name} has it on repeat: {n} of their last {s['recent_total']} plays.",
        ))
    if s["top_artist_year"]:
        a = s["top_artist_year"]
        out.append((
            "artists",
            f"Who's had {a} as their #1 artist all year?",
            lambda x, a=a: x["top_artist_year"] == a,
            f"{a} tops {name}'s last 12 months.",
        ))
    others = [o for opid, o in everyone.items() if opid != pid]
    unique = [a for a in s["top10_long"] if all(a not in o["artist_names"] for o in others)]
    if unique:
        a = unique[0]
        out.append((
            "artists",
            f"Who's the only one here with {a} in their top artists?",
            lambda x, a=a: a in x["top10_long"],
            f"Nobody else in the room has {a} anywhere near their top 20.",
        ))
    if s["top_artist_month"] and s["top_artist_month"] not in s["top10_long"]:
        a = s["top_artist_month"]
        out.append((
            "artists",
            f"Who's in a brand new {a} phase?",
            lambda x, a=a: x["top_artist_month"] == a and a not in x["top10_long"],
            f"{a} is {name}'s #1 this month and wasn't in their top 10 for the year.",
        ))
    if s["top_genre"]:
        g = s["top_genre"]
        out.append((
            "genre",
            f"Whose top genre is {g}?",
            lambda x, g=g: x["top_genre"] == g,
            f"{g} shows up across {name}'s top artists more than anything else.",
        ))
    if s["loyal_n"] >= 3:
        a = s["loyal_artist"]
        out.append((
            "genre",
            f"Whose top songs this month are {s['loyal_n']} of {s['loyal_total']} {a}?",
            lambda x, a=a, n=s["loyal_n"]: x["loyal_artist"] == a and x["loyal_n"] == n,
            f"{name} is loyal: {s['loyal_n']} of their top {s['loyal_total']} tracks are {a}.",
        ))
    return out


def build_questions(profiles: dict[str, dict], names: dict[str, str], n: int = QUESTIONS_PER_GAME, rng: random.Random | None = None) -> list[Question]:
    rng = rng or random.Random()
    st = {pid: stats(p) for pid, p in profiles.items()}
    pools: dict[str, list[Question]] = {c: [] for c in CATEGORIES}
    for pid, s in st.items():
        for cat, text, holds, explain in _candidates(pid, names[pid], s, st):
            correct = [q for q, qs in st.items() if holds(qs)]
            if pid not in correct:
                continue
            # A question everyone gets right by default is no question.
            if len(correct) == len(st):
                continue
            pools[cat].append(Question(cat, text, pid, correct, explain))
    for pool in pools.values():
        rng.shuffle(pool)

    # Spread the spotlight: take from each category in turn, preferring people
    # who haven't been the subject yet, and keep categories in deck order.
    per_cat = {c: [] for c in CATEGORIES}
    seen_text: set[str] = set()
    subject_count: Counter = Counter()
    while sum(len(v) for v in per_cat.values()) < n and any(pools.values()):
        for cat in CATEGORIES:
            pool = pools[cat]
            if not pool or sum(len(v) for v in per_cat.values()) >= n:
                continue
            pool.sort(key=lambda q: subject_count[q.subject])
            q = pool.pop(0)
            if q.text in seen_text:
                continue
            seen_text.add(q.text)
            subject_count[q.subject] += 1
            per_cat[cat].append(q)
    return [q for c in CATEGORIES for q in per_cat[c]]


def awards(profiles: dict[str, dict], names: dict[str, str]) -> list[dict]:
    st = {pid: stats(p) for pid, p in profiles.items()}
    if not st:
        return []

    def best(key):
        return max(st, key=lambda pid: st[pid][key])

    cards = []
    pid = best("loyalty")
    s = st[pid]
    if s["loyal_artist"]:
        cards.append({"id": "loyal", "title": "Most Loyal Listener", "color": "red", "winner": names[pid],
                      "stat": f"{s['loyal_n']} of their top {s['loyal_total']} songs are {s['loyal_artist']}"})
    pid = best("switch")
    s = st[pid]
    line = (f"From {s['switch_from']} to {s['switch_to']}" if s["switch_from"] and s["switch_to"]
            else f"{round(s['switch'] * 100)}% new artists this month")
    cards.append({"id": "switch", "title": "Biggest Genre Switch", "color": "mustard", "winner": names[pid], "stat": line})
    pid = max(st, key=lambda p: st[p]["fan_plays"] / max(st[p]["recent_total"], 1))
    s = st[pid]
    if s["fan_artist"]:
        cards.append({"id": "superfan", "title": "Top 0.5% Listener", "color": "green", "winner": names[pid],
                      "stat": f"{s['fan_plays']} of their last {s['recent_total']} plays were {s['fan_artist']}"})
    pid = best("loop_count")
    s = st[pid]
    if s["loop_track"]:
        cards.append({"id": "looper", "title": "Biggest Song Looper", "color": "blue", "winner": names[pid],
                      "stat": f"“{s['loop_track']['name']}” {s['loop_count']} times in {s['recent_total']} plays"})
    return cards


@dataclass
class Player:
    id: str
    key: str
    name: str
    profile: dict
    source: str  # "spotify" | "sample"
    is_bot: bool = False
    score: int = 0
    joined_at: float = field(default_factory=time.time)


@dataclass
class Room:
    code: str
    players: dict[str, Player] = field(default_factory=dict)
    host_id: str | None = None
    phase: str = "lobby"  # lobby | question | reveal | report
    questions: list[Question] = field(default_factory=list)
    qi: int = 0
    started_at: float = 0.0
    answers: dict[str, tuple[str, float]] = field(default_factory=dict)
    bot_plan: dict[str, tuple[str, float]] = field(default_factory=dict)
    last_points: dict[str, int] = field(default_factory=dict)
    cards: list[dict] = field(default_factory=list)
    touched: float = field(default_factory=time.time)

    # --- membership -------------------------------------------------------
    def add_player(self, name: str, profile: dict, source: str, is_bot: bool = False) -> Player:
        if len(self.players) >= MAX_PLAYERS:
            raise ValueError("This room is full.")
        if self.phase != "lobby":
            raise ValueError("This game already started. Wait for the rematch.")
        name = _unique_name(name.strip()[:20] or "Player", {p.name for p in self.players.values()})
        p = Player(id=secrets.token_hex(4), key=secrets.token_urlsafe(16), name=name,
                   profile=profile, source=source, is_bot=is_bot)
        self.players[p.id] = p
        if self.host_id is None and not is_bot:
            self.host_id = p.id
        return p

    # --- flow -------------------------------------------------------------
    def start(self, rng: random.Random | None = None) -> None:
        if len(self.players) < 2:
            raise ValueError("Need at least 2 players.")
        self.questions = build_questions(
            {pid: p.profile for pid, p in self.players.items()},
            {pid: p.name for pid, p in self.players.items()},
            rng=rng,
        )
        if not self.questions:
            raise ValueError("Not enough listening history to build questions yet.")
        for p in self.players.values():
            p.score = 0
        self.qi = 0
        self._open_question()

    def _open_question(self) -> None:
        self.phase = "question"
        self.started_at = time.time()
        self.answers = {}
        self.last_points = {}
        q = self.questions[self.qi]
        ids = list(self.players)
        self.bot_plan = {}
        for pid, p in self.players.items():
            if not p.is_bot or pid == q.subject:
                continue
            # Bots are right a bit over half the time, never instantly.
            pick = rng_choice_weighted(q.correct, ids, 0.55)
            self.bot_plan[pid] = (pick, self.started_at + random.uniform(2.5, 9))

    def tick(self, now: float | None = None) -> None:
        now = now or time.time()
        if self.phase != "question":
            return
        for pid, (pick, at) in list(self.bot_plan.items()):
            if now >= at and pid not in self.answers:
                self.answers[pid] = (pick, at)
        subject = self.questions[self.qi].subject
        everyone_in = all(pid in self.answers or pid == subject for pid in self.players)
        if everyone_in or now - self.started_at >= QUESTION_SECONDS:
            self._reveal()

    def answer(self, pid: str, choice: str) -> None:
        self.tick()
        if self.phase != "question":
            raise ValueError("Too late, answers are locked.")
        if choice not in self.players:
            raise ValueError("Pick someone in the room.")
        if pid in self.answers:
            raise ValueError("You already answered.")
        if pid == self.questions[self.qi].subject:
            raise ValueError("This one's about you. Sit tight.")
        self.answers[pid] = (choice, time.time())
        self.tick()

    def _reveal(self) -> None:
        q = self.questions[self.qi]
        points: dict[str, int] = {}
        right = 0
        for pid, (choice, at) in self.answers.items():
            if pid == q.subject:
                continue
            if choice in q.correct:
                right += 1
                left = max(0.0, QUESTION_SECONDS - (at - self.started_at))
                points[pid] = BASE_POINTS + round(SPEED_POINTS * left / QUESTION_SECONDS)
        if right:
            points[q.subject] = points.get(q.subject, 0) + KNOWN_POINTS * right
        for pid, pts in points.items():
            if pid in self.players:
                self.players[pid].score += pts
        self.last_points = points
        self.phase = "reveal"

    def next(self) -> None:
        self.tick()
        if self.phase == "question":
            self._reveal()
            return
        if self.phase != "reveal":
            return
        if self.qi + 1 < len(self.questions):
            self.qi += 1
            self._open_question()
        else:
            self.cards = awards({pid: p.profile for pid, p in self.players.items()},
                                {pid: p.name for pid, p in self.players.items()})
            self.phase = "report"

    def rematch(self) -> None:
        self.phase = "lobby"
        self.questions = []
        self.answers = {}
        self.cards = []

    # --- what one player is allowed to see --------------------------------
    def view(self, me: str | None) -> dict:
        self.tick()
        q = self.questions[self.qi] if self.phase in ("question", "reveal") else None
        out = {
            "code": self.code,
            "phase": self.phase,
            "host_id": self.host_id,
            "me": me,
            "players": [
                {"id": p.id, "name": p.name, "score": p.score, "source": p.source, "bot": p.is_bot,
                 "answered": p.id in self.answers}
                for p in sorted(self.players.values(), key=lambda p: p.joined_at)
            ],
        }
        if q:
            out["question"] = {
                "index": self.qi, "total": len(self.questions), "category": q.category, "text": q.text,
                "seconds": QUESTION_SECONDS,
                "time_left": max(0, round(QUESTION_SECONDS - (time.time() - self.started_at))),
                "about_me": me == q.subject,
                "my_answer": self.answers.get(me, (None,))[0] if me else None,
            }
        if self.phase == "reveal" and q:
            out["reveal"] = {
                "correct": q.correct, "subject": q.subject, "explain": q.explain,
                "picks": {pid: c for pid, (c, _) in self.answers.items()},
                "points": self.last_points,
            }
        if self.phase == "report":
            out["cards"] = self.cards
        return out


def rng_choice_weighted(correct: list[str], ids: list[str], p_right: float) -> str:
    if random.random() < p_right:
        return random.choice(correct)
    wrong = [i for i in ids if i not in correct]
    return random.choice(wrong or correct)


def _unique_name(name: str, taken: set[str]) -> str:
    if name not in taken:
        return name
    n = 2
    while f"{name} {n}" in taken:
        n += 1
    return f"{name} {n}"


def new_code(existing: set[str]) -> str:
    # No I or O: they read as 1 and 0 when someone shouts a code across a room.
    alphabet = "".join(c for c in string.ascii_uppercase if c not in "IO")
    while True:
        code = "".join(secrets.choice(alphabet) for _ in range(4))
        if code not in existing:
            return code
