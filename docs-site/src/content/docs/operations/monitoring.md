---
title: Monitoring
description: Health endpoints, alerting, and observability for memoria-nox.
sidebar:
  order: 4
---

Full source: [`docs/ops/MONITORING.md`](https://github.com/totobusnello/memoria-nox/blob/main/docs/ops/MONITORING.md)

## Health endpoint

```bash
curl http://127.0.0.1:18802/api/health | jq .
```

Key fields:

| Field | Expected | Description |
|---|---|---|
| `vectorCoverage.embedded` | ≈ total | Chunks with embeddings |
| `vectorCoverage.total` | — | Total chunks |
| `sectionDistribution.compiled` | 183+ | Entity chunks ingested correctly |
| `opsAudit.recentFailed` | 0 | No recent failed operations |
| `salience` | — | Shadow salience scores (if `NOX_SALIENCE_MODE=shadow`) |

:::caution[Always verify DB state]
Never trust the last line of CLI output. `vectorize` can report `Done: 0 embedded, N errors` silently if `.env` was not sourced. Always confirm via `/api/health`.
:::

## Automated checks

| Frequency | Check | Alert channel |
|---|---|---|
| */5min | `/api/health` probe — service alive | Discord |
| */15min | Schema invariants (5 checks) | Discord |
| */30min | Semantic canary smoke test | Discord |
| 23:00 BRT | Nightly cron completion | Discord |

## Prometheus metrics

Prometheus endpoint (F10 observability, PR #35): `http://127.0.0.1:18802/metrics`

Key metrics:
- `nox_chunks_total` — total chunk count
- `nox_vec_coverage_ratio` — embedded / total
- `nox_search_latency_ms` — p50/p95/p99 histogram
- `nox_kg_entities_total` — entity count
- `nox_ops_audit_failed_total` — failed operation counter

## Key signals

```bash
# Vector coverage (should be ≈ 1.0)
curl -s http://127.0.0.1:18802/api/health | jq '.vectorCoverage.embedded / .vectorCoverage.total'

# Recent operation failures
curl -s http://127.0.0.1:18802/api/health | jq '.opsAudit.recentFailed'

# Entity section distribution (compiled should be ≥ 183)
curl -s http://127.0.0.1:18802/api/health | jq '.sectionDistribution'
```

## Alert playbook

| Alert | Likely cause | First action |
|---|---|---|
| Vector coverage drops | Vectorize cron failed | Check `/api/health`, source `.env`, run `nox-mem vectorize` |
| Invariant violation | Schema drift or entity reindex without routing guard | Check `ops_audit` table for recent failed ops |
| Semantic canary fails | Gemini quota exhausted or key expired | Check Gemini console, rotate key if needed |
| Service not responding | Process crashed | `systemctl restart nox-mem-api`, check journal |
