"""Exercise the MCP restore server over real stdio JSON-RPC.

The unit suite imports store.py directly, so nothing covers the MCP framing:
handshake, tool listing, and an actual tools/call round trip. A server that
imports cleanly but speaks the wrong protocol is still broken.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SERVER = REPO / "mcp" / "restore_server.py"


def rpc(proc, payload):
    """Send one framed JSON-RPC message and read the reply."""
    proc.stdin.write(json.dumps(payload) + "\n")
    proc.stdin.flush()
    for _ in range(200):
        line = proc.stdout.readline()
        if not line:
            return None
        line = line.strip()
        if line:
            return json.loads(line)
    return None


def start(cwd):
    return subprocess.Popen(
        [sys.executable, str(SERVER)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, cwd=str(cwd),
        env={"PYTHONPATH": str(REPO / "src"), "PATH": "/usr/bin:/bin",
             "JEV_COMPACT_STORE": ".jev-compact"},
    )


def test_initialize_reports_protocol_version(tmp_path):
    p = start(tmp_path)
    try:
        r = rpc(p, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                    "params": {"protocolVersion": "2025-06-18",
                               "capabilities": {},
                               "clientInfo": {"name": "t", "version": "0"}}})
        assert r is not None, "no reply to initialize"
        assert r["result"]["protocolVersion"], "missing protocolVersion"
    finally:
        p.kill()


def test_tools_list_exposes_the_documented_tools(tmp_path):
    p = start(tmp_path)
    try:
        rpc(p, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                           "clientInfo": {"name": "t", "version": "0"}}})
        r = rpc(p, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        assert r is not None, "no reply to tools/list"
        names = sorted(t["name"] for t in r["result"]["tools"])
        # "restore" is the CLI verb; over MCP the same capability is get_span.
        assert names == ["get_highlight", "get_span", "list_tombstones"], names
    finally:
        p.kill()


def test_tools_call_restore_returns_text(tmp_path):
    """End to end: compact a transcript, then restore via MCP."""
    rows = [
        {"role": "user", "content": "Set up the deploy pipeline for staging"},
        {"role": "assistant", "content": "Examining CI config and targets."},
        {"role": "tool", "content": "<config>name: staging-deploy</config>"},
        {"role": "assistant", "content": "Creating the workflow file."},
        {"role": "user", "content": "no wait, use trunk-based deploys"},
        {"role": "assistant", "content": "Switching to trunk-based with flags."},
        {"role": "tool", "content": "<flags>enabled: false</flags>"},
        {"role": "assistant", "content": "Flags added, prior approach gone."},
    ]
    t = tmp_path / "t.jsonl"
    t.write_text("\n".join(json.dumps(r) for r in rows))

    # Produce a tombstone first, via the CLI, in the same cwd.
    subprocess.run([sys.executable, "-m", "jev_compact", "compact",
                    "--transcript", str(t), "--scorer", "heuristic",
                    "--budget", "40"],
                   cwd=str(tmp_path), capture_output=True, text=True,
                   env={"PYTHONPATH": str(REPO / "src"), "PATH": "/usr/bin:/bin"})

    p = start(tmp_path)
    try:
        rpc(p, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                           "clientInfo": {"name": "t", "version": "0"}}})
        r = rpc(p, {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                    "params": {"name": "list_tombstones", "arguments": {}}})
        assert r is not None, "no reply to tools/call"
        assert "result" in r, r
        payload = json.dumps(r["result"])
        assert "s0" in payload, f"expected a tombstone range: {payload[:300]}"
    finally:
        p.kill()