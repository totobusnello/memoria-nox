# Trial start — Epoch 1 activated, 2026-09-01

> The serving path left `shadow` and entered `active` at **2026-09-01T10:25:39Z**.
> First treated brief: **10:37:01Z**. This file records the instant and the
> evidence, because "when did the trial start" is a fact a reader must be able to
> check, and a `systemctl` state is not evidence of it.

## What was switched

| | |
|---|---|
| unit | `nox-mem-api`, drop-in `zz-p2-active.conf` (8th of 8, loads last) |
| `NOX_P2_OUTCOME` | `shadow` → `active` |
| `NOX_P2_ASSIGNMENT` | `/root/.openclaw/paper2/ASSIGNMENT-SERVING.json` |
| sha256 | `8957cc5fe8696204c8a71416c0e1f89374d46f1f75db982c52067adbb43d625c` |
| restart | 2026-09-01T10:25:39Z, 0 restarts since |

Read from `/proc/<pid>/environ`, not from the unit file: a drop-in missing the
`[Service]` header disables silently while `systemctl is-active` keeps saying
`active` (lesson of 2026-08-19).

## Epoch 1 as served

Seven briefs in the 10:37Z cron burst, all seven identical:

```
epoch=2026-09-01  modo=active  servido=tratado  w=4  boosts=19  churn=0
```

`w = 4.0` matches the assignment for 2026-09-01 under drand quicknet round
31774052. `boosts=19` matches the number of signature groups in `p2_verdict`
(19 groups, 55 chunks): one designated chunk per group, which is the invariant
the unit test pins.

⚠️ **`churn = 0` in these seven is not a finding.** Shadow measured 3.74%
(151/4,037), so the expected count in 7 briefs is 0.26 — zero is the modal
outcome. Churn becomes a question only over days, not over one burst.

## Two operational facts worth recording

**The epoch boundary is 09:00 UTC, not midnight.** `epochInicioISO`
(`src/paper2/brief-outcome.ts:420`) rolls the epoch at 09:00Z = 06:00 BRT. At
07:08Z on 2026-09-01 the current epoch was still `2026-08-31`, a date absent
from the assignment sequence; switching then would have returned
`epoch 2026-08-31 ausente da sequência` and served **control on every brief for
1h52**, while `systemctl is-active` reported `active`. Activation was therefore
held until after 09:00Z. Confirmed empirically before switching: the 07:07:06Z
log line reads `epoch = 2026-08-31`.

**`/api/brief` is called in bursts, not continuously.** The caller is
`7,22,37,52 * * * *` — four bursts per hour of ~7 briefs each, which reconstructs
the observed 672/day. An 8-minute verification window opened at 10:25 contained
no burst and returned zero new lines; that was the wrong window, not a fault. A
mean rate does not license expecting an event inside an interval shorter than the
generator's period.

## Not established here

- Nothing about effect. Epoch 1 is one epoch of 234; the design runs to
  2027-04-22.
- Nothing about churn under treatment. n = 7.
- The Gemini embedding quota returned `429 RESOURCE_EXHAUSTED` with backoff at
  10:22Z, before the restart. Non-fatal and unrelated to the switch, but it
  touches semantic search and is open.
