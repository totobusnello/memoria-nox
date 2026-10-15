#!/usr/bin/env python3
"""Stdio MCP server that replays a captured tool list for one server name and refuses every call.
Usage: stub_mcp.py <surface.json> <server-name>. Tool schemas are permissive stubs (spec §8 limit)."""
import json
import sys

surface, server = sys.argv[1], sys.argv[2]
with open(surface) as f:
    TOOLS = json.load(f)[server]


def send(o):
    sys.stdout.write(json.dumps(o) + "\n")
    sys.stdout.flush()


for line in sys.stdin:
    if not line.strip():
        continue
    msg = json.loads(line)
    mid, method = msg.get("id"), msg.get("method")
    if mid is None:
        continue
    if method == "initialize":
        pv = (msg.get("params") or {}).get("protocolVersion", "2025-06-18")
        send({"jsonrpc": "2.0", "id": mid, "result": {"protocolVersion": pv, "capabilities": {"tools": {}},
                                                       "serverInfo": {"name": server, "version": "7b-stub"}}})
    elif method == "tools/list":
        send({"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}})
    elif method == "tools/call":
        send({"jsonrpc": "2.0", "id": mid, "result": {
            "content": [{"type": "text", "text": "7b probe stub: not executed"}], "isError": True}})
    else:
        send({"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "method not found"}})
