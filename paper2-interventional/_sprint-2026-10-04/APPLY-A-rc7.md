# APPLY — Paper A rc6 → rc7 (2026-10-05)

Input: `A-v1.1-rc6.md` (sha256 `109bcad190892720…e7465861`, 2,680 lines), unchanged.
Output: `A-v1.1-rc7.md` (sha256 `e6a833ef7b3230e2…00f92e97`, 2,712 lines). Only rc7 was edited.
Parity: `A-rc7/parity-rc7.py` → `PARITY OK` (13 hunks, 13/13 anchors, 17 token keys, no heading
change, no fence change, 0 residual class phrasings outside the F-5 addenda; 33 forbidden
phrasings = the 20 rc6 ones kept + 13 new);
`--selftest` → `SELFTEST OK` (11 mutations, all bite; the 8 class reintroductions bite on
`classes`, four of them on `classes` alone).
Guard: `claims_check.py` not touched — no literal it pins occurs in rc6 and not in rc7 (all 718
string literals of ≥ 12 chars checked).

Source: the Codex pass over rc6 (receipt
`.remember/adversary-receipt-codex-2026-10-05T095025-69718.txt`, exit 0): four medium findings,
"not ready to deposit". Each was checked against the code or against §3.1 before it was applied,
then fixed as a **class** (whole-manuscript search, a decision per hit, a `classes` pattern in
parity). **No number was recomputed or changed.**

## The four findings, verified before writing

| # | finding | verified against | applied |
|---|---|---|---|
| 1 | §4.1 "the surface does not show even the fragments the system itself marked as relevant" asserts non-delivery without the search scope | §3.1 (tracked-search bound, untracked search unresolved) — same bound the rest of rc6 already carries | §4.1: the fragments that pass the importance floor have neither a brief-log record nor a positive search counter; lower bound on non-delivery by the brief and tracked search; non-delivery across all agent-facing search not established (↩ F-3.4; §3.1). Codex text, plus "that pass the coverage channel's importance floor" so the sentence keeps its subject (the 10,008). |
| 2 | §4.1.1 "The union counts what was exposed *at some point*…" and "the population of which one can say 'never exposed'" | §3.1 + the §4.1 table: 11,051 = 10,899 live + 152 deleted brief chunks; the search leg is candidacy, not delivery | Union = historical brief-log membership + positive search counters on live chunks; includes the 152; does not count delivered exposure. Complement = live chunks with neither record at 2026-08-28 09:52Z, lower bound on non-delivery by the brief and tracked search. "…over which this record predicate is measured". |
| 3 | "only one of them is a decision of the system" (§4.1.1), "only the brief is a delivery decided by the system" (Abstract), "only the brief is decided by the system" (§1), "Only the brief" (§4.1.1) | `serving-search.ts:377-396` (rc6 R2): the counter does not identify initiators, automated callers included ⇒ no exclusive attribution | "The brief proactively selects content for delivery; the search counter records candidacy in tracked calls without identifying their initiators" (§4.1.1); "the brief proactively selects content for delivery" (Abstract, §1); "The brief (…) records what was selected for delivery" (§4.1.1). Sweep also caught Abstract l.48 "The surface the system decides, the brief" → "The brief, the surface that proactively selects content for delivery". |
| 4 | §4.3.1 / §5.5 reduce eligibility to paths ("which file paths…", "which paths enter the pool") and give relevance an exclusive role ("Relevance acts…", "Per-brief selection is where relevance acts") | `serving-brief.ts:638-647` (`fetchFreshCandidates`): `source_file LIKE` path patterns (639) AND `COALESCE(importance,0) >= freshMinImp OR COALESCE(pain,0) >= freshMinPain` (642-643) AND `julianday('now') - julianday(COALESCE(source_date, created_at)) <= freshMaxAgeDays` (644-647). Two age windows: agent sub-pool uses `freshMaxAgeDays`, global sub-pool `freshGlobalMaxAgeDays` (l.809, 845). Confirmed: paths alone do not fix the population. | Both passages: "Eligibility combines path patterns, the importance/pain floor and age windows. In the measured regime, the channel exhausted that eligible population on every measured day. Holding eligibility fixed, an additive salience bonus changes per-brief selection only within `last_served` ties; the tested intervention saturated at 17/350 replay states." §4.3.1 keeps "the corpus grew outside the configured path patterns" (the rc6 claim, now naming the patterns, not the population). §5.5 keeps its two-part frame ("The first is the channel's daily reach, bounded by its eligible population … The second is per-brief selection") and its last sentence now reads "with eligibility held fixed, no additive salience adjustment could change selection there beyond the ceiling". |

## Sweep — every hit of every pattern, rc6 → rc7

Line numbers are of each file. "Addendum" = F-5 history region (rc5/rc6/rc7 addenda), excluded
from `classes` because it quotes the replaced phrasings.

| pattern | rc6 hits | decision | rc7 hits |
|---|---|---|---|
| `only the brief` | 99 (Abstract), 180 (§1), 229 (contributions), 514 (§4.1.1) | 99, 180, 514 fixed (finding 3). 229 "the capacity cited is only the brief's" is a scope statement about capacity, not attribution — kept; regex excludes `brief's`. | 229 (kept), 2605 (rc7 addendum) |
| `only one of them` | 509 (§4.1.1) | fixed (finding 3) | — |
| `decided by the system` | 99, 181 | fixed (finding 3) | 2605 (rc7 addendum) |
| `decision of the system` | 0 on one line (rc6 509–510 broke it across lines) | fixed with 509 | — |
| `the system decides` (sweep extra) | 48 (Abstract), 514 (§4.1.1) | both fixed (finding 3 class) | — |
| `counts what was exposed` | 527 (§4.1.1) | fixed (finding 2) | — |
| `of which one can say` (sweep extra) | 531–532 (broken across lines) | fixed (finding 2) | 2603 (rc7 addendum) |
| `does not show` | 451 (§4.1), 1126 (§4.4 caveat, "this measurement does not show it"), 1331 (§5.4, "this comparison does not show that they crossed…") | 451 fixed (finding 1). 1126 and 1331 are statements about what a measurement fails to establish — already scoped, kept; regex is `surface does not show`. | 1130, 1335 (kept), 2596 (rc7 addendum) |
| `which paths` | 1366 (§5.5) | fixed (finding 4) | — |
| `file paths` | 854 (§4.3.1) | fixed (finding 4) | — |
| `paths enter` (sweep extra) | 1366 | fixed (finding 4) | — |
| `set by eligibility` | 66 (Abstract), 854 (§4.3.1), 1068 (§4.3.2), 1366 (§5.5), 2061 (§9), 2577 (rc6 addendum) | 854, 1366 fixed (finding 4). 66, 1068, 2061 did not reduce eligibility to paths, but summarised it without its components and (1068, 2061) as "it exhausts" without the regime → "has a daily reach bounded by its eligible population (path patterns, the importance/pain floor and age windows), which it exhausted in [that / the measured] regime". 2577 is rc6 history; the rc7 addendum supersedes it explicitly. | 2582 (rc6 addendum, history) |
| `relevance acts` (sweep extra) | 856 (§4.3.1), 1368 (§5.5) | fixed (finding 4) | — |

Also read, not changed: `decide`/`relevance` outside the addenda (l.72, 146–147, 163, 222, 431,
648, 656, 814, 1080, 1364, 1940, 1970, 1975; plus 264, 1270, 1537, 1542, 1544, 1602, 2284, 2294,
which use "decide" about tie-breaks, the agent or the warnings, not about the system's delivery). §1 l.145–147 ("neither of them a shortage of
relevance: the first fixes which items are eligible at all") was left: it names the two reasons
(calendar, ordering) and does not reduce eligibility to paths; §1 l.222 already lists the three
components. **Flag for the author:** "neither of them a shortage of relevance" is defensible for the
10,008 that pass the importance floor, but the floor itself is part of eligibility; if a reviewer
pushes on it, "neither of them a shortage of slots" is the safe form.

## Numeric delta rc6 → rc7 (all owned, none recomputed)

| token | Δ | owner | justification |
|---|---:|---|---|
| `3.1` | +2 | §4.1 (R3), rc7 addendum | "(↩ F-3.4; §3.1)"; "§3.1" in the addendum |
| `17`, `350` | +1 each | §4.3.1 (R7) | "17/350 replay states", the existing §4.4 ceiling quoted |
| `638`, `647` | +1 each | rc7 addendum | `brief.ts:638-647`, the eligibility predicate |
| `4.1` | +2 | rc7 addendum | "§4.1 finding", "§4.1 said" |
| `4.1.1` | +2 | rc7 addendum | union bullet, R2 list |
| `1`, `4.3.1`, `5.5`, `4.3.2`, `9` | +1 each | rc7 addendum | section lists |
| `2026`, `10` | +2 each | rc7 addendum | "rc7 (2026-10-05)", "_sprint-2026-10-04/APPLY-A-rc7.md" |
| `05`, `04` | +1 each | rc7 addendum | same two dates |
| `four` | +2 | rc7 addendum | "four rc6 phrasings", "four medium findings" |

No value in the paper changed: 1,635 / 1,787 / 152 / 9,755 / 10,899 / 11,051 / 56,288 / 67,187 /
67,339 / 83.78% / 17/350 are all byte-identical where they already stood.

## Not done (by rule)

No git, no Zenodo, no voices. No host, IP or personal path written. `MANUSCRIPT.md` not touched
(rc7 is not promoted). A fresh Codex pass over rc7 is the natural next gate; each pass so far has
produced a new artifact that needs its own pass.
