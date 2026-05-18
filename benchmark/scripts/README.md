# benchmark/scripts — Q1+Q2+Q3 Runnable Scripts

Runbooks and executable scripts to trigger the three benchmark runs that unlock the Q4 COMPARISON gate (GTM Phase 2).

**Reference spec:** `specs/2026-05-18-Q1-Q2-Q3-vps-scheduling.md`
**Reference gate:** `benchmark/COMPARISON.md §5 Gate Decision Logic`

---

## Scripts overview

| Script | What it does | Cost | Duration |
|---|---|---|---|
| `run-q3.sh` | Latency baseline — search + ingest on real VPS DB | $0.00 | ~45 min |
| `run-q1.sh` | LoCoMo R@5/R@1/MRR/nDCG@10 harness | ~$0.05 | ~1.5h |
| `run-q2.sh` | LongMemEval task-accuracy + judge (gpt-4o + gemini) | ~$1.08 | ~3h |
| `collect-results.sh` | scp results from VPS → local, validate schema | $0.00 | ~2 min |
| `generate-comparison.ts` | Validate Q1+Q2+Q3 + run `benchmark/generate-comparison.ts` | $0.00 | ~30s |

Total estimated cost for one full run: **~$1.13**
Recommended: 3 runs minimum for published numbers → **~$3.40 + ~18h** over 3 days.

---

## Pre-flight checklist

Run these checks on the VPS before starting **any** benchmark:

```bash
# 1. SSH into VPS
ssh root@<vps-ip>

# 2. Source env (CLAUDE.md regra #1 — mandatory before any nox-mem CLI)
set -a; source /root/.openclaw/.env; set +a

# 3. Check nox-mem-api health
curl -sf "http://127.0.0.1:${NOX_API_PORT:-18802}/api/health" | jq '{status, total, embedded, schemaVersion}'
# Expected: status="ok", embedded≈total, schemaVersion>=20

# 4. Check disk space (need >=5 GB for Q2)
df -h /root/ | tail -1
# Need at least 5G free

# 5. Check Gemini API key present and valid
echo "GEMINI_API_KEY: ${GEMINI_API_KEY:0:12}..."
curl -s "https://generativelanguage.googleapis.com/v1beta/models?key=${GEMINI_API_KEY}" \
  | jq '.error.code // "OK"'
# Expected: "OK"

# 6. Check OPENAI_API_KEY (only required for Q2 gpt-4o judge — optional)
echo "OPENAI_API_KEY: ${OPENAI_API_KEY:0:12}..."

# 7. Set cost cap (mandatory per spec §7)
export NOX_PROVIDER_DAILY_USD_CAP=20
echo "Cost cap: $NOX_PROVIDER_DAILY_USD_CAP"

# 8. CPU idle check
top -bn1 | head -5
# Ideally >=70% CPU idle before starting

# 9. Create log dir
mkdir -p /var/log/nox-mem/bench && chmod 700 /var/log/nox-mem/bench
```

---

## tmux + nohup pattern (resilience to SSH disconnect)

**Use tmux for all benchmark runs.** Processes survive SSH disconnect; you can re-attach later.

```bash
# On VPS — open tmux session
tmux new -s benchmark

# Navigate panels:
#   Ctrl+B → D    = detach (leave running)
#   Ctrl+B → C    = new window
#   Ctrl+B → 0/1  = switch window
#   tmux attach -t benchmark = re-attach after disconnect

# Scripts internally do exec > logfile 2>&1, so logs persist even without terminal.
```

---

## Recommended execution order: Q3 → Q1 → Q2

| Order | Why |
|---|---|
| Q3 first | $0.00 cost, validates VPS is idle and harness runs correctly |
| Q1 second | Only $0.05 embedding cost; validates retrieval pipeline before paying for generation |
| Q2 last | Most expensive (~$1.08); only run after Q1 confirms retrieval is working |

If Q1 shows R@5 unexpectedly low (< 0.5), investigate before running Q2.

---

## Running Q3 — Latency baseline (~45 min, $0)

```bash
# On VPS, inside tmux:
NM=/root/.openclaw/workspace/tools/nox-mem
cd $NM
set -a; source /root/.openclaw/.env; set +a

# Full run (all workloads)
bash benchmark/scripts/run-q3.sh 2>&1 | tee /var/log/nox-mem/bench/q3-console.log

# Single workload (optional — each takes ~3-5 min)
bash benchmark/scripts/run-q3.sh --workload search.medium

# Dry-run (validate env + print plan)
bash benchmark/scripts/run-q3.sh --dry-run
```

Q3 has no inter-workload checkpoint. If interrupted, restart the specific workload.

**Output:** `benchmark/results/q3-latency-<TS>.json` + `benchmark/results/q3-summary-<TS>.json`

---

## Running Q1 — LoCoMo (~1.5h, ~$0.05)

```bash
# On VPS, inside tmux:
NM=/root/.openclaw/workspace/tools/nox-mem
cd $NM
set -a; source /root/.openclaw/.env; set +a
export NOX_PROVIDER_DAILY_USD_CAP=1  # safe cap for Q1

# Full run n=100, seed=42
bash benchmark/scripts/run-q1.sh

# Dry-run
bash benchmark/scripts/run-q1.sh --dry-run

# Resume from checkpoint (if run was interrupted)
LATEST_CHECKPOINT=$(ls -t eval/locomo/results/partial-*.json | head -1)
bash benchmark/scripts/run-q1.sh --resume "$LATEST_CHECKPOINT"
```

Q1 saves a checkpoint every 10 queries at `eval/locomo/results/partial-<TS>.json`.

**Output:** `benchmark/results/q1-locomo-<TS>.json`

---

## Running Q2 — LongMemEval (~3h, ~$1.08)

```bash
# On VPS, inside tmux:
NM=/root/.openclaw/workspace/tools/nox-mem
cd $NM
set -a; source /root/.openclaw/.env; set +a
export NOX_PROVIDER_DAILY_USD_CAP=5  # $5 cap; estimated cost ~$1.08

# Full run — both judges (auto-detects OPENAI_API_KEY)
bash benchmark/scripts/run-q2.sh

# Force single judge (if OPENAI_API_KEY unavailable)
bash benchmark/scripts/run-q2.sh --judge gemini-2.5-pro

# Dry-run
bash benchmark/scripts/run-q2.sh --dry-run

# Resume from partial hypotheses
LATEST=$(ls -t eval/longmemeval/hypotheses/*.jsonl | head -1)
bash benchmark/scripts/run-q2.sh --resume "$LATEST"
```

Q2 saves partial hypotheses incrementally per question at `eval/longmemeval/hypotheses/run-<TS>-partial.jsonl`.

**Monitor cost mid-run** (in a separate tmux pane):
```bash
watch -n 60 'sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
  "SELECT ROUND(SUM(cost_usd),4) || \" USD (\" || COUNT(*) || \" calls)\" \
   FROM provider_telemetry WHERE created_at >= date(\"now\");"'
# If cost accumulates >$0.02/min, something is wrong — interrupt and investigate
```

**Output:** `benchmark/results/q2-longmemeval-gpt4o-<TS>.json` + `benchmark/results/q2-longmemeval-gemini25pro-<TS>.json`

---

## Cost-cap explanation

Every run script exports `NOX_PROVIDER_DAILY_USD_CAP` before any API calls:

| Script | Default cap | Expected cost | Safety margin |
|---|---|---|---|
| run-q3.sh | $20 (global) | $0.00 | N/A — no API calls |
| run-q1.sh | $1 | ~$0.05 | 20× |
| run-q2.sh | $5 | ~$1.08 | ~5× |

The `CostCappedProvider` module (A3) aborts calls when the daily cap is hit and marks remaining questions as `"status": "aborted_cost_cap"` in the output JSON. This is not a crash — the partial result is still valid and resumable.

Override caps for unusual conditions:
```bash
export NOX_PROVIDER_DAILY_USD_CAP=0.10  # extra-tight for test run
export NOX_PROVIDER_DAILY_USD_CAP=50    # if running 3 full Q2 runs in one day
```

---

## Collecting results (run on Mac, not VPS)

After all three benchmarks complete, collect from VPS to local:

```bash
# On Mac:
cd /Users/lab/Claude/Projetos/memoria-nox

# Collect all results
bash benchmark/scripts/collect-results.sh --vps root@<vps-ip> --all

# Collect specific benchmarks
bash benchmark/scripts/collect-results.sh --vps root@<vps-ip> --q3
bash benchmark/scripts/collect-results.sh --vps root@<vps-ip> --q1 --q2

# Dry-run (print what would be collected)
bash benchmark/scripts/collect-results.sh --vps root@<vps-ip> --all --dry-run
```

The script validates JSON schemas and checks required fields. Exit code 0 = all results valid.

---

## Gate update workflow

After collecting results locally:

```bash
# 1. Spot-check numbers manually (NEVER skip this)
jq '{r5:.metrics.r5, ndcg10:.metrics.ndcg10}' eval/locomo/results/full-run.json
jq '{accuracy:.metrics.overall_accuracy, judge:.judge_model}' eval/longmemeval/full-run.gpt4o.json
jq '.workloads["search.medium"]' eval/latency/results/summary.json

# 2. Check no null metrics
jq '.metrics | to_entries | map(select(.value == null))' eval/locomo/results/full-run.json
# Expected: []

# 3. Run validation wrapper (validates + calls main generator)
npx tsx benchmark/scripts/generate-comparison.ts

# 4. If validation passes:
GATE_VERIFIED=1 \
  LOCOMO_RESULTS_DIR=eval/locomo/results \
  LONGMEMEVAL_RESULTS_DIR=eval/longmemeval \
  LATENCY_RESULTS_DIR=eval/latency/results \
  npx tsx benchmark/generate-comparison.ts

# 5. Verify COMPARISON.md has no 'pending' cells
grep -i "pending" benchmark/COMPARISON.md
# Expected: no output

# 6. Commit
git add benchmark/COMPARISON.md \
  eval/locomo/results/full-run.json \
  eval/longmemeval/full-run.gpt4o.json \
  eval/longmemeval/full-run.gemini25pro.json \
  eval/latency/results/

git commit -m "data(Q4-gate): Q1+Q2+Q3 VPS results + COMPARISON.md gate opened $(date +%Y-%m-%d)"
```

---

## Q4 gate decision tree

```
Q: Is VPS idle (CPU >70% idle, disk >5 GB, nox-mem-api healthy)?
├── NO  → Wait. Check: systemctl status nox-mem-api; top; df -h /root/
└── YES → continue

Q: Is GEMINI_API_KEY valid and has quota?
├── NO  → Wait for midnight UTC quota reset, or provision new key
└── YES → continue

Q: Which benchmark next?
├── None ran yet           → Q3 (free, validates env)
├── Q3 done, Q1 pending    → Q1 (~$0.05, ~1.5h)
├── Q1 done, Q2 pending    → verify OPENAI_API_KEY → Q2 (~$1.08, ~3h)
└── All done               → collect-results.sh → gate update → commit

Q: Q1 R@5 is unexpectedly low (< 0.5)?
├── Dry-run first: npx tsx eval/locomo/run.ts --n 5 --seed 42 --cli
├── Bug in ingest/search? → Fix, re-run Q1
└── Honest result?        → Publish with disclosure (gate opens anyway)

Q: Q2 run was interrupted?
├── Partial .jsonl exists? → bash run-q2.sh --judge <judge> --resume <path>
├── eval.db corrupted?     → sqlite3 eval/longmemeval/eval.db "PRAGMA integrity_check;"
│                            → If not "ok": rm eval.db && re-ingest (costs ~$0.35 re-embedding)
└── Quota exhausted?       → Wait for midnight UTC reset, resume via checkpoint

Q: Gate update script aborts?
├── "Missing result files" → verify all 3 JSON files exist and are valid
├── "GATE_VERIFIED not set" → export GATE_VERIFIED=1 before running
└── "null metrics"         → run was incomplete; use --resume to complete
```

---

## What to skip

| Condition | Skip |
|---|---|
| Q3 not needed for GTM argument | Q3 is $0 and <1h — highly recommended to always run |
| OPENAI_API_KEY unavailable | Q2 gemini-2.5-pro judge alone is acceptable; document limitation in COMPARISON.md §9 |
| Q1 result is unexpectedly good | Never skip verification; publish honest numbers |
| Q2 M-split (500 sessions/question) | Deferred — too expensive for first gate run |

**Q1 cannot be skipped.** It is the benchmark that directly compares against agentmemory's published R@5 95.2% claim.

---

## Files not to commit

The `.gitignore` already covers these — do not override:

- `eval/*.db`, `eval/**/*.db` — eval databases are disposable
- `eval/**/data/*.json` — dataset caches (large, CC/MIT licensed separately)
- `eval/**/hypotheses/*.jsonl` — intermediate judge hypotheses
- `eval/**/dataset.lock.json` — local dataset pins
- `/var/log/nox-mem/bench/*.log` — VPS logs (not in repo)

---

## Retry playbook

| Failure | Action |
|---|---|
| Rate limit 429 (Gemini) | Harness has built-in backoff; if persistent, wait for quota reset at midnight UTC |
| VPS disk full | `ls -lhS /var/backups/nox-mem/ \| head -20` — remove pre-op snapshots older than 7d |
| Node OOM during Q1/Q2 | Reduce `--n 50`, run in two passes via `--resume` |
| VPS CPU throttled | `top` shows load; wait 5 min and retry |
| SSH disconnect mid-run | `tmux attach -t benchmark` — process kept running inside tmux |
| eval.db integrity error | `PRAGMA integrity_check;` → if fails: delete eval.db, re-ingest (costs re-embedding) |

---

*Spec: `specs/2026-05-18-Q1-Q2-Q3-vps-scheduling.md` (Wave M)*
*Gate: `benchmark/COMPARISON.md §5`*
*Decisions: `docs/DECISIONS.md`*
