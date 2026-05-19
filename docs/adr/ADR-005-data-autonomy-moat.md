# ADR-005: Data autonomy as primary competitive moat

Date: 2026-05-17

## Status

Accepted

## Context

The AI memory tooling market has two dominant patterns as of 2026:

1. **SaaS backend pattern** (memanto/Moorcheh): user memories are stored in a vendor-controlled cloud backend. High UX polish, but data portability is vendor-dependent. Users cannot self-host, cannot inspect the raw store, cannot switch providers without losing memory history.

2. **Runtime lock-in pattern** (agentmemory/iii-engine): open-source surface but requires a proprietary runtime daemon (`iii-engine`) to operate. Memory is technically on-device but functionally coupled to the daemon's API. Switching requires re-ingestion and re-embedding with a different runtime.

nox-mem's current architecture already embodies a third pattern that neither competitor replicates: a portable SQLite file (`nox-mem.db`) that:
- Is readable by any SQLite client without proprietary software
- Can be moved between machines via `cp`
- Contains all embeddings, full-text index, knowledge graph, and audit trail in a single file
- Has no dependency on a vendor-controlled API for basic read access

This architectural property was not previously named as a moat. It emerged from pragmatic engineering choices (SQLite for simplicity, Gemini for embedding quality). The competitor analysis of 2026-05-17 revealed it as a genuine defensible differentiator.

## Decision

**Data autonomy is the primary competitive positioning for nox-mem.** Every product decision is evaluated against the question: "Does this preserve or erode the user's ownership of their memory data?"

Specific architectural commitments that operationalize this:

1. **SQLite-first storage**: the canonical memory store is a single portable `.db` file. No separate vector store, no graph database, no cloud-synced state required for core functionality.

2. **Export/import as first-class feature (A2)**: full round-trip export to open formats (SQLite snapshot, JSONL, Markdown) with import that restores embeddings, FTS index, and KG. Not a backup feature — a portability feature.

3. **Provider abstraction (A3)**: embedding provider (Gemini, OpenAI, Anthropic, Voyage, local) is swappable via config. Gemini remains the default for quality, but the user is never locked in. Re-embedding from a different provider is a supported operation.

4. **Zero-vendor validation (A4)**: automated checks that confirm the memory store is readable and functional without any vendor API key. Smoke tests run against the raw SQLite file.

5. **No proprietary daemon**: nox-mem runs as a standard Node.js process. No persistent daemon required for core read/search operations (HTTP API is optional).

The tagline *"Pain-weighted hybrid memory with shadow discipline — yours by design."* encodes this positioning: "yours by design" refers specifically to data ownership, not just UX customization.

## Consequences

- **Positive:** Defensible differentiation against both SaaS competitors (memanto) and runtime-lock competitors (agentmemory). Autonomy moat cannot be replicated by either without a full architectural rewrite.
- **Positive:** Appeals directly to the technical user segment that distrusts SaaS memory storage (privacy-conscious, self-hosting enthusiasts, enterprise with data residency requirements).
- **Positive:** A2 export/import and A3 provider abstraction are natural marketing assets ("take your memories anywhere, switch providers in one command").
- **Negative:** SQLite-first architecture has scaling limits (~500K entities threshold per DECISIONS.md §1 items 9-10). At that scale, the autonomy story becomes harder to maintain with a single file.
- **Negative:** Provider abstraction (A3) adds implementation overhead: every embedding operation must go through the abstraction layer; re-embedding 62K+ chunks when switching providers takes hours.
- **Risks:** If users don't perceive data autonomy as a meaningful benefit (they trust SaaS providers), the moat doesn't convert to adoption. Explicit trigger: if Q4 gate closes and user perception surveys show <30% citing data ownership as a reason to choose nox-mem, reassess.

## Alternatives considered

- **SaaS pivot** — rejected: directly destroys the moat; operationally expensive; contradicts the core user value proposition; see ADR-004.
- **Federated storage (SQLite + optional cloud sync)** — deferred: technically interesting but adds complexity. Could be revisited as an A2 extension (sync is opt-in, local-first remains default).
- **Lean into benchmark leadership as primary moat (Quality-first)** — rejected as sole moat: quality metrics (nDCG) are replicable by well-funded competitors; autonomy is architectural and harder to copy. Quality is a pillar (Q), not the primary moat.
- **Open-source mindshare as moat (agentmemory-style viral)** — rejected as primary strategy: viral requires breadth (12 IDEs) which dilutes depth; autonomy narrative is more defensible long-term for the target segment.

## Related

- Supersedes: none
- References:
  - `docs/DECISIONS.md` D40 (Q/A/P pivot, competitor analysis)
  - `docs/DECISIONS.md` D26 (MIT license — maximizes adoption, compatible with autonomy positioning)
  - ADR-004 (Q/A/P pillars — establishes A pillar context)
  - ADR-008 (provider abstraction — technical implementation of autonomy)
  - `docs/ROADMAP.md` §A-pillar (A1–A4)
  - `memory/qap-pillars-strategic-decision.md`
