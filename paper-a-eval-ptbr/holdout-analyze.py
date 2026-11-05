#!/usr/bin/env python3
"""Paper A, H-A1 (PREREGISTRATION.md §4): pooled minus strict nDCG@10 on the holdout. Keyless.

  python3 -I holdout-analyze.py <score.json> <labels.json> <holdout.jsonl> <rescore.txt>

score.json   from eval/run-gold-eval.mjs (rows[].ranked, rows[].gold_ids, summary.ndcg_at_10)
labels.json  from eval/judge-relevance.py (rows[].prob_contem_resposta), JUDGE_MODE=full
holdout.jsonl the private holdout, read only for each query's stratum and lexical overlap
rescore.txt  the printed output of audits/2026-10-27-v3-rescore.py on the same two files

Definitions are those of audits/2026-10-27-v3-rescore.py, copied, at the registered threshold
p > 0.5 and K = 10: strict = gold only, ideal |gold| capped at K; pooled = gold or judged
relevant, ideal |that set| capped at K. A query whose ideal is 0 in either arm is left out of the
paired difference (it cannot happen for strict when the gold resolved).

CONTROLS, and the script exits 1 without them, before printing any reading:
  * the judged fraction of the top-10 is 100% (the registered pooled arm judges all of it);
  * the strict mean reproduces run-gold-eval's summary.ndcg_at_10 within 0.0005;
  * strict and pooled means reproduce the "honest interval" v3-rescore.py printed, within 0.0005.
Copying a definition is a second implementation; the last control is what keeps it the same one.
"""
import json
import math
import random
import re
import sys

K, THRESH, SEED, B, MARGIN = 10, 0.5, 20261105, 10000, 0.10


def dcg(rels):
    return sum(r / math.log2(i + 2) for i, r in enumerate(rels))


def main(score_p, labels_p, holdout_p, rescore_p):
    d = json.load(open(score_p))
    rows = [r for r in d["rows"] if r.get("ndcg") is not None]
    lab = json.load(open(labels_p))
    P = {(int(r["query_id"]), int(r["chunk_id"])): r["prob_contem_resposta"]
         for r in lab["rows"] if r.get("prob_contem_resposta") is not None}
    meta = {}
    for l in open(holdout_p, encoding="utf-8"):
        h = json.loads(l)
        meta[int(h["query_id"])] = h
    tot = sum(len(r["ranked"][:K]) for r in rows)
    jud = sum((r["query_id"], c) in P for r in rows for c in r["ranked"][:K])
    print(f"queries scored {len(rows)} of {len(meta)} · judged fraction of the top-{K} "
          f"{jud}/{tot} = {jud / tot:.1%}")
    if jud != tot:
        sys.exit("CONTROL FAIL: the top-10 is not fully judged")
    per = []
    for r in rows:
        q, gold, ranked = r["query_id"], set(r["gold_ids"]), r["ranked"][:K]
        relset = gold | {c for (qq, c), v in P.items() if qq == q and v > THRESH}
        i_s, i_p = min(len(gold), K), min(len(relset), K)
        if i_s <= 0 or i_p <= 0:
            continue
        s = dcg([1 if c in gold else 0 for c in ranked]) / dcg([1] * i_s)
        p = dcg([1 if c in relset else 0 for c in ranked]) / dcg([1] * i_p)
        per.append((q, s, p))
    ms = sum(s for _, s, _ in per) / len(per)
    mp = sum(p for _, _, p in per) / len(per)
    exp = d["summary"]["ndcg_at_10"]
    m = re.search(r"honest interval \[([\d.]+) · ([\d.]+)\]", open(rescore_p).read())
    ok = (abs(ms - exp) < 5e-4 and m and abs(ms - float(m.group(1))) < 5e-4
          and abs(mp - float(m.group(2))) < 5e-4)
    print(f"CONTROL strict {ms:.4f} (run-gold-eval {exp:.4f}) · v3-rescore "
          f"[{m.group(1) if m else '?'} · {m.group(2) if m else '?'}] vs ours [{ms:.4f} · {mp:.4f}]"
          f" -> {'PASS' if ok else 'FAIL'}")
    if not ok:
        sys.exit("CONTROL FAIL: this recomputation does not reproduce the registered tooling")
    diffs = [p - s for _, s, p in per]
    est = sum(diffs) / len(diffs)
    rng = random.Random(SEED)
    boots = sorted(sum(rng.choice(diffs) for _ in diffs) / len(diffs) for _ in range(B))
    lo, hi = boots[int(0.025 * B)], boots[int(0.975 * B) - 1]
    reading = ("holds" if lo >= MARGIN else "does not hold" if hi < MARGIN else "inconclusive")
    print(f"\nH-A1: pooled - strict = {est:+.4f} [{lo:+.4f}, {hi:+.4f}] over {len(per)} queries "
          f"(margin {MARGIN}) -> {reading}")
    print(f"      strict {ms:.4f} · pooled {mp:.4f}")
    ov = sorted(meta[q]["overlap"] for q, _, _ in per)
    cut = (ov[len(ov) // 3], ov[2 * len(ov) // 3])
    print("\nby lexical-overlap tercile (descriptive):")
    for name, f in (("low", lambda o: o < cut[0]), ("mid", lambda o: cut[0] <= o < cut[1]),
                    ("high", lambda o: o >= cut[1])):
        sub = [(s, p) for q, s, p in per if f(meta[q]["overlap"])]
        if sub:
            print(f"  {name:4s} n={len(sub):2d} strict {sum(s for s, _ in sub)/len(sub):.4f} "
                  f"pooled {sum(p for _, p in sub)/len(sub):.4f}")
    print("\nby stratum (descriptive):")
    for st in sorted({meta[q]["stratum"] for q, _, _ in per}):
        sub = [(s, p) for q, s, p in per if meta[q]["stratum"] == st]
        print(f"  {st} n={len(sub):2d} strict {sum(s for s, _ in sub)/len(sub):.4f} "
              f"pooled {sum(p for _, p in sub)/len(sub):.4f}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    sys.exit(main(*sys.argv[1:]))
