---
title: Threat Model
description: STRIDE matrix, 10 gap categories, and control matrix for memoria-nox.
sidebar:
  order: 1
---

Full source: [`docs/security/THREAT-MODEL.md`](https://github.com/totobusnello/memoria-nox/blob/main/docs/security/THREAT-MODEL.md)

## Scope

The threat model covers:
- **nox-mem.db** — SQLite file containing all chunks, vectors, KG, and audit logs
- **HTTP API** (:18802) — unauthenticated by default on localhost
- **MCP server** — runs in-process with the agent runtime
- **CLI** — invoked by user shell and cron jobs
- **Embedding provider API** — outbound Gemini / OpenAI calls

## STRIDE analysis (summary)

| Category | Threat | Primary Control |
|---|---|---|
| **Spoofing** | Forged ingest source paths | `realpath()` + allowlist validation |
| **Tampering** | Direct DB file modification | File permissions 0600, WAL mode |
| **Tampering** | `ops_audit` row deletion | DB trigger blocks DELETE/UPDATE on terminal rows |
| **Repudiation** | Claiming op did not run | `ops_audit` append-only log |
| **Information Disclosure** | World-readable DB file | `0600` ACL, snapshot dir `0700` |
| **Information Disclosure** | Secrets in chunk content | A1 privacy filter (13 patterns, FP 1.7%) |
| **Denial of Service** | Unbounded FTS5 query | Query length limit + timeout wrapper |
| **Elevation of Privilege** | Command injection via user input | `execFileSync(cmd, [args])` — no shell interpolation |

## Top 10 gaps (Wave B controls)

1. **API authentication** — HTTP API has no auth. Mitigated by localhost-only bind. Planned: token auth in P-series.
2. **Snapshot encryption** — Pre-op snapshots are plaintext SQLite. Mitigated by `0600` ACL. A2 AES-256-GCM encryption for export archives.
3. **Secrets in error paths** — Stack traces may leak env vars. `redactSecrets()` wrapper on all error serialization.
4. **KG extraction prompt injection** — Malicious content could manipulate LLM extraction. Input sanitization before Gemini calls.
5. **Cron job integrity** — Cron scripts not signed. Mitigated by file ownership checks.
6. **Dependency supply chain** — npm dependencies are untrusted. Mitigated by lockfile + Renovate + SBOM.
7. **Log injection** — User content in log lines. Structured logging (JSON) prevents CRLF injection.
8. **Path traversal** — `ingest <path>` with `../` sequences. `realpath()` + allowlist in `execFileSync` defense.
9. **Memory exhaustion** — Large ingest batches. Batch size cap + streaming pipeline.
10. **Stale WAL on restore** — Restoring snapshot without removing WAL/SHM causes corruption. `safeRestore()` removes WAL/SHM before restore.

## Key security rules

:::danger[Hard rules]
- `execFileSync(cmd, [args])` always — never `execSync` with template strings (command injection, CRITICAL)
- No API keys in git — ever. Regex grep before every commit.
- NEVER `sed -i` on `.db` files — corrupts SQLite page boundaries.
:::

## Vulnerability reporting

See [Vulnerability Reporting](/memoria-nox/security/reporting) for responsible disclosure policy.

## Review cadence

Threat model reviewed quarterly. Next review gate: Q3 2026.
