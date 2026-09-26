#!/usr/bin/env python3
"""Minimal stdio MCP client for the Blender official server.

Usage:
  python3 mcp_run.py @script.py            -> tools/call execute_blender_code
  python3 mcp_run.py '{"name": ..., "arguments": {...}}'   -> raw tool call
"""
import json
import os
import queue
import subprocess
import sys
import threading
import time

def find_launcher() -> str:
    candidates = []
    if os.environ.get("KIMI_BLENDER_PLUGIN"):
        candidates.append(os.path.join(os.environ["KIMI_BLENDER_PLUGIN"], "scripts"))
    candidates.append(os.path.join(os.path.expanduser(
        "~/Library/Application Support/kimi-desktop/daimon-share/daimon/runtime/"
        "kimi-code/home/plugins/managed/blender/scripts")))
    candidates.append(os.path.join(os.path.expanduser(
        "~/.local/share/kimi/plugins/managed/blender/scripts")))
    for scripts in candidates:
        launcher = os.path.join(scripts, "blender_mcp_launcher.py")
        if os.path.isfile(launcher):
            return launcher
    raise SystemExit("blender_mcp_launcher.py not found; set KIMI_BLENDER_PLUGIN to the plugin root")


LAUNCHER = find_launcher()


def main() -> int:
    arg = sys.argv[1]
    if arg.startswith("@"):
        with open(arg[1:], "r", encoding="utf-8") as f:
            code = f.read()
        call = {"name": "execute_blender_code",
                "arguments": {"code": code}}
    else:
        call = json.loads(arg)

    proc = subprocess.Popen(
        [sys.executable, LAUNCHER],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, bufsize=1,
    )
    out_q: queue.Queue = queue.Queue()
    err_tail: list[str] = []

    def pump_out():
        try:
            for line in proc.stdout:
                out_q.put(line)
        finally:
            out_q.put(None)

    def pump_err():
        for line in proc.stderr:
            err_tail.append(line)
            if len(err_tail) > 100:
                del err_tail[:20]

    threading.Thread(target=pump_out, daemon=True).start()
    threading.Thread(target=pump_err, daemon=True).start()

    def send(obj):
        proc.stdin.write(json.dumps(obj) + "\n")
        proc.stdin.flush()

    def read_reply(want_id, timeout=300):
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"timeout waiting for id={want_id}")
            line = out_q.get(timeout=remaining)
            if line is None:
                raise EOFError("server exited; stderr=" + "".join(err_tail)[-2000:])
            msg = json.loads(line)
            if msg.get("id") == want_id:
                return msg

    send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "kimi-blender-runner", "version": "0.1"},
    }})
    init = read_reply(1, 60)
    if "error" in init:
        print("INIT_ERROR:", json.dumps(init["error"]))
        return 1
    send({"jsonrpc": "2.0", "method": "notifications/initialized"})
    send({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": call})
    called = read_reply(2, 600)
    result = called.get("result", called.get("error"))
    print(json.dumps(result, ensure_ascii=False, indent=1)[:8000])
    try:
        proc.terminate(); proc.wait(timeout=5)
    except Exception:
        proc.kill()
    return 0


if __name__ == "__main__":
    sys.exit(main())
