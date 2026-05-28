"""Phase G preflight — verify cross-encoder rerank actually fires.

Phase F lesson cravada: env var presence != reranker firing. The `.env`
NOX_RERANKER_MODEL=Xenova/bge-reranker-base override silently sent all
626 rerank attempts down the fallback path, then a $0.75 batch ran on
unranked results. This script catches that failure mode BEFORE the batch.

Run from the harness root (must have eval/src/adapters/nox_mem_adapter.py
installed). Env vars must be set by the caller:

  NOX_API_BASE        — e.g. http://127.0.0.1:18815
  NOX_ADAPTER_MODE    — must be "phaseF"
  NOX_RERANKER_ENABLED=1
  NOX_RERANKER_MODEL  — must be a sentence-transformers-loadable model id
  NOX_RERANKER_OVERFETCH=50

Expected output for each of 3 queries:
  rerank_applied=True
  rerank_error=None
  rerank_ms > 0

Exit non-zero on any rerank failure so caller (run-batch-phaseG.sh) aborts
before spending money on the answer + judge stages.
"""
import asyncio
import sys

sys.path.insert(0, ".")
from eval.src.adapters.nox_mem_adapter import NoxMemAdapter


async def main() -> int:
    a = NoxMemAdapter({}, None)
    print(f"reranker_enabled={a.reranker_enabled}")
    print(f"reranker_model={a.reranker_model_id}")
    print(f"reranker_overfetch={a.reranker_overfetch}")

    if not a.reranker_enabled:
        print("FAIL: reranker_enabled is False — env not set correctly")
        return 2

    queries = [
        "who likes coffee",
        "who works on the project plan",
        "what did Alice say about lunch",
    ]
    any_failed = False
    for i, q in enumerate(queries, 1):
        r = await a.search(q, f"preflight{i}", top_k=10)
        m = r.metadata
        print(f"=== Query {i}: {q!r} ===")
        print(f"  api_returned={m.get('api_returned')} returned={m.get('returned')}")
        print(f"  rerank_applied={m.get('rerank_applied')}")
        print(f"  rerank_ms={m.get('rerank_ms')}")
        print(f"  rerank_error={m.get('rerank_error')}")
        if r.retrieved_memories:
            print(f"  top1_preview={r.retrieved_memories[0][:120]!r}")
        if not m.get("rerank_applied"):
            any_failed = True
            print(f"  FAIL: rerank did NOT fire on query {i}")

    await a.close()
    if any_failed:
        print("PREFLIGHT FAILED — aborting before paid stages")
        return 3
    print("PREFLIGHT OK — rerank fires on all sample queries")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
