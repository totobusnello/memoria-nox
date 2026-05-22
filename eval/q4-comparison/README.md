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

## What's in this directory

| Path | Role |
|---|---|
| `adapters/__init__.py` | Adapter contract (Protocol type) + `ALL_ADAPTERS` registry |
| `adapters/nox_mem.py` | nox-mem via HTTP `/api/search` |
| `adapters/mem0.py` | Mem0 via Python SDK |
| `adapters/zep.py` | Zep OSS via `zep_python` |
| `adapters/letta.py` | Letta via `letta_client.archival_memory_search` |
| `adapters/agentmemory.py` | agentmemory via CLI subprocess |
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
