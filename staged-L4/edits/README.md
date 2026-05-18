# staged-L4 — Regex-first KG extraction (T1-T6)

**Status:** T1-T6 of L4 implementation. Pure-function extractors + ingest-router decision layer, no DB writes, no Gemini calls, no production src/ modified.

**Branch:** `overnight/2026-05-19/L4-regex-impl-T1-T6`
**Spec:** `specs/2026-05-18-L4-regex-first-extraction.md`
**Inspired by:** [gbrain](https://github.com/garry-tan/gbrain) — MIT, Garry Tan, 16.6k★. Regex pattern ported from `src/core/link-extraction.ts`; adapted for nox-mem domain (DIR_PATTERN whitelist + nuanced hybrid gating instead of enforced authoring convention).

---

## What lives here

```
staged-L4/
├── package.json
├── tsconfig.json
└── edits/
    ├── README.md
    └── src/lib/regex-extract/
        ├── index.ts                  # Public surface
        ├── types.ts                  # NOX_ENTITY_TYPES + EntityRef/CodeRef/FrontmatterRelation
        ├── strip-code.ts             # T1 — stripCodeBlocks (length-preserving)
        ├── patterns.ts               # T2 — DIR_PATTERN + regex constructors
        ├── extractor.ts              # T3 + T5 — extractEntityRefsRegex / extractCodeRefs
        ├── frontmatter.ts            # T4 — extractFrontmatterRelations + minimal YAML parser
        ├── ingest-router-l4.ts       # T6 — decideExtraction + mergeRelations (pure decision layer)
        └── __tests__/
            ├── strip-code.test.ts        # T1 — 6 tests
            ├── extractor.test.ts         # T3 + T5 — 38 tests (positive + negative + edge + code-refs)
            ├── frontmatter.test.ts       # T4 — 16 tests
            └── ingest-router-l4.test.ts  # T6 — 12 tests
```

**Total tests:** 72. **Spec requires ≥30.**

---

## Design Decisions

1. **Pure functions, zero IO.** Production caller (the real `src/lib/ingest-router.ts` on VPS) handles DB writes + Gemini calls + telemetry persistence. This layer is unit-testable without fixtures.
2. **DIR_PATTERN whitelist over open match.** Matching `[[anything/anything]]` causes false-positives in prose (URLs, code, dates). Hard whitelist of 16 nox entity types matches gbrain's design discipline while leaving the FK-id resolution to the caller (MEMORY.md `kg_relations usa FK ids, NÃO strings inline`).
3. **Length-preserving strip.** `stripCodeBlocks` replaces fence/inline-code spans with whitespace of equivalent length (newlines preserved) so any future offset/line-number work over the stripped buffer maps 1:1 to the original — caller can use the same `lastIndex` to reach back into source text.
4. **No external deps.** Minimal YAML parser handles the 6 typed-relation fields (§5 table). Full YAML is the caller's job if they need it — `extractFrontmatterRelationsFromObject` accepts pre-parsed objects.
5. **Skip-Gemini gate is conservative.** Default to running Gemini whenever section is null, type is conversation-like, or regex finds zero refs. CLAUDE.md regra #5 mandates shadow-mode first, so the production wiring will gate this whole module behind `NOX_L4_REGEX_ENABLED=1`.

---

## Run tests locally

```bash
cd staged-L4
npm install
npm test
```

Zero credentials, zero network calls. All fixtures inline in test files.

---

## Cross-refs

- Spec §4: entity types whitelist
- Spec §5: frontmatter typed-relation rules
- Spec §6: regex patterns (port + adaptations)
- Spec §7: skip-Gemini gating logic
- Spec §11: task ID map (T0-T9; this PR covers T1-T6)
