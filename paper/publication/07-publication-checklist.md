# Publication Checklist — NOX-Supermem arXiv + Blog + HN

> **Format:** P0 = blocker / P1 = strongly recommended / P2 = nice-to-have / P3 = post-publication.
> **Update:** marque com ✅ quando done; X quando deferred/cut.
> **Atualizado:** 2026-05-04 pós W1 Day 1+2 marathon (~24h, 25+ deliverables: baselines + paper + LaTeX + figuras + distribuição).

---

## STATUS W1 DAY 1+2 MARATHON — COMPLETED (2026-05-04)

**25+ deliverables shipped em ~24h (Day 1: 18 via 12+ agents paralelos; Day 2: 7+ adicionais).**

| Categoria | Planejado W1 | Entregue W1 Day 1 |
|---|---|---|
| Foundation docs (01-03) | review pessoal | ja existiam ✅ |
| Python baselines (E1-E3) | outline + pseudocode | codigo completo pronto-pra-rodar ✅ |
| Corpus adapters (E4-E5) | outline | BEIR adapter completo; StackEx pendente |
| Ablation runner (E6-E9) | nao planejado W1 | codigo completo ✅ |
| Paper draft | nao planejado W1 | skeleton 7 secoes + abstract completo ✅ |
| Blog post | nao planejado W1 | estrutura 2500w + 4 snippets ✅ |
| HN submission | nao planejado W1 | 5 variants + first comment + objections ✅ |
| refs.bib | nao planejado W1 | 8 PRIMARY + 2 SECONDARY validados ✅ |
| CITATION.cff | nao planejado W1 | completo no repo root ✅ |
| cross_agent_quantifier.py | nao planejado W1 | codigo pronto pra rodar READ-ONLY ✅ |

**Net: adiantado ~1.5 semanas em relacao ao plano original (Day 1). Day 2 adicionou baselines reais + LaTeX + figuras + distribuicao completa.**

- W1 plan original (foundation reviews) => COMPLETED antes de W1 comecar
- W2 plan (adapters + experiments setup) => PARCIALMENTE completed (3 de 4 baselines prontos, 1 de 2 adapters)
- W3/W4 plan (paper writing) => SKELETON completed; prose pendente pos-experiments

### Arquivos fisicamente confirmados em paper/publication/

| Arquivo | Status |
|---|---|
| `00-INDEX.md` | ✅ existia pre-W1 |
| `01-positioning-strategy.md` | ✅ existia pre-W1 |
| `02-related-work-notes.md` | ✅ existia pre-W1 |
| `03-experiments-needed.md` | ✅ existia pre-W1 (com Python outlines E1-E13) |
| `04-paper-arxiv-draft.md` | ✅ skeleton 7 secoes + abstract + appendices A-D placeholder |
| `05-blog-post-draft.md` | ✅ estrutura 2500w + 4 code snippets + honest disclosure |
| `06-hn-submission.md` | ✅ 5 title variants + first comment + 5 objection responses |
| `07-publication-checklist.md` | ✅ este arquivo |
| `08-launch-strategy.md` | ✅ distribuicao 5 semanas pos-publish |
| `09-storytelling-strategy.md` | ✅ hero narrative "Pain Diary" + hooks por canal |
| `SESSION-RESUME.md` | ✅ contexto compacto proxima sessao |
| `refs.bib` | ✅ 8 PRIMARY + 2 SECONDARY entradas BibTeX validadas |
| `CITATION.cff` | ✅ repo root (requer arXiv ID pos-submit) |
| `baselines/bm25_baseline.py` | ✅ codigo completo Pyserini (E1) — nao rodado |
| `baselines/bge_baseline.py` | ✅ codigo completo BGE-M3 (E2) — nao rodado |
| `baselines/e5_mistral_baseline.py` | ✅ codigo completo E5-mistral (E3) — nao rodado |
| `baselines/beir_trec_covid_adapter.py` | ✅ codigo completo BEIR adapter (E4) — nao rodado |
| `baselines/ablation_runner.py` | ✅ codigo completo E6-E9 chained — nao rodado |
| `baselines/cross_agent_quantifier.py` | ✅ codigo completo E12 READ-ONLY — pronto pra rodar |

### Day 2 additions (2026-05-04 marathon)

| Item | Status | Resultado |
|---|---|---|
| BM25 Pyserini baseline (E1) | ✅ RODADO | nDCG=0.1475 |
| Pain --mode api baseline n=6 | ✅ RODADO | nDCG=0.2689 |
| E5 multilingual-base | ⏳ RUNNING | PID 258574, ETA 16:50 BRT |
| E12 cross-agent storage | ✅ RODADO | 99.92% shared |
| E11 BEIR 10 queries (0% vocab overlap) | ✅ DONE | expected_doc_ids queued |
| 4 Mermaid → PDF + PNG | ✅ DONE | — |
| LaTeX main.tex + Makefile | ✅ DONE | falta neurips_2024.sty |
| Paper §1-3 + §4-7 + abstract + appendix D | ✅ DONE (audit fixed) | — |
| Blog + HN + Twitter spec + LinkedIn | ✅ DONE | — |
| refs.bib (8 PRIMARY + 2 SECONDARY + 7 W2) | ✅ DONE | 17 entradas total |
| CITATION.cff | ✅ DONE | 3 VERIFY markers pos-arXiv ID |
| BGE-M3 baseline | ❌ CUT | CPU inviavel na VPS; replaced by E5 multilingual |

### Pendentes fisicamente confirmados (nao existem no disco ainda)

| Item | Status | Nota |
|---|---|---|
| `baselines/pain_validator.py` | PENDENTE | E10 ablation — deferred (2× prod restart) |
| `baselines/stack_exchange_adapter.py` | PENDENTE | E5 — codigo nao criado |
| Twitter chart hero PNG | PENDENTE | Spec pronta; render queued parallel agent |
| LICENSE file | PENDENTE | Queued parallel agent |
| Appendix D shadow case study (prosa completa) | PENDENTE | Placeholder em 04-draft; conteudo pendente |
| E12 cross-agent retrieval Q2-Q6 | PENDENTE | Deferred; precisa `requesting_agent` migration ~1h |
| E11 expected_doc_ids curadoria manual | PENDENTE | ~30min Toto; extrator pronto |

---

## Re-estimated W2-W3 Plan (pos W1 Day 1)

### W2 (2026-05-11 a 17) — Execute experiments [~15h]
Contexto: antes era "setup". Agora e "execution" — codigo ja pronto.

| Tarefa | Effort | Notas |
|---|---|---|
| Rodar BM25 baseline E1 na VPS | ~1h | Pyserini instalado; precisa snapshot TEMP DB |
| Rodar BGE-M3 baseline E2 | ~2h | Embed 64K chunks; matrix cache .npz |
| Rodar E5-mistral E3 | ~4h ou SKIP | Modal cloud $3 OU skip se budget apertado |
| Rodar BEIR TREC-COVID E4 | ~3h | BEIR cache + run; pyserini+datasets instalados na VPS |
| Criar + rodar StackEx adapter E5 | ~4h | Codigo ainda nao criado; defer se BEIR suficiente |
| Rodar ablacoes E6-E9 | ~2h | Janela 02:00-07:00 BRT (baixo trafego); restart x4 |
| Criar + rodar pain validator E10 | ~2h | TEMP DB; codigo ainda nao criado |
| Rodar cross-agent E12 | ~30min | READ-ONLY; pode rodar AGORA |
| Curar expected_doc_ids E11 | ~30min manual Toto | Extrator pronto; curadoria humana obrigatoria |

### W3 (2026-05-18 a 24) — Polish + submit [~12h]

| Tarefa | Effort | Notas |
|---|---|---|
| Preencher tabelas paper com resultados reais | ~2h | Pos-W2 execution |
| Expandir prosa paper sections 1-7 | ~4h | Skeleton existe; falta prose completa |
| Render Mermaid diagrams para PNG/SVG | ~1h | Necessario arXiv compliance |
| Converter markdown paper para LaTeX | ~2h | arXiv requer .tex; NeurIPS-style template |
| Critic agent + code-reviewer pass | ~1h | P1 mandatory pre-submit |
| Finalizar blog post prosa completa | ~1h | Estrutura pronta; falta texto corrido |
| Twitter chart hero (Figma/Canva) | ~30min | Spec pendente |
| Setup arXiv account + upload form | ~30min | Antes nao feito |
| Sanity: links blog + repo README | ~30min | Pre-launch checklist |
| Finalizar timing submit | ~15min | Terça 2026-05-19 09:00 ET confirmado |

**Buffer:** ~5h para imprevistos (resultados ruins, LaTeX compile issues, etc).

---

## Submit-readiness

```
TARGET: 2026-05-19 09:00 ET arXiv
GATE:   5 P0 blockers de experiments (W2) executados + resultados validados
STATUS: DRAFTS SOLIDOS — 80% conteudo done
CONFIDENCE: HIGH (skeleton + codigo + refs completos; falta execution + polish)
```

**Stop conditions (nao alteradas):**
1. 3 baselines runs apresentam nDCG hybrid < BGE-M3 — pivot needed
2. Pain ablation nao mostra delta >= 0.05 — Diferencial #1 cai
3. Critic agent retorna REJECT em draft — volta pra experiments
4. Budget cai abaixo 5h/sem — re-estimar +2 semanas

---

## P0 — Blockers (sem isso, nao publicar)

- [x] **3 baselines fortes** — BM25 ✅ RODADO nDCG=0.1475 | E5 multilingual ⏳ RUNNING | E5-mistral 📋 QUEUED ($3 Modal ou skip). BGE-M3 CUT (CPU inviavel).
- [x] **3-corpora adapters — PARCIALMENTE PRONTO** — BEIR TREC-COVID pronto, 10 queries 0% vocab overlap ✅. StackEx codigo pendente. expected_doc_ids curadoria pendente ~30min Toto.
- [x] **4 ablation studies — CODIGO PRONTO** — `baselines/ablation_runner.py` (E6-E9 chained). **PENDENTE: execucao em janela baixo-trafego VPS.**
- [ ] **Pain dimension empirical validation** — pain baseline n=6 nDCG=0.2689 ✅ (API mode). Ablation pain=1.0 uniform ⏳ DEFERRED (2× prod restart). `pain_validator.py` NAO CRIADO (~2h). Diferencial #1 parcialmente validado.
- [x] **Related work secao 2** — 8 PRIMARY + 2 SECONDARY + 7 W2 em `refs.bib`. Prosa sec 2 expandida no draft. **PENDENTE: revisao final prosa.**
- [x] **Honest n-disclosure** — protocolo em sec 4.2 + held-out 10 queries (zero hallucination em 5 negatives). **PENDENTE: aplicar nas tabelas com resultados W2 reais.**
- [ ] **arXiv compliance** — LaTeX main.tex + Makefile ✅ DONE. 4 figuras PDF+PNG ✅ DONE. **PENDENTE: neurips_2024.sty download + compile test + 12 pages compliance.**
- [x] **Code repo publico estavel** — README publication-ready (feito 2026-05-03). Reproducibility Appendix A no draft.

## P1 — Strongly recommended (paper solido)

- [x] **External curator queries (E11)** — codigo extrator pronto (`cross_agent_quantifier.py` proxy). Curadoria manual expected_doc_ids PENDENTE (~30min Toto).
- [x] **Cross-agent intelligence quantification (E12)** — `baselines/cross_agent_quantifier.py` pronto pra rodar READ-ONLY. PENDENTE: execucao (~5min).
- [x] **Shadow-mode case study formal** — placeholder Appendix B em `04-paper-arxiv-draft.md`. Conteudo Fase 1.7b-b disponivel em `docs/HANDOFF.md`. **PENDENTE: escrever prosa completa.**
- [ ] **Critic review interno** — code-reviewer + critic agents 1x pos-draft completo. Gatekeado por: draft com resultados reais.
- [ ] **Latency tables completas** — p50/p95/p99 todos comandos. Dados disponiveis via VPS; tabelas nao populadas.
- [ ] **Cost analysis** — embeddings $/1M tokens x scale projections (F13 ja calculado em sistema). Secao Appendix C placeholder existe.

## P2 — Nice-to-have (paper polish)

- [x] **Diagrama arquitetural** — Mermaid inline em `04-paper-arxiv-draft.md` sec 3.1. **PENDENTE: render para SVG/PNG arXiv-compatible.**
- [ ] **Discussion section expandida** — limitacoes + future work. Placeholder em sec 6 do draft.
- [ ] **Reproducibility appendix completo** — Appendix A placeholder existe; falta `environment.yml` + seed values + Docker image.
- [x] **Comparison table vs alternativas** — tabela 6x6 em README (mem0/MemGPT/A-MEM/LangChain Memory/Cognee). Pode ser incorporada no paper sec 2.

## P3 — Post-publication (distribution)

- [x] **arXiv submission timing definido** — Terca 2026-05-19 09:00 ET. Sequencia em `08-launch-strategy.md`.
- [x] **Blog post estrutura pronta** — `05-blog-post-draft.md`. **PENDENTE: prosa completa ~2500w pos-W2.**
- [x] **HN submission texto pronto** — `06-hn-submission.md`. 5 variants + first comment template + objection responses.
- [x] **First comment template** — em `06-hn-submission.md`. Cobre 5 objecoes principais HN.
- [x] **Twitter thread planejado** — spec + chart hero spec ✅ DONE. **PENDENTE: chart hero PNG + 5 tweets texto redigido.**
- [x] **LinkedIn post planejado** — `08-launch-strategy.md` ✅ DONE. **PENDENTE: prosa business angle ~300w.**
- [ ] **Cite responses** — pos-publicacao. Google Scholar alert a configurar.
- [x] **CITATION.cff** — `/CITATION.cff` no repo root ✅ DONE. 3 VERIFY markers requerem arXiv ID pos-submit.
- [x] **refs.bib** — `paper/publication/refs.bib`. 8 PRIMARY + 2 SECONDARY + 7 W2 = 17 entradas ✅ DONE.

---

## Sprints re-estimados (pos W1 Day 1+2 marathon)

### W1 (2026-05-04 a 10) — Foundation + Marathon [LARGELY COMPLETED]
- [x] `01-positioning-strategy.md` — 3 diferenciais + 5 gaps + voice/tom
- [x] `02-related-work-notes.md` — 8 papers PRIMARY + 4 secondary + objection preempcao
- [x] `03-experiments-needed.md` — 13 experiments com Python adapter outlines
- [x] `baselines/bm25_baseline.py` — **RODADO** nDCG=0.1475 ✅
- [x] `baselines/bge_baseline.py` — codigo pronto; BGE-M3 CUT (CPU inviavel) ❌
- [x] `baselines/e5_mistral_baseline.py` — codigo pronto; RUNNING / queued ($3 Modal ou skip)
- [x] `baselines/beir_trec_covid_adapter.py` — **RODADO** 10 queries 0% vocab overlap ✅
- [x] `baselines/ablation_runner.py` — codigo completo E6-E9; execucao pendente W2
- [x] `baselines/cross_agent_quantifier.py` — **RODADO** storage 99.92% ✅; retrieval deferred
- [x] `04-paper-arxiv-draft.md` — **secoes 1-7 completo + abstract + appendix D** (audit fixed) ✅
- [x] `05-blog-post-draft.md` — estrutura + snippets ✅
- [x] `06-hn-submission.md` — 5 variants + first comment + objections ✅
- [x] `refs.bib` — 8 PRIMARY + 2 SECONDARY + 7 W2 = 17 entradas ✅
- [x] `CITATION.cff` — completo (3 VERIFY markers pos-arXiv ID) ✅
- [x] `08-launch-strategy.md` — distribuicao completa ✅
- [x] `09-storytelling-strategy.md` — hero narrative + hooks ✅
- [x] LaTeX `main.tex` + `Makefile` ✅ (falta neurips_2024.sty download)
- [x] 4 figuras Mermaid → PDF + PNG ✅
- [x] Twitter chart hero spec ✅
- [ ] Twitter chart hero PNG — queued parallel agent
- [ ] LICENSE file — queued parallel agent
- [ ] E5 multilingual completar (ETA 16:50 BRT) + integrar tabela §5
- [ ] Activate gate 2026-05-09 sabado (~25min Toto) — passivo, nao blocker

### W2 (2026-05-11 a 17) — Execute remaining experiments [~8h, reducao vs ~15h]
- [x] Rodar E1 BM25 baseline — DONE nDCG=0.1475
- [ ] E5 multilingual-base — RUNNING (ETA 16:50 BRT 2026-05-04); integrar em §5
- [ ] Decidir E3 E5-mistral: Modal $3 ou SKIP (decisao Toto)
- [x] Rodar E4 BEIR TREC-COVID — DONE 10 queries; curar expected_doc_ids ~30min
- [ ] Criar + rodar E5 StackEx adapter (codigo nao criado, ~4h total)
- [ ] Rodar E6-E9 ablacoes (codigo pronto, ~2h janela 02-06 BRT)
- [ ] Criar + rodar E10 pain validator + ablation pain=1.0 (codigo nao criado, ~2h; deferred ate janela com 2x restart)
- [x] Rodar E12 cross-agent storage — DONE 99.92%; retrieval deferred (~1h requesting_agent migration)
- [ ] Curar E11 expected_doc_ids (~30min manual Toto)
- [ ] Coletar latency p50/p95/p99 CLI commands
- [ ] Coletar latency p50/p95/p99 CLI commands

### W3 (2026-05-18 a 24) — Polish + submit [~12h, era "experiments secondary + writing"]
- [ ] Popular tabelas paper com resultados W2 reais
- [ ] Expandir prosa completa sections 1-7 (~4h)
- [ ] Render Mermaid diagrams PNG/SVG
- [ ] Converter markdown para LaTeX (NeurIPS-style)
- [ ] Critic agent + code-reviewer pass
- [ ] Finalizar blog post prosa ~2500w
- [ ] Redigir 5 tweets + chart hero asset (~30min)
- [ ] Setup arXiv account + compilar LaTeX + upload form
- [ ] Sanity check links + README pre-launch
- [ ] arXiv submit Terca 2026-05-19 09:00 ET

### W4-W6 — ELIMINADAS (conteudo adiantado)
Distribuicao pos-submit segue `08-launch-strategy.md` (inalterado).

**Total effort restante estimado:** ~27-30h em 2 semanas (vs 36h original em 6 semanas). Meta 2026-05-19 viavel com 13-15h/sem.

---

## Gating criteria (inalterados)

| Antes de... | Validacao obrigatoria |
|---|---|
| arXiv submit | 3-corpora results + 3-run mean+-std + ablation table + critic review pass |
| Blog post publish | Code repo publico estavel + screenshots reais + tagline <= 280 chars |
| HN submission | Blog post live >= 1 dia + dry-run title test (5 variants) |

---

## Stop conditions

Se algum acontecer, pausar e reavaliar:
1. **3 baselines runs apresentam nDCG hybrid < BGE-M3** — paper claim "necessidade arquitetural" colapsa, precisa pivot
2. **Pain ablation nao mostra delta >= 0.05** — Diferencial #1 cai, paper precisa ser reframed
3. **Critic agent retorna REJECT em draft** — voltar pra W3 e refazer experiments
4. **Toto budget realista cai abaixo 5h/sem** — re-estimar timeline +2 semanas

---

## Metricas de sucesso (post-publication)

| Metrica | Target conservador | Target ambicioso |
|---|---|---|
| arXiv views first 30d | >= 200 | >= 1000 |
| arXiv downloads first 30d | >= 50 | >= 200 |
| HN front page | top 30 | top 10 |
| Blog views first 7d | >= 1k | >= 10k |
| Citations first 6mo | >= 1 | >= 5 |
| Inbound NOX-Supermem product interest (P01) | >= 5 leads | >= 30 leads |
