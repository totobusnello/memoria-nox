#!/usr/bin/env python3
"""Derive the holdout's per-stratum quotas from the v3 gold set (PREREGISTRATION.md §3).

  python3 -I derive-quotas.py <golden-queries-v3.jsonl> --out quotas.json

The v3 gold file is private (removed from the public tree on 2026-11-04); this script reads it
locally and writes only counts and its sha256. It replaced a constant typed by hand, which two
adversarial reviews found could not be reproduced: the hand count gave 15/10/9/8/12/6 for n = 60,
while this rule gives 15/9/9/8/12/7.

Rule: the 57 queries the scorer accepts (status accepted or accepted_marginal, as
eval/run-gold-eval.mjs reads them); for each, the SET of strata its gold source files fall in,
using holdout-draw.py's own stratum function; one count per (query, stratum) pair. Allocation by
largest remainder; ties in the remainder broken by stratum letter.
"""
import hashlib
import importlib.util
import json
import pathlib
import sys

N = 120
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from strata import stratum  # noqa: E402  (reads no file at import)


def main(path, dest):
    raw = pathlib.Path(path).read_bytes()
    gold = [json.loads(l) for l in raw.decode("utf-8").splitlines() if l.strip()]
    acc = [q for q in gold if q.get("status") in ("accepted", "accepted_marginal")]
    pairs, outside = {}, 0
    for q in acc:
        for s in {stratum(g["source_file"]) for g in q.get("gold", [])}:
            if s is None:
                outside += 1
            else:
                pairs[s] = pairs.get(s, 0) + 1
    total = sum(pairs.values())
    # integer arithmetic: in floats, 11*120/72 - 18 and 8*120/72 - 13 differ in the last bit and
    # an exact tie in the remainder was broken by rounding error instead of by the stated rule
    quota = {s: pairs[s] * N // total for s in pairs}
    rem = {s: pairs[s] * N % total for s in pairs}
    for s in sorted(pairs, key=lambda s: (-rem[s], s))[:N - sum(quota.values())]:
        quota[s] += 1
    out = {"n": N, "v3_sha256": hashlib.sha256(raw).hexdigest(), "v3_queries_accepted": len(acc),
           "pairs": dict(sorted(pairs.items())), "pairs_total": total,
           "pairs_outside_frame": outside, "quota": dict(sorted(quota.items()))}
    text = json.dumps(out, indent=1) + "\n"
    pathlib.Path(dest).write_text(text)
    print(text, end="")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 4 or sys.argv[2] != "--out":
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1], sys.argv[3]))
