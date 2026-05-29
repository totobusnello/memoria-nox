# Phase H — EverMemBench GPT-4.1-mini Backbone Parity (batch 004)

**Spec:** `specs/2026-05-28-phase-h-gpt41mini-parity.md` (commit a6ef866)
**Date:** 2026-05-28
**Predecessor results:** Phase D (PR #365, batch 004 = 61.98% on gemini-2.5-flash)
**Parallel:** Phase G 5-batch (ports 18816–18819) — isolated to port 18820

## Headline

**BLOCKED — funding gate (HTTP 402 from OpenRouter, balance $0).** No GPT-4.1-mini answer call could complete. Setup + ingest + vectorize + search all worked correctly; the only failure surface is the LLM-backbone billing.

Gate decision: **STOP** (no batch 004 numbers produced — funding-side blocker, not adapter/methodology). Paper §5 cross-backbone claim **status quo**: not yet defensible, will be re-attempted once OpenRouter is topped up or a working direct `OPENAI_API_KEY` is provisioned.

## What the spec assumed (and where it broke)

> Spec §"Prereq — API key": *"Confirmar `OPENAI_API_KEY` em `/root/.openclaw/.env` na VPS (provavelmente já existe para outros adapters Q4)."*

VPS state at run time (2026-05-28 20:43 BRT):

| Variable | Present? | Validation | Result |
|---|---|---|---|
| `OPENAI_API_KEY` | yes (162 chars, `sk-proj-...hcUA`) | `curl https://api.openai.com/v1/chat/completions` | **HTTP 401** — *"Incorrect API key provided: sk-proj-...hcUA"* |
| `OPENROUTER_API_KEY` | yes (73 chars, `sk-or-v1-9...f097`) | `curl https://openrouter.ai/api/v1/chat/completions` | HTTP 200 OK for preflight (cost $0.0000084) |
| OpenRouter balance | — | `GET /api/v1/credits` | `{"total_credits":0,"total_usage":0.34225205}` |
| `ANTHROPIC_API_KEY` | disabled (commented as `#_DISABLED_ANTHROPIC_API_KEY`) | — | Not viable as fallback backbone |

Both OpenAI routes are non-operational. The OpenRouter key authenticates but has no credits — preflight (which costs ~$0.0000084) passes; the actual 626-query batch (which would consume ~$0.10–0.30) returns HTTP 402 *Insufficient* on every call and retries 20× per question.

The harness preflight in `run-batch-phaseH.sh` ("Reply only OK", 13 tokens) succeeded because OpenRouter still serves zero-cost-equivalent calls or accepts the first sub-cent debit. Real query volume exhausts the floor immediately.

## Where Phase H got to before the block

| Step | Status | Evidence |
|---|---|---|
| 1. Init fresh DB schema (v18 + KG) | ✅ | `chunks=0` on `/api/health` |
| 2. Spawn isolated nox-mem api-server on port 18820 | ✅ | `pid=269125, Listening on 127.0.0.1:18820` |
| 2b. Preflight (`/api/search?q=test`) | ✅ | `[]` (empty corpus, no errors) |
| 2b'. Preflight OpenRouter | ✅ | `OpenRouter preflight OK` (single "Reply only OK") |
| 3. Add stage (10,222 messages × 254 days) | ✅ (warnings) | `10033 chunks, 21 errors (0.2%)` — typical Phase B behaviour |
| 4. Vectorize (Gemini 3072d) | ✅ | `embedded=10033/10033`, `orphans=0` |
| 5. Clear stale results files | ✅ | `cleared stale results files in eval/results/nox_mem` |
| 6. Search stage (626 questions, top-k=20) | ✅ | `Search completed: 626 results` |
| 7. **Answer stage (openai/gpt-4.1-mini)** | ❌ **BLOCKED** | HTTP 402 Insufficient on every call; retries 1→20 with exponential backoff |
| 8. Evaluate stage (gemini-2.5-flash judge) | not reached | — |

Total wall clock to the block: ~28 minutes (add + vectorize were the dominant cost; search completed in ~2 min).

## MemOS Table 4 GPT-4.1-mini column (paper reference) — for posterity

Source: arxiv 2602.01313 §4.2, Table 4 (Page 6 / line 412 of `pdftotext -layout`).

> Hu, C. et al. (2026). *Evaluating Long-Horizon Memory for Multi-Party Collaborative Dialogues.* arXiv:2602.01313. 25 pages, 21 figures, 10 tables.

Methodology per paper §4.1: *"all memory-augmented systems use GPT-4.1-mini as the answer model, allowing us to isolate retrieval effects."*

| Sub-dim | Column header | MemOS+GPT-4.1-mini (paper) |
|---|---|---:|
| F_SH (single-hop) | Single | 71.36 ± 6.1 |
| F_MH (multi-hop) | Multi | 18.88 ± 4.8 |
| F_TP (temporal) | Temp | 15.67 ± 4.0 |
| MA_C (constraint) | Const | 69.90 ± 4.5 |
| MA_P (proactive) | Proact | 51.99 ± 4.7 |
| MA_U (update) | Update | 45.15 ± 6.0 |
| P_Style | Style | 28.98 ± 6.5 |
| P_Skill | Skill | 32.54 ± 7.1 |
| P_Title (role) | Role | 48.47 ± 7.1 |
| **Overall** | **Average** | **42.55 ± 1.9 (+5.11)** |

(`+5.11` = delta vs GPT-4.1-mini Full Context baseline of 37.44.)

Full Context baseline (no memory) on this backbone: 37.44%. All four memory-augmented systems on GPT-4.1-mini fell within a 5 pp band (34.27–42.55%); MemOS was the highest. This is the bar nox-mem would have to clear to claim cross-backbone generalisation.

## Config that would have run (and what to reuse)

Both artefacts are committed in this PR:

- `eval/evermembench/pipeline-phaseH.yaml` — overrides Phase D pipeline.yaml with `answer.model: openai/gpt-4.1-mini`, `answer.api_key: ${OPENROUTER_API_KEY}`, `answer.base_url: https://openrouter.ai/api/v1`; keeps `evaluate.model: gemini-2.5-flash` so the OE judge is identical to Phase D (isolates the change to the answer-stage backbone).
- `eval/evermembench/run-batch-phaseH.sh` — wraps the Phase D launcher with: (a) explicit `NOX_RERANKER_ENABLED=0` + `unset NOX_RERANKER_MODEL` after `source .env`, isolating Phase H from Phase G's rerank state; (b) live preflight against OpenRouter before touching the DB; (c) port 18820 hardcoded so Phase G's 18816–18819 are untouched; (d) `rm` of stale `answer_results_*.json` / `evaluation_results_*.json` per `[[evermembench-eval-gotchas-2026-05-28]]`.

Per-stage backbone routing relies on the harness honouring `answer.api_key` and `answer.base_url` overrides from YAML (verified at `eval/src/core/answerer.py:88-96` of the EverMemBench harness commit shipped in `evermembench-phaseB-1779978778`).

## Unlock conditions (any one is sufficient to re-dispatch)

1. **Top up the OpenRouter account by ≥ $1.00.** Single batch 004 will then complete inside the $1 budget cap; `run-batch-phaseH.sh 004 18820` is idempotent against the existing artifacts (no code changes needed).
2. **Provision a working `OPENAI_API_KEY` (direct).** Update `pipeline-phaseH.yaml` to point `answer.base_url` at `https://api.openai.com/v1` and `answer.api_key` at `${OPENAI_API_KEY}`. Run script and harness stay unchanged.
3. **(Off-spec, escalate first)** Accept a different OpenAI-compatible backbone (e.g. Anthropic claude-3.5-sonnet via direct or Vertex) as the cross-backbone test. This would no longer be "parity vs MemOS Table 4 GPT-4.1-mini column", so paper §5.4 framing would need to widen from *"on GPT-4.1-mini too"* to *"on a second backbone too"*. Recommend NOT taking this path without explicit Toto sign-off — it weakens the paper claim.

Per spec §"Gate decision" the right call here is **STOP** — option 1 or 2 is funding/credentials work, not engineering, and Phase H setup is now fully reproducible.

## Cost

| Component | Estimated | Actual |
|---|---:|---:|
| OpenRouter preflight ("Reply only OK", 13 tokens) | ~$0.0000084 | $0.0000084 (one call) |
| OpenRouter answer batch | ~$0.10–0.30 | $0 (every call returned 402, no successful completion) |
| Gemini vectorize (free quota, not billed) | $0 | $0 |
| Gemini-2.5-flash OE judge | ~$0.05 | $0 (evaluate stage never reached) |
| **Total batch 004** | **~$0.40** | **~$0.0000084** |
| Budget cap | $1.00 | — |

## Paper §5 cross-backbone claim status

> **Not yet defensible.** Phase D win (62.22% vs MemOS 59.27%, batch 004 = 61.98%) remains a single-backbone (Gemini-2.5-Flash) result. The cross-backbone generalisation experiment is **set up but unrun**: harness, launcher, isolated workdir, OpenRouter routing, and MemOS Table 4 baseline (42.55%) are all locked in and reproducible. The only remaining gap is funding/credentials on the answer-LLM side.

Recommend §5 narrative for the current paper draft:
- §5.1: keep Phase D 5-batch win on Gemini-2.5-flash (unchanged).
- §5.4: **defer** "structural advantage is the adapter, not the backbone" — frame as future work. Sentence: *"Cross-backbone generalisation (e.g. GPT-4.1-mini, the answer model used in the original EverMemBench Table 4) is set up in `eval/evermembench/pipeline-phaseH.yaml` and `run-batch-phaseH.sh` and will be reported in a follow-up once a budgeted answer-LLM endpoint is available."*

## Anomalies / observations

1. **OpenRouter preflight passes but real batch fails on credits.** A 13-token "Reply OK" call (cost ~$8.4e-06) succeeded; the 626-question batch (cost ~$0.10–0.30) returned 402 *Insufficient* on every call. This is OpenRouter's billing-floor behaviour, not a key/model issue. Lesson for future preflights: do not infer "billing works" from a single sub-cent call. Either (a) check `/api/v1/credits` for non-zero balance before dispatch, or (b) run a 1k-token preflight to amortise enough that the billing floor is exercised.
2. **The 21 add-stage errors (0.2% of 10,222 messages) match Phase B / Phase D baseline behaviour** and are not Phase H-specific. They are not the blocker.
3. **Phase G's 4 parallel batches (005/010/011/016 on ports 18816–18819) were unaffected** — they use Gemini-2.5-flash answer backbone, not OpenRouter, and their `/api/health` shows them progressing normally.
4. **OPENAI_API_KEY in `/root/.openclaw/.env` is dead at OpenAI direct (401).** Worth a separate cleanup item — every adapter that ever assumes that variable will silently fail to authenticate. Either rotate or remove from the env file to fail loudly.

## Reproduction (once funding unblocks)

```bash
# Workdir + harness setup (one-time)
WORK=/tmp/phaseH-batch004-$(uuidgen)
mkdir -p "$WORK" && cd "$WORK"
git clone --depth 5 https://github.com/totobusnello/memoria-nox.git memoria-nox
cp -r /root/.openclaw/evermembench-phaseB-1779978778/everos "$WORK/everos"
ln -sfn /root/.openclaw/evermembench-phaseB-1779978778/venv "$WORK/venv"

# Deploy Phase H configs (from this PR)
cp memoria-nox/eval/evermembench/pipeline-phaseH.yaml \
   "$WORK/everos/benchmarks/EverMemBench/eval/config/pipeline.yaml"
cp memoria-nox/eval/evermembench/run-batch-phaseH.sh \
   "$WORK/everos/benchmarks/EverMemBench/run-batch-phaseH.sh"
chmod +x "$WORK/everos/benchmarks/EverMemBench/run-batch-phaseH.sh"

# Pre-dispatch check (NEW — added based on this failure)
set -a; source /root/.openclaw/.env; set +a
BAL=$(curl -s --max-time 30 https://openrouter.ai/api/v1/credits \
    -H "Authorization: Bearer $OPENROUTER_API_KEY" \
    | python3 -c "import json,sys;d=json.load(sys.stdin);print(d.get('data',{}).get('total_credits',0))")
if (( $(echo "$BAL < 1.0" | bc -l) )); then
    echo "ABORT: OpenRouter balance \$$BAL < \$1.00 — top up before dispatch"; exit 1
fi
echo "OpenRouter balance: \$$BAL — OK"

# Launch in tmux (port 18820, no Phase G conflict)
cd "$WORK/everos/benchmarks/EverMemBench"
source "$WORK/venv/bin/activate"
export WORK
tmux new-session -d -s phaseH "bash run-batch-phaseH.sh 004 18820 2>&1 | tee /tmp/phaseH-stream.log"
tmux attach -t phaseH    # monitor live; Ctrl-b d to detach
```

## Files in this PR

| File | Purpose |
|---|---|
| `eval/evermembench/RESULTS-PHASEH.md` | this report — blocker outcome, MemOS Table 4 baseline extracted, paper §5 status, reproduction recipe |
| `eval/evermembench/pipeline-phaseH.yaml` | Phase D pipeline.yaml with answer-stage backbone swapped to OpenRouter `openai/gpt-4.1-mini` (evaluate stage unchanged) |
| `eval/evermembench/run-batch-phaseH.sh` | Phase D launcher hardened: explicit reranker-OFF env, OpenRouter preflight, port 18820, stale results purge per `[[evermembench-eval-gotchas-2026-05-28]]` |
