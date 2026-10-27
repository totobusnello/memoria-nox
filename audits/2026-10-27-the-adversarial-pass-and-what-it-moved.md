# The adversarial pass: 20% of judge labels flip on a second reading, and the ceiling drop IS coverage — 2026-10-27

Two voices, two scopes, both `exit: 0`, both read the files themselves from the repo root.

| voice | scope | duration | findings |
|---|---|---|---|
| Codex `gpt-6-astra` | §11 of the pre-registration | 155 s | 6 — see `2026-10-27-codex-challenge-s11.md` and §11.7 |
| Kimi `kimi-code/k3.1-pro` | the three ruler audits | 333 s | 6 — resolved below |

**Follow-up cost US$ 0.0026.** Four of Kimi's six were measurable with data in hand, and the results
run in both directions.

## 🔴 Finding 3 — the judge flips 20% of labels on a second reading

Kimi's point: the 21/21 verification tested **provenance**, and nothing in the audits measured whether
the same `(query, chunk)` pair gets the same label twice. Measured, on a sample stratified across the
probability range because stability at the extremes says nothing about the middle:

| band | n | flips at p>0.5 | mean \|Δp\| |
|---|---|---|---|
| very low (0–0.1) | 12 | **0** | 0.004 |
| low (0.1–0.4) | 12 | 3 | 0.208 |
| **borderline (0.4–0.6)** | 12 | **4** | 0.228 |
| **high (0.6–0.9)** | 12 | **5** | **0.301** |
| very high (0.9–1.0) | 12 | **0** | 0.035 |
| **total** | **60** | **12 = 20.0%** | |

Cases: Q74 **0.13 → 0.82**, Q46 **0.38 → 0.97**, Q76 **0.52 → 0.02**. The judge is firm at the
extremes and unstable in between — and the *high* band is the worst, not the borderline, which is not
what a threshold-sensitivity analysis would have predicted.

**What it does to the published ceiling:** substituting the second reading on those 60 pairs (9.7% of
620 labels) moves pooled **0.4394 → 0.4315**, −1.8%. Nine of 57 queries move, the worst being Q55
**0.3066 → 0.0000**.

⇒ **Reporting 0.4394 to four decimals claims a precision the labelling does not have.** The honest
form is **[0.26 · 0.44] with the ceiling carrying roughly ±0.01 of labelling noise**, and the
threshold robustness I reported (0.024 across p>0.3…0.7) does **not** cover this: it varies the cut
on one reading of the judge, not the reading.

## ✅ Finding 1 — the criticism is right, the conclusion survives a proper contrast

Kimi: the v2→v3 comparison confounds four changes at once — queries 55→57, gold 95→85, 27 repaired,
Q52 added — so *"the ceiling fell because the top-10 is now fully judged"* is not identified by it.
**Correct, and the controlled contrast already existed in this repo since 2026-10-26; I did not use
it.** `eval/judge-relevance.py` had labelled the full top-10 of the **unchanged** v2: same rankings,
same gold, same 55 queries, 98.9% coverage.

| | ceiling |
|---|---|
| v2, partial labels (published 2026-10-22) | 0.5114 |
| **v2, full labels** — only coverage differs | **0.4412** |
| **⇒ attributable to coverage alone** | **−0.0702** |
| v3, full labels | 0.4394 |
| ⇒ residual: gold repair + two added queries | **−0.0018** |

**Coverage accounts for 97% of the −0.0720 drop.** The attribution holds — but it held by luck of
having the artifact, not by the reasoning I published, and Kimi's other point stands untested: the
audits never showed the retrieved rankings were the same across runs.

## ✅ Finding 4 — confirmed; reproducing strict was a weak control, and the real one now exists

Strict needs no LLM, so it is unchanged **by definition** when labels change. Measured:

| perturbation | pooled | strict |
|---|---|---|
| flip one relevant label inside a top-10 | 0.4394 → 0.4377 ✅ moves | — |
| flip **all 113** relevant labels inside top-10s | → **0.2567** | **unchanged, Δ 0.0000** |

Flipping every label collapses pooled exactly onto strict, which is direct proof that strict sees
nothing of the arm the rescore was built for. ⚠️ And a correction to my own script: its printed note
asserted that a label **outside** every top-10 moves pooled. The measured delta was **0.0000** —
pooled's ideal saturates at K=10, so the sensitivity is conditional. I wrote the warning without
measuring it.

## ✅ Finding 5 — does not materialise

Kimi: byte-identity proves no anchor can separate the chunks, not that they are equivalent for every
question, and the exemption is worthless if the **scorer** credits only one arbitrary id. Checked
against the actual resolved map:

| entry | resolver found | scorer credits |
|---|---|---|
| Q71 `ambiguous_duplicate` | [316535, 316569] | **both** |
| Q92 `ambiguous_structural` | [227319, 227320] | **both** |

The contract holds. (Q71's run returned neither, so its nDCG is 0 regardless.) The broader point —
that byte-identical text can differ in provenance, and that the selftest probes cardinality extremes
rather than the semantic boundary — is accepted and unaddressed.

## ⚠️ Findings 2 and 6 — both correct, both soften a claim of mine

**2.** My statement that the invalid gold *"was measuring the wrong thing, not depressing a score the
system deserved"* is **too categorical**. A query can have had gold that zeroed it unfairly **and** a
true answer the retriever also misses; a low score after repair does not decompose the earlier error.
And there is **selection**: receiving invalid gold plausibly correlates with obscure or dispersed
answers — the 21 answers found outside the original file are themselves evidence of a localisation
problem, which plausibly correlates with harder retrieval. The defensible claim is narrower: **the
+37.5% prediction did not materialise, and the repaired queries still fail at retrieval.** Also
correct: the zero-hit rise 52.7% → 56.1% is **not independent evidence** — same run, changed
denominator.

**6.** *"Immaterial on average"* does not follow from 1.9% corpus duplication. The ~0.2-slots figure
assumes uniform draws; duplicates score identically and arrive adjacent, so the corpus mean does not
transfer to a top-10. With 57 queries, one query contributes 1.75% of the aggregate, so a handful of
severely capped queries can move it. My own text said the real waste needs the actual top-10s and
then drew the conclusion anyway. **The claim is withdrawn to "concentrated in few files; the per-query
effect is unmeasured."**

## What this pass cost and what it bought

Two shells, two voices, US$ 0.0026 of follow-up measurement. It produced one finding I would not have
found mechanically (**the 20% flip rate**, which changes how the headline number must be written),
confirmed one weak control and replaced it, cleared one concern, and softened two claims. Every
mechanical gate I ran on these audits had passed.

🔑 **Adversarial review and mechanical checks catch disjoint defects** — and the specific shape here
is that mechanical checks verify what the code does, while both voices went after **what the numbers
are allowed to mean.**

**Artifacts.** `audits/2026-10-27-kimi-{3-judge-stability,3-effect,4-5,1-paired}.py`, the two pareceres
(`-codex-challenge-s11.md`, `-kimi-challenge-medicoes.md`), receipts under
`~/Claude/logs/adversary-receipts/`.
