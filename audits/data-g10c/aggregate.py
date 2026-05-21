#!/usr/bin/env python3
"""G10c per-style aggregation from G10b artifacts.

Same A8 canonical config + same g9.db + same harness = G10b runs are
the authoritative source for G10c style breakdown. The harness already
emits per_style natively. We re-derive from per_query to (a) verify
agreement with harness-emitted per_style, and (b) compute the 2D
style×category breakdown that the native per_style flattens.
"""
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path("/tmp/g10c")


def load(path: Path) -> dict:
    with path.open() as f:
        return json.load(f)


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def agg(per_query: list[dict], key_fn) -> dict[str, dict[str, float]]:
    """Group per_query rows by key_fn, return metrics dict per group."""
    buckets: dict[str, list[dict]] = defaultdict(list)
    for q in per_query:
        buckets[key_fn(q)].append(q)
    out: dict[str, dict[str, float]] = {}
    for k, rows in buckets.items():
        out[k] = {
            "n": len(rows),
            "ndcg_at_10": mean([r["ndcg_at_10"] for r in rows]),
            "mrr": mean([r["mrr"] for r in rows]),
            "recall_at_10": mean([r["recall_at_10"] for r in rows]),
            "precision_at_5": mean([r["precision_at_5"] for r in rows]),
        }
    return out


def delta_pct(active: float, disabled: float) -> float:
    if disabled == 0:
        return 0.0 if active == 0 else float("inf")
    return 100.0 * (active - disabled) / disabled


def fmt_row(metric_active: dict, metric_disabled: dict, label: str, n: int) -> str:
    a = metric_active
    d = metric_disabled
    return (
        f"| {label} | {n} | "
        f"{a['ndcg_at_10']:.4f} | {d['ndcg_at_10']:.4f} | "
        f"{a['ndcg_at_10']-d['ndcg_at_10']:+.4f} | "
        f"{delta_pct(a['ndcg_at_10'], d['ndcg_at_10']):+.2f}% | "
        f"{a['mrr']:.4f} | {d['mrr']:.4f} | "
        f"{delta_pct(a['mrr'], d['mrr']):+.2f}% | "
        f"{a['recall_at_10']:.4f} | {d['recall_at_10']:.4f} | "
        f"{delta_pct(a['recall_at_10'], d['recall_at_10']):+.2f}% | "
        f"{a['precision_at_5']:.4f} | {d['precision_at_5']:.4f} | "
        f"{delta_pct(a['precision_at_5'], d['precision_at_5']):+.2f}% |"
    )


def main() -> None:
    active = load(ROOT / "mutex_active.json")
    disabled = load(ROOT / "mutex_disabled.json")

    # ── Verify harness per_style matches our re-derivation ─────────
    derived_active = agg(active["per_query"], lambda q: q["style"])
    derived_disabled = agg(disabled["per_query"], lambda q: q["style"])
    print("# Verification: harness vs re-derived per_style")
    for label, harness_emit, derived in [
        ("active", active["per_style"], derived_active),
        ("disabled", disabled["per_style"], derived_disabled),
    ]:
        for style in ["natural-language", "keyword"]:
            h = harness_emit[style]
            r = derived[style]
            ok = abs(h["ndcg_at_10"] - r["ndcg_at_10"]) < 1e-9
            print(f"  {label}/{style}: ndcg harness={h['ndcg_at_10']:.6f} re-derived={r['ndcg_at_10']:.6f} match={ok}")

    print()
    print("# Per-Style breakdown (full metrics)")
    print()
    print("| style | n | nDCG active | nDCG disabled | Δabs | Δ% | MRR active | MRR disabled | Δ% | R@10 active | R@10 disabled | Δ% | P@5 active | P@5 disabled | Δ% |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for style in ["natural-language", "keyword"]:
        n = derived_active[style]["n"]
        print(fmt_row(derived_active[style], derived_disabled[style], style, n))

    # ── 2D style × category ───────────────────────────────────────
    print()
    print("# Style × Category 2D breakdown — nDCG@10")
    print()
    derived_sc_active = agg(active["per_query"], lambda q: (q["style"], q["category"]))
    derived_sc_disabled = agg(disabled["per_query"], lambda q: (q["style"], q["category"]))

    categories = ["single-hop", "multi-hop", "temporal", "open-domain", "adversarial"]
    print("| style | category | n | nDCG active | nDCG disabled | Δabs | Δ% |")
    print("|---|---|---:|---:|---:|---:|---:|")
    for style in ["natural-language", "keyword"]:
        for cat in categories:
            k = (style, cat)
            a = derived_sc_active.get(k)
            d = derived_sc_disabled.get(k)
            if not a or not d:
                continue
            print(
                f"| {style} | {cat} | {a['n']} | "
                f"{a['ndcg_at_10']:.4f} | {d['ndcg_at_10']:.4f} | "
                f"{a['ndcg_at_10']-d['ndcg_at_10']:+.4f} | "
                f"{delta_pct(a['ndcg_at_10'], d['ndcg_at_10']):+.2f}% |"
            )

    print()
    print("# Style × Category 2D — MRR")
    print()
    print("| style | category | MRR active | MRR disabled | Δ% |")
    print("|---|---|---:|---:|---:|")
    for style in ["natural-language", "keyword"]:
        for cat in categories:
            k = (style, cat)
            a = derived_sc_active.get(k)
            d = derived_sc_disabled.get(k)
            if not a or not d:
                continue
            print(
                f"| {style} | {cat} | "
                f"{a['mrr']:.4f} | {d['mrr']:.4f} | "
                f"{delta_pct(a['mrr'], d['mrr']):+.2f}% |"
            )

    # ── Aggregate cross-check ─────────────────────────────────────
    print()
    print("# Aggregate cross-check (sanity)")
    print()
    a_sum = active["summary"]
    d_sum = disabled["summary"]
    for m in ["ndcg_at_10", "mrr", "recall_at_10", "precision_at_5"]:
        print(
            f"  {m}: active={a_sum[m]:.4f} disabled={d_sum[m]:.4f} "
            f"Δ={a_sum[m]-d_sum[m]:+.4f} Δ%={delta_pct(a_sum[m], d_sum[m]):+.2f}%"
        )

    # ── Save derived JSON ─────────────────────────────────────────
    derived = {
        "per_style_active": derived_active,
        "per_style_disabled": derived_disabled,
        "per_style_x_category_active": {f"{k[0]}|{k[1]}": v for k, v in derived_sc_active.items()},
        "per_style_x_category_disabled": {f"{k[0]}|{k[1]}": v for k, v in derived_sc_disabled.items()},
        "aggregate": {
            "active": a_sum,
            "disabled": d_sum,
        },
    }
    with (ROOT / "g10c-derived.json").open("w") as f:
        json.dump(derived, f, indent=2)
    print()
    print(f"derived JSON: {ROOT / 'g10c-derived.json'}")


if __name__ == "__main__":
    main()
