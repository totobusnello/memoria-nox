#!/usr/bin/env python3
"""Phase MQ smoke — verify decomposer + multi-retrieve path on 3 sample queries.

Bypasses SearchResult dataclass, calls adapter internals only.

Usage (on VPS):
    set -a; source /root/.openclaw/.env; set +a
    source /root/.openclaw/evermembench-phaseB-1779978778/venv/bin/activate
    cd /tmp/<MQ-work-dir>
    NOX_DB_PATH=/root/.openclaw/evermembench-runs/phaseH-v2-004-1780019268/nox-mem.db \
    NOX_API_PORT=18842 NOX_MQ_DEBUG=1 \
        python smoke-phaseMQ.py
"""
import asyncio
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


async def _main() -> int:
    db = os.environ.get("NOX_DB_PATH", "")
    port = os.environ.get("NOX_API_PORT", "18842")
    api_base = os.environ.get("NOX_API_BASE", f"http://127.0.0.1:{port}")
    assert db, "NOX_DB_PATH required"

    # Spawn isolated api-server
    api_proc = subprocess.Popen(
        ["node", "--no-warnings", "dist/api-server.js"],
        cwd="/root/.openclaw/workspace/tools/nox-mem",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env={**os.environ, "NOX_DB_PATH": db, "NOX_API_PORT": port},
    )
    print(f"[mq-smoke] api-server pid={api_proc.pid}, waiting 6s...")
    rc = 0
    try:
        time.sleep(6)
        import urllib.request
        try:
            with urllib.request.urlopen(f"{api_base}/api/health", timeout=10) as r:
                health = json.loads(r.read().decode())
        except Exception as exc:
            print(f"[mq-smoke] ERROR: api health failed: {exc}")
            return 1
        chunks = health.get("chunks", {})
        total = chunks.get("total") if isinstance(chunks, dict) else chunks
        print(f"[mq-smoke] api health: chunks={total}")

        from adapter_nox_mem import (  # noqa: E402
            _mq_decompose_query,
            _mq_rrf_merge,
            DEFAULT_MQ_LLM,
            DEFAULT_MQ_LLM_BASE_URL,
            DEFAULT_MQ_N,
            DEFAULT_MQ_RRF_K,
        )

        import aiohttp  # noqa: E402

        api_key = (
            os.environ.get("NOX_MQ_LLM_API_KEY")
            or os.environ.get("GEMINI_API_KEY", "")
        )
        if not api_key:
            print("[mq-smoke] ERROR: GEMINI_API_KEY missing")
            return 1
        model = os.environ.get("NOX_MQ_LLM", DEFAULT_MQ_LLM)
        base_url = os.environ.get("NOX_MQ_LLM_BASE_URL", DEFAULT_MQ_LLM_BASE_URL)

        # Three sample queries covering single-hop, multi-hop, temporal
        queries = [
            # Factual single-hop
            "What did Weihua Zhang say about the project?",
            # Multi-hop — should decompose into entity/relation/temporal sub-Qs
            "How did Mingzhi Li and Weihua Zhang collaborate after the Q4 review, "
            "and what changed in their working relationship afterward?",
            # Temporal
            "When was the last time Group 1 met to discuss budget?",
        ]

        session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        try:
            for i, q in enumerate(queries):
                print(f"\n[mq-smoke] === Query {i+1} ===")
                print(f"[mq-smoke] orig: {q}")

                # Step 1: baseline retrieval (for comparison)
                async with session.post(
                    f"{api_base}/api/search",
                    json={"query": q, "limit": 20, "hybrid": True},
                ) as resp:
                    base_data = await resp.json()
                if isinstance(base_data, dict):
                    base_raw = base_data.get("results", [])
                else:
                    base_raw = base_data
                base_ids = [it.get("id") for it in base_raw[:10] if isinstance(it, dict)]
                print(f"[mq-smoke] baseline top-10 ids: {base_ids}")

                # Step 2: decompose
                dec_start = time.monotonic()
                sub_queries, err = await _mq_decompose_query(
                    q,
                    n=DEFAULT_MQ_N,
                    model=model,
                    base_url=base_url,
                    api_key=api_key,
                    timeout_s=30.0,
                    session=session,
                )
                dec_ms = (time.monotonic() - dec_start) * 1000
                if err:
                    print(f"[mq-smoke] decompose ERROR: {err}")
                    continue
                print(f"[mq-smoke] decomposed in {dec_ms:.0f}ms -> {len(sub_queries)} sub-queries:")
                for j, sq in enumerate(sub_queries):
                    print(f"[mq-smoke]   {j+1}. {sq}")

                # Step 3: per-sub-query retrieval
                ret_start = time.monotonic()

                async def _fetch_sub(sq: str):
                    async with session.post(
                        f"{api_base}/api/search",
                        json={"query": sq, "limit": 10, "hybrid": True},
                    ) as r:
                        d = await r.json()
                    rr = d.get("results", []) if isinstance(d, dict) else d
                    out = []
                    for it in rr:
                        if isinstance(it, dict):
                            c = it.get("chunk_text") or it.get("content") or ""
                            if c:
                                out.append((c, it))
                    return out

                per_sub = await asyncio.gather(*[_fetch_sub(sq) for sq in sub_queries])
                ret_ms = (time.monotonic() - ret_start) * 1000
                total_pre_dedup = sum(len(r) for r in per_sub)

                # Step 4: RRF merge
                merged = _mq_rrf_merge(per_sub, rrf_k=DEFAULT_MQ_RRF_K)
                merged_ids = [it.get("id") for _c, it in merged[:10]]
                print(
                    f"[mq-smoke] retrieved {total_pre_dedup} pre-dedup -> "
                    f"{len(merged)} unique in {ret_ms:.0f}ms"
                )
                print(f"[mq-smoke] MQ top-10 ids: {merged_ids}")

                # Step 5: validate union expanded coverage
                base_set = set(base_ids)
                mq_set = set(merged_ids)
                added = mq_set - base_set
                preserved = mq_set & base_set
                lost = base_set - mq_set
                print(
                    f"[mq-smoke] coverage delta: +{len(added)} new, "
                    f"{len(preserved)} preserved, {len(lost)} dropped"
                )
                # Convergence: how many chunks appeared in >=2 sub-queries
                multi_hits = sum(1 for _c, it in merged if (it.get("_mq_subquery_count") or 0) >= 2)
                print(f"[mq-smoke] convergence: {multi_hits} chunks hit by ≥2 sub-queries")
        finally:
            await session.close()
        print("\n[mq-smoke] === SMOKE PASS ===")
    finally:
        api_proc.kill()
        try:
            api_proc.wait(timeout=5)
        except Exception:  # noqa: BLE001
            pass
    return rc


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
