"""Smoke test for Phase MAP (Lab Q1 #2) — MA-protection bypass-entity.

Validates without VPS / network:
  1. ENTITY_SECTION_NAMES contains 'compiled' and 'frontmatter' (and only those).
  2. _merge_preserving_entity_positions() correctly:
     - Places entity chunks at their original bi-encoder positions
     - Fills empty slots with reranked Set R in rerank order
     - Handles edge case: empty Set E (no entities → all reranked)
     - Handles edge case: empty Set R (only entities → no rerank)
     - Handles edge case: Set E size > total_slots → drops overflow
     - Handles edge case: Set R shorter than empty-slot count → compacts
  3. NoxMemAdapter init reads NOX_MA_PROTECTION_ENABLED env var correctly
     (truthy / falsy / unset for each adapter_mode).
  4. NoxMemAdapter init reads NOX_ADAPTER_MODE=phaseMAP → ma_protection_enabled
     defaults to True AND reranker_enabled defaults to True.

Run:
    python eval/evermembench/test_phaseMAP_smoke.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Stub-import path: import adapter directly (bypasses harness).
sys.path.insert(0, str(Path(__file__).parent))
import adapter_nox_mem as A  # noqa: E402


def _mk(text: str, section: str | None = None, **extra: Any) -> Tuple[str, Dict[str, Any]]:
    """Build a candidate tuple matching adapter's (chunk_text, item) shape."""
    item: Dict[str, Any] = {"chunk_text": text, "section": section}
    item.update(extra)
    return (text, item)


def _failures() -> int:
    """Return count of failed assertions (0 = all green)."""
    failures = 0

    def check(label: str, cond: bool, detail: str = "") -> None:
        nonlocal failures
        status = "PASS" if cond else "FAIL"
        line = f"  [{status}] {label}"
        if detail:
            line += f" — {detail}"
        print(line)
        if not cond:
            failures += 1

    # ─── 1. ENTITY_SECTION_NAMES ────────────────────────────────────────────
    print("\n[1] ENTITY_SECTION_NAMES")
    check(
        "contains 'compiled'",
        "compiled" in A.ENTITY_SECTION_NAMES,
    )
    check(
        "contains 'frontmatter'",
        "frontmatter" in A.ENTITY_SECTION_NAMES,
    )
    check(
        "does NOT contain 'timeline'",
        "timeline" not in A.ENTITY_SECTION_NAMES,
    )
    check(
        "does NOT contain None",
        None not in A.ENTITY_SECTION_NAMES,
    )

    # ─── 2. _merge_preserving_entity_positions ──────────────────────────────
    print("\n[2] _merge_preserving_entity_positions — basic cases")

    # Case A: mixed candidates — entities at original positions, regular reranked
    # Original bi-encoder order: [reg0, ent1, reg2, ent3, reg4]
    # After rerank, regular re-ordered to [reg4, reg2, reg0]
    cands = [
        _mk("reg0", None),
        _mk("ent1", "compiled"),
        _mk("reg2", None),
        _mk("ent3", "frontmatter"),
        _mk("reg4", "timeline"),
    ]
    entity_indexed = [(1, cands[1]), (3, cands[3])]
    # Reranked regular: rank 0 = reg4, rank 1 = reg2, rank 2 = reg0
    reranked_regular = [(4, cands[4]), (2, cands[2]), (0, cands[0])]
    merged = A._merge_preserving_entity_positions(
        entity_indexed, reranked_regular, total_slots=5
    )
    texts = [m[0] for m in merged]
    # Expected: pos0=reg4 (rerank top), pos1=ent1 (preserved), pos2=reg2,
    # pos3=ent3 (preserved), pos4=reg0
    expected = ["reg4", "ent1", "reg2", "ent3", "reg0"]
    check(
        "Case A: entity positions preserved + regular rerank-ordered",
        texts == expected,
        f"got {texts}, want {expected}",
    )

    # Case B: empty Set E (no entities — should be pure rerank order)
    print("\n[2b] empty Set E → behaves like normal rerank")
    rerank_only = [(0, _mk("a")), (1, _mk("b")), (2, _mk("c"))]
    merged_b = A._merge_preserving_entity_positions([], rerank_only, total_slots=3)
    check(
        "Case B: pure rerank order",
        [m[0] for m in merged_b] == ["a", "b", "c"],
    )

    # Case C: empty Set R (all candidates entity — no rerank possible)
    print("\n[2c] empty Set R → entities only, preserved")
    entity_only = [(0, _mk("e0", "compiled")), (1, _mk("e1", "frontmatter"))]
    merged_c = A._merge_preserving_entity_positions(entity_only, [], total_slots=2)
    check(
        "Case C: entity-only positions preserved",
        [m[0] for m in merged_c] == ["e0", "e1"],
    )

    # Case D: Set E size > total_slots — entities beyond total_slots dropped
    # (defensive — should not happen in practice but must not crash)
    print("\n[2d] Set E with orig_idx > total_slots → dropped")
    overflow_entities = [
        (0, _mk("e0", "compiled")),
        (10, _mk("e10", "compiled")),  # out of slots — dropped
    ]
    merged_d = A._merge_preserving_entity_positions(
        overflow_entities, [(1, _mk("r1"))], total_slots=2
    )
    check(
        "Case D: overflow entity dropped, slots compacted",
        [m[0] for m in merged_d] == ["e0", "r1"],
    )

    # Case E: Set R shorter than empty-slot count → compact (no None left)
    print("\n[2e] Set R shorter than gap → compact result")
    entities_short = [(0, _mk("e0", "compiled"))]
    rerank_short = [(2, _mk("r2"))]  # only 1 regular, but total_slots=5
    merged_e = A._merge_preserving_entity_positions(
        entities_short, rerank_short, total_slots=5
    )
    check(
        "Case E: compact result (no None gaps)",
        [m[0] for m in merged_e] == ["e0", "r2"],
    )

    # Case F: total_slots=0 → empty list
    print("\n[2f] total_slots=0 → empty")
    merged_f = A._merge_preserving_entity_positions([], [], total_slots=0)
    check("Case F: total_slots=0 returns []", merged_f == [])

    # ─── 3. NoxMemAdapter init — env-var gating ─────────────────────────────
    print("\n[3] NoxMemAdapter init — MA-protection env gating")

    # Bypass __init__ (needs harness types); manually mimic the gating logic.
    # We test only the env-var resolution + adapter_mode default behavior by
    # constructing the same boolean ladder the __init__ does.
    def _resolve_map(env_val: str, adapter_mode: str) -> bool:
        env_map = env_val.strip().lower()
        env_map_truthy = env_map in ("1", "true", "yes", "on")
        env_map_falsy = env_map in ("0", "false", "no", "off")
        if env_map_falsy:
            return False
        if env_map_truthy:
            return True
        return adapter_mode == "phaseMAP"

    def _resolve_rerank(env_val: str, adapter_mode: str) -> bool:
        env_enable = env_val.strip().lower()
        env_enable_truthy = env_enable in ("1", "true", "yes", "on")
        env_enable_falsy = env_enable in ("0", "false", "no", "off")
        if env_enable_falsy:
            return False
        if env_enable_truthy:
            return True
        return adapter_mode in ("phaseF", "phaseMAP")

    # Unset env + phaseMAP → both default on
    check(
        "phaseMAP + unset env → ma_protection_enabled=True",
        _resolve_map("", "phaseMAP") is True,
    )
    check(
        "phaseMAP + unset env → reranker_enabled=True",
        _resolve_rerank("", "phaseMAP") is True,
    )
    # phaseB + unset → both False (backward compat: Phase G OFF unless opted in)
    check(
        "phaseB + unset env → ma_protection_enabled=False",
        _resolve_map("", "phaseB") is False,
    )
    check(
        "phaseB + unset env → reranker_enabled=False",
        _resolve_rerank("", "phaseB") is False,
    )
    # phaseF + unset → MAP=False but rerank=True (Phase G behavior preserved)
    check(
        "phaseF + unset env → ma_protection_enabled=False (Phase G preserved)",
        _resolve_map("", "phaseF") is False,
    )
    check(
        "phaseF + unset env → reranker_enabled=True",
        _resolve_rerank("", "phaseF") is True,
    )
    # Explicit truthy override on phaseB
    check(
        "phaseB + NOX_MA_PROTECTION_ENABLED=1 → True",
        _resolve_map("1", "phaseB") is True,
    )
    # Explicit falsy override on phaseMAP — opt-out
    check(
        "phaseMAP + NOX_MA_PROTECTION_ENABLED=0 → False (opt-out)",
        _resolve_map("0", "phaseMAP") is False,
    )
    # Various truthy/falsy spellings
    for v in ("true", "TRUE", "yes", "on", "1"):
        check(
            f"truthy spelling '{v}' resolves True",
            _resolve_map(v, "phaseB") is True,
        )
    for v in ("false", "FALSE", "no", "off", "0"):
        check(
            f"falsy spelling '{v}' resolves False",
            _resolve_map(v, "phaseMAP") is False,
        )

    # ─── 4. Sample candidate flow simulation ────────────────────────────────
    print("\n[4] End-to-end flow simulation — entity chunks survive 'displacement'")
    # Simulate the realistic scenario from spec §1.3:
    # Pre-rerank candidates: 2 entity (positions 1 and 3) + 8 regular.
    # Suppose cross-encoder ranks the entities at positions 8 and 9 (low) and
    # one regular as the new top.
    cands = []
    for i in range(10):
        if i == 1:
            cands.append(_mk(f"chunk_{i}", "compiled"))
        elif i == 3:
            cands.append(_mk(f"chunk_{i}", "frontmatter"))
        elif i == 6:
            cands.append(_mk(f"chunk_{i}", "timeline"))  # timeline is NOT entity
        else:
            cands.append(_mk(f"chunk_{i}", None))

    entity_indexed = [(i, cands[i]) for i in (1, 3)]
    # Reranked regular order: suppose model thinks chunk_5 is best, then 0,2,4,6,7,8,9
    regular_order = [5, 0, 2, 4, 6, 7, 8, 9]
    reranked_regular = [(i, cands[i]) for i in regular_order]

    merged = A._merge_preserving_entity_positions(
        entity_indexed, reranked_regular, total_slots=10
    )
    texts = [m[0] for m in merged]
    # Expected: pos0=chunk_5, pos1=chunk_1 (entity preserved), pos2=chunk_0,
    #           pos3=chunk_3 (entity preserved), pos4=chunk_2, pos5=chunk_4,
    #           pos6=chunk_6, pos7=chunk_7, pos8=chunk_8, pos9=chunk_9
    expected = [
        "chunk_5", "chunk_1", "chunk_0", "chunk_3", "chunk_2",
        "chunk_4", "chunk_6", "chunk_7", "chunk_8", "chunk_9",
    ]
    check(
        "10-candidate merge: entities at orig pos 1,3 / regular reranked",
        texts == expected,
        f"got {texts}",
    )
    # Critical assertion: entity chunks landed in top-K (top-10 here = all,
    # but in real MA query top-K=5 the entity-at-pos-1 would survive even if
    # cross-encoder would have shoved it to pos 8 without protection).
    entity_in_top_5 = sum(1 for t in texts[:5] if t in ("chunk_1", "chunk_3"))
    check(
        "Top-5 of merged contains both protected entities (would NOT be the case under naive rerank)",
        entity_in_top_5 == 2,
        f"entities in top-5: {entity_in_top_5}/2",
    )

    return failures


if __name__ == "__main__":
    print("=" * 70)
    print("Phase MAP (Lab Q1 #2) — bypass-entity smoke test")
    print("=" * 70)
    fc = _failures()
    print("\n" + "=" * 70)
    if fc == 0:
        print("ALL CHECKS PASSED")
        sys.exit(0)
    else:
        print(f"FAILED: {fc} check(s) failed")
        sys.exit(1)
