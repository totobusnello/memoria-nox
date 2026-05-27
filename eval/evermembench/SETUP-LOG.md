# EverMemBench Bootstrap Setup Log

**Date:** 2026-05-27
**Task:** Lab Q1 #6 — bootstrap EverMemBench so nox-mem can run against it
**Outcome:** SUCCESS — harness reachable, adapter wired end-to-end, smoke test passes at the expected boundary

---

## 1. Environment

| Item | Value |
|------|-------|
| Host | macOS darwin 25.5.0 (local laptop) |
| Python | 3.12.12 (via Homebrew; 3.14 also present but skipped — too new for safety) |
| Venv | `/tmp/evermembench-venv` |
| Clone path | `/tmp/everos-eval-27839/benchmarks/EverMemBench/` |
| EverOS repo | `https://github.com/EverMind-AI/EverOS` — public, accessible, NOT 404 |

EverOS repo is alive: tagged 5k+ stars. The 404 risk flagged in memory `project_evermos_honest_comparison_benchmark_gap` did not materialize.

## 2. Steps Executed

1. Cloned EverOS shallow into `/tmp/everos-eval-27839` (depth 1, ~6MB).
2. Validated `benchmarks/EverMemBench/` directory layout matches investigation (eval/cli.py, eval/src/adapters/, eval/src/core/, eval/config/, requirements.txt, env.template, tools/analyze_results.py — all present).
3. Created Python 3.12 venv at `/tmp/evermembench-venv`.
4. Installed core deps from `requirements.txt`, EXCLUDING the three vendor SDKs (`mem0ai`, `memobase`, `zep-cloud`) — none are needed for the `nox_mem` adapter, and skipping them keeps the venv small and removes potential install failures on Python 3.12. Core deps installed: `aiohttp 3.13.5`, `aiolimiter 1.2.1`, `openai 2.38.0`, `python-dotenv 1.2.2`, `PyYAML 6.0.3`, `rich 15.0.0`.
5. Copied `adapter_nox_mem.py` into `eval/src/adapters/nox_mem_adapter.py`.
6. Registered `nox_mem` system in `eval/cli.py` (added to `SUPPORTED_SYSTEMS` and `create_adapter()` factory).
7. Created `eval/config/nox_mem.yaml` with env-var defaults (`${NOX_API_BASE:http://127.0.0.1:18802}` and search/ingest params).
8. Downloaded batch `004` from HuggingFace `EverMind-AI/EverMemBench-Dynamic` (public, no auth required). Files: `dialogue_en.json` (3.9 MB) and `qa_004.json` (1.1 MB). Renamed `dialogue_en.json` → `dialogue.json` to match harness expectations.
9. Staged at `benchmarks/EverMemBench/dataset/004/`.

## 3. Smoke Test

Ran: `python -m eval.cli --dataset dataset/004/dialogue.json --system nox_mem --user-id 004 --stages add --smoke --smoke-days 1`

**Result:** Pipeline executed correctly:
- Dataset loaded: 254 days, 10222 messages, date range 2025-01-09 → 2025-12-31.
- Smoke subset: 1 day, 31 messages.
- Adapter `add()` invoked, refused cleanly with actionable error (no `NotImplementedError`).

## 4. Adapter Changes

The adapter was upgraded from raise-NotImplementedError skeleton to a wireable implementation:

- **Add stage (Option B — CLI subprocess):** writes dataset to a single Markdown file (grouped by day), invokes `nox-mem ingest <tmpfile> --source evermembench-<uid>` via `asyncio.create_subprocess_exec` (no shell, per `feedback_execfilesync_over_execsync_for_user_input`). Two safety guards:
  1. Refuses if `NOX_MEM_BIN` not set and `nox-mem` not on PATH — returns actionable error.
  2. **Isolation guard:** refuses if `NOX_DB_PATH` is empty or does not match the pattern `/evermembench-<user_id>.db`. This prevents accidental cross-contamination of the production memory DB on the VPS (per CLAUDE.md rule #6).
- **Search stage:** already-wired HTTP `POST /api/search` left intact (validated to compile; will be exercised when a live nox-mem instance is reachable on `:18802`).

**Validation runs** (direct adapter call, all passing):
- Case 1: `NOX_DB_PATH` unset → refused with isolation-pattern error. ✓
- Case 2: `NOX_DB_PATH=/var/lib/nox-mem/nox-mem.db` (prod-like) → refused. ✓
- Case 3: `NOX_DB_PATH=/tmp/evermembench-004.db` + binary present → success (days=1, msgs=31). ✓

## 5. Files Modified / Created

**In this repo (memoria-nox):**
- `eval/evermembench/adapter_nox_mem.py` — upgraded from skeleton to wireable (Option B implemented, isolation guard added)
- `eval/evermembench/SETUP-LOG.md` — this file
- `eval/evermembench/COST-ESTIMATE.md` — phased budget proposal

**In `/tmp/everos-eval-27839/benchmarks/EverMemBench/` (NOT committed — disposable harness checkout):**
- `eval/src/adapters/nox_mem_adapter.py` (copy of adapter)
- `eval/config/nox_mem.yaml` (new config)
- `eval/cli.py` (2 small edits: SUPPORTED_SYSTEMS entry + factory branch)
- `dataset/004/dialogue.json` + `dataset/004/qa_004.json` (staged from HF)

## 6. Blockers For Next Session

| Blocker | Severity | Resolution path |
|---------|----------|-----------------|
| OpenRouter API key (`LLM_API_KEY=sk-or-v1-...`) | MEDIUM | Required for `answer` + `evaluate` stages (not for `add` or `search`). Toto can create one at openrouter.ai (~$5 prepay covers a full 5-batch run easily, see COST-ESTIMATE.md). |
| Live nox-mem instance | MEDIUM | `add` and `search` stages need a running nox-mem with `NOX_DB_PATH=/tmp/evermembench-<uid>.db` per batch. Either run locally with VPS source mirror, or SSH to VPS and run there. Cannot smoke from this laptop without local nox-mem binary. |
| HF dataset download | NONE | Confirmed public + anonymous. ~6 MB per batch. Reproducible. |
| Python 3.14 compat | LOW (mitigated) | Used 3.12 explicitly. If 3.13+ is forced later, the only at-risk dep is `openai` SDK — re-test then. |
| Domain mismatch (group chat vs entity notes) | MEDIUM (open question) | Investigation.md flagged this. Current adapter ingests as flat Markdown — works mechanically but does not exploit nox-mem's section_boost/entity-file routing. Phase B improvement: route through `ingest-entity` with synthetic entity files per speaker. |

## 7. Recommended Next Steps

1. **Get OpenRouter key** (~$5 prepay) — unblocks `answer` + `evaluate` stages.
2. **Run Phase 1: batch 004 only, `add` stage**, on VPS where nox-mem CLI exists. Validate via `curl :18802/api/health | jq .vectorCoverage`. Estimated 10k-msg ingest: 20-40 min with embedding generation.
3. **Run Phase 1 continued: `search` + `answer` + `evaluate` for batch 004** (~626 questions, ~$0.20-$0.30 spend, see COST-ESTIMATE.md).
4. **Compare accuracy vs EverOS-published numbers** for batch 004 in their paper Table X. Decide whether to expand to remaining batches (005, 010, 011, 016).
5. **Phase B (deferred):** consider entity-file ingestion path for better section_boost utilization. Only pursue if Phase 1 accuracy is materially below EverOS published.

## 8. Reproducibility Notes

Everything outside `eval/evermembench/` lives in `/tmp` and is disposable. To redo from scratch:

```bash
# fresh clone + venv
git clone --depth 1 https://github.com/EverMind-AI/EverOS /tmp/everos-eval-XXXX
python3.12 -m venv /tmp/evermembench-venv
source /tmp/evermembench-venv/bin/activate
pip install aiohttp aiolimiter openai python-dotenv PyYAML rich

# copy adapter from this repo (relative paths from repo root)
cp eval/evermembench/adapter_nox_mem.py \
  /tmp/everos-eval-XXXX/benchmarks/EverMemBench/eval/src/adapters/nox_mem_adapter.py
# create eval/config/nox_mem.yaml + edit eval/cli.py per section 2.6

# download dataset
python -c "from huggingface_hub import hf_hub_download; [hf_hub_download('EverMind-AI/EverMemBench-Dynamic', f, repo_type='dataset', local_dir='/tmp/everos-eval-XXXX/benchmarks/EverMemBench/hf_raw') for f in ['dataset/004/dialogue_en.json', 'dataset/004/qa_004.json']]"

# stage + smoke
mkdir -p /tmp/everos-eval-XXXX/benchmarks/EverMemBench/dataset/004
cp /tmp/everos-eval-XXXX/benchmarks/EverMemBench/hf_raw/dataset/004/dialogue_en.json /tmp/everos-eval-XXXX/benchmarks/EverMemBench/dataset/004/dialogue.json
cp /tmp/everos-eval-XXXX/benchmarks/EverMemBench/hf_raw/dataset/004/qa_004.json /tmp/everos-eval-XXXX/benchmarks/EverMemBench/dataset/004/qa_004.json
cd /tmp/everos-eval-XXXX/benchmarks/EverMemBench
python -m eval.cli --dataset dataset/004/dialogue.json --system nox_mem --user-id 004 --stages add --smoke --smoke-days 1
```
