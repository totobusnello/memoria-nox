# tasks-v1-draft notes

## Skipped ranks and reserves
- Rank 37 (D-2026-11-03, GTM Phase 2 adiado): skipped. Its fact (GTM postponed until Paper 3 stage 1 result) is superseded the next day by rank 18 (D-2026-11-04, GTM reopened). A task keyed to rank 37 would have a stale "correct" answer that contradicts K19. Reserve 40 (D45, tagline) used, placed last as K40.
- No other skips. K ids are sequential in rank order: K01-K37 = ranks 0-36, K38 = rank 38, K39 = rank 39, K40 = reserve rank 40.

## Items where the decisive fact is uncertain or time-bound
- K03 (rank 2, D43): the +15% gate is from May; D-2026-11-03/04 say the Q4 gate was never re-evaluated after Oct and the GTM picture changed. Threshold fact is faithful to the source but may be considered stale.
- K15 (rank 14, D31): "golden set n>=30" prerequisite is dated pre-R03 (May); D28 (rank 42, not used) reports n=60 golden at an earlier date, so the body itself is inconsistent about the current size. Prompt avoids naming the current set size.
- K18 (rank 17, D37): entry is marked SUPERSEDED; I used the superseding fact (`--no-vault-facts`, default ON), which is in the body.
- K24 (rank 23, D-2026-09-14): time-bound to the trial (closed 2026-09-21). Pass criterion accepts a note that it applied until the trial closed.
- K33 (rank 32): the kill-switch / "reindex must become upsert" part may be superseded by rank 6 (D-2026-10-14c, reindex now per-file diff). Recovery from pre-op snapshot and the overwrite root cause stay valid; criterion does not hinge on the flag.
- K26 (rank 25): body says pre-op snapshot retention 7 d; CLAUDE.md says 5 d now. Not used in the task.
- K27 (rank 26, D42): quarterly cadence is guessable; I keyed the task to the "ranking change or destructive op passes threat review before merge" implication instead (medium risk).
- Several bodies in the draw are truncated mid-sentence (ranks 1, 3, 4, 11, 13, 16, 21, 28, 34, 43, ...). Facts used are only from the visible text.
- K12/K14 (ranks 11, 13): same canary symptom, different causes (billing 429 vs hybrid label bug). Prompts carry distinguishing details (429 + empty vectorize vs. healthy search + full coverage) so a correct answer to one is not a correct answer to the other.
- K05 vs K07 (ranks 4, 6): both about chunk deletion; rank 4's "watcher ignores deletion" is superseded by rank 6's tombstone behavior, so K05 is keyed to the duplicate-copies-come-back / protected-rows facts, not the watcher.

## Counts
K 40, G 20 (10 config-like G01-G10, 10 conceptual G11-G20), W+ 10, W- 10. Ids unique, JSONL parses.
K generic_answer_risk: low 26, medium 14, high 0 (number rated high: 0).
Banned-word check on K and G prompts (remember, previously, history, decided, memory, docs, earlier, again, recall, look up, consult): clean after one fix (K34 "recall" -> "coverage").

# Supersession check (v1)

Corpus: docs/DECISIONS.md, docs/INCIDENTS.md, CLAUDE.md and 204 audits/* at commit a819385 (via git show). Method: full source section read for every item (including the part past the 2,500-char cut), then a grep for the key entities and numbers across the whole corpus, outside the item's own section, reading every later line that changes, expires or contradicts the fact. Reserves 41-47 checked the same way. Result file: tasks-v1.jsonl (draft file untouched). Ids in this table are the draft ids.

| id | class | evidence / action |
|---|---|---|
| K01 | superseded | DECISIONS.md:2047 (schema v20 added `requesting_agent`); audits 2026-10-23 query it. REPLACED by rank 41 |
| K02 | current | no later text on Jev; DECISIONS.md:79 item 31 agrees. Added "if reopened: rrf(hybrid, jev@30), jev-1.13.0 pinned" |
| K03 | superseded | DECISIONS.md:3356 says the Q4 gate was never re-evaluated after 26-27/10; audit 2026-05-24 shows D43 verified on the production path (nDCG@10 0.6380), so the "must confirm production path" condition is closed. REPLACED by rank 42 |
| K04 | current | D69 only; made explicit that 2.00% is 2/5 batches (partial) |
| K05 | conflicting (mechanism only) | "ingestFile deletes and reinserts" and "watcher ignores deletion" were superseded by D-2026-10-14c (content diff, tombstones). Rule (live-file copies return; protected rows) still holds. KEPT, criterion restricted, `supersession_note` added |
| K06 | current | D58/D55 and CLAUDE.md P3 status agree |
| K07 | current | D-2026-10-14c is the newest word on tombstones |
| K08 | superseded | F10 Phase C deployed 2026-05-23 (audit 2026-05-23-f10-phase-c-*), Phase D deployed (audit 2026-05-24-f10-phase-d-*, CLAUDE.md "F10 Phase D (#291)"). REPLACED by rank 45 |
| K09 | current | no later text on MA-protection default |
| K10 | current | D-2026-11-04 agrees (769x only in harness; KG path $0/query). 529 ms tagged as the May measurement |
| K11 | current | no later portability figure |
| K12 | current | 2026-09-01 retraction is already in the same section; added "balance is per Google project" |
| K13 | current | no later text |
| K14 | current | same incident, full section read |
| K15 | superseded | the n>=30 golden-set prerequisite was met and overtaken (n=60 in D28, n=80 at 17/05, later goldens and ruler v3). REPLACED by rank 46 |
| K16 | current | 0.281 / n=100 / seed 42 appears only in D30 |
| K17 | current | no later text |
| K18 | current | `NOX_VAULT_FACTS_MODE` went active -> shadow -> active on 2026-10-22; CLI flag unchanged. Criterion mentions the env knob; note added |
| K19 | current | newest entry in the corpus |
| K20 | current | Jev entry (Sept) still calls the MiniLM reranker opt-in |
| K21 | current | no later reversal of order or of the sham status |
| K22 | current | moonshot appears only in its own section; added the flock/claim prevention |
| K23 | conflicting (partial) | "SOURCE_TYPE_BOOST disabled" superseded: it is in the canonical stack (D51, G11 audit). Rule 5 (additive, separate commits) is current in CLAUDE.md. KEPT, criterion restricted, note added |
| K24 | expired | DECISIONS.md:1592: `desliga-dose-p2.sh` ran at 2026-09-21 09:43:05Z. REPLACED by rank 47 |
| K25 | current | vec0 / sqliteVec rule repeated by later incidents |
| K26 | current | DISABLE_COMPACT appears only in its section; added 182 files / 681 relations |
| K27 | current | (the "next audit Q3 2026" line is expired but not used by the task) |
| K28 | current | later Paper 2 text still lists glm-5.2; audit 2026-10-27 uses glm-5.3 with `model_returned`, not a contradiction |
| K29 | current | no later text on the threshold |
| K30 | current | D76 NAO FAZEMOS read in full (dedicated CPU plan / SLO provider); INCIDENTS version says the PR is kept as draft, D76 says abandoned; criterion avoids the PR state |
| K31 | current | hook text only in INCIDENTS and the workspace CLAUDE.md |
| K32 | current | no later text |
| K33 | conflicting (partial) | root cause refined on 2026-05-26 (reindex ignored OPENCLAW_WORKSPACE and hit the main DB); kill-switch / "until reindex is upsert" overtaken by the 2026-10-14 reindex rewrite. KEPT; criterion = cause + recovery only |
| K34 | current | no later FTS5 expansion adopted |
| K35 | current | no later correction in the corpus (an "errata" in docs/HANDOFF.md is mentioned but not in the corpus) |
| K36 | current | no later text |
| K37 | current | no later text |
| K38 | current | library version differs between D54 (v13.x) and a dry-run audit (^11.10), not used by the criterion |
| K39 | conflicting (partial) | cause (reindex cascade) is pre-rewrite behavior; fix (vectorize with .env, verify with /api/health) current. KEPT, criterion restricted to fix + verification |
| K40 | current | repo CLAUDE.md and 2026-05-22/24 audits carry the same tagline |

## Replacements (strict reserve order)
- Rank 41 (D-2026-11-01, daily-notes cron off) -> K01. Newest entry, nothing later.
- Rank 42 (D28, E5 vs Gemini embedding) -> K03. NAO FAZEMOS item 28 still current.
- Rank 43 (D77, vec0 repack "recomendado, execucao pendente") SKIPPED: superseded; it was executed 2026-08-28 and 2026-09-30, and DECISIONS.md:2224 (2026-10-21) says do NOT repack now (33.1% -> 4.0%).
- Rank 44 (D33, cross-encoder F gate at nDCG@10 < 0.775) SKIPPED: expired; the gate was written against the old eval ruler (golden/ruler changed, later ruler v3 gives ~0.26) and reranking later shipped as MiniLM opt-in (D60).
- Rank 45 (Deploy Validator stderr->JSON) -> K08. Current; generic_answer_risk high (the symptom nearly gives the cause), kept because the skip rule allows only superseded or untaskable items.
- Rank 46 (Hostinger throttling incident) -> K15. Same event as K30 (D76) but an incident-side angle (what to record as the result); the two tasks are correlated, flagged.
- Rank 47 (_retired watcher pollution) -> K24. Current: the allowlist still exists in the 2026-10-14c watcher.
- All 5 slots filled; reserves exhausted at 47 with none left over.

## Full-section re-check (step 4) changes
K02 (reopen arm), K04 (2.00% is partial), K12 (per-project balance), K22 (flock prevention), K26 (182 files / 681 relations), K28 (follow-ups), K30 (NAO FAZEMOS: SLA upgrade; 20 retries x 900 s), K33 (cause refined), K10 (May measurement). No numeric error found in the others.

## Open points for the reviewer
- K05, K23, K33, K39 are kept with restricted criteria (same treatment as K33) rather than replaced; if you want them replaced strictly, there are no reserves left (4 slots would stay unfilled).
- Final K risk: low 25, medium 14, high 1 (K08).
