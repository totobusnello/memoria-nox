# E10 Pain Dimension Validation — Baseline API mode

> **Run date:** 2026-05-04 ~07:21 BRT
> **Mode:** `--mode api` (HTTP GET against prod nox-mem `:18802/api/search`)
> **DB:** prod `/root/.openclaw/workspace/tools/nox-mem/nox-mem.db` (READ-only via API)

## Setup

| Parameter | Value |
|---|---|
| Variant | `pain_real` (baseline — real pain values from prod) |
| Metric | nDCG@10 (binary relevance) |
| N queries | 6 post-incident curated subset |
| API | nox-mem hybrid (FTS5 + Gemini 3072d + RRF k=60) |

## Result

**Mean nDCG@10 = 0.2689** (over 6 post-incident queries)

| Query | Category | nDCG@10 |
|---|---|---|
| Q47 — `o que faz withOpAudit e quando usar` | entity | tracked in audit log |
| Q52 — `como rodar nox-mem reindex com segurança` | procedure | tracked |
| Q67 — `qual a regra sobre rsync delete` | decision | tracked |
| Q71 — `qual a primeira lição do incident reindex 2026-04-25` | temporal | tracked |
| Q85 — `como Lex e Cipher se complementam em incidents` | cross-agent | tracked |
| Q89 — `como rotacionar a key Slack sem downtime` | security | tracked |
| **Mean** | | **0.2689** |

(Per-query nDCG individual values em `pain_test_audit.log`.)

## Comparison context

- **Overall n=50 hybrid baseline (R01b):** 0.5213 ± 0.0004
- **Post-incident subset (n=6) baseline:** **0.2689**
- Δ = -0.2524 — post-incident queries são **intrinsically harder** than the average golden query

This is itself an interesting finding: the queries that SHOULD benefit most from pain weighting (post-incident) are the hardest in the corpus. Pain dimension's value would be in **lifting** these specifically.

## Pain ablation status: NOT EXECUTED

**Why:** ablating pain (setting `pain=1.0` uniform) requires:
1. Stop nox-mem-api service
2. Apply UPDATE chunks SET pain=1.0 in TEMP DB
3. Start nox-mem-api with `NOX_DB_PATH=temp-db`
4. Run eval
5. Restore prod DB path
6. Restart nox-mem-api

This is **2× restarts of prod service** = operational risk. User has not authorized this execution path.

## Honest framing for paper §5.5

> "We measured nox-mem hybrid retrieval performance on a curated subset of 6 post-incident queries (queries that explicitly reference incidents, lessons, or post-mortem context). Mean nDCG@10 = 0.2689 — significantly lower than the overall corpus baseline (0.5213, n=50) — indicating that post-incident queries are an intrinsically harder retrieval class. Empirical ablation of the pain dimension (setting pain=1.0 uniform vs real values) requires controlled API restart and is documented as future work (Appendix B.4). Diferencial #1 (pain-weighted salience as retrieval signal) remains a **design contribution** with empirical baseline; isolation of the pain term's marginal contribution awaits the deferred ablation."

## Backlog item E10-followup

| Step | Effort | Authorization needed |
|---|---|---|
| 1. Snapshot DB → TEMP | 5min | already covered (snapshot exists) |
| 2. Apply pain=1.0 SQL UPDATE in TEMP | 1min | ✅ TEMP DB only |
| 3. Stop nox-mem-api | 30s | ⚠️ prod service |
| 4. Restart with NOX_DB_PATH=temp | 1min | ⚠️ prod service |
| 5. Run pain validator --mode api | 5min | API now points to temp |
| 6. Restore prod NOX_DB_PATH | 30s | ⚠️ prod service |
| 7. Restart nox-mem-api | 30s | ⚠️ prod service |
| **Total** | **~12min** | **2× prod restarts** |

When user authorizes 2× prod restart window: re-run completes the experiment.

## What survives in paper §5.5

- ✅ Pain-aware baseline number (0.2689) over post-incident subset
- ✅ Comparison to overall baseline (-0.2524 = post-incident queries are harder class)
- ⚠️ Pain ablation Δ — mark as "experiment pending; deferred from W2 due to operational restart constraint"
- ✅ Architectural design contribution remains intact (formula + schema)
