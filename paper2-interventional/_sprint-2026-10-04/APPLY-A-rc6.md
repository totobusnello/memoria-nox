# APPLY — Paper A rc5 → rc6 (2026-10-05)

Input: `A-v1.1-rc5.md` (sha256 `d2be7f49ddcab74a…e116e086`, 2,609 lines), unchanged.
Output: `A-v1.1-rc6.md` (sha256 `109bcad190892720…e7465861`, 2,680 lines). Only rc6 was edited.
Parity: `A-rc6/parity-rc6.py` → `PARITY OK` (41 hunks, 46/46 anchors, 33 token keys, 1 documented
heading change, no fence change, 0 residual class phrasings outside the F-5 addenda);
`--selftest` → `SELFTEST OK` (7 mutations, all bite).
Guard: `claims_check.py` unchanged — no literal it pins occurs in rc5 and not in rc6 (all 718
string literals of ≥ 12 chars checked); its guards read `MANUSCRIPT.md`, not the rc files, and
its baseline (11 divergences, the rc-not-promoted ones included) is the same before and after.

Source: the final Codex pass over rc5 (receipt
`.remember/adversary-receipt-codex-2026-10-05T074945-16991.txt`, exit 0; the output text itself
was not preserved, only the receipt). It confirmed 6 of the 10 rc4 corrections and found 4 applied
only at the quoted place: R2-addendum, R3, R4, R7. Each was fixed here as a **class**: the whole
manuscript was searched with a pattern per class, every hit got a decision, and parity now carries
a `classes` check that fails if any categorical phrasing of the four survives outside the F-5
addenda. **No number was recomputed or changed.**

## The four classes, verified against the code before writing

| class | code read | what the text now says |
|---|---|---|
| R2 — who initiated / what search delivered | `serving-search.ts:377-396`: `recordAccess` increments `access_count` for every id passed when `enabled`; `trackAccess` defaults to `true` in `search`, `searchSemantic`, `searchHybrid` (l.400, 488, 616); the comment records that the semantic canary bumped its top-N candidates every cycle until the D1 fix switched it off. Counters are cumulative. | The counter records candidacy in some tracked call, whoever initiated it (automated callers included) and whether or not the chunk was returned. No claim that it shows agent-initiated exposure or that search accounts for / delivered most exposure. |
| R3 — non-delivery scope | (same) + §3.1's own bound | "56,288 live chunks (83.78%) have neither a brief-log record nor a positive search counter. This is a lower bound on non-delivery by the brief and by tracked search; non-delivery across all agent-facing search is not established." Carried by every unconditional statement; §2 makes "never exposed" the record predicate with that scope. |
| R4 — pinning order | `serving-brief.ts:438-480` (`pickDedup`): phase 0 pinned (high-pain already in the current brief) placed first and counting toward `mainTarget`; phase 1 quota pass; phase 2 backfill to `mainTarget`; phase 3 fresh slots; phase 4 backfill to `n`. Served path `brief.ts:819-822` passes `pinnedIds`. | §4.3.2: quota pass runs after pinning and before backfill. F-5 rc5 entry: pinning precedes. §4.3.1: F7 listed last but runs first. §5.6: `pickDedup` places pinned first. |
| R7 — relevance vs eligibility | `brief-diversity.ts` comparator `(last_served ASC, salience DESC)`; §4.3.1 exhaustion; §4.4 replay 17/350 | Daily reach = eligibility (fixes the candidate population; exhausted in the measured regime). Per-brief selection = salience within `last_served` ties, saturating at 17/350. No "nothing to do with relevance", "not governed by relevance", "score does not decide", "deafness", "not by relevance", "does not predict". |

## Title

Title: *"Spare capacity, narrow surface: what a production agent-memory system actually
surfaces"*. It asserts no unconditional non-surfacing, so it was **not** changed. One flag for the
author: "actually surfaces" reads as a full census of delivery, whereas the search leg is only
bounded (tracked candidacy); the subtitle is defensible for the brief and for the records, less so
for "what search delivered". Left to the author.

## Numeric delta rc5 → rc6 (all owned, none recomputed)

| token | Δ | owner | justification |
|---|---:|---|---|
| `3.1` | +15 | R2, R3, addendum | `(§3.1)` pointers carried by the new scope/counter prose (13 in the body, 2 in the addendum) |
| `56,288` | +3 | R3 | quoted by the scope sentence (Abstract, §4.1 text, §8.1) |
| `83.78%` | +2 | R3, addendum | quoted in §4.1 text and the addendum |
| `377`, `396` | +2 each | R2, addendum | file lines of the canary comment, `search.ts:377-396` |
| `438`, `480` | +3 each | R4, addendum | file lines of `pickDedup` phases, `brief.ts:438-480` |
| `0`, `1` | +3, +5 | R4, addendum | "phase 0", "phase 1"; "§1" ×3 in the addendum |
| `17`, `350` | +2 each | R7, addendum | the replay ceiling 17/350 quoted in §5.5 and the addendum |
| `4.3.1`, `5.3`, `5.4`, `5.5` | +3, +1, +1, +1 | R7, addendum | section pointers |
| `2`, `7`, `9`, `4.1`, `4.1.1`, `4.2`, `4.3.2`, `4.5`, `8.1`, `8.2` | small | addendum | section lists of the addendum |
| `2026`, `10`, `05`, `04` | +2, +2, +1, +1 | addendum | "rc6 (2026-10-05)", `_sprint-2026-10-04/APPLY-A-rc6.md` |
| `four`, `six`, `ten`, `two` | +2, +1, +1, +1 | addendum, R7 | "four rc4 corrections" ×2, "six of the ten"; §5.5 "two parts" |

Heading change (documented in `HEADING_CHANGES`): §4.1 "83.78% of the corpus was never exposed" →
"83.78% of the corpus has no exposure record" (R3).

## parity-rc6.py

Extends `parity-rc5.py` (numbers / owners with the novelty rule / headings / fences; rc5 → rc6
defaults) with a **classes** check: 20 forbidden categorical phrasings (R2 ×6, R3 ×5, R4 ×2,
R7 ×7) must not occur in rc6 outside the two F-5 addenda, which quote them as history. Self-test
mutations: (1) number in untouched prose → `numbers`; (2) heading → `headings`; (3) §4.1 heading
reverted → `headings`; (4) the R3 scope sentence removed from the Abstract → `numbers`; (5) the R4
order reverted in pure prose → `owners`; (6) anchor planted in OLD → `owners` (novelty rule);
(7) "initiated by the agent" reintroduced inside an already-changed hunk → `classes` (only this
check can see it: same hunk, same numbers, anchors intact).

## Decisions not taken (and why)

- §2 item 2 ("on-demand search, when the agent decides to look something up") is kept: it names
  the surface's role, not what the counter records; §3.1 now defines the counter.
- §4.3.2 and §8.2 "if the loop closes, it closes through the agent": kept. The loop is brief
  exposure → later search, so it needs a reader of the brief who then searches, which is the
  agent. The canary's documented feedback (the D1 comment) ran from its own searches to the
  counter, not from brief exposure, and §3.1 now states it.
- Later uses of "never exposed" as the term defined in §2 (cohort table, population accounting)
  are kept; the definition now carries the scope.
- The rc5 addendum bullets are history and stay, except the R4 bullet (factually wrong about the
  code), which is corrected in place and marked "rc6".

## Pre-edit search (rc5) and decisions

Pattern per class below. C2 includes a second-pass pattern (`did not arrive`, `exactly the population`, `record of arriving`, `lower bound on`) added after the first sweep found that "measures what did not arrive" (§1, §4.1.1) and "exactly the population this paper measures (83.78%)" (§8.1) carried the same unconditional claim without any of the first-pass words.

### C1 (Codex-R2, who initiated / what search delivered)

pattern: `agent-initiated|initiated by the agent|agent initiates|the agent (decides|looked|found)|most of (the|that) (recorded )?exposure|accounts for most|for the most part|search traffic|accessed by search|search results path|the larger one`

| rc5 l. | hit | decision |
|---:|---|---|
| 47 | Most of that recorded exposure | **change** — abstract: no agent attribution; states what the counter records (candidacy in a tracked call, any initiator, returned or not) |
| 56 | Search traffic | **change** — "Tracked search traffic …, whoever initiated it (§3.1)" |
| 98 | initiated by the agent | **change** — abstract caveat: "records candidacy in a tracked call, not who initiated it" |
| 178 | initiated by the agent | **change** — §1: drops "initiated by the agent and accounts for most of the exposure"; search share of delivered exposure not established |
| 259 | the agent decides | leave — §2 names the search surface's role (on-demand lookup); it says nothing about the counter, which §3.1 now defines |
| 304 | search results path | **change** — §3.1 table: "incremented for the top candidates of each tracked search sub-query" |
| 493 | the larger one | **change** — §4.1.1 rewritten: counter = candidacy in a tracked call, any initiator, returned or not; only the brief is a system decision |
| 495 | initiated by the agent | **change** — §4.1.1 rewritten: counter = candidacy in a tracked call, any initiator, returned or not; only the brief is a system decision |
| 520 | agent initiates | **change** — §4.2 caveat: records mark tracked-search candidacy, not delivery and not initiator |
| 930 | search traffic | **change** — §4.3.2: "tracked search traffic …, whoever initiated it (§3.1)" |
| 1010 | search traffic | leave — quotes the withdrawn "fossil" sentence as history |
| 1860 | accessed by search | **change** — §7: counter definition replaced ("a top candidate of at least one tracked search sub-query", any initiator, returned or not) |
| 1914 | search traffic | **change** — §8.2: "past tracked search traffic, whoever initiated it"; the loop sentence that follows is kept: a loop from brief exposure can only close through the brief's reader, the agent |
| 2020 | search traffic | **change** — §9: "tracked search traffic …, whoever initiated it" |
| 2306 | agent-initiated | **change** — F-2 table: "search-counter records, not brief deliveries (… not who initiated the call)" |
| 2494 | For the most part | leave — rc5 addendum history; superseded explicitly by the rc6 addendum |

### C2 (Codex-R3, scope of non-delivery)

pattern: `never (been )?exposed|never-exposed|never reached|reached the agent|either surface|by either|no surface|non-exposure|never showed|ever showed|did not\s*$|did not arrive|exactly the population|record of arriving|lower bound on`

| rc5 l. | hit | decision |
|---:|---|---|
| 45 | by either | **change** — abstract: "56,288 live chunks (83.78%) have neither a brief-log record nor a positive search counter. This is a lower bound …; non-delivery across all agent-facing search is not established" |
| 47 | either surface | leave — "with a record on either surface" is the record predicate itself |
| 92 | non-exposure | leave — capacity argument about the brief (policy vs capacity), no delivery claim |
| 122 | never exposed | **change** — §1: "has no exposure record on either surface, a lower bound on non-delivery by the brief and by tracked search" |
| 123 | non-exposure | leave — capacity argument (slots do not impose it), no delivery claim |
| 125 | did not arrive | **change** — §1: 'measures what has no record of arriving' (found by the second-pass pattern) |
| 131 | non-exposure | leave — capacity argument (slots do not impose it), no delivery claim |
| 132 | non-exposure | leave — capacity argument (slots do not impose it), no delivery claim |
| 223 | never exposed | **change** — contributions: same scope as §1 |
| 261 | Never exposed | **change** — §2: "never exposed" defined as the record predicate + lower-bound scope; later uses of the defined term inherit it |
| 294 | never-exposed | leave — identifier of the figure generator's identity check |
| 316 | lower bound on | leave — §3.1 already states the lower-bound scope of the complement |
| 371 | never exposed | **change** — §4.1 heading: "has no exposure record" (heading change, documented in parity) |
| 381 | never exposed | **change** — table row "no record on either"; new sentence after the table carries the full scope |
| 394 | never exposed | **change** — "have no exposure record" |
| 402 | non-exposure | **change** — "absence of a record on both surfaces (brief ∪ tracked search)"; "neither the brief nor tracked search has a record of showing it" |
| 404 | no surface | **change** — "absence of a record on both surfaces (brief ∪ tracked search)"; "neither the brief nor tracked search has a record of showing it" |
| 417 | never exposed | **change** — "of the 56,288 with no record" |
| 418 | non-exposure | leave — the filtering objection, stated in the defined term |
| 421 | no surface | **change** — "neither the brief nor tracked search has a record of showing" |
| 445 | never exposed | leave — cohort table header, defined term (scope in §2 and §4.1) |
| 497 | never exposed | **change** — §4.1.1: adds "a lower bound on non-delivery by the brief and by tracked search" |
| 498 | did not | **change** — §4.1.1: 'what has no record of arriving' (second pass) |
| 512 | never been exposed | leave — live-vs-historical population accounting of the defined term |
| 514 | never exposed | leave — live-vs-historical population accounting of the defined term |
| 735 | did not | leave — unrelated ('the served coverage set did not change') |
| 739 | never reached | leave — "never reached the served set": a brief-log fact |
| 884 | never reached | leave — main pool top-k, measured from the brief log; brief-only claim |
| 990 | lower bound on | leave — unrelated ('lower bound on the drop', §4.3.2 counterfactual) |
| 1125 | never reached | **change** — §4.5: "has no record of reaching the agent through the brief or tracked search (a lower bound …; not established …)" |
| 1893 | exactly the population | **change** — §8.1: 'the population this paper measures, within a stated scope: 56,288 live chunks (83.78%) … lower bound …; … not established' (second pass) |
| 1985 | non-exposure | leave — §9 First: policy vs capacity of the brief |
| 2058 | non-exposure | **change** — §9: "the 83.78% without an exposure record" |
| 2434 | lower bound on | leave — F-5 Codex-1 entry, already scoped to tracked search |
| 2590 | non-exposure | leave — struck-through Open item (history), about the coverage channel |

### C3 (Codex-R4, pinning order)

pattern: `pinn|quota|backfill|first pass|picks first|phase 0|runs first`

| rc5 l. | hit | decision |
|---:|---|---|
| 275 | quota | leave — `freshSlots` is a ceiling on the fresh fill loop; not about selection order |
| 356 | pinn | leave — other sense (hash pinning, pinned instant, quotable, quotation) |
| 840 | quota | leave — F1's nominal quota of 5 is `ceil(n/2)` (`buildPools`), correct |
| 843 | quota | leave — F6 is correctly the quota pass capped at `mainTarget`; the order note goes on F7 |
| 844 | picks first | **change** — §4.3.1: "F7 is listed last but runs first: phase 0 of `pickDedup` … before the F6 quota pass (phase 1) and the backfill (`brief.ts:438-480`)" |
| 862 | quota | leave — filter label |
| 951 | pinn | leave — other sense (hash pinning, pinned instant, quotable, quotation) |
| 960 | quota | **change** — §4.3.2: quota pass (phase 1) runs after pinning (phase 0, counting toward `mainTarget`) and before the backfill |
| 961 | quota | **change** — §4.3.2: quota pass (phase 1) runs after pinning (phase 0, counting toward `mainTarget`) and before the backfill |
| 1223 | quota | leave — `freshSlots` is a ceiling on the fresh fill loop; not about selection order |
| 1353 | pinn | **change** — §5.6: "`pickDedup`, which places the pinned items first and deduplicates as it fills" |
| 1698 | quota | leave — other sense (hash pinning, pinned instant, quotable, quotation) |
| 1808 | Pinn | leave — other sense (hash pinning, pinned instant, quotable, quotation) |
| 1813 | pinn | leave — other sense (hash pinning, pinned instant, quotable, quotation) |
| 1815 | pinn | leave — other sense (hash pinning, pinned instant, quotable, quotation) |
| 1818 | pinn | leave — other sense (hash pinning, pinned instant, quotable, quotation) |
| 1835 | pinn | leave — other sense (hash pinning, pinned instant, quotable, quotation) |
| 1977 | pinn | leave — other sense (hash pinning, pinned instant, quotable, quotation) |
| 2211 | pinn | leave — other sense (hash pinning, pinned instant, quotable, quotation) |
| 2395 | quota | leave — other sense (hash pinning, pinned instant, quotable, quotation) |
| 2499 | quota | **change** — F-5 rc5 entry: "pinning precedes the quota pass and backfill follows it" |
| 2500 | pinn | **change** — F-5 rc5 entry: "pinning precedes the quota pass and backfill follows it" |
| 2522 | pinn | leave — other sense (hash pinning, pinned instant, quotable, quotation) |
| 2598 | quota | leave — filter label |

### C4 (Codex-R7, relevance vs eligibility)

pattern: `relevance|immune|deaf|respond|not by |does not decide|nothing to do|daily reach`

| rc5 l. | hit | decision |
|---:|---|---|
| 65 | respond | **change** — abstract: daily reach set by eligibility (exhausted in that regime); within a brief, ties only, 17/350 |
| 66 | respond | **change** — abstract: daily reach set by eligibility (exhausted in that regime); within a brief, ties only, 17/350 |
| 143 | nothing to do | **change** — §1: "neither of them a shortage of relevance: the first fixes which items are eligible (daily reach), the second lets the score decide only within ties (per-brief selection)" |
| 144 | relevance | **change** — §1: "neither of them a shortage of relevance: the first fixes which items are eligible (daily reach), the second lets the score decide only within ties (per-brief selection)" |
| 218 | does not decide | **change** — §1: "the score decides only within ties of the dominant coordinate" |
| 415 | relevance | leave — a measured stratification by declared relevance, not a mechanism claim |
| 564 | not by  | leave — unrelated sense |
| 626 | relevance | leave — already the supported weaker claim (size predicts better than relevance) |
| 634 | relevance | **change** — §4.2: "predicts exposure less well than the size of the collection does" |
| 734 | not by  | leave — unrelated sense |
| 835 | relevance | **change** — §4.3.1: daily reach set by eligibility (exhausted every measured day); relevance acts on per-brief selection, within ties, up to a ceiling |
| 902 | deaf | **change** — §4.3.2: "a bounded response to the score" |
| 1037 | respond | leave — table column; the coverage answer is "only up to a ceiling" |
| 1043 | respond | **change** — §4.3.2 symmetry: daily reach by eligibility + per-brief ties |
| 1313 | respond | leave — already bounded ("only within ties", "bounded by construction") |
| 1332 | relevance | leave — already bounded ("only within ties", "bounded by construction") |
| 1334 | respond | leave — already bounded ("only within ties", "bounded by construction") |
| 1338 | not by  | **change** — §5.5: two parts kept apart (daily reach = eligibility, exhausted; per-brief selection = salience within ties, 17/350) |
| 1339 | relevance | **change** — §5.5: two parts kept apart (daily reach = eligibility, exhausted; per-brief selection = salience within ties, 17/350) |
| 1556 | nothing to do | leave — unrelated sense |
| 1682 | not by  | leave — unrelated sense |
| 1899 | relevance | leave — unrelated sense |
| 1923 | respond | leave — scoped ("responds only within ties of the dominant coordinate") |
| 1925 | respond | leave — scoped ("responds only within ties of the dominant coordinate") |
| 1962 | not by  | leave — unrelated sense |
| 2014 | respond | leave — §9 Second already separates population (eligibility) from the tie-bounded score response |
| 2023 | respond | **change** — §9: daily reach by eligibility + per-brief ties |
| 2024 | respond | **change** — §9: daily reach by eligibility + per-brief ties |
| 2289 | respond | leave — unrelated sense |
| 2445 | respond | leave — F-5 history quoting the rc3 wording |
| 2446 | respond | leave — F-5 history quoting the rc3 wording |
| 2460 | not by  | leave — unrelated sense |
| 2506 | Immune | leave — rc5 addendum history |
| 2507 | respond | leave — rc5 addendum history |
| 2538 | not by  | leave — unrelated sense |
| 2565 | not by  | leave — unrelated sense |

## Post-edit search (rc6): every remaining hit

### C1 (Codex-R2, who initiated / what search delivered)

| rc6 l. | hit | status |
|---:|---|---|
| 56 | search traffic | rc6 wording (scoped) |
| 264 | the agent decides | unchanged, decided above (rc5 l.259): leave |
| 953 | search traffic | rc6 wording (scoped) |
| 1035 | search traffic | unchanged, decided above (rc5 l.1010): leave |
| 1950 | search traffic | rc6 wording (scoped) |
| 2057 | search traffic | rc6 wording (scoped) |
| 2532 | For the most part | rc5 addendum, unchanged history (superseded by the rc6 addendum) |
| 2564 | agent-initiated | rc6 addendum (record of this round, quotes the replaced phrasings) |

### C2 (Codex-R3, scope of non-delivery)

| rc6 l. | hit | status |
|---:|---|---|
| 45 | lower bound on | rc6 wording (scoped) |
| 47 | either surface | rc6 wording (scoped) |
| 93 | non-exposure | unchanged, decided above (rc5 l.92): leave |
| 123 | either surface | rc6 wording (scoped) |
| 125 | non-exposure | unchanged, decided above (rc5 l.123): leave |
| 127 | record of arriving | rc6 wording (scoped) |
| 133 | non-exposure | unchanged, decided above (rc5 l.131): leave |
| 134 | non-exposure | unchanged, decided above (rc5 l.132): leave |
| 227 | either surface | rc6 wording (scoped) |
| 266 | Never exposed | rc6 wording (scoped) |
| 268 | lower bound on | rc6 wording (scoped) |
| 301 | never-exposed | unchanged, decided above (rc5 l.294): leave |
| 327 | lower bound on | unchanged, decided above (rc5 l.316): leave |
| 403 | lower bound on | rc6 wording (scoped) |
| 434 | non-exposure | unchanged, decided above (rc5 l.418): leave |
| 461 | never exposed | unchanged, decided above (rc5 l.445): leave |
| 515 | never exposed | rc6 wording (scoped) |
| 516 | lower bound on | rc6 wording (scoped) |
| 517 | record of arriving | rc6 wording (scoped) |
| 530 | never been exposed | unchanged, decided above (rc5 l.512): leave |
| 532 | never exposed | unchanged, decided above (rc5 l.514): leave |
| 754 | did not | unchanged, decided above (rc5 l.735): leave |
| 758 | never reached | unchanged, decided above (rc5 l.739): leave |
| 907 | never reached | unchanged, decided above (rc5 l.884): leave |
| 1015 | lower bound on | unchanged, decided above (rc5 l.990): leave |
| 1152 | lower bound on | rc6 wording (scoped) |
| 1929 | lower bound on | rc6 wording (scoped) |
| 2022 | non-exposure | unchanged, decided above (rc5 l.1985): leave |
| 2472 | lower bound on | unchanged, decided above (rc5 l.2434): leave |
| 2566 | never exposed | rc6 addendum (record of this round, quotes the replaced phrasings) |
| 2567 | never reached | rc6 addendum (record of this round, quotes the replaced phrasings) |
| 2568 | lower bound on | rc6 addendum (record of this round, quotes the replaced phrasings) |
| 2571 | never exposed | rc6 addendum (record of this round, quotes the replaced phrasings) |
| 2661 | non-exposure | unchanged, decided above (rc5 l.2590): leave |

### C3 (Codex-R4, pinning order)

| rc6 l. | hit | status |
|---:|---|---|
| 282 | quota | unchanged, decided above (rc5 l.275): leave |
| 368 | pinn | unchanged, decided above (rc5 l.356): leave |
| 861 | quota | unchanged, decided above (rc5 l.840): leave |
| 864 | quota | unchanged, decided above (rc5 l.843): leave |
| 866 | runs first | rc6 wording (scoped) |
| 867 | pinn | rc6 wording (scoped) |
| 868 | backfill | rc6 wording (scoped) |
| 885 | quota | unchanged, decided above (rc5 l.862): leave |
| 974 | pinn | unchanged, decided above (rc5 l.951): leave |
| 983 | quota | rc6 wording (scoped) |
| 984 | phase 0 | rc6 wording (scoped) |
| 985 | quota | rc6 wording (scoped) |
| 1251 | quota | unchanged, decided above (rc5 l.1223): leave |
| 1387 | pinn | rc6 wording (scoped) |
| 1731 | quota | unchanged, decided above (rc5 l.1698): leave |
| 1841 | Pinn | unchanged, decided above (rc5 l.1808): leave |
| 1846 | pinn | unchanged, decided above (rc5 l.1813): leave |
| 1848 | pinn | unchanged, decided above (rc5 l.1815): leave |
| 1851 | pinn | unchanged, decided above (rc5 l.1818): leave |
| 1868 | pinn | unchanged, decided above (rc5 l.1835): leave |
| 2014 | pinn | unchanged, decided above (rc5 l.1977): leave |
| 2249 | pinn | unchanged, decided above (rc5 l.2211): leave |
| 2433 | quota | unchanged, decided above (rc5 l.2395): leave |
| 2537 | quota | rc6 wording in the rc5 addendum entry (Codex-R4 fix, pinning first) |
| 2538 | pinn | rc6 wording in the rc5 addendum entry (Codex-R4 fix, pinning first) |
| 2573 | Pinn | rc6 addendum (record of this round, quotes the replaced phrasings) |
| 2574 | backfill | rc6 addendum (record of this round, quotes the replaced phrasings) |
| 2575 | pinn | rc6 addendum (record of this round, quotes the replaced phrasings) |
| 2576 | runs first | rc6 addendum (record of this round, quotes the replaced phrasings) |
| 2593 | pinn | unchanged, decided above (rc5 l.2522): leave |
| 2669 | quota | unchanged, decided above (rc5 l.2598): leave |

### C4 (Codex-R7, relevance vs eligibility)

| rc6 l. | hit | status |
|---:|---|---|
| 65 | respond | rc6 wording (scoped) |
| 66 | daily reach | rc6 wording (scoped) |
| 67 | respond | rc6 wording (scoped) |
| 146 | relevance | rc6 wording (scoped) |
| 431 | relevance | unchanged, decided above (rc5 l.415): leave |
| 583 | not by  | unchanged, decided above (rc5 l.564): leave |
| 645 | relevance | unchanged, decided above (rc5 l.626): leave |
| 653 | relevance | rc6 wording (scoped) |
| 753 | not by  | unchanged, decided above (rc5 l.734): leave |
| 853 | daily reach | rc6 wording (scoped) |
| 854 | Daily reach | rc6 wording (scoped) |
| 856 | Relevance | rc6 wording (scoped) |
| 1062 | respond | unchanged, decided above (rc5 l.1037): leave |
| 1068 | daily reach | rc6 wording (scoped) |
| 1069 | respond | rc6 wording (scoped) |
| 1341 | respond | unchanged, decided above (rc5 l.1313): leave |
| 1360 | relevance | unchanged, decided above (rc5 l.1332): leave |
| 1362 | respond | unchanged, decided above (rc5 l.1334): leave |
| 1366 | Daily reach | rc6 wording (scoped) |
| 1368 | relevance | rc6 wording (scoped) |
| 1371 | relevance | rc6 wording (scoped) |
| 1589 | nothing to do | unchanged, decided above (rc5 l.1556): leave |
| 1715 | not by  | unchanged, decided above (rc5 l.1682): leave |
| 1935 | relevance | unchanged, decided above (rc5 l.1899): leave |
| 1960 | respond | unchanged, decided above (rc5 l.1923): leave |
| 1962 | respond | unchanged, decided above (rc5 l.1925): leave |
| 1999 | not by  | unchanged, decided above (rc5 l.1962): leave |
| 2051 | respond | unchanged, decided above (rc5 l.2014): leave |
| 2060 | respond | rc6 wording (scoped) |
| 2061 | daily reach | rc6 wording (scoped) |
| 2062 | respond | rc6 wording (scoped) |
| 2327 | respond | unchanged, decided above (rc5 l.2289): leave |
| 2483 | respond | unchanged, decided above (rc5 l.2445): leave |
| 2484 | respond | unchanged, decided above (rc5 l.2446): leave |
| 2498 | not by  | unchanged, decided above (rc5 l.2460): leave |
| 2544 | Immune | rc5 addendum, unchanged history (superseded by the rc6 addendum) |
| 2545 | respond | rc5 addendum, unchanged history (superseded by the rc6 addendum) |
| 2577 | Relevance | rc6 addendum (record of this round, quotes the replaced phrasings) |
| 2580 | nothing to do | rc6 addendum (record of this round, quotes the replaced phrasings) |
| 2581 | does not decide | rc6 addendum (record of this round, quotes the replaced phrasings) |
| 2609 | not by  | unchanged, decided above (rc5 l.2538): leave |
| 2636 | not by  | unchanged, decided above (rc5 l.2565): leave |

