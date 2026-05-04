# Publication Checklist — NOX-Supermem arXiv + Blog + HN

> **Format:** P0 = blocker / P1 = strongly recommended / P2 = nice-to-have / P3 = post-publication.
> **Update:** marque com ✅ quando done; X quando deferred/cut.

---

## P0 — Blockers (sem isso, não publicar)

- [ ] **3-corpora results** — adicionar BEIR subset + Stack Exchange. Run 3-batch each. Gap #1.
- [ ] **3 baselines fortes** — BM25 (Pyserini) + BGE-M3 + E5-mistral-7b. Gap #3.
- [ ] **4 ablation studies** — FTS-only / sem-RRF / sem-salience / sem-section_boost. Gap #4.
- [ ] **Pain dimension empirical validation** — ablation `salience com vs sem pain` em ≥10 post-incident queries. Diferencial #1.
- [ ] **Related work §2** — 8-10 papers citados corretamente, posicionamento honest. Section dedicada.
- [ ] **Honest n-disclosure** — toda tabela com sample size + std + caveat method.
- [ ] **arXiv compliance** — LaTeX template (NeurIPS-style ou similar) + 12 pages max + figures vetoriais.
- [ ] **Code repo público estável** — README publication-ready (✅ already done 2026-05-03), reproducibility instructions.

## P1 — Strongly recommended (paper sólido)

- [ ] **External curator queries** (10 held-out) — Gap #2. Se inviable, BEIR queries servem.
- [ ] **Cross-agent intelligence quantification** — Diferencial #3 needs numbers (e.g., "X% das hits cross-agent search vieram de agent ≠ requester").
- [ ] **Shadow-mode case study formal** — Fase 1.7b-b salience activation como anexo metodológico.
- [ ] **Critic review interno** — code-reviewer + critic agents 1× pós-draft completo.
- [ ] **Latency tables completas** — p50/p95/p99 todos comandos (search, impact, detect-changes, eval).
- [ ] **Cost analysis** — embeddings $/1M tokens × scale projections (já F13).

## P2 — Nice-to-have (paper polish)

- [ ] **Diagrama arquitetural** — system overview SVG/PNG (1 figure, prefer Mermaid → PDF).
- [ ] **Discussion section** — limitations + future work + threats to validity expandido.
- [ ] **Reproducibility appendix** — environment.yml + seed values + Docker image.
- [ ] **Comparison table** vs LangChain Memory + Cognee + GraphRAG (hybrid feature parity).

## P3 — Post-publication (distribution)

- [ ] **arXiv submission Tuesday 09:00 ET** (visibility window).
- [ ] **Blog post live ≥ 1 dia antes de HN**.
- [ ] **HN submission Tuesday/Wednesday 09:00 ET** (peak engagement).
- [ ] **First comment template ready** — counter common HN objections.
- [ ] **Twitter thread** com 1 chart hero.
- [ ] **LinkedIn post** com angle business (P01 product tease).
- [ ] **Cite responses** — quando paper for cited, monitor via Google Scholar alerts.
- [ ] **Update CITATION.cff** no repo com BibTeX correto.

---

## ⏱️ Sprints (4-6 semanas, ~6h/semana)

### W1 (2026-05-04→10) — Foundation [~5h]
- [ ] Finalizar `01-positioning-strategy.md` review pessoal Toto
- [ ] Completar `02-related-work-notes.md` com 8 papers full notes
- [ ] Detalhar `03-experiments-needed.md` com Python adapter outlines
- [ ] Adquirir Voyage trial $20 (OPCIONAL — Gap #5 OPÇÃO B alternative se BGE-M3 cobre)

### W2 (05-11→17) — Experiments primary [~7h]
- [ ] Impl BM25 baseline adapter Python
- [ ] Impl BGE-M3 dense baseline
- [ ] BEIR subset adapter (TREC-COVID 50 queries)
- [ ] Run baseline 3-batch each → tabela inicial

### W3 (05-18→24) — Experiments secondary + start writing [~6h]
- [ ] Stack Exchange dump adapter (10K subset)
- [ ] 4 ablation studies runs
- [ ] arXiv paper draft skeleton (sections + headings + key tables placeholders)

### W4 (05-25→31) — Writing intensive [~8h]
- [ ] Paper sections 1-3 (Intro + Related Work + Architecture) — 4h
- [ ] Paper sections 4-6 (Experiments + Discussion + Conclusion) — 4h

### W5 (06-01→07) — Polish + critic + revise [~6h]
- [ ] Critic agent + code-reviewer pass
- [ ] Revise based on findings
- [ ] Blog post draft (2500 words)
- [ ] HN submission text (5 title variants tested)

### W6 (06-08→14) — Submit + distribute [~4h]
- [ ] arXiv submit Tuesday 06-09 09:00 ET
- [ ] Blog publish 06-10
- [ ] HN submit 06-11 Tuesday 09:00 ET
- [ ] Twitter/LinkedIn announce
- [ ] Monitor + respond to comments first 48h

**Total estimated:** ~36h spread em 6 semanas = **6h/semana** (within budget).

---

## 🚨 Stop conditions (quando reconsiderar timeline)

Se algum acontecer, pausar e reavaliar:
1. **3 baselines runs apresentam nDCG hybrid < BGE-M3** — paper claim "necessidade arquitetural" colapsa, precisa pivot
2. **Pain ablation não mostra Δ ≥ 0.05** — Diferencial #1 cai, paper precisa ser reframed
3. **Critic agent retorna REJECT em draft** — voltar pra W3 e refazer experiments
4. **Toto budget realista cai abaixo 5h/sem** — re-estimar timeline +2 semanas

---

## 📊 Success metrics (post-publication)

| Métrica | Target conservador | Target ambicioso |
|---|---|---|
| arXiv views first 30d | ≥ 200 | ≥ 1000 |
| arXiv downloads first 30d | ≥ 50 | ≥ 200 |
| HN front page | top 30 | top 10 |
| Blog views first 7d | ≥ 1k | ≥ 10k |
| Citations first 6mo | ≥ 1 | ≥ 5 |
| Inbound NOX-Supermem product interest (P01) | ≥ 5 leads | ≥ 30 leads |
