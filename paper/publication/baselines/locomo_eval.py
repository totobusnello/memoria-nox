#!/usr/bin/env python3
"""LOCOMO benchmark evaluation for NOX-Supermem paper §5.2.

Downloads snap-research/locomo (CC BY-NC 4.0), indexes turns into FTS5,
runs stratified 100-query subset, computes nDCG@10/MRR/Recall@10/Precision@5.

Usage:
    python3 locomo_eval.py download   # fetch locomo10.json (~9 MB)
    python3 locomo_eval.py index      # build temp SQLite FTS5 from turns
    python3 locomo_eval.py eval       # run 100 stratified queries + metrics
    python3 locomo_eval.py full       # download + index + eval

Output: /tmp/locomo-results.jsonl + summary stats to stdout.

Schema (verified 2026-05-04):
    locomo10.json = list[10] of {
        sample_id, qa: [{question, answer, evidence:["D1:3"], category:int}],
        conversation: {speaker_a, speaker_b,
                       session_N: [{speaker, dia_id, text}],
                       session_N_date_time: str},
        event_summary, observation, session_summary
    }
    Categories: 1=single-hop 2=multi-hop 3=temporal 4=open-domain 5=adversarial
    Evidence refs are dia_ids that match conversation.session_N[i].dia_id
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import sqlite3
import sys
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

DATASET_URL = "https://raw.githubusercontent.com/snap-research/locomo/main/data/locomo10.json"
LICENSE = "CC BY-NC 4.0 (snap-research/locomo)"

CACHE = Path("/tmp/locomo10.json")
DB_PATH = Path("/tmp/locomo-eval.db")
RESULTS = Path("/tmp/locomo-results.jsonl")

CATEGORY_NAMES = {
    1: "single-hop",
    2: "multi-hop",
    3: "temporal",
    4: "open-domain",
    5: "adversarial",
}

SUBSET_PER_CATEGORY = 20  # 5 cats × 20 = 100 queries
SEED = 42


def download(force: bool = False) -> Path:
    if CACHE.exists() and not force:
        print(f"[download] cached: {CACHE} ({CACHE.stat().st_size:,} bytes)", file=sys.stderr)
        return CACHE
    print(f"[download] {DATASET_URL}", file=sys.stderr)
    req = urllib.request.Request(DATASET_URL, headers={"User-Agent": "noxmem-paper-eval/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        CACHE.write_bytes(r.read())
    print(f"[download] saved: {CACHE} ({CACHE.stat().st_size:,} bytes)", file=sys.stderr)
    return CACHE


def load_corpus() -> list[dict[str, Any]]:
    return json.loads(CACHE.read_text())


def iter_turns(corpus: list[dict]) -> list[tuple[str, str, str]]:
    """Yield (chunk_id, dia_id_full, text) tuples.

    chunk_id = f"{sample_id}::{dia_id}"
    dia_id_full = f"{sample_id}::{dia_id}"  (used to match evidence)
    """
    out: list[tuple[str, str, str]] = []
    for conv in corpus:
        sid = conv["sample_id"]
        c = conv["conversation"]
        for k, v in c.items():
            if not (k.startswith("session_") and not k.endswith("_date_time")):
                continue
            if not isinstance(v, list):
                continue
            for turn in v:
                if not isinstance(turn, dict):
                    continue
                dia_id = turn.get("dia_id")
                speaker = turn.get("speaker", "")
                text = turn.get("text", "")
                if not dia_id or not text:
                    continue
                full_id = f"{sid}::{dia_id}"
                payload = f"{speaker}: {text}"
                out.append((full_id, dia_id, payload))
    return out


def build_index(corpus: list[dict]) -> int:
    if DB_PATH.exists():
        DB_PATH.unlink()
    con = sqlite3.connect(str(DB_PATH))
    con.execute("CREATE TABLE turns (chunk_id TEXT PRIMARY KEY, sample_id TEXT, dia_id TEXT, text TEXT)")
    con.execute(
        "CREATE VIRTUAL TABLE turns_fts USING fts5(text, content='turns', content_rowid='rowid', tokenize='unicode61 remove_diacritics 2')"
    )
    rows = []
    for full_id, dia_id, text in iter_turns(corpus):
        sample_id = full_id.split("::", 1)[0]
        rows.append((full_id, sample_id, dia_id, text))
    con.executemany("INSERT INTO turns(chunk_id,sample_id,dia_id,text) VALUES(?,?,?,?)", rows)
    con.execute("INSERT INTO turns_fts(rowid,text) SELECT rowid,text FROM turns")
    con.commit()
    con.close()
    print(f"[index] {len(rows):,} turns in {DB_PATH}", file=sys.stderr)
    return len(rows)


def select_queries(corpus: list[dict]) -> list[dict]:
    """Stratified 20 per category × 5 categories, seed=42."""
    rng = random.Random(SEED)
    by_cat: dict[int, list[dict]] = defaultdict(list)
    for conv in corpus:
        sid = conv["sample_id"]
        for q in conv.get("qa", []):
            cat = q.get("category")
            if cat not in CATEGORY_NAMES:
                continue
            ev = q.get("evidence", [])
            if not isinstance(ev, list) or not ev:
                continue
            gold_ids = [f"{sid}::{e}" for e in ev if isinstance(e, str)]
            if not gold_ids:
                continue
            by_cat[cat].append(
                {
                    "category": cat,
                    "category_name": CATEGORY_NAMES[cat],
                    "sample_id": sid,
                    "question": q["question"],
                    "answer": q.get("answer") if q.get("answer") is not None else q.get("adversarial_answer", ""),
                    "gold_chunk_ids": gold_ids,
                }
            )
    selected: list[dict] = []
    for cat in sorted(by_cat):
        pool = by_cat[cat][:]
        rng.shuffle(pool)
        selected.extend(pool[:SUBSET_PER_CATEGORY])
    print(f"[queries] selected {len(selected)} (per-cat target {SUBSET_PER_CATEGORY})", file=sys.stderr)
    return selected


def fts5_escape(q: str) -> str:
    """Escape FTS5 special chars + tokenise to OR-join."""
    cleaned = re.sub(r"[^\w\s\-]", " ", q, flags=re.UNICODE)
    tokens = [t for t in cleaned.split() if len(t) >= 2]
    if not tokens:
        return '""'
    return " OR ".join(f'"{t}"' for t in tokens[:20])


def search_fts5(con: sqlite3.Connection, query: str, k: int = 10) -> list[str]:
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


def ndcg_at_k(retrieved: list[str], gold: set[str], k: int = 10) -> float:
    dcg = 0.0
    for i, rid in enumerate(retrieved[:k]):
        if rid in gold:
            dcg += 1.0 / math.log2(i + 2)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(min(len(gold), k)))
    return dcg / idcg if idcg else 0.0


def mrr(retrieved: list[str], gold: set[str]) -> float:
    for i, rid in enumerate(retrieved):
        if rid in gold:
            return 1.0 / (i + 1)
    return 0.0


def recall_at_k(retrieved: list[str], gold: set[str], k: int = 10) -> float:
    if not gold:
        return 0.0
    hit = sum(1 for r in retrieved[:k] if r in gold)
    return hit / len(gold)


def precision_at_k(retrieved: list[str], gold: set[str], k: int = 5) -> float:
    if not retrieved:
        return 0.0
    hit = sum(1 for r in retrieved[:k] if r in gold)
    return hit / k


def evaluate(queries: list[dict]) -> dict[str, Any]:
    con = sqlite3.connect(str(DB_PATH))
    per_query: list[dict] = []
    for q in queries:
        retrieved = search_fts5(con, q["question"], k=20)
        gold = set(q["gold_chunk_ids"])
        per_query.append(
            {
                "query": q["question"][:120],
                "category": q["category"],
                "category_name": q["category_name"],
                "ndcg_at_10": ndcg_at_k(retrieved, gold, 10),
                "mrr": mrr(retrieved, gold),
                "recall_at_10": recall_at_k(retrieved, gold, 10),
                "precision_at_5": precision_at_k(retrieved, gold, 5),
                "n_gold": len(gold),
                "n_retrieved": len(retrieved),
            }
        )
    con.close()
    RESULTS.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in per_query) + "\n")

    def mean(xs: list[float]) -> float:
        return sum(xs) / len(xs) if xs else 0.0

    aggregate = {
        "system": "fts5_baseline_locomo",
        "n_queries": len(per_query),
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
            }
        )
    return {"aggregate": aggregate, "per_category": per_category}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["download", "index", "eval", "full"])
    args = p.parse_args()

    if args.cmd in ("download", "full"):
        download()
    if args.cmd in ("index", "full"):
        corpus = load_corpus()
        build_index(corpus)
    if args.cmd in ("eval", "full"):
        corpus = load_corpus()
        queries = select_queries(corpus)
        out = evaluate(queries)
        print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
