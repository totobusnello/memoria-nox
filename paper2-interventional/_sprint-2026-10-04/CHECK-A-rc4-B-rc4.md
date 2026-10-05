# CHECK: A-v1.1-rc4 and B-v2-rc4 (independent check, 2026-10-05)

Scope: `A-v1.1-rc4.md` (2,542 lines, sha256 `e1f30245…`) and `B-v2-rc4.md` (1,965 lines,
148,941 bytes, sha256 `b5ac910c…`). The sizes and hashes match those in `APPLY-A-rc4.md` /
`APPLY-B-rc4.md`. No manuscript was edited. No git command, deposit, contact or adversarial
voice. Recomputed outputs went to the session scratchpad only.

## 1. Parity scripts

| script | result | self-test |
|---|---|---|
| `A-rc4/parity-rc4.py` | `PARITY OK` (exit 0): 77 hunks, 86/86 anchors landed, 205 numeric tokens change, 3 heading changes, 1 fence removed (`b*`, Codex-5) | `SELFTEST OK`: 3 mutations, all bite |
| `B-rc4/parity-rc4.py` | `PARITY: PASS` (exit 0): 35 tokens changed, 35 justified; 1 heading renamed (title); dangling § refs 7 → 7, 0 new | 3 mutations caught; unmutated passes |

What the parity scripts prove: every numeric change is pinned and has an owner. What they do not
prove: that any value is correct. So the values were spot-checked below against the artifacts.

## 2. Recomputation scripts dated 2026-10-05 (rerun; output compared byte-for-byte)

| script | rerun inputs | result |
|---|---|---|
| `measurement/sprint-bonus-vs-passo.py` | repo files | **byte-identical** to `out/BONUS-VS-STEP-2026-10-05.json` |
| `measurement/sprint-contrafactual-salience-producao.mjs` | scratchpad extract + `--extract52` + `--sondas out/ancora-sondas.json` | **byte-identical** to `out/SALIENCE-COUNTERFACTUAL-PROD-2026-10-05.json` (without `--sondas` the organic-144/196 legs come out empty; the recorded run used it) |
| `measurement/sprint-empates-salience-producao.mjs` | scratchpad extract + `A-rc2/COVERAGE-SET-FROM-LOG-2026-10-04.json` | **byte-identical** to `out/TIEBREAK-EXPOSURE-PROD-2026-10-05.json` |
| `measurement/sprint-c12-empates-por-braco.py` | lastro backup + `-COPIA/verdicts` | **byte-identical** to `out/C12-EMPATES-POR-BRACO-2026-10-05.json`; controls 1–3 pass |

Note on C12: the artifact records `c4_repeats.condicao_i_inalterada: false`. So control 4 did not
gate in this run; it was only reported. Its values still agree (0.00 / +1.00).

## 3. Spot-checks, Paper A (against the artifacts)

| # | manuscript | artifact value | verdict |
|---|---|---|---|
| 1 | §5.7.1 table, comparator key: second 34–42 (0.59–0.73%), minute 212–238 (3.67–4.12%), hour 472–749 (8.17–12.96%), day 1,197 (20.72%) | TIEBREAK-PROD, three window instants | match |
| 2 | pre-rank column 45–59 / 277–322 / 663–1,024 / 1,656 | same | match |
| 3 | largest block 4 / 10–12 / 18–33 / 42; 15 vs 6 distinct values | same | match |
| 4 | "28–35× from second to day" | 1,197/42 = 28.5; 1,197/34 = 35.2 | match |
| 5 | positions 1, 3, 4; last access 42 / 90 / 30 days before 2026-08-28 | `prod` ranks; `the_three` dates (07-17, 05-30, 07-29) | match |
| 6 | access zeroed: 44–46 of 149 (45–47 by day), 23–25 drop-future, 23–47 overall; 54–56 / 201; 40–42 / 144; 50–52 / 196 | SALIENCE-COUNTERFACTUAL-PROD | match |
| 7 | 39,130 NULL-retention chunks; 35 of 149 | `retention_days_null` | match |
| 8 | scope pool "1, 5 and 6 to 76–119, with 76–79 candidates from 43–46 files strictly above" | `prod_noacc`: first rank 76, **57 above, 24 files**; `prod_acc0`: 76–79 above, 43–46 files | **defect D-A1** |
| 9 | bonus 0.0473, 0.90×; old 0.0946 / 1.79× | BONUS-VS-STEP (0.8972; 1.7944) | match |
| 10 | lowest changing dose 0.02–4.4, median 1.7, five censored at 0.02 | `out/limiar-17.json` (recomputed: 17 states, 5 at 0.02, median 1.7) | match |
| 11 | 1,635 live, 1,787 with 152 deleted, 2.43%; 583,763/1,787 ≈ 327 | arithmetic | match |
| 12 | 2/9 ≈ 22%; 5,376 = 8 × 672; 18 rows ≈ 2.6/day over 7 days | arithmetic | match |

The remaining-ties sentence of §5.7.1 ("one `lessons.md` ingestion … same … access instant") was
checked against the extract: 45 groups are `memory/lessons.md` with one `last_accessed_at` and
19 are entity groups with one `last_accessed_at`. It holds, but the cited artifact does not carry
`source_file` or `last_accessed_at` (D-A3).

## 4. Spot-checks, Paper B

| # | manuscript | artifact value | verdict |
|---|---|---|---|
| 1 | fractional effective size 84.8 | `H1C-POWER-FRACIONARIA` `n_efetivo_realizado` 84.8 (10.9375T / 7.23375C) | match |
| 2 | 91.49 with `09-02` as a full ninth control epoch, margin 4.1% | `power-10.9375T-8.23375C…` 91.49, `queda…pct` 4.1 | match |
| 3 | whole 11T/8C 90.2 | `H1C-POWER-REALIZADO` and `power-11T-8C…` 90.2 | match |
| 4 | 11T/9C 96.41 > 95.26, relative MDE 0.996, detectable | `power-11T-9C…` (`detectavel…: true`) | match |
| 5 | spec's own 9-control case 96.4, set aside (`09-02` 0 briefs) | `SPEC-ANALISE` §3 item 3 | match |
| 6 | spec extremes 11T/8C and 11T/7C | `SPEC-ANALISE` §9 | match |
| 7 | whole-window sham 11,812 states, 18 epochs, 53 excluded, `09-01` out | `JANELA-LANCAMENTO.md` relaunch; `ts-janela.txt` 11,865 − `ts-janela-excluidos-53.txt` 53 (52 on 09-21, 1 on 09-06) | match |
| 8 | ties 28 = 10 T + 11 C + 7 outside | C12 artifact | match |
| 9 | 4 / 7 tied H1c opportunities, 0 failures under 3 families; 3 label changes (1/1/1); 25 already `not_failure` | C12 artifact | match |
| 10 | gains 20, losses 28 | C12 `c3` | match |
| 11 | one `created_at` for all 19 designated, 30-day window | `out/expiracao-designados-2026-09-09.json` | match |

## 5. Leftover and hygiene checks

- B title line equals exactly *"A registration that outlived its intervention: a pre-registered
  randomized trial of memory dosing in a production agent fleet"*: **yes**.
- "under-powered by construction": 0 in A. In B it occurs only in changelog 59, which quotes the old
  title. Other "by construction" uses are technical (H1b = 1.0, §3.0.1 heading); none is a title.
- "projection-robust": B l.177 is qualified in the very next sentence (l.178); §9 l.1434 is
  qualified; l.1843 and l.1946 are changelog. No unqualified use.
- Old A numbers (1.18%, 24×, 15.87%, 28.66%, "2, 3, 5", "twelve weeks", "does not respond to
  score", "through 2026-08-31"): 0 left. 131/129/128, 0.0946/1.79×, "beyond rank 100", `b*`,
  "98 s" and 68/269/917 remain only as labelled anchors, in F-5, or as negations ("none places
  them beyond rank 100").
- Host / IP / `/Users` path: none in A. B has none either. B l.1628 contains the generic directory
  `/root/.openclaw`, which predates this round and is neither a host, an IP nor a personal path.

## 6. Defects

| id | where | quote | problem | fix |
|---|---|---|---|---|
| D-A1 | A §4.3.2 l.951-952 | "they fall from pool ranks 1, 5 and 6 to 76–119, with 76–79 candidates from 43–46 distinct source files strictly above them" | The sentence mixes variants. The lower end 76 comes from `prod_noacc`, where only **57** candidates from **24** files are strictly above. 76–79 / 43–46 holds only for `prod_acc0`. Also, 76–119 are stable-sort positions inside a 0.69 tie block (the three score 0.69, as in the 149 table). They are not tie ranges. | "…they fall into a tie at 0.69 below 57–79 candidates from 24–46 distinct source files (stable-sort positions 76–119), against at most 5 slots for that pool" |
| D-A2 | A §4.3.2 l.992 | "but not unique. between 22 and 44 other chunks" | The sentence after the full stop starts lowercase (typo introduced in rc4). | "…not unique. Between 22 and 44 other chunks…" |
| D-A3 | A §5.7.1 l.1506-1508 | "chunks of one `lessons.md` ingestion with identical fields, or entity chunks with the same importance, pain, access count and access instant" | This is true (checked on the extract), but the cited artifact cannot show it: `ties_at_second_with_calculateSalience.shared` lacks `last_accessed_at` and `source_file`. | Add those two fields to the artifact's `shared` (script change, artifact regenerated under a new date), or cite the extract-side check. |
| D-B1 | B §7 "Tie rule" l.1207-1210 (and §4 l.357-359) | "and counted in rc4 it is nil for H1c: … none of the 11 that are H1c opportunities was a failure under the three-family majority" | The rule's bias is "toward fewer failures", which means relative to resolving ties as failure. Against that counterfactual its effect is not nil: 4 tied opportunities in treatment (HT 27.78) and 7 in control (HT 36.73) are held at `not_failure`. To first order (ignoring condition-(i) feedback) the four-vote difference would go from −0.0208 to about −0.027. "No change relative to the three-family labels" is not the same as "no effect on the contrast". | Replace "it is nil for H1c" with the counts and weights, e.g. "it changes no H1c label relative to the three-family majority; against the opposite resolution it holds 4 treatment and 7 control opportunities (HT 27.78 and 36.73) at `not_failure`, not computed as an estimate". Or compute that estimate with `estimador_itt.py`. |
| D-B2 | B working list item 9 l.1694-1696 | "The larger set (the 11,865 states of the trial window, about 36 h) ~~is configured and not run~~ is running as item 15." | The count and ETA are stale. What runs is `job-janela2` on 11,812 states (53 excluded), ETA ≈ 41 h, about 2026-10-07T03:00Z. This contradicts the STATUS block, §4.0.1c, item 15 and B.1. | "…The larger set (11,812 reconstructible states of the trial window) is running as item 15." |
| D-B3 | `B-rc4/parity-rc4.py` l.2, 65-66, 243 | "token: (signed change rc2 -> rc3 … C1..C22)", "unmutated rc3: PASS" | Labels were left over from the rc3 script. The tool compares rc3 → rc4 (variables `RC2`/`RC3` point at rc3/rc4), but its self-test prints "unmutated rc3". This is cosmetic, but it misleads a reader of the log. | Rename the labels to rc3 → rc4 and print "unmutated rc4". |

Not defects (checked): B §1.1 says "a cut the spec does not include" and §4.1.1 says the spec
"computed that case itself (96.4) and set it aside". Both are consistent with `SPEC-ANALISE` §3
item 3 and §9. The "19 served epochs" for the fractional 84.8 (10.94 + 7.23 epoch-equivalents)
is accurate as worded.
