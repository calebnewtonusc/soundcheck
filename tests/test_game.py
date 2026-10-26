import json
import random

from backend.game import Room, awards, build_questions, new_code
from backend.samples import SAMPLES, sample_profile


def profiles(n):
    ps = {f"p{i}": sample_profile(s) for i, s in enumerate(SAMPLES[:n])}
    names = {f"p{i}": s["name"] for i, s in enumerate(SAMPLES[:n])}
    return ps, names


def room_with(n, rng_seed=3):
    room = Room(code="TEST")
    players = [room.add_player(s["name"], sample_profile(s), "sample") for s in SAMPLES[:n]]
    room.start(rng=random.Random(rng_seed))
    return room, players


def test_questions_are_true_and_never_everyone():
    ps, names = profiles(5)
    for seed in range(20):
        for q in build_questions(ps, names, rng=random.Random(seed)):
            assert q.correct
            if q.kind == "who":
                assert set(q.subjects) <= set(q.correct)
                assert len(q.correct) < len(ps)
            else:
                assert len(q.options) == 4 and len(q.correct) == 1
                assert len({o["label"] for o in q.options}) == 4


def test_mix_of_shapes_categories_and_people():
    ps, names = profiles(5)
    qs = build_questions(ps, names, n=12, rng=random.Random(2))
    assert len(qs) == 12
    assert {q.kind for q in qs} == {"who", "pick"}
    assert {q.category for q in qs} == {"songs", "artists", "genre"}
    assert len({s for q in qs for s in q.subjects}) == 5
    order = ["songs", "artists", "genre"]
    assert [q.category for q in qs] == sorted((q.category for q in qs), key=order.index)


def test_lengths():
    ps, names = profiles(5)
    for n in (5, 8, 12):
        assert len(build_questions(ps, names, n=n, rng=random.Random(n))) == n


def test_subject_sits_out_and_scoring():
    room, (a, b) = room_with(2)
    q = room.questions[0]
    subject = q.subjects[0]
    other = b.id if subject == a.id else a.id
    choice = q.correct[0]
    try:
        room.answer(subject, choice)
        raise AssertionError("subject answered their own question")
    except ValueError:
        pass
    room.answer(other, choice)
    assert room.phase == "reveal"
    assert room.players[other].score >= 100
    assert room.players[subject].score == 50


def test_answers_hidden_until_reveal():
    room, (a, _) = room_with(2, 4)
    view = room.view(a.id)
    assert "reveal" not in view
    assert "correct" not in json.dumps(view["question"])


def test_room_survives_a_round_trip():
    room, (a, *_) = room_with(3, 5)
    restored = Room.from_dict(json.loads(json.dumps(room.to_dict())))
    assert restored.view(a.id)["question"]["text"] == room.view(a.id)["question"]["text"]
    assert restored.players[a.id].key == a.key


def test_four_game_cards():
    ps, names = profiles(5)
    assert [c["id"] for c in awards(ps, names)] == ["loyal", "switch", "superfan", "looper"]


def test_code_generation_gives_up():
    from backend import game
    taken = {a + b + c + d for a in "AB" for b in "AB" for c in "AB" for d in "AB"}
    old = game.CODE_ALPHABET
    game.CODE_ALPHABET = "AB"
    try:
        new_code(taken)
        raise AssertionError("expected RuntimeError")
    except RuntimeError:
        pass
    finally:
        game.CODE_ALPHABET = old


def test_every_mode_fills_with_its_own_questions():
    from backend.game import MODES
    ps, names = profiles(5)
    for mode in MODES:
        qs = build_questions(ps, names, n=8, rng=random.Random(9), mode=mode)
        assert len(qs) == 8
        assert sum(mode in q.tags for q in qs) >= 5, mode


def test_biggest_fan_is_the_deck_question():
    from backend.game import _fans, stats
    ps, names = profiles(5)
    st = {p: stats(x) for p, x in ps.items()}
    qs = _fans(st, names, random.Random(1))
    drake = next(q for q in qs if "Drake" in q.text)
    assert names[drake.correct[0]] == "Kaylie"


def test_teams_split_and_score():
    room = Room(code="TEAM")
    ps = [room.add_player(s["name"], sample_profile(s), "sample") for s in SAMPLES[:4]]
    room.settings(teams=True)
    assert sorted(p.team for p in room.players.values()) == ["blue", "blue", "red", "red"]
    room.start(rng=random.Random(2))
    view = room.view(ps[0].id)
    assert set(view["team_scores"]) == {"red", "blue"}


def test_reactions_toggle_only_on_reveal():
    room, (a, b) = room_with(2, 6)
    try:
        room.react(a.id, "SUS")
        raise AssertionError("reacted before reveal")
    except ValueError:
        pass
    room.next()
    room.react(a.id, "SUS")
    assert room.view(a.id)["reveal"]["reactions"] == [[a.id, "SUS"]]
    room.react(a.id, "SUS")
    assert room.view(a.id)["reveal"]["reactions"] == []


def test_no_recent_plays_means_no_recent_questions():
    ps, names = profiles(5)
    for p in ps.values():
        p["recent"] = []
    for seed in range(10):
        for q in build_questions(ps, names, n=12, rng=random.Random(seed)):
            assert "last song" not in q.text and "times in their last" not in q.text and " AM?" not in q.text


def test_round_trip_keeps_settings():
    room = Room(code="KEEP")
    for s in SAMPLES[:3]:
        room.add_player(s["name"], sample_profile(s), "sample")
    room.settings(length=5, mode="decades", teams=True)
    restored = Room.from_dict(json.loads(json.dumps(room.to_dict())))
    assert (restored.length, restored.mode, restored.teams) == (5, "decades", True)


def test_quick_picks_skip_time_window_questions():
    ps, names = profiles(4)
    picked = {"top_tracks_short": ps["p0"]["top_tracks_short"][:5], "top_tracks_long": ps["p0"]["top_tracks_short"][:5],
              "top_artists_short": ps["p0"]["top_artists_long"][:5], "top_artists_long": ps["p0"]["top_artists_long"][:5],
              "recent": [], "self_reported": True}
    ps["p0"] = picked
    for seed in range(15):
        for q in build_questions(ps, names, n=12, rng=random.Random(seed)):
            if "p0" in q.subjects:
                assert not any(w in q.text for w in ("past year", "all year", "whole year", "brand new")), q.text


def test_season_and_fresh_questions_across_rematches():
    room, (a, *_) = room_with(4, 11)
    first = {q.text for q in room.questions}
    while room.phase != "report":
        room.next()
    room.rematch()
    room.start(rng=random.Random(12))
    second = {q.text for q in room.questions}
    assert len(first & second) <= 1
    season = room.view(a.id)["season"]
    assert season["games"] == 1 and len(season["table"]) == 4


def test_leaving_scrubs_the_season():
    room, (a, b) = room_with(2, 13)
    while room.phase != "report":
        room.next()
    room.rematch()
    room.remove_player(b.id)
    for g in room.history:
        assert b.id not in g["scores"] and b.id not in g.get("names", {})
    assert not any(b.name in t for t in room.asked)


def test_strangers_see_only_the_join_screen():
    room, (a, _) = room_with(2, 14)
    pub = room.public_view()
    assert "question" not in pub and "reveal" not in pub
    assert all(p["score"] == 0 for p in pub["players"])
