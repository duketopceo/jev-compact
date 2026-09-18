# jev-compact

> Context compaction for agent harnesses: a decision-model scores each transcript span against the conversation's moving highlight, keeps what still matters verbatim, tombstones the rest — restorable on demand.

## Stack

- Python 3.11+ (stdlib only — no runtime deps)
- TypeSafe **Jev** System One model (`jev-latest`) for calibrated span scoring; heuristic scorer works offline
- MCP (stdio JSON-RPC) restore server — `context-restore` for tombstone rehydration
- Harness adapters: Claude Code (PreCompact + SessionStart), Codex and OpenCode next

## How it works

Summarization compaction mangles the exact things agents need — code, errors, paths, diffs. jev-compact is a **retention filter**, not a summarizer:

1. **Segment** the transcript into spans (user turn, assistant block, tool call+result).
2. **Highlight** the moving topic — last user intent + last assistant action + active files. Drift (moon research → lidar code) moves the highlight; scoring follows it.
3. **Score** every span on two axes via Jev (`relevance_to_current`, `load_bearing`) — or the built-in heuristic scorer with zero keys.
4. **Knapsack** under a token budget: top spans kept verbatim, mid band tombstoned (one-line receipt), tail dropped. Full transcript stays on disk — nothing is destroyed.
5. **Restore** any tombstoned span through the `context-restore` MCP server when the conversation swings back.

## Local Setup

```bash
# clone
git clone https://github.com/duketopceo/jev-compact
cd jev-compact

# install (editable, stdlib only)
pip install -e .

# env vars (optional — heuristic scorer needs none)
cp .env.example .env
# fill in .env

# compact a transcript
jev-compact compact --transcript session.jsonl --budget 8000

# run tests
python -m pytest tests/
```

## Deploy

Local tool — no deploy. Optional service mode: run `python mcp/restore_server.py` as an MCP server registered in your harness config.

## Docs

- `docs/design.md` — algorithm spec, scoring axes, adapter contract, harness matrix
- `adapters/` — per-harness wiring (Claude Code ready)
- See `AGENTS.md` for agent context.
