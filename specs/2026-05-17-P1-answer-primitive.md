# P1 — Answer Primitive (Grounded RAG with Citations)

> Terceira primitiva canônica: `nox-mem answer "<question>"`. Recebe pergunta NL, monta contexto via hybrid retrieval (BM25+vec+KG+RRF salience-weighted), chama LLM com prompt anti-hallucination, retorna resposta + citações verificadas (chunk_id → file_path + line_range + snippet). Fecha o trio `remember / recall / **answer**`.
>
> *Pain-weighted hybrid memory with shadow discipline — yours by design.*

**Status:** Design spec (CANDIDATE — implementation-ready)
**Data:** 2026-05-17
**ID:** P1 (Q/A/P pillar — primeira spec do pillar **P**rimitives)
**Roadmap pillar:** P (Primitives) — P1 fecha trio canônico
**Owner:** Toto (decisão) · Forge (proposta) · Maestro (execução future sprint)
**Esforço estimado:** spec 2h ✅ · impl ~6h · tests ~3h · shadow 7d · activate 0.5h
**Dependências:**
- ✅ Hybrid search v3.7 (BM25+vec+KG+RRF) — `nox-mem search` produz top-K com `chunk_id, file_path, line_range, content, score, salience, section_boost`
- ✅ Salience formula (Fase 1.7b-b) ativa em ranking
- ✅ Entity file format (`section_boost` compiled=2.0, frontmatter=1.5, timeline=0.8)
- ✅ Provider abstraction Gemini (existing CLI `nox-mem search` já usa `gemini-embedding-001`)
- ✅ HTTP API 18802 (extensible — `/api/{health,search,kg,reflect,…}`)
- ✅ MCP server v3.7+ (16 tools — `nox_mem_search` é padrão a imitar)
**Bloqueia:** P2 (multi-turn answer com session memory) · P3 (streaming response) · D02 (cross-encoder rerank no answer pipeline)
**Cross-ref:** `specs/2026-05-10-E14-retrieval-evolution.md` (retrieval baseline 0.6813), `specs/2026-05-01-E03a-spo-injection.md` (KG context injection — padrão a reusar), `specs/2026-05-06-E13-temporal-aware-ranking.md` (temporal query detector pode informar retrieval mode), `docs/DECISIONS.md` D39 (FTS5 silent design), `paper/paper-tecnico-nox-mem.md` (R02 baseline), regra crítica #5 (scoring é feature work, não fix), regra crítica #2 (validar via /api/health, não logs).

---

## 1. Motivação

### Gap competitivo

| Sistema | remember | recall | **answer** | Citation provenance | KG-aware | Pain-weighted |
|---|---|---|---|---|---|---|
| **memanto** | ✅ | ✅ | ✅ | parcial (chunk refs sem line ranges) | ❌ | ❌ |
| **mem0** | ✅ | ✅ (chat-style query) | ✅ implícito (mistura recall+gen) | ❌ | parcial | ❌ |
| **Mem0/LangMem** | ✅ | ✅ | parcial (via LangChain RAG add-on) | ❌ | ❌ | ❌ |
| **nox-mem (hoje)** | ✅ | ✅ | **❌ gap P1** | já temos no recall | ✅ | ✅ |

**Diferenciação nox-mem que P1 desbloqueia:**

1. **Citation provenance estrutural** — `chunk_id → file_path + line_range + section + section_boost`. Nenhum competidor entrega line-range na resposta. Auditável end-to-end.
2. **KG-aware grounding** — opcional `--with-kg` reusa pipeline E03a (`<vault-facts>` SPO injection) pra adicionar relações curadas além de chunks. Resposta vê **entidades + relações + chunks**, não só blobs.
3. **Pain-weighted salience no contexto** — chunks com `pain` alto (incidents, lessons) sobem no contexto. Resposta lembra do que doeu, não só do que existiu.
4. **Shadow discipline** — feature ship em shadow-mode primeiro (1 semana baseline via `/api/health.answerMetrics`) antes de activate por default. Padrão validado em Fase 1.7b-b.
5. **Provider-agnostic com fallback chain** — Gemini default (já temos key+billing), OpenAI/Anthropic via env. Mesmo padrão de fallback do gateway OpenClaw.

### Pitch externo (ver §15)

> *"Three primitives, not two. Remember stores the memory. Recall fetches the chunks. Answer composes a grounded reply — with chunk-id, file_path, and line range for every claim."*

---

## 2. CLI Shape

### Sintaxe exata

```
nox-mem answer "<question>" \
  [--top-k N]            (default: 8)              \
  [--no-cite]            (default: false — citations always on) \
  [--max-tokens N]       (default: 1500 LLM output) \
  [--provider P]         (gemini|openai|anthropic; default: gemini) \
  [--model M]            (default: provider-specific — see §9) \
  [--temperature N]      (default: 0.2)            \
  [--with-kg]            (default: false — opt-in SPO injection) \
  [--mode M]             (factual|exploratory|temporal; default: auto) \
  [--shadow]             (compute but don't return — telemetry only) \
  [--json]               (output JSON envelope vs human-readable)
```

### Flag semantics

| Flag | Effect |
|---|---|
| `--top-k 8` | Quantos chunks vão no contexto LLM. **Hard cap 32** (acima disso vira RAG-over-RAG, latência explode). |
| `--no-cite` | Desativa output `[chunk_X]` markers no texto. Citations array ainda computado. Diff: output legível pra humano vs auditable pra agente. |
| `--max-tokens 1500` | LLM `max_output_tokens`. Não confundir com context budget (esse é derivado, §9). |
| `--provider gemini` | Roteia pra `gemini/gemini-2.5-flash` (default — see §9 e regra crítica #3 pra delta vs flash-lite). |
| `--model` | Override explícito. Ex: `--provider gemini --model gemini-2.5-flash-lite` pra baixar custo em batch. |
| `--temperature 0.2` | Baixa por design — grounded answer não deve criar; só compor do contexto. |
| `--with-kg` | Adiciona bloco `<vault-facts>` (top-8 SPO triples relevantes à query) ao prompt. Reusa E03a pipeline. Custo: +200-250 tokens contexto. |
| `--mode auto` | Detecta `factual` (default) vs `temporal` (timeline boost, reusa E13 detector) vs `exploratory` (top-k ampliado pra 16, temp 0.4 — exploratório literal). |
| `--shadow` | Roda pipeline completo, persiste em `answer_telemetry`, mas retorna apenas `{ok: true, shadow: true, metrics_id}`. Usado em A/B testing. |
| `--json` | Output do tipo `{answer, citations, retrieval_metadata, provider_metadata, timing}` (schema §3). Sem flag, output humano colorido. |

### Comportamentos default

```
nox-mem answer "qual modelo Gemini default do nox-mem?"
```
- top-k=8, gemini-2.5-flash, temp=0.2, citations on, no KG, mode=auto (→ factual)
- Output humano:
  ```
  O modelo Gemini default do nox-mem é gemini-2.5-flash-lite [chunk_3].

  Citations:
    [chunk_3] CLAUDE.md L52-58 — "Modelo Gemini padrão: gemini/gemini-2.5-flash-lite..."

  (8 chunks retrieved, 1 cited, 1.2s, gemini-2.5-flash, 412 tok in / 38 tok out)
  ```

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Answer returned, ≥1 citation, all citations validated |
| 2 | Empty retrieval (no chunks above similarity threshold). Stdout: `{answer: "No memory matches this question.", citations: []}` |
| 3 | All providers failed (Gemini quota + OpenAI 5xx + Anthropic 5xx). Stderr message. |
| 4 | LLM cited nonexistent chunk_id even after retry (§8). Stderr + telemetry flagged. |
| 5 | Token budget exhausted before single chunk fit (impossible with default, possible se top-k 32 + huge chunks). |

---

## 3. HTTP API Shape

### Endpoint

```
POST /api/answer
Content-Type: application/json
```

### Request schema (TypeScript)

```typescript
interface AnswerRequest {
  question: string;                       // required, 3-2000 chars
  topK?: number;                          // default 8, max 32
  maxTokens?: number;                     // default 1500, max 4000
  provider?: 'gemini' | 'openai' | 'anthropic';  // default 'gemini'
  model?: string;                         // override default for provider
  temperature?: number;                   // default 0.2, range [0.0, 1.0]
  withKG?: boolean;                       // default false
  mode?: 'factual' | 'exploratory' | 'temporal' | 'auto';  // default 'auto'
  shadow?: boolean;                       // default false
  includeChunkContent?: boolean;          // default true — return full content in citations
}
```

### Response schema

```typescript
interface AnswerResponse {
  answer: string;                         // LLM output, [chunk_N] markers inline
  citations: Citation[];                  // verified, deduplicated
  retrievalMetadata: {
    totalRetrieved: number;               // top-k actual after dedupe
    totalCited: number;                   // citations.length
    retrievalMode: 'factual' | 'exploratory' | 'temporal';
    kgInjected: boolean;
    spoTriplesIncluded: number;           // 0 if !withKG
    avgSalience: number;
    maxPain: number;
  };
  providerMetadata: {
    provider: string;
    model: string;
    tokensIn: number;
    tokensOut: number;
    fallbackUsed: boolean;                // true if primary failed
    fallbackChain: string[];              // ['gemini-2.5-flash', 'gemini-2.5-flash-lite']
  };
  timing: {
    retrievalMs: number;
    llmMs: number;
    totalMs: number;
  };
  warnings: string[];                     // e.g. ['chunk_4 cited but pruned by token budget']
  shadow?: true;                          // present only if request.shadow
}

interface Citation {
  chunkId: number;                        // db PK
  filePath: string;                       // e.g. "memory/entities/project/nox-mem.md"
  lineRange: [number, number];            // [start, end] 1-indexed inclusive
  section: 'compiled' | 'frontmatter' | 'timeline' | null;
  sectionBoost: number;                   // multiplier applied
  snippetPreview: string;                 // first 240 chars of content
  score: number;                          // post-RRF score
  salience: number;
  pain: number;
  markerId: string;                       // 'chunk_1' .. 'chunk_8' — matches [chunk_N] in answer
}
```

### Error response

```typescript
interface AnswerError {
  error: 'EMPTY_RETRIEVAL' | 'PROVIDER_FAILURE' | 'HALLUCINATED_CITATION' | 'TOKEN_BUDGET' | 'BAD_REQUEST';
  message: string;
  retryAfter?: number;                    // seconds, when PROVIDER_FAILURE due to rate limit
  partial?: AnswerResponse;               // present if pipeline got past retrieval but failed later
}
```

### HTTP status codes

| Status | Condition |
|---|---|
| 200 | Success (`answer` populated) |
| 200 | `EMPTY_RETRIEVAL` (body has `error` field but valid envelope — semantic "no match" ≠ HTTP error) |
| 400 | Bad request (`question` missing, topK>32, temp out of range) |
| 502 | All providers failed |
| 503 | DB locked / health degraded |
| 422 | Hallucinated citation after retry — explicit semantic failure |

---

## 4. MCP Tool Shape

Add to MCP server config alongside existing 16 tools.

```json
{
  "name": "nox_mem_answer",
  "description": "Answer a question using nox-mem hybrid memory as the sole source. Returns a grounded answer with citations linking back to chunk_id, file_path, and line range. Every claim in the answer references at least one chunk. Use this when the user asks a factual question that should be answered from memory rather than free-form generation.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "question": {
        "type": "string",
        "description": "The user's question in natural language. PT-BR or EN both supported.",
        "minLength": 3,
        "maxLength": 2000
      },
      "topK": {
        "type": "integer",
        "description": "Number of memory chunks to retrieve for context. Default 8. Max 32.",
        "default": 8,
        "minimum": 1,
        "maximum": 32
      },
      "withKG": {
        "type": "boolean",
        "description": "If true, also inject top SPO triples from knowledge graph (entity facts) into the LLM context. Default false. Use when question mentions specific entities (people, projects, products).",
        "default": false
      },
      "mode": {
        "type": "string",
        "enum": ["factual", "exploratory", "temporal", "auto"],
        "description": "Retrieval mode. 'auto' detects from query (e.g. 'quando/when' → temporal). 'factual' is strict-match. 'exploratory' widens top-k and raises temperature.",
        "default": "auto"
      },
      "provider": {
        "type": "string",
        "enum": ["gemini", "openai", "anthropic"],
        "default": "gemini"
      },
      "maxTokens": {
        "type": "integer",
        "default": 1500,
        "minimum": 64,
        "maximum": 4000
      }
    },
    "required": ["question"]
  }
}
```

**Return value (MCP-style content block):**

```typescript
{
  content: [
    { type: 'text', text: response.answer },
    { type: 'text', text: '\n\n---\nCitations:\n' + formatCitations(response.citations) }
  ],
  isError: false,
  _meta: {
    retrievalMetadata: response.retrievalMetadata,
    providerMetadata: response.providerMetadata,
    timing: response.timing
  }
}
```

---

## 5. Retrieval Chain (6 steps)

```
USER QUESTION
   │
   ▼
┌──────────────────────────────────────────────────────────────┐
│ Step 1: Hybrid search top-K (default 8)                     │
│   - Reuse existing search.ts pipeline                       │
│   - FTS5 BM25 + Gemini 3072d + RRF (k=60)                   │
│   - Salience formula applied (recency × pain × importance)  │
│   - Output: HybridSearchResult[] with full chunk metadata   │
└──────────────────────────────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────────────────────────┐
│ Step 2: Rerank w/ section_boost (already in search pipeline)│
│   - compiled ×2.0, frontmatter ×1.5, timeline ×0.8          │
│   - If mode=temporal, INVERT timeline → ×1.5 (reuse E13)    │
│   - Salience x section_boost = final answer-context-score   │
└──────────────────────────────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────────────────────────┐
│ Step 3: Dedupe near-duplicates                              │
│   - Group chunks where Levenshtein(content_a, content_b)    │
│     normalized > 0.85 OR same (file_path, line_overlap>50%) │
│   - Keep highest-scored representative                      │
│   - Output: ≤top-k unique chunks                            │
└──────────────────────────────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────────────────────────┐
│ Step 4: Format context with chunk_id markers                │
│   - Assign markerId chunk_1..chunk_N (1-indexed by score)   │
│   - Compute token budget:                                   │
│       contextBudget = providerMaxContext                    │
│                     - maxTokens (output)                    │
│                     - systemPromptTokens (~400)             │
│                     - kgBlockTokens (200-250 if withKG)     │
│                     - safetyMargin (200)                    │
│   - Truncate chunks oldest-first if over budget             │
│   - Inject SPO triples (E03a <vault-facts>) if --with-kg    │
└──────────────────────────────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────────────────────────┐
│ Step 5: LLM call w/ prompt template (§7)                    │
│   - Provider-specific adapter (gemini/openai/anthropic)     │
│   - On rate limit / 5xx → fallback chain (§9)               │
│   - Stream OFF v1 (see §14)                                 │
└──────────────────────────────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────────────────────────┐
│ Step 6: Parse output, validate citations                    │
│   - Regex extract [chunk_N] markers                         │
│   - Map each marker → chunkId via the retrieval set         │
│   - If LLM cited [chunk_K] where K > N (or unknown)         │
│     → §8 anti-hallucination guard                           │
│   - Build Citation[] with full provenance                   │
│   - Persist telemetry row                                   │
└──────────────────────────────────────────────────────────────┘
```

### Why this order

- Step 2 happens INSIDE step 1 in the existing search pipeline. Listed separately for clarity but **no code change** — answer just calls `searchHybrid({query, topK, mode})` and inherits the section_boost + salience for free.
- Step 3 dedupe is NEW for answer (recall returns dupes by design, answer can't tolerate them — LLM gets confused by 2 chunks with same content but different IDs).
- Step 4 token budgeting is the **load-bearing** step. Get the math wrong and you either truncate gold chunks or get 429 from provider.

---

## 6. Citation Format

### Inline (in `answer` field)

```
O modelo Gemini default do nox-mem é gemini-2.5-flash-lite [chunk_3]. A regra
crítica #3 proíbe voltar pra gemini-2.5-flash full por causa de quota 3M/d
[chunk_3][chunk_5]. KG extraction pode usar flash full porque volume é baixo
[chunk_5].
```

### Structured (in `citations` array)

```json
[
  {
    "chunkId": 117984,
    "filePath": "CLAUDE.md",
    "lineRange": [52, 58],
    "section": null,
    "sectionBoost": 1.0,
    "snippetPreview": "Modelo Gemini padrão: gemini/gemini-2.5-flash-lite. NUNCA voltar pra gemini-2.5-flash (quota 3M/d estoura)...",
    "score": 0.847,
    "salience": 0.92,
    "pain": 0.6,
    "markerId": "chunk_3"
  }
]
```

### Rules

1. **Every non-trivial claim MUST have ≥1 [chunk_N]** — enforced by prompt (§7) and validated post-hoc (§8).
2. **Multiple citations OK** — `[chunk_3][chunk_5]` means both support the claim.
3. **No citation = "synthesis" sentence** — allowed only for connective text ("Em resumo:", "Portanto:") with ZERO factual content.
4. **`markerId` is the bridge** — LLM sees only `chunk_N`, never the real DB id. Mapping table stays server-side.
5. **`lineRange` derived** from `chunks.line_start, chunks.line_end` (must be NOT NULL — invariant guaranteed by existing schema v10).
6. **`snippetPreview` truncated at 240 chars** + `…` if longer. Full content available via `nox-mem search --chunk-id N` if user wants.

---

## 7. Prompt Template

### SYSTEM prompt (constant per provider, ~380 tokens)

```
You are nox-mem's grounded answer engine. Your job is to answer the user's
question USING ONLY the numbered context chunks provided below. You are NOT
allowed to use external knowledge.

RULES (non-negotiable):

1. Every claim in your answer MUST be supported by at least one chunk.
   Cite chunks inline using [chunk_N] markers (e.g., [chunk_3] or [chunk_3][chunk_5]).

2. If the chunks do not contain enough information to answer the question,
   reply EXACTLY with: "I don't have enough memory to answer this."
   Then list the closest related chunks you DID find (still cited).

3. Do NOT invent chunk numbers. Only cite chunks that actually appear in the
   context below. Citing a chunk that doesn't exist is a hard failure.

4. Quote the source verbatim when the question asks for an exact value, name,
   number, or date. Don't paraphrase what could be quoted.

5. Prefer chunks marked higher (chunk_1 > chunk_2 > ...) when sources conflict.
   Higher rank = higher salience × section_boost in nox-mem ranking.

6. Be concise. Default to 1-3 sentences unless the question explicitly asks
   for elaboration. Length is a cost.

7. Match the language of the question: PT-BR question → PT-BR answer.
   EN question → EN answer.

OUTPUT FORMAT: plain prose with inline [chunk_N] markers. No JSON, no markdown
headers. Citations array is built server-side from your markers — do NOT add
a "Citations:" section yourself.
```

### USER prompt (template, populated per request)

```
QUESTION: {{question}}

{{#if kgInjected}}
<vault-facts>
{{spoTriples}}
</vault-facts>

{{/if}}
CONTEXT CHUNKS (ordered by retrieval score, highest first):

[chunk_1] {{chunk_1.content}}
  (source: {{chunk_1.filePath}} L{{chunk_1.lineStart}}-{{chunk_1.lineEnd}}, section={{chunk_1.section || 'na'}})

[chunk_2] {{chunk_2.content}}
  (source: {{chunk_2.filePath}} L{{chunk_2.lineStart}}-{{chunk_2.lineEnd}}, section={{chunk_2.section || 'na'}})

...

[chunk_N] {{chunk_N.content}}
  (source: {{chunk_N.filePath}} L{{chunk_N.lineStart}}-{{chunk_N.lineEnd}}, section={{chunk_N.section || 'na'}})

ANSWER:
```

### Notes

- The `(source: ...)` annotation per chunk is for the LLM's reasoning, but the **server still re-derives** provenance from the retrieval set when building `Citation[]`. The LLM cannot lie about file paths.
- Provider-specific tweaks: Anthropic gets `<question>...</question>` and `<context>...</context>` tags (Anthropic best practice). Gemini and OpenAI use plain markers above. Adapter handles this.

---

## 8. Anti-Hallucination Guard

### Detection

After LLM returns, regex-extract every `[chunk_N]` marker:

```typescript
const cited = [...output.matchAll(/\[chunk_(\d+)\]/g)].map(m => parseInt(m[1], 10));
const valid = new Set(retrievalSet.map((_, i) => i + 1));  // [1..N]
const hallucinated = cited.filter(id => !valid.has(id));
```

### Action ladder

| Hallucinated count | Action |
|---|---|
| 0 | Happy path — build citations, return |
| ≥1 (first occurrence) | **Retry once** with stricter prompt (see below). Telemetry: `retried=1` |
| ≥1 after retry | Fail hard. HTTP 422 `HALLUCINATED_CITATION`. Telemetry: `failed=1` |

### Stricter retry prompt (delta from §7)

Append to SYSTEM:

```
PREVIOUS ATTEMPT FAILED: you cited chunk(s) that do not exist in the context.
The valid chunk numbers are exactly: chunk_1, chunk_2, ..., chunk_{N}.
DO NOT cite any other number. If you cannot answer with the chunks listed,
reply: "I don't have enough memory to answer this."
```

Append to USER, prepended:

```
[RETRY — prior attempt cited invalid chunks: chunk_{hallucinated.join(', chunk_')}]
```

### Why retry-once not retry-N

- Cost — every retry doubles latency and tokens
- If the LLM hallucinates a chunk_id twice, it's confused about the context. Better to fail cleanly with HTTP 422 + telemetry flag than burn budget retrying
- The hard fail surfaces a real bug (e.g. retrieval set <8 but LLM was told 8) instead of masking it

### Edge case: zero citations

LLM returns answer with ZERO `[chunk_N]` markers. This is also a guard failure but a softer one:

- If answer matches `/^i don'?t have enough memory/i` → expected behavior, no retry
- Otherwise → retry once with stricter prompt forcing citation
- After retry, if still 0 citations → return answer but flag `warnings: ['Answer has zero citations — treat as uncited synthesis']` and HTTP 200 (degraded, not failed)

---

## 9. Configuration

### Environment variables

| Var | Required | Default | Purpose |
|---|---|---|---|
| `GEMINI_API_KEY` | YES (if provider=gemini) | — | Default provider key. Existing nox-mem dep. |
| `OPENAI_API_KEY` | NO | — | Enables OpenAI fallback |
| `ANTHROPIC_API_KEY` | NO | — | Enables Anthropic fallback |
| `NOX_ANSWER_MODEL_GEMINI` | NO | `gemini-2.5-flash` | Override default Gemini model |
| `NOX_ANSWER_MODEL_OPENAI` | NO | `gpt-4o-mini` | Override OpenAI model |
| `NOX_ANSWER_MODEL_ANTHROPIC` | NO | `claude-haiku-4-5` | Override Anthropic model |
| `NOX_ANSWER_FALLBACK_CHAIN` | NO | `gemini-2.5-flash,gemini-2.5-flash-lite` | Comma-separated fallback order |
| `NOX_ANSWER_MAX_CONTEXT_TOKENS` | NO | `120000` | Provider context window minus safety. Override per provider. |
| `NOX_ANSWER_SHADOW_MODE` | NO | `false` | If `true`, all answers go shadow regardless of `--shadow` flag. Used during 7d activation period. |
| `NOX_ANSWER_LOG_QUESTIONS` | NO | `false` | If `true`, telemetry logs raw question hash + question text. Default off (privacy — see §11). |

### Default model choice rationale

- **Gemini 2.5 flash (not flash-lite)** — flash-lite OK for batch/agent infra (per user-level memory feedback) BUT answer is user-facing and quality matters; flash gives better instruction-following on "cite every claim" rule. flash-lite is the **first fallback**.
- **OpenAI gpt-4o-mini** — cheap, fast, decent at instruction following. Not gpt-4o (overkill for grounded RAG).
- **Anthropic claude-haiku-4-5** — cheap and current. Don't default to Sonnet unless `--mode exploratory` (future v2 consideration).

### Fallback chain

```
primary (e.g. gemini-2.5-flash)
  └─ on 429/5xx/timeout(15s) → gemini-2.5-flash-lite
      └─ on 429/5xx/timeout(15s) → openai gpt-4o-mini (if OPENAI_API_KEY set)
          └─ on 429/5xx/timeout(15s) → anthropic claude-haiku-4-5 (if ANTHROPIC_API_KEY set)
              └─ exit 3 / HTTP 502 PROVIDER_FAILURE
```

`providerMetadata.fallbackUsed=true` when chain advanced ≥1 step. `fallbackChain` lists the actual providers tried.

### Defaults summary

| Setting | Default |
|---|---|
| top-k | 8 |
| max-tokens (output) | 1500 |
| temperature | 0.2 |
| max-context-tokens | 120000 (Gemini 1M is overkill, leave headroom for KG/system) |
| timeout per provider | 15s |
| retry on hallucination | 1× |

---

## 10. Error Handling

### Failure modes & responses

| Condition | CLI exit | HTTP status | Body |
|---|---|---|---|
| Empty retrieval (0 chunks above threshold) | 2 | 200 | `{answer: "No memory matches this question.", citations: [], retrievalMetadata: {totalRetrieved: 0, ...}}` |
| Retrieval returned chunks but ALL pruned by token budget | 5 | 200 | `{answer: "...", citations: [], warnings: ["All retrieved chunks exceeded token budget"]}` |
| Primary provider 429 (rate limit) | 0 if fallback works, else 3 | 200 / 502 | Fallback chain attempted (§9) |
| Primary provider 5xx | same as 429 | same | Fallback |
| Primary provider timeout >15s | same as 429 | same | Fallback |
| All providers failed | 3 | 502 | `{error: "PROVIDER_FAILURE", message: "All providers exhausted", fallbackChain: [...]}` |
| LLM hallucinated chunk_id (after 1 retry) | 4 | 422 | `{error: "HALLUCINATED_CITATION", partial: {...prefix valid...}}` |
| DB locked / health degraded | 1 | 503 | `{error: "DB_LOCKED", retryAfter: 5}` |
| Bad request (question too long, topK>32, etc.) | 1 | 400 | `{error: "BAD_REQUEST", message: "topK must be ≤32"}` |
| Question matches block-pattern (e.g. literal secret regex) | 1 | 400 | `{error: "BAD_REQUEST", message: "Question contains potential secret"}` |

### Token budget exhaustion (graceful degrade)

When `sum(chunk_tokens) + systemPromptTokens + kgBlockTokens + outputBudget > maxContext`:

1. Estimate per-chunk tokens (`chunk.content.length / 4` heuristic, refine later with tiktoken-like)
2. Sort chunks by `(answer-context-score) DESC, recency DESC`
3. Pop **lowest-score** chunks one at a time until fits
4. Persist `warnings: ['Pruned N chunks of M to fit context (kept top-K by score)']`
5. If even top-1 chunk doesn't fit → exit 5 / `{warnings: ['Single chunk exceeded token budget — chunk_id X is too large; consider re-chunking']}`

**Rationale "prune lowest-score, not oldest":** "oldest" is wrong heuristic for RAG — old chunks can be more salient (incidents, lessons). Score already encodes salience × section_boost × pain. Trust the ranker.

---

## 11. Telemetry

### Table `answer_telemetry` (new — schema v11 candidate)

```sql
CREATE TABLE answer_telemetry (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts INTEGER NOT NULL,                    -- unix epoch ms
  question_hash TEXT NOT NULL,            -- sha256(question), hex
  question_text TEXT,                     -- ONLY IF NOX_ANSWER_LOG_QUESTIONS=1
  question_lang TEXT,                     -- 'pt' | 'en' | 'mixed' (detected)
  retrieval_count INTEGER NOT NULL,
  citation_count INTEGER NOT NULL,
  cited_chunk_ids TEXT,                   -- JSON array
  retrieved_chunk_ids TEXT,               -- JSON array
  mode TEXT NOT NULL,                     -- 'factual' | 'exploratory' | 'temporal'
  with_kg INTEGER NOT NULL DEFAULT 0,
  spo_triples_included INTEGER NOT NULL DEFAULT 0,
  provider TEXT NOT NULL,
  model TEXT NOT NULL,
  fallback_used INTEGER NOT NULL DEFAULT 0,
  fallback_chain TEXT,                    -- JSON array
  tokens_in INTEGER,
  tokens_out INTEGER,
  retrieval_ms INTEGER,
  llm_ms INTEGER,
  total_ms INTEGER,
  shadow INTEGER NOT NULL DEFAULT 0,
  retried INTEGER NOT NULL DEFAULT 0,     -- 1 if hallucination retry triggered
  failed_reason TEXT,                     -- 'hallucinated' | 'provider_failure' | NULL
  avg_salience REAL,
  max_pain REAL,
  warnings_count INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX idx_answer_telemetry_ts ON answer_telemetry(ts);
CREATE INDEX idx_answer_telemetry_provider ON answer_telemetry(provider, ts);
CREATE INDEX idx_answer_telemetry_failed ON answer_telemetry(failed_reason) WHERE failed_reason IS NOT NULL;
```

### Privacy invariants (NON-NEGOTIABLE)

1. **`question_text` and `answer` are NEVER logged by default** — only `question_hash` (irreversible). User-level memory rule: feedback_no_secrets_in_git applies — questions may contain secrets, never persist as plaintext.
2. **`NOX_ANSWER_LOG_QUESTIONS=1`** opt-in for debugging only. Document in HANDOFF that it must be disabled in prod within 48h of enabling.
3. **`cited_chunk_ids` IS logged** — they're internal db ids, not user content; useful for analyzing which chunks dominate answers (signal for re-ranking).

### Exposed via `/api/health.answerMetrics`

```json
{
  "answerMetrics": {
    "last24h": {
      "requests": 142,
      "shadowRequests": 0,
      "avgRetrievalCount": 7.8,
      "avgCitationCount": 2.4,
      "p50LatencyMs": 1180,
      "p95LatencyMs": 3420,
      "fallbackRate": 0.014,
      "hallucinationRetryRate": 0.007,
      "hardFailureRate": 0.000,
      "providerBreakdown": {"gemini": 140, "openai": 2}
    },
    "last7d": { /* same shape */ }
  }
}
```

### Shadow-mode discipline

- First 7 days post-deploy: `NOX_ANSWER_SHADOW_MODE=true` — pipeline runs on every call from agent personas (Atlas/Boris/etc) but **response is suppressed**, only telemetry persisted
- Baseline collection: p50/p95 latency, fallback rate, hallucination retry rate, retrieval quality (avg_salience, max_pain distribution)
- Activate decision at day 7 — if hallucinationRetryRate <2% and p95 <5s, flip `NOX_ANSWER_SHADOW_MODE=false`
- Validated pattern from Fase 1.7b-b salience (user-level memory: feedback_shadow_mode_for_ranking_changes)

---

## 12. Tests Plan

### Unit tests (Vitest / node:test)

| Test | Asserts |
|---|---|
| `parseAnswerFlags` — defaults | All flags resolve to documented defaults |
| `parseAnswerFlags` — overrides | `--top-k 16` overrides default 8 |
| `parseAnswerFlags` — invariants | `--top-k 33` rejected, `--temperature 1.5` rejected |
| `dedupeChunks` — exact dupes | Same file_path + 100% line overlap → 1 result |
| `dedupeChunks` — near dupes | Levenshtein >0.85 → 1 result, highest score kept |
| `dedupeChunks` — preserves order | Output sorted by score DESC |
| `extractCitations` — happy path | `[chunk_3]` markers → Citation[] with right markerIds |
| `extractCitations` — hallucinated | `[chunk_99]` when only 8 retrieved → flagged |
| `extractCitations` — zero citations | Empty markers → warnings populated |
| `tokenBudget` — fits | All chunks fit → no truncation |
| `tokenBudget` — overflow | Prunes lowest-score until fit |
| `tokenBudget` — single chunk overflow | Fails with exit 5 |
| `buildPrompt` — system | Includes 7 rules verbatim |
| `buildPrompt` — user with KG | `<vault-facts>` block present, ≤250 tok |
| `buildPrompt` — user without KG | No `<vault-facts>` block |
| `fallbackChain` — primary OK | No fallback triggered, fallbackUsed=false |
| `fallbackChain` — 429 cascade | Each fallback tried in order until success |
| `fallbackChain` — all fail | Exit 3 / HTTP 502 |
| `modeAuto` — temporal detection | "quando subiu schema v12?" → mode=temporal |
| `modeAuto` — factual default | "qual modelo gemini?" → mode=factual |

### Golden Q/A pairs (n=20, suggest harvest from existing entity files + INCIDENTS.md)

Curated by Toto during shadow-mode week. Suggested distribution:

| Category | Count | Examples (PT-BR) |
|---|---|---|
| factual single-chunk | 6 | "qual modelo Gemini default?" / "porta da API nox-mem?" / "schema atual?" |
| factual multi-chunk | 4 | "regras críticas memoria-only" / "alavancas refutadas no E14" |
| temporal | 3 | "quando subiu schema v10?" / "qual primeira lição do reindex incident?" |
| cross-language | 3 | EN question → PT answer / mixed |
| no-match (expected EMPTY_RETRIEVAL) | 2 | "qual cor da camisa do Toto?" / "receita de feijoada" |
| adversarial (insufficient context) | 2 | Question that golden chunk doesn't fully answer → expect "I don't have enough memory" |

For each pair: `{question, expectedCitedChunkIds, expectedSubstrings, mustNotContain}`.

### Integration tests (mock provider)

| Test | Mock behavior | Assert |
|---|---|---|
| Happy path | Returns `"X is Y [chunk_1]."` | Citation[] has chunkId, lineRange |
| Hallucination | Returns `"X is Y [chunk_99]."` (when 8 retrieved) | Retry triggered, 2nd mock call has stricter prompt |
| Hallucination after retry | Returns hallucinated again | Exit 4 / HTTP 422 |
| Empty retrieval | Mock retrieval returns 0 chunks | LLM NOT called, exit 2 / HTTP 200 with empty citations |
| Zero citations | Returns plain text no markers | Warnings populated |
| Token overflow | 8 huge chunks 500K tok total | Pruned to fit, warnings shows count |
| Provider 429 | First mock raises 429 | Fallback chain advances |
| All providers down | All mocks raise 5xx | Exit 3 / HTTP 502 |

### E2E test (real Gemini, opt-in via `RUN_E2E=1`)

| Test | Steps |
|---|---|
| smoke | `nox-mem answer "qual porta da API nox-mem?"` → exit 0, contains "18802", ≥1 citation |
| temporal | `nox-mem answer "quando o schema v10 foi introduzido?" --mode temporal` → cites timeline section chunk |
| KG | `nox-mem answer "qual modelo Gemini do nox-mem?" --with-kg` → retrievalMetadata.kgInjected=true |
| no-match | `nox-mem answer "what is the capital of Mars?"` → exit 2, "no memory" |
| latency budget | 10 calls in serial → p95 <5s on flash, <8s on flash-lite fallback |

### Negative tests

| Test | Assert |
|---|---|
| `--top-k 100` | Rejected, exit 1, "topK max 32" |
| `--temperature 2.0` | Rejected |
| `question="hi"` (3-char min) | Allowed (≥3) |
| `question=""` | Rejected |
| Provider key missing | Falls back; if no key for any → exit 3 |
| DB locked | Exit 1 / HTTP 503 with retryAfter |

---

## 13. DoD (Definition of Done) — 5 acceptance criteria

1. **CLI works end-to-end on prod corpus** — `nox-mem answer "qual modelo Gemini default?"` returns correct answer with ≥1 citation pointing to CLAUDE.md L52-58 in <3s p50. Exit 0. `--json` envelope matches schema §3.

2. **HTTP `POST /api/answer` works** — same question via curl returns 200 with schema-compliant `AnswerResponse`. `/api/health.answerMetrics.last24h.requests > 0` reflects the call. Telemetry row persisted in `answer_telemetry`.

3. **MCP tool `nox_mem_answer` discoverable + invocable** — appears in MCP server tool list, called by Maestro/Atlas in test session, returns content blocks with citations.

4. **Anti-hallucination guard validated** — integration test with mock provider that always cites `[chunk_99]` produces exit 4 / HTTP 422 + telemetry `failed_reason='hallucinated'`. Retry path covered (telemetry `retried=1` for at-least-one-attempt scenarios).

5. **Shadow-mode discipline passes 7d baseline** — `NOX_ANSWER_SHADOW_MODE=true` for 7 days, ≥50 answers logged, `/api/health.answerMetrics.last7d.hallucinationRetryRate < 0.02`, `p95LatencyMs < 5000`. Activate flip captured in `docs/DECISIONS.md` as Dxx entry.

---

## 14. NÃO-fazemos (v1)

| Out of v1 scope | Why deferred |
|---|---|
| Multi-turn / conversational context | Each call independent; conversation state belongs to caller (agent runtime), not nox-mem. P2 spec future. |
| Streaming responses (SSE / chunked) | Citations must be validated post-hoc; streaming requires partial-validation logic. P3 future. |
| Auto-rerank beyond existing salience + section_boost | D01/D02 cross-encoder reranker is its own spec (see `specs/2026-05-07-D01-cross-encoder-reranker.md`). Answer reuses whatever search produces. |
| Answer caching by question_hash | Premature optimization. Measure cache-hit potential after 30d of telemetry. Risk: stale chunks → stale cached answer. |
| Function calling / tool use from LLM mid-answer | Answer is grounded RAG, not agentic. If question requires "go fetch X", that's `nox-mem search` then `nox-mem answer`. |
| Citation confidence scores | LLM self-confidence is unreliable. Use existing chunk-level salience as proxy. |
| Multimodal context (images/audio in retrieved chunks) | Out of scope until E12 Tier 3 OCR fills audio/image chunks with text. |
| Auto-translate question or context | Match-the-language rule in prompt (§7) handles bilingual corpus naturally. No translation step. |
| User-customizable prompt template via flag | Security risk + telemetry skew. v1 hardcoded. Power users edit code (low N). |
| Cost meter per call in CLI output | Telemetry tracks tokens; nightly cron can aggregate to $/day. Not per-call UX. |

---

## 15. Out-of-band — Pitch lines

### For paper appendix (R03 supplement)

> *nox-mem implements three primitives: `remember`, `recall`, and `answer`. The third is grounded retrieval-augmented generation with verified citations — every claim in the response is anchored to a `(chunk_id, file_path, line_range)` tuple resolved against the source corpus. Pain-weighted salience and section_boost are applied at the retrieval stage, so the answer composition prioritizes high-cost lessons over generic prose. Anti-hallucination is enforced by re-parsing the LLM output and rejecting citations that don't match the retrieval set.*

### For README

> **Three primitives, not two.**
> `nox-mem remember` ingests memory · `nox-mem recall` searches it · `nox-mem answer` composes a grounded reply with citations. Pain-weighted hybrid memory with shadow discipline — yours by design.

### For Nox-Supermem landing (PT-BR)

> **Sua memória responde.**
> Não é só busca — é resposta fundamentada. Cada afirmação vem com `chunk_id`, arquivo, e linhas exatas. Sem alucinação, sem invenção, sem caixa-preta. Memória híbrida com disciplina shadow — sua por design.

### For social / X post

> wired up the third primitive in nox-mem today: `answer`. grounded RAG with chunk_id + file_path + line_range citations on every claim. anti-hallucination guard rejects fabricated chunk refs. shadow-mode for 7 days before flipping default. three primitives now: remember / recall / answer.

---

## Front-matter for ROADMAP.md row

```
| **P1** | Answer primitive (grounded RAG w/ citations) | Spec ✅ 2026-05-17 | impl ~6h · tests ~3h · shadow 7d | Toto / Forge / Maestro | P (Primitives) — fecha trio canônico vs memanto/mem0 |
```

---

*Status final desta spec:* CANDIDATE pronto pra impl. Executor agent precisa apenas de `specs/2026-05-17-P1-answer-primitive.md` + acesso ao código existente em `/root/.openclaw/workspace/tools/nox-mem/` pra construir sem ambiguidade. Sem dependências bloqueantes além do que já tá em prod (v3.7). 0 BLOCKED.md.
