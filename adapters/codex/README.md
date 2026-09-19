# Codex adapter

Augment-style integration: Codex's native compaction still runs;
jev-compact's verbatim retention + tombstone receipts are injected on
top of it.

## Why augment, not replace

Codex added `PreCompact`/`PostCompact` hooks in openai/codex#19905, but
upstream intentionally does not support `decision:"block"` — a hook
cannot take over compaction the way the Claude Code adapter can via the
placeholder + inject pattern. `continue:false` stops compaction without
injecting anything, which just makes auto-compaction retry. So the
Codex adapter does the honest thing: run the retention pipeline before
compaction, inject the result after.

## Install

1. Install the package so `python3 -m jev_compact` resolves:

   ```bash
   pipx install /path/to/jev-compact        # or: uv tool install
   ```

2. Merge `hooks.snippet.json` into `~/.codex/hooks.json` under the
   top-level `"hooks"` object — replacing `/ABSOLUTE/PATH/TO` with the
   real adapter path. `~/.codex/hooks.json` is a shared file; do not
   overwrite it wholesale (other tools like numbat register hooks
   there).

3. Optional: set `TYPESAFE_API_KEY` or `OPENROUTER_API_KEY` in the
   environment for Jev scoring; without keys the offline heuristic
   scorer runs.

## How it works

- `PreCompact` (`manual|auto`): runs `jev_compact compact` on the
  rollout transcript Codex passes via `transcript_path`, writing
  `<cwd>/.jev-compact/out.md` + the span store.
- `SessionStart` (`compact`): emits `additionalContext` containing the
  retained spans, the moving highlight, and tombstone receipts.
- Tombstoned content restores through the `jev-compact-restore` MCP
  server (`src/jev_compact/mcp/restore_server.py`) — register it in
  `~/.codex/config.toml` as an MCP server for on-demand rehydration.

## Verified against

codex-cli 0.155.0 (`PreCompact`/`PostCompact`/`compact_prompt` present
in the binary; hook input contract per
developers.openai.com/codex/hooks).
