import json
from pathlib import Path

from jev_compact import transcript


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "t.jsonl"
    p.write_text(text)
    return p


def test_generic_ndjson(tmp_path):
    p = _write(
        tmp_path,
        '{"role": "user", "content": "hello"}\n'
        '{"role": "assistant", "content": "hi back"}\n',
    )
    ev = transcript.load(p)
    assert [e["kind"] for e in ev] == ["user_turn", "assistant_text"]
    assert ev[0]["text"] == "hello"


def test_claude_code_jsonl(tmp_path):
    lines = [
        {
            "type": "user",
            "message": {"role": "user", "content": [{"type": "text", "text": "fix the lidar parser"}]},
            "timestamp": "2026-09-18T00:00:00Z",
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "looking at the parser"},
                    {"type": "tool_use", "name": "Read", "input": {"file_path": "/src/lidar.py"}},
                ],
            },
            "timestamp": "2026-09-18T00:00:01Z",
        },
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [{"type": "tool_result", "content": "def scan(): ..."}],
            },
            "timestamp": "2026-09-18T00:00:02Z",
        },
    ]
    p = _write(tmp_path, "\n".join(json.dumps(x) for x in lines))
    ev = transcript.load(p)
    kinds = [e["kind"] for e in ev]
    assert kinds == ["user_turn", "assistant_text", "tool_call", "tool_result"]
    assert "Read" in ev[2]["text"]
    assert "scan" in ev[3]["text"]


def test_json_array_input(tmp_path):
    p = _write(tmp_path, json.dumps([{"role": "user", "text": "array input"}]))
    ev = transcript.load(p)
    assert ev[0]["kind"] == "user_turn"
    assert ev[0]["text"] == "array input"


def test_bad_lines_skipped(tmp_path):
    p = _write(tmp_path, 'not json\n{"role": "user", "content": "ok"}\n')
    ev = transcript.load(p)
    assert len(ev) == 1
    assert ev[0]["text"] == "ok"


def test_content_list_joined(tmp_path):
    p = _write(
        tmp_path,
        json.dumps([{"role": "assistant", "content": [{"text": "a"}, {"text": "b"}]}]),
    )
    ev = transcript.load(p)
    assert ev[0]["text"] == "a\nb"
