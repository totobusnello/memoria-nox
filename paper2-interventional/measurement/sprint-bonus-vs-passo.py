#!/usr/bin/env python3
"""
sprint-bonus-vs-passo.py — recomputes the "0.0946, 1.79x the largest adjacent step" of
Paper A §4.4 / §5.4 with the severity multiplier of the DEPOSITED production code.

Why (verification of Codex #14 on rc3, 2026-10-05): the sentence compares the bonus at the
largest w_min (4.4) with the largest adjacent gap of the pool (0.05272). The bonus was taken
from `replay-oportunidade.mjs:944,1014-1019`, which hardcodes the severity multiplier as
S1 -> 0.5, S2 -> 1.0. Production (`serving-brief-outcome.ts`, pinned b3a3b1a8..., the module the
dose replay itself imports) uses SEVERIDADE_PAIN = {S1: 0.25, S2: 0.5, ...} and
`w * P2_DELTA_CUT * sev`. The dose thresholds were produced by the production function; only
the summary ratio used the hardcoded one.

Inputs, all in the repo (read-only):
  ../serving-brief-outcome.ts            P2_DELTA_CUT and SEVERIDADE_PAIN, parsed from source
  ../out/limiar-17.json                  fine dose grid over the 17 states (rowid cut)
  ../out/gaps.json                       largest adjacent in-stratum gap, one state (inclusive cut)
  ../p2-verdict-frame-2026-08-26.csv     severity label of each designated chunk

Output: ../out/BONUS-VS-STEP-2026-10-05.json (with --out)
"""
import argparse
import csv
import json
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    a = ap.parse_args()

    src = open(os.path.join(RAIZ, "serving-brief-outcome.ts"), encoding="utf8").read()
    delta = float(re.search(r"export const P2_DELTA_CUT = ([0-9.]+);", src).group(1))
    bloco = re.search(r"const SEVERIDADE_PAIN[^{]*\{([^}]*)\}", src).group(1)
    sev = {k: float(v) for k, v in re.findall(r"(S\d):\s*([0-9.]+)", bloco)}

    lim = json.load(open(os.path.join(RAIZ, "out", "limiar-17.json")))
    grid = sorted({r["w"] for r in lim["dose"]["tabela"]})
    first = {}
    for r in lim["dose"]["detalhe"]:
        k = (r["ts"], r["agent"])
        if r["churn"] > 0 and k not in first:
            first[k] = (r["w"], r["would_enter"])
    if len(first) != 17:
        print(f"expected 17 states with a threshold, got {len(first)}", file=sys.stderr)
        return 1
    wmax = max(w for w, _ in first.values())
    prev = max(g for g in grid if g < wmax)

    frame = {}
    with open(os.path.join(RAIZ, "p2-verdict-frame-2026-08-26.csv"), newline="") as f:
        for row in csv.reader(f):
            if len(row) >= 3 and row[2].isdigit():
                frame[int(row[2])] = row[1]

    gaps = json.load(open(os.path.join(RAIZ, "out", "gaps.json")))["gaps"]
    gmax = gaps["sub_pool_global"]["todos_os_pares"]["gap_max"]

    estados = []
    for (ts, ag), (w, ent) in sorted(first.items()):
        if w != wmax:
            continue
        for cid in ent:
            s = frame.get(cid)
            b_prod = w * delta * sev[s]
            b_prev = prev * delta * sev[s]
            estados.append({
                "ts": ts, "agent": ag, "w_min": w, "grid_bracket": [prev, w], "entering_id": cid,
                "severity": s, "multiplier_production": sev[s],
                "bonus_at_w_min_production": round(b_prod, 6),
                "bonus_bracket_production": [round(b_prev, 6), round(b_prod, 6)],
                "ratio_to_largest_adjacent_gap_production": round(b_prod / gmax, 4),
                "bonus_at_w_min_harness_hardcoded_0.5": round(w * delta * 0.5, 6),
                "ratio_harness_published": round(w * delta * 0.5 / gmax, 4),
            })

    out = {
        "script": "measurement/sprint-bonus-vs-passo.py",
        "P2_DELTA_CUT": delta,
        "SEVERIDADE_PAIN_production": sev,
        "harness_multiplier_hardcoded": {"S1": 0.5, "S2": 1.0, "where": "replay-oportunidade.mjs:944,1014-1019"},
        "largest_adjacent_gap": {"value": gmax, "scope": "one state, t_ref " + gaps["t_ref"] + ", inclusive serve-state cut, global sub-pool, all pairs"},
        "w_min_scope": "17 states of p2-serving-CLOSED-WINDOW, rowid cut (limiar-17.json)",
        "w_min_max": wmax,
        "states_at_w_min_max": estados,
        "published": {"bonus": 0.0946, "ratio": 1.79},
    }
    s = json.dumps(out, indent=1, ensure_ascii=False)
    if a.out:
        open(a.out, "w").write(s + "\n")
    print(s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
