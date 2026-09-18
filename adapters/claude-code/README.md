# Claude Code adapter

Replaces Claude Code's built-in compaction with jev-compact's
retention filter, using the proven block-free path:

1. `CLAUDE.md` carries the Compact Instructions snippet → the model's
   built-in `/compact` summary becomes a one-line placeholder.
2. `PreCompact` hook (`hooks/precompact.py`) runs the real compaction
   against the full transcript → writes `.jev-compact/out.md` + span store.
3. `SessionStart` hook (`hooks/sessionstart.py`, `source=compact`) injects
   `out.md` as `additionalContext` → the session resumes on retained
   spans + tombstone receipts.
4. `context-restore` MCP server lets the model rehydrate any tombstoned
   span by range.

## Install

```bash
pip install -e /path/to/jev-compact   # makes `python3 -m jev_compact` resolvable

# 1) Merge hooks + MCP server into ~/.claude/settings.json
#    (edit the /path/to placeholders in settings.snippet.json first)
# 2) Append compact-instructions.snippet.md to your project's CLAUDE.md
```

Verify: run `/compact` in a session — the summary line should be the
placeholder, and the next turn should open with the retained spans block.

## Notes

- The PreCompact hook never blocks (exit 2 / `{"decision":"block"}` would
  leave context unshrunk); replacement happens via placeholder + inject.
- `JEV_STORE_DIR` defaults to `.jev-compact` under the project cwd;
  `JEV_BUDGET_TOKENS` defaults to 8000.
- Scorer env: `TYPESAFE_API_KEY` (native) or `OPENROUTER_API_KEY`
  (fallback); unset → heuristic scorer, still fully functional.
