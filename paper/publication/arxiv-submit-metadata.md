# arXiv Submit Metadata — NOX-Supermem Paper
# Rehearsal target: 2026-05-19 | Submit before 14:00 ET
# All fields copy-paste ready. TBDs marked explicitly.

---

## 1. TITLE
**Limit: 250 characters**

```
The Pain Diary and Shadow Discipline: A Memory System That Learns from Its Own Incidents
```

Character count: 90 — well within limit.

---

## 2. AUTHORS

**Format: Last, First [Affiliation] — one author per block**

```
Busnello, Luiz Antonio
```

- **Affiliation:** Curious Tech Entrepreneur, São Paulo, Brazil
- **Email:** lab@generantis.com.br
- **ORCID:** [TBD — register at orcid.org before 2026-05-19 if desired; not required for submission]

> Note: arXiv author field accepts plain "Luiz Antonio Busnello" in the name box plus affiliation in the affiliation box. No comma-reversal needed in the UI form itself.

---

## 3. ABSTRACT
**Limit: 1920 characters | Plain-text version below: 1997 chars (77 over). LaTeX-inline-math version: ~1900 chars (fits).**

> **RECOMMENDED PATH (2026-05-05):** Paste the **content inside** `\begin{abstract}...\end{abstract}`
> from `latex/sec_abstract.tex` (i.e., the body without the begin/end tags).
> arXiv's submit form accepts inline LaTeX math (`$\Delta$`, `$\pm$`, `$[-0.014, +0.034]$`,
> `$\times$`) and renders it correctly. This preserves all numbers/CIs with proper notation,
> stays within ~1900 chars, and keeps a single source of truth.
>
> **Pre-submit step:** convert any remaining `\cite{...}` tags to inline parenthetical
> form (e.g., `\cite{kohavi2020trustworthy,chapelle2012interleaved}` → `(Kohavi 2020;
> Chapelle 2012)`). The current abstract has zero `\cite` calls — verified in
> `sec_abstract.tex`.
>
> **Fallback A** (if LaTeX math doesn't render correctly in arXiv): use the plain-text
> version below (1997 chars, 77 over) and trim manually — drop the final punchline
> "Operational discipline is at least as important as embedding sophistication." (~85 chars
> saved).
>
> All numbers below reflect post-cure R01c-v1.1 state (2026-05-07): 3-month corpus, 61,302 chunks,
> BM25 Pyserini 0.1475, hybrid 0.5831 (4.0x lift), BEIR TREC-COVID e5 0.8335.

```
Production memory systems fail not because retrieval is hard, but because silent architectural degradation accumulates faster than any embedding model can compensate. GraphRAG, MemGPT, Mem0, and A-MEM encode structure and recency; none encodes incident severity, none enforces ranking-change validation. NOX-Supermem's design is incident-driven: each failure became a schema constraint. Three contributions: (1) Pain-weighted salience (salience = recency x pain x importance, pain in [0.1, 1.0]) as a first-class retrieval dimension, calibrated to PagerDuty P1-P5, not psychometric scales. Ablation (n=31, hybrid mode) shows non-significant aggregate effect (Delta = +0.0065, 95% CI [-0.014, +0.034]); lift observed in 1/31 queries (Q55, Delta = +0.349); 29/31 unaffected because semantic scores were not tied. The binding constraint is BM25 recall ceiling: 55 of 60 queries fail FTS-only regardless of pain calibration; full hybrid retains Recall@10 = 0.7667 via Gemini. (2) Shadow discipline: a seven-day gate before any ranking change activates, enforced via /api/health as an architectural constraint, not a convention. (3) Shared-canonical context: six agents, one corpus, no federation. On 61,302 chunks, hybrid retrieval (FTS5 + Gemini 3072-d + RRF, k=60) achieves nDCG@10 = 0.5831 +/- 0.0046 (n=60, 3-run mean, post-cure gold standard v1.1) versus 0.0000 for FTS5 vanilla and 0.1475 for BM25 Pyserini (n=60), a 4.0x lift over the strongest lexical baseline. Edge-type enum coverage improved 14% -> 56% (4x gain, n=100, 95% Wilson CI [46-66%]); self-reported enum coverage rate, not human-validated accuracy. On LOCOMO (Maharana et al., 2024, n=100), FTS5 achieves nDCG@10 = 0.281, confirming lexical difficulty is corpus-dependent; on BEIR TREC-COVID, multilingual-e5-base achieves nDCG@10 = 0.8335 (n=50). Open gap: corpus scale >100K. Code, harness, golden set (n=60), and incident log: https://github.com/totobusnello/memoria-nox (MIT). Operational discipline is at least as important as embedding sophistication.
```

> Formatting note: arXiv abstract field does not render LaTeX math inline. Replace × with "x" and ∈ with "in" as done above. Avoid special Unicode symbols.

---

## 4. COMMENTS
**Limit: 1024 characters | Current: ~280 characters**

```
18-22 pages, 4 figures, 14 tables. Public repository: github.com/totobusnello/memoria-nox. Reproducibility kit includes evaluation harness, BM25/E5 baseline adapters, BEIR adapter, and 60-query golden set. Solo author, 3-month production system. License: MIT.
```

---

## 5. PRIMARY SUBJECT CATEGORY

```
cs.IR
```

Rationale: the core contribution is a retrieval architecture (hybrid FTS5 + dense + RRF, nDCG@10 evaluation, baseline comparisons). cs.IR is the canonical category for retrieval systems papers and maximizes visibility to the target audience.

---

## 6. CROSS-LIST CATEGORIES
**Maximum: 3**

```
cs.CL
cs.AI
cs.DB
```

- **cs.CL** — LLM agent context, embedding models (Gemini), language-grounded retrieval
- **cs.AI** — multi-agent system design, autonomous agent infrastructure
- **cs.DB** — SQLite/FTS5 architectural choices, schema versioning, knowledge graph storage

---

## 7. KEYWORDS
**5–10 recommended; arXiv does not enforce a hard limit here**

```
agent memory; retrieval-augmented generation; knowledge graph; hybrid retrieval; pain-weighted salience; shadow discipline; multi-agent systems; operational discipline; SQLite-based RAG; production memory system
```

> Separate by semicolons in the arXiv form. Some fields use commas — adapt to whatever the form shows on submission day.

---

## 8. LICENSE

```
Creative Commons Attribution 4.0 International (CC BY 4.0)
```

Rationale: maximizes downstream reuse, citation reach, and compatibility with future venue submissions that require open-access licenses. MIT code license in the repo is separate and unaffected.

---

## 9. ENDORSEMENT

arXiv requires endorsement for first-time submitters in cs.IR if the account is new.

**Action required before 2026-05-15 (buffer: 4 days):**

1. Check whether your arXiv account already has cs.IR endorsement (login → "My account" → endorsement status).
2. If not endorsed: contact 1–2 authors of cited papers via email. Best candidates:
   - **Patrick Lewis** (lead author, Lewis et al. 2020 RAG paper, arXiv:2005.11401) — widely reachable via academic email
   - **Gordon Cormack** (Cormack & Lynam 2009 RRF paper) — University of Waterloo
3. Email template (adapt as needed):

```
Subject: arXiv endorsement request — cs.IR

Dear [Name],

I am submitting a paper titled "The Pain Diary and Shadow Discipline:
A Memory System That Learns from Its Own Incidents" to arXiv cs.IR
on 2026-05-19. Your work ([cite their paper]) is directly referenced
in our evaluation. I am a first-time arXiv submitter in cs.IR and
would be grateful for an endorsement. The draft is available at
[link to draft PDF] for your review.

Thank you,
Luiz Antonio Busnello
lab@generantis.com.br
```

4. arXiv endorsement link will be sent to the endorser automatically once you start the submission and request endorsement — follow arXiv's on-screen flow.

---

## 10. SOURCE UPLOAD (TAR)

**arXiv requires LaTeX source, not PDF-only.**

Files to include in tar.gz:

```
main.tex
refs.bib
neurips_2024.sty
figures/fig-salience-formula.pdf
figures/fig-architecture-overview.pdf
figures/fig-hybrid-search-pipeline.pdf
figures/fig-shadow-discipline-flow.pdf
```

> Figures must be PDF or EPS — not PNG raster. Verify before packaging.

Pre-flight tar command (run from paper/ directory):

```bash
bash scripts/arxiv-tar.sh
# or manually:
tar -czf arxiv-submit-$(date +%Y%m%d).tar.gz \
  main.tex refs.bib neurips_2024.sty figures/*.pdf
```

Upload the resulting `.tar.gz` in the "Upload files" step of the arXiv submission form.

---

## 11. PRE-SUBMIT CHECKLIST

Run through this on 2026-05-18 (day before), not the morning of submit.

### LaTeX / PDF
- [ ] PDF compiles cleanly with zero errors (`pdflatex main.tex` twice, then `bibtex main`, twice more)
- [ ] No `?` citation markers in compiled PDF
- [ ] No `??` figure reference markers
- [ ] All figures embedded as PDF/EPS (not PNG raster)
- [ ] Page count 18–22 (verify with `pdfinfo main.pdf | grep Pages`)

### Metadata limits
- [ ] Abstract < 1920 characters (count without LaTeX markup)
- [ ] Title < 250 characters (90 chars — already confirmed)
- [ ] Comments < 1024 characters

### Content integrity
- [ ] nDCG@10 values consistent across abstract, body, and tables
- [ ] Author name spelled identically in all places: "Luiz Antonio Busnello"
- [ ] Repository URL live and public: github.com/totobusnello/memoria-nox
- [ ] CITATION.cff updated with actual arXiv ID after submission (post-submit task)

### Submission logistics
- [ ] arXiv account active and email verified
- [ ] Endorsement secured (cs.IR) — or confirmed not required for your account
- [ ] License decision locked: CC BY 4.0
- [ ] Source tar.gz prepared and test-uploaded in arXiv "sandbox" (if available)

---

## 12. POST-SUBMIT TIMELINE

| Day | Date | Action |
|-----|------|--------|
| Day 0 | Tue 2026-05-19 | Submit before **14:00 ET** (22:00 BRT) — arXiv processing window for same-day queuing |
| Day 0 | Tue 2026-05-19 | arXiv sends submission confirmation email with paper ID (arXiv:XXXX.XXXXX) |
| Day 1 | Wed 2026-05-20 | Paper appears on arXiv. Check PDF preview email link — validate visually (figures, tables, references) |
| Day 1 | Wed 2026-05-20 | Update CITATION.cff with real arXiv ID and URL |
| Day 1 | Wed 2026-05-20 | Publish blog posts: dev.to + Substack, including arXiv URL |
| Day 2 | Thu 2026-05-21 | Submit to Hacker News at **09:00 ET** (10:00 BRT) with arXiv + blog URLs |

> arXiv announce emails go out ~20:00 ET the day of submission for papers submitted before 14:00 ET. Papers submitted after 14:00 ET appear next business day.

---

## TBDs — Items Requiring Action Before 2026-05-19

| Item | Status | Owner | Deadline |
|------|--------|-------|----------|
| ORCID registration | Optional but recommended | Toto | 2026-05-15 |
| arXiv endorsement (cs.IR) | Required if first paper | Toto | 2026-05-15 |
| Final arXiv ID and URL in CITATION.cff | Post-submit | Toto | 2026-05-20 |
| Git tag at submit time (update CITATION.cff version) | Pre-submit | Toto | 2026-05-19 |
| Figures confirmed as PDF/EPS (not PNG) | Pre-submit | Toto | 2026-05-18 |
| multilingual-e5-base baseline result (W2) | Optional for richer abstract | Toto | 2026-05-18 |
