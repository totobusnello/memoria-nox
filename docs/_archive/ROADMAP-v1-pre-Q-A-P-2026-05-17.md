# nox-mem ROADMAP — single source of truth

> **Canônico desde 2026-04-27.** Sistema unificado de IDs (F/E/R/P/G/D) substitui os 6+ namespaces antigos (A/B/W/Q/Fase/Phase). Cross-ref em §8.
> **Última atualização:** 2026-05-04 marathon W1 Day 1+2 (~24h): BM25 baseline 0.1475 + pain baseline 0.2689 + E5 multilingual running + paper §1-7 draft completo + LaTeX template + 4 figuras + distribuição completa. BGE-M3 CUT (CPU inviável); E12 retrieval e E10 pain ablation em backlog.
> Para "por quê" de qualquer decisão → `docs/DECISIONS.md`. Para estado atual → `docs/HANDOFF.md`.

---

## 1. Estado atual (snapshot 2026-05-17 noite)

```
Sistema:        nox-mem v3.7+, schema v18 (PRAGMA user_version aligned), ops_audit append-only
Chunks:         69.298 (99.97% embedded, Gemini 3072d) — fts_anchor populated (E-lite-2 ACTIVE)
DB size:        ~1.24 GB
KG:             15.646 entities / 21.533 relations
Agentes:        7 (1 main Maestro + 6 personas: nox/atlas/boris/cipher/forge/lex)
OpenClaw:       v2026.4.29
Eval nDCG@10:   0.6813 (n=78 honest golden set, run 85)
Vs paper baseline (0.5831): +16.9% relativo / +9.8pp absoluto

Features ranking ATIVAS (5):
 ✅ Salience (recency × pain × importance) — G01 2026-04-30
 ✅ Section boost (compiled +100%, frontmatter +49%) — G02 2026-05-01
 ✅ Edge typing (relation_reason enum 7) — E05 Phase 1 2026-05-02
 ✅ Temporal boost (E13) — 2026-05-06
 ✅ SPO Injection (E03b, integrated em CLI) — 2026-05-17 (D37 superseded)
 ✅ E-lite-2 (fts_anchor bilingual) — 2026-05-17 (Wave 1 E14)
 ✅ D (language-aware RRF weights) — 2026-05-17 (Wave 1 E14)

Features CORTADAS (lições codificadas):
 ❌ A7 focus topic boost — CUT D36 (consumer absent)
 ❌ E05b reason-boost — CUT D38 (bias arquitetural, 3 rounds gate)
 ⛔ A1/A2/G — DEFERRED PERMANENTE D39 (FTS5 silent design)
 ⛔ D01 cross-encoder v1+v2 — CUT (OOM); v3 Cohere pendente decisão Toto

Schema migrations: v16 → v17 (op-audit gaps) → v18 (fts_anchor) entregues 2026-05-15/17
Tests:          136/211 (pre-existing fails 75, confirmados estáveis pré/pós CUTs)
Capacity:       ~6h/semana realista até Set/2026 (CEO em 5 frentes)
Margem incident: 20h reservadas
```

### Sessão 2026-05-17 delivered (~10h) — Wave 1 E14 completa + D ACTIVE + decisões arquiteturais

Maratona com 8 entregas executadas + 9 tentativas refutadas (todas documentadas).

**Entregas que ficaram:**
- ✅ **E03b SPO injection ACTIVATED** — integrado em `nox-mem search` CLI (flag `--no-vault-facts` opt-out). Smoke OK: 4 entities/7 triples surface em queries entity-rich. D37 superseded. VPS commit `90fa3180`.
- ✅ **E05b reason-boost CUT (D38)** — 3 rounds gate review (06/05 + 16/05 + 17/05), bias arquitetural confirmado (reason_boost amplifica chunks com KG coverage independente da qualidade). Removido 518 LOC. VPS commit `26640d16`.
- ✅ **Golden set expansion 65→80→78 honest** — Cross-language 0→10, cross-agent 4→5/7, temporal 4→6. 4 queries dropped via refinement (qid 117/119/120/122 com gold genérico). 2 cross-language Toto-curadas (qid 125/126).
- ✅ **Schema v17→v18 (fts_anchor column)** — `ALTER TABLE chunks ADD COLUMN fts_anchor` via `withOpAudit` (audit_id=55). VPS commit `b71d4c18`.
- ✅ **E-lite-2 ACTIVE (Wave 1 E14)** — `src/lib/fts-anchor.ts` v4 regex (60 cognates + 35 PT/EN pairs + 25 entities + 8 identifier patterns) + `backfill-fts-anchor` CLI + `e-lite-2-recreate-fts5.mjs`. Backfill 69298 chunks 17.3s. FTS5 recreate 7.2s. **Overall +0.94pp** (0.6644→0.6738). VPS commit `d48b115e`.
- ✅ **D (language-aware RRF) ACTIVE** — `detectQueryLanguage` + `LANG_WEIGHTS` (PT: dense 1.15/fts 0.85; EN/mixed balanced). **Overall +1.92pp ZERO regressão** (0.6605→0.6797). procedure +6.55pp, cross-agent +5.34pp. VPS commit `7dc46fb5`.

**Tentativas REFUTADAS empiricamente (lições):**
- ❌ A2 standalone *4: -6.5pp
- ❌ v5 vocab expansion: -1.2pp (entity -8.7pp, security +3.8pp — net negativo)
- ❌ A1 *15 standalone: -0.7pp
- ❌ A2+D combinado *4: -7.98pp
- ⚠️ A1+D *3 combinado: +0.59pp (noise — média de 3 runs = -0.47pp)
- ❌ FTS5 v1 OR-all: -23.6pp
- ❌ FTS5 v2 AND+OR quoted: -22.5pp
- ❌ FTS5 v3 unquoted: -18.5pp
- ❌ FTS5 v4 confidence-aware (AND=1.0/OR=0.4): -5.4pp

**Decisões arquiteturais codificadas:**
- **D36** A7 focus topic boost CUT (consumer absent)
- **D37** E03b HOLD por consumer absent → SUPERSEDED via CLI integration
- **D38** E05b CUT por bias arquitetural (reason quality > quantity)
- **D39** FTS5 silent design accepted (4 tentativas refutadas, A1/A2/G DEFERRED permanente)

**Estado final consolidado:**
- Overall nDCG@10: **0.6813** (vs paper baseline 0.583 = **+16.9% relativo, +9.8pp absoluto**)
- 5 features ranking ativas
- 9 commits Mac + 6 commits VPS

Cross-link: docs/HANDOFF.md §"RETOMADA"; docs/DECISIONS.md D36-D39; specs/2026-05-10-E14-retrieval-evolution.md.

### Sessão 2026-05-16 delivered (~6h) — op-audit validation + 4 gates fechados

- ✅ **Op-audit overnight validation** — cron snapshot 3am rodou (audit_id=53, 853MB gz), watchdog reaped stale row na 1ª execução real, byDbSource populated.
- ✅ **Gate review E05b silent-fail fix** — cron 13/05 falhou Permission denied (mascarado por `2>&1`). Fixes: chmod +x, parser bug `json_object → json_group_object`, Discord trap pra exit≠0.
- ✅ **E13 temporal-boost ACTIVATE confirmed** — já em prod desde 06/05, gate review validou Δ temporal +0.14.
- ✅ **E04 A7 focus CUT** — 14 dias zumbi, design pressupõe UX inexistente. Removido 519 LOC. VPS commit `128b7065`.
- ✅ **E03b HOLD por consumer absent** — 336/336 logs shadow eram canary. Pré-req ACTIVATE: integrar em consumer real (executado dia seguinte).

Cross-link: docs/DECISIONS.md D36/D37, VPS commit `128b7065`.

### Sessão 2026-05-15 noite delivered (op-audit hardening, 6 fases ~3h vs 5.5h estimado)

Origem: deep triage de 3 alertas (`openclaw-api inactive`, OCR zombies, snapshots 13MB). Investigation expôs que snapshots 13MB eram **sub-DBs legítimos de 6 agentes** (atlas/boris/cipher/forge/lex/nox) — NÃO bug. Mas 4 gaps reais + 1 bonus do Forge identificados e fixed mesma sessão.

- ✅ **Fase 1 — `op-audit.ts` core** — `deriveDbSource()` env primary (`NOX_DB_SOURCE`) + path parse fallback + `'unknown'` final; filename pattern atualizado para `<op>-<dbSource>-<ts>-<pid>-<uid>.db`; `recordHeartbeat()` helper; `OpsAuditStats.byDbSource` interface.
- ✅ **Fase 2 — schema v17** — `migrateToV17()` adiciona `db_source TEXT DEFAULT 'unknown'`, `db_path TEXT DEFAULT 'unknown'`, `last_heartbeat_at TEXT`; DEFAULT backfilla rows existentes sem `UPDATE` (evita conflito com `trg_ops_audit_terminal_immutable`); migration wrapper `migrate-v17-ops-audit.ts` via `withOpAudit` (snapshot `schema-v17-migration-main-...db` 1.24GB).
- ✅ **Fase 3 — OCR safety** — `HARD_TIMEOUT_MS=10800000` (3h, override `OCR_HARD_TIMEOUT_MS`) com `process.exit(124)`; `setInterval(recordHeartbeat, 5min)`; cleanup `clearTimeout`+`clearInterval` em path normal.
- ✅ **Fase 4 — daily main snapshot** — subcomando `snapshot-main.ts` (app context com vec0.so via better-sqlite3, Forge Q1 confirmou que sqlite3 CLI standalone não carrega) + `snapshot-main-db.sh` (gzip -9 ~30s, 72% ratio, retention 5d) + cron `0 3 * * *`; validado 2026-05-16 02:08 BRT (852MB gz).
- ✅ **Fase 5 — nightly + canary integration** — `nightly-maintenance.sh` prefixa `NOX_DB_SOURCE=<agent>` em todas 5 invocações por agente (atlas/boris/cipher/forge/lex/nox) + main; `canary-bundle-15min.sh` invoca `ocr-watchdog.sh` (3 rodadas validadas mesma noite, todas OK 0s); `/api/health.opsAudit.byDbSource` populated.
- ✅ **Fase 6 — Gap E (Forge bonus)** — `prune-pre-op-snapshots.sh`: linha morta `DELETE FROM ops_audit` (mascarada por `|| true`, bloqueada por trigger `trg_ops_audit_no_delete` CWE-693) removida + comentário misleading substituído por documentação do trade-off append-only.

Execution log completo: `plans/2026-05-15-op-audit-gaps-review.md` §11. Commits `d2dff45` (plan) → `91365ba` (Forge sign-off) → `71fa03a` (DONE). VPS commit `2dd5be64` (Nox author) no `nox-workspace`.

**Validação agendada:** task `99b92b00` dispara 2026-05-16 09:13 BRT — verifica cron snapshot 3am + nightly maintenance overnight + watchdog logs + breakdown byDbSource via `/api/health.opsAudit`.

### Sessão 2026-05-01 noite delivered (marathon ~20h30→21h30 BRT, 15 deliverables)

Closeout de gates + foundation hardening + design specs Maio:
- **G02 ✅ DONE** section_boost shadow→active após análise 7d (compiled +100% n=1252, frontmatter +49% n=315, timeline -17% n=11). `.env` `NOX_SECTION_BOOST_MODE=active`, services restarted.
- **G03 ✅ DONE** archive `memory/{projects,decisions,lessons}.md → .archived-20260502`. 8 chunks órfãos cleanup via better-sqlite3 (cascade trigger). DB 62.927 → 62.919.
- **F12 ✅ DONE** RB-05 Gemini SPOF playbook (Tier 1 FTS-fallback / Tier 2 OpenAI+Voyage / Tier 3 shadow-index trimestral) appended em `docs/RUNBOOKS.md`.
- **F13 ✅ DONE** cost projection 4 cenários 12mo + switch plan emergencial OpenAI 1h + comparativo 7 providers em `runbooks/cost-projection-alt-providers.md`.
- **F14 ✅ DONE** DR drill: script `dr-drill.sh` standalone idempotente (lockfile, JSON log, Discord webhook, dual schema check); cron `0 9 1 1,4,7,10 1` instalado; próxima execução auto 2026-07-06; smoke test OK.
- **E02 🔄 IN-PROGRESS** audit revelou gap real 954 PDFs (não 2.269); cobertura A6 = 79% (3.541/4.495). Retry B-target NUVIVI+CONTRATOS (226 PDFs): 22 CONV / 12 ERR / 192 SCANNED → 23 .md gerados → +1.236 chunks ingestados. E12 escopo expandido pra ~728 PDFs gap residual.
- **5 specs criadas:** E03a SPO injection (1.5h impl), E04a focus boost (1.5h impl), F10 observability dashboard (2.5-3h impl), R01a eval harness revalidated (5h estimate), F14 DR drill quarterly.
- **3 bug fixes:** #1 `src/db.ts:7` honra `NOX_DB_PATH` env (priority NOX_DB_PATH > OPENCLAW_WORKSPACE > __dirname) + test setupDb refeito → 27/27 tests pass; #2 PRAGMA `user_version` aligned 0→10 com `meta.schema_version`; #3 cleanup 8 chunks órfãos G03.

**Estado final pós-sessão:** chunks 64.155 / 100% embedded / salience active / section_boost active / schema v10 aligned / 27/27 tests pass.

### Sessão 2026-04-30 delivered (G01 + audit fixes)
- **G01 ✅ DONE** salience activation `recency × pain × importance` exposta em `/api/health.salience`. `NOX_SALIENCE_MODE=active` aplicado pós baseline 7d OK.
- 7 CRITICAL fixes pós-marathon audit (apiKeys literais, gitleaks, db perms 644→640, 4 races/leaks).
- **OpenClaw upgrade** v2026.4.26 → v2026.4.29 zero-downtime (script Phase 5/6 auto-restaura baseUrl + RelayPlane inactive).

### Sprint A1 + A3 delivered (2026-04-27)

Ingestão massiva GitHub repos + Claude workspace + Mac local delta, **pré-R01a (baseline-first em corpus completo)**:
- **A1 Fase 1: +1.046 graph_nodes** via `graphify-ingest` em 9 repos com graphify-out já gerados (Future-Farm, GalapagosApp, Granix-App, agent-hub-dashboard, daily-tech-digest, memoria-nox, nox-supermem, projeto-ai-galapagos, sao-thiago-fii)
- **A1 Fase 2a: +304 markdown chunks** via clone+ingest de 7 repos pequenos (biolab-ai, curso-ai, posts-linkedin, grancoffee, superfrio, fake-news-check, claude-project-template)
- **A1 Fase 2b: +17.714 chunks** via Claude workspace scope curado (1.356 md de docs+agents+skills+commands+Projetos)
- **A3: +863 chunks** via Mac local `~/Claude/Projetos/agent-orchestrator/` (106 md, único projeto local-only não-duplicado)
- **Scope cut:** _retired/, prompts/, powerpoint-templates (Tier 3 OCR), nox-workspace (257MB scope decision posterior), ~/Desktop (transitório), outros ~/Claude/Projetos/* (duplicam shared/imports)
- **Total:** +19.933 chunks (DB +85%)
- Implicação: F09 off-site backup vira **mais crítico** (mais dados = exposição maior em disk failure)
- Implicação: G01 baseline 7d pode shift 2-3 dias se distribuição salience mudar significativamente

## 2. Sistema unificado de IDs

| Prefix | Categoria | Exemplos |
|---|---|---|
| **F** | Foundation — infra, hardening, ops, security | F01 Query logging, F02 Audit log, F11 Off-site backup |
| **E** | Evolution — features, capabilities, search/ranking | E01 Obsidian, E03 SPO Injection, E05 Edge typing |
| **R** | Research — eval, paper, benchmarks | R01 Eval harness, R02 Paper v2 |
| **P** | Product — NOX-Supermem productization path | P01 Supermem Wave 1 |
| **G** | Gates — decision points (data-fixed) | G01 Salience, G02 Section_boost |
| **D** | Deferred / Cut — com trigger pra revisitar | D01 Q5 reranker, D03 Group routing |

## 3. Status enum

- ✅ `DONE` — entregue, validado em produção
- ⏳ `GATED` — esperando trigger explícito
- 📋 `QUEUED` — pronto pra executar quando bloco abrir
- 🔄 `IN-PROGRESS` — execução ativa
- 🤔 `CANDIDATE` — em validation, precisa POC antes de committed scope
- 🛑 `DEFERRED` — adiado com trigger explícito
- ❌ `CUT` — não fazemos (ver DECISIONS.md)

---

## 4. Tabela mestre cronológica

Velocity buckets aplicados (corrigidos pós-review crítico):
- **Hardening de código existente:** ~0.4× estimates conservadores (validated Bloco I)
- **Greenfield feature** (schema novo, código zero-existente): ~0.7×
- **Cognitive floor** (curadoria humana, paper writing): NÃO comprime — usar estimates honestos

### Foundation (Maio-Set sprints intercalados)

| ID | Vision § | Item | Status | h | Trigger |
|---|---|---|---|---|---|
| **F01** | §0,7 | Query logging + golden-tag (search_telemetry +4 cols) | ✅ DONE | 1 | — |
| **F02** | §15 (audit) | Audit log + `withOpAudit` snapshot pré-op atômico | ✅ DONE | 6 | incident 04-25 |
| **F03** | §1,2 | Ingest-router unified (`routeIngest`) | ✅ DONE | 1 | incident 04-25 |
| **F04** | (tests) | Unit tests `parseRetentionOverride` (20 cases) | ✅ DONE | 0.4 | — |
| **F05** | §10 (canary) | Canary invariants extension (5 invariants */15min Discord) | ✅ DONE | 0.5 | — |
| **F06** | §15 | Dry-run mode reindex/consolidate | ✅ DONE | 1 | — |
| **F07** | (ops) | OpenClaw upgrade defense system (ckpt + improvements + watcher + orchestrator) | ✅ DONE | 4 | OpenClaw .24 break |
| **F08** | (backlog) | B3 backlog sprint 7/8 (issue + CONVENTIONS + alert + playbooks) | ✅ DONE | 1.5 | — |
| **F09** ⭐ | §3,resilience | ~~Off-site backup rclone → B2/R2~~ → moved to **D22 ❌ CUT** (user rejected 2x — VPS Hostinger native backup suffices) | ❌ CUT | — | — |
| **F10** | §10 | Observability dashboard — spec ready (`/api/health` time-series no agent-hub-dashboard, 4 painéis, IndexedDB ring buffer 7d) | 🛑 DEFERRED | 2.5-3 (realista 4-5) | trigger: ≥2 features shadow-mode rodando (E03a/E04a) OR R01a publicar evalMetrics. User não usa dashboard agora; impl prematura sem dados pra plotar. Spec `specs/2026-05-01-F10-observability-dashboard.md` continua válido. |
| **F11** | (incident) | RUNBOOKS.md formalizado (cobre RB-01 a RB-10 — incident playbooks) | ✅ DONE | 2 | — |
| **F12** | (resilience) | Embedding model migration playbook — Gemini SPOF mitigation Tier 1/2/3 (FTS-fallback / OpenAI+Voyage switch / shadow-index trimestral) | ✅ DONE | 1 | RB-05 em `docs/RUNBOOKS.md` |
| **F13** | (cost) | Cost projection pay-per-token alternative — 4 cenários 12mo, switch plan emergencial OpenAI 1h, comparativo 7 providers | ✅ DONE | 1 | `runbooks/cost-projection-alt-providers.md` |
| **F14** | §10 | DR drill trimestral — initial executed 2026-05-01 (RTO validate snapshot ~5s = 1s VACUUM + 2s integrity_check + ~1s schema + ~1s invariants; recovery efetivo ~30s); user_version aligned 10/10; cron `0 9 1 1,4,7,10 1` Q1/Q2/Q3/Q4 09:00 BRT instalado; script `/root/.openclaw/scripts/dr-drill.sh` (Discord alert P0 em fail) | ✅ DONE | 1 + 0.5 cron | `runbooks/dr-drill-quarterly.md`; próxima execução auto 2026-07-06 |
| **F15a** | §11 | **CLI Observability** (renamed pós-critic 2026-05-03) — `cli_telemetry` table + Commander preAction/postAction hooks + `cli-stats` subcomando. Captura command/status/duration. Insights: top usage / slow / error-prone / dormant / recent errors. Opt-out NOX_CLI_TELEMETRY=0. Secret redaction defensiva. `src/cli-telemetry.ts` ~165 LOC | ✅ DONE | 1 (real ~30min) | 2026-05-03 |
| **F15b** | §11 | SEH proper — `seh-report` subcomando: WoW comparison detecta perf_regression / error_spike / dormant_command / capacity_warning / first_use / recovery + PERF_PATCH_HINTS map sugere config patches específicos. Não auto-aplica (FP risk). exit 1 se algum alert. `src/seh-detector.ts` ~165 LOC | ✅ DONE | 2-3 (real ~25min) | 2026-05-03 |
| ~~F16~~ | — | **MOVED 2026-05-03** → escopo `openclaw-vps/infra/` (não memoria-nox; é plataforma OpenClaw, não core memory) | 🚚 MOVED | — | ver `openclaw-vps/infra/docs/HANDOFF.md` |
| **F17** | §15 (audit) | **Op-audit gaps fixed (6 fases, Gap A→E)** — extensão do F02 baseada em deep triage de 3 alertas 2026-05-15. Gap A (Forge): main DB sem snapshot diário → `dist/cli/snapshot-main.js` (app context, vec0.so carregado) + wrapper `snapshot-main-db.sh` + cron `0 3 * * *` + gzip -9 (72%) + retention 5d. Gap B (naming): pattern `<op>-<ts>-<pid>-<uid>` ambíguo entre agentes → schema v17 (`db_source` + `db_path` + `last_heartbeat_at` cols) + `deriveDbSource()` (env primary, parse fallback, 'unknown' final) + filename inclui dbSource. Gap C (visibility): `/api/health.opsAudit` sem breakdown por agente → `byDbSource` em `OpsAuditStats` + `GROUP BY db_source, status`. Gap D (OCR zombies): timeout/heartbeat ausentes → `HARD_TIMEOUT_MS=10800000` (3h) em `ocr-batch.ts` + `recordHeartbeat()` 5min + `ocr-watchdog.sh` (PID liveness + identity `/proc/<pid>/cmdline` + SIGTERM→5s→SIGKILL + UPDATE crashed) integrado em `canary-bundle-15min.sh`. Gap E (Forge bonus): linha morta `DELETE FROM ops_audit` em `prune-pre-op-snapshots.sh` (mascarada por `2>/dev/null \|\| true`, bloqueada por trigger CWE-693) removida + documentado trade-off append-only. Spec: `plans/2026-05-15-op-audit-gaps-review.md` (Q1-Q11 Forge sign-off). Cron snapshot validado 2026-05-16 02:08 BRT (852MB gz). | ✅ DONE | 5.5 estimado / ~3h real | sessão 2026-05-15; Forge code-owner sign-off Q1-Q11 |

### Gates (data-fixed)

| ID | Data | Item | Status | h | Comando |
|---|---|---|---|---|---|
| **G01** | **2026-04-30** | Salience activation `recency × pain × importance` ativa em `/api/health.salience` | ✅ DONE | 0.1 | aplicado via `activate-salience.sh --apply` após baseline 7d OK |
| **G02** | **2026-05-01** | Section_boost shadow→active (compiled +100% n=1252 / frontmatter +49% n=315 / timeline -17% n=11 confirmou ranking previsto) | ✅ DONE | 0.3 | `.env` `NOX_SECTION_BOOST_MODE=active` + services restarted |
| **G03** | **2026-05-01** | Archive 3 source files `memory/{projects,decisions,lessons}.md → .archived-20260502` + cleanup 8 chunks órfãos | ✅ DONE | 0.1 | `mv` + DELETE via better-sqlite3 (vec0 cascade) |

### Evolution (Maio-Set)

A6/A7 (E03/E04) **separados em implement vs activate** após review crítico (shadow-mode 7d obrigatório per regra existente):

| ID | Vision § | Item | Status | h | Dependências |
|---|---|---|---|---|---|
| **E01** | §11 (Fase 4) | Obsidian view-only (Python gen 430 LOC + cron+launchd) | ✅ DONE | 1 | F01-F08 done |
| **E02** | §11 (Fase 3) | Tier 2 PDFs ingest — **3.541/4.495 (79%) DONE via A6 + 226 retry NUVIVI+CONTRATOS in progress 2026-05-01** | 🔄 IN-PROGRESS | 15-25 (I/O) | gap residual (PPR 372 + PESSOAL 250 + outros) → E12 OCR |
| **E12** | §11 (Tier 3) | Tier 3 OCR ✅ DONE 2026-05-08 19:30 BRT. Pipeline cloud Google Document AI + Tesseract local (PDF→pdftoppm 200dpi→tesseract por page, 3-worker parallel). Spec `specs/2026-05-07-E12-tier3-ocr.md`. **Final: 2835 docs OCR'd (2583 cloud + 252 tesseract)**, 9 fails ETIMEDOUT, 31 skipped (architectural + VERRE>25MB choice B). $14.20 spent (cap $50). +8772 chunks (61257→70029). Disk freed 4.5GB pós-cleanup auto. Foundation: schema v15, ocr-detector/ocr-jobs/ocr-engine-stub/cli/routeIngest. Code: imageless mode + retry-failed engine override + safeguard duplicate batch. Lessons: cloud 5MB/15p limits → imageless gives 30p, watcher cleanup só post-natural-tmux-end (kill = race condition) | ✅ DONE | 12h end-to-end (2 sessions) | foundation + cloud + tesseract todos rodaram, choice B aceitou perder VERRE judicial >25MB pra ETA viável |
| **E03a** | (ClawMem Q1) | **A6 implement** Entity-Facts SPO Injection (`<vault-facts>` block via KG) — `src/lib/spo-injection.ts` + envelope `/api/search`; shadow-mode active 2026-05-02 19:16 BRT; smoke OK 1 entity / 7 triples / 55 tokens; 17/17 tests pass | ✅ DONE | 1.5 (real ~1.2h incl. 2 bug fixes) | ≥G03 ✅; v1 sem confidence filter (top-K simples) |
| **E03b** | — | **A6 ACTIVATE 2026-05-17** — task #18 fechada: integrado em `nox-mem search` CLI (import `getVaultFacts` + chamada após results + flag `--no-vault-facts` opt-out, default ON). Mode shadow→active. Smoke entity-rich (Boris): 4 entities/7 triples/91 tokens block surfaced. CLI exercitado por Toto manual + scripts/crons que usam `nox-mem search`. VPS commit `90fa3180`. D37 superseded — consumer absent resolvido. | ✅ DONE ACTIVATE | 0.2 + ~1h integração | task #18 ✅ |
| ~~E04a~~ | (ClawMem Q2) | **CUT 2026-05-16** — A7 focus topic boost: 0 logs em prod 14d, focus state expirado 09/05 sem uso, design pressupõe UX manual que não existe. Removido `src/lib/focus.ts` (266 LOC) + tests (253 LOC) + CLI subcommands + search.ts integration + env. VPS commit `128b7065`. Lição D36: não ship sem consumer real. E14 substitui via A2+D+E-lite-2. | ❌ CUT | (impl 1.5h) + CUT 30min | — |
| ~~E04b~~ | — | **CUT 2026-05-16** — superseded por E04a CUT. | ❌ CUT | — | — |
| **E05** | §11 Wave 1 | Edge typing FULL — `relation_reason` enum 7 (`depends_on/derived_from/opposes/extends/replaces/mentions/unknown`) + Gemini prompt 4-tupla + SPO surface annotation `[reason]` (kg_relations v12). Deployed 2026-05-02 20:42 BRT, schema v12 ativo. Phase 2 (ranking boost) = E05b ✅ shadow 2026-05-06 | ✅ DONE Phase 1+2(shadow) | **8-10** (real ~2h Phase 1 + ~2.5h Phase 2) | shadow 7d antes activate |
| ~~E05b~~ | §11 Wave 1 | **CUT 2026-05-17 — bias arquitetural confirmado**. Golden set 65→80 + re-gate refutou hipótese "regression-to-mean por sample pequeno". Procedure (n=9 inalterado) regrediu EXATAMENTE o mesmo -5pp. Forense: qid=52 "como rodar nox-mem reindex" caía 1.0→0.63 deslocada por chunk 112196 (snippet de comandos com depends_on triviais sobre "query"/"PATH"/"N"). Gold 116800 (FAQ "reindex seguro"): 0 relations. **Reason_boost amplifica chunks com KG coverage independente de qualidade dos reasons** — bias arquitetural, não estatística. Removido reason-boost.ts (266 LOC) + tests (252 LOC) + integration. VPS commit `26640d16`. E14 (20/05) substitui via path arquitetural. Side-effect: 538 relations + 305 entities do kg-extract focado ontem ficam no DB pra outros usos. Lição D38: reason quality > reason quantity. | ❌ CUT | 3h impl + 4h shadow/forense + 30min CUT | — |
| **E13** | §11 Wave 1 | **Temporal-aware Ranking** — detector regex (`quando`, `primeira/última`, `deployado`, ISO date) + override `section_boost`: timeline 0.8→1.4, compiled 2.0→1.0, frontmatter 1.5→0.9. Schema v14. `src/lib/temporal-detector.ts` ~110 LOC, 21/21 tests + suite 140/141. **Gate preview 2026-05-06 21:13 BRT:** ACTIVATE-READY ✅ (Δ temporal +0.149, Δ non-temporal +0.004, 9.2% detected in range). **ACTIVATED 2026-05-06 21:18 BRT** (`NOX_TEMPORAL_BOOST_MODE=active`). Aplica em produção. Spec `specs/2026-05-06-E13-temporal-aware-ranking.md` | ✅ DONE active | 2h impl + 1h Toto cure | gate ACTIVATED 05-06 (Δ temporal +14.9pp, no regressão global) |
| **E06** | §11 | `nox-mem detect-changes --since=<commit>` (read-only git diff→entities) | 📋 QUEUED | 2-3 | — |
| **E07** | §11 | `nox-mem impact <entity>` 1-hop blast radius via kg_relations | 📋 QUEUED | 2.5 | E05 active (não shadow) |
| **E08** | §11 | `nox-mem api-impact <signature>` multi-arquivo grep + classificação import/definition/usage. Smoke prod: getDb=37 files/157 refs em 11ms. Excludes node_modules/dist/.git/build/.next/coverage. `src/api-impact.ts` ~150 LOC | ✅ DONE | 1.5 (real ~20min) | 2026-05-03 |
| **E09** | (ClawMem Q3 + §1.7b dormente) | A-MEM auto-keywords/links no ingest (funde §1.7b Hierarchical Tagging) | 🤔 CANDIDATE | 5-6 | E05 active obrigatório (enum CLOSED); shadow obrigatório |
| **E10** | (ClawMem Q4 + W2.2) | Consolidation merge candidate detection (DRY-RUN). Smoke: 914 entities → 52 pairs em 136ms (39 LOW FP / 9 MEDIUM / 4 HIGH protected). Apply BLOCKED até R01c≥0.6 (Run #9 = 0.519). `src/consolidation.ts` ~210 LOC | 🟡 PARTIAL DONE (dry-run only) | 3-4 (real ~45min) | 2026-05-03; --apply requer R01 ≥ 0.6 |
| **E11** | §11 | Reflect cache (semantic key) — exact hash + cosine ≥ 0.88 fallback. Smoke: exact hit 30× speedup, semantic hit 4× speedup (sim=0.914). 4 env vars `NOX_REFLECT_SEMANTIC_*`. Fail-open. `src/reflect.ts` extension | ✅ DONE | 1.5 (real ~25min) | 2026-05-03 |
| **E06** | §11 Wave 1 | `nox-mem detect-changes --since=<commit>` read-only git diff name-status + entity resolution 2-path (frontmatter name + chunk evidence). Smoke prod: 1498 files → 182 entities em 268ms. `src/detect-changes.ts` ~210 LOC | ✅ DONE | 2-3 (real ~30min) | 2026-05-03 |
| **E07** | §11 | `nox-mem impact <entity>` 1-hop blast radius bidirecional via kg_relations agrupado por reason E05. REASON_PRIORITY weights + blast_radius_score. Smoke prod: Toto blast=29152.1, Forge 12 depends_on, em 1ms. `src/impact.ts` ~165 LOC | ✅ DONE | 2.5 (real ~25min) | 2026-05-03; uso E05 confirma valor reasons enriquecidos |
| **E14** | §11 Wave 2 | **Retrieval evolution — Wave 1 COMPLETA 2026-05-17 (3 dias antes do target)**. Sub-features: **E-lite-2 ACTIVE** (fts_anchor bilingual regex v4, +0.94pp), **D ACTIVE** (language-aware RRF PT 1.15/0.85, +1.92pp ZERO regressão). **A1/A2/G DEFERRED PERMANENTE (D39)** — 4 tentativas FTS5 fix refutadas; dense Gemini 3072d é o motor; FTS5 silencioso é design correto pra este corpus. F (Cohere) gate condicional pós-evidência empírica adicional. Estado: 0.6813 overall (+16.9% vs paper baseline 0.583). Cross-link D31-D33 (roadmap original) + D39 (FTS5 silent) + spec `specs/2026-05-10-E14-retrieval-evolution.md`. | ✅ Wave 1 DONE; Wave 2 (D01v3/Cohere) ON HOLD | 7h real (era 5-7 spread Mai-Jul) | golden n=78 honest; D39 codificado |
| **E15** | §11 (UX/budget) | **CodeGraph-inspired improvements** (A+B+C pacote, spec 2026-05-17) — origem análise [`Jakedismo/codegraph-rust`](https://github.com/Jakedismo/codegraph-rust). **A.** Tier-aware behavior por context window do consumer (Small/Medium/Large/Massive escalam `limit` + dense top_k + SPO triples K; detection via env/header/CLI flag). **B.** Context overflow protection multi-layer (truncation flag + cumulative tracking via header + soft fail 80%×4 budget). **C.** Indexing tiers `--tier {fast|balanced|full}` em `reindex`/`vectorize`/`kg-extract`. Pacote 4-7h total. Ortogonal a D01 v3 (E15 melhora UX/budget; D01 melhora ceiling nDCG). Spec: `specs/2026-05-17-E15-codegraph-inspired-improvements.md`. | 📋 QUEUED | 4-7h (A 1-2h + B 1-2h + C 2-3h) | pós-R03 submit (ortogonal a Wave 2 E14) |

### Sprint pós-R03 — E14 retrieval evolution

**Início:** 20 mai 2026 (após arXiv submit R03 em 19/05)
**Spec canonical:** `specs/2026-05-10-E14-retrieval-evolution.md`
**Workspace VPS (Forge ops):** `/root/.openclaw/workspace/shared/plans/nox-mem-retrieval-evolution-spec.md`
**Baseline:** Hybrid nDCG@10 = 0.699 | **Target:** 0.750-0.780 | **Sub-target cross-language:** ≥0.85 do overall
**Latency teto:** p95 <1.5s pós-A2 (estimativa +150ms vs baseline 1s)

| Semana | Ação | Gate / Output |
|--------|------|---------------|
| ~~20-23 mai~~ | ~~Golden set expansion n≥30~~ — **ADIANTADO 2026-05-17** (65→78 honest após cleanup; cross-lang 0→10 ✅, cross-agent 4→5, temporal 4→6 ✅). | ✅ Pré-requisito atingido |
| ~~27 mai - 02 jun~~ | ~~E-lite-2 backfill regex bilíngue~~ — **ADIANTADO 2026-05-17 mesmo dia que design**. Implementação v4 regex (3 layers) + backfill 69298 chunks 17.3s + FTS5 recreate 7.2s. **Overall +0.94pp (0.6644→0.6738), vs paper baseline +15.6% relativo.** cross-agent +6.4pp, procedure +3.9pp, entity +3.1pp. VPS commit `d48b115e`. | ✅ ACTIVE |
| ~~10-14 jun~~ | ~~A2 + D~~ — **D ADIANTADO 2026-05-17 mesmo dia**. D standalone +1.92pp ZERO regressão (procedure +6.55pp, cross-agent +5.34pp, security +2.46pp, entity +1.64pp, concept +1.32pp). A2+D combinado REFUTADO (-7.98pp). A2 deferred indefinido. VPS commit `7dc46fb5`. **Overall final 0.6813 (+16.9% vs paper baseline).** | ✅ D ACTIVE; A2 DEFERRED |
| 24-26 mai | Analisar composição: recall zero vs parcial | Define ordem E vs A+D |
| 27 mai - 02 jun | E-lite-2: schema v.18 (`ALTER TABLE chunks ADD fts_anchor`) + backfill regex bilíngue (~19K chunks) | Zero Gemini; SQLite ≥3.35 pra rollback DROP COLUMN |
| 03-09 jun | Shadow 7 dias E-lite-2 + ablation vs baseline | Shadow obrigatório (regra crítica #6) |
| 10-14 jun | A2 (dense pool 50→100-150) + D (language-aware RRF weights) | Latency gate p95 <1.5s |
| 15-21 jun | Shadow 7 dias A2+D + ablation incremental | Shadow obrigatório |
| 22 jun | Medir nDCG@10 overall + cross-language sub-eval | Avaliar gap vs target |
| Jul (se gap > 0) | A1 (FTS5 pool) e/ou G-seletivo (HyDE on-demand quando pool <5) | Baseado em resultados |
| Jul+ (se <0.775) | Avaliar Cohere `rerank-multilingual-v3.0` (fallback condicional, custo recorrente) | Gate métrico — não decidir a priori |
| Q3 2026 | Reavaliar Caminho B (gate cross-language <70%/≥85%) e Caminho C (KG ≥75% coverage) | Gate quantitativo — D32 |

**Regras do sprint:** shadow 7d obrigatório entre ativações; p95 <1.5s teto absoluto; ablation registrada em `paper/publication/results/`; material de ablation reforça paper follow-up (pain × shadow discipline empírica).

### Research (eval + paper)

⚠️ **Mudança crítica pós-review:** R01 dividido em skeleton (Maio) + curation (Jun-Jul) — baseline-first é precondição arquitetural pra E05/E10 mudarem ranking.

| ID | Vision § | Item | Status | h | Dependências |
|---|---|---|---|---|---|
| **R01a** | §11 Wave 2 | **Eval harness skeleton** (schema v11 + tabelas `eval_queries`/`eval_runs`/`eval_results` + nDCG@10/MRR/Recall@10/Precision@5 + CLI 6 subcomandos + JSONL out + `/api/eval-metrics` + 5 golden seed queries) — `src/lib/eval-metrics.ts` (pure funcs) + `src/lib/eval.ts` (orchestration) deployed 2026-05-02 19:43 BRT; baseline n=40 cured = hybrid 0.658 / Recall 0.850 (post-R01b batch2); 28/28 eval tests + 109/110 suite total pós-E05 | ✅ DONE | 4-6 (real ~3h) | F01 corpus ready ✅ |
| **R01b** | — | **Curadoria 50 golden queries** ✅ **MILESTONE 50/50 fechado 2026-05-03** (5 seed + 20 batch1 + 15 batch2 + 10 batch3 dos quais 6 NEGATIVE/GAP + 4 cured); cobre 8 categorias mistas | ✅ DONE | 8-10 (real ~30min batch3 + ~6h spread Maio) | — |
| **R01c** | — | Baseline FTS-only vs hybrid run + publish em `/api/eval-metrics`. **Run #9 hybrid n=50 = nDCG@10 0.519 / MRR 0.482 / Recall@10 0.687 / Prec@5 0.268** (drag de balanceamento: 6 negatives 12% sample). **Run #8 FTS-only n=50 = nDCG 0.015 (gap 97.7% loss)** confirma necessidade arquitetural hybrid. By category: concept 0.656, procedure 0.619, security 0.594, decision 0.542, entity 0.459, **cross-agent 0.369**, **temporal 0.233**, negative 0. **Trigger D01 NÃO dispara** (0.519 < 0.6) — D01 desativado | ✅ DONE | 1-2 (real ~30min) | 2026-05-03 |
| **R02** | §11 Wave 3 | **Paper v1.1 ✅ DONE 2026-05-07** — Run #30/#31/#32 numbers (n=60 R01c-v1.1 post-cure): hybrid 0.5831±0.0046, FTS 0.0000, Δ +58.3pp, 4.0× BM25 Pyserini. §6.5 ablations E7-E9 confirmadas (E7=-0.029 marginal, E8=-0.041, E9=-0.032). §7 framing "Measurement instrument matures alongside the system" justificando +11.9% gain via gold cleanup + corpus growth (sem code change). Disclosure v1.0→v1.1 com v1.0.0 git tag preserved. PDF 891KB / 31 pages compilado. arxiv-submit-metadata + RESUMO + blog-post sincronizados. | ✅ DONE v1.1 | 5-6 (floor cognitivo) | — |
| **R03** | §11 Wave 3 | **arXiv submit prep + endorsement + submission** — target 2026-06-02. Path 2 endorsement obrigatório (policy 2026-01-21). Candidatos TIER 1: Jayr Pereira UFCA/UNICAMP (autor JUÁ Brazilian Legal IR, domain match), backups Maritaca AI (Rodrigo Nogueira, Thales Almeida). Cold email template em HANDOFF. Pré-submit checklist em HANDOFF (12 itens). Post-submit: Patrick Lewis follow-up + Twitter/HN/LinkedIn launch. | 🟡 NEXT-SESSION | 2-4 (cold emails + arXiv UI) | R02 v1.1 ✅; arXiv account ✅ |

### Product (NOX-Supermem)

| ID | Vision § | Item | Status | h | Dependências |
|---|---|---|---|---|---|
| **P01** | §11 (Fase 4b/5/P) | NOX-Supermem productização — Fase 4b → 5 → P | 📋 QUEUED | semanas | E01 estável 30d (= 2026-05-26 elegível) |

**Short-circuit identificado pelo architect-reviewer:** P01 depende **apenas** de E01 estável 30d. Wave 1-3 (E05-E10, R01-R02) são **enrichments**, não bloqueadores. Toto pode iniciar **P01 design** em **05-26** sem aguardar Wave 2.

### Deferred / Cut

| ID | Item | Decisão | Trigger pra reavaliar |
|---|---|---|---|
| **D01-v1/v2** | Q5 Cross-encoder reranker — **CUT v1 + v2 (2026-05-08+09)**. Spec `specs/2026-05-07-D01-cross-encoder-reranker.md`. v1 (BGE-base, English): offline eval Δ nDCG = -0.2113 → CUT (English não transfere PT-BR). v2 (`onnx-community/bge-reranker-v2-m3-ONNX`, multilingual): tentativa 2026-05-09 19:40 BRT → **OOM-killed** (process consumed 15GB RSS, VPS tem 15GB total; quantized variant insuficiente para 568M params em @xenova/Node stack). NOX_RERANKER_MODE=off mantido. Schema v16 preservado (innocuous). Source-of-truth limpo (dead code revertido 2026-05-09 commit `2c5bae0`). **D01-v3 deferred:** opções Cohere Rerank API ($), VPS upgrade ($), sidecar Python (infra) ou smaller multilingual (jina-v2-base test). Decisão require evidência de query patterns que precisam re-ranking OU demanda explícita Toto. **0.5831 nDCG hybrid baseline mantido como teto operacional** | ⛔ CUT v1 + v2 | 4h v1 + 30min v2 attempt | sem path simples local; vendor SaaS é alternativa |
| **D02** | W3.2 Plugin hooks (`onIngest`, `onRelation`) | 🛑 DEFERRED (não CUT) | Multi-tenancy P01 design — se >2 tenants pediram custom ingest, design hooks ANTES de implementar |
| **D03** | Group routing (`@group`, `groups.yaml`) | ❌ CUT | Açúcar de `cross-search --agents` se aparecer dor real |
| **D04** | W3.3 Group routing v2 (frontmatter tag) | ❌ CUT | — (mesma razão D03) |
| **D05** | Phase 3 deductive synthesis cross-session | ❌ CUT | LLM confabula sem citation chain |
| **D06** | Phase 4 recall stats worker dedicado | 🛑 DEFER | F10 dashboard cobre? Revisitar Jul antes de R01a |
| **D07** | Heavy-lane quiet-window worker | ❌ CUT | Cron 23:00 + canary já cobrem |
| **D08** | Silos schema separados (docs+observations+KG) | ❌ CUT | chunks canônico evita drift |
| **D09** | 30 MCP tools (gbrain pattern) | ❌ CUT | Cap em 16 |
| **D10** | Memgraph / Neo4j | ❌ CUT | >500K entities |
| **D11** | Postgres / PGLite | ❌ CUT | >500K entities |
| **D12** | Text2Cypher / query DSL | ❌ CUT | — (estrutural) |
| **D13** | Free-form `relation_reason` vocabulary | ❌ CUT | — (estrutural) |
| **D14** | Atomic hybrid query (CTE única) | ❌ CUT | p95 >500ms persistente |
| **D15** | Dashboard React como roadmap item | ❌ CUT | Já existe (`agent-hub-dashboard`) |
| **D16** | Expertise profiling automático | ❌ CUT | >20 agentes |
| **D17** | Productizar nox-supermem em paralelo | 🛑 DEFER | E01 estável 30d |
| **D18** | Bump v1.6→v1.7 / v14→v15 (ClawMem-driven) | ❌ CUT | POC + 7d shadow validados |
| **D19** | Tier 3 OCR no critical path Fase 4 | 🛑 OPCIONAL | Volume PDF scaneado >50 docs |
| **D20** | git-as-source-of-truth | ❌ CUT | Nunca (incompatível) |
| **D21** | W2.3 Tool/Skill map | 🛑 DEFER ≥6mo | Caso de uso concreto aparecer |
| **D22** | F09 Off-site backup rclone → B2/R2 | ❌ CUT (2026-04-29) | Permanente — user declarou 2x ("VPS Hostinger backup basta", "não vamos gastar tempo e espaço"). Ver DECISIONS.md linha 246. |

---

## 5. Capacity tracker (recalibrado pós-review + atualizado 2026-05-01)

```
Disponível 05-02 → 09-30:        ~21 semanas × 6h/sem realista = 126h
Margem incident:                 -20h reservadas (histórico: 4 incidents 2 dias)
Capacity líquida:                ~106h

Já queimado (Abr 27 → Mai 01):   ~22h (gates G01-G03 + F12-F14 + F02-F08 + bug fixes + 5 specs)

Compromissado núcleo (estimates honestos pós-review):
  F09 off-site backup:           ❌ CUT (D22) — não conta
  F10 observability dashboard:   🛑 DEFERRED 2026-05-02 (user não usa agora; trigger ≥2 features shadow OR R01a evalMetrics) — não conta
  F12 Gemini SPOF playbook:      ✅ DONE 2026-05-01 (1h)
  F13 cost projection alt:       ✅ DONE 2026-05-01 (1h)
  F14 DR drill (1 inicial):      ✅ DONE 2026-05-01 (1.5h cron+script)
  E02 Tier 2 PDFs (I/O):         15-25h IN-PROGRESS ← retry rodando background
  E05 Edge typing FULL:          8-10h  ← greenfield 0.7×
  E06 detect-changes:            2-3h
  E07 impact:                    2.5h
  E08 api_impact (defer 1º):     1.5h
  R01a eval skeleton (Maio!):    4-6h   ← MOVED earlier
  R01b curadoria 50 queries:     8-10h  ← cognitive floor
  R01c baseline + publish:       1-2h
  R02 paper v2:                  5-6h   ← writing tem floor
                                 ───────
Subtotal núcleo:                 49.5-68h total (já 3.5h done; F10 deferred -2.5/-3h = restam 46-64.5h)

Candidates Section 9:
  E03a/b A6 implement+activate:  1.7h
  E04a/b A7 implement+activate:  1.8h + 7d wall
  E09 A-MEM keywords:            5-6h
  E10 consolidation merge:       3-4h
                                 ───────
Subtotal candidates:             11.5-13.5h

Bloco V (Set+):
  E11 reflect cache:             1.5h
  F15 SEH:                       1h
  E12/P01 dias-semanas:          out-of-budget Maio-Ago
                                 ───────

TOTAL núcleo + candidates + small Set+:  64-86h total vs 106h capacity restante (2026-05-02 forward, pós-F10 defer)

Já entregue:                     ~22h queimadas (gates fechados, foundation)
Restante a queimar:               ~42-64h
Sobra realista:                  +42 a +64h (margem ampliada com F10 defer)
```

**Diferença vs estimate ingênuo anterior:**
- Antes: 36-41h vs 45h (4-9h sobra)
- **Agora honesto:** 67-89h vs 112h (23-45h sobra)
- **Capacity ampliada** (10h/sem fantasia → 6h/sem realista × mais semanas) **bate com cognitive floor honesto**

**Decisões de ajuste obrigatórias:**
- ✅ **Defer E08** (api_impact, 1.5h) — primeiro corte se apertar
- ✅ **Recompactar R02** pra 4-5h se sem dados eval completos
- ✅ **Promover E03/E04 (A6/A7) candidates** post-G03 — 3.5h total, additive, baixo risco
- 🤔 **E09/E10 candidates entram se sobrar tempo pós-Wave 1 core** (60-70% likely com capacity nova)
- ❌ **F09 off-site backup CUT (D22)** — user rejected 2x; VPS Hostinger native backup suffices

## 6. Wave gating métrico (não calendário)

**Wave 1 → Wave 2 (E05 → R01/E10):**
- E05 atinge ≥80% das ~544 rels classificadas com confidence ≥0.7 em shadow-mode por ≥7d
- E06 + E07 + E08 rodaram ≥3x em uso real sem falso-positivo
- 50 golden queries (R01b) curadas e validadas

**Wave 2 → Wave 3 (R01c → R02 + D01 trigger):**
- nDCG@10 baseline publicado em `/api/health.evalMetrics`
- 1 incident-free month pós-Wave 1
- Affective Ranking validado com salience ativa (G01 OK)

**Kill switches:**
- E07/E08 não usados ≥3x/semana após 30d → archive feature
- R01b não conseguir 50 queries em 2 semanas → reduzir pra 20 + accept lower power
- Health: salience delta ≥5%, vectorCoverage <99%, ou confidence distribution bimodal extrema → PAUSE wave + investigar

---

## 7. Critical path & ordering (revisado)

```
HOJE 05-01 NOITE ──┐
                   │ (Gates G01/G02/G03 ✅ DONE | F12/F13/F14 ✅ DONE | F09 CUT D22)
                   ▼
[E02 Tier 2 PDFs IN-PROGRESS — retry NUVIVI/CONTRATOS background] ═══════════════│
             │                                                                    │
             ├──→ [E03a A6 implement 1.5h Maio] ──→ shadow 7d ──→ [E03b activate]
             ├──→ [E04a A7 implement 1.5h Maio] ──→ shadow 7d ──→ [E04b activate]
             ├──→ [F10 dashboard impl 2.5-3h Maio] (paralelo, agent-hub-dashboard)
             │
             ▼
[R01a eval skeleton 4-6h MAIO] ◀── baseline-first                        │
             │                                                            │
             ▼                                                            │
[E05 edge typing 8-10h] ──→ shadow 7d ──→ E05 active                     │
             │                                                            │
             ▼                                                            │
[E06 detect-changes 2-3h] + [E07 impact 2.5h] + [E08 api_impact 1.5h]    │
             │                                                            │
             ▼                                                            │
[R01b curadoria 8-10h spread Jun-Jul] ──→ [R01c baseline publish]        │
             │                                                            │
             ▼                                                            │
[E10 consolidation merge 3-4h candidate] (gated nDCG≥0.6)                │
             │                                                            │
             ▼                                                            │
[R02 paper v2 5-6h Ago]                                                   │
             │                                                            │
             ▼                                                            │
[E01 Fase 4 estabiliza 30d wall-clock] ◀── DONE 04-26 conta from there  │
             │                                                            │
             ▼                                                            │
[P01 NOX-Supermem productização] semanas (≥05-26 elegível)                │
                                                                          │
                                                                          ▼
                                                              SHORT-CIRCUIT POSSÍVEL:
                                                              P01 design pode iniciar 05-26
                                                              SEM aguardar Wave 2/3
                                                              (E05-R02 = enrichments, não bloqueadores)
```

---

## 8. Cross-ref ID systems (decoder de namespaces antigos)

Nomenclatura antiga (v1.5/v1.6/ClawMem/Wave/Bloco) → nova:

| Antigo | Novo | Item |
|---|---|---|
| A0 | F01 | Query logging |
| A1 | F02 | Audit log + snapshot |
| A2 | F03 | Ingest-router |
| A3 | F04 | Tests parseRetentionOverride |
| A4 | F05 | Canary invariants |
| A5 | F06 | Dry-run mode |
| upgrade-defense | F07 | OpenClaw upgrade defense |
| B3 | F08 | Backlog sprint |
| (novo) | F09 | Off-site backup ⭐ |
| (novo) | F10 | Observability dashboard ⭐ |
| (novo) | F11 | RUNBOOKS.md |
| (novo) | F12 | Gemini SPOF playbook ⭐ |
| (novo) | F13 | Cost projection alt ⭐ |
| (novo) | F14 | DR drill ⭐ |
| C2 | F15 | SEH Self-Evolving Hooks |
| (novo) | ~~F16~~ | Telegram rollback bot ⭐ → MOVED 2026-05-03 → openclaw-vps/infra |
| gate.salience | G01 | — |
| gate.section_boost | G02 | — |
| gate.archive_3files | G03 | — |
| B1 | E01 | Obsidian view-only |
| B2 | E02 | Tier 2 PDFs |
| A6 (Q1) | E03a + E03b | SPO Injection (split implement/activate) |
| A7 (Q2) | E04a + E04b | Focus Boost (split implement/activate) |
| W1.1 | E05 | Edge typing FULL |
| W1.2 | E06 | detect-changes |
| W1.3 | E07 | impact |
| W1.4 | E08 | api_impact |
| W1.5 (Q3, §1.7b) | E09 | A-MEM keywords |
| W2.2 (Q4) | E10 | Consolidation merge |
| C1 | E11 | Reflect cache |
| C3 | E12 | Tier 3 OCR |
| W2.1 | R01a + R01b + R01c | Eval harness (split skeleton/curation/baseline) |
| W3.1 | R02 | Paper v2 |
| C4 | P01 | NOX-Supermem productização |
| Q5 | D01 | Cross-encoder reranker |
| W3.2 | D02 | Plugin hooks |
| (group routing) | D03/D04 | Group routing v1/v2 |
| (Phase 3 ClawMem) | D05 | Deductive synthesis |
| (Phase 4 ClawMem) | D06 | Recall stats worker |
| (heavy-lane ClawMem) | D07 | Quiet-window worker |
| (silos ClawMem) | D08 | Schema separados |
| (gbrain) | D09 | 30 MCP tools |
| — | D10 | Memgraph/Neo4j |
| — | D11 | Postgres/PGLite |
| — | D12 | Text2Cypher |
| — | D13 | Free-form relation_reason |
| — | D14 | Atomic hybrid query |
| — | D15 | Dashboard React (existe) |
| — | D16 | Expertise profiling |
| — | D17 | Productizar paralelo |
| — | D18 | Bump v1.6→v1.7 |
| — | D19 | Tier 3 OCR critical-path |
| — | D20 | git-as-source-of-truth |
| W2.3 | D21 | Tool/Skill map |

⭐ = item **NOVO** identificado pelos agents review (não estava no roadmap original).

---

## 9. Cruzamento com VISION.md (nox-neural-memory v14)

A coluna `Vision §` em §4 referencia seções da visão estratégica. Mapping resumido:

| Conceito Vision | Implementado por |
|---|---|
| §0 Query Strategy | F01 (telemetry corpus) |
| §1 graphify vs nox-mem KG | F03 (router) |
| §3 Cross-Agent Intelligence | (existing `cross-search`) |
| §4 Obsidian painel visual | E01 ✅ |
| §5 KG extraction Gemini 2.5 Flash | (existing — kg-build) |
| §6 graph-memory plugin | (existing) |
| §7 Estratégia camadas hot/warm/cold | F01, F05 |
| §8 Affective Ranking pain-weighted | (salience formula ativa post-G01) |
| §9 Compiled Truth + Timeline 3-section | F03 (entity ingest) ✅ |
| §10 Bridge Mode | (R02 paper v2 documenta) |
| §11 Memory Graph Maturity Waves | E05, E06, E07, E08, E09, E10, R01a-c, R02 |
| Fase 1.7b dormente | E09 (resurrected as candidate) |
| Fase 1.7a Reflective Loops | ✅ DONE 04-19 — destrava E11 |
| Fase 4 Obsidian | E01 ✅ |
| Fase 5 openclaw-memory-sync | (parte de P01) |
| Fase P NOX-Supermem | P01 |

Próximo update VISION.md: pós-G01/G02/G03 (capturar resultado dos gates).

---

## 10. Próxima ação concreta (referência rápida)

Hoje é **2026-05-01 noite** (sexta). Gates G01/G02/G03 ✅ fechados, F12/F13/F14 ✅ done. Foco shifta pra implementação Maio.

### O que já foi entregue (recap pós-marathon)
- ✅ G01 salience active (04-30) | G02 section_boost active (05-01) | G03 archive done (05-01)
- ✅ F12 Gemini SPOF playbook | F13 cost projection alt | F14 DR drill (cron quarterly instalado)
- ✅ 5 specs (E03a / E04a / F10 / R01a revalidated / F14 quarterly) — prontas pra impl
- ✅ 3 bug fixes (db.ts NOX_DB_PATH, PRAGMA user_version aligned 10/10, 8 chunks órfãos G03)
- ✅ 109/110 tests pass + 1 skip + 0 fail | chunks 64.165 / 100% embedded | schema v12

### O que já foi entregue (2026-05-02 marathon, ~10.4h)
- ✅ E02 retry NUVIVI/CONTRATOS (+1.246 chunks)
- ✅ E03a SPO injection deploy (shadow)
- ✅ E04a Focus boost deploy (shadow)
- ✅ R01a Eval Harness deploy (schema v12, 6 CLI subcomandos, endpoint)
- ✅ R01b 40/50 cured (5 seed + 20 batch1 + 15 batch2; 8 categorias)
- ✅ R01c prelim n=40: hybrid nDCG=0.658 / Recall=0.850 / FTS=0.000 (gap publicado)
- ✅ E05 Edge Typing Phase 1 deploy (schema v12, relation_reason enum 7, SPO surface)
- ✅ Schedule routine 2026-05-09 (verdict ACTIVATE/KEEP-SHADOW automático)
- ✅ 3 fixes residuais (F14 RTO / F10 stack / cost projection)
- ✅ PRAGMA v2 patch ensureSchema (drift recovery proof)

### Próxima sessão (2026-05-03+) — fila imediata
1. **R01c prelim oficial n=40 fts variant** (5min run + 15min análise) — publica baseline definitivo fts vs hybrid com sample 8x maior que primeira tentativa
2. **kg-build incremental** (~30min) — valida E05 Phase 3 end-to-end com Gemini real (distribuição reason muda de unknown=464 → menos)
3. **R01b cure 41-50** (~1h) — fecha milestone 50/50 → libera R01c definitivo

### Activate gates pendentes — auto 2026-05-09 sábado
- **E03b** SPO surface — routine `trig_012nuCN14VwcxGLq8ERaLPCK` gera GitHub Issue verdict ACTIVATE/KEEP-SHADOW
- **E04b** Focus apply — mesma routine
- E05b ranking boost ainda não definido (depende análise pós-E05 Phase 1 + shadow telemetria)

### Wave 1 restante (Maio-Jun)
- **E06** detect-changes (2-3h) — read-only git diff→entities (Wave 1 next)
- **E07** impact 1-hop blast radius (2.5h) — depende E05 active (não shadow)
- **E08** api_impact (1.5h, defer 1º se apertar capacity)
- **E11** Reflect cache (1.5h) — telemetria 7d cron já rodando, dado disponível

### Jun-Jul
- **R01b** restante 10 queries (até 50/50)
- **R01c** definitivo após R01b 50/50 (1-2h, publish em `/api/eval-metrics`)
- **E10** consolidation merge candidate (3-4h, gated nDCG≥0.6 + dry-run zero FP) — D01 trigger técnico já passou em hybrid n=40
- **E12** Tier 3 OCR (escopo expandido ~728 PDFs gap E02 + Fathom + Path C)
- **D01** cross-encoder reranker (Qwen3 local) — gated nDCG≥0.6 ✅ JÁ ATIVO em hybrid; aguardar R01b 50/50 pra commit

### Ago
- **R02** paper v2 (5-6h, writing tem floor cognitivo) — dependent R01c published

### Set+
- **F15** SEH Self-Evolving Hooks
- **P01** NOX-Supermem productizacao (elegível desde 2026-05-26 = E01 estável 30d)

### Set+
- **E11** reflect cache (1.5h) — depende telemetria reflect 7d
- **F15** SEH Self-Evolving Hooks (1h)
- **P01** NOX-Supermem productização (elegível desde 2026-05-26 = E01 estável 30d; Wave 2 NÃO bloqueador per architect-reviewer)

---

## 11. Mudanças vs versão anterior do ROADMAP

### 2026-05-04 marathon — W1 Day 1+2 (~24h, publication sprint)

1. ✅ **BM25 baseline** — Pyserini n=60, nDCG=0.1475 (confirma necessidade hybrid)
2. ✅ **Pain baseline** — --mode api n=6, nDCG=0.2689 (diferencial #1 sustentado)
3. ⏳ **E5 multilingual-base RUNNING** — PID 258574, ETA 16:50 BRT; BGE-M3 CUT (CPU inviável)
4. ✅ **E12 storage** — 99.92% shared cross-agent confirmado
5. ⏳ **E12 retrieval BACKLOG** — depende migração `requesting_agent` (~1h)
6. ⏳ **E10 pain ablation BACKLOG** — pain=1.0 uniform; precisa 2× prod restart (~12min)
7. ✅ **E11 BEIR** — 10 queries curadas, 0% vocab overlap; expected_doc_ids queued
8. ✅ **Paper §1-7** — draft completo, abstract, appendix D (audit fixed)
9. ✅ **LaTeX template** — main.tex + Makefile (falta neurips_2024.sty download)
10. ✅ **4 figuras** — Mermaid → PDF + PNG
11. ✅ **Distribuição completa** — Blog + HN + Twitter spec + LinkedIn
12. ✅ **refs.bib** — 8 PRIMARY + 2 SECONDARY + 7 W2 = 17 entradas
13. ✅ **CITATION.cff** — completo (3 VERIFY markers pós-arXiv ID)
14. 📋 **LICENSE + chart hero PNG** — parallel agents queued
15. ✅ **R02 IN-PROGRESS** — status atualizado (era QUEUED)

### 2026-05-01 noite — Marathon closeout (sessão atual)

Sincronização pós-trabalho da sessão noite (commit `9156f50`):
1. ✅ **G01/G02/G03 todos DONE** — salience active 04-30, section_boost active 05-01, archive 3 files 05-01
2. ✅ **F12/F13/F14 todos DONE** — Gemini SPOF playbook + cost projection alt + DR drill (cron quarterly instalado)
3. 🔄 **E02 IN-PROGRESS** — gap real 954 PDFs (não 2.269); cobertura A6 = 79%; retry NUVIVI+CONTRATOS rodando em background (+1.236 chunks ingestados, +1.258 vectorized)
4. 📋 **E12 escopo expandido** — inclui ~728 PDFs gap residual E02 (PPR 372 + PESSOAL 250 + size-rejected ~106) + Fathom + Path C
5. 🤔 **E03a/E04a/F10 specs CANDIDATE** — design specs criadas, prontas pra impl Maio (1.5h + 1.5h + 2.5-3h)
6. ✅ **3 bug fixes** — db.ts honra NOX_DB_PATH; PRAGMA user_version aligned 10/10; 8 chunks órfãos G03 cleanup
7. ✅ **Estado vivo §1 atualizado** — chunks 62.836 → 64.155 / OpenClaw v.26 → v.29 / salience+section_boost active / 27/27 tests
8. ✅ **§10 Próxima ação reformulada** — recap pós-marathon + fila imediata Maio (5 itens) + activate gates pendentes E03b/E04b

### 2026-04-27 manhã — Sistema unificado de IDs

Pós-review por 3 agents (architect, critic, architect-reviewer):

1. ✅ **Sistema unificado de IDs** F/E/R/P/G/D substitui 6+ namespaces
2. ✅ **F09 off-site backup adicionado** como P0 (antes G01) — gap crítico
3. ✅ **F10/F12/F13/F14 adicionados** (observability + DR + cost) — ~~F16~~ moved 2026-05-03 → openclaw-vps/infra
4. ✅ **R01 dividido em R01a/R01b/R01c** — skeleton em Maio (era Jun-Jul) pra baseline-first
5. ✅ **E03/E04 dividido em implement/activate** — captura latência shadow 7d wall-clock
6. ✅ **Velocity bucketada** (greenfield 0.7×, hardening 0.4×, cognitive floor não comprime)
7. ✅ **Capacity recalibrada** (6h/sem × 22 sem = 132h, vs 10h/sem × 5 meses = 50h fantasia)
8. ✅ **Margem incident ampliada** (5h → 20h baseado em histórico real)
9. ✅ **D02 promovido de CUT → DEFERRED** (Plugin hooks, gatilho multi-tenancy)
10. ✅ **D01 trigger antecipado** (Q5 reranker; 2 PRs mal-rankeadas OR R01c)
11. ✅ **Cross-ref VISION.md adicionado** (coluna `Vision §`)
12. ✅ **Critical path & short-circuit explicitados** (P01 elegível 05-26 sem aguardar Wave 2)
13. ✅ **E05 → E07 dependência explícita** (edge typing active antes de impact CLI)
14. ✅ **E09 → E05 active dependência explícita** (auto-keywords não pode poluir enum closed)

Este arquivo é a **fonte mestre**. Cross-refs:
- **`docs/HANDOFF.md`** — estado vivo + próxima ação imediata
- **`docs/DECISIONS.md`** — porquê + NÃO FAZEMOS + lições
- **`docs/VISION.md`** — long-term thesis (nox-neural-memory v14)
- **`docs/ARCHITECTURE.md`** — system design overview
- **`docs/RUNBOOKS.md`** — incident playbooks
- **`CLAUDE.md`** — regras críticas operacionais 1-15
- **`plans/_archive/`** — v1.6, v1.5, ClawMem analysis (referência histórica)
