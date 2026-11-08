#!/usr/bin/env python3
"""C2 shadow study, step 7 (SHADOW-PREREGISTRATION.md §5 and §6): read the controls, then H-S1 and
H-S2. Keyless; no model call.

  python3 -I s-read.py --private <dir> --repo <clone> --refs <freeze>,<questions>,<results>,<human>
  python3 -I s-read.py --private <dir> --smoke

Refuses, before computing anything, unless the four commitments are on origin/main in the order
tag -> freeze -> questions -> results -> human, each written once and byte-equal to its private
copy; the running code is the tag's; the human commitment is the registered sample (not smoke,
n 60) made from exactly this results.json and questions.jsonl; and the frozen files match the
committed manifest. Then reads, in this order:

  §5.1 controls   ceiling: arm A, primary set, judge 1, accuracy >= 0.70
                  positive: arm C2-cut, primary set, judge 1, accuracy <= 0.10
                  record integrity: every frozen block's text hashes to its block_sha256, its C2
                  prompt sha256 is the registered one, and no C2 unit has importance below 0.5
                  If one fails, H-S1 and H-S2 are reported with every number and marked not
                  interpreted.
  §5.2 H-S1       primary set, judge 1: mean over questions of Y(C2) - Y(C0), 95% percentile
                  bootstrap with sessions as clusters, 10,000 resamples, seed of §3 (Paper D's
                  d-read.contrast); judge 2 is the bracket
       H-S2       the same on the secondary set, apart
  §5.3            the human sample's kappa with judge 1, against the 0.40 limit
  §5.4            descriptives, no threshold

Writes <dir>/read/reading.json (aggregates only) and <dir>/read/reading.txt.
"""
import argparse
import collections
import importlib.util
import json
import pathlib
import statistics
import sys

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("scommon", HERE / "s-common.py")
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)
DR = C.load("dread_shadow", HERE / "d-read.py")        # Paper D's contrast and accuracy
L = C.load("lme_shadow_read", C.ROOT / "paper3-construction/lme-run.py")   # prices only


def checks(a, P):
    refs = a.refs.split(",") if a.refs else [None] * 4
    if not a.smoke and len(refs) != 4:
        sys.exit("--refs needs the freeze, questions, results and human commits")
    got = C.chain(a.repo, P, list(zip(C.COMMITS, refs)), a.smoke)
    (fb, fc), (qb, qc), (rb, rc), (hb, hc) = (got[n] for n in C.COMMITS)
    if not a.smoke:
        C.same_as_tag(a.repo)
        if hc["n"] != C.N_HUMAN:
            sys.exit(f"refusing: the human commitment is not the registered sample of {C.N_HUMAN}")
    res_b = (P / "run" / "results.json").read_bytes()
    res = json.loads(res_b)
    if (rc["results_sha256"], hc["results_sha256"]) != (C.sha_bytes(res_b),) * 2:
        sys.exit("refusing: results.json is not the one the results and human commitments name")
    if hc["results_commitment_sha256"] != C.sha_bytes(rb) or hc["questions_sha256"] != qc["questions_sha256"]:
        sys.exit("refusing: the human commitment was not made from these results and questions")
    if (rc["questions_commitment_sha256"], rc["freeze_commitment_sha256"]) != (C.sha_bytes(qb), C.sha_bytes(fb)):
        sys.exit("refusing: the results commitment names other freeze or questions commitments")
    if (res["meta"]["questions_sha256"], res["meta"]["freeze_commitment_sha256"]) != \
            (qc["questions_sha256"], C.sha_bytes(fb)) or res["meta"]["smoke"] is not bool(a.smoke):
        sys.exit("refusing: results.json was not run on these commitments")
    if C.sha_file(P / "questions.jsonl") != qc["questions_sha256"]:
        sys.exit("refusing: questions.jsonl is not the committed one")
    C.check_manifest(P / "freeze", fc["manifest_sha256"])
    return fc, qc, rc, hc, res


def integrity(recs):
    """§5.1 record integrity over every frozen block."""
    n = bad_hash = bad_prompt = low = 0
    for _, _, r in recs:
        n += 1
        if C.sha_bytes(C.r_block(r).encode("utf-8")) != r.get("block_sha256"):
            bad_hash += 1
        if C.r_c2(r).get("prompt_sha256") != C.C2_PROMPT_SHA256:
            bad_prompt += 1
        for u in C.r_c2_units(r):
            imp = u.get("importance") if isinstance(u, dict) else None
            if not isinstance(imp, (int, float)) or isinstance(imp, bool) or imp < C.IMPORTANCE_MIN:
                low += 1
    return {"blocks": n, "block_hash_mismatch": bad_hash, "prompt_hash_mismatch": bad_prompt,
            "c2_units_below_0.5": low, "pass": n > 0 and bad_hash == bad_prompt == low == 0}


def reading_of(h, interpret):
    """§5.2: C2 better iff lower bound > 0; C0 better iff upper bound < 0; else not shown, with
    whether the interval excludes +0.10 (d-read: upper bound below +0.10). Judge 2 is the bracket."""
    if h["j1"] and h["j2"]:
        both = h["j1"]["ci95"][0] > 0 and h["j2"]["ci95"][0] > 0
        h["bracket"] = "C2 better across judge families" if both else (
            "judge-dependent" if h["j1"]["reading"] != h["j2"]["reading"] else "judges agree: " + h["j1"]["reading"])
    for j in ("j1", "j2"):
        if h[j]:
            h[j]["lower_bound_above_plus_0.10"] = h[j]["ci95"][0] > 0.10
    h["interpreted"] = interpret
    return h


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--private", required=True)
    ap.add_argument("--repo", default=str(C.ROOT))
    ap.add_argument("--refs")
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args(argv)
    if not a.smoke and not a.refs:
        sys.exit("--refs is required (or --smoke)")
    P = C.private(a.private)
    fc, qc, rc, hc, res = checks(a, P)
    DR.C.SEED, DR.B = fc["seed"], C.B_BOOT     # §5.2: the seed of §3, 10,000 resamples
    qs = {q["qid"]: q for q in map(json.loads, open(P / "questions.jsonl", encoding="utf-8"))}
    recs = C.frozen_records(P / "freeze")
    Y = {j: {arm: {} for arm in C.ARMS} for j in ("j1", "j2")}
    K = {arm: {} for arm in C.ARMS}
    tok = {arm: [0, 0, 0] for arm in C.ARMS}
    for r in res["rows"]:
        Y["j1"][r["arm"]][r["qid"]] = int(bool(r["j1"]))
        Y["j2"][r["arm"]][r["qid"]] = int(bool(r["j2"]))
        K[r["arm"]][r["qid"]] = int(bool(r["j1_contradiz_bin"]))
        t = tok[r["arm"]]
        t[0], t[1], t[2] = t[0] + (r.get("tin") or 0), t[1] + (r.get("tout") or 0), t[2] + 1
    sets = {s: sorted(q for q in qs if qs[q]["set"] == s) for s in C.SETS}
    prim = sets["primary"]
    acc = DR.acc

    # ---------------------------------------------------------------- §5.1 controls, first
    ctl = {"ceiling": {"value": acc(prim, Y["j1"], "A"), "judge2": acc(prim, Y["j2"], "A")},
           "positive": {"value": acc(prim, Y["j1"], "C2-cut"), "judge2": acc(prim, Y["j2"], "C2-cut")},
           "record_integrity": integrity(recs)}
    ctl["ceiling"]["pass"] = ctl["ceiling"]["value"] is not None and ctl["ceiling"]["value"] >= C.GATES["ceiling"]
    ctl["positive"]["pass"] = ctl["positive"]["value"] is not None and \
        ctl["positive"]["value"] <= C.GATES["positive"] + 1e-12
    interpret = all(ctl[k]["pass"] for k in ctl)

    # ---------------------------------------------------------------- §5.2 hypotheses
    hyp = {}
    for name, s in (("H-S1", "primary"), ("H-S2", "secondary")):
        hyp[name] = reading_of({j: DR.contrast(sets[s], qs, Y[j]) for j in ("j1", "j2")}, interpret)

    # ---------------------------------------------------------------- §5.4 descriptives
    c0n = [len(C.r_c0_units(r)) for _, _, r in recs]
    c2n = [len(C.r_c2_units(r)) for _, _, r in recs]
    c2tok = [C.r_c2_tokens(r) for _, _, r in recs]
    cutb = res["cut_blocks"].values()
    ag = lambda q: qs[q].get("agent") or "?"
    desc = {
        "units_per_block": {arm: {"total": sum(v), "mean": round(statistics.mean(v), 3) if v else None,
                                  "median": statistics.median(v) if v else None}
                            for arm, v in (("C0", c0n), ("C2", c2n))},
        "blocks_with_no_unit": {"C0": sum(x == 0 for x in c0n), "C2": sum(x == 0 for x in c2n),
                                "either": sum(a_ == 0 or b_ == 0 for a_, b_ in zip(c0n, c2n)),
                                "both": sum(a_ == 0 and b_ == 0 for a_, b_ in zip(c0n, c2n)),
                                "blocks": len(recs)},
        "accuracy": {s: {j: {arm: acc(sets[s], Y[j], arm) for arm in C.ARMS} for j in ("j1", "j2")}
                     for s in C.SETS},
        "contradiction_j1": {s: {arm: acc(sets[s], K, arm) for arm in C.ARMS} for s in C.SETS},
        "by_agent_j1": {g: DR.contrast([q for q in prim if ag(q) == g], qs, Y["j1"])
                        for g in sorted({ag(q) for q in prim})},
        "by_category_j1": {c: DR.contrast([q for q in prim if qs[q]["category"] == c], qs, Y["j1"])
                           for c in sorted({qs[q]["category"] for q in prim})},
        "tokens_and_cost": {
            "reader": {arm: {"rows": t[2], "tokens_in": t[0], "tokens_out": t[1],
                             "usd": round(t[0] * L.G_IN + t[1] * L.G_OUT, 6)} for arm, t in tok.items()},
            "judge1_usd": {arm: round(t[2] * L.J_CALL, 6) for arm, t in tok.items()},
            "distill": {"C0": None,     # production's C0 call; its tokens are not in the record
                        "C2": {"tokens_in": sum(x for x, _ in c2tok), "tokens_out": sum(y for _, y in c2tok),
                               "usd": round(sum(x * L.G_IN + y * L.G_OUT for x, y in c2tok), 6)},
                        "C2-cut": {"calls": sum(not b["cut_empty"] for b in cutb),
                                   "tokens_in": sum(b["cut_tin"] for b in cutb),
                                   "tokens_out": sum(b["cut_tout"] for b in cutb),
                                   "usd": round(sum(b["cut_tin"] * L.G_IN + b["cut_tout"] * L.G_OUT for b in cutb), 6),
                                   "failed": sum(b["cut_failed"] for b in cutb)}},
            "judge2": "not separable by arm: lme-run.judge2 does not return its tokens",
            "ledger_usd": res["meta"]["usd"], "writer_usd": res["meta"].get("writer_usd"),
            "writer_calls": qc["writer_calls_total"]},
        "generation": {"blocks": qc["blocks"], "validated": qc["validated"], "questions": qc["questions"],
                       "drops": qc["drops"], "writer_over_max_facts": qc["writer_over_max_facts"]},
        "freeze": {"window": fc["window"], "totals": fc["totals"], "stopping": fc["stopping"]},
        "human": {k: hc[k] for k in ("n", "agreement", "kappa", "table")}
                 | {"validated": hc["kappa"] >= C.KAPPA_MIN, "limit": C.KAPPA_MIN},
    }
    out = {"smoke": bool(a.smoke), "controls": ctl, "interpret": interpret, "hypotheses": hyp,
           "descriptive": desc}
    (P / "read").mkdir(exist_ok=True)
    C.write_private(P / "read" / "reading.json", json.dumps(out, indent=1, ensure_ascii=False))
    lines = ["CONTROLS (§5.1)"]
    for k, v in ctl.items():
        lines.append(f"  {k:17s} {json.dumps(v, ensure_ascii=False)}")
    lines.append(f"  -> contrasts {'INTERPRETED' if interpret else 'NOT INTERPRETED (a control failed)'}")
    for name, h in hyp.items():
        lines.append(f"{name} ({'primary' if name == 'H-S1' else 'secondary'}): "
                     + ("" if interpret else "[not interpreted] ")
                     + f"judge 1 {json.dumps(h['j1'])} · judge 2 {json.dumps(h['j2'])} · {h.get('bracket')}")
    lines.append(f"human sample: n {hc['n']} · kappa {hc['kappa']}"
                 + ("" if hc["kappa"] >= C.KAPPA_MIN else
                    f" · BELOW {C.KAPPA_MIN}: judge-dependent conclusions not validated by a human"))
    txt = "\n".join(lines) + "\n"
    C.write_private(P / "read" / "reading.txt", txt)
    C.lock_down(P)
    print(txt, end="")
    print(f"descriptives in {P / 'read' / 'reading.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
