# rc4 — All-Gemini Fair Comparison Plan

**Purpose:** Control the embedding confound in §6 (Q4 comparison). The baseline run
split nox-mem (Gemini 3072d prod / 768d eval-hybrid) vs mem0 (OpenAI text-embedding-3-small
1536d). rc4 forces all participating systems to the **same embedder** (Gemini
`gemini-embedding-001`, 768d) so any residual nDCG gap reflects memory architecture,
not embedding quality.

**Authored:** 2026-06-28  
**Status:** Plan only — no adapters edited, no pod run triggered.

---

## 1. System-by-System Analysis

### 1.1 nox-mem (baseline — already Gemini)

**Supports Gemini embedder:** YES — nox-mem hybrid mode already uses Gemini.

**Config point:** `adapters/nox_mem.py:84`
```python
_GEMINI_EMBED_MODEL = "models/gemini-embedding-001"  # gemini-embedding-001 (768d output)
```

**Embedding call:** `nox_mem.py:356-363`
```python
def _embed_text(genai, text: str) -> list[float]:
    result = genai.embed_content(
        model=_GEMINI_EMBED_MODEL,
        content=text,
        task_type="RETRIEVAL_DOCUMENT",
    )
    return result["embedding"]
```

**Dim at runtime:** The dim is probed live before schema creation (`nox_mem.py:1215-1218`):
```python
sample_vec = _embed_text(genai, "hello world")
dim = len(sample_vec)
```
No `output_dimensionality` is passed to the SDK → the SDK returns the model's default.

**Actual dim emitted:** **768** (gemini-embedding-001 default without `output_dimensionality`).

**Important discrepancy:** Prod nox-mem uses **3072d** — explicitly requested via
`outputDimensionality: 3072` in `staged/A3/edits/src/providers/embedding/gemini.ts:27`:
```typescript
export const GEMINI_EMBED_DEFAULT_DIM = 3072;
// ...
outputDimensionality: this.dimensions,  // line 103
```
The eval adapter's hybrid mode is therefore **NOT prod-equivalent** — it uses 768d, not 3072d.
For rc4 purposes, 768d is the target dim (both systems default to 768d with Gemini, avoids cost of
re-embedding at 3072d, and the goal is provider-fairness not prod-replication).

**Activation:** Set `NOX_EVAL_MODE=hybrid` + `GEMINI_API_KEY=<key>`. No adapter edits needed.

**Re-ingest required:** Only if `cache/nox-mem-hybrid.db` does not exist or was created with a
different embedder/dim. If the file exists and `eval_meta` table has `embed_dim=768`, it is reusable.

---

### 1.2 mem0 (currently OpenAI — CAN switch to Gemini)

**Supports Gemini embedder:** YES — mem0 has a first-class `GoogleGenAIEmbedding` class.

**Source evidence (mem0ai package, confirmed 2026-06-28):**
```python
# mem0/embeddings/gemini.py
class GoogleGenAIEmbedding(EmbeddingBase):
    def __init__(self, config):
        self.config.model = self.config.model or "models/gemini-embedding-001"
        self.config.embedding_dims = self.config.embedding_dims or \
                                     self.config.output_dimensionality or 768
        api_key = self.config.api_key or os.getenv("GOOGLE_API_KEY")
        self.client = genai.Client(api_key=api_key)
```

**Config dict (to inject into `_build_config`):**
```python
{
    "embedder": {
        "provider": "gemini",
        "config": {
            "model": "models/gemini-embedding-001",
            "embedding_dims": 768,
            "api_key": "<GOOGLE_API_KEY>",   # or env GOOGLE_API_KEY
        }
    },
    "vector_store": {
        "provider": "chroma",
        "config": {
            "collection_name": "q4-eval-gemini",  # NEW — avoids dim clash with OpenAI 1536d run
            "path": "<MEM0_CHROMA_PATH>",
        }
    },
    # LLM section omitted → mem0 defaults to OpenAI for fact extraction.
    # Set MEM0_SKIP_LLM_EXTRACTION=1 (default in adapter) to bypass LLM entirely.
}
```

**Env vars required:**
- `GOOGLE_API_KEY` — mem0's Gemini embedder reads this (NOT `GEMINI_API_KEY`).
  On pod: `export GOOGLE_API_KEY="$GEMINI_API_KEY"` before starting the run.
- `MEM0_CHROMA_PATH` — must point to a NEW directory (e.g., `.mem0-chroma-gemini/`)
  to avoid Chroma failing on dim mismatch with the existing 1536d OpenAI collection.
- `MEM0_TELEMETRY=False` — see §4 (thread-leak mitigation).
- `ANONYMIZED_TELEMETRY=False` — idem.
- `MEM0_SKIP_LLM_EXTRACTION=1` — already default in adapter; keep for cost control.
- `OPENAI_API_KEY` — still required IF `MEM0_SKIP_LLM_EXTRACTION=0`; with skip=1 it may
  not be called but mem0's validate() still checks for it. Set a dummy value if skipping.

**Current adapter problem:** `adapters/mem0.py:_build_config()` (line 142-165) does NOT
include an `embedder` section — it hardcodes only `vector_store`. This means mem0 silently
falls back to OpenAI embedder. **The existing adapter cannot be edited** (per rc4 rules).

**Solution (no adapter edit required):** Monkeypatch `_build_config` before import resolution.
`lib/all_gemini_config.py` exports `patch_mem0_adapter()` which injects a new `_build_config`
function via attribute replacement. This must be called **before `adapters.mem0` is imported**
(the runner lazy-imports adapters, so a pre-run shim works). See §3 for the rc4 runner sequence.

**Dim:** 768d (matching nox-mem hybrid, matching mem0 Gemini default).

**Re-ingest required:** YES, always — different Chroma collection than OpenAI run.
Full corpus: ~9,882 chunks. At Gemini free tier ~1500 RPM embed calls → ~7 min ingest.
With `MEM0_INGEST_LIMIT` for smoke tests: keep ≤ 500 for pod preflight.

---

### 1.3 agentmemory — CANNOT participate in rc4

**Supports Gemini embedder:** **UNKNOWN / likely NO at adapter level.**

**Evidence:** `adapters/agentmemory.py` is a pure REST adapter — it POSTs raw text to the
iii-engine daemon (`/agentmemory/remember`) and the daemon handles embedding internally
(node_modules iii-engine). There is no API parameter for embedding provider override.

**Config path:** Even if the daemon supports a config file with an embedding provider field,
this would require modifying the daemon startup environment and restarting it — outside the
scope of what the eval adapter controls. Probing the iii-engine config schema would require
reverse-engineering the npm package internals.

**Conclusion:** agentmemory is **excluded from rc4**. This is a documented §6 limitation,
not a failure of the benchmark design. The rc4 result set is: nox-mem (hybrid/Gemini) vs
mem0 (Gemini). agentmemory baseline results from the original §6 run remain valid but are
not part of the rc4 fair-embedding comparison.

---

### 1.4 Other systems (zep, letta, evermind)

These were either gaps (docker-impossible for zep, letta stalls at 94%) or keys/server
required (evermind). Their embedder configurability was not investigated for rc4 since they
were already out of scope for §6. Treat as excluded from rc4.

---

## 2. Embedding Dimensions

| System | rc4 Embedder | rc4 Dim | Prod Dim | Notes |
|---|---|---|---|---|
| nox-mem (hybrid) | gemini-embedding-001 | **768** | 3072 | default SDK output; no `output_dimensionality` set |
| mem0 (Gemini) | gemini-embedding-001 | **768** | — | mem0 Gemini default `embedding_dims=768` |
| agentmemory | iii-engine internal | unknown | — | excluded from rc4 |

**Why 768d not 3072d for rc4:**
- Both systems default to 768d without extra config — no adapter edit required for nox-mem.
- 3072d would require editing `nox_mem.py` (passing `output_dimensionality=3072` to the SDK)
  which violates the rc4 "no adapter edits" rule.
- 3072d costs 4× more embeddings and stores 4× larger vectors.
- The goal is provider-fairness (Gemini vs Gemini) not prod-parity.
- Caveat documented: rc4 nox-mem runs at 768d, prod nox-mem at 3072d → rc4 is a
  fair inter-system comparison but is not a faithful reproduction of prod performance.

**Backend dim constraints:**
- nox-mem hybrid: `eval_vecs USING vec0(embedding float[{dim}])` — dim is set at schema
  creation from the probe call. If DB already exists with dim=768, it is reusable.
- mem0 Chroma: Chroma auto-detects dim from first ingest. New collection required for rc4
  because OpenAI run used 1536d — mixing would raise Chroma `InvalidDimensionException`.

---

## 3. Thread-Leak Mitigation for mem0

Memory: `[[feedback_mem0_thread_leak_telemetry_faiss_architecture]]`

mem0 spawns background threads via PostHog telemetry on every `Memory.add()` and
`Memory.search()` call. At scale (9,882 chunks) this exhausts PID limits.

**Mandatory env vars before any mem0 process:**
```bash
export MEM0_TELEMETRY=False
export ANONYMIZED_TELEMETRY=False
```

**Mandatory process isolation:**
- Run ingest in a **separate subprocess** from search.
- Never share a `Memory` singleton across ingest + eval loop.
- Pattern:
  ```
  python -c "import adapters.mem0; adapters.mem0.setup()"   # ingest process
  python runner.py --systems mem0 ...                        # eval process (no ingest)
  ```
  Or use `subprocess.run()` from an rc4 orchestrator script.

**Why FAISS vs Chroma matters here:** The FAISS backend leaks fewer threads than Chroma
under load. However, for rc4 the existing Chroma-based adapter is used (unchanged).
The telemetry env vars above are the primary mitigation.

---

## 4. Re-ingest Scope and Cost

| System | Re-ingest needed? | Corpus size | Embed calls | Est. time | Est. cost |
|---|---|---|---|---|---|
| nox-mem hybrid | Only if cache/nox-mem-hybrid.db absent | ~9,882 | ~9,882 | ~8 min | ~$0.001 |
| mem0 Gemini | YES (new collection) | ~9,882 | ~9,882 | ~7 min | ~$0.001 |

Notes:
- Gemini `gemini-embedding-001` pricing: $0.00015 per 1K chars (≈ $0.15/1M tokens).
  Full corpus ≈ 9,882 × ~200 tokens avg = ~2M tokens total → ~$0.30 per system.
- Use `NOX_MEM_INGEST_LIMIT` / `MEM0_INGEST_LIMIT` for smoke: 100 chunks each.
- Gemini free tier: 1500 RPM embed. Rate-delay in nox_mem hybrid is 50ms/chunk (~20 RPS).
  mem0 uses batch embed (up to 100 items/call) → faster.

---

## 5. Execution Order (pod startup)

```bash
# 0. Set env
export GEMINI_API_KEY="<key>"
export GOOGLE_API_KEY="$GEMINI_API_KEY"   # mem0 Gemini embedder reads GOOGLE_API_KEY
export MEM0_TELEMETRY=False
export ANONYMIZED_TELEMETRY=False
export MEM0_SKIP_LLM_EXTRACTION=1
export MEM0_CHROMA_PATH="$(pwd)/eval/q4-comparison/.mem0-chroma-gemini"
export NOX_EVAL_MODE=hybrid
export NOX_EVAL_DB_PATH="$(pwd)/eval/q4-comparison/cache/nox-mem-hybrid.db"

# Optional smoke (100 chunks):
export NOX_MEM_INGEST_LIMIT=100
export MEM0_INGEST_LIMIT=100

# 1. Apply mem0 Gemini patch (via all_gemini_config.py — see §6)
#    This must happen before runner.py imports adapters.mem0.

# 2. Ingest nox-mem hybrid (idempotent if DB exists with same dim)
python -c "
import sys; sys.path.insert(0, 'eval/q4-comparison')
import adapters.nox_mem as m
m.setup(['locomo', 'longmemeval'])
m.teardown()
"

# 3. Ingest mem0 Gemini (separate process, mandatory for thread-leak isolation)
python -c "
import sys, os; sys.path.insert(0, 'eval/q4-comparison')
from lib.all_gemini_config import patch_mem0_adapter; patch_mem0_adapter()
import adapters.mem0 as m
m.setup()
m.teardown()
"

# 4. Run benchmark (both systems, no re-ingest)
python -c "
import sys; sys.path.insert(0, 'eval/q4-comparison')
from lib.all_gemini_config import patch_mem0_adapter; patch_mem0_adapter()
" && \
python eval/q4-comparison/runner.py \
  --systems nox_mem,mem0 \
  --datasets locomo,longmemeval \
  --queries-file eval/q4-comparison/cache/queries-n100.jsonl \
  --output-dir eval/q4-comparison/output/rc4-all-gemini

# 5. Aggregate
python eval/q4-comparison/aggregate.py \
  --input-dir eval/q4-comparison/output/rc4-all-gemini \
  --output eval/q4-comparison/output/rc4-all-gemini/summary.json
```

Note: Steps 3 and 4 both call `patch_mem0_adapter()` — the patch is idempotent (replaces
`_build_config` attribute on the already-imported module). Since the runner lazy-imports
adapters via `importlib.import_module`, patching before the runner's first `search()` call
is sufficient. The safest pattern is a wrapper script (see §6).

---

## 6. Recommended RC4 Runner Script

Instead of modifying runner.py (an existing file), create `runner_rc4.py` as a thin wrapper:

```python
# eval/q4-comparison/runner_rc4.py  (NEW file — safe to create)
"""RC4 all-Gemini wrapper: patches mem0 config before delegating to runner."""
import sys, os
from pathlib import Path
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from lib.all_gemini_config import patch_mem0_adapter, assert_env_ready
assert_env_ready()
patch_mem0_adapter()
import runner  # noqa: F401,E402 — must import AFTER patch
runner.main()
```

Then run:
```bash
python eval/q4-comparison/runner_rc4.py --systems nox_mem,mem0 --datasets locomo,longmemeval ...
```

---

## 7. Risks and Caveats

### 7.1 Results may reverse — this is a valid finding
If switching mem0 to Gemini closes the nDCG gap or reverses it (nox-mem < mem0), it would
confirm that the baseline split was partly embedding-quality driven rather than architecture.
This is the honest outcome to report in §6. Do NOT suppress or re-run until the gap reopens.

### 7.2 Dim mismatch: rc4 (768d) vs prod nox-mem (3072d)
rc4 nox-mem runs at 768d; prod nox-mem uses 3072d (explicit `outputDimensionality: 3072`
in TypeScript source `staged/A3/.../gemini.ts:27`). This means rc4 compares nox-mem at
sub-optimal embedding resolution vs prod. The §6 paper claim should state:
> "rc4 uses gemini-embedding-001 at 768d for both systems; prod nox-mem uses 3072d."

If a future experiment wants to match prod, add `output_dimensionality=3072` to
`_embed_text()` and `_embed_query()` in `adapters/nox_mem.py` — but this requires an
adapter edit and a full re-ingest of the hybrid DB.

### 7.3 mem0 LLM extraction
Even with `MEM0_SKIP_LLM_EXTRACTION=1`, mem0's `_build_config()` in the patched version
does not specify an LLM section. If mem0ai initializes a default LLM client at
`Memory.from_config()` time, `OPENAI_API_KEY` must be available. Set a non-empty dummy
value if the key is unavailable and extraction is off:
```bash
export OPENAI_API_KEY="not-used-extraction-off"
```

### 7.4 Chroma version compatibility with google-genai
mem0's Gemini embedder uses `from google import genai` (the new `google-genai` SDK, not
`google.generativeai`). If the pod's venv only has `google-generativeai` installed,
`pip install google-genai` is required before the Gemini embedder loads.
Check: `python -c "from google import genai; print(genai.__version__)"`.

### 7.5 agentmemory exclusion
agentmemory is excluded from rc4 (§1.3). Its §6 baseline scores remain valid as a
"native embedder" reference point. Do not re-run agentmemory as part of rc4.

---

## 8. Incertezas não resolvidas

| Uncertainty | Impact | Resolution |
|---|---|---|
| Does `google.generativeai.embed_content` without `output_dimensionality` return exactly 768d for `gemini-embedding-001`? | Defines actual dim in nox-mem hybrid DB | Confirm via `python -c "import google.generativeai as g; g.configure(api_key='...'); print(len(g.embed_content('models/gemini-embedding-001','test')['embedding']))"` on pod |
| Does the pod venv have `google-genai` (new SDK) in addition to `google-generativeai`? | mem0 Gemini embedder import fails if not | `pip list | grep google-gen` on pod |
| Does mem0ai 0.1.114 (pinned in adapter) use `GOOGLE_API_KEY` or `GEMINI_API_KEY`? | Wrong env var → auth failure | Confirmed via mem0 source: `os.getenv("GOOGLE_API_KEY")`. Set both for safety. |
| Does iii-engine (agentmemory) support Gemini? | If yes, agentmemory could join rc4 | Inspect `agentmemory --help` or its config schema on pod |
| Are there rate limits for Gemini `embed_content` batch calls from mem0? | Could cause partial ingest | Monitor for 429s; add retry config if needed |
