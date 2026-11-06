# C2 in shadow beside the production distiller: protocol

Written 2026-11-06, after the Paper D note, before the shadow was turned on. Approved by the author
on 2026-11-06 («faca de 4 a 7», item 4: C2 in production, in shadow). This is a collection
protocol. It fixes what is recorded and how the run is bounded; it does not fix an analysis. Any
study read from these records gets its own pre-registration, tagged before anything beyond the
counts in §5 is read.

## 1. Why

Paper D asked whether criterion C2 extracts a more useful memory than the deployed C0 from
production sessions, and could not answer: its offline replay rebuilt the input and kept the
scheduled-job prompts that production drops, so the fidelity control failed (`NOTE.md` §4). A
shadow beside the deployed distiller removes that failure mode by construction. Each C2 call reads
the exact block production just sent to its model, after production's own parser, noise filter and
block split.

## 2. What runs

Code: `tools/nox-mem/src/distill-shadow.ts` on the production host, called from
`session-distill.ts` (host commit `ac642951`). For every block production distils, after
production's own call, dedup and ingest for that block:

- one Gemini call, model `gemini-2.5-flash-lite`, temperature 0.1, JSON response, the same request
  shape as production's;
- prompt C2 = production's prompt with Paper 3's identifier and event paragraphs inserted before
  the JSON anchor. The module computes it from the deployed C0 prompt and refuses to run unless its
  sha256 equals Paper 3's `DISTILL_SYSTEM_V3`
  (`325342a36e742f1e844b7c3792dae3eb47a76879c501678b576cd6df2cc8089d`);
- units with importance below 0.5 dropped, as production does. No Groq fallback, no dedup.

It runs inside both callers of the distiller: the weekly Sunday run and the daily end-of-day step
(`DISTILLER-SCHEDULE-2026-11-06.json`).

## 3. What is recorded, and where

One JSON line per block, appended to `c2-shadow-<UTC date>.jsonl` in a private directory on the
production host (directory mode 700, files 600). Each line carries the session key and agent, the
block index and count, the session's message count and file time, the block text and its sha256,
production's C0 units for that block as its distiller returned them (before dedup), and the C2
units with the model version, token usage, and error, if any.

The block text is private corpus text. It stays on the host, is never copied into this repository
or sent to any service other than the call above, and is deleted when the study that uses it is
closed, or on 2027-06-30, whichever comes first. The host is not named in this repository.

Nothing is ingested and no memory is written to the database. The one database write is the
provider-cost row that every tracked call makes, under caller `session-distill.shadow-c2`, so the
shadow's spend shows in the same ledger as production's.

## 4. Bounds and switch

- On only while a file named `ENABLED` exists in the shadow directory. Removing it turns the shadow
  off at the next run, with no deploy and no restart.
- Off by itself from 2027-01-11, a date fixed in the code.
- Per run: at most 300 shadow calls and 15 minutes of shadow time. Blocks over either cap are
  counted, not called.
- Off in `--dry-run`, and without an API key.
- A shadow failure (HTTP, parse, write) is counted in the log and never raised into production's
  loop. Production's own calls, dedup, ingest and log rows are unchanged.

Expected volume, from the distiller's log from 2026-09-13 to 2026-11-06: about 28 sessions a week
reach the model, so the window to 2027-01-11 should collect on the order of 250 sessions. At
flash-lite list prices that is well under US$ 1.

## 5. Monitoring

Each run prints `[DISTILL-SHADOW] C2 shadow on|off (<reason>)` and, when on, `Done: <calls> C2
calls, <failed> failed, <skipped> blocks over the cap`. The weekly run's lines land in the nightly
maintenance log; the daily run's in the end-of-day agent's output. Before any study is
pre-registered, only these counts may be read: sessions, blocks, calls, failures, skips and cost.

## 6. What a study from these records can and cannot say

It can compare C0 and C2 on production's own input, block by block, with C0 being what production
actually extracted. It cannot say what C2 would do once ingested, because C2 units never enter the
database, the dedup, the brief or retrieval. Questions for such a study would have to be written
from the recorded blocks, which contain no scheduled-job prompts because production's parser
already removed them.
