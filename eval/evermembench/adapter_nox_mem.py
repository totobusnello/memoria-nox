"""
nox-mem Adapter for EverMemBench — Phase F + Phase KG + Phase MQ + Phase KGMQ + Phase IterC (Q3 POC — orchestration-stage Self-Ask, 2026-05-29).

Connects nox-mem (CLI ingest + HTTP search API) to the EverMemBench
evaluation harness.

Phase A (PR #363, batch 004 = 56.07%) used flat-paragraph markdown with
inline `[Group][Speaker][Time]` prefixes. The nox-mem segmenter coalesced
~9 messages per chunk (10,222 msgs -> 1,140 chunks), diluting per-message
metadata. Multi-hop scored 4% / Temporal 10%.

Phase B introduced H2-per-message chunks + structured prefix + day-group
digests. Phase D added a search-time over-fetch (top_k=20 from API) that
won the 5-batch aggregate at 62.22% (beat MemOS 59.27%). But multi-hop
remained weak (5.22% 5-batch avg).

Phase F attacks the multi-hop bottleneck with cross-encoder reranking on
top of Phase D's retrieval. Pipeline:
  1. Request top-50 from nox-mem hybrid search (over-fetch).
  2. Pass (query, chunk_text) pairs through BAAI/bge-reranker-v2-m3
     CrossEncoder which sees the full context together and can score
     "bridge facts" that bi-encoder retrieval misses.
  3. Re-sort by rerank score, take top_k for the harness.

Cross-encoder rerank adds local compute cost (~50-300ms per query on CPU,
faster on GPU). For end-user latency-sensitive paths this would be a
trade-off; for offline benchmark eval it is acceptable.

Phase KG (Lab Q1 #4, 2026-05-29) — KG path retrieval (Approach A, 1-hop):
  1. Extract candidate entity mentions from the query via regex against
     `kg_entities.name` (cheapest path per spec §3.A).
  2. Look up 1-hop neighbors via SQL JOIN over `kg_relations` (FK ids,
     not inline strings — per [[kg-relations-uses-fk-ids-not-inline-strings]]).
  3. Use `kg_relations.evidence_chunk_id` (direct FK to chunks) to find
     "evidence chunks" for the neighbor entities — much cleaner than
     `source_path LIKE '%slug%'` matching.
  4. Apply ADDITIVE score delta to evidence chunks already present in
     the hybrid search top-N. Per memoria-nox rule §5 (boost multiplicativo
     empilhável é veneno), the delta is added to RRF score, not multiplied.

Phase MQ (Lab Q1 #3, 2026-05-29) — Multi-query expansion (Approach B from
specs/2026-05-28-multi-query-expansion.md). Pre-retrieval LLM decomposes
the query into N atomic sub-questions, each is independently retrieved
top-K from nox-mem, and results are unioned + deduplicated + re-ranked
via RRF over per-sub-query ranks.

  1. Call gemini-flash-lite (or NOX_MQ_LLM) with a decomposition prompt
     that returns a JSON array of 3-5 sub-questions covering distinct
     aspects of the original multi-hop query.
  2. For each sub-question, hit the same /api/search hybrid endpoint
     with top_k=NOX_MQ_PER_QUERY_TOPK (default 10).
  3. Build the union: each chunk_id maps to the list of sub-query ranks
     in which it appeared.
  4. RRF re-merge: chunk_score = sum(1 / (k + rank_i)) over sub-queries
     it appeared in, with k=NOX_MQ_RRF_K (default 60). Chunks that
     appear in multiple sub-queries get a natural boost (convergence
     signal) without multiplicative stacking (per rule §5).
  5. Sort by chunk_score desc, return top_k to the harness.

Cost: 1 LLM decomposer call (~$0.0001 with flash-lite) + N x baseline
retrieval. Latency overhead: +200-500ms (LLM dominates).

Fallback: if decomposition fails (LLM error, malformed JSON, < 2 sub-
queries returned), gracefully fall back to single-query retrieval — the
mode is logged as "fallback_single" in metadata.

Phase KGMQ (Wave B composability, 2026-05-29) — Combines Phase KG + Phase MQ
in a single adapter mode. Mechanism (per [[mq-kg-mechanically-additive-prediction-6-42pp]]):

  1. MQ decomposes the original query into N atomic sub-queries via LLM
  2. For each sub-query, retrieve top-K candidates from /api/search (same
     as Phase MQ alone)
  3. RRF-union across all sub-query results (Phase MQ merge step)
  4. THEN apply KG 1-hop entity boost on the MQ-merged candidate set
     (entities extracted from the ORIGINAL query, not sub-queries —
     entities-of-interest are stable across decomposition)
  5. Final ranking respects both signals (sub-query convergence via RRF
     score + KG entity proximity via additive delta)

Both mechanisms use RRF additive boost on the same score level (no
multiplicative stacking, per memoria-nox rule §5). Predicted combined
F_MH lift: Phase H v2 (3.21%) + KG (+2.81pp) + MQ (+3.61pp) = ~9.63%
F_MH if additive holds. Wave B validates composability via 4-gate test:
F_MH lift ≥ +5.5pp (additivity floor: +2.81 + +3.61 − 1pp interaction
penalty), F_MH ≥ Phase MQ alone, Overall regression ≤ MQ alone + 0.5pp,
MA composite ≥ MQ alone − 0.5pp.

Phase IterC (Q3 POC — orchestration-stage Self-Ask, 2026-05-29).
Implements Self-Ask (Press et al. 2022, arxiv:2210.03350) — the
cheapest of Q3's three iterative-retrieval candidates per spec
`specs/2026-05-29-iterative-retrieval-q3.md` §3.

Hypothesis (Q3 spec §1): retrieval-stage stacking saturated at F_MH ~7.25%
(Waves A/B/C — D69 cravada, PR #395). To break the F_MH ceiling we must
operate in a *different* pipeline stage. Self-Ask is the cheapest such
mechanism: it adds one orchestration round (LLM-driven sub-Q generation
+ intermediate sub-answers) on top of any underlying retrieval (here:
Phase H v2 baseline, no Wave A/B/C knobs — clean isolation).

Pipeline:
  1. Decomposer (gemini-flash-lite): turn the query into 2-4 atomic
     sub-questions covering the multi-hop chain.
  2. Per sub-question: nox-mem hybrid search top_k=10 (Phase H v2 config).
  3. Per sub-question: gpt-4.1-mini answers the sub-question using only
     the chunks retrieved for IT (intermediate sub-answers). This is the
     orchestration-stage signal that distinguishes Self-Ask from Phase MQ
     — the LLM "thinks" between hops, producing intermediate facts that
     feed the final synthesis.
  4. Chunk union via RRF (k=NOX_ITERC_RRF_K, default 60) — identical
     mechanism to Phase MQ for chunk-side merge.
  5. Context injection: the final context returned to the harness's
     answer stage starts with "## Sub-question N: ... ## Intermediate
     answer: ..." blocks followed by "## Retrieved chunks: ..." — so the
     final gpt-4.1-mini answer sees both the orchestration reasoning
     and the underlying evidence.

Cost: 1 decomposer call + N sub-answer calls + 1 final answer call (via
harness) ≈ 2× harness baseline answer cost. Latency: +1-3s per query
(decomposer + N parallel sub-answers + RRF merge).

Fallback ladder:
  - Decomposer fails → fall back to single-query retrieval (no Self-Ask).
  - Sub-answer fails → keep chunks for union, drop the intermediate
    sub-answer block from context (graceful degradation).
  - No sub-answers succeed → fall back to standard chunk-only context.

Predicted F_MH lift (spec §3 decision matrix):
  - Approach A (CoT-Enrich): +1-2pp F_MH (single-shot, no decomposition)
  - Approach C (Self-Ask, this POC): +2-4pp F_MH
  - Approach B (ReAct full): +3-5pp F_MH (but 4× cost)

This POC validates the orthogonal-stage hypothesis — if Self-Ask clears
the +2pp F_MH gate it greenlights Q3 IterB (ReAct full). If it fails all
gates, Q3 IterC is dead and we pivot directly to IterB.

Modes:
    NOX_ADAPTER_MODE=baseline  -> PR #363 flat-paragraph ingest format
    NOX_ADAPTER_MODE=phaseB    -> H2-per-message + digest (default)
    NOX_ADAPTER_MODE=phaseF    -> phaseB ingest + cross-encoder rerank in search
    NOX_ADAPTER_MODE=phaseKG   -> phaseB ingest + KG 1-hop entity boost in search
    NOX_ADAPTER_MODE=phaseMQ   -> phaseB ingest + multi-query expansion (decompose)
    NOX_ADAPTER_MODE=phaseIterC -> phaseB ingest + Self-Ask (Q3 POC):
                                  sub-Q decomposition + per-sub-Q retrieval +
                                  per-sub-Q intermediate answer (gpt-4.1-mini)
                                  + chunk-union via RRF + context injection of
                                  (sub-Q, intermediate-answer) blocks. No
                                  Wave A/B/C retrieval knobs (clean isolation).
    NOX_ADAPTER_MODE=phaseIterB -> phaseB ingest + ReAct (Q3 POC, this PR — Yao
                                  et al. 2022 arxiv:2210.03629). Multi-round
                                  retrieve-reason orchestration loop:
                                    Round 1..max_rounds: orchestrator emits
                                    either {action:retrieve, query} or
                                    {action:answer, answer}. Retrieve hits
                                    /api/search top_k=10; observations feed
                                    back into scratchpad. Final answer
                                    synthesized either by LLM signal or by
                                    max_rounds/cost_ceiling termination.
                                  Chunk-union across rounds via RRF (k=60).
                                  Context prefix = scratchpad + draft answer.
                                  No Wave A/B/C knobs (clean isolation).
                                  Canonical F_MH ceiling break attempt per
                                  PR #393 spec §3.B (vs Self-Ask wrong class
                                  for F_MH per PR #406).
    NOX_ADAPTER_MODE=phaseKGMQ -> phaseB ingest + MQ decompose + KG 1-hop entity
                                  boost composed (Wave B composability — PR #389)
    NOX_ADAPTER_MODE=phaseMAP  -> phaseB ingest + rerank with bypass-entity (MA-protection
                                  Approach A from PR #386); chunks tagged section IN
                                  ('compiled','frontmatter') skip cross-encoder and keep
                                  their bi-encoder position.
    NOX_ADAPTER_MODE=phaseTriple -> phaseB ingest + MQ decompose + KG 1-hop boost +
                                    cross-encoder rerank + MA-protection (KG-anchored bypass).
                                    Wave C composability — combines all 3 retrieval/rerank
                                    mechanisms in distinct pipeline stages:
                                      stage 1 (retrieval expansion): MQ sub-query decomposition + RRF
                                      stage 2 (retrieval entity-walk): KG 1-hop boost on MQ-merged candidates
                                      stage 3 (rerank protection): MAP-style bypass-entity for KG anchor chunks
                                    Predicted F_MH ~8.5-9.5pp (additive floor 6.85pp; cap by KG/MQ overlap).
    NOX_ADAPTER_MODE=phaseKGMAP -> phaseB ingest + KG 1-hop boost + cross-encoder rerank +
                                   MA-protection extended with KG anchor (Wave B
                                   composability — this PR). Bypass criterion becomes
                                   section IN ('compiled','frontmatter')
                                   OR chunk_id IN kg_evidence_chunks_for_query_entities.
                                   Closes corpus mismatch on chat-only corpora.

Environment variables:
    NOX_API_BASE              — nox-mem API base URL (default: http://127.0.0.1:18802)
    NOX_DB_PATH               — per-batch DB path override (REQUIRED for isolation)
    NOX_MEM_BIN               — path to nox-mem CLI binary (default: "nox-mem" on PATH)
    NOX_ADAPTER_MODE          — "phaseB" (default) / "baseline" / "phaseF" / "phaseKG"
                                / "phaseMQ" / "phaseKGMQ" / "phaseMAP" / "phaseKGMAP"
                                / "phaseTriple" / "phaseIterC" / "phaseIterB"
    NOX_RERANKER_ENABLED      — "1" to force cross-encoder rerank in phaseF
    NOX_RERANKER_MODEL        — HF model id (default: BAAI/bge-reranker-v2-m3)
    NOX_RERANKER_OVERFETCH    — int top-N to pull from API before rerank (default: 50)
    NOX_RERANKER_BATCH_SIZE   — CrossEncoder.predict batch_size (default: 32)
    NOX_KG_PATH_ENABLED       — "1" to force KG 1-hop boost (env override on any mode)
    NOX_KG_BOOST_MAGNITUDE    — float, additive delta applied to RRF score (default: 0.05)
    NOX_KG_DIRECT_MULTIPLIER  — float, multiplier of base delta for chunks containing
                                directly-mentioned entities (default: 1.5)
    NOX_KG_MAX_NEIGHBORS      — int, max neighbors per mentioned entity (default: 20)
    NOX_KG_MIN_NAME_LEN       — int, minimum entity name length to use in regex
                                extraction (default: 3) — avoids matching common tokens
                                like "a", "of", "is" that may be entity names in noisy KGs.
    NOX_MA_PROTECTION_ENABLED — "1" to enable MA-protection bypass-entity in rerank
                                (env override; default-on for phaseMAP / phaseKGMAP).
                                When set, chunks whose `section` is in ENTITY_SECTION_NAMES
                                ('compiled', 'frontmatter') retain their bi-encoder rank
                                instead of being shuffled by the cross-encoder.
    NOX_MA_PROTECTION_KG_ANCHOR — "1" to extend bypass criterion with KG evidence chunks
                                for query-mentioned entities (Wave B composability fix
                                for chat-only corpora where Set E = empty). Default-on
                                for phaseKGMAP. Requires NOX_KG_PATH_ENABLED active.
    NOX_MA_PROTECTION_MAX     — int, maximum number of protected chunks per query
                                (caps Set P to avoid degenerate "protect everything"
                                cases when query mentions a high-degree hub entity).
                                Default 25.
    NOX_MQ_ENABLED            — "1" to force multi-query expansion (env override on any mode)
    NOX_MQ_LLM                — model id for decomposer (default: gemini-2.5-flash-lite)
    NOX_MQ_LLM_API_KEY        — auth bearer for decomposer (default: GEMINI_API_KEY)
    NOX_MQ_LLM_BASE_URL       — base URL for decomposer (default: Gemini OpenAI-compat)
    NOX_MQ_N                  — int, target sub-question count (default: 4, range 2-6)
    NOX_MQ_PER_QUERY_TOPK     — int, top_k per sub-query before union (default: 10)
    NOX_MQ_RRF_K              — int, RRF constant for union re-merge (default: 60)
    NOX_MQ_TIMEOUT_S          — float, decomposer LLM timeout in seconds (default: 30)
    NOX_MQ_DEBUG              — "1" to log decompositions + per-query result counts
    NOX_ITERC_ENABLED         — "1" to force Self-Ask (env override on any mode);
                                default-on for NOX_ADAPTER_MODE=phaseIterC
    NOX_ITERC_DECOMPOSER_LLM  — decomposer model (default: gemini-2.5-flash-lite,
                                shared infra with Phase MQ)
    NOX_ITERC_DECOMPOSER_BASE_URL — Gemini OpenAI-compat endpoint (default same
                                    as NOX_MQ_LLM_BASE_URL)
    NOX_ITERC_DECOMPOSER_API_KEY — auth bearer for decomposer
                                   (default: GEMINI_API_KEY)
    NOX_ITERC_ANSWERER_LLM    — model for per-sub-Q intermediate answers
                                (default: gpt-4.1-mini — matches Phase H v2
                                final-answer backbone for fair compare)
    NOX_ITERC_ANSWERER_BASE_URL — answerer endpoint
                                  (default: https://api.openai.com/v1)
    NOX_ITERC_ANSWERER_API_KEY — auth bearer for answerer (default: OPENAI_API_KEY)
    NOX_ITERC_N               — int, sub-question count (default: 3, range 2-4)
    NOX_ITERC_PER_QUERY_TOPK  — int, top_k per sub-question retrieval (default: 10)
    NOX_ITERC_RRF_K           — int, RRF constant for chunk union (default: 60)
    NOX_ITERC_DECOMPOSER_TIMEOUT_S — float, decomposer timeout (default: 30)
    NOX_ITERC_ANSWERER_TIMEOUT_S — float, sub-answer timeout (default: 45 — each
                                   sub-answer is a small task; 5 in parallel)
    NOX_ITERB_ENABLED         — "1" to force ReAct (env override on any mode);
                                default-on for NOX_ADAPTER_MODE=phaseIterB
    NOX_ITERB_ORCHESTRATOR_LLM — orchestrator model (default: gpt-4.1-mini)
    NOX_ITERB_ORCHESTRATOR_BASE_URL — orchestrator endpoint
                                  (default: https://api.openai.com/v1)
    NOX_ITERB_ORCHESTRATOR_API_KEY — auth bearer (default: OPENAI_API_KEY for
                                  gpt-*, GEMINI_API_KEY for gemini-*)
    NOX_ITERB_MAX_ROUNDS      — int, hard cap on rounds per query (default: 5)
    NOX_ITERB_PER_ROUND_TOPK  — int, top_k per round retrieve (default: 10)
    NOX_ITERB_RRF_K           — int, RRF constant for chunk union (default: 60)
    NOX_ITERB_ORCHESTRATOR_TIMEOUT_S — float, per-round LLM timeout
                                       (default: 45)
    NOX_ITERB_ORCHESTRATOR_MAX_TOKENS — int, orchestrator output cap
                                        (default: 400 — JSON action object)
    NOX_ITERB_COST_CEILING_USD — float, hard cost cap per query (default: 0.01)
    NOX_ITERB_INPUT_COST_PER_1M — float, USD per 1M input tokens
                                  (default: 0.40 — gpt-4.1-mini)
    NOX_ITERB_OUTPUT_COST_PER_1M — float, USD per 1M output tokens
                                   (default: 1.60 — gpt-4.1-mini)
    NOX_ITERB_DEBUG           — "1" to log per-round action + cost + scratchpad
    NOX_ITERC_ANSWERER_MAX_TOKENS — int, per-sub-Q answer cap (default: 160 —
                                    intermediate answers are short)
    NOX_ITERC_DEBUG           — "1" to log decompositions + sub-answers + RRF
"""
import asyncio
import os
import shlex
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

# ---------------------------------------------------------------------------
# BaseAdapter import: adjust path when placed inside EverMemBench tree
# ---------------------------------------------------------------------------
try:
    from eval.src.adapters.base import BaseAdapter
    from eval.src.core.data_models import Dataset, GroupChatMessage, AddResult, SearchResult
except ImportError:
    # Stub imports for skeleton validation without EverMemBench installed
    from typing import Protocol
    class BaseAdapter(Protocol):  # type: ignore[no-redef]
        pass
    Dataset = Any  # type: ignore[assignment,misc]
    AddResult = Any  # type: ignore[assignment,misc]
    SearchResult = Any  # type: ignore[assignment,misc]
    GroupChatMessage = Any  # type: ignore[assignment,misc]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_NOX_API_BASE = "http://127.0.0.1:18802"
DEFAULT_NOX_MEM_BIN = "nox-mem"

# ---------------------------------------------------------------------------
# Phase B chunking strategy (2026-05-28)
# ---------------------------------------------------------------------------
# Per-message H2 block. Metadata in header + structured lead lines so both
# BM25 (FTS5) and Gemini-embedding retrieval bind to speaker / group / time
# / preceding context.
PHASEB_MESSAGE_BLOCK = (
    "## [{time} | {group} | {speaker}]\n"
    "speaker: {speaker}\n"
    "group: {group}\n"
    "date: {date}\n"
    "time: {time}\n"
    "context: {context}\n"
    "content: {content}\n"
)

# Daily group rollup -- emitted once per (date, group) tuple after all
# messages of that day-group are written. Helps temporal queries.
PHASEB_DAY_GROUP_ROLLUP = (
    "## Day {date} -- {group} digest\n"
    "group: {group}\n"
    "date: {date}\n"
    "participants: {participants}\n"
    "message_count: {message_count}\n"
    "summary: Conversation on {date} in {group} between {participants_short}. "
    "First line: {first_line}\n"
)

# Legacy baseline template (kept for ablation fallback via NOX_ADAPTER_MODE=baseline)
MESSAGE_TEMPLATE = "[Group: {group}][Speaker: {speaker}][Time: {time}] {content}"

# How many messages per batched ingest subprocess call.
DEFAULT_INGEST_BATCH_SIZE = 50

# Timeout (seconds) per `nox-mem ingest` subprocess call.
INGEST_SUBPROCESS_TIMEOUT = 180

# Adapter mode default.
DEFAULT_ADAPTER_MODE = "phaseB"

# How many preceding turns (same group) to embed as "context" per chunk.
PHASEB_CONTEXT_WINDOW = 2

# Phase F cross-encoder reranker defaults.
DEFAULT_RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"
DEFAULT_RERANKER_OVERFETCH = 50
DEFAULT_RERANKER_BATCH_SIZE = 32
DEFAULT_RERANKER_MAX_LENGTH = 512

# Phase KG (Lab Q1 #4) — KG 1-hop boost defaults.
#
# BASE_DELTA = 0.05 per spec §8.6 — scaled to typical RRF score range (0.01-0.1).
# DIRECT_MULTIPLIER = 1.5 → directly-mentioned entities get 1.5× neighbor boost
# per spec §3.A. MAX_NEIGHBORS prevents pathological cases where a high-degree
# entity (e.g. a hub person in the chat) floods the boost candidate set.
# MIN_NAME_LEN = 3 avoids regex false positives on short tokens like "i", "of".
DEFAULT_KG_BOOST_MAGNITUDE = 0.05
DEFAULT_KG_DIRECT_MULTIPLIER = 1.5
DEFAULT_KG_MAX_NEIGHBORS = 20
DEFAULT_KG_MIN_NAME_LEN = 3
DEFAULT_KG_OVERFETCH = 50  # pull top-50 from API so KG can re-rank within

# Phase MAP (Lab Q1 #2 / PR #386) — MA-protection bypass-entity defaults.
#
# ENTITY_SECTION_NAMES = nox-mem entity-file section markers (schema v10). A
# chunk whose `section` column is in this set is considered "entity-style"
# context (compiled truth section OR frontmatter metadata). Rerank is bypassed
# for these chunks to preserve Memory Awareness (profile / preference) recall.
#
# Wave B composability (this phase): when NOX_MA_PROTECTION_KG_ANCHOR=1, the
# bypass set is extended with `chunk_id IN kg_evidence_chunks_for_query_entities`
# so the mechanism fires on chat-only corpora (EverMemBench) too — without
# touching the protection logic for prod-style corpora.
#
# DEFAULT_MA_PROTECTION_MAX caps the protected set per query to avoid
# degenerate cases (a single high-degree hub entity could otherwise pin the
# top-K to its evidence chunks alone, starving non-entity hard-recall).
ENTITY_SECTION_NAMES = frozenset({"compiled", "frontmatter"})
DEFAULT_MA_PROTECTION_MAX = 25

# Phase MQ (Lab Q1 #3) — Multi-query expansion (Approach B) defaults.
#
# N=4 sub-queries balances cost vs coverage (spec §2.B). PER_QUERY_TOPK=10
# matches Phase H v2 top_k=10 retrieval, keeping per-query latency stable.
# RRF_K=60 is the canonical RRF constant (BM25+dense fusion); we reuse it for
# cross-sub-query fusion. Mitigation §7.6 calls out k=30/k=90 as ablation
# targets if results indicate sub-query correlation issues.
# TIMEOUT_S=30 is generous; flash-lite typically returns in 1-3s.
DEFAULT_MQ_LLM = "gemini-2.5-flash-lite"
DEFAULT_MQ_LLM_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
DEFAULT_MQ_N = 4
DEFAULT_MQ_PER_QUERY_TOPK = 10
DEFAULT_MQ_RRF_K = 60
DEFAULT_MQ_TIMEOUT_S = 30.0

# Decomposition prompt — explicit instruction to:
#   1. produce JSON array of strings (parseable)
#   2. preserve language of original query (PT-BR / EN)
#   3. atomic sub-questions (each independently answerable)
#   4. cap N (spec §2.B target 3-5)
PHASEMQ_DECOMPOSE_PROMPT = (
    "Decompose the following question into {n} atomic sub-questions that "
    "together cover all aspects needed to answer the original. Each "
    "sub-question MUST be independently answerable and use the SAME language "
    "as the original. Return ONLY a JSON array of strings, no prose, no "
    "markdown fences.\n\n"
    "Question: {query}\n\n"
    "JSON array:"
)


# ---------------------------------------------------------------------------
# Phase IterC (Q3 POC) — Self-Ask defaults
# ---------------------------------------------------------------------------
#
# N=3 sub-questions — Self-Ask paper (arxiv:2210.03350) reports best results
# at 2-4 sub-Qs for 2-3 hop questions. EverMemBench multi-hop is typically
# 2-3 hops (per Phase G analysis). N=3 hits the sweet spot.
#
# PER_QUERY_TOPK=10 matches Phase H v2 baseline retrieval shape — keeps
# per-sub-Q latency stable.
#
# RRF_K=60 reuses MQ canonical constant. Chunk-union mechanism is
# mechanically identical to Phase MQ.
#
# ANSWERER_MAX_TOKENS=160 — intermediate sub-answers should be short factual
# strings ("Mingzhi Li was the lead reviewer", "Date: 2024-11-15"), NOT full
# essays. Caps cost.
#
# ANSWERER_TIMEOUT_S=45 — 3 sub-answers run in parallel via asyncio.gather,
# so wall time ≈ slowest one; 45s gives margin for gpt-4.1-mini cold start.
DEFAULT_ITERC_DECOMPOSER_LLM = "gemini-2.5-flash-lite"
DEFAULT_ITERC_DECOMPOSER_BASE_URL = (
    "https://generativelanguage.googleapis.com/v1beta/openai"
)
DEFAULT_ITERC_ANSWERER_LLM = "gpt-4.1-mini"
DEFAULT_ITERC_ANSWERER_BASE_URL = "https://api.openai.com/v1"
DEFAULT_ITERC_N = 3
DEFAULT_ITERC_PER_QUERY_TOPK = 10
DEFAULT_ITERC_RRF_K = 60
DEFAULT_ITERC_DECOMPOSER_TIMEOUT_S = 30.0
DEFAULT_ITERC_ANSWERER_TIMEOUT_S = 45.0
DEFAULT_ITERC_ANSWERER_MAX_TOKENS = 160

# Self-Ask decomposition prompt — distinct from Phase MQ because Self-Ask
# explicitly frames sub-questions as "follow-up questions a system would
# need to answer in order to answer the original". This framing matters:
# the LLM produces more *sequenced* / *causal* sub-Qs vs MQ's *parallel
# coverage* sub-Qs. Both return JSON arrays — parser is reused.
PHASE_ITERC_DECOMPOSE_PROMPT = (
    "You are a Self-Ask decomposer (Press et al. 2022). The user has a "
    "multi-hop question that needs intermediate sub-questions answered in "
    "sequence to arrive at the final answer. Decompose the question into "
    "{n} atomic follow-up sub-questions a downstream system should answer "
    "to gather the facts needed for the final answer.\n\n"
    "Each sub-question MUST:\n"
    "  - be independently answerable from a memory store of group-chat "
    "messages\n"
    "  - target ONE atomic fact (person, date, place, event, attribute)\n"
    "  - use the SAME language as the original question\n\n"
    "Return ONLY a JSON array of strings — no prose, no markdown fences, "
    "no numbering.\n\n"
    "Original question: {query}\n\n"
    "JSON array of {n} sub-questions:"
)

# Per-sub-question answerer prompt — instruct gpt-4.1-mini to answer the
# sub-Q using ONLY the chunks retrieved for IT, and to keep the answer
# atomic (a short fact). If the chunks don't contain the answer, the model
# returns "UNKNOWN" (parseable, no hallucination penalty).
PHASE_ITERC_ANSWERER_PROMPT = (
    "You are a memory-grounded sub-question answerer. Use ONLY the "
    "retrieved memory chunks below. If they don't contain the answer "
    "return the literal string UNKNOWN.\n\n"
    "Sub-question: {subq}\n\n"
    "Retrieved memory chunks:\n{chunks}\n\n"
    "Answer (atomic fact or UNKNOWN, no prose):"
)


# ---------------------------------------------------------------------------
# Phase IterB (Q3 POC) — ReAct (Yao et al. 2022, arxiv:2210.03629)
# ---------------------------------------------------------------------------
#
# Loop until answer found OR max_rounds (default 5). Each round the
# orchestrator LLM emits structured JSON with either:
#   {"thought": "...", "action": "retrieve", "query": "..."}
#   {"thought": "...", "action": "answer", "answer": "..."}
#
# Termination:
#   - max_rounds=5 (hard cap)
#   - LLM signals "action": "answer"
#   - Cost ceiling per query ≤ NOX_ITERB_COST_CEILING_USD (default 0.005)
#
# Orchestrator backbone: gpt-4.1-mini by default (~$0.001/round × 3-5 rounds
# = $0.003-0.005/q). Also support Gemini-3-flash variant via
# NOX_ITERB_ORCHESTRATOR_LLM env override (cheap variant).
#
# Per-round retrieval re-uses the SAME /api/search endpoint as Phase H v2
# (top_k=NOX_ITERB_PER_ROUND_TOPK, default 10). Chunk-union across rounds
# uses the same RRF mechanism as Phase MQ/IterC (RRF_K=60), so signal stays
# comparable.
#
# Set E per-query instrumentation:
#   - rounds_executed (max NOX_ITERB_MAX_ROUNDS)
#   - per-round chunks retrieved
#   - per-round chunk overlap with prior rounds (Jaccard)
#   - termination reason ("answer", "max_rounds", "cost_ceiling", "error")
#   - per-round latency (decode + retrieve)
#   - total cost in USD (estimated via token counts × per-1M rates)
DEFAULT_ITERB_ORCHESTRATOR_LLM = "gpt-4.1-mini"
DEFAULT_ITERB_ORCHESTRATOR_BASE_URL = "https://api.openai.com/v1"
DEFAULT_ITERB_MAX_ROUNDS = 5
DEFAULT_ITERB_PER_ROUND_TOPK = 10
DEFAULT_ITERB_RRF_K = 60
DEFAULT_ITERB_ORCHESTRATOR_TIMEOUT_S = 45.0
DEFAULT_ITERB_ORCHESTRATOR_MAX_TOKENS = 400
DEFAULT_ITERB_COST_CEILING_USD = 0.01  # gate 4 ceiling
# Token cost estimates (USD per 1M tokens). Defaults reflect gpt-4.1-mini
# public pricing 2026-05 ($0.40 input / $1.60 output). Override via env if
# switching backbone (e.g. Gemini-3-flash $0.30/$2.50).
DEFAULT_ITERB_INPUT_COST_PER_1M = 0.40
DEFAULT_ITERB_OUTPUT_COST_PER_1M = 1.60

# ReAct orchestrator prompt — structured JSON output to make termination
# unambiguous. The LLM gets the original query + a running scratchpad of
# (thought, action, observation) triples from prior rounds.
PHASE_ITERB_ORCHESTRATOR_PROMPT = (
    "You are a ReAct orchestrator (Yao et al. 2022) answering a multi-hop "
    "question over a memory store of group-chat messages.\n\n"
    "At each round you may issue ONE of two actions:\n"
    "  1. retrieve — emit a sub-query string to fetch more memory chunks\n"
    "  2. answer — emit the final answer when you have enough evidence\n\n"
    "Rules:\n"
    "  - Use ONLY facts from the observations below (no hallucination)\n"
    "  - Prefer retrieve when you do NOT yet have enough evidence\n"
    "  - You have up to {max_rounds} rounds total; you are on round {round}\n"
    "  - On the last round you MUST emit answer (final round forces synthesis)\n"
    "  - Keep retrieve sub-queries ATOMIC (one fact / entity / date per query)\n"
    "  - Use the SAME language as the original question\n\n"
    "Output ONLY a JSON object — no prose, no markdown fences:\n"
    "  {{\"thought\": \"...\", \"action\": \"retrieve\", \"query\": \"...\"}}\n"
    "  {{\"thought\": \"...\", \"action\": \"answer\", \"answer\": \"...\"}}\n\n"
    "Original question: {query}\n\n"
    "Scratchpad (prior rounds):\n{scratchpad}\n\n"
    "Round {round} JSON output:"
)


# ---------------------------------------------------------------------------
# Reranker singleton loader
# ---------------------------------------------------------------------------
#
# Cached so each Python process loads the model once (~600MB on disk, ~2-3GB
# resident). Lazy: only imported when phaseF actually runs.
# Returns (model_or_None, error_or_None). On failure (missing package,
# download error, OOM), error is a string and the caller falls back to
# non-reranked results gracefully.
# ---------------------------------------------------------------------------
import functools as _functools  # noqa: E402  — local-only alias


@_functools.lru_cache(maxsize=1)
def _load_reranker(model_id: str, max_length: int) -> Tuple[Any, Optional[str]]:
    try:
        from sentence_transformers import CrossEncoder  # type: ignore[import-not-found]
    except Exception as exc:  # noqa: BLE001
        return None, f"sentence_transformers import failed: {type(exc).__name__}: {exc}"

    try:
        model = CrossEncoder(model_id, max_length=max_length)
    except Exception as exc:  # noqa: BLE001
        return None, f"CrossEncoder({model_id}) load failed: {type(exc).__name__}: {exc}"

    return model, None


# ---------------------------------------------------------------------------
# Phase KG (Lab Q1 #4) — KG path retrieval helpers
# ---------------------------------------------------------------------------
#
# These helpers run direct SQLite queries against the same DB the api-server
# is using. They are read-only (SELECT only) and use the FK schema documented
# in `[[kg-relations-uses-fk-ids-not-inline-strings]]`:
#
#   kg_entities (id, name, entity_type, mention_count, attributes, ...)
#   kg_relations (id, source_entity_id, relation_type, target_entity_id,
#                 evidence_chunk_id, confidence, ...)
#
# Important: SQLite WAL mode + concurrent readers are SAFE — the api-server
# holds its own connection, and our read-only connection sees a snapshot.
# We open and cache a single read-only connection per (db_path, process).


@_functools.lru_cache(maxsize=4)
def _kg_open_db(db_path: str) -> Tuple[Any, Optional[str]]:
    """Open a read-only SQLite connection to the KG DB. Cached per path."""
    import sqlite3 as _sqlite3
    try:
        # URI mode + mode=ro = read-only, will not interfere with api-server.
        conn = _sqlite3.connect(
            f"file:{db_path}?mode=ro",
            uri=True,
            check_same_thread=False,
            timeout=5.0,
        )
        # Confirm KG tables exist
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name IN ('kg_entities','kg_relations')"
        ).fetchall()
        if len(row) < 2:
            return None, f"KG tables missing in {db_path} (found {[r[0] for r in row]})"
    except Exception as exc:  # noqa: BLE001
        return None, f"sqlite3.connect failed: {type(exc).__name__}: {exc}"
    return conn, None


@_functools.lru_cache(maxsize=8)
def _kg_load_entity_names(db_path: str, min_name_len: int) -> Tuple[Tuple[Tuple[int, str], ...], Optional[str]]:
    """Load all (id, name) pairs from kg_entities with len(name) >= min_name_len.

    Cached as tuple-of-tuples so the lru_cache key is hashable. Names are
    lowercased here once so per-query regex matching is cheap.
    """
    conn, err = _kg_open_db(db_path)
    if err is not None or conn is None:
        return (), err

    try:
        rows = conn.execute(
            "SELECT id, LOWER(name) FROM kg_entities "
            "WHERE LENGTH(name) >= ? "
            "ORDER BY mention_count DESC",
            (min_name_len,),
        ).fetchall()
    except Exception as exc:  # noqa: BLE001
        return (), f"kg_entities query failed: {type(exc).__name__}: {exc}"

    return tuple((int(r[0]), str(r[1])) for r in rows), None


def _kg_extract_query_entities(
    query: str,
    entity_pool: Tuple[Tuple[int, str], ...],
    max_entities: int = 10,
) -> List[Tuple[int, str]]:
    """Regex-extract entity mentions from query against KG entity pool.

    Approach A (cheapest): substring match. Lowercases query once, then
    iterates entity_pool (already lowercased) checking presence. Returns
    list of (entity_id, entity_name) tuples in pool order (which is
    mention_count DESC) up to `max_entities`.

    Why substring (not word boundary): EverMemBench entity names are
    multi-token person/group names (e.g. "Weihua Zhang", "Group 1") and
    Unicode word boundary regex `\b` is unreliable in PT-BR / accented
    contexts — per [[js-regex-unicode-word-boundary-fails]], same caveat
    applies to Python `re` with `\b`. We use substring containment with a
    `min_name_len` >= 3 filter to control false positives.
    """
    import re as _re

    q_lower = query.lower()
    matched: List[Tuple[int, str]] = []
    seen: set = set()
    for ent_id, ent_name_lc in entity_pool:
        if ent_id in seen:
            continue
        # Whole-word-ish match: name surrounded by non-alphanumeric or string edges.
        # This is more robust than naive `in` (e.g. avoids matching "al" inside "alpha").
        # We still avoid `\b` because non-ASCII unicode breaks JS regex; in Python
        # `re.UNICODE` works but we prefer explicit boundary chars for portability.
        pattern = r'(?:^|[^a-z0-9])' + _re.escape(ent_name_lc) + r'(?:$|[^a-z0-9])'
        if _re.search(pattern, q_lower):
            matched.append((ent_id, ent_name_lc))
            seen.add(ent_id)
            if len(matched) >= max_entities:
                break
    return matched


def _kg_get_1hop_neighbors(
    db_path: str,
    entity_ids: List[int],
    max_neighbors_per_entity: int,
) -> List[Tuple[int, int, float, int]]:
    """Return 1-hop neighbors of given entity_ids.

    Returns list of tuples: (neighbor_entity_id, evidence_chunk_id, confidence,
    source_entity_id). evidence_chunk_id may be 0 if not set on the relation
    (we filter those out at boost time — they don't contribute to chunk boost).

    Walks both directions: relations where source IS the seed AND relations
    where target IS the seed. The "neighbor" is always the other end of the
    edge from the seed.

    Per [[kg-relations-uses-fk-ids-not-inline-strings]]: use FK ids, not names.
    """
    conn, err = _kg_open_db(db_path)
    if err is not None or conn is None or not entity_ids:
        return []

    placeholders = ",".join("?" * len(entity_ids))
    # Outbound edges: seed = source_entity_id, neighbor = target_entity_id
    # Inbound edges:  seed = target_entity_id, neighbor = source_entity_id
    sql = f"""
        SELECT target_entity_id AS neighbor, evidence_chunk_id, confidence, source_entity_id
        FROM kg_relations
        WHERE source_entity_id IN ({placeholders})
          AND target_entity_id NOT IN ({placeholders})
          AND target_entity_id IS NOT NULL
        UNION ALL
        SELECT source_entity_id AS neighbor, evidence_chunk_id, confidence, target_entity_id
        FROM kg_relations
        WHERE target_entity_id IN ({placeholders})
          AND source_entity_id NOT IN ({placeholders})
          AND source_entity_id IS NOT NULL
    """
    try:
        rows = conn.execute(sql, entity_ids * 4).fetchall()
    except Exception:  # noqa: BLE001
        return []
    # Cap per-seed neighbor count to avoid hub flooding
    by_seed: Dict[int, List[Tuple[int, int, float, int]]] = {}
    for n, ev, conf, seed in rows:
        bucket = by_seed.setdefault(int(seed), [])
        if len(bucket) < max_neighbors_per_entity:
            bucket.append((int(n), int(ev or 0), float(conf or 0.0), int(seed)))
    out: List[Tuple[int, int, float, int]] = []
    for bucket in by_seed.values():
        out.extend(bucket)
    return out


def _kg_get_direct_chunk_ids(
    db_path: str,
    entity_ids: List[int],
) -> set:
    """Return chunk_ids that are direct evidence for the given (directly-mentioned) entities.

    A chunk is "direct evidence" for an entity if any relation where the entity
    appears as source OR target lists that chunk in evidence_chunk_id.
    """
    conn, err = _kg_open_db(db_path)
    if err is not None or conn is None or not entity_ids:
        return set()

    placeholders = ",".join("?" * len(entity_ids))
    sql = f"""
        SELECT DISTINCT evidence_chunk_id FROM kg_relations
        WHERE (source_entity_id IN ({placeholders}) OR target_entity_id IN ({placeholders}))
          AND evidence_chunk_id IS NOT NULL
    """
    try:
        rows = conn.execute(sql, entity_ids * 2).fetchall()
    except Exception:  # noqa: BLE001
        return set()
    return {int(r[0]) for r in rows if r[0]}


# ---------------------------------------------------------------------------
# Phase MAP (Lab Q1 #2 / PR #386) — MA-protection bypass-entity helpers
# ---------------------------------------------------------------------------
#
# Approach A from spec `specs/2026-05-28-ma-protection-rerank.md` §2:
# partition top-N retrieved candidates into Set E (entity-style chunks to
# protect) and Set R (rest to rerank). After cross-encoder rerank, merge so
# that Set E chunks land at the position they held in the bi-encoder
# ordering, and Set R fills the remaining slots in rerank order.
#
# Wave B composability (this PR): Set E may include KG-evidence chunks for
# the query-mentioned entities. See `_kg_anchor_protected_chunk_ids`.
#
# Rationale (lessons cravadas):
#   - `[[ma-protection-needs-entity-corpus-or-kg-anchor]]` — pure section
#     approach was empty on EverMemBench (Set E ∅ for 3125/3125 queries).
#   - `[[empirical-set-e-empty-confirms-mechanism-not-corpus]]` — instrument
#     bypass count per query; if Set E + Set KG = ∅ everywhere, mechanism
#     didn't fire and we surface that in metadata.


def _ma_extract_protected_chunk_ids_section(
    candidates: List[Tuple[str, Dict[str, Any]]],
) -> set:
    """Identify candidate chunk_ids whose `section` field is in ENTITY_SECTION_NAMES.

    Returns a set of chunk_id ints. Skips candidates whose chunk_id is
    missing or non-integer (treated as non-protected).
    """
    protected: set = set()
    for _content, item in candidates:
        section = item.get("section")
        if section is None:
            continue
        if str(section).lower() not in ENTITY_SECTION_NAMES:
            continue
        cid = item.get("id") or item.get("chunk_id") or item.get("rowid")
        try:
            cid_int = int(cid) if cid is not None else None
        except (TypeError, ValueError):
            cid_int = None
        if cid_int is not None:
            protected.add(cid_int)
    return protected


def _ma_extract_protected_chunk_ids_kg_anchor(
    candidates: List[Tuple[str, Dict[str, Any]]],
    kg_evidence_chunk_ids: set,
) -> set:
    """Identify candidate chunk_ids that are KG-evidence for query entities.

    Intersection of `candidates` chunk_ids with `kg_evidence_chunk_ids`.
    This is the Wave B composability extension: even when section markers
    are absent (chat-only corpora), KG-anchored chunks can still be
    protected from rerank displacement.
    """
    if not kg_evidence_chunk_ids:
        return set()
    protected: set = set()
    for _content, item in candidates:
        cid = item.get("id") or item.get("chunk_id") or item.get("rowid")
        try:
            cid_int = int(cid) if cid is not None else None
        except (TypeError, ValueError):
            cid_int = None
        if cid_int is not None and cid_int in kg_evidence_chunk_ids:
            protected.add(cid_int)
    return protected


def _ma_partition_candidates(
    candidates: List[Tuple[str, Dict[str, Any]]],
    protected_chunk_ids: set,
    max_protected: int,
) -> Tuple[
    List[Tuple[int, Tuple[str, Dict[str, Any]]]],  # set_e: [(bi_position, candidate)]
    List[Tuple[str, Dict[str, Any]]],              # set_r: rest in bi-encoder order
]:
    """Partition candidates into Set E (protected, with original positions) and Set R.

    Caps Set E at `max_protected` (keeps the earliest bi-encoder positions —
    those are the strongest entity matches).

    Returns:
        set_e: list of (bi_position, candidate) tuples — protected chunks
               that will be re-inserted at their original bi-encoder rank
               position after rerank.
        set_r: list of candidates in bi-encoder order — sent to rerank.
    """
    set_e: List[Tuple[int, Tuple[str, Dict[str, Any]]]] = []
    set_r: List[Tuple[str, Dict[str, Any]]] = []
    for pos, (content, item) in enumerate(candidates):
        cid = item.get("id") or item.get("chunk_id") or item.get("rowid")
        try:
            cid_int = int(cid) if cid is not None else None
        except (TypeError, ValueError):
            cid_int = None
        if (
            cid_int is not None
            and cid_int in protected_chunk_ids
            and len(set_e) < max_protected
        ):
            set_e.append((pos, (content, item)))
        else:
            set_r.append((content, item))
    return set_e, set_r


def _ma_merge_preserving_protected_positions(
    set_e: List[Tuple[int, Tuple[str, Dict[str, Any]]]],
    set_r_reranked: List[Tuple[str, Dict[str, Any]]],
    total_slots: int,
) -> List[Tuple[str, Dict[str, Any]]]:
    """Merge protected (Set E) at bi-encoder positions + reranked (Set R) elsewhere.

    Mechanics (PR #386 spec):
      1. Allocate `total_slots` empty positions.
      2. For each (bi_position, cand) in set_e: place cand at bi_position
         (clamped to total_slots-1 if bi_position >= total_slots).
      3. Fill remaining empty positions with set_r_reranked in rerank order.

    Edge cases:
      - set_e overflows total_slots → keep first N (earliest bi positions).
      - set_r_reranked shorter than empty-slot count → tail compacted (skip).
      - set_e empty → all reranked (degenerate case = Phase F behaviour).
      - set_r empty → only protected (degenerate case = "everything is entity").
    """
    if total_slots <= 0:
        return []
    if not set_e and not set_r_reranked:
        return []
    if not set_e:
        return list(set_r_reranked[:total_slots])
    if not set_r_reranked:
        # Return Set E in original bi-encoder order, capped at total_slots.
        sorted_e = sorted(set_e, key=lambda x: x[0])
        return [cand for _, cand in sorted_e[:total_slots]]

    # Sort Set E by original position. Clamp positions to total_slots-1.
    sorted_e = sorted(set_e, key=lambda x: x[0])
    placed: List[Optional[Tuple[str, Dict[str, Any]]]] = [None] * total_slots
    taken: set = set()
    for bi_pos, cand in sorted_e:
        slot = min(bi_pos, total_slots - 1)
        # If slot already taken (multiple protected mapped to same clamped slot),
        # find next free slot forward, then backward.
        if slot in taken:
            free = next((s for s in range(slot, total_slots) if s not in taken), None)
            if free is None:
                free = next((s for s in range(slot - 1, -1, -1) if s not in taken), None)
            if free is None:
                continue  # no free slot, drop this protected
            slot = free
        placed[slot] = cand
        taken.add(slot)

    # Fill remaining empty positions with reranked items in order
    r_iter = iter(set_r_reranked)
    for i in range(total_slots):
        if placed[i] is None:
            try:
                placed[i] = next(r_iter)
            except StopIteration:
                break

    # Compact: drop trailing None entries (case: set_r exhausted)
    return [c for c in placed if c is not None]


# ---------------------------------------------------------------------------
# Phase MQ (Lab Q1 #3) — Multi-query expansion helpers
# ---------------------------------------------------------------------------
#
# Decomposer calls an LLM (default gemini-flash-lite via OpenAI-compat
# endpoint) using an async aiohttp POST and parses the JSON array response.
# Designed to be backbone-agnostic: pass any OpenAI-compatible chat endpoint
# via NOX_MQ_LLM_BASE_URL + NOX_MQ_LLM_API_KEY.
#
# Returns (sub_queries, error). On any failure (HTTP error, JSON parse fail,
# too few sub-queries) returns ([], reason_str) and the caller falls back to
# single-query retrieval.


async def _mq_decompose_query(
    query: str,
    n: int,
    model: str,
    base_url: str,
    api_key: str,
    timeout_s: float,
    session: aiohttp.ClientSession,
) -> Tuple[List[str], Optional[str]]:
    """Call LLM to decompose query into N atomic sub-questions.

    Returns (sub_queries, error). sub_queries is the parsed list (may be
    empty if LLM returned an empty/malformed payload).
    """
    import json as _json
    import re as _re

    prompt = PHASEMQ_DECOMPOSE_PROMPT.format(n=n, query=query)
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 400,
    }
    endpoint = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try:
        async with session.post(
            endpoint,
            json=payload,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=timeout_s),
        ) as resp:
            if resp.status != 200:
                body = (await resp.text())[:300]
                return [], f"decomposer HTTP {resp.status}: {body}"
            data = await resp.json()
    except asyncio.TimeoutError:
        return [], f"decomposer timeout after {timeout_s}s"
    except aiohttp.ClientError as exc:
        return [], f"decomposer client error: {type(exc).__name__}: {exc}"
    except Exception as exc:  # noqa: BLE001
        return [], f"decomposer unexpected: {type(exc).__name__}: {exc}"

    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return [], f"decomposer malformed response: {str(data)[:200]}"

    # Try strict JSON parse first. If LLM wrapped in ```json fences,
    # strip them. If still not parseable, extract array via regex fallback.
    candidate = text.strip()
    # Strip code fences
    if candidate.startswith("```"):
        candidate = _re.sub(r"^```(?:json)?\s*", "", candidate)
        candidate = _re.sub(r"\s*```\s*$", "", candidate)
        candidate = candidate.strip()

    sub_queries: List[str] = []
    try:
        parsed = _json.loads(candidate)
        if isinstance(parsed, list):
            sub_queries = [str(x).strip() for x in parsed if str(x).strip()]
    except _json.JSONDecodeError:
        # Fallback: line-by-line parse (LLM may have returned numbered list)
        for line in candidate.splitlines():
            stripped = line.strip()
            # Strip JSON array brackets / commas / quotes
            stripped = _re.sub(r'^[\[\],\s"\']+', "", stripped)
            stripped = _re.sub(r'[\],\s"\']+$', "", stripped)
            # Strip numbered prefix "1." / "2)"
            stripped = _re.sub(r"^\d+[\.\):]\s*", "", stripped)
            stripped = stripped.strip().strip('"').strip("'").strip()
            if len(stripped) > 5 and "?" in stripped or len(stripped) > 10:
                sub_queries.append(stripped)

    # Sanity: require at least 2 sub-queries to bother (else fall back)
    sub_queries = [s for s in sub_queries if len(s) >= 5]
    if len(sub_queries) < 2:
        return [], f"too few sub-queries parsed ({len(sub_queries)}); fallback to single"

    return sub_queries, None


def _mq_rrf_merge(
    per_subquery_results: List[List[Tuple[str, Dict[str, Any]]]],
    rrf_k: int,
) -> List[Tuple[str, Dict[str, Any]]]:
    """RRF merge results from N sub-query retrievals.

    Each per_subquery_results[i] is the API rank-ordered list of (content, item)
    from sub-query i. We compute, for each unique chunk_id (or content fallback),
    score = sum over sub-queries it appeared in of 1 / (rrf_k + rank).

    Chunks appearing in multiple sub-queries naturally get higher score
    (cross-sub-query convergence), without any multiplicative stacking.

    Dedup key precedence: item.get("id") | item.get("chunk_id") | content hash.
    Returns the merged candidates in score-desc order. The dict item that
    survives is the first occurrence (typically the highest-ranked across
    sub-queries by API rank in its first appearance).
    """
    score_by_key: Dict[Any, float] = {}
    first_item_by_key: Dict[Any, Tuple[str, Dict[str, Any]]] = {}
    sub_count_by_key: Dict[Any, int] = {}

    for sub_results in per_subquery_results:
        for rank, (content, item) in enumerate(sub_results):
            # Build a stable key
            key = (
                item.get("id")
                or item.get("chunk_id")
                or item.get("rowid")
                or hash(content)
            )
            score_by_key[key] = score_by_key.get(key, 0.0) + 1.0 / (rrf_k + rank + 1)
            sub_count_by_key[key] = sub_count_by_key.get(key, 0) + 1
            if key not in first_item_by_key:
                # Annotate metadata so downstream can see convergence
                item_copy = dict(item)
                first_item_by_key[key] = (content, item_copy)

    # Stitch the merged candidates and sort by score desc.
    merged: List[Tuple[float, Tuple[str, Dict[str, Any]]]] = []
    for key, score in score_by_key.items():
        content, item = first_item_by_key[key]
        # Annotate aggregate metadata
        item["_mq_rrf_score"] = score
        item["_mq_subquery_count"] = sub_count_by_key[key]
        merged.append((score, (content, item)))

    merged.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in merged]


# ---------------------------------------------------------------------------
# Phase IterC (Q3 POC) — Self-Ask helpers
# ---------------------------------------------------------------------------
#
# We deliberately keep these as module-level helpers (parallel to MQ) so
# they are unit-testable in isolation and can be reused later by Q3 IterB
# (ReAct) which will iterate multiple Self-Ask-like rounds.
#
# Reuse PHASEMQ JSON parsing logic via _mq_decompose_query? No — the prompt
# differs (Self-Ask framing is causal/sequential, MQ is parallel coverage).
# Keep them separate so spec evolution doesn't cross-contaminate. The JSON
# parsing is small enough to copy.


async def _iterc_decompose_query(
    query: str,
    n: int,
    model: str,
    base_url: str,
    api_key: str,
    timeout_s: float,
    session: aiohttp.ClientSession,
) -> Tuple[List[str], Optional[str]]:
    """Self-Ask decomposer. Returns (sub_questions, error)."""
    import json as _json
    import re as _re

    prompt = PHASE_ITERC_DECOMPOSE_PROMPT.format(n=n, query=query)
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 500,
    }
    endpoint = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try:
        async with session.post(
            endpoint,
            json=payload,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=timeout_s),
        ) as resp:
            if resp.status != 200:
                body = (await resp.text())[:300]
                return [], f"iterc decomposer HTTP {resp.status}: {body}"
            data = await resp.json()
    except asyncio.TimeoutError:
        return [], f"iterc decomposer timeout after {timeout_s}s"
    except aiohttp.ClientError as exc:
        return [], f"iterc decomposer client error: {type(exc).__name__}: {exc}"
    except Exception as exc:  # noqa: BLE001
        return [], f"iterc decomposer unexpected: {type(exc).__name__}: {exc}"

    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return [], f"iterc decomposer malformed response: {str(data)[:200]}"

    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = _re.sub(r"^```(?:json)?\s*", "", candidate)
        candidate = _re.sub(r"\s*```\s*$", "", candidate)
        candidate = candidate.strip()

    sub_qs: List[str] = []
    try:
        parsed = _json.loads(candidate)
        if isinstance(parsed, list):
            sub_qs = [str(x).strip() for x in parsed if str(x).strip()]
    except _json.JSONDecodeError:
        for line in candidate.splitlines():
            stripped = line.strip()
            stripped = _re.sub(r'^[\[\],\s"\']+', "", stripped)
            stripped = _re.sub(r'[\],\s"\']+$', "", stripped)
            stripped = _re.sub(r"^\d+[\.\):]\s*", "", stripped)
            stripped = stripped.strip().strip('"').strip("'").strip()
            if len(stripped) > 5 and "?" in stripped or len(stripped) > 10:
                sub_qs.append(stripped)

    sub_qs = [s for s in sub_qs if len(s) >= 5]
    if len(sub_qs) < 2:
        return [], f"too few sub-questions parsed ({len(sub_qs)}); fallback to single"

    return sub_qs, None


async def _iterc_answer_subquestion(
    subq: str,
    chunks: List[str],
    model: str,
    base_url: str,
    api_key: str,
    timeout_s: float,
    max_tokens: int,
    session: aiohttp.ClientSession,
) -> Tuple[str, Optional[str]]:
    """Answer one sub-question using its retrieved chunks.

    Returns (sub_answer, error). On any failure (HTTP error, malformed
    response, empty answer) returns ("", error_str) and the caller treats
    the sub-Q as unanswered (chunks still feed the union; intermediate
    block is dropped from context).
    """
    if not chunks:
        return "UNKNOWN", None  # cheap: skip LLM call when no evidence

    # Truncate chunks to fit a reasonable prompt budget. Keep top-N (already
    # API-rank ordered). 6 × ~400 char chunks ≈ 2.4k chars context.
    chunk_block = "\n\n".join(
        f"[{i+1}] {c[:500]}" for i, c in enumerate(chunks[:6])
    )
    prompt = PHASE_ITERC_ANSWERER_PROMPT.format(subq=subq, chunks=chunk_block)
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": max_tokens,
    }
    endpoint = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try:
        async with session.post(
            endpoint,
            json=payload,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=timeout_s),
        ) as resp:
            if resp.status != 200:
                body = (await resp.text())[:300]
                return "", f"iterc answerer HTTP {resp.status}: {body}"
            data = await resp.json()
    except asyncio.TimeoutError:
        return "", f"iterc answerer timeout after {timeout_s}s"
    except aiohttp.ClientError as exc:
        return "", f"iterc answerer client error: {type(exc).__name__}: {exc}"
    except Exception as exc:  # noqa: BLE001
        return "", f"iterc answerer unexpected: {type(exc).__name__}: {exc}"

    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return "", f"iterc answerer malformed response: {str(data)[:200]}"

    answer = text.strip()
    if not answer:
        return "UNKNOWN", None
    return answer, None


def _iterc_per_subquery_overlap(
    per_subquery_chunk_ids: List[List[Any]],
) -> float:
    """Compute mean Jaccard overlap between sub-question retrieval sets.

    High overlap (→ 1.0) means sub-questions retrieved mostly the same
    chunks (decomposition may be too narrow / redundant — risk for the
    Self-Ask mechanism). Low overlap (→ 0.0) means each sub-question
    retrieved a distinct chunk set (decomposition spans the multi-hop
    chain well — Self-Ask sweet spot).

    Returns mean pairwise Jaccard. 0.0 if fewer than 2 sub-queries.
    """
    if len(per_subquery_chunk_ids) < 2:
        return 0.0
    sets = [set(ids) for ids in per_subquery_chunk_ids if ids]
    if len(sets) < 2:
        return 0.0
    pairs = 0
    total = 0.0
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            si, sj = sets[i], sets[j]
            union = si | sj
            if not union:
                continue
            inter = si & sj
            total += len(inter) / len(union)
            pairs += 1
    return total / pairs if pairs > 0 else 0.0


# ---------------------------------------------------------------------------
# Phase IterB (Q3 POC) — ReAct helpers
# ---------------------------------------------------------------------------
#
# Module-level helpers (parallel to Phase MQ / Phase IterC) so they are
# unit-testable in isolation. The ReAct loop itself lives inside
# NoxMemAdapter.search() to keep aiohttp.ClientSession lifecycle clean,
# but the per-round LLM decoder + cost estimator + overlap calculator are
# pure functions here.


async def _iterb_orchestrator_step(
    query: str,
    scratchpad: str,
    round_idx: int,
    max_rounds: int,
    model: str,
    base_url: str,
    api_key: str,
    timeout_s: float,
    max_tokens: int,
    session: aiohttp.ClientSession,
) -> Tuple[Dict[str, Any], Optional[str], Dict[str, int]]:
    """One ReAct orchestrator round.

    Returns (parsed_action_dict, error_str_or_None, usage_dict).

    parsed_action_dict shape:
        {"thought": str, "action": "retrieve", "query": str}
        OR
        {"thought": str, "action": "answer", "answer": str}

    usage_dict shape: {"input_tokens": int, "output_tokens": int}
        (best-effort; falls back to zero if API doesn't return usage)

    On parse failure we degrade gracefully: returns action="answer" with
    answer="UNKNOWN" so the loop terminates and the harness still gets a
    final synthesis stage.
    """
    import json as _json
    import re as _re

    prompt = PHASE_ITERB_ORCHESTRATOR_PROMPT.format(
        max_rounds=max_rounds,
        round=round_idx,
        query=query,
        scratchpad=scratchpad if scratchpad else "(empty — round 1)",
    )
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": max_tokens,
    }
    endpoint = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    usage: Dict[str, int] = {"input_tokens": 0, "output_tokens": 0}
    try:
        async with session.post(
            endpoint,
            json=payload,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=timeout_s),
        ) as resp:
            if resp.status != 200:
                body = (await resp.text())[:300]
                return (
                    {"action": "answer", "answer": "UNKNOWN", "thought": ""},
                    f"iterb orchestrator HTTP {resp.status}: {body}",
                    usage,
                )
            data = await resp.json()
    except asyncio.TimeoutError:
        return (
            {"action": "answer", "answer": "UNKNOWN", "thought": ""},
            f"iterb orchestrator timeout after {timeout_s}s",
            usage,
        )
    except aiohttp.ClientError as exc:
        return (
            {"action": "answer", "answer": "UNKNOWN", "thought": ""},
            f"iterb orchestrator client error: {type(exc).__name__}: {exc}",
            usage,
        )
    except Exception as exc:  # noqa: BLE001
        return (
            {"action": "answer", "answer": "UNKNOWN", "thought": ""},
            f"iterb orchestrator unexpected: {type(exc).__name__}: {exc}",
            usage,
        )

    # Extract usage if returned
    u = data.get("usage", {}) if isinstance(data, dict) else {}
    if isinstance(u, dict):
        usage["input_tokens"] = int(u.get("prompt_tokens") or 0)
        usage["output_tokens"] = int(u.get("completion_tokens") or 0)

    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return (
            {"action": "answer", "answer": "UNKNOWN", "thought": ""},
            f"iterb orchestrator malformed response: {str(data)[:200]}",
            usage,
        )

    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = _re.sub(r"^```(?:json)?\s*", "", candidate)
        candidate = _re.sub(r"\s*```\s*$", "", candidate)
        candidate = candidate.strip()

    # First try JSON parse
    parsed: Optional[Dict[str, Any]] = None
    try:
        obj = _json.loads(candidate)
        if isinstance(obj, dict):
            parsed = obj
    except _json.JSONDecodeError:
        # Try to extract a JSON object embedded in prose
        m = _re.search(r"\{[^{}]*\"action\"[^{}]*\}", candidate, _re.DOTALL)
        if m:
            try:
                obj = _json.loads(m.group(0))
                if isinstance(obj, dict):
                    parsed = obj
            except _json.JSONDecodeError:
                parsed = None

    if parsed is None:
        # Last-ditch: regex extract action + query/answer
        action_m = _re.search(
            r"\"action\"\s*:\s*\"(retrieve|answer)\"", candidate
        )
        action = action_m.group(1) if action_m else "answer"
        if action == "retrieve":
            q_m = _re.search(r"\"query\"\s*:\s*\"([^\"]+)\"", candidate)
            if q_m:
                return (
                    {"action": "retrieve", "query": q_m.group(1), "thought": ""},
                    "iterb parsed via regex fallback (no clean JSON)",
                    usage,
                )
        a_m = _re.search(r"\"answer\"\s*:\s*\"([^\"]+)\"", candidate)
        if a_m:
            return (
                {"action": "answer", "answer": a_m.group(1), "thought": ""},
                "iterb parsed via regex fallback (no clean JSON)",
                usage,
            )
        # Treat the whole text as an answer
        return (
            {"action": "answer", "answer": candidate[:400] or "UNKNOWN", "thought": ""},
            "iterb fallback: treated raw text as answer",
            usage,
        )

    # Normalize action field
    action = str(parsed.get("action", "")).strip().lower()
    if action not in ("retrieve", "answer"):
        # Force answer on unrecognized action so loop terminates
        return (
            {
                "action": "answer",
                "answer": str(parsed.get("answer") or "UNKNOWN")[:400],
                "thought": str(parsed.get("thought", "")),
            },
            f"iterb unrecognized action '{action}', forced answer",
            usage,
        )

    if action == "retrieve":
        q = str(parsed.get("query", "")).strip()
        if not q:
            return (
                {"action": "answer", "answer": "UNKNOWN", "thought": str(parsed.get("thought", ""))},
                "iterb retrieve action missing 'query' field, forced answer",
                usage,
            )
        return (
            {"action": "retrieve", "query": q, "thought": str(parsed.get("thought", ""))},
            None,
            usage,
        )

    # action == answer
    ans = str(parsed.get("answer", "")).strip() or "UNKNOWN"
    return (
        {"action": "answer", "answer": ans[:1000], "thought": str(parsed.get("thought", ""))},
        None,
        usage,
    )


def _iterb_estimate_cost(
    input_tokens: int,
    output_tokens: int,
    input_cost_per_1m: float,
    output_cost_per_1m: float,
) -> float:
    """Estimate cost in USD given token counts + per-1M rates."""
    return (
        (input_tokens / 1_000_000.0) * input_cost_per_1m
        + (output_tokens / 1_000_000.0) * output_cost_per_1m
    )


def _iterb_per_round_overlap(
    per_round_chunk_ids: List[List[Any]],
) -> List[float]:
    """Per-round Jaccard overlap of round-i chunks with the UNION of all
    prior rounds (rounds 0..i-1).

    overlap[0] = 0.0 by definition (no prior rounds).
    overlap[i] = |round_i ∩ prior_union| / |round_i ∪ prior_union| for i ≥ 1.

    Low overlap on later rounds → ReAct is exploring NEW evidence each
    round (sweet spot — multi-hop progression). High overlap → orchestrator
    is going in circles (sub-queries redundant).
    """
    out: List[float] = []
    prior_union: set = set()
    for i, ids in enumerate(per_round_chunk_ids):
        s_i = set(ids) if ids else set()
        if i == 0 or not prior_union:
            out.append(0.0)
        else:
            union = s_i | prior_union
            if not union:
                out.append(0.0)
            else:
                inter = s_i & prior_union
                out.append(len(inter) / len(union))
        prior_union |= s_i
    return out


class NoxMemAdapter(BaseAdapter):
    """
    nox-mem adapter for EverMemBench multi-person group chat evaluation.

    Add stage:
        Writes group-chat messages to a temp markdown file (Phase B format
        when NOX_ADAPTER_MODE != "baseline"), then invokes `nox-mem ingest`
        via subprocess. Subprocess inherits NOX_DB_PATH for isolation.

    Search stage:
        Calls POST /api/search with the QA question text. The HTTP API must
        be started against the SAME NOX_DB_PATH that Add ingested into.

    Config YAML example (nox_mem.yaml):
    ```yaml
    name: "nox_mem"
    api_base: "${NOX_API_BASE}"
    nox_mem_bin: "${NOX_MEM_BIN}"
    search_top_k: 10
    search_timeout: 30
    ingest_batch_size: 50
    ingest_delay_ms: 0
    adapter_mode: "phaseB"
    ```
    """

    def __init__(self, config: Dict[str, Any], output_dir: Optional[Path] = None):
        super().__init__(config, output_dir)

        self.api_base = config.get("api_base", "").rstrip("/") or os.environ.get(
            "NOX_API_BASE", DEFAULT_NOX_API_BASE
        )
        self.nox_mem_bin = config.get("nox_mem_bin", "") or os.environ.get(
            "NOX_MEM_BIN", DEFAULT_NOX_MEM_BIN
        )
        self.search_top_k = config.get("search_top_k", 10)
        self.search_timeout = config.get("search_timeout", 30)
        self.ingest_batch_size = config.get("ingest_batch_size", DEFAULT_INGEST_BATCH_SIZE)
        self.ingest_delay_ms = config.get("ingest_delay_ms", 0)
        self.adapter_mode = (
            config.get("adapter_mode", "")
            or os.environ.get("NOX_ADAPTER_MODE", DEFAULT_ADAPTER_MODE)
        )
        self.context_window = int(
            config.get("phaseb_context_window", PHASEB_CONTEXT_WINDOW)
        )

        # Phase F cross-encoder rerank config (only consumed when
        # adapter_mode == "phaseF" AND NOX_RERANKER_ENABLED resolves truthy).
        self.reranker_model_id = config.get("reranker_model", "") or os.environ.get(
            "NOX_RERANKER_MODEL", DEFAULT_RERANKER_MODEL
        )
        self.reranker_overfetch = int(
            config.get("reranker_overfetch", 0)
            or os.environ.get("NOX_RERANKER_OVERFETCH", "")
            or DEFAULT_RERANKER_OVERFETCH
        )
        self.reranker_batch_size = int(
            config.get("reranker_batch_size", 0)
            or os.environ.get("NOX_RERANKER_BATCH_SIZE", "")
            or DEFAULT_RERANKER_BATCH_SIZE
        )
        self.reranker_max_length = int(
            config.get("reranker_max_length", 0)
            or DEFAULT_RERANKER_MAX_LENGTH
        )
        # Reranker is enabled either by being in phaseF / phaseMAP / phaseKGMAP
        # mode (default-on for those modes) OR by explicit env override on top
        # of any other mode. Phase MAP and Phase KGMAP both require rerank to
        # exist before bypass-entity has anything to bypass.
        env_enable = os.environ.get("NOX_RERANKER_ENABLED", "").strip().lower()
        env_enable_truthy = env_enable in ("1", "true", "yes", "on")
        env_enable_falsy = env_enable in ("0", "false", "no", "off")
        if env_enable_falsy:
            self.reranker_enabled = False
        elif env_enable_truthy:
            self.reranker_enabled = True
        else:
            self.reranker_enabled = self.adapter_mode in (
                "phaseF", "phaseMAP", "phaseKGMAP", "phaseTriple"
            )

        # Phase KG (Lab Q1 #4) — entity 1-hop boost config.
        # Enabled by phaseKG / phaseKGMAP mode (default-on for those modes) OR
        # by explicit NOX_KG_PATH_ENABLED env override on top of any other mode.
        env_kg = os.environ.get("NOX_KG_PATH_ENABLED", "").strip().lower()
        env_kg_truthy = env_kg in ("1", "true", "yes", "on")
        env_kg_falsy = env_kg in ("0", "false", "no", "off")
        if env_kg_falsy:
            self.kg_enabled = False
        elif env_kg_truthy:
            self.kg_enabled = True
        else:
            # phaseKG, phaseKGMQ, phaseKGMAP, phaseTriple all default-on for KG path
            self.kg_enabled = self.adapter_mode in (
                "phaseKG", "phaseKGMQ", "phaseKGMAP", "phaseTriple"
            )

        self.kg_boost_magnitude = float(
            os.environ.get("NOX_KG_BOOST_MAGNITUDE", "")
            or DEFAULT_KG_BOOST_MAGNITUDE
        )
        self.kg_direct_multiplier = float(
            os.environ.get("NOX_KG_DIRECT_MULTIPLIER", "")
            or DEFAULT_KG_DIRECT_MULTIPLIER
        )
        self.kg_max_neighbors = int(
            os.environ.get("NOX_KG_MAX_NEIGHBORS", "")
            or DEFAULT_KG_MAX_NEIGHBORS
        )
        self.kg_min_name_len = int(
            os.environ.get("NOX_KG_MIN_NAME_LEN", "")
            or DEFAULT_KG_MIN_NAME_LEN
        )
        self.kg_overfetch = int(
            os.environ.get("NOX_KG_OVERFETCH", "")
            or DEFAULT_KG_OVERFETCH
        )
        # The DB path is the same one the api-server is bound to; we open a
        # separate read-only conn for KG queries.
        self.kg_db_path = os.environ.get("NOX_DB_PATH", "")

        # Phase MAP (Lab Q1 #2 / PR #386) — MA-protection bypass-entity config.
        # Enabled by phaseMAP / phaseKGMAP mode (default-on for those modes) OR
        # by explicit NOX_MA_PROTECTION_ENABLED env override on top of any mode.
        # Requires rerank to be enabled (otherwise nothing to bypass).
        env_map = os.environ.get("NOX_MA_PROTECTION_ENABLED", "").strip().lower()
        env_map_truthy = env_map in ("1", "true", "yes", "on")
        env_map_falsy = env_map in ("0", "false", "no", "off")
        if env_map_falsy:
            self.ma_protection_enabled = False
        elif env_map_truthy:
            self.ma_protection_enabled = True
        else:
            self.ma_protection_enabled = self.adapter_mode in (
                "phaseMAP", "phaseKGMAP", "phaseTriple"
            )

        # Wave B composability — KG anchor extends bypass criterion with
        # chunk_id IN kg_evidence_chunks_for_query_entities. Default-on for
        # phaseKGMAP; opt-in env-only otherwise.
        env_kg_anchor = os.environ.get(
            "NOX_MA_PROTECTION_KG_ANCHOR", ""
        ).strip().lower()
        env_kg_anchor_truthy = env_kg_anchor in ("1", "true", "yes", "on")
        env_kg_anchor_falsy = env_kg_anchor in ("0", "false", "no", "off")
        if env_kg_anchor_falsy:
            self.ma_protection_kg_anchor = False
        elif env_kg_anchor_truthy:
            self.ma_protection_kg_anchor = True
        else:
            self.ma_protection_kg_anchor = self.adapter_mode in (
                "phaseKGMAP", "phaseTriple"
            )

        self.ma_protection_max = int(
            os.environ.get("NOX_MA_PROTECTION_MAX", "")
            or DEFAULT_MA_PROTECTION_MAX
        )

        # Phase MQ (Lab Q1 #3) — Multi-query expansion config.
        # Enabled by phaseMQ mode (default-on for that mode) OR by explicit
        # NOX_MQ_ENABLED env override on top of any other mode.
        env_mq = os.environ.get("NOX_MQ_ENABLED", "").strip().lower()
        env_mq_truthy = env_mq in ("1", "true", "yes", "on")
        env_mq_falsy = env_mq in ("0", "false", "no", "off")
        if env_mq_falsy:
            self.mq_enabled = False
        elif env_mq_truthy:
            self.mq_enabled = True
        else:
            # phaseMQ, phaseKGMQ, phaseTriple default-on multi-query expansion
            self.mq_enabled = (
                self.adapter_mode in ("phaseMQ", "phaseKGMQ", "phaseTriple")
            )

        self.mq_model = os.environ.get("NOX_MQ_LLM", "") or DEFAULT_MQ_LLM
        self.mq_base_url = (
            os.environ.get("NOX_MQ_LLM_BASE_URL", "") or DEFAULT_MQ_LLM_BASE_URL
        )
        # API key defaults to GEMINI_API_KEY (matches default model).
        # If user changes model to OpenAI, must set NOX_MQ_LLM_API_KEY explicitly.
        self.mq_api_key = (
            os.environ.get("NOX_MQ_LLM_API_KEY", "")
            or os.environ.get("GEMINI_API_KEY", "")
        )
        self.mq_n = int(os.environ.get("NOX_MQ_N", "") or DEFAULT_MQ_N)
        self.mq_per_query_topk = int(
            os.environ.get("NOX_MQ_PER_QUERY_TOPK", "") or DEFAULT_MQ_PER_QUERY_TOPK
        )
        self.mq_rrf_k = int(os.environ.get("NOX_MQ_RRF_K", "") or DEFAULT_MQ_RRF_K)
        self.mq_timeout_s = float(
            os.environ.get("NOX_MQ_TIMEOUT_S", "") or DEFAULT_MQ_TIMEOUT_S
        )
        self.mq_debug = os.environ.get("NOX_MQ_DEBUG", "").strip().lower() in (
            "1", "true", "yes", "on"
        )

        # ----------------------------------------------------------------
        # Phase IterC (Q3 POC) — Self-Ask flags
        # ----------------------------------------------------------------
        iterc_env = os.environ.get("NOX_ITERC_ENABLED", "").strip().lower()
        if iterc_env in ("0", "false", "no", "off"):
            self.iterc_enabled = False
        elif iterc_env in ("1", "true", "yes", "on"):
            self.iterc_enabled = True
        else:
            self.iterc_enabled = self.adapter_mode == "phaseIterC"

        self.iterc_decomposer_model = (
            os.environ.get("NOX_ITERC_DECOMPOSER_LLM", "")
            or DEFAULT_ITERC_DECOMPOSER_LLM
        )
        self.iterc_decomposer_base_url = (
            os.environ.get("NOX_ITERC_DECOMPOSER_BASE_URL", "")
            or DEFAULT_ITERC_DECOMPOSER_BASE_URL
        )
        self.iterc_decomposer_api_key = (
            os.environ.get("NOX_ITERC_DECOMPOSER_API_KEY", "")
            or os.environ.get("GEMINI_API_KEY", "")
        )
        self.iterc_answerer_model = (
            os.environ.get("NOX_ITERC_ANSWERER_LLM", "")
            or DEFAULT_ITERC_ANSWERER_LLM
        )
        self.iterc_answerer_base_url = (
            os.environ.get("NOX_ITERC_ANSWERER_BASE_URL", "")
            or DEFAULT_ITERC_ANSWERER_BASE_URL
        )
        self.iterc_answerer_api_key = (
            os.environ.get("NOX_ITERC_ANSWERER_API_KEY", "")
            or os.environ.get("OPENAI_API_KEY", "")
        )
        self.iterc_n = int(
            os.environ.get("NOX_ITERC_N", "") or DEFAULT_ITERC_N
        )
        self.iterc_per_query_topk = int(
            os.environ.get("NOX_ITERC_PER_QUERY_TOPK", "")
            or DEFAULT_ITERC_PER_QUERY_TOPK
        )
        self.iterc_rrf_k = int(
            os.environ.get("NOX_ITERC_RRF_K", "") or DEFAULT_ITERC_RRF_K
        )
        self.iterc_decomposer_timeout_s = float(
            os.environ.get("NOX_ITERC_DECOMPOSER_TIMEOUT_S", "")
            or DEFAULT_ITERC_DECOMPOSER_TIMEOUT_S
        )
        self.iterc_answerer_timeout_s = float(
            os.environ.get("NOX_ITERC_ANSWERER_TIMEOUT_S", "")
            or DEFAULT_ITERC_ANSWERER_TIMEOUT_S
        )
        self.iterc_answerer_max_tokens = int(
            os.environ.get("NOX_ITERC_ANSWERER_MAX_TOKENS", "")
            or DEFAULT_ITERC_ANSWERER_MAX_TOKENS
        )
        self.iterc_debug = os.environ.get("NOX_ITERC_DEBUG", "").strip().lower() in (
            "1", "true", "yes", "on"
        )

        # ----------------------------------------------------------------
        # Phase IterB (Q3 POC) — ReAct flags
        # ----------------------------------------------------------------
        iterb_env = os.environ.get("NOX_ITERB_ENABLED", "").strip().lower()
        if iterb_env in ("0", "false", "no", "off"):
            self.iterb_enabled = False
        elif iterb_env in ("1", "true", "yes", "on"):
            self.iterb_enabled = True
        else:
            self.iterb_enabled = self.adapter_mode == "phaseIterB"

        self.iterb_orchestrator_model = (
            os.environ.get("NOX_ITERB_ORCHESTRATOR_LLM", "")
            or DEFAULT_ITERB_ORCHESTRATOR_LLM
        )
        self.iterb_orchestrator_base_url = (
            os.environ.get("NOX_ITERB_ORCHESTRATOR_BASE_URL", "")
            or DEFAULT_ITERB_ORCHESTRATOR_BASE_URL
        )
        # Default api key resolution: OPENAI_API_KEY for gpt-* models, else
        # GEMINI_API_KEY (matches the "cheap variant" gemini-3-flash path).
        # Explicit NOX_ITERB_ORCHESTRATOR_API_KEY always wins.
        _iterb_key_override = os.environ.get("NOX_ITERB_ORCHESTRATOR_API_KEY", "")
        if _iterb_key_override:
            self.iterb_orchestrator_api_key = _iterb_key_override
        elif "gemini" in self.iterb_orchestrator_model.lower():
            self.iterb_orchestrator_api_key = os.environ.get("GEMINI_API_KEY", "")
        else:
            self.iterb_orchestrator_api_key = os.environ.get("OPENAI_API_KEY", "")

        self.iterb_max_rounds = int(
            os.environ.get("NOX_ITERB_MAX_ROUNDS", "")
            or DEFAULT_ITERB_MAX_ROUNDS
        )
        self.iterb_per_round_topk = int(
            os.environ.get("NOX_ITERB_PER_ROUND_TOPK", "")
            or DEFAULT_ITERB_PER_ROUND_TOPK
        )
        self.iterb_rrf_k = int(
            os.environ.get("NOX_ITERB_RRF_K", "") or DEFAULT_ITERB_RRF_K
        )
        self.iterb_orchestrator_timeout_s = float(
            os.environ.get("NOX_ITERB_ORCHESTRATOR_TIMEOUT_S", "")
            or DEFAULT_ITERB_ORCHESTRATOR_TIMEOUT_S
        )
        self.iterb_orchestrator_max_tokens = int(
            os.environ.get("NOX_ITERB_ORCHESTRATOR_MAX_TOKENS", "")
            or DEFAULT_ITERB_ORCHESTRATOR_MAX_TOKENS
        )
        self.iterb_cost_ceiling_usd = float(
            os.environ.get("NOX_ITERB_COST_CEILING_USD", "")
            or DEFAULT_ITERB_COST_CEILING_USD
        )
        self.iterb_input_cost_per_1m = float(
            os.environ.get("NOX_ITERB_INPUT_COST_PER_1M", "")
            or DEFAULT_ITERB_INPUT_COST_PER_1M
        )
        self.iterb_output_cost_per_1m = float(
            os.environ.get("NOX_ITERB_OUTPUT_COST_PER_1M", "")
            or DEFAULT_ITERB_OUTPUT_COST_PER_1M
        )
        self.iterb_debug = os.environ.get("NOX_ITERB_DEBUG", "").strip().lower() in (
            "1", "true", "yes", "on"
        )

        # HTTP session — created lazily to allow use in async context
        self._session: Optional[aiohttp.ClientSession] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.search_timeout)
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    # ------------------------------------------------------------------
    # Add stage — Option B (CLI subprocess)
    # ------------------------------------------------------------------

    async def add(
        self,
        dataset: Dataset,
        user_id: str,
        days_to_process: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> AddResult:
        """
        Ingest group chat messages into nox-mem via CLI subprocess.

        Strategy (Phase B):
            1. Flatten dataset -> ordered list with stable (date, group) keys
            2. Chunk into batches of `ingest_batch_size` (preserving order)
            3. For each batch: write H2-per-message markdown + day-group digest
               blocks, invoke `nox-mem ingest <tmpfile>`.
            4. Subprocess inherits NOX_DB_PATH from caller env for isolation.

        Returns:
            AddResult with success, days_processed, messages_sent, errors.

        Required env in caller:
            NOX_DB_PATH=/tmp/evermembench-{user_id}.db (or /root/.openclaw/... per op-audit)
            NOX_MEM_BIN=/path/to/nox-mem (optional, default = "nox-mem" on PATH)
        """
        start_ms = time.monotonic() * 1000
        errors: List[str] = []

        db_path = os.environ.get("NOX_DB_PATH", "")
        if not db_path:
            errors.append(
                "NOX_DB_PATH env var is required for isolated EverMemBench run "
                "(set to e.g. /root/.openclaw/evermembench-runs/X.db before invoking harness)"
            )
            return AddResult(
                success=False,
                days_processed=0,
                messages_sent=0,
                errors=errors,
                metadata={"isolation_check": "failed", "user_id": user_id},
            )
        if "/root/.openclaw/workspace/tools/nox-mem/nox-mem.db" in db_path:
            errors.append(
                f"NOX_DB_PATH={db_path} points at production DB; refusing to ingest."
            )
            return AddResult(
                success=False,
                days_processed=0,
                messages_sent=0,
                errors=errors,
                metadata={"isolation_check": "prod_path_blocked", "user_id": user_id},
            )

        messages = self._collect_messages(dataset, days_to_process)
        if not messages:
            return AddResult(
                success=True,
                days_processed=0,
                messages_sent=0,
                errors=[],
                metadata={"reason": "no_messages_after_filter", "user_id": user_id},
            )

        days_seen = {getattr(m, "date", None) or self._date_of(m) for m in messages}
        total_sent = 0

        # Build day-group context cache (used for digest blocks + context window)
        # Map (date, group) -> ordered list of messages
        self._day_group_cache: Dict[Tuple[str, str], List[GroupChatMessage]] = {}
        for m in messages:
            key = (self._date_of(m), str(getattr(m, "group", "?")))
            self._day_group_cache.setdefault(key, []).append(m)
        # Track which (date, group) digests have been emitted
        self._digest_emitted: set = set()

        # Batch ingest
        for batch_start in range(0, len(messages), self.ingest_batch_size):
            batch = messages[batch_start:batch_start + self.ingest_batch_size]
            batch_idx = batch_start // self.ingest_batch_size
            try:
                sent = await self._ingest_batch(batch, user_id, batch_idx, batch_start)
                total_sent += sent
            except Exception as exc:  # noqa: BLE001 — surface all failures
                errors.append(
                    f"batch {batch_idx} ({len(batch)} msgs) failed: {type(exc).__name__}: {exc}"
                )

            if self.ingest_delay_ms:
                await asyncio.sleep(self.ingest_delay_ms / 1000.0)

        elapsed_ms = time.monotonic() * 1000 - start_ms
        success = (total_sent == len(messages)) and not errors
        return AddResult(
            success=success,
            days_processed=len(days_seen),
            messages_sent=total_sent,
            errors=errors,
            metadata={
                "user_id": user_id,
                "db_path": db_path,
                "ingest_batch_size": self.ingest_batch_size,
                "adapter_mode": self.adapter_mode,
                "context_window": self.context_window,
                "elapsed_ms": elapsed_ms,
                "messages_total": len(messages),
                "day_group_count": len(self._day_group_cache),
            },
        )

    async def _ingest_batch(
        self,
        batch: List["GroupChatMessage"],
        user_id: str,
        batch_idx: int,
        batch_start: int,
    ) -> int:
        """
        Write batch to temp .md file (Phase B or baseline format), invoke
        `nox-mem ingest <file>`, return count of messages dispatched.
        """
        lines = [f"# EverMemBench user_id={user_id} batch={batch_idx} mode={self.adapter_mode}\n"]

        if self.adapter_mode == "baseline":
            # PR #363 paragraph format (for ablation)
            for m in batch:
                lines.append(self._format_message_baseline(m))
                lines.append("")
        else:
            # Phase B: H2-per-message with structured metadata + context window
            for i, m in enumerate(batch):
                lines.append(self._format_message_phaseb(m, batch_start + i))
                lines.append("")

                # Emit digest once per (date, group) when the LAST message of
                # that day-group appears (within this batch). Same-batch
                # digests cluster near their messages; cross-batch digests
                # land in whichever batch contains the day-group's last msg.
                key = (self._date_of(m), str(getattr(m, "group", "?")))
                if key in self._digest_emitted:
                    continue
                day_group_msgs = self._day_group_cache.get(key, [])
                if day_group_msgs and m is day_group_msgs[-1]:
                    digest = self._format_day_group_digest(key, day_group_msgs)
                    if digest:
                        lines.append(digest)
                        lines.append("")
                        self._digest_emitted.add(key)

        content = "\n".join(lines)

        # Write to NamedTemporaryFile with .md suffix.
        tmp = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".md",
            prefix=f"evermembench-{user_id}-b{batch_idx:04d}-",
            delete=False,
        )
        tmp_path = tmp.name
        try:
            tmp.write(content)
            tmp.close()

            # Invoke `nox-mem ingest <tempfile>` via execvp-style argv.
            # NOTE: `--source` flag removed (2026-05-28); nox-mem v3.8 rejects it.
            argv = [
                self.nox_mem_bin,
                "ingest",
                tmp_path,
            ]

            proc = await asyncio.create_subprocess_exec(
                *argv,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=os.environ.copy(),
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=INGEST_SUBPROCESS_TIMEOUT
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                raise RuntimeError(
                    f"nox-mem ingest subprocess timed out after {INGEST_SUBPROCESS_TIMEOUT}s "
                    f"(batch {batch_idx}, {len(batch)} messages)"
                )

            if proc.returncode != 0:
                err_text = (stderr or b"").decode("utf-8", errors="replace")[:500]
                raise RuntimeError(
                    f"nox-mem ingest exited {proc.returncode}: {err_text}"
                )

            return len(batch)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    # ------------------------------------------------------------------
    # Phase B helpers
    # ------------------------------------------------------------------

    def _format_message_phaseb(
        self,
        msg: "GroupChatMessage",
        global_idx: int,
    ) -> str:
        """Phase B: H2 block with structured metadata + preceding-context window."""
        group = str(getattr(msg, "group", "?"))
        speaker = str(getattr(msg, "speaker", "?"))
        content = str(getattr(msg, "content", "")).strip()
        time_str = str(
            getattr(msg, "time", None)
            or getattr(msg, "timestamp", None)
            or "?"
        )
        date = self._date_of(msg)

        # Build "context" snippet: last N messages from the SAME (date, group)
        # preceding this message. This gives multi-hop retrieval a local anchor.
        key = (date, group)
        day_group_msgs = self._day_group_cache.get(key, [])
        try:
            pos = day_group_msgs.index(msg)
        except ValueError:
            pos = -1
        context_parts: List[str] = []
        if pos > 0:
            start = max(0, pos - self.context_window)
            for prev in day_group_msgs[start:pos]:
                prev_speaker = str(getattr(prev, "speaker", "?"))
                prev_content = str(getattr(prev, "content", "")).strip()
                # Shorten preceding context to avoid blowing up chunk size
                prev_snip = prev_content[:120].replace("\n", " ")
                if len(prev_content) > 120:
                    prev_snip += "..."
                context_parts.append(f"{prev_speaker}: {prev_snip}")
        context_str = " | ".join(context_parts) if context_parts else "(start of conversation)"

        return PHASEB_MESSAGE_BLOCK.format(
            time=time_str,
            group=group,
            speaker=speaker,
            date=date,
            context=context_str,
            content=content,
        )

    def _format_message_baseline(self, msg: "GroupChatMessage") -> str:
        """PR #363 baseline format (one paragraph)."""
        group = str(getattr(msg, "group", "?"))
        speaker = str(getattr(msg, "speaker", "?"))
        content = str(getattr(msg, "content", "")).strip()
        time_str = str(
            getattr(msg, "time", None)
            or getattr(msg, "timestamp", None)
            or "?"
        )
        return MESSAGE_TEMPLATE.format(
            group=group,
            speaker=speaker,
            time=time_str,
            content=content,
        )

    # Public alias kept for backwards compat
    def _format_message(self, msg: "GroupChatMessage") -> str:
        if self.adapter_mode == "baseline":
            return self._format_message_baseline(msg)
        # Phase B path: cannot include preceding context without batch context;
        # callers should prefer _format_message_phaseb directly.
        return self._format_message_baseline(msg)

    def _format_day_group_digest(
        self,
        key: Tuple[str, str],
        day_group_msgs: List["GroupChatMessage"],
    ) -> str:
        """Build the per-(date, group) digest block."""
        date, group = key
        speakers: List[str] = []
        seen_speakers: set = set()
        for m in day_group_msgs:
            sp = str(getattr(m, "speaker", "?"))
            if sp not in seen_speakers:
                seen_speakers.add(sp)
                speakers.append(sp)
        participants = ", ".join(speakers)
        # Short form for natural-language summary line
        if len(speakers) <= 3:
            participants_short = ", ".join(speakers)
        else:
            participants_short = ", ".join(speakers[:3]) + f", and {len(speakers)-3} others"
        first_line = ""
        if day_group_msgs:
            first_content = str(getattr(day_group_msgs[0], "content", "")).strip()
            first_line = first_content[:180].replace("\n", " ")
            if len(first_content) > 180:
                first_line += "..."
        return PHASEB_DAY_GROUP_ROLLUP.format(
            date=date,
            group=group,
            participants=participants,
            message_count=len(day_group_msgs),
            participants_short=participants_short,
            first_line=first_line,
        )

    def _date_of(self, msg: "GroupChatMessage") -> str:
        """Extract date string from message (best effort)."""
        # Prefer explicit `date` attr if present (some Dataset versions add it)
        d = getattr(msg, "date", None)
        if d:
            return str(d)
        ts = getattr(msg, "time", None) or getattr(msg, "timestamp", None) or ""
        if isinstance(ts, str) and "T" in ts:
            return ts.split("T", 1)[0]
        return str(ts)[:10] if ts else "?"

    def _collect_messages(
        self,
        dataset: "Dataset",
        days_to_process: Optional[List[str]],
    ) -> List["GroupChatMessage"]:
        """
        Flatten dataset into ordered list of GroupChatMessage objects.

        Respects `days_to_process` filter (None = all days).
        Messages within each day are sorted by timestamp.
        """
        messages: List[GroupChatMessage] = []
        for day in getattr(dataset, "days", []):
            day_date = getattr(day, "date", None)
            if days_to_process and day_date not in days_to_process:
                continue
            groups = getattr(day, "groups", {}) or {}
            for _group_name, group_msgs in groups.items():
                sorted_msgs = sorted(
                    group_msgs,
                    key=lambda m: getattr(m, "timestamp", None) or getattr(m, "time", ""),
                )
                # Annotate date on each message for context lookups even
                # when GroupChatMessage doesn't carry .date natively.
                if day_date:
                    for m in sorted_msgs:
                        if not getattr(m, "date", None):
                            try:
                                setattr(m, "date", day_date)
                            except Exception:
                                pass
                messages.extend(sorted_msgs)
        return messages

    # ------------------------------------------------------------------
    # Search stage
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        user_id: str,
        top_k: int = 10,
        **kwargs: Any,
    ) -> SearchResult:
        """
        Retrieve memories from nox-mem for a QA question.

        Calls POST /api/search with hybrid mode (BM25 + Gemini semantic + RRF).
        The API server must be running against the SAME isolated NOX_DB_PATH
        that Add stage ingested into.

        Phase F: if `self.reranker_enabled` is True, request top-N (default 50)
        from the API and rerank with BAAI/bge-reranker-v2-m3 CrossEncoder
        before truncating to `top_k`. Falls back to plain top_k on any
        reranker failure (logged in metadata.rerank_error).
        """
        start_ms = time.monotonic() * 1000
        session = await self._get_session()

        # Initialize fall-through state needed by every downstream branch.
        # `api_limit` is recorded in metadata regardless of which retrieval
        # path fires; `candidates`/`api_returned` are populated by the
        # retrieval path that runs.
        api_limit: int = top_k
        candidates: List[Tuple[str, Dict[str, Any]]] = []
        api_returned: int = 0

        # ------------------------------------------------------------------
        # Phase IterB (Q3 POC) — ReAct multi-round orchestration path
        # ------------------------------------------------------------------
        # When IterB is enabled, we run the ReAct loop END-TO-END:
        #   loop up to max_rounds:
        #     orchestrator LLM emits {action: retrieve, query}  or
        #                            {action: answer, answer}
        #     retrieve → hit /api/search top_k=iterb_per_round_topk → feed
        #                observation back into scratchpad
        #     answer   → terminate, synthesize final context
        # Termination: explicit answer | max_rounds | cost_ceiling | error.
        # Phase MQ / IterC / KG / MAP / rerank are NOT stacked on top —
        # POC isolates orchestration-stage ReAct signal vs Phase H v2.
        iterb_meta: Dict[str, Any] = {
            "iterb_enabled": self.iterb_enabled,
            "iterb_applied": False,
        }
        iterb_used_path = False
        iterb_rounds_executed = 0
        iterb_termination_reason: Optional[str] = None
        iterb_total_cost_usd = 0.0
        iterb_total_input_tokens = 0
        iterb_total_output_tokens = 0
        iterb_per_round_chunk_counts: List[int] = []
        iterb_per_round_overlap_vals: List[float] = []
        iterb_per_round_latency_ms: List[float] = []
        iterb_per_round_sub_queries: List[str] = []
        iterb_per_round_thoughts: List[str] = []
        iterb_final_answer: str = ""
        iterb_orchestrator_errors: List[str] = []
        iterb_context_prefix: str = ""

        if self.iterb_enabled:
            if not self.iterb_orchestrator_api_key:
                iterb_meta["iterb_error"] = (
                    "no api_key (NOX_ITERB_ORCHESTRATOR_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY)"
                )
                iterb_meta["iterb_status"] = "fallback_single"
            else:
                # ReAct loop state
                scratchpad_parts: List[str] = []
                per_round_results: List[List[Tuple[str, Dict[str, Any]]]] = []
                per_round_chunk_ids: List[List[Any]] = []
                api_limit_iterb = self.iterb_per_round_topk
                iterb_loop_start = time.monotonic() * 1000

                for round_idx in range(1, self.iterb_max_rounds + 1):
                    # If we're on final round and orchestrator chose retrieve
                    # last time, force answer this round via prompt round_idx.
                    round_start = time.monotonic() * 1000

                    # Build scratchpad from prior rounds
                    scratchpad = "\n\n".join(scratchpad_parts) if scratchpad_parts else ""

                    # Orchestrator step
                    parsed, step_err, usage = await _iterb_orchestrator_step(
                        query=query,
                        scratchpad=scratchpad,
                        round_idx=round_idx,
                        max_rounds=self.iterb_max_rounds,
                        model=self.iterb_orchestrator_model,
                        base_url=self.iterb_orchestrator_base_url,
                        api_key=self.iterb_orchestrator_api_key,
                        timeout_s=self.iterb_orchestrator_timeout_s,
                        max_tokens=self.iterb_orchestrator_max_tokens,
                        session=session,
                    )
                    if step_err:
                        iterb_orchestrator_errors.append(
                            f"round {round_idx}: {step_err}"
                        )
                    iterb_total_input_tokens += usage.get("input_tokens", 0)
                    iterb_total_output_tokens += usage.get("output_tokens", 0)
                    iterb_total_cost_usd = _iterb_estimate_cost(
                        iterb_total_input_tokens,
                        iterb_total_output_tokens,
                        self.iterb_input_cost_per_1m,
                        self.iterb_output_cost_per_1m,
                    )

                    thought = parsed.get("thought", "")
                    action = parsed.get("action", "answer")
                    iterb_per_round_thoughts.append(thought)
                    iterb_rounds_executed = round_idx

                    if self.iterb_debug:
                        print(
                            f"[IterB R{round_idx}] action={action} "
                            f"cost=${iterb_total_cost_usd:.5f} "
                            f"thought={thought[:120]}",
                            file=__import__("sys").stderr,
                        )

                    if action == "answer":
                        iterb_final_answer = parsed.get("answer", "") or "UNKNOWN"
                        iterb_termination_reason = "answer"
                        round_lat = time.monotonic() * 1000 - round_start
                        iterb_per_round_latency_ms.append(round_lat)
                        iterb_per_round_sub_queries.append("")
                        iterb_per_round_chunk_counts.append(0)
                        per_round_chunk_ids.append([])
                        scratchpad_parts.append(
                            f"### Round {round_idx} (final answer)\n"
                            f"Thought: {thought}\n"
                            f"Answer: {iterb_final_answer}"
                        )
                        break

                    # action == retrieve
                    sub_query = parsed.get("query", "") or query
                    iterb_per_round_sub_queries.append(sub_query)

                    # Hit /api/search for the sub-query
                    try:
                        async with session.post(
                            f"{self.api_base}/api/search",
                            json={
                                "query": sub_query,
                                "limit": api_limit_iterb,
                                "hybrid": True,
                            },
                            headers={"Content-Type": "application/json"},
                        ) as resp:
                            resp.raise_for_status()
                            r_data = await resp.json()
                    except aiohttp.ClientError as exc:
                        iterb_orchestrator_errors.append(
                            f"round {round_idx} retrieve error: {type(exc).__name__}: {exc}"
                        )
                        r_data = {}

                    if isinstance(r_data, list):
                        raw_round_results = r_data
                    elif isinstance(r_data, dict):
                        raw_round_results = r_data.get("results", []) or []
                    else:
                        raw_round_results = []

                    round_chunks: List[Tuple[str, Dict[str, Any]]] = []
                    round_chunk_ids: List[Any] = []
                    for item in raw_round_results:
                        if isinstance(item, dict):
                            content = item.get("chunk_text") or item.get("content") or ""
                            if content:
                                round_chunks.append((content, item))
                                cid = (
                                    item.get("id")
                                    or item.get("chunk_id")
                                    or item.get("rowid")
                                )
                                if cid is not None:
                                    round_chunk_ids.append(cid)

                    per_round_results.append(round_chunks)
                    per_round_chunk_ids.append(round_chunk_ids)
                    iterb_per_round_chunk_counts.append(len(round_chunks))

                    # Build observation block for scratchpad (top-3 chunk
                    # snippets; keeps prompt size bounded across rounds).
                    obs_lines: List[str] = []
                    for i, (c, _it) in enumerate(round_chunks[:3]):
                        obs_lines.append(f"  [{i+1}] {c[:300]}")
                    obs_block = "\n".join(obs_lines) if obs_lines else "  (no results)"
                    scratchpad_parts.append(
                        f"### Round {round_idx}\n"
                        f"Thought: {thought}\n"
                        f"Action: retrieve(\"{sub_query[:200]}\")\n"
                        f"Observation:\n{obs_block}"
                    )

                    round_lat = time.monotonic() * 1000 - round_start
                    iterb_per_round_latency_ms.append(round_lat)

                    # Cost ceiling check (after the round, so the round
                    # that BREACHES the ceiling still gets recorded)
                    if iterb_total_cost_usd >= self.iterb_cost_ceiling_usd:
                        iterb_termination_reason = "cost_ceiling"
                        if self.iterb_debug:
                            print(
                                f"[IterB R{round_idx}] cost ceiling "
                                f"${self.iterb_cost_ceiling_usd:.4f} reached "
                                f"(actual ${iterb_total_cost_usd:.5f})",
                                file=__import__("sys").stderr,
                            )
                        break

                if iterb_termination_reason is None:
                    iterb_termination_reason = "max_rounds"

                # Build candidate pool via RRF union across all retrieve rounds
                if per_round_results:
                    # Reuse MQ's RRF merger (chunk-union mechanism is identical)
                    merged_chunks = _mq_rrf_merge(
                        per_round_results, rrf_k=self.iterb_rrf_k
                    )
                    candidates = merged_chunks
                    api_returned = len(candidates)
                    api_limit = api_limit_iterb * max(1, iterb_rounds_executed)

                    # Per-round overlap (each round vs union of priors)
                    iterb_per_round_overlap_vals = _iterb_per_round_overlap(
                        per_round_chunk_ids
                    )

                    # Build augmented context prefix (ReAct scratchpad +
                    # final answer block). Harness's gpt-4.1-mini final
                    # call sees the orchestration trace AND the chunks.
                    prefix_lines: List[str] = ["## ReAct orchestration trace"]
                    for i in range(iterb_rounds_executed):
                        if i < len(iterb_per_round_sub_queries):
                            sq = iterb_per_round_sub_queries[i]
                        else:
                            sq = ""
                        if i < len(iterb_per_round_thoughts):
                            th = iterb_per_round_thoughts[i]
                        else:
                            th = ""
                        prefix_lines.append(f"### Round {i+1}")
                        if th:
                            prefix_lines.append(f"Thought: {th}")
                        if sq:
                            prefix_lines.append(f"Sub-query: {sq}")
                            if i < len(iterb_per_round_chunk_counts):
                                prefix_lines.append(
                                    f"Retrieved: {iterb_per_round_chunk_counts[i]} chunks"
                                )
                    if iterb_final_answer:
                        prefix_lines.append(
                            f"### ReAct draft answer: {iterb_final_answer}"
                        )
                    prefix_lines.append("")
                    prefix_lines.append("## Retrieved memory chunks (RRF union across rounds)")
                    iterb_context_prefix = "\n".join(prefix_lines)

                    iterb_used_path = True
                    iterb_meta["iterb_applied"] = True
                    iterb_meta["iterb_status"] = "applied"
                else:
                    # No retrieve rounds fired (LLM answered round 1 directly)
                    # Fall through to single-query path so harness still has
                    # something — but record that iterb terminated early.
                    iterb_meta["iterb_status"] = "answered_round_1_no_retrieve"

                iterb_loop_ms = time.monotonic() * 1000 - iterb_loop_start
                iterb_meta["iterb_loop_ms"] = iterb_loop_ms

                if self.iterb_debug:
                    print(
                        f"[IterB] DONE rounds={iterb_rounds_executed} "
                        f"reason={iterb_termination_reason} "
                        f"cost=${iterb_total_cost_usd:.5f} "
                        f"loop_ms={iterb_loop_ms:.0f}",
                        file=__import__("sys").stderr,
                    )

        # ------------------------------------------------------------------
        # Phase IterC (Q3 POC) — Self-Ask orchestration-stage path
        # ------------------------------------------------------------------
        # When IterC is enabled, we run the Self-Ask pipeline END-TO-END
        # (decompose + per-sub-Q retrieve + per-sub-Q answer + chunk RRF
        # union + augmented context). Phase MQ / KG / MAP / rerank are NOT
        # stacked on top — this POC isolates the orchestration-stage signal
        # vs Phase H v2 baseline. On any decomposer failure, we fall back
        # to the standard single-query path (same as MQ does).
        iterc_meta: Dict[str, Any] = {
            "iterc_enabled": self.iterc_enabled,
            "iterc_applied": False,
        }
        iterc_used_path = False
        iterc_sub_questions: List[str] = []
        iterc_sub_answers: List[str] = []
        iterc_sub_answer_errors: List[Optional[str]] = []
        iterc_decompose_ms: Optional[float] = None
        iterc_retrieve_ms: Optional[float] = None
        iterc_synthesis_ms: Optional[float] = None
        iterc_total_returned = 0
        iterc_overlap: Optional[float] = None
        iterc_context_prefix: str = ""

        if self.iterc_enabled and not iterb_used_path:
            if not self.iterc_decomposer_api_key:
                iterc_meta["iterc_error"] = (
                    "no api_key (NOX_ITERC_DECOMPOSER_API_KEY / GEMINI_API_KEY)"
                )
                iterc_meta["iterc_status"] = "fallback_single"
            elif not self.iterc_answerer_api_key:
                iterc_meta["iterc_error"] = (
                    "no api_key (NOX_ITERC_ANSWERER_API_KEY / OPENAI_API_KEY)"
                )
                iterc_meta["iterc_status"] = "fallback_single"
            else:
                # Step 1: Self-Ask decomposition
                dec_start = time.monotonic() * 1000
                sub_qs, decompose_err = await _iterc_decompose_query(
                    query,
                    n=self.iterc_n,
                    model=self.iterc_decomposer_model,
                    base_url=self.iterc_decomposer_base_url,
                    api_key=self.iterc_decomposer_api_key,
                    timeout_s=self.iterc_decomposer_timeout_s,
                    session=session,
                )
                iterc_decompose_ms = time.monotonic() * 1000 - dec_start
                if decompose_err is not None:
                    iterc_meta["iterc_error"] = decompose_err
                    iterc_meta["iterc_status"] = "fallback_single"
                elif not sub_qs:
                    iterc_meta["iterc_error"] = "empty sub_questions"
                    iterc_meta["iterc_status"] = "fallback_single"
                else:
                    iterc_sub_questions = sub_qs
                    if self.iterc_debug:
                        print(
                            f"[IterC] decomposed in {iterc_decompose_ms:.0f}ms "
                            f"-> {len(sub_qs)} sub-Qs:",
                            file=__import__("sys").stderr,
                        )
                        for i, sq in enumerate(sub_qs):
                            print(f"[IterC]   {i+1}. {sq}", file=__import__("sys").stderr)

                    # Step 2: per-sub-Q parallel retrieval
                    retrieve_start = time.monotonic() * 1000
                    api_limit_iterc = self.iterc_per_query_topk

                    async def _iterc_fetch(sq: str) -> List[Tuple[str, Dict[str, Any]]]:
                        payload_sub = {
                            "query": sq,
                            "limit": api_limit_iterc,
                            "hybrid": True,
                        }
                        try:
                            async with session.post(
                                f"{self.api_base}/api/search",
                                json=payload_sub,
                                headers={"Content-Type": "application/json"},
                            ) as r:
                                r.raise_for_status()
                                d = await r.json()
                        except Exception:  # noqa: BLE001
                            return []
                        if isinstance(d, list):
                            rr = d
                        elif isinstance(d, dict):
                            rr = d.get("results", [])
                        else:
                            return []
                        out: List[Tuple[str, Dict[str, Any]]] = []
                        for it in rr:
                            if isinstance(it, dict):
                                c = it.get("chunk_text") or it.get("content") or ""
                                if c:
                                    out.append((c, it))
                        return out

                    per_sub_results = await asyncio.gather(
                        *[_iterc_fetch(sq) for sq in iterc_sub_questions]
                    )
                    iterc_retrieve_ms = time.monotonic() * 1000 - retrieve_start

                    # Step 3: per-sub-Q intermediate answer (parallel)
                    synth_start = time.monotonic() * 1000

                    async def _iterc_answer_one(
                        sq: str, results: List[Tuple[str, Dict[str, Any]]]
                    ) -> Tuple[str, Optional[str]]:
                        chunks_only = [c for c, _ in results]
                        return await _iterc_answer_subquestion(
                            subq=sq,
                            chunks=chunks_only,
                            model=self.iterc_answerer_model,
                            base_url=self.iterc_answerer_base_url,
                            api_key=self.iterc_answerer_api_key,
                            timeout_s=self.iterc_answerer_timeout_s,
                            max_tokens=self.iterc_answerer_max_tokens,
                            session=session,
                        )

                    sub_answer_pairs = await asyncio.gather(
                        *[
                            _iterc_answer_one(sq, res)
                            for sq, res in zip(iterc_sub_questions, per_sub_results)
                        ]
                    )
                    iterc_sub_answers = [pair[0] for pair in sub_answer_pairs]
                    iterc_sub_answer_errors = [pair[1] for pair in sub_answer_pairs]
                    iterc_synthesis_ms = time.monotonic() * 1000 - synth_start

                    if self.iterc_debug:
                        for i, (sq, ans, err) in enumerate(zip(
                            iterc_sub_questions, iterc_sub_answers, iterc_sub_answer_errors
                        )):
                            if err:
                                print(
                                    f"[IterC]   sub-A {i+1} ERR: {err[:120]}",
                                    file=__import__("sys").stderr,
                                )
                            else:
                                print(
                                    f"[IterC]   sub-A {i+1}: {ans[:120]}",
                                    file=__import__("sys").stderr,
                                )

                    # Step 4: RRF chunk union across sub-Q retrievals
                    merged_chunks = _mq_rrf_merge(
                        per_sub_results, rrf_k=self.iterc_rrf_k
                    )
                    candidates = merged_chunks
                    api_returned = len(candidates)
                    iterc_total_returned = sum(len(r) for r in per_sub_results)
                    # Reflect IterC's effective fetch budget in meta. We pull
                    # `iterc_per_query_topk` per sub-Q × N sub-Qs (less dedup).
                    api_limit = api_limit_iterc * len(iterc_sub_questions)

                    # Set E instrumentation: overlap between per-sub-Q chunks
                    per_sub_ids: List[List[Any]] = []
                    for res in per_sub_results:
                        ids: List[Any] = []
                        for _c, it in res:
                            cid = (
                                it.get("id")
                                or it.get("chunk_id")
                                or it.get("rowid")
                            )
                            if cid is not None:
                                ids.append(cid)
                        per_sub_ids.append(ids)
                    iterc_overlap = _iterc_per_subquery_overlap(per_sub_ids)

                    # Step 5: build augmented context prefix (sub-Q + answer
                    # blocks). The harness's gpt-4.1-mini final-answer call
                    # will see both the orchestration trace and the chunks.
                    prefix_lines: List[str] = ["## Self-Ask intermediate reasoning"]
                    for i, (sq, ans, err) in enumerate(zip(
                        iterc_sub_questions, iterc_sub_answers, iterc_sub_answer_errors
                    )):
                        prefix_lines.append(f"### Sub-question {i+1}: {sq}")
                        if err or not ans:
                            prefix_lines.append("Intermediate answer: [unavailable]")
                        else:
                            prefix_lines.append(f"Intermediate answer: {ans}")
                    prefix_lines.append("")
                    prefix_lines.append("## Retrieved memory chunks (RRF union across sub-Qs)")
                    iterc_context_prefix = "\n".join(prefix_lines)

                    iterc_used_path = True
                    iterc_meta["iterc_applied"] = True
                    iterc_meta["iterc_status"] = "applied"
                    iterc_meta["iterc_n"] = len(iterc_sub_questions)
                    iterc_meta["iterc_sub_questions"] = iterc_sub_questions
                    iterc_meta["iterc_sub_answers"] = iterc_sub_answers
                    iterc_meta["iterc_sub_answer_errors"] = [
                        e for e in iterc_sub_answer_errors if e
                    ]
                    iterc_meta["iterc_per_query_topk"] = self.iterc_per_query_topk
                    iterc_meta["iterc_rrf_k"] = self.iterc_rrf_k
                    iterc_meta["iterc_total_results_pre_dedup"] = iterc_total_returned
                    iterc_meta["iterc_unique_after_dedup"] = api_returned
                    iterc_meta["iterc_subq_overlap"] = iterc_overlap
                    if self.iterc_debug:
                        print(
                            f"[IterC] retrieved {iterc_total_returned} pre-dedup "
                            f"-> {api_returned} unique (overlap={iterc_overlap:.3f}) "
                            f"in {iterc_retrieve_ms:.0f}ms; synth in "
                            f"{iterc_synthesis_ms:.0f}ms",
                            file=__import__("sys").stderr,
                        )

        # ------------------------------------------------------------------
        # Phase MQ (Lab Q1 #3) — Multi-query expansion path
        # ------------------------------------------------------------------
        # When MQ is enabled, we replace the single-query retrieval with:
        #   1. LLM decomposition into N sub-queries
        #   2. Per-sub-query API call (top_k=NOX_MQ_PER_QUERY_TOPK)
        #   3. RRF union+dedup
        # On any decomposition failure, gracefully fall back to single-query
        # (same code path as baseline) with mq_status="fallback_single".
        mq_meta: Dict[str, Any] = {
            "mq_enabled": self.mq_enabled,
            "mq_applied": False,
        }
        mq_used_subquery_path = False
        mq_sub_queries: List[str] = []
        mq_decompose_ms: Optional[float] = None
        mq_retrieve_ms: Optional[float] = None
        mq_total_returned = 0

        if self.mq_enabled and not iterc_used_path and not iterb_used_path:
            if not self.mq_api_key:
                mq_meta["mq_error"] = "no api_key (NOX_MQ_LLM_API_KEY / GEMINI_API_KEY)"
            else:
                # Step 1: decompose
                dec_start = time.monotonic() * 1000
                sub_queries, decompose_err = await _mq_decompose_query(
                    query,
                    n=self.mq_n,
                    model=self.mq_model,
                    base_url=self.mq_base_url,
                    api_key=self.mq_api_key,
                    timeout_s=self.mq_timeout_s,
                    session=session,
                )
                mq_decompose_ms = time.monotonic() * 1000 - dec_start
                if decompose_err is not None:
                    mq_meta["mq_error"] = decompose_err
                    mq_meta["mq_status"] = "fallback_single"
                elif not sub_queries:
                    mq_meta["mq_error"] = "empty sub_queries"
                    mq_meta["mq_status"] = "fallback_single"
                else:
                    mq_sub_queries = sub_queries
                    if self.mq_debug:
                        print(
                            f"[MQ] decomposed in {mq_decompose_ms:.0f}ms -> {len(sub_queries)} sub-queries:",
                            file=__import__("sys").stderr,
                        )
                        for i, sq in enumerate(sub_queries):
                            print(f"[MQ]   {i+1}. {sq}", file=__import__("sys").stderr)

                    # Step 2: parallel retrieval for each sub-query.
                    # API supports concurrent connections; we run them in
                    # an asyncio.gather to minimize wall time.
                    retrieve_start = time.monotonic() * 1000
                    api_limit = self.mq_per_query_topk

                    async def _fetch_sub(sq: str) -> List[Tuple[str, Dict[str, Any]]]:
                        payload_sub = {"query": sq, "limit": api_limit, "hybrid": True}
                        try:
                            async with session.post(
                                f"{self.api_base}/api/search",
                                json=payload_sub,
                                headers={"Content-Type": "application/json"},
                            ) as r:
                                r.raise_for_status()
                                d = await r.json()
                        except Exception:  # noqa: BLE001
                            return []
                        if isinstance(d, list):
                            rr = d
                        elif isinstance(d, dict):
                            rr = d.get("results", [])
                        else:
                            return []
                        out: List[Tuple[str, Dict[str, Any]]] = []
                        for it in rr:
                            if isinstance(it, dict):
                                c = it.get("chunk_text") or it.get("content") or ""
                                if c:
                                    out.append((c, it))
                        return out

                    per_sub_results = await asyncio.gather(
                        *[_fetch_sub(sq) for sq in sub_queries]
                    )
                    mq_retrieve_ms = time.monotonic() * 1000 - retrieve_start
                    # Step 3: RRF merge + dedup
                    merged = _mq_rrf_merge(per_sub_results, rrf_k=self.mq_rrf_k)
                    candidates = merged
                    api_returned = len(candidates)
                    mq_total_returned = sum(len(r) for r in per_sub_results)
                    mq_used_subquery_path = True
                    mq_meta["mq_applied"] = True
                    mq_meta["mq_status"] = "applied"
                    mq_meta["mq_n"] = len(sub_queries)
                    mq_meta["mq_sub_queries"] = sub_queries
                    mq_meta["mq_per_query_topk"] = self.mq_per_query_topk
                    mq_meta["mq_rrf_k"] = self.mq_rrf_k
                    mq_meta["mq_total_results_pre_dedup"] = mq_total_returned
                    mq_meta["mq_unique_after_dedup"] = api_returned
                    if self.mq_debug:
                        print(
                            f"[MQ] retrieved {mq_total_returned} pre-dedup -> "
                            f"{api_returned} unique chunks in {mq_retrieve_ms:.0f}ms",
                            file=__import__("sys").stderr,
                        )

        # ------------------------------------------------------------------
        # Baseline single-query path (used when MQ/IterC disabled or fell back)
        # ------------------------------------------------------------------
        if not mq_used_subquery_path and not iterc_used_path and not iterb_used_path:
            # Decide how many results to request from the API.
            # Phase F: overfetch then rerank locally. Other modes: request top_k.
            # Phase KG: also needs overfetch so we have a pool to re-rank within
            # via KG boost. Phase MAP / KGMAP: rerank-driven, so overfetch is
            # already covered via reranker_overfetch. If multiple paths active,
            # take the max overfetch.
            api_limit = top_k
            if self.reranker_enabled:
                api_limit = max(api_limit, self.reranker_overfetch)
            if self.kg_enabled:
                api_limit = max(api_limit, self.kg_overfetch)

            payload = {
                "query": query,
                "limit": api_limit,
                "hybrid": True,
            }

            try:
                async with session.post(
                    f"{self.api_base}/api/search",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                ) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
            except aiohttp.ClientError as exc:
                return SearchResult(
                    question_id=kwargs.get("question_id", "unknown"),
                    query=query,
                    retrieved_memories=[],
                    context="[nox-mem search failed: " + str(exc) + "]",
                    search_duration_ms=time.monotonic() * 1000 - start_ms,
                    metadata={"error": str(exc), **mq_meta},
                )

            # Validate shape before .get() access
            if isinstance(data, list):
                raw_results = data
            elif isinstance(data, dict):
                raw_results = data.get("results", [])
            else:
                return SearchResult(
                    question_id=kwargs.get("question_id", "unknown"),
                    query=query,
                    retrieved_memories=[],
                    context="[nox-mem returned unexpected shape]",
                    search_duration_ms=time.monotonic() * 1000 - start_ms,
                    metadata={"raw": str(data)[:200], **mq_meta},
                )

            # Extract candidate (chunk_text, item) pairs in API rank order.
            candidates: List[Tuple[str, Dict[str, Any]]] = []
            for item in raw_results:
                if isinstance(item, dict):
                    content = item.get("chunk_text") or item.get("content") or ""
                    if content:
                        candidates.append((content, item))

            api_returned = len(candidates)
        else:
            # MQ path was used. We still need a `data` object for downstream
            # took_ms_api lookup; set a stub so meta extraction doesn't crash.
            data = {"took_ms": None}

        # ------------------------------------------------------------------
        # Phase KG (Lab Q1 #4) — 1-hop entity boost (post-RRF, pre-rerank)
        # ------------------------------------------------------------------
        kg_error: Optional[str] = None
        kg_ms: Optional[float] = None
        kg_applied = False
        kg_meta: Dict[str, Any] = {}
        # Captured at function scope for downstream MA-protection KG-anchor
        # reuse (Wave B composability). Empty set if KG path disabled or no
        # entities matched in query.
        kg_evidence_for_map: set = set()

        if self.kg_enabled and candidates and self.kg_db_path and not iterc_used_path and not iterb_used_path:
            kg_start = time.monotonic() * 1000
            try:
                # 1. Load entity pool (cached per DB after first call)
                entity_pool, load_err = _kg_load_entity_names(
                    self.kg_db_path, self.kg_min_name_len
                )
                if load_err is not None:
                    kg_error = load_err
                elif not entity_pool:
                    kg_meta["status"] = "empty_kg"
                else:
                    # 2. Extract entity mentions from query (regex)
                    matched = _kg_extract_query_entities(query, entity_pool)
                    matched_ids = [m[0] for m in matched]
                    if not matched_ids:
                        kg_meta["status"] = "no_entities_in_query"
                    else:
                        # 3a. Get direct evidence chunks (chunks tied to the
                        #     mentioned entity itself — strongest signal)
                        direct_chunks = _kg_get_direct_chunk_ids(
                            self.kg_db_path, matched_ids
                        )
                        # 3b. Get 1-hop neighbors and their evidence chunks
                        neighbors = _kg_get_1hop_neighbors(
                            self.kg_db_path,
                            matched_ids,
                            self.kg_max_neighbors,
                        )
                        # Map: chunk_id → (best_confidence, hop_type)
                        # hop_type: "direct" (1.5×) or "neighbor" (1.0×)
                        chunk_boost_score: Dict[int, Tuple[float, str]] = {}
                        for cid in direct_chunks:
                            if cid <= 0:
                                continue
                            chunk_boost_score[cid] = (1.0, "direct")
                        for n_eid, ev_cid, conf, _seed in neighbors:
                            if ev_cid <= 0:
                                continue
                            if ev_cid in chunk_boost_score and chunk_boost_score[ev_cid][1] == "direct":
                                continue  # direct trumps neighbor
                            prev = chunk_boost_score.get(ev_cid)
                            if prev is None or conf > prev[0]:
                                chunk_boost_score[ev_cid] = (conf, "neighbor")

                        # 4. Apply ADDITIVE boost to candidates whose
                        #    chunk_id matches the boost map.
                        #    Per memoria-nox rule §5 (multiplicative empilhável
                        #    é veneno), we use additive delta.
                        boost_count = 0
                        for idx, (content, item) in enumerate(candidates):
                            cid = item.get("id") or item.get("chunk_id") or item.get("rowid")
                            try:
                                cid_int = int(cid) if cid is not None else None
                            except (TypeError, ValueError):
                                cid_int = None
                            if cid_int is None or cid_int not in chunk_boost_score:
                                continue
                            conf, hop_type = chunk_boost_score[cid_int]
                            multiplier = (
                                self.kg_direct_multiplier
                                if hop_type == "direct"
                                else 1.0
                            )
                            delta = self.kg_boost_magnitude * multiplier * conf
                            # Record the delta on the item so downstream
                            # sorting (after rerank, if enabled) uses it.
                            item["_kg_boost"] = delta
                            item["_kg_hop_type"] = hop_type
                            boost_count += 1

                        # Re-sort candidates: API rank position + kg delta.
                        # We use a synthetic score = (rrf_score or 1/(rank+1)) + delta.
                        # Most APIs do not return rrf_score so we approximate
                        # with 1/(rank+1) which is the RRF k=0 form.
                        def _kg_sort_key(rank_item: Tuple[int, Tuple[str, Dict[str, Any]]]) -> float:
                            rank, (_c, it) = rank_item
                            base_score = (
                                float(it.get("rrf_score") or it.get("score") or 0.0)
                                or 1.0 / (rank + 1)
                            )
                            return -(base_score + float(it.get("_kg_boost") or 0.0))

                        candidates = [
                            c for _, c in sorted(
                                enumerate(candidates),
                                key=_kg_sort_key,
                            )
                        ]
                        kg_applied = True
                        # Snapshot KG evidence chunks for MA-protection
                        # KG-anchor reuse (Wave B composability). Includes
                        # direct evidence + neighbor evidence chunks (both
                        # are entity-grounded by virtue of appearing in
                        # kg_relations.evidence_chunk_id for a relation
                        # touching a query-mentioned entity).
                        kg_evidence_for_map = set(direct_chunks)
                        for _n_eid, ev_cid, _conf, _seed in neighbors:
                            if ev_cid and ev_cid > 0:
                                kg_evidence_for_map.add(ev_cid)
                        kg_meta.update(
                            status="applied",
                            entities_in_query=len(matched_ids),
                            entity_names_matched=[m[1] for m in matched],
                            neighbors_found=len(neighbors),
                            direct_chunks=len(direct_chunks),
                            chunks_boosted=boost_count,
                        )
            except Exception as exc:  # noqa: BLE001
                kg_error = f"KG boost failed: {type(exc).__name__}: {exc}"
            kg_ms = time.monotonic() * 1000 - kg_start

        # ------------------------------------------------------------------
        # Phase MAP (Lab Q1 #2 / PR #386) — MA-protection bypass-entity
        # ------------------------------------------------------------------
        # Compute the protected set BEFORE rerank so we can instrument the
        # firing count even when rerank later fails or is disabled. This is
        # the empirical surface needed to validate the mechanism on chat-
        # only corpora (lesson `[[empirical-set-e-empty-confirms-mechanism-
        # not-corpus]]`).
        ma_protected_section: set = set()
        ma_protected_kg: set = set()
        ma_protected_total: set = set()
        ma_protection_applied = False
        ma_protection_error: Optional[str] = None
        ma_protection_status = "off"

        if self.ma_protection_enabled and candidates:
            try:
                ma_protected_section = (
                    _ma_extract_protected_chunk_ids_section(candidates)
                )
                if self.ma_protection_kg_anchor and kg_evidence_for_map:
                    ma_protected_kg = (
                        _ma_extract_protected_chunk_ids_kg_anchor(
                            candidates, kg_evidence_for_map
                        )
                    )
                ma_protected_total = ma_protected_section | ma_protected_kg
                if not ma_protected_total:
                    ma_protection_status = "empty_protected_set"
                else:
                    ma_protection_status = "partition_ready"
            except Exception as exc:  # noqa: BLE001
                ma_protection_error = (
                    f"ma-protection partition failed: "
                    f"{type(exc).__name__}: {exc}"
                )
                ma_protection_status = "error"

        # ------------------------------------------------------------------
        # Phase F: cross-encoder rerank (graceful fallback)
        # ------------------------------------------------------------------
        rerank_error: Optional[str] = None
        rerank_ms: Optional[float] = None
        rerank_applied = False

        if self.reranker_enabled and candidates and not iterc_used_path and not iterb_used_path:
            rerank_start = time.monotonic() * 1000
            model, err = _load_reranker(
                self.reranker_model_id, self.reranker_max_length
            )
            if err is not None:
                rerank_error = err
            else:
                try:
                    # MA-protection path: partition first, rerank only Set R.
                    # When ma_protected_total is empty (e.g. corpus mismatch),
                    # this degenerates cleanly into plain rerank — same path
                    # as Phase F (PR #386 lesson: behaviour MUST equal plain
                    # rerank when there's nothing to protect, NOT crash).
                    if (
                        self.ma_protection_enabled
                        and ma_protected_total
                        and ma_protection_error is None
                    ):
                        total_slots_pre_truncate = len(candidates)
                        set_e, set_r = _ma_partition_candidates(
                            candidates,
                            ma_protected_total,
                            self.ma_protection_max,
                        )
                        if set_r:
                            pairs = [(query, c[0]) for c in set_r]
                            scores = await asyncio.to_thread(
                                model.predict,
                                pairs,
                                batch_size=self.reranker_batch_size,
                                show_progress_bar=False,
                            )
                            scored = list(zip(set_r, scores))
                            scored.sort(key=lambda x: float(x[1]), reverse=True)
                            set_r_reranked = [c for c, _ in scored]
                        else:
                            set_r_reranked = []
                        candidates = _ma_merge_preserving_protected_positions(
                            set_e=set_e,
                            set_r_reranked=set_r_reranked,
                            total_slots=total_slots_pre_truncate,
                        )
                        rerank_applied = True
                        ma_protection_applied = True
                        ma_protection_status = "applied"
                    else:
                        # Standard rerank — no protection (or empty set).
                        pairs = [(query, c[0]) for c in candidates]
                        # CrossEncoder.predict is sync CPU/GPU work — run in a
                        # thread to avoid blocking the asyncio loop entirely.
                        scores = await asyncio.to_thread(
                            model.predict,
                            pairs,
                            batch_size=self.reranker_batch_size,
                            show_progress_bar=False,
                        )
                        scored = list(zip(candidates, scores))
                        scored.sort(key=lambda x: float(x[1]), reverse=True)
                        candidates = [c for c, _ in scored]
                        rerank_applied = True
                except Exception as exc:  # noqa: BLE001 — fall back gracefully
                    rerank_error = (
                        f"rerank predict failed: {type(exc).__name__}: {exc}"
                    )
            rerank_ms = time.monotonic() * 1000 - rerank_start

        # Truncate to top_k after optional rerank.
        candidates = candidates[:top_k]
        memories: List[str] = [c[0] for c in candidates]

        # Format context string for LLM answer stage. Phase IterC prepends
        # the Self-Ask intermediate reasoning block so the harness's final
        # gpt-4.1-mini answer call sees both the orchestration trace and
        # the underlying retrieved chunks.
        context_lines = [f"{i + 1}. {m}" for i, m in enumerate(memories)]
        chunks_body = "\n".join(context_lines) if context_lines else "[No memories retrieved]"
        if iterb_used_path and iterb_context_prefix:
            context = iterb_context_prefix + "\n" + chunks_body
        elif iterc_used_path and iterc_context_prefix:
            context = iterc_context_prefix + "\n" + chunks_body
        else:
            context = chunks_body

        elapsed_ms = time.monotonic() * 1000 - start_ms
        meta: Dict[str, Any] = {
            "api_base": self.api_base,
            "top_k": top_k,
            "api_limit": api_limit,
            "returned": len(memories),
            "api_returned": api_returned,
            "took_ms_api": data.get("took_ms", None) if isinstance(data, dict) else None,
            "rerank_enabled": self.reranker_enabled,
            "rerank_applied": rerank_applied,
            "rerank_model": self.reranker_model_id if self.reranker_enabled else None,
            "rerank_ms": rerank_ms,
            "rerank_error": rerank_error,
            "kg_enabled": self.kg_enabled,
            "kg_applied": kg_applied,
            "kg_ms": kg_ms,
            "kg_error": kg_error,
            "kg_meta": kg_meta,
            "ma_protection_enabled": self.ma_protection_enabled,
            "ma_protection_kg_anchor": self.ma_protection_kg_anchor,
            "ma_protection_applied": ma_protection_applied,
            "ma_protection_status": ma_protection_status,
            "ma_protection_error": ma_protection_error,
            "ma_set_e_count": len(ma_protected_section),
            "ma_set_e_kg_count": len(ma_protected_kg),
            "ma_total_protected_count": len(ma_protected_total),
            "ma_kg_evidence_pool_size": len(kg_evidence_for_map),
            "ma_protection_max": self.ma_protection_max,
            "mq_enabled": self.mq_enabled,
            "mq_applied": mq_meta.get("mq_applied", False),
            "mq_status": mq_meta.get("mq_status", "off" if not self.mq_enabled else "unknown"),
            "mq_decompose_ms": mq_decompose_ms,
            "mq_retrieve_ms": mq_retrieve_ms,
            "mq_error": mq_meta.get("mq_error"),
            "mq_n_actual": len(mq_sub_queries),
            "mq_sub_queries": mq_sub_queries if self.mq_debug or mq_meta.get("mq_applied") else [],
            "mq_total_results_pre_dedup": mq_total_returned if mq_used_subquery_path else None,
            "mq_unique_after_dedup": api_returned if mq_used_subquery_path else None,
            "mq_rrf_k": self.mq_rrf_k if self.mq_enabled else None,
            # Composability (Wave B) — both fired in this query
            "composability_kg_mq_active": bool(
                kg_applied and mq_meta.get("mq_applied", False)
            ),
            # Phase IterC (Q3 POC) — Self-Ask orchestration
            "iterc_enabled": self.iterc_enabled,
            "iterc_applied": iterc_meta.get("iterc_applied", False),
            "iterc_status": iterc_meta.get(
                "iterc_status", "off" if not self.iterc_enabled else "unknown"
            ),
            "iterc_error": iterc_meta.get("iterc_error"),
            "iterc_n_actual": len(iterc_sub_questions),
            "iterc_sub_questions": (
                iterc_sub_questions
                if self.iterc_debug or iterc_meta.get("iterc_applied")
                else []
            ),
            "iterc_sub_answers": (
                iterc_sub_answers
                if self.iterc_debug or iterc_meta.get("iterc_applied")
                else []
            ),
            "iterc_sub_answer_error_count": sum(
                1 for e in iterc_sub_answer_errors if e
            ),
            "iterc_decompose_ms": iterc_decompose_ms,
            "iterc_retrieve_ms": iterc_retrieve_ms,
            "iterc_synthesis_ms": iterc_synthesis_ms,
            "iterc_total_results_pre_dedup": (
                iterc_total_returned if iterc_used_path else None
            ),
            "iterc_unique_after_dedup": (
                api_returned if iterc_used_path else None
            ),
            "iterc_subq_overlap": iterc_overlap,
            "iterc_rrf_k": self.iterc_rrf_k if self.iterc_enabled else None,
            "iterc_per_query_topk": (
                self.iterc_per_query_topk if self.iterc_enabled else None
            ),
            # Phase IterB (Q3 POC) — ReAct instrumentation (Set E per-query)
            "iterb_enabled": self.iterb_enabled,
            "iterb_applied": iterb_meta.get("iterb_applied", False),
            "iterb_status": iterb_meta.get(
                "iterb_status", "off" if not self.iterb_enabled else "unknown"
            ),
            "iterb_error": iterb_meta.get("iterb_error"),
            "iterb_orchestrator_errors": (
                iterb_orchestrator_errors if iterb_orchestrator_errors else None
            ),
            "iterb_rounds_executed": iterb_rounds_executed,
            "iterb_max_rounds": self.iterb_max_rounds if self.iterb_enabled else None,
            "iterb_termination_reason": iterb_termination_reason,
            "iterb_per_round_chunk_counts": iterb_per_round_chunk_counts,
            "iterb_per_round_overlap_with_prior": iterb_per_round_overlap_vals,
            "iterb_per_round_latency_ms": iterb_per_round_latency_ms,
            "iterb_per_round_sub_queries": (
                iterb_per_round_sub_queries
                if (self.iterb_debug or iterb_used_path)
                else []
            ),
            "iterb_per_round_thoughts": (
                iterb_per_round_thoughts
                if self.iterb_debug
                else []
            ),
            "iterb_final_draft_answer": iterb_final_answer or None,
            "iterb_total_input_tokens": iterb_total_input_tokens,
            "iterb_total_output_tokens": iterb_total_output_tokens,
            "iterb_total_cost_usd": (
                round(iterb_total_cost_usd, 6) if self.iterb_enabled else None
            ),
            "iterb_cost_ceiling_usd": (
                self.iterb_cost_ceiling_usd if self.iterb_enabled else None
            ),
            "iterb_rrf_k": self.iterb_rrf_k if self.iterb_enabled else None,
            "iterb_per_round_topk": (
                self.iterb_per_round_topk if self.iterb_enabled else None
            ),
            "iterb_loop_ms": iterb_meta.get("iterb_loop_ms"),
        }
        return SearchResult(
            question_id=kwargs.get("question_id", "unknown"),
            query=query,
            retrieved_memories=memories,
            context=context,
            search_duration_ms=elapsed_ms,
            metadata=meta,
        )

    # ------------------------------------------------------------------
    # System info
    # ------------------------------------------------------------------

    def get_system_info(self) -> Dict[str, Any]:
        return {
            "name": "nox_mem",
            "type": "NoxMemAdapter",
            "api_base": self.api_base,
            "nox_mem_bin": self.nox_mem_bin,
            "search_top_k": self.search_top_k,
            "adapter_mode": self.adapter_mode,
            "phaseb_context_window": self.context_window,
            "reranker_enabled": self.reranker_enabled,
            "reranker_model": self.reranker_model_id,
            "reranker_overfetch": self.reranker_overfetch,
            "reranker_batch_size": self.reranker_batch_size,
            "reranker_max_length": self.reranker_max_length,
            "kg_enabled": self.kg_enabled,
            "kg_boost_magnitude": self.kg_boost_magnitude,
            "kg_direct_multiplier": self.kg_direct_multiplier,
            "kg_max_neighbors": self.kg_max_neighbors,
            "kg_min_name_len": self.kg_min_name_len,
            "kg_overfetch": self.kg_overfetch,
            "kg_db_path": self.kg_db_path,
            "ma_protection_enabled": self.ma_protection_enabled,
            "ma_protection_kg_anchor": self.ma_protection_kg_anchor,
            "ma_protection_max": self.ma_protection_max,
            "mq_enabled": self.mq_enabled,
            "mq_model": self.mq_model,
            "mq_base_url": self.mq_base_url,
            "mq_n": self.mq_n,
            "mq_per_query_topk": self.mq_per_query_topk,
            "mq_rrf_k": self.mq_rrf_k,
            "mq_timeout_s": self.mq_timeout_s,
            "iterc_enabled": self.iterc_enabled,
            "iterc_decomposer_model": self.iterc_decomposer_model,
            "iterc_decomposer_base_url": self.iterc_decomposer_base_url,
            "iterc_answerer_model": self.iterc_answerer_model,
            "iterc_answerer_base_url": self.iterc_answerer_base_url,
            "iterc_n": self.iterc_n,
            "iterc_per_query_topk": self.iterc_per_query_topk,
            "iterc_rrf_k": self.iterc_rrf_k,
            "iterc_decomposer_timeout_s": self.iterc_decomposer_timeout_s,
            "iterc_answerer_timeout_s": self.iterc_answerer_timeout_s,
            "iterc_answerer_max_tokens": self.iterc_answerer_max_tokens,
            "iterb_enabled": self.iterb_enabled,
            "iterb_orchestrator_model": self.iterb_orchestrator_model,
            "iterb_orchestrator_base_url": self.iterb_orchestrator_base_url,
            "iterb_max_rounds": self.iterb_max_rounds,
            "iterb_per_round_topk": self.iterb_per_round_topk,
            "iterb_rrf_k": self.iterb_rrf_k,
            "iterb_orchestrator_timeout_s": self.iterb_orchestrator_timeout_s,
            "iterb_orchestrator_max_tokens": self.iterb_orchestrator_max_tokens,
            "iterb_cost_ceiling_usd": self.iterb_cost_ceiling_usd,
            "iterb_input_cost_per_1m": self.iterb_input_cost_per_1m,
            "iterb_output_cost_per_1m": self.iterb_output_cost_per_1m,
            "version": "phase-iterB-q3-poc-0.1",
        }
