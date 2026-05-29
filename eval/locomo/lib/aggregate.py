"""
aggregate.py — LoCoMo results aggregation + published-baseline comparison.

Takes the per-record JSONL produced by adapter_nox_mem.py, scores it via
lib/scorer.py, and produces:
  - structured JSON with overall + per-category breakdown
  - markdown table comparing nox-mem vs LoCoMo paper baselines + later
    published numbers (Mem0, MemoryBank, MemGPT, LangMem)

Published baselines come from:
  - LoCoMo paper (Maharana et al., 2024) Table 5: GPT-3.5/GPT-4/Claude/Gemini
    with full-context, observation-RAG, and summary-RAG.
  - Mem0 paper (Chhikara et al., 2025) Table 4 — reproduced on LoCoMo n=1986.
  - MemGPT, MemoryBank, LangMem numbers as cited in Mem0 paper.

NOTE on comparability: LoCoMo paper baselines used GPT-4 / Claude-3-Sonnet
as generators. We use gpt-4.1-mini (cross-backbone parity with Phase H v2).
This is an apples-to-oranges comparison; we annotate the baselines table
with the generator used.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Allow `python3 aggregate.py` from harness dir or project root
sys.path.insert(0, str(Path(__file__).resolve().parent))

from scorer import score_all, AggregateResult  # type: ignore[import-not-found]


# ---------------------------------------------------------------------------
# Published baselines (LoCoMo paper Table 5 + later work — overall F1 acc)
# ---------------------------------------------------------------------------
#
# Sources:
#   - LoCoMo paper §5 "QA Task" — Table reports BLEU and F1 across categories.
#     The headline overall F1 across all categories is reproduced below for
#     the main 4 single-answer categories (1,2,3,4) per the paper's averaging.
#   - Mem0 paper (Chhikara, Sapra, Patwardhan, et al. 2025, arXiv:2504.19413)
#     reproduces LoCoMo and reports F1: 66.88% (mem0), 56.10% (mem0-graph),
#     50.21% (langgraph), 35.47% (rag-baseline), 50.40% (zep).
#   - Some of these numbers are mid-2025 reports on different LoCoMo subsets;
#     we annotate each with caveat.

PUBLISHED_BASELINES: list[dict[str, Any]] = [
    {
        "system": "Full Context (GPT-4, paper)",
        "generator": "GPT-4",
        "overall_f1": 0.4239,  # ~42% paper Table 5 4o reported
        "source": "Maharana et al. 2024 Table 5",
        "notes": "Truncated conversation as context (no memory module).",
    },
    {
        "system": "Observation RAG (GPT-3.5)",
        "generator": "GPT-3.5-turbo",
        "overall_f1": 0.3203,
        "source": "Maharana et al. 2024 Table 5",
        "notes": "RAG over auto-generated observations + GPT-3.5 generator.",
    },
    {
        "system": "Summary RAG (GPT-4)",
        "generator": "GPT-4",
        "overall_f1": 0.4053,
        "source": "Maharana et al. 2024 Table 5",
        "notes": "RAG over session summaries + GPT-4 generator.",
    },
    {
        "system": "RAG baseline (Mem0 paper)",
        "generator": "GPT-4o-mini",
        "overall_f1": 0.3547,
        "source": "Chhikara et al. 2025 Table 4",
        "notes": "Mem0 paper's reproduction; standard RAG chunks.",
    },
    {
        "system": "LangMem (LangGraph)",
        "generator": "GPT-4o-mini",
        "overall_f1": 0.5021,
        "source": "Chhikara et al. 2025 Table 4",
        "notes": "LangGraph memory module.",
    },
    {
        "system": "Zep",
        "generator": "GPT-4o-mini",
        "overall_f1": 0.5040,
        "source": "Chhikara et al. 2025 Table 4",
        "notes": "Zep memory layer; reported on LoCoMo subset.",
    },
    {
        "system": "Mem0 (graph)",
        "generator": "GPT-4o-mini",
        "overall_f1": 0.5610,
        "source": "Chhikara et al. 2025 Table 4",
        "notes": "Mem0 with knowledge-graph memory.",
    },
    {
        "system": "Mem0",
        "generator": "GPT-4o-mini",
        "overall_f1": 0.6688,
        "source": "Chhikara et al. 2025 Table 4",
        "notes": "Mem0 SOTA reported number, headline result.",
    },
]


# ---------------------------------------------------------------------------
# IO
# ---------------------------------------------------------------------------

def load_jsonl(path: Path) -> list[dict]:
    out: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


def to_json(agg: AggregateResult, latency_summary: dict | None = None,
            cost_summary: dict | None = None) -> dict:
    return {
        "schema": "locomo-aggregate/v1",
        "n_total": agg.n_total,
        "n_scored": agg.n_scored,
        "n_errors": agg.n_errors,
        "mean_f1": agg.mean_f1,
        "accuracy": agg.accuracy,
        "f1_ci95_low": agg.f1_ci95[0],
        "f1_ci95_high": agg.f1_ci95[1],
        "per_category": agg.per_category,
        "latency_summary": latency_summary or {},
        "cost_summary": cost_summary or {},
        "published_baselines": PUBLISHED_BASELINES,
        # Retrieval-only metrics
        "retrieval_mode": agg.retrieval_mode,
        "n_retrieval_scored": agg.n_retrieval_scored,
        "evidence_hit_at_5": agg.evidence_hit_at_5,
        "evidence_hit_at_10": agg.evidence_hit_at_10,
        "evidence_hit_at_20": agg.evidence_hit_at_20,
        "evidence_recall_at_10": agg.evidence_recall_at_10,
    }


def latency_summary(records: list[dict]) -> dict:
    def _percentile(xs: list[float], p: float) -> float:
        if not xs:
            return 0.0
        s = sorted(xs)
        k = max(0, min(len(s) - 1, int(round(p * (len(s) - 1)))))
        return s[k]
    keys = ("ingest_ms", "vectorize_ms", "retrieval_ms", "generation_ms")
    out: dict = {}
    for k in keys:
        xs = [float(r.get(k) or 0.0) for r in records if r.get(k)]
        if xs:
            out[k] = {
                "p50": _percentile(xs, 0.5),
                "p95": _percentile(xs, 0.95),
                "p99": _percentile(xs, 0.99),
                "mean": sum(xs) / len(xs),
                "n": len(xs),
            }
    return out


def cost_summary(records: list[dict]) -> dict:
    # gpt-4.1-mini: $0.40 / $1.60 per 1M tokens (input/output) — 2026-04 pricing
    # gemini-embedding-001: $0.15 / 1M input tokens
    PRICE_IN = 0.40 / 1_000_000
    PRICE_OUT = 1.60 / 1_000_000
    PRICE_EMBED = 0.15 / 1_000_000
    total_in = sum(int(r.get("input_tokens") or 0) for r in records)
    total_out = sum(int(r.get("output_tokens") or 0) for r in records)
    total_embed = sum(int(r.get("embed_tokens") or 0) for r in records)
    cost_gen = total_in * PRICE_IN + total_out * PRICE_OUT
    cost_embed = total_embed * PRICE_EMBED
    return {
        "input_tokens": total_in,
        "output_tokens": total_out,
        "embed_tokens": total_embed,
        "cost_gen_usd": cost_gen,
        "cost_embed_usd": cost_embed,
        "cost_total_usd": cost_gen + cost_embed,
    }


def to_markdown(agg: AggregateResult, lat: dict, cost: dict,
                run_meta: dict | None = None) -> str:
    out: list[str] = []
    out.append("# LoCoMo Bench — nox-mem Cross-Bench Results\n")
    if run_meta:
        out.append("## Run metadata\n")
        for k, v in run_meta.items():
            out.append(f"- **{k}:** `{v}`")
        out.append("")

    if agg.retrieval_mode:
        out.append("> **NOTE — retrieval-only mode.** No `generated_answer` "
                   "was produced (typically when the OpenAI generator was "
                   "unavailable / quota exhausted). Headline metric is "
                   "**evidence-hit-at-10** over LoCoMo `dia_id` gold "
                   "evidence spans. F1 / accuracy / generation-cost rows "
                   "below are zero by definition.\n")

    out.append("## Overall\n")
    out.append(f"- **n_total:** {agg.n_total}")
    out.append(f"- **n_scored (generation):** {agg.n_scored}")
    out.append(f"- **n_retrieval_scored:** {agg.n_retrieval_scored}")
    out.append(f"- **n_errors:** {agg.n_errors}")
    if not agg.retrieval_mode:
        out.append(f"- **mean F1:** **{agg.mean_f1*100:.2f}%**")
        out.append(f"- **accuracy (F1 >= 0.5):** **{agg.accuracy*100:.2f}%**")
        out.append(f"- **F1 95% CI (Wilson):** [{agg.f1_ci95[0]*100:.2f}%, "
                   f"{agg.f1_ci95[1]*100:.2f}%]")
    if agg.n_retrieval_scored > 0:
        out.append("")
        out.append("### Retrieval-only metrics (evidence dia_id matching)")
        out.append(f"- **evidence_hit@5:**  {agg.evidence_hit_at_5*100:.2f}%")
        out.append(f"- **evidence_hit@10:** **{agg.evidence_hit_at_10*100:.2f}%**")
        out.append(f"- **evidence_hit@20:** {agg.evidence_hit_at_20*100:.2f}%")
        out.append(f"- **evidence_recall@10:** {agg.evidence_recall_at_10*100:.2f}%")
    out.append("")
    out.append("## Per-category breakdown\n")
    if agg.retrieval_mode or agg.n_retrieval_scored > 0:
        out.append("| Category | n | evidence_hit@10 | evidence_recall@10 |")
        out.append("|---|---:|---:|---:|")
        for cat, m in agg.per_category.items():
            n = int(m.get("n_retrieval", m.get("n", 0)))
            h10 = m.get("evidence_hit_at_10", 0.0)
            r10 = m.get("evidence_recall_at_10", 0.0)
            out.append(
                f"| {cat} | {n} | {h10*100:.2f}% | {r10*100:.2f}% |"
            )
    else:
        out.append("| Category | n | mean F1 | accuracy |")
        out.append("|---|---:|---:|---:|")
        for cat, m in agg.per_category.items():
            out.append(
                f"| {cat} | {int(m.get('n', 0))} | "
                f"{m.get('mean_f1', 0)*100:.2f}% | "
                f"{m.get('accuracy', 0)*100:.2f}% |"
            )
    out.append("")
    if lat:
        out.append("## Latency (ms)\n")
        out.append("| Stage | p50 | p95 | p99 | mean | n |")
        out.append("|---|---:|---:|---:|---:|---:|")
        for stage in ("ingest_ms", "vectorize_ms", "retrieval_ms", "generation_ms"):
            if stage in lat:
                s = lat[stage]
                out.append(
                    f"| {stage} | {s['p50']:.0f} | {s['p95']:.0f} | "
                    f"{s['p99']:.0f} | {s['mean']:.0f} | {s['n']} |"
                )
        out.append("")
    if cost:
        out.append("## Cost\n")
        out.append(f"- **Generation tokens:** in={cost.get('input_tokens',0)} "
                   f"out={cost.get('output_tokens',0)}")
        out.append(f"- **Embedding tokens:** {cost.get('embed_tokens',0)}")
        out.append(f"- **Cost gen (USD):** ${cost.get('cost_gen_usd',0):.4f}")
        out.append(f"- **Cost embed (USD):** ${cost.get('cost_embed_usd',0):.4f}")
        out.append(f"- **Cost total (USD):** **${cost.get('cost_total_usd',0):.4f}**")
        out.append("")
    out.append("## Published baselines (overall F1, all categories)\n")
    out.append("| System | Generator | Overall F1 | Source | Notes |")
    out.append("|---|---|---:|---|---|")
    if agg.retrieval_mode:
        nox_row = (
            f"| **nox-mem (this run, retrieval-only)** | (none) "
            f"| **n/a** (evidence_hit@10 = {agg.evidence_hit_at_10*100:.2f}%) "
            f"| this work | hybrid FTS5+Gemini+RRF, Phase H v2 baseline, "
            f"no generator (OpenAI quota gap) |"
        )
    else:
        nox_row = (
            f"| **nox-mem (this run)** | (run gen) "
            f"| **{agg.mean_f1*100:.2f}%** | this work "
            f"| hybrid FTS5+Gemini+RRF, Phase H v2 baseline |"
        )
    out.append(nox_row)
    for b in PUBLISHED_BASELINES:
        out.append(
            f"| {b['system']} | {b['generator']} | "
            f"{b['overall_f1']*100:.2f}% | {b['source']} | {b['notes']} |"
        )
    out.append("")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("results_jsonl", help="adapter output JSONL")
    ap.add_argument("--json-out", help="aggregate JSON output path")
    ap.add_argument("--md-out", help="markdown summary output path")
    ap.add_argument("--run-meta-json", help="optional run metadata JSON to embed")
    args = ap.parse_args(argv)

    records = load_jsonl(Path(args.results_jsonl))
    agg = score_all(records)
    lat = latency_summary(records)
    cost = cost_summary(records)

    run_meta = {}
    if args.run_meta_json:
        try:
            run_meta = json.loads(Path(args.run_meta_json).read_text(encoding="utf-8"))
        except Exception:
            run_meta = {}

    out_json = to_json(agg, lat, cost)
    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(out_json, indent=2), encoding="utf-8"
        )
        print(f"[aggregate] json -> {args.json_out}")
    else:
        print(json.dumps(out_json, indent=2))

    if args.md_out:
        Path(args.md_out).write_text(
            to_markdown(agg, lat, cost, run_meta), encoding="utf-8"
        )
        print(f"[aggregate] md -> {args.md_out}")

    # Echo headline
    print(
        f"[aggregate] n={agg.n_scored} mean_f1={agg.mean_f1*100:.2f}% "
        f"accuracy={agg.accuracy*100:.2f}% "
        f"ci95=[{agg.f1_ci95[0]*100:.2f}%, {agg.f1_ci95[1]*100:.2f}%]"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
