# Prompt pra próxima sessão — nox-mem

**Gerado:** 2026-04-21 (noite, pós-roadmap v1.3)
**Uso:** copiar o bloco abaixo, colar na próxima janela Claude Code

---

```
Olá! Estou retomando a execução do plano nox-mem (roadmap v1.3).
Sessão anterior: 2026-04-21 — audit sistêmica completa + análise do paper "Claude Memory Setup".

CONTEXTO OBRIGATÓRIO (leia antes de qualquer ação):
1. /Users/lab/Claude/Projetos/memoria-nox/handoffs/MASTER-HANDOFF-2026-04-21.md (leitura única consolidada)
2. /Users/lab/Claude/Projetos/memoria-nox/CLAUDE.md (v3.6d — Evolution + Incident Log + Convenções)
3. /Users/lab/Claude/Projetos/memoria-nox/plans/2026-04-19-unified-evolution-roadmap.md (v1.3 — Phase Matrix atualizada)
4. /Users/lab/Claude/Projetos/memoria-nox/plans/2026-04-21-claude-memory-setup-gaps.md (plan detalhado das sub-fases 1.7b-a/b/c)

ORDEM DE PRIORIDADE (reiterada pelo Toto):
Plano operacional primeiro → auditoria detalhada → Fase 2 scale → 1.7b-b → 1.7b-c → Fase 3+ → (estável 30d+) → produtização NOX-Supermem POR ÚLTIMO.

ESTADO ATUAL:
- Sistema v3.6d em produção estável
- 2073 chunks 100% embedded, canary */30min OK, RelayPlane ativo com budget cap
- Git em sync com GitHub (commits 7f5d0c4, 8d6c4a6, f53a121, 6e9e688 já pushed)
- Zero pendência crítica ou alta

PRÓXIMO PASSO APROVADO: IM + 1.7b-a JUNTOS (~3h total)

Ordem de execução DENTRO desta sessão:

[FASE A] — 1.7b-a: Typed source retention matrix (2h, FAZER PRIMEIRO)
  Plan: plans/2026-04-21-claude-memory-setup-gaps.md, seção "Proposta 1"
  Entregáveis:
  [ ] Schema migration v8: adicionar `retention_days INTEGER` + `expires_at` virtual + index
  [ ] RETENTION_BY_TYPE map em src/retention.ts:
      feedback=null, person=null (never), lesson=180, decision=365, project=365,
      daily=90, team=120, digest=180, pending=30, other=90
  [ ] Backfill nos 2073 chunks existentes (UPDATE ... SET retention_days = CASE chunk_type ...)
  [ ] Ingest logic (ingest.ts + graphify-ingest.ts) popula retention_days no insert
  [ ] User override via HTML comment: <!-- retention: never --> ou <!-- retention: 365 -->
  [ ] Tier evaluation considera expires_at (archive candidates = expires_at < now AND tier != 'core')
  [ ] Novo endpoint /api/health.retentionDistribution (quantos chunks expiram em 30d/90d/etc)
  [ ] Validar: zero feedback arquivado; canary continua OK; build do nox-mem passa
  [ ] Commit + push

[FASE B] — IM: Import repos locais (45min, FAZER DEPOIS de A)
  Plan: plans/2026-04-21-session-start.md (intacto)
  Escopo: docs-only (*.md) de 10 projetos ~/Claude/Projetos/ + raiz ~/Claude/
  4 fases:
  [ ] Fase 1 Inventário (5min): listar *.md por projeto, identificar duplicados, escolher pilot
  [ ] Fase 2 Pilot (10min): scp docs do pilot → ingest → vectorize → validar search semantic
  [ ] Fase 3 Batch (25min): iterate 9 projetos restantes + raiz, 1 query validação por projeto
  [ ] Fase 4 KG + docs (5min): nox-mem kg-build + update CLAUDE.md com métricas finais
  [ ] Commit + push

[ZERO-COST BONUS]: novos repos importados em [FASE B] já entram com retention_days correto
porque [FASE A] está aplicada — nenhum backfill depois.

ANTES DE COMEÇAR — SANITY CHECK (2 comandos):
  ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d[\"vectorCoverage\"]))"'
  (esperado: embedded=2073 total=2073 orphans=0)

  ssh root@100.87.8.44 'tail -3 /var/log/nox-canary.log'
  (esperado: OKs consecutivos)

CONVENÇÕES OBRIGATÓRIAS:
- Sempre carregar .env antes de CLI nox-mem via SSH: set -a; source /root/.openclaw/.env; set +a
- Nunca confiar só na última linha do CLI — validar via /api/health pós-operação
- Schema changes: migration script + backfill, NUNCA ALTER TABLE solto sem testar em cópia
- Gemini Flash-Lite é o modelo default (heartbeats, crons, active-memory) — nunca voltar pra 2.5 Flash full
- Monkey-patch Issue #62028 ativo em dist/restart-stale-pids-*.js — reaplicar após npm update
- Backup sempre com .bak-pre-<feature>-<date> antes de editar arquivos produção

DEPOIS DA FASE A + B:
Após commitar e pushar ambas, estado próximo é:
  → Audit detalhada do checklist plans/2026-04-20-next-session-checklist.md
  → Fase 2 Graphify scale 3→15 repos
  → Fase 1.7b-b (Salience formula, 4h shadow-mode 1 semana)
  → Fase 1.7b-c (Compiled truth + timeline, 1-2d, FINALIZA Fase 1.7b)

Pergunta pro Toto ANTES de começar: quer que eu execute [FASE A] + [FASE B] direto,
ou prefere revisar meu plano de migração v8 primeiro?
```

---

## Uso alternativo — prompt curto (emergência)

Se só quiser retomar rápido, cole isto:

```
Retomando nox-mem v3.6d. Leia MASTER-HANDOFF-2026-04-21.md + roadmap v1.3.
Próximo: IM + 1.7b-a juntos (detalhes em claude-memory-setup-gaps.md e session-start.md).
Posso começar?
```

---

*Este arquivo é só um lembrete — o conteúdo real vai via copy-paste pra próxima sessão. Atualizar aqui se o plano mudar antes da próxima janela abrir.*
