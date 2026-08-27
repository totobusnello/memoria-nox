# staged/health-probe-restart-loop

> **Restart storm, second edition.** `health-probe.sh` restarts `nox-mem-api` on a **single** failed 3-second curl, with **no debounce, no cooldown, and no circuit breaker** — the one service in the probe that lacks all three. The 2026-08-19 morning report (`🔴 restarted 4x in last hour`) is that policy firing, and the report cannot tell whether the probe or systemd did it, so it guesses: *"probe likely broken again"*.

This patch set makes the probe classify before it acts, bounds how often it may act, and writes down **why** it acted so the next morning report states a cause instead of a suspicion.

## What the 06:30 report actually told us

| Signal | Value | Reading |
|---|---|---|
| `restarts 1h` | 4 | ~4 of the 12 probes in the window restarted the API — **intermittent**, not the constant loop of 2026-04-18 |
| `chunks embedded` | 67024/67024, orphans 0 | API answered `/api/health` for `morning-report.sh` (5s timeout) at 06:30 |
| `canary` | `OK: total=10 semantic=8 fts=2` | API served `/api/search` at 06:00 |
| `query` write-path | 51× 1470ms avg | LLM-call telemetry (tokens + cost), **not** endpoint latency — does not bear on the probe's budget |
| `wal size` / `disk` / `429` | 4MB / 58% / 0 | no resource pressure, no quota wall |

So the service was **alive and serving on both sides of the window**. Four restarts of a service that works is the failure — each one kills writes mid-flight, which is exactly the damage mode of INCIDENTS `2026-04-18` (288 restarts/day, 6,627 orphaned rows, semantic search silently dead for weeks).

## Root cause: the policy, not the port

The Tier-0 fix of 2026-04-18 corrected the probe's *address* (`NOX_API_PORT` from `.env` instead of hardcoded `:18800`). It never corrected the probe's *judgment*. Lines 46–52 of the mirrored script are still:

```bash
if curl -sf --max-time 3 "http://127.0.0.1:${NOX_API_PORT}/api/health" > /dev/null 2>&1; then
    log "OK: nox-mem API port ${NOX_API_PORT}"
else
    log "WARN: nox-mem API not responding on ${NOX_API_PORT}, restarting"
    systemctl restart nox-mem-api 2>/dev/null
fi
```

Six defects, in the order they bite:

1. **One `curl` failure = one restart.** No confirmation. The `semantic-canary.sh` in the same directory debounces two consecutive failures *specifically because* "restart transitório do processo Node, ~30s de boot" — the probe that causes those boots has no such guard.
2. **3s timeout cannot distinguish "dead" from "busy".** `/api/health` counts and JOINs over ~95k chunks, walks `vec_chunk_map`, and shells out to `systemctl show` per service. Measured on prod 2026-08-19 it answers in **0.70s**, so 3s is not tight *today* — but it is the tightest budget in the fleet for the heaviest-shelling endpoint, and it is the only one wired to a restart: `morning-report.sh` allows 5s for the same endpoint, the canary allows 15s for search. Widening to 8s is cheap insurance; the classification below is what actually fixes the storm.
3. **Every failure mode is treated as death.** `curl -sf` fails identically for connection-refused (really dead), timeout (alive but blocked), and HTTP 5xx (alive, one subsystem broken). A restart fixes only the first, and actively harms the third by killing in-flight writes while the real fault stays.
4. **No cooldown, and it restarts into its own boot.** A cold start loads sqlite-vec over ~95k×3072d vectors and takes ~30s. Nothing stops the probe from hitting the service while `systemd` still reports `activating` and restarting it again.
5. **No circuit breaker.** The gateway stops after 3 restarts and alerts. The API — the service that owns the database — restarts forever, silently.
6. **No alert and no evidence.** The API branch never appends to `$ALERTS`, so no Discord message fires. It logs one line with no HTTP code, no curl exit code, no listener state. Six hours later the morning report has nothing to attribute the restarts to, which is why the alert text is a guess.

Two smaller bugs found in the same file, fixed here:

- **`--noproxy` (latent).** The Tier-0 fix added `set -a; . /root/.openclaw/.env`, which exports **every** variable in that file — including `http_proxy`/`HTTPS_PROXY`/`ALL_PROXY` if it ever gains one. `curl` honours those for `127.0.0.1` unless `NO_PROXY` happens to cover loopback, so adding a proxy line to `.env` would turn every probe into an instant restart. Worth ruling out on the VPS (step 1 below) as a candidate for *this* incident too.
- **Gateway breaker latched by unrelated checks.** The breaker is cleared only when `$FAILED -eq 0`, but `$FAILED` is also set by the SQLite and `node.real` checks. An unreadable DB kept the *gateway* breaker open even with the gateway perfectly healthy. Clearing now keys off gateway state alone.

## The new policy

| Observed state | Detection | Action |
|---|---|---|
| HTTP 200 | — | nothing; clear counter + API breaker |
| Fails once, passes on in-run retry (2s later) | — | nothing; logged as `recovered on retry` |
| Port not bound **and** unit not activating | `ss -tln` + `systemctl is-active` | **restart now** — nothing is listening, no writes to kill |
| Port bound, HTTP times out or errors | 2 consecutive probes (10 min at `*/5`) | restart |
| Unit `activating` | `systemctl is-active` | **never restart** — a boot in progress is what turns one bad probe into a storm |
| Process answers 4xx/5xx | curl rc 0 + code | **never restart** — a restart cannot fix a broken DB/schema; alert instead |
| Any of the above | 10-min cooldown since last restart | skip |
| Any of the above | >3 restarts in a rolling hour | **open API circuit**, alert, stop restarting |

Plus: timeout 3s → **8s**; one in-run retry; a readiness wait (up to 45s) after each restart so the *next* probe never lands on a booting process; and API failures now reach Discord at the time they happen.

Worst case goes from **12 restarts/hour, unattributed and silent** to **≤3, each with a written reason, then a latched breaker and an alert**.

### Evidence trail

Every restart appends one line to `/var/lib/nox-health/api-restarts.log`:

```
1755584820 2026-08-19T05:52:00+0000 hung http=000 rc=28
```

`morning-report.sh` reads that ledger and splits the journal count by cause, so the alert becomes falsifiable:

```
restarts 1h      : 4 (probe 2)
api circuit      : closed
...
🔴 nox-mem-api restarted 4x in last hour (probe 2 / self 2; last probe reason: hung http=000 rc=28)
```

`probe 0 / self 4` would mean the opposite diagnosis — systemd `Restart=on-failure` crash-looping or an OOM kill — and would have been mislabelled "probe likely broken again" by the old text.

## Files

| File | Prod path | Change |
|---|---|---|
| `edits/scripts/health-probe.sh` | `/root/.openclaw/scripts/health-probe.sh` | nox-mem-api block rewritten; gateway breaker clear fixed; `set -u`; paths overridable for tests |
| `edits/scripts/morning-report.sh` | `/root/.openclaw/scripts/morning-report.sh` | restart attribution (probe vs self), circuit line, reason in the alert |
| `edits/scripts/health-probe.test.sh` | — (repo only) | 27 assertions over the restart policy, fully stubbed (no network/systemd/DB) |

```
$ ./edits/scripts/health-probe.test.sh
  27 passed, 0 failed
```

Covered: healthy no-op · transient recovery on retry · first hung probe does **not** restart · second one does · cooldown · dead-process fast path · `activating` never restarted · 5xx never restarted · breaker opens at 3/h, stays open, clears on health · ledger entries older than 1h age out · gateway breaker no longer latches on unrelated failures.

## ⚠️ Before deploying: the mirror is 4 months stale

`scripts/vps-mirror/README.md` records the last sync as **2026-04-19**, and `docs/HANDOFF.md:256` shows the live script has since diverged — it lives in the `nox-scripts` repo (commit `3a723a8`), is `CHECK`-numbered (CHECK 10 = crontab line count), and runs **every 10 min**, not 5. These edits are written against the mirrored snapshot.

**So: port the nox-mem-api block into the live file, do not overwrite it wholesale.**

**And on a `*/10` cadence, set `NOX_PROBE_FAIL_THRESHOLD=1`.** This is not a style preference — `nox-mem-api` has a documented **event-loop freeze** failure mode (process `active`, port bound, HTTP mute) whose only cure *is* `systemctl restart`. Under the new policy that lands in `hung` → restart after N consecutive probes, so a threshold of 2 at `*/10` doubles the MTTR of that specific failure from ~10 to ~20 minutes.

The debounce is the **weakest of the three guards** and the only one that costs recovery time: with threshold `1`, the 10-min cooldown and the 3-restarts/hour breaker still cap the worst case at **≤3 restarts/h** (versus 12 today), and the classification still refuses to restart a booting or 5xx-serving process. Threshold `2` earns its keep on a `*/5` cadence, where 10 minutes of confirmation is cheap; at `*/10` it mostly buys a longer outage.

**What the probe deliberately does not do:** run `PRAGMA integrity_check` before restarting. Corruption is *exposed* by a restart, not caused by it, so the check belongs in the post-restart triage and in `withOpAudit()` — not inside a 5-minute cron probe, where a full check over ~95k chunks would blow the interval and become its own outage.

## Deploy

```bash
# 0) Which script is actually live, and on what cadence?
ssh root@<vps> 'crontab -l | grep -i health-probe; md5sum /root/.openclaw/scripts/health-probe.sh'

# 1) Rule out the proxy variable before changing anything (30s, and it would
#    explain 100% probe failure rather than 4/12 — check it anyway)
ssh root@<vps> 'grep -iE "^(http|https|all)_proxy|^NO_PROXY" /root/.openclaw/.env || echo "no proxy vars — not the cause"'

# 2) What did the restarts look like? (the answer this patch makes permanent)
ssh root@<vps> 'grep -E "nox-mem API|restarting" /var/log/nox-health.log | tail -40'
ssh root@<vps> 'journalctl -u nox-mem-api --since "24 hours ago" --no-pager | grep -E "Started|Stopping|Killed|oom|signal" | tail -40'
ssh root@<vps> 'systemctl show nox-mem-api -p NRestarts -p ExecMainStartTimestamp -p MemoryCurrent -p MemoryMax'

# 3) Measure the endpoint the probe judges on — is 3s actually tight?
ssh root@<vps> 'for i in $(seq 5); do curl -s -o /dev/null -w "%{time_total}\n" --noproxy "*" http://127.0.0.1:18802/api/health; done'

# 4) Back up, patch, verify syntax
ssh root@<vps> 'cp /root/.openclaw/scripts/health-probe.sh /root/.openclaw/scripts/health-probe.sh.bak-$(date +%F)'
scp edits/scripts/health-probe.sh root@<vps>:/root/.openclaw/scripts/health-probe.sh   # or port the block by hand
ssh root@<vps> 'bash -n /root/.openclaw/scripts/health-probe.sh && mkdir -p /var/lib/nox-health && chmod 0700 /var/lib/nox-health'

# 5) Dry run against a healthy API — must log OK and restart nothing
ssh root@<vps> 'bash /root/.openclaw/scripts/health-probe.sh; tail -8 /var/log/nox-health.log'
ssh root@<vps> 'systemctl show nox-mem-api -p NRestarts --value'   # unchanged from step 2

# 6) Same for the report
ssh root@<vps> 'cp /root/.openclaw/scripts/morning-report.sh{,.bak-$(date +%F)}'
scp edits/scripts/morning-report.sh root@<vps>:/root/.openclaw/scripts/morning-report.sh
ssh root@<vps> 'bash /root/.openclaw/scripts/morning-report.sh; tail -2 /var/log/nox-morning.log'
```

## Verification (next 24h)

- `grep -c RESTART /var/log/nox-health.log` over 24h → **0** while the API is healthy.
- `/var/lib/nox-health/api-restarts.log` → empty, or every line carries a reason you can act on.
- Tomorrow's 06:30 report → `restarts 1h : 0 (probe 0)` and `api circuit : closed`.
- If restarts persist with `probe 0 / self N`, the probe was never the cause — the fault is in the service (crash loop / OOM), and `journalctl -u nox-mem-api` now has the whole story instead of being drowned in probe-initiated stops.

## Rollback

```bash
ssh root@<vps> 'cp /root/.openclaw/scripts/health-probe.sh.bak-<date> /root/.openclaw/scripts/health-probe.sh'
```

State files are additive (`/var/lib/nox-health/*`) — the old script ignores them; delete the directory if you want a clean slate.

## Mirror

`scripts/vps-mirror/health-probe.sh` and `morning-report.sh` are deliberately **left untouched** in this patch set: per `scripts/vps-mirror/README.md` they are snapshots of what is running, and re-mirroring is step 3 of the deploy flow, not step 0. Re-`scp` them down and commit once this is live.

## References

- `docs/INCIDENTS.md#2026-04-18` — the first restart storm (port mismatch, 288 restarts/day, writes killed mid-flight)
- `docs/INCIDENTS.md#2026-08-19` — this recurrence
- `audits/sre-deepening-2026-04-18.md:11-21` — the original probe analysis; fixed the address, left the policy
- `scripts/vps-mirror/semantic-canary.sh:117-145` — the debounce pattern this patch brings to the probe
- `CLAUDE.md` §4 (`NOX_API_PORT`, never hardcode) and §6 (destructive ops need a safety net)
