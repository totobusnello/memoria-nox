# APPLY B-rc21: review of rc20 applied (2026-10-06)

`B-v2-rc20.md` (`617d90ea…`) was copied to `B-v2-rc21.md` (`c0589f85…`), and only rc21 was
edited. No git write, no Zenodo write, no voices, no VPS, no LLM API call. Source: the Fable read
of rc20 (NO-GO, two MEDIUM, six LOW, no HIGH), as relayed; Fable ran as a `critic` agent, so
there is no receipt file. Each finding was verified against the manuscript and
`DEVIATIONS-FOR-PAPER.md` (§10.13, §10.14, §10.15, §10.22, §10.28, §10.29) and the artifacts
before it was applied. None was rejected. Three were adapted (M-1, L1, L2) where the proposed
text said more than the source. Parity: `B-rc21/parity-rc21.py` (`47ddf0f6…`), PASS;
`--self-test` caught 35 of 35 mutations, and the unmutated file passes.

## M-1 §3.0.1: **holds**, adapted

| fact | source |
|---|---|
| morning of 2026-09-09: decision to **widen** the window (*"Escolhido: alargar a janela do pool global"*) | DEVIATIONS l.1467–1470 (§10.13) |
| *"A primeira metade desta decisão foi REVERTIDA no mesmo dia — ver §10.14"* | l.1472 |
| afternoon: *"não alargar a janela. O ensaio termina em 2026-09-20"* | §10.14 heading, l.1536 |
| instruction *"encerra 20/09 mesmo, e desliga a dose depois"*, 14:38 BRT | §10.22, l.2410–2412 |
| expiry artifact `ts` 2026-09-09T17:46:27Z | `out/expiracao-designados-2026-09-09.json` |

"Left the design decision open" is false: the decision was taken that day. Applied as "on the
day the decision was taken not to widen the window and so to end the trial at the `09-20`
epoch (§3.0; DEVIATIONS §10.13, §10.14, §10.22)". I did **not** use Fable's "in the session that
took the decision". The log does not show that one session made both the measurement and the
decision. §10.13 cites a sibling session, `memoria-nox-21`, and the expiry artifact is timestamped
8 min after the 14:38 BRT instruction.

## M-2 Abstract: **holds**

Before the sentence, the Abstract names the primary switch (*"It is therefore a deviation from
the public registration"*) and the horizon (*"The trial ended before its registered 234-epoch
horizon"*). Both were deposited before the seed and not kept. Applied verbatim. §9 already says
"Three further commitments", so the two now match. The rc13 headline lock "Three commitments made
before the seed were not kept." is declared −1 in `JUSTIFIED_PHRASE`.

## L1 §3.0: **holds**, adapted

Applied, keeping the file name once. "14:38 BRT" became "14:38 local time, UTC−3", because the
manuscript never uses "BRT" and §1.1 writes its times as "(local time, UTC−3)".

## L2 §3.0: **holds**, adapted

- 20/672 at `09-08`: §10.14 l.1566 (`churn>0` em 20/672 no epoch 09-08). The positive control
  matches `out/CONTROLES-2026-09-10.json` `por_epoch.2026-09-08` (treatment, `mexeu` 20, `n`
  672) and manuscript l.975.
- "Data-dependent" overclaimed, because the decision did rest on data. "Outcome-dependent" is
  the right term.
- Fable's "it rested on the expiry measurement and on the positive-control reading" reads as an
  exhaustive list. §10.14 also weighs the cost of widening the window (pool 115 → 305), and it
  cites a replay on the realigned corpus that §10.15 later withdrew as a ground (note at
  l.1538). The applied text is "it rested on measurements, not on outcomes, among them the expiry
  measurement and the instrument's positive-control reading of `09-08` (20 of 672 briefs
  changed; §10.14)". The old "no outcome had been computed …" clause is now its own sentence.

## L3 §1.1: **holds**

The new sentence under "What requires trusting us" dates the closure decision to 2026-09-09,
before any outcome. That date rests on the times written in the deviation log (§10.14; §10.22,
14:38 local time) and on the dry-run receipt `YELLOW p2-desliga-dose
motivo=janela-ainda-aberta-faltam-279h` of 2026-09-09 17:42:31Z, quoted in §10.28 l.2992–2993.
That receipt comes 4.5 min after the instruction (14:38 BRT = 17:38Z). It fits "append-only is
process discipline", which §1.1 already says.

## L4 §3.0.1: **holds**

`09-20` has `braco: control` (`ITT-REGISTRADO-v4` `pernas.registrado.por_epoch.2026-09-20`;
manuscript l.1828). "could reach" → "could have reached".

## L5 changelog item 174: **holds**

The old relative clause could be read with "which" as its subject. Applied verbatim as a
declared tail edit (`TAIL_EDITS`). rc19 item 172 set the precedent for this kind of edit.

## L6 §9: **holds**

The rc8 changelog item 104 records the stopping rule of §3-bis as met and not executed. The
§3.0 heading also says "Correction (rc8, …)". "while preparing this version" → "while preparing
rc8". A sweep found one other "for this version" in the body, l.535 (*"We did not inspect the
production host for this version"*). It is still true for rc21, so it was left unchanged.

## Files

- `B-v2-rc21.md`: the edits above, the rc21 status header, working list 24 note, and changelog
  block rc21 (items 178–184). The 10 `SHAM-JANELA` blocks are byte-identical to rc20. No
  heading changed, and no number of the analysis moved. No body number was removed. The added
  tokens are 14:38 and 17:42:31Z, both checked in S21; every other token is already in rc20.
- `B-rc21/parity-rc21.py`: rc20 → rc21. It pins `parity-rc20.py` (`3210aa95…`) and rc20's bytes,
  and it carries every earlier lock, including the title, "did not stop early", the Appendix A
  count of 12 with the horizon item, and the closure date CD. CD is now also a presence lock,
  and a sweep lock bars "decision taken on 2026-09-21". The new sweep locks bar
  "data-dependent stop", "left the design decision open", "in a session that recorded it",
  "could reach a designated", "while preparing this version", "Three commitments made before
  the seed were not kept" and the undated "the author's explicit instruction)". Hedge deltas are
  declared per hunk: L1 `not` +2, M1 `not` +1, L3 `any` +1, ST `any` +1. The new source block S21
  checks §10.13 (widen, then reverted), the §10.14 heading, 20/672 and the §10.15 note, §10.22
  at 14:38 BRT, the §10.28 receipt, CONTROLES `09-08`, `09-20` as control, the date of the expiry
  artifact, rc8 item 104, and that the Abstract names the switch and the horizon before
  "Three further".
