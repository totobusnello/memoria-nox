# Amendment 1 (2026-11-25, 20:40 UTC): a null quote on a "no" is an empty quote

## What went wrong

`judges.parse` required `oito_palavras` (J-pool, J-repass) and `citacao_verbatim` (J-oracle) to be
strings. When the model answers `trecho_responde: false` it often returns `null` there. The sources
read these fields as `(j.get(...) or "")`, so a `null` was an empty quote and the label was a valid
"no". The frozen parser read it as a missing label instead.

It surfaced in the J-pool full run (20:33 UTC): 329 of 555 units missing. Over 10% missing triggered
the registered re-run (§7), which started at 20:35:13 and was stopped by hand at 20:35:50 after 172
attempts (US$ 0.0088 in the ledger), before it wrote a run file. The stop was decided on the missing
count alone.

## What was seen before the fix

To find the cause, the missing J-pool rows were grouped by the parsed `trecho_responde` value and the
type of `oito_palavras`: 328 rows were `false` with `null`, 1 row did not parse. That is a count of
negative labels; nothing was compared with the key `T`, with the human annotations or with another
instrument, and no reading of §4 was computed.

## What changes

- `judges.parse`: a `null` or absent `oito_palavras` or `citacao_verbatim` becomes `""`, as in the
  sources. Any other non-string value is still invalid. Every other rule stays.
- `run.py <instrument> reparse`: re-reads the stored responses of an instrument with the current
  parser, makes no call, and keeps the run-time label as `parsed_at_run` where it changes.
- `test-stage2.py`: three cases (null on a "no" is valid for J-pool and J-oracle; a numeric
  `oito_palavras` is still invalid).

The stored J-oracle and J-pool runs (smoke and full) are re-parsed under this amendment, and the
remaining instruments run with the amended parser. The interrupted re-run produced no labels and
does not count as the instrument's one re-run; the re-run rule is applied to the re-parsed full run.
The 172 attempts stay in the ledger.
