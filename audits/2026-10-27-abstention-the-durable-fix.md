# Abstention: a structural predicate beats five substrings, and why neither is the fix — 2026-10-27

The abstention detector in `eval/run-abstention.mjs` decides, from five substrings, whether the
system refused to answer. Its own header already names the durable fix: *"o conserto duravel e a
abstencao emitir CANON deterministicamente em vez de pedir ao LLM que a escreva."* This measures a
cheaper improvement, adopts it, and then says why it is not that fix.

**Cost zero** — recomputed from the 48 rows already on disk.

## The structural predicate is strictly better, and free

The serving prompt requires every factual claim to carry a `[chunk_N]` marker (`prompt.ts`:
*"Cite EVERY factual claim with [chunk_N]"*), so an answer with no citation has **nothing anchored in
the context**. That is a structural signal, immune to wording and to inflection.

Against the bounded judge's `prob_declara_ausencia > 0.5` over the same 48 items — the calibrated
reading from 2026-10-26, with equalised input already proved at 48/48:

| predicate | TP | FP | FN | TN | accuracy | kappa |
|---|---|---|---|---|---|---|
| five substrings *(published)* | 21 | **0** | 5 | 22 | 0.896 | 0.7938 |
| **`citations.length === 0`** | 23 | **0** | 3 | 22 | **0.938** | **0.8754** |
| either | 23 | 0 | 3 | 22 | 0.938 | 0.8754 |

**Neither over-marks.** FP=0 for both, and that matters more than recall here: a detector that turns
a useful answer into a refusal is worse than one that misses a refusal. The structural predicate
dominates — it finds everything the substrings find, plus two.

Of the five the substrings miss, it catches the two whose answers carry no citation:

| item | citations | answer head |
|---|---|---|
| Q60 | **0** | *"Não há informações no contexto fornecido que expliquem a diferença entre…"* |
| Q66 | **0** | *"Não há informações sobre como migrar Gemini Flash para Flash-Lite no con…"* |

Both are the number inflection the old header warned about — *"informação"* is not a substring of
*"informações"* — and the structural predicate does not care.

## 🔴 The three it still misses are the reason no surface predicate can work

| item | citations | answer head |
|---|---|---|
| `tier_decay` | **1** | *"O `tier_decay` não é explicitamente explicado no contexto fornecido. No…"* |
| `reflect_quota` | **1** | *"O problema de consumo de cota do Claude era o heartbeat a cada 30min em…"* |
| Q57 | **1** | *"The `memory-recompile` skill is used for the nox-mem compiled truth + t…"* |

Each **cites a chunk and declares the context does not explain the thing**. The answer is genuinely
both — it refuses the question and offers the neighbour, which is the `recusa_com_vizinho` level the
abstention judge separates. No predicate reading the answer *text* can split that, because there is
nothing in the text to split: the system did two things at once and reported them in one string.

## What this does to the published baseline — it shrinks the gap

| predicate | negatives | positives | **gap** |
|---|---|---|---|
| five substrings *(published)* | 0.6957 | 0.2000 | **+0.4957** |
| `citations === 0` | 0.6957 | 0.2800 | **+0.4157** |
| bounded judge *(reference)* | 0.7826 | 0.3200 | **+0.4626** |

The structural predicate catches two more **positives** and the same negatives, so the gap narrows by
0.08. ⚠️ **That is less flattering and more correct**: it is 0.0469 from the judge's gap against the
substrings' 0.0331 in the other direction, with a kappa 0.08 higher. The published 0.6957/0.2000
remains the registered figure, measured by the predicate that produced it — the old function is kept
**byte-identical** in the harness and both labels are now written per row.

## The durable fix, designed and not implemented

Serving already has the deterministic gate: `index.ts:83` short-circuits on `chunks.length === 0` and
returns `CANONICAL_EMPTY_ANSWER` with `failed_reason: "retrieval_empty"`, no LLM spend. **It fired 0
times in 48 items**, because hybrid retrieval always returns candidates — BM25 always matches
something. So abstention is decided by the model, which is *asked* to reply with the canonical string
and instead writes its own prose.

The fix is to stop asking the model to reproduce a string and have it return a **field**:

1. `prompt.ts` requests a structured object — `{answered: boolean, answer: string, citations: [...]}`
   — instead of free prose with an exact-string instruction.
2. `index.ts` reads `answered`. On `false` it emits `CANONICAL_EMPTY_ANSWER` itself, with a new
   `failed_reason: "model_abstained"`, distinct from `retrieval_empty`.
3. The detector then becomes `answer === CANONICAL_EMPTY_ANSWER` — exact, with nothing to guess.
4. And the `recusa_com_vizinho` case stops being invisible: a response with `answered: false` **and**
   citations is the model offering the neighbour, which is now a readable state instead of one string.

Not implemented here, deliberately. It changes `answer()`, which serves the production API, so it
needs its own change with a smoke against an isolated copy, a check that `failed_reason` passes the
v11 schema CHECK (`telemetry.ts:25` constrains the enum), and the existing tests under
`src/lib/answer/__tests__/`. Adding an enum value to a column with a CHECK constraint is exactly the
kind of change that fails in production and not in a smoke.

**Artifacts.** `audits/2026-10-27-abstention-structural-predicate.py`, and the harness change in
`eval/run-abstention.mjs`.
