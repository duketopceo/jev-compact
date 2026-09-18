#!/usr/bin/env python3
"""Claude Code SessionStart hook for jev-compact.

After the harness compacts (source == "compact"), injects the
jev-compact output as additionalContext so the compacted session
resumes from the retained spans + tombstones, not the placeholder.

stdin  (JSON): {session_id, source: "startup"|"resume"|"compact"|"clear", cwd}
stdout (JSON): {"hookSpecificOutput": {"hookEventName": "SessionStart",
                "additionalContext": "..."}} or {} when nothing to inject.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

STORE_DIR = os.environ.get("JEV_STORE_DIR", ".jev-compact")
MAX_INJECT = 400_000


def main() -> int:
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        event = {}

    if event.get("source") != "compact":
        print("{}")
        return 0

    cwd = event.get("cwd") or os.getcwd()
    out_file = Path(cwd) / STORE_DIR / "out.md"
    context = ""
    try:
        if out_file.is_file() and out_file.stat().st_size <= MAX_INJECT:
            context = out_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        context = ""

    if context:
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "SessionStart",
                        "additionalContext": (
                            "jev-compact retention context (tombstoned spans are "
                            "restorable via the context-restore MCP server):\n\n"
                            + context
                        ),
                    }
                }
            )
        )
    else:
        print("{}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
