# Faithfulness tax on a live corpus: the QA replay — 2026-10-26

**Question.** The Memory Tax paper (published 2026-10-26) decomposes the net value of an agent
memory system against naive RAG, and its *faithfulness* axis asks what the construction step
discards before any retrieval. The portable method is: mark the gold raw turns and the gold memory
units per query, then replay the QA with one and with the other. The difference is construction
tax, not search tax. This is that replay, run on our own production corpus.

**Headline.** Over 99 questions whose answer the raw transcript demonstrably contains, the
distilled memory answers **42.4%** against the raw side's **88.9%** — a faithfulness tax of
**52.3% relative**. It is a **floor**, for the reasons under Limits.

And the tax is not spread evenly. It falls almost entirely on one of the four categories the
builder itself declares it keeps.

## Design — and the two choices that decide whether the number means anything

**The questions come from the raw side only.** Anchoring them on what survived would manufacture a
null by selection, which is what rotted the PT-BR golden set (61 of 85 chunk ids dead, and the
surviving anchors biased toward what the pipeline kept).

**The asking criterion is the builder's own, copied verbatim** from `DISTILL_SYSTEM` in
`src/session-distill.ts`: decisions, user preferences, lessons learned, relevant project context,
`importance >= 0.5`. This matters more than it looks. The median session compresses to **10.8%** of
its prose, and a summariser that drops 89% of the text is *working*. It owes an answer only about
the class of fact it promised to keep; asking about anything else measures my preference, not its
faithfulness.

| | |
|---|---|
| sessions | 20, stratified by produced memory (pools of 52 / 120 / 18 / 4) |
| windows | 30 of 20,000 chars (10 removed as exact duplicates — see Defects) |
| questions generated | 117; 104 kept (13 had no verifiable citation) |
| arm **A** | answer using the raw evidence window (±1,500 chars around the citations) |
| arm **B** | answer using **all** of that session's distilled chunks, **no retrieval step** |
| answerer | `gemini-2.5-flash-lite`, temperature 0, both arms, `NAO SEI` permitted |
| judge | OpenAI Decisions API, `gpt-6-luna` — a different family, and no free-text field |
| cost | **US$ 0.13** all in (generate 0.051, answer 0.052, judge 0.016, smokes 0.012) |

Arm B getting **100% of the session's units with no retrieval** is deliberate: it removes
accessibility tax by construction, so what remains is construction tax alone.

## Result

| | contains the fact | contradicts it | silent |
|---|---|---|---|
| **A — raw turns** | **88 = 88.9%** | 17 = 17.2% | 0 |
| **B — memory units** | **42 = 42.4%** | 7 = 7.1% | 48 = 48.5% |

**Arm A is the positive control, and it is also the population filter**: 5 of 104 questions were
dropped because the raw evidence could not answer them, before anything was compared. Its 88.9%
is not 100%, and the missing 11.1% is instrument noise, not memory.

### The tax is concentrated in `context`

| category | n | A | B | tax (relative) | B silent |
|---|---|---|---|---|---|
| `lesson` | 28 | 92.9% | 60.7% | **34.6%** | 25.0% |
| `decision` | 29 | 82.8% | 48.3% | 41.7% | 37.9% |
| **`context`** | 42 | 90.5% | **26.2%** | **71.1%** | **71.4%** |
| `preference` | 0 | — | — | — | — |

🔑 **The builder keeps lessons and loses project detail.** Of the 42 cases where the raw side
answers and the memory is silent, **27 are `context`** — file names, paths, commands, which
delivery channels are forbidden. A lesson is self-contained and reads as insight, so it survives
extraction; `active-tasks.md` and `session-context.json` do not.

That lands on top of two results already in this repository: the VPS agents do not search nox-mem
at all (100% of searches were canaries), and the brief does not guide a first action (3 of 28, and
0 of 10 on the decisive cases). A memory holding insights but not file names, paths or commands
cannot guide an action even if something did read it — this is a mechanism for those nulls, not
another instance of them.

### Two predictions of mine that the data refused

**1. The 2000-char block was NOT the mechanism.** `BLOCK_SIZE = 2000` with no overlap
(`session-distill.ts:375, 402-413`) means each LLM call sees one block and nothing else, so I
predicted that facts whose evidence spans more than 2000 characters would be lost at a higher
rate. They are not:

| evidence span | n | A | B | tax |
|---|---|---|---|---|
| < 2000 | 87 | 89.7% | 42.5% | 52.6% |
| 2000–4000 | 8 | 100% | 62.5% | **37.5%** |
| > 4000 | 4 | 50.0% | 0% | — (A too weak to read) |

The middle band has **less** tax, the opposite direction, and the top band has n=4 with arm A at
50%, which cannot carry a reading either way.

**2. Distributed evidence does BETTER, not worse.** Facts that only exist by joining two distant
parts of the window: tax **41.4%**, against **57.6%** for local facts (n=33 and 66). Also the
opposite of the prediction. A plausible reading — a fact stated twice in a conversation is a fact
the conversation cared about, so it survives extraction more often than a detail mentioned once —
but that is a hypothesis, not a measurement.

### Tax falls as the session produces more memory, non-monotonically

| units the session produced | n | A | B | tax |
|---|---|---|---|---|
| 1–5 | 7 | 100% | 14.3% | 85.7% |
| 6–15 | 10 | 90.0% | 20.0% | 77.8% |
| 16–60 | 53 | 86.8% | 50.9% | **41.3%** |
| 61+ | 29 | 89.7% | 41.4% | 53.8% |

## The judge's own `contradiz` predicate is reproved, by a control inside the run

Arm A answered using the very window the reference answer was extracted from, so **arm A cannot
genuinely contradict the reference**. Its contradiction rate is therefore a negative control:

| | flagged as contradicting |
|---|---|
| arm A — impossible by construction | **17.2%** ← false-positive floor |
| arm B | 7.1% |

B is **below** the predicate's own noise, so **there is no evidence of damage** — no finding that
the memory answers confidently and wrongly. And 9 of A's 17 flags (53%) scored `contem` *and*
`contradiz` together: the two predicates are not exclusive, and the flag is firing on difference of
detail. Reading the 7 B flags by hand confirms it — one of them is reference *"O pacote
`typing_extensions` faltava. A versão instalada foi a v3.1.0"* against candidate *"Faltava o pacote
`typing_extensions`. A versão instalada do `fast-flights` foi a v3.1.0"*, which is the same fact.

So the question that mattered most going in — does the memory *lie*, or merely fall silent? — comes
back **unanswered**, because the instrument built for it does not work. What is measured is
silence: 48.5% of B, and 47.7% of everything the raw side can answer.

## Defects found and fixed mid-run, all by controls rather than by inspection

**The prose extractor was losing the raw side, which hides tax.** Compression came out above 100%
in four sessions — distilled output larger than the prose it came from, which is impossible. Two
causes: a turn *matching* a noise pattern was rejected whole, but the user's real message follows
the `Conversation info: ⟦openclaw:ctx⟧` + JSON envelope, so one session dropped 315,527 of 361,603
characters; and the archive holds two schemas, with `session-distill.ts:190` accepting
`type: "message"` (legacy OpenClaw) while the extractor accepted only `user`/`assistant`.
Envelopes must be **cut out of** the text, never used to reject it. After the fix: 0 sessions above
100%, median compression 10.8%, and that session back to 349,560 characters.

**`start` and `middle` windows were byte-identical** for any session under 20,000 characters of
prose, which would have inflated n with repeated questions carrying no new information. 10 of 40
windows were duplicates.

**An output ceiling reads as "this window held no facts".** Without `maxOutputTokens` the generator
looped and returned 170 KB of unterminated JSON; with a ceiling of 4,000 it returned *guaranteed*
truncated JSON on 10 windows. Fixed by raising it to 8,192 **and** parsing tolerantly — balanced-brace
scanning recovers the complete facts before the cut, because discarding the reply attributes a fact
about the ceiling to the corpus.

**The judge's envelope key is `answers`, not `questions`.** With the wrong key every predicate read
as absent, absent read as probability 0, and the first smoke printed **arm A at 0.0% correct** — a
perfect tax produced entirely by a parser bug. Arm A being impossible-to-fail is what caught it.
`pull()` now raises on an envelope without the predicates instead of returning an empty dict.

## Limits

- **Arm A is an oracle, not a retriever.** It receives the window around the evidence, so it is an
  upper bound on what naive RAG over the raw transcript would achieve. Comparing to the paper's
  figures would need a real retrieval step on the raw side; against a real retriever the gap would
  be smaller. This is the main reason the tax is a floor.
- **The question, the reference answer and both answers come from the same model family**
  (`gemini-2.5-flash-lite`). The judge is a different family, which is the part that matters most,
  and the shared answerer affects both arms equally — but a question phrased by the same model that
  answers it is easier than a human's question.
- n=99 over 20 sessions, one run. Cells below n=15 (`> 4000` span, `1-5 units`, the `few` stratum)
  are reported for shape and carry no interval.
- Sessions of 600,000+ characters are represented by two 20,000-char windows, so the large
  sessions are sampled thinly and their tax is measured on a small part of their content.
- `preference` produced zero questions; the category is untested.
- The 2000-char block hypothesis is **unsupported**, not refuted: the span cells that would test it
  hold 8 and 4 items.

## What this changes

- **We can state a faithfulness tax on a production corpus: 52.3% relative, a floor.** No paper in
  the 2026-10-26 batch measures one outside a bench.
- **The actionable finding is the category skew, not the headline.** `context` at 71.1% tax with
  71.4% silence is where to intervene, and it is the category an agent needs in order to *act*.
- **Do not claim the memory fabricates.** The instrument for that was built, run, and reproved by
  its own negative control.
- Taken with the construction probe (`2026-10-26-construction-tax-probe.md`), the two tax
  components now have numbers from different instruments: **operational** — 259 transcripts holding
  4.5M characters of prose never offered to the builder — and **faithfulness** — 52.3% of what the
  raw side answers, lost in extraction.

**Artifacts.** `audits/2026-10-26-replay-{build,generate,answer,judge,report}.py`. The question set,
answers and labels stay on the host (`/root/medicoes/2026-10-26-memory-tax/`): the corpus is private
and this repository is public.
