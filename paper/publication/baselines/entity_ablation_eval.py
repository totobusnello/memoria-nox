#!/usr/bin/env python3
"""Entity-flavored ablation harness — variant of locomo_ablation_eval.py that
uses the synthetic entity-flavored corpus + queries (entity-eval-2026-05-19)
instead of LoCoMo conversational data.

WHY: standard LoCoMo eval shows the boost stack (section_boost, BOOST_TYPES,
source_type_boost, tier_boost, pain·recency salience) contributes +0.0% nDCG
because LoCoMo chunks have no entity metadata for boosts to act on (Ablation F
PR #139 confirmed). This harness measures feature contribution on a corpus
that DOES carry those attributes, so the boost layer can demonstrate signal.

DOWNSTREAM ORCHESTRATION (G3 work):
  1. Ingest corpus.jsonl into the nox-mem database with full metadata
     preserved (section/chunk_type/pain/source_date/source_type/tier/importance)
  2. For each ablation config, set the corresponding NOX_* env vars and
     restart nox-mem-api
  3. Invoke this script with --label <config> --out results/<config>.json
  4. Compare per-config nDCG@10 / Recall@10 / MRR / Precision@5 deltas

ABLATION MATRIX (mirrors locomo_ablation_eval but tuned for entity eval):
  baseline                  — all features on
  dense_only                — disable BM25 (FTS5 lexical layer)
  no_expansion              — disable query expansion
  no_pool                   — semantic pool size = 0
  no_boosts                 — NOX_DISABLE_BOOSTS=1 (kill section/type/tier/source_type)
  no_salience               — NOX_SALIENCE_MODE=off
  no_section_boost          — section_boost ablated only (keep others)
  full_prod                 — production-path config

THIS SCRIPT DOES NOT RUN THE ABLATIONS. It is the eval driver — the shell
orchestrator (separate G3 work) flips env vars and restarts the API between
calls.

USAGE
-----
  # Smoke test against locally-running API (n=5):
  python3 entity_ablation_eval.py --label smoke --n 5 \\
      --out results/entity_ablation_smoke.json

  # Full run (n=100):
  python3 entity_ablation_eval.py --label baseline \\
      --out results/entity_ablation_baseline.json \\
      --toggles NOX_DISABLE_BOOSTS=0,NOX_SALIENCE_MODE=shadow

  # Offline scoring (no API — just sanity-check the fixture file):
  python3 entity_ablation_eval.py --label fixture-self-check --offline \\
      --out results/entity_self_check.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

# ────────────────────────────────────────────────────────────────────────────
# Defaults
# ────────────────────────────────────────────────────────────────────────────

DEFAULT_FIXTURE_DIR = Path("paper/publication/data/entity-eval-2026-05-19")
DEFAULT_ENDPOINT = "http://127.0.0.1:18803/api/search"

# ────────────────────────────────────────────────────────────────────────────
# SAFETY GUARD — fail-closed DB isolation check (postmortem 2026-05-19)
# ────────────────────────────────────────────────────────────────────────────
# Root cause: G3 orchestrator ran `nox-mem ingest` without NOX_DB_PATH
# explicitly set to an isolated eval DB, causing 500 eval chunks to land in
# the production nox-mem.db (68k+ chunks wiped, restore required from snapshot).
#
# This guard fires at *import time* so the error surfaces immediately — before
# any subprocess or API call is made — and blocks the run if the resolved API
# endpoint is the production endpoint (port 18802) or if NOX_EVAL_DB_PATH is
# not explicitly set when the script is not in --offline mode.
#
# The check is intentionally conservative:
#   - Port 18802 = prod; 18803 = eval (per CLAUDE.md §4).
#   - NOX_EVAL_DB_PATH must be set AND must NOT resolve to the production path
#     (*/tools/nox-mem/nox-mem.db) when running non-offline eval.
#
# To bypass in a legitimate isolated test environment set:
#   NOX_EVAL_ISOLATION_OVERRIDE=1  (explicit, auditable)

_PROD_PORT_PATTERN = re.compile(r":18802\b")
_PROD_DB_PATTERN = re.compile(r"/tools/nox-mem/nox-mem\.db$")


def _check_eval_isolation(endpoint: str, offline: bool) -> None:
    """Abort if the eval harness appears to be targeting prod resources.

    Called from main() before any network/ingest activity.

    Args:
        endpoint: The /api/search endpoint URL in use.
        offline: True when --offline flag is set (no API calls made).

    Raises:
        SystemExit: With a descriptive error message if isolation is violated.
    """
    if offline:
        return  # offline mode makes no network calls and no ingest

    override = os.environ.get("NOX_EVAL_ISOLATION_OVERRIDE", "").strip()
    if override == "1":
        print(
            "[entity-ablation] WARNING: NOX_EVAL_ISOLATION_OVERRIDE=1 — "
            "DB isolation check bypassed. Ensure you are running against an "
            "isolated eval DB, NOT the production nox-mem.db.",
            file=sys.stderr,
        )
        return

    errors: list[str] = []

    # Check 1: endpoint must not be the production port
    if _PROD_PORT_PATTERN.search(endpoint):
        errors.append(
            f"Endpoint '{endpoint}' targets port 18802 (production). "
            "Entity-flavored eval MUST run against port 18803 (isolated eval API). "
            "Start a second nox-mem-api instance with NOX_DB_PATH=/tmp/<eval>.db "
            "NOX_API_PORT=18803 before invoking this harness."
        )

    # Check 2: NOX_EVAL_DB_PATH must be explicitly set
    eval_db = os.environ.get("NOX_EVAL_DB_PATH", "").strip()
    if not eval_db:
        errors.append(
            "NOX_EVAL_DB_PATH is not set. "
            "The G3 orchestrator MUST export NOX_EVAL_DB_PATH=/tmp/<eval>.db "
            "so the ingest step targets the isolated DB. "
            "Without this, `nox-mem ingest` falls back to OPENCLAW_WORKSPACE "
            "and writes eval chunks into the production nox-mem.db. "
            "(This was the root cause of the 2026-05-19 wipe incident.)"
        )
    elif _PROD_DB_PATTERN.search(eval_db):
        errors.append(
            f"NOX_EVAL_DB_PATH='{eval_db}' resolves to the production database. "
            "Set it to an isolated path under /tmp/ or /root/.openclaw/eval/."
        )

    if errors:
        print("\n[entity-ablation] FATAL — DB ISOLATION GUARD TRIGGERED:", file=sys.stderr)
        for i, e in enumerate(errors, 1):
            print(f"  [{i}] {e}", file=sys.stderr)
        print(
            "\nTo bypass (only if you have verified isolation manually): "
            "export NOX_EVAL_ISOLATION_OVERRIDE=1",
            file=sys.stderr,
        )
        sys.exit(1)
DEFAULT_N = 100
TOP_K = 20  # retrieve top-20, score top-10

CATEGORIES = ["single-hop", "multi-hop", "temporal", "open-domain", "adversarial"]

# ────────────────────────────────────────────────────────────────────────────
# Fixture loading
# ────────────────────────────────────────────────────────────────────────────

def load_fixtures(fixture_dir: Path) -> tuple[list[dict], list[dict]]:
    corpus_path = fixture_dir / "corpus.jsonl"
    queries_path = fixture_dir / "queries.jsonl"
    if not corpus_path.exists():
        raise FileNotFoundError(f"corpus not found: {corpus_path}")
    if not queries_path.exists():
        raise FileNotFoundError(f"queries not found: {queries_path}")
    corpus = [json.loads(ln) for ln in corpus_path.read_text().splitlines() if ln.strip()]
    queries = [json.loads(ln) for ln in queries_path.read_text().splitlines() if ln.strip()]
    return corpus, queries


# ────────────────────────────────────────────────────────────────────────────
# Retrieval — API path
# ────────────────────────────────────────────────────────────────────────────

def extract_retrieved_ids(hits: list[dict]) -> list[str]:
    """Extract chunk IDs from /api/search results.

    Production /api/search returns hits with `chunk_text` (which starts with
    `chunk_id: "..."` per the generator's text shaper) plus an optional
    `id` field.
    """
    import re
    pattern = re.compile(r'chunk_id:\s*"([^"]+)"')
    out: list[str] = []
    for h in hits:
        # Prefer an explicit id field if present
        cid = h.get("id") or h.get("chunk_id")
        if not cid:
            # Fallback — extract from chunk_text
            text = h.get("chunk_text") or h.get("text") or ""
            m = pattern.search(text)
            if m:
                cid = m.group(1)
        if cid:
            out.append(cid)
    return out


def search_via_api(endpoint: str, query: str, top_k: int = TOP_K, timeout: float = 30.0) -> tuple[list[str], float]:
    body = json.dumps({"q": query, "limit": top_k}).encode("utf-8")
    req = urllib.request.Request(
        endpoint, data=body,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
        return [], -1.0
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    hits = data if isinstance(data, list) else data.get("results", data.get("hits", []))
    return extract_retrieved_ids(hits), elapsed_ms


# ────────────────────────────────────────────────────────────────────────────
# Offline scoring — for fixture self-check (no API)
# ────────────────────────────────────────────────────────────────────────────

def offline_retrieve(query: dict, corpus: list[dict], top_k: int = TOP_K) -> list[str]:
    """Trivial keyword-overlap retrieval that returns gold chunks first when
    they match, then fillers. Used only for --offline self-check to verify
    that the harness pipes scores correctly. NOT a production retrieval.
    """
    gold_set = set(query.get("gold_chunk_ids", []))
    q = query["query"].lower()
    q_terms = set(t for t in q.replace("?", " ").split() if len(t) > 3)

    def score(c: dict) -> float:
        text_lower = c["text"].lower()
        overlap = sum(1 for t in q_terms if t in text_lower)
        gold_bump = 100.0 if c["id"] in gold_set else 0.0
        return overlap + gold_bump

    ranked = sorted(corpus, key=score, reverse=True)
    return [c["id"] for c in ranked[:top_k]]


# ────────────────────────────────────────────────────────────────────────────
# Metrics
# ────────────────────────────────────────────────────────────────────────────

def _dcg(rel: list[int], k: int) -> float:
    return sum((2**r - 1) / math.log2(i + 2) for i, r in enumerate(rel[:k]))


def ndcg_at_k(retrieved: list[str], gold: set[str], k: int = 10) -> float:
    """Canonical formula (full-ideal IDCG)."""
    rel = [1 if r in gold else 0 for r in retrieved[:k]]
    dcg = _dcg(rel, k)
    ideal_hits = min(len(gold), k)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_hits))
    return dcg / idcg if idcg > 0 else 0.0


def mrr(retrieved: list[str], gold: set[str]) -> float:
    for i, r in enumerate(retrieved):
        if r in gold:
            return 1.0 / (i + 1)
    return 0.0


def recall_at_k(retrieved: list[str], gold: set[str], k: int = 10) -> float:
    if not gold:
        return 0.0
    hits = sum(1 for r in retrieved[:k] if r in gold)
    return hits / len(gold)


def precision_at_k(retrieved: list[str], gold: set[str], k: int = 5) -> float:
    if k == 0:
        return 0.0
    hits = sum(1 for r in retrieved[:k] if r in gold)
    return hits / k


# ────────────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────────────

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--label", required=True, help="ablation label, e.g. baseline / no_boosts")
    p.add_argument("--out", required=True, help="output JSON path")
    p.add_argument("--fixture-dir", type=Path, default=DEFAULT_FIXTURE_DIR)
    p.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    p.add_argument("--n", type=int, default=DEFAULT_N, help="subset size (head of query file)")
    p.add_argument("--toggles", default="", help="comma-separated key=val toggles to record in summary (env vars are set on the API process by the orchestrator, not by this script)")
    p.add_argument("--offline", action="store_true", help="bypass API; use keyword-overlap retrieval (fixture self-check only)")
    args = p.parse_args()

    # Fail-closed isolation guard (postmortem 2026-05-19)
    _check_eval_isolation(args.endpoint, args.offline)

    corpus, queries = load_fixtures(args.fixture_dir)
    queries = queries[: args.n]
    print(f"[entity-ablation:{args.label}] fixture: {len(corpus)} chunks, evaluating {len(queries)} queries")

    toggles_dict: dict[str, str] = {}
    for kv in args.toggles.split(","):
        kv = kv.strip()
        if "=" in kv:
            k, v = kv.split("=", 1)
            toggles_dict[k.strip()] = v.strip()

    per_q = []
    t0 = time.perf_counter()
    for i, q in enumerate(queries, 1):
        if args.offline:
            retrieved_ids = offline_retrieve(q, corpus, top_k=TOP_K)
            ms = 0.0
        else:
            retrieved_ids, ms = search_via_api(args.endpoint, q["query"], top_k=TOP_K)
        gold = set(q["gold_chunk_ids"])
        rec = {
            "qid":              q["qid"],
            "category":         q["category"],
            "style":            q["style"],
            "query":            q["query"],
            "gold_chunk_ids":   q["gold_chunk_ids"],
            "retrieved_chunk_ids": retrieved_ids[:TOP_K],
            "retrieval_ms":     round(ms, 2),
            "ndcg_at_10":       ndcg_at_k(retrieved_ids, gold, 10),
            "mrr":              mrr(retrieved_ids, gold),
            "recall_at_10":     recall_at_k(retrieved_ids, gold, 10),
            "precision_at_5":   precision_at_k(retrieved_ids, gold, 5),
        }
        per_q.append(rec)
        if i % 20 == 0:
            elapsed = time.perf_counter() - t0
            print(f"[entity-ablation:{args.label}] {i}/{len(queries)} ({elapsed:.1f}s)")

    def agg(metric: str) -> float:
        vals = [r[metric] for r in per_q]
        return sum(vals) / len(vals) if vals else 0.0

    per_cat = {}
    per_style = {"natural-language": [], "keyword": []}
    for cat in CATEGORIES:
        cat_recs = [r for r in per_q if r["category"] == cat]
        if cat_recs:
            per_cat[cat] = {
                "n":             len(cat_recs),
                "ndcg_at_10":    sum(r["ndcg_at_10"] for r in cat_recs) / len(cat_recs),
                "mrr":           sum(r["mrr"] for r in cat_recs) / len(cat_recs),
                "recall_at_10":  sum(r["recall_at_10"] for r in cat_recs) / len(cat_recs),
                "precision_at_5":sum(r["precision_at_5"] for r in cat_recs) / len(cat_recs),
            }
    for r in per_q:
        per_style.setdefault(r["style"], []).append(r)
    per_style_agg = {}
    for sty, recs in per_style.items():
        if recs:
            per_style_agg[sty] = {
                "n":             len(recs),
                "ndcg_at_10":    sum(r["ndcg_at_10"] for r in recs) / len(recs),
                "mrr":           sum(r["mrr"] for r in recs) / len(recs),
                "recall_at_10":  sum(r["recall_at_10"] for r in recs) / len(recs),
                "precision_at_5":sum(r["precision_at_5"] for r in recs) / len(recs),
            }

    summary = {
        "label":          args.label,
        "toggles":        toggles_dict,
        "n_queries":      len(per_q),
        "fixture_dir":    str(args.fixture_dir),
        "endpoint":       args.endpoint if not args.offline else "(offline)",
        "ndcg_at_10":     agg("ndcg_at_10"),
        "mrr":            agg("mrr"),
        "recall_at_10":   agg("recall_at_10"),
        "precision_at_5": agg("precision_at_5"),
        "mean_latency_ms": statistics.mean([r["retrieval_ms"] for r in per_q if r["retrieval_ms"] >= 0]) if not args.offline else 0,
        "p95_latency_ms":  sorted([r["retrieval_ms"] for r in per_q if r["retrieval_ms"] >= 0])[int(len(per_q) * 0.95)] if per_q and not args.offline else 0,
        "wallclock_s":     round(time.perf_counter() - t0, 2),
    }

    out = {
        "summary":      summary,
        "per_category": per_cat,
        "per_style":    per_style_agg,
        "per_query":    per_q,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(f"\n[entity-ablation:{args.label}] wrote {args.out}")
    print(f"{'='*72}")
    print(f"ABLATION {args.label} (n={summary['n_queries']})")
    print(f"toggles: {toggles_dict or '(default)'}")
    print(f"{'='*72}")
    print(f"nDCG@10        {summary['ndcg_at_10']:.4f}")
    print(f"MRR            {summary['mrr']:.4f}")
    print(f"Recall@10      {summary['recall_at_10']:.4f}")
    print(f"Precision@5    {summary['precision_at_5']:.4f}")
    if not args.offline:
        print(f"Mean latency   {summary['mean_latency_ms']:.0f}ms")
        print(f"P95 latency    {summary['p95_latency_ms']:.0f}ms")
    print(f"Wallclock      {summary['wallclock_s']:.1f}s")
    print(f"{'='*72}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
