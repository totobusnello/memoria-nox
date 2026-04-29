# nox-mem HANDOFF — estado vivo

> **Atualizado:** 2026-04-29 ~10:30 BRT (sync-verify patch + cron 5:30 cross-agent-sync heartbeat + docs sync F09→CUT + audit pós-marathon iniciado)
> Substitui a sequência `handoffs/MASTER-HANDOFF-<date>.md`. Este arquivo único é mantido vivo a cada sessão.
> Histórico individual em `handoffs/_archive/`. Para "o que vem" → `docs/ROADMAP.md`. Para "por quê" → `docs/DECISIONS.md`.

## Última sessão (2026-04-28) — Optimization Marathon

| Métrica chave | Antes | Depois |
|---|---|---|
| OpenClaw | 2026.4.25 | **2026.4.26** |
| Turn latency | 39.8s | **10.4s** (-74%) |
| Boot gateway | ~10s | 5.7s |
| `.git` workspace | 11GB | **134MB** (-99%) |
| Skills missing | 39 | **0** |
| Heartbeats/dia | 384 | 144 (-62.5%) |
| Token revogado 6 personas | sim (silent 401) | resolvido |
| Disk free `/` | 114GB | 116GB |

**Documentação completa:** `docs/RUNBOOKS/2026-04-28-optimization-marathon.md` (458 linhas, reproduzível).
**Plan original:** `plans/2026-04-28-openclaw-v2026.4.26-upgrade.md`.

---

## 1. Sanity check (1-cmd)

```bash
ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq "{
  total: .chunks.total,
  embedded: .vectorCoverage.embedded,
  salience: .salience.mode,
  section: .sectionDistribution,
  opsAudit: .opsAudit,
  db: .dbSizeMB
}"'
```

**Última leitura (2026-04-27 ~19:00 BRT pós-A1+A3+A4+A5+A6):**
```
total:    62836 chunks (+42005 vs baseline manhã = +202% / TRIPLICOU)
embedded: 62836 / 62836 (100%, gap=0)
salience: shadow (gate G01 04-30)
section:  compiled=183, frontmatter=183, timeline=366, legacy=62104
opsAudit: 1 op 24h (compact 02:00 ✓)
db:       1.016 GB (era 318MB pré-A1, +220% / >1GB)
search:   smoke OK em Granix-App, Claude skills, biolab-ai, agent-orchestrator, NUVIVI (debenture/PDF), PPR (xlsx/pptx/PDF licitação)
```

## 2. Improvements audit

```bash
ssh root@100.87.8.44 '/root/bin/improvements check'
```

**Última leitura:** **13/13 OK** (7 critical + 6 warn-only, todos pass).

## 3. Onde paramos

Sessões 2026-04-25/26/27 entregaram:
- **F01-F08** ✅ Bloco I hardening completo + B1 Obsidian + B3 backlog
- **F07** ✅ OpenClaw upgrade defense system (commit 3b9e23c, pushed)
- **Consolidação documental** ✅ ROADMAP/DECISIONS/HANDOFF (3 arquivos canônicos) + README + ARCHITECTURE + RUNBOOKS + CONTRIBUTING (4 docs novos via agents)
- **Sistema unificado de IDs** F/E/R/P/G/D (substitui 6+ namespaces antigos)
- **Reorganização repo:** plans/_archive (25), handoffs/_archive (9)
- Review triplo (architect + critic + architect-reviewer): 14 mudanças aplicadas no ROADMAP (capacity recalibrada, R01 split skeleton/curation, E03/E04 split implement/activate, F09-F16 gaps adicionados)
- **R01a Eval Harness design spec** ✅ commit 3d85ffd (424 linhas, schema v12 + CLI + métricas)
- **Sprint A1 ingestão massiva** ✅ +19.070 chunks (graphify-ingest 9 repos + 7 repos pequenos + Claude workspace scope curado)
  - Fase 1: graphify-ingest 9 repos com graphify-out → +1.046 graph_nodes
  - Fase 2a: clone+ingest 7 repos pequenos (biolab-ai, curso-ai, posts-linkedin, grancoffee, superfrio, fake-news-check, claude-project-template) → +304 markdown chunks
  - Fase 2b: Claude workspace scope curado (docs+agents+skills+commands+Projetos, _retired excluído) → +17.714 chunks de 1.356 md
  - Decisão: SKIP powerpoint-templates (114MB visual, gated Tier 3 OCR), SKIP nox-workspace (257MB, scope decision posterior), SKIP A2 ~/Desktop (transitório)
- **Sprint A3 Mac local Claude/Projetos delta** ✅ +863 chunks
  - rsync `~/Claude/Projetos/agent-orchestrator/` → VPS shared/imports/ (143MB, exclude .git/node_modules)
  - 106 md ingestados manualmente (watcher race em rsync rápido)
  - Outros 240 md de ~/Claude/Projetos/* duplicariam shared/imports/<repo>/, scope cut
- **Sprint A4 ~/Documents office files (docx+xlsx+pptx)** ✅ +2.469 chunks
  - rsync seletivo: 536 docx + 976 xlsx + 83 pptx → VPS mac-docs/ (NUVIVI, PPR, PESSOAL, CONTRATOS, BANCOS, EMPRESAS Cont)
  - Conversão pipeline expandido: pandoc (docx) + libreoffice-calc (xlsx→csv) + **markitdown[pptx]** (pptx→md)
  - markitdown novo na stack (Microsoft, 117k stars, MIT, Python) — resolveu pptx que libreoffice-impress sem filtro txt
- **Sprint A5 — pipeline unified script** ✅
  - convert-office-to-md.sh refatorado: markitdown primary + pandoc/libreoffice fallback
  - Idempotente (skip se .md newer than source)
  - /root/.openclaw/scripts/pdf-batch.sh standalone reusável
- **Sprint A6 — PDF batch (Tier 2 antecipado, sem OCR)** ✅ +19.602 chunks
  - 4.494 PDFs no ~/Documents (NUVIVI 546 + PPR 1807 + PESSOAL 1163 + CONTRATOS 689 + BANCOS 142 + 84 não-sync EMPRESAS Cont com espaço)
  - rsync paralelo 5 dirs simultâneos
  - Markitdown[pdf] via tmux session (após 2 falhas: parent-shell death + systemd quoting hell + watchdog buggy 69 procs simultâneos)
  - 1.444 PDFs text-layer convertidos com sucesso → 19.602 chunks
  - 781 PDFs scanned/imagem (NFs, fotos, comprovantes) detectados como output <100 chars e descartados (esperam OCR Tier 3 / E12)
  - Vectorize 100% sucesso (15.693 embedded em 13min, 0 errors no retry sem load alto)
  - Lições: 1) systemd-run com `${var}` precisa script standalone; 2) 69 markitdown simultâneos sufoca VPS (load 22, OOM); 3) tmux é a abordagem mais estável; 4) batch idempotent é safety net

Sistema saudável e mais rico. Em **holding pattern** até G01 (3 dias).

## 4. Próxima ação concreta

Hoje é **2026-04-29** (quarta). **G01 amanhã 04-30.**

### 🔴 P0 — em andamento agora
- **Audit pós-marathon** (3 agents paralelos rodando) — architect drift + security regressões + code review A1-A6
- **Output:** `audits/2026-04-29-post-marathon-audit.md` consolidado
- **Decisão:** go/no-go pra G01 amanhã baseado em findings

### F09 → ❌ CUT (D22)
~~Off-site backup rclone~~ — user rejeitou 2x. Decisão registrada em DECISIONS.md linha 246. Movido pra D22 no roadmap.

### 🟡 Opcional pre-G01 (se sobra tempo após audit)

| ID | Trabalho | Esforço | Valor |
|---|---|---|---|
| E03a/E04a | Design specs A6 SPO Injection + A7 Focus Boost | ~40min cada | Alto — execução rápida pós-G03 |
| E09 | Decisão "Fase 1.7b dormente vs E09 executável" | ~30min | Médio (destrava Maio) |
| (cleanup) | Test isolation fix (--test dir glob) + 5 LOW polish | ~1h | Médio (hygiene) |

### Combo recomendado pré-G01
1. **Audit consolidado** (em andamento) — primeira prioridade
2. **Fix critical/high findings** se houver
3. **E03a + E04a designs** (~80min) se restar tempo
4. **G01 amanhã** com sistema validado

### Atividade 2026-04-29 (esta sessão)
- ✅ sync-verify cross-agent-sync.sh patched: HEARTBEAT line escrita sempre, mesmo TOTAL=0
- ✅ cron 5:30 BRT adicionado (`30 5 * * *`) antes do sync-verify 6:00
- ✅ activity log heartbeat validado: `2026-04-29T10:20:03Z [SYSTEM] HEARTBEAT`
- ✅ ROADMAP/HANDOFF sync: F09 → D22 CUT, datas atualizadas
- 🔄 Audit pós-marathon (3 agents paralelos)

## 5. Eventos agendados (gates + waves)

- **2026-04-30** terça — **G01** Salience activation (`activate-salience.sh check` → `--apply` se READY)
- **2026-05-01** quarta — **G02** Section_boost decision (`analyze-shadow-telemetry.sh 7`)
- **2026-05-02** quinta — **G03** Archive 3 source files + iniciar E02 + E03a + E04a paralelo
- **05-09** quinta — **E03b + E04b activate** (após shadow 7d)
- **Maio 2026** — Wave 1 (E05 → E06/E07/E08) + R01a eval skeleton (antecipado!)
- **Jun-Jul 2026** — R01b curadoria 50 queries + R01c baseline + E10 candidate (gated)
- **Ago 2026** — R02 paper v2
- **Set+ 2026** — E11 reflect cache + F15 SEH + **P01 NOX-Supermem productização**

## 6. Contexto necessário pra retomar

**Mínimo absoluto (3 arquivos):**
1. Este arquivo (`docs/HANDOFF.md`) — estado atual
2. `docs/ROADMAP.md` — o que vem, capacity, gates, IDs unificados
3. `CLAUDE.md` — regras críticas operacionais 1-15

**Quando precisar entender "por quê":**
4. `docs/DECISIONS.md` — NÃO FAZEMOS, decisões arquiteturais, lições

**Quando precisar profundidade:**
5. `docs/ARCHITECTURE.md` — system design + ASCII diagrams
6. `docs/VISION.md` — long-term thesis (nox-neural-memory v14)
7. `docs/RUNBOOKS.md` — incident playbooks (10 cenários)

**Quando precisar referência histórica:**
- `plans/_archive/2026-04-25-integration-roadmap-v1.6.md` — v1.6 original
- `plans/_archive/2026-04-26-clawmem-analysis.md` — Section 9 candidates
- `handoffs/_archive/MASTER-HANDOFF-2026-04-26.md` — última sessão detalhada

**Memory auto-load:**
- `MEMORY.md` (em `~/.claude/projects/-Users-lab-Claude-Projetos-memoria-nox/memory/`) — 36+ feedback files

## 7. Comandos úteis quick-ref

```bash
# Sanity check completo
ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq .'

# Improvements audit (13/13 baseline)
ssh root@100.87.8.44 '/root/bin/improvements check'

# Schema invariants
ssh root@100.87.8.44 'tail -5 /var/log/nox-schema-invariants.log'

# Tests (rodar individualmente, race condition em --test dir)
ssh root@100.87.8.44 'cd /root/.openclaw/workspace/tools/nox-mem && node --test dist/__tests__/retention.test.js dist/__tests__/op-audit-e2e.test.js 2>&1 | tail -5'

# OpenClaw release watcher state
ssh root@100.87.8.44 'cat /root/.openclaw/upgrade-watcher/state.json'

# Latest checkpoint
ssh root@100.87.8.44 'ckpt list | head -3'

# Logs gateway
ssh root@100.87.8.44 'journalctl -u openclaw-gateway --since "10 min ago" --no-pager | tail -30'

# CLI nox-mem (lembrar source env primeiro)
ssh root@100.87.8.44 'set -a; source /root/.openclaw/.env; set +a; nox-mem --help'

# Salience activation gate (G01 04-30)
ssh root@100.87.8.44 'bash /root/.openclaw/scripts/activate-salience.sh check'

# Section_boost analysis (G02 05-01)
ssh root@100.87.8.44 'bash /root/.openclaw/scripts/analyze-shadow-telemetry.sh 7'
```

## 8. Convenções obrigatórias (lembrete rápido)

Ver `CLAUDE.md` para detalhes completos das 15 regras. Top 5:

1. **Secrets só via env** (`${VAR_NAME}` em configs, gitleaks pre-commit)
2. **Antes de CLI nox-mem em SSH/cron:** `set -a; source /root/.openclaw/.env; set +a`
3. **Validar features com DB state, não só logs** (`/api/health` JOIN é a fonte)
4. **Modelo Gemini default = `gemini-2.5-flash-lite`** (flash full estoura quota)
5. **claude-cli backend zero-cost** — `chattr +i` em `.credentials.json`, NO `CLAUDE_CODE_OAUTH_TOKEN` em env

**PT-BR:** "você" não "tu". Registro Brasil/Hotmart.

---

**Próxima atualização deste arquivo:** quando estado mudar (gates passarem, sprint completar, incident).
