"""
temporal_scoring.py — temporal proximity scoring for LoCoMo retrieval re-rank.

Background (PR #404 -> this PR):
  PR #404 reached LoCoMo temporal F1 44.21% via prompt-level date injection
  (session_date_map for cat=2 + 'D Month YYYY' format hint). Residual gap to
  Mem0 SOTA (66.88% overall, ~66% temporal-equivalent) is partly retrieval-
  side: top-K mixes chunks from many sessions with no preference for chunks
  whose session date matches the query's date intent.

Hypothesis (this module):
  For temporal-class queries, chunks from a session whose date matches the
  query's referenced date should rank higher. Adjacent month/year should
  still rank above unrelated; non-date chunks score 0 and rely on hybrid
  signal alone.

Mechanism (post-retrieval re-rank):
  1. Extract query date intent (regex + 'Use DATE of CONVERSATION...' hint).
  2. Extract chunk date by mapping session_id (parsed from chunk text) to
     canonical date via session_date_map.
  3. Compute temporal_proximity(query_date, chunk_date) in [0, 1].
  4. Blend with original retrieval score:
       final = (1 - alpha) * normalized_retrieval + alpha * temporal_proximity
     Default alpha=0.5 for temporal queries; alpha=0.0 (passthrough) otherwise.

This module is **stateless** and depends only on lib/temporal_normalizer.py.

Public exports:
  - extract_query_dates(query: str) -> list[ParsedDate]
  - extract_chunk_date(chunk_text: str, session_date_map: dict[str, str]) -> ParsedDate | None
  - temporal_proximity(qd: ParsedDate | None, cd: ParsedDate | None) -> float
  - rerank_with_temporal_proximity(...) -> list[ScoredChunk]
  - is_temporal_query(query: str, category_name: str | None = None) -> bool
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

# Allow `import lib.temporal_normalizer` and `from temporal_normalizer ...`
from temporal_normalizer import (  # type: ignore[import-not-found]
    MONTH_ABBR,
    MONTH_BY_NUM,
    MONTH_NAMES,
    parse_session_date,
)


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ParsedDate:
    """A parsed date with optional precision.

    - year is required (only confident dates flow through);
    - month/day may be None when intent is coarser (e.g. "2023" -> year-only,
      "May 2023" -> month-year).
    """
    year: int
    month: Optional[int] = None   # 1..12
    day: Optional[int] = None     # 1..31

    @property
    def precision(self) -> str:
        if self.day is not None and self.month is not None:
            return "day"
        if self.month is not None:
            return "month"
        return "year"

    def canonical(self) -> str:
        """Render canonical 'D Month YYYY' / 'Month YYYY' / 'YYYY'."""
        if self.day is not None and self.month is not None:
            mon = MONTH_BY_NUM.get(self.month, "")
            return f"{self.day} {mon} {self.year}".strip()
        if self.month is not None:
            mon = MONTH_BY_NUM.get(self.month, "")
            return f"{mon} {self.year}".strip()
        return str(self.year)


@dataclass
class ScoredChunk:
    chunk_id: str
    text: str
    original_score: float
    temporal_score: float        # in [0, 1]
    final_score: float           # blended
    parsed_chunk_date: Optional[ParsedDate] = None
    session_id: str = ""
    dia_id: str = ""


# ---------------------------------------------------------------------------
# Query date extraction
# ---------------------------------------------------------------------------

# "Use DATE of CONVERSATION to answer with an approximate date." — LoCoMo
# temporal augmentation. Strip before parsing so we don't false-match "DATE".
_AUG_PREFIX_RE = re.compile(
    r"\s*Use DATE of CONVERSATION to answer with an approximate date\.?\s*$",
    re.IGNORECASE,
)

# Date patterns ordered most-specific first
_PAT_DAY_MONTH_YEAR = re.compile(
    r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+),?\s+(\d{4})\b", re.IGNORECASE,
)
_PAT_MONTH_DAY_YEAR = re.compile(
    r"\b([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b", re.IGNORECASE,
)
_PAT_ISO = re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b")
_PAT_MONTH_YEAR = re.compile(r"\b([A-Za-z]+),?\s+(\d{4})\b", re.IGNORECASE)
_PAT_YEAR_ALONE = re.compile(r"\b(20\d{2}|19\d{2})\b")
_PAT_NUMERIC_SLASH = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")

# Temporal-class trigger keywords (used by is_temporal_query)
_TEMPORAL_KEYWORDS = {
    "when", "date", "year", "month", "day", "week", "hour",
    "before", "after", "during", "while", "since", "until",
    "first", "last", "earliest", "latest", "previously",
    "previous", "next", "earlier", "later",
    "yesterday", "today", "tomorrow",
    "ago", "later",
}


def _month_to_num(token: str) -> Optional[int]:
    t = token.lower().rstrip(".,")
    if not t:
        return None
    for i, m in enumerate(MONTH_NAMES, start=1):
        if m.lower() == t:
            return i
    abbr = MONTH_ABBR.get(t[:4], MONTH_ABBR.get(t[:3]))
    if abbr:
        for i, m in enumerate(MONTH_NAMES, start=1):
            if m == abbr:
                return i
    return None


def _strip_augmentation(query: str) -> str:
    return _AUG_PREFIX_RE.sub("", query or "")


def extract_query_dates(query: str) -> list[ParsedDate]:
    """Extract explicit date references from a LoCoMo query.

    Strategy: scan the original question (post-aug-strip) for date-like
    patterns and return them in source order, deduped by canonical form.
    Returns [] if no explicit date is in the query (most temporal questions
    actually don't carry a date — they ask FOR one).
    """
    if not query:
        return []
    q = _strip_augmentation(query)

    seen: set[str] = set()
    out: list[ParsedDate] = []

    def _emit(pd: Optional[ParsedDate]) -> None:
        if pd is None:
            return
        key = pd.canonical()
        if key in seen:
            return
        seen.add(key)
        out.append(pd)

    # ISO
    for m in _PAT_ISO.finditer(q):
        y = int(m.group(1))
        mo = int(m.group(2))
        d = int(m.group(3))
        if 1 <= mo <= 12 and 1 <= d <= 31 and 1900 <= y <= 2100:
            _emit(ParsedDate(year=y, month=mo, day=d))

    # M/D/YYYY
    for m in _PAT_NUMERIC_SLASH.finditer(q):
        mo = int(m.group(1))
        d = int(m.group(2))
        y = int(m.group(3))
        if 1 <= mo <= 12 and 1 <= d <= 31 and 1900 <= y <= 2100:
            _emit(ParsedDate(year=y, month=mo, day=d))

    # D Month YYYY
    for m in _PAT_DAY_MONTH_YEAR.finditer(q):
        mo = _month_to_num(m.group(2))
        if mo is None:
            continue
        try:
            d = int(m.group(1))
            y = int(m.group(3))
        except ValueError:
            continue
        if 1 <= d <= 31 and 1900 <= y <= 2100:
            _emit(ParsedDate(year=y, month=mo, day=d))

    # Month D, YYYY
    for m in _PAT_MONTH_DAY_YEAR.finditer(q):
        mo = _month_to_num(m.group(1))
        if mo is None:
            continue
        try:
            d = int(m.group(2))
            y = int(m.group(3))
        except ValueError:
            continue
        if 1 <= d <= 31 and 1900 <= y <= 2100:
            _emit(ParsedDate(year=y, month=mo, day=d))

    # Month YYYY (only emit if not already covered by day-level match)
    for m in _PAT_MONTH_YEAR.finditer(q):
        mo = _month_to_num(m.group(1))
        if mo is None:
            continue
        try:
            y = int(m.group(2))
        except ValueError:
            continue
        if 1900 <= y <= 2100:
            # Skip if a day-level emit for same (y, mo) already present
            if any(pd.year == y and pd.month == mo and pd.day is not None for pd in out):
                continue
            _emit(ParsedDate(year=y, month=mo, day=None))

    # Bare year (only if not subsumed by anything above)
    for m in _PAT_YEAR_ALONE.finditer(q):
        try:
            y = int(m.group(1))
        except ValueError:
            continue
        if any(pd.year == y for pd in out):
            continue
        _emit(ParsedDate(year=y, month=None, day=None))

    return out


# ---------------------------------------------------------------------------
# Chunk date extraction
# ---------------------------------------------------------------------------

# Chunks are rendered from corpus_loader.SESSION_MD_TEMPLATE / TURN_MD_TEMPLATE
# Each chunk_text (or sub-chunk after FTS5 split) contains:
#   sample_id: conv-26 | session_id: session_1 | dia_id: D1:3
# We parse session_id first, then look up date in session_date_map. We also
# accept the inline 'date: 1:56 pm on 8 May, 2023' header as a fallback.
_CHUNK_SESSION_RE = re.compile(r"session_id:\s*(session_\d+)")
_CHUNK_DIA_RE = re.compile(r"dia_id:\s*(D(\d+):\d+)")
_CHUNK_DATE_HEADER_RE = re.compile(r"date:\s*([^\n]+)")


def _parsed_date_from_canonical(canonical: str) -> Optional[ParsedDate]:
    """Parse a canonical 'D Month YYYY' / 'Month YYYY' / 'YYYY' back to
    ParsedDate. Returns None on failure."""
    if not canonical:
        return None
    s = canonical.strip()
    # YYYY alone
    m = re.fullmatch(r"(\d{4})", s)
    if m:
        return ParsedDate(year=int(m.group(1)), month=None, day=None)
    # Month YYYY
    m = re.fullmatch(r"([A-Za-z]+)\s+(\d{4})", s)
    if m:
        mo = _month_to_num(m.group(1))
        if mo:
            return ParsedDate(year=int(m.group(2)), month=mo, day=None)
    # D Month YYYY
    m = re.fullmatch(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", s)
    if m:
        mo = _month_to_num(m.group(2))
        if mo:
            d = int(m.group(1))
            if 1 <= d <= 31:
                return ParsedDate(year=int(m.group(3)), month=mo, day=d)
    return None


def extract_chunk_date(
    chunk_text: str,
    session_date_map: dict[str, str] | None,
) -> Optional[ParsedDate]:
    """Resolve a chunk's anchor date.

    Order:
      1. Parse session_id from chunk_text, look up in session_date_map.
      2. Fallback: parse inline 'date: 1:56 pm on 8 May, 2023' header.
      3. Fallback: derive session_id from dia_id (D<N>:K -> session_<N>) and
         look up in session_date_map.
    """
    if not chunk_text:
        return None

    # 1. session_id direct
    if session_date_map:
        m = _CHUNK_SESSION_RE.search(chunk_text)
        if m:
            sid = m.group(1)
            canonical = session_date_map.get(sid)
            if canonical:
                pd = _parsed_date_from_canonical(canonical)
                if pd is not None:
                    return pd

    # 2. Inline date header
    m = _CHUNK_DATE_HEADER_RE.search(chunk_text)
    if m:
        canonical = parse_session_date(m.group(1)) or ""
        pd = _parsed_date_from_canonical(canonical)
        if pd is not None:
            return pd

    # 3. dia_id -> session inference
    if session_date_map:
        m = _CHUNK_DIA_RE.search(chunk_text)
        if m:
            sid = f"session_{m.group(2)}"
            canonical = session_date_map.get(sid)
            if canonical:
                pd = _parsed_date_from_canonical(canonical)
                if pd is not None:
                    return pd

    return None


def extract_chunk_session_and_dia(chunk_text: str) -> tuple[str, str]:
    """Best-effort extraction of (session_id, dia_id) from a chunk."""
    sid = ""
    dia = ""
    if not chunk_text:
        return sid, dia
    m = _CHUNK_SESSION_RE.search(chunk_text)
    if m:
        sid = m.group(1)
    m = _CHUNK_DIA_RE.search(chunk_text)
    if m:
        dia = m.group(1)
        if not sid:
            sid = f"session_{m.group(2)}"
    return sid, dia


# ---------------------------------------------------------------------------
# Temporal proximity
# ---------------------------------------------------------------------------

# Tunable scoring constants (changed only after smoke ablation)
SCORE_EXACT_DAY = 1.0
SCORE_SAME_MONTH = 0.85
SCORE_ADJACENT_MONTH = 0.7
SCORE_SAME_YEAR = 0.45
SCORE_ADJACENT_YEAR = 0.3
SCORE_NO_CHUNK_DATE = 0.0
SCORE_NO_QUERY_DATE = 0.0

# For temporal queries WITHOUT an explicit date in the query (~87% of LoCoMo
# temporal cat — questions like "When did X happen?"), we still want to
# prefer chunks that have a session anchor over unanchored chunks (date
# answers must come from anchored chunks). This is a "soft" temporal
# preference applied when activate=True but query_dates=[].
SCORE_HAS_DATE_FALLBACK = 0.6
SCORE_NO_DATE_FALLBACK = 0.0


def _ym_index(pd: ParsedDate) -> int:
    """year*12 + month-1 (month-monotonic ordinal)."""
    return pd.year * 12 + (pd.month or 1) - 1


def _proximity_pair(qd: ParsedDate, cd: ParsedDate) -> float:
    """Compute proximity for a single (query, chunk) date pair."""
    if qd.year != cd.year:
        if abs(qd.year - cd.year) == 1:
            # Adjacent month spanning year boundary?
            if qd.month is not None and cd.month is not None:
                qm = _ym_index(qd)
                cm = _ym_index(cd)
                if abs(qm - cm) <= 1:
                    return SCORE_ADJACENT_MONTH
            return SCORE_ADJACENT_YEAR
        return SCORE_NO_CHUNK_DATE
    # Same year
    if qd.month is None or cd.month is None:
        return SCORE_SAME_YEAR
    if qd.month == cd.month:
        # Day-level only if BOTH have day
        if qd.day is not None and cd.day is not None and qd.day == cd.day:
            return SCORE_EXACT_DAY
        return SCORE_SAME_MONTH
    if abs(qd.month - cd.month) == 1:
        return SCORE_ADJACENT_MONTH
    return SCORE_SAME_YEAR


def temporal_proximity(
    query_dates: list[ParsedDate],
    chunk_date: Optional[ParsedDate],
    *,
    has_date_fallback: bool = False,
) -> float:
    """Max proximity across all query dates.

    - If no query date AND has_date_fallback: anchored chunks get
      SCORE_HAS_DATE_FALLBACK (default 0.6) to elevate them above
      anchorless chunks; unanchored chunks get SCORE_NO_DATE_FALLBACK (0.0).
    - If no query date AND NOT has_date_fallback: return 0.0 (passthrough).
    - If no chunk date: return 0.0 (chunk has no anchor).
    - Else: max over (qd, cd) pairs of _proximity_pair.
    """
    if not query_dates:
        if has_date_fallback:
            return SCORE_HAS_DATE_FALLBACK if chunk_date is not None else SCORE_NO_DATE_FALLBACK
        return 0.0
    if chunk_date is None:
        return 0.0
    return max(_proximity_pair(qd, chunk_date) for qd in query_dates)


# ---------------------------------------------------------------------------
# Temporal-class detection
# ---------------------------------------------------------------------------


def is_temporal_query(
    query: str,
    category_name: Optional[str] = None,
) -> bool:
    """Detect if a query should activate temporal-aware re-ranking.

    Heuristic:
      - If category_name == 'temporal' (LoCoMo cat 2): True
      - Else: query (post-aug-strip) lowercase contains a temporal keyword
              OR a year/month/date pattern.
    """
    if category_name == "temporal":
        return True
    if not query:
        return False
    q = _strip_augmentation(query).lower()
    # Word-boundary keyword match
    for kw in _TEMPORAL_KEYWORDS:
        if re.search(rf"\b{re.escape(kw)}\b", q):
            return True
    # Numeric date or year
    if _PAT_ISO.search(q) or _PAT_NUMERIC_SLASH.search(q):
        return True
    if _PAT_YEAR_ALONE.search(q):
        return True
    # Month name
    for mon in MONTH_NAMES:
        if re.search(rf"\b{mon.lower()}\b", q):
            return True
    for ab in MONTH_ABBR.keys():
        if re.search(rf"\b{ab}\b", q):
            return True
    return False


# ---------------------------------------------------------------------------
# Re-rank
# ---------------------------------------------------------------------------


def _minmax_normalize(scores: list[float]) -> list[float]:
    """Map scores to [0, 1] using min-max. Constant input -> all 0.5."""
    if not scores:
        return scores
    s_min = min(scores)
    s_max = max(scores)
    if s_max - s_min < 1e-12:
        return [0.5 for _ in scores]
    return [(s - s_min) / (s_max - s_min) for s in scores]


def rerank_with_temporal_proximity(
    chunks: list[dict],
    query: str,
    session_date_map: dict[str, str] | None,
    *,
    alpha: float = 0.5,
    category_name: Optional[str] = None,
    force_on: Optional[bool] = None,
    has_date_fallback: bool = True,
) -> list[ScoredChunk]:
    """Re-rank the top-K retrieved chunks using temporal proximity.

    Args:
        chunks: list of dicts with at least 'text' (or 'chunk_text') and
                'score' (or 'relevance'); 'chunk_id' optional. Preserves
                original input order on ties.
        query: original user query (will have LoCoMo augmentation stripped).
        session_date_map: {session_id: canonical 'D Month YYYY'} from
                          corpus_loader / temporal_normalizer.build_session_date_map.
        alpha: blend weight for temporal score in [0, 1]. 0.0 = passthrough,
               1.0 = temporal only.
        category_name: LoCoMo category_name to bias is_temporal_query.
        force_on: explicit override; True forces re-rank even if non-temporal,
                  False forces passthrough.
        has_date_fallback: when True and the temporal query carries no date,
                  anchored chunks (any date) get SCORE_HAS_DATE_FALLBACK so
                  they rank above anchorless chunks. ~87% of LoCoMo temporal
                  queries have no explicit date — this is what drives the lift
                  for them. Default True.

    Returns:
        list[ScoredChunk] sorted by final_score desc. Length == len(chunks).
        Original input order is preserved for ties via stable sort.
    """
    if not chunks:
        return []

    activate = (
        force_on
        if force_on is not None
        else is_temporal_query(query, category_name)
    )

    # Always parse to populate output metadata
    query_dates = extract_query_dates(query)
    originals: list[float] = []
    chunk_dates: list[Optional[ParsedDate]] = []
    sessions_dias: list[tuple[str, str]] = []
    texts: list[str] = []
    chunk_ids: list[str] = []

    for c in chunks:
        if not isinstance(c, dict):
            continue
        txt = str(c.get("text") or c.get("chunk_text") or c.get("snippet") or "")
        try:
            sc = float(c.get("score") or c.get("relevance") or 0.0)
        except (TypeError, ValueError):
            sc = 0.0
        cd = extract_chunk_date(txt, session_date_map)
        sid, dia = extract_chunk_session_and_dia(txt)
        cid = str(c.get("chunk_id") or c.get("id") or "")

        originals.append(sc)
        chunk_dates.append(cd)
        sessions_dias.append((sid, dia))
        texts.append(txt)
        chunk_ids.append(cid)

    normed = _minmax_normalize(originals)

    scored: list[ScoredChunk] = []
    for i, (sc_orig, sc_norm) in enumerate(zip(originals, normed)):
        cd = chunk_dates[i]
        if activate:
            tp = temporal_proximity(
                query_dates, cd,
                has_date_fallback=has_date_fallback,
            )
            final = (1.0 - alpha) * sc_norm + alpha * tp
        else:
            tp = 0.0
            final = sc_norm

        scored.append(
            ScoredChunk(
                chunk_id=chunk_ids[i],
                text=texts[i],
                original_score=sc_orig,
                temporal_score=tp,
                final_score=final,
                parsed_chunk_date=cd,
                session_id=sessions_dias[i][0],
                dia_id=sessions_dias[i][1],
            )
        )

    # Stable sort desc by final_score
    scored.sort(key=lambda s: s.final_score, reverse=True)
    return scored


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def _self_test() -> int:
    fail = 0

    def _assert(cond: bool, msg: str) -> None:
        nonlocal fail
        status = "OK" if cond else "FAIL"
        if not cond:
            fail += 1
        print(f"{status} {msg}")

    # extract_query_dates
    qd = extract_query_dates("What happened on 7 May 2023?")
    _assert(len(qd) == 1 and qd[0].canonical() == "7 May 2023",
            f"extract_query_dates 'D Month YYYY' -> {[d.canonical() for d in qd]}")

    qd = extract_query_dates("What did they discuss in May 2023?")
    _assert(len(qd) == 1 and qd[0].canonical() == "May 2023",
            f"extract_query_dates 'Month YYYY' -> {[d.canonical() for d in qd]}")

    qd = extract_query_dates("In 2023, what was Caroline's hobby?")
    _assert(len(qd) == 1 and qd[0].canonical() == "2023",
            f"extract_query_dates 'YYYY alone' -> {[d.canonical() for d in qd]}")

    qd = extract_query_dates("What did they talk about?")
    _assert(qd == [], f"extract_query_dates no date -> {qd}")

    qd = extract_query_dates(
        "When was it? Use DATE of CONVERSATION to answer with an approximate date."
    )
    _assert(qd == [], f"extract_query_dates aug-only -> {qd}")

    # extract_chunk_date
    chunk_text = (
        "### Caroline (dia_id: D1:3)\n\n"
        "sample_id: conv-26 | session_id: session_1 | dia_id: D1:3\n"
        "I went to a LGBTQ support group yesterday."
    )
    smap = {"session_1": "8 May 2023", "session_2": "25 May 2023"}
    cd = extract_chunk_date(chunk_text, smap)
    _assert(cd is not None and cd.canonical() == "8 May 2023",
            f"extract_chunk_date session_id route -> {cd}")

    # Inline date header fallback
    chunk_text2 = (
        "# LoCoMo conv-26 session_5\n\n"
        "date: 1:56 pm on 12 June, 2023\n"
        "## Conversation\n"
    )
    cd = extract_chunk_date(chunk_text2, None)
    _assert(cd is not None and cd.canonical() == "12 June 2023",
            f"extract_chunk_date inline header -> {cd}")

    # dia_id fallback
    chunk_text3 = (
        "### Bob (dia_id: D3:5)\n\n"
        "Some text without session_id label."
    )
    smap3 = {"session_3": "1 July 2023"}
    cd = extract_chunk_date(chunk_text3, smap3)
    _assert(cd is not None and cd.canonical() == "1 July 2023",
            f"extract_chunk_date dia_id route -> {cd}")

    # temporal_proximity
    qd_day = [ParsedDate(2023, 5, 8)]
    qd_month = [ParsedDate(2023, 5)]
    qd_year = [ParsedDate(2023)]
    cd_day = ParsedDate(2023, 5, 8)
    cd_month_same = ParsedDate(2023, 5, 9)
    cd_month_adj = ParsedDate(2023, 6, 1)
    cd_year_far = ParsedDate(2023, 11, 1)
    cd_other_year = ParsedDate(2024, 5, 8)
    cd_year_adj = ParsedDate(2022, 12, 30)  # Dec 2022 vs May 2023 (qd_day) -> far
    qd_jan = [ParsedDate(2023, 1, 15)]
    cd_dec_prev = ParsedDate(2022, 12, 30)  # Jan 2023 query vs Dec 2022 chunk

    _assert(temporal_proximity(qd_day, cd_day) == SCORE_EXACT_DAY,
            "proximity exact day")
    _assert(temporal_proximity(qd_day, cd_month_same) == SCORE_SAME_MONTH,
            "proximity same month")
    _assert(temporal_proximity(qd_day, cd_month_adj) == SCORE_ADJACENT_MONTH,
            "proximity adjacent month")
    _assert(temporal_proximity(qd_day, cd_year_far) == SCORE_SAME_YEAR,
            "proximity same year far")
    _assert(temporal_proximity(qd_day, cd_other_year) == SCORE_ADJACENT_YEAR,
            "proximity adjacent year")
    _assert(temporal_proximity(qd_jan, cd_dec_prev) == SCORE_ADJACENT_MONTH,
            "proximity Dec->Jan adjacent month across year boundary")
    _assert(temporal_proximity(qd_month, cd_day) == SCORE_SAME_MONTH,
            "proximity month-query day-chunk")
    _assert(temporal_proximity(qd_year, cd_day) == SCORE_SAME_YEAR,
            "proximity year-query day-chunk")
    _assert(temporal_proximity([], cd_day) == 0.0,
            "proximity no query date -> 0")
    _assert(temporal_proximity(qd_day, None) == 0.0,
            "proximity no chunk date -> 0")

    # is_temporal_query
    _assert(is_temporal_query("When did she go to the LGBTQ group?", "temporal"),
            "is_temporal cat=temporal")
    _assert(is_temporal_query("What was the date of the wedding?", None),
            "is_temporal keyword 'date'")
    _assert(is_temporal_query("In May 2023, what happened?", None),
            "is_temporal month name")
    _assert(not is_temporal_query("What is her favorite color?", None),
            "is_temporal non-temporal")

    # rerank_with_temporal_proximity
    chunks_in = [
        {"chunk_id": "c1", "text": "session_id: session_1\nfoo bar baz", "score": 0.9},
        {"chunk_id": "c2", "text": "session_id: session_2\nblah blah", "score": 0.85},
        {"chunk_id": "c3", "text": "session_id: session_3\nirrelevant", "score": 0.95},
        {"chunk_id": "c4", "text": "no session anchor here", "score": 0.7},
    ]
    smap = {
        "session_1": "8 May 2023",
        "session_2": "25 May 2023",
        "session_3": "1 December 2023",
    }
    scored = rerank_with_temporal_proximity(
        chunks_in,
        query="What happened on 8 May 2023?",
        session_date_map=smap,
        alpha=0.6,
        category_name="temporal",
    )
    _assert(scored[0].chunk_id == "c1",
            f"rerank: exact-day session_1 wins -> {scored[0].chunk_id}")
    # session_2 same-month should beat session_3 same-year-far (alpha=0.6)
    rank_ids = [s.chunk_id for s in scored]
    pos_c2 = rank_ids.index("c2")
    pos_c3 = rank_ids.index("c3")
    _assert(pos_c2 < pos_c3,
            f"rerank: same-month c2 above same-year-far c3 -> {rank_ids}")

    # Passthrough mode (non-temporal)
    scored_pt = rerank_with_temporal_proximity(
        chunks_in,
        query="What is her favorite color?",
        session_date_map=smap,
        alpha=0.6,
        category_name="single_hop",
    )
    pt_ids = [s.chunk_id for s in scored_pt]
    # Should be sorted by original_score: c3 (0.95) > c1 (0.9) > c2 (0.85) > c4 (0.7)
    _assert(pt_ids == ["c3", "c1", "c2", "c4"],
            f"rerank passthrough non-temporal -> {pt_ids}")

    print(f"\n{fail} failures")
    return 1 if fail else 0


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
