#!/usr/bin/env python3
"""Full integration smoke: api-server + adapter.search() with KG boost active.

Spawns api-server, waits for boot, runs 3 sample queries through the actual
NoxMemAdapter.search() pipeline, prints metadata (kg_meta) confirming KG
boost path fires.

Usage:
    source /root/.openclaw/.env
    export NOX_DB_PATH=/root/.openclaw/phaseKG-smoke-<ts>/nox-mem.db
    export NOX_API_PORT=18829
    export NOX_API_BASE=http://127.0.0.1:18829
    export NOX_ADAPTER_MODE=phaseKG
    export NOX_KG_PATH_ENABLED=1
    python3 eval/evermembench/smoke-phaseKG-full.py
"""
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

    # 1) Spawn api-server
    api_proc = subprocess.Popen(
        ["node", "--no-warnings", "dist/api-server.js"],
        cwd="/root/.openclaw/workspace/tools/nox-mem",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env={**os.environ},
    )
    print(f"[full-smoke] api-server pid={api_proc.pid}, waiting 6s for boot...")

    try:
        time.sleep(6)
        # Quick health check
        import urllib.request
        try:
            with urllib.request.urlopen(f"{api_base}/api/health", timeout=10) as r:
                health = json.loads(r.read().decode())
            chunks = health.get("chunks", {})
            total = chunks.get("total") if isinstance(chunks, dict) else chunks
            print(f"[full-smoke] api health: chunks={total}")
        except Exception as exc:
            print(f"[full-smoke] api health FAIL: {exc}")
            return 2

        # 2) Build adapter
        from adapter_nox_mem import NoxMemAdapter
        cfg = {
            "api_base": api_base,
            "nox_mem_bin": os.environ.get("NOX_MEM_BIN", "nox-mem"),
            "search_top_k": 20,
            "search_timeout": 30,
            "ingest_batch_size": 50,
            "ingest_delay_ms": 0,
            "adapter_mode": "phaseKG",
            "phaseb_context_window": 2,
        }
        adapter = NoxMemAdapter(cfg, output_dir=None)
        info = adapter.get_system_info()
        print(f"[full-smoke] adapter version: {info.get('version')}")
        print(f"[full-smoke] kg_enabled: {info.get('kg_enabled')}")
        print(f"[full-smoke] kg_boost_magnitude: {info.get('kg_boost_magnitude')}")

        # 3) Run 3 queries
        queries = [
            "What did Weihua Zhang say?",
            "How did Mingzhi Li and Weihua Zhang collaborate?",
            "Random topic XYZ123 unlikely entity",
        ]
        for i, q in enumerate(queries):
            print(f"\n[full-smoke] query {i+1}: {q}")
            res = await adapter.search(q, user_id="smoke", top_k=10)
            meta = res.metadata or {}
            print(f"  returned: {meta.get('returned')} / api_returned: {meta.get('api_returned')}")
            print(f"  kg_enabled: {meta.get('kg_enabled')} kg_applied: {meta.get('kg_applied')}")
            print(f"  kg_ms: {meta.get('kg_ms')}")
            print(f"  kg_error: {meta.get('kg_error')}")
            print(f"  kg_meta: {json.dumps(meta.get('kg_meta', {}), default=str)[:400]}")
            if res.retrieved_memories:
                first = res.retrieved_memories[0][:80].replace('\n', ' ')
                print(f"  first hit: {first}")
        await adapter.close()
        print("\n[full-smoke] OK")
        return 0
    finally:
        api_proc.terminate()
        try:
            api_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            api_proc.kill()


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
