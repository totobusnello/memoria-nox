# APPLY A-rc18 (2026-10-05): notes of REVIEW-A-rc17-2026-10-05.md

Input `A-v1.1-rc17.md` (sha256 `e6798b11…930d9d`) → output `A-v1.1-rc18.md` (sha256
`f8b43d23…88d2d1e`). Gate: `A-rc18/parity-rc18.py --selftest`: PARITY OK, SELFTEST OK (27
mutations: 26 bite on the expected check; the unit mutation is not caught, as in rc10 to rc17, and
the selftest records that as a known limit). The deposit copy
`deposit/paperA-v1.1/spare-capacity-narrow-surface-v1.1.md` is byte-identical to rc18 (parity
`deposit` check).

The review is saved in `REVIEW-A-rc17-2026-10-05.md`: Fable's three notes on the rc16 → rc17
diff, verbatim as relayed, verdict GO. IDs: F18-1..F18-3 = Fable notes 1..3.

parity-rc18 carries every rc17 check (numbers, footnotes, refs, code, links, headings, tables,
history, qualifiers, the 35 `classes`, `withdrawn`, dashes, addendum, deposit). `history`: rc18
corrects no earlier addendum, so the addenda rc5..rc17 must be byte-identical (the last sentence of
the rc17 addendum is qualified by the rc18 addendum, not edited). `withdrawn` carries the 97
phrasings of rc11 to rc17 and adds 6 (F18-1 ×1, F18-2 ×5). One heading changes (F18-1, declared);
no table row changes. One qualifier delta: `no-record` +1 (F18-3).

| # | verified against | holds? | applied? | note |
|---|---|---|---|---|
| F18-1 [low] §8.3 heading | rc17 §8.3 body (l.2052-2083): it speaks of pre-registration in clinical trials and psychology, its absence from the survey, the OSF `yf7d2` study and the correction; "in systems CS" left the body in rc17 (C17-2). `grep "systems CS"` in rc17: the heading and two F-5 addendum lines (history), nothing else. No cross-reference quotes the heading text (the description, the build scripts and the preamble do not either; `build/*.tex` are generated) | yes | yes, Fable wording | "### 8.3 Pre-registration, and what this paper does not claim about it". The section's own last paragraphs say what is not claimed (precedence, pre-registration of this manuscript), so the heading names what the body does. |
| F18-2 [low] §1 gap bullet | §3.1 (rc17 l.326-333): `brief_log` records the items the brief selected, written before rendering; counts are of logged selections | yes | yes, Fable wording | "how many distinct items a system in production selects for an agent, and which ones." **Sweep (class: the measured quantity phrased as what the agent sees or receives), every "see/sees/seen/saw/receive/receives/received" outside Appendix F:** §1 question "what does the agent receive?" → "what does the system select for the agent?"; §5.5 "To move what the agent sees beyond that bound" → "what the brief selects"; §9 caveat "boundary between "what the agent sees" and "what exists"" → ""what the brief selects for the agent"". Kept, not of the class: §1 "presupposes … that what the agent receives is the top of that ranking" (the retrieval presupposition, not the measurement); §2 "No agent asks for it: it receives it" (the brief as such, kept in C17-1 too); Abstract "what the agent received … was always the control" (which arm, kept in C17-1); §4.3.2 and §8.2 "the agent, which/who sees the item" (conditional, unmeasured loop); §8.2 "an agent that receives 10 items at once" (the format of the surface in the analogy); "the channel sees 0.16%", "sub-pool sees", "the slots that the stratum receives", "which chunk receives exposure", "the two S1 items … receive" (not the agent); §8.1 "under the traffic it received" (the neighbours, and the system's traffic); Appendix E row ("the function receives the instant"); Appendix F (history). Description: the v1.0 quote "how many distinct items an agent in production actually receives" is already listed as superseded (C17-1). |
| F18-3 [low] §3.1, outside the diff | `serving-brief.ts` (= deposited `scripts-v1.1.zip` member, md5 `ffe9d2d0…70bb87b4`; cited as `brief.ts`) `:1081-1101`: the `INSERT INTO brief_log` loop over `result.items` sits in `try { … } catch { // fail-open: tracking nunca derruba o priming }`; the `catch` body is that comment only, with no counter, log line or metric, and the response is returned after it (`:1103-1106`), so a failed write still serves the brief. The loop is not in a transaction, so a failure part-way leaves the earlier rows. `grep -n "catch"` over the file: the other fail-open catches (`:576`, `:713`, `:752`, `:1028`, `:1076`) also record nothing; none of them is on the log write | yes | yes, adapted | §3.1, right after the logged-selections sentence that follows the truncation sentence: "The lower-bound reading of *no-record* (defined below) also assumes that this log write never failed: the write is fail-open (`brief.ts:1099-1101`), so a failed write would deliver items with no row, and the code records no such failure." Placed after "*served* … means selected and logged" so that "therefore" keeps its premise (the truncation sentence) adjacent. Description: the lower bound is stated in the 83.78% bullet, not in the logged-selections bullet, so the assumption went there: "The bound also assumes that the brief's log write, which is fail-open and records no failure, never failed: a failed write would deliver items with no row." The other statements of the lower bound (Abstract, §1, §3.1 correction, §4.1, Appendix F) point to §3.1, where the assumption now sits; they are not repeated. |

## Number deltas (all declared in parity-rc18 with finding IDs)

F18-3 §3.1: 1099, 1101 +1 each. Code: `brief.ts:1099-1101` +1 (F18-3). Heading: §8.3 replaced
(F18-1). Qualifier: `no-record` +1 (F18-3). No footnote, reference, link or table change.

## F-5

"Addendum, rc18 (2026-10-05): a Fable review of the rc17 diff." appended after the rc17 addendum,
before Open items. No earlier addendum is touched.

## Package

`build-package.py`: `FONTE` → rc18; `REVIEW-A-rc17-2026-10-05.md` and `APPLY-A-rc18.md` added to
the artefacts, `A-rc18/parity-rc18.py` to the scripts (the rc18 addendum cites all three). The
description block: the F18-3 sentence above, the package counts, "rc8 to rc18" and
"(rc18, Appendix F-5)". Rebuild results are in `deposit/paperA-v1.1/DRAFT-READBACK.md`.
