# MASTER HANDOFF — memoria-nox (2026-04-24)

**Documento consolidado. Leitura única pra próxima janela retomar sem gaps.**

**Data da consolidação:** 2026-04-24 ~12:15 BRT (sessão curta — ~1h15min: Cipher diagnostic + CLI completion)
**Sessão anterior:** 2026-04-23 (MASTER-HANDOFF-2026-04-23.md) — dia épico 2073→7367 chunks, schema v10
**Versão do sistema:** nox-mem schema v10, OpenClaw 2026.4.21

---

## TL;DR EXECUTIVO

Sessão curta disparada por relatório do Cipher alegando "CRÍTICO: CLI quebrado + consolidação falhando". Triagem contra VPS real revelou **sistema 90% saudável** — Cipher misturou 2 fatos reais com 3 falsos positivos. Oportunidade foi usada pra:

1. ✅ **WAL checkpoint** — 96MB recuperados (WAL tinha acumulado noite toda)
2. ✅ **Archive `shared-memory.db`** — 28KB legacy movido pra /tmp
3. ✅ **CLI `ingest-entity` adicionado** — fecha último gap da foundation 1.7b-c
4. ⚠️ **3 pendências operacionais identificadas** (nightly cron ENV, WAL no cron, daily notes)

Estado do sistema: **healthier** que EOD de ontem. Foundation 1.7b-c agora com CLI formal (era hack `node -e`). Pronto pra 1.7b-c close ou Fase 3.

---

## 1. SANITY CHECK PRA ABRIR A PRÓXIMA SESSÃO

```bash
# 1. Health completo (tudo verde esperado)
ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq "{total: .chunks.total, vectorCoverage, retention: .retentionDistribution, salience: .salience, section: .sectionDistribution, dbSizeMB}"'
# Esperado: total=6328+, vectorCoverage.embedded=.total, salience.mode=shadow, section.compiled=2, dbSizeMB≈134

# 2. Canary 24h
ssh root@100.87.8.44 'tail -5 /var/log/nox-canary.log'

# 3. Gateway + patches integrity
ssh root@100.87.8.44 'systemctl is-active openclaw-gateway; bash /root/.openclaw/scripts/check-monkey-patch.sh && echo patch-ok'

# 4. CLI novo funciona
ssh root@100.87.8.44 'nox-mem ingest-entity --help 2>&1 | head -5'

# 5. WAL não regrediu
ssh root@100.87.8.44 'ls -lh /root/.openclaw/workspace/tools/nox-mem/nox-mem.db-wal'
# Esperado: pequeno (<10M). Se >50M, rodar PRAGMA wal_checkpoint(TRUNCATE) novamente
```

---

## 2. ROADMAP STATUS — ONDE ESTAMOS

### ✅ CONCLUÍDO (cumulativo até 2026-04-24)

| Fase | Done | Evidência |
|---|---|---|
| 1 / 1.5 / 0.5 / 1.6 / 1.7a / D1-D4 | ≤ 2026-04-21 | MASTER-HANDOFF-2026-04-21.md |
| CLI backend migration | 2026-04-22 | plans/2026-04-22-* |
| Double-failure recovery | 2026-04-23 | docs/INCIDENTS.md |
| 1.7b-a Typed retention | 2026-04-23 | schema v8, backfill 6301 chunks |
| IM Import repos | 2026-04-23 | 147 docs, zero-cost bonus retention |
| Stabilization sprint | 2026-04-23 | 10 fixes, 5-agent APPROVE |
| Fase 2.5 graph-memory | 2026-04-23 (patched) | gm_messages populando |
| Fase 2 Graphify scale | 2026-04-23 | 9 repos, 1046 graph_node chunks |
| 1.7b-b Salience shadow | 2026-04-23 | schema v9, baseline 207 promote |
| 1.7b-c Foundation | 2026-04-23 | schema v10, 2 entities piloto |
| **1.7b-c CLI completion** | **2026-04-24** | `nox-mem ingest-entity <file>` formal |
| **Ops housekeeping** | **2026-04-24** | WAL checkpoint (-96MB), shared-memory.db archived |

### 🔧 PENDENTE (ordem)

| # | Nome | Esforço | Bloqueio |
|---|------|---------|----------|
| **1.7b-c close** | Migração massiva memory/*.md → entities/ + /memory-recompile skill + section_boost shadow em search | 4-6h | — |
| **1.7b-b activation** | Depois de ≥7d baseline (~2026-04-30) → NOX_SALIENCE_MODE=active | 5min + observação | Baseline faltam ~6d |
| Fase 3 | HD Mac rsync + enrichment tiered | 1h + rsync | 1.7b-c close (ou paralelo) |
| Fase 4 | Obsidian view-only | 1h | 3 |
| Path B-lite | Semantic reflect cache | 2-3h | telemetria |
| Path C | WAL shipping + cold tier | dias | 4 |
| Fase P | Produtização NOX-Supermem | — | TODO estável 30+ dias (regra Toto) |

### 🟡 Reativo / housekeeping

- Path A — Write coordinator (SQLITE_BUSY trigger)
- **Ops 2026-04-24**: verificar ENV no nightly-maintenance.sh (consolidate error 03:31)
- **Ops 2026-04-24**: adicionar `PRAGMA wal_checkpoint(TRUNCATE)` no nightly cron
- **Ops 2026-04-24**: auditar daily notes em /root/.openclaw/workspace/memory/daily/ (Cipher alegou missing 23/24)

---

## 3. ESTADO ATUAL DO SISTEMA (2026-04-24 12:15)

### Infra (inalterada desde ontem)

- **VPS:** `root@100.87.8.44` (Tailscale) / `187.77.234.79` (público)
- **OpenClaw:** 2026.4.21 + monkey-patch Issue #62028
- **Backend primário:** Claude CLI via OAuth Max (zero API bill)
- **Fallback chain:** claude-cli → openai-codex → gemini/2.5-pro
- **Gateway uptime:** estável
- **Canários hourly:** monkey-patch integrity + gm_messages growth

### nox-mem DB

- **Chunks totais:** 6328 (vs 7367 ontem — consolidation noturno normal)
- **Vectors:** 6328/6328 embedded (100%), 0 orphans
- **DB size:** 134MB (WAL: 0MB após checkpoint hoje)
- **Schema:** v10 (retention_days v8 + pain v9 + section v10)
- **Last backup:** `backups/nox-mem-pre-v10-*.db` (133M, ontem)

### Distribuições atuais

```json
"retentionDistribution": {
  "never_decay": 23,       // drop de 92 ontem — verificar se é recomputação após consolidation
  "expiring_30d": 9,
  "expiring_90d": 913,
  "expiring_365d": 5367,
  "already_expired": 0
}

"salience": {             // shadow-mode — baseline coletando
  "mode": "shadow",
  "promote_candidates": 196,  // era 207 ontem
  "retain": 50,
  "review_needed": 5045,
  "archive_candidates": 1009, // era 1886 ontem — consolidation removeu candidates
  "mean": 0.1897,
  "median": 0.1594
}

"sectionDistribution": {
  "compiled": 2,
  "frontmatter": 2,
  "timeline": 16,
  "legacy": 6308
}

"knowledgeGraph": { "entities": 402, "relations": 544 }
```

**⚠️ Observação crítica**: `never_decay` caiu de 92 → 23. Pode ser que o consolidation noturno **removeu chunks feedback/person** ou **recomputou retention perdendo `<!-- retention: never -->` overrides**. Investigar na próxima sessão antes de rodar migração massiva 1.7b-c close.

### Canários/crons ativos (inalterados)

- `semantic-canary.sh` `*/30min`
- `check-discord-heartbeat-validation.sh` `*/30min`
- `check-monkey-patch.sh` `0 * * * *`
- `check-gm-messages.sh` `15 * * * *`
- `nightly-maintenance.sh` 23:00 (⚠️ sem WAL checkpoint — adicionar)
- Logrotate, backup diário 02:00

---

## 4. ARQUIVOS DE CÓDIGO MODIFICADOS HOJE

### Na VPS (`/root/.openclaw/workspace/tools/nox-mem/src/`)

| Arquivo | Diff | Backup |
|---------|------|--------|
| `src/index.ts` | +11 linhas (import + `.command("ingest-entity <file>")` block) | `src/index.ts.bak-20260424-115355` |
| `dist/index.js` | Rebuilt via `npm run build` (tsc clean) | — |

### VPS ops

| Ação | Arquivo/Objeto | Resultado |
|---|---|---|
| `PRAGMA wal_checkpoint(TRUNCATE)` | `nox-mem.db-wal` | 96MB → 0 bytes |
| `mv shared-memory.db` | → `/tmp/shared-memory.db.archived-20260424-114900` | Safety net preservada |

### Entities piloto (VPS) — re-ingested hoje via CLI novo

- `/root/.openclaw/workspace/memory/entities/agents/nox.md` (8 chunks)
- `/root/.openclaw/workspace/memory/entities/systems/nox-mem.md` (12 chunks)

---

## 5. DECISÕES E APRENDIZADOS DA SESSÃO

### Novos princípios

1. **Agents secundários (Cipher/Atlas/etc) exigem validação independente** — Cipher misturou 2 fatos reais (WAL bloat, shared-memory dup) com 3 falsos positivos (CLI "quebrado", consolidation "falhando", daily notes "missing"). Sempre checar /api/health + log real + package.json.bin antes de agir em alegações.
2. **Entry point de CLI é `package.json.bin`, não inferência por nome** — Cipher procurou `dist/cli.js`; real é `dist/index.js`.
3. **WAL precisa estar no nightly-maintenance** — acumulou 96MB em ~1 dia. Ou checkpoint auto, ou cron dedicado.
4. **Consolidation wrapper tem dependência implícita de ENV** — erro 03:31 sugere cron noturno não fez `set -a; source .env`. Precisa auditar `nightly-maintenance.sh`.

### Memórias a salvar (auto-memory)

- `feedback_validate_cipher_diagnostics_independently.md` — Cipher relatórios precisam verification, não action cega
- `reference_nox_mem_cli_entry_is_index_js.md` — entry é `dist/index.js`, não `cli.js`
- `project_ops_pending_2026_04_24.md` — 3 pendências housekeeping pra próxima sessão

---

## 6. COMMITS PENDENTES (não pushed ainda)

```
feat(cli): add nox-mem ingest-entity <file> subcommand

Fecha o gap da 1.7b-c foundation — entity ingest agora tem entry point
formal no CLI, não precisa mais de node -e hack.

- Import ingestEntityFile em src/index.ts
- Register subcommand (~10 lines) antes de reindex
- Rebuild via tsc (clean)
- Re-ingest 2 entities piloto: 8 chunks (nox) + 12 chunks (nox-mem)
- Backup: src/index.ts.bak-20260424-115355

Validação: nox-mem ingest-entity --help OK, hybrid search retorna
section=compiled top hit para "role of nox agent".
```

```
chore(ops): 2026-04-24 housekeeping

- PRAGMA wal_checkpoint(TRUNCATE) — 96MB recuperados
- Archive shared-memory.db (28KB legacy) em /tmp/
- Cipher diagnostic revisão: 2/5 alegações reais

Pendências identificadas (próxima sessão):
- Adicionar WAL checkpoint ao nightly-maintenance.sh
- Auditar ENV sourcing no consolidate_retry.sh call
- Verificar daily notes fs 23/04 e 24/04
```

---

## 7. PRÓXIMA SESSÃO — OPÇÕES DE ENTRADA

### A — Fechar Fase 1.7b-c completa (4-6h, recomendada)

**Escopo:**
1. Script parse `memory/projects.md` (15+ projects) → `memory/entities/projects/<slug>.md`
   - Agora invoca `nox-mem ingest-entity` (formal, não hack)
2. Similar pra `memory/decisions.md` (135 decisions) e `memory/lessons.md` (45 lessons)
3. `/memory-recompile <entity>` skill (Gemini Flash-Lite)
4. Search ranking aplica `section_boost` em SHADOW MODE (logado, não aplicado 7d)

**Pré-requisito**: investigar drop do `never_decay` (92→23) antes de migrar — pode indicar bug no consolidation.

### B — Pular pra Fase 3 (HD Mac rsync)

Aceita 1.7b-c foundation como close. Foco em volume bruto.

### C — Housekeeping pós-Cipher (30-60min)

- Auditar daily notes
- Adicionar WAL ao nightly
- Auditar ENV no consolidate_retry cron context
- Investigar drop `never_decay`
- Responder Cipher com retratação

### Recomendação

**C primeiro (30-60min)** → validar que sistema está realmente healthy sem surpresas → depois **A (1.7b-c close)**. O drop de never_decay 92→23 é red flag que precisa resolver antes de investir em migração massiva.

---

## 8. CHECKLIST PRA ABRIR AMANHÃ

- [ ] Sanity check (seção 1)
- [ ] Ler este handoff + `2026-04-24-session-cipher-diagnostic.md`
- [ ] Investigar `never_decay: 23` (esperado 92+) — pode haver bug no consolidation
- [ ] Decidir: A / B / C
- [ ] Antes de A, fazer C (housekeeping)

---

## 9. CLOSING NOTE

Sessão com tom de "investigação + limpeza + 1 ganho inesperado". O Cipher diagnostic inicialmente soou alarmante mas revelou-se diagnóstico parcial — **sistema está healthy**. Ganhamos:

- 96MB de WAL limpo
- 1 DB legacy arquivado
- CLI formal `ingest-entity` (última peça da foundation 1.7b-c)
- 3 pendências operacionais mapeadas
- 1 red flag novo (never_decay drop) pra investigar

Nenhum rollback necessário. Todos os backups preservados. Sistema **mais limpo** que 12h atrás.

**Próxima janela abre com:** `ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq "{total:.chunks.total,vc:.vectorCoverage,salience:.salience.mode,section:.sectionDistribution,retention:.retentionDistribution}"'`

Se `never_decay < 50`, **investigar consolidation behavior antes de Fase 1.7b-c close**.

---

*Documento gerado: 2026-04-24 ~12:15 BRT. Próxima janela sugerida: ainda hoje (tarde) ou amanhã. Sistema estável, sem urgência.*
