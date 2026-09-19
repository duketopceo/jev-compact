# OpenCode adapter

Augment-style integration: at compaction time the plugin serializes the
session transcript through the OpenCode plugin SDK client, runs
`jev_compact compact`, and pushes the retention document into
`output.context` — so OpenCode's summarizer sees verbatim load-bearing
spans and preserves them exactly.

## Why augment, not replace

`experimental.session.compacting` offers `output.prompt` to replace the
compaction *prompt*, but a summarizer LLM still processes it — there is
no "emit this text verbatim" path in the hook contract. Feeding the
summarizer our retained spans + tombstone receipts is the honest win:
exact code/paths/errors survive the summary instead of being
paraphrased away.

## Install

1. Make `python3 -m jev_compact` resolvable:

   ```bash
   pipx install /path/to/jev-compact        # or: uv tool install
   ```

   Dev checkout alternative: set `JEV_PYTHONPATH=<repo>/src` in the
   environment. (The plugin also falls back to `<repo>/src` when run
   from inside the repo tree.)

2. Drop the plugin into OpenCode's plugin dir:

   ```bash
   ln -s /path/to/jev-compact/adapters/opencode/jev-compact.ts \
         ~/.config/opencode/plugins/jev-compact.ts
   ```

3. Optional: `TYPESAFE_API_KEY` or `OPENROUTER_API_KEY` for Jev scoring;
   offline heuristic scorer runs without keys.

## How it works

- Hook: `experimental.session.compacting` (fires for `/compact` and
  auto-overflow compaction alike).
- Transcript: `ctx.client.session.messages({path:{id}})` — no reliance
  on on-disk storage layout, which varies across OpenCode versions.
- Output: retention doc pushed to `output.context`; tombstoned spans
  restore through the `jev-compact-restore` MCP server
  (`src/jev_compact/mcp/restore_server.py`), registerable in
  `opencode.json` under `mcp`.

## Verified against

Hook contract per opencode.ai/docs/plugins (`context.push` /
`output.prompt` semantics). SDK message fetch is defensive — adapter
silently no-ops if the client shape differs, never breaking compaction.
