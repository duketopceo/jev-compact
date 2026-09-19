# jev-compact — design

Retention-filter compaction for agent transcripts. Instead of
summarizing everything into a blob (lossy: code, errors, paths, exact
values get paraphrased away), jev-compact *selects* what stays verbatim.

## Pipeline

```
transcript → segment → highlight → score → knapsack → emit + store
```

1. **Segment** (`spans.py`) — events grouped into spans: user turn,
   assistant text, tool call+result (atomic pair). Never line-level:
   partial code is worse than a tombstone.
2. **Highlight** (`highlight.py`) — moving spec of current work: last
   user intent + last assistant action + active file paths. Drift is the
   feature: when the topic moves, the highlight moves, and every span's
   relevance is scored against *now*, not the session average.
3. **Score** (`scorer.py`) — each span gets two axes in [0,1]:
   - `relevance` — matters for the work in the highlight
   - `load_bearing` — still-needed setup facts even if off-topic
     (chosen approach, paths, fixed errors, issue/commit refs)
   Backends: `HeuristicScorer` (offline, deterministic) or `JevScorer`
   (TypeSafe Jev primitives — `score` + `noul` — calibrated, and output
   tokens are free on Jev's pricing).
4. **Knapsack** (`compact.py`) — rank by `0.65·rel + 0.35·load`, greedy
   fill under token budget. Hard rules: last `TAIL_KEEP` spans always
   kept (live edge); `load ≥ 0.8` pinned regardless of budget; dropped
   contiguous runs emit one tombstone receipt each.
5. **Store + restore** (`store.py`, `mcp/restore_server.py`) — full
   spans persist at `.jev-compact/<session>/` (atomic 0600 writes).
   Tombstones are receipts, not deletions — `get_span` rehydrates any
   range verbatim via MCP.

## Why a decision model

Jev returns typed answers (choice/score/noul) with calibrated
probabilities — exactly what retention triage needs, and output is free.
It cannot write prose, which is fine: tombstones are mechanical, the
highlight is heuristic extraction, nothing here needs generated text.
A summarizer would be the wrong tool; a classifier is the right one.

## Scoring questions sent to Jev

- `rel` (score 0–10): relevance of the span to the current-work highlight
- `load` (noul): probability the span carries facts still needed to
  continue, even if off-topic

Two questions per span, independent — the System One "ask together"
pattern. 32K model context fits highlight + span comfortably; spans are
bounded to a 1.5KB view for scoring (full text retained in store).

## Drift and resurrection

Pure recency weighting deletes early topics permanently — wrong, since
conversations swing back. Tombstones keep a one-line receipt in context;
a rescore or explicit `get_span` call restores the original text from
the store. Compaction is therefore non-destructive end to end.

## Open questions (tracked)

- Verify TypeSafe `/v1/systemone` request/response field names against a
  live key (written from public docs). TypeSafe models are NOT served
  on OpenRouter — the OpenRouter path scores with a generic chat model
  (`JEV_OPENROUTER_MODEL`, verified live on llama-3.2-3b 2026-09-19).
- Batch question calls per request once the API shape is confirmed.
- Codex compact hooks intentionally do not support `decision:"block"`
  (openai/codex#19905) — the Codex adapter is augment-posture by
  design. `continue:false` stops compaction without injecting anything,
  which only makes auto-compaction retry.
- Dependency-closure pass: rescore "is span X needed to understand the
  kept set?" — likely unnecessary at span granularity; revisit with data.
