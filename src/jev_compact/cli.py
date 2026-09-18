"""jev-compact CLI.

  jev-compact compact   --transcript T [--budget N] [--scorer auto|jev|heuristic]
                        [--store DIR] [--out FILE] [--json]
  jev-compact highlight --transcript T
  jev-compact restore   --store DIR [--session ID] --span s4 | s4-s9
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from . import __version__, compact as engine, highlight as hl, scorer, spans, store, transcript

log = logging.getLogger("jev-compact")
DEFAULT_BUDGET = 8000


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="jev-compact")
    ap.add_argument("--version", action="version", version=__version__)
    ap.add_argument("-v", "--verbose", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("compact", help="compact a transcript")
    c.add_argument("--transcript", type=Path, required=True)
    c.add_argument("--budget", type=int, default=DEFAULT_BUDGET)
    c.add_argument("--scorer", choices=["auto", "jev", "heuristic"], default="auto")
    c.add_argument("--store", type=Path, default=Path(".jev-compact"))
    c.add_argument("--out", type=Path)
    c.add_argument("--json", action="store_true", help="print stats as JSON")

    h = sub.add_parser("highlight", help="print the moving highlight")
    h.add_argument("--transcript", type=Path, required=True)

    r = sub.add_parser("restore", help="rehydrate a tombstoned span range")
    r.add_argument("--store", type=Path, default=Path(".jev-compact"))
    r.add_argument("--session", help="session id (default: latest)")
    r.add_argument("--span", required=True, help="s4 or s4-s9")
    r.add_argument("--list", action="store_true", help="list tombstones instead")

    args = ap.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(name)s: %(message)s",
    )

    if args.cmd == "highlight":
        sp = _load_spans(args.transcript)
        print(hl.extract(sp).text)
        return 0
    if args.cmd == "restore":
        return _restore(args)
    return _compact(args)


def _load_spans(path: Path) -> list[spans.Span]:
    if not path.is_file():
        _die(f"transcript not found: {path}")
    events = transcript.load(path)
    if not events:
        _die(f"no events parsed from {path}")
    return spans.segment(events)


def _compact(args: argparse.Namespace) -> int:
    sp = _load_spans(args.transcript)
    highlight = hl.extract(sp)
    sc = scorer.resolve(args.scorer, total_spans=len(sp))
    result = engine.compact(sp, highlight, sc, args.budget)

    session = store.session_id_for(args.transcript)
    st = store.SpanStore(args.store, session)
    st.save(sp, highlight, result.tombstoned, args.transcript)

    if args.out:
        args.out.write_text(result.text + "\n", encoding="utf-8")
    else:
        print(result.text)
    stats = {
        "session": session,
        "spans": result.stats["spans"],
        "kept": result.stats["kept"],
        "tombstone_runs": result.stats["tombstone_runs"],
        "tokens_before": result.tokens_before,
        "tokens_after": result.tokens_after,
        "ratio": result.stats["ratio"],
    }
    if args.json:
        print(json.dumps(stats, indent=1), file=sys.stderr)
    else:
        print(
            f"\n--- {stats['spans']} spans -> {stats['kept']} kept "
            f"({stats['tombstone_runs']} tombstone runs) · "
            f"{stats['tokens_before']} -> {stats['tokens_after']} tok "
            f"({stats['ratio'] * 100:.0f}%) · store {args.store}/{session}",
            file=sys.stderr,
        )
    return 0


def _restore(args: argparse.Namespace) -> int:
    session = args.session or store.latest_session(args.store)
    if session is None:
        _die(f"no sessions under {args.store}")
    st = store.SpanStore(args.store, session)
    if args.list:
        for t in st.list_tombstones():
            print(f"{t['range']}: {t['preview']}")
        return 0
    text = st.get_range(args.span)
    if text is None:
        _die(f"span {args.span} not found in session {session}")
    print(text)
    return 0


def _die(msg: str) -> None:
    print(f"jev-compact: {msg}", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    sys.exit(main())
