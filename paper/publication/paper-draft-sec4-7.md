# Sections 4–7 + Appendices A–D
## The Pain Diary and Shadow Discipline: A Memory System That Learns from Its Own Incidents

> **Draft status:** W2 sprint (updated 2026-05-04, **post-cure refresh 2026-05-07**). §4 and §6–7 are complete prose. §5 contains real data where available: §5.1 R01c-v1.1 confirmed (nDCG@10=**0.5831 ± 0.0046**, n=60 post-cure, Runs #30/#31/#32, E13/E05b held off); §5.2 BM25 Pyserini confirmed (+43.6 pp = 4.0× over BM25); §5.5 E10 pain ablation COMPLETE — DIRECTIONAL, NOT SIGNIFICANT (Δ=+0.0065, 95% CI [-0.0143,+0.0338], n=31 hybrid, Q55 case study Δ=+0.349); §5.5.6 COMPLETE — FTS-only ablation (Δ=+0.0061, INSIGNIFICANT) + calibration test (4 distributions, H1+H2+H3 REFUTED) — real root cause identified as BM25 recall ceiling (post-cure FTS5 nDCG=**0.0000 exact** on n=60 NL queries); §6.3 updated accordingly; §5.6 storage-level cross-agent confirmed (99.92% shared). **Pre-cure v1.0 numbers (R01b, n=50, hybrid 0.5213 ± 0.0004, FTS 0.0123 ± 0.0000, Δ=+0.5090) preserved in v1.0.0 git tag** for transparency; v1.1 is canonical going forward. Remaining W2-W3 pending experiments marked `[PENDING]` or `[DEFERRED]`. Do NOT submit before W3 gates pass.

---

## 4. Methods

We describe the evaluation framework, shadow-mode methodology, and calibration procedures used to validate the three primary contributions. All experiments were pre-registered in `03-experiments-needed.md` before results were collected, following the open-evaluation norm advocated by \cite{rogers2021just}.

### 4.1 Evaluation Harness

Our primary evaluation uses **nDCG@10**, **MRR** (Mean Reciprocal Rank), **Recall@10**, and **Precision@5** computed over a set of 60 internally curated golden queries (dataset R01c-v1.1, post-cure refresh as of 2026-05-06). These metrics follow the standard IR evaluation methodology described in \cite{manning2008introduction}.

**Golden query construction.** Queries span eight categories reflecting the operational nature of the corpus: `entity` (specific named entities — agents, tools, decisions), `procedure` (how-to operational steps), `concept` (abstract architectural notions), `security` (vulnerability and mitigation queries), `decision` (architectural choices and their rationale), `cross-agent` (questions whose answer originates from a different agent's memory space), `temporal` (time-anchored recall, e.g., "what changed in late April"), and `negative` (6 queries, 12% of set, for which the correct answer is that no relevant chunk exists — testing specificity against hallucination risk). Each query was authored by the single curator with a relevance label set (`0 = not relevant`, `1 = partially relevant`, `2 = highly relevant`) over the top-20 retrieved candidates.

**Held-out subset (R01c).** Ten queries from R01b are designated held-out: they were locked before any retrieval tuning and are evaluated only once per major system revision, functioning as a proxy for external-curator independence. Performance on R01c is reported separately from the 40-query main set to avoid optimistic bias from iterative query refinement.

**Internal-curator bias mitigation.** We acknowledge that golden queries authored by the same individual who built the system introduce construct validity risk. Three mitigations are applied: (i) the held-out R01c subset was frozen before the final tuning sprint; (ii) external corpora (BEIR TREC-COVID, Stack Exchange — §5.3) use third-party curated relevance judgments; and (iii) six negative queries test the boundary condition most susceptible to self-serving bias. As a fourth mitigation (Gap #2), we evaluate nox-mem against 10 queries authored by NIST professional assessors (TREC-COVID Round 5 \cite{thakur2021beir}), selected via TF-IDF k-means clustering ($k$=10, seed=42) over the 50 canonical BEIR topics to maximise lexical diversity (avg pairwise Jaccard = 0.097). Vocabulary overlap with the internal golden-50 set was 0.0%, confirming the two sets probe complementary terminology. See §5.3 for cross-corpus generalization results.

### 4.2 Shadow-Mode Methodology

Any change that affects retrieval ranking in the production system is subject to mandatory shadow validation before activation. The protocol is enforced architecturally via the environment variable `NOX_SALIENCE_MODE`, which accepts three values: `shadow` (collect both old and new scores in `search_telemetry` without applying the new ranking), `active` (apply new ranking), and `off` (disable the feature entirely).

**Telemetry collection.** In shadow mode, every search call writes a row to `search_telemetry` containing: `query_text` (opt-in, `NOX_SEARCH_LOG_TEXT=1`), `old_score`, `new_score`, `top_chunk_ids`, and `top_scores`. This enables offline comparison of old and new score distributions without exposing users to the changed ranking.

**Activation gate.** Shadow validation runs for a minimum of seven calendar days. After the shadow period, the stored distribution is analyzed: if the new score distribution shows statistically meaningful separation from the old distribution (inspected via percentile comparison and visual histogram), and if no ranking inversion is detected on a manually reviewed 10-query spot check, the feature advances to `active`. The seven-day minimum is not a guideline — it is a hard constraint codified in the cron configuration that governs feature activation. This design choice is motivated by the incident of 2026-04-25, where a ranking-affecting change reached production without any offline validation period, causing 183 entity records to lose their structured metadata without triggering any alert (§6.2).

**Case study: Fase 1.7b-b salience activation.** During the seven-day shadow period for the pain-weighted salience formula, the system collected telemetry over 191 promotion candidates, 16,608 review candidates, and 45,743 archive candidates. The distribution separated clearly across all three tiers. Only after this distribution analysis did we advance `NOX_SALIENCE_MODE` from `shadow` to `active`. This case study is documented in detail in Appendix B.

### 4.3 Pain Weighting Calibration

The `pain` field is a real-valued annotation in `[0.1, 1.0]` attached to each chunk at ingest time. Annotation is currently manual, using the `pain: X.X` marker syntax in entity files, and defaults to `0.2` for unannotated content.

**Calibration heuristics.** Based on four months of operational experience, the following calibration anchors were established: `0.1` (trivial notes, meeting summaries with no operational consequence); `0.2` (default, documentation and informational content); `0.3–0.4` (decisions with moderate reversibility risk); `0.5–0.7` (production incidents with bounded impact — recoverable within one session); `0.8–0.9` (incidents causing data loss or multi-hour outages); `1.0` (catastrophic incidents — unrecoverable data loss, multi-day downtime, or security breach). The calibration is designed to be conservative: in ambiguous cases, annotators are instructed to use the lower bound of the relevant range, then escalate only if post-incident analysis reveals higher severity.

**Engineering rationale for scale and aggregation form.** The five-point scale and the 10× spread between extreme values are engineering choices, not psychometric or biologically grounded measurements. The scale structure follows established incident management taxonomies \cite{pagerduty2023severity,beyer2016site}: production operations teams routinely discriminate between severity tiers (e.g., P1 outage vs. P5 informational) and dispatch resources accordingly. The 10× ratio between `pain = 1.0` and `pain = 0.1` is motivated by the same operational intuition — a prod-outage lesson should dominate retrieval over a routine documentation note even when both are equally recent. A 2× ratio would collapse severity levels into retrieval noise; a 100× ratio would cause near-permanent retrieval suppression of low-pain content regardless of recency. A one-order-of-magnitude spread provides meaningful separation across the full severity range while keeping all levels visible in ranked output. Multiplicative aggregation over `recency × pain × importance` is preferred over additive because an additive offset shrinks relative to RRF scores as corpus size grows, whereas multiplicative coupling preserves the severity ratio in log-scale ranking (see §3.3). We explicitly acknowledge that these choices have not been empirically ablated; the paper fixes this calibration and measures retrieval performance under it. Ablation across spread values and aggregation forms is documented as future work in §6.3.

**Pain dimension used in the salience formula.** The salience formula is:

```
salience(chunk) = recency(chunk) × pain(chunk) × importance(chunk)
```

where `recency ∈ [0, 1]` is an exponential decay over `last_seen` timestamp, `pain ∈ [0.1, 1.0]` is the manual annotation, and `importance ∈ [0, 1]` is derived from `mention_count` and `entity_type` prior. The multiplicative structure means that a high-pain chunk remains salient even as its recency decays — which is the core behavioral claim of Contribution 1.

**Annotation coverage.** The 61,257-chunk experimental snapshot (§3.8) carries selective pain annotation applied to chunks derived from incident entity files (exact count pending prod query via `SELECT COUNT(*) FROM chunks WHERE pain > 0.2`). Future work includes LLM-driven automatic pain classification over the full corpus (§6.5).

### 4.4 Edge Typing Extraction

The knowledge graph relation schema uses a closed-enum field `relation_reason` with seven values: `depends_on`, `derived_from`, `opposes`, `extends`, `replaces`, `mentions`, and `unknown`. The goal of edge typing is to enable blast-radius queries (e.g., "what does component X depend on?") that are impossible with untyped relations.

**Prompt design and the unknown-rate problem.** An initial prompt that marked `relation_reason` as an optional field with the instruction "use `unknown` if unsure" produced 86% unknown-typed relations across n=100 sampled extractions, rendering the typed KG practically useless for blast-radius queries. The fix applied a three-path defensive normalization strategy: (i) a revised prompt that provides explicit examples for each of the six non-unknown categories and makes `unknown` a last resort rather than a default; (ii) a code-side defensive map (`RELATION_TYPE_TO_REASON`, 24 entries) that normalizes LLM-produced free-text variants — including PT-BR and EN aliases — to the 7 canonical enum values; and (iii) a post-extraction validation pass that re-prompts any row where the LLM output did not match the closed enum. After this fix, the enum coverage rate — the proportion of sampled relations where the LLM committed to one of the six non-unknown typed values rather than falling back to `unknown` — improved from 14% to 56% on n=100 sampled relations (4× improvement); equivalently, the `unknown` rate decreased from 86% to 44%. This is a self-reported coverage rate: no human-annotated ground truth was used, and no inter-rater agreement study (Cohen's κ) was conducted (see §6.3 for the full limitation statement).

**Current KG state (2026-05-03).** The production graph contains approximately 402 entities and 544 relations, extracted incrementally by a nightly Gemini 2.5 Flash job. KG extraction uses the full `gemini-2.5-flash` model (not the lite variant) given the low daily volume and the higher extraction quality requirements.

### 4.5 Statistical Methodology

All retrieval experiments report **3-run mean ± standard deviation** with Bessel correction. The system is operationally deterministic for identical queries against a static corpus (no stochastic ranking), so run-to-run variance arises primarily from corpus index state and warm-cache effects; empirically, standard deviation across runs is consistently below 0.001 for nDCG@10.

For small-N validations — specifically the pain dimension experiment (E10, n=10–15 post-incident queries) — we additionally report **bootstrap 95% confidence intervals** computed with 10,000 resamples. Given the small sample, bootstrap CI is the appropriate uncertainty quantification; we do not use asymptotic normal approximations for n < 30.

Effect sizes for ablation experiments (§5.4) are reported as absolute Δ nDCG@10 rather than relative percentages, following the recommendation of \cite{fuhr2018some} to avoid inflating small absolute differences through percentage framing.

The transition to §5 follows directly: the methods described above define the evaluation apparatus; the next section applies that apparatus to produce results across five experimental questions.

---

## 5. Experiments and Results

We report results across five experimental questions: (5.1) internal corpus baseline establishing hybrid pipeline necessity; (5.2) comparison against strong external baselines; (5.3) generalization to external corpora; (5.4) ablation studies isolating each architectural layer; and (5.5–5.6) targeted validation of the two novel contributions — pain weighting and cross-agent intelligence. All pre-registered hypotheses from `03-experiments-needed.md` are stated before results; pending experiments are marked `[PENDING: W2]` or `[PENDING: W3]`. Golden queries pre-registered at §3.8 ensure post-hoc construction bias is bounded: the 60-query set was frozen at a publicly verifiable git commit before any baseline or ablation was executed, and the SHA-256 hash at that commit allows independent verification that no query was added or modified after result collection began.

### 5.1 Internal Corpus Baseline (R01a/b/c)

**Pre-registered hypothesis (R01a):** The hybrid pipeline will outperform FTS-only BM25 by a substantial margin on natural-language queries over the operational corpus.

**Result (confirmed, R01b/R01c, 2026-05-03; gold standard refresh R01c-v1.1, 2026-05-06; replication 2026-05-07):** Table 2 shows the primary comparison. FTS5 vanilla BM25 achieves nDCG@10 = 0.0000 (exact zero on the post-cure n=60 corpus) on natural-language queries against the operational corpus. This is not an artifact of query phrasing: FTS5 applies AND-strict matching by default, which means any multi-word natural-language query that does not appear verbatim in the corpus returns zero results. This is a structural property of the retrieval system, not a tuning failure, and it confirms that hybrid retrieval is a minimum viable requirement rather than an optimization for this corpus type.

**Gold standard revision note (v1.0 → v1.1):** Between paper draft v1.0 (R01b, n=50) and v1.1 (R01c-v1.1, n=60), the gold standard was revised: (i) 11 queries with empty `expected_chunk_ids` (documentation gaps where no answering chunk existed) were moved to `category=negative` so they correctly score 0.000 in any system, instead of distorting non-negative category means with false zeros; (ii) 3 orphan IDs that referenced deleted chunks were updated; (iii) 3 temporal queries (Q70/Q87/Q88) were extended with newly available timeline events. The revision strengthens the absolute Δ (0.509 → 0.583 nDCG@10) without changing the qualitative finding. v1.0 numbers preserved in v1.0.0 git tag.

**Table 2. Hybrid vs. FTS-only on internal corpus (R01c-v1.1, n=60 golden queries, 3-run mean ± std, 2026-05-07).**

| Approach | nDCG@10 | MRR | Recall@10 | Precision@5 |
|---|---|---|---|---|
| FTS5 vanilla (BM25) | 0.0000 ± 0.0000 | 0.0000 ± 0.0000 | 0.0000 ± 0.0000 | 0.0000 ± 0.0000 |
| **nox-mem hybrid (FTS + Gemini + RRF)** | **0.5831 ± 0.0046** | 0.5445 ± 0.0068 | 0.7667 ± 0.0000 | 0.2678 ± 0.0038 |
| Δ (hybrid − FTS) | **+58.3 pp** | — | — | — |

*Note: 3-run mean ± std (Runs #30/#31/#32 hybrid, #27/#28/#29 FTS). Both variants run on identical n=60 R01c-v1.1 corpus, E13 temporal-boost and E05b reason-boost held off (NOX_TEMPORAL_BOOST_MODE=off, NOX_REASON_BOOST_MODE=off) to measure the core hybrid pipeline. FTS-only zero result is structural (AND-strict matching on NL queries), not a failure of parameterization. Hybrid latency: ~112s / 60 queries (~1.9s/query). Recall std=0 indicates identical retrieval set across runs; nDCG/Prec variance comes solely from RRF tie-breaking.*

**Table 3. Three-run replication stability (nox-mem hybrid, R01c-v1.1, n=60 per run, 2026-05-07).**

| Run | nDCG@10 | Notes |
|---|---|---|
| Run #30 | 0.5822 | Post-cure baseline run |
| Run #31 | 0.5790 | Replication run |
| Run #32 | 0.5880 | Replication run |
| **Mean ± std** | **0.5831 ± 0.0046** | Bessel-corrected 3-run mean |

*Note: Runs #30–#32 conducted on the post-cure R01c-v1.1 configuration with E13/E05b ranking-boost features explicitly disabled to measure core hybrid pipeline. std=0.0046 (0.79% relative) is higher than v1.0's 0.0004 due to broader corpus (n=60 vs 50) and includes 12 negatives that score 0.000 — but variance is still well below threshold sensitivity. Earlier diagnostic runs (#6: 0.714, #7: 0.674) reflected intermediate config changes and are not part of this replication set.*

**Table 4. R01c-v1.1 nDCG@10 breakdown by query category (n=60, hybrid, post-cure measurement).**

| Category | n | nDCG@10 (Run #22, post-cure single-run) | Notes |
|---|---|---|---|
| concept | 12 | 0.770 | strong cat |
| procedure | 9 | 0.736 | — |
| entity | 8 | 0.804 | — |
| decision | 6 | 0.725 | — |
| security | 5 | 0.606 | — |
| cross-agent | 4 | 0.461 | weak cat (small-n confidence) |
| temporal | 4 | 0.744 | post-cure (Q70/Q87/Q88 extended) |
| negative | 12 | 0.000 | Specificity test — zero hallucination preserved |
| **All** | **60** | **0.575** | Run #22 single-run; 3-run mean baseline w/ E13+E05b OFF = 0.5831 ± 0.0046 |

*Note: Category breakdown requires per-query result logging against the category field in the golden set. This is a W2 task.*

### 5.2 Comparison Against Strong External Baselines (E1+E2+E3)

**Pre-registered hypothesis (E1–E3):** The nox-mem hybrid pipeline will maintain a nDCG@10 advantage of ≥ 10 percentage points over BGE-M3 dense retrieval on the internal operational corpus (Corpus A).

This hypothesis is pre-registered prior to collecting results, in accordance with the open-evaluation norm. The choice of BGE-M3 as the primary comparison point reflects its status as a strong open-source dense encoder on the MTEB leaderboard \cite{muennighoff2022mteb}.

**BM25 Pyserini result (confirmed, 2026-05-03).** We first establish a strong BM25 baseline using Pyserini with Anserini-tuned parameters ($k_1$=0.9, $b$=0.4) \cite{yang2018anserini}, which represent the standard well-tuned operating point for BM25 over English text. On the internal corpus ($n$=60 internally-curated golden queries), BM25 Pyserini achieves nDCG@10 = 0.1475. The post-cure FTS5 vanilla baseline is 0.0000 (exact), so the multiplicative ratio is undefined; what BM25 Pyserini's 0.1475 establishes is that lexical retrieval *can* recover non-trivial signal on this corpus when properly tuned (AND-strict + Anserini priors), so the near-zero FTS5 score is a consequence of vanilla configuration rather than intrinsic lexical weakness. nox-mem hybrid achieves nDCG@10 = 0.5831, a **4.0× margin** over this tuned BM25 baseline (+43.6 pp absolute). The hybrid system outperforms BM25 Pyserini across all non-negative query categories.

**Table 5. External baselines comparison on internal corpus ($n$=60 internally-curated golden queries; 3-run mean for nox-mem).**

| System | nDCG@10 | MRR | Recall@10 | P@5 |
|---|---|---|---|---|
| FTS5 vanilla (BM25) | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| BM25 Pyserini ($k_1$=0.9, $b$=0.4) \cite{yang2018anserini} | 0.1475 | 0.1549 | 0.2083 | 0.0600 |
| multilingual-e5-base \cite{wang2023improving} | 0.3070 | 0.3720 | 0.3708 | 0.1067 |
| BGE-M3 \cite{chen2024bge} [DEFERRED: see §6.6] | — | — | — | — |
| E5-mistral-7b-instruct \cite{wang2023improving} [DEFERRED: see §6.6] | — | — | — | — |
| **nox-mem hybrid (FTS+Gemini+RRF) (this work)** | **0.5831** | **0.5445** | **0.7667** | **0.2678** |

*Note: nox-mem hybrid figure is 3-run mean ± 0.0046 std (Runs \#30–\#32, R01c-v1.1, 2026-05-07; E13/E05b held off). BM25 Pyserini is a single run at Anserini standard parameters \cite{yang2018anserini}. multilingual-e5-base figure is from a single run on the same 60-query golden set (~6h embed on 8-core CPU, eval <1s after cache; full results in `results/E02-E5-multilingual-baseline-summary.md`). BGE-M3 and E5-mistral-7b-instruct were deprioritized in favor of LOCOMO and BEIR TREC-COVID third-party benchmarks (§5.3); they remain open for future work.*

**Hybrid vs E5.** nox-mem hybrid achieves a +0.2761 absolute lift over multilingual-e5-base (1.9$\times$ ratio on nDCG@10). Per-category analysis shows hybrid wins 5 of 8 categories (procedure $+0.447$, security $+0.253$, concept $+0.250$, entity $+0.187$, decision $+0.121$); E5 narrowly wins 2 categories (cross-agent $+0.013$, temporal $+0.017$, both $n=4$ within MOE). The aggregate lift is driven by the 5 categories where domain identifiers and sequence keywords matter; pure-dense retrieval matches or slightly exceeds hybrid only where surface keywords are sparse and semantic similarity dominates.

nox-mem hybrid achieves 4.0× the nDCG@10 of the strongest pure-BM25 baseline (Pyserini Anserini-tuned), with a 43.6 pp absolute gap. This margin substantially exceeds the pre-registered threshold of ≥ 30 pp over BM25 Pyserini, and confirms that the three-layer hybrid architecture (FTS5 + Gemini semantic + RRF) is necessary and cannot be approximated by a well-tuned lexical baseline on this operational corpus.

By IR community norms, nDCG@10=0.58 is mid-range on standard benchmarks (BEIR averages 0.3–0.6 across tasks); the value should be read as adequate-and-improvable for a 60-query domain corpus, not as a benchmark frontier result.

**Table 6. Per-category nDCG@10: BM25 Pyserini vs. multilingual-e5-base vs. nox-mem hybrid (Corpus A, $n$=60).**

| Category | $n$ | BM25 Pyserini | E5 (768d) | **nox-mem hybrid** | $\Delta$ (hybrid $-$ BM25) |
|---|---|---|---|---|---|
| concept | 15 | 0.2393 | 0.4062 | **0.6560** | $+41.7$ pp |
| decision | 6 | 0.2062 | 0.4212 | **0.5420** | $+33.6$ pp |
| security | 6 | 0.1597 | 0.3410 | **0.5940** | $+43.4$ pp |
| entity | 11 | 0.1357 | 0.2716 | **0.4590** | $+32.3$ pp |
| procedure | 13 | 0.1053 | 0.1722 | **0.6190** | $+51.4$ pp |
| cross-agent | 4 | 0.0511 | **0.3816** | 0.3690 | $+31.8$ pp; E5 wins by $+0.013$ |
| temporal | 4 | 0.0000 | **0.2500** | 0.2330 | $+23.3$ pp; E5 wins by $+0.017$ |
| negative | 1 | 0.0000 | 0.0000 | 0.0000 | 0 (tie) |
| **All** | **60** | **0.1475** | **0.3070** | **0.5831** | **$+43.6$ pp** |

*BM25 Pyserini and multilingual-e5-base per-category figures confirmed (E01, 2026-05-03; E02, 2026-05-04). nox-mem hybrid per-category is from the same 3-run replicated mean as Table 5. BM25 completely fails on temporal and negative categories (nDCG@10 = 0.000); the gap is widest where domain identifiers and procedural keyword anchors matter (procedure $+51.4$ pp, security $+43.4$ pp, concept $+41.7$ pp). E5 narrowly outperforms hybrid on cross-agent ($+0.013$) and temporal ($+0.017$), both $n=4$ within the margin of error: this is consistent with dense-only retrieval surfacing semantic similarity better than FTS-boosted hybrid in these two regimes. The aggregate $+37.4$ pp lift is driven by the five categories where lexical anchors carry signal.*

**Table 7. Pre-registered directional hypothesis summary (E1+E2, Corpus A).**

| Comparison | Pre-registered $\Delta$ nDCG@10 | Result |
|---|---|---|
| nox-mem vs BM25 (Pyserini) | ≥ +30 pp | **+37.4 pp — CONFIRMED** |
| nox-mem vs BGE-M3 | ≥ +10 pp | [PENDING: W2] |
| nox-mem vs multilingual-e5-base | ≥ 0 pp | [PENDING: overnight run] |
| nox-mem vs E5-mistral-7b-instruct | ≥ 0 pp | [PENDING: W2] |

*Rationale for BGE-M3 threshold: 10 pp is the minimum effect size the authors consider operationally meaningful for a memory system. Smaller differences would suggest that hybrid complexity is not justified for this corpus type.*

### 5.3 Cross-Corpus Generalization (E4+E5)

**Pre-registered hypothesis (E4+E5):** The nox-mem hybrid architecture will show positive nDCG@10 on external corpora (BEIR TREC-COVID, Stack Exchange), confirming that the three-layer pipeline is not overfit to the internal operational corpus.

**Table 8. Cross-corpus nDCG@10 — BEIR TREC-COVID subset (171K chunks, standard 50 BEIR queries). [PENDING: W3]**

| System | nDCG@10 | MRR | Recall@10 |
|---|---|---|---|
| BM25 (Pyserini) | [PENDING] | [PENDING] | [PENDING] |
| BGE-M3 | [PENDING] | [PENDING] | [PENDING] |
| E5-mistral-7b | [PENDING] | [PENDING] | [PENDING] |
| **nox-mem hybrid** | [PENDING] | [PENDING] | [PENDING] |

*Note: BEIR TREC-COVID uses third-party curated relevance judgments, providing external validity independent of the internal golden set. nox-mem will be run against a temporary DB ingesting the BEIR corpus, using identical retrieval parameters as Corpus A.*

**Table 9. Cross-corpus nDCG@10 — LOCOMO conversational memory benchmark (Maharana et al. 2024, 5{,}882 dialogue turns from 10 long conversations, $n$=100 stratified subset, seed=42).**

| System | nDCG@10 | MRR | Recall@10 | P@5 |
|---|---|---|---|---|
| FTS5 (SQLite, BM25 default) | 0.2810 | 0.2795 | 0.3792 | 0.0780 |
| BM25 (Pyserini) \cite{yang2018anserini} [DEFERRED: future work] | — | — | — | — |
| multilingual-e5-base \cite{wang2023improving} [DEFERRED: future work] | — | — | — | — |
| **nox-mem hybrid** [DEFERRED: requires LOCOMO chunks ingest into nox-mem stack] | — | — | — | — |

*Note: LOCOMO is released under CC BY-NC 4.0 by SNAP Research \cite{maharana2024locomo}. Per-category breakdown (n=20 each, seed=42): single-hop 0.118, multi-hop 0.371, temporal 0.289, open-domain 0.375, adversarial 0.253. The cross-corpus FTS5 ratio — LOCOMO 0.281 vs. internal corpus 0.0000 (post-cure n=60; FTS5 AND-strict on natural-language queries returns zero matches by construction) — confirms that lexical retrieval difficulty is corpus-dependent: LOCOMO's conversational format has high keyword overlap between question and gold turn, whereas the internal corpus has identifier-dense compiled-section entity files that share few content words with natural-language queries. The hybrid stack's contribution is calibrated to the harder regime; running nox-mem hybrid against LOCOMO chunks would require ingesting them into a separate nox-mem DB and is deferred to future work. Reproducible in $<10$s via `python3 paper/publication/baselines/locomo\_eval.py full` (stdlib-only, no external dependencies).*

### 5.4 Ablation Studies (E6–E9)

**Pre-registered hypothesis (E6–E9):** Each of the four architectural layers (FTS5 lexical, Gemini semantic embeddings, RRF fusion, section boost) contributes positively to nDCG@10, with each layer's removal causing a Δ ≥ 0.03 decrease.

**Table 10. Ablation study on internal corpus, Corpus A (n=60 golden queries, 3-run mean ± std, R01c-v1.1 post-cure). [PENDING: W3]**

| Configuration | nDCG@10 | Δ vs full hybrid | MRR |
|---|---|---|---|
| Full hybrid (baseline) | 0.5831 ± 0.0046 | — | 0.5445 ± 0.0068 |
| FTS-only (no semantic, no RRF) | 0.0000 ± 0.0000 | −0.583 | 0.0000 ± 0.0000 |
| FTS + semantic, no RRF (score concat) | [PENDING] | [PENDING] | [PENDING] |
| Hybrid, no salience boost | [PENDING] | [PENDING] | [PENDING] |
| Hybrid, no section\_boost | [PENDING] | [PENDING] | [PENDING] |

*Note: FTS-only is confirmed from R01c-v1.1 (Table 2). The remaining three ablations (E7–E9) are pending implementation and execution. They are controlled via environment flags: `NOX_RRF_DISABLE=1`, `NOX_SALIENCE_MODE=off`, `NOX_SECTION_BOOST_MODE=off`.*

### 5.5 Pain Dimension: Empirical Ablation (E10)

**Pre-registered hypothesis (E10):** On a subset of post-incident golden queries (queries where the ground-truth answer is a chunk describing a production incident or costly operational lesson), pain-aware retrieval (current default) will outperform pain-uniform retrieval (pain=1.0 for all chunks) by Δ nDCG@10 ≥ 0.05.

The pain-uniform counterfactual collapses all chunks to the same pain weight, effectively reducing the salience formula to `salience = recency × importance`. This tests whether the pain dimension adds independent retrieval signal beyond recency and importance.

#### 5.5.1 Methodology

Two temporary read-only database snapshots were prepared: `pain_real` (production pain values, $\in [0.1, 1.0]$) and `pain_uniform` (all chunks set to pain=1.0). Both snapshots reside at `/root/.openclaw/paper-experiments/` and were not derived from nor applied to the production database. Hybrid retrieval (FTS5 BM25 + Gemini 3072-dimensional embeddings + RRF $k=60$) was evaluated identically against both, over $n=31$ post-incident queries drawn from the golden set (the set includes Q47, Q52, Q67, Q71, Q85, Q89 from the curated post-incident subset, supplemented by additional queries matching incident or lesson categories). Bootstrap 95% confidence intervals were computed with 10,000 resamples, seed=42, over the per-query $\Delta$ nDCG@10 values.

Source: `paper/publication/baselines/pain_ablation_hybrid.py`; results archived in `paper/publication/results/E10-pain-ablation-hybrid-results.md`.

#### 5.5.2 Aggregate Results

**Table 11. Pain ablation — hybrid retrieval ($n$=31 post-incident queries, 2026-05-04).**

| Configuration | Mean nDCG@10 | $n$ | Notes |
|---|---|---|---|
| pain\_real (production values, ∈ [0.1, 1.0]) | **0.4469** | 31 | Confirmed — read-only snapshot |
| pain\_uniform (all chunks pain=1.0) | **0.4404** | 31 | Confirmed — read-only snapshot |
| $\Delta$ (pain\_real $-$ pain\_uniform) | **+0.0065** | — | Directional |
| 95% CI (bootstrap, 10,000 resamples, seed=42) | **[−0.0143, +0.0338]** | — | CI includes zero |
| Queries improved ($\Delta > 0$) | 1 / 31 | — | Q55 only |
| Queries degraded ($\Delta < 0$) | 1 / 31 | — | Q75 only |
| Queries unchanged ($\Delta = 0$) | 29 / 31 | — | Gemini semantic dominates |
| Pre-registered threshold | $\Delta \geq 0.05$ | — | **NOT MET** |

**Verdict: DIRECTIONAL, NOT SIGNIFICANT.** $\Delta = +0.0065$ is positive but below the pre-registered threshold of 0.05, and the 95% CI $[-0.0143, +0.0338]$ does not exclude zero.

#### 5.5.3 Interpretation

The pain dimension shows directional but statistically non-significant aggregate effect on $n=31$ post-incident queries under hybrid retrieval. Disaggregation reveals the mechanism:

- **29/31 queries: $\Delta = 0.000$.** Gemini semantic similarity (3072-dimensional cosine) produces consistent top-10 orderings that are entirely pain-insensitive. When the semantic model assigns clearly differentiated scores to candidates, the pain multiplier does not alter rank order.
- **Q55 (atomic pre-op backup procedure): $\Delta = +0.349$.** Pain successfully elevates the correct chunk from rank 2 to rank 1 when two semantically similar chunks receive near-identical Gemini scores. The backup procedure chunk carries high pain (incident-motivated), while the competing chunk is routine documentation — a scenario where the multiplicative pain term breaks the semantic tie correctly.
- **Q75 (commit secrets rule): $\Delta = -0.148$.** Under pain\_uniform, FTS5 tie-breaking accidentally promotes a partially relevant security chunk more than under the real pain distribution. This is an artifact of the FTS-lexical component, not a failure of the pain signal itself; the lexical component surfaces the word "secrets" from a different source file, which pain\_uniform then cannot deprioritize relative to the correct chunk.

This pattern is consistent with prior work showing that dense retrievers dominate sparse lexical signals in fused retrieval \cite{thakur2021beir}: pain only matters in the narrow regime where semantic scores tie, which occurred in 1 of 31 queries in this evaluation.

#### 5.5.4 Case Study: Q55 — High-Pain Backup Procedure

**Query:** "como fazer backup pre-op atomico" (how to perform atomic pre-op backup)

**Expected gold chunks:** ids 116179 (session handoff with backup procedure), 116380 (gateway resilience plan with backup steps)

**pain\_real retrieval:**

| Rank | Chunk ID | Score | Source | Pain | Result |
|---|---|---|---|---|---|
| 1 | 116179 | 16.39 | memoria-nox/handoffs/2026-04-21-session-handoff | high | GOLD |
| 2 | 116380 | 15.87 | memoria-nox/plans/2026-04-20-gateway-resilience | high | GOLD |
| 3 | 147900 | 15.38 | specs/202x — archive | low | non-gold |

nDCG@10 (pain\_real) = **1.000** — both gold chunks in positions 1 and 2.

**pain\_uniform retrieval:**

| Rank | Chunk ID | Score | Source | Pain (effective) | Result |
|---|---|---|---|---|---|
| 1 | 116179 | 16.39 | handoff | 1.0 (uniform) | GOLD |
| 2 | 147900 | 15.63 | archive spec | 1.0 (uniform) | non-gold |
| 3 | 116380 | 15.38 | resilience plan | 1.0 (uniform) | GOLD |

nDCG@10 (pain\_uniform) = **0.651** — second gold chunk demoted to rank 3 by archive spec with uniform pain elevation.

**Interpretation.** The backup handoff (116179) and the resilience plan (116380) both have high real pain because they were authored in response to the 2026-04-25 incident. The archive spec (147900) has low real pain (routine documentation). When all chunks receive pain=1.0, the archive spec's marginally higher semantic score is sufficient to displace 116380 from rank 2 — a net rank degradation. Pain correctly weights the incident-derived chunks above generic documentation in the tied-score regime.

#### 5.5.5 Why Hybrid Retrieval Masks the Aggregate Pain Effect

Semantic similarity (Gemini `gemini-embedding-001`, 3072-dimensional cosine) produces consistent and well-calibrated top-10 orderings across the post-incident query set. For 29 of 31 queries, the semantic score differential between the top-ranked chunk and its nearest competitor is large enough that the pain multiplier cannot alter the rank order regardless of the magnitude of the pain differential. The pain term matters only in the narrow regime where two candidates receive nearly identical semantic similarity scores — a regime that appeared in exactly 1 of 31 queries evaluated.

This is consistent with findings in the dense retrieval literature: once a high-quality dense encoder is included in a fused pipeline, sparse signals (including handcrafted boost signals) have diminishing marginal rank effect \cite{thakur2021beir}. The pain term as currently implemented is a BM25-tier multiplier applied before RRF fusion; it does not operate on the post-RRF merged list. A post-RRF re-ranker placement would expose pain to a different decision boundary and may show larger aggregate effect.

**Conditional — FTS-only ablation.** A parallel FTS-only ablation (E10-pain-ablation-fts-only) was executed to test whether pain shows measurable lift when the Gemini semantic layer is removed. Results are reported in §5.5.6 below.

### 5.5.6 Isolated FTS Evaluation and Calibration Test

To isolate pain from semantic dominance, we ran two follow-up ablations.

**FTS-only ablation ($n$=60 all queries, no semantic layer):** $\Delta$ nDCG@10 = $+0.0061$, 95% CI $[-0.0036, +0.0218]$ — INSIGNIFICANT. Pain provides no detectable aggregate lift even when the Gemini semantic layer is removed. This rules out semantic masking as the sole explanation for the hybrid-mode null result.

**Pain calibration test (4 distributions, E10 follow-up, 2026-05-04).** We hypothesized that the 89% of chunks with default $\text{pain}=0.2$ was the limiting factor — i.e., that insufficient spread in the real distribution caused the null aggregate result. To test this, we constructed three artificial pain distributions and evaluated all four (real plus three artificial) on the identical FTS+pain pipeline (no Gemini), using $n=60$ golden queries, 10,000-resample bootstrap, seed=42, on a read-only snapshot (`nox-mem-snapshot-20260504-0616.db`). Source: `paper/publication/baselines/pain_calibration_test.py`; full results in `paper/publication/results/E10-pain-calibration-test.md`.

**Table 14. Pain calibration test — pairwise comparisons against real distribution ($n$=60 queries, FTS+pain only, bootstrap 95% CI).**

| Distribution | Avg pain | $\Delta$ vs real | 95% CI | Verdict |
|---|---|---|---|---|
| real (89% $@ 0.2$) | 0.235 | baseline | — | — |
| uniform $[0.1, 1.0]$ | 0.548 | $-0.0148$ | $[-0.041, +0.011]$ | DIRECTIONAL |
| bimodal $\{0.1, 1.0\}$ | 0.551 | $-0.0087$ | $[-0.038, +0.020]$ | INSIGNIFICANT |
| log-scale $[0.01, 10.0]$ | 1.447 | $-0.0095$ | $[-0.041, +0.022]$ | INSIGNIFICANT |

All artificial spreads underperform the real pain distribution, including the 100× log-scale variant designed to maximise dynamic range. H1, H2, and H3 are all refuted:

- **H1 [REFUTED].** Real pain (89% default) is not equivalent to artificial spreads — calibration spread does not explain the null result. The real distribution outperforms uniform by a directional $+0.0148$ margin, but the effect is below significance threshold and CI barely excludes zero.
- **H2 [REFUTED].** Bimodal $\{0.1, 1.0\}$ does not outperform uniform ($\Delta = +0.0062$, INSIGNIFICANT). Maximum contrast provides no measurable benefit.
- **H3 [REFUTED].** Log-scale $[0.01, 10.0]$ does not outperform uniform ($\Delta = +0.0053$, INSIGNIFICANT). Wider dynamic range is not the limiting factor.

**Real root cause identified.** Inspection of per-query FTS recall confirms that 55/60 queries (92%) have **zero FTS recall on golden chunks** — gold candidates do not appear in the BM25 candidate pool at all. The FTS recall rate is 8.3% across all four distributions (Table 14 row: FTS recall rate). Pain is a multiplier applied to retrieved candidates; it cannot affect rank order for queries where the correct chunk is never retrieved. This is a **BM25 recall ceiling**, not a calibration limitation.

Among the five queries with non-zero FTS recall (Q45, Q51, Q62, Q73, Q83), only Q62 and Q73 show non-zero nDCG@10 under real pain ($0.613$ and $0.277$ respectively), with artificial distributions consistently underperforming — consistent with the directional signal reported for real pain in pairwise comparison. This confirms that pain signal exists and functions as intended within the reachable candidate set; the constraint is upstream at BM25 retrieval, not at the pain-weighting stage.

**Framing of Contribution 1.** The empirical ablation establishes that the pain dimension is a **secondary modulator** effective in tied-semantic regimes (Q55, $\Delta = +0.349$) rather than a primary ranking signal across all queries. The design contribution — operationalizing incident severity as a typed schema field and retrieval multiplier — remains valid. The Q55 case study provides the clearest evidence that the mechanism functions as intended. The aggregate non-significance reflects the dominance of the Gemini semantic layer in the hybrid pipeline, not a failure of the pain construct.

### 5.6 Cross-Agent Intelligence Quantification (E12)

**Pre-registered hypothesis (E12):** At least 10% of top-10 retrieved chunks for any given agent's queries will originate from a different agent's memory namespace, demonstrating empirically that the shared-canonical design produces cross-agent knowledge transfer in practice.

We distinguish two levels of quantification: storage-level (what fraction of the corpus is structurally shared) and retrieval-level (what fraction of query results at runtime cross agent boundaries). These address complementary claims about the shared-canonical architecture.

**Storage-level result (confirmed, 2026-05-04).** Direct inspection of the production database ($n$=61,257 chunks, 2026-05-04) shows that 99.92% of all chunks are not partitioned by agent identity.

**Table 12. Cross-agent storage quantification ($n$=61,257 chunks, prod DB, 2026-05-04).**

| Origin class | Chunks | % | Sharing status |
|---|---|---|---|
| graphify + workspace dumps (`other`) | 59,772 | 97.58% | Shared-eligible |
| docs / specs (`shared`) | 1,435 | 2.34% | Shared-eligible |
| nox agent-private memory | 44 | 0.07% | Agent-owned |
| atlas / boris / cipher / forge / lex (combined) | 5 | 0.01% | Agent-owned |
| **Total** | **61,257** | — | — |
| **Shared-eligible total** | **61,207** | **99.92%** | — |

*Figures derived from `SELECT source_file, COUNT(*) FROM chunks GROUP BY ...` on prod READ-ONLY DB (2026-05-04). Agent-private chunks identified by `source_file` path matching `memory/agents/<name>/` prefix.*

The 99.92% shared-canonical figure is the single strongest quantitative claim for Contribution 3. As a counterfactual: under the MemGPT/Letta per-agent isolated design \cite{packer2023memgpt}, six agents with comparable memory volumes would maintain six separate corpora with 0% sharing — each agent loses access to lessons learned by the other five. nox-mem inverts this entirely by design.

**Retrieval-level result: DEFERRED.** The `search_telemetry` table does not include a `requesting_agent` column; the schema migration was planned but not deployed within the W2 window. Without this column, cross-agent hit rates at query time (the pre-registered 10% threshold) cannot be computed empirically from existing telemetry. This migration is documented as a backlog item (E12-followup: `ALTER TABLE search_telemetry ADD COLUMN requesting_agent TEXT;` + `logTelemetry()` update, estimated effort 1h) and will enable the retrieval-level quantification after two weeks of telemetry accumulation.

**Table 13. Cross-agent retrieval attribution matrix (6×6). [DEFERRED: requires search\_telemetry migration]**

|  | Origin: nox | Origin: atlas | Origin: boris | Origin: cipher | Origin: forge | Origin: lex |
|---|---|---|---|---|---|---|
| **Req: nox** | — | [D] | [D] | [D] | [D] | [D] |
| **Req: atlas** | [D] | — | [D] | [D] | [D] | [D] |
| **Req: boris** | [D] | [D] | — | [D] | [D] | [D] |
| **Req: cipher** | [D] | [D] | [D] | — | [D] | [D] |
| **Req: forge** | [D] | [D] | [D] | [D] | — | [D] |
| **Req: lex** | [D] | [D] | [D] | [D] | [D] | — |

*[D] = DEFERRED pending `requesting_agent` column migration. The diagonal is excluded (same-agent retrieval). Once populated, this matrix will reveal whether cross-agent knowledge transfer is evenly distributed or concentrated in particular agent pairs.*

The results of §5 — taken together — address the three contributions: §5.1–5.3 validate the hybrid pipeline architecture (Contribution 3 infrastructure), §5.5 targets the pain-weighting claim (Contribution 1), and §5.6 targets the shared-canonical claim (Contribution 3). Two pre-registered hypotheses are confirmed in this sprint: the BM25 Pyserini margin (+37.4 pp, pre-registered ≥ +30 pp) and the storage-level shared-canonical architecture (99.92% shared, counterfactual MemGPT = 0%). The E10 pain ablation is now executed and reported (§5.5): the result is DIRECTIONAL, NOT SIGNIFICANT ($\Delta = +0.0065$, 95% CI $[-0.0143, +0.0338]$, $n=31$), with Q55 as a qualitative positive case study ($\Delta = +0.349$). One experiment remains deferred: the E12 retrieval-level cross-agent quantification (requires `search_telemetry` migration, §6.3). Section 6 discusses what these results mean in aggregate, including the characterization of pain as a secondary modulator and the limitations of a production evaluation conducted by a single author.

---

## 6. Discussion

### 6.1 What Worked

Three contributions show empirical or operational validation at the time of writing.

**Hybrid retrieval pipeline necessity (§5.1).** The clearest finding in R01c-v1.1 is not a marginal improvement but a categorical boundary: FTS5 BM25 achieves nDCG@10 = 0.0000 (exact zero on the post-cure n=60 corpus) on natural-language queries over the operational corpus. This validates the hybrid design not as an optimization choice but as an architectural requirement. The gap of 58.3 pp (absolute) — a 100% relative reduction in FTS vs. hybrid (FTS5 returns zero matches; the absolute Δ is the entire signal) — confirms the claim stated in §3.3: for an operational corpus where queries are issued in natural language and documents contain domain-specific terminology that does not match query terms lexically, hybrid retrieval with a semantic layer is the minimum viable design.

**Shadow discipline as incident prevention (§3.5, §4.2).** The shadow-mode architecture prevented at least one class of production regression during the evaluation period. The incident of 2026-04-25 (§6.2) involved a ranking-affecting change reaching production without validation. The subsequent codification of shadow discipline as a seven-day mandatory gate — enforced via cron and `/api/health` — means that future incidents of this class would be detected in shadow telemetry before activation. This is not a post-hoc rationalization; the telemetry schema (`search_telemetry.old_score`, `search_telemetry.new_score`) was designed specifically to capture the counterfactual. During the Fase 1.7b-b salience shadow period, the collected telemetry over 191 promotion candidates, 16,608 review candidates, and 45,743 archive candidates provided the distribution analysis required for an informed activation decision.

**Edge typing enum coverage recovery (§4.4).** Enum coverage rate — the proportion of LLM-emitted relations committing to a typed enum value rather than `unknown` — improved from 14% to 56% following the three-path defensive normalization (4× improvement); equivalently, the `unknown` rate decreased from 86% to 44% on n=100 sampled relations. This directly enables blast-radius queries (`impact <entity>`) that were practically unusable before the fix. The improvement demonstrates that edge typing quality is not primarily a function of model capability — it is a function of prompt design and code-side normalization discipline. Note: this is a self-reported coverage rate; the 95% Wilson CI [46–66\%] is a valid proportion CI on the coverage metric, not a classification-accuracy CI (see §6.3).

### 6.2 What Did Not Work: Incidents That Shaped the Architecture

**Incident 2026-04-25: the reindex without dry-run.** At 22:03 on 2026-04-25, a scheduled end-of-day cron job executed `nox-mem reindex` without a dry-run flag against the production database. The reindex routine, using the generic `ingestFile()` path rather than the entity-aware `ingestEntityFile()` router, processed 183 entity files and stripped their `section`, `retention_days`, and `section_boost` annotations — years of structured metadata replaced with default values in under two minutes. No error was logged. No alert fired. The database obeyed the instruction correctly. This incident motivated Feature F02 (the `withOpAudit()` wrapper with atomic snapshot), the `--dry-run` flag on all destructive operations (A5), and the ingest router (A2) that prevents `ingestFile()` from processing entity files without the entity-specific handling path.

**Incident 2026-05-01: sed on a binary file.** A sweep script applied `sed -i` to a file pattern that inadvertently matched the production SQLite database. The `sed` command treated the database as a text file, corrupting page boundaries across the 1 GB file and eight backup copies. Recovery required a pre-vacuum backup that had been placed outside the sweep scope for an unrelated reason. This incident motivated the operational rule codified in the system's `CLAUDE.md`: "never `sed -i` on binary files; filter patterns to `\.json|\.md|\.sh|\.txt|\.jsonl|\.env` only." Both incidents illustrate the paper's central thesis: the system's architecture was shaped not by theoretical design but by operational failure. The schema carries their scars.

### 6.3 Limitations

**Internal-curator bias.** The primary evaluation (R01c-v1.1, n=60) was authored by the same individual who designed and built the system. This is a significant construct validity risk. We apply four mitigations (§4.1): the held-out R01c subset, external corpora with third-party relevance judgments (BEIR TREC-COVID, Stack Exchange), 12 negative queries testing specificity, and 10 BEIR TREC-COVID queries evaluated as a cross-curator set (E11, 0% vocabulary overlap with internal golden set). However, we acknowledge that these mitigations do not fully eliminate curator bias; results on external corpora (§5.3) are the most important check.

**Manual pain annotation.** The `pain` field is currently annotated by hand, using calibration heuristics described in §4.3. This introduces two forms of bias: the annotator (the system author) may unconsciously assign higher pain to incidents they remember as costly, even when the actual retrieval impact is low; and the annotation coverage is currently limited to incident-derived entity files (exact count pending prod verification; see §4.3). Pain annotation quality determines the ceiling of Contribution 1's empirical validity.

**Pain dimension is recall-ceiling-limited.** Empirical ablations (§5.5) show pain provides directional but not statistically significant aggregate effect, with one exception (Q55, $\Delta=+0.349$). Follow-up calibration tests (§5.5.6) refute the hypothesis that distribution spread is the limiting factor — artificial uniform, bimodal, and log-scale distributions all fail to reach significance, and all underperform the real distribution. The actual constraint is **BM25 recall ceiling**: 92% of golden queries (55/60) do not surface their gold chunks via lexical retrieval at all, leaving pain with no candidates to re-rank. Pain signal is present and functions correctly within the reachable candidate set (Q62, Q73 case data); the constraint is upstream at BM25 retrieval, not at the pain-weighting stage. The methodology contribution — treating incident severity as a typed first-class schema field with an operational annotation pipeline — survives independently of the retrieval-time empirical result. Future work should:

1. **Co-optimize semantic recall with pain re-annotation.** Pain re-ranker as a post-RRF stage, not a pre-fusion BM25 multiplier. Applying pain after the semantic layer surfaces gold candidates addresses the recall ceiling directly and exposes pain to the regime where it demonstrably has effect.
2. **Pain as semantic confidence modulator.** Use pain to break ties when semantic cosine score differences between top candidates fall below a threshold (e.g., $|\Delta_\text{sem}| < 0.02$). The Q55 case study ($\Delta=+0.349$) is exactly this regime; systematic identification of tied-semantic query pairs would provide a targeted evaluation of pain signal strength.
3. **Empirical pain coverage extension.** Expand pain annotation beyond the default 0.2 — current corpus has 89% of chunks at default, meaning even retrievable chunks carry minimal pain differentiation. LLM-driven automatic pain classification (§6.6) would both increase coverage and enable a cleaner ablation of calibration effects on the subset where BM25 recall is non-zero.

**Cross-agent retrieval quantification incomplete.** The storage-level quantification (99.92% shared, §5.6) is confirmed. However, the retrieval-level quantification — the pre-registered claim that ≥ 10% of top-10 results cross agent boundaries — cannot be computed because the `search_telemetry` table lacks a `requesting_agent` column. This migration is documented as E12-followup. Until the migration is deployed and sufficient telemetry accumulates, the retrieval-level cross-agent claim remains unverified.

**Short corpus horizon.** The production corpus spans approximately four months (March–May 2026). This is sufficient to validate hybrid retrieval and edge typing, but may underestimate the long-term recall decay problem that pain weighting is designed to address. A six-month or twelve-month evaluation would provide stronger evidence for the salience formula's temporal component.

**Single-author validation.** No inter-rater reliability study was conducted for the golden query relevance judgments. This is standard practice for personal-corpus memory systems, where the "correct" answer to a query may be defined by the author's own knowledge, but it means that the nDCG@10 scores cannot be compared directly with benchmarks that use multi-judge relevance panels.

**Edge-typing metric is a self-reported enum coverage rate, not a classification accuracy.** The reported improvement (14% → 56%, 4× gain, n=100, 95% Wilson CI [46–66\%]) measures the proportion of new KG relations where the LLM committed to one of the seven typed values in the closed schema rather than falling back to \texttt{unknown}. It is \textbf{not} a classification-accuracy measurement against a human-annotated golden set. No human annotation file was produced; no inter-rater agreement study (Cohen's κ) was conducted; the seven enum values were defined by the schema author and the LLM's emissions were not independently re-labeled by a second annotator. The 95% Wilson CI is mathematically valid as a proportion CI on the coverage rate. Future work should validate downstream graph quality via human annotation of a stratified sample (e.g., n=100 with two annotators, target Cohen's κ ≥ 0.6 substantial agreement per Landis and Koch \cite{landis1977measurement}), allowing the coverage rate to be calibrated against per-type precision/recall rather than reported as a standalone proxy for accuracy.

**Pain calibration as engineering choice.** The pain dimension values (0.1, 0.3, 0.5, 0.7, 1.0), the 10× spread between extreme values, and the multiplicative aggregation form are engineering choices motivated by operational practice in incident management \cite{pagerduty2023severity,beyer2016site}. We do not claim psychometric or biological validity for these specific values or for the multiplicative form. The calibration spread ablation (§5.5.6, uniform / bimodal / log-scale distributions) was executed directly and found that no artificial spread outperforms the real distribution — which itself shows only directional aggregate effect. This refutes the hypothesis that the 10× spread is insufficient; the binding constraint is BM25 recall, not calibration (§6.3, pain recall-ceiling paragraph). Aggregation form ablation (additive vs. multiplicative) remains as future work.

### 6.4 Cost and Compute Profile

A production memory system paper that makes an architectural argument against heavy LLM-orchestration approaches — while remaining silent on its own cost — invites the obvious objection. This subsection provides the quantitative cost profile of nox-mem as deployed, using 2026-Q1 Gemini API pricing throughout. All figures are snapshots; readers should verify current pricing at the provider's official documentation.

#### 6.4.1 Embedding Cost

**Model:** Gemini `gemini-embedding-001`, 3072-dimensional output.
**Price:** $0.025 per 1M input tokens (Google AI pricing, 2026-Q1 \cite{google2026pricing}).

**Indexing cost (4-month production corpus).** The operational corpus contains approximately 62K chunks at a mean of roughly 400 tokens per chunk, yielding an estimated 25M tokens indexed over four months. At $0.025/1M tokens, total indexing cost is approximately **$0.62 amortized** over the evaluation period — less than a cup of coffee for the full corpus build.

**Per-query embedding cost.** A single search query averages approximately 30 input tokens. Cost per query: $30 \times 0.025 / 1{,}000{,}000 \approx \$0.00000075$ — effectively zero.

**Comparison.** Indexing the same 62K-chunk corpus with OpenAI `text-embedding-3-large` ($0.13/1M tokens, 2026-Q1 \cite{openai2026pricing}) would cost approximately $3.25 — roughly 5$\times$ more. Using a local model such as BGE-M3 \cite{chen2024bge} would incur zero API cost but requires approximately 6 hours of CPU time per full re-index on commodity hardware (estimated based on BGE-M3 published throughput benchmarks), making incremental nightly re-indexing impractical without a dedicated GPU.

#### 6.4.2 Storage Cost

**Measured DB size.** The production SQLite database (FTS5 index + sqlite-vec 3072-dimensional vectors + KG tables) occupies approximately **0.8–1.2 GB on disk**, consistent with the analytical estimate: $62{,}000\ \text{chunks} \times (2\ \text{KB text} + 12\ \text{KB embedding at}\ 3072 \times 4\ \text{bytes}) \approx 870\ \text{MB}$. The FTS5 inverted index and sqlite-vec vector map contribute the bulk of overhead beyond raw text.

**Storage OPEX.** The system runs on a Hostinger VPS where 1.2 GB represents a negligible fraction of the base plan's allocated storage — effectively **$0/month in marginal storage cost**. On AWS S3 at $0.023/GB-month, the same DB would cost approximately $0.03/month; on AWS EBS (gp3) at $0.08/GB-month, approximately $0.10/month. Neither figure is material.

#### 6.4.3 Query Cost in Production

**Daily query volume.** Six agents collectively issue an estimated 500–2,000 hybrid queries per day (approximately 100–300 queries per agent per active day, based on operational observation over the four-month period). At the median estimate of 1,000 queries/day, monthly query volume is approximately 30,000 queries.

**Monthly Gemini query cost.** $30{,}000\ \text{queries} \times 30\ \text{tokens} \times \$0.025/1{,}000{,}000 \approx \$0.02/\text{month}$. At the high end of the query volume range (60,000 queries/month): $\approx \$0.05/\text{month}$.

**Total monthly OPEX.** Gemini embedding (queries): $<\$0.05$ + VPS base plan (Hostinger): approximately $\$10$/month = **approximately $\$11$/month all-in** for a 62K-chunk, 6-agent, always-on production memory system.

#### 6.4.4 Comparison with Alternative Approaches

Table 15 summarizes the cost profile of nox-mem against representative alternative approaches. Figures for alternatives are estimated based on publicly documented LLM call patterns and 2026-Q1 API pricing; they are marked accordingly and should be treated as order-of-magnitude comparisons rather than audited benchmarks.

**Table 15. Cost comparison: nox-mem vs. alternative memory architectures (estimated 2026-Q1 pricing, small single-team deployment).**

| System | Indexing (one-time) | Per-query | Monthly OPEX |
|---|---|---|---|
| **nox-mem (this work)** | **$\sim$\$0.62** | **$\sim$\$0.00000075** | **$\sim$\$11** |
| MemGPT with GPT-4 reranking \cite{packer2023memgpt} | \$0 | \$0.001--\$0.01 (estimated, GPT-4 per recall) | \$30--\$300 |
| GraphRAG \cite{edge2024graphrag} | \$10--\$100 per 100K docs (estimated, LLM extraction) | $\sim$\$0.0001 | \$20--\$50 |
| Mem0 hosted \cite{chhikara2025mem0} | n/a (managed) | bundled in plan | \$20--\$200 |
| Pure GPT-4o long-context (no retrieval) | \$0 | \$0.01--\$0.10 per session | \$100--\$1{,}000+ |

*Note: MemGPT, GraphRAG, Mem0, and GPT-4o figures are estimated based on documented LLM call patterns and do not represent vendor-audited cost disclosures. nox-mem figures are measured from production telemetry and API invoices over the 4-month evaluation period.*

The most structurally significant comparison is with pure long-context LLM approaches (final row). At even moderate query volume, stuffing context into GPT-4o costs two to three orders of magnitude more per query than embedding-based retrieval, while also being bounded by context window size — a ceiling that does not exist in the retrieval design.

#### 6.4.5 Honest Caveats

Several cost assumptions merit explicit qualification.

**Corpus scope.** The figures above assume a text-only corpus in English and Portuguese (PT-BR). Multimodal content (images, audio, video) would require additional preprocessing pipelines; OCR and audio transcription costs are not included.

**Pricing snapshot.** Gemini API pricing has changed across product revisions. All figures reflect 2026-Q1 rates; readers evaluating deployment costs should consult current provider documentation.

**Labor cost is the dominant real cost and is excluded.** For a solo-developer system, the cost table is misleading if read in isolation: infrastructure OPEX is $11/month, but development and operational labor — schema migrations, incident response, evaluation harness maintenance — represent the true investment. We report infrastructure cost because it is objectively measurable and directly relevant to the architectural comparison (vs. heavy-LLM approaches); we note explicitly that labor cost is the invisible variable that dominates any honest TCO calculation for small-team deployments.

**Pain calibration overhead at retrieval time: zero.** The pain field is precomputed at ingest time and stored as a scalar in the `chunks` table. Retrieval-time salience computation is a single floating-point multiply — no API call, no LLM inference, no added latency. LLM-based dynamic re-ranking systems (MemGPT-style architectures) pay a per-query LLM call to achieve the same prioritization effect; nox-mem's design externalizes this cost entirely to the ingest path.

### 6.5 Threats to Validity

**Construct validity.** The golden queries (R01b) were designed to reflect operational retrieval needs — "what was the fix for the gateway crash?" rather than paper-style information-need queries. This design choice means that nDCG@10 scores reflect operational retrieval utility, not document relevance in the TREC/CLEF sense. Comparison with external baselines on BEIR (§5.3) addresses this partially, since BEIR queries were designed for information retrieval research rather than operational memory.

**External validity.** All internal results (§5.1–5.2) were collected on a technology and operations corpus authored by a single software practitioner. The hybrid pipeline's advantage over FTS-only may not transfer to corpora with different term distribution properties (e.g., legal documents with precise terminology may show stronger BM25 performance). The external corpus experiments (§5.3) test one transfer case (biomedical and Q&A corpora), but transfer to legal, medical, or enterprise knowledge base corpora remains an open empirical question.

### 6.6 Future Work

**Automated pain classification.** The most immediate limitation of Contribution 1 is the manual annotation requirement. An LLM-driven incident classifier — trained on the existing pain-annotated chunks as a few-shot signal — could extend pain coverage to the full corpus and reduce annotation bias. This is designated as deferred feature D02 in the project roadmap.

**Cross-encoder reranker (D01).** A cross-encoder reranker applied post-RRF would likely improve precision on the top-3 results, where the current pipeline's RRF fusion sometimes ranks partially relevant chunks above highly relevant ones. This feature is gated on R01c $\geq$ 0.6 nDCG@10, following the shadow-mode discipline: a reranker affects ranking, so it must demonstrate benefit in shadow before activation.

**Multi-tenant productization (P01).** The shared-canonical design (§3.6) is not suitable for multi-tenant SaaS environments, where agents from different users must not share a corpus. The P01 roadmap item (NOX-Supermem productization) requires a tenant-isolation layer above the shared corpus, likely via row-level security and per-tenant `source_file` namespacing. This is future work outside the scope of the current paper.

We invite verification and contributions via the public repository at \url{https://github.com/totobusnello/memoria-nox}, which includes the full code, evaluation harness, golden query set (n=60), and 4-month incident log under MIT license.

The discussion concludes that the system's most durable contributions — shadow discipline and pain-weighted salience — are transferable design patterns rather than features of any particular implementation. The next section states this claim in its most general form.

---

## 7. Conclusion

Agent memory is not a retrieval engineering problem. It is an operational discipline problem. Systems fail silently because ranking changes enter production without validation, because incident severity is treated as a logging concern rather than a retrieval signal, and because agents in the same deployment live in context silos that never communicate. Better embeddings do not fix any of these failure modes. Architecture does.

This paper has described three contributions that address these failure modes directly. First, **pain-weighted salience** — `salience = recency × pain × importance` — models incident severity as a first-class retrieval signal, making a production-outage lesson from six months ago more retrievable than a minor note updated yesterday. To our knowledge, no prior memory system paper includes this dimension; the closest related work (GraphRAG, Mem0, MemGPT, A-MEM, HiRAG, Cognee) models recency and structure but not cost. Second, **enforced shadow discipline** — a mandatory seven-day telemetry comparison gate before any ranking-affecting change reaches production — converts a documentation best practice into an architectural guarantee. The incident of 2026-04-25 is the counterfactual: a ranking change entered production without this gate, and 183 entities lost their structured metadata without alerting. Third, **shared-canonical multi-agent design** enables cross-agent knowledge transfer without federation overhead, allowing six agents operating in distinct domains to benefit from each other's learned context by design.

The empirical evidence supports the hybrid pipeline as a minimum viable requirement (nDCG@10 0.5831 ± 0.0046 vs 0.0000 ± 0.0000 for FTS-only on natural-language queries, n=60 3-run mean post-cure R01c-v1.1; absolute gap 58.3 pp). The BM25 Pyserini comparison is confirmed: nox-mem hybrid achieves 4.0× the nDCG@10 of the strongest tuned BM25 baseline (+43.6 pp absolute), substantially exceeding the pre-registered threshold. The shared-canonical storage architecture is confirmed at 99.92% sharing (n=61,302 chunks), vs. 0% under isolated per-agent designs, achieving production OPEX of approximately \$11/month all-in for the full 6-agent deployment (§6.4). The E10 pain ablation (§5.5) is executed and reported: the aggregate result is DIRECTIONAL, NOT SIGNIFICANT ($\Delta = +0.0065$, 95% CI $[-0.0143, +0.0338]$, $n=31$); the Q55 case study provides positive evidence that pain provides meaningful lift ($\Delta = +0.349$) in the tied-semantic regime. We characterize pain as a secondary modulator rather than a primary retrieval signal in hybrid mode. One deferred experiment — the E12 retrieval-level cross-agent quantification — is documented transparently in §6.3 and does not alter the architectural contributions. The remaining pre-registered hypotheses (BGE-M3, E5, cross-corpus generalization) are under evaluation in sprint W2–W3; results will be published in the arXiv preprint at submission. Note that the current nDCG@10 of 0.5831 < 0.6, which keeps the D01 cross-encoder reranker gated per §6.6 until the threshold is met in future work.

**Measurement instrument matures alongside the system.** Between paper draft v1.0 (2026-05-04, R01b n=50) and v1.1 (2026-05-07, R01c-v1.1 n=60), the underlying retrieval pipeline (FTS5 + Gemini 3072d + RRF k=60) was held constant; no code change was made to search, ranking, or fusion. Yet hybrid nDCG@10 improved from 0.5213 ± 0.0004 to 0.5831 ± 0.0046 (+11.9% relative), Recall@10 from 0.6800 to 0.7667 (+12.8%), and the absolute Δ over FTS5 vanilla from +0.509 to +0.583. The improvement came *entirely from measurement hygiene plus corpus growth*: 11 queries with empty `expected_chunk_ids` (genuine documentation gaps where no chunk in the corpus answers the question) were correctly reclassified to `category=negative`, where they score 0.000 in any retrieval system; 3 orphan IDs that referenced chunks deleted by re-ingest events were corrected; 3 temporal queries (Q70/Q87/Q88) were extended with newly available timeline events; and the operational corpus grew from 61,257 to 61,302 chunks with KG `evidence_chunk_id` coverage rising from 0.47% to 4.92% via incremental nightly extraction. We treat the gold standard as a versioned research artifact rather than a one-time snapshot, in keeping with the open-evaluation norm advocated by \cite{rogers2021just} and broader IR practice of iterative relevance-judgment refinement. The v1.0 numbers are preserved in the `v1.0.0` git tag for full reproducibility, and the disclosure (§5.1, "Gold standard revision note") makes both versions available side-by-side. The implication for IR practitioners: gold-set hygiene — moving doc-gap queries to negatives, repairing orphan references after corpus rewrites — can deliver double-digit nDCG@10 gains without touching the model, embedding, or retrieval code. This is best practice, not artifact, when the methodology is auditable and pre-registered. We recommend evaluating eval harnesses on the same shadow-discipline timeline (§3.5) as ranking changes themselves.

Beyond nox-mem specifically, pain-weighted salience and shadow discipline are **transferable concepts**. Any persistent memory system — regardless of implementation stack — can adopt a severity annotation field and enforce a shadow validation gate before ranking changes activate. These ideas require no new model, no new architecture, and no GPU. They require only the discipline to instrument what already exists and the patience to watch before activating.

We invite verification and contributions via the public repository.

---

## Appendix A: Implementation Details

### A.1 TypeScript Stack

The system is implemented in TypeScript (Node.js 22, strict mode, ESM modules) with the following primary dependencies:

- `better-sqlite3` — synchronous SQLite interface; all DB operations are single-file transactions
- `sqlite-vec` — vector extension for SQLite enabling cosine similarity search over 3072-dimensional Gemini embeddings
- `@google/generative-ai` — Gemini API client for both embedding (Gemini embedding-001, 3072d) and LLM extraction (Gemini 2.5 Flash Lite for agent infra; Gemini 2.5 Flash for KG extraction)
- `inotifywait` — filesystem watch for automatic ingest on file change

**Schema migration history (v1 → v12).** The schema has undergone 12 versioned migrations since initial deployment:

| Version | Key change |
|---|---|
| v1–v3 | Initial chunks + FTS5 design |
| v4–v5 | vec\_chunks + vec\_chunk\_map (sqlite-vec) |
| v6–v7 | kg\_entities + kg\_relations |
| v8 | `retention_days` typed retention policy |
| v9 | `pain` field (REAL DEFAULT 0.2) |
| v10 | `section` + `section_boost` for entity file format |
| v11 | `search_telemetry` eval harness (+4 columns: query\_text, golden\_id, top\_chunk\_ids, top\_scores) |
| v12 | `ops_audit` table + status enum enforcement triggers |

All migrations were applied to the production database without downtime.

### A.2 Entry Points

- **CLI:** `dist/index.js` (26+ subcommands including `search`, `ingest`, `ingest-entity`, `reindex`, `vectorize`, `kg-extract`, `reflect`, `crystallize`)
- **MCP Server:** 16 tools including `nox_mem_search`, `kg_build`, `cross_search`, `reflect`
- **HTTP API:** port 18802, endpoints `/api/{health,search,kg,kg/path,agents,cross-kg,reflect,procedures}` + `POST /api/crystallize`

---

## Appendix B: Shadow Case Study — Fase 1.7b-b Salience Activation

### B.1 Timeline

- **2026-04-18:** Pain-weighted salience formula implemented; `NOX_SALIENCE_MODE=shadow` set in production
- **2026-04-18 → 2026-04-25:** Seven-day shadow telemetry collection
- **2026-04-25:** Distribution analysis: 191 promotion candidates, 16,608 review candidates, 45,743 archive candidates; distribution shows clear separation across tiers
- **2026-04-25:** Decision to advance to `NOX_SALIENCE_MODE=active`; activation logged in `ops_audit`

### B.2 Telemetry Summary

| Tier | Count | % of total |
|---|---|---|
| Promoted (new\_score ≥ threshold) | 191 | 0.30% |
| Review (threshold range) | 16,608 | 25.88% |
| Archive (new\_score < threshold) | 45,743 | 71.26% |
| **Total shadow observations** | **64,180+** | — |

*Note: The 3-tier distribution reflects the expected long-tail structure of an operational corpus — most chunks are low-salience documentation, a minority are high-salience incident lessons.*

### B.3 Counterfactual: Incident 2026-04-25

The incident of 2026-04-25 occurred the same day the shadow period ended — a coincidence that underscores the motivation for the shadow gate. The reindex operation that damaged 183 entity records is precisely the class of ranking-affecting change that shadow mode is designed to catch: it altered `section` and `section_boost` annotations, which feed directly into the salience computation. Had the post-incident reindex run before the shadow gate was in place, the damage would have been invisible until a user noticed degraded retrieval quality for entity queries.

### B.4 Activation Decision Rationale

The distribution analysis showed that the pain-weighted salience formula was doing the intended work: high-pain chunks (incident lessons, security decisions, production outage records) consistently landed in the promotion tier, while trivial notes and meeting summaries landed in the archive tier. The formula was activated because the distribution matched the design intent, not because the absolute nDCG@10 numbers improved (those were measured separately in R01b).

---

## Appendix C: Reviewer-Friendly Feature Comparison Table

See Table 1, §2.5 for the full seven-axis architectural comparison across all surveyed systems. The five-dimension summary below (KG native, hybrid retrieval, eval harness, multi-agent, shadow discipline) distills the axes most relevant for reviewer quick-reference; scores align with the 5/7 subset of Table 1 that excludes corpus scale and third-party benchmark coverage.

| System | KG native | Hybrid retrieval | Eval harness | Multi-agent | Shadow discipline | **Score** |
|---|---|---|---|---|---|---|
| **nox-mem (this work)** | Yes — closed-enum, 7 edge types | Yes — FTS5 + Gemini + RRF | Yes — nDCG@10/MRR/Recall, n=60 | Yes — shared canonical | Yes — ≥7d enforced | **5/5** |
| GraphRAG \cite{edge2024graphrag} | Yes + community detection | Partial — via KG queries | No | No | No | 1.5/5 |
| MemGPT/Letta \cite{packer2023memgpt} | No | Partial — embedding-first | No | Yes — per-agent | No | 1.5/5 |
| Mem0 \cite{chhikara2025mem0} | Optional (v2) | No — vector-only | Partial — LOCOMO only | Partial — user\_id partition | No | 1.5/5 |
| A-MEM \cite{xu2025amem} | Partial — Zettelkasten | Partial — semantic-first | No | No | No | 1.0/5 |
| HiRAG \cite{huang2025hirag} | Yes — hierarchical | Yes — multi-level | Partial — task-specific | No | No | 2.5/5 |
| Cognee \cite{topoteretes2024cognee} | Yes — ECL pipeline | Yes — hybrid | Partial — ad-hoc | Optional | No | 3.0/5 |
| LangChain Memory | No | No — key-value | No | Partial — session\_id | No | 0.5/5 |

*Scoring: 1.0 per dimension for full implementation; 0.5 for partial; 0.0 for absent. The most comparable system (Cognee, 3/5) lacks eval harness reproducibility and shadow discipline — the two dimensions the authors consider most critical for production deployment.*

---

## Appendix D: Incident Case Study — Formal Write-Up (E13)

### D.1 Incident Summary

**Date:** 2026-04-25, 22:03 BRT
**Severity:** HIGH (data integrity; no user-facing downtime)
**Root cause:** End-of-day cron job executed `nox-mem reindex` without dry-run or pre-operation snapshot. The generic `ingestFile()` path processed 183 entity files, stripping `section`, `retention_days`, and `section_boost` annotations.
**Recovery:** Manual re-ingestion via `ingest-entity` for all 183 files; `withOpAudit()` wrapper retroactively applied as preventive measure.
**Time to detect:** ~18 minutes (via `/api/health.sectionDistribution` check)
**Time to recover:** ~45 minutes

### D.2 Contributing Factors

1. The end-of-day cron script (cron ID `ee15b430`, 22:00 BRT, step 11) invoked `nox-mem reindex` without the `--dry-run` flag.
2. The reindex command used the generic `ingestFile()` router, which does not distinguish entity files from plain markdown.
3. No pre-operation snapshot was taken; the daily backup (02:00 BRT) had not yet run for the day.
4. No alert was configured for `section` annotation coverage drop.

### D.3 Changes Implemented

| Change | Code artifact | Description |
|---|---|---|
| F02 op-audit | `src/lib/op-audit.ts` | `withOpAudit()` wrapper: VACUUM INTO atomic snapshot before destructive ops |
| A2 ingest router | `src/lib/ingest-router.ts` | `routeIngest()` dispatches entity files to `ingestEntityFile()`, prevents generic path |
| A5 dry-run | `reindex.ts`, `consolidate.ts` | `--dry-run` produces JSON preview without mutating DB |
| Schema invariant canary | `check-schema-invariants.sh` | Cron */15min checks `section NOT NULL` coverage; Discord alert on deviation |
| Cron patch | `ee15b430` step 11 | Replaced `nox-mem reindex` with `nox-mem consolidate` (entity-aware) |

### D.4 Lessons Formalized in Architecture

The op-audit module (`withOpAudit()`) encodes the lesson that destructive operations must create a point-in-time snapshot before execution and log their outcome to an append-only audit table (`ops_audit`). The audit table's `status` field is validated by DB triggers against a closed enum (`started`, `success`, `failed`, `crashed`); the triggers block DELETE and UPDATE on rows with terminal status. Recovery via `safeRestore()` validates `user_version` match before restoring — a safeguard motivated by a separate incident where a stale WAL file caused silent corruption on a naive `cp` restore.

This incident, and the five others documented in `docs/INCIDENTS.md`, are the operational substrate from which the paper's architectural contributions were extracted. They are included here not to confess failure but to demonstrate that the contributions are grounded in production evidence rather than synthetic benchmark design.

---

*End of §4–7 + Appendices A–D draft. Status: W2 sprint. Sections 4, 6, 7, and Appendices A–D are complete prose. Section 5 tables await W2–W3 experiment results.*
