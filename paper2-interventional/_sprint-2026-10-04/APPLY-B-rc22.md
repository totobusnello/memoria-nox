# APPLY B-rc22: final read of rc21 applied (2026-10-06)

`B-v2-rc21.md` (`c0589f85…`) was copied to `B-v2-rc22.md` (`168ddd5d…`), and only rc22 was
edited. No git write, no Zenodo write, no voices, no VPS, no LLM API call. Source: Codex's final
read of rc21, GO with three LOW, as relayed. The receipt is
`.remember/adversary-receipt-codex-2026-10-06T133927-60502.txt` (voice codex, `exit: 0`,
2026-10-06T133927 → 134426, 299 s). No output file from that run sits beside the receipt, so the
verdict text is as relayed. Each finding was checked against the artifacts and
`DEVIATIONS-FOR-PAPER.md` before it was applied. None was rejected. One was adapted (LOW 2,
wording). rc22 is the text frozen until the whole-window sham result is integrated. Parity:
`B-rc22/parity-rc22.py` (`82b14a53…`) passes. `--self-test` caught 29 of 29 mutations, and the
unmutated file passes.

## LOW 1 §4 Adjudication: **holds**

| leg | `unknown_ponderado_sobre_oportunidades` | % |
|---|---|---|
| v4 `registrado` (substitution panel) | 0.009998 | **1.00%** |
| v4 `atual` (three families, the manuscript's "sensitivity analysis") | 0.013412 | 1.34%, **holds** |
| v2 `registrado` | 0.010193 | 1.02%, the stale value |

The 1.02% came from v2. v3 and v4 give 0.009998. The text says "the sensitivity analysis uses the
three families alone", and the v4 configs agree: `atual.painel = 3fam`, `registrado.painel =
substituicao`. The 10% rule fires on neither leg. Sweep: there was no other "1.02%" citing the
registered leg. The other `1.02` tokens in the body are l.1532 (`−61.02`, a CI bound) and l.1659
(`−1.02`, an effect estimate), and neither is the unknown share. The rc22 changelog cites 1.02%
only as the old value.

## LOW 2 Working list 4: **holds**, adapted

- The expiry measurement `out/expiracao-designados-2026-09-09.json` has `ts`
  2026-09-09T17:46:27Z. The draft, with §3.0.1, was opened 2026-09-21 (status header).
- The new text is "Measured 2026-09-09; incorporated into the manuscript 2026-09-21. Only dose
  eligibility, not continued data collection, was limited to 20 epochs."
- Adapted: "`N = 234` **was** infeasible" became "a dosed `N = 234` **was** infeasible". Left
  unqualified, that sentence would contradict the clause added after it and the rc20 framing in
  §3.0.1 ("neither 234 randomized epochs nor the calendar cap was reached"). This is a declared
  tail edit (`TAIL_EDITS`).

## LOW 3 Appendix A: **holds**

§10.14 (*"Decisão revisada (2026-09-09, tarde): não alargar a janela. O ensaio termina em
2026-09-20"*) and §10.22 (*"Desfecho: decisão explícita, janela elegível e o desligamento
armado"*) hold the closure decision of §3.0, and both are in the log. The new text reads "the
substantive ones for this paper are §10.14 and §10.22 (the closure decision of §3.0) and §10.29
through §10.34". The list of items absent from the log does not change, which matches rc20
changelog item 174.

## Files

- `B-v2-rc22.md` contains the three edits, the rc22 status entry (Codex GO on rc21, the receipt,
  the freeze), the working list 24 note, and changelog block rc22 (items 185–187). The 10
  `SHAM-JANELA` blocks are byte-identical to rc21. No heading changed. Body numbers: `1.02` −1
  (declared), `1.00` +1 (v4). No hedge or locked-phrase delta.
- `B-rc22/parity-rc22.py` checks rc21 → rc22. It pins `parity-rc21.py` (`47ddf0f6…`) and rc21's
  bytes, and it carries every earlier lock, including all of rc21's (S21, CD, the L2 and M1
  sweeps), the title, "did not stop early" and the Appendix A count. New sweep locks bar
  "unknown share of opportunities is 1.02%" and "substantive ones … are §10.29". New presence
  locks pin U1 and A3. The status marks require the rc22 entry, the receipt name and the freeze
  clause. The new source block S22 checks the v4 registered share (1.00%), the v4 `atual` share
  (1.34%) and the two panel configs, the v2 provenance of 1.02%, the 2026-09-09 date of the
  expiry artifact, the 2026-09-21 draft date, the §3.0.1 horizon sentence, the §10.14, §10.22,
  §10.29 and §10.34 headings, and the receipt (codex, `exit: 0`, 2026-10-06T133927).
- **Caveat:** S22 reads the receipt from `.remember/`, which is in `.gitignore`. The parity
  therefore runs only on this machine. A copy elsewhere, or CI, fails with "S22/ST" until the
  receipt is versioned or copied beside the script.
