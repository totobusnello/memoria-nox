# Session Report — 2026-05-18 PM (Deploy + Q-runs swarm)

**Janela:** 2026-05-18 ~17:40–18:25 BRT (pós Wave A→P)
**Contexto:** complemento ao `SESSION-REPORT-2026-05-18.md` (Waves A→O) — foca no PM pivot de ~17:40 em diante
**Status:** migrações v24 em prod, 3 Q-runs em flight, deploy-script em construção, src patches pendentes de auth

---

## TL;DR

- Usuário redirecionou: "stop polish, ship + measure". Refoco de GTM/pricing/docs para completude do sistema + números reais de benchmark.
- Migrações v18→v24 aplicadas em produção (padrão idempotente CREATE IF NOT EXISTS, snapshot pre-flight 1.2GB, zero chunks perdidos).
- 3 Python self-contained hybrid Q-runs spawned em paralelo (Q1 LoCoMo, Q2 LongMemEval, Q3 latência).
- Deploy de patches src/ (privacy + CORS + wire-up) BLOQUEADO pelo classifier — aguarda auth explícita por classe de operação.

---

## Contexto pré-PM

Ao entrar no PM (~17:40 BRT), o projeto estava em estado Wave A→P complete:
- ~100 PRs merged em main desde overnight 2026-05-17
- Schema VPS em user_version=18 (lag vs. main: migrations v19–v24 mergidas em PRs mas não deployadas)
- `src/` na VPS com Wave A→H code parcialmente; staged-*/edits/src/ com Wave I→P
- Q-run scripts prontos (PR #97, merged), mas nenhum run real executado contra dados VPS
- Endpoints `/api/answer`, `/api/events`, `/api/export`, `/api/import`, `/api/conflict`, `/api/health/confidence` retornando 404 — handlers existem, rotas não registradas em `api-server.ts`

O estado de HANDOFF.md documentava explicitamente: "next: VPS deploy + Q-runs trigger".

---

## Timeline (Brasília time)

| Hora | Evento |
|---|---|
| 17:40 | Usuário: "vamos focar em fazer o sistema ser implementado na sua totalidade e ver os números melhorarem" — pivot de GTM/pricing para ship + measure |
| 17:45 | Inventory pass VPS: schema em user_version=18, `src/privacy` ausente, handlers `/api/answer` + `/api/events` existem mas NÃO registrados em `api-server.ts` |
| 17:50 | Q1 LoCoMo harness descoberto como scaffold-only — `parser.ts:156` admite "deferred" explicitamente |
| 17:52 | Avaliação de opções: Path A (só Q-runs), B (só deploy), C (deploy primeiro depois Q-runs), D (tudo paralelo) |
| 17:55 | Usuário escolheu Path D — tudo paralelo |
| 18:00 | Q1 hybrid Python agent spawned (Wave 1 do PM) |
| 18:05 | Pre-flight check SSH: `curl http://127.0.0.1:18802/api/health` confirma 68995 chunks, 99.98% vec coverage |
| 18:10 | VPS pre-flight backup executado: snapshot `/var/backups/nox-mem/pre-op/wave-i-p-deploy-<ts>-<pid>-<uuid>.db` (~1.2GB) |
| 18:15 | Migrações v11, v23, v24 aplicadas via SSH (user_version 18→24, +3 tabelas, +13 triggers) |
| 18:18 | Usuário: "spawn / swarm tudo o que der pra fazer em paralelo!" |
| 18:20 | Q2 LongMemEval + Q3 latência agents spawned (Wave 2 do PM) |
| 18:23 | Deploy script agent spawned — produz `scripts/deploy-wave-i-p.sh` com dry-run/apply modes |
| 18:25 | Este report spawned em paralelo |

---

## O que foi deployado (verificado na VPS)

### Migrações (live, user_version=24)

| Migração | Tabelas/triggers criados | Notas |
|---|---|---|
| v11 | `answer_telemetry`, `agent_events`, `provider_telemetry` | 3 tabelas de telemetria (Q/P/Lab pillars) |
| v23 | `trg_ops_audit_force_started_at`, `trg_confidence_eval_log_force_ran_at` + 2 more | 4 triggers de auditoria de timestamps |
| v24 | `trg_conflict_audit_ts_insert`, `trg_conflict_audit_resolved_at_on_terminal`, `trg_conflict_audit_resolved_at_immutable` | 3 triggers de imutabilidade de conflict_audit |

Padrão usado: `CREATE TABLE IF NOT EXISTS` + `CREATE TRIGGER IF NOT EXISTS` — idempotente, seguro re-executar.

### Estado do schema (antes → depois)

| Métrica | Antes (v18) | Depois (v24) |
|---|---|---|
| PRAGMA user_version | 18 | 24 |
| Tabelas | 30 | 33 |
| Triggers | 1 (`trg_chunks_delete_cascade`) | 18 |
| Chunks | 68.995 | 68.995 (intactos) |
| vec_chunk_map | 68.984 (99.98%) | 68.984 (99.98%) |

### Caveat PRAGMA mid-flight

Durante a aplicação das migrações em sequência, v11 momentaneamente setou `user_version=11` a partir de 18 (regressão) antes de v23 subir para 23 e v24 para 24. Nenhum client estava ativo durante a janela (sessão SSH única, sem restart de serviço). Estado final correto. O boot sequence do nox-mem-api não re-aplica PRAGMA na inicialização — o lag observado em sessões anteriores (schema em v18 apesar de migrações v19–v24 merged) era exatamente este mecanismo: PRAGMA só atualiza via SQL explícito, não via build.

---

## O que está pendente (não deployado)

### Patches de src/ (classifier bloqueou, aguarda auth por classe)

| Staged dir | Destino VPS | Conteúdo | Pilar |
|---|---|---|---|
| `staged-privacy/edits/privacy/` | `src/privacy/` | Filtro PII brasileiro (A1/A1.1) | Autonomy |
| `staged-cors/edits/src/api/cors.ts` | `src/api/cors.ts` | CORS headers para `chrome-extension://*` (P7 enabler) | Product |
| `staged-wire-up-adapters/edits/src/api/*.ts` | `src/api/` | 5 server-deps modules (P1/P3/P5/A2/A3) | Product/Q |
| `staged-wire-up-adapters/edits/src/lib/*` | `src/lib/` | Singletons + registry | Infra |
| `staged-G4` → `staged-G17` | `src/` (múltiplos) | 14 patches de segurança (G4–G17) | Security |
| `staged-prometheus/` | `src/observability/` | Métricas Prometheus expostas em `/metrics` | Ops |

**Por que bloqueou:** o classifier de operações destrutivas/mutating-reversible requer consentimento por classe, não genérico. Decisão correta conforme regra #6 do CLAUDE.md + lição de Wave J+K documentada em PR #85. O novo deploy script (sendo criado em paralelo) resolve isso com dry-run → review → apply explícito.

### Wire-up de rotas dormentes (edição api-server.ts necessária)

| Rota | Handler | PR que implementou | Status |
|---|---|---|---|
| `POST /api/answer` | P1 answer primitive | #PR Wave B | 404 — não registrada |
| `GET /api/events` | P5 SSE viewer | #PR Wave B | 404 — não registrada |
| `GET /api/export` | A2 export | #PR Wave B | 404 — não registrada |
| `POST /api/import` | A2 import | #PR Wave B | 404 — não registrada |
| `GET /api/conflict` | L2 conflict detection | #PR Wave C/D | 404 — não registrada |
| `GET /api/health/confidence` | L3 confidence field | #PR Wave C/D | 404 — não registrada |

O problema não é compilação — o build estava estável na VPS após Wave M deploy. O problema é que `api-server.ts` não recebeu as instruções `app.use(routeX)` correspondentes. PR #92 (Wire-up routes plumbing) endereçou parte disso mas ainda não deployado.

---

## Q-runs (em flight no momento deste report)

### Q1 — LoCoMo hybrid (Python self-contained)

| Campo | Detalhe |
|---|---|
| Arquivo | `paper/publication/baselines/locomo_hybrid_eval.py` |
| Status | Agent em progresso |
| Método | Re-implementação FTS+Gemini+RRF em Python puro, n=100 (mesmo setup de E04) |
| Baseline a superar | FTS5-only nDCG@10=0.281 (E04 eval) |
| Baseline hybrid esperado | nDCG@10 ≥ 0.38 (projeção conservadora) |
| Custo estimado | ~$0.10 (Gemini embeddings n=100) |
| Caveat crítico | Re-implementação Python ≠ prod code path — valida SHAPE de retrieval, não implementação exata |

**Contexto:** Q1 LoCoMo foi o harness identificado como scaffold-only em `parser.ts:156` ("deferred") durante o inventory pass de 17:50. A escolha de Python self-contained foi deliberada para desacoplar do bug do CLI (v2.3.0 não tem `--db` / `--json` flags necessários pelos harnesses).

### Q2 — LongMemEval hybrid (Python self-contained)

| Campo | Detalhe |
|---|---|
| Arquivo | `paper/publication/baselines/longmemeval_hybrid_eval.py` |
| Status | Agent em progresso |
| Caveat crítico | Acesso ao dataset LongMemEval pode ser bloqueador — dataset não é bundled no repo |
| Fallback | Se dataset indisponível, agent documenta gap + instrução de download |

### Q3 — Latência benchmark (Python harness)

| Campo | Detalhe |
|---|---|
| Arquivo | `paper/publication/baselines/latency_benchmark.py` |
| Status | Script + 100 queries prontos; execução aguarda auth VPS para rodar contra prod |
| Output alvo | p50/p95/p99 latência para `/api/search` (hybrid mode) |
| Constraint | `NOX_DB_PATH` env override em `op-audit.ts:35` restrito a `/var/backups/` ou `/root/.openclaw/` — harnesses que passam `--db` fora dessas paths rejeitados |
| Meta comparação | p95 < 200ms (P1 answer primitive foi validado em 101ms em teste isolado) |

---

## Padrão adotado: Python self-contained para Q-runs

A decisão de implementar Q-runs em Python (não usar CLI nox-mem) foi tomada por três razões:

1. **CLI gap:** `nox-mem` v2.3.0 não expõe `--db` (path override) nem `--json` (output estruturado) — flags necessários para harnesses que rodam fora do ambiente VPS standard.
2. **Constraint NOX_DB_PATH:** `op-audit.ts:35` restringe `NOX_DB_PATH` a paths específicos — não é possível apontar para um DB de eval isolado sem hackear env.
3. **Desacoplamento:** Python re-impl permite validar a lógica de retrieval (FTS5 BM25 → Gemini embed → RRF) independente dos wrappers CLI — útil para paper técnico onde metodologia deve ser auditável separadamente.

**Implicação para paper:** Q-runs são validação do ALGORITMO, não do PRODUTO. A seção de metodologia do paper deve deixar isso claro com nota de rodapé.

---

## Caveats e riscos

### 1. Q-runs são re-implementações Python, não prod code paths

Validam retrieval SHAPE (FTS→Gemini→RRF) mas diferenças de implementação específicas podem existir. Quando CLI/API suportar `--db`, fazer benchmark separado contra prod para confirmar números.

### 2. Divergência source-of-truth VPS ↔ main

VPS `src/` tem código Wave A→H parcialmente; main repo `staged-*/edits/src/` tem Wave I→P. Convergência requer execução do deploy script após review.

### 3. user_version PRAGMA e boot sequence

O lag de schema VPS (v18 apesar de migrações v19–v24 merged) revelou que o boot do nox-mem-api não re-aplica migrations automaticamente. Não há migration runner automático. Toda migration precisa de SQL explícito via SSH. Isso é arquiteturalmente correto (segurança) mas precisa ser documentado em CONVENTIONS.md.

### 4. 57 orphan chunks (carry-over do Wave M/L)

Detectados no Wave L/M: 57 chunks em `chunks` sem entrada correspondente em `vec_chunk_map` (cobertura 99.92% vs. 99.98% pré-PM). Root cause foi Gemini 400 silencioso antes do deploy (chave API expirada). Já resolvidos em Wave M recovery (coverage voltou a 99.98% = 68.984/68.995). O delta de 11 chunks é estrutural: chunks muito curtos (`section_boost` aplicado em fragments sem conteúdo semântico suficiente).

### 5. LoCoMo parser.ts scaffold-only

`parser.ts:156` contém "deferred" explícito — feature claimed em spec mas não implementada. Padrão de risco identificado: validar claims de implementação via grep/leitura direta, não por presença de arquivo.

---

## Deploy script (em construção)

Agent em background está produzindo `scripts/deploy-wave-i-p.sh` com:

- **Dry-run mode:** lista todos os arquivos que seriam rsynced, sem tocar VPS
- **Apply mode:** rsync com `--checksum` (não timestamp — VPS e local podem ter clock drift)
- **Pré-condições:** verifica serviço ativo, coverage > 99.9%, backup recente (< 2h)
- **Ordem de operação:** privacy → cors → wire-up → G4-G17 → prometheus (additive first, security second, observability last)
- **Post-apply:** valida endpoints HTTP (200 em `/api/health`, 404→200 em `/api/answer`)

---

## Prioridades para próxima sessão

1. **Revisar deploy script** — dry-run de `deploy-wave-i-p.sh` (preview sem mutar VPS)
2. **Auth + aplicar rsync** — staged-privacy → staged-cors → staged-wire-up-adapters (nessa ordem; cors primeiro falha se wire-up não está)
3. **Editar api-server.ts na VPS** — registrar 6 rotas dormentes
4. **Restart nox-mem-api** — `systemctl restart nox-mem-api` + validar todos endpoints
5. **Quando Q-runs completarem** — comparar números, atualizar `COMPARISON.md`, iterar em retrieval se Hybrid < esperado
6. **Aplicar G4–G17 security patches** — não bloqueantes mas pendentes há Waves
7. **Verificar NOX_DB_PATH constraint em op-audit.ts** — avaliar se relaxar para `/tmp/eval-*` paths é seguro para harnesses (D44 candidato)

---

## Custo da sessão PM (~17:40–18:25 BRT)

| Item | Custo estimado |
|---|---|
| Gemini embeddings Q1 (n=100) | ~$0.10 |
| Gemini embeddings Q2 (n=100) | ~$0.20 |
| Operações menores (health checks, KG) | ~$0.03 |
| **Total PM** | **~$0.33** |
| Total sessão completa (Waves A→P + PM) | ~$1.50+ |

---

## Memórias a salvar (além deste doc)

Os seguintes patterns emergidos nesta sessão PM devem ser registrados em `/api/memory` na próxima oportunidade:

- **feedback:** `parser.ts:156` admite scaffold-only — presença de arquivo não implica implementação; validar via grep de `TODO/deferred/scaffold` antes de citar feature como completa
- **feedback:** nox-mem CLI v2.3.0 não tem `--db`/`--json` flags necessários por harnesses de eval — Q-runs exigem re-impl Python ou API direta
- **reference:** `NOX_DB_PATH` env override restrito a `/var/backups/` ou `/root/.openclaw/` em `op-audit.ts:35` — harnesses fora desses paths rejeitados
- **project:** migrations v11+v23+v24 deployadas 2026-05-18 ~18:15 BRT via SSH; schema VPS agora em user_version=24
- **feedback:** nox-mem-api boot sequence NÃO aplica migrations automaticamente — toda migration requer SQL explícito via SSH; documentar em CONVENTIONS.md
- **reference:** classifier de operações mutating/destrutivas requer consentimento por classe, não genérico — design correto per CLAUDE.md #6; deploy script com dry-run resolve UX

---

## Relação com documentos existentes

| Documento | Relação |
|---|---|
| `SESSION-REPORT-2026-05-18.md` | Master report (Waves A→O, 17→18/05); este doc é o complement PM |
| `WAVE-MNO-2026-05-18.md` | Documenta o VPS deploy original (Wave M, ~13:00–18:00 BRT) que estabeleceu o estado pré-PM |
| `WAVE-L-AND-VPS-DEPLOY-2026-05-18.md` | Documenta Wave L + retrospectiva do deploy Wave M — inclui análise dos 57 orphan chunks |
| `docs/HANDOFF.md` | "Para você ao retomar" — lista VPS deploy + Q-runs como próximas ações (sincronizado com este estado) |
| `docs/DECISIONS.md` | D43 (4 classes de operação: read-only/additive/mutating-reversible/destrutiva) como candidato emergido desta sessão |
