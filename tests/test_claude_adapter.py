"""Claude Code adapter hooks, exercised end to end.

The adapter is a pair of hooks: PreCompact writes the store + out.md, and
SessionStart injects it as additionalContext. Neither had test coverage, and
they are the only path by which the package reaches a real harness — a bug
here is invisible to every unit test in the package.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HOOKS = REPO / "adapters" / "claude-code" / "hooks"

ROWS = [
    {"role": "user", "content": "Set up the deploy pipeline for staging"},
    {"role": "assistant", "content": "Examining CI config and targets."},
    {"role": "tool", "content": "<config>name: staging-deploy</config>"},
    {"role": "assistant", "content": "Creating the workflow file."},
    {"role": "user", "content": "no wait, use trunk-based deploys"},
    {"role": "assistant", "content": "Switching to trunk-based with flags."},
    {"role": "tool", "content": "<flags>enabled: false</flags>"},
    {"role": "assistant", "content": "Flags added, prior approach gone."},
]


def run_hook(name, payload, cwd):
    return subprocess.run(
        [sys.executable, str(HOOKS / name)],
        input=json.dumps(payload), capture_output=True, text=True,
        cwd=str(cwd),
        env={"PYTHONPATH": str(REPO / "src"), "PATH": "/usr/bin:/bin"},
    )


def test_precompact_then_sessionstart_injects(tmp_path):
    t = tmp_path / "t.jsonl"
    t.write_text("\n".join(json.dumps(r) for r in ROWS))

    pre = run_hook("precompact.py",
                   {"session_id": "t1", "transcript_path": str(t),
                    "trigger": "auto", "cwd": str(tmp_path)}, tmp_path)
    assert pre.returncode == 0, pre.stderr
    assert json.loads(pre.stdout) == {"continue": True}, pre.stdout

    out_md = tmp_path / ".jev-compact" / "out.md"
    assert out_md.is_file(), "precompact did not write out.md"

    post = run_hook("sessionstart.py",
                    {"session_id": "t1", "cwd": str(tmp_path),
                     "source": "compact"}, tmp_path)
    assert post.returncode == 0, post.stderr
    body = json.loads(post.stdout)
    ctx = body["hookSpecificOutput"]["additionalContext"]
    assert body["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    assert "trunk-based" in ctx, ctx[:300]


def test_sessionstart_is_a_noop_outside_compact(tmp_path):
    """source != "compact" must emit {} so the harness adds nothing."""
    for source in ("startup", "resume", "clear"):
        r = run_hook("sessionstart.py",
                     {"session_id": "t1", "cwd": str(tmp_path),
                      "source": source}, tmp_path)
        assert r.returncode == 0, r.stderr
        assert json.loads(r.stdout) == {}, f"{source} should inject nothing"


def test_codex_adapter_round_trip(tmp_path):
    """Codex speaks the same protocol plus turn_id/model/hook_event_name."""
    t = tmp_path / "t.jsonl"
    t.write_text("\n".join(json.dumps(r) for r in ROWS))
    codex = REPO / "adapters" / "codex" / "hooks"

    pre = subprocess.run(
        [sys.executable, str(codex / "precompact.py")],
        input=json.dumps({"session_id": "t1", "turn_id": 7,
                          "transcript_path": str(t), "trigger": "auto",
                          "cwd": str(tmp_path), "model": "gpt-5",
                          "hook_event_name": "PreCompact"}),
        capture_output=True, text=True, cwd=str(tmp_path),
        env={"PYTHONPATH": str(REPO / "src"), "PATH": "/usr/bin:/bin"})
    assert pre.returncode == 0, pre.stderr
    assert (tmp_path / ".jev-compact" / "out.md").is_file()

    post = subprocess.run(
        [sys.executable, str(codex / "sessionstart.py")],
        input=json.dumps({"session_id": "t1", "cwd": str(tmp_path),
                          "source": "compact"}),
        capture_output=True, text=True, cwd=str(tmp_path),
        env={"PYTHONPATH": str(REPO / "src"), "PATH": "/usr/bin:/bin"})
    assert post.returncode == 0, post.stderr
    assert "trunk-based" in post.stdout


def test_precompact_survives_a_missing_transcript(tmp_path):
    """A bad path must not block the harness's own compaction."""
    r = run_hook("precompact.py",
                 {"session_id": "t1", "transcript_path": "/nonexistent/x.jsonl",
                  "trigger": "auto", "cwd": str(tmp_path)}, tmp_path)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == {"continue": True}