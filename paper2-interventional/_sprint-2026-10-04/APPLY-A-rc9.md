# APPLY A rc9: writing pass (avoid-ai-writing) over A-v1.1-rc8

Date: 2026-10-05. Input `A-v1.1-rc8.md`, output `A-v1.1-rc9.md` (rc8 untouched). Skill
`avoid-ai-writing`, mode edit, voice technical, context docs/academic. Whole manuscript read;
priority on the text that entered in rc5 to rc8 (`diff A-v1.1-rc4.md A-v1.1-rc8.md`, 388 changed
lines). No git, no Zenodo, no voices.

Gate: `A-rc9/parity-rc9.py` (OLD rc8, NEW rc9).

```
python3 A-rc9/parity-rc9.py              # PARITY OK (12 checks), exit 0
python3 A-rc9/parity-rc9.py --selftest   # 15 mutations, 15 BITES, SELFTEST OK, exit 0
```

Checks: numbers, footnotes, refs, code (inline + fences), links/DOIs, headings (title included),
tables (as in `A-rc3/parity-rc3.py`); history (F-5 addenda rc5..rc8 byte-identical); qualifiers
(19 scope phrasings of rc6-rc8, whitespace-normalized counts unchanged); classes (the 35 = 33 + 2
forbidden phrasings, imported from `A-rc8/parity-rc8.py` so the list cannot drift); dashes (em
dashes in running prose outside carve-outs <= 0); addendum (rc9 addendum present once, in place).
The rc9 addendum is cut from NEW before every comparison.

## Counts, before -> after

Body = everything outside the F-5 addenda (rc5 onward), tables, headings and fences.

| measure | rc8 | rc9 |
|---|---|---|
| words (whole file; rc9 without its addendum) | 31,820 | 31,785 |
| em dashes, whole file | 52 | 49 |
| em dashes in running prose outside carve-outs | 3 | 0 |
| em dashes per 1,000 words, running prose | 0.09 | 0 |
| "is not X: it is Y" pivots (regex) | 6 | 2 |
| "actually" (outside title/headings) | 2 | 1 |
| "in fact" | 3 | 2 |
| "radically" / "the very" / "perhaps" | 1 / 2 / 1 | 0 / 0 / 0 |
| "exactly" (all senses) | 34 | 29 |
| significance labels ("what matters", "in its own right", "needs saying", "completes the thesis") | 5 | 0 |
| mid-list bold (non-parallel) | 1 | 0 |

The 49 em dashes left: 28 table separators/empty cells, 13 headings (§4.1, §4.1.1, Appendix A-F,
F-1..F-5; byte-identical by rule), 6 F-3 run-in labels (historical F-entries), 1 in the status
blockquote (the symbol "—" quoted from Appendix D), 1 inside the quotation
*"87 markers in 288 paragraphs — 26.7%"* (Appendix F). The manuscript was already low on prose
dashes: most of the 52 were in tables and headings.

Tier-1 vocabulary: the only hits are "beacon" (drand randomness beacon, a term of art, 4×) and
"robust" (statistical sense: "robust estimator", "robust in order of magnitude", 3×). Both left.
Stacked hedges ("could potentially", "may possibly"): none found.

## The 23 edits (rc8 -> rc9)

| # | where | before | after | pattern |
|---|---|---|---|---|
| E01 | Abstract | how much search actually delivered | how much search delivered | hollow intensifier |
| E02 | §1 | There are in fact two choices | There are two choices | intensifier |
| E03 | §1, "Why the question matters" | the surface is not small; it is 8.7× the corpus. What matters is what remains after that: | the surface is 8.7× the corpus. That leaves the following: | pivot + persuasive trope |
| E04 | §2 | what matters for the paper is the shape of the surface | the paper depends on the shape of the surface | persuasive trope |
| E05 | §4.1 | The 10,008 are not "chunks ... did not": they are chunks whose importance ... | The 10,008 are chunks whose importance ..., not "chunks ... did not", | pivot (quote kept verbatim) |
| E06 | §4.2, Figure 1 | radically greater variance | much greater variance | intensifier |
| E07 | §4.2 caveat | This needs saying because | We say this because | significance label |
| E08 | §4.3.1 caveat | which is exactly the gap | which is the gap | emphatic "exactly" |
| E09 | §4.3.1 | on the very mechanism that the paper describes | on the mechanism that the paper itself describes | intensifier |
| E10 | §4.3.1 (rc7 text) | This is a result in its own right | This is a separate result | significance label |
| E11 | §2 list | 2. **on-demand search** | 2. on-demand search | bold (item 1 is not bold) |
| E12 | §4.3.2 | **The symmetry that completes the thesis.** | **The symmetry.** | significance label |
| E13 | §5.3, consequence 3 | the ceiling is not a design parameter: it is a property of the distribution of `ℓ` ... | the ceiling is a property of the distribution of `ℓ` ..., and not a design parameter. | pivot |
| E14 | §5.7 | is not a property of the comparator alone: it is a property of how many ties | depends on more than the comparator: it depends on how many ties | pivot |
| E15 | §5.7.1 list | **redundancy** — under minute | **redundancy:** under minute | em dash |
| E16 | §5.7.1 list | **unreachability** — under hour | **unreachability:** under hour | em dash |
| E17 | §6.1 | for the very reason this paragraph describes | for the reason this paragraph describes | intensifier |
| E18 | §6.1 | which is exactly the defect | which is the defect | emphatic "exactly" |
| E19 | §6.2 | which is exactly the property one wants | which is the property one wants | emphatic "exactly" |
| E20 | §8.2 | perhaps searches for it again | may search for it again (as in §4.3.2) | hedge |
| E21 | §9, Third | one of them exactly the one that recorded | among them the one that recorded | emphatic "exactly" |
| E22 | Appendix F intro | announced as optional exactly what is not | announced as optional what is not | emphatic "exactly" |
| E23 | Open items, item 6 (struck) | from Codex's opinion — the only criticism | from Codex's opinion, the only criticism | em dash |

Plus the F-5 "Addendum, rc9 (writing pass, 2026-10-05)" paragraph.

## Left on purpose

- "exactly" where it states an identity or a count (29 left: "exactly 2 per brief", "exactly the
  lexicographic order", "exactly the 52 absent", "exactly zero effect", ...). Removing it would
  weaken a measured claim.
- "in fact" in §4.2 ("Large types are, in fact, older") and §5.7.1 ("The count does in fact rise"):
  both mark a concession the sentence then qualifies.
- "What is actually missing" (Open items): contrasts the stale list with the current state.
- The two remaining "not X: it is Y" hits: Appendix A ("is not in that log; it is reported in Paper
  B's list", two facts, not a pivot) and F-1 (correction history).
- The run-in markers ("**Caveat.**", "**Note.**", "**Correction.**"): they are the paper's
  paragraph-label convention, and Appendix F measures their density; changing them would move a
  number the text reports about itself.
- The two §1 sentences that rc8 took verbatim from Codex (registry anchors of parity-rc8), every
  rc6-rc8 scope qualifier (counted by the `qualifiers` check), the title, all headings, tables,
  quotations, code spans, and the F-1..F-5 correction history (the `history` check pins the F-5
  addenda byte for byte).
- Aphoristic closers that carry the author's argument ("Retention does not read hashes.",
  "Declaring ignorance is cheaper than measuring, ..."): voice, not filler.

## Deposit copy

`deposit/paperA-v1.1/MANUSCRIPT-v1.1.md` received the same edits (the rc8 -> rc9 unified diff,
applied with `patch`; the backup `.orig` that `patch` left was removed). Verified:

```
diff A-v1.1-rc9.md ../deposit/paperA-v1.1/MANUSCRIPT-v1.1.md
2231,2232c2231
< [TODO at deposit: insert its version DOI here, or a pre-reserved DOI if one is created before
< deposit.] The pre-registration of the interventional study is a separate record
---
> Its version DOI is `10.5281/zenodo.23163119`, reserved before deposit. The pre-registration ...
```

The only difference is the documented Appendix D DOI fill; the status block is identical in both
(rc8 already carried the deposit status). `parity-rc9.py rc8 MANUSCRIPT-v1.1.md` fails only on
that DOI (numbers `10.5281` +1, code and links +1 `10.5281/zenodo.23163119`), as expected.

Not done: `MANUSCRIPT-v1.1.pdf`, `build/` and the zips in `deposit/paperA-v1.1/` were not
regenerated and now predate the manuscript; the Zenodo draft was not touched.
