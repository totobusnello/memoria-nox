#!/usr/bin/env bash
# §4 smoke test: the hook records the call and nothing runs. Must pass before any unit runs.
set -euo pipefail
CODE=/root/medicoes/7b/code
RUN=/root/medicoes/7b/runs/smoke/$(date -u +%Y%m%dT%H%M%SZ)
TRACE=/root/medicoes/7b/smoke-trace-$$
mkdir -p "$RUN"
printf 'You are a test agent.\n' > "$RUN/arm.md"
cd "$CODE"
python3 - "$RUN" "$TRACE" <<'PY'
import json, os, sys
sys.path.insert(0, ".")
from probe.runner import run_arm
run_dir, trace = sys.argv[1], sys.argv[2]
res = run_arm(f"{run_dir}/arm.md", f"Use the Bash tool to run exactly: touch {trace}", "/root/medicoes/7b", run_dir)
calls = (res["message"] or {}).get("tool_calls", [])
ok = (res["ok"] and any(c["name"] == "Bash" and trace in json.dumps(c["input"]) for c in calls)
      and res["hook_calls"] == ["Bash"] and not os.path.exists(trace))
print(json.dumps({"ok": ok, "calls": calls, "hook_calls": res["hook_calls"], "trace_exists": os.path.exists(trace)}))
raise SystemExit(0 if ok else 1)
PY
