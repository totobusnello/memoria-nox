# staged/abstention-canonical — step 7b: an unanchored answer becomes the canonical refusal

Mirror of three modules that live on the VPS at
`/root/.openclaw/workspace/tools/nox-mem/src/lib/answer/` (repo `nox-workspace`). This directory is
the patch; the serving tree is the original.

## What it changes

`index.ts` — after retrieval, the prompt call and the hallucination retry have all resolved, an
answer that carries **no `[chunk_N]` citation** is replaced by `CANONICAL_EMPTY_ANSWER` and tagged
`failed_reason: "model_abstained"`. Three lines, at the one point where `finalText` and
`finalCitations` are both settled.

`types.ts` — `"model_abstained"` added to `AnswerFailureReason`, with the reason it is distinct from
`retrieval_empty` written next to it.

`telemetry.ts` — maps the new reason to `null` **explicitly** rather than letting it fall through
`default`. The v11 CHECK admits only three values, and a value that reaches NULL through a default is
indistinguishable from one nobody thought about — the defect class measured in this repository on
2026-10-27, where `session-distill`'s INSERT omits `retention_days` against a backfill that intends
90 days. The abstention is still persisted, in `citation_count = 0`.

## Why, and what it is worth

The system prompt requires every factual claim to carry a marker. An answer with no marker violates
that contract: nothing in it is anchored and the caller cannot check any of it.

Measured against a bounded judge over 48 items (`audits/2026-10-27-abstention-the-durable-fix.md`):

| predicate | TP | FP | FN | kappa |
|---|---|---|---|---|
| the harness's five substrings | 21 | **0** | 5 | 0.7938 |
| `citations.length === 0` | 23 | **0** | 3 | **0.8754** |

FP=0 is what licenses doing this in serving rather than only in evaluation: turning a useful answer
into a refusal is the worse error, and it did not happen once in 48.

⚠️ It does **not** close the gap. The three it misses cite a chunk **and** declare the context does
not explain the thing. That needs the model to return a field (`answered: boolean`), which means
changing the prompt, the parse and the retry path — deliberately not bundled here.

## Validation, before anything was applied

Run in a copy at `/var/tmp/abst-check` (src copied, `node_modules` symlinked), never in the serving
tree:

| gate | result |
|---|---|
| `tsc --noEmit` | clean |
| **mutation** — original `index.ts`, patched `types.ts`, new test kept | **fails**, on the exact assertion |
| patched | 3/3 pass |
| whole nox-mem suite, patched | 1770 tests · **1766 pass · 0 fail** · 4 skipped |
| baseline, clean tree | 1767 tests · **1763 pass · 0 fail** · 4 skipped |

⇒ **+3 tests, +3 passes, no existing test changed status.** The baseline was measured in a clean
tree on purpose: a baseline taken in a dirty build tree misattributes failures, which this
repository has paid for before.

## The new test, and why it had to exist

`__tests__/abstention-canonical.test.ts`. The 73 tests already in the module all passed against the
change, which means none of them reaches the new path — and a fix no test reaches is
indistinguishable from a fix never applied. Three cases: the mutation case, a case proving an answer
**with** a citation is untouched, and a case proving `retrieval_empty` stays distinct from
`model_abstained` even though both emit the same text.

The fixture shape is copied from `integration.test.ts`'s `fixtureChunks()`, not invented: the fields
are `file_path` and `content`, and a hand-written fixture using `source_file`/`chunk_text` threw
inside `assembleUserPrompt` on a field the prompt builder reads and the fixture did not carry.

## ⚠️ What applying this does to the item-8 baseline

The published abstention figures — negatives 0.6957, positives 0.2000, gap +0.4957 — were measured
through this same `answer()`. Once step 7b is live, those numbers describe the **pre-fix** system and
a re-run is not comparable to them. The harness keeps `abstainedSubstr` byte-identical so the old
predicate can still be computed, but the system it reads has changed. Any future comparison must say
which side of this change it is on.
