#!/usr/bin/env python3
"""Reader ceiling — EXPLORATORY, not registered. Committed before its first call.

v1.2 selected no reader (§13.10): the best one, R3, reached acc(11) = 0.505 against a 0.55 bar.
Before deciding whether a v1.3 with a stronger reader is worth paying for, this asks how much of
the gap is the READER and how much is what it is SERVED. It runs on the same 200 spent stage-1
instances, and it builds no cell of the 2x2 — so, again, no contrast can be computed from it.

Two oracle materials per instance, both restricted to the answer (evidence) sessions:

  E-raw    the evidence sessions as raw turns, chronological: "[date] [ROLE]: content"
  E-dist   the C1 distilled units of the evidence sessions only, served exactly as cell 11 serves
           them (serve(), importance then recency) — from the stage-1 cache, nothing re-distilled

Read against cell 11 (all sessions, C1 units; 0.505 under R3) they split the loss in two:
  cell 11 -> E-dist   what the ~50 distractor sessions cost the reader (length / interference)
  E-dist  -> E-raw    what distillation costs (units lost or flattened)
  E-raw               the reader's own ceiling on this task with perfect retrieval

Readers: R3 (the best of v1.2) and R0 (the stage-1 reader), from lme-run.py READERS.
Judges: the registered two, unchanged.

  python3 -I reader-ceiling.py --stage1-cache <cache.sqlite> --out <dir>                 estimate
  python3 -I reader-ceiling.py --stage1-cache <...> --out <dir> --yes --cap-usd 8         run
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

READERS = ("R0", "R3")
ARMS = ("E-dist", "E-raw")
CAL_ROWS = HERE / "runs" / "calibration-2026-11-03" / "rows-calibration.ndjson"


def cached_units(cache, r, crit, idx):
    out = {}
    for i in idx:
        sb = []
        for b in lr.session_blocks(r["haystack_sessions"][i]):
            v = cache.get(lr.h("distill", crit, lr.PROMPTS[crit], b))
            sb.append(v["units"] if v else [])
        out[i] = sb
    return out


def raw_material(r, idx):
    lines = []
    for i in sorted(idx, key=lambda i: (r["haystack_dates"][i], i)):
        for t in r["haystack_sessions"][i]:
            lines.append(f"[{r['haystack_dates'][i]}] [{(t.get('role') or '').upper()}]: "
                         f"{t.get('content') or ''}")
    return "\n".join(lines)


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
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cpath = out / "cache.sqlite"
    if not cpath.exists():
        shutil.copyfile(a.stage1_cache, cpath)   # the source cache is never written
    cache = lr.Cache(str(cpath))

    mats = []
    for q in man["stage1"]:
        r = data[q]
        ev = sorted(lr.evidence(r))
        ub = cached_units(cache, r, "C1", ev)
        full = [ub.get(i, []) for i in range(len(r["haystack_sessions"]))]
        for arm, mat in (("E-dist", lr.serve(full, ev, r)), ("E-raw", raw_material(r, ev))):
            mats.append({"qid": q, "arm": arm, "material": mat, "question": lr.question_text(r),
                         "q_plain": r["question"], "reference": str(r["answer"]),
                         "question_type": r["question_type"], "n_evidence": len(ev),
                         "material_sha256": hashlib.sha256(mat.encode()).hexdigest()})
    for arm in ARMS:
        ch = [len(m["material"]) for m in mats if m["arm"] == arm]
        print(f"{arm}: n={len(ch)} · mean {sum(ch)/len(ch):,.0f} chars · "
              f"empty {sum(c == 0 for c in ch)}")
    for rid in READERS:
        _, _, _, p_in, p_out = lr.READERS[rid]
        chars = sum(len(m["material"]) for m in mats)
        print(f"  {rid} ~US$ {chars / 4 * p_in + len(mats) * 600 * p_out:.2f} (answers only)")
    if not a.yes:
        print("estimate only; pass --yes to run")
        return

    led = lr.Ledger(a.cap_usd)
    t0 = time.time()
    jobs = [(rid, m) for rid in READERS for m in mats]

    def run(job):
        rid, m = job
        av = lr.answer(cache, led, m["material"] or "(vazio)", m["question"], rid)
        jv = lr.judge(cache, led, m["reference"], av["text"], m["q_plain"])
        j2 = lr.judge2(cache, led, m["reference"], av["text"], m["q_plain"])
        return {"reader": rid, "qid": m["qid"], "arm": m["arm"],
                "question_type": m["question_type"], "n_evidence": m["n_evidence"],
                "material_chars": len(m["material"]), "material_sha256": m["material_sha256"],
                "reference": m["reference"], "answer": av["text"], "finish": av.get("finish"),
                "answer_model_version": av.get("model_version"),
                "abstained": lr.abstained(av["text"]), "judge": jv,
                "correct": (jv.get("contem") or 0) > lr.THR, "correct_j2": bool(j2.get("correta"))}

    rows = []
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for n, row in enumerate(ex.map(run, jobs)):
            rows.append(row)
            if (n + 1) % 100 == 0 or n + 1 == len(jobs):
                print(f"  {n+1}/{len(jobs)} · US$ {led.usd:.2f} · {time.time()-t0:.0f}s", flush=True)

    # cell 11 from the calibration, for the same readers and instances (no new call)
    cal = [x for x in map(json.loads, open(CAL_ROWS)) if x["cell"] == "11" and x["reader"] in READERS]
    for x in cal:
        x["arm"] = "cell11"

    lines, summ = [], {}

    def p(s=""):
        print(s)
        lines.append(s)

    p("READER CEILING · exploratory, not registered · 200 stage-1 instances")
    p("cell11 = all sessions, C1 units (from the v1.2 calibration); E-dist = evidence sessions,")
    p("C1 units; E-raw = evidence sessions, raw turns")
    p("")
    p(f"{'reader':6s} {'arm':7s} {'acc j1':>7s} {'j2':>6s} {'abst':>6s} {'STOP':>6s} {'chars':>9s}")
    for rid in READERS:
        for arm in ("cell11",) + ARMS:
            rr = [x for x in (cal if arm == "cell11" else rows) if x["reader"] == rid and x["arm"] == arm]
            s = {"n": len(rr), "acc_j1": sum(x["correct"] for x in rr) / len(rr),
                 "acc_j2": sum(x["correct_j2"] for x in rr) / len(rr),
                 "abst": sum(x["abstained"] for x in rr) / len(rr),
                 "stop": sum(x["finish"] == "STOP" for x in rr) / len(rr)}
            if arm != "cell11":
                s["mean_chars"] = sum(x["material_chars"] for x in rr) / len(rr)
            summ[f"{rid}/{arm}"] = s
            p(f"{rid:6s} {arm:7s} {s['acc_j1']:7.3f} {s['acc_j2']:6.3f} {s['abst']:6.3f} "
              f"{s['stop']:6.1%} {s.get('mean_chars', 0):9,.0f}")
    p("")
    types = sorted({x["question_type"] for x in rows})
    p("by question_type, judge 1, R3:")
    p(f"{'type':28s} {'n':>4s} " + " ".join(f"{a:>7s}" for a in ("cell11",) + ARMS))
    by = {}
    for t in types:
        vals = []
        for arm in ("cell11",) + ARMS:
            rr = [x for x in (cal if arm == "cell11" else rows)
                  if x["reader"] == "R3" and x["arm"] == arm and x["question_type"] == t]
            vals.append(sum(x["correct"] for x in rr) / len(rr))
        by[t] = dict(zip(("cell11",) + ARMS, vals))
        n = sum(1 for x in rows if x["reader"] == "R3" and x["arm"] == "E-raw" and x["question_type"] == t)
        p(f"{t:28s} {n:4d} " + " ".join(f"{v:7.3f}" for v in vals))
    p("")
    p(f"spend US$ {led.usd:.4f} · {led.n} calls · {time.time()-t0:.0f}s")

    with open(out / "rows-ceiling.ndjson", "w") as f:
        for row in sorted(rows, key=lambda x: (x["reader"], x["arm"], x["qid"])):
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    (out / "ceiling.txt").write_text("\n".join(lines) + "\n")
    (out / "ceiling.json").write_text(json.dumps(
        {"summary": summ, "by_type_R3_j1": by, "spend_usd": round(led.usd, 4), "calls": led.n,
         "runner_sha256": hashlib.sha256((HERE / "lme-run.py").read_bytes()).hexdigest(),
         "ceiling_sha256": hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()},
        indent=1, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
