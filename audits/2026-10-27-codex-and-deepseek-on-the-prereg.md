# Two families on the pre-registration, and the primary moved

**2026-10-27.** Toto asked for both voices on the paper — *"Passe o codex e deepseek no paper"* —
over `paper3-construction/PREREGISTRATION-DRAFT.md` and `README.md`, in `challenge` mode, neither
voice anchored on the other's findings or on the earlier pass of the same day.

## Receipts

| voice | model returned | exit | duration | what proves it read the document |
|---|---|---|---|---|
| DeepSeek | `deepseek-v4-pro` | 0 | 81 s | `attach_bytes: 51378` — the two files measure 51,378 characters |
| Codex | `assinatura(OpenAI/gpt-6-astra)` | 0 | 253 s | `harness/nativo`, read from disk, `cwd` at the repo root |

- `logs/adversary-receipts/adversary-receipt-deepseek-2026-10-27T163540-52400.txt`
- `logs/adversary-receipts/adversary-receipt-codex-2026-10-27T163613-53106.txt`

`verify-adversary-receipt.sh` returns **VÁLIDO** for both. 7 findings from DeepSeek (5 high,
2 medium); 12 from Codex. The Codex voice states it did not open the scripts or the cited audits,
and says so where a conclusion would have depended on them.

⚠️ **Two shell failures, both in the shells and neither in the voices.** The Codex shell ended its
command with `2>&1 | true` — piping, which the route guard blocks — so the first attempt never
reached the provider: no request, no charge, no verdict. It then diagnosed the failure by listing
`logs/adversary-receipts/` **relative to the repo**, a path that does not exist, and read "does not
exist" as "is empty", concluding the voice had left no receipt. The real directory holds 229
entries including two Codex receipts from earlier the same day. The DeepSeek shell also piped
(`2>&1 | cat >/dev/null`), discarding stdout, but the wrapper had already written the output to
disk, so nothing was lost. Its summary then said "6 findings" while listing seven — which is why
the rule is to read the `output_file` and never the shell's summary.

## What both found independently, and the arithmetic confirms

**The power table sized the interaction test with the total effect as δ.** From the document's own
four cell means:

| quantity | value |
|---|---|
| main effect, window | +4.1 pp |
| main effect, criterion | +4.1 pp |
| **interaction** | **+13.0 pp** |
| **total** | **+21.2 pp** |

The row read *"21.4 pp — production's measured interaction"*. Ten lines below, the same section
said *"the honest ceiling of what 500 instances can resolve is ≈13 pp"*. Both sentences were true
and they contradicted each other.

Consequence, at α=0.03 and 80% power with `Var(D)=0.973`:

| δ | n | against a corpus of 500 |
|---|---|---|
| 21.2 pp (total) | **196** | fits |
| 13.0 pp (interaction) | **522** | **does not fit** |

n=193 delivers **36.7%** power for the effect it exists to detect; the whole 500 delivers 78.1%.
The earlier fix of the same day (#613) corrected the **variance** and left the **numerator** wrong:
one leg repaired, the other still bent.

## What only Codex found

**1. "Worst case over ρ ∈ [0, 0.6]" is not a worst case.** It supplied a joint distribution with the
same four marginals and `Var(D) = 3.3471` — reproduced exactly by `estimand-and-power.py`, by
integration rather than simulation:

```
U ~ Uniform(0,1);  Y11 = 1[U < 0.636];  Y00 = 1[U < 0.424];  Y10 = Y01 = 1[U > 0.535]
marginals 0.636 / 0.424 / 0.465 / 0.465   E[D] = 0.130   Var(D) = 3.3471
```

A maximum inside a dependence family the author chose is not an upper bound. The word
"conservative" is removed from the plan, and the second column of every power table now reports what
this counterexample would cost, so the exposure is visible before the run.

**2. A pipeline that beats every declared control.** The added legs killed the constant-`NAO SEI`
answerer; they did not test that the causal path was walked:

```
keep answer_session_ids and the reference answer on the item
if any evidence session is still present -> return the reference answer
else                                     -> return NAO SEI
```

Floor in the positive control, full-window accuracy in the negative one, clears the answerable
floor, passes the paired item-wise diagnosis — without ever reading the constructed context. A
**counterfactual-evidence** control was added: rewrite the answer-bearing session so the fact
itself differs, and require the answer to follow the altered fact.

**3. A positive interaction does not identify the mechanism.** In `P(correct|w,c) = e_w · q_c` — the
window governing whether evidence arrives, the prompt whether it is used — the additive interaction
is `(e₁−e₀)(q₁−q₀) > 0` with nothing jointly repaired. His worked example (8% / 14% / 32% / 56%,
interaction 18 pp) reproduces exactly.

🔑 **And this is the finding that made the design better rather than smaller.** The serial model is
*fitted*: three cells determine the fourth, `Y11 = Y01·Y10/Y00`. On our own measurements it predicts
an interaction of **+0.4 pp** against the **+13.0 pp** measured — **33×** — and the direct check
fails in the right direction (`Y00·Y11 = 0.2697` vs `Y01·Y10 = 0.2162`). So the secondary hypothesis
is now stated against the serial null instead of against zero, which is what finally gives this leg
a prediction the benchmark can **refute**.

**4. The documentary boundary.** §§1–10 describe the blocked first attempt and §11 what will run;
the plan said "§3 is amended to match" without carrying the replacement text. A boundary note now
says §11 governs and §§1–10 are history, so the run can be implemented without deciding which old
sentences still bind.

## What only DeepSeek found

**5. Nothing refuted the thesis.** A CI containing 0 was labelled *"no interaction demonstrated at
this n; report the interval, not a null"* — no equivalence margin, so no possible outcome was a
refutation. A **5 pp margin** is now pre-set for both the primary and the secondary.

**6. Context length is not controlled.** W1C1 serves more prose than W0C0 by construction, so a
positive effect is consistent with "more context helps" and needs no construction story. Served
length is now recorded per item, entered as a covariate, and a **length-matched reference arm** runs
on the stage-1 sample.

**7. The judge bracket does not cover the primary.** The two families were compared on
`d_full − c_all` only, and the disagreement is asymmetric **toward the W1C1 corner** (+30.3% on
`d_full` against +17.2% on `c_all`) — the corner that carries both the total effect and the
interaction. The blind human grading of §7 must therefore reach the primary contrast, or the
confirmatory claim is judge-conditional and says so.

**8. W became a three-level factor and the design dissolved.** The full window left the matrix while
the estimand still needed it, and no primary contrast was named for three levels. The matrix is now
fixed: four primary cells at W ∈ {0.240, full} × C, plus four dose-sensitivity cells on an n=60
subsample. The cut rule is executable rather than described — most-recent-first, cumulative
`len(prose)`, the crossing session included whole, realised fraction recorded per instance.

## One finding that was mine, not the paper's

Codex reported a metric disagreement: nDCG cannot parameterise an interaction of Bernoullis. The
document is consistent — it says *"matched the deployed **accuracy** exactly (42.4%)"*, judged
accuracy, binary per item, which is what `D_i ∈ {−2..2}` requires. **The word "nDCG" came from the
prompt I wrote to both voices.** The prompt carrying the error it asks the voice to find, which is
a failure mode already recorded in this repo and repeated here.

## What the cost turned out to be

The missing full-window cell was also a missing cost. The draft quoted 565 blocks per instance for
"six cells" in a matrix where W=full did not appear; the four primary cells alone are **608**.

| | n | cost |
|---|---|---|
| primary 2×2 | 200 | US$ 75.7 |
| dose sensitivity, 4 cells | 60 | US$ 16.7 |
| counterfactual-evidence control | 40 | US$ 15.1 |
| **stage 1** | | **US$ 108** |
| stage 2, primary only | 500 | US$ 189 |

**US$ 108 for stage 1, not the US$ 71 approved** — the price of the cell the design needs and the
controls that make it interpretable.

## Verdicts, verbatim

> **Codex:** *"Minha recomendação é preservar a abordagem de duas pernas, mas bloquear o depósito
> desta versão como confirmação da tese do README."*

> **DeepSeek**, finding 1: *"O n=200 do estágio 1 não tem poder para o efeito de interação medido de
> 13,0 pp; ele só tem poder para um efeito de 21,4 pp que foi incorretamente rotulado como a
> interação."*

Both verdicts were acted on. The deposit was **not** made against the version they read.

## Instruments

| file | what it does | exits non-zero when |
|---|---|---|
| `paper3-construction/estimand-and-power.py` | recomputes the decomposition, the serial null, both variance scenarios, every n and every achieved power | the decomposition stops closing, the serial null stops being beaten, or the interaction starts fitting the corpus |

The third condition is deliberate: if the interaction ever fits 500 instances, the reason this
design demoted it has gone away, and the script should force that to be re-examined rather than let
a stale decision stand.

## Two defects in how I verified

Both patches asserted their own post-conditions, and **two of those assertions failed on strings the
new text quotes on purpose** — `US$ 71` inside *"not the US$ 71 the draft promised"*, and
`§3 is amended to match` inside the sentence explaining why that promise was wrong. The edits had
already been written to disk; only the verification was wrong. A gate that forbids a string cannot
tell a claim from a quotation of a claim, and the fix is to assert on counts and position, not on
absence.
