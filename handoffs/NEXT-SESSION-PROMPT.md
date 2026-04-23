# Prompt pra próxima sessão — nox-mem

**Gerado:** 2026-04-23 final de dia (pós Fase 1.7b-a + IM + Fase 2 + 1.7b-b + 1.7b-c foundation)
**Uso:** copiar o bloco abaixo, colar na próxima janela Claude Code

---

```
Olá! Retomando nox-mem pós dia 2026-04-23 (sessão pesada — 4h15min dev, 10 commits, chunks 2073→7367, schema v7→v10).

CONTEXTO OBRIGATÓRIO — ler ANTES de qualquer ação:
1. /Users/lab/Claude/Projetos/memoria-nox/handoffs/MASTER-HANDOFF-2026-04-23.md  (leitura única)
2. /Users/lab/Claude/Projetos/memoria-nox/CLAUDE.md  (estado + 14 regras críticas)
3. /Users/lab/Claude/Projetos/memoria-nox/plans/2026-04-19-unified-evolution-roadmap.md  (v1.5 — Phase Matrix)

SANITY CHECK (1 comando — esperar tudo verde):
ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq "{total:.chunks.total, vc:.vectorCoverage, retention:.retentionDistribution, salience:.salience, section:.sectionDistribution}"'
# Esperado: total=7367+, vc.embedded=vc.total, salience.mode=shadow, section.compiled=2

ESTADO ATUAL:
- 7367 chunks, 100% embedded, 0 orphans
- Schema v10 (retention_days v8 + pain v9 + section v10)
- Claude CLI backend OAuth (zero API bill), fallback chain sem anthropic/*
- Canários hourly ativos (monkey-patch integrity, gm_messages growth)
- 2 entities piloto em memory/entities/ (agents/nox.md + systems/nox-mem.md)
- Salience em shadow-mode (baseline: 207 promote_candidates, 1886 archive)
- Zero pendência crítica

PRÓXIMA AÇÃO — 3 OPÇÕES (Toto escolhe):

OPÇÃO A — Fechar Fase 1.7b-c completa (4-6h) — RECOMENDADA
  Migração massiva memory/*.md → memory/entities/*.md:
  [ ] Script parse memory/projects.md (15+ projects) → entities/projects/<slug>.md
      cada um com frontmatter + compiled + timeline extraído
  [ ] Script parse memory/decisions.md (135 decisions) → agrupar por entidade
  [ ] Script parse memory/lessons.md (45 lessons) → entities/lessons/*.md
  [ ] /memory-recompile <entity> skill (Gemini Flash-Lite reescreve compiled)
  [ ] Shadow-mode search ranking aplica section_boost (log, não aplica 7d)
  [ ] A/B top-5 queries típicas antes/depois
  [ ] Finaliza Fase 1.7b como um todo
  (Pode ativar 1.7b-b junto: NOX_SALIENCE_MODE=active + restart)

OPÇÃO B — Pular pra Fase 3 (HD Mac rsync + enrichment tiered, ~1h + rsync)
  Aceitar 1.7b-c foundation como close. Partir pra Fase 3:
  [ ] rsync 21GB de ~/Documents pro VPS
  [ ] graphify incremental + enrichment tiered (Tier 1/2/3)
  [ ] Monitorar SQLITE_BUSY — se aparecer, ativar Path A reativo
  Risco: volume alto de writes, possível regressão em performance

OPÇÃO C — Activation 1.7b-b + observação passiva (~30min trabalho)
  Só ativar salience (NOX_SALIENCE_MODE=active) + monitorar 48h impact.
  Baseline já coletada hoje. Baixo risco, rollback trivial.
  Depois voltar pra A/B em sessão dedicada.

CONVENÇÕES OBRIGATÓRIAS (não mudou desde ontem):
- set -a; source /root/.openclaw/.env; set +a; antes de CLI nox-mem via SSH
- Nunca confiar última linha CLI — validar via /api/health pós-operação
- Schema changes: migration + backfill, nunca ALTER TABLE solto
- Features novas que mudam ranking → SHADOW MODE primeiro (1 semana baseline)
- openclaw models auth * invalida monkey-patch E registry — diff+reapply ANTES de restart
- Backup .bak-pre-<feature>-<date> antes de editar arquivos produção
- Validar features com DB state, NUNCA só com logs (graph-memory zombie 4d lesson)

MEMÓRIAS NOVAS SALVAS HOJE (auto-memory, carrega nas próximas sessões):
- models auth login wipes registry + monkey-patches (2 efeitos colaterais)
- graph-memory probe errors in doctor are stale (runtime pode estar ok)
- heartbeat "Unknown Channel" regression = janela rolante 24h artifact
- Validate features com DB state, não logs sozinhos
- VPS infra triage command bundle (7 comandos read-only)

Pergunta pro Toto ANTES de começar: A / B / C?
```

---

## Uso alternativo — prompt curto (emergência)

```
Retomando nox-mem v3.7+ (schema v10). Leia handoffs/MASTER-HANDOFF-2026-04-23.md.
Próximo: Fase 1.7b-c close (migração memory/*.md → entities/) OU Fase 3 (HD rsync).
Sanity: ssh 100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq .chunks.total'
Esperado 7367+.
```

---

*Esse arquivo é só um lembrete — copiar o conteúdo pra próxima sessão. Atualizar aqui se o plano mudar antes da próxima janela abrir.*
