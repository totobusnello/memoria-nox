# The net value of memory is negative, and the mechanism is see-once — 2026-10-27

**Two questions, one answer.** Yesterday's replay put the faithfulness tax at 52.3% and declared it
a floor, because the raw arm was an oracle: it received the window around the evidence, so it bounded
what naive RAG over the transcript would achieve rather than measuring it. The number the field's
papers report is a different one — a memory system against naive RAG — and we could not state it.
Separately, a 23× spread in chunks-per-block was reported as possible silent API failure.

Both were measured today. The spread was mine, and chasing it produced the mechanism that explains
the tax.

## Headline — memory loses to BM25 over the raw transcript, at identical context cost

Same 99 questions, same judge, same `ANSWER_SYSTEM`. Arm B receives **all** of the session's memory
units with no retrieval. The RAG arms receive chunks of the raw transcript retrieved by the question,
**truncated to the same number of characters arm B got** (`iso`), or a flat top-10 (`k10`).

| arm | correct | vs B | silent | contradicts |
|---|---|---|---|---|
| A — oracle window on raw *(not a result)* | 88.9% | — | 0.0% | 17.2% |
| **B — memory units, all of them** | **42.4%** | — | **49.5%** | 7.1% |
| bm25_iso — raw, equal budget | **63.6%** | **+21.2 pp** | 24.2% | 15.2% |
| dense_iso — raw, equal budget | **64.6%** | **+22.2 pp** | 18.2% | 20.2% |
| bm25_k10 — raw, ~15k chars | 78.8% | +36.4 pp | 10.1% | 17.2% |
| dense_k10 — raw, ~15k chars | 79.8% | +37.4 pp | 4.0% | 20.2% |

🔑 **The net value of the memory system on this corpus is −21.2 pp against BM25 and −22.2 pp against
dense retrieval, at equal context cost.** This is the Memory Tax paper's central finding —
*"many dedicated memory systems underperform naive RAG in many cases, indicating a negative net
value"* — reproduced on a production corpus rather than a benchmark, which is the gap no paper in the
2026-10-26 batch can close.

And it is not an artefact of giving RAG a bigger context. The equal-budget control is enforced in
code and asserts: chunks are admitted in score order only while they fit, the top one is truncated
when none does. Measured aggregate `retrieved/memory` = **0.954**; 2 of 99 pairs exceeded the budget,
by 4 and 6 characters, which is the `---` separator. The first smoke of this run gave the RAG arm
**3.56×** arm B's characters, and would have reported the budget as a finding.

## It gets worse exactly where the corpus is large

| final transcript prose | n | A | B memory | bm25_iso | net value of memory |
|---|---|---|---|---|---|
| < 50k chars | 52 | 90.4% | 53.8% | 63.5% | **−9.7 pp** |
| 50–200k | 7 | 71.4% | 42.9% | 71.4% | −28.5 pp |
| 200k–1M | 40 | 90.0% | **27.5%** | 62.5% | **−35.0 pp** |

The oracle holds at ~90% in both outer bands, so this is not the questions getting harder. Memory
falls from 53.8% to 27.5% while retrieval over the same text barely moves. The next section says why.

## The mechanism: the builder sees a session once and never returns

`session-distill.ts:141-144` skips any session already in the log:

```
const already = db.prepare("SELECT id FROM session_distill_log WHERE session_key = ?").get(sessionKey);
if (already) continue;
```

A live session is distilled the first time the cron reaches it, with whatever it held at that
instant, and is never revisited however much it grows. The archive keeps the **final** transcript.

Measured over the 684 sessions that hold both a log row and a raw transcript, splitting the prose by
turn timestamp at `processed_at`:

| final prose | n | median fraction the builder ever saw |
|---|---|---|
| < 10k | 644 | 100.0% |
| 10–50k | 31 | 100.0% |
| 50–200k | 3 | 72.1% |
| **200k–1M** | **6** | **24.0%** |

52 of 684 sessions (7.6%) were distilled while still growing. The band where the net value collapses
is the band where three quarters of the conversation was never offered to the builder.

**This is operational tax, not faithfulness tax** — the same family as the 259 transcripts never
logged at all, measured yesterday. It is invisible on a benchmark, where the builder receives the
corpus once, complete, with no window and no per-run ceiling.

## So yesterday's 52.3% was a floor contaminated by this

Each generated fact carries verbatim citations from the raw prose. A citation inside the visible
prefix was available to the builder; one only in the final prose was not.

| population | n | A | B | tax |
|---|---|---|---|---|
| placed | 85 | 88.2% | 48.2% | 45.3% |
| **evidence VISIBLE to the builder** | **77** | 89.6% | **53.2%** | **40.6%** |
| evidence arrived AFTER see-once | 8 | 75.0% | **0.0%** | 100.0% |

**The honest faithfulness tax is 40.6%**, and 8 of 85 questions were charged to construction for a
window it never saw. On that clean population the net value of memory is **−13.0 pp** against BM25
and −14.3 pp against dense.

⚠️ The control on this split is not clean: arm A differs by 14.6 pp between the two populations
(89.6% against 75.0%), on n=8. Two cases. The split is reported with that stated, not as settled.

## The category asymmetry survives, and sharpens

On the visible population:

| category | n | A | B | bm25_iso | B tax |
|---|---|---|---|---|---|
| **context** | 30 | 90.0% | **33.3%** | 70.0% | **63.0%** |
| decision | 23 | 82.6% | 60.9% | 60.9% | 26.3% |
| lesson | 24 | 95.8% | 70.8% | 66.7% | 26.1% |

🔑 **The builder keeps the lesson and loses the project detail.** `context` is file names, paths,
commands, a forbidden channel — and it is the only category where retrieval over the raw text beats
memory outright (70.0% against 33.3%). On `decision` and `lesson` the two are level. A compressor
that keeps what reads like an insight and drops the path is exactly what cannot guide an action, and
that is the mechanism behind two nulls already measured here: the agents do not search nox-mem, and
the brief does not guide the first action.

## The damage predicate, calibrated again on the arm that cannot fail

Arm A read the window the reference was written from, so it cannot contradict it. Its rate is the
false-positive floor of the predicate, not a result.

| arm | contradicts | reading |
|---|---|---|
| **floor (arm A)** | **17.2%** | impossible by construction |
| B — memory | 7.1% | below the floor → no evidence of damage |
| bm25_iso | 15.2% | below |
| bm25_k10 | 17.2% | at |
| dense_iso / dense_k10 | 20.2% | **above**, by 3 pp |

Nine of arm A's 17 flags carry `contem` **and** `contradiz` together, so the predicates are not
exclusive and the flag fires on difference of detail. Dense sitting 3 pp over a floor measured at
17.2% on n=99 does not establish damage either. **No arm is asserted to answer wrong.** The
silence-or-error question is still unanswered, for the second day, by the same calibration.

## What the 23× spread actually was

Reported yesterday: `9c75f331` produced 19 chunks over 316 blocks = 0.06/block, against `a35348df`
at 1.39/block. Hypothesis: silent API failure, since `distillWithGemini` has `return []` on five
distinct paths. The hypothesis is **refuted**, and the number was wrong in two places:

| | reported | measured |
|---|---|---|
| API failures | suspected | `provider_telemetry`: **495 calls, 0 failures**, `tokens_src='api'` on 100% |
| blocks in `9c75f331` | 316 (chars ÷ 2000) | **84** — the loop never splits a line, so a long turn is one oversized block |
| what the builder saw | 631,998 chars | **18,999 = 3.01%**, i.e. **4 blocks** |
| chunks per block | 0.06 | **4.75 per block it was actually given** — the system median is 5.0 |
| spread p90/p10 | 23× | **3.8×** on the right denominator |

The LLM did nothing unusual in that session. It was shown 3% of it.

**The blocking re-implementation is validated independently**: over the telemetry window, excluding
sessions with `message_count < 3` which never reach the LLM, this script computes **469** visible
blocks against **495** calls the provider recorded. Ratio 0.95.

Two mechanisms were ruled out on the way, both free:

- **the noise filter cannot be it.** `noise-filter.ts` rule 2 returns false for any text ≥ 500 chars,
  and the 240 learned prototypes hold **4 hits in total**.
- **the Groq fallback is a dead route.** `session-distill.groq`: **13 calls, 13 failures (100%)**,
  with `GROQ_API_KEY` present. And `distillBlock` selects it on `geminiResult.length > 0`, which
  collapses five causes of `[]` — no key, non-2xx, no text, unparseable JSON, and *the model
  correctly found nothing* — into one indistinguishable signal. A block with genuinely nothing to
  remember pays for a second provider call; a block that failed looks identical.

## Controls that fired, and what they caught

| control | what it caught |
|---|---|
| rebuilt prose vs `prose_chars` from replay-build | **20/20 mismatched** — the original joined turns with `\n\n`, I used `\n`. Off by N−1 chars per session, which would have moved every window offset. Fixed to the verbatim separator; now 20/20 exact |
| equal-budget assertion | the RAG arm receiving **3.56×** arm B's context in the first smoke |
| partition exhaustiveness | 502 of 1,186 sessions in no bucket at all |
| the label on that class | I called it "no prose" and the control refused the label: 3,248 prose-bearing events. They are **cron sessions** (`[cron:…]`, `HEARTBEAT_OK`), filtered by the distiller's own design — correctly excluded, wrongly named |
| sessions that ENDED before `processed_at` must be at 100% | 632 of them, 0 violations — the date handling holds |
| timestamp coverage per session | 0 sessions under 90%, so no fraction rests on undated turns |

## Limits

- **20 sessions, 99 questions.** Every figure here is a point estimate on that sample; the 200k–1M
  band is n=40 pairs over 6 sessions.
- **`preference` still generated no question at all** and remains untested, for the second day.
- **The RAG arms are not the product.** They retrieve over one session's transcript, which the live
  system cannot do: the raw transcripts are pruned at 7 days from the live directories and only the
  archive holds the past. The comparison establishes that the information survived in the raw text,
  not that a deployable retriever could reach it.
- **Retrieval recall bounds the RAG arms too**: in the 200k–1M band even `k10` brings the verbatim
  evidence only 85.0–87.5% of the time, so their tax against the oracle is partly their own recall.
- **The embedding cost was not measured** — those calls do not go through `tracked`. ~665k input
  tokens by character count.

**Cost.** Answers US$ 0.2187 and judging US$ 0.0318, both measured from the providers' own token
counts; smokes ~US$ 0.015; embeddings unmeasured as above. Everything else was free: the see-once
probe, the partition, the decomposition and this report read stored artefacts and a read-only
database.

**Artifacts.** `audits/2026-10-27-see-once-probe.py`, `-see-once-partition.py`,
`-decompose-see-once.py`, `-naive-rag-{build,answer,judge,report}.py`. Labels, answers and judge keys
stay on the host (`/root/medicoes/2026-10-26-memory-tax/`): the corpus is private and this repository
is public.
