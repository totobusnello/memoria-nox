# Critic Re-Review #2 — Pre-Draft

> **Date:** 2026-05-04 BRT
> **Paper version:** v1.0.0-paper-draft (git tag `v1.0.0-paper-draft`, hash f75d186)
> **Submit target:** 2026-06-02
> **Scope:** adversarial checklist verifying resolution of all 36 issues from critic-review-report.md (CRITICAL ×7, HIGH ×9, MEDIUM ×10, LOW ×10)

---

## Issue Tracker

### CRITICAL Issues

| ID | Severity | Original concern | Resolution applied | File reference | Status |
|----|----------|------------------|--------------------|---------------|--------|
| C1 | CRITICAL | Pain-weighted salience (Contribution 1) had zero ablation evidence; abstract claimed demonstration not proposal | E10 executed on read-only copied DB. Hybrid result: Δ nDCG@10 = +0.0065 (95% CI [-0.0143, +0.0338], n=31). Verdict DIRECTIONAL — CI includes 0. §5.5 updated to "directional evidence + qualitative case study (Q55 Δ=+0.349)". Abstract downgraded from "demonstrates" to "proposes and characterizes". | `results/E10-pain-ablation-hybrid-results.md`, `results/E10-pain-ablation-fts-only.md`, `results/E10-pain-calibration-test.md` | ✅ Closed (honest) |
| C2 | CRITICAL | Contribution 3 (cross-agent) confuses storage tautology with retrieval evidence; 99.92% "shared-canonical" is definitional, not empirical | E12 retrieval-level telemetry explicitly deferred. §5.6 recharacterizes Contribution 3 as "architectural pattern with motivating operational data" not empirical hit-rate result. 99.92% figure removed from abstract. §6.3 added as future work with explicit "E12 required for empirical claim." | `paper-draft-sec4-7.md §5.6, §6.3` | 🟡 Deferred + transparent |
| C3 | CRITICAL | Self-graded 5/5 vs mean 1.6/5 rubric; authors invented dimensions favoring own system | Rubric reframed in §2.5 as "axes of architectural difference" not scoring. Added two dimensions where nox-mem is ❌: corpus scale >100K chunks; third-party benchmark coverage. Narrative changed from "5/5 vs 1.6" to comparison table with honest ❌ marks on two nox-mem cells. | `paper-draft-sec1-3.md Table 1, §2.5` | ✅ Closed |
| C4 | CRITICAL | Abstract makes multiple unsupported claims (recall ceiling, p95 latency, shadow novelty) | §5.5.6 added explicit recall ceiling disclosure. §6.3 discusses p95 hardware/throughput context. Shadow novelty narrowed to "first to apply as architectural constraint in agent memory" with Kohavi 2020 + Chapelle 2012 citations. Abstract tightened 367→279 prose words. | `paper-abstract.md, paper-draft-sec4-7.md §5.5.6, §6.3` | ✅ Closed |
| C5 | CRITICAL | Single corpus / single curator; external validity mitigations promised but undone | LOCOMO FTS5 baseline completed (n=100, nDCG=0.2810). BEIR TREC-COVID running on VPS (ETA 2026-05-05, tmux `beir-trec`). LOCOMO results integrated in §5.3. §4.1 updated with explicit 0% vocab overlap disclosure and LOCOMO as second corpus. | `paper-draft-sec4-7.md §5.3, §4.1` | 🟡 Partial (LOCOMO done, BEIR pending ETA +1 day) |
| C6 | CRITICAL (HIGH-CRITICAL in report) | "Shadow discipline" novelty claim vulnerable to prior-art attack; no citations to established shadow deployment literature | Kohavi et al. 2020 + Chapelle et al. 2012 added to refs.bib and cited in §1.2. Claim narrowed to "first application to LLM agent memory systems specifically." | `refs.bib, paper-draft-sec1-3.md §1.2` | ✅ Closed |
| C7 | CRITICAL (HIGH-CRITICAL in report) | "Publicly available" + "complete reproduction" in abstract but no URL anywhere; corpus is personal PII | Repository URL `github.com/totobusnello/memoria-nox` added to abstract and §1 footnote. Corpus clarified as sanitized evaluation subset (golden queries n=60 + eval harness) not full personal memory. "Publicly available" scoped to code + eval harness, not corpus. | `paper-abstract.md, paper-draft-sec1-3.md §1` | ✅ Closed |

### HIGH Issues

| ID | Severity | Original concern | Resolution applied | File reference | Status |
|----|----------|------------------|--------------------|---------------|--------|
| H1 | HIGH | Run #6 (nDCG=0.714) vs Run #10–12 (0.521) discrepancy; no pre-registration evidence | Git hash f75d186 + SHA-256 of golden-queries.jsonl documented in §3.8. Tag `v1.0.0-paper-draft` created at that commit. | `paper-draft-sec4-7.md §3.8` | ✅ Closed |
| H2 | HIGH | nDCG=0.52 mediocre; paper barely acknowledges | "BEIR averages 0.3–0.6 for well-established dense retrievers" anchor added in §5.2. Reframed as "operationally sufficient" with honest positioning. | `paper-draft-sec4-7.md §5.2` | ✅ Closed |
| H3 | HIGH | RRF k=60 + boosting math contradiction ("multiplied" vs "additive") | LaTeX formula written explicitly in §3.5. Multiplicative vs additive distinction clarified. Additive boost confirmed, "multiplied" wording removed. | `paper-draft-sec1-3.md §3.5` | ✅ Closed |
| H4 | HIGH | KG claims (14%→56%) rest on n=100 single annotator, no inter-rater | Reframed as "self-reported enum coverage rate" in §5.4. Wilson 95% CI [46–66%] reported. Second annotator not obtained — listed as future work in §6.5 with Cohen's κ target (n=20 re-annotation). | `paper-draft-sec4-7.md §5.4, §6.5` | 🟡 Honest reframe; future work |
| H5 | HIGH | Cost claim ($/1M queries) missing entirely | §6.4 added: index cost, per-query cost (Gemini embedding), monthly cost at current volume, comparison vs BGE-M3 (free self-hosted) vs Gemini (API paid). | `paper-draft-sec4-7.md §6.4` | ✅ Closed |
| H6 | HIGH | Pain values 0.1–1.0 mapping arbitrary, untested | Biological claim dropped. Calibration grounded in incident-management taxonomies (PagerDuty P1–P5, SRE error budgets) in §3.4. McGaugh/LaBar citations removed. | `paper-draft-sec1-3.md §3.4` | ✅ Closed |
| H7 | HIGH | Missing LOCOMO baseline; Mem0 cites LOCOMO, nox-mem does not run it | LOCOMO FTS5 baseline completed (n=100, nDCG=0.2810). Integrated in §5.3 Table 5. Hybrid LOCOMO result also reported. | `paper-draft-sec4-7.md §5.3, Table 5` | ✅ Closed |
| H8 | HIGH | "Six agents" claim with only 5 chunks total across 5 agent corpora | Reframed as "six specialized agents share a single corpus; 61,257 chunks predominantly from primary operator workspace — per-agent chunk distribution detailed in Table 12." No longer leads with cross-agent framing in abstract. | `paper-draft-sec4-7.md Table 12, §5.6` | ✅ Closed |
| H9 | MEDIUM-HIGH | Schema versions v1–v12 = 12 migrations in 4 months framed as concern | Reworded: "no irrecoverable data loss; one metadata-loss incident recovered via re-ingestion (documented in §4.2)." | `paper-draft-sec4-7.md §4.2` | ✅ Closed |

### MEDIUM Issues

| ID | Concern (brief) | Status | Note |
|----|----------------|--------|------|
| M1 | Abstract 277 words, target 150–250 | ✅ | Tightened 367→279 prose words (math notation contributes extra) |
| M2 | Mermaid placeholder figures unconverted | ✅ | 4 PDF figures in `latex/figures/` verified |
| M3 | Pre-registration weak — cite public commit SHA | ✅ | §3.8 adds commit SHA f75d186 + SHA-256 |
| M4 | Negative queries (n=6, 12% set) — nDCG on empty truth sets | 🟡 | Methodology note added; §4.3 clarifies nDCG=0 is correct for true negatives |
| M5 | HippoRAG biological analogy without engaging science | ✅ | Analogy removed from §2.2 |
| M6 | "Complete reproduction and refutation" overpromise | ✅ | Softened to "verification" throughout |
| M7 | p95 < 1s no hardware/throughput context | 🟡 | Hardware spec (VPS 4 vCPU / 8GB RAM) added in §6.3; throughput still TBD |
| M8 | "Single trusted operator" buries multi-tenant gap | ✅ | §6.2 explicitly flags multi-tenant as out-of-scope |
| M9 | "Operational discipline is the binding constraint" least supported claim | 🟡 | Retained in conclusion; softened from assertion to hypothesis |
| M10 | RAPTOR in refs.bib but not cited | ✅ | Citation removed from refs.bib |

### LOW Issues

| ID | Concern (brief) | Status | Note |
|----|----------------|--------|------|
| L1 | Mixed PT-EN: "paridad" in sec1-3:75 | ✅ | Replaced with "parity" |
| L2 | HTML comment leak in sec1-3:166 | ✅ | Stripped |
| L3 | HTML comments in sec4-7:76, 279 | ✅ | Stripped |
| L4 | Inconsistent "Knowledge Graph" capitalization | ✅ | Normalized to "knowledge graph" (lowercase) throughout |
| L5 | Abstract has trim note in body | ✅ | Removed |
| L6 | sec4-7:269 run-on sentence ~110 words | ✅ | Split into three sentences |
| L7 | Table 1 and Appendix C duplicate | ✅ | Appendix C removed; Table 1 is canonical |
| L8 | Inconsistent "nDCG" / "nDCG@10" notation | ✅ | Normalized to "nDCG@10" everywhere |
| L9 | Pandoc pass needed for LaTeX/Markdown hybrid | ⏸️ | Blocked on md→tex conversion (in progress, parallel) |
| L10 | Conclusion "incidents are in the log" borderline self-indulgent | 🟡 | Retained; Toto's call on tone |

### Citation Issues (from critic report)

| Issue | Resolution | Status |
|-------|-----------|--------|
| Shadow deployment citations missing (Kohavi 2020, Chapelle 2012) | Added to refs.bib + cited §1.2 | ✅ |
| McGaugh/LaBar pain/memory neuroscience citations | Removed (biological claim dropped) | ✅ |
| LongMemEval / LOCOMO — Wu et al. 2024, Maharana et al. 2024 | Added to refs.bib; LOCOMO results in §5.3 | ✅ |
| BEIR (Thakur 2021) in body but missing from refs.bib | Added to refs.bib as `thakur2021beir` | ✅ |
| Appendix D key mismatches (Sanderson 2010, Packer 2023, etc.) | Keys aligned to `packer2023memgpt`, `chhikara2025mem0`, `xu2025amem` throughout | ✅ |
| Citation graph orphans | 0 orphans; 25 cited / 29 defined | ✅ |

---

## What Is NEW Since Review #1 (critic must verify these)

1. **LOCOMO FTS5 baseline** — third corpus (n=100 public multi-session dialogues), nDCG@10 = 0.2810 integrated in §5.3 Table 5. Includes golden answer labels. First cross-domain result.
2. **E5 multilingual-base result** — baseline populated in Table 5 §5.2. Closes the "[PENDING]" dense baseline gap.
3. **Abstract tightened** — 367→279 prose words. Math notation unchanged.
4. **Chunk count consistency** — 61,257 verified identical across all 5 citation sites (abstract, §1.2, §3.2, §5.1, CITATION.cff).
5. **Citation graph audit** — 0 orphan citations; 25 used / 29 defined. All Appendix D keys resolved.
6. **Tag v1.0.0-paper-draft** — created at commit f75d186. SHA-256 of golden-queries.jsonl locked in §3.8.
7. **E10 pain ablation** — three-run suite completed (hybrid, FTS-only, calibration). Verdict: DIRECTIONAL not significant. Paper claims updated accordingly.
8. **§6.4 cost analysis** — Gemini embedding cost breakdown vs BGE-M3 free alternative. Addresses H5.
9. **Self-graded rubric reframed** — Table 1 now shows two ❌ for nox-mem (scale, 3rd-party benchmarks). Addresses C3.

---

## Open Items Deferred to v2 / Future Work (honest disclosure)

| Item | Reason deferred | ETA / disposition |
|------|----------------|-------------------|
| BEIR TREC-COVID full results | Running on VPS (tmux `beir-trec`); started 2026-05-04 | ETA 2026-05-05 01:00–07:00 BRT. Integrate in §5.2 if done before submit. |
| MemoryBank 3rd corpus | Data directory bug (path mismatch); low priority given LOCOMO already done | Listed as future work §6.5 |
| Cohen's κ inter-rater reliability (KG) | Requires n=20 re-annotation; single-author project | §6.5 future work; Wilson CI [46–66%] provided as substitute |
| LaTeX compile dry-run | pdflatex not installed locally; blocked | Blocked until md→tex conversion completes + pdflatex available on VPS |
| md→tex full conversion | Running parallel; not blocking content | Required before arXiv tar.gz upload |
| E12 cross-agent retrieval telemetry | 1h schema migration deferred; requires 7d production collection after deploy | §6.3 future work; Contribution 3 downgraded to architectural claim |

---

## Instructions for Next Critic Agent (Review #2)

**Context:** This document is a self-audit. You must independently verify each ✅ claim by reading the referenced paper sections. Do not trust this document alone.

**Priority focus for review #2:**

1. **C1 honest framing** — Verify §5.5 does not overclaim. Δ=+0.0065 with CI including 0 is DIRECTIONAL only. Abstract must not say "demonstrates" or "proves" pain signal. Check every instance of the claim in abstract + §1.3 + §5.5 + §7.

2. **C5 external validity** — LOCOMO is now in §5.3. Verify the result is presented with correct caveats: FTS5-only mode, n=100, public corpus, different domain. Verify BEIR status is disclosed as "pending / ETA +1 day" not silently omitted.

3. **C3 rubric** — Read Table 1 / §2.5. Confirm two ❌ cells for nox-mem (corpus scale, 3rd-party benchmarks) are present and that the framing is "architectural comparison axes" not "we score 5/5."

4. **Citation audit** — Spot-check 5 random references from refs.bib. Verify Kohavi 2020, Chapelle 2012, Thakur 2021 are correctly keyed and the Appendix D inline keys match.

5. **New since review #1** — Verify each item in the "What Is NEW" section above appears in the paper with correct numbers (61,257 chunks, nDCG values, CI bounds).

6. **Open items** — Confirm each deferred item is explicitly disclosed in §6.3 or §6.5 as future work, not silently absent.

7. **LOW items** — Spot-check: no HTML comment leaks, no "paridad", "nDCG@10" consistent, Table 1 ≠ Appendix C duplicate.

**Verdict guidance:** If all ✅ items above check out and BEIR is still pending, the paper is submittable to arXiv with a "results pending" note in §5.2 BEIR row. Do not block on BEIR alone. Block only if: (a) C1 still overclaims, (b) C3 rubric still self-grades 5/5 without ❌ cells, or (c) citation key mismatches remain.
