#!/usr/bin/env python3
"""Descriptive tables the manuscript cites that `lme-analyze.py` does not print.

Keyless and read-only: it reads `runs/confirm-2026-11-04/rows.ndjson` and `v13-manifest.json`
and prints. Nothing here is a registered contrast; the manuscript labels every number from this
script as descriptive.

    python3 -I paper3-construction/manuscript-tables.py [run_dir]

Table A: judge-1 and judge-2 accuracy and mean served characters per cell, on the 242
confirmatory instances only (the rows file also carries the 31 counterfactual variants, marked
by `variant != qid`, which are excluded here).

Table B: primary-cell accuracy split by how many annotated evidence sessions the 0.240 cut kept
in cell 00 (none / some / all). The split is a property of the instance and the cut, fixed
before any answer is read, so it does not condition on the outcome.
"""
import collections
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
run = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "runs/confirm-2026-11-04"
confirm = set(json.loads((HERE / "v13-manifest.json").read_text())["confirm"])
rows = [json.loads(l) for l in (run / "rows.ndjson").read_text().splitlines() if l.strip()]
prim = [r for r in rows if r["variant"] == r["qid"] and r["qid"] in confirm]

by = collections.defaultdict(list)
for r in prim:
    by[r["cell"]].append(r)

assert len(by["00"]) == len(by["11"]) == len(confirm) == 242, "expected 242 instances per primary cell"


def acc(rs, key="correct"):
    return sum(bool(r[key]) for r in rs) / len(rs)


print("A. cells on the 242 (variants excluded)")
print(f"   {'cell':<9}{'n':>4}{'judge1':>8}{'judge2':>8}{'mean chars':>12}")
for c in sorted(by):
    rs = by[c]
    chars = sum(r["served_chars"] for r in rs) / len(rs)
    print(f"   {c:<9}{len(rs):>4}{acc(rs):>8.3f}{acc(rs, 'correct_j2'):>8.3f}{chars:>12,.0f}")

c00 = {r["qid"]: r for r in by["00"]}
groups = {
    "none kept": {q for q, r in c00.items() if r["evidence_kept"] == 0},
    "some kept": {q for q, r in c00.items() if 0 < r["evidence_kept"] < r["evidence_total"]},
    "all kept": {q for q, r in c00.items() if r["evidence_kept"] == r["evidence_total"]},
}
assert sum(len(s) for s in groups.values()) == 242

print("\nB. judge-1 accuracy by evidence sessions the 0.240 cut kept (cell 00)")
print(f"   {'group':<11}{'n':>4}" + "".join(f"{c:>8}" for c in ("00", "01", "10", "11")))
for name, s in groups.items():
    vals = "".join(f"{acc([r for r in by[c] if r['qid'] in s]):>8.3f}" for c in ("00", "01", "10", "11"))
    print(f"   {name:<11}{len(s):>4}{vals}")
