# E10 Followup: Pain Ablation Execution Plan

**Spec ID:** E10-followup-pain-ablation-execution
**Status:** Blocked — requires explicit authorization from Toto before execution
**Effort:** ~12 minutes active execution + 2× ~60s prod API downtime (~2 min total)
**Risk:** Low — operates on a temporary copy of the database; prod DB is never modified

---

## 1. Motivation

Pain-weighted salience (`salience = recency × pain × importance`) is Differentiator #1 of the nox-mem paper:
> "nox-mem is the first documented memory system to model incident severity as a first-class retrieval signal."

A baseline for pain-aware retrieval exists from the post-incident evaluation (nDCG@10 = 0.2689, n=6, 2026-05-04). However, the paper's §5.5 currently lacks a quantitative Δ versus the trivially uniform alternative (all `pain = 1.0`). Without this ablation, Differentiator #1 rests on design rationale alone rather than empirical evidence — a gap that peer reviewers will flag.

This spec defines the procedure to produce that Δ using the existing `pain_dimension_validator.py` harness against a temporary snapshot database, with no permanent modification to production state.

---

## 2. Procedure

Total active time: approximately 12 minutes. Requires two prod API restarts and a maintenance window of low traffic (recommended: 02:00–06:00 BRT).

```
Step 1 — Snapshot (5 min)
  VACUUM INTO '/tmp/nox-pain-test.db'
  via: sqlite3 $NOX_DB_PATH "VACUUM INTO '/tmp/nox-pain-test.db';"
  Confirms: snapshot file size matches prod DB before proceeding.

Step 2 — Uniform pain injection (1 min)
  sqlite3 /tmp/nox-pain-test.db "UPDATE chunks SET pain = 1.0;"
  Operates exclusively on the snapshot. Prod DB is untouched.

Step 3 — Stop prod API (30 s)
  systemctl stop nox-mem-api
  Confirm: curl http://127.0.0.1:18802/api/health returns connection refused.

Step 4 — Start API against snapshot DB (1 min)
  NOX_DB_PATH=/tmp/nox-pain-test.db systemctl start nox-mem-api
  Confirm: /api/health responds + dbPath shows /tmp/nox-pain-test.db.

Step 5 — Run ablation harness (5 min)
  python pain_dimension_validator.py --mode api
  Records nDCG@10 under uniform pain across the existing query set.

Step 6 — Stop API (30 s)
  systemctl stop nox-mem-api

Step 7 — Restore prod API (1 min)
  systemctl start nox-mem-api   # env file restores NOX_DB_PATH to prod default
  Confirm: /api/health responds + dbPath shows prod path.

Step 8 — Validate prod state (1 min)
  curl http://127.0.0.1:18802/api/health | jq "{chunks: .chunks.total, embedded: .vectorCoverage.embedded, salience: .salience.mode}"
  Expected: chunk count and embed coverage identical to pre-ablation snapshot.
```

---

## 3. Risk Assessment

| Risk | Likelihood | Mitigation |
|---|---|---|
| Snapshot creation fails (disk full) | Low — `/tmp` has headroom | Check `df -h /tmp` before Step 1; abort if < 2× DB size available |
| API fails to start against snapshot DB | Very low | Confirmed pattern from F02 op-audit testing; rollback is Step 7 |
| Prod DB modified accidentally | None | Step 2 targets `/tmp/nox-pain-test.db` exclusively; no write path to prod in Steps 1–6 |
| Extended downtime (API hangs in Step 4) | Very low | Hard timeout: if Step 5 exceeds 8 min, kill API, run Step 7 immediately |
| False Δ from harness query-set size (n=6) | Moderate | Document n=6 as limitation in §5.5; result is directional, not definitive |

**Total prod unavailability:** ~2 minutes (2× ~60s restarts), within acceptable bounds for a 02:00–06:00 BRT window.

---

## 4. Rollback

If any step produces an unexpected result:

```bash
# Kill API regardless of state
systemctl stop nox-mem-api

# Restore env file from backup (if somehow modified)
cp /root/.openclaw/.env.bak-pre-ablation /root/.openclaw/.env

# Restart against prod
systemctl start nox-mem-api

# Verify
curl http://127.0.0.1:18802/api/health | jq .chunks.total
```

The prod DB is never in the write path during Steps 1–6. The snapshot at `/tmp/nox-pain-test.db` can be deleted after the run completes successfully.

---

## 5. Result Interpretation

The ablation produces a single metric: nDCG@10 under uniform `pain = 1.0`. Compare against the existing baseline (pain-aware, nDCG@10 = 0.2689).

| Outcome | Δ nDCG@10 | Paper §5.5 conclusion |
|---|---|---|
| Pain-aware clearly superior | ≥ 0.05 | Empirical validation of Differentiator #1; include as primary evidence |
| Directional evidence | 0 < Δ < 0.05 | Report as directional; note n=6 limitation; retain design rationale as co-evidence |
| No measurable effect | Δ ≤ 0 | Reframe Differentiator #1 as architectural contribution (design discipline, not retrieval gain); update positioning in §2 and §6 accordingly |

Any non-null result is publishable. The absence of a large positive Δ is itself a finding worth reporting honestly.

---

## 6. Authorization Requirement

This experiment requires Toto's explicit go-ahead before execution due to the 2× prod API restart. Recommended authorization phrase:

> "Rodar E10 pain ablation com 2× prod restart"

No deadline is imposed by the paper timeline — the ablation can run any time before W4 writing begins (2026-05-25). Preferred window: W2 off-peak (2026-05-11–17, 02:00–06:00 BRT).

---

## 7. Effort Summary

| Phase | Duration |
|---|---|
| Pre-run check (`df`, env backup) | 2 min |
| Steps 1–8 (execution) | ~12 min |
| Result logging in `docs/HANDOFF.md` + paper §5.5 | ~5 min |
| **Total** | **~20 min** |
