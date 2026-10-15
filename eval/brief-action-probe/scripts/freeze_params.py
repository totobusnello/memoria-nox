#!/usr/bin/env python3
"""§5: pilot A/A per stratum, validity ceiling, MDE by simulation; writes params.json (no content)."""
import hashlib
import json
import subprocess
import sys
from itertools import combinations

sys.path.insert(0, __file__.rsplit("/scripts/", 1)[0])
from probe import canon  # noqa: E402
from probe.stats import mde_from_curve, simulate_mde  # noqa: E402

R = "/root/medicoes/7b"
CODE = __file__.rsplit("/scripts/", 1)[0]
Q_GRID = [0.0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0]


def fsha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    man = [json.loads(l) for l in open(f"{R}/manifest.jsonl")]
    stratum = {u["unit_id"]: u["stratum"] for u in man}
    runs = [json.loads(l) for l in open(f"{R}/results-pilot.jsonl")]
    seqs, by_unit = {}, {}
    for r in runs:
        if r["ok"]:
            rid = (r["unit_id"], r["rep"])
            seqs[rid] = canon.serialize(r["message"])
            by_unit.setdefault(r["unit_id"], []).append(rid)
    params = {"canon_version": canon.CANON_VERSION, "canon_sha256": fsha(f"{CODE}/probe/canon.py"),
              "max_tokens": canon.MAX_TOKENS, "ceiling": 0.5, "pilot_aa": {}, "valid": {}, "mde": {},
              "mde_curve": {}, "seeds": {"manifest": 20261014, "mde": 7}}
    cache = {}

    def dist(a, b):
        k = (a, b) if a <= b else (b, a)
        if k not in cache:
            cache[k] = canon.divergence(seqs[a], seqs[b])
        return cache[k]

    for s in ("C", "H"):
        units = [ids for uid, ids in by_unit.items() if stratum[uid] == f"pilot_{s}" and len(ids) == 4]
        aa = [sum(dist(a, b) for a, b in combinations(ids, 2)) / 6 for ids in units]
        params["pilot_aa"][s] = sum(aa) / len(aa)
        params["valid"][s] = params["pilot_aa"][s] <= 0.5
        sizes = {}
        for u in man:
            if u["stratum"] == s:
                sizes[u["cluster"]] = sizes.get(u["cluster"], 0) + 1
        curve = simulate_mde(units, dist, list(sizes.values()), Q_GRID, n_sim=200, n_boot=1000, alpha=0.0125, seed=7)
        params["mde_curve"][s] = curve
        params["mde"][s] = mde_from_curve(curve)
        params[f"pilot_units_{s}"] = len(units)
    params["scaffold_sha256"] = "7b4b0820009bc170d178e0ce8bf16af5780a9d394e90bf678b2addee0dffb75c"
    params["config_dir_sha256"] = open(f"{R}/config-dir.sha256").read().strip()
    params["manifest_sha256"] = fsha(f"{R}/manifest.jsonl")
    params["h_requests_sha256"] = fsha(f"{R}/h_requests.jsonl")
    params["rubrics_sha256"] = fsha(f"{R}/rubrics.jsonl")
    params["control_sha256"] = fsha(f"{R}/control/scenarios.jsonl")
    params["cli_version"] = subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip()
    json.dump(params, open(f"{R}/params.json", "w"), indent=1)
    print(json.dumps({k: params[k] for k in ("pilot_aa", "valid", "mde")}))


if __name__ == "__main__":
    main()
