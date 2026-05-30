"""
scorer.py — HotPotQA official-style F1 + EM + supporting-facts metrics.

Re-implements `hotpot_evaluate_v1.py` (Yang et al. 2018) in-tree to avoid an
external dependency. Reference:
    https://github.com/hotpotqa/hotpot/blob/master/hotpot_evaluate_v1.py

Three answer-type metrics + three supporting-facts metrics + joint metrics:

    Answer metrics (per the paper §4.1):
        ans_em  — exact match after normalization
        ans_f1  — token-level F1 after normalization
        ans_prec, ans_recall — F1 components

    Supporting facts metrics (per the paper §4.1):
        sp_em   — exact match on set of (title, sent_idx) gold facts
        sp_f1   — F1 over the (title, sent_idx) set

    Joint metrics (paper §4.1, joint scoring):
        joint_em = ans_em AND sp_em
        joint_f1 = ans_f1 * sp_f1
        joint_prec = ans_prec * sp_prec
        joint_recall = ans_recall * sp_recall

Normalization rules (faithful to official script):
    - Lowercase
    - Remove punctuation
    - Remove articles (a, an, the)
    - Collapse whitespace
"""
from __future__ import annotations

import re
import string
from collections import Counter


# ---------------------------------------------------------------------------
# String normalization (verbatim from hotpot_evaluate_v1.py)
# ---------------------------------------------------------------------------

def _normalize_answer(s: str) -> str:
    def remove_articles(text: str) -> str:
        return re.sub(r"\b(a|an|the)\b", " ", text)

    def white_space_fix(text: str) -> str:
        return " ".join(text.split())

    def remove_punc(text: str) -> str:
        exclude = set(string.punctuation)
        return "".join(ch for ch in text if ch not in exclude)

    def lower(text: str) -> str:
        return text.lower()

    return white_space_fix(remove_articles(remove_punc(lower(s or ""))))


# ---------------------------------------------------------------------------
# Answer F1 + EM
# ---------------------------------------------------------------------------

def f1_score(prediction: str, ground_truth: str) -> tuple[float, float, float]:
    """Return (f1, precision, recall) at token level after normalization.

    HotPotQA convention: yes/no questions count as bool answers — exact-match
    handles them; for F1, a single-token answer matches normally. Empty
    predictions get 0 on all three metrics.
    """
    normalized_prediction = _normalize_answer(prediction)
    normalized_ground_truth = _normalize_answer(ground_truth)

    ZERO_METRIC = (0.0, 0.0, 0.0)

    if normalized_prediction in ("yes", "no", "noanswer") and normalized_prediction != normalized_ground_truth:
        return ZERO_METRIC
    if normalized_ground_truth in ("yes", "no", "noanswer") and normalized_prediction != normalized_ground_truth:
        return ZERO_METRIC

    prediction_tokens = normalized_prediction.split()
    ground_truth_tokens = normalized_ground_truth.split()
    if not prediction_tokens or not ground_truth_tokens:
        if normalized_prediction == normalized_ground_truth:
            return 1.0, 1.0, 1.0
        return ZERO_METRIC

    common = Counter(prediction_tokens) & Counter(ground_truth_tokens)
    num_same = sum(common.values())
    if num_same == 0:
        return ZERO_METRIC
    precision = 1.0 * num_same / len(prediction_tokens)
    recall = 1.0 * num_same / len(ground_truth_tokens)
    f1 = (2 * precision * recall) / (precision + recall)
    return f1, precision, recall


def exact_match_score(prediction: str, ground_truth: str) -> float:
    return float(_normalize_answer(prediction) == _normalize_answer(ground_truth))


# ---------------------------------------------------------------------------
# Supporting facts metrics
# ---------------------------------------------------------------------------

def supporting_facts_metrics(
    pred_sp: list[tuple[str, int]],
    gold_sp: list[tuple[str, int]],
) -> tuple[float, float, float, float]:
    """Compute (em, f1, precision, recall) over (title, sent_idx) sets.

    Faithful to official script: counts matched pairs at set granularity.
    """
    cur_sp_pred = set((str(t), int(i)) for t, i in pred_sp)
    gold_sp_set = set((str(t), int(i)) for t, i in gold_sp)
    if not gold_sp_set:
        # No gold sp -> EM is whether prediction is also empty
        em = 1.0 if not cur_sp_pred else 0.0
        return em, 1.0 if em else 0.0, 1.0 if em else 0.0, 1.0 if em else 0.0
    tp = len(cur_sp_pred & gold_sp_set)
    fp = len(cur_sp_pred - gold_sp_set)
    fn = len(gold_sp_set - cur_sp_pred)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    em = 1.0 if (fp == 0 and fn == 0) else 0.0
    return em, f1, precision, recall


# ---------------------------------------------------------------------------
# Per-record scoring
# ---------------------------------------------------------------------------

def score_record(
    pred_answer: str,
    gold_answer: str,
    pred_supporting: list[tuple[str, int]],
    gold_supporting: list[tuple[str, int]],
) -> dict:
    """Return per-record metrics dict (matches hotpot_evaluate_v1 fields)."""
    ans_em = exact_match_score(pred_answer, gold_answer)
    ans_f1, ans_prec, ans_recall = f1_score(pred_answer, gold_answer)
    sp_em, sp_f1, sp_prec, sp_recall = supporting_facts_metrics(pred_supporting, gold_supporting)
    joint_em = float(ans_em * sp_em)
    joint_f1 = ans_f1 * sp_f1
    joint_prec = ans_prec * sp_prec
    joint_recall = ans_recall * sp_recall
    return {
        "ans_em": ans_em,
        "ans_f1": ans_f1,
        "ans_prec": ans_prec,
        "ans_recall": ans_recall,
        "sp_em": sp_em,
        "sp_f1": sp_f1,
        "sp_prec": sp_prec,
        "sp_recall": sp_recall,
        "joint_em": joint_em,
        "joint_f1": joint_f1,
        "joint_prec": joint_prec,
        "joint_recall": joint_recall,
    }
