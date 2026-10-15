#!/usr/bin/env bash
# Builds the isolated CLAUDE_CONFIG_DIR for the probe (spec §4). Run on the VPS.
set -euo pipefail
D=/root/.claude-7b-probe
CODE=/root/medicoes/7b/code
mkdir -p "$D" && chmod 700 "$D"
# Auth: the agents' long-lived token is passed per run by env (probe.runner.oauth_token); nothing is
# written here, so the agents' credentials can never be refreshed or rotated by the probe.
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
echo "config dir ready: $(cat /root/medicoes/7b/config-dir.sha256)"
