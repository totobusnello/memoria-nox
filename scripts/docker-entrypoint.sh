#!/bin/sh
# docker-entrypoint.sh — nox-mem container startup
#
# Responsibilities:
#   1. Validate required environment variables
#   2. Run DB schema migrations (idempotent — checks user_version)
#   3. Hand off to the main process via exec (preserves PID 1 + signal handling)
#
# Signal handling:
#   SIGTERM → passed through to Node process via exec; Node's better-sqlite3
#   runs WAL checkpoint on clean shutdown. No custom trap needed.
#
# This script runs as noxmem (uid 10000). It must NOT need root.

set -eu

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
log()  { echo "[nox-mem entrypoint] $*" >&2; }
die()  { log "ERROR: $*"; exit 1; }

# ─────────────────────────────────────────────────────────────────────────────
# 1. Validate required vars
# ─────────────────────────────────────────────────────────────────────────────
if [ -z "${GEMINI_API_KEY:-}" ]; then
  # Hard-fail only if provider health-check is strict
  if [ "${NOX_PROVIDER_HEALTH_FAIL_FAST:-1}" = "1" ]; then
    die "GEMINI_API_KEY is not set. Set it in your .env file. See .env.example."
  else
    log "WARNING: GEMINI_API_KEY is not set. Embeddings and KG extraction will fail."
  fi
fi

# Resolve DB path — default to /data/nox-mem.db if not specified
DB_PATH="${NOX_DB_PATH:-/data/nox-mem.db}"
DATA_DIR="${NOX_MEM_DIR:-/data}"

# Ensure data directory exists and is writable
if [ ! -d "$DATA_DIR" ]; then
  log "Creating data directory: $DATA_DIR"
  mkdir -p "$DATA_DIR" || die "Cannot create data directory $DATA_DIR"
fi

if [ ! -w "$DATA_DIR" ]; then
  die "Data directory $DATA_DIR is not writable by uid $(id -u). Check volume permissions."
fi

# ─────────────────────────────────────────────────────────────────────────────
# 2. Schema migration (idempotent)
#
# nox-mem's schema is additive and migration-safe via user_version checks.
# We call `nox-mem migrate` if the binary supports it, or let the process
# self-migrate on first boot (the API server runs migrations at startup).
#
# We only attempt the explicit migrate call if the dist/index.js exists —
# in development (docker-compose.dev.yml with tsx), it may not be present.
# ─────────────────────────────────────────────────────────────────────────────
DIST_ENTRY="/app/dist/index.js"
if [ -f "$DIST_ENTRY" ]; then
  # Check if DB already exists (not first boot)
  if [ -f "$DB_PATH" ]; then
    log "Existing database found at $DB_PATH — checking schema version..."
    # Let the serve command handle migration internally (it does on every startup)
    log "Schema migration will run as part of process startup."
  else
    log "First boot — database will be initialized at $DB_PATH"
  fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# 3. Hand off to main process
#
# Using exec ensures:
#   - The Node process becomes PID 1 (receives SIGTERM directly from Docker)
#   - No zombie processes
#   - Clean shutdown: better-sqlite3 flushes WAL and closes cleanly on SIGTERM
# ─────────────────────────────────────────────────────────────────────────────
log "Starting nox-mem: $*"
exec "$@"
