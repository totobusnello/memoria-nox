# B3 Backlog Sprint — 2026-04-26

**Trigger:** Backlog item B3 (#4 + #5 + #7 + #8) listado pra POST-GATE 05-02+ no roadmap v1.6, antecipado pré-gate (sistema estável, gate 04-30 não muda nada até lá).

**Tempo real:** ~45min (vs estimativa 1h45 — 2.3x mais rápido porque #7 já estava implementado).

---

## Items entregues

### #4 — Issue upstream graph-memory plugin
**Status:** RASCUNHO documentado em `plans/2026-04-26-graph-memory-upstream-issue-draft.md`

Não abri o issue — repo upstream URL precisa ser confirmado primeiro (`openclaw plugin info graph-memory`). Toto decide quando abrir. Draft cobre: title, body, reproduction, suggested fix, workarounds atuais, environment.

### #5 — Docs CONVENTIONS.md chunk_type unificado
**Status:** ✅ DONE

Adicionada seção "chunk_type — enum canônico (B3-5, 2026-04-26)" em `docs/CONVENTIONS.md`. Cobre:
- Tabela canônica de 11 tipos (feedback, person, lesson, decision, project, daily, team, digest, pending, graph_node, other) com retention default + origem ingest + notes
- Workflow pra adicionar tipo novo (6 steps)
- Documentação do ingest-router unified (Fase A2 v1.6) — single dispatch + handlers + callers

Per roadmap v1.6: "MERGE com Fase 0.5 ingest-router doc" — feito junto.

### #7 — Monkey-patch orphan alert
**Status:** ✅ JÁ ESTAVA IMPLEMENTADO

Validação:
- Cron `*/15 * * * *` em crontab (`/root/.openclaw/scripts/check-monkey-patch.sh`)
- Script tem Discord alert com 🚨 CRITICAL message no path do fail
- Logs últimas 24h: `OK: monkey-patch intact in /usr/lib/node_modules/openclaw/dist/restart-stale-pids-CegQx-K9.js` consistente
- Smoke manual: `bash check-monkey-patch.sh; echo $?` = `0` ✅

Sem trabalho novo necessário. Item fechado por validação.

### #8 — Rollback playbooks
**Status:** ✅ DONE — 3 playbooks novos

Arquivos criados:
- `runbooks/rollback-nox-mem-version.md` — TS code rollback (5min procedure + pegadinhas closeDb/singleton)
- `runbooks/rollback-openclaw-version.md` — gateway version rollback (10min + monkey-patch reapply + sessions cleanup)
- `runbooks/rollback-schema-migration.md` — DB migration rollback via safeRestore (15min, com referência ao W2-4 reorder)

Per roadmap v1.6: "MERGE com Fase 1 (snapshot pré-op)" — playbooks usam `safeRestore()` do A1 v2 + W2-4 reorder.

---

## Cobertura final do backlog (item #1-#8)

| # | Item | Status |
|---|---|---|
| 1 | Unit tests parseRetentionOverride | ✅ DONE 04-25 (A3) — 14 cases + 6 adversarial (W2-9) = 20 total |
| 2 | Daily retention telemetry | ✅ Coberto pelo A0 (search_telemetry +4 cols) |
| 3 | expires_at generated column | ✅ FECHADO pela 1.7b-b (pain+retention compõem salience) |
| 4 | Issue upstream graph-memory | ✅ Draft criado (`plans/2026-04-26-graph-memory-upstream-issue-draft.md`) |
| 5 | Docs CONVENTIONS.md chunk_type | ✅ DONE 04-26 (seção nova) |
| 6 | Canários como MCP tools | ⏳ PRECURSOR de Fase 0.7 (feature flags) — defer Wave 2+ |
| 7 | Monkey-patch orphan alert | ✅ Já implementado pré-existente |
| 8 | Rollback playbooks | ✅ DONE 04-26 (3 runbooks novos) |

**7 de 8 fechados.** Item #6 (canary como MCP tool) defer formal pra Wave 2+ por ser arquitetura nova (não trivial).

---

## Smoke (3/3 passaram)

| Teste | Resultado |
|---|---|
| Cron monkey-patch ativo + Discord alert path | ✅ logs OK */15min sem WARN |
| CONVENTIONS.md tabela chunk_type renderiza | ✅ 11 rows + workflow + ingest-router doc |
| Rollback playbooks legíveis + path validation correto | ✅ 3 docs, 6KB total, todos referenciam comandos reais |

---

## Estado pós-B3

- 7/8 backlog itens fechados (item #6 defer)
- Phase Matrix em `docs/nox-neural-memory.md` v14 atualizada (Fase 4 ✅ DONE)
- 3 runbooks novos em `runbooks/` (era só recovery-from-snapshot.md + post-incident-validation.md)
- CONVENTIONS.md cresceu com seção chunk_type + ingest-router doc

---

## Próximos passos

- **04-30 (4d):** salience activation gate
- **05-01 (5d):** section_boost decision gate
- **05-02+:** B2 Tier 2 PDFs (4432 PDFs do HD Mac, dias) — único item POST-GATE significativo restante
- **Wave 1+ (Maio 2026):** Memory Graph Maturity gated por métricas

Não há mais nada significativo pra atacar pré-gate. Sistema em estado ótimo.
