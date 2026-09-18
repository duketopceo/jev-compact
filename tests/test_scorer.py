import os

import pytest

from jev_compact import highlight, scorer, spans


def _ev(kind, text):
    return {"kind": kind, "text": text}


def _spans_and_hl():
    ev = [
        _ev("user_turn", "research lunar landing parameters"),
        _ev("assistant_text", "the moon descent profile"),
        _ev("user_turn", "now fix the lidar parser bug"),
        _ev("assistant_text", "the frame header offset is wrong"),
    ]
    sp = spans.segment(ev)
    return sp, highlight.extract(sp)


def test_heuristic_ranks_on_topic_higher():
    sp, hl = _spans_and_hl()
    sc = scorer.HeuristicScorer(total_spans=len(sp))
    rel_moon, _ = sc.score(sp[1], hl)      # moon answer, now off-topic
    rel_lidar, _ = sc.score(sp[3], hl)     # lidar finding, on-topic
    assert rel_lidar > rel_moon


def test_heuristic_decision_span_load_bearing():
    sp, hl = _spans_and_hl()
    sc = scorer.HeuristicScorer(total_spans=len(sp))
    decision = spans.segment(
        [_ev("assistant_text", "decided: the fix is the header offset, root cause found")]
    )[0]
    _, load = sc.score(decision, hl)
    assert load >= 0.4


def test_heuristic_bounds():
    sp, hl = _spans_and_hl()
    sc = scorer.HeuristicScorer(total_spans=len(sp))
    for s in sp:
        rel, load = sc.score(s, hl)
        assert 0.0 <= rel <= 1.0
        assert 0.0 <= load <= 1.0


def test_resolve_heuristic_without_keys(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    sc = scorer.resolve("auto", total_spans=4)
    assert isinstance(sc, scorer.HeuristicScorer)


def test_resolve_jev_without_key_errors(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(scorer.ScorerError):
        scorer.resolve("jev")


def test_resolve_picks_typesafe_over_openrouter(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "ts-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
    sc = scorer.resolve("auto")
    assert isinstance(sc, scorer.JevScorer)
    assert sc._via == "typesafe"


def test_resolve_openrouter_fallback(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
    sc = scorer.resolve("auto")
    assert sc._via == "openrouter"


def test_first_json_extraction():
    assert scorer._first_json('noise {"rel": 7, "load": 0.5} tail') == '{"rel": 7, "load": 0.5}'
    with pytest.raises(ValueError):
        scorer._first_json("no json here")


def test_openrouter_parse(monkeypatch):
    sp, hl = _spans_and_hl()
    sc = scorer.JevScorer("k", via="openrouter")
    fake = {"choices": [{"message": {"content": '{"rel": 8, "load": 0.7}'}}]}
    monkeypatch.setattr(sc, "_post", lambda url, payload: fake)
    rel, load = sc.score(sp[0], hl)
    assert rel == pytest.approx(0.8)
    assert load == pytest.approx(0.7)


def test_openrouter_bad_payload_raises(monkeypatch):
    sp, hl = _spans_and_hl()
    sc = scorer.JevScorer("k", via="openrouter")
    monkeypatch.setattr(sc, "_post", lambda u, p: {"choices": []})
    with pytest.raises(scorer.ScorerError):
        sc.score(sp[0], hl)
