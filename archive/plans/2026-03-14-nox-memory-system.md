# Nox Memory System — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a memory system for the Nox OpenClaw agent with SQLite FTS5 search, AI-powered consolidation via local Ollama, and auto-indexation via inotifywait file watcher.

**Status:** IMPLEMENTADO e DEPLOYADO (v2.1.2, 2026-03-14) — 6 rounds de code review pelo Forge agent

**Architecture:** CLI tool (`nox-mem`) written in Node.js/TypeScript that chunks Markdown files into a SQLite FTS5 index for fast search. A file watcher auto-indexes changes. A nightly cron uses Llama 3.2 3B (via Ollama) to extract facts from daily notes and append them to curated topic files. All runs on a Hostinger VPS (4 cores, 16GB RAM) accessed via Tailscale at `100.87.8.44`.

**Tech Stack:** Node.js 22, TypeScript, better-sqlite3, commander, Ollama, llama3.2:3b, inotify-tools, systemd

**Spec:** `specs/2026-03-14-nox-memory-system-design.md`

**VPS access:** `ssh root@100.87.8.44` (via Tailscale)

**Workspace root:** `/root/.openclaw/workspace/`

**Tool location:** `/root/.openclaw/workspace/tools/nox-mem/`

---

## File Structure

```
~/.openclaw/workspace/tools/nox-mem/
├── package.json
├── tsconfig.json
├── .gitignore
├── src/
│   ├── index.ts          — CLI entry point (commander)
│   ├── db.ts             — SQLite connection, schema, migrations
│   ├── ingest.ts         — chunk .md/.json files, insert to FTS5
│   ├── search.ts         — FTS5 query + boost + recency
│   ├── primer.ts         — context recovery post-compaction
│   ├── consolidate.ts    — Ollama API, extract facts, append topic files
│   ├── digest.ts         — weekly summary via Ollama
│   ├── appendInSection.ts — insert content inside markdown sections
│   ├── reindex.ts        — rebuild index (preserves consolidated_files)
│   ├── stats.ts          — chunk counts, consolidation status, db size
│   ├── doctor.ts         — system diagnostics (SQLite, FTS5, Ollama, Notion, watcher)
│   └── notion-sync.ts    — sync consolidated items to Notion diary (optional)
├── prompts/
│   ├── consolidate.txt   — fact extraction prompt
│   └── digest.txt        — weekly summary prompt
├── nox-mem-watch.sh      — inotifywait watcher with debounce
├── nox-mem.db            — SQLite (gitignored, auto-created)
└── dist/                 — compiled JS (gitignored)
```

**VPS files modified outside nox-mem/:**
- `/etc/systemd/system/nox-mem-watcher.service`
- `/usr/local/bin/nox-mem` (symlink)
- `TOOLS.md`, `SOUL.md` (OpenClaw workspace)
- `tools/backup-config.sh`

---

## Chunk 1: Infrastructure Setup

### Task 1: Install SQLite3

- [ ] **Step 1:** Install sqlite3 and dev headers
```bash
ssh root@100.87.8.44 "apt update && apt install -y sqlite3 libsqlite3-dev"
```

- [ ] **Step 2:** Verify FTS5 support
```bash
ssh root@100.87.8.44 "sqlite3 ':memory:' \"CREATE VIRTUAL TABLE t USING fts5(c); DROP TABLE t; SELECT 'FTS5 OK';\""
```
Expected: `FTS5 OK`

---

### Task 2: Install Ollama + llama3.2:3b

- [ ] **Step 1:** Install Ollama
```bash
ssh root@100.87.8.44 "curl -fsSL https://ollama.ai/install.sh | sh"
```

- [ ] **Step 2:** Verify running
```bash
ssh root@100.87.8.44 "systemctl status ollama --no-pager | head -5"
```
Expected: `active (running)`

- [ ] **Step 3:** Pull model (~1.8GB)
```bash
ssh root@100.87.8.44 "ollama pull llama3.2:3b"
```

- [ ] **Step 4:** Test JSON format
```bash
ssh root@100.87.8.44 'curl -s http://127.0.0.1:11434/api/generate -d "{\"model\":\"llama3.2:3b\",\"prompt\":\"Return {\\\"ok\\\": true}\",\"format\":\"json\",\"stream\":false}" | python3 -c "import sys,json; print(json.loads(sys.stdin.read())[\"response\"])"'
```
Expected: `{"ok": true}`

---

### Task 3: Install inotify-tools

- [ ] **Step 1:** Install
```bash
ssh root@100.87.8.44 "apt install -y inotify-tools"
```

- [ ] **Step 2:** Verify
```bash
ssh root@100.87.8.44 "inotifywait --help 2>&1 | head -1"
```
Expected: version info

---

## Chunk 2: Project Scaffold + Database

### Task 4: Create nox-mem project

- [ ] **Step 1:** Create directories
```bash
ssh root@100.87.8.44 "mkdir -p /root/.openclaw/workspace/tools/nox-mem/{src,prompts,dist}"
```

- [ ] **Step 2:** Create package.json on VPS
Write `/root/.openclaw/workspace/tools/nox-mem/package.json`:
```json
{
  "name": "nox-mem",
  "version": "1.0.0",
  "description": "Nox memory system with FTS5 search and AI consolidation",
  "type": "module",
  "bin": { "nox-mem": "./dist/index.js" },
  "scripts": { "build": "tsc" },
  "dependencies": {
    "better-sqlite3": "^11.0.0",
    "commander": "^12.0.0"
  },
  "devDependencies": {
    "@types/better-sqlite3": "^7.6.0",
    "@types/node": "^22.0.0",
    "typescript": "^5.5.0"
  }
}
```

- [ ] **Step 3:** Create tsconfig.json
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "node",
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "declaration": true,
    "skipLibCheck": true
  },
  "include": ["src/**/*"]
}
```

- [ ] **Step 4:** Create .gitignore: `node_modules/`, `dist/`, `nox-mem.db`

- [ ] **Step 5:** Install dependencies
```bash
ssh root@100.87.8.44 "cd /root/.openclaw/workspace/tools/nox-mem && npm install"
```

- [ ] **Step 6:** Commit scaffold
```bash
ssh root@100.87.8.44 "cd /root/.openclaw/workspace && git add tools/nox-mem/package.json tools/nox-mem/tsconfig.json tools/nox-mem/.gitignore tools/nox-mem/package-lock.json && git commit -m 'feat(nox-mem): scaffold project'"
```

---

### Task 5: Implement db.ts

- [x] **Step 1:** Create `src/db.ts` — SQLite connection with WAL mode, schema v1→v2 migration system via `meta.schema_version`. See spec section 5 for full schema.

Key points:
- Use `better-sqlite3` synchronous API (singleton pattern with `getDb()`/`closeDb()`)
- `pragma('journal_mode = WAL')`
- Create schema on first run, check version on subsequent runs
- `migrateToV1()` creates: chunks, chunks_fts, triggers (ai/ad), indexes, meta
- `migrateToV2()` creates: `consolidated_files` table (survives reindex), drops `chunks_au` trigger (FTS5 write amplification fix), drops `idx_chunks_consolidated`

- [x] **Step 2:** Build and test DB creation
Expected: `Schema: { value: '2' }`

- [ ] **Step 3:** Commit
```bash
ssh root@100.87.8.44 "cd /root/.openclaw/workspace && git add tools/nox-mem/src/db.ts && git commit -m 'feat(nox-mem): SQLite schema with FTS5 and migrations'"
```

---

### Task 6: Implement ingest.ts

- [x] **Step 1:** Create `src/ingest.ts` — Chunking by markdown headers (`##`/`###`), 500 word max, 20 word min merge, JSON array splitting, type detection from path (see spec path table), date extraction from filename. Upsert pattern: delete old chunks for file, insert new. Accepts optional `externalDb` (shared connection for reindex) and `skipDelete` (skip DELETE when table already cleared). Includes `sanitizeUtf8()` to fix Portuguese encoding mojibake (ã, ç, é, etc.).

- [ ] **Step 2:** Build and test with a real file
```bash
ssh root@100.87.8.44 "cd /root/.openclaw/workspace/tools/nox-mem && npx tsc && node -e \"import('./dist/ingest.js').then(m => console.log(m.ingestFile('/root/.openclaw/workspace/memory/decisions.md')))\""
```
Expected: `{ chunks: X }` where X > 0

- [ ] **Step 3:** Verify in DB
```bash
ssh root@100.87.8.44 "cd /root/.openclaw/workspace/tools/nox-mem && sqlite3 nox-mem.db 'SELECT chunk_type, COUNT(*) FROM chunks GROUP BY chunk_type'"
```

- [ ] **Step 4:** Commit
```bash
ssh root@100.87.8.44 "cd /root/.openclaw/workspace && git add tools/nox-mem/src/ingest.ts && git commit -m 'feat(nox-mem): markdown chunking and FTS5 ingestion'"
```

---

## Chunk 3: Search + Primer + Reindex + Stats + CLI

### Task 7: Implement search.ts

- [ ] **Step 1:** Create `src/search.ts` — FTS5 MATCH with bm25() ranking. Boost topic files (decision/lesson/person/project/pending) x2.0. Recency boost x1.5 for last 7 days. Return top-5 with score, source_file, chunk_text.

- [ ] **Step 2:** Build and test
```bash
ssh root@100.87.8.44 "cd /root/.openclaw/workspace/tools/nox-mem && npx tsc && node -e \"import('./dist/search.js').then(m => console.log(m.formatResults(m.search('limite linkedin'))))\""
```

- [ ] **Step 3:** Commit

---

### Task 8: Implement stats.ts

- [ ] **Step 1:** Create `src/stats.ts` — Count chunks by type, last consolidation from meta table, pending daily notes count, db file size.

- [ ] **Step 2:** Build and test

- [ ] **Step 3:** Commit

---

### Task 9: Implement reindex.ts

- [x] **Step 1:** Create `src/reindex.ts` — `DELETE FROM chunks` (but PRESERVE `consolidated_files` table), rebuild FTS5 index, scan `memory/` and `shared/` directories recursively for `.md`/`.json`, call `ingestFile(file, db, skipDelete=true)` with shared connection for each.

- [ ] **Step 2:** Build and test full reindex
```bash
ssh root@100.87.8.44 "cd /root/.openclaw/workspace/tools/nox-mem && npx tsc && node -e \"import('./dist/reindex.js').then(m => console.log(m.reindex()))\""
```
Expected: `{ files: ~20, chunks: ~80-150 }`

- [ ] **Step 3:** Verify search works after reindex

- [ ] **Step 4:** Commit

---

### Task 10: Implement primer.ts

- [x] **Step 1:** Create `src/primer.ts` — Read SESSION-STATE.md for active task. Query top-5 recent decisions (by `id DESC`, not source_date) with `extractDecisionLine()` parsing 3 formats (auto bullets, **Decisão:**, ## headers). Query today's daily note chunks. Query up to 3 pending items. Format as ~500 token summary.

- [ ] **Step 2:** Build and test
```bash
ssh root@100.87.8.44 "nox-mem primer"
```
Expected: Structured context recovery output

- [ ] **Step 3:** Commit

---

### Task 11: Implement CLI entry point (index.ts)

- [x] **Step 1:** Create `src/index.ts` — commander-based CLI v2.1.2 with 10 subcommands: search, ingest, reindex, primer, stats, consolidate, retry-failed, digest, sync-notion, doctor. All commands call `closeDb()` after execution.

- [ ] **Step 2:** Build
```bash
ssh root@100.87.8.44 "cd /root/.openclaw/workspace/tools/nox-mem && npx tsc"
```

- [ ] **Step 3:** Make executable and create symlink
```bash
ssh root@100.87.8.44 "chmod +x /root/.openclaw/workspace/tools/nox-mem/dist/index.js && ln -sf /root/.openclaw/workspace/tools/nox-mem/dist/index.js /usr/local/bin/nox-mem"
```

- [ ] **Step 4:** Test all CLI commands
```bash
ssh root@100.87.8.44 "nox-mem --help && nox-mem search 'linkedin' && nox-mem stats && nox-mem primer"
```

- [ ] **Step 5:** Commit

---

## Chunk 4: File Watcher + Initial Indexing

### Task 12: Create watcher and systemd service

- [x] **Step 1:** Create `nox-mem-watch.sh` — inotifywait monitoring `memory/` and `shared/`, debounce 3s per file via lock files in `/tmp/nox-mem-locks/` (md5sum per file path — bash vars don't work in pipe subshells), skip MEMORY.md and SESSION-STATE.md, monitors modify/create/delete events.

- [ ] **Step 2:** Make executable
```bash
ssh root@100.87.8.44 "chmod +x /root/.openclaw/workspace/tools/nox-mem/nox-mem-watch.sh"
```

- [ ] **Step 3:** Create `/etc/systemd/system/nox-mem-watcher.service` — Type=simple, ExecStart calls the watcher script, Restart=on-failure, RestartSec=5.

- [ ] **Step 4:** Enable and start
```bash
ssh root@100.87.8.44 "systemctl daemon-reload && systemctl enable nox-mem-watcher && systemctl start nox-mem-watcher && systemctl status nox-mem-watcher --no-pager | head -5"
```
Expected: `active (running)`

- [ ] **Step 5:** Test auto-indexation
```bash
ssh root@100.87.8.44 "echo '## Auto-test' >> /root/.openclaw/workspace/memory/pending.md && sleep 3 && journalctl -u nox-mem-watcher --no-pager -n 3 && sed -i '/^## Auto-test$/d' /root/.openclaw/workspace/memory/pending.md"
```
Expected: Log shows ingest of pending.md

- [ ] **Step 6:** Run initial full reindex
```bash
ssh root@100.87.8.44 "nox-mem reindex && nox-mem stats"
```

- [ ] **Step 7:** Commit
```bash
ssh root@100.87.8.44 "cd /root/.openclaw/workspace && git add tools/nox-mem/nox-mem-watch.sh && git commit -m 'feat(nox-mem): inotifywait watcher with debounce'"
```

---

## Chunk 5: AI Consolidation + Digest

### Task 13: Implement consolidate.ts

- [ ] **Step 1:** Create `prompts/consolidate.txt` — Prompt for structured JSON extraction of decisions, lessons, people, projects, pending from daily note text.

- [x] **Step 2:** Create `src/consolidate.ts`:
  - Find unconsolidated daily notes via `consolidated_files` table (NOT `is_consolidated` column) — max 5 per run
  - Concatenate chunks per source_file
  - Call Ollama API (`format: "json"`, `temperature: 0`, timeout 120s, retry 3x)
  - Deduplicate via FTS5 (first 8 significant words >3 chars, 70% overlap threshold)
  - Insert new items INSIDE topic file sections via `appendInSection()` (not just append at EOF)
  - Track state in `consolidated_files` table: `status=1` (ok) or `status=-1` (failed)
  - Save items to `last-sync.json` for Notion re-sync
  - Sync to Notion if enabled
  - Git commit automatically
  - Report remaining count for re-execution
  - `retry-failed` option resets status=-1 files for reprocessing

- [ ] **Step 3:** Update index.ts — replace consolidate placeholder with async import

- [ ] **Step 4:** Build and test
```bash
ssh root@100.87.8.44 "cd /root/.openclaw/workspace/tools/nox-mem && npx tsc && nox-mem consolidate"
```

- [ ] **Step 5:** Commit

---

### Task 13b: Implement notion-sync.ts (Notion diary)

Syncs consolidated items to the Notion "Memória & Decisões" database as a visual project diary.

**Notion Database:** `31d8e29911ab8163b718d7af565f2fcc`
**Token:** read from `~/.config/notion/api_key`
**Schema:**
| Property | Type | Mapping |
|---|---|---|
| Título | title | First line or summary of the item |
| Data | date | source_date from the daily note |
| Categoria | select | `Decisão` / `Lição` / `Pendência` / `Contexto` / `Sistema Openclaw` |
| Conteúdo | rich_text | Full text of the extracted item |
| Fonte | rich_text | Source file path (e.g. `memory/2026-03-14.md`) |

**Category mapping from consolidation types:**
- `decisions[]` → Categoria: `Decisão`
- `lessons[]` → Categoria: `Lição`
- `people[]` → Categoria: `Contexto`
- `projects[]` → Categoria: `Contexto`
- `pending[]` → Categoria: `Pendência`

**Files:**
- Create: `tools/nox-mem/src/notion-sync.ts`

- [ ] **Step 1:** Create `src/notion-sync.ts`:
  - Read token from `~/.config/notion/api_key`
  - Use Node.js native `fetch` to call Notion API (`https://api.notion.com/v1/pages`)
  - Accept array of items with: `title`, `date`, `category`, `content`, `source`
  - Create one Notion page per item in the database
  - Rate limit: 3 requests/second (Notion API limit)
  - If Notion API fails → `[WARN]` log and continue (never block consolidation)

- [ ] **Step 2:** Integrate into consolidate.ts:
  - After successful extraction and append to topic files
  - Collect all new (non-duplicate) items
  - Call `syncToNotion(items)` at the end
  - Notion sync is best-effort — failure doesn't affect local consolidation

- [ ] **Step 3:** Add `sync-notion` CLI command for manual sync:
  - `nox-mem sync-notion` — re-syncs today's consolidation to Notion
  - Update index.ts with new command

- [ ] **Step 4:** Build and test
```bash
ssh root@100.87.8.44 "cd /root/.openclaw/workspace/tools/nox-mem && npx tsc && nox-mem sync-notion"
```
Expected: Items created in Notion database

- [ ] **Step 5:** Commit
```bash
ssh root@100.87.8.44 "cd /root/.openclaw/workspace && git add tools/nox-mem/src/notion-sync.ts tools/nox-mem/src/consolidate.ts tools/nox-mem/src/index.ts && git commit -m 'feat(nox-mem): add Notion sync for Memória & Decisões diary'"
```

---

### Task 14: Implement digest.ts

- [ ] **Step 1:** Create `prompts/digest.txt` — Prompt for 3-5 bullet weekly summary.

- [ ] **Step 2:** Create `src/digest.ts`:
  - Query chunks from last 7 days (all types)
  - Send to Ollama (temperature 0.3, no JSON format)
  - Save to `memory/digests/YYYY-WNN.md`
  - Create digests directory if needed

- [ ] **Step 3:** Update index.ts — replace digest placeholder

- [ ] **Step 4:** Build and test
```bash
ssh root@100.87.8.44 "nox-mem digest && cat /root/.openclaw/workspace/memory/digests/*.md | head -20"
```

- [ ] **Step 5:** Commit

---

## Chunk 6: OpenClaw Integration + Validation

### Task 15: Create OpenClaw crons

- [ ] **Step 1:** Create `memory-consolidation` cron (0 23 * * *, llama3.2:3b, timeout 480s)
- [ ] **Step 2:** Create `memory-digest` cron (0 21 * * 0, llama3.2:3b, timeout 300s)
- [ ] **Step 3:** Verify crons registered

---

### Task 16: Update SOUL.md

- [ ] **Step 1:** Append memory search instructions block (when to search, when not to, compaction recovery protocol). See spec section 9.
- [ ] **Step 2:** Commit

---

### Task 17: Update TOOLS.md

- [x] **Step 1:** Append nox-mem tool documentation (10 commands: search, ingest, reindex, primer, stats, consolidate, retry-failed, digest, sync-notion, doctor). See spec section 9.
- [ ] **Step 2:** Commit

---

### Task 18: Add nox-mem.db to backup

- [ ] **Step 1:** Append `cp` line to `tools/backup-config.sh`
- [ ] **Step 2:** Commit

---

### Task 19: End-to-end validation

- [ ] **Step 1:** Verify services: `systemctl status nox-mem-watcher ollama`
- [ ] **Step 2:** Test 4 search queries: linkedin, fernando, miami, slack
- [ ] **Step 3:** Test consolidation: `nox-mem consolidate`
- [ ] **Step 4:** Test auto-indexation: append to file, wait 3s, search
- [ ] **Step 5:** Test resilience: stop Ollama, run consolidate (should warn), run search (should work), start Ollama
- [ ] **Step 6:** Test reindex from scratch: delete db, reindex, verify stats match

---

### Task 20: Final push

- [ ] **Step 1:** Push all commits
```bash
ssh root@100.87.8.44 "cd /root/.openclaw/workspace && git push"
```

- [x] **Step 2:** Report summary to Toto with: chunk count, services running, crons configured, commands available

---

## Post-Implementation: Fixes from 6 Forge Code Review Rounds (v2.1.2)

All tasks above were completed and then refined through 6 rounds of automated code review by the Forge agent. Key fixes applied:

| # | Fix | Impact |
|---|-----|--------|
| 1 | Schema v2: `consolidated_files` table separate from chunks | HIGH — consolidation state survives reindex |
| 2 | Dropped `chunks_au` FTS5 trigger | MEDIUM — eliminated write amplification |
| 3 | Max 5 files per consolidation run | HIGH — prevents cron timeout |
| 4 | `appendInSection()` utility | MEDIUM — inserts inside sections, not at EOF |
| 5 | `sanitizeUtf8()` in ingest | MEDIUM — fixes Portuguese encoding |
| 6 | `ingestFile()` optional params (externalDb, skipDelete) | MEDIUM — efficient reindex |
| 7 | Lock file debounce in watcher | MEDIUM — bash vars don't work in pipe subshells |
| 8 | `extractDecisionLine()` with 3 format parsers | MEDIUM — handles manual + auto decisions |
| 9 | ISO 8601 week numbers (Thursday anchor) | LOW — correct week calculation |
| 10 | Digest temperature 0.3 + retry 3x | LOW — better summaries |
| 11 | Notion API version → 2025-09-03 | LOW — updated to latest |
| 12 | Pending category → "Pendência" (was "Insight") | LOW — correct categorization |
| 13 | `last-sync.json` persistence | MEDIUM — allows Notion retry without reconsolidation |
| 14 | `retry-failed` command added | MEDIUM — reprocess failed consolidations |
| 15 | `doctor` command added | MEDIUM — full system diagnostics |
| 16 | Version synced to 2.1.2 everywhere | LOW — consistency |

**Final score from Forge: 9/10**
**Production stats: 507 chunks indexed from 195 files, 75 facts extracted, 75 Notion entries synced**
