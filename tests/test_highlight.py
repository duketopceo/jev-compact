from jev_compact import highlight, spans


def _ev(kind, text):
    return {"kind": kind, "text": text}


def _drifted_spans():
    """Moon research early, lidar code late — the user's drift example."""
    ev = [
        _ev("user_turn", "research lunar landing trajectory parameters"),
        _ev("assistant_text", "the moon descent profile uses a Hohmann transfer"),
        _ev("user_turn", "what delta-v budget for the descent stage"),
        _ev("assistant_text", "approximately 2.5 km/s for lunar descent"),
        _ev("user_turn", "ok now fix the lidar scanner code"),
        _ev("assistant_text", "looking at the point-cloud parser"),
        _ev("tool_call", "Read: {file: /src/lidar/parser.py}"),
        _ev("tool_result", "def parse_frame(buf): ..."),
        _ev("assistant_text", "the frame header offset is wrong"),
    ]
    return spans.segment(ev)


def test_highlight_follows_drift():
    sp = _drifted_spans()
    hl = highlight.extract(sp)
    assert "lidar" in hl.text.lower()
    assert "moon" not in hl.text.lower()


def test_highlight_has_intent_and_action():
    sp = _drifted_spans()
    hl = highlight.extract(sp)
    assert "Intent:" in hl.text
    assert "Latest action:" in hl.text


def test_active_files_from_tool_spans():
    sp = _drifted_spans()
    hl = highlight.extract(sp)
    assert "parser.py" in hl.text


def test_keywords_track_tail():
    sp = _drifted_spans()
    hl = highlight.extract(sp)
    assert "lidar" in hl.keywords or "parser" in hl.keywords


def test_empty_session():
    hl = highlight.extract([])
    assert "start of session" in hl.text
