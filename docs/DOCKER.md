# nox-mem — Docker Install Guide

> **Scope:** local development and single-user evaluation.
>
> For production VPS deployment (systemd, reverse proxy, TLS, resource limits), see **`DEPLOY-WAVE-B.md`** (not Docker).

---

## Contents

1. [Quick start](#1-quick-start)
2. [Requirements](#2-requirements)
3. [Configuration](#3-configuration)
4. [Persistence](#4-persistence)
5. [Updating](#5-updating)
6. [Backup and restore](#6-backup-and-restore)
7. [Development mode](#7-development-mode)
8. [Production considerations](#8-production-considerations)
9. [Troubleshooting](#9-troubleshooting)
10. [Limitations](#10-limitations)

---

## 1. Quick start

```bash
# 1. Clone the repo
git clone https://github.com/totobusnello/memoria-nox.git
cd memoria-nox

# 2. Create your config — set GEMINI_API_KEY at minimum
cp .env.example .env
$EDITOR .env   # fill in GEMINI_API_KEY

# 3. Start the stack
docker compose up -d

# 4. Verify the API is healthy (wait ~10s for first-boot init)
curl http://localhost:18802/api/health | jq .

# 5. Ingest your first document
docker compose exec nox-mem-api node dist/index.js ingest /data/notes.md

# 6. Search
docker compose exec nox-mem-api node dist/index.js search "salience formula"
```

The API is now available at `http://localhost:18802`. The SSE viewer (P5) is at `http://localhost:18802/ui`.

---

## 2. Requirements

| Requirement | Minimum | Notes |
|---|---|---|
| Docker Engine | 24+ | BuildKit enabled by default |
| Docker Compose | v2.20+ | `docker compose` (v2 syntax, no hyphen) |
| CPU | amd64 or arm64 | Multi-arch image (see [§8](#8-production-considerations)) |
| RAM | 512 MB | 1 GB recommended for large corpora (>50k chunks) |
| Disk | 1 GB free | SQLite DB grows with corpus size (~5 MB per 1k chunks) |
| Gemini API key | Required | Get one at [aistudio.google.com](https://aistudio.google.com) — free tier works |

---

## 3. Configuration

All configuration is via environment variables. Copy `.env.example` to `.env` and edit:

```bash
cp .env.example .env
```

**Minimum required:**

```bash
GEMINI_API_KEY=AIzaSy...   # your Gemini API key
```

Everything else has safe defaults. Key variables:

| Variable | Default | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | _(required)_ | Embedding + KG extraction |
| `NOX_API_PORT` | `18802` | HTTP API port |
| `NOX_DB_PATH` | `/data/nox-mem.db` | SQLite file path inside container |
| `NOX_MEM_DIR` | `/data` | Data root inside container |
| `NOX_SALIENCE_MODE` | `shadow` | Ranking mode — flip to `active` only after eval gate |
| `NOX_PROVIDER_HEALTH_FAIL_FAST` | `1` | Fail startup if provider unreachable |

Full reference: [`docs/CONFIGURATION.md`](CONFIGURATION.md).

### Overriding individual vars

You can override any `.env` variable without editing the file:

```bash
NOX_SALIENCE_MODE=active docker compose up -d
```

Or add an override section to `docker-compose.yml` under `environment:`.

---

## 4. Persistence

The SQLite database (your entire memory store) is mounted at `./data:/data`:

```
./data/           ← on your host machine
  nox-mem.db      ← SQLite file — this IS your memory
  nox-mem.db-wal  ← WAL journal (normal — auto-checkpointed)
```

**The `./data/` directory must exist before starting:**

```bash
mkdir -p data
docker compose up -d
```

If you move the project, move `./data/` with it. The SQLite file is self-contained — no export needed.

### Verify data is persisting

```bash
# Check chunk count before restart
curl http://localhost:18802/api/health | jq .chunkCount

docker compose restart nox-mem-api

# Should match after restart
curl http://localhost:18802/api/health | jq .chunkCount
```

---

## 5. Updating

```bash
# Pull the latest image
docker compose pull

# Restart with new image (zero-downtime for single-container setup)
docker compose up -d --no-deps nox-mem-api

# Verify health
curl http://localhost:18802/api/health | jq .schemaVersion
```

Schema migrations run automatically on startup — the server applies pending migrations before accepting connections.

### Rolling back

If you need to roll back to a previous image version:

```bash
# Pin to a specific tag
docker compose stop nox-mem-api
# Edit docker-compose.yml: change image tag to previous version
docker compose up -d nox-mem-api
```

Always verify `/api/health` after rollback — confirm `schemaVersion` did not regress.

---

## 6. Backup and restore

### Quick backup (copy the SQLite file)

```bash
# While API is running — uses VACUUM INTO for safe hot backup
docker compose exec nox-mem-api \
  node dist/index.js export --output /data/backup-$(date +%Y%m%d).tar.gz
```

Or copy the SQLite file directly (safe while API is running via WAL):

```bash
# Stop writes first for a clean copy (optional but safer)
docker compose stop nox-mem-api
cp data/nox-mem.db data/nox-mem.db.bak-$(date +%Y%m%d)
docker compose start nox-mem-api
```

### Restore

```bash
docker compose stop nox-mem-api
cp data/nox-mem.db.bak-20260518 data/nox-mem.db
# Remove stale WAL/SHM files — required after manual copy
rm -f data/nox-mem.db-wal data/nox-mem.db-shm
docker compose start nox-mem-api
curl http://localhost:18802/api/health | jq .chunkCount
```

> Never use `cp backup.db nox-mem.db` while the API is running — this can corrupt the WAL journal. Always stop first or use `nox-mem export` for live backups.

### Automated daily backup

Add to your host crontab:

```cron
0 2 * * * cd /path/to/memoria-nox && docker compose exec -T nox-mem-api node dist/index.js export --output /data/backup-$(date +\%Y\%m\%d).tar.gz 2>> /var/log/nox-backup.log
```

---

## 7. Development mode

For live TypeScript reloading (no rebuild required after source edits):

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

This override:
- Mounts `./src` into the builder stage container
- Runs `tsx --watch src/index.ts serve` instead of `node dist/index.js serve`
- Exposes Node inspector on port `9229` for VS Code / Chrome DevTools
- Sets `NODE_ENV=development`

### Attach VS Code debugger

1. Open VS Code in the project root
2. Add to `.vscode/launch.json`:

```json
{
  "type": "node",
  "request": "attach",
  "name": "Docker: nox-mem",
  "remoteRoot": "/build",
  "localRoot": "${workspaceFolder}",
  "port": 9229,
  "restart": true
}
```

3. Start the dev compose stack, then run the "Docker: nox-mem" launch config.

---

## 8. Production considerations

> **The recommended production path is not Docker.** See `DEPLOY-WAVE-B.md` for the VPS setup with systemd, reverse proxy (Caddy), TLS, and resource limits.
>
> If you choose to run Docker in production anyway, apply everything in this section.

### Reverse proxy (TLS)

Never expose port 18802 directly to the internet. Put nox-mem behind a reverse proxy:

**Caddy example (`Caddyfile`):**

```
mem.yourdomain.com {
    reverse_proxy localhost:18802
}
```

**nginx example:**

```nginx
location /nox-mem/ {
    proxy_pass http://127.0.0.1:18802/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

### Auth token (required if network-exposed)

Generate and set `NOX_VIEWER_AUTH_TOKEN` when the API is accessible beyond localhost:

```bash
echo "NOX_VIEWER_AUTH_TOKEN=$(openssl rand -hex 32)" >> .env
docker compose up -d
```

All `/api/*` requests then require `Authorization: Bearer <token>`.

### Resource limits

Add to `docker-compose.yml` under `nox-mem-api:`:

```yaml
deploy:
  resources:
    limits:
      memory: 1g
      cpus: '1.0'
    reservations:
      memory: 256m
```

### Multi-arch build (amd64 + arm64)

The Dockerfile supports both architectures. To build for both:

```bash
docker buildx create --use --name nox-builder
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag ghcr.io/totobusnello/memoria-nox:latest \
  --push .
```

### Read-only filesystem

The `docker-compose.yml` already sets `read_only: true`. The only writable surface is `/data` (via volume) and `/tmp` (via tmpfs). This means:
- No process inside the container can modify the image layer
- Attacks that write to `/etc`, `/bin`, etc. are blocked
- `/data` must be writable — verify with `ls -la data/`

---

## 9. Troubleshooting

### Container exits immediately

```bash
docker compose logs nox-mem-api
```

**Common causes:**

| Error | Fix |
|---|---|
| `GEMINI_API_KEY is not set` | Set `GEMINI_API_KEY` in `.env` |
| `Data directory /data is not writable` | Run `mkdir -p data && chmod 755 data` on host |
| `Cannot find module dist/index.js` | Rebuild: `docker compose build --no-cache` |
| `address already in use :18802` | Another process is using 18802 — change `NOX_API_PORT` in `.env` |

### Health check failing

```bash
# Check from inside the container
docker compose exec nox-mem-api wget -qO- http://localhost:18802/api/health

# Check from host
curl http://localhost:18802/api/health | jq .
```

If the health endpoint returns a non-200, check:

```bash
# Logs since last restart
docker compose logs --since 5m nox-mem-api

# Is the API process running?
docker compose ps
```

### Port conflict

```bash
# Find what's using 18802
lsof -i :18802

# Change port in .env
echo "NOX_API_PORT=18803" >> .env
docker compose up -d
```

### Database corruption (WAL inconsistency)

```bash
# Stop the container
docker compose stop nox-mem-api

# Remove stale WAL/SHM files
rm -f data/nox-mem.db-wal data/nox-mem.db-shm

# Verify DB integrity
sqlite3 data/nox-mem.db "PRAGMA integrity_check;"

# Restart
docker compose start nox-mem-api
```

If `integrity_check` returns anything other than `ok`, restore from the latest backup.

### Embeddings not generating

```bash
# Check provider health inside container
docker compose exec nox-mem-api \
  node dist/index.js health --verbose

# Verify GEMINI_API_KEY is set correctly
docker compose exec nox-mem-api sh -c 'echo "Key prefix: ${GEMINI_API_KEY:0:8}..."'
```

Embeddings fail silently if `GEMINI_API_KEY` is wrong — the CLI prints `Done: 0 embedded, N errors`. Always verify via `/api/health`:

```bash
curl http://localhost:18802/api/health | jq '{embedded: .vectorCoverage.embedded, total: .vectorCoverage.total}'
```

### Viewing detailed logs

```bash
# Follow logs in real time
docker compose logs -f nox-mem-api

# Last 200 lines
docker compose logs --tail=200 nox-mem-api

# Since a specific time (ISO 8601)
docker compose logs --since "2026-05-18T12:00:00" nox-mem-api
```

---

## 10. Limitations

Docker is the right tool for **local development, evaluation, and single-user deployments**. It is not the recommended production path.

| Use case | Docker | VPS (DEPLOY-WAVE-B.md) |
|---|---|---|
| Local dev / first evaluation | Recommended | Overkill |
| Single-user, laptop-local | Fine | Overkill |
| Multi-user, shared server | Not designed for this | Recommended |
| Production VPS, TLS, systemd | Works with hardening (§8) | Recommended |
| nightly cron + watcher daemon | Requires compose orchestration | Native, simpler |
| Pre-op snapshots (`withOpAudit`) | Writes to `/data` — works | Full `/var/backups` path |

**Known Docker limitations:**

- `inotifywait`-based file watcher does not work with Docker bind mounts on macOS (FS events not propagated). Use `nox-mem ingest` manually, or run the watcher directly on the host.
- Port 18802 is bound to `127.0.0.1` by default — expose deliberately if you need external access, and set `NOX_VIEWER_AUTH_TOKEN`.
- The Gemini embedding provider requires outbound HTTPS. If your Docker setup uses a restrictive network policy, add `https://generativelanguage.googleapis.com` to the allowlist.
- SQLite WAL mode means you may see `.db-wal` and `.db-shm` files in `./data/` — this is normal and healthy.

For anything beyond single-user local use, follow `DEPLOY-WAVE-B.md`.
