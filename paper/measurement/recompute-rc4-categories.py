#!/usr/bin/env python3
"""Recompute the §6.4 per-category table of the paper from the rc4 run outputs.

Why this script exists
----------------------
§6.4 of `paper/paper-tecnico-nox-mem.md` reports nDCG@10 per query category for the
rc4 embedding-matched run (nox-mem vs Mem0, both on gemini-embedding-001 3072-d) and
for the task-type ablation. The rc4 output files carry a `category` label written at
run time by `eval/q4-comparison/lib/category_labeler.py`, whose LoCoMo map permutes
LoCoMo's numeric categories 1-4 (1->single-hop, 2->multi-hop, 3->temporal,
4->open-domain). The questions support a different map, which §6.4 declares:

    1 -> multi-hop    2 -> temporal    3 -> open-domain    4 -> single-hop
    5 -> adversarial  (unchanged)

So `_aggregate.md` next to the outputs, and the labeler, give a different table
from the one the paper prints. This script is the paper's source for §6.4: it reads
the run outputs, re-derives each LoCoMo query's bucket from the dataset's NATIVE
integer category (not from the label stored in the output), keeps the LongMemEval
map unchanged, and scores nDCG@10 with the harness's own `aggregate.ndcg_at_k`.
It does not modify the labeler or the outputs.

Scorer fix (2026-10-04, manuscript v1.0.6)
------------------------------------------
`aggregate.ndcg_at_k` now credits each retrieved id once, at its first rank, without
re-padding the top 10. Before the fix, 3 LongMemEval queries of the rc4 Mem0 output
whose top 10 held the same gold id twice scored nDCG@10 above 1 (1.57, 1.57, 0.75 with
recall 2.0/2.0/1.5). Two printed §6.4 cells move: Mem0 temporal 0.4570 -> 0.4565 and
Mem0 adversarial 0.2955 -> 0.2930; every nox-mem cell and the ablation are unchanged
(no nox-mem output repeats an id). `PAPER` below holds the v1.0.6 values; the v1.0.5
printed values are kept in `PAPER_V105` for the record. Detail and the full old -> new
table: paper2-interventional/_sprint-2026-10-04/noxmem-v106/SCORER-FIX.md.

Inputs (read-only)
------------------
  eval/q4-comparison/output/rc4/nox_mem.json           rc4, nox-mem arm
  eval/q4-comparison/output/rc4/mem0.json              rc4, Mem0 arm
  eval/q4-comparison/output/rc4-ablation/nox_mem.json  task-type ablation, nox-mem arm
  eval/q4-comparison/cache/raw/locomo10.json           LoCoMo native categories

The three output files (11-44 MB each) match `*.json` in
`eval/q4-comparison/output/.gitignore`; their sha256 is recorded in
`eval/q4-comparison/MANIFESTO-LASTRO.json` (checked equal on 2026-10-04) and they are
backed up per that manifest. The output JSON records each input's sha256.

Two legs that must both hold before a number is written:
  (1) every LoCoMo label stored in an output equals OLD_MAP[native category] — so
      the question_id -> native category join is the right join;
  (2) the recomputed cells equal the figures printed in §6.4 (to 4 decimals).

Output: paper/measurement/out/recompute-rc4-categories.json (or --out PATH)

Usage:  python3 paper/measurement/recompute-rc4-categories.py [--out PATH]
Exit 0 = both legs hold; 1 = a leg failed (message on stderr).
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
Q4 = ROOT / "eval" / "q4-comparison"
sys.path.insert(0, str(Q4))
from aggregate import ndcg_at_k  # noqa: E402  (the harness's own metric)

K = 10

OLD_MAP = {1: "single-hop", 2: "multi-hop", 3: "temporal", 4: "open-domain", 5: "adversarial"}
DECLARED_MAP = {1: "multi-hop", 2: "temporal", 3: "open-domain", 4: "single-hop", 5: "adversarial"}

INPUTS = {
    "rc4/nox-mem": Q4 / "output" / "rc4" / "nox_mem.json",
    "rc4/mem0": Q4 / "output" / "rc4" / "mem0.json",
    "rc4-ablation/nox-mem": Q4 / "output" / "rc4-ablation" / "nox_mem.json",
}
LOCOMO_RAW = Q4 / "cache" / "raw" / "locomo10.json"
OUT = ROOT / "paper" / "measurement" / "out" / "recompute-rc4-categories.json"

# Figures printed in §6.4 (table and ablation sentence), checked to 4 decimals.
# v1.0.6 (scorer fix 2026-10-04): only the two rc4/mem0 cells marked below moved.
PAPER = {
    "rc4/nox-mem": {"single-hop": 0.5922, "multi-hop": 0.3641, "temporal": 0.5502,
                    "adversarial": 0.4370, "open-domain": 0.2592},
    "rc4/mem0": {"single-hop": 0.5607, "multi-hop": 0.3218, "temporal": 0.4565,   # v1.0.5: 0.4570
                 "adversarial": 0.2930, "open-domain": 0.2351},                   # v1.0.5: 0.2955
    "rc4-ablation/nox-mem": {"single-hop": 0.5773, "multi-hop": 0.3515, "temporal": 0.5571,
                             "adversarial": 0.4573, "open-domain": 0.2365},
}
# What v1.0.5 printed (scored with the pre-fix scorer that credited repeated ids).
PAPER_V105 = {**PAPER, "rc4/mem0": {**PAPER["rc4/mem0"], "temporal": 0.4570, "adversarial": 0.2955}}
PAPER_N = {"single-hop": 997, "multi-hop": 415, "temporal": 454, "adversarial": 524,
           "open-domain": 92}


def _list(v):
    if isinstance(v, list):
        return v
    if v in (None, "", "None"):
        return []
    return ast.literal_eval(v)


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def native_locomo() -> dict[str, int]:
    out = {}
    for s in json.loads(LOCOMO_RAW.read_text(encoding="utf-8")):
        for i, qa in enumerate(s["qa"]):
            out[f"{s['sample_id']}::q{i}"] = int(qa["category"])
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT), help=f"output JSON (default {OUT.relative_to(ROOT)})")
    out = Path(ap.parse_args().out).resolve()
    native = native_locomo()
    fails: list[str] = []
    result: dict = {"k": K, "scorer": "each retrieved id credited once (fix 2026-10-04)",
                    "declared_locomo_map": DECLARED_MAP, "inputs": {}, "cells": {}}
    for arm, path in INPUTS.items():
        payload = json.loads(path.read_text(encoding="utf-8"))
        result["inputs"][arm] = {"path": str(path.relative_to(ROOT)), "sha256": _sha256(path),
                                 "n_queries": len(payload["queries"])}
        per: dict[str, list[float]] = defaultdict(list)
        join_bad = 0
        for q in payload["queries"]:
            if q.get("error") not in (None, "", "None"):
                continue
            gold = set(_list(q.get("gold_chunk_ids")))
            if not gold:
                continue
            if q["dataset"] == "locomo":
                cat = native[q["question_id"]]
                if q.get("category") != OLD_MAP[cat]:
                    join_bad += 1
                bucket = DECLARED_MAP[cat]
            else:
                bucket = q.get("category") or "uncategorized"
            retrieved = [str(r.get("id") or "") for r in _list(q.get("results"))]
            per[bucket].append(ndcg_at_k(retrieved, gold, K))
        if join_bad:
            fails.append(f"{arm}: {join_bad} LoCoMo labels disagree with OLD_MAP[native] — "
                         f"the question_id join is wrong, no number is valid")
        cells = {b: {"n": len(v), "ndcg10": round(sum(v) / len(v), 6)} for b, v in sorted(per.items())}
        result["cells"][arm] = cells
        for b, want in PAPER[arm].items():
            got = cells.get(b, {}).get("ndcg10")
            if got is None or round(got, 4) != want:
                fails.append(f"{arm}/{b}: recomputed {got} != paper {want}")
            if cells.get(b, {}).get("n") != PAPER_N[b]:
                fails.append(f"{arm}/{b}: n {cells.get(b, {}).get('n')} != paper {PAPER_N[b]}")
    result["matches_paper_section_6_4"] = not fails
    result["paper_values_checked"] = "v1.0.6"
    result["v105_cells_that_moved"] = {
        f"{arm}/{b}": {"v1.0.5": PAPER_V105[arm][b], "v1.0.6": PAPER[arm][b]}
        for arm in PAPER for b in PAPER[arm] if PAPER_V105[arm][b] != PAPER[arm][b]}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if fails:
        print("\n".join(fails), file=sys.stderr)
        return 1
    try:
        shown = out.relative_to(ROOT)
    except ValueError:
        shown = out
    print(f"ok — §6.4 (v1.0.6 values) reproduced from the rc4 outputs; written {shown}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
