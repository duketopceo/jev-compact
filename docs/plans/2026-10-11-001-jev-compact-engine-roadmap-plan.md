---
title: "jev-compact engine program roadmap"
type: program-roadmap
status: proposed
date: 2026-10-11
origin: docs/research/2026-10-11-landscape.md
---

# jev-compact engine program roadmap

> Written by hand (`compound-engineering:ce-plan` not run; docs-only pass, small repo). It is the upstream half of `a0-plugin-jev-compact`'s roadmap: that plan's U1 (sync guard), U2 (eval harness) and U7 (de-duplicate) depend on units here. Claims checked against the code on 2026-10-11.

## Summary

The engine is the source of truth. Next work: prove retention, make the engine installable so the plugin stops vendoring it, and close adapter test gaps.

## Now / Next / Later

| ID | Unit | Horizon | Difficulty |
|---|---|---|---|
| U1 | Land docs PR #6 | Now | easy |
| U2 | Retention eval harness (offline first) | Now | medium |
| U3 | Verify or delete the native `/v1/systemone` scorer path | Now | easy |
| U4 | Adapter tests for Codex and OpenCode | Next | medium |
| U5 | Restore search tool (`search_spans`) | Next | medium |
| U6 | First tagged release and an installable package for the a0 plugin | Next | medium |
| U7 | Base-URL proxy adapter for harnesses without hooks | Later | hard |

## Units

### U1. Land PR #6
- Status: Now. Evidence: PR #6 (README adapters line) is open. **Difficulty**: easy. **Feasibility**: owner review. **Simpler alternative**: none.

### U2. Retention eval harness
- Status: Now, not started. Evidence: `tests/test_compact.py` checks mechanics (budget, tail, pins), not whether planted facts survive. A 23-span synthetic transcript run on 2026-10-11 (heuristic scorer, `--budget 400`) tombstoned the span range holding the bug diagnosis and commit hash (`s1-s4`) while the highlight was that same bug; the receipt preview still shows its first words, so it is restorable, but the fact left the context. One example, not a measurement.
- Goal: fixtures with planted facts (path, error string, decision) and probe checks: kept verbatim or reachable via a tombstone receipt, at several budgets, for the heuristic scorer. This is `a0-plugin-jev-compact` U2, built here first so the plugin can reuse it.
- Verification: deterministic pytest thresholds; a paid Jev comparison runs only through the `orch` wrapper and the `orchestral-eval-v3` key.
- **Difficulty**: medium. Realistic fixtures are the work; probes are substring checks.
- **Feasibility**: Factory's method uses LLM-graded probes ([source](https://factory.ai/news/evaluating-compression)); free substring probes are a weaker approximation.
- **Simpler alternative**: three hand-written fixtures asserting `load_bearing >= 0.8` spans are never tombstoned.

### U3. Verify or delete the native scorer path
- Status: Now. Evidence: `src/jev_compact/scorer.py` `_score_typesafe` (about 35 lines) posts to `/v1/systemone`, schema "per docs.typesafe.ai", unverified; the OpenRouter decisions path is verified live.
- Verification: a recorded live response with a TypeSafe key, or removal with tests still green.
- **Difficulty**: easy. **Feasibility**: needs a TypeSafe key the owner may not have.
- **Simpler alternative**: this is the simplification. Delete the native path and `_via == "typesafe"` branch; keep `heuristic` and OpenRouter.

### U4. Adapter tests
- Status: Next. Evidence: only `tests/test_claude_adapter.py` exists; `adapters/codex/hooks/*.py` (161 lines) and `adapters/opencode/jev-compact.ts` (114 lines) are untested.
- Verification: Codex hooks tested like the Claude ones; OpenCode needs a TS runner.
- **Difficulty**: medium. **Feasibility**: the Python hooks are easy to copy from the Claude tests; the TypeScript plugin needs `bun` or `node` in CI and an OpenCode host contract that was not verified here.
- **Simpler alternative**: test only the Codex hooks and mark the OpenCode adapter experimental in its README.

### U5. Restore search
- Status: Next. Evidence: `mcp/restore_server.py` offers `get_span`, `list_tombstones`, `get_highlight`, `list_sessions`; no search. Letta offers searchable recall.
- **Difficulty**: medium. Small code, but the plugin vendors the store; coordinate with its U1.
- **Feasibility**: none external; stay read-only and stdlib-only.
- **Simpler alternative**: skip it. Receipts already carry a `begins:` preview that `list_tombstones` returns.

### U6. First release
- Status: Next. Evidence: `gh release list` and `git tag` are empty; `pyproject.toml` is version 0.1.0 with a `jev-compact` script entry. The a0 plugin vendors `src/jev_compact` instead of depending on it.
- Verification: `python -m build` produces a wheel that installs and runs `jev-compact --version` in a clean venv; a tag `v0.1.0`.
- **Difficulty**: medium. **Feasibility**: Agent Zero installs plugins by git clone, so a plugin cannot `pip install` at load without a hook; PyPI publishing is an owner decision.
- **Simpler alternative**: keep vendoring and add the plugin's sync guard (its U1); skip packaging.

### U7. Base-URL proxy adapter
- Status: Later, design only (`adapters/README.md` row "Any base-url harness").
- **Difficulty**: hard. A local proxy rewriting API request bodies. **Feasibility**: provider payload formats differ and change; streaming must pass through.
- **Simpler alternative**: restore-only mode for such harnesses (the Devin row), which already works through MCP.

## Verdict

Keep as the engine of record; no merge into the plugin. Biggest simplification: U3, about 35 lines and one scorer mode.
