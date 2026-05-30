"""
scorer.py — MuSiQue official scoring metric (answer F1/EM + support F1).

Mirrors /tmp/musique-repo/metrics/answer.py and /tmp/musique-repo/metrics/support.py
(Trivedi et al. TACL 2022).

Per-question metrics:
  - answer_em : exact match between normalized predicted_answer and any
                of [answer] + answer_aliases. Take MAX over ground-truth set.
  - answer_f1 : SQuAD-style token-overlap F1 (MAX over ground-truth set).
  - support_f1: F1 over predicted supporting paragraph indices vs gold
                supporting indices.

Normalisation (SQuAD-style; mirrors metrics/answer.py::normalize_answer):
  lowercase → strip punctuation → strip articles (a/an/the) → collapse ws.

Public exports:
  - score_record(predicted_answer, predicted_support_idxs, question) -> ScoreDetail
  - score_all(records, questions_by_id) -> AggregateResult
  - normalize_answer / get_tokens / compute_f1 / compute_exact (utility)
  - support_f1(pred_idxs, gold_idxs) -> (em, f1)

This is the SECOND source-of-truth file in the harness (corpus_loader being
the first). Adapter does NOT score; aggregate imports from here.
"""
from __future__ import annotations

import math
import re
import string
from collections import Counter
from dataclasses import dataclass, field
from typing import Iterable


# ---------------------------------------------------------------------------
# SQuAD-style normalisation (MuSiQue metrics/answer.py)
# ---------------------------------------------------------------------------

_ARTICLES_RE = re.compile(r"\b(a|an|the)\b", flags=re.UNICODE)
_PUNCT_SET = set(string.punctuation)


def normalize_answer(s: str) -> str:
    """SQuAD-style: lowercase → strip punctuation → strip articles → collapse ws."""
    if s is None:
        return ""
    s = str(s).lower()
    s = "".join(ch for ch in s if ch not in _PUNCT_SET)
    s = _ARTICLES_RE.sub(" ", s)
    s = " ".join(s.split())
    return s


def get_tokens(s: str) -> list[str]:
    return normalize_answer(s).split() if s else []


def compute_exact(a_gold: str, a_pred: str) -> int:
    return int(normalize_answer(a_gold) == normalize_answer(a_pred))


def compute_f1(a_gold: str, a_pred: str) -> float:
    gold_toks = get_tokens(a_gold)
    pred_toks = get_tokens(a_pred)
    common = Counter(gold_toks) & Counter(pred_toks)
    num_same = sum(common.values())
    if len(gold_toks) == 0 or len(pred_toks) == 0:
        # Per SQuAD: if either is no-answer, F1 is 1 iff they agree.
        return float(int(gold_toks == pred_toks))
    if num_same == 0:
        return 0.0
    precision = num_same / len(pred_toks)
    recall = num_same / len(gold_toks)
    return 2 * precision * recall / (precision + recall)


def metric_max_over_ground_truths(
    metric_fn, prediction: str, ground_truths: list[str]
) -> float:
    if not ground_truths:
        return 0.0
    return max(float(metric_fn(g, prediction)) for g in ground_truths)


# ---------------------------------------------------------------------------
# Support F1 (HotpotQA-style; MuSiQue metrics/support.py)
# ---------------------------------------------------------------------------

def support_em_f1(
    predicted_support_idxs: list[int], gold_support_idxs: list[int]
) -> tuple[float, float]:
    """Returns (em, f1) following metrics/support.py logic."""
    cur_sp_pred = set(int(x) for x in predicted_support_idxs)
    gold_sp_pred = set(int(x) for x in gold_support_idxs)
    tp = sum(1 for e in cur_sp_pred if e in gold_sp_pred)
    fp = sum(1 for e in cur_sp_pred if e not in gold_sp_pred)
    fn = sum(1 for e in gold_sp_pred if e not in cur_sp_pred)
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * prec * recall / (prec + recall) if (prec + recall) > 0 else 0.0
    em = 1.0 if (fp + fn == 0) else 0.0
    if not cur_sp_pred and not gold_sp_pred:
        f1, em = 1.0, 1.0
    return em, f1


# ---------------------------------------------------------------------------
# Per-record scoring
# ---------------------------------------------------------------------------

@dataclass
class ScoreDetail:
    qid: str
    hop_count: int
    hop_prefix: str
    answer_em: int               # 0/1
    answer_f1: float             # [0,1]
    support_em: float            # 0/1 (as float for averaging compat)
    support_f1: float            # [0,1]
    answer_is_correct: bool      # answer_f1 >= 0.5


def score_record(
    predicted_answer: str,
    predicted_support_idxs: list[int],
    gold_answers: list[str],
    gold_support_idxs: list[int],
    qid: str = "",
    hop_count: int = 0,
    hop_prefix: str = "",
) -> ScoreDetail:
    em = int(metric_max_over_ground_truths(
        compute_exact, predicted_answer, gold_answers
    ))
    f1 = metric_max_over_ground_truths(
        compute_f1, predicted_answer, gold_answers
    )
    s_em, s_f1 = support_em_f1(predicted_support_idxs, gold_support_idxs)
    return ScoreDetail(
        qid=qid,
        hop_count=hop_count,
        hop_prefix=hop_prefix,
        answer_em=em,
        answer_f1=f1,
        support_em=s_em,
        support_f1=s_f1,
        answer_is_correct=(f1 >= 0.5),
    )


# ---------------------------------------------------------------------------
# Aggregate
# ---------------------------------------------------------------------------

@dataclass
class AggregateResult:
    n_total: int                       # total adapter records
    n_scored: int                      # records w/ generated answer
    n_errors: int
    # Generation/answer metrics (MuSiQue official)
    answer_em: float
    answer_f1: float
    support_f1: float
    accuracy: float                    # share with answer_f1 >= 0.5
    # CI on answer_f1
    f1_ci95: tuple[float, float] = (0.0, 0.0)
    # Per-hop breakdown
    per_hop: dict[str, dict[str, float]] = field(default_factory=dict)
    # Retrieval-only metrics (when no generator)
    n_retrieval_scored: int = 0
    support_hit_at_5: float = 0.0
    support_hit_at_10: float = 0.0
    support_hit_at_20: float = 0.0
    support_recall_at_10: float = 0.0
    retrieval_mode: bool = False


def _wilson_ci(p: float, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    z2 = z * z
    denom = 1 + z2 / n
    centre = (p + z2 / (2 * n)) / denom
    half = (z * math.sqrt((p * (1 - p) + z2 / (4 * n)) / n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def _support_hit_at_k(
    retrieved_para_idxs: list[int], gold: set[int], k: int
) -> int:
    if not gold:
        return 0
    return 1 if any(idx in gold for idx in retrieved_para_idxs[:k]) else 0


def _support_recall_at_k(
    retrieved_para_idxs: list[int], gold: set[int], k: int
) -> float:
    if not gold:
        return 0.0
    hits = sum(1 for idx in retrieved_para_idxs[:k] if idx in gold)
    return hits / len(gold)


def score_all(records: Iterable[dict]) -> AggregateResult:
    """
    Score adapter JSONL records using MuSiQue official metric.

    Each record must have:
      - qid, hop_prefix, hop_count
      - gold_answers (list[str], from question.all_answers)
      - gold_support_idxs (list[int], from question.supporting_idxs)
      - generated_answer (str)
      - predicted_support_idxs (list[int]) — derived from retrieved_para_idxs top-K
      - retrieved_para_idxs (list[int])
      - error (str, optional)

    Modes:
      - generation mode: records have generated_answer; compute answer_f1 + support_f1
      - retrieval-only: no generator; compute support hit@k recall@k
    """
    answer_em_list: list[int] = []
    answer_f1_list: list[float] = []
    support_f1_list: list[float] = []
    correct_list: list[int] = []
    per_hop_f1: dict[str, list[float]] = {}
    per_hop_em: dict[str, list[int]] = {}
    per_hop_sup: dict[str, list[float]] = {}
    per_hop_n: dict[str, int] = {}

    # Retrieval-only
    hit5: list[int] = []
    hit10: list[int] = []
    hit20: list[int] = []
    recall10: list[float] = []
    per_hop_hit10: dict[str, list[int]] = {}
    per_hop_recall10: dict[str, list[float]] = {}

    n_total = 0
    n_err = 0
    n_scored = 0
    n_retrieval_scored = 0
    any_generated = False

    records_list = list(records)
    for r in records_list:
        if r.get("generated_answer"):
            any_generated = True
            break

    for r in records_list:
        n_total += 1
        hop = str(r.get("hop_prefix") or "unknown")
        gold_answers = list(r.get("gold_answers") or [])
        gold_support = set(int(x) for x in (r.get("gold_support_idxs") or []))
        retrieved = list(r.get("retrieved_para_idxs") or [])
        retrieved_int: list[int] = []
        for x in retrieved:
            try:
                retrieved_int.append(int(x))
            except Exception:
                continue

        # Retrieval-only metrics (always when we have data)
        if gold_support and retrieved_int:
            hit5.append(_support_hit_at_k(retrieved_int, gold_support, 5))
            hit10.append(_support_hit_at_k(retrieved_int, gold_support, 10))
            hit20.append(_support_hit_at_k(retrieved_int, gold_support, 20))
            recall10.append(_support_recall_at_k(retrieved_int, gold_support, 10))
            per_hop_hit10.setdefault(hop, []).append(
                _support_hit_at_k(retrieved_int, gold_support, 10)
            )
            per_hop_recall10.setdefault(hop, []).append(
                _support_recall_at_k(retrieved_int, gold_support, 10)
            )
            n_retrieval_scored += 1

        if r.get("error") and not r.get("generated_answer"):
            n_err += 1
            continue

        pred_answer = str(r.get("generated_answer") or "")
        pred_support = list(r.get("predicted_support_idxs") or [])

        if pred_answer and gold_answers:
            detail = score_record(
                predicted_answer=pred_answer,
                predicted_support_idxs=pred_support,
                gold_answers=gold_answers,
                gold_support_idxs=list(gold_support),
                qid=str(r.get("qid") or ""),
                hop_count=int(r.get("hop_count") or 0),
                hop_prefix=hop,
            )
            answer_em_list.append(detail.answer_em)
            answer_f1_list.append(detail.answer_f1)
            support_f1_list.append(detail.support_f1)
            correct_list.append(1 if detail.answer_is_correct else 0)
            per_hop_f1.setdefault(hop, []).append(detail.answer_f1)
            per_hop_em.setdefault(hop, []).append(detail.answer_em)
            per_hop_sup.setdefault(hop, []).append(detail.support_f1)
            per_hop_n[hop] = per_hop_n.get(hop, 0) + 1
            n_scored += 1

    def _mean(xs: list[float]) -> float:
        return sum(xs) / len(xs) if xs else 0.0

    answer_em = _mean([float(x) for x in answer_em_list])
    answer_f1 = _mean(answer_f1_list)
    support_f1 = _mean(support_f1_list)
    accuracy = _mean([float(x) for x in correct_list])

    per_hop: dict[str, dict[str, float]] = {}
    for hop in sorted(set(list(per_hop_n.keys()) + list(per_hop_hit10.keys()))):
        d: dict[str, float] = {}
        if hop in per_hop_n:
            d["n"] = float(per_hop_n[hop])
            d["answer_em"] = _mean([float(x) for x in per_hop_em.get(hop, [])])
            d["answer_f1"] = _mean(per_hop_f1.get(hop, []))
            d["support_f1"] = _mean(per_hop_sup.get(hop, []))
        if hop in per_hop_hit10:
            d["n_retrieval"] = float(len(per_hop_hit10[hop]))
            d["support_hit_at_10"] = _mean(
                [float(x) for x in per_hop_hit10[hop]]
            )
            d["support_recall_at_10"] = _mean(per_hop_recall10[hop])
        per_hop[hop] = d

    lo, hi = _wilson_ci(accuracy, n_scored) if n_scored else (0.0, 0.0)

    return AggregateResult(
        n_total=n_total,
        n_scored=n_scored,
        n_errors=n_err,
        answer_em=answer_em,
        answer_f1=answer_f1,
        support_f1=support_f1,
        accuracy=accuracy,
        f1_ci95=(lo, hi),
        per_hop=per_hop,
        n_retrieval_scored=n_retrieval_scored,
        support_hit_at_5=_mean([float(x) for x in hit5]),
        support_hit_at_10=_mean([float(x) for x in hit10]),
        support_hit_at_20=_mean([float(x) for x in hit20]),
        support_recall_at_10=_mean(recall10),
        retrieval_mode=(not any_generated and n_retrieval_scored > 0),
    )


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def _self_test() -> None:
    # normalize_answer
    assert normalize_answer("The Beatles!") == "beatles"
    assert normalize_answer("  An apple, A pie  ") == "apple pie"
    # f1 / em
    assert compute_exact("Miquette Giraudy", "Miquette Giraudy") == 1
    assert compute_exact("the Beatles", "Beatles") == 1  # articles stripped
    assert compute_f1("Miquette Giraudy", "Miquette Giraudy") == 1.0
    assert 0 < compute_f1("Miquette Giraudy", "Miquette") < 1.0
    assert compute_f1("Beatles", "Stones") == 0.0
    # metric_max_over_ground_truths
    assert metric_max_over_ground_truths(
        compute_f1, "Beatles", ["Stones", "The Beatles"]
    ) == 1.0
    # support
    em, f1 = support_em_f1([5, 10], [5, 10])
    assert em == 1.0 and f1 == 1.0
    em, f1 = support_em_f1([5, 11], [5, 10])
    assert em == 0.0 and 0 < f1 < 1.0
    em, f1 = support_em_f1([], [])
    assert em == 1.0 and f1 == 1.0
    # score_record
    sd = score_record(
        predicted_answer="Miquette Giraudy",
        predicted_support_idxs=[5, 10],
        gold_answers=["Miquette Giraudy"],
        gold_support_idxs=[5, 10],
        qid="2hop__test",
        hop_count=2,
        hop_prefix="2hop",
    )
    assert sd.answer_em == 1
    assert sd.answer_f1 == 1.0
    assert sd.support_f1 == 1.0
    assert sd.answer_is_correct
    # score_all
    recs = [
        {
            "qid": "2hop__t1",
            "hop_prefix": "2hop",
            "hop_count": 2,
            "gold_answers": ["Miquette Giraudy"],
            "gold_support_idxs": [5, 10],
            "generated_answer": "Miquette Giraudy",
            "predicted_support_idxs": [5, 10],
            "retrieved_para_idxs": [5, 10, 3, 7],
        },
        {
            "qid": "3hop1__t1",
            "hop_prefix": "3hop1",
            "hop_count": 3,
            "gold_answers": ["London"],
            "gold_support_idxs": [1, 4, 8],
            "generated_answer": "Paris",
            "predicted_support_idxs": [1, 4],
            "retrieved_para_idxs": [1, 4, 2, 7],
        },
    ]
    agg = score_all(recs)
    assert agg.n_scored == 2
    assert 0 < agg.answer_f1 < 1.0
    assert "2hop" in agg.per_hop
    assert "3hop1" in agg.per_hop
    print(f"OK scorer self-test passed (n_scored={agg.n_scored}, "
          f"answer_f1={agg.answer_f1:.3f}, support_f1={agg.support_f1:.3f})")


if __name__ == "__main__":
    _self_test()
