# Shared loader canonical pattern — mem0 + agentmemory both use lib/corpus_loader.py

**Date:** 2026-05-24 evening
**Incident:** PR #285 (mem0 adapter corpus fix) + PR #281 (agentmemory REST adapter)
**Lesson:** Two independent Q4 ingestion adapters converged on same abstraction.

## Pattern

Both mem0 and agentmemory adapters needed a **canonical corpus loader** to:
1. Load LoCoMo baseline corpus from filesystem (standardized paths)
2. Route corpus chunks to adapter's ingest method
3. Handle graceful degradation when SDK unavailable
4. Return structured validation results (hits, latency, errors)

**Solution:** Extract shared `lib/corpus_loader.py` with signature:

```python
class CorpusLoader:
    def __init__(self, corpus_path: str, adapter: BaseAdapter):
        self.corpus_path = corpus_path
        self.adapter = adapter
    
    def load_and_ingest(self, limit: int = None) -> dict:
        """Load corpus from filesystem, ingest via adapter.
        Returns: {corpus_size, ingested, errors, latency_avg, gold_hits}
        """
        # 1. Load corpus JSON/markdown from corpus_path
        # 2. Call adapter.ingest(chunks)
        # 3. Collect latency + error telemetry
        # 4. Return structured result
```

## Why it matters

**Before (PR #269 + #281 separate):**
- mem0 adapter rolled own corpus loading logic
- agentmemory adapter rolled own corpus loading logic
- 2 independent implementations → 2 failure modes, 2 versions of "truth"
- Test fixtures hardcoded paths differently

**After (PR #285 refactor):**
- Single source of truth for corpus loading
- Adapters delegate to `CorpusLoader(corpus_path, adapter)`
- Canonical paths validated once (vs each adapter)
- Latency measurements standardized
- Gold hit collection unified

**PR #285 impact:** Unlocked mem0 gold_hits by fixing path routing in corpus_loader.py. No adapter code change needed; library fix cascaded.

## Canonical paths

```
eval/q4-comparison/
  ├── data/
  │   ├── locomo/
  │   │   └── corpus.json (baseline ~1.2k chunks)
  │   └── longmemeval/
  │       └── corpus.json (baseline ~500 chunks)
  └── adapters/
      ├── nox_mem_adapter.py
      ├── mem0_adapter.py
      ├── agentmemory_adapter.py
      └── ...
```

All adapters read corpus from `eval/q4-comparison/data/{dataset}/corpus.json` via shared loader.

## Applicability

**Reuse for:**
- Zep adapter (PR #272) — already uses corpus_loader
- Future competitor adapters (Letta, etc.)
- Eval harness expansion (additional datasets)

**Do NOT:** Embed corpus paths in adapter init. Always delegate to CorpusLoader.

## Cross-reference

- PR #285 (mem0 fix)
- PR #281 (agentmemory implementation)
- PR #270 (original loader scaffolding)
- `eval/q4-comparison/lib/corpus_loader.py` (canonical implementation)

## Lesson for future work

When 2+ independent subsystems converge on same pattern (corpus loading, adapter lifecycle, etc.):
1. Extract to shared library immediately (don't wait for 3rd instance)
2. Validate via 2 independent callers (mem0 + agentmemory both use it)
3. Document canonical paths + error handling
4. Add to "Conventions" HANDOFF section if it becomes recurring pattern

This prevents "works for A, breaks for B" surprises later.
