# Review of `paper/paper-tecnico-nox-mem.md` v1.0.3: verification of the Kimi and Codex findings

Sprint 2026-10-04. Target: `paper/paper-tecnico-nox-mem.md` (1 495 lines, uncommitted v1.0.3
working tree). The v1.0.2 copy used for "was it already there" checks is in the session scratchpad,
`scratchpad/v102/`. Every quote below was located with `grep` (line numbers are v1.0.3's) and
checked against the text and against the artifact or paper it cites:
`eval/evermembench/RESULTS-*.json|md`, `eval/q4-comparison/output/rc4/_aggregate.{json,md}`,
`staged/P1/edits/src/lib/answer/config.ts`, and the EverMemBench paper arXiv:2602.01313 v1/v2/v3
(`scratchpad/evmb3/`). Numbers that the manuscript does not contain were recomputed in this pass.
Nothing in the manuscript, the supplement or `abstract.md` was edited.

## 1. Which voices count

| voice | exit | status | receipt |
|---|---|---|---|
| Kimi k3 | 0 | **valid** | `.remember/adversary-receipt-kimi-2026-10-04T000358-8847.txt`, 950 s, `output_bytes 131 595` |
| Codex gpt-6-astra | 0 | **valid** | `.remember/adversary-receipt-codex-2026-10-04T000331-8384.txt`, 590 s, `output_bytes 580 772` |

Both voices are valid. Kimi raised 8 items (2 medium, 1 low, 4 pre-existing lows, 1 caveat). Codex
raised 17 (3 high, 8 medium, 4 low, 2 "evidence limits"). After merging 2 duplicates
(IterB CI; arXiv version), **16 confirmed** and **7 rejected**.

## 2. Confirmed

### High

**H1. The IterB CI is not IterB's, and the significance verdict contradicts the paper's own rule.**
(Kimi M1 + Codex 2.)
- Quote, l.789: "IterB ReAct lifts F_MH **+2.01 pp** on Gemini-3-flash (95% CI [1.06, 9.39], overlapping baseline — directional, not significant)". The same verdict also appears at l.475, l.476 and l.489.
- Verified: `[1.06, 9.39]` is the CI of **AC threshold=5 on gpt-4.1-mini**. The supplement states this at l.99 ("AC (threshold=5) | +2.01 pp (CI [1.06, 9.39])") and l.262/266. Both lifts happen to be +2.01 pp. IterB's artifact `RESULTS-Q3-ITERB-POC-GEMINI.json` stores no CI. Its per-batch F_MH is [8.0, 6.0, 10.0, 8.0, 8.16]: mean 8.032, sample SD 1.416. The t-interval, the method §5.8.1 declares, is **[6.27, 9.79]**. Its lower bound exceeds the Gemini-3-flash baseline mean of 6.02, so under §5.8.1's own "claim threshold" (l.904) IterB would count as a claimable win.
- Recomputed tests against the bare Gemini-3-flash baseline (`RESULTS-BACKBONE-MATRIX.json`, per batch [4, 6, 8, 6, 6.12]):
  - Paired t by batch: mean diff 2.01, t = 3.17, df 4 (p ≈ 0.03), CI [0.25, 3.76].
  - Welch t: t = 2.24, df 8 (p ≈ 0.055).
  - Question level: **20 vs 15 correct of 249**, which is clearly not significant.
- Conclusion: "directional" can stand on the question-level count, but the interval cited is wrong, and the verdict conflicts with §5.8.1's rule.
- Fix: in §5.5.2, replace the CI with IterB's own (t-CI [6.27, 9.79], or the paired difference CI [0.25, 3.76]) and name the test that supports "not significant": question level, 20/249 vs 15/249. In §5.8.1, either say that the CI-lower-bound-vs-baseline-mean rule ignores baseline variance, or apply it consistently. Kimi's reading that this "would be a claimable win" holds only under that rule.

**H2. "Like-for-like" is not true: the question population differs from Table 4's.** (Codex 1.)
- Quote, l.645: "The row "Table 4's aggregation" averages the nine sub-dimensions Table 4 reports, from the same counts, and is the like-for-like figure." Related, l.951: "only validated that the 5-batch sampling preserves the per-category distribution of the published numbers".
- Verified: the EverMemBench v3 paper reports **2,400** QA pairs after filtering (l.1533–1536 and l.1661–1662 of the text extract). The local nine categories in `RESULTS-BACKBONE-MATRIX.json` sum to **2,733**.

  | category | v3 paper | local |
  |---|---:|---:|
  | Single-hop | 213 | 247 |
  | Multi-hop | 249 | 249 |
  | Temporal | 300 | 300 |
  | Constraint | 402 | 500 |
  | Proactivity | 427 | 500 |
  | Update | 268 | 287 |
  | Style | 176 | 181 |
  | Skill | 169 | 221 |
  | Role / Title | 196 | 248 |

  The aggregation formula matches; the questions do not. Shares differ as well: Constraint is 16.75% of the paper's set and 18.29% of ours, so the l.951 "preserves the distribution" claim is overstated.
- Fix: replace "is the like-for-like figure" with "uses Table 4's aggregation formula". Disclose that the five released batches hold 2,733 questions in the nine categories, against 2,400 in the paper's filtered set, with different per-category counts. Soften l.951 to match.

### Medium

**M1. The Wave C CI was computed with a z interval and population SD, not the declared t interval.** (Codex 3.)
- Quote, l.621: "(95% CI of the mean [2.20, 12.27], `eval/evermembench/RESULTS-WAVE-C-TRIPLE.json`)". Also l.627: "confidence intervals 6–10 pp wide".
- Verified: `aggregate_phaseTriple_5batch.py` l.144–145 uses `statistics.pstdev` × 1.96 / √n. The artifact's 5.7459 is the population SD; the sample SD is 6.42. With §5.8.1's t interval, [4, 2, 4, 18, 8.16] gives **[−0.74, 15.21]**, which is 16 pp wide. The KG+MAP artifact uses the same z method: [4.34, 10.16] becomes [2.64, 11.86] under t. KG+MQ uses t ([4.12, 11.93]).
- Fix: recompute the Wave C and KG+MAP intervals with t, or state the method actually used. Update "6–10 pp wide" to match. The qualitative claim, that the triple is indistinguishable from KG+MAP, is unaffected.

**M2. The abstract attributes F_MH "principally to task setup"; §5.4 says that attribution is not established.** (Codex.)
- Quotes:
  - l.18: "which §5.4 attributes principally to task setup".
  - l.489: "attributed principally to the task setup".
  - l.945: "attributing it principally to the task setup".
  - Against these, §5.4 l.759: "we present them as the leading account rather than an established attribution — nothing below separates a corpus effect from a system limitation".
- Verified: the benchmark's own oracle results (v3 §4.2, Table 5) show GPT-4.1-mini rising from 2.41% to 97.99% on F_MH, and Gemini-3-Flash from 26.51% to 88.37%, once ground-truth evidence is supplied. That points to evidence retrieval and attribution, the memory system's job. It does not point to the scoring rule.
- Fix: in the abstract, l.489 and l.945, use §5.4's hedge ("which §5.4 discusses; the leading account is task setup, not an established attribution"), and cite the oracle result in §5.4.

**M3. The rc4 rows say "not captured" for latency, R@10 and MRR, but the rc4 artifact has all three.** (Codex, under "evidence limits".)
- Quotes: l.1075/1098: "| — | — | not captured in rc4 (standalone: …)"; l.1076/1100: "| — | — | not captured".
- Verified: `eval/q4-comparison/output/rc4/_aggregate.md` (headline table) and `_aggregate.json` have:

  | system | p50 | p95 | p99 | R@10 | MRR |
  |---|---:|---:|---:|---:|---:|
  | nox-mem | 515.6 ms | 619.8 ms | 683.1 ms | 0.6656 | 0.4749 |
  | Mem0 | 349.8 ms | 410.0 ms | 519.2 ms | 0.5852 | 0.4092 |

  The accurate statement is l.1285's: captured, but not under a normalized transport.
- Fix: fill in R@10 and MRR. Report latency as "515.6 / 349.8 ms p50, not transport-normalized; not a speed claim", or write "captured, not normalized", instead of "not captured".

**M4. HyperMem's 92.73% is a LoCoMo number, not LongMemEval.** (Codex.)
- Quote, l.1308: "and 92.73% on LongMemEval for HyperMem".
- Verified: the abstract of arXiv:2604.08256 reads "Experiments on the LoCoMo benchmark show that HyperMem achieves … 92.73% LLM-as-a-judge accuracy".
- Fix: "92.73% on LoCoMo (LLM-judged) for HyperMem".

**M5. gbrain's 97.6% is R@5, and its source has since revised it.** (Codex.)
- Quote, l.850: "Comparison to gbrain (97.6% nDCG@10 on LongMemEval-S)".
- Verified: `garrytan/gbrain-evals` `docs/benchmarks/2026-05-07-longmemeval-s.md` reports 97.60% **R@5**, then an "August 31: correcting the May score" section: official `recall_all@5` 83.40%, `recall_any@5` 97.66%, nDCG_any@5 90.58%.
- Fix: cite it as R@5, give the corrected figure (83.40% recall_all@5, 2026-08-31), and drop "nDCG@10".

**M6. An "empirical upper bound" is given for a composition that was never tested.** (Codex.)
- Quote, l.939: "The corrected empirical upper bound for measured+plausible IterB composability on Gemini-3-flash is ~8–9% F_MH (see §5.5.4 corrected table)."
- Verified: the very next bullet (l.940) and §5.5.8 say the IterB + Wave C test is INDETERMINATE, "an untested hypothesis". "Measured+plausible" is not empirical. The main-text §5.5.4 (l.795–797) also contains no "corrected table"; it points to the supplement.
- Fix: "a projection of ~8–9% F_MH, untested (§5.5.8); table in supplement §S5.5.4".

**M7. The KG+MQ overlap is argued from a near-tautological co-fire rate.** (Codex.)
- Quote, l.608: "overlap at a **90.8% co-fire rate** on EverMemBench queries — both activate on the same query population (entity-bearing multi-hop queries)". Repeated at l.625.
- Verified: `RESULTS-WAVE-B-KG-MQ.md` l.76 shows MQ firing on 99.3% of **all** 3,121 queries, KG on 91.4%, and both on 90.8%. The co-fire rate is essentially KG's firing rate. The population is every query type, not "entity-bearing multi-hop queries". Co-firing also does not show that the two knobs act on the same evidence. KG+MAP, which works at different stages, is also sub-additive (point 2).
- Fix: "MQ fires on 99% of queries, so it co-fires with KG wherever KG fires (90.8%)". Drop the "same population (entity-bearing multi-hop)" gloss, and present overlap as a hypothesis.

**M8. The EverMemBench citation is not pinned to v3, and the footnote title is wrong.** (Kimi caveat + Codex.)
- Quotes: l.1477: "Hu et al., *Evaluating Long-Horizon Memory for Multi-Party Collaborative Agents* (the EverMemBench paper), 2026. arXiv:2602.01313." Also l.951 "(arxiv:2602.01313)". `refs.bib` l.374 and l.668 are unversioned.
- Verified:
  - v1 and v2 are titled "EverMemBench: Benchmarking Long-Term Interactive Memory in Large Language Models". They contain 41.59 and none of 42.55, 59.27 or 18.88.
  - v3 (11 Mar 2026) holds all the numbers the paper cites.
  - Only the supplement erratum names v3.
  - Found in this pass, not by either voice: the footnote's title ends in "Collaborative **Agents**", while v3 and `refs.bib` both say "Collaborative **Dialogues**".
- Fix: cite "arXiv:2602.01313v3" in the footnote, at l.951 and in both bib entries, and correct the title to "…Collaborative Dialogues".

### Low

**L1. "Best published system" needs the "memory-augmented" qualifier.** (Kimi M2.)
- Quotes: l.18: "against 18.88% for the best published system on that track (both LLM-judged)". Also l.489, l.757, l.945, and `abstract.md`.
- Verified:
  - v3 §4.2 says "the best memory-augmented system reaches only 18.88%".
  - The same Table 4 lists Full Context on Gemini-3-Flash at 26.51% F_MH.
  - Further nuance: 18.88% is the GPT-4.1-mini column. The Gemini-3-flash run that the abstract calls "the same EverMemBench run" (nox-mem F_MH 6.02%) has MemOS at 10.84% in its own column.
- Fix: "the best published memory-augmented system (MemOS, 18.88%, GPT-4.1-mini column)". Mention the full-context 26.51% once in §5.4.

**L2. `abstract.md` says 99.85% "of the ablated gain"; the paper says 99.86% "of the full-stack score".** (Kimi L1.)
- Quote, `abstract.md` l.20: "(99.85% of the ablated gain)".
- Verified: 0.6228 / 0.6237 = 99.856%, which rounds to 99.86%. Also, the share of the *gain* over G3 is (0.6228 − 0.3488) / (0.6237 − 0.3488) = **99.67%**, so "of the ablated gain" mislabels the ratio.
- Fix: "(A3 alone reaches 99.86% of the full-stack nDCG@10)".

**L3. MAP standalone is reported as "~7.23%"; the artifact says 7.22%.** (Kimi, pre-existing.)
- Quote, l.616: "| Phase MAP standalone | ~7.23% | +4.02 pp |".
- Verified: `RESULTS-PHASEMAP-5BATCH.json` gives F_MH mean 7.22, and the `.md` l.40 gives "7.22% … +4.02". 7.23 is the Wave C triple's value (l.621). The +4.02 is correct.
- Fix: "7.22%".

**L4. The headline transfer range omits KG's 0%.** (Codex.)
- Quotes: l.476: "transfer at only **~24–40% efficiency**"; l.950: "The ~30–40% transfer rate pattern of §5.5.5".
- Verified: the §5.5.5 table reads KG 0%, AC 40%, MQ 34%, aggregate 24%. Elsewhere the paper says "0–40%" (l.647, l.938).
- Fix: "0–40% (24% in aggregate)" in both places.

**L5. The `answer` primitive's topK is 10 in the paper but 8 in the cited code.** (Codex.)
- Quote, l.318: "Internally calls `search` with `topK = 10`". `docs/PRIMITIVES.md` l.96 has the same.
- Verified: the implementation the paper cites, `staged/P1/edits/src/lib/answer/config.ts` l.18, sets `DEFAULT_TOPK = 8`. `retrieval.ts` overfetches `topK*2` and caps at topK. `NOX_ANSWER_TOPK` overrides it, clamped to 1..20.
- Fix: "`topK = 8` by default (`NOX_ANSWER_TOPK`, 1–20)".

**L6. The single-hop explanation is an unmeasured mechanism.** (Codex.)
- Quote, l.1148: "the narrowest is **single-hop** (+0.006), where a single strong dense match suffices and the hybrid adds little."
- Verified: no measurement supports it, and both systems score only ~0.39 nDCG@10 on single-hop (rc4 0.3969; generic-task 0.3924 vs 0.3908). That does not look like "a single strong match suffices". The preceding clause is hedged; this one is not.
- Fix: hedge it like the adversarial/temporal clause, or drop the explanation.

## 3. Rejected (7)

| # | voice | item | why rejected |
|---|---|---|---|
| R1 | Kimi | §5.1.6 CI [49.88, 53.49] vs artifact [49.87, 53.48] | The paper's interval is centred on the **weighted** mean, 51.682 ± 1.805, which is the reported 51.68%. `RESULTS-PHASEH-v2-5BATCH.md` l.30 and l.119 give 49.88 as the weighted bound. The difference is a 0.01 rounding choice and is defensible |
| R2 | Kimi | §5.4 "100+ conversation turns" | It is a lower bound consistent with v3 (">10,000 turns" per 1M-token project, evidence spread across speakers, groups and days). Kimi's replacement, "hundreds of turns", is no better sourced |
| R3 | Kimi | F1 heading "(not yet deployed)" vs body "(deployed)" | The parenthetical in l.1297 qualifies the Ed25519 checkpoints, which shipped in P4 (#294). The body then says P5 "had not been deployed". The sentence is ambiguous but not wrong; this is style only |
| R4 | Codex | Supplement still claims "+2 pp … above the retrieval-stage ceiling" | The v1.0.3 erratum at the top of the supplement (l.14–29) says ceiling statements "are left as written here; §5.1.9 of the main paper supersedes them". The supplement's "PASS / ONLY VALIDATED" labels for IterB are gate verdicts, not significance claims (relevant to Kimi's supplement remark too) |
| R5 | Codex | "offline-capable" overstates (l.1312) | The sentence concerns the future reranker not adding a cloud call. The FTS5-only keyless mode is declared in the abstract and §4 |
| R6 | Codex | EverOS 4 GB / 60 s / 12× unverifiable | Already labelled as *estimates* of a historical configuration, with a dated caveat on the 404 (l.1205, l.1385) |
| R7 | Codex | "Adding MQ … yields no incremental lift" → "observed mean did not increase" | Wording only; the quantitative point is covered by M1 |

## 4. Verdict

**Not ready to publish.** The two high findings are required fixes:
- the IterB CI belongs to another experiment (AC on gpt-4.1-mini), and its "not significant" verdict lacks a named test and contradicts §5.8.1;
- the "like-for-like" Table 4 comparison runs on 2,733 questions against the paper's 2,400.

All are text-level fixes; no new run is needed. The medium findings should go in the same pass, as they are corrections of fact or of a cited number:
- the Wave C CI method;
- the "principally task setup" attribution;
- the rc4 "not captured" cells;
- HyperMem, gbrain, the "empirical upper bound", the co-fire claim;
- the v3 pin and the footnote title.

The six lows are quick edits.
