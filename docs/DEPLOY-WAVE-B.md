# DEPLOY-WAVE-B — VPS Deployment Guide for All Staged Patches

**Target VPS path:** `/root/.openclaw/workspace/tools/nox-mem/`
**Stack:** TypeScript · better-sqlite3 · FTS5 · sqlite-vec · Gemini 3072d
**Baseline schema:** v10 (`retention_days` + `pain` + `section`)
**Post-deploy schema:** v20

> Deploy Validator CI was fixed in `62be1f6` (2026-05-18) — see [INCIDENTS.md](INCIDENTS.md#2026-05-18-1623-brt-10min-fix--deploy-validator-ci-100-fail-por-stderrjson-contamination).

---

## TL;DR — Order of operations

```
Pre-flight → v11 migration → v19 migration → v20 migration
→ staged-privacy → staged-A3 → staged-P5a → staged-P1
→ staged-A2 → staged-L4 → staged-P5 → staged-P3
→ Post-deploy validation → Shadow-mode gates
```

Older patches (`staged-1.6/`, `staged-1.7a/`, `staged-1.8/`) target non-source
files (prompt text, heartbeat scripts, cron helpers) and are applied LAST,
after all source-tree changes are built and validated.

---

## Path Conventions

> **Never use worktree-absolute paths.** Worktree paths (`/Users/.../worktrees/agent-*/`)
> are local development artifacts and **do not exist on the VPS**. Using them in
> deployment commands silently fails when run on a different machine or CI.

| Context | Pattern | Example |
|---|---|---|
| Local repo paths (rsync source) | **Repo-relative** from repo root | `staged-P5/edits/migrations/v20-viewer-telemetry.sql` |
| VPS paths (rsync destination) | **VPS absolute** under nox-mem root | `/root/.openclaw/workspace/tools/nox-mem/staged-migrations/v20.sql` |
| VPS root shorthand | `${NM}` env var | `export NM=/root/.openclaw/workspace/tools/nox-mem` |

**Rule:** All `rsync` source paths in this guide are relative to the **repo root on
your local machine**. The `rsync` command must be run from the repo root, or paths
must be prefixed with `$(git rev-parse --show-toplevel)/`.

---

## 1. Pre-flight Checklist

Run EVERY item before touching any files.

```bash
# Set env first — required for all nox-mem CLI operations (CLAUDE.md regra #1)
set -a; source /root/.openclaw/.env; set +a

# 1a. Service health — must return HTTP 200
curl -sf http://127.0.0.1:18802/api/health | jq '{status: .status, total: .total, schemaVersion: .schemaVersion}'
# Expected: status "ok", schemaVersion 10 (pre-migration)

# 1b. Baseline chunk + KG counts (save for post-deploy delta check)
curl -sf http://127.0.0.1:18802/api/health | jq '{total, embedded, kg_entities, kg_relations}' | tee /tmp/baseline-counts.json

# 1c. Disk space — need > 5 GB free on backup volume
df -h /var/backups/nox-mem
# Abort if free < 5 GB: migrations create VACUUM INTO snapshots (~1× DB size each)

# 1d. Full pre-deploy backup via backup-all.sh
/root/.openclaw/workspace/tools/nox-mem/scripts/backup-all.sh
# Confirm backup created under /var/backups/nox-mem/

# 1e. Read DECISIONS.md D40+D41 to understand what shipped
#     (local read — no VPS command needed)

# 1f. Verify no end-of-day cron collision
#     The 22:00 BRT cron runs `nox-mem consolidate` (patched 2026-04-25).
#     Schedule this deployment window between 09:00–19:00 BRT.
crontab -l | grep -E "nox-mem|openclaw"
```

**STOP if any check fails.** Do not proceed past a failing pre-flight item.

---

## 2. Staged Patches Inventory

All `staged-*/edits/` directories are relative to the **repo root** on the local
machine. The VPS receives files via `rsync` — the local repo is the source of truth.

### 2.1 Schema patches (apply FIRST — all others depend on schema)

| Directory | PR | What it adds | VPS path |
|---|---|---|---|
| `staged-migrations/v11.sql` | #28 | `answer_telemetry` + `agent_events` + `provider_telemetry` tables | DB mutation — no src copy |
| `staged-migrations/v19.sql` | #28 | `chunks.confidence` + `chunks.provenance_kind` + `kg_relations` temporal cols | DB mutation — no src copy |
| `staged-P5/edits/migrations/v20-viewer-telemetry.sql` | #42 | `viewer_telemetry` table | DB mutation — no src copy |

**No new npm dependencies.** All tables use only built-in SQLite types.

### 2.2 Source patches (apply after schema)

| Directory | PRs | What it adds | Target VPS src path | New env vars |
|---|---|---|---|---|
| `staged-privacy/edits/privacy/` | — | Regex-based PII/secret redaction filter applied at ingest time | `src/privacy/` (new dir) | — |
| `staged-A3/edits/src/providers/` | #36, #39 | Provider abstraction — Gemini real + OpenAI/Anthropic/Voyage stubs + registry + boot health | `src/providers/` (new dir) | `NOX_EMBEDDING_PROVIDER` · `NOX_LLM_PROVIDER` (optional; default stays Gemini) |
| `staged-P5a/edits/src/lib/events/` | #33 | Internal EventEmitter bus — prerequisite for P5 SSE endpoint | `src/lib/events/` (new dir) | — |
| `staged-P1/edits/src/lib/answer/` | #18, #31, #34, #40 | Answer primitive — `answer()` function + CLI + HTTP + MCP tools + telemetry writes | `src/lib/answer/` · `src/api/answer.ts` · `src/cli/answer.ts` · `src/mcp/tools/answer.ts` | `NOX_ANSWER_MODEL` (default: `gemini-2.5-flash-lite`) · `NOX_ANSWER_MAX_CHUNKS` (default: 8) |
| `staged-A2/edits/src/lib/archive/` | #37, #41 | Encrypted export/import archive (AES-256-GCM, scrypt KDF) | `src/lib/archive/` (new dir) | `NOX_EXPORT_PASSPHRASE` (prompted interactively if unset) |
| `staged-L4/edits/src/lib/regex-extract/` | #35, #38 | Regex-first KG entity extraction with Gemini fallback | `src/lib/regex-extract/` (new dir) | `NOX_L4_REGEX_ENABLED=1` to activate (ships disabled) |
| `staged-P5/edits/src/` | #42 | Real-time viewer — SSE endpoint + static HTML/CSS/JS + viewer telemetry | `src/api/events-stream.ts` · `src/api/viewer-static.ts` · `src/viewer/` · `src/cli/viewer.ts` · `src/mcp/tools/viewer.ts` · `src/lib/viewer/` | `NOX_VIEWER_TOKEN` (random string, required for auth) |
| `staged-P3/edits/` | #2 | Temporal query filters `--as-of` / `--changed-since` across CLI + HTTP + MCP | `src/lib/dates.ts` · `src/search.ts` · `src/index.ts` · `src/api-server.ts` · `src/mcp-search-tool.ts` | — |

### 2.3 Non-source patches (apply LAST, after build validates)

| Directory | What it contains | Target VPS path |
|---|---|---|
| `staged-1.6/edits/` | `search.ts` + `db.ts` + `api-server.ts` patches (dedup + query expansion) | `src/` — merge with P3 edits |
| `staged-1.7a/edits/` | `db.ts`, `search.ts`, `kg-llm.ts`, `generate-user-profile.ts`, `index.ts` | `src/` — already superseded by P3; apply only if diff shows unique content |
| `staged-1.8/scripts/` | Cron helpers: `cipher-weekly-audit.sh`, `heartbeat-sync.sh`, `weather-sp.sh` | `/root/.openclaw/workspace/scripts/` |
| `staged-1.8/*.txt` | Prompt templates: `cipher-weekly-prompt.txt`, `daily-briefing-prompt.txt` | `/root/.openclaw/workspace/prompts/` |
| `staged-graphify-ingest/graphify-ingest.ts` | graphify ingest pipeline helper | `src/` or standalone script |

**Note on 1.6 / 1.7a overlap:** `staged-P3/edits/search.ts` supersedes the 1.7a
`search.ts` delta. Before applying 1.6/1.7a, run `diff` against the P3-patched file
and apply only the non-overlapping hunks.

---

## 3. Deployment Order — Dependency DAG

```
Step 1  ── Schema v11        (telemetry foundation)
Step 2  ── Schema v19        (confidence + provenance; requires v11)
Step 3  ── Schema v20        (viewer_telemetry; requires v19)
Step 4  ── staged-privacy    (additive new dir; no DB dep)
Step 5  ── staged-A3         (additive new dir; no DB dep)
Step 6  ── staged-P5a        (additive new dir; no DB dep)
Step 7  ── staged-P1         (depends on A3 for provider; writes answer_telemetry → v11)
Step 8  ── staged-A2         (additive new dir; reads v19 cols for serializers)
Step 9  ── staged-L4         (additive new dir; writes kg_relations.extraction_method → v19)
Step 10 ── staged-P5         (depends on P5a bus; writes viewer_telemetry → v20)
Step 11 ── staged-P3         (patches search.ts/api-server.ts/index.ts/mcp — must be last src change before final build)
Step 12 ── staged-1.6/1.7a   (non-critical historical patches; diff + apply or skip)
Step 13 ── staged-1.8        (scripts + prompts — no build required)
Step 14 ── Final build + restart + validation
```

---

## 4. Step-by-Step Deployment Commands

> **Convention:** `$VPS_HOST` is the VPS address (e.g. `export VPS_HOST=root@<your-vps-ip>`).
> All commands run from the **repo root on your local machine** unless noted.

```bash
export VPS_HOST=root@<vps>
export NM=/root/.openclaw/workspace/tools/nox-mem
```

### Step 1 — Schema v11

```bash
# 1a. Backup before first mutation (withOpAudit creates snapshot automatically when called
#     from code; for CLI sqlite3 path we take a manual snapshot here)
ssh $VPS_HOST "
  set -euo pipefail
  SNAP_V11=/var/backups/nox-mem/pre-op/migrate_v11-$(date +%Y%m%d-%H%M%S).db
  sqlite3 ${NM}/nox-mem.db \"VACUUM INTO '${SNAP_V11}'\"
  chmod 0600 \"${SNAP_V11}\"
  echo \"Snapshot: ${SNAP_V11}\"
"

# 1b. Verify pre-migration version
ssh $VPS_HOST "sqlite3 ${NM}/nox-mem.db 'PRAGMA user_version;'"
# Must return 10

# 1c. Copy migration file
rsync -avz staged-migrations/v11.sql $VPS_HOST:${NM}/staged-migrations/v11.sql

# 1d. Apply migration
ssh $VPS_HOST "sqlite3 ${NM}/nox-mem.db < ${NM}/staged-migrations/v11.sql"

# 1e. Verify
ssh $VPS_HOST "sqlite3 ${NM}/nox-mem.db 'PRAGMA user_version;'"
# Must return 11

# 1f. Run validation tests
rsync -avz staged-migrations/v11-tests.sql $VPS_HOST:${NM}/staged-migrations/v11-tests.sql
ssh $VPS_HOST "sqlite3 ${NM}/nox-mem.db < ${NM}/staged-migrations/v11-tests.sql"
# Every line must start with PASS:
```

### Step 2 — Schema v19

```bash
# 2a. Backup before v19
ssh $VPS_HOST "
  set -euo pipefail
  SNAP_V19=/var/backups/nox-mem/pre-op/migrate_v19-$(date +%Y%m%d-%H%M%S).db
  sqlite3 ${NM}/nox-mem.db \"VACUUM INTO '${SNAP_V19}'\"
  chmod 0600 \"${SNAP_V19}\"
  echo \"Snapshot: ${SNAP_V19}\"
"

# 2b. Verify pre-migration version
ssh $VPS_HOST "sqlite3 ${NM}/nox-mem.db 'PRAGMA user_version;'"
# Must return 11

# 2c. Copy + apply
rsync -avz staged-migrations/v19.sql $VPS_HOST:${NM}/staged-migrations/v19.sql
ssh $VPS_HOST "sqlite3 ${NM}/nox-mem.db < ${NM}/staged-migrations/v19.sql"

# 2d. Verify version jump (11 → 19; versions 12-18 reserved per migrations/README.md)
ssh $VPS_HOST "sqlite3 ${NM}/nox-mem.db 'PRAGMA user_version;'"
# Must return 19

# 2e. Run validation tests
rsync -avz staged-migrations/v19-tests.sql $VPS_HOST:${NM}/staged-migrations/v19-tests.sql
ssh $VPS_HOST "sqlite3 ${NM}/nox-mem.db < ${NM}/staged-migrations/v19-tests.sql"
# Every line must start with PASS:

# 2f. Confirm sectionDistribution.compiled == 183 (v19 must not disturb entity chunks)
curl -sf http://127.0.0.1:18802/api/health | jq '.sectionDistribution.compiled'
```

### Step 3 — Schema v20 (viewer_telemetry)

```bash
# 3a. Backup before v20
ssh $VPS_HOST "
  set -euo pipefail
  SNAP_V20=/var/backups/nox-mem/pre-op/migrate_v20-$(date +%Y%m%d-%H%M%S).db
  sqlite3 ${NM}/nox-mem.db \"VACUUM INTO '${SNAP_V20}'\"
  chmod 0600 \"${SNAP_V20}\"
  echo \"Snapshot: ${SNAP_V20}\"
"

# 3b. Verify pre-migration version
ssh $VPS_HOST "sqlite3 ${NM}/nox-mem.db 'PRAGMA user_version;'"
# Must return 19

# 3c. Copy + apply (run from repo root)
rsync -avz \
  staged-P5/edits/migrations/v20-viewer-telemetry.sql \
  $VPS_HOST:${NM}/staged-migrations/v20-viewer-telemetry.sql
ssh $VPS_HOST "sqlite3 ${NM}/nox-mem.db < ${NM}/staged-migrations/v20-viewer-telemetry.sql"

# 3d. Verify
ssh $VPS_HOST "sqlite3 ${NM}/nox-mem.db 'PRAGMA user_version;'"
# Must return 20

ssh $VPS_HOST "sqlite3 ${NM}/nox-mem.db \"SELECT name FROM sqlite_master WHERE type='table' AND name='viewer_telemetry';\""
# Must return: viewer_telemetry
```

### Step 4 — Privacy filter (staged-privacy)

```bash
# 4a. Backup src before first code change
ssh $VPS_HOST "cp -r ${NM}/src /tmp/src.bak-pre-privacy-$(date +%Y%m%d-%H%M%S)"

# 4b. Dry-run rsync to preview changes
rsync -avz --dry-run staged-privacy/edits/privacy/ $VPS_HOST:${NM}/src/privacy/

# 4c. Apply
rsync -avz staged-privacy/edits/privacy/ $VPS_HOST:${NM}/src/privacy/

# 4d. Apply ingest-router.ts patch manually
#     (staged-privacy/edits/ingest-router.patch.md describes the two code injection points)
#     Edit ${NM}/src/lib/ingest-router.ts on VPS:
#       - Add `import { redact } from "../privacy/filter.js";` at top
#       - In ingestFile(): wrap rawChunkText with redact() before INSERT
#       - In ingestEntityFile(): wrap each section string before split
#     CRITICAL: do not use sed — edit the TypeScript file with your editor over ssh/scp

# 4e. Verify false-positive rate before build (run against entity corpus)
ssh $VPS_HOST "
  set -a; source /root/.openclaw/.env; set +a
  cd ${NM}
  # Quick manual false-positive check on a sample file
  echo 'salience formula recency pain importance' | node -e \"
    const {redact} = require('./dist/privacy/filter.js');
    const chunks = require('fs').readFileSync('/dev/stdin','utf8');
    const {redactionCount} = redact(chunks);
    console.log('redactionCount:', redactionCount, '(expect 0 for legitimate content)');
  \"
" 2>/dev/null || echo "Check after build in Step 14"
```

### Step 5 — Provider abstraction (staged-A3)

```bash
# 5a. Backup note: src backup already taken in Step 4 (cumulative — no new backup needed
#     for additive-only patches that don't modify existing files)

# 5b. Dry-run
rsync -avz --dry-run staged-A3/edits/src/providers/ $VPS_HOST:${NM}/src/providers/

# 5c. Apply (additive new directory — zero existing file changes)
rsync -avz staged-A3/edits/src/providers/ $VPS_HOST:${NM}/src/providers/

# 5d. No env changes required at this step — Gemini default stays via existing
#     GEMINI_API_KEY in .env. NOX_EMBEDDING_PROVIDER / NOX_LLM_PROVIDER are
#     optional overrides; omitting them keeps Gemini default per D41.
```

### Step 6 — Event bus (staged-P5a)

```bash
# 6a. Dry-run
rsync -avz --dry-run staged-P5a/edits/src/lib/events/ $VPS_HOST:${NM}/src/lib/events/

# 6b. Apply (additive new directory)
rsync -avz staged-P5a/edits/src/lib/events/ $VPS_HOST:${NM}/src/lib/events/

# 6c. Wire integration points into existing modules
#     See staged-P5a/README.md §Integration Points for exact code snippets.
#     Files to patch on VPS:
#       src/lib/ingest-router.ts  → emit chunk.created after insert
#       src/lib/db.ts             → emit chunk.deleted after DELETE
#       src/commands/kg-extract.ts → emit kg.entity.created + kg.relation.created
#       src/lib/search.ts         → emit search.executed after RRF
#       src/lib/op-audit.ts       → emit op_audit.started + op_audit.completed
```

### Step 7 — Answer primitive (staged-P1)

```bash
# 7a. Backup src before P1 (modifies api-server.ts + index.ts + mcp server)
ssh $VPS_HOST "cp -r ${NM}/src /tmp/src.bak-pre-p1-$(date +%Y%m%d-%H%M%S)"

# 7b. Dry-run for each P1 target
rsync -avz --dry-run staged-P1/edits/src/lib/answer/ $VPS_HOST:${NM}/src/lib/answer/
rsync -avz --dry-run staged-P1/edits/src/api/answer.ts $VPS_HOST:${NM}/src/api/answer.ts
rsync -avz --dry-run staged-P1/edits/src/cli/answer.ts $VPS_HOST:${NM}/src/cli/answer.ts
rsync -avz --dry-run staged-P1/edits/src/mcp/tools/answer.ts $VPS_HOST:${NM}/src/mcp/tools/answer.ts

# 7c. Apply
rsync -avz staged-P1/edits/src/lib/answer/ $VPS_HOST:${NM}/src/lib/answer/
rsync -avz staged-P1/edits/src/api/answer.ts $VPS_HOST:${NM}/src/api/answer.ts
rsync -avz staged-P1/edits/src/cli/answer.ts $VPS_HOST:${NM}/src/cli/answer.ts
rsync -avz staged-P1/edits/src/mcp/tools/answer.ts $VPS_HOST:${NM}/src/mcp/tools/answer.ts

# 7d. Wire real providers (replace placeholder stubs in answer/provider.ts)
#     After A3 is in place, update src/lib/answer/provider.ts to import from
#     src/providers/llm/gemini.ts instead of the MockProvider placeholder.
#     See staged-P1/edits/README.md §How to apply step 3 for the exact binding.

# 7e. Env var check — P1 uses defaults from config.ts; no new vars required
#     unless overriding model: NOX_ANSWER_MODEL defaults to gemini-2.5-flash-lite (D41 locked)
ssh $VPS_HOST "grep -E 'NOX_ANSWER' /root/.openclaw/.env || echo 'no P1 overrides — using defaults'"
```

### Step 8 — Archive primitives (staged-A2)

```bash
# 8a. Dry-run (additive new directory — no existing file changes)
rsync -avz --dry-run staged-A2/edits/src/lib/archive/ $VPS_HOST:${NM}/src/lib/archive/

# 8b. Apply
rsync -avz staged-A2/edits/src/lib/archive/ $VPS_HOST:${NM}/src/lib/archive/

# 8c. NOX_EXPORT_PASSPHRASE env var
#     A2 encryption uses AES-256-GCM + scrypt. Passphrase is read from env or
#     interactive stdin — never from argv. Add to .env if you want non-interactive export:
ssh $VPS_HOST "grep -q 'NOX_EXPORT_PASSPHRASE' /root/.openclaw/.env && echo 'already set' || echo 'Add NOX_EXPORT_PASSPHRASE=<strong-passphrase> to /root/.openclaw/.env'"
#     IMPORTANT: use a strong, unique passphrase — this key encrypts all exported memory.
#     The passphrase is never stored in the DB or logs.
```

### Step 9 — Regex-first KG extraction (staged-L4)

```bash
# 9a. Dry-run (additive new directory)
rsync -avz --dry-run staged-L4/edits/src/lib/regex-extract/ $VPS_HOST:${NM}/src/lib/regex-extract/

# 9b. Apply
rsync -avz staged-L4/edits/src/lib/regex-extract/ $VPS_HOST:${NM}/src/lib/regex-extract/

# 9c. L4 ships DISABLED by default (CLAUDE.md regra #5 — shadow-mode first)
#     Do NOT set NOX_L4_REGEX_ENABLED=1 at deploy time.
#     The env var gate will be enabled after 7-day shadow baseline (see §8).
ssh $VPS_HOST "grep -q 'NOX_L4_REGEX_ENABLED' /root/.openclaw/.env && echo 'WARNING: L4 already enabled — should be shadow only' || echo 'OK: L4 disabled (default)'"
```

### Step 10 — Real-time viewer (staged-P5)

```bash
# 10a. Backup src before P5 (touches api-server.ts integration)
ssh $VPS_HOST "cp -r ${NM}/src /tmp/src.bak-pre-p5-$(date +%Y%m%d-%H%M%S)"

# 10b. Dry-run (run from repo root)
rsync -avz --dry-run \
  staged-P5/edits/src/ \
  $VPS_HOST:${NM}/src/

# 10c. Apply (run from repo root)
rsync -avz \
  staged-P5/edits/src/ \
  $VPS_HOST:${NM}/src/

# 10d. NOX_VIEWER_TOKEN — required for SSE auth
#      Generate a random token and add to .env:
VIEWER_TOKEN=$(openssl rand -hex 32)
echo "NOX_VIEWER_TOKEN=${VIEWER_TOKEN}"
# Then: ssh $VPS_HOST "echo 'NOX_VIEWER_TOKEN=${VIEWER_TOKEN}' >> /root/.openclaw/.env"
# (or edit .env manually on VPS — never echo a secret to shell history without care)
```

### Step 11 — Temporal queries (staged-P3)

```bash
# 11a. Backup src — P3 modifies 5 existing files
ssh $VPS_HOST "cp -r ${NM}/src /tmp/src.bak-pre-p3-$(date +%Y%m%d-%H%M%S)"

# 11b. Dry-run for each P3 target
rsync -avz --dry-run staged-P3/edits/dates.ts $VPS_HOST:${NM}/src/lib/dates.ts
rsync -avz --dry-run staged-P3/edits/search.ts $VPS_HOST:${NM}/src/search.ts
rsync -avz --dry-run staged-P3/edits/index.ts $VPS_HOST:${NM}/src/index.ts
rsync -avz --dry-run staged-P3/edits/api-server.ts $VPS_HOST:${NM}/src/api-server.ts
rsync -avz --dry-run staged-P3/edits/mcp-search-tool.ts $VPS_HOST:${NM}/src/mcp-search-tool.ts
rsync -avz --dry-run staged-P3/tests/temporal.test.ts $VPS_HOST:${NM}/src/lib/search/__tests__/temporal.test.ts

# 11c. Review dry-run output carefully — these replace existing files
#      Verify no conflicts with 1.6/1.7a search.ts changes (diff if needed):
# diff staged-P3/edits/search.ts staged-1.7a/edits/search.ts

# 11d. Apply
rsync -avz staged-P3/edits/dates.ts $VPS_HOST:${NM}/src/lib/dates.ts
rsync -avz staged-P3/edits/search.ts $VPS_HOST:${NM}/src/search.ts
rsync -avz staged-P3/edits/index.ts $VPS_HOST:${NM}/src/index.ts
rsync -avz staged-P3/edits/api-server.ts $VPS_HOST:${NM}/src/api-server.ts
rsync -avz staged-P3/edits/mcp-search-tool.ts $VPS_HOST:${NM}/src/mcp-search-tool.ts
rsync -avz staged-P3/tests/temporal.test.ts $VPS_HOST:${NM}/src/lib/search/__tests__/temporal.test.ts
```

### Step 12 — Historical patches (staged-1.6, staged-1.7a)

```bash
# 1.6 and 1.7a predate the overnight work and are partially superseded by P3.
# BEFORE applying, diff each file against the P3-patched version:

# Example for search.ts:
diff staged-1.7a/edits/search.ts staged-P3/edits/search.ts
# If the 1.7a patch adds unique hunks not in P3, apply those manually.
# If P3 fully supersedes, skip the 1.7a file.

# Procedure for each file in staged-1.6/edits/ and staged-1.7a/edits/:
# 1. diff against current VPS version (after P3 applied)
# 2. Apply only non-overlapping unique hunks
# 3. Rebuild after each set of changes

# Shortcut: if you are confident P3 is the superset for search.ts/api-server.ts/index.ts,
# the only 1.7a file you may still need is generate-user-profile.ts (not touched by P3):
rsync -avz --dry-run staged-1.7a/edits/generate-user-profile.ts $VPS_HOST:${NM}/src/generate-user-profile.ts
```

### Step 13 — Cron scripts + prompts (staged-1.8)

```bash
# 13a. Scripts to /root/.openclaw/workspace/scripts/
rsync -avz staged-1.8/scripts/cipher-weekly-audit.sh $VPS_HOST:/root/.openclaw/workspace/scripts/
rsync -avz staged-1.8/scripts/heartbeat-sync.sh $VPS_HOST:/root/.openclaw/workspace/scripts/
rsync -avz staged-1.8/scripts/weather-sp.sh $VPS_HOST:/root/.openclaw/workspace/scripts/
ssh $VPS_HOST "chmod +x /root/.openclaw/workspace/scripts/cipher-weekly-audit.sh \
                         /root/.openclaw/workspace/scripts/heartbeat-sync.sh \
                         /root/.openclaw/workspace/scripts/weather-sp.sh"

# 13b. Prompt templates to /root/.openclaw/workspace/prompts/
ssh $VPS_HOST "mkdir -p /root/.openclaw/workspace/prompts"
rsync -avz staged-1.8/cipher-weekly-prompt.txt $VPS_HOST:/root/.openclaw/workspace/prompts/
rsync -avz staged-1.8/daily-briefing-prompt.txt $VPS_HOST:/root/.openclaw/workspace/prompts/

# 13c. No build required — pure text files
```

### Step 14 — Build, restart, and validate

```bash
# 14a. Build
ssh $VPS_HOST "
  set -euo pipefail
  set -a; source /root/.openclaw/.env; set +a
  cd ${NM}
  npm run build 2>&1 | tail -20
"
# Watch for TypeScript errors. Fix before proceeding.

# 14b. Restart nox-mem-api systemd service
ssh $VPS_HOST "systemctl restart nox-mem-api && sleep 3"

# 14c. Confirm service came back up
ssh $VPS_HOST "systemctl is-active nox-mem-api"
# Must return: active

# 14d. Health check
ssh $VPS_HOST "curl -sf http://127.0.0.1:18802/api/health | jq '{status, total, embedded, schemaVersion}'"
# Expected: status "ok", schemaVersion 20

# 14e. Delta check — chunk count should not drop (may increase if reindex ran)
ssh $VPS_HOST "curl -sf http://127.0.0.1:18802/api/health | jq '{total, embedded, kg_entities, kg_relations}'"
# Compare against /tmp/baseline-counts.json from pre-flight step 1b
```

---

## 5. Schema Migration Commands Reference

Consolidated reference for all three migrations.

```bash
# ── Pre-migration state check ─────────────────────────────────────────────
ssh $VPS_HOST "sqlite3 ${NM}/nox-mem.db 'PRAGMA user_version;'"

# ── v11: telemetry tables ─────────────────────────────────────────────────
# Precondition: user_version = 10
# Creates: answer_telemetry, agent_events, provider_telemetry (3 tables, 7 indexes)
ssh $VPS_HOST "sqlite3 ${NM}/nox-mem.db < ${NM}/staged-migrations/v11.sql"
ssh $VPS_HOST "sqlite3 ${NM}/nox-mem.db 'PRAGMA user_version;'"  # → 11
ssh $VPS_HOST "sqlite3 ${NM}/nox-mem.db < ${NM}/staged-migrations/v11-tests.sql"

# ── v19: confidence + provenance + temporal ───────────────────────────────
# Precondition: user_version = 11
# Adds columns to chunks (2) and kg_relations (6), plus 3 new indexes
ssh $VPS_HOST "sqlite3 ${NM}/nox-mem.db < ${NM}/staged-migrations/v19.sql"
ssh $VPS_HOST "sqlite3 ${NM}/nox-mem.db 'PRAGMA user_version;'"  # → 19
ssh $VPS_HOST "sqlite3 ${NM}/nox-mem.db < ${NM}/staged-migrations/v19-tests.sql"

# ── v20: viewer_telemetry ─────────────────────────────────────────────────
# Precondition: user_version = 19
# Creates: viewer_telemetry (1 table, 3 indexes)
ssh $VPS_HOST "sqlite3 ${NM}/nox-mem.db < ${NM}/staged-migrations/v20-viewer-telemetry.sql"
ssh $VPS_HOST "sqlite3 ${NM}/nox-mem.db 'PRAGMA user_version;'"  # → 20

# ── Idempotency ───────────────────────────────────────────────────────────
# v11: uses CREATE TABLE IF NOT EXISTS — safe to re-run (no-op on re-run)
# v19: uses ALTER TABLE ADD COLUMN — NOT idempotent; running twice errors on duplicate column
#      check user_version before running: skip if already >= 19
# v20: uses CREATE TABLE IF NOT EXISTS — safe to re-run
```

**Version chain:**

```
v10 (baseline: retention_days + pain + section)
 │
v11 — telemetry tables
 │
v19 — confidence + provenance + temporal (versions 12-18 reserved for other sprints)
 │
v20 — viewer_telemetry
```

---

## 6. Post-Deploy Validation

Run all commands **on the VPS** via ssh, or locally if you have a tunnel to :18802.

```bash
# Set env first
set -a; source /root/.openclaw/.env; set +a

# ── 6a. Health endpoint ───────────────────────────────────────────────────
curl -sf http://127.0.0.1:18802/api/health | jq '{
  status,
  total,
  embedded,
  schemaVersion,
  sectionDistribution,
  vectorCoverage
}'
# Expected:
#   status: "ok"
#   schemaVersion: 20
#   sectionDistribution.compiled: 183  (unchanged from baseline)
#   vectorCoverage: embedded == total  (CLAUDE.md regra #2)

# ── 6b. Answer primitive ─────────────────────────────────────────────────
curl -sf http://127.0.0.1:18802/api/answer \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"question": "What is salience in nox-mem?"}' | jq '{answer: .answer[:100], model: .metadata.model, citations: (.citations | length)}'
# Expected: answer not empty, metadata.model = "gemini-2.5-flash-lite" (D41 #1 locked)

# ── 6c. SSE stream (P5) ───────────────────────────────────────────────────
# Requires NOX_VIEWER_TOKEN set in .env
curl -sf -N \
  -H "Authorization: Bearer ${NOX_VIEWER_TOKEN}" \
  http://127.0.0.1:18802/api/events/stream &
SSE_PID=$!
sleep 2
# Trigger a search to generate events:
curl -sf "http://127.0.0.1:18802/api/search?q=salience&limit=3" > /dev/null
sleep 1
kill $SSE_PID
# Expected: SSE connection hung open + at least 1 "event: search.executed" line printed

# ── 6d. Archive export/import (A2) ───────────────────────────────────────
export NOX_EXPORT_PASSPHRASE=smoke-test-passphrase-$(date +%s)
nox-mem export --out /tmp/test-export.tgz
# Expected: /tmp/test-export.tgz created, encrypted

nox-mem import /tmp/test-export.tgz --dry-run
# Expected: manifest parsed, counts match, no errors, nothing written
rm -f /tmp/test-export.tgz
unset NOX_EXPORT_PASSPHRASE

# ── 6e. Temporal queries (P3) ────────────────────────────────────────────
curl -sf "http://127.0.0.1:18802/api/search?q=salience&as_of=2026-05-01" | jq '.results | length'
curl -sf "http://127.0.0.1:18802/api/search?q=salience&changed_since=30d" | jq '.results | length'
# Both must return numeric values (0 is valid if no matching chunks in range)

nox-mem search "deployment decisions" --as-of 2026-04-01
nox-mem search "schema migration" --changed-since 30d
# Must not error; result count may be 0

# ── 6f. Telemetry tables populated ───────────────────────────────────────
sqlite3 ${NM}/nox-mem.db "SELECT COUNT(*) FROM answer_telemetry;"
# > 0 after at least one /api/answer call

sqlite3 ${NM}/nox-mem.db "SELECT COUNT(*) FROM provider_telemetry;"
# > 0 after answer call (writes one row per Gemini call)

sqlite3 ${NM}/nox-mem.db "SELECT COUNT(*) FROM viewer_telemetry;"
# > 0 after at least one SSE connection opened

sqlite3 ${NM}/nox-mem.db "SELECT COUNT(*) FROM agent_events;"
# May still be 0 — agent_events requires P2 hooks to be wired (P2 merge pending)

# ── 6g. Privacy filter smoke test ────────────────────────────────────────
echo "ANTHROPIC_API_KEY=sk-ant-test-EXAMPLEKEY1234567890abcdefghij" > /tmp/test-secret.md
nox-mem ingest /tmp/test-secret.md
nox-mem search "sk-ant-test"
# Must return no matches (key should be redacted in stored chunk)

sqlite3 ${NM}/nox-mem.db \
  "SELECT chunk_text FROM chunks WHERE source_file LIKE '%test-secret%' ORDER BY id DESC LIMIT 1;"
# Must NOT contain "sk-ant-test" — expect [REDACTED:anthropic-key] or similar
rm /tmp/test-secret.md

# ── 6h. Provider health (A3) ─────────────────────────────────────────────
node -e "
  import('./dist/src/providers/index.js').then(async (m) => {
    const e = m.selectEmbeddingProvider();
    const l = m.selectLLMProvider();
    const r = await m.bootProviderHealth({ embedding: e, llm: l, failFast: false });
    console.log(JSON.stringify(r, null, 2));
  });
"
# Expected: allOk: true, both providers latencyMs < 500ms
```

---

## 7. Rollback Plan

Each phase has an explicit pre-op snapshot. Use the closest snapshot to the failing step.

### Source rollback (any code step 4–13)

```bash
# Replace src/ with the backup taken before the failing step
# Example: rolling back after a P1 failure
ssh $VPS_HOST "
  set -euo pipefail
  BAK=/tmp/src.bak-pre-p1-<timestamp>   # replace with actual timestamp from Step 7a
  rm -rf ${NM}/src
  cp -r \${BAK} ${NM}/src
"

# Rebuild + restart
ssh $VPS_HOST "
  set -euo pipefail
  set -a; source /root/.openclaw/.env; set +a
  cd ${NM}
  npm run build
  systemctl restart nox-mem-api
  sleep 3
  curl -sf http://127.0.0.1:18802/api/health | jq .status
"
```

### Schema rollback (v11 only — v19/v20 are forward-only)

```bash
# v11 rollback is supported (drops telemetry tables, no existing data touched)
rsync -avz staged-migrations/v11-rollback.sql $VPS_HOST:${NM}/staged-migrations/v11-rollback.sql
ssh $VPS_HOST "sqlite3 ${NM}/nox-mem.db < ${NM}/staged-migrations/v11-rollback.sql"
ssh $VPS_HOST "sqlite3 ${NM}/nox-mem.db 'PRAGMA user_version;'"  # → 10

# v19 rollback — NOT recommended in production (ALTER TABLE DROP COLUMN unreliable
# with CHECK constraints). Preferred path:
#   1. Restore from pre-v19 snapshot using safeRestore() — NEVER cp directly (stale WAL risk)
#   2. OR disable L2/L3/L4 feature code in source while keeping schema columns in place

# v20 rollback — same as v19: restore from pre-v20 snapshot if truly needed
```

### Using safeRestore() for schema rollback

```bash
# safeRestore() is in src/lib/op-audit.ts — use it for any snapshot restoration:
ssh $VPS_HOST "
  set -a; source /root/.openclaw/.env; set +a
  cd ${NM}
  node -e \"
    import('./dist/src/lib/op-audit.js').then(async (m) => {
      await m.safeRestore('/var/backups/nox-mem/pre-op/migrate_v19-<timestamp>.db');
      console.log('restore complete');
    });
  \"
"
# NEVER: cp /var/backups/.../snapshot.db ${NM}/nox-mem.db  — corrupts if WAL is stale
```

### Validation after rollback

```bash
ssh $VPS_HOST "curl -sf http://127.0.0.1:18802/api/health | jq '{status, total, schemaVersion}'"
# Compare total against /tmp/baseline-counts.json — must be >= baseline
```

---

## 8. Shadow-Mode Features

Per CLAUDE.md regra #5: **never activate a ranking or extraction change without 7-day
shadow baseline.** The following features ship in shadow mode and must NOT be activated
at deploy time.

### 8.1 L4 Regex-first KG extraction

**Env var:** `NOX_L4_REGEX_ENABLED`
**Default at deploy:** unset (feature disabled)
**Shadow → Active protocol:**

```bash
# Day 0 — deploy (do NOT set this var)
# Day 0–7 — monitor kg_relations.extraction_method distribution:
sqlite3 ${NM}/nox-mem.db "
  SELECT extraction_method, COUNT(*) as n
  FROM kg_relations
  GROUP BY extraction_method
  ORDER BY n DESC;
"
# Watch for extraction_method = 'regex_only' or 'regex_primary_gemini_secondary'
# growing as new chunks are ingested. If distribution is healthy after 7 days:

# Day 7+ — activate
ssh $VPS_HOST "echo 'NOX_L4_REGEX_ENABLED=1' >> /root/.openclaw/.env"
systemctl restart nox-mem-api
```

### 8.2 Salience formula (already in shadow-mode, pre-existing)

**Env var:** `NOX_SALIENCE_MODE`
**Default:** `shadow` (set in .env since Fase 1.7b-b)
**Shadow → Active protocol:**

```bash
# Check current baseline via health endpoint:
curl -sf http://127.0.0.1:18802/api/health | jq .salience
# When 7+ days of shadow telemetry show no regression in retrieval quality:
ssh $VPS_HOST "sed -i 's/NOX_SALIENCE_MODE=shadow/NOX_SALIENCE_MODE=active/' /root/.openclaw/.env"
# Wait — sed is forbidden on .db but .env is a text file (allowed)
systemctl restart nox-mem-api
```

### 8.3 L2 Conflict detection (Wave C — not yet shipped)

**Env var:** `NOX_CONFLICT_MODE`
**Values:** `shadow` | `active`
**Default at ship:** `shadow`
**Activation:** after 7-day baseline on `kg_relations.superseded_by_relation_id` growth rate.

### 8.4 L3 Confidence field (Wave C — not yet shipped)

**Env var:** `NOX_CONFIDENCE_SCORING`
**Values:** `shadow` | `active`
**Default at ship:** `shadow`
**Activation:** after 7-day baseline on `chunks.confidence` distribution.

---

## 9. Common Pitfalls

### 9.1 Missing env source — silent failure

```bash
# WRONG — vectorize / kg-extract / answer will fail silently:
nox-mem vectorize

# CORRECT — always set env first (CLAUDE.md regra #1):
set -a; source /root/.openclaw/.env; set +a
nox-mem vectorize
```

### 9.2 Wrong port

```bash
# WRONG — Chrome squats :18800:
curl http://127.0.0.1:18800/api/health

# CORRECT — nox-mem-api listens on :18802 (CLAUDE.md regra #4):
curl http://127.0.0.1:18802/api/health
```

### 9.3 Never `npm install -g openclaw` on this stack

Running `npm install -g openclaw` resets `baseUrl` and reactivates RelayPlane in
`openclaw.json` (memory: `npm-install-g-openclaw-resets-baseurl`). This is unrelated
to nox-mem but runs on the same VPS. Avoid during this deployment window.

### 9.4 Never `sed -i` on `.db` files

`sed -i` on a SQLite `.db` file corrupts page boundaries (memory: `never-sed-binary-files`).
Only apply sed to text files: `.json`, `.md`, `.sh`, `.txt`, `.jsonl`, `.env`.
For `.db` modifications, always use `sqlite3` CLI or the nox-mem TypeScript API.

### 9.5 Verify production state, not just code

After deploy, always query the DB directly to confirm new tables/columns exist
and counts match — do not trust build success alone (memory: `audit-must-check-prod-state`).

### 9.6 Schema v19 is NOT idempotent

`ALTER TABLE ADD COLUMN` fails if the column already exists. Check `PRAGMA user_version`
before running v19.sql. If already >= 19, skip this migration.

```bash
ssh $VPS_HOST "sqlite3 ${NM}/nox-mem.db 'PRAGMA user_version;'"
# Run v19.sql ONLY if this returns exactly 11
```

### 9.7 ops_audit rows — never DELETE or UPDATE terminal rows

The `ops_audit` table is append-only with DB triggers (CWE-693). Valid status values
are `started`, `success`, `failed`, `crashed`. Do not attempt `UPDATE` on rows with
terminal status (`success`/`failed`/`crashed`) — the trigger will block it.

### 9.8 Do not trust sub-agent diagnostic findings without verification

SSH into the VPS and check `/api/health` + DB state directly before acting on any
automated diagnostic report (memory: `subagent-findings-validate-critical`).

### 9.9 Build errors from ESM static imports

If TypeScript build succeeds but runtime fails with `cannot find module` or env-dependent
failures, check for module-level `const FOO = process.env.X` captures in new files
(memory: `esm-static-import-hoisting`). New modules should use dynamic `await import()`
or lazy getters for env-dependent config.

---

## 10. Env Variables Reference

Consolidated list of all new env vars introduced by Wave B patches.

| Variable | Module | Default | Description |
|---|---|---|---|
| `NOX_ANSWER_MODEL` | P1 | `gemini-2.5-flash-lite` | LLM model for answer primitive. D41 #1 — do not override to `gemini-2.5-flash` (quota). |
| `NOX_ANSWER_MAX_CHUNKS` | P1 | `8` | Max retrieval chunks passed to LLM for answer. |
| `NOX_EMBEDDING_PROVIDER` | A3 | `gemini` | Embedding provider. Valid: `gemini` (only real impl; others are stubs). |
| `NOX_LLM_PROVIDER` | A3 | `gemini` | LLM provider. Valid: `gemini` (only real impl; others are stubs). |
| `NOX_EXPORT_PASSPHRASE` | A2 | (interactive) | Passphrase for AES-256-GCM export encryption. Prompted on stdin if unset. NEVER pass via `--passphrase=` flag. |
| `NOX_L4_REGEX_ENABLED` | L4 | unset (disabled) | Set to `1` after 7-day shadow baseline to activate regex-first KG extraction. |
| `NOX_VIEWER_TOKEN` | P5 | (required) | Auth token for SSE viewer endpoint. Generate with `openssl rand -hex 32`. |
| `NOX_CONFLICT_MODE` | L2 (Wave C) | `shadow` | Conflict detection mode. Do not set to `active` until 7-day baseline. |
| `NOX_CONFIDENCE_SCORING` | L3 (Wave C) | `shadow` | Confidence scoring mode. Do not set to `active` until 7-day baseline. |

**Existing vars that remain unchanged:**

| Variable | Value | Note |
|---|---|---|
| `GEMINI_API_KEY` | (set) | Used by both A3 Gemini wrappers and pre-existing embedding/KG code. |
| `NOX_API_PORT` | `18802` | Never hardcode — read from .env. |
| `NOX_SALIENCE_MODE` | `shadow` | Keep as-is until 7-day baseline completes. |
| `NOX_ALLOW_NO_SNAPSHOT` | (unset) | Emergency override for destructive ops. Use only if snapshot fails for a known legitimate reason. |

---

*Prepared: 2026-05-18 | Wave B patches: PRs #2, #18, #24, #28, #29, #31, #33–#42*
