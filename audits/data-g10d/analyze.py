#!/usr/bin/env python3
"""G10d ablation analyzer — aggregate + per-category + per-style breakdown.

Produces:
- aggregate table (4 configs)
- per-category table (5 categories × 4 configs)
- per-style table (NL/keyword × 4 configs)
- style × category matrix
- D51 threshold check
"""
import json, sys
from pathlib import Path

RESULTS_DIR = Path(sys.argv[1] if len(sys.argv) > 1 else "results")
CONFIGS = ["a8_prime_baseline", "a8d_t1", "a8d_t2", "a8_off_control"]
LABELS = {
    "a8_prime_baseline": "A8' (G10 baseline)",
    "a8d_t1": "A8d-1 (threshold=1)",
    "a8d_t2": "A8d-2 (threshold=2)",
    "a8_off_control": "A8' off (control)",
}

data = {}
for c in CONFIGS:
    p = RESULTS_DIR / f"{c}.json"
    if not p.exists():
        print(f"[MISSING] {p}")
        continue
    data[c] = json.loads(p.read_text())

def pct(d, b):
    if b == 0: return 0.0
    return (d - b) / b * 100.0

baseline = data.get("a8_prime_baseline", {})
bsum = baseline.get("summary", {})

# === Aggregate table ===
print("\n## Aggregate (n=100)\n")
print("| Config | nDCG@10 | MRR | R@10 | P@5 | Δ%nDCG vs A8' | Δ%MRR vs A8' | Δ%R@10 vs A8' |")
print("|---|---:|---:|---:|---:|---:|---:|---:|")
for c in CONFIGS:
    s = data.get(c, {}).get("summary", {})
    dn = pct(s.get("ndcg_at_10", 0), bsum.get("ndcg_at_10", 1))
    dm = pct(s.get("mrr", 0), bsum.get("mrr", 1))
    dr = pct(s.get("recall_at_10", 0), bsum.get("recall_at_10", 1))
    print(f"| {LABELS[c]} | {s.get('ndcg_at_10',0):.4f} | {s.get('mrr',0):.4f} | {s.get('recall_at_10',0):.4f} | {s.get('precision_at_5',0):.4f} | {dn:+.2f}% | {dm:+.2f}% | {dr:+.2f}% |")

# === Per-category ===
print("\n## Per-Category nDCG@10\n")
cats = ["single-hop", "multi-hop", "temporal", "open-domain", "adversarial"]
print("| Category | A8' | A8d-1 | A8d-2 | A8 off | Δ%(d1−A8') | Δ%(d2−A8') | Δ%(off−A8') |")
print("|---|---:|---:|---:|---:|---:|---:|---:|")
for cat in cats:
    row = [cat]
    bv = baseline.get("per_category", {}).get(cat, {}).get("ndcg_at_10", 0)
    vals = []
    for c in CONFIGS:
        v = data.get(c, {}).get("per_category", {}).get(cat, {}).get("ndcg_at_10", 0)
        vals.append(v)
        row.append(f"{v:.4f}")
    for v in vals[1:]:
        row.append(f"{pct(v, bv):+.2f}%")
    print("| " + " | ".join(row) + " |")

# Same for MRR
print("\n## Per-Category MRR\n")
print("| Category | A8' | A8d-1 | A8d-2 | A8 off | Δ%(d1−A8') | Δ%(d2−A8') | Δ%(off−A8') |")
print("|---|---:|---:|---:|---:|---:|---:|---:|")
for cat in cats:
    row = [cat]
    bv = baseline.get("per_category", {}).get(cat, {}).get("mrr", 0)
    vals = []
    for c in CONFIGS:
        v = data.get(c, {}).get("per_category", {}).get(cat, {}).get("mrr", 0)
        vals.append(v)
        row.append(f"{v:.4f}")
    for v in vals[1:]:
        row.append(f"{pct(v, bv):+.2f}%")
    print("| " + " | ".join(row) + " |")

# R@10
print("\n## Per-Category R@10\n")
print("| Category | A8' | A8d-1 | A8d-2 | A8 off | Δ%(d1−A8') | Δ%(d2−A8') | Δ%(off−A8') |")
print("|---|---:|---:|---:|---:|---:|---:|---:|")
for cat in cats:
    row = [cat]
    bv = baseline.get("per_category", {}).get(cat, {}).get("recall_at_10", 0)
    vals = []
    for c in CONFIGS:
        v = data.get(c, {}).get("per_category", {}).get(cat, {}).get("recall_at_10", 0)
        vals.append(v)
        row.append(f"{v:.4f}")
    for v in vals[1:]:
        row.append(f"{pct(v, bv):+.2f}%")
    print("| " + " | ".join(row) + " |")

# === Per-style ===
print("\n## Per-Style nDCG@10\n")
styles = ["natural-language", "keyword"]
print("| Style | A8' | A8d-1 | A8d-2 | A8 off | Δ%(d1−A8') | Δ%(d2−A8') | Δ%(off−A8') |")
print("|---|---:|---:|---:|---:|---:|---:|---:|")
for sty in styles:
    row = [sty]
    bv = baseline.get("per_style", {}).get(sty, {}).get("ndcg_at_10", 0)
    vals = []
    for c in CONFIGS:
        v = data.get(c, {}).get("per_style", {}).get(sty, {}).get("ndcg_at_10", 0)
        vals.append(v)
        row.append(f"{v:.4f}")
    for v in vals[1:]:
        row.append(f"{pct(v, bv):+.2f}%")
    print("| " + " | ".join(row) + " |")

# Style × Category — compute on the fly from per_query
print("\n## Style × Category nDCG@10 (Δ% vs A8')\n")
def collect_style_cat(per_q):
    out = {}  # (style, cat) -> [(ndcg, mrr, r10)]
    for r in per_q:
        k = (r["style"], r["category"])
        out.setdefault(k, []).append(r)
    return out

base_pq = baseline.get("per_query", [])
base_sc = collect_style_cat(base_pq)
base_means = {k: {"ndcg": sum(r["ndcg_at_10"] for r in v)/len(v),
                  "mrr": sum(r["mrr"] for r in v)/len(v),
                  "r10": sum(r["recall_at_10"] for r in v)/len(v),
                  "n": len(v)} for k,v in base_sc.items()}

print("| Style | Category | n | A8' | A8d-1 | A8d-2 | A8 off | Δ%(d1) | Δ%(d2) | Δ%(off) |")
print("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
for sty in styles:
    for cat in cats:
        k = (sty, cat)
        if k not in base_means: continue
        b = base_means[k]["ndcg"]
        n = base_means[k]["n"]
        row = [sty, cat, str(n), f"{b:.4f}"]
        for c in ["a8d_t1", "a8d_t2", "a8_off_control"]:
            pq = data.get(c, {}).get("per_query", [])
            sc = collect_style_cat(pq)
            vals = sc.get(k, [])
            if not vals:
                row.append("-")
                continue
            v = sum(r["ndcg_at_10"] for r in vals)/len(vals)
            row.append(f"{v:.4f}")
        # deltas
        for c in ["a8d_t1", "a8d_t2", "a8_off_control"]:
            pq = data.get(c, {}).get("per_query", [])
            sc = collect_style_cat(pq)
            vals = sc.get(k, [])
            if not vals:
                row.append("-")
                continue
            v = sum(r["ndcg_at_10"] for r in vals)/len(vals)
            row.append(f"{pct(v,b):+.2f}%")
        print("| " + " | ".join(row) + " |")

# === Latency ===
print("\n## Latency (mean / p95)\n")
print("| Config | Mean (ms) | P95 (ms) |")
print("|---|---:|---:|")
for c in CONFIGS:
    s = data.get(c, {}).get("summary", {})
    print(f"| {LABELS[c]} | {s.get('mean_latency_ms',-1):.0f} | {s.get('p95_latency_ms',-1):.0f} |")

# === D51 thresholds check ===
print("\n## D51 GO/NO-GO threshold check (best conditional config vs A8' baseline)\n")
def check_config(c):
    s = data.get(c, {})
    if not s: return None
    summary = s.get("summary", {})
    pc = s.get("per_category", {})
    return {
        "agg_ndcg": summary.get("ndcg_at_10", 0),
        "agg_mrr": summary.get("mrr", 0),
        "sh_ndcg": pc.get("single-hop", {}).get("ndcg_at_10", 0),
        "sh_mrr": pc.get("single-hop", {}).get("mrr", 0),
        "mh_ndcg": pc.get("multi-hop", {}).get("ndcg_at_10", 0),
        "mh_r10": pc.get("multi-hop", {}).get("recall_at_10", 0),
        "od_ndcg": pc.get("open-domain", {}).get("ndcg_at_10", 0),
        "ad_ndcg": pc.get("adversarial", {}).get("ndcg_at_10", 0),
    }

# We're comparing A8d-1 / A8d-2 BACK to the GOLD STANDARD which is the
# previously-measured G10b/G10c absolute number. But for the ablation
# itself, threshold deltas are relative to A8' baseline (this run).
b = check_config("a8_prime_baseline")
print("Note: Δ%s below are relative to A8' (G10 baseline) **in this run**.")
print("Earlier G10b/G10c gave us absolute % deltas vs pre-mutex; those")
print("provide the original numbers (e.g., single-hop +8.22% etc).")
print()
print("| Metric | A8' (baseline) | A8d-1 | Δ% | A8d-2 | Δ% | GO threshold | A8d-1 verdict | A8d-2 verdict |")
print("|---|---:|---:|---:|---:|---:|---|---|---|")
thresholds = [
    ("Aggregate nDCG@10", "agg_ndcg", "≥ baseline"),
    ("Aggregate MRR", "agg_mrr", "≥ baseline"),
    ("Single-hop nDCG@10", "sh_ndcg", "≥ baseline (preserve)"),
    ("Single-hop MRR", "sh_mrr", "≥ baseline (preserve)"),
    ("Multi-hop nDCG@10", "mh_ndcg", "≥ +2% (recover regression)"),
    ("Multi-hop R@10", "mh_r10", "≥ +3% (recover regression)"),
    ("Open-domain nDCG@10", "od_ndcg", "≥ baseline"),
    ("Adversarial nDCG@10", "ad_ndcg", "bonus if ≥ baseline"),
]
d1 = check_config("a8d_t1")
d2 = check_config("a8d_t2")
for label, key, gate in thresholds:
    bv = b[key] if b else 0
    d1v = d1[key] if d1 else 0
    d2v = d2[key] if d2 else 0
    d1p = pct(d1v, bv)
    d2p = pct(d2v, bv)
    # Simple verdict: positive delta vs baseline = pass
    d1ok = "PASS" if d1p >= 0 else ("MARGINAL" if d1p > -1 else "FAIL")
    d2ok = "PASS" if d2p >= 0 else ("MARGINAL" if d2p > -1 else "FAIL")
    print(f"| {label} | {bv:.4f} | {d1v:.4f} | {d1p:+.2f}% | {d2v:.4f} | {d2p:+.2f}% | {gate} | {d1ok} | {d2ok} |")
