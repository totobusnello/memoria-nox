#!/usr/bin/env python3
"""Per-epoch non-main (coverage-side) id set straight from the serving log, no corpus.

Preserves as an artifact the computation that REVIEW-A-2026-10-04.md finding #6 ran by
hand. For each epoch: all ids in 10-row agent briefs (ids_controle), minus the month's
main-pool union taken from observed-main-from-log.json. Reports per-epoch size, whether
the set equals the 2026-08-24 reference set, and its min/max id.

usage: coverage-set-from-log.py SERVING_LOG OBSERVED_MAIN_JSON OUT_JSON
"""
import hashlib, json, sys
from collections import defaultdict
from datetime import datetime, timezone

serving, observed, out = sys.argv[1:4]
main_union = set(json.load(open(observed))["union_main_ids"])
all10 = defaultdict(set)
briefs = defaultdict(int)
for ln in open(serving):
    try:
        d = json.loads(ln)
    except json.JSONDecodeError:
        continue
    if not d.get("agent") or len(d.get("ids_controle") or []) != 10:
        continue
    all10[d["epoch"]] |= set(d["ids_controle"])
    briefs[d["epoch"]] += 1
ref_epoch = "2026-08-24"
ref = all10[ref_epoch] - main_union
res = {}
for ep in sorted(all10):
    s = all10[ep] - main_union
    res[ep] = {"briefs": briefs[ep], "distinct_all_10": len(all10[ep]),
               "distinct_non_main": len(s), "equals_ref": s == ref,
               "min_id": min(s) if s else None, "max_id": max(s) if s else None,
               "added_vs_ref": sorted(s - ref), "removed_vs_ref": sorted(ref - s)}
h = hashlib.sha256(open(serving, "rb").read()).hexdigest()
json.dump({"generated_by": "_sprint-2026-10-04/A-rc2/coverage-set-from-log.py",
           "generated_at": datetime.now(timezone.utc).isoformat(),
           "serving_log": serving, "serving_log_sha256": h,
           "main_union_from": observed, "main_union_size": len(main_union),
           "reference_epoch": ref_epoch, "reference_set_size": len(ref),
           "reference_ids": sorted(ref), "per_epoch": res}, open(out, "w"), indent=1)
print(f"-> {out}", file=sys.stderr)
