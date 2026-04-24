# Prompt pra próxima sessão — nox-mem

**Gerado:** 2026-04-24 manhã (pós Cipher diagnostic + CLI `ingest-entity` completion)
**Uso:** copiar o bloco abaixo, colar na próxima janela Claude Code

---

```
Retomando nox-mem pós-sessão 2026-04-24 manhã (curta — Cipher diagnostic + CLI completion).

CONTEXTO OBRIGATÓRIO — ler ANTES de qualquer ação:
1. /Users/lab/Claude/Projetos/memoria-nox/handoffs/MASTER-HANDOFF-2026-04-24.md  (leitura única)
2. /Users/lab/Claude/Projetos/memoria-nox/handoffs/2026-04-24-session-cipher-diagnostic.md  (detalhe da sessão manhã)
3. /Users/lab/Claude/Projetos/memoria-nox/CLAUDE.md  (estado + 14 regras críticas)
4. /Users/lab/Claude/Projetos/memoria-nox/plans/2026-04-19-unified-evolution-roadmap.md  (v1.5 — Phase Matrix)

SANITY CHECK (1 comando — esperar tudo verde):
ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq "{total:.chunks.total, vc:.vectorCoverage, retention:.retentionDistribution, salience:.salience, section:.sectionDistribution}"'
# Esperado: total=6328+, vc.embedded=vc.total, salience.mode=shadow, section.compiled=2
# NOTA: total caiu de 7367→6328 vs ontem por consolidation noturno — comportamento esperado

ESTADO ATUAL (2026-04-24 12:00):
- 6328 chunks, 100% embedded, 0 orphans
- Schema v10 mantido (retention_days v8 + pain v9 + section v10)
- DB WAL zero (checkpoint feito hoje — liberou 96MB)
- shared-memory.db (obsoleto 28KB) arquivado em /tmp
- CLI `nox-mem ingest-entity <file>` ADICIONADO hoje (era gap da 1.7b-c)
- Claude CLI backend OAuth ativo, fallback chain sem anthropic/*
- Canários hourly OK
- 2 entities piloto em memory/entities/ (agents/nox.md + systems/nox-mem.md)
- Salience em shadow-mode (baseline 207 promote / 1886 archive)

PRÓXIMA AÇÃO — 3 OPÇÕES (Toto escolhe):

OPÇÃO A — Fechar Fase 1.7b-c completa (4-6h) — RECOMENDADA
  Migração massiva memory/*.md → memory/entities/*.md
  ✨ AGORA com CLI formal: nox-mem ingest-entity <file>
  [ ] Script parse memory/projects.md (15+ projects) → entities/projects/<slug>.md
  [ ] Script parse memory/decisions.md (135 decisions) → agrupar por entidade
  [ ] Script parse memory/lessons.md (45 lessons) → entities/lessons/*.md
  [ ] /memory-recompile <entity> skill (Gemini Flash-Lite reescreve compiled)
  [ ] Shadow-mode search ranking aplica section_boost (log, não aplica 7d)
  [ ] A/B top-5 queries típicas antes/depois
  (Pode ativar 1.7b-b junto: NOX_SALIENCE_MODE=active + restart — baseline tem 1d, ainda cedo, esperar ≥7d)

OPÇÃO B — Pular pra Fase 3 (HD Mac rsync + enrichment tiered, ~1h + rsync)
  Aceitar 1.7b-c foundation como close. Partir pra Fase 3:
  [ ] rsync 21GB de ~/Documents pro VPS
  [ ] graphify incremental + enrichment tiered (Tier 1/2/3)
  [ ] Monitorar SQLITE_BUSY — se aparecer, ativar Path A reativo

OPÇÃO C — Cleanup pós-Cipher + observação (~30min)
  Investigar pendências deixadas pela sessão manhã:
  [ ] Verificar daily notes 23/04 e 24/04 em /root/.openclaw/workspace/memory/daily/
  [ ] Revisar se nightly-maintenance.sh faz `source .env` antes do consolidate_retry.sh
  [ ] Adicionar `PRAGMA wal_checkpoint(TRUNCATE)` no nightly (evitar WAL bloat futuro)
  [ ] Responder Cipher com retratação dos diagnósticos incorretos

CONVENÇÕES OBRIGATÓRIAS (não mudou):
- set -a; source /root/.openclaw/.env; set +a; antes de CLI nox-mem via SSH
- Nunca confiar última linha CLI — validar via /api/health pós-operação
- Schema changes: migration + backfill, nunca ALTER TABLE solto
- Features que mudam ranking → SHADOW MODE primeiro (1 semana baseline)
- openclaw models auth * invalida monkey-patch E registry — diff+reapply ANTES de restart
- Backup .bak-pre-<feature>-<date> antes de editar arquivos produção
- Validar features com DB state, NUNCA só com logs
- Validar alegações de agents secundários (Cipher/Atlas/etc) ANTES de agir — nem tudo que reportam é real

MEMÓRIAS NOVAS (a salvar hoje):
- Cipher diagnostic requer validação — mistura fatos com assumptions
- nox-mem entry point é dist/index.js (ler package.json.bin, não inferir nome)
- WAL checkpoint deveria estar no nightly-maintenance (falta no cron atual)

Pergunta pro Toto ANTES de começar: A / B / C?
```

---

## Uso alternativo — prompt curto (emergência)

```
Retomando nox-mem v3.7+ (schema v10). Leia handoffs/MASTER-HANDOFF-2026-04-24.md.
Próximo: Fase 1.7b-c close (migração memory/*.md → entities/) OU Fase 3 (HD rsync).
CLI nox-mem ingest-entity <file> agora disponível (fix de hoje).
Sanity: ssh 100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq .chunks.total'
Esperado 6328+.
```

---

*Esse arquivo é só um lembrete — copiar o conteúdo pra próxima sessão. Atualizar aqui se o plano mudar antes da próxima janela abrir.*
