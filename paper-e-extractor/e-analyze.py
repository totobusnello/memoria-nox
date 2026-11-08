#!/usr/bin/env python3
"""Paper E analysis, fixed before the run (PREREGISTRATION.md §6). Keyless; reads rows.ndjson.

  -. completeness: exactly one row per (instance, cell) of the design (242 x 6 + 2 x 40),
     nothing else; otherwise it refuses to analyze
  0. controls, which gate interpretation of 1 and 2 (a failure blocks it; its cause is not
     attributed):
       floor      acc(F_C2) >= 0.50 and acc(L_C2) >= 0.50, judge 1
       positive   acc(L_C2_pos) <= 0.10 and acc(F_C2_pos) <= 0.10 on the control subsample
  1. primary    I = E[(F_C2 - F_C0) - (L_C2 - L_C0)], judge 1, 95% two-sided interval,
                cluster-robust (CR1) over answer-session groups, as Paper 3.
                hi < 0: the C2 advantage shrinks with the stronger extractor; lo > 0: it grows;
                otherwise inconclusive (no equivalence claim)
  2. bracket    I under judge 2
  3. secondary  F_C0 - L_C0 and F_C2 - L_C2 (which term moved), F_P - F_C2, the P interaction
                (F_P - F_C0) - (L_P - L_C0), L_P - L_C0, F_P - F_C0, F_C2 - F_C0, and
                L_C2 - L_C0 beside Paper 3's +24.8 pp. Intervals, no test claimed
  4. failures   failed blocks and units per block per extractor x criterion, from receipt.json
  5. describe   accuracy, abstention and median served characters per cell; per question_type

  python3 -I e-analyze.py <run dir>            writes analysis.{txt,json} there
  python3 -I e-analyze.py <run dir> --check    exit 1 unless both are reproduced byte for byte
"""
import importlib.util
import json
import os
import pathlib
import statistics as st
import sys
from collections import defaultdict
from statistics import NormalDist

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("lme_analyze",
                                               HERE.parent / "paper3-construction" / "lme-analyze.py")
LA = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(LA)

ALPHA = 0.05
MAIN = ["L_C0", "L_C2", "L_P", "F_C0", "F_C2", "F_P"]
POS = ["L_C2_pos", "F_C2_pos"]
P3_MANIFEST = HERE.parent / "paper3-construction" / "v13-manifest.json"


def expected_design():
    man = json.load(open(P3_MANIFEST))
    return list(man["confirm"]), list(man["control_subsample"])


def validate(rows, qids, ctrl):
    """exactly the design's (qid, cell) pairs, once each"""
    want = {(q, c) for q in qids for c in MAIN} | {(q, c) for q in ctrl for c in POS}
    seen, dup = set(), []
    for r in rows:
        k = (r["qid"], r["cell"])
        if k in seen:
            dup.append(k)
        seen.add(k)
    missing, extra = sorted(want - seen), sorted(seen - want)
    if dup or missing or extra:
        raise ValueError(f"rows are not the design: {len(missing)} missing, {len(extra)} "
                         f"unexpected, {len(dup)} duplicated (first: "
                         f"{(missing or extra or dup)[:3]})")
P3_CRITERION = 0.248      # CONFIRM-RESULT.md, criterion contrast 11 - 10, judge 1


def analyze(rows, data, qids, ctrl, receipt=None):
    validate(rows, qids, ctrl)
    out, J = [], {}
    p = out.append
    Y = {j: defaultdict(dict) for j in ("j1", "j2")}
    ab, chars = defaultdict(list), defaultdict(list)
    qtype = {}
    for r in rows:
        Y["j1"][r["cell"]][r["qid"]] = int(bool(r["correct"]))
        Y["j2"][r["cell"]][r["qid"]] = int(bool(r["correct_j2"]))
        ab[r["cell"]].append(int(bool(r["abstained"])))
        chars[r["cell"]].append(r["served_chars"])
        qtype[r["qid"]] = r["question_type"]
    prim, pos = sorted(qids), sorted(ctrl)
    cl = LA.clusters(prim, data)
    z = NormalDist().inv_cdf(1 - ALPHA / 2)
    sizes = defaultdict(int)
    for q in prim:
        sizes[cl[q]] += 1
    G = len(sizes)
    p(f"Paper E analysis · {len(prim)} instances · {G} answer-session clusters "
      f"(largest {max(sizes.values())}) · alpha {ALPHA}")
    J["n"], J["clusters"], J["largest_cluster"] = len(prim), G, max(sizes.values())

    def acc(j, c, ids=None):
        ids = ids if ids is not None else prim
        return sum(Y[j][c][q] for q in ids) / len(ids) if ids else float("nan")

    def contrast(j, f):
        m, lo, hi, se, _ = LA.cluster_mean_ci({q: f(Y[j], q) for q in prim}, cl, z)
        return {"est": round(m, 6), "lo": round(lo, 6), "hi": round(hi, 6), "se": round(se, 6)}

    def fmt(e):
        return f"{e['est']*100:+.1f} pp [{e['lo']*100:+.1f}, {e['hi']*100:+.1f}]"

    # 0. controls
    floor = {c: round(acc("j1", c), 6) for c in ("F_C2", "L_C2")}
    pos_acc = {c: round(acc("j1", c, pos), 6) for c in POS}
    ok_floor = all(v >= 0.50 for v in floor.values())
    ok_pos = all(v <= 0.10 for v in pos_acc.values())
    p("\n0. CONTROLS")
    p(f"   floor     acc(F_C2) = {floor['F_C2']:.3f}, acc(L_C2) = {floor['L_C2']:.3f}  "
      f"(>= 0.50)  {'pass' if ok_floor else 'FAIL'}")
    p(f"   positive  acc(L_C2_pos) = {pos_acc['L_C2_pos']:.3f}, acc(F_C2_pos) = "
      f"{pos_acc['F_C2_pos']:.3f}  (n = {len(pos)} each, <= 0.10)  {'pass' if ok_pos else 'FAIL'}")
    interpret = ok_floor and ok_pos
    J["controls"] = {"floor": floor, "floor_pass": ok_floor, "positive": pos_acc,
                     "positive_n": len(pos), "positive_pass": ok_pos, "interpret": interpret}

    def inter(y, q):
        return (y["F_C2"][q] - y["F_C0"][q]) - (y["L_C2"][q] - y["L_C0"][q])

    # 1-2. primary and bracket
    e1, e2 = contrast("j1", inter), contrast("j2", inter)
    if e1["hi"] < 0:
        verdict = "the C2 advantage shrinks with the stronger extractor"
    elif e1["lo"] > 0:
        verdict = "the C2 advantage grows with the stronger extractor"
    else:
        verdict = "inconclusive: the interval contains 0 (not an equivalence claim)"
    p("\n1. PRIMARY · I = E[(F_C2 - F_C0) - (L_C2 - L_C0)], judge 1")
    p(f"   {fmt(e1)}")
    p(f"   {verdict if interpret else 'NOT INTERPRETED: a control failed'}")
    p("\n2. BRACKET · I under judge 2")
    p(f"   {fmt(e2)}")
    J["primary"] = dict(e1, verdict=verdict if interpret else "not interpreted")
    J["bracket_j2"] = e2

    # 3. secondary
    sec = {
        "F_C0 - L_C0": lambda y, q: y["F_C0"][q] - y["L_C0"][q],
        "F_C2 - L_C2": lambda y, q: y["F_C2"][q] - y["L_C2"][q],
        "F_P - F_C2": lambda y, q: y["F_P"][q] - y["F_C2"][q],
        "P interaction (F_P - F_C0) - (L_P - L_C0)":
            lambda y, q: (y["F_P"][q] - y["F_C0"][q]) - (y["L_P"][q] - y["L_C0"][q]),
        "L_P - L_C0": lambda y, q: y["L_P"][q] - y["L_C0"][q],
        "F_P - F_C0": lambda y, q: y["F_P"][q] - y["F_C0"][q],
        "F_C2 - F_C0": lambda y, q: y["F_C2"][q] - y["F_C0"][q],
        "L_C2 - L_C0 (Paper 3: +24.8)": lambda y, q: y["L_C2"][q] - y["L_C0"][q],
    }
    p("\n3. SECONDARY (intervals, no test claimed)          judge 1                judge 2")
    J["secondary"] = {}
    for name, f in sec.items():
        a1, a2 = contrast("j1", f), contrast("j2", f)
        J["secondary"][name] = {"j1": a1, "j2": a2}
        p(f"   {name:45s} {fmt(a1):24s} {fmt(a2)}")

    # 4. failures
    p("\n4. FAILED BLOCKS per extractor x criterion (receipt.json)")
    J["failures"] = (receipt or {}).get("failures_by_cell")
    if not J["failures"]:
        p("   no receipt")
    else:
        for k, d in J["failures"].items():
            p(f"   {k:28s} {d['failed']:>6d} of {d['blocks']:>6d} ({d['failed_share']*100:.2f}%)"
              f"{'  OVER 1%' if d['over_1pct'] else ''}   units/block {d['units_per_block']:.2f}")

    # 5. describe
    p("\n5. CELLS                 acc j1   acc j2   abstain   median chars")
    J["cells"] = {}
    for c in MAIN + POS:
        ids = pos if c in POS else prim
        d = {"n": len(ids), "acc_j1": round(acc("j1", c, ids), 6), "acc_j2": round(acc("j2", c, ids), 6),
             "abstain": round(sum(ab[c]) / len(ab[c]), 6), "median_chars": st.median(chars[c])}
        J["cells"][c] = d
        p(f"   {c:20s} {d['acc_j1']:7.3f}  {d['acc_j2']:7.3f}  {d['abstain']:8.3f}  {d['median_chars']:>12,.0f}")
    p("\n   per question_type (judge 1)")
    p("   " + f"{'type':28s} {'n':>4s} " + " ".join(f"{c:>6s}" for c in MAIN))
    J["by_type"] = {}
    for t in sorted(set(qtype[q] for q in prim)):
        ids = [q for q in prim if qtype[q] == t]
        vals = {c: round(acc("j1", c, ids), 6) for c in MAIN}
        J["by_type"][t] = dict(vals, n=len(ids))
        p(f"   {t:28s} {len(ids):4d} " + " ".join(f"{vals[c]:6.3f}" for c in MAIN))
    return "\n".join(out) + "\n", J


def main():
    run = pathlib.Path(sys.argv[1])
    check = "--check" in sys.argv[2:]
    rows = [json.loads(l) for l in open(run / "rows.ndjson")]
    data_path = os.environ.get("E_DATA", LA.DATA)
    data = {r["question_id"]: r for r in json.load(open(data_path))}
    rc = run / "receipt.json"
    qids, ctrl = expected_design()
    try:
        txt, J = analyze(rows, data, qids, ctrl, json.loads(rc.read_text()) if rc.exists() else None)
    except ValueError as e:
        sys.exit(str(e))
    js = json.dumps(J, indent=1, sort_keys=True) + "\n"
    if check:
        same = ((run / "analysis.txt").read_text() == txt and (run / "analysis.json").read_text() == js)
        print("identical" if same else "DIFFERS")
        sys.exit(0 if same else 1)
    (run / "analysis.txt").write_text(txt)
    (run / "analysis.json").write_text(js)
    print(txt)


if __name__ == "__main__":
    main()
