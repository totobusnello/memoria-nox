#!/usr/bin/env python3
"""PreToolUse hook for the 7b probe: record the call, deny it. Nothing the agent asks for executes.
Exit 2 (block) when the event cannot be parsed, so a malformed event never lets a tool through."""
import json
import os
import sys
import time

try:
    ev = json.load(sys.stdin)
except Exception:
    print("7b probe: unparseable hook event; blocking", file=sys.stderr)
    sys.exit(2)
log = os.environ.get("PROBE_HOOK_LOG")
if log:
    with open(log, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": time.time(), "tool_name": ev.get("tool_name"),
                            "tool_input": ev.get("tool_input")}, ensure_ascii=False) + "\n")
print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                         "permissionDecisionReason": "7b probe: tools are not executed"}}))
