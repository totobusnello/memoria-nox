# CLI Recipes — Common Workflows

10 real-world patterns for nox-mem. All commands are tested against the live corpus.

**Prerequisite for every script:**
```bash
set -a; source ~/.openclaw/.env; set +a
```
Without this, `vectorize`, `kg-build`, and `answer` fail silently (0 embedded, 0 extracted). See CLAUDE.md rule #1.

---

## Recipe 1 — Search then answer

Pull context, then get a grounded answer with citations.

```bash
# Step 1: search to see what's available
nox-mem search "how does pain affect ranking" --limit 5

# Step 2: get a full grounded answer
nox-mem answer "How does pain affect search ranking in nox-mem?"

# With JSON output (for scripting)
nox-mem answer "How does pain affect search ranking?" --json | jq '{answer: .answer, citations: [.citations[].source_file]}'
```

For time-travel: what did we know last week?

```bash
nox-mem search "authentication implementation" --as-of 7d
```

---

## Recipe 2 — Export then import (backup workflow)

Portable archive with AES-256-GCM encryption. Round-trip preserves nDCG@10 ± 0.001.

```bash
# Export (passphrase from env, never from CLI arg)
export NOX_ARCHIVE_PASS="your-passphrase"
nox-mem archive export ~/backups/nox-mem-$(date +%Y%m%d).noxarchive \
  --passphrase-env NOX_ARCHIVE_PASS

# Verify archive integrity
nox-mem archive export ~/backups/test.noxarchive --dry-run

# Import on another machine
nox-mem archive import ~/backups/nox-mem-20260518.noxarchive \
  --passphrase-env NOX_ARCHIVE_PASS \
  --on-conflict skip    # default: merge, skip duplicates

# Verify after import
curl http://127.0.0.1:18802/api/health | jq '{total: .totalChunks, embedded: .embeddedChunks}'
```

---

## Recipe 3 — Mark canonical, search shows preference

Elevate a fact you want the retrieval stack to prefer. Requires L3 deploy.

```bash
# Find the chunk ID
nox-mem search "gemini-2.5-flash-lite is the default model" --json | jq '.[0].id'
# → 4821

# Mark as canonical (confidence → 1.0)
nox-mem mark 4821 --kind canonical --notes "Confirmed as of 2026-05-18"

# Verify
nox-mem search "default model" --json | jq '.[0] | {id, content, confidence}'

# Mark old chunk as superseded by the new one
nox-mem supersede 3200 --by 4821 --reason manual_resolution
```

> Ranking effect requires `NOX_RANKING_CONFIDENCE=active`. Shadow by default.

---

## Recipe 4 — Run conflict scan + review

Detect opposing relations in the knowledge graph. Requires L2 deploy.

```bash
# Full corpus scan (wrapped in withOpAudit)
nox-mem conflicts scan

# Scope to one entity
nox-mem conflicts scan --subject "gemini-2.5-flash"

# List unresolved
nox-mem conflicts list --type direct --limit 20

# Inspect one
nox-mem conflicts show 7

# Resolve: keep relation 142, suppress 143
nox-mem conflicts resolve 7 --keep 142 --note "flash-lite is the current default"

# Dismiss false positive
nox-mem conflicts dismiss 12 --note "Both valid for different use cases"
```

---

## Recipe 5 — Open viewer in browser

Real-time SSE viewer. Requires P5 deploy and P5a event bus.

```bash
# Ensure nox-mem-api is running
nox-mem serve

# Open in browser (macOS)
open http://127.0.0.1:18802/viewer

# Debug: stream raw events to terminal
curl -N http://127.0.0.1:18802/api/events

# Filter by event type
curl -N http://127.0.0.1:18802/api/events | grep '"kind":"ingest"'
```

---

## Recipe 6 — Restore from corrupted DB

Use `safeRestore()` via the CLI recovery command. Never use `cp` directly (WAL corruption).

```bash
# List available pre-op snapshots
ls /var/backups/nox-mem/pre-op/

# Restore from a specific snapshot (validates user_version match)
nox-mem restore /var/backups/nox-mem/pre-op/reindex-20260518-120345-abc123.db

# Verify after restore
curl http://127.0.0.1:18802/api/health | jq .vectorCoverage

# If disk full (emergency override — use only if snapshot failed for legitimate reason)
NOX_ALLOW_NO_SNAPSHOT=1 nox-mem reindex
```

> Never `cp snapshot.db nox-mem.db` — stale WAL file will corrupt the restore. Always use `nox-mem restore`.

---

## Recipe 7 — Add custom PII pattern

Extend the A1 privacy filter with a domain-specific redaction pattern.

```bash
# Check current patterns
nox-mem privacy list

# Add a custom pattern (regex)
nox-mem privacy add --name "internal-ticket" --pattern "PROJ-[0-9]{4,}" --replacement "<ticket-id>"

# Test redaction without ingest
echo "See PROJ-1234 for details" | nox-mem privacy test

# Ingest with custom pattern active (applied automatically via ingest router)
nox-mem ingest ~/notes/standup-2026-05-18.md
```

---

## Recipe 8 — Manage providers (switch from Gemini to OpenAI)

nox-mem supports `gemini`, `openai`, and `local` embedding providers. Switching provider requires re-vectorizing the corpus.

```bash
# Check current provider
echo $NOX_EMBED_PROVIDER   # gemini

# Switch to OpenAI
export NOX_EMBED_PROVIDER=openai
export OPENAI_API_KEY=sk-...

# Re-vectorize (this replaces all embeddings — run with --dry-run first)
nox-mem vectorize --dry-run
nox-mem vectorize

# Verify coverage
curl http://127.0.0.1:18802/api/health | jq .vectorCoverage

# Check cost — provider overhead benchmark
nox-mem answer "test" --json | jq '.metadata | {provider, latency_ms}'
```

> Provider abstraction overhead: 0.0025ms per LLM call (A3 benchmark). Switching is safe — the schema is provider-agnostic.

---

## Recipe 9 — Run latency benchmark locally

Reproduce the p50/p95/p99 numbers against your own corpus.

```bash
# Search latency (10 queries)
for q in "salience formula" "pain field" "shadow discipline" "RRF fusion" "FTS5 BM25" \
         "retention days" "entity file format" "MCP tools" "kg relations" "section boost"; do
  time nox-mem search "$q" --limit 5 --json > /dev/null
done

# Answer primitive latency (5 questions)
time nox-mem answer "What is the salience formula?" --json > /dev/null

# Full benchmark with JSON output
nox-mem answer "How does pain affect ranking?" --json | jq '.metadata.latency_ms'

# P5 viewer latency (SSE first-event-to-render)
# Start viewer in browser, then ingest a file and watch the latency in browser DevTools
nox-mem ingest ~/test-note.md
```

Reference: p95 answer = 101.74ms (mock LLM @ 100ms, PR #40). Your results will vary by corpus size and provider.

---

## Recipe 10 — Apply staged Wave B patch

Deploy a staged patch from `staged-<name>/` to the VPS.

```bash
# Read the deploy guide first
cat docs/DEPLOY-WAVE-B.md

# Dry-run: check what would change
nox-mem reindex --dry-run

# Apply a specific patch (example: staged-P1)
cd /root/.openclaw/workspace/tools/nox-mem
cp ~/staged-P1/edits/src/mcp/tools/answer.ts src/mcp/tools/answer.ts
npm run build

# Restart the API
systemctl restart nox-mem-api

# Verify
curl http://127.0.0.1:18802/api/health | jq .version
nox-mem answer "test" --json | jq .metadata
```

> Always source env before running on VPS: `set -a; source /root/.openclaw/.env; set +a`
