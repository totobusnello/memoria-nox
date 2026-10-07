# APPLY B-rc20: review of rc19 applied (2026-10-06)

`B-v2-rc19.md` (`fe1be667…`) was copied to `B-v2-rc20.md` (`f047acd0…`), and only rc20 was
edited. No git write, no Zenodo write, no voices, no VPS, no LLM API call. Source: the Codex
read of rc19 (NO-GO, one MEDIUM, two LOW), receipt
`.remember/adversary-receipt-codex-2026-10-06T095645-63516.txt` (`voice: codex`, `exit: 0`,
764 s, output 795 018 bytes), as relayed. Each finding was verified against the manuscript,
`PREREG-DRAFT.md`, `DEVIATIONS-FOR-PAPER.md` and the artifacts before it was applied. None was
rejected. Parity: `B-rc20/parity-rc20.py` (`dcf0b5a1…`), PASS; `--self-test` 45/45 mutations
caught, unmutated PASS.

## M1: verdict **holds**

| fact | value | source |
|---|---|---|
| deposited stopping rule | *"data collection ends at **234 randomized epochs** … or the pre-committed calendar end date, whichever comes first … No interim analyses; no optional stopping."* | PREREG l.795 |
| calendar cap | `date(first randomized epoch) + 240 days`, amended 2026-08-17 to 323 days, so no earlier than 2027-07-21 for a first epoch of 2026-09-01 | PREREG l.799, l.801 |
| realized | 20 epochs, `2026-09-01` → `2026-09-20`; neither condition reached | §3.0.1 table |
| expiry as a stop | not in the registration: the only "expir…" in PREREG is the snapshot-count note at l.861 | grep |
| closure | decided 2026-09-09 (§10.14, *"O ensaio termina em 2026-09-20"*; §10.22, the instruction *"encerra 20/09 mesmo, e desliga a dose depois"*), executed 2026-09-21 09:43:05Z (§10.29) | DEVIATIONS |

So "The trial did not stop early" and "234 was infeasible from the start" claim more than the
registration grants: the trial ended before the deposited horizon, by a decision, on a condition
the deposit does not name. The closure is in the deviation log (§10.14, §10.22, §10.29), but
Appendix A did not list it.

What was applied:

- Abstract: Codex's two sentences, verbatim, replace "The trial did not stop early: 234 was
  infeasible from the start."
- §3.0.1 heading: Codex's text, verbatim.
- §3.0.1 text: "The trial did not stop early." became "The trial ended before the deposited
  data-collection horizon: neither 234 randomized epochs nor the calendar cap was reached, and
  expiry of the fixed designation is not a deposited stopping condition (Appendix A)." "Switched
  off later" became "switched off only after the fixed designation had expired". The times are
  kept.
- Appendix A: a twelfth item, "the horizon", carrying Codex's two sentences and the times of
  expiry and switch-off. The count changed from "Eleven" to "~~Eleven~~ Twelve". Appendix A did
  not already declare the closure, so the item was added and nothing was merged. The opening
  paragraph's list of items absent from the deviation log is unchanged, because the closure is
  in that log.
- Sweep across the whole body. "did not stop early", "stop early", "infeasible", "ran exactly
  as long as it could": no other hit after the edits. One adjacent sentence was changed: §3.0.1
  "so the expiry stops the trial and leaves the instrument unaffected" became "the expiry ends
  the intervention". That sentence named expiry as what stopped the trial. §1, §3.0, §7 and §9
  make no claim that the closure satisfied the registration. §3.0 says it "was not a
  data-dependent stop", which is a different claim and still holds. The title is unchanged.
  Working list item 4 ("`N = 234` **was** infeasible") is in the tail. It is a dated record and
  was not edited.

## L1: verdict **holds**

`out/ITT-REGISTRADO-v4-2026-10-05.json`, `09-20`:

| leg | hours | opportunities | repeats |
|---|---:|---:|---:|
| `atual` (sensitivity: washout kept, per-timestamp) | 0.62352 | 208.405 | 11.945 |
| `registrado_sem_janela` (registered, no cut) | 0.59018 | 215.35 | 11.945 |
| `registrado` (registered) | 0.48202 | 192.515 | 9.945 |
| block `corte_pos_expiracao` | 0.6235 → 0.5154 | 22.835 removed | 2 removed |

`so_washout_in_denominator` is also 0.59018. That shows the gap between 0.6235 and 0.5902 is the
washout. On the registered leg the cut removes the same 22.835 opportunities and 2 repeats, so
only the hours were wrong. §3.0.1 now reads "0.5902 to 0.4820" and cites the file and both legs.
The B.1 row now reads "0.5902 → 0.4820 h on the registered leg" with the field paths, and keeps
0.6235 → 0.5154 under the name of the washout-retaining diagnostic of `corte_pos_expiracao`.

## L2: verdict **holds**

§9 now reads "had a 30-day age limit, leaving 20 eligible trial epochs, 8.5% of the registered
234 (§3.0.1)". The sentence has no em dash. 20/234 = 8.5%.

## Parenthesis in §1: applied

"(option B) (the deposited bytes, md5 …; the repository file was extended …)" became one
parenthetical: "(option B; the deposited bytes are md5 `35abeb68…`, 7 036 bytes, the blob of
commit `d42f950`, and the repository file was extended after publication to record the
decision)".

## Not applied, for the author: §3.0 dates the closure decision to 2026-09-21

§3.0 says *"The trial closed at the `2026-09-20` epoch by a decision taken on 2026-09-21,
executed by `desliga-dose-p2.sh` at 09:43:05Z"* and *"the analysis specification … was written
on 2026-09-10, eleven days earlier"*. DEVIATIONS has the decision on **2026-09-09**: §10.14 (the
decision not to widen the window, ending on 2026-09-20) and §10.22 (the explicit instruction,
14:38 BRT). 2026-09-21 is the date of execution (§10.29). If that is right, the spec was
written one day **after** the decision, not eleven days before it. "No outcome had been
computed" still holds either way. This was outside the Codex findings, and the new text does not
date the decision, so it was left for the author to decide.

## Files

- `B-v2-rc20.md`: status header rc20, changelog block rc20 (items 174–177), working list 24
  note. The 10 `SHAM-JANELA` blocks are byte-identical to rc19's.
- `B-rc20/parity-rc20.py`: rc19 → rc20. It carries every earlier lock, including the title.
  The deviation-count lock (rc16's `appa_count`) is replaced: the count is 12 and the horizon
  item must be present. The struck-span invariant allows only `~~Eleven~~`. The heading
  invariant allows only the §3.0.1 heading. New sweep locks bar "did not stop early", "stop
  early", "infeasible", "ran exactly as long as it could", "expiry stops the trial", "30-day
  life", "8.5% of the registered design", "session-hours fall from 0.6235" and "(option B) (".
  Source block S20 checks PREREG l.795/799/801 and the absence of any expiry stop, the expiry
  from `expiracao-designados-2026-09-09.json` (19 items, one `created_at`, 30 d → 2026-09-20
  22:51:23), DEVIATIONS §10.14/§10.22/§10.29, the v4 legs and block, and the receipt's
  `exit: 0`.

## Main-session correction after the agent's report (2026-10-06): closure decision date
§3.0 said "a decision taken on 2026-09-21" and the spec was "written on 2026-09-10, eleven days earlier".
DEVIATIONS-FOR-PAPER.md §10.14 (2026-09-09, afternoon, "registrado antes de qualquer ação e sem consultar
desfecho") and §10.22 (author's explicit instruction, 2026-09-09 14:38 BRT: "encerra 20/09 mesmo, e desliga a
dose depois") date the decision 2026-09-09; §10.29 dates the execution 2026-09-21 09:43:05Z. Rewritten: decision
2026-09-09, executed 2026-09-21; the spec (2026-09-10) came the day after the decision and eleven days before the
first outcome was computed (ITT-PRELIMINAR 2026-09-21). Parity: hunk anchored as CD; no number removed.
