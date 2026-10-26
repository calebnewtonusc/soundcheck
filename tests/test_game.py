import random

from backend.game import Room, awards, build_questions
from backend.samples import SAMPLES


def profiles(n):
    ps = {f"p{i}": {k: v for k, v in s.items() if k != "name"} for i, s in enumerate(SAMPLES[:n])}
    names = {f"p{i}": s["name"] for i, s in enumerate(SAMPLES[:n])}
    return ps, names


def test_questions_are_true_and_not_everyone():
    ps, names = profiles(5)
    qs = build_questions(ps, names, rng=random.Random(1))
    assert len(qs) == 8
    for q in qs:
        assert q.subject in q.correct
        assert len(q.correct) < len(ps)
    assert [q.category for q in qs] == sorted([q.category for q in qs], key=["songs", "artists", "genre"].index)


def test_spotlight_spreads_across_players():
    ps, names = profiles(5)
    qs = build_questions(ps, names, rng=random.Random(2))
    assert len({q.subject for q in qs}) >= 4


def test_subject_cannot_answer_and_scoring():
    room = Room(code="TEST")
    a = room.add_player("A", {k: v for k, v in SAMPLES[0].items() if k != "name"}, "sample")
    b = room.add_player("B", {k: v for k, v in SAMPLES[1].items() if k != "name"}, "sample")
    room.start(rng=random.Random(3))
    q = room.questions[0]
    other = b.id if q.subject == a.id else a.id
    try:
        room.answer(q.subject, other)
        raise AssertionError("subject answered their own question")
    except ValueError:
        pass
    room.answer(other, q.subject)  # everyone else is in, so it reveals
    assert room.phase == "reveal"
    assert room.players[other].score >= 100
    assert room.players[q.subject].score == 50


def test_answers_hidden_until_reveal():
    room = Room(code="TEST")
    a = room.add_player("A", {k: v for k, v in SAMPLES[0].items() if k != "name"}, "sample")
    room.add_player("B", {k: v for k, v in SAMPLES[1].items() if k != "name"}, "sample")
    room.start(rng=random.Random(4))
    view = room.view(a.id)
    assert "reveal" not in view and "correct" not in str(view["question"])


def test_four_game_cards():
    ps, names = profiles(5)
    cards = awards(ps, names)
    assert [c["id"] for c in cards] == ["loyal", "switch", "superfan", "looper"]
