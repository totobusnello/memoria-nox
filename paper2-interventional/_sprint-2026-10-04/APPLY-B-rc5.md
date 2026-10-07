# APPLY — `B-v2-rc4.md` → `B-v2-rc5.md` (Paper B, 2026-10-05)

Source: one Codex regression review of rc4 (exit 0; receipt kept in the local `.remember/`
directory, `adversary-receipt-codex-2026-10-05T073210-97443.txt`, output sha256
`9b62e3f78ab2eff7…`). Five findings; each was checked against the code and artifacts
before applying. All five confirmed; fixes adapted where the proposed wording did not match
what was done (finding 3).
`B-v2-rc4.md` is unchanged (sha256 `32680551e055d620…`, 1,991 lines, 152,035 bytes).
rc5: sha256 `efc04188d3f71d76…`, 2,039 lines, 156,347 bytes.
No git command, no deposit, no contact, no adversarial voice.

## Findings, verification, application

| # | sev | finding | verified against | verdict | where in rc5 |
|---|---|---|---|---|---|
| 1 | HIGH | "would require more than 100%" / "a reduction above 100% is impossible, so … cannot be read as the treatment working" treats proportional dilution as a causal bound | the arithmetic reproduces (70.7/3.14 = 22.5; 47.1/3.14 = 15.0; 70.7/6.85 = 10.3; 47.1/6.85 = 6.9). §4.3 reading 1 (treatment reduces failure **volume**) and §8.3 (carryover through *state*) are in the manuscript and contradict an impossibility claim | **confirmed** | abstract ¶ on H1 and abstract last ¶; §4.0.2 "`H1` rejects under both"; §4.3 (Codex's text, plus pointers to reading 1 and §8.3). `H1` stays an unexplained rejection |
| 2 | MED | estimator definition presents PREREG §4.1 snapshot membership as what is checked | `estimador_itt.py` l.69–72: `primeiro_failure[sig] = e.epoch` (first failure per signature over the corpus); l.88–89: skip if `t0 > e.epoch − EPOCH_H`. `pilot_replay.py` l.34–39: "DECLARED APPROXIMATION … `pruneEpochs(keep=3)` deletes the historical .db files … reconstructed by timestamp" | **confirmed** | §4 "The combined estimator, written out": registered requirement quoted, then the implemented proxy |
| 3 | MED | §4.0.1c "any designation of the same severity and bonus mass" and §7 "establishes specificity" exceed 20 shams; rank is not a calibrated randomization p | see below | **confirmed, wording adapted** | abstract (sham sentence), §4.0.1c "What it shows", §7 "Scope of the specificity control" |
| 4 | MED | §9 "anything less stays out of reach" and §4.1.1 "under-powered for any smaller effect" contradict `mde_relativo_h1c: 0.996` | `REVIEW-B-rc2-evidence/power-11T-9C-whole-epochs.json`: `mde_relativo_h1c` 0.996, `detectavel_no_limite_p1_igual_zero` true | **confirmed** | §4.1.1, §9, B.1 power row: "80% power only for reductions of about 99.6% or more" |
| 5 | LOW | "the first-order value is the same −0.0266" | `out/C12-EMPATES-COMO-FAILURE-2026-10-05.json`: `diferenca_4votos_empate_como_failure` −0.026571; `primeira_ordem.diferenca` −0.026566 | **confirmed** | §4 tie paragraph, B.1 C12 row, changelog 67 (struck "the same", pointer to 73) |

### Finding 3: what was actually done (checked, as asked)

- **Real designation:** one chunk per `p2_verdict` signature group, drawn by a drand-seeded
  rule (`DESIGNATION-SEED-2026-08-26.md`: "Escolher, dentro de cada grupo de assinatura …
  qual chunk recebe o boost … Um por grupo").
- **Shams:** `B-sham-v2/REPORT.md` §2.1, mode `impulsionavel`: 19 drawn from the 36
  boostable non-designated items, stratified 10 S1 + 9 S2 to match the real designation's
  severities, so bonus mass is 0.301·w for every sham; seeds `sha256("p2-sham-v2-2026-10-04|i")`;
  no signature-group constraint.
- So the shams are **matched draws on severity and bonus mass, not draws under the same
  rule**. Codex's premise ("generated differently") is true, and rc4 already said so in the
  third declared limit of §4.0.1c and in §4.0.1b ("a randomization p-value only to the
  extent that the shams are drawn by the same mechanism as the real designation, which
  neither configuration … does").
- **Terminology:** the spec (`SPEC-ANALISE-2026-09-10.md` §5, "Pré-comprometido") defines
  the sham as a *falsification test of specificity* with "19 chunks aleatórios não
  designados, mesmo `w`"; it does not define a randomization p-value. PREREG-DRAFT does not
  mention the sham. The manuscript's own term is "rank p-value", `p = (1 + #{sham ≥ real}) / 21`.
  Codex's fix renamed it "descriptive rank"; rc5 **keeps "rank p-value"** and the `p`
  notation (table header, §7, abstract) and adds that it is not a calibrated randomization
  p-value, pointing to the third limit for the reason. The specificity claim is limited to
  "these 20" matched designations.

## Parity

`B-rc5/parity-rc5.py` (adapted from `B-rc4/parity-rc4.py`: old = rc4, new = rc5; same five
checks; `HEADINGS` empty, no rename; self-test number mutation now on `99.6%`):
**PARITY: PASS**. 22 numeric tokens change count, 22 justified (F1–F5, WL, CHANGELOG),
none unlisted or stale. Headings: 40, identical. Dangling internal § refs 7 → 7, 0 new.
Citation keys unchanged; no footnotes; no host, IP or personal path added. `--self-test`:
3 mutations caught, unmutated rc5 passes. rc4's own parity still passes.

## Style (changed sentences only)

No em dash added (34 in rc4, 34 in rc5). No Tier 1 vocabulary or hedge stacks; the one
softening ("hard to attribute to the altered briefs, not impossible") is the content of
finding 1, not a hedge. Bold kept only on "these 20" in §4.0.1c, where the scope is the point.

## Not changed, and why

- Changelog items 43 and 59–68 that quote the old impossibility wording are history; only
  item 67 is corrected, because Codex asked and the error there is factual.
- The B.1 row "22.5 / 15.0 and 10.3 / 6.9 times total elimination" keeps its label: it
  names arithmetic, and the text now calls it a proportional-dilution calculation.
- The 0.144%/epoch divergence that `pilot_replay.py` declares for the timestamp
  reconstruction is not added to §4: it would be a new number without a B.1 artifact.

## Open for the author

1. Codex's closing note, unchanged by rc5: not ready for deposit until the whole-window sham
   (`job-janela2`, working list 15) is in and working list item 10 (ballast gap) is closed.
2. rc5 has not been reviewed adversarially.
