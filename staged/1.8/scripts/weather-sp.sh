#!/bin/bash
# weather-sp.sh — current + today's min/max for São Paulo via wttr.in
set -uo pipefail
curl -s --max-time 10 'wttr.in/São+Paulo?format=j1' | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    curr = d["current_condition"][0]
    today = d["weather"][0]
    cond = curr["weatherDesc"][0]["value"].strip()
    t_cur = curr["temp_C"]
    t_min = today["mintempC"]
    t_max = today["maxtempC"]
    print(f"São Paulo: {cond} +{t_cur}°C · min {t_min}°C / max {t_max}°C")
except Exception:
    print("Clima indisponível")
'
