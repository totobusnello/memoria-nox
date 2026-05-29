# LongMemEval Cross-Bench Validation — Methodology

> **Status:** harness shipped 2026-05-29; first canonical run on Sat 2026-05-29.
> **Goal:** triangulate Phase D / Phase H v2 EverMemBench cross-backbone WIN
> claim (nox-mem 51.68% > MemOS 42.55% on gpt-4.1-mini) with an orthogonal
> long-term-memory benchmark.

## Why a second benchmark

Phase H v2 5-batch settled the EverMemBench cross-backbone narrative
([RESULTS-PHASEH-v2-5BATCH.md](../evermembench/RESULTS-PHASEH-v2-5BATCH.md)).
But a single benchmark is a single distribution. LongMemEval (ICLR 2025, Wu et al.,
arXiv:2410.10813) has different gold structure (session-level evidence),
different categories (single-session-user/assistant/preference/multi-session/
temporal-reasoning/knowledge-update + `_abs` abstention variants), and
different evaluation primitive (LLM-as-judge task accuracy + retrieval recall).

If the Phase D config wins LongMemEval too, the cross-benchmark WIN narrative
is robust. If it doesn't, we surface a benchmark-distribution-specific failure
mode — itself a methodology signal (and arguably a stronger paper section than
"we won everywhere").

## Configuration — Phase D parity

| Parameter | Value | Rationale |
|---|---|---|
| Split | `longmemeval_oracle` | Evidence-only per-q haystack (2-3 sessions per q); fast + cheap. Headline split for retrieval signal. |
| n | 300 (stratified) | 30/cell across 10 cells (6 base categories × {non_abs, _abs}). |
| Seed | 42 | Matches Q2 baseline + LoCoMo harness reproducibility seed. |
| top_k | 20 | Phase D over-fetch (matches PR #363+ EverMemBench config). |
| Hybrid | ON (FTS5 + Gemini-3072d + RRF k=60) | Production default. |
| Rerank | OFF (`NOX_RERANKER_ENABLED=0`) | Phase D cross-backbone baseline (rerank-on is Phase F). |
| Ingest | Per-q markdown via `nox-mem ingest <file>` × N sessions | Real ingest path (not scaffold stub). Phase D-equivalent chunking via markdown. |
| Embedding | Gemini-3072d | `gemini-embedding-001`, production default. |
| Isolation | Per-q `NOX_DB_PATH=/root/.openclaw/eval/lme-crossbench-<uuid>/q-<qid>/lme.db` | Op-audit `ALLOWED_PREFIXES` (P1 guard); never touches prod `nox-mem.db`. |
| API server | Per-q restart on port 18835 | Each question's API binds to its own fresh DB. Adds ~5s/q startup. |
| Generator | `gpt-4.1-mini` | Cross-backbone parity with Phase H v2 (matches MemOS Table 4 GPT-4.1-mini column). |
| Judge | `gemini-2.5-flash` | Cheap; explicit caveat in report — paper-grade judge is gpt-4o per LongMemEval paper. |
| Budget cap | $5 | Expected ~$2 actual (Gemini embeds + gpt-4.1-mini generator + Gemini judge). |

## What is measured

Per question, we record:
- **Retrieval-only metrics** (gold = `answer_session_ids`; retrieved =
  parsed session_id from chunk markdown):
  - `nDCG@10` — relevance-weighted ordering quality
  - `Recall@10` — fraction of gold sessions retrieved
  - `MRR` — mean reciprocal rank of first gold hit
  - `session_hit@10` — binary did-any-gold-make-top-10

- **Task accuracy** (LLM-as-judge on generated answer):
  - Overall accuracy + Wilson 95% CI
  - Per base-category breakdown
  - Per `_abs` variant breakdown (refuse-correct semantics on abstention)

- **Latency** breakdown (p50/p95/p99/mean):
  - Ingest (per-q sessions × subprocess)
  - Vectorize (Gemini embedding API)
  - Retrieval (hybrid search API)

## Safety + isolation enforcement

The harness enforces 4 layers of safety:

1. **Path allowlist** — `NOX_DB_PATH` must start with `/var/backups/` or
   `/root/.openclaw/` (op-audit P1 guard, `dist/lib/op-audit.js:75`).
   `/tmp/` paths are rejected — that's why workdir is under
   `/root/.openclaw/eval/`.

2. **Prod-DB refusal** — explicit `refuse_if_prod(db_path, api_base)` aborts
   if the resolved path equals
   `/root/.openclaw/workspace/tools/nox-mem/nox-mem.db` or if api_base contains
   `:18802`.

3. **Per-q DB cleanup** — `shutil.rmtree(qdir)` after each question removes
   the per-q markdown + DB. Only the JSONL result line persists.

4. **API process group SIGTERM** — `stop_api_server` kills the entire process
   group (handles worker forks). Errors during a question still trigger the
   `finally` block.

## Schema bootstrap workaround

Discovered during smoke (2026-05-29 00:30 BRT): the production `dist/db.js`
ships with `SCHEMA_VERSION = 18` but the migration ladder only calls
`migrateToV1..V7`. Functions for V8-V18 (which add `retention_days`, `pain`,
`section`, `section_boost`, KG tables, etc) are missing from the compiled dist.
The prod DB has the V8+ schema because it was migrated incrementally by older
dist builds.

This is a **pre-existing dist bug** that affects any fresh DB ingest.
`adapter_lme.py:bootstrap_db()` works around it by:

1. Running `nox-mem stats` to trigger V1-V7 (this also runs the V5 FTS
   tokenizer migration).
2. Applying the missing V8-V18 `ALTER TABLE chunks` statements directly via
   sqlite3 (idempotent — skips duplicate-column errors).
3. Creating `kg_entities` and `kg_relations` tables (required by api-server
   `/api/search` query).

This is a workaround, not a fix. The proper fix is to either:
- Add `migrateToV8..V18` functions to the next dist build, OR
- Reset `SCHEMA_VERSION = 7` to match the actual migration ladder, OR
- Have `ensureSchema` synthesize V8+ ALTERs from a canonical schema spec.

Tracked separately; out of scope for this cross-bench PR.

## Reproduction

On the VPS (root@187.77.234.79):

```bash
bash /root/.openclaw/workspace/tools/nox-mem/scripts/run-longmemeval-crossbench.sh \
    300 oracle
```

Outputs land in `/root/.openclaw/eval/longmemeval-<uuid>/`:
- `results.jsonl` — per-q retrieval + generated_answer records
- `aggregate.json` — full metrics aggregate
- `summary.md` — human-readable table
- `run.log` — wall-clock log

## Comparison anchors (what we triangulate against)

| Anchor | Source | Numbers |
|---|---|---|
| **nox-mem Q2 baseline (n=100)** | `[[q2-full-results-2026-05-19]]` (pre-G1 sanitize fix) | nDCG@10 = 0.9126, MRR = 0.9162 |
| **Phase H v2 EverMemBench cross-backbone (gpt-4.1-mini)** | `RESULTS-PHASEH-v2-5BATCH.md` | nox-mem 51.68% > MemOS 42.55% (+9.13pp), 5-batch weighted |
| **LongMemEval paper headline (Wu et al. ICLR 2025)** | arXiv:2410.10813 Tables 2-3 | Mem0 / Letta / Zep / LangMem published task accuracy per category |
| **gbrain LongMemEval-S recall** | `[[lab-q1-parte-c-nox-mem-em-longmemeval-s-recall-vs-gbrain]]` | 97.6% session recall (Lab Q1 task #17 reference; pending verification) |

## What this PR does NOT claim

1. **Headline n=500 full sweep.** We run n=300 stratified. Full-corpus is
   Lab Q1 follow-up.
2. **Paper-grade judge.** gemini-2.5-flash is dry-run-grade. Paper headline
   requires gpt-4o judge for κ-style inter-judge calibration. The numbers
   here are directionally correct for the cross-bench WIN signal; absolute
   accuracy magnitudes need gpt-4o cross-check before any paper claim.
3. **S-cleaned (115k-token haystack) numbers.** Oracle split has 2-3 sessions
   per question (~5-30 chunks each). S-cleaned has 40-53 sessions per q (~120k
   tokens). Oracle is paper-protocol-faithful for retrieval signal but
   easier; S-cleaned numbers are a follow-up.
4. **5-batch statistical robustness.** Single run, single seed=42. The
   `[[single-batch-gates-unreliable-5x-overstate]]` lesson applies: cross-bench
   WIN claims should ideally be 5-batch validated. We mark this as a
   methodology gap and propose 5-batch follow-up in the verdict section if
   the single-batch number is on the cusp.

## Caveats for cross-system comparison

We do **NOT** re-run Mem0 / Zep / Letta / LangMem on LongMemEval here. Their
published numbers (paper Tables 2-3) are used as-is, with the same
"methodology details may differ" caveat as LoCoMo Q1. Direct head-to-head
with corpus parity is Lab Q1 priority (`[[everos-honest-comparison-benchmark-gap]]`).

## Files

| File | Purpose |
|---|---|
| `adapter_lme.py` | Per-question ingest + vectorize + search helpers. Schema bootstrap workaround. |
| `run_crossbench.py` | Driver: stratified sample, per-q API spinup, generator call, JSONL writer. Resume support via `--resume`. |
| `score_crossbench.py` | Aggregate: nDCG@10 / R@10 / MRR / session_hit@10 + per-category + Wilson 95% CI. Optional LLM-as-judge task accuracy. |
| `../../scripts/run-longmemeval-crossbench.sh` | Orchestrator: env bootstrap, preflight billing, dataset download, kill leaked processes, run + score. |
| `CROSSBENCH-METHODOLOGY.md` | This document. |
| `RESULTS-CROSSBENCH-2026-05-29.md` | Verdict + numbers + paper §6 implications. |

---

*Authored 2026-05-29 for cross-bench validation post Phase H v2 5-batch ship.*
