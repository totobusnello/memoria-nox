# staged-A3 — Provider abstraction core (T1-T8)

**Status:** T1-T8 of A3 implementation kickoff (PR #16). Interfaces + Gemini
real impls + OpenAI/Anthropic/Voyage stubs + registry + boot-time health check.

**Branch:** `overnight/2026-05-19/A3-impl-T1-T8`
**Spec (kickoff):** `specs/2026-05-18-A3-implementation-kickoff.md`
**Pillar:** A (Autonomy) — "Your memory. Your provider. Your bill. No middlemen."
**D41:** Gemini-only default (locked) — gemini-embedding-001 (3072d) +
gemini-2.5-flash-lite. Swap is opt-in only.

---

## What lives here

```
staged-A3/
├── package.json                                # node:test runner + tsc
├── tsconfig.json                               # strict ES2022 NodeNext
└── edits/
    ├── README.md                               # this file
    └── src/providers/
        ├── index.ts                            # T2 registry + T8 boot health
        ├── types.ts                            # HealthStatus + typed errors
        ├── embedding/
        │   ├── types.ts                        # T1 EmbeddingProvider interface
        │   ├── gemini.ts                       # T3 REAL Gemini wrapper (fetch)
        │   ├── openai.ts                       # T5 stub (throws on embed)
        │   └── voyage.ts                       # T7 stub (throws on embed)
        ├── llm/
        │   ├── types.ts                        # T1 LLMProvider interface
        │   ├── gemini.ts                       # T4 REAL Gemini wrapper (fetch)
        │   ├── openai.ts                       # T5 stub (throws on complete)
        │   └── anthropic.ts                    # T6 stub (throws on complete)
        └── __tests__/
            ├── factory.test.ts                 # 9 cases — selectXProvider
            ├── conformance.test.ts             # 10 cases — interface shape
            ├── gemini.test.ts                  # 14 cases — mock-based fetch
            └── health.test.ts                  # 6 cases — bootProviderHealth
```

**Test count:** 39 cases across 4 files. **No real network calls** — all Gemini
provider tests use injected `fetchFn` stubs.

---

## Run tests locally

```bash
cd staged-A3
npm install        # one-time: typescript + @types/node
npm test           # build + run all node:test files
```

Tests require ZERO credentials (Gemini API key uses a fake `AIza...` literal
that never leaves the test harness).

---

## How to apply on the VPS (after PR merges)

1. **Copy the module** into the live tree:

   ```bash
   cd /root/.openclaw/workspace/tools/nox-mem
   rsync -av staged-A3/edits/src/providers/ src/providers/
   ```

2. **No prod call sites changed yet** — T13 (refactor 15 call sites) lands
   in a separate PR. This patch is **additive only**.

3. **Smoke test on VPS** (real key required):

   ```bash
   set -a; source /root/.openclaw/.env; set +a
   node -e "
     import('./dist/src/providers/index.js').then(async (m) => {
       const e = m.selectEmbeddingProvider();
       const l = m.selectLLMProvider();
       const r = await m.bootProviderHealth({ embedding: e, llm: l, failFast: false });
       console.log(JSON.stringify(r, null, 2));
     });
   "
   ```

   Expect: `allOk: true`, both latencyMs under 500ms.

---

## Design decisions encoded in this slice

1. **Stubs return `ok=false` from `healthCheck()` deterministically.**
   - Rationale: registry can probe every registered provider at boot without
     un-activated stubs throwing. User who keeps Gemini defaults never sees a
     spurious failure. Caller opts in by passing the stub to
     `bootProviderHealth()` only after activating it.

2. **Gemini wrapper uses Node 18+ global `fetch` + injected `fetchFn` test seam.**
   - No SDK dependency (`@google/genai` is heavyweight). The wire shape matches
     `src/lib/gemini-client.ts` so T13 refactor is byte-equivalent.
   - `fetchFn` injection makes 100% of tests offline.

3. **`MissingKeyError` thrown at construction for Gemini only; stubs lazy.**
   - Stubs MUST NOT validate keys at construction — otherwise users with only
     `GEMINI_API_KEY` set can't even import the registry (every stub would
     scream). Validation moves to `embed()`/`complete()` in A3.1 when the stub
     becomes a real impl.

4. **`HealthStatus.error` is REQUIRED iff `ok=false`.**
   - Asserted by conformance tests. Caller can rely on the error field being
     populated for any failure path — including timeout, HTTP error, malformed
     response. Never echoes raw API key bytes (regex-redacted via `redactSecrets`).

5. **Boot health probe wraps in 5s timeout via `Promise.race`.**
   - A hung Gemini API (T9 spec acceptance: probe <5s) cannot block boot
     indefinitely. Timer cleared in `finally` to avoid leaking the timeout
     (lesson 2026-05-03 audit: leaked handles in serial pipelines).

---

## What is NOT done (next sprint)

- **T9 — `/api/health` endpoint extension** (separate PR; touches HTTP layer)
- **T10 — LLM fallback chain** (high blast radius, isolated review)
- **T11 — Cost telemetry write-behind** (schema v11 already merged)
- **T12 — Daily cost cap + bypass audit**
- **T13.a/b/c — Refactor 15 call sites** (3 PRs, sequential)
- **T14 — Full regression suite** (bit-identical embeddings vs pre-A3 baseline)
- **T15 — `nox-mem reembed` placeholder CLI**
- **T16 — `docs/PROVIDERS.md` + runbook**

Per kickoff §11, this PR is the "foundations" slice — additive, zero behaviour
change in prod, fully revertible.

---

## LOC budget

| Area | LOC |
|---|---|
| Interfaces + types | ~120 |
| Gemini impls (embedding + LLM) | ~270 |
| Stubs (3 providers) | ~150 |
| Registry + boot health | ~190 |
| Tests (4 files) | ~520 |
| **Total** | **~1250** |

Tests intentionally heavy — A3 is the swap surface for the whole product;
conformance + secret-hygiene coverage is non-negotiable.
