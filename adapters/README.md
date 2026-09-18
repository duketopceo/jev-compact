# Harness adapters

The compaction engine is harness-agnostic (`src/jev_compact`). An adapter
is the thin per-harness wiring that (a) runs compaction against the raw
transcript at compaction time and (b) gets the output into the resumed
context.

## Adapter contract

Every adapter must do three things:

1. **Intercept compaction** — run `python3 -m jev_compact compact
   --transcript <raw> --store <dir> --out <file>` before/at the harness's
   compaction event. Never block the harness's own context reduction.
2. **Inject output** — place the emitted retention block (highlight +
   kept spans + tombstones) into the post-compaction context via whatever
   surface the harness offers.
3. **Expose restore** — register `mcp/restore_server.py` as an MCP server
   so tombstoned spans stay rehydratable.

## Harness matrix

| Harness | Intercept | Inject | Restore | Status |
|---------|-----------|--------|---------|--------|
| Claude Code | `PreCompact` hook | `SessionStart(source=compact)` `additionalContext` | MCP | `adapters/claude-code/` |
| Codex | plugin hook (per compact-plus pattern) | `additionalContext` | MCP | not wired — see tracking issue |
| OpenCode | JS plugin event hooks | plugin context surface | MCP | not wired |
| OpenClaw | gateway/plugin SDK | context surface | MCP | not wired |
| Devin | none — compaction is harness-owned | rules/skills only | MCP only | restore-only |
| Any base-url harness | local proxy intercepting the API payload | rewritten request body | MCP | design only |

## Format note

Proxy adapters must normalize provider message shapes (Anthropic vs
OpenAI) — that path is intentionally deferred until the hook path proves
the algorithm.
