"""
aggregate.py — aggregate per-question HotPotQA results into corpus-level metrics.

Reads a JSONL file produced by `adapter_nox_mem.py` where each line is:
    {
      "question_id": str,
      "type": "comparison" | "bridge",
      "level": "easy"|"medium"|"hard",
      "predicted_answer": str,
      "gold_answer": str,
      "predicted_supporting_facts": [[title, sent_idx], ...],
      "gold_supporting_facts": [[title, sent_idx], ...],
      "retrieval_ms": float,
      "ingest_ms": float,
      "generation_ms": float,
      "error": str | null,
      ...
    }

Outputs:
    {
      "n_total": ...,
      "n_scored": ...,
      "n_errors": ...,
      "answer": {em, f1, prec, recall, n},
      "supporting_facts": {em, f1, prec, recall, n},
      "joint": {em, f1, prec, recall, n},
      "by_type": {comparison: {...}, bridge: {...}},
      "by_level": {easy: {...}, medium: {...}, hard: {...}},
      "latency_ms": {p50, p95, p99},
      "cost_usd_est": float,
      "config": {...}
    }
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any, Iterable

# Allow running both as module and as script
sys.path.insert(0, str(Path(__file__).resolve().parent))
from scorer import score_record  # type: ignore[import-not-found]


METRIC_FIELDS = (
    "ans_em", "ans_f1", "ans_prec", "ans_recall",
    "sp_em", "sp_f1", "sp_prec", "sp_recall",
    "joint_em", "joint_f1", "joint_prec", "joint_recall",
)


def _mean(xs: Iterable[float]) -> float:
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


def _percentile(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    k = (len(s) - 1) * p
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return s[f]
    return s[f] + (s[c] - s[f]) * (k - f)


def _score_one(rec: dict) -> dict:
    pred_ans = str(rec.get("predicted_answer") or "")
    gold_ans = str(rec.get("gold_answer") or "")
    pred_sp_raw = rec.get("predicted_supporting_facts") or []
    gold_sp_raw = rec.get("gold_supporting_facts") or []
    pred_sp = [(str(x[0]), int(x[1])) for x in pred_sp_raw if isinstance(x, list) and len(x) >= 2]
    gold_sp = [(str(x[0]), int(x[1])) for x in gold_sp_raw if isinstance(x, list) and len(x) >= 2]
    return score_record(pred_ans, gold_ans, pred_sp, gold_sp)


def aggregate(records: list[dict]) -> dict:
    scored: list[dict] = []
    errors = 0
    latencies: list[float] = []
    gen_lat: list[float] = []
    ingest_lat: list[float] = []
    by_type: dict[str, list[dict]] = {}
    by_level: dict[str, list[dict]] = {}

    for r in records:
        if r.get("error"):
            errors += 1
            continue
        try:
            m = _score_one(r)
        except Exception:
            errors += 1
            continue
        m["question_id"] = r.get("question_id")
        scored.append(m)
        # Latency tracking
        if "retrieval_ms" in r:
            try:
                latencies.append(float(r["retrieval_ms"]))
            except (TypeError, ValueError):
                pass
        if "generation_ms" in r:
            try:
                gen_lat.append(float(r["generation_ms"]))
            except (TypeError, ValueError):
                pass
        if "ingest_ms" in r:
            try:
                ingest_lat.append(float(r["ingest_ms"]))
            except (TypeError, ValueError):
                pass
        # Breakdown buckets
        t = str(r.get("type") or "")
        if t:
            by_type.setdefault(t, []).append(m)
        lvl = str(r.get("level") or "")
        if lvl:
            by_level.setdefault(lvl, []).append(m)

    def _summary(items: list[dict]) -> dict:
        if not items:
            return {f: 0.0 for f in METRIC_FIELDS} | {"n": 0}
        return {f: _mean(it[f] for it in items) for f in METRIC_FIELDS} | {"n": len(items)}

    answer = {k.split("ans_")[1]: _summary(scored)[k] for k in METRIC_FIELDS if k.startswith("ans_")}
    answer["n"] = len(scored)
    sp = {k.split("sp_")[1]: _summary(scored)[k] for k in METRIC_FIELDS if k.startswith("sp_")}
    sp["n"] = len(scored)
    joint = {k.split("joint_")[1]: _summary(scored)[k] for k in METRIC_FIELDS if k.startswith("joint_")}
    joint["n"] = len(scored)

    return {
        "n_total": len(records),
        "n_scored": len(scored),
        "n_errors": errors,
        "answer": answer,
        "supporting_facts": sp,
        "joint": joint,
        "by_type": {k: _summary(v) for k, v in sorted(by_type.items())},
        "by_level": {k: _summary(v) for k, v in sorted(by_level.items())},
        "latency_ms": {
            "retrieval_p50": _percentile(latencies, 0.50),
            "retrieval_p95": _percentile(latencies, 0.95),
            "retrieval_p99": _percentile(latencies, 0.99),
            "generation_p50": _percentile(gen_lat, 0.50),
            "generation_p95": _percentile(gen_lat, 0.95),
            "ingest_p50": _percentile(ingest_lat, 0.50),
            "ingest_p95": _percentile(ingest_lat, 0.95),
        },
    }


def load_jsonl(path: Path) -> list[dict]:
    out: list[dict] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="inp", required=True, help="input JSONL path")
    p.add_argument("--out-json", required=True, help="output JSON summary path")
    p.add_argument("--config", default="", help="JSON string of run config to embed")
    args = p.parse_args(argv)

    records = load_jsonl(Path(args.inp))
    print(f"[aggregate] loaded {len(records)} records from {args.inp}", file=sys.stderr)
    agg = aggregate(records)
    if args.config:
        try:
            agg["config"] = json.loads(args.config)
        except json.JSONDecodeError:
            agg["config"] = {"raw": args.config}
    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(agg, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(agg, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
