#!/usr/bin/env python3
"""Paper D, step 6 (PREREGISTRATION.md §5 and §6): read the controls, then H-D1 and H-D2.

Called by d-read.sh from the tag tree d-run.sh extracted; keyless, no model call.

  python3 -I d-read.py --repo <clone> --private <dir> --freeze-ref <c> --questions-ref <c> --human-ref <c>
  python3 -I d-read.py --repo <clone> --private <dir> --smoke

Refuses, before computing anything, unless the three commitments are on origin/main in the order
tag -> freeze -> questions -> human, each written once and byte-equal to its private copy, and
the human commitment is the registered sample (not smoke, n 60) made from exactly this
results.json and questions.jsonl. Then reads, in this order: the four controls of §5.1 (if any
fails, H-D1 and H-D2 are printed as not interpreted), H-D1 under judge 1 with judge 2 as the
bracket, H-D2, and the descriptives of §5.5.

Writes <dir>/read/reading.json (aggregates only, publishable) and <dir>/read/reading.txt.
"""
import argparse
import collections
import importlib.util
import json
import math
import pathlib
import random
import statistics
import sys

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dcommon", HERE / "d-common.py")
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)
B = 10_000
GATES = {"ceiling": 0.70, "positive": 0.10, "cf_original": 0.10, "fidelity": 0.05, "cf_min": 10}
ARMS = ("A", "C0", "C2", "C2-cut", "P", "V")


def checks(a, P):
    loc = {n: (P / f"{n}-COMMITMENT.json").read_bytes() for n in C.COMMITS}
    if not a.smoke:
        got = C.ordered(a.repo, [("FREEZE", a.freeze_ref), ("QUESTIONS", a.questions_ref),
                                 ("HUMAN", a.human_ref)])
        for n in C.COMMITS:
            pub = C.git(a.repo, "show", f"{got[n]['_commit']}:{C.D}/{n}-COMMITMENT.json").stdout
            if pub.encode() != loc[n]:
                sys.exit(f"refusing: the published {n} commitment is not the private copy")
    fc, qc, hc = (json.loads(loc[n]) for n in C.COMMITS)
    res_b = (P / "run" / "results.json").read_bytes()
    res = json.loads(res_b)
    want = (bool(a.smoke), C.sha_bytes(res_b), qc["questions_sha256"])
    if (hc["smoke"], hc["results_sha256"], hc["questions_sha256"]) != want:
        sys.exit("refusing: the human commitment was not made from this results.json and questions")
    if not a.smoke and hc["n"] != 60:
        sys.exit("refusing: the human commitment is not the registered sample of 60")
    if res["meta"]["smoke"] is not bool(a.smoke) or fc["smoke"] is not bool(a.smoke):
        sys.exit("refusing: smoke flags disagree")
    if (res["meta"]["questions_sha256"], res["meta"]["freeze_commitment_sha256"]) != \
            (qc["questions_sha256"], C.sha_bytes(loc["FREEZE"])):
        sys.exit("refusing: results.json was not run on these commitments")
    if C.sha_file(P / "questions.jsonl") != qc["questions_sha256"]:
        sys.exit("refusing: questions.jsonl is not the committed one")
    return fc, qc, hc, res


def quantile(xs, p):
    xs = sorted(xs)
    i = p * (len(xs) - 1)
    lo, hi = math.floor(i), math.ceil(i)
    return xs[lo] + (xs[hi] - xs[lo]) * (i - lo)


def contrast(qids, qs, Y, t="C2", c="C0"):
    """mean over questions of Y(t) - Y(c), 95% percentile cluster bootstrap over sessions."""
    per = collections.defaultdict(lambda: [0, 0])
    for q in qids:
        per[qs[q]["uuid"]][0] += Y[t][q] - Y[c][q]
        per[qs[q]["uuid"]][1] += 1
    cl = list(per.values())
    if not cl:
        return None
    est = sum(x for x, _ in cl) / sum(n for _, n in cl)
    rng = random.Random(C.SEED)
    boots = []
    for _ in range(B):
        s = [cl[rng.randrange(len(cl))] for _ in cl]
        boots.append(sum(x for x, _ in s) / sum(n for _, n in s))
    lb, ub = quantile(boots, 0.025), quantile(boots, 0.975)
    read = "C2 better" if lb > 0 else "C0 better" if ub < 0 else "not shown"
    return {"n_questions": len(qids), "n_sessions": len(cl), "estimate": round(est, 4),
            "ci95": [round(lb, 4), round(ub, 4)], "reading": read,
            "excludes_plus_0.10": ub < 0.10}


def mcnemar(qids, Y, t="C2", c="C0"):
    b = sum(Y[t][q] and not Y[c][q] for q in qids)
    cc = sum(Y[c][q] and not Y[t][q] for q in qids)
    n = b + cc
    p = 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, k) for k in range(min(b, cc) + 1)) / 2 ** n)
    return {"C2_only": b, "C0_only": cc, "p_exact": round(p, 4)}


def acc(qids, Y, arm):
    return round(sum(Y[arm][q] for q in qids) / len(qids), 4) if qids else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--private", required=True)
    for k in ("--freeze-ref", "--questions-ref", "--human-ref"):
        ap.add_argument(k)
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    if not a.smoke and not (a.freeze_ref and a.questions_ref and a.human_ref):
        sys.exit("--freeze-ref, --questions-ref and --human-ref are required (or --smoke)")
    P = C.private(a.private)
    fc, qc, hc, res = checks(a, P)
    qs = {q["qid"]: q for q in map(json.loads, open(P / "questions.jsonl", encoding="utf-8"))}
    Y = {j: {arm: {} for arm in ARMS} for j in ("j1", "j2")}
    K = {arm: {} for arm in ARMS}
    for r in res["rows"]:
        Y["j1"][r["arm"]][r["qid"]] = int(bool(r["j1"]))
        Y["j2"][r["arm"]][r["qid"]] = int(bool(r["j2"]))
        K[r["arm"]][r["qid"]] = int(bool(r["j1_contradiz_bin"]))
    sets = {s: sorted(q for q in qs if qs[q]["set"] == s) for s in ("primary", "secondary")}
    prim = sets["primary"]

    # ---------------------------------------------------------------- §5.1 controls, first
    cf = res["counterfactual"]
    n_cf = len(cf)
    orig, alt = sum(r["has_original"] for r in cf), sum(r["has_altered"] for r in cf)
    ctl = {
        "ceiling": {"value": acc(prim, Y["j1"], "A"), "judge2": acc(prim, Y["j2"], "A")},
        "positive": {"value": acc(prim, Y["j1"], "C2-cut")},
        "counterfactual": {"eligible": res["meta"]["cf_eligible"], "rows": n_cf,
                           "original": orig, "altered": alt,
                           "original_rate": round(orig / n_cf, 4) if n_cf else None},
        "fidelity": {"P": acc(prim, Y["j1"], "P"), "V": acc(prim, Y["j1"], "V")},
    }
    ctl["ceiling"]["pass"] = ctl["ceiling"]["value"] is not None and ctl["ceiling"]["value"] >= GATES["ceiling"]
    ctl["positive"]["pass"] = ctl["positive"]["value"] is not None and ctl["positive"]["value"] <= GATES["positive"]
    if res["meta"]["cf_eligible"] < GATES["cf_min"]:
        ctl["counterfactual"]["pass"], ctl["counterfactual"]["status"] = None, "not testable"
    else:
        ok = ctl["counterfactual"]["original_rate"] <= GATES["cf_original"] and orig < alt
        ctl["counterfactual"]["pass"], ctl["counterfactual"]["status"] = ok, "pass" if ok else "fail"
    fp, fv = ctl["fidelity"]["P"], ctl["fidelity"]["V"]
    ctl["fidelity"]["difference"] = round(abs(fp - fv), 4) if None not in (fp, fv) else None
    ctl["fidelity"]["pass"] = ctl["fidelity"]["difference"] is not None and \
        ctl["fidelity"]["difference"] <= GATES["fidelity"] + 1e-12
    interpret = all(ctl[k]["pass"] is not False for k in ctl)

    # ---------------------------------------------------------------- §5.2 hypotheses
    hyp = {}
    for name, s in (("H-D1", "primary"), ("H-D2", "secondary")):
        h = {j: contrast(sets[s], qs, Y[j]) for j in ("j1", "j2")}
        if h["j1"] and h["j2"]:
            both = h["j1"]["ci95"][0] > 0 and h["j2"]["ci95"][0] > 0
            h["bracket"] = "C2 better across judge families" if both else (
                "judge-dependent" if h["j1"]["reading"] != h["j2"]["reading"] else "judges agree: "
                + h["j1"]["reading"])
        h["interpreted"] = interpret
        hyp[name] = h

    # ---------------------------------------------------------------- §5.5 descriptives
    S = res["sessions"]
    zero_prod = {u for u, s in S.items() if s["units"]["P"] == 0}
    band = lambda u: "<50k" if S[u]["prose_chars"] < 50_000 else "50k-200k" if S[u]["prose_chars"] < 200_000 else ">=200k"
    desc = {
        "accuracy": {s: {j: {arm: acc(sets[s], Y[j], arm) for arm in ARMS} for j in ("j1", "j2")}
                     for s in sets},
        "contradiction_j1": {s: {arm: acc(sets[s], K, arm) for arm in ARMS} for s in sets},
        "mcnemar": {s: {j: mcnemar(sets[s], Y[j]) for j in ("j1", "j2")} for s in sets},
        "by_category_j1": {c: contrast([q for q in prim if qs[q]["category"] == c], qs, Y["j1"])
                           for c in sorted({qs[q]["category"] for q in prim})},
        "by_band_j1": {b: contrast([q for q in prim if band(qs[q]["uuid"]) == b], qs, Y["j1"])
                       for b in sorted({band(qs[q]["uuid"]) for q in prim})},
        "zero_production_units_j1": {"sessions": len(zero_prod),
                                     "effect": contrast([q for q in prim if qs[q]["uuid"] in zero_prod], qs, Y["j1"])},
        "units_per_session": {arm: {"mean": round(statistics.mean(s["units"][arm] for s in S.values()), 2),
                                    "median": statistics.median(s["units"][arm] for s in S.values())}
                              for arm in ("C0", "C2", "C2-cut", "P", "V")},
        "failed_blocks": {arm: sum(s["failed_blocks"][arm] for s in S.values())
                          for arm in ("C0", "C2", "C2-cut", "V")},
        "blocks": {arm: sum(s["blocks"][arm] for s in S.values()) for arm in ("C0", "C2", "C2-cut", "V")},
        "V_units_vs_chunks_extracted": {"V_units": sum(s["units"]["V"] for s in S.values()),
                                        "chunks_extracted": sum(s["chunks_extracted"] for s in S.values()),
                                        "P_units": sum(s["units"]["P"] for s in S.values())},
        "V_message_count_matches_log": {"sessions": len(S), "equal": sum(
            s["visible_messages"] == s["message_count_log"] for s in S.values())},
        "generation": {"questions": qc["questions"], "drops": qc["drops"],
                       "sessions_used": qc["sessions_used"], "extension": qc["extension_sessions"]},
        "frame": {"counts": fc["counts"], "bands": fc["bands"]},
        "human": {k: hc[k] for k in ("n", "agreement", "kappa", "table")}
                 | {"validated": hc["kappa"] >= 0.4},
        "cost_usd": res["meta"]["usd"],
    }
    out = {"smoke": bool(a.smoke), "controls": ctl, "interpret": interpret, "hypotheses": hyp,
           "descriptive": desc}
    (P / "read").mkdir(exist_ok=True)
    (P / "read" / "reading.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    lines = ["CONTROLS (primary set, judge 1)"]
    for k, v in ctl.items():
        lines.append(f"  {k:15s} {json.dumps(v, ensure_ascii=False)}")
    lines.append(f"  -> contrasts {'INTERPRETED' if interpret else 'NOT INTERPRETED (instrument failure)'}")
    for name, h in hyp.items():
        lines.append(f"{name} ({'primary' if name == 'H-D1' else 'secondary'}): "
                     + ("" if interpret else "[not interpreted] ")
                     + f"judge 1 {json.dumps(h['j1'])} · judge 2 {json.dumps(h['j2'])} · "
                       f"{h.get('bracket')}")
    lines.append(f"human sample: n {hc['n']} · kappa {hc['kappa']}"
                 + ("" if hc["kappa"] >= 0.4 else " · BELOW 0.4: judge-dependent conclusions not validated"))
    txt = "\n".join(lines) + "\n"
    (P / "read" / "reading.txt").write_text(txt, encoding="utf-8")
    print(txt, end="")
    print(f"descriptives in {P / 'read' / 'reading.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
