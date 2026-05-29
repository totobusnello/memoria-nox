"""Smoke test for Phase Triple (Wave C composability) — KG + MQ + MAP combined.

Validates the triple-mode wiring without VPS / network:
  1. NOX_ADAPTER_MODE=phaseTriple turns on:
       - kg_enabled (KG 1-hop entity walk in retrieval stage)
       - mq_enabled (multi-query sub-question decomposition + RRF union)
       - reranker_enabled (cross-encoder rerank stage)
       - ma_protection_enabled (bypass-entity protection on rerank)
       - ma_protection_kg_anchor (extends bypass set with KG-evidence chunks)
  2. Triple mode is the only mode that fires ALL FOUR flags by default.
     Cross-check against phaseKGMQ (no MAP), phaseKGMAP (no MQ), phaseMQ alone.
  3. Env override discipline holds for each flag in triple mode (each can
     be force-disabled via NOX_*=0 even when default-on).
  4. metadata payload exposed by the adapter includes all triple flags
     correctly (kg_enabled / mq_enabled / reranker_enabled /
     ma_protection_enabled / ma_protection_kg_anchor) — downstream
     dashboards must be able to detect triple mode without inspecting
     NOX_ADAPTER_MODE directly.

Run:
    python eval/evermembench/test_phaseTriple_smoke.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Stub-import path: import adapter directly (bypasses harness).
sys.path.insert(0, str(Path(__file__).parent))
import adapter_nox_mem as A  # noqa: E402


_PASS = 0
_FAIL = 0


def _assert(cond: bool, msg: str) -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  PASS  {msg}")
    else:
        _FAIL += 1
        print(f"  FAIL  {msg}")


def _scrub_env() -> None:
    """Clear every flag the adapter reads so default-from-mode logic isn't masked."""
    for key in (
        "NOX_ADAPTER_MODE",
        "NOX_KG_PATH_ENABLED",
        "NOX_MQ_ENABLED",
        "NOX_RERANKER_ENABLED",
        "NOX_MA_PROTECTION_ENABLED",
        "NOX_MA_PROTECTION_KG_ANCHOR",
        "NOX_KG_ANCHOR",
    ):
        os.environ.pop(key, None)


def _build_adapter(**overrides: str) -> A.NoxMemAdapter:
    _scrub_env()
    for k, v in overrides.items():
        os.environ[k] = v
    return A.NoxMemAdapter({})


def test_phase_triple_default_fires_all_four_stages() -> None:
    print("\n[1] phaseTriple default → kg + mq + rerank + ma_protection + kg_anchor")
    a = _build_adapter(NOX_ADAPTER_MODE="phaseTriple")
    _assert(a.kg_enabled is True, "kg_enabled default-on in phaseTriple")
    _assert(a.mq_enabled is True, "mq_enabled default-on in phaseTriple")
    _assert(a.reranker_enabled is True, "reranker_enabled default-on in phaseTriple")
    _assert(a.ma_protection_enabled is True, "ma_protection_enabled default-on in phaseTriple")
    _assert(
        a.ma_protection_kg_anchor is True,
        "ma_protection_kg_anchor default-on in phaseTriple",
    )


def test_phase_triple_is_strictly_richer_than_sub_modes() -> None:
    print("\n[2] phaseTriple ⊃ phaseKGMQ ∪ phaseKGMAP ∪ phaseMQ")

    a_kgmq = _build_adapter(NOX_ADAPTER_MODE="phaseKGMQ")
    _assert(a_kgmq.kg_enabled and a_kgmq.mq_enabled, "phaseKGMQ has KG + MQ")
    _assert(
        a_kgmq.ma_protection_enabled is False,
        "phaseKGMQ has NO ma_protection (triple-only)",
    )
    _assert(
        a_kgmq.reranker_enabled is False,
        "phaseKGMQ has NO rerank (triple-only via MAP layer)",
    )

    a_kgmap = _build_adapter(NOX_ADAPTER_MODE="phaseKGMAP")
    _assert(
        a_kgmap.kg_enabled and a_kgmap.reranker_enabled and a_kgmap.ma_protection_enabled,
        "phaseKGMAP has KG + rerank + ma_protection",
    )
    _assert(
        a_kgmap.mq_enabled is False, "phaseKGMAP has NO MQ (triple-only)"
    )

    a_mq = _build_adapter(NOX_ADAPTER_MODE="phaseMQ")
    _assert(a_mq.mq_enabled is True, "phaseMQ has MQ")
    _assert(
        not any([a_mq.kg_enabled, a_mq.reranker_enabled, a_mq.ma_protection_enabled]),
        "phaseMQ has only MQ active (no KG/rerank/MAP)",
    )


def test_phase_triple_env_overrides_each_stage_off() -> None:
    print("\n[3] phaseTriple + per-flag env=0 → flag disabled (override discipline)")
    cases = [
        ("NOX_KG_PATH_ENABLED", "kg_enabled"),
        ("NOX_MQ_ENABLED", "mq_enabled"),
        ("NOX_RERANKER_ENABLED", "reranker_enabled"),
        ("NOX_MA_PROTECTION_ENABLED", "ma_protection_enabled"),
        ("NOX_MA_PROTECTION_KG_ANCHOR", "ma_protection_kg_anchor"),
    ]
    for env_key, attr in cases:
        a = _build_adapter(NOX_ADAPTER_MODE="phaseTriple", **{env_key: "0"})
        _assert(
            getattr(a, attr) is False,
            f"phaseTriple + {env_key}=0 disables {attr}",
        )


def test_phase_triple_env_override_each_stage_on_alt_mode() -> None:
    print("\n[4] phaseB + triple env flags=1 → equivalent to phaseTriple behaviour")
    a = _build_adapter(
        NOX_ADAPTER_MODE="phaseB",
        NOX_KG_PATH_ENABLED="1",
        NOX_MQ_ENABLED="1",
        NOX_RERANKER_ENABLED="1",
        NOX_MA_PROTECTION_ENABLED="1",
        NOX_MA_PROTECTION_KG_ANCHOR="1",
    )
    _assert(a.kg_enabled, "phaseB + NOX_KG_PATH_ENABLED=1 turns kg on")
    _assert(a.mq_enabled, "phaseB + NOX_MQ_ENABLED=1 turns mq on")
    _assert(a.reranker_enabled, "phaseB + NOX_RERANKER_ENABLED=1 turns rerank on")
    _assert(
        a.ma_protection_enabled,
        "phaseB + NOX_MA_PROTECTION_ENABLED=1 turns map on",
    )
    _assert(
        a.ma_protection_kg_anchor,
        "phaseB + NOX_MA_PROTECTION_KG_ANCHOR=1 turns kg-anchor on",
    )


def test_phase_triple_metadata_exposed() -> None:
    print("\n[5] adapter has the metadata attributes downstream aggregator reads")
    a = _build_adapter(NOX_ADAPTER_MODE="phaseTriple")
    for attr in (
        "adapter_mode",
        "kg_enabled",
        "mq_enabled",
        "reranker_enabled",
        "ma_protection_enabled",
        "ma_protection_kg_anchor",
        "kg_boost_magnitude",
        "kg_max_neighbors",
        "mq_n",
        "mq_per_query_topk",
        "mq_rrf_k",
        "ma_protection_max",
    ):
        _assert(hasattr(a, attr), f"adapter exposes {attr}")
    _assert(a.adapter_mode == "phaseTriple", "adapter_mode == phaseTriple")


def main() -> int:
    test_phase_triple_default_fires_all_four_stages()
    test_phase_triple_is_strictly_richer_than_sub_modes()
    test_phase_triple_env_overrides_each_stage_off()
    test_phase_triple_env_override_each_stage_on_alt_mode()
    test_phase_triple_metadata_exposed()

    print(f"\nSummary: {_PASS} pass, {_FAIL} fail")
    return 0 if _FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
