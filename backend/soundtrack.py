"""Soundtrack: the round where everyone picks a song for a moment and the room votes.

It came out of the P4c user interviews on 2026-11-09. Gavin plays it on road
trips with no app ("someone picks a scenario, everybody picks a song, then you
vote"), 3 of 5 people liked it more than the stats quiz, and the one thing
everyone said about the stats quiz was that it's a one-time game. JT's two
worries about Soundtrack shaped the rules here: "people don't always have
something in their brain" (so everyone picks from their own top songs), and
"if the other person doesn't know what the song is, it ruins the vibe" (so
every pick shows its art and plays a clip on the reveal).

What Spotify adds that a car game can't:
  - your deck is your own listening, so nobody blanks
  - picks stay anonymous until the vote is in, so the stats quiz's "wait,
    THAT'S yours?" moment happens every round
  - some prompts are written from the group's real data ("pick Sam's walkout
    song, he's been deep in alternative r&b"), so no two groups get the same game
  - a pick nobody else in the room listens to earns a deep cut bonus
"""
from __future__ import annotations

import random
import secrets
from dataclasses import dataclass, field

PICK_SECONDS = 40
VOTE_SECONDS = 25
VOTE_POINTS = 100
JUDGE_POINTS = 250
DEEP_CUT_POINTS = 50
DECK_SIZE = 12
PER_GAME = 3

# Moments anyone can play. Specific beats generic: a moment you can picture
# picks a song in seconds, "a happy song" picks nothing.
MOMENTS = [
    "PCH at sunset, windows down, nobody talking",
    "Walking into the function like you paid for it",
    "3am drive home after the best night of the semester",
    "The last lap of a run you almost quit",
    "Leavey Library at 2am, essay due at 9",
    "Main character walk to class in the rain",
    "The car next to you at the red light just caught you singing",
    "First song at the beach bonfire",
    "Victory lap after your last final",
    "Sunday morning, pancakes, nowhere to be",
    "Road trip, minute one, everyone just got in the car",
    "Locker room before the biggest game of the season",
    "Shower concert after getting left on read",
    "Your senior year graduation slideshow",
    "The plane is landing somewhere you've never been",
    "Cleaning your whole room at midnight for no reason",
    "Your crush walks in and you have to act normal",
    "The group chat just planned a spontaneous trip",
    "Packing up your dorm on the last day",
    "Slow dance at a wedding where you know nobody",
    "Gym PR attempt, everyone watching",
    "Driving home for the holidays",
    "Your team just won and the whole bus is screaming",
    "Getting ready, fit is fire, leaving in 10",
    "Fake movie trailer for your life",
]


@dataclass
class Prompt:
    text: str
    hint: str = ""
    judge: str | None = None  # a player the prompt is about; they don't pick, only they vote
    image: str | None = None
    tags: list[str] = field(default_factory=list)


def _personal(st: dict[str, dict], names: dict[str, str], rng: random.Random) -> list[Prompt]:
    """Prompts written from the room's own listening, so every group's game is theirs."""
    out: list[Prompt] = []
    for pid, s in st.items():
        name = names[pid]
        genre = s.get("top_genre")
        artist = (s.get("top_artist_month") or {}).get("name") or s.get("fan_artist")
        image = (s.get("top_artist_month") or {}).get("image")
        hint = (f"They've been deep in {genre} lately" if genre
                else f"Their #1 artist right now is {artist}" if artist else "")
        out.append(Prompt(f"Pick {name}'s walkout song", hint, judge=pid, image=image))
        if artist:
            out.append(Prompt(f"Convert {name}: the one song that gets them into YOUR music",
                              f"They live on {artist}. Pull them out of it.", judge=pid, image=image))
        loop, n = s.get("loop_track"), s.get("loop_count") or 0
        if loop and n >= 3:
            out.append(Prompt(f"{name} needs a new song to loop",
                              f"They've played \"{loop['name']}\" {n} times lately. Save them.",
                              judge=pid, image=loop.get("image")))
        late = s.get("late_track")
        if late and s.get("late_plays", 0) >= 2:
            out.append(Prompt(f"It's 2am and {name} is still up. What should be playing?",
                              f"Last time it was \"{late['name']}\".", judge=pid, image=late.get("image")))
    rng.shuffle(out)
    return out


def prompts(st: dict[str, dict], names: dict[str, str], rng: random.Random,
            n: int = PER_GAME, skip: set[str] | None = None) -> list[Prompt]:
    """Open moments everyone votes on, then one personal prompt with a judge as the finale."""
    skip = skip or set()
    personal = [p for p in _personal(st, names, rng) if p.text not in skip]
    moments = [Prompt(m) for m in MOMENTS if m not in skip] or [Prompt(m) for m in MOMENTS]
    rng.shuffle(moments)
    # A judge needs at least 2 friends picking for them, so 3+ players.
    finale = personal[:1] if len(st) >= 3 else []
    return moments[: max(0, n - len(finale))] + finale


def _key(t: dict) -> tuple[str, str]:
    return (str(t.get("name", "")).lower(), str(t.get("artist", "")).lower())


def deck(profile: dict, size: int = DECK_SIZE) -> list[dict]:
    """The songs a player picks from: this month first, then all time, then recent plays."""
    seen: set[tuple[str, str]] = set()
    out: list[dict] = []
    for src in ("top_tracks_short", "top_tracks_long", "recent"):
        for t in profile.get(src) or []:
            k = _key(t)
            if k in seen or not t.get("name"):
                continue
            seen.add(k)
            out.append({"name": t["name"], "artist": t.get("artist", "?"), "image": t.get("image"),
                        "id": t.get("id")})
            if len(out) >= size:
                return out
    return out


def plays(profile: dict, track: dict) -> int:
    k = _key(track)
    return sum(1 for t in profile.get("recent") or [] if _key(t) == k)


def listens_to(profile: dict, artist: str) -> bool:
    a = artist.lower()
    for src in ("top_artists_short", "top_artists_long"):
        if any(str(x.get("name", "")).lower() == a for x in profile.get(src) or []):
            return True
    for src in ("top_tracks_short", "top_tracks_long", "recent"):
        if any(str(x.get("artist", "")).lower() == a for x in profile.get(src) or []):
            return True
    return False


def option_id() -> str:
    # Opaque, so the vote screen can't leak whose pick is whose.
    return secrets.token_hex(4)
