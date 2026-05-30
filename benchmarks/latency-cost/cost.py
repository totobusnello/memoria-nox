#!/usr/bin/env python3
"""
cost.py — nox-mem per-query cost calculator and competitor comparison

Calculates exact cost per query for nox-mem and compares against
published competitor pricing (Zep Cloud, Mem0, MemOS, LangMem, Letta).

Cost model:
  nox-mem retrieval:
    - Query embed: Gemini text-embedding-004 = $0.13/1M tokens
    - FTS5 BM25:   $0 (SQLite, no API)
    - KG walk:     $0 (SQLite, no API)
    - RRF fusion:  $0 (local merge)
    - Total (retrieval only): ~$0.0000013/query (10 avg tokens)

  nox-mem answer (/api/answer):
    - Retrieval: $0.0000013 (embed)
    - Context assembly: $0 (local)
    - LLM answer:
      - gpt-4.1-mini: $0.0004/query (~500 in + 150 out tokens)
      - gemini-2.5-flash-lite: $0.000083/query (~500 in + 150 out tokens)

Usage:
    python benchmarks/latency-cost/cost.py [--output FILE]
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass, asdict
from typing import Optional


# ---------------------------------------------------------------------------
# Pricing constants (as of 2026-05-29 — verify against provider docs)
# ---------------------------------------------------------------------------

# Gemini text-embedding-004 (= gemini-embedding-001)
# Source: ai.google.dev/pricing
GEMINI_EMBED_USD_PER_1M_TOKENS = 0.13

# GPT-4.1-mini
# Source: openai.com/pricing
GPT41_MINI_INPUT_USD_PER_1M = 0.40
GPT41_MINI_OUTPUT_USD_PER_1M = 1.60

# Gemini 2.5 Flash Lite
# Source: ai.google.dev/pricing
GEMINI_FLASH_LITE_INPUT_USD_PER_1M = 0.075
GEMINI_FLASH_LITE_OUTPUT_USD_PER_1M = 0.30

# Gemini 2.5 Flash (full)
GEMINI_FLASH_INPUT_USD_PER_1M = 0.15
GEMINI_FLASH_OUTPUT_USD_PER_1M = 0.60

# OpenAI text-embedding-3-small
OPENAI_EMBED_SMALL_USD_PER_1M = 0.02

# OpenAI text-embedding-3-large
OPENAI_EMBED_LARGE_USD_PER_1M = 0.13


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class CostBreakdown:
    """Per-query cost breakdown in USD."""
    embed_usd: float
    fts_usd: float
    kg_walk_usd: float
    rrf_usd: float
    llm_answer_usd: float  # 0 for retrieval-only
    total_usd: float
    notes: str


@dataclass
class CompetitorCost:
    name: str
    display_name: str
    deployment: str  # "self-hosted" | "SaaS"
    retrieval_cost_per_query_usd: Optional[float]
    retrieval_cost_source: str
    answer_cost_per_query_usd: Optional[float]
    saas_plan_notes: str
    latency_p50_ms: Optional[int]
    latency_source: str
    self_hosted_available: bool
    embed_dependency: str
    notes: str


# ---------------------------------------------------------------------------
# nox-mem cost calculations
# ---------------------------------------------------------------------------

def calc_embed_cost(tokens: int, model: str = "gemini-embedding-001") -> float:
    if "gemini" in model.lower():
        return tokens * GEMINI_EMBED_USD_PER_1M_TOKENS / 1_000_000
    elif "3-small" in model.lower():
        return tokens * OPENAI_EMBED_SMALL_USD_PER_1M / 1_000_000
    elif "3-large" in model.lower():
        return tokens * OPENAI_EMBED_LARGE_USD_PER_1M / 1_000_000
    return 0.0


def calc_answer_cost(
    input_tokens: int,
    output_tokens: int,
    backbone: str = "gemini-2.5-flash-lite",
) -> float:
    if backbone == "gpt-4.1-mini":
        return (input_tokens * GPT41_MINI_INPUT_USD_PER_1M / 1_000_000 +
                output_tokens * GPT41_MINI_OUTPUT_USD_PER_1M / 1_000_000)
    elif backbone == "gemini-2.5-flash-lite":
        return (input_tokens * GEMINI_FLASH_LITE_INPUT_USD_PER_1M / 1_000_000 +
                output_tokens * GEMINI_FLASH_LITE_OUTPUT_USD_PER_1M / 1_000_000)
    elif backbone == "gemini-2.5-flash":
        return (input_tokens * GEMINI_FLASH_INPUT_USD_PER_1M / 1_000_000 +
                output_tokens * GEMINI_FLASH_OUTPUT_USD_PER_1M / 1_000_000)
    return 0.0


def build_nox_mem_costs() -> dict:
    """Compute nox-mem cost breakdown for realistic query profiles."""

    # Assumptions:
    # - Avg query length: 10 tokens (short) to 25 tokens (long)
    # - Retrieval only: no LLM call, just embed + FTS5 + KG + RRF
    # - Answer mode: embed + FTS5 + KG + RRF + LLM (500 in + 150 out tokens)

    short_embed = calc_embed_cost(10)
    medium_embed = calc_embed_cost(18)
    long_embed = calc_embed_cost(25)

    answer_input_tokens = 500   # query + top-k chunk context
    answer_output_tokens = 150  # typical answer

    return {
        "retrieval_only": {
            "short_query": CostBreakdown(
                embed_usd=short_embed,
                fts_usd=0.0,
                kg_walk_usd=0.0,
                rrf_usd=0.0,
                llm_answer_usd=0.0,
                total_usd=short_embed,
                notes="10 avg tokens, Gemini text-embedding-004",
            ),
            "medium_query": CostBreakdown(
                embed_usd=medium_embed,
                fts_usd=0.0,
                kg_walk_usd=0.0,
                rrf_usd=0.0,
                llm_answer_usd=0.0,
                total_usd=medium_embed,
                notes="18 avg tokens, Gemini text-embedding-004",
            ),
            "long_query": CostBreakdown(
                embed_usd=long_embed,
                fts_usd=0.0,
                kg_walk_usd=0.0,
                rrf_usd=0.0,
                llm_answer_usd=0.0,
                total_usd=long_embed,
                notes="25 avg tokens, Gemini text-embedding-004",
            ),
        },
        "answer_mode": {
            "gpt-4.1-mini": CostBreakdown(
                embed_usd=medium_embed,
                fts_usd=0.0,
                kg_walk_usd=0.0,
                rrf_usd=0.0,
                llm_answer_usd=calc_answer_cost(answer_input_tokens, answer_output_tokens, "gpt-4.1-mini"),
                total_usd=medium_embed + calc_answer_cost(answer_input_tokens, answer_output_tokens, "gpt-4.1-mini"),
                notes=f"embed({answer_input_tokens}t) + gpt-4.1-mini({answer_input_tokens}in+{answer_output_tokens}out)",
            ),
            "gemini-2.5-flash-lite": CostBreakdown(
                embed_usd=medium_embed,
                fts_usd=0.0,
                kg_walk_usd=0.0,
                rrf_usd=0.0,
                llm_answer_usd=calc_answer_cost(answer_input_tokens, answer_output_tokens, "gemini-2.5-flash-lite"),
                total_usd=medium_embed + calc_answer_cost(answer_input_tokens, answer_output_tokens, "gemini-2.5-flash-lite"),
                notes=f"embed({answer_input_tokens}t) + gemini-2.5-flash-lite({answer_input_tokens}in+{answer_output_tokens}out)",
            ),
            "gemini-2.5-flash": CostBreakdown(
                embed_usd=medium_embed,
                fts_usd=0.0,
                kg_walk_usd=0.0,
                rrf_usd=0.0,
                llm_answer_usd=calc_answer_cost(answer_input_tokens, answer_output_tokens, "gemini-2.5-flash"),
                total_usd=medium_embed + calc_answer_cost(answer_input_tokens, answer_output_tokens, "gemini-2.5-flash"),
                notes=f"embed({answer_input_tokens}t) + gemini-2.5-flash({answer_input_tokens}in+{answer_output_tokens}out)",
            ),
        },
        "assumptions": {
            "short_query_tokens": 10,
            "medium_query_tokens": 18,
            "long_query_tokens": 25,
            "answer_context_input_tokens": answer_input_tokens,
            "answer_output_tokens": answer_output_tokens,
            "embed_model": "gemini-embedding-001 (= text-embedding-004)",
            "embed_price_per_1m_tokens": GEMINI_EMBED_USD_PER_1M_TOKENS,
            "fts5_price": "$0 — local SQLite, no API",
            "kg_path_price": "$0 — local SQLite graph walk, no API",
            "rrf_price": "$0 — local merge, no API",
        },
    }


# ---------------------------------------------------------------------------
# Competitor cost data
# ---------------------------------------------------------------------------

def build_competitor_costs() -> list[CompetitorCost]:
    """
    Published pricing for comparable memory systems.
    Sources verified 2026-05-29. "not published" = no per-query breakdown available.
    """
    return [
        CompetitorCost(
            name="nox_mem",
            display_name="nox-mem (this project)",
            deployment="self-hosted",
            retrieval_cost_per_query_usd=1.3e-6,  # ~$0.0000013 (10 tokens @ Gemini)
            retrieval_cost_source="Calculated: Gemini text-embedding-004 $0.13/1M tokens × 10 tokens",
            answer_cost_per_query_usd=8.3e-5,  # gemini-2.5-flash-lite default
            saas_plan_notes="No SaaS. Self-hosted only. VPS ~$12/mo covers 69k-chunk production corpus.",
            latency_p50_ms=529,
            latency_source="Measured 2026-05-29, 100 queries, real 69k-chunk VPS corpus",
            self_hosted_available=True,
            embed_dependency="Gemini text-embedding-004 (switchable: OpenAI / Anthropic / local)",
            notes="Backbone-portable. $0 for FTS5+KG+RRF (local SQLite). Embed is only API cost.",
        ),
        CompetitorCost(
            name="zep_cloud",
            display_name="Zep Cloud (SaaS)",
            deployment="SaaS",
            retrieval_cost_per_query_usd=None,  # Per-MAU + token-based, not per-query
            retrieval_cost_source="$49/mo Starter (5k MAU, 1M tokens) → ~$0.049/query @1k queries/day. Source: getzep.com/pricing",
            answer_cost_per_query_usd=None,
            saas_plan_notes="$49/mo Starter | $149/mo Pro + $0.09/1k overage tokens | Enterprise: custom",
            latency_p50_ms=None,
            latency_source="Zep claims '<100ms' (SaaS US-East, not independently verified). No per-percentile breakdown published.",
            self_hosted_available=True,
            embed_dependency="OpenAI (Zep Cloud) or configurable (Zep OSS)",
            notes="Zep OSS (Apache-2.0) available for self-hosting. Zep Cloud adds managed infra. Temporal KG is a differentiator.",
        ),
        CompetitorCost(
            name="zep_oss",
            display_name="Zep OSS (self-hosted)",
            deployment="self-hosted",
            retrieval_cost_per_query_usd=None,  # depends on user's embed provider
            retrieval_cost_source="Embed cost only (user-provided OpenAI key). OpenAI text-embedding-3-small: $0.02/1M tokens → $0.00000018/query @ 9 tokens",
            answer_cost_per_query_usd=None,
            saas_plan_notes="Free (self-hosted). Requires Postgres + Docker.",
            latency_p50_ms=None,
            latency_source="Not published. Requires Postgres + vector extension — likely 20-80ms retrieval (estimated, unverified).",
            self_hosted_available=True,
            embed_dependency="OpenAI (default). Configurable.",
            notes="Requires Postgres. No SQLite mode. KG temporal memory is strongest differentiator vs nox-mem.",
        ),
        CompetitorCost(
            name="mem0_cloud",
            display_name="Mem0 Cloud (SaaS)",
            deployment="SaaS",
            retrieval_cost_per_query_usd=0.001,  # published overage rate
            retrieval_cost_source="$0.001/call overage above plan tier. Source: mem0.ai/pricing (as of 2026-05-29)",
            answer_cost_per_query_usd=None,
            saas_plan_notes="Free (1k memories, 5k calls) | Team $49/mo (50k calls) | Pro $199/mo (500k calls) | $0.001/call overage",
            latency_p50_ms=None,
            latency_source="'Optimized for <200ms' claimed in docs (mem0.ai). No per-percentile published.",
            self_hosted_available=True,
            embed_dependency="OpenAI (default). Configurable.",
            notes="53k+ GitHub stars. OSS version (Apache-2.0) available. Vector + optional graph backend.",
        ),
        CompetitorCost(
            name="mem0_oss",
            display_name="Mem0 OSS (self-hosted)",
            deployment="self-hosted",
            retrieval_cost_per_query_usd=None,
            retrieval_cost_source="Embed cost only. OpenAI text-embedding-3-small default: ~$0.0000002/query",
            answer_cost_per_query_usd=None,
            saas_plan_notes="Free (self-hosted, Apache-2.0). Requires OpenAI API key for default embed.",
            latency_p50_ms=None,
            latency_source="Not published independently. Python-based; likely 100-400ms depending on embed provider latency.",
            self_hosted_available=True,
            embed_dependency="OpenAI (default). Configurable via LiteLLM.",
            notes="Most popular OSS memory library. Production-proven at scale.",
        ),
        CompetitorCost(
            name="memos",
            display_name="MemOS (MemTensor)",
            deployment="self-hosted",
            retrieval_cost_per_query_usd=None,
            retrieval_cost_source="Embed cost only (user-provided). No published per-query breakdown.",
            answer_cost_per_query_usd=None,
            saas_plan_notes="Free (self-hosted, open source). No SaaS offering.",
            latency_p50_ms=None,
            latency_source="Not published. No independent benchmark available.",
            self_hosted_available=True,
            embed_dependency="OpenAI or Hugging Face (user-configured)",
            notes="Research project from MemTensor. Strong benchmark results on EverMemBench (nox-mem vs MemOS: +9.13pp EverMemBench 5-batch). No production latency data.",
        ),
        CompetitorCost(
            name="langmem",
            display_name="LangMem (LangChain)",
            deployment="self-hosted",
            retrieval_cost_per_query_usd=None,
            retrieval_cost_source="Embed cost only. No separate per-query pricing.",
            answer_cost_per_query_usd=None,
            saas_plan_notes="Free (Python library, part of LangChain ecosystem). No separate pricing.",
            latency_p50_ms=None,
            latency_source="Not published. Python-based LangChain integration.",
            self_hosted_available=True,
            embed_dependency="User-provided (OpenAI, Cohere, etc. via LangChain)",
            notes="LangChain integration library. No standalone latency benchmarks published.",
        ),
        CompetitorCost(
            name="letta",
            display_name="Letta / MemGPT (letta-ai)",
            deployment="both",
            retrieval_cost_per_query_usd=None,
            retrieval_cost_source="Cloud: $0.10/1k agent steps. Retrieval-only not separately priced.",
            answer_cost_per_query_usd=None,
            saas_plan_notes="OSS free | Cloud $0.10/1k agent steps | Enterprise: custom",
            latency_p50_ms=None,
            latency_source="Not published for retrieval-only mode. Full agent loop is heavier.",
            self_hosted_available=True,
            embed_dependency="OpenAI (default). Configurable.",
            notes="22k+ stars. Full agent runtime; retrieval-only mode not the primary use case.",
        ),
    ]


# ---------------------------------------------------------------------------
# Cost at scale
# ---------------------------------------------------------------------------

def build_scale_projections(nox_retrieval_per_query: float, nox_answer_per_query: float) -> dict:
    """Project costs at 1k/10k/100k queries per month."""
    tiers = [1_000, 10_000, 100_000, 1_000_000]
    return {
        f"{t:,}_queries_per_month": {
            "retrieval_only_usd": round(t * nox_retrieval_per_query, 4),
            "with_answer_gemini_flash_lite_usd": round(t * nox_answer_per_query, 4),
            "vps_cost_included": "~$12/mo (Hostinger VPS handles all tiers)",
        }
        for t in tiers
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="nox-mem cost calculator")
    parser.add_argument("--output", default="benchmarks/latency-cost/results/cost_analysis.json")
    args = parser.parse_args()

    nox_costs = build_nox_mem_costs()
    competitor_costs = build_competitor_costs()

    # Key numbers for report
    retrieval_usd = nox_costs["retrieval_only"]["medium_query"].total_usd
    answer_usd = nox_costs["answer_mode"]["gemini-2.5-flash-lite"].total_usd

    scale = build_scale_projections(retrieval_usd, answer_usd)

    output = {
        "generated": "2026-05-29",
        "nox_mem": {
            "costs": {k: {vk: asdict(vv) if hasattr(vv, '__dataclass_fields__') else vv
                         for vk, vv in v.items()}
                     if isinstance(v, dict) else v
                     for k, v in nox_costs.items()},
        },
        "competitors": [asdict(c) for c in competitor_costs],
        "scale_projections": scale,
        "key_findings": {
            "retrieval_cost_per_query_usd": retrieval_usd,
            "retrieval_cost_per_1k_queries_usd": round(retrieval_usd * 1000, 6),
            "answer_cost_gemini_flash_lite_per_query_usd": round(answer_usd, 7),
            "kg_path_cost_per_query_usd": 0.0,
            "fts5_cost_per_query_usd": 0.0,
            "vps_monthly_usd": 12.0,
            "break_even_queries_per_month": "Any usage — VPS fixed cost dominates",
            "embed_is_only_api_cost": True,
            "headline": (
                f"nox-mem: ${retrieval_usd:.7f}/query retrieval-only "
                f"(vs Mem0 Cloud $0.001/call = {round(0.001/retrieval_usd):.0f}× more expensive). "
                f"KG path retrieval: $0.00/query. "
                f"Self-hosted, no per-query SaaS fees."
            ),
        },
        "pricing_sources": {
            "gemini_embed": "ai.google.dev/pricing — text-embedding-004",
            "gpt41_mini": "openai.com/pricing — gpt-4.1-mini",
            "gemini_flash_lite": "ai.google.dev/pricing — gemini-2.5-flash-lite",
            "zep_cloud": "getzep.com/pricing",
            "mem0_cloud": "mem0.ai/pricing",
            "memos": "github.com/MemTensor/MemOS (open source, no SaaS)",
            "langmem": "github.com/langchain-ai/langmem (open source)",
            "letta": "letta.ai/pricing",
            "verified_date": "2026-05-29",
        },
    }

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Wrote cost analysis to {args.output}")

    # Print summary
    print("\n=== Cost Summary ===")
    print(f"nox-mem retrieval only:           ${retrieval_usd:.8f}/query")
    print(f"nox-mem retrieval (per 1k):       ${retrieval_usd * 1000:.4f}")
    print(f"nox-mem + answer (flash-lite):    ${answer_usd:.6f}/query")
    print(f"nox-mem KG path:                  $0.0000000/query")
    print(f"Mem0 Cloud (overage):             $0.001000/query  ({round(0.001/retrieval_usd):.0f}× more)")
    print(f"Zep Cloud Starter ($49/mo@1k/d):  ~$0.049000/query (plan-based)")

    return output


if __name__ == "__main__":
    main()
