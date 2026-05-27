# EverMemBench — nox-mem Integration

Adapter for running nox-mem against EverMemBench (Option B — CLI subprocess).

| File | Purpose |
|------|---------|
| `INVESTIGATION.md` | Original 2026-05-24 investigation (dataset format, metrics, Lab Q1 recommendation) |
| `adapter_nox_mem.py` | Implemented adapter — Option B CLI subprocess + defensive prod-DB guard |
| `GEMINI-ONLY-STACK.md` | Recipe for swapping the harness's OpenRouter LLM stack with Gemini direct (saves $ + removes OR key dep) |
| `RUN-VPS.md` | Step-by-step VPS execution checklist for batch 004 + remaining batches |
| `BLOCKED-LOCAL.md` | Why batch 004 can't run from the macOS dev host (nox-mem source lives only on VPS) |
| `results-batch-004.json` | (Pending VPS run) raw evaluation_results JSON |
| `RESULTS-BATCH-004.md` | (Pending VPS run) headline + per-category analysis with honest-framing disclosure |

## Status (2026-05-27)

- [x] Investigation complete (2026-05-24)
- [x] Adapter Option B implemented (`adapter_nox_mem.py`)
- [x] Gemini-only LLM stack recipe documented (`GEMINI-ONLY-STACK.md`)
- [x] VPS run checklist drafted (`RUN-VPS.md`)
- [ ] **Batch 004 first run — DEFERRED to VPS execution** (see `BLOCKED-LOCAL.md`)
- [ ] Batches 005, 010, 011, 016 follow-up (after batch 004 lands)
- [ ] OpenRouter-parity Phase 2 re-run (after Gemini-only baseline lands)

## Quick start (VPS shell)

```bash
# See RUN-VPS.md for the full 11-step checklist
ssh openclaw

# Skim the highlights:
TMPDIR=/tmp/evermembench-run-$(date +%s)
git clone --depth 1 https://github.com/EverMind-AI/EverOS "$TMPDIR/everos"
cd "$TMPDIR/everos/benchmarks/EverMemBench"

python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Adapter + config
cp /root/repos/memoria-nox/eval/evermembench/adapter_nox_mem.py \
   eval/src/adapters/nox_mem_adapter.py
# (Register in eval/src/adapters/__init__.py + eval/cli.py — see RUN-VPS.md §4)

# Gemini-only LLM swap (see GEMINI-ONLY-STACK.md §2 for exact YAML)
cp env.template .env
export GEMINI_API_KEY=$(cat /tmp/.gemini-key-XXXXX.txt | tr -d '\n')
export LLM_API_KEY="$GEMINI_API_KEY"
export LLM_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"

# Isolated nox-mem
export NOX_DB_PATH=/tmp/evermembench-004.db
export NOX_API_PORT=18810
export NOX_API_BASE=http://127.0.0.1:18810
set -a; source /root/.openclaw/.env; set +a
export NOX_DB_PATH=/tmp/evermembench-004.db  # re-export after sourcing prod env
nohup nox-mem serve > /tmp/evermembench-api.log 2>&1 &

# Add → Search → Answer → Evaluate
python -m eval.cli --dataset dataset/004/dialogue.json --system nox_mem --user-id 004 --stages add
python -m eval.cli --dataset dataset/004/dialogue.json --qa dataset/004/qa_004.json \
    --system nox_mem --user-id 004 --stages search answer evaluate --top-k 10

# Analyze
python tools/analyze_results.py eval/results/nox_mem/evaluation_results_004.json
```

## Batches

User IDs: `004`, `005`, `010`, `011`, `016`
Each batch needs a clean isolated `NOX_DB_PATH` (e.g. `/tmp/evermembench-{user_id}-{ts}.db`).

## Expected output

```
eval/results/nox_mem/
  search_results_004.json
  answer_results_004.json
  evaluation_results_004.json   ← accuracy here
```

Primary metric: **accuracy** (% correct, MC direct + OE LLM judge via Gemini).

**Honest-framing note:** any results published from the Gemini-only stack
MUST disclose the methodology deviation (see `GEMINI-ONLY-STACK.md §3`).
Numbers are NOT directly comparable to EverOS-published leaderboard
entries that use OpenRouter `gpt-4.1-mini` + `gemini-3-flash-preview`.

## Cost

| Run | Estimated cost (Gemini-only) |
|-----|------------------------------|
| Batch 004 only | ~$0.45 USD |
| All 5 batches (004, 005, 010, 011, 016) | ~$2.25 USD |
| OpenRouter parity Phase 2 (batch 004 only) | ~$0.40 USD |

Cap: $1.50/run, $5 total. Monitor at https://aistudio.google.com/usage.
