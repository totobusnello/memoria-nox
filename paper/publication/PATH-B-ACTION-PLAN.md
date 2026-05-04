# Path B Action Plan — Submit slip 2026-05-19 → 2026-06-02

> **Decisão:** 2026-05-04 ~08:30 BRT
> **Trigger:** critic-review-report.md verdict REVISE_HEAVY (36 issues, 7 CRITICAL)
> **Goal:** preservar contribution claims, fechar 7 CRITICAL antes de submit

---

## Nova timeline

| Old date | New date | Event |
|---|---|---|
| ~~2026-05-19 Tue~~ | **2026-06-02 Tue 09:00 ET** | arXiv submit |
| ~~2026-05-20 Wed~~ | **2026-06-03 Wed** | dev.to + Substack publish |
| ~~2026-05-21 Thu 09:00 ET~~ | **2026-06-04 Thu 09:00 ET** | HN submit |

**Slip:** +14 dias

---

## Sprint W2 (2026-05-04 → 2026-05-10): close 7 CRITICAL

### Critical fixes obrigatórios

| # | Issue | Action | Owner | ETA |
|---|---|---|---|---|
| **C1** | Pain ablation deferred | Execute E10 on copied DB (no prod restart needed) | python-pro agent | 1 day |
| **C2** | Cross-agent storage tautology | Deploy E12 migration + start 7d telemetry collection | typescript-pro + Toto SSH | 15min apply + 7d wait |
| **C3** | Self-graded rubric | Add 2 dimensions where nox-mem partial/none (>100K scale, LOCOMO benchmark coverage) | technical-writer | 30min |
| **C4** | Abstract overclaims | Soften: "we propose"/"we suggest" instead of "we demonstrate" until validated | technical-writer | 30min |
| **C5** | External validity | Run BEIR TREC-COVID baseline against nox-mem hybrid | python-pro | 1 day |
| **C6** | Shadow novelty vs prior art | Add Kohavi 2020 + Chapelle 2012 + Pinterest interleaving citations | researcher + technical-writer | 30min |
| **C7** | Reproducibility URL | Add github.com/totobusnello/memoria-nox to abstract + §1 + §6 | technical-writer | 5min |

### Citation bugs (compile-blocking)

| Bug | Fix |
|---|---|
| `\cite{thakur2021beir}` not in refs.bib | Add Thakur 2021 BEIR entry |
| Appendix D uses `Sanderson2010/Packer2023/OpAudit2026` keys | Rename to match refs.bib (`packer2023memgpt` etc) OR add missing entries |

---

## Sprint W3 (2026-05-11 → 2026-05-17): HIGH issues + LOCOMO

| # | Issue | Action |
|---|---|---|
| **H1** | Pre-registration weak | Add public commit SHA + GitHub URL with timestamp |
| **H2** | nDCG=0.52 mediocre framing | Reframe as "operationally sufficient" with IR literature comparison |
| **H3** | RRF + boost math contradiction | Write actual LaTeX formula, distinguish multiplicative vs additive |
| **H4** | KG n=100 no inter-rater | Wilson 95% CI + label protocol description |
| **H5** | Cost claim missing | Add §6.x cost breakdown (Gemini vs BGE-M3 self-hosted) |
| **H6** | Pain values arbitrary | Cite McGaugh 2003 OR drop biological framing |
| **H7** | Missing LOCOMO baseline | Run LOCOMO subset against nox-mem hybrid |
| **H8** | Six agents = 5 chunks | Reframe "shared canonical" with honest chunk distribution table |
| **H9** | Schema v1-v12 framing | Reword "no irrecoverable data loss" with metadata-loss caveat |

---

## Sprint W4 (2026-05-18 → 2026-05-24): MEDIUM/LOW + integration

- M1-M10: trim abstract, fix pre-registration, methodology details
- L1-L10: stylistic polish, HTML leak strip, bibliography cleanup
- Integrate E5 multilingual results (running now, ETA 13:30 BRT)
- Integrate E10 ablation results
- Integrate E12 cross-agent retrieval results (after 7d wait)
- Integrate BEIR + LOCOMO results
- Critic re-review #2 → confirm REVISE_LIGHT or SUBMIT_AS_IS

---

## Sprint W5 (2026-05-25 → 2026-06-01): submit prep

- Re-compile LaTeX with all updates
- Final pass: figures, tables, bibliography
- arXiv endorsement secured (contact Patrick Lewis or Cormack)
- Pre-submit dry-run via arxiv-package.sh
- Publish blog draft to dev.to scheduled
- Substack draft scheduled

---

## Submit week (2026-06-02 → 2026-06-04)

- Tue 06-02 09:00 ET: arXiv submit
- Wed 06-03: blog + Substack publish (cross-post)
- Thu 06-04 09:00 ET: HN submit + first comment within 5min

---

## Disparos imediatos (now)

### Wave 6 — fix CRITICAL bugs in parallel

1. **C3** (rubric reframe) — technical-writer agent, 30min
2. **C4 + C6 + C7** (abstract softening + citations + URL) — technical-writer agent, 1h
3. **Citation bugs** (BEIR + Appendix D keys) — technical-writer agent, 20min
4. **H3** (RRF formula) — technical-writer agent, 20min
5. **H6** (pain calibration) — technical-writer agent, 20min
6. **L2/L3** (HTML leak strip) — refactoring-specialist, 10min

Total: 6 agents parallel, ~2h wall.

---

## Capacity check

- W2-W5 = 4 weeks × 12h/week = 48h total
- 7 CRITICAL fixes ≈ 4 days = ~12h
- 9 HIGH fixes ≈ 5 days = ~15h
- Re-runs (E5, BEIR, LOCOMO, E10, E12) ≈ 8h actual + 7d wait
- Re-integration + critic review #2 ≈ 8h
- Submit prep ≈ 5h

**Total committed:** ~48h ≈ exactly capacity

**Margem incident:** 0h. Tight but feasible. Se algo derrapar (incidente prod, agent quality issue), slip mais 1 sem pra 2026-06-09.
