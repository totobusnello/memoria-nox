# ADR-008: Provider abstraction over vendor lock-in

Date: 2026-05-17

## Status

Accepted

## Context

nox-mem's embedding layer currently has a hard dependency on Gemini (`gemini-embedding-001`, 3072d). This dependency is wired directly into the ingest pipeline, vectorize CLI command, and search path. Switching providers requires changing multiple call sites, re-embedding the entire corpus (~62K chunks), and potentially migrating the `vec_chunks` schema.

Three forces push toward abstraction:

1. **Data autonomy moat (ADR-005)**: if nox-mem's primary differentiator is "your data, your choice," that claim is undermined if the user is implicitly locked to Gemini for embeddings. Provider portability is a necessary condition for the autonomy story to be credible.

2. **Vendor risk**: the 2026-04-20 incident showed that Gemini quota exhaustion (3M/d) can silently degrade the system. A provider abstraction with fallback chain mitigates this.

3. **Commercial deployment (NOX-Supermem)**: enterprise customers may have data residency requirements that preclude Gemini. A local-embedding option (via Voyage, local ONNX, etc.) is needed without a full rewrite.

Empirical embedding quality benchmark (D28, 2026-05-04):
- `gemini-embedding-001` (hybrid): nDCG@10 = 0.5213
- `multilingual-e5-base` (dense baseline): nDCG@10 = 0.3070

Gemini retains a 1.7× quality advantage. The abstraction must not compromise the default quality — Gemini stays as the canonical default.

## Decision

**A3 provider abstraction** introduces a pluggable embedding provider interface that decouples the embedding call site from the specific provider SDK:

```
EmbeddingProvider interface:
  embed(texts: string[]): Promise<Float32Array[]>
  dimensions: number
  model: string
  provider: 'gemini' | 'openai' | 'anthropic' | 'voyage' | 'local'
```

Key design decisions:

1. **Gemini remains default** (`gemini-embedding-001`, 3072d) for quality. The abstraction makes switching possible, not mandatory.

2. **Provider is declared in config** (`nox-mem.config.json` or env `NOX_EMBEDDING_PROVIDER`), not hardcoded. Switching providers requires re-embedding existing chunks (offline migration, not live swap).

3. **Dimension mismatch protection**: `vec_chunks` schema stores dimension count. On startup, the system validates that the configured provider's dimensions match the stored dimensions. Mismatch aborts with a clear error (not silent corruption).

4. **Fallback chain** (optional): if primary provider fails (quota, network), fall back to secondary provider. Fallback is declared explicitly in config; no silent fallback to lower-quality model.

5. **Local provider option**: for air-gapped or privacy-sensitive deployments, a local ONNX/llama.cpp provider can be registered. Performance SLA relaxed for local (no VPS RAM constraint applies for user-owned hardware).

6. **A4 zero-vendor validation** uses the provider abstraction to confirm the memory store is readable/searchable without any vendor API key (using cached embeddings only, no new embed calls).

## Consequences

- **Positive:** Data autonomy claim is now technically credible — users can re-embed their entire corpus with a different provider in a single migration command.
- **Positive:** Gemini SPOF risk is mitigated. If quota is exhausted, a pre-configured secondary provider activates rather than silently degrading.
- **Positive:** Commercial deployment (NOX-Supermem) can offer provider selection as a paid tier differentiator.
- **Negative:** Provider abstraction adds a layer of indirection to every embed call. Negligible runtime overhead (<1ms) but increases codebase complexity.
- **Negative:** Re-embedding 62K+ chunks when switching providers takes hours (estimated 8h for `multilingual-e5-base` on CPU, ~30min for Gemini API with batching). This is a one-time migration cost, not ongoing.
- **Negative:** Maintaining provider adapters for 4+ providers requires ongoing maintenance as provider APIs evolve.
- **Risks:** If Gemini changes its embedding API (model rename, dimension change), the abstraction layer is the only place that needs updating — but the dimension mismatch protection must be robust enough to catch silent model swaps.

## Alternatives considered

- **Keep Gemini hardcoded, add fallback only** — rejected: doesn't satisfy the autonomy moat requirement; fallback to another provider is only useful if that provider's embeddings are compatible (same dimensions, similar quality). True portability requires the full abstraction.
- **Replace Gemini with self-hosted model** — rejected: multilingual-e5-base CPU throughput = 0.3 chunks/s → 55h for 62K chunks. Inviável on current VPS hardware. GPU cloud option deferred (D23). Gemini API quality × cost is optimal for current scale.
- **Vector database with built-in provider abstraction (Weaviate, Qdrant)** — rejected: adds a separate service/daemon; SQLite-first architecture is non-negotiable for the autonomy moat (single portable file).
- **Provider abstraction via external library (LangChain embeddings, LlamaIndex)** — rejected: adds a heavy dependency, imports LangChain's architectural opinions, and ties nox-mem's abstractions to a third-party release cadence. Thin internal interface is sufficient.

## Related

- Supersedes: none
- References:
  - `docs/DECISIONS.md` D28 (multilingual-e5-base baseline; Gemini stays canonical)
  - `docs/DECISIONS.md` D40 (Q/A/P pivot; A3 is Autonomy pillar item)
  - `docs/DECISIONS.md` §3.Models & Costs item 18 (Gemini default = flash-lite)
  - ADR-004 (Q/A/P pillars — A3 is the provider abstraction sprint)
  - ADR-005 (data autonomy moat — provider portability is part of the autonomy story)
  - `specs/` A3 provider abstraction spec (in progress as of 2026-05-18)
  - `feedback_model_selection_for_agent_infra.md`
