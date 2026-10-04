"""Prove the reply deadline is real: a server that accepts input and never
answers must fail the test in bounded time, not hang CI forever."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_mcp_server import REPLY_TIMEOUT_S, rpc  # noqa: E402

import subprocess  # noqa: E402


def test_silent_server_fails_within_the_deadline():
    # A process that reads stdin forever and never writes to stdout.
    proc = subprocess.Popen(
        [sys.executable, "-c", "import sys\nfor _ in sys.stdin: pass"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True,
    )
    t0 = time.monotonic()
    try:
        try:
            rpc(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                       "params": {}})
        except AssertionError as e:
            elapsed = time.monotonic() - t0
            assert "no reply" in str(e)
            # Must be bounded, and must not be instant (proves we waited).
            assert REPLY_TIMEOUT_S <= elapsed < REPLY_TIMEOUT_S + 5, elapsed
        else:
            raise AssertionError("rpc() should have raised on a silent server")
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=5)