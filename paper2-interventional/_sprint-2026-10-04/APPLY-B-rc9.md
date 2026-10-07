# APPLY B-rc9: review of rc8 applied (2026-10-05)

Manuscript: `B-v2-rc8.md` copied to `B-v2-rc9.md`; only rc9 was edited. No git, no Zenodo, no
voices, no VPS, no production. Not touched: `estimador_itt.py`, `rerandomizacao.py`, the locked
artifacts (`~/Backups/paper2-ensaio-2026-09-21/`, `~/.paper2-verdicts/`, read-only),
`out/ITT-REGISTRADO-2026-10-05.json` (v1), `B-rc8/`, the rc8 and rc4 figures.

Review: `REVIEW-B-rc8-2026-10-05.md` (Codex C1–C5, Fable F1–F7; both NO-GO). Analysis part:
`B-registered/RESULTADO-v2.md`. Every finding was checked against code, artifacts and
registration before it was applied; none was rejected, two were applied in a form that differs
from the reviewer's suggested text because the verification changed the answer (F4, F6).

## Evidence produced for rc9

| artifact | role |
|---|---|
| `measurement/estimador_itt_registrado.py` (sha256 `ac9d2f05…`) | switch 5 `washout_in_denominator`; diagnostic leg without boundary-straddling sessions; Holm under both readings; control: switches off rebuild the locked files byte for byte, switch 5 alone off gives v1 field for field |
| `out/ITT-REGISTRADO-v2-2026-10-05.json` (`7ebb61ad…`) | the registered analysis reported in rc9 (v1 file kept) |
| `B-registered/estimador_itt_registrado-v1-c28b064f.py` | frozen v1 script, so v1's provenance still resolves |
| `B-rc9/checks-rc9.py` → `checks-rc9.json` | v2 sensitivity legs, hours per epoch, ratios, BCa ranks (A); washout removals and `09-14` sessions (W); straddling sessions (S); guards G reproduce v2 and v1 |
| `B-registered/f4_promoviveis_w4.py` → `f4-promoviveis-w4.json` | promotable sets per `w`; Epoch-1 coverage at `w = 2` (reproduces rc8 block D) and `w = 4` |
| `B-registered/f3_abort_ex_post.py` → `f3-abort-ex-post.json` | safety abort evaluated ex post over adjudicated episodes |
| `measurement/sprint-figB-h1a-inversao-registrado-v2.py` → `figures/figB1-h1a-inversao-registrado-v2.{svg,png,run.json}` | Figure B1 from v2; aborts unless panel (a) reproduces v2 hours and every epoch of `checks-rc9.json`, panel (b) matches v2 and the artifact is the five-switch one |

None of these is in the ballast manifest (working list 17 extended).

## Findings

| # | verified? | what the check found | applied where |
|---|---|---|---|
| **C1** washout in the denominator | **holds** | `span_por_sessao(eps_an)` runs before the `offset_h < WASHOUT_H` filter; PREREG §2 items 3–4, l.642/644/1036 make the denominator post-washout; Codex's 1,007 episodes and 12.56155/4.33499 → 10.74711/3.24868 reproduce exactly | switch 5; v2 numbers in abstract, §2 (Washout), §4 (estimator, new paragraph "The washout in the denominator"), Uncertainty (BCa ranks), §4.0.2 table and text, §4.1 sources, §4.2 (heading, rc9 correction, table with an rc8 row, denominator paragraph, take-away), Figure B1 regenerated, §4.3 (H1, legs, hours, reductions 73.5%/43.1%, ratios), §5 H2 source, §7, App. A, App. B, B.1 |
| **C2** M10 measures the wrong quantity | **holds** | `cobertura_e_m10.py` correlates arm with designated-item presence among served briefs; PREREG §5 coverage is session-level `brief_log` coverage. Registered M10 **not computable**: no `brief_log` in the locked inputs, and the table has no session column (`serving-brief.ts`); a session ↔ brief link would need an unregistered agent-and-time rule | §4.6 renamed "Exploratory arm–designated-item-presence correlation" with the reviewer's opening, adapted; §3 table; §4.1.2; §5 (M10 row, 95%-coverage set row); App. A bullet; App. B and B.1 labels; working list 13 annotated |
| **C3** substitution rule attributed to the deposit | **holds** | PREREG l.695: "Mitigation, not adopted here … seat a fourth API family"; the substitute-only rule is DEVIATIONS §10.31 | abstract (reviewer's sentence, extended with the washout); §6 item 7 |
| **C4 + F1** chronology | **holds** | commit `3e1c259` (21:56:42Z, 2026-08-30) retracts the declared rule before Epoch 1 and appends the RETRACTION section to `ASSIGN-SEED-2026-08-30.md` | abstract (F1's text, with the C4 framing); §1 (retraction section named); §7; §9 ("we report both here for the first time"); App. A |
| **C5** stopping disclosure exceeds evidence | **holds** | "was not evaluated" is unprovable; "not biased since never applied" overreaches | App. A (reviewer's wording, plus F4); §7 (reviewer's two sentences) |
| **F2** H1's rejection is a hybrid of readings | **holds** | under the switch H1 is secondary; Holm m = 6 / 5 does not reject. Artifact added (`multiplicidade.*.leitura_depositada` / `leitura_da_troca`). v1: 0.0798 / 0.0665 reproduce; **v2: 0.151 / 0.1208** | abstract; §1 table and new paragraph; §1.1; §4.0.2 table H1 row and text; §4.3; §9; App. A; parity check 4(b) |
| **F3** deposited stop/abort not mentioned | **holds** | PREREG l.795 (fixed horizon, no optional stopping), l.804-806 (abort). **No record that the abort ran**: deployed dormant 2026-08-21, one run exit 4 (gate), no cron entry in the 08-23 / 08-31 snapshots nor the 09-09 inventory, no abort tag in `gatilhos.ndjson`, its log not local. Ex post: 0 panel-majority S3/S4 among 696 adjudicated | §3.0 new opening paragraph and close (deposit vs undeposited revision); §7; App. A new bullet |
| **F4** "condition was met" uses the `w = 2` set | **holds, and changes the answer** | the derivation from `dose-350-v3.json` reproduces the seven at `w = 2` and gives ten at `w = 4`; Epoch-1 coverage at `w = 4` is **37.4%** (52/139, Wilson [29.8; 45.7]), above 36.7%, and every other reading is above too. Rather than Fable's "we have not computed", rc9 reports both definitions and does not choose | abstract; §1.1; §3.0 (new paragraph, qualified heading and conclusion); §7; §8.2 row; §9; App. A; B.1 |
| **F5** the declaration's failure clause | **holds** | ASSIGN-SEED l.100-102 and l.152-153, quoted verbatim | §1 (appended); App. A |
| **F6** 0.0335 vs 0.0336 | **partly** | the paper's 0.0335 is right from unrounded values (−0.056038 + 0.089552 = 0.033514); 0.0336 comes from the rounded values shown | §4.1.1: both stated, with the unrounded inputs |
| **F7** "hours after" vs 24 min 38 s | **holds** | RETRACTION: "Filed 2026-08-30, hours after the round was consumed"; commit 24 min 38 s after emission | §1, cited with the discrepancy |

**Found while verifying C1 (not in the review): boundary-straddling sessions.** PREREG §2 item 3
attributes a session that crosses an epoch boundary to its start epoch, flagged, with a
with/without sensitivity; the estimator does not. Four sessions in the window cross a boundary;
one (`d37a5964`, started 09-08) makes 6.33 of `09-14`'s 6.79 h. The "without" leg, computed as a
diagnostic, has H1 −7.40 [−16.33; +1.64] (p 0.1957) and H1a −51.12 [−115.60; +22.07]: both
contain zero. rc9 reports it in §4.2, §4.3, §5 (new row), App. A, abstract; the registered
"with" leg is left to the author (working list 22). **This is the item most likely to change how
H1 reads; it needs a decision.**

## Sweep, by class, over the whole manuscript (outside struck text and the historical changelog)

- **H1 rejects**: every sentence presenting H1 as rejecting now carries "deposited" (parity check
  4(b), mechanical; plus §4.3's last "unexplained rejection" and the §1.1 reader note).
- **"was met"**: every stopping-condition statement carries the planning qualifier (check 4(c));
  rc8's correction label qualified ("rc8, qualified in rc9").
- **v1 numbers**: 0.0133, 0.0241, 0.1205, 0.0964, 12.56/4.33, 163.52, 69.8%, 44.6%, 22.2, 15.3,
  6.5, 7.13 h, 57%, 0.97 h, 9th/18th, 0.543/0.541, 74/65/56 remain only where explicitly labelled
  rc8 / "with the washout in" (§4 paragraph, §4.2 rc8 row, B.1 rc8 row) or struck.
- **M10**: outside §4.6's explicit "registered M10" statements and file/field names, the
  correlation is called the designated-presence correlation.
- **SHAM-JANELA**: 10 blocks, byte-identical to rc8.

## Parity

`python3 B-rc9/parity-rc9.py` → **PASS**: 96 hunks, all with an ID; 357 added numeric tokens,
each justified by rc8, an artifact read at run time, or a literal with its source
(`--report`); 2 heading renames (§4.2, §4.6); 10 SHAM blocks identical; new claim check 4(b)
(no H1 rejection without "deposited") and 4(c). `--self-test`: 21 mutations, all caught; the
unmutated rc9 passes.

## Not done (declared)

- Ballast: none of the rc9 artifacts is in `MANIFESTO-LASTRO-P2.json` (working list 17).
- `B-rc8/checks-rc8.py` no longer runs against the v2 script (`KeyError: 'v1_registrado'`, and it
  pins v1's script hash); re-run it against the frozen v1 copy.
- The registered "with" leg for straddling sessions (working list 22).
- Review of rc9 (working list 21).
