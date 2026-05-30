"""
corpus_loader.py — HotPotQA dataset loader (distractor setting).

HotPotQA paper: Yang et al. 2018, arxiv:1809.09600.
Dataset: https://hotpotqa.github.io/wiki-readme.html

Distractor setting (standard eval config):
    - For each question, 10 paragraphs are provided (`context` field).
    - 2 of those paragraphs are "supporting facts" (gold).
    - 8 are "distractors" pulled from Wikipedia.
    - The model must (a) retrieve the right supporting facts AND (b) read them
      to answer the question — hence "multi-hop".

Record shape (dev-distractor, JSON array of objects):
    {
      "_id": "<hex>",                    # question_id
      "answer": "<short string>",        # gold answer
      "question": "<question text>",
      "type": "comparison" | "bridge",   # multi-hop type
      "level": "easy" | "medium" | "hard",
      "context": [                       # 10 paragraphs (distractor setting)
        ["<title>", ["<sentence_0>", "<sentence_1>", ...]],
        ...
      ],
      "supporting_facts": [              # list of (title, sentence_idx) gold
        ["<title>", <sent_idx_int>],
        ...
      ]
    }

We expose:
    HotpotQuestion dataclass (clean view of one question)
    load_questions(path) -> list[HotpotQuestion]
    paragraph_text(question, title) -> joined sentences for a paragraph title
    gold_supporting_sentences(question) -> list of (title, sent_idx, text)

Shared loader canonical pattern (per [[shared-loader-canonical-pattern]]):
    Adapters MUST use this loader — never implement adapter-specific parsing.
    Tests verify that the parsed structure matches the reference dev set.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class HotpotQuestion:
    question_id: str
    question: str
    answer: str
    type: str            # "comparison" | "bridge"
    level: str           # "easy" | "medium" | "hard"
    paragraphs: list[tuple[str, list[str]]]            # [(title, [sentences])]
    supporting_facts: list[tuple[str, int]]            # [(title, sent_idx)]

    @property
    def gold_titles(self) -> set[str]:
        return {t for t, _ in self.supporting_facts}


def load_questions(path: Path | str) -> list[HotpotQuestion]:
    """Load HotPotQA dev-distractor JSON file.

    Validates record shape; skips malformed records with a stderr note.
    Accepts both single-file array and JSON-lines for forward-compat.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"HotPotQA dataset not found: {p}")

    text = p.read_text(encoding="utf-8")
    # Try JSON array first (standard distribution format)
    try:
        raw = json.loads(text)
        if not isinstance(raw, list):
            raise ValueError(f"expected top-level JSON array in {p}, got {type(raw).__name__}")
    except json.JSONDecodeError:
        # Fallback: JSONL
        raw = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                raw.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    out: list[HotpotQuestion] = []
    for r in raw:
        if not isinstance(r, dict):
            continue
        qid = r.get("_id") or r.get("id")
        question = r.get("question")
        answer = r.get("answer")
        ctx = r.get("context") or []
        sf = r.get("supporting_facts") or []
        if not qid or not question or answer is None:
            continue
        # Normalize context paragraphs
        paragraphs: list[tuple[str, list[str]]] = []
        for entry in ctx:
            if not isinstance(entry, list) or len(entry) < 2:
                continue
            title = str(entry[0])
            sents = entry[1] if isinstance(entry[1], list) else []
            paragraphs.append((title, [str(s) for s in sents]))
        # Normalize supporting_facts
        sf_norm: list[tuple[str, int]] = []
        for entry in sf:
            if not isinstance(entry, list) or len(entry) < 2:
                continue
            try:
                sf_norm.append((str(entry[0]), int(entry[1])))
            except (TypeError, ValueError):
                continue
        out.append(HotpotQuestion(
            question_id=str(qid),
            question=str(question),
            answer=str(answer),
            type=str(r.get("type") or ""),
            level=str(r.get("level") or ""),
            paragraphs=paragraphs,
            supporting_facts=sf_norm,
        ))
    return out


def paragraph_text(q: HotpotQuestion, title: str) -> Optional[str]:
    """Return joined sentence text for paragraph `title` in question, or None if missing."""
    for t, sents in q.paragraphs:
        if t == title:
            return " ".join(sents)
    return None


def gold_supporting_sentences(q: HotpotQuestion) -> list[tuple[str, int, str]]:
    """Return (title, sent_idx, sentence_text) tuples for gold supporting facts."""
    out: list[tuple[str, int, str]] = []
    by_title: dict[str, list[str]] = {t: sents for t, sents in q.paragraphs}
    for title, idx in q.supporting_facts:
        sents = by_title.get(title)
        if not sents or idx < 0 or idx >= len(sents):
            continue
        out.append((title, idx, sents[idx]))
    return out


def question_to_markdown(q: HotpotQuestion) -> str:
    """Render a HotpotQA question's 10-paragraph distractor pool as ingestable markdown.

    Each paragraph becomes an H2 block with title in the header and full text body.
    Embedded `paragraph_title:` metadata line lets the chunker and reranker re-bind
    to the paragraph identity if H2 splits.

    Note: we deliberately do NOT include the gold supporting_facts marker in the
    text — that would leak gold during retrieval. The harness scorer matches by
    paragraph title independently.
    """
    lines: list[str] = [
        f"# HotPotQA question_id={q.question_id} type={q.type} level={q.level}\n"
    ]
    for title, sents in q.paragraphs:
        body = " ".join(sents).strip()
        if not body:
            continue
        # Sanitize H2 title: strip control chars, collapse whitespace
        safe_title = " ".join(title.split())
        lines.append(f"## {safe_title}\n")
        lines.append(f"paragraph_title: {safe_title}\n")
        lines.append(f"{body}\n")
    return "\n".join(lines)
