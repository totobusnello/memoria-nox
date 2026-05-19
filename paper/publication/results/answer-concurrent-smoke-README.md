# answer-concurrent-smoke — README

Smoke test for `/api/answer` under concurrent load. Validates PR #114 behavior
when 10 threads hit the endpoint simultaneously.

## Quick start (on VPS)

```bash
ssh root@<vps>

# 1. Create dirs
mkdir -p /root/.openclaw/eval/paper/baselines
mkdir -p /root/.openclaw/eval/paper/results

# 2. Copy files from local
scp paper/publication/baselines/answer_concurrent_smoke.py \
    paper/publication/data/latency-queries-100.jsonl \
    root@<vps>:/root/.openclaw/eval/paper/

# 3. Load env + run (default: 50 req, 10 concurrent)
set -a; source /root/.openclaw/.env; set +a
cd /root/.openclaw/eval/paper
python3 baselines/answer_concurrent_smoke.py

# 4. Conservative run (cheaper, lower risk)
python3 baselines/answer_concurrent_smoke.py --total 30 --concurrent 5

# 5. Pull results back
scp root@<vps>:/root/.openclaw/eval/paper/results/answer-concurrent-smoke.json \
    paper/publication/results/
```

## CLI flags

| Flag | Default | Description |
|------|---------|-------------|
| `--endpoint` | `http://127.0.0.1:18802/api/answer` | API endpoint (reads `NOX_API_ENDPOINT` env) |
| `--concurrent` | `10` | Parallel threads — max 10 without explicit consent |
| `--total` | `50` | Total requests across all threads |
| `--queries` | `paper/publication/data/latency-queries-100.jsonl` | Query pool file |
| `--pool-size` | `20` | Number of queries to load from file |
| `--output` | `paper/publication/results/answer-concurrent-smoke.json` | Output JSON path |
| `--timeout` | `30` | Per-request timeout in seconds |
| `--verbose` | off | Print every request (default: errors only) |
| `--no-output` | off | Skip writing file |
| `--seed` | none | Random seed for reproducible query sampling |

## Expected output shape

```json
{
  "meta": {
    "endpoint": "http://127.0.0.1:18802/api/answer",
    "concurrent": 10,
    "total_requests": 50,
    "queries_pool_size": 20,
    "timeout_sec": 30,
    "ran_at": "2026-05-18T..."
  },
  "wall_clock_sec": 12.34,
  "throughput_rps": 4.06,
  "latency_per_request": {
    "p50": 1.80,
    "p95": 2.65,
    "p99": 2.90,
    "max": 3.10,
    "min": 1.40,
    "mean": 1.85,
    "n": 50
  },
  "status_distribution": {"200": 48, "500": 2},
  "error_count": 2,
  "errors": [
    {"query": "...", "status_code": 500, "error": null, "latency_sec": 2.1}
  ],
  "answer_metadata": {
    "retry_count_p50": 0,
    "retry_count_max": 1,
    "sources_count_p50": 5.0
  }
}
```

## Health signals to look for

| Signal | Good | Concern |
|--------|------|---------|
| `status_distribution["200"]` | = total_requests | Any 500/503/429 |
| `latency_per_request.p95` | < 5.0s | > 8.0s (queue starvation) |
| `latency_per_request.p99` | < 8.0s | > 15.0s (timeout pressure) |
| `answer_metadata.retry_count_max` | 0 | ≥ 2 (Gemini saturation) |
| `error_count` | 0 | > 5% of total |

## Cost estimate

| Requests | Est. cost |
|----------|-----------|
| 30 | ~$0.015 |
| 50 | ~$0.025 |
| 100 | ~$0.050 |

Each request invokes Gemini (embedding lookup + generation). Do NOT run
`--concurrent > 10` without checking quota — rate limiting (429) will inflate
error counts and latency artificially.

## Caveats

- Endpoint binds to `127.0.0.1` only. Script must run on VPS (or via SSH tunnel).
- `requests` library is optional — falls back to stdlib `urllib` if not installed.
- `retry_count` in `answer_metadata` requires the `/api/answer` response to
  include a `metadata.retry_count` field. If absent, it will be `null` in output.
- Throughput (`throughput_rps`) is wall-clock-based — includes all overhead
  (thread scheduling, GIL contention). True server-side RPS may be slightly higher.

## Results location

Place actual run output at:
`paper/publication/results/answer-concurrent-smoke.json`

Timestamp in `meta.ran_at` identifies the run uniquely.
