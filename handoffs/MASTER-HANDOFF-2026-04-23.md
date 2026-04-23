# MASTER HANDOFF — memoria-nox (2026-04-23)

**Documento consolidado. Leitura única pra próxima janela retomar sem gaps.**

**Data da consolidação:** 2026-04-23 (fim do dia, ~4h15min de dev puro + triagens)
**Versão do sistema:** nox-mem schema v10, OpenClaw 2026.4.21
**Sessão anterior relevante:** 2026-04-21 (audit sistêmica v3.6d), 2026-04-22 (migração CLI backend)

---

## TL;DR EXECUTIVO

Dia de transformação do nox-mem de sistema "flat" pra estrutura tipada avançada. **6 fases completadas**:

1. 🔧 Infra recovery — double-failure (auth login overwrite + graph-memory zombie 4d)
2. ✅ Fase 1.7b-a — Typed retention matrix (schema v8)
3. ✅ IM — Import 147 docs dos 10 projetos + raiz (chunks 2073→6301)
4. 🛡️ Stabilization sprint — 10 fixes pós 5-agent review
5. ✅ Fase 2 — Graphify scale 9 repos (1046 graph_node chunks)
6. ✅ Fase 1.7b-b — Salience formula (shadow-mode, schema v9)
7. 🔧 Fase 1.7b-c — Compiled truth foundation (schema v10)

**Chunks totais 2073 → 7367** (+255%). Schema v7 → v10. Backend: Claude CLI OAuth (zero API bill). 100% vectorized, canary verde, commits pushed.

**Próxima sessão (pré-planejada)**: fechar 1.7b-c (migração massiva `memory/*.md` → `entities/`) **OU** partir pra Fase 3 (HD Mac rsync + enrichment tiered).

---

## 1. SANITY CHECK PRA ABRIR A PRÓXIMA SESSÃO

```bash
# 1. Health — deve ter todos os campos novos
ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq "{total: .chunks.total, vectorCoverage, retention: .retentionDistribution, salience: .salience, section: .sectionDistribution}"'
# Esperado: total=7367, embedded=7367, salience.mode=shadow, sectionDistribution.compiled=2

# 2. Canary 24h — deve ter >40 OKs consecutivos
ssh root@100.87.8.44 'tail -5 /var/log/nox-canary.log'

# 3. Gateway e patches
ssh root@100.87.8.44 'systemctl is-active openclaw-gateway; bash /root/.openclaw/scripts/check-monkey-patch.sh && echo patch-ok; bash /root/.openclaw/scripts/check-gm-messages.sh && echo gm-ok'

# 4. Schema version = 10
ssh root@100.87.8.44 'sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db "SELECT value FROM meta WHERE key=\"schema_version\";"'
```

Se algum retornar red, abrir debug antes de qualquer trabalho novo.

---

## 2. ROADMAP STATUS — ONDE ESTAMOS

### ✅ CONCLUÍDO (cumulativo)

| Fase | Done | Evidência |
|------|------|-----------|
| 1 / 1.5 / 0.5 / 1.6 / 1.7a / D1-D4 | ≤ 2026-04-21 | Ver MASTER-HANDOFF-2026-04-21.md |
| CLI backend migration | 2026-04-22 | plans/2026-04-22-* |
| Double-failure recovery | 2026-04-23 | docs/INCIDENTS.md |
| **1.7b-a Typed retention** | **2026-04-23** | Schema v8, 6301 chunks backfilled |
| **IM Import repos** | **2026-04-23** | 147 docs, zero-cost bonus retention |
| **Stabilization sprint** | **2026-04-23** | 10 fixes, 5-agent review APPROVE |
| **Fase 2.5 graph-memory** | **2026-04-23** (patched) | gm_messages populando (era zombie) |
| **Fase 2 Graphify scale** | **2026-04-23** | 9 repos, 1046 graph_node chunks |
| **1.7b-b Salience shadow** | **2026-04-23** | Schema v9, baseline 207 promote |
| **1.7b-c Foundation** | **2026-04-23** | Schema v10, 2 entities piloto |

### 🔧 PENDENTE (ordem)

| # | Nome | Esforço | Bloqueio |
|---|------|---------|----------|
| **1.7b-c close** | Migração massiva `memory/*.md` → `entities/` + /memory-recompile skill + section_boost em search (shadow) | 4-6h | — |
| **1.7b-b activation** | Depois de ≥7d baseline → `NOX_SALIENCE_MODE=active` | 5min + observação | 1 semana |
| Fase 3 | HD Mac rsync + enrichment tiered | 1h + rsync | 1.7b-c close (ou paralelo) |
| Fase 4 | Obsidian view-only | 1h | 3 |
| Path B-lite | Semantic reflect cache | 2-3h | telemetria |
| Path C | WAL shipping + cold tier | dias | 4 |
| Fase P | Produtização NOX-Supermem | — | TODO estável 30+ dias (regra Toto) |

### 🟡 Reativo (só se sintoma)

- Path A — Write coordinator (SQLITE_BUSY trigger)
- Issue upstream graph-memory plugin v1.5.8 vs core 2026.4.21

---

## 3. ESTADO ATUAL DO SISTEMA (2026-04-23 fim do dia)

### Infra
- **VPS:** `root@100.87.8.44` (Tailscale) / `187.77.234.79` (público)
- **OpenClaw:** 2026.4.21 + monkey-patch Issue #62028 reaplicado
- **Backend primário:** Claude CLI via OAuth Max (zero API bill)
- **Fallback chain:** claude-cli → openai-codex → gemini/2.5-pro (sem anthropic/*)
- **Gateway uptime:** estável pós fixes de hoje (0 SIGTERM loops)
- **Systemd circuit breaker:** StartLimitBurst=5/300s (previne novos crash loops)

### nox-mem DB
- 7367 chunks / 7367 embedded (100%) / 0 orphans
- Schema v10 (retention_days v8, pain v9, section v10)
- 9 DBs agente (main + 6 personas + atlas/forge etc com cross-agent)
- Last backup: `backups/nox-mem-pre-v10-20260423-1306.db` (133M)

### Distribuições atuais (observability ativa)

```json
"retentionDistribution": {
  "never_decay": 92,     // 17 feedback + 6 person + 61 core tier + 8 entity
  "expiring_30d": 9,
  "expiring_90d": 1954,
  "expiring_365d": 5312,
  "already_expired": 0
}

"salience": {           // shadow-mode (não aplica no ranking)
  "mode": "shadow",
  "promote_candidates": 207,
  "retain": 331,
  "review_needed": 4911,
  "archive_candidates": 1886,
  "mean": 0.1776,
  "median": 0.1601
}

"sectionDistribution": {
  "compiled": 2,
  "frontmatter": 2,
  "timeline": 16,
  "legacy": 7347
}

"knowledgeGraph": { "entities": 402, "relations": 544 }
```

### Canários/crons ativos
- `semantic-canary.sh` `*/30min` (self-heal, 50+ OKs consecutivos)
- `check-discord-heartbeat-validation.sh` `*/30min`
- `check-monkey-patch.sh` `0 * * * *` (hourly integrity check)
- `check-gm-messages.sh` `15 * * * *` (hourly growth SLO)
- `nightly-maintenance.sh` 23:00 (reindex + vectorize + kg-build + consolidate + dedup)
- Logrotate 9 logs nox-*
- Backup diário 02:00 (7d retention)

---

## 4. ARQUIVOS DE CÓDIGO MODIFICADOS HOJE

### Na VPS (`/root/.openclaw/workspace/tools/nox-mem/src/`)

| Arquivo | Novo / Patched | Resumo |
|---------|----------------|--------|
| `db.ts` | Patched | SCHEMA_VERSION 7→10, migrateToV8/V9/V10 (retention_days + pain + section) |
| `retention.ts` | **NOVO** | RETENTION_BY_TYPE map + parseRetentionOverride (30 lines, CRLF-safe) + resolveRetention |
| `salience.ts` | **NOVO** | calculateSalience (recency×pain×importance), classifySalience, inferPain, inferImportance, getSalienceMode |
| `ingest-entity.ts` | **NOVO** | parseEntityFile (3-section) + ingestEntityFile + SECTION_BOOST map |
| `ingest.ts` | Patched | Import retention + salience; INSERT inclui retention_days + pain |
| `graphify-ingest.ts` | Patched | graph_node retention=60d |
| `tier-manager.ts` | Patched | countArchiveCandidates + getRetentionDistribution + getSalienceDistribution + getSectionDistribution + evaluateTiers core-tier preservation |
| `api-server.ts` | Patched | /api/health expõe retentionDistribution + archiveCandidates + salience + sectionDistribution; bind 127.0.0.1 (NOX_API_HOST override) |

### Na VPS (extensions + core)

| Arquivo | Patch |
|---------|-------|
| `/root/.openclaw/extensions/graph-memory/index.ts` | `afterTurn` chama `ingestMessage` inline + `<untrusted-recall>` wrapper em systemPromptAddition |
| `/usr/lib/node_modules/openclaw/dist/restart-stale-pids-BvLkOxHa.js` | `cleanStaleGatewayProcessesSync` retorna `[]` (monkey-patch Issue #62028) |

### Memory/entities piloto (VPS)

- `/root/.openclaw/workspace/memory/entities/agents/nox.md` (8 chunks)
- `/root/.openclaw/workspace/memory/entities/systems/nox-mem.md` (12 chunks)

### Systemd (VPS)

- `/etc/systemd/system/openclaw-gateway.service.d/circuit-breaker.conf` (StartLimitBurst=5/300s)

### Scripts novos (VPS)

- `/root/.openclaw/scripts/check-monkey-patch.sh` (hourly canary)
- `/root/.openclaw/scripts/check-gm-messages.sh` (hourly growth SLO)

### Backups preservados (VPS)

- `/root/.openclaw/workspace/tools/nox-mem/bak-src-v8-20260423-1121/` (src/ antes do 1.7b-a)
- `/root/.openclaw/workspace/tools/nox-mem/backups/nox-mem-pre-v8-20260423-1121.db` (64M)
- `/root/.openclaw/workspace/tools/nox-mem/backups/nox-mem-pre-v9-20260423-1306.db` (133M)
- `/root/.openclaw/workspace/tools/nox-mem/backups/nox-mem-pre-v10-*.db`
- `/usr/lib/node_modules/openclaw/dist/restart-stale-pids-BvLkOxHa.js.bak-prepatch-20260423-1102`
- `/root/.openclaw/extensions/graph-memory/index.ts.bak-pre-ingest-fix-20260423`

---

## 5. COMMITS PUSHED HOJE (10)

```
52f0858 docs(roadmap): Fase 1.7b-c foundation DONE — compiled truth + timeline
f45b7cd docs(roadmap): Fase 1.7b-b DONE (shadow-mode) — salience formula
d45f2d2 docs(roadmap): Fase 2 DONE — 9 repos com código indexados (100% exit)
4e870da docs(roadmap): Fase 2 parcial — 7/~15 repos graphified + ingested
60f8ff4 docs(roadmap): v1.5 — sprint consolidado 2026-04-23 + backlog formal
7a5d533 docs(audit): stabilization sprint pós-1.7b-a (5 agent reviews)
09e765e docs(claude.md): pós-IM + Fase 1.7b-a — 6.3k chunks, retention_days
aaf52bb docs(23-04): double-failure recovery + Fase 1.7b-a typed retention matrix
af8a1aa docs(22-04): migração Claude CLI backend — zero API usage
c587348 docs(claude.md): slim index + detail moved to docs/   ← pré-existente
```

---

## 6. DECISÕES E APRENDIZADOS DO DIA

### Novos princípios confirmados

1. **Shadow-mode é padrão pra features que mudam ranking** — salience não afeta search até ≥7d de baseline + comparação A/B (regra Toto validada na 1.7b-b)
2. **Migrations devem ter narrow catch** — só swallow "duplicate column", não disco cheio/locked (code-reviewer HIGH em 1.7b-a)
3. **Features "DONE" requerem validação de DB state** — log-only validation é falso positivo (aprendido com graph-memory zombie 4 dias)
4. **`<!-- retention: X -->` só em linha isolada** — previne match em docs descritivos
5. **`openclaw models auth *` invalida TANTO o registry QUANTO o monkey-patch** — sempre diff+reapply antes de restart
6. **Core-tier preservation contract** — promoção pra core deve zerar `retention_days` (architect review D2)
7. **5-agent review antes de abrir nova frente grande** — detectou 10 issues reais pós-1.7b-a

### Memórias novas salvas (5 hoje)

- `feedback_openclaw_models_auth_login_removes_registry.md`
- `feedback_models_auth_login_reinstalls_node_modules.md`
- `feedback_heartbeat_regression_false_positive.md`
- `feedback_graph_memory_probe_errors_are_stale.md`
- `feedback_validate_features_with_db_not_logs.md`
- `reference_vps_infra_triage_commands.md`

---

## 7. PRÓXIMA SESSÃO — OPÇÕES DE ENTRADA

### A — Fechar Fase 1.7b-c completa (4-6h, recomendada)

**Escopo:**
1. Script de migração `memory/projects.md` (15+ projects) → `memory/entities/projects/<slug>.md`
   - Parse H2 sections + identify entities mentioned
   - Generate compiled + timeline per entity
   - Dry-run primeiro, validar 2-3 manualmente, batch depois
2. Script similar pra `memory/decisions.md` (135 decisions) — agrupar por entidade mencionada
3. `memory/lessons.md` (45 lessons) → `entities/lessons/*.md` (ou merge em projects)
4. `/memory-recompile <entity>` skill (Gemini Flash-Lite reescreve compiled baseado em timeline)
5. Search ranking aplica `section_boost` em SHADOW MODE (logado, não aplicado 7d)
6. Comparação A/B com top-5 queries típicas

**Ativação salience (1.7b-b)** pode ir junto — `NOX_SALIENCE_MODE=active` + restart.

**Abrir com:**
```bash
cd ~/Claude/Projetos/memoria-nox
cat handoffs/MASTER-HANDOFF-2026-04-23.md | head -100
ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq ".sectionDistribution"'
```

### B — Pular pra Fase 3 (HD Mac rsync, paralela)

**Escopo:** 21GB de `~/Documents` do Mac → rsync pra VPS → graphify incremental + enrichment tiered.

**Risco:** pode gerar volume alto de writes (5000+ nodes). Se SQLITE_BUSY aparecer, ativar Path A reativo.

**Trade-off:** skipa close da 1.7b entirely. Aceitar que 1.7b-c foundation é suficiente e evolução virá orgânica.

### C — Activation 1.7b-b + observação passiva

**Escopo:** apenas ativar salience (`NOX_SALIENCE_MODE=active`) + monitorar 48h impact no search. Zero código novo.

**Risco:** baixo (rollback trivial). Valida que a formula é realmente útil antes de investir em 1.7b-c close.

### Minha recomendação

**Opção A**, porque:
- Foundation 1.7b-c está shipped mas sem content — 95% do valor vem da migração massiva
- `memory/projects.md` de 300+ linhas hoje não é search-friendly (drift de fatos)
- Completar a Fase 1.7b como um todo libera Fase 3 com base sólida
- Salience activation pode ir embutida (ativar no meio da sessão após validar)

---

## 8. COMANDOS ÚTEIS PRA 1.7b-c CLOSE

```bash
# Ingest manual de um entity file (quando criar novos)
ssh root@100.87.8.44 'set -a; source /root/.openclaw/.env; set +a; cd /root/.openclaw/workspace/tools/nox-mem; node -e "import(\"./dist/ingest-entity.js\").then(m => m.ingestEntityFile(process.argv[1])).then(r => console.log(r))" /root/.openclaw/workspace/memory/entities/<path>.md'

# Listar entities ingested
ssh root@100.87.8.44 'sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db "SELECT DISTINCT source_file FROM chunks WHERE section = \"compiled\";"'

# Search priorizando compiled truth (já funciona hoje — score 32+ vs legacy 16)
ssh root@100.87.8.44 'set -a; source /root/.openclaw/.env; set +a; /root/.openclaw/workspace/tools/nox-mem/dist/index.js search "<query>" --limit 5'

# Activation salience (quando baseline tiver ≥7d)
ssh root@100.87.8.44 'sed -i "s/#*NOX_SALIENCE_MODE=.*/NOX_SALIENCE_MODE=active/" /root/.openclaw/.env || echo "NOX_SALIENCE_MODE=active" >> /root/.openclaw/.env; systemctl restart nox-mem-api; sleep 3; curl -s http://127.0.0.1:18802/api/health | jq .salience.mode'
```

---

## 9. CHECKLIST PRA ABRIR AMANHÃ

- [ ] Sanity check (seção 1 deste arquivo)
- [ ] Ler este handoff + roadmap v1.5 section "Fase 1.7b-c"
- [ ] Confirmar estado: 7367 chunks, 100% embedded, canary exit=0
- [ ] Review `memory/entities/agents/nox.md` + `memory/entities/systems/nox-mem.md` pra entender formato antes de migrar massa
- [ ] Decidir: A (1.7b-c close) / B (Fase 3) / C (activation + observação)
- [ ] Executar

---

## 10. CLOSING NOTE

Dia histórico. Saímos de sistema flat com 2073 chunks pra **sistema tiered + typed + compiled-truth-aware com 7367 chunks**. Três fases novas no schema (v8→v10), pipeline de graphify escalado 3→9 repos, 5-agent review fechado com APPROVE, todos os canários hourly novos validando integridade contínua.

Sistema em **estado mais sólido da história do nox-mem**. Pipeline end-to-end validado (docs+código+compiled truth no mesmo hybrid search), zero pendência crítica. Backlog formal de 8 itens agendados pós-Fase 1.7b close.

O Toto topou trabalho denso hoje — retain this pace is unsustainable but the dia foi excepcional. Descansar bem. Amanhã: **1.7b-c close** ou **Fase 3**, sua escolha.

**Próxima janela abre com:** `ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq "{total:.chunks.total,vc:.vectorCoverage,retention:.retentionDistribution,salience:.salience.mode,section:.sectionDistribution}"'`

---

*Documento gerado: 2026-04-23 ~13:15 BRT. Próxima janela recomendada: 2026-04-24 manhã após sanity check.*
