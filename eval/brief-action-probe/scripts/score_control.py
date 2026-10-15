#!/usr/bin/env python3
"""§7 positive control alone (run before the main phase, Toto 2026-10-15): prints the frozen pass rule."""
import json
import sys

sys.path.insert(0, __file__.rsplit("/scripts/", 1)[0])
from probe.control import actions_blob, score_control  # noqa: E402

R = "/root/medicoes/7b"
rows = [json.loads(l) for l in open(f"{R}/results-control.jsonl")]
sc = [json.loads(l) for l in open(f"{R}/control/scenarios.jsonl", encoding="utf-8")]
print(json.dumps(score_control(rows, sc)))
# per scenario, for reading only: does the planted value reach the actions or only the text?
for s in sc:
    rs = [r for r in rows if r["unit_id"] == s["scenario_id"] and r["ok"]]
    bp = [r["message"] for r in rs if r["arm"] == "BP"]
    print(s["scenario_id"], s["kind"], "BP actions", sum(s["planted"] in actions_blob(m) for m in bp), "/", len(bp),
          "BP text", sum(s["planted"] in (m.get("text") or "") for m in bp), "/", len(bp))
