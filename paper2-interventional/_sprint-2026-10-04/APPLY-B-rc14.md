# APPLY B-rc14: writing pass over rc13 (2026-10-05)

`B-v2-rc13.md` was copied to `B-v2-rc14.md`, and only rc14 was edited. rc13 is unchanged.
No git, no Zenodo, no voices, no VPS, no API calls.

The pass ran the `avoid-ai-writing` skill in mode edit, with voice technical and context
research paper. Its scope was the prose that changed since rc6, the last writing pass
(`diff B-v2-rc6.md B-v2-rc13.md`: 137 line ranges, 1 253 body lines), plus the Abstract and §9
in full. The following were left untouched: SHAM-JANELA blocks, struck text, the working list
and changelog, tables, quotations and code.

## Edits (11, all mapped to a hunk ID in parity)

| ID | where | before → after | pattern |
|---|---|---|---|
| E1 | Abstract, spec sentence | "written on 2026-09-10 and dated by our commit log, not deposited with the registration (ten days before … computed)" → "written on 2026-09-10 (ten days before … computed), dated by our commit log and not deposited with the registration" | misplaced parenthetical. Both qualifiers kept |
| E2 | Abstract, uncertainty | "Our two statements about uncertainty rest on different constructions. The planning power approximation and the realized bootstrap interval use different variance constructions and assumptions;" → one sentence naming both, "rest on different variance constructions and assumptions;" | repeated scope clause |
| E3 | Abstract, closing paragraph | "The primary test does not reject the sharp null. Given … above, this result neither establishes …" → "Given … above, the primary test's non-rejection of the sharp null neither establishes …" | restatement of l.97 |
| E4 | §3, 09-02 | "The ground is real:" → "That ground holds:" | hollow "real" |
| E5 | §4.0.2 closer | cut "We would rather have found this before an adversarial reviewer told us the test was missing." | narrated-candor closer. Its content is §4.0.1's opening, "Both were found by adversarial review of this manuscript, not by us.", which stands |
| E6 | §4.1.1 | "**Caveat.** This also disciplines §4.3: … established, which is a further reason …. The caveat applies" → "The same limit disciplines §4.3: … established; that is a further reason …. The limit applies" | run-in bold label, run-on sentence |
| E7 | §4.1.2 | the "since the frozen sample …" clause moved after "in every interval that uses stratum B (…)"; "and it is not negligible:" → "It is not negligible:" | clause order |
| E8 | §4.5, Correction (rc7) | "Designated-chunk serving occurrences were approximately uniform … That differs from the planning statistic, which counted …; the present measurement therefore does not test" → "Those occurrences were approximately uniform …; because they are not the covered action opportunities the planning statistic counted by signature, the present measurement does not test" | repetition. "approximately" kept |
| E9 | §9, first observation | "Neither document was wrong; they were never read against each other. The failure mode is two locks that each look complete alone, with no step in the process whose job is to cross them." → "The two were never read against each other, and no step in the process had the job of crossing them." | three restatements of "correct in isolation", aphoristic closer |
| E10 | B.1 | "two of them had no artifact at all: the coverage figures and … M10 (§4.6) were computed by an ad-hoc script and never saved." → "two of them, the coverage figures and … M10 (§4.6), had no artifact at all; an ad-hoc script computed them, and they were never saved." | double colon |
| E11 | B.1 | "**Caveat.** Several of these are **outside the repository** and several are large." → no label, no bold | run-in bold label, bold overuse |

## Counts by pattern (scoped prose)

| pattern | found in scope | changed | left, and why |
|---|---:|---:|---|
| em-dash splice | 21 `—` | 0 | 20 sit in table cells and 1 inside the PREREG italic quotation (§4, "adjudication volume and panel — LOCKED …"). Both em-dash counts are 39, so nothing was added |
| run-in **Correction/Note/Caveat** label in body prose | 8 | 2 (E6, E11) | the 5 `**Correction (rcN).**` labels and `**Deviation (rc11)…**` carry the version that made the correction and sit next to struck text, so they are part of the record. The §7 threat headers and §8.5 position labels are list structure. Caveats outside the scope (header, §1.1, §2, §3.0.1, §3.1, §4.0.1b, §4.5) were not touched. `**Caveat.**` went from 11 to 9 |
| repeated scope clause / restatement | 5 | 5 (E2, E3, E5, E8, E9) | none. No qualifier was dropped; see the qualifier set below |
| aphoristic paragraph closer | 4 | 2 (E5, E9) | the abstract's "silence, or a claim" and §9's "worth less than nothing" are the paper's stated position and are kept. "a method cannot be optimistic selectively" is attributed to the reviewer |
| "It's not X, it's Y" | 3 | 0 | each one names a contrast the paper argues: "a property of the registration, not of the realized window", "directional bias … not indeterminacy", "an artifact of the clock, not of the arm" |
| triads | 0 | 0 | none |
| hollow intensifier | 18 hits | 1 (E4) | "exactly" (4) is literal. "truly agreed" sits inside a locked headline. "actually worked" (§4.2) marks the contrast with idle sessions. "robust" (6) is the statistical term inside locked qualifiers |
| syntax (parenthetical, clause order, double colon) | 3 | 3 (E1, E7, E10) | none |

Word count: total 41 909 → 41 870 (−39), body before the working list 34 072 → 34 033 (−39).
The working list and changelog are byte-identical to rc13.

## Parity

Running `python3 B-rc14/parity-rc14.py` gives **PASS**. The script (sha256 `04e2dc01…`) imports
`B-rc13/parity-rc13.py`, pinned at `89172df4…`, which carries rc12's and rc11's checks.

- 11 hunks, each with an edit ID (E1–E11).
- These are multiset-equal from rc13 to rc14:

  | invariant | count |
  |---|---:|
  | numeric tokens | 3 756 |
  | § cross-references | 724 |
  | code spans | 1 303 |
  | italic quotations | 45 |
  | straight-quoted strings | 114 |
  | path-like tokens | 267 |
  | citations | 112 |
  | DOIs | 37 |
  | struck spans | 81 |
  | table lines | 203 |
  | image links | 2 |

  The 40 headings are identical, and the working list and changelog are byte-identical.
- SHAM-JANELA: all 10 blocks are byte-identical to rc13.
- Carried locks: `claims_rc13`, i.e. rc11 (a)–(f), rc12 (g)–(h) and rc13 (i)–(l), and all 61
  headlines of rc11, rc12 (except the §7 "drifted" sentence that rc13 rewrote) and rc13.
- Qualifier set:
  - (a) 101 locked phrases must keep their rc13 counts. These are the reviewers' qualifiers
    ("deposited reading", "not robust", "not that the dose had no effect", "under the
    registered BCa construction only", "no contemporaneous record", "did not reproduce",
    "declared before its first call", "dated by our commit log", "not deposited", "does not
    reject", "contains zero", "may under-cover", "not established", …), rc13's census marks
    and every carried headline. Two deltas are justified, both from E3: "does not reject"
    −1 and "non-rejection" +1, because the cut restatement was folded into the next sentence.
  - (b) A multiset of 36 hedge words over the body, struck text removed. The justified deltas
    are "neither" −1 (E9), "alone" −1 (E9), "would" −1 (E5), "rather" −1 (E5) and
    "therefore" −1 (E8, kept as "because"). "not" nets to zero: E3 removes one and E8 adds one.
    The script fails on any delta it does not list, and on any listed delta that is not measured.
- Carried integrity: rc11 script (13), rc12 census record (14), rc13 B-censo paths and bridges (15).

`--self-test`: all **27 mutations are caught**, and the unmutated rc14 passes. The mutations
cover:
- a number and a § cross-reference inside edited paragraphs
- a hedge added, a qualifier dropped, and non-rejection turned into rejection
- each reviewer qualifier weakened, including "only" dropped, "drifted" for "did not
  reproduce", and the dose qualifier inverted
- "may" removed, and a negation removed
- a code span, an italic quotation, a table cell, a heading, struck text, the changelog, a
  SHAM block and a citation
- an unmapped hunk
- two carried claim locks, two carried B-censo mutations and one carried census-record mutation

The run does not count a mutation as caught when its only failure is the hunk-ID check, except
for the unmapped-hunk test. `B-rc13/parity-rc13.py` still passes on rc12 → rc13.

## Not done (declared)

- Prose that has not changed since rc6 was out of scope. That includes the aphoristic
  closers in §3.1, §4.1 ("process failure … and still a failure"), §4.0.1b ("That is the
  whole purpose of the control") and Appendix A ("a second copy that will diverge from the
  first").
- rc14 has not been reviewed.
