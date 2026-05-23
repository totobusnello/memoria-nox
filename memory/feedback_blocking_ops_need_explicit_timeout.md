# Blocking ops need explicit timeout wrapper — run-sat-q4.sh hang lesson

**Timeline:** PR #295 (2026-05-24) — discovered `run-sat-q4.sh` preflight hangs indefinitely.

**Problem:** Q4 orchestrator script calls `docker info` at start to validate Docker daemon. On VPS with transient network issues or slow daemon:
```bash
# Original (HANGS)
docker info > /dev/null || { echo "Docker not ready"; exit 1; }
```

If Docker daemon is slow to respond or socket is unresponsive, `docker info` blocks **forever** (default is no timeout). Parent shell waits indefinitely. Cron job never completes. Operator assumes the job is running, but it's actually stalled.

**Symptom:** `ps aux | grep run-sat-q4` shows the process, but `tail -f <logfile>` shows no new output for >30min. Cron never sends completion email (job still "running").

**Solution (PR #295):** Wrap blocking ops with explicit `timeout N` wrapper:
```bash
# Fixed (FAILS FAST)
timeout 5 docker info > /dev/null || {
    echo "Docker not ready or timeout (5s)" >&2
    exit 1
}
```

Timeout value depends on expected latency:
- **Local CLI calls** (git, grep, echo): `timeout 2` (fallback quick)
- **Network I/O** (curl, ssh, docker): `timeout 10-30` (allow for RTT)
- **Long-running tasks** (build, vectorize): `timeout 300` (5min)

**Applied to run-sat-q4.sh (PR #295 checklist):**
- ✓ `docker info` — timeout 5
- ✓ `docker ps` — timeout 5
- ✓ `docker exec <container> test -f /path/to/corpus` — timeout 10
- ✓ HTTP health check (`curl /api/health`) — timeout 15

**Additional safeguards (PR #295):**
- Add `--skip-preflight` flag to allow manual override (e.g., if on machine without Docker)
- Add `--quiet` flag to suppress preflight logs in CI (reduce noise)
- Log each timeout as `WARN: preflight <op> timeout N (hung)` to audit trail

**Lesson generalized:** Any subprocess that talks to external system (network, daemon, filesystem) needs explicit timeout **before** calling. Prevents "stuck job" incidents. Standard pattern in production scripts.

**Reference:** PR #295. Pattern applies to all CI/cron scripts in memoria-nox.
