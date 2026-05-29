# LoCoMo Evaluation Harness — memoria-nox

> **Status (2026-05-29):** Two harnesses now coexist in this directory:
>
> 1. **TypeScript scaffold** (`parser.ts`, `run.ts`, `score.ts`, `download.ts`)
>    — original 2026-05-18 design, IR-style nDCG@10/MRR/R@10/P@5 over the
>    LoCoMo conversation corpus. Useful for direct comparison vs FTS5
>    baselines.
> 2. **Python cross-bench harness** (`adapter_nox_mem.py`, `run-bench.sh`,
>    `lib/{corpus_loader,scorer,aggregate}.py`) — 2026-05-29 design,
>    end-to-end QA accuracy (LoCoMo paper §4.2 F1) using nox-mem as memory
>    layer + gpt-4.1-mini as generator. Mirrors `eval/longmemeval/` and
>    `eval/evermembench/` patterns for cross-bench parity.
>
> See `README-CROSSBENCH.md` + `METHODOLOGY-CROSSBENCH.md` for the Python
> harness; this file documents the TypeScript scaffold.

## What this is

A reproducible benchmark of **memoria-nox's full hybrid stack** (FTS5 BM25 +
sqlite-vec Gemini 3072d semantic + RRF fusion k=60) on the **LoCoMo** (Long-term
Conversation Memory) dataset published by snap-research.

This is *not* the same as the existing FTS5-only LoCoMo run in
`paper/publication/baselines/locomo_eval.py` (E04, 2026-05-04, nDCG@10=0.281,
n=100, FTS5 vanilla). That run isolated the lexical baseline and was
[honestly disclosed][honest] as deferring the hybrid measurement. This harness
closes that gap.

[honest]: ../../paper/publication/results/E04-locomo-summary.md "Honest disclosures point #2"

## Dataset

| | |
|---|---|
| Source | https://github.com/snap-research/locomo |
| File | `data/locomo10.json` (~9 MB) |
| Mirror URL | `https://raw.githubusercontent.com/snap-research/locomo/main/data/locomo10.json` |
| License | **CC BY-NC 4.0** (non-commercial only — see §"Licensing footprint" below) |
| Citation | Maharana, Lee, Tulyakov, Bansal, Barbieri, Fang. *Evaluating Very Long-Term Conversational Memory of LLM Agents*. arXiv:2402.17753, 2024. |
| Commit pin | **TBD on first download** — `download.ts` writes the resolved git SHA into `dataset.lock.json` (gitignored copy) and the README is updated by the runner on full-run. Dry-run uses `main` HEAD. |
| Schema | `list[10]` of conversations. Each has `sample_id`, `qa[]`, `conversation.session_N[]` (turns with `dia_id`, `speaker`, `text`), plus `event_summary`/`observation`/`session_summary`. |
| QA categories | 1=single-hop (282), 2=multi-hop (321), 3=temporal (96), 4=open-domain (841), 5=adversarial (446) — 1,986 questions total across 5,882 dialogue turns. |
| Evidence format | `evidence: ["D1:3", ...]` where `D1:3` = session 1 turn 3 (matches `session_1[i].dia_id`). |

### Why LoCoMo

- **Standard external benchmark** with growing competitor uptake. rohitg00/agentmemory publishes R@5 = 95.2% on a LoCoMo-like setup; memoria-nox currently has zero comparable number.
- **Long-term conversational** structure (avg 19 sessions / conversation) stresses memory recall in ways that snapshot QA benches do not.
- **Public, license-permissive for research** (CC BY-NC 4.0 — see footprint note).

### Licensing footprint

`locomo10.json` ships **CC BY-NC 4.0**. This means:

- ✅ academic paper §5.3 reproduction, blog posts, research artefacts: OK.
- ❌ shipping the dataset (or derivative chunks) inside the commercial nox-supermem distribution: **not OK**.
- The eval DB (`eval.db`) at `eval/locomo/eval.db` is **a research artefact** and is `.gitignored`. The dataset cache file is also gitignored. We commit only the harness code, the protocol doc, and aggregate JSON summaries — never raw conversation text or per-question dumps that include LoCoMo content verbatim.

## Protocol decisions (all explicit on purpose)

### D1 — Ingestion granularity: **per-turn**

Each `session_N[i]` turn is one chunk. `chunk_text = f"{speaker}: {text}"`,
`chunk_id = f"{sample_id}::{dia_id}"`. Rationale:

- The dataset's `evidence` field points to individual turns via `dia_id`. To match competitor protocol and existing FTS5 baseline (E04), the unit of retrieval *must* be the turn.
- Per-session would inflate recall artificially (one turn correct → whole session counts). Per-message subword would deflate it (BM25 underranks tiny chunks).
- Trade-off accepted: nox-mem in production usually ingests at file/document granularity. The per-turn mode here is purpose-built for LoCoMo and isolated in `eval.db`; it does *not* reflect the production retention/section/salience pipeline. That is acknowledged as a measurement framing choice — see "What is NOT covered" §3 below.

### D2 — Correct retrieval judgement: **chunk-ID set match (binary)**

`retrieved_chunk_id ∈ gold_chunk_ids` ⇒ relevant (1), else not (0). No LLM-as-judge, no semantic answer scoring. Rationale:

- LoCoMo provides explicit `evidence` lists; that is the authoritative gold. Anything else introduces a judge model whose biases and cost dwarf the actual retrieval signal.
- Matches the methodology already used in `paper/publication/baselines/locomo_eval.py` so the FTS5-only number and the hybrid number are directly comparable.
- Binary (not graded). LoCoMo does not provide graded relevance.
- We do **not** score answer correctness, only retrieval. Answer generation would compound retrieval and LLM-quality signals; we want the retrieval question answered cleanly.

### D3 — Metrics: **R@5, R@1, MRR, nDCG@10** (all four reported)

- **R@5** is the headline competitor metric (rohitg00 claim). Report it first.
- **R@1** stresses precision-at-top (most useful for agent grounding).
- **MRR** captures rank quality across the full top-K.
- **nDCG@10** lets us compare against E04's FTS5-only number directly (apples-to-apples).
- Top-K retrieved = 20. All metrics computed off that list.

### D4 — Sampling for dry-run: **10 questions, stratified, seed=42**

2 questions per category (1=single-hop, 2=multi-hop, 3=temporal,
4=open-domain, 5=adversarial). Purpose is to validate end-to-end plumbing
(download → parse → ingest → search → score → JSON), **not** to produce a
statistically meaningful estimate. Full-run is 100 stratified
(20/category) matching E04 to allow direct comparison, with the option of
the full 1,986 if Toto wants it.

### D5 — Search interface: **HTTP API preferred, CLI fallback**

`run.ts` calls `POST http://127.0.0.1:${NOX_API_PORT}/api/search` with
`{"query": ..., "limit": 20, "db": "<eval.db path>"}` when an `--api` flag
is set. Default for dry-run is `--cli` which shells out to
`nox-mem search "<q>" --json --limit 20 --db <eval.db>` (avoids
contaminating prod API logs and salience). Both paths are scaffolded; CLI
is what the dry-run exercises.

### D6 — Isolation: **dedicated `eval.db`, never touch `nox-mem.db`**

`eval/locomo/eval.db` is created fresh per run. The harness sets
`OPENCLAW_WORKSPACE=eval/locomo/.workspace` (or equivalent CLI flag) so the
prod DB at `/root/.openclaw/workspace/tools/nox-mem/nox-mem.db` is never
opened. **CONSTRAINT-CRITICAL.** A safeguard in `run.ts` aborts if
`process.env.NOX_DB_PATH` resolves to anything containing `nox-mem.db` not
prefixed by the eval workspace.

### D7 — Embedding budget

Per-turn embedding of 5,882 turns via Gemini gemini-embedding-001 (3072d).
Empirical cost from prior bulk runs: ~\$0.05 USD per full corpus. Dry-run
n=10 embeds only the conversations those 10 questions reference (~1-2
conversations, ~600-1200 turns) so cost is <\$0.01. Full run is
deliberately one-shot — re-running flushes `eval.db` and re-embeds.

## What is NOT covered (yet)

1. **No published R@5 yet.** Dry-run output is plumbing validation only. Toto runs the full n=100 (or n=1986) sweep himself in a subsequent session; numbers go into the paper §5.3 or a paper-PR.
2. **No statistical significance test.** n=10 dry-run gives no CI. Full n=100 enables binomial CI on R@5 / R@1; n=1986 enables non-trivial subgroup CIs per category. Both are computed in `score.ts` when called with `--ci`.
3. **No per-turn vs per-session ablation.** D1 fixed at per-turn. Whether per-session ingestion would change the result is an open question; defer to follow-up spec.
4. **No competitor head-to-head.** We measure ourselves on LoCoMo. We do not re-run rohitg00/agentmemory. Their 95.2% R@5 number is taken as-published with the caveat that their methodology details may differ (which is itself a result worth surfacing in the paper).
5. **No LLM-judge variant.** D2 fixed at binary evidence-match. If reviewers request answer-quality scoring, a `--judge` mode can be added later; out of scope here.
6. **No KG / salience / pain interaction.** memoria-nox's KG entities and pain-weighted salience are nox-mem production features. LoCoMo turns are not entity-extracted, and pain is meaningless for a synthetic corpus. We measure the retrieval substrate (FTS5 + dense + RRF) only. This is an honest disclosure about scope, not a hidden limitation.

## Reproduction steps

```bash
# 1. Install deps (run from repo root)
cd /Users/lab/Claude/Projetos/memoria-nox
npm i --no-save tsx better-sqlite3   # if not present in package.json

# 2. Set env (provides GEMINI_API_KEY for embeddings, OPENCLAW_WORKSPACE)
set -a; source /root/.openclaw/.env; set +a

# 3. Download dataset (writes eval/locomo/data/locomo10.json — gitignored)
npx tsx eval/locomo/download.ts

# 4. Parse + ingest (writes eval/locomo/eval.db)
npx tsx eval/locomo/parser.ts --ingest

# 5. Dry-run 10 questions
npx tsx eval/locomo/run.ts --n 10 --seed 42 --cli > eval/locomo/dry-run-sample.json

# 6. Score
npx tsx eval/locomo/score.ts eval/locomo/dry-run-sample.json
```

For the full run (Toto only):

```bash
npx tsx eval/locomo/run.ts --n 100 --seed 42 --cli --full > eval/locomo/full-run.json
npx tsx eval/locomo/score.ts eval/locomo/full-run.json --ci
```

## Files in this directory

| File | Purpose | Generated |
|---|---|---|
| `README.md` | This protocol document. | hand-written |
| `download.ts` | Fetches LoCoMo dataset; writes `data/locomo10.json` + `dataset.lock.json`. | scaffold |
| `parser.ts` | Parses dataset → `(chunk_id, session_id, turn_text)` tuples; can also drive ingest into `eval.db`. | scaffold |
| `run.ts` | Issues queries against memoria-nox (CLI or HTTP), collects top-K chunk-IDs per question. | scaffold |
| `score.ts` | Computes R@5, R@1, MRR, nDCG@10 (+ optional binomial CI); emits JSON. | scaffold |
| `dry-run-sample.json` | Output of the 10-question dry-run (validates plumbing). | generated by `run.ts` |
| `data/locomo10.json` | Cached dataset. **gitignored.** | downloaded |
| `dataset.lock.json` | Resolved commit SHA + sha256 of dataset file. | downloaded |
| `eval.db` | Isolated SQLite + FTS5 + sqlite-vec database for the eval corpus. **gitignored.** | built |
| `BLOCKED.md` | Created only if scaffold hits a hard block (dataset missing, methodology unclear, etc). | conditional |

## Versioning

This harness lives at `eval/locomo/` on the `overnight/2026-05-17/Q1-locomo-harness` branch (PR target `main`). Once merged, future ranking / scoring changes that affect search MUST re-run this harness and commit a delta vs the previously published number (CLAUDE.md §5: scoring changes are feature work, never "fix" commits).

## Open questions for Toto (non-blocking)

1. Should the full-run target be n=100 (matches E04 directly) or n=1986 (whole dataset, statistically meaningful subgroups)? Default is n=100 unless overridden with `--full-corpus`.
2. Do we want a parallel `--no-hybrid` switch (FTS5-only same harness) to produce an apples-to-apples lift number vs E04 in the same run, with same code path? `parser.ts` and `run.ts` are written to support it; default off.
3. Long-term: should LoCoMo R@5 become a CI gate (regression alarm if it drops >2pp)? Currently no — full runs are manual.

---

*Authored 2026-05-17 by scientist-high overnight agent. Per task constraint: no published numbers in this PR.*
