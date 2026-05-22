# nox-mem — Self-Hosting Guide

> **Audience:** operators deploying nox-mem to a VPS, cloud instance, or on-premises server.
> **Not for local dev** — use [QUICKSTART.md](QUICKSTART.md) for a 5-minute local install.
> **Updated:** 2026-05-22 · v3.7+

---

## §1 What this guide covers

nox-mem runs as a single Node.js process backed by a single SQLite file. That simplicity is intentional — it makes deployment, recovery, and auditing cheap. This guide gets you from a fresh VPS to a production-grade deployment: sizing, dependency install, systemd service, cron jobs, backups, monitoring, and cost estimation.

**What you will have when you are done:**

- `nox-mem-api` running under systemd, restart-on-crash, logs to `/var/log/`
- 4 cron jobs: schema-invariants canary, VPS healthcheck, daily maintenance, nightly KG extraction
- Pre-op snapshot system via `withOpAudit()` to `/var/backups/nox-mem/pre-op/`
- Daily backup rotation with 7-day retention
- Two built-in observability dashboards at `/observability/health.html` and `/observability/evals.html`

**Reference prod:** Hostinger VPS, 8 cores / 16 GB RAM / Ubuntu 22.04, running since 2026-04 with 69k+ chunks, 187.77.234.79:18802.

---

## §2 Hardware sizing

### Compute

| Workload | Min spec | Recommended | Tested at |
|---|---|---|---|
| < 10k chunks | 2 cores / 2 GB RAM | 4 cores / 4 GB | Small dev |
| 10k – 100k chunks | 4 cores / 4 GB | 8 cores / 16 GB | **Reference prod** |
| 100k – 500k chunks | 8 cores / 16 GB | 16 cores / 32 GB | Lab Q1 target |
| > 500k chunks | 16+ cores / 32+ GB | Distributed federation | Not yet validated |

The bottleneck at any scale is not CPU — it is the Gemini embedding round-trip (~800 ms at p50 for a fresh query). CPU spikes only during KG extraction (nightly cron) and FTS5 reindex. WAL mode means readers do not block writers; a single-process design means no connection-pool overhead.

### Disk

Estimation:
- Base install: ~500 MB (Node modules + build artifacts)
- Per chunk: ~1 KB (text + metadata)
- Per chunk embeddings: ~12 KB (3072-dimension float32 vector)
- Combined: ~13 MB per 1,000 chunks

Reference prod numbers:
- 69k chunks → approximately 1 GB DB (WAL + SHM files add ~100 MB during writes)
- Pre-op snapshots: up to 1 GB × number of destructive ops per day (7-day retention)
- Daily backups: 1 GB × 7 days = ~7 GB reserved at `/var/backups/nox-mem/`

**Minimum safe disk for reference prod workload:** 20 GB NVMe. Provision 50 GB if you expect corpus growth over 12 months.

### Network

Only outbound traffic to the Gemini API. No inbound ports required unless you expose the HTTP API. See §10 (security model) for reverse-proxy recommendations.

---

## §3 OS and dependencies

### Supported

| OS | Status |
|---|---|
| Ubuntu 22.04 LTS | Tested, reference prod |
| Debian 12 | Works |
| RHEL 9 / AlmaLinux 9 | Works (use `dnf` not `apt`) |
| macOS 14+ | Dev only — not for production |

### Required packages

```bash
# Ubuntu / Debian
sudo apt-get update
sudo apt-get install -y \
  nodejs \
  npm \
  python3 \
  python3-pip \
  sqlite3 \
  build-essential \
  inotify-tools \
  curl \
  jq

# Verify Node version — must be 20+
node --version   # expect v20.x or higher
python3 --version  # expect 3.10+
sqlite3 --version  # expect 3.40+ (Ubuntu 22.04 ships 3.37 — upgrade if needed)
```

**Node 20+ via NodeSource** if the distro ships an older version:

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### SQLite requirements

FTS5 and sqlite-vec are both required:

- **FTS5** — ships compiled-in on Ubuntu 22.04's SQLite package. Verify: `sqlite3 :memory: 'SELECT fts5(?1)' 'test'` — should return `test`, not an error.
- **sqlite-vec** — Node extension loaded at startup. Install:

```bash
pip3 install sqlite-vec
# Or via npm — nox-mem's package.json resolves the correct binary automatically.
# If the npm install fails on ARM64 / Alpine: build from source at https://github.com/asg017/sqlite-vec
```

### Optional

- **nginx / Caddy** — reverse proxy for TLS + auth. nox-mem binds to `127.0.0.1:18802` by default; expose via proxy only.
- **Cloudflare** — CDN / DDoS guard if you publish the API publicly.
- **tmux** — strongly recommended for long-running batch operations (embedding full corpus, KG extraction). Do not use nohup alone for multi-hour jobs.

---

## §4 Service install

### 1. Create the system user and directories

```bash
sudo useradd --system --no-create-home --shell /usr/sbin/nologin nox
sudo mkdir -p /opt/nox-mem
sudo mkdir -p /var/backups/nox-mem/pre-op
sudo mkdir -p /var/log/nox-mem
sudo chown nox:nox /opt/nox-mem /var/backups/nox-mem /var/log/nox-mem
sudo chmod 0700 /var/backups/nox-mem/pre-op
```

### 2. Clone and build

```bash
cd /opt/nox-mem
sudo -u nox git clone https://github.com/totobusnello/nox-mem.git .
sudo -u nox npm install
sudo -u nox npm run build
# Build output: dist/ directory (entry point: dist/index.js)
```

### 3. Configure environment

```bash
sudo -u nox cp .env.example /opt/nox-mem/.env
sudo chmod 0600 /opt/nox-mem/.env
sudo chown nox:nox /opt/nox-mem/.env
```

Edit `/opt/nox-mem/.env` — minimum required:

```bash
GEMINI_API_KEY=your-key-here
OPENCLAW_WORKSPACE=/opt/nox-mem
NOX_API_PORT=18802
NOX_SALIENCE_MODE=active
```

Full reference: `docs/ARCHITECTURE.md §9`.

### 4. Install the systemd unit

Create `/etc/systemd/system/nox-mem-api.service`:

```ini
[Unit]
Description=nox-mem API
Documentation=https://github.com/totobusnello/nox-mem
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=nox
Group=nox
WorkingDirectory=/opt/nox-mem
EnvironmentFile=/opt/nox-mem/.env
ExecStart=/usr/bin/node /opt/nox-mem/dist/index.js serve
Restart=always
RestartSec=10
# Limit restart storms
StartLimitIntervalSec=300
StartLimitBurst=5

# Logging
StandardOutput=append:/var/log/nox-mem/nox-mem.log
StandardError=append:/var/log/nox-mem/nox-mem.err

# Hardening
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ReadWritePaths=/opt/nox-mem /var/backups/nox-mem /var/log/nox-mem

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable nox-mem-api
sudo systemctl start nox-mem-api
sudo systemctl status nox-mem-api   # expect Active: active (running)
```

### 5. Verify

```bash
curl -s http://127.0.0.1:18802/api/health | jq '{schemaVersion, totalChunks, vectorCoverage}'
```

Expected output:

```json
{
  "schemaVersion": 10,
  "totalChunks": 0,
  "vectorCoverage": 1
}
```

`totalChunks: 0` on a fresh install is correct — you have not ingested anything yet.

---

## §5 Cron setup

**Critical preflight rule:** every cron job that calls the `nox-mem` CLI must source the environment first. Without it, vectorize and KG extraction fail silently ("Done: 0 embedded, N errors"):

```bash
set -a; source /opt/nox-mem/.env; set +a
```

All four scripts below are included in `scripts/`. Install them by adding to root crontab (`sudo crontab -e`):

```cron
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# Schema-invariants canary — every 15 minutes
*/15 * * * *  /opt/nox-mem/scripts/check-schema-invariants.sh >> /var/log/nox-mem/schema-invariants.log 2>&1

# VPS healthcheck — every 15 minutes
*/15 * * * *  /opt/nox-mem/scripts/vps-healthcheck.sh >> /var/log/nox-mem/healthcheck.log 2>&1

# Daily maintenance — 06:00 UTC
0 6 * * *     /opt/nox-mem/scripts/daily-maintenance.sh >> /var/log/nox-mem/daily-maintenance.log 2>&1

# Nightly maintenance (KG extraction) — Sunday 23:00 UTC
0 23 * * 0    /opt/nox-mem/scripts/nightly-maintenance.sh >> /var/log/nox-mem/nightly-maintenance.log 2>&1

# Daily backup — 02:00 UTC
0 2 * * *     /opt/nox-mem/scripts/backup-all.sh >> /var/log/nox-mem/backup.log 2>&1
```

**Why `PATH` must be explicit:** macOS and some Linux cron environments strip `/sbin` from PATH. The healthcheck script uses `ping`, which lives in `/sbin` on macOS. The explicit `PATH=` line prevents silent failures.

### Cron details

**1. Schema-invariants canary** (`*/15 * * * *` → `check-schema-invariants.sh`)

Validates four DB invariants every 15 minutes:
- Chunk count matches FTS5 index
- Vector coverage (embedded chunks / total chunks)
- KG entity count vs. known floor
- `ops_audit` table integrity (no orphaned rows)

Non-zero exit pages stderr to the systemd journal. First failure at 03:15 after a bad reindex is how you catch drift before users notice.

**2. VPS healthcheck** (`*/15 * * * *` → `vps-healthcheck.sh`)

Confirms the VPS is reachable and `/api/health` responds. The script uses `ping` + `curl` with short timeouts. Caught the 2026-05-20 Hostinger floating-IP swap within 30 minutes. Set up an external monitoring hook (UptimeRobot or equivalent) to alert on healthcheck failures.

**3. Daily maintenance** (`0 6 * * *` → `daily-maintenance.sh`)

Runs `consolidate` (low-risk compaction, not destructive), log rotation, and backup archival. Does **not** run `reindex` — reindex is treated as a destructive op and requires manual trigger with `--dry-run` first. Retention: backup files older than 7 days are deleted.

**4. Nightly maintenance** (`0 23 * * 0` → `nightly-maintenance.sh`)

Sunday only. Runs the KG extraction phase (Gemini 2.5 Flash) + L4 regex extraction. Populates `kg_relations.extraction_method` column. Monitor Monday morning with:

```bash
NOX_DB_PATH=/opt/nox-mem/nox-mem.db ./scripts/l4-watchpoint-check.sh
```

Expected output: `RESULT: PASS` with non-NULL extraction_method rows confirmed.

---

## §6 Backups and disaster recovery

### Backup strategy

| Layer | Trigger | Destination | Retention |
|---|---|---|---|
| Daily backup | `backup-all.sh` at 02:00 UTC | `/var/backups/nox-mem/daily/` | 7 days rolling |
| Pre-op snapshot | Every destructive op via `withOpAudit()` | `/var/backups/nox-mem/pre-op/` | 7 days rolling |

### Pre-op snapshots (automatic)

Every destructive operation — `reindex`, `consolidate`, `compact`, `crystallize`, `kg-prune` — creates a point-in-time snapshot via `VACUUM INTO` before touching data. The snapshot is stored at:

```
/var/backups/nox-mem/pre-op/<op>-<ts>-<pid>-<uuid>.db
```

File permissions: `0600`, directory: `0700`, owned by `nox`. Symlink-aware path validation via `realpathSync()` — no traversal exploit.

The `ops_audit` table logs every op with `started_at`, `status`, and snapshot path. Valid terminal statuses: `success`, `failed`, `crashed`. The table is append-only at the DB level (W2-1 triggers) — DELETE and UPDATE on terminal rows both error.

**Emergency override:** if a snapshot fails (e.g., disk full) and you must run the op anyway, set `NOX_ALLOW_NO_SNAPSHOT=1` in the environment. This is logged in `ops_audit` with the reason. Use it only when the snapshot failure cause is known and accepted.

### Recovery

**Do not** `cp snapshot.db nox-mem.db` directly — this leaves stale WAL/SHM files and corrupts the DB.

Use `safeRestore()` in `src/lib/op-audit.ts`:

```bash
# From the nox-mem CLI:
node /opt/nox-mem/dist/index.js restore --snapshot /var/backups/nox-mem/pre-op/<snapshot>.db
```

`safeRestore()` validates `user_version` match, restores the main DB, then removes orphaned WAL/SHM files in the correct order.

### Off-site backup

Off-site backup is intentionally **not included** in this guide. For the current scale (< 2 GB DB), VPS-native backup is sufficient. Hostinger daily snapshots provide an additional recovery point independent of the application-layer backups above. If your use case requires RPO < 24h or geographic redundancy, evaluate Litestream (streams WAL to S3) — but that is out of scope for v1.

### Verify backup integrity

```bash
# Check latest daily backup is present and readable
ls -lh /var/backups/nox-mem/daily/ | tail -5

# Quick integrity check on a snapshot
sqlite3 /var/backups/nox-mem/daily/latest.db "PRAGMA integrity_check;"
# Expected: ok
```

---

## §7 Monitoring and observability

### Built-in dashboards (F10)

Once the service is running, two dashboards are available:

| URL | Purpose | Update interval |
|---|---|---|
| `http://127.0.0.1:18802/observability/health.html` | Prod health snapshot + 24h delta | Auto-poll 30s |
| `http://127.0.0.1:18802/observability/evals.html` | Eval gate history (G5..G12) | On-demand |

Expose these behind a reverse proxy with authentication if the API is network-accessible.

### `/api/health` programmatic check

```bash
curl -s http://127.0.0.1:18802/api/health | jq '{
  schemaVersion,
  totalChunks,
  vectorCoverage,
  "orphanedVectors": .orphanedVectors,
  "sectionDistribution": .sectionDistribution
}'
```

Automation target: `vectorCoverage.embedded == vectorCoverage.total`. Any gap means chunks were ingested without embedding — run `nox-mem vectorize` to close it.

### Logs

| Log file | Source |
|---|---|
| `/var/log/nox-mem/nox-mem.log` | API server stdout |
| `/var/log/nox-mem/nox-mem.err` | API server stderr |
| `/var/log/nox-mem/schema-invariants.log` | Canary cron |
| `/var/log/nox-mem/healthcheck.log` | Healthcheck cron |
| `/var/log/nox-mem/daily-maintenance.log` | Daily maintenance |
| `/var/log/nox-mem/nightly-maintenance.log` | Nightly KG extraction |
| `/var/log/nox-mem/backup.log` | Backup cron |

Set up log rotation via `logrotate`:

```bash
# /etc/logrotate.d/nox-mem
/var/log/nox-mem/*.log {
    daily
    rotate 14
    compress
    missingok
    notifempty
    copytruncate
}
```

### External monitoring (recommended)

| Tool | How |
|---|---|
| UptimeRobot (free tier) | HTTP check on `http://<your-vps-ip>:18802/api/health` every 5 min |
| Better Uptime | Status page if you offer SLA to users |
| Grafana + Prometheus | Only if you already run the stack; no native nox-mem exporter in v1 |

### `ops_audit` table

Query it directly for a history of all destructive operations:

```bash
sqlite3 /opt/nox-mem/nox-mem.db \
  "SELECT op_name, status, started_at, snapshot_path FROM ops_audit ORDER BY started_at DESC LIMIT 20;"
```

Any row with `status = 'failed'` or `status = 'crashed'` needs investigation before running the same op again.

---

## §8 Cost estimation

### VPS

| Provider | Spec | Price/mo (approx.) |
|---|---|---|
| Hostinger Cloud VPS Premium | 8 cores / 16 GB | ~$30 |
| DigitalOcean s-8vcpu-16gb | 8 cores / 16 GB | ~$80 |
| AWS m5.xlarge | 4 cores / 16 GB | ~$140 (on-demand, no savings plan) |
| Hetzner CPX41 | 8 cores / 16 GB | ~$25 |

Hostinger is the reference deployment; Hetzner is the best price/performance alternative in EU.

### Gemini API

nox-mem uses two Gemini endpoints:

| Operation | Model | Cost |
|---|---|---|
| Embeddings (ingest + query) | `gemini-embedding-001` | $0.13 / M tokens |
| KG extraction (nightly) | `gemini-2.5-flash` | ~$0.0015 / 1k tokens |
| Answer generation | `gemini-2.5-flash-lite` | ~$0.0001 / 1k tokens |

**Per-operation estimates:**

- Chunk ingest: ~1k tokens → **$0.00013 / chunk**
- Query (embedding only): ~100 tokens → **$0.000013 / query**
- 1,000 queries/day → **~$0.40/mo**
- 100,000 queries/day → **~$40/mo**
- Full corpus embed (69k chunks): **~$9 one-time**
- Nightly KG extraction (delta ~200 chunks): **< $0.01/night**

**Default model selection rule:** use `gemini-2.5-flash-lite` for all agent infra tasks (heartbeats, summaries, routing). Switch to `gemini-2.5-flash` only for KG extraction. Never use `gemini-2.5-flash` for embeddings — the embedding model is `gemini-embedding-001` regardless of reasoning model choice.

**Do not use `gemini-2.5-flash` as the default** — at high volume it hits the 3M token/day quota. Stick to `flash-lite` for everything except KG extraction.

### Local model alternative (Autonomy pillar)

Running Ollama with `nomic-embed-text` eliminates the Gemini embedding cost entirely. Retrieval quality will differ — nox-mem's eval harness is benchmarked against Gemini 3072d embeddings. The local path is supported but not the default and has not been benchmarked on LongMemEval equivalents. If you go this route, run your own ablation first.

---

## §9 Scaling considerations

### When to worry

| Signal | Threshold | Action |
|---|---|---|
| Query latency p95 | > 3s | Profile — Gemini embed is usually the bottleneck |
| Embedding API quota | > 80% of daily limit | Switch to batch-embed cron pattern |
| Chunk count | > 200k | Monitor FTS5 BM25 scoring — large corpora need score normalization review |
| Concurrent queries | > 50 req/s | SQLite WAL handles concurrent reads well; writes will queue |

### SQLite write bottleneck

SQLite is single-writer. At v1, one workspace per VPS is the isolation model. If you need multi-user writes (multiple agents ingesting simultaneously), the practical limit is ~5–10 concurrent ingest processes before queue latency becomes noticeable. Writes are fast (< 1 ms for a chunk insert); the bottleneck is the Gemini embed round-trip before the write, not the write itself.

### Migration paths (future)

These are not v1 deliverables — they are documented here so you know where the architecture is heading:

- **Litestream** — streams WAL to S3 for point-in-time recovery and read replicas. Lab Q2 candidate.
- **Postgres + pgvector** — would replace SQLite + sqlite-vec for the vector layer. Loses the single-file simplicity; only makes sense at > 500k chunks sustained. Lab Q2 candidate.
- **Federation** — multiple VPS instances, federated at query time. The single-file invariant makes this natural: shard by workspace, merge results at the API gateway.
- **Distributed / horizontal** — not before v3.0. The architecture is explicitly designed to be simple first.

---

## §10 Pre-deploy checklist

Run through this before going live. Adapt `scripts/check-pre-launch.sh` for self-host validation.

```
Infrastructure
  [ ] VPS reachable via SSH; public IP confirmed
  [ ] Floating IP risk accepted (if using Hostinger — see [[vps-ip-change-2026-05-20]])
  [ ] DNS record pointing to VPS IP (if exposing publicly)

Dependencies
  [ ] Node 20+ installed (node --version)
  [ ] Python 3.10+ installed (python3 --version)
  [ ] SQLite >= 3.40 with FTS5 compiled in
  [ ] sqlite-vec extension resolves at Node startup
  [ ] inotify-tools installed (inotifywait --version)

Service
  [ ] systemd unit installed: /etc/systemd/system/nox-mem-api.service
  [ ] EnvironmentFile=/opt/nox-mem/.env readable by nox user
  [ ] GEMINI_API_KEY set in .env
  [ ] OPENCLAW_WORKSPACE set in .env
  [ ] Service active: systemctl status nox-mem-api
  [ ] /api/health returns HTTP 200

Crons
  [ ] 5 cron entries installed (crontab -l | grep nox-mem)
  [ ] PATH= line includes /sbin in crontab
  [ ] Scripts source .env before calling nox-mem CLI

Backups
  [ ] /var/backups/nox-mem/ created, perms 0700
  [ ] /var/backups/nox-mem/pre-op/ created, perms 0700
  [ ] Both owned by nox user
  [ ] backup-all.sh runs successfully: bash /opt/nox-mem/scripts/backup-all.sh
  [ ] sqlite3 /var/backups/nox-mem/daily/latest.db "PRAGMA integrity_check;" → ok

Monitoring
  [ ] /observability/health.html accessible
  [ ] External uptime check configured (UptimeRobot or equivalent)
  [ ] Logrotate configured: /etc/logrotate.d/nox-mem
  [ ] ops_audit table queryable

Security
  [ ] API binds to 127.0.0.1, not 0.0.0.0 (unless reverse proxy in front)
  [ ] Reverse proxy with TLS if API is externally accessible
  [ ] .env file perms 0600
  [ ] Backup dir perms 0700, files 0600
  [ ] Off-site backup accepted or explicitly deferred
```

---

## §11 Common issues and fixes

### "FTS5 not available"

```
Error: near "fts5": syntax error
```

SQLite was compiled without `--enable-fts5`. Ubuntu 22.04 ships with FTS5 compiled in — if you see this on Ubuntu, you may be running a custom SQLite build. Verify:

```bash
sqlite3 :memory: 'CREATE VIRTUAL TABLE t USING fts5(x);'
# Should return nothing (no error). Any error = FTS5 missing.
```

Fix: install `sqlite3` from the Ubuntu apt repo, not a custom build.

### "sqlite-vec extension not loaded"

Check the API startup log:

```bash
tail -50 /var/log/nox-mem/nox-mem.err | grep -i vec
```

The extension is loaded via Node's `better-sqlite3` Database options. If it fails to load, the process starts but vector search returns empty results without crashing. Run `curl /api/health | jq .vectorCoverage` — if `embedded: 0` and `total: N`, the extension did not load.

Fix: rebuild `better-sqlite3` with the extension:

```bash
cd /opt/nox-mem && npm rebuild better-sqlite3
sudo systemctl restart nox-mem-api
```

### "GEMINI_API_KEY rate limit" or quota exhaustion

Symptom: `nox-mem vectorize` reports "Done: 0 embedded, N errors" in the last line of output.

Cause 1: `.env` was not sourced. Run `set -a; source /opt/nox-mem/.env; set +a` first.  
Cause 2: Actual quota exhaustion. Check Gemini console quota usage. If you are near the 3M token/day limit, switch to `flash-lite` for all non-KG operations.

If you cannot resolve quota issues, local embedding via Ollama is supported — see §8 Local model alternative.

### "Port 18802 in use"

```bash
lsof -i :18802  # identify what is using the port
```

Set a different port: add `NOX_API_PORT=19000` (or any free port) to `/opt/nox-mem/.env` and restart the service. Note: port 18800 is squatted by Chrome on macOS — do not use it.

### High memory usage

Check current RSS:

```bash
ps aux | grep "dist/index.js serve" | awk '{print $6/1024 " MB"}'
```

Expected: 200–500 MB for a 69k-chunk corpus. If above 1 GB:
- Check vector coverage: `curl /api/health | jq .vectorCoverage` — partial coverage means sqlite-vec is loading partial index
- Check KG growth: `sqlite3 nox-mem.db 'SELECT COUNT(*) FROM kg_entities;'` — if > 50k, consider `kg-prune`
- Check for a hung consolidation: query `ops_audit` for rows with `status = 'started'` and old timestamps

### Logs filling disk

If `/var/log/nox-mem/` grows unexpectedly fast, check for crash-loop spam:

```bash
grep -c "Error\|FATAL" /var/log/nox-mem/nox-mem.err
```

A crash loop will generate hundreds of restart-error cycles per hour. Fix the underlying error, then `sudo systemctl restart nox-mem-api`.

### Schema-invariants canary fires at night

Likely cause: the daily maintenance cron ran `reindex` without `withOpAudit()` protecting the operation, and section/retention columns were zeroed. See `docs/INCIDENTS.md` — this happened in production on 2026-04-25.

Recovery: restore from the pre-op snapshot via `safeRestore()`. Then audit how the op was invoked.

---

## §12 See also

| Resource | What it covers |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System internals — schema, search layers, scoring, KG pipeline |
| [QUICKSTART.md](QUICKSTART.md) | Local dev install in 5 minutes |
| [FAQ.md](FAQ.md) | General questions about nox-mem |
| [docs/DECISIONS.md](DECISIONS.md) | Architectural decisions and explicit non-decisions |
| [docs/RUNBOOKS.md](RUNBOOKS.md) | Step-by-step recovery runbooks for known incidents |
| [audits/2026-05-22-pre-launch-security-review.md](../audits/2026-05-22-pre-launch-security-review.md) | Security model and trust boundaries |
| [docs/CONFIGURATION.md](CONFIGURATION.md) | Full `.env` reference |
