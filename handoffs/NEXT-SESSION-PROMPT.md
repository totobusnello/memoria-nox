# Prompt pra próxima sessão — nox-mem

**Gerado:** 2026-04-24 ~14:05 BRT (dia épico: 10 commits, 6335→9541 chunks, Fase 1.7b-c 100%, HD Mac Tier 1)
**Uso:** copiar o bloco abaixo, colar na próxima janela Claude Code

---

```
Retomando nox-mem pós-sessão 2026-04-24 (dia cheio: Cipher triage, 1.7b-c COMPLETA, HD Mac Tier 1).

CONTEXTO OBRIGATÓRIO — ler ANTES de qualquer ação:
1. /Users/lab/Claude/Projetos/memoria-nox/handoffs/MASTER-HANDOFF-2026-04-24.md  (leitura única — este é o fresh, não o de 23/04)
2. /Users/lab/Claude/Projetos/memoria-nox/CLAUDE.md  (estado + 14 regras críticas)
3. /Users/lab/Claude/Projetos/memoria-nox/plans/2026-04-19-unified-evolution-roadmap.md  (Phase Matrix, Fase 1.7b-c agora ✅ DONE)
4. /Users/lab/Claude/Projetos/memoria-nox/plans/2026-04-24-fase-3-hd-mac-staged.md  (Tier 2/3 PDFs pendente)

SANITY CHECK (1 comando — esperar tudo verde):
ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq "{total:.chunks.total, vc:.vectorCoverage, salience:.salience.mode, section:.sectionDistribution, retention:.retentionDistribution, db:.dbSizeMB}"'
# Esperado: total≥9541, embedded=total, salience.mode=shadow, section.compiled=183, db_mb≈170

SHADOW TELEMETRY (novo — rodou 23:45 BRT ontem):
ssh root@100.87.8.44 'tail -3 /var/log/nox-section-shadow-daily.log | jq .'
# Esperado: entries JSON com by_section (compiled/frontmatter/timeline)

ESTADO ATUAL (2026-04-24 14:05):
- 9541 chunks, 100% embedded, 0 orphans, DB 170MB
- 184 entities ingestadas (2 agents + 1 system + 12 projects + 42 lessons + 127 decisions)
- 2697 chunks em memory/mac-docs/ (HD Mac Tier 1 md+docx)
- Source .md files (projects/decisions/lessons) arquivados — entities substituem
- Schema v10 totalmente utilizado (sections: compiled:183, frontmatter:183, timeline:366, legacy:8809)
- never_decay=104 (core + feedback + person + entity overrides)
- Shadow modes ativos:
  * NOX_SECTION_BOOST_MODE=shadow (active em 7d se baseline OK, ~2026-05-01)
  * NOX_SALIENCE_MODE=shadow (active em 2026-04-30 via activate-salience.sh)
- Claude CLI backend OAuth, fallback sem anthropic/*
- Canários hourly + daily OK
- Arquitetura: core-tier preservation em reindex (bug fixado ontem)
- CLI: nox-mem ingest-entity <file> disponível

10 COMMITS PUSHED HOJE:
c45c207 Fase 3 Tier 1 EXECUTADO (HD Mac 2697 chunks)
edefba5 itens 2+3+4 pós-close 1.7b-c
288d697 telemetria 7d section_boost shadow-mode
63e454a Fase 1.7b-c Chunk 4 — section_boost + /memory-recompile
10c1b92 Fase 1.7b-c chunks 1-3 — migração massiva
dd0484c Opção C housekeeping + core-tier preservation fix
67fa926 MASTER-HANDOFF-2026-04-24 + Cipher diagnostic
8ab3f98 1.7b-c ganha CLI formal (nox-mem ingest-entity)

PRÓXIMA AÇÃO — 3 OPÇÕES (Toto escolhe):

OPÇÃO A — Fase 3 Tier 2 (PDFs text-layer, ~4-5h) — RECOMENDADA
  4432 PDFs do HD Mac → pdftotext → .md → watcher auto-ingest
  [ ] rsync -ah --include='*.pdf' Documents/ VPS:/root/.openclaw/workspace/memory/mac-pdfs-raw/
  [ ] apt-get install poppler-utils (se não tiver)
  [ ] scripts/pdf-text-extract.sh criar (pdftotext loop, skip empty/<20w)
  [ ] Expected: +5000-15000 chunks, DB 170MB → talvez 400MB
  [ ] Monitorar SQLITE_BUSY e vectorize throughput

OPÇÃO B — Enriquecer entities com /memory-recompile (~1-2h)
  Rodar skill em 5-10 entities piloto:
  [ ] /memory-recompile nuvini (project entity)
  [ ] /memory-recompile casa-b-04-boa-vista-village
  [ ] /memory-recompile 2026-04-22-migracao-pro-claude-cli-backend-zero (lesson)
  [ ] Comparar compiled antes/depois, validar Gemini Flash-Lite prompt
  [ ] Search quality A/B vs shadow-mode telemetry

OPÇÃO C — Observar + pequenos Tier 2 incrementais (~30min/dia)
  [ ] Deixar shadow telemetry acumular mais dias
  [ ] Processar ~500 PDFs por vez
  [ ] Sem pressa, sem risco de overload

EVENTOS AGENDADOS:
- 2026-04-30: salience activation (bash activate-salience.sh --apply) — 7d baseline atingido
- 2026-05-01: shadow telemetry analysis (analyze-shadow-telemetry.sh 7) → decidir ativar section_boost
- 2026-05-01: review decisão ativar section_boost active baseado em agregação 7d

CONVENÇÕES OBRIGATÓRIAS:
- set -a; source /root/.openclaw/.env; set +a; antes de CLI nox-mem via SSH
- Nunca confiar última linha CLI — validar via /api/health pós-operação
- Schema changes: migration + backfill, nunca ALTER TABLE solto
- Features que mudam ranking → SHADOW MODE primeiro (1 semana baseline)
- openclaw models auth * invalida monkey-patch E registry — diff+reapply ANTES de restart
- Backup .bak-pre-<feature>-<date> antes de editar arquivos produção
- Validar features com DB state, NUNCA só com logs
- Validar alegações de agents secundários (Cipher/Atlas/etc) ANTES de agir
- Entry point CLI é dist/index.js (não cli.js) — ler package.json.bin
- <!-- retention: X --> HTML comment na frente, NÃO YAML

MEMÓRIAS NOVAS (auto-memory, carregam):
- Cipher diagnostic requer validação independente
- nox-mem CLI entry é dist/index.js + ingest-entity subcommand
- Core-tier preservation exige chamada explícita em reindex/consolidate
- Watcher async processa modify events de rsync automaticamente
- Shadow-mode precisa telemetria real pra decisão informada

Pergunta pro Toto ANTES de começar: A (Tier 2 PDFs) / B (recompile entities) / C (observar)?
```

---

## Uso alternativo — prompt curto (emergência)

```
Retomando nox-mem v3.7+ (schema v10, 9541 chunks). Leia handoffs/MASTER-HANDOFF-2026-04-24.md.
Próximo: Fase 3 Tier 2 (4432 PDFs text-layer) OU /memory-recompile entities piloto.
Sanity: ssh 100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq .chunks.total'
Esperado: 9541+.
Shadow telemetry: tail /var/log/nox-section-shadow-daily.log
Salience activation (2026-04-30): bash /root/.openclaw/scripts/activate-salience.sh --apply
```

---

*Esse arquivo é só um lembrete — copiar o conteúdo pra próxima sessão. Atualizar aqui se o plano mudar antes da próxima janela abrir.*
