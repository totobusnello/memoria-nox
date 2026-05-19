# P1 Implementation Kickoff — Answer Primitive

**Doc type:** Implementation task breakdown (not re-spec)
**Owner:** Engineering executor (post PR #3 merge)
**Date:** 2026-05-18
**Status:** READY-TO-EXECUTE
**Sprint:** First post-merge sprint per D41 #5
**Tagline:** *Pain-weighted hybrid memory with shadow discipline — yours by design.*

---

## 0. Cross-Reference

| Artifact | Location |
|---|---|
| P1 canonical spec | [PR #3](https://github.com/totobusnello/memoria-nox/pull/3) → `specs/2026-05-17-P1-answer-primitive.md` (812 lines) |
| D41 decision (default model + sprint order) | `docs/DECISIONS.md` §2026-05-18 madrugada |
| A3 provider abstraction (optional dep) | [PR #8](https://github.com/totobusnello/memoria-nox/pull/8) → `specs/2026-05-17-A3-provider-abstraction.md` |
| L3 schema candidate (telemetry alignment) | [PR #15](https://github.com/totobusnello/memoria-nox/pull/15) — schema v19 candidate |
| Shadow discipline regra crítica | `CLAUDE.md` §regras-críticas #5 |
| Morning review that produced D41 | `docs/MORNING-REVIEW-2026-05-18.md` |

**Read this doc instead of the 5,307-word spec for execution.** The spec stays canonical for design questions; this kickoff is the engineering work order.

---

## 1. Default Model — LOCKED (D41 #1)

| Lane | Model | Rationale |
|---|---|---|
| **Default** | `gemini-2.5-flash-lite` | Toto: "tem que ser barato e bom" — cost prioritized over peak quality |
| **Opt-in upgrade** | `gemini-2.5-flash` via `--model gemini-2.5-flash` CLI flag or `NOX_ANSWER_MODEL` env | Reserved for empirically validated quality issues post-Q1 |
| **Emergency fallback** | `claude-opus` (via OpenClaw) | Only via `NOX_ANSWER_FALLBACK_OPUS=1` env override; NOT a default chain link |

**Fallback chain (P1 v1):** `flash-lite → flash → fail (HTTP 502)`. Opus is gated behind explicit env flag to prevent silent cost blowups.

**Implementation note:** Hardcoded default `'gemini-2.5-flash-lite'` in `src/lib/answer/config.ts`. NEVER fall back to `gemini-2.5-flash` (CLAUDE.md regra #3 — quota 3M/d estoura) without telemetry-driven justification.

---

## 2. Task Breakdown (dependency-ordered)

> 14 tasks. T1 unblocks T2-T7. T2-T7 unblock T8-T10. T11-T14 close the loop.

### T1 — Module skeleton (`src/lib/answer/`)

**Goal:** Create directory structure + empty TS files + `types.ts` with public interfaces.

**DoD:**
- [ ] `src/lib/answer/{index,retrieval,prompt,citation,telemetry,config,types}.ts` exist
- [ ] `__tests__/` subdir with empty `.test.ts` files
- [ ] `types.ts` defines `AnswerRequest`, `AnswerResponse`, `Citation`, `RetrievalContext`, `AnswerTelemetryRecord`
- [ ] `npm run build` passes (no `any`, no implicit-any)
- [ ] `index.ts` re-exports public API: `answer()`, `AnswerRequest`, `AnswerResponse`

**Est:** 1.5h

### T2 — Retrieval wrapper (`retrieval.ts`)

**Goal:** Single entry `retrieve(question, opts)` that calls existing hybrid search, dedupes chunks by `id`, truncates to `top_k`, formats context block with `[chunk_N]` markers.

**DoD:**
- [ ] Calls existing `hybridSearch()` from `src/search/hybrid.ts` (no reimplementation)
- [ ] Dedup by `chunk_id` (keep highest-score)
- [ ] Returns `{markerId, chunk_id, file_path, line_range, score, text}[]` with `markerId = "chunk_1".."chunk_N"`
- [ ] Token-budget pruning = **lowest-score first** (spec §5 step 4; NOT recency — see PR #3 critical decision #2)
- [ ] Honors `top_k` (default 8, range 1-20)
- [ ] Pure function: no DB writes, no LLM calls

**Est:** 3h

### T3 — Prompt template (`prompt.ts`)

**Goal:** Two functions: `buildSystemPrompt(provider)` + `buildUserPrompt(question, retrievalContext)`. Anti-hallucination clause + citation requirement.

**DoD:**
- [ ] System prompt ~380 tokens, parametrized per provider (Gemini vs OpenAI vs Anthropic markdown quirks)
- [ ] User prompt injects `[chunk_N]` blocks verbatim from T2 output
- [ ] Explicit citation rule: "Cite every factual claim with `[chunk_N]`. If no chunk supports it, say 'unknown' — do not invent."
- [ ] Stricter retry variant (`buildRetryPrompt`) per spec §8
- [ ] Unit tests: deterministic snapshot of assembled prompt given fixed inputs

**Est:** 2h

### T4 — LLM call with provider abstraction (`provider.ts`)

**Goal:** Function `callLLM(messages, opts)` that hides Gemini vs OpenAI vs Anthropic. Use A3 module if PR #8 merged before P1 starts; otherwise direct Gemini call with A3-compatible interface.

**DoD:**
- [ ] If A3 merged: `import { llm } from '../provider'` (A3 module); no Gemini SDK in `answer/`
- [ ] If A3 NOT merged: direct `@google/genai` call wrapped in `LlmProvider` interface that matches A3 spec §3 (`call(messages, {model, max_tokens, temperature, json_mode}) → {text, tokens_in, tokens_out, finish_reason}`)
- [ ] Default `model = 'gemini-2.5-flash-lite'` (per D41 #1)
- [ ] Env override: `NOX_ANSWER_MODEL` wins over default
- [ ] Surfaces `finish_reason` so caller can detect truncation
- [ ] Timeout: 15s hard (configurable via `NOX_ANSWER_TIMEOUT_MS`)

**Est:** 3h (4h if A3 not merged)

### T5 — Citation extraction (`citation.ts`)

**Goal:** Parse `[chunk_N]` markers from LLM output. Validate every marker exists in retrieval set. Return `Citation[]` mapped to real `(chunk_id, file_path, line_range)`.

**DoD:**
- [ ] Regex: `/\[chunk_(\d+)\]/g` (no surprises — markers are bracketed integers)
- [ ] Validates every parsed N is in `1..retrievalSet.length`
- [ ] Returns `{markerId, chunk_id, file_path, line_range}[]` (text NOT included — clients fetch via separate API if needed)
- [ ] Out-of-range markers → flagged as `hallucinated_markers` in failure path
- [ ] Pure function, no I/O

**Est:** 1.5h

### T6 — Anti-hallucination retry-once-then-fail

**Goal:** Detect hallucinated markers → rebuild with stricter retry prompt → if still bad, return HTTP 422 / exit 4 with structured failure.

**DoD:**
- [ ] After T5, if `hallucinated_markers.length > 0` → call `callLLM` once with `buildRetryPrompt()`
- [ ] If retry still hallucinates → return failure response with `failure_reason: 'hallucination_after_retry'`
- [ ] NO retry-N loop (spec critical decision #3)
- [ ] Zero citations case handled: if zero `[chunk_N]` markers AND retrieval set non-empty → also triggers retry (suspect lazy LLM)
- [ ] Logs both attempts to `answer_telemetry` (`retry_count=0` initial + `retry_count=1` retry)

**Est:** 2h

### T7 — Telemetry table + insert (`telemetry.ts`)

**Goal:** Create `answer_telemetry` table (schema bump v11 — coordinate with L3 if v19 lands first); function `recordAnswer(record)` inserts row.

**DoD:**
- [ ] Migration script in `src/migrations/v11-answer-telemetry.sql` (or v19 if L3 schema ships first; align column names)
- [ ] `recordAnswer()` uses `withOpAudit()` ONLY if write touches `chunks`/`kg_*` (it doesn't — so direct INSERT is fine; see Open Q #1)
- [ ] All rows inserted even on failure (failure modes captured)
- [ ] Insert is non-blocking from user perspective (fire-and-forget OK, but error-logged)
- [ ] PII hygiene: `question_hash = sha256(question)` only; raw question opt-in via `NOX_ANSWER_LOG_QUESTION=1` (defaults OFF)

**Schema (see §5 for full DDL).**

**Est:** 2h

### T8 — CLI command (`src/cli/answer.ts`)

**Goal:** `nox-mem answer "<question>" [--top-k N] [--model X] [--json] [--no-citations]`.

**DoD:**
- [ ] Registered in `src/cli/index.ts` command dispatcher
- [ ] Default output: human-readable answer + numbered citation list at bottom
- [ ] `--json` flag → `AnswerResponse` JSON to stdout
- [ ] `--no-citations` suppresses inline `[chunk_N]` from rendered answer (still in telemetry)
- [ ] Exit codes: 0 success / 1 unknown error / 2 invalid args / 3 retrieval empty / 4 hallucination after retry / 5 LLM error
- [ ] Honors `OPENCLAW_WORKSPACE` env (CLAUDE.md regra global)
- [ ] Help text: `nox-mem answer --help` lists all flags with examples

**Est:** 2.5h

### T9 — HTTP endpoint (`src/api/answer.ts`)

**Goal:** `POST /api/answer` on port 18802. Reuse Fastify/Express plumbing of existing endpoints.

**DoD:**
- [ ] Route registered in `src/api/server.ts`
- [ ] Request validation via existing JSON schema validator (ajv or zod, whichever repo uses)
- [ ] Response shape matches §6 contract below
- [ ] HTTP status codes per spec §3: 200 ok / 400 bad input / 422 hallucination / 502 LLM unreachable / 503 retrieval empty
- [ ] Surfaces `X-Trace-Id` header for telemetry join

**Est:** 2h

### T10 — MCP tool (`src/mcp/tools/answer.ts`)

**Goal:** `nox_mem_answer` tool exposed via MCP server (in addition to existing 16 tools).

**DoD:**
- [ ] Tool definition + JSON schema per §6 contract
- [ ] Wrapped in same `answer()` call as CLI/HTTP — single code path
- [ ] Registered in `src/mcp/tools/index.ts`
- [ ] MCP `list_tools` shows it with description + arg schema
- [ ] Tested via Claude Code MCP session (manual smoke)

**Est:** 1.5h

### T11 — Integration tests with mock provider (`__tests__/integration.test.ts`)

**Goal:** End-to-end tests with stubbed LLM (deterministic responses) covering retrieval → prompt → LLM → citation → telemetry path.

**DoD:**
- [ ] Mock `LlmProvider` that returns canned responses
- [ ] 5+ scenarios: happy path, hallucination → retry success, hallucination → retry fail, zero retrieval, LLM timeout
- [ ] Asserts telemetry row inserted for each path with correct `failure_reason`
- [ ] No real Gemini calls — runs in CI without credentials
- [ ] All tests use `node:test` (repo standard)

**Est:** 3h

### T12 — E2E tests with real Gemini (flash-lite)

**Goal:** Run real Gemini calls against `nox-mem.db` testbed for 15 golden Q/A pairs.

**DoD:**
- [ ] Test script `scripts/p1-eval-golden.ts` runs 15 pairs (sourced per §7)
- [ ] Gated behind `RUN_E2E=1` env (skip in CI by default)
- [ ] Reports: citation accuracy %, hallucination rate, p50/p95 latency, total cost USD estimate
- [ ] Source `/root/.openclaw/.env` before invocation (CLAUDE.md regra #1)
- [ ] Persists results in `audits/2026-XX-XX-P1-golden-eval.md` template

**Est:** 4h (includes curating 15 pairs)

### T13 — Documentation

**Goal:** Quick Start in README, interfaces section in CLAUDE.md, error message reference.

**DoD:**
- [ ] README.md §Quick Start adds 4-line example: `nox-mem answer "What is salience formula?"`
- [ ] `CLAUDE.md` §Interfaces updates: CLI count `26+ → 27+`, MCP tools `16 → 17`, HTTP API adds `/api/answer`
- [ ] `docs/RUNBOOKS.md` adds entry: "Answer primitive — debugging hallucination retries"
- [ ] Example telemetry queries in `docs/RUNBOOKS.md` (per §8 below)

**Est:** 1.5h

### T14 — Performance benchmark

**Goal:** p50/p95 latency on golden Q/A set, separate from quality eval.

**DoD:**
- [ ] Script `scripts/p1-bench-latency.ts` runs each of 15 pairs 10× → 150 samples
- [ ] Reports p50/p95/p99 latency total + per-step (retrieval / LLM call / citation parse)
- [ ] Target: p95 < 2000ms with flash-lite (per DoD overall #1)
- [ ] If misses target → file follow-up audit, NOT block P1 merge (gate is correctness, not perf v1)

**Est:** 2h

---

## 3. File Structure (proposed)

```
src/lib/answer/
  index.ts            # public API: answer(req: AnswerRequest): Promise<AnswerResponse>
  config.ts           # default model + timeouts + env reads
  types.ts            # AnswerRequest, AnswerResponse, Citation, RetrievalContext, AnswerTelemetryRecord
  retrieval.ts        # T2 — hybrid search wrapper, dedup, format
  prompt.ts           # T3 — buildSystemPrompt, buildUserPrompt, buildRetryPrompt
  provider.ts         # T4 — LlmProvider interface + Gemini impl (or A3 re-export)
  citation.ts         # T5 — extract + validate markers
  telemetry.ts        # T7 — recordAnswer()
  __tests__/
    integration.test.ts   # T11
    citation.test.ts      # T5 unit
    prompt.test.ts        # T3 snapshot
    retrieval.test.ts     # T2 with mock hybridSearch

src/cli/answer.ts             # T8 — CLI dispatch
src/api/answer.ts             # T9 — HTTP route
src/mcp/tools/answer.ts       # T10 — MCP tool def

src/migrations/v11-answer-telemetry.sql   # T7 schema

scripts/p1-eval-golden.ts     # T12
scripts/p1-bench-latency.ts   # T14

audits/2026-XX-XX-P1-golden-eval.md   # T12 output template
```

---

## 4. Schema Delta — `answer_telemetry`

```sql
-- Migration: v11 (or v19 if L3 schema lands first — coordinate column names)
-- File: src/migrations/v11-answer-telemetry.sql

CREATE TABLE IF NOT EXISTS answer_telemetry (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  ts                INTEGER NOT NULL DEFAULT (unixepoch()),
  trace_id          TEXT NOT NULL,                       -- X-Trace-Id, joins HTTP/CLI/MCP
  question_hash     TEXT NOT NULL,                       -- sha256(question), PII-safe
  question_raw      TEXT,                                -- NULL unless NOX_ANSWER_LOG_QUESTION=1
  retrieval_count   INTEGER NOT NULL,                    -- chunks returned by hybrid search
  citation_count    INTEGER NOT NULL,                    -- markers validated in answer
  hallucinated_count INTEGER NOT NULL DEFAULT 0,        -- markers NOT in retrieval set
  latency_ms        INTEGER NOT NULL,                    -- total round-trip
  latency_retrieval_ms INTEGER,
  latency_llm_ms    INTEGER,
  latency_validate_ms INTEGER,
  provider          TEXT NOT NULL,                       -- 'gemini' / 'openai' / 'anthropic'
  model             TEXT NOT NULL,                       -- 'gemini-2.5-flash-lite' default
  tokens_in         INTEGER,
  tokens_out        INTEGER,
  fallback_used     INTEGER NOT NULL DEFAULT 0,          -- 0 = default lane, 1 = flash, 2 = opus
  retry_count       INTEGER NOT NULL DEFAULT 0,          -- 0 or 1 (per spec, no retry-N)
  failure_reason    TEXT,                                -- NULL on success; 'hallucination_after_retry' / 'llm_timeout' / 'retrieval_empty' / 'llm_error'
  schema_version    INTEGER NOT NULL DEFAULT 11
);

CREATE INDEX IF NOT EXISTS idx_answer_telemetry_ts ON answer_telemetry(ts);
CREATE INDEX IF NOT EXISTS idx_answer_telemetry_failure ON answer_telemetry(failure_reason) WHERE failure_reason IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_answer_telemetry_model ON answer_telemetry(model);
```

**L3 alignment note:** If PR #15 (L3 confidence schema v19) lands first, bump P1 to v19 too and add `confidence REAL` + `provenance_json TEXT` columns from L3 spec.

---

## 5. API Contracts

### TypeScript — `AnswerRequest` / `AnswerResponse`

```ts
// src/lib/answer/types.ts

export interface AnswerRequest {
  question: string;            // required, 1..2000 chars
  top_k?: number;              // default 8, range 1..20
  model?: string;              // default per config (flash-lite); overrides NOX_ANSWER_MODEL
  no_citations?: boolean;      // default false — strip [chunk_N] from rendered answer (still in citations[])
  trace_id?: string;           // optional client-supplied; server generates if omitted
  filters?: {                  // forwarded to hybridSearch
    type?: string[];
    section?: ('compiled' | 'frontmatter' | 'timeline')[];
    file_path_prefix?: string;
  };
}

export interface Citation {
  marker_id: string;           // 'chunk_1' .. 'chunk_N'
  chunk_id: number;            // real DB id
  file_path: string;
  line_range: [number, number];
  score: number;               // hybrid score from retrieval
}

export interface AnswerResponse {
  answer: string;              // LLM output with [chunk_N] markers inline (unless no_citations=true)
  citations: Citation[];       // ordered by first appearance in answer
  trace_id: string;
  model: string;
  retry_count: 0 | 1;
  retrieval_count: number;
  latency_ms: number;
  failure_reason?: 'hallucination_after_retry' | 'llm_timeout' | 'retrieval_empty' | 'llm_error';
}
```

### HTTP — `POST /api/answer`

| | |
|---|---|
| **Request body** | `AnswerRequest` (JSON) |
| **Response body** | `AnswerResponse` (JSON) |
| **Headers in** | `Content-Type: application/json`, optional `X-Trace-Id` |
| **Headers out** | `X-Trace-Id`, `X-Model-Used`, `X-Retry-Count` |
| **Status codes** | 200 ok / 400 invalid body / 422 hallucination after retry / 502 LLM unreachable / 503 retrieval empty / 504 timeout |

### MCP — `nox_mem_answer` tool

```json
{
  "name": "nox_mem_answer",
  "description": "Answer a question using nox-mem corpus with grounded citations [chunk_N]. Anti-hallucination guard built-in.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "question": { "type": "string", "minLength": 1, "maxLength": 2000 },
      "top_k": { "type": "integer", "minimum": 1, "maximum": 20, "default": 8 },
      "no_citations": { "type": "boolean", "default": false }
    },
    "required": ["question"]
  }
}
```

---

## 6. Test Plan — 15 Golden Q/A Pairs

**Source files (curate 1-2 pairs per file for coverage):**

| Pair # | Source entity | Sample question |
|---|---|---|
| 1-2 | `memory/entities/decision/nox-mem-v3.7.md` | "What is nox-mem schema v10?" / "Which retention defaults apply to lesson type?" |
| 3-4 | `memory/entities/feedback/feedback_use_voce_not_tu_in_portuguese.md` | "What is the PT-BR pronoun rule?" / "Why is 'tu' forbidden?" |
| 5-6 | `memory/entities/lesson/feedback_validate_features_with_db_not_logs.md` | "How should we validate features?" / "Why are logs alone insufficient?" |
| 7-8 | `memory/entities/project/project_openclaw_key_rotation_workflow.md` | "What is the key rotation workflow?" / "Which services restart after rotation?" |
| 9-10 | `docs/DECISIONS.md` §D40 | "What is the Q/A/P pivot?" / "Why was 80/20 retrieval rejected?" |
| 11-12 | `docs/DECISIONS.md` §D41 | "What is the default Gemini model for P1?" / "What is the sprint order?" |
| 13 | `CLAUDE.md` §regras-críticas | "What command sources env before nox-mem CLI?" |
| 14 | `specs/2026-05-17-P1-answer-primitive.md` (self-ref) | "What is the anti-hallucination retry policy?" |
| 15 | **Adversarial** — question not in corpus | "What is the capital of France?" → expected: zero citations + "unknown" |

**Hallucination synthetic test (T11 mock):**
- Mock LLM returns `"Salience uses formula X [chunk_99]"` where retrieval set has 8 chunks (no `chunk_99`)
- Expected: detect → retry once → still hallucinates → return 422 + `failure_reason: 'hallucination_after_retry'`

**Provider swap test (T12):**
- Run pair #1 with `NOX_ANSWER_MODEL=gemini-2.5-flash` (no code change)
- Assert: response uses flash, telemetry row shows `model='gemini-2.5-flash'` and `fallback_used=1`

---

## 7. Telemetry Queries (operator runbook)

```sql
-- Avg latency by hour (last 24h)
SELECT
  datetime(ts, 'unixepoch', 'localtime', 'start of hour') AS hour,
  COUNT(*) AS calls,
  AVG(latency_ms) AS avg_ms,
  printf('%.0f', AVG(latency_ms)) AS avg_str
FROM answer_telemetry
WHERE ts > unixepoch('now', '-24 hours')
GROUP BY hour
ORDER BY hour DESC;

-- Citation accuracy %
SELECT
  COUNT(*) AS total,
  SUM(CASE WHEN hallucinated_count = 0 THEN 1 ELSE 0 END) AS clean,
  printf('%.1f%%', 100.0 * SUM(CASE WHEN hallucinated_count = 0 THEN 1 ELSE 0 END) / COUNT(*)) AS accuracy
FROM answer_telemetry
WHERE ts > unixepoch('now', '-7 days')
  AND failure_reason IS NULL;

-- Retry rate
SELECT
  retry_count,
  COUNT(*) AS calls,
  printf('%.1f%%', 100.0 * COUNT(*) / (SELECT COUNT(*) FROM answer_telemetry WHERE ts > unixepoch('now', '-7 days'))) AS pct
FROM answer_telemetry
WHERE ts > unixepoch('now', '-7 days')
GROUP BY retry_count;

-- Failure mode distribution
SELECT
  COALESCE(failure_reason, 'success') AS outcome,
  COUNT(*) AS calls,
  printf('%.1f%%', 100.0 * COUNT(*) / (SELECT COUNT(*) FROM answer_telemetry WHERE ts > unixepoch('now', '-7 days'))) AS pct
FROM answer_telemetry
WHERE ts > unixepoch('now', '-7 days')
GROUP BY failure_reason
ORDER BY calls DESC;

-- Model distribution (verify flash-lite is dominant per D41)
SELECT model, COUNT(*) AS calls
FROM answer_telemetry
WHERE ts > unixepoch('now', '-7 days')
GROUP BY model;
```

Add these to `docs/RUNBOOKS.md` in T13.

---

## 8. Definition of Done — P1 Implementation Complete

1. `nox-mem answer "<q>"` returns answer + citations in **<2s p95 latency** with `gemini-2.5-flash-lite` (measured T14)
2. **All 14 tasks complete** with their per-task DoD met (T1-T14 checklists)
3. **15 golden Q/A pairs pass** with citation accuracy **≥95%** (T12 output)
4. **Anti-hallucination retry** triggers correctly on T11 synthetic test; **fails clearly with 422 + `failure_reason: 'hallucination_after_retry'`** after 1 retry
5. **Provider swap test** passes: `NOX_ANSWER_MODEL=gemini-2.5-flash` works without code change; telemetry shows `model='gemini-2.5-flash'`
6. **Telemetry table populated** for every call (success + failure); all 5 example queries in §7 return non-empty rows on synthetic test data
7. **Documentation updated**: README §Quick Start has example; `CLAUDE.md` §Interfaces section reflects 27+ CLI cmds + 17 MCP tools + `/api/answer`

---

## 9. Risks + Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| flash-lite quality insufficient for complex queries | Med | Med | Telemetry monitors citation accuracy %; `NOX_ANSWER_MODEL` env override exists; Q1 LongMemEval (Q2 sprint) validates empirically |
| Citation validation overhead bloats latency | Low | Low | Validation is regex + set membership (O(N) on tiny sets); only the retry path is expensive — and it's bounded to 1 retry |
| A3 provider abstraction (PR #8) not merged before P1 starts | Med | Low | T4 ships A3-compatible interface inline; refactor to import A3 is a trivial PR when A3 lands |
| Schema v11 collides with L3 v19 | Med | Med | T7 coordinates with L3 owner before migration; if L3 v19 lands first, P1 telemetry table bumps to v19 with extra L3 columns nullable |
| Gemini quota spike from E2E tests | Low | Low | T12 gated `RUN_E2E=1`; CI never invokes; 15 pairs × 10 runs = ~150 calls << 3M/d quota |
| Token-budget pruning kicks too aggressively on long entities | Med | Low | Default `top_k=8`; pruning thresholds tested in T2 unit; lowest-score-first (not oldest) per spec critical decision #2 |
| Silent telemetry insert failure masks bugs | Low | Med | T7 logs insert errors to stderr; non-blocking but visible |

---

## 10. Timeline Estimate

| Phase | Tasks | Hours |
|---|---|---|
| Foundation | T1, T2, T3 | 6.5h |
| Core logic | T4, T5, T6, T7 | 8.5h (9.5h if A3 not merged) |
| Surfaces | T8, T9, T10 | 6h |
| Validation | T11, T12, T14 | 9h |
| Polish | T13 | 1.5h |
| **Total** | **14 tasks** | **31.5h (32.5h if A3 not merged)** |

**Recommended sprint shapes:**
- **1 engineer, sequential:** 4-5 working days (8h × 4-5)
- **Swarm (2-3 executors parallel after T1):** 2-3 days (T2+T3+T4 parallel after T1; T8+T9+T10 parallel after T7; T11+T12+T14 parallel after T10)
- **Conservative buffer:** 1 week including review + golden pair curation iteration

---

## 11. Open Questions (non-blocking, resolve during impl)

1. **`withOpAudit()` for telemetry inserts?** — Recommend NO. `withOpAudit` is for destructive ops on `chunks`/`kg_*`. `answer_telemetry` is append-only telemetry. Direct INSERT with try/catch is sufficient. **Confirm with code-reviewer in T7 audit.**
2. **Cache answer responses (memo by `question_hash + retrieval_signature`)?** — Defer to v2. v1 measures latency without cache to expose real cost. If p95 misses target consistently post-deploy, add bounded LRU memo as fast-follow.
3. **Streaming response support?** — Defer to v2. CLI/MCP have no streaming UX yet; HTTP could but adds Server-Sent Events plumbing. P1 ships sync; streaming = follow-up spec.
4. **Should `--no-citations` strip markers from `answer` field but keep `citations[]` array populated?** — Recommend YES. `answer` is the rendered output; `citations[]` is the structured data. Decoupling is cleaner. **Confirmed in §5 contract.**

---

## 12. References

- **P1 spec:** [PR #3](https://github.com/totobusnello/memoria-nox/pull/3) — `specs/2026-05-17-P1-answer-primitive.md`
- **D41 (default model + sprint order):** `docs/DECISIONS.md` §2026-05-18 madrugada
- **D40 (Q/A/P pivot):** `docs/DECISIONS.md` §2026-05-17 noite
- **A3 provider abstraction:** [PR #8](https://github.com/totobusnello/memoria-nox/pull/8) — optional dep
- **L3 schema candidate:** [PR #15](https://github.com/totobusnello/memoria-nox/pull/15) — coordinate v11 vs v19
- **Shadow discipline:** `CLAUDE.md` §regras-críticas #5 — ranking changes ≠ "fix" commits
- **Morning review:** `docs/MORNING-REVIEW-2026-05-18.md` — context for D41
- **Salience precedent (shadow-mode pattern):** Fase 1.7b-b in `CLAUDE.md`

---

**End of kickoff doc.** Engineering can execute T1-T14 sequentially or swarm-parallel without reopening the 5,307-word spec. Open questions are non-blocking. Schema delta is concrete. Telemetry queries are copy-paste ready.
