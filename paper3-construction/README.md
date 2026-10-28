# Paper 3 — the construction step. Collision check first, then the claim that survives it.

> Status **2026-10-27**: collision check done, four neighbours read, claim narrowed. **No text
> written.** The scope below needs Toto's approval before drafting, because the obvious claim is
> already taken and the one that survives is narrower than what Monday's measurements suggested.

## The collision check, and it is substantial

Four neighbours were read, not skimmed from the index. The first three overlap with the result we
measured on 2026-10-27, and one of them is **pre-registered**.

| our finding | already published? | by whom |
|---|---|---|
| LLM-extracted memory loses to raw/verbatim turns | **yes, three times** | `2601.00821` *Fidelity before Structure* (verbatim chunks beat lossy artifact extraction); `2609.34227`; `2610.29823` |
| the **context budget** decides who wins | **yes** | `2609.34227` — reranking adds 17.4 pts at a tight budget, 1.5 at a generous one, and it says this is why the literature disagrees |
| the **writer** sets a ceiling the reader cannot recover | **yes** | `2610.29823` §4 — *"a stronger reader does not recover what a weaker writer left out"*, Zep's gpt-4o-mini graph reads 43/43/45% across three readers |
| **construction order** discards different evidence | **yes** | `2609.34160` RoutePrism — restoring one displaced record recovers >60 pp |
| the mechanism is **lossy distillation**, and accuracy tracks how much source text survives | **yes** | `2601.00821` *Fidelity before Structure* — controlled ablation, one fixed pipeline, six confound controls |
| what is lost is the **literal detail** | **yes** | `2601.00821` — summarization turns *"use type hints **everywhere**"* into *"the user prefers type hints"*, deleting the quantifier: 14.0% against 91.0% |
| write-time loss against query-time loss, quantified | **yes** | `2601.00821` — of diagnosable failures, **69.0%** are facts the extractor never wrote down, 31.0% are retrieval misses |
| build cost exceeds the whole rollout it saves | **yes** | `2610.29823` §3 — Mem0's build $0.56 against full context's $0.43 |

⛔ **So "agent memory has negative net value against naive RAG" is not ours to claim.** Three papers
hold it, `2609.34227` holds it with a registered plan, a non-inferiority margin and blind human
grading, and `2610.29823` holds it with a cost frontier across three model tiers. Publishing that as
our contribution would be entering a crowded room with a weaker instrument.

### What none of them has

| | why they cannot have it |
|---|---|
| **the construction window** — `session-distill.ts:141-144` skips any session already logged, so the builder saw a median **24.0%** of the prose in the 200k–1M band | on a benchmark the builder receives the corpus once, complete, with no window, no prune and no per-run ceiling. The variable does not exist there |
| **the factorial** — window × criterion, and their **interaction** | `factorial` appears 0 times in RoutePrism, which is the most intervention-minded of the four. All four vary **one** thing: the reader, the budget, the order, the method |
| **the repair** — fixing both brings extraction level with selection (net value −21.2 pp → **0.0 pp**) | all four treat extraction as a black box at its defaults. `2610.29823` states it: *"Mem0 and Zep run with their default extraction and retrieval, and other settings may do better"* |
| **a production multi-agent corpus** — 1,610 transcripts, 6 agents, 2.66M chars of real human prose | all four use LoCoMo / LongMemEval / PersonaMem. `2609.34227` declares it: *"LoCoMo, whose dialogues are LLM-generated"*; `2610.29823` runs **one** conversation |

### And `2601.00821` hands us a named prediction to test

Read in full on 2026-10-27, after the first collision pass. It is the closest prior statement of our
faithfulness half — and it leaves our intervention explicitly undone, twice:

> *"These patterns suggest that extraction prompts **could be improved** by explicitly instructing the
> LLM to attend to implicit attributes, emotional states, and negative constraints."*

> *"**Better extraction prompts** — explicit date/time targeting, temporal attribute modeling — could
> shrink this class, **but cannot reach the unconditional retention of a verbatim store.**"*

Its only prompt variation is a **contamination control** (few-shot examples swapped so they stop
favouring the artifact pipeline), not an intervention; and its *gleaning pass* — a second extraction
scan — is reported as contributing "negligibly". So improving the criterion is conjectured, not
tested, and the one thing resembling it that was tested did not work.

🔑 **Our arm D is that prediction, run.** And our result splits it in a way that is more informative
than either outcome alone:

| the prediction, on | verdict |
|---|---|
| **retention** | **holds, and trivially.** Identifier survival went 6.6% → 12.9%. A verbatim store retains 100%. 12.9% is not unconditional |
| **accuracy, at equal context budget** | **holds.** 48.5% against naive RAG's 63.6% |
| **accuracy, at the budget a repaired builder naturally produces** | **fails.** 63.6% against 63.6% — level; and 67.5% against 62.5% in the 200k–1M band, where memory overtakes |

That refines their law rather than contradicting it. *"Accuracy tracks how much source text
survives"* is a statement about text in general. Ours is that what governs is the survival of the
**identifier the question asks for**, that this is steerable by the criterion, and that it does **not
have to reach 100%** for accuracy to draw level: a 6 pp gain in identifier retention bought 21 pp of
accuracy. A sixth of the retention, all of the accuracy.
| **the asymmetry by fact type** — `context` 26.2% against `lesson` 60.7%, and only `context` fails to move when the window is fixed | `2609.34227` decomposes by category, but of the **selection** bottleneck (shortlist misses 11.5%, rerank drops 9.2%), not of what construction destroys |

## The claim that survives, and it is the inverse of theirs

All four conclude, in their own words, that the answer is to stop designing memory and give the model
better search over the raw record. Our measurement says something they could not test:

> **Extraction is not inferior to selection. *This* extraction was.** `2601.00821` predicts that a
> better extraction criterion *"cannot reach the unconditional retention of a verbatim store"*. On
> retention it is right and trivially so. On **accuracy** it fails: two properties of the
> construction step — how much of the conversation the builder is shown, and whether its criterion
> requires identifiers verbatim — interact **superadditively**, each alone recovering 8.7% of the gap
> to an oracle and both together 45.7%, and the repaired memory draws level with naive retrieval over
> the raw text. What governs is not how much text survives but whether the **identifier the question
> asks for** survives, and that is steerable at a sixth of full retention. The window is a property
> only production has; the criterion is one every published study held at its default.

🔴 **Scoped down on 2026-10-27, by two adversarial voices from different families**
(`audits/2026-10-27-codex-and-deepseek-on-the-prereg.md`). Three sentences of that claim are **not
what the pre-registered plan can confirm**, and the plan was changed rather than the claim being
softened with a caveat:

| the claim above | what §11 can now support |
|---|---|
| the two repairs interact **superadditively** | confirmatory: the **total** effect of repairing both. The interaction is a pre-registered **secondary**, underpowered at every n this corpus allows (78.1% at the full 500, 38.0% at the n=200 stage 1) |
| what governs is whether the **identifier** survives | **nothing in §11 measures this.** H3 lives in §§1–10, which are history, and §11 builds no identifier-survival instrument. It is a hypothesis this study leaves open |
| the repaired memory **draws level with naive retrieval** over the raw text | **not testable here.** §11 has no selection arm: the 2×2 is window × criterion, both inside the memory pipeline, with no BM25 or dense baseline over raw text. The 63.6/63.6 draw is from the exploratory run only |
| a constructive **refutation** of a conclusion four papers share | an **estimate that is inconsistent with** that conclusion on this corpus — and the estimate that licenses even that comes from the production leg (12 sessions, 8 of them reused, a single judge family), not from §11 |

The reason is not timidity. A two-stage system — the window deciding whether evidence arrives, the
prompt deciding whether it is used — produces a positive additive interaction **with no joint
mechanism at all**, so "interaction > 0" never identified the mechanism. §11.4 turns that into the
plan's substantive null and the measurement survives it: serial chaining predicts **+0.4 pp** from
our own three other cells, against the **+13.0 pp** measured — 33×. That comparison is the sharpest
thing here, and it is a thing the benchmark can **refute**, which the earlier framing was not.

🔴 **Scoped down again on 2026-10-27, by a third family** (GLM-5.3, `audits/2026-10-27-glm-on-the-
final.md`). Two of the four rows above are new: the plan never had a selection arm, and it never had
an identifier-survival instrument, so two claims that read as results of this study were results of
nothing in it. The same pass found that the **equivalence margin could not be reached at any n this
corpus allows** — so §11.4 no longer promises evidence of absence, and says in the document why it
cannot. Three families have now read this plan; each found something the previous two did not.

It still answers `2609.34227`'s title — *When Does Selection Replace Extraction?* — from the other
side: on this corpus, selection replaced extraction because the extraction was misconfigured, not
because selection is better in principle.

### Numbers it rests on (all measured, all in `audits/2026-10-27-*`)

| | |
|---|---|
| gap to oracle | A 88.9% vs B 42.4% = 46.5 pp |
| window alone | 46.5% → +4.1 pp, 8.8% of the gap |
| criterion alone | 46.5% → +4.1 pp, 8.8% |
| **both** | **63.6% → +21.2 pp, 45.6%** — interaction **13.0 pp**, larger than either main effect |
| net value vs BM25 at equal budget | B −21.2 pp · repaired, equal budget −15.2 pp · repaired, its own 2.41× context **0.0 pp** |
| `context` | 26.2% → 52.4%, still 14 pp under retrieval ⇒ improved, not solved |
| 200k–1M band | 27.5% → 67.5%, **overtakes** naive RAG |
| see-once in production | median visible fraction 100% / 72.1% / **24.0%** by size band; 7.6% of sessions distilled while still growing |

## Where we are weaker than `2609.34227`, and it must be said in the paper

- **No pre-registration.** They registered a plan, a primary test and a non-inferiority margin before
  the held-out run. We did not; every arm here was designed after seeing the previous one.
- **No human grading.** They graded blind and reported that it narrows the margin. Our labels are one
  model's, with the arm-A false-positive floor as the only calibration.
- **n.** 99 questions over 20 sessions against their 778 over five conversations.
- **One judge family.** Deterministic (540 pairs, 0 label changes) but single.
- **Two cells where our own re-implementation is unfaithful**, stated in
  `2026-10-27-neither-cause-explains-it-alone.md`: `context` 16.7% against the real 26.2%, and the
  50–200k band.

⇒ The honest shape is **a short empirical paper with a registered follow-up**, not a claim of
superiority over a registered study. `2610.29823` shows the format is publishable: it calls itself
*"a short empirical study, with one conversation and one run per cell"* and lists its limits.

## Open decisions — Toto's

1. **Scope.** Short empirical note on the interaction (what the data supports today), or hold and
   pre-register the factorial on a bigger sample first?
2. **Cite or compete.** The claim above cites all four as motivation. Confirm that is the posture.
3. **Corpus release.** The numbers rest on a private multi-agent corpus. Nothing is releasable as
   text; what can be released is the code, the question set in redacted form, and the judge keys.
   Without some release we are the only ones who can check it — which is what we criticise elsewhere.
4. **The repair ships or not**, independently of the paper: `session-distill.ts:141-144` plus the
   identifier paragraph, both or neither (each alone buys 4 pp and reads as a failed intervention).

## Read, with what each was read for

| id | title | read for |
|---|---|---|
| `2609.34227` | When Does Selection Replace Extraction? A Pre-Registered Test… | the declared collision candidate. Full text + limitations |
| `2610.29823` | MemoryTax: The Bitter Lesson of Agent Memory | full text. **The most dangerous**: 13 votes, same question, cost frontier |
| `2609.34160` | RoutePrism: Tracing Construction Order Effects in Agent Memory | abstract + term census. Varies order, not window; `factorial` = 0 hits |
| `2610.agent-memory-net-value-tax` | Memory Tax: Dissecting the Net Value of Agent Memory | read 2026-10-26; source of the faithfulness/accessibility/robustness split |

| `2601.00821` | Fidelity before Structure: Verbatim Chunks Beat Lossy Artifact Extraction | **read in full 2026-10-27**. The closest prior work, and the source of the prediction arm D tests. Takes our faithfulness half; leaves the criterion intervention undone |

**What reading it changed.** The faithfulness half is no longer a contribution — An has it with a
controlled ablation, six confound controls and a write-time/query-time split (69%/31%). What it
bought instead is better: a **named, published prediction** to test, and a sharper mechanism
**hypothesis** (identifier survival, not text survival) — which §11.5 item 9 keeps out of the
confirmatory claims, because this design cannot identify it. This is why it was read before depositing the plan; H2 and
H3 below were rewritten because of it.
