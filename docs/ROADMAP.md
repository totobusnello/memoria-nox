# nox-mem ROADMAP — Q/A/P + Lab

> **"Hybrid memory with shadow discipline — yours by design."**
>
> Single source of truth. Reorganized **2026-05-17 night** during overnight automode push.
> v1 (630 lines, cluttered with session logs) archived at `docs/_archive/ROADMAP-v1-pre-Q-A-P-2026-05-17.md`.

---

## TL;DR

3 product pillars + 1 research lab + 1 conditional GTM phase. **60% capacity on product, 40% on research.**

| Track | Why | Sprints | Status |
|---|---|---|---|
| **Q — Quality** | Numbers that lead the market | Q1-Q4 | Q1+Q2+Q3 scaffolded 2026-05-17, Q4 spec |
| **A — Autonomy** | Data yours, provider your choice, zero vendor lock-in | A1-A4 | A1 implemented (staged), A2+A3 specced, A4 scaffolded |
| **P — Product** | UX that ships | P1-P5 | P1+P2+P4+P5 specced, P3 implemented (staged) |
| **Lab — Retrieval Research** | Paper-grade improvements, 40% capacity | L1-L3 | L1 (E15) paused; L2+L3 specs done |
| **GTM Phase 2** | Viral launch | conditional | Locked behind COMPARISON.md winning; spec ready (PR #16) |

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

## 2. Estado atual (snapshot 2026-05-17 noite)

```
Sistema:        nox-mem v3.7+, schema v18, ops_audit append-only
Chunks:         69.298 (99.97% embedded, Gemini 3072d) — fts_anchor populated
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

Features CORTADAS (lições codificadas em DECISIONS.md):
 ❌ Reason boost (D38), Focus boost (D36), Reranker v1+v2 (CUT), A1/A2/G (D39)
```

---

## 3. Pillar Q — Quality (números que lideram)

Objetivo: provar nox-mem #1 (ou identificar gap exato) com benchmarks padrão indústria.

### Sprints

| Sprint | DoD | Status | Spec/PR |
|---|---|---|---|
| **Q1** LoCoMo R@5 publicado | R@5, R@1, MRR, nDCG@10 + Wilson CI, full run reproducible | **Scaffolded** 2026-05-17 | PR #6 (eval/locomo/) |
| **Q2** LongMemEval task accuracy | Accuracy % + per-category, LLM-as-judge GPT-4o + Gemini 2.5-pro | **Scaffolded** 2026-05-17 | PR #12 (eval/longmemeval/) |
| **Q3** Latency p50/p95/p99 | Cold + warm, 6 workloads, sub-ms accuracy | **Scaffolded** 2026-05-17 | PR #11 (eval/latency/) |
| **Q4** Public COMPARISON.md | nox-mem vs agentmemory + memanto + mem0 + Letta + Zep, todos rodados localmente | **Spec scaffolded** 2026-05-17 (gated by Q1+Q2+Q3 winning) | Q4 harness PR pendente |

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
| **A2** Schema export/import portable | tar.gz archive, encryption optional, round-trip preserves nDCG@10 ±0.001 | **Specced** 2026-05-17 (3,403 words) | PR #9 |
| **A3** Provider abstraction layer | EmbeddingProvider + LLMProvider interfaces, env-driven selection, health check + fallback | **Specced** 2026-05-17 (4,171 words) | PR #8 |
| **A4** Zero-vendor validation suite | automated test prova nenhum third-party runtime dep crítico, 8 checks, CI-runnable | **Scaffolded** 2026-05-17 (10 files, 4 checks runnable, 4 need VPS) | PR #14 |

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
| **P1** `answer` primitive | CLI + API + MCP `nox_mem_answer`, citação por chunk_id, anti-hallucination guard | **Specced** 2026-05-17 (5,307 words) | PR #3 |
| **P2** Auto-capture via Claude Code hooks | 5 hooks (SessionStart/UserPromptSubmit/PostToolUse/Stop/PreCompact), zero manual ingest, 5 layers privacy defense | **Specced** 2026-05-17 (3,968 words) | PR #4 |
| **P3** Temporal queries `--as-of` `--changed-since` | CLI + API + MCP, hard pre-filter (não boost), 23 tests | **Implemented** 2026-05-17 (staged) | PR #2 |
| **P4** `nox-mem connect <ide>` | Tier A (Claude Code + Cursor + Codex deep) + Tier B (10 IDEs MCP-passive) | **Specced** 2026-05-17 (2,904 words, 13 IDEs) | PR #7 |
| **P5** Real-time viewer upgrade | SSE + 4 panels (live feed/counters/charts/heatmap), <500ms ingest→event | **Specced** 2026-05-17 (2,958 words) | PR #10 |

### Marketing message
> "Memória deep pro stack que você usa de verdade, não memória pra qualquer IDE."

---

## 6. Lab — Retrieval Research (40% capacity)

| Sprint | Foco | Status |
|---|---|---|
| **L1** E15 CodeGraph-inspired improvements (A+B+C, 4-7h) | Spec gravado pré-Q/A/P pivot | **Pausado** 2026-05-17, retoma pós-Q1 |
| **L2** Conflict/contradiction detection sobre KG (memanto-inspired) | Detectar relations opostas no mesmo sujeito | **Specced** 2026-05-17 (3,067 words) — PR #13 |
| **L3** Confidence + provenance field schema v19 (memanto-inspired) | Só se eval mostrar lift (gated) | **Specced** 2026-05-17 (3,526 words) — PR #15 |

---

## 7. GTM Phase 2 — Viral launch (CONDITIONAL)

**Locked behind:** Q4 publica COMPARISON.md com nox-mem em cima ou empatando topo.

**Spec ready:** PR #16 (`specs/2026-05-17-GTM-readme-hero-upgrade.md`, ~3,850 words). Includes asset list (20 files: banner + 6 stat SVGs dark/light + arch PNG + demo GIF + logo), copy templates, marketing channels, A/B testing methodology.

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

## 11. Próxima ação concreta (referência rápida)

**Manhã 2026-05-18:**
1. Review 15+ PRs overnight (#2 P3 / #3 P1 / #4 P2 / #5 A1 / #6 Q1 / #7 P4 / #8 A3 / #9 A2 / #10 P5 / #11 Q3 / #12 Q2 / #13 L2 / #14 A4 / #15 L3 / #16 GTM)
2. Decidir cada: merge, request-changes, or close
3. Atualizar `docs/HANDOFF.md` com estado pós-merge
4. Q1+Q2+Q3 full run scheduling (VPS)
5. Identificar primeiro pilar implementation sprint (provavelmente P1 answer primitive — spec mais maduro, deps light)

**Esta semana:**
- Q1 LoCoMo full run → primeiro número padrão indústria
- A2+A3 implementation kickoff
- P1 implementation kickoff (specced, dependência A1 ready)

---

## 12. Ponteiros canônicos

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

*ROADMAP v2 redigido durante overnight automode push 2026-05-17. Próxima review: 2026-05-18 morning.*
