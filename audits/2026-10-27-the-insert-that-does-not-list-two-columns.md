# Two columns the distiller's INSERT does not list — 2026-10-27

Found while answering a different question: why `preference` generated no question at all in the
replay, for two days running. The answer is that **the replay's categories never came from the
memory** — they came from the question generator, which was given the distiller's own criterion.
The chunks carry no category in the column at all.

## Measured

```sql
SELECT memory_type, COUNT(*) FROM chunks WHERE source_file LIKE 'sessions/%' GROUP BY 1;
-- (null) | 6898        -- 100.0%
SELECT retention_days, COUNT(*) FROM chunks WHERE source_file LIKE 'sessions/%' GROUP BY 1;
-- (null) | 6898        -- 100.0%
```

`session-distill.ts:453` lists seven columns:

```sql
INSERT INTO chunks (source_file, chunk_text, chunk_type, source_date, metadata, tier, importance)
```

`memory_type` and `retention_days` are not among them, so every distilled chunk takes the column
default, which is NULL for both.

**The category is not lost, only misplaced.** It is written twice, in two places neither of which is
the column: as a prefix inside the text (`[${memory.category}|${agentId}] ${memory.text}`) and inside
the `metadata` JSON (`{"category":"context","source_agent":"nox","session":"…"}`). So
`UPDATE chunks SET memory_type = json_extract(metadata,'$.category')` reconstructs all 6,898 without
calling a model.

## What each omission actually costs

**`memory_type`: nothing today, because nothing reads it.** The only writer in `src/` is
`consolidate.ts:490` (`UPDATE chunks SET memory_type = 'decision' …`), which accounts for the 726
rows outside `sessions/%`. There is no reader: no search, ranking or brief query filters or weights
on it. `db.ts:710` calls it *"memory_type column for typed retrieval (Sprint 2)"* — the retrieval it
was added for never shipped. This is a column with a writer and **no reader**, the mirror image of the
`top_chunk_ids` case in rule 8, and it is why the loss has no symptom. It becomes a real loss the day
typed retrieval is built, and reconstructing it then is still free.

**`retention_days`: it silently makes every distilled chunk never-decay.** Following the consumer
rather than guessing, `salience.ts:58-71`:

```js
if (retention_days === null) { return 0; }      // resolveRetentionDays
...
if (retention_days <= 0) return 1.0;            // recencyComponent
```

NULL resolves to 0, and 0 means never-decay, so **the recency component is pinned at 1.0 for all
6,898 distilled chunks, permanently** — the maximum of a component worth 0.15 of the additive
salience formula, independent of age.

🔴 **And the codebase holds the opposite decision about the same column.** `db.ts:437-452` backfills
typed retention by `chunk_type` with `ELSE 90`, i.e. it wants distilled chunks to decay in 90 days,
and it is guarded by `WHERE retention_days IS NULL`. The 6,898 NULLs show which rule wins: the
backfill cannot reach a row inserted after it ran, and the INSERT's omission is permanent. The
effective behaviour is **accidental** — the same shape as the two snapshot pruners of the same
directory, where whichever ran last decided the retention and nobody had chosen it.

The comment at `salience.ts:67-68` shows NULL-as-never-decay *is* a deliberate choice, made so that
chunk types absent from `DEFAULT_RETENTION_BY_TYPE` ('other', 'digest') would not silently decay. The
distiller did not make that choice. It inherited it by not listing a column.

> **Not writing a column is a decision about behaviour.** `PRAGMA table_info` cannot tell a default
> that was chosen from a default that was inherited, and here the two readable intentions — the
> backfill's 90 days and salience's never-decay — disagree.

## Not fixed here

Both are serving changes and neither was touched. Recorded so the next person does not re-derive it:

1. `memory_type`: reconstructible from `metadata` with one `UPDATE`, no model. Worth doing **when**
   there is a reader, not before — writing a column nothing reads is what produced this entry.
2. `retention_days`: needs a decision first, not a patch. Should distilled memory never decay (what
   production does) or expire in 90 days (what the backfill intends)? Whichever is chosen has to be
   written in the INSERT, because a backfill guarded on NULL will never see tomorrow's rows.

Also recorded from the same investigation: **`preference` is absent from the generated questions
because the generator found no preference fact in the sampled prose windows**, not because the
builder drops the category. The distilled corpus cannot be checked for it by column — the label only
exists in `metadata` and in the text prefix.

---

## Addendum, same day — the retention decision, measured instead of argued

`audits/2026-10-27-retention-days-impact.py`, read-only, free. `NOX_SALIENCE_MODE` was read from the
serving process's own environment (`/proc/<pid>/environ`, found via the listening socket on :18802,
not by `pgrep -f`, which matched the probe's own command line) and is **`active`** — so salience does
move the ranking and the question is not academic.

**Control that could fail:** under the NULL scenario every distilled chunk must come out at recency
exactly 1.0, or the replica of `salience.ts` is wrong. 0 of 6,898 violated it.

| | NULL (today) | 90 days | change |
|---|---|---|---|
| median salience of a distilled chunk | 0.555 | 0.496 | **−0.082** |
| its percentile against the other 55,542 chunks | **97.7%** | **93.7%** | −4.0 pp |
| `promote` | 128 | 28 | −100 |
| `retain` | 6,770 | 6,016 | −754 |
| `review` | 0 | 854 | +854 |
| `archive` | **0** | **0** | **0** |

954 of 6,898 chunks (**13.8%**) cross a class boundary, and the mean change in the delta the search
path adds is **0.0706** on a scale that spans 1.0.

**So the effect is real and modest, and nothing is archived under either rule.** A distilled chunk
stays above 93% of the corpus whichever way it goes.

🔑 **Recommendation: do not change the behaviour — make it explicit, and remove the contradiction.**
Write `retention_days = NULL` in the INSERT with a comment saying never-decay is chosen, and drop
`distilled` from the `ELSE 90` branch of the `db.ts` backfill. Rationale: the measured gain from
switching to 90 days does not justify moving a served ranking, but two readable intentions that
disagree is what produces accidental behaviour — and the next person to open a **fresh** database
gets the backfill's 90 days, i.e. a system that behaves differently from production for a reason
nobody chose. Making it explicit costs one line and one comment and ends the divergence.
