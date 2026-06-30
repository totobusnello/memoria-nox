# A3 Refactor Sites — T11 Migration Guide

**Status:** Documented for T11 migration. Sites verified via grep on `main` branch 2026-05-18.

Each site replaces a direct `new GoogleGenerativeAI(apiKey)` / `geminiClient.X()` call with
`selectEmbeddingProvider()` or `selectLLMProvider()` from `src/providers/index.ts`.

**Backward compatibility rule:** with zero env overrides, refactored site must behave identically
to pre-A3 hardcoded code (D41 invariant). The provider factory defaults to Gemini.

---

## Site list (15 sites)

| # | File | Type | Risk | Notes |
|---|---|---|---|---|
| 1 | `src/embedder.ts` | embedding | LOW | Wrapped by T3 Gemini impl — internal swap to `selectEmbeddingProvider()`. This file wraps the actual Google SDK; other sites call through it. |
| 2 | `src/vectorize.ts` | embedding | LOW | Batch embed loop calls `embedder.embedBatch()`. After T13.a: calls `selectEmbeddingProvider().embed()`. |
| 3 | `src/lib/kg-llm.ts` (entity extraction) | LLM | MEDIUM | KG extraction first call — override model `gemini-2.5-flash` for quality (existing pattern must be preserved). |
| 4 | `src/lib/kg-llm.ts` (relation extraction) | LLM | MEDIUM | Second call site in same file. Same model override caveat. |
| 5 | `src/reflect.ts` | LLM | MEDIUM | Reflection synthesis loop — quality-sensitive. |
| 6 | `src/crystallize.ts` (synthesis) | LLM | MEDIUM | Crystallization main synthesis pass. |
| 7 | `src/crystallize.ts` (validate) | LLM | MEDIUM | Validator second pass in same file. |
| 8 | `src/cli/ingest-entity.ts` | embedding | MEDIUM | Entity ingest path — embeds entity chunk texts. |
| 9 | `src/lib/semantic-cache.ts` | embedding | MEDIUM | Cache key embedding — lesson 2026-05-03: Buffer pool aliasing. Must continue using `new Float32Array` copy. |
| 10 | `src/lib/cross-search.ts` | LLM | MEDIUM | Cross-corpus synthesis call. |
| 11 | `src/lib/heartbeat.ts` | LLM | LOW | Hard-coded `gemini-2.5-flash-lite` — KEEP model, just route through provider for telemetry. Do NOT allow `NOX_LLM_MODEL` to override here (cost lesson 2026-04-22). |
| 12 | `src/lib/session-distill.ts` | LLM | LOW | Session noise filter — flash-lite acceptable. |
| 13 | `src/lib/section-classifier.ts` | LLM | LOW | Frontmatter/compiled/timeline routing classifier. |
| 14 | `src/mcp-server.ts` (search) | embedding | HIGH | Query embedding on MCP search path — touches query latency. Last to migrate (T13.c). |
| 15 | `src/api/search.ts` | embedding | HIGH | HTTP query embedding — same blast radius as MCP path. Last to migrate. |

---

## Migration order (T13.a → T13.b → T13.c)

### T13.a — Non-quality paths (commit: `refactor(providers): T13.a`)

Sites: **1** (embedder.ts), **2** (vectorize.ts)

```typescript
// Before:
import { embed } from '../embedder.js';
const vectors = await embed(texts);

// After:
import { selectEmbeddingProvider } from '../providers/index.js';
const embProvider = selectEmbeddingProvider();
const vectors = await embProvider.embed(texts);
```

Validation: regression embeddings bit-identical on 100-chunk fixture.

### T13.b — Quality paths (commit per file)

Sites: **3, 4** (kg-llm), **5** (reflect), **6, 7** (crystallize), **8** (ingest-entity), **9** (semantic-cache), **10** (cross-search), **11** (heartbeat), **12** (session-distill), **13** (section-classifier)

**Heartbeat special case (site 11):**

```typescript
// heartbeat.ts — NEVER allow NOX_LLM_MODEL to override here.
// Cost lesson 2026-04-22: heartbeat MUST stay on flash-lite.
import { selectLLMProvider } from '../providers/index.js';
const llm = selectLLMProvider('gemini', { GEMINI_API_KEY: env.GEMINI_API_KEY, NOX_LLM_MODEL: 'gemini-2.5-flash-lite' });
```

**KG extraction special case (sites 3, 4):**

```typescript
// kg-llm.ts — preserve explicit flash model for KG quality.
import { selectLLMProvider } from '../providers/index.js';
const llm = selectLLMProvider('gemini', { ...env, NOX_LLM_MODEL: env.NOX_LLM_MODEL ?? 'gemini-2.5-flash' });
```

Validation per T13.b: KG extraction rate within ±2% of baseline on 100-doc fixture.

### T13.c — Search hot path (commit: `refactor(providers): T13.c`)

Sites: **14** (mcp-server), **15** (api/search)

Validation: search p50/p95 unchanged ±10%; nDCG on E14 eval set unchanged ±0.005.

---

## Deprecation warning pattern

Each retired direct call adds a one-time process warning:

```typescript
import { warnOnce } from '../lib/warn-once.js';
// At call site replacement:
warnOnce('[A3] direct geminiClient.embed is deprecated, use selectEmbeddingProvider()');
```

---

## Backward compatibility guarantee

With zero env overrides (`NOX_EMBEDDING_PROVIDER`, `NOX_LLM_PROVIDER`, `NOX_LLM_MODEL` all unset),
the factory returns `GeminiEmbeddingProvider(gemini-embedding-001, 3072d)` and `GeminiLLMProvider(gemini-2.5-flash-lite)`.
These wrap the same API as the pre-A3 hardcoded code — byte-identical embeddings, same model behavior.

---

## grep commands to locate sites

```bash
# Embedding call sites
grep -rn "GoogleGenerativeAI\|embedContent\|batchEmbedContents\|embedder\.embed" \
  src/ --include="*.ts" | grep -v "staged-A3\|node_modules\|__tests__"

# LLM call sites (gemini generateContent)
grep -rn "generateContent\|geminiClient\|GeminiClient\|gemini\.generate" \
  src/ --include="*.ts" | grep -v "staged-A3\|node_modules\|__tests__"
```

---

*Maintained by T11 refactor sprint. Update as sites are migrated.*
