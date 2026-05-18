# `benchmark/` — Public Comparison Framework

> **Scope:** This directory holds the *public-facing* benchmark publication
> machinery. It is the artifact a reader lands on when they want to know
> "how does nox-mem compare?" Internal harnesses (the things that *produce*
> the numbers) live under `eval/locomo/`, `eval/longmemeval/`, `eval/latency/`.

---

## Files at a glance

| File | Purpose | Status |
|---|---|---|
| `README.md` | This file — overview, methodology umbrella, gate doc | scaffold |
| `COMPARISON.md.template` | Public template, placeholders only | scaffold |
| `LONGMEMEVAL.md.template` | Detailed per-benchmark template (LongMemEval) | scaffold |
| `LOCOMO.md.template` | Detailed per-benchmark template (LoCoMo) | scaffold |
| `LATENCY.md.template` | Detailed per-benchmark template (latency) | scaffold |
| `competitor-configs.json` | 7 competitors: install, invocation, quirks | scaffold |
| `collect-competitor-data.ts` | Per-tool data collection runner (dry-run first) | scaffold |
| `generate-comparison.ts` | Render template → final `COMPARISON.md` (GATE-locked) | scaffold |
| `BLOCKED.md` | Competitors with no accessible eval interface | scaffold |
| `.gitignore` | Scratch/cache/intermediate JSON | scaffold |

**Generated artifacts** (written *only* after `GATE_VERIFIED=1`):

- `COMPARISON.md`
- `LONGMEMEVAL.md`
- `LOCOMO.md`
- `LATENCY.md`
- `results/<competitor>/{locomo,longmemeval,latency}.json` (raw per-tool data)

---

## Publication gate

This is the critical operational decision: **the comparison only publishes if
nox-mem is at the top or tied across the headline metrics.** Otherwise it
stays private, becomes a Lab finding, and we go back to the drawing board.

### Gate inputs

The gate evaluates results from `eval/locomo/`, `eval/longmemeval/`,
`eval/latency/` (Q1+Q2+Q3 harnesses) and the per-competitor JSONs in
`benchmark/results/`. To publish, the following must hold simultaneously:

1. **LoCoMo R@5** — nox-mem ≥ best competitor − 0.5pp (top or tied within
   the 95% CI of the published number).
2. **LongMemEval overall accuracy** — nox-mem ≥ best competitor − 0.5pp.
3. **p95 latency (search.medium)** — nox-mem ≤ best competitor + 5ms
   (top or tied within negligible delta).
4. **Autonomy axis** — nox-mem is self-host without proprietary daemon
   dependencies (this is a fixed-by-design win, not a measurement).

If any of (1), (2), (3) fails → **DO NOT PUBLISH**. Move to Lab.

If autonomy axis (4) is the *only* axis where competitors lose, that alone is
not enough for publication — the numeric axes must be at parity or better,
because a comparison page that loses on numbers and wins only on autonomy
looks defensive.

### Gate mechanics

```
GATE_VERIFIED=1 \
  LOCOMO_RESULTS_DIR=eval/locomo/results \
  LONGMEMEVAL_RESULTS_DIR=eval/longmemeval/results \
  LATENCY_RESULTS_DIR=eval/latency/results \
  npx tsx benchmark/generate-comparison.ts
```

Without `GATE_VERIFIED=1`, `generate-comparison.ts` refuses to write any
output file. It will print a gate-status table and exit non-zero.

The gate verification flag is a **manual human action** after reviewing the
inputs. The script does *not* set this itself based on numbers — that decision
is the human's, and intentionally so. Automation here would risk publishing
an unfavourable comparison if a metric flipped.

### Going back to the Lab

If the gate fails:

1. The raw per-tool JSONs stay in `benchmark/results/` (gitignored by
   default; commit explicitly if the Lab finding warrants it).
2. The findings get written up as a private `lessons/<date>-comparison-lab.md`
   document.
3. `COMPARISON.md` is **not** generated. No partial publish, no "we win on 2/3"
   framing.
4. The next iteration plans whatever change is needed to close the gap and
   re-runs.

This is the same philosophy as feature shadow-mode (Fase 1.7b-b) — ship only
when the data supports it.

---

## Methodology umbrella

The principles below apply to every benchmark folder. Per-benchmark templates
restate them in their own context.

### Default settings, not optimised

Every competitor is tested with the settings **its README recommends**, not
the settings that would make our benchmark flatter for them or for us.

- Vector dim: whatever the tool defaults to.
- Top-K: 10 unless the tool's primary API uses something else.
- Indexing: same corpus loaded via each tool's "load these messages" path.
- No prompt engineering of competitor queries — the same question text goes
  in for every tool.

If a competitor *requires* configuration to function at all (e.g., DB URL,
API key), that is documented in `competitor-configs.json` and noted in the
results.

### Same dataset, same metric, same seed

- LoCoMo: the official HuggingFace `snap-research/locomo` corpus, the official
  questions, our parser at `eval/locomo/parser.ts`. R@5 from `eval/locomo/score.ts`.
- LongMemEval: official `xiaowu0162/LongMemEval` v1, questions split as
  documented in `eval/longmemeval/README.md`. Accuracy from `eval/longmemeval/score.ts`.
- Latency: `eval/latency/` workloads (`search.short`, `search.medium`, `search.long`,
  `search.kg-heavy`, `ingest.entity-file`, `ingest.chunk-batch`).
- Seed = 42 everywhere. Stratified sampling matches the harnesses.

### 3 runs minimum, mean ± stddev

- Each competitor × benchmark combination is run **at least 3 times**.
- The reported number is the mean; the published spread is one stddev.
- Wall-clock conditions (warm cache, same machine, same load) are matched
  within each run set.

### Cost classification

- **Free tier** vs **paid** is annotated per competitor.
- **BYO key** vs **hosted** is annotated per competitor.
- Cost/month estimate assumes the workload that produced the benchmark
  numbers (not "what would 1k QPS cost?").

### Self-host classification

Three buckets:

- **yes** — runs entirely on user infra, no proprietary daemon, no required
  external service. nox-mem and built-in MEMORY.md sit here.
- **with proprietary daemon** — open-source surface but a closed/binary core
  is required (e.g., agentmemory's iii-engine). Disclosed in the table.
- **SaaS only** — must talk to vendor's hosted backend (e.g., Memanto's
  Moorcheh). Disclosed in the table.

### Reproducibility

Each benchmark publishes:

- The exact tool version (npm/pip output + git SHA if vendored).
- The exact corpus version (HuggingFace revision pin).
- The exact harness commit.
- The raw per-question JSON output (in `benchmark/results/`).

A third party with our `competitor-configs.json` and the harness should be
able to reproduce the numbers within ±1pp of accuracy and ±10% of latency.

---

## Honest caveats

These are *built into the template*. They publish whether nox-mem wins or
ties — they do not disappear in the marketing pass.

- **Snapshot in time.** Tool versions move, vendors release, our own code
  changes. Numbers are stamped with a date.
- **Quarterly re-run pledge.** This page is re-generated quarterly (Mar, Jun,
  Sep, Dec). If a competitor pulls ahead, we publish it ahead.
- **Judge variance for LongMemEval.** LLM-as-judge scoring has inter-run
  variance. We use Gemini 2.5 Flash for judging and report inter-judge
  agreement.
- **Conflicts of interest.** We built nox-mem. The benchmark is run by us.
  Raw data is published so any party can re-score independently. We invite
  PRs that improve any competitor's configuration.
- **Where we might not win.** The template carves out a section for axes
  where we lose or tie (e.g., we may lose on raw inference speed against a
  pure-FAISS tool, or on hosted convenience against Memanto). These are
  named, not hidden.

---

## How to extend

To add a new competitor:

1. Append an entry to `competitor-configs.json` (see schema in that file).
2. Add a `BLOCKED.md` entry if you cannot reach their eval interface.
3. Run `npx tsx benchmark/collect-competitor-data.ts --competitor <name> --dataset locomo --dry-run`
   to validate the config without consuming API quota.
4. Once validated, drop `--dry-run` (requires VPS + API access; see `BLOCKED.md`).

To add a new dimension (e.g., a new benchmark):

1. Build the harness under `eval/<name>/` following the Q1/Q2/Q3 pattern.
2. Add a `<NAME>.md.template` here.
3. Wire the new dataset into `collect-competitor-data.ts` and
   `generate-comparison.ts`.
4. Update the gate criteria above.

---

## Status

- **Q1 (LoCoMo harness)** — PR #6 (scaffolded).
- **Q2 (LongMemEval harness)** — PR #11 (scaffolded).
- **Q3 (latency harness)** — PR #12 (scaffolded).
- **Q4 (this directory)** — scaffolded; awaits Q1+Q2+Q3 numeric outputs and
  the per-competitor runs documented in `BLOCKED.md`.

See `docs/HANDOFF.md` for the live state.
