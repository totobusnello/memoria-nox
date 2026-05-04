# Paper Drafts Audit Report

**Auditor:** code-reviewer (Claude Opus 4.7)
**Date:** 2026-05-03
**Inputs:**
- `/Users/lab/Claude/Projetos/memoria-nox/paper/publication/paper-draft-sec1-3.md`
- `/Users/lab/Claude/Projetos/memoria-nox/paper/publication/paper-draft-sec4-7.md`
**Canonical sources:** `RESUMO-EXECUTIVO.md`, `docs/HANDOFF.md`, `docs/ROADMAP.md`, `CLAUDE.md`, `refs.bib`

---

## CRITICAL bugs (must fix before submit)

### C1. nDCG@10 headline is INCONSISTENT and uses STALE n=40 data

- [ ] **paper-draft-sec1-3.md** never states a headline nDCG number but Table 1 / context implies hybrid wins.
- [ ] **paper-draft-sec4-7.md:83** Table 2 reports "0.714 ± 0.001" for hybrid n=50.
- [ ] **paper-draft-sec4-7.md:84** Table 2 reports "Δ +71.4 pp".
- [ ] **paper-draft-sec4-7.md:97** Table 3 mean = "0.674".
- [ ] **paper-draft-sec4-7.md:111** Table 4 "All 50 = 0.674 Run #6 mean".
- [ ] **paper-draft-sec4-7.md:128** Table 5 hybrid = "0.674".
- [ ] **paper-draft-sec4-7.md:176** Table 9 ablation baseline = "0.674".
- [ ] **paper-draft-sec4-7.md:241,287** Discussion + Conclusion: "0.674 vs 0.000" / "71.4 pp".

**Source of truth (HANDOFF.md):**
- HANDOFF.md:90,146,283,540-548,561 — **Run #9 hybrid n=50 = nDCG 0.519** / MRR 0.482 / Recall 0.687 / Prec@5 0.268.
- HANDOFF.md:284 — **Run #13-15 FTS-only n=50 = 0.0123 ± 0.0000** (NOT 0.000 — see C2).
- HANDOFF.md:799 — "0.714 → **0.674** (-0.040)" — that pair is the **n=40** R01b interim run (Run #6 / #7), already superseded.
- HANDOFF.md:283 — n=50 3-run "**Hybrid 0.5213 ± 0.0004**" canonical.

**Verdict:** Both 0.714 AND 0.674 are obsolete n=40 numbers. The R01b/R01c **n=50** baseline that the paper claims to use is **0.5213 (hybrid) vs 0.0123 (FTS)**, gap **~50.9 pp** (NOT 71.4). The paper headline is wrong by ~15 pp and the FTS=0 claim is technically wrong (FTS is 0.012, near-zero but not zero).

**Fix:** Replace every "0.714"/"0.674" with **0.5213** (or the 3-run mean Run #10/#11/#12 figure). Update Δ from "+71.4 pp" → "+50.9 pp". Replace "FTS5 = 0.000" with "FTS5 = 0.012 (effectively zero on natural-language queries)".

---

### C2. FTS5 nDCG=0.000 claim contradicts canonical n=50

- [ ] **paper-draft-sec1-3.md:142** "FTS5 vanilla AND-mode behavior … return zero results" (qualitative — OK).
- [ ] **paper-draft-sec4-7.md:76,82** "FTS5 vanilla BM25 achieves nDCG@10 = 0.000".
- [ ] **paper-draft-sec4-7.md:177** Ablation Table 9 "FTS-only 0.000 ± 0.000".
- [ ] **paper-draft-sec4-7.md:241** §6.1 "FTS5 BM25 achieves nDCG@10 = 0.000".

**Source:** HANDOFF.md:284 = **0.0123 ± 0.0000** (3-run n=50). The earlier 0.000 was an n=5 / n=40 sample artifact.

**Fix:** Use 0.012 (or 0.0123) and frame as "near-zero, structural FTS5 AND-strict behavior". Δ becomes ~50.9 pp instead of 71.4 pp.

---

### C3. Five citations referenced in §4 do NOT EXIST in refs.bib

- [ ] **paper-draft-sec4-7.md:10** `\cite{rogers2021just}` — NOT in refs.bib
- [ ] **paper-draft-sec4-7.md:14** `\cite{manning2008introduction}` — NOT in refs.bib
- [ ] **paper-draft-sec4-7.md:62** `\cite{fuhr2018some}` — NOT in refs.bib
- [ ] **paper-draft-sec4-7.md:119** `\cite{muennighoff2022mteb}` — NOT in refs.bib
- [ ] **paper-draft-sec4-7.md:125** `\cite{yang2018anserini}` — NOT in refs.bib
- [ ] **paper-draft-sec4-7.md:126** `\cite{chen2024bge}` — NOT in refs.bib
- [ ] **paper-draft-sec4-7.md:127** `\cite{wang2023improving}` — NOT in refs.bib

**Fix:** Either (a) add BibTeX entries for all 7 to refs.bib, or (b) remove the citations and rephrase prose. arXiv submission with undefined `\cite{}` keys produces "?" in PDF — embarrassing.

---

### C4. Appendix C uses 4 BROKEN citation keys (different from §2 keys)

- [ ] **paper-draft-sec4-7.md:366** `\cite{edge2024local}` — refs.bib has `edge2024graphrag`
- [ ] **paper-draft-sec4-7.md:369** `\cite{xu2024mem}` — refs.bib has `xu2025amem`
- [ ] **paper-draft-sec4-7.md:370** `\cite{liu2024hirag}` — refs.bib has `huang2025hirag` (note: HiRAG first author is **Huang**, not Liu — refs.bib correction doc l.68-71)
- [ ] **paper-draft-sec4-7.md:371** `\cite{cognee2024}` — refs.bib has `topoteretes2024cognee`

**Fix:** Replace Appendix C citation keys with the canonical refs.bib keys (same as Table 1 in sec1-3 §2.5).

---

### C5. Edge typing claim INCONSISTENCY between drafts

- [ ] **paper-draft-sec1-3.md:166** "reduced the unknown rate to 14%, a 6.1× improvement in labeling precision".
- [ ] **paper-draft-sec4-7.md:52** "After this fix, the unknown rate dropped from 86% to 14% on n=100 sampled relations, a 6.1x improvement."
- [ ] **paper-draft-sec4-7.md:245** "reduction in `unknown` relation rate from 86% to 14% … 6.1x improvement".

**Source of truth (RESUMO-EXECUTIVO.md:72-74 + HANDOFF.md:577,594):**
- **Classification rate (correct labels): 14% → 56% = 4× improvement**
- **Unknown rate: 86% → 44% = decreased 42 pp**
- The "14%" in the drafts is being misapplied as both pre-fix classification AND post-fix unknown — that's a confusion of the two metrics.

**Fix:** Rephrase to: "Classification rate improved from 14% to 56% (4× improvement); equivalently, `unknown` rate dropped from 86% to 44% on n=100 sampled relations." The "6.1×" figure is fabricated (86/14 ≈ 6.1 is the wrong ratio — would only be valid if both numbers measured the same metric, which they don't).

---

### C6. Edge typing enum count CONTRADICTION inside the same paper

- [ ] **paper-draft-sec1-3.md:93** Table 1 row "nox-mem: closed-enum, **24 cat.**"
- [ ] **paper-draft-sec1-3.md:164** Prose "closed-enum `relation_reason` field drawn from **24 categories**".
- [ ] **paper-draft-sec1-3.md:166** "code-side defensive mapping (`RELATION_TYPE_TO_REASON`, **24 entries**)".
- [ ] **paper-draft-sec4-7.md:50** "closed-enum field `relation_reason` with **seven values**".
- [ ] **paper-draft-sec4-7.md:365** Appendix C Table "closed-enum, **7 edge types**".

**Source (CLAUDE.md, HANDOFF.md:585, ROADMAP.md:128):** **7 enum values** in `relation_reason` (`depends_on / derived_from / opposes / extends / replaces / mentions / unknown`). The **24** is the size of `RELATION_TYPE_TO_REASON` defensive map (input aliases like `requires/needs/uses → depends_on`), NOT the output enum.

**Fix:** sec1-3.md must say "closed-enum 7 values, with a 24-entry defensive normalization map (`RELATION_TYPE_TO_REASON`) covering PT-BR + EN aliases that collapse to the 7 canonical reasons." Table 1 cell becomes "closed-enum, 7 reasons". This was flagged in the audit checklist as the #1 confusion risk.

---

### C7. Annotation coverage claim uses wrong figure

- [ ] **paper-draft-sec4-7.md:46** "Annotation coverage (n=12 pain-annotated incident chunks as of 2026-05-03)".

**Source:** No canonical confirms n=12. HANDOFF/CLAUDE.md silent on exact pain-annotated chunk count. This is **UNVERIFIED — needs prod check** via `sqlite3 nox-mem.db "SELECT COUNT(*) FROM chunks WHERE pain > 0.2"`.

**Fix:** Either run the query and use the real number, or rephrase "annotated selectively across an incident-derived subset (exact count pending)".

---

## HIGH priority (should fix before submit)

### H1. Personas: drafts have NO Brazilian/nerd reference
- [ ] **paper-draft-sec1-3.md, paper-draft-sec4-7.md** — neither contains "developer building solo" or "solo nerd entrepreneur".
- RESUMO-EXECUTIVO.md:131 closes with "empreendedor nerd em São Paulo".

**Fix (per audit spec §D):** Add to §7 Conclusion or Author Note: "Built solo by a developer building solo, in São Paulo, over four months of continuous production use." Aligns with the canonical persona register.

### H2. KG entity count freshness
- [ ] **paper-draft-sec1-3.md:162** "~402 entities … ~544 relations".
- [ ] **paper-draft-sec4-7.md:54** "approximately 402 entities and 544 relations".

**Source:** HANDOFF.md:68 — current distribution `unknown=595 / depends_on=260 / mentions=213 / derived_from=35 / extends=3 / replaces=2 / opposes=1` = **1109 relations** (post-B3 backfill, HANDOFF:685). 402 entities is plausible-canonical (CLAUDE.md:64) but **relations grew from 544 → 1109** after kg-reclassify backfill.

**Fix:** Update to "~402 entities, ~1109 relations (post-2026-05-02 backfill from 544 → 1109)". OR explicitly anchor "as of 2026-05-01" so the number is honest at a frozen date.

### H3. Latency p95 < 1s — no source given
- [ ] **paper-draft-sec1-3.md:37,158** "p95 latency below one second".
- [ ] **paper-draft-sec4-7.md:241** implicit baseline.

**Source check:** HANDOFF.md mentions perf_regression alerts (l.310) but no canonical p95 measurement. Same for RESUMO-EXECUTIVO:96 "< 1s em 64K chunks". **UNVERIFIED — needs prod check** via `/api/health.searchLatency` or telemetry query.

**Fix:** Either cite a §5 measurement table or rephrase to "operationally observed sub-second p95" with explicit caveat. Reviewers will flag this number without a source.

### H4. Vector coverage 99.97% — needs prod check
- [ ] **paper-draft-sec1-3.md:37,144** "99.97% vector coverage".
- [ ] **paper-draft-sec4-7.md** absent (good).

**Source:** CLAUDE.md:62 says "~99.97% coverage" (ballpark). HANDOFF.md:166,626 says "**100% embedded**" at the n=64,180 snapshot.

**Fix:** Either use the canonical "~100% (64,180 / 64,180)" or run `curl /api/health | jq .vectorCoverage` to get the exact post-2026-05-02 number. The 99.97% is stale.

### H5. RRF k=60 parameter — verify implementation
- [ ] **paper-draft-sec1-3.md:130,156,83** "RRF with k=60".
- [ ] **paper-draft-sec4-7.md** consistent.

**Source:** CLAUDE.md:72 confirms "RRF fusion (k=60)". OK ✅. (Auditor note: this matches the audit spec §F).

### H6. Hybrid Δ uses wrong baseline ratio
- [ ] **paper-draft-sec1-3.md:241** §6.1 in sec4-7 actually: "gap of 71.4 pp".
- [ ] **paper-draft-sec4-7.md:84,241** "+71.4 pp".

Cascading from C1+C2: with Hybrid 0.5213 and FTS 0.0123, the real Δ is **+50.9 pp** (or report the n=40 gap from HANDOFF:639 of "97.7% relative loss" if framed as relative).

### H7. Schema migration count — sec1-3 vs Appendix A consistency
- [ ] **paper-draft-sec1-3.md:108,140** "12 schema migrations" / "v1 through v12".
- [ ] **paper-draft-sec4-7.md:306** Appendix A table covers v1–v12.
- Both consistent ✅, but draft-sec1-3.md:108 says "operated continuously since March 2026 with 12 schema migrations and **no data loss**" — incident 2026-04-25 caused **183 entity records to lose section/retention** (technically NOT data loss but metadata loss). Recovered via re-ingest.

**Fix:** Soften to "no irrecoverable data loss" or add "(see §6.2 incident discussion for one metadata-loss event recovered via re-ingestion)".

### H8. Months-of-production count
- [ ] **paper-draft-sec1-3.md:37,108** "four months of continuous deployment / since March 2026".
- ✅ matches CLAUDE.md and audit spec §A. But §6.3 line 259 says "approximately four months (March–May 2026)" — internally consistent.

---

## MEDIUM (consider fixing)

### M1. Hybrid result Run inconsistency in Table 3
- **paper-draft-sec4-7.md:90-95** Table 3: Run 1 = 0.714, Run 2 = 0.674, Run 3 = TBD, Mean = 0.674.

If Run 1 (0.714) ≠ Run 2 (0.674) by 0.040, std cannot be "<0.001 expected". Note in caption acknowledges "ranking changes between runs" but reviewers will see Run 1/2/3 as a 3-run replication and think the std is wrong. **Fix:** clearly label as "diagnostic runs across config changes, not 3-run replication" OR drop Run 1 entirely.

### M2. Pain default 0.2 — verify schema
- **paper-draft-sec1-3.md:140** "(`pain` REAL DEFAULT 0.2)" ✅ matches CLAUDE.md:65.

### M3. Section_boost values (compiled 2.0 / frontmatter 1.5 / timeline 0.8 / legacy 1.0)
- **paper-draft-sec1-3.md:156** matches CLAUDE.md:65 ✅.

### M4. Discord alert + cron 15-min interval
- **paper-draft-sec1-3.md:188** "cron checks every 15 minutes and alerts via Discord" ✅ matches HANDOFF context.

### M5. Honest disclosure flags present and correct
- §4.1 single-curator declared ✅
- §6.3 internal-curator bias declared ✅
- §6.3 short corpus horizon declared ✅
- §6.3 single-author validation declared ✅

---

## VERIFIED OK

- ✅ Stack: TypeScript + better-sqlite3 + sqlite-vec + FTS5 (CLAUDE.md:57)
- ✅ Storage: SQLite single DB (sec1-3.md:108)
- ✅ HTTP API port: 18802 (CLAUDE.md:77, sec1-3.md:134)
- ✅ Embeddings: Gemini 3072d / `gemini-embedding-001` (CLAUDE.md:72, sec1-3.md:144)
- ✅ RRF k=60 (CLAUDE.md:72, sec1-3.md:130)
- ✅ Salience formula `recency × pain × importance` (CLAUDE.md:67, sec1-3.md:172)
- ✅ Pain ∈ [0.1, 1.0] (sec1-3.md:39, sec4-7.md:34)
- ✅ Schema v12 (HANDOFF.md:166, both drafts)
- ✅ 6 agents Atlas/Boris/Cipher/Forge/Lex/Nox (NOT 7) (CLAUDE.md, both drafts:13,196)
- ✅ 50 golden queries R01b (HANDOFF.md:90, sec4-7.md:14)
- ✅ Negatives = 6 queries 12% of set (sec4-7.md:16, HANDOFF.md:548)
- ✅ Hybrid 3 layers FTS5 → Gemini → RRF (CLAUDE.md:72, sec1-3.md:130-131)
- ✅ Shadow telemetry counts 191 / 16,608 / 45,743 (sec1-3.md:41, sec4-7.md:30 — internally consistent; cannot verify against external source)
- ✅ Incident 2026-04-25 (CLAUDE.md:103, both drafts)
- ✅ Incident 2026-05-01 sed -i (CLAUDE.md MEMORY.md, sec4-7.md:251)
- ✅ Dates: arXiv 2026-05-19, Blog 05-20, HN 05-21 (RESUMO:127-129, sec4-7 §7 mentions 05-19)
- ✅ Cross-section pain calibration anchors (0.1/0.3/0.5/0.7/1.0 vs 0.1/0.2/0.3-0.4/0.5-0.7/0.8-0.9/1.0 — different granularities between sec1-3.md:177 and sec4-7.md:36; minor inconsistency but both internally well-formed). **MINOR**: align granularity.

---

## Citations

**All `\cite{}` keys vs refs.bib audit:**

| Key | In refs.bib? | Used in |
|---|---|---|
| `edge2024graphrag` | ✅ | sec1-3 |
| `edge2024local` | ❌ MISSING | **sec4-7 Appendix C — BUG** |
| `packer2023memgpt` | ✅ | both |
| `chhikara2025mem0` | ✅ | both |
| `xu2025amem` | ✅ | sec1-3 |
| `xu2024mem` | ❌ MISSING | **sec4-7 Appendix C — BUG** |
| `huang2025hirag` | ✅ | sec1-3 |
| `liu2024hirag` | ❌ MISSING | **sec4-7 Appendix C — BUG (also wrong first author)** |
| `topoteretes2024cognee` | ✅ | sec1-3 |
| `cognee2024` | ❌ MISSING | **sec4-7 Appendix C — BUG** |
| `lewis2020rag` | ✅ | sec1-3 |
| `cormack2009rrf` | ✅ | sec1-3 |
| `guo2024hipporag` | ✅ | sec1-3 |
| `sarthi2024raptor` | ✅ in refs.bib | not cited in drafts |
| `rogers2021just` | ❌ MISSING | sec4-7:10 |
| `manning2008introduction` | ❌ MISSING | sec4-7:14 |
| `fuhr2018some` | ❌ MISSING | sec4-7:62 |
| `muennighoff2022mteb` | ❌ MISSING | sec4-7:119 |
| `yang2018anserini` | ❌ MISSING | sec4-7:125 |
| `chen2024bge` | ❌ MISSING | sec4-7:126 |
| `wang2023improving` | ❌ MISSING | sec4-7:127 |

**Total missing/broken keys: 11** — 4 broken in Appendix C (key drift) + 7 W2 baseline / methodology refs missing from refs.bib.

**All citations exist in refs.bib: NO**

---

## Final verdict

**NEEDS FIXES** — 7 CRITICAL + 8 HIGH + 1 MEDIUM open.

The drafts cannot be submitted as-is. The primary blockers are:

1. **Headline number wrong by ~15 pp** (using stale n=40 0.674/0.714 instead of canonical n=50 0.5213). Fixing this is mechanical but propagates through 8+ tables and 4+ prose mentions.
2. **24 vs 7 enum confusion** — exactly the bug the audit checklist warned about, present in §3.4 and Table 1 of sec1-3 while sec4-7 §4.4 / Appendix C correctly use 7. The two drafts contradict each other on the most novel KG claim.
3. **11 broken/missing citations** — 4 are pure key drift in Appendix C (cheap fix) and 7 are methodology references that need real BibTeX entries before LaTeX will compile cleanly.
4. **Edge typing improvement is misframed** — "86% → 14%, 6.1×" conflates two different metrics; correct framing is "14% → 56% classification (4×) / 86% → 44% unknown".

Once C1–C7 + H1 are addressed, the paper has a defensible empirical core: hybrid pipeline structurally beats FTS-only by ~50 pp on natural-language queries over a 64K-chunk operational corpus, edge typing improved 4× post-defensive-map, and the shadow discipline mechanism is novel in the literature.

**Recommendation:** REQUEST CHANGES — block submit until C1–C7 fixed; H1–H8 should be batched in the same revision.

