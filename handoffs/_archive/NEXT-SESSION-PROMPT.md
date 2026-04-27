# Prompt pra próxima sessão — nox-mem

**Gerado:** 2026-04-26 ~20:00 BRT (sessão completa: hardening + audit triplo + Wave 2 + E2E + Fase 4 Obsidian + B3 backlog + theming + sync fix)
**Uso:** copiar o bloco abaixo, colar na próxima janela Claude Code

```
Retomando nox-mem pós-sessão 2026-04-26 (sanity 24h → audit triplo 47 findings → 11 HIGH fechados → Wave 2 cleanup → E2E test → Fase 4 Obsidian DONE → B3 backlog 7/8 → 5 graph snippets + Things theme + Juggl/3D Graph instalados).

CONTEXTO OBRIGATÓRIO — ler ANTES de qualquer ação:
1. /Users/lab/Claude/Projetos/memoria-nox/handoffs/MASTER-HANDOFF-2026-04-26.md  (FRESH — leitura única)
2. /Users/lab/Claude/Projetos/memoria-nox/CLAUDE.md  (estado + 15 regras críticas — regra #15 atualizada hoje com NOX_ALLOW_NO_SNAPSHOT + ops_audit append-only)
3. /Users/lab/Claude/Projetos/memoria-nox/plans/2026-04-25-integration-roadmap-v1.6.md  (CANÔNICO)
4. /Users/lab/Claude/Projetos/memoria-nox/docs/nox-neural-memory.md  (v14)

SANITY CHECK (3 comandos — esperar tudo verde):
ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq "{total:.chunks.total, vc:.vectorCoverage, salience:.salience.mode, section:.sectionDistribution, opsAudit:.opsAudit, db:.dbSizeMB}"'
# Esperado: total=9692+, embedded=total, salience=shadow, section.compiled=183, db≈172

ssh root@100.87.8.44 'tail -5 /var/log/nox-schema-invariants.log'
# Esperado: 5 entries OK (5 invariants verdes — section_nonnull≥600 compiled≈183 feedback_wrong=0 ops_failed=0 boost_mismatch=0)

ssh root@100.87.8.44 'cd /root/.openclaw/workspace/tools/nox-mem && node --test dist/__tests__/ 2>&1 | tail -5'
# Esperado: 27 pass 0 fail (14 retention + 7 E2E + 6 outros)

ESTADO ATUAL (2026-04-26 ~17:00 BRT):
- 9692 chunks, 100% embedded, 0 orphans, DB ~172MB
- 184 entities ingestadas (compiled=183, frontmatter=183, timeline=366)
- Schema v10 + ops_audit table com 2 triggers append-only (CWE-693)
- 0 HIGH abertos (12 fechados em 24h via 5 commits hoje)
- Shadow modes: salience (gate 04-30), section_boost (gate 05-01)
- 5 camadas defesa hardened + 27 fixes adicionais

9 COMMITS PUSHED HOJE (2026-04-26):
<NEW> docs+ops(closing): final handoff + Phase Matrix Fase 4 ✅ + sync excludes fix + theming docs
d809416 docs+ops(B3): backlog sprint #4+#5+#7+#8 + Phase Matrix Fase 4 ✅ DONE
d2d8340 feat(obsidian): launchd plist Mac auto-sync 03:00 BRT
409cb08 feat(obsidian): B1 Fase 4 view-only vault — DONE (destrava Fase P)
a0b9b4e docs(handoff): update NEXT-SESSION-PROMPT pra estado pós-04-26
e3b1b31 test(safety)+docs(handoff): E2E test suite + MASTER-HANDOFF-2026-04-26
b3eedd0 fix(safety+quality): Wave 2 cleanup — 11 MEDIUM/LOW fechados
880cbe7 fix(safety+audit): 7 HIGH follow-up — todos fechados (0 HIGH abertos)
e3654d9 fix(safety+audit): audit triplo A1v2+A3+A4+A5 — 4 HIGH fixados (47 findings)
143cab6 fix(safety): B1+B2 — reaper coverage gap + closeDb mid-function bug

OBSIDIAN VAULT (Mac, ~/ObsidianVault):
- 199 .md (sync VPS→Mac diário 03:00 BRT via launchd + Tailscale)
- Things 2 theme + dark mode
- 5 plugins: Dataview + 3D Graph + BRAT + Graph Analysis + Juggl
- 5 graph snippets pra alternar vibe: galaxy-nox (default), cyberpunk, retrowave, minimal-pro, matrix
- Color groups por tag (singular): project/decision/lesson/agent/system/kg/index
- Cmd+G grafo 2D, Cmd+P "Open 3D Graph (global)" pra galáxia 3D
- Sync excludes preservam customizações locais (themes/plugins/snippets/community-plugins/appearance/graph.json)

PRÓXIMA AÇÃO — 5 OPÇÕES (Toto escolhe):

OPÇÃO A — Salience activation gate (RECOMENDADA se for 2026-04-30+)
  bash /root/.openclaw/scripts/activate-salience.sh check
  # Se "READY: baseline 7d OK" → bash activate-salience.sh --apply
  # Se "NOT READY" → aguardar mais dias

OPÇÃO B — Section_boost decision gate (se for 2026-05-01+)
  ssh root@100.87.8.44 'bash /root/.openclaw/scripts/analyze-shadow-telemetry.sh 7'
  # Decidir ativar via NOX_SECTION_BOOST_MODE=active no .env + restart api

OPÇÃO C — Wave 3 cleanup (~2h, opcional pré-gate)
  6 MEDIUM + 5 LOW cosmetic restantes:
  - ts uniqueness via process.hrtime.bigint()
  - Authorization layer (geteuid + chmod 700 binary)
  - accessSnapshot streaming via temp table
  - Crystallize wrap em withOpAudit (antes de qualquer cron)
  - log curl exit code em discord (visibility webhook rotation)
  - regex ordering em scrubSecrets (cosmetic "Bearer [REDACTED][REDACTED]")
  - statvfs cross-FS edge cases handling

OPÇÃO D — Setup Fase 3 Tier 2 (4432 PDFs HD Mac, ~4-5h I/O)
  Preparar pipeline pdftotext → .md → watcher
  Aguardar gates A+B passarem antes pra não contaminar baseline

OPÇÃO E — B1 Fase 4 Obsidian view-only (1h, destrava Fase P)
  Originalmente listado pós-gate mas pode antecipar

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
- **Regra #15 (atualizada 04-26):** ops destrutivas só com --dry-run OU withOpAudit snapshot. ops_audit append-only (DELETE/UPDATE-terminal blocked). NOX_ALLOW_NO_SNAPSHOT=1 override emergencial. closeDb pertence ao caller, NUNCA mid-op.

ESTILO PT-BR (lembrete): use "você", não "tu" (PT-BR business register).

MEMÓRIAS NOVAS HOJE (auto-memory, carregam):
- closeDb mid-function invalidates withOpAudit (B2 lesson)
- Audit must verify prod state, not only code (SEC HIGH #1 lesson)

DOCS/RUNBOOKS NOVOS:
- audits/2026-04-26-B1-B2-zombie-fix.md
- audits/2026-04-26-A1v2-A3-A4-A5-review.md (47 findings consolidados)
- audits/2026-04-26-7highs-followup-fix.md
- audits/2026-04-26-W2-cleanup.md

Pergunta pro Toto ANTES de começar: qual data hoje? Se 04-30+ → A. Se 05-01+ → B. Senão → C/D/E.
```

## Uso alternativo — prompt curto (emergência)

```
Retomando nox-mem v3.7+ (schema v10 + ops_audit append-only, 9692 chunks, 5 camadas defesa + 27 fixes, 27 tests).
Leia handoffs/MASTER-HANDOFF-2026-04-26.md.
Sanity: ssh 100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq "{total:.chunks.total,opsAudit:.opsAudit,section:.sectionDistribution}"'
Esperado: 9692+, opsAudit active, section.compiled=183.
Schema invariants: tail /var/log/nox-schema-invariants.log
Tests: ssh 100.87.8.44 'cd /root/.openclaw/workspace/tools/nox-mem && node --test dist/__tests__/ 2>&1 | tail -5'
Próximo gate: 2026-04-30 salience activation (bash /root/.openclaw/scripts/activate-salience.sh check).
PT-BR: "você" não "tu".
```
