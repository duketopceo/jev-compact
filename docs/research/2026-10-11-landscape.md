# Landscape: jev-compact (2026-10-11)

Question: who else compacts agent context, and what is different about a retention filter with restore? Code read first (`src/jev_compact/*`, `mcp/restore_server.py`, `adapters/`, `docs/design.md`). The a0 wrapper, `a0-plugin-jev-compact`, has its own landscape file with more projects; this one covers the library and cites sources I re-read this session.

## What this repo is

A stdlib-only Python 3.11 engine (about 1,160 lines in `src/` and `mcp/`) plus per-harness adapters. It segments a transcript into spans, extracts a moving highlight, scores each span on `relevance` and `load_bearing` (heuristic offline, or the Jev decision model through OpenRouter), keeps top spans verbatim under a token budget, tombstones the rest with a one-line receipt, and stores full spans under `.jev-compact/<session>/` so a stdio MCP server can restore any range. Adapters exist for Claude Code, Codex and OpenCode (`adapters/README.md` matrix); 53 offline tests, none for the Codex or OpenCode adapters.

## Comparable approaches

| Approach | What it does | Better than this repo | Worse than this repo |
|---|---|---|---|
| Summarising compaction (Claude Code `/compact` and auto-compact; described in an [academic paper](https://arxiv.org/pdf/2608.01326) and a [vendor guide](https://www.morphllm.com/compaction-vs-summarization)) | The model writes a summary of earlier history | Built into the harness, no extra install; compresses hard | Lossy: sources say summaries paraphrase paths and error codes (vendor source, treat as marketing) |
| [LLMLingua](https://github.com/microsoft/LLMLingua) (MIT) | A small model prunes low-information tokens; claims up to 20x with minimal loss | Higher compression, task-agnostic | Its own example output garbles numbers and words, and the page makes no exact-value guarantee; no restore |
| Deletion-based compaction ([Morph](https://morphllm.com/context-compaction), vendor) | Drops low-value lines, keeps survivors verbatim | Same family as this repo; hosted product | Vendor benchmarks only; no span restore seen in the pages read |
| [Factory's anchored summarisation](https://factory.ai/news/evaluating-compression) | Structured summaries scored by probe questions | A published way to measure what compaction loses | Still summarisation; no verbatim restore. Numbers are vendor-run |
| [Letta (MemGPT)](https://docs.letta.com/guides/agents/architectures/memgpt) | Memory blocks, searchable recall and archival memory the agent edits | The agent can search its own history | A full memory architecture, not a drop-in for an existing harness |
| [Rate-distortion view of compaction](https://arxiv.org/pdf/2607.08032) | Theory paper on which information to keep under a budget | A frame for evaluating the knapsack | Theory only; not a tool |

## What users expect

- Automatic: compaction fires without thought (Claude Code behaviour). This repo's adapters hook `PreCompact`, so it rides the harness trigger rather than adding its own.
- Exact things survive: paths, error strings, diffs. That is this repo's whole premise.
- Proof. Factory frames retention as measurable; this repo has mechanics tests but no retention eval.

## What is unique here

1. Non-destructive by construction: tombstones are receipts, and `get_span` restores verbatim.
2. A moving highlight, so scoring follows topic drift rather than a session average.
3. One engine, several harness adapters, a contract documented in `adapters/README.md`.
4. Free to run: the heuristic scorer needs no key; Jev scoring costs about $0.000016 per span (AGENTS.md, measured 2026-09-19).

## Gaps and risks

- No retention eval, so quality claims rest on design reasoning. A quick synthetic run (heuristic scorer, 23 spans, budget 400) tombstoned a span range carrying a bug diagnosis and commit hash even though the highlight was that bug; one example, but it is the case an eval should catch.
- `JevScorer._score_typesafe` targets `/v1/systemone`, written from public docs and never verified with a key (AGENTS.md). The OpenRouter path is the verified one.
- Codex and OpenCode adapters have no tests.
- No release or tag exists; the a0 plugin vendors a copy of the engine, which has already drifted.
- Restore is by span id only; no search over tombstones.
