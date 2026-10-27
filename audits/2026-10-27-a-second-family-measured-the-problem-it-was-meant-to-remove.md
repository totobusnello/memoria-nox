# A second judge family measured the problem it was meant to remove — 2026-10-27

The strong form of H2 asked for human grading by someone who did not build the arms. The decision
was to use a **different model family** instead. It was run: Google `gemini-2.5-flash-lite` against
OpenAI `gpt-6-luna`, over the same 99 replay items, 594 judgements, **0 errors, 52 s**, cost under a
cent.

The result is that the substitution **does not** stand in for human grading — it quantifies why
human grading was asked for.

## The two families disagree on the effect, not just on the level

| arm | n | family 1 acc | family 2 acc | agreement | kappa |
|---|---|---|---|---|---|
| `c_all` | 99 | 0.061 | 0.232 | 0.828 | 0.3514 |
| `c_visible` | 99 | 0.101 | 0.253 | 0.848 | 0.4992 |
| `c_iso` | 99 | 0.071 | 0.242 | 0.828 | 0.3842 |
| `d_full` | 99 | 0.141 | **0.444** | 0.697 | 0.3415 |
| `d_visible` | 99 | 0.101 | 0.313 | 0.768 | 0.3379 |
| `d_iso` | 99 | 0.111 | 0.333 | 0.778 | 0.4000 |

A level difference between judges would be harmless, because the claim is a **contrast**. The
contrast differs too:

| contrast | family 1 | family 2 | difference |
|---|---|---|---|
| **`d_full − c_all`** — the decisive pair, both full-window, only the prompt differing | **+8.1 pp** | **+21.2 pp** | **13.1 pp** |
| `d_visible − c_visible` | +0.0 pp | +6.1 pp | 6.1 pp |
| `d_iso − c_iso` | +4.0 pp | +9.1 pp | 5.1 pp |

🔴 **The difference on the decisive pair is larger than the effect one of the families reports.** The
criterion effect depends on who judges, which is finding 7 of the Codex pass made numerical.

## The direction of the disagreement, which narrows it to two readings

| | |
|---|---|
| items family 2 accepts and family 1 rejects | **123** |
| items family 1 accepts and family 2 rejects | **1** |
| ratio | **123 : 1** |

**Almost one-directional** — the signature of a calibration difference, not of noise. And the extra
permissiveness is **not symmetric across the pair**:

| arm | family 2 adds | |
|---|---|---|
| `c_all` | 17/99 = **17.2%** | |
| `d_full` | 30/99 = **30.3%** | **asymmetry +13.1 pp** |
| `c_visible` → `d_visible` | 15.2% → 22.2% | +7.1 pp |
| `c_iso` → `d_iso` | 17.2% → 22.2% | +5.1 pp |

By category on `d_full`: `decision` 41.4%, `lesson` 39.3%, `context` 16.7%.

## The two readings, and why neither can be chosen here

**(a) Literalness bias.** The identifier prompt produces more literal answers, and the permissive
judge rewards them without an equal gain in correctness. Then **+21.2 pp is inflated** and +8.1 pp is
nearer the truth. The asymmetry toward D is exactly what this predicts.

**(b) Severity.** Family 1 rejects correct answers that family 2 recognises, and arm D simply has
more correct answers to recognise. Then **+21.2 pp is the truer number** and +8.1 pp is deflated.

The asymmetry is consistent with **both**: under (a) D attracts extra credit it has not earned; under
(b) D attracts extra credit because it has earned more. Two LLM judges cannot separate them — a third
rater is needed, and the only kind that is not another LLM is human.

🔑 **So the substitution measured the problem it was meant to remove.** That is a real result and it
cost under a cent: before this run, the criterion effect was a single number from a single family;
after it, the effect is known to sit somewhere in **[+8.1 · +21.2] pp depending on the judge**, and
the width of that bracket is the thing a human pass would collapse.

⚠️ **What this changes in the pre-registration:** §11.5's item 7 said the human validation in §7 must
reach the primary contrast. It now has a number attached — the judge choice moves the criterion
effect by **13.1 pp** — so a run whose headline is the criterion effect cannot report one judge's
figure as the figure. Either both are reported as a bracket, or a human pass picks between them.

**Artifacts.** `audits/2026-10-27-second-family-judge.py`,
`audits/2026-10-27-family-disagreement-direction.py`. Labels on the host at
`/root/medicoes/second-family-judge-2026-10-27.json`.
