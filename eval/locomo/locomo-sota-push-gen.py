#!/usr/bin/env python3
"""
locomo-sota-push-gen.py — LoCoMo F1 SOTA push generation pass.

Builds on locomo-constrained-gen-pass.py with:
  1. Session-date map injection for temporal questions (Improvement A core).
  2. Optional commonsense retrieval expansion via larger context window
     (Improvement B — uses chunks already in e2e JSONL, top_k=30 if available).
  3. Prompt variations selectable via --prompt-variant {A,B,C}.

Inputs:
  --in-jsonl PATH    — existing e2e JSONL (has retrieved_texts already)
  --out-jsonl PATH   — output JSONL with new generated answers
  --locomo-json PATH — source locomo10.json (for session_date_time maps)
  --prompt-variant   — A (constrained baseline), B (date-anchor), C (entity-only)
  --no-temporal-norm — disable temporal normalizer post-processor
  --no-session-dates — disable session-date injection in prompt
  --commonsense-ctx-boost — commonsense gets full top-N retrieved
  --max-questions N  — 0=all, 100=smoke
  --smoke            — alias for --max-questions 100 stratified

Output JSONL fields (same shape as constrained pass + new):
  - generated_answer_sota: post-normalize answer
  - generated_answer_raw: raw LLM output before normalization
  - f1_sota: F1 of normalized answer vs gold
  - f1_raw: F1 of raw answer vs gold (for ablation)
  - prompt_variant: A/B/C
  - normalizer_changed: bool
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

# Allow `import lib.temporal_normalizer` when run from repo root or eval/locomo/
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from lib.temporal_normalizer import (  # noqa: E402
    build_session_date_map,
    normalize_predicted_date,
)

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
    max_tokens: int = 32,
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
# Prompt builders — variants A/B/C
# ---------------------------------------------------------------------------

def build_session_date_block(session_date_map: dict[str, str]) -> str:
    """
    Render session date map as a sorted block:
        Session dates:
        - session_1: 8 May 2023
        - session_2: 25 May 2023
        ...

    Sorted by session number (numeric, not lex).
    """
    if not session_date_map:
        return ""

    def sortkey(sid: str) -> int:
        try:
            return int(sid.split("_")[1])
        except Exception:
            return 0

    sorted_sids = sorted(session_date_map.keys(), key=sortkey)
    lines = ["Session dates (use these to anchor temporal answers):"]
    for sid in sorted_sids:
        lines.append(f"  - {sid}: {session_date_map[sid]}")
    return "\n".join(lines) + "\n\n"


def build_prompt_A(
    augmented_question: str,
    retrieved_texts: list[str],
    session_date_map: dict[str, str] | None,
    category_name: str,
    inject_dates: bool = True,
    top_n_chunks: int = 10,
) -> str:
    """
    Variant A — improved constrained prompt:
      - Inject session_date_map for temporal questions
      - Format: 'D Month YYYY' explicit
      - Short answer constraint preserved
    """
    chunks_used = retrieved_texts[:top_n_chunks]
    ctx = "\n\n".join(
        f"--- chunk {i+1} ---\n{c[:1800]}" for i, c in enumerate(chunks_used)
    )

    date_block = ""
    if inject_dates and category_name == "temporal" and session_date_map:
        date_block = build_session_date_block(session_date_map)

    return (
        "You are answering a question about a long-term conversation. "
        "Use ONLY the retrieved memory chunks below as evidence; do not invent facts.\n\n"
        f"{date_block}"
        f"Retrieved memory:\n{ctx or '[no context retrieved]'}\n\n"
        f"Question: {augmented_question}\n\n"
        "Answer in 1-5 words ONLY. Format dates as 'D Month YYYY' (e.g. '7 May 2023'). "
        "Do not include explanations, justifications, or full sentences. "
        "Just the answer. If not mentioned in the memory, answer: Not mentioned\n\n"
        "Answer:"
    )


def build_prompt_B(
    augmented_question: str,
    retrieved_texts: list[str],
    session_date_map: dict[str, str] | None,
    category_name: str,
    inject_dates: bool = True,
    top_n_chunks: int = 10,
) -> str:
    """
    Variant B — entity-or-phrase focus:
      - Emphasizes 'exact entity or short phrase'
      - Drops 'sentence' phrasing
      - Same date-anchor injection for temporal
    """
    chunks_used = retrieved_texts[:top_n_chunks]
    ctx = "\n\n".join(
        f"--- chunk {i+1} ---\n{c[:1800]}" for i, c in enumerate(chunks_used)
    )

    date_block = ""
    if inject_dates and category_name == "temporal" and session_date_map:
        date_block = build_session_date_block(session_date_map)

    return (
        "Answer the question using ONLY the retrieved memory chunks. "
        "Do not invent facts.\n\n"
        f"{date_block}"
        f"Retrieved memory:\n{ctx or '[no context retrieved]'}\n\n"
        f"Question: {augmented_question}\n\n"
        "Reply with the exact entity, phrase, or date that answers the question. "
        "Format dates as 'D Month YYYY' (e.g. '7 May 2023'). "
        "Prefer 1-3 words; max 5 words. No explanations. "
        "If not in the memory, say: Not mentioned\n\n"
        "Answer:"
    )


def build_prompt_C(
    augmented_question: str,
    retrieved_texts: list[str],
    session_date_map: dict[str, str] | None,
    category_name: str,
    inject_dates: bool = True,
    top_n_chunks: int = 10,
) -> str:
    """
    Variant C — terse 1-3 words preferred:
      - Hardline brevity
      - Same date-anchor injection for temporal
      - Explicit no-explanation
    """
    chunks_used = retrieved_texts[:top_n_chunks]
    ctx = "\n\n".join(
        f"--- chunk {i+1} ---\n{c[:1800]}" for i, c in enumerate(chunks_used)
    )

    date_block = ""
    if inject_dates and category_name == "temporal" and session_date_map:
        date_block = build_session_date_block(session_date_map)

    return (
        "Use ONLY the retrieved memory chunks below as evidence.\n\n"
        f"{date_block}"
        f"Retrieved memory:\n{ctx or '[no context retrieved]'}\n\n"
        f"Question: {augmented_question}\n\n"
        "Answer in 1-3 words preferred, max 5 words. "
        "Dates: 'D Month YYYY'. No explanations. "
        "If unknown, answer: Not mentioned\n\n"
        "Answer:"
    )


PROMPT_BUILDERS = {
    "A": build_prompt_A,
    "B": build_prompt_B,
    "C": build_prompt_C,
}


# ---------------------------------------------------------------------------
# Scorer
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
# Session date map per conversation
# ---------------------------------------------------------------------------

def load_session_date_maps(locomo_json: str) -> dict[str, dict[str, str]]:
    """
    Return {sample_id: {session_id: canonical_date_str}}.
    """
    out: dict[str, dict[str, str]] = {}
    with open(locomo_json, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        return out
    for item in data:
        if not isinstance(item, dict):
            continue
        sid = str(item.get("sample_id", "?"))
        conv = item.get("conversation") or {}
        out[sid] = build_session_date_map(conv)
    return out


# ---------------------------------------------------------------------------
# Stratified sample
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
    p.add_argument("--in-jsonl", required=True)
    p.add_argument("--out-jsonl", required=True)
    p.add_argument("--locomo-json", required=True,
                   help="path to locomo10.json (for session_date_time maps)")
    p.add_argument("--model", default="gpt-4.1-mini")
    p.add_argument("--prompt-variant", default="A", choices=["A", "B", "C"])
    p.add_argument("--no-temporal-norm", action="store_true",
                   help="disable temporal normalizer post-processor")
    p.add_argument("--no-session-dates", action="store_true",
                   help="disable session-date injection in prompt")
    p.add_argument("--commonsense-top-n", type=int, default=10,
                   help="top-N chunks for commonsense (default 10, try 15-20)")
    p.add_argument("--default-top-n", type=int, default=10,
                   help="top-N chunks for non-commonsense (default 10)")
    p.add_argument("--max-questions", type=int, default=0)
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

    if not args.no_preflight:
        err = preflight(openai_key, args.model)
        if err:
            print(f"[FATAL] {err}", file=sys.stderr)
            return 2

    # Session date maps
    print(f"[sota] loading session date maps from {args.locomo_json}", file=sys.stderr)
    session_date_maps = load_session_date_maps(args.locomo_json)
    print(f"[sota] loaded maps for {len(session_date_maps)} conversations", file=sys.stderr)
    for sid, smap in list(session_date_maps.items())[:2]:
        print(f"  {sid}: {len(smap)} sessions, e.g. {list(smap.items())[:2]}", file=sys.stderr)

    # Load input
    records = []
    with open(args.in_jsonl, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    print(f"[sota] loaded {len(records)} records from {args.in_jsonl}", file=sys.stderr)

    # Sample
    if args.max_questions > 0:
        records = stratified_sample(records, args.max_questions, args.seed)
        print(f"[sota] sampled {len(records)} (stratified, max_q={args.max_questions})",
              file=sys.stderr)

    # Resume
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
        print(f"[sota] resume: {len(done_keys)} already done", file=sys.stderr)
    open_mode = "a" if args.resume and out_path.exists() else "w"

    prompt_builder = PROMPT_BUILDERS[args.prompt_variant]
    print(f"[sota] using prompt variant {args.prompt_variant}", file=sys.stderr)
    print(f"[sota] temporal_norm={'OFF' if args.no_temporal_norm else 'ON'} "
          f"session_dates={'OFF' if args.no_session_dates else 'ON'}",
          file=sys.stderr)

    t_start = time.time()
    n_done = 0
    n_err = 0
    n_normalized = 0
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
            cat_name = rec.get("category_name", "unknown")
            sample_id = rec.get("sample_id", "?")

            session_map = session_date_maps.get(sample_id, {})

            # Choose top_n per category
            top_n = (
                args.commonsense_top_n if cat_name == "commonsense"
                else args.default_top_n
            )

            prompt = prompt_builder(
                augmented_q, retrieved_texts, session_map, cat_name,
                inject_dates=(not args.no_session_dates),
                top_n_chunks=top_n,
            )

            gen_txt, gms, in_t, out_t, gerr = call_openai(
                prompt, args.model, openai_key, max_tokens=32
            )
            total_in += in_t
            total_out += out_t

            # Apply temporal normalizer for temporal category
            raw_answer = gen_txt
            normalized_answer = gen_txt
            normalizer_changed = False
            if cat_name == "temporal" and not args.no_temporal_norm and gen_txt:
                normalized_answer = normalize_predicted_date(gen_txt, session_map)
                if normalized_answer != gen_txt:
                    normalizer_changed = True
                    n_normalized += 1

            f1_sota = token_f1(normalized_answer, gold) if gerr is None else 0.0
            f1_raw = token_f1(raw_answer, gold) if gerr is None else 0.0

            out_rec = {
                "sample_id": sample_id,
                "qa_index": rec["qa_index"],
                "category": rec["category"],
                "category_name": cat_name,
                "question": rec["question"],
                "augmented_question": augmented_q,
                "answer": gold,
                "generated_answer_raw": raw_answer,
                "generated_answer_sota": normalized_answer,
                "f1_sota": f1_sota,
                "f1_raw": f1_raw,
                "prompt_variant": args.prompt_variant,
                "normalizer_changed": normalizer_changed,
                "top_n_chunks_used": top_n,
                "generation_ms": gms,
                "input_tokens": in_t,
                "output_tokens": out_t,
                "error": gerr,
                "evidence": rec.get("evidence") or [],
                "retrieved_dia_ids": rec.get("retrieved_dia_ids") or [],
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
                    f"[sota] {n_done}/{len(records)} done errs={n_err} "
                    f"norm={n_normalized} elapsed={elapsed:.0f}s rate={rate:.1f}q/s "
                    f"eta={eta:.0f}s in_tok={total_in} out_tok={total_out}",
                    file=sys.stderr, flush=True
                )
                if n_done <= 5:
                    print(
                        f"  [{cat_name}] gold={repr(gold[:40])} "
                        f"raw={repr(raw_answer[:50])} norm={repr(normalized_answer[:50])} "
                        f"f1={f1_sota:.2f}",
                        file=sys.stderr
                    )

    elapsed = time.time() - t_start
    cost = total_in * 0.15 / 1_000_000 + total_out * 0.60 / 1_000_000
    print(
        f"[sota] DONE n={n_done} errs={n_err} normalized={n_normalized} "
        f"elapsed={elapsed:.0f}s in_tok={total_in} out_tok={total_out} cost=${cost:.4f}",
        file=sys.stderr
    )

    # Aggregate
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

    by_cat_sota: dict[str, list[float]] = {}
    by_cat_raw: dict[str, list[float]] = {}
    all_sota = []
    all_raw = []
    n_normalizer_changed = 0
    n_normalizer_helped = 0
    n_normalizer_hurt = 0

    for r in records:
        if r.get("error"):
            continue
        f1s = float(r.get("f1_sota") or 0.0)
        f1r = float(r.get("f1_raw") or 0.0)
        cat = r.get("category_name", "unknown")
        by_cat_sota.setdefault(cat, []).append(f1s)
        by_cat_raw.setdefault(cat, []).append(f1r)
        all_sota.append(f1s)
        all_raw.append(f1r)
        if r.get("normalizer_changed"):
            n_normalizer_changed += 1
            if f1s > f1r:
                n_normalizer_helped += 1
            elif f1s < f1r:
                n_normalizer_hurt += 1

    overall_f1_sota = sum(all_sota) / len(all_sota) if all_sota else 0.0
    overall_f1_raw = sum(all_raw) / len(all_raw) if all_raw else 0.0
    accuracy = sum(1 for f in all_sota if f >= 0.5) / len(all_sota) if all_sota else 0.0
    comp_eff = overall_f1_sota / RETRIEVAL_CEILING if RETRIEVAL_CEILING > 0 else 0.0
    delta_vs_mem0 = (overall_f1_sota - MEM0_SOTA_F1) * 100
    delta_vs_constrained = (overall_f1_sota - 0.5038) * 100  # PR #400 baseline

    print("\n" + "="*60, file=sys.stderr)
    print("SOTA PUSH RESULTS", file=sys.stderr)
    print(f"n={len(all_sota)} overall_F1_sota={overall_f1_sota*100:.2f}% "
          f"(raw={overall_f1_raw*100:.2f}%) accuracy={accuracy*100:.2f}%", file=sys.stderr)
    print(f"composition_efficiency={comp_eff*100:.1f}% "
          f"(F1 / retrieval_ceiling {RETRIEVAL_CEILING*100:.2f}%)", file=sys.stderr)
    print(f"vs Mem0 SOTA 66.88%: {delta_vs_mem0:+.2f}pp", file=sys.stderr)
    print(f"vs constrained PR#400 50.38%: {delta_vs_constrained:+.2f}pp", file=sys.stderr)
    print(f"normalizer: changed={n_normalizer_changed} "
          f"helped={n_normalizer_helped} hurt={n_normalizer_hurt}", file=sys.stderr)
    print(f"cost=${cost:.4f} USD elapsed={elapsed:.0f}s", file=sys.stderr)
    print("", file=sys.stderr)
    print("Per-category (sota vs raw):", file=sys.stderr)
    for cat in sorted(by_cat_sota.keys()):
        v_s = by_cat_sota[cat]
        v_r = by_cat_raw.get(cat, [])
        c_s = sum(v_s) / len(v_s) if v_s else 0.0
        c_r = sum(v_r) / len(v_r) if v_r else 0.0
        delta = (c_s - c_r) * 100
        print(f"  {cat}: n={len(v_s)} sota={c_s*100:.2f}% raw={c_r*100:.2f}% "
              f"Δnorm={delta:+.2f}pp", file=sys.stderr)
    print("", file=sys.stderr)

    summary = {
        "schema": "locomo-sota-push/v1",
        "run": "sota_push_generation",
        "generator": args.model,
        "prompt_variant": args.prompt_variant,
        "temporal_norm_enabled": not args.no_temporal_norm,
        "session_dates_injected": not args.no_session_dates,
        "commonsense_top_n": args.commonsense_top_n,
        "default_top_n": args.default_top_n,
        "date": time.strftime("%Y-%m-%d"),
        "n_total": len(records),
        "n_scored": len(all_sota),
        "n_errors": n_err,
        "mean_f1_sota": overall_f1_sota,
        "mean_f1_raw": overall_f1_raw,
        "accuracy_sota": accuracy,
        "composition_efficiency_sota": round(comp_eff, 4),
        "retrieval_ceiling": RETRIEVAL_CEILING,
        "mem0_sota_f1": MEM0_SOTA_F1,
        "delta_vs_mem0_sota_pp": round(delta_vs_mem0, 2),
        "delta_vs_constrained_pp": round(delta_vs_constrained, 2),
        "constrained_baseline_f1": 0.5038,
        "normalizer_stats": {
            "n_changed": n_normalizer_changed,
            "n_helped": n_normalizer_helped,
            "n_hurt": n_normalizer_hurt,
        },
        "per_category": {
            cat: {
                "n": len(by_cat_sota[cat]),
                "mean_f1_sota": round(sum(by_cat_sota[cat]) / len(by_cat_sota[cat]), 6) if by_cat_sota[cat] else 0.0,
                "mean_f1_raw": round(sum(by_cat_raw.get(cat, [])) / len(by_cat_raw.get(cat, []) or [1]), 6) if by_cat_raw.get(cat) else 0.0,
                "accuracy_sota": round(sum(1 for f in by_cat_sota[cat] if f >= 0.5) / len(by_cat_sota[cat]), 6) if by_cat_sota[cat] else 0.0,
            }
            for cat in sorted(by_cat_sota.keys())
        },
        "elapsed_s": round(elapsed, 0),
        "cost_actual_usd": round(cost, 4),
        "input_tokens": total_in,
        "output_tokens": total_out,
    }
    json_out = out_path.with_suffix(".json")
    with open(json_out, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    print(f"[sota] summary JSON -> {json_out}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
