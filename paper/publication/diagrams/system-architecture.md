# NOX-Supermem — System Architecture (Paper Figures)

Source-of-truth for figures referenced in `paper/publication/04-paper-arxiv-draft.md` §3 and `05-blog-post-draft.md`. All four diagrams are renderable standalone in mermaid.live.

Color convention (high-contrast, accessible):
- **Indigo `#4F46E5`** — agents / consumers
- **Slate `#475569`** — neutral infrastructure (interfaces, storage)
- **Amber `#D97706`** — *pain* dimension (contribution #1)
- **Emerald `#059669`** — *shadow-mode* discipline (contribution #2)
- **Rose `#E11D48`** — *shared canonical* corpus (contribution #3)
- White text on dark fills throughout (WCAG AA).

---

## Figure 1 — System Overview (HERO)

```mermaid
%%{init: {'theme':'base','themeVariables':{'fontSize':'14px','fontFamily':'Inter, system-ui'}}}%%
flowchart TB
    subgraph AGENTS["6 Agents — shared canonical corpus"]
        direction LR
        A1[Atlas]
        A2[Boris]
        A3[Cipher]
        A4[Forge]
        A5[Lex]
        A6[Nox]
    end

    subgraph IFACE["Interface Layer"]
        direction LR
        CLI["CLI<br/>26+ commands"]
        MCP["MCP Server<br/>16 tools"]
        API["HTTP API<br/>:18802"]
    end

    subgraph SEARCH["Hybrid Search Engine — 3-layer fusion"]
        direction TB
        L1["L1: FTS5 BM25<br/>lexical recall"]
        L2["L2: Gemini semantic<br/>3072-d cosine"]
        L3["L3: RRF fusion<br/>k=60"]
        L1 --> L3
        L2 --> L3
    end

    subgraph STORE["Canonical Storage — single SQLite DB"]
        direction LR
        CH["chunks + chunks_fts<br/>~64k rows"]
        VEC["vec_chunks<br/>3072-d Gemini"]
        KG["kg_entities (402)<br/>kg_relations (544)"]
    end

    subgraph CROSS["Cross-cutting Discipline"]
        direction LR
        SHADOW["Shadow-mode pipeline<br/>≥7d before activate"]
        AUDIT["ops_audit (append-only)<br/>+ withOpAudit() snapshot"]
    end

    AGENTS -->|read/write| IFACE
    IFACE --> SEARCH
    SEARCH --> STORE
    STORE -. governs .- CROSS
    SEARCH -. governs .- CROSS

    classDef agent fill:#4F46E5,stroke:#312E81,color:#fff
    classDef iface fill:#475569,stroke:#1E293B,color:#fff
    classDef search fill:#475569,stroke:#1E293B,color:#fff
    classDef store fill:#E11D48,stroke:#881337,color:#fff
    classDef cross fill:#059669,stroke:#064E3B,color:#fff

    class A1,A2,A3,A4,A5,A6 agent
    class CLI,MCP,API iface
    class L1,L2,L3 search
    class CH,VEC,KG store
    class SHADOW,AUDIT cross
```

**[Figure 1: System overview.]** Six personas read and write through a unified interface layer (CLI / MCP / HTTP) into a single canonical SQLite corpus (rose) — no per-agent silos. Retrieval runs as a three-layer hybrid (BM25 → 3072-d Gemini cosine → RRF, k=60). The shadow-mode pipeline and append-only `ops_audit` (emerald) are cross-cutting governance: every ranking change ships shadow first; every destructive op is wrapped by `withOpAudit()` snapshot.

---

## Figure 2 — Salience Pipeline (pain dimension highlighted)

```mermaid
%%{init: {'theme':'base','themeVariables':{'fontSize':'14px','fontFamily':'Inter, system-ui'}}}%%
flowchart LR
    INGEST["File ingest<br/>(watcher / CLI / MCP)"]
    ROUTER["ingest-router<br/>entity / md / graph"]
    ANNOT["Annotate<br/>retention_days · section · pain"]
    COMPUTE["Compute salience<br/>recency × pain × importance"]
    SHADOW["Shadow-mode<br/>NOX_SALIENCE_MODE=shadow<br/>≥7 days telemetry"]
    GATE{{"Activate gate<br/>distribution + nDCG OK?"}}
    APPLIED["Applied to ranking<br/>RRF post-fusion boost"]

    INGEST --> ROUTER --> ANNOT --> COMPUTE --> SHADOW --> GATE
    GATE -- yes --> APPLIED
    GATE -- no --> SHADOW

    classDef base fill:#475569,stroke:#1E293B,color:#fff
    classDef pain fill:#D97706,stroke:#92400E,color:#fff
    classDef shadow fill:#059669,stroke:#064E3B,color:#fff
    classDef gate fill:#0F172A,stroke:#000,color:#fff

    class INGEST,ROUTER,APPLIED base
    class ANNOT,COMPUTE pain
    class SHADOW shadow
    class GATE gate
```

**[Figure 2: Salience pipeline.]** Each chunk is annotated at ingest with three signals — `retention_days` (typed lifetime), `section` (compiled / frontmatter / timeline), and **pain** (0.1 trivial → 1.0 prod-outage, amber). Salience = `recency × pain × importance` is computed and exposed via `/api/health.salience` for at least seven days before any activation. The activate gate inspects distribution shape and nDCG@10 deltas; failure loops back to shadow. Pain is the novel axis — recency and importance are common in prior work; a domain-validated severity multiplier is the contribution.

---

## Figure 3 — Shadow Discipline State Machine

```mermaid
%%{init: {'theme':'base','themeVariables':{'fontSize':'14px','fontFamily':'Inter, system-ui'}}}%%
stateDiagram-v2
    direction LR
    [*] --> Implement
    Implement --> Shadow: deploy with NOX_*_MODE=shadow
    Shadow --> Shadow: cron health check<br/>(every 15 min)
    Shadow --> ActivateEligible: ≥7 days wall-clock<br/>+ telemetry > N events
    ActivateEligible --> Shadow: distribution skew<br/>or nDCG regression
    ActivateEligible --> Activate: distribution OK<br/>+ manual approve
    Activate --> Rollback: post-activate regression
    Rollback --> Shadow: revert env-var
    Activate --> [*]

    note right of Shadow
        Telemetry: /api/health.<feature>
        Audit log: ops_audit
        Examples: salience, section_boost,
        focus_boost, edge_typing
    end note

    note right of Activate
        Env-var flip only —
        zero schema change
    end note
```

**[Figure 3: Shadow discipline.]** Every ranking-affecting change traverses this machine. Activation requires three independent signals: at least seven days of shadow telemetry, a healthy distribution (no degenerate clustering), and explicit human approve. Regression at any point reverts via a single environment-variable flip — zero schema rollback ever required. Validated end-to-end on Phase 1.7b-b salience, G02 section_boost (1,578 events analysed), E03a SPO injection, E04a focus boost, and E05 edge typing.

---

## Figure 4 — KG Edge Typing Flow (closed-enum + defensive normalize)

```mermaid
%%{init: {'theme':'base','themeVariables':{'fontSize':'14px','fontFamily':'Inter, system-ui'}}}%%
flowchart TB
    SRC["Source chunks<br/>~64k corpus"]
    EXTRACT["Gemini 2.5-flash extraction<br/>SPO triples"]
    LLM_OUT["LLM output<br/>relation_type free-text"]

    subgraph NORMALIZE["Defensive normalize — 3 paths"]
        direction TB
        P1["Path 1<br/>direct enum match<br/>(7 canonical values)"]
        P2["Path 2<br/>RELATION_TYPE_TO_REASON map<br/>(24 PT-BR + EN inputs)"]
        P3["Path 3<br/>fallback → unknown"]
    end

    ENUM["relation_reason ∈ enum-7<br/>depends_on · derived_from · opposes ·<br/>extends · replaces · mentions · unknown"]
    PERSIST["kg_relations<br/>(schema v12 CHECK constraint)"]

    BEFORE["Before B1+B2+B3<br/>14% classified · 86% unknown"]
    AFTER["After fix<br/>56% classified · 4× improvement<br/>(n=100, 2026-05-03)"]

    SRC --> EXTRACT --> LLM_OUT --> NORMALIZE
    NORMALIZE --> ENUM --> PERSIST
    PERSIST -. measured .- BEFORE
    PERSIST -. measured .- AFTER

    classDef base fill:#475569,stroke:#1E293B,color:#fff
    classDef enum fill:#4F46E5,stroke:#312E81,color:#fff
    classDef bad fill:#7F1D1D,stroke:#450A0A,color:#fff
    classDef good fill:#059669,stroke:#064E3B,color:#fff

    class SRC,EXTRACT,LLM_OUT,P1,P2,P3,PERSIST base
    class ENUM enum
    class BEFORE bad
    class AFTER good
```

**[Figure 4: KG edge typing flow (E05).]** Gemini emits free-text relation labels; a defensive three-path normaliser collapses them into a closed enum of seven canonical reasons enforced by a schema-v12 `CHECK` constraint. The annotated before/after captures the lesson: an LLM-optional enum field combined with the prompt clause *"use unknown if unsure"* drove 86% of relations into `unknown`. The fix — code-side defensive map (24 PT-BR + EN aliases) plus a revised prompt — lifted classification from 14% → 56% (4×) on n=100. A closed enum without a defensive normaliser is half a feature.
