"""
category_labeler.py — §6.4 per-category bucket assignment for Q4 comparison.

Maps native dataset fields to the 6 §6.4 buckets:
  single-hop | multi-hop | temporal | adversarial | open-domain | numeric

MAPPING TABLE
=============

LoCoMo (snap-research/locomo, locomo10.json)
  Native field: qa_record['category']  (int 1-5, stored as int in parsed JSON)
  Source of truth: eval/locomo/dry-run-sample.json  →  category_name field
  Confirmed cross-check: category 5 == all records with 'adversarial_answer' key (n=446, 100%)

    1 → single-hop    (single-session single-evidence retrieval)
    2 → multi-hop     (multi-evidence across sessions)
    3 → temporal      (time-anchored queries)
    4 → open-domain   (common-knowledge + long-horizon retrieval)
    5 → adversarial   (adversarial_answer field present; system must reject distractor)

  NOT MAPPED: 'numeric' — no native numeric category in LoCoMo.
  Cells LoCoMo×numeric → n/a in §6.4 table.

LongMemEval (xiaowu0162/longmemeval-cleaned, oracle split)
  Native field: question_record['question_type']  (str)
  Source of truth: longmemeval_oracle.json  (distribution verified 2026-06-28)

    'single-session-user'       → single-hop  (single-session, user-perspective query)
    'single-session-assistant'  → single-hop  (single-session, assistant-perspective query;
                                               retrieval structure identical to user variant)
    'single-session-preference' → single-hop  (single-session preference recall)
    'multi-session'             → multi-hop   (evidence spans ≥2 sessions)
    'temporal-reasoning'        → temporal    (requires temporal ordering/dating)
    'knowledge-update'          → adversarial [AMBIGUOUS — see note below]

  NOT MAPPED: 'open-domain' — no native open-domain category in LME.
  Cells LME×open-domain → n/a in §6.4 table.

  NOT MAPPED: 'numeric' — no native numeric category in LME.
  Cells LME×numeric → n/a in §6.4 table.

AMBIGUITY NOTE: 'knowledge-update' (LME, n=78)
  This question type tests whether the system tracks knowledge changes over time
  (e.g., user says X, later corrects to Y; system must return Y not X).
  It has a temporal element (update ordering) AND an adversarial element (prior
  state is a distractor). Mapped to 'adversarial' because the core challenge is
  distractor rejection, matching LoCoMo cat-5 semantics. Alternative mapping
  'temporal' is defensible. NOT mapped to 'open-domain' (requires memory context).
  Paper footnote recommended.

INTEGRITY CONTRACT
  Every bucket assignment traces to a native field (category int or question_type str).
  No heuristics, no answer-text inspection, no LLM classification.
  Unknown values return None — callers must handle explicitly.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# LoCoMo: integer category → §6.4 bucket
# Source: eval/locomo/dry-run-sample.json category_name field (verified 2026-06-28)
# ---------------------------------------------------------------------------

LOCOMO_CATEGORY_MAP: dict[int, str] = {
    1: "single-hop",   # single-session single-evidence
    2: "multi-hop",    # multi-evidence, cross-session
    3: "temporal",     # time-anchored queries
    4: "open-domain",  # common-knowledge / long-horizon
    5: "adversarial",  # adversarial_answer present; distractor rejection
}

# ---------------------------------------------------------------------------
# LongMemEval: question_type string → §6.4 bucket
# Source: longmemeval_oracle.json question_type field (verified 2026-06-28)
# ---------------------------------------------------------------------------

LME_QUESTION_TYPE_MAP: dict[str, str] = {
    "single-session-user": "single-hop",
    "single-session-assistant": "single-hop",   # same retrieval structure
    "single-session-preference": "single-hop",
    "multi-session": "multi-hop",
    "temporal-reasoning": "temporal",
    "knowledge-update": "adversarial",           # AMBIGUOUS — see module docstring
}

# Buckets present in §6.4 table
ALL_BUCKETS: tuple[str, ...] = (
    "single-hop",
    "multi-hop",
    "temporal",
    "adversarial",
    "open-domain",
    "numeric",
)

# Buckets with no native source in any dataset → n/a in §6.4
NATIVE_ABSENT_BUCKETS: dict[str, list[str]] = {
    # dataset → list of buckets that have no native field mapping
    "locomo": ["numeric"],
    "longmemeval": ["open-domain", "numeric"],
}


def label_locomo_qa(qa_record: dict) -> str | None:
    """
    Return the §6.4 bucket for a LoCoMo QA record.

    Parameters
    ----------
    qa_record : dict
        One element from the 'qa' list of a LoCoMo conversation.
        Expected key: 'category' (int or int-castable value).

    Returns
    -------
    str | None
        One of ALL_BUCKETS, or None if 'category' is absent / unrecognised.
        Callers should treat None as unclassified and skip the record.
    """
    raw = qa_record.get("category")
    if raw is None:
        return None
    try:
        cat_int = int(raw)
    except (ValueError, TypeError):
        return None
    return LOCOMO_CATEGORY_MAP.get(cat_int)


def label_lme_question(question_record: dict) -> str | None:
    """
    Return the §6.4 bucket for a LongMemEval question record.

    Parameters
    ----------
    question_record : dict
        One element from the LongMemEval oracle JSON array.
        Expected key: 'question_type' (str).

    Returns
    -------
    str | None
        One of ALL_BUCKETS, or None if 'question_type' is absent / unrecognised.
        Callers should treat None as unclassified and skip the record.
    """
    qt = question_record.get("question_type")
    if qt is None:
        return None
    return LME_QUESTION_TYPE_MAP.get(str(qt))
