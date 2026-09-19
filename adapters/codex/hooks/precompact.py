#!/usr/bin/env python3
"""Codex PreCompact hook for jev-compact.

Runs the retention pipeline before Codex compacts, storing the result
for the SessionStart hook to inject alongside Codex's own summary.
Codex compaction cannot be fully replaced by a hook (decision:block is
intentionally unsupported upstream), so this adapter augments: the
native summary still runs, and jev-compact's verbatim spans + tombstone
receipts land on top via additionalContext.

stdin  (JSON): {session_id, turn_id, transcript_path, trigger:
                "auto"|"manual", cwd, model, hook_event_name}
stdout (JSON): {"continue": true} — never blocks; a hook failure must
               not stall the session.
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

# Dev-checkout fallback: when jev_compact isn't installed, run it from
# the repo src/ (this file lives at adapters/codex/hooks/precompact.py).
_REPO_SRC = Path(__file__).resolve().parents[3] / "src"


def _env() -> dict[str, str]:
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}
    pypath = os.environ.get("PYTHONPATH", "")
    if pypath:
        env["PYTHONPATH"] = os.pathsep.join(
            str(Path(p).resolve()) for p in pypath.split(os.pathsep) if p
        )
    else:
        try:
            import jev_compact  # noqa: F401
        except ImportError:
            if _REPO_SRC.is_dir():
                env["PYTHONPATH"] = str(_REPO_SRC)
    return env


def main() -> int:
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        event = {}
    transcript = event.get("transcript_path") or ""
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
                env=_env(),
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
