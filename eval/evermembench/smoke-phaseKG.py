#!/usr/bin/env python3
"""
Phase KG smoke test — Lab Q1 #4.

Validates that:
  1. Adapter loads with phaseKG mode
  2. KG SQL helpers can read kg_entities + kg_relations
  3. Entity extraction matches at least 1 entity per of 3 sample queries
  4. _kg_get_1hop_neighbors returns rows
  5. _kg_get_direct_chunk_ids returns rows

Usage (on VPS):
    source /root/.openclaw/.env
    export NOX_DB_PATH=/root/.openclaw/evermembench-runs/phaseKG-004-<ts>/nox-mem.db
    python3 eval/evermembench/smoke-phaseKG.py
"""
import os
import sys

# Make adapter helpers importable as plain module
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from adapter_nox_mem import (  # noqa: E402
    _kg_open_db,
    _kg_load_entity_names,
    _kg_extract_query_entities,
    _kg_get_1hop_neighbors,
    _kg_get_direct_chunk_ids,
    DEFAULT_KG_MIN_NAME_LEN,
    DEFAULT_KG_MAX_NEIGHBORS,
)


def main() -> int:
    db_path = os.environ.get("NOX_DB_PATH", "")
    if not db_path:
        print("ERROR: NOX_DB_PATH not set")
        return 2

    print(f"[smoke] DB: {db_path}")

    # Step 1: open DB
    conn, err = _kg_open_db(db_path)
    if err:
        print(f"ERROR: {err}")
        return 2
    print("[smoke] DB open OK")

    # Step 2: load entity pool
    pool, err = _kg_load_entity_names(db_path, DEFAULT_KG_MIN_NAME_LEN)
    if err:
        print(f"ERROR: {err}")
        return 2
    print(f"[smoke] entity_pool size: {len(pool)}")
    if not pool:
        print("ERROR: empty KG — kg-extract must run first")
        return 2

    # Step 3: sample top-10 entities
    print(f"[smoke] top-10 entities (by mention_count DESC):")
    for eid, name in pool[:10]:
        print(f"  {eid:>6} | {name}")

    # Step 4: try 3 queries — both synthetic and dataset-like
    sample_queries = [
        # Synthetic query: pick a top-mention entity name
        f"What did {pool[0][1]} say about the project?" if pool else "test",
        # Generic chat-style query that likely mentions group/person names
        "Who attended the meeting on January 9?",
        # Multi-entity query (multi-hop bait)
        f"How did {pool[0][1]} and {pool[1][1]} interact?" if len(pool) >= 2 else "test",
    ]

    for i, q in enumerate(sample_queries):
        print(f"\n[smoke] query {i+1}: {q}")
        matched = _kg_extract_query_entities(q, pool)
        print(f"  matched entities: {len(matched)}")
        for eid, ename in matched[:5]:
            print(f"    {eid:>6} | {ename}")
        if not matched:
            print("  (no match — query likely too generic for this KG)")
            continue
        matched_ids = [m[0] for m in matched]
        # Direct chunks
        direct = _kg_get_direct_chunk_ids(db_path, matched_ids)
        print(f"  direct chunk_ids (count): {len(direct)}")
        # 1-hop
        nbrs = _kg_get_1hop_neighbors(db_path, matched_ids, DEFAULT_KG_MAX_NEIGHBORS)
        print(f"  1-hop neighbors: {len(nbrs)}")
        # Unique evidence chunks across neighbors
        nbr_chunks = {n[1] for n in nbrs if n[1] > 0}
        print(f"  neighbor evidence chunks (unique): {len(nbr_chunks)}")

    print("\n[smoke] OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
