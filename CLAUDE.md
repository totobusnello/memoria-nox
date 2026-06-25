# memoria-nox — Evolução do nox-mem

> **"Pain-weighted hybrid memory with shadow discipline — yours by design."**
>
> **Q/A/P architecture** (pivot 2026-05-17). 3 pilares: **Quality** (números #1) / **Autonomy** (data sua, provider sua escolha, zero vendor lock-in) / **Product** (UX que ganha). + Lab (40% capacity, retrieval research). + GTM Phase 2 (gated, conditional on Q4 COMPARISON winning).
>
> Detalhes: `docs/ROADMAP.md`. v1 pré-pivot arquivado: `docs/_archive/ROADMAP-v1-pre-Q-A-P-2026-05-17.md`.

---

## Sat 2026-05-24 Closure Summary

**Delivered:** Q4 honest framing (#296) + preflight timeouts (#295) + A2 Tier 3 P2-P5 migration (#286, #294, #292-293, #291) + F10 Phase D (#291) + schema pins + 6 critical learnings consolidated.

**Sat learnings crystallized:**
1. Worktree sparse-checkout root cause → `/tmp/<task>-clone` pattern
2. Shared corpus_loader canonical pattern enforcement
3. Honest cross-system framing (mem0 concentration vs nox-mem coverage)
4. Blocking ops explicit timeout wrapper (run-sat-q4 fix)
5. SQLite PRAGMA key cannot retrofit to plaintext (migration via VACUUM INTO)
6. VACUUM INTO + ATTACH reverse pattern (better-sqlite3 limitation)

**Status:** Q4 run ready. Phase 2 gate methodology finalized (nDCG@10 + coverage threshold). Roadmap unchanged, capacity on track.

## Escopo deste repo
APENAS evolução do **nox-mem** (sistema de memória inteligente):
- Schema (chunks, FTS5, sqlite-vec, KG)
- Search (hybrid: BM25 + Gemini semantic + RRF)
- Salience formula (recency × pain × importance)
- Embeddings (Gemini 3072d)
- KG entities + relations
- Paper técnico
- Specs e decisões arquiteturais de memória

Quando produtizar (Hotmart/instalador/marketing) → migra pra `nox-supermem/`.

## NÃO pertence aqui (movido em 2026-05-01)

| Tema | Repo correto |
|---|---|
| OpenClaw upgrade, gateway, monkey-patch, RelayPlane, Max OAuth, fallback chain, channels/plugins/hooks da plataforma | `~/Claude/Projetos/openclaw-vps/infra/` |
| Captura WhatsApp/Slack, daily briefing, action items, reuniões iPhone | `~/Claude/Projetos/openclaw-vps/nox-secretary/` |
| Multi-agent personas (Atlas, Boris, Cipher, Forge, Lex), sessions, AGENTS.md, SOUL.md | `~/Claude/Projetos/openclaw-vps/infra/` |
| Produto comercial NOX-Supermem (tiers, Hotmart, marketing) | `~/Claude/Projetos/nox-supermem/` |

## Onde fica cada coisa

**Canônicos (ler nessa ordem pra retomar):**

| Conteúdo | Arquivo |
|---|---|
| Estado vivo + próxima ação | **`docs/HANDOFF.md`** ← começar aqui |
| Roadmap (o que vem, capacity, gates) | **`docs/ROADMAP.md`** |
| Decisões + NÃO FAZEMOS + razões | **`docs/DECISIONS.md`** |
| Regras críticas operacionais | **este arquivo** |
| Visão estratégica (longo prazo) | `docs/VISION.md` (v14) |

**Referência:**

| Conteúdo | Arquivo |
|---|---|
| Histórico de versões (v1.0 → v3.6d) | `docs/EVOLUTION.md` |
| Incident log (memoria-only) | `docs/INCIDENTS.md` |
| Convenções detalhadas | `docs/CONVENTIONS.md` |
| Specs técnicos | `specs/*.md` |
| Audits de schema/search/KG | `audits/*.md` |
| Paper técnico | `paper/paper-tecnico-nox-mem.md` / `.docx` |

**Histórico arquivado:**

| Conteúdo | Arquivo |
|---|---|
| Plans antigos (25 arquivos) | `plans/_archive/` |
| Handoffs antigos | `handoffs/_archive/` |

## Estado atual nox-mem (v3.8, sincronizado 2026-05-24)

**Path na VPS:** `/root/.openclaw/workspace/tools/nox-mem/`
**Stack:** TypeScript, better-sqlite3, FTS5, sqlite-vec, Gemini embeddings (3072d), inotifywait
**Plataforma onde roda:** ver `~/Claude/Projetos/openclaw-vps/infra/CLAUDE.md`

### A2 Tier 3 Status (Encrypted Backups — 2026-05-24)
- **P1 (Spec):** ✓ Merged (#258)
- **P2 (Migration script + VACUUM INTO):** ✓ Deployed (#286 — reverse pattern due to better-sqlite3 ATTACH limitation)
- **P3 (reads_audit wrapper + retention sweep):** ✓ Deployed (#292, #293)
- **P4 (Ed25519 checkpoints):** ✓ Deployed (#294)
- **P5 (Dashboard + monitoring):** Deferred to Phase B (GTM Phase 2 dependent)
- **Canary test (PR #280):** Plaintext → encrypted migration validated. Key lesson: PRAGMA key cannot retrofit existing DB — must migrate via atomic VACUUM INTO

### Schema (V7)
- `chunks` + `chunks_fts` (FTS5) — **94.9k chunks** ativos (sincronizado 2026-06-04 pós-limpeza _retired; jun teve bulk import Mac workspace +34k via watcher sem allowlist → 5.6k de skills aposentadas removidos com snapshot — ver INCIDENTS 2026-06-04)
- `vec_chunks` + `vec_chunk_map` (sqlite-vec, 3072d) — ~99.97% coverage
- `kg_entities` (~15.6k) + `kg_relations` (~21.5k) — Gemini 2.5 Flash extraction (incremental nightly; sincronizado 2026-06-04)
- **Schema v10** (2026-04-23): `retention_days` v8 + `pain` v9 + `section` v10
  - `retention_days` — typed retention (feedback/person=NULL never-decay, lesson 180d, decision/project 365d, team 120d, daily 90d, pending 30d, graph_node 60d, default 90d)
  - `pain` REAL DEFAULT 0.2 — severity 0.1 trivial → 1.0 prod-outage
  - `section` TEXT + `section_boost` REAL — entity file format (compiled/frontmatter/timeline/NULL). SECTION_BOOST={compiled:2.0, frontmatter:1.5, timeline:0.8, legacy:1.0}
- **Salience formula v2 aditiva (mode `active` em prod desde ~2026-05-19)**: importance 0.55 + recency 0.15 + pain 0.10 + access 0.20, exposta em `/api/health.salience`. Consumida como produto pelo `/api/brief` (F1, 2026-06-04)
- **Trigger `trg_chunks_delete_cascade`** — DELETE em chunks limpa vetores (não remover)

### Hybrid Search (3 camadas)
FTS5 BM25 → Gemini semantic (gemini-embedding-001) → RRF fusion (k=60)

### Interfaces
- **CLI (26+ cmds):** search/ingest/**ingest-entity**/reindex/vectorize/kg-*/cross-*/reflect/crystallize... (`nox-mem --help`). **Entry point é `dist/index.js`** (package.json.bin), não cli.js — confusão comum. `ingest-entity <file>` adicionado 2026-04-24.
- **MCP Server (16 tools):** `nox_mem_search`, `stats`, `kg_build`, `cross_search`, `reflect`, etc.
- **HTTP API (porta 18802):** `/api/{health,search,kg,kg/path,agents,cross-kg,reflect,procedures}` + `POST /api/crystallize{,/validate}`
- **Dashboard:** github.com/totobusnello/agent-hub-dashboard (4 páginas nox-mem)

### Entity file format (referência)
`memory/entities/<type>/<slug>.md` com 3 sections:
1. **frontmatter** YAML (metadata)
2. **compiled** truth section
3. **timeline** events

Ingest via `src/ingest-entity.ts` produz N+2 chunks com `section_boost`. Routing automático em `ingestFile()` desde 2026-04-25 (caller agnóstico).

## Regras críticas (memoria-only)

> Regras OpenClaw plataforma migraram pra `~/Claude/Projetos/openclaw-vps/infra/CLAUDE.md`.

### 1. Antes de rodar `nox-mem` CLI em SSH/cron/script

`set -a; source /root/.openclaw/.env; set +a`. Sem isso, vectorize/kg-extract falham silenciosamente ("Done: 0 embedded, N errors" na última linha).

### 2. Verificar estado real pós-operação de memória

`curl http://127.0.0.1:18802/api/health | jq .vectorCoverage` — confirmar `embedded == total`. Nunca confiar na última linha do CLI.

### 3. Modelo Gemini padrão: `gemini/gemini-2.5-flash-lite`

NUNCA voltar pra `gemini-2.5-flash` (quota 3M/d estoura) nem `gemini-2.0-flash` (deprecated, shutdown 2026-06-01). KG extraction pode usar `gemini-2.5-flash` full enquanto volume baixo.

### 4. `nox-mem-api` escuta em :18802

Não 18800 — Chrome squata. Nunca hardcode; ler `NOX_API_PORT` do .env.

### 5. Nunca introduzir ranking/scoring change em commit de "fix"

Scoring é feature work (prefix `tune(search):` ou `feat(search):`). Boost multiplicativo empilhável é veneno — usar aditivo. Violação causou incident v3.4.

### 6. Operações destrutivas em chunks só com `--dry-run` ou snapshot atômico

Lição do incident 2026-04-25 (reindex.ts wipou section/retention de 183 entities; root cause = end-of-day cron diário rodava `nox-mem reindex` sem rede de proteção). Antes de `reindex`, `consolidate`, `compact`, `crystallize`, `kg-prune` em prod: ou rodar com `--dry-run` (preview JSON, não muta) OU usar `withOpAudit()` wrapper que cria snapshot atômico em `/var/backups/nox-mem/pre-op/<op>-<ts>-<pid>-<uuid>.db` (retention 7d, ACL 0600, dir 0700, snapshot path validation symlink-aware via realpathSync). Backup-all.sh 02:00 NÃO conta — é diário, não pré-op. Ingest-router unified (Fase A2 v1.6) rota entity files via `ingestEntityFile()` automaticamente; sem ele, `ingestFile()` genérico zera section/retention. Validar pós-op com `/api/health.sectionDistribution.compiled == 183`.

**Recovery via `safeRestore()`** em `src/lib/op-audit.ts` — valida `user_version` match + restaura main DB primeiro + remove WAL/SHM órfãos depois (W2-4 fix 04-26: ordem importa). NÃO fazer `cp snapshot.db nox-mem.db` direto (corrompe se WAL stale).

**Override emergencial:** `NOX_ALLOW_NO_SNAPSHOT=1` no env permite rodar op destrutiva mesmo se snapshot falhar (ex: disk full + emergency reindex) — usar SÓ se snapshot falhou por motivo legítimo conhecido, nunca como atalho.

Audit log `ops_audit` é **append-only** (W2-1 trigger CWE-693): DELETE bloqueado, UPDATE bloqueado em rows com status terminal.

**Status enum válido (validado via DB triggers 2026-04-29):** `'started'` (inicial), `'success'` (terminal OK), `'failed'` (terminal erro app), `'crashed'` (terminal erro sistema). `'completed'` e `'rolled_back'` NÃO são status válidos apesar de docs antigas mencionarem.

Detalhes incident: `docs/INCIDENTS.md#2026-04-25`. Audits pós-fix: `audits/2026-04-25-A1-A2-review.md` + `audits/2026-04-26-{A1v2-A3-A4-A5-review,7highs-followup-fix,W2-cleanup}.md`.

### 7. Sed nunca em arquivos .db

`sed -i` em SQLite corrompe page boundaries. Filter `grep -rl | grep -E '\.(json|md|sh|txt|jsonl|env)$'`. Recovery via pre-vacuum backup outside sweep scope. Lesson 2026-05-01.

## Roadmap canônico

**Single source of truth:** `docs/ROADMAP.md`.
- "O que vem, ordem cronológica, capacity, gates" → `docs/ROADMAP.md`
- "Por quê / NÃO FAZEMOS / decisões arquiteturais" → `docs/DECISIONS.md`
- "Estado vivo + próxima ação" → `docs/HANDOFF.md`
- "Visão estratégica longo prazo" → `docs/VISION.md` (v14)

Histórico de pensamento (não operacional) em `plans/_archive/`.

## Convenções de workflow

- Specs e plans usam formato **Superpowers** (checkbox tasks, chunk boundaries)
- Todos os módulos respeitam `OPENCLAW_WORKSPACE` env var
- Hybrid search é o padrão (`--no-hybrid` para desabilitar)
- Forge faz code review via PRs no GitHub
