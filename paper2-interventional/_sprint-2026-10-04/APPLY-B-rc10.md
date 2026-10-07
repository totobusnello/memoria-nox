# APPLY B-rc10: sessions in the epoch of their start (2026-10-05)

Manuscript: `B-v2-rc9.md` copied to `B-v2-rc10.md`; only rc10 was edited. No git, no Zenodo, no
voices, no VPS, no production. Not touched: `estimador_itt.py`, `rerandomizacao.py`, the locked
artifacts (`~/Backups/paper2-ensaio-2026-09-21/`, `~/.paper2-verdicts/`, read-only),
`out/ITT-REGISTRADO-2026-10-05.json` (v1), `out/ITT-REGISTRADO-v2-2026-10-05.json` (v2), `B-rc8/`,
`B-rc9/`, the rc9, rc8 and rc4 figures.

Instruction: the author decided that the analysis reported is the registered one, so PREREG §2
item 3 applies: a session is attributed to the epoch of its start, flagged, with a with/without
sensitivity; sessions longer than one epoch are their own stratum. Analysis part:
`B-registered/RESULTADO-v3.md`.

## Evidence produced for rc10

| artifact | role |
|---|---|
| `measurement/estimador_itt_registrado.py` (sha256 `b5135f04…`) | switch 6 `sessao_ao_epoch_de_inicio` (on in the registered analysis); registered 'without' leg `sens_registrado_sem_sessoes_atravessadas`; rc8- and rc9-equivalent legs with both Holm readings; controls: all switches off rebuild the locked files byte for byte, switch 6 off gives v2 field for field (and v2's diagnostic leg), switches 5 and 6 off give v1 field for field |
| `out/ITT-REGISTRADO-v3-2026-10-05.json` (`36f6421a…`) | the registered analysis reported in rc10; reproduces apart from `gerado_em` |
| `B-registered/estimador_itt_registrado-v2-ac9d2f05.py` | frozen v2 script, so v2's provenance still resolves |
| `B-rc10/checks-rc10.py` → `checks-rc10.json` (`b774e61c…`) | v3 sensitivity legs, hours per epoch, ratios, identity, BCa ranks (A); washout removals (W); straddling sessions with start epoch, arm, span (S); four-vote ties under v3 (C); guards G reproduce v3 (four legs) and v2 |
| `measurement/sprint-figB-h1a-inversao-registrado-v3.py` → `figures/figB1-h1a-inversao-registrado-v3.{svg,png,run.json}` | Figure B1 from v3; panel (a) attributes each session to its start epoch; aborts unless it reproduces v3 hours and every epoch of `checks-rc10.json`, panel (b) matches v3 and the artifact is the six-switch one |

None of these is in the ballast manifest (working list 17 extended).

## v3 against v2 (what rc10 reports)

| | v2 (rc9) | **v3 (rc10, registered)** | v3 without boundary-crossing sessions |
|---|---|---|---|
| H1 | −19.85 [−32.69; −9.89], p 0.0302 | **−1.27 [−28.15; +23.50], p 0.3294** | −7.40 [−16.33; +1.64], p 0.1957 |
| H1a | −233.20 [−352.07; −80.31], p 0.0168 | **−15.22 [−372.20; +314.65], p 0.2599** | −51.12 [−115.60; +22.07], p 0.1501 |
| H1c | −0.0121 [−0.0445; +0.0125], p 0.434 | **−0.0140 [−0.0464; +0.0110], p 0.4006** | −0.0109 [−0.0425; +0.0137], p 0.4571 |
| deposited: H1 alone | rejects | **does not reject** | does not reject |
| deposited Holm (H1a, m = 5 / 4) | 0.0840 / 0.0672 | **1.0 / 1.0** | 0.7505 / 0.6004 |
| switch Holm (H1, m = 6 / 5) | 0.151 / 0.1208 | **1.0 / 1.0** | 0.9785 / 0.7828 |
| switch, H1c alone (H1, m = 5 / 4) | 0.1208 / 0.0906 | **1.0 / 1.0** | 0.7828 / 0.6004 |
| session-hours T / C | 10.75 / 3.25 | 324.95 / 57.06 | 3.52 / 3.06 |

## Changes, by place

| place | change |
|---|---|
| status header | rc10 line |
| abstract | registered H1 under both readings; the earlier rejection attributed to split sessions; H1c numbers (−0.0140, 0.0663/0.0803, p 0.4006, 17%); the H1/H1a parenthetical paragraphs struck and replaced with "corrected in rc10" text; H2's two intervals named |
| §1 table and text | H1 / H1a rows; both readings and both Holm families under v3; earlier rejections kept as rc8 / rc9 / sensitivity values |
| §2 | new paragraph "Sessions that cross an epoch boundary" with the PREREG §2 quote (verbatim, checked) |
| §4 (method) | six switches; control against v2 and v1; new paragraph "Sessions in the epoch of their start (rc10)": rule, the three long sessions, the own stratum (321.43 h / 139.96 opp. / 6.00 rep. T; 54.00 h / 0 / 0 C), one-switch and registered-minus-one deltas, the 'without' leg; washout count under v3 (972); epoch-set delta under v3; four-vote ties under v3; BCa now extreme at the upper quantiles |
| §4.0.2 | table and text under v3; the rc9 H1a paragraph struck with a note; the H1 "unexplained rejection" paragraph replaced |
| §4.1, §4.1.1, §4.1.2 | H1c rows (registered legs, 'without', rc9 row); distance 0.0339; CI and 17% |
| §4.2 | heading renamed; rc9 correction struck; rc10 correction; table with v3, 'without', rc9, rc8, sensitivity rows; the denominator paragraph rewritten for start-epoch attribution; take-away rewritten; Figure B1 regenerated and caption rewritten |
| §4.3 | heading renamed; v3 result first; rc9 result struck and kept as history; identity error 3.8×10⁻⁶; the volume and dilution arguments relabelled as rc9's |
| §5 | straddling row: now reportable, with/without numbers; H2 table under v3, rc9 values in a note |
| §7, §8.3, §9 | ties under v3; opportunities per epoch 109.5 / 135.0; H1 statements; the lesson paragraph rewritten |
| Appendix A | primary-outcome item, registered-analysis item, straddling item struck |
| Appendix B, B.1 | v3, checks-rc10, figure v3 rows; v2 row relabelled; B.1 numbers |
| working list | 17 extended; 22 struck and closed; 23 (review of rc10) added |
| changelog | items 119–124 |

## Checks

- **Claim lock**: rule 4(b) of rc9 kept (no H1 rejection without "deposited"); new rule 4(c): no
  sentence presents H1 as rejecting in "the registered analysis" unless it places the rejection
  in the sensitivity analysis or an earlier version.
- **v2 numbers** (−19.85, −233.20, 0.0302, 0.0168, 0.0840/0.0672, 0.151/0.1208, 10.75/3.25,
  6.79 h, 63%, 73.5%, 23.4…) remain only where labelled rc9 / "rc9's analysis" or struck.
- **SHAM-JANELA**: 10 blocks, byte-identical to rc9.

## Parity

`python3 B-rc10/parity-rc10.py` → **PASS**: 84 hunks, all with an ID; 399 added numeric tokens,
each justified by rc9 (163), an artifact read at run time (235, all from `ITT-REGISTRADO-v3` or
`checks-rc10`) or a literal with its source (1: 321.43 = 240.42 + 81.01); headline strings
formatted from v3 present; 2 heading renames (§4.2, §4.3); 10 SHAM blocks identical; one quote
added (PREREG §2, verbatim); claim lock 4(b) and new 4(c). `--self-test`: 22 mutations, all
caught by a content check (a catch by "hunk has no ID" alone no longer counts); the unmutated
rc10 passes.

## Not done (declared)

- Ballast: none of the rc10 artifacts is in `MANIFESTO-LASTRO-P2.json` (working list 17).
- `B-rc9/checks-rc9.py` no longer runs against the v3 script (`KeyError: 'v2_registrado'`, and
  it pins v2's script hash); re-run it against the frozen v2 copy. Same for `checks-rc8.py` / v1.
- Review of rc9 (working list 21) and of rc10 (working list 23).
- The own stratum has no within-stratum contrast (two treatment sessions, one control); it is
  listed, not estimated.
