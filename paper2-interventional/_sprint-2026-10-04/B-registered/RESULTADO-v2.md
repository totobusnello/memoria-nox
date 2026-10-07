# Paper B — the registered ITT analysis, v2 (2026-10-05): review of rc8, part 1

Answers the four analysis items of the review of rc8
(`_sprint-2026-10-04/REVIEW-B-rc8-2026-10-05.md`): (a) Codex C1, the washout in the
denominator; (b) Codex C2, the registered M10; (c) Fable F4, the promotable set at `w = 4`;
(d) Fable F3, the deposited safety abort. Every finding was checked against the code, the
artifacts and the registration before anything was changed. Nothing here touches
`estimador_itt.py`, the locked artifacts in `~/Backups/paper2-ensaio-2026-09-21/`, git, a
deposit, a voice, the VPS or production. Inputs are read in place, read-only; as in v1 they are
not copied here (the episode corpus and the panel's reasons hold real work content).

| new artifact | sha256 (prefix) | what it is |
|---|---|---|
| `measurement/estimador_itt_registrado.py` | `ac9d2f05…` | v1 + switch 5 + diagnostic leg + both Holm readings |
| `out/ITT-REGISTRADO-v2-2026-10-05.json` | `7ebb61ad…` | the v2 run (v1 file left untouched) |
| `B-registered/estimador_itt_registrado-v1-c28b064f.py` | `c28b064f…` | frozen copy of the v1 script, the sha256 v1's provenance records |
| `B-rc9/checks-rc9.py` · `checks-rc9.json` | `23e4a57c…` (json) | v2 sensitivity legs, per-epoch hours, ratios, BCa ranks, washout and straddling blocks |
| `B-registered/f4_promoviveis_w4.py` · `f4-promoviveis-w4.json` | `e247f225…` (json) | item (c) |
| `B-registered/f3_abort_ex_post.py` · `f3-abort-ex-post.json` | `26da74b0…` (json) | item (d), ex-post part |
| `measurement/sprint-figB-h1a-inversao-registrado-v2.py` · `figures/figB1-h1a-inversao-registrado-v2.*` | — | Figure B1 from v2 (aborting guards) |

None of them is in the ballast manifest yet.

```
python3 measurement/estimador_itt_registrado.py --out out/ITT-REGISTRADO-v2-2026-10-05.json
python3 _sprint-2026-10-04/B-rc9/checks-rc9.py
python3 _sprint-2026-10-04/B-registered/f4_promoviveis_w4.py --out _sprint-2026-10-04/B-registered/f4-promoviveis-w4.json
python3 _sprint-2026-10-04/B-registered/f3_abort_ex_post.py --out _sprint-2026-10-04/B-registered/f3-abort-ex-post.json
```

Re-running the estimator reproduces every field except `gerado_em` (checked on a second run).

## (a) C1 — the washout in the session-hour denominator: **holds; fixed**

**Verified.** `por_epoch` computes `span_por_sessao(eps_an)` before the outcome loop drops
episodes with `offset_h < WASHOUT_H`. The washout therefore left the outcomes and stayed in the
H1/H1a denominator. `estimador_itt.py` does the same, and the v1 control, which rebuilt the
locked files byte for byte, preserved it. PREREG: "first 2 h of each epoch excluded from
analysis" (§2 item 3), "the primary analysis set is all post-washout session-hours" (§2 item 4),
an opportunity is an action "in a session starting after the epoch's 2 h washout" (l.642), "the
denominator is post-washout exposure" (l.644), "Sessions excluded by the washout are excluded
from both sets" (l.1036). Codex's diagnostic numbers reproduce exactly: 1,007 washout episodes in
the registered set; T/C hours 12.56155 / 4.33499 → 10.74711 / 3.24868.

**The fix: switch 5, `washout_in_denominator ∈ {sim, nao}`.** Under `nao` (registered), a
(epoch, session) unit is eligible iff its first episode in that epoch, over the whole corpus, has
offset ≥ 2 h; only eligible units enter `span_por_sessao` and the outcome loop (and H2's
population). The a_past corpus is never cut. On the locked corpus the session rule and the
episode rule select the same set inside the analysis window (0 post-washout episodes in a unit
that started inside the washout; 3 such episodes exist in the corpus, all on 2026-08-27, outside
the window). Removed in the registered set: 1,007 episodes, 638 treatment / 369 control, no
opportunity (the outcomes already excluded them).

**Validation.** With every switch at the old value the script still rebuilds
`ITT-2026-09-21.json` and `RERANDOMIZACAO-2026-09-21.json` byte for byte (exit 2 otherwise).
With switch 5 alone at the old value (`registrado_sem_washout_in_denominator`) it gives back v1's
`resumo.registrado` field for field (exit 3 otherwise): the old value reproduces the locked v1
numbers. `checks-rc9.py` re-runs the legs independently and aborts on any difference.

### v2 against v1 (registered analysis, 19 epochs, BCa, 10,000 replicates, seed 20260921)

| | v1 (rc8: washout in the denominator) | **v2 (rc9: washout out)** |
|---|---|---|
| session-hours T / C | 12.56 / 4.33 | **10.75 / 3.25** |
| opportunities / repeats (weighted) T / C | 1,138.47 / 76.84 · 1,101.75 / 87.72 | unchanged |
| **H1** repeats per session-hour | −14.12 [−22.15; −7.04], p 0.0133 | **−19.85 [−32.69; −9.89], p 0.0302** |
| **H1a** opportunities per session-hour | −163.52 [−282.29; −61.12], p 0.0241 | **−233.20 [−352.07; −80.31], p 0.0168** |
| **H1c** repeats per opportunity | −0.0121 [−0.0445; +0.0125], p 0.434 | unchanged |
| H2 time / tokens (raw p) | 0.831 / 0.684 | unchanged |
| BCa lower bound (H1 / H1a) | 18th / 9th smallest replicate | 6th / 6th (α₁ = 0.00056 / 0.00053) |

### One switch at a time (others at the earlier choice; `deltas_um_a_um`)

| switch on | H1 (Δ) | H1 p | H1a (Δ) | H1a p | H1c (Δ) | H1c p |
|---|---|---|---|---|---|---|
| none (sensitivity analysis) | −14.622 | 0.0127 | −143.92 | 0.0855 | −0.01994 | 0.1603 |
| (1) panel | −14.816 (−0.19) | 0.0126 | −146.57 (−2.6) | 0.0917 | −0.02084 (−0.0009) | 0.1475 |
| (2) window | −15.508 (−0.89) | 0.0058 | −153.50 (−9.6) | 0.0380 | −0.01998 (0.0000) | 0.1649 |
| (3) BCa | −14.622 (0) | 0.0127 | −143.92 (0) | 0.0855 | −0.01994 (0) | 0.1603 |
| (4) 19-epoch set | −13.011 (+1.61) | 0.0403 | −148.72 (−4.8) | 0.0778 | −0.01128 (+0.0087) | 0.4393 |
| **(5) washout out of the denominator** | **−21.952 (−7.33)** | **0.0124** | **−222.26 (−78.3)** | **0.0128** | −0.01994 (0) | 0.1603 |

Registered minus one (`deltas_registrado_menos_um`): without (5) the registered analysis is v1;
without (4) H1c returns to −0.0209 (p 0.152) and H1 to −22.84 (p 0.009); without (2) H1 is
−19.32 (p 0.0397); without (1) H1 −19.55 (p 0.032); without (3) only the intervals change.

**Sensitivity legs (registered v2, `checks-rc9.json` block A).** Pre-committed (partials removed,
10 T / 6 C): H1 −21.30 [−34.94; −9.74]; H1a −219.26 [−349.29; −55.45]; H1c −0.0187 [−0.0596;
+0.0094]. Post-hoc (without `09-14`): H1 −11.63 [−20.31; −3.40]; **H1a −97.85 [−162.77;
−26.43]**, which now excludes zero (v1: [−146.22; +1.95]); H1c −0.0159 [−0.0485; +0.0098].
`09-14` now holds 6.79 h, 63% of treatment exposure; the other 18 epochs 0.25–0.94 h. H1
reductions 73.5% (locked) / 43.1% (post-hoc); dilution ratios 23.4 / 13.7 (3.14%), 16.1 / 9.4
(4.56%), 10.7 / 6.3 (6.85%).

### Multiplicity under both readings (`multiplicidade`, F2's artifact)

| reading | family | v1 | **v2** | sensitivity analysis |
|---|---|---|---|---|
| deposited: H1 primary, alone at α 0.05 | — | p 0.0133, rejects | **p 0.0302, rejects** | 0.0127, rejects |
| deposited: Holm on H1a, H1b, H1c, H2×2 | m = 5 (H1b as p = 1) | H1a adj 0.1205 | **H1a adj 0.0840** | 0.4275 |
| | m = 4 (H1b dropped) | 0.0964 | **0.0672** | 0.342 |
| switch: H1 secondary, Holm with H1a–H1c + H2 | m = 6 | H1 adj 0.0798 | **H1 adj 0.151** (H1a 0.1008) | 0.0762 |
| | m = 5 (H1b dropped) | H1 adj 0.0665 | **H1 adj 0.1208** (H1a 0.084) | 0.0635 |
| switch, H1c tested alone; Holm on H1, H1a, H1b, H2×2 | m = 5 / m = 4 | 0.0665 / 0.0532 | **0.1208 / 0.0906** | 0.0635 / 0.0508 |
| switch: H1c primary, alone | — | p 0.434 | **p 0.434** | 0.1603 |

Nothing in any Holm family rejects in any variant. Under the switch the smallest p is H1a's
(0.0168), above the first threshold (0.0083 with m = 6, 0.01 with m = 5), so the step-down stops
at once. **H1 rejects only under the deposited reading.** Fable's v1 numbers (0.0798; 0.0665)
reproduce in the v1-equivalent leg.

### Found while verifying C1, not in the review: boundary-straddling sessions

PREREG §2 item 3 assigns sessions that cross an epoch boundary to the epoch of their **start**,
flagged, with a with/without sensitivity. The estimator keys sessions by the epoch of each
episode, so a long session contributes exposure to every epoch it touches. Six sessions in the
corpus have episodes in more than one epoch; four touch the window. One of them, `d37a5964`
(started 2026-09-08 20:14Z, 60 episodes over 11 epochs), makes 6.33 of `09-14`'s 6.79 h.

The registered "with" leg (attribution to the start epoch) is **not implemented** (it changes the
arm of those episodes; author decision, working list 22 of rc9). The "without" leg is computed as
a diagnostic (`diag_registrado_sem_sessoes_atravessadas`: every unit of a session with episodes
in more than one epoch is dropped):

| | registered v2 | **without straddling sessions** |
|---|---|---|
| hours T / C | 10.75 / 3.25 | 3.52 / 3.06 |
| H1 | −19.85 [−32.69; −9.89], p 0.0302 | **−7.40 [−16.33; +1.64], p 0.1957** |
| H1a | −233.20 [−352.07; −80.31], p 0.0168 | **−51.12 [−115.60; +22.07], p 0.1501** |
| H1c | −0.0121 [−0.0445; +0.0125], p 0.434 | −0.0109 [−0.0425; +0.0137], p 0.4571 |

On the registered "without" leg neither H1 nor H1a excludes zero, and H1's test does not reject.
rc9 reports this in §5, §4.2, §4.3 and Appendix A as a diagnostic, not as a verdict.

## (b) C2 — the registered M10: **holds; not computable from the locked inputs**

**Verified.** `cobertura_e_m10.py` correlates the arm with the share of served briefs that contain
a designated item (`ids_tratado`/`ids_controle` against `DESIGNATION`), over 19 epochs. PREREG §5
(l.1028–1036) registers a different quantity: per epoch, the share of sessions starting in it
(post-washout) that have a `brief_log` row with non-null `brief_id`, the denominator taken from the
session corpus; M10 is the arm × coverage correlation with its interval, the TOST at |r| ≤ 0.15
evaluated only at K ≥ 30. SPEC §2 and §9.1 keep the session definition. So +0.1130 is not M10.

**Why the registered M10 cannot be computed here, exactly:**
1. `brief_log` is not among the locked inputs: `~/Backups/paper2-ensaio-2026-09-21/` holds the
   episode corpus, `p2-serving.ndjson`, `gatilhos.ndjson` and the panel batches (the verdicts are
   in `~/.paper2-verdicts/`), but no `brief_log` export.
2. Even in production the table cannot answer "∃ brief_log row **for s**": its schema
   (`serving-brief.ts` `ensureBriefLog`) is `id, chunk_id, scope, agent, served_at, brief_id`, with
   no session column. `concentracao-de-oportunidades.py` recorded the same on 2026-08-30
   ("`brief_log` não tem `session_id` — só `agent` e `served_at`").
3. `p2-serving.ndjson` (19,572 rows) carries `agent` and `ts` and neither a session id nor a
   `brief_id`; the episode corpus labels agents differently (`agents-boris`, `subagents`,
   `-root--openclaw-workspace`, …). Linking a session to "its" brief would need an agent-and-time
   matching rule that was never registered: a new estimator, defined after unblinding.

Therefore not computed: the registered M10 correlation and interval, its TOST (unevaluable at
K = 19 anyway), and the 95%-logging-coverage analysis set (same quantity). rc9 renames §4.6
"Exploratory arm–designated-item-presence correlation", states the above, and lists both in §5
and Appendix A.

## (c) F4 — the promotable set at `w = 4`: **holds; computed — the condition is not met at `w = 4`**

**Verified.** `CONCENTRATION-2026-08-30.json` lists `assinaturas_promovidas_sob_w2`;
`concentracao-de-oportunidades.py` takes the set as input. Epoch 1 (`09-01`) was served at
`w = 4`.

**Derivation (same definitions).** The list had no saved derivation. A signature is promotable at
`w` iff its designated item (`DESIGNATION-2026-08-26.json`) is in `would_enter` in ≥ 1 of the 350
states of `out/dose-350-v3.json` (the calibration replay whose `w = 2` row the planning script
reads for its denominator). Guard: at `w = 2` this returns the artifact's seven exactly (abort
otherwise). Sets by dose: 3 (w 0.5), 5 (1), **7 (2)**, **10 (4)**, 12 (≥ 7.5). `w = 4` adds
`Read|arquivo:doc`, `Read|arquivo:outro`, `ToolSearch|consulta`.

**Planning corpus** (from the artifact's per-signature totals; the 1,843-episode live archive is
not available): `w = 2` 611/1,526 = 40.0% (reproduced); `w = 4` 677/1,526 = **44.4%**.

**Epoch 1 (rule of `concentracao-de-oportunidades.py`; readings of checks-rc8 block D):**

| reading | `w = 2` (rc8) | **`w = 4`** | threshold 36.7% at `w = 4` |
|---|---|---|---|
| whole epoch | 45/139 = 32.4% [25.2; 40.5] | **52/139 = 37.4% [29.8; 45.7]** | above |
| `active` phase | 34/101 = 33.7% | **41/101 = 40.6%** | above |
| after the 2 h washout | 30/75 = 40.0% | **36/75 = 48.0%** | above |
| trial's weighted rule | 54.5% | **65.1%** | above |

Under the set reachable at the served dose the §3-bis condition is **not met** on any reading;
under the planning (`w = 2`) definition it is met on two. Both Wilson intervals contain 36.7%.
§3-bis does not say which set defines coverage (it was written before the assignment; its
coverage is the planning artifact's). rc9 reports both and does not choose.

## (d) F3 — was the deposited safety abort evaluated at the 20 boundaries? **No record that it was.**

PREREG l.804-806: a script in the frozen commit evaluates an arm-blind rule at every epoch
boundary over the incident stream; halt on ≥ 1 S4 in an analyzed epoch, or ≥ S3 count over 3
epochs > 3× baseline (baseline zero, PREREG §3).

What exists (searched: this repo, `nox-workspace`, the infrastructure repo, `~/Backups`; no VPS):

| evidence | what it says |
|---|---|
| `nox-workspace` PR #46, `tools/nox-mem/src/paper2/abort-check{,-cli}.ts` | the script exists; the CLI "NAO agenda a si mesmo"; exit 0 / 3 HALT / 4 gate not met; writes `p2-abort.ndjson` |
| `DEPLOY-C2-C3-2026-08-21.md` | component 3 deployed **dormant**: "nada importa nem agenda"; `cron com "abort": 0 entradas` |
| `SHADOW-ARMED-2026-08-21.md` | the one recorded run: `exit 4`, 7 days of history against the 14-day gate, **refused to evaluate** |
| `LAMBDA-RESULTS-2026-08-21.md` | zero S3/S4 in 870 calls; "o abort-check medirá contra baseline zero" (future tense) |
| infra `cron/history/crontab-2026-08-23-*.txt`, `crontab-2026-08-31-reconciliado.txt` | `p2-` lines (composição, saturação, designados, corpus-alinhado, restart) and **no abort entry** |
| infra `runbooks/crontab-canonical.md`, 2026-09-09 | the seven live `p2-` lines inventoried; **no abort-check** among them |
| locked `gatilhos.ndjson` (1,833 rows) | tags composição/designados/corpus_alinhado/heartbeat/coorte/saturação/restart; **no abort tag** |
| `p2-abort.ndjson` | not found anywhere locally; it would live on the production host, not inspected |

**Ex post** (`f3_abort_ex_post.py`; NOT the registered evaluation — it sees only the adjudicated
episodes, not the incident stream, and it is not at the boundaries): window 09-01..09-20,
substitution panel 696 adjudicated episodes (3 families: 686). Panel-majority ≥ S3: **0**; ≥ S4:
**0**; at least one panelist ≥ S3: 10, ≥ S4: 1. Clause (a) would not fire; clause (b), baseline
zero, max 3-epoch count 0, would not fire.

rc9 states the deposited horizon ("No interim analyses; no optional stopping"), the abort and the
absence of any record in §3.0, declares the non-evaluation in Appendix A, and keeps the Epoch-1
stop as a deviation from the undeposited revision that is consistent with the deposit.

## Side effect to know

`B-rc8/checks-rc8.py` no longer runs against the v2 script: it stops with `KeyError:
'v1_registrado'` (the new input is not in v1's provenance), and its next guard, which pins v1's
script sha256, would abort it anyway. To re-run it, point it at the frozen v1 copy
(`B-registered/estimador_itt_registrado-v1-c28b064f.py`) under the original module name.
