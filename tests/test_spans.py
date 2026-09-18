from jev_compact import spans


def _ev(kind, text):
    return {"kind": kind, "text": text}


def test_tool_call_result_pairing():
    ev = [
        _ev("user_turn", "read lidar.py"),
        _ev("tool_call", "Read: {file: lidar.py}"),
        _ev("tool_result", "def scan(): ..."),
        _ev("assistant_text", "the parser drops frames"),
    ]
    sp = spans.segment(ev)
    assert len(sp) == 3
    assert sp[1].kind == "tool"
    assert "Read" in sp[1].text and "def scan" in sp[1].text


def test_unpaired_tool_call_becomes_span():
    ev = [_ev("tool_call", "Bash: ls"), _ev("assistant_text", "done")]
    sp = spans.segment(ev)
    assert [s.kind for s in sp] == ["tool", "assistant_text"]


def test_ids_and_token_est():
    ev = [_ev("user_turn", "x" * 40), _ev("assistant_text", "y" * 400)]
    sp = spans.segment(ev)
    assert [s.id for s in sp] == ["s0", "s1"]
    assert sp[0].token_est == 10
    assert sp[1].token_est == 100


def test_preview_first_line():
    sp = spans.segment([_ev("user_turn", "first line\nsecond line")])
    assert sp[0].preview == "first line"
