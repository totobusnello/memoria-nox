# APPLY B-rc24: LOW wording fixes of the two final GO reads of rc23 (2026-10-07)

`B-v2-rc23.md` (`ff46bd65…`) was copied to `B-v2-rc24.md` (`f66bf8c6…`), and only rc24 was
edited. No git write, no Zenodo write, no voices, no VPS, no LLM API call; the ballast (manifest
and both copies) was read, not changed. Parity: `B-rc24/parity-rc24.py` (`5340173f…`) passes;
`--self-test` caught 35 of 35 mutations (each S24 mutation by its own S24 leg) and the unmutated
file passes. `parity-rc23.py` still passes on rc22 → rc23.

## Sources

Both final full reads of rc23 are GO with no MEDIUM and no HIGH:

- **Fable** (critic agent run; no file left): four LOW (F1–F4 below).
- **Codex**: receipt `receipts/adversary-receipt-codex-2026-10-07T093115-73165.txt` (`voice:
  codex`, `exit: 0`, 238 s), verdict `REVIEW-B-rc23-codex-2026-10-07.md`, five LOW (X1–X5).

rc24 changes wording only; no number of the analysis or of the sham results moves (parity: no
numeric token removed; tokens added are rc23 tokens, the runner start and the receipt name).

## Findings, verified, applied

| # | where | verification | applied |
|---|---|---|---|
| F1 | §4.0.1c | `B-sham-v2/job-janela2/DETERMINISMO.json` has `REAL_vs_amostra200` (400/400 on 200 states, 0 outside the window) and no sham-against-sample field; the shams are compared only with `job-v2b` (4,032/4,032 each) | "as are the 200 states of the calibration sample (400/400)" → "and the real run's records for the 200 states of the calibration sample are identical to that sample (400/400)" |
| F2 | status header, working list 24 | the two reads above | status: "rc23 has not been reviewed" → "rc23 had two full reads, Fable and Codex, both GO with no MEDIUM or HIGH, Codex receipt …", plus the rc24 entry; working list 24: an rc24 note appended (the rc23 note stays as history, like every earlier one) |
| F3 | §4.0.1c first limit, working list 15 | `job-janela2/RECIBO.txt` line 1: `inicio 2026-10-05T09:40:32Z … (ate 2026-10-08T20:09:53Z)` (deadline = 09:39:53Z + 297 000 s); `JANELA-LANCAMENTO.md`: `## Relançamento 2026-10-05T09:39:53Z` | "runner start 2026-10-05T09:40:32Z" beside the relaunch time; in item 15 outside the struck text (the struck text is unchanged) |
| F4 | status header | `RESUMO.json` `fidelidade_real.estados` = 11,812 | "changed 790 brief states of the trial window" → "changed 790 of the 11,812 reconstructible brief states" |
| X1 | §4.0.1c limits (rc23 l.1243) | wording | "a randomization p-value only to that extent" → "not a calibrated randomization p-value" |
| X2 | §4.0.1c "What it adds" (l.1276) | 449–583 is the min–max of the 20 shams (`RESUMO.json`) | "the background that a matched designation produces" → "the range produced by these 20 matched designations" |
| X3 | §8.3 (l.2285) | `job-v2b`: `inicio 2026-10-04T11:19:52Z`, `CONCLUIDO 2026-10-04T23:47:06Z`; `job-janela2`: `inicio 2026-10-05T09:40:32Z`, `CONCLUIDO 2026-10-07T02:09:46Z` | "and again over the whole hash-verified trial window in a second run, 2026-10-05 to 2026-10-07" |
| X4 | Appendix B, v3 row (l.2658) | `MANIFESTO-LASTRO-P2.json` (`d310e4e9…`) entry `_sprint-2026-10-04/B-registered`: `2555baf8…`, 19 files; recomputed on the live directory with the manifest's own `sha256_dir` (`scripts/manifesto-lastro-p2.py`): `2555baf8…`, 19 files, `RESULTADO-v3.md` among them; `diff -r` against the ballast copy: identical | "no recorded sha256 covers that file" → "the corrected file is covered by the rc23 ballast manifest through the `B-registered/` directory hash" |
| X5 | Appendix B, manifest row (l.2676) | the manifest cannot hash itself; see the finding below | exceptions: "the manifest itself, `B-censo/raw/` …, and the two records of the final Codex read of rc23, written after the manifest" |

## Found while verifying X5, and stated (not fixed)

The manifest's `_sprint-2026-10-04/receipts` entry (`504d38c7…`) hashes **22** receipts. The
Codex receipt of the rc23 read and `REVIEW-B-rc23-codex-2026-10-07.md` were written after the
manifest was extended (2026-10-07 12:02Z), so the live `receipts/` now holds 23 files and hashes
to `8ba721af…`, not to the manifest entry; the ballast copy holds the 22. Neither record is in the
manifest. rc24 says so instead of claiming coverage: the manifest row names them among the
exceptions, and a new Appendix B row lists the two records (receipt and verdict) with that
statement. Extending the ballast was not part of this task; if wanted, it is one more
`LASTRO-B-item10.md` §7 pass (the `receipts/` entry would have to be re-hashed or a new entry
added, since entries are appended, not regenerated).

## Text changes (rc23 → rc24)

| where | change |
|---|---|
| status header | F2, F4, the rc24 entry |
| §4.0.1c | F1, F3, X1, X2 |
| §8.3 | X3 |
| Appendix B | X4; X5 manifest row; one new row (the rc23 Codex receipt and verdict; the Fable read left no file) |
| working list 15, 24 | F3 (outside the struck text); rc24 note |
| changelog | block rc24, items 195–203 |

Not changed: any number of the analysis or of the sham results, any heading, any earlier
changelog line, any struck span, the H1 family.

## Parity (`B-rc24/parity-rc24.py`)

- Pins `parity-rc23.py` at `167263a2…` and rc23 at `ff46bd65…`; carries every earlier lock and
  integrity block (S…S23, with S19/L6 replaced by S23/M as in rc23).
- Three rc23 locks that rc24 makes false on purpose are replaced, not dropped: the status mark
  "rc23 has not been reviewed" (now forbidden in the header), the S23/X status sentence (re-derived
  from `RESUMO.json` in its new form, S24/F4), and the manifest-row present-lock (X5).
- New sweep locks forbid each old wording; new present-locks pin each new one.
- S24 checks every fact a fix rests on: DETERMINISMO (F1), RECIBO and JANELA-LANCAMENTO (F3),
  `RESUMO.json` (F4), the two jobs' dates (X3), the `B-registered/` directory hash by the
  manifest's own function and the manifest entry (X4), the 22-receipt `receipts/` entry and its
  ballast copy, and that neither rc23-read record is in the manifest (X5), the Codex receipt
  (`exit: 0`, no IP) and verdict (GO, no MEDIUM/HIGH, LOW at 1243/1276/2285/2658/2676).
- Declared deltas: phrase "not a calibrated" +2 (X1 and changelog 199); hedges per hunk group
  (ST no +2, only +1; X1 not +1, only −1; X4 no −1; X5 not +1, no +3); no numeric token removed.
- **Caveat:** S24/M reads `~/Backups/paper2-ensaio-2026-09-21` (outside the repository, by
  design); without it, it is a NOT VERIFIED warning, never a pass.
