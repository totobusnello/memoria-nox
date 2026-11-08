# Specs — Índice

> Regerado em 2026-11-08 por auditoria contra o código, não a partir do campo `**Status:**` de cada spec.
> Critério: uma spec só conta como entregue se o código for alcançável no pacote npm `nox-mem@3.9.1`
> (`nox-supermem/nox-mem`) ou no código de produção (espelho `nox-workspace/tools/nox-mem`, 31/10;
> A2 conferido na VPS em 08/11). Código em `eval/` ou `staged/` não conta. O `Status` escrito na spec
> é uma afirmação da época; o estado verificado está na primeira linha de cada spec e aqui.
> 57 entradas na pasta `specs/` (o índice anterior, de 2026-05-21, listava 37).

## No produto (npm) (10)

| Spec | Assunto | Estado verificado | Evidência | Falta |
|---|---|---|---|---|
| [2026-05-01-E03a-spo-injection](2026-05-01-E03a-spo-injection.md) | `<vault-facts>` SPO | no npm (e em produção) (default shadow) | N+P `lib/spo-injection.ts`, `api-server.ts:17,401`; `NOX_VAULT_FACTS_MODE` default shadow, `active` only surfaces | E03b activation never decided |
| [2026-05-17-P1-answer-primitive](2026-05-17-P1-answer-primitive.md) | P1 answer | no npm (e em produção) | N+P `api/answer.ts`, `lib/answer/*`, `cli/answer.ts`, wire-up `/api/answer`; N MCP `mcp/tools/answer.ts` | none |
| [2026-05-18-A3-implementation-kickoff](2026-05-18-A3-implementation-kickoff.md) | A3 provider abstraction | no npm (e em produção) | N `providers/`, `NOX_EMBEDDING_PROVIDER` in `search.ts`, `embed.ts`; P has `providers/` but `embed.ts` does not use it (ROADMAP v6 ❌ prod) | port to prod |
| [2026-05-20-mutual-exclusion-section-source-type](2026-05-20-mutual-exclusion-section-source-type.md) | hard mutex | no npm (e em produção) | N+P `search.ts:65,153` default ON (`NOX_DISABLE_MUTEX_SECTION_SOURCE_TYPE`) | none |
| [2026-05-21-G10d-conditional-mutex-by-query-entities](2026-05-21-G10d-conditional-mutex-by-query-entities.md) | G10d | no npm (e em produção) | N+P `search.ts` conditional by `countQueryEntities` (`query-entity-count.ts` imported), `NOX_MUTEX_QUERY_ENTITY_THRESHOLD`, `NOX_DISABLE_CONDITIONAL_MUTEX` | INDEX wrong |
| [2026-05-30-vec0-load-source-fix-migration](2026-05-30-vec0-load-source-fix-migration.md) | vec0 load in db.ts | no npm (e em produção) | N `db.ts:106` and P `db.ts:78` load sqlite-vec before schema | none |
| [2026-06-04-F1-api-brief-implementation](2026-06-04-F1-api-brief-implementation.md) | /api/brief | no npm (e em produção) | N+P `api/brief.ts` imported by `api-server.ts` | none |
| [2026-06-05-cipher-simbiose-itens-1-2-3](2026-06-05-cipher-simbiose-itens-1-2-3.md) | Cipher plan | no npm (e em produção) (item 2 churn); items 1/3 = data/SOUL docs in VPS workspace | N+P `churn.ts`, `index.ts` `--changed-since` | items 1/3 unverifiable here |
| [2026-06-07-D2-brief-diversity-term](2026-06-07-D2-brief-diversity-term.md) | D2 diversity | no npm (e em produção) (default off), active in prod | N+P `api/brief-diversity.ts`; HANDOFF:4181 `NOX_BRIEF_DIVERSITY=active` | pain-floor question open (DECISIONS ~2319) |
| [E12-followup-requesting-agent-migration](E12-followup-requesting-agent-migration.md) | `requesting_agent` | no npm (e em produção) | `search.ts` writes it N+P; `E12-followup-implementation/deployment-log.md` 2026-05-04; nox-workspace#55, nox-mem#43 | INDEX wrong |

## Só em produção, fora do npm (11)

| Spec | Assunto | Estado verificado | Evidência | Falta |
|---|---|---|---|---|
| [2026-04-27-R01a-eval-harness](2026-04-27-R01a-eval-harness.md) | R01a eval harness | só em produção (fora do npm) | P `lib/eval.ts`, `eval-metrics.ts`, imported by `api-server.ts:18`; harness in memoria-nox/eval; not in N | none (npm omission is by choice?) |
| [2026-05-01-F10-observability-dashboard](2026-05-01-F10-observability-dashboard.md) | F10 dashboard | só em produção (fora do npm) | DECISIONS D53: Phase A (#207) + B (#212) LIVE; P `observability/` 17 files, imported by `api-server.ts`; N has only slim `observability.ts` | none |
| [2026-05-07-E12-tier3-ocr](2026-05-07-E12-tier3-ocr.md) | E12 OCR | só em produção (fora do npm) | P `lib/ocr-detector/ocr-jobs/ocr-engines`, `cli/ocr-batch.ts`, `lib/ingest-router.ts` imports; N none | npm gap only |
| [2026-05-17-A2-export-import](2026-05-17-A2-export-import.md) | A2 export/import | só em produção (fora do npm) (HTTP POST /api/export and /api/import, confirmed on the VPS 2026-11-08; no CLI) | P `api/export.ts`, `lib/archive/*`, wire-up `/api/export`+`/api/import` (503 if `lib/archive/server-deps.js` absent; present in P dist); no CLI registered in P `index.ts`; N none; ROADMAP v6 says ❌ in prod (contradicts); in git since 7fdaab4f 2026-05-19 | confirm on VPS; npm port |
| [2026-05-17-L2-conflict-detection](2026-05-17-L2-conflict-detection.md) | L2 conflict | só em produção (fora do npm) | P `lib/conflict/*`, `api/conflict.ts`, `cli/conflict.ts`, `mcp/tools/conflict.ts`, wire-up `/api/conflict`; N only a string in `api/brief.ts`; HANDOFF/DECISIONS silent on live use | no usage evidence; README says "specced" |
| [2026-05-17-P2-hooks-autocapture](2026-05-17-P2-hooks-autocapture.md) | P2 autocapture | só em produção (fora do npm) (partial) | P `lib/hooks/*`, `plugins/nox-hooks`, `cli/hooks.ts`, `/api/hooks/*`; N only `api/ingest-event.ts` (digest). DECISIONS 2026-06-04: full autocapture GATED/NÃO FAZEMOS; ROADMAP #10 reopens it | full capture stays gated |
| [2026-05-17-P5-viewer-realtime](2026-05-17-P5-viewer-realtime.md) | P5 SSE viewer | só em produção (fora do npm) | P `lib/viewer/*`, `api/events-stream*.ts`, `viewer-static.ts`, `cli/viewer.ts`, `/api/events/stream`; N none; staged/P5 | npm gap; `lib/events/bus` has no importers |
| [2026-05-24-A2-tier3-crypto-audit-RECON](2026-05-24-A2-tier3-crypto-audit-RECON.md) | A2 Tier 3 | só em produção (fora do npm) (P1-P4; P5 deferred) | DECISIONS D54-58, memoria-nox CLAUDE.md; P `lib/archive`, `op-audit-extension`, `atomic-snapshot`, `cli/snapshot-main.ts` | P5 deferred |
| [2026-06-04-session-priming-loop](2026-06-04-session-priming-loop.md) | session priming | só em produção (fora do npm) (Phase 1 only) | brief + `nox-mem-brief-refresh.sh` cron (P tools/nox-mem, not in N); `session-distill` in index; 7b/ROADMAP #7 shows brief does not steer first action | Phases 2-4 unclear |
| [2026-07-25-P2S1-serving-side-snapshot](2026-07-25-P2S1-serving-side-snapshot.md) | P2 epoch serving | só em produção (fora do npm) retired | P `lib/epoch-serving/shadow/snapshot.ts`; memoria-nox CLAUDE.md: epoch rotation disabled 2026-10-26 (openclaw-vps#63), `mode: "off"` | dead code candidate |
| [2026-08-18-P2S2-outcome-write-path](2026-08-18-P2S2-outcome-write-path.md) | P2 write path | só em produção (fora do npm) | P `paper2/write-path.ts`, `api-server.ts:25,536` `/internal/paper2/adjudicated-failure`; spec says "Nada implantado" | ensaio closed 21/09; consider removal |

## Seguem a spec-mãe (kickoffs) (4)

| Spec | Assunto | Estado verificado | Evidência | Falta |
|---|---|---|---|---|
| [2026-05-18-A2-implementation-kickoff](2026-05-18-A2-implementation-kickoff.md) | A2 kickoff | segue a spec-mãe A2 (SHIPPED-prod-only) + A2 Tier 3 | see A2 / RECON rows | INDEX stale |
| [2026-05-18-P1-implementation-kickoff](2026-05-18-P1-implementation-kickoff.md) | P1 kickoff | segue a spec-mãe P1 (SHIPPED-npm) |  | INDEX stale |
| [2026-05-18-P2-implementation-kickoff](2026-05-18-P2-implementation-kickoff.md) | P2 kickoff | segue a spec-mãe P2 |  | INDEX stale |
| [2026-05-18-P5-implementation-kickoff](2026-05-18-P5-implementation-kickoff.md) | P5 kickoff | segue a spec-mãe P5 (prod-only) |  | INDEX stale |

## Código existe mas não é alcançável (4)

| Spec | Assunto | Estado verificado | Evidência | Falta |
|---|---|---|---|---|
| [2026-04-12-self-evolving-hooks](2026-04-12-self-evolving-hooks.md) | SEH hooks | código existe, não alcançável (module orphan) | `seh-detector.ts` in N and P, 0 non-test importers, no CLI/cron/route; header cites F15b | wire or delete |
| [2026-05-18-L4-regex-first-extraction](2026-05-18-L4-regex-first-extraction.md) | L4 regex-first | código existe, não alcançável (code present, unreachable) | N and P `lib/regex-extract/*` 9 files, 0 importers outside module; `production-wire.ts` header says "ingestFile() router imports this", but `ingest-router.ts` never did (`git log -S"regex-extract"` empty); `kg-llm.ts` doesn't call it | wire into ingest/kg-build or drop; DECISIONS D52 "L4 fires 05-24" not supported by code |
| [2026-05-18-P6-mobile-sync](2026-05-18-P6-mobile-sync.md) | P6 mobile | código existe, não alcançável | `staged/P6-mobile` (app, packages) only | no decision |
| [2026-05-18-P7-browser-extension](2026-05-18-P7-browser-extension.md) | P7 extension | código existe, não alcançável | `staged/P7-browser-extension` only | no decision |

## Só no harness de eval (resultado de pesquisa) (5)

| Spec | Assunto | Estado verificado | Evidência | Falta |
|---|---|---|---|---|
| [2026-05-28-adaptive-query-classifier](2026-05-28-adaptive-query-classifier.md) | Lab Q1 #1 | só no harness de eval | `eval/evermembench/query_classifier.py`; grep `NOX_ADAPTIVE_CLASSIFIER` N/P NONE | ROADMAP: "resultado de pesquisa" |
| [2026-05-28-kg-path-retrieval](2026-05-28-kg-path-retrieval.md) | KG path | só no harness de eval | `adapter_nox_mem_phaseAC_kg.py`; grep `NOX_KG_PATH_ENABLED` N/P NONE; D75 −0.01pp | port only if ROADMAP #1 candidate |
| [2026-05-28-ma-protection-rerank](2026-05-28-ma-protection-rerank.md) | MAP | só no harness de eval | `aggregate_phaseMAP_5batch.py`, RESULTS-PHASEMAP-5BATCH; `NOX_MA_PROTECTION*` N/P NONE | Lab, parked |
| [2026-05-28-multi-query-expansion](2026-05-28-multi-query-expansion.md) | MQ | só no harness de eval | `aggregate-phaseMQ.py`, RESULTS-PHASEMQ-5BATCH; `NOX_MQ_ENABLED` N/P NONE (prod `search-expansion.ts` is different, FTS query expansion) | none |
| [2026-05-29-iterative-retrieval-q3](2026-05-29-iterative-retrieval-q3.md) | IterB/Self-Ask | só no harness de eval | RESULTS-Q3-ITER*; ROADMAP §5 "saiu do roadmap" | none |

## Medição concluída (6)

| Spec | Assunto | Estado verificado | Evidência | Falta |
|---|---|---|---|---|
| [2026-05-10-E14-retrieval-evolution](2026-05-10-E14-retrieval-evolution.md) | E14 retrieval evolution | medição concluída | spec: levers A1/A2/FTS expansion refuted; lever D "language-aware RRF" only in eval (grep `NOX_LANG_AWARE_RRF` N/P NONE); ROADMAP v6 table; D01 v3 Wave 2 on hold -> ROADMAP §5 out | nothing as product |
| [2026-05-18-Q1-Q2-Q3-vps-scheduling](2026-05-18-Q1-Q2-Q3-vps-scheduling.md) | Q1-Q3 scheduling | medição concluída | eval/locomo, longmemeval, latency exist; COMPARISON.md; Q4 consumed them | close |
| [2026-05-23-Q4-comparison-execution-plan](2026-05-23-Q4-comparison-execution-plan.md) | Q4 plan | medição concluída | eval/q4-comparison, output-2026-09-10 `_aggregate.json`, paper §6.3.3; DECISIONS ~2047 | none |
| [2026-05-28-phase-h-gpt41mini-parity](2026-05-28-phase-h-gpt41mini-parity.md) | Phase H | medição concluída | RESULTS-PHASEH(-v2)(-5BATCH).md, DECISIONS ~1069-1130 | none |
| [2026-10-14-7b-brief-action-probe-design](2026-10-14-7b-brief-action-probe-design.md) | 7b probe | medição concluída | ROADMAP #7, MEMORY: 7b closed 15/10, positive control 0/10 | none |
| [E10-followup-pain-ablation-execution](E10-followup-pain-ablation-execution.md) | pain ablation | medição concluída | DECISIONS D29 has E10 results (REFUTED); no `NOX_PAIN` code | close |

## Não começadas (6)

| Spec | Assunto | Estado verificado | Evidência | Falta |
|---|---|---|---|---|
| [2026-05-17-E15-codegraph-inspired-improvements](2026-05-17-E15-codegraph-inspired-improvements.md) | E15 A/B/C | não começado | spec = tier-aware, overflow protection, indexing tiers; no code; ROADMAP §5 "saiu do roadmap"; (impact.ts is E07, unrelated) | nothing, retired |
| [2026-05-17-P4-connect-ide](2026-05-17-P4-connect-ide.md) | `nox-mem connect` | não começado | grep `connect` N/P/staged NONE; ROADMAP v6 ❌❌ | spec only |
| [2026-05-18-P4-implementation-kickoff](2026-05-18-P4-implementation-kickoff.md) | P4 kickoff | não começado |  |  |
| [2026-05-21-per-method-benchmark-comparison](2026-05-21-per-method-benchmark-comparison.md) | per-method benchmark | não começado | no artifact in eval/, docs, HANDOFF | gated on D49 phase 2, which is dead (#33) |
| [2026-05-24-per-method-benchmark-phase-b](2026-05-24-per-method-benchmark-phase-b.md) | Phase B ablation | não começado | same as above | same |
| [2026-05-29-profile-chunk-identification-q2](2026-05-29-profile-chunk-identification-q2.md) | profile chunk | não começado | no artifact (DECISIONS:1385 lists "profile-chunk" as untried mechanism class) | Lab idea |

## Cortadas por decisão ou superadas (10)

| Spec | Assunto | Estado verificado | Evidência | Falta |
|---|---|---|---|---|
| [2026-05-01-E04a-focus-boost](2026-05-01-E04a-focus-boost.md) | focus boost | cortado por decisão | DECISIONS D36 (CUT permanent, code removed: focus.ts, CLI); grep NONE in N/P | none |
| [2026-05-06-E05b-reason-ranking-boost](2026-05-06-E05b-reason-ranking-boost.md) | E05b reason boost | cortado por decisão | P `search.ts:606` "CUT E05b reason-boost"; only trace is `reason_boost_*` columns in `db.ts:213`; grep search.ts NONE | none; INDEX wrong |
| [2026-05-06-E13-temporal-aware-ranking](2026-05-06-E13-temporal-aware-ranking.md) | E13 temporal ranking | cortado por decisão (module dead) | `lib/temporal-detector.ts` imported only by its test (N and P); ROADMAP v6: `NOX_TEMPORAL_BOOST_MODE` removed 14/10; NÃO FAZEMOS #33 | none; INDEX wrong |
| [2026-05-07-D01-cross-encoder-reranker](2026-05-07-D01-cross-encoder-reranker.md) | D01 cross-encoder | cortado por decisão (residual dead module) | spec says "sem dead code" but `lib/reranker.ts` exists in N and P; only use is startup pre-warm when `NOX_RERANKER_MODE`!=off (`api-server.ts:503`); `search.ts` never calls it | delete `lib/reranker.ts` + prewarm, or admit it |
| [2026-05-17-L3-confidence-field](2026-05-17-L3-confidence-field.md) | L3 confidence | cortado por decisão (ranking) + partial shipped | NÃO FAZEMOS #34 (D-2026-10-20: 100% default values); P keeps `lib/confidence/db-shim`, `mark`, `/api/health/confidence`; ranking modules deleted (nox-workspace#65) | none |
| [2026-05-21-neural-reranker-design](2026-05-21-neural-reranker-design.md) | D01 v3 bge-v2-m3 | cortado por decisão | D-2026-09-21c; ROADMAP §5 "reranker no caminho default" out; NÃO FAZEMOS #31, DECISIONS §2 | none |
| [E12-followup-implementation/](E12-followup-implementation/) | patches | superado | patches applied (deployment-log) | archive |
| [d50-template](d50-template.md) | D50 | superado | D-2026-10-14b NÃO FAZEMOS #33 | close |
| [d51-template](d51-template.md) | D51 | superado by G10d shipped | G10d row | close |
| [temporal-retrieval-path-spike](temporal-retrieval-path-spike.md) | D49 spike | cortado por decisão (code residual) | `temporal-retrieval.ts` in `search.ts` only logs, does not mutate; drop-in removed 14/10; NÃO FAZEMOS #33 | optional cleanup |

## Outras (1)

| Spec | Assunto | Estado verificado | Evidência | Falta |
|---|---|---|---|---|
| [2026-05-17-GTM-readme-hero-upgrade](2026-05-17-GTM-readme-hero-upgrade.md) | README hero | parcial (partial, hero only) | memoria-nox/README.md has banner/badges/demo.gif/assets/readme; but D-2026-11-03/-04: GTM gate re-evaluated, first step = fix discourse | fix numbers in hero before GTM |

## Status do índice anterior que estavam errados

E05b e E13 estavam como Done e foram cortados (E13: o módulo só é importado pelo teste). E04a estava como
Deferred «sem impl» e foi cortado (D36). F10, G10d e o E12-followup estavam como Active e já estão no
código. L3 estava Active e o ranking por confiança foi cortado (NÃO FAZEMOS #34). E10-followup estava
Blocked e a medição foi feita (D29). O d50-template foi decidido (NÃO FAZEMOS #33). 21 specs não constavam.

## Divergências que ficaram para decisão

- **L4** (`lib/regex-extract`, 9 arquivos): presente no npm e em produção, sem nenhum importador fora do
  módulo; o cabeçalho de `production-wire.ts` afirma uma ligação com o `ingestFile()` que nunca existiu, e
  `NOX_L4_REGEX_ENABLED` não tem efeito. Ligar ou remover.
- **`lib/reranker.ts`** (D01, cortado): só é usado pelo aquecimento na subida do `api-server`, que só roda
  com `NOX_RERANKER_MODE` diferente de `off` (em produção é `off`). A busca nunca o chama.
- **Sem importador fora de teste nos dois códigos:** `temporal-detector.ts`, `seh-detector.ts`,
  `lib/events/bus.ts`, `impact.ts`, `detect-changes.ts`, `lib/cost-cap.ts`, `graphify-ingest.ts` (alguns
  podem ser chamados por script ou cron; não conferido).
- **npm × produção:** A3 só no npm (o `embed.ts` de produção não usa `providers/`); L2, P5, hooks, A2 e OCR
  só em produção.

*Nova spec: `specs/AAAA-MM-DD-<ID>-<slug>.md`, com a linha de estado verificado logo abaixo do título,
atualizada quando o estado mudar, e uma linha neste índice.*
