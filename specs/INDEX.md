# Specs — Índice

> Gerado em 2026-05-21. Status derivado do campo `**Status:**` de cada spec.  
> Pasta: `specs/` — 37 itens (36 arquivos `.md` + 1 diretório de implementação).

---

## Seção 1 — Active

Specs em andamento, implementation-ready ou em kickoff explícito.

| Spec | Título | Status declarado | Criado |
|---|---|---|---|
| [E10-followup-pain-ablation-execution.md](E10-followup-pain-ablation-execution.md) | E10 Followup: Pain Ablation Execution Plan | Blocked — requires explicit authorization | — |
| [E12-followup-requesting-agent-migration.md](E12-followup-requesting-agent-migration.md) | E12 Followup: `requesting_agent` Column Migration | Ready for implementation | — |
| [2026-05-01-E03a-spo-injection.md](2026-05-01-E03a-spo-injection.md) | E03a — Entity-Facts SPO Injection (`<vault-facts>` block) | Design spec (CANDIDATE) | 2026-05-01 |
| [2026-05-17-GTM-readme-hero-upgrade.md](2026-05-17-GTM-readme-hero-upgrade.md) | GTM — README Hero Visual Upgrade (post-Q4 gate) | READY-TO-EXECUTE (gated on Q4 COMPARISON) | 2026-05-17 |
| [2026-05-17-L2-conflict-detection.md](2026-05-17-L2-conflict-detection.md) | L2 — KG conflict / contradiction detection (memanto-inspired) | SPEC — implementation-ready, blocked on schema | 2026-05-17 |
| [2026-05-17-L3-confidence-field.md](2026-05-17-L3-confidence-field.md) | Lab L3 — Confidence + provenance field (schema v19 candidate) | SPEC — implementation-ready, ranking GATED | 2026-05-17 |
| [2026-05-17-P1-answer-primitive.md](2026-05-17-P1-answer-primitive.md) | P1 — Answer Primitive (Grounded RAG with Citations) | Design spec (CANDIDATE — implementation-ready) | 2026-05-17 |
| [2026-05-17-P2-hooks-autocapture.md](2026-05-17-P2-hooks-autocapture.md) | P2 — Auto-capture de conversas via Claude Code hooks | Proposto — spec implementation-ready | 2026-05-17 |
| [2026-05-17-P4-connect-ide.md](2026-05-17-P4-connect-ide.md) | P4 — `nox-mem connect <ide>` — Multi-IDE Bridge | SPEC (não-implementado) | 2026-05-17 |
| [2026-05-18-A2-implementation-kickoff.md](2026-05-18-A2-implementation-kickoff.md) | A2 Implementation Kickoff — Export/Import (Encrypt-by-Default) | Kickoff aberto, implementation pending T1 | 2026-05-18 |
| [2026-05-18-A3-implementation-kickoff.md](2026-05-18-A3-implementation-kickoff.md) | A3 Implementation Kickoff — Provider Abstraction Layer | KICKOFF (planning only, NOT implementation) | 2026-05-18 |
| [2026-05-18-L4-regex-first-extraction.md](2026-05-18-L4-regex-first-extraction.md) | L4 — Regex-first typed-link extraction with Gemini fallback | SPEC — implementation-ready, shadow-mode default | 2026-05-18 |
| [2026-05-18-P1-implementation-kickoff.md](2026-05-18-P1-implementation-kickoff.md) | P1 Implementation Kickoff — Answer Primitive | READY-TO-EXECUTE | 2026-05-18 |
| [2026-05-18-P2-implementation-kickoff.md](2026-05-18-P2-implementation-kickoff.md) | P2 Implementation Kickoff — Claude Code Hooks Auto-Capture | READY-TO-EXECUTE (after P1 + A2) | 2026-05-18 |
| [2026-05-18-P4-implementation-kickoff.md](2026-05-18-P4-implementation-kickoff.md) | P4 Implementation Kickoff — `nox-mem connect <ide>` | ready to start (planning artifact) | 2026-05-18 |
| [2026-05-18-P5-implementation-kickoff.md](2026-05-18-P5-implementation-kickoff.md) | P5 Implementation Kickoff — Real-time Viewer (SSE + 4 panels) | ready to start (planning artifact) | 2026-05-18 |
| [2026-05-18-P6-mobile-sync.md](2026-05-18-P6-mobile-sync.md) | P6 — Mobile Sync Architecture Spec | Spec (2026-05-18) — P6 candidate | 2026-05-18 |
| [2026-05-18-P7-browser-extension.md](2026-05-18-P7-browser-extension.md) | P7 — Browser Extension Spec | Spec (2026-05-18) — P7 candidate | 2026-05-18 |
| [2026-05-18-Q1-Q2-Q3-vps-scheduling.md](2026-05-18-Q1-Q2-Q3-vps-scheduling.md) | Q1+Q2+Q3 VPS Scheduling — Operational Spec | SPEC (pendente execução supervisionada) | 2026-05-18 |
| [2026-05-21-per-method-benchmark-comparison.md](2026-05-21-per-method-benchmark-comparison.md) | Per-method benchmark — nox-mem vs Mem0/Zep/EverCore/HyperMem | SPEC — implementation pending, gated D49 phase 2 | 2026-05-21 |
| [2026-05-21-G10d-conditional-mutex-by-query-entities.md](2026-05-21-G10d-conditional-mutex-by-query-entities.md) | G10d — Conditional Hard Mutex by query_entities count | SPEC — implementation-ready, gated em ablation eval | 2026-05-21 |
| [2026-05-01-F10-observability-dashboard.md](2026-05-01-F10-observability-dashboard.md) | F10 — Observability Dashboard (refresh 2026-05-21) | SPEC — Phase A implementation-ready | 2026-05-01 |
| [2026-05-21-neural-reranker-design.md](2026-05-21-neural-reranker-design.md) | Neural reranker — bge-v2-m3 via vLLM local sidecar (D01 v3) | SPEC — parking-lot Lab Q1, gated D49/D50 | 2026-05-21 |
| [2026-05-24-per-method-benchmark-phase-b.md](2026-05-24-per-method-benchmark-phase-b.md) | Per-method benchmark Phase B — intra-system method-config ablation matrix (Lab Q1) | SPEC — implementation pending, gated D49 phase 2 | 2026-05-24 |

---

## Seção 2 — Done

Specs com implementação concluída e merged, ou explicitamente marcadas como completas.

| Spec | Título | Status declarado | Criado |
|---|---|---|---|
| [2026-04-27-R01a-eval-harness.md](2026-04-27-R01a-eval-harness.md) | R01a — Eval Harness Skeleton | Proposto (impl scheduled pós-G03) — depois executado | 2026-04-27 |
| [2026-05-06-E05b-reason-ranking-boost.md](2026-05-06-E05b-reason-ranking-boost.md) | E05b — Reason-aware Ranking Boost | Design spec (CANDIDATE) — merged Wave A | 2026-05-06 |
| [2026-05-06-E13-temporal-aware-ranking.md](2026-05-06-E13-temporal-aware-ranking.md) | E13 — Temporal-aware Ranking | Design spec — implementado | 2026-05-06 |
| [2026-05-07-E12-tier3-ocr.md](2026-05-07-E12-tier3-ocr.md) | E12 — Tier 3 OCR pipeline | Design spec — implementado (ver E12-followup-implementation/) | 2026-05-07 |
| [2026-05-10-E14-retrieval-evolution.md](2026-05-10-E14-retrieval-evolution.md) | E14 — Retrieval Evolution (post-R03) | ✅ Wave 1 COMPLETA 2026-05-17 | 2026-05-10 |
| [2026-05-17-A2-export-import.md](2026-05-17-A2-export-import.md) | A2 — Schema Export/Import Portability | 📐 Spec aberto (kickoff em 2026-05-18-A2) | 2026-05-17 |
| [2026-05-17-P5-viewer-realtime.md](2026-05-17-P5-viewer-realtime.md) | P5 — Real-time Viewer Upgrade (SSE + 4 panels) | Design spec 📋 QUEUED overnight 2026-05-17 — executado | 2026-05-17 |
| [2026-05-20-mutual-exclusion-section-source-type.md](2026-05-20-mutual-exclusion-section-source-type.md) | Hard Mutex section ↔ source_type | ✅ Implementado via PR #182 + G10 validated (+0.79% nDCG / +2.65% MRR) + G11 trim rejected | 2026-05-20 |

> **Nota:** Vários specs do tipo `*-implementation-kickoff.md` (2026-05-18) ficaram em Active porque a implementação estava em andamento na data de criação; verificar PRs merged para reclassificar.

---

## Seção 3 — Deferred

Parked, aguardando evidência, cortados ou gated em condição futura.

| Spec | Título | Status declarado | Criado |
|---|---|---|---|
| [2026-04-12-self-evolving-hooks.md](2026-04-12-self-evolving-hooks.md) | Self-Evolving Hooks — Spec | Proposto (sem ação pós-spec) | 2026-04-12 |
| [2026-05-01-E04a-focus-boost.md](2026-05-01-E04a-focus-boost.md) | E04a — Session Focus Topic Boost | Design spec (CANDIDATE) — sem evidência de impl | 2026-05-01 |
| [2026-05-07-D01-cross-encoder-reranker.md](2026-05-07-D01-cross-encoder-reranker.md) | D01 — Cross-encoder Reranker (Shadow) | ⛔ CUT v1 (2026-05-08) — source-of-truth limpo | 2026-05-07 |
| [2026-05-17-E15-codegraph-inspired-improvements.md](2026-05-17-E15-codegraph-inspired-improvements.md) | E15 — CodeGraph-inspired retrieval improvements | 📋 QUEUED — pós-R03 ou paralelo a D01 v3 | 2026-05-17 |
| [temporal-retrieval-path-spike.md](temporal-retrieval-path-spike.md) | Temporal Retrieval Path — Q1 R&D Spike | Research spike — design + spike isolado, não deploy | — |

---

## Seção 4 — Templates

Arquivos de template ou scaffolding pré-aberto.

| Spec | Título | Notas | Criado |
|---|---|---|---|
| [d50-template.md](d50-template.md) | D50 Template — Temporal proximity rerank active vs off | TEMPLATE pré-aberto (2026-05-20), decisão final D50 pendente | 2026-05-20 |
| [d51-template.md](d51-template.md) | D51 Template — Conditional Hard Mutex (G10d) active vs G10 | TEMPLATE pré-aberto (2026-05-21), decisão final D51 pendente em G10d ablation | 2026-05-21 |

---

## Diretórios

| Diretório | Conteúdo |
|---|---|
| [E12-followup-implementation/](E12-followup-implementation/) | Artefatos de implementação E12: patches, migration SQL, deployment checklist + log |

---

*Para adicionar novo spec: criar `specs/YYYY-MM-DD-<ID>-<slug>.md` com `**Status:**` na linha 3. Atualizar este INDEX manualmente ou via `docs(specs): update INDEX`.*
