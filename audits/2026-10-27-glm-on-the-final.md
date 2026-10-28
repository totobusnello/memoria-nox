# The third family read the deposited draft and found the gate's blind spot

**2026-10-27, 22:35 BRT.** The plan had already been rewritten twice that day, by Codex
(`gpt-6-astra`) and DeepSeek (`v4-pro`). The Zenodo draft was built, filled and read back,
`divergent: none`, with the tag `paper3-prereg-v1.0` pointing at a tree whose bytes matched the
deposit. Toto asked for one more family — *"ta c duvida chama o glm pra te ajudar"* — over a style
question. It returned seven defects in the design, and one of them was mine from that same day.

## Receipt

| field | value |
|---|---|
| voice | GLM-5.3 (Zhipu), `transport: http-direto` |
| `model_returned` | `glm-5.3` — the provider's own echo, matching the request |
| `exit` / `attempts` | `0` / `1` |
| `duration_s` | 476 (ceiling 540) |
| `attach_bytes` | 66,968 — the two files measure 66,968 characters |
| `cwd` | repo root, confirmed before launch |
| usage | prompt 18,054 · completion 34,212 · reasoning 30,214 |
| parecer | `adversary-output-glm-2026-10-27T223520-3941.txt`, 14,176 B |

An earlier attempt the same hour returned `http 429`, code 1113, *"Insufficient balance"* — the
account, not the prompt. Worth recording separately: `verify-vozes-http.sh` reported `ok` for GLM
before **and after** that failure. Its predicate is *"the host answers and rejects an invalid
key"*, which exercises authentication with a deliberately bad key so the check costs nothing.
Balance only shows with a **valid** key, as a 429 the probe never sends. A channel check that
costs zero cannot see what only appears when you spend.

## The finding that stopped the deposit

**The pre-set equivalence margin was unreachable at every sample this corpus allows**, and the
arithmetic is the plan's own. At `Var(D)=0.973`:

| n | SE | half-width at α=0.02 | inside ±5 pp? |
|---|---|---|---|
| 200 | 6.97 pp | 16.23 pp | no |
| **500** (whole corpus) | **4.41 pp** | **10.26 pp** | **no** |
| 2,106 | 2.15 pp | 5.00 pp | at the boundary |

Declaring equivalence needs **n ≈ 2,106** against a corpus of 500, so the decision table's
*"evidence of absence"* state could never be reached. Widening the margin does not rescue it: a
margin above 10.3 pp would swallow the whole 13.0 pp interaction.

The margin had been added earlier the same day, in response to the second pass, precisely so that
some outcome could refute the thesis. It was added without checking that it was attainable.

**And `estimand-and-power.py` — written that day as the gate against exactly this class — did not
catch it.** It checks the decomposition, the serial null and the power at each n. Power is a
statement about *detecting* an effect; equivalence is a statement about *bounding* one, and the
script had no section for the second. A gate blind to the claim it exists to protect is the
defect, not the claim. Section 6 now does that arithmetic, and fails if the plan ever promises an
absence verdict again — mutation-tested: reintroducing the margin makes it exit 1 and name the
promise.

## The other six, each verified in the text before being accepted

| # | finding | verification |
|---|---|---|
| 1 | §11.5 item 2 restates **verbatim** the sentence §11.2 quotes as wrong | L316 calls it wrong, L646 repeated it |
| 2 | §11.5 item 1 orders doses 0.12/0.48 | §11.7 records those as the corrected error; the matrix fixes 0.020/0.894 |
| 3 | §11.5 numbering duplicated | items 8 and 9 appeared twice; README cites "item 9" |
| 4 | §11.7 table says `OPEN` / `still owed` | three lines above prose announcing both items closed |
| 5 | README `4.0 + 4.0 + 13.2` vs plan `4.1 + 4.1 + 13.0` | the cells give 4.1 / 4.1 / 13.0; the README was wrong |
| 6 | the stopping rule is ambiguous | *"above the equivalence margin"* reads as −5 or +5; under the first, a CI of (1, 4) declares a confirmed repair and an absent effect at once |
| 7 | the answerable floor is a word, not a number | *"quantitative floor still owed"* — deciding the pass after the data is the freedom pre-registration removes |

Plus two of scope, which cost the README two claims:

- **No selection arm.** The 2×2 is window × criterion, both inside the memory pipeline. `naive RAG`
  appears once in §11, descriptively. The claim *"draws level with naive retrieval over the raw
  text"* is not testable by this plan.
- **No identifier-survival instrument.** `H3` appears once in §11 — in the sentence delegating to
  it. H3 is defined in §§1–10, which §3 declares history. The delegation was circular.

And the diagnosis that organises all of them: **palimpsest.** Each correction had been appended
without regenerating the sections that govern, so the header could claim *"All are addressed"*
while two §11.5 items contradicted §11.2 and §11.4. The missing edit was never another round of
findings.

## What the style question got

The voice **agreed with the decision and disagreed with the reason**, which is what it was asked
to do. Of ~70 em dashes: about 70% are label→gloss (the work of a colon, not staging), a few are
genuine parenthetical pairs, and **5 to 8 are rhetorical** — where the claim that they all carry
technical qualification fails. It cited each sentence in full. It also named what a mechanical
pass would have broken: em dashes **inside quotations** from another paper, and the `−` minus
signs in the estimand formulas.

Nothing was rewritten. Eight specific cases are on record for a future pass; the density itself
stays, because the 1.0/thousand ceiling is a ruler for narrative prose and this document is
definitional.

## What this costs the study, stated plainly

**No outcome now refutes the repair thesis by showing the repair does nothing.** A primary CI
containing 0 is inconclusive, and the document says so instead of promising otherwise. What
remains refutable is the *mechanism* claim, through the serial null — production exceeds it by
33× (+0.4 pp predicted against +13.0 pp measured), and that leg is intact.

## The pattern across the day

Five families were asked; three never returned a verdict, each for a different reason, and none of
them was the voice:

| voice | receipt | cause |
|---|---|---|
| Codex | `exit: 0`, 253 s | delivered |
| DeepSeek | `exit: 0`, 81 s | delivered |
| Grok | 3× `exit: 1`, 481/481/480 s | wall-clock: ~60 KB does not return within the 480 s the visible route allows |
| Gemini | **no receipt in 2 h** | the shell never reached `adversary-run.sh` |
| GLM | `exit: 1` then `exit: 0`, 476 s | balance, then delivered |

The third family found what the first two did not, on a document the first two had already
rewritten. That is the argument for different training families, and it is also the warning: a
finding from the third pass is a defect introduced by the fixes from the first two.
