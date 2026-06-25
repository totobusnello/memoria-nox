# The 3 Primitives of nox-mem

> **"3 primitives, 1 file, any LLM."**
>
> nox-mem exposes three retrieval primitives, all backed by the same SQLite store
> (chunks + FTS5 + sqlite-vec + KG). Each primitive is surfaced identically across
> three transport layers — CLI, HTTP API, MCP — so any LLM, any agent runtime, or
> any human at a shell can call them.

---

## Why three primitives, not more

The design space for "memory" is huge — graph traversal, summarization, reflection,
crystallization, KG-path expansion, salience tuning, cross-agent fan-out. We've
shipped all of those, but they're **internal mechanisms**, not user-facing
contracts. The contract surface is intentionally small:

| Primitive | Question it answers | Latency target |
|---|---|---|
| `search` | "Show me chunks matching X" | < 1s p95 (hybrid) |
| `answer` | "Synthesize an answer to X, citing memory" | < 5s p95 (Gemini Flash Lite) |
| `temporal filter` | "Restrict X to a time window" | adds < 5ms (SQL pre-filter) |

Everything else (KG path, reflect, cross-search, crystallize) composes from these
three. If you can express your question as `search` + optional `answer` + optional
temporal scope, you don't need any of the advanced verbs.

This is the **closure property** that makes nox-mem composable: a single short
contract, three transports, deterministic semantics.

---

## Primitive 1 — `search` (hybrid retrieval)

The core retrieval primitive. Combines FTS5 BM25 + Gemini semantic (3072d) +
Reciprocal Rank Fusion (k=60), with optional Hard Mutex section gating and
SOURCE_TYPE_BOOST overlays. Returns ranked chunks with scores, evidence,
and provenance.

### CLI

```bash
nox-mem search "what is the salience formula?"
nox-mem search "deployment decisions" --limit 20
nox-mem search "OpenClaw fixes" --no-hybrid       # FTS5-only fast path
nox-mem search "schema migration" --as-of 2026-05-01
nox-mem search "recent lessons" --changed-since 7d
```

### HTTP API

```bash
curl "http://localhost:18802/api/search?q=salience+formula&limit=10"

curl -X POST http://localhost:18802/api/search \
  -H 'Content-Type: application/json' \
  -d '{"q":"schema migration","as_of":"2026-05-01","limit":10}'
```

### MCP

```json
{
  "name": "nox_mem_search",
  "arguments": { "query": "deployment", "limit": 10, "as_of": "2026-04-01" }
}
```

### What you get back

```json
{
  "results": [
    {
      "id": 42017,
      "text": "Pain-weighted ranking multiplies recency × pain × importance...",
      "source_file": "memory/entities/decision/d48-implement-pain-weighted.md",
      "section": "compiled",
      "score": 8.42,
      "match_type": "hybrid",
      "created_at": "2026-05-19T14:22:01.000Z",
      "updated_at": "2026-05-21T09:13:48.000Z"
    }
  ],
  "latency_ms": 940,
  "total_matched": 17,
  "query_log_id": "qlog_7f8a..."
}
```

---

## Primitive 2 — `answer` (grounded RAG with citations)

Retrieve, then synthesize. Wraps `search` internally with `topK=10` by default,
builds a prompt with the retrieved context, calls the configured LLM
(`gemini-2.5-flash-lite` by default per **D41**), parses citations inline,
and returns the answer plus the sources used.

**Anti-hallucination guard:** answers must cite chunk IDs as `[chunk_<id>]`.
If the model emits a citation pointing to a chunk that wasn't retrieved,
the answer is rejected and retried once with a stricter prompt. After the
second failure, `AnswerError('hallucination_after_retry')` is thrown rather
than returning unsafe content.

**Empty retrieval short-circuit:** if `search` returns zero chunks, we return
the canonical "I have no memory matches for this question." without ever
spending an LLM call.

### CLI

```bash
nox-mem answer "how does pain affect ranking?"
nox-mem answer "what did we decide about Stripe vs Hotmart?" --top-k 15
nox-mem answer "summarize last week's incidents" --json
```

### HTTP API

```bash
curl -X POST http://localhost:18802/api/answer \
  -H 'Content-Type: application/json' \
  -d '{"question":"how does pain affect ranking?","topK":10}'
```

Response:

```json
{
  "answer": "Pain weighting multiplies the salience score by a severity factor in [0.1, 1.0]. Trivial events score 0.1, while prod-outage-class events score 1.0 [chunk_42017]. The default for unscored chunks is 0.2 [chunk_42031].",
  "citations": [
    { "chunk_id": 42017, "source": "memory/entities/decision/d48-implement-pain-weighted.md", "score": 8.42 },
    { "chunk_id": 42031, "source": "specs/2026-05-19-pain-weighting.md", "score": 6.18 }
  ],
  "metadata": {
    "latency_ms": 1612,
    "tokens_in": 2840,
    "tokens_out": 87,
    "provider": "gemini",
    "model": "gemini-2.5-flash-lite",
    "retrieval_count": 10,
    "retry_count": 0
  }
}
```

### MCP

```json
{
  "name": "nox_mem_answer",
  "arguments": { "question": "how does pain affect ranking?", "topK": 10 }
}
```

### Environment

| Variable | Default | Purpose |
|---|---|---|
| `NOX_GEMINI_MODEL` | `gemini-2.5-flash-lite` | LLM for synthesis (D41 locked) |
| `GEMINI_API_KEY` | _required for live answer_ | Provider key |
| `NOX_ANSWER_TOP_K` | `10` | Default retrieval depth |
| `NOX_ANSWER_TIMEOUT_MS` | `4300` | Per-call deadline |

**Measured latency:** p95 `101.74ms` on the offline mock-LLM bench (PR #40,
42× under the 4.3s budget). Live p95 with Gemini Flash Lite ranges
`1.5s – 2.5s` depending on Gemini availability.

---

## Primitive 3 — Temporal filter (`--as-of` / `--changed-since`)

Time-travel and recency-window selectors. **Hard SQL pre-filter**, not a
ranking boost — chunks outside the window simply don't appear in results.
Layered onto `search` (and therefore `answer`) without changing any score.

This closes **Gap #2 (temporal decay)** of the Six Gaps reframe: most
agent-memory systems either ignore time entirely or bolt on opaque
recency-decay multipliers. nox-mem treats time as a **first-class
selector**: ask exactly the window you want, get back exactly that window.

### Semantics

| Flag | SQL semantics | Use case |
|---|---|---|
| `--as-of <date>` | `created_at <= date AND (deleted_at IS NULL OR deleted_at > date)` | Time-travel: "what did we know on date X?" |
| `--changed-since <date>` | `updated_at > date OR created_at > date` | Recency: "what's changed since date X?" |
| Both flags | AND of the two clauses | "Chunks that existed on `as-of` AND have been modified since `changed-since`" |

### Accepted date formats

- ISO 8601 full:   `2026-05-01T00:00:00Z`
- ISO 8601 date:   `2026-05-01`
- Relative:        `7d`, `1w`, `30d`, `2h`, `15m`

**Note:** `1mo` is NOT supported — use `30d`. (Documented in `src/lib/dates.ts`.)

### CLI

```bash
# Time-travel: what did the system look like on 2026-04-01?
nox-mem search "deployment decisions" --as-of 2026-04-01

# Recency: what changed in the last week?
nox-mem search "OpenClaw fixes" --changed-since 7d

# Combined: chunks that existed on 2026-05-01 AND were updated since
nox-mem search "schema migration" --as-of 2026-05-01 --changed-since 30d

# Works with --no-hybrid too (FTS5-only fast path)
nox-mem search "recent lessons" --changed-since 1w --no-hybrid
```

### HTTP API

```bash
# Query string (GET)
curl "http://localhost:18802/api/search?q=deployment&as_of=2026-04-01"
curl "http://localhost:18802/api/search?q=fixes&changed_since=7d"

# JSON body (POST)
curl -X POST http://localhost:18802/api/search \
  -H 'Content-Type: application/json' \
  -d '{"q":"schema","as_of":"2026-05-01","changed_since":"30d"}'
```

### MCP

```json
{ "name": "nox_mem_search",
  "arguments": { "query": "deployment", "as_of": "2026-04-01" } }

{ "name": "nox_mem_search",
  "arguments": { "query": "fixes", "changed_since": "7d" } }
```

### Architectural notes

- **No schema changes** — uses existing `chunks.created_at` and `chunks.updated_at`
  columns from schema v18.
- **No ranking changes** — the filter applies as a `WHERE` clause before scoring.
  This is distinct from the E13 temporal proximity boost (`NOX_TEMPORAL_PATH`),
  which **adds** a recency boost to rankings.
- **`deleted_at` guarded with `COALESCE`** — safe even if column doesn't exist
  in older schema versions.
- **`created_at IS NULL` treated as "always existed"** — legacy chunks without
  timestamps are not silently dropped.
- **KG paths NOT covered** — `kg_entities` and `kg_relations` do not have
  `created_at`/`updated_at` in schema v18. Temporal filtering applies to chunks
  only. KG-path temporal filtering deferred to a future spec.

---

## Composing the primitives

The three primitives compose orthogonally:

```bash
# search + temporal: time-windowed retrieval
nox-mem search "incidents" --as-of 2026-05-15 --changed-since 7d

# answer + temporal: grounded synthesis over a time window
nox-mem answer "what incidents happened last week?" --changed-since 7d

# answer + custom top-k: deeper retrieval before synthesis
nox-mem answer "explain the pain weighting evolution" --top-k 20
```

### Packaged composition: `GET /api/brief` (session priming)

`/api/brief` is not a fourth primitive — it is a packaged composition of
salience ranking + temporal filtering, designed for the Session Priming
Loop (spec `2026-06-04-session-priming-loop.md`): every session starts
with a compact pointer digest of the most salient knowledge for its scope.

```bash
# top-10 by salience for a project scope (JSON)
curl 'http://127.0.0.1:18802/api/brief?scope=memoria-nox'

# agent persona refinement + plain text, stdout-ready for SessionStart hooks
curl 'http://127.0.0.1:18802/api/brief?scope=global&agent=cipher&format=text'

# compose with recency window (same grammar as --changed-since)
curl 'http://127.0.0.1:18802/api/brief?scope=NUVIVI&since=30d&n=5'
```

Invariants: read-only over `chunks`; serving tracked in `brief_log` only —
`access_count` stays organic. Budget ≤ ~1,200 tokens (pointer pattern:
fetch details on demand via `search`).

Every advanced verb in nox-mem (`reflect`, `cross-search`, `kg-path`,
`crystallize`, …) is implemented internally as a sequence of these three
primitives. If you're writing an agent, you can build any retrieval
workflow you need from just these three calls.

---

## Cross-reference

| Layer | Spec / source |
|---|---|
| **`search` (hybrid)** | [`specs/2026-03-14-nox-memory-system-design.md`](../specs/2026-03-14-nox-memory-system-design.md), `paper/paper-tecnico-nox-mem.md` §4 |
| **`answer` (P1)** | [`staged-P1/README.md`](../staged-P1/README.md), PRs #3 #18 #31 #34 #40 #114 #283 |
| **Temporal (P3)** | [`staged-P3/DEPLOY.md`](../staged-P3/DEPLOY.md), PRs #2 #167 |
| **E13 temporal boost (distinct from P3 filter)** | [`staged-temporal-spike/edits/temporal-retrieval.ts`](../staged-temporal-spike/edits/temporal-retrieval.ts) |

---

## Tagline lineage

**"3 primitives, 1 file, any LLM."**

- **3 primitives:** `search` + `answer` + temporal filter — the entire user-facing contract.
- **1 file:** the SQLite database (`nox-mem.db`) on your disk. No external service,
  no proprietary index, no vendor cluster. You can copy it, encrypt it, or burn it.
- **Any LLM:** the `answer` primitive abstracts the provider via the `LLMProvider`
  interface. Gemini is the default; OpenAI, Anthropic, and local providers
  (Ollama, vLLM) are swappable via env config without code changes.
