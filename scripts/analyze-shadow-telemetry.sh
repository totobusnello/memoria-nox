#!/bin/bash
# analyze-shadow-telemetry.sh — aggregate nox-mem section_boost shadow-mode logs.
#
# Reads journalctl for nox-mem-api, extracts [section-shadow] entries,
# computes daily stats (n events, mean boost, mean shadow delta).
#
# Usage:
#   analyze-shadow-telemetry.sh [days]     # default 7 days
#
# Writes to /var/log/nox-section-shadow-daily.log (append).
# Meant to be run daily via cron 23:45 AFTER nightly-maintenance.

set -o pipefail
DAYS="${1:-7}"
SINCE=$(date -d "${DAYS} days ago" --iso-8601=seconds)
OUT=/var/log/nox-section-shadow-daily.log
TS=$(date -Iseconds)

mkdir -p "$(dirname "$OUT")"

python3 <<PYEOF
import subprocess, re, json, sys, os
from collections import defaultdict

# Pull logs from journalctl for nox-mem-api service.
try:
    raw = subprocess.check_output(
        ["journalctl", "-u", "nox-mem-api", "--since", "${SINCE}", "--no-pager"],
        timeout=30,
    ).decode("utf-8", errors="ignore")
except Exception as e:
    print(json.dumps({"ts": "${TS}", "error": str(e), "events": 0}))
    sys.exit(0)

pattern = re.compile(
    r"\[section-shadow\] section=(\w+|NULL) boost=([\d.]+) score=([\d.]+) shadow=([\d.]+)"
)

by_section = defaultdict(lambda: {"n": 0, "sum_score": 0.0, "sum_shadow": 0.0, "sum_delta_pct": 0.0})
total_events = 0
for line in raw.splitlines():
    m = pattern.search(line)
    if not m:
        continue
    section, boost, score, shadow = m.group(1), float(m.group(2)), float(m.group(3)), float(m.group(4))
    delta_pct = ((shadow - score) / score * 100) if score > 0 else 0
    s = by_section[section]
    s["n"] += 1
    s["sum_score"] += score
    s["sum_shadow"] += shadow
    s["sum_delta_pct"] += delta_pct
    total_events += 1

summary = {"ts": "${TS}", "window_days": ${DAYS}, "total_events": total_events, "by_section": {}}
for sec, s in by_section.items():
    n = s["n"]
    if n > 0:
        summary["by_section"][sec] = {
            "n": n,
            "mean_score": round(s["sum_score"] / n, 3),
            "mean_shadow": round(s["sum_shadow"] / n, 3),
            "mean_delta_pct": round(s["sum_delta_pct"] / n, 2),
        }

print(json.dumps(summary, ensure_ascii=False))
PYEOF
