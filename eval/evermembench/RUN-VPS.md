# EverMemBench batch 004 — VPS run checklist

> **Status:** batch 004 executed 2026-05-28. Headline **56.07% (351/626)**.
> See `RESULTS-BATCH-004.md` for the full breakdown and the
> **"Setup gotchas (batch 004 retrospective)"** section at the bottom of this
> doc for issues discovered during the run that must be addressed in batches
> 005/010/011/016.
>
> **Audience:** the next session that picks up batch 005+ execution on the
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

---

## Setup gotchas (batch 004 retrospective, 2026-05-28)

Issues encountered during the first VPS execution that future runs MUST address:

### 1. `nox-mem serve` does not exist
The doc above references `nohup nox-mem serve` (step 6) — there is no such
subcommand. Start the API directly:

```bash
cd /root/.openclaw/workspace/tools/nox-mem
nohup node --no-warnings dist/api-server.js > /tmp/evermembench-api.log 2>&1 &
```

The prod systemd `nox-mem-api.service` uses the same entry point on :18802.

### 2. `NOX_DB_PATH` prefix restriction (op-audit guard, PR #358)
`/tmp/*` paths are REJECTED by `op-audit` workspace-consistency guard. Use:

```bash
mkdir -p /root/.openclaw/evermembench-runs
export NOX_DB_PATH=/root/.openclaw/evermembench-runs/evermembench-005-$(date +%s).db
```

The adapter's prod-DB check (`/root/.openclaw/workspace/tools/nox-mem/nox-mem.db`)
still applies — only that exact path is blocked, not all `/root/.openclaw/`
paths.

### 3. Schema migration drift on fresh DBs
`nox-mem stats` against an empty DB initialises only v1 schema. The current
hybrid retrieval code path requires v18 columns and KG tables. Apply
manually after `nox-mem stats` runs:

```bash
sqlite3 "$NOX_DB_PATH" <<'SQL'
ALTER TABLE chunks ADD COLUMN retention_days INTEGER;
ALTER TABLE chunks ADD COLUMN pain REAL DEFAULT 0.2;
ALTER TABLE chunks ADD COLUMN section TEXT;
ALTER TABLE chunks ADD COLUMN section_boost REAL DEFAULT 1.0;
PRAGMA user_version = 18;
CREATE TABLE IF NOT EXISTS kg_entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL, entity_type TEXT NOT NULL,
    first_seen TEXT DEFAULT (datetime('now')),
    last_seen TEXT DEFAULT (datetime('now')),
    mention_count INTEGER DEFAULT 1, attributes TEXT,
    UNIQUE(name, entity_type));
CREATE INDEX IF NOT EXISTS idx_kg_entities_name ON kg_entities(name);
CREATE INDEX IF NOT EXISTS idx_kg_entities_type ON kg_entities(entity_type);
CREATE TABLE IF NOT EXISTS kg_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_entity_id INTEGER NOT NULL, relation_type TEXT NOT NULL,
    target_entity_id INTEGER NOT NULL, evidence_chunk_id INTEGER,
    confidence REAL DEFAULT 0.8, created_at TEXT DEFAULT (datetime('now')),
    expires_at TEXT, last_confirmed TEXT,
    relation_reason TEXT DEFAULT 'unknown',
    superseded_by_relation_id INTEGER, superseded_at INTEGER,
    superseded_reason TEXT, extraction_method TEXT,
    FOREIGN KEY (source_entity_id) REFERENCES kg_entities(id),
    FOREIGN KEY (target_entity_id) REFERENCES kg_entities(id));
SQL
```

Without these, `nox-mem ingest` throws `no column 'retention_days'` and
`/api/search` throws `no such table: kg_entities`.

### 4. Dataset layout — `dialogue.json` does not exist
The HuggingFace dataset puts batch files at `dataset/dataset/{004,005,010,011,016}/`
with `dialogue_en.json` (not `dialogue.json`) and `qa_<N>.json`. Symlink:

```bash
mkdir -p dataset/<NNN>
ln -sf dataset/dataset/<NNN>/dialogue_en.json dataset/<NNN>/dialogue.json
ln -sf dataset/dataset/<NNN>/qa_<NNN>.json    dataset/<NNN>/qa_<NNN>.json
```

Also: HuggingFace CLI `huggingface-cli download` is deprecated → use `hf download`.

### 5. `pipeline.yaml` `provider` block kills Gemini direct
The harness injects `extra_body.provider` into the OpenAI client request when
`answer.provider` is present in pipeline.yaml. Gemini's OpenAI-compat endpoint
returns **HTTP 400** for any unknown field, including `provider`. **Delete**
the `provider:` blocks under both `answer:` and `evaluate:` after applying
the Gemini-only stack swap. This was the single biggest time sink in batch
004 (50 minutes spent retrying one question through the 20-retry exponential
backoff before the run was killed).

```yaml
# WRONG (default — fails on Gemini direct):
answer:
  model: "gemini-2.5-flash"
  provider:
    order: ["google-ai-studio"]
    allow_fallbacks: false
  # ...

# RIGHT (Gemini-only):
answer:
  model: "gemini-2.5-flash"
  temperature: 0
  max_tokens: 1000
  timeout: 300
  concurrency: 4
```

### 6. Concurrency=1 wastes wall-clock time
Default `answer.concurrency: 1` puts a 5+ second Gemini call in serial
through 626 questions = ~50 min/batch with no benefit. Bump to 4 (the
adapter is async and Gemini AI Studio paid tier handles it without
rate-limiting). `evaluate.concurrency` can stay at 8.

### 7. `--source` flag removed from nox-mem ingest
The adapter (`adapter_nox_mem.py`) passed `--source evermembench-{user_id}`
in argv. Current nox-mem CLI (v3.8) does not accept this flag — exit code 1
on every call. The flag has been removed from the adapter in the same PR
that landed these results.

### 8. Search API response shape
The prod `/api/search` endpoint returns a top-level JSON **array** of result
dicts, not `{"results": [...]}`. The adapter previously called
`data.get("results", [])` which raised on the list. Patched to handle both
shapes for forward compatibility.

### 9. `chunk_text` vs `content` field name
Result dicts use `chunk_text`, not `content`. Adapter patched to try both.

### 10. Schema gotchas were silent
The fresh-DB schema bugs and `--source` failure both surfaced as
`AddResult.success = False; errors = [...]` with a generic count
("Errors: 205") and no per-error printout in the pipeline summary. Always
run a 2-day subset adapter probe directly (`asyncio.run(adapter.add(...))`)
before kicking off the full 254-day Add stage on a fresh DB.
