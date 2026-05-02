# Nox Neural Memory — Segundo Cérebro do Toto Busnello

> Documento de visão — **v14 (2026-04-25)**
> **Status:** Sistema em **v3.7+**, **9692 chunks** 100% embedded, schema **v10** (retention_days/pain/section/section_boost) + ops_audit append-only triggers (CWE-693). Phases 1, 1.5, 0.5, 24h, 1.6, 1.7a, 2.5, D1-D4, RP, IM, 1.7b-a, Stab, Fase 2, 1.7b-b shadow, 1.7b-c, Fase 3 Tier 1, **A0-A5 hardening + audit triplo (47 findings, 11/11 HIGH fixados) + Wave 2 cleanup (11 MED/LOW) + E2E test suite (27 tests)**, **Fase 4 Obsidian view-only** **CONCLUÍDAS**. Próximo bloco: gates 04-30 (salience) / 05-01 (section_boost) → Tier 2 PDFs (4432) pós-gate → Memory Graph Maturity Waves (Maio-Ago 2026). Fase P 🔓 destravada (precisa Fase 4 estável 30d).
>
> **Plano de execução canônico:** `memoria-nox/plans/2026-04-25-integration-roadmap-v1.6.md` (v1.6) — Phase Matrix consolidada + Wave Roadmap evolutivo. Este doc é **visão estratégica**; o plano é o que **executa**. Roadmap v1.5 (`2026-04-19-unified-evolution-roadmap.md`) permanece referência ativa pra Cross-Cutting Concerns + Decisões Válidas + "NÃO FAZEMOS".
> **Master handoff:** `memoria-nox/handoffs/MASTER-HANDOFF-2026-04-24.md` — sessão completa de migração entities.
> **Correção crítica (v14):** incident 2026-04-25 — `nox-mem reindex` (disparado pelo cron OpenClaw `end-of-day` 22:00 BRT diário) zerou section/retention de 183 entities porque `ingestFile()` genérico não rotava entity files via `ingestEntityFile()`. Recovery 12min. **Fix arquitetural:** guard no topo de `ingestFile()` rota `memory/entities/<type>/*.md` automaticamente; cron `end-of-day` editado pra `consolidate` em vez de `reindex`; **regra #15 CLAUDE.md**: ops destrutivas só com `--dry-run` ou snapshot atômico. Pendência menor: user-level systemd órfão rodando v4.15 em restart loop ~40% CPU também resolvido (stop+disable). Detalhes: `docs/INCIDENTS.md#2026-04-25`.
> **Adendo sessão 2026-04-26 (~9h reais, 10 commits):** sanity check 24h pós-A1v2 detectou anomalia (6 zombie rows agent DBs) → bugs B1+B2 fixados (closeDb mid-function + reaper coverage gap). Audit triplo paralelo (4 reviewers) achou 47 findings — 11/11 HIGH fechados em 3 commits (sec hardening, symlink protection, TOCTOU mitigation, secret scrub, PID liveness, dry-run accuracy). Wave 2 cleanup (11 MED/LOW): ops_audit append-only triggers, free space DoS check, safeRestore reorder, configurable canary, early-zombie WARN. E2E test suite: 7 tests com regression guard pro B2 (total 27 tests passing). **Fase 4 Obsidian view-only DONE** (era POST-GATE 05-02+, antecipada): generator Python (430 LOC) gera vault em VPS, cron 02:30 BRT + launchd Mac 03:00 BRT (rsync via Tailscale). Mac vault c/ Things theme + 5 plugins (Dataview, BRAT, 3D Graph, Graph Analysis, Juggl) + 5 graph snippets (galaxy-nox/cyberpunk/retrowave/minimal-pro/matrix). B3 backlog 7/8 fechados (3 rollback playbooks novos, CONVENTIONS.md chunk_type doc). Bug crítico no sync detectado via dry-run (rsync --delete apagaria customizações local-only) e fixado adicionando excludes pra .obsidian/{themes,plugins,snippets,community-plugins.json,appearance.json,hotkeys.json,types.json,graph.json}. Estado: **0 HIGH abertos**, ops_audit append-only ativo, 5 camadas defesa + 27 fixes, snapshot dir 0700 + 0600 perms.
> **Correção v13 (histórica):** incident 2026-04-21 reindex sem auto-vectorize → cegueira semântica 5h. Fix em camadas.
> **Correção v12 (histórica):** v11 afirmava "3588 vetores Operacional" — era 100% órfãos. Fase 0.5 corrigiu.

---

## Visão Central

**Objetivo:** Qualquer documento, contrato, planilha, gravação, nota ou conversa gerada pelo Totó — em qualquer área de atuação — vira conhecimento consultável em segundos via WhatsApp.

*"Qual era o múltiplo de EBITDA do deal SME?"*
*"O que o Sorensen disse sobre o prazo do 20-F?"*
*"Qual a área do terreno da Sorocaba?"*

Nox responde na hora, com fonte citada.

---

## O que já temos (base)

| Componente | Status verificado (2026-04-25) |
|---|---|
| `memory/*.md` — decisions, lessons, pending, wip, people, projects | ✅ Operacional + **3 source files arquivados 2026-04-25** (decisions/lessons/projects.md → entities) |
| **nox-mem v3.7+** — FTS5 + Gemini embeddings + RRF fusion, **9540 chunks** (+360% volume desde v3.6d) | ✅ Operacional |
| **Schema v10** — retention_days (v8) + pain (v9) + section/section_boost (v10) | ✅ Operacional 2026-04-23/24 |
| **Knowledge Graph v2** — **~402 entidades**, ~544 relações, extração via Gemini 2.5 Flash | ✅ Operacional |
| **Semantic search** — sqlite-vec, **9540 / 9540 (100% coverage)**, Gemini embeddings 3072d | ✅ Operacional |
| **Reindex com auto-vectorize + entity routing** — `dist/reindex.js` + `dist/ingest.js` patched 2026-04-25 | ✅ Operacional (entity files → ingestEntityFile automático; fix arquitetural elimina classe inteira de bug) |
| **Hermes upgrades** — reflect (KG synthesis) + crystallize (procedures searchable) | ✅ Operacional (deployado 2026-04-13) |
| **Compiled Truth + Timeline** — entity 3-section format, 183 entities migradas (12 projects + 42 lessons + 127 decisions + 2 agents) | ✅ Operacional 2026-04-24 (1.7b-c) — 732 chunks (compiled=183, frontmatter=183, timeline=366) |
| **Affective Ranking (pain-weighted)** — schema v9, baseline 207 promote/1886 archive candidates | ✅ Shadow-mode (NOX_SALIENCE_MODE=shadow), ativação prevista 2026-04-30 |
| **Section Boost** — compiled=2.0x, frontmatter=1.5x, timeline=0.8x | ✅ Shadow-mode (NOX_SECTION_BOOST_MODE=shadow), ativação prevista 2026-05-01 |
| **Typed Source Retention** — feedback/person=NULL never-decay, lesson 180d, decision/project 365d, default 90d, override via HTML comment | ✅ Operacional 2026-04-23 (1.7b-a) |
| **HTTP API** — porta **18802**, 10 endpoints incl. /salience + /sectionDistribution | ✅ Operacional |
| **MCP Server** — **16 tools** via JSON-RPC 2.0 stdio | ✅ Operacional |
| **CLI** — 26+ subcomandos incl. `ingest-entity` (NOVO 2026-04-24) | ✅ Operacional |
| **Trigger `trg_chunks_delete_cascade`** — AFTER DELETE ON chunks limpa vec_chunks + map | ✅ Instalado 2026-04-18 + propagado 6 DBs agentes 2026-04-21 |
| **Semantic canary + self-heal** (`semantic-canary.sh`) | ✅ Ativo `*/30min` com auto-recovery |
| **Section shadow telemetry** (`section-shadow-telemetry`) | ✅ Ativo daily 23:45 BRT — JSON em `/var/log/nox-section-shadow-daily.log` |
| **Discord heartbeat validation** | ✅ Ativo `*/30min` — 6 channels + zero "Unknown Channel" |
| **Morning report** (`morning-report.sh`) | ✅ Ativo 06:30 BRT |
| **Nightly maintenance** (`nightly-maintenance.sh`) | ✅ 7 phases (incl. Phase 7 WAL checkpoint TRUNCATE add 2026-04-24) |
| **Heartbeat-sync** | ✅ `*/15min` |
| **Claude CLI backend (zero pay-per-token)** — agents.defaults via OAuth Max | ✅ Operacional desde 2026-04-22, routing per-agent v3.7b 2026-04-24 (nox+forge=opus, atlas+boris+cipher+lex=sonnet) |
| **OpenClaw v2026.4.23** + monkey-patch Issue #62028 + upgrade scripts idempotent | ✅ Operacional |
| **active-memory plugin** — Gemini Flash-Lite, recall pré-turn | ✅ Operacional |
| **graph-memory plugin** — session continuity, log misleading patched 2026-04-24 | ✅ Operacional |
| **Cross-agent Intelligence** — 7 DBs (workspace + 6 agentes) | ✅ Operacional |
| **Bridge Mode** (CLI + MCP + HTTP API + dashboard sobre mesma SQLite) | ✅ Operacional (formalização docs prevista Wave 3) |
| **HD Mac Tier 1** — md+docx via pandoc + watcher async | ✅ 543 files / 2697 chunks ingestados 2026-04-24 |
| **Snapshot pré-op atômico** + audit log + ingest-router unified | 🟡 Pre-gate hardening A0-A2 (executar até 2026-04-29) |
| Tailscale Mac (`100.119.65.10`) ↔ VPS (`100.87.8.44`) | ✅ Operacional |

---

## Phase Matrix (status canônico embedded — v1.6)

> Tabela autossuficiente pra entender estado real sem abrir o plano. Detalhes operacionais (sequência, esforços, gates) em `plans/2026-04-25-integration-roadmap-v1.6.md`.

| # | Fase | Status | Conclusão | Notas |
|---|---|---|---|---|
| 1 | Quick Wins (wip, feedback, L1) | ✅ DONE | 2026-04-11 | — |
| 1.5 | KG Migration Ollama→Gemini | ✅ DONE | 2026-04-11 | 1489 entities |
| 0.5 | Foundation Repair | ✅ DONE | 2026-04-18 | 1951/1951 embedded |
| 24h | Observação pós-Foundation | ✅ DONE | 2026-04-21 | 3d estável |
| 1.6 | Search Quality (expansion + dedup) | ✅ DONE | 2026-04-19 | wrapper puro |
| 1.7a | Core Memory Quality | ✅ DONE | 2026-04-19 | ontology, USER-PROFILE |
| 2.5 | graph-memory plugin | ✅ DONE (patched) | 2026-04-23 | log misleading 2026-04-24 |
| D1-D4 | Audit sistêmica | ✅ DONE | 2026-04-21 | 17 fixes |
| RP | RelayPlane | ✅ DONE | 2026-04-21 | INATIVO desde 04-22 (substituído pelo Claude CLI) |
| IM | Import repos locais | ✅ DONE | 2026-04-23 | 147 docs + 9 repos |
| **1.7b-a** | Typed retention matrix | ✅ DONE | 2026-04-23 | schema v8 |
| Stab | 5-agent audit + 10 fixes | ✅ DONE | 2026-04-23 | APPROVE WITH MINOR |
| **2** | Graphify scale | ✅ DONE (9 repos) | 2026-04-23 | 1046 graph_node chunks |
| **1.7b-b** | Salience formula formal | ✅ DONE shadow | 2026-04-23 | schema v9, pain REAL |
| **1.7b-c** | Compiled truth + timeline | ✅ DONE | 2026-04-24 | schema v10, 181 entities |
| **3 Tier 1** | HD Mac md+docx | ✅ DONE | 2026-04-24 | 2697 chunks via pandoc + watcher |
| **A0** | Query logging + golden-tag | ✅ DONE | 2026-04-25 ~10:45 BRT | Migration aditiva search_telemetry +4 cols, opt-in via NOX_SEARCH_LOG_TEXT |
| **A1** | Audit log + snapshot pré-op atômico (v2 hardened) | ✅ DONE | 2026-04-25 ~12:50 BRT (v1) + ~16:30 BRT (v2) | src/lib/op-audit.ts: withOpAudit() fail-closed + safeRestore() + reapZombies(); audit duplo expôs 27 findings, 5 CRITICAL/HIGH fixados (filename collision/path traversal/VACUUM atomicity/schema version/WAL órfãos); ver audits/2026-04-25-A1-A2-review.md + runbooks/recovery-from-snapshot.md |
| **A2** | Ingest-router unified (single dispatch) | ✅ DONE | 2026-04-25 ~14:00 BRT | src/lib/ingest-router.ts routeIngest() em 4 callers; defesa em camadas |
| **G01** | Salience activation `recency × pain × importance` em `/api/health.salience` | ✅ DONE | 2026-04-30 | `NOX_SALIENCE_MODE=active` aplicado pós-baseline 7d OK |
| **G02** | Section_boost shadow→active (compiled +100% n=1252 / frontmatter +49% n=315 / timeline -17% n=11) | ✅ DONE | 2026-05-01 | `.env` `NOX_SECTION_BOOST_MODE=active` + services restarted |
| **G03** | Archive 3 source files `memory/{projects,decisions,lessons}.md → .archived-20260502` + cleanup 8 chunks órfãos | ✅ DONE | 2026-05-01 | `mv` + DELETE via better-sqlite3 (vec0 cascade) |
| **A3** | Unit tests parseRetentionOverride (14 cases) | ✅ DONE | 2026-04-25 ~15:55 BRT | node:test built-in, 14/14 pass |
| **A4** | Canary invariants extension (4 invariants */15min) | ✅ DONE | 2026-04-25 ~16:01 BRT | check-schema-invariants.sh com Discord alert |
| **A5** | Dry-run mode em reindex+consolidate | ✅ DONE | 2026-04-25 ~16:30 BRT | --dry-run flag CLI, JSON preview wouldDelete/wouldProcess/protected; compact já tinha; crystallize defer |
| **4** | Obsidian view-only | ✅ DONE | 2026-04-26 | Antecipado pré-gate. Generator Python (`/root/.openclaw/scripts/export-obsidian-vault.py`, 430 LOC) gera vault em `/root/ObsidianVault-build/` (199 .md, 184 entities + KG index Dataview + by-type breakdowns). Cron 02:30 BRT VPS + launchd 03:00 BRT Mac (rsync via Tailscale `100.87.8.44`, excludes preservam customizações local-only). Mac vault: Things 2 theme + dark mode + 5 plugins (Dataview/BRAT/3D Graph/Graph Analysis/Juggl) + 5 graph snippets pra alternar vibe (galaxy-nox/cyberpunk/retrowave/minimal-pro/matrix). Color groups por tag singular (project/decision/lesson/agent/system/kg/index). **Fase P agora destravada** — precisa "Fase 4 estável 30d" antes de productizar. Audit doc: `audits/2026-04-26-B1-obsidian-view-only.md`. |
| **E02** Tier 2 | PDFs text-layer (gap real 954, cobertura A6 = 79% / 3.541 ingested) | 🔄 IN-PROGRESS | 2026-05-01 | retry NUVIVI+CONTRATOS rodando background, +1.236 chunks já ingestados; gap residual ~728 → E12 OCR |
| **F08** Backlog | #4 issue + #5 docs + #7 alert + #8 playbooks | ✅ DONE | 2026-04-27 | sprint B3 fechado |
| **F11** RUNBOOKS | Incident playbooks RB-01 a RB-10 formalizados | ✅ DONE | 2026-04-29 | `docs/RUNBOOKS.md` |
| **F12** | Gemini SPOF mitigation Tier 1/2/3 (FTS-fallback / OpenAI+Voyage / shadow-index trimestral) | ✅ DONE | 2026-05-01 | RB-05 em `docs/RUNBOOKS.md` |
| **F13** | Cost projection alt providers (4 cenários 12mo + switch OpenAI 1h) | ✅ DONE | 2026-05-01 | `runbooks/cost-projection-alt-providers.md` |
| **F14** | DR drill quarterly — script + cron `0 9 1 1,4,7,10 1` instalado, RTO 3s validado | ✅ DONE | 2026-05-01 | próxima execução auto 2026-07-06 |
| **F10** | Observability dashboard (4 painéis IndexedDB ring buffer 7d) | 🤔 SPEC READY | 2026-05-01 | spec `specs/2026-05-01-F10-observability-dashboard.md`, impl 2.5-3h Maio |
| **E03a** | A6 SPO Injection (`<vault-facts>` block via KG) | 🤔 SPEC READY | 2026-05-01 | spec `specs/2026-05-01-E03a-spo-injection.md`, impl 1.5h |
| **E04a** | A7 Focus Boost (`focus set <topic>` 1.4×/0.75×) | 🤔 SPEC READY | 2026-05-01 | spec `specs/2026-05-01-E04a-focus-boost.md`, impl 1.5h |
| **W1** | Memory Graph Maturity Wave 1 (edge typing, detect-changes, impact, api_impact) | 🔮 Maio 2026 | gated por métricas | 27-30h |
| **W2** | Wave 2 (eval harness completo) | 🔮 Jun-Jul 2026 | depende W1 + golden curated | 14-20h |
| **W3** | Wave 3 (paper v2: Affective + Federation + Bridge Mode) | 🔮 Ago 2026 | depende W2 nDCG baseline | 5-8h |
| 3 Tier 3 | OCR Gemini PDFs scanned (opcional) | 🔒 OPCIONAL | — | dias |
| 3.5 | Fathom API | 🔒 OPCIONAL | — | 3-4h |
| Path B-lite | Semantic reflect cache | 🔒 BLOCKED | depende telemetria reflect | 2-3h |
| Path C | WAL shipping + cold tier | 🔒 BLOCKED | depende Fase 4 estável 30d | dias |
| 4b/5 | Obsidian write + bidirectional | 🔒 FUTURO | depende Fase 4 + 2-4 sem | semanas |
| SEH | Self-Evolving Hooks | 🔒 INDEPENDENTE | — | 2h |
| **P** | Productização NOX-Supermem | 🔒 HORIZONTE 60d+ | depende Fase 4 estável 30d | semanas |

Legenda: ✅ DONE / 🤔 SPEC READY (impl pendente) / 🔄 IN-PROGRESS / 🔮 WAVE FUTURA (gated por métricas) / 🔒 BLOCKED ou FUTURO / 🟡 EM ANDAMENTO

---

## Decisões de Arquitetura

### 0. Query Strategy — como o Nox decide qual sistema consultar

**Decisão: Opção B — Nox decide pelo tipo de pergunta (não busca nos dois simultaneamente).**

```
Pergunta sobre conversa/decisão/time    → nox-mem KG + FTS5 + hybrid search
Pergunta sobre documento/contrato/repo  → graphify query
Pergunta ambígua                        → nox-mem primeiro → se não achar → graphify
```

**Por que não buscar nos dois sempre:**
- Evita resultados contraditórios (dois grafos respondendo coisas diferentes)
- Sem custo duplo de API por query
- Lógica simples e auditável — Nox aprende a classificar pelo contexto

**Roteamento entre agentes:**
Sistema simples via `shared/agent-expertise.md` (lido no boot). Cada agente tem expertise declarada — Nox roteia manualmente com base no SOUL.md. Expertise profiling automático é over-engineering para um time de 6 agentes com papéis fixos.

---

### 1. graphify vs nox-mem KG — complementares, não substitutos

| Dimensão | nox-mem KG v2 | graphify |
|---|---|---|
| **Escopo** | Memória operacional (conversas, decisões, lessons dos agentes) | Documentos estáticos (repos, PDFs, PPTX, XLSX, imagens) |
| **Extração** | Gemini 2.5 Flash (migrado de Ollama 2026-04-11) | Claude Vision (multimodal) |
| **Storage** | SQLite (`kg_entities`, `kg_relations`) | `graph.json` + Obsidian vault + wiki/ |
| **Query** | `kg-query`, `kg-path` (BFS), MCP tools | `graphify query`, `graphify path`, `graphify explain` |

**Decisão:** Operam em camadas diferentes. graphify indexa DOCUMENTOS. nox-mem indexa MEMÓRIA OPERACIONAL. A ponte entre eles: nox-mem ingere `GRAPH_REPORT.md` como chunk consultável.

```
Camada 1: graphify  → indexa DOCUMENTOS (PPTX, PDF, XLSX, repos)
Camada 2: nox-mem   → indexa MEMÓRIA OPERACIONAL (conversas, decisões, lessons)
Camada 3: busca unificada → agente recebe resultados de ambos
```

### 2. Path do vault — separado com symlink

**Decisão:** `/root/vault/` separado do workspace OpenClaw, com symlink para integração.

**Motivo:** O workspace operacional tem 51 MB. rsync do HD Mac pode trazer GBs. Misturar polui stats, backups e consolidation.

```
/root/vault/                           ← dados brutos (potencialmente grande)
├── projetos/                          ← git clones dos repos
├── documentos/                        ← rsync do HD Mac
└── reunioes/                          ← transcrições Fathom

/root/.openclaw/workspace/vault → /root/vault   (symlink)
```

**Fluxo:**
```
Mac (rsync) → /root/vault/documentos/
GitHub (git pull) → /root/vault/projetos/
Fathom (API) → /root/vault/reunioes/
     ↓
graphify --watch /root/vault/ → graph.json + GRAPH_REPORT.md
     ↓
nox-mem ingest GRAPH_REPORT.md → chunks consultáveis pelo hybrid search
agentes leem GRAPH_REPORT.md no boot → contexto completo
```

### 3. Cross-Agent Intelligence — real vs aspiracional

**O que existe hoje (atualizado 2026-04-21):**
- Todos os 6 agentes leem o **banco workspace** (compartilhado) — principal fluxo de conhecimento
- **DBs isolados por agente existem** mas são snapshots estáticos (last chunk: Mar 22 / Apr 1) — criados originalmente e congelados porque o pipeline de ingest não roda por-agente. Foram ressuscitados em 2026-04-21 com trigger + vetores pra feature `cross-search`/`cross-stats`/`cross-kg` funcionar
- Especialização via SOUL.md de cada agente — Nox roteia manualmente
- `shared/agent-expertise.md` + `shared/agent-map.md` — mapa de SessionKeys Discord pra delegação via `sessions_send("agent:X:discord:channel:ID", "msg")`
- **Delegação inter-agente validada end-to-end** em 2026-04-21: Nox recebe prompt → chama `sessions_send` pro Atlas → Atlas responde → Nox reporta de volta. Ambos turns passam pelo RelayPlane com budget cap.

**O que NÃO existe hoje (e não é necessário agora):**
- Expertise profiling automático ❌
- Roteamento algorítmico ❌
- Agentes escrevendo nos próprios DBs via watcher automático ❌ (pipeline atual só escreve no workspace DB)

**Quando faz sentido evoluir:**
- Expertise automático: time com 20+ agentes (hoje são 6 com papéis fixos)
- Agent DBs ativos: refatorar watcher pra monitorar `/agents/*/memory/*.md` + session-distill por-agente (trabalho de dias, não prioritário hoje)

---

### 4. Obsidian — painel de controle visual, não memória

**Papel do Obsidian:** É a **janela** para enxergar o segundo cérebro — grafo 3D rotacionável, clusters por projeto, Dataview como SQL visual. A memória real vive em `nox-mem.db` (warm), `graph-memory.db` (hot) e `graphify/graph.json` (cold). O Obsidian não é necessário para o Nox responder — ele funciona igual com ou sem o Obsidian aberto.

**Decisão:** Fase 4 = view-only. Fase 4b (escrita bidirecional) só após 2-4 semanas de validação.

**Papel no L3 (cold):** Após Fase 2.5 (graph-memory) e com camadas hot/warm/cold operacionais, o Obsidian visualiza o L3 — o grafo completo de documentos gerado pelo graphify. Você navega pelo que o agente usa para responder perguntas sobre documentos, contratos e repos.

**Motivo view-only primeiro:** O sistema já tem 29 cron jobs e 6 serviços. Adicionar 25 comandos e 4 agentes do obsidian-second-brain cria risco de conflito. O nox-mem já consolida conhecimento — Obsidian como visualizador é ouro, como escritor duplica responsabilidade.

### 5. KG extraction — Gemini 2.5 Flash (migrado 2026-04-11)

**Decisão:** Ollama llama3.2:3b (local, inativo) → Gemini 2.5 Flash (API, grátis).

**Motivo:** Ollama estava `inactive (dead)` no systemd desde ~março. KG congelado em 384 entidades sem ninguém perceber (fail-silent no código). Gemini usa a mesma API key dos embeddings, tem 500 RPM free tier, e `thinkingBudget: 0` elimina tokens desperdiçados em reasoning.

**Resultado do primeiro build:** 1489 entities + 348 relations extraídas, mentions aumentaram 70-78%, +8 relações novas. Logging ativo com tag `[KG-LLM]` e alerta após 5 falhas consecutivas.

---

## Pipeline de Escrita — como a memória cresce

**A memória é autônoma. Cresce com o uso, sem intervenção manual.**

Cada conversa com qualquer agente (Nox no WhatsApp, Forge/Lex/Atlas/Boris/Cipher no Discord) alimenta o mesmo banco compartilhado. Todos os 6 agentes compartilham o nox-mem — o que você explica para o Lex hoje, o Nox já sabe amanhã.

```
Você fala com Nox/Forge/Lex/Atlas/Boris/Cipher
        ↓ imediato (Fase 2.5)
graph-memory extrai triples da conversa (a cada 7 turnos) → graph-memory.db (HOT)
        ↓ 22h
end-of-day consolida → nox-mem.db atualizado → git push (WARM)
        ↓ 23h (semanal para KG)
kg-build extrai entidades novas → KG cresce automaticamente (WARM)
        ↓ cron horário (Fase 2)
git pull em todos repos GitHub → novos documentos no vault (COLD)
        ↓ cron noturno
graphify --update → graph.json atualizado → GRAPH_REPORT.md regenerado (COLD)
        ↓ sempre disponível
nox-mem hybrid search + graph-memory recall → Nox responde com contexto completo
```

**Obsidian** é opcional — você abre quando quer **ver** o segundo cérebro. A memória funciona igual sem ele.

---

### 6. graph-memory — plugin de contexto inline para conversas

**Decisão:** Adicionar [graph-memory](https://github.com/adoresever/graph-memory) como plugin OpenClaw para compressão de contexto e recall automático em conversas.

**O que faz:** Extrai triples (subject-relation-object) das conversas em tempo real, comprime contexto ~75% (95K→24K tokens), e injeta knowledge recall automaticamente antes de cada resposta. Cross-session: lembra de sessões anteriores sem intervenção manual.

**Por que complementa o nox-mem (não substitui):**
- nox-mem = memória de **longo prazo** (chunks, KG, documentos) — batch, cron
- graph-memory = memória de **curto prazo** (conversas ativas) — inline, real-time
- Operam em DBs separados (`graph-memory.db` vs `nox-mem.db`), hooks diferentes, zero conflito

**Custo:** ~1 call LLM a cada 7 turnos de conversa (não por mensagem). Extraction usa provider padrão do gateway. Embeddings via Gemini endpoint OpenAI-compatible.

**Riscos analisados e resolvidos:**
| Risco | Severidade | Mitigação |
|---|---|---|
| Custo LLM por mensagem | Baixo — 1 call/7 turnos | Usa provider padrão (Sonnet via RelayPlane) |
| Conflito com nox-mem | Mínimo — DBs e hooks isolados | Nenhuma ação necessária |
| Mais um SQLite | Baixo — auto-mantido, <50MB | Adicionar ao backup script |

### 7. Estratégia de camadas — hot/warm/cold

**Decisão:** Não buscar em todos os sistemas a cada pergunta. Usar cache hierárquico como CPU L1/L2/L3.

**Contexto:** Com GitHub + HD + Fathom indexados, o sistema pode chegar a 20K-70K entidades. Buscar em 70K entidades a cada mensagem no WhatsApp seria lento e caro. A solução é camadas com granularidades diferentes.

```
┌─────────────────────────────────────────────────────────────┐
│ Pergunta chega (WhatsApp/Discord)                           │
│                                                             │
│ L1 — HOT (real-time, <100ms)                                │
│ ├── graph-memory: triples da conversa ativa + recall        │
│ ├── nox-mem hybrid search: chunks mais relevantes           │
│ └── Tamanho: <5K entidades ativas                           │
│                        ↓ se L1 não achar                    │
│ L2 — WARM (on-demand, <2s)                                  │
│ ├── nox-mem KG completo: todas entidades com decay          │
│ ├── graphify GRAPH_REPORT.md: resumo do grafo documental    │
│ └── Tamanho: 5K-20K entidades                               │
│                        ↓ se L2 não achar                    │
│ L3 — COLD (batch, minutos)                                  │
│ ├── graphify query no graph.json completo                   │
│ ├── Busca direta no vault (/root/vault/)                    │
│ └── Tamanho: 20K-70K entidades                              │
└─────────────────────────────────────────────────────────────┘
```

**Medidas de proteção para não ficar pesado:**
1. **TTL agressivo** — decay -0.1/30d, prune threshold 0.3. Entidades sem menção em 90 dias são removidas
2. **Graph traversal max depth=2** — nunca depth=3+ (explode exponencialmente com nós centrais como "Toto" que tem 700+ mentions)
3. **Extração incremental** — só chunks novos/modificados (SHA256 cache). Nunca re-extrair todo o vault
4. **Vectorização lazy** — vetorizar os 1000 chunks mais acessados primeiro, expandir sob demanda
5. **GRAPH_REPORT.md como cache** — agentes leem resumo no boot (20 top entities), não fazem query no grafo completo
6. **DBs separados por camada** — graph-memory.db (hot), nox-mem.db (warm), graphify graph.json (cold). Nunca mergear tudo num banco só

### 8. Affective Ranking — pain-weighted retrieval (NOVO v14)

**Decisão:** chunks têm peso afetivo (`pain` REAL 0.1-1.0) que pondera o ranking — crash em prod pesa mais que warning. Validado experimentalmente via `salience = recency × pain × importance`.

**Por que é diferencial:** RAGs convencionais ranqueiam por relevância semântica + frequência. Nox-mem v3.7+ adiciona **dimensão emocional/operacional** — incidentes pesam mais, lessons sobre crashes ficam visíveis quando relevantes mesmo após 6 meses.

**Estado atual:** schema v9 deployado 2026-04-23. Backfill heurístico: 256 chunks pain=1.0 (prod-outage/crash), 43 pain=0.8 (lesson), 469 pain=0.5 (bug/error), 105 pain=0.3 (warn/deprec), 6474 pain=0.2 (default). Shadow-mode rodando, ativação prevista 2026-04-30.

### 9. Compiled Truth + Timeline — entity 3-section format (NOVO v14)

**Decisão:** entities (`memory/entities/<type>/<slug>.md`) têm 3 seções: **frontmatter** (metadata), **compiled truth** (verdade atual reescrita conforme evidência muda), **timeline** (append-only, fatos datados). Cada arquivo gera N+2 chunks com `section_boost` diferenciado.

**Por que é diferencial:** code-intelligence externa indexa código atemporal. Nox-mem v3.7+ tracha **temporalidade epistêmica** — sabe que "X era verdade ontem mas hoje mudou". Compiled é rewritável (Toto via `/memory-recompile` skill); timeline é append-only (histórico imutável).

**Estado atual:** 183 entities migradas 2026-04-24 (12 projects + 42 lessons + 127 decisions + 2 agents). Distribuição: compiled=183, frontmatter=183, timeline=366. `section_boost`: compiled=2.0x, frontmatter=1.5x, timeline=0.8x. Shadow-mode telemetry coletando A/B desde 04-24, ativação prevista 2026-05-01.

### 10. Bridge Mode — uma indexação, múltiplos consumidores (NOVO v14)

**Decisão:** mesma SQLite (`nox-mem.db`) consumida via 4 interfaces equivalentes: CLI (26+ subcomandos), MCP (16 tools), HTTP API (porta 18802, 10 endpoints), agent-hub-dashboard (4 páginas). Zero duplicação de indexação.

**Por que é diferencial:** muitos sistemas de memória têm 1 cliente fixo (chatbot OU dashboard OU CLI). Bridge Mode permite Nox no WhatsApp, Forge no Discord, Toto na CLI, painel visual no browser — todos na mesma fonte de verdade. **Já implementado** desde Fase 1.6, mas formalização docs prevista pra Wave 3 (paper v2).

---

## Fontes de Conhecimento

### 1. Projetos (GitHub — prioridade máxima)
- **Local Mac:** `~/claude/projetos/` — cada subpasta = um projeto
- **GitHub:** `github.com/totobusnello/<repo>` — um repo por projeto, maioria privado
- **Conteúdo:** PPTX, PDF, XLSX, DOCX, MD, código
- **Sync para VPS:** git clone + pull automático (cron horário)

### 2. Documentos pessoais (HD Mac — resto do HD)
- **Localização:** `~/Documents/`, `~/Downloads/`, outras pastas
- **Tipos:** PPTX, PDF, XLSX, DOCX, fotos, vídeos
- **Sync para VPS:** rsync via Tailscale (agendado ou sob demanda)

### 3. Reuniões (Fathom)
- **Ferramentas:** Zoom + Fathom, Google Meet + Fathom
- **O que gera:** transcrições automáticas por reunião, com speakers identificados
- **Sync para VPS:** Fathom API → cron noturno → vault
- **Pré-requisito:** Confirmar capabilities da Fathom API antes de comprometer fase

### 4. Conversas do time (já na VPS)
- **WhatsApp/Discord:** daily notes em `memory/YYYY-MM-DD.md`
- **Consolidação:** nox-mem consolidate (23h)

---

## Arquitetura Final

```
┌─────────────────────────────────────────────────────────────────┐
│                      FONTES (Mac + Nuvem)                        │
│                                                                   │
│  GitHub repos (totobusnello/*)    Fathom (transcrições)          │
│  HD Mac (PPTX/PDF/XLSX/DOCX)     WhatsApp/Discord               │
└──────────┬─────────────────┬───────────────────┬────────────────┘
           │ git pull (1h)   │ rsync (diário)    │ Fathom API (noturno)
           ▼                 ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                    VPS — Hub Central                              │
│                                                                   │
│  /root/vault/              (dados brutos, separado do workspace) │
│    ├── projetos/           ← git clone de cada repo              │
│    ├── documentos/         ← rsync do HD Mac                     │
│    └── reunioes/           ← transcrições Fathom                 │
│                                                                   │
│  /root/.openclaw/workspace/vault → /root/vault (symlink)         │
│                                                                   │
│  EXTRAÇÃO DE CONHECIMENTO:                                       │
│  ├── graphify (Claude Vision) → graph.json + GRAPH_REPORT.md    │
│  ├── nox-mem KG (Gemini 2.5 Flash) → kg_entities + kg_relations │
│  └── nox-mem embeddings (Gemini) → vec_chunks (3072d)            │
│                                                                   │
│  BUSCA UNIFICADA:                                                │
│  ├── Layer 1: FTS5 BM25 (keyword) ──────────── [fts]            │
│  ├── Layer 2: Gemini semantic (vector) ─────── [semantic]        │
│  ├── Layer 3: RRF fusion ──────────────────── [hybrid]           │
│  └── Layer 4: graphify query (documentos) ── [graph]             │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                       AGENTES                                     │
│                                                                   │
│  Boot: leem GRAPH_REPORT.md antes de qualquer busca              │
│  On-demand: graphify query "pergunta" → subgrafo + fonte         │
│  On-demand: nox-mem search "query" → hybrid search               │
│                                                                   │
│  Nox → responde Totó no WhatsApp com fonte citada                │
│  Lex → consulta contratos e cláusulas                            │
│  Atlas → research parte do conhecimento acumulado                │
│  Forge → histórico técnico + decisões de arquitetura             │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                    VISUALIZAÇÃO                                   │
│                                                                   │
│  Obsidian 3D (view-only) ← graphify vault via rsync             │
│  Dashboard React ← nox-mem HTTP API (:18802)                     │
│  WhatsApp/Discord ← agentes com contexto completo               │
│  graph.html — grafo interativo no browser                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Sincronização Mac → VPS

### Projetos (GitHub — automático)
```bash
# Na VPS: clonar todos os repos do totobusnello (uma vez)
gh repo list totobusnello --limit 100 --json name,isPrivate \
  | python3 -c "import json,sys; [print(r['name']) for r in json.load(sys.stdin)]" \
  | xargs -I{} gh repo clone totobusnello/{} /root/vault/projetos/{}

# Cron horário na VPS: atualizar todos
find /root/vault/projetos/ -maxdepth 1 -type d | xargs -I{} git -C {} pull
```

### HD Mac (rsync via Tailscale)
```bash
# Script no Mac: ~/sync-vault.sh
#!/bin/bash
rsync -avz --delete \
  --exclude='*.DS_Store' \
  --exclude='node_modules/' \
  --include='*.pdf' \
  --include='*.pptx' \
  --include='*.xlsx' \
  --include='*.docx' \
  --include='*.png' \
  --include='*.jpg' \
  --include='*/' \
  --exclude='*' \
  ~/Documents/ \
  root@100.87.8.44:/root/vault/documentos/

# Agendar via launchd (diário às 2h) ou rodar manualmente quando quiser
```

### Reuniões (Fathom API)
```bash
# Cron noturno na VPS: puxa transcrições novas do Fathom
# Pré-requisito: validar Fathom API capabilities (endpoints, auth, rate limits)
# Script salva cada call em /root/vault/reunioes/YYYY-MM-DD-titulo.md
```

---

## Interface Visual — Obsidian 3D (view-only)

**Obsidian é o visualizador do segundo cérebro.** Fase inicial = somente leitura.

### Preview real — seus projetos como grafo

> Gerado a partir dos repos reais: `totobusnello/sao-thiago-fii`, `Area-Campolim-Sorocaba`, `Area-Manuel_Nobrega`, `Future-Farm`, `GalapagosApp`, `Granix-App`, `biolab-ai`, `nox-workspace`

![Grafo 3D dos projetos do Toto](grafo-toto-preview.jpg)

*Nós identificados nos seus repos: Nuvini, FII São Thiago, Área Sorocaba, Manuel Nóbrega, Future Farm, GalapagosApp, Granix, Biolab AI — conectados a documentos reais (PDFs, XLSX, DOCX, apresentações, análises)*

---

### O que você vê na tela

```
┌──────────────────────────────────────────────────┐
│     OBSIDIAN 3D GRAPH  —  o cérebro do Toto       │
│                                                  │
│    • Nuvini ●────● SME Deal ●─── R$174M       │
│       │              │                         │
│    ● Sorensen    ● SEC Filing                  │
│       │              │                         │
│    ● 20-F       ● Due Diligence               │
│                                                  │
│    ● FII Treviso ●── Contrato ●──● 2.400m²      │
│       │                                         │
│    ● Aeronaves ●────● Estrutura Fundo          │
│                                                  │
│  [ Clusters coloridos por área ]                │
│  Azul=Financeiro  Verde=Imóveis  Roxo=Pessoas   │
└──────────────────────────────────────────────────┘
```

**Cada nó é um conceito.** Cada aresta é uma relação.
Você clica em "Nuvini" → vê todos os deals, pessoas e documentos conectados.
Você clica em "Sorensen" → vê tudo que ele aparece: reuniões, contratos, decisões.

### Views disponíveis

| View | O que mostra | Como acessa |
|---|---|---|
| **3D Graph** | Galáxia completa rotacionável — todo o conhecimento | Plugin 3D Graph (BRAT) |
| **Local Graph** | Vizinhança de um nó (ex: tudo ligado a "SME Deal") | Clica num nó → Local Graph |
| **Canvas** | Quadro visual por projeto — timeline, tarefas, decisões | Plugin Canvas |
| **Dataview** | Tabelas SQL-like ("contratos assinados em 2025") | Plugin Dataview |
| **Graph Analysis** | Força dos clusters, nós mais centrais | Plugin Graph Analysis |

### Como o vault chega no Mac

```
VPS: graphify gera vault Obsidian em /root/vault/obsidian/
        ↓ Tailscale (100.87.8.44)
Mac: rsync noturno copia vault para ~/ObsidianVault/
        ↓
Tela: galáxia 3D interativa com todo o conhecimento (read-only)
```

### Plugins necessários (instalação única no Mac)

1. **BRAT** (Community Plugins) → adiciona `3D Graph v2.4.1`
2. **Dataview** → Community Plugins → Browse → Dataview
3. **Canvas** → já nativo no Obsidian 1.11+
4. **Graph Analysis** → Community Plugins → Browse

**Setup total:** ~20 minutos após vault gerado.

---

## Fases de Execução

### ✅ Fase 1 — Quick Wins (CONCLUÍDA — 2026-04-11)
- [x] `wip.md`, `feedback/approved.json`, `feedback/rejected.json`
- [x] L1 índices em decisions.md e lessons.md
- [x] Documento de visão no GitHub

### ✅ Fase 1.5 — KG Extraction Migration (CONCLUÍDA — 2026-04-11)
- [x] Diagnosticar Ollama inativo no systemd
- [x] Migrar `kg-llm.ts` de Ollama para Gemini 2.5 Flash
- [x] Adicionar logging com tag `[KG-LLM]` e alerta após 5 falhas
- [x] Configurar `thinkingBudget: 0` + `responseMimeType: "application/json"` + schema nativo
- [x] Build + teste real: 10 entidades, 6 relações extraídas com sucesso
- [x] Rodar `kg-build --limit 1000`: 1489 entities + 348 relations processadas
- [x] Resultado: mentions aumentaram 70-78%, +8 relações novas, KG descongelado

---

### ✅ Fase 0.5 — Foundation Repair (CONCLUÍDA — 2026-04-18)

**Contexto:** Diagnóstico via 4 agentes especializados (architect + database-optimizer + sre-engineer + performance-engineer) identificou **5 gaps críticos que invalidavam a afirmação de "Layer 2 Operacional" na v11** deste doc. Layer 2 semântica estava silenciosamente morta há semanas — hybrid search era FTS-only disfarçado.

**Tier 0 — Stop the bleeding** (fixes reversíveis, zero risco):
- [x] `health-probe.sh` lê `${NOX_API_PORT}` do `.env` — elimina 288 restarts/dia causados por port mismatch (Chrome squatter em :18800)
- [x] `db.ts` ganhou `PRAGMA busy_timeout = 5000` — elimina SQLITE_BUSY silencioso sob contention
- [x] `/api/health.vectorCoverage` usa `INNER JOIN chunks × vec_chunk_map` em vez de COUNT sobre vec_chunk_map — para de mentir

**Tier 1 — Restaurar camada semântica:**
- [x] DELETE dos 6.627 órfãos em `vec_chunk_map` + 2.587 unreferenced em `vec_chunks`
- [x] Trigger `trg_chunks_delete_cascade AFTER DELETE ON chunks` instalado — previne recorrência
- [x] `vectorize.ts` bug corrigido (consultava `vec_chunks.chunk_id` — coluna inexistente)
- [x] `embed.ts` ganhou `embedBatchAPI()` usando `batchEmbedContents` Gemini — **3 → 26.4 chunks/s (9×)**
- [x] Re-embed completo dos 1.951 chunks em **74 segundos, zero 429**
- [x] Verificação: `match_type: "semantic"` aparece em resultados naturais de search (antes era 0%)

**Autodefesa + automação:**
- [x] `semantic-canary.sh` diário às 06:00 — alerta Discord se `match_type: "semantic"` sumir dos resultados
- [x] `morning-report.sh` diário às 06:30 — resumo de saúde + mudanças de 24h no `#nox-chief-of-staff`
- [x] Webhook Discord ativo (`#nox-chief-of-staff`, criada via API com `DISCORD_BOT_TOKEN`)
- [x] Script local Mac: `~/Claude/Projetos/memoria-nox/scripts/check-nox-mem.sh` — 1 comando, GO/NO-GO colorido
- [x] Índice composto `idx_chunks_type_date` — elimina TEMP B-TREE em queries `chunk_type + source_date DESC`
- [x] Snapshot completo do DB antes do nightly (136MB, `PRAGMA integrity_check: ok`) em `/root/.openclaw/workspace/backups/nox-mem-pre-nightly-20260418-125019.db`

**Aprendizado institucional:**
- Endpoints de saúde **nunca** devem derivar de tabelas isoladas — sempre JOIN com source-of-truth (chunks)
- Embedding layer **exige** teste canário diário. Fail-silent é o pior tipo de falha
- Quando a doc estratégica contradizer `/api/health`, auditar ambos — doc pode estar mentindo

**Deliverables completos:**
- `audits/audit-2026-04-18-db-gaps-remediation.md` (DB)
- `audits/sre-deepening-2026-04-18.md` (SRE)
- `audits/perf-baseline-2026-04-18.md` (performance)
- `plans/2026-04-18-tier0-tier1-session-log.md` (handoff completo)
- `plans/2026-04-19-unified-evolution-roadmap.md` (plano executável unificado — **fonte primária** de execução daqui em diante)

---

### Fase 1.6 — Search Quality Upgrade (aguardando OK)
**Objetivo:** Melhorar qualidade do hybrid search com 2 técnicas comprovadas do gbrain (14.7K+ brain files em produção).
**Tempo estimado:** 2h. Zero risco — wrappers puros do pipeline existente.
**Inspiração:** [garrytan/gbrain](https://github.com/garrytan/gbrain) — `search/expansion.ts` + `search/dedup.ts`

**Query Expansion — Multi-Query Rewrite (~50 LOC em `search.ts`):**
- Antes do hybrid search, gerar 2 reformulações da query via Gemini 2.5 Flash (já pago, 500 RPM free)
- Queries curtas (<3 palavras) ficam como estão — sem overhead desnecessário
- **Config `expansionEnabled: boolean`** — liga/desliga sem deploy. Padrão: `true`. Se uso escalar e custo Gemini subir, desligar aqui sem tocar no código
- Cada reformulação gera embedding + vector search separado
- RRF fusion mergeia os 3 rankings (original + 2 expansões)
- Exemplo: "deal Sorensen" → ["deal Sorensen", "negociação Nuvini Sorensen", "SME transaction M&A"]
- Fallback gracioso: se Gemini falhar, usa query original (non-fatal)
- **Impacto estimado: +30-40% recall** em queries ambíguas no WhatsApp

**Search Dedup Pipeline 4-Layer (~80 LOC, post-processor do RRF fusion):**
- Layer 1: Top 3 chunks por page (não deixa 1 page dominar)
- Layer 2: Text similarity >0.85 removido (elimina chunks quase idênticos)
- Layer 3: Nenhum `type` >60% dos resultados (diversidade — evita 10 lessons sem decisions)
- Layer 4: Max 2 chunks por page final (cap hard)
- Aplica DEPOIS do RRF fusion existente — zero mudança no core search
- **Impacto: resultados mais diversos e úteis, menos redundância**

**Resultado:** Hybrid search retorna respostas melhores sem tocar em FTS5, sqlite-vec ou schema. Wrapper puro sobre o pipeline existente.

---

### Fase 1.7a — Core Memory Quality (aguardando OK)
**Objetivo:** Entidades ricas + economia de API + User Profile no boot dos agentes.
**Tempo estimado:** 2-3h. Baixo risco — mudanças de prompt + ~60 linhas de código.

> **Sequência recomendada:** 1.6 → 1.7a → 2.5 → 2 → 1.7b
> Search quality (1.6) primeiro porque é wrapper puro, zero risco. graph-memory (2.5) antes do graphify (2) para L1 estar pronto.

---

### Fase 1.7 — Reasoning Traces + Multi-Stage Extraction (aguardando OK)
**Objetivo:** Agentes gravam como chegaram nas respostas. Extração de entidades fica mais eficiente.
**Tempo estimado:** 1-2h

**Reasoning Traces (~50 linhas em TypeScript):**
- Novo tipo de chunk `reasoning_trace` no nox-mem
- Quando agente responde query complexa (WhatsApp/Discord), grava: query → fontes consultadas → dados extraídos → resposta
- Queries similares futuras encontram o trace via hybrid search e respondem mais rápido
- Nox pode responder "como você chegou nessa resposta?" com fonte

**Multi-Stage Extraction (~30 linhas em `kg-llm.ts`):**
- Antes de chamar Gemini 2.5 Flash, rodar regex para entidades óbvias:
  - Nomes próprios (palavras com maiúscula que não iniciam frase)
  - Valores monetários (R$, US$, €)
  - Datas (DD/MM/YYYY, mês por extenso)
  - Emails, URLs, telefones
- Se regex extrair ≥3 entidades de um chunk simples, pula call Gemini
- Se chunk for complexo (poucas entidades por regex), chama Gemini normalmente
- **Ganho:** Reduz 30-40% das calls Gemini no `kg-build` semanal

**Ontology Grounding (mudança de prompt, zero código novo):**
- Em vez de "extraia entidades genéricas", o prompt define campos por tipo:
  - `project`: name, value (R$), status, key_person, ebitda_multiple
  - `person`: name, role, organization, relationship_to_toto
  - `document`: name, type (contrato/apresentação/análise), date, parties
  - `decision`: what, who_decided, date, outcome
- Gemini 2.5 Flash com `responseSchema` já suporta isso nativamente
- **Ganho:** Nox responde "Nuvini: R$174M, 8x EBITDA, Sorensen" ao invés de "Nuvini é um project"

**Conflict Detection (query SQL no kg-build, ~20 linhas):**
- Quando `kg-build` encontra entidades com mesmo nome mas atributos conflitantes, loga o conflito
- Exemplo: doc 2024 diz "FII São Thiago = 2400m²", transcrição 2026 diz "renegociamos para 3200m²"
- Conflitos são marcados para revisão — Nox avisa "há informação conflitante sobre isso"
- Crítico quando graphify + HD + Fathom trouxerem dados de épocas diferentes

**Invalidation Chains (2 campos novos em kg_entities, ~15 linhas):**
- Adicionar `valid_until` + `superseded_by` na tabela `kg_entities`
- Quando entidade é atualizada, a antiga recebe `valid_until = now()`, nova referencia a antiga
- Nox responde com dados mais recentes e pode dizer "isso mudou desde março"
- Histórico preservado — nunca deletar, só invalidar

**Source Text Preservation (1 campo novo no schema):**
- Guardar raw text original junto com entidades extraídas (`source_text` na kg_entities)
- Quando extração não cobre a pergunta, fallback para busca no verbatim
- Custo: mais storage, zero LLM. MemPalace prova que raw + bom retrieval = 96.6% accuracy

**Hierarchical Tagging — scope/category/topic (mudança de prompt):**
- 3 campos de metadata por entidade, inspirado no palace structure (+34% retrieval accuracy)
- `scope`: projeto ou pessoa (ex: `nuvini`, `fii-sao-thiago`, `toto`)
- `category`: tipo de conhecimento (ex: `decisions`, `contracts`, `people`)
- `topic`: subtópico específico (ex: `pricing`, `ebitda`, `terreno`)
- Hybrid search filtra por scope/category antes de buscar — reduz espaço de busca
- Prompt do Gemini pede para classificar cada entidade nos 3 níveis

**Smart Forgetting (TTL inteligente, ~10 linhas no extractor):**
- Quando Gemini extrai entidade com data ("reunião amanhã", "prazo sexta", "evento 15/04"), calcular TTL relativo
- Fatos temporais: TTL = data + 7 dias (margem). Fatos permanentes: TTL = 90 dias (atual)
- Evita poluição do KG com informação expirada — "prova amanhã" de 3 meses atrás some automaticamente

**User Profile Cache (`USER-PROFILE.md`, gerado pelo cron):**
- Resumo auto-gerado do Toto: top facts, projetos ativos, preferências, decisões recentes
- Injetado no boot de todo agente — Nox sabe quem é o Toto sem re-ler chunks
- Evolução do `KG-SUMMARY.md` (que só tem stats) para perfil de contexto rico
- Gerado semanalmente após kg-build (mesmo cron)

**Resultado:** Memória de raciocínio + economia de API + entidades ricas + detecção de contradições + versionamento de fatos + auto-esquecimento inteligente + perfil de usuário persistente.

**Divisão obrigatória em 1.7a e 1.7b:**

**Fase 1.7a — Core (execução 2-3h, baixo risco):**
- Ontology Grounding (só mudança de prompt)
- Multi-Stage Extraction (30 linhas, 30-40% menos calls Gemini)
- User Profile Cache (USER-PROFILE.md — alto impacto no boot)
- Source Attribution — campo `source_type` nos chunks: `user_statement`, `compiled`, `timeline`, `external`. Hierarquia: user > compiled > timeline > external. RRF fusion aplica boost por source_type (user 2x, compiled 1.5x, timeline 1x, external 0.8x). Zero infra nova — ajuste no scoring. **(gbrain)**
- Compiled Truth Flag — campo `is_compiled` nos chunks: consolidados = `true` (síntese = verdade atual), originais = timeline (evidência). Search dá boost para chunks compilados. Conceito validado pelo gbrain em 14.7K brain files. **(gbrain)**

**Fase 1.7b — Quality (execução 4-6h, requer testes):**
- Reasoning Traces
- Conflict Detection
- Invalidation Chains (**regra crítica:** entidades com `superseded_by` são imunes a TTL — arquivadas, nunca deletadas)
- Smart Forgetting
- Source Text Preservation + Hierarchical Tagging
- Inline Entity Detection — regex fast-path em cada mensagem WhatsApp/Discord: se ≥3 entidades (nomes, valores, datas), gravar direto no KG sem LLM. Se <3, chamar Gemini Flash em background async. KG atualizado em tempo real vs delay de 7 dias. Conceito validado pelo gbrain: entity detection spawna subagent em toda mensagem. **(gbrain)**

**Inspiração:** [neo4j-labs/agent-memory](https://github.com/neo4j-labs/agent-memory) (reasoning traces, multi-stage extraction) + [topoteretes/cognee](https://github.com/topoteretes/cognee) (ontology grounding) + [kraklabs/mie](https://github.com/kraklabs/mie) (conflict detection, invalidation chains) + [supermemoryai/supermemory](https://github.com/supermemoryai/supermemory) (smart forgetting, user profiles) + [MemPalace/mempalace](https://github.com/MemPalace/mempalace) (verbatim preservation, hierarchical tagging — 96.6% LongMemEval) + [garrytan/gbrain](https://github.com/garrytan/gbrain) (source attribution, compiled truth, inline entity detection — 14.7K brain files em produção).

---

### Fase 2.5 — graph-memory Plugin (aguardando OK) ← **executar ANTES da Fase 2**
**Objetivo:** Agentes ganham memória de curto prazo — compressão de contexto e recall automático em conversas via WhatsApp/Discord.
**Tempo estimado:** 30 min (plugin install + config)

> **Por que antes da Fase 2:** Com 20K entidades chegando via graphify, o L1 (graph-memory) precisa estar ativo para absorver o volume sem sobrecarregar o sistema a cada pergunta no WhatsApp.

**Passos:**
1. `pnpm openclaw plugins install graph-memory` na VPS
2. Configurar no `openclaw.json`:
   - `compactTurnCount: 7` (extrai triples a cada 7 turnos)
   - `recallMaxNodes: 6` (injeta até 6 nós de recall)
   - `recallMaxDepth: 2` (max 2 hops no grafo)
   - LLM: usa provider padrão do gateway (Sonnet)
   - Embeddings: Gemini via endpoint OpenAI-compatible (já pago)
3. Adicionar `graph-memory.db` ao backup script
4. Testar: conversa longa no WhatsApp → verificar compressão e recall
5. Monitorar por 1 semana antes de considerar concluído

**Resultado:** Nox no WhatsApp lembra o que conversou ontem. Contexto de 174 mensagens cabe em 24K tokens.

---

### Fase 2 — Graphify + GitHub Projetos (aguardando OK)
**Objetivo:** Primeiro grafo real sobre os projetos do Totó.
**Tempo estimado:** 2-3h

**Passos:**
1. `pip install graphifyy` na VPS
2. `graphify install --platform claw` (escreve no AGENTS.md)
3. Criar `/root/vault/` + symlink no workspace
4. Clonar repos prioritários do GitHub na VPS (`/root/vault/projetos/`)
5. `/graphify /root/vault/projetos/` — primeiro grafo
6. Analisar GRAPH_REPORT.md: quais são os god nodes? Quais conexões surpresa?
7. Cron horário: `git pull` em todos os repos
8. Cron diário 23h30: `graphify --update /root/vault/` (rebuild incremental)
9. Agentes passam a ler GRAPH_REPORT.md no boot
10. nox-mem ingest GRAPH_REPORT.md (ponte graphify → hybrid search)
11. **Semantic Chunking para novos docs** — chunks existentes ficam como estão, novos ingestões usam semantic chunker **(gbrain)**:
    - Embeds cada frase, calcula similaridade coseno entre adjacentes
    - Savitzky-Golay filter (5-window, 3rd-order polynomial) para achar mínimos locais = topic boundaries
    - Fallback automático para recursive chunker se embedding falhar
    - ~150 LOC portado do gbrain (`chunkers/semantic.ts`, validado em 14.7K brain files)
    - **Impacto: chunks de documentos longos (PPTX, PDF) ficam semanticamente coerentes em vez de cortados no meio de parágrafos**

**Resultado:** Nox sabe o que está em todos os projetos do Totó. Primeira query real. Docs longos geram chunks melhores.

---

### Fase 1.7b — Memory Quality (aguardando OK — executar após validar 1.7a + 2.5 + 2)
**Objetivo:** Detecção de contradições, versionamento de fatos, auto-esquecimento inteligente.
**Tempo estimado:** 4-6h. Requer testes cuidadosos.

> **Regra crítica de TTL:** Entidades com `superseded_by` são **imunes ao TTL** — apenas arquivadas, nunca deletadas. Conflito entre Smart Forgetting e Invalidation Chains resolvido por esta regra.

- Reasoning Traces
- Conflict Detection (crítico quando graphify trouxer dados de épocas diferentes)
- Invalidation Chains (`valid_until` + `superseded_by`) + regra de proteção TTL
- Smart Forgetting (TTL inteligente por data)
- Source Text Preservation + Hierarchical Tagging

---

### Fase 3 — HD Mac via rsync (aguardando OK)
**Objetivo:** Documentos pessoais (PPTX, PDF, XLSX, DOCX) indexados.
**Tempo estimado:** 1h setup + tempo do rsync inicial (depende do volume)

**Passos:**
1. Script `sync-vault.sh` no Mac (rsync via Tailscale para `/root/vault/documentos/`)
2. Definir pastas prioritárias (quais `~/Documents/` primeiro?)
3. Primeiro rsync manual
4. graphify processa os novos arquivos (`--update`)
5. launchd no Mac: sync diário às 2h

**Nota:** fotos e vídeos pesados → filtrar por extensão, só PPTX/PDF/XLSX/DOCX no primeiro round.

**Enrichment Pipeline Tiered (design nesta fase, implementação incremental) — (gbrain):**
- Com graphify + rsync trazendo centenas/milhares de entidades, enriquecimento manual fica inviável
- 3 tiers de gasto por importância da entidade:
  - **Tier 1 (key people/deals):** Pipeline completo — cross-reference todos os chunks, gerar compiled truth, validar conflitos
  - **Tier 2 (menções frequentes):** Light touch — apenas cross-reference e timeline
  - **Tier 3 (passagem):** Raw data only — preservar verbatim sem processamento
- Classificação automática: entidades com ≥5 mentions = Tier 1, 2-4 = Tier 2, 1 = Tier 3
- Usa o próprio nox-mem como fonte (cross-reference entre chunks) — sem APIs externas por agora
- **Impacto: recursos de processamento focados no que importa, Sorensen e Nuvini viram Tier 1 automaticamente**

---

### Fase 3.5 — Fathom API (paralela, opcional, aguardando OK)
**Objetivo:** Reuniões indexadas automaticamente, sem esforço.
**Não bloqueia Fase 4.** Se API Fathom não existir ou for limitada, projeto continua.
**Tempo estimado:** 3-4h

**Pré-requisito:** Validar Fathom API capabilities antes de comprometer esta fase.
- [ ] Fathom tem API REST pública? Quais endpoints?
- [ ] Auth token disponível? Rate limits?
- [ ] Export de transcrições com speakers identificados?

**Passos:**
1. Validar API (pré-requisitos acima)
2. Script Python: puxa calls novas desde última execução → salva como .md em `/root/vault/reunioes/`
3. Cron noturno 1h: roda o script
4. graphify --update processa as transcrições novas

**Resultado:** Reunião de hoje → indexada amanhã cedo → Nox responde "o que foi decidido na call de quinta?"

---

### Fase 4 — Obsidian View-Only (aguardando OK)
**Objetivo:** Visualizar a galáxia de conhecimento no Mac sem risco.
**Tempo estimado:** 1h

**Passos:**
1. graphify gera `graphify-out/obsidian/` como vault pronto
2. rsync do vault da VPS para o Mac (`~/ObsidianVault/`)
3. Instalar plugins (BRAT + 3D Graph, Dataview) — 20 min
4. Cron noturno: VPS → Mac via Tailscale

**Resultado:** Galáxia 3D interativa, zero risco de corrupção de dados.

> O Obsidian é o **painel de controle visual** do segundo cérebro — não é necessário para a memória funcionar. É onde você vê o L3 (cold) como galáxia interativa. A memória cresce e serve os agentes independentemente de o Obsidian estar aberto.

### Fase 4b — Obsidian Write (futuro, condicional)
**Pré-requisito:** 2-4 semanas usando Obsidian view-only. Só avançar se sentir falta de escrita.

**Se aprovada:**
- Começar com 1 comando (`/obsidian-save`) antes de 25
- Avaliar conflito com consolidation do nox-mem
- Agente noturno para reconciliar

---

### Fase 5 — openclaw-memory-sync (aguardando OK)
**Objetivo:** Sync bidirecional Obsidian ↔ OpenClaw.
**Tempo estimado:** 1h

Plugin Obsidian que conecta na porta 18789 (gateway) e sincroniza a cada 5 minutos:
- Memórias do OpenClaw → notas Obsidian
- Notas Obsidian → contexto dos agentes

---

## Decisões Fechadas (2026-04-11)

| Decisão | Escolha | Motivo |
|---|---|---|
| Query strategy | Opção B — Nox decide pelo tipo | Sem custo duplo, sem conflito, auditável |
| Dashboard React | Mover para Evoluções Futuras | Sem fase definida, não pertence na arquitetura atual |
| Cross-Agent | Expertise via SOUL.md + agent-expertise.md | Over-engineering para 6 agentes |
| Sequência crons | graphify (23h30) → precompact (23h45) | Constraint explícita documentada |
| Fathom | Fase 3.5 paralela, não sequencial | Não bloqueia o resto do projeto |
| Obsidian | Painel de controle visual (L3 view-only) | Memória vive em nox-mem.db+graph-memory.db+graph.json — Obsidian só visualiza |
| Sequência fases | 1.6 → 1.7a → 2.5 → 2 → 1.7b → 3 → 3.5 | Search quality (wrapper puro) primeiro, depois graph-memory antes do graphify |
| TTL + Invalidation | `superseded_by` = imune a TTL | Sem essa regra, histórico é perdido pelo Smart Forgetting |
| Notion | Manter apenas para Tarefas & Deals (pipeline operacional) | Memória & Decisões migra para nox-mem + Obsidian; crons de sync de memória para Notion serão aposentados |
| graph-memory | Plugin complementar (Fase 2.5) | Memória curto prazo (conversas) vs nox-mem longo prazo (documentos) |
| Estratégia de camadas | Hot/warm/cold com DBs separados | Com 20K-70K entidades, buscar em tudo a cada pergunta é inviável |
| Memgraph | Evolução futura (>500K entidades) | Over-engineering severo para 384 entidades atuais |
| gbrain engine pluggável | Não adotar (PGLite/Postgres) | **Motivo explícito:** o gbrain suporta PGLite e Postgres como engines alternativos ao SQLite. Migrar o nox-mem para Postgres adicionaria um serviço extra (daemon, backup, autovacuum), aumentaria complexidade operacional e não traria benefício mensurável abaixo de 500K entidades. O SQLite com WAL mode performa em <5ms para os volumes atuais. Revisitar se/quando migrar para Memgraph (>500K entidades). |
| gbrain git-as-source-of-truth | Não adotar (markdown-as-code) | **Motivo explícito:** o gbrain usa markdown files versionados em git como banco primário — cada entidade é um arquivo `.md` com frontmatter YAML. O nox-mem usa SQLite com FTS5 + sqlite-vec + schema relacional. São filosofias de storage opostas. Adotar o modelo gbrain significaria reescrever o nox-mem do zero (novo schema, novo chunker, novo indexer, novo search). As features individuais (query expansion, dedup, semantic chunking, source attribution) são portáveis e foram adotadas. A arquitetura de storage não é. |
| gbrain 30 MCP tools | Manter 14 tools atuais | Mais tools = mais manutenção. Novos capabilities via search quality + enrichment |
| **Regra #15 — ops destrutivas** (v14) | `--dry-run` ou snapshot atômico OBRIGATÓRIO | Lição incident 2026-04-25 — `nox-mem reindex` zerou metadados de 183 entities. backup-all.sh diário 02:00 NÃO conta como pré-op. CLAUDE.md regra #15 detalha. |
| **Inspirações externas (v14): incorporar conceitos, não migrar arquitetura** | Filtrar por valor mensurável no domínio nox-mem (memória conceitual multi-agent) | Padrões de code-intelligence externos têm domínio diferente (código, atemporal, single-user). Ideias portáveis (edge typing, dry-run, eval harness, impact analysis) viram Memory Graph Maturity Waves. License/stack externa NÃO entra. |
| **Group routing (v14)** | CORTADO definitivamente — qualquer formato | Viola Decisão #4 SOUL.md (cross-Agent não-algorítmico). `cross-search --agents X,Y` já cobre. Frontmatter tag também cortado (algorithmic routing disfarçado). |

---

## Riscos e Mitigações

| Risco | Impacto | Mitigação |
|---|---|---|
| **Storage VPS** — rsync do HD Mac traz GBs | Disco cheio, backups lentos | `/root/vault/` separado, filtro por extensão, monitorar `df -h` |
| **Custo API Gemini** — graphify usa Claude Vision por arquivo | Billing inesperado | Usar free tier, monitorar RPM, processar em batches |
| **Fathom API** — pode não existir ou ser limitada | Fase 4 inviável | Validar capabilities ANTES de implementar |
| **Single point of failure** — tudo na VPS | Perda total se VPS cair | Backups diários (já existem), vault no GitHub, rsync bidirecional |
| **Dois sistemas de grafo** — graphify + nox-mem KG | Dados inconsistentes | Query strategy Opção B (Nox decide), GRAPH_REPORT.md como ponte |
| **inotifywait + symlinks** — watcher pode não seguir symlinks | Vault não monitorado | Testar com `-r` na Fase 2, fallback: cron em vez de watch |
| **Escala 20K-70K entidades** — graph traversal fica lento | Queries >2s no WhatsApp | Camadas hot/warm/cold, TTL 90d, max depth=2, extração incremental |
| **KG extraction batch** — 50K docs via Gemini = horas | Custo API, rate limit | SHA256 cache (só novos), vectorização lazy (top 1000 primeiro) |
| **Reindex sem snapshot pré-op** (v14) | Wipe de metadados em produção (incident 2026-04-25 wipou 183 entities) | Regra #15 obrigatória + Fase A1 hardening (snapshot atômico em `/var/backups/nox-mem/pre-op/` retention 7d) |
| **End-of-day cron disparando reindex daily** (v14) | Toda noite 22:00 BRT redo full DELETE+INSERT, expondo qualquer bug arquitetural | Cron `end-of-day` editado 2026-04-25 pra `nox-mem consolidate` (não muta chunks; só `consolidated_files.status`). Reindex full continua via nightly Phase 2 (odd DOM, agent workspaces) |
| **User-level systemd órfão** (v14) | Servicio v4.15 antigo em restart loop ~40% CPU paralelo ao system gateway v4.23 | Stop+disable+rename do `~/.config/systemd/user/openclaw-gateway.service` (load avg 0.95→0.56 imediato) — **regra**: após upgrades OpenClaw, `loginctl user-status root` pra detectar duplicatas |

---

## Nox Answers — exemplos concretos por fase

Cada fase habilita novas perguntas reais. Teste esses exemplos para validar que a fase entregou o prometido.

| Fase | Pergunta de teste | Fonte esperada |
|---|---|---|
| ✅ 1.5 | "Quais entidades estão no KG?" | `nox-mem kg-query` |
| 1.6 | "Quem trabalhou com Sorensen?" (query ambígua) | Query expansion gera 3 variantes, recall +30% vs busca direta |
| 1.6 | "decisões recentes" (busca genérica) | Dedup 4-layer retorna mix de types (decisions, lessons, notes) |
| 1.7a | "Qual era o múltiplo de EBITDA do SME?" | entidade ontologia `project.ebitda_multiple` |
| 1.7a | "De onde veio essa informação?" | Source attribution: "segundo reunião de 2026-03-15" |
| 1.7a | "Qual é o perfil de contexto do Toto hoje?" | `USER-PROFILE.md` injetado no boot |
| 2.5 | "O que conversamos sobre o Sorensen na semana passada?" | `graph-memory` recall cross-session |
| 2.5 | "Qual o status do deal que discutimos ontem?" | graph-memory compressão 75% |
| 2 | "O que tem no repo sao-thiago-fii?" | `graphify query` |
| 2 | "Quais documentos mencionam EBITDA nos meus projetos?" | graphify + nox-mem GRAPH_REPORT |
| 1.7b | "O FII São Thiago tem 2400m² ou 3200m²?" | Conflict Detection — "há informação conflitante" |
| 3 | "Qual a área do terreno da Sorocaba?" | XLSX indexado via rsync + graphify |
| 3.5 | "O que foi decidido na call de quinta?" | Fathom transcrição indexada |
| 4 | [visual] Nuvini → SME Deal → Sorensen → 20-F | Obsidian 3D grafo |

---

## Métricas de Sucesso por Fase

| Fase | Métrica | Meta |
|---|---|---|
| ✅ 1 | Arquivos criados, índices funcionais | Concluído |
| ✅ 1.5 | KG extraction rodando, logging ativo | Concluído (1489 extrações) |
| 1.6 | Query expansion ativo, dedup 4-layer aplicando | +30% recall em queries ambíguas, resultados sem duplicatas |
| 1.7a | Ontology Grounding ativo, User Profile gerado, source attribution, compiled truth | ≥30% menos calls Gemini, respostas com fonte citada |
| 1.7b | Reasoning traces, conflicts, TTL, inline entity detection | Zero `superseded_by` deletadas por TTL, KG real-time |
| 2 | `graphify query` retorna resultados reais, semantic chunking ativo | ≥ 80% queries com resposta, chunks semanticamente coerentes |
| 2.5 | Compressão de contexto ativa, recall cross-session funcionando | <30K tokens em conversa de 7+ rounds |
| 3 | Documentos do HD consultáveis, enrichment tiered ativo | ≥ 50 docs indexados, Tier 1 entities com compiled truth |
| 3.5 | Reuniões da última semana consultáveis | ≤ 24h delay entre reunião e indexação |
| 4 | Obsidian rodando no Mac com grafo visual | Setup completo, vault atualizado diariamente |
| 4b | Nox escreve no vault sem conflitos | Zero corrupção em 2 semanas |
| 5 | Sync bidirecional < 5 min delay | Entidade criada no OpenClaw aparece no Obsidian em 5 min |

---

## Referências Estudadas

| Repo | O que traz | Status |
|---|---|---|
| [glaucobrito/unified-memory-ai-agents](https://github.com/glaucobrito/unified-memory-ai-agents) | wip.md, feedback loop, L0/L1/L2, auto-precompact — 33 dias em produção | Aplicado (Fase 1) |
| [safishamsi/graphify](https://github.com/safishamsi/graphify) | Grafo semântico multimodal — 71.5x menos tokens, suporte OpenClaw nativo | Fase 2 |
| [adoresever/graph-memory](https://github.com/adoresever/graph-memory) | KG context engine — compressão 75%, recall automático cross-session, PageRank, community detection | Fase 2.5 |
| [eugeniughelbur/obsidian-second-brain](https://github.com/eugeniughelbur/obsidian-second-brain) | 25 comandos, vault auto-reescrevente, 4 agentes agendados, preset executive | Fase 4b (condicional) |
| [openclaw/openclaw#22958](https://github.com/openclaw/openclaw/issues/22958) | Feature request oficial: Obsidian como memória externa do OpenClaw | Referência |
| [YearsAlso/openclaw-memory-sync](https://github.com/YearsAlso/openclaw-memory-sync) | Plugin Obsidian ↔ OpenClaw sync bidirecional, porta 18789 plug-and-play | Fase 5 |
| [neo4j-labs/agent-memory](https://github.com/neo4j-labs/agent-memory) | 3 camadas (short/long/reasoning), POLE+O model, multi-stage extraction, MCP 16 tools | Fase 1.7 (ideias) |
| [topoteretes/cognee](https://github.com/topoteretes/cognee) | Knowledge engine, ontology grounding, remember/recall API, outcome tracking, Claude Code hooks | Fase 1.7 (ontology) |
| [kraklabs/mie](https://github.com/kraklabs/mie) | Single binary Go, conflict detection, invalidation chains, typed nodes, cross-agent daemon | Fase 1.7 (conflicts, versioning) |
| [supermemoryai/supermemory](https://github.com/supermemoryai/supermemory) | #1 em 3 benchmarks, smart forgetting, user profiles ~50ms, contradiction resolution, connectors | Fase 1.7 (forgetting, profiles) |
| [MemPalace/mempalace](https://github.com/MemPalace/mempalace) | 96.6% LongMemEval, raw verbatim storage, palace structure (+34% retrieval), zero API, local only | Fase 1.7 (source_text, scope/category/topic) |
| [garrytan/gbrain](https://github.com/garrytan/gbrain) | Personal brain do Garry Tan (YC president), 5K+ stars, 14.7K brain files em produção. Query expansion (Haiku, ~70 LOC), search dedup 4-layer, semantic chunking (Savitzky-Golay), compiled truth + timeline, source attribution, entity detection inline, enrichment pipeline tiered, 30 MCP tools. Stack: TypeScript, Postgres/pgvector/PGLite, OpenAI embeddings | Fase 1.6 (query expansion, dedup), 1.7a (source attribution, compiled truth), 1.7b (inline entity), 2 (semantic chunking), 3 (enrichment) |
| [memgraph/memgraph](https://github.com/memgraph/memgraph) | Graph DB in-memory C++, Cypher, 40+ algoritmos MAGE, vector+text indexes, GraphRAG atômico | Evolução futura |
| Guia @brunobracaioli | Tutorial prático graphify + métrica 71.5x confirmada | Referência |

---

## Evoluções Futuras (não prioritárias agora)

Ideias estudadas que fazem sentido quando o sistema crescer, mas são over-engineering hoje.

### Memory Graph Maturity Waves (Maio-Ago 2026) — NOVO v14

Roadmap evolutivo em 3 waves, distribuído em ~50h ao longo de 4 meses, **gated por métricas (não calendário)**. Detalhes operacionais completos em `plans/2026-04-25-integration-roadmap-v1.6.md` Seção 7. Resumo:

**WAVE 1 (Maio 2026, paralelo a Tier 2 PDFs) — 27-30h**
- W1.1 Edge typing FULL: `relation_reason` enum 7 + `confidence` REAL em `kg_relations`. Migration v11. Vocabulário enum CLOSED (sem free-form, sem query DSL — respeita NÃO FAZEMOS Text2Cypher). 12-14h.
- W1.2 `nox-mem detect-changes --since=<commit>`: git diff → entities/chunks afetados. READ-ONLY, sem hook automático. 5-6h.
- W1.3 `nox-mem impact <entity>`: 1-hop blast radius via kg_relations. Risk summary por chunk_type. SQL fixa, sem DSL. 6h.
- W1.4 `nox-mem api_impact <signature>`: multi-arquivo via grep + import graph. Cobre classe que W1.3 não cobre (bug arquitetural). 4h.

**WAVE 2 (Jun-Jul 2026) — 14-20h**
- W2.1 Eval harness completo: 50 golden queries + nDCG@10 + MRR. Migration v12 com `eval_queries` table. CLI `nox-mem eval run` + JSONL out. CI gate opcional. 14-20h.

**WAVE 3 (Ago 2026, pré-NOX-Supermem) — 5-8h**
- W3.1 Paper v2 update: Affective Ranking + Multi-Agent Memory Federation + Bridge Mode. Update `paper-tecnico-nox-mem.md/.docx` v3.0.0 stale. 5-6h.

**Cortados definitivamente (4 ideias eliminadas pós-validação):**
- ~~W2.2 Bridge mode docs standalone~~ → fundido em W3.1
- ~~W2.3 Tool/Skill map~~ → DEFER ≥6mo (sem consumer real, premature polish)
- ~~W3.2 Plugin hooks~~ → YAGNI (n=1 consumer = graphify), aproxima "30 MCP tools"
- ~~W3.3 Group routing v2~~ → viola Decisão #4 SOUL.md

**Wave gating métrico (não-calendário):**
- W1→W2: ≥80% rels classificadas com confidence ≥0.7 em shadow 7d + 50 golden curated
- W2→W3: nDCG@10 baseline publicado + 1 incident-free month + Affective Ranking validado
- Kill switches: features não usadas ≥3x/sem após 30d → archive; queries golden <50 em 2 sem → reduzir pra 20

### Graph database dedicado (Memgraph ou Neo4j)
**Quando:** KG ultrapassar 500K entidades com queries multi-hop complexas em real-time.
**O que traz:** Cypher query language, 40+ algoritmos nativos (PageRank, community detection, GNNs, link prediction), vector+text indexes em query única, sub-millisecond traversals.
**Por que não agora:** Com 384 entidades, SQLite responde em <5ms. Memgraph é in-memory (consome 500MB-1GB+ RAM), precisa Docker, é mais um serviço para manter. Ferrari para percurso de 5km.
**Gatilho:** Se graph traversal depth=2 começar a demorar >2s ou se precisar de algoritmos que SQLite não suporta (link prediction, temporal graphs).

### Atomic hybrid query (CTE no SQLite)
**Quando:** Latência do hybrid search ultrapassar 500ms.
**O que traz:** Combinar FTS5 + vector + RRF fusion numa única CTE (Common Table Expression) do SQLite, ao invés de 3 queries separadas em TypeScript.
**Por que não agora:** 3 queries separadas rodam em <100ms total. O ganho seria marginal.

### Obsidian escrita bidirecional
**Quando:** Após 2-4 semanas usando Obsidian view-only (Fase 4). Só se sentir falta.
**O que traz:** Vault que cresce sozinho, agente noturno reconcilia, /obsidian-save, /obsidian-challenge.
**Por que não agora:** Duplica responsabilidade com nox-mem consolidation. Risco de conflito alto.

### Text2Cypher para queries naturais
**Quando:** Se migrar para Memgraph/Neo4j.
**O que traz:** "Quais projetos o Sorensen participou?" → Cypher automático → resultado do grafo.
**Por que não agora:** Sem graph database, não há Cypher. O hybrid search do nox-mem já cobre 80% desses casos.

### Fase P — Productização NOX-Supermem (horizonte: pós-Fase 4)
**Quando:** Depois que todas as fases funcionais (1.6 → 5) estiverem estáveis e usadas internamente por 30+ dias.
**O que traz:** Empacota o sistema de memória como produto comercial para o mercado brasileiro via Hotmart.
**Repo:** `github.com/totobusnello/nox-supermem` (private) — já existe scaffold no Mar/15 (v2.1.2, ~10% implementação)
**Gap atual:** produto comercial está 6+ meses atrás do sistema interno. Não tem Layer 2 semantic, KG, reflect, crystallize, MCP, HTTP API. Plano de implementação com 57 tasks pendentes.
**Tiers:** A R$147, B R$197, C R$227 + R$30/semana suporte.
**Decisão:** NÃO atacar em paralelo com evolução interna. Fazer produto DEPOIS que o sistema estiver em paridade interna com v3.3+ e fases 1.6-4 estáveis por 30 dias.

### Self-Evolving Hooks — Feedback Loop Automático (spec: 2026-04-12)
**Quando:** Implementável agora — complementa nox-mem com aprendizado local.
**O que traz:** 3 hooks no Claude Code local (Mac) que capturam correções do usuário e transformam em regras permanentes automaticamente. O sistema aprende com "não faz assim" sem intervenção manual.
**Fonte:** [buildthisnow.com/blog/real-examples/self-evolving-hooks](https://www.buildthisnow.com/blog/real-examples/self-evolving-hooks)
**Spec detalhado:** `specs/2026-04-12-self-evolving-hooks.md`

**Arquitetura (3 hooks):**
1. **`on-stop.js`** (Stop hook) — Quando sessão encerra, captura transcript: mensagens humanas, agentes rodados, skills lidas → salva JSONL em `.claude/learning/sessions/`
2. **`dream.js`** (Background worker) — A cada 4h+ com 3+ sessões novas, spawna `claude -p --model haiku` que analisa padrões de correções e escreve regras em `.claude/learning/global.md` ou por agente/skill. Max 5 regras/run. 1 sessão = ruído, 2+ = regra.
3. **`subagent-start.js`** (PreToolUse: Agent) — Injeta regras aprendidas no boot de cada subagent.

**Bridge Local → VPS:** O dream worker pode opcionalmente ingerir regras no nox-mem via HTTP API (:18802), fechando o loop: correções no Mac → regras para agentes na VPS.

**Princípios:** User é ground truth (não avaliador AI), captura raw / interpreta depois, noise filtering (2+ sessões), auto-limitação (max 5 regras/run, cooldown 4h).

**Por que é relevante agora:** O nox-mem resolve memória para agentes VPS, mas no Claude Code local as correções se perdem. Este é o elo que faltava — feedback loop automático sem esforço manual. Custo: ~$0.01/dream run (Haiku).

---

## Ganhos Esperados por Fase

| Fase | Ganho principal |
|---|---|
| ✅ 1 | Boot -60% tokens. Feedback loop. Continuidade entre sessões. |
| ✅ 1.5 | KG vivo novamente. Extração via Gemini 2.5 Flash. Logging ativo. |
| 1.6 | Search +30-40% recall. Resultados sem duplicatas. Wrapper puro, zero risco. **(gbrain)** |
| 1.7a | Entidades ricas + User Profile + respostas com fonte citada. **(gbrain: source attribution, compiled truth)** |
| 1.7b | Contradições detectadas, fatos versionados, KG real-time. **(gbrain: inline entity detection)** |
| 2 | Projetos consultáveis. Chunks semanticamente coerentes. **(gbrain: semantic chunking)** |
| 2.5 | Nox lembra conversas anteriores no WhatsApp. Contexto comprimido 75%. |
| 3 | HD indexado. Enrichment tiered (Sorensen=Tier 1 automaticamente). **(gbrain: enrichment pipeline)** |
| 3.5 | Reuniões indexadas automaticamente. Zero esforço manual. |
| 4 | Galáxia 3D visual no Mac. Obsidian como painel de controle. |
| 4b | Vault que cresce sozinho (condicional). |
| 5 | Loop fechado: Obsidian ↔ OpenClaw em tempo real. |
| SEH | Claude Code local aprende com correções. Bridge Mac→VPS. |

---

## Próximos Passos — Aguardando OK do Totó

**Para começar Fase 1.6 (Search Quality — vitória mais rápida):**
- [ ] OK do Totó para executar
- [ ] ~130 LOC, ~2h, wrapper puro sobre hybrid search existente

**Para começar Fase 2 (após 1.6 + 1.7a + 2.5):**
- [ ] OK do Totó para executar
- [ ] Confirmar quais repos priorizar (Nuvini? FII? todos?)
- [ ] gh auth na VPS tem acesso aos repos privados? (verificar)

**Para Fase 3:**
- [ ] OK do Totó
- [ ] Definir pastas do HD Mac para incluir no primeiro rsync

**Para Fase 4:**
- [ ] OK do Totó
- [ ] Validar Fathom API capabilities
- [ ] Auth token do Fathom (Settings → API)

---

*Documento vivo — atualizado após cada fase concluída.*
*Última atualização: **2026-04-25 v14** — incorporação completa do salto v3.6d→v3.7+ (5 dias). Phase Matrix tabular embedded (autossuficiente). Adicionadas 3 decisões arquiteturais novas (Affective Ranking, Compiled Truth+Timeline, Bridge Mode). Memory Graph Maturity Waves (Maio-Ago 2026) consolidado em Evoluções Futuras. Regra #15 ops destrutivas (lição incident 2026-04-25 reindex wipe). 3 riscos novos catalogados (reindex sem snapshot, end-of-day cron, user-level systemd órfão). 2 cortes definitivos: Group routing (todas formas), Plugin hooks (YAGNI). Plano de execução canônico atualizado pra `plans/2026-04-25-integration-roadmap-v1.6.md`. Sistema em **v3.7+**: 9540 chunks 100% embedded, schema v10 (retention/pain/section), 184 entities migradas (compiled+frontmatter+timeline), HD Mac Tier 1 (2697 chunks md+docx), Claude CLI backend OAuth zero pay-per-token, OpenClaw v2026.4.23 + monkey-patch, 4/4 services active (load 0.56). Master handoff em `handoffs/MASTER-HANDOFF-2026-04-24.md`.*
*v13 (2026-04-21): sessão de audit completa, 22 tasks, 18 fixes em 4 rounds. v3.6d com 2073 chunks, RelayPlane ativo, canary self-heal, reindex auto-vectorize inline.*
*v12 (2026-04-18): Fase 0.5 Foundation Repair concluída; correção da afirmação falsa sobre Layer 2 operacional na v11; status re-verificado (1951 chunks, 100% coverage, 16 MCP tools); Fase P productização adicionada ao horizonte.*
*v11 original: 2026-04-12 — config `expansionEnabled` na Fase 1.6; motivos explícitos para não adotar gbrain git-as-source-of-truth e engine pluggável; decisão Notion documentada.*
