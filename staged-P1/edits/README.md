# staged-P1 — Answer primitive (T1-T14, COMPLETE)

**Status:** T1-T14 of P1 implementation kickoff. Module skeleton +
retrieval wrapper + prompt template + LLM provider abstraction + citation
parse + anti-hallucination retry + telemetry + CLI + HTTP + MCP +
integration tests + E2E Gemini gated suite + docs + latency bench.

**Branches:**
- T1-T4: `overnight/2026-05-18/P1-implementation-T1-T4` (PRs #29, #31)
- T5-T10: `overnight/2026-05-18/P1-implementation-T5-T10` (PR #34)
- **T11-T14: `wave-b/2026-05-18/P1-impl-T11-T14`** (this branch)

**Spec:** [PR #3](https://github.com/totobusnello/memoria-nox/pull/3) — `specs/2026-05-17-P1-answer-primitive.md`
**Kickoff:** [PR #18](https://github.com/totobusnello/memoria-nox/pull/18) — `specs/2026-05-18-P1-implementation-kickoff.md`
**Docs:** [`docs/ANSWER.md`](docs/ANSWER.md) — full operator + caller reference (T13)
**D41:** default model = `gemini-2.5-flash-lite` (locked, not flash)

---

## What lives here

```
staged-P1/
├── package.json                                     # node:test runner + tsc
├── tsconfig.json                                    # strict ES2022 NodeNext
└── edits/
    ├── README.md                                    # this file
    └── src/lib/answer/
        ├── index.ts              # public API: answer() + AnswerError
        ├── types.ts              # AnswerOpts / AnswerResult / Citation / RetrievedChunk
        ├── config.ts             # defaults + env overrides (D41 #1 locked)
        ├── retrieval.ts          # T2 wrapper around hybrid search (injectable)
        ├── prompt.ts             # T3 system+user prompts (anti-halluc guard)
        ├── provider.ts           # T4 LLMProvider interface + MockProvider + selectProvider()
        └── __tests__/
            ├── integration.test.ts   # 21 cases — end-to-end with mocks
            └── prompt.test.ts        # 12 cases — focused prompt assembly
```

**Total: ~640 LOC source + tests, well under the 700 LOC ceiling.**

---

## Run tests locally

```bash
cd staged-P1
npm install           # one-time: installs typescript + @types/node
npm test              # build + run all node:test files
```

Tests require ZERO credentials and make ZERO network calls:

- `retrieval.ts` exposes `__setRawSearchForTests(fn)` — the integration suite
  binds a fixture-based stub before each block.
- `provider.ts` ships `MockProvider` — deterministic, queue-driven responses.
- `answer({ providerOverride, retrieveOverride })` accepts injection points
  so callers can bypass the real Gemini path entirely.

---

## How to apply on the VPS (after PR #3 merges)

1. **Copy the module** into the live tree:

   ```bash
   cd /root/.openclaw/workspace/tools/nox-mem
   rsync -av staged-P1/edits/src/lib/answer/ src/lib/answer/
   ```

2. **Bind the real hybrid search** in `src/lib/answer/retrieval.ts` —
   replace the `defaultRawSearch` placeholder with:

   ```ts
   import { hybridSearch } from "../search/hybrid.js"; // adjust path

   async function defaultRawSearch(question: string, topK: number) {
     // Adapter — hybridSearch returns its own shape; map to RawChunk[].
     const hits = await hybridSearch(question, { topK });
     return hits.map((h) => ({
       chunk_id: h.id,
       file_path: h.file_path,
       line_range: h.line_range ?? undefined,
       content: h.content,
       content_hash: h.content_hash ?? undefined,
       score: h.score,
     }));
   }
   ```

3. **Bind the real Gemini provider** in `src/lib/answer/provider.ts` —
   replace `placeholderGemini` with a `@google/genai` client. T4 kickoff
   note: when A3 (PR #8) merges, just `export { llm as default }` from
   the A3 module and delete the placeholder.

4. **Source env BEFORE running** any CLI / test that hits real Gemini
   (CLAUDE.md regra #1):

   ```bash
   set -a; source /root/.openclaw/.env; set +a
   ```

5. **Validate** with a smoke call:

   ```bash
   node -e "import('./dist/src/lib/answer/index.js').then(m => m.answer({question:'What is salience?'})).then(r => console.log(r))"
   ```

   Watch `metadata.model === 'gemini-2.5-flash-lite'` (D41 #1).

---

## What was delivered T11-T14 (this slice)

- **T11 integration tests against real schema** — `src/lib/answer/__tests__/integration-sqlite.test.ts` (10 tests, real `better-sqlite3` in-memory + v11 schema applied; NO mocking the DB)
- **T12 E2E real-Gemini suite (gated)** — `src/lib/answer/__tests__/e2e-gemini.test.ts` (4 tests behind `NOX_E2E_GEMINI=1` + `GEMINI_API_KEY`; cost-capped at <$0.01 per run; SKIP fallback test always passes with reason logged)
- **T13 docs** — `docs/ANSWER.md` (469 lines: overview / architecture mermaid diagram / CLI / HTTP / MCP / configuration / failure modes table / cost model / retry logic / telemetry / roadmap)
- **T14 latency benchmark** — `benchmark/answer-latency.ts` (50 samples × mock LLM 100ms; per-phase p50/p95/p99 + budget pass/fail report; JSON + human output)

**Test counts:** 73 (T1-T10) + 10 (T11) + 1 (T12 gating skip-marker) = **84 tests, 0 fail** baseline. With `NOX_E2E_GEMINI=1` + real key: **88 tests** (4 extra E2E).

## What is NOT done (deferred to follow-up sprints)

See `docs/ANSWER.md §11 Roadmap` for the full list. Highlights:
- **T15 — Golden Q/A eval harness** (gated on Q4 LongMemEval scaffolding)
- **T16 — Cache layer** (LRU memo, conditional on p95 missing target post-deploy)
- **T17 — `--shadow` mode** for A/B testing prompt/model changes
- **T18 — Multi-provider fallback chain** (flash → opus, behind explicit env gate)

---

## Design decisions encoded in this slice

1. **Citation marker format = `[chunk_N]` (1-indexed, bracketed)**
   - LLM never sees real DB ids; marker assigned by `retrieval.ts` is the bridge.
   - Validation = regex `/\[chunk_(\d+)\]/g` + set-membership check.
   - Hallucinated markers (out of range) trigger one retry with stricter prompt.

2. **Token-budget pruning drops lowest-score chunks first** (not oldest)
   - Aligns with kickoff critical decision #2: old chunks can be high-salience.
   - Trust the ranker (salience × section_boost × pain), not recency.

3. **Provider abstraction = minimal interface, fail-fast placeholder**
   - `LLMProvider { name, complete(opts) → result }` matches A3 §3 spec.
   - `placeholderGemini` throws explicit error — prevents accidental network
     calls in CI; VPS apply step swaps in the real client.
   - `MockProvider` is always available; powers integration tests.

4. **`AnswerError` is a real class, not a generic Error**
   - Carries `reason: AnswerFailureReason` + partial `metadata`.
   - Callers (CLI/HTTP) can map `reason` → exit code / HTTP status directly.

5. **Empty retrieval short-circuits BEFORE calling the LLM**
   - Returns canonical "I have no memory matches for this question."
   - Saves tokens; surfaces `failed_reason: 'retrieval_empty'` in metadata.
