#!/usr/bin/env python3
"""Arm WH (PREREGISTRATION.md, study W): a project Stop hook that asks once, before the agent ends,
whether a decision the user stated should be recorded. On the second stop (`stop_hook_active`)
it lets the agent end, so it can never loop. It writes nothing itself and names no task."""
import json
import sys

REASON = ("Before you finish: if the user stated a decision, rule or ownership in this task that "
          "should still hold next time, record it now with nox_mem_decision_set (stable slug key, "
          "with the reason). If nothing like that was stated, finish without writing anything.")

try:
    event = json.load(sys.stdin)
except Exception:
    event = {}
if event.get("stop_hook_active"):
    sys.exit(0)
print(json.dumps({"decision": "block", "reason": REASON}))
