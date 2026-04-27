# memoria-nox

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Last Commit](https://img.shields.io/github/last-commit/totobusnello/memoria-nox)](https://github.com/totobusnello/memoria-nox/commits/main)
[![Tests](https://img.shields.io/badge/tests-27%20passing-brightgreen)](docs/HANDOFF.md)
[![Schema](https://img.shields.io/badge/schema-v10-blue)](CLAUDE.md)
[![Improvements](https://img.shields.io/badge/improvements-13%2F13%20OK-brightgreen)](docs/HANDOFF.md)

> Sistema de memória inteligente multi-agent com hybrid search, knowledge graph e backend claude-cli zero-cost.

---

## Por que isso existe

Agentes AI sem memória persistente repetem erros, perdem contexto entre sessões e tratam cada conversa como se fosse a primeira. Quando você escala pra 7 agentes com papéis distintos, o problema multiplica: memórias fragmentadas por agente, rankings de busca frágeis que quebram sem aviso, drift de schema em ops destrutivas.

**nox-mem** resolve isso com uma camada de memória canônica compartilhada: a tabela `chunks` é a fonte única de verdade. O knowledge graph (`kg_entities` + `kg_relations`) é derivado via extração Gemini — não um silo separado. Qualquer mudança de ranking passa por shadow-mode obrigatório de 7 dias antes de ativar. Ops destrutivas criam snapshot atômico pré-execução via `withOpAudit()`.

O resultado é um sistema que, na prática, resiste a upgrades de infra, patches de segurança, incidents reais e mudanças de equipe sem perder memória acumulada — 20.831 chunks, 99,2% embedded, 318MB de DB em produção na VPS desde v1.0.

---

## Arquitetura

```
INPUTS
─────────────────────────────────────────────────────────────────────
  graphify CLI          nox-mem-watcher           nox-mem ingest
  (knowledge graph      (inotifywait,              (CLI manual,
   extraction)          debounce 15s)              MCP tools)
        │                     │                          │
        └──────────────────── routeIngest() ─────────────┘
                               (ingest-router unified)
                                       │
                           ┌───────────▼───────────┐
STORAGE                    │  chunks (FTS5 + BM25)  │◄─── ops_audit
─────────────────────────  │  vec_chunks (3072d)    │     (append-only,
                           │  kg_entities  (~402)   │     SQL triggers,
                           │  kg_relations (~544)   │     CWE-693)
                           └───────────┬───────────┘
                                       │
                             hybrid search pipeline
SEARCH                    ┌────────────▼────────────┐
──────────────────────    │  FTS5 BM25               │
                          │    + Gemini semantic      │
                          │    + RRF (k=60)           │
                          │    + MMR (λ=0.7)          │
                          │    + temporal decay       │
                          │    + salience weight      │
                          │      (recency×pain×imp)   │
                          └────────────┬────────────┘
                                       │
OUTPUTS                  ┌─────────────┼─────────────┐
──────────────────────   │             │              │
                    16 MCP tools  HTTP API       CLI (26+ cmds)
                    (nox_mem_search  :18802       search / ingest /
                     kg_build        /api/        reindex / reflect /
                     reflect         health       crystallize /
                     cross_search    search       kg-build / cross-* ...)
                     ...)            kg/path
                                     agents)
                                       │
                               ┌───────▼───────┐
AGENTS                         │  main (Maestro) │
──────────────────             │  nox  | atlas   │  cross-agent
                               │  boris| cipher  │  search/stats/KG
                               │  forge| lex      │  ativo
                               └───────────────┘
```

---

## Quick start

```bash
# Verificar estado do sistema
ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq'

# Audit de improvements (13/13 baseline)
ssh root@100.87.8.44 '/root/bin/improvements check'

# Buscar na memória
ssh root@100.87.8.44 'set -a; source /root/.openclaw/.env; set +a; nox-mem search "sua query" --hybrid'
```

---

## Funcionalidades principais

- **Hybrid search** — FTS5 BM25 + Gemini semantic (gemini-embedding-001, 3072d) + RRF fusion (k=60); pure-vector e lexical-only falham silenciosamente em casos opostos
- **Cross-agent search** — 7 agentes com DBs isolados, busca/stats/KG compartilhados via `nox-mem cross-*`
- **Knowledge graph** — Gemini 2.5 Flash extraction, ~402 entidades, ~544 relações, enum fechado de 7 tipos de relação
- **Salience-weighted retrieval** — fórmula multiplicativa `recency × pain × importance`; shadow-mode 7d antes de ativar (gate 2026-04-30)
- **Section boost** — entity files com seções `compiled` (2.0×) / `frontmatter` (1.5×) / `timeline` (0.8×)
- **Shadow-mode safety** — qualquer mudança de ranking requer `NOX_*_MODE=shadow` + baseline 7d em `/api/health` antes de ativar
- **Append-only audit log** — `ops_audit` com SQL triggers CWE-693: DELETE e UPDATE em rows terminais bloqueados
- **Atomic snapshot pre-op** — `withOpAudit()` wrapper cria `VACUUM INTO snapshot` em `/var/backups/nox-mem/pre-op/` antes de qualquer op destrutiva
- **Dry-run em ops destrutivas** — `nox-mem reindex --dry-run` e `consolidate --dry-run` produzem JSON preview sem mutar o DB
- **Canary invariants** — 13 invariantes verificados `*/15min` com alert Discord; schema canary semantic `*/30min`

---

## Estado atual

Para estado vivo e proxima acao: [docs/HANDOFF.md](docs/HANDOFF.md)

| Periodo | Items |
|---|---|
| **DONE (Abr 2026)** | Hardening triplo (47 findings → 11 HIGH fechados), E2E test suite (27 tests), Fase 4 Obsidian view-only, upgrade defense system (ckpt + improvements + watcher + orchestrator), consolidacao documental |
| **EM ESPERA (gates)** | `gate.salience` 2026-04-30, `gate.section_boost` 2026-05-01, archive 3 source files 2026-05-02 |
| **PROXIMO (pos-gates)** | A6 Entity-Facts SPO Injection, A7 Session Focus Boost, B2 PDF ingest (4.432 PDFs), W1.1 edge typing FULL |

---

## Mapa de documentacao

| Para... | Leia... |
|---|---|
| Proxima acao imediata + estado vivo | [docs/HANDOFF.md](docs/HANDOFF.md) |
| Roadmap completo + capacity + gates | [docs/ROADMAP.md](docs/ROADMAP.md) |
| Decisoes arquiteturais + NAO FAZEMOS | [docs/DECISIONS.md](docs/DECISIONS.md) |
| System design overview | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| Visao estrategica long-term | [docs/VISION.md](docs/VISION.md) |
| Regras criticas pra AI assistants (1-15) | [CLAUDE.md](CLAUDE.md) |
| Incident playbooks | [docs/RUNBOOKS.md](docs/RUNBOOKS.md) |
| Convencoes de codigo e docs | [docs/CONVENTIONS.md](docs/CONVENTIONS.md) |
| Historico de versoes v1.0 → v3.7 | [docs/EVOLUTION.md](docs/EVOLUTION.md) |
| Incident log completo | [docs/INCIDENTS.md](docs/INCIDENTS.md) |
| Como trabalhar neste repo | [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) |
| Audit trail (13+ docs) | [audits/](audits/) |
| Paper tecnico | [paper/paper-tecnico-nox-mem.md](paper/paper-tecnico-nox-mem.md) |

---

## Estrutura do repositorio

```
memoria-nox/
├── README.md                   <- este arquivo
├── CLAUDE.md                   <- regras operacionais 1-15 para AI assistants
├── docs/
│   ├── HANDOFF.md              <- estado vivo (single source of truth "agora")
│   ├── ROADMAP.md              <- timeline + capacity + gates ("o que vem")
│   ├── DECISIONS.md            <- append-only (NAO FAZEMOS + razoes + licoes)
│   ├── ARCHITECTURE.md         <- system design overview
│   ├── VISION.md               <- long-term thesis
│   ├── CONVENTIONS.md          <- convencoes detalhadas
│   ├── EVOLUTION.md            <- historico v1.0→v3.7
│   ├── INCIDENTS.md            <- incident log
│   ├── RUNBOOKS.md             <- incident playbooks
│   ├── CONTRIBUTING.md         <- como trabalhar no repo
│   └── _archive/               <- handoffs e plans antigos (referencia historica)
├── specs/                      <- especificacoes tecnicas
├── audits/                     <- audit trail (13+ docs)
├── scripts/                    <- ops scripts (ckpt, improvements, oc-upgrade, release-watcher)
├── paper/                      <- paper tecnico (.md + .docx)
├── plans/_archive/             <- roadmaps anteriores (v1.5, v1.6)
├── handoffs/_archive/          <- handoffs de sessoes anteriores
└── .github/
```

---

## Stack tecnico

- **Runtime:** TypeScript / Node.js 22 (wrapper `--no-warnings` obrigatorio)
- **Storage:** better-sqlite3 + FTS5 (BM25) + sqlite-vec (3072d vectors)
- **Embeddings:** Gemini gemini-embedding-001 via `gemini-2.5-flash-lite` default
- **Backend agents:** Claude CLI (`/usr/bin/claude`) via OAuth Max — zero cobrança de API
- **Orchestration:** OpenClaw v2026.4.23 (monkey-patched para Issue #62028)
- **Watcher:** inotifywait + debounce 15s
- **Process management:** systemd (3 servicos ativos: openclaw-gateway + nox-mem-api + nox-mem-watcher)
- **Dashboard:** [agent-hub-dashboard](https://github.com/totobusnello/agent-hub-dashboard) (4 paginas nox-mem)

---

## Operacoes e seguranca

O sistema opera com 5 camadas de defesa sobrepostas: (1) `withOpAudit()` cria snapshot atomico antes de qualquer op destrutiva; (2) dry-run obrigatorio antes de operacoes em prod; (3) `ops_audit` append-only com SQL triggers CWE-693; (4) canary de invariantes `*/15min` com alert Discord; (5) improvements audit com 13 checks (7 critical + 6 warn-only) que cobrem permissoes, cron, env vars, monkey-patch e session drift.

O script `ckpt` cria checkpoints git com snapshot de estado de sistema. O release-watcher monitora novas versoes do OpenClaw antes que upgrades automaticos destruam o monkey-patch do Issue #62028. O orchestrator de upgrade (`oc-upgrade`) aplica versoes novas com auto-rollback em caso de fratricide detectado.

Baseline de saude: `ssh root@100.87.8.44 '/root/bin/improvements check'` deve retornar **13/13 OK**.

---

## Projetos relacionados

- **[nox-supermem](https://github.com/totobusnello/nox-supermem)** (privado) — produto comercial PT-BR baseado no nox-mem. Mercado Brasil, distribuicao Hotmart, tiers A/B/C. Em desenvolvimento apos Fase 4 estavel 30 dias.
- **[agent-hub-dashboard](https://github.com/totobusnello/agent-hub-dashboard)** — dashboard UI com 4 paginas nox-mem (chunks, KG, search telemetry, health).

---

## Licenca

MIT — veja [LICENSE](LICENSE).

---

## Agradecimentos

Construido por [Toto Busnello](https://github.com/totobusnello). Powered by [Claude](https://anthropic.com) (Anthropic). Usa [OpenClaw](https://openclaw.dev), [sqlite-vec](https://github.com/asg017/sqlite-vec) e Gemini (Google DeepMind).
