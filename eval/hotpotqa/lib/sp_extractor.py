"""
sp_extractor.py — LLM-based supporting-fact extractor for HotPotQA.

Replaces the token-overlap heuristic in adapter_nox_mem.py when
``--sp-llm-extractor`` flag is enabled.

Design
------
Input:
    question   : str
    answer     : str
    paragraphs : list of (title, sentences) — the retrieved paragraphs,
                 sentences already split (sentence_id == position in list)

Output:
    list of [title, sentence_id] — predicted supporting facts

Approach:
    1.  Build a numbered-sentence view of each retrieved paragraph.
    2.  Call gpt-4.1-mini with a structured-output prompt asking which
        sentences are *necessary* to arrive at the answer.
    3.  Parse the JSON array response, validate titles + sent_ids, return.

The model receives a token-counted, truncated view so latency stays ≤1s
per query on average (short paragraphs; 5–15 sentences typical).

Cost estimate (full 7405-question bench):
    ~400 tokens/call average × 7405 = ~3M tokens
    gpt-4.1-mini input  $0.40/1M  → ~$1.20
    gpt-4.1-mini output $1.60/1M  × ~30 tok/call → ~$0.36
    Total                          ≈ $1.56  (well within $3 gate)

Latency estimate per question:
    gpt-4.1-mini typical p50 ~300–500ms at small token counts.
    Overhead above retrieval: ~+0.4s/query (within ≤1s gate).

Fallback:
    If the LLM call errors (network, parse failure, timeout), the caller
    falls back to the original token-overlap heuristic — no hard failure.
"""
from __future__ import annotations

import json
import re
import time
import urllib.request
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = "gpt-4.1-mini"
DEFAULT_TIMEOUT = 20  # seconds per call
MAX_SENT_LEN = 300    # chars truncation per sentence (keep tokens tight)
MAX_SENTS_PER_PARA = 12  # cap paragraph to 12 sentences for prompt size

# System prompt: concise instruction, JSON-output contract.
_SYSTEM = (
    "You are a supporting-fact extractor for the HotPotQA benchmark.\n"
    "Given a question, the final answer, and a set of numbered sentences from "
    "retrieved paragraphs, identify which sentences are NECESSARY to support "
    "or derive the answer.\n"
    "Rules:\n"
    "- Only select sentences from the provided paragraphs.\n"
    "- Select the minimum set of sentences that, together, suffice to answer "
    "the question.\n"
    "- Prefer specific, fact-bearing sentences over background/intro sentences.\n"
    "- Output ONLY a JSON array, no explanations:\n"
    '  [{"title": "<paragraph title>", "sentence_id": <int>}, ...]\n'
    "- If no sentences are relevant, output: []"
)


# ---------------------------------------------------------------------------
# Paragraph → numbered-sentence text
# ---------------------------------------------------------------------------

def _truncate(s: str, max_chars: int = MAX_SENT_LEN) -> str:
    s = s.strip()
    return s[:max_chars] + "…" if len(s) > max_chars else s


def format_paragraphs_for_prompt(
    paragraphs: list[tuple[str, list[str]]],
) -> str:
    """Render (title, sentences) list to a numbered prompt block.

    Each sentence is labelled  [title | sent_id=N].
    Example:
        Paragraph: Iqbal F. Qadir
          [0] Vice-Admiral Iqbal Fazl Quadir (Urdu:…) is a retired admiral…
          [1] He is renowned for his participation in the second war with India…
    """
    parts: list[str] = []
    for title, sents in paragraphs:
        parts.append(f"Paragraph: {title}")
        for i, s in enumerate(sents[:MAX_SENTS_PER_PARA]):
            parts.append(f"  [{i}] {_truncate(s)}")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Chunk text → (title, sentences) list
# ---------------------------------------------------------------------------

_PARA_TITLE_RE = re.compile(r"^paragraph_title:\s*(.+?)\s*$", re.MULTILINE)
_H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
# Sentence split: split on ". " or ".\n" while avoiding abbreviations crudely.
_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _title_from_chunk(chunk_text: str) -> str:
    m = _PARA_TITLE_RE.search(chunk_text)
    if m:
        return m.group(1).strip()
    m = _H2_RE.search(chunk_text)
    if m:
        return m.group(1).strip()
    return ""


def _body_from_chunk(chunk_text: str) -> str:
    """Strip markdown headers + paragraph_title: marker from chunk text."""
    lines = chunk_text.splitlines()
    body_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        # Skip H1/H2 headers
        if stripped.startswith("## ") or stripped.startswith("# "):
            continue
        # Skip paragraph_title: marker
        if stripped.startswith("paragraph_title:"):
            continue
        body_lines.append(line)
    return "\n".join(body_lines).strip()


def chunks_to_paragraphs(
    chunk_texts: list[str],
    paragraph_titles: list[str],
) -> list[tuple[str, list[str]]]:
    """Convert retrieved chunk texts to (title, sentences) pairs.

    We use the paragraph_titles already extracted by the adapter to avoid
    re-parsing.  Sentences are split from the chunk body.

    The HotPotQA gold SP format uses sentence_id = position in the ORIGINAL
    paragraph's sentence list.  Since we're splitting the retrieved chunk text
    (which is the full paragraph), the positions should align.
    """
    paragraphs: list[tuple[str, list[str]]] = []
    seen_titles: set[str] = set()
    for i, chunk_text in enumerate(chunk_texts):
        title = paragraph_titles[i] if i < len(paragraph_titles) else _title_from_chunk(chunk_text)
        if not title or title in seen_titles:
            continue
        seen_titles.add(title)
        body = _body_from_chunk(chunk_text)
        # Sentence split
        raw_sents = _SENT_SPLIT_RE.split(body)
        sents: list[str] = [s.strip() for s in raw_sents if s.strip()]
        if not sents:
            sents = [body[:200]] if body else []
        paragraphs.append((title, sents))
    return paragraphs


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------

def _call_llm(
    prompt: str,
    api_key: str,
    model: str = DEFAULT_MODEL,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[str, float, Optional[str]]:
    """Call OpenAI chat completions. Returns (raw_text, latency_ms, error)."""
    body = json.dumps({
        "model": model,
        "temperature": 0,
        "max_tokens": 256,
        "messages": [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": prompt},
        ],
    }).encode("utf-8")
    req = urllib.request.Request(
        OPENAI_URL,
        data=body,
        headers={
            "content-type": "application/json",
            "authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            j = json.loads(r.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        return "", (time.time() - t0) * 1000.0, f"{type(e).__name__}: {e}"
    ms = (time.time() - t0) * 1000.0
    txt = (j.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""
    return txt.strip(), ms, None


# ---------------------------------------------------------------------------
# JSON response parsing
# ---------------------------------------------------------------------------

_JSON_ARRAY_RE = re.compile(r"\[.*?\]", re.DOTALL)


def _parse_sp_response(
    raw: str,
    valid_titles: set[str],
) -> list[list]:
    """Parse LLM JSON output → [[title, sent_id], ...].

    Tolerant: extracts first JSON array from response, validates fields.
    """
    # Try direct parse first
    stripped = raw.strip()
    # Extract first JSON array if surrounded by prose
    m = _JSON_ARRAY_RE.search(stripped)
    if not m:
        return []
    try:
        arr = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    if not isinstance(arr, list):
        return []
    result: list[list] = []
    seen: set[tuple[str, int]] = set()
    for item in arr:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "") or "")
        sent_id_raw = item.get("sentence_id")
        if sent_id_raw is None:
            # Try alternative keys
            sent_id_raw = item.get("sent_id") or item.get("id") or item.get("idx")
        if sent_id_raw is None:
            continue
        try:
            sent_id = int(sent_id_raw)
        except (TypeError, ValueError):
            continue
        if sent_id < 0:
            continue
        # Accept title even if not in valid_titles (minor title mismatch)
        # — the scorer does exact string match so wrong titles score 0 anyway.
        key = (title, sent_id)
        if key in seen:
            continue
        seen.add(key)
        result.append([title, sent_id])
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_supporting_facts(
    question: str,
    answer: str,
    chunk_texts: list[str],
    paragraph_titles: list[str],
    api_key: str,
    model: str = DEFAULT_MODEL,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[list[list], float, Optional[str]]:
    """Extract supporting facts via LLM.

    Returns:
        (supporting_facts, latency_ms, error_or_None)
        supporting_facts: [[title, sent_id], ...]

    On error returns ([], latency_ms, error_str) — caller falls back to
    token-overlap heuristic.
    """
    paragraphs = chunks_to_paragraphs(chunk_texts, paragraph_titles)
    if not paragraphs:
        return [], 0.0, "no paragraphs extracted from chunks"

    valid_titles = {t for t, _ in paragraphs}
    para_block = format_paragraphs_for_prompt(paragraphs)

    user_prompt = (
        f"Question: {question}\n"
        f"Answer: {answer}\n\n"
        f"Paragraphs:\n{para_block}\n\n"
        "Which sentences are necessary to support the answer? "
        "Output JSON array only."
    )

    raw, ms, err = _call_llm(user_prompt, api_key, model=model, timeout=timeout)
    if err:
        return [], ms, err

    parsed = _parse_sp_response(raw, valid_titles)
    return parsed, ms, None
