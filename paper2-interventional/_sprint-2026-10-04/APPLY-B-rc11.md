# APPLY B-rc11: review of rc10 applied (2026-10-05)

Manuscript: `B-v2-rc10.md` copied to `B-v2-rc11.md`; only rc11 was edited. No git, no Zenodo, no
voices, no VPS, no production. Not touched: `estimador_itt.py`, `rerandomizacao.py`, the locked
artifacts (`~/Backups/paper2-ensaio-2026-09-21/`, `~/.paper2-verdicts/`, read-only), v1/v2
artifacts, `B-rc8/`, `B-rc9/`, `B-rc10/` (including `checks-rc10.json`), every figure.

Source: `REVIEW-B-rc10-2026-10-05.md` (Fable HIGH-1, MEDIUM-1/2, LOW-3..6; Codex 1..9). Each
finding was verified against code, artifacts and registration before it was applied. **All 16
hold; none rejected** (Codex 5's first half is Fable HIGH-1).

## Verification, per finding

| finding | verified against | result | applied where |
|---|---|---|---|
| Fable HIGH-1 / Codex 5a — §7 "not attributed as the registration requires" | rc10 §2, §4: switch 6 is on; `checks-rc10.json` `pico_share_tratamento` 0.7409; three sessions 321.43 + 54.00 of 382.01 h | holds | §7 Denominator, Fable's text (74%) |
| Codex 5b — App. A "no registered verdict differs" | abstract l.83 of rc10 already says one verdict differs; v3 `multiplicidade` | holds | App. A, Codex text ("in the registered analysis (v3)" for "in v3") |
| Fable MEDIUM-1 — §9 lesson heading; §9 "the denominator and not the dose" | `estimador_itt_registrado.py` `atribui_ao_inicio` moves `epoch` of every episode of the session, so outcomes move with exposure; rc10 §4 l.702 says so | holds | §9 heading (Fable text); §9 sentence (Fable text, "attributes it to the construction" → "shows it was not robust to the registered rule", per Codex 2) |
| Codex 2 — §4.0.2 "not of the dose" | same | holds | §4.0.2 (Codex text). Swept: abstract ("carried by three long sessions that the denominator split"), §4.2 rc10 correction ("came from a denominator"), §9 ("came from a denominator…", "explained it") rewritten to the non-robustness reading. Headings and the Figure B1 caption title ("came from … split across epochs") kept: they name which construction produced the intervals, not a claim about the dose |
| Fable MEDIUM-2 — H2 intervals exclude zero only under BCa | v3 `H2.registrado`: time winsorized `ic95_percentil` [−0.010681; +0.660535], tokens raw [−389.52; +10 748.39]; BCa [+0.0108; +0.690], [+740; +12 282] | holds | abstract, §5 |
| Fable LOW-3 — four stale strings in the estimator | l.8, l.17, l.20, docstring of `unidades_elegiveis` | holds | script fixed (below) |
| Fable LOW-4 — "leaves the analysis with its 49 episodes" | `checks-rc10.json` S: `1a5d8840` starts 2026-08-27, 49 episodes, touches `09-02`, `09-03`, `09-05`, `09-06`, `09-07` | holds | §4 (Fable text) |
| Fable LOW-5 — expiry cut under start-epoch attribution | `predicado_janela` reads `e.epoch` after `atribui_ao_inicio`, so the cut binds on episodes attributed to `09-20`; S block: latest epoch any crossing session touches is `09-18`, and any session starting before `09-20` with an episode past expiry would be a crossing session | holds | §3.0.1 (Fable text + the `09-18` evidence) |
| Fable LOW-6 — §7 ties under rc10 | `checks-rc10.json` C: 4 / 7 / 9 / 7 / 1 | holds | §7 |
| Codex 1 — census replaced by a sample | `PREREG-DRAFT.md` §3 (Sampling Plan) l.676 *"Live-study adjudication volume and panel — LOCKED 2026-07-30: census, API-only panel"*, l.680 "Subsampling is dominated"; locked corpus 5 951 episodes, 395 `is_error`, 5 556 others; `estrato-b-ids` 800 lines; `ITT-2026-09-21.json` `n_estrato_b_amostrado` 800, `n_resto_no_corpus` 5 556, `peso_estrato_b` 6.945 = 5 556 / 800; not in `DEVIATIONS-FOR-PAPER.md` | holds | §4 (bold "Deviation (rc11)" + Codex text + the PREREG quote, verbatim) and App. A (Codex text as a new item; preface list; "Twelve" → "Thirteen"); working list 25 (author decision pending: 4 756 = 5 556 − 800 episodes) |
| Codex 3 — own stratum "no contrast is estimable" | computed from v3: registered minus 'without' leg per arm: T 321.43 h / 139.96 opp. / 6.00 rep.; C 54.00 / 0 / 0. Δ repeats/h = 6.00/321.43 − 0 = **+0.018667**; Δ opp./h = 139.96/321.43 − 0 = **+0.435429**. Codex's +0.01867 / +0.43543 confirmed | holds | §4, with the source; B.1 |
| Codex 4 — `span_por_sessao` floor | `pilot_replay.py` l.238 `max((max(v) − min(v)).total_seconds() / 3600, PISO_SESSAO_H)`, `PISO_SESSAO_H = 1 / 60` | holds | §4.2 (Codex text) and Figure B1 caption (same class). Codex's 82 T / 52 C floored sessions not stated (not recounted here) |
| Codex 6 — §4.5 "the ITT … is the primary" | `PREREG-DRAFT.md` §5 l.1042 "Mandatory ITT co-estimate. The primary is reported alongside an intention-to-treat estimate…" | holds | §4.5 (Codex text) |
| Codex 7 — §8.1/§8.5 "no cost/latency", "measure cost" | §5 reports time and token regret | holds | §8.1 (Codex text), §8.5 likewise |
| Codex 8 — manifest "every artifact in this table" | `MANIFESTO-LASTRO-P2.json`: `n_artefatos` 50 | holds | App. B row, Codex text (manifest not extended) |
| Codex 9 — "unexecuted abort" | §3.0: "We find no record that the abort ran" | holds | §3.0 (Codex text); App. A preface "the unexecuted safety abort" → "the safety abort without an execution record" |

Further sweep (same classes): status header (rc11 line) and the review caveat ("under review as
of 2026-09-21" → reviews of rc6, rc8, rc10); §5 co-estimates row "outside the four departures" →
"the six switches of §4"; App. A preface "boundary-straddling attribution not computed" → "not
applied until rc10".

## Fable LOW-3: the script

- `measurement/estimador_itt_registrado.py`: l.8 "adds four switches" → six (with what each
  version added); l.17 "all four switches" → six; "THE FOUR SWITCHES" → SIX; the
  `unidades_elegiveis` docstring now names switch 6 (`atribui_ao_inicio`) as the 'with' leg.
  AST identical to rc10's apart from docstrings (checked).
- sha256 `b5135f04…` → **`0aa9202b…`**. Re-run (14 s): every field of v3 identical except
  `gerado_em` and `proveniencia.script.sha256` (field-by-field diff; the text diff is those two
  lines). `out/ITT-REGISTRADO-v3-2026-10-05.json` regenerated: `36f6421a…` → **`41a0a0ee…`**.
- Frozen: `B-registered/estimador_itt_registrado-v3-0aa9202b.py`.
- Kept so the rc10 pins resolve: `B-registered/estimador_itt_registrado-v3-rc10-b5135f04.py` and
  `B-registered/ITT-REGISTRADO-v3-rc10-36f6421a.json` (`checks-rc10.json` and the rc10 figure
  `.run.json` pin `36f6421a`).
- `B-rc10/checks-rc10.py` re-run to scratch against the regenerated v3: passes its guards and
  reproduces `checks-rc10.json` in every block except `sha256_ITT_REGISTRADO_v3`.
- `sprint-figB-h1a-inversao-registrado-v3.py` aborts against the regenerated v3 (its guard
  compares against `checks-rc10.json`'s pin) and, run against the kept rc10 copy, reproduces
  the rc10 SVG byte for byte.
- sha256 updated in: v3 provenance (by the re-run), `B-registered/RESULTADO-v3.md` (table),
  rc11 Appendix B (v3 row) and B.1 (first row).

## Parity

`python3 B-rc11/parity-rc11.py` → **PASS**: 39 hunks, all with an ID; 93 added numeric tokens
(77 from rc10, 6 artifact leaves, 10 derived at run time, 0 literals beyond the date); no
heading renamed; 10 SHAM-JANELA blocks byte-identical to rc10; 1 quote added (PREREG §3,
verbatim); 55 code spans added, all resolving. `--self-test`: **37 mutations (32 of the
manuscript, 5 of the script-integrity inputs), all caught by a content check** (a catch by
"hunk has no ID" alone does not count; each integrity mutation must trip its own specific
check); the unmutated rc11 passes. `B-rc10/parity-rc10.py` still passes against the
regenerated v3. Checks: hunks with IDs; added
numbers justified by rc10, an artifact leaf, a run-time derivation (stratum contrasts, 4 756,
`09-18`, the 3600 of `span_por_sessao`, the PREREG §3 lock date) or a literal; headline strings
from the artifacts (rc10's kept, rc11's added); claim locks 4(a)–(d) kept (H1 rejection needs
"deposited"; never "rejects in the registered analysis"), new **4(e)**: no sentence reads the
switch-6 correction as "not the dose" / "no effect of the dose" (allowed negation: "not that the
dose had no effect"), new **4(f)**: the twelve stale sentences are absent; SHAM-JANELA 10 blocks
byte-identical; quotes verbatim; code spans resolve; **13**: script integrity (running script =
frozen copy = v3 provenance; regenerated v3 = kept rc10 v3 outside `gerado_em` and the script
hash; kept bytes hash to the rc10 pins; no stale string in the script). `--self-test` mutates
rc11 in memory (and the integrity inputs) and requires each mutation to be caught by a content
check.

## Not done (declared)

- Ballast: none of the rc10/rc11 artifacts is in `MANIFESTO-LASTRO-P2.json` (working list 17,
  extended); the manifest was not extended in this step (Codex 8 asked only for its coverage).
- The census (Codex 1): declared, not restored; working list 25, author decision pending.
- `checks-rc10.json` still pins the rc10 v3 bytes (kept in `B-registered/`); not regenerated,
  since `B-rc10/` belongs to rc10.
- Review of rc11 (working list 24).
