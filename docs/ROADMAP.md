# nox-mem ROADMAP — single source of truth

> **Canônico desde 2026-04-27.** Substitui `plans/2026-04-25-integration-roadmap-v1.6.md` como referência operacional.
> v1.6 e v1.5 ficam em `plans/_archive/` como referência histórica de decisão.
> Para "por que" qualquer decisão → `docs/DECISIONS.md`.
> Para estado atual + próximo passo → `docs/HANDOFF.md`.

---

## 1. Estado atual (snapshot)

```
Sistema:        nox-mem v3.7+, schema v10, ops_audit append-only
Chunks:         20831 (99.2% embedded, 0 orphans)
DB size:        318MB
Agentes:        6 personas + main, cross-search ativo
OpenClaw:       v2026.4.23 (.24 quebrado, .25-stable aguardada)
Improvements:   13/13 OK (audit baseline)
Última sessão:  2026-04-26 (hardening + audit triplo + Fase 4 Obsidian)
```

## 2. Calendário cronológico — UMA tabela mestre

Velocity real medida (Bloco I): **~0.6× dos estimates conservadores originais**. Horas abaixo já recalibradas.

### Status enum
- ✅ `DONE` — entregue, validado em produção
- ⏳ `GATED` — esperando trigger (data específica ou condição)
- 📋 `QUEUED` — pronto pra executar quando bloco abrir
- 🤔 `CANDIDATE` — em validation, precisa POC antes de committed scope
- 🛑 `DEFERRED` — adiado com trigger explícito de revisão
- ❌ `CUT` — não fazemos (ver DECISIONS.md)

### Tabela mestre

Estimates **recalibrados pela velocity real medida** (Bloco I + 04-26 day): feature novo ~0.4×, hardening/security ~1.0×, I/O-bound ~0.6×. Coluna `h` é o esforço esperado pra você executar, não fantasia.

| Janela | ID canônico | Aliases | Item | Status | h (real) | Trigger / Gate |
|---|---|---|---|---|---|---|
| 04-25 | **A0** | v1.5 Fase 1.6 ext | Query logging + golden-tag (search_telemetry +4 cols) | ✅ DONE | 1 | — |
| 04-25 | **A1** | v1.5 Path A reativo | Audit log + `withOpAudit` (v1+v2 hardened) | ✅ DONE | 4 | incident 04-25 |
| 04-25 | **A2** | v1.5 ingest split | Ingest-router unified (`routeIngest`) | ✅ DONE | 1 | incident 04-25 |
| 04-25 | **A3** | Backlog #1 | Unit tests `parseRetentionOverride` (20 cases) | ✅ DONE | 0.4 | — |
| 04-25 | **A4** | — | Canary invariants ext (5 invariants */15min) | ✅ DONE | 0.5 | — |
| 04-25 | **A5** | pattern externo | Dry-run mode (reindex+consolidate) | ✅ DONE | 1 | — |
| 04-26 | **B1** | v1.5 Fase 4 | Fase 4 Obsidian view-only (430 LOC + cron+launchd) | ✅ DONE | 1 | A1-A5 done |
| 04-26 | **B3** | Backlog #4/5/7/8 | Sprint 7/8 (issue + CONVENTIONS + alert + playbooks) | ✅ DONE 7/8 | 1.5 | — |
| 04-26 | **upgrade-defense** | — | ckpt + improvements + watcher + oc-upgrade orchestrator | ✅ DONE | 4 | OpenClaw .24 break |
| **04-30** | **gate.salience** | v1.5 Fase 1.7b-b | `activate-salience.sh --apply` se baseline 7d OK | ⏳ GATED | 0.1 | 7d shadow OK |
| **05-01** | **gate.section_boost** | — | `analyze-shadow-telemetry.sh 7` → decidir activate | ⏳ GATED | 0.3 | 7d shadow telemetry |
| **05-02** | **gate.archive_3files** | — | Arquivar 3 source files `.archived-20260502` | ⏳ GATED | 0.1 | gates anteriores OK |
| ≥05-02 | **A6** | ClawMem Q1; Section 9 | Entity-Facts SPO Injection (`<vault-facts>` via KG) | 🤔 CANDIDATE | 1.5 | POC + 7d subjective utility |
| ≥05-02 | **A7** | ClawMem Q2; Section 9 | Session Focus Topic Boost (`focus set <topic>`) | 🤔 CANDIDATE | 1.5 | POC + 7d shadow; delta ≥3% |
| ≥05-02 | **B3.last** | Backlog #8 | Último item residual do backlog | 📋 QUEUED | 0.3 | — |
| 05-02→05-15 | **B2** | v1.5 Fase 3 Tier 2 | PDFs text-layer ingest (4432 PDFs HD Mac) | 📋 QUEUED | **15** (I/O) | gates passados; paralelo a infra |
| Maio | **W1.1** | v1.6 Wave 1 | Edge typing FULL — `relation_reason` enum 7 + `confidence` | 📋 QUEUED | **5-6** | shadow 7d antes ranking |
| Maio | **W1.2** | Wave 1 | `nox-mem detect-changes --since=<commit>` | 📋 QUEUED | **2-3** | — |
| Maio | **W1.3** | Wave 1 | `nox-mem impact <entity>` 1-hop blast radius | 📋 QUEUED | **2.5** | W1.1 ready |
| Maio | **W1.4** | Wave 1 | `nox-mem api_impact` multi-arquivo | 📋 QUEUED | **1.5** | nice-to-have (defer 1º) |
| Maio | **W1.5** | ClawMem Q3; v1.5 Fase 1.7b dormente | A-MEM auto-keywords/links no ingest | 🤔 CANDIDATE | **3-4** | doc 1.7b vs W1.5; shadow obrigatório |
| Jun-Jul | **W2.1** | Wave 2; Backlog #2 | Eval harness (50 golden, nDCG@10, MRR) | 📋 QUEUED | **7-9** | A0 corpus ready |
| Jun-Jul | **W2.2** | ClawMem Q4; funde W1.1 | Consolidation merge + contradiction detection | 🤔 CANDIDATE | **1.5-2** | W2.1 nDCG≥0.6 + dry-run zero FP |
| Ago | **W3.1** | Wave 3; Paper v2 | Paper update (Affective + Federation + Bridge) | 📋 QUEUED | **2.5-3** | W2.1 published |
| Set+ | **C1** | v1.5 Path B-lite | Reflect cache (semantic key) | 📋 QUEUED | **1.5** | 7d telemetria reflect |
| Set+ | **C2** | v1.5 SEH | Self-Evolving Hooks | 📋 QUEUED | **1** | — |
| Set+ | **C3** | v1.5 Tier 3 | OCR + Fathom + Path C (opcional) | 📋 QUEUED | dias | — |
| Set+ | **C4** | v1.5 Fase 4b/5/P | NOX-Supermem productização | 📋 QUEUED | semanas | Fase 4 estável 30d |
| Set+ | **Q5** | ClawMem cross-encoder | Cross-encoder reranker (Qwen3 local) | 🛑 DEFERRED | dias | W2.1 nDCG≥0.6 + caso real |

## 3. Capacity tracker (recalibrado pela velocity real)

```
Disponível 04-27 → 09-30:        ~50h (10h/sem, otimista)
Margem incident reservada:       ~5h
Capacity líquida:                ~45h

Compromissado núcleo (estimates recalibrados @velocity real):
  B2 Tier 2 PDFs (I/O):          15h    ← paralelo a infra
  B3 #8 último:                  0.3h
  Gates 04-30/05-01/05-02:       0.5h
  W1.1 + W1.2 + W1.3:            9.5-11.5h
  W1.4 (defer candidato):        1.5h
  W2.1 eval harness:             7-9h
  W3.1 paper:                    2.5-3h
                                 ───────
Subtotal núcleo:                 36-41h

Candidates Section 9 (validation pendente):
  A6 + A7:                       3h
  W1.5 (funde 1.7b):             3-4h
  W2.2 (funde W1.1):             1.5-2h
                                 ───────
Subtotal candidates:             7.5-9h

Bloco V (Set+, opcional):
  C1 + C2:                       2.5h
  C3/C4:                         out-of-budget
                                 ───────

TOTAL líquido NÚCLEO + candidates + C1/C2:  46-52.5h
```

**Análise:**
- **Sem candidates:** 36-41h vs 45h disponível → **sobra 4-9h** (margem confortável)
- **Com TODOS candidates A6/A7/W1.5/W2.2:** 43.5-50h vs 45h → **sobra -5 a +1.5h** (apertado mas viável)
- **B2 PDFs paralelizável** (I/O bound enquanto você trabalha em outras coisas) — não conta serial → realmente 21-26h em "trabalho ativo"

**Decisões obrigatórias:**
- ✅ **Defer W1.4** (1.5h, nice-to-have) — primeiro corte se apertar
- ✅ **Recompactar W3.1** pra 2.5h se sem dados eval
- ✅ **Promover A6 + A7 candidates** post-gate (3h total, additive, baixo risco)
- 🤔 **W1.5/W2.2 candidates entram se sobrar 7h pós-W1 core** (60% likely)
- ✅ **C3/C4 fora do orçamento Maio-Ago** — horizonte Set+ separado

## 4. Gates ativos (próximos 5 dias)

| Data | Gate | Comando | Critério |
|---|---|---|---|
| 2026-04-30 | salience | `bash /root/.openclaw/scripts/activate-salience.sh check` | "READY: baseline 7d OK" → `--apply` |
| 2026-05-01 | section_boost | `bash /root/.openclaw/scripts/analyze-shadow-telemetry.sh 7` | Decidir `NOX_SECTION_BOOST_MODE=active` |
| 2026-05-02 | archive 3 source files | manual mv `.archived-20260502` | Após 2 gates anteriores OK |

## 5. Cortados / Deferred (com trigger pra reavaliar)

Razões completas em `docs/DECISIONS.md` § NÃO FAZEMOS.

| ID | Item | Decisão | Trigger pra reavaliar |
|---|---|---|---|
| Q5 | Cross-encoder reranker (Qwen3 local) | 🛑 DEFERRED | W2.1 nDCG ≥0.6 + caso ambíguo doc + decisão local-vs-cloud |
| Group routing | `@group`, `groups.yaml` | ❌ CUT | Se aparecer dor → açúcar de `cross-search` |
| W3.2 | Plugin hooks (`onIngest`, `onRelation`) | ❌ CUT | Pós-NOX-Supermem multi-tenancy |
| W3.3 | Group routing v2 (frontmatter tag) | ❌ CUT | — (mesmo que group routing) |
| W2.2 orig | Bridge mode docs | ❌ CUT (fundido em W3.1) | — |
| W2.3 | Tool/Skill map | 🛑 DEFER ≥6mo | Caso de uso concreto aparecer |
| Phase 3 deductive synth | Cross-session insights | ❌ CUT | LLM confabula sem citation |
| Phase 4 recall worker | Stats dedicado | ❌ CUT | search_telemetry já cobre |
| Heavy-lane worker | Quiet-window | ❌ CUT | Cron 23:00 + canary já cobrem |
| Silos schema | docs+observations+KG | ❌ CUT | chunks canônico evita drift |
| 30 MCP tools | gbrain pattern | ❌ CUT | Cap em 16, capabilities via search |
| Memgraph/Neo4j | Graph DB dedicado | ❌ CUT | >500K entities |
| Postgres/PGLite | gbrain engine | ❌ CUT | >500K entities |

## 6. Wave gating métrico (não calendário)

**Wave 1 → Wave 2:**
- W1.1 atinge ≥80% das ~544 rels classificadas com confidence ≥0.7 em shadow-mode por ≥7d
- W1.2 + W1.3 + W1.4 rodaram ≥3x em uso real sem falso-positivo
- 50 golden queries curadas e validadas

**Wave 2 → Wave 3:**
- nDCG@10 baseline publicado em `/api/health.evalMetrics`
- 1 incident-free month pós-W1
- Affective Ranking validado com salience ativa (gate 04-30 OK)

**Kill switches:**
- W1.3/W1.4 não usados ≥3x/semana após 30d → archive feature
- W2.1 não consegue 50 queries em 2 semanas → reduzir pra 20 + accept lower power
- Health: salience delta ≥5%, vectorCoverage <99%, ou confidence distribution bimodal extrema → PAUSE wave + investigar

## 7. Cross-ref ID systems (decoder)

| ID v1.6 | ≡ ID v1.5 | ≡ ClawMem | ≡ vision v14 |
|---|---|---|---|
| A0 | Fase 1.6 ext | — | — |
| A1 | Fase 1 hardening | — | — |
| A2 | (novo, ingest split) | — | — |
| A6 | (novo) | Q1 | — |
| A7 | (novo) | Q2 | — |
| W1.1 | Fase 1.7b-edge | — | — |
| W1.5 | Fase 1.7b dormente | Q3 | linhas 660-694 |
| W2.1 | Fase eval | — | — |
| W2.2 | Fase merge | Q4 | — |
| W3.1 | Paper v2 | — | — |
| Q5 | — | Q5 | — |

## 8. Próximo passo concreto (referência rápida)

Hoje é **2026-04-27**. Em ordem:

1. **Aguardar gates 04-30 / 05-01** (3-4 dias) — não tocar shadow telemetry
2. **Trabalho hoje (opcional, baixo risco):**
   - Design A6 + A7 POC specs (pré-execução pós-gate)
   - Decisão "1.7b dormente vs W1.5 executável" (destrava Maio)
   - Wave 3 cleanup (test isolation + 5 LOW polish)
   - B3 #8 último item
3. **05-02:** executar gates archive + iniciar A6/A7/B2 paralelo
4. **Maio:** W1.1 → W1.2 → W1.3, com B2 PDFs paralelo
5. **Jun-Jul:** W2.1 (eval) + W2.2 candidate
6. **Ago:** W3.1 paper

Este arquivo é a fonte mestre. Cross-refs:
- **DECISIONS.md** — por que cortamos coisas, decisões arquiteturais
- **HANDOFF.md** — estado vivo, próxima sessão
- **CLAUDE.md** — regras críticas operacionais 1-15
- **plans/_archive/** — v1.6, v1.5, ClawMem analysis (referência histórica)
