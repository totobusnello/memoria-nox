# BLOCKED — Prerequisites Before Starting Listed Work

> Filed during overnight automode push. Items here block downstream impl kickoffs.

---

## 2026-05-18 — P5a — Internal event bus refactor (prerequisite for P5)

**Blocks:** `specs/2026-05-18-P5-implementation-kickoff.md` tasks T2-T15.

**Finding:** During P5 kickoff planning (2026-05-18), pre-flight grep across `src/` returned **zero results** for `EventEmitter` and zero internal `emit(` patterns suitable for reuse. P5 spec (PR #10) assumed an event bus exists; it does not.

**What's needed (P5a, est. 3-4h):**

1. Add `src/lib/events/bus.ts` exporting a singleton `EventEmitter` with:
   - listener cap (100, warn on overflow)
   - non-blocking emit (`setImmediate` wrapper)
   - microbenchmark <100µs per emit
2. Plumb emit hooks into existing producers (NO new functionality, only event surfacing):
   - `src/ingest-router.ts` — after redact + insert succeeds → `emit("chunk.created", {...})`
   - `src/api/search.ts` (or hybrid search caller) — after RRF fusion → `emit("search.executed", {...})`
   - `src/lib/op-audit.ts` — inside `withOpAudit()` → `emit("op_audit.started" / "op_audit.completed", {...})`
   - `src/kg/extract.ts` — per entity/relation insert → `emit("kg.entity.created" / "kg.relation.created", {...})`
   - `chunk.deleted` — either trigger-side notify or wrapper around `deleteChunks()` → `emit("chunk.deleted", {...})`
3. Verify no latency regression on ingest/search benchmarks (async emit must not block DB write).
4. Unit test: 1000 sequential emits aggregate <10ms; listener cap enforced.

**Why not part of P5 itself:** P5 is the **viewer** (UX surface). Refactoring producers to emit events is a **cross-cutting infra concern** that belongs in its own PR for clean diff + reviewability + rollback safety.

**Suggested branch:** `overnight/2026-05-1x/P5a-event-bus-refactor`

**Override:** if Toto wants to bundle P5a + P5 in single PR, fine — just expand P5 timeline to 25-32h (per kickoff §12) and label commits clearly.

**Verification command before unblocking:**
```bash
grep -rl "EventEmitter" /Users/lab/Claude/Projetos/memoria-nox/src/lib/events/
# must return: src/lib/events/bus.ts
```

---
