# SRE Review — Fase 1.8 (2026-04-19)

**Verdict: CONDITIONAL NO-GO.** Partial GO for Deliverables 1 (audit) + 5 (Cipher cron) only.

Promote to full GO requires:
1. Path A shipped OR inbox writes routed through writer
2. Discord rate budget measured + hard cap on A2A
3. Nox downtime degradation plan

## Top 3 Operational Gaps

1. **[SEV-1] Inbox writes contradict Path A WIP.** 6 agents × 5 dispatches/day + status updates + FTS triggers + heartbeat + watcher re-ingest = hundreds of writes/day concurrent with 23:00 cron (consolidate + vectorize + kg-build). SQLITE_BUSY silencioso = exact failure mode that busy_timeout=5000 masks but doesn't solve. **Fix:** inbox waits for Path A, OR becomes JSONL append-only + rollup in cron.

2. **[SEV-2] Discord webhook saturation not measured.** 1 bot + 6 personas via webhook. Discord limit: 5 req/s per webhook, 30/min per channel. Heartbeats + Cipher cron + proactive suggestions + A2A chatter + status flips can exceed 30/min. **Fix:** measure baseline 24h, set hard cap with circuit breaker.

3. **[SEV-2] Nox = SPOF for mesh.** Heartbeat crashes + gateway restart loops (Mar 31, Apr 1) = mesh goes silent. **Fix:** degraded mode (direct dispatch bypass Nox when `nox_heartbeat_stale > 30min`); document MTTR.

## Numbers to Measure BEFORE

| Baseline | Command |
|---|---|
| Writes/day nox-mem | `SELECT COUNT(*) FROM chunks WHERE created_at > ...` |
| Discord webhook peak | log POST /webhooks/ 48h |
| SQLITE_BUSY count | grep journalctl 7d |
| Gemini $/day | token counter × price 7d |
| Nox heartbeat success | meta table / journalctl |
| systemd-run cold start | `time systemd-run --wait --pipe node -e '1'` × 20 |
| Cron overlap 23:00 / 04:30 | crontab -l + wall-clock analysis |

## Rollback Gaps

- Consolidation: restore files but agents re-ingested consolidated content in nox-mem
- Schema v7 → v6: DROP TABLE + FTS triggers cascade issue
- Nox proactive toggle: gateway prompt cache doesn't invalidate until restart (~15min)
- Cipher cron: if script did `fuser -k`, side effects outlast crontab removal
- Discord webhook: if URL leaks in log/KG, rotation invalidates all 6 personas
