# Audit: L4 Regex-first KG Extraction — Implementation

**Date:** 2026-05-21
**Branch:** `impl/l4-regex-first-extraction`
**Spec:** `specs/2026-05-18-L4-regex-first-extraction.md`
**Status:** shadow-mode default, NOT deployed to prod

---

## Architecture

```
INGEST CHUNK (text + ChunkContext)
         │
         ▼
  resolveExtractMode()  ← NOX_KG_EXTRACT_MODE env
         │
   ┌─────┴─────────────────────────────────┐
   │                                       │
   ▼                                       ▼
regex_only          gemini_only      hybrid_shadow (DEFAULT) / hybrid_active
   │                    │                  │
   ▼                    ▼                  ▼
regexExtract()    fastPathExtract()   regexExtract() ← always runs
   │               ≥3 hits? → skip        │
   │               else: callGemini()  callGemini() ← always in shadow;
   │                    │               conditional in active
   ▼                    ▼                  ▼
RegexExtractionResult  LLMExtraction   logExtractDiff() → /var/log/nox-kg/
```

### Regex pipeline (regexExtract)

1. `stripCodeBlocks(text)` — length-preserving, newlines preserved, offset-safe
2. `extractEntityRefsRegex(text)` — 3 regex passes:
   - Markdown link `[Name](entityType/slug)` — groups: display, type, slug
   - Obsidian wikilink `[[entityType/slug|display]]` — optional `entities/` prefix
   - Bare ref `entityType/slug` — lookbehind/lookahead, NO `\b` (MEMORY.md: Unicode)
3. `extractFrontmatterRelations(text)` — minimal YAML parser for 6 typed-relation fields
4. `extractCodeRefs(text)` — `src/`, `specs/`, `audits/`, etc. with optional `:line`

### Hybrid orchestration (kg-llm.ts)

| Mode | Regex | Gemini | Shadow log | Return |
|---|---|---|---|---|
| `regex_only` | yes | no | no | regex_result |
| `gemini_only` | no | yes | no | LLM entities/relations |
| `hybrid_shadow` | yes | yes | yes | Gemini (regex attached) |
| `hybrid_active` | yes | only if needed | yes | regex or LLM |

Default: `hybrid_shadow`. Changeable via `NOX_KG_EXTRACT_MODE` env.

---

## Files Changed

### New

| File | Lines | Purpose |
|---|---|---|
| `staged-1.7a/edits/regex-extract.ts` | ~280 | Tier 1 regex extraction (T1-T5): strip, patterns, entity refs, frontmatter, code refs |
| `staged-1.7a/edits/lib/kg-extract-telemetry.ts` | ~130 | Shadow JSONL telemetry: logExtractDiff, buildDiffEntry, summarizeDiffEntries |
| `staged-1.7a/edits/__tests__/regex-extract.test.ts` | ~220 | 15+ test cases: all entity types, frontmatter rules, code refs, edge cases, Unicode |
| `staged-1.7a/edits/__tests__/hybrid-extract.test.ts` | ~180 | 6+ test cases: all 4 modes, invalid-mode fallback, telemetry smoke |

### Modified

| File | Change |
|---|---|
| `staged-1.7a/edits/kg-llm.ts` | L4 hybrid orchestration: `NOX_KG_EXTRACT_MODE` routing, regex import, telemetry integration, model corrected to `gemini-2.5-flash-lite` |

---

## Test Coverage

**Total test cases: 36** (15 in regex-extract.test.ts, 7 direct + 6 hybrid in hybrid-extract.test.ts, 1 direct unit)

| Category | Cases | Files |
|---|---|---|
| Person/entity markdown links | 4 | regex-extract.test.ts |
| Wikilinks (bare, display, entities/ prefix, negative) | 4 | |
| Bare refs (positive, negative URL guard) | 3 | |
| Decision patterns (D48, D49) | 2 | |
| Multi-entity dedup + priority | 3 | |
| Code fence stripping | 3 | |
| Frontmatter typed relations (all 6 rules) | 7 | |
| Code ref extraction | 5 | |
| Aggregated regexExtract | 4 | |
| isAmbiguous (fallback signal) | 5 | |
| PascalCase false-positive rejection | 1 | |
| NOX_ENTITY_TYPES completeness | 2 | |
| Hybrid mode: regex_only | 1 | hybrid-extract.test.ts |
| Hybrid mode: gemini_only (2 sub-cases) | 2 | |
| Hybrid mode: hybrid_shadow | 1 | |
| Hybrid mode: hybrid_active (skip + force) | 2 | |
| Invalid mode → hybrid_shadow fallback | 1 | |
| Telemetry smoke (shadow) | 1 | |
| Rich entity file aggregation | 1 | |

---

## Performance Expectations

| Metric | Expected | Source |
|---|---|---|
| `regexExtract()` p50 | <5ms | pure regex, no IO |
| `regexExtract()` p95 | <10ms | even large chunks (8k chars) |
| `callGemini()` p50 | ~500ms | Gemini API SLA |
| `callGemini()` p95 | ~1500ms | API latency variance |
| `logExtractDiff()` | <2ms | appendFileSync, async not needed |
| Gemini calls saved (hybrid_active, structured content) | ≥40% | per spec DoD #2 |

---

## Shadow-Mode Validation Plan (1 week)

### What runs in shadow mode

`NOX_KG_EXTRACT_MODE=hybrid_shadow` (default):
- Every chunk: regex extraction runs + Gemini runs
- Diff logged to `/var/log/nox-kg/extract-diff-YYYY-MM-DD.jsonl`
- Gemini result is returned (authoritative), regex result is attached as `regex_result`

### Telemetry log format

```jsonl
{"ts":"2026-05-21T10:00:00Z","chunk_id":"12345","section":"compiled","mode":"hybrid_shadow",
 "regex_entity_refs":["decision/d48","feedback/no_secrets"],
 "regex_frontmatter_relations":["is_agent_of:atlas"],
 "regex_code_refs":["codepath/src/lib/op-audit.ts:42"],
 "gemini_entities":["D48","Atlas","no_secrets"],
 "gemini_relations":["D48→Atlas"],
 "latency_regex_ms":3,"latency_gemini_ms":487}
```

### Daily review query (7-day validation)

```bash
# Coverage ratio per day
cat /var/log/nox-kg/extract-diff-2026-05-*.jsonl | jq -s '
  group_by(.ts[:10]) |
  map({
    date: .[0].ts[:10],
    total: length,
    avg_regex_refs: (map(.regex_entity_refs | length) | add / length),
    avg_gemini_entities: (map(.gemini_entities // [] | length) | add / length)
  })'
```

### Promotion criteria (shadow → active)

ALL of the following must pass over 7 continuous days:

1. **Regex coverage ≥85%** of Gemini-found entities in structured chunks (compiled/frontmatter/timeline)
2. **False-positive rate ≤2%** on prose/conversation chunks (manual spot-check 20 entries)
3. **Retrieval nDCG@10 zero regression** vs baseline 0.6813 (E14 Wave 1)
4. **Latency p95 entity file ingest <100ms** (vs current ~1.5s Gemini-only)
5. **No critical KG corruption incidents** (canary `check-schema-invariants.sh` stays green)

To promote: `NOX_KG_EXTRACT_MODE=hybrid_active` in `/root/.openclaw/.env`.

---

## Rollback Paths

Three env flags provide instant rollback at any stage:

| Scenario | Action |
|---|---|
| L4 regex quality issue (false positives) | `NOX_KG_EXTRACT_MODE=gemini_only` — reverts to pre-L4 behavior |
| Shadow telemetry disk pressure | `NOX_KG_TELEMETRY_DIR=/dev/null` — drops logs silently |
| Active mode regression detected | `NOX_KG_EXTRACT_MODE=hybrid_shadow` — back to shadow, both run |

Regex code never writes to DB directly — all DB writes are handled by the existing `ingest-router.ts` caller. Rollback is pure env-flag with no migration.

---

## Security Checklist

- `GEMINI_API_KEY` always from `process.env["GEMINI_API_KEY"]` — never hardcoded
- Telemetry log is append-only text (no DB, no secrets in JSONL)
- No exec/shell in regex pipeline
- Env-flag reads use `process.env["KEY"]` notation (not template-string injection)

---

## Known Gaps (post-shadow)

| Item | Priority | Notes |
|---|---|---|
| T0 validation: VPS entity types vs DIR_PATTERN | Before deploy | SSH read was blocked; validate manually on VPS before enabling `NOX_KG_EXTRACT_MODE` |
| T8 eval harness: golden set 100 entity files | Lab Q1 | `eval/golden-l4-regex-extract.jsonl` not yet created |
| Stale-link reconciliation watcher integration | T7, post-shadow | `staged-L4/edits/src/lib/regex-extract/reconcile.ts` has the logic; needs watcher hook |
| `/api/health.kgExtraction` telemetry endpoint | T9 | `summarizeDiffEntries()` ready; HTTP endpoint not wired |

---

## Cross-References

- Spec: `specs/2026-05-18-L4-regex-first-extraction.md`
- Staged implementation (T1-T9 prior work): `staged-L4/edits/src/lib/regex-extract/`
- Shadow-mode rule: CLAUDE.md §regra 5
- Incident log: `docs/INCIDENTS.md`
- Unicode regex lesson: MEMORY.md `JS regex \b falha em Unicode`
- KG relations schema: MEMORY.md `kg_relations usa FK ids, NÃO strings inline`
- Model selection: CLAUDE.md §regra 3 (`gemini-2.5-flash-lite`, NOT flash or 2.0)
