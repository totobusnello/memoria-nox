#!/usr/bin/env bash
# Builds the isolated CLAUDE_CONFIG_DIR for the probe (spec §4). Run on the VPS after the login step.
set -euo pipefail
D=/root/.claude-7b-probe
CODE=/root/medicoes/7b/code
test -f "$D/.credentials.json" || { echo "not logged in: run the login step first"; exit 1; }
python3 "$CODE/scripts/capture_surface.py" "$D/surface.json"
cat > "$D/settings.json" <<JSON
{"hooks": {"PreToolUse": [{"matcher": "*", "hooks": [{"type": "command",
  "command": "python3 $CODE/runtime/deny_hook.py"}]}]}}
JSON
python3 - "$D" "$CODE" <<'PY'
import json, sys
d, code = sys.argv[1], sys.argv[2]
servers = json.load(open(f"{d}/surface.json"))
cfg = {"mcpServers": {s: {"command": "python3", "args": [f"{code}/runtime/stub_mcp.py", f"{d}/surface.json", s]}
                      for s in servers}}
json.dump(cfg, open(f"{d}/mcp-config.json", "w"), indent=1, sort_keys=True)
PY
cat "$D/settings.json" "$D/mcp-config.json" "$D/surface.json" | sha256sum | cut -d' ' -f1 > /root/medicoes/7b/config-dir.sha256
python3 - <<'PY'
import json
a = json.load(open("/root/.claude-7b-probe/.claude.json")).get("oauthAccount", {})
b = json.load(open("/root/.claude-nuvini-team/.claude.json")).get("oauthAccount", {})
same = a.get("accountUuid") == b.get("accountUuid")
print("probe account differs from agents' account:", not same)
raise SystemExit(1 if same or not a else 0)
PY
echo "config dir ready: $(cat /root/medicoes/7b/config-dir.sha256)"
