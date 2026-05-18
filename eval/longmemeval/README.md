# LongMemEval Evaluation Harness — memoria-nox

> **Status: scaffold only. No published numbers. Dry-run validates pipeline; full run is human-supervised.**

## What this is

A reproducible benchmark of **memoria-nox's full hybrid stack** (FTS5 BM25 +
sqlite-vec Gemini 3072d semantic + RRF fusion k=60) on the **LongMemEval**
dataset (Di Wu et al., ICLR 2025) — the canonical long-term-memory QA
benchmark for chat assistants.

Sister harness of `eval/locomo/` (PR #6). Where LoCoMo measures *retrieval
recall* against gold evidence chunks (R@5, MRR, nDCG@10), LongMemEval measures
**task accuracy on the end-to-end QA pipeline**: ingest → retrieve →
generate → judge. The two harnesses are complementary, not redundant. See
"Why LongMemEval differs from LoCoMo" below.

## Dataset

| | |
|---|---|
| Source | https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned |
| Repo (paper code) | https://github.com/xiaowu0162/LongMemEval |
| Citation | Di Wu et al. *LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory.* ICLR 2025. arXiv:2410.10813. |
| License | **MIT** (dataset + paper code) — non-commercial restrictions lift here vs LoCoMo, but the data is **still not ours to redistribute inside the repo**: see "Licensing footprint" below. |
| Commit pin | `98d7416c24c778c2fee6e6f3006e7a073259d48f` (resolved 2026-05-17; written to `dataset.lock.json` on first download). |
| Deprecation note | The original `xiaowu0162/longmemeval` repo was **deprecated 2025-09-19**; noisy history-session data was cleaned. Always use `longmemeval-cleaned`. |
| Splits | `longmemeval_oracle` (evidence-only, smallest, ~500 q with only the relevant history) — dry-run; `longmemeval_s_cleaned` (~115k-token haystacks, ~40 sessions) — paper headline; `longmemeval_m_cleaned` (~500-session haystacks) — harder track, deferred. |
| Question count | 500 total across all splits. |
| Categories (7) | `single-session-user`, `single-session-assistant`, `single-session-preference`, `temporal-reasoning`, `knowledge-update`, `multi-session`, plus an `_abs` suffix for abstention variants ("the assistant should answer it doesn't know"). |
| Per-question schema | `question_id`, `question_type`, `question`, `answer`, `question_date`, `haystack_session_ids[]`, `haystack_dates[]`, `haystack_sessions[]` (each turn may have `has_answer: true`), `answer_session_ids[]`. |

### Why LongMemEval differs from LoCoMo

| Axis | LoCoMo (E04 / Q1) | LongMemEval (Q2 / this harness) |
|---|---|---|
| Primary metric | Retrieval recall (R@5, R@1, MRR, nDCG@10) | **Task accuracy** (LLM-as-judge: was the generated answer correct?) |
| Unit of gold | `evidence: ["D1:3", ...]` — turn-level chunk IDs | `haystack_sessions[].has_answer = true` (session-level), plus a ground-truth `answer` string |
| Pipeline stages measured | ingest → retrieve | ingest → retrieve → **generate** → **judge** |
| Judge | None (binary chunk-ID set match) | **GPT-4o LLM-as-judge** (paper-standard, comparability) |
| Difficulty axis | Long-term conversational recall (avg 19 sessions / conv) | **Mixed long-context**: oracle (easy plumbing), S (~115k tokens, paper headline), M (~500 sessions, frontier) |
| What it tells us | Does the retrieval substrate find the right turns? | Does memoria-nox + an LLM **actually answer questions correctly** under realistic long-horizon load? |

LoCoMo isolates the retrieval substrate. LongMemEval is end-to-end. Both
matter; running them in parallel surfaces whether a retrieval gain (R@5 ↑)
actually translates to an answer-quality gain (accuracy ↑) or is eaten by
generation/judging noise.

### Licensing footprint

LongMemEval-cleaned is MIT-licensed (much more permissive than LoCoMo's CC
BY-NC 4.0). We could *technically* commit it. We **do not**, for two
non-license reasons:

1. **Size & churn.** Full corpus is hundreds of MB across splits — bloats
   git history with regenerable artefacts.
2. **Provenance discipline.** Pinning to `commit SHA + sha256` in
   `dataset.lock.json` and re-fetching is the same discipline LoCoMo
   demands. Consistent ops > shaved download time.

The eval DB (`eval.db`) is a research artefact (gitignored). The hypothesis
files (one row per question with the generated answer and the judge's
verdict — `hypotheses/*.jsonl`) are also gitignored because they include
LongMemEval question text verbatim. **We commit harness code, this
protocol doc, the dry-run-sample.json (10 rows for plumbing only),
schema-shaped aggregate JSON, and full-run aggregate JSON.** Never raw
per-question dumps.

## Protocol decisions (all explicit on purpose)

### D1 — Split & dry-run target: **`longmemeval_oracle`, n=10 stratified, seed=42**

Why oracle (not S) for the dry-run:

- The oracle split contains only the *relevant* haystack sessions per
  question (no distractors). For plumbing validation we want fast,
  cheap, deterministic. S would force ingesting 40+ sessions per q for
  a dry-run that nobody will read — wasted Gemini budget.
- 10 questions stratified ≈ 1-2 per category across the 7 base categories
  (collapsing `_abs` variants into their parent for stratification — see
  D5). Exact distribution emitted by `run.ts --n 10 --seed 42`.
- Same seed-and-shuffle pattern as Q1 LoCoMo (`seededShuffle` LCG with
  per-category seed offset) — bit-for-bit reproducible.

Headline number (separate, not in this PR):

- **`longmemeval_s_cleaned`, n=100 stratified, seed=42** matches the
  paper's published headline (~115k-token haystacks, ~40 sessions per q).
- Full S sweep (all ~500 q on S) is `--full-corpus`. Toto runs this
  manually on the VPS with cost confirmation; one-shot.

### D2 — Scoring: **LLM-as-judge** (not string match)

LongMemEval explicitly mandates LLM-as-judge in its official harness
(`src/evaluation/evaluate_qa.py`). String-match scoring on natural-language
QA is known to under-count synonyms and over-count surface matches. We
follow the paper.

Judge configuration via env (default secondary, with explicit override):

| `LONGMEMEVAL_JUDGE=` | Model | When to use |
|---|---|---|
| `gpt-4o` (paper-default) | OpenAI GPT-4o | Headline run for comparability with paper / leaderboard. Requires `OPENAI_API_KEY`. |
| `gemini-2.5-pro` | Google Gemini 2.5 Pro | Cost-effective secondary; report alongside `gpt-4o` if both available. Already keyed via VPS `.env`. |
| `gemini-2.5-flash` (dry-run default) | Gemini 2.5 Flash | Cheapest. Used by the n=10 dry-run on `longmemeval_oracle`. Numbers are NOT publication-grade. |

Judge prompt is the paper's prompt (loaded inline in `score.ts`). Verdict
is binary `correct: true|false` parsed from the structured response.

**We will run BOTH `gpt-4o` and `gemini-2.5-pro` on the headline run and
report both numbers + a Cohen's-κ-style inter-judge agreement.** Disagreement
between judges is itself a methodology signal (paper §4.4 reports judge κ).

### D3 — Generator: **memoria-nox hybrid search → prompt → LLM**

Per question:

1. Set `question_date` as the assistant's "current date".
2. Ingest `haystack_sessions[]` into an isolated `eval.db`, one
   `session_<idx>` markdown chunk per session (NOT per turn — see D6 vs
   LoCoMo D1). Tag with `haystack_dates[idx]` so temporal-reasoning
   questions have ground for date math.
3. Issue `question` against the hybrid search (FTS5 + Gemini semantic +
   RRF k=60) via the **CLI default** (`nox-mem search "<q>" --json
   --limit 20 --db <eval.db>`) or HTTP (`--api`).
4. Format a prompt that bundles top-K retrieved chunks + `question_date`
   + `question`; call a **generator LLM** (default
   `gemini-2.5-flash-lite` per CLAUDE.md §3 to stay inside the 3M/d
   free tier; `gemini-2.5-flash` and `gpt-4o` available via env
   `LONGMEMEVAL_GENERATOR=`).
5. Store the LLM's free-text answer alongside `gold_answer`,
   `question_id`, `question_type`, `retrieved_chunk_ids[]`,
   `retrieval_ms`, `generation_ms`.
6. Hand off to `score.ts` which calls the judge model for each
   `(question, gold_answer, generated_answer)` triple → verdict.

### D4 — Ingestion granularity: **per-session** (NOT per-turn)

This is the deliberate divergence from LoCoMo Q1 D1.

- LongMemEval's gold is `answer_session_ids[]` — a session-level marker
  ("the answer is somewhere in session X") plus a `has_answer: true`
  flag on individual turns within that session for the more granular
  evidence trail.
- For QA (not retrieval-recall), the *answer-generation prompt* benefits
  from session-level chunks: the LLM gets coherent context, not isolated
  utterances. Per-turn chunks fragment dialogue and hurt accuracy.
- Trade-off accepted: nox-mem hybrid retrieval on session-sized chunks
  is closer to production usage (note files, journal entries) than the
  per-turn LoCoMo mode. Different framing for different question.

`chunk_text` per session = newline-joined `f"{turn.role}: {turn.content}"`
with a leading `[session_id={sid} date={date}]` header so the FTS5 index
and the LLM both see the date.

### D5 — Stratified sampling across 7 categories + abstention

Categories used for stratification (collapsing `_abs` into parent):

1. `single-session-user`
2. `single-session-assistant`
3. `single-session-preference`
4. `temporal-reasoning`
5. `knowledge-update`
6. `multi-session`

With `_abs` variants folded in, 6 strata. Dry-run n=10 ≈ 1-2 per stratum,
seed=42, LCG shuffle. Per-category accuracy emitted by `score.ts` for
both base and `_abs` separately (the abstention variants are scored
correct-iff-the-assistant-said-it-doesn't-know — judge prompt switches
on `_abs` suffix). See "What is NOT covered" §3 for nuance.

### D6 — Isolation: **dedicated `eval.db`, never touch `nox-mem.db`**

`eval/longmemeval/eval.db` is created fresh per run. The harness sets
`OPENCLAW_WORKSPACE=eval/longmemeval/.workspace` (or `--db <path>` CLI
flag). A safeguard in `run.ts` aborts if the resolved DB path looks
like the production `nox-mem.db` at
`/root/.openclaw/workspace/tools/nox-mem/nox-mem.db`. **CONSTRAINT-CRITICAL.**

Re-running flushes `eval.db` and re-embeds. No persistent leakage between
question batches (a question can have date-sensitive answers that would
poison a later question if the haystack persisted — see paper §3.2).

## What is NOT covered (yet)

1. **No published task-accuracy number yet.** Dry-run output is plumbing
   validation only (n=10, oracle split, cheap judge). The headline run
   on `longmemeval_s_cleaned, n=100` is human-supervised in a follow-up
   session; numbers go into paper §5.4 or a paper-PR.
2. **No M-split run.** `longmemeval_m_cleaned` (~500-session haystacks)
   is the frontier track. Cost ~10× S and Gemini context limits start
   biting. Deferred until S is published.
3. **Abstention category scoring nuance.** `_abs` variants demand the
   assistant *refuse to answer*. Our judge prompt has two code paths
   (correct-if-answered for non-`_abs`, correct-if-refused for `_abs`)
   but we have not yet calibrated against the paper's reference
   abstention judge. Treat per-category `_abs` numbers as best-effort
   in the headline run; document the calibration gap explicitly.
4. **No multi-seed statistical significance.** seed=42 is fixed for
   reproducibility. Multiple-seed runs to bound stratification variance
   are a follow-up — out of scope here.
5. **No competitor head-to-head.** We measure ourselves on LongMemEval
   following the paper's protocol. We do not re-run LangMem / Letta /
   Mem0 / Zep. Their published numbers (paper Tables 2-3) are taken
   as-is with the same caveat as LoCoMo Q1: their methodology details
   may differ and that itself is a result worth surfacing in our paper.
6. **No KG / salience / pain interaction in scope.** Same as Q1: nox-mem's
   KG entities and pain-weighted salience are production features.
   LongMemEval sessions are not entity-extracted (would take days), and
   pain is meaningless for a synthetic corpus. We measure the
   FTS5+dense+RRF substrate only. KG-as-router is a separate experiment.

## Reproduction steps

```bash
# 1. Install deps (run from repo root)
cd /Users/lab/Claude/Projetos/memoria-nox
npm i --no-save tsx better-sqlite3   # if not present in package.json

# 2. Set env (provides GEMINI_API_KEY for embeddings + generator,
#             OPENAI_API_KEY for paper-grade GPT-4o judge,
#             OPENCLAW_WORKSPACE)
set -a; source /root/.openclaw/.env; set +a

# 3. Download dataset (writes eval/longmemeval/data/longmemeval_oracle.json
#    + longmemeval_s_cleaned.json — both gitignored)
npx tsx eval/longmemeval/download.ts --split oracle
npx tsx eval/longmemeval/download.ts --split s_cleaned

# 4. Parse + ingest oracle into eval.db (for dry-run)
npx tsx eval/longmemeval/parser.ts --split oracle --ingest

# 5. Dry-run 10 questions (cheap Gemini flash judge + generator)
LONGMEMEVAL_JUDGE=gemini-2.5-flash \
LONGMEMEVAL_GENERATOR=gemini-2.5-flash-lite \
  npx tsx eval/longmemeval/run.ts --split oracle --n 10 --seed 42 --cli \
  > eval/longmemeval/dry-run-sample.json

# 6. Score (calls judge for each q)
npx tsx eval/longmemeval/score.ts eval/longmemeval/dry-run-sample.json
```

For the headline run (Toto only, on VPS, with cost confirmation):

```bash
# n=100 on the S-cleaned split, paper headline. Run BOTH judges.
LONGMEMEVAL_JUDGE=gpt-4o \
LONGMEMEVAL_GENERATOR=gemini-2.5-flash \
  npx tsx eval/longmemeval/run.ts --split s_cleaned --n 100 --seed 42 \
    --cli --full > eval/longmemeval/full-run.gpt4o.json
npx tsx eval/longmemeval/score.ts eval/longmemeval/full-run.gpt4o.json --ci

LONGMEMEVAL_JUDGE=gemini-2.5-pro \
LONGMEMEVAL_GENERATOR=gemini-2.5-flash \
  npx tsx eval/longmemeval/run.ts --split s_cleaned --n 100 --seed 42 \
    --cli --full > eval/longmemeval/full-run.gemini25pro.json
npx tsx eval/longmemeval/score.ts eval/longmemeval/full-run.gemini25pro.json --ci
```

## Files in this directory

| File | Purpose | Generated |
|---|---|---|
| `README.md` | This protocol document. | hand-written |
| `download.ts` | Fetches LongMemEval splits from HuggingFace; writes `data/<split>.json` + `dataset.lock.json`. | scaffold |
| `parser.ts` | Parses dataset → `(question_id, question_type, question, answer, haystack_session_ids, haystack_dates, haystack_sessions, answer_session_ids)` tuples + per-session chunk records. | scaffold |
| `run.ts` | Per question: ingest haystack → hybrid search → generator LLM → record hypothesis. | scaffold |
| `score.ts` | Per-record LLM-as-judge call → task accuracy overall + per category + per `_abs` variant + Wilson 95% CI. | scaffold |
| `dry-run-sample.json` | Output of the 10-question dry-run (plumbing validation). | generated by `run.ts` |
| `data/*.json` | Cached dataset splits. **gitignored.** | downloaded |
| `dataset.lock.json` | Resolved commit SHA + per-split sha256. **gitignored.** | downloaded |
| `eval.db` | Isolated SQLite + FTS5 + sqlite-vec database for the eval corpus. **gitignored.** | built |
| `hypotheses/<run>.jsonl` | Per-question hypothesis dump (gold + generated answer + judge verdict). **gitignored** (contains question text verbatim). | generated |
| `BLOCKED.md` | Created only if scaffold hits a hard block. | conditional |

## Versioning

This harness lives at `eval/longmemeval/` on the
`overnight/2026-05-17/Q2-longmemeval-harness` branch (PR target `main`).
Once merged, future ranking / generation / judging changes that affect
end-to-end accuracy MUST re-run this harness and commit a delta vs the
previously published number (CLAUDE.md §5: scoring/ranking changes are
feature work, never "fix" commits).

## Open questions for Toto (non-blocking)

1. **Judge cost vs comparability.** GPT-4o on 500 q is non-trivial USD.
   Are we OK budgeting it for the headline run, or do we publish a
   Gemini-2.5-pro-only number first and add the GPT-4o run as a
   follow-up when budget approves?
2. **Generator choice for the headline.** Default in dry-run is
   `gemini-2.5-flash-lite` (cheapest, CLAUDE.md §3). For the publishable
   headline we likely want `gemini-2.5-flash` (full) or even
   `gemini-2.5-pro` to reduce generator-noise contamination of the
   memoria-nox retrieval signal. Decision needed before full S run.
3. **Should LongMemEval task-accuracy become a CI gate?** Currently no
   — full runs are manual + expensive. Same answer as LoCoMo Q1 by
   default; revisit if cost-per-run drops (e.g. via a smaller fixed
   eval slice that's both stable and cheap).

---

*Authored 2026-05-17 by executor-high overnight agent. Per task constraint: no published numbers in this PR. Mirrors `eval/locomo/` (Q1 PR #6) pattern; structural parity intentional.*
