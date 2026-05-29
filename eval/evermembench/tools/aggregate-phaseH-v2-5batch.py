#!/usr/bin/env python3
"""Aggregate Phase H v2 5-batch results.

Schema: top-level dict with `detailed_results` list of records:
  { question_id: "<MAJOR>_<MINOR>_TopXXX_NNN", question_type, is_correct }
"""
import json
import re
import statistics
import sys
from math import sqrt
from pathlib import Path

RESULTS = {
    "004": "/root/.openclaw/evermembench-runs/phaseH-v2-004-1780019268/results-batch-004.json",
    "005": "/root/.openclaw/evermembench-runs/phaseH-v2-005-1780022478/results-batch-005.json",
    "010": "/root/.openclaw/evermembench-runs/phaseH-v2-010-1780022481/results-batch-010.json",
    "011": "/root/.openclaw/evermembench-runs/phaseH-v2-011-1780022485/results-batch-011.json",
    "016": "/root/.openclaw/evermembench-runs/phaseH-v2-016-1780022490/results-batch-016.json",
}

MEMOS = {
    "Overall":  42.55,
    "F_SH":     71.36,
    "F_MH":     18.88,
    "F_TP":     15.67,
    "MA_C":     69.90,
    "MA_P":     51.99,
    "MA_U":     45.15,
    "P_Style":  28.98,
    "P_Skill":  32.54,
    "P_Title":  48.47,
}

B004_SINGLE = 54.15
PHASE_D_5BATCH_OVERALL = 62.22
T_CRIT_4 = 2.776

QID_RE = re.compile(r"^([A-Z]+)_([A-Za-z]+)_Top\d+_\d+$")


def parse_qid(qid):
    m = QID_RE.match(qid)
    if not m:
        return None, None
    return m.group(1), m.group(2)


def load_batch(path):
    with open(path) as f:
        data = json.load(f)
    records = data["detailed_results"]
    total_n = len(records)
    total_correct = 0
    minor_buckets, combined_buckets, major_buckets, type_buckets = {}, {}, {}, {}
    unparseable = 0
    for r in records:
        correct = 1 if r.get("is_correct") else 0
        total_correct += correct
        qid = r.get("question_id", "")
        major, minor = parse_qid(qid)
        if not major or not minor:
            unparseable += 1
            continue
        n, c = minor_buckets.get(minor, (0, 0)); minor_buckets[minor] = (n + 1, c + correct)
        n, c = major_buckets.get(major, (0, 0)); major_buckets[major] = (n + 1, c + correct)
        key = f"{major}_{minor}"
        n, c = combined_buckets.get(key, (0, 0)); combined_buckets[key] = (n + 1, c + correct)
        qtype = r.get("question_type", "")
        if qtype:
            n, c = type_buckets.get(qtype, (0, 0)); type_buckets[qtype] = (n + 1, c + correct)
    return {
        "total_n": total_n,
        "total_correct": total_correct,
        "overall_pct": 100.0 * total_correct / max(total_n, 1),
        "minor": minor_buckets, "major": major_buckets, "combined": combined_buckets,
        "type": type_buckets, "unparseable_qids": unparseable,
    }


def pct(c, n):
    return (100.0 * c / n) if n else float("nan")


def ci95(values, n):
    if n < 2:
        return (float("nan"), float("nan"), float("nan"))
    mean = statistics.mean(values)
    stdev = statistics.stdev(values)
    se = stdev / sqrt(n)
    half = T_CRIT_4 * se
    return mean, half, stdev


def main():
    per_batch = {}
    for b, path in RESULTS.items():
        if not Path(path).exists():
            print(f"MISSING: {path}", file=sys.stderr); sys.exit(1)
        per_batch[b] = load_batch(path)
    batches = list(per_batch.keys())

    print("# Phase H v2 5-batch aggregate\n")
    for b in batches:
        d = per_batch[b]
        if d["unparseable_qids"]:
            print(f"> NOTE: batch {b} had {d['unparseable_qids']} unparseable question_ids.")
    print()

    print("## Per-batch overall accuracy\n")
    print("| batch | total | correct | accuracy |")
    print("|---|---:|---:|---:|")
    for b in batches:
        d = per_batch[b]
        print(f"| {b} | {d['total_n']} | {d['total_correct']} | {d['overall_pct']:.2f}% |")
    total_n = sum(per_batch[b]["total_n"] for b in batches)
    total_c = sum(per_batch[b]["total_correct"] for b in batches)
    weighted = 100.0 * total_c / total_n
    print(f"| **5-batch weighted** | **{total_n}** | **{total_c}** | **{weighted:.2f}%** |")
    print()

    overalls = [per_batch[b]["overall_pct"] for b in batches]
    mean_o, half_o, sd_o = ci95(overalls, len(overalls))
    lo, hi = mean_o - half_o, mean_o + half_o
    print(f"- Per-batch mean: **{mean_o:.2f}%**")
    print(f"- Sample stdev: **{sd_o:.2f} pp**")
    print(f"- 95% CI (t-dist, n=5, dof=4): **{lo:.2f}% – {hi:.2f}%** (±{half_o:.2f} pp)")
    print(f"- Min: {min(overalls):.2f}% (batch {batches[overalls.index(min(overalls))]}) / "
          f"Max: {max(overalls):.2f}% (batch {batches[overalls.index(max(overalls))]})")
    print()

    all_keys = set()
    for b in batches:
        all_keys.update(per_batch[b]["combined"].keys())
    cat_order = ["F_SH", "F_MH", "F_TP", "F_HL", "MA_C", "MA_P", "MA_U", "P_Style", "P_Skill", "P_Title"]
    cat_order_used = [k for k in cat_order if k in all_keys]

    print("## Per-category 5-batch results vs MemOS GPT-4.1-mini\n")
    print("| category | 004 | 005 | 010 | 011 | 016 | mean | stdev | 95% CI | weighted | MemOS | Δ |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    cat_aggregates = {}
    for cat in cat_order_used:
        pcts, ns, cs = [], [], []
        for b in batches:
            n, c = per_batch[b]["combined"].get(cat, (0, 0))
            ns.append(n); cs.append(c)
            pcts.append(pct(c, n) if n else 0.0)
        mean, half, sd = ci95(pcts, len(pcts))
        clo, chi = mean - half, mean + half
        weighted_pct = 100.0 * sum(cs) / sum(ns) if sum(ns) else float("nan")
        memos_v = MEMOS.get(cat)
        delta = (weighted_pct - memos_v) if memos_v is not None else float("nan")
        row = (f"| {cat} | "
               + " | ".join(f"{p:.2f}%" for p in pcts)
               + f" | {mean:.2f}% | {sd:.2f} | {clo:.2f}–{chi:.2f}% | "
               + f"**{weighted_pct:.2f}%** | "
               + (f"{memos_v:.2f}%" if memos_v is not None else "—")
               + " | "
               + (f"**{delta:+.2f}**" if memos_v is not None else "—")
               + " |")
        print(row)
        cat_aggregates[cat] = {"pcts": pcts, "mean": mean, "stdev": sd, "ci_lo": clo, "ci_hi": chi,
                              "weighted": weighted_pct, "memos": memos_v, "delta": delta,
                              "ns": ns, "cs": cs}

    delta_o = weighted - MEMOS["Overall"]
    print(f"| **Overall** | "
          + " | ".join(f"{p:.2f}%" for p in overalls)
          + f" | {mean_o:.2f}% | {sd_o:.2f} | {lo:.2f}–{hi:.2f}% | "
          + f"**{weighted:.2f}%** | {MEMOS['Overall']:.2f}% | **{delta_o:+.2f}** |")
    print()

    print("## Per-question-type\n")
    print("| type | 5-batch n | correct | weighted | per-batch (004/005/010/011/016) |")
    print("|---|---:|---:|---:|---|")
    for t in ("multiple_choice", "open_ended"):
        n_total = c_total = 0
        per_b = []
        for b in batches:
            n, c = per_batch[b]["type"].get(t, (0, 0))
            n_total += n; c_total += c
            per_b.append(pct(c, n) if n else 0.0)
        weighted_t = 100.0 * c_total / n_total if n_total else float("nan")
        print(f"| {t} | {n_total} | {c_total} | **{weighted_t:.2f}%** | {' / '.join(f'{p:.2f}' for p in per_b)} |")
    print()

    b004_overall = per_batch["004"]["overall_pct"]
    z = (b004_overall - mean_o) / sd_o if sd_o else float("nan")
    print("## Variance analysis — was batch 004 outlier?\n")
    print(f"- Batch 004 overall: **{b004_overall:.2f}%**")
    print(f"- 5-batch mean: **{mean_o:.2f}%**")
    print(f"- 5-batch 95% CI: **{lo:.2f}–{hi:.2f}%**")
    print(f"- Batch 004 z-score: **{z:+.2f} σ**")
    if b004_overall > hi:
        verdict = "**Batch 004 was upper-tail outlier (above 95% CI upper bound).**"
    elif b004_overall < lo:
        verdict = "**Batch 004 was lower-tail outlier (below 95% CI lower bound).**"
    else:
        verdict = "**Batch 004 within 5-batch 95% CI (representative).**"
    print(f"- Verdict: {verdict}")
    print()

    reportable = [c for c in cat_order_used if cat_aggregates[c]["memos"] is not None]
    win_count = sum(1 for c in reportable if cat_aggregates[c]["delta"] > 0)
    lose_count = sum(1 for c in reportable if cat_aggregates[c]["delta"] < 0)
    se_o = sd_o / sqrt(len(overalls))
    halflen_o = T_CRIT_4 * se_o
    weighted_lo = weighted - halflen_o
    weighted_hi = weighted + halflen_o

    print("## Cross-backbone WIN vs MemOS GPT-4.1-mini\n")
    print(f"- 5-batch weighted overall: **{weighted:.2f}% vs MemOS 42.55% → {delta_o:+.2f} pp**")
    print(f"- Sub-dims WIN: **{win_count} / {len(reportable)}** (F_HL excluded — MemOS doesn't report)")
    print(f"- Sub-dims LOSE: {lose_count} / {len(reportable)}")
    print(f"- Per-batch 95% CI for overall: **{weighted_lo:.2f}–{weighted_hi:.2f}%**")
    if weighted_lo > MEMOS["Overall"]:
        print(f"- **WIN is statistically robust:** CI lower bound {weighted_lo:.2f}% > MemOS 42.55%.")
    else:
        print(f"- WIN not statistically distinguishable at 95% CI (lower bound {weighted_lo:.2f}% < 42.55%).")
    print()

    print("## Best / worst sub-dim per-batch swings\n")
    print("| category | min batch | min % | max batch | max % | swing (pp) |")
    print("|---|---|---:|---|---:|---:|")
    for cat in cat_order_used:
        pcts = cat_aggregates[cat]["pcts"]
        min_i = pcts.index(min(pcts)); max_i = pcts.index(max(pcts))
        print(f"| {cat} | {batches[min_i]} | {pcts[min_i]:.2f}% | {batches[max_i]} | {pcts[max_i]:.2f}% | {pcts[max_i]-pcts[min_i]:.2f} |")
    print()

    print("## Headline summary\n")
    print("| metric | Phase H v2 batch 004 (PR #372) | Phase H v2 5-batch | MemOS GPT-4.1-mini |")
    print("|---|---:|---:|---:|")
    print(f"| Overall | {B004_SINGLE:.2f}% | **{weighted:.2f}%** | 42.55% |")
    print(f"| Δ vs MemOS | +11.60 pp | **{delta_o:+.2f} pp** | — |")
    print()

    with open("/tmp/phaseH-v2-5batch-agg.json", "w") as f:
        out = {
            "per_batch": {b: {
                "total_n": per_batch[b]["total_n"],
                "total_correct": per_batch[b]["total_correct"],
                "overall_pct": per_batch[b]["overall_pct"],
                "combined": {k: {"n": v[0], "correct": v[1], "pct": pct(v[1], v[0])}
                              for k, v in per_batch[b]["combined"].items()},
                "type": {k: {"n": v[0], "correct": v[1], "pct": pct(v[1], v[0])}
                          for k, v in per_batch[b]["type"].items()},
            } for b in batches},
            "weighted_overall": weighted,
            "per_batch_overall_pcts": overalls,
            "overall_mean": mean_o,
            "overall_stdev": sd_o,
            "overall_ci_lo": lo,
            "overall_ci_hi": hi,
            "weighted_ci_lo": weighted_lo,
            "weighted_ci_hi": weighted_hi,
            "categories": {k: {kk: vv for kk, vv in v.items()} for k, v in cat_aggregates.items()},
            "memos_baseline": MEMOS,
            "b004_single_overall": B004_SINGLE,
            "verdict_b004": verdict,
        }
        json.dump(out, f, indent=2, default=str)
    print("Structured aggregate saved -> /tmp/phaseH-v2-5batch-agg.json")


if __name__ == "__main__":
    main()
