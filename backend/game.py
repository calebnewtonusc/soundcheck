"""Rooms, question generation, scoring and the end-of-game cards.

A profile is the slice of a player's Spotify history the game needs: top
tracks and artists over the last 4 weeks (short) and the last year (long),
plus their last 50 plays with the local hour each was played. Tokens never
reach this module.

Two question shapes:
  who   - options are the players ("Whose #1 song this month is Espresso?")
  pick  - options are songs, artists or genres about one player
          ("Which of these is actually in Maia's top 5 this month?")
"""

from __future__ import annotations

import random
import re
import secrets
import string
import threading
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Callable

QUESTION_SECONDS = 20
LENGTHS = (5, 8, 12)
DEFAULT_LENGTH = 8
MAX_PLAYERS = 20
# Points: 100 for a right answer plus up to 50 for speed. Whoever a question
# is about gets 50 for every friend who got them right, so being known pays.
BASE_POINTS = 100
SPEED_POINTS = 50
KNOWN_POINTS = 50
# Late night is midnight to 5am in the player's own timezone.
LATE_HOURS = range(0, 5)
CATEGORIES = ["songs", "artists", "genre"]
MODES = ("classic", "wrapped", "roadtrip", "decades", "genres")
# Road trips get longer to answer: someone is driving, phones get passed.
MODE_SECONDS = {"roadtrip": 30}
REACTIONS = ("CALLED IT", "NO WAY", "SUS", "RESPECT")
# Enough memory for about two months of weekly 12-question games.
MAX_ASKED = 120
MAX_HISTORY = 50
TEAMS = ("red", "blue")


def _key(t: dict) -> tuple[str, str]:
    return (t["name"], t["artist"])


def stats(profile: dict) -> dict:
    """Derive the facts questions and cards are built from."""
    short = profile.get("top_tracks_short") or []
    long_ = profile.get("top_tracks_long") or []
    recent = profile.get("recent") or []
    artists_long = profile.get("top_artists_long") or []
    artists_short = profile.get("top_artists_short") or []

    loop_track, loop_count = None, 0
    if recent:
        k, loop_count = Counter(_key(t) for t in recent).most_common(1)[0]
        loop_track = next(t for t in recent if _key(t) == k)

    genres: Counter = Counter()
    for rank, artist in enumerate(artists_long[:20]):
        for g in artist.get("genres") or []:
            genres[g] += 20 - rank
    top_genre = genres.most_common(1)[0][0] if genres else None

    by_artist = Counter(t["artist"] for t in short)
    loyal_artist, loyal_n = by_artist.most_common(1)[0] if by_artist else (None, 0)

    s_names = [a["name"] for a in artists_short[:10]]
    l_names = [a["name"] for a in artists_long[:10]]
    union = set(s_names) | set(l_names)
    switch = 1 - len(set(s_names) & set(l_names)) / len(union) if union else 0.0

    top_artist = artists_long[0]["name"] if artists_long else None
    fan_plays = sum(1 for t in recent if t["artist"] == top_artist) if top_artist else 0

    years = [t["year"] for t in short + long_ if t.get("year")]
    dated = sorted((t for t in short + long_ if t.get("year")), key=lambda t: t["year"])
    late = [t for t in recent if t.get("hour") is not None and t["hour"] in LATE_HOURS]
    short_keys = {_key(t) for t in short[:10]}
    stayers = [t for t in long_[:10] if _key(t) in short_keys]

    # Quick picks are one self-reported list, not two time windows, so
    # anything that compares this month with the year is left out.
    picked = bool(profile.get("self_reported"))
    return {
        "top_song": short[0] if short else None,
        "song_of_year": long_[0] if long_ and not picked else None,
        "top5": short[:5],
        "track_keys": {_key(t) for t in short + long_},
        "recent_keys": {_key(t) for t in recent},
        "last_played": recent[0] if recent else None,
        "stayer": stayers[0] if stayers and not picked else None,
        "top_artist_year": artists_long[0] if artists_long and not picked else None,
        "top_artist_month": artists_short[0] if artists_short else None,
        "top_genre": top_genre,
        "genres": set(genres),
        "loop_track": loop_track,
        "loop_count": loop_count,
        "loyal_artist": loyal_artist,
        "loyal_n": loyal_n,
        "loyal_total": len(short),
        "loyalty": loyal_n / len(short) if short else 0.0,
        "switch": switch,
        "switch_from": next((n for n in l_names if n not in s_names), None),
        "switch_to": next((n for n in s_names if n not in l_names), None),
        "fan_artist": top_artist,
        "fan_plays": fan_plays,
        "recent_total": len(recent),
        "late_plays": len(late),
        "late_track": late[0] if late else None,
        "artist_names": {a["name"] for a in artists_long[:20]} | {a["name"] for a in artists_short[:20]},
        "top10_long": l_names,
        "artists_by_name": {a["name"]: a for a in artists_long + artists_short},
        "picked": picked,
        "avg_year": sum(years) / len(years) if years else None,
        "oldest": dated[0] if dated else None,
        "decades": {y // 10 * 10 for y in years},
        "dated": dated,
        "recent_artists": Counter(t["artist"] for t in recent),
        "rank_long": {a["name"]: i for i, a in enumerate(artists_long[:20])},
        "rank_short": {a["name"]: i for i, a in enumerate(artists_short[:20])},
    }


@dataclass
class Question:
    category: str
    kind: str  # "who" | "pick"
    text: str
    subjects: list[str]  # players the question is about; they sit it out
    correct: list[str]  # option ids (player ids for "who")
    explain: str
    image: str | None = None  # the album or artist the question is about
    options: list[dict] = field(default_factory=list)  # for "pick": {id, label, sub, image}
    tags: list[str] = field(default_factory=list)  # themed modes this question suits


def _track_label(t: dict) -> dict:
    return {"label": t["name"], "sub": t["artist"], "image": t.get("image")}


def _artist_label(a: dict) -> dict:
    return {"label": a["name"], "sub": "", "image": a.get("image")}


def _pick(options_right: list[dict], decoys: list[dict], rng: random.Random, n: int = 4) -> tuple[list[dict], list[str]] | None:
    """Mix one right option with decoys. None when there aren't enough decoys."""
    seen = {o["label"] for o in options_right}
    uniq = []
    for d in decoys:
        if d["label"] not in seen:
            seen.add(d["label"])
            uniq.append(d)
    if len(uniq) < n - len(options_right):
        return None
    rng.shuffle(uniq)
    opts = options_right + uniq[: n - len(options_right)]
    rng.shuffle(opts)
    out, correct = [], []
    right_labels = {o["label"] for o in options_right}
    for i, o in enumerate(opts):
        out.append({"id": f"o{i}", **o})
        if o["label"] in right_labels:
            correct.append(f"o{i}")
    return out, correct


Holds = Callable[[dict], bool]


def _who(pid: str, name: str, s: dict, st: dict[str, dict]) -> list[tuple[str, str, Holds, str, str | None]]:
    """Each candidate: (category, text, holds(stats), explanation, image)."""
    out: list[tuple[str, str, Holds, str, str | None]] = []
    q = "“"
    e = "”"
    if s["top_song"]:
        t = s["top_song"]
        out.append(("songs", f"Whose #1 song this month is {q}{t['name']}{e} by {t['artist']}?",
                    lambda x, t=t: x["top_song"] is not None and _key(x["top_song"]) == _key(t),
                    f"{name}'s most played track of the last 4 weeks.", t.get("image")))
    if s["song_of_year"] and (not s["top_song"] or _key(s["song_of_year"]) != _key(s["top_song"])):
        t = s["song_of_year"]
        out.append(("songs", f"Whose most played song of the past year is {q}{t['name']}{e}?",
                    lambda x, t=t: x["song_of_year"] is not None and _key(x["song_of_year"]) == _key(t),
                    f"{t['name']} by {t['artist']} is {name}'s #1 over the last 12 months.", t.get("image")))
    if s["loop_track"] and s["loop_count"] >= 3:
        t, n = s["loop_track"], s["loop_count"]
        out.append(("songs", f"Who played {q}{t['name']}{e} {n} times in their last {s['recent_total']} plays?",
                    lambda x, t=t, n=n: x["loop_track"] is not None and _key(x["loop_track"]) == _key(t) and x["loop_count"] == n,
                    f"{name} has it on repeat: {n} of their last {s['recent_total']} plays.", t.get("image")))
    if s["stayer"] and s["top_song"] and _key(s["stayer"]) != _key(s["top_song"]):
        t = s["stayer"]
        out.append(("songs", f"Who still has {q}{t['name']}{e} in their top 10, a whole year later?",
                    lambda x, t=t: _key(t) in x["track_keys"],
                    f"{t['name']} is in {name}'s top 10 for the month and for the year.", t.get("image")))
    if s["top_artist_year"]:
        a = s["top_artist_year"]
        out.append(("artists", f"Who's had {a['name']} as their #1 artist all year?",
                    lambda x, a=a: x["top_artist_year"] is not None and x["top_artist_year"]["name"] == a["name"],
                    f"{a['name']} tops {name}'s last 12 months.", a.get("image")))
    others = [o for opid, o in st.items() if opid != pid]
    unique = [a for a in s["top10_long"] if all(a not in o["artist_names"] for o in others)]
    if unique:
        a = s["artists_by_name"][unique[0]]
        out.append(("artists", f"Who's the only one here with {a['name']} in their top artists?",
                    lambda x, a=a: a["name"] in x["top10_long"],
                    f"Nobody else in the room has {a['name']} anywhere in their top 20.", a.get("image")))
    m = s["top_artist_month"]
    if m and m["name"] not in s["top10_long"] and not s["picked"]:
        out.append(("artists", f"Who's in a brand new {m['name']} phase?",
                    lambda x, m=m: x["top_artist_month"] is not None and x["top_artist_month"]["name"] == m["name"] and m["name"] not in x["top10_long"],
                    f"{m['name']} is {name}'s #1 this month and wasn't in their top 10 for the year.", m.get("image")))
    if s["top_genre"]:
        g = s["top_genre"]
        out.append(("genre", f"Whose top genre is {g}?", lambda x, g=g: x["top_genre"] == g,
                    f"{g} runs through more of {name}'s top artists than anything else.", None))
    if s["loyal_n"] >= 3:
        a, n, tot = s["loyal_artist"], s["loyal_n"], s["loyal_total"]
        img = (s["artists_by_name"].get(a) or {}).get("image")
        out.append(("genre", f"Whose top {tot} songs this month include {n} by {a}?",
                    lambda x, a=a, n=n: x["loyal_artist"] == a and x["loyal_n"] == n,
                    f"{name} is loyal: {n} of their top {tot} tracks are {a}.", img))
    if s["late_track"] and s["late_plays"] >= 2:
        t, n = s["late_track"], s["late_plays"]
        hour = t["hour"] or 12
        out.append(("genre", f"Who was playing {q}{t['name']}{e} at {hour} AM?",
                    lambda x, t=t: x["late_track"] is not None and _key(x["late_track"]) == _key(t),
                    f"{name} is a night owl: {n} of their last {s['recent_total']} plays came between midnight and 5 AM.", t.get("image")))
    return out


def _picks(pid: str, name: str, s: dict, st: dict[str, dict], rng: random.Random) -> list[Question]:
    out: list[Question] = []
    others = [o for opid, o in st.items() if opid != pid]
    if s["top5"]:
        right = s["top5"][rng.randrange(len(s["top5"]))]
        decoys = [_track_label(t) for o in others for t in (o["top5"] + [o["top_song"], o["song_of_year"]]) if t and _key(t) not in s["track_keys"]]
        mixed = _pick([_track_label(right)], decoys, rng)
        if mixed:
            out.append(Question("songs", "pick", f"Which of these is actually in {name}'s top 5 this month?", [pid], mixed[1],
                                f"{right['name']} by {right['artist']} sits in {name}'s top 5. The rest belong to the room.", None, mixed[0]))
    if s["last_played"]:
        lp = s["last_played"]
        decoys = [_track_label(o["last_played"]) for o in others if o["last_played"] and _key(o["last_played"]) not in s["recent_keys"]]
        decoys += [_track_label(t) for o in others for t in o["top5"] if _key(t) not in s["recent_keys"]]
        mixed = _pick([_track_label(lp)], decoys, rng)
        if mixed:
            out.append(Question("songs", "pick", f"What's the last song {name} played?", [pid], mixed[1],
                                f"{name} last played {lp['name']} by {lp['artist']}.", None, mixed[0]))
    m = s["top_artist_month"]
    if m:
        decoys = [_artist_label(o["top_artist_month"]) for o in others if o["top_artist_month"] and o["top_artist_month"]["name"] not in s["artist_names"]]
        decoys += [_artist_label(a) for o in others for a in o["artists_by_name"].values() if a["name"] not in s["artist_names"]]
        mixed = _pick([_artist_label(m)], decoys, rng)
        if mixed:
            out.append(Question("artists", "pick", f"Who's {name}'s #1 artist this month?", [pid], mixed[1],
                                f"{m['name']} leads {name}'s last 4 weeks.", None, mixed[0]))
    if s["top_genre"] and others:
        g = s["top_genre"]
        decoys = [{"label": o["top_genre"], "sub": "", "image": None} for o in others if o["top_genre"] and o["top_genre"] not in s["genres"]]
        decoys += [{"label": x, "sub": "", "image": None} for o in others for x in o["genres"] if x not in s["genres"]]
        mixed = _pick([{"label": g, "sub": "", "image": None}], decoys, rng)
        if mixed:
            out.append(Question("genre", "pick", f"What's {name}'s top genre?", [pid], mixed[1],
                                f"{g} runs through more of {name}'s top artists than anything else.", None, mixed[0]))
    return out


def _pairs(st: dict[str, dict], names: dict[str, str], rng: random.Random) -> list[Question]:
    """Shared-taste questions: the artist two friends both rate."""
    out = []
    ids = list(st)
    rng.shuffle(ids)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            shared = [n for n in st[a]["top10_long"] if n in st[b]["artist_names"]]
            if not shared:
                continue
            art = st[a]["artists_by_name"][shared[0]]
            both = st[a]["artist_names"] | st[b]["artist_names"]
            decoys = [_artist_label(x) for pid in ids if pid not in (a, b) for x in st[pid]["artists_by_name"].values() if x["name"] not in both]
            mixed = _pick([_artist_label(art)], decoys, rng)
            if mixed:
                out.append(Question("artists", "pick", f"Which artist do {names[a]} and {names[b]} both have in their top artists?",
                                    [a, b], mixed[1], f"{art['name']} is the overlap. Start the group chat.", None, mixed[0]))
            if len(out) >= 2:
                return out
    return out


def _fans(st: dict[str, dict], names: dict[str, str], rng: random.Random) -> list[Question]:
    """The deck's headline question: who's the biggest fan of an artist two
    or more people share. Spotify doesn't publish listener percentiles, so
    the room ranks itself: rank in each top list plus share of recent plays."""
    def score(s: dict, a: str) -> float:
        sc = 0.0
        if a in s["rank_long"]:
            sc += 20 - s["rank_long"][a]
        if a in s["rank_short"]:
            sc += 10 - min(s["rank_short"][a], 10)
        sc += 3 * s["recent_artists"].get(a, 0)
        return sc

    shared = Counter(a for s in st.values() for a in s["artist_names"])
    out = []
    for artist, n in sorted(shared.items(), key=lambda kv: (-kv[1], kv[0])):
        if n < 2:
            break
        ranked = sorted(st, key=lambda pid: -score(st[pid], artist))
        top, second = ranked[0], ranked[1]
        if score(st[top], artist) < score(st[second], artist) + 4:
            continue  # too close to call, so not a fair question
        s = st[top]
        art = s["artists_by_name"][artist]
        plays = s["recent_artists"].get(artist, 0)
        rank = s["rank_long"].get(artist, s["rank_short"].get(artist, 0)) + 1
        out.append(Question("artists", "who", f"Who's the biggest {artist} fan in the room?", [top], [top],
                            f"{artist} sits at #{rank} in {names[top]}'s top artists"
                            + (f", plus {plays} of their last {s['recent_total']} plays." if plays else ", higher than anyone else here."),
                            art.get("image"), tags=["wrapped", "genres", "classic"]))
        if len(out) >= 3:
            break
    rng.shuffle(out)
    return out


def _eras(st: dict[str, dict], names: dict[str, str], rng: random.Random) -> list[Question]:
    out: list[Question] = []
    dated = {pid: s for pid, s in st.items() if s["avg_year"]}
    if len(dated) >= 2:
        ranked = sorted(dated, key=lambda pid: dated[pid]["avg_year"])
        old, nxt = ranked[0], ranked[1]
        if dated[nxt]["avg_year"] - dated[old]["avg_year"] >= 2:
            s = dated[old]
            out.append(Question("genre", "who", "Whose top songs are the most throwback?", [old], [old],
                                f"{names[old]}'s top songs came out in {round(s['avg_year'])} on average. Oldest: {s['oldest']['name']} ({s['oldest']['year']}).",
                                s["oldest"].get("image"), tags=["decades", "classic"]))
    if len(dated) >= 2:
        newest = sorted(dated, key=lambda pid: -dated[pid]["avg_year"])
        if dated[newest[0]]["avg_year"] - dated[newest[1]]["avg_year"] >= 0.8:
            s = dated[newest[0]]
            out.append(Question("genre", "who", "Whose top songs are the newest?", [newest[0]], [newest[0]],
                                f"{names[newest[0]]}'s top songs came out in {round(s['avg_year'])} on average, the newest in the room.",
                                None, tags=["decades"]))
        oldest_any = min((s["oldest"]["year"], pid) for pid, s in dated.items())
        holders = [pid for pid, s in dated.items() if s["oldest"]["year"] == oldest_any[0]]
        if len(holders) < len(st):
            t = dated[oldest_any[1]]["oldest"]
            out.append(Question("genre", "who", "Who has the oldest song in the room in their top songs?", [oldest_any[1]], holders,
                                f"{t['name']} by {t['artist']}, from {t['year']}, beats every other top song here.", t.get("image"), tags=["decades"]))
    for pid, s in dated.items():
        t = s["dated"][len(s["dated"]) // 2]
        decoys = sorted({t["year"] + d for d in (-7, -4, -2, 2, 3, 6)} - {t["year"]}, key=lambda y: rng.random())[:3]
        years = [t["year"]] + decoys
        rng.shuffle(years)
        options = [{"id": f"o{i}", "label": str(y), "sub": "", "image": None} for i, y in enumerate(years)]
        out.append(Question("genre", "pick", f"What year did \u201c{t['name']}\u201d by {t['artist']} come out?", [pid], [o["id"] for o in options if o["label"] == str(t["year"])],
                            f"{t['year']}. It's in {names[pid]}'s top songs.", None, options, tags=["decades"]))
        counts = Counter(x["year"] // 10 * 10 for x in s["dated"])
        top_decade, n_top = counts.most_common(1)[0]
        if n_top / len(s["dated"]) >= 0.5:
            pool = sorted({1970, 1980, 1990, 2000, 2010, 2020} - {top_decade}, key=lambda y: rng.random())[:3] + [top_decade]
            rng.shuffle(pool)
            options = [{"id": f"o{i}", "label": f"{y}s", "sub": "", "image": None} for i, y in enumerate(pool)]
            out.append(Question("genre", "pick", f"Which decade is most of {names[pid]}'s top songs from?", [pid],
                                [o["id"] for o in options if o["label"] == f"{top_decade}s"],
                                f"{n_top} of {names[pid]}'s {len(s['dated'])} top songs came out in the {top_decade}s.", None, options, tags=["decades"]))
    for pid, s in dated.items():
        decade = min(s["decades"])
        holders = [p for p, x in dated.items() if decade in x["decades"]]
        if 0 < len(holders) < len(st) and decade < 2020:
            t = next(t for t in s["dated"] if t["year"] // 10 * 10 == decade)
            out.append(Question("genre", "who", f"Who has a song from the {decade}s in their top songs?", [pid], holders,
                                f"{t['name']} by {t['artist']} came out in {t['year']}.", t.get("image"), tags=["decades"]))
        uniq = []
        for t in s["dated"]:
            if t["year"] not in {u["year"] for u in uniq} and _key(t) not in {_key(u) for u in uniq}:
                uniq.append(t)
        if len(uniq) >= 4:
            four = [uniq[0]] + rng.sample(uniq[1:], 3)
            oldest = four[0]
            opts = [_track_label(t) for t in four]
            rng.shuffle(opts)
            options = [{"id": f"o{i}", **o} for i, o in enumerate(opts)]
            correct = [o["id"] for o in options if o["label"] == oldest["name"]]
            out.append(Question("genre", "pick", f"Which of {names[pid]}'s top songs is the oldest?", [pid], correct,
                                f"{oldest['name']} by {oldest['artist']} came out in {oldest['year']}.", None, options, tags=["decades"]))
    rng.shuffle(out)
    return out


ROADTRIP_HINTS = ("this month", "last song", "times in their last", " AM?", "brand new", "top 5")
WRAPPED_HINTS = ("past year", "all year", "whole year", "only one here", "top genre", "both have", "biggest")
GENRE_HINTS = ("genre", "only one here", "both have", "biggest", "loyal")


def _auto_tags(q: Question) -> list[str]:
    tags = set(q.tags) | {"classic"}
    if any(h in q.text for h in ROADTRIP_HINTS):
        tags.add("roadtrip")
    if any(h in q.text for h in WRAPPED_HINTS):
        tags.add("wrapped")
    if any(h in q.text for h in GENRE_HINTS[:5]) or "songs this month include" in q.text:
        tags.add("genres")
    return sorted(tags)


def _template(q: Question, names: dict[str, str]) -> str:
    """Questions built from the same sentence frame, so a game can cap them."""
    text = re.sub("\u201c[^\u201d]*\u201d", "T", q.text)
    for n in names.values():
        text = text.replace(n, "X")
    return " ".join(text.split()[:4]) + "|" + q.kind


MAX_PER_TEMPLATE = 2


def build_questions(profiles: dict[str, dict], names: dict[str, str], n: int = DEFAULT_LENGTH, rng: random.Random | None = None, mode: str = "classic", skip: set[str] | None = None) -> list[Question]:
    rng = rng or random.Random()
    st = {pid: stats(p) for pid, p in profiles.items()}
    pools: dict[str, list[Question]] = {c: [] for c in CATEGORIES}
    for pid, s in st.items():
        for cat, text, holds, explain, image in _who(pid, names[pid], s, st):
            correct = [q for q, qs in st.items() if holds(qs)]
            if pid not in correct or len(correct) == len(st):
                continue
            pools[cat].append(Question(cat, "who", text, [pid], correct, explain, image))
        for q in _picks(pid, names[pid], s, st, rng):
            pools[q.category].append(q)
    if len(st) >= 3:
        for q in _pairs(st, names, rng):
            pools[q.category].append(q)
    for q in _fans(st, names, rng) + _eras(st, names, rng):
        pools[q.category].append(q)
    for pool in pools.values():
        for q in pool:
            q.tags = _auto_tags(q)
        rng.shuffle(pool)

    # Spread the spotlight: take categories in turn, prefer whoever has been
    # asked about least, and don't run the same question shape twice in a row.
    chosen: dict[str, list[Question]] = {c: [] for c in CATEGORIES}
    subject_count: Counter = Counter()
    # Texts this group has already seen: a weekly group shouldn't get last
    # week's questions back while fresh ones exist.
    seen: set[str] = set(skip or ())
    last_kind = ""
    total = 0
    per_template: Counter = Counter()
    if mode != "classic":
        # Themed modes fill from their own questions first, whatever the
        # category, then top up from everything else.
        themed = sorted((q for c in CATEGORIES for q in pools[c] if mode in q.tags), key=lambda q: rng.random())
        while themed and total < n:
            themed.sort(key=lambda q: sum(subject_count[s] for s in q.subjects))
            q = themed.pop(0)
            if q.text in seen or per_template[_template(q, names)] >= MAX_PER_TEMPLATE:
                continue
            per_template[_template(q, names)] += 1
            pools[q.category].remove(q)
            seen.add(q.text)
            for x in q.subjects:
                subject_count[x] += 1
            chosen[q.category].append(q)
            total += 1
    while total < n and any(pools.values()):
        progressed = False
        for cat in CATEGORIES:
            pool = pools[cat]
            if not pool or total >= n:
                continue
            # The mode's own questions first, then spread the spotlight.
            pool.sort(key=lambda q: (mode not in q.tags, sum(subject_count[s] for s in q.subjects), q.kind == last_kind))
            q = pool.pop(0)
            if q.text in seen or per_template[_template(q, names)] >= MAX_PER_TEMPLATE:
                continue
            per_template[_template(q, names)] += 1
            seen.add(q.text)
            for s in q.subjects:
                subject_count[s] += 1
            last_kind = q.kind
            chosen[cat].append(q)
            total += 1
            progressed = True
        if not progressed and not any(pools.values()):
            break
    return [q for c in CATEGORIES for q in chosen[c]]


def awards(profiles: dict[str, dict], names: dict[str, str]) -> list[dict]:
    st = {pid: stats(p) for pid, p in profiles.items()}
    if not st:
        return []

    def best(fn):
        return max(st, key=fn)

    cards = []
    pid = best(lambda p: st[p]["loyalty"])
    s = st[pid]
    if s["loyal_artist"]:
        cards.append({"id": "loyal", "title": "Most Loyal Listener", "color": "red", "winner": names[pid], "pid": pid,
                      "stat": f"{s['loyal_n']} of their top {s['loyal_total']} songs are {s['loyal_artist']}"})
    pid = best(lambda p: st[p]["switch"])
    s = st[pid]
    line = (f"From {s['switch_from']} to {s['switch_to']}" if s["switch_from"] and s["switch_to"]
            else f"{round(s['switch'] * 100)}% new artists this month")
    cards.append({"id": "switch", "title": "Biggest Genre Switch", "color": "mustard", "winner": names[pid], "pid": pid, "stat": line})
    pid = best(lambda p: st[p]["fan_plays"] / max(st[p]["recent_total"], 1))
    s = st[pid]
    if s["fan_artist"]:
        cards.append({"id": "superfan", "title": "Top 0.5% Listener", "color": "green", "winner": names[pid], "pid": pid,
                      "stat": f"{s['fan_plays']} of their last {s['recent_total']} plays were {s['fan_artist']}"})
    pid = best(lambda p: st[p]["loop_count"])
    s = st[pid]
    if s["loop_track"]:
        cards.append({"id": "looper", "title": "Biggest Song Looper", "color": "blue", "winner": names[pid], "pid": pid,
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
    avatar: str | None = None
    score: int = 0
    streak: int = 0
    right: int = 0
    team: str | None = None
    joined_at: float = field(default_factory=time.time)


def locked(fn):
    def wrapper(self, *a, **kw):
        with self.lock:
            return fn(self, *a, **kw)
    wrapper.__name__ = fn.__name__
    return wrapper


@dataclass
class Room:
    code: str
    players: dict[str, Player] = field(default_factory=dict)
    host_id: str | None = None
    phase: str = "lobby"  # lobby | question | reveal | report
    length: int = DEFAULT_LENGTH
    mode: str = "classic"
    teams: bool = False
    ai: bool = False
    seconds: int = QUESTION_SECONDS
    reactions: dict[str, list] = field(default_factory=dict)  # question index -> [[pid, label], ...]
    history: list[dict] = field(default_factory=list)  # one entry per finished game
    asked: list[str] = field(default_factory=list)  # every question text this room has played
    questions: list[Question] = field(default_factory=list)
    qi: int = 0
    started_at: float = 0.0
    answers: dict[str, list] = field(default_factory=dict)  # pid -> [choice, at]
    bot_plan: dict[str, list] = field(default_factory=dict)
    last_points: dict[str, int] = field(default_factory=dict)
    cards: list[dict] = field(default_factory=list)
    touched: float = field(default_factory=time.time)
    version: int = 0
    lock: threading.RLock = field(default_factory=threading.RLock, repr=False, compare=False)

    # --- persistence ------------------------------------------------------
    def to_dict(self) -> dict:
        with self.lock:
            d = {f: getattr(self, f) for f in self.__dataclass_fields__ if f != "lock"}
            d["players"] = {pid: asdict(p) for pid, p in self.players.items()}
            d["questions"] = [asdict(q) for q in self.questions]
            return d

    @classmethod
    def from_dict(cls, d: dict) -> Room:
        d = dict(d)
        d["players"] = {pid: Player(**p) for pid, p in d.get("players", {}).items()}
        d["questions"] = [Question(**q) for q in d.get("questions", [])]
        d.pop("lock", None)
        return cls(**d)

    # --- membership -------------------------------------------------------
    @locked
    def add_player(self, name: str, profile: dict, source: str, is_bot: bool = False, avatar: str | None = None) -> Player:
        if len(self.players) >= MAX_PLAYERS:
            raise ValueError("This room is full.")
        if self.phase != "lobby":
            raise ValueError("This game already started. Wait for the rematch.")
        name = _unique_name(name.strip()[:20] or "Player", {p.name for p in self.players.values()})
        p = Player(id=secrets.token_hex(4), key=secrets.token_urlsafe(16), name=name,
                   profile=profile, source=source, is_bot=is_bot, avatar=avatar)
        self.players[p.id] = p
        if self.teams:
            counts = Counter(x.team for x in self.players.values() if x.team)
            p.team = min(TEAMS, key=lambda t: counts[t])
        if self.host_id is None and not is_bot:
            self.host_id = p.id
        self.version += 1
        return p

    @locked
    def remove_player(self, pid: str) -> None:
        if self.phase != "lobby" or pid not in self.players:
            raise ValueError("Players can only leave from the lobby.")
        self.players.pop(pid)
        if self.host_id == pid:
            humans = [p for p in self.players.values() if not p.is_bot]
            self.host_id = humans[0].id if humans else None
        self.version += 1

    @locked
    def settings(self, length: int | None = None, mode: str | None = None, teams: bool | None = None, ai: bool | None = None) -> None:
        if self.phase != "lobby":
            raise ValueError("Change settings between games.")
        if length is not None:
            if length not in LENGTHS:
                raise ValueError("Pick 5, 8 or 12 questions.")
            self.length = length
        if mode is not None:
            if mode not in MODES:
                raise ValueError("Unknown mode.")
            self.mode = mode
        if teams is not None:
            self.teams = teams
            if teams:
                self._split_teams()
        if ai is not None:
            self.ai = ai
        self.version += 1

    def _split_teams(self, shuffle: bool = False) -> None:
        ids = sorted(self.players, key=lambda pid: self.players[pid].joined_at)
        if shuffle:
            random.shuffle(ids)
        for i, pid in enumerate(ids):
            self.players[pid].team = TEAMS[i % 2]

    @locked
    def shuffle_teams(self) -> None:
        if self.phase != "lobby" or not self.teams:
            raise ValueError("Turn on team mode first.")
        self._split_teams(shuffle=True)
        self.version += 1

    @locked
    def react(self, pid: str, label: str) -> None:
        if self.phase != "reveal":
            raise ValueError("Reactions open when the answer shows.")
        if label not in REACTIONS:
            raise ValueError("Unknown reaction.")
        mine = self.reactions.setdefault(str(self.qi), [])
        entry = [pid, label]
        if entry in mine:
            mine.remove(entry)
        else:
            mine.append(entry)
        self.version += 1

    # --- flow -------------------------------------------------------------
    @locked
    def prepare(self, rng: random.Random | None = None) -> list[Question]:
        """Write the questions without starting, so wording can be polished first."""
        if self.phase != "lobby":
            raise ValueError("The game already started.")
        if len(self.players) < 2:
            raise ValueError("Need at least 2 players.")
        if self.teams and len({p.team for p in self.players.values()}) < 2:
            self._split_teams()
        qs = build_questions(
            {pid: p.profile for pid, p in self.players.items()},
            {pid: p.name for pid, p in self.players.items()},
            n=self.length, rng=rng, mode=self.mode, skip=set(self.asked),
        )
        if len(qs) < self.length:
            # Out of fresh questions for this group: allow repeats again.
            qs = build_questions(
                {pid: p.profile for pid, p in self.players.items()},
                {pid: p.name for pid, p in self.players.items()},
                n=self.length, rng=rng, mode=self.mode,
            )
        if not qs:
            raise ValueError("Not enough listening history to build questions yet.")
        return qs

    @locked
    def begin(self, questions: list[Question]) -> None:
        if self.phase != "lobby":
            raise ValueError("The game already started.")
        self.questions = questions
        self.asked = (self.asked + [q.text for q in questions])[-MAX_ASKED:]
        self.seconds = MODE_SECONDS.get(self.mode, QUESTION_SECONDS)
        self.reactions = {}
        for p in self.players.values():
            p.score = p.streak = p.right = 0
        self.qi = 0
        self._open_question()

    def start(self, rng: random.Random | None = None) -> None:
        self.begin(self.prepare(rng))

    def _option_ids(self, q: Question) -> list[str]:
        return list(self.players) if q.kind == "who" else [o["id"] for o in q.options]

    def _open_question(self) -> None:
        self.phase = "question"
        self.started_at = time.time()
        self.answers = {}
        self.last_points = {}
        q = self.questions[self.qi]
        ids = self._option_ids(q)
        self.bot_plan = {}
        for pid, p in self.players.items():
            if p.is_bot and pid not in q.subjects:
                # Bots are right a bit over half the time, never instantly.
                pick = random.choice(q.correct) if random.random() < 0.55 else random.choice([i for i in ids if i not in q.correct] or q.correct)
                self.bot_plan[pid] = [pick, self.started_at + random.uniform(2.5, min(9, self.seconds - 2))]
        self.version += 1

    def _tick(self, now: float | None = None) -> None:
        now = now or time.time()
        if self.phase != "question":
            return
        changed = False
        for pid, (pick, at) in list(self.bot_plan.items()):
            if now >= at and pid not in self.answers:
                self.answers[pid] = [pick, at]
                changed = True
        q = self.questions[self.qi]
        everyone_in = all(pid in self.answers or pid in q.subjects for pid in self.players)
        if everyone_in or now - self.started_at >= self.seconds:
            self._reveal()
        elif changed:
            self.version += 1

    @locked
    def tick(self) -> None:
        self._tick()

    @locked
    def answer(self, pid: str, choice: str) -> None:
        self._tick()
        if self.phase != "question":
            raise ValueError("Too late, answers are locked.")
        q = self.questions[self.qi]
        if pid in q.subjects:
            raise ValueError("This one's about you. Sit tight.")
        if choice not in self._option_ids(q):
            raise ValueError("That's not one of the options.")
        if pid in self.answers:
            raise ValueError("You already answered.")
        self.answers[pid] = [choice, time.time()]
        self.version += 1
        self._tick()

    def _reveal(self) -> None:
        if self.phase != "question":
            return
        q = self.questions[self.qi]
        points: dict[str, int] = {}
        right = 0
        for pid, p in self.players.items():
            if pid in q.subjects:
                continue
            ans = self.answers.get(pid)
            if ans and ans[0] in q.correct:
                right += 1
                left = max(0.0, self.seconds - (ans[1] - self.started_at))
                points[pid] = BASE_POINTS + round(SPEED_POINTS * left / self.seconds)
                p.streak += 1
                p.right += 1
            else:
                p.streak = 0
        if right:
            for s in q.subjects:
                points[s] = points.get(s, 0) + KNOWN_POINTS * right
        for pid, pts in points.items():
            if pid in self.players:
                self.players[pid].score += pts
        self.last_points = points
        self.phase = "reveal"
        self.version += 1

    @locked
    def next(self) -> None:
        self._tick()
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
            ranked = sorted(self.players.values(), key=lambda p: -p.score)
            # Nobody wins a game that ended on a tie or with no points on the board.
            clear = ranked and ranked[0].score > 0 and (len(ranked) == 1 or ranked[0].score > ranked[1].score)
            entry = {"at": time.time(), "mode": self.mode, "winner": ranked[0].id if clear else None,
                     "scores": {p.id: p.score for p in ranked}, "names": {p.id: p.name for p in ranked}}
            if self.teams:
                ts = {t: sum(p.score for p in self.players.values() if p.team == t) for t in TEAMS}
                entry["team_winner"] = max(ts, key=ts.get) if ts["red"] != ts["blue"] else None
            self.history = (self.history + [entry])[-MAX_HISTORY:]
            self.phase = "report"
            self.version += 1

    def _season(self) -> dict:
        """All-time standings for this room: wins first, then total points."""
        wins: Counter = Counter()
        points: Counter = Counter()
        names: dict[str, str] = {}
        for g in self.history:
            if g.get("winner"):
                wins[g["winner"]] += 1
            for pid, sc in g["scores"].items():
                points[pid] += sc
            names.update(g.get("names", {}))
        for pid, p in self.players.items():
            names[pid] = p.name
        table = sorted(points, key=lambda pid: (-wins[pid], -points[pid]))
        return {"games": len(self.history),
                "table": [{"id": pid, "name": names.get(pid, "?"), "wins": wins[pid], "points": points[pid],
                           "here": pid in self.players} for pid in table][:12]}

    @locked
    def rematch(self) -> None:
        self.phase = "lobby"
        self.questions = []
        self.answers = {}
        self.cards = []
        self.version += 1

    # --- what one player is allowed to see --------------------------------
    @locked
    def view(self, me: str | None) -> dict:
        self._tick()
        q = self.questions[self.qi] if self.phase in ("question", "reveal") else None
        out = {
            "code": self.code,
            "phase": self.phase,
            "version": self.version,
            "host_id": self.host_id,
            "length": self.length,
            "mode": self.mode,
            "teams": self.teams,
            "ai": self.ai,
            "me": me,
            "players": [
                {"id": p.id, "name": p.name, "score": p.score, "source": p.source, "bot": p.is_bot,
                 "avatar": p.avatar, "streak": p.streak, "right": p.right, "answered": p.id in self.answers,
                 "team": p.team}
                for p in sorted(self.players.values(), key=lambda p: p.joined_at)
            ],
        }
        if q:
            mine = self.answers.get(me) if me else None
            out["question"] = {
                "index": self.qi, "total": len(self.questions), "category": q.category, "kind": q.kind,
                "text": q.text, "image": q.image, "options": q.options,
                "seconds": self.seconds,
                "time_left": max(0, round(self.seconds - (time.time() - self.started_at))),
                "about_me": me in q.subjects,
                "my_answer": mine[0] if mine else None,
                "waiting_on": sum(1 for pid in self.players if pid not in self.answers and pid not in q.subjects),
            }
        if self.phase == "reveal" and q:
            out["reveal"] = {
                "correct": q.correct, "subjects": q.subjects, "explain": q.explain,
                "picks": {pid: c for pid, (c, _) in self.answers.items()},
                "points": self.last_points,
                "reactions": self.reactions.get(str(self.qi), []),
            }
        if self.phase == "report":
            out["cards"] = self.cards
        if self.history:
            out["season"] = self._season()
        if self.teams:
            out["team_scores"] = {t: sum(p.score for p in self.players.values() if p.team == t) for t in TEAMS}
        return out


def _unique_name(name: str, taken: set[str]) -> str:
    if name not in taken:
        return name
    n = 2
    while f"{name} {n}" in taken:
        n += 1
    return f"{name} {n}"


# No I or O: they read as 1 and 0 when someone shouts a code across a room.
CODE_ALPHABET = "".join(c for c in string.ascii_uppercase if c not in "IO")
CODE_ATTEMPTS = 50


def new_code(existing: set[str]) -> str:
    for _ in range(CODE_ATTEMPTS):
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(4))
        if code not in existing:
            return code
    raise RuntimeError("No free room codes.")
