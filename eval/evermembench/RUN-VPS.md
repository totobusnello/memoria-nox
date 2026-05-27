# EverMemBench batch 004 — VPS run checklist

> **Audience:** the next session that picks up batch 004 execution on the
> VPS (where nox-mem CLI + dist + API are installed).
>
> **Why deferred:** the local memoria-nox repo (and its GitHub remote)
> does NOT ship the runtime source tree — nox-mem source/dist lives
> exclusively at `/root/.openclaw/workspace/tools/nox-mem/` on the VPS
> (per `CLAUDE.md` and `paper/`). The 2026-05-27 attempt to run batch 004
> from the macOS dev host was therefore blocked: there is no `nox-mem`
> binary on PATH locally and the public repo can't bootstrap one.
>
> The adapter (Option B CLI subprocess) and Gemini-only LLM swap recipe
> ARE complete and committed in this PR; only the actual execution
> needs to happen from the VPS shell.

---

## 0. Prerequisites (one-time)

- [ ] Gemini API key available at `/tmp/.gemini-key-98949.txt` (or fresh path)
- [ ] VPS reachable at `187.77.234.79` (Hostinger floating IP, see
      `~/Claude/Projetos/memoria-nox/...` reference notes; healthcheck cron
      pings every 15 min)
- [ ] nox-mem CLI on PATH on VPS (`which nox-mem`); should resolve to
      `/root/.openclaw/workspace/tools/nox-mem/dist/index.js` via npm bin
- [ ] Disk free `df -h /tmp` shows ≥2 GB free for isolated DB

## 1. SSH into VPS and prepare workspace

```bash
ssh openclaw
TS=$(date +%s)
TMPDIR=/tmp/evermembench-run-$TS
mkdir -p "$TMPDIR"
cd "$TMPDIR"
```

## 2. Clone EverOS (fresh)

```bash
git clone --depth 1 https://github.com/EverMind-AI/EverOS "$TMPDIR/everos"
cd "$TMPDIR/everos/benchmarks/EverMemBench"
```

## 3. Set up Python venv

```bash
python3.12 -m venv .venv 2>/dev/null || python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 4. Copy nox-mem adapter from memoria-nox and register

```bash
# Adjust path to wherever this PR's tree is checked out on VPS
MEMNOX=/root/repos/memoria-nox
cp "$MEMNOX/eval/evermembench/adapter_nox_mem.py" \
   eval/src/adapters/nox_mem_adapter.py
```

Patch `eval/src/adapters/__init__.py` to register the adapter:

```python
# Append to the imports + ADAPTERS dict (exact path may vary by version)
from eval.src.adapters.nox_mem_adapter import NoxMemAdapter
ADAPTERS["nox_mem"] = NoxMemAdapter
```

Patch `eval/cli.py` `create_adapter()` function to route `nox_mem` system_name
(look for the dispatch block around line 100-130; mirror the `mem0` branch).

Create `eval/config/nox_mem.yaml`:

```yaml
name: "nox_mem"
api_base: "http://127.0.0.1:18802"
nox_mem_bin: "nox-mem"
search_top_k: 10
search_timeout: 30
ingest_batch_size: 50
ingest_delay_ms: 0
```

## 5. Apply Gemini-only LLM stack (see `GEMINI-ONLY-STACK.md`)

```bash
# Edit eval/config/pipeline.yaml — change answer.model + evaluate.model
# to "gemini-2.5-flash" and provider order to ["google-ai-studio"].
# (See GEMINI-ONLY-STACK.md §2 for exact YAML diff.)

# Set env vars
cp env.template .env
export GEMINI_API_KEY=$(cat /tmp/.gemini-key-98949.txt | tr -d '\n')
export LLM_API_KEY="$GEMINI_API_KEY"
export LLM_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"

# Smoke test (see GEMINI-ONLY-STACK.md §5)
python -c "import os, asyncio; from openai import AsyncOpenAI; \
asyncio.run((async def: ...).__call__())"  # paste full smoke test from §5
```

## 6. Set up isolated nox-mem instance

```bash
export NOX_DB_PATH=/tmp/evermembench-004-$TS.db
export NOX_MEM_BIN=$(which nox-mem)

# Source production env WITHOUT NOX_DB_PATH override (we set it above)
set -a; source /root/.openclaw/.env; set +a
# But preserve our NOX_DB_PATH — re-export AFTER source
export NOX_DB_PATH=/tmp/evermembench-004-$TS.db

# Start nox-mem API in background bound to isolated DB
# (use a non-default port if 18802 is occupied by prod instance)
export NOX_API_PORT=18810
nohup nox-mem serve > /tmp/evermembench-api-$TS.log 2>&1 &
NOX_API_PID=$!
sleep 5

# Verify the API is alive AND pointing at the isolated DB
curl -s http://127.0.0.1:18810/api/health | jq '.dbPath, .vectorCoverage'
# dbPath should equal $NOX_DB_PATH, NOT /root/.openclaw/...

# Also export API base for the adapter
export NOX_API_BASE=http://127.0.0.1:18810
```

**⚠️ ISOLATION GUARD:** the adapter refuses to ingest if NOX_DB_PATH
contains `/root/.openclaw/workspace/tools/nox-mem/nox-mem.db`. This is
defense-in-depth — verify the path yourself before running Add.

## 7. Download dataset

```bash
# Option A: huggingface CLI
pip install -U huggingface_hub
huggingface-cli download EverMind-AI/EverMemBench-Dynamic --repo-type dataset --local-dir dataset/

# Option B: it ships in EverOS clone already at benchmarks/EverMemBench/dataset/
ls dataset/004/
# Expected: dialogue.json qa_004.json
```

## 8. Run Add stage

```bash
python -m eval.cli \
    --dataset dataset/004/dialogue.json \
    --system nox_mem \
    --user-id 004 \
    --stages add 2>&1 | tee /tmp/evermembench-add-004-$TS.log

# Verify ingest worked
curl -s http://127.0.0.1:18810/api/health | jq '.totalChunks, .vectorCoverage'
# Expect totalChunks ≥ 1000 (group chat has ~1k+ messages per batch)
```

## 9. Run Search + Answer + Evaluate

```bash
python -m eval.cli \
    --dataset dataset/004/dialogue.json \
    --qa dataset/004/qa_004.json \
    --system nox_mem \
    --user-id 004 \
    --stages search answer evaluate \
    --top-k 10 2>&1 | tee /tmp/evermembench-eval-004-$TS.log

# Monitor cost as it runs — Gemini usage shows in
# https://aistudio.google.com/usage. Cost cap = $1.50 USD.
# If approaching cap, Ctrl-C and report partial results.
```

## 10. Analyze + commit results

```bash
python tools/analyze_results.py eval/results/nox_mem/evaluation_results_004.json \
    > /tmp/evermembench-analysis-004-$TS.txt

# Copy results JSON back to memoria-nox repo
cp eval/results/nox_mem/evaluation_results_004.json \
   "$MEMNOX/eval/evermembench/results-batch-004.json"

# Write RESULTS-BATCH-004.md with:
#   - headline accuracy %
#   - per-category breakdown (MC vs OE, single-hop vs multi-hop)
#   - latency p50/p95
#   - comparison to EverOS published numbers (if known)
#   - HONEST FRAMING block from GEMINI-ONLY-STACK.md §3
#   - cost summary

cd "$MEMNOX"
git add eval/evermembench/results-batch-004.json eval/evermembench/RESULTS-BATCH-004.md
git commit -m "feat(eval): EverMemBench batch 004 results — nox-mem Gemini-only stack"
gh pr create --title "feat(eval): EverMemBench batch 004 results — nox-mem Gemini-only stack" \
             --body-file /tmp/evermembench-pr-body.md
```

## 11. Cleanup

```bash
# Kill background API
kill $NOX_API_PID 2>/dev/null

# Remove isolated DB (or keep for re-runs / per-batch baseline)
rm -f /tmp/evermembench-004-$TS.db*  # .db + .db-wal + .db-shm

# Remove Gemini key file if rotated
# (or leave for next batch 005, 010, 011, 016 runs)
```

---

## Cost cap enforcement

The harness does NOT have a built-in spend tracker. Manual discipline:

1. **Before Add:** $0 (no LLM calls)
2. **After Search:** $0 (no LLM calls — pure retrieval)
3. **Mid-Answer:** check https://aistudio.google.com/usage every ~5 min
4. **If usage approaches $1.50:** Ctrl-C the harness, save partial results,
   note "aborted at N/total questions" in RESULTS-BATCH-004.md

Per `GEMINI-ONLY-STACK.md §4`, full batch 004 should land ~$0.45.
$1.50 is 3× cap — plenty of safety margin.

---

## Comparison to EverOS-published numbers

EverOS publishes batch-by-batch accuracy in their EverMemBench paper
appendix + leaderboard. **Reference table (TODO: fill from paper §C):**

| System | Batch 004 | Batch 005 | Batch 010 | Batch 011 | Batch 016 |
|--------|-----------|-----------|-----------|-----------|-----------|
| EverCore | TODO | TODO | TODO | TODO | TODO |
| Mem0 | TODO | TODO | TODO | TODO | TODO |
| Memos | TODO | TODO | TODO | TODO | TODO |
| Zep | TODO | TODO | TODO | TODO | TODO |
| Memobase | TODO | TODO | TODO | TODO | TODO |
| **nox-mem (this run)** | **PENDING** | — | — | — | — |

Methodology delta: nox-mem (this row) uses `gemini-2.5-flash` for both
answer + judge; published rows use `gpt-4.1-mini` answer + `gemini-3-flash-preview`
judge. Numbers are directionally informative, not direct parity. See
`GEMINI-ONLY-STACK.md §3` for the honest-framing required disclosure.

---

## Next steps after batch 004 lands

1. **If batch 004 lands above 60% accuracy:** run batches 005, 010, 011,
   016 (same recipe) for full 5-batch comparison. Est. total cost ~$2.25.
2. **If batch 004 lands below 30% accuracy:** debug Add-stage chunking
   first (likely the message-per-paragraph segmentation is dropping
   speaker/group context). Don't burn more $ on remaining batches until
   single-batch is plausible.
3. **OpenRouter parity Phase 2:** once nox-mem has a stable Gemini-only
   number, re-run batch 004 with `LLM_API_KEY=sk-or-v1-...` + default
   `pipeline.yaml` to get apples-to-apples vs published EverOS numbers.
   Estimated incremental cost ~$0.40 + 1 OpenRouter key purchase.
