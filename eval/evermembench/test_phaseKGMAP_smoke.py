"""Smoke test for Phase KGMAP (Wave B composability) — KG-anchored MA-protection.

Validates without VPS / network:
  1. ENTITY_SECTION_NAMES constant + default MA_PROTECTION_MAX.
  2. _ma_extract_protected_chunk_ids_section() correctly:
     - Returns set of chunk_ids whose `section` ∈ ENTITY_SECTION_NAMES.
     - Skips chunks with section=None or section outside the whitelist.
     - Skips chunks with missing or non-integer chunk_id.
  3. _ma_extract_protected_chunk_ids_kg_anchor() correctly:
     - Returns intersection of candidates.chunk_id with kg_evidence_chunk_ids.
     - Returns empty set if kg_evidence_chunk_ids is empty (no entities matched).
     - Handles candidates with missing chunk_id gracefully.
  4. _ma_partition_candidates() correctly:
     - Set E preserves bi-encoder positions.
     - Set R contains the rest in bi-encoder order.
     - Caps Set E at max_protected (drops overflow).
  5. _ma_merge_preserving_protected_positions() correctly:
     - Places entity chunks at their original bi-encoder positions.
     - Fills empty slots with reranked Set R in rerank order.
     - Handles edge cases: empty Set E, empty Set R, both empty, overflow.
  6. NoxMemAdapter init reads NOX_MA_PROTECTION_ENABLED + NOX_MA_PROTECTION_KG_ANCHOR
     env vars correctly (truthy / falsy / unset for each adapter_mode).
  7. NoxMemAdapter init with NOX_ADAPTER_MODE=phaseKGMAP enables KG + rerank +
     MA protection + KG anchor by default.
  8. NoxMemAdapter init with NOX_ADAPTER_MODE=phaseMAP enables rerank +
     MA protection but NOT KG path / KG anchor (unless env override).

Run:
    python eval/evermembench/test_phaseKGMAP_smoke.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Stub-import path: import adapter directly (bypasses harness).
sys.path.insert(0, str(Path(__file__).parent))
import adapter_nox_mem as A  # noqa: E402


def _mk(
    text: str,
    section: str | None = None,
    cid: int | None = None,
    **extra: Any,
) -> Tuple[str, Dict[str, Any]]:
    """Build a candidate tuple matching adapter's (chunk_text, item) shape."""
    item: Dict[str, Any] = {"chunk_text": text, "section": section}
    if cid is not None:
        item["id"] = cid
    item.update(extra)
    return (text, item)


def _check(cond: bool, label: str, failures: List[str]) -> None:
    if not cond:
        failures.append(label)
        print(f"  FAIL: {label}")
    else:
        print(f"  ok: {label}")


def _section_constants(failures: List[str]) -> None:
    print("\n[1] Constants")
    _check(
        "compiled" in A.ENTITY_SECTION_NAMES,
        "ENTITY_SECTION_NAMES contains 'compiled'",
        failures,
    )
    _check(
        "frontmatter" in A.ENTITY_SECTION_NAMES,
        "ENTITY_SECTION_NAMES contains 'frontmatter'",
        failures,
    )
    _check(
        len(A.ENTITY_SECTION_NAMES) == 2,
        "ENTITY_SECTION_NAMES is exactly {'compiled', 'frontmatter'}",
        failures,
    )
    _check(
        isinstance(A.DEFAULT_MA_PROTECTION_MAX, int)
        and A.DEFAULT_MA_PROTECTION_MAX > 0,
        f"DEFAULT_MA_PROTECTION_MAX is positive int (got {A.DEFAULT_MA_PROTECTION_MAX})",
        failures,
    )


def _section_extract(failures: List[str]) -> None:
    print("\n[2] _ma_extract_protected_chunk_ids_section")
    cands = [
        _mk("ent compiled", section="compiled", cid=1),
        _mk("ent frontmatter", section="frontmatter", cid=2),
        _mk("ent timeline", section="timeline", cid=3),
        _mk("ent NULL", section=None, cid=4),
        _mk("ent compiled NO ID", section="compiled"),  # missing cid → skip
        _mk("ent compiled bad ID", section="compiled", cid="abc"),  # bad type
        _mk("ent CASE", section="COMPILED", cid=7),  # case-insensitive
    ]
    out = A._ma_extract_protected_chunk_ids_section(cands)
    _check(1 in out, "section=compiled (id=1) protected", failures)
    _check(2 in out, "section=frontmatter (id=2) protected", failures)
    _check(3 not in out, "section=timeline (id=3) NOT protected", failures)
    _check(4 not in out, "section=None (id=4) NOT protected", failures)
    _check(7 in out, "section=COMPILED case-insensitive (id=7) protected", failures)
    _check(
        len(out) == 3,
        f"exactly 3 protected (got {len(out)} = {out})",
        failures,
    )


def _section_extract_kg(failures: List[str]) -> None:
    print("\n[3] _ma_extract_protected_chunk_ids_kg_anchor")
    cands = [
        _mk("c1", cid=10),
        _mk("c2", cid=20),
        _mk("c3", cid=30),
        _mk("c4", cid=40),
        _mk("c5 no cid"),  # missing chunk_id
    ]
    # KG evidence pool = {10, 30, 99}; 99 not in candidates
    kg_pool = {10, 30, 99}
    out = A._ma_extract_protected_chunk_ids_kg_anchor(cands, kg_pool)
    _check(10 in out, "cid=10 KG-protected (in pool + in candidates)", failures)
    _check(30 in out, "cid=30 KG-protected", failures)
    _check(99 not in out, "cid=99 NOT in candidates → not in output", failures)
    _check(20 not in out, "cid=20 NOT in KG pool → not protected", failures)
    _check(len(out) == 2, f"exactly 2 KG-protected (got {len(out)})", failures)

    # Empty pool → empty output
    out_empty = A._ma_extract_protected_chunk_ids_kg_anchor(cands, set())
    _check(out_empty == set(), "empty KG pool → empty output", failures)


def _section_partition(failures: List[str]) -> None:
    print("\n[4] _ma_partition_candidates")
    cands = [
        _mk("c0", cid=10),  # protected
        _mk("c1", cid=20),  # not
        _mk("c2", cid=30),  # protected
        _mk("c3", cid=40),  # not
        _mk("c4", cid=50),  # protected (would-be 3rd)
    ]
    protected = {10, 30, 50}

    # max_protected=10 → all 3 in Set E
    set_e, set_r = A._ma_partition_candidates(cands, protected, max_protected=10)
    _check(len(set_e) == 3, f"Set E size=3 (got {len(set_e)})", failures)
    _check(len(set_r) == 2, f"Set R size=2 (got {len(set_r)})", failures)
    _check(set_e[0][0] == 0, "Set E[0] bi position = 0 (c0)", failures)
    _check(set_e[1][0] == 2, "Set E[1] bi position = 2 (c2)", failures)
    _check(set_e[2][0] == 4, "Set E[2] bi position = 4 (c4)", failures)

    # max_protected=2 → caps at 2 (drops c4)
    set_e2, set_r2 = A._ma_partition_candidates(cands, protected, max_protected=2)
    _check(len(set_e2) == 2, f"Set E capped at 2 (got {len(set_e2)})", failures)
    # c4 (cid=50) should land in set_r2 instead
    set_r2_cids = [it.get("id") for _c, it in set_r2]
    _check(50 in set_r2_cids, "c4 (capped overflow) lands in Set R", failures)


def _section_merge(failures: List[str]) -> None:
    print("\n[5] _ma_merge_preserving_protected_positions")

    # Case 1: all protected (Set R empty) → return Set E in bi order
    set_e = [(2, _mk("e2", cid=20)), (0, _mk("e0", cid=10))]
    out = A._ma_merge_preserving_protected_positions(set_e, [], total_slots=5)
    _check(len(out) == 2, "all protected → len matches set_e", failures)
    _check(out[0][1]["id"] == 10, "all protected → bi order preserved (e0 first)", failures)

    # Case 2: no protected → return Set R reranked
    set_r = [_mk("r0", cid=100), _mk("r1", cid=101), _mk("r2", cid=102)]
    out = A._ma_merge_preserving_protected_positions([], set_r, total_slots=5)
    _check(len(out) == 3, "no protected → len matches set_r", failures)
    _check(out[0][1]["id"] == 100, "no protected → rerank order preserved", failures)

    # Case 3: mixed — Set E at positions 0,2; Set R reranked fills 1,3,4
    set_e3 = [(0, _mk("e_pos0", cid=10)), (2, _mk("e_pos2", cid=20))]
    set_r3 = [_mk("r_top", cid=100), _mk("r_mid", cid=101), _mk("r_bot", cid=102)]
    out3 = A._ma_merge_preserving_protected_positions(set_e3, set_r3, total_slots=5)
    _check(len(out3) == 5, "mixed → total_slots respected", failures)
    _check(out3[0][1]["id"] == 10, "mixed → e_pos0 at slot 0", failures)
    _check(out3[2][1]["id"] == 20, "mixed → e_pos2 at slot 2", failures)
    _check(out3[1][1]["id"] == 100, "mixed → rerank top at slot 1", failures)
    _check(out3[3][1]["id"] == 101, "mixed → rerank mid at slot 3", failures)
    _check(out3[4][1]["id"] == 102, "mixed → rerank bot at slot 4", failures)

    # Case 4: total_slots=0 → empty list
    out4 = A._ma_merge_preserving_protected_positions(set_e3, set_r3, total_slots=0)
    _check(out4 == [], "total_slots=0 → empty list", failures)

    # Case 5: set_r exhausted before slots fill (skip trailing Nones)
    set_e5 = [(0, _mk("e0", cid=10))]
    set_r5 = [_mk("r0", cid=100)]
    out5 = A._ma_merge_preserving_protected_positions(set_e5, set_r5, total_slots=5)
    _check(len(out5) == 2, f"set_r exhausted → compact (got len={len(out5)})", failures)
    _check(out5[0][1]["id"] == 10 and out5[1][1]["id"] == 100, "exhaustion order ok", failures)

    # Case 6: set_e overflow into single slot (bi_pos > total_slots)
    set_e6 = [(99, _mk("e99", cid=10)), (50, _mk("e50", cid=20))]
    out6 = A._ma_merge_preserving_protected_positions(set_e6, [], total_slots=3)
    # Both clamped to slot 2, first wins, second falls back to slot 1
    _check(len(out6) <= 3, "set_e overflow clamped within total_slots", failures)


def _section_init(failures: List[str]) -> None:
    print("\n[6] NoxMemAdapter init env vars")
    # Save env to restore at end
    save = {
        k: os.environ.get(k)
        for k in [
            "NOX_ADAPTER_MODE",
            "NOX_MA_PROTECTION_ENABLED",
            "NOX_MA_PROTECTION_KG_ANCHOR",
            "NOX_KG_PATH_ENABLED",
            "NOX_RERANKER_ENABLED",
            "NOX_DB_PATH",
            "NOX_MA_PROTECTION_MAX",
        ]
    }

    def _clear() -> None:
        for k in save:
            os.environ.pop(k, None)

    try:
        # Case 1: phaseB (default) → MA protection OFF
        _clear()
        os.environ["NOX_ADAPTER_MODE"] = "phaseB"
        a = A.NoxMemAdapter(config={})
        _check(not a.ma_protection_enabled, "phaseB → MA protection OFF", failures)
        _check(not a.ma_protection_kg_anchor, "phaseB → KG anchor OFF", failures)

        # Case 2: phaseMAP → MA on, KG anchor OFF, rerank ON
        _clear()
        os.environ["NOX_ADAPTER_MODE"] = "phaseMAP"
        a = A.NoxMemAdapter(config={})
        _check(a.ma_protection_enabled, "phaseMAP → MA protection ON", failures)
        _check(not a.ma_protection_kg_anchor, "phaseMAP → KG anchor OFF (no auto)", failures)
        _check(a.reranker_enabled, "phaseMAP → rerank ON", failures)
        _check(not a.kg_enabled, "phaseMAP → KG path OFF", failures)

        # Case 3: phaseKGMAP → MA + KG anchor + rerank + KG path all ON
        _clear()
        os.environ["NOX_ADAPTER_MODE"] = "phaseKGMAP"
        a = A.NoxMemAdapter(config={})
        _check(a.ma_protection_enabled, "phaseKGMAP → MA protection ON", failures)
        _check(a.ma_protection_kg_anchor, "phaseKGMAP → KG anchor ON", failures)
        _check(a.reranker_enabled, "phaseKGMAP → rerank ON", failures)
        _check(a.kg_enabled, "phaseKGMAP → KG path ON", failures)

        # Case 4: phaseB + env truthy
        _clear()
        os.environ["NOX_ADAPTER_MODE"] = "phaseB"
        os.environ["NOX_MA_PROTECTION_ENABLED"] = "1"
        os.environ["NOX_MA_PROTECTION_KG_ANCHOR"] = "1"
        a = A.NoxMemAdapter(config={})
        _check(a.ma_protection_enabled, "phaseB + MA=1 → MA ON", failures)
        _check(a.ma_protection_kg_anchor, "phaseB + KG anchor=1 → ON", failures)

        # Case 5: phaseKGMAP + env falsy → MA OFF
        _clear()
        os.environ["NOX_ADAPTER_MODE"] = "phaseKGMAP"
        os.environ["NOX_MA_PROTECTION_ENABLED"] = "0"
        a = A.NoxMemAdapter(config={})
        _check(not a.ma_protection_enabled, "phaseKGMAP + MA=0 → MA OFF", failures)

        # Case 6: max override
        _clear()
        os.environ["NOX_MA_PROTECTION_MAX"] = "5"
        a = A.NoxMemAdapter(config={})
        _check(a.ma_protection_max == 5, "NOX_MA_PROTECTION_MAX=5 honored", failures)

    finally:
        # Restore env
        _clear()
        for k, v in save.items():
            if v is not None:
                os.environ[k] = v


def main() -> int:
    print("=" * 70)
    print("Phase KGMAP smoke test (Wave B composability)")
    print("=" * 70)
    failures: List[str] = []
    _section_constants(failures)
    _section_extract(failures)
    _section_extract_kg(failures)
    _section_partition(failures)
    _section_merge(failures)
    _section_init(failures)
    print("\n" + "=" * 70)
    if failures:
        print(f"FAIL: {len(failures)} assertion(s) failed:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("PASS: all assertions green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
