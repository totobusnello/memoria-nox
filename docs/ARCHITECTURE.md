# nox-mem — Architecture

> **Audience:** HN technical visitors, applied-IR researchers, infra engineers evaluating nox-mem before reading the paper.
> **Companion docs:** `paper/paper-tecnico-nox-mem.md` (formal), `docs/ROADMAP.md` (where it's going), `docs/DECISIONS.md` (why it looks like this).
> **Updated:** 2026-05-22 · System: nox-mem v3.7+ · Schema v10 · Single Node.js process · Single SQLite file.

---

## §1 TL;DR

**nox-mem is a pain-weighted hybrid memory system that runs as one Node.js process backed by one SQLite file.** Retrieval fuses three layers — FTS5 BM25, sqlite-vec dense (Gemini 3072d embeddings), and Reciprocal Rank Fusion at k=60 — over a salience-weighted scoring formula that biases toward recent + painful + important + frequently-accessed memories. A nightly Gemini KG extraction pipeline keeps ~15k entities and ~21k relations refreshed alongside the chunks, and a shadow-discipline rule keeps every scoring change behind a flag until ablation proves it on the eval harness.

```
Client (CLI · MCP · HTTP)
        ↓
   nox-mem-api :18802
        ↓
  ┌───────────────────────────┐
  │ SQLite single file        │
  │   ├ FTS5 (BM25)           │
  │   ├ sqlite-vec (3072d)    │
  │   └ KG tables             │
  └───────────────────────────┘
        ↕
   Gemini API (embeddings + KG extraction · the only network dependency)
```

---

## §2 System diagram

```
┌────────────────────────────────────────────────────────────────────────┐
│  CLIENTS                                                               │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────────┐    │
│  │  CLI         │   │  MCP server  │   │  HTTP API                │    │
│  │  26+ cmds    │   │  16 tools    │   │  /api/{health,search,    │    │
│  │  dist/       │   │  nox_mem_*   │   │       answer,kg,...}     │    │
│  │  index.js    │   │              │   │                          │    │
│  └──────┬───────┘   └──────┬───────┘   └────────────┬─────────────┘    │
│         └──────────────────┼────────────────────────┘                  │
└────────────────────────────┼───────────────────────────────────────────┘
                             │
                  ┌──────────▼──────────┐
                  │  nox-mem-api        │  Node.js + TypeScript
                  │  systemd unit       │  listens on :18802
                  │  (single process)   │  reads OPENCLAW_WORKSPACE
                  └──────────┬──────────┘
                             │
        ┌────────────────────┼─────────────────────────────┐
        │                    │                             │
   ┌────▼────────┐    ┌──────▼────────┐         ┌──────────▼─────────┐
   │ FTS5 BM25   │    │ sqlite-vec    │         │ KG (entities +     │
   │ chunks_fts  │    │ vec_chunks    │         │ relations) — built │
   │ Unicode-    │    │ 3072d Gemini  │         │ by nightly cron    │
   │ aware       │    │ cosine        │         │ via Gemini extract │
   └────┬────────┘    └──────┬────────┘         └──────────┬─────────┘
        │                    │                             │
        └──────────RRF──────┴─── boosts ── salience ───────┘
                         (k=60 fusion → top-K)
                             │
                             ▼
                  ┌──────────────────────┐
                  │  /api/search         │
                  │  /api/answer (RAG)   │
                  │  /api/brief (priming)│
                  └──────────────────────┘

External:
  ┌────────────────────────────────────────┐
  │ Gemini API                             │
  │   • gemini-embedding-001 (3072d)       │
  │   • gemini-2.5-flash-lite (default)    │
  │   • gemini-2.5-flash (KG extraction)   │
  └────────────────────────────────────────┘

Observability:
  ┌────────────────────────────────────────┐
  │ F10 Phase A — /observability/health.html (prod snapshot + delta_24h) │
  │ F10 Phase B — /observability/evals.html  (gates G5..G12 annotated)    │
  │ Crons       — schema-invariants */15min, healthcheck */15min,         │
  │               daily-maintenance 06h BRT, nightly-maintenance Sun      │
  └────────────────────────────────────────┘
```

All client surfaces hit the same process and the same SQLite file. There is no message bus, no separate vector service, no Postgres. Failure modes collapse to two: "the file is healthy" or "the file isn't" — the canary in §7 watches exactly that.

---

## §3 Storage layer

One SQLite file (`${OPENCLAW_WORKSPACE}/tools/nox-mem/nox-mem.db`, WAL mode), accessed exclusively through better-sqlite3 from the API process. The file is the system of record; everything else is derivable.

**Tables (schema v10):**

| Table | Purpose |
|---|---|
| `chunks` | Source of truth: text, source path, section, retention_days, pain, importance, access_count, created_at, last_seen_at, source_type. |
| `chunks_fts` | FTS5 virtual table over `chunks.text` (Unicode tokenizer, BM25 ranking). |
| `vec_chunks` | sqlite-vec virtual table: `embedding FLOAT[3072]`. |
| `vec_chunk_map` | Bridge `chunks.id ↔ vec_chunks.rowid`. |
| `kg_entities` | 17 canonical types (D52 plural-normalisation), `description`, `source_type`. |
| `kg_relations` | FK source/target + predicate + extraction_method. |
| `ops_audit` | Append-only log of destructive ops (W2-1 triggers block DELETE / UPDATE on terminal rows). |
| `search_telemetry` | Per-query latencies + result-set hashes (opt-in: `NOX_SEARCH_LOG_TEXT=1`). |

**Triggers worth knowing:**
- `trg_chunks_delete_cascade` — deleting a chunk wipes its vector + map row. Never drop this.
- `ops_audit` append-only triggers (W2-1) — DELETE is hard-blocked; UPDATE blocked on `success`/`failed`/`crashed` rows.

**Schema evolution:**

| Version | Added | Date |
|---|---|---|
| v7 | `chunks` + FTS5 + sqlite-vec + KG (baseline shipped) | 2026-Q1 |
| v8 | `retention_days` (typed TTL per source_type) | 2026-04 |
| v9 | `pain` REAL (severity 0.1 → 1.0) | 2026-04 |
| v10 | `section` + `section_boost` (entity-file 3-section format) | 2026-04-23 |

The schema-invariants canary (§7) verifies four hard invariants every 15 minutes: `vec_chunk_map` bijection vs `chunks`, no orphan `vec_chunks` rows, FK integrity in `kg_relations`, and presence of `trg_chunks_delete_cascade`.

---

## §4 Retrieval pipeline

The retrieval path is where every performance number lives. It is a deterministic series of seven steps over the same SQLite file:

```
query string
   │
   ▼
[1] sanitize  ── Unicode whitelist (/[^\p{L}\p{N}\s]/gu) — keeps Portuguese
   │              accents + CJK; strips punctuation that breaks FTS5 MATCH.
   ▼
[2] FTS5 BM25 ──► ranked list L1   (chunks_fts MATCH, ~1–5 ms cold)
   │
[3] embed(query) via Gemini ──────────────────────────────────┐
   │   gemini-embedding-001 → 3072d float32                    │
   ▼                                                           │ ~700–900 ms
[4] sqlite-vec cosine ──► ranked list L2  (vec_chunks)         │ (network bound)
   │                                                           │
   ▼                                                           │
[5] RRF fusion  ── score(d) = Σ_l 1 / (k + rank_l(d)), k=60   ◄┘
   │              produces a single fused order F.
   ▼
[6] boost stack (additive, never multiplicative — rule #5):
       • section_boost      (compiled 2.0 · frontmatter 1.5 · timeline 0.8)
       • source_type_boost  (G8: live, additive)
       • Hard Mutex G10d    (conditional: threshold=2 entity hits in query;
                             off-switch NOX_DISABLE_CONDITIONAL_MUTEX=1)
   │
   ▼
[7] salience score (see §5) and return top-K (default K=10).
```

**Why three layers and not two.** BM25 wins keyword-heavy queries (proper nouns, code, IDs). Dense Gemini wins natural-language paraphrase. RRF is rank-based, so it doesn't need score calibration between layers and is robust to either layer returning garbage on a given query — the other layer's signal dominates. The G-series ablations (G3 → G12) consistently show neither layer alone matches the fused order; the eval dashboard in §7 annotates every gate.

**Why additive boosts.** Multiplicative boost stacks were the root cause of v3.4 incident — small wins compounded into runaway scores on edge cases. Rule #5 (CLAUDE.md) now forbids multiplicative composition in any "fix" commit; new boosts ship in shadow mode behind a flag (§5) until an ablation lands.

Typical latency budget at prod scale (~95k chunks, 2026-06-04):
`p50 ≈ 940 ms · p95 ≈ 2.3 s · p99 ≈ 2.5 s` — dominated by the Gemini embed round-trip in step [3]. Local-only paths (FTS5 + cached embed) run sub-10ms.

---

## §5 Salience formula (pain-weighted)

After fusion + boosts, candidates are scored against a salience function that biases retrieval toward memories the user is likely to need again. The formula is intentionally simple and additive:

```
salience(d) = W_RECENCY    × recency_decay(last_seen_at)
            + W_PAIN       × pain_score(pain)
            + W_IMPORTANCE × importance_norm(importance)
            + W_ACCESS     × access_count_norm(access_count)
```

**Default weights (G-series ablations, current prod):**

| Term | Weight | Intuition |
|---|---|---|
| `W_IMPORTANCE` | **0.55** | Curator-assigned signal (0–1). Highest weight — explicit > inferred. |
| `W_ACCESS` | **0.20** | `log(1 + access_count)`, capped. Frequently-used wins quietly. |
| `W_RECENCY` | **0.15** | `exp(-age_days / retention_days)` — typed half-life per `source_type` (feedback/person never decay, lesson 180d, decision/project 365d, default 90d). |
| `W_PAIN` | **0.10** | `pain ∈ [0.1, 1.0]` — incidents and prod-outages outrank trivia. |

**Modes (`NOX_SALIENCE_MODE`):**
- `active` (default in prod since G10) — salience contributes to ranking.
- `shadow` — salience is computed and exposed at `/api/health.salience` but does **not** affect rank. Every formula change ships here first.
- `off` — bypass entirely (used for ablations).

The shadow-mode discipline is non-negotiable: G7 (2026-05-20) showed isolated salience contributes Δ +0.5% nDCG on the 500-question entity-eval corpus — within noise. The signal becomes material on the larger 68k-chunk g5.db corpus, which is exactly why shadow → active gating exists. See `[[shadow-mode-for-ranking-changes]]`.

---

## §6 Knowledge Graph (KG)

A derived layer over `chunks`, refreshed by a nightly cron. The KG is not on the hot path of `/api/search`; it powers `/api/kg/search`, `/api/kg/path` (relation walks), and disambiguation hints for `/api/answer`.

**Pipeline:**

```
nightly cron (Sunday + delta_24h on weeknights)
   │
   ▼
[1] regex-first extractor — fast, deterministic, covers ~70% of entity types
   │                        (people, projects, decisions, files, dates).
   ▼
[2] Gemini fallback — gemini-2.5-flash for chunks the regex layer didn't
   │                  cover. Optional via NOX_KG_EXTRACT_MODE=regex_first|gemini|both.
   ▼
[3] normalize → 17 canonical entity types (D52 plural-normalisation)
   │   person · project · decision · lesson · feedback · system · ...
   ▼
[4] upsert into kg_entities (dedup by canonical name)
[5] LLM-summarize duplicate descriptions when density ≥10×
   │   (LightRAG-inspired pattern, ref'd in [[lightrag-kg-incremental-merge-pattern]])
   ▼
[6] kg_relations — FK ids (source_entity_id, target_entity_id) + predicate +
                   extraction_method. NEVER inline strings — see rule.
```

**Current scale (prod):** ~15k entities · ~21k relations · 17 canonical types.

**Query surface:** `/api/kg/search?q=…` (entity name + fuzzy), `/api/kg/path?from=A&to=B` (BFS over relations capped at depth 4).

**Watchpoint:** D52 L4 deployed 2026-05-21 — first plural-normalisation cron fires Sun 2026-05-24 23:00 UTC. `scripts/l4-watchpoint-check.sh` validates Mon morning that `kg_relations.extraction_method` is populated (was 100% NULL pre-cron).

---

## §7 Observability

Three independent surfaces, all read-only:

**F10 Phase A — Prod Health snapshot** (`/observability/health.html`, deployed 2026-05-21)
- Live `/api/health` snapshot: chunk count, vectorCoverage %, sectionDistribution, salience histogram, port + uptime.
- `delta_24h` indicators (chunks ingested, ops_audit rows, KG entity growth) with green/yellow/red thresholds.
- One page, no auth, designed to be the first link in an incident.

**F10 Phase B — Eval dashboard** (`/observability/evals.html`, merged 2026-05-21)
- nDCG@10 / MRR over time, annotated with every gate ABLATION: **G5 V3 · G6 · G8 · G10 · G10b · G10c · G10d · G11 · G12 R3**.
- Per-method and per-category breakdowns (single-hop, multi-hop, temporal, adversarial, open-domain).
- Doubles as the public artifact for the launch — every claim in the paper traces back to a gate row here.

**Schema-invariants canary** (`scripts/check-schema-invariants.sh`, cron `*/15 * * * *`)
- Four invariants checked every 15 minutes; non-zero exit pages stderr via systemd journal.
- Cheapest possible signal that "the SQLite file is still well-formed".

**Healthcheck** (cron `*/15 * * * *`, fixed 2026-05-20 — see `[[cron-path-must-include-sbin]]`)
- ICMP ping + `curl :18802/api/health` from a remote watchdog.
- Caught the 2026-05-20 Hostinger floating-IP swap within 30 min (`[[vps-ip-change-2026-05-20]]`).

**Maintenance crons:**
- `daily-maintenance` — 06h BRT, KG delta_24h + telemetry roll-up.
- `nightly-maintenance` — Sundays, full KG re-extract + VACUUM INTO archive.

Every destructive op (reindex / consolidate / compact / crystallize / kg-prune) writes to `ops_audit` via `withOpAudit()` with a pre-op `VACUUM INTO` snapshot to `/var/backups/nox-mem/pre-op/`. Recovery via `safeRestore()`. Override flag `NOX_ALLOW_NO_SNAPSHOT=1` exists for emergencies (disk full) and is logged.

---

## §8 Deployment topology

```
┌─────────────────────────────────────────────────────────────┐
│  Hostinger VPS — Ubuntu 22.04                               │
│  8 cores · 16 GB RAM · NVMe                                 │
│  IP: 187.77.234.79  (floating; previous: 45.43.85.86)       │
│                                                             │
│  ┌─────────────────────────────────────────────────┐        │
│  │ systemd: nox-mem-api.service                    │        │
│  │   ExecStart=/usr/bin/node dist/index.js serve   │        │
│  │   listens on 127.0.0.1:18802                    │        │
│  │   user=nox-mem, dir=${OPENCLAW_WORKSPACE}       │        │
│  └─────────────────────────────────────────────────┘        │
│                                                             │
│  ┌─────────────────────────────────────────────────┐        │
│  │ inotifywait watcher (entity files → ingest)     │        │
│  │ 15s debounce, routes via ingestRouter           │        │
│  └─────────────────────────────────────────────────┘        │
│                                                             │
│  ┌─────────────────────────────────────────────────┐        │
│  │ cron table (root)                               │        │
│  │   */15 * * * *  check-schema-invariants.sh      │        │
│  │   */15 * * * *  healthcheck.sh                  │        │
│  │   0   06 * * *  daily-maintenance.sh            │        │
│  │   0   23 * * 0  nightly-maintenance.sh          │        │
│  │   0   02 * * *  backup-all.sh                   │        │
│  └─────────────────────────────────────────────────┘        │
│                                                             │
│  Storage: /root/.openclaw/workspace/tools/nox-mem/          │
│           ├ nox-mem.db          (WAL mode, single file)     │
│           ├ nox-mem.db-wal                                  │
│           └ nox-mem.db-shm                                  │
│  Backups: /var/backups/nox-mem/  (daily 02h + per-op)       │
└─────────────────────────────────────────────────────────────┘
```

There is intentionally no horizontal scaling story. Scaling out means **another VPS with another file**, federated only at query time. The single-file invariant is the reason recovery is fast, audits are auditable, and the canary stays cheap.

---

## §9 Configuration (.env reference)

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `GEMINI_API_KEY` | **yes** | — | Embeddings + KG extraction. Only secret nox-mem needs. |
| `NOX_API_PORT` | no | `18802` | HTTP API listen port (Chrome squats on 18800 — don't change). |
| `NOX_DB_PATH` | no | `${OPENCLAW_WORKSPACE}/tools/nox-mem/nox-mem.db` | Override DB location (used by eval harness — must be set explicitly per `[[eval-harness-must-explicit-isolate-db]]`). |
| `NOX_SALIENCE_MODE` | no | `active` | `active` · `shadow` · `off`. Shadow ships every formula change first. |
| `NOX_MUTEX_QUERY_ENTITY_THRESHOLD` | no | `2` | G10d Hard Mutex threshold — number of entity hits required to engage mutex carve-out. |
| `NOX_DISABLE_CONDITIONAL_MUTEX` | no | unset | Off-switch for the G10d Hard Mutex (rollback in seconds). |
| `NOX_KG_EXTRACT_MODE` | no | `regex_first` | `regex_first` · `gemini` · `both`. Controls KG extraction pipeline. |
| `NOX_ENTITY_DIRS_PLURAL` | no | unset | D52 opt-in: treat `entities/decisions/` as canonical (singular `decision/` is the legacy default). |
| `NOX_ALLOW_NO_SNAPSHOT` | no | unset | Emergency only — allows destructive op without pre-op snapshot. Logged. |
| `NOX_ALLOW_PROD_INGEST` | no | unset | Guards eval harness from accidentally writing to prod DB. |
| `NOX_SEARCH_LOG_TEXT` | no | unset | Opt-in: log raw query text into `search_telemetry`. |
| `OPENCLAW_WORKSPACE` | yes | — | Root workspace path (CLI honors this; never hardcode). |

Pre-flight rule (`CLAUDE.md` §1): every cron / SSH / script that calls `nox-mem` CLI **must** do `set -a; source /root/.openclaw/.env; set +a` first — vectorize/kg-extract fail silently without it.

---

## §10 Trust boundaries & security model

**Data flow:**
```
local files (Obsidian + repos)  ──ingest──►  SQLite (local)
SQLite chunk text  ──embed──►  Gemini API  ──3072d vector──►  SQLite (local)
SQLite chunk text  ──extract──►  Gemini API  ──entities/relations──►  SQLite (local)
```

**What leaves the machine:** only chunk text routed to the Gemini API for embedding or KG extraction. No telemetry, no analytics, no third-party storage. If `GEMINI_API_KEY` is revoked, retrieval keeps working on already-embedded chunks — only new ingest stalls.

**API surface:**
- `/api/health`, `/api/search`, `/api/kg/*`, `/api/answer`, `/api/brief` — **read-only** (brief escreve apenas em `brief_log` própria), currently unauthenticated, designed to bind to `127.0.0.1`. Reverse proxy (Caddy/nginx) handles TLS + auth at the edge.
- `POST /api/crystallize`, `POST /api/crystallize/validate` — write paths. Currently **trusted-localhost** (same-process). Admin auth + token scopes are a Q1 2026 deliverable (`docs/ROADMAP.md` → v2).

**Storage hardening:**
- `ops_audit` is append-only at the DB level (W2-1 triggers — CWE-693 mitigation). DELETE always errors; UPDATE on terminal rows errors.
- Pre-op snapshots live in `/var/backups/nox-mem/pre-op/` with ACL `0600`, dir `0700`, symlink-aware path validation via `realpathSync`.
- Snapshot retention 7 days; full daily backups go to `/var/backups/nox-mem/daily/` at 02h BRT.

**Not handled in v1 (deferred to nox-supermem):**
- PII detection / redaction at ingest.
- Multi-tenant isolation (the v1 model is one workspace per VPS).
- Field-level encryption at rest (filesystem-level via VPS host is the current boundary).

**Acceptance note.** The Gemini API key is the only externally-trustable secret in the system. Risk of key compromise is accepted at v1 (see `[[user-accepts-gemini-key-risk]]`); rotation cost is low (rebuild embeddings) and detection is via Gemini console quota anomalies.

---

## §11 References

| Resource | Where |
|---|---|
| Paper (formal architecture + benchmarks) | `paper/paper-tecnico-nox-mem.md` |
| Specs (per-feature) | `specs/*.md` |
| Decisions log (why X, why not Y) | `docs/DECISIONS.md` |
| Roadmap | `docs/ROADMAP.md` |
| Incident log | `docs/INCIDENTS.md` |
| Audits (G-series, opsAudit, schema) | `audits/*.md` |
| Eval harness (Q4 comparison) | `eval/q4-comparison/` |
| Observability dashboards | `/observability/health.html` · `/observability/evals.html` |
| Source tree | `src/` (TypeScript) · `dist/` (compiled, runtime entry `dist/index.js`) |

For the architectural narrative behind specific decisions — Q/A/P pillars, shadow-discipline rule, single-file invariant, additive-only boost rule — see `docs/DECISIONS.md`. For the live state and next action, see `docs/HANDOFF.md`.
