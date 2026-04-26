# Integration Roadmap v1.6 — Phase Matrix consolidada + Wave Roadmap evolutivo

**Data:** 2026-04-25
**Versão:** 1.6 — **CANÔNICO** (substitui Phase Matrix do v1.5; resto do v1.5 permanece referência)
**Status:** promovido após 4 rodadas de revisão (architect, critic, planner, architect-reviewer + segunda rodada técnica)
**Tese unificadora (1 linha):**
> *"Antes de adicionar fases novas, blindar as que existem: snapshot pré-op atômico, ingest-router unificado e canary invariants são pré-requisito pra ativar shadow modes (salience/section_boost) com confiança. Tier 2 PDFs e Fase 4 Obsidian são momentum — não atrasar por hardening serial."*

---

## 1. Mapeamento Direto — propostas de evolução vs estado atual (v1.5)

Análise das 6 ideias inspiradas em padrões externos de code-intelligence/memória, cruzadas com o que já existe em `2026-04-19-unified-evolution-roadmap.md` v1.5:

| # | Proposta de evolução | Status no v1.5 | Veredito | Ação proposta |
|---|---|---|---|---|
| **1. Edge typing** (`relation_reason`+`confidence`) | `kg_entities`/`kg_relations` existem (~544 rels via Gemini 2.5 Flash); 1.7a já passou ontology grounding | **REFINO**, não fase nova | Migration aditiva v11 (`relation_reason TEXT`, `confidence REAL DEFAULT 0.7`) + backfill heurístico via existing `extraction_method`. Vocabulário enum CLOSED (`mentions/owns/decides/depends/derives_from/contradicts/supersedes`) — sem free-form. **4-6h** |
| **2. Staleness layer** (`stale-check` via lastCommit) | `graphify-out/cache/*.json` já tem hashes por arquivo (`<sha256>.json`). Graphify update já é incremental. Não há `nox-mem stale-check` exposto | **PARCIAL** (graphify tem; nox-mem CLI não expõe) | Subcomando `nox-mem stale-check` consulta cache + `chunks.last_seen_at` + git log no path. Não duplica graphify; é leitura. **2-3h** |
| **3. Dry-run mode** | Zero precedente. `consolidate`, `compact`, `crystallize`, `reindex` mutam direto | **NOVO** (mas crítico pós-incident 2026-04-25 reindex.ts wipe) | `--dry-run` produz diff JSON em stdout sem tocar DB. Implementar primeiro em `reindex` (autor do incident), depois propagar. **3-4h** |
| **4. Eval harness** (`eval/queries.jsonl`) | `search_telemetry` existe (Fase 1.6) + `/api/health.searchTelemetry` | **EVOLUÇÃO**, não criação | Eval harness consome telemetry + 50 golden queries. Sem isso, ativação salience/section_boost é vibe-check. **8-12h** |
| **5. Group routing** (`@group`, `memory/groups.yaml`) | `cross-search` cobre N agents; SOUL.md é decisão filosófica de routing humano | **CONFLITO LEVE** | `cross-search` já entrega isso ad-hoc. `groups.yaml` reintroduz config estática que SOUL.md rejeitou. **CORTAR** ou diluir como sintaxe açúcar de `cross-search --agents nox,forge` |
| **6. Paper v2** | `paper-tecnico-nox-mem.md/.docx` existe (stale, v3.0.0) | **UPDATE**, não criação | Não é fase de eng. **POSTERGAR** pra após Fase 3 Tier 2 estabilizar (paper sem dados novos é prematuro) |

**Críticas dos 3 agents — mapeamento adicional:**

| # | Crítica | Status no v1.5 | Veredito |
|---|---|---|---|
| Fase 0 — Query logging | `search_telemetry` já loga (Fase 1.6) | **JÁ EXISTE** — só falta golden-query tagging |
| Fase 0.5 — Ingest-router unified | Hoje: `ingest`, `ingest-entity`, `graphify-ingest` separados; reindex bypassa todos (causou incident hoje) | **NOVA, alta prioridade** — paga débito do incident |
| Fase 0.7 — Feature flags + migration framework | Schema v8/v9/v10 fizeram migration ad-hoc; flags são env vars (`NOX_SALIENCE_MODE`, `NOX_SECTION_BOOST_MODE`) | **PARCIAL** — formalizar registry |
| Fase 1 — Audit log + snapshot pré-op | Backup diário 02:00 + pre-release snapshots existem; **falta** snapshot pré-op atômico (reindex/consolidate) | **NOVA** — exata cura do incident 2026-04-25 |
| Fase 2 — Schema invariant tests CI gate | Zero CI nos schemas v8-v10 | **NOVA** — preveniria wipe de section/retention |
| Incremental indexing fundir Fase 2 | OK — Staleness + Incremental são duas faces | **MERGE** com #2 |

---

## 2. Conflitos com "NÃO FAZEMOS"

| Proposta | Risco de violar | Mitigação |
|---|---|---|
| **Ingest-router unified** | Pode aproximar "30 MCP tools" se cada modo virar tool | Manter **1 CLI verb** com `--mode={auto,entity,graphify,raw}`; **não** explodir em MCP tools novas |
| **Edge `relation_reason` vocabulary** | Se vocabulário virar free-form e indexado, vira "Text2Cypher in disguise" | Enum **fechado** (7 valores), sem query DSL. Pesquisa continua sendo hybrid search, não graph traversal |
| **Group routing** | Reintroduz routing algorítmico que SOUL.md rejeitou explicitamente | **CORTAR** ou virar açúcar sintático de `cross-search` |
| **Paper v2** com "Multi-Agent Federation" | Pode encorajar feature work especulativo | Paper documenta **o que existe**, não vende roadmap |
| **Eval harness** | Pode crescer pra "Dashboard de scoring" | Manter como CLI `nox-mem eval run` + JSONL out; UI fica no agent-hub-dashboard existente |

---

## 3. Dependências Cruzadas e Gates

**Gates intocáveis (não atrasar):**
- **2026-04-30** — ativação salience (`activate-salience.sh --apply`)
- **2026-05-01** — análise telemetria section_boost
- **7d observação shadow** dos 3 source files antes de arquivar

**Pré-requisitos para ativar shadow modes com confiança:**
1. **Fase 0 (query logging tagging)** — saber se ranking degradou pós-ativação
2. **Fase 1 (audit log + snapshot pré-op)** — rollback rápido se ativação correr mal
3. **Fase 2 (schema invariant CI)** — garantir que migrations futuras não wipam pain/section

**O que destrava Fase 4 Obsidian (hoje BLOCKED por Fase 3):**
- Fase 3 Tier 2 (PDFs text-layer) — único bloqueio real
- Tier 3 OCR é **opcional** — não bloqueia Fase 4 (decidir cortar do critical path)

**O que pode rodar paralelo:**
- Tier 2 ingest (I/O bound) ‖ infra hardening (Fase 0/1/2 Corpo B)
- SEH Self-Evolving Hooks (independente, 2h) ‖ qualquer outra coisa

---

## 4. Backlog pós-Fase 2 — Reconciliação

| # | Item | Status novo | Justificativa |
|---|---|---|---|
| 1 | Unit tests `parseRetentionOverride` | **MERGE com Fase 2 Corpo B** (schema invariant CI) | Mesmo gate de qualidade |
| 2 | Daily retention telemetry | **MERGE com Fase 0 (query logging)** | Mesmo pipeline de telemetry |
| 3 | `expires_at` generated column | **FECHADO** pela 1.7b-b (pain+retention já compõem salience) | Confirma hipótese |
| 4 | Issue upstream graph-memory | Mantém **baixa**, independente | OK |
| 5 | Docs CONVENTIONS.md chunk_type | **MERGE com Fase 0.5 ingest-router** | Doc do verb unificado |
| 6 | Canários como MCP tools | **PRECURSOR de feature flags (Fase 0.7)** | Confirma — flag-gated tools |
| 7 | Monkey-patch orphan alert | Mantém **baixa**, op tooling | OK |
| 8 | Rollback playbooks | **MERGE com Fase 1 (snapshot pré-op)** | Mesma família — dry-run preview + snapshot + playbook formam o tripé |

---

## 5. Sequência Cronológica Integrada

### Bloco I — PRÉ-GATE (HOJE → 2026-04-29) — 7h, infra crítica

Pré-gate enxuto: **só Fases A0 + A1**. Outras fases hardening movem pra pós-gate pra não congestionar telemetria shadow.

| # | Fase | Origem | Esforço | Justificativa |
|---|---|---|---|---|
| **A0** ✅ | Query logging + golden-tag (extends search_telemetry) | Crítica | **DONE 2026-04-25 ~10:45 BRT (~1h)** | Migration aditiva: 4 colunas em search_telemetry (`query_text`, `golden_id`, `top_chunk_ids`, `top_scores`) + index parcial em `golden_id`. Patch `search.ts` logTelemetry: opt-in via env `NOX_SEARCH_LOG_TEXT=1` (privacy default OFF). Backup `pre-A0-20260425-093920.db` (172MB). Validado: query 363 logou texto + top 5 chunk IDs + scores. /api/health.searchTelemetry agregações intactas. Zero regressão (canary OK, vc 100%). |
| **A1** ✅ | Audit log + snapshot pré-op atômico (v2 hardened) | Crítica + incident hoje | **DONE 2026-04-25 ~12:50 BRT (~3h v1) + ~45min fix v2 (16:30 BRT)** | **v1**: módulo `src/lib/op-audit.ts` (130 LOC) com `withOpAudit()` wrapper. **v2 pós-audit**: 130→285 LOC, 5 CRITICAL/HIGH fixados (filename collision-resistant pid+uuid, fail-closed snapshot via throw, path traversal protection allowlist, VACUUM INTO atômico via `.tmp`+integrity_check+rename, `safeRestore()` helper exportado, reapZombies on startup, schema_user_version+pid+snapshot_bytes nas audit rows, ACL 0600). Audit completo em `audits/2026-04-25-A1-A2-review.md`. |
| **A2** ✅ | Ingest-router unified (single dispatch ingestFile/ingestEntity/graphify) | Crítica + incident | **DONE 2026-04-25 ~14:00 BRT (~1h, vs 3h estimado)** | `src/lib/ingest-router.ts` (77 LOC) com `routeIngest()` + `detectIngestKind()`. 4 callers refatorados (watch/reindex/CLI ingest/MCP); CLI ingest-entity mantido direto (acesso explícito). Fallback automático pra markdown se entity parse falha. Defesa em camadas: `ingestFile()` mantém guard interno (fix incident hoje). Smoke test: `routeIngest(nox.md)` retornou `{kind:"entity", routedTo:"ingestEntityFile", chunks:8}`. |

**Riscos pré-gate (validados pelo planner):**
- A2 pode perturbar telemetria shadow → flag `NOX_INGEST_ROUTER=legacy` pra rollback de 1 comando
- A1 cresce storage com snapshots → retention 7d em `/var/backups/nox-mem/pre-op/`
- A2 não ataca o incident sozinho — A1 já protege via snapshot; A2 é prevenção arquitetural pra próxima classe

### Bloco II — GATES (2026-04-30 → 2026-05-02) — observação shadow

Janela de OBSERVAÇÃO. **Nada de schema/ranking changes.**

| Data | Gate | Ação |
|---|---|---|
| 2026-04-30 | Salience activation | `bash /root/.openclaw/scripts/activate-salience.sh --apply` se baseline 7d OK |
| 2026-05-01 | Section_boost decision | `bash analyze-shadow-telemetry.sh 7` — decidir `NOX_SECTION_BOOST_MODE=active` |
| 2026-05-02 | Arquivar 3 source files | `.archived-20260502` em projects.md/decisions.md/lessons.md |

### Bloco III — POST-GATE (2026-05-02 → ~2026-05-15) — momentum visível

Prioridade: **destravar Fase P + entregar valor visível ao Toto, paralelo a infra remanescente.**

| # | Fase | Origem | Esforço | Bloqueia |
|---|---|---|---|---|
| **A3** ✅ | Unit tests `parseRetentionOverride` (14 casos) | Backlog #1 | **DONE 2026-04-25 ~15:55 BRT (~25min)** | `src/__tests__/retention.test.ts` via `node:test` built-in (zero deps novas). 14 cases: never/numeric/CRLF/case-insensitive/edge cases/regression guards. **14/14 pass.** |
| **A4** ✅ | Canary invariants extension (+section/retention NOT NULL) | Crítica | **DONE 2026-04-25 ~16:01 BRT (~30min)** | `check-schema-invariants.sh` cron `*/15min` com 4 invariants: section NOT NULL ≥600, compiled ~183, feedback/person never_decay, ops_audit zero fails 24h, section_boost values consistentes (compiled=2.0/frontmatter=1.5/timeline=0.8). Exit code = violation count. Discord alert via webhook. Log `/var/log/nox-schema-invariants.log`. Smoke test: `OK section_nonnull=732 compiled=183 feedback_wrong=0 ops_failed=0 boost_mismatch=0`. |
| **A5** ✅ | Dry-run mode em reindex/consolidate (crystallize defer) | Pattern externo | **DONE 2026-04-25 ~16:30 BRT (~1h, vs 3h estimado)** | `nox-mem reindex --dry-run` + `nox-mem consolidate --dry-run` produzem JSON preview (wouldDelete/wouldProcess/protected/estimatedDuration) sem mutar DB. Compact já tinha dryRun nativo. CLI flag via commander. Smoke test: ambos retornam preview correto, `chunks=9540 / section=732` intactos pós-execução. Crystallize não wrapped (manual via skill, baixo risco; defer pra demanda futura). |
| **B1** | **Fase 4 Obsidian view-only** | v1.5 | 1h | **Destrava Fase P** |
| **B2** | Fase 3 Tier 2 — PDFs text-layer (paralelo) | v1.5 | dias | Fase 4 estabilizar |
| **B3** | Backlog #4, #5, #7, #8 sprint (issue upstream + docs CONVENTIONS + monkey-patch alert + rollback playbooks) | Backlog | 1h45 | — |
| **(candidates)** | **A6** (Entity-Facts SPO Injection) + **A7** (Session Focus Topic Boost) | ClawMem analysis 04-26 | ~6h total | ver **Section 9** + `plans/2026-04-26-clawmem-analysis.md` |

### Bloco IV — Memory Graph Maturity Waves (Maio-Ago 2026) — ver Seção 7

Edge typing, detect-changes, impact, eval harness, paper v2 — todos GATED por métricas, não calendário. **Detalhamento completo em Seção 7.**

### Bloco V — Horizonte 60d+ (~Setembro 2026 em diante)

| # | Fase | Origem | Esforço | Depende |
|---|---|---|---|---|
| C1 | Path B-lite reflect cache (semantic key) | v1.5 | 2-3h | 7d telemetria reflect + Fase 1.7a |
| C2 | SEH Self-Evolving Hooks | v1.5 | 2h | — |
| C3 | Tier 3 OCR + Fathom + Path C | v1.5 (opcional) | dias | — |
| C4 | Fase 4b → 5 → P (productização NOX-Supermem) | v1.5 | semanas | Fase 4 estável 30d |

**Cortado definitivamente:** Group routing (#5 Corpo B) — viola SOUL.md. Se algum dia doer, virar açúcar de `cross-search`.

---

## 6. Plano de Comunicação Pós-Promoção

Ordem de notificação após este doc virar canônico (do planner):

1. **Toto** (este review) — aprovação final + ack das mudanças
2. **Forge** (PR review se ingest-router for shipado) — Discord channel forge
3. **Cipher** (snapshot retention monitoring) — Discord channel cipher
4. **agent-hub-dashboard** — atualizar painel de versão do roadmap
5. **CLAUDE.md** — commit junto da regra #15 ("reindex/consolidate/crystallize só com `--dry-run` OU snapshot atômico — lição do incident 2026-04-25")
6. **MEMORY.md** auto-memory já contém os 3 feedback files de hoje (reindex_must_route_entity_files, eod_cron_reindex_was_real_trigger, user_systemd_units_can_run_rogue)

---

## 7. Memory Graph Maturity Waves — Roadmap Evolutivo (Maio-Ago 2026)

**Premissa:** conceitos extraídos de precedentes externos de code-intelligence + memória vetorial foram filtrados pelo domínio nox-mem (memória conceitual multi-agent). Não copiamos arquitetura externa — incorporamos seletivamente o que entrega valor mensurável ao nosso problema, gated por métricas (não calendário).

**Capacity reality (validada pelo critic):**
- 4 meses ≈ 150h disponíveis (10h/semana focado, otimista)
- Compromisso pré-existente até Set/2026: ~95h (hardening 7h + Tier 2 PDFs ~25h + Fase 4 1h + backlog ~20h + Fase P early ~12h + buffer 30h)
- Sobra para Waves: **~50h em 4 meses, margem incident ~5h**
- Hoje (2026-04-25) foi incident de 12min recovery; um único de 4-6h queima 80% da margem

**Conclusão:** as 3 waves abaixo somam **46-58h realista** (não 43h fantasia inicial). Margem apertada → kill switches obrigatórios.

### WAVE 1 — Maio 2026 (paralelo a Tier 2 PDFs) — 27-30h

| ID | Item | Esforço | Notas |
|---|---|---|---|
| **W1.1** | Edge typing FULL — `relation_reason` enum 7 (`mentions/owns/decides/depends/derives_from/contradicts/supersedes`) + `confidence REAL DEFAULT 0.7` em `kg_relations` | **12-14h** (subestimado original 6h) | Migration v11. Pré-req: amostragem dos ~544 rels Gemini-livre validar enum cobre ≥85%. Backfill com rollback. **Shadow-mode 7d antes de aplicar em ranking.** Vocabulário enum **CLOSED** (não free-form, não query DSL — respeita NÃO FAZEMOS Text2Cypher). |
| **W1.2** | `nox-mem detect-changes --since=<commit>` — git diff → entities/chunks afetados | **5-6h** | **READ-ONLY**, sem hook automático de reingest (senão viola "git-as-source-of-truth"). Cruza paths→`chunks.source_file`→entities. Útil pra "o que mudou desde última sessão Toto?". |
| **W1.3** | `nox-mem impact <entity>` — 1-hop blast radius via `kg_relations` | **6h** | Upstream (callers) + downstream (callees). Risk summary: count por chunk_type. **Sem DSL, traversal SQL fixa.** Cap em 1-hop pra MVP; multi-hop = Wave 4 se valor provar-se. |
| **W1.4** | `nox-mem api_impact <signature-change>` — multi-arquivo via grep + import graph | **4h** (NOVO — adicionado pós-architect) | Cobre a classe que W1.3 NÃO cobre: bug arquitetural tipo o de hoje (DELETE+rewrite no DB, não relação faltante). |
| **(candidate)** | **W1.5** — A-MEM auto-keywords/links no ingest (funde Fase 1.7b dormente) | **6-8h líquidos** | ver **Section 9** + analysis note. Decisão prévia: 1.7b morta vs W1.5 é versão executável. |

### WAVE 2 — Jun-Jul 2026 (depende eval harness ready) — 14-20h

| ID | Item | Esforço | Notas |
|---|---|---|---|
| **W2.1** | Eval harness completo — 50 golden queries + nDCG@10 + MRR | **14-20h** (subestimado original 10h) | Schema migration v12: tabela `eval_queries(id, text, expected_chunk_ids, tags)`. Curadoria 50 queries (Toto sozinho ~6h, ou crowdsource Cipher/Atlas). Self-judge bias documentado. Baseline FTS-only vs hybrid. CLI `nox-mem eval run` + JSONL out. CI gate opcional. |
| **(candidate)** | **W2.2** — Consolidation merge + contradiction detection (funde W1.1) | **+3-4h líquidos** | ver **Section 9** + analysis note. Mandatory `withOpAudit()` + dry-run + canary extension. Depende W2.1 publicar nDCG@10. |

**Cortado:**
- ~~W2.2 Bridge mode docs~~ → fundido em W3.1 (paper v2)
- ~~W2.3 Tool/Skill map~~ → DEFER ≥6mo até existir caso de uso concreto

### WAVE 3 — Ago 2026 (pré-NOX-Supermem) — 5-8h

| ID | Item | Esforço | Notas |
|---|---|---|---|
| **W3.1** | Paper v2 update — Affective Ranking + Multi-Agent Federation + Bridge Mode | **5-6h** (subestimado original 3h) | Update do `paper-tecnico-nox-mem.md/.docx` v3.0.0 (stale). 3 seções novas + diagramas. Affective Ranking depende W2.1 (sem dados eval, é vapor); outras 2 já têm dados. |

**Cortados definitivamente:**
- ~~W3.2 Plugin hooks (onIngest, onRelation)~~ → YAGNI clássico (n=1 consumer = graphify), aproxima "30 MCP tools" proibidos. Se valor aparecer pós-NOX-Supermem multi-tenancy, retomar como design-doc only (2h).
- ~~W3.3 Group routing v2 (frontmatter tag)~~ → contradiz Seção 1 deste mesmo doc + viola Decisão #4 SOUL.md. **CORTADO definitivamente.**

### Wave Gating Métrico (não-calendário)

**Wave 1 → Wave 2:**
- W1.1 atinge ≥80% das ~544 rels classificadas com confidence ≥0.7 em shadow-mode por ≥7d
- W1.2 + W1.3 + W1.4 rodaram ≥3x em uso real sem falso-positivo
- 50 golden queries curadas e validadas

**Wave 2 → Wave 3:**
- nDCG@10 baseline publicado em `/api/health.evalMetrics`
- 1 incident-free month pós-W1 (zero regressão em search_telemetry)
- Affective Ranking validado com salience ativa (gate 04-30 deu OK)

**Kill switches:**
- W1.3/W1.4 não usados ≥3x/semana após 30d → archive feature
- W2.1 não conseguir 50 queries em 2 semanas → reduzir pra 20 + accept lower power
- Health: salience delta ≥5%, vectorCoverage <99%, ou confidence distribution bimodal extrema → PAUSE wave + investigar

### Wave totals consolidados

| Wave | Items | Esforço realista | Cortado/deferred |
|---|---|---|---|
| W1 | W1.1, W1.2, W1.3, W1.4 | 27-30h | — |
| W2 | W2.1 | 14-20h | W2.2, W2.3 |
| W3 | W3.1 | 5-8h | W3.2, W3.3 |
| **Total** | **6 items** | **46-58h** | 4 items removidos (15h fantasia eliminados) |

**Recomendação dos agents:** se margem ficar apertada após Tier 2 + hardening, defer **W1.4** (4h) primeiro — é nice-to-have. W1.1/W1.2/W1.3/W2.1/W3.1 são core.

---

## 8. Próximos Passos Imediatos (executar agora)

1. ✅ Promovido — header atualizado, Section 7 incorporada
2. ⏭ **Adicionar regra #15 ao CLAUDE.md** (próximo commit): "reindex/consolidate/crystallize só com `--dry-run` ou snapshot atômico — lição do incident 2026-04-25"
3. ⏭ **Plano de comunicação executar:** Toto ack hoje → Forge/Cipher quando A1/A2 forem shipados → dashboard quando v1.6 chegar a `main`
4. ⏭ **Anexar v1.6-review.md + section7-validation.md** (ambos no diretório `plans/`) como histórico de decisão
5. ⏭ Atualizar header de `2026-04-19-unified-evolution-roadmap.md` apontando que Phase Matrix está agora canonicalizada em v1.6, mas v1.5 permanece como referência histórica + cross-cutting/decisões válidas/não-fazemos

---

## 9. Candidate Items — Pending POC (ClawMem analysis 2026-04-26)

**Status:** investigation, **NÃO** committed scope. Detalhes em `plans/2026-04-26-clawmem-analysis.md`.

Após análise comparativa de `github.com/yoloshii/ClawMem` (MIT, mesmo nicho OpenClaw) com validation paralela (researcher fact-check + architect + critic), identificados 5 itens candidatos. **Não bumpamos v1.6 nem visão v14** — promoção condicional aos triggers individuais.

### 9.1. Onde cada candidate encaixa no timeline existente

```
HOJE 04-26 ──────┐
                 │ Bloco I (pré-gate)         ✅ A0 A1 A2 A3 A4 A5 DONE
                 │   [holding pattern]
                 │
                 │ Bloco II (gates)            ─── observação shadow ───
                 ├── 04-30  salience activation
                 │   05-01  section_boost decision
                 │   05-02  arquivar 3 source files
                 │
                 │ Bloco III (post-gate)       ◀── A6 + A7 candidates
                 ├── B1 Fase 4 Obsidian (1h)        plug aqui (~05-02→05-08)
                 │   B2 Fase 3 Tier 2 PDFs (dias)
                 │   B3 Backlog #4/#5/#7/#8 (1h45)
                 │   ▸ A6 Entity-Facts SPO Injection (3h)
                 │   ▸ A7 Session Focus Topic Boost (3h + shadow 7d)
                 │
                 │ Wave 1 — Maio 2026          ◀── W1.5 candidate
                 │   W1.1 Edge typing (12-14h)      plug aqui
                 │   W1.2 detect-changes (5-6h)
                 │   W1.3 impact (6h)
                 │   W1.4 api_impact (4h)
                 │   ▸ W1.5 A-MEM keywords (6-8h, funde 1.7b dormente)
                 │
                 │ Wave 2 — Jun-Jul 2026       ◀── W2.2 candidate
                 │   W2.1 Eval harness (14-20h)     plug aqui
                 │   ▸ W2.2 merge+contradiction (3-4h líquidos, funde W1.1)
                 │
                 │ Wave 3 — Ago 2026
                 │   W3.1 Paper v2 (5-6h)
                 │
                 │ Wave 4 hipotética — Set+    ◀── Q5 deferred
                 └── ▸ Q5 Cross-encoder reranker (gated nDCG ≥0.6)
```

### 9.2. Tabela detalhada (4 colunas separadas pra clareza)

| ID | Origem ClawMem (resumo 1-linha) | Encaixe (seção/bloco) | Janela temporal | Métrica de promoção | Decisão prévia |
|---|---|---|---|---|---|
| **A6** candidate | Entity-Facts SPO Injection — bloco `<vault-facts>` no context surface usando KG existente | Bloco III (Section 5), pós-B1/B2/B3 | ≥**2026-05-02** | POC 3h + 7d subjective utility report do Toto | nenhuma — additive, sem overlap |
| **A7** candidate | Session Focus Topic Boost — `focus set <topic>` aplica 1.4× match / 0.75× demote por session | Bloco III (Section 5), pós-B1/B2/B3 | ≥**2026-05-02** | POC 3h + 7d shadow obrigatório → delta recall ≥3% OU clear subjective | nenhuma — fail-open, isolado por session |
| **W1.5** candidate | A-MEM auto-keywords/links — LLM enrich chunks no ingest | Wave 1 (Section 7), funde **Fase 1.7b dormente** (Hierarchical Tagging + Multi-Stage Extraction, `docs/nox-neural-memory.md:660-694`) | **Maio 2026**, paralelo a Tier 2 | shadow 7d obrigatório + feature flag `NOX_AMEM_KEYWORDS=shadow\|active` | **Fase 1.7b está morta ou W1.5 é versão executável dela?** Documentar antes |
| **W2.2** candidate | Consolidation merge + contradiction detection — entity-anchor validation bloqueia merge "Alice/Bob decidiu X" | Wave 2 (Section 7), funde **W1.1** (`relation_reason` enum já inclui `contradicts`) | **Jun-Jul 2026**, depois W2.1 | nDCG@10 publicado em `/api/health.evalMetrics` ≥0.6 + zero false-positive em dry-run 100 chunks | Mandatory `withOpAudit()` + dry-run + canary invariants extension (regra #15) |
| **Q5** deferred | Cross-encoder reranker (Qwen3-Reranker-0.6B via llama-server local) post-RRF | Wave 4 hipotética (não está em Section 7) | ≥**Set 2026** | W2.1 baseline ≥0.6 + caso concreto de query ambígua mal-rankeada documentado | **llama-server local vs cloud API?** + viola SLA L2 (`<2s`) — confirmar trade-off |

### 9.3. NÃO FAZEMOS adicionados (em `plans/2026-04-19-unified-evolution-roadmap.md`)

| Item | Razão (1-linha) |
|---|---|
| Phase 3 deductive synthesis cross-session | LLM confabula sem citation chain rastreável |
| Phase 4 recall stats worker dedicado | `search_telemetry` + `/api/health.searchTelemetry` já cobrem |
| Heavy-lane quiet-window worker | Cron 23:00 unificado + canary `*/15min` cobrem com 10% complexidade |
| Silos schema docs+observations+KG separados | `chunks` canônico evita 3-way drift |

### 9.4. Capacity reality

W1+W2+W3 atuais = **46-58h** pra **~50h** disponíveis até Set/2026. Promover **todos** os 5 candidates sem cortar/recompactar é fantasia. Candidatos a corte/defer se capacity apertar:
- **W1.4** (`api_impact`, 4h, nice-to-have) — primeiro candidato a defer
- **W3.1** (paper v2, 5-6h) — recompactável pra 3-4h sem dados eval
- **Q5** já deferred — não conta no orçamento
