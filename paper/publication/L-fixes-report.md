# L-Fixes Report — Critic Review Polish Pass

Applied 2026-05-03. All 10 L-severity bugs fixed across 3 files (paper-abstract.md, paper-draft-sec1-3.md, paper-draft-sec4-7.md). appendix-d-shadow-case-study.md required no changes.

---

## L1 — Mixed PT-EN: "paridad"

**File:** `paper-draft-sec1-3.md:75`
**Before:** `Cognee achieves 3/5 on our architectural paridad dimensions (Table 1).`
**After:** `Cognee achieves 3/5 on our architectural parity dimensions (Table 1).`

---

## L2 — HTML comment leak (sec1-3)

**File:** `paper-draft-sec1-3.md:184`
**Before:** `...44% [NEEDS VALIDATION §5, n=100 sample]. <!-- per HANDOFF.md:577,594 --> This experience...`
**After:** `...44% [NEEDS VALIDATION §5, n=100 sample]. This experience...`

---

## L3 — HTML comment leaks (sec4-7, 2 occurrences)

**File:** `paper-draft-sec4-7.md:76`
**Before:** `Table 2 shows the primary comparison. <!-- per HANDOFF.md:283-284 --> FTS5 vanilla BM25 achieves`
**After:** `Table 2 shows the primary comparison. FTS5 vanilla BM25 achieves`

**File:** `paper-draft-sec4-7.md:279`
**Before:** `hybrid retrieval with a semantic layer is the minimum viable design. <!-- per HANDOFF.md:283-284 -->`
**After:** `hybrid retrieval with a semantic layer is the minimum viable design.`

---

## L4 — Inconsistent "knowledge graph" capitalization

No normalization required beyond existing usage. Audit confirmed all occurrences in the four target files follow the rule already: lowercase "knowledge graph" in prosa corrente, "Knowledge Graph" in the §2.1 heading, "KG" in technical inline references. No changes applied (already consistent).

---

## L5 — Abstract trim note in body

**File:** `paper-abstract.md:13–15`
**Before:**
```
**Word count:** ~302 words (trim note below)

> **Trim note for arXiv submission:** If the venue enforces 250 words strictly, remove the parenthetical...
```
**After:**
```
**Word count:** ~302 words
```
Trim note removed entirely.

---

## L6 — Run-on sentence sec4-7 §5 closing paragraph

**File:** `paper-draft-sec4-7.md:271`
**Before:** Single run-on paragraph ending with both the deferred experiments and the section transition in one sentence.
**After:** Added explicit sentence break: "These deferrals do not affect the architectural contribution claims." before the section-6 transition sentence. Four distinct sentences now instead of a compound clause chain.

---

## L7 — Table 1 (sec1-3) and Appendix C duplicate

**File:** `paper-draft-sec4-7.md` — Appendix C
**Before:** Appendix C contained a full independent 5-axis feature comparison table duplicating the 7-axis Table 1 in §2.5.
**After:** Appendix C now opens with "See Table 1, §2.5 for the full seven-axis architectural comparison across all surveyed systems." followed by the 5-axis distilled table with an explanatory note that it is a reviewer quick-reference subset of Table 1. Table 1 is the canonical source; Appendix C is the derivation.

---

## L8 — Inconsistent "nDCG" / "nDCG@10" notation

**File:** `paper-draft-sec4-7.md` — 3 occurrences fixed:
- Line 4 (draft status note): `nDCG=0.5213` → `nDCG@10=0.5213`
- Line 303: `nDCG scores cannot be compared` → `nDCG@10 scores cannot be compared`
- Line 399 (Appendix B.4): `absolute nDCG numbers improved` → `absolute nDCG@10 numbers improved`

Also fixed in Appendix C table header: `nDCG/MRR/Recall` → `nDCG@10/MRR/Recall`

No occurrences found in paper-abstract.md or appendix-d-shadow-case-study.md.

---

## L9 — `\texttt{<!-- pain: 0.X -->}` markdown-LaTeX hybrid

**File:** `paper-draft-sec1-3.md:195`
**Before:** `annotated via \texttt{<!-- pain: 0.X -->} markers in entity files`
**After:** `annotated via \texttt{pain: 0.X} markers in entity files`

**File:** `paper-draft-sec4-7.md:34`
**Before:** `using the \`<!-- pain: X.X -->\` comment syntax in entity files`
**After:** `using the \`pain: X.X\` marker syntax in entity files`

Both occurrences — LaTeX `\texttt{}` form and markdown backtick form — cleaned.

---

## L10 — Conclusion tagline (arXiv version)

**File:** `paper-draft-sec4-7.md:337` (§7 Conclusion, last line)
**Before:** `The incidents are in the log. The log is in the schema. The schema is in this paper.`
**After:** `We invite verification and contributions via the public repository.`

Tagline preserved in RESUMO-EXECUTIVO.md and distribution pieces (not in scope for this pass, confirmed not modified).

---

## Validation

```
grep -r "<!-- per\|paridad\|nDCG[^@]" paper/publication/paper-abstract.md \
  paper/publication/paper-draft-sec1-3.md \
  paper/publication/paper-draft-sec4-7.md \
  paper/publication/appendix-d-shadow-case-study.md
```

**Result: zero matches.** All three validation targets clean.
