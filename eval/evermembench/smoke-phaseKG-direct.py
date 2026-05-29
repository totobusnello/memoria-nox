#!/usr/bin/env python3
"""Direct integration smoke — bypass SearchResult dataclass, call internals only."""
import asyncio
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


async def _main():
    db = os.environ.get("NOX_DB_PATH", "")
    port = os.environ.get("NOX_API_PORT", "18829")
    api_base = os.environ.get("NOX_API_BASE", f"http://127.0.0.1:{port}")
    assert db, "NOX_DB_PATH required"

    api_proc = subprocess.Popen(
        ["node", "--no-warnings", "dist/api-server.js"],
        cwd="/root/.openclaw/workspace/tools/nox-mem",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env={**os.environ},
    )
    print(f"[direct-smoke] api-server pid={api_proc.pid}, waiting 6s...")
    try:
        time.sleep(6)
        import urllib.request
        with urllib.request.urlopen(f"{api_base}/api/health", timeout=10) as r:
            health = json.loads(r.read().decode())
        chunks = health.get("chunks", {})
        total = chunks.get("total") if isinstance(chunks, dict) else chunks
        print(f"[direct-smoke] api health: chunks={total}")

        # Manual call to api/search + apply KG boost
        from adapter_nox_mem import (
            _kg_load_entity_names,
            _kg_extract_query_entities,
            _kg_get_1hop_neighbors,
            _kg_get_direct_chunk_ids,
            DEFAULT_KG_MIN_NAME_LEN,
            DEFAULT_KG_MAX_NEIGHBORS,
            DEFAULT_KG_BOOST_MAGNITUDE,
            DEFAULT_KG_DIRECT_MULTIPLIER,
        )

        pool, err = _kg_load_entity_names(db, DEFAULT_KG_MIN_NAME_LEN)
        assert not err, err
        print(f"[direct-smoke] entity_pool size: {len(pool)}")

        queries = [
            "What did Weihua Zhang say?",
            "How did Mingzhi Li and Weihua Zhang collaborate?",
            "Random topic XYZ123 unlikely entity",
        ]
        import aiohttp
        session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        try:
            for i, q in enumerate(queries):
                print(f"\n[direct-smoke] query {i+1}: {q}")
                async with session.post(
                    f"{api_base}/api/search",
                    json={"query": q, "limit": 50, "hybrid": True},
                ) as resp:
                    data = await resp.json()
                if isinstance(data, dict):
                    raw = data.get("results", [])
                else:
                    raw = data
                print(f"  api returned: {len(raw)}")
                # First few hit IDs
                first_ids = [it.get("id") for it in raw[:5] if isinstance(it, dict)]
                print(f"  first 5 ids (pre-boost): {first_ids}")

                matched = _kg_extract_query_entities(q, pool)
                print(f"  matched entities: {len(matched)} | sample: {matched[:3]}")
                if not matched:
                    continue
                matched_ids = [m[0] for m in matched]
                direct = _kg_get_direct_chunk_ids(db, matched_ids)
                nbrs = _kg_get_1hop_neighbors(db, matched_ids, DEFAULT_KG_MAX_NEIGHBORS)
                nbr_chunks = {n[1] for n in nbrs if n[1] > 0}
                print(f"  direct chunks: {len(direct)}")
                print(f"  1-hop neighbors: {len(nbrs)}  (unique evidence chunks: {len(nbr_chunks)})")

                # Count overlap with API results
                api_ids = {int(it.get("id", 0)) for it in raw if isinstance(it, dict)}
                direct_overlap = direct & api_ids
                nbr_overlap = nbr_chunks & api_ids
                print(f"  overlap direct ∩ api: {len(direct_overlap)}")
                print(f"  overlap neighbor_chunks ∩ api: {len(nbr_overlap)}")
                print(f"  candidate chunks affected by boost: "
                      f"{len(direct_overlap | nbr_overlap)} / {len(api_ids)}")
        finally:
            await session.close()
        print("\n[direct-smoke] OK")
        return 0
    finally:
        api_proc.terminate()
        try:
            api_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            api_proc.kill()


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
