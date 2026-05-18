#!/usr/bin/env python3
"""
python-quickstart.py

Same flow as typescript-quickstart.ts — answer + export + SSE stream.
Prerequisites: Python 3.11+, pip install nox-mem-client

Run: python sdk/examples/python-quickstart.py
"""

import asyncio
import os

from nox_mem_client import NoxMemClient, NoxMemApiError, ExportRequest


async def main() -> None:
    async with NoxMemClient(
        base_url=os.environ.get("NOX_API_URL", "http://127.0.0.1:18802"),
        auth_token=os.environ.get("NOX_API_TOKEN"),
    ) as client:

        # 1. Health check
        health = await client.health()
        total = health.chunks.total if health.chunks else 0
        db_mb = health.db_size_mb or 0
        print(f"Chunks: {total}, DB: {db_mb} MB")

        # 2. Hybrid search
        results = await client.search("Gemini quota exceeded cron", limit=3)
        for r in results:
            score = f"{r.score:.3f}" if r.score else "?"
            content = (r.content or "")[:80]
            print(f"  [{score}] {content}...")

        # 3. Answer with citations (requires NOX_ANSWER_ENABLED=1)
        try:
            ans = await client.answer(
                "What is the correct way to reapply the monkey-patch after upgrading OpenClaw?",
                top_k=8,
            )
            print(f"\nAnswer: {ans.answer[:200]}")
            print(f"Citations: {len(ans.citations)}")
        except NoxMemApiError as e:
            if e.is_feature_disabled:
                print("Answer feature not enabled (NOX_ANSWER_ENABLED=1 required)")
            else:
                raise

        # 4. Export archive (requires NOX_ARCHIVE_ENABLED=1)
        try:
            archive_bytes = await client.export(ExportRequest(
                format="tar",  # type: ignore[arg-type]
                exclude_embeddings=True,
            ))
            with open("/tmp/nox-mem-export.tar.gz", "wb") as f:
                f.write(archive_bytes)
            print("Exported archive to /tmp/nox-mem-export.tar.gz")
        except NoxMemApiError as e:
            if e.is_feature_disabled:
                print("Archive feature not enabled (NOX_ARCHIVE_ENABLED=1 required)")
            else:
                raise

        # 5. SSE viewer stream — collect up to 5 events then stop
        try:
            count = 0
            print("Listening to SSE stream (first 5 events)...")
            async for event in client.stream_events():
                print(f"  SSE: {event.kind.value} @ {event.ts}")
                count += 1
                if count >= 5:
                    break
        except NoxMemApiError as e:
            if e.is_feature_disabled:
                print("Viewer feature not enabled (NOX_VIEWER_ENABLED=1 required)")
            else:
                raise


if __name__ == "__main__":
    asyncio.run(main())
