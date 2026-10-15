#!/usr/bin/env python3
"""Tool surface for the stub MCP servers: every `mcp__<server>__<tool>` name the agents called between
2026-08-15 and 2026-10-15. Names only; schemas are permissive stubs, identical in every arm (spec §8)."""
import glob
import json
import sys

PROJ = "/root/.claude-nuvini-team/projects"
OUT = sys.argv[1] if len(sys.argv) > 1 else "/root/.claude-7b-probe/surface.json"
names = set()
for path in glob.glob(f"{PROJ}/-root--openclaw-workspace*/*.jsonl"):
    with open(path, errors="replace") as f:
        for raw in f:
            if '"tool_use"' not in raw or "mcp__" not in raw:
                continue
            try:
                o = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not ("2026-08-15" <= (o.get("timestamp") or "") < "2026-10-15"):
                continue
            for b in (o.get("message") or {}).get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_use" and str(b.get("name", "")).startswith("mcp__"):
                    names.add(b["name"])
surface = {}
for n in sorted(names):
    _, server, tool = n.split("__", 2)
    surface.setdefault(server, []).append({"name": tool, "description": f"{server} tool {tool}",
                                           "inputSchema": {"type": "object", "additionalProperties": True}})
with open(OUT, "w") as f:
    json.dump(surface, f, indent=1, sort_keys=True)
print(json.dumps({s: len(t) for s, t in surface.items()}))
