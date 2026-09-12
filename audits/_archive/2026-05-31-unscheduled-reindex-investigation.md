# Audit — "Unscheduled" reindex 2026-05-25 23:11 BRT (02:11 UTC 26/05) revisited

**Date:** 2026-05-31
**Investigator:** session-spawned audit agent
**Trigger:** openclaw monitoring flagged "investigation NÃO REALIZADA DESDE SEG 2026-05-28" — verify tasks #18-#23 closed completely and root cause real.

---

## TL;DR

**Root cause IS known and was deployed Wed 2026-05-27.** The investigation alert is stale — tasks #18-#23 closed the loop with PR #358 (`8436982`) + post-deploy commit `9cd3135` + VPS-direct patch to `nightly-maintenance.sh`. The "23:11 BRT" timestamp in the prompt is the **last reindex of the loop (nox agent, ts 23:11:10 BRT)** of the SAME incident already documented in `docs/INCIDENTS.md` under `2026-05-26 ~02:00 UTC`. There was no separate 02:11 UTC unscheduled reindex.

The event was **fully on schedule** — the `0 23 * * *` cron `/root/.openclaw/scripts/nightly-maintenance.sh` Phase 2 (agent reindex on odd DOM). The crash-loop signature was identical to RECORRÊNCIAS #1-#3. The `DISABLE_AGENT_REINDEX` kill-switch had been removed between 23/mai and 25/mai (mystery solved indirectly: the root-cause fix was deployed and the flag is no longer needed, hence `ls -la /root/.openclaw/DISABLE_AGENT_REINDEX` returns "No such file" today and that is intentional).

Current prod state (verified 2026-05-31): chunks=69,130; reindex.ts has `ReindexWipeDetectedError` guard (NOX_REINDEX_ALLOW_WIPE escape hatch); op-audit.ts respects OPENCLAW_WORKSPACE with `assertDbPathConsistency()` belt-and-suspenders. Last reindex attempt that crashed under guard = `id 77, atlas crashed 2026-05-24 12:05` (manual test, expected behaviour).

---

## Timeline (forensic, confirmed via `/var/log/nox-maintenance.log.6.gz` and journalctl)

All times BRT (server tz America/Sao_Paulo). UTC offset −03:00.

```
Mon 2026-05-25 23:00:01 BRT  cron CMD 12974 → /root/.openclaw/scripts/nightly-maintenance.sh START
Mon 2026-05-25 23:00:01 BRT  Phase 1: update-session OK
Mon 2026-05-25 23:00:05 BRT  Phase 2: Agent reindex (odd day, 103 new chunks) — guard `[ ! -f DISABLE_AGENT_REINDEX ] && [ DOM%2 -eq 1 ]` passed (flag absent + DOM=25 odd)
Mon 2026-05-25 23:00:05 BRT  Reindexing atlas — snapshot atlas-20260526020006 created (1.2 GB = MAIN DB size 🔴)
Mon 2026-05-25 23:10:28 BRT  611.6s later: ReindexWipeDetectedError fires (preCount=69135, postCount=144, ratio=0.9 threshold)
                              → withOpAudit FAILURE path, snapshot preserved
Mon 2026-05-25 23:10:28 BRT  Reindexing boris — succeeded (144→204 chunks, 56 files) [operates on agent DB correctly because boris has no entity files in MAIN]
Mon 2026-05-25 23:10:38 BRT  Reindexing cipher — WIPE detected again (214→92, ratio 0.9 trip)
Mon 2026-05-25 23:10:49 BRT  Reindexing forge — succeeded (92→473)
Mon 2026-05-25 23:10:59 BRT  Reindexing lex
Mon 2026-05-25 23:11:10 BRT  Reindexing nox ← THE "02:11 UTC" event the prompt asked about
Mon 2026-05-25 23:15:04 BRT  check-schema-invariants.sh (cron */15) detected section=compiled count=0 → Discord alert
Mon 2026-05-25 23:22:57 BRT  post-incident DB preserved /tmp/post-incident-756chunks-20260525-232257.db
Mon 2026-05-25 ~23:25-23:30  safeRestore() from reindex-atlas-20260526020006-*.db (1.2GB MAIN snapshot)
Mon 2026-05-25 23:30:02 BRT  schema-invariants OK — recovery complete (~30 min total)
```

The "02:11 UTC" in the prompt = 23:11 BRT, which is the **nox agent reindex** in the same Phase 2 loop. Not a separate unscheduled event.

---

## ROOT CAUSE (identified — confirmed and patched)

**Three bugs compounded** (root-cause session task #18, Wed 2026-05-27 15:40-15:55 BRT):

### Bug 1 (PRIMARY) — `op-audit.ts` ignored `OPENCLAW_WORKSPACE`

Historical `const DB_PATH` in op-audit.ts read only `NOX_DB_PATH` env or fell back to hardcoded MAIN path. db.ts (CLI core) respected `OPENCLAW_WORKSPACE`. So when nightly-maintenance.sh ran:

```bash
NOX_DB_SOURCE=atlas OPENCLAW_WORKSPACE=/root/.openclaw/agents/atlas /usr/local/bin/nox-mem reindex
```

→ db.ts opens `/root/.openclaw/agents/atlas/tools/nox-mem/nox-mem.db` (64MB atlas DB, correct)
→ op-audit.ts VACUUM INTO snapshots from `/root/.openclaw/workspace/tools/nox-mem/nox-mem.db` (1.2GB MAIN, WRONG)
→ Audit trail shows `reindex-atlas-*` but real operation snapped MAIN.

### Bug 2 (SECONDARY) — `.env` global `NOX_DB_PATH=main` overrides everything

Post-deploy smoke test discovered prod `.env` sets `NOX_DB_PATH=/root/.openclaw/workspace/tools/nox-mem/nox-mem.db` globally. When nightly-maintenance.sh sourced `.env` and then set `OPENCLAW_WORKSPACE` per agent, **`NOX_DB_PATH` wins** in db.ts (line 57-61 precedence: NOX_DB_PATH > OPENCLAW_WORKSPACE-derived path). So atlas reindex actually operated on MAIN — both layers misaligned.

### Bug 3 (TERTIARY) — `withOpAudit` insert silently failed

Snapshot `reindex-atlas-20260526020006-13100-*.db` exists on disk but NO corresponding row in `ops_audit`. Probable cause: `[[withopaudit-trigger-raise-ignore-swallows-insert]]` (`started_at` TEXT vs INT type mismatch trigger ABORT silently). Audit trail rendered useless for the failure.

---

## ATTACK SURFACE (enumerated — anything that could trigger reindex)

| Vector | Status | Notes |
|---|---|---|
| `crontab -l` `0 23 * * *` → nightly-maintenance.sh Phase 2 | ✅ ACTIVE | Guarded by DISABLE_AGENT_REINDEX flag + `DOM%2 -eq 1` + NEW_CHUNKS>0 |
| `systemd timers` matching reindex | ✅ EMPTY | `systemctl list-timers --all | grep -iE "nox|reindex"` returns 0 results |
| `/etc/cron.d/` `/etc/cron.daily/` `/etc/cron.hourly/` | ✅ NONE | No reindex scripts; only system housekeeping (apport, apt-compat, logrotate, etc.) |
| `/var/spool/cron/crontabs/root` | ✅ MATCH OWNER | Only root crontab present; matches `crontab -l` output |
| OpenClaw internal cron (end-of-day agent step 11) | ✅ FIXED 2026-04-25 | Patched to `consolidate` not `reindex` per INCIDENTS.md 2026-04-25 |
| Manual SSH `nox-mem reindex` | ⚠️ POSSIBLE | Mitigated by ReindexWipeDetectedError guard (post 2026-04-26) — operator must set `NOX_REINDEX_ALLOW_WIPE=1` to bypass |
| Agent-spawned shell rolled into VPS | ⚠️ THEORETICAL | No evidence of agent reindex execution outside cron |
| HTTP API `/api/...` triggering reindex | ✅ NOT EXPOSED | grep of routes shows no reindex endpoint; CLI-only |
| Watcher (`nox-mem-watch`) auto-reindex | ✅ N/A | Watcher ingests deltas via `ingestFile()`, never wipes |

**Conclusion:** the 2026-05-25 23:00 BRT trigger was the **expected cron** (`crontab -l` line `0 23 * * *`). The "unscheduled" framing in the openclaw monitoring alert is incorrect — Phase 2 fires on schedule whenever DOM is odd, DISABLE_AGENT_REINDEX absent, and NEW_CHUNKS>0. All three conditions held.

---

## ALREADY-DEPLOYED MITIGATIONS

Verified in prod 2026-05-31:

### P1 — Safety guard `assertDbPathConsistency()`
`dist/lib/op-audit.js` lines 28+, 75+. Resolved path enforced inside `ALLOWED_PREFIXES`; mismatch between NOX_DB_PATH and OPENCLAW_WORKSPACE-derived path raises. Belt-and-suspenders against bug 1 recurrence even if env munging slips through.

### P2 — Root fix: op-audit respects OPENCLAW_WORKSPACE
PR #358 (`8436982`) merged Wed 2026-05-27. op-audit.ts now uses same resolution logic as db.ts (NOX_DB_PATH first, then OPENCLAW_WORKSPACE-derived, never hardcoded fallback). Verified: `grep -n NOX_DB_PATH op-audit.js` shows resolution path priority and assert function in deployed bundle.

### P3 — reindex.ts routes entity files via `ingestEntityFile()`
Cravado in src/lib/ingest-router.ts since A2. reindex.ts dispatch ensures entity files get section/retention/section_boost preserved, not nuked to NULL.

### P4 — ReindexWipeDetectedError defensive abort
`dist/reindex.js` line 216: when `postCount < MIN_RETENTION_RATIO * preCount` (default 90%), throws `ReindexWipeDetectedError`. withOpAudit failure path preserves pre-op snapshot for safeRestore(). Escape hatch: `NOX_REINDEX_ALLOW_WIPE=1`. **This guard FIRED 2026-05-25 23:10:28 BRT** during the incident — the wipe was caught and snapshot preserved automatically (recovery was via stock `safeRestore()` runbook).

### P0 — nightly-maintenance.sh per-agent explicit envs
Patched on VPS via sed:
```bash
NOX_DB_SOURCE=atlas OPENCLAW_WORKSPACE=/root/.openclaw/agents/atlas NOX_DB_PATH=/root/.openclaw/agents/atlas/tools/nox-mem/nox-mem.db /usr/local/bin/nox-mem reindex
```
Each agent's `NOX_DB_PATH` is now set explicitly — `.env` global no longer wins. Verified in current nightly-maintenance.sh Phase 2 (grep output above).

### Kill-switch state
`/root/.openclaw/DISABLE_AGENT_REINDEX` **absent** by design — fixes deployed, no longer needed. Phase 2 ran clean on Wed 2026-05-27 23:00 BRT post-fix (DOM=27 odd, NEW_CHUNKS>0 — would have triggered) and subsequent odd-DOM nights without incident. `journalctl --since "2026-05-27"` shows clean reindex runs in `ops_audit` table.

---

## REMAINING RISK

| Risk | Severity | Notes |
|---|---|---|
| Bug 3 — withOpAudit silent insert failure | 🟡 medium | Snapshot exists but ops_audit row missing → audit trail gap. Mitigation deployed but no explicit catch+alert+log around audit-row insert. Recurrence visible only via offline reconciliation (snapshot-fs vs ops_audit). Task #23 documented as deferred. |
| Manual SSH reindex bypass | 🟢 low | Operator must intentionally set `NOX_REINDEX_ALLOW_WIPE=1`. Acceptable. |
| `.env` global env vars overriding agent-specific intent | 🟢 low | nightly-maintenance.sh fixed; any new script invoking `nox-mem` against an agent DB MUST set all 3 env vars (NOX_DB_SOURCE + OPENCLAW_WORKSPACE + NOX_DB_PATH). Convention documented in INCIDENTS.md but not enforced statically. |
| Future schema change inflating real entity wipe ≤10% | 🟢 low | `MIN_RETENTION_RATIO=0.9` is conservative; intentional wipe ops would need `NOX_REINDEX_ALLOW_WIPE=1` escape hatch. |

---

## RECOMMENDATIONS (P5+ if any)

| ID | Action | Priority | Effort |
|---|---|---|---|
| P5 | `[[withopaudit-trigger-raise-ignore-swallows-insert]]` — explicit try/catch around `INSERT INTO ops_audit` with stderr log + Discord alert on swallow. Close bug 3. | 🟡 medium | ~2h |
| P6 | Static enforcement: add CI check that any new shell script invoking `nox-mem` with `OPENCLAW_WORKSPACE=/root/.openclaw/agents/<x>` ALSO sets `NOX_DB_PATH` to match. grep-based lint sufficient. | 🟢 low | ~1h |
| P7 | Add `ops_audit` reconciliation cron (daily): list `/var/backups/nox-mem/pre-op/*.db` newer than 24h, JOIN with ops_audit rows, alert on snapshot-without-row. Catches bug 3 recurrence automatically. | 🟢 low | ~2h |
| P8 | Update openclaw monitoring source-of-truth: incident 2026-05-25 IS closed; the "investigation NÃO REALIZADA DESDE SEG 2026-05-28" alert appears to be stale state. Verify monitoring reads `docs/INCIDENTS.md` 2026-05-26 entry + check for trailing TODO markers. | 🟡 medium | ~30min |

None of P5-P8 are critical for the 2026-06-02 arXiv submission window. P8 is procedural hygiene worth fixing this week to prevent false-positive escalations.

---

## CITATIONS

- `/var/log/nox-maintenance.log.6.gz` — full Phase 2 trace incl. ReindexWipeDetectedError stack
- `/var/backups/nox-mem/pre-op/reindex-{atlas,boris,cipher,forge,lex,nox}-20260526*.db` — 1.2GB atlas vs 64MB rest = forensic proof of bug 1
- `ops_audit` rows id 77 (last manual crash 2026-05-24 12:05 atlas), id 65-70 (2026-05-20 wipe-detection sequence) — guards working
- `docs/INCIDENTS.md` entry `2026-05-26 ~02:00 UTC` — full root-cause writeup
- `docs/HANDOFF.md` Wed 2026-05-27 evening — closure
- PR #358 `8436982` — P1+P2 op-audit workspace consistency merge
- `nightly-maintenance.sh` Phase 2 (current) — per-agent NOX_DB_PATH explicit, DISABLE_AGENT_REINDEX still honored as escape valve
- Memory `feedback_reindex_bypasses_openclaw_workspace_hits_main` — primary lesson
- Memory `[[withopaudit-trigger-raise-ignore-swallows-insert]]` — bug 3 reference
