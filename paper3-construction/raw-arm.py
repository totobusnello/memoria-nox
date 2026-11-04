#!/usr/bin/env python3
"""Raw-evidence arm on the 242 — registered in PREREGISTRATION-DRAFT.md §15 (v1.4).

Two materials per confirmatory instance, both restricted to the annotated evidence sessions:
  E-raw        evidence sessions as raw turns, chronological (reader-ceiling.raw_material)
  E-dist(C2)   C2 units of the same sessions from the confirmatory cache, served by serve()
Reader R3, the two registered judges. Cell 11 is read from the confirmatory rows (no call).

  python3 -I raw-arm.py --confirm-cache <cache.sqlite> --out <dir>                    estimate
  python3 -I raw-arm.py --confirm-cache <...> --out <dir> --yes --cap-usd 10          run
  python3 -I raw-arm.py --out <dir> --analyze                                         re-analyze
"""
import argparse
import hashlib
import importlib.util
import json
import os
import pathlib
import random
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor

HERE = pathlib.Path(__file__).resolve().parent


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


lr = load("lr", "lme-run.py")
la = load("la", "lme-analyze.py")
rc = load("rc", "reader-ceiling.py")

READER = "R3"
ARMS = ("E-dist", "E-raw")
DELTA = 0.10
FLOOR_RAW = 0.60
CONFIRM_ROWS = HERE / "runs" / "confirm-2026-11-04" / "rows.ndjson"


def analyze(out, data, confirm):
    rows = [json.loads(l) for l in open(out / "rows-raw-arm.ndjson")]
    by = {(r["arm"], r["qid"]): r for r in rows}
    assert all((a, q) in by for a in ARMS for q in confirm), "incomplete run: no inference (§15.7)"
    c11 = {}
    for l in open(CONFIRM_ROWS):
        r = json.loads(l)
        if r["cell"] == "11" and r["variant"] == r["qid"] and r["qid"] in confirm:
            c11[r["qid"]] = r
    assert len(c11) == len(confirm)
    for q, r in c11.items():
        by[("cell11", q)] = r
    qids = sorted(confirm)
    cl = la.clusters(qids, data)
    lines = []

    def p(s=""):
        print(s)
        lines.append(s)

    def acc(arm, key, ids):
        return sum(bool(by[(arm, q)][key]) for q in ids) / len(ids)

    p("RAW-EVIDENCE ARM · registered v1.4 (§15) · 242 confirmatory instances · reader R3")
    p("")
    p(f"{'arm':8s} {'acc j1':>7s} {'j2':>6s} {'abst':>6s} {'STOP':>6s} {'chars':>9s}")
    summ = {}
    for arm in ("cell11",) + ARMS:
        rr = [by[(arm, q)] for q in qids]
        s = {"acc_j1": acc(arm, "correct", qids), "acc_j2": acc(arm, "correct_j2", qids),
             "abst": sum(bool(x.get("abstained")) for x in rr) / len(rr),
             "stop": sum(x.get("finish") == "STOP" for x in rr) / len(rr),
             "mean_chars": sum(x.get("material_chars", x.get("served_chars", 0)) for x in rr) / len(rr)}
        summ[arm] = s
        p(f"{arm:8s} {s['acc_j1']:7.3f} {s['acc_j2']:6.3f} {s['abst']:6.3f} {s['stop']:6.1%} "
          f"{s['mean_chars']:9,.0f}")
    p("")
    floor_ok = summ["E-raw"]["acc_j1"] >= FLOOR_RAW
    p(f"instrument check: acc(E-raw) j1 = {summ['E-raw']['acc_j1']:.3f} "
      f"{'>=' if floor_ok else '<'} {FLOOR_RAW} -> {'PASS' if floor_ok else 'FAIL: H4 not interpreted'}")
    p("")
    res = {}
    for name, a, b, prim in (("H4  E-dist(C2) - E-raw", "E-dist", "E-raw", True),
                             ("cell11 - E-raw", "cell11", "E-raw", False),
                             ("cell11 - E-dist(C2)", "cell11", "E-dist", False)):
        for key, jn in (("correct", "j1"), ("correct_j2", "j2")):
            fn = (lambda ids, a=a, b=b, key=key: acc(a, key, ids) - acc(b, key, ids))
            est = fn(qids)
            lo, hi, _ = la.boot(fn, qids, cl, 0.05, random.Random(la.SEED))
            disc = (sum(bool(by[(a, q)][key]) and not bool(by[(b, q)][key]) for q in qids),
                    sum(bool(by[(b, q)][key]) and not bool(by[(a, q)][key]) for q in qids))
            res[f"{name}/{jn}"] = [est, lo, hi, *disc]
            p(f"{name:24s} {jn}: {est*100:+.1f} pp [{lo*100:+.1f}, {hi*100:+.1f}] · "
              f"discordant {disc[0]}/{disc[1]}")
    p("")
    for jn in ("j1", "j2"):
        est, lo, hi = res[f"H4  E-dist(C2) - E-raw/{jn}"][:3]
        worse, ni = hi < 0, lo > -DELTA
        verdict = ("both: worse than raw evidence, by less than delta" if worse and ni else
                   "C2 units lose to raw evidence" if worse else
                   "non-inferior at delta = 10 pp" if ni else "inconclusive")
        p(f"H4 decision ({jn}): {verdict}")
    p(f"G = {len(set(cl.values()))} answer-session clusters")
    p("")
    types = sorted({by[('E-raw', q)]["question_type"] for q in qids})
    p("by question_type, judge 1:")
    p(f"{'type':28s} {'n':>4s} " + " ".join(f"{a:>7s}" for a in ("cell11",) + ARMS))
    for t in types:
        ids = [q for q in qids if by[("E-raw", q)]["question_type"] == t]
        p(f"{t:28s} {len(ids):4d} " + " ".join(f"{acc(a, 'correct', ids):7.3f}" for a in ("cell11",) + ARMS))
    (out / "raw-arm.txt").write_text("\n".join(lines) + "\n")
    (out / "raw-arm.json").write_text(json.dumps(
        {"summary": summ, "contrasts": res, "instrument_check_pass": floor_ok, "delta": DELTA,
         "raw_arm_sha256": hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
         "runner_sha256": hashlib.sha256((HERE / "lme-run.py").read_bytes()).hexdigest()},
        indent=1, sort_keys=True) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm-cache")
    ap.add_argument("--out", required=True)
    ap.add_argument("--data", default=la.DATA)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--cap-usd", type=float, default=0)
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--analyze", action="store_true")
    a = ap.parse_args()

    confirm = set(json.load(open(HERE / "v13-manifest.json"))["confirm"])
    assert len(confirm) == 242
    data = {r["question_id"]: r for r in json.load(open(a.data))}
    out = pathlib.Path(a.out)
    if a.analyze:
        analyze(out, data, confirm)
        return
    out.mkdir(parents=True, exist_ok=True)
    cpath = out / "cache.sqlite"
    if not cpath.exists():
        shutil.copyfile(a.confirm_cache, cpath)   # the source cache is never written
    cache = lr.Cache(str(cpath))

    mats = []
    for q in sorted(confirm):
        r = data[q]
        ev = sorted(lr.evidence(r))
        ub = rc.cached_units(cache, r, "C2", ev)
        missing = sum(1 for i in ev for b in lr.session_blocks(r["haystack_sessions"][i])
                      if cache.get(lr.h("distill", "C2", lr.PROMPTS["C2"], b)) is None)
        assert missing == 0, f"{q}: {missing} evidence blocks not in the C2 cache"
        full = [ub.get(i, []) for i in range(len(r["haystack_sessions"]))]
        for arm, mat in (("E-dist", lr.serve(full, ev, r)), ("E-raw", rc.raw_material(r, ev))):
            mats.append({"qid": q, "arm": arm, "material": mat, "question": lr.question_text(r),
                         "q_plain": r["question"], "reference": str(r["answer"]),
                         "question_type": r["question_type"], "n_evidence": len(ev),
                         "material_sha256": hashlib.sha256(mat.encode()).hexdigest()})
    for arm in ARMS:
        ch = [len(m["material"]) for m in mats if m["arm"] == arm]
        print(f"{arm}: n={len(ch)} · mean {sum(ch)/len(ch):,.0f} chars · empty {sum(c == 0 for c in ch)}")
    _, _, _, p_in, p_out = lr.READERS[READER]
    chars = sum(len(m["material"]) for m in mats)
    print(f"  {READER} ~US$ {chars / 4 * p_in + len(mats) * 600 * p_out:.2f} (answers only; judges extra)")
    if not a.yes:
        print("estimate only; pass --yes to run")
        return

    led = lr.Ledger(a.cap_usd)
    t0 = time.time()

    def run(m):
        av = lr.answer(cache, led, m["material"] or "(vazio)", m["question"], READER)
        jv = lr.judge(cache, led, m["reference"], av["text"], m["q_plain"])
        j2 = lr.judge2(cache, led, m["reference"], av["text"], m["q_plain"])
        return {"reader": READER, "qid": m["qid"], "arm": m["arm"],
                "question_type": m["question_type"], "n_evidence": m["n_evidence"],
                "material_chars": len(m["material"]), "material_sha256": m["material_sha256"],
                "reference": m["reference"], "answer": av["text"], "finish": av.get("finish"),
                "answer_model_version": av.get("model_version"),
                "abstained": lr.abstained(av["text"]), "judge": jv,
                "correct": (jv.get("contem") or 0) > lr.THR, "correct_j2": bool(j2.get("correta"))}

    rows = []
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for n, row in enumerate(ex.map(run, mats)):
            rows.append(row)
            if (n + 1) % 50 == 0 or n + 1 == len(mats):
                print(f"  {n+1}/{len(mats)} · US$ {led.usd:.2f} · {time.time()-t0:.0f}s", flush=True)
    with open(out / "rows-raw-arm.ndjson", "w") as f:
        for row in sorted(rows, key=lambda x: (x["arm"], x["qid"])):
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    (out / "receipt.json").write_text(json.dumps(
        {"rows": len(rows), "spend_usd": round(led.usd, 4), "calls": led.n,
         "seconds": round(time.time() - t0), "cap_usd": a.cap_usd}, indent=1) + "\n")
    print(f"rows written: {len(rows)} · spend US$ {led.usd:.4f}")
    analyze(out, data, confirm)


if __name__ == "__main__":
    main()
