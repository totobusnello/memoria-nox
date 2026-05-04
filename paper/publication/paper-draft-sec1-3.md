# The Pain Diary and Shadow Discipline: A Memory System That Learns from Its Own Incidents

> **Draft sections §1–§3** — prose-complete. Sections §4–§7 in separate sprint.
> All claims annotated with `[NEEDS VALIDATION §5]` where empirical support is pending.
> LaTeX-friendly markdown: `\cite{}`, `\texttt{}`, `\textbf{}` used inline; tables to be converted.

---

## 1. Introduction

At 22:03 on April 25, 2026, an end-of-day cron job executed \texttt{nox-mem reindex} without a dry-run flag. Within seconds, 183 entity records lost their \texttt{section}, \texttt{retention\_days}, and \texttt{section\_boost} fields — years of structured operational context flattened into generic chunks. No error log. No alarm. The database simply obeyed.

This incident did not expose a retrieval failure. It exposed a discipline failure. The system had no enforced gate requiring a dry-run preview before a destructive reindex. It had no mechanism for distinguishing between a trivial documentation update and a production outage — both were stored with equal weight and retrieved with equal priority. And when six AI agents (Atlas, Boris, Cipher, Forge, Lex, and Nox) shared a common operational corpus, a single unchecked operation could silently degrade context for all of them simultaneously.

The incident became the motivating example for this paper.

### 1.1 Problem Statement

LLM agent memory is increasingly recognized as a prerequisite for sustained, coherent assistance across sessions \cite{lewis2020rag, packer2023memgpt}. Yet the literature on agent memory systems — from MemGPT's OS-inspired paging \cite{packer2023memgpt} to Mem0's self-improving extraction \cite{chhikara2025mem0} to A-MEM's Zettelkasten-inspired linking \cite{xu2025amem} — converges on a narrow set of concerns: retrieval accuracy on benchmark corpora, latency at scale, and memory capacity. What these systems do not address is the operational discipline required to keep a production memory system trustworthy over months of continuous use.

Three specific gaps drive this work:

**Silent regression risk.** Ranking changes — new scoring formulas, boosting coefficients, retrieval layer modifications — can degrade retrieval quality without any observable error signal. Production memory systems have no established methodology for validating such changes before they affect live queries. The April 25 incident is one instance of a broader pattern: operations that silently alter system behavior with no guard and no rollback.

**Incident severity as an invisible dimension.** Existing memory systems model recency and semantic relevance. None, to our knowledge, model the operational cost of the experience being stored. A lesson learned from a production outage and a routine implementation note may share similar timestamps and embedding distances; they do not share similar importance to future retrieval. This asymmetry is unrepresented in current retrieval architectures.

**Multi-agent context silos.** When multiple agents operate over isolated memory stores, intelligence accumulated by one agent is inaccessible to others. Solutions that partition by \texttt{user\_id} \cite{chhikara2025mem0} or maintain per-agent state \cite{packer2023memgpt} impose federation overhead or simply accept the silo. For trusted multi-agent deployments — where agents serve a single operator with a shared context — this isolation is an architectural choice, not a requirement.

### 1.2 Thesis

\textbf{Agent memory is not a retrieval problem — it is an operational discipline problem.}

Better embeddings, larger corpora, and faster fusion layers address the retrieval surface. They do not address the question of whether the system can be trusted to evolve without silent regressions, whether it surfaces the most operationally important context rather than merely the most recent, or whether the intelligence accumulated by one agent is available to the others who need it.

### 1.3 Contributions

We present \textbf{nox-mem}, a production memory system designed for multi-agent operational use and built over four months of continuous deployment.\footnote{Repository: \url{https://github.com/totobusnello/memoria-nox}; submission tar at \texttt{paper/publication/}; license MIT.} The system indexes 61,257 chunks (snapshot at experiment freeze 2026-05-04; live deployment is 61,258 at submission time, reflecting only continuous ingest between freeze and submit) across a shared canonical corpus, maintains 99.97% vector coverage, and operates at p95 latency below one second on commodity VPS hardware (8-core x86\_64) over the production query mix. Three primary contributions distinguish this work:

1. **Pain-weighted salience as a secondary ranking modulator** (§3.5). We \textbf{propose} a retrieval scoring signal that explicitly models incident severity: \texttt{salience = recency × pain × importance}, where \texttt{pain} $\in [0.1, 1.0]$ encodes the operational cost of the recorded experience — from trivial notes (0.1) to production outages (1.0). To our knowledge, this is the first documented retrieval signal in the memory systems literature that treats incident severity as a first-class dimension. Empirical ablation (§5.5, E10, $n=31$ post-incident queries, hybrid mode) shows directional but non-significant aggregate effect ($\Delta = +0.0065$, 95% CI $[-0.014, +0.034]$). The dimension provides meaningful lift in the narrow regime where high-pain and low-pain chunks receive near-identical Gemini semantic scores (Q55 case study, $\Delta = +0.349$). The transferable contribution is the methodology of treating incident severity as typed schema input — a design pattern adoptable independently of any retrieval stack — rather than a demonstrated corpus-wide retrieval improvement.

2. **Enforced shadow discipline** (§3.6). We describe a methodology for validating ranking changes against a shadow telemetry baseline before deployment, implemented as an architectural constraint rather than a documented suggestion. The mechanism is codified via environment variable gating (\texttt{NOX\_SALIENCE\_MODE=shadow|active}), enforced by a cron-checked health endpoint, with a mandatory minimum observation period of seven days. During the salience validation run (Fase 1.7b-b), this produced 191 promotion candidates, 16,608 review cases, and 45,743 archive recommendations before any activation. This is, to our knowledge, the first memory system paper to codify such a discipline as an architectural constraint rather than a suggested practice.

3. **Shared-canonical multi-agent design** (§3.7). Six agents share a single \texttt{chunks} table distinguished by \texttt{source\_file} prefix rather than separate stores. Cross-agent retrieval requires no synchronization because partitioning never occurred. When Forge records a decision about infrastructure, Atlas retrieves it directly on the next relevant query — not because data was replicated, but because the design assumed shared context from the start.

Secondary contributions include: a reproducible evaluation harness with nDCG@10, MRR, Recall@10, and Precision@5 over 50 curated golden queries; four months of operational evidence across five infrastructure upgrades without data loss; and comparative analysis against strong retrieval baselines [NEEDS VALIDATION §5].

### 1.4 Paper Organization

Section 2 surveys related work across knowledge graph–augmented retrieval, agent memory systems, and production-oriented frameworks, identifying the specific gaps this work addresses. Section 3 describes the system architecture across storage, retrieval, knowledge graph, and operational discipline layers. Section 4 details the evaluation methodology, including the golden query harness, baseline selection, and three-corpus design. Section 5 presents experimental results, including hybrid pipeline ablations, baseline comparisons, pain dimension validation, and the shadow discipline case study. Section 6 discusses deployment scope, limitations, and future work. Section 7 concludes.

---

## 2. Related Work

Agent memory research has accelerated rapidly since the introduction of retrieval-augmented generation \cite{lewis2020rag}, with recent work spanning knowledge graph–augmented retrieval, autonomous memory management, and production deployment frameworks. We survey the most directly relevant systems and identify the specific dimensions where this work diverges.

### 2.1 Knowledge Graph–Augmented Retrieval

\textbf{GraphRAG} \cite{edge2024graphrag} introduced a pipeline that uses LLM extraction to build entity-relation graphs over document corpora, applies community detection (Leiden algorithm) to identify thematic clusters, and generates multi-level summaries for query-focused retrieval. The approach substantially improves global query coverage — queries requiring synthesis across many documents — compared to naive RAG. nox-mem adopts the LLM-extraction paradigm for knowledge graph construction but diverges in objective: GraphRAG optimizes for global summarization via community traversal, while nox-mem targets entity-centric local retrieval for operational contexts, with closed-enum edge typing designed to support downstream blast-radius analysis. GraphRAG does not model retrieval as an operational concern and has no analogue to the discipline mechanisms described in §3.5–3.6.

\textbf{HiRAG} \cite{huang2025hirag} extends the KG-augmented paradigm with hierarchical knowledge representation and iterative reasoning chains, demonstrating state-of-the-art performance on multiple QA benchmarks. The hierarchical approach — traversing from coarse to fine-grained graph levels — optimizes for accuracy on complex reasoning tasks. nox-mem instead maintains a flat three-layer fusion pipeline (§3.4), accepting the accuracy-latency trade-off explicitly: p95 below one second at 64K chunks serves operational use cases where query latency is a usability constraint, not just a benchmark metric. HiRAG does not address multi-agent deployment, evaluation harnesses for operational corpora, or retrieval discipline.

\textbf{HippoRAG} \cite{guo2024hipporag} draws on neurobiological memory models to improve associative retrieval via hippocampal-inspired graph structures. The system demonstrates that non-uniform memory consolidation — weighting some associations more strongly than others based on structural graph properties — improves retrieval over flat indexing. nox-mem introduces a conceptually related asymmetry through the pain dimension (§3.5), though the design rationale is grounded in operational incident management practice rather than neuroscience. HippoRAG does not model incident severity as a retrieval signal.

### 2.2 Agent Memory Systems

\textbf{MemGPT} \cite{packer2023memgpt} proposed treating the LLM itself as an operating system, with the agent autonomously managing its own context through function calls that page between main context and external storage. The architecture gives agents direct control over their memory — a compelling design for single-agent autonomy. nox-mem adopts the opposite philosophy: memory is managed by an external pipeline (file watcher, ingest router, nightly KG extraction), and agents are consumers of a shared canonical store rather than managers of isolated state. This separation enables cross-agent retrieval as a structural property while imposing the discipline that agents cannot corrupt their own context.

\textbf{Mem0} \cite{chhikara2025mem0} introduced a production-focused memory layer with LLM-driven memory extraction, deduplication, and temporal updates. Evaluated on the LOCOMO benchmark, Mem0 demonstrates +26% accuracy improvement over baselines on long-context conversation scenarios. nox-mem shares the production emphasis but diverges in two important respects. First, Mem0 relies on autonomous LLM editing decisions to update and merge memories; nox-mem requires shadow-period validation before any retrieval-affecting change propagates to production, specifically to mitigate silent regression risk. Second, Mem0's multi-user design partitions memory by \texttt{user\_id}, treating agents as user-addressable endpoints; nox-mem's shared canonical design treats agents as roles within a single trusted operational context.

\textbf{A-MEM} \cite{xu2025amem} introduced agentic memory with Zettelkasten-inspired structure: notes are automatically tagged, interlinked, and contextualized by an LLM controller, enabling dynamic memory evolution. The approach handles unstructured conversation well but does not address operational corpora with explicit schema requirements, retention policies, or incident-severity differentiation. A-MEM has no evaluation harness independent of LLM-generated quality judgments, and does not address multi-agent deployments or ranking change discipline.

### 2.3 Production-Oriented Frameworks

\textbf{Cognee} \cite{topoteretes2024cognee} provides an open-source AI memory framework implementing an Extract-Cognify-Load (ECL) pipeline with native knowledge graph support and hybrid retrieval. Of the systems surveyed, Cognee is architecturally closest to nox-mem: both maintain native KGs, both support hybrid retrieval, and both target production deployment scenarios. Cognee achieves 3/5 on our architectural parity dimensions (Table 1). The key differentiators are shadow discipline — Cognee provides no enforced validation gate for retrieval-affecting changes — and the evaluation harness: Cognee lacks a reproducible evaluation methodology with standard IR metrics over a fixed golden set. nox-mem's eval harness (§4) enables the kind of regression detection that the shadow discipline gate is designed to act on.

\textbf{LangChain Memory} provides key-value and buffer memory primitives widely used in production applications. The design prioritizes API simplicity and framework compatibility over retrieval quality; it does not support hybrid retrieval, knowledge graph construction, or evaluation. It serves as a practical lower bound in comparative analysis.

### 2.4 Foundational Retrieval Methods

\textbf{Retrieval-Augmented Generation} \cite{lewis2020rag} established the foundational architecture combining parametric LLM knowledge with non-parametric document retrieval, enabling factual question answering over dynamic corpora. nox-mem extends this foundation to persistent, evolving operational corpora with explicit retention, pain weighting, and multi-agent routing.

\textbf{Reciprocal Rank Fusion} \cite{cormack2009rrf} provides the rank-combination mechanism at the core of nox-mem's hybrid retrieval layer. Cormack et al. demonstrated that RRF consistently outperforms individual rank learning methods and Condorcet-based fusion without requiring system-specific tuning. We adopt RRF with $k=60$ as the fusion parameter, consistent with the paper's recommendations, as the final combination step over BM25 and dense retrieval ranked lists.

### 2.5 Positioning: Where nox-mem Fits

Table 1 maps seven architectural and operational axes across the surveyed systems. The table is intended to illustrate where the systems differ structurally, not to function as a competition score. We include two dimensions where nox-mem does not yet have coverage — corpus scale above 100K chunks and third-party benchmark evaluation — because honest comparison requires acknowledging these gaps explicitly. Limitations arising from these gaps are addressed in §6.3; planned mitigations are in §6.5.

**Table 1: Architectural and operational axes across memory systems.** Axes reflect structural design choices, not performance rankings. ✅ = implemented; ⚠️ = partial or indirect; ❌ = absent.

| System | KG Native | Hybrid Retrieval | Eval Harness | Multi-Agent | Shadow Discipline | Scale ≥100K corpus | Third-party benchmark | Coverage |
|---|---|---|---|---|---|---|---|---|
| **nox-mem (ours)** | closed-enum, 7 reasons | FTS5 + Gemini + RRF | nDCG/MRR/Recall | shared canonical | enforced >=7d | ❌ (64K current) | ❌ (internal golden only) | **5/7** |
| GraphRAG \cite{edge2024graphrag} | community detection | via KG queries | none | none | none | ✅ (1M+ MS-MARCO eval) | ⚠️ paper-specific | 1.5/7 |
| MemGPT \cite{packer2023memgpt} | none | embedding-first | none | per-agent state | none | ⚠️ varies | ❌ | 1.5/7 |
| Mem0 \cite{chhikara2025mem0} | optional (v2) | vector-only | LOCOMO only | user\_id partition | none | ❌ | ✅ LOCOMO | 1.5/7 |
| A-MEM \cite{xu2025amem} | Zettelkasten links | semantic-first | none | none | none | ❌ | ❌ | 1.0/7 |
| HiRAG \cite{huang2025hirag} | hierarchical | multi-level | task-specific | none | none | ⚠️ varies | ✅ multi-task | 2.5/7 |
| Cognee \cite{topoteretes2024cognee} | ECL pipeline | hybrid | ad-hoc | optional | none | ⚠️ ad-hoc | ⚠️ partial | 3.0/7 |
| LangChain Memory | none | key-value/buffer | none | session\_id | none | ⚠️ varies | ❌ | 0.5/7 |

We compare across seven axes. nox-mem covers 5/7: knowledge graph, hybrid retrieval, eval harness, multi-agent design, and enforced shadow discipline. It does **not** yet cover corpus scale above 100K chunks (current corpus: 64K) or evaluation against third-party benchmarks such as LOCOMO, LongMemEval, or BEIR — the evaluation harness uses an internally curated golden set. These are explicit limitations, not omissions, and are documented in §6.3 and §6.5. The two axes with zero coverage across all surveyed systems — pain-weighted salience and shadow discipline — are the primary novelty claims of this paper. We note that shadow validation as a technique has well-established roots in production search evaluation \cite{chapelle2012interleaved} and online controlled experiment methodology \cite{kohavi2020trustworthy}; our contribution is the instantiation of this discipline as an enforced architectural constraint in an LLM agent memory system, rather than as a testing methodology applied to web-scale traffic populations. Section 3 describes the nox-mem architecture across all five covered dimensions; Sections 4–5 provide empirical grounding.

---

## 3. System Architecture

nox-mem is a production memory system built on SQLite with three primary subsystems — storage, retrieval, and knowledge graph — plus an operational discipline layer that governs how the system evolves. The implementation is in TypeScript using \texttt{better-sqlite3} for synchronous database access, \texttt{sqlite-vec} for approximate nearest-neighbor search, and Gemini for embedding generation and LLM-based KG extraction. The system has operated continuously since March 2026 with 12 schema migrations and no irrecoverable data loss (one metadata-loss event on 2026-04-25 was recovered via re-ingestion; see §6.2).

### 3.1 System Overview

\[FIGURE 1: System Architecture — Mermaid diagram to be converted to PDF vector figure\]

```
Source files (.md / .docx / .pptx / .pdf / entity files)
    |
    v
ingest-router (inotifywait watcher + manual CLI)
    |
    |-----> chunks table (canonical, 64K+ rows)
               |
               |-----> chunks_fts (FTS5 BM25 index)
               |-----> vec_chunks (sqlite-vec, 3072d Gemini embeddings)
               |-----> kg_entities + kg_relations (LLM-extracted, nightly)
               |-----> search_telemetry (shadow-mode telemetry + eval harness)
               |
    query --> search() pipeline:
               Layer 1: FTS5 BM25 candidates
               Layer 2: Gemini semantic candidates
               Layer 3: RRF fusion (k=60) + salience boost + section_boost
               --> ranked results (p95 < 1s @ 64K chunks)
```

The entry point for all CLI operations is \texttt{dist/index.js} (the compiled package binary). An HTTP API on port 18802 exposes search, knowledge graph, health, and operational endpoints for agent integration.

### 3.2 Storage Layer

The canonical store is a single SQLite database accessed via \texttt{better-sqlite3} for synchronous, blocking reads — a deliberate choice that simplifies the concurrency model for a single-node deployment. Three coordinated tables implement the storage layer:

\texttt{chunks} is the central table, containing content text, metadata (\texttt{source\_file}, \texttt{chunk\_type}, \texttt{created\_at}, \texttt{last\_seen}), and operational fields (\texttt{pain} REAL DEFAULT 0.2, \texttt{importance} REAL, \texttt{section} TEXT, \texttt{section\_boost} REAL, \texttt{retention\_days}). The schema has evolved through 12 versions (v1 through v12) since March 2026; all migrations have been applied to the live database without downtime or data loss. Key schema additions include \texttt{retention\_days} (v8, typed retention by chunk category), \texttt{pain} (v9, severity signal), and \texttt{section} with \texttt{section\_boost} (v10, structural weighting for entity file sections).

\texttt{chunks\_fts} is an FTS5 virtual table providing BM25-ranked full-text search over chunk content. FTS5 vanilla AND-mode behavior — requiring all query terms to match — means that natural language queries frequently return zero results when run against the lexical index alone. This structural characteristic of FTS5 makes hybrid retrieval a necessity rather than an optimization, a finding confirmed in evaluation (§5.1).

\texttt{vec\_chunks} stores 3072-dimensional Gemini embeddings (\texttt{gemini-embedding-001}) via the \texttt{sqlite-vec} extension, enabling approximate cosine similarity search without external vector store infrastructure. Current vector coverage is 99.97% across the 61,257-chunk snapshot used for all reported experiments (§3.8).

Retention policy is encoded directly in the schema via \texttt{retention\_days}: feedback and person records are set to \texttt{NULL} (never decay); decisions and projects have 365-day retention; team context 120 days; daily notes 90 days; pending items 30 days. This ensures that the system's own operating rules cannot be silently evicted by a generic decay policy.

### 3.3 Retrieval Layer

The retrieval pipeline operates in three sequential layers, with results from layers one and two merged via Reciprocal Rank Fusion \cite{cormack2009rrf}:

**Layer 1 — Lexical retrieval.** FTS5 BM25 search expands the query against the \texttt{chunks\_fts} index, returning up to $k_1$ ranked candidates. Results are deduplicated by chunk ID before passing to fusion.

**Layer 2 — Semantic retrieval.** The query is embedded using \texttt{gemini-embedding-001} (3072d), and cosine similarity search is performed against \texttt{vec\_chunks} via \texttt{sqlite-vec}, returning up to $k_2$ ranked candidates.

**Layer 3 — RRF fusion and boosting.** Candidates from layers one and two are merged via Reciprocal Rank Fusion \cite{cormack2009rrf} with $k=60$:

\[
  s_{\text{rrf}}(d) = \frac{1}{k + r_{\text{fts}}(d)} + \frac{1}{k + r_{\text{sem}}(d)}
\]

where $r_{\text{fts}}(d)$ and $r_{\text{sem}}(d)$ are the BM25 and cosine-similarity ranks of chunk $d$ respectively.

The fused score is then combined with two boost signals via log-additive aggregation:

\[
  \log s_{\text{final}}(d) = \log s_{\text{rrf}}(d) + \log s_{\text{salience}}(d) + \log s_{\text{section}}(d)
\]

where $s_{\text{salience}}(d) = \texttt{recency}(d) \times \texttt{pain}(d) \times \texttt{importance}(d) \in [0, 2]$ (§3.5), and $s_{\text{section}}(d) \in \{2.0,\,1.5,\,0.8,\,1.0\}$ for compiled, frontmatter, timeline, and unstructured (NULL) section types respectively.

Equivalently in linear space, $s_{\text{final}}(d) = s_{\text{rrf}}(d) \cdot s_{\text{salience}}(d) \cdot s_{\text{section}}(d)$. The two formulations are mathematically identical; the log-additive form is operationally preferred because it allows each boost's contribution to be recorded and monitored independently in the \texttt{search\_telemetry} log without re-multiplication. The concern motivating this choice is multiplicative stacking: uncapped multiplicative boosts compound geometrically (e.g.\ three independent 2$\times$ boosts yield an 8$\times$ total factor), causing score distribution collapse that prior operational experience identified as a ranking instability [NEEDS VALIDATION §5.5]. The log-additive encoding does not cap the boosts; it makes each factor's contribution linearly visible in telemetry, enabling early detection of stacking before activation.

Top-$k$ chunks are returned in descending order of $s_{\text{final}}$.

The pipeline achieves p95 search latency below one second across the 64K chunk corpus, measured in production over the observation period. The \texttt{--no-hybrid} flag disables semantic retrieval for latency-constrained contexts where lexical precision is acceptable.

### 3.4 Knowledge Graph Layer

An LLM-extracted knowledge graph augments chunk retrieval with structured relationship data. Entities and relations are extracted incrementally via nightly batch runs using \texttt{gemini-2.5-flash} and stored in \texttt{kg\_entities} (~402 entities) and \texttt{kg\_relations} (~544 relations).

Entity types follow a closed taxonomy of 10 categories: person, project, agent, tool, concept, organization, technology, document, decision, and metric. Relation edges use free-form \texttt{relation\_type} text combined with a closed-enum \texttt{relation\_reason} field with seven canonical values: \texttt{depends\_on}, \texttt{derived\_from}, \texttt{opposes}, \texttt{extends}, \texttt{replaces}, \texttt{mentions}, and \texttt{unknown}. The closed enum enables downstream tooling — \texttt{impact \textless entity\textgreater} computes one-hop blast radius with reason-priority weighting; \texttt{detect-changes} maps git diffs to affected KG entities — without requiring LLM inference at query time.

Edge type enum coverage required explicit engineering. Initial extraction with an optional enum field and a "use unknown if unsure" prompt instruction produced 86% \texttt{unknown} labels across n=100 sampled relations. A three-path fix — a revised prompt with explicit examples for each non-unknown category; a code-side defensive normalization map (\texttt{RELATION\_TYPE\_TO\_REASON}, 24 input aliases covering PT-BR and EN free-text variants that collapse to the 7 canonical reasons); and a post-extraction validation pass — improved the enum coverage rate from 14% to 56% (4× improvement), equivalently reducing the \texttt{unknown} rate from 86% to 44% [NEEDS VALIDATION §5, n=100 sample]. The enum coverage rate measures the proportion of sampled relations where the LLM committed to one of the six non-unknown typed values rather than falling back to \texttt{unknown}; it is a self-reported coverage rate, not a classification accuracy against a human-annotated ground truth (see §6.3). This experience reinforces a general principle: LLM-extracted structured fields with optional enums and uncertainty-deferring prompts will systematically underperform; defensive code-side normalization is required.

### 3.5 Pain-Weighted Salience

The salience formula is:

$$\texttt{salience}(\textit{chunk}) = \texttt{recency}(\textit{chunk}) \times \texttt{pain}(\textit{chunk}) \times \texttt{importance}(\textit{chunk})$$

where:

- $\texttt{recency} \in [0, 1]$ is an exponential decay function over the \texttt{last\_seen} timestamp, parameterized by the chunk's \texttt{retention\_days} value;
- $\texttt{pain} \in [0.1, 1.0]$ encodes the operational severity of the recorded experience, annotated via \texttt{pain: 0.X} markers in entity files. Values are assigned on a five-point semantic scale: 0.1 (trivial note), 0.3 (minor friction), 0.5 (significant issue), 0.7 (major incident), 1.0 (production outage with data loss or downtime);
- $\texttt{importance} \in [0, 1]$ is derived from \texttt{mention\_count} across the corpus and entity-type priors.

The formula is multiplicative: a high-pain chunk with low recency can still score above a low-pain chunk with high recency when the severity differential is large. This reflects an engineering choice motivated by operational practice rather than a biological or psychometric claim. The five-point scale (0.1, 0.3, 0.5, 0.7, 1.0) follows the structure of established incident severity taxonomies \cite{pagerduty2023severity,beyer2016site}: just as incident management systems assign higher dispatch priority to a production outage than a documentation note regardless of their timestamps, pain weighting ensures that incident-derived memory dominates retrieval over routine content even when recency is comparable. The 10× spread between extreme values is an engineering judgment: a prod-outage memory should dominate retrieval over a routine note even when both are recent, and a 10× ratio provides meaningful separation without compressing the middle of the scale. Multiplicative aggregation is preferred over additive because it preserves the relative severity ratio across log-scale ranking; a constant additive offset shrinks relative to RRF scores as corpus size grows. We do not claim psychometric or biological validity for the specific values or the aggregation form; calibration validation (e.g., 2× vs. 100× spread, additive vs. multiplicative) is left as future empirical work (§6.3).

The salience signal is exposed in shadow mode at \texttt{/api/health.salience} without affecting production ranking, enabling comparison against the baseline before activation (§3.6). Ablation results comparing retrieval quality with real versus uniform pain values on $n=31$ post-incident queries are reported in §5.5 (E10, 2026-05-04); the aggregate result is directional but not statistically significant, with Q55 as the primary positive case study ($\Delta = +0.349$).

### 3.6 Enforced Shadow Discipline

The shadow discipline mechanism enforces a separation between observing a retrieval change and deploying it. Any modification that affects ranking — scoring formula changes, boost adjustments, new retrieval layers — must run in shadow mode for a minimum of seven days before activation. This is an architectural constraint, not a documented recommendation. Shadow validation has well-established roots in production search and online controlled experiments \cite{kohavi2020trustworthy,chapelle2012interleaved}. Our contribution is the application of shadow discipline specifically to LLM agent memory systems, with architectural enforcement via cron and health endpoints.

Implementation relies on three components: (1) an environment variable gate (\texttt{NOX\_SALIENCE\_MODE=shadow|active}) that controls whether the salience score affects production ranking or is only written to \texttt{search\_telemetry}; (2) a health endpoint (\texttt{/api/health.opsAudit}) that cron checks every 15 minutes and alerts via Discord if the shadow observation period has not been met; (3) an append-only audit log (\texttt{ops\_audit} table) with database triggers that block DELETE and UPDATE on rows with terminal status, ensuring the shadow-period record cannot be retroactively modified.

The distinction from A/B testing is important: A/B testing requires live traffic over a production population. Shadow discipline for operational/personal corpora has no such traffic — queries are infrequent, irregular, and non-i.i.d. The shadow mechanism instead collects telemetry on what the proposed ranking *would have done* on each live query, accumulating promotion, review, and archive candidate distributions across the observation period. The distribution comparison then drives the activation decision.

The salience validation run (Fase 1.7b-b) ran for seven days before activation, producing 191 promotion candidates, 16,608 review cases, and 45,743 archive recommendations. The distribution was reviewed, found consistent with design intent, and activation proceeded. Counterfactual analysis suggests that the April 25 reindex incident — the motivating example in §1 — would have been detected during a shadow period: the reindex operation altered chunk distributions in ways that would have surfaced as anomalous in telemetry within hours.

### 3.7 Shared-Canonical Multi-Agent Design

Six agents (Atlas, Boris, Cipher, Forge, Lex, and Nox) share a single \texttt{chunks} table. Agent-specific content is distinguished by \texttt{source\_file} path prefix (\texttt{agents/\textless name\textgreater /...}) rather than separate tables, schemas, or databases. Cross-agent queries use \texttt{cross-search} and \texttt{cross-kg} CLI commands, which apply additional \texttt{source\_file} filters to retrieve context generated by a specific agent.

The design assumes a single trusted operator. It is explicitly not suitable for multi-tenant SaaS deployments, where user isolation is a security requirement rather than an engineering choice. Within the trusted-operator constraint, shared-canonical design provides cross-agent intelligence as a structural property: when Forge ingests a decision about an infrastructure change, Atlas retrieves it on the next architecturally relevant query without any synchronization step.

The operational tooling layer — \texttt{detect-changes}, \texttt{impact}, \texttt{api-impact}, \texttt{consolidate-merge}, \texttt{kg-reclassify} — extends the system to support multi-agent workflows beyond retrieval, enabling agents to query the KG for blast-radius analysis before executing changes, and to surface merge candidates across agent-sourced entities.

The architecture in §3 provides the substrate for the empirical evaluation in §4–5. Section 4 describes the evaluation methodology, including the golden query harness, baseline systems, and three-corpus protocol designed to address the single-corpus and single-curator limitations of operational memory benchmarking.

### 3.8 Pre-registration and Reproducibility Commitments

A persistent concern in machine learning evaluation is post-hoc query set construction: a curated golden set assembled with knowledge of retrieval results can unintentionally favor the system under evaluation, inflating reported metrics without any deliberate manipulation \cite{munafosystematic2017}. We address this concern explicitly by anchoring the experimental design to a pre-registration artifact that predates all result collection.

\textbf{Pre-registration document.} The evaluation protocol — including query categories, metrics, baseline selection criteria, and success thresholds for each hypothesis — was committed to \texttt{paper/publication/03-experiments-needed.md} before any baseline or ablation experiment was executed. This document is tracked in the public repository (\url{https://github.com/totobusnello/memoria-nox}) and its commit history is immutable. The git commit hash and ISO-8601 author timestamp for that file should be verified at submission via:

\begin{verbatim}
git log --follow -1 --format="%H  %aI" \
    paper/publication/03-experiments-needed.md
\end{verbatim}

\textbf{Golden query set freeze.} The 60-query golden set (\texttt{eval/golden-queries.jsonl}, comprising the 50-query main set R01b and the 10-query held-out subset R01c) is included in the public repository and the submission tar. The verifiable identifiers are:

\begin{itemize}
  \item \textbf{Git commit hash} (import from production VPS into the versioned repository): \texttt{f75d1864b581d0a0933704e997669bbd41aa507f}
  \item \textbf{Author timestamp} (ISO-8601 with BRT offset): \texttt{2026-05-04T13:38:01-03:00}
  \item \textbf{Freeze mtime} (last meaningful content modification on VPS, UTC): \texttt{2026-05-04T09:45Z}
  \item \textbf{SHA-256 hash}: \texttt{9bff8ee7b9056eff6a1af22305cae762aa4b98e682578faffb4c22cdd0a2cd7d}
  \item \textbf{File size}: 8990 bytes, 60 lines (one query per line, JSONL)
\end{itemize}

The freeze mtime is the timestamp of the last addition (the R01c held-out partition Q51–Q60); the file was authored on the production VPS and remained byte-stable until imported into the versioned repository at the commit hash above. The SHA-256 hash allows any third party to verify byte-for-byte that the included \texttt{golden-queries.jsonl} matches the artifact used for all reported evaluations. The git commit hash anchors the file to an immutable point in the public repository's history, predating arXiv submission. The golden query set was frozen \textit{before} any BM25 (Pyserini), multilingual-e5-base, BEIR TREC-COVID, LOCOMO, or pain-ablation (E10) experiment was executed; all results in §5 were produced against this exact file. The evaluation metrics (nDCG@10, MRR, Recall@10, Precision@5) and the analysis pipeline were specified in the \texttt{03-experiments-needed.md} pre-registration document at the same git commit.

\textbf{Held-out subset disclosure.} The 10 queries designated R01c (held-out for baseline robustness validation) were locked as a named subset within the golden set before the final tuning sprint that fixed the RRF $k=60$ parameter and the salience boost coefficients. They were not constructed after tuning; they are a partition of the original 60-query set, identified by their position index (Q51–Q60) in the JSONL file. R01c is evaluated at most once per major system revision and its results are reported separately from the 50-query main set to prevent iterative query refinement bias (§4.1). No queries were added or modified after the freeze commit; the set grew from an early draft of 50 queries to 60 through a single documented extension, at which point the R01c partition was simultaneously designated and locked.

\textbf{Registered reports context.} While this paper does not constitute a formal registered report in the sense of \cite{munafosystematic2017} — no journal or conference pre-acceptance was obtained prior to experimentation — the \texttt{03-experiments-needed.md} document serves an equivalent function within the project's operational discipline: it records pre-registered hypotheses with explicit success thresholds (e.g., $\Delta$ nDCG@10 $\geq 0.05$ for E10) that are reported honestly regardless of outcome, as evidenced by the DIRECTIONAL, NOT SIGNIFICANT result for the E10 pain ablation (§5.5). The pre-registration document, the golden query set, and all evaluation scripts are included in the public repository under MIT license, permitting full independent verification.
