#!/usr/bin/env python3
"""Reader calibration of amendment v1.2 (§13.4-13.6). Committed and tagged before its first call.

It answers ONE question: which of the readers R0-R3 (lme-run.py READERS) clears the answerable
floor with margin while staying at the floor without evidence. It does that on the 200 spent
stage-1 instances, and it builds only two cells there:

  cell 11   full window, criterion C1, all 200          the floor
  pos       full window minus every answer session, C1, the 40 of control_subsample

No other cell is built under a new reader — not 00, 01, 10, the doses, neg, lenmatch or the
counterfactual — so no contrast can be computed from what this script produces.

The material is rebuilt from the stage-1 cache and must hash-equal the stage-1 row's
material_sha256, row by row, or the script stops before any call. Nothing is re-distilled: the
143 blocks that failed in stage 1 stay empty, exactly as they were served there. R0 is the stage-1
reader under its stage-1 cache key, so its rows must reproduce stage 1's verdicts exactly.

Selection (§13.6), applied by this script and printed, never chosen by hand:
  pass      acc_judge1(11) >= 0.55  and  acc_judge1(pos) <= 0.10  and  finish STOP on >= 98% of rows
  selected  the passing reader with the lowest measured cost per answer; NONE if no reader passes

  python3 -I reader-calibration.py --stage1-cache <stage-1 cache.sqlite> --out <dir>          estimate
  python3 -I reader-calibration.py --stage1-cache <...> --out <dir> --yes --cap-usd 25          run
"""
import argparse
import hashlib
import importlib.util
import json
import os
import pathlib
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("lr", HERE / "lme-run.py")
lr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lr)

ORDER = ("R0", "R1", "R2", "R3")
FLOOR_CAL, POS_MAX, STOP_MIN = 0.55, 0.10, 0.98
STAGE1_ROWS = HERE / "runs" / "stage1-2026-11-03" / "rows.ndjson"


def cached_units(cache, r, crit):
    out = []
    for s in r["haystack_sessions"]:
        sb = []
        for b in lr.session_blocks(s):
            v = cache.get(lr.h("distill", crit, lr.PROMPTS[crit], b))
            sb.append(v["units"] if v else [])   # failed in stage 1 -> served empty there too
        out.append(sb)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage1-cache", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--data", default=os.path.expanduser(
        "~/datasets/longmemeval/longmemeval_s_cleaned.json"))
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--cap-usd", type=float, default=0)
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()

    man = json.load(open(HERE / "stage1-manifest.json"))
    data = {r["question_id"]: r for r in json.load(open(a.data))}
    s1 = {(x["variant"], x["cell"]): x for x in map(json.loads, open(STAGE1_ROWS))}
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cpath = out / "cache.sqlite"
    if not cpath.exists():
        shutil.copyfile(a.stage1_cache, cpath)   # the stage-1 cache itself is never written
    cache = lr.Cache(str(cpath))

    # materials, verified against stage 1 before anything is spent
    mats = []
    for q in man["stage1"]:
        r = data[q]
        ub = cached_units(cache, r, "C1")
        for cell in (["11", "pos"] if q in man["control_subsample"] else ["11"]):
            crit, sess = lr.cell_spec(cell, r)
            assert crit == "C1"
            mat = lr.serve(ub, sess, r)
            sha = hashlib.sha256(mat.encode()).hexdigest()
            want = s1[(q, cell)]["material_sha256"]
            if sha != want:
                sys.exit(f"material of {q}/{cell} differs from stage 1 ({sha[:12]} != {want[:12]})")
            mats.append({"qid": q, "cell": cell, "material": mat, "question": lr.question_text(r),
                         "q_plain": r["question"], "reference": str(r["answer"]),
                         "question_type": r["question_type"]})
    n11 = sum(m["cell"] == "11" for m in mats)
    npos = len(mats) - n11
    chars = sum(len(m["material"]) for m in mats)
    print(f"materials verified against stage 1: {n11} cell-11 + {npos} pos, all hashes equal")
    for rid in ORDER[1:]:
        _, _, _, p_in, p_out = lr.READERS[rid]
        print(f"  {rid} {lr.READERS[rid][0]:22s} prompt {lr.READERS[rid][1]} · "
              f"~US$ {chars / 4 * p_in + len(mats) * 600 * p_out:.2f} (chars/4 tokens, 600 out)")
    if not a.yes:
        print("estimate only; pass --yes to run")
        return

    led = lr.Ledger(a.cap_usd)
    t0 = time.time()
    jobs = [(rid, m) for rid in ORDER for m in mats]

    def run(job):
        rid, m = job
        av = lr.answer(cache, led, m["material"] or "(vazio)", m["question"], rid)
        jv = lr.judge(cache, led, m["reference"], av["text"], m["q_plain"])
        j2 = lr.judge2(cache, led, m["reference"], av["text"], m["q_plain"])
        _, _, _, p_in, p_out = lr.READERS[rid]
        return {"reader": rid, "qid": m["qid"], "cell": m["cell"],
                "question_type": m["question_type"], "reference": m["reference"],
                "answer": av["text"], "finish": av.get("finish"),
                "answer_model_version": av.get("model_version"),
                "answer_usd": (av.get("tin") or 0) * p_in + (av.get("tout") or 0) * p_out,
                "abstained": lr.abstained(av["text"]), "judge": jv,
                "correct": (jv.get("contem") or 0) > lr.THR, "correct_j2": bool(j2.get("correta"))}

    rows = []
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for n, row in enumerate(ex.map(run, jobs)):
            rows.append(row)
            if (n + 1) % 50 == 0 or n + 1 == len(jobs):
                print(f"  {n+1}/{len(jobs)} · US$ {led.usd:.2f} · {time.time()-t0:.0f}s", flush=True)

    # R0 must replay stage 1 verdict for verdict
    bad = [(x["qid"], x["cell"]) for x in rows if x["reader"] == "R0"
           and (x["correct"], x["correct_j2"]) != (s1[(x["qid"], x["cell"])]["correct"],
                                                    s1[(x["qid"], x["cell"])]["correct_j2"])]
    if bad:
        sys.exit(f"R0 does not replay stage 1 on {len(bad)} rows, e.g. {bad[:3]}")

    lines, summ = [], {}

    def p(s=""):
        print(s)
        lines.append(s)

    p("READER CALIBRATION · v1.2 §13.6 · 200 stage-1 instances (cell 11) + 40 (pos)")
    p(f"pass: acc_j1(11) >= {FLOOR_CAL} and acc_j1(pos) <= {POS_MAX} and STOP >= {STOP_MIN:.0%}")
    p("R0 replays stage 1 verdict for verdict: yes")
    p("")
    p(f"{'id':3s} {'model':22s} {'pr':2s} {'acc11 j1':>8s} {'j2':>6s} {'abst11':>7s} "
      f"{'pos j1':>7s} {'abstpos':>7s} {'STOP':>6s} {'US$/ans':>9s}  verdict")
    for rid in ORDER:
        rr = [x for x in rows if x["reader"] == rid]
        c11 = [x for x in rr if x["cell"] == "11"]
        cp = [x for x in rr if x["cell"] == "pos"]
        acc11 = sum(x["correct"] for x in c11) / len(c11)
        acc11b = sum(x["correct_j2"] for x in c11) / len(c11)
        accp = sum(x["correct"] for x in cp) / len(cp)
        stopf = sum(x["finish"] == "STOP" for x in rr) / len(rr)
        cost = sum(x["answer_usd"] for x in rr) / len(rr)
        ok = acc11 >= FLOOR_CAL and accp <= POS_MAX and stopf >= STOP_MIN
        summ[rid] = {"model": lr.READERS[rid][0], "prompt": lr.READERS[rid][1],
                     "acc11_j1": acc11, "acc11_j2": acc11b,
                     "abst11": sum(x["abstained"] for x in c11) / len(c11),
                     "accpos_j1": accp, "abstpos": sum(x["abstained"] for x in cp) / len(cp),
                     "stop_frac": stopf, "usd_per_answer": cost, "pass": ok}
        s = summ[rid]
        p(f"{rid:3s} {s['model']:22s} {s['prompt']:2s} {acc11:8.3f} {acc11b:6.3f} "
          f"{s['abst11']:7.3f} {accp:7.3f} {s['abstpos']:7.3f} {stopf:6.1%} {cost:9.5f}  "
          f"{'PASS' if ok else 'fail'}")
    passing = [r for r in ORDER if summ[r]["pass"]]
    sel = min(passing, key=lambda r: (summ[r]["usd_per_answer"], r)) if passing else "NONE"
    p("")
    p(f"SELECTED: {sel}" + ("" if passing else "  -> v1.2 stops here (§13.6)"))
    p(f"spend US$ {led.usd:.4f}")

    with open(out / "rows-calibration.ndjson", "w") as f:
        for row in sorted(rows, key=lambda x: (x["reader"], x["qid"], x["cell"])):
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    (out / "calibration.txt").write_text("\n".join(lines) + "\n")
    (out / "calibration.json").write_text(json.dumps(
        {"summary": summ, "selected": sel, "spend_usd": round(led.usd, 4), "calls": led.n,
         "seconds": round(time.time() - t0),
         "runner_sha256": hashlib.sha256((HERE / "lme-run.py").read_bytes()).hexdigest(),
         "calibration_sha256": hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()},
        indent=1, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
