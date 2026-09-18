#!/usr/bin/env python3
"""Claude Code PreCompact hook for jev-compact.

Runs the compaction pipeline before the harness compacts, storing the
result for the SessionStart hook to inject. Pair with the
compact-instructions snippet in CLAUDE.md so the built-in summary is a
placeholder and jev-compact's output is what actually lands in context.

stdin  (JSON): {session_id, transcript_path, trigger: "auto"|"manual", cwd}
stdout (JSON): {"continue": true} — never blocks; replacement happens via
               placeholder + SessionStart injection.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

TIMEOUT_S = 120
STORE_DIR = Path(os.environ.get("JEV_STORE_DIR", ".jev-compact"))
BUDGET = os.environ.get("JEV_BUDGET_TOKENS", "8000")


def main() -> int:
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        event = {}
    transcript = event.get("transcript_path", "")
    cwd = event.get("cwd") or os.getcwd()
    store_dir = Path(cwd) / STORE_DIR
    out_file = store_dir / "out.md"

    if transcript and Path(transcript).is_file():
        store_dir.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(
                [
                    "/usr/bin/python3",
                    "-m",
                    "jev_compact",
                    "compact",
                    "--transcript",
                    transcript,
                    "--budget",
                    BUDGET,
                    "--scorer",
                    "auto",
                    "--store",
                    str(store_dir),
                    "--out",
                    str(out_file),
                    "--json",
                ],
                cwd=cwd,
                timeout=TIMEOUT_S,
                env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass  # compaction failure must never block the session

    print(json.dumps({"continue": True}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
