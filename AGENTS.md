# AGENTS.md — jev-compact

> This file is the agent entry point for this repo.
> Full agent context lives at: https://github.com/duketopceo/luke-agents

Inherits from [luke-agents/AGENTS.md](https://github.com/duketopceo/luke-agents/blob/main/AGENTS.md). This file specializes; it does not replace.

## What This Repo Does

Context compaction engine for agent harnesses. Scores transcript spans against the conversation's moving highlight using TypeSafe's Jev System One decision model (calibrated `score`/`noul` primitives, free output tokens), retains high-value spans verbatim, tombstones the rest with restorable receipts. Ships a stdio MCP restore server and per-harness adapters (Claude Code first).

## Key Files

- `src/jev_compact/cli.py` — `jev-compact` entry: `compact`, `restore`, `highlight` verbs
- `src/jev_compact/compact.py` — knapsack retention engine (score → rank → keep/tombstone/drop)
- `src/jev_compact/scorer.py` — `HeuristicScorer` (offline) + `JevScorer` (TypeSafe/OpenRouter)
- `src/jev_compact/highlight.py` — moving-highlight extraction
- `src/jev_compact/store.py` — span store backing tombstone restore (atomic 0600 writes)
- `mcp/restore_server.py` — stdio JSON-RPC MCP server (`get_span`, `list_tombstones`, `get_highlight`)
- `adapters/claude-code/` — PreCompact + SessionStart hook wiring
- `docs/design.md` — algorithm spec + adapter contract + harness matrix

## Current Status

- [x] In development
- [ ] Deployed
- [ ] Production traffic

## Active Issues / Known State

- `JevScorer` native TypeSafe `/v1/systemone` request schema written from public docs — still needs a TypeSafe key to verify. The OpenRouter path IS verified live (2026-09-19): TypeSafe models serve via `POST /api/alpha/decisions` (model `~typesafe/jev-latest` or `typesafe/jev-1.13`) — `state` + `questions` map of `score`/`noul`/`choice` primitives, ~$0.000016/span, both scoring axes in one call. Non-TypeSafe OpenRouter slugs fall back to generic chat JSON scoring.
- Codex + OpenCode adapters not yet wired (see tracking issue).

## Agent Instructions (repo-specific)

- Python 3.11+, **stdlib only** for the core package — no runtime deps without discussion.
- Type hints on every signature; `pathlib` over `os.path`; `logging` over `print` (CLI output excepted).
- Compaction is non-destructive by design: never delete source transcripts; tombstones must resolve back to verbatim spans via the store.
- Tests run with `python -m pytest tests/` (pytest via `uvx --with pytest pytest` when not installed).
- Default: follow duketopceo/luke-agents for all standards.
