<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/brand/wordmark-dark.svg">
    <img alt="jev-compact" src="assets/brand/wordmark.svg" height="56">
  </picture>
</p>

[![M8ven Trust Index](https://m8ven.ai/badge/mcp/duketopceo/jev-compact)](https://m8ven.ai/mcp/duketopceo/jev-compact)

> Context compaction for agent harnesses: a decision-model scores each transcript span against the conversation's moving highlight, keeps what still matters verbatim, tombstones the rest — restorable on demand.

Status: v0.1.0, 53 offline tests, no tagged release yet. See [ROADMAP.md](ROADMAP.md).

```text
$ jev-compact compact --transcript session.json --budget 400 --scorer heuristic
CURRENT WORK:
Intent: Back to the lidar parser: add a regression test for frame 112 ...
========================================
[s0 · user_turn]
Why does the lidar parser crash on frame 112? Look at src/lidar/parse.py

[[s1-s4 tombstoned · 4 span(s) · assistant_text,user_turn · begins: Reading src/lidar/parse.py. The crash is a struct.error ...]]
...
--- 23 spans -> 12 kept (8 tombstone runs) · 1416 -> 479 tok (34%) · store .jev-compact/4e85494f5141

$ jev-compact restore --store .jev-compact --span s1-s4
```

<sub>Real output (trimmed) from a synthetic 23-span transcript with the offline heuristic scorer. It is a demonstration of the format, not a quality claim: see the roadmap for the retention eval.</sub>

## Stack

- Python 3.11+ (stdlib only — no runtime deps)
- TypeSafe **Jev** System One model (`jev-latest`) for calibrated span scoring; heuristic scorer works offline
- MCP (stdio JSON-RPC) restore server — `context-restore` for tombstone rehydration
- Harness adapters (`adapters/`): Claude Code (PreCompact + SessionStart), Codex (rollout transcript parser + PreCompact/SessionStart), OpenCode (`session.compacting` plugin)

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
- `adapters/` — per-harness wiring (Claude Code, Codex, OpenCode)
- See `AGENTS.md` for agent context.

## Known behaviors

**`--budget` is a target, not a hard cap.** The last `TAIL_KEEP` spans are
never scored out, and tombstone receipts add tokens back. A budget below the
tail size will still overshoot — `80 -> 82 tok` at `--budget 40` is expected,
not a bug. Check the printed `before -> after (n%)` line.

**`restore --store` takes the parent directory.** Pass `.jev-compact`, not
the session subdirectory: `latest_session()` scans for session dirs *under*
the path you give it.

## Contributing

Stdlib only for the core package; `pip install -e ".[dev]"` then `python -m pytest`.
Never delete source transcripts; tombstones must restore verbatim (see
[AGENTS.md](AGENTS.md)). Design direction and brand assets (a proposal,
pending owner sign-off): [DESIGN.md](DESIGN.md), [assets/brand/](assets/brand/).

## License

MIT, see [LICENSE](LICENSE).
