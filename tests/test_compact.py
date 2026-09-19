from jev_compact import compact, highlight, scorer, spans


def _ev(kind, text):
    return {"kind": kind, "text": text}


class FixedScorer:
    """Test double: score by span id prefix."""

    def __init__(self, table):
        self.table = table

    def score(self, span, hl):
        return self.table.get(span.id, (0.0, 0.0))


def _moon_lidar_spans():
    ev = [
        _ev("user_turn", "research lunar landing trajectory parameters"),
        _ev("assistant_text", "the moon descent profile uses a Hohmann transfer. " * 30),
        _ev("tool_call", "WebSearch: {q: lunar descent delta-v}"),
        _ev("tool_result", "apollo descent documentation and trajectory tables. " * 40),
        _ev("user_turn", "delta-v for descent stage?"),
        _ev("assistant_text", "about 2.5 km/s"),
        _ev("user_turn", "now fix the lidar parser"),
        _ev("assistant_text", "the frame header offset is wrong in parser.py"),
        _ev("tool_call", "Edit: {file: /src/lidar/parser.py}"),
        _ev("tool_result", "applied"),
        _ev("assistant_text", "offset fixed, tests green"),
        _ev("user_turn", "ship it"),
    ]
    return spans.segment(ev)


def test_drift_keeps_recent_drops_old():
    sp = _moon_lidar_spans()
    hl = highlight.extract(sp)
    sc = scorer.HeuristicScorer(total_spans=len(sp))
    result = compact.compact(sp, hl, sc, budget_tokens=200)
    kept_text = "\n".join(s.text for s in sp if s.id in result.kept_ids)
    assert "lidar" in kept_text.lower()
    assert result.tokens_after < result.tokens_before
    assert result.tombstoned  # moon spans tombstoned or dropped


def test_tail_always_kept_under_zero_budget():
    sp = _moon_lidar_spans()
    hl = highlight.extract(sp)
    result = compact.compact(sp, hl, FixedScorer({}), 0)
    tail_ids = {s.id for s in sp[-compact.TAIL_KEEP:]}
    assert tail_ids <= set(result.kept_ids)


def test_load_bearing_pinned_over_budget():
    sp = _moon_lidar_spans()
    hl = highlight.extract(sp)
    # s1 (moon answer) marked load-bearing — must survive a tiny budget
    table = {"s1": (0.0, 0.9)}
    result = compact.compact(sp, hl, FixedScorer(table), 50)
    assert "s1" in result.kept_ids


def test_tombstone_receipt_format():
    sp = _moon_lidar_spans()
    hl = highlight.extract(sp)
    result = compact.compact(sp, hl, FixedScorer({}), 10)
    for rng, receipt in result.tombstoned:
        assert receipt.startswith("[[")
        assert "tombstoned" in receipt
        assert rng in receipt


def test_output_contains_highlight_header():
    sp = _moon_lidar_spans()
    hl = highlight.extract(sp)
    result = compact.compact(sp, hl, FixedScorer({}), 500)
    assert result.text.startswith("CURRENT WORK:")


def test_stats_ratio():
    sp = _moon_lidar_spans()
    hl = highlight.extract(sp)
    result = compact.compact(sp, hl, FixedScorer({}), 100)
    assert 0 < result.stats["ratio"] <= 1
    assert result.stats["spans"] == len(sp)


def test_empty_kept_spans_not_emitted():
    ev = [
        _ev("user_turn", "do the thing"),
        _ev("other", ""),
        _ev("assistant_text", "done"),
    ]
    sp = spans.segment(ev)
    hl = highlight.extract(sp)
    # generous budget keeps everything scored — but the empty span must not emit
    result = compact.compact(sp, hl, FixedScorer({}), 5000)
    assert "[s1 · other]" not in result.text
    assert "do the thing" in result.text


def test_receipt_uses_first_nonempty_preview():
    ev = [
        _ev("other", ""),
        _ev("assistant_text", "early moon research content " * 40),
        _ev("other", ""),
    ]
    # filler pushes the early spans into the scored head (tail keeps last TAIL_KEEP)
    ev += [_ev("assistant_text", f"recent work chunk {i} " * 20) for i in range(28)]
    sp = spans.segment(ev)
    hl = highlight.extract(sp)
    result = compact.compact(sp, hl, FixedScorer({}), 200)
    receipts = [r for _, r in result.tombstoned]
    assert receipts
    assert any("moon research" in r for r in receipts)
    assert not any("begins: (empty)" in r for r in receipts if "moon" in r)
