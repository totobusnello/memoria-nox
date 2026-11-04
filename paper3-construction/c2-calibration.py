#!/usr/bin/env python3
"""Criterion calibration of amendment v1.3 (§14.4-14.5). Committed and tagged before its first call.

ONE candidate, so nothing is selected: it asks whether criterion C2 (lme-run.py PROMPTS["C2"]),
read by R3, clears the answerable floor with margin on the 200 spent stage-1 instances while
staying at the floor without evidence. It distils every block of those 200 instances under C2,
and builds only:

  cell 11   full window, C2, all 200                             the floor
  pos       full window minus every answer session, C2, the 40 of control_subsample
  E-dist    evidence sessions only, C2 — exploratory, read against READER-CEILING.md, not in the rule

No cell under C0, no cut window, no dose, neg, lenmatch or counterfactual: no contrast of the
2x2 can be computed from what this script produces.

  pass   acc_judge1(11) >= 0.55  and  acc_judge1(pos) <= 0.10  and  STOP on >= 98% of R3 rows
  fail   v1.3 stops; no other criterion is tried without a new registered amendment

  python3 -I c2-calibration.py --stage1-cache <stage-1 cache.sqlite> --out <dir>             estimate
  python3 -I c2-calibration.py --stage1-cache <...> --out <dir> --yes --cap-usd 30            run
"""
import argparse
import hashlib
import importlib.util
import json
import os
import pathlib
import shutil
import time
from concurrent.futures import ThreadPoolExecutor

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("lr", HERE / "lme-run.py")
lr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lr)

READER, CRIT = "R3", "C2"
FLOOR_CAL, POS_MAX, STOP_MIN = 0.55, 0.10, 0.98
BLOCK_USD = 1.48e-4     # stage 1 measured: US$ 18.80 over 126,986 distills incl. answers and judges


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage1-cache", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--data", default=os.path.expanduser(
        "~/datasets/longmemeval/longmemeval_s_cleaned.json"))
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--cap-usd", type=float, default=0)
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()

    man = json.load(open(HERE / "stage1-manifest.json"))
    data = {r["question_id"]: r for r in json.load(open(a.data))}
    qids = man["stage1"]
    blocks = sorted({b for q in qids for s in data[q]["haystack_sessions"] for b in lr.session_blocks(s)})
    print(f"{len(qids)} instances · {len(blocks)} distinct blocks under {CRIT} · "
          f"~US$ {len(blocks) * BLOCK_USD * 1.2:.2f} distil (+20% for the longer prompt) · "
          f"~US$ {(200 + 40 + 200) * 0.035:.2f} answers")
    if not a.yes:
        print("estimate only; pass --yes to run")
        return

    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cpath = out / "cache.sqlite"
    if not cpath.exists():
        shutil.copyfile(a.stage1_cache, cpath)   # the stage-1 cache itself is never written
    cache = lr.Cache(str(cpath))
    led = lr.Ledger(a.cap_usd)
    t0 = time.time()

    # 1. distil
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for n, _ in enumerate(ex.map(lambda b: lr.distill(cache, led, CRIT, b), blocks)):
            if (n + 1) % 5000 == 0 or n + 1 == len(blocks):
                print(f"  distil {n+1}/{len(blocks)} · US$ {led.usd:.2f} · {time.time()-t0:.0f}s",
                      flush=True)
    failed = sum(1 for b in blocks if (cache.get(lr.h("distill", CRIT, lr.PROMPTS[CRIT], b)) or
                                        {"failed": True}).get("failed"))
    print(f"  failed blocks: {failed} of {len(blocks)} (served empty)")

    def ub(r):
        out = []
        for s in r["haystack_sessions"]:
            sb = []
            for b in lr.session_blocks(s):
                v = cache.get(lr.h("distill", CRIT, lr.PROMPTS[CRIT], b))
                sb.append(v["units"] if v else [])
            out.append(sb)
        return out

    # 2. materials
    lr.REPAIR = CRIT
    mats = []
    for q in qids:
        r = data[q]
        u = ub(r)
        cells = ["11", "pos"] if q in man["control_subsample"] else ["11"]
        for cell in cells:
            crit, sess = lr.cell_spec(cell, r)
            assert crit == CRIT
            mats.append((q, cell, lr.serve(u, sess, r)))
        mats.append((q, "E-dist", lr.serve(u, sorted(lr.evidence(r)), r)))

    # 3. read and judge
    def run(m):
        q, cell, mat = m
        r = data[q]
        av = lr.answer(cache, led, mat or "(vazio)", lr.question_text(r), READER)
        jv = lr.judge(cache, led, str(r["answer"]), av["text"], r["question"])
        j2 = lr.judge2(cache, led, str(r["answer"]), av["text"], r["question"])
        return {"qid": q, "cell": cell, "criterion": CRIT, "reader": READER,
                "question_type": r["question_type"], "reference": str(r["answer"]),
                "material_chars": len(mat), "material_sha256": hashlib.sha256(mat.encode()).hexdigest(),
                "answer": av["text"], "finish": av.get("finish"),
                "answer_model_version": av.get("model_version"),
                "abstained": lr.abstained(av["text"]), "judge": jv,
                "correct": (jv.get("contem") or 0) > lr.THR, "correct_j2": bool(j2.get("correta"))}

    rows = []
    with ThreadPoolExecutor(max_workers=12) as ex:
        for n, row in enumerate(ex.map(run, mats)):
            rows.append(row)
            if (n + 1) % 100 == 0 or n + 1 == len(mats):
                print(f"  read {n+1}/{len(mats)} · US$ {led.usd:.2f} · {time.time()-t0:.0f}s", flush=True)

    lines, summ = [], {}

    def p(s=""):
        print(s)
        lines.append(s)

    p(f"CRITERION CALIBRATION · v1.3 §14.5 · {CRIT} read by {READER} · 200 stage-1 instances")
    p(f"pass: acc_j1(11) >= {FLOOR_CAL} and acc_j1(pos) <= {POS_MAX} and STOP >= {STOP_MIN:.0%}")
    p(f"failed blocks: {failed} of {len(blocks)}")
    p("")
    p(f"{'cell':7s} {'n':>4s} {'acc j1':>7s} {'j2':>6s} {'abst':>6s} {'STOP':>6s} {'chars':>9s}")
    for cell in ("11", "pos", "E-dist"):
        rr = [x for x in rows if x["cell"] == cell]
        s = {"n": len(rr), "acc_j1": sum(x["correct"] for x in rr) / len(rr),
             "acc_j2": sum(x["correct_j2"] for x in rr) / len(rr),
             "abst": sum(x["abstained"] for x in rr) / len(rr),
             "stop": sum(x["finish"] == "STOP" for x in rr) / len(rr),
             "mean_chars": sum(x["material_chars"] for x in rr) / len(rr)}
        summ[cell] = s
        p(f"{cell:7s} {s['n']:4d} {s['acc_j1']:7.3f} {s['acc_j2']:6.3f} {s['abst']:6.3f} "
          f"{s['stop']:6.1%} {s['mean_chars']:9,.0f}")
    rule = [x for x in rows if x["cell"] in ("11", "pos")]
    stopf = sum(x["finish"] == "STOP" for x in rule) / len(rule)
    ok = summ["11"]["acc_j1"] >= FLOOR_CAL and summ["pos"]["acc_j1"] <= POS_MAX and stopf >= STOP_MIN
    p("")
    p(f"VERDICT: {'PASS -> confirmatory run on the 262 (§14.6)' if ok else 'FAIL -> v1.3 stops (§14.5)'}")
    p("")
    p("by question_type, judge 1, cell 11 / E-dist:")
    for t in sorted({x["question_type"] for x in rows}):
        a11 = [x["correct"] for x in rows if x["cell"] == "11" and x["question_type"] == t]
        ae = [x["correct"] for x in rows if x["cell"] == "E-dist" and x["question_type"] == t]
        p(f"  {t:28s} {len(a11):4d} {sum(a11)/len(a11):7.3f} {sum(ae)/len(ae):7.3f}")
    p("")
    p(f"spend US$ {led.usd:.4f} · {led.n} · {time.time()-t0:.0f}s")

    with open(out / "rows-c2-calibration.ndjson", "w") as f:
        for row in sorted(rows, key=lambda x: (x["cell"], x["qid"])):
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    (out / "c2-calibration.txt").write_text("\n".join(lines) + "\n")
    (out / "c2-calibration.json").write_text(json.dumps(
        {"summary": summ, "stop_frac_rule_rows": stopf, "pass": ok, "failed_blocks": failed,
         "blocks": len(blocks), "spend_usd": round(led.usd, 4), "calls": led.n,
         "runner_sha256": hashlib.sha256((HERE / "lme-run.py").read_bytes()).hexdigest(),
         "calibration_sha256": hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
         "c2_prompt_sha256": hashlib.sha256(lr.PROMPTS[CRIT].encode()).hexdigest()},
        indent=1, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
