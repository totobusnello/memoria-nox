"""
scorer.py — LoCoMo official scoring metric.

Mirrors /tmp/locomo-repo/task_eval/evaluation.py (Maharana et al., 2024).

Per-category scoring:
  - cat 1 (multi_hop)       : F1 with sub-answer split on ';' / ',' (partial credit)
  - cat 2 (temporal)        : token-level F1 (same as single_hop)
  - cat 3 (commonsense)     : answer pre-split on ';' (first sub-answer)
  - cat 4 (single_hop)      : token-level F1
  - cat 5 (adversarial)     : 1 if response indicates abstention, else 0

Tokenization mirrors SQuAD-style normalisation: lowercase, strip punctuation,
strip articles, collapse whitespace.

Public exports:
  - score_record(category, gold_answer, generated_answer) -> ScoreDetail
  - score_all(records) -> AggregateResult
  - tokenize / normalize_answer / f1_score (utility)

This is the SECOND source-of-truth file in the harness (corpus_loader being
the first). Adapter does NOT score; orchestrator imports from here.
"""
from __future__ import annotations

import math
import re
import string
from collections import Counter
from dataclasses import dataclass, field
from typing import Iterable


# ---------------------------------------------------------------------------
# SQuAD-style normalisation (LoCoMo paper §4.2)
# ---------------------------------------------------------------------------

_ARTICLES_RE = re.compile(r"\b(a|an|the)\b", flags=re.UNICODE)
_PUNCT_RE = re.compile(f"[{re.escape(string.punctuation)}]")
_WS_RE = re.compile(r"\s+")


def normalize_answer(s: str) -> str:
    """SQuAD-style: lowercase → strip punctuation → strip articles → collapse ws."""
    if s is None:
        return ""
    s = str(s).lower()
    s = _PUNCT_RE.sub(" ", s)
    s = _ARTICLES_RE.sub(" ", s)
    s = _WS_RE.sub(" ", s).strip()
    return s


def tokenize(s: str) -> list[str]:
    return [t for t in normalize_answer(s).split(" ") if t]


def f1_score(pred: str, gold: str) -> float:
    """Token-overlap F1 (SQuAD)."""
    p_toks = tokenize(pred)
    g_toks = tokenize(gold)
    if not p_toks or not g_toks:
        # Both empty → 1.0; one empty + one not → 0.0
        return 1.0 if p_toks == g_toks else 0.0
    common = Counter(p_toks) & Counter(g_toks)
    n_common = sum(common.values())
    if n_common == 0:
        return 0.0
    precision = n_common / len(p_toks)
    recall = n_common / len(g_toks)
    return 2 * precision * recall / (precision + recall)


def multi_hop_f1(pred: str, gold: str) -> float:
    """
    Multi-hop scoring (cat 1) per LoCoMo evaluation.py::f1():
    split gold on ';' (or ',' as fallback) into sub-answers; average per-sub F1
    over sub-answers; pred is the FULL prediction string compared against EACH
    sub-answer (partial credit).
    """
    gold = str(gold or "")
    # Primary split: semicolon. If only one piece, try comma.
    parts = [p.strip() for p in gold.split(";") if p.strip()]
    if len(parts) < 2:
        parts = [p.strip() for p in gold.split(",") if p.strip()]
    if not parts:
        return 0.0
    scores = [f1_score(pred, p) for p in parts]
    return sum(scores) / len(scores)


_ABSTAIN_PATTERNS = [
    "not mentioned",
    "no information",
    "no info",
    "i don't know",
    "i do not know",
    "cannot answer",
    "can't answer",
    "unanswerable",
    "not answerable",
    "not available",
    "not provided",
    "no answer",
    "unknown",
    "i'm not sure",
    "cannot be determined",
    "no relevant",
    "no record",
]


def adversarial_score(pred: str) -> float:
    """
    Cat 5 scoring: 1 if model refused (abstained), 0 otherwise.
    Pattern list mirrors LoCoMo evaluation.py and expands common refusal phrases
    from GPT/Claude/Gemini families.
    """
    if not pred:
        return 0.0
    low = pred.lower()
    for pat in _ABSTAIN_PATTERNS:
        if pat in low:
            return 1.0
    return 0.0


# ---------------------------------------------------------------------------
# Per-record scoring
# ---------------------------------------------------------------------------

@dataclass
class ScoreDetail:
    category: int
    category_name: str
    f1: float
    is_correct: bool          # 1 if F1 >= 0.5 else 0 (binary-decision)
    method: str               # "f1" | "multi_hop_f1" | "adversarial"


def _category_name(cat: int) -> str:
    return {
        1: "multi_hop",
        2: "temporal",
        3: "commonsense",
        4: "single_hop",
        5: "adversarial",
    }.get(cat, "unknown")


def score_record(category: int, gold_answer: str, generated_answer: str) -> ScoreDetail:
    """
    Score one (category, gold, generated) triple per LoCoMo official metric.

    Returns ScoreDetail with `f1` ∈ [0, 1] and `is_correct` (F1 >= 0.5).
    """
    gen = str(generated_answer or "")
    gold = str(gold_answer or "")
    cat_name = _category_name(category)
    if category == 1:
        s = multi_hop_f1(gen, gold)
        return ScoreDetail(category=category, category_name=cat_name,
                           f1=s, is_correct=(s >= 0.5), method="multi_hop_f1")
    if category == 3:
        # Commonsense: gold may have ';' separating alternative answers;
        # per evaluation.py: answer = answer.split(';')[0].strip()
        gold = gold.split(";")[0].strip() or gold
        s = f1_score(gen, gold)
        return ScoreDetail(category=category, category_name=cat_name,
                           f1=s, is_correct=(s >= 0.5), method="f1")
    if category == 5:
        s = adversarial_score(gen)
        return ScoreDetail(category=category, category_name=cat_name,
                           f1=s, is_correct=(s == 1.0), method="adversarial")
    # cats 2 (temporal), 4 (single_hop), and unknown → token F1
    s = f1_score(gen, gold)
    return ScoreDetail(category=category, category_name=cat_name,
                       f1=s, is_correct=(s >= 0.5), method="f1")


# ---------------------------------------------------------------------------
# Aggregate
# ---------------------------------------------------------------------------

@dataclass
class AggregateResult:
    n_total: int
    n_scored: int
    n_errors: int
    mean_f1: float
    accuracy: float           # share with F1 >= 0.5
    per_category: dict[str, dict[str, float]] = field(default_factory=dict)
    # nDCG-style helper for headline (not LoCoMo official but useful)
    f1_ci95: tuple[float, float] = (0.0, 0.0)
    # Retrieval-only metrics (populated when generated_answer empty)
    n_retrieval_scored: int = 0
    evidence_hit_at_5: float = 0.0
    evidence_hit_at_10: float = 0.0
    evidence_hit_at_20: float = 0.0
    evidence_recall_at_10: float = 0.0
    retrieval_mode: bool = False  # True if no generated_answer present


def _wilson_ci(p: float, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    z2 = z * z
    denom = 1 + z2 / n
    centre = (p + z2 / (2 * n)) / denom
    half = (z * math.sqrt((p * (1 - p) + z2 / (4 * n)) / n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def _evidence_hit_at_k(retrieved_dia_ids: list[str], gold: set[str], k: int) -> int:
    if not gold:
        return 0
    return 1 if any(d in gold for d in retrieved_dia_ids[:k]) else 0


def _evidence_recall_at_k(retrieved_dia_ids: list[str], gold: set[str], k: int) -> float:
    if not gold:
        return 0.0
    hits = sum(1 for d in retrieved_dia_ids[:k] if d in gold)
    return hits / len(gold)


def score_all(records: Iterable[dict]) -> AggregateResult:
    """
    Score JSONL-style adapter records.

    Modes:
      - generation mode (default): records have generated_answer; computes
        LoCoMo official F1 + per-category breakdown.
      - retrieval-only mode (no generator): records have retrieved_dia_ids;
        computes evidence-hit-at-k + recall-at-k against gold evidence dia_ids.

    Each record must have:
      - category (int)
      - answer (gold) — may be empty for adversarial
      - generated_answer (str, optional)
      - retrieved_dia_ids (list[str], optional — used in retrieval-only mode)
      - evidence (list[str], gold dia_ids — for retrieval scoring)
      - error (optional)
    """
    overall_f1: list[float] = []
    overall_correct: list[int] = []
    per_cat_f1: dict[str, list[float]] = {}
    per_cat_correct: dict[str, list[int]] = {}
    n_total = 0
    n_err = 0
    n_scored = 0
    # Retrieval-only stats
    hit5: list[int] = []
    hit10: list[int] = []
    hit20: list[int] = []
    recall10: list[float] = []
    per_cat_hit10: dict[str, list[int]] = {}
    per_cat_recall10: dict[str, list[float]] = {}
    n_retrieval_scored = 0
    any_generated = False

    records_list = list(records)  # need to iterate twice possibly
    for r in records_list:
        if r.get("generated_answer"):
            any_generated = True
            break

    for r in records_list:
        n_total += 1
        if r.get("error") and not r.get("generated_answer"):
            n_err += 1
            # Still count for retrieval if dia_ids present
            cat_raw = r.get("category", 0)
            try:
                cat = int(cat_raw)
            except Exception:
                cat = 0
            evidence = set(r.get("evidence") or [])
            retr_dias = list(r.get("retrieved_dia_ids") or [])
            if evidence and retr_dias:
                cat_name = _category_name(cat)
                h5 = _evidence_hit_at_k(retr_dias, evidence, 5)
                h10 = _evidence_hit_at_k(retr_dias, evidence, 10)
                h20 = _evidence_hit_at_k(retr_dias, evidence, 20)
                r10 = _evidence_recall_at_k(retr_dias, evidence, 10)
                hit5.append(h5)
                hit10.append(h10)
                hit20.append(h20)
                recall10.append(r10)
                per_cat_hit10.setdefault(cat_name, []).append(h10)
                per_cat_recall10.setdefault(cat_name, []).append(r10)
                n_retrieval_scored += 1
            continue
        cat_raw = r.get("category", r.get("category_int", 0))
        try:
            cat = int(cat_raw)
        except Exception:
            cat = 0
        cat_name = _category_name(cat)
        # Retrieval scoring (always when evidence + retrieved dias)
        evidence = set(r.get("evidence") or [])
        retr_dias = list(r.get("retrieved_dia_ids") or [])
        if evidence and retr_dias:
            h5 = _evidence_hit_at_k(retr_dias, evidence, 5)
            h10 = _evidence_hit_at_k(retr_dias, evidence, 10)
            h20 = _evidence_hit_at_k(retr_dias, evidence, 20)
            r10 = _evidence_recall_at_k(retr_dias, evidence, 10)
            hit5.append(h5)
            hit10.append(h10)
            hit20.append(h20)
            recall10.append(r10)
            per_cat_hit10.setdefault(cat_name, []).append(h10)
            per_cat_recall10.setdefault(cat_name, []).append(r10)
            n_retrieval_scored += 1
        # Generation scoring (only if generated_answer present)
        if r.get("generated_answer"):
            detail = score_record(cat, r.get("answer", ""), r.get("generated_answer", ""))
            overall_f1.append(detail.f1)
            overall_correct.append(1 if detail.is_correct else 0)
            per_cat_f1.setdefault(detail.category_name, []).append(detail.f1)
            per_cat_correct.setdefault(detail.category_name, []).append(
                1 if detail.is_correct else 0
            )
            n_scored += 1

    def _mean(xs: list[float]) -> float:
        return sum(xs) / len(xs) if xs else 0.0

    mean_f1 = _mean(overall_f1)
    accuracy = _mean([float(x) for x in overall_correct])

    per_cat_out: dict[str, dict[str, float]] = {}
    # If we have generation, populate per-cat with F1/acc
    if n_scored > 0:
        for cat_name in sorted(per_cat_f1.keys()):
            f1s = per_cat_f1[cat_name]
            accs = per_cat_correct[cat_name]
            per_cat_out[cat_name] = {
                "n": float(len(f1s)),
                "mean_f1": _mean(f1s),
                "accuracy": _mean([float(x) for x in accs]),
            }
    # Merge retrieval per-cat metrics
    for cat_name in sorted(set(list(per_cat_hit10.keys()) + list(per_cat_out.keys()))):
        d = per_cat_out.setdefault(cat_name, {})
        if cat_name in per_cat_hit10:
            d["evidence_hit_at_10"] = _mean([float(x) for x in per_cat_hit10[cat_name]])
            d["evidence_recall_at_10"] = _mean(per_cat_recall10[cat_name])
            d["n_retrieval"] = float(len(per_cat_hit10[cat_name]))

    lo, hi = _wilson_ci(accuracy, n_scored) if n_scored else (0.0, 0.0)
    return AggregateResult(
        n_total=n_total,
        n_scored=n_scored,
        n_errors=n_err,
        mean_f1=mean_f1,
        accuracy=accuracy,
        per_category=per_cat_out,
        f1_ci95=(lo, hi),
        n_retrieval_scored=n_retrieval_scored,
        evidence_hit_at_5=_mean([float(x) for x in hit5]),
        evidence_hit_at_10=_mean([float(x) for x in hit10]),
        evidence_hit_at_20=_mean([float(x) for x in hit20]),
        evidence_recall_at_10=_mean(recall10),
        retrieval_mode=(not any_generated and n_retrieval_scored > 0),
    )


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def _self_test() -> None:
    # f1
    assert f1_score("Paris", "Paris") == 1.0
    assert 0 < f1_score("Paris France", "Paris") < 1.0
    assert f1_score("Berlin", "Paris") == 0.0
    # multi-hop
    assert multi_hop_f1("Adoption agencies and counseling",
                        "Adoption agencies; counseling certification") >= 0.5
    assert multi_hop_f1("psychology counseling certification",
                        "Psychology; counseling certification") >= 0.6
    # Identity-ish case (cat 1) — note: multi_hop_f1 compares FULL pred vs each
    # sub-answer (LoCoMo paper §4.2), so even pred=gold can't reach 1.0 if
    # gold splits into >=2 subs of different lengths.
    assert multi_hop_f1("foo bar; baz", "foo bar; baz") >= 0.6
    # adversarial
    assert adversarial_score("Not mentioned in the conversation") == 1.0
    assert adversarial_score("Caroline went to Paris") == 0.0
    # cat 3 commonsense
    d = score_record(3, "psychology; counseling",
                     "psychology")
    assert d.is_correct
    # cat 5 adversarial
    d = score_record(5, "", "I don't know")
    assert d.is_correct
    print("OK scorer self-test passed")


if __name__ == "__main__":
    _self_test()
