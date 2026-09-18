#!/usr/bin/env python3
"""context-restore — stdio MCP server (newline-delimited JSON-RPC).

Exposes tombstoned spans back to any MCP-capable harness:

  tools:
    get_span(span: "s4" | "s4-s9", session?: str) -> verbatim span text
    list_tombstones(session?: str)               -> [{range, receipt, preview}]
    get_highlight(session?: str)                 -> moving-highlight text

Config (any harness's MCP block):
  {"command": "python3", "args": ["mcp/restore_server.py"],
   "env": {"JEV_STORE_DIR": "/path/to/.jev-compact"}}
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from jev_compact import __version__, store  # noqa: E402

PROTOCOL_VERSION = "2024-11-05"
STORE_ROOT = Path(os.environ.get("JEV_STORE_DIR", ".jev-compact"))

TOOLS = [
    {
        "name": "get_span",
        "description": "Rehydrate a tombstoned span or span range (e.g. 's4' or 's4-s9') to its verbatim transcript text.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "span": {"type": "string", "description": "span id or range: s4, s4-s9"},
                "session": {"type": "string", "description": "session id (default: latest)"},
            },
            "required": ["span"],
        },
    },
    {
        "name": "list_tombstones",
        "description": "List tombstone receipts left by compaction: range, receipt text, and a preview of the first span.",
        "inputSchema": {
            "type": "object",
            "properties": {"session": {"type": "string"}},
        },
    },
    {
        "name": "get_highlight",
        "description": "Return the moving-highlight spec recorded at last compaction (what the conversation was about).",
        "inputSchema": {
            "type": "object",
            "properties": {"session": {"type": "string"}},
        },
    },
]


def _store(session: str | None) -> store.SpanStore | None:
    sid = session or store.latest_session(STORE_ROOT)
    return store.SpanStore(STORE_ROOT, sid) if sid else None


def _call(name: str, args: dict) -> str:
    st = _store(args.get("session"))
    if st is None:
        return f"no sessions under {STORE_ROOT}"
    if name == "get_span":
        return st.get_range(str(args["span"])) or "span not found"
    if name == "list_tombstones":
        rows = st.list_tombstones()
        return "\n".join(f"{t['range']}: {t['preview']}" for t in rows) or "none"
    if name == "get_highlight":
        return st.get_highlight() or "none recorded"
    return f"unknown tool: {name}"


def _respond(msg_id, result=None, error=None) -> None:
    out: dict = {"jsonrpc": "2.0", "id": msg_id}
    if error is not None:
        out["error"] = error
    else:
        out["result"] = result
    sys.stdout.write(json.dumps(out) + "\n")
    sys.stdout.flush()


def _tool_result(text: str) -> dict:
    return {"content": [{"type": "text", "text": text}]}


def handle(msg: dict) -> None:
    method = msg.get("method", "")
    msg_id = msg.get("id")
    if method == "initialize":
        _respond(
            msg_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "context-restore", "version": __version__},
            },
        )
    elif method == "tools/list":
        _respond(msg_id, {"tools": TOOLS})
    elif method == "tools/call":
        params = msg.get("params", {})
        try:
            text = _call(str(params.get("name", "")), params.get("arguments") or {})
            _respond(msg_id, _tool_result(text))
        except Exception as exc:  # tool errors go back as content, not crashes
            _respond(msg_id, _tool_result(f"error: {exc}"))
    elif method == "ping":
        _respond(msg_id, {})
    elif msg_id is not None:  # unknown request
        _respond(msg_id, error={"code": -32601, "message": f"no such method: {method}"})
    # notifications (no id) are ignored


def main() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(msg, dict):
            handle(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
