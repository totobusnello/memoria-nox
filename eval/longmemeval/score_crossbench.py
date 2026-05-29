"""
score_crossbench.py — score the run_crossbench JSONL output.

Computes retrieval-only metrics over session-id matching:
    - nDCG@10
    - R@10 (Recall@10)
    - MRR (Mean Reciprocal Rank)
    - session_hit@K (did ANY answer_session_id appear in top-K retrieved?)

Per-category breakdown (6 base categories + _abs variants).

Wilson 95% CI on accuracy-style metrics (session_hit@10 only — nDCG/R/MRR
are continuous so we report mean ± SE).

If --task-accuracy flag set, also calls Gemini-2.5-flash judge for each
record with a generated_answer field (LongMemEval-paper LLM-as-judge).
Judge prompt has a separate branch for _abs (refuse-correct) vs non-abs
(answer-correct).

Output:
    - JSON aggregate to --out (or stdout)
    - Markdown summary table to --md-out (or stdout if --md)

Usage:
    python3 score_crossbench.py results.jsonl --out aggregate.json [--md-out summary.md]
    python3 score_crossbench.py results.jsonl --task-accuracy
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
import urllib.request
from collections import defaultdict
from pathlib import Path


# ---------------------------------------------------------------------------
# Metric formulas
# ---------------------------------------------------------------------------

def dcg(rels: list[int]) -> float:
    return sum(rel / math.log2(i + 2) for i, rel in enumerate(rels))


def ndcg_at_k(retrieved: list[str], gold: set[str], k: int) -> float:
    rel = [1 if r in gold else 0 for r in retrieved[:k]]
    n_gold = len(gold)
    if n_gold == 0:
        return 0.0
    ideal = [1] * min(n_gold, k) + [0] * max(0, k - min(n_gold, k))
    idcg = dcg(ideal)
    return dcg(rel) / idcg if idcg > 0 else 0.0


def recall_at_k(retrieved: list[str], gold: set[str], k: int) -> float:
    if not gold:
        return 0.0
    hits = sum(1 for r in retrieved[:k] if r in gold)
    return hits / len(gold)


def mrr(retrieved: list[str], gold: set[str]) -> float:
    for i, r in enumerate(retrieved):
        if r in gold:
            return 1.0 / (i + 1)
    return 0.0


def session_hit_at_k(retrieved: list[str], gold: set[str], k: int) -> int:
    return 1 if any(r in gold for r in retrieved[:k]) else 0


def wilson_ci(p: float, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    z2 = z * z
    denom = 1 + z2 / n
    centre = (p + z2 / (2 * n)) / denom
    half = (z * math.sqrt((p * (1 - p) + z2 / (4 * n)) / n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


# ---------------------------------------------------------------------------
# Judge (LongMemEval paper — LLM-as-judge)
# ---------------------------------------------------------------------------

GEMINI_URL_TPL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    "?key={key}"
)


def judge_prompt(question: str, gold_answer: str, generated: str, is_abs: bool) -> str:
    if is_abs:
        return (
            "You are evaluating whether an assistant correctly REFUSED to answer "
            "a question for which the long-term memory contains no answer.\n\n"
            f"Question: {question}\n"
            f"Assistant's response: {generated}\n\n"
            "Output JSON: {\"correct\": true} if the assistant clearly indicated "
            "it does not know, has no information, or cannot answer. Otherwise "
            "{\"correct\": false}. Output ONLY the JSON object."
        )
    return (
        "You are evaluating whether an assistant's answer to a question is "
        "factually correct.\n\n"
        f"Question: {question}\n"
        f"Gold answer: {gold_answer}\n"
        f"Assistant's answer: {generated}\n\n"
        "If the assistant's answer conveys the same factual information as the "
        "gold answer (paraphrases / synonyms accepted; minor extra detail OK), "
        "output {\"correct\": true}. Otherwise {\"correct\": false}. "
        "Output ONLY the JSON object."
    )


def call_gemini_judge(prompt: str, model: str, key: str, timeout: int = 30) -> tuple[bool | None, str | None]:
    url = GEMINI_URL_TPL.format(model=model, key=key)
    body = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        # Note: gemini-2.5-flash sometimes wraps {"correct": true} with markdown
        # fences or adds whitespace; need enough headroom. 32 was too tight and
        # silently truncated mid-JSON, breaking the parser.
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": 128},
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, headers={"content-type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            j = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"
    try:
        text = j["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return None, f"judge parse error: {type(e).__name__}: {e}"
    txt = text.strip()
    # Strip code fences if any
    if txt.startswith("```"):
        # find the first JSON object
        i = txt.find("{")
        if i >= 0:
            txt = txt[i:]
        if txt.endswith("```"):
            txt = txt.rsplit("```", 1)[0]
    try:
        # Try parsing as JSON; on failure, scan for first {...}
        d = json.loads(txt)
    except Exception:
        i = txt.find("{")
        j2 = txt.rfind("}")
        if i >= 0 and j2 > i:
            try:
                d = json.loads(txt[i:j2 + 1])
            except Exception:
                return None, f"judge JSON parse failed; raw={text[:200]}"
        else:
            return None, f"judge JSON parse failed; raw={text[:200]}"
    return bool(d.get("correct")), None


# ---------------------------------------------------------------------------
# Scoring driver
# ---------------------------------------------------------------------------

def load_records(path: Path) -> list[dict]:
    out: list[dict] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception as e:
                print(f"[score] skip bad line: {e}", file=sys.stderr)
    return out


def aggregate(records: list[dict], top_k: int = 10) -> dict:
    overall = defaultdict(list)
    per_cat: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    per_abs: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    n_total = 0
    n_err = 0
    n_no_gold = 0
    latencies_retrieval = []
    latencies_ingest = []
    latencies_vectorize = []
    for r in records:
        n_total += 1
        if r.get("error"):
            n_err += 1
            # Still record latency
            latencies_retrieval.append(float(r.get("retrieval_ms") or 0.0))
            continue
        gold = set(r.get("gold_session_ids") or [])
        # Dedupe retrieved_session_ids preserving order. nox-mem returns
        # chunk-level hits, but a single session_id can appear in multiple
        # chunks (one per turn). For session-level retrieval metrics we
        # collapse to first-occurrence-per-session.
        raw_retr = r.get("retrieved_session_ids") or []
        seen: set[str] = set()
        retr: list[str] = []
        for sid in raw_retr:
            if sid in seen:
                continue
            seen.add(sid)
            retr.append(sid)
        if not gold:
            n_no_gold += 1
            continue
        n = ndcg_at_k(retr, gold, top_k)
        rec = recall_at_k(retr, gold, top_k)
        mr = mrr(retr, gold)
        hit = session_hit_at_k(retr, gold, top_k)
        overall["ndcg"].append(n)
        overall["recall"].append(rec)
        overall["mrr"].append(mr)
        overall["hit"].append(hit)

        cat = r.get("base_category") or "unknown"
        per_cat[cat]["ndcg"].append(n)
        per_cat[cat]["recall"].append(rec)
        per_cat[cat]["mrr"].append(mr)
        per_cat[cat]["hit"].append(hit)
        per_cat[cat]["n"].append(1)  # type: ignore[arg-type]

        abs_key = "_abs" if r.get("is_abstention") else "non_abs"
        per_abs[abs_key]["ndcg"].append(n)
        per_abs[abs_key]["recall"].append(rec)
        per_abs[abs_key]["mrr"].append(mr)
        per_abs[abs_key]["hit"].append(hit)

        latencies_retrieval.append(float(r.get("retrieval_ms") or 0.0))
        latencies_ingest.append(float(r.get("ingest_ms") or 0.0))
        latencies_vectorize.append(float(r.get("vectorize_ms") or 0.0))

    def _mean(xs: list[float]) -> float:
        return sum(xs) / len(xs) if xs else 0.0

    def _percentile(xs: list[float], p: float) -> float:
        if not xs:
            return 0.0
        s = sorted(xs)
        k = (len(s) - 1) * (p / 100.0)
        lo = math.floor(k)
        hi = math.ceil(k)
        if lo == hi:
            return s[int(k)]
        return s[lo] + (s[hi] - s[lo]) * (k - lo)

    def _stats(xs: list[float]) -> dict:
        if not xs:
            return {"n": 0, "mean": 0.0, "se": 0.0, "ci95": [0.0, 0.0]}
        n = len(xs)
        m = sum(xs) / n
        if n > 1:
            var = sum((x - m) ** 2 for x in xs) / (n - 1)
            se = math.sqrt(var / n)
        else:
            se = 0.0
        ci_lo = max(0.0, m - 1.96 * se)
        ci_hi = min(1.0, m + 1.96 * se)
        return {"n": n, "mean": round(m, 4), "se": round(se, 4), "ci95": [round(ci_lo, 4), round(ci_hi, 4)]}

    hit_mean = _mean(overall["hit"]) if overall["hit"] else 0.0
    hit_n = len(overall["hit"])
    hit_lo, hit_hi = wilson_ci(hit_mean, hit_n)

    agg = {
        "n_total": n_total,
        "n_scored": len(overall["ndcg"]),
        "n_errors": n_err,
        "n_no_gold": n_no_gold,
        "top_k": top_k,
        "overall": {
            "ndcg_at_10": _stats(overall["ndcg"]),
            "recall_at_10": _stats(overall["recall"]),
            "mrr": _stats(overall["mrr"]),
            "session_hit_at_10": {
                "mean": round(hit_mean, 4),
                "n": hit_n,
                "wilson_95": [round(hit_lo, 4), round(hit_hi, 4)],
            },
        },
        "per_category": {
            cat: {
                "n": len(v["ndcg"]),
                "ndcg_at_10": round(_mean(v["ndcg"]), 4),
                "recall_at_10": round(_mean(v["recall"]), 4),
                "mrr": round(_mean(v["mrr"]), 4),
                "session_hit_at_10": round(_mean(v["hit"]), 4),
            }
            for cat, v in sorted(per_cat.items())
        },
        "per_abstention": {
            k: {
                "n": len(v["ndcg"]),
                "ndcg_at_10": round(_mean(v["ndcg"]), 4),
                "recall_at_10": round(_mean(v["recall"]), 4),
                "mrr": round(_mean(v["mrr"]), 4),
                "session_hit_at_10": round(_mean(v["hit"]), 4),
            }
            for k, v in sorted(per_abs.items())
        },
        "latency_ms": {
            "ingest": {
                "p50": round(_percentile(latencies_ingest, 50), 1),
                "p95": round(_percentile(latencies_ingest, 95), 1),
                "p99": round(_percentile(latencies_ingest, 99), 1),
                "mean": round(_mean(latencies_ingest), 1),
            },
            "vectorize": {
                "p50": round(_percentile(latencies_vectorize, 50), 1),
                "p95": round(_percentile(latencies_vectorize, 95), 1),
                "p99": round(_percentile(latencies_vectorize, 99), 1),
                "mean": round(_mean(latencies_vectorize), 1),
            },
            "retrieval": {
                "p50": round(_percentile(latencies_retrieval, 50), 1),
                "p95": round(_percentile(latencies_retrieval, 95), 1),
                "p99": round(_percentile(latencies_retrieval, 99), 1),
                "mean": round(_mean(latencies_retrieval), 1),
            },
        },
    }
    return agg


def score_task_accuracy(records: list[dict], judge_model: str, gemini_key: str) -> dict:
    """Returns per-category + overall task accuracy via LLM-as-judge."""
    overall = []
    per_cat: dict[str, list[int]] = defaultdict(list)
    per_abs: dict[str, list[int]] = defaultdict(list)
    n_judged = 0
    n_skip = 0
    n_err = 0
    for r in records:
        gen = r.get("generated_answer", "")
        if not gen:
            n_skip += 1
            continue
        prompt = judge_prompt(
            r["question"], r["gold_answer"], gen, bool(r.get("is_abstention")),
        )
        verdict, jerr = call_gemini_judge(prompt, judge_model, gemini_key)
        if verdict is None:
            n_err += 1
            continue
        n_judged += 1
        v = 1 if verdict else 0
        overall.append(v)
        cat = r.get("base_category") or "unknown"
        per_cat[cat].append(v)
        per_abs["_abs" if r.get("is_abstention") else "non_abs"].append(v)

    def _acc(xs: list[int]) -> dict:
        n = len(xs)
        if n == 0:
            return {"n": 0, "accuracy": 0.0, "wilson_95": [0.0, 0.0]}
        m = sum(xs) / n
        lo, hi = wilson_ci(m, n)
        return {"n": n, "accuracy": round(m, 4), "wilson_95": [round(lo, 4), round(hi, 4)]}

    return {
        "judge_model": judge_model,
        "n_judged": n_judged,
        "n_skipped": n_skip,
        "n_judge_errors": n_err,
        "overall": _acc(overall),
        "per_category": {k: _acc(v) for k, v in sorted(per_cat.items())},
        "per_abstention": {k: _acc(v) for k, v in sorted(per_abs.items())},
    }


def render_md(agg: dict, task_acc: dict | None = None) -> str:
    lines: list[str] = []
    lines.append("# LongMemEval Cross-Bench Validation — Aggregate")
    lines.append("")
    lines.append(f"- Total questions: **{agg['n_total']}**")
    lines.append(f"- Scored (with gold): **{agg['n_scored']}**")
    lines.append(f"- Errors: **{agg['n_errors']}**")
    lines.append(f"- No-gold skipped: **{agg['n_no_gold']}**")
    lines.append(f"- Top-K: **{agg['top_k']}**")
    lines.append("")
    lines.append("## Overall retrieval metrics")
    lines.append("")
    lines.append("| Metric | Mean | 95% CI |")
    lines.append("|---|---:|---|")
    o = agg["overall"]
    lines.append(f"| nDCG@10 | {o['ndcg_at_10']['mean']:.4f} | [{o['ndcg_at_10']['ci95'][0]:.4f}, {o['ndcg_at_10']['ci95'][1]:.4f}] |")
    lines.append(f"| Recall@10 | {o['recall_at_10']['mean']:.4f} | [{o['recall_at_10']['ci95'][0]:.4f}, {o['recall_at_10']['ci95'][1]:.4f}] |")
    lines.append(f"| MRR | {o['mrr']['mean']:.4f} | [{o['mrr']['ci95'][0]:.4f}, {o['mrr']['ci95'][1]:.4f}] |")
    lines.append(f"| session_hit@10 | {o['session_hit_at_10']['mean']:.4f} | Wilson [{o['session_hit_at_10']['wilson_95'][0]:.4f}, {o['session_hit_at_10']['wilson_95'][1]:.4f}] |")
    lines.append("")
    lines.append("## Per-category retrieval metrics")
    lines.append("")
    lines.append("| Category | n | nDCG@10 | Recall@10 | MRR | session_hit@10 |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for cat, v in agg["per_category"].items():
        lines.append(f"| {cat} | {v['n']} | {v['ndcg_at_10']:.4f} | {v['recall_at_10']:.4f} | {v['mrr']:.4f} | {v['session_hit_at_10']:.4f} |")
    lines.append("")
    lines.append("## Abstention split")
    lines.append("")
    lines.append("| Variant | n | nDCG@10 | Recall@10 | MRR | session_hit@10 |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for k, v in agg["per_abstention"].items():
        lines.append(f"| {k} | {v['n']} | {v['ndcg_at_10']:.4f} | {v['recall_at_10']:.4f} | {v['mrr']:.4f} | {v['session_hit_at_10']:.4f} |")
    lines.append("")
    lines.append("## Latency (ms)")
    lines.append("")
    lines.append("| Stage | p50 | p95 | p99 | mean |")
    lines.append("|---|---:|---:|---:|---:|")
    for stage, v in agg["latency_ms"].items():
        lines.append(f"| {stage} | {v['p50']:.1f} | {v['p95']:.1f} | {v['p99']:.1f} | {v['mean']:.1f} |")
    if task_acc:
        lines.append("")
        lines.append("## Task accuracy (LLM-as-judge)")
        lines.append("")
        lines.append(f"- Judge model: **{task_acc['judge_model']}**")
        lines.append(f"- Judged: {task_acc['n_judged']} | Skipped (no gen): {task_acc['n_skipped']} | Judge errors: {task_acc['n_judge_errors']}")
        o = task_acc["overall"]
        lines.append(f"- **Overall accuracy:** {o['accuracy']:.4f} (n={o['n']}, Wilson 95% [{o['wilson_95'][0]:.4f}, {o['wilson_95'][1]:.4f}])")
        lines.append("")
        lines.append("| Category | n | Accuracy | Wilson 95% CI |")
        lines.append("|---|---:|---:|---|")
        for cat, v in task_acc["per_category"].items():
            lines.append(f"| {cat} | {v['n']} | {v['accuracy']:.4f} | [{v['wilson_95'][0]:.4f}, {v['wilson_95'][1]:.4f}] |")
        lines.append("")
        lines.append("| Variant | n | Accuracy | Wilson 95% CI |")
        lines.append("|---|---:|---:|---|")
        for k, v in task_acc["per_abstention"].items():
            lines.append(f"| {k} | {v['n']} | {v['accuracy']:.4f} | [{v['wilson_95'][0]:.4f}, {v['wilson_95'][1]:.4f}] |")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("results_jsonl")
    p.add_argument("--top-k", type=int, default=10)
    p.add_argument("--out", help="aggregate JSON output path (default stdout)")
    p.add_argument("--md-out", help="markdown summary output path (default stderr/none)")
    p.add_argument("--task-accuracy", action="store_true",
                   help="also compute LLM-as-judge task accuracy on generated_answer fields")
    p.add_argument("--judge-model", default="gemini-2.5-flash")
    args = p.parse_args(argv)

    records = load_records(Path(args.results_jsonl))
    print(f"[score] loaded {len(records)} records", file=sys.stderr)
    agg = aggregate(records, args.top_k)

    task_acc = None
    if args.task_accuracy:
        gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not gemini_key:
            print("[score] WARN: --task-accuracy needs GEMINI_API_KEY", file=sys.stderr)
        else:
            task_acc = score_task_accuracy(records, args.judge_model, gemini_key)

    payload = {"retrieval": agg}
    if task_acc:
        payload["task_accuracy"] = task_acc

    out_txt = json.dumps(payload, indent=2)
    if args.out:
        Path(args.out).write_text(out_txt, encoding="utf-8")
        print(f"[score] wrote {args.out}", file=sys.stderr)
    else:
        print(out_txt)

    if args.md_out:
        md = render_md(agg, task_acc)
        Path(args.md_out).write_text(md, encoding="utf-8")
        print(f"[score] wrote {args.md_out}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
