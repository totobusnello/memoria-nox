# Q4 COMPARISON harness — kickoff guide

> Saturday 2026-05-24 morning runbook. Spec: [`specs/2026-05-23-Q4-comparison-execution-plan.md`](../../specs/2026-05-23-Q4-comparison-execution-plan.md). Status: scaffolding shipped overnight Fri 2026-05-23, awaiting Toto's `python runner.py` run.

This harness drives 6 memory systems against LongMemEval + LoCoMo and writes
per-system JSON output, then aggregates into cross-system tables for
`docs/COMPARISON.md`.

Toto runs every command below from `eval/q4-comparison/` on the VPS (or
locally, with `NOX_API_BASE` pointed at the VPS endpoint).

---

## Saturday 9-step recipe

```bash
# 1. cd into the harness dir
cd eval/q4-comparison/

# 2. Install Python deps (≈10 min depending on the network)
#    Pinned versions live in REQUIREMENTS.md (rationale per pin)
pip install -r requirements.txt

# 3. Spin up Docker side (Zep OSS + Postgres, optionally Letta + nox-mem)
docker compose -f compose/docker-compose.yml up -d zep postgres
#    Optional extra profiles:
#       docker compose -f compose/docker-compose.yml --profile letta up -d
#       docker compose -f compose/docker-compose.yml --profile noxmem up -d

# 4. Export env vars (or pre-load via direnv / .env.q4)
export OPENAI_API_KEY=...           # required by Mem0 + Letta defaults
export GEMINI_API_KEY=...           # required by nox-mem
#    Optional:
# export NOX_API_BASE=http://vps:18802  # if running nox-mem-api elsewhere
# export ZEP_API_URL=http://127.0.0.1:8000
# export LETTA_BASE_URL=http://127.0.0.1:8283

# 5. Smoke test — validates every adapter without burning API quota
python smoke_test.py
#    Expected: 6/6 OK (or 5/6 if iii-engine / EverMind blocker hits)

# 6. Dry-run the runner — prints plan + per-adapter validation, no API calls
python runner.py --dry-run

# 7. Run the actual comparison (~4-5h compute per spec §6)
python runner.py \
    --systems all \
    --datasets locomo,longmemeval \
    --limit 100 \
    --k 10

# 8. Aggregate cross-system tables
python aggregate.py
#    → output/_aggregate.json  (machine-readable)
#    → output/_aggregate.md    (markdown ready to paste into docs/COMPARISON.md)

# 9. Review output/ and merge findings into docs/COMPARISON.md
ls output/
cat output/_aggregate.md
```

---

## Zep OSS — setup & corpus ingestion

Zep uses a session-based memory model: chunks are stored as "messages" inside
sessions. The adapter groups chunks by conversation prefix (`conv-48::...` →
session `q4-conv-48`) and stores the original gold chunk ID in message metadata
so search results can be mapped back.

### Docker startup

```bash
# Start Zep OSS + backing Postgres (default port 8000)
docker compose -f compose/docker-compose.yml up -d zep postgres

# Verify healthy
curl http://127.0.0.1:8000/healthz   # expected: {"status":"ok"}
```

### Pre-run corpus ingest (Zep only)

Unlike nox-mem (corpus pre-loaded), Zep needs explicit ingestion before
queries run. Call `ingest_corpus()` from the adapter in your pre-run script:

```python
import sys; sys.path.insert(0, ".")
import adapters.zep as zep_adapter

zep_adapter.setup()
chunks = [  # shape: {"id": <gold_id>, "text": <content>, [conv_id], [metadata]}
    {"id": "conv-48::D2:13", "text": "Deborah finds peace in mountains."},
    ...
]
result = zep_adapter.ingest_corpus(chunks)
print(result)  # {"sessions_created": N, "messages_added": M, "errors": 0}
```

Chunks sharing the same conversation prefix land in one Zep session — this
mirrors Zep's intended use case (per-conversation memory). Ingestion is
idempotent (existing sessions are reused).

### Running tests

```bash
# Unit tests (no Zep daemon needed, CI-safe)
pytest test/test_zep_ingest.py -m "not integration" -v

# Integration tests (requires docker compose up first)
pytest test/test_zep_ingest.py -v
```

---

## agentmemory — daemon setup (validated 2026-05-24)

agentmemory uses a local daemon (iii-engine) on `:3111`. The daemon must be
running before `runner.py` is invoked.

### Install

```bash
npm install -g @agentmemory/agentmemory   # v0.9.21; Node ≥ 18
```

Note: `agentmemory --version` **hangs** (it starts the daemon). Confirm version
via `npm view @agentmemory/agentmemory version`.

### Start daemon

```bash
nohup agentmemory > /tmp/agentmemory-daemon.log 2>&1 &
sleep 8   # iii-engine boot takes 5-8s
curl http://localhost:3111/agentmemory/livez   # → {"service":"agentmemory","status":"ok"}
```

### Corpus ingest

`setup()` handles corpus ingest automatically from the shared JSONL cache.
It is idempotent — safe to call multiple times.

```bash
# First run (smoke test, limit 50 chunks for speed):
AGENTMEMORY_INGEST_LIMIT=50 python3 runner.py --systems agentmemory --datasets locomo --limit 5

# Full Q4 run (no limit; first run ~52 min to ingest 6830 chunks at ~460ms/chunk):
python3 runner.py --systems agentmemory --datasets locomo,longmemeval --limit 100
```

**Env overrides:**

| Variable | Default | Effect |
|---|---|---|
| `AGENTMEMORY_INGEST_LIMIT=N` | unset (all chunks) | Limit ingest to N chunks |
| `AGENTMEMORY_FORCE_REINGEST=1` | off | Re-ingest even if count matches |
| `AGENTMEMORY_URL` | `http://localhost:3111` | Non-default daemon URL |

### Stop daemon

```bash
pkill -f agentmemory   # memories persist across restarts (iii-engine disk storage)
```

### Smoke result (2026-05-24)

```
5/5 queries, 0 errors, gold_hits=1/13 (limit=50; remaining gold IDs at corpus lines 511-5688)
ID format: conv-XX::DX:X  (correct — no mem_xxx leakage)
```

Full audit: `audits/2026-05-24-agentmemory-smoke-validation.md`.

---

## What's in this directory

| Path | Role |
|---|---|
| `adapters/__init__.py` | Adapter contract (Protocol type) + `ALL_ADAPTERS` registry |
| `adapters/nox_mem.py` | nox-mem via HTTP `/api/search` |
| `adapters/mem0.py` | Mem0 via Python SDK |
| `adapters/zep.py` | Zep OSS via `zep_python` |
| `adapters/letta.py` | Letta via `letta_client.archival_memory_search` |
| `adapters/agentmemory.py` | agentmemory via REST API (iii-engine v0.9.21); daemon required |
| `adapters/evermind.py` | EverMind-AI via CLI OR Python module (dual path) |
| `compose/docker-compose.yml` | Self-hosted Zep + Postgres (+ optional profiles) |
| `requirements.txt` | Python pins for all SDKs |
| `REQUIREMENTS.md` | Per-system install rationale + blockers |
| `runner.py` | Main dispatcher — `--dry-run` first, then real run |
| `smoke_test.py` | Pre-flight adapter validation (no API calls) |
| `aggregate.py` | nDCG@10 / R@10 / MRR / latency percentiles + markdown |
| `output/` | Per-system JSON results (gitignored except `.gitkeep`) |

---

## Adapter contract (cheat-sheet)

Every adapter module exposes:

```python
NAME: str                            # display name, e.g., "mem0"
VERSION_PIN: str                     # exact resolved version
REQUIRES_ENV: list[str]              # mandatory env vars
INSTALL_HINT: str                    # one-line install command

def validate() -> dict:              # returns {ok, error, version, notes}
def setup() -> None:                 # idempotent; called before first search
def teardown() -> None:              # idempotent; called after dataset finish
def search(query: str, k: int = 10) -> list[dict]:
    # Returns ranked items. Each item: {id, score, text, source}.
    # Latency measured externally (around call).
```

Adding a new adapter:

1. Create `adapters/<name>.py` matching the contract above.
2. Add `<name>` to `ALL_ADAPTERS` in `adapters/__init__.py`.
3. Pin its version in `requirements.txt` (or document the install path in
   `REQUIREMENTS.md` if it's not a PyPI package).
4. Run `python smoke_test.py --systems <name>` to validate.

---

## Stop conditions (per spec §8)

The run is **aborted + escalated** if any of:

1. Smoke test shows 3+ adapters failing `validate()` → setup gap too wide.
2. nox-mem result falls > 15pp below the G5 V3 internal baseline → likely
   corpus drift; investigate before publishing.
3. Mid-run latency consistently > 30 s/query → infrastructure issue; retry
   Monday.

The runner does NOT auto-stop on individual query errors. It logs them per
record (`error: "..."`) and continues; aggregator filters errored queries
from ranking metrics but counts them in `n_errors`.

---

## Methodology guarantees (per spec §5)

1. **Identical corpus.** Every system ingests the same chunks before
   queries run (ingest step is currently out-of-band — see
   `benchmark/collect-competitor-data.ts` and methodology writeup planned
   for Sun 2026-05-25 in `docs/Q4-COMPARISON-METHODOLOGY.md`).
2. **Identical eval set.** All systems get the same queries + gold sets.
3. **Native defaults.** No tuning to win — each system runs as-shipped.
4. **K cutoff = 10.** Standardized; runner enforces.
5. **Embeddings.** Gemini for nox-mem; each competitor's native default.
   Optional side-experiment: "all Gemini" with `MEM0_EMBED_PROVIDER=gemini`
   etc. — not in the headline number.

---

## Cost expectations

| System | Per-query cost | Why |
|---|---|---|
| nox-mem | ~$0.000004 | Gemini flash-lite embed + local SQLite |
| Mem0 | ~$0.00001 | OpenAI text-embedding-3-small per query |
| Letta | ~$0.00001 | OpenAI default |
| Zep OSS | ~$0 | FastEmbed (local), no API calls in default OSS config |
| agentmemory | ~$0 | local iii-engine |
| EverMind-AI | ~$0 | sentence-transformers local |

Per spec §6: 100 queries × 2 datasets × 6 systems = 1,200 calls per system,
total ≈ 7,200 API calls. Budget well under $1.

---

## Cross-references

- Spec: `specs/2026-05-23-Q4-comparison-execution-plan.md`
- Working draft headline numbers: `benchmark/COMPARISON.md`
- Competitor configs (long-form, used by `benchmark/`): `benchmark/competitor-configs.json`
- Gate D43: `docs/DECISIONS.md` D43
- GTM Phase 2: `docs/ROADMAP.md` §7

---

*Last updated 2026-05-21 overnight (Toto's Friday → Saturday handoff).*
