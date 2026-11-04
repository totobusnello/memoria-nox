#!/usr/bin/env python3
"""Two more judges on the v1.4 raw-evidence arm — registered in PREREGISTRATION-DRAFT.md §16 (v1.5).

Judge 3 is glm-5.3 (Z.ai), judge 4 is gemini-4-argon. Both use judge 2's prompt (J2_PROMPT,
verbatim) and grade the 484 rows of runs/raw-arm-2026-11-04 (E-dist(C2) and E-raw on the 242).
No answer is regenerated: the rows' answers are graded as they stand.

Gate per new judge, before its rows count (§16.3): it rejects all 16 smoke abstentions (8 smoke
instances x 2 abstention strings, the §12.7 preflight) and accepts the reference answer itself on
at least 7 of the 8 smoke instances. A judge that fails is reported and left out of the committee.

Primary (§16.4): a committee label per row, correct iff at least 3 of the 4 judges accept it
(a 2-2 tie counts as not correct). H4's decision table (§15.4) is applied to that label.

  python3 -I h4-judges.py --out <dir> [--workers 8]        run (keys from the environment/files)
  python3 -I h4-judges.py --out <dir> --analyze            re-analyze from the rows, keyless
"""
import argparse
import hashlib
import importlib.util
import json
import os
import pathlib
import random
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = pathlib.Path(__file__).resolve().parent


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


lr = load("lr", "lme-run.py")
la = load("la", "lme-analyze.py")

RAW = HERE / "runs" / "raw-arm-2026-11-04" / "rows-raw-arm.ndjson"
J3_MODEL, J4_MODEL = "glm-5.3", "gemini-4-argon"
J3_URL = "https://api.z.ai/api/coding/paas/v4/chat/completions"
DELTA = 0.10
ABSTAIN = ("NAO SEI", "The information is not available in the retrieved sessions; I don't know.")
VERDICT = re.compile(r'"correta"\s*:\s*(true|false)')
MAX_CALLS = 1100


def _post(url, body, hdr, timeout=240):
    last = None
    for i in range(5):
        try:
            req = urllib.request.Request(url, json.dumps(body).encode(), hdr)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except Exception as e:      # retried; the last error is raised
            last = e
            time.sleep(3 * (i + 1))
    raise RuntimeError(str(last))


def glm_key():
    return pathlib.Path(os.path.expanduser("~/.config/glm/token")).read_text().strip()


class Counter:
    def __init__(self):
        self.n = 0

    def tick(self):
        self.n += 1
        if self.n > MAX_CALLS:
            raise SystemExit(f"CALL CAP REACHED: {self.n}")


def judge3(cache, cnt, ref, cand, q):
    k = lr.h("judge3", J3_MODEL, lr.J2_PROMPT, ref, cand, q)
    hit = cache.get(k)
    if hit is not None:
        return hit
    cnt.tick()
    d = _post(J3_URL, {"model": J3_MODEL, "temperature": 0, "max_tokens": 4096,
                       "thinking": {"type": "enabled"}, "reasoning_effort": "low",
                       "messages": [{"role": "user", "content":
                                     lr.J2_PROMPT.format(q=q, gold=ref, ans=cand)}]},
              {"Content-Type": "application/json", "Authorization": f"Bearer {glm_key()}"})
    txt = ((d.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    m = VERDICT.search(txt)
    if not m:
        raise RuntimeError(f"judge 3 gave no verdict: {txt[:90]!r}")
    v = {"correta": m.group(1) == "true", "model": d.get("model")}
    cache.put(k, "judge3", v)
    return v


def judge4(cache, cnt, ref, cand, q):
    k = lr.h("judge4", J4_MODEL, lr.J2_PROMPT, ref, cand, q)
    hit = cache.get(k)
    if hit is not None:
        return hit
    cnt.tick()
    body = {"contents": [{"parts": [{"text": lr.J2_PROMPT.format(q=q, gold=ref, ans=cand)}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 8192,
                                 "responseMimeType": "application/json",
                                 "thinkingConfig": {"thinkingLevel": "low"}}}
    d = _post(lr.gurl(J4_MODEL), body, {"Content-Type": "application/json"})
    c = (d.get("candidates") or [{}])[0]
    txt = "".join(p.get("text", "") for p in (c.get("content") or {}).get("parts") or [])
    m = VERDICT.search(txt)
    if not m:
        raise RuntimeError(f"judge 4 gave no verdict: {txt[:90]!r}")
    v = {"correta": m.group(1) == "true", "model_version": d.get("modelVersion")}
    cache.put(k, "judge4", v)
    return v


JUDGES = {"j3": judge3, "j4": judge4}


def run(out, data, workers):
    cache, cnt = lr.Cache(str(out / "cache.sqlite")), Counter()
    smoke = json.load(open(HERE / "stage1-manifest.json"))["smoke"]
    pre = {}
    for jn, fn in JUDGES.items():
        ab = [fn(cache, cnt, str(data[q]["answer"]), c, data[q]["question"])["correta"]
              for q in smoke for c in ABSTAIN]
        rf = [fn(cache, cnt, str(data[q]["answer"]), str(data[q]["answer"]), data[q]["question"])["correta"]
              for q in smoke]
        pre[jn] = {"abstentions_accepted": sum(ab), "of": len(ab),
                   "references_accepted": sum(rf), "of_ref": len(rf),
                   "pass": sum(ab) == 0 and sum(rf) >= 7}
        print(f"preflight {jn}: abstentions accepted {sum(ab)}/{len(ab)} · references accepted "
              f"{sum(rf)}/{len(rf)} -> {'PASS' if pre[jn]['pass'] else 'FAIL'}", flush=True)
    rows = [json.loads(l) for l in open(RAW)]
    assert len(rows) == 484

    def grade(r):
        q = data[r["qid"]]["question"]
        return {jn: fn(cache, cnt, r["reference"], r["answer"], q) for jn, fn in JUDGES.items()}

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        res = []
        for n, g in enumerate(ex.map(grade, rows)):
            res.append(g)
            if (n + 1) % 100 == 0 or n + 1 == len(rows):
                print(f"  {n+1}/{len(rows)} · {cnt.n} calls · {time.time()-t0:.0f}s", flush=True)
    with open(out / "rows-h4-judges.ndjson", "w") as f:
        for r, g in sorted(zip(rows, res), key=lambda x: (x[0]["arm"], x[0]["qid"])):
            f.write(json.dumps({"arm": r["arm"], "qid": r["qid"], "question_type": r["question_type"],
                                "j1": bool(r["correct"]), "j2": bool(r["correct_j2"]),
                                "j3": g["j3"]["correta"], "j4": g["j4"]["correta"],
                                "j3_model": g["j3"].get("model"),
                                "j4_model": g["j4"].get("model_version")},
                               ensure_ascii=False, sort_keys=True) + "\n")
    (out / "preflight.json").write_text(json.dumps(pre, indent=1) + "\n")
    (out / "receipt.json").write_text(json.dumps({"calls": cnt.n, "seconds": round(time.time() - t0),
                                                  "rows": len(rows)}, indent=1) + "\n")


def analyze(out, data):
    rows = [json.loads(l) for l in open(out / "rows-h4-judges.ndjson")]
    pre = json.load(open(out / "preflight.json"))
    by = {(r["arm"], r["qid"]): r for r in rows}
    qids = sorted({r["qid"] for r in rows})
    assert len(qids) == 242
    cl = la.clusters(qids, data)
    judges = ["j1", "j2"] + [j for j in ("j3", "j4") if pre[j]["pass"]]
    for r in rows:   # committee: >= 3 of 4 accept (2-2 counts as not correct), §16.4
        r["committee"] = sum(r[j] for j in ("j1", "j2", "j3", "j4")) >= 3 if len(judges) == 4 else None
    lines, res = [], {}

    def p(s=""):
        print(s)
        lines.append(s)

    p("H4 WITH FOUR JUDGES · registered v1.5 (§16) · 484 rows of the v1.4 arm")
    for j in ("j3", "j4"):
        x = pre[j]
        p(f"preflight {j}: abstentions accepted {x['abstentions_accepted']}/{x['of']}, references "
          f"accepted {x['references_accepted']}/{x['of_ref']} -> {'PASS' if x['pass'] else 'FAIL, excluded'}")
    p("")
    labels = judges + (["committee"] if len(judges) == 4 else [])
    p(f"{'label':10s} {'E-dist':>7s} {'E-raw':>7s}   H4 = E-dist - E-raw        discordant   reading")
    for j in labels:
        acc = lambda arm, ids: sum(bool(by[(arm, q)][j]) for q in ids) / len(ids)
        fn = lambda ids: acc("E-dist", ids) - acc("E-raw", ids)
        est = fn(qids)
        lo, hi, _ = la.boot(fn, qids, cl, 0.05, random.Random(la.SEED))
        disc = (sum(bool(by[("E-dist", q)][j]) and not bool(by[("E-raw", q)][j]) for q in qids),
                sum(bool(by[("E-raw", q)][j]) and not bool(by[("E-dist", q)][j]) for q in qids))
        worse, ni = hi < 0, lo > -DELTA
        reading = ("both: worse, by less than delta" if worse and ni else "units lose to raw evidence"
                   if worse else "non-inferior at 10 pp" if ni else "inconclusive")
        res[j] = {"est": est, "lo": lo, "hi": hi, "disc": disc, "reading": reading}
        p(f"{j:10s} {acc('E-dist', qids):7.3f} {acc('E-raw', qids):7.3f}   {est*100:+.1f} pp "
          f"[{lo*100:+.1f}, {hi*100:+.1f}]   {disc[0]:>3d}/{disc[1]:<3d}     {reading}")
    p("")
    ties = sum(1 for r in rows if sum(r[j] for j in ("j1", "j2", "j3", "j4")) == 2)
    p(f"2-2 ties (counted as not correct by the committee): {ties} of {len(rows)} rows")
    agree = {f"{a}-{b}": sum(r[a] == r[b] for r in rows) / len(rows)
             for i, a in enumerate(("j1", "j2", "j3", "j4")) for b in ("j1", "j2", "j3", "j4")[i + 1:]}
    p("pairwise agreement: " + " · ".join(f"{k} {v:.3f}" for k, v in agree.items()))
    (out / "h4-judges.txt").write_text("\n".join(lines) + "\n")
    (out / "h4-judges.json").write_text(json.dumps(
        {"results": res, "preflight": pre, "ties": ties, "agreement": agree,
         "script_sha256": hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()},
        indent=1, sort_keys=True) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--data", default=la.DATA)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--analyze", action="store_true")
    a = ap.parse_args()
    data = {r["question_id"]: r for r in json.load(open(a.data))}
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if not a.analyze:
        run(out, data, a.workers)
    analyze(out, data)


if __name__ == "__main__":
    main()
