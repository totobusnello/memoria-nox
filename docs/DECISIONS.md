# nox-mem DECISIONS LOG

> **Append-only.** Não edite entries antigas — adicione novas. Histórico de "por quê" para qualquer decisão arquitetural.
> Para "o que fazer agora" → `docs/ROADMAP.md`. Para estado atual → `docs/HANDOFF.md`. Para regras operacionais 1-15 → `CLAUDE.md`.

---

## 1. NÃO FAZEMOS — inventário consolidado

| # | Item | Razão | Trigger pra revisitar | Origem |
|---|---|---|---|---|
| 1 | **Group routing** (`@group`, `groups.yaml`, frontmatter tag) | Viola SOUL.md Decisão #4 (rejeita routing algorítmico estático). `cross-search --agents` cobre ad-hoc. | Se aparecer dor → açúcar sintático de `cross-search` only | v1.5:21,43,140; v1.6 §2 |
| 2 | **Phase 3 deductive synthesis cross-session** (LLM gera "insights sintéticos" cross-session) | LLM confabula sem citation chain rastreável. Crystallize manual gated é alternativa. | Após eval harness W2.1 + caso concreto justificado | ClawMem analysis §5 |
| 3 | **Phase 4 recall stats worker dedicado** | `search_telemetry` + `/api/health.searchTelemetry` já cobrem. Worker = overhead op. | — | ClawMem analysis §5 |
| 4 | **Heavy-lane quiet-window worker** (`worker_leases` + query-rate gate) | Cron 23:00 + canary `*/15min` cobrem com 10% complexidade. | — | ClawMem analysis §5 |
| 5 | **Silos schema separados** (docs+observations+KG em 3 tabelas) | `chunks` canônico + `kg_*` derivados evita 3-way drift. | — | ClawMem analysis §5 |
| 6 | **W3.2 Plugin hooks** (`onIngest`, `onRelation`) | YAGNI clássico (n=1 consumer = graphify). Aproxima "30 MCP tools" proibido. | NOX-Supermem multi-tenancy → design-doc only (1h) | v1.6:197 |
| 7 | **W3.3 Group routing v2** (frontmatter tag) | Contradiz Section 1 v1.6 + viola SOUL.md Decisão #4 (mesmo do #1). | Nunca | v1.6:198 |
| 8 | **30 MCP tools** (gbrain pattern) | Mais tools = mais manutenção. Manter cap em 16; capabilities crescem via search quality. | NOX-Supermem multi-tenancy | v1.5:641; v1.6 §2 |
| 9 | **Memgraph / Neo4j** (graph DB dedicado) | Over-engineering para 371 entities. SQLite + sqlite-vec atende. | >500K entities | v1.5:642 |
| 10 | **Postgres / PGLite** (gbrain engine substituto) | Adicionaria daemon + autovacuum + backup. SQLite WAL <5ms suficiente. | >500K entities | v1.5:639 |
| 11 | **Text2Cypher / query DSL** | Sem graph DB, não há Cypher. Vocabulário enum CLOSED 7 valores. | Adoção de Memgraph (improvável) | v1.5:646; v1.6 §2 |
| 12 | **Free-form `relation_reason` vocabulary** | Vira "Text2Cypher in disguise" se indexável. Enum fechado é constraint estrutural. | Nunca | v1.6 §2 |
| 13 | **Atomic hybrid query (CTE única)** | Latência atual <100ms. Ganho marginal não compensa complexidade. | p95 >500ms persistente | v1.5:643 |
| 14 | **Dashboard React como roadmap item** | Já existe (`agent-hub-dashboard`). Não é trabalho novo. | — | v1.5:644 |
| 15 | **Expertise profiling automático** | Over-engineering para 6 agentes com papéis fixos. | >20 agentes | v1.5:645 |
| 16 | **Productizar nox-supermem em paralelo** | Divergência 6 meses. Priorizar paridade interna antes. | Fase 4 estável 30d | v1.5:647 |
| 17 | **Bump v1.6→v1.7 / v14→v15** baseado em ClawMem | Subagents leriam Q1-Q5 como decididos sem POC. | POC + 7d shadow validados | ClawMem analysis §6 |
| 18 | **Tier 3 OCR no critical path Fase 4** | Opcional. Não bloqueia Obsidian Fase 4 (texto-layer suficiente). | Volume PDF scaneado >50 docs | v1.6:62 |
| 19 | **Adotar git-as-source-of-truth (gbrain markdown)** | Filosofias opostas de storage. Reescrita do zero. Features portáveis, arquitetura não. | Nunca (incompatível) | v1.5:640 |
| 20 | **W2.3 Tool/Skill map** | Sem caso de uso concreto hoje. | 6+ meses ou multi-tenancy | v1.6:188 |
| 21 | **BGE-M3 como dense baseline no paper** (`BAAI/bge-m3`, 568M params) | Throughput CPU = 0.3 chunks/s → 55h ETA pra 61K chunks (testado 2026-05-04). Inviável overnight. Substituído por `multilingual-e5-base`. | GPU disponível (cloud/local) + volume <10K chunks | D23 — 2026-05-04 |
| 22 | **Pain ablation completa pré-submit arXiv** | Requer 2× restart prod nox-mem-api + janela 2min downtime sem autorização explícita. Não é pré-requisito pra submit (paper §5.5 cobre como future work). | Pós-submit 2026-05-19 com janela autorizada | D24 — 2026-05-04 |
| 23 | **Cross-agent retrieval-level quantification pré-submit** | `search_telemetry` não tem `requesting_agent` column (sketch sem deploy). +1h impl + 2 sem wait telemetria. Storage-level (99.92%) já é claim forte. | E12-followup com migration testada 2 sem | D25 — 2026-05-04 |
| 24 | **Modal cloud GPU pro paper** | BGE-M3 comparison não foi cobrada por reviewer; custo cloud GPU não justificado. `multilingual-e5-base` CPU cobre baseline. | Reviewer cobrar comparison específica em revisão pós-submit | D23 — 2026-05-04 |
| 25 | **Submit arXiv em dia/horário não-otimizado (Fri/weekend)** | Friday/weekend = baixo engagement no feed arXiv + HN. Tuesday peak window pra arXiv; Thursday peak pra HN tech audience. | Deadline de conferência forçar data específica | D27 — 2026-05-04 |
| 26 | **Skip blog pré-HN** | HN Thread precisa de link externo canonical. Post sem blog = link direto arXiv, que não converte em discussão de produto. | — | D27 — 2026-05-04 |
| 27 | **AGPL/copyleft pro repo memoria-nox** | Audience mista research + commercial. MIT maximiza adoption. Copyleft restringiria integração em OpenClaw (privado) e NOX-Supermem. | — | D26 — 2026-05-04 |
| 28 | **Trocar embedding primário de gemini-embedding-001 para multilingual-e5-base** | Baseline E5 n=60 replicado 3×: nDCG@10=0.3070 vs hybrid 0.5213 (lift 1.7×). Gemini é 1.7× melhor; redução de custo 12× não compensa. E5 vence em 2/8 categorias (cross-agent +0.013, temporal +0.017) mas margens estão dentro do MOE. | GPU + volume <10K chunks + reviewer exigir comparison específica | D28 — 2026-05-04 |

## 2. Q5 Cross-encoder reranker — DEFERRED (5 razões)

Por que **Q5 (Qwen3-Reranker-0.6B local via llama-server)** está deferred (não cortado):

1. **ROI claim "+15% recall" sem baseline** — W2.1 (eval harness) ainda não rodou; nDCG@10 inexistente; comparação é vibe-check
2. **Latência +200ms quebra SLA L2** (`<2s` definido em `docs/VISION.md:282`)
3. **Infra nova heavy** — llama-server + Qwen3-Reranker-0.6B comendo 2-3GB RAM na VPS Hostinger KVM 4 (compete com OpenClaw + nox-mem-api + nightly)
4. **Ranking change permanente sem shadow-mode** — viola precedente salience/section_boost + regra `feedback_shadow_mode_for_ranking_changes.md`
5. **Stack lean violation** — adiciona dep heavy (CPU/GPU inference) ao stack TS+SQLite+Gemini API atual

**Trigger pra reavaliar:** W2.1 publicar nDCG@10 baseline ≥0.6 + caso concreto de query ambígua mal-rankeada documentado + decisão arquitetural sobre llama-server local vs cloud API. Reavaliação como design-doc com shadow obrigatório 14d.

Origem: `plans/2026-04-26-clawmem-analysis.md` §3.

---

## 3. Decisões arquiteturais válidas (porque o sistema é assim)

### Search & Ranking

1. **Hybrid search é o padrão** — FTS5 BM25 + Gemini semantic + RRF (k=60, λ=0.7). Pure vector mente em recall lexical; semantic-only quebra silenciosamente. Canário `match_type:"semantic"` `*/30min` é não-negociável.
   *Origem:* `v1.5 §search`; `feedback_shadow_mode_for_ranking_changes.md`

2. **Salience formula multiplicativa** — `recency × pain × importance`. Boost multiplicativo empilhável é veneno; usar aditivo. Violação causou incident v3.4.
   *Origem:* `CLAUDE.md regra 8`; `v1.5 Fase 1.7b-b`

3. **Shadow-mode 7d obrigatório antes de aplicar ranking change** — `NOX_SALIENCE_MODE=shadow`, `NOX_SECTION_BOOST_MODE=shadow`. Validar baseline em `/api/health` antes de ativar.
   *Origem:* `feedback_shadow_mode_for_ranking_changes.md`

### Schema & Storage

4. **`chunks` é a tabela canônica** — `kg_entities`/`kg_relations` derivados via Gemini extraction. Evita 3-way drift dos silos ClawMem-style (docs+observations+KG separados).
   *Origem:* `v1.5:651`; ClawMem analysis §5

5. **Schema migrations aditivas + backfill** — v8 retention_days, v9 pain, v10 section. Sempre `ALTER TABLE ADD COLUMN` + backfill heurístico. Nunca DROP/recreate.
   *Origem:* `CLAUDE.md` schema; v1.5 §67-69

6. **Workspace memory > daily files** — `memory/entities/<type>/<slug>.md` formato 3-section (compiled/frontmatter/timeline). Ingest via `ingestEntityFile()` produz N+2 chunks com section_boost {compiled:2.0, frontmatter:1.5, timeline:0.8}.
   *Origem:* `reference_entity_file_format.md`

7. **Single ingest-router unified** — `routeIngest()` em `src/lib/ingest-router.ts` é dispatch único (entity/markdown/graphify) usado por watch/reindex/CLI/MCP. Defesa em camadas com guard `ingestFile` mantido.
   *Origem:* `reference_a2_ingest_router.md`; v1.6 Fase A2

### Operations & Safety

8. **`withOpAudit()` wrapper obrigatório em ops destrutivas** — VACUUM INTO snapshot atômico em `/var/backups/nox-mem/pre-op/`. Retention 7d, ACL 0600, dir 0700, symlink-aware via realpathSync.
   *Origem:* `CLAUDE.md regra 15`; `reference_a1_op_audit_module.md`

9. **`ops_audit` append-only (CWE-693)** — triggers `trg_ops_audit_no_delete` + `trg_ops_audit_terminal_immutable` ABORT em DELETE/UPDATE de status terminal.
   *Origem:* `audits/2026-04-26-W2-cleanup.md` W2-1

10. **`closeDb()` pertence ao caller, NUNCA mid-function** — singleton lifecycle = CLI handler / daemon startup / test setup. Nunca dentro de função wrapped por context manager (withOpAudit, withTransaction, etc).
    *Origem:* `feedback_closedb_mid_function_invalidates_withopaudit.md`; B2 lesson 04-26

11. **`--dry-run` ou `withOpAudit()` obrigatório em** reindex/consolidate/compact/crystallize/kg-prune. NOX_ALLOW_NO_SNAPSHOT=1 só emergencial.
    *Origem:* `CLAUDE.md regra 15`

12. **Validar features com DB state, não logs alone** — graph-memory rodou zombie 4 dias porque afterTurn logs fired mas gm_messages stayed empty. Sempre query persistent state directly.
    *Origem:* `feedback_validate_features_with_db_not_logs.md`

### OpenClaw / Anthropic Max OAuth (schema canônico v.29 pós-2026-05-01)

13. **Anthropic via Max OAuth = zero-cost backend** — provider `anthropic` (`baseUrl: https://api.anthropic.com`) com auth-profile `anthropic-max` usa subprocess CLI Claude que lê **só** de `.credentials.json` (NÃO env var `CLAUDE_CODE_OAUTH_TOKEN` conflitante). `chattr +i` após `setup-token`. Fallback chain canônica = `[openai-codex/gpt-5.5, gemini/gemini-2.5-pro]` (sem duplicar primary; provider `claude-cli/*` foi removido em v.26 — usar `anthropic/<model>`).
    *Origem:* `CLAUDE.md regra 5` (reescrita 2026-05-01); audits sessão de 2026-05-01

14. **Editar `openclaw.json` via `openclaw config set`, NÃO `jq + mv`** — gateway tem in-memory canonical state que sobrescreve edits manuais no startup.
    *Origem:* `CLAUDE.md regra 5`; `feedback_openclaw_config_set_required_for_persistence.md`

15. **`agentRuntime.id` deve ser `pi` (não `claude-cli`)** — schema v.26 removeu provider `claude-cli`. `agentRuntime.id = "claude-cli"` causa erro `Requested agent harness "claude-cli" is not registered` em crons isolated. Fix universal: `for i in 0..6: openclaw config set agents.list.$i.agentRuntime.id pi`.
    *Origem:* fix sessão 2026-05-01 (vectorize-weekly broken 7+ dias)

16. **OpenClaw v.24 NÃO atualizar até .25 stable** — bug #71957 (claude-cli harness race) deprecou choiceId; fix em .25-beta.4. Defesa: `oc-upgrade <version>` orchestrator com pre-flight check + auto-rollback.
    *Origem:* `feedback_openclaw_24_breaks_claude_cli_harness.md`; commit `3b9e23c` (referência histórica — schema mudou em v.26+)

17. **Sessions.json filtrar pós-mudança model.primary** — `jq 'with_entries(select(.value.model | startswith("claude-")))'` ou reset `{}`. Sem isso, sessions stuck em fallback model.
    *Origem:* `CLAUDE.md regra 11`

### Models & Costs

18. **Modelo Gemini default = `gemini-2.5-flash-lite`** — `flash` estoura quota 3M/d; `2.0-flash` deprecated jun-2026; KG extraction usa flash full enquanto volume baixo.
    *Origem:* `CLAUDE.md regra 4`; `feedback_model_selection_for_agent_infra.md`

19. **No secrets in git — ever** — API keys, tokens, creds só em `.env` (perms 0600). Run regex grep before commit. Aplica a todos repos incl. private.
    *Origem:* `feedback_no_secrets_in_git.md`; `feedback_no_hardcoded_secrets.md`

20. **Per-agent heartbeat só nas 6 personas** — main agent NUNCA heartbeat (gera "Unknown Channel" persistente). nox/atlas/boris/cipher/forge/lex.
    *Origem:* `CLAUDE.md regra 14`

### Evolution rules

21. **Wave gating métrico (não calendário)** — Wave 1→2 gated em ≥80% rels classificadas + 7d shadow. Wave 2→3 em nDCG baseline publicado.
    *Origem:* v1.6 §7

22. **Cross-Agent via SOUL.md (não algorítmico)** — over-engineering para 6 agentes; group routing rejeitado filosoficamente. `cross-search` cobre ad-hoc.
    *Origem:* v1.5 Decisão 4

---

## 4. Lições críticas (incidents resolvidos)

| Data | Incident | Root cause | Mitigação aplicada | Memory feedback |
|---|---|---|---|---|
| 2026-04-26 | OpenClaw v.24 quebrou produção (~10min downtime) | Bug #71957 race condition: channels.startup() fired BEFORE anthropic plugin registers claude-cli harness | Rollback .24→.23 via `rollback-zero-downtime.sh`. **Sistema upgrade defense** (ckpt + improvements + watcher + oc-upgrade orchestrator) construído pra prevenir | `feedback_openclaw_24_breaks_claude_cli_harness.md` |
| 2026-04-26 | 6 zombie ops_audit rows + B1 reaper coverage gap | `closeDb()` mid-function em `_reindexImpl` invalidou `withOpAudit` final UPDATE | Removido closeDb mid-function; `reapZombies()` no preAction hook | `feedback_closedb_mid_function_invalidates_withopaudit.md` |
| 2026-04-26 | Audit triplo: 7 HIGH security/code follow-up | snapshot dir 0755 + DB 0644 world-readable; UUID 32-bit; secret leak em ops_audit | realpathSync.native; UUID 128-bit; statSync TOCTOU; `scrubSecrets()` redact | `audits/2026-04-26-7highs-followup-fix.md` |
| 2026-04-25 | Section/retention metadata wipe via reindex (~12min recovery) | `reindex.ts DELETE+ingestFile` genérico ignorou `ingestEntityFile`; OpenClaw end-of-day cron rodava reindex full diário | Guard em `ingestFile` rota entity files via `ingestEntityFile`; cron step 11 reindex→consolidate; user-systemd órfão killed | `feedback_reindex_must_route_entity_files.md` |
| 2026-04-23 | `openclaw models auth login` overwrite (fratricide loop) | Comando remove entries `agents.defaults.models` + reinstala node_modules (destrói monkey-patch #62028) | Reapply automatizado `/root/reapply-monkey-patch.sh`; CLAUDE.md regra 6 atualizada | `feedback_openclaw_models_auth_login_removes_registry.md` |
| 2026-04-23 | graph-memory zombie DONE 4 dias | Plugin v1.5.8 esperava hook `ingest()` que OpenClaw 2026.4.21 não chama mais | Patch local em afterTurn → `for (const m of newMessages) ingestMessage(...)` | `feedback_validate_features_with_db_not_logs.md` |
| 2026-04-21 | Gemini + Perplexity keys exposed/revoked | Hardcoded `apiKey` em 7 JSONs + ingested chunks + backups | Migração completa pra envsub `${VAR}`; gitleaks pre-commit global | `feedback_no_secrets_in_git.md` |
| 2026-04-20 | Gemini 2.5 Flash quota blowout | Default era flash full (3M/d quota); concomitante Anthropic burn oculto | Default → flash-lite; routing per-agent; agent-infra tasks lock em flash-lite | `feedback_model_selection_for_agent_infra.md` |
| 2026-04-20 | Gateway fratricide Issue #62028 (~6h downtime) | `cleanStaleGatewayProcessesSync` mata gateway autoritativo | Monkey-patch return `[]`; wrapper imutável `chattr +i`; reload.mode=off | `CLAUDE.md regra 6` |

---

## 5. Constraints arquiteturais permanentes

Lista de constraints que **NÃO mudam sem ADR explícito**:

- `bootstrapMaxChars` limit on system prompt budget (graph-memory R7 ≤30K tokens compression target)
- Salience formula multiplicativa: `recency × pain × importance` (sem empilhamento aditivo de boosts)
- `ops_audit` append-only via triggers (CWE-693): DELETE blocked, UPDATE blocked em status terminal
- Single memory plugin (graph-memory only); não adicionar segundo sem ADR
- `chunks` é tabela canônica única; `kg_entities`/`kg_relations` são derivados, não silos paralelos
- Vocabulário `relation_reason` enum CLOSED 7 valores (`mentions/owns/decides/depends/derives_from/contradicts/supersedes`); nunca free-form
- 16 MCP tools cap (não escalar para 30+); capabilities crescem via search quality
- `superseded_by` imune a TTL/Smart Forgetting (preserva histórico)
- Trigger `trg_chunks_delete_cascade` nunca remover (DELETE chunks → limpa vetores)
- `nox-mem-api` SEMPRE em :18802 via env `NOX_API_PORT`; nunca hardcode
- Node.js wrapper bash `/usr/bin/node` → `node.bin --no-warnings` (sem isso DEP0040 crashloop)
- `chattr +i ~/.claude/.credentials.json` após setup-token (CLI auto-trunca em ~8h sem isso)
- Snapshot pré-op ACL 0600, dir 0700, retention 7d, ALLOWED_PREFIXES `/var/backups/` ou `/root/.openclaw/`
- Free space check `statfsSync` ≥2x DB size antes de VACUUM INTO (DoS prevention)
- Schema invariants canary `*/15min` Discord alert (5 invariants ativos)
- Backup-all daily 02:00 retention 7d (NÃO substitui pre-op snapshot)
- `agents.defaults.models` jamais editado removendo entries
- `--dry-run` ou `withOpAudit()` obrigatório em reindex/consolidate/compact/crystallize/kg-prune
- Logs e DB state ambos validados antes de marcar DONE (log-only validation = fake-green)
- PT-BR "você" not "tu" (registro Brasil/Hotmart NOX-Supermem audience)
- Vault Obsidian view-only com excludes locais (themes/plugins/snippets/community-plugins/appearance/graph.json)

---

## 6. Append log (decisões pontuais por data)

### 2026-04-27
- **Consolidação documental** — criados ROADMAP.md + DECISIONS.md + HANDOFF.md como single source of truth. Move 25 plans/ + 9 handoffs/ pra `_archive/` (referência histórica).
- **Recalibração de horas v1** (manhã) — todos estimates aplicaram velocity ingênua (~0.4× uniforme).

### 2026-04-27 (tarde — review triplo + sistema unificado)
- **Sistema unificado de IDs F/E/R/P/G/D** substitui 6+ namespaces (A/B/W/Q/Fase/Phase/Wave/Bloco). Cross-ref em ROADMAP.md §8.
- **Review triplo aplicado** (architect + critic + architect-reviewer) — 14 mudanças no ROADMAP:
  - **F09 off-site backup** adicionado P0 (architect: gap crítico — single VPS = disk failure apaga 7.3k chunks; rclone B2/R2 1h)
  - **F10/F12/F13/F14** gaps adicionados (observability dashboard, Gemini SPOF playbook, cost projection alt, DR drill trimestral) — ~~F16~~ telegram rollback bot moved 2026-05-03 → openclaw-vps/infra (escopo plataforma, não memória)
  - **R01 dividido em R01a/R01b/R01c** (skeleton Maio + curation Jun-Jul + baseline) — antecipação por architect-reviewer pra baseline-first antes de E05 mudar ranking
  - **E03/E04 (A6/A7) dividido em implement/activate** — captura latência shadow 7d wall-clock (critic apontou: viola própria regra `feedback_shadow_mode_for_ranking_changes.md`)
  - **Velocity bucketada** (greenfield 0.7×, hardening 0.4×, cognitive floor não comprime) — critic apontou: 0.4× uniforme em curadoria 50 queries é fantasia
  - **Capacity recalibrada** 6h/sem realista × 22 sem = 132h (era 10h/sem × 5 meses = 50h fantasia); margem incident 5h → 20h baseado em histórico (4 incidents 2 dias 04-25/26)
  - **D02 promovido CUT → DEFERRED** (W3.2 plugin hooks): pré-req arquitetural pra multi-tenancy P01, não cortar permanente
  - **D01 trigger antecipado** (Q5 reranker): "2 PRs com query mal-rankeada documentadas" como early trigger além do R01c
- **Reorganização professional do repo:**
  - `paper/` ← top-level (era em `archive/`)
  - `docs/VISION.md` ← renomeado de `nox-neural-memory.md` (convenção)
  - `docs/ARCHITECTURE.md` ← NOVO (system design + ASCII diagrams)
  - `docs/RUNBOOKS.md` ← NOVO (10 incident playbooks RB-01 a RB-10)
  - `docs/CONTRIBUTING.md` ← NOVO (standards + PR process + AI assistant rules)
  - `README.md` ← reescrito profissional (badges + arch diagram + doc map)
- **NÃO foi mudado:** decisões arquiteturais §3, constraints §5, lições §4 — todos permanecem válidos.

### 2026-04-26
- **OpenClaw upgrade defense system** construído (commit 3b9e23c) — 4 sprints: ckpt + improvements manifest + release watcher + oc-upgrade orchestrator. Commit pushed origin/main.
- **NÃO atualizar OpenClaw para .24** até .25 stable — bug #71957 confirmado.
- **Audit triplo aplicado** — 4 reviewers paralelos detectaram 47 findings; 11 HIGH fechados em 2 commits; 11 MEDIUM/LOW Wave 2 fechados.
- **Fase 4 Obsidian view-only DONE** (era POST-GATE 05-02+; antecipado).

### 2026-04-25
- **Roadmap v1.6 promovido canônico** — 4 rodadas de revisão (architect, critic, planner, architect-reviewer + segunda rodada técnica).
- **Bloco I A0-A5 100% DONE** em 1 dia.
- **Regra #15 adicionada CLAUDE.md** — "reindex/consolidate/crystallize só com `--dry-run` OU snapshot atômico".

### 2026-04-26 (ClawMem analysis decision)
- **5 candidates promovidos a CANDIDATE** (não committed) — A6, A7, W1.5, W2.2, Q5
- **NÃO bumpar v1.6→v1.7 nem v14→v15** — subagents leriam Q1-Q5 como decididos
- **4 NÃO FAZEMOS adicionados** (Phase 3 deductive synth, Phase 4 worker, heavy-lane worker, silos schema)

### 2026-04-27 (Sprint A1 — backfill ingestão pré-R01a)
- **Re-ordering decision:** ingestão massiva ANTES de R01a, motivada por 3 razões:
  1. Curadoria R01b (50 golden queries, 8-10h cognitive floor) ficaria stale se corpus crescer 50% depois
  2. Baseline R01c em corpus parcial vira obsoleto assim que Tier 2/Tier 3 completarem
  3. E07 impact + E10 consolidation precisam do grafo completo pra blast radius correto
- **Trade-off aceito:** G01 baseline 7d shadow pode shift 2-3 dias se distribuição salience mudar significativamente pós-A1. Não é catástrofe, é ajuste de cronograma.
- **Sprint A1 Fase 1 — graphify-ingest 9 repos com graphify-out já gerado:** +1.046 graph_nodes (Future-Farm 34 + GalapagosApp 150 + Granix-App 163 + agent-hub-dashboard 240 + daily-tech-digest 112 + memoria-nox 50 + nox-supermem 56 + projeto-ai-galapagos 147 + sao-thiago-fii 94)
- **Sprint A1 Fase 2a — clone+ingest 7 repos pequenos:** +304 chunks (biolab-ai, curso-ai, posts-linkedin, grancoffee, superfrio, fake-news-check, claude-project-template)
- **Sprint A1 Fase 2b — Claude workspace scope curado (Plano A):** +17.714 chunks de 1.356 md (docs+agents+skills+commands+Projetos)
- **Scope cuts deliberados:**
  - **SKIP `_retired/` 502 md** — deprecated/arquivado, ruído
  - **SKIP `prompts/` 43 md** — baixo signal-to-noise
  - **SKIP `powerpoint-templates` 114MB** — visual content, gated Tier 3 OCR (E12 opcional)
  - **SKIP `nox-workspace` 257MB** — scope decision posterior (config + skills + agents misturados)
- **Implicação F09:** off-site backup vira mais crítico (DB +38%: 318MB → ~440MB). Re-priorizar quando voltar atenção pós-G01.
- **Implicação watcher:** inotifywait race em `git clone` rápido (15 md files perdidos no event stream); ingestão manual via `nox-mem ingest` foi necessária. Não é regressão, é limitação conhecida do filtro `--include`.
- **Não-mudança intencional:** `_retired/` ficará permanentemente excluído mesmo em re-runs (ruído arquivado).
- **Sprint A3 — Mac local Claude/Projetos delta (mesmo dia):** +863 chunks via rsync `~/Claude/Projetos/agent-orchestrator/` → shared/imports/ (106 md). Único projeto local-only que não duplica shared/imports/<repo>/.
- **A3 scope cuts:**
  - SKIP A2 (`~/Desktop/*`) — usuário declarou "transitório"
  - SKIP outros 240 md de `~/Claude/Projetos/*` — duplicariam shared/imports/<repo>/ já ingestado (memoria-nox, Granix-App, nox-supermem, etc)
- **Sprint A4 — ~/Documents office files (mesmo dia):** +2.469 chunks via rsync seletivo docx+xlsx+pptx + conversion pipeline expandido
  - 6 dirs sincronizadas: NUVIVI, PPR, PESSOAL, CONTRATOS, BANCOS, EMPRESAS Cont
  - 972 xlsx → md (libreoffice-calc → csv → markdown wrapper) → +1.860 chunks
  - 81/83 pptx → md (markitdown, Microsoft Python) → +609 chunks
  - 6 docx idempotent updates
  - **Stack expandido permanentemente:** `libreoffice-core/calc/impress` + `markitdown[pptx]` (PyPI 0.1.5)
  - **markitdown adotado oficialmente** — substitui libreoffice-impress que tem filter txt missing; cobre PPTX/PDF/DOCX/XLSX/Images-OCR/Audio/HTML/CSV/JSON/XML/ZIP/EPubs. Future: avaliar substituir todo pipeline (libreoffice + pandoc) por markitdown unified
  - SKIP fotos/videos (não-textual em ~/Documents) — usuário declarou
- **F09 off-site backup REJEITADO permanentemente** — VPS Hostinger nativo basta. User declarou 2x ("já disse, VPS tem backup", "não vamos gastar tempo e espaço nisso"). Não sugerir mais como next action mesmo quando DB cresce.
- **Sprint A5 — Pipeline unified (mesmo dia):** `convert-office-to-md.sh` refatorado pra markitdown primary + fallback. `pdf-batch.sh` standalone reusável em `/root/.openclaw/scripts/`. Idempotente.
- **Sprint A6 — PDF batch Tier 2 antecipado (mesmo dia):** +19.602 chunks de 4.494 PDFs `~/Documents` (NUVIVI 546 + PPR 1807 + PESSOAL 1163 + CONTRATOS 689 + BANCOS 142). 1.444 text-layer convertidos com sucesso; 781 scanned/imagem descartados (esperam OCR Tier 3 / E12).
- **Lições incident A6 (3 tentativas):**
  - **Tentativa 1:** SSH command com `nohup ... &` — parent-shell death matou children apesar nohup. Lesson: `disown` necessário ou usar systemd-run/tmux
  - **Tentativa 2:** systemd-run com bash inline — `${f%.pdf}` interpretado como env var pelo systemd quoting hell. Lesson: scripts standalone em arquivo, NÃO inline em systemd-run
  - **Tentativa 3:** Watchdog próprio (`pdf-batch-watchdog.service`) — pgrep regex falsa positiva spawnou 69 markitdown simultâneos, sufocou VPS (load 22, OOM-like comportamento). Lesson: NÃO escrever watchdog próprio se systemd-run + Restart=on-failure resolve
  - **Tentativa 4 (final ✅):** `tmux new-session -d` chamando script standalone. Estável, sobrevive SSH disconnect, sem complexidade extra.
- **Adoção markitdown ampliada:** `markitdown[pdf,docx,xlsx,pptx]` instalado. PDF batch 2.66s/PDF média sem OCR. OCR (precisa OpenAI key) fica gated em E12.
- **Resultado total dia 2026-04-27:** corpus triplicou (20.831 → 62.836 chunks, DB 318MB → 1.016 GB). Pré-R01a baseline em corpus completo cumprido.

### 2026-05-01 (G02 section_boost activation + design specs paralelos)
- **G02 ✅ APLICADO** — `NOX_SECTION_BOOST_MODE=shadow → active`. Análise telemetria 7d pré-decisão: 1.578 events.
  - **compiled** n=1252 (79%), mean delta +100.32% (boost 2.0× efetivo, dentro de 1% do target)
  - **frontmatter** n=315 (20%), mean delta +48.94% (boost 1.5× efetivo, dentro de 1% do target)
  - **timeline** n=11 (0.7%), mean delta -17.45% (boost 0.8× = demote intencional documentado)
  - Decisão: ativar todos 3 boosts conforme schema v10. Timeline n=11 é statistically insignificant mas o boost é design choice (timeline = history não deve dominar compiled truth).
  - Backup pré-mudança: `/root/.openclaw/.env.bak-pre-section-boost-active-20260501-203152`. Rollback documentado.
- **G03 ✅ DONE** — 3 source files (`memory/{projects,decisions,lessons}.md`) arquivados como `.archived-20260502`. 8 chunks órfãos restantes (lessons=4, decisions=2, projects=2) cleanup deferido pro consolidate noturno (cron 02:00) — sqlite3 CLI direto não consegue deletar (módulo `vec0` não loaded em standalone, trigger cascade falha). Lição: cleanup orphans só via app context (better-sqlite3 com extension), nunca via sqlite3 standalone.
- **Specs E03a + E04a CRIADAS** — `specs/2026-05-01-E03a-spo-injection.md` (vault-facts block via KG, 1.5h impl) + `specs/2026-05-01-E04a-focus-boost.md` (focus set/clear/get com cache file TTL 7d, 1.5h impl). Ambas zero-mudança schema, env-var driven shadow→active per regra `feedback_shadow_mode_for_ranking_changes.md`.
- **R01a re-validado** — spec 04-27 está pronta pra execução Maio (5h). Schema target será **v11** se R01a executar antes de E05; v12 se depois. Decisão pragmática: **R01a primeiro = v11** (E05 está gated em R01a baseline, ordem natural).
- **E02 audit revisado** — gap real ≠ estimativa: **954 PDFs (não 2.269)**. Cobertura A6 = 3.541/4.495 = 79%. Distribuição gap: PPR 372 / PESSOAL 250 / CONTRATOS 171 / EMPRESAS Cont 83 / NUVIVI 55 / outros 23. Size analysis: ~585 recuperáveis (text-layer 100KB-10MB), ~307 OCR-only (<100KB ou >10MB).
- **E02 retry B-target IN-PROGRESS** — decidido escopo cirúrgico (NUVIVI+CONTRATOS = 226 PDFs) ao invés de retry completo (954). Motivação: alta priority business (Filings-SEC + contratos sociais), 3-4h I/O bound em background não-conflitante com R01a, validação real do retry pattern antes de commit dos 954.
  - Sample primeiros 8 NUVIVI: todos SCANNED <100ch (contratos sociais escaneados, Side Letters, alterações). Recovery rate baixa esperada pra NUVIVI; CONTRATOS depois dirá efetividade real.
  - Path canônico: `/root/.openclaw/workspace/memory/mac-docs/` (consistente com source_file no DB).
  - Script standalone tmux per regra `feedback_long_running_batch_use_tmux.md` (lições incident A6).
- **E02 escopo revisado:** marcado IN-PROGRESS; gap residual (~728 PDFs PPR+PESSOAL+size-rejected) movido pra E12 OCR (Tier 3). E12 escopo expandido pra cobrir gap.
- **Lição cleanup orphans:** `sqlite3` CLI standalone NÃO consegue triggers que dependem de extensions runtime-loaded (vec0/sqlite-vec). DELETE em chunks falha em "no such module: vec0" porque `trg_chunks_delete_cascade` referencia `vec_chunks`. Caminho correto: app context (better-sqlite3 com extension) ou esperar consolidate noturno.

### 2026-05-01 (noite extra — bug fixes)
- **Cleanup 8 chunks órfãos G03 ✅** via better-sqlite3 (`node -e "require('./dist/db.js').getDb().prepare('DELETE FROM chunks WHERE source_file IN (...)').run()"`). DB 62.927 → 62.919. vec_chunks cascade-deleted. Confirmado caminho correto pra orphan cleanup operacional.
- **PRAGMA user_version aligned 0 → 10 ✅** — F14 DR drill expôs que `PRAGMA user_version=0` enquanto `meta.schema_version=10`. Análise: NÃO É BUG SCHEMA — é inconsistência de fonte. nox-mem usa `meta.schema_version` como source-of-truth canônico (via `ensureSchema` em db.ts); `PRAGMA user_version` é só sentinel usado em `op-audit.safeRestore()` pra validar schema mismatch durante restore. Bumpado pra 10 manualmente via `sqlite3 ... "PRAGMA user_version = 10"`. Backup `/var/backups/nox-mem/pre-bump-pragma-20260501-211006.db`. Future ops_audit registrará `schema_user_version=10` corretamente. R01a impl bumpa pra 11/12 em `migrateToV11/V12` normais.
- **op-audit-e2e bug ✅ FIXED** — `src/db.ts:7` patched pra honrar `process.env.NOX_DB_PATH` (priority: NOX_DB_PATH > OPENCLAW_WORKSPACE > __dirname fallback). Test setupDb refeito: era CREATE TABLE chunks com schema v1 minimal que entrava em conflito com migrations cumulativas v3+ (source_date, pain, section adicionados). Solução: deixar ensureSchema do getDb() construir schema v10 completo, depois INSERT samples via SQL direta. **27/27 tests pass** (retention 20 + op-audit-e2e 7). Backup `src/db.ts.bak-pre-noxdbpath-20260501-211042`. Build redeployado, prod nox-mem-api restarted health OK.
- **Lição test setup vs migrations cumulativas:** test que cria tabela manualmente conflita com schema migrations idempotentes (CREATE TABLE IF NOT EXISTS encontra tabela pré-existente sem colunas que migrations v3+ esperam). Padrão correto: deixar app code construir schema (via getDb() → ensureSchema), test só insere data sample.

### 2026-05-04 — Paper publication: decisões D23–D27

#### D23 — BGE-M3 cortado; multilingual-e5-base substituto como dense baseline
- **Decisão:** Pular `BAAI/bge-m3` (568M params) como dense baseline no paper; usar `intfloat/multilingual-e5-base` (278M params, 768d).
- **Por quê:** BGE-M3 testado em CPU 2026-05-04: throughput = 0.3 chunks/s → 55h ETA pra 61K chunks. Inviável overnight. multilingual-e5-base = 2.8 chunks/s → ~5.5h, coberto em batch noturno. Corpus PT+EN é mix-aware com multilingual-e5.
- **Trade-off aceito:** -5–10% qualidade máxima vs BGE-M3 full-recall, mas dense baseline ainda competitivo em BEIR e suficiente pra paper contribution.
- **NÃO FAZEMOS:** rodar BGE-M3 em CPU (55h = impraticável); cogitar Modal cloud GPU a menos que reviewer exija comparison específica em revisão pós-submit.
- *Origem:* sessão 2026-05-04; NÃO FAZEMOS §1 itens 21+24.

#### D24 — Pain ablation deferred pós-submit arXiv
- **Decisão:** Ablation completa de pain (pain=1.0 uniform vs valores reais) deferred pós-submit 2026-05-19. Baseline pós-incident medido: nDCG@10 = 0.2689 (n=6).
- **Por quê:** Ablation requer 2× restart de `nox-mem-api` em prod (DB swap pra TEMP DB com pain=1.0 → eval → restore). Janela ~2min downtime precisa de autorização explícita separada. Paper §5.5 permanece íntegro: design contribution de pain-weighted salience não depende de ablation para o submit — ablation fortalece mas não é pré-requisito.
- **Trade-off aceito:** §5.5 marcado "deferred future work" em vez de "confirmed via ablation". Diferencial #1 (pain-weighted salience) permanece como design contribution com baseline empírico.
- **NÃO FAZEMOS:** restart prod sem janela autorizada explicitamente; omitir pain do paper por ablation incompleta (baseline empírico é suficiente).
- *Origem:* sessão 2026-05-04; NÃO FAZEMOS §1 item 22.

#### D25 — Cross-agent retrieval-level quantification deferred (E12-followup)
- **Decisão:** Cross-agent quantification confirmada no nível de storage (99.92% chunks compartilhados); retrieval-level (% queries com top-1 hit cross-agent) deferred até E12-followup migration.
- **Por quê:** `search_telemetry` não tem coluna `requesting_agent` (sketch nunca deployado). Adicionar = 1h impl + mínimo 2 semanas aguardando telemetria popular. Bloqueia submit por insuficiência de dados. Storage-level claim é empiricamente forte e suficiente pra §5.6.
- **Trade-off aceito:** §5.6 apresenta 99.92% storage-level + marca retrieval-level quantification como "future work". Não enfraquece a contribuição de cross-agent memory sharing.
- **NÃO FAZEMOS:** retrofit migration ad-hoc só pra paper sem ciclo de teste de 2 semanas; remover §5.6 por falta de retrieval-level data.
- *Origem:* sessão 2026-05-04; NÃO FAZEMOS §1 item 23.

#### D26 — LICENSE MIT confirmado
- **Decisão:** MIT license adotada pro repo `memoria-nox`. Apex: Luiz Antonio Busnello.
- **Por quê:** Maximiza adoption, permissivo, padrão em research projects e papers técnicos. Compatível com integração em OpenClaw (privado) e NOX-Supermem (comercial) sem restrições copyleft.
- **NÃO FAZEMOS:** AGPL ou qualquer copyleft — audience é mista research + commercial; copyleft restringiria integração nos repos privados do ecossistema.
- *Origem:* sessão 2026-05-04; NÃO FAZEMOS §1 item 27. Cross-link: `docs/VISION.md` §licensing.

#### D27 — Submit timing: arXiv 2026-05-19 Tuesday 09:00 ET; blog Wednesday; HN Thursday
- **Decisão:** arXiv submit Tuesday 2026-05-19 09:00 ET. Blog post Wednesday 2026-05-20. HN "Show HN" Thursday 2026-05-21 09:00 ET.
- **Por quê:** Tuesday é peak de visibilidade no feed arXiv (menor competição que Monday + maior que Wednesday). HN Thursday tech audience peak pra "Show HN". Blog Wednesday dá buffer de 1 dia pra rascunho do top comment HN e link canonical externo.
- **Trade-off aceito:** Uma semana de lead time pós-E05 Phase 1 (schema v12 concluído 2026-05-04). E05 Phase 2 + paper final writing em paralelo na semana de 2026-05-12.
- **NÃO FAZEMOS:** submit Friday/weekend (baixo engagement arXiv + HN); submit sem blog (HN thread precisa de link externo canonical, arXiv link direto não converte em discussão de produto).
- *Origem:* sessão 2026-05-04; NÃO FAZEMOS §1 itens 25+26. Cross-link: `docs/ROADMAP.md` §paper-publication gate.

#### D28 — multilingual-e5-base baseline: gemini-embedding-001 permanece canonical
- **Decisão:** Não trocar embedding primário para multilingual-e5-base. gemini-embedding-001 (3072d) permanece canônico.
- **Resultados E5 baseline** (n=60 golden, 3-run replicado): nDCG@10=0.3070, MRR=0.3720, Recall@10=0.3708, Precision@5=0.1067. Custo: ~6h embed CPU 8-core, cache 162 MB, eval <1s pós-cache.
- **Comparação:** hybrid (gemini) 0.5213 vs E5 0.3070 = +0.2143 (1.7× lift). Hybrid vence 5/8 categorias. E5 vence 2/8 narrow (cross-agent +0.013, temporal +0.017) dentro do MOE.
- **Por quê:** Lift 1.7× supera redução de custo 12×. Robustez por categoria favorece hybrid. Margens E5 em cross-agent e temporal são estatisticamente insignificantes.
- **NÃO FAZEMOS:** trocar embedding primário (item 28 §1). E5 fica como baseline paper (dense comparison), não como runtime.
- *Origem:* sessão 2026-05-04 sprint W2; NÃO FAZEMOS §1 item 28. Resultados: `paper/publication/results/E02-E5-multilingual-baseline-summary.md`.

#### D29 — BM25 recall ceiling é a constraint dominante; pain permanece modulador secundário
- **Decisão:** pain dimension mantida como modulador secundário pós-RRF; NÃO promovida a multiplicador BM25 pré-fusão.
- **Resultados E10** (pain ablation): hybrid Δ=+0.0065 NOT_SIGNIFICANT (n=31); FTS-only Δ=0.0000 (n=31), Δ=+0.0061 (n=60) INSIGNIFICANT. Calibration test 4 distribuições (real/uniform/bimodal/log-scale): H1+H2+H3 REFUTED.
- **Q55 case study:** Δ=+0.349 em regime narrow tied-semantic — pain é real mas regime-bound.
- **Root cause real:** BM25 RECALL CEILING — 92% (55/60) das golden queries falham em surfaçar gold via lexical retrieval, independente de calibração de pain. Pain não pode compensar ausência de match lexical.
- **Por quê:** Efeito de pain é real mas confinado ao regime onde BM25 já rankeia o gold (Q55). Promover pain a pré-fusão não resolve o teto de recall. Re-posicionamento de pain como post-RRF re-ranker é trabalho futuro aberto.
- **Trade-off aceito:** pain contribution documentada como regime-bound em §5.5. Não enfraquece o design contribution.
- *Origem:* sessão 2026-05-04 sprint W2. Resultados: `paper/publication/results/E10-pain-ablation-hybrid-results.md`, `E10-pain-ablation-fts-only.md`, `E10-pain-calibration-test.md`.

#### D30 — LOCOMO adotado como segundo benchmark third-party (§5.2)
- **Decisão:** LOCOMO é o segundo benchmark externo no paper §5.2, ao lado de BEIR TREC-COVID.
- **Adapter:** `paper/publication/baselines/locomo_eval.py` — stdlib SQLite FTS5, ~250 linhas. Schema correto: snap-research/locomo (NÃO snap-stanford), CC BY-NC 4.0.
- **Resultados** (n=100 stratified seed=42): FTS5 nDCG@10=0.2810.
- **Cross-corpus ratio:** LOCOMO FTS5 0.281 vs golden FTS5 0.012 = 23× — confirma que nosso corpus é harder (conversacional + multi-agente vs benchmark limpo).
- **Por quê:** Fecha diretamente o crítico C5 (single-corpus). Benchmark de memória conversacional alinha com o framing do paper melhor do que TREC-COVID retrieval-only. 23× ratio é resultado narrativo forte pra §5.2.
- **Trade-off aceito:** LOCOMO é FTS5 baseline (não dense), mas suficiente pra claim de robustez cross-corpus.
- *Origem:* sessão 2026-05-04 sprint W2. Resultados: `paper/publication/results/E04-locomo-summary.md`.

### 2026-05-10 — E14 retrieval evolution roadmap (post-R03): decisões D31–D33

#### D31 — E14 retrieval evolution roadmap arquivado (post-R03)
- **Decisão:** Roadmap multi-alavanca (A1+A2+D+E-lite-2 + addendums latency/schema/parking-lot) arquivado como spec E14, execução pós-R03 (20 mai 2026+). Spec canonical: `specs/2026-05-10-E14-retrieval-evolution.md`.
- **Origem:** 3 rodadas iterativas de proposta Forge (v1→v2→v3), 5 refinamentos pós-v2, 3 addendums consolidados.
- **Baseline:** Hybrid nDCG@10 = 0.699 (eval recente). Target overall: 0.750-0.780. Target cross-language sub-eval: ≥0.85 do overall.
- **Pré-requisito absoluto:** golden set expansion n≥30 (semana 20-23 mai, LLM-assisted, ≥10 cross-language + ≥5 incidentes). Sem isso, qualquer ganho <10% é ruído estatístico (n=5 atual não tem poder).
- **Sequência decidida:** golden set → análise composição (recall zero vs parcial) → E-lite-2 ou A2+D primeiro (depende da composição) → shadow 7d entre ativações → ablation incremental → medir gap.
- **NÃO FAZEMOS:** começar antes de R03 submit (19 mai). Reordenar antes de medir composição do golden set. Implementar F self-hosted (D01-v2 OOM, hardware bloqueado).
- *Origem:* sessão 2026-05-10. Cross-link: `docs/ROADMAP.md` §sprint-pos-R03, `docs/HANDOFF.md` §retomada.

#### D32 — Caminho B (pain-augmented embedding) DEFER para Q3 2026 com gate quantitativo
- **Decisão:** Caminho B deferred para Q3 2026, **não cut**. Pain-augmented embedding altera o vetor em si (vs E-lite-2 que ataca lexical, A2 que amplia pool denso) — proposta de valor distinta, vale preservar pra reabrir condicionalmente.
- **Gate quantitativo de reativação** (após A+D+E completos + golden set expandido):
  - Se cross-language sub-eval mostrar chunks high-pain com recall **< 70% do overall:** B vira **prioridade Q3** (pain embedding ataca representação que anchoring não cobre)
  - Se cross-language sub-eval **≥ 85% do overall:** B vira **cut permanente** (A+D+E resolveram sem re-ingestão)
  - Faixa intermediária (70-85%): caso-a-caso com Cohere fallback antes de B
- **Custo se reativado:** ~8.3M tokens Gemini (3 dias quota Flash com batching), schema migration v.31 (campo `embedding_variant`), shadow A/B duplica custo Gemini (16.6M tokens vs 8.3M solo).
- **NÃO FAZEMOS:** cut permanente sem medir cross-language sub-eval. Reabrir B antes de A+D+E completos (B é redundante se pool + anchoring resolverem).
- *Origem:* sessão 2026-05-10. Spec: `specs/2026-05-10-E14-retrieval-evolution.md` Addendum C.

#### D33 — Caminho F (cross-encoder) como fallback condicional + Schema v.18 sub-task
- **Decisão:** F **não eliminado permanentemente** — vira fallback condicional pós-A+D+E. Self-hosted continua bloqueado (D01-v2 OOM `bge-reranker-v2-m3` em VPS 15GB), mas Cohere API permanece avaliável por métrica.
- **Gate de ativação F:** após A+D+E completos, medir nDCG@10. Se **< 0.775** (faltam ~3-4% pra teto ~0.80), avaliar Cohere `rerank-multilingual-v3.0`. Se ≥0.775, F dispensado.
- **Por quê Cohere e não self-hosted:** D01-v1 CUT por -0.21 nDCG (English não transfere PT-BR), D01-v2 CUT por OOM (15GB VPS insuficiente pra bge-reranker-v2-m3 568M params). Hardware não muda no curto prazo. Cohere API tem custo recorrente aceitável se for último 5-10% pra atingir 0.80.
- **Schema migration v.18 (sub-task de E-lite-2):** `ALTER TABLE chunks ADD COLUMN fts_anchor TEXT`, executa primeira semana de E-lite-2 (27 mai - 02 jun) antes do backfill regex. Rollback via `safeRestore()` (sempre disponível) ou `DROP COLUMN` (requer SQLite ≥3.35.0 — verificar pré-execução).
- **NÃO FAZEMOS:** F self-hosted enquanto VPS for 15GB RAM. Reativar bge-reranker sem upgrade de hardware. Skip schema v.18 dry-run em snapshot atômico (regra crítica #6).
- *Origem:* sessão 2026-05-10. Cross-link: `docs/HANDOFF.md` (D01 v1+v2 cut history), spec `specs/2026-05-10-E14-retrieval-evolution.md` Addendum B.

### 2026-05-15 — Op-audit canonical patterns (Gap A→E fixes): decisão D34

#### D34 — Op-audit canonical patterns (post-Gap A→E fixes 2026-05-15)
- **Decisão:** consolidar 4 padrões arquiteturais derivados do triage de op-audit como invariantes operacionais — todos derivam de gaps reais que tornaram audit trail ambíguo, frágil ou cego.
- **Padrão 1 — `NOX_DB_SOURCE` env primary, parse fallback, `'unknown'` final.** Toda invocação CLI/cron precisa exportar `NOX_DB_SOURCE=<agent>|main` antes do `node`. `deriveDbSource()` em `src/lib/op-audit.ts` tenta env primeiro, depois parse do path (`/agents/<X>/` → `X`), depois `'unknown'`. Decisão defensiva: sem env explícito não dá pra confiar em parse heurístico em multi-agent layout — `'unknown'` é melhor que classificação errada.
- **Padrão 2 — Append-only `ops_audit` é não-negociável.** 2 triggers (`trg_ops_audit_no_delete` bloqueia DELETE, `trg_ops_audit_terminal_immutable` bloqueia UPDATE em rows status terminal) protegem CWE-693. Trade-off aceito: rows legacy podem apontar `snapshot_path` para arquivo deletado pelo `prune-pre-op-snapshots.sh` (audit trail completo > disk minimal). Status enum válido: `started/success/failed/crashed` (NÃO `completed`, NÃO `rolled_back`).
- **Padrão 3 — Snapshot via app context, nunca via `sqlite3` CLI standalone.** Forge Q1 sign-off confirmou: `sqlite3` CLI **não carrega `vec0.so`**, daily snapshot precisa rodar em app context (better-sqlite3 + extension loaded por `db.ts`). Subcomando `dist/cli/snapshot-main.js` wrappa `withOpAudit('daily-main')` com callback no-op (VACUUM INTO atômico + integrity_check + ops_audit row registrada). Wrapper bash `snapshot-main-db.sh` (cron `0 3 * * *`) faz gzip -9 (~72% ratio) + retention 5d.
- **Padrão 4 — HARD_TIMEOUT + heartbeat + watchdog pra batch jobs >30min.** OCR zombie 2026-04-30 (PIDs 1762/3022) ficou running 14d sem auto-clean. Solução em 3 camadas: (1) `HARD_TIMEOUT_MS` no app força `process.exit(124)` antes do limite; (2) `recordHeartbeat()` 5min UPDATE `last_heartbeat_at` (permitido em status non-terminal, trigger não bloqueia); (3) `ocr-watchdog.sh` no canary 15min identifica stale rows (heartbeat NULL ou >20min) + PID liveness + identity check via `/proc/<pid>/cmdline` + SIGTERM grace 5s → SIGKILL → UPDATE crashed.
- **NÃO FAZEMOS:** (a) confiar em parse heurístico sem env override — usar `'unknown'` é honesto; (b) DELETE em `ops_audit` "pra limpar disk" — trigger bloqueia silencioso, `snapshot_path` órfão é trade-off aceito; (c) snapshot via `sqlite3` CLI standalone — perde `vec_chunks_*` tables; (d) batch job sem heartbeat se duração esperada >30min.
- **Validação contínua:** `/api/health.opsAudit.byDbSource` expõe breakdown por agente (atlas/boris/cipher/forge/lex/nox/main/unknown). Se `unknown` count > 0 em qualquer hora pós-2026-05-15, investigar invocação sem env.
- *Origem:* sessão 2026-05-15. Spec completo: `plans/2026-05-15-op-audit-gaps-review.md`. Schema migration v17 aplicada via `migrate-v17-ops-audit.ts`. Forge code-owner sign-off Q1-Q11. Cross-link: `docs/ROADMAP.md` F17.

### 2026-05-16 — E05b verdict HOLD + golden set é o knob real

#### D35 — E05b KEEP-SHADOW indefinido até golden set expansion (n≥30)
- **Decisão:** Round 2 (pesos cortados pela metade) **mantido em SHADOW indefinidamente** até golden set chegar a n≥30 (pré-req E14, semana 20-23/05). Sem tunar pesos. Sem rodar mais kg-extract focado pra atacar regressões pontuais.
- **Evidência empírica (gate review re-executado 2026-05-16):**
  - Round 1: cross-agent Δ=-0.0506 ❌ (causa: gold chunks `shared/agent-{expertise,map}.md` com 0 KG relations; non-gold competidores com 5-24 relations)
  - Intervenção: kg-extract focado --limit 100 (cursor 112421→112556 inclui os 16 chunks gold). +538 relations, +305 entities. 3min44s, ~$0.04 Gemini.
  - Round 2 (post-kg-extract): cross-agent **+0.0765 ✅** (resolveu) mas procedure **-0.0503 ❌** (qid=52 "como rodar nox-mem reindex com segurança" caiu 1.0→0.63 sozinha; carrega -37pp dos -50pp da categoria)
  - Padrão: **regression-to-mean com n=4-9 por categoria**. kg-extract MOVE qual categoria regride, não resolve.
- **Diagnóstico arquitetural:** o problema não é `reason_boost` nem pesos — é **falta de poder estatístico no golden set**. 1 query oscilando desloca média 5-20pp. Continuar tunando E05b sem n≥30 é otimização de ruído.
- **Próxima decisão (auto-trigger semana 27/05):** Re-rodar gate review com golden set expandido. Matriz:
  - Gate passa todos critérios verdes → **ACTIVATE**
  - Gate falha mas distribuição uniforme (sem 1 query carregando) → **SHADOW Round 3** com tuning informado
  - Gate falha com mesmo padrão regression-to-mean (1-2 queries carregam) → **CUT** (E14 multi-alavanca substitui)
- **NÃO FAZEMOS:** (a) tunar pesos antes de medir com n≥30 — é otimização de ruído; (b) rodar mais kg-extract focado pra "atacar" categoria que regrediu — efeito ricochet; (c) ACTIVATE com sample atual — risco de regressões reais escondidas.
- **Side-effect positivo:** 538 relations + 305 entities permanentes no DB. KG coverage 4.92% → ~5.5%. Trabalho não desperdiçado.
- **Side-fixes (mesma sessão):** (a) script `gate-review-e05b-e13.sh` faltava bit executável (cron 13/05 silent-failed `Permission denied` mascarado por `2>&1`); (b) bug parser `json_object(...) GROUP BY` → `json_group_object(...)`; (c) trap `on_error` envia Discord webhook se exit≠0 (previne silent-fail futuro).
- *Origem:* sessão 2026-05-16 manhã. Cross-link: `specs/2026-05-06-E05b-reason-ranking-boost.md` §Gate review history. Discovery: análise forense qid-by-qid em cross-agent (n=4) — diagnóstico via JOIN `kg_relations` em `evidence_chunk_id`.

#### D36 — E04a/E04b A7 focus topic boost CUT (consumer absent)
- **Decisão:** A7 focus topic boost **CUT permanente** após 14 dias zumbi em shadow. Removido código (`src/lib/focus.ts` 266 LOC), tests (`focus.test.ts` 253 LOC), CLI subcommands (`focus set/get/clear` ~41 lines), integration em `search.ts`, env vars `NOX_FOCUS_*` (5), state dir `tools/nox-mem/focus/`. VPS commit `128b7065`.
- **Evidência empírica:** 0 logs em prod últimos 7d. Focus state persistido `topic="schema v11 edge typing"` setado 2026-05-02, expirado 2026-05-09 sem ninguém ter usado. Nenhum agente Discord exercita workflow `focus set <topic>` manual. Pre-existing test fails (75) confirmados unchanged via `git stash` check antes/depois do CUT.
- **Diagnóstico arquitetural:** design pressupõe UX que não existe na prática. Toto pula entre tópicos rapidamente, não seta focus manual antes de cada query. **Feature sem workflow real.**
- **Substituição arquitetural:** E14 multi-alavanca (A2 + D + E-lite-2, início 20/05) ataca cross-language recall (problema que A7 tentava resolver tangencialmente) por path mais robusto, sem requerer UX manual.
- **Lição transversal:** **não ship feature sem definir consumer + workflow real PRIMEIRO.** Mesma classe de erro de A6 (E03a SPO injection, HOLD por consumer absent em D37 abaixo) e graph-memory zumbi 4 dias (`feedback_validate_features_with_db_not_logs`). Próxima feature de ranking/injection deve ter consumer identificado antes do impl.
- **NÃO FAZEMOS:** (a) reabrir A7 sem workflow real validado por uso prod ≥30d; (b) shipar feature similar (boost manual setado por usuário) sem PoC de consumer real; (c) confundir "código funciona em test" com "feature útil em prod" — telemetria DB era zero apesar de tests verdes.
- *Origem:* sessão 2026-05-16. Cross-link: `specs/2026-05-02-E04a-focus-boost.md` → status CUT, `docs/ROADMAP.md` E04 row, memory `feedback_validate_features_with_db_not_logs`.

#### D38 — E05b CUT por bias arquitetural (após re-gate com n=80)
- **Decisão:** E05b reason-aware ranking boost **CUT permanente** após 3 sessões consecutivas de gate review com mesmo diagnóstico. Removido `src/lib/reason-boost.ts` (266 LOC) + tests (252 LOC) + integração em `search.ts` + env vars `NOX_REASON_BOOST_*`. Schema cols `search_telemetry.reason_boost_*` mantidos (append-only) hardcoded 0/'off'. VPS commit `26640d16`. **D35 superseded** (KEEP-SHADOW indefinido → CUT).
- **Evidência empírica (3 rounds):**
  - **Round 1 (06/05 preview):** KEEP-SHADOW — boost regredia 4/6 categorias. Pesos cortados pela metade → Round 2.
  - **Round 2 (16/05 com n=65):** cross-agent Δ=-0.0506 ❌. Forense: 1 query (qid=76 "Atlas/Boris comunicam") carrega -20pp. Gold chunks `shared/agent-{expertise,map}.md` com 0 KG relations vs non-gold com 5-24 relations. **Intervenção:** kg-extract focado --limit 100 (+538 relations). Re-run: cross-agent +0.0765 ✅ mas procedure -0.0503 ❌ (qid=52 carrega -37pp).
  - **Round 3 (17/05 com n=80):** golden set expansion 65→80 testou hipótese "regression-to-mean por sample pequeno". REFUTADA: procedure (n=9 inalterado) regrediu EXATAMENTE -0.0502. Forense procedure: mesma situação — gold sem KG coverage, displacer (chunk 112196 "snippet de comandos") com 3 depends_on triviais sobre "query"/"PATH"/"N". Cross-agent flipou +0.0765→-0.0403 (sinal que ganho ontem era bias circular do kg-extract focado).
- **Diagnóstico arquitetural final:** `reason_boost` amplifica chunks com KG coverage **independente de qualidade dos reasons**. Não é variância, não é peso, não é categoria. Cada intervenção (tunar pesos, kg-extract focado, expansion do golden set) move o problema entre categorias. **3 sessões = 3 confirmações do mesmo padrão.**
- **Substituição arquitetural:** E14 (start 20/05, 3 dias) ataca o mesmo problema (recall em queries weak-lexical, cross-language) via path arquitetural:
  - `fts_anchor` regex bilíngue (E-lite-2)
  - Pool dense ampliado 50→100-150 (A2)
  - RRF language-aware weights (D)
  - **Sem dependência de KG quality.**
- **Smoke test pós-CUT:** mesma query qid=52 ("como rodar nox-mem reindex") agora retorna gold (FAQ 116800) em pos #1 — sem reason_boost atrapalhando. SPO injection E03b (active) continua funcionando.
- **Side-effect positivo permanente:** 538 relations + 305 entities do kg-extract focado de 16/05 ficam no DB. São consumidos por SPO injection E03b (ACTIVE) + E14 futuro + outros consumers.
- **NÃO FAZEMOS:** (a) re-introduzir reason_boost sem garantir qualidade upstream dos reasons (extração com filtros); (b) ship feature que AMPLIFICA sinal sem garantir qualidade do sinal — princípio geral; (c) confundir "feature funciona em test" com "feature melhora produto" — 3 gates confirmaram regression real.
- **Lição transversal D38:** **reason quality > reason quantity**. KG extraction produz relations triviais sobre fragmentos de código (`"query"`, `"PATH"`) com mesmo peso semântico que relations sobre conceitos. Boost amplifica indiscriminadamente. Próxima feature de boost deve incluir gate de qualidade no signal upstream.
- *Origem:* sessão 2026-05-17 manhã (após 2 sessões prévias 06/05 + 16/05). Cross-link: `specs/2026-05-06-E05b-reason-ranking-boost.md` §Gate review history (3 rounds documented), VPS commit `26640d16`. D35 superseded.

#### D37 — E03b A6 SPO injection HOLD por consumer absent (~~SUPERSEDED 2026-05-17~~ — task #18 fechada: CLI integration → ACTIVATE)
**SUPERSEDED 2026-05-17:** Task #18 integrou `getVaultFacts()` em `nox-mem search` CLI com flag `--no-vault-facts` opt-out (default ON). Mode shadow→active. Smoke OK: query "Boris LinkedIn Daily Byte" → 4 entities, 7 triples, 91 tokens block surfaced. CLI exercitado por Toto manual + scripts. VPS commit `90fa3180`. Consumer absent resolvido. Mantido aqui pra histórico — original entry abaixo:

- **Decisão:** A6 SPO injection **KEEP-SHADOW bloqueado por consumer absent** — não ACTIVATE, não CUT. Código permanece em prod (`src/lib/spo-injection.ts` 220 LOC + tests). Gate ACTIVATE liberado apenas após ≥1 consumer real exercitar `/api/search` ou caminho equivalente com queries entity-rich e validar utilidade subjetiva.
- **Evidência empírica:** 336 logs shadow últimos 7d, **100% do canary semantic** (query genérica health check "memória persistente knowledge graph", todos `entities=0 triples=0 tokens=0`). Apenas 4 queries distintas no período (canary + "test" + 2 manuais que eu rodei agora durante gate review). Quando exercitado funciona: "o que faz o Boris" → 2 entities/7 triples/82 tokens.
- **Diferenciação vs A7:** SPO injection tem hipótese de valor mais sólida (entities → triples → contexto pro agente é signal arquitetural), e código está estruturalmente correto. Problema é apenas integração — nenhum agente Discord usa `/api/search`, todos usam `nox-mem` CLI ou outros endpoints.
- **Pré-req ACTIVATE (task #18):** integrar `getVaultFacts()` em `nox-mem search` CLI output OU em pipeline de agente Discord OU criar novo endpoint específico que consumer use. Esforço estimado 1-2h.
- **NÃO FAZEMOS:** ACTIVATE sem evidence ≥1 consumer real. ACTIVATE "técnico" (que muda envelope mas ninguém lê) é cosmético sem valor.
- *Origem:* sessão 2026-05-16. Cross-link: `specs/2026-05-01-E03a-spo-injection.md`, task #18 (integração).

### 2026-05-18 noite — Q4 gate threshold + Phase 2 GTM open (D43)

#### D43 — Q4 gate: ≥+15% nDCG@10 + 2-tier scale-up

**Context:** Q1 LoCoMo hybrid Python re-implementation entregou **+18.8% nDCG@10** vs E04 FTS5-only baseline (n=100 stratified seed=42, validated 2026-05-18 19:16 BRT). Q4 gate pra GTM Phase 2 ("COMPARISON winning") nunca tinha threshold formal — bloqueava decisão de "open Phase 2 now?".

**Decisão:** Threshold = **≥+15% nDCG@10 (rel)**, current **+18.8% MEETS**. Phase 2 GTM **ABRE HOJE** (2026-05-18 noite) com claim "+18.8% nDCG@10 measured" + caveat de Python re-implementation. **MAS scale-up condicional a production-path Q1 (in flight tonight) confirmar ≥+15% no código TS prod** (não Python re-impl).

**Rationale (5 bullets):**
- Hybrid retrieval papers SOTA (BEIR, MTEB) reportam +10-25% gain sobre BM25-only → +15% é threshold defensável + sólido
- +18.8% é número reproduzível (mesmo seed=42 do E04 baseline, mesmo subset, mesmo método de scoring)
- Marketing copy clean: "*Hybrid retrieval (FTS5 + Gemini 3072d + RRF) improves nDCG@10 by 18.8% over FTS5-only baseline on LoCoMo n=100. Verified 2026-05-18.*"
- Threshold C (≥+20% AND competitor beat) exigia 2 trabalhos pesados antes de Phase 2: production-path Q1 confirmar + benchmark vs competitor com métrica comparável (agentmemory reporta R@5, não nDCG — apples-to-oranges) — atraso desnecessário
- 2-tier preserva commitment estratégico: ABRE com claim atual, ESCALA com confirmação prod

**Alternativas rejeitadas:**
- A (qualquer improvement) — fraco, não sobrevive review scrutiny
- C (≥+20% AND competitor beat) — perfect-enemy-of-good, +1-2 semanas delay
- D (≥+30%) — irrealista pra single retrieval improvement, "breakthrough" claim hyped

**Implicação operacional:**
- **Phase 2 GTM workstreams (pricing, demo video, landing page) podem iniciar imediatamente**
- README.md + docs/COMPARISON.md já refletem "+18.8% verified 2026-05-18" (PR #110)
- Production-path Q1 (rodando 2026-05-18 ~22:00 BRT, ETA ~22:15) é o gate pra Phase 2 SCALE-UP — se reproduzir +15-22%, scale-up greenlight; se vier <+15%, pausa scale-up + investiga implementation diff
- Per-category temporal -1.2% NÃO é blocker (agent stat-power analysis em PR #113 refutou como statistically NULL, n=20)

**Cross-ref:** `paper/publication/results/locomo-hybrid-vs-fts5-summary.md` (Q1 numbers), `paper/publication/results/q1-temporal-regression-analysis.md` (D43 dependency cleared), `docs/VISION.md` v14 §Phase 2 trigger, `paper/publication/baselines/locomo_production_path.md` (Option A runbook — scale-up gate).

---

### 2026-05-18 noite — 4 Metis pricing prerequisites resolved (D44)

#### D44 — Pricing strategy prerequisites: scope, Hotmart, data posture

**Context:** Metis pre-planning agent (2026-05-18 noite) recusou rodar pricing-recommendations work até resolver 4 prerequisitos estratégicos (saved em `memory/project_pricing_prerequisites_2026_05_18.md`). Resolvidos hoje:

**D44a — Scope: pricing strategy migra pra `nox-supermem/` quando ativo**
- Por ora, `docs/gtm/PRICING-STRATEGY.md` fica em `memoria-nox/` (precedente, evita migration churn)
- Header explícito "This will migrate to nox-supermem/ when that repo is active" adicionado ao topo do doc na próxima edit
- Cross-link ao `~/Claude/Projetos/memoria-nox/CLAUDE.md` regra escopo

**D44b — Pivot pra Stripe-first (Toto decision 2026-05-18 noite)**
- Toto: "Não vou usar Hotmart agora" (rejected options A + B)
- Consequências derivadas:
  - **P5 (BRL vs USD default):** USD default em Stripe Checkout (multi-currency suportado, mas USD é o natural target pra dev tools/devs internacionais)
  - **P6 (trial sem cartão vs sandbox):** Trial via Stripe Checkout built-in (14d free trial nativo, cancela auto se não converter)
  - **P7 (afiliados Hotmart):** REJECTED — Stripe não tem programa nativo de afiliados como Hotmart. Defer pra Tier 3 OR partnership ad-hoc futuro
- **§9 "Contexto Hotmart e Mercado BR" em PRICING-STRATEGY.md DEVE ser reescrita** pra refletir Stripe-first context (próxima sessão de pricing)
- Implicação fiscal/cambial: USD revenue + custo USD (Gemini, VPS) = natural hedge. BR market pricing fica como secondary tier (BRL via Stripe Brazil OR via PIX integration futuro)

**D44c — Data posture markers (universal convention)**
- Todo número em docs estratégicos DEVE ter um destes markers:
  - `[verified YYYY-MM-DD <source>]` — measured, fonte ref
  - `[estimated]` — projeção, sem measurement
  - `[ASSUMPTION]` — input externo não-validado (ex: Hotmart fee ~10%)
- Aplicado retroativamente em `docs/COMPARISON.md` (PR #110 + #114)
- Próximos PRs estratégicos auto-honor

**D44d — Q4 gate timing:** RESOLVIDO em D43 (Phase 2 abre hoje)

**Rationale:**
- TODOS os 4 prerequisites Metis resolved (a/b/c/d) — pricing-recommendations agent pode rodar sem bloqueio
- D44c em particular é hard rule pra paper §5 + GTM materials (review safety)
- D44b pivot (Stripe-first) muda o tom global da PRICING-STRATEGY.md — não é mais "BR-first via Hotmart afiliados" mas "global SaaS via Stripe" + Brazil secondary tier

**Implicação operacional:**
- **Spawn pricing-recommendations agent na próxima sessão** com guardrails: USD default, Stripe Checkout, NO afiliados, NO Hotmart references except como "rejected alt" historical context
- **Reescrever PRICING-STRATEGY.md §9** ("Contexto Hotmart e Mercado BR") pra "Contexto Stripe-first + Brazil secondary tier" — preserva análise mercado BR mas pivota infra
- Próximo PR estratégico (qualquer doc) DEVE seguir D44c markers — auto-grep CI rule a considerar futuro
- `memory/project_pricing_prerequisites_2026_05_18.md` atualizada com status "RESOLVED 2026-05-18 (a=migrate-later, b=Stripe-first, c=universal markers, d=Phase 2 open per D43)"

**Cross-ref:** `memory/project_pricing_prerequisites_2026_05_18.md`, `docs/gtm/PRICING-STRATEGY.md`, `~/Claude/Projetos/memoria-nox/CLAUDE.md` §escopo, `docs/COMPARISON.md` (verified markers exemplo).

---

### 2026-05-18 noite — Slogan update: pain-weighted leading (D45)

#### D45 — Pain-weighted leading position in slogan

**Context:** D40 locked tagline "Hybrid memory with shadow discipline — yours by design" (2026-05-17 noite). Toto challenged tonight (2026-05-18 noite final): "hybrid" é genérico (todo RAG moderno é hybrid), enquanto **pain weighting** é a primary novelty claim do paper §1.1 contributions: "(1) a pain-weighted salience formula (recency × pain × importance) that explicitly models incident severity as a retrieval signal—novel in the RAG/memory literature".

**Decisão:** Pivot tagline pra **"Pain-weighted hybrid memory with shadow discipline — yours by design."**

**Rationale:**
- Pain weighting = paper's primary novelty (paper-draft-sec1-3.md §1.1 + RESUMO-EXECUTIVO).
- "Hybrid memory" sozinho é descritivo, não diferenciador — mem0/agentmemory/memanto todos são hybrid também.
- "Pain-weighted" faz o leitor parar 1 segundo (curiosity hook).
- Slogan original mantido como subset (hybrid + shadow + yours by design preservados).
- Trade-off aceito: tagline ficou 8 palavras (vs 6 antes) — mais mouthful mas inclui paper novelty.

**Implicação:** atualização propagada em README.md (H1, banner alt), docs/VISION.md, docs/HANDOFF.md, docs/ROADMAP.md, CLAUDE.md, CONTRIBUTING.md, SECURITY.md, CHANGELOG.md, docs/DECISIONS.md (este), docs/COMPETITIVE-POSITIONING.md, docs/marketing/*, docs/gtm/*, docs-site/*, specs/*, staged-*/. Banner SVGs (separate PR — design agents). Stat-cards SVGs preservam (não mencionam slogan).

**D40 status:** superseded — slogan D40 era prefix; D45 adiciona "Pain-weighted" prefix.

**Cross-ref:** paper-draft-sec1-3.md §1.1 (paper claim), paper RESUMO-EXECUTIVO.md (novelty axes), banner redesign PR (visual), D44b Stripe-first (orthogonal but tonight cluster).

---

### 2026-05-18 noite — Threat-model iteração recursiva + cadência quarterly (D42)

#### D42 — Threat-model iteração recursiva: adotar cadência trimestral de security audit

**Context:** Wave E entregou THREAT-MODEL.md inicial (PR #55) cobrindo A1/A2/A3 + endpoints Wave B. Wave F (PR #58) analisou os módulos pendentes (P5/L2/P2/A2) — sparse-checkout artifact havia excluído essas seções da Wave E — e encontrou **7 novos gaps** (G11–G17), sendo 2 HIGH. Wave G (PR #66) fechou todos os 7 em 1 PR.

**Decisão:** Adotar **cadência trimestral de security audit** como prática standing. Cada audit irá provavelmente revelar novos gaps à medida que a superfície de código cresce.

**Rationale:**
- Wave E perdeu P5/L2/P2/A2 por artifact de sparse-checkout — não falha de método, mas de scope
- Mesmo após fix, nova superfície (Wave B/C) criou novos vetores de ataque
- Security work não tem estado "done" — é iterativo por natureza
- Cadência previne acúmulo de long-tail risk que aparece só em produção
- Padrão estabelecido na sessão de 2026-04-29 (`feedback_audit_critical_modules_same_session`): audit na mesma sessão expõe issues que apareceriam semanas depois

**Alternativas rejeitadas:**
- "Audit once before launch" — pressupõe superfície de código estática, contradiz velocidade do roadmap
- "Audit only when bug found" — reativo, permite acúmulo; Wave G provou que proativo é mais barato
- "Audit a cada PR grande" — overhead too high; trimestral balanceia custo × cobertura

**Implicação operacional:**
- Próximo audit Q3 2026 (aproximadamente Wave M ou equivalente)
- `docs/THREAT-MODEL.md` vira living doc; versão tagueada por audit (v1.0 Wave E, v1.1 Wave F)
- Cross-link ao ROADMAP — todo ranking change ou op destrutiva passa por threat review antes de merge
- Formato: parallel agents analisam módulos por pillar (Q/A/P/Lab) para cobrir toda superfície

**Cross-ref:** memories `feedback_audit_critical_modules_same_session` + `feedback_audit_must_check_prod_state_not_only_code`, `docs/THREAT-MODEL.md` v1.1, PR #55 (Wave E) + PR #58 (Wave F) + PR #66 (Wave G).

---

### 2026-05-18 madrugada — Q/A/P cross-cutting decisions resolved (D41)

**Decisão:** Toto resolveu 5 cross-cutting questions levantadas pelo `docs/MORNING-REVIEW-2026-05-18.md` antes de fechar overnight 2026-05-17 noite.

1. **P1 default Gemini model: `gemini-2.5-flash-lite` (NOT flash)**
   - Razão: "tem que ser barato e bom" — Toto priorizou custo
   - Toggle pra `gemini-2.5-flash` post-Q1 SE quality issue empírico aparecer
   - PR #3 spec §9 deve refletir: lite default, flash como opção via `--model` flag
   - Aplicar durante implementation P1 (não pre-merge edit no branch do PR)

2. **A2 encryption default: opt-out (encrypt by default)**
   - Razão: A2 é keystone Autonomy pillar; encrypted-by-default sinaliza "data é sua, protegida por default"
   - Plaintext via `--unencrypted` flag para edge cases (backup pra mídia confiável)
   - PR #9 spec §3 deve reframe: default behavior = encrypted (AES-256-GCM + scrypt KDF), `--unencrypted` é opt-out explícito
   - Aplicar durante implementation A2

3. **GTM brand color palette: D (minimal — mono + 1 accent)**
   - Razão: Moat é lean ("your data, your choice") → visual minimalista combina, não compete com conteúdo
   - Accent color: `#00C896` (success green) picked pelo asset production agent — works on dark + light, semantic fit "data is healthy", unclaimed in this space (memanto + agentmemory both orange/amber)
   - PR #16 spec §2 deve lock D minimal + #00C896 accent
   - Asset production (banner + 6 stat SVGs + logo) DONE em PR #19 — pronto para gate Q4

4. **L3 confidence gate threshold: ≥1.0pp absolute lift (KEPT)**
   - Razão: 1.0pp é honest bar; menos arrisca complexity for marginal gain
   - Se eval <1pp, schema ships sozinho (v19), ranking integration aguarda L3.2 (iteração separada)
   - PR #15 spec §6 unchanged

5. **Implementation sprint order: P1 (answer) → A2 (export, parallel se capacity) → P2 (hooks) → P4 (connect IDE)**
   - Razão: P1 = highest user impact, unblocks P2-P5 mental model; A2 = backend-heavy paralelo OK; P2 depende P1; P4 depende P2 hooks
   - Aplicar quando PRs #2-#16 forem merged ou após VPS sync
   - Implementation kickoff issues criados pelos agents prep nesta madrugada: P1 (PR #18), A2 (PR #17), P2 (in progress), A3 (in progress), P4 (in progress)

**Implicação operacional:**
- PR comments informativos adicionados em #3, #9, #15, #16
- GTM asset production COMPLETE (PR #19, 20 files, palette D + accent #00C896)
- Implementation prep COMPLETE pra P1 (PR #18) + A2 (PR #17)
- A4 completion COMPLETE (PR #20, all 8 checks runnable in CI, no VPS dependency)
- VISION.md v15 written (branch ready, PR pending)
- Q4 COMPARISON harness em curso (async)
- P2 + A3 + P4 implementation kickoffs em curso (async)
- README-DRAFT.md em curso (async, locked behind Q4 gate but draft ready)

**Origem:** Toto morning review 2026-05-18 ~06:00 BRT em resposta ao `docs/MORNING-REVIEW-2026-05-18.md`.

**Ver também:**
- `docs/MORNING-REVIEW-2026-05-18.md` (playbook que levantou as 5 questions)
- `docs/_archive/ROADMAP-v1-pre-Q-A-P-2026-05-17.md` (pré-pivot)
- D40 (Q/A/P pivot que estabeleceu o framework)
- PR #17, #18, #19, #20 (artifacts deste D41)

---

### 2026-05-17 noite — Q/A/P strategic pivot pós-análise memanto + agentmemory (D40)

**Decisão:** Reorganizar roadmap em 3 pilares product-first + 1 Lab + 1 GTM phase, abandonando estrutura E-numbered focada em retrieval research interna.

**Estrutura aprovada:**
- **Q (Quality):** Q1 LoCoMo, Q2 LongMemEval, Q3 Latency, Q4 COMPARISON.md (gated)
- **A (Autonomy):** A1 privacy filter, A2 export/import, A3 provider abstraction, A4 zero-vendor validation
- **P (Product):** P1 answer primitive, P2 Claude Code hooks auto-capture, P3 temporal queries, P4 connect <ide>, P5 real-time viewer
- **Lab (40% capacity):** L1 E15 paused, L2 conflict detection (memanto-inspired), L3 confidence field (gated)
- **GTM Phase 2:** viral launch playbook, locked behind Q4 winning

**Tagline aprovada (D40):** *"Hybrid memory with shadow discipline — yours by design."* ⚠️ **Superseded by D45 (2026-05-18 noite) — pain-weighted prefix added. Ver D45.**

**Capacity split:** 60% pilares product (Q/A/P), 40% lab. Anteriormente 80/20 com lab dominante.

**Por quê:**
- Análise 2026-05-17 de competidores diretos memanto (126 stars, SaaS Moorcheh, pitch acadêmico) e rohitg00/agentmemory (11.3k stars, iii-engine runtime, produto viral) expôs gap UX/produto crítico.
- Roadmap pré-pivot tinha 80% capacity em retrieval interno (E13/E14/E15) — pesquisa boa, mas invisível externamente.
- agentmemory provou que mesmo arquitetura similar (BM25+vec+KG+RRF) ganha mercado por UX (hooks auto-capture, multi-IDE breadth, real-time viewer, marketing presentation).
- Moat real identificado: nox-mem é o único concorrente que entrega **data autonomy genuína** — SQLite file portável, sem daemon proprietário (vs agentmemory iii-engine), sem SaaS backend (vs memanto Moorcheh). É terreno defensável que diferencia simultaneamente dos dois.

**Alternativas consideradas e rejeitadas:**
1. **Continuar 80/20 retrieval research** — REJEITADO. Paper sai mas produto fica invisível. Bom pra acadêmico, ruim pra Nox-Supermem comercialização Hotmart.
2. **Pivot SaaS estilo memanto** — REJEITADO. Mata o moat de autonomia. Não escalável sem infra cara.
3. **Pivot stack-bridge genérico estilo agentmemory** — REJEITADO. 12 IDEs shallow vira PR-spam e dilui marca. Tier A premium (3 IDEs deep) + Tier B basic (passive MCP) faz mais sentido.
4. **Open-source backend pluggable em agentmemory** — REJEITADO. Vira commodity layer, perde brand.

**Implicação operacional:**
- E15 CodeGraph improvements: **PAUSADO** (não cortado) — retoma pós-Q1
- Public benchmark transparency: APROVADO mas Q4 **só publica se vencermos ou empatarmos topo**
- Gemini-only confirmed para embeddings (quality bias) — A3 abstraction permite swap mas Gemini fica default
- Tagline vai pra header de TODOS canônicos (CLAUDE.md, ROADMAP.md, paper, futuro README, Nox-Supermem landing)

**Overnight automode push 2026-05-17 noite:** 15 PRs abertos cobrindo Q1+Q2+Q3 scaffolds, A1 implementation + A2+A3+A4 specs/scaffold, P1+P2+P3+P4+P5 specs/impl, L2+L3 specs, GTM README hero spec. Todos sem auto-merge, review pendente 2026-05-18.

**Trigger pra revisitar:** Q4 gate fechado (numbers publicados) ou se em 6 meses o moat de autonomia não se materializar como diferenciador percebido pelos usuários.

**Origem:** Conversa estratégica Toto + análise repos memanto + agentmemory 2026-05-17.

**Ver também:**
- `docs/ROADMAP.md` (v2, atual)
- `docs/_archive/ROADMAP-v1-pre-Q-A-P-2026-05-17.md` (v1, arquivado)
- Memory `qap-pillars-strategic-decision`, `overnight-automode-2026-05-17`, `memanto-inspired-ideas`, `repo-visual-style-inspiration`

---

### 2026-05-17 — FTS5 silencioso é arquiteturalmente correto pra este corpus (D39)

#### D39 — FTS5 silent design accepted (após 4 tentativas de fix)
- **Decisão:** Manter FTS5 silencioso (AND-strict + sem stopword strip) como design permanente. Dense Gemini 3072d carrega 100% do recall. A1 (FTS5 pool expansion) e G (HyDE) DEFERRED PERMANENTE.
- **Evidência empírica (4 tentativas mesmo dia 2026-05-17 ~16:50-17:10):**
  - v1 (strip stopwords + OR-all): -23.6pp overall (decision -47pp catastrófico)
  - v2 (AND-first + OR-fallback, tokens quoted): -22.5pp
  - v3 (unquoted tokens AND/OR): -18.5pp
  - v4 (confidence-aware: AND=1.0, OR=0.4): -5.4pp (melhor mas ainda regride)
- **Diagnóstico arquitetural:** padrão consistente — FTS5 acordado sempre dilui ranking via RRF, independente de tuning. BM25 nesse corpus tech-mixed PT/EN não distingue bem gold de near-miss. Mesmo OR fallback com weight 0.4 introduz ruído competidor.
- **Root cause empirico:** FTS5 vanilla AND-strict zera em 96% das queries (stopwords + AND). Mas "acordar" expõe que BM25 ranking faz worse damage que silêncio + dense-only.
- **Implicações roadmap:**
  - A1 (FTS5 pool 50→200) DEFERRED PERMANENTE — sem recall, mais pool não ajuda
  - A2 (dense pool expansion) DEFERRED — também dilui (testado 2x hoje)
  - G (HyDE) DEFERRED — gate métrico inviável (96% queries triggariam = G global)
  - E-lite-2 (fts_anchor) PERMANECE ACTIVE — capturou o pouco ganho FTS disponível (+0.94pp medido)
  - D (language-aware RRF) PERMANECE ACTIVE — capturou ganho de pesos corretos (+1.92pp)
- **Próximo upside esperado:** cross-encoder reranker (D01 v3 com Cohere API, bloqueio resolvido se hardware mudar) ou features ranking novas (E07 impact-based, kg-derived signals).
- **FTS5 como failsafe latente:** se Gemini outage/quota, sistema degrada gracefully — FTS5 retorna o que AND-strict pega (geralmente pouco mas não zero pra queries com termos exatos do corpus).
- **NÃO FAZEMOS:** (a) re-tentar FTS5 query expansion sem evidência empírica nova; (b) ampliar FTS5 pool achando que vai funcionar (testado: não funciona); (c) HyDE global (custo Gemini explode); (d) confiar que "smoke positivo" = "eval positivo" — confidence v4 teve smoke OK mas eval -5pp.
- *Origem:* sessão 2026-05-17 ~16:50-17:10 BRT. Cross-link: `feedback_fts5_vanilla_and_strict_explains_zero_recall` (memory). Runs eval: 79 (D baseline 0.6797), 80-84 (4 tentativas FTS5 fix), 85 (rollback confirmado 0.6813).

---

### 2026-05-20 — Temporal retrieval path em shadow mode (D49)

#### D49 — Temporal proximity rerank ativado em shadow-mode opt-in (gated em 7 dias baseline)
- **Pergunta:** depois do spike #157 (proximity rerank + temporal intent detection) e curagem do gold Q87+Q88 (PR #159), ativar em prod ou deixar shadow?
- **Decisão:** **shadow-mode opt-in** via `NOX_TEMPORAL_PATH=1`, com 7 dias mínimos de baseline telemetry antes de qualquer switch pra active.
- **Por quê:**
  - Princípio CLAUDE.md §5 — features que afetam search/tier decisions precisam ≥1 semana baseline via `/api/health` antes de ativar
  - Gold Q87+Q88 curados hoje (PR #159) — agora 4/4 temporais com `expected_chunk_ids` válido pra medição numérica
  - Spike isolated em `staged-temporal-spike/` (não toca prod search.ts ainda) — deploy é additional, não breaking change
  - Trade-off identificado pelo spike: E13 section-boost flip e proximity rerank são **ortogonais** — 98.9% do corpus tem `section=NULL` (E13 não cobre), enquanto queries adverbial-only como Q70 ("quando o salience foi ativado") não têm anchor parseável (proximity não dispara). Nenhum path sozinho cobre 4 queries temporais — eles compõem
- **Roadmap implementação (4 fases gated):**
  - **Phase 1:** deploy spike code em `src/temporal-retrieval.ts` na VPS via novo Wave (não PR #154 retroativo). Wire em `searchHybrid` mas apenas se `NOX_TEMPORAL_PATH=1`
  - **Phase 2:** ativar shadow telemetry — `NOX_TEMPORAL_PATH=1` + log de detector hit-rate + (would-be) re-rank deltas via probe stderr JSON
  - **Phase 3:** medir Δ nDCG temporal subset (4 queries: Q70/Q71/Q87/Q88) por **7 dias** em prod com queries reais
  - **Phase 4:** D50 decisão de active/off com numbers cravados (target: ≥+10% nDCG temporal subset sem regressão em outras categorias)
- **NÃO FAZEMOS:**
  - Skip shadow window achando que spike test é suficiente (smoke ≠ eval, lesson D39)
  - Deploy via PR #154 retroactive (já merged, scope creep)
  - Ativar sem comparing baseline ablation (precisa A0 dedicated temporal)
- **Cross-links:** spike PR #157 (staged-temporal-spike), gold cure PR #159, D43/D44 (Q4 gate Phase 2 já open), memory `[[temporal-q1-spike-2026-05-20]]`.
- *Origem:* sessão 2026-05-20 ~11h-12h BRT, pós deploy Wave A novo e gold cure.
