"""eval/evermembench/query_classifier.py — heuristic adaptive query classifier.

Lab Q1 #1 (spec PR #373) — Option A heuristic classifier.

Routes multi-hop queries to cross-encoder rerank (Phase G) and factual queries
to bi-encoder retrieval (Phase D / Phase H v2). Best-of-both:
  - Multi-hop benefits from rerank (Phase G F_MH +1.61 pp at 5-batch)
  - Factual queries preserve MA_C / MA_P / MA_U (rerank regressed -3 to -4 pp)
  - Overall projected: +1-3 pp vs always-rerank, closes ~30-50% of MemOS gap

Heuristic features (per spec §1.1 + Option A pseudocode §2):
  - entity_count: capitalized proper-noun-like spans + quoted topics
  - conjunction_count: and/or/while/because/after/before chains
  - has_comparative: "compared to", "vs", "difference between", "how does X relate"
  - has_abstract_reasoning: why / explain / summarize / what caused / what led to
  - token_count: query length signal
  - has_temporal_chain: "before … happened", "since … changed", "after … and then"

Threshold default = 4 (per spec §2 Option A). Tunable via NOX_ADAPTIVE_THRESHOLD.

PT-BR variants included per spec §7.2 risk mitigation: depois que / antes de /
como se compara / qual a diferença entre / por que / explique.

Latency target: <5 ms per query (per spec §1.4 and gate D §5.3). Pure regex,
no DB lookup, no LLM call.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Feature weights (per spec §2 Option A pseudocode)
# ---------------------------------------------------------------------------
WEIGHT_ENTITY_COUNT_GE_3 = 3
WEIGHT_CONJUNCTION_COUNT_GE_2 = 2
WEIGHT_COMPARATIVE = 3
WEIGHT_ABSTRACT_REASONING = 2
WEIGHT_LONG_TOKEN_COUNT = 1
WEIGHT_TEMPORAL_CHAIN = 2

DEFAULT_THRESHOLD = 4
LONG_TOKEN_COUNT = 10


# ---------------------------------------------------------------------------
# Regex patterns (case-insensitive unless noted)
# ---------------------------------------------------------------------------

# Conjunctions — chains of cause/effect/sequence (EN + PT-BR)
_CONJUNCTIONS_RE = re.compile(
    r"\b("
    # English
    r"and|or|but|while|because|after|before|since|until|whereas|"
    # Portuguese
    r"e|ou|mas|enquanto|porque|depois|antes|desde|at[eé]|quando"
    r")\b",
    re.IGNORECASE,
)

# Comparative markers — high signal for multi-hop
_COMPARATIVE_RE = re.compile(
    r"("
    # English
    r"compared to|differ from|differs from|difference between|"
    r"how does .{1,30} (?:compare|relate|differ)|"
    r"vs\.?\s|versus|in contrast|"
    # Portuguese
    r"comparado (?:a|com)|como se compara|qual a diferen[çc]a entre|"
    r"em rela[çc]ão a|diferente de"
    r")",
    re.IGNORECASE,
)

# Abstract reasoning markers — sumarisation / explanation / causation
_ABSTRACT_REASONING_RE = re.compile(
    r"\b("
    # English
    r"why|explain|summari[sz]e|describe|what caused|what led to|"
    r"how did .{1,30} (?:come about|happen|emerge|develop)|"
    # Portuguese
    r"por qu[eê]|explique|explica|resuma|resume|descreva|descreve|"
    r"o que causou|o que levou"
    r")\b",
    re.IGNORECASE,
)

# Temporal chains — "after X and then Y" / "before X happened"
_TEMPORAL_CHAIN_RE = re.compile(
    r"("
    # English
    r"before .{1,40} happened|since .{1,40} changed|"
    r"after .{1,30} and then|"
    r"prior to .{1,30} (?:becoming|being)|"
    # Portuguese
    r"depois que .{1,40} aconteceu|"
    r"antes de .{1,40} acontecer|"
    r"desde que .{1,40} mudou"
    r")",
    re.IGNORECASE,
)

# Entity proxy — proper-noun-like spans (capitalized words not at sentence start)
# plus quoted topics. Approximates EN "Joe / Mary / Acme / 2024" without an
# NER library. PT-BR names usually capitalize the same way so the same regex
# generalises. We collapse adjacent capitalised words ("New York") into a
# single entity.
_PROPER_NOUN_RE = re.compile(
    r"(?:^|[\s\.,;:!?])([A-ZÀ-Ý][a-zà-ÿ]+(?:\s+[A-ZÀ-Ý][a-zà-ÿ]+)*)"
)
_QUOTED_TOPIC_RE = re.compile(r"[\"'`]([^\"'`]{2,80})[\"'`]")
# Numerals (years, IDs, version numbers) — count as entity signal
_NUMERAL_RE = re.compile(r"\b(\d{2,})\b")

# Stop-words to drop from the proper-noun candidate set (first-word capitalisation
# is normally the sentence opener, not an entity). The regex above already
# skips sentence-initial capitals because it requires a leading whitespace or
# punctuation; this stop-list catches edge cases where the query string starts
# with a wh-word that happens to capitalise itself in the corpus (e.g. "Who",
# "What", "When" — interrogatives, not entities).
_WHWORDS_LOWER: set[str] = {
    # English
    "who", "what", "when", "where", "which", "how", "why",
    # Portuguese
    "quem", "que", "qual", "como", "onde", "quando", "porque",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@dataclass
class ClassificationResult:
    """Result of classifying a single query."""

    score: int
    threshold: int
    decision: str  # "multi_hop" | "factual"
    features: dict[str, Any] = field(default_factory=dict)

    @property
    def is_multi_hop(self) -> bool:
        return self.decision == "multi_hop"


def classify_query(
    query: str,
    threshold: int = DEFAULT_THRESHOLD,
) -> ClassificationResult:
    """Classify a query as multi-hop or factual via Option A heuristics.

    Per spec PR #373 §2 Option A:

        score = 0
        if entity_count(query) >= 3:    score += 3
        if conjunction_count(query) >= 2: score += 2
        if has_comparative(query):       score += 3
        if has_abstract_reasoning(query): score += 2
        if token_count(query) > 10:      score += 1
        if has_temporal_chain(query):    score += 2

        score >= THRESHOLD (default 4) → MULTI_HOP → rerank ON
        score < THRESHOLD              → FACTUAL  → rerank OFF

    Args:
        query: The natural-language query string.
        threshold: Minimum score to classify as multi-hop. Default 4 (per spec).

    Returns:
        ClassificationResult with score, decision, and audit-trail features.
    """
    if not query or not query.strip():
        return ClassificationResult(
            score=0,
            threshold=threshold,
            decision="factual",
            features={"empty_query": True},
        )

    q = query.strip()

    # ── Feature 1: entity count ────────────────────────────────────────────
    proper_nouns = _PROPER_NOUN_RE.findall(q)
    proper_nouns_clean: list[str] = []
    for span in proper_nouns:
        words = span.split()
        # Drop wh-words that capitalised at sentence start
        if all(w.lower() not in _WHWORDS_LOWER for w in words):
            proper_nouns_clean.append(span)
    quoted_topics = _QUOTED_TOPIC_RE.findall(q)
    numerals = _NUMERAL_RE.findall(q)
    # Distinct case-insensitive entity set
    entity_set = {x.lower() for x in proper_nouns_clean + quoted_topics + numerals}
    entity_count = len(entity_set)

    # ── Feature 2: conjunction count ───────────────────────────────────────
    conjunction_matches = _CONJUNCTIONS_RE.findall(q)
    conjunction_count = len(conjunction_matches)

    # ── Feature 3: comparative ─────────────────────────────────────────────
    has_comparative = bool(_COMPARATIVE_RE.search(q))

    # ── Feature 4: abstract reasoning ──────────────────────────────────────
    has_abstract_reasoning = bool(_ABSTRACT_REASONING_RE.search(q))

    # ── Feature 5: token count ─────────────────────────────────────────────
    token_count = len(q.split())

    # ── Feature 6: temporal chain ──────────────────────────────────────────
    has_temporal_chain = bool(_TEMPORAL_CHAIN_RE.search(q))

    # ── Score per spec §2 Option A ─────────────────────────────────────────
    score = 0
    if entity_count >= 3:
        score += WEIGHT_ENTITY_COUNT_GE_3
    if conjunction_count >= 2:
        score += WEIGHT_CONJUNCTION_COUNT_GE_2
    if has_comparative:
        score += WEIGHT_COMPARATIVE
    if has_abstract_reasoning:
        score += WEIGHT_ABSTRACT_REASONING
    if token_count > LONG_TOKEN_COUNT:
        score += WEIGHT_LONG_TOKEN_COUNT
    if has_temporal_chain:
        score += WEIGHT_TEMPORAL_CHAIN

    decision = "multi_hop" if score >= threshold else "factual"

    return ClassificationResult(
        score=score,
        threshold=threshold,
        decision=decision,
        features={
            "entity_count": entity_count,
            "entity_set": sorted(entity_set),
            "conjunction_count": conjunction_count,
            "has_comparative": has_comparative,
            "has_abstract_reasoning": has_abstract_reasoning,
            "token_count": token_count,
            "has_temporal_chain": has_temporal_chain,
        },
    )
