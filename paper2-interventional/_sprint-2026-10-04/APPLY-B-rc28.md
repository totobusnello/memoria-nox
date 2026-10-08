# APPLY B-rc28: the final reads of the rc27 package (Grok, Fable), both NO-GO (2026-10-07)

`B-v2-rc27.md` (`cb38c5cf…`) was copied to `B-v2-rc28.md` (`449d4dec…`), and only rc28 was
edited. No git write, no voices, no VPS. Zenodo: read-only GETs of the public API, and the
`deposit-v2.0.py --fill` / `--readback` of the existing draft 23223385 (no new draft, no publish).
Parity: `B-rc28/parity-rc28.py` (`cf50fe56…`) passes; `--self-test` catches 21 of 21 mutations,
each by its own leg, and the unmutated file passes.

## Sources

| read | object | verdict | record |
|---|---|---|---|
| Grok 4.7 | the built package (`registered-horizon-outlived-intervention-v2.0.md`, rc27 with the DOI) | NO-GO: six MEDIUM, five LOW | `receipts/adversary-receipt-grok-2026-10-07T181540-7884.txt` (exit 0, attach 338,670 bytes; host and home path redacted) |
| Fable | the built package and its description | NO-GO: one HIGH, four MEDIUM, two LOW | agent run, no receipt |
| Codex | — | did not run: exit 1 after 4 s, the account being out of credits | `receipts/adversary-receipt-codex-2026-10-07T181828-14394.txt` (exit 1) |

The receipts record the exit code and the byte counts, not the reason for the Codex failure; the
reason (no credits) is as reported by the session that launched the read.

## Findings: verification and what was applied

| # | finding | verification | verdict | applied |
|---|---|---|---|---|
| F-H1 | header l.6–7 and description l.2: "Versions 1.0 to 1.12 … the registration and its amendments" | public API `GET /api/records/22110203/versions`: **3** published versions of concept 21964093: 1.9 (record 21964094, 2026-08-17), 1.11 (21978476, 2026-08-17), 1.12 (22110203, 2026-08-26); 1.11's description: "an error correction" and "Version 1.10 was written and never deposited"; 1.12's: "the amendment is descriptive". The draft's `versions.index` 4 = these 3 + 1 (no deleted or hidden version needed to explain it). Snapshot: `B-rc28/zenodo-21964093-versions.json` | holds | header and description list the three versions with records and dates |
| F-M1 | description "declares every deviation … listed below" with 6 items | Appendix A lists twelve live items (one struck); `DEVIATIONS-FOR-PAPER.md` is in `artifacts-v2.0.zip` | holds | "declares the deviations"; Appendix A lists the twelve a reader cannot reconstruct; the packaged append-only log holds the others; heading "Six of the deviations … the full list is there" |
| F-M2 | header lacks rc27 and stops at "rc3 to rc26" | header text | holds | rc27 line (items 208–210), the two final reads both NO-GO, the confirmation read planned, "rc3 to rc28" |
| F-M3 | item 24 promises a final read by Grok, Codex and Fable | receipts above | holds | the rc27 sentence struck; rc28 note: what each read did, Codex did not run, rc28 itself not read, confirmation read planned |
| F-M4 | READY.md / DRAFT-READBACK.md top out of date | `.draft-id-v2.0` = 23223385; readback summary of 21:10Z all ok | holds | both rewritten to the real state (outside the text) |
| F-L1 | item 8 "Done, rc27 (2026-10-07)" dates the deposit | publish is manual and later | holds | "Done (rc27)" + rc28 note |
| F-L2 | description "This shows that the dose acted on what was served" | same as G-M3 | holds | sham paragraph rewritten |
| G-M1 | description "the second replay contains the states of the first" | `JANELA-LANCAMENTO.md` §1: shares 2,016 of job-v2b's 2,646 (09-01's 630 w = 4 states are not in the window); 2,646 − 630 = 2,016 = 3 × 672 | holds | "share 2,016 states (the w = 4 epochs except 09-01)", in the abstract too |
| G-M2 | description "on 2026-09-20, after 20 epochs" | expiry 2026-09-20 22:51:23Z (§3.0.1); epochs start 09:00Z, so 09-20 (13.86 h by the spec) is the 20th, partial | holds | "at 2026-09-20 22:51:23Z, during the 20th epoch" |
| G-M3 | the window replay forces w = 4 everywhere, so 790 vs 449–583 is not about what was served off the w = 4 epochs | §4.0.1c already says "The dose is replayed at `w = 4` in every state, whatever arm production served there"; `JANELA-LANCAMENTO.md`: "doses w = 4 and 100,000"; production served w = 0/2/4/7.5 by epoch; the replay matches production's churn only in the 2,016 states of 09-12/14/15 | holds | the served-dose specificity claim rests on the w = 4 epochs (132 vs 81–122); the window result is stated as a forced-w = 4 counterfactual in the abstract, §4.0.1b row, §4.0.1c ("What it adds", "What this does"), §7, §8.3, §8.5 and the description; "2.83–6.85% … more through the designated items" limited to the w = 4 epochs |
| G-M4 | title | the author's decision | applied | line 1, description `<em>`, PDF title; deposit metadata takes line 1 (`deposit-v2.0.py`, unchanged) |
| G-M5 | abstract "The trial retained the registered 234-epoch horizon while adopting…" | v1.12 says 234; v1.13 held (`deposit/PLAN-v1.13.md`, Appendix A); designation chosen 2026-08-26, not deposited; window closed at expiry (§3.0.1) | holds | Grok's wording, keeping the date of the designation |
| G-M6 | description power sentence and the grouped amendment | §4.1.1 / abstract: planning assumptions, ICC of a different quantity, not calibrated; OSF API `registrations/yf7d2`: `date_modified` 2026-08-18T07:56:44Z, not withdrawn | holds | caveat added; the amendment is of this Zenodo record, OSF yf7d2 not amended |
| G-L1 | "20 epochs ran" vs 09-02 never served | §3: 20 designated, 19 served data, 09-02 empty (outage) | holds | description |
| G-L2 | assignment bullet: served arms from `assign_arms.py` | §1: "The trial served the registered rule's assignment" | holds | description |
| G-L3 | H1 sensitivity rejection (p = 0.0127) under the deposited reading | abstract and §4.0.2 | holds | description |
| G-L4 | H2: BCa only; raw time has the opposite sign | §5 table: percentile [−0.011; +0.661] and [−390; +10 748]; raw time −1.18 s | holds | description |
| G-L5 | "nine epochs as projection" at 21:40 on 09-10 vs ten epochs not yet started | `SPEC-ANALISE-2026-09-10.md` §1: "as 9 de `09-11`…`09-19` são projeção"; 09-20 entered as partial by clock (13.86 h); 09-10 omitted, still open. l.381 ("the spec … marks nine epochs as projection") is right; l.397 ("nine of the epochs were still projection") was not | holds in part | l.397 only |

## Text changes (rc27 → rc28): 16 hunks + changelog 211–222

Title; status header (versions, rc27 line, final reads, rc3 to rc28); abstract (horizon sentence;
sham replays); §1.1 caveat (nine epochs); §4.0.1b specificity row; §4.0.1c "What it adds" and
"What this does to the claims" (two hunks); §7 scope of the specificity control; §8.3; §8.5;
working list 8 and 24; changelog block rc28 (items 211–222). No number of the analysis or of the
sham results moves.

## Parity (`B-rc28/parity-rc28.py`)

- **A**: rc28 with the 16 declared hunks reverted and the rc28 block removed is rc27 byte for byte.
- **N**: every number rc28 carries that rc27 does not (1.9, 1.10, 21964094, 211, 222, and the
  receipt-name suffixes 7884 and 14394) is declared and found in its source.
- **B**: `parity-rc27.py` (pinned), run rc24/rc25/rc26 → rc28, fails with exactly the 82 declared
  failures, each caused by a hunk or the rc28 block.
- **C**: title; header versions equal to the API snapshot; abstract sham claim with the
  counterfactual; no rc27 wording that put the window on "what was served" outside the changelog;
  item 8 date-neutral; item 24 (receipts present and scrubbed, no Codex read claimed); placeholder 2×
  (= build); the build sources rc28 at its sha.
- **E**: the description (title = line 1, no "1.0 to 1.12", no "every deviation", the twelve and the
  log, six said six, expiry instant, 09-02, `assign_arms.py`, p = 0.0127, power caveat, the sham
  counterfactual and 2,016 shared states, OSF not amended).
- **D**: changelog 149..222, rc28 block = 211..222 after rc27's.

**Side effect, declared.** `parity-rc24.py` (and through it rc25, rc26, rc27, run standalone on
their own pairs) now fails one environmental lock, S24/X5, "receipts/ does not hold 23 receipts",
because receipts/ holds 25: the two receipts of this round. Nothing else in them fails.

## Description (outside the text)

`deposit/paperB/description-v2.0.html` (`13687d18…`): the changes of F-H1, F-M1, F-L2, G-M1–M3,
G-M6, G-L1–L4; avoid-ai-writing pass (detect, technical) on the changed sentences: no flags.
