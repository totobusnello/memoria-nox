# A3 Implementation Kickoff — Provider Abstraction Layer

**Date:** 2026-05-18
**Status:** KICKOFF (planning only, NOT implementation)
**Spec source:** A3 design spec — PR #8 `overnight/2026-05-17/A3-provider-abstraction-spec` (4,171 words)
**Pillar:** A (Autonomy) — "Your memory. Your provider. Your bill. No middlemen."
**Branch for this doc:** `overnight/2026-05-18/A3-impl-kickoff`
**Target PR title:** `[overnight] A3-kickoff — Implementation tasks for provider abstraction`
**Auto-merge:** NO

---

## 1. Cross-references

### Upstream

| Source | Why it matters here |
|---|---|
| **A3 spec (PR #8)** | Architectural source of truth: 13 sections, 5 V1 providers, no-proxy invariant, per-dim tables, conformance suite contract. |
| **D41 — Gemini-only default** | Locks default provider for both embeddings and LLM (decision recorded 2026-05-17). A3 must NOT change retrieval quality; swap is opt-in only. |
| **E14 retrieval evolution** | Empirical validation that Gemini-embedding-001 (3072d) + RRF beats every alternative tested. Defends the "Gemini stays default" stance under any swap test. |
| **Schema v10** (canonical) | Current vec table `vec_chunks` is single-dim 3072. A3 introduces `vec_chunks_<dim>` family. v11 delta scoped here. |

### Downstream consumers

| Sprint | Hard or soft dependency | Behavior if A3 not shipped |
|---|---|---|
| **P1 — answer primitive** (PR #18) | SOFT — wants `selectLLMProvider()` so flash-lite default is swap-ready | Calls `geminiClient` directly; P1 still ships; A3 retrofit later. |
| **A2 — export/import** (PR #17) | SOFT — wants provider metadata in export bundle (which dims, which provider) | Exports current `vec_chunks` only; cross-provider bundles deferred to A2.1. |
| **A3.1 — reembed migration** | HARD — needs A3 interfaces locked first | Out of scope here; placeholder T15. |

A3 ships before P1+A2 finalize → both pick up provider injection for free. A3 ships after → both refactor in A3.1 follow-up. Either order is acceptable.

---

## 2. Default lock (D41 compliance)

| Slot | Default | Override env |
|---|---|---|
| Embeddings | `gemini-embedding-001` (3072d) | `NOX_EMBEDDING_PROVIDER`, `NOX_EMBEDDING_MODEL` |
| LLM | `gemini-2.5-flash-lite` | `NOX_LLM_PROVIDER`, `NOX_LLM_MODEL` |
| Fallback chain | DISABLED | `NOX_LLM_FALLBACK=anthropic:sonnet,openai:gpt-4o-mini` |
| Daily $ cap | $50.00 | `NOX_PROVIDER_DAILY_USD_CAP` |

**Invariant:** with zero env overrides, A3 must produce byte-identical embeddings and bit-identical LLM outputs versus the pre-A3 main branch on a fixed test corpus. T14 regression suite enforces.

---

## 3. Task breakdown (16 tasks, ~35-40h)

### T1 — Interfaces (2h)

**Files:** `src/providers/embedding/types.ts`, `src/providers/llm/types.ts`, `src/providers/types.ts`

Locked signatures from A3 spec §3:

```typescript
// src/providers/embedding/types.ts
export interface EmbeddingProvider {
  readonly id: string;            // 'gemini' | 'openai' | 'anthropic' | 'voyage' | 'local'
  readonly model: string;         // 'gemini-embedding-001'
  readonly dimensions: number;    // 3072
  readonly costPer1MTokens: number; // USD
  embed(texts: string[], opts?: EmbedOptions): Promise<EmbedResult>;
  health(): Promise<HealthStatus>;
}

export interface EmbedOptions {
  taskType?: 'retrieval.query' | 'retrieval.document';
  signal?: AbortSignal;
}

export interface EmbedResult {
  vectors: Float32Array[];        // one per input text
  tokensConsumed: number;
  latencyMs: number;
}

// src/providers/llm/types.ts
export interface LLMProvider {
  readonly id: string;
  readonly model: string;
  readonly costPer1MInputTokens: number;
  readonly costPer1MOutputTokens: number;
  complete(prompt: string, opts?: CompleteOptions): Promise<CompleteResult>;
  health(): Promise<HealthStatus>;
}

export interface CompleteOptions {
  maxTokens?: number;
  temperature?: number;
  systemPrompt?: string;
  signal?: AbortSignal;
}

export interface CompleteResult {
  text: string;
  inputTokens: number;
  outputTokens: number;
  latencyMs: number;
  providerId: string;             // populated by chain if fallback fires
}

// src/providers/types.ts
export interface HealthStatus {
  ok: boolean;
  latencyMs: number;
  error?: string;
}
```

**DoD:** types compile, no implementations imported, zero runtime impact.

### T2 — Registry / selectors (3h)

**Files:** `src/providers/index.ts`, `src/providers/registry.ts`

```typescript
export function selectEmbeddingProvider(env = process.env): EmbeddingProvider;
export function selectLLMProvider(env = process.env): LLMProvider;
export function getLLMFallbackChain(env = process.env): LLMProvider[]; // [] when NOX_LLM_FALLBACK unset
```

**Rules:**
- Default branch (no env): returns Gemini providers
- Missing API key for selected provider → throw `MissingKeyError` with redacted message (never echo key prefix)
- Unknown provider id → throw `UnknownProviderError`
- Model override (`NOX_LLM_MODEL=gemini-2.5-flash`) applied at construction

**DoD:** factory tests cover (default, override, missing key, unknown name, model override) = 5 cases.

### T3 — Gemini embedding provider (3h)

**File:** `src/providers/embedding/gemini.ts`

Wraps existing `src/embedder.ts` logic verbatim. NO behavior change — same retries, same batching, same task-type routing. Existing call sites continue working through compat layer until T13.

**DoD:** regression test: `embed(["hello world"])` returns vector bit-identical to pre-refactor main on same API key.

### T4 — Gemini LLM provider (3h)

**File:** `src/providers/llm/gemini.ts`

Wraps existing `src/lib/gemini-client.ts`. Default model `gemini-2.5-flash-lite`. Heartbeat-style calls keep their own model config (cost lesson 2026-04-22) — A3 provider exposes the model but does not force callers to upgrade.

**DoD:** completion against fixed prompt returns same text on same temperature seed.

### T5 — OpenAI stub (1h)

**Files:** `src/providers/embedding/openai.ts`, `src/providers/llm/openai.ts`

Interface conformance only. Models registered: `text-embedding-3-small` (1536d), `text-embedding-3-large` (3072d), `gpt-4o-mini`. Skeleton calls real OpenAI SDK but is gated behind `NOX_EMBEDDING_PROVIDER=openai`. Manual smoke test required before declaring "ready" — auto-test would burn budget.

**DoD:** conformance suite passes against mock; live smoke test documented in `runbooks/A3-provider-smoke.md`.

### T6 — Anthropic stub (1h)

**File:** `src/providers/llm/anthropic.ts`

LLM only (Anthropic has no public embedding API as of 2026-05). Models: `claude-3-5-sonnet`, `claude-3-5-haiku`. Same conformance gate as T5.

**DoD:** conformance + mock; no embedding sibling exported.

### T7 — Voyage stub (1h)

**File:** `src/providers/embedding/voyage.ts`

Embedding only. Models: `voyage-3` (1024d), `voyage-3-large` (1024d), `voyage-code-2` (1536d). Cohere left out of V1 scope here per A3 spec §6 (kicked to V1.5).

**DoD:** conformance + mock; appears in `selectEmbeddingProvider` switch.

### T8 — Local provider stub (1h)

**Files:** `src/providers/embedding/local.ts`, `src/providers/llm/local.ts`

OpenAI-compatible HTTP shim (Ollama, llama.cpp server, vLLM). `NOX_LOCAL_BASE_URL` configurable. Treated as stub — no quality claims, just interface plumbing.

**DoD:** conformance against fixture HTTP server; documented as "experimental".

### T9 — Health checks (2h)

**File:** `src/providers/health.ts` + extends `/api/health` HTTP endpoint

Each provider implements `health()` with 5s timeout, no token consumption (use `models.list` or equivalent metadata call). Exposed at `/api/health.providers` as `{ embedding: {...}, llm: {...}, fallback: [...] }`.

**DoD:** stale-key, network-down, and rate-limit responses each map to deterministic `HealthStatus` shape; timeout enforced; no health probe ever costs > $0.01.

### T10 — LLM fallback chain (3h)

**File:** `src/providers/llm/chain.ts`

LLM ONLY. Embeddings are deterministic per model → mixing providers silently corrupts semantic search (A3 spec §5). Activation:

```
NOX_LLM_FALLBACK=anthropic:claude-3-5-haiku,openai:gpt-4o-mini
```

Behavior:
- Primary timeout (default 30s) → try next
- HTTP 429 (rate limit) → try next, mark primary cooldown 60s
- HTTP 401/403 (auth) → fail-fast, do NOT try fallback (likely user config bug)
- Each call returns `providerId` field so caller telemetry attributes correctly

**DoD:** chain tests cover (primary OK, primary 429 → fallback OK, primary 401 → no fallback, all fail → original error surfaced).

### T11 — Cost telemetry (3h)

**File:** `src/lib/provider-telemetry.ts` + schema v11

```sql
CREATE TABLE IF NOT EXISTS provider_telemetry (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  ts          INTEGER NOT NULL,        -- unix ms
  provider_id TEXT    NOT NULL,        -- 'gemini' | 'openai' | ...
  model       TEXT    NOT NULL,
  kind        TEXT    NOT NULL,        -- 'embedding' | 'llm'
  tokens_in   INTEGER NOT NULL DEFAULT 0,
  tokens_out  INTEGER NOT NULL DEFAULT 0,
  cost_usd    REAL    NOT NULL,
  latency_ms  INTEGER NOT NULL,
  ok          INTEGER NOT NULL,        -- 0/1
  caller      TEXT,                    -- 'vectorize' | 'kg-extract' | 'reflect' | 'crystallize' | 'embedder'
  session_id  TEXT
);
CREATE INDEX idx_provider_telemetry_ts       ON provider_telemetry(ts);
CREATE INDEX idx_provider_telemetry_provider ON provider_telemetry(provider_id, ts);
```

**NO prompts, NO response text logged.** Caller name + token count + cost only.

**DoD:** telemetry row written per call within 5ms (write-behind queue acceptable); ±5% cost accuracy vs provider invoice over 24h sample; `/api/health.cost.last24h` returns aggregates.

### T12 — Daily cost cap (2h)

**File:** `src/lib/cost-cap.ts`

```
NOX_PROVIDER_DAILY_USD_CAP=50.00   # default
```

Pre-call check: if today's `SUM(cost_usd)` ≥ cap, throw `CostCapExceededError`. Override:

```
NOX_PROVIDER_DAILY_USD_CAP_BYPASS=1   # explicit, audit-logged
```

Bypass writes to `ops_audit` table (existing A1 op-audit infra) — never silent.

**DoD:** cap halt within 200ms of crossing; bypass leaves audit row; reset at UTC midnight.

### T13 — Refactor 15 call sites (8h)

**Sites (verified via current main grep on 2026-05-18):**

| # | File | Type | Notes |
|---|---|---|---|
| 1 | `src/embedder.ts` | embedding | Wrapped by T3 — caller pattern remains; internal swap to `selectEmbeddingProvider()` |
| 2 | `src/vectorize.ts` | embedding | Batch embed loop |
| 3 | `src/lib/kg-llm.ts` | LLM | KG extraction calls — keep `gemini-2.5-flash` override for volume (existing pattern) |
| 4 | `src/lib/kg-llm.ts` (relation) | LLM | Second call site in same file |
| 5 | `src/reflect.ts` | LLM | Reflection loop |
| 6 | `src/crystallize.ts` | LLM | Crystallization synthesis |
| 7 | `src/crystallize.ts` (validate) | LLM | Validator pass |
| 8 | `src/cli/ingest-entity.ts` | embedding | Entity ingest path |
| 9 | `src/lib/semantic-cache.ts` | embedding | Cache key embedding |
| 10 | `src/lib/cross-search.ts` | LLM | Cross-corpus synthesis |
| 11 | `src/lib/heartbeat.ts` | LLM | Hard-coded flash-lite — KEEP, just route through provider for telemetry |
| 12 | `src/lib/session-distill.ts` | LLM | Session noise filter |
| 13 | `src/lib/section-classifier.ts` | LLM | Frontmatter/compiled/timeline routing |
| 14 | `src/mcp-server.ts` (search) | embedding | Query embedding |
| 15 | `src/api/search.ts` | embedding | HTTP query embedding |

**Order:**
1. T13.a — call sites with provider already swappable (embedder, vectorize) — low risk
2. T13.b — KG/reflect/crystallize — medium risk (LLM behavior matters for KG quality)
3. T13.c — search-path (mcp-server, api/search) — last (touches query latency)

**Backward compatibility:** old direct calls to `geminiClient.embed()` continue working until T13 retires each site. Compat shim warns once per process.

**DoD:** all 15 sites compile and pass existing test suite; no behavior diff on regression corpus (T14).

### T14 — Tests (5h)

**Files:** `src/providers/__tests__/`

1. **Conformance suite** — runs each registered provider through the same 12-case battery (embed empty, embed long, embed batch, LLM short, LLM long, LLM with system prompt, abort, timeout, auth error, rate limit, 5xx, malformed response). Live providers gated behind `NOX_TEST_LIVE_<PROVIDER>=1`.
2. **Health timeout** — fixture server with 10s delay → health must return `ok:false` within 5s.
3. **Fallback chain** — mock primary returns 429 → assert fallback used + telemetry attributes correctly.
4. **Cost cap** — seed telemetry to $49.99 → next call halts, bypass override succeeds.
5. **Refactor regression** — fixed 100-chunk corpus: embed via pre-A3 baseline vs A3 default-Gemini path → vectors bit-identical, search top-10 identical.
6. **Secret hygiene smoke** — grep test output, error messages, telemetry rows for any string matching API key regex → must return zero matches.

**DoD:** all six pass on CI; live-provider tests pass on manual smoke run; coverage > 90% on `src/providers/`.

### T15 — Migration placeholder (1h)

**File:** `src/cli/reembed.ts` (stub only)

```
nox-mem reembed --provider <id> --model <name> --confirm
```

Prints: "A3.1 — not yet implemented. See specs/2026-05-XX-A3.1-reembed-migration.md". Exit 2.

Rationale: locking the CLI surface now means A3.1 only fills in the body; A2 export bundles can reserve the field.

**DoD:** command registered in CLI router, prints stub message, returns exit 2.

### T16 — Docs (2h)

**Files:** `docs/PROVIDERS.md`, `runbooks/A3-provider-smoke.md`, updates to `README.md` (1 paragraph), `docs/DECISIONS.md` (D41 cross-link), `CLAUDE.md` (add `Provider selection` subsection under "Regras críticas").

Content:
- One-page provider matrix (provider × dim × cost × status)
- 4-step "swap provider" walkthrough
- Smoke test runbook (per-provider live verification, ~5 min each)
- Security note: keys env-only, never logged, never in error messages
- D41 reaffirmed: Gemini is the default; swap is opt-in.

**DoD:** docs render in repo viewer, runbook executable end-to-end on clean VPS.

---

## 4. File structure

```
src/providers/
├── index.ts                       # selectEmbeddingProvider, selectLLMProvider, chain
├── types.ts                       # HealthStatus, shared errors
├── registry.ts                    # provider name → class map
├── health.ts                      # cross-provider health probe
├── embedding/
│   ├── types.ts                   # EmbeddingProvider interface
│   ├── gemini.ts                  # T3
│   ├── openai.ts                  # T5
│   ├── voyage.ts                  # T7
│   └── local.ts                   # T8
├── llm/
│   ├── types.ts                   # LLMProvider interface
│   ├── gemini.ts                  # T4
│   ├── openai.ts                  # T5
│   ├── anthropic.ts               # T6
│   ├── local.ts                   # T8
│   └── chain.ts                   # T10 fallback
└── __tests__/
    ├── conformance.test.ts        # T14.1
    ├── factory.test.ts            # T2 DoD
    ├── health.test.ts             # T14.2
    ├── fallback.test.ts           # T14.3
    ├── cost-cap.test.ts           # T14.4
    ├── regression.test.ts         # T14.5
    └── secret-hygiene.test.ts     # T14.6

src/lib/
├── provider-telemetry.ts          # T11
└── cost-cap.ts                    # T12
```

---

## 5. Schema v11 delta

```sql
-- migration: schema_v11_provider_telemetry.sql
PRAGMA user_version = 11;

CREATE TABLE provider_telemetry (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  ts          INTEGER NOT NULL,
  provider_id TEXT    NOT NULL,
  model       TEXT    NOT NULL,
  kind        TEXT    NOT NULL CHECK (kind IN ('embedding','llm')),
  tokens_in   INTEGER NOT NULL DEFAULT 0,
  tokens_out  INTEGER NOT NULL DEFAULT 0,
  cost_usd    REAL    NOT NULL,
  latency_ms  INTEGER NOT NULL,
  ok          INTEGER NOT NULL CHECK (ok IN (0,1)),
  caller      TEXT,
  session_id  TEXT,
  CHECK (cost_usd >= 0),
  CHECK (tokens_in >= 0),
  CHECK (tokens_out >= 0)
);
CREATE INDEX idx_provider_telemetry_ts       ON provider_telemetry(ts);
CREATE INDEX idx_provider_telemetry_provider ON provider_telemetry(provider_id, ts);

-- per-dim vec table family: ADD ONLY when first non-3072 provider activated
-- (kept out of v11 to avoid empty tables polluting backups)
```

Note: A3 spec §4 describes `vec_chunks_<dim>` family but those are created lazily on first non-default dim selection. v11 only adds telemetry — vec_chunks_1024, vec_chunks_1536 ship in A3.1.

---

## 6. T13 migration plan (detail)

### Phase 1 — non-quality paths (low risk)
- T13.a: `src/embedder.ts` (internal wiring), `src/vectorize.ts`
- Validate: regression embeddings bit-identical
- Commit: `refactor(providers): T13.a wire vectorize via selectEmbeddingProvider`

### Phase 2 — quality paths (medium risk)
- T13.b: `kg-llm.ts` (2 sites), `reflect.ts`, `crystallize.ts` (2 sites), `cross-search.ts`, `section-classifier.ts`, `session-distill.ts`, `heartbeat.ts`
- Validate: KG extraction rate within ±2% of baseline on 100-doc fixture (E05 lesson: validate distribution at n≥50)
- Commit per file or per related cluster

### Phase 3 — search hot path (highest blast radius)
- T13.c: `cli/ingest-entity.ts`, `mcp-server.ts`, `api/search.ts`, `lib/semantic-cache.ts`
- Validate: search p50/p95 unchanged ±10%; nDCG on E14 eval set unchanged ±0.005
- Last to merge

### Backward compat
- Existing exports kept for one minor version
- Each retired site adds deprecation warning logged once per process: `[A3] direct geminiClient.X is deprecated, use selectXProvider()`

---

## 7. DoD overall (6 criteria — from A3 spec acceptance)

1. **Zero behavior diff at defaults** — T14.5 regression suite shows bit-identical embeddings + identical top-10 search on E14 eval corpus.
2. **Single-env-var swap** — `NOX_EMBEDDING_PROVIDER=voyage` (with VOYAGE_API_KEY set) reroutes new embeddings to Voyage without code change.
3. **Conformance suite green** — 12-case battery passes for Gemini, OpenAI, Anthropic, Voyage, local stub.
4. **Cost tracking ±5%** — provider_telemetry sum matches provider invoice within 5% over 24h sample.
5. **Daily cap enforced** — synthetic burn test halts within 200ms of crossing $50.
6. **No secret leakage** — secret-hygiene smoke (T14.6) returns zero matches across logs, telemetry, error messages.

---

## 8. Risks

| Risk | Likelihood | Severity | Mitigation |
|---|---|---|---|
| **Dimension drift mid-corpus** — user sets `NOX_EMBEDDING_PROVIDER=voyage` (1024d) on a corpus embedded with Gemini (3072d); semantic search returns garbage | HIGH | HIGH | Fail-fast on mismatch: refuse to search if active provider dim ≠ stored vec dim; emit clear error pointing to A3.1 reembed CLI. |
| **Provider deprecation cliff** (Gemini text-embedding-004 lesson: shutdown announced with ~60d notice) | MEDIUM | HIGH | Provider registry includes `deprecatedAfter` field; health check warns when within 90d of EOL; runbook for rolling reembed (A3.1). |
| **Cost spike from fallback chain** (LLM 429 storms route everything to expensive primary fallback) | MEDIUM | MEDIUM | Per-fallback cost cap subdivides daily $50: primary 80% / fallback-1 15% / fallback-2 5%; chain disabled by default. |
| **KG extraction quality regression** when wrapping kg-llm.ts (T13.b) | MEDIUM | MEDIUM | Distribution validation at n≥100 before merging Phase 2 (E05 lesson); shadow-mode comparison against baseline for 24h before declaring ready. |
| **Refactor breaks heartbeat cost config** (heartbeat must stay flash-lite, lesson 2026-04-22) | LOW | MEDIUM | T13 line item explicitly preserves `heartbeat.model=gemini-2.5-flash-lite`; regression test asserts. |
| **API key leak via error messages** (provider SDK echoes auth header in 401 body) | LOW | HIGH | Error redaction wrapper in all provider impls; T14.6 grep smoke as gate. |
| **Telemetry write contention** at high QPS (every embed call writes to SQLite) | LOW | LOW | Write-behind queue, 100-row batch flush, async; tested at 10x normal load. |

---

## 9. Timeline

| Phase | Tasks | Hours |
|---|---|---|
| Foundations | T1, T2, T9, T11, T12 | 12h |
| Gemini wrap | T3, T4 | 6h |
| Stubs | T5, T6, T7, T8 | 4h |
| Fallback | T10 | 3h |
| Refactor | T13 (a/b/c) | 8h |
| Tests | T14 | 5h |
| Placeholder + docs | T15, T16 | 3h |
| **Total** | **16 tasks** | **~41h** |

Realistic landing: 35-40h with parallelization across T3+T5/T7 (independent provider impls) and T11+T12 (telemetry + cap share infra).

---

## 10. Open questions (resolve in interview before T1)

1. **Cohere V1 or V1.5?** A3 spec PR body says V1; spec sec 6 (no-fazemos) is ambiguous. Default here: V1.5 (out of scope for this kickoff). Confirm.
2. **Streaming LLM responses?** Not in A3 spec NÃO-FAZEMOS list explicitly but spec mentions "complete()" not "stream()". Default here: no streaming in V1; P1 answer primitive batches.
3. **Voyage requires special init for rerank model?** voyage-rerank-2 has different API surface than voyage-3 embedding. Default here: rerank NOT in A3 V1 (rerank lives in D01 spec).
4. **Cost data source-of-truth?** Provider invoices are monthly; telemetry is realtime. For ±5% DoD do we reconcile manually each month or auto-pull provider billing API? Default: manual reconciliation in runbook; auto-pull is A3.2.
5. **vec_chunks_<dim> creation trigger?** On first non-default provider activation (lazy) or at v11 migration (eager)? Default here: lazy. Confirm.
6. **NOX_PROVIDER_DAILY_USD_CAP scope** — global across all callers or per-caller subcap? Default here: global; per-caller is A3.2.

---

## 11. Handoff

When this kickoff is approved:
1. Open T1 implementation branch: `overnight/<date>/A3-T1-interfaces`
2. Land T1+T2+T9+T11+T12 as foundation PR (no behavior change)
3. Land T3+T4 + T14.5 regression as "Gemini wrap" PR (gate: bit-identical baseline)
4. Land T5-T8 stubs in one PR (interface conformance only)
5. T10 fallback as separate PR (high blast radius, isolated review)
6. T13.a → T13.b → T13.c as three sequential refactor PRs
7. T15+T16 close out as docs-only PR

Each PR independently revertible. No PR depends on another's deploy.

---

**Status:** kickoff complete, awaiting decision to start T1.

**This doc is PLANNING ONLY.** No code in this PR. No implementation begins until Toto green-lights the foundation PR.
