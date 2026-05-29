# Wave B KG+MQ composability — recovery notes (2026-05-29)

> Companion to `RESULTS-WAVE-B-KG-MQ.md`. Captures the recovery flow after the
> original Wave B agent (id `a944f6f8c6acb6df6`) stalled on watchdog timeout
> while the VPS bench was still running, plus the lesson reinforcement on
> `[[agent-stall-on-multi-phase-pipelines]]`.

## Recovery timeline (BRT, 2026-05-29)

| Time | Event |
|---|---|
| 14:21 | Original agent staged `/tmp/wave-B-KG-MQ-BEFFB4E5-…/` + adapter + harness |
| 14:24 | Smoke runs OK (`phaseKGMQ-smoke-*`) |
| 14:29 | `tmux new-session -d -s kgmq-bench` dispatched `run-sequential-phaseKGMQ.sh` |
| 14:30 | Batch 004 started, port 18846 |
| 14:54 | Batch 004 done (rc=0); 005 started |
| ~15:10 | **Original agent killed by watchdog** (>10 min no stream output) |
| 15:09 | Batch 005 done (rc=0); 010 started |
| 15:28 | Batch 010 done (rc=0); 011 started |
| 15:46 | Batch 011 done (rc=0); 016 started |
| ~15:40 | **Recovery agent dispatched**, SSH diagnose: tmux still alive, 3/5 batches done |
| 16:06 | Batch 016 done (rc=0); `sequential.done` written |
| 16:08 | Recovery agent ran `aggregate-phaseKGMQ.py` on synced analysis files |
| 16:1x | RESULTS doc + this notes file + PR pushed |

## Bench state at recovery dispatch

```
ssh root@187.77.234.79 \
  ls -la /tmp/wave-B-KG-MQ-BEFFB4E5-7001-4788-BBC8-100E20C6C9E9/
```

- tmux session `kgmq-bench` still attached (PID 518290), bash script still
  iterating through `BATCHES=(004 005 010 011 016)`.
- 3/5 evermembench-runs/ dirs present (`phaseKGMQ-004/005/010-*`).
- Batch 011 child process (PID 528398) running `run-batch-phaseKGMQ.sh 011 18846`.
- No corruption, no port conflict, no DB damage.

**Decision:** wait, do NOT restart. The tmux session was self-driving and the
agent was the only thing that died — the bench was fine.

## Aggregation method

The aggregate script (`aggregate-phaseKGMQ.py`, pushed in the original branch
commit) imports `from eval.lib.aggregate_5batch import aggregate_5batch` +
`from eval.lib.report_template import generate_report`. Those modules don't
exist on the VPS workdir (only the staged adapter/harness files live there).

Workaround: pulled `analysis.txt` + `search-results-batch-*.json` from each of
the 5 evermembench-runs/ dirs back to the recovery clone, renamed dirs to
match the regex `phaseKGMQ-<batch>-<ts>` (used `-recovery` as the ts segment),
and ran the script locally where `eval/lib/` is present.

Files synced per batch:
- `analysis.txt` (≈3.7 KB) — drives the percentage-by-sub-dim tables.
- `search-results-batch-<id>.json` (≈19–20 MB) — drives MQ/KG firing rate
  + decompose/KG latency p50 + sample decompositions.

The full `nox-mem.db` (≈150 MB) + `answer-results-batch-<id>.json` were NOT
synced — those aren't needed for aggregate output.

## Composability verdict

**1 / 4 gates met → REJECT composability default.**

Highlights:
- **F_MH +4.81pp vs Phase H v2** (8.02% vs 3.21%). Beats Phase MQ alone
  (+1.20pp) — gate 2 PASS. But misses the +5.5pp additivity floor — gate 1
  FAIL.
- **Additivity residual −1.61pp**: combo (8.02%) underperforms the additive
  prediction (KG +2.81 + MQ +3.61 = 9.63). Mechanisms are not fully
  independent — there's a ~1.6pp interaction penalty when both fire together
  (90.8% of queries had both active).
- **Overall regression −0.85pp vs Phase MQ alone**: gate 3 FAIL by 0.35pp
  beyond tolerance.
- **MA composite −0.69pp vs Phase MQ alone**: gate 4 FAIL by 0.19pp beyond
  tolerance. MA_C dropped from 84.60% → 81.60% (−3pp), MA_P from 66.80% →
  62.80% (−4pp). KG entity boost crowds out top-K slots used by MA queries
  that prefer broader recall, and MQ subqueries already boost MA queries; the
  two overlap badly on MA_C / MA_P.

Recommendation: ship MQ alone (PR #385, 3/4 gates) as the default-opt-in
multi-hop knob. Document KG+MQ stack as a paper §5 nuance, not a deploy path.

## Lesson reinforced: `[[agent-stall-on-multi-phase-pipelines]]`

The original agent prompt included long blocking `wait` loops on
`sequential.done`. Watchdog kills agents with no stream output for >10 min,
but the bench produces stream output every ~15-18 min (per-batch). Same
trap as the previous Sat-D43 incident.

Recovery patterns that worked here (codified for future Wave-style benches):

1. **Pre-stage with tmux + done-file polling** is the right shape. The
   original agent did this correctly. The mistake was waiting inside the
   agent's own session.
2. **Recovery flow: SSH first, restart never.** Diagnose `tmux ls`, the
   process tree, and `evermembench-runs/` before touching the workdir. The
   bench survives the agent dying — no need to rebuild from zero.
3. **Pull, don't ship-from-VPS.** Aggregate locally where `eval/lib/` lives.
   Saves ~750 MB of `nox-mem.db` rsync and avoids running Python on the prod
   host.
4. **Future ergonomics:** ship `eval/lib/` to the WORK dir at setup time so
   aggregation can run on VPS in a single command at end-of-bench. (Skipped
   here because the recovery clone path was faster.)

## Files in this PR

| File | Source |
|---|---|
| `eval/evermembench/adapter_nox_mem.py` (39 LOC mod) | Original branch (commit 91d377a) |
| `eval/evermembench/aggregate-phaseKGMQ.py` (527 LOC) | Original branch |
| `eval/evermembench/run-batch-phaseKGMQ.sh` (194 LOC) | Original branch |
| `eval/evermembench/run-sequential-phaseKGMQ.sh` (93 LOC) | Original branch |
| `eval/evermembench/smoke-phaseKGMQ.py` (107 LOC) | Original branch |
| `eval/evermembench/RESULTS-WAVE-B-KG-MQ.md` | **Generated this recovery (auto-template)** |
| `eval/evermembench/RESULTS-WAVE-B-KG-MQ-RECOVERY-NOTES.md` | **This file** |

## Cost

- VPS compute: ~$0 marginal (1 nox-mem-api process on port 18846 + harness).
- LLM spend: ~$5.50 of the $6 budget (MQ decomposer × 3121 queries ×
  gpt-4.1-mini ≈ $0.0001/q + answer eval baselines).
- Already paid before recovery dispatched — recovery added only the
  aggregate Python run and the doc writing.
