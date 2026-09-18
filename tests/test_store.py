from pathlib import Path

from jev_compact import highlight, spans, store


def _spans():
    return spans.segment(
        [
            {"kind": "user_turn", "text": "research lunar landing parameters"},
            {"kind": "assistant_text", "text": "the moon descent profile"},
            {"kind": "user_turn", "text": "now fix the lidar parser"},
        ]
    )


def _save(tmp_path: Path) -> tuple[store.SpanStore, list]:
    sp = _spans()
    hl = highlight.extract(sp)
    st = store.SpanStore(tmp_path, "sess1")
    st.save(sp, hl, [("s0-s1", "[[s0-s1 tombstoned]]")], Path("/tmp/t.jsonl"))
    return st, sp


def test_roundtrip_span_text(tmp_path):
    st, sp = _save(tmp_path)
    assert st.get_span("s0") == sp[0].text


def test_range_restore(tmp_path):
    st, sp = _save(tmp_path)
    text = st.get_range("s0-s1")
    assert sp[0].text in text and sp[1].text in text


def test_single_span_range(tmp_path):
    st, _ = _save(tmp_path)
    assert st.get_range("s2") == st.get_span("s2")


def test_bad_range_returns_none(tmp_path):
    st, _ = _save(tmp_path)
    assert st.get_range("bogus") is None
    assert st.get_range("s99") is None


def test_list_tombstones(tmp_path):
    st, _ = _save(tmp_path)
    tombs = st.list_tombstones()
    assert len(tombs) == 1
    assert tombs[0]["range"] == "s0-s1"
    assert "lunar" in tombs[0]["preview"]


def test_get_highlight(tmp_path):
    st, _ = _save(tmp_path)
    assert "CURRENT WORK" in st.get_highlight()


def test_latest_session(tmp_path):
    _save(tmp_path)
    assert store.latest_session(tmp_path) == "sess1"
    assert store.latest_session(tmp_path / "nope") is None


def test_files_mode_0600(tmp_path):
    st, _ = _save(tmp_path)
    mode = (st.dir / "spans.json").stat().st_mode & 0o777
    assert mode == 0o600


def test_session_id_stable(tmp_path):
    a = store.session_id_for(Path("/x/session.jsonl"))
    b = store.session_id_for(Path("/x/session.jsonl"))
    assert a == b and len(a) == 12
