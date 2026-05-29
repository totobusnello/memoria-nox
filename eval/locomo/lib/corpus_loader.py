"""
corpus_loader.py — LoCoMo conversation → nox-mem markdown chunks.

Loads `data/locomo10.json` (snap-research/LoCoMo official dataset, n=10
multi-session dialogues with ~588 turns/conv) and renders each session as
a markdown file ready for `nox-mem ingest`.

LoCoMo schema (verified 2026-05-29 from /tmp/locomo-repo/data/locomo10.json):
  - top-level: list[dict], len=10
  - per item keys: ["qa", "conversation", "event_summary", "observation",
                    "session_summary", "sample_id"]
  - conversation = {speaker_a, speaker_b,
                    session_1, session_1_date_time,
                    session_2, session_2_date_time, ...}
  - session_N = list[{speaker, dia_id, text}]  (dia_id like "D1:3")
  - qa = list[{question, answer, evidence, category}]
  - category: 1=multi-hop, 2=temporal, 3=commonsense, 4=single-hop, 5=adversarial
  - evidence: list[str] of dia_id refs like ["D1:3"]

Canonical category mapping (from /tmp/locomo-repo/task_eval/{evaluation,gpt_utils}.py):

  | int | name               | scoring                                 |
  |-----|--------------------|-----------------------------------------|
  |  1  | multi-hop          | F1 with sub-answer split (semicolon)    |
  |  2  | temporal           | F1, question augmented w/ "Use DATE..." |
  |  3  | commonsense        | F1, answer pre-split by ';'             |
  |  4  | single-hop         | F1                                      |
  |  5  | adversarial        | refuse-correct (output = "no info...")  |

Public exports:
  - load_conversations(json_path) -> list[Conversation]
  - render_session_md(conv, session_index) -> str
  - write_conversation_md_files(conv, out_dir) -> list[Path]
  - iter_qa(conv) -> Iterator[QAPair]
  - CATEGORY_NAMES, CATEGORY_BY_NAME

This loader is the SINGLE SOURCE OF TRUTH for LoCoMo data shape. Adapter and
scorer MUST consume from here (per "shared corpus_loader canonical pattern"
lesson cravada Sat 2026-05-24).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator


# ---------------------------------------------------------------------------
# Category mapping (LoCoMo paper Table 1 + repo task_eval/evaluation.py)
# ---------------------------------------------------------------------------

CATEGORY_NAMES: dict[int, str] = {
    1: "multi_hop",
    2: "temporal",
    3: "commonsense",
    4: "single_hop",
    5: "adversarial",
}
CATEGORY_BY_NAME: dict[str, int] = {v: k for k, v in CATEGORY_NAMES.items()}


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------

@dataclass
class Turn:
    speaker: str
    dia_id: str       # e.g. "D1:3"
    text: str
    session_id: str   # e.g. "session_1"
    session_index: int

    @property
    def session_number(self) -> int:
        # Parse "D1:3" → 1
        m = re.match(r"D(\d+):", self.dia_id)
        return int(m.group(1)) if m else self.session_index


@dataclass
class Session:
    session_id: str           # "session_1"
    session_index: int        # 1-based
    date_time: str            # raw string from dataset
    turns: list[Turn]
    observation: str = ""     # auto-generated observations (per-session)
    summary: str = ""         # auto-generated summary (per-session)


@dataclass
class QAPair:
    question: str
    answer: str               # string (may be empty for adversarial)
    evidence: list[str]       # list of dia_id refs
    category: int             # 1..5
    category_name: str        # derived
    qa_index: int             # 0-based within conversation
    sample_id: str            # parent conversation id (e.g. "conv-26")
    augmented_question: str = ""  # question after category-specific augmentation


@dataclass
class Conversation:
    sample_id: str            # "conv-26"
    speaker_a: str
    speaker_b: str
    sessions: list[Session] = field(default_factory=list)
    qa_pairs: list[QAPair] = field(default_factory=list)

    @property
    def total_turns(self) -> int:
        return sum(len(s.turns) for s in self.sessions)


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

_SESSION_KEY_RE = re.compile(r"^session_(\d+)$")
_SESSION_DATE_RE = re.compile(r"^session_(\d+)_date_time$")
_OBSERVATION_RE = re.compile(r"^session_(\d+)_observation$")
_SUMMARY_RE = re.compile(r"^session_(\d+)_summary$")


def _stringify(v: object) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, list):
        return " ".join(_stringify(x) for x in v)
    if isinstance(v, dict):
        return json.dumps(v, ensure_ascii=False)
    return str(v)


def _augment_question(category: int, question: str, answer: str) -> str:
    """
    Mirror LoCoMo paper's category-specific question augmentation
    (from /tmp/locomo-repo/task_eval/gpt_utils.py).

    Cat 2 (temporal): add 'Use DATE of CONVERSATION to answer with an approximate date.'
    Cat 5 (adversarial): we do NOT randomly pick MCQ (a)/(b) here because that
        adds RNG that distorts cross-bench comparability. Instead, we tell the
        model to answer or say "Not mentioned in the conversation". The scorer
        then checks for refusal substrings.
    Other cats: pass through.
    """
    q = question.strip()
    if category == 2:
        return q + " Use DATE of CONVERSATION to answer with an approximate date."
    if category == 5:
        # Deterministic refuse-correct hint
        return (
            q
            + " Based ONLY on the retrieved memory, answer concisely. "
            "If the memory does not contain the answer, reply exactly with: "
            "Not mentioned in the conversation."
        )
    return q


def load_conversations(json_path: str | Path) -> list[Conversation]:
    """
    Parse locomo10.json into Conversation records.

    Raises FileNotFoundError if json_path missing.
    Returns a list[Conversation] in dataset order.
    """
    p = Path(json_path)
    with p.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, list):
        raise ValueError(f"expected JSON array at {p}, got {type(raw).__name__}")

    out: list[Conversation] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        sample_id = str(item.get("sample_id", "?"))
        conv_dict = item.get("conversation") or {}
        speaker_a = str(conv_dict.get("speaker_a", "Speaker A"))
        speaker_b = str(conv_dict.get("speaker_b", "Speaker B"))
        # First pass: collect session number -> turns
        sessions_by_idx: dict[int, dict] = {}
        for key, val in conv_dict.items():
            m_s = _SESSION_KEY_RE.match(key)
            m_d = _SESSION_DATE_RE.match(key)
            if m_s:
                idx = int(m_s.group(1))
                sess = sessions_by_idx.setdefault(idx, {"turns": [], "date_time": ""})
                if isinstance(val, list):
                    sess["turns"] = val
            elif m_d:
                idx = int(m_d.group(1))
                sess = sessions_by_idx.setdefault(idx, {"turns": [], "date_time": ""})
                sess["date_time"] = _stringify(val)

        # Observations + summaries (separate top-level dicts)
        obs_dict = item.get("observation") or {}
        sum_dict = item.get("session_summary") or {}
        observations_by_idx: dict[int, str] = {}
        summaries_by_idx: dict[int, str] = {}
        for k, v in (obs_dict.items() if isinstance(obs_dict, dict) else []):
            m = _OBSERVATION_RE.match(str(k))
            if m:
                observations_by_idx[int(m.group(1))] = _stringify(v)
        for k, v in (sum_dict.items() if isinstance(sum_dict, dict) else []):
            m = _SUMMARY_RE.match(str(k))
            if m:
                summaries_by_idx[int(m.group(1))] = _stringify(v)

        sessions: list[Session] = []
        for idx in sorted(sessions_by_idx.keys()):
            raw_turns = sessions_by_idx[idx]["turns"]
            sid = f"session_{idx}"
            turns: list[Turn] = []
            for t in raw_turns:
                if not isinstance(t, dict):
                    continue
                turns.append(
                    Turn(
                        speaker=str(t.get("speaker", "")),
                        dia_id=str(t.get("dia_id", "")),
                        text=str(t.get("text", "")),
                        session_id=sid,
                        session_index=idx,
                    )
                )
            sessions.append(
                Session(
                    session_id=sid,
                    session_index=idx,
                    date_time=str(sessions_by_idx[idx]["date_time"]),
                    turns=turns,
                    observation=observations_by_idx.get(idx, ""),
                    summary=summaries_by_idx.get(idx, ""),
                )
            )

        qa_pairs: list[QAPair] = []
        for qi, q in enumerate(item.get("qa") or []):
            if not isinstance(q, dict):
                continue
            cat_raw = q.get("category")
            try:
                cat_int = int(cat_raw)
            except Exception:
                cat_int = 0
            cat_name = CATEGORY_NAMES.get(cat_int, "unknown")
            ans_val = q.get("answer", "")
            ans_str = "" if ans_val is None else str(ans_val)
            question_str = str(q.get("question", "")).strip()
            qa_pairs.append(
                QAPair(
                    question=question_str,
                    answer=ans_str,
                    evidence=[str(e) for e in (q.get("evidence") or [])],
                    category=cat_int,
                    category_name=cat_name,
                    qa_index=qi,
                    sample_id=sample_id,
                    augmented_question=_augment_question(cat_int, question_str, ans_str),
                )
            )

        out.append(
            Conversation(
                sample_id=sample_id,
                speaker_a=speaker_a,
                speaker_b=speaker_b,
                sessions=sessions,
                qa_pairs=qa_pairs,
            )
        )
    return out


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------

SESSION_MD_TEMPLATE = """# LoCoMo {sample_id} {session_id}

sample_id: {sample_id}
session_id: {session_id}
session_index: {session_index}
date: {date}
speakers: {speaker_a}, {speaker_b}

## Conversation

{turns}
"""

TURN_MD_TEMPLATE = (
    "### {speaker} (dia_id: {dia_id})\n\n"
    "sample_id: {sample_id} | session_id: {session_id} | dia_id: {dia_id}\n"
    "{text}\n"
)


def render_session_md(conv: Conversation, session: Session) -> str:
    """
    Render one session as a markdown file for `nox-mem ingest`.

    Embeds per-turn `dia_id` markers so that even if nox-mem chunker splits
    the session across boundaries, the dia_id survives in each chunk_text
    (parsed back by the scorer for evidence matching).
    """
    turns_md_parts: list[str] = []
    for t in session.turns:
        if not t.text:
            continue
        turns_md_parts.append(
            TURN_MD_TEMPLATE.format(
                speaker=t.speaker or "?",
                dia_id=t.dia_id,
                sample_id=conv.sample_id,
                session_id=session.session_id,
                text=t.text.replace("\r\n", "\n").replace("\r", "\n"),
            )
        )
    turns_md = "\n".join(turns_md_parts).rstrip() or "(empty session)"
    return SESSION_MD_TEMPLATE.format(
        sample_id=conv.sample_id,
        session_id=session.session_id,
        session_index=session.session_index,
        date=session.date_time or "?",
        speaker_a=conv.speaker_a,
        speaker_b=conv.speaker_b,
        turns=turns_md,
    )


def write_conversation_md_files(conv: Conversation, out_dir: Path) -> list[Path]:
    """
    Write one .md file per session of the conversation into out_dir.
    Files named `{sample_id}_{session_id}.md`.

    Returns the list of file paths in session order.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for s in conv.sessions:
        fpath = out_dir / f"{conv.sample_id}_{s.session_id}.md"
        fpath.write_text(render_session_md(conv, s), encoding="utf-8")
        paths.append(fpath)
    return paths


def iter_qa(conv: Conversation) -> Iterator[QAPair]:
    yield from conv.qa_pairs


# ---------------------------------------------------------------------------
# Self-test (smoke)
# ---------------------------------------------------------------------------

def _self_test(json_path: str | Path) -> None:
    convs = load_conversations(json_path)
    assert len(convs) == 10, f"expected 10 conversations, got {len(convs)}"
    total_qa = sum(len(c.qa_pairs) for c in convs)
    total_turns = sum(c.total_turns for c in convs)
    from collections import Counter

    cat_counts: Counter = Counter()
    for c in convs:
        for q in c.qa_pairs:
            cat_counts[q.category_name] += 1
    print(f"OK: convs={len(convs)} qa={total_qa} turns={total_turns}")
    print(f"per category: {dict(cat_counts)}")
    # Render one session sample
    md = render_session_md(convs[0], convs[0].sessions[0])
    print(f"---sample session md (first {min(400, len(md))} chars)---")
    print(md[:400])


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="eval/locomo/data/locomo10.json")
    args = ap.parse_args()
    _self_test(args.json)
