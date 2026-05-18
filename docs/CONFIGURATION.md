# nox-mem — Configuration Reference

> Full environment variable reference. Every variable documented here is wired in the codebase.
>
> **Quick start:** copy `.env.example` to `.env`, set `GEMINI_API_KEY`, and run `set -a; source .env; set +a` before any `nox-mem` command. See [`docs/QUICKSTART.md`](QUICKSTART.md) for a working tutorial.
>
> **Validate resolved values at runtime:** `curl http://127.0.0.1:18802/api/health | jq .` — the health endpoint shows the actual values the running process resolved, not just what is in `.env`.

---

## How env vars are loaded

nox-mem does not auto-load `.env`. You must source it explicitly:

```bash
set -a; source /path/to/.env; set +a
nox-mem <command>
```

In cron jobs and systemd units, add the source call before the `nox-mem` invocation. Without it, `GEMINI_API_KEY` (and all other vars) are absent from the process environment — vectorize and kg-extract fail silently, reporting `Done: 0 embedded, N errors` at the end while looking otherwise healthy.

**Reload behavior:** almost all config values are read at process startup. Changing a value in `.env` requires restarting the `nox-mem serve` process (or the MCP server) to take effect. The health endpoint at `/api/health` always reflects the values the current process resolved.

---

## Core

### `NOX_API_PORT`

| | |
|---|---|
| **Default** | `18802` |
| **Type** | number (TCP port) |
| **Controls** | Port the HTTP API (`nox-mem serve`) and SSE viewer listen on |
| **When to change** | If 18802 is already in use by another service on your machine |

**Do not set this to 18800.** Chrome's remote-debugging service squats port 18800. The choice of 18802 is intentional — see rule #4 in [`CLAUDE.md`](../CLAUDE.md).

```bash
NOX_API_PORT=18802
```

---

### `NOX_DB_PATH`

| | |
|---|---|
| **Default** | `./nox-mem.db` |
| **Type** | path (absolute or relative to CWD) |
| **Controls** | Location of the SQLite database file |
| **When to change** | To point at an existing DB or to put the store in a stable non-CWD location |

The SQLite file is the entire memory store. `cp nox-mem.db backup.db` is a valid backup. Do not `mv` it while the API is running — use `nox-mem export` for live exports.

```bash
NOX_DB_PATH=/root/.openclaw/workspace/tools/nox-mem/nox-mem.db
```

---

### `NOX_MEM_DIR`

| | |
|---|---|
| **Default** | `$PWD/data` (or parent dir of `NOX_DB_PATH` if set) |
| **Type** | path |
| **Controls** | Root directory for data files (DB, KG snapshots, temp artifacts) |
| **When to change** | To separate data from the code directory |

```bash
NOX_MEM_DIR=/var/lib/nox-mem
```

---

### `OPENCLAW_WORKSPACE`

| | |
|---|---|
| **Default** | unset |
| **Type** | path |
| **Controls** | Workspace root for all nox-mem modules — all relative paths are resolved against this |
| **When to change** | When running nox-mem inside an OpenClaw installation or a multi-tenant workspace |

All modules respect this variable. Setting it allows the full stack to run from an arbitrary directory without changing CWDs.

---

## Embedding and LLM providers

### `GEMINI_API_KEY`

| | |
|---|---|
| **Default** | _(required for embeddings and KG extraction)_ |
| **Type** | string (API key) |
| **Controls** | Gemini API authentication — used by the default embedding provider and KG extraction |
| **When to change** | Initial setup; after key rotation |

Get a key at [aistudio.google.com](https://aistudio.google.com). The key is never logged, never included in exports, and never proxied through any nox-mem server.

```bash
GEMINI_API_KEY=AIzaSy...
```

> **Never commit this key to git.** Run `grep -r "AIzaSy" .` before any commit. The `.gitignore` excludes `.env` by default — do not override this.

---

### `NOX_EMBEDDING_PROVIDER`

| | |
|---|---|
| **Default** | `gemini` |
| **Type** | enum: `gemini` \| `openai` \| `voyage` |
| **Controls** | Which provider generates 3072-d embeddings for new chunks |
| **When to change** | To switch from Gemini to OpenAI (`text-embedding-3-large`) or Voyage for BYO-provider setups |

Gemini is the default because the eval baseline was established on Gemini 3072-d embeddings. Switching providers changes all future embeddings but does not re-embed existing chunks — run `nox-mem vectorize --force` after switching to rebuild the entire vector store.

```bash
NOX_EMBEDDING_PROVIDER=gemini   # or: openai, voyage
```

Required keys by provider:
- `gemini`: `GEMINI_API_KEY`
- `openai`: `OPENAI_API_KEY`
- `voyage`: `VOYAGE_API_KEY`

---

### `NOX_EMBEDDING_MODEL`

| | |
|---|---|
| **Default** | provider default (Gemini: `gemini-embedding-001`) |
| **Type** | string (model ID) |
| **Controls** | Which embedding model is called — overrides the provider default |
| **When to change** | When testing a new embedding model against the golden eval set |

Shadow-mode discipline applies: change embedding models only after running `eval/golden/` and confirming `nDCG@10` does not regress.

```bash
NOX_EMBEDDING_MODEL=text-embedding-3-large
```

---

### `NOX_LLM_PROVIDER`

| | |
|---|---|
| **Default** | `gemini` |
| **Type** | enum: `gemini` \| `openai` \| `anthropic` |
| **Controls** | LLM provider used for KG extraction, answer grounding, and reflection |
| **When to change** | To switch to OpenAI or Anthropic for LLM-backed operations |

```bash
NOX_LLM_PROVIDER=gemini   # or: openai, anthropic
```

Required keys by provider:
- `gemini`: `GEMINI_API_KEY`
- `openai`: `OPENAI_API_KEY`
- `anthropic`: `ANTHROPIC_API_KEY`

---

### `NOX_LLM_MODEL`

| | |
|---|---|
| **Default** | `gemini/gemini-2.5-flash-lite` |
| **Type** | string (model ID with provider prefix) |
| **Controls** | Which model handles KG extraction, answer grounding, and reflection |
| **When to change** | Only with explicit reason — the default is cost-optimized and quota-safe |

**Never change this to `gemini-2.5-flash`** (quota 3M/day exhausts quickly on large corpora) or `gemini-2.0-flash` (deprecated, shutdown 2026-06-01). KG extraction can use `gemini-2.5-flash` full while corpus volume is low.

See rule #3 in [`CLAUDE.md`](../CLAUDE.md).

```bash
NOX_LLM_MODEL=gemini/gemini-2.5-flash-lite
```

---

### `NOX_PROVIDER_HEALTH_FAIL_FAST`

| | |
|---|---|
| **Default** | `1` (fail fast) |
| **Type** | boolean (`1` / `0`) |
| **Controls** | Whether a failed boot-time provider health check throws (hard) or logs a warning (soft) |
| **When to change** | Set to `0` in CI environments where providers are mocked, or during network-degraded startup |

When `1` (default), `bootProviderHealth()` throws `ProviderHealthError` on startup if any selected provider is unreachable. When `0`, logs a warning and continues — the process comes up degraded.

```bash
NOX_PROVIDER_HEALTH_FAIL_FAST=1
```

---

## Search and ranking

### `NOX_SALIENCE_MODE`

| | |
|---|---|
| **Default** | `shadow` |
| **Type** | enum: `shadow` \| `active` |
| **Controls** | Whether salience scores (`recency × pain × importance`) influence live query ranking |
| **When to change** | After ≥7 days of shadow-mode baseline showing positive eval delta |

In `shadow` mode, salience is computed and exposed on `/api/health.salience` but does not affect the ranking of results returned to callers. In `active` mode, salience composes with the RRF score at query time.

**The bar for flipping to `active` is non-negotiable:** ≥7 days of baseline + `+1.0pp nDCG@10` over the current golden set. See rule #5 in [`CLAUDE.md`](../CLAUDE.md) and [`CONTRIBUTING.md`](../CONTRIBUTING.md) Shadow Discipline section.

```bash
NOX_SALIENCE_MODE=shadow    # default — safe
NOX_SALIENCE_MODE=active    # only after eval gate passes
```

---

### `NOX_LANG_AWARE_RRF`

| | |
|---|---|
| **Default** | `1` (enabled) |
| **Type** | boolean (`1` / `0`) |
| **Controls** | Language-aware RRF fusion weights — tilts dense up on PT queries (1.15×), FTS down (0.85×), balanced on EN/mixed |
| **When to change** | Only to disable for an A/B experiment — this feature was validated at +1.92pp on PT/EN mixed corpus (Wave E14) |

```bash
NOX_LANG_AWARE_RRF=1
```

---

### `NOX_SEARCH_LOG_TEXT`

| | |
|---|---|
| **Default** | `0` (off) |
| **Type** | boolean (`1` / `0`) |
| **Controls** | Whether query text is persisted in the `search_telemetry` table alongside scores |
| **When to change** | Enable when running eval harness or building a golden set — adds 4 telemetry columns including `query_text`, `golden_id`, `top_chunk_ids`, `top_scores` |

Query text is never logged by default — privacy protection. Enable only in controlled eval environments.

```bash
NOX_SEARCH_LOG_TEXT=0    # default — queries not stored
NOX_SEARCH_LOG_TEXT=1    # eval mode — queries stored in search_telemetry
```

---

## Confidence and provenance (L3)

These variables control the confidence/provenance system (Lab sprint L3). The ranking mode defaults to `disabled` — same shadow-mode gate as salience.

### `NOX_RANKING_CONFIDENCE`

| | |
|---|---|
| **Default** | `disabled` |
| **Type** | enum: `disabled` \| `shadow` \| `active` |
| **Controls** | Whether confidence scores influence query ranking |
| **When to change** | After ≥7d shadow baseline + `+1.0pp nDCG@10` eval gate |

```bash
NOX_RANKING_CONFIDENCE=disabled
```

---

### `NOX_CONFIDENCE_OBSERVED`

| | |
|---|---|
| **Default** | `0.95` |
| **Type** | float \[0, 1\] |
| **Controls** | Default confidence assigned to chunks sourced from direct observation or explicit user statement |

---

### `NOX_CONFIDENCE_INFERRED`

| | |
|---|---|
| **Default** | `0.65` |
| **Type** | float \[0, 1\] |
| **Controls** | Default confidence for chunks whose provenance is inferred (e.g., extracted by LLM from context, not stated explicitly) |

---

### `NOX_CONFIDENCE_DERIVED`

| | |
|---|---|
| **Default** | `0.75` |
| **Type** | float \[0, 1\] |
| **Controls** | Default confidence for chunks derived from other chunks (crystallize output, reflection summaries) |

---

### `NOX_CONFIDENCE_GRAPHIFY`

| | |
|---|---|
| **Default** | `0.70` |
| **Type** | float \[0, 1\] |
| **Controls** | Default confidence assigned to chunks ingested via the graphify pipeline |

---

### `NOX_CONFIDENCE_USER_CANONICAL`

| | |
|---|---|
| **Default** | `1.00` |
| **Type** | float \[0, 1\] |
| **Controls** | Confidence value applied when a user explicitly marks a chunk as canonical (`nox-mem mark --canonical <id>`) |

---

### `NOX_CONFIDENCE_USER_REFUTED`

| | |
|---|---|
| **Default** | `0.05` |
| **Type** | float \[0, 1\] |
| **Controls** | Confidence value applied when a user explicitly marks a chunk as refuted |

---

### `NOX_CONFIDENCE_ACTIVE_FLOOR`

| | |
|---|---|
| **Default** | `0.30` |
| **Type** | float \[0, 1\] |
| **Controls** | When `NOX_RANKING_CONFIDENCE=active`, chunks with confidence below this floor are excluded from results |

---

### `NOX_CONFIDENCE_DECAY_HALFLIFE_DAYS`

| | |
|---|---|
| **Default** | `-1` (disabled) |
| **Type** | integer (days, `-1` = disabled) |
| **Controls** | Half-life for confidence time-decay — disabled in v1, reserved for future activation |

---

## Conflict detection (L2)

Lab sprint L2 — KG conflict and contradiction detection. Defaults to `disabled` pending eval lift confirmation.

### `NOX_CONFLICT_MODE`

| | |
|---|---|
| **Default** | `disabled` |
| **Type** | enum: `disabled` \| `shadow` \| `active` |
| **Controls** | Whether the conflict detector runs passes and surfaces conflicts |
| **When to change** | After reviewing conflict detection results in shadow mode over ≥7 days |

In `shadow` mode, conflict passes run and write results to the `conflict_audit` table, but nothing surfaces to callers. In `active` mode, detected conflicts appear in search results and via `/api/conflict`.

```bash
NOX_CONFLICT_MODE=disabled
```

---

### `NOX_CONFLICT_SCAN_CRON`

| | |
|---|---|
| **Default** | `0 3 * * *` (03:00 daily — after backup-all at 02:00) |
| **Type** | cron expression (`M H * * *` format) |
| **Controls** | When the periodic conflict scanner runs (if the daemon is opt-in enabled) |
| **When to change** | To move the scan window away from backup time, or to run more/less frequently |

The scheduler only supports `M H * * *` format — day-of-month, month, and day-of-week fields must be `*`.

```bash
NOX_CONFLICT_SCAN_CRON="0 3 * * *"
```

---

## Regex-first extraction (L4)

Lab sprint L4 — gbrain-inspired regex-first typed-link extraction with Gemini fallback.

### `NOX_L4_REGEX_ENABLED`

| | |
|---|---|
| **Default** | `0` (off) |
| **Type** | boolean (`1` / `0`) |
| **Controls** | Whether L4 regex-first extraction runs during ingest as a KG relation source |
| **When to change** | Enable after reviewing the precision/recall numbers from `eval/regex-vs-llm.ts` on your corpus |

When disabled, the standard Gemini LLM extraction pipeline runs unchanged. When enabled, L4 attempts regex extraction first and falls through to Gemini only for low-confidence matches (`bare_refs < 0.75`).

```bash
NOX_L4_REGEX_ENABLED=0
```

---

### `NOX_L4_SKIP_GEMINI`

| | |
|---|---|
| **Default** | `0` (off — Gemini fallback active) |
| **Type** | boolean (`1` / `0`) |
| **Controls** | When `NOX_L4_REGEX_ENABLED=1`, whether low-confidence refs are passed to Gemini or dropped |
| **When to change** | Enable for cost-cap environments where Gemini calls are quota-constrained — accept lower recall in exchange for zero LLM cost on ambiguous refs |

```bash
NOX_L4_SKIP_GEMINI=0
```

---

### `NOX_L4_AUTO_RENAME`

| | |
|---|---|
| **Default** | `0` (off — destructive mode disabled) |
| **Type** | boolean (`1` / `0`) |
| **Controls** | Whether L4 reconciler rewrites old slug references to new slugs when an entity is renamed |
| **When to change** | Enable only during a planned entity rename operation — this rewrites chunk content in place |

This is a **destructive operation** — it rewrites stored chunk text. Only enable when performing a deliberate slug rename, and only after running with `--dry-run` to preview the changes. The reconciler prevents circular renames and validates the rename chain before writing.

```bash
NOX_L4_AUTO_RENAME=0    # default — safe
NOX_L4_AUTO_RENAME=1    # enable only for planned rename ops
```

---

## Real-time viewer (P5)

### `NOX_VIEWER_SHOW_QUERY`

| | |
|---|---|
| **Default** | `0` (off — queries redacted) |
| **Type** | boolean (`1` / `0`) |
| **Controls** | Whether the SSE viewer at `/ui` shows the full text of search queries |
| **When to change** | Enable in controlled eval or debugging sessions; leave off for any shared or networked deployment |

Query text contains potentially sensitive information. The viewer redacts it by default — only the result counts and scores are shown.

```bash
NOX_VIEWER_SHOW_QUERY=0
```

---

### `NOX_VIEWER_AUTH_TOKEN`

| | |
|---|---|
| **Default** | unset (no auth — local-only safe) |
| **Type** | string (random token) |
| **Controls** | If set, the viewer and `/api/*` endpoints require `Authorization: Bearer <token>` |
| **When to change** | Set whenever `nox-mem serve` binds to a non-localhost interface or is exposed through a reverse proxy |

Generate a token:

```bash
openssl rand -hex 32
```

```bash
NOX_VIEWER_AUTH_TOKEN=a7f3c9...
```

---

## Operational and safety

### `NOX_ALLOW_NO_SNAPSHOT`

| | |
|---|---|
| **Default** | `0` (off — snapshot required) |
| **Type** | boolean (`1` / `0`) |
| **Controls** | Whether `withOpAudit()` proceeds if the pre-op snapshot fails to write |
| **When to change** | Only when the snapshot legitimately cannot be created (e.g., disk full during an emergency reindex) |

This is an emergency override for destructive operations (`reindex`, `compact`, `crystallize`, `kg-prune`). The normal behavior requires a pre-op snapshot in `/var/backups/nox-mem/pre-op/` (ACL `0600`) before proceeding.

**Do not use this as a shortcut.** The incident on 2026-04-25 showed what happens when destructive ops run without safety nets. See rule #6 in [`CLAUDE.md`](../CLAUDE.md).

```bash
NOX_ALLOW_NO_SNAPSHOT=0    # default — always require snapshot
NOX_ALLOW_NO_SNAPSHOT=1    # emergency only — document the reason before enabling
```

---

## Quick reference table

| Variable | Default | Domain |
|---|---|---|
| `NOX_API_PORT` | `18802` | Core |
| `NOX_DB_PATH` | `./nox-mem.db` | Core |
| `NOX_MEM_DIR` | `$PWD/data` | Core |
| `OPENCLAW_WORKSPACE` | _(unset)_ | Core |
| `GEMINI_API_KEY` | _(required)_ | Providers |
| `NOX_EMBEDDING_PROVIDER` | `gemini` | Providers |
| `NOX_EMBEDDING_MODEL` | provider default | Providers |
| `NOX_LLM_PROVIDER` | `gemini` | Providers |
| `NOX_LLM_MODEL` | `gemini/gemini-2.5-flash-lite` | Providers |
| `NOX_PROVIDER_HEALTH_FAIL_FAST` | `1` | Providers |
| `NOX_SALIENCE_MODE` | `shadow` | Search |
| `NOX_LANG_AWARE_RRF` | `1` | Search |
| `NOX_SEARCH_LOG_TEXT` | `0` | Search |
| `NOX_RANKING_CONFIDENCE` | `disabled` | L3 — Confidence |
| `NOX_CONFIDENCE_OBSERVED` | `0.95` | L3 — Confidence |
| `NOX_CONFIDENCE_INFERRED` | `0.65` | L3 — Confidence |
| `NOX_CONFIDENCE_DERIVED` | `0.75` | L3 — Confidence |
| `NOX_CONFIDENCE_GRAPHIFY` | `0.70` | L3 — Confidence |
| `NOX_CONFIDENCE_USER_CANONICAL` | `1.00` | L3 — Confidence |
| `NOX_CONFIDENCE_USER_REFUTED` | `0.05` | L3 — Confidence |
| `NOX_CONFIDENCE_ACTIVE_FLOOR` | `0.30` | L3 — Confidence |
| `NOX_CONFIDENCE_DECAY_HALFLIFE_DAYS` | `-1` | L3 — Confidence |
| `NOX_CONFLICT_MODE` | `disabled` | L2 — Conflict |
| `NOX_CONFLICT_SCAN_CRON` | `0 3 * * *` | L2 — Conflict |
| `NOX_L4_REGEX_ENABLED` | `0` | L4 — Extraction |
| `NOX_L4_SKIP_GEMINI` | `0` | L4 — Extraction |
| `NOX_L4_AUTO_RENAME` | `0` | L4 — Extraction |
| `NOX_VIEWER_SHOW_QUERY` | `0` | Viewer |
| `NOX_VIEWER_AUTH_TOKEN` | _(unset)_ | Viewer |
| `NOX_ALLOW_NO_SNAPSHOT` | `0` | Safety |

---

## `.env.example` template

```bash
# ── Core ──────────────────────────────────────────────────────────────────
NOX_API_PORT=18802
NOX_DB_PATH=./data/nox-mem.db
# NOX_MEM_DIR=./data
# OPENCLAW_WORKSPACE=/root/.openclaw/workspace

# ── Providers ─────────────────────────────────────────────────────────────
GEMINI_API_KEY=          # required — get from aistudio.google.com
# OPENAI_API_KEY=        # if NOX_EMBEDDING_PROVIDER=openai or NOX_LLM_PROVIDER=openai
# ANTHROPIC_API_KEY=     # if NOX_LLM_PROVIDER=anthropic
# VOYAGE_API_KEY=        # if NOX_EMBEDDING_PROVIDER=voyage

NOX_EMBEDDING_PROVIDER=gemini
# NOX_EMBEDDING_MODEL=   # override only if testing a specific model
NOX_LLM_PROVIDER=gemini
NOX_LLM_MODEL=gemini/gemini-2.5-flash-lite   # DO NOT change to gemini-2.5-flash (quota) or gemini-2.0-flash (deprecated)
NOX_PROVIDER_HEALTH_FAIL_FAST=1

# ── Search / ranking ──────────────────────────────────────────────────────
NOX_SALIENCE_MODE=shadow         # flip to 'active' only after 7d shadow + eval gate
NOX_LANG_AWARE_RRF=1
NOX_SEARCH_LOG_TEXT=0            # set to 1 for eval harness runs only

# ── Confidence (L3) — defaults are safe ───────────────────────────────────
NOX_RANKING_CONFIDENCE=disabled
NOX_CONFIDENCE_OBSERVED=0.95
NOX_CONFIDENCE_INFERRED=0.65
NOX_CONFIDENCE_DERIVED=0.75
NOX_CONFIDENCE_GRAPHIFY=0.70
NOX_CONFIDENCE_USER_CANONICAL=1.00
NOX_CONFIDENCE_USER_REFUTED=0.05
NOX_CONFIDENCE_ACTIVE_FLOOR=0.30
NOX_CONFIDENCE_DECAY_HALFLIFE_DAYS=-1

# ── Conflict detection (L2) ───────────────────────────────────────────────
NOX_CONFLICT_MODE=disabled
# NOX_CONFLICT_SCAN_CRON="0 3 * * *"

# ── L4 regex extraction ───────────────────────────────────────────────────
NOX_L4_REGEX_ENABLED=0
NOX_L4_SKIP_GEMINI=0
NOX_L4_AUTO_RENAME=0             # DESTRUCTIVE — leave off

# ── Viewer ────────────────────────────────────────────────────────────────
NOX_VIEWER_SHOW_QUERY=0
# NOX_VIEWER_AUTH_TOKEN=         # set if viewer is network-accessible

# ── Safety ────────────────────────────────────────────────────────────────
NOX_ALLOW_NO_SNAPSHOT=0          # EMERGENCY ONLY — document before enabling
```

---

## See also

- [`docs/QUICKSTART.md`](QUICKSTART.md) — copy-paste tutorial from install to first query
- [`CONTRIBUTING.md`](../CONTRIBUTING.md) — shadow discipline, testing requirements, branch conventions
- [`CLAUDE.md`](../CLAUDE.md) — critical operational rules (rule #3: model selection, rule #4: port, rule #5: ranking discipline, rule #6: destructive ops)
- [`docs/DECISIONS.md`](DECISIONS.md) — architectural decisions and explicit "NÃO FAZEMOS" (things we decided against)
