# E03 — BEIR TREC-COVID Baseline Evaluation: LAUNCHED

**Closes:** C5 (external validity, single-corpus). Paper §5.3 Table 3.

---

## Launch Summary

| Field | Value |
|---|---|
| Launch timestamp BRT | 2026-05-04 10:30 BRT (13:30 UTC) |
| VPS | root@187.77.234.79 (Hostinger, 8-core, 15GB RAM) |
| tmux session | `beir-trec` |
| Expected completion | 2026-05-05 ~22:00–06:00 BRT (3-6h e5 embed + <1min eval) |
| Corpus | BEIR TREC-COVID, 50K-doc subset (seed=42), 50 queries, Round 5 qrels |

---

## Phases Status (at launch)

| Phase | Status | Notes |
|---|---|---|
| 1. build-db (50K subset) | DONE | `/tmp/nox-mem-trec-covid.db` — 50K docs + FTS5 index |
| 2. convert-queries | DONE | `/tmp/trec-covid-eval-queries.jsonl` — 50 queries |
| 3. BM25-FTS5 baseline | DONE | `/root/beir-results/baselines-bm25-beir.jsonl` — 50 queries |
| 4. multilingual-e5-base | RUNNING | ETA 3-6h (50K × 768d on CPU, 2 cores capped) |
| 5. compare + CSV | PENDING | Runs automatically after Phase 4 |

### Phase 3 BM25 Preliminary Results (full 50-query run on 50K subset)
- Query 1 ("what is the origin of COVID-19"): nDCG@10=0.315, MRR=1.0, P@5=0.4
- These are real numbers, not smoke test values.

---

## Bug Found and Patched

**Bug:** `_load_qrels()` in `beir_trec_covid_adapter.py` expected 4-column TREC
format (`query_id 0 doc_id grade`) but BEIR TREC-COVID delivers 3-column with
header (`query-id corpus-id score`). Original code silently loaded 0 judgments.

**Fix:** 2026-05-04 — dual-format detection (3-col vs 4-col), header skip via
non-numeric grade detection. Patched in both local repo and VPS copy.

**Evidence:** Smoke test before patch: `Loaded qrels: 0 queries, 0 total judgments`.
After patch: `Loaded qrels: 50 queries, 66336 total judgments`.

---

## Scripts Deployed

| Script | Location (VPS) | Purpose |
|---|---|---|
| `beir_trec_covid_adapter.py` | `/root/beir-baselines/` | BEIR pipeline (download/build-db/convert-queries/compare) |
| `beir_bm25_fts5.py` | `/root/beir-baselines/` | BM25 via FTS5 (no Pyserini/JVM) |
| `beir_e5_runner.py` | `/root/beir-baselines/` | multilingual-e5-base dense retrieval |
| `beir_full_run.sh` | `/root/beir-baselines/` | Orchestrator (phases 1-5) |
| `beir-kill-if-overload.sh` | `/usr/local/bin/` | Kill-switch (load15 > 5.0) |

**venv:** `/root/beir-adapter-venv/` (Python 3.13, torch CPU, sentence-transformers)

---

## Monitor Commands

```bash
# Check tmux session alive
ssh root@187.77.234.79 'tmux ls'

# Watch live progress
ssh root@187.77.234.79 'tail -f /var/log/nox-mem/beir-full-run.log'

# 5-min progress ticker (docs embedded + ETA)
ssh root@187.77.234.79 'tail -f /var/log/nox-mem/beir-progress.log'

# Kill-switch log
ssh root@187.77.234.79 'tail -20 /var/log/nox-mem/beir-killswitch.log'

# Check results dir
ssh root@187.77.234.79 'ls -lh /root/beir-results/'
```

---

## Recovery if VPS Reboots

The pipeline is idempotent. If VPS reboots:

```bash
ssh root@187.77.234.79

# Check what already ran
ls /root/beir-results/
ls /tmp/nox-mem-trec-covid.db  # TEMP DB (survives reboot? check /tmp)

# If TEMP DB gone after reboot, Phase 1+2 rerun automatically (~2-3 min)
# If e5 .npz cache exists, embedding is skipped (idempotent)
ls /root/beir-results/e5-trec-covid.npz

# Relaunch inside tmux
tmux new-session -d -s beir-trec 'bash /root/beir-baselines/beir_full_run.sh 2>&1 | tee -a /var/log/nox-mem/beir-full-run.log'
tmux ls
```

**NOTE:** `/tmp/nox-mem-trec-covid.db` is in tmpfs — survives until reboot.
If rebooted: Phase 1 (build-db) reruns (~2-3 min, corpus cached at `~/.cache/beir/`).
`/root/beir-results/` is on disk — survives reboots. e5 .npz cache survives.

---

## Kill-Switch (Cron)

Active in root crontab:
```
*/30 * * * * root /usr/local/bin/beir-kill-if-overload.sh >> /var/log/nox-mem/beir-killswitch.log 2>&1
```
Kills `beir-trec` tmux session if 15min load avg > 5.0 (62.5% of 8-core VPS).

---

## Expected Outputs

| File | Description |
|---|---|
| `/root/beir-results/baselines-bm25-beir.jsonl` | BM25-FTS5 — 50 queries (DONE) |
| `/root/beir-results/e5-trec-covid.npz` | e5 embedding cache — 50K × 768d |
| `/root/beir-results/baselines-e5-beir.jsonl` | e5 dense retrieval — 50 queries |
| `/root/beir-results/baselines-comparison-beir.csv` | Table 3 for §5.3 |

On completion, rsync to local:
```bash
rsync -av root@187.77.234.79:/root/beir-results/ \
    /Users/lab/Claude/Projetos/memoria-nox/paper/publication/results/beir/
```
