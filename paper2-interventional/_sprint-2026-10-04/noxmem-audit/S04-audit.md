# S04 audit — §2 System Architecture, §3 Memory Pipeline, §4 Hybrid Search

Paper: paper/paper-tecnico-nox-mem.md (lines 220–471; identical to scratchpad base-audit.md, diff = 0 lines).
Code checked: ~/Claude/Projetos/nox-workspace/tools/nox-mem/src (HEAD 416b009f, 2026-10-04 — live source tree, schema v18)
and memoria-nox/staged/{1.6,1.7a,P1,P3}/edits (the paths the paper cites).
No git commands run, nothing published, nobody contacted.

## Verified OK
- §2.3 type counts sum 499+161+126+34+21+11+8+6+6+2 = 874 = Workspace row of §2.4.
- §2.4 chunks 185+148+182+30+31+31+874 = 1,481. 67,724 on 2026-09-09 = 239+239+387+66,859 (CLAUDE.md, /api/health).
- §2.5 answer: DEFAULT_TOPK=8, TOPK 1..20, DEFAULT_MODEL gemini-2.5-flash-lite (staged/P1/edits/src/lib/answer/config.ts:16-25); hallucination_after_retry (ANSWER.md:19); as-of / changed-since predicates (staged/P3/edits/search.ts:49-55); `w` unit (dates.ts:29); schema v18 (P3/DEPLOY.md:66; db.ts:26 SCHEMA_VERSION=18).
- §3.1 debounce 2000 ms (watch.ts:61); >500 words sub-split, <20 merged (ingest.ts:59,71); auto-vectorize LIMIT 20 (ingest.ts:188); heartbeat file /tmp/nox-mem-watcher-heartbeat (nox-mem-health.sh:91).
- §3.3 semantic threshold 0.85 (dedup.ts:36).
- §3.4.3 weights 0.55/0.15/0.10/0.20 (staged/1.7a/edits/salience.ts:229-232); mode default shadow (salience.ts:33-36); retention table (salience.ts:45-56).
- §3.5 83/46,824 serves = 0.18%, median 48d, 931, 3 searches + 0 answers (specs/2026-06-07-D2-brief-diversity-term.md:11-15); 146→67→3, 184/184, 190, ~45/h (docs/HANDOFF.md:2600-2608, 2627-2634). These are handoff/spec numbers, not raw artifacts.
- §4.1 bm25(chunks_fts,1.0,0.5,0.5) (search.ts:415); RRF k=60 (search.ts:592); 7-day window (search.ts:426,525); semantic 0-10 normalization (search.ts:528); dedup key source_file + first 50 chars (search.ts:680); RETRIEVAL_DOCUMENT/QUERY (embed.ts:94,131).
- §4.3 cross-search opens agent DBs readonly (cross-search.ts:30); 6 agents + workspace.

## Defects (detail in StructuredOutput)
HIGH
1. §3.4.1 crystallize: code (crystallize.ts:1-60; api-server.ts:253-273) saves a caller-supplied procedure as chunk_type='procedure'. No LLM, no pending→lesson promotion, no entity file, no withOpAudit (withOpAudit callers in src: backfill-*, compact, graphify-ingest, index(kg-merge/kg-confirm/kg-restore), prune-orphan-vectors, reindex*, salience — not crystallize). Footnote [^crystallize-src] "wrapped by withOpAudit()" also false.
2. §3.4.2 pain auto-adjust: no code path writes `pain` from retrieval/feedback/consolidation (grep of SET pain in repo: only eval scripts). pain set at ingest by inferPain() keyword regex (salience.ts:167) + v9 backfill (memory note feedback_pain_column_is_topical_not_episodic: 62,425 at 0.2, 4,129 at 0.5, 566 at 1.0).
3. §3.4.4 reflect: reflect() returns an answer; only write is INSERT INTO reflect_cache (reflect.ts:321), TTL-based not LRU; no chunk write, no CONFIDENCE_DERIVED use in reflect.ts.
4. §3.4.5 consolidate: consolidate.ts calls Gemini 2.5 flash-lite then Groq; no reflect, no crystallize, no withOpAudit, no VACUUM INTO.
MEDIUM
5. §4.1 boosts are additive deltas since 2026-05-19 (search.ts:36-42: +1.0/+0.5 FTS, +0.5/+0.2 semantic) over 5 types (decision, lesson, person, project, pending), not 2.0x/1.5x/1.2x multipliers on decision+lesson.
6. FTS tokenizer: migrateToV5 (db.ts:615-642) replaced porter with 'unicode61 remove_diacritics 2' (§2.2 and §4.1 say porter unicode61).
7. Query sanitizer replace(/[^\p{L}\p{N}\s]/gu," ") (search.ts:402) strips hyphens.
8. Watcher: ALLOWED_EXTS .md,.txt; .json and .jsonl in SKIP_PATTERNS (watch.ts:35-43). MEMORY.md/SESSION-STATE.md exclusion not found in watch.ts (not verifiable).
9. Dedup fallback threshold 0.7 (dedup.ts:85), not 60%; isDuplicate is imported by consolidate.ts / session-distill.ts, not ingest.ts.
10. §3.4.3 "empirically outperformed the strict multiplicative product ... §5.1 reports the ablation": §5.1.2 compares active (A8 0.6237) vs shadow (A7 0.6155); no additive-vs-multiplicative arm under otherwise equal config. G3 (multiplicative) vs G5 differs in several components.
11. §2.2 "schema (version 3)": SCHEMA_VERSION=18; chunks column list omits pain, retention_days, section, section_boost, importance, access_count, last_accessed_at, tier, source_type used in §3.4/§4/§5.
12. §2.1 port 18800 (CLAUDE.md rule 4: 18802, Chrome squats 18800) and ollama service; consolidate.ts:87 "Ollama removed — offline and not planned to return". §3.2 step 2 likewise.
13. §2.5 "surfaced identically across three transport layers": README.md:235 "P1 on the CLI and HTTP (MCP tool pending)".
14. §2.5 "Every advanced verb ... decomposes internally into sequences of these three primitives": crystallize is a direct INSERT; cross-search runs its own FTS per DB; reflect calls search but not answer/temporal; kg-path is graph traversal.
LOW
15. "shadow discipline (§4 and §5)" — §4 never discusses it; defined §1.4 (line 75), measured §5.1.2.
16. "E13 temporal proximity boost (NOX_TEMPORAL_PATH, §5)" — neither string appears in §5; internal label.
17. "Hard Mutex section gating and SOURCE_TYPE_BOOST overlays ... Detailed in §4" — §4 does not describe them.
18. "Table V8" — no such table.
19. "cosine distance" — vec0 created without distance_metric (embed.ts:323-325) → L2 default (rank-equivalent only for unit-norm vectors).
20. Footnotes [^bm25] "§3.1", [^rrf] "§3.2", [^sqlitevec] "§3.1", [^geminiembed] "§3.3" — actual call sites §2.2, §2.5, §2.2, §4.1.
21. §4.2 "significant quality improvements" from 3 anecdotal queries, no artifact.
22. §2.5 101.74 ms is mock-LLM@100ms (README.md:256) so "42× under the 4.3 s budget" measures harness overhead; "live p95 1.5–2.5 s" — no artifact found (ANSWER.md:420 only says "<2s p95"): not verifiable.
23. [^salience-src] "lines 1–80 contain the module docstring ... retention defaults": docstring is lines 1–26; retention 45–56; weights at 229–232.
24. §3.4.3 heading "continuous in background" vs body "aging is a property of the read path"; recency anchors to last_accessed_at ?? source_date (salience.ts:83), so access resets decay — omitted.
