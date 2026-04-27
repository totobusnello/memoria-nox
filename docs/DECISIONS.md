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

### OpenClaw / Claude CLI

13. **claude-cli backend zero-cost via Max OAuth** — subprocess `/usr/bin/claude` lê **só** de `.credentials.json` (NÃO env var conflitante). `chattr +i` após `setup-token`. Fallback chain SEM `anthropic/*` direto (mascara CLI failure → bill pay-per-token).
    *Origem:* `CLAUDE.md regra 5`; `feedback_openclaw_fallback_should_include_claude_cli_sonnet.md`

14. **Editar `openclaw.json` via `openclaw config set`, NÃO `jq + mv`** — gateway tem in-memory canonical state que sobrescreve edits manuais no startup.
    *Origem:* `CLAUDE.md regra 5`; `feedback_openclaw_config_set_required_for_persistence.md`

15. **`agents.defaults.cliBackends.claude-cli` NUNCA criar bloco** — OpenClaw tem backend nativo auto-carregado. Configs customizadas têm `output:"json"` + `input:"arg"` que QUEBRA o parser; built-in usa `output:"jsonl"` + `input:"stdin"`.
    *Origem:* `CLAUDE.md regra 5`

16. **OpenClaw v.24 NÃO atualizar até .25 stable** — bug #71957 (claude-cli harness race) deprecou choiceId; fix em .25-beta.4. Defesa: `oc-upgrade <version>` orchestrator com pre-flight check + auto-rollback.
    *Origem:* `feedback_openclaw_24_breaks_claude_cli_harness.md`; commit `3b9e23c`

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
  - **F10/F12/F13/F14/F16** gaps adicionados (observability dashboard, Gemini SPOF playbook, cost projection alt, DR drill trimestral, telegram rollback bot)
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
- **Implicação F09 atualizada:** DB cresceu 99% (DOBROU) pós-A1+A3+A4 (318MB → 631MB). Re-priorizar urgentemente pós-G01.
