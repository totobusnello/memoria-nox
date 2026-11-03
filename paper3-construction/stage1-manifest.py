#!/usr/bin/env python3
"""Every draw the public-corpus leg makes, fixed by one seed BEFORE any arm runs (amendment v1.1).

v1.0 said "sampled by seed" and recorded no seed, no allocation rule and no subsample membership
— so any draw would have conformed. This script is the draw. Its output, stage1-manifest.json,
is committed in the amendment and the runner refuses to start if the file it reads differs.

Order of the draws matters and is fixed here:
  1. eligible universe   the 470 answerable instances (the 30 `_abs` are out, §12.1)
  2. smoke               8 instances, removed from every confirmatory analysis (§12.2)
  3. stage 2 universe    the remaining 462
  4. stage 1             200 of the 462, proportional to question_type, largest remainder
  5. dose subsample      60 of stage 1, same allocation rule
  6. control subsample   40 of stage 1, same rule — positive and negative controls (§12.5)
  7. counterfactual      ALL counterfactual-eligible instances in the 462 (§12.6)

Also computed, because it is a property of the design and not an outcome: the realised fraction
of each window cut, per instance, under the cut rule of §11.2.

  python3 -I stage1-manifest.py <longmemeval_s_cleaned.json>            writes the manifest
  python3 -I stage1-manifest.py <json> --check                          exit 1 unless identical
"""
import hashlib
import json
import pathlib
import random
import re
import statistics
import sys
from collections import Counter

SEED = 20261103
EXPECTED_SHA256 = "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442"
OUT = pathlib.Path(__file__).resolve().parent / "stage1-manifest.json"
DOSES = (0.020, 0.240, 0.894)
SMOKE_ALLOC = {"multi-session": 2, "temporal-reasoning": 2, "knowledge-update": 1,
               "single-session-user": 1, "single-session-assistant": 1,
               "single-session-preference": 1}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def allocate(pool, n, rng):
    """Proportional to question_type, largest remainder; ties broken by type name."""
    by = {}
    for r in pool:
        by.setdefault(r["question_type"], []).append(r)
    total = len(pool)
    quota = {k: n * len(v) / total for k, v in by.items()}
    base = {k: int(q) for k, q in quota.items()}
    rest = n - sum(base.values())
    for k in sorted(by, key=lambda k: (-(quota[k] - base[k]), k))[:rest]:
        base[k] += 1
    out = []
    for k in sorted(by):
        ids = sorted(r["question_id"] for r in by[k])
        out += rng.sample(ids, base[k])
    return sorted(out), dict(sorted(base.items()))


def prose(sess):
    return sum(len(t.get("content") or "") for t in sess)


def cut(r, frac):
    """§11.2: most-recent-first, cumulative prose chars, the crossing session included whole."""
    order = sorted(range(len(r["haystack_sessions"])),
                   key=lambda i: (r["haystack_dates"][i], i), reverse=True)
    total = sum(prose(s) for s in r["haystack_sessions"])
    kept, run = [], 0
    for i in order:
        if run >= frac * total:
            break
        kept.append(i)
        run += prose(r["haystack_sessions"][i])
    ev = {i for i, sid in enumerate(r["haystack_session_ids"]) if sid in r["answer_session_ids"]}
    return {"sessions": len(kept), "realised": round(run / total, 4),
            "evidence_kept": len(ev & set(kept)), "evidence_total": len(ev)}


NUM = re.compile(r"\d+(?:\.\d+)?")


def cf_eligible(r):
    """§12.6: answer short, contains a number, appears verbatim in an evidence turn, and nowhere
    outside the answer sessions — otherwise the original fact survives the rewrite."""
    a = str(r["answer"]).strip()
    if not (2 <= len(a) <= 60) or not NUM.search(a):
        return False
    al = a.lower()
    in_ev = out_ev = False
    for sid, sess in zip(r["haystack_session_ids"], r["haystack_sessions"]):
        for t in sess:
            if al in (t.get("content") or "").lower():
                if sid in r["answer_session_ids"] and t.get("has_answer"):
                    in_ev = True
                elif sid not in r["answer_session_ids"]:
                    out_ev = True
    return in_ev and not out_ev


def altered(answer):
    """§12.6, the rewrite rule: every number in the answer moves by a fixed offset — +3 for a
    year (1900..2100), +7 otherwise. Deterministic, so the expected answer is known by
    construction and no model is asked to invent the counterfactual."""
    def shift(m):
        s = m.group(0)
        if "." in s:
            return f"{float(s) + 7:g}"
        n = int(s)
        return str(n + 3 if 1900 <= n <= 2100 else n + 7)
    return NUM.sub(shift, answer)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    path = sys.argv[1]
    digest = sha256(path)
    if digest != EXPECTED_SHA256:
        sys.exit(f"dataset sha256 {digest} != {EXPECTED_SHA256}: wrong file or revision")
    data = json.load(open(path))
    byid = {r["question_id"]: r for r in data}
    rng = random.Random(SEED)

    answerable = [r for r in data if not r["question_id"].endswith("_abs")]
    excluded_abs = sorted(r["question_id"] for r in data if r["question_id"].endswith("_abs"))
    assert len(answerable) == 470 and len(excluded_abs) == 30, (len(answerable), len(excluded_abs))

    smoke = []
    for k, n in sorted(SMOKE_ALLOC.items()):
        ids = sorted(r["question_id"] for r in answerable if r["question_type"] == k)
        smoke += rng.sample(ids, n)
    smoke = sorted(smoke)
    universe = [r for r in answerable if r["question_id"] not in set(smoke)]
    assert len(universe) == 462

    stage1, alloc1 = allocate(universe, 200, rng)
    s1 = [byid[i] for i in stage1]
    dose, alloc_d = allocate(s1, 60, rng)
    controls, alloc_c = allocate(s1, 40, rng)
    elig = sorted(r["question_id"] for r in universe if cf_eligible(r))
    # v1.0 promised a 40-item subsample without counting the pool. The pool is 31 in the 462,
    # so the control runs on ALL of them (§12.6) — no draw, nothing for a seed to choose.
    cf_rows = {}
    for i in elig:
        r = byid[i]
        alt = altered(str(r["answer"]).strip())
        hay = " ".join((t.get("content") or "") for s in r["haystack_sessions"] for t in s).lower()
        if alt.lower() in hay:
            continue  # the altered value already occurs: the control could not tell them apart
        cf_rows[i] = {"original": str(r["answer"]).strip(), "altered": alt}
    cf = sorted(cf_rows)

    cuts = {r["question_id"]: {f"{f:.3f}": cut(r, f) for f in DOSES}
            for r in answerable}
    s1_real = [cuts[i]["0.240"]["realised"] for i in stage1]
    s1_evk = Counter(cuts[i]["0.240"]["evidence_kept"] == cuts[i]["0.240"]["evidence_total"]
                     for i in stage1)

    man = {
        "seed": SEED, "dataset": "longmemeval_s_cleaned.json",
        "dataset_revision": "98d7416c24c778c2fee6e6f3006e7a073259d48f", "sha256": digest,
        "excluded_abs": excluded_abs, "smoke": smoke,
        "stage2_universe_n": len(universe),
        "stage1": stage1, "stage1_allocation": alloc1,
        "dose_subsample": dose, "dose_allocation": alloc_d,
        "control_subsample": controls, "control_allocation": alloc_c,
        "counterfactual_eligible_n": len(elig), "counterfactual": cf,
        "counterfactual_rewrite": cf_rows,
        "cuts": cuts,
    }
    text = json.dumps(man, indent=1, sort_keys=True) + "\n"
    if "--check" in sys.argv:
        same = OUT.exists() and OUT.read_text() == text
        print("manifest identical" if same else "MANIFEST DIFFERS")
        sys.exit(0 if same else 1)
    OUT.write_text(text)

    print(f"dataset sha256 ok · seed {SEED}")
    print(f"excluded _abs {len(excluded_abs)} · smoke {len(smoke)} · stage-2 universe {len(universe)}")
    print(f"stage 1 {len(stage1)} {alloc1}")
    print(f"dose {len(dose)} {alloc_d}")
    print(f"controls {len(controls)} {alloc_c}")
    print(f"counterfactual eligible {len(elig)} · usable {len(cf)} (altered value absent "
          f"from the haystack) · in stage 1: {len(set(cf) & set(stage1))}")
    for i in cf[:5]:
        print(f"    {i}: {cf_rows[i]['original']!r} -> {cf_rows[i]['altered']!r}")
    print(f"W=0.240 on stage 1: realised median {statistics.median(s1_real):.3f} "
          f"[{min(s1_real):.3f} .. {max(s1_real):.3f}] · all evidence kept in "
          f"{s1_evk[True]} of {len(stage1)}")
    for f in DOSES:
        rs = [cuts[i][f"{f:.3f}"]["realised"] for i in stage1]
        ek = sum(cuts[i][f"{f:.3f}"]["evidence_kept"] == cuts[i][f"{f:.3f}"]["evidence_total"]
                 for i in stage1)
        nk = sum(cuts[i][f"{f:.3f}"]["evidence_kept"] == 0 for i in stage1)
        print(f"  W={f:.3f}: realised median {statistics.median(rs):.3f} · all evidence kept "
              f"{ek} · none kept {nk}")
    print(f"wrote {OUT.name}")


if __name__ == "__main__":
    main()
