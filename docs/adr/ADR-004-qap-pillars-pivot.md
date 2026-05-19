# ADR-004: Q/A/P pillars strategic pivot

Date: 2026-05-17

## Status

Accepted

## Context

As of 2026-05-17, the nox-mem roadmap was structured around a numbered list of research experiments (E01–E15) with ~80% capacity allocated to internal retrieval research (E13/E14/E15). This produced academically sound work (paper submitted to arXiv) but left the product largely invisible externally.

A strategic analysis of two direct competitors revealed a critical gap:

- **memanto** (126 GitHub stars, SaaS via Moorcheh backend, academic pitch): positioned as "AI memory layer," closed SaaS backend, pitch-deck framing. Moat: VC-backed infrastructure. Risk: user data is held by vendor.
- **rohitg00/agentmemory** (11.3k stars, `iii-engine` runtime, viral traction): similar core architecture (BM25 + vector + KG + RRF) but wins market through UX (auto-capture hooks, multi-IDE breadth, real-time viewer, strong marketing presentation). Moat: viral flywheel + mindshare. Risk: runtime lock-in via proprietary `iii-engine`.

Neither competitor delivers **data autonomy** — the user's memory is either in a SaaS backend (memanto) or depends on a proprietary runtime daemon (agentmemory). nox-mem's architecture — SQLite file portable across machines, no proprietary daemon, provider-swappable embeddings — is a genuinely defensible differentiator that neither competitor can replicate without a full rewrite.

The prior 80/20 allocation (research-heavy) was appropriate for shipping a credible paper. It is not appropriate for building a product that wins mindshare alongside that paper.

## Decision

Reorganize the roadmap into **3 product pillars + Lab + GTM Phase 2**:

- **Q (Quality):** Q1 LoCoMo benchmark, Q2 LongMemEval, Q3 Latency hardening, Q4 COMPARISON.md (public, gated on winning or tying top).
- **A (Autonomy):** A1 privacy filter, A2 export/import (portable SQLite), A3 provider abstraction, A4 zero-vendor validation.
- **P (Product):** P1 answer primitive, P2 Claude Code hooks auto-capture, P3 temporal queries, P4 connect IDE, P5 real-time viewer.
- **Lab (40% capacity):** L1 E15 paused (resumes post-Q1), L2 conflict detection (memanto-inspired), L3 confidence field (gated at ≥1.0pp lift).
- **GTM Phase 2:** viral launch playbook, locked behind Q4 gate.

**Capacity split:** 60% product pillars (Q/A/P), 40% Lab. Previously 80% Lab / 20% product.

**Tagline:** *"Pain-weighted hybrid memory with shadow discipline — yours by design."*

**Gemini embeddings remain canonical** for quality (1.7× lift over E5 baseline at 12× lower cost is wrong direction — Gemini wins on quality, A3 abstraction allows swap later).

E15 CodeGraph improvements: paused, not cut — resumes post-Q1.

## Consequences

- **Positive:** Product roadmap is now externally legible. Autonomy moat is explicitly named and defensible against both competitors. GTM assets (README, demo, visual palette) can be built around a coherent positioning.
- **Positive:** Lab remains at 40% — research quality is preserved; paper trajectory unaffected.
- **Negative:** Internal retrieval experiments (E13/E14/E15) shift to Lab priority, potentially slowing some nDCG improvements.
- **Negative:** Product pillars (P1–P5) require UX/integration work that has no prior art in this codebase; velocity estimates are uncertain.
- **Risks:** If autonomy moat doesn't materialize as a perceived differentiator within 6 months, the pivot rationale needs reassessment (explicit trigger: Q4 gate closed + user perception signal).

## Alternatives considered

- **Continue 80/20 retrieval research** — rejected: paper ships but product stays invisible; incompatible with Nox-Supermem Hotmart commercialization timeline.
- **Pivot to SaaS (memanto-style)** — rejected: destroys the autonomy moat; requires expensive backend infra; contradicts the "your data, your choice" positioning entirely.
- **Pivot to broad stack-bridge (agentmemory-style, 12 IDEs)** — rejected: shallow breadth becomes PR-spam and dilutes brand; 3 IDEs deep (Tier A premium) + passive MCP (Tier B) is more defensible.
- **Contribute nox-mem backend into agentmemory as open-source plugin** — rejected: becomes commodity layer; loses brand identity and direct user relationship.

## Related

- Supersedes: `docs/_archive/ROADMAP-v1-pre-Q-A-P-2026-05-17.md` (not as an ADR, but as the prior roadmap)
- References:
  - `docs/DECISIONS.md` D40 (2026-05-17 noite — Q/A/P strategic pivot)
  - `docs/ROADMAP.md` (v2, current)
  - `memory/qap-pillars-strategic-decision.md`
  - `memory/memanto-inspired-ideas.md`
  - `memory/benchmark-gap-longmemeval-locomo.md`
  - ADR-005 (data autonomy as primary moat — companion decision)
