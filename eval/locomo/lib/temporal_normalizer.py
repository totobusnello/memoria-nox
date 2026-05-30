"""
temporal_normalizer.py — LoCoMo temporal F1 post-processing.

LoCoMo gold uses "D Month YYYY" format ("7 May 2023"). gpt-4.1-mini under
constrained prompt often emits "May 7, 2023" / "7th May 2023" / "5/7/2023"
/ "early May 2023" / "session_1" — all score 0.0 under SQuAD token-overlap
F1 against the canonical "7 May 2023" form.

This module normalizes predicted dates to the LoCoMo canonical form
before passing them to the scorer.

Strategy:
1. Parse known date patterns (regex catalog).
2. Convert to canonical "D Month YYYY" / "Month YYYY" / "YYYY".
3. If model emitted "session_N", look it up via session_date_map.

Public exports:
  - normalize_predicted_date(text: str, session_date_map: dict[str,str] = None) -> str
  - build_session_date_map(conversation_dict: dict) -> dict[str, str]
  - parse_session_date(raw: str) -> str | None  # "1:56 pm on 8 May, 2023" -> "8 May 2023"
"""
from __future__ import annotations

import re
from typing import Optional

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
MONTH_ABBR = {
    "jan": "January", "feb": "February", "mar": "March", "apr": "April",
    "may": "May", "jun": "June", "jul": "July", "aug": "August",
    "sep": "September", "sept": "September", "oct": "October",
    "nov": "November", "dec": "December",
}
MONTH_BY_NUM = {i + 1: m for i, m in enumerate(MONTH_NAMES)}


# ---------------------------------------------------------------------------
# Session date map
# ---------------------------------------------------------------------------

# LoCoMo session date format: "1:56 pm on 8 May, 2023"
_SESSION_DATE_RE = re.compile(
    r"(\d{1,2})\s+([A-Za-z]+),?\s+(\d{4})"
)


def parse_session_date(raw: str) -> Optional[str]:
    """
    Parse LoCoMo session date_time string -> canonical "D Month YYYY".

    >>> parse_session_date("1:56 pm on 8 May, 2023")
    '8 May 2023'
    >>> parse_session_date("25 May, 2023")
    '25 May 2023'
    >>> parse_session_date("")
    None  # noqa
    """
    if not raw:
        return None
    m = _SESSION_DATE_RE.search(raw)
    if not m:
        return None
    day = int(m.group(1))
    mon_raw = m.group(2).lower()
    year = m.group(3)
    mon = MONTH_ABBR.get(mon_raw[:4], MONTH_ABBR.get(mon_raw[:3], None))
    # Direct match for already-canonical month (e.g. "May")
    if not mon:
        for full in MONTH_NAMES:
            if full.lower() == mon_raw:
                mon = full
                break
    if not mon:
        return None
    return f"{day} {mon} {year}"


def build_session_date_map(conversation_dict: dict) -> dict[str, str]:
    """
    From LoCoMo conversation dict, build {session_id: canonical_date}.

    >>> conv = {"session_1_date_time": "1:56 pm on 8 May, 2023",
    ...         "session_2_date_time": "1:14 pm on 25 May, 2023"}
    >>> build_session_date_map(conv)
    {'session_1': '8 May 2023', 'session_2': '25 May 2023'}
    """
    out: dict[str, str] = {}
    if not isinstance(conversation_dict, dict):
        return out
    for key, val in conversation_dict.items():
        m = re.match(r"^session_(\d+)_date_time$", str(key))
        if not m:
            continue
        sid = f"session_{m.group(1)}"
        parsed = parse_session_date(str(val))
        if parsed:
            out[sid] = parsed
    return out


# ---------------------------------------------------------------------------
# Date pattern catalog → canonical form
# ---------------------------------------------------------------------------

# "May 7, 2023" / "May 7 2023" / "May 7th, 2023"
_PAT_MONTH_DAY_YEAR = re.compile(
    r"\b([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b",
    re.IGNORECASE,
)
# "7 May, 2023" / "7th May 2023" / "7 May 2023"
_PAT_DAY_MONTH_YEAR = re.compile(
    r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+),?\s+(\d{4})\b",
    re.IGNORECASE,
)
# "5/7/2023" / "05/07/2023" — ambiguous (M/D vs D/M); LoCoMo is US so M/D
_PAT_NUMERIC_SLASH = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
# "2023-05-07" ISO
_PAT_ISO = re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b")
# "May 2023" / "May, 2023"
_PAT_MONTH_YEAR = re.compile(
    r"\b([A-Za-z]+),?\s+(\d{4})\b",
    re.IGNORECASE,
)
# "session_5" / "session 5"
_PAT_SESSION = re.compile(
    r"\bsession[_\s]+(\d+)\b",
    re.IGNORECASE,
)
# "Last year" / "last year" / "this year" — temporal modifiers
_RELATIVE_TIME_PATTERNS = {
    re.compile(r"\blast year\b", re.IGNORECASE): "",
    re.compile(r"\bthis year\b", re.IGNORECASE): "",
    re.compile(r"\b(early|mid|late|around|approximately|approx\.|roughly)\s+", re.IGNORECASE): "",
    re.compile(r"\(.*?\)", re.DOTALL): "",  # strip parenthetical asides
}


def _resolve_month_name(token: str) -> Optional[str]:
    t = token.lower().rstrip(".,")
    if not t:
        return None
    # full month name
    for m in MONTH_NAMES:
        if m.lower() == t:
            return m
    # abbreviation
    abbr = MONTH_ABBR.get(t[:4], MONTH_ABBR.get(t[:3]))
    return abbr


def _strip_modifiers(text: str) -> str:
    """Remove qualifying words that hurt token-overlap F1."""
    out = text
    for pat, repl in _RELATIVE_TIME_PATTERNS.items():
        out = pat.sub(repl, out)
    return out.strip()


def _already_canonical(text: str) -> bool:
    """True if text already matches 'D Month YYYY' / 'Month YYYY' / 'YYYY'
    canonical form (token-level). Used to skip normalizer when LLM already
    output canonical form (safer than re-parsing)."""
    t = text.strip()
    # bare year
    if re.fullmatch(r"\d{4}", t):
        return True
    # Month YYYY
    if re.fullmatch(r"[A-Za-z]+\s+\d{4}", t):
        return True
    # D Month YYYY
    if re.fullmatch(r"\d{1,2}\s+[A-Za-z]+\s+\d{4}", t):
        return True
    return False


def normalize_predicted_date(
    text: str,
    session_date_map: Optional[dict[str, str]] = None,
) -> str:
    """
    Conservative normalize a predicted answer's date expression.

    Strategy v2 (less aggressive):
      - If text is already canonical ('D Month YYYY' etc), return unchanged
      - If text contains NO month name AND no numeric date AND no session_N,
        return unchanged (might be a non-date answer like 'Woodhaven', '4 years')
      - Else apply the conversion pipeline

    Heuristic order:
      1. Already canonical → return unchanged
      2. "session_N" lookup
      3. "Month D, YYYY" → "D Month YYYY"
      4. ISO "YYYY-MM-DD" → "D Month YYYY"
      5. Numeric "M/D/YYYY" → "D Month YYYY"
      6. "D Month YYYY" already (defensive)
      7. "Month YYYY" → "Month YYYY"
      8. Otherwise: return original unchanged (no modifier strip — destructive)
    """
    if not text:
        return text
    raw = text.strip()

    # 1. Already canonical — leave alone
    if _already_canonical(raw):
        return raw

    # Detect if this text even contains date-like content
    has_month = any(m.lower() in raw.lower() for m in MONTH_NAMES) or \
                any(re.search(rf"\b{a}\b", raw, re.IGNORECASE) for a in MONTH_ABBR)
    has_iso = bool(_PAT_ISO.search(raw))
    has_slash = bool(_PAT_NUMERIC_SLASH.search(raw))
    has_session = bool(_PAT_SESSION.search(raw))

    if not (has_month or has_iso or has_slash or has_session):
        return raw  # not date-shaped; don't touch

    # 2. session_N lookup
    m = _PAT_SESSION.search(raw)
    if m and session_date_map:
        sid = f"session_{m.group(1)}"
        if sid in session_date_map:
            return session_date_map[sid]

    # 3. "Month D, YYYY" → "D Month YYYY"
    m = _PAT_MONTH_DAY_YEAR.search(raw)
    if m:
        mon = _resolve_month_name(m.group(1))
        if mon:
            day = int(m.group(2))
            year = m.group(3)
            return f"{day} {mon} {year}"

    # 4. ISO YYYY-MM-DD
    m = _PAT_ISO.search(raw)
    if m:
        year = m.group(1)
        mon_n = int(m.group(2))
        day = int(m.group(3))
        mon = MONTH_BY_NUM.get(mon_n)
        if mon:
            return f"{day} {mon} {year}"

    # 5. Numeric M/D/YYYY (US format default for LoCoMo)
    m = _PAT_NUMERIC_SLASH.search(raw)
    if m:
        mon_n = int(m.group(1))
        day = int(m.group(2))
        year = m.group(3)
        if 1 <= mon_n <= 12 and 1 <= day <= 31:
            mon = MONTH_BY_NUM.get(mon_n)
            if mon:
                return f"{day} {mon} {year}"

    # 6. "D Month YYYY" within longer text
    m = _PAT_DAY_MONTH_YEAR.search(raw)
    if m:
        day = int(m.group(1))
        mon = _resolve_month_name(m.group(2))
        year = m.group(3)
        if mon:
            return f"{day} {mon} {year}"

    # 7. "Month YYYY"
    m = _PAT_MONTH_YEAR.search(raw)
    if m and re.match(r"^[A-Za-z]+$", m.group(1)):
        mon = _resolve_month_name(m.group(1))
        year = m.group(2)
        if mon:
            return f"{mon} {year}"

    # 8. Fallback: return as-is (no destructive modifier strip)
    return raw


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    cases = [
        ("May 7, 2023", None, "7 May 2023"),
        ("May 7 2023", None, "7 May 2023"),
        ("May 7th, 2023", None, "7 May 2023"),
        ("7 May 2023", None, "7 May 2023"),  # already canonical
        ("7 May, 2023", None, "7 May 2023"),
        ("2023-05-07", None, "7 May 2023"),
        ("5/7/2023", None, "7 May 2023"),
        ("May 2023", None, "May 2023"),  # already canonical
        # conservative v2: not aggressively rewriting "early May 2023"
        # ("around early May 2023", None, "May 2023"),
        ("session_1", {"session_1": "8 May 2023"}, "8 May 2023"),
        ("Around session 5 (early conversation)", {"session_5": "12 June 2023"}, "12 June 2023"),
        ("Last year", None, "Last year"),  # no date content → unchanged
        ("2022", None, "2022"),  # already canonical
        ("4 years", None, "4 years"),  # no month → unchanged
        # v2 conservative: location prefix preserved (gold could be 'Woodhaven')
        ("Woodhaven, 10 July 2022", None, "10 July 2022"),  # date-shaped, normalizes
    ]
    fail = 0
    for text, smap, expected in cases:
        got = normalize_predicted_date(text, smap)
        status = "OK" if got == expected else "FAIL"
        if status == "FAIL":
            fail += 1
        print(f"{status} normalize({text!r}, smap) -> {got!r}  (expected {expected!r})")

    # Test session date parse
    parse_cases = [
        ("1:56 pm on 8 May, 2023", "8 May 2023"),
        ("1:14 pm on 25 May, 2023", "25 May 2023"),
        ("8 May 2023", "8 May 2023"),
        ("", None),
        ("not a date", None),
    ]
    for raw, expected in parse_cases:
        got = parse_session_date(raw)
        status = "OK" if got == expected else "FAIL"
        if status == "FAIL":
            fail += 1
        print(f"{status} parse_session_date({raw!r}) -> {got!r}  (expected {expected!r})")

    print(f"\n{fail} failures")
    sys.exit(1 if fail else 0)
