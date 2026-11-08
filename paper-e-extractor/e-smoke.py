#!/usr/bin/env python3
"""Paper E cost smoke. Measures what the strong extractor costs per block, and nothing else.

What it reads: 40 blocks drawn (fixed seed) from the haystacks of the 200 Paper 3 stage-1
instances, which are already spent, excluding any block that also occurs in the 242 confirmatory
haystacks. No reader, no judge, no question: no outcome of any instance is computed or seen.

What it calls, per block:
  gemini-2.5-pro         x {C0, C2, P} x {default thinking, thinkingBudget 128}
  gemini-2.5-flash-lite  x {P}          (C0 and C2 on flash-lite are priced by Paper 3 already)
Every body is the Paper 3 distill body (same text, responseMimeType, temperature 0.1); only the
model and, in one arm, the thinking budget change.

What it writes: token counts, unit counts, parse failures and latency per call. No block text and
no memory text, so the repo gains no corpus content and nobody reads an extraction before the
pre-registration.

  python3 -I e-smoke.py --out <dir> [--set pro|flash]   plan only, spends nothing
  GEMINI_API_KEY=... python3 -I e-smoke.py --out <dir> --yes [--cap-usd 5]
"""
import argparse
import hashlib
import json
import os
import pathlib
import random
import statistics as st
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e_prompts  # noqa: E402

lme = e_prompts.lme
P3 = HERE.parent / "paper3-construction"
SEED = "paper-e-smoke-v1"
N_BLOCKS = 40
PRICE = {"gemini-2.5-pro": (1.25e-6, 10.0e-6),        # ai.google.dev pricing, read 2026-11-08,
         "gemini-2.5-flash": (0.30e-6, 2.50e-6),       # standard tier, prompts <= 200k tokens
         "gemini-2.5-flash-lite": (0.10e-6, 0.40e-6)}
ARMS = [("gemini-2.5-pro", "dyn", None, c) for c in ("C0", "C2", "P")] + \
       [("gemini-2.5-pro", "b128", {"thinkingBudget": 128}, c) for c in ("C0", "C2", "P")] + \
       [("gemini-2.5-flash-lite", "base", None, "P")]
# --set flash (added after the pro arms priced the design out): the middle model of the same
# generation, thinking off, so the body is the flash-lite body with only the model name changed
ARM_SETS = {"pro": ARMS,
            "flash": [("gemini-2.5-flash", "t0", {"thinkingBudget": 0}, c) for c in ("C0", "C2", "P")]}


def all_blocks(data, qids):
    out = []
    for q in qids:
        for s in data[q]["haystack_sessions"]:
            out.extend(lme.session_blocks(s))
    return out


def call(model, think, crit, block):
    gen = {"responseMimeType": "application/json", "temperature": 0.1}
    if think:
        gen["thinkingConfig"] = think
    body = {"contents": [{"role": "user",
                          "parts": [{"text": e_prompts.PROMPTS[crit] + "\n\nConversa:\n" + block}]}],
            "generationConfig": gen}
    t0 = time.time()
    try:
        d = lme.post(lme.gurl(model), body, {"Content-Type": "application/json"}, timeout=300)
    except Exception as e:  # recorded, never retried past lme.post's own retries
        return {"error": str(e)[:160], "secs": round(time.time() - t0, 2)}
    c = (d.get("candidates") or [{}])[0]
    txt = "".join(p.get("text", "") for p in (c.get("content") or {}).get("parts") or [])
    u = d.get("usageMetadata") or {}
    try:  # parse_ok: the Paper 3 parser ({"memories": [...]} only); mem: Paper E's, which also
        j = json.loads(txt) if txt else None  # accepts a top-level list (SMOKE-RESULT.md)
        parse_ok = isinstance(j, dict)
        mem = (j.get("memories") or []) if isinstance(j, dict) else (j if isinstance(j, list) else [])
        shape = "dict" if isinstance(j, dict) else ("list" if j else "empty_list" if j == [] else "none")
    except Exception:
        mem, parse_ok, shape = [], False, "unparseable"
    kept = [m for m in mem if isinstance(m, dict) and (m.get("importance") or 0) >= 0.5]
    return {"tin": u.get("promptTokenCount", 0) or 0,
            "tcand": u.get("candidatesTokenCount", 0) or 0,
            "tthink": u.get("thoughtsTokenCount", 0) or 0,
            "shape": shape, "units_raw": len(mem), "units_kept": len(kept), "parse_ok": parse_ok,
            "finish": c.get("finishReason"), "model_version": d.get("modelVersion"),
            "secs": round(time.time() - t0, 2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--data", default=os.path.expanduser(
        "~/datasets/longmemeval/longmemeval_s_cleaned.json"))
    ap.add_argument("--cap-usd", type=float, default=5.0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--set", choices=sorted(ARM_SETS), default="pro")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()
    ARMS_ = ARM_SETS[a.set]
    if a.cap_usd > 10:
        sys.exit("the smoke's cap is at most US$ 10")

    data = {r["question_id"]: r for r in json.load(open(a.data))}
    s1 = json.load(open(P3 / "stage1-manifest.json"))["stage1"]
    v13 = json.load(open(P3 / "v13-manifest.json"))["confirm"]
    confirm_blocks = set(all_blocks(data, v13))
    pool = sorted(set(all_blocks(data, s1)) - confirm_blocks)
    sample = random.Random(SEED).sample(pool, N_BLOCKS)
    est_in = sum(len(b) for b in sample) / N_BLOCKS
    print(f"pool {len(pool)} spent-only blocks; sample {N_BLOCKS}; mean block {est_in:.0f} chars")
    print(f"arms {len(ARMS_)}, calls {len(ARMS_) * N_BLOCKS}, cap US$ {a.cap_usd:.2f}")
    for c in e_prompts.PROMPTS:
        print(f"  prompt {c} sha256 {e_prompts.sha(c)[:16]}")
    if not a.yes:
        print("plan only (add --yes to spend)")
        return

    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    lock, spent, recs = threading.Lock(), [0.0], []

    def job(arm, i):
        model, tag, think, crit = arm
        with lock:
            if spent[0] > a.cap_usd:
                return
        r = call(model, think, crit, sample[i])
        pin, pout = PRICE[model]
        usd = r.get("tin", 0) * pin + (r.get("tcand", 0) + r.get("tthink", 0)) * pout
        r.update(model=model, arm=tag, crit=crit, block=i, usd=usd,
                 block_sha256=hashlib.sha256(sample[i].encode()).hexdigest())
        with lock:
            spent[0] += usd
            recs.append(r)

    t0 = time.time()
    with ThreadPoolExecutor(a.workers) as ex:
        list(ex.map(lambda x: job(*x), [(arm, i) for arm in ARMS_ for i in range(N_BLOCKS)]))

    summ = {}
    for model, tag, _, crit in ARMS_:
        rs = [r for r in recs if r["model"] == model and r["arm"] == tag and r["crit"] == crit]
        ok = [r for r in rs if "error" not in r]
        summ[f"{model}|{tag}|{crit}"] = {
            "calls": len(rs), "errors": len(rs) - len(ok),
            "parse_fail": sum(not r["parse_ok"] for r in ok),
            "finish_not_stop": sum(r["finish"] != "STOP" for r in ok),
            "tin_mean": round(st.mean(r["tin"] for r in ok), 1) if ok else None,
            "tcand_mean": round(st.mean(r["tcand"] for r in ok), 1) if ok else None,
            "tthink_mean": round(st.mean(r["tthink"] for r in ok), 1) if ok else None,
            "tthink_max": max((r["tthink"] for r in ok), default=None),
            "units_kept_mean": round(st.mean(r["units_kept"] for r in ok), 2) if ok else None,
            "usd_per_call": round(st.mean(r["usd"] for r in ok), 6) if ok else None,
            "secs_median": round(st.median(r["secs"] for r in ok), 2) if ok else None,
            "model_versions": sorted({r["model_version"] for r in ok if r.get("model_version")}),
        }
    res = {"set": a.set, "seed": SEED, "n_blocks": N_BLOCKS, "pool": len(pool),
           "prompt_sha256": {c: e_prompts.sha(c) for c in e_prompts.PROMPTS},
           "runner_sha256": hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
           "prices_per_token": PRICE, "spent_usd": round(spent[0], 4),
           "seconds": round(time.time() - t0, 1), "arms": summ}
    (out / "smoke-calls.ndjson").write_text("".join(json.dumps(r, sort_keys=True) + "\n"
                                                    for r in sorted(recs, key=lambda r: (r["model"], r["arm"], r["crit"], r["block"]))))
    (out / "smoke-result.json").write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps(res, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
