# nox-mem ROADMAP — Q/A/P + Lab

> **"Hybrid memory with shadow discipline — yours by design."**
>
> Single source of truth. Reorganized **2026-05-17 night** during overnight automode push.
> v1 (630 lines, cluttered with session logs) archived at `docs/_archive/ROADMAP-v1-pre-Q-A-P-2026-05-17.md`.
> **Atualizado 2026-05-18 pós Wave H** — 69 PRs merged, todos os pilares cobertos com implementação.

---

## TL;DR

3 product pillars + 1 research lab + 1 conditional GTM phase. **60% capacity on product, 40% on research.**

| Track | Why | Sprints | Status |
|---|---|---|---|
| **Q — Quality** | Numbers that lead the market | Q1-Q4 | Q1+Q2+Q3 scaffolded + Q2.1 CLI; Q4 harness + COMPARISON.md populated; full runs pendente VPS |
| **A — Autonomy** | Data yours, provider your choice, zero vendor lock-in | A1-A4+A1.1 | A1 impl staged; **A1.1 BR PII shipped**; A2+A3 impl completo (T1-T18); **A4 100% runnable em CI** |
| **P — Product** | UX that ships | P1-P5+P5a | P1 impl completo (T1-T14); P2 impl completo (T1-T15); P3 impl staged; P4 spec+kickoff; **P5 impl completo** + P5a event bus merged |
| **Lab — Retrieval Research** | Paper-grade improvements, 40% capacity | L1-L4 | L1 paused; **L2 impl completo** (T1-T12); **L3 impl completo** (T1-T13); **L4 regex-first impl completo** |
| **GTM Phase 2** | Viral launch | conditional | Assets + pricing + demo script + COMPARISON.md + README final + Docker — zero blocker quando Q4 gate abrir |

---

## 1. Posicionamento estratégico

### O moat real (definido 2026-05-17 análise vs memanto + agentmemory)

| Eixo | memanto | agentmemory | nox-mem |
|---|---|---|---|
| **Data autonomy** | ❌ SaaS Moorcheh | ⚠️ iii-engine runtime | ✅ **SQLite file, `cp` é backup** |
| **Provider lock** | ❌ Moorcheh fechado | ⚠️ iii proprietary | ✅ **Bring your own key** |
| **Self-host real** | ❌ | ⚠️ com lock-in | ✅ sem lock-in |
| **Inspectable** | ❌ | ⚠️ via iii API | ✅ `sqlite3 nox-mem.db` |
| **Quality bias** | Moorcheh black box | mix vendors | ✅ Gemini 3072d (best public) |

### Pitch headline
> **"A única memória de agent que é genuinamente sua. SQLite no seu disco, provider sua escolha, zero vendor lock-in."**

### Diferenciação técnica (manter como moat de pesquisa)
- Pain-weighted salience (`recency × pain × importance`) — único
- Shadow discipline (arquitetural ≥7d antes de ativar) — único
- KG edge typing (relation_reason enum) — único
- Compiled/timeline/frontmatter sections com section_boost — único

---

## 2. Estado atual (snapshot 2026-05-18 pós Wave H)

```
Sistema:        nox-mem v3.7+, schema v22 (v11/v19/v20/v21/v22 migrados), ops_audit append-only
Chunks:         69.298+ (99.97% embedded, Gemini 3072d) — fts_anchor populated
DB size:        ~1.24 GB
KG:             15.646 entities / 21.533 relations
Agentes:        7 (1 main Maestro + 6 personas: nox/atlas/boris/cipher/forge/lex)
OpenClaw:       v2026.4.29
Eval nDCG@10:   0.6813 (n=78 honest golden set, run 85)
Vs paper baseline (0.5831): +16.9% relativo / +9.8pp absoluto

Features ranking ATIVAS:
 ✅ Salience (recency × pain × importance) — G01 2026-04-30
 ✅ Section boost (compiled +100%, frontmatter +49%) — G02 2026-05-01
 ✅ Edge typing (relation_reason enum 7) — E05 Phase 1 2026-05-02
 ✅ Temporal boost (E13) — 2026-05-06
 ✅ SPO Injection (E03b, integrated em CLI) — 2026-05-17
 ✅ E-lite-2 (fts_anchor bilingual) — 2026-05-17 (Wave 1 E14)
 ✅ D (language-aware RRF weights) — 2026-05-17 (Wave 1 E14)
 ✅ L4 regex-first KG extraction (Gemini fallback) — 2026-05-18 (Wave B, OPEX -80%)
 ✅ L2 conflict detection (KG) — 2026-05-18 (Wave C)
 ✅ L3 confidence + provenance — 2026-05-18 (Wave C, gated em ranking por eval)

Features CORTADAS (lições codificadas em DECISIONS.md):
 ❌ Reason boost (D38), Focus boost (D36), Reranker v1+v2 (CUT), A1/A2/G (D39)

Wave A→H entregues (2026-05-17 noite → 2026-05-18):
 69 PRs merged | ~55.000 LOC | 1.100+ testes | 5 schema migrations (v11/v19/v20/v21/v22)
 CI verde (eval harnesses + privacy filter + zero-vendor + typecheck + cross-pillar)
 Docker: Dockerfile + docker-compose + CI build image
 Ops: DR + BACKUP + MONITORING runbooks
 Security: THREAT-MODEL.md v1.1, G1-G17 todos endereçados
 GTM: pricing strategy + ROI calculator + demo video script + README final
```

---

## 3. Pillar Q — Quality (números que lideram)

Objetivo: provar nox-mem #1 (ou identificar gap exato) com benchmarks padrão indústria.

### Sprints

| Sprint | DoD | Status | Spec/PR |
|---|---|---|---|
| **Q1** LoCoMo R@5 publicado | R@5, R@1, MRR, nDCG@10 + Wilson CI, full run reproducible | **Scaffolded** 2026-05-17 — full run pendente VPS | PR #6 (eval/locomo/) |
| **Q2** LongMemEval task accuracy | Accuracy % + per-category, LLM-as-judge GPT-4o + Gemini 2.5-pro | **Scaffolded + CLI first-class** 2026-05-18 — full run pendente VPS | PR #12 + #29 (eval/longmemeval/) |
| **Q3** Latency p50/p95/p99 | Cold + warm, 6 workloads, sub-ms accuracy | **Scaffolded** 2026-05-17 — full run pendente VPS | PR #11 (eval/latency/) |
| **Q4** Public COMPARISON.md | nox-mem vs agentmemory + memanto + mem0 + Letta + Zep, todos rodados localmente | **Harness scaffolded + COMPARISON.md populated** 2026-05-18 (gated por Q1+Q2+Q3 winning) | PR #23 + #47 |

### Métrica-alvo (working hypothesis)
- LoCoMo R@5 ≥ 90% (agentmemory: 95.2%, Letta: 83.2%, mem0: 68.5%)
- LongMemEval task accuracy ≥ 85% (memanto: 89.8%, paper SOTA ~96%)
- Latency p95 ≤ 200ms (memanto: "sub-90ms" claim)

### Gate
Q4 só pública depois de Q1+Q2+Q3 com números defensáveis E nox-mem em cima ou empatando. Honestidade transparente: se ficarmos abaixo, **não publicamos, voltamos pra lab**.

---

## 4. Pillar A — Autonomy (data é sua, provider sua escolha)

Objetivo: tornar o moat "sem vendor lock-in" tangível e auditável.

### Sprints

| Sprint | DoD | Status | Spec/PR |
|---|---|---|---|
| **A1** Privacy filter pre-storage | 13+ patterns, `<private>` tag, 30+ tests, integrated in ingest-router | **Implemented** 2026-05-17 (staged, 68 tests passing, FP 1.7%) | PR #5 |
| **A1.1** BR PII patterns | CPF/CNPJ/pix/CEP/RG — addressa G2 CRITICAL do threat model | **Shipped** 2026-05-18 (Wave F) | PR #64 |
| **A2** Schema export/import portable | tar.gz archive, AES-256-GCM encrypt-by-default, round-trip preserves nDCG@10 ±0.001 | **Implementação completa** T1-T18 (Wave overnight+B) — staged | PR #37 + #41 |
| **A3** Provider abstraction layer | EmbeddingProvider + LLMProvider interfaces, env-driven selection, fallback + cost cap | **Implementação completa** T1-T16 (Wave overnight+B) — staged | PR #36 + #39 |
| **A4** Zero-vendor validation suite | 8 checks, **todos CI-runnable**, <1s runtime | **100% completo** 2026-05-18 | PR #14 + #20 |

### Princípios não-negociáveis
- Chaves direto no provider, NUNCA proxy nosso
- Manifesto de archive aberto (`tar -tzf` mostra tudo)
- Schema v* sempre forward-migratable, falha clara em downgrade
- BYO key obrigatório (sem chaves embutidas em build)

---

## 5. Pillar P — Product (UX que ganha)

Objetivo: UX competitiva com agentmemory + memanto, sem comprometer pilares Q+A.

### Sprints

| Sprint | DoD | Status | Spec/PR |
|---|---|---|---|
| **P1** `answer` primitive | CLI + API + MCP `nox_mem_answer`, citação por chunk_id, anti-hallucination guard | **Implementação completa** T1-T14 (Wave overnight+B) — p95=101ms (42× under budget) | PR #31 + #34 + #40 |
| **P2** Auto-capture via Claude Code hooks | 5 hooks (SessionStart/UserPromptSubmit/PostToolUse/Stop/PreCompact), zero manual ingest, 5 layers privacy defense | **Implementação completa** T1-T15 (Wave B) | PR #43 |
| **P3** Temporal queries `--as-of` `--changed-since` | CLI + API + MCP, hard pre-filter (não boost), 23 tests | **Implemented** 2026-05-17 (staged) | PR #2 |
| **P4** `nox-mem connect <ide>` | Tier A (Claude Code + Cursor + Codex deep) + Tier B (10 IDEs MCP-passive) | **Spec + kickoff** 2026-05-18 — 13 IDEs cobertos | PR #7 + #21 |
| **P5** Real-time viewer upgrade | SSE + 4 panels (live feed/counters/charts/heatmap), <500ms ingest→event | **Implementação completa** T1-T15 (Wave B) — 11.7KB bundle vanilla JS | PR #10 + #33 + #42 |
| **P5a** Event bus refactor | P5 prerequisite, isolates SSE from ingest path | **Shipped** 2026-05-18 (Wave overnight) | PR #33 |

### Marketing message
> "Memória deep pro stack que você usa de verdade, não memória pra qualquer IDE."

---

## 6. Lab — Retrieval Research (40% capacity)

| Sprint | Foco | Status |
|---|---|---|
| **L1** E15 CodeGraph-inspired improvements (A+B+C, 4-7h) | Spec gravado pré-Q/A/P pivot | **Pausado** 2026-05-17, retoma pós-Q1 |
| **L2** Conflict/contradiction detection sobre KG (memanto-inspired) | Detectar relations opostas no mesmo sujeito | **Implementação completa** T1-T12 (Wave C) | PR #13 + #51 |
| **L3** Confidence + provenance field schema v19 (memanto-inspired) | Só se eval mostrar lift (gated) — ranking integration aguarda gate ≥1.0pp | **Implementação completa** T1-T13 (Wave C) — schema shipped, ranking gated | PR #15 + #48 |
| **L4** Regex-first KG extraction com Gemini fallback (gbrain-inspired) | OPEX -80% eliminando Gemini calls em links explícitos | **Implementação completa** T1-T9 (Wave overnight+B) — 95.8% precision, 80% Gemini savings | PR #27 + #35 + #38 |

---

## 7. GTM Phase 2 — Viral launch (CONDITIONAL)

**Locked behind:** Q4 publica COMPARISON.md com nox-mem em cima ou empatando topo.

**Assets entregues (Wave B→H):**
- PR #16: spec README hero upgrade (~3,850 words)
- PR #19: 20 assets palette D (banner + 6 stat SVGs + logo + arch PNG), accent `#00C896`
- PR #22: README-DRAFT.md (276 linhas, assets wired)
- PR #46: README.md **final canonical** (Wave D numbers + competitive positioning)
- PR #47: COMPARISON.md populated — 7 competitors, Gate via `GATE_VERIFIED=1`
- PR #49: COMPETITIVE-POSITIONING.md — Six Gaps matrix
- PR #63: demo video script + recording plan + messaging guide
- PR #67: docs/ops/ DR + BACKUP + MONITORING runbooks
- PR #68: Docker Dockerfile + docker-compose + CI build
- PR #69: docs/gtm/PRICING-STRATEGY + ROI-CALCULATOR + cost model

Quando o gate abrir, executar playbook agentmemory:
- Hero visual upgrade README (logo SVG + 6 stat SVGs custom + demo GIF + arch PNG + TOC bar)
- Trendshift badge + Star History chart
- Viral GitHub gist com design doc
- Product Hunt launch
- Twitter/HN thread coordenado
- Nox-Supermem landing page (Hotmart conversion path)
- Paper distribution (drafts já em paper/publication/distribution/)

**Targets pós-launch:**
- 1k stars em 30 dias
- Top 10 trending TS/AI em GitHub
- Inclusão em listas de "agent memory tools" curadas

---

## 8. Calendário (ordem recomendada)

```
Nov-Dez 2025:  Q1 + Q2 + Q3 rodar full (não só scaffold) — números defensáveis
               A1 ship to prod (staged → merged)
               A2 + A3 implementation
               A4 ship validation suite

Jan 2026:      P1 + P3 ship (answer primitive + temporal queries)
               P2 implementation (hooks auto-capture)
               L1 retomado (E15)
               Q4 gate check: comparison wins? → GTM Phase 2 disparado

Fev-Mar 2026:  P4 + P5 implementation
               GTM Phase 2 launch (se gate Q4 abriu)

Abr+ 2026:     L2 conflict detection
               L3 confidence (se eval mostrar lift)
               Iteração com feedback da comunidade
```

---

## 9. Convenções

- **Specs canônicos:** `specs/YYYY-MM-DD-{pilar}{N}-{slug}.md` (ex: `specs/2026-05-17-P1-answer-primitive.md`)
- **Branches overnight:** `overnight/YYYY-MM-DD/{pilar}{N}-{slug}`
- **PR title pattern:** `[overnight] {pilar}{N} — {one-line}` (não-overnight: `{prefix}({scope}): summary`)
- **Métricas em PR:** sempre incluir DoD checklist + acceptance criteria
- **Shadow discipline:** features de ranking/scoring exigem ≥7d shadow-mode antes de ativar (regra crítica #5 CLAUDE.md)

---

## 10. Decoder de namespaces antigos

| Namespace antigo | Novo |
|---|---|
| F (Foundation), R (Research), G (Gate), D (Decision) | Mantidos — cross-ref histórico |
| E13 Temporal boost ativo | Re-tagueado como **L0** (lab done) |
| E14 Wave 1 (E-lite-2, D) ativo | Re-tagueado como **L0** (lab done) |
| E15 CodeGraph | **L1** (paused) |
| A1/A2/A3 ingest-router pré-pivot | Mantidos; novo A1/A2/A3 são autonomy pillar sprints |

Se confusão, consultar `docs/_archive/ROADMAP-v1-pre-Q-A-P-2026-05-17.md` § Sistema unificado de IDs.

---

## 11. Sprint history — Wave A→H (2026-05-17 noite → 2026-05-18)

| Wave | Janela | PRs | Destaques |
|---|---|---|---|
| **Overnight 2026-05-17** | ~22:00–04:00 BRT | #2-#16 (15 PRs) | Q/A/P pivot, specs + scaffolds todos pilares, P3 impl staged |
| **Overnight 2026-05-18 madrugada** | ~04:00–09:00 BRT | #17-#33 (17 PRs) | D41 5 decisões, kickoffs P1/P2/P4/P5/A2/A3, CI workflows, VISION v15, P1 T1-T4, P5a event bus |
| **Wave B** | ~09:00–11:00 BRT | #34-#43 (10 PRs) | P1/A2/A3/P5 impl completo (T7-T18), L4 prod wire, P2 T1-T15 |
| **Wave C** | ~11:00–12:00 BRT | #44-#48 (5 PRs) | L2+L3 impl completo, deploy guide, docs consolidation |
| **Wave D** | ~12:00–12:30 BRT | #46-#50 (5 PRs) | README final, COMPARISON.md populated, competitive positioning, QA matrix |
| **Wave E** | ~12:30–13:00 BRT | #52-#56 (5 PRs) | OpenAPI spec, CONTRIBUTING + QUICKSTART, THREAT-MODEL.md, integrations scaffold, wave-CD post-mortem |
| **Wave F** | ~13:00–16:00 BRT | #57-#64 (8 PRs) | GitHub hygiene, THREAT-MODEL v1.1 (G11-G17 novos), G4/G6/G7/G8/G10 fixes, G1+G5 critical fixes, A1.1 BR PII, MEMORY review + DOCS hub |
| **Wave G** | ~16:00–18:00 BRT | #61-#66 (6 PRs) | G11-G17 security bundle, cross-pillar tests (77 tests), demo video script, deploy validator, wave-F post-mortem |
| **Wave H** | ~18:00–20:00 BRT | #67-#69 (3 PRs) | ops runbooks (DR+BACKUP+MONITORING), Docker, pricing strategy + ROI calculator |
| **Wave I** | ~20:00+ BRT | canonical docs sync | ROADMAP + HANDOFF + DECISIONS sync (este PR) |

**Total Wave A→H:** 69 PRs merged | ~55.000 LOC | 1.100+ testes | schema v11→v22 | CI verde

---

## 12. Próxima ação concreta (referência rápida) — pós Wave H

**Decisão imediata (VPS deploy):**
Ver `docs/DEPLOY-WAVE-B.md` — 3 caminhos (A=tudo, B=seletivo, C=staging) com checklist pré-deploy.
Patches staged: A1 privacy filter, P3 temporal queries.
Implementations completos em staged-*/: A2, A3, P1, P2, P5, L2, L3, L4.

**Reviews críticos antes de deploy:**
1. PR #64 A1.1 BR PII — endereça G2 CRITICAL threat model (CPF/CNPJ exposure)
2. PR #62 G1+G5 — passphrase entropy enforce + central error sanitizer
3. PR #66 G11-G17 — 7 novos gaps de segurança fechados

**Esta semana:**
1. VPS deploy das staged patches (Path A ou B per `docs/DEPLOY-WAVE-B.md`)
2. Q1 LoCoMo full run → primeiro número padrão indústria
3. Q2 LongMemEval full run (CLI pronto: `nox-mem eval longmemeval`)
4. 18 pricing open questions em `docs/gtm/PRICING-STRATEGY.md` (C1-C5 + P1-P10)

**Quando Q4 gate abrir:**
- README final já pronto (PR #46)
- COMPARISON.md já scaffolded (PR #47)
- Assets já prontos: palette D, accent `#00C896` (PR #19)
- Demo video script pronto (PR #63)
- Pricing strategy pronta (PR #69)
- Docker image pronta (PR #68)

---

## 13. Ponteiros canônicos

| Conteúdo | Arquivo |
|---|---|
| **Estado vivo + próxima ação** | `docs/HANDOFF.md` ← começar aqui |
| **Roadmap (este)** | `docs/ROADMAP.md` |
| **Decisões + NÃO FAZEMOS** | `docs/DECISIONS.md` |
| **Regras críticas operacionais** | `CLAUDE.md` |
| **Visão estratégica longo prazo** | `docs/VISION.md` (v14) |
| **Histórico de versões (v1.0 → v3.7)** | `docs/EVOLUTION.md` |
| **Incidents (memoria-only)** | `docs/INCIDENTS.md` |
| **Paper técnico** | `paper/publication/latex/paper.pdf` (v1.1) |
| **Convenções detalhadas** | `docs/CONVENTIONS.md` |

---

*ROADMAP v3 — v2 redigido overnight 2026-05-17; v3 atualizado pós Wave H 2026-05-18 (Wave I canonical sync). Próxima review: pós VPS deploy + Q1 full run.*
