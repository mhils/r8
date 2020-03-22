import r8
from r8.scoring import Scoreboard


def test_scoreboard(monkeypatch):
    monkeypatch.setitem(r8.settings, "scoring", True)
    monkeypatch.setitem(r8.settings, "scoring_alpha", 0.1)
    monkeypatch.setitem(r8.settings, "scoring_beta", 1.5)
    monkeypatch.setitem(r8.settings, "scoring_first_solve_bonus", 8)

    d = 0
    s = Scoreboard()
    assert s.scores["foo"] == 0
    assert s.scores["bar"] == 0
    assert s.scores["baz"] == 0

    s = s.solve("foo", "cid1", d)
    assert s.scores["foo"] == 508
    assert s.scores["bar"] == 0
    assert s.scores["baz"] == 0

    s = s.solve("bar", "cid2", d)
    assert s.scores["foo"] == 508
    assert s.scores["bar"] == 508
    assert s.scores["baz"] == 0

    s = s.solve("baz", "cid1", d)
    assert s.scores["foo"] == 494
    assert s.scores["bar"] == 508
    assert s.scores["baz"] == 490

    assert repr(s)


def test_scoreboard_time(monkeypatch):
    monkeypatch.setitem(r8.settings, "scoring", True)
    monkeypatch.setitem(r8.settings, "scoring_alpha", 1)
    monkeypatch.setitem(r8.settings, "scoring_beta", 1)
    monkeypatch.setitem(r8.settings, "scoring_first_solve_bonus", 0)

    t1 = 1234567890
    t2 = t1 + 10
    t3 = t1 + 20

    s = Scoreboard()
    assert s.scores["foo"] == 0
    assert s.scores["bar"] == 0
    assert s.scores["baz"] == 0

    s = s.solve("foo", "cid1", t1)
    assert s.scores["foo"] == 499.9876543211
    assert s.scores["bar"] == 0
    assert s.scores["baz"] == 0

    s = s.solve("bar", "cid2", t2)
    assert s.scores["foo"] == 499.9876543211
    assert s.scores["bar"] == 499.9876543210
    assert s.scores["baz"] == 0

    s = s.solve("baz", "cid1", t3)
    assert s.scores["foo"] == 264.9876543211
    assert s.scores["bar"] == 499.9876543210
    assert s.scores["baz"] == 264.9876543209

    assert repr(s) == "Scoreboard[#1 bar (500), #2 foo (265), #3 baz (265)]"
