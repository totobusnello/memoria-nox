#!/usr/bin/env python3
"""Analysis of the public-corpus leg, fixed in amendment v1.1 BEFORE stage 1 runs. Keyless.

Reads <run>/rows.ndjson (written by lme-run.py) and the dataset (for the answer-session clusters)
and computes, in this order, exactly what §11.4 and §12 pre-specify:

  0. controls, which gate interpretation:
       answerable floor   acc(cell 11) >= 0.50 on the stage-1 instances      (§11.3, §12.5)
       positive           acc(pos) <= 0.10 on the control subsample          (§12.5)
       negative           |acc(neg) - acc(11)| <= 0.10 and discordance <= 0.20 (§12.5)
       counterfactual     cell 11: answers carrying the ORIGINAL number <= 10% of the variants,
                          and answers carrying the ALTERED number outnumber them (§12.6)
     if the floor fails, the primary is NOT interpreted (instrument failure, §11.3)
  1. primary    total effect  E[Y11 - Y00], judge 1, two-sided 1-alpha interval,
                cluster-robust over answer-session groups; licence label of §11.4; stop rule
  2. bracket    the same under judge 2, and the criterion contrast 11-10 under both (§11.5.9)
  3. secondary  interaction E[Y11-Y10-Y01+Y00] minus the serial null computed on the same
                cells, cluster bootstrap 10,000, seed 20261103
  4. length     primary adjusted for served length (OLS on the centred length difference,
                cluster bootstrap), and the length-matched arm against 00 and 11 (§11.5.8)
  5. dose       sign of Y(full,C1) - Y(dose,C0) at 0.020 and 0.894 on the dose subsample
  6. describe   per question_type, realised dose, abstention rate per cell

  python3 -I lme-analyze.py <run dir> [--alpha 0.03]           writes analysis.{txt,json} there
  python3 -I lme-analyze.py <run dir> --check                  exit 1 unless both are identical
"""
import json
import math
import os
import pathlib
import random
import re
import sys
from collections import Counter, defaultdict
from statistics import NormalDist

SEED = 20261103
B = 10_000
DATA = os.path.expanduser("~/datasets/longmemeval/longmemeval_s_cleaned.json")
NUM = re.compile(r"\d+(?:\.\d+)?")


def clusters(qids, data):
    """connected components of instances that share an ANSWER session (§11.2)."""
    parent = {q: q for q in qids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    owner = {}
    for q in qids:
        for sid in data[q]["answer_session_ids"]:
            if sid in owner:
                parent[find(q)] = find(owner[sid])
            else:
                owner[sid] = q
    return {q: find(q) for q in qids}


def cluster_mean_ci(vals, cl, z):
    """mean of per-instance values, cluster-robust SE (CR1)."""
    n = len(vals)
    m = sum(vals.values()) / n
    g = defaultdict(float)
    for q, v in vals.items():
        g[cl[q]] += v - m
    G = len(g)
    var = sum(x * x for x in g.values()) / (n * n) * (G / (G - 1) if G > 1 else 1)
    se = math.sqrt(var)
    return m, m - z * se, m + z * se, se, G


def boot(fn, qids, cl, alpha, rng):
    groups = defaultdict(list)
    for q in qids:
        groups[cl[q]].append(q)
    keys = sorted(groups)
    est, dropped = [], 0
    for _ in range(B):
        sample = [q for k in (rng.choice(keys) for _ in keys) for q in groups[k]]
        v = fn(sample)
        if v is None:
            dropped += 1      # undefined on this resample (serial null with acc00 = 0): counted,
            continue          # reported, never silently absorbed (found by the smoke, §12.2.1)
        est.append(v)
    if not est:
        return float("nan"), float("nan"), dropped
    est.sort()
    lo = est[int(alpha / 2 * len(est))]
    hi = est[min(len(est) - 1, int((1 - alpha / 2) * len(est)))]
    return lo, hi, dropped


def licence(lo, hi, ref=0.212):
    if lo > 0 and hi <= ref:
        return "excludes 0, entirely below 21.2 pp: repair confirmed, smaller on this corpus"
    if lo > 0 and lo >= ref:
        return "excludes 0, entirely above 21.2 pp: repair confirmed, larger on this corpus"
    if lo > 0:
        return "excludes 0, contains 21.2 pp: repair confirmed, covers production's estimate"
    if hi < 0:
        return "excludes 0, entirely negative: repairing both HURTS on this corpus"
    return "contains 0: INCONCLUSIVE — never a null (§11.4)"


def nums(s):
    return NUM.findall(s or "")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    run = pathlib.Path(sys.argv[1])
    receipt = json.load(open(run / "receipt.json"))
    confirm = receipt["phase"] == "confirm"   # v1.2 §13.8: one stage, alpha 0.05, no stop rule
    alpha = (float(sys.argv[sys.argv.index("--alpha") + 1]) if "--alpha" in sys.argv
             else (0.05 if confirm else 0.03))
    z = NormalDist().inv_cdf(1 - alpha / 2)
    rows = [json.loads(l) for l in open(run / "rows.ndjson")]
    data = {r["question_id"]: r for r in json.load(open(DATA))}
    man = json.load(open(pathlib.Path(__file__).resolve().parent / "stage1-manifest.json"))
    rng = random.Random(SEED)

    Y, Y2, R = defaultdict(dict), defaultdict(dict), defaultdict(dict)
    for r in rows:
        if r["variant"].endswith("#cf"):
            continue
        Y[r["cell"]][r["qid"]] = int(r["correct"])
        Y2[r["cell"]][r["qid"]] = int(r["correct_j2"])
        R[r["cell"]][r["qid"]] = r
    prim = sorted(set(Y["00"]) & set(Y["01"]) & set(Y["10"]) & set(Y["11"]))
    assert not set(prim) & set(man["excluded_abs"]), "an _abs instance reached the analysis"
    cl = clusters(prim, data)
    out, J = [], {"alpha": alpha, "z": round(z, 4), "n": len(prim), "phase": receipt["phase"]}

    def p(s=""):
        out.append(s)

    def acc(cell, ids, y=Y):
        ids = [q for q in ids if q in y[cell]]
        return (sum(y[cell][q] for q in ids) / len(ids)) if ids else float("nan"), len(ids)

    p(f"phase {receipt['phase']} · n={len(prim)} instances with all four primary cells · "
      f"{len(set(cl.values()))} answer-session clusters · alpha {alpha} (z={z:.4f})")
    p(f"spend (estimated from usage) US$ {receipt['spend_usd_estimated']} · failed blocks "
      f"{receipt['failed_blocks']}")

    # 0. controls
    p("\n0. CONTROLS")
    a11, n11 = acc("11", prim)
    floor_ok = a11 >= 0.50
    p(f"   answerable floor  acc(11) = {a11:.3f} (n={n11})  required >= 0.500  "
      f"{'PASS' if floor_ok else 'FAIL -> instrument failure, primary NOT interpreted'}")
    J["floor"] = {"acc11": a11, "pass": floor_ok}
    ctrl = sorted(set(Y["pos"]) & set(Y["neg"]) & set(Y["11"]))
    if ctrl:
        apos, _ = acc("pos", ctrl)
        aneg, _ = acc("neg", ctrl)
        a11c, _ = acc("11", ctrl)
        disc = sum(Y["neg"][q] != Y["11"][q] for q in ctrl) / len(ctrl)
        pos_ok = apos <= 0.10
        neg_ok = abs(aneg - a11c) <= 0.10 and disc <= 0.20
        p(f"   positive          acc(pos) = {apos:.3f} (n={len(ctrl)})  required <= 0.100  "
          f"{'PASS' if pos_ok else 'FAIL'}")
        p(f"   negative          acc(neg) = {aneg:.3f} vs acc(11) = {a11c:.3f}, discordance "
          f"{disc:.3f}  required |diff| <= 0.100 and discordance <= 0.200  "
          f"{'PASS' if neg_ok else 'FAIL'}")
        J["positive"] = {"acc": apos, "pass": pos_ok}
        J["negative"] = {"acc_neg": aneg, "acc_11": a11c, "discordance": disc, "pass": neg_ok}
    cf = [r for r in rows if r["variant"].endswith("#cf") and r["cell"] == "11"]
    if cf:
        rw = man["counterfactual_rewrite"]
        orig = sum(1 for r in cf if set(nums(rw[r["qid"]]["original"])) <= set(nums(r["answer"])))
        alt = sum(1 for r in cf if set(nums(rw[r["qid"]]["altered"])) <= set(nums(r["answer"])))
        cf_ok = orig <= 0.10 * len(cf) and alt > orig
        p(f"   counterfactual    cell 11 on {len(cf)} rewritten variants: carries ORIGINAL "
          f"{orig}, carries ALTERED {alt}  required original <= {0.10*len(cf):.1f} and "
          f"altered > original  {'PASS' if cf_ok else 'FAIL'}")
        J["counterfactual"] = {"n": len(cf), "original": orig, "altered": alt, "pass": cf_ok}
    pre = receipt.get("judge_preflight") or []
    if pre:
        acc1 = sum(x["accepted"] for x in pre)
        acc2 = sum(x.get("accepted_j2", False) for x in pre)
        p(f"   judge preflight   abstentions on answerable questions accepted: judge 1 "
          f"{acc1}/{len(pre)}, judge 2 {acc2}/{len(pre)}  required 0 for judge 1")
        J["preflight"] = {"n": len(pre), "accepted_j1": acc1, "accepted_j2": acc2}

    # 1. primary
    p("\n1. PRIMARY · total effect E[Y11 - Y00], judge 1 (gpt-6-luna)")
    d = {q: Y["11"][q] - Y["00"][q] for q in prim}
    m, lo, hi, se, G = cluster_mean_ci(d, cl, z)
    p(f"   {m*100:+.1f} pp  [{lo*100:+.1f} .. {hi*100:+.1f}]  (cluster-robust SE {se*100:.2f} pp, "
      f"G={G}) · acc00 {acc('00', prim)[0]:.3f} · acc11 {a11:.3f}")
    p(f"   licence: {licence(lo, hi) if floor_ok else 'NOT INTERPRETED (floor failed)'}")
    J["primary"] = {"est": m, "lo": lo, "hi": hi, "se": se, "clusters": G,
                    "licence": licence(lo, hi)}
    if not confirm:
        stop = lo > 0.05
        p(f"   stop at stage 1 (interval entirely above +5 pp): {'YES' if stop else 'NO -> stage 2'}")
        J["primary"]["stop_at_stage1"] = stop

    # 2. bracket
    p("\n2. JUDGE-FAMILY BRACKET (§11.5 item 9)")
    for name, (c1, c0) in {"total 11-00": ("11", "00"), "criterion 11-10": ("11", "10"),
                           "criterion 01-00": ("01", "00"), "window 11-01": ("11", "01")}.items():
        e1 = cluster_mean_ci({q: Y[c1][q] - Y[c0][q] for q in prim}, cl, z)
        e2 = cluster_mean_ci({q: Y2[c1][q] - Y2[c0][q] for q in prim}, cl, z)
        p(f"   {name:16s} judge1 {e1[0]*100:+6.1f} [{e1[1]*100:+.1f} .. {e1[2]*100:+.1f}] · "
          f"judge2 {e2[0]*100:+6.1f} [{e2[1]*100:+.1f} .. {e2[2]*100:+.1f}] · bracket "
          f"[{min(e1[0], e2[0])*100:+.1f} · {max(e1[0], e2[0])*100:+.1f}] pp")
        J.setdefault("bracket", {})[name] = {"j1": e1[:3], "j2": e2[:3]}
    agree = sum(Y[c][q] == Y2[c][q] for c in ("00", "01", "10", "11") for q in prim)
    p(f"   agreement between families over the primary cells: {agree}/{4*len(prim)}")

    # 3. secondary
    p("\n3. SECONDARY · interaction minus the serial null (cluster bootstrap)")

    def inter_minus_serial(ids):
        n = len(ids)
        y = {c: sum(Y[c][q] for q in ids) / n for c in ("00", "01", "10", "11")}
        if y["00"] == 0:
            return None
        inter = y["11"] - y["10"] - y["01"] + y["00"]
        serial = y["01"] * y["10"] / y["00"] - y["10"] - y["01"] + y["00"]
        return inter - serial
    pt = inter_minus_serial(prim)
    n = len(prim)
    yy = {c: sum(Y[c][q] for q in prim) / n for c in ("00", "01", "10", "11")}
    inter = yy["11"] - yy["10"] - yy["01"] + yy["00"]
    if pt is None:
        p("   undefined: acc(00) = 0, the serial null divides by it")
    else:
        lo2, hi2, drop2 = boot(inter_minus_serial, prim, cl, alpha, rng)
        lab = ("excludes 0 from above: joint repair beyond serial chaining" if lo2 > 0 else
               "excludes 0 from BELOW: mechanism claim REFUTED" if hi2 < 0 else
               "contains 0: inconclusive (equivalence not declarable, §11.4)")
        p(f"   interaction {inter*100:+.1f} pp · minus serial null {pt*100:+.1f} pp "
          f"[{lo2*100:+.1f} .. {hi2*100:+.1f}] -> {lab}")
        p(f"   bootstrap resamples undefined (acc00 = 0) and dropped: {drop2} of {B}")
        J["secondary"] = {"interaction": inter, "minus_serial": pt, "lo": lo2, "hi": hi2,
                          "label": lab, "dropped_resamples": drop2}

    # 4. length
    p("\n4. SERVED LENGTH (§11.5 item 8)")
    dl = {q: R["11"][q]["served_chars"] - R["00"][q]["served_chars"] for q in prim}
    mdl = sum(dl.values()) / n

    def adj(ids):
        xs = [dl[q] - mdl for q in ids]
        ys = [d[q] for q in ids]
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        sxx = sum((x - mx) ** 2 for x in xs)
        b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx if sxx else 0.0
        return my - b * mx
    a_pt = adj(prim)
    a_lo, a_hi, _ = boot(adj, prim, cl, alpha, rng)
    p(f"   mean served chars: 00 {sum(R['00'][q]['served_chars'] for q in prim)/n:,.0f} · "
      f"11 {sum(R['11'][q]['served_chars'] for q in prim)/n:,.0f}")
    p(f"   primary adjusted for length difference: {a_pt*100:+.1f} pp [{a_lo*100:+.1f} .. "
      f"{a_hi*100:+.1f}] (unadjusted {m*100:+.1f})")
    lm = sorted(set(Y["lenmatch"]) & set(prim))
    if lm:
        e_a = cluster_mean_ci({q: Y["lenmatch"][q] - Y["00"][q] for q in lm}, cl, z)
        e_b = cluster_mean_ci({q: Y["lenmatch"][q] - Y["11"][q] for q in lm}, cl, z)
        capacity = e_a[1] > 0 and e_a[0] >= 0.5 * m
        p(f"   length-matched minus 00: {e_a[0]*100:+.1f} [{e_a[1]*100:+.1f} .. {e_a[2]*100:+.1f}] · "
          f"minus 11: {e_b[0]*100:+.1f} [{e_b[1]*100:+.1f} .. {e_b[2]*100:+.1f}]")
        p(f"   capacity reading (lenmatch-00 >= half the total effect, interval above 0): "
          f"{'YES — report the effect as capacity, not construction' if capacity else 'no'}")
        J["length"] = {"adjusted": [a_pt, a_lo, a_hi], "lenmatch_minus_00": e_a[:3],
                       "lenmatch_minus_11": e_b[:3], "capacity": capacity}

    # 5. dose
    rep_lvl = receipt.get("repair", "C1")   # v1.3 §14.9: label the repaired level that ran
    p(f"\n5. DOSE SENSITIVITY (sign of Y(full,{rep_lvl}) - Y(dose,C0), dose subsample)")
    for dn in ("d020", "d894"):
        ids = sorted(set(Y[f"{dn}_C0"]) & set(Y["11"]))
        if ids:
            e = cluster_mean_ci({q: Y["11"][q] - Y[f"{dn}_C0"][q] for q in ids}, cl, z)
            p(f"   W={dn[1]}.{dn[2:]}: {e[0]*100:+.1f} pp [{e[1]*100:+.1f} .. {e[2]*100:+.1f}] "
              f"(n={len(ids)}) · sign {'same' if (e[0] > 0) == (m > 0) else 'FLIPS'}")
            J.setdefault("dose", {})[dn] = e[:3]

    # 6. describe
    p("\n6. DESCRIPTIVE")
    p(f"   {'question_type':28s} {'n':>4s} " + " ".join(f"{c:>6s}" for c in ("00", "01", "10", "11")))
    for t in sorted({data[q]["question_type"] for q in prim}):
        ids = [q for q in prim if data[q]["question_type"] == t]
        p(f"   {t:28s} {len(ids):4d} " + " ".join(f"{acc(c, ids)[0]:6.3f}" for c in ("00", "01", "10", "11")))
    for c in sorted(R):
        ab = [r["abstained"] for r in R[c].values()]
        p(f"   abstention rate cell {c:8s} {sum(ab)/len(ab):.3f} (n={len(ab)})")
    rz = sorted(R["00"][q]["realised"] for q in prim)
    p(f"   realised dose of cell 00: median {rz[len(rz)//2]:.3f} [{rz[0]:.3f} .. {rz[-1]:.3f}]")
    ek = sum(R["00"][q]["evidence_kept"] == 0 for q in prim)
    p(f"   cell 00 instances with NO evidence session kept: {ek}/{n}")

    txt = "\n".join(out) + "\n"
    js = json.dumps(J, indent=1, sort_keys=True, default=float) + "\n"
    if "--check" in sys.argv:
        same = ((run / "analysis.txt").read_text() == txt and (run / "analysis.json").read_text() == js)
        print("analysis identical" if same else "ANALYSIS DIFFERS")
        sys.exit(0 if same else 1)
    (run / "analysis.txt").write_text(txt)
    (run / "analysis.json").write_text(js)
    print(txt)


if __name__ == "__main__":
    main()
