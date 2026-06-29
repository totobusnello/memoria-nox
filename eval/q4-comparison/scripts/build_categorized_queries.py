#!/usr/bin/env python3
"""
build_categorized_queries.py — Produce §6.4-ready query files with category labels.

Reads the raw dataset files, applies the category_labeler mapping, validates
gold IDs against the corpus cache (GOLD-MATCH GUARD), and writes:

  cache/queries-locomo-categorized.jsonl
  cache/queries-longmemeval-categorized.jsonl

Each output line is a JSON object with:
  question_id     : str   — "{sample_id}::q{N}" for LoCoMo; question_id for LME
  dataset         : str   — "locomo" or "longmemeval"
  category_name   : str   — §6.4 bucket (runner picks up via category_name field)
  category_native : str   — original native field value for audit trail
  question        : str   — query text
  gold_chunk_ids  : list  — validated chunk IDs present in corpus cache

Usage (from repo root):
  python eval/q4-comparison/scripts/build_categorized_queries.py

Or from inside eval/q4-comparison/:
  python scripts/build_categorized_queries.py

Outputs:
  - Two JSONL files in cache/
  - Distribution table printed to stdout (dataset × category counts)
  - Records skipped by GOLD-MATCH GUARD are reported (gold_chunk_ids all-miss)

GOLD-MATCH GUARD (LoCoMo):
  The 'evidence' field in LoCoMo QA records is a list of dia_id strings.
  Some records have compound items (e.g. 'D8:6; D9:17' or 'D9:1 D4:4 D4:6').
  Guard steps:
    1. Split each item on [;\\s]+
    2. Keep only fragments matching D\\d+:\\d+ (valid dia_id pattern)
    3. Normalize leading zeros in turn number (D30:05 → D30:5)
    4. Construct {sample_id}::{dia_id} and check against corpus ID set
    5. If zero valid gold IDs → skip QA (counted in guard_miss stats)

GOLD-MATCH GUARD (LME):
  answer_session_ids are bare session IDs; checked directly against corpus.
  All 500 oracle records matched in corpus (verified 2026-06-28).
"""

from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — works when run from repo root OR from eval/q4-comparison/
# ---------------------------------------------------------------------------

_THIS_FILE = Path(__file__).resolve()
_SCRIPTS_DIR = _THIS_FILE.parent
_Q4_DIR = _SCRIPTS_DIR.parent  # eval/q4-comparison/
_REPO_ROOT = _Q4_DIR.parent.parent  # memoria-nox/

# Add lib/ to sys.path so we can import category_labeler
sys.path.insert(0, str(_Q4_DIR))

from lib.category_labeler import label_locomo_qa, label_lme_question  # noqa: E402

_RAW_DIR = _Q4_DIR / "cache" / "raw"
_CACHE_DIR = _Q4_DIR / "cache"

LOCOMO_RAW = _RAW_DIR / "locomo10.json"
LME_RAW = _RAW_DIR / "longmemeval_oracle.json"
LOCOMO_CORPUS_JSONL = _CACHE_DIR / "locomo.jsonl"
LME_CORPUS_JSONL = _CACHE_DIR / "longmemeval.jsonl"

OUT_LOCOMO = _CACHE_DIR / "queries-locomo-categorized.jsonl"
OUT_LME = _CACHE_DIR / "queries-longmemeval-categorized.jsonl"

# Minimum count per (dataset, category) below which §6.4 cell is n/a
N_A_THRESHOLD = 10


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DIA_ID_PATTERN = re.compile(r"^D\d+:\d+$")
_DIA_ID_SPLIT = re.compile(r"[;\s]+")


def _normalize_dia_id(raw: str) -> str:
    """
    Normalize a dia_id fragment to match corpus ID format.

    Strips leading zeros from the turn number:
      D30:05 → D30:5   (corpus stores without leading zeros)
    """
    m = re.match(r"^(D\d+):(\d+)$", raw)
    if m:
        return f"{m.group(1)}:{int(m.group(2))}"
    return raw


def _parse_evidence_to_gold(sample_id: str, evidence: list, corpus_ids: set[str]) -> list[str]:
    """
    Convert a LoCoMo evidence list to validated gold chunk IDs.

    Parameters
    ----------
    sample_id : str
        Conversation ID (e.g. "conv-48").
    evidence : list
        List of dia_id strings from qa_record['evidence'].
        Items may be compound ("D8:6; D9:17" or "D9:1 D4:4 D4:6").
    corpus_ids : set[str]
        Set of all chunk IDs from locomo.jsonl (for guard check).

    Returns
    -------
    list[str]
        Validated gold chunk IDs present in corpus.
        Empty list means GOLD-MATCH GUARD failed → skip this QA.
    """
    gold: list[str] = []
    seen: set[str] = set()
    for item in evidence:
        if not isinstance(item, str):
            continue
        # Split compound items (e.g. "D8:6; D9:17", "D9:1 D4:4 D4:6")
        fragments = _DIA_ID_SPLIT.split(item.strip())
        for frag in fragments:
            frag = frag.strip()
            if not _DIA_ID_PATTERN.match(frag):
                continue
            frag = _normalize_dia_id(frag)
            chunk_id = f"{sample_id}::{frag}"
            if chunk_id in corpus_ids and chunk_id not in seen:
                gold.append(chunk_id)
                seen.add(chunk_id)
    return gold


# ---------------------------------------------------------------------------
# LoCoMo builder
# ---------------------------------------------------------------------------

def build_locomo(corpus_ids: set[str]) -> tuple[int, int, int, dict[str, int]]:
    """
    Process locomo10.json → queries-locomo-categorized.jsonl.

    Returns
    -------
    (emitted, guard_miss, unclassified, category_counts)
    """
    raw = json.loads(LOCOMO_RAW.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise RuntimeError(f"Unexpected LoCoMo shape: {type(raw).__name__}")

    emitted = 0
    guard_miss = 0
    unclassified = 0
    category_counts: dict[str, int] = collections.defaultdict(int)

    with OUT_LOCOMO.open("w", encoding="utf-8") as fh:
        for conv in raw:
            sample_id = conv.get("sample_id", "")
            qa_list = conv.get("qa") or []
            for idx, qa in enumerate(qa_list):
                # Category labeling
                bucket = label_locomo_qa(qa)
                if bucket is None:
                    unclassified += 1
                    continue

                # GOLD-MATCH GUARD
                evidence = qa.get("evidence") or []
                if isinstance(evidence, str):
                    # Defensive: should already be a list after json.load
                    try:
                        import ast
                        evidence = ast.literal_eval(evidence)
                    except Exception:
                        evidence = []
                gold_ids = _parse_evidence_to_gold(sample_id, evidence, corpus_ids)
                if not gold_ids:
                    guard_miss += 1
                    continue

                question_id = f"{sample_id}::q{idx}"
                record = {
                    "question_id": question_id,
                    "dataset": "locomo",
                    "category_name": bucket,
                    "category_native": str(qa.get("category", "")),
                    "question": qa.get("question", ""),
                    "gold_chunk_ids": gold_ids,
                }
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                category_counts[bucket] += 1
                emitted += 1

    return emitted, guard_miss, unclassified, dict(category_counts)


# ---------------------------------------------------------------------------
# LongMemEval builder
# ---------------------------------------------------------------------------

def build_lme(lme_corpus_ids: set[str]) -> tuple[int, int, int, dict[str, int]]:
    """
    Process longmemeval_oracle.json → queries-longmemeval-categorized.jsonl.

    Returns
    -------
    (emitted, guard_miss, unclassified, category_counts)
    """
    raw = json.loads(LME_RAW.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise RuntimeError(f"Unexpected LME shape: {type(raw).__name__}")

    emitted = 0
    guard_miss = 0
    unclassified = 0
    category_counts: dict[str, int] = collections.defaultdict(int)

    with OUT_LME.open("w", encoding="utf-8") as fh:
        for q in raw:
            # Category labeling
            bucket = label_lme_question(q)
            if bucket is None:
                unclassified += 1
                continue

            # GOLD-MATCH GUARD
            answer_sids = q.get("answer_session_ids") or []
            gold_ids = [s for s in answer_sids if isinstance(s, str) and s in lme_corpus_ids]
            if not gold_ids:
                guard_miss += 1
                continue

            question_id = str(q.get("question_id", ""))
            record = {
                "question_id": question_id,
                "dataset": "longmemeval",
                "category_name": bucket,
                "category_native": str(q.get("question_type", "")),
                "question": q.get("question", ""),
                "gold_chunk_ids": gold_ids,
            }
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            category_counts[bucket] += 1
            emitted += 1

    return emitted, guard_miss, unclassified, dict(category_counts)


# ---------------------------------------------------------------------------
# Distribution printer
# ---------------------------------------------------------------------------

_ALL_BUCKETS = ("single-hop", "multi-hop", "temporal", "adversarial", "open-domain", "numeric")


def print_distribution(
    locomo_counts: dict[str, int],
    lme_counts: dict[str, int],
    threshold: int = N_A_THRESHOLD,
) -> None:
    print()
    print("=== §6.4 Per-Category Distribution ===")
    print(f"  n/a threshold: n < {threshold}")
    print()
    print(f"  {'Category':<18}  {'LoCoMo':>8}  {'LME':>8}  {'Notes'}")
    print(f"  {'-'*18}  {'-'*8}  {'-'*8}  {'-'*40}")

    for bucket in _ALL_BUCKETS:
        loc_n = locomo_counts.get(bucket, 0)
        lme_n = lme_counts.get(bucket, 0)

        loc_cell = str(loc_n) if loc_n >= threshold else (f"{loc_n} [n/a]" if loc_n > 0 else "n/a")
        lme_cell = str(lme_n) if lme_n >= threshold else (f"{lme_n} [n/a]" if lme_n > 0 else "n/a")

        notes = []
        if bucket == "numeric":
            notes.append("no native field in either dataset")
        if bucket == "adversarial" and lme_n > 0:
            notes.append("LME: knowledge-update (ambiguous mapping)")
        if bucket == "open-domain" and lme_n == 0:
            notes.append("no native field in LME")

        print(f"  {bucket:<18}  {loc_cell:>8}  {lme_cell:>8}  {', '.join(notes)}")

    print()
    total_loc = sum(locomo_counts.values())
    total_lme = sum(lme_counts.values())
    print(f"  {'TOTAL':<18}  {total_loc:>8}  {total_lme:>8}")
    print()

    # n/a summary
    na_cells = []
    for bucket in _ALL_BUCKETS:
        if locomo_counts.get(bucket, 0) < threshold:
            na_cells.append(f"LoCoMo×{bucket}")
        if lme_counts.get(bucket, 0) < threshold:
            na_cells.append(f"LME×{bucket}")
    if na_cells:
        print(f"  Cells marked n/a in §6.4: {', '.join(na_cells)}")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    # Pre-flight: check raw files exist
    for p in (LOCOMO_RAW, LME_RAW, LOCOMO_CORPUS_JSONL, LME_CORPUS_JSONL):
        if not p.exists():
            print(f"[ERROR] Missing required file: {p}", file=sys.stderr)
            print("  Run from a host with the full dataset cache.", file=sys.stderr)
            return 1

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Load corpus ID sets (for GOLD-MATCH GUARD)
    print("[1/4] Loading LoCoMo corpus IDs...", file=sys.stderr)
    locomo_corpus_ids: set[str] = set()
    with LOCOMO_CORPUS_JSONL.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                locomo_corpus_ids.add(json.loads(line)["id"])
    print(f"      {len(locomo_corpus_ids):,} chunk IDs loaded", file=sys.stderr)

    print("[2/4] Loading LME corpus IDs...", file=sys.stderr)
    lme_corpus_ids: set[str] = set()
    with LME_CORPUS_JSONL.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                lme_corpus_ids.add(json.loads(line)["id"])
    print(f"      {len(lme_corpus_ids):,} chunk IDs loaded", file=sys.stderr)

    # Build LoCoMo categorized queries
    print("[3/4] Building LoCoMo categorized queries...", file=sys.stderr)
    loc_emitted, loc_guard_miss, loc_unclassified, loc_counts = build_locomo(locomo_corpus_ids)
    print(
        f"      emitted={loc_emitted}  guard_miss={loc_guard_miss}  unclassified={loc_unclassified}",
        file=sys.stderr,
    )
    print(f"      -> {OUT_LOCOMO}", file=sys.stderr)

    # Build LME categorized queries
    print("[4/4] Building LME categorized queries...", file=sys.stderr)
    lme_emitted, lme_guard_miss, lme_unclassified, lme_counts = build_lme(lme_corpus_ids)
    print(
        f"      emitted={lme_emitted}  guard_miss={lme_guard_miss}  unclassified={lme_unclassified}",
        file=sys.stderr,
    )
    print(f"      -> {OUT_LME}", file=sys.stderr)

    # Print distribution to stdout
    print_distribution(loc_counts, lme_counts)

    print("Done. To run the disaggregated benchmark:")
    print(f"  python runner.py --systems nox_mem,mem0,agentmemory \\")
    print(f"    --datasets locomo --queries-file {OUT_LOCOMO} --limit 100")
    print(f"  python runner.py --systems nox_mem,mem0,agentmemory \\")
    print(f"    --datasets longmemeval --queries-file {OUT_LME} --limit 100")
    print()
    print("NOTE: With --limit 100 on LoCoMo (total ~1977 queries), the natural")
    print("order may undersample 'temporal' (cat 3). Consider --limit 0 (all)")
    print("or a stratified sample script for balanced per-category counts.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
