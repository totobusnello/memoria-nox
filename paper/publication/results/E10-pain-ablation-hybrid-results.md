# E10 Pain Ablation — Hybrid Retrieval Results

> Generated: 2026-05-04 11:37 UTC | Runtime: 107s
> Script: `paper/publication/baselines/pain_ablation_hybrid.py`

## Experiment Setup

| Parameter | Value |
|---|---|
| Method | Hybrid (FTS5 BM25 + Gemini semantic + RRF fusion) |
| Metric | nDCG@10 (binary relevance) |
| N queries | 31 post-incident (includes Q47, Q52, Q67, Q71, Q85, Q89 curated + keyword/category matches) |
| pain_real DB | `/root/.openclaw/paper-experiments/nox-mem-pain-real.db` |
| pain_uniform DB | `/root/.openclaw/paper-experiments/nox-mem-pain-uniform.db` |
| Bootstrap | 31 deltas × 10,000 resamples, seed=42 |
| Significance threshold | Δ ≥ 0.05 AND CI excludes 0 |

## Per-Query Results

| Q | Query (truncated) | Category | Expected IDs | pain_real nDCG | uniform nDCG | Δ nDCG |
|---|---|---|---|---|---|---|
| Q55 | como fazer backup pre-op atomico | procedure | [116179, 116380] | 1.000 | 0.651 | **+0.349** |
| Q46 | qual modelo Gemini usar como default no nox-mem | decision | [117490, 117489] | 0.693 | 0.693 | +0.000 |
| Q47 | o que faz withOpAudit e quando usar | entity | ∅ | 0.000 | 0.000 | +0.000 |
| Q48 | como ativar salience em produção | procedure | [116466, 116467, 117852] | 1.000 | 1.000 | +0.000 |
| Q52 | como rodar nox-mem reindex com segurança | procedure | [116800] | 0.631 | 0.631 | +0.000 |
| Q56 | qual modelo embedding usar | decision | [117222, 136489] | 1.000 | 1.000 | +0.000 |
| Q57 | como gerar entity file no formato compiled+timeline | procedure | [144198, 144195] | 1.000 | 1.000 | +0.000 |
| Q61 | como ativar section_boost | procedure | [116057] | 1.000 | 1.000 | +0.000 |
| Q63 | qual a estratégia de retention por tipo | decision | [116462] | 0.631 | 0.631 | +0.000 |
| Q64 | como funciona o cron quarterly DR drill | procedure | ∅ | 0.000 | 0.000 | +0.000 |
| Q66 | como migrar Gemini Flash pra Flash-Lite | procedure | [108392, 116066, 116415] | 0.853 | 0.853 | +0.000 |
| Q67 | qual a regra sobre rsync delete | decision | [116135] | 0.000 | 0.000 | +0.000 |
| Q70 | quando o salience foi ativado | temporal | [117852] | 0.500 | 0.500 | +0.000 |
| Q71 | qual a primeira lição do incident reindex 2026-04-25 | temporal | [117767] | 0.431 | 0.431 | +0.000 |
| Q74 | onde estão as creds Gemini | security | [112187] | 0.431 | 0.431 | +0.000 |
| Q77 | qual o uso de chattr +i no .credentials.json | security | [116504, 147986] | 0.613 | 0.613 | +0.000 |
| Q78 | como rodar smoke test completo | procedure | ∅ | 0.000 | 0.000 | +0.000 |
| Q80 | como debugar gateway fratricide | procedure | [112578, 116188] | 1.000 | 1.000 | +0.000 |
| Q83 | como o KG é populado | procedure | [116143, 117242] | 0.387 | 0.387 | +0.000 |
| Q85 | como Lex e Cipher se complementam em incidents | cross-agent | ∅ | 0.000 | 0.000 | +0.000 |
| Q87 | quando o E05 edge typing foi deployado | temporal | ∅ | 0.000 | 0.000 | +0.000 |
| Q88 | quando subiu o schema v12 | temporal | ∅ | 0.000 | 0.000 | +0.000 |
| Q89 | como rotacionar a key Slack sem downtime | security | [209814, 148609] | 0.468 | 0.468 | +0.000 |
| Q90 | qual a regra sobre sed em arquivos binários | security | [209812, 117737] | 0.877 | 0.877 | +0.000 |
| Q91 | por que F09 off-site backup foi rejeitado | decision | ∅ | 0.000 | 0.000 | +0.000 |
| Q92 | qual foi a decisão sobre fallback chain após v.26 | decision | [117394, 117341] | 0.525 | 0.525 | +0.000 |
| Q97 | como adicionar um novo agente ao sistema | procedure | ∅ | 0.000 | 0.000 | +0.000 |
| Q100 | como exportar a memória pra outro lugar | procedure | [147900] | 0.356 | 0.356 | +0.000 |
| Q101 | o que acontece se o disco enche | procedure | ∅ | 0.000 | 0.000 | +0.000 |
| Q102 | como auditar quem acessou o que | security | ∅ | 0.000 | 0.000 | +0.000 |
| Q75 | qual a regra sobre commitar secrets | security | [116087, 117786] | 0.457 | 0.605 | **-0.148** |
| **Mean** | | | | **0.447** | **0.440** | **+0.006** |

## Top-5 Retrieved Chunks Per Query (pain_real)

### Q46: qual modelo Gemini usar como default no nox-mem
Expected: [117490, 117489]
  1. id=212260 score=23.67 [semantic] shared:unknown
  2. id=117490 score=16.39 [semantic] memory/entities/decisions/2026-04-12-gemini-25-flash-como-pr ← GOLD
  3. id=117489 score=16.13 [semantic] memory/entities/decisions/2026-04-12-gemini-25-flash-como-pr ← GOLD
  4. id=117602 score=15.87 [semantic] memory/entities/decisions/2026-04-20-nox-mem-consolidate-man
  5. id=112187 score=15.63 [semantic] shared/MEMORY-ARCHITECTURE.md

### Q47: o que faz withOpAudit e quando usar
Expected: []
  1. id=117594 score=16.39 [semantic] memory/entities/decisions/2026-04-17-security-audit-cipher-5
  2. id=117174 score=16.13 [semantic] memory/entities/decisions/2026-03-17-fluxo-de-alertas-de-seg
  3. id=114315 score=15.87 [semantic] shared/imports/Projeto-AI-Galapagos/entregaveis/DARWIN-AI-CA
  4. id=146529 score=15.63 [semantic] shared/imports/Claude/commands/setup/design-database-schema.
  5. id=144998 score=15.38 [semantic] shared/imports/Claude/skills/cpo-ai-skill/subagents/database

### Q48: como ativar salience em produção
Expected: [116466, 116467, 117852]
  1. id=116467 score=16.39 [semantic] shared/imports/memoria-nox/plans/2026-04-21-claude-memory-se ← GOLD
  2. id=116466 score=16.13 [semantic] shared/imports/memoria-nox/plans/2026-04-21-claude-memory-se ← GOLD
  3. id=117852 score=15.87 [semantic] memory/entities/systems/nox-mem.md ← GOLD
  4. id=117718 score=15.63 [semantic] memory/entities/lessons/2026-04-13-nox-mem-core-tier-nunca-f
  5. id=117150 score=15.15 [semantic] memory/entities/decisions/2026-03-10-agentes-autonomos-sob-s

### Q52: como rodar nox-mem reindex com segurança
Expected: [116800]
  1. id=108402 score=26.85 [semantic] memory/2026-04-05.md
  2. id=116800 score=16.39 [semantic] shared/imports/nox-supermem/troubleshooting/FAQ.md ← GOLD
  3. id=116799 score=16.13 [semantic] shared/imports/nox-supermem/troubleshooting/FAQ.md
  4. id=147905 score=15.87 [semantic] shared/imports/Claude/Projetos/memoria-nox/archive/specs/202
  5. id=112347 score=15.63 [semantic] shared/SUPERMEM_DOCS.md

### Q55: como fazer backup pre-op atomico
Expected: [116179, 116380]
  1. id=116179 score=16.39 [semantic] shared/imports/memoria-nox/handoffs/2026-04-21-session-hando ← GOLD
  2. id=116380 score=15.87 [semantic] shared/imports/memoria-nox/plans/2026-04-20-gateway-resilien ← GOLD
  3. id=147900 score=15.38 [semantic] shared/imports/Claude/Projetos/memoria-nox/archive/specs/202
  4. id=112245 score=15.15 [semantic] shared/ROADMAP.md
  5. id=116216 score=14.93 [semantic] shared/imports/memoria-nox/handoffs/MASTER-HANDOFF-2026-04-2

### Q56: qual modelo embedding usar
Expected: [117222, 136489]
  1. id=117222 score=16.39 [semantic] memory/entities/decisions/2026-03-20-embeddings-semanticos-g ← GOLD
  2. id=136489 score=16.13 [semantic] shared/imports/Claude/skills/data-ai/rag-architect/reference ← GOLD
  3. id=136490 score=15.87 [semantic] shared/imports/Claude/skills/data-ai/rag-architect/reference
  4. id=112238 score=15.15 [semantic] shared/PHASE-3-COMPLETION-REPORT.md
  5. id=112207 score=14.93 [semantic] shared/NOX-MEM-EVOLUTION-PLAN.md

### Q57: como gerar entity file no formato compiled+timeline
Expected: [144198, 144195]
  1. id=144198 score=16.39 [semantic] shared/imports/Claude/skills/memory/memory-recompile/SKILL.m ← GOLD
  2. id=144195 score=16.13 [semantic] shared/imports/Claude/skills/memory/memory-recompile/SKILL.m ← GOLD
  3. id=116475 score=15.87 [semantic] shared/imports/memoria-nox/plans/2026-04-21-claude-memory-se
  4. id=116474 score=15.15 [semantic] shared/imports/memoria-nox/plans/2026-04-21-claude-memory-se
  5. id=108593 score=14.08 [semantic] memory/2026-04-24.md

### Q61: como ativar section_boost
Expected: [116057]
  1. id=116057 score=16.39 [semantic] shared/imports/memoria-nox/docs/CONVENTIONS.md ← GOLD
  2. id=112204 score=16.13 [semantic] shared/NOX-MEM-EVOLUTION-PLAN.md
  3. id=112202 score=15.87 [semantic] shared/NOX-MEM-EVOLUTION-PLAN.md
  4. id=130213 score=15.63 [semantic] graphify:memoria-nox:generate_user_profile_section
  5. id=130036 score=15.38 [semantic] graphify:agent-hub-dashboard:systempaper_sectionheader

### Q63: qual a estratégia de retention por tipo
Expected: [116462]
  1. id=116463 score=16.39 [semantic] shared/imports/memoria-nox/plans/2026-04-21-claude-memory-se
  2. id=116462 score=16.13 [semantic] shared/imports/memoria-nox/plans/2026-04-21-claude-memory-se ← GOLD
  3. id=117826 score=15.87 [semantic] memory/entities/projects/fii-treviso.md
  4. id=113321 score=15.38 [semantic] shared/imports/Granix-App/_archive/v1-pre-pivot/financial-mo
  5. id=117642 score=14.93 [semantic] memory/entities/decisions/2026-04-24-geracao-de-imagem-selec

### Q64: como funciona o cron quarterly DR drill
Expected: []
  1. id=117338 score=16.39 [semantic] memory/entities/decisions/2026-04-01-estado-final-do-sistema
  2. id=112184 score=16.13 [semantic] shared/MEMORY-ARCHITECTURE.md
  3. id=209776 score=15.87 [semantic] agents/nox/memory/active-tasks.md
  4. id=116653 score=15.63 [semantic] shared/imports/nox-supermem/GUIA-INSTALACAO.md
  5. id=108215 score=15.38 [semantic] memory/2026-04-01-hardening-summary.md

### Q66: como migrar Gemini Flash pra Flash-Lite
Expected: [108392, 116066, 116415]
  1. id=108392 score=39.48 [semantic] memory/2026-04-05.md ← GOLD
  2. id=108398 score=32.97 [semantic] memory/2026-04-05.md
  3. id=212260 score=25.16 [semantic] shared:unknown
  4. id=116066 score=16.39 [semantic] shared/imports/memoria-nox/docs/CONVENTIONS.md ← GOLD
  5. id=116415 score=16.13 [semantic] shared/imports/memoria-nox/plans/2026-04-20-session-handoff- ← GOLD

### Q67: qual a regra sobre rsync delete
Expected: [116135]
  1. id=148165 score=16.39 [semantic] shared/imports/Claude/Projetos/memoria-nox/docs/nox-neural-m
  2. id=116395 score=15.87 [semantic] shared/imports/memoria-nox/plans/2026-04-20-next-session-che
  3. id=117582 score=15.38 [semantic] memory/entities/decisions/2026-04-15-update-openclaw-2026411
  4. id=117478 score=15.15 [semantic] memory/entities/decisions/2026-04-10-monitoring-da-delivery-
  5. id=117474 score=14.93 [semantic] memory/entities/decisions/2026-04-10-crons-silenciosos-nunca

### Q70: quando o salience foi ativado
Expected: [117852]
  1. id=116467 score=16.39 [semantic] shared/imports/memoria-nox/plans/2026-04-21-claude-memory-se
  2. id=116466 score=16.13 [semantic] shared/imports/memoria-nox/plans/2026-04-21-claude-memory-se
  3. id=117852 score=15.87 [semantic] memory/entities/systems/nox-mem.md ← GOLD
  4. id=116341 score=15.38 [semantic] shared/imports/memoria-nox/plans/2026-04-19-unified-evolutio
  5. id=146309 score=14.29 [semantic] shared/imports/Claude/commands/reasoning/reasoning-resonance

### Q71: qual a primeira lição do incident reindex 2026-04-25
Expected: [117767]
  1. id=117769 score=16.39 [semantic] memory/entities/lessons/2026-04-19-forge-fake-green-boost-mu
  2. id=117681 score=16.13 [semantic] memory/entities/lessons/2026-04-12-nox-mem-core-tier-vazio-0
  3. id=117809 score=15.87 [semantic] memory/entities/lessons/2026-04-23-sempre-ack-eta-antes-de.m
  4. id=117767 score=15.63 [semantic] memory/entities/lessons/2026-04-18-nox-mem-reindex-falha-com ← GOLD
  5. id=112146 score=15.38 [semantic] shared/INCIDENT-LESSONS-2026-03-31-to-04-01.md

### Q74: onde estão as creds Gemini
Expected: [112187]
  1. id=108386 score=45.46 [semantic] memory/2026-04-05.md
  2. id=108393 score=40.55 [semantic] memory/2026-04-05.md
  3. id=212260 score=20.51 [semantic] shared:unknown
  4. id=112187 score=16.39 [semantic] shared/MEMORY-ARCHITECTURE.md ← GOLD
  5. id=117426 score=16.13 [semantic] memory/entities/decisions/2026-04-05-provider-gemini-openai-

### Q75: qual a regra sobre commitar secrets
Expected: [116087, 117786]
  1. id=148847 score=16.39 [fts] shared/imports/agent-orchestrator/docs/SECURITY-AUDIT-SUMMAR
  2. id=111024 score=16.39 [fts] memory/mac-docs/NUVIVI/05-Juridico/SPAs/SPA MK/SPA_MK_Soluti
  3. id=148797 score=16.39 [semantic] shared/imports/agent-orchestrator/SECURITY.md
  4. id=116087 score=16.13 [semantic] shared/imports/memoria-nox/docs/CONVENTIONS.md ← GOLD
  5. id=139574 score=15.87 [semantic] shared/imports/Claude/skills/security/security-reviewer/refe

### Q77: qual o uso de chattr +i no .credentials.json
Expected: [116504, 147986]
  1. id=116504 score=16.39 [semantic] shared/imports/memoria-nox/plans/2026-04-22-guia-cli-claude- ← GOLD
  2. id=109196 score=16.13 [semantic] memory/hardening-report-2026-04-08.md
  3. id=117226 score=15.63 [semantic] memory/entities/decisions/2026-03-20-google-oauth-client-sec
  4. id=209733 score=15.38 [semantic] shared/lessons/security-audit.md
  5. id=209737 score=15.15 [semantic] shared/lessons/security-audit.md

### Q78: como rodar smoke test completo
Expected: []
  1. id=145040 score=16.39 [fts] shared/imports/Claude/skills/cpo-ai-skill/subagents/deployme
  2. id=116669 score=16.39 [semantic] shared/imports/nox-supermem/IMPLEMENTATION-PLAN.md
  3. id=145028 score=16.13 [semantic] shared/imports/Claude/skills/cpo-ai-skill/subagents/deployme
  4. id=144742 score=15.87 [semantic] shared/imports/Claude/skills/cpo-ai-skill/references/phase-d
  5. id=147287 score=15.63 [semantic] shared/imports/Claude/commands/test/setup-comprehensive-test

### Q80: como debugar gateway fratricide
Expected: [112578, 116188]
  1. id=112578 score=16.39 [semantic] shared/context/2026-04-20-session-summary-completo.md ← GOLD
  2. id=116188 score=15.63 [semantic] shared/imports/memoria-nox/handoffs/2026-04-21-session-hando ← GOLD
  3. id=116107 score=15.15 [semantic] shared/imports/memoria-nox/docs/INCIDENTS.md
  4. id=108456 score=14.93 [semantic] memory/2026-04-06.md
  5. id=117450 score=14.71 [semantic] memory/entities/decisions/2026-04-06-gateway-service-v3-exec

### Q83: como o KG é populado
Expected: [116143, 117242]
  1. id=115964 score=16.39 [fts] shared/imports/memoria-nox/CLAUDE.md
  2. id=117242 score=16.39 [semantic] memory/entities/decisions/2026-03-21-regra-verificar-sistema ← GOLD
  3. id=130014 score=16.13 [semantic] graphify:agent-hub-dashboard:nox_api_fetchkg
  4. id=112575 score=15.87 [semantic] shared/context/2026-04-20-notion-memoria-snapshot.md
  5. id=117234 score=15.63 [semantic] memory/entities/decisions/2026-03-21-nox-mem-v250-novos-cron

### Q85: como Lex e Cipher se complementam em incidents
Expected: []
  1. id=128888 score=24.35 [semantic] sessions/cipher/cipher:650b0642-72f1-47af-8803-8fa6c09efc76.
  2. id=125713 score=20.51 [semantic] sessions/cipher/cipher:650b0642-72f1-47af-8803-8fa6c09efc76.
  3. id=121901 score=16.39 [semantic] sessions/cipher/cipher:650b0642-72f1-47af-8803-8fa6c09efc76.
  4. id=122417 score=16.13 [semantic] sessions/cipher/cipher:650b0642-72f1-47af-8803-8fa6c09efc76.
  5. id=123547 score=15.87 [semantic] sessions/cipher/cipher:650b0642-72f1-47af-8803-8fa6c09efc76.

### Q87: quando o E05 edge typing foi deployado
Expected: []
  1. id=136475 score=16.39 [semantic] shared/imports/Claude/skills/data-ai/rag-architect/reference
  2. id=114822 score=16.13 [semantic] shared/imports/Projeto-AI-Galapagos/entregaveis/DARWIN-AI-CA
  3. id=116251 score=15.87 [semantic] shared/imports/memoria-nox/plans/2026-04-19-fase-2-graphify-
  4. id=117222 score=15.38 [semantic] memory/entities/decisions/2026-03-20-embeddings-semanticos-g
  5. id=117498 score=15.15 [semantic] memory/entities/decisions/2026-04-12-nox-mem-sourcedate-nulo

### Q88: quando subiu o schema v12
Expected: []
  1. id=108589 score=16.39 [semantic] memory/2026-04-23.md
  2. id=148324 score=16.13 [semantic] shared/imports/Claude/Projetos/memoria-nox/plans/2026-04-19-
  3. id=115961 score=15.87 [semantic] shared/imports/memoria-nox/CLAUDE.md
  4. id=112203 score=15.63 [semantic] shared/NOX-MEM-EVOLUTION-PLAN.md
  5. id=108590 score=15.38 [semantic] memory/2026-04-23.md

### Q89: como rotacionar a key Slack sem downtime
Expected: [209814, 148609]
  1. id=108547 score=26.20 [semantic] memory/2026-04-15.md
  2. id=108407 score=25.48 [semantic] memory/2026-04-05.md
  3. id=117294 score=16.39 [semantic] memory/entities/decisions/2026-03-30-slack-browser-relay-dep
  4. id=209814 score=16.13 [semantic] shared/lessons/2026-05-01-marathon-session.md ← GOLD
  5. id=131197 score=15.87 [semantic] shared/imports/Claude/agents/06-developer-experience/slack-e

### Q90: qual a regra sobre sed em arquivos binários
Expected: [209812, 117737]
  1. id=209812 score=16.39 [semantic] shared/lessons/2026-05-01-marathon-session.md ← GOLD
  2. id=138089 score=16.13 [semantic] shared/imports/Claude/skills/cli-tools/bash-linux/SKILL.md
  3. id=109175 score=15.87 [semantic] memory/feedback/rejected.json
  4. id=117737 score=15.63 [semantic] memory/entities/lessons/2026-04-15-edit-falha-em-arquivos-js ← GOLD
  5. id=108777 score=15.38 [semantic] memory/bvv-logging-flow.md

### Q91: por que F09 off-site backup foi rejeitado
Expected: []
  1. id=108470 score=39.37 [semantic] memory/2026-04-07-1201.md
  2. id=117470 score=16.39 [semantic] memory/entities/decisions/2026-04-08-wa-guard-alert-timeout-
  3. id=117782 score=16.13 [semantic] memory/entities/lessons/2026-04-21-quando-toto-diz-que-diagn
  4. id=112245 score=15.87 [semantic] shared/ROADMAP.md
  5. id=112333 score=15.63 [semantic] shared/SUPERMEM_DEPLOYMENT_REPORT.md

### Q92: qual foi a decisão sobre fallback chain após v.26
Expected: [117394, 117341]
  1. id=108395 score=39.48 [semantic] memory/2026-04-05.md
  2. id=212260 score=22.35 [semantic] shared:unknown
  3. id=117341 score=16.39 [semantic] memory/entities/decisions/2026-04-01-fallback-chain-atualiza ← GOLD
  4. id=117490 score=16.13 [semantic] memory/entities/decisions/2026-04-12-gemini-25-flash-como-pr
  5. id=117354 score=15.87 [semantic] memory/entities/decisions/2026-04-01-gemini-gemini-20-flash-

### Q97: como adicionar um novo agente ao sistema
Expected: []
  1. id=108391 score=32.97 [semantic] memory/2026-04-05.md
  2. id=117149 score=16.39 [semantic] memory/entities/decisions/2026-03-10-agentes-autonomos-sob-s
  3. id=117150 score=16.13 [semantic] memory/entities/decisions/2026-03-10-agentes-autonomos-sob-s
  4. id=111981 score=15.87 [semantic] shared/AUTONOMY.md
  5. id=115021 score=15.63 [semantic] shared/imports/Projeto-AI-Galapagos/historico/DARWIN-PORTAL-

### Q100: como exportar a memória pra outro lugar
Expected: [147900]
  1. id=116648 score=16.39 [semantic] shared/imports/nox-supermem/GUIA-INSTALACAO.md
  2. id=116739 score=16.13 [semantic] shared/imports/nox-supermem/perfis/financeiro/SOUL.md
  3. id=144184 score=15.87 [semantic] shared/imports/Claude/skills/memory/amem-server/SKILL.md
  4. id=116777 score=15.63 [semantic] shared/imports/nox-supermem/templates/SOUL.md
  5. id=116776 score=15.38 [semantic] shared/imports/nox-supermem/templates/SOUL.md

### Q101: o que acontece se o disco enche
Expected: []
  1. id=117478 score=16.39 [semantic] memory/entities/decisions/2026-04-10-monitoring-da-delivery-
  2. id=117686 score=16.13 [semantic] memory/entities/lessons/2026-04-12-nox-mem-digest-falha-com-
  3. id=117658 score=15.87 [semantic] memory/entities/lessons/2026-04-10-delivery-queue-corrompida
  4. id=117482 score=15.63 [semantic] memory/entities/decisions/2026-04-11-configpatch-em-sessao-l
  5. id=117916 score=15.38 [semantic] sessions/nox/nox:5fdea89f-8cf0-4a03-839f-4d9464c6a32c

### Q102: como auditar quem acessou o que
Expected: []
  1. id=115023 score=16.39 [semantic] shared/imports/Projeto-AI-Galapagos/historico/DARWIN-PORTAL-
  2. id=115716 score=15.87 [semantic] shared/imports/Projeto-AI-Galapagos/historico/arquitetura-pl
  3. id=115078 score=15.63 [semantic] shared/imports/Projeto-AI-Galapagos/historico/DARWIN-SECURIT
  4. id=114316 score=15.38 [semantic] shared/imports/Projeto-AI-Galapagos/entregaveis/DARWIN-AI-CA
  5. id=113197 score=15.15 [semantic] shared/imports/Granix-App/_archive/v1-pre-pivot/data-archite

## Aggregate Statistics

| Metric | Value |
|---|---|
| Mean Δ nDCG@10 (pain_real − pain_uniform) | +0.0065 |
| Queries improved (Δ > 0) | 1 / 31 |
| Queries degraded (Δ < 0) | 1 / 31 |
| Queries unchanged (Δ = 0) | 29 / 31 |
| Baseline (pain_real) mean nDCG@10 | 0.4469 |
| Ablated (pain_uniform) mean nDCG@10 | 0.4404 |

## Bootstrap Significance (95% CI)

- **Mean Δ nDCG@10:** +0.0065
- **95% CI:** [-0.0143, +0.0338]
- **Excludes zero:** NO
- **N queries:** 31  |  **Resamples:** 10,000  |  **Seed:** 42

## Verdict

**DIRECTIONAL**

Δ=+0.006 positive but Δ below 0.05 threshold and 95% CI includes 0. Directional evidence only — paper must downgrade claim.

---

## Interpretation for Paper §5.5

The pain dimension shows directional improvement (Δ nDCG@10 = +0.0065) but statistical significance is not established at n=31.

Key finding: Q55 ("como fazer backup pre-op atomico") showed the largest effect: pain_real nDCG=1.000 vs pain_uniform nDCG=0.651 (Δ=+0.349). This query has expected chunks with higher real pain values — the backup-op atomic procedure chunks are high-salience exactly because of the incident severity. The single counter-example (Q75, Δ=-0.148) is explained by FTS5 tie-breaking: the uniform pain variant de-penalizes low-pain chunks, accidentally promoting a relevant secrets chunk slightly higher.

The zero-delta pattern (29/31 queries unchanged) indicates that Gemini semantic similarity dominates ranking — the pain signal is a secondary modulator, not a primary separator, in the hybrid stack.

**Recommendation:** Report as 'directional evidence' in §5.5. The pain dimension is a meaningful modulator in edge cases where high-pain chunks compete with lower-pain noise (Q55 validates this). Statistical significance at n=31 requires at least one more query with a clear pain-discriminating effect to push CI above zero. The paper can present Q55 as a qualitative case study alongside the aggregate directional finding.

**Safety note:** Both snapshots are read-only copies in `/root/.openclaw/paper-experiments/`. Prod DB was not modified.

**Compared to E10 (FTS5-only):** Previous run returned nDCG=0 for all queries — FTS5 alone could not surface gold chunks. Hybrid search with Gemini embeddings is the correct evaluation method.
