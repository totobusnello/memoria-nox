#!/usr/bin/env python3
"""
locomo-constrained-gen-pass.py

Generation-pass-only script for LoCoMo constrained-generation experiment.

Reads existing e2e JSONL (which has retrieved_texts already),
re-runs ONLY the generation step with a constrained prompt,
writes new JSONL with constrained generated answers.

This avoids re-running the full ingest+vectorize+retrieve pipeline (~30 min).
Cost estimate: ~$0.15-0.25 for 1986q at gpt-4.1-mini pricing.

Usage:
  python3 locomo-constrained-gen-pass.py \\
      --in-jsonl /root/.openclaw/locomo-e2e-rerun-af562a4b/results-e2e-1986q.jsonl \\
      --out-jsonl /root/.openclaw/locomo-constrained-<uuid>/results-constrained-1986q.jsonl \\
      --max-questions 100   # smoke: omit for full 1986q
      --smoke               # 100 stratified for quick gate check
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
ENV_FILE = "/root/.openclaw/.env"
DEFAULT_GENERATION_TIMEOUT = 40
MEM0_SOTA_F1 = 0.6688
RETRIEVAL_CEILING = 0.7452


# ---------------------------------------------------------------------------
# Env loading
# ---------------------------------------------------------------------------

def env_from_file(path: str) -> dict[str, str]:
    env: dict[str, str] = {}
    if not os.path.exists(path):
        return env
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


# ---------------------------------------------------------------------------
# OpenAI generation
# ---------------------------------------------------------------------------

def call_openai(
    prompt: str,
    model: str,
    openai_key: str,
    timeout: int = DEFAULT_GENERATION_TIMEOUT,
    max_tokens: int = 32,  # short: constrained answers should be <10 tokens
) -> tuple[str, float, int, int, str | None]:
    body = json.dumps({
        "model": model,
        "temperature": 0,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(
        OPENAI_URL,
        data=body,
        headers={
            "content-type": "application/json",
            "authorization": f"Bearer {openai_key}",
        },
        method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            j = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_str = ""
        try:
            body_str = e.read().decode("utf-8")[:400]
        except Exception:
            pass
        return "", (time.time() - t0) * 1000.0, 0, 0, f"HTTPError {e.code}: {body_str}"
    except Exception as e:
        return "", (time.time() - t0) * 1000.0, 0, 0, f"{type(e).__name__}: {e}"
    ms = (time.time() - t0) * 1000.0
    txt = (j.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""
    usage = j.get("usage") or {}
    return (
        txt.strip(),
        ms,
        int(usage.get("prompt_tokens") or 0),
        int(usage.get("completion_tokens") or 0),
        None,
    )


# ---------------------------------------------------------------------------
# Constrained prompt builder
# ---------------------------------------------------------------------------

def build_constrained_prompt(
    augmented_question: str, retrieved_texts: list[str]
) -> str:
    ctx = "\n\n".join(
        f"--- chunk {i+1} ---\n{c[:1800]}" for i, c in enumerate(retrieved_texts[:10])
    )
    return (
        "You are answering a question about a long-term conversation. "
        "Use ONLY the retrieved memory chunks below as evidence; do not invent facts.\n\n"
        f"Retrieved memory:\n{ctx or '[no context retrieved]'}\n\n"
        f"Question: {augmented_question}\n\n"
        "Answer in 1-5 words ONLY. Do not include explanations, justifications, or full sentences. "
        "Just the answer. If not mentioned in the memory, answer: Not mentioned\n\n"
        "Answer:"
    )


# ---------------------------------------------------------------------------
# Scorer (token-overlap F1, same as LoCoMo paper)
# ---------------------------------------------------------------------------

def normalize_answer(s: str) -> str:
    import re
    import string
    s = s.lower()
    s = re.sub(r"\b(a|an|the)\b", " ", s)
    s = "".join(ch if ch not in string.punctuation else " " for ch in s)
    return " ".join(s.split())


def token_f1(pred: str, gold: str) -> float:
    if not gold:
        # adversarial: if model abstains (no content match to gold ""), award 1.0
        abstain_phrases = [
            "not mentioned", "not in the memory", "no information",
            "not found", "not provided", "not available", "not stated",
            "not specified", "unknown",
        ]
        pred_lower = pred.lower()
        if any(p in pred_lower for p in abstain_phrases) or not pred.strip():
            return 1.0
        return 0.0
    pred_norm = normalize_answer(pred)
    gold_norm = normalize_answer(gold)
    pred_tokens = pred_norm.split()
    gold_tokens = gold_norm.split()
    if not pred_tokens or not gold_tokens:
        return 0.0
    common = set(pred_tokens) & set(gold_tokens)
    if not common:
        return 0.0
    precision = len(common) / len(pred_tokens)
    recall = len(common) / len(gold_tokens)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------

def preflight(openai_key: str, model: str) -> str | None:
    txt, ms, in_t, out_t, err = call_openai(
        "Say 'ok' (2 letters)", model, openai_key, timeout=15, max_tokens=5
    )
    if err:
        return f"openai preflight failed: {err}"
    if not txt:
        return f"openai preflight returned empty text (in={in_t} out={out_t})"
    print(f"[preflight] OK: '{txt}' in={in_t} out={out_t} ms={ms:.0f}", file=sys.stderr)
    return None


# ---------------------------------------------------------------------------
# Stratified sample (same as adapter_nox_mem.py)
# ---------------------------------------------------------------------------

def stratified_sample(records: list[dict], max_n: int, seed: int = 42) -> list[dict]:
    by_cat: dict[str, list[dict]] = {}
    for r in records:
        cat = r.get("category_name", "unknown")
        by_cat.setdefault(cat, []).append(r)
    rng = random.Random(seed)
    cats = sorted(by_cat.keys())
    per_cat = max(1, max_n // max(1, len(cats)))
    selected: list[dict] = []
    for c in cats:
        pool = list(by_cat[c])
        rng.shuffle(pool)
        selected.extend(pool[:per_cat])
    rng.shuffle(selected)
    if len(selected) > max_n:
        selected = selected[:max_n]
    return selected


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--in-jsonl", required=True,
                   help="existing e2e results JSONL with retrieved_texts")
    p.add_argument("--out-jsonl", required=True,
                   help="output JSONL with constrained generated answers")
    p.add_argument("--model", default="gpt-4.1-mini")
    p.add_argument("--max-questions", type=int, default=0,
                   help="0 = all; 100 for smoke")
    p.add_argument("--smoke", action="store_true",
                   help="shorthand for --max-questions 100 stratified")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--no-preflight", action="store_true")
    p.add_argument("--resume", action="store_true")
    args = p.parse_args()

    if args.smoke and args.max_questions == 0:
        args.max_questions = 100

    # Env
    env_base = dict(os.environ)
    env_file = env_from_file(ENV_FILE)
    for k, v in env_file.items():
        env_base.setdefault(k, v)
    openai_key = env_base.get("OPENAI_API_KEY", "")
    if not openai_key:
        print("[FATAL] OPENAI_API_KEY not set", file=sys.stderr)
        return 2

    # Preflight
    if not args.no_preflight:
        err = preflight(openai_key, args.model)
        if err:
            print(f"[FATAL] {err}", file=sys.stderr)
            return 2

    # Load input JSONL
    records = []
    with open(args.in_jsonl, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    print(f"[pass] loaded {len(records)} records from {args.in_jsonl}", file=sys.stderr)

    # Sample
    if args.max_questions > 0:
        records = stratified_sample(records, args.max_questions, args.seed)
        print(f"[pass] sampled {len(records)} (stratified, max_q={args.max_questions})",
              file=sys.stderr)

    # Resume: skip already-done (sample_id, qa_index)
    out_path = Path(args.out_jsonl)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done_keys: set[tuple[str, int]] = set()
    if args.resume and out_path.exists():
        with out_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    j = json.loads(line)
                    done_keys.add((j["sample_id"], int(j["qa_index"])))
                except Exception:
                    pass
        print(f"[pass] resume: {len(done_keys)} already done", file=sys.stderr)

    open_mode = "a" if args.resume and out_path.exists() else "w"

    t_start = time.time()
    n_done = 0
    n_err = 0
    total_in = 0
    total_out = 0

    with out_path.open(open_mode, encoding="utf-8") as fh:
        for i, rec in enumerate(records):
            key = (rec["sample_id"], int(rec["qa_index"]))
            if key in done_keys:
                continue

            retrieved_texts = rec.get("retrieved_texts") or []
            augmented_q = rec.get("augmented_question") or rec.get("question") or ""
            gold = rec.get("answer") or ""

            prompt = build_constrained_prompt(augmented_q, retrieved_texts)

            gen_txt, gms, in_t, out_t, gerr = call_openai(
                prompt, args.model, openai_key, max_tokens=32
            )
            total_in += in_t
            total_out += out_t

            f1 = token_f1(gen_txt, gold) if gerr is None else 0.0

            out_rec = {
                "sample_id": rec["sample_id"],
                "qa_index": rec["qa_index"],
                "category": rec["category"],
                "category_name": rec["category_name"],
                "question": rec["question"],
                "augmented_question": augmented_q,
                "answer": gold,
                "generated_answer_constrained": gen_txt,
                "f1_constrained": f1,
                "generated_answer_naive": rec.get("generated_answer") or "",
                "generation_ms": gms,
                "input_tokens": in_t,
                "output_tokens": out_t,
                "error": gerr,
                # Carry over retrieval fields for scoring comparison
                "evidence": rec.get("evidence") or [],
                "retrieved_dia_ids": rec.get("retrieved_dia_ids") or [],
                "retrieved_texts": retrieved_texts,
            }
            fh.write(json.dumps(out_rec) + "\n")
            fh.flush()
            n_done += 1
            if gerr:
                n_err += 1

            if n_done % 50 == 0 or n_done <= 5:
                elapsed = time.time() - t_start
                rate = n_done / elapsed if elapsed > 0 else 0
                eta = (len(records) - n_done) / rate if rate > 0 else 0
                print(
                    f"[pass] {n_done}/{len(records)} done errs={n_err} "
                    f"elapsed={elapsed:.0f}s rate={rate:.1f}q/s eta={eta:.0f}s "
                    f"in_tok={total_in} out_tok={total_out}",
                    file=sys.stderr, flush=True
                )
                if n_done <= 5:
                    cat_str = rec['category_name']
                    print(
                        f"  [{cat_str}] gold={repr(gold[:40])} -> constrained={repr(gen_txt[:50])} f1={f1:.2f}",
                        file=sys.stderr
                    )

    elapsed = time.time() - t_start
    print(
        f"[pass] DONE n={n_done} errs={n_err} elapsed={elapsed:.0f}s "
        f"in_tokens={total_in} out_tokens={total_out}",
        file=sys.stderr
    )
    # Cost estimate at gpt-4.1-mini pricing ($0.15/1M in + $0.60/1M out)
    cost = total_in * 0.15 / 1_000_000 + total_out * 0.60 / 1_000_000
    print(f"[pass] cost_estimate=${cost:.4f} USD", file=sys.stderr)

    # Quick aggregate report
    _aggregate(out_path, n_done, n_err, elapsed, total_in, total_out, cost, args)
    return 0


def _aggregate(
    out_path: Path, n_done: int, n_err: int, elapsed: float,
    total_in: int, total_out: int, cost: float, args
) -> None:
    records = []
    with out_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    if not records:
        return

    by_cat: dict[str, list[float]] = {}
    all_f1 = []
    for r in records:
        if r.get("error"):
            continue
        f1 = float(r.get("f1_constrained") or 0.0)
        cat = r.get("category_name", "unknown")
        by_cat.setdefault(cat, []).append(f1)
        all_f1.append(f1)

    overall_f1 = sum(all_f1) / len(all_f1) if all_f1 else 0.0
    accuracy = sum(1 for f in all_f1 if f >= 0.5) / len(all_f1) if all_f1 else 0.0
    comp_eff = overall_f1 / RETRIEVAL_CEILING if RETRIEVAL_CEILING > 0 else 0.0
    delta_vs_mem0 = (overall_f1 - MEM0_SOTA_F1) * 100

    print("\n" + "="*60, file=sys.stderr)
    print(f"CONSTRAINED GENERATION RESULTS", file=sys.stderr)
    print(f"n={len(all_f1)} overall_F1={overall_f1*100:.2f}% accuracy={accuracy*100:.2f}%", file=sys.stderr)
    print(f"composition_efficiency={comp_eff*100:.1f}% (F1 / retrieval_ceiling {RETRIEVAL_CEILING*100:.2f}%)", file=sys.stderr)
    print(f"vs Mem0 SOTA 66.88%: {delta_vs_mem0:+.2f}pp", file=sys.stderr)
    print(f"cost=${cost:.4f} USD", file=sys.stderr)
    print("", file=sys.stderr)
    print("Per-category:", file=sys.stderr)
    for cat in sorted(by_cat.keys()):
        vals = by_cat[cat]
        cat_f1 = sum(vals) / len(vals) if vals else 0.0
        print(f"  {cat}: n={len(vals)} F1={cat_f1*100:.2f}%", file=sys.stderr)
    print("", file=sys.stderr)

    # Verdict
    if overall_f1 >= 0.60:
        verdict = f"SOTA_COMPETITIVE — F1={overall_f1*100:.2f}% >= 60% threshold"
    elif overall_f1 >= 0.50:
        verdict = f"COMPETITIVE — F1={overall_f1*100:.2f}% in 50-60% range"
    else:
        verdict = f"COMPOSITION_ISSUE — F1={overall_f1*100:.2f}% < 50%; verbosity not sole cause"
    print(f"VERDICT: {verdict}", file=sys.stderr)
    print("="*60, file=sys.stderr)

    # Write JSON summary alongside JSONL
    summary = {
        "schema": "locomo-constrained-gen/v1",
        "run": "end_to_end_constrained",
        "generator": args.model,
        "prompt_type": "constrained_1_5_words",
        "date": time.strftime("%Y-%m-%d"),
        "n_total": len(records),
        "n_scored": len(all_f1),
        "n_errors": n_err,
        "mean_f1": overall_f1,
        "accuracy": accuracy,
        "composition_efficiency": round(comp_eff, 4),
        "retrieval_ceiling": RETRIEVAL_CEILING,
        "mem0_sota_f1": MEM0_SOTA_F1,
        "delta_vs_mem0_sota_pp": round(delta_vs_mem0, 2),
        "hypothesis_verdict": verdict,
        "per_category": {
            cat: {
                "n": len(vals),
                "mean_f1": round(sum(vals) / len(vals), 6) if vals else 0.0,
                "accuracy": round(sum(1 for f in vals if f >= 0.5) / len(vals), 6) if vals else 0.0,
            }
            for cat, vals in by_cat.items()
        },
        "naive_baseline_f1": 0.3490,
        "delta_vs_naive_pp": round((overall_f1 - 0.3490) * 100, 2),
        "elapsed_s": round(elapsed, 0),
        "cost_actual_usd": round(cost, 4),
        "input_tokens": total_in,
        "output_tokens": total_out,
    }
    json_out = out_path.with_suffix(".json")
    with open(json_out, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    print(f"[pass] summary JSON -> {json_out}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
