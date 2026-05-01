# nox-mem — Convenções Detalhadas

> Regras expandidas do **nox-mem core** com contexto + razão + exemplos. CLAUDE.md mantém as críticas inline; as demais ficam aqui como referência via `Read docs/CONVENTIONS.md`.
>
> ⚠️ Convenções de **plataforma OpenClaw** (gateway, RelayPlane, monkey-patch, multi-agent, heartbeat, systemd) migraram pra `~/Claude/Projetos/openclaw-vps/infra/`. Versão mestra pré-split preservada em `_archive-pre-split-20260501/CONVENTIONS.md.bak`.

## Ranking / Scoring / Busca

### Nunca introduzir mudança de ranking/scoring em commit de "fix"
Scoring changes são feature work e precisam: (a) commit separado com prefix `tune(search):` ou `feat(search):`, (b) menção explícita no relatório, (c) A/B em 5 queries antes/depois. Violação causou incident v3.4 (`SOURCE_TYPE_BOOST` escondido em commit `d764009`).

### Boost multiplicativo é veneno quando empilhável
`search.ts` já tem TIER × BOOST_TYPES × recency (~7×). Adicionar mais um multiplicativo colapsa top-N. Se precisar ponderar por nova dimensão:
- **Aditivo:** `score += bonus`
- **Normalizar:** `score /= soma_pesos`

Ver `shared/lessons/2026-04-19-boost-stacking-and-fake-green.md`.

### Hybrid search é o padrão
`--no-hybrid` para desabilitar.

### Teste canário semântico obrigatório pós-operação
Depois de qualquer operação que toca chunks (consolidation, dedup, re-ingest), validar que `curl /api/search?q=...` retorna pelo menos 1 resultado com `match_type: "semantic"`. Canário automático em `/root/.openclaw/scripts/semantic-canary.sh` roda `*/30 * * * *`. Query PT-BR, não inglês (lição v3.4).

**Self-heal ativo (v3.6):** ao detectar `total=0` ou `semantic=0`, dispara `timeout 300 nox-mem vectorize` + lockfile + re-query; alerta Discord como `**auto-healed**` (sucesso) ou `FAILED — manual intervention needed` (falha). Exit codes: 0=ok/healed, 1=API down, 2=parse error, 3=still-empty, 4=semantic-still-down, 5=orphans.

## Embeddings / Database

### Embedding em massa sempre via `embedBatchAPI`
`batchEmbedContents` do Gemini. Nunca loop serial. Batch 50, pause 1s = ~26 chunks/s estável sem 429.

### Trigger `trg_chunks_delete_cascade` nunca remover
`AFTER DELETE ON chunks` garante que DELETE limpa `vec_chunks` + `vec_chunk_map`.

### `/api/health.vectorCoverage` embedded via JOIN
Deve reportar `embedded` via `JOIN chunks × vec_chunk_map` (não COUNT sobre vec_chunk_map sozinho — conta órfãos).

### `busy_timeout=5000ms` obrigatório em `db.ts`
Sem isso, SQLITE_BUSY silencioso sob contenção (watcher + api + CLI escrevendo em paralelo).

### KG v2 LLM extraction
Via **Gemini 2.5 Flash** (migrado de Ollama 2026-04-11) — superior a regex.

### `dist/reindex.js` patchado pra auto-vectorize (2026-04-21, v3.6)
`import { vectorize } from "./vectorize.js"` no topo + bloco `try/catch` depois do restore metadata e antes de `closeDb()` chama `await vectorize()`. Sem esse patch, `DELETE FROM chunks` cascadeia via trigger e deixa `vec_chunks` vazio até alguém rodar vectorize manualmente. **Após `npm update` ou reinstall do nox-mem, verificar se patch persiste** — senão re-aplicar. Backup: `dist/reindex.js.bak-pre-autovectorize-20260421`.

### `nightly-maintenance.sh` Phase 6 diária (v3.6)
Roda `nox-mem vectorize` (idempotente) no fim de todo nightly. Safety net caso o auto-vectorize do reindex falhe. Não remover.

### `nightly-maintenance.sh` DB path correto
`/root/.openclaw/workspace/tools/nox-mem/nox-mem.db` (NÃO `.../workspace/nox-mem.db` — esse é arquivo 0 bytes legado).

## Ambiente / Env Vars

### Antes de qualquer `nox-mem` CLI via SSH/cron/script
`set -a; source /root/.openclaw/.env; set +a`. Sem isso, `GEMINI_API_KEY`/`ANTHROPIC_API_KEY`/etc. não estão no process env → vectorize/kg-extract falham silenciosamente batch a batch. **Sintoma:** CLI mostra progresso mas log final é `Done: 0 embedded, N errors` (lição v3.4).

### Verificar estado real pós-operação de memória
Depois de reindex/vectorize/consolidate, rodar `curl http://127.0.0.1:18802/api/health | jq .vectorCoverage` e confirmar `embedded == total`. **Nunca** confiar na última linha do CLI — ler a contagem de erros.

## Modelos (memoria-only)

### Modelo Gemini de uso geral em crons/heartbeats do nox-mem
`gemini/gemini-2.5-flash-lite` (migrado 2026-04-20). **Nunca** voltar pra:
- `gemini-2.5-flash` (quota 3M/dia estoura)
- `gemini-2.0-flash` (deprecated "no longer available to new users" 2026, shutdown 2026-06-01)

KG extraction pode continuar com 2.5 Flash full enquanto volume baixo.

## Serviços / Portas (nox-mem)

### nox-mem-api escuta em :18802
Não 18800 — Chrome remote-debugging squata 18800. **Nunca hardcode a porta; ler de `NOX_API_PORT` no `.env`.**

### Um watcher só (v3.6)
`nox-mem-watcher.service` é o ativo (enabled, executa `nox-mem-watch.sh`). `nox-mem-watch.service` foi stopped+disabled (era duplicata). Auditoria mensal: `systemctl list-units --type=service | grep -i watch`.

## Logs / Backups (nox-mem)

### Logrotate cobre nox-mem.log (weekly, 8 rotations)
Em `/etc/logrotate.d/nox`. Se mudar paths de log, atualizar essa config.

## Git

### Specs e plans usam formato Superpowers
Checkbox tasks, chunk boundaries.

### Todos os módulos respeitam `OPENCLAW_WORKSPACE` env var

### Forge agent faz code review via PRs no GitHub

## chunk_type — enum canônico (B3-5, 2026-04-26)

> Tipos de chunk são uma **decisão de design**: cada tipo carrega retention default + behavior de ingest + relevância pra crons (consolidate filtra `daily`, etc). Não criar tipo novo sem atualizar matriz aqui + `src/retention.ts:RETENTION_BY_TYPE` + `migrateToV8` no `db.ts`.

### Tipos canônicos (schema v10)

| `chunk_type` | retention default | Origem (ingest) | Notes |
|---|---|---|---|
| `feedback` | NULL (never-decay) | `memory/feedback.md` ou via `--type=feedback` no ingest | Evidência preservada — user feedback, lições críticas |
| `person` | NULL (never-decay) | `memory/people.md`, entity files type=person | Ontologia estável de pessoas |
| `lesson` | 180d | `memory/lessons.md`, entity files type=lesson | Mistakes caros merecem 6 meses |
| `decision` | 365d | `memory/decisions.md`, entity files type=decision | Decisões têm lifespan longo |
| `project` | 365d | `memory/projects.md`, entity files type=project | Projetos ativos |
| `daily` | 90d | session daily notes (`memory/2026-MM-DD.md`) | Único iterado pelo `consolidate` loop real |
| `team` | 120d | shared/notes per-team | Estado de time evolui |
| `digest` | 180d | output do `nox-mem digest` (weekly) | Consolidação semanal |
| `pending` | 30d | `memory/pending.md`, entity files type=pending | Se 30d sem resolver, escala pra review |
| `graph_node` | 60d | `graphify-ingest` em repos externos | Research-like, decay rápido |
| `other` | 90d (default) | Qualquer file não classificável | Fallback do `RETENTION_BY_TYPE` |

### Adicionar tipo novo (workflow)

1. Adicionar entry em `src/retention.ts:RETENTION_BY_TYPE` com retention apropriada
2. Atualizar `migrateToV8` em `src/db.ts` se houver backfill heurístico (UPDATE por `source_file LIKE`)
3. Atualizar tabela acima neste arquivo
4. Se o ingest precisa de path-based dispatch: adicionar handler em `src/lib/ingest-router.ts:routeIngest()` (Fase A2 v1.6)
5. Atualizar canary `check-schema-invariants.sh` se houver invariant pra esse tipo (ex: feedback NULL sempre)
6. Bumpar `SCHEMA_VERSION` em `db.ts` SE estiver mudando schema (não só seed)

### Ingest-router unified (Fase A2 v1.6, 2026-04-25)

Single dispatch point: `src/lib/ingest-router.ts:routeIngest(file, opts)` rota automaticamente:
- `memory/entities/<type>/*.md` → `ingestEntityFile()` (3-section format: frontmatter + compiled + timeline)
- `*.md` (genérico) → `ingestFile()` com chunk_type inferido por path/frontmatter
- `*.json` → `ingestFile()` com chunk_type=`other`
- `--force-kind=graphify` (futuro) → `graphifyIngest()` (não wrapped ainda — Wave 2)

Callers: watch.ts (file events), reindex.ts (loop), index.ts CLI `ingest`/`ingest-entity`, mcp-server.ts.
**Nunca** chamar `ingestFile()` diretamente em loop sem passar pelo router — A2 fix do incident 2026-04-25 expôs isso.
