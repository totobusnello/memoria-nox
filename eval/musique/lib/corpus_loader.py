"""
corpus_loader.py — MuSiQue paragraphs → nox-mem markdown chunks.

Loads `musique_ans_v1.0_dev.jsonl` (or _full_dev.jsonl) from the official
MuSiQue release (Trivedi et al. 2022, arxiv:2108.00573, github:StonyBrookNLP/musique)
and renders each question's paragraph set as markdown ready for `nox-mem ingest`.

MuSiQue schema (verified 2026-05-29 from /tmp/musique-repo/data/musique_ans_v1.0_dev.jsonl):
  - top-level: jsonl, one question per line
  - per question keys: ["id", "paragraphs", "question",
                        "question_decomposition", "answer", "answer_aliases",
                        "answerable"]
  - id format: "{hop}__{seed_id1}_{seed_id2}..." — hop ∈ {2hop, 3hop1, 3hop2,
                4hop1, 4hop2, 4hop3} (variants encode decomposition topology)
  - paragraphs = list[{idx, title, paragraph_text, is_supporting}] — always 20
  - question_decomposition = list of single-hop sub-questions w/
                              paragraph_support_idx pointer
  - answer + answer_aliases used by metric_max_over_ground_truths
  - answerable: bool — False ONLY in musique_full (unanswerable variants).
                For musique_ans dev, all answerable=True.

Critical architectural decision (mirror EverMemBench / LongMemEval):
  MuSiQue ingestion is **per-question** (each question has its OWN 20-paragraph
  corpus, disjoint from other questions). NOT per-conversation (LoCoMo) and
  NOT corpus-wide (LongMemEval style). This means:
    - One isolated DB per question — pure but slow (~2417 DBs in dev set).
    - OR: one DB per question reusing the SAME on-disk file (drop + bootstrap
      between questions) — faster, what we'll do.

The 20 paragraphs/question include `is_supporting: True` for the gold
paragraphs (typically 2-4 paragraphs, matching the hop count). The rest are
distractors selected by the MuSiQue authors to be confusable (same surface
keywords, different entity), making single-shot retrieval HARD.

Hop distribution (musique_ans_v1.0_dev.jsonl, n=2417):
  - 2hop:   1252 (51.8%)
  - 3hop1:   568 (23.5%)
  - 3hop2:   192 (7.9%)
  - 4hop1:   246 (10.2%)
  - 4hop2:    64 (2.6%)
  - 4hop3:    95 (3.9%)

Public exports:
  - load_questions(jsonl_path) -> list[Question]
  - render_paragraph_md(question, paragraph) -> str
  - write_question_md_files(question, out_dir) -> list[Path]
  - HOP_CATEGORIES

This loader is the SINGLE SOURCE OF TRUTH for MuSiQue data shape (per the
"shared corpus_loader canonical pattern" lesson cravada Sat 2026-05-24).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator


# ---------------------------------------------------------------------------
# Hop categorisation
# ---------------------------------------------------------------------------

HOP_CATEGORIES: dict[str, int] = {
    "2hop":  2,
    "3hop1": 3,
    "3hop2": 3,
    "4hop1": 4,
    "4hop2": 4,
    "4hop3": 4,
}


def hop_count_from_id(qid: str) -> int:
    """
    Extract canonical hop count from MuSiQue id like '2hop__460946_294723',
    '3hop1__a_b_c', '4hop3__a_b_c_d'.
    Returns 0 if pattern not matched.
    """
    if not qid:
        return 0
    prefix = qid.split("__", 1)[0]
    return HOP_CATEGORIES.get(prefix, 0)


def hop_prefix_from_id(qid: str) -> str:
    if not qid:
        return "unknown"
    return qid.split("__", 1)[0]


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------

@dataclass
class Paragraph:
    idx: int               # 0-19, matches MuSiQue paragraph.idx
    title: str
    text: str              # MuSiQue 'paragraph_text'
    is_supporting: bool


@dataclass
class DecompositionStep:
    """One single-hop step from `question_decomposition`."""
    step_id: int           # seed id from original single-hop dataset
    sub_question: str      # raw '#1 >> spouse' style
    sub_answer: str
    support_idx: int       # paragraph idx where this sub-q is grounded


@dataclass
class Question:
    qid: str               # e.g. "2hop__460946_294723"
    question: str
    answer: str
    answer_aliases: list[str]
    answerable: bool
    paragraphs: list[Paragraph]
    decomposition: list[DecompositionStep] = field(default_factory=list)
    hop_prefix: str = ""   # e.g. "2hop", "3hop1", etc.
    hop_count: int = 0     # 2/3/4

    @property
    def supporting_idxs(self) -> list[int]:
        return [p.idx for p in self.paragraphs if p.is_supporting]

    @property
    def all_answers(self) -> list[str]:
        """List for metric_max_over_ground_truths (answer + aliases, dedup)."""
        out = [self.answer]
        for a in self.answer_aliases:
            if a and a not in out:
                out.append(a)
        return out


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def load_questions(jsonl_path: str | Path) -> list[Question]:
    """
    Parse musique_(ans|full)_v1.0_dev.jsonl into Question records.

    Raises FileNotFoundError if jsonl_path missing.
    Returns list[Question] preserving dataset order.
    """
    p = Path(jsonl_path)
    if not p.exists():
        raise FileNotFoundError(f"MuSiQue dataset not found: {p}")

    out: list[Question] = []
    with p.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                j = json.loads(line)
            except Exception:
                continue
            qid = str(j.get("id", f"line{line_no}"))
            paragraphs: list[Paragraph] = []
            for p_raw in (j.get("paragraphs") or []):
                if not isinstance(p_raw, dict):
                    continue
                paragraphs.append(
                    Paragraph(
                        idx=int(p_raw.get("idx", 0)),
                        title=str(p_raw.get("title", "")),
                        text=str(p_raw.get("paragraph_text", "")),
                        is_supporting=bool(p_raw.get("is_supporting", False)),
                    )
                )
            decomposition: list[DecompositionStep] = []
            for d_raw in (j.get("question_decomposition") or []):
                if not isinstance(d_raw, dict):
                    continue
                decomposition.append(
                    DecompositionStep(
                        step_id=int(d_raw.get("id", 0)),
                        sub_question=str(d_raw.get("question", "")),
                        sub_answer=str(d_raw.get("answer", "")),
                        support_idx=int(d_raw.get("paragraph_support_idx", -1) or -1),
                    )
                )
            ans_aliases = j.get("answer_aliases") or []
            if not isinstance(ans_aliases, list):
                ans_aliases = []
            out.append(
                Question(
                    qid=qid,
                    question=str(j.get("question", "")).strip(),
                    answer=str(j.get("answer", "")),
                    answer_aliases=[str(a) for a in ans_aliases],
                    answerable=bool(j.get("answerable", True)),
                    paragraphs=paragraphs,
                    decomposition=decomposition,
                    hop_prefix=hop_prefix_from_id(qid),
                    hop_count=hop_count_from_id(qid),
                )
            )
    return out


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------

PARAGRAPH_MD_TEMPLATE = """# MuSiQue {qid} paragraph {idx}

qid: {qid}
paragraph_idx: {idx}
title: {title}
is_supporting: {is_supporting}

## Content

para_idx: {idx} | qid: {qid} | title: {title}

{text}
"""


def _sanitize_filename(s: str) -> str:
    """Safe filename: replace non-alnum with underscore."""
    return re.sub(r"[^A-Za-z0-9._-]", "_", s)[:120]


def render_paragraph_md(question: Question, paragraph: Paragraph) -> str:
    """
    Render one MuSiQue paragraph as a markdown file for `nox-mem ingest`.

    Embeds per-paragraph `para_idx` and `qid` markers so that even if nox-mem
    chunker splits the paragraph across boundaries, the para_idx survives in
    each chunk_text (parsed back by the scorer for is_supporting matching).

    Single paragraphs are short enough (~100-500 words) that they typically
    fit in 1-2 nox-mem chunks.
    """
    safe_title = paragraph.title.replace("\r\n", "\n").replace("\r", "\n")
    safe_text = paragraph.text.replace("\r\n", "\n").replace("\r", "\n")
    return PARAGRAPH_MD_TEMPLATE.format(
        qid=question.qid,
        idx=paragraph.idx,
        title=safe_title,
        is_supporting=paragraph.is_supporting,
        text=safe_text,
    )


def write_question_md_files(question: Question, out_dir: Path) -> list[Path]:
    """
    Write one .md file per paragraph of the question into out_dir.
    Files named `{qid}_p{idx:02d}.md`.

    Returns the list of file paths in paragraph-idx order.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_qid = _sanitize_filename(question.qid)
    paths: list[Path] = []
    # Sort by idx to ensure deterministic order
    for p in sorted(question.paragraphs, key=lambda x: x.idx):
        fpath = out_dir / f"{safe_qid}_p{p.idx:02d}.md"
        fpath.write_text(render_paragraph_md(question, p), encoding="utf-8")
        paths.append(fpath)
    return paths


def iter_questions(jsonl_path: str | Path) -> Iterator[Question]:
    yield from load_questions(jsonl_path)


# ---------------------------------------------------------------------------
# Self-test (smoke)
# ---------------------------------------------------------------------------

def _self_test(jsonl_path: str | Path) -> None:
    qs = load_questions(jsonl_path)
    assert len(qs) > 0, f"expected questions, got 0 from {jsonl_path}"
    from collections import Counter

    hop_counts: Counter = Counter()
    para_counts: Counter = Counter()
    sup_counts: Counter = Counter()
    for q in qs:
        hop_counts[q.hop_prefix] += 1
        para_counts[len(q.paragraphs)] += 1
        sup_counts[len(q.supporting_idxs)] += 1
    print(f"OK: n_questions={len(qs)}")
    print(f"  hop distribution: {dict(hop_counts)}")
    print(f"  paragraphs per Q: {dict(para_counts)}")
    print(f"  supporting per Q: {dict(sup_counts)}")
    # Render a sample paragraph
    q0 = qs[0]
    p0 = q0.paragraphs[0]
    md = render_paragraph_md(q0, p0)
    print(f"---sample paragraph md (first {min(400, len(md))} chars)---")
    print(md[:400])
    # Sanity: first question hop_count present
    assert q0.hop_count in (2, 3, 4), f"unexpected hop_count: {q0.hop_count}"
    assert q0.supporting_idxs, "expected supporting paragraphs"


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--jsonl",
        default="/tmp/musique-repo/data/musique_ans_v1.0_dev.jsonl",
    )
    args = ap.parse_args()
    _self_test(args.jsonl)
