#!/usr/bin/env python3
"""LOCOMO Hybrid retrieval evaluation (FTS5 + Gemini dense + RRF k=60).

Self-contained Python re-implementation of memoria-nox's hybrid retrieval
architecture, evaluated on the SAME stratified 100-query LOCOMO subset
used by `locomo_eval.py` (E04, seed=42).

⚠️  This script re-implements the *shape* of nox-mem's retrieval pipeline.
It is NOT a test of production code paths — it validates that the
FTS5 + dense + RRF approach yields uplift over FTS5-only on LOCOMO.

Components:
    1. FTS5 BM25  : reused from `locomo_eval.py` (same tokenizer, same SQLite)
    2. Dense      : Gemini `gemini-embedding-001` (3072d), cosine similarity
    3. Fusion     : RRF with k=60, top-10 after fusion

Usage:
    export GEMINI_API_KEY=...
    python3 locomo_hybrid_eval.py full   # download + index + embed + eval
    python3 locomo_hybrid_eval.py eval   # eval only (requires existing cache)

Output:
    /tmp/locomo-hybrid-eval.db         (turns + embeddings BLOB cache)
    paper/publication/results/locomo-hybrid-results.jsonl
    paper/publication/results/locomo-hybrid-vs-fts5-summary.md

Cost: ~$0.05-0.10 (~6k turn embeds + 100 query embeds, first run only).
Wall clock: 5-10 min first run, ~30 s subsequent runs (cached).

Reproducibility: seed=42, same subset as E04, same metrics functions.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
import statistics
import struct
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

# ── Reuse exact FTS5/index/sampling logic from E04 ──────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent))
from locomo_eval import (  # noqa: E402
    CACHE,
    CATEGORY_NAMES,
    SEED,
    SUBSET_PER_CATEGORY,
    build_index as build_fts5_index,
    download,
    fts5_escape,
    iter_turns,
    load_corpus,
    mrr,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    select_queries,
)

import numpy as np  # noqa: E402

try:
    import requests  # noqa: E402
except ImportError:
    print("[fatal] `requests` not installed. Run: pip install requests", file=sys.stderr)
    sys.exit(2)

# ── Hybrid-specific config ───────────────────────────────────────────────────
DB_PATH = Path("/tmp/locomo-hybrid-eval.db")     # separate DB (don't mutate E04)
RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"
RESULTS = RESULTS_DIR / "locomo-hybrid-results.jsonl"
SUMMARY = RESULTS_DIR / "locomo-hybrid-vs-fts5-summary.md"
FTS5_RESULTS = RESULTS_DIR / "locomo-fts5-baseline-results.jsonl"

GEMINI_MODEL = "gemini-embedding-001"
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:embedContent"
)
EMBED_DIM = 3072                  # matches production nox-mem
RRF_K = 60                        # matches production nox-mem
TOP_K_FTS = 20                    # candidate pool per system
TOP_K_DENSE = 20
TOP_K_FINAL = 10

BATCH_SLEEP = 0.05                # gentle pacing to dodge 429
MAX_RETRIES = 4


def check_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        print(
            "\n"
            "  ╭─────────────────────────────────────────────────────────────╮\n"
            "  │ GEMINI_API_KEY is not set.                                  │\n"
            "  │                                                             │\n"
            "  │ This evaluation requires Gemini embeddings to compute the   │\n"
            "  │ dense-retrieval branch of the hybrid pipeline.              │\n"
            "  │                                                             │\n"
            "  │ Fix:                                                        │\n"
            "  │     export GEMINI_API_KEY=AIza...                           │\n"
            "  │     python3 locomo_hybrid_eval.py full                      │\n"
            "  │                                                             │\n"
            "  │ Get a key: https://aistudio.google.com/app/apikey           │\n"
            "  │ Cost estimate for this run: < $0.10                         │\n"
            "  ╰─────────────────────────────────────────────────────────────╯\n",
            file=sys.stderr,
        )
        sys.exit(3)
    return key


# ── Embedding cache schema ──────────────────────────────────────────────────
def open_db() -> sqlite3.Connection:
    con = sqlite3.connect(str(DB_PATH))
    con.execute("PRAGMA journal_mode=WAL")
    return con


def init_db(corpus: list[dict]) -> int:
    if DB_PATH.exists():
        DB_PATH.unlink()
    con = open_db()
    con.execute(
        "CREATE TABLE turns ("
        " chunk_id TEXT PRIMARY KEY, sample_id TEXT, dia_id TEXT, "
        " text TEXT, embedding BLOB)"
    )
    con.execute(
        "CREATE VIRTUAL TABLE turns_fts USING fts5("
        " text, content='turns', content_rowid='rowid', "
        " tokenize='unicode61 remove_diacritics 2')"
    )
    rows = []
    for full_id, dia_id, text in iter_turns(corpus):
        sample_id = full_id.split("::", 1)[0]
        rows.append((full_id, sample_id, dia_id, text))
    con.executemany(
        "INSERT INTO turns(chunk_id,sample_id,dia_id,text) VALUES(?,?,?,?)", rows
    )
    con.execute("INSERT INTO turns_fts(rowid,text) SELECT rowid,text FROM turns")
    con.commit()
    n = con.execute("SELECT COUNT(*) FROM turns").fetchone()[0]
    con.close()
    print(f"[index] {n:,} turns in {DB_PATH}", file=sys.stderr)
    return n


# ── Gemini embedding (single-call API; batch=N not supported on free tier) ───
def embed_one(text: str, api_key: str, *, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
    """Call Gemini embedContent once. Retries on 429/5xx with exponential backoff."""
    body = {
        "model": f"models/{GEMINI_MODEL}",
        "content": {"parts": [{"text": text}]},
        "taskType": task_type,
        "outputDimensionality": EMBED_DIM,
    }
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    delay = 1.0
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.post(GEMINI_URL, json=body, headers=headers, timeout=30)
        except requests.RequestException as exc:
            if attempt == MAX_RETRIES:
                raise
            print(f"[embed retry {attempt}] {exc}", file=sys.stderr)
            time.sleep(delay)
            delay *= 2
            continue
        if r.status_code == 200:
            j = r.json()
            vals = j.get("embedding", {}).get("values") or j.get("embedding", {}).get("value")
            if not vals or len(vals) != EMBED_DIM:
                raise RuntimeError(f"embedding shape mismatch: got {len(vals) if vals else 0}, want {EMBED_DIM}")
            return vals
        if r.status_code in (429, 500, 502, 503, 504):
            if attempt == MAX_RETRIES:
                raise RuntimeError(f"Gemini API exhausted retries: {r.status_code} {r.text[:200]}")
            print(f"[embed retry {attempt}] HTTP {r.status_code}; backoff {delay}s", file=sys.stderr)
            time.sleep(delay)
            delay *= 2
            continue
        raise RuntimeError(f"Gemini API error: {r.status_code} {r.text[:300]}")
    raise RuntimeError("unreachable")


def pack_vec(v: list[float]) -> bytes:
    arr = np.asarray(v, dtype=np.float32)
    # L2-normalise once at write time so cosine == dot product later
    n = np.linalg.norm(arr)
    if n > 0:
        arr = arr / n
    return arr.tobytes()


def unpack_vec(b: bytes) -> np.ndarray:
    return np.frombuffer(b, dtype=np.float32)


def embed_corpus(api_key: str) -> int:
    con = open_db()
    rows = con.execute(
        "SELECT chunk_id, text FROM turns WHERE embedding IS NULL"
    ).fetchall()
    if not rows:
        cnt = con.execute("SELECT COUNT(*) FROM turns WHERE embedding IS NOT NULL").fetchone()[0]
        print(f"[embed] all {cnt:,} turns already embedded", file=sys.stderr)
        con.close()
        return cnt
    print(f"[embed] embedding {len(rows):,} turns via {GEMINI_MODEL}…", file=sys.stderr)
    t0 = time.time()
    done = 0
    for chunk_id, text in rows:
        v = embed_one(text, api_key, task_type="RETRIEVAL_DOCUMENT")
        con.execute("UPDATE turns SET embedding = ? WHERE chunk_id = ?", (pack_vec(v), chunk_id))
        done += 1
        if done % 50 == 0:
            con.commit()
            elapsed = time.time() - t0
            rate = done / elapsed if elapsed else 0
            eta = (len(rows) - done) / rate if rate else 0
            print(f"[embed] {done}/{len(rows)} ({rate:.1f}/s, eta {eta:.0f}s)", file=sys.stderr)
        if BATCH_SLEEP:
            time.sleep(BATCH_SLEEP)
    con.commit()
    con.close()
    print(f"[embed] done {done} turns in {time.time()-t0:.1f}s", file=sys.stderr)
    return done


# ── Hybrid retrieval ─────────────────────────────────────────────────────────
def load_dense_matrix(con: sqlite3.Connection) -> tuple[list[str], np.ndarray]:
    rows = con.execute(
        "SELECT chunk_id, embedding FROM turns WHERE embedding IS NOT NULL"
    ).fetchall()
    ids = [r[0] for r in rows]
    mat = np.stack([unpack_vec(r[1]) for r in rows]) if rows else np.zeros((0, EMBED_DIM), dtype=np.float32)
    return ids, mat


def search_fts5(con: sqlite3.Connection, query: str, k: int = TOP_K_FTS) -> list[str]:
    fq = fts5_escape(query)
    try:
        rows = con.execute(
            "SELECT t.chunk_id FROM turns t JOIN turns_fts f ON f.rowid=t.rowid "
            "WHERE turns_fts MATCH ? ORDER BY bm25(turns_fts) LIMIT ?",
            (fq, k),
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    return [r[0] for r in rows]


def search_dense(
    query: str,
    api_key: str,
    ids: list[str],
    mat: np.ndarray,
    k: int = TOP_K_DENSE,
) -> list[str]:
    qv = np.asarray(embed_one(query, api_key, task_type="RETRIEVAL_QUERY"), dtype=np.float32)
    n = np.linalg.norm(qv)
    if n > 0:
        qv = qv / n
    sims = mat @ qv                              # cosine, already L2-normed
    if k >= len(sims):
        order = np.argsort(-sims)
    else:
        # partial argsort for speed on large corpora
        idx = np.argpartition(-sims, k)[:k]
        order = idx[np.argsort(-sims[idx])]
    return [ids[i] for i in order[:k]]


def rrf_fuse(rankings: list[list[str]], k: int = RRF_K, top: int = TOP_K_FINAL) -> list[str]:
    """Reciprocal-Rank Fusion. score(doc) = Σ 1/(k + rank_i)."""
    scores: dict[str, float] = defaultdict(float)
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking):
            scores[doc_id] += 1.0 / (k + rank + 1)   # rank is 0-indexed; +1 → 1-indexed
    fused = sorted(scores.items(), key=lambda kv: -kv[1])
    return [d for d, _ in fused[:top]]


# ── Eval driver ──────────────────────────────────────────────────────────────
def evaluate(queries: list[dict], api_key: str) -> dict[str, Any]:
    con = open_db()
    ids, mat = load_dense_matrix(con)
    if not ids:
        print("[fatal] no embeddings in DB — run `full` or `embed` first", file=sys.stderr)
        sys.exit(4)
    print(f"[eval] dense corpus: {len(ids):,} vectors × {mat.shape[1]}d", file=sys.stderr)

    per_query: list[dict] = []
    t0 = time.time()
    for i, q in enumerate(queries, 1):
        fts_top = search_fts5(con, q["question"], k=TOP_K_FTS)
        dense_top = search_dense(q["question"], api_key, ids, mat, k=TOP_K_DENSE)
        fused = rrf_fuse([fts_top, dense_top], k=RRF_K, top=TOP_K_FINAL)
        gold = set(q["gold_chunk_ids"])
        per_query.append(
            {
                "query": q["question"][:120],
                "category": q["category"],
                "category_name": q["category_name"],
                "ndcg_at_10": ndcg_at_k(fused, gold, 10),
                "mrr": mrr(fused, gold),
                "recall_at_10": recall_at_k(fused, gold, 10),
                "precision_at_5": precision_at_k(fused, gold, 5),
                "n_gold": len(gold),
                "n_retrieved": len(fused),
            }
        )
        if i % 10 == 0:
            print(f"[eval] {i}/{len(queries)} ({(time.time()-t0):.1f}s)", file=sys.stderr)
        if BATCH_SLEEP:
            time.sleep(BATCH_SLEEP)
    con.close()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in per_query) + "\n")

    def mean(xs: list[float]) -> float:
        return sum(xs) / len(xs) if xs else 0.0

    aggregate = {
        "system": "hybrid_fts5_gemini_rrf_locomo",
        "n_queries": len(per_query),
        "rrf_k": RRF_K,
        "embedding_model": GEMINI_MODEL,
        "embedding_dim": EMBED_DIM,
        "ndcg_at_10": mean([r["ndcg_at_10"] for r in per_query]),
        "mrr": mean([r["mrr"] for r in per_query]),
        "recall_at_10": mean([r["recall_at_10"] for r in per_query]),
        "precision_at_5": mean([r["precision_at_5"] for r in per_query]),
    }
    by_cat: dict[int, list[dict]] = defaultdict(list)
    for r in per_query:
        by_cat[r["category"]].append(r)
    per_category: list[dict] = []
    for cat in sorted(by_cat):
        rs = by_cat[cat]
        per_category.append(
            {
                "category": cat,
                "category_name": CATEGORY_NAMES[cat],
                "n": len(rs),
                "ndcg_at_10": mean([r["ndcg_at_10"] for r in rs]),
                "mrr": mean([r["mrr"] for r in rs]),
                "recall_at_10": mean([r["recall_at_10"] for r in rs]),
                "precision_at_5": mean([r["precision_at_5"] for r in rs]),
            }
        )
    return {"aggregate": aggregate, "per_category": per_category, "per_query": per_query}


# ── Comparison report (FTS5 baseline vs Hybrid) ──────────────────────────────
def load_fts5_results() -> list[dict] | None:
    if not FTS5_RESULTS.exists():
        return None
    out = []
    for line in FTS5_RESULTS.read_text().splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def ci95(xs: list[float]) -> tuple[float, float, float]:
    """Mean + 95% CI half-width via normal approx (n=100 large enough)."""
    if not xs:
        return 0.0, 0.0, 0.0
    m = statistics.fmean(xs)
    if len(xs) < 2:
        return m, m, m
    sd = statistics.stdev(xs)
    se = sd / math.sqrt(len(xs))
    h = 1.96 * se
    return m, m - h, m + h


def write_summary(hybrid_results: dict, fts5_per_query: list[dict] | None) -> None:
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    agg = hybrid_results["aggregate"]
    per_cat_h = {c["category"]: c for c in hybrid_results["per_category"]}
    per_q_h = hybrid_results["per_query"]

    lines: list[str] = []
    lines.append("# E04 LOCOMO — Hybrid (FTS5 + Gemini + RRF) vs FTS5 baseline\n")
    lines.append(f"**Run date:** {time.strftime('%Y-%m-%d %H:%M %Z')}")
    lines.append(f"**Dataset:** snap-research/locomo (CC BY-NC 4.0), `data/locomo10.json`")
    lines.append(f"**Subset:** n=100 stratified (20 per category × 5), seed={SEED}")
    lines.append(f"**Embedding model:** `{GEMINI_MODEL}` ({EMBED_DIM}d, L2-normed)")
    lines.append(f"**Fusion:** RRF with k={RRF_K}, top-{TOP_K_FINAL} after fusion")
    lines.append(f"**Candidates per branch:** FTS5 top-{TOP_K_FTS}, dense top-{TOP_K_DENSE}\n")

    lines.append("## ⚠️ Caveats (read before citing)\n")
    lines.append(
        "1. **Python re-implementation, NOT production code path.** This script reproduces the *architectural shape* of memoria-nox's hybrid retrieval (FTS5 BM25 + Gemini 3072d dense + RRF k=60). It does NOT execute nox-mem's production TypeScript pipeline. Production-path validation requires running the same queries through `nox-mem search` against an isolated DB — separate work item."
    )
    lines.append(
        "2. **Sample n=100, not full 1986 questions.** Same stratified seed=42 subset as E04 FTS5 baseline, enabling apples-to-apples comparison."
    )
    lines.append(
        "3. **Embedding cache local to this script** (`/tmp/locomo-hybrid-eval.db`). Production nox-mem reuses embeddings across queries via `vec_chunks` table — same effective behaviour for retrieval, different persistence."
    )
    lines.append(
        "4. **Gold relevance is binary** (chunk-id match against query evidence list). LoCoMo does not provide graded judgments.\n"
    )

    # Aggregate comparison
    fts5_ndcg, fts5_mrr, fts5_rec, fts5_prec = (None,) * 4
    fts5_ndcg_xs = []
    if fts5_per_query is not None:
        fts5_ndcg = statistics.fmean(r["ndcg_at_10"] for r in fts5_per_query)
        fts5_mrr = statistics.fmean(r["mrr"] for r in fts5_per_query)
        fts5_rec = statistics.fmean(r["recall_at_10"] for r in fts5_per_query)
        fts5_prec = statistics.fmean(r["precision_at_5"] for r in fts5_per_query)
        fts5_ndcg_xs = [r["ndcg_at_10"] for r in fts5_per_query]

    h_ndcg_xs = [r["ndcg_at_10"] for r in per_q_h]
    h_m, h_lo, h_hi = ci95(h_ndcg_xs)
    f_m, f_lo, f_hi = ci95(fts5_ndcg_xs) if fts5_ndcg_xs else (None, None, None)

    lines.append("## Aggregate metrics (n=100)\n")
    lines.append("| Metric | FTS5 baseline (E04) | **Hybrid (this run)** | Δ absolute | Δ relative |")
    lines.append("|---|---|---|---|---|")
    def row(name: str, f: float | None, h: float) -> str:
        if f is None:
            return f"| {name} | — | **{h:.4f}** | — | — |"
        delta_abs = h - f
        delta_rel = (delta_abs / f * 100) if f else float("inf")
        return f"| {name} | {f:.4f} | **{h:.4f}** | {delta_abs:+.4f} | {delta_rel:+.1f}% |"
    lines.append(row("nDCG@10", fts5_ndcg, agg["ndcg_at_10"]))
    lines.append(row("MRR", fts5_mrr, agg["mrr"]))
    lines.append(row("Recall@10", fts5_rec, agg["recall_at_10"]))
    lines.append(row("Precision@5", fts5_prec, agg["precision_at_5"]))
    lines.append("")

    lines.append("### 95% CI on nDCG@10 (normal approx, n=100)\n")
    if f_m is not None:
        lines.append(f"- FTS5 baseline: **{f_m:.4f}** [{f_lo:.4f}, {f_hi:.4f}]")
    lines.append(f"- Hybrid:        **{h_m:.4f}** [{h_lo:.4f}, {h_hi:.4f}]\n")

    # Per-category breakdown
    lines.append("## Per-category nDCG@10 (n=20 per cat)\n")
    lines.append("| Category | FTS5 | Hybrid | Δ abs | Δ % |")
    lines.append("|---|---|---|---|---|")
    fts5_by_cat: dict[int, list[float]] = defaultdict(list)
    if fts5_per_query:
        for r in fts5_per_query:
            fts5_by_cat[r["category"]].append(r["ndcg_at_10"])
    for cat in sorted(per_cat_h):
        c = per_cat_h[cat]
        h = c["ndcg_at_10"]
        f = statistics.fmean(fts5_by_cat[cat]) if fts5_by_cat.get(cat) else None
        if f is None:
            lines.append(f"| {cat}. {c['category_name']} | — | **{h:.4f}** | — | — |")
        else:
            da = h - f
            dr = (da / f * 100) if f else float("inf")
            lines.append(f"| {cat}. {c['category_name']} | {f:.4f} | **{h:.4f}** | {da:+.4f} | {dr:+.1f}% |")
    lines.append("")

    # Per-category MRR + Recall (hybrid)
    lines.append("## Hybrid per-category — all metrics\n")
    lines.append("| Category | n | nDCG@10 | MRR | Recall@10 | Precision@5 |")
    lines.append("|---|---|---|---|---|---|")
    for cat in sorted(per_cat_h):
        c = per_cat_h[cat]
        lines.append(
            f"| {cat}. {c['category_name']} | {c['n']} | "
            f"{c['ndcg_at_10']:.4f} | {c['mrr']:.4f} | "
            f"{c['recall_at_10']:.4f} | {c['precision_at_5']:.4f} |"
        )
    lines.append("")

    # Methodology
    lines.append("## Methodology\n")
    lines.append("**FTS5 branch:** identical to E04 baseline — `unicode61 remove_diacritics 2`, BM25 ranking, OR-joined phrase tokens (`fts5_escape` reused via import), top-20 candidates.\n")
    lines.append("**Dense branch:** Gemini `gemini-embedding-001` with `outputDimensionality=3072`. Document embeddings use `taskType=RETRIEVAL_DOCUMENT`; query embeddings use `RETRIEVAL_QUERY`. Embeddings are L2-normed at write time so cosine = dot product. Top-20 by cosine similarity.\n")
    lines.append(f"**Fusion:** Reciprocal Rank Fusion (Cormack et al., 2009) with k={RRF_K}. Score per doc = Σ 1/(k + rank_i) across both rankings. Top-10 after fusion → fed to metric computation.\n")
    lines.append("**Metrics:** nDCG@10, MRR, Recall@10, Precision@5 — same functions as E04 (imported from `locomo_eval.py`).\n")

    lines.append("## Reproducibility\n")
    lines.append("```bash\nexport GEMINI_API_KEY=AIza...\ncd paper/publication/baselines\npython3 locomo_hybrid_eval.py full\n```\n")
    lines.append(f"Output: `{RESULTS.relative_to(RESULTS_DIR.parent.parent)}` (100 JSONL lines, same shape as FTS5 baseline).\n")

    SUMMARY.write_text("\n".join(lines))
    print(f"[summary] wrote {SUMMARY}", file=sys.stderr)


# ── Pretty stdout table ──────────────────────────────────────────────────────
def print_comparison(hybrid_results: dict, fts5_per_query: list[dict] | None) -> None:
    agg = hybrid_results["aggregate"]
    print("\n" + "=" * 72)
    print("LOCOMO n=100 — FTS5 baseline vs Hybrid (FTS5 + Gemini + RRF)")
    print("=" * 72)
    if fts5_per_query is None:
        print("(FTS5 baseline file not found — printing hybrid only)")
        print(f"  Hybrid nDCG@10 = {agg['ndcg_at_10']:.4f}")
        return
    f_ndcg = statistics.fmean(r["ndcg_at_10"] for r in fts5_per_query)
    f_mrr = statistics.fmean(r["mrr"] for r in fts5_per_query)
    f_rec = statistics.fmean(r["recall_at_10"] for r in fts5_per_query)
    f_prec = statistics.fmean(r["precision_at_5"] for r in fts5_per_query)
    print(f"{'Metric':<14}{'FTS5':>12}{'Hybrid':>14}{'Δ abs':>12}{'Δ rel':>10}")
    print("-" * 72)
    for name, f, h in [
        ("nDCG@10", f_ndcg, agg["ndcg_at_10"]),
        ("MRR", f_mrr, agg["mrr"]),
        ("Recall@10", f_rec, agg["recall_at_10"]),
        ("Precision@5", f_prec, agg["precision_at_5"]),
    ]:
        da = h - f
        dr = (da / f * 100) if f else 0
        print(f"{name:<14}{f:>12.4f}{h:>14.4f}{da:>+12.4f}{dr:>+9.1f}%")
    print("-" * 72)

    fts5_by_cat: dict[int, list[float]] = defaultdict(list)
    for r in fts5_per_query:
        fts5_by_cat[r["category"]].append(r["ndcg_at_10"])
    per_cat_h = {c["category"]: c for c in hybrid_results["per_category"]}
    print(f"\n{'Category':<18}{'FTS5':>10}{'Hybrid':>12}{'Δ abs':>10}{'Δ rel':>10}")
    for cat in sorted(per_cat_h):
        c = per_cat_h[cat]
        f = statistics.fmean(fts5_by_cat[cat])
        h = c["ndcg_at_10"]
        da = h - f
        dr = (da / f * 100) if f else 0
        print(f"{c['category_name']:<18}{f:>10.4f}{h:>12.4f}{da:>+10.4f}{dr:>+9.1f}%")
    print("=" * 72 + "\n")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["download", "index", "embed", "eval", "full"])
    args = p.parse_args()

    if args.cmd in ("download", "full"):
        download()
    if args.cmd in ("index", "full"):
        corpus = load_corpus()
        init_db(corpus)
    if args.cmd in ("embed", "full"):
        api_key = check_api_key()
        if not DB_PATH.exists():
            print("[fatal] DB missing — run `index` first", file=sys.stderr)
            return 4
        embed_corpus(api_key)
    if args.cmd in ("eval", "full"):
        api_key = check_api_key()
        corpus = load_corpus()
        queries = select_queries(corpus)
        results = evaluate(queries, api_key)
        # stdout: aggregate JSON
        print(json.dumps({"aggregate": results["aggregate"], "per_category": results["per_category"]}, indent=2, ensure_ascii=False))
        # stderr: human comparison table
        fts5 = load_fts5_results()
        print_comparison(results, fts5)
        write_summary(results, fts5)
    return 0


if __name__ == "__main__":
    sys.exit(main())
