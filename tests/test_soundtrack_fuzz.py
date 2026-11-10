"""Random games end to end: every path a real room can take through Soundtrack.

Each game picks 2 to 8 players (some bots), plays the quiz fast, then drives
the Soundtrack rounds with random behavior: people who never pick, picks from
search with odd names, the host skipping steps, timers running out, votes for
your own pick, the judge trying to pick, a vote before picks close, and the
room saved and reloaded mid-step. Only ValueError may come out of a player
action; anything else is a crash a real room would hit.
"""
import random

from backend import soundtrack
from backend.game import Room
from backend.samples import SAMPLES, sample_profile

ODD = [
    {"name": "x" * 200, "artist": "y" * 200},
    {"name": "<script>alert(1)</script>", "artist": "Nobody"},
    {"name": "Café del Mar 🌊", "artist": "Energy 52"},
    {"name": "  spaced  ", "artist": "  out  "},
    {"name": "Track", "artist": "Artist", "image": "javascript:alert(1)", "id": "../../etc"},
    {"name": "", "artist": "Empty"},
    {"name": "No artist", "artist": ""},
]


def try_(fn, *a):
    try:
        fn(*a)
    except ValueError:
        pass


def play(seed: int) -> Room:
    rng = random.Random(seed)
    room = Room(code="FUZZ")
    n = rng.randint(2, 8)
    for i in range(n):
        s = SAMPLES[i % len(SAMPLES)]
        bot = i > 0 and rng.random() < 0.3
        room.add_player(f"{s['name']}{i}", sample_profile(s), "sample", is_bot=bot)
    room.settings(length=5, teams=rng.random() < 0.3)
    room.start(rng=rng)
    ids = list(room.players)
    steps = 0
    while room.phase != "report":
        steps += 1
        assert steps < 400, "game never ended"
        q = room.questions[room.qi]
        if rng.random() < 0.15:
            room = Room.from_dict(room.to_dict())
        if q.kind != "song":
            room.next()
            continue
        if room.phase == "reveal":
            assert room.step == ""
            res = room.song_result
            for c in res["cards"]:
                assert c["owner"] not in c["voters"], "voted for own pick"
                assert c["votes"] == len(c["voters"])
            if q.subjects:
                assert all(c["owner"] != q.subjects[0] for c in res["cards"]), "judge picked"
            room.next()
            continue
        if room.step == "pick":
            for pid in ids:
                r = rng.random()
                if r < 0.15:
                    continue  # never picks
                if r < 0.25:
                    try_(room.pick_song, pid, rng.choice(ODD))
                else:
                    d = soundtrack.deck(room.players[pid].profile)
                    if d:
                        try_(room.pick_song, pid, rng.choice(d))
                if rng.random() < 0.1:
                    try_(room.pick_song, pid, {"name": "again", "artist": "again"})
                if rng.random() < 0.05:
                    try_(room.answer, pid, "nope")
                if room.step != "pick":
                    break
            for pid, t in room.song_picks.items():
                assert t["name"] and t["artist"]
                assert t["image"] is None or t["image"].startswith("https://")
                assert t["id"] is None or t["id"].isalnum()
            if room.step == "pick":
                if rng.random() < 0.5:
                    room.next()
                else:
                    room._tick(now=room.started_at + soundtrack.PICK_SECONDS + 1)
            continue
        if room.step == "vote":
            opts = [o["id"] for o in room.song_options]
            for pid in ids:
                if rng.random() < 0.2:
                    continue
                choice = rng.choice(opts + ["bogus"])
                try_(room.answer, pid, choice)
                if room.step != "vote":
                    break
            if room.phase == "question":
                if rng.random() < 0.5:
                    room.next()
                else:
                    room._tick(now=room.started_at + soundtrack.VOTE_SECONDS + 1)
            continue
        raise AssertionError(f"song question in phase {room.phase} with step {room.step!r}")
    for p in room.players.values():
        assert p.score >= 0
    # Every view a phone could ask for renders at every point, including after the game.
    for pid in ids + [None]:
        room.view(pid)
    room.public_view()
    return room


def test_hundreds_of_random_games():
    for seed in range(300):
        play(seed)


def test_views_mid_round_never_leak_owners():
    for seed in range(40):
        rng = random.Random(seed)
        room = Room(code="LEAK")
        for i, s in enumerate(SAMPLES[:4]):
            room.add_player(s["name"], sample_profile(s), "sample")
        room.settings(length=5)
        room.start(rng=rng)
        while room.questions[room.qi].kind != "song":
            room.next()
        for pid in room.players:
            d = soundtrack.deck(room.players[pid].profile)
            try_(room.pick_song, pid, d[0])
        if room.step != "vote":
            continue
        for pid in list(room.players) + [None]:
            v = room.view(pid)
            blob = repr(v["question"]["options"])
            others = [p for p in room.players if p != pid]
            assert not any(o in blob for o in others), "an option names its owner"
            assert "song" not in v.get("reveal", {}), "reveal shown during the vote"
