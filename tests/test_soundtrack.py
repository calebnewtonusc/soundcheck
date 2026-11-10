import random

from backend import soundtrack
from backend.game import Room, stats
from backend.samples import SAMPLES, sample_profile


def song_room(n=3, seed=5):
    room = Room(code="SONG")
    players = [room.add_player(s["name"], sample_profile(s), "sample") for s in SAMPLES[:n]]
    room.settings(length=5)
    room.start(rng=random.Random(seed))
    # Skip the quiz to the first Soundtrack round.
    while room.questions[room.qi].kind != "song":
        room.next()
        room.next()
    return room, players


def test_game_ends_on_soundtrack_with_the_judge_last():
    room, players = song_room(3)
    kinds = [q.kind for q in room.questions]
    assert kinds[:5] == [k for k in kinds[:5] if k != "song"]
    assert kinds[5:] == ["song"] * 3
    finale = room.questions[-1]
    assert finale.subjects and finale.subjects[0] in {p.id for p in players}


def test_two_players_get_no_judge_prompt():
    room, _ = song_room(2)
    assert all(not q.subjects for q in room.questions if q.kind == "song")


def test_soundtrack_can_be_turned_off():
    room = Room(code="OFFF")
    for s in SAMPLES[:3]:
        room.add_player(s["name"], sample_profile(s), "sample")
    room.settings(length=5, soundtrack=False)
    room.start(rng=random.Random(1))
    assert all(q.kind != "song" for q in room.questions)


def test_deck_is_your_own_listening():
    p = sample_profile(SAMPLES[0])
    d = soundtrack.deck(p)
    mine = {(t["name"], t["artist"]) for k in ("top_tracks_short", "top_tracks_long", "recent") for t in p[k]}
    assert d and all((t["name"], t["artist"]) in mine for t in d)
    assert len({(t["name"], t["artist"]) for t in d}) == len(d)


def test_pick_vote_reveal_and_points():
    room, (a, b, c) = song_room(3)
    assert room.step == "pick"
    for p in (a, b, c):
        room.pick_song(p.id, soundtrack.deck(p.profile)[0])
    assert room.step == "vote"
    # Votes are anonymous: nothing in the view says whose pick is whose.
    v = room.view(a.id)["question"]
    assert all("owner" not in o for o in v["options"])
    assert sum(o["mine"] for o in v["options"]) == 1
    mine = next(o["id"] for o in v["options"] if o["mine"])
    try:
        room.answer(a.id, mine)
        raise AssertionError("voted for own pick")
    except ValueError:
        pass
    b_opt = next(oid for oid, pid in room.song_owner.items() if pid == b.id)
    c_opt = next(oid for oid, pid in room.song_owner.items() if pid == c.id)
    room.answer(a.id, b_opt)
    room.answer(c.id, b_opt)
    room.answer(b.id, c_opt)
    assert room.phase == "reveal"
    r = room.view(a.id)["reveal"]["song"]
    top = r["cards"][0]
    assert top["owner"] == b.id and top["votes"] == 2 and top["winner"]
    assert room.players[b.id].score >= 200
    assert room.players[c.id].score >= 100


def test_judge_alone_decides_and_sits_out_picking():
    room, players = song_room(3)
    while not room.questions[room.qi].subjects:
        room.next()
        room.next()
    judge = room.questions[room.qi].subjects[0]
    others = [p for p in players if p.id != judge]
    try:
        room.pick_song(judge, {"name": "x", "artist": "y"})
        raise AssertionError("judge picked")
    except ValueError:
        pass
    for p in others:
        room.pick_song(p.id, soundtrack.deck(p.profile)[0])
    assert room.step == "vote"
    opt = room.song_options[0]["id"]
    try:
        room.answer(others[0].id, opt if room.song_owner[opt] != others[0].id else room.song_options[1]["id"])
        raise AssertionError("non-judge voted on a judge prompt")
    except ValueError:
        pass
    room.answer(judge, opt)
    assert room.phase == "reveal"
    assert room.players[room.song_owner[opt]].score >= soundtrack.JUDGE_POINTS


def test_deep_cut_bonus_only_when_nobody_else_listens():
    room, (a, b, c) = song_room(3)
    room.pick_song(a.id, {"name": "Obscure Song", "artist": "Nobody Knows Them"})
    room.pick_song(b.id, soundtrack.deck(b.profile)[0])
    room.pick_song(c.id, soundtrack.deck(c.profile)[0])
    a_opt = next(oid for oid, pid in room.song_owner.items() if pid == a.id)
    before = room.players[a.id].score
    room.answer(b.id, a_opt)
    room.answer(c.id, a_opt)
    room.answer(a.id, next(oid for oid, pid in room.song_owner.items() if pid == b.id))
    card = next(x for x in room.song_result["cards"] if x["owner"] == a.id)
    assert any("Deep cut" in n for n in card["notes"])
    assert room.players[a.id].score - before == 2 * soundtrack.VOTE_POINTS + soundtrack.DEEP_CUT_POINTS


def test_nobody_picks_and_host_skips_through():
    room, _ = song_room(3)
    room.next()  # host closes picking with nothing in
    assert room.phase == "reveal" and room.song_result["cards"] == []
    room.next()
    assert room.phase in ("question", "report")


def test_bots_pick_and_vote_on_their_own():
    room = Room(code="BOTS")
    human = room.add_player("Caleb", sample_profile(SAMPLES[0]), "sample")
    for s in SAMPLES[1:3]:
        room.add_player(s["name"], sample_profile(s), "sample", is_bot=True)
    room.settings(length=5)
    room.start(rng=random.Random(2))
    while room.questions[room.qi].kind != "song":
        room.next()
        room.next()
    room.pick_song(human.id, soundtrack.deck(human.profile)[0])
    room._tick(now=room.started_at + 60)
    assert room.step == "vote" and len(room.song_picks) == 3
    room._tick(now=room.started_at + 60)
    assert room.phase == "reveal"


def test_room_round_trips_mid_vote():
    room, (a, b, c) = song_room(3)
    for p in (a, b, c):
        room.pick_song(p.id, soundtrack.deck(p.profile)[0])
    back = Room.from_dict(room.to_dict())
    assert back.step == "vote" and back.song_owner == room.song_owner
    assert back.view(a.id)["question"]["kind"] == "song"


def test_personal_prompts_use_real_listening():
    profiles = {f"p{i}": sample_profile(s) for i, s in enumerate(SAMPLES[:3])}
    names = {f"p{i}": s["name"] for i, s in enumerate(SAMPLES[:3])}
    st = {pid: stats(p) for pid, p in profiles.items()}
    ps = soundtrack._personal(st, names, random.Random(0))
    assert ps and all(p.judge in names for p in ps)
    assert any(names[p.judge] in p.text for p in ps)
    assert all(p.hint for p in ps if "walkout" in p.text)


def test_rematch_gets_fresh_moments():
    room, _ = song_room(3)
    first = {q.text for q in room.questions if q.kind == "song"}
    while room.phase != "report":
        room.next()
    room.rematch()
    room.start(rng=random.Random(9))
    second = {q.text for q in room.questions if q.kind == "song"}
    assert not (first & second)
