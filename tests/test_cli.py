"""CLI-level regression tests.

These cover argument handling, which the unit tests below this level never
touch: module-level logic is tested elsewhere, but `argparse` wiring bugs
(such as a flag that is documented but unreachable) are only observable by
invoking the parser.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def run_cli(*args, cwd=None):
    """Invoke the CLI in a subprocess so exit codes and stderr are real."""
    return subprocess.run(
        [sys.executable, "-m", "jev_compact", *args],
        capture_output=True, text=True, cwd=str(cwd or REPO),
        env={"PYTHONPATH": str(REPO / "src"), "PATH": "/usr/bin:/bin"},
    )


# TAIL_KEEP is 4: the last four spans are never scored out. A transcript
# shorter than that produces no tombstones at all, so --list would be
# legitimately empty and the test would prove nothing. Use 8 spans.
TRANSCRIPT_ROWS = [
    {"role": "user", "content": "Set up the deploy pipeline for staging"},
    {"role": "assistant", "content": "Examining CI config and deploy targets."},
    {"role": "tool", "content": "<config>name: staging-deploy</config>"},
    {"role": "assistant", "content": "Creating the workflow file for staging."},
    {"role": "user", "content": "no wait, use trunk-based deploys instead"},
    {"role": "assistant", "content": "Switching to trunk-based with flags."},
    {"role": "tool", "content": "<flags>enabled: false</flags>"},
    {"role": "assistant", "content": "Feature flags added, prior approach gone."},
]


@pytest.fixture
def transcript(tmp_path):
    p = tmp_path / "t.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in TRANSCRIPT_ROWS))
    return p


def test_help_lists_all_three_subcommands():
    r = run_cli("--help")
    assert r.returncode == 0
    for sub in ("compact", "highlight", "restore"):
        assert sub in r.stdout


def test_restore_list_works_without_span(tmp_path, transcript):
    """Regression: --span was `required=True`, so --list could never run.

    The flag is documented as "list tombstones instead" but argparse rejected
    the invocation before the handler ever saw it.
    """
    r = run_cli("compact", "--transcript", str(transcript),
                "--scorer", "heuristic", "--budget", "40", cwd=tmp_path)
    assert r.returncode == 0, r.stderr

    r = run_cli("restore", "--store", ".jev-compact", "--list", cwd=tmp_path)
    assert r.returncode == 0, f"--list should not require --span: {r.stderr}"
    assert "s0" in r.stdout


def test_restore_without_span_or_list_explains_itself(tmp_path):
    """The guard message must name both valid invocations."""
    r = run_cli("restore", "--store", ".jev-compact", cwd=tmp_path)
    assert r.returncode != 0
    assert "--span" in (r.stderr + r.stdout)
    assert "--list" in (r.stderr + r.stdout)
