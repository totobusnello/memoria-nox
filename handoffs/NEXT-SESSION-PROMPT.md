# Prompt pra próxima sessão — nox-mem

**Gerado:** 2026-04-25 ~16:45 BRT (sessão de incident recovery + 6 fases hardening)
**Uso:** copiar o bloco abaixo, colar na próxima janela Claude Code

---

```
Retomando nox-mem pós-sessão 2026-04-25 (incident recovery + pre-gate hardening completo + 3 itens post-gate antecipados).

CONTEXTO OBRIGATÓRIO — ler ANTES de qualquer ação:
1. /Users/lab/Claude/Projetos/memoria-nox/handoffs/MASTER-HANDOFF-2026-04-25.md  (FRESH — leitura única)
2. /Users/lab/Claude/Projetos/memoria-nox/CLAUDE.md  (estado + 15 regras críticas — regra #15 é nova: ops destrutivas só com --dry-run ou snapshot atômico)
3. /Users/lab/Claude/Projetos/memoria-nox/plans/2026-04-25-integration-roadmap-v1.6.md  (CANÔNICO desde 04-25; substitui Phase Matrix do v1.5)
4. /Users/lab/Claude/Projetos/memoria-nox/docs/nox-neural-memory.md  (v14, visão estratégica com Phase Matrix tabular embedded + 3 decisões novas)

SANITY CHECK (1 comando — esperar tudo verde):
ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq "{total:.chunks.total, vc:.vectorCoverage, salience:.salience.mode, section:.sectionDistribution, opsAudit:.opsAudit, db:.dbSizeMB}"'
# Esperado: total=9540, embedded=9540, salience=shadow, section.compiled=183, opsAudit (active), db≈172

SCHEMA INVARIANTS (NOVO canário A4 — */15min):
ssh root@100.87.8.44 'tail -3 /var/log/nox-schema-invariants.log'
# Esperado: 3 entries OK (section_nonnull≥600 compiled≈183 feedback_wrong=0 ops_failed=0 boost_mismatch=0)

ESTADO ATUAL (2026-04-25 16:45):
- 9540 chunks, 100% embedded, 0 orphans, DB ~172MB
- 184 entities ingestadas (compiled=183, frontmatter=183, timeline=366)
- 2697 chunks em memory/mac-docs/ (HD Mac Tier 1)
- Source .md files arquivados — entities substituem
- Schema v10 + 4 cols A0 + ops_audit table A1
- Shadow modes ativos:
  * NOX_SECTION_BOOST_MODE=shadow (decisão 2026-05-01)
  * NOX_SALIENCE_MODE=shadow (ativação 2026-04-30)
  * NOX_SEARCH_LOG_TEXT=1 (NOVO A0, opt-in pra eval harness futura)
- Claude CLI backend OAuth, fallback sem anthropic/*
- 5 camadas de defesa ativas: semantic-canary + schema-invariants + ops_audit + withOpAudit + --dry-run
- Pre-gate hardening A0+A1+A2 completo
- Post-gate parcial A3+A4+A5 antecipado

6 COMMITS PUSHED HOJE (2026-04-25):
942dcf7 feat(safety): A5 dry-run mode em reindex+consolidate
2b29d06 test+ops(safety): A3 retention tests + A4 schema invariants canary
9da8f7c feat(arch): A2 ingest-router — single dispatch entry point
b5fba08 feat(safety): A1 op-audit module — atomic snapshot + audit log
2d47158 feat(observability): A0 query logging extension — search_telemetry +4 cols
398ad7e docs(memory): v3.7+ consolidação — v1.6 roadmap + v14 vision + #15 + incident

PRÓXIMA AÇÃO — 3 OPÇÕES (Toto escolhe):

OPÇÃO A — Salience activation gate (RECOMENDADA se for 2026-04-30+)
  bash /root/.openclaw/scripts/activate-salience.sh check
  # Se "READY: baseline 7d OK" → bash activate-salience.sh --apply
  # Se "NOT READY" → aguardar mais dias

OPÇÃO B — Section_boost decision gate (se for 2026-05-01+)
  ssh root@100.87.8.44 'bash /root/.openclaw/scripts/analyze-shadow-telemetry.sh 7'
  # Decidir ativar via NOX_SECTION_BOOST_MODE=active no .env + restart api

OPÇÃO C — Continuar post-gate remanescente (~3h estimado, ~2h real)
  - B1 Fase 4 Obsidian view-only (1h, destrava Fase P)
  - B3 Backlog #4 issue + #5 docs + #7 alert + #8 playbooks (1h45)
  - Arquivar 3 source files (.archived-20260502, 5min)

OPÇÃO D — Iniciar Fase 3 Tier 2 (PDFs text-layer, ~4-5h)
  4432 PDFs do HD Mac → pdftotext → .md → watcher auto-ingest
  Aguardar gates A+B passarem antes pra não contaminar baseline

EVENTOS AGENDADOS:
- 2026-04-30: salience activation (--apply se baseline 7d OK)
- 2026-05-01: section_boost decision (analyze-shadow-telemetry.sh 7)
- 2026-05-02+: arquivar 3 source files + iniciar B1/B3/D
- Maio-Ago 2026: Memory Graph Maturity Waves W1/W2/W3 (gated por métricas)

CONVENÇÕES OBRIGATÓRIAS (CLAUDE.md regras 1-15):
- set -a; source /root/.openclaw/.env; set +a antes de CLI nox-mem
- Nunca confiar última linha CLI — validar via /api/health pós-operação
- Schema changes: aditivas + backfill, nunca ALTER TABLE solto
- Features que mudam ranking → SHADOW MODE 1 semana baseline
- openclaw models auth * invalida monkey-patch E registry
- Backup .bak-pre-<feature>-<date> antes de editar arquivos produção
- Validar features com DB state, NUNCA só com logs
- Entry point CLI é dist/index.js (não cli.js)
- <!-- retention: X --> HTML comment na frente, NÃO YAML
- Editar openclaw.json via `openclaw config set`, NÃO jq+mv
- **Regra #15 (NOVA):** ops destrutivas (reindex/consolidate/compact/crystallize) só com --dry-run OU snapshot atômico. backup-all.sh diário NÃO conta como pré-op.

ESTILO PT-BR (lembrete): use "você", não "tu" (PT-BR business register, audience NOX-Supermem product).

MEMÓRIAS NOVAS (auto-memory, carregam):
- A0 query logging extension (search_telemetry +4 cols)
- A1 op-audit module (withOpAudit wrapper, ops_audit table)
- A2 ingest-router (single dispatch entry point)
- A3+A4 retention tests + schema invariants canary (4 invariants */15min)
- A5 dry-run mode (reindex+consolidate)
- Reindex/watcher must route entity files via ingestEntityFile (incident lesson)
- end-of-day OpenClaw cron drives daily reindex (incident lesson)
- User-level systemd units can run rogue (incident lesson)
- Use você não tu (estilo PT-BR)

Pergunta pro Toto ANTES de começar: qual data hoje? Se 04-30+ → A. Se 05-01+ → B. Senão → C ou D.
```

---

## Uso alternativo — prompt curto (emergência)

```
Retomando nox-mem v3.7+ (schema v10 + ops_audit, 9540 chunks, 5 camadas defesa).
Leia handoffs/MASTER-HANDOFF-2026-04-25.md.
Sanity: ssh 100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq "{total:.chunks.total,opsAudit:.opsAudit,section:.sectionDistribution}"'
Esperado: 9540, opsAudit active, section.compiled=183.
Schema invariants: tail /var/log/nox-schema-invariants.log
Próximo gate: 2026-04-30 salience activation (bash /root/.openclaw/scripts/activate-salience.sh check).
PT-BR: "você" não "tu".
```

---

*Esse arquivo é só um lembrete — copiar o conteúdo pra próxima sessão. Atualizar aqui se o plano mudar antes da próxima janela abrir.*
