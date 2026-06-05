# nox-mem DECISIONS LOG

> **Append-only.** Não edite entries antigas — adicione novas. Histórico de "por quê" para qualquer decisão arquitetural.
> Para "o que fazer agora" → `docs/ROADMAP.md`. Para estado atual → `docs/HANDOFF.md`. Para regras operacionais 1-15 → `CLAUDE.md`.

---

## 1. NÃO FAZEMOS — inventário consolidado

**Adicionados 2026-06-04 (Session Priming Loop):**
- **P2 full autocapture (~170 eventos/sessão) — GATED, não fazemos agora.** 3 razões: contradiz decisão de review Q3 (só digest, qualidade>volume, prompts crus fora); custo de embedding material (prepaid Gemini esgotou 2026-06-04 com bulk de 34k chunks); claude-mem já captura o Mac em alta resolução e o feeder entrega curado. **Critério de reabertura objetivo:** crystallize mostrando promotes de `events/` + brief melhorando por causa deles em 2-4 semanas de observação.
- **Brief NÃO incrementa `access_count`** — serving vai pra `brief_log` própria; o sinal orgânico fica 100% puro pro audit de high-pain órfãos (73% nunca acessados, medido 2026-06-04).
- **Tabela `agent_events` (P2 §6) não criada** — digest 1/sessão vai direto pra `chunks` como type=daily/90d; agent_events só se P2 full reabrir.

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
| 29 | **Buscar match com mem0 no cap@500 via ingest-side concentration** (chunk summarizer, query rewrite, ou expansão+rerank no query path) | 3 caminhos independentes falharam: PR #337 query rewrite Gemini Flash Lite (−11.8%), PR #339 E+F+H combo KG+RRF+top-k expansion (NEUTRAL +2.4%, gap persiste), PR #341 A2 chunk summarizer (−34% full corpus / −69% gap@500). mem0's cap@500 advantage é **structural** (extracted-fact concentration sobre 500 facts extraídos LLM-side, NÃO 500 raw turns) — não replicável dentro da arquitetura hybrid sem trocar mecanismo de ingest. Custo total dos 3 experimentos: $0.30 Gemini + ~14h compute. | Lab Q1 "hybrid-of-hybrids" router (index both raw + summarized, route by intent) com nDCG@10 + coverage two-metric gate | D59 — 2026-05-24 |

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

**2026-06-04 (Session Priming day):**
- **Watcher de ingest SEM allowlist ingere lixo** — `_retired/` inteiro (5.6k chunks) entrou via inotifywait sem exclusões; guard case/esac no loop (`--exclude`/`--include` do inotifywait são mutuamente exclusivos). DELETE de limpeza em chunks NÃO roda no sqlite3 CLI (`no such module: vec0`) — usar better-sqlite3 + sqliteVec.load.
- **429 Gemini "prepayment depleted" é por PROJETO** — key nova não recarrega saldo; testar key direto no endpoint Google isola billing de bug em 1 comando. Key formato `AQ.` autentica via `?key=`/`x-goog-api-key`, não Bearer.
- **Disciplina "esperar dados" é pra SCORING de search (regra #5)** — defeito objetivo em camada de seleção/apresentação (near-dups, união de pools) itera no mesmo dia. Brief v1.2 shipped horas após o gate F3.
- **Gates humanos pagam:** "por que 69k?" → corpus pollution descoberta; "pergunta ao Nox" → agent main sem brief (PR#6) + 2 defeitos de conteúdo (v1.2).

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

---

### 2026-05-21 — G10d Conditional Hard Mutex ACTIVE-T2 deployed (D51)

#### D51 — Conditional Hard Mutex section↔source_type, threshold=2 ativo em prod
- **Pergunta:** após G10 Hard Mutex (PR #182) validado +0.79% nDCG / +2.65% MRR aggregate mas single-hop +8.22% / multi-hop −3.95% / adversarial −2.95%, vale gate mutex por query_entities count pra recuperar multi-hop sem perder o ganho aggregate?
- **Decisão:** **ACTIVE-T2** — deploy Conditional Hard Mutex gated por `query_entities ≤ 2`. Mutex aplicado quando count ≤ 2; bypass quando count ≥ 3 (multi-entity queries preservam chain signal entity::compiled).
- **Por quê:**
  - 4-config ablation grid (A8'/A8d-1/A8d-2/A8 off) contra `g9.db` (69 495 chunks) n=100 mostrou: threshold=1 regrediu (entity inventory 15 612 = 40× spec estimate → quase toda query bate count≥1 → no conditional benefit); threshold=2 cravou WIN
  - Aggregate threshold=2: **+1.35% nDCG@10 / +1.37% MRR** vs A8' baseline
  - Per-category recovery: multi-hop **+1.58%** nDCG (recovery +5.53pp vs G10), adversarial **+3.04%** nDCG / +6.25% MRR (recovery +5.99pp), open-domain +2.92% (preserves G10b win)
  - Single-hop trade-off: −3.26% vs A8' MAS **+3.31% vs pre-mutex baseline** — sacrifício aceitável dado aggregate net positive + multi-hop/adversarial massive recovery
  - 6/8 D51 criteria met (single-hop nDCG/MRR são únicos FAILs, mas vs A8' pico não pre-mutex baseline)
- **Deploy procedure executed 2026-05-21 ~15h10 BRT:**
  - SCP `query-entity-count.ts` + `search.ts` pra VPS `/root/.openclaw/workspace/tools/nox-mem/src/`
  - systemd drop-in `/etc/systemd/system/nox-mem-api.service.d/g10d-active-t2.conf` com `Environment="NOX_MUTEX_QUERY_ENTITY_THRESHOLD=2"`
  - Restart nox-mem-api → active
  - Smoke test 3/3 PASS: single-entity (`Toto Busnello CEO`) → mutex applied; multi-entity (`Toto Galapagos Capital Fundo Lombardia`) → mutex DISABLED returning entity::compiled top1; no-entity (`what is hybrid memory search`) → no mutex
- **Rollback paths (3-tier documented):**
  1. (5min) `NOX_DISABLE_CONDITIONAL_MUTEX=1` — disable conditional layer, keep G10 hard mutex
  2. (5min) `NOX_DISABLE_MUTEX_SECTION_SOURCE_TYPE=1` — disable entire mutex (pre-PR #182)
  3. Remove drop-in completely
- **NÃO FAZEMOS:**
  - Skip ablation pre-deploy (CLAUDE.md §5 shadow discipline)
  - Threshold=1 ignorando entity density real (production tem 15 612 entities, spec era 402)
  - Trade-off single-hop FAIL como blocker quando aggregate é positive e adversarial/multi-hop recovery massive
- **Cross-links:** PR #198 (G10d code) + PR #203 (ablation execution) + PR #208 (paper §5.5 addendum fourth triangulation point), spec `specs/2026-05-21-G10d-conditional-mutex-by-query-entities.md`, template `specs/d51-template.md`, audit `audits/2026-05-21-G10d-ablation-execution.md`, memory `[[g10d-ablation-d51-verdict-active-t2]]` + `[[g10d-active-t2-deployed-2026-05-21]]`.
- *Origem:* sessão 2026-05-21 ablation cycle pós G10b/G10c (per-category mutex + per-style mutex). D48 saga (G3 → G11 → **G10d**) CLOSED com canonical boost stack: section_boost + source_type_boost + Hard Mutex gated em query_entity_count ≤ 2 + salience v2 additive.

---

### 2026-05-21 — L4 DIR_PATTERN aceita plural filesystem forms (D52)

#### D52 — `regex-extract.ts` normaliza plural filesystem dirs → singular canonical entity types
- **Pergunta:** descobriu durante PR #210 cleanup que `kg_entities.entity_type` usa singular (16 types: feedback/person/agent/...) enquanto `memory/entities/` filesystem usa plural (5 dirs: agents/decisions/lessons/projects/systems/). Wikilink `[[agents/nox]]` mirrorando filesystem layout não matchava — silenciosamente dropava. Como bridge?
- **Decisão:** Extend `DIR_PATTERN` regex pra aceitar ambas formas; `asEntityType()` normaliza plural → singular antes de armazenar. `EntityRef.entityType` e `key` sempre singular canonical (matches DB FK).
- **Por quê:**
  - Discovery durante cleanup PR #210 (audit PR #211 confirmou `kg_relations.extraction_method` NULL em 21 518 rows — L4 nunca rodou em prod até hoje, KG cron roda só domingos)
  - Forçar uma única convenção (singular ou plural) é breaking change pra qualquer agente que escrevesse memory files (filesystem ALREADY plural)
  - Aceitar ambas formas com normalisation é 100% backward-compatible — singular continua matching, plural agora também
  - Operationally: L4 fire primeira vez 2026-05-24 Sunday cron — esta PR ship em tempo
- **Implementation:**
  - Add `NOX_ENTITY_DIRS_PLURAL` constant (5 dirs)
  - Add `PLURAL_TO_SINGULAR` map: `agents→agent, decisions→decision, lessons→lesson, projects→project, systems→system`
  - Add `system` 17th canonical type em `NOX_ENTITY_TYPES` (was 16) — needed pra canonicalise `systems/` filesystem dir
  - `DIR_PATTERN = (?:feedback|person|...|agents|decisions|...|systems)`
  - 10 new test cases (8 plural variants + 2 `system` canonical), 57/57 passing
- **NÃO FAZEMOS:**
  - Quebrar singular convention existente (breaking change)
  - Add novos tipos sem evidência filesystem (avoid bloating DIR_PATTERN com types phantom)
  - Backfill retroativo de rows pré-PR — forward-only per spec §9
  - Mass-rename memory entity files de plural pra singular (filesystem stays plural, regex adapts)
- **Spec amendment pending:** `specs/2026-05-18-L4-regex-first-extraction.md` §4 originalmente listava 16 singular types. Follow-up doc PR atualizará pra documentar normalisation rule explicitly.
- **Cross-links:** PR #210 (cleanup que surfou divergence), PR #211 (audit doc + 2026-05-24 watchpoint), PR #214 (this decision impl), memory `[[late-evening-2026-05-21-f10b-deployed-l4-plural]]`.
- *Origem:* sessão 2026-05-21 late evening pós F10 Phase B deploy. Toto "tocaa pau" → adiantar pendentes follow-ups.

---

### 2026-05-21 — F10 Phase A + Phase B deployed (Foundation observability) (D53)

#### D53 — F10 observability dashboard Phase A + Phase B ambos LIVE em prod
- **Pergunta:** F10 spec (2026-05-01, refresh 2026-05-21) previa rollout phased 4 fases (~24h total). Ship só Phase A standalone (4h) ou push até Phase B (Eval Dashboard, +6h)?
- **Decisão:** **Ambas Phase A + Phase B deployed mesmo dia** — F10 ficou completamente functional pra "está OK agora" (Phase A) e "score over time per config" (Phase B) numa janela só.
- **Por quê:**
  - Phase A standalone ~4h: 3 endpoints (`health` + `recent-ops` + `canary-tail`) + static dashboard `health.html`, polling 30s
  - Phase B (~6h, agent worktree paralelo): endpoint `/api/observability/evals` reading `audits/data-G*/` + static `evals.html` com Chart.js line charts + gate annotations
  - Lean stack mantido: vanilla JS + Chart.js CDN, no Next.js/Vercel/Prometheus/Grafana
  - Phase A smoke 6/6 PASS, Phase B smoke 5/5 PASS no VPS
  - 2 fixes operacionais cravados deploy-time: (1) `handleObsEvals(query, opts)` é dois args separados não merged object (agent wire-up doc estava ambíguo); (2) `auditsRoot` default `cwd/../audits` resolve `tools/audits` no VPS = wrong → explicit `${OPENCLAW_WORKSPACE}/audits` no wire-up
- **Phase C + D parqueados:**
  - Phase C (Telemetry drilldown + Shadow tracker, ~8h) — gated em D49 phase 2 baseline ≥7 dias
  - Phase D (Ops audit timeline + KG stats, ~6h) — gated em Phase C land + kg_snapshots table criada
- **Acesso prod:** `http://nox-vps.tailnet:18802/observability/{health,evals}.html` via Tailscale tunnel
- **NÃO FAZEMOS:**
  - Prometheus/Grafana integration (200MB+ RAM permanent VPS, lean stack rule violation)
  - Time-series DB (data já em SQLite com timestamps)
  - Alerting/SMS (cron canary */15min + Discord webhook F05 já cobre)
  - Multi-user/RBAC (single-user dashboard)
- **Cross-links:** spec `specs/2026-05-01-F10-observability-dashboard.md` (refresh 2026-05-21), PR #207 (Phase A), PR #212 (Phase B), memory `[[evening-burst-2026-05-21-4prs-f10-deployed]]` + `[[late-evening-2026-05-21-f10b-deployed-l4-plural]]`.
- *Origem:* sessão 2026-05-21 evening. Spec refresh + Phase A solo + agent worktree paralelo pra Phase B.

---

### 2026-05-24 — A2 Tier 3 crypto + audit — 5 decisions RESOLVED + P0 spike GO (D54-D58)

#### D54 — SQLCipher como at-rest cipher primary, conditional approved via P0 spike GO verdict

- **Pergunta:** A2 Tier 3 (at-rest encryption + audit trail) precisa cipher path. Vale SQLCipher (drop-in, auditor-friendly, WAL coberto, backup transparent) vs LUKS-only (kernel-layer, mais simples mas força boot-time unlock) vs reject (espera futuro)?
- **Decisão:** **SQLCipher primary** (recon §10 D-A2T3-1 option b: conditional on P0 spike pass). P0 spike executed 2026-05-24, 22/22 critical gates PASS, **verdict GO**. SQLCipher 4.16.0 + `better-sqlite3-multiple-ciphers` v13.x + `sqlite-vec` v0.1.9 form a viable stack. LUKS-only pivot reserved as fallback for future SQLCipher CVE/regression scenarios.
- **Por quê:**
  - WAL/SHM herda cipher transparentemente (T3 storage breach coberto)
  - `VACUUM INTO` snapshots herdam cipher (T2 backup theft coberto + op-audit pattern compat zero-change)
  - Backup compat — `cp file.db` mantém cifra (no unlock externo)
  - Open-source auditor story — Signal, 1Password, dezenas M deploys
  - P0 spike confirmou perf real (Phase 7 steady-state): read p50 +22µs (4→26µs), FTS5 p50 +24µs (9→33µs) — projected impact on 940ms p50 hybrid search = +3-7%, fica dentro do §7 hard-gate p95 <3000ms
  - sqlite-vec v0.1.9 carrega na DB encriptada via `loadExtension()` API; vec0 virtual table + INSERT + cosine MATCH + VACUUM INTO snapshot todos preservam dados — zero breaking
  - Licenças compatíveis (MIT + Apache-2.0 + BSD-3-Clause), zero GPL contamination
- **Cipher mode locked:** `PRAGMA cipher_compatibility = 4` → AES-256-CBC + HMAC-SHA512 (SQLCipher 4 default). GCM não exposto via plain PRAGMA em 4.x; CBC+HMAC pairing provê AEAD-equivalent integrity, FIPS-vetted. Satisfaz §12 hard rule "no plain CBC" — pairing is integrity-protected.
- **NÃO FAZEMOS:**
  - Custom VFS implementation (NIH; recon §2 rejeitado)
  - Column-level app encryption (quebra FTS5 + sqlite-vec; recon §2 rejeitado)
  - Static-linked custom SQLCipher build (high maintenance; D57 option b rejected)
  - HSM/KMS integration (Tier 3.1 futuro; §11 anti-scope)
- **Cross-links:** recon `specs/2026-05-24-A2-tier3-crypto-audit-RECON.md` §10, spike `experiments/a2-tier3-sqlcipher-spike/RESULTS.md`, memory `[[user-accepts-gemini-key-risk]]` (key-material risk posture precedent), D27 sequencing.
- *Origem:* sessão 2026-05-24 Sat morning. Toto §10 sign-off + executor-high P0 spike pipeline. 22/22 critical gates PASS.

#### D55 — `reads_audit` table opt-in default OFF via `NOX_READS_AUDIT=1`

- **Pergunta:** Read-path audit (search queries, answer calls, /api/health hits) é default ON ou OFF? Trade-off privacy-by-default (Autonomy pillar) vs compliance-completeness (regulated tier)?
- **Decisão:** **Default OFF** (recon §10 D-A2T3-2 option a). Opt-in via env `NOX_READS_AUDIT=1` (canonical name; normalized from draft `NOX_AUDIT_READS` to match table-name + existing env conventions like `NOX_SEARCH_LOG_TEXT`).
- **Por quê:**
  - Alinha com Autonomy pillar princípio "data é sua, provider sua escolha" — don't collect what user didn't ask
  - Zero hot-path overhead em deploys non-regulated (early-return em wrapper antes de qualquer SQL)
  - Regulated tier (LGPD/HIPAA/SOC2) habilita via single env var — discoverable, doc em DEPLOY-A2-T3.md
  - Trade-off T6 (read trail gap em recon §1.1) accepted in non-regulated default; mitigated via flag
- **Implementation note:** `withReadAudit()` wrapper short-circuits when `process.env.NOX_READS_AUDIT !== '1'` — zero INSERTs, zero contention. p50 impact OFF: 0 µs. p50 impact ON: ~+0.5ms per query (single indexed row INSERT, hash precomputed).
- **NÃO FAZEMOS:**
  - Default ON sem opt-out (recon §10 option b violates Autonomy)
  - NODE_ENV-conditional default (option c — too magic, env detection unreliable across CLI/MCP/cron)
  - Log plaintext query — `query_hash` (sha256 canonical) only; secret scrubbing herda de op-audit
- **Cross-links:** D54, recon §4.3 F1, memory `[[a1-op-audit-module]]` (parent pattern).
- *Origem:* sessão 2026-05-24 Sat morning, Toto §10 sign-off.

#### D56 — Signed checkpoints via Ed25519 manual signing (auditor-grade, offline pubkey)

- **Pergunta:** Como gate forense (auditor verifiability) pro audit trail? Auto-cron HMAC (zero ops cost mas reviewer must trust host) vs Ed25519 manual (auditor-grade mas operational batch)?
- **Decisão:** **Ed25519 manual signing** (recon §10 D-A2T3-3 option a). Toto signa checkpoints em batch semanal; cron escreve `audit_checkpoints` rows com `signature=NULL` (pending state). Public key publishable em `docs/AUDIT-PUBKEY.md`; private key off-box (Toto laptop + offline paper backup).
- **Por quê:**
  - Reviewer pode verify chain offline contra published public key, **sem precisar confiar no host VPS** — moat real pra Autonomy story
  - HMAC sozinho (option b) com key in box = reviewer must trust nox-mem operator → defeats purpose pra cliente regulado
  - Both (option c, defesa em camadas) é upgrade futuro se cliente pedir explicitamente — começar (a) sozinho
- **Implementation note:**
  - Cron escreve `audit_checkpoints` rows com `signature=NULL, signature_algo=NULL` (pending state)
  - `nox-mem audit verify` reporta pending checkpoints separately from chain-broken (3-state: VERIFIED / PENDING / BROKEN)
  - Signing tool offline: `nox-mem audit sign --since <id> --key <pubkey-hash>` assina batch + UPDATEs rows (permitido apenas quando `OLD.signature IS NULL` per trigger `trg_audit_checkpoints_no_update_finalized`)
  - Ed25519 keypair geração one-shot via `nox-mem audit keygen` (saves pubkey em repo, private em separate file flag-protected)
- **NÃO FAZEMOS:**
  - Key escrow em nuvem terceira (vendor lock-in, §11 anti-scope O5)
  - HSM/YubiKey integration v1 (Tier 3.1 futuro)
  - Auto-sign via cron (defeats auditor-grade — reviewer must verify Toto sign manually)
- **Cross-links:** D54, recon §4.3 F2 + §5 schema sketch (audit_checkpoints table).
- *Origem:* sessão 2026-05-24, Toto §10 sign-off.

#### D57 — Loadable extensions enabled + path allowlist + chmod 0o555 hardening

- **Pergunta:** sqlite-vec é loadable extension. SQLCipher 4 permite via `enable_load_extension`. Security risk de shared lib injection se atacante escreve em workspace?
- **Decisão:** **Yes, habilitar com hardening em camadas** (recon §10 D-A2T3-4 option a). P0 spike confirmou `sqlite-vec` v0.1.9 carrega cleanly via `loadExtension()` API. Hardening cravado em P1 spec.
- **Por quê:**
  - Static-linked custom build (option b) é alta manutenção: pipeline custom + sem patches upstream + bottleneck cada update sqlite-vec
  - Spike GO removeu need pra "wait until alternatives explored" (option c)
  - Risk mitigation em 4 camadas:
    1. **Path allowlist** — somente `node_modules/sqlite-vec-{platform}-{arch}/vec0.{dylib,so}` resolvable; absolute path rejected se não estiver em allowlist
    2. **chmod 0o555** em extension binary — read+execute only, NO write (previne on-disk swap do dylib)
    3. **chmod 0o700** em parent `node_modules/sqlite-vec-*/` — only nox-mem service user pode traverse
    4. **dylib SHA256 verification opt-in** via `NOX_VERIFY_EXTENSION_SHA256=<expected>` env (P3 future extension)
- **Implementation note:** Add to `src/lib/db.ts` startup: `db.loadExtension(allowedPath)` only after `realpath(allowedPath)` check matches allowlist member. Reject relative paths, `..` traversal, symlinks pointing outside `node_modules/sqlite-vec-*`. Pattern lifted from op-audit snapshot path validation (memory `[[a1-op-audit-module]]` symlink-aware realpathSync).
- **NÃO FAZEMOS:**
  - Allow arbitrary loadExtension() paths em prod (security regression)
  - Disable load_extension globally (breaks sqlite-vec, breaks core search)
  - Skip dylib verification permanently — P3 extension obriga `NOX_VERIFY_EXTENSION_SHA256` em regulated tier
- **Cross-links:** D54, recon §3.4 + §10 D-A2T3-4, spike Phase 4 + Phase 8 PASS results, memory `[[a1-op-audit-module]]`.
- *Origem:* sessão 2026-05-24, Toto §10 sign-off, hardened via P0 spike empírico.

#### D58 — `reads_audit` retention env-driven 90d default + archive (não delete) policy

- **Pergunta:** Quanto tempo manter read trail antes de archive-out? 30d (privacy max) / 90d (compliance default) / indefinite (storage blow-up) / env-driven?
- **Decisão:** **Env-driven `NOX_READS_AUDIT_RETENTION_DAYS` default 90, archive policy (não delete)** (recon §10 D-A2T3-5 option d). Move logic em separate `nox-mem-audit-archive.db` file (também SQLCipher-encrypted, same key); main `reads_audit` mantém append-only invariant.
- **Por quê:**
  - Alinha com `retention_days` schema convention existente (chunks daily=90d, lesson=180d, decision=365d, feedback/person=NULL) — operator aprende UM padrão só
  - Archive (não delete) preserva forensic completeness — reviewer pode reconstruir histórico full
  - 30d default (option a) curto demais pra quarterly compliance reviews
  - Indefinite (option c) explode storage em high-cardinality search workloads (estimate ~100k+ rows/month em dev ativo, ~5MB/month)
  - Env-driven permite regulated user override (`NOX_READS_AUDIT_RETENTION_DAYS=365`) sem code change
- **Implementation note:**
  - Cron weekly (NOT daily — table will be small, weekly suffices)
  - Archive mechanism é LOGICAL (separate file), main table never DELETEs (preserves trg_no_delete invariant)
  - Query union: `SELECT * FROM reads_audit WHERE ts >= now() - retention UNION ALL SELECT * FROM archive.reads_audit WHERE ts < now() - retention`
  - Archive file rsync-friendly off-box for regulated tier (opt-in, NÃO default — alinha com `[[no-f09-offsite-backup]]`)
  - Storage cost: ~50 bytes/row × 100k = 5MB/month — negligible em DB que já tem 62.9k chunks @ ~200MB
- **NÃO FAZEMOS:**
  - DELETE rows do main table (quebra append-only invariant cravado D55+W2-1)
  - Auto off-site backup (`[[no-f09-offsite-backup]]` memory, Toto rejeitou 2× já)
  - Retention applied ao `ops_audit` (continua indefinite — destructive ops são raros, ~12/day; bounded growth)
  - Retention applied ao `audit_checkpoints` (chain integrity exige todos checkpoints — indefinite mandatory)
- **Cross-links:** D54, D55, recon §6 retention table, memory `[[no-f09-offsite-backup]]`, schema v.30 bump.
- *Origem:* sessão 2026-05-24, Toto §10 sign-off, retention pattern alinhado com `retention_days` schema convention.

#### D59 — Close cap@500 mem0 gap via ingest-side concentration is structurally non-viable; ship two-metric narrative

- **Pergunta:** Após o gate Q4 Phase 2 ficar dependente de superar mem0 em métricas cross-system, três caminhos foram explorados em 2026-05-23/24 para fechar o gap de **−0.0397 nDCG@10** que nox-mem hybrid@500 (0.0918) tinha vs mem0@500 (0.1315). É possível fechar esse gap sem trocar o stack de modelos (Gemini, não OpenAI)?
- **Decisão:** **Não — ship a narrativa two-metric (nDCG@10 + coverage) já cravada no `docs/COMPARISON.md` rev4.** O gap structural é inherente ao mecanismo de comparação (`mem0` cap@500 = 500 extracted facts via LLM ingestion; nox-mem cap@500 = 500 raw chunks). Os três experimentos a seguir confirmam isso de forma independente:
- **Por quê:**
  1. **PR #337 — Query rewrite layer (Gemini Flash Lite)** falhou com **−11.8% nDCG@10** vs baseline. Hipótese: enriquecer queries cape@500 via LLM antes do retrieval. Resultado: ruído adicionado piora o ranking. Aprendizado: query-side pre-processing não compensa concentration mismatch.
  2. **PR #339 — E+F+H combo (KG traversal + RRF k=20 + top-k expansion)** retornou **NEUTRAL +2.4%** com gap **persistente**. Apenas F (RRF k=20) carregou o ganho (+0.0022). E (KG traversal) foi dead-weight com +600ms penalty. H (top-k expansion) regrediu adversarial −7.9% a −13.8%. Hub-entity centrality failure: Melanie/Caroline cover 22-40% de 583 entities. Aprendizado: nenhum dos três é suficiente isoladamente nem combinado.
  3. **PR #341 — A2 chunk summarizer (Gemini Flash Lite, atomic-fact mem0-style)** falhou pior: **−34% nDCG@10 full corpus (0.4509 → 0.2973), −69% no cap@500 (0.0918 → 0.0645)**. 3 mecanismos de falha: (a) LoCoMo turns curtas demais (mean 144 chars) — 40% retornam "no facts found"; (b) LongMemEval session compression 95-99% perde verbatim signal — adversarial/preference/user-quote subsets viram 0.00; (c) embeddings densas sobre fact bullets clusterizam denso demais. Custo: $0.30 Gemini, 6,822 chunks summarized em 18min + 44min ingest. Template vencedor (de 3 testados em mini-ablation n=10): A — atomic-fact extraction.
- **Estrutura confirmada:** Os 3 paths exploraram 3 vetores distintos (query-side rewrite, hybrid graph+RRF, ingest-side LLM concentration). Todos falharam de modos DIFERENTES. Evidência forte que **a vantagem mem0@500 é a concentração de ingest (500 facts extraídos LLM-side com viés-de-saliência embutido)** vs **nox-mem@500 (500 raw turns sem concentração)**. Não é replicável dentro do hybrid sem mudar o paradigma de ingest.
- **Design intel preservado (Lab Q1 parking-lot):** A2 **WON em 4 subsets full-corpus** quando aplicado: multi-hop 0.75 / single-session-assistant 0.63 / temporal-reasoning 0.62 / open-domain 0.50. A2 **FATALLY FAILED em 3 subsets** (0.00): adversarial / single-session-preference / single-session-user. Esta assimetria sugere um **hybrid-of-hybrids router** — indexar AMBOS raw + summarized chunks, routing por detected query intent. Concentration para analytical/multi-hop; verbatim para adversarial/preference/quote. Carved em `[[d59-implement-pain-weighted]]` follow-up para Lab Q1.
- **Implementation note:**
  - Ship narrativa `docs/COMPARISON.md` rev4 (já em main): "production-realistic full-corpus advantage" (nDCG@10 0.4509, +243% vs mem0 cap-imposed) + honest disclosure do trade-off cap@500
  - Q4 Phase 2 gate: **two-metric (nDCG@10 + coverage threshold ≥87%)** — captura tanto qualidade quanto cobertura, evita o jogo de cap-cherry-picking
  - Encerrar todas as 3 branches como archived NEGATIVE com per-subset breakdowns preservados em branch remotes
  - NÃO tentar 4o caminho de concentration pré-launch Wed 2026-06-03
- **NÃO FAZEMOS:**
  - Buscar concentration parity com mem0 dentro da arquitetura hybrid atual (3× rejected; structural mismatch)
  - Trocar Gemini → OpenAI/Claude embeddings para emular extracted-fact density (Toto rejeitou explicitly 2026-05-24, `[[user-accepts-gemini-key-risk]]`)
  - Apresentar cap@500 nDCG@10 como single-metric headline (esconde o trade-off — narrativa rev4 já corrige)
- **Cross-links:** PRs #337, #339, #341 (all closed/archived), `docs/COMPARISON.md` rev4, memory `[[honest-cross-system-framing]]`, `[[adapter-response-shape-validation]]`, `[[no-getdb-in-eval-scripts]]`, `[[shared-loader-canonical-pattern]]`, NÃO FAZEMOS §1 item 29.
- *Origem:* sessão 2026-05-23/24, três experimentos independentes 2026-05-23 23:30 BRT a 2026-05-24 11:30 BRT, Toto sign-off "Fechar e arquivar" 2026-05-24 13:40 BRT.

---

### 2026-05-28 — Phase G EverMemBench 5-batch learnings (D60-D63)

#### D60 — Rerank shipped opt-in, NÃO default

- **Context:** Phase G EverMemBench 5-batch validation (PRs #367 + #369 merged) — batch 004 single-shot dizia F_MH +8pp (5× lift, "breakthrough"); 5-batch revelou +1.61pp marginal (95% CI [3.97, 9.69] sobrepõe baseline 5.22%). MA dim regrediu -3 a -4pp (invisível em batch 004 por selection bias). F_SH sign-flipped (batch -6.12 vs 5-batch +0.40) — regressão era batch-specific.
- **Decisão:** MiniLM-L-6-v2 cross-encoder rerank shipped **opt-in** via `--rerank` flag / `NOX_RERANKER_ENABLED=1` / `/api/answer?mode=exploratory`. **Default OFF.** PR #367 code stayed merged (env-gated).
- **Rationale:**
  - 5-batch honest trade-off: F_MH +1.61pp marginal, Overall -0.96pp, MA_C -4.00pp / MA_P -2.80pp / MA_U -3.84pp, latência +3.7s p50
  - Trade-off é workload-dependent (hard-recall multi-hop workloads ganham; head-precision + entity lookup + MA workloads perdem) — não universal-win
  - Phase D config (rerank OFF) permanece canonical headline: **62.22% nDCG@10 > MemOS 59.27%** — Phase G NÃO compete com esse headline, é trade-off study
  - MemOS F_MH gap (18.94%) fechou só 11.7% com rerank (5.22% → 6.83%); remaining 12.11pp provavelmente requer multi-query expansion ou query decomposition (Lab Q2)
- **Não-objetivo:** rerank como default universal. Re-evaluation trigger: adaptive query classifier (D60-follow-up Lab Q1 #1) que enable always-on rerank COM routing inteligente por query type.
- **NÃO FAZEMOS:**
  - Ship rerank como default sem adaptive classifier que mitigue MA regression
  - Citar batch 004 +8pp em materials marketing ou paper (single-batch overclaim)
  - Apresentar rerank como win em head-precision ou MA workloads (evidência contrária)
- **Cross-links:** PRs #367 (batch 004 baseline, env-gated) + #369 (5-batch validation + RESULTS-PHASEG-5BATCH.md), memory `[[phase-g-minilm-multi-hop-breakthrough]]`, `[[cross-encoder-trade-off-shape]]`, `[[single-batch-gates-unreliable-5x-overstate]]`, `[[memory-awareness-dimension-must-be-audited]]`.
- *Origem:* sessão 2026-05-28. 5-batch agent `aa153b5d66b9a9fbe` (~$3.00 ~93min). Cumulative Phase G: ~$3.90.

---

#### D61 — Optional install path para rerank dependencies

- **Context:** Autonomy pillar preservation — nox-mem core pitch é "um arquivo SQLite, `cp` é backup". Rerank deps (sentence-transformers + torch/onnxruntime) pesam ~500MB.
- **Decisão:** rerank deps NÃO bundled em `nox-mem` core. Optional install `pip install nox-mem[rerank]` (ou equivalent extras_require em `pyproject.toml` / `package.json` devDependencies opcional). Core permanece sqlite-only.
- **Rationale:**
  - "nox-mem é um arquivo SQLite" pitch (vs Zep "precisa Neo4j", vs mem0 "precisa OpenAI") é fundamental para Autonomy positioning
  - ~500MB deps obrigatórios quebraria essa narrativa para usuários que não precisam de rerank
  - Pattern da indústria: `pip install transformers[torch]`, `pip install sentence-transformers[onnxruntime]` — users opt-in explicitamente
  - VPS Hostinger 4 vCPU / 16GB RAM: ~1.1GB RAM para 4 processos MiniLM paralelos — aceitável mas não obrigatório para todos os deploys
- **NÃO FAZEMOS:**
  - Bundle sentence-transformers/torch em nox-mem core install
  - Fazer rerank dep obrigatória sem gate de opt-in explícito
- **Cross-links:** D60 (rerank opt-in decision), memory `[[parallel-crossencoder-cpu-scaling]]`, `[[cross-encoder-trade-off-shape]]`.
- *Origem:* sessão 2026-05-28, derivado de D60 + Autonomy pillar preservation.

---

#### D62 — 5-batch + 95% CI methodology canonical para gate decisions

- **Context:** Phase G batch 004 single-shot (+8pp F_MH) foi initial gate candidate — 5-batch validation revelou apenas +1.61pp marginal, com F_MH 95% CI sobrepondo baseline. Batch 004 era +1.4σ upper-tail outlier dos 5 batches (per-batch F_MH: 004=10 / 005=4 / 010=6 / 011=6 / 016=8.2). Single-batch overstated efeitos 3-6× across categories.
- **Decisão:** Single-batch eval results são **"preliminary signal"**, não decision gates. Ship/reject claims requerem **5-batch + 95% CI lower bound > baseline**. Canonical 5-batch set EverMemBench: `004, 005, 010, 011, 016`.
- **Rationale:**
  - Per-batch variance EverMemBench: F_MH σ ~2.3pp, F_HL σ ~5pp, F_SH σ ~3pp, MA_C/P/U σ ~3pp. Qualquer single-batch Δ < 2σ é provavelmente noise floor.
  - Sign-flips e selection bias são frequentes em single-batch: F_SH flippou (batch -6.12 vs 5-batch +0.40); MA regression invisible em batch 004 por selection bias (batch 004 já tinha pior MA dos 5).
  - Cost-benefit: 5-batch eval ~4× single-batch ($3 vs $0.75) — ROI positivo vs paper credibility risk de single-batch overclaim. Phase G pagou $3.75 total pra evitar overclaim.
  - Precedente cascata: D59 três experimentos independentes confirmaram pattern; D62 generaliza pra todos os evals futuros.
- **Aplicação operacional:**
  - "Preliminary signal" do single-batch pode (e deve) informar hipóteses, triggerar 5-batch run, guiar ablation design — mas NÃO decide ship/reject sozinho
  - PRs que reportam eval results DEVEM incluir se são single-batch (preliminary) ou 5-batch (decision-grade)
  - Se 5-batch indisponível imediatamente, single-batch result DEVE incluir per-batch CI estimate dos baselines históricos + flag "preliminary — CI não confirma"
- **NÃO FAZEMOS:**
  - Gate decisions de ship/reject baseadas em single-batch result sem CI confirmation
  - Citar single-batch numbers como headline em paper ou GTM materials sem CI bounds
  - Assumir que single-batch "breakthrough" sobreviverá 5-batch validation sem verificar σ historical
- **Cross-links:** PRs #367 + #369, memory `[[single-batch-gates-unreliable-5x-overstate]]`, `[[phase-g-minilm-multi-hop-breakthrough]]`, D60.
- *Origem:* sessão 2026-05-28, lesson cravada pós Phase G batch 004 → 5-batch delta revelation.

---

#### D63 — MA dim (Memory Awareness) mandatory em eval reports de retrieval changes

- **Context:** Phase G batch 004 single não reportou MA dim regression. 5-batch revelou MA_C -4.00pp / MA_P -2.80pp / MA_U -3.84pp — cross-encoder rerank rank por query-chunk relevance, NÃO por user-context maintenance, logo profile/entity chunks get displaced silently.
- **Decisão:** Memory Awareness sub-dims (MA_C/MA_P/MA_U) **sempre reportados** em qualquer eval que mude retrieval pipeline. Não basta F_SH/F_MH/F_HL/F_TP/MC/OE.
- **Rationale:**
  - MA é "silent killer dim" — não aparece em traditional retrieval metrics (precision/recall/nDCG/MRR). Requer eval queries explicit testing context understanding + profile recall + preference updates.
  - Cross-encoder rerank é principal MA-regressor identificado até agora. Multi-query expansion, query decomposition, KG path retrieval — todos precisam ser testados em MA dim antes de ship.
  - nox-mem entity file format (compiled/frontmatter/timeline) + section_boost provavelmente PROTEGE MA via boost garantido de entity chunks — hipótese a verificar empiricamente antes de MA-protection mechanism (Lab Q1 #2).
  - Lab Q1 #2 (MA-protection mechanism): force `section_boost` entity files sobrevivem rerank displacement — architectural fix para o regression. Spec e PR separados depois.
- **Aplicação operacional:**
  - Eval PRs que modificam retrieval ranking DEVEM incluir MA_C/P/U numbers (ou explicitamente documentar por que MA eval não disponível + plano pra medir)
  - `docs/COMPARISON.md` updates futuros incluem MA dim quando competitors reportarem
  - Paper §5 e §6: MA regression discussion é differentiator de research maturity vs papers que só reportam F_SH/F_MH
- **NÃO FAZEMOS:**
  - Approve retrieval changes sem MA audit (mesmo que F_MH/F_HL positive)
  - Assumir que MA está OK se não foi medido — "não medido" ≠ "sem regressão"
  - Skip MA dim em evals por ser "expensive" — EverMemBench já inclui MA_C/P/U no mesmo run; zero custo adicional
- **Cross-links:** memory `[[memory-awareness-dimension-must-be-audited]]`, `[[cross-encoder-trade-off-shape]]`, `[[phase-g-minilm-multi-hop-breakthrough]]`, D60, D62.
- *Origem:* sessão 2026-05-28, pattern revelado por Phase G 5-batch (MA invisible em batch 004 por selection bias).

---

### 2026-05-29 — Wave A consolidated learnings (D64-D67)

#### D64 — KG densification REJECTED, sparse canonical

- **Context:** PR #384 Wave A — Phase KG densification test (2.77× entities + 2.99× relations target met) vs sparse baseline (PR #379).
- **Decisão:** Lab Q1 #4 KG path retrieval uses **sparse KG (~500 entities, ~800 relations)** as canonical. Densification REJECTED.
- **Rationale:**
  - 5-batch bench dense vs sparse: Overall -0.53pp regression / F_MH -1.60pp regression (sparse achieved +2.81pp vs Phase H v2; dense only +1.21pp) / latency 4-50× slower (307-353ms p50 vs 7-105ms)
  - Mechanism: dense KG dilutes 1-hop walk discriminator + boost noise (more entities matched per query = more chunks ranked up = top-K filled with marginal content)
  - MA gap NÃO density-bound — only MA_U responds (+1.68pp), MA_C + MA_P flat. Closing MA gap requires different mechanism (composability w/ KG path scoring Approach C ou MA-protection w/ KG anchor)
  - Coverage saturation: sparse already 90.84%, dense 97.24% marginal lift introduces noise across all queries
- **Re-evaluation trigger:** alternative KG mechanism (path scoring Approach C Q2) ou GPU + larger KG indexing approach.
- **NÃO FAZEMOS:**
  - Densify KG beyond ~500-800 entities for 1-hop walk
  - Run kg-build com gemini-2.5-flash full unless investigating Approach C
  - Use density as MA gap closure mechanism (refuted)
- **Cross-links:** PR #379 (sparse canonical), PR #384 (density test), memory `[[kg-density-refuted-sparse-canonical]]`, `[[kg-extract-density-bounds-signal-CEILING]]`, `[[lab-q1-4-kg-path-3of4-gates-win]]`.
- *Origem:* sessão 2026-05-29 Wave A — agent `a42c12f56e9e03b79` ~88min, $3.64 spent.

---

#### D65 — Multi-query expansion ship opt-in (biggest single F_MH knob)

- **Context:** PR #385 — Lab Q1 #3 Approach B sub-query decomposition (LLM splits query → N sub-queries → RRF union) 5-batch bench.
- **Decisão:** `NOX_MQ_ENABLED=1` env-gated, **default OFF**. Ship as opt-in for multi-hop-heavy workloads.
- **Rationale:**
  - F_MH +3.61pp 5-batch = **biggest single retrieval-side knob measured** (2× KG sparse +2.81pp, 2.5× Phase G rerank +1.61pp, 1.8× Phase AC +2.01pp)
  - 3/4 gates met (Overall -1.12pp narrowly misses -1pp tolerance; MA -1.38pp ✅; Latency 1.68× ✅)
  - Cost ~$0.0001/query (gemini-flash-lite decomposer free under quota); LLM overhead ~$0 in practice
  - Latency p50 +1085ms (1.68× baseline) — acceptable for opt-in advanced multi-hop mode
  - **Composability with KG sparse predicted +6.42pp F_MH combined = closes 41% of MemOS GPT-4.1-mini gap** (Wave B validation in-flight)
- **Não-objetivo:** ship MQ como default — Overall regression -1.12pp não justifica forcing latency cost em factual workloads.
- **NÃO FAZEMOS:**
  - Enable MQ default sem clean adaptive routing (Lab Q1 #1) ou composability validation
  - Use rerank simultaneously with MQ no current adapter (rerank OFF in Phase MQ for isolated measurement)
- **Cross-links:** PR #385, memory `[[lab-q1-3-multi-query-expansion-3of4-gates-win]]`, `[[mq-kg-mechanically-additive-prediction-6-42pp]]`, `[[f-mh-retrieval-bound-not-generation]]`, D60.
- *Origem:* sessão 2026-05-29 Wave A — agent `a1fc7084b0794845c` ~101min, $5 spent.

---

#### D66 — MA-protection Approach A ships opt-in com corpus mismatch caveat

- **Context:** PR #386 — Lab Q1 #2 Approach A bypass-entity (skip cross-encoder rerank para chunks `section IN ('compiled', 'frontmatter')`) 5-batch bench em EverMemBench (chat-only corpus).
- **Decisão:** `NOX_MA_PROTECTION_ENABLED=1` env-gated, **default OFF**. Mechanism corretamente implementado (32/32 unit tests pass) MAS validation corpus mismatch — Set E (entity chunks identified) = empty para 3125/3125 queries no EverMemBench (chat transcripts não têm section markers).
- **Rationale:**
  - **Unexpected positive bonus:** F_MH +4.02pp (2.5× Phase G Gemini's +1.61pp) + F_HL +4.34pp (1.7× Phase G's +2.58pp) — cross-encoder rerank on gpt-4.1-mini backbone amplifies hard-recall lift significativamente vs Gemini (lesson `[[gpt-4-1-mini-amplifies-rerank-hard-recall-25x]]`)
  - **MA recovery FAILED (0%, actually -6.55pp worse than baseline)** — bypass-entity Set E empty, mechanism never fired
  - **Composability path identified:** extend bypass criterion to `(section IN compiled/frontmatter) OR (chunk_id IN kg_evidence_chunks_for_query_entities)` — uses KG path retrieval entity lookup (PR #379) to identify protected chunks. Works on any corpus.
  - Wave B KG+MAP bench validates composability (in-flight)
  - Validation deferred to prod-style corpus (nox-mem prod 183 entity files) ou KG-anchored composability — bench result on EverMemBench tells us nothing about mechanism efficacy
- **Aplicação operacional:**
  - Code production-ready, ship as opt-in immediately
  - DO NOT use Phase MAP single bench results to argue against bypass-entity mechanism — corpus was wrong
  - Wave B KG+MAP results determine future investment direction
- **NÃO FAZEMOS:**
  - Enable MA-protection default sem corpus que tem entity markers ou KG-anchored extension
  - Cite -6.55pp MA regression como mechanism failure (was corpus mismatch)
  - Skip Set E instrumentation em future MA-protection benches (lesson `[[empirical-set-e-empty-confirms-mechanism-not-corpus]]`)
- **Cross-links:** PR #386, memory `[[lab-q1-2-ma-protection-corpus-mismatch]]`, `[[ma-protection-needs-entity-corpus-or-kg-anchor]]`, `[[gpt-4-1-mini-amplifies-rerank-hard-recall-25x]]`, D60.
- *Origem:* sessão 2026-05-29 Wave A — agent `ae97162c2b0aa6033` ~189min, $4.50 spent.

---

#### D67 — Backbone portability claim revised 2.1× → 1.6× (5-batch correction)

- **Context:** PR #372 Phase H v2 batch 004 single dizia nox-mem 54.15% vs MemOS 42.55% = +11.6pp (implying 2.1× portability ratio Gemini→GPT-4.1-mini swap). PR #377 5-batch validation revelou batch 004 was +1.7σ upper-tail outlier; 5-batch reality is +9.13pp.
- **Decisão:** nox-mem cross-backbone portability claim = **1.6× more portable than MemOS** (5-batch verified). Replace prior 2.1× single-batch claim em all materials.
- **Rationale:**
  - 5-batch swap math: nox-mem -10.54pp (Phase D 62.22% → Phase H v2 51.68%) vs MemOS -16.72pp (Table 4 Gemini 59.27% → GPT-4.1-mini 42.55%)
  - Ratio: 16.72 / 10.54 = 1.586 ≈ **1.6×**
  - Prior 2.1× was artifact of batch 004 outlier single-shot extrapolation
  - 1.6× still strong claim — robust + defensible across 5-batch CI
- **Aplicação operacional:**
  - Paper §5 (PR #382) já atualizado com 1.6× (revised)
  - GTM messaging (PR #383, README + COMPARISON.md + COMPETITIVE-POSITIONING.md) já atualizado com "what not to say" guardrails preventing future 2.1× regression
  - Memory `[[nox-mem-backbone-portability]]` já atualizado
  - Future single-batch claims que produzem outlier ratios devem flag as "preliminary, awaiting 5-batch confirmation" (D62)
- **NÃO FAZEMOS:**
  - Cite 2.1× em qualquer material novo (paper, GTM, blog, talks)
  - Use single-batch portability ratios as headline numbers without CI confirmation
- **Cross-links:** PRs #372, #377, #382, #383, memory `[[nox-mem-backbone-portability]]`, `[[phase-h-v2-cross-backbone-win]]`, `[[single-batch-gates-unreliable-5x-overstate]]`, D62.
- *Origem:* sessão 2026-05-29, 5-batch correction lesson aplicada cross-material.

---

#### D68 — Wave B composability dual finding: same-stage overlap vs different-stage additivity

- **Context:** Wave B testou 2 composabilidades em paralelo (PR #389 KG+MQ; PR #390 KG+MAP) sobre Phase H v2 baseline (gpt-4.1-mini). Resultado: mecanismos no MESMO stage do pipeline (KG+MQ ambos retrieval-side) OVERLAP em 90.8% co-fire rate (residual -1.61pp vs +6.42pp additive prediction). Mecanismos em DIFERENTES stages (KG retrieval + MAP rerank-protection) compõem ADDITIVELY no F_MH (+4.04pp ≈ standalone MAP +4.02pp) E entregam partial MA recovery (+1.53pp vs MAP alone).
- **Decisão:**
  - **Ship Phase KGMAP opt-in** (PR #390 merged) via `NOX_ADAPTER_MODE=phaseKGMAP`. Default OFF. 3/4 gates passed (Overall -0.67pp ≤ -1pp tolerance + F_MH +4.04pp + MA partial recovery vs MAP alone). MA composite gate fail (-5.02pp vs Phase H v2) accepted como improvement vs prior opt-in standalone.
  - **REJECT Phase KGMQ default-enable** (PR #389 merged opt-in via `NOX_KG_MQ_COMBO=1` for max F_MH at any cost users only). 1/4 gates passed. Don't ship combo as default.
  - **Wave C orthogonal-stages hypothesis priorizada** — different-stage composability é mais robusto que same-stage; futuras explorações priorize MUDAR de stage (retrieval → rerank → routing → temporal) ao invés de stack mecanismos no mesmo stage.
- **Rationale:**
  - **Mechanism validation (mecanicamente alive):** Phase MAP standalone (PR #386) Set E empty 3125/3125 queries (corpus inert). Phase KGMAP Set E = 0.33 chunks/query × 90.7% queries com KG pool. Corpus-mismatch problem resolvido via KG anchor bridge.
  - **F_MH composability shape:** sub-additive (-2.79pp residual vs perfect additivity) mas LOAD-BEARING — KG path lift (+2.81pp) NÃO é dominado por MAP lift (+4.02pp); MAP standalone era corpus-inert na maioria das queries, KG anchor desbloqueia mecanismo em 90.7%.
  - **MA recovery shape:** partial. KG anchor protege chunks identificadas via `kg_relations` walk (entity-relation evidence). EverMemBench MA dim queries usuário hit PROFILE chunks (user-info type questions: "what's my user's email?"). Profile chunks rarely são entity-relation chunks. Q2 future direction = profile-chunk identification mechanism (ortogonal a KG entity walk).
  - **Same-stage overlap (KG+MQ 90.8% co-fire):** validates a teoria que mecanismos no mesmo stage do pipeline convergem nas mesmas chunks (KG entity-walk identifica chunks A, MQ sub-query decomposição traz chunks A também via reformulações). RRF union sobre ambos = same boost twice. Not additive in practice.
  - **Different-stage additivity (KG+MAP):** retrieval expansion + rerank protection acting em diferentes pipeline stages compõem melhor. Stage orthogonality > score-merge non-conflict como composability principle.
- **Aplicação operacional:**
  - **Lab Q1 priorities final reorder:** 🥇 MQ canonical multi-hop (#385) + 🥇 KG sparse standalone (#379) + 🥇 KG+MAP opt-in combo (#390 NEW); 🚫 KG+MQ default REJECTED (#389 opt-in only); 🟡 AC clean (#381) + MAP standalone (#386) opt-in marginais
  - **Wave C candidates:** Triple KG+MQ+MAP (validate full pipeline-stage additivity); KG+MAP+temporal (3 stages); Profile-chunk identification (close remaining MA -5.02pp gap, NOT entity-chunk class)
  - **Paper §5 dual finding revision priorizada** — PR #382 §5 atual tem old additivity hypothesis (+6.42pp predicted KG+MQ). Revisar com:
    1. KG+MQ same-stage overlap (90.8% co-fire) refutes "retrieval-side knobs additive" naïve hypothesis
    2. KG+MAP different-stage additivity (+4.04pp on F_MH + partial MA recovery 0.33 chunks/q × 90.7% queries) validates "orthogonal pipeline-stages compose" refined hypothesis
  - **GTM messaging update:** "Hybrid retrieval+protection mode (opt-in)" como concrete pairing message; substituir prior "41% MemOS gap closure via composability" claim com "30% gap closure via best retrieval-side knob OR 26% via composable retrieval+protection mode (opt-in)"
  - **MemOS F_MH gap closure revised** (KG+MQ 30%, KG+MAP 26%, triple stretch predicted ~33-40%)
- **NÃO FAZEMOS:**
  - Default-enable KG+MQ combo (PR #389 opt-in only para max F_MH users)
  - Default-enable KG+MAP combo (PR #390 opt-in para users que precisam multi-hop + partial MA recovery)
  - Cite "41% MemOS gap closure via composability" em qualquer material novo (refuted via KG+MQ overlap)
  - Cite "KG anchor recovers MA cost" sem "partial" qualifier (+1.53pp recovery, gap remaining -5.02pp)
  - Future composability testa MESMO stage (e.g. KG + KG-variant, MQ + query-rewrite) — Wave B mostra overlap dominant; priorize stage orthogonality
- **Cross-links:** PRs #379 (KG sparse), #385 (MQ), #386 (MAP standalone), #389 (KG+MQ), #390 (KG+MAP), memory `[[lab-q1-wave-b-kgmap-3of4-gates-ship-opt-in]]`, `[[kg-mq-overlap-refutes-additivity]]`, `[[kg-anchor-fires-on-chat-corpus-validates-composability]]`, `[[kg-and-rerank-compose-additively-on-fmh]]`, `[[ma-recovery-needs-profile-chunks-not-entity-chunks]]`, D64, D65, D66.
- *Origem:* sessão 2026-05-29 Wave B — agents `kgmq-bench` (recovery) + `a0750026ed989b801` (KG+MAP). Total Wave B ~$10 budget across both benches. Wave A→B closure complete; Wave C queued.

---

#### D69 — Wave C triple REJECT default + F_MH ceiling DISCOVERED at retrieval-stage stacking

- **Context:** Wave C triple combo (KG+MQ+MAP) bench partial 2/5 batches (OpenAI quota exhausted mid-batch 010, preflight saved batches 011+016). F_MH REGRESSED -1.21pp vs Phase H v2 baseline (triple 2.00% vs baseline 3.21% vs best single opt-in KG+MAP 7.25%). Additivity residual -11.65pp = MOST NEGATIVE composability residual ever observed in Wave A/B/C. MA composite recovered +1.81pp vs KG+MAP alone (only PASS gate). 1/3 strict gates → REJECT default.
- **Decisão:**
  - **Ship Phase Triple as opt-in only** (PR #394 merged) via `NOX_ADAPTER_MODE=phaseTriple`. Default OFF. Artifacts shipped (adapter mode + smoke tests + bench scripts + aggregator) for future re-runs. Document corpus-mismatch + ceiling caveat.
  - **F_MH RETRIEVAL CEILING CONFIRMED** ≈ 7.25% (Wave B KG+MAP best). Stacking additional retrieval-stage mechanisms cannot escape this ceiling because KG+MQ 90.8% co-fire overlap (D68 finding) dominates top-K candidates; MAP rerank protection then inhibits demotion of redundant chunks. Result: answer model receives LESS diverse evidence than single-stage best opt-in, F_MH multi-hop reasoning fails.
  - **Q3 Iterative Retrieval (PR #393 spec) elevated** from "future direction" to **TOP F_MH lever**. Wave C empirically validated the orthogonal-stage hypothesis: F_MH ceiling cannot be escaped by retrieval-stage stacking; need answer/orchestration-stage mechanisms (multi-round retrieve-reason). Q3 ETA: spec freeze 2026-06-15 → POC 2026-06-30 → 5-batch 2026-07-15 → ship 2026-08-01.
  - **Re-run Wave C 5-batch CLEAN pending OpenAI quota top-up** (~$5). F_MH 2.00% on 2/5 batches could be lower-tail variance OR structural cap. Re-run will clarify magnitude but unlikely to change REJECT verdict (even if F_MH revealed as 4-5%, still below KG+MAP 7.25%).
- **Rationale:**
  - **Mechanism failure mechanism:** KG+MQ 90.8% co-fire (D68) means both surface same first-hop neighborhood chunks. MAP applied at rerank stage protects 14.52% of those (already-redundant) chunks. Answer model top-K is dominated by first-hop entity neighborhood. Bridge entities for second-hop multi-hop reasoning are ABSENT (filtered out by redundancy). F_MH catastrophic.
  - **Empirical validation of D68 orthogonal-stages hypothesis:** Wave B showed retrieval+rerank (KG+MAP) compose additively because they act on different pipeline stages. Wave C shows retrieval+retrieval+rerank (KG+MQ+MAP) DOES NOT compose because two retrieval mechanisms overlap structurally even with rerank protection on top.
  - **Cumulative F_MH learning matrix confirms ceiling ≈ 7-8% on gpt-4.1-mini with retrieval-side knobs only.** Path to closing remaining 11pp MemOS gap requires:
    1. Orthogonal-stage answer/orchestration mechanism (Q3 Iterative Retrieval; predicted +3-5pp)
    2. Backbone upgrade (Backbone Matrix in-flight; could close 30-50%+ via frontier reasoning over our retrieval pipeline)
    3. Q4 Profile-chunk MA-targeted (PR #392 spec; F_MH indirect via classifier routing)
  - **Latency compound effect:** Triple latency 3.7× baseline. Even if F_MH had worked, latency forces opt-in. Composition latency compounds; future composability stacks must measure compound latency, not per-mechanism.
- **Aplicação operacional:**
  - **Lab Q1 priorities final state (post-Wave-C):**
    🥇 MQ canonical multi-hop (#385)
    🥇 KG sparse standalone (#379)
    🥇 KG+MAP opt-in combo (#390)
    🚫 Triple combo (#394) — opt-in only, REJECT default
    🚫 KG+MQ combo (#389) — opt-in only, REJECT default
    🟡 AC clean (#381) + MAP standalone (#386) opt-in marginais
  - **Q3 Iterative Retrieval (PR #393) elevated:** top F_MH lever post-current waves
  - **Backbone Matrix (in-flight):** cheapest F_MH gap closure path if frontier backbones deliver
  - **Wave C re-run policy:** dispatch ~$5 5-batch CLEAN AFTER user tops up OpenAI quota. If F_MH stays ≤4% → REJECT permanently. If F_MH 5-8% → REJECT stands (still below KG+MAP). If F_MH ≥8% → re-evaluate gates (unlikely).
  - **Paper §5 third revision needed** (cumulative Wave A/B/C): replace "composability closes 41% MemOS gap" → "26% closure via single best opt-in; F_MH retrieval-stage ceiling discovered; orthogonal-stage Q3 in development to break ceiling"
  - **GTM messaging update:** don't claim triple/composability for F_MH. Concrete narrative: "best opt-in (KG+MAP) closes 26% F_MH gap; orthogonal-stage iterative retrieval predicted to close additional 15-25% (Q3 development)"
- **NÃO FAZEMOS:**
  - Default-enable Triple combo (PR #394 opt-in only, REJECT default)
  - Claim "composability solves F_MH gap" em qualquer material novo (refuted 3× now: KG+MQ overlap, KG+MAP partial, Triple regression)
  - Stack additional retrieval-stage mechanisms para F_MH (Wave C is the empirical falsification)
  - Use single-batch Wave C result (2.00% F_MH) as headline magnitude — partial 2/5 only; await re-run for magnitude certainty (mechanism conclusion stands regardless)
  - Skip preflight billing on bench dispatch — Wave C 011+016 validated preflight saves compute when quota exhausted
  - Re-run Wave C without OpenAI quota top-up — fast-fail expected (already 429 insufficient_quota)
- **Cross-links:** PR #394 (Wave C triple), #393 (Q3 Iterative spec), #390 (Wave B KG+MAP), #389 (Wave B KG+MQ), #379/#385/#386 (Lab Q1 standalone knobs), memory `[[wave-c-triple-reject-fmh-ceiling-found]]`, `[[wave-c-triple-fmh-cap-by-mq-kg-overlap-confirmed]]`, `[[openai-insufficient-quota-needs-fast-fail-not-backoff]]`, `[[preflight-billing-saves-batches-not-just-time]]`, `[[wave-c-triple-latency-3-7x-overhead]]`, `[[2-batch-partial-still-informs-mechanism-not-magnitude]]`, D68.
- *Origem:* sessão 2026-05-29 evening BRT — agent `acc6dd1377940d6ff` ran ~79min, $5 spent (OpenAI quota exhausted mid-run), PR #394 merged 22:55 UTC. Wave C ceiling discovery is strategic inflection — research focus shifts from composability stacking to orthogonal-stage mechanisms (Iterative Retrieval Q3 + Backbone Matrix in-flight).

---

#### D70 — Gemini-3-flash ship opt-in primary recommendation

- **Context:** PR #397 Backbone Matrix — Gemini-3-flash-preview 5-batch validado SOTA: Overall 63.28% (+20.73pp vs MemOS) + MA 88.42% (+32.74pp vs MemOS) com o mesmo pipeline Phase H v2 baseline. Comparado a gpt-4.1-mini default: +11.60pp Overall + +15.08pp MA, 60% mais barato por query.
- **Decisão:** Ship Gemini-3-flash-preview como opt-in primary recommendation via `NOX_ANSWER_BACKBONE=gemini-3-flash-preview`. Default OFF — gpt-4.1-mini permanece default até: (a) 30-day prod stability, (b) LoCoMo e2e Gemini-3-flash validation, (c) Gemini-3-flash GA (sem "preview" tag). Default switch gateado em Gemini-3-flash GA.
- **Rationale:**
  - +11.60pp Overall + +15.08pp MA vs gpt-4.1-mini a mesma dependência Gemini-embed
  - 60% cheaper per query vs gpt-4.1-mini
  - "preview" tag = risco de deprecação antes Q3; não assumir estabilidade de produção
  - Compõe com Wave A/B/C knobs (pipeline stage diferente — orthogonal)
  - Backbone upgrade é cheapest remaining F_MH lever (D69 discovery): frontier reasoning over our retrieval pipeline
- **Aplicação operacional:**
  - Documentar `NOX_ANSWER_BACKBONE=gemini-3-flash-preview` em README opt-in section + api-reference
  - GTM messaging: "60% cheaper + 11pp accuracy lift (opt-in)" — não afirmar como default
  - Paper §5: adicionar §5.3 Backbone Sensitivity com Backbone Matrix 5-batch table
  - Gate default switch: monitorar Gemini-3-flash GA announcement + LoCoMo e2e result (PR #396/#400/#404)
- **NÃO FAZEMOS:**
  - Default-switch para Gemini-3-flash antes de GA + cross-bench validado
  - Dropar gpt-4.1-mini default antes de Gemini-3-flash production-stable
  - Afirmar "Gemini-3-flash-preview é production-ready" sem qualificação "preview/opt-in"
  - Usar Gemini-3-flash-preview como backbone em benchmarks comparativos sem declarar explicitamente (honestidade metodológica)
- **Cross-links:** PR #397, memory `[[backbone-matrix-gemini-3-flash-overall-ma-sota]]`, D67 (portability), D69 (Q3 Iterative Retrieval como complemento orthogonal-stage).
- *Origem:* sessão 2026-05-29 evening BRT — Backbone Matrix 5-batch validation.

---

#### D71 — Production SOTA dimensions cravadas como GTM differentiators canônicos

- **Context:** PR #403 Latency/cost/footprint measurement bench. Números medidos: KG path p50 2.5ms / p95 6.1ms (sub-10ms class); retrieval $0.0000013/query; KG path $0.00/query (vs Mem0 $0.001/query = 769× mais caro); RSS idle 399MB; scaling +15MB 10× concurrent; arquitetura single-process self-hosted (vs Zep/Mem0/MemOS multi-service).
- **Decisão:** Cristalizar 4 production SOTA claims como GTM differentiators canônicos. Publicar em README + COMPARISON.md + COMPETITIVE-POSITIONING.md:
  1. **Sub-10ms KG path** (2.5ms p50 / 6.1ms p95) — latency class única vs market
  2. **$0/query KG path** (SQL+regex, zero LLM cost) — competitor-uncontested
  3. **769× mais barato** que Mem0 em retrieval (Gemini embed path $0.0000013 vs Mem0 $0.001)
  4. **Single-process self-hosted** (399MB RSS idle) — ops simplicity vs multi-service competitors
- **Rationale:**
  - Production-side metrics são competitor-uncontested: Mem0/MemOS/Letta/Zep não publicam latency breakdown
  - $0/query KG path é genuinamente único — resto do mercado é SaaS ou compute-paid
  - Sub-10ms p50 KG path = latency class diferente de hybrid (529ms p50)
  - Self-hosted single-process = ops simplicity advantage tangível e auditável
- **Aplicação operacional:**
  - README: adicionar "Production performance" section com 4 claims + metodologia (n=50 concurrent)
  - COMPARISON.md: adicionar coluna latency/cost/footprint vs Mem0/Zep/MemOS/Letta
  - COMPETITIVE-POSITIONING.md: seção "Production ops" com 4 differentiators
  - Paper §5: adicionar §5.4 Production Performance com metodologia bench PR #403
- **NÃO FAZEMOS:**
  - Afirmar "nox-mem bate Zep" em standard hybrid 529ms vs Zep <100ms (Zep claim unverified percentile; framing honesto: "KG path 2.5ms vs Zep unverified <100ms claim")
  - Anunciar standard hybrid p50 529ms como SOTA (Gemini API domina; local embed mudaria números)
  - Afirmar cost/footprint superiority sem metodologia explícita e data do bench
- **Cross-links:** PR #403, memory `[[production-sota-latency-cost-2026-05-30]]`.
- *Origem:* sessão 2026-05-30 ~02:00 UTC — production bench measurement.

---

#### D72 — Classical multi-hop QA dual SOTA cravado (MuSiQue + HotPotQA) + EverMemBench F_MH paradox RESOLVIDO

- **Context:** PRs #407 + #408 — MuSiQue F1 58.62% (+22.82pp vs IRCoT iterativo, +8.92pp vs EX(SA) supervisionado) + HotPotQA ans_F1 73.37% (acima do DPR+FiD reader SOTA range 65-72%). Ambos sem treinamento especializado. Validação dual-benchmark em datasets públicos reproduzíveis. Resolve o paradoxo EverMemBench: F_MH gap de -13 a -16pp no EverMemBench NÃO é fraqueza de reasoning multi-hop — nox-mem é SOTA em multi-hop QA clássico; o gap é estrutural ao corpus EverMemBench (longos conversation chains + scoring estrito).
- **Decisão:**
  - Cristalizar "SOTA em classical multi-hop QA sem treinamento especializado" como claim canônico (dual-benchmark validated = strongest claim type).
  - **Reframe Q3 priorities:** Q3 IterB (ReAct) ainda relevante para EverMemBench-specific F_MH challenge — mas NÃO é indicador de weakness em multi-hop reasoning em geral.
  - **Atualizar GTM messaging:** substituir "F_MH gap indica weakness multi-hop" por framing correto: "SOTA em classical multi-hop (MuSiQue+HotPotQA); EverMemBench F_MH gap é desafio estrutural de corpus long-chain, não de reasoning".
- **Rationale:**
  - Dual benchmark validation = forma mais forte de SOTA claim
  - Ambos benchmarks públicos + reproduzíveis com metodologia documentada
  - Single-shot architecture supera métodos iterativos (IRCoT) e supervisionados (EX(SA)) — portabilidade metodológica confirmada
  - MuSiQue F1 58.62%: IRCoT baseline 35.80%, EX(SA) supervised 49.70% — gap vs ambos substancial
  - HotPotQA ans_F1 73.37%: DPR+FiD reader SOTA 65-72% — supera reader-level SOTA
  - Mecanismo: KG path retrieval + hybrid + compositional answer generation — arquitetura não-especializada
- **Aplicação operacional:**
  - GTM messaging: "SOTA em classical multi-hop QA (MuSiQue + HotPotQA) sem treinamento especializado"
  - Paper: adicionar §5.2 Classical Multi-hop QA SOTA + §5.5 EverMemBench F_MH paradox resolution
  - README + COMPARISON.md: seção "Multi-hop reasoning" com MuSiQue + HotPotQA numbers
  - Memory update: substituir `[[f_mh-retrieval-bound-not-generation]]` com framing refinado (retrieval-bound em EverMemBench corpus specifically, não em classical multi-hop)
  - Não citar "F_MH retrieval-bound" lesson sem qualificação LoCoMo+MuSiQue+HotPotQA refinement
- **NÃO FAZEMOS:**
  - Afirmar "F_MH SOTA no EverMemBench" — esse gap persiste (estrutural ao corpus)
  - Citar lesson anterior "F_MH retrieval-bound" sem refinamento (era válida para EverMemBench specifically, não para classical multi-hop)
  - Apresentar EverMemBench F_MH gap como indicador de reasoning weakness em talks/paper/GTM
  - Reportar MuSiQue/HotPotQA sem declarar metodologia (sem fine-tuning, Phase H v2 + KG path pipeline)
- **Cross-links:** PR #407 (MuSiQue), #408 (HotPotQA), memory `[[musique-sota-crushing-beats-ircot-ex-sa]]`, `[[hotpotqa-full-73-37-above-dpr-fid-sota]]`, `[[evermembench-fmh-resolved-as-corpus-structural-not-reasoning-weakness]]`, D69 (Q3 Iterative Retrieval reframe), D73 (mechanism class refinement).
- *Origem:* sessão 2026-05-30 07:00-11:30 UTC — MuSiQue 4.3h eval + HotPotQA 8h09m eval.

---

#### D73 — Q3 Iterative Retrieval mechanism class refinement: Self-Ask (F_HL) vs ReAct (F_MH)

- **Context:** PR #406 Q3 IterC POC Self-Ask 5-batch — F_HL +35.84pp BREAKTHROUGH (synthesis/high-level queries beneficiam de parallel sub-question decomposition) mas F_MH -0.40pp (zero lift em multi-hop chaining). Mechanism class distinction empiricamente validada: (A) parallel sub-question decomposition (Self-Ask) → ajuda synthesis, NÃO ajuda multi-hop chains; (B) sequential multi-round retrieve-reason (ReAct) → canonical para multi-hop chains. PR #393 spec Q3 IterB (ReAct) hipótese refinada por D72: urgência menor pois multi-hop reasoning broadly é SOTA (MuSiQue+HotPotQA); IterB ainda relevante especificamente para EverMemBench F_MH structural challenge.
- **Decisão:**
  - **Ship Q3 IterC opt-in** para F_HL synthesis use case via `NOX_ITERATIVE_RETRIEVAL=self-ask`. F_HL +35.84pp valida hipótese de decomposição paralela para synthesis queries.
  - **Q3 IterB (ReAct) permanece como candidato F_MH para EverMemBench specifically.** POC ainda vale $10-15 para confirmar/refutar — mas com urgência reduzida pós-D72 (multi-hop reasoning broadly RESOLVIDO via MuSiQue+HotPotQA SOTA).
  - **Refinamento da PR #393 spec:** separar IterB (ReAct, F_MH target) e IterC (Self-Ask, F_HL target) como sub-specs independentes com mecanismos distintos.
- **Rationale:**
  - Q3 IterC empiricamente wrong mechanism para F_MH (zero lift confirmado 5-batch)
  - Q3 IterC right mechanism para F_HL (35.84pp lift — maior single-mechanism F_HL lift ever observed)
  - Mechanism class distinction: sub-query decomposition converge para mesma vizinhança de first-hop que KG path (overlap) — não adiciona bridge entities para second-hop. ReAct loop explicitamente busca bridge entities via sequential reason → retrieve.
  - Per D72, EverMemBench F_MH gap é structural corpus challenge — IterB POC valor informativo (refuta/confirma) mas não resolve reasoning weakness (já não há)
  - F_HL +35.84pp é actionable: users que fazem synthesis/summarization queries terão ganho massivo opt-in
- **Aplicação operacional:**
  - Documentar `NOX_ITERATIVE_RETRIEVAL=self-ask` como F_HL opt-in em README + api-reference
  - PR #393 spec: split em §IterB (ReAct, F_MH EverMemBench) + §IterC (Self-Ask, F_HL synthesis) com mecanismos separados
  - GTM messaging: "F_HL synthesis mode (opt-in): +35.84pp accuracy em queries de síntese e alto nível"
  - Q3 timeline revisado: IterC shipped (opt-in); IterB POC budget $10-15 alocável sob demanda
  - Paper: citar IterC resultado em §5 como evidence de mechanism class distinction (empirical)
- **NÃO FAZEMOS:**
  - Ship Q3 IterC para F_MH workloads (wrong mechanism — zero lift confirmado)
  - Cancelar Q3 IterB POC (ainda relevante para EverMemBench F_MH specifically)
  - Afirmar "parallel decomposition fecha F_MH gap" (refutado empiricamente)
  - Tratar IterB e IterC como variantes da mesma spec (mecanismos fundamentalmente distintos)
- **Cross-links:** PR #406 (IterC POC), #393 (spec Q3), memory `[[q3-iterC-poc-self-ask-f-hl-breakthrough]]`, `[[orthogonal-stage-hypothesis-needs-mechanism-class-refinement]]`, D69 (Q3 elevado post-Wave C), D72 (F_MH paradox resolution reduz urgência IterB).
- *Origem:* sessão 2026-05-30 03:00-04:00 UTC — Q3 IterC POC 5-batch results.

#### D74 — Q3 IterB ReAct breaks F_MH ceiling on best backbone (D69 ceiling REFINED, NOT falsified)

- **Context:** PR #419 Q3 IterB ReAct 5-batch (n=3121, batches 004/005/010/011/016) on Gemini-3-flash bare baseline (D70 strongest available backbone). Two parallel verdicts: (A) vs gpt-4.1-mini Phase H v2 (project convention baseline): F_MH +4.82pp, Overall +11.02pp, MA +11.55pp — 4/4 gates PASS (SHIP_DEFAULT_CANDIDATE if confounding with backbone allowed). (B) vs gemini-3-flash bare (D70 backbone baseline): **F_MH +2.01pp clean ReAct lift** (6.02% → 8.03%), Overall -0.58pp (within 5-batch noise CI ±1.5pp), MA composite -3.53pp BORDERLINE-FAIL (similar Phase G rerank trade-off). Wave A/B/C ceiling 7.25% (D69) BROKEN by +0.78pp standalone. **D72 narrative refined:** F_MH still largely structural on EverMemBench, MAS orchestration adds +2pp on top of strongest backbone.
- **Decisão:**
  - **Ship Q3 IterB opt-in** via `NOX_ITERB_GEMINI=1` (and equivalent for gpt-4.1-mini backbone). MA -3.53pp trade-off makes default-on unsafe.
  - **D69 F_MH ceiling status: REFINED, NOT falsified.** Single-stage retrieval ceiling (KG+MAP+MQ triple) confirmed at 7.25%. Orchestration-stage ReAct loop adds ~+2pp on top of any backbone. F_MH gap remaining (~6pp to MemOS) treated as structural challenge of EverMemBench's chain length × cross-session compression — addressable only via composability (IterB + Wave A/B/C single-stage knobs).
  - **Composability matrix becomes Q1 priority.** Predict IterB additive (or sub-additive) with KG path (+2.81pp) / AC (+2.01pp) / MQ (+3.61pp). Pessimistic projection: IterB + Wave C triple = ~12.07% F_MH = ~41% MemOS gap closure. ⚠️ **CAVEAT 2026-05-31 (R0 sanity PR #423):** KG path component of composability projection REFUTED on Gemini-3-flash backbone — F_MH delta -0.01pp (mean 6.02% = identical to bare). +2.81pp lift was backbone-specific to gpt-4.1-mini. AC + MQ backbone-portability re-baseline in progress (Wave 2 Phase 1.5). See `[[kg-path-backbone-dependent-no-replicate-gemini-3-flash]]`. Net composability projection downgraded pending AC + MQ re-baseline outcomes.
- **Rationale:**
  - +2.01pp clean lift on best backbone = ReAct mechanism load-bearing (not artifact of weak baseline).
  - Two-baseline honest framing (vs H v2 AND vs gemini-3-flash bare) prevents the conflated +4.82pp claim from over-anchoring. Same lesson cravada `[[honest-cross-baseline-framing]]`.
  - 99.6% IterB applied (3107/3121), mean 4.25 rounds, 99.5% terminated `answer`, round-2 chunk overlap mean 0.257 (LOW — ReAct exploring NEW evidence, sweet spot). Set E instrumentation confirms mechanism healthy.
  - MA -3.53pp borderline-fail acceptable for opt-in but disqualifies default-on (paying noise-Overall for F_MH lift only worth it when user opts in for multi-hop workloads).
  - Cost $0.00295/q within $0.005 budget = ship-economic. 5940ms p50 latency acceptable for offline analytics (not real-time chat).
- **Aplicação operacional:**
  - GTM messaging: "F_MH ceiling broken +2.01pp clean lift via ReAct on best backbone (opt-in)"
  - Paper §5 fourth revision: add IterB section + composability matrix + dual-baseline reporting table
  - README + COMPARISON.md + COMPETITIVE-POSITIONING.md: add 11th SOTA-tier dimension (F_MH ceiling break)
  - ROADMAP v5.0: Q3 IterB graduates from "research" to "available opt-in feature"; composability validation runs in Q1 (next milestone)
  - Spec PR #393: §IterB ReAct production-ready (was POC-stage)
- **NÃO FAZEMOS:**
  - Ship IterB default-on (MA -3.53pp trade-off; users must opt-in)
  - Conflate +4.82pp (vs H v2 weak baseline) with +2.01pp (clean ReAct lift) in GTM messaging
  - Claim "F_MH ceiling DESTROYED" (it's broken by +0.78pp on best backbone — real but modest)
  - Treat IterB + Wave C composability as additive without empirical 5-batch validation
  - Abandon Wave A/B/C single-stage knobs (they remain composable foundations for stacking with IterB)
- **Cross-links:** PR #419 (5-batch IterB Gemini-3), PR #414 (IterB harness), PR #406 + D73 (sibling IterC Self-Ask F_HL), PR #395 + D69 (Wave A/B/C ceiling), PR #377 (Phase H v2 baseline), PR #397 + D70 (Gemini-3-flash backbone), D72 (F_MH paradox resolution context), arxiv:2210.03629 (ReAct paper Yao et al. 2022), memory `[[q3-iterB-fmh-ceiling-broken-2pp]]`, `[[honest-cross-baseline-framing]]`, `[[preflight-must-validate-both-backbones]]`, `[[tmux-survived-zero-socket-drops]]`, `[[reused-fresh-clone-symlink-pattern]]`.
- *Origem:* sessão 2026-05-30 20:02-22:29 UTC — Q3 IterB POC 5-batch results vs both baselines; PR #419 merged a0ddaae via squash + admin override (npm audit pre-existing astro/starlight transitive vulns unrelated).

#### D75 — Wave 2 Phase 1.5 retrieval-stage composability CLOSED on Gemini-3-flash (D74 projection partially refuted)

- **Context:** Wave 2 Phase 1 R0 sanity (PR #423) + Phase 1.5 re-baseline AC (PR #424) + MQ (PR #425) on Gemini-3-flash 5-batch CLEAN (n=3,121, batches 004/005/010/011/016 — same as PR #419). All three single-stage retrieval-knob standalones FAIL gate +1.5pp F_MH:
  - KG path: F_MH **-0.01pp** (R0 PR #423; 95% CI [3.00, 9.04])
  - AC threshold=5: F_MH **+0.81pp** (PR #424; CI [4.62, 9.03])
  - MQ standalone: F_MH **+1.21pp borderline 0.29pp short** (PR #425; CI [4.99, 9.48])
  - **3-knob sum +2.01pp = 24% of D74 pessimistic projection +8.43pp**
- **Cross-backbone transfer pattern (NEW empirical insight):** ~24-40% transfer rate from gpt-4.1-mini to Gemini-3-flash for retrieval-stage knobs (KG 0% / AC 40% / MQ 34%). Wave A knob lifts measured on gpt-4.1-mini are NOT backbone-invariant.
- **MQ MA backbone flip sub-finding:** MQ on Gemini-3-flash PRESERVES MA composite +0.12pp + MA_U +3.10pp (strongest MA gain Wave 2). On gpt-4.1-mini MQ regressed MA -1.38pp. Multi-axis backbone-conditional behavior — paper-worthy.
- **Architectural lock (load-bearing for paper §5 v5):** PR #419 IterB adapter deliberately short-circuits Wave A knobs via explicit guards at `eval/evermembench/adapter_nox_mem.py` lines 2736 (MQ) / 2906 (KG) / 3063 (rerank) `if not iterb_used_path:`. Composability NOT possible via env vars AS-IS. Wave 2 Phase 2 Capstone (PR #426 draft) patches 2/3 guards (KG + rerank; MQ kept — subsumed by ReAct sub-queries).
- **Decisão:**
  - **Wave 2 retrieval-stage composability path CLOSED.** Single-stage knob stacking on Gemini-3-flash bounded at ~+1.2pp ceiling per knob, aggregate ~+2pp.
  - **IterB ReAct (+2.01pp clean, D74) remains the only validated F_MH lever on Gemini-3-flash.**
  - **Phase 2 Capstone (PR #426 in flight tmux `wave2-capstone-7a1cadf2` PID 2194486 ETA 24-36h)** tests orchestration-stage composability via 2-guard removal patch. Will decide D76 on completion.
  - **Paper §5 v5 reframe required:** composability matrix moves from "projected" to "empirically measured per backbone". Honest negative-result section.
- **Rationale:**
  - 3 independent retrieval-stage knobs all show ~24-40% transfer — NOT noise, structural backbone-conditional behavior.
  - Hypothesis: Gemini-3-flash native context utilization (window + attention + filtering) saturates the knob compensation that Wave A was designed for on gpt-4.1-mini. Compensation mechanisms for weaker backbones diminish on stronger backbones.
  - Same lesson generalizes to future SOTA backbones (Claude Opus 4.7, GPT-5, Gemini 4): retrieval-stage knobs require per-backbone re-baseline before composability claims.
  - Architectural lock (explicit `iterb_used_path` guards) means D74 composability projection assumed both backbone-portability AND architectural composability — neither held by default.
- **Aplicação operacional:**
  - GTM messaging: D74 "composability projection ~33-41% gap closure" REMOVED — replaced with honest "empirically bounded by knob transfer rate × architectural composability". Specific projections reframed as per-backbone measurements.
  - README §F_MH ceiling break: Wave 2 caveat block added (research integrity over inflated claims).
  - Paper §5 v5 (rebuild pending Mon AM): honest negative-result composability section + dual-baseline transfer rate table + architectural lock discovery as scientific contribution.
  - Future spec authoring: when designing new orchestration-stage mechanisms, document upfront whether they short-circuit or compose with existing knobs.
  - D74 composability bullet annotated with R0 caveat (see line 1287 D74 section above).
- **NÃO FAZEMOS:**
  - Claim composability matrix lifts on Gemini-3-flash without 5-batch re-baseline per knob on that backbone.
  - Re-attempt R0/AC/MQ standalone composability on Gemini-3-flash without different mechanism class (orchestration-stage, synthesis-stage, profile-chunk).
  - Switch backbone trade to gpt-4.1-mini just to recover composability lifts — D70 ship opt-in Gemini-3-flash GTM position is load-bearing and not negotiable for this purpose.
  - Inflate Wave 2 NO-REPLICATE as "scientific contribution" while suppressing the architectural lock — both must be reported.
  - Treat capstone (PR #426) outcome as predetermined. ANY of 4 outcomes (DEFAULT / OPT-IN / CLOSED / INTERFERENCE) is valid honest finding.
- **Cross-links:** PR #423 (R0 KG), PR #424 (AC re-baseline), PR #425 (MQ re-baseline), PR #426 (capstone draft in flight), PR #379 (KG path gpt-4.1-mini original +2.81pp), PR #381 (AC gpt-4.1-mini original +2.01pp), PR #385 (MQ gpt-4.1-mini original +3.61pp), PR #397 + D70 (Gemini-3-flash backbone), PR #419 + D74 (IterB only validated Gemini F_MH lever — composability projection partially refuted), memory `[[kg-path-backbone-dependent-no-replicate-gemini-3-flash]]`, `[[wave-2-phase-1-5-ac-mq-no-replicate-gemini-3-flash]]`, `[[iterB-architectural-lock-short-circuits-wave-a-knobs]]`, `[[wave-2-composability-matrix-plan]]`, `[[single-knob-lifts-are-backbone-conditional]]`, `[[honest-cross-baseline-framing]]`.
- *Origem:* sessão 2026-05-31 13:25-18:30 BRT — agents `a813d2410595bb291` (R0) + `ac84ec72cc649d2c8` (AC) + `a9bddaeef071a268e` (MQ) + harvester `a822874b3f87602fc` (PRs #424+#425) + capstone setup `ad607d7734881c5f5` (PR #426 draft). Wave 2 Phase 1 + Phase 1.5 closed. Phase 2 Capstone in flight (D76 pending).

#### D76 — Wave 2 Phase 2 Capstone ABORTED (Hostinger infrastructure throttling, INDETERMINATE outcome)

- **Context:** Wave 2 Phase 2 Capstone (IterB ReAct + KG + rerank composability test, PR #426 draft) dispatched Sun 2026-05-31 17:40 BRT on Hostinger VPS 187.77.234.79. Two reboots + multiple resume attempts + yaml patches (search timeout 120s→600s, concurrency 3→1) + bash cost-tracking fixes (commit dcc1e34) + .env ONNX thread caps (ORT/OMP/MKL/OpenBLAS=2) + taskset CPU pinning + openclaw-gateway+warmup disable applied. Despite all mitigations:
  - Hostinger CPU steal oscillated 8.5% → 97% → 21% → 51-71% (sustained host-level throttling, anti-abuse scanner triggered)
  - Batch 005 ran ~23h after final yaml patch with **0 questions completed** of 50
  - Queries (e.g. F_SH_Top005_040/041/042) reached retry 19/20 with 300s delay each
  - Mathematical impossibility: 20 retries × (600s timeout + 300s delay) = 5h max per query × 50 questions × 4 batches = 1000h ceiling under sustained throttle
  - **48h elapsed total** (Sun 17:40 → Tue ~17:55 BRT) with only batch 004 analysis.txt preserved (completed pre-second-reboot)
  - **~$20-25 spent** on retry burn without producing aggregable 5-batch data
- **Decisão:**
  - **CAPSTONE ABORTED, OUTCOME INDETERMINATE.** Bench technically incomplete (1/5 batches, n=49 of n=3,121). NOT statistically valid for 5-batch gate. NOT publishable as orchestration composability finding.
  - **Wave 2 CLOSED via Phase 1.5 findings + architectural lock discovery.** Single-stage retrieval-knob composability proven non-portable to Gemini-3-flash backbone (D75). IterB ReAct (D74) remains the sole validated F_MH lever. Composability projection from D74 reframed as "theoretical and architecturally blocked by design."
  - **Capstone batch 004 (n=49) preserved on disk** for future re-run if/when stable infrastructure available. Workdir: `/root/.openclaw/evermembench-runs/capstone-iterB-triple-004-1780260019/analysis.txt`.
  - **PR #426 abandoned as draft** with abandon comment + cross-link to D76. NOT merged. Branch preserved as `wave-2/capstone-iterB-triple-7a1cadf2` for future revisit.
  - **Paper §5 v5 rebuild prioritized** (Task #102) — incorporate D75 + D76 + architectural lock + 3-knob NO-REPLICATE pattern as honest scientific contribution.
- **Rationale:**
  - Hostinger steal 51-97% sustained makes ONNX rerank (CPU-bound bge-reranker-v2-m3) impossible to complete batches under cost budget. Not a code problem, an infrastructure problem.
  - Three independent mitigation rounds tried — pinning, capping, restarting, yaml patching, rebooting. None bridged the gap.
  - Continuing to retry would burn budget without producing decision-grade data. Pragmatic shutdown protects research credibility.
  - Wave 2 Phase 1.5 + architectural lock + IterB D74 deliver substantial publishable findings (~5 new insights). Capstone would have added 1 more (13th SOTA-tier dim or honest negative result) — non-load-bearing for paper §5 v5.
  - Honest negative-finding framing of capstone abort STRENGTHENS paper as research integrity proof: "we tried, infrastructure constraints, here is what we learned."
- **Aplicação operacional:**
  - PR #426 comment with link to D76 + abandon explanation + batch 004 partial data note
  - Task #102 paper §5 v5 rebuild incorporates D75 + D76 + architectural lock discovery + 3-knob backbone-conditional pattern as section
  - GTM messaging: 12 SOTA dims canonical (no 13th). Composability matrix presented as honest empirical study (per backbone × per knob measured matrix replacing original projection table).
  - ROADMAP v5.1: capstone moved to "deferred to future stable infrastructure" parking lot. Q1 priority shifts to HyDE bench (different mechanism family, PR #415 deferred) + Claude Sonnet 4.6/Opus 4.7 backbone bench (needs key rotation).
  - Memory crystallized: `[[capstone-aborted-hostinger-throttling-indeterminate]]` (this finding) + `[[ort-num-threads-cap-during-capstone]]` (mitigation playbook) for future infra contingency reference.
- **NÃO FAZEMOS:**
  - Re-run capstone on Hostinger without verified host SLA upgrade (dedicated CPU plan or migration to different provider with steal SLO)
  - Claim 13th SOTA-tier dimension from capstone (batch 004 alone is not 5-batch valid)
  - Present composability matrix in paper as "completed" — must be honest about retrieval-stage scope only
  - Conflate "infrastructure abort" with "scientific failure" — these are categorically different (D75 documents real scientific finding; D76 documents infrastructure constraint)
  - Burn more budget retrying capstone in current Hostinger environment
- **Cross-links:** PR #426 (capstone draft, abandoned), PR #423 (R0 KG NO-GO), PR #424 (AC NO-GO), PR #425 (MQ NO-GO), PR #419 + D74 (IterB only validated lever), PR #397 + D70 (Gemini-3-flash backbone), D75 (Phase 1.5 closure prerequisite), memory `[[capstone-aborted-hostinger-throttling-indeterminate]]`, `[[ort-num-threads-cap-during-capstone]]`, `[[iterB-architectural-lock-short-circuits-wave-a-knobs]]`, `[[wave-2-phase-1-5-ac-mq-no-replicate-gemini-3-flash]]`, `[[wave-2-composability-matrix-plan]]`.
- *Origem:* sessão 2026-05-31 17:40 BRT → 2026-06-02 ~17:55 BRT (~48h elapsed). Agents: `ad607d7734881c5f5` (original capstone), `ac838a0621554c73b` (resume 1), `a495bbebb6426e016` (resume 2 + yaml patch), manual cleanup direct. Two Hostinger VPS reboots. Three resume attempts. Final abort decision Tue 2026-06-02 ~17:55 BRT after batch 005 confirmed 0/50 questions completed in 23h.
