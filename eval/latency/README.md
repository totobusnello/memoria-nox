# Latency Benchmark — nox-mem Hybrid Search

## Purpose

Produce defensible p50/p95/p99 latency numbers for the three core primitives
of nox-mem: hybrid search, ingest, and (future) answer. These numbers feed the
"Numbers that lead" pillar and provide a baseline to compare against competitors
(Memanto claims sub-90ms retrieval; agentmemory has no published number).

---

## Workload Definitions

### search.short
- Description: 1–3 word queries — minimal FTS5 + semantic surface area.
- Source: golden-queries.jsonl, filtered to words ≤ 3, padded with synthetic
  single-keyword queries to reach n=100.
- Metric target: sub-100ms p50 warm (hypothesis).

### search.medium *(mapped from search.short extended to 4–9 words)*
- Description: Typical conversational queries. The bulk of real traffic.
- Source: golden-queries.jsonl queries with 4–9 words, padded to n=100.

### search.long
- Description: 10+ word natural-language questions. Tests full BM25+semantic
  pipeline with longer tokenization.
- Source: golden-queries.jsonl filtered to words ≥ 10, padded with multi-clause
  synthetic queries to reach n=100.

### search.kg-heavy
- Description: Queries containing known named entities (agent names, project
  slugs, tool names) that trigger KG traversal in hybrid search.
- Source: golden-queries.jsonl category=entity, padded to n=50.
- Note: latency delta between search.short and search.kg-heavy isolates KG tax.

### ingest.entity-file
- Description: Ingest a typical ~5KB entity Markdown file (frontmatter +
  compiled + timeline sections). Warm-DB run — DB is pre-loaded, not cold.
- Source: a fixture entity file at eval/latency/fixtures/entity-fixture.md.
- n=50 (each run appends unique slug to avoid dedup short-circuit).

### ingest.chunk-batch
- Description: Batch insert 100 raw text chunks via programmatic API (or CLI
  subprocess). Tests write throughput, FTS5 insert, and vector queue.
- Source: synthetic 200-word chunks generated from lorem-like text.
- n=20 (each run uses fresh slugs).

### answer.placeholder
- Description: Stub workload for when the P1 Answer primitive ships.
  Records "NOT_YET" for all metrics until P1 is integrated.
- See: specs/answer/ for upcoming interface.

---

## Measurement Methodology

### Timing
Use `process.hrtime.bigint()` (nanosecond resolution) rather than `Date.now()`
(millisecond, susceptible to wall-clock drift). Convert to ms for output.

```
const t0 = process.hrtime.bigint();
await runWorkloadIteration();
const elapsed_ns = Number(process.hrtime.bigint() - t0);
const elapsed_ms = elapsed_ns / 1_000_000;
```

### Warmup
- 10 warmup iterations before counting.
- Warmup results are discarded (not included in p50/p95/p99 calculation).
- Purpose: populate OS page cache, JIT warm SQLite prepared statements,
  prime Node.js V8 JIT, and load nox-mem module once if subprocess approach.

### Sample Count
- Minimum n=100 for search workloads; n=50 for ingest; n=20 for chunk-batch.
- At n=100 with typical σ~20ms, 95% CI half-width ≈ ±3.9ms — acceptable for
  v1. Tighter CIs require n≥400; deferred to v2.

### Outlier Handling
- **v1 decision: NO trimming.** Document raw distribution including GC pauses.
  Rationale: p99/p99.9 are explicitly interesting; trimming hides tail behavior.
  If GC spikes inflate p99 artificially, note it in the run report.
- p99.9 is computed to expose GC-pause outliers explicitly.

### Cold vs Warm Cache

**Warm (default):**
Run after 10 warmup iterations. OS page cache is hot. This is the "steady-state
production" number — the one most relevant to live usage.

**Cold:**
Drop OS file cache before the first iteration (Linux only):
```bash
sync && echo 3 > /proc/sys/vm/drop_caches  # requires sudo
```
macOS: `purge` command (requires admin), or reboot. Cold runs should be in
a separate invocation with `--cold` flag.

Report cold and warm as separate workload variants:
`workload.cold.search.short` vs `workload.warm.search.short`.

### Subprocess Tax
nox-mem does not expose an importable TypeScript module (VPS binary is compiled
to `dist/index.js`). Search and ingest are measured as **child_process
subprocess calls**. The subprocess startup cost (~50–150ms first call) is
absorbed in warmup. Post-warmup, the process is spawned fresh each iteration
(shell startup overhead ~5–15ms) — this is measured and documented, not hidden.

If a future PR exposes a programmatic API (HTTP :18802 or in-process module),
replace subprocess calls with direct calls and document the delta.

---

## Reproduction Steps

### Prerequisites
1. Clone nox-mem to VPS or local with access to `dist/index.js`.
2. Set env: `set -a; source /root/.openclaw/.env; set +a`
3. Prepare eval DB: `cp /path/to/nox-mem.db eval/latency/eval.db`
   *(eval.db is NOT included in git — see .gitignore)*
4. Install harness deps: `cd eval/latency && npm install`
5. Build harness: `npm run build`

### Run
```bash
# Warm run (default)
node dist/runner.js --workload search.short --output results/search-short.json

# All workloads
node dist/runner.js --all --output results/full-run.json

# 10-query dry-run (validates pipeline, fast)
node dist/runner.js --workload search.short --n 10 --warmup 0 --output results/dry-run-sample.json
```

### Aggregate
```bash
node dist/aggregator.js --input results/full-run.json --output results/summary.json
```

---

## What Is NOT Covered in v1

- **Concurrent clients**: single-tenant only. No load test, no queue saturation.
- **Network latency**: measured locally on VPS; no client-to-server roundtrip.
- **Cross-machine variance**: only tested on Hostinger VPS (4 vCPU, 8GB RAM).
  Results will differ on different hardware.
- **Vector embedding latency**: Gemini embedding API call is part of ingest path
  but has external network dependency — measured end-to-end, NOT isolated.
- **Cold start at process level**: Node.js cold start (first `node dist/index.js`
  invocation) measured separately if needed; not part of default workload.
- **DB growth effects**: benchmarks run at current ~69k chunk corpus. Not tested
  at 500k or 1M chunks.

---

## Open Questions for Toto

1. **Competitor comparison framing**: Memanto says "sub-90ms retrieval" — do we
   know if that's warm p50 or p99? And is it single-tenant? If apples-to-apples
   requires clarification, we should footnote our published numbers carefully.

2. **Publishing threshold**: At what p50 warm number are we comfortable
   publishing? Is "sub-200ms p50" good enough for v1 marketing, or do we need
   sub-100ms before going public with this?

3. **Ingest SLA target**: For the answer primitive (P1), latency budget matters.
   Should ingest.entity-file p95 be a hard gate before P1 ships, or is it
   informational only right now?
