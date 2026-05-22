# RFC #0001 — Template (for proposing features)

This thread defines the RFC (Request for Comments) format for nox-mem feature proposals. Use it as a reference when opening your own RFC thread.

**To propose a feature:** open a new Discussion under "Ideas", title it `RFC #NNNN — Your feature name`, and fill in the sections below.

This thread itself is not a real RFC — it's the template definition. Discussion here is about the process, not a specific feature.

---

## RFC template

```
## Background / motivation

Why does this need to exist? What pain does it solve?
Link to relevant issues, discussions, or external references.

## Proposed solution

Describe the change concretely. If it's a new API, show the interface.
If it touches search ranking, describe the expected nDCG/MRR impact direction.

## Alternative solutions considered

At least two alternatives, and why you ruled them out.
"Do nothing" is always a valid alternative — why isn't it sufficient?

## Implementation cost

Rough estimate in person-weeks. Break it down:
- Schema changes (migrations, backward compat)
- Core logic
- Tests
- Docs

## Reversibility

How hard is it to back this out after shipping?
- Easy: config flag, feature can be disabled without schema migration
- Medium: schema additive-only, old clients still work
- Hard: schema destructive change or API break

## Performance impact

Will this make search slower? By how much (estimate)?
If you're adding a new ranking signal, what's the latency cost?
Anything touching the hot path (hybrid search, RRF) needs a benchmark estimate.

## Open questions

List what you don't know yet and would like input on.
```

---

## Worked example: RFC #0002 — Add Ollama provider for local embedding

To show the template in use, here's a hypothetical RFC filled in.

**Background / motivation**

Gemini embeddings require an API key and internet access. Users who want fully air-gapped operation (regulated environments, offline edge devices) cannot use the current default. Ollama can serve `nomic-embed-text` locally with no API key. This would fulfill the Autonomy pillar promise of "zero vendor lock-in."

**Proposed solution**

Add an `OllamaEmbeddingProvider` class implementing the `EmbeddingProvider` interface in `src/lib/embedding-provider.ts`. Configure via `NOX_EMBEDDING_PROVIDER=ollama` + `NOX_OLLAMA_URL=http://localhost:11434`. Dimensionality from `nomic-embed-text` is 768d vs Gemini's 3072d — existing `vec_chunks` tables would need migration or a separate index.

**Alternative solutions considered**

1. OpenAI `text-embedding-3-small` (1536d) — also vendor-dependent, doesn't solve air-gap use case.
2. Sentence-transformers via Python sidecar — adds Python runtime dependency, complicates deployment.

**Implementation cost**

- Provider interface: 2d
- Ollama adapter: 3d
- Migration for 768d index: 3d (tricky — existing vec_chunks are 3072d)
- Tests + docs: 3d
- Total: ~2 weeks

**Reversibility**

Medium. Schema additive if we keep a separate vec_chunks_768 table. But dual-index adds complexity.

**Performance impact**

nomic-embed-text is ~5× faster than Gemini API round-trip (no network). Quality delta unknown — ablation needed before shipping. Expect nDCG regression vs Gemini baseline; magnitude TBD.

**Open questions**

- Accept quality regression for air-gap use case? Or only ship if within 5% of Gemini baseline?
- Should dimensionality be a runtime config (risking silent mismatch) or a compile-time constant?

---

That's the format. Open a new thread to propose a real feature.
