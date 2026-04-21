# memoria-nox — Projeto de Memória Inteligente para OpenClaw

## O que é este repo
Documentação, specs, plans e paper técnico do sistema **nox-mem** (deployado na VPS) e do produto comercial **NOX-Supermem** (em desenvolvimento no repo `nox-supermem`).

## Onde fica cada coisa

| Conteúdo | Arquivo |
|---|---|
| Estado atual + regras críticas | **este arquivo** |
| Histórico de versões (v1.0 → v3.6d) | `docs/EVOLUTION.md` |
| Incident log completo | `docs/INCIDENTS.md` |
| Convenções detalhadas (todas, com contexto) | `docs/CONVENTIONS.md` |
| Specs técnicos | `specs/*.md` |
| Plans de execução | `plans/*.md` |
| Audits de infra | `audits/*.md` |
| Paper técnico | `paper-tecnico-nox-mem.md` / `.docx` |

## Infraestrutura (estado atual — v3.6d, Abr 21)

- **VPS:** `ssh root@100.87.8.44` (Tailscale) ou `187.77.234.79` (público); Hostinger KVM 4
- **Path:** `/root/.openclaw/workspace/tools/nox-mem/`
- **Stack:** TypeScript, better-sqlite3, FTS5, sqlite-vec, Gemini embeddings (3072d), inotifywait, systemd
- **OpenClaw:** v2026.4.15 (binário; requer Node.js 22.12+; **monkey-patched** em `dist/restart-stale-pids-*.js` pra Issue #62028)
- **Node.js:** v22.22.2 com wrapper `--no-warnings` em `/usr/bin/node`
- **RelayPlane:** v1.8.37 ativo em :4100 (budget caps $5/d, $1/h, $0.50/req)

### Serviços ativos (4 + tailscale)
- `openclaw-gateway` :18789 WS → RelayPlane :4100 → providers
- `nox-mem-api` :18802 HTTP (porta via `NOX_API_PORT` no .env)
- `nox-mem-watcher` (inotifywait, debounce 15s) — **único**, watcher legado disabled
- `relayplane-proxy` :4100 (cascade sonnet→haiku→deepseek-r1→qwen3→llama-70b)
- `tailscaled` 100.87.8.44

### Schema (V7)
- `chunks` + `chunks_fts` (FTS5) — **2.5k+ chunks** ativos
- `vec_chunks` + `vec_chunk_map` (sqlite-vec, 3072d) — 100% coverage
- `kg_entities` (~397) + `kg_relations` (~516) — Gemini 2.5 Flash extraction
- **Trigger `trg_chunks_delete_cascade`** — DELETE em chunks limpa vetores (não remover)

### Hybrid Search (3 camadas)
FTS5 BM25 → Gemini semantic (gemini-embedding-001) → RRF fusion (k=60)

### Interfaces
- **CLI (25+ cmds):** search/ingest/reindex/vectorize/kg-*/cross-*/reflect/crystallize... (`nox-mem --help`)
- **MCP Server (16 tools):** `nox_mem_search`, `stats`, `kg_build`, `cross_search`, `reflect`, etc.
- **HTTP API (porta 18802):** `/api/{health,search,kg,kg/path,agents,cross-kg,reflect,procedures}` + `POST /api/crystallize{,/validate}`
- **Dashboard:** github.com/totobusnello/agent-hub-dashboard (4 páginas nox-mem)

### Cron
Runner único às 23:00 via `/root/.openclaw/scripts/nightly-maintenance.sh` (serializa reindex → consolidate → vectorize → kg-build → kg-prune → session-distill). Canário semantic `*/30min`. Health probe `*/5min`. Backup diário 02:00 (7d retention). Logrotate em `/etc/logrotate.d/nox`.

### Multi-agent (6 agentes, DBs isolados)
main + nox/atlas/boris/cipher/forge/lex. Cross-agent search/stats/KG disponível via `nox-mem cross-*`.

## Regras críticas (violação = produção quebra)

> As 10 mais sensíveis ficam aqui. Regras completas em `docs/CONVENTIONS.md`.

1. **Secrets só via env.** Todo `apiKey` em `openclaw.json` / `agents/*/agent/models.json` usa `${VAR_NAME}`. Valores literais estão bloqueados globalmente por gitleaks pre-commit hook. Rotação = `.env` + `systemctl restart openclaw-gateway nox-mem-api nox-mem-watcher`.

2. **Antes de rodar `nox-mem` CLI em SSH/cron/script:** `set -a; source /root/.openclaw/.env; set +a`. Sem isso, vectorize/kg-extract falham silenciosamente ("Done: 0 embedded, N errors" na última linha).

3. **Verificar estado real pós-operação de memória:** `curl http://127.0.0.1:18802/api/health | jq .vectorCoverage` — confirmar `embedded == total`. Nunca confiar na última linha do CLI.

4. **Modelo Gemini padrão: `gemini/gemini-2.5-flash-lite`.** NUNCA voltar pra `gemini-2.5-flash` (quota 3M/d estoura) nem `gemini-2.0-flash` (deprecated, shutdown 2026-06-01). KG extraction pode usar `gemini-2.5-flash` full enquanto volume baixo.

5. **RelayPlane requer DOIS pontos de config:** (a) `ANTHROPIC_BASE_URL=http://127.0.0.1:4100` no `.env`; (b) `providers.anthropic.baseUrl: "http://127.0.0.1:4100"` no `openclaw.json` (sem isso o JSON sobrescreve o env). Crítico pro OAuth Claude MAX (pós-política Anthropic 2026, extra usage cobrado).

6. **Gateway fratricide (Issue #62028, v2026.4.14+):** monkey-patch em `/usr/lib/node_modules/openclaw/dist/restart-stale-pids-*.js` fazendo `cleanStaleGatewayProcessesSync` retornar `[]`. Wrapper em `/usr/local/bin/openclaw-gateway-wrapper` (imutável com `chattr +i`) unset `OPENCLAW_SERVICE_MARKER/KIND`. Config `commands.restart=false` + `gateway.reload.mode=off` + `discovery.mdns.mode=off`. Antes de `npm update -g openclaw`, checar Issue #62028 + re-aplicar patch (hash do arquivo muda).

7. **`nox-mem-api` escuta em :18802** (não 18800 — Chrome squata). Nunca hardcode; ler `NOX_API_PORT` do .env.

8. **Nunca introduzir ranking/scoring change em commit de "fix".** Scoring é feature work (prefix `tune(search):` ou `feat(search):`). Boost multiplicativo empilhável é veneno — usar aditivo. Violação causou incident v3.4.

9. **Nunca editar `openclaw.json` removendo `agents.defaults`** (fallback chain, heartbeat, compaction). Nunca adicionar chaves root novas sem verificar versão do binário na VPS.

10. **Node.js wrapper obrigatório:** `/usr/bin/node` é wrapper bash → `/usr/bin/node.bin --no-warnings`. Sem isso, DEP0040 (punycode) causa crash loop. Se `apt upgrade nodejs` rodar, recriar wrapper (renomear binary para `node.bin`).

## Produto NOX-Supermem

Repo `github.com/totobusnello/nox-supermem` (private), local `~/Claude/Projetos/nox-supermem/`. Mercado Brasil (PT-BR, Hotmart). Tiers A/B/C R$147/197/227 + R$30/sem suporte. Plan de 24 tasks em 4 chunks.

## Convenções de workflow

- Specs e plans usam formato **Superpowers** (checkbox tasks, chunk boundaries)
- Todos os módulos respeitam `OPENCLAW_WORKSPACE` env var
- Hybrid search é o padrão (`--no-hybrid` para desabilitar)
- Forge faz code review via PRs no GitHub
- **SESSION-STATE.md é a fonte única de estado** (`session-context.json` e `active-tasks.md` deprecated)
- Scripts permanentes em `/root/.openclaw/scripts/` (nunca /tmp/)
