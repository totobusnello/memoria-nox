"""
rescore_sp_llm.py — Re-score HotPotQA SP-F1 using LLM SP extractor.

Reads an existing RESULTS JSONL produced by adapter_nox_mem.py (PR #408),
replaces predicted_supporting_facts with LLM-extracted ones, and recomputes
full metrics.

This avoids re-running the 8h inference pipeline — only the cheap SP
extraction LLM call is added (~$1.56 for 7405 questions, ~300-500ms/call).

Usage:
    python eval/hotpotqa/rescore_sp_llm.py \
        --input  /path/to/RESULTS-FULL-7K-DEV.jsonl \
        --output /path/to/RESULTS-SP-LLM.jsonl \
        --openai-key $OPENAI_API_KEY

Output:
    RESULTS-SP-LLM.jsonl — same fields as input + sp_llm_* fields
    RESULTS-SP-LLM.json  — aggregate metrics JSON
    RESULTS-SP-LLM.md    — human-readable results markdown
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Add eval/hotpotqa to path so we can import lib modules
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from lib.sp_extractor import extract_supporting_facts  # type: ignore[import-not-found]
from lib.scorer import score_record  # type: ignore[import-not-found]

# Also need the original SP heuristic for fallback
sys.path.insert(0, str(_HERE))


# ---------------------------------------------------------------------------
# Heuristic SP fallback (copy from adapter — avoids circular import)
# ---------------------------------------------------------------------------

import re as _re
_TOKEN_RE = _re.compile(r"[A-Za-z0-9]+")
DEFAULT_MAX_SP_SENTENCES = 6


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


def predict_sp_heuristic(
    question: str,
    retrieved_titles: list[str],
    paragraphs_by_title: dict[str, list[str]],  # title -> sentences
    max_titles: int = 2,
    max_sentences_per_title: int = 3,
) -> list[list]:
    """Token-overlap SP heuristic (baseline, same as adapter)."""
    pred: list[list] = []
    seen: set[str] = set()
    q_tokens = set(_tokenize(question))
    for title in retrieved_titles:
        if title in seen:
            continue
        sents = paragraphs_by_title.get(title)
        if sents is None:
            continue
        seen.add(title)
        scored: list[tuple[int, float, int]] = []
        for i, s in enumerate(sents):
            s_tokens = set(_tokenize(s))
            if not s_tokens:
                continue
            overlap = len(q_tokens & s_tokens)
            if overlap == 0:
                continue
            scored.append((i, float(overlap) / max(1, len(s_tokens)), i))
        scored.sort(key=lambda x: (-x[1], x[2]))
        for i, _score, _tb in scored[:max_sentences_per_title]:
            pred.append([title, int(i)])
        if not scored and sents:
            pred.append([title, 0])
        if len(seen) >= max_titles:
            break
    return pred[:DEFAULT_MAX_SP_SENTENCES]


# ---------------------------------------------------------------------------
# Metric aggregation
# ---------------------------------------------------------------------------

@dataclass
class MetricAccum:
    n: int = 0
    n_sp_llm: int = 0         # LLM extractions (non-fallback)
    n_sp_fallback: int = 0    # fallback to heuristic
    n_error: int = 0
    sp_llm_latency_ms_total: float = 0.0

    # Baseline metrics (from PR #408 heuristic SP)
    base_sp_f1: float = 0.0
    base_sp_em: float = 0.0
    base_joint_f1: float = 0.0
    base_joint_em: float = 0.0

    # LLM SP metrics
    llm_sp_f1: float = 0.0
    llm_sp_em: float = 0.0
    llm_joint_f1: float = 0.0
    llm_joint_em: float = 0.0

    # Answer metrics (unchanged — same predicted_answer)
    ans_f1: float = 0.0
    ans_em: float = 0.0
    ans_prec: float = 0.0
    ans_recall: float = 0.0

    # Per-type accumulators
    bridge: "MetricAccum" = field(default_factory=lambda: MetricAccum.__new__(MetricAccum))
    comparison: "MetricAccum" = field(default_factory=lambda: MetricAccum.__new__(MetricAccum))
    _is_sub: bool = False

    def __post_init__(self) -> None:
        if not self._is_sub:
            self.bridge = _SubAccum()
            self.comparison = _SubAccum()

    def add(self, rec: dict, base_scores: dict, llm_scores: dict) -> None:
        self.n += 1
        self.base_sp_f1 += base_scores["sp_f1"]
        self.base_sp_em += base_scores["sp_em"]
        self.base_joint_f1 += base_scores["joint_f1"]
        self.base_joint_em += base_scores["joint_em"]
        self.llm_sp_f1 += llm_scores["sp_f1"]
        self.llm_sp_em += llm_scores["sp_em"]
        self.llm_joint_f1 += llm_scores["joint_f1"]
        self.llm_joint_em += llm_scores["joint_em"]
        self.ans_f1 += llm_scores["ans_f1"]
        self.ans_em += llm_scores["ans_em"]
        self.ans_prec += llm_scores["ans_prec"]
        self.ans_recall += llm_scores["ans_recall"]
        qtype = rec.get("type", "unknown")
        if qtype == "bridge":
            self.bridge.add(rec, base_scores, llm_scores)
        elif qtype == "comparison":
            self.comparison.add(rec, base_scores, llm_scores)

    def summary(self) -> dict:
        n = max(self.n, 1)
        return {
            "n": self.n,
            "n_sp_llm": self.n_sp_llm,
            "n_sp_fallback": self.n_sp_fallback,
            "n_error": self.n_error,
            "sp_llm_latency_p50_ms": None,   # filled post-hoc
            "ans_f1": round(100 * self.ans_f1 / n, 4),
            "ans_em": round(100 * self.ans_em / n, 4),
            "ans_prec": round(100 * self.ans_prec / n, 4),
            "ans_recall": round(100 * self.ans_recall / n, 4),
            "base_sp_f1": round(100 * self.base_sp_f1 / n, 4),
            "base_sp_em": round(100 * self.base_sp_em / n, 4),
            "base_joint_f1": round(100 * self.base_joint_f1 / n, 4),
            "base_joint_em": round(100 * self.base_joint_em / n, 4),
            "llm_sp_f1": round(100 * self.llm_sp_f1 / n, 4),
            "llm_sp_em": round(100 * self.llm_sp_em / n, 4),
            "llm_joint_f1": round(100 * self.llm_joint_f1 / n, 4),
            "llm_joint_em": round(100 * self.llm_joint_em / n, 4),
            "sp_f1_delta": round(100 * (self.llm_sp_f1 - self.base_sp_f1) / n, 4),
            "joint_f1_delta": round(100 * (self.llm_joint_f1 - self.base_joint_f1) / n, 4),
            "bridge": self.bridge.summary() if not self._is_sub else None,
            "comparison": self.comparison.summary() if not self._is_sub else None,
        }


class _SubAccum(MetricAccum):
    """Sub-accumulator (no nested bridge/comparison)."""
    def __init__(self) -> None:
        self.n = 0
        self.n_sp_llm = 0
        self.n_sp_fallback = 0
        self.n_error = 0
        self.sp_llm_latency_ms_total = 0.0
        self.base_sp_f1 = 0.0
        self.base_sp_em = 0.0
        self.base_joint_f1 = 0.0
        self.base_joint_em = 0.0
        self.llm_sp_f1 = 0.0
        self.llm_sp_em = 0.0
        self.llm_joint_f1 = 0.0
        self.llm_joint_em = 0.0
        self.ans_f1 = 0.0
        self.ans_em = 0.0
        self.ans_prec = 0.0
        self.ans_recall = 0.0
        self._is_sub = True

    def add(self, rec: dict, base_scores: dict, llm_scores: dict) -> None:
        """Accumulate without sub-type dispatch (no bridge/comparison nesting)."""
        self.n += 1
        self.base_sp_f1 += base_scores["sp_f1"]
        self.base_sp_em += base_scores["sp_em"]
        self.base_joint_f1 += base_scores["joint_f1"]
        self.base_joint_em += base_scores["joint_em"]
        self.llm_sp_f1 += llm_scores["sp_f1"]
        self.llm_sp_em += llm_scores["sp_em"]
        self.llm_joint_f1 += llm_scores["joint_f1"]
        self.llm_joint_em += llm_scores["joint_em"]
        self.ans_f1 += llm_scores["ans_f1"]
        self.ans_em += llm_scores["ans_em"]
        self.ans_prec += llm_scores["ans_prec"]
        self.ans_recall += llm_scores["ans_recall"]

    def summary(self) -> dict:
        n = max(self.n, 1)
        return {
            "n": self.n,
            "base_sp_f1": round(100 * self.base_sp_f1 / n, 4),
            "llm_sp_f1": round(100 * self.llm_sp_f1 / n, 4),
            "base_joint_f1": round(100 * self.base_joint_f1 / n, 4),
            "llm_joint_f1": round(100 * self.llm_joint_f1 / n, 4),
            "sp_f1_delta": round(100 * (self.llm_sp_f1 - self.base_sp_f1) / n, 4),
            "joint_f1_delta": round(100 * (self.llm_joint_f1 - self.base_joint_f1) / n, 4),
            "ans_f1": round(100 * self.ans_f1 / n, 4),
        }


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------

def render_markdown(summary: dict, out_jsonl: str, elapsed_s: float) -> str:
    s = summary
    bridge = s.get("bridge") or {}
    comparison = s.get("comparison") or {}

    sp_delta = s["sp_f1_delta"]
    joint_delta = s["joint_f1_delta"]
    gate1_pass = sp_delta >= 5.0
    gate2_pass = joint_delta >= 3.0
    latency_note = s.get("sp_llm_latency_p50_ms")
    if latency_note is not None:
        gate3_pass = latency_note <= 1000.0
        gate3_note = f"{latency_note:.0f}ms p50"
    else:
        gate3_pass = None
        gate3_note = "N/A"

    verdict_parts = []
    if gate1_pass:
        verdict_parts.append(f"SP-F1 +{sp_delta:.2f}pp GATE PASS")
    else:
        verdict_parts.append(f"SP-F1 +{sp_delta:.2f}pp GATE FAIL (need +5pp)")
    if gate2_pass:
        verdict_parts.append(f"joint_F1 +{joint_delta:.2f}pp GATE PASS")
    else:
        verdict_parts.append(f"joint_F1 +{joint_delta:.2f}pp GATE FAIL (need +3pp)")

    verdict = " | ".join(verdict_parts)

    lines = [
        "# HotPotQA SP-F1 LLM Extractor — Results",
        "",
        f"> **{verdict}**",
        "",
        "## Summary",
        "",
        "```",
        f"RESULTS (n={s['n']}, HotPotQA distractor dev)",
        "",
        f"  ans_F1:              {s['ans_f1']:.2f}%   (unchanged from PR #408)",
        f"  ans_EM:              {s['ans_em']:.2f}%",
        "",
        f"  --- Supporting Facts ---",
        f"  baseline  sp_F1:    {s['base_sp_f1']:.2f}%   (token-overlap heuristic, PR #408)",
        f"  llm       sp_F1:    {s['llm_sp_f1']:.2f}%   (gpt-4.1-mini extractor)",
        f"  Δ sp_F1:          {sp_delta:+.2f}pp",
        "",
        f"  baseline  sp_EM:    {s['base_sp_em']:.2f}%",
        f"  llm       sp_EM:    {s['llm_sp_em']:.2f}%",
        "",
        f"  --- Joint Metrics ---",
        f"  baseline  joint_F1: {s['base_joint_f1']:.2f}%",
        f"  llm       joint_F1: {s['llm_joint_f1']:.2f}%",
        f"  Δ joint_F1:       {joint_delta:+.2f}pp",
        "",
        f"  baseline  joint_EM: {s['base_joint_em']:.2f}%",
        f"  llm       joint_EM: {s['llm_joint_em']:.2f}%",
        "",
        f"  --- SP LLM Extraction Stats ---",
        f"  LLM calls:          {s['n_sp_llm']}  ({100*s['n_sp_llm']/max(s['n'],1):.1f}% of questions)",
        f"  Fallback (heuristic):{s['n_sp_fallback']}  ({100*s['n_sp_fallback']/max(s['n'],1):.1f}%)",
        f"  Errors:             {s['n_error']}",
        f"  Latency p50:        {gate3_note}",
        f"  Wall-clock:         {elapsed_s/60:.1f}min",
        "```",
        "",
        "## Gate Evaluation",
        "",
        f"| Gate | Target | Result | Pass? |",
        f"|---|---|---|---|",
        f"| SP-F1 lift ≥ +5pp | ≥59.22% | {s['llm_sp_f1']:.2f}% (+{sp_delta:.2f}pp) | {'PASS' if gate1_pass else 'FAIL'} |",
        f"| Joint-F1 lift ≥ +3pp | ≥46.97% | {s['llm_joint_f1']:.2f}% (+{joint_delta:.2f}pp) | {'PASS' if gate2_pass else 'FAIL'} |",
        f"| Latency overhead ≤ +1s | ≤1000ms/q | {gate3_note} | {'PASS' if gate3_pass else ('FAIL' if gate3_pass is False else 'N/A')} |",
        f"| Cost ≤ $3 for full bench | ≤$3 | ~$1.56 est. | PASS |",
        "",
        "## Per Question Type",
        "",
        "| Type | n | base sp_F1 | llm sp_F1 | Δ | base joint_F1 | llm joint_F1 | Δ | ans_F1 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for qtype, sub in [("bridge", bridge), ("comparison", comparison)]:
        if sub and sub.get("n", 0) > 0:
            lines.append(
                f"| {qtype} | {sub['n']} "
                f"| {sub['base_sp_f1']:.2f}% "
                f"| {sub['llm_sp_f1']:.2f}% "
                f"| {sub['sp_f1_delta']:+.2f}pp "
                f"| {sub['base_joint_f1']:.2f}% "
                f"| {sub['llm_joint_f1']:.2f}% "
                f"| {sub['joint_f1_delta']:+.2f}pp "
                f"| {sub['ans_f1']:.2f}% |"
            )

    lines += [
        "",
        "## Methodology",
        "",
        "- **Input:** PR #408 JSONL (7405 answers already generated — no re-inference)",
        "- **SP extractor:** `eval/hotpotqa/lib/sp_extractor.py`",
        "- **Model:** gpt-4.1-mini @ temp=0, max_tokens=256",
        "- **Fallback:** token-overlap heuristic on LLM error/timeout",
        "- **Paragraph rendering:** chunk body split into sentences, capped at 12/para",
        "- **Scoring:** official HotPotQA scorer (hotpot_evaluate_v1.py re-implementation)",
        "",
        "## Competitive Position Update",
        "",
        "| System | ans_F1 | sp_F1 | joint_F1 | Notes |",
        "|---|---|---|---|---|",
        "| DPR + FiD (SOTA reader ~2021) | 65-72 | 75-82 | 50-58 | specialized multi-hop |",
        f"| **nox-mem PR #408 baseline** | **73.37** | **55.29** | **42.97** | token-overlap SP heuristic |",
        f"| **nox-mem SP-LLM extractor (this PR)** | **{s['ans_f1']:.2f}** | **{s['llm_sp_f1']:.2f}** | **{s['llm_joint_f1']:.2f}** | LLM SP + same ans |",
        "",
        f"> Output: `{out_jsonl}`",
    ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Re-score HotPotQA SP-F1 using LLM extractor")
    p.add_argument("--input", required=True, help="Input JSONL from adapter_nox_mem.py")
    p.add_argument("--output", required=True, help="Output JSONL path (will write sp_llm_* fields)")
    p.add_argument("--openai-key", default=os.environ.get("OPENAI_API_KEY", ""))
    p.add_argument("--model", default="gpt-4.1-mini")
    p.add_argument("--timeout", type=int, default=20)
    p.add_argument("--n", type=int, default=0, help="Hard cap on n questions (0=all)")
    p.add_argument("--progress-every", type=int, default=100)
    p.add_argument("--no-fallback", action="store_true",
                   help="Do not fall back to heuristic on LLM error")
    args = p.parse_args(argv)

    if not args.openai_key:
        raise SystemExit("OPENAI_API_KEY required (--openai-key or env var)")

    in_path = Path(args.input)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_json_path = out_path.with_suffix(".json")
    out_md_path = out_path.with_suffix(".md")

    print(f"[rescore_sp] input={in_path}", file=sys.stderr)
    print(f"[rescore_sp] output={out_path}", file=sys.stderr)
    print(f"[rescore_sp] model={args.model}", file=sys.stderr)

    # Load all records
    records: list[dict] = []
    with in_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    print(f"[rescore_sp] loaded {len(records)} records", file=sys.stderr)

    if args.n > 0:
        records = records[: args.n]
        print(f"[rescore_sp] capped to n={len(records)}", file=sys.stderr)

    accum = MetricAccum()
    latency_samples: list[float] = []
    t_start = time.time()

    with out_path.open("w", encoding="utf-8") as fh_out:
        for i, rec in enumerate(records):
            question = rec.get("question", "")
            predicted_answer = rec.get("predicted_answer", "")
            gold_supporting = rec.get("gold_supporting_facts", [])
            pred_sp_heuristic = rec.get("predicted_supporting_facts", [])
            retrieved_texts = rec.get("retrieved_texts", [])
            retrieved_titles = rec.get("retrieved_paragraph_titles", [])
            qtype = rec.get("type", "unknown")
            gold_answer = rec.get("gold_answer", "")

            # ---- Baseline SP scores (from PR #408 heuristic) ----
            base_scores = score_record(
                predicted_answer,
                gold_answer,
                [tuple(x) for x in pred_sp_heuristic],  # type: ignore[arg-type]
                [tuple(x) for x in gold_supporting],     # type: ignore[arg-type]
            )

            # ---- LLM SP extraction ----
            sp_llm: list[list] = []
            sp_llm_ms: float = 0.0
            sp_llm_used: bool = False
            sp_llm_err: Optional[str] = None

            if retrieved_texts and predicted_answer:
                sp_llm, sp_llm_ms, sp_llm_err = extract_supporting_facts(
                    question=question,
                    answer=predicted_answer,
                    chunk_texts=retrieved_texts,
                    paragraph_titles=retrieved_titles,
                    api_key=args.openai_key,
                    model=args.model,
                    timeout=args.timeout,
                )
                if sp_llm_err:
                    accum.n_error += 1
                    if not args.no_fallback:
                        sp_llm = pred_sp_heuristic  # type: ignore[assignment]
                        accum.n_sp_fallback += 1
                else:
                    sp_llm_used = True
                    accum.n_sp_llm += 1
                    latency_samples.append(sp_llm_ms)
            else:
                # No text retrieved — fallback to heuristic
                sp_llm = pred_sp_heuristic  # type: ignore[assignment]
                accum.n_sp_fallback += 1

            # ---- LLM SP scores ----
            llm_scores = score_record(
                predicted_answer,
                gold_answer,
                [tuple(x) for x in sp_llm],      # type: ignore[arg-type]
                [tuple(x) for x in gold_supporting], # type: ignore[arg-type]
            )

            accum.add(rec, base_scores, llm_scores)

            # Write enriched record
            out_rec = dict(rec)
            out_rec["sp_llm_predicted"] = sp_llm
            out_rec["sp_llm_ms"] = sp_llm_ms
            out_rec["sp_llm_used"] = sp_llm_used
            out_rec["sp_llm_error"] = sp_llm_err
            out_rec["sp_llm_f1"] = llm_scores["sp_f1"]
            out_rec["sp_llm_em"] = llm_scores["sp_em"]
            out_rec["sp_base_f1"] = base_scores["sp_f1"]
            out_rec["joint_llm_f1"] = llm_scores["joint_f1"]
            out_rec["joint_base_f1"] = base_scores["joint_f1"]
            fh_out.write(json.dumps(out_rec) + "\n")

            if (i + 1) % args.progress_every == 0:
                elapsed = time.time() - t_start
                rate = (i + 1) / elapsed
                eta = (len(records) - i - 1) / rate if rate > 0 else 0
                avg_lat = sum(latency_samples[-100:]) / max(len(latency_samples[-100:]), 1)
                print(
                    f"[rescore_sp] {i+1}/{len(records)} "
                    f"({100*(i+1)/len(records):.1f}%) "
                    f"llm={accum.n_sp_llm} fallback={accum.n_sp_fallback} "
                    f"errors={accum.n_error} "
                    f"avg_llm_lat={avg_lat:.0f}ms "
                    f"elapsed={elapsed:.0f}s ETA={eta:.0f}s",
                    file=sys.stderr,
                )

    elapsed = time.time() - t_start

    # Compute p50 latency
    if latency_samples:
        latency_samples.sort()
        p50_ms = latency_samples[len(latency_samples) // 2]
    else:
        p50_ms = 0.0

    # Final summary
    accum.n_sp_llm = accum.n_sp_llm
    summary = accum.summary()
    summary["sp_llm_latency_p50_ms"] = round(p50_ms, 1)
    summary["elapsed_s"] = round(elapsed, 1)

    # Write JSON metrics
    out_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[rescore_sp] metrics written to {out_json_path}", file=sys.stderr)

    # Write markdown
    md = render_markdown(summary, str(out_path), elapsed)
    out_md_path.write_text(md, encoding="utf-8")
    print(f"[rescore_sp] markdown written to {out_md_path}", file=sys.stderr)

    # Print headline to stdout
    sp_delta = summary["sp_f1_delta"]
    joint_delta = summary["joint_f1_delta"]
    print(
        f"\n=== SP-LLM EXTRACTOR RESULTS (n={summary['n']}) ===\n"
        f"  ans_F1:           {summary['ans_f1']:.2f}%  (unchanged)\n"
        f"  base sp_F1:       {summary['base_sp_f1']:.2f}%  (PR #408 heuristic)\n"
        f"  llm  sp_F1:       {summary['llm_sp_f1']:.2f}%  Δ{sp_delta:+.2f}pp\n"
        f"  base joint_F1:    {summary['base_joint_f1']:.2f}%\n"
        f"  llm  joint_F1:    {summary['llm_joint_f1']:.2f}%  Δ{joint_delta:+.2f}pp\n"
        f"  LLM extractions:  {summary['n_sp_llm']}\n"
        f"  Fallbacks:        {summary['n_sp_fallback']}\n"
        f"  Latency p50:      {p50_ms:.0f}ms\n"
        f"  Wall-clock:       {elapsed/60:.1f}min\n"
        f"\n  GATE 1 (SP +5pp): {'PASS' if sp_delta >= 5 else 'FAIL'}\n"
        f"  GATE 2 (joint +3pp): {'PASS' if joint_delta >= 3 else 'FAIL'}\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
