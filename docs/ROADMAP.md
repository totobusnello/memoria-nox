# nox-mem ROADMAP — Q/A/P + Lab

> **"Pain-weighted hybrid memory with shadow discipline — yours by design."**
>
> Single source of truth. Reorganized **2026-05-17 night** durante overnight automode push.
> v1 (630 lines, cluttered com session logs) arquivado em `docs/_archive/ROADMAP-v1-pre-Q-A-P-2026-05-17.md`.
> **Atualizado 2026-05-24 EOD** — **20+ PRs merged Sat** (#265-#287). **Q4 LIVE validation:** nDCG@10 **0.6380** (prod instance, LoCoMo n=100) **+83.0% vs G3**, exceeds D43 gate (+18.8%). **4 deployments Sat:** F10 Phase C Phase 2 (#283 answer API telemetry hook), A2 Tier 3 P0+P1+P2 merged (SQLCipher GO + db.ts key-open + migration script), CI persist-credentials fix (#284), mem0 corpus_loader canonical (#285). Boost stack canonical = section_boost + source_type_boost + **Hard Mutex conditional t=2** + salience v2 + temporal v2. **Q4 harness:** nox_mem 13/20 gold (p50 12ms), mem0 gold_hits unlocked, agentmemory REST adapter validated (iii-engine v0.9.21 OSS), zep/letta baseline OK, evermind repo 404 skipped. **D43 gate VERIFIED** (COMPARISON.md credible). **A2 Tier 3:** P0+P1+P2 merged, P3 in-flight. **F10 Phase C:** telemetry LIVE prod (5/5 smoke PASS), Phase D queued. **Worktree defense:** 7 leaks Sat, all recovered via layer 2 hook; hardening queued Sun. D49 phase 2 baseline rolling (~7d shadow window, D50 decision ~2026-05-27).

---

## TL;DR

3 product pillars + 1 research lab + 1 conditional GTM phase. **60% capacity on product, 40% on research.**

| Track | Why | Sprints | Status |
|---|---|---|---|
| **Q — Quality** | Numbers que lideram o mercado | Q1-Q4 | **Q1+Q2 full runs ✅ DONE** (G5 V3 0.6237 nDCG@10); **Q3 latency ✅ DONE** (p50 12ms / p95 43ms local); **Q4 LIVE validation ✅ DONE** (0.6380 nDCG@10 prod, +83% vs baseline, D43 gate verified) |
| **A — Autonomy** | Data sua, provider sua escolha, zero vendor lock-in | A1-A4+A1.1 | A1 impl staged; **A1.1 BR PII shipped**; A2+A3 impl completo (T1-T18); **A4 100% runnable em CI**; **A2 Tier 3 P0+P1+P2 merged** |
| **P — Product** | UX que ganha | P1-P10 | P1 LIVE em prod (answer API); P2 impl completo; P3 staged; P4 spec; **P5 impl completo** + P5a event bus; **F10 Phase C Phase 1+2 LIVE prod** |
| **Lab — Retrieval Research** | Paper-grade improvements, 40% capacity | L1-L4 + G-series | L1 paused; **L2+L3+L4 impl completo**; G-series ablation ativa (G7 cravado, G8 pendente); **D49 phase 2 rolling** (~7d shadow, D50 ETA 2026-05-27) |
| **GTM Phase 2** | Viral launch | conditional | **Gate D43 VERIFIED** (nDCG@10 0.6380 exceeds +15% threshold); assets + pricing + Docker prontos; COMPARISON.md credible; **desbloqueada condicionalmente** |

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
- Pain-weighted salience (`recency × pain × importance`) — único — **formula v2 aditiva validated G7**
- Shadow discipline (arquitetural ≥7d antes de ativar) — único
- KG edge typing (relation_reason enum) — único
- Compiled/timeline/frontmatter sections com section_boost — único

---

## 2. Estado atual (snapshot 2026-05-20 pós Wave A deployed)

```
Sistema:        nox-mem v3.7+, schema v22 (v11/v19/v20/v21/v22 migrados), ops_audit append-only
Chunks:         ~68.995 (99.97% embedded, Gemini 3072d) — fts_anchor populated
DB size:        ~1.24 GB
KG:             15.646 entities / 21.533 relations
Agentes:        7 (1 main Maestro + 6 personas: nox/atlas/boris/cipher/forge/lex)
OpenClaw:       v2026.4.29
Eval nDCG@10:   0.6237 (G5 V3, n=prod-flavored 68k g5.db, A8 full stack — CANONICAL)
                Δ vs G3 baseline (0.3487): +78.8% relativo — headline número
                Δ vs paper baseline (0.5831): +6.9pp — paper §5 cravado
Eval secondary: 0.5845 (entity-eval.db 500 chunks — válido só comparando consigo mesmo)

Features ranking ATIVAS em prod (Wave A deployed 2026-05-19):
 ✅ Salience formula v2 aditiva (recency × pain × importance, weights 0.55/0.15/0.10/0.20) — G01+G7
 ✅ Section boost (compiled +100%, frontmatter +49%) — G02 2026-05-01
 ✅ SOURCE_TYPE_BOOST map — PR #154 (backfill keys unlocked)
 ✅ Tier boost — OFF by default (D50 pendente, confirma com G8)
 ✅ Edge typing (relation_reason enum 7) — E05 Phase 1 2026-05-02
 ✅ Temporal boost (E13) — 2026-05-06
 ✅ SPO Injection (E03b, integrated em CLI) — 2026-05-17
 ✅ E-lite-2 (fts_anchor bilingual) — 2026-05-17 (Wave 1 E14)
 ✅ D (language-aware RRF weights) — 2026-05-17 (Wave 1 E14)
 ✅ L4 regex-first KG extraction (Gemini fallback) — 2026-05-18 (Wave B, OPEX -80%)
 ✅ L2 conflict detection (KG) — 2026-05-18 (Wave C)
 ✅ L3 confidence + provenance — 2026-05-18 (Wave C, ranking gated por eval)
 ✅ Temporal path shadow D49 phase 1 — PR #167 (NOX_TEMPORAL_PATH=shadow opt-in)

Features CORTADAS (lições em DECISIONS.md):
 ❌ Reason boost (D38), Focus boost (D36), Reranker v1+v2 (CUT), A1/A2/G (D39)
 ❌ Tier boost isolated (-21% G5 V3) — confirmado inerte, OFF prod (PR #150)

Wave A→H entregues (2026-05-17 noite → 2026-05-18):
 69 PRs merged | ~55.000 LOC | 1.100+ testes | 5 schema migrations (v11/v19/v20/v21/v22)
 CI verde (eval harnesses + privacy filter + zero-vendor + typecheck + cross-pillar)
 Docker: Dockerfile + docker-compose + CI build image
 Ops: DR + BACKUP + MONITORING runbooks
 Security: THREAT-MODEL.md v1.1, G1-G17 todos endereçados
 GTM: pricing strategy + ROI calculator + demo video script + README final

Wave A 2026-05-19→20 deployed (17 PRs em 2026-05-20):
 Boost stack wiring real (PR #148) | salience formula v2 (PR #150) | source_type backfill (PR #151)
 G5 ablation matrix + V3 cravado (PR #152) | Wave A deploy prep (PR #153) | SOURCE_TYPE_BOOST (PR #154)
 Visual identity +78.8% (PR #155) | Paper §5 reframe (PR #156) | Temporal Q1 spike (PR #157)
 api-server docs patch (PR #158) | Gold Q87+Q88 cure (PR #159) | CI eval-harnesses fix (PR #160)
 Temporal smoke test (PR #161) | INCIDENTS+DECISIONS+D49 (PR #162) | Paper .docx (PR #163)
 VPS healthcheck (PR #164) | G6 investigation (PR #165) | Competitive analysis (PR #166)
 D49 phase 1 deploy (PR #167) | Temporal queries Q105-Q110 (PR #168) | Formula v2 grid search design (PR #169)
```

---

## 3. Pillar Q — Quality (números que lideram)

Objetivo: provar nox-mem #1 (ou identificar gap exato) com benchmarks padrão indústria.

### Sprints

| Sprint | DoD | Status | Spec/PR |
|---|---|---|---|
| **Q1** LoCoMo R@5 publicado | R@5, R@1, MRR, nDCG@10 + Wilson CI, full run reproducible | **✅ DONE** — G5 V3 0.6237 nDCG@10 (+78.8% vs G3 baseline) | PR #6 + G5 V3 2026-05-19 |
| **Q2** LongMemEval task accuracy | Accuracy % + per-category, LLM-as-judge GPT-4o + Gemini 2.5-pro | **✅ DONE** — n=100 full run: nDCG@10=0.9126, MRR=0.9162, R@10=0.9558 (2026-05-19) | PR #12 + #29 |
| **Q3** Latency p50/p95/p99 | Cold + warm, 6 workloads, sub-ms accuracy | **⚠️ Medido mas pendente formalização** — p50=940ms, p95=2342ms (VPS 2026-05-18); Gemini embed domina (~800ms) | PR #11 |
| **Q4** Public COMPARISON.md | nox-mem vs agentmemory + memanto + mem0 + Letta + Zep, todos rodados localmente | **⚠️ Harness scaffolded + COMPARISON.md populated** — gate D43 aberto, execução de comparison final pendente | PR #23 + #47 |

### Números canônicos (G5 V3, 2026-05-19)
- **nDCG@10 = 0.6237** (A8 full stack, g5.db 68k prod-flavored) — headline paper + visual identity
- Δ vs G3 baseline 0.3487: **+78.8%** — headline marketing
- G7 check (entity-eval.db): formula v2 NEUTRA (+0.5% ruído) — D48 success, wiring real confirmed

### Próximas métricas alvo
- Q3 formalizar: reduzir p95 Gemini embed → target sub-500ms (cache ou batching)
- Q4 comparison rodar: alvo LoCoMo R@5 ≥ 90%, LongMemEval ≥ 85%

### Gate D43 (aberto 2026-05-18)
+18.8% nDCG@10 atende threshold ≥+15%. GTM Phase 2 desbloqueada condicionalmente em Q4 comparison wins.

---

## 4. Pillar A — Autonomy (data é sua, provider sua escolha)

Objetivo: tornar o moat "sem vendor lock-in" tangível e auditável.

### Sprints

| Sprint | DoD | Status | Spec/PR |
|---|---|---|---|
| **A1** Privacy filter pre-storage | 13+ patterns, `<private>` tag, 30+ tests, integrated in ingest-router | **✅ Implemented** (staged, 68 tests passing, FP 1.7%) | PR #5 |
| **A1.1** BR PII patterns | CPF/CNPJ/pix/CEP/RG — endereça G2 CRITICAL do threat model | **✅ Shipped** 2026-05-18 (Wave F) | PR #64 |
| **A2** Schema export/import portable | tar.gz archive, AES-256-GCM encrypt-by-default, round-trip preserves nDCG@10 ±0.001 | **✅ Implementação completa** T1-T18 (Wave overnight+B) — staged | PR #37 + #41 |
| **A3** Provider abstraction layer | EmbeddingProvider + LLMProvider interfaces, env-driven selection, fallback + cost cap | **✅ Implementação completa** T1-T16 (Wave overnight+B) — staged | PR #36 + #39 |
| **A4** Zero-vendor validation suite | 8 checks, todos CI-runnable, <1s runtime | **✅ 100% completo** 2026-05-18 | PR #14 + #20 |

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
| **P1** `answer` primitive | CLI + API + MCP `nox_mem_answer`, citação por chunk_id, anti-hallucination guard | **✅ LIVE em prod** — first answer real 2026-05-18 19:48 BRT (~1.6s, gemini-2.5-flash-lite, 8 retrieved + cited) | PR #31 + #34 + #40 + #114 |
| **P2** Auto-capture via Claude Code hooks | 5 hooks (SessionStart/UserPromptSubmit/PostToolUse/Stop/PreCompact), zero manual ingest, 5 layers privacy defense | **✅ Implementação completa** T1-T15 (Wave B) — staged | PR #43 |
| **P3** Temporal queries `--as-of` `--changed-since` | CLI + API + MCP, hard pre-filter (não boost), 23 tests | **✅ Implemented** (staged; D49 phase 1 shadow em prod) | PR #2 + #167 |
| **P4** `nox-mem connect <ide>` | Tier A (Claude Code + Cursor + Codex deep) + Tier B (10 IDEs MCP-passive) | **⏳ Spec + kickoff** — 13 IDEs cobertos | PR #7 + #21 |
| **P5** Real-time viewer upgrade | SSE + 4 panels (live feed/counters/charts/heatmap), <500ms ingest→event | **✅ Implementação completa** T1-T15 (Wave B) — 11.7KB bundle vanilla JS | PR #10 + #33 + #42 |
| **P5a** Event bus refactor | P5 prerequisite, isolates SSE from ingest path | **✅ Shipped** 2026-05-18 (Wave overnight) | PR #33 |

### Marketing message
> "Memória deep pro stack que você usa de verdade, não memória pra qualquer IDE."

---

## 6. Lab — Retrieval Research (40% capacity)

### Sprints de feature

| Sprint | Foco | Status |
|---|---|---|
| **L1** E15 CodeGraph-inspired improvements (A+B+C, 4-7h) | Spec gravado pré-Q/A/P pivot | **⏸️ Pausado** 2026-05-17, retoma pós-Q1 |
| **L2** Conflict/contradiction detection sobre KG (memanto-inspired) | Detectar relations opostas no mesmo sujeito | **✅ Implementação completa** T1-T12 (Wave C) | PR #13 + #51 |
| **L3** Confidence + provenance field schema v19 (memanto-inspired) | Só se eval mostrar lift (gated) — ranking integration aguarda gate ≥1.0pp | **✅ Implementação completa** T1-T13 (Wave C) — schema shipped, ranking gated | PR #15 + #48 |
| **L4** Regex-first KG extraction com Gemini fallback (gbrain-inspired) | OPEX -80% eliminando Gemini calls em links explícitos | **✅ Implementação completa** T1-T9 (Wave overnight+B) — 95.8% precision, 80% Gemini savings | PR #27 + #35 + #38 |

### G-series ablation (D48 saga CLOSED 2026-05-20 EOD)

| Run | DB | Config | nDCG@10 | Status |
|---|---|---|---|---|
| **G3** | entity-eval.db | baseline pre-Wave A | 0.3487 | ✅ Reference |
| **G4** | g4.db | pré-salience | ~0.57x | ✅ Cravado |
| **G5 V3** | g5.db (68k prod) | A8 full stack | **0.6237** | ✅ CANONICAL |
| **G6** | entity-eval.db | A8 full stack | 0.5845 | ✅ Resolved (DB swap, não regression) |
| **G7** | entity-eval.db | A8 ACTIVE vs OFF | 0.5845 vs 0.5872 | ✅ Formula v2 NEUTRA (+0.5% ruído) |
| **G8** | entity-eval-v2.db | source_type prod-consistent | A5 +2.66% / A8 < A10 -0.81% | ✅ SOURCE_TYPE_BOOST live + redundância flagged |
| **G9** | g5.db (68k prod) | A5 isolated vs A8 vs A10 | A5 +14.2%, A10 > A8 +2.6% | ✅ Redundância CONFIRMED em prod |
| **G10** | g9.db (69495 chunks) | A8' mutex vs A8 nomutex | 0.5478 vs 0.5435 | ✅ Hard Mutex VALIDATED (+0.79% nDCG / +2.65% MRR) |
| **G11** | g9.db (69495 chunks) | trim entity 2.0→1.3 vs canonical | 0.5337 vs 0.5376 | ❌ REJECT (-0.73% nDCG / -1.58% MRR) — single-hop -4.62% |
| **G10b** | g9.db (n=100, 20/cat) | mutex per-category breakdown | varies por cat | ✅ KEEP DEPLOYED (single-hop +8.22%, multi-hop -3.95%) |
| **G10c** | g9.db (n=100, 50/style) | mutex per-style breakdown | NL +1.56% / KW -0.72% | ✅ KEEP DEPLOYED (style-conditional behavior cravado) |
| **G10d** | g9.db (n=100, 4 configs) | conditional mutex thresh=1/2/off | A8d-2 +1.35% / +1.37% MRR | ✅ **ACTIVE-T2 DEPLOYED** (D51, multi-hop +1.58% / adversarial +3.04% recovered) |
| **G11** | g9.db (69495 chunks) | trim entity 2.0→1.3 vs canonical | 0.5337 vs 0.5376 | ❌ REJECT (-0.73% nDCG) |

**Boost stack final canonical** (G10d ACTIVE-T2 deployed 2026-05-21):
- `section_boost` (compiled=2.0, frontmatter=1.5, timeline=0.8)
- `source_type_boost` (entity=2.0, lesson=1.8, ... canonical)
- `Hard Mutex` section ↔ source_type **conditional `query_entities ≤ 2`** (PR #182 + #198, deployed 2026-05-21)
- `salience v2` additive (W_IMPORTANCE=0.55 + W_RECENCY=0.15 + W_PAIN=0.10 + W_ACCESS=0.20)

### Lab — próximos itens (ordem de prioridade)

| Item | DoD | Status | Blocker |
|---|---|---|---|
| **D49 phase 2 shadow 7d baseline** | Cron scrape coletando journalctl temporal_path JSONL daily → D50 decision | **⏳ Rolling** (cron ativo, ETA D50 ~2026-05-27) | Aguarda 7d telemetria |
| **D50 decision temporal active/off** | Baseline 7d shadow phase 2 concluída → decide ativar NOX_TEMPORAL_PATH=active | **⏳ Aguarda phase 2 baseline** | D49 phase 2 shadow 7d |
| **Paper §5.5 G10d update** | Quarto triangulation point com G10d deploy numbers | **✅ DONE** PR #208 (2026-05-21 agent worktree) | — |
| **L4 watchpoint 2026-05-24** | Query `extraction_method` distribution pós Sunday cron — primeira janela L4 fire em prod | **⏳ Aguarda Sunday cron 2026-05-24 23h UTC** | KG-build cron schedule |
| **L4 spec §4 amendment** | Doc PR atualiza spec pra refletir plural normalisation (D52 implementation) | **⏳ Pendente** | — |
| **F10 Phase C (Telemetry+Shadow tracker)** | Per-query latency drilldown + D49 shadow visualization | **⏳ Queued ~8h** | D49 phase 2 baseline ≥7d collected |
| **F10 Phase D (Ops timeline + KG stats)** | ops_audit visualization 7d + KG growth charts | **⏳ Queued ~6h** | Phase C land + kg_snapshots table |
| **Re-smoke Q105-Q110** | Pós shadow ter dados reais → confirma spike v2 em prod | **⏳ Aguarda shadow telemetry** | — |
| **Formula v2 weights grid search** | Grid search 0.4-0.7/0.1-0.2/0.05-0.15/0.15-0.25 range; I1 env vars pra tunability | **⏳ Design done** (PR #169) — impl pendente I1 env vars | PR #55 (I1 env vars) merged pré-req |
| **Neural reranker** | cross-encoder rerank após RRF; +3-8% nDCG literatura | **🅿️ Parking lot Q1/Q2** | bge/cohere/deepinfra; obrigatório ablation real + shadow |

---

## 7. GTM Phase 2 — Viral launch (CONDITIONAL)

**Gate D43:** aberto 2026-05-18. Threshold ≥+15% nDCG@10 atendido (+18.8%). Execution gated em Q4 COMPARISON.md com nox-mem em cima ou empatando topo.

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

**Assets sincronizados com G5 V3 (2026-05-20):**
- PR #155: Visual identity atualizada com +78.8% headline
- PR #156: Paper §5 reframe com Wave A numbers + 4-claim sub-evidence

Quando o gate abrir (Q4 comparison wins):
- Hero visual upgrade README (logo SVG + 6 stat SVGs custom + demo GIF + arch PNG + TOC bar)
- Trendshift badge + Star History chart
- Viral GitHub gist com design doc
- Product Hunt launch
- Twitter/HN thread coordenado
- Nox-Supermem landing page (Stripe-first, USD default — D44)
- Paper distribution (drafts já em paper/publication/distribution/)

**Targets pós-launch:**
- 1k stars em 30 dias
- Top 10 trending TS/AI em GitHub
- Inclusão em listas de "agent memory tools" curadas

---

## 8. Calendário (updated 2026-05-24 pós Q4 LIVE validation)

```
FEITO (2026-05-17 → 2026-05-24):
 ✅ Q1+Q2 full runs — G5 V3 0.6237 canonical
 ✅ Wave A boost stack wiring deployed em prod
 ✅ Salience formula v2 aditiva validated (G7 neutra)
 ✅ D49 phase 1 shadow telemetry ativa
 ✅ Temporal queries Q105-Q110 curadas (6 novas, gold rank 5-13)
 ✅ Visual identity + paper §5 synced com G5 V3
 ✅ VPS healthcheck script + cron
 ✅ Q3 latency measured (p50 12ms / p95 43ms, sub-target)
 ✅ Q4 LIVE validation complete — nDCG@10 0.6380, D43 gate verified
 ✅ A2 Tier 3 P0+P1+P2 merged (SQLCipher GO, db.ts key-open, migration script)
 ✅ F10 Phase C Phase 1+2 LIVE prod (telemetry + answer API hook)
 ✅ Q4 adapters validated (nox_mem 13/20, mem0 gold unlock, agentmemory REST, zep baseline)

PRÓXIMAS 3-5 DIAS (Sat evening → Sun → Mon):
 ⏳ Sun 06h — Worktree spawn audit + hardening (7 leaks recovery pattern)
 ⏳ Sun 10h — F10 Phase D dispatch (ops audit viz + KG growth charts)
 ⏳ Sun 14h — agentmemory P3 full ingest ETL (~52min)
 ⏳ Mon 09h — A2 Tier 3 P3 merge (per-user key derivation + Tier 2)
 ⏳ Mon 14h — Pre-launch final checklist (CI + opsAudit + readiness)

PRÓXIMA SEMANA (Tue-Wed):
 ⏳ Tue 2026-06-02 09h — arXiv submit (paper v1.0 final)
 ⏳ Wed 2026-06-03 10h — Launch (GitHub + HN + PH + social + demo)
 ⏳ Post-launch — Demo GIF generation, blog post publication, outreach

PARALELAMENTE:
 ⏳ D49 phase 2 shadow 7d baseline rolling (ETA D50 decision ~2026-05-27)
 ⏳ D50 decision — activate NOX_TEMPORAL_PATH=active or keep shadow?
 ⏳ G8 entity-eval-v2 ablation (optional post-launch; current state canonical)
 ⏳ I1 env vars tunability (post-launch Lab Q1)
 ⏳ Formula v2 weights grid search (post-launch Lab Q1; current weights canonical)

POST-LAUNCH (Lab Q1/Q2):
 ⏳ Neural reranker ablation (bge/cohere/deepinfra + shadow 7d)
 ⏳ EverMemBench honest comparison (iii-engine baseline + nox-mem validation)
 ⏳ Scale test 250k chunks (infrastructure + perf validation)
 ⏳ Multilingual support (CJK embeddings + FTS5 language routing)

NOTES:
 • D43 gate VERIFIED (no additional comparison runs required)
 • COMPARISON.md credible (nox_mem 0.6380 live, adapters validated)
 • GTM Phase 2 desbloqueada (go/no-go decision is launch timing, not technical gate)
 • Pricing strategy Stripe-first (D44 + PR #69 already merged)
 • Paper v1.0 publication-ready (§6 skeleton filled Sat evening)
```

---

## 9. Convenções

- **Specs canônicos:** `specs/YYYY-MM-DD-{pilar}{N}-{slug}.md` (ex: `specs/2026-05-17-P1-answer-primitive.md`)
- **Branches overnight:** `overnight/YYYY-MM-DD/{pilar}{N}-{slug}`
- **PR title pattern:** `[overnight] {pilar}{N} — {one-line}` (não-overnight: `{prefix}({scope}): summary`)
- **Métricas em PR:** sempre incluir DoD checklist + acceptance criteria
- **Shadow discipline:** features de ranking/scoring exigem ≥7d shadow-mode antes de ativar (regra crítica #5 CLAUDE.md)
- **Eval isolation:** NOX_DB_PATH obrigatório + `_check_eval_isolation()` pré-req; large-DB guard requer NOX_ALLOW_PROD_INGEST=1
- **Ablation protocol:** sempre especificar DB + harness; comparar só dentro do mesmo universo (G6 lesson)

---

## 10. Decoder de namespaces

| Namespace | Significado |
|---|---|
| F (Foundation), R (Research), D (Decision) | Cross-ref histórico — mantidos |
| G-series (G1-G8+) | Ablation eval runs (G-series Lab) |
| E13 Temporal boost ativo | Re-tagueado como **L0** (lab done) |
| E14 Wave 1 (E-lite-2, D) ativo | Re-tagueado como **L0** (lab done) |
| E15 CodeGraph | **L1** (paused) |
| A1/A2/A3 ingest-router pré-pivot | Mantidos; novo A1/A2/A3 são autonomy pillar sprints |
| I1 | Env vars tunability sprint |
| D49 | Temporal retrieval path decision (DECISIONS.md) |
| D50 | Temporal active/off decision (pendente phase 2 baseline) |

Se confusão, consultar `docs/_archive/ROADMAP-v1-pre-Q-A-P-2026-05-17.md` § Sistema unificado de IDs.

---

## 11. Sprint history

### Wave A→H (2026-05-17 noite → 2026-05-18)

| Wave | Janela | PRs | Destaques |
|---|---|---|---|
| **Overnight 2026-05-17** | ~22:00–04:00 BRT | #2-#16 (15 PRs) | Q/A/P pivot, specs + scaffolds todos pilares, P3 impl staged |
| **Overnight 2026-05-18 madrugada** | ~04:00–09:00 BRT | #17-#33 (17 PRs) | D41 5 decisões, kickoffs P1/P2/P4/P5/A2/A3, CI workflows, VISION v15, P1 T1-T4, P5a event bus |
| **Wave B** | ~09:00–11:00 BRT | #34-#43 (10 PRs) | P1/A2/A3/P5 impl completo (T7-T18), L4 prod wire, P2 T1-T15 |
| **Wave C** | ~11:00–12:00 BRT | #44-#48 (5 PRs) | L2+L3 impl completo, deploy guide, docs consolidation |
| **Wave D** | ~12:00–12:30 BRT | #46-#50 (5 PRs) | README final, COMPARISON.md populated, competitive positioning, QA matrix |
| **Wave E** | ~12:30–13:00 BRT | #52-#56 (5 PRs) | OpenAPI spec, CONTRIBUTING + QUICKSTART, THREAT-MODEL.md, integrations scaffold |
| **Wave F** | ~13:00–16:00 BRT | #57-#64 (8 PRs) | GitHub hygiene, THREAT-MODEL v1.1 (G11-G17), G1+G5 critical fixes, A1.1 BR PII |
| **Wave G** | ~16:00–18:00 BRT | #61-#66 (6 PRs) | G11-G17 security bundle, cross-pillar tests (77 tests), demo video script |
| **Wave H** | ~18:00–20:00 BRT | #67-#69 (3 PRs) | ops runbooks (DR+BACKUP+MONITORING), Docker, pricing strategy + ROI calculator |

**Total Wave A→H:** 69 PRs merged | ~55.000 LOC | 1.100+ testes | schema v11→v22 | CI verde

### Wave A 2026-05-19→20 (boost stack deployed)

| Janela | PRs | Destaques |
|---|---|---|
| **2026-05-19 noite** | #148-#153 | Boost stack wiring (PR #148), salience formula v2 aditiva (PR #150), source_type backfill (PR #151), G5 ablation + V3 cravado (PR #152), Wave A deploy prep (PR #153) |
| **2026-05-20 morning** | #154-#159 | SOURCE_TYPE_BOOST map (PR #154), visual identity +78.8% (PR #155), paper §5 (PR #156), temporal Q1 spike (PR #157), api-server docs patch (PR #158), gold Q87+Q88 (PR #159) |
| **2026-05-20 midday** | #160-#162 | CI eval-harnesses fix (PR #160), temporal smoke test (PR #161), INCIDENTS+DECISIONS+D49 (PR #162) |
| **2026-05-20 afternoon** | #163-#166 | Paper .docx (PR #163), VPS healthcheck (PR #164), G6 investigation (PR #165), competitive analysis (PR #166) |
| **2026-05-20 early evening** | #167-#169 | D49 phase 1 shadow (PR #167), temporal Q105-Q110 (PR #168), formula v2 grid search design (PR #169) |

**Total Wave A 2026-05-19→20:** ~20 PRs | boost stack live em prod | G5 V3 0.6237 canonical

### Sprint 2026-05-21 (G10d deploy + F10 observability dashboard + L4 plural)

| Janela | PRs | Destaques |
|---|---|---|
| **2026-05-21 morning** | #188-#205 (~17) | G10d spec + D51 template (#192), opsAudit hygiene Issues #1+#3 deployed (#193), G10b/c audits closed no-merge (#188+#189), GTM README hero merged (#190), per-method benchmark spec (#191), vec0 fix deployed (#194), opsaudit-3b db_source enforce (#204), G10d ablation eval execution (#203), G12 frontmatter audit (#205) |
| **2026-05-21 afternoon** | (G10d deploy + spec follow-ups) | G10d ACTIVE-T2 deployed em prod (systemd drop-in `NOX_MUTEX_QUERY_ENTITY_THRESHOLD=2`); smoke 3/3 PASS |
| **2026-05-21 evening** | #206-#211 (6) | G12 R3 dedup carve-out (#206), F10 Phase A endpoints + UI (#207) + DEPLOYED PROD, paper §5.5 G10d addendum agent (#208), L4 foundation T0-T3 (#209) → cleanup (#210), L4 extraction_method NULL audit + watchpoint 2026-05-24 (#211) |
| **2026-05-21 late evening** | #212-#214 (3) | HANDOFF evening refresh (#213), F10 Phase B eval dashboard agent worktree (#212) + DEPLOYED PROD, L4 DIR_PATTERN plural normalisation + `system` 17th canonical (#214) |

**Total 2026-05-21:** **24 PRs merged** | **4 production deploys** (G10d ACTIVE-T2, opsAudit hygiene, F10 A+B, G12 R3) | D51+D52+D53 decisions cravados | D48 saga FINAL CLOSED | G12 audit FINAL status (R3 deployed, R1+R2 closed eval-only PR #216, R4 deferred)

---

## 12. Próxima ação concreta — Sun 2026-05-25 morning prep + Wave 16 in-flight (atualizado Sat 2026-05-24 EOD)

> **Nota:** Q4 LIVE validation complete Sat 2026-05-24 evening — nDCG@10 **0.6380** (prod instance LoCoMo n=100) exceeds D43 gate (+83.0%). Wave 1-16 merged/in-flight (20+ PRs Sat + 4 deploys). **Sun morning:** validate Wave 16 landing, run hybrid@500 verdict (P2 priority), finalize launch comm. **No blockers for Wed 2026-06-03 launch.** D49 phase 2 baseline rolling (ETA D50 ~2026-05-27); L4 watchpoint Monday post-cron.

### Sun 2026-05-25 (morning prep + Wave 16 handoff)

| Janela | Ação | Blocker |
|---|---|---|
| **06h–08h — Wave 16 PR validation** | Merge PRs #310-#316 (in-flight from Sat); smoke test Q4 harness local; verify COMPARISON.md structure (GATE_VERIFIED flag ready) | None — PRs awaiting notification |
| **09h–10h — Gemini hybrid@500 execute** | Rodar `python eval/q4-comparison/runner.py --systems all --datasets locomo,longmemeval --limit 500`; capture per-system breakdown (nox_mem vs mem0/zep/letta/agentmemory); update Lab Q1 priorities se regresso ≥1pp detectado | Wave 16 merge + evaluation harness |
| **10h–11h — Review Q4 results + update COMPARISON.md** | Confirmar gate D43 (threshold ≥+15% atendido); populate COMPARISON.md cells com números Sat eve (0.6380) + hybrid@500 results; flag `GATE_VERIFIED=1` | Hybrid@500 execution |
| **11h–12h — Paper §6 final + methodology** | Seção §6 paper: como rodou Q4, isolation protocol, harness overview — escrito com nDCG@10 0.6380 + per-system results em mão | COMPARISON.md populated |
| **14h–15h — Launch comm approval** | Se hybrid@500 WINS (nox_mem ≥ topo): aprove blog final (#221), social copy (#224), paper §6 (#226) + merge; se REGRESS: reframe narrativa LoCoMo leadership + confidence intervals | Hybrid verdict + paper review |
| **14h–16h — F10 Phase D dispatch (optional)** | Se Phase C baseline ≥7h rolling: dispatch agent pra Phase D ops timeline viz + KG growth charts; else defer Mon | Phase C telemetry sufficiency |
| **23h UTC — Observe cron** | Log L4 + KG build completion; note any anomalies (expected: kg_relations rows gain extraction_method post-cron) | Automatic (no action needed) |

### Mon 2026-05-27 (pre-launch checkpoint)

| Ação | Detalhe | Owner |
|---|---|---|
| **09h — L4 watchpoint query** | `SELECT extraction_method, COUNT(*) FROM kg_relations WHERE created_at >= DATE('2026-05-24') GROUP BY extraction_method` post-cron. Esperado: nonzero extraction_method distribution. If all NULL → escalate PR #195 wire-up | Executor |
| **10h — D49 phase 2 → D50 prep** | Phase 2 baseline rolling (cron telemetry 7d); ETA D50 decision window 2026-05-27. Decide: ativar `NOX_TEMPORAL_PATH=active` ou keep shadow? | Toto |
| **14h EOD — Pre-launch final checklist** | CI workflows green (8/8 expected), opsAudit clean (1 real row expected), readiness dashboard 100% | Toto + Executor |

### Tue 2026-06-02 (hard deadline — per D27 sequencing)

| Item | Ação | Blocker |
|---|---|---|
| **arXiv submit window** | Paper v1.0 submission (Tue 09h → Wed live, coordenar com launch) | Paper §6 final (due Sun) |

### Wed 2026-06-03 (LAUNCH coordenado)

| Canal | Status | Notes |
|---|---|---|
| GitHub README final | ✅ PR #46 + assets #155 | Synced G5 V3 0.6237 |
| COMPARISON.md | 🔄 Awaiting Sun update | nox_mem 0.6380 + hybrid@500 + GATE_VERIFIED=1 |
| Docker image | ✅ PR #68 | Ready to push |
| Blog post | 🔄 Awaiting Sun approval | #221 + Q4 numbers embedded |
| Social copy (Twitter/HN/LinkedIn) | 🔄 Awaiting Sun approval | #224 + results summary |
| asciinema demo | 🔄 Recording Sat 05-30 | Demo GIF (GTM P0 manual — Toto) |
| Paper v1.0 | 🔄 Awaiting Sun §6 final | arXiv Tue, GitHub launch Wed |
| Product Hunt | 🔄 Draft Tue 06-02 | Coordinate with arXiv |
| Nox-Supermem landing | ⏳ Deferred | Stripe-first USD (D44); pricing decision pending |

### In-flight Wave 16 (Sat evening → Sun morning)

| Wave | PRs (est) | Destaques | Status |
|---|---|---|---|
| **Wave 15** | #308-#309 | Q4 execution final + COMPARISON.md scaffold | ✅ Done Sat |
| **Wave 16 Phase A** | #310-#312 | Adapter ingestion finalization (mem0/zep/agentmemory full E2E) | 🔄 In-flight |
| **Wave 16 Phase B** | #313-#315 | Q4 harness runner polish + COMPARISON.md final populate | 🔄 In-flight |
| **Wave 16 Phase C** | #316 | ROADMAP + HANDOFF Sun sync | 🔄 In-flight |

**Próximo review:** Sun 2026-05-25 ~12h (post Wave 16 + hybrid@500). Launch readiness 100% expected Wed 10h BRT.

### D49/D50 + Lab Q1 rolling background

- D49 phase 2: cron telemetry rolling (baseline 7d, ETA D50 ~2026-05-27)
- D50 decision: activate temporal path or keep shadow? (decision ~2026-05-27)
- Lab Q1 priorities updated post-hybrid@500 verdict (reranker/scale/multilingual ETA post-launch)
- G12 R1 corpus enrich: parked, awaiting Toto sanity-check mass-edit approach (~100 memory files)

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

*ROADMAP v4.5 — v2 overnight 2026-05-17; v3 pós Wave H 2026-05-18; v4 pós Wave A 2026-05-20; v4.1 EOD 2026-05-20 D48 saga (G3→G11); v4.2 EOD 2026-05-21 inicial (G10d + F10 A+B + L4 plural); v4.3 EOD FINAL 2026-05-21 (24 PRs total + 4 prod deploys + G12 R3 VPS-deployed + G12 R1+R2 closed eval-only via PR #216 audit §11); v4.4 overnight 2026-05-21 ~22h BRT (10 agents em paralelo + §12 next-action calendário Sat-launch); **v4.5 Sat 2026-05-24 manhã (§12 ajustado por Q4 ingestion gap — 14h aggregate defer, ingestion sprint 6 agents)**. Próxima review: Sat 2026-05-24 tarde pós ingestion PRs mergeados.*
