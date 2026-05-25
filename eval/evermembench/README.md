# EverMemBench — nox-mem Integration

Adapter skeleton for running nox-mem against EverMemBench.  
Full investigation: `INVESTIGATION.md`.

## Quick start (after adapter is complete)

```bash
# 1. Clone EverOS into a temp dir
git clone --depth 1 https://github.com/EverMind-AI/EverOS /tmp/everos-eval
cd /tmp/everos-eval/benchmarks/EverMemBench

# 2. Install harness deps
pip install -r requirements.txt

# 3. Copy nox-mem adapter
cp /path/to/memoria-nox/eval/evermembench/adapter_nox_mem.py \
   eval/src/adapters/nox_mem_adapter.py
# TODO: register in eval/src/adapters/__init__.py + eval/cli.py

# 4. Configure
cp env.template .env
# Set LLM_API_KEY=sk-or-v1-... (OpenRouter key)

# 5. Start nox-mem API in isolated mode per batch
NOX_DB_PATH=/tmp/evermembench-004.db nox-mem serve &

# 6. Run Add stage (ingest group chat)
NOX_DB_PATH=/tmp/evermembench-004.db python -m eval.cli \
    --dataset dataset/004/dialogue.json \
    --system nox_mem \
    --user-id 004 \
    --stages add

# 7. Run Search → Answer → Evaluate
python -m eval.cli \
    --dataset dataset/004/dialogue.json \
    --qa dataset/004/qa_004.json \
    --system nox_mem \
    --user-id 004 \
    --stages search answer evaluate \
    --top-k 10

# 8. Analyze
python tools/analyze_results.py eval/results/nox_mem/evaluation_results_004.json
```

## TODOs before this runs

- [ ] Implement `NoxMemAdapter.add()` — HTTP ingest or CLI ingest option
- [ ] Confirm `/api/search` response schema matches parsing in `search()`
- [ ] Register adapter in `eval/src/adapters/__init__.py`
- [ ] Add `nox_mem.yaml` config file (connection + search params)
- [ ] Add `nox_mem` case to `eval/cli.py` system routing
- [ ] Smoke test: `python -m eval.cli --dataset dataset/004/dialogue.json --system nox_mem --smoke`
- [ ] Run all 5 batches (004, 005, 010, 011, 016) and aggregate with `analyze_results.py`

## Batches

User IDs: `004`, `005`, `010`, `011`, `016`  
Each batch needs a clean isolated `NOX_DB_PATH`.

## Expected output

```
eval/results/nox_mem/
  search_results_004.json
  answer_results_004.json
  evaluation_results_004.json   ← accuracy here
```

Primary metric: **accuracy** (% correct, MC direct + OE LLM judge via OpenRouter Gemini-3-flash).
