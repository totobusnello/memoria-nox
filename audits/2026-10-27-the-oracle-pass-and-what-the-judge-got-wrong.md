# The oracle pass over the nine: the −14.1% is really −3.5%, and the judge was wrong on half of what it accepted — 2026-10-27

The morning's audit bounded the published PT-BR interval as **up to 14.1% optimistic**, because nine
queries with no gold ask about topics the corpus holds. This pass resolves the bound. It also found
two things that matter more than the number.

**Cost US$ 0.0264.** No search path was called: the pool is FTS5/BM25 over a read-only connection, so
no telemetry row was written and no `access_count` bumped.

## The number: −3.5%, not −14.1%

Of the nine, the deep pool (40 candidates by BM25 over the OR of the query's terms, judged one by one
by the bounded judge) plus a by-hand review of every proposal gives:

| verdict | n | queries |
|---|---|---|
| **gold accepted** | **2** | Q108, Q72 |
| gold accepted, marginal | 1 | Q52 |
| rejected — perishable question | 1 | Q79 |
| rejected — judge false positive | 1 | Q83 |
| stays a negative (false premise) | 1 | Q68 |
| negative, nothing in 40 answers it | 3 | Q49, Q85, Q89 |

| | published | 2 accepted (n=57) | with the marginal (n=58) |
|---|---|---|---|
| nDCG@10 strict | 0.2428 | **0.2343** (−3.5%) | 0.2302 (−5.2%) |
| nDCG@10 pooled | 0.5114 | **0.4935** | 0.4849 |

So the bound was right in direction and **four times too large in magnitude**: six of the nine are
not retrieval failures at all. Three are genuine negatives, one is a false-premise negative, one is
malformed, and one the judge got wrong.

## 🔴 The judge accepted three of six proposals that do not survive reading

Automating this pass would have put bad gold into the ruler. Each failure is a measured mode, not bad
luck:

| query | the judge's proposal | why it fails |
|---|---|---|
| Q83 *"como o KG é populado"* | `/root/.claude/.credentials.json` **populado** pelo `claude setup-token` (p=0.88) | matched the word *populado* in a sentence about credentials. Nothing to do with the knowledge graph |
| Q79 *"qual a versão atual do OpenClaw"* | `OpenClaw v2026.4.11` from a June digest (p=1.00) | **perishable**: a dated digest answers *what was the version in June*. A question about present state has no stable gold — the v1 decay failure in a new form |
| Q68 *"como resolver Sentence Transformer Issue 62028"* | a commit message naming Issue #62028 (p=0.74) | **false premise.** #62028 is the OpenClaw gateway fratricide, not a Sentence Transformer issue. The judge matched the issue NUMBER and let the premise through — the already-measured mode where an LLM judge cannot hold a negative |

Three of six accepted proposals wrong is a 50% false-positive rate on this task, from the same judge
that scores the retrieval interval. It is also the judge that correctly rejected a gold already **on
record** — see below — so this is not a judge that accepts everything.

## 🔴 Two of six accepted queries have invalid gold, found by the positive control

The control put six already-accepted queries through the same pipeline and required their recorded
gold to come back. **4 of 6 passed.** The two failures are not pipeline failures:

**Q99** — *"qual o limite máximo de chunks armazenáveis"*, gold anchor *"229 chunks = ~52k tokens
excede o limite do Groq"*. A diagnosis run (`2026-10-27-diagnose-control-failure-q99.py`) shows the
gold chunk was **at ranks 5 and 8** of the pool, so recall was fine: the judge saw it and rejected
it. And the judge is right — that is a per-call API limit for the digest, not a storage capacity.
**The recorded gold does not answer the recorded question**, and Q99 is one of the 55 accepted
queries contributing to the published nDCG.

This is consistent with 2026-10-26, where a second judge confirmed only **19 of 30** pre-registered
gold pairs. Q99 is a concrete instance of that 11.

🔑 **A positive control that fails because the known answer is wrong is the control working.** The
first version of this script treated a control failure as a hard gate and exited; it had to be
changed to report a *suspect gold* instead — but only after the diagnosis established that recall was
fine, because without that, "the pipeline is broken" and "the gold is wrong" look identical.

## And a correction to the instrument I built this morning

The first run marked **7 of the 9 as "bad question"** because a closed-book oracle answered them
without any context. The answers:

> *"A versão atual do OpenClaw é a 7.6."* — an internal system with no such version.
> *"Cross-search entre agentes permite que eles compartilhem e acessem informações uns dos outros."*
> *"Lex e Cipher se complementam em Incidents ao fornecerem diferentes perspectivas."*

**That is fabrication, not knowledge.** A closed-book filter is only valid where the model abstains
when it does not know, and this corpus's own abstention baseline already measured the model
fabricating on **17.4% of verified negatives, with citations attached**. Treating "the model produced
text" as "the model knows" would have discarded seven queries for being too easy, when the model was
making the answers up.

Fixed: the closed-book answer is **informative, printed beside each verdict**, and the pool decides.
It is worth keeping for the case it was built for — a genuinely generic question — but it cannot
carry a verdict on a corpus of internal systems.

## Delivered, and what needs a decision

`eval/gold-proposals-2026-10-27.jsonl` — all nine with verdict, confidence, the proposed anchor and
the reason. **Nothing was written into the ruler.** `golden-queries-v2.jsonl` is the artifact the
published interval was measured on, and the same rule that kept v1 untouched applies: a v3 is a
decision, not a side effect of this pass.

Open:

1. **Approve or amend the three accepts** (Q108 high, Q72 high, Q52 marginal) → that is the v3.
2. **Q99's gold is invalid and Q99 is inside the published 55.** Re-judging the other 54 against this
   judge costs about US$ 0.02 and would say how many more there are. 2026-10-26 suggests roughly a
   third.
3. **Q79 is malformed, not unanswerable.** A ruler cannot hold questions about present state; either
   rewrite it with an as-of date or drop it.

**Artifacts.** `audits/2026-10-27-oracle-pass-over-the-nine.py`,
`audits/2026-10-27-diagnose-control-failure-q99.py`, `eval/gold-proposals-2026-10-27.jsonl`.
