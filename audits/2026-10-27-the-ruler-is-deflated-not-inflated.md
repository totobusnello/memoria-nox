# The ruler is deflated, not inflated: 27.3% of its scored queries have gold that does not answer them — 2026-10-27

This morning's audit bounded the published PT-BR interval as **up to 14.1% optimistic**, from nine
queries excluded with no gold. The oracle pass cut that to **−3.5%**. This audit looks the other way
— at the gold that *is* on record — and finds a larger error in the opposite direction.

**Cost US$ 0.0098**, 152 judgements, no search path called.

## 60% of recorded gold entries do not answer their own question

Every one of the 95 gold entries of the 55 accepted queries was judged against its own query by the
bounded judge, on the resolved **chunk** (not the 160-char anchor, because the ruler scores chunks).

| | |
|---|---|
| gold entries accepted | **57 of 95 = 60.0%** |
| gold entries rejected | **38** |
| **queries whose EVERY gold entry is rejected** | **15 of 55 = 27.3%** |

Those 15 score **zero by construction in the strict arm, whatever the system returns.** Excluding
them: strict nDCG@10 **0.2428 → 0.3338, +37.5%**.

🔑 **So the two errors run in opposite directions and the second is far larger.** Including the two
new queries costs −3.5%; excluding the 15 whose gold is invalid gains +37.5%. The published strict
figure is **deflated**, not inflated — the system is being punished for not returning chunks that do
not answer the question.

And 27.3% matches the independent reading from 2026-10-26, where a second judge confirmed only 19 of
30 pre-registered gold pairs — 36.7% rejected, by a different instrument on a different subset.

## The three controls, all of which pass

A rejection rate on its own is a fact about the judge.

| control | result | reading |
|---|---|---|
| **negative** — each query against a RANDOM chunk | accepted **1.8%** of 55 | the judge does not accept noise, so 60% is not blind severity |
| **positive** — the two gold entries built today from the oracle pass | accepted **100%** of 2 | the judge has not drifted from the predicate that proposed them |
| **anchor** — the judged text is the resolved chunk, not the anchor string | by construction | judging the anchor would measure its wording, not the gold |

The signal is **58.2 pp above the judge's floor**.

## Hand-check: the judge is right 4 times in 6, and severe twice

A rate is not a verdict, so six of the fifteen were read in full:

| query | the recorded gold | call |
|---|---|---|
| Q51 *"o que é monkey-patch fratricide"* | the frontmatter **tags** line: `tags: [openclaw, gateway, systemd, fratricide, monkey-patch, issue-62028]` | 🔴 judge right — names the subject, explains nothing |
| Q55 *"como fazer backup pre-op atomico"* | `Backup do crontab: /var/backups/crontab.pre-nox-vectorize-lock-...` | 🔴 judge right — a record that a backup happened, not the procedure |
| Q58 *"o que é shadow-mode e por quê obrigatório"* | `Fase 1.7b-b — Salience formula shadow-mode (schema v9)`, inside a list of completed phases | 🔴 judge right — the term in a list |
| Q64 *"como funciona o cron quarterly DR drill"* | `Quarterly cascade testing`, inside *Recommendations for Next Session* | 🔴 judge right — three words in a list |
| Q57 *"como gerar entity file no formato compiled+timeline"* | the `memory-recompile` skill's description, which says it recompiles the compiled-truth section **from its timeline** | ⚠️ **judge severe** — names the tool that does exactly this; a partial answer |
| Q61 *"como ativar section_boost"* | `Override section_boost timeline 0.8→1.4 em queries temporais` | ⚠️ **judge severe** — shows the value being set; *"como ativar"* asks for a procedure, so defensible either way |

⇒ **27.3% is an upper bound.** Scaling by the hand-check gives roughly **18–27%** of scored queries
with invalid gold, and the +37.5% correspondingly **+25% to +37.5%**. Reported as a range, because
that is what six hand-checks support.

## 🔑 The mechanism, which matters more than the number

Every clear failure has the same shape: **the anchor landed on a MENTION of the term — a tags line, a
phase list, a recommendations list, a title — instead of on the text that answers.** The v2 repair
chose anchors by whether they contained the query's terms, and term containment is not answering.

That is the same defect as the 8-word citation check (retired yesterday for partitioning on
formatting) and of the judge matching *"populado"* in a sentence about credentials this morning: a
lexical proxy standing in for a semantic property.

⚠️ **And I committed it again today, in this very frontier.** The oracle pass's `anchor_of()` picks
the line with the most query terms:

```python
lw = set(terms(line));  sc = len(ws & lw)
if sc > score: best, score = line, sc
```

That is exactly the rule that produced the bad anchors it was built to find. The two gold entries it
proposed happen to be correct — I read them — but the selection rule is wrong and would produce the
same class of defect at scale. **Anchors must be chosen by the judged span, not by term overlap**:
the resolved chunk is already judged, so the anchor should be cut from the sentence the judge's
probability rests on.

## What this changes

- **Do not quote 0.2428 as the strict lower bound without this.** The honest statement is that the
  strict arm is computed over 55 queries of which **15 cannot be answered by any system**, so it
  reports retrieval failure where the defect is the ruler.
- **The interval needs rebuilding, not adjusting.** Both ends move: the 9 add −3.5%, the 15 add
  +25–37.5%, and they are not independent of the pooled arm either.
- **The anchors need re-cutting by a semantic rule**, for the 38 rejected entries and for the
  selection code. That is a v3 of the query set, and a decision.
- **`decision` gold is sound and `procedure`/`temporal` gold is not**: rejection runs 9.1% on
  `decision` against 50% on `procedure` and `temporal`, 48% on `concept`. A ruler that is reliable
  for one category and not another cannot carry a per-category table — and the published one has
  six categories.

**Artifacts.** `audits/2026-10-27-does-the-recorded-gold-answer-the-question.py`,
`audits/2026-10-27-inspect-rejected-gold.py`. Labels stay on the host
(`/root/medicoes/gold-audit-2026-10-27.json`).
