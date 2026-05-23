# agentmemory Smoke Validation — 2026-05-24

**Scope:** Install, daemon lifecycle, corpus ingest, Q4 runner smoke (5 queries), ID round-trip.  
**Linked PR:** validation/q4-agentmemory-smoke-2026-05-24  
**Time-box:** 1.5h (started ~2026-05-23 18:30 BRT)

---

## 1. Install

```
npm install -g @agentmemory/agentmemory
```

- **Version:** 0.9.21 (confirmed via `npm view @agentmemory/agentmemory version`)
- **Binary:** `/opt/homebrew/bin/agentmemory` → `../lib/node_modules/@agentmemory/agentmemory/dist/cli.mjs`
- **Node:** v25.9.0 / npm 11.12.1
- **Platform:** macOS arm64 (Darwin 25.5.0)
- **Warnings:** peer dep conflict `@anthropic-ai/sdk` (cosmetic — no install failure); deprecated `prebuild-install@7.1.3` / `node-domexception@1.0.0` (cosmetic)
- **Errors:** none

Note: `agentmemory --version` hangs (it boots the daemon). Version confirmed via npm, not CLI flag.

---

## 2. Daemon Lifecycle

### Start

```bash
nohup agentmemory > /tmp/agentmemory-daemon.log 2>&1 &
sleep 8   # daemon boot takes 5-8s (iii-engine process + WebSocket connect)
```

**Startup log confirms:**

```
iii-engine process started
iii-engine is ready
agentmemory v0.9.21
  REST API     http://localhost:3111
  Viewer       http://localhost:3113
  Streams      ws://localhost:3112
  Engine       ws://localhost:49134
```

### Health check

```bash
curl http://localhost:3111/agentmemory/livez
# → {"service":"agentmemory","status":"ok"}
```

### Stop

```bash
pkill -f agentmemory   # may need -9 if iii-engine subprocess persists
```

**Important:** memories persist across daemon restarts (iii-engine stores to disk).

---

## 3. API Endpoint Findings

| Endpoint | Method | Status | Notes |
|---|---|---|---|
| `/agentmemory/livez` | GET | 200 OK | `{"service":"agentmemory","status":"ok"}` |
| `/agentmemory/remember` | POST | 200 OK | `{success: true, memory: {id: "mem_xxx", ...}}` |
| `/agentmemory/search` | POST | 200 OK | Returns **dict** `{format, results, tokens_used, truncated}` — NOT bare list |
| `/agentmemory/memories` | GET | 200 OK | `{memories: [...]}` — used for idempotency count |
| `/agentmemory/stats` | GET | **404** | Not implemented in v0.9.21 |
| `/agentmemory/health` | GET | 200 OK | Circuit breaker status — no memory count |

**Pre-fix adapter bugs caught during validation:**

1. `_count_existing()` tried `/agentmemory/stats` (404) and `/agentmemory/health` (no count field) → returned `None` → idempotency check broken.  
   Fix: use `GET /agentmemory/memories` → `len(data["memories"])`.

2. `setup()` was a no-op (`return None`) — corpus never ingested → 0 search results.  
   Fix: `setup()` now calls `_ingest_from_corpus_cache()` from shared JSONL cache.

---

## 4. Corpus Ingest Design

The adapter ingests via `setup()` using `lib.corpus_loader` JSONL cache:

- Cache: `eval/q4-comparison/cache/locomo.jsonl` (5,882 chunks) + `longmemeval.jsonl` (948 chunks)
- Content format: `"[nox_id:<id>] <text>"` — embeds nox-mem chunk ID as parseable prefix
- ID round-trip: `search()` parses `[nox_id:...]` from narrative/facts → returns `conv-XX::DX:X` format IDs

### Env controls

| Variable | Default | Effect |
|---|---|---|
| `AGENTMEMORY_INGEST_LIMIT=N` | unset (all) | Stop after N chunks (smoke/unit tests) |
| `AGENTMEMORY_FORCE_REINGEST=1` | off | Bypass idempotency check |

### Idempotency

`GET /agentmemory/memories` returns existing count. If count ≥ expected, skips ingest.  
Works correctly on second run.

### Latency benchmark

`POST /agentmemory/remember` avg: **~460ms/chunk**.  
- 50 chunks ≈ 23s (smoke)  
- Full 5,882 locomo ≈ 45 min  
- Full 6,830 total corpus ≈ 52 min

**Recommendation:** use `AGENTMEMORY_INGEST_LIMIT` for smoke tests; full Q4 run requires overnight or pre-warm.

---

## 5. Q4 Runner Smoke Results

Command:

```bash
cd eval/q4-comparison
AGENTMEMORY_FORCE_REINGEST=1 AGENTMEMORY_INGEST_LIMIT=50 \
  python3 runner.py --systems agentmemory --datasets locomo --limit 5
```

**Output:** `eval/q4-comparison/output/agentmemory.json`

| Metric | Value |
|---|---|
| Queries | 5/5 |
| Errors | 0 |
| gold_hits | 1/13 |
| Results returned (total) | 41 |
| ID format | `conv-XX::DX:X` (correct) |
| mem_xxx IDs in output | 0 |

The 1/13 gold hit is conv-26::q6 → conv-26::D2:7 (chunk at line 25 in corpus, within the 50-chunk limit). The other 12 gold IDs live at lines 511–5688, beyond the limit.

**Conclusion:** pipeline works end-to-end. gold_hits = 1 is expected given limit=50. Full corpus ingest required for meaningful nDCG.

---

## 6. ID Round-Trip Verification

Sample result from `output/agentmemory.json`:

```json
{
  "question_id": "conv-26::q6",
  "gold_chunk_ids": ["conv-26::D2:7"],
  "results": [
    {"id": "conv-26::D2:7", "score": 13.868, "text": "Sophia: ..."}
  ]
}
```

ID `conv-26::D2:7` correctly returned (not `mem_xxx`). Round-trip via `[nox_id:...]` prefix confirmed.

---

## 7. Full Q4 Run Notes

For the real Q4 benchmark:

1. Pre-warm the daemon: `agentmemory &; sleep 8`
2. Run with full corpus: `python3 runner.py --systems agentmemory --datasets locomo,longmemeval --limit 100`  
   (Omit `AGENTMEMORY_INGEST_LIMIT` — let it ingest all 6,830 chunks; ~52 min first run)
3. On re-run, idempotency check skips ingest.
4. AGENTMEMORY_FORCE_REINGEST=1 to re-ingest if corpus changed.

---

## 8. Bugs Fixed (PR #283)

| ID | File | Description |
|---|---|---|
| B1 | `adapters/agentmemory.py` | `setup()` was no-op; now ingests corpus from shared JSONL cache |
| B2 | `adapters/agentmemory.py` | `_count_existing()` hit 404 `/stats` endpoint; now uses `/memories` |

---

## 9. Daemon Start/Stop Sequence (canonical)

```bash
# START
nohup agentmemory > /tmp/agentmemory-daemon.log 2>&1 &
AGENTMEMORY_PID=$!
sleep 8
curl http://localhost:3111/agentmemory/livez  # {"service":"agentmemory","status":"ok"}

# INGEST (first run only; idempotent)
# Done automatically by runner.py via adapter.setup()

# RUN
python3 runner.py --systems agentmemory --datasets locomo,longmemeval --limit 100

# STOP
kill $AGENTMEMORY_PID  # or pkill -f agentmemory
```
