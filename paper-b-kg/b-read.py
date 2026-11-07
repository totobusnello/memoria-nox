#!/usr/bin/env python3
"""Paper B, step 4 (PREREGISTRATION.md §6, §7.4): the reading.

  python3 -I b-read.py --private <dir> --freeze-ref <c> --judges-ref <c> --sheet-ref <c> --human-ref <c>

Refuses unless the four commitments are on the public main branch in order and each private file
is byte-equal to its committed hash. Computes the controls per judge, the final label of each of
the 300 rows, B-F with its Wilson interval, and the figures §6 reports without interpreting.
Writes READING-<date>.json next to this script: counts, rates and intervals only.
"""
import argparse
import collections
import datetime
import importlib.util
import json
import pathlib
import random
import sys

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("bcommon", HERE / "b-common.py")
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)
H = C.load("bhuman", HERE / "b-human.py")

NEG_MIN, MISMATCH_MAX, KAPPA_LIMIT = 0.95, 0.10, 0.40


def controls(fz, res, human, seed):
    """Per judge: the negative citation control, the mismatched-evidence control, and kappa
    against the human on the random rows."""
    by_id = {r["relation_id"]: r for r in fz["sample"]}
    mm_text = {m["relation_id"]: m["chunk_text"] for m in fz["mismatch"]}
    rnd_rows = sorted(i for i, (o, _) in human.items() if o == "random")
    out = {}
    for name in ("judge1", "judge2"):
        prim, mm = res[name]["primary"], res[name]["mismatch"]
        rng = random.Random(seed + 4)
        tested = rejected = 0
        for i in sorted(by_id):
            v = prim[str(i)]
            if not v["verified"]:
                continue
            sw = C.swap_two(v["quote"], rng)
            if sw is None:
                continue
            tested += 1
            rejected += not C.quote_ok(sw, by_id[i]["chunk_text"][:C.CHUNK_CHARS])
        acc = sum(1 for i in mm_text if mm[str(i)]["verified"])
        claimed = sum(1 for i in mm_text if mm[str(i)]["claims"])
        neg = rejected / tested if tested else None
        mrate = acc / len(mm_text) if mm_text else None
        k = C.kappa([human[i][1] for i in rnd_rows], [int(prim[str(i)]["verified"]) for i in rnd_rows])
        out[name] = {
            "negative_citation": {"tested": tested, "rejected": rejected,
                                  "rate": None if neg is None else round(neg, 4),
                                  "passes": neg is not None and neg >= NEG_MIN},
            "mismatched_evidence": {"n": len(mm_text), "verified": acc, "claimed": claimed,
                                    "rate": None if mrate is None else round(mrate, 4),
                                    "passes": mrate is not None and mrate <= MISMATCH_MAX},
            "kappa_vs_human_random": {"n": len(rnd_rows), "kappa": k,
                                      "below_limit": k is not None and k < KAPPA_LIMIT}}
        out[name]["passes"] = (out[name]["negative_citation"]["passes"]
                               and out[name]["mismatched_evidence"]["passes"])
    return out


def final_labels(fz, res, human, ctl):
    """{relation_id: (label 0/1, source)}. The human grade where there is one. Elsewhere the two
    judges agree by construction (every disagreement is on the sheet); a judge that failed a
    control does not count, so the label is the passing judge's; if both failed, the row has no
    final label and B-F falls back to the human's random rows (§6)."""
    ok = [n for n in ("judge1", "judge2") if ctl[n]["passes"]]
    out = {}
    for r in fz["sample"]:
        i = r["relation_id"]
        if i in human:
            out[i] = (human[i][1], "human")
        elif ok:
            labs = {int(res[n]["primary"][str(i)]["verified"]) for n in ok}
            if len(labs) != 1:
                raise SystemExit(f"relation {i}: passing judges disagree off the sheet")
            out[i] = (labs.pop(), "judges" if len(ok) == 2 else ok[0])
    return out


def rate(labels):
    k, n = sum(labels), len(labels)
    return {"supported": k, "n": n, "rate": round(k / n, 4) if n else None, "wilson95": C.wilson(k, n)}


def reading(fz, res, graded):
    human = {i: (o, g) for i, o, g in graded}
    ctl = controls(fz, res, human, fz["seed"])
    fin = final_labels(fz, res, human, ctl)
    by_id = {r["relation_id"]: r for r in fz["sample"]}
    if len(fin) == len(by_id):
        primary = rate([lab for lab, _ in fin.values()])
        primary["basis"] = "final label, all sampled rows"
    else:
        primary = rate([g for o, g in human.values() if o == "random"])
        primary["basis"] = "both judges failed a control: human grades on the random rows only"
    j_claims_unsupported = sum(
        1 for i, (lab, _) in fin.items() if not lab and any(
            res[n]["primary"][str(i)]["claims"] for n in ("judge1", "judge2")))
    group = lambda key: {k: rate([fin[i][0] for i in ids if i in fin]) for k, ids in sorted(
        collections.defaultdict(list, _groups(by_id, key)).items())}
    hum_by_origin = collections.defaultdict(list)
    for o, g in human.values():
        hum_by_origin[o].append(g)
    return {
        "B_F": primary,
        "controls": ctl,
        "final_label_source": dict(collections.Counter(s for _, s in fin.values())),
        "reported_not_interpreted": {
            "judge1_verified": rate([int(res["judge1"]["primary"][str(i)]["verified"]) for i in by_id]),
            "judge2_verified": rate([int(res["judge2"]["primary"][str(i)]["verified"]) for i in by_id]),
            "judge1_claimed": rate([int(res["judge1"]["primary"][str(i)]["claims"]) for i in by_id]),
            "judge2_claimed": rate([int(res["judge2"]["primary"][str(i)]["claims"]) for i in by_id]),
            "claimed_ceiling": {
                "rows_final_unsupported_but_claimed_by_a_judge": j_claims_unsupported,
                "ceiling": rate([1 if (fin[i][0] or any(res[n]["primary"][str(i)]["claims"]
                                                         for n in ("judge1", "judge2"))) else 0
                                 for i in fin])},
            "human_by_origin": {o: rate(g) for o, g in sorted(hum_by_origin.items())},
            "by_relation_reason": group("relation_reason"),
            "by_evidence_bucket": group("bucket")}}


def _groups(by_id, key):
    g = collections.defaultdict(list)
    for i, r in by_id.items():
        g[str(r[key])].append(i)
    return g


def main():
    ap = argparse.ArgumentParser()
    for k in ("private", "freeze-ref", "judges-ref", "sheet-ref", "human-ref"):
        ap.add_argument(f"--{k}", required=True)
    a = ap.parse_args()
    P = C.private(a.private)
    com = C.ordered(C.ROOT, [("FREEZE", a.freeze_ref), ("JUDGES", a.judges_ref),
                             ("SHEET", a.sheet_ref), ("HUMAN", a.human_ref)])
    C.same_private(com["FREEZE"], "freeze_json_sha256", P / "freeze.json")
    C.same_private(com["JUDGES"], "judges_json_sha256", P / "judges.json")
    C.same_private(com["HUMAN"], "graded_sheet_sha256", P / "human-sheet.csv")
    fz = json.loads((P / "freeze.json").read_text(encoding="utf-8"))
    res = json.loads((P / "judges.json").read_text(encoding="utf-8"))
    sel = H.select(fz, res, fz["seed"])
    if C.sha_json(sel) != com["SHEET"]["selection_sha256"]:
        sys.exit("refusing: the recomputed selection is not the committed one")
    graded = H.read_sheet(P / "human-sheet.csv", fz, sel)
    if C.sha_json(graded) != com["HUMAN"]["grades_sha256"]:
        sys.exit("refusing: the grades are not the committed ones")
    out = reading(fz, res, graded)
    out["commits"] = {n: com[n]["_commit"] for n in C.COMMITS}
    out["tag_commit"] = com["_tag"]
    day = datetime.date.today().isoformat()
    C.write_public(HERE / f"READING-{day}.json", out)
    print(json.dumps(out["B_F"]), json.dumps({n: out["controls"][n]["passes"] for n in out["controls"]}))


if __name__ == "__main__":
    main()
