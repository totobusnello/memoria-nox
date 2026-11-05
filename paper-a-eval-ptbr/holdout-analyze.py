#!/usr/bin/env python3
"""Paper A, H-A1 (PREREGISTRATION.md §4): pooled minus strict nDCG@10 on the holdout. Keyless.

  python3 -I holdout-analyze.py <score.json> <labels.json> <holdout.jsonl> <commitment.json> <rescore.txt>

score.json      eval/run-gold-eval.mjs output (rows[].ranked, rows[].gold_ids, summary.ndcg_at_10)
labels.json     eval/judge-relevance.py output, JUDGE_MODE=full ({"meta", "rows"})
holdout.jsonl   the private holdout (stratum, overlap, gold chunk id per query)
commitment.json HOLDOUT-COMMITMENT.json as pushed before any ranking (n, per-stratum counts, sha256)
rescore.txt     printed output of audits/2026-10-27-v3-rescore.py on the same score and labels

Definitions copied from audits/2026-10-27-v3-rescore.py at p > 0.5, K = 10: strict = gold only,
ideal = |gold| capped at K; pooled = gold or judged relevant at p > 0.5, ideal = |that set| capped
at K. Both are complete scoring procedures, denominators included: pooled minus strict is the
DIRECTIONAL contrast between two annotation protocols, not a correction of one by the other. It can
be negative (a newly judged relevant document raises the ideal), and the descriptive part reports
how often it is.

INPUT CONTRACT, checked before any number is printed; exit 1 on the first violation:
  * the holdout's sha256 equals the commitment's, its n and per-stratum counts equal the
    commitment's, and its query ids are unique;
  * score.json has exactly one row per holdout query, no row with an error, no duplicate chunk id
    in any ranking, and each row's gold is exactly the holdout's drawn chunk id;
  * labels.json was produced by the registered judge (gpt-6-luna) at threshold 0.5 with 6,000
    characters per chunk and 0 errors; no (query, chunk) pair appears twice; every probability is
    a number in [0, 1]; every returned top-10 pair is labelled;
  * strict and pooled means reproduce run-gold-eval's mean and the interval v3-rescore.py printed,
    within 0.0005 (a second implementation must agree with the registered one).
A ranking shorter than K is allowed and counted.

Interval: 10,000 bootstrap resamples, seed 20261105, resampling queries WITHIN each stratum so
every replicate keeps the registered quotas.
"""
import hashlib
import json
import math
import random
import re
import sys

K, THRESH, SEED, B, MARGIN, MIN_STRATUM = 10, 0.5, 20261105, 10000, 0.10, 5
JUDGE, CHUNK_CHARS = "gpt-6-luna", 6000


def dcg(rels):
    return sum(r / math.log2(i + 2) for i, r in enumerate(rels))


def fail(msg):
    sys.exit("INPUT CONTRACT FAIL: " + msg)


def main(score_p, labels_p, holdout_p, commit_p, rescore_p):
    commit = json.load(open(commit_p))
    hb = open(holdout_p, "rb").read()
    if hashlib.sha256(hb).hexdigest() != commit["holdout_sha256"]:
        fail("holdout sha256 differs from the commitment")
    meta = {}
    for l in hb.decode("utf-8").splitlines():
        h = json.loads(l)
        if int(h["query_id"]) in meta:
            fail(f"duplicate query id {h['query_id']}")
        meta[int(h["query_id"])] = h
    if len(meta) != commit["n"]:
        fail(f"holdout has {len(meta)} queries, commitment says {commit['n']}")
    per_st = {}
    for h in meta.values():
        per_st[h["stratum"]] = per_st.get(h["stratum"], 0) + 1
    if per_st != commit["per_stratum"]:
        fail(f"per-stratum counts {per_st} differ from the commitment {commit['per_stratum']}")

    d = json.load(open(score_p))
    rows = d["rows"]
    ids = [int(r["query_id"]) for r in rows]
    if sorted(ids) != sorted(meta) or len(set(ids)) != len(ids):
        fail(f"score rows {len(ids)} do not match the holdout's {len(meta)} query ids one to one")
    short = 0
    for r in rows:
        if r.get("error") or r.get("skipped") or r.get("ndcg") is None:
            fail(f"query {r['query_id']} has no valid score ({r.get('error') or r.get('skipped')})")
        rk = r["ranked"][:K]
        if len(set(rk)) != len(rk):
            fail(f"query {r['query_id']}: duplicate chunk id in the ranking")
        short += len(rk) < K
        want = {int(g["chunk_id"]) for g in meta[int(r["query_id"])]["gold"]}
        if set(map(int, r["gold_ids"])) != want:
            fail(f"query {r['query_id']}: scored gold {r['gold_ids']} is not the drawn chunk {sorted(want)}")

    lab = json.load(open(labels_p))
    lm = lab.get("meta", {})
    if (lm.get("judge"), lm.get("threshold"), lm.get("chunk_chars"), lm.get("n_errors")) != \
            (JUDGE, THRESH, CHUNK_CHARS, 0):
        fail(f"label meta {lm.get('judge')}, {lm.get('threshold')}, {lm.get('chunk_chars')}, "
             f"errors {lm.get('n_errors')} is not the registered judge configuration")
    P = {}
    for x in lab["rows"]:
        key = (int(x["query_id"]), int(x["chunk_id"]))
        if key in P:
            fail(f"pair {key} labelled twice")
        p = x.get("prob_contem_resposta")
        if not isinstance(p, (int, float)) or not (0.0 <= p <= 1.0) or math.isnan(p):
            fail(f"pair {key} has probability {p!r}")
        P[key] = p
    tot = sum(len(r["ranked"][:K]) for r in rows)
    jud = sum((int(r["query_id"]), int(c)) in P for r in rows for c in r["ranked"][:K])
    if jud != tot:
        fail(f"top-{K} judged {jud}/{tot}")
    print(f"input contract PASS · {len(rows)} queries · {per_st} · top-{K} judged {jud}/{tot}"
          f" · rankings shorter than {K}: {short}")

    per = []
    for r in rows:
        q = int(r["query_id"])
        gold, ranked = set(map(int, r["gold_ids"])), [int(c) for c in r["ranked"][:K]]
        relset = gold | {c for (qq, c), v in P.items() if qq == q and v > THRESH}
        i_s, i_p = min(len(gold), K), min(len(relset), K)
        s = dcg([1 if c in gold else 0 for c in ranked]) / dcg([1] * i_s)
        p = dcg([1 if c in relset else 0 for c in ranked]) / dcg([1] * i_p)
        per.append((q, s, p))
    ms = sum(s for _, s, _ in per) / len(per)
    mp = sum(p for _, _, p in per) / len(per)
    exp = d["summary"]["ndcg_at_10"]
    m = re.search(r"honest interval \[([\d.]+) · ([\d.]+)\]", open(rescore_p).read())
    ok = (m is not None and abs(ms - exp) < 5e-4 and abs(ms - float(m.group(1))) < 5e-4
          and abs(mp - float(m.group(2))) < 5e-4)
    print(f"CONTROL strict {ms:.4f} (run-gold-eval {exp:.4f}) · v3-rescore "
          f"[{m.group(1) if m else '?'} · {m.group(2) if m else '?'}] vs ours [{ms:.4f} · {mp:.4f}]"
          f" -> {'PASS' if ok else 'FAIL'}")
    if not ok:
        fail("this recomputation does not reproduce the registered tooling")

    diffs = {q: p - s for q, s, p in per}
    by_st = {}
    for q in diffs:
        by_st.setdefault(meta[q]["stratum"], []).append(diffs[q])
    # a stratum with fewer than MIN_STRATUM queries gives the within-stratum bootstrap nothing to
    # resample, and the interval collapses to a point (the 6-query smoke printed [x, x] -> holds)
    small = {st: len(v) for st, v in by_st.items() if len(v) < MIN_STRATUM}
    if small:
        fail(f"strata too small for a within-stratum bootstrap: {small}")
    est = sum(diffs.values()) / len(diffs)
    rng = random.Random(SEED)
    boots = []
    for _ in range(B):
        tot_ = 0.0
        for st in sorted(by_st):
            v = by_st[st]
            tot_ += sum(rng.choice(v) for _ in v)
        boots.append(tot_ / len(diffs))
    boots.sort()
    lo, hi = boots[int(0.025 * B)], boots[int(0.975 * B) - 1]
    reading = "holds" if lo >= MARGIN else "does not hold" if hi < MARGIN else "inconclusive"
    print(f"\nH-A1: pooled - strict = {est:+.4f} [{lo:+.4f}, {hi:+.4f}], {len(diffs)} queries, "
          f"stratified bootstrap (margin {MARGIN}) -> {reading}")
    print(f"      strict {ms:.4f} · pooled {mp:.4f}")
    pos = sum(v > 0 for v in diffs.values())
    neg = sum(v < 0 for v in diffs.values())
    print(f"\nper-query direction (descriptive): pooled > strict {pos} · equal {len(diffs) - pos - neg}"
          f" · pooled < strict {neg}")
    ov = sorted(meta[q]["overlap"] for q in diffs)
    cut = (ov[len(ov) // 3], ov[2 * len(ov) // 3])
    print("\nby question-side lexical overlap tercile (descriptive):")
    for name, f in (("low", lambda o: o < cut[0]), ("mid", lambda o: cut[0] <= o < cut[1]),
                    ("high", lambda o: o >= cut[1])):
        sub = [(s, p) for q, s, p in per if f(meta[q]["overlap"])]
        if sub:
            print(f"  {name:4s} n={len(sub):3d} strict {sum(s for s, _ in sub)/len(sub):.4f} "
                  f"pooled {sum(p for _, p in sub)/len(sub):.4f}")
    print("\nby stratum (descriptive):")
    for st in sorted(by_st):
        sub = [(s, p) for q, s, p in per if meta[q]["stratum"] == st]
        print(f"  {st} n={len(sub):3d} strict {sum(s for s, _ in sub)/len(sub):.4f} "
              f"pooled {sum(p for _, p in sub)/len(sub):.4f}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 6:
        sys.exit(__doc__)
    sys.exit(main(*sys.argv[1:]))
