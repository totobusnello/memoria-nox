#!/usr/bin/env python3
"""
locomo-temporal-aware-gen.py — LoCoMo temporal-aware re-rank + generation pass.

Builds on locomo-sota-push-gen.py (PR #404) by inserting a temporal-aware
re-rank step BEFORE prompt construction:

  1. Load PR #404 baseline JSONL (already has retrieved_texts, retrieved_chunk_ids).
  2. Re-rank chunks per record using lib/temporal_aware_retrieve.rerank_existing_records.
     - Temporal queries (cat=2): blend (1-alpha)*norm_retrieval + alpha*temporal_proximity.
     - Non-temporal queries: passthrough (original order).
  3. Re-prompt gpt-4.1-mini with the new top-K chunks (variant A — same as PR #404).
  4. Re-score against gold.

This is the offline companion to adapter_nox_mem.py --temporal-aware (live
HTTP path). Both produce identical scoring; the offline path is cheaper
when an existing baseline JSONL is available (avoids re-ingest+vectorize).

Inputs:
  --in-jsonl PATH        existing PR #404 SOTA push or e2e baseline JSONL
  --out-jsonl PATH       output JSONL with re-ranked + re-generated answers
  --locomo-json PATH     source locomo10.json (for session_date_time maps)
  --alpha FLOAT          blend weight (default 0.5)
  --keep-top-k INT       chunks after re-rank (default 10, matches PR #404 ctx)
  --model TEXT           generator (default gpt-4.1-mini)
  --max-questions INT    0=all (1986), 100=smoke
  --seed INT             stratified sample seed (default 42)
  --no-temporal-norm     disable normalize_predicted_date post-processor
  --no-session-dates     disable session date block in prompt
  --resume               skip already-written records

Output JSONL extends PR #404 shape with:
  - temporal_aware: bool
  - temporal_alpha: float
  - temporal_chunks_with_date: int
  - temporal_chunks_total: int
  - reranked_order_changed: bool
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

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "lib"))

from lib.temporal_normalizer import (  # noqa: E402
    build_session_date_map,
    normalize_predicted_date,
)
from lib.temporal_aware_retrieve import (  # noqa: E402
    rerank_existing_records,
)

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
ENV_FILE = "/root/.openclaw/.env"
DEFAULT_GENERATION_TIMEOUT = 40
MEM0_SOTA_F1 = 0.6688
RETRIEVAL_CEILING = 0.7452
PR_404_BASELINE_F1 = 0.5185
PR_404_TEMPORAL_F1 = 0.4421


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


def build_session_date_block(session_date_map: dict[str, str]) -> str:
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


def build_prompt_variant_A(
    augmented_question: str,
    retrieved_texts: list[str],
    session_date_map: dict[str, str] | None,
    category_name: str,
    inject_dates: bool = True,
    top_n_chunks: int = 10,
) -> str:
    """Variant A — same as PR #404 SOTA push (paired with temporal-aware retrieval)."""
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


def load_session_date_maps(locomo_json: str) -> dict[str, dict[str, str]]:
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


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--in-jsonl", required=True)
    p.add_argument("--out-jsonl", required=True)
    p.add_argument("--locomo-json", required=True)
    p.add_argument("--model", default="gpt-4.1-mini")
    p.add_argument("--alpha", type=float, default=0.5,
                   help="temporal blend weight in [0,1] (default 0.5)")
    p.add_argument("--keep-top-k", type=int, default=10,
                   help="chunks fed into prompt after re-rank (default 10)")
    p.add_argument("--no-temporal-norm", action="store_true")
    p.add_argument("--no-session-dates", action="store_true")
    p.add_argument("--max-questions", type=int, default=0)
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--no-preflight", action="store_true")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--force-on", action="store_true",
                   help="force temporal-aware re-rank on ALL queries (debug)")
    p.add_argument("--no-has-date-fallback", action="store_true",
                   help="disable has-date fallback for queries without "
                        "extractable dates (default: enabled, gives anchored "
                        "chunks 0.6 score when query has no date)")
    p.add_argument("--rerank-only", action="store_true",
                   help="re-rank + score WITHOUT regenerating (re-uses old "
                        "generated_answer_sota / generated_answer). Useful for "
                        "quick ablations.")
    args = p.parse_args()

    if args.smoke and args.max_questions == 0:
        args.max_questions = 100

    # Env
    env_base = dict(os.environ)
    env_file = env_from_file(ENV_FILE)
    for k, v in env_file.items():
        env_base.setdefault(k, v)
    openai_key = env_base.get("OPENAI_API_KEY", "")
    if not openai_key and not args.rerank_only:
        print("[FATAL] OPENAI_API_KEY not set", file=sys.stderr)
        return 2

    if not args.no_preflight and not args.rerank_only:
        err = preflight(openai_key, args.model)
        if err:
            print(f"[FATAL] {err}", file=sys.stderr)
            return 2

    print(f"[temporal-aware] loading session date maps from {args.locomo_json}",
          file=sys.stderr)
    session_date_maps = load_session_date_maps(args.locomo_json)
    print(f"[temporal-aware] loaded maps for {len(session_date_maps)} conversations",
          file=sys.stderr)

    # Load baseline JSONL
    records = []
    with open(args.in_jsonl, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    print(f"[temporal-aware] loaded {len(records)} records from {args.in_jsonl}",
          file=sys.stderr)

    # Sample
    if args.max_questions > 0:
        records = stratified_sample(records, args.max_questions, args.seed)
        print(f"[temporal-aware] sampled {len(records)} (stratified)",
              file=sys.stderr)

    # Apply re-rank (mutates records in place)
    print(f"[temporal-aware] re-ranking with alpha={args.alpha} "
          f"keep_top_k={args.keep_top_k}", file=sys.stderr)
    rerank_stats = rerank_existing_records(
        records,
        session_date_maps,
        alpha=args.alpha,
        keep_top_k=args.keep_top_k,
        force_on=args.force_on if args.force_on else None,
        has_date_fallback=not args.no_has_date_fallback,
    )

    # Resume support
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
        print(f"[temporal-aware] resume: {len(done_keys)} already done",
              file=sys.stderr)
    open_mode = "a" if args.resume and out_path.exists() else "w"

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

            raw_answer = ""
            normalized_answer = ""
            gms = 0.0
            in_t = 0
            out_t = 0
            gerr: str | None = None

            if args.rerank_only:
                # Reuse old answer (SOTA push or e2e). Prefer
                # generated_answer_sota then generated_answer.
                raw_answer = (
                    rec.get("generated_answer_sota")
                    or rec.get("generated_answer")
                    or rec.get("generated_answer_raw")
                    or ""
                )
                normalized_answer = raw_answer
            else:
                prompt = build_prompt_variant_A(
                    augmented_q, retrieved_texts, session_map, cat_name,
                    inject_dates=(not args.no_session_dates),
                    top_n_chunks=args.keep_top_k,
                )
                gen_txt, gms, in_t, out_t, gerr = call_openai(
                    prompt, args.model, openai_key, max_tokens=32
                )
                total_in += in_t
                total_out += out_t
                raw_answer = gen_txt
                normalized_answer = gen_txt

            normalizer_changed = False
            if (
                cat_name == "temporal"
                and not args.no_temporal_norm
                and normalized_answer
            ):
                norm = normalize_predicted_date(normalized_answer, session_map)
                if norm != normalized_answer:
                    normalizer_changed = True
                    n_normalized += 1
                normalized_answer = norm

            if gerr is None or args.rerank_only:
                f1_final = token_f1(normalized_answer, gold)
                f1_raw = token_f1(raw_answer, gold)
            else:
                f1_final = 0.0
                f1_raw = 0.0

            out_rec = {
                "sample_id": sample_id,
                "qa_index": rec["qa_index"],
                "category": rec["category"],
                "category_name": cat_name,
                "question": rec["question"],
                "augmented_question": augmented_q,
                "answer": gold,
                "generated_answer_raw": raw_answer,
                "generated_answer_temporal": normalized_answer,
                "f1_temporal": f1_final,
                "f1_raw": f1_raw,
                "temporal_aware": rec.get("temporal_aware", False),
                "temporal_alpha": rec.get("temporal_alpha", args.alpha),
                "temporal_chunks_with_date": rec.get("temporal_chunks_with_date", 0),
                "temporal_chunks_total": rec.get("temporal_chunks_total", 0),
                "temporal_proximity_scores": rec.get("temporal_proximity_scores", []),
                "normalizer_changed": normalizer_changed,
                "top_n_chunks_used": args.keep_top_k,
                "generation_ms": gms,
                "input_tokens": in_t,
                "output_tokens": out_t,
                "error": gerr,
                "evidence": rec.get("evidence") or [],
                "retrieved_dia_ids": rec.get("retrieved_dia_ids") or [],
                "retrieved_chunk_ids": rec.get("retrieved_chunk_ids") or [],
                "retrieved_scores": rec.get("retrieved_scores") or [],
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
                    f"[temporal-aware] {n_done}/{len(records)} done errs={n_err} "
                    f"norm={n_normalized} elapsed={elapsed:.0f}s "
                    f"rate={rate:.1f}q/s eta={eta:.0f}s "
                    f"in_tok={total_in} out_tok={total_out}",
                    file=sys.stderr, flush=True,
                )
                if n_done <= 5:
                    print(
                        f"  [{cat_name}] gold={repr(gold[:40])} "
                        f"raw={repr(raw_answer[:50])} norm={repr(normalized_answer[:50])} "
                        f"f1={f1_final:.2f}",
                        file=sys.stderr,
                    )

    elapsed = time.time() - t_start
    cost = total_in * 0.15 / 1_000_000 + total_out * 0.60 / 1_000_000
    print(
        f"[temporal-aware] DONE n={n_done} errs={n_err} normalized={n_normalized} "
        f"elapsed={elapsed:.0f}s in_tok={total_in} out_tok={total_out} "
        f"cost=${cost:.4f}",
        file=sys.stderr,
    )

    _aggregate(
        out_path, n_done, n_err, elapsed, total_in, total_out, cost, args,
        rerank_stats,
    )
    return 0


def _aggregate(
    out_path: Path, n_done: int, n_err: int, elapsed: float,
    total_in: int, total_out: int, cost: float, args, rerank_stats: dict,
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
    by_cat_raw: dict[str, list[float]] = {}
    all_f = []
    all_raw = []
    n_norm_changed = 0
    n_norm_helped = 0
    n_norm_hurt = 0
    n_temporal_active = 0
    n_temporal_reranked_order_change = 0

    for r in records:
        if r.get("error") and not args.rerank_only:
            continue
        f1 = float(r.get("f1_temporal") or 0.0)
        f1_raw = float(r.get("f1_raw") or 0.0)
        cat = r.get("category_name", "unknown")
        by_cat.setdefault(cat, []).append(f1)
        by_cat_raw.setdefault(cat, []).append(f1_raw)
        all_f.append(f1)
        all_raw.append(f1_raw)
        if r.get("normalizer_changed"):
            n_norm_changed += 1
            if f1 > f1_raw:
                n_norm_helped += 1
            elif f1 < f1_raw:
                n_norm_hurt += 1
        if r.get("temporal_aware"):
            n_temporal_active += 1

    overall_f1 = sum(all_f) / len(all_f) if all_f else 0.0
    overall_raw = sum(all_raw) / len(all_raw) if all_raw else 0.0
    accuracy = sum(1 for f in all_f if f >= 0.5) / len(all_f) if all_f else 0.0
    comp_eff = overall_f1 / RETRIEVAL_CEILING if RETRIEVAL_CEILING > 0 else 0.0
    delta_vs_mem0 = (overall_f1 - MEM0_SOTA_F1) * 100
    delta_vs_pr404 = (overall_f1 - PR_404_BASELINE_F1) * 100

    print("\n" + "=" * 60, file=sys.stderr)
    print("TEMPORAL-AWARE RESULTS", file=sys.stderr)
    print(f"n={len(all_f)} overall_F1={overall_f1*100:.2f}% "
          f"(raw={overall_raw*100:.2f}%) accuracy={accuracy*100:.2f}%",
          file=sys.stderr)
    print(f"composition_efficiency={comp_eff*100:.1f}% "
          f"(F1 / retrieval_ceiling {RETRIEVAL_CEILING*100:.2f}%)",
          file=sys.stderr)
    print(f"vs Mem0 SOTA 66.88%: {delta_vs_mem0:+.2f}pp", file=sys.stderr)
    print(f"vs PR #404 SOTA push 51.85%: {delta_vs_pr404:+.2f}pp", file=sys.stderr)
    print(f"normalizer: changed={n_norm_changed} "
          f"helped={n_norm_helped} hurt={n_norm_hurt}", file=sys.stderr)
    print(f"temporal-aware active records: {n_temporal_active}/{len(records)}",
          file=sys.stderr)
    print(f"cost=${cost:.4f} elapsed={elapsed:.0f}s", file=sys.stderr)

    print("\nPer-category:", file=sys.stderr)
    pr_404_per_cat = {
        "single_hop": 0.5518,
        "multi_hop": 0.3816,
        "temporal": 0.4421,
        "commonsense": 0.2377,
        "adversarial": 0.6578,
    }
    for cat in sorted(by_cat.keys()):
        v = by_cat[cat]
        v_r = by_cat_raw.get(cat, [])
        c = sum(v) / len(v) if v else 0.0
        c_r = sum(v_r) / len(v_r) if v_r else 0.0
        baseline = pr_404_per_cat.get(cat, 0.0)
        delta_vs_baseline = (c - baseline) * 100 if baseline > 0 else 0.0
        print(f"  {cat}: n={len(v)} f1={c*100:.2f}% raw={c_r*100:.2f}% "
              f"Δvs_PR404={delta_vs_baseline:+.2f}pp", file=sys.stderr)

    summary = {
        "schema": "locomo-temporal-aware/v1",
        "run": "temporal_aware_gen",
        "generator": args.model,
        "alpha": args.alpha,
        "keep_top_k": args.keep_top_k,
        "rerank_only": args.rerank_only,
        "session_dates_injected": not args.no_session_dates,
        "temporal_norm_enabled": not args.no_temporal_norm,
        "n_total": len(records),
        "n_done": n_done,
        "n_errors": n_err,
        "n_normalized": n_norm_changed,
        "n_norm_helped": n_norm_helped,
        "n_norm_hurt": n_norm_hurt,
        "n_temporal_active": n_temporal_active,
        "overall_f1_temporal": overall_f1,
        "overall_f1_raw": overall_raw,
        "accuracy_at_50": accuracy,
        "composition_efficiency": comp_eff,
        "delta_vs_mem0_sota_pp": delta_vs_mem0,
        "delta_vs_pr404_pp": delta_vs_pr404,
        "per_category_f1": {
            cat: sum(v) / len(v) for cat, v in by_cat.items() if v
        },
        "per_category_n": {cat: len(v) for cat, v in by_cat.items()},
        "per_category_delta_vs_pr404_pp": {
            cat: (sum(v) / len(v) - pr_404_per_cat.get(cat, 0.0)) * 100
            for cat, v in by_cat.items() if v
        },
        "rerank_stats": rerank_stats,
        "cost_usd": cost,
        "elapsed_s": elapsed,
        "in_tokens": total_in,
        "out_tokens": total_out,
        "in_jsonl": args.__dict__.get("in_jsonl"),
        "out_jsonl": str(out_path),
    }

    agg_path = out_path.with_suffix(".agg.json")
    with agg_path.open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    print(f"[temporal-aware] aggregate written: {agg_path}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
