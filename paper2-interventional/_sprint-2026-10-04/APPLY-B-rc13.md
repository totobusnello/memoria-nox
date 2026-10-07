# APPLY B-rc13: the Fable review of rc12, and the personal paths in `B-censo/` (2026-10-05)

Manuscript: `B-v2-rc12.md` copied to `B-v2-rc13.md`; only rc13 was edited (rc12 unchanged).
Also edited, as authorized: one sentence of `B-registered/RESULTADO-v3.md` (LOW-4) and the
path lines of four scripts in `B-censo/`, with `SHA256SUMS` and `census-pins.sha256`
regenerated. No git, no Zenodo, no voices, no VPS, no API calls. No episode text, panelist
reason or credential was read into the manuscript or this file.

Source: `REVIEW-B-rc12-2026-10-05.md` (Fable, single full read, NO-GO; Codex not run).

## Findings: verified, then applied

| finding | verified against | holds? | applied |
|---|---|---|---|
| MEDIUM-1, census missing from "two commitments" | `PREREG-DRAFT.md` l.676 (§3 Sampling Plan): *Live-study adjudication volume and panel — LOCKED 2026-07-30: census, API-only panel*, i.e. a month before the seed (2026-08-30), in the deposited v1.12; the stopping rule (`PROSPECTIVE-ESTIMAND`) and the seed declaration's rule are undeposited (rc12 §1, App. A). The abstract and §9 said "two"; the abstract had no census and no attempt | yes | Abstract: "Three commitments…", "The other" → "The second", and the reviewer's third-commitment sentences (wording: "a test-retest gate declared before its first call" instead of "pre-declared", since the rules postdate unblinding). §9: reviewer's text, with the assignment-rule clause recast to fit the list |
| MEDIUM-2, "two layers of randomness" | §4.1.2; `gate2-compare.json`: 4 panel-outcome changes, two `failure` ↔ `not_failure` in opposite directions (`not_failure`→`failure`, `failure`→`not_failure`), two with `unknown`; the bootstrap resamples epochs with labels fixed | yes, with one correction | Reviewer's text, except "each such flip moves the weighted repeat count by 6.945": a flip moves the weighted **failure** count by 6.945, and the repeat count only if the episode is a repeat. Written "moves any weighted count it enters (failures, and repeats where the episode is one) by 6.945". The closing sentence "The first … the second" was re-pointed (frozen sample; hash order; panel variation). Swept: the abstract's uncertainty sentence ("does not re-draw the stratum-B sample") now also says the bootstrap does not re-adjudicate. §4.1.1 has no layer count |
| LOW-1, header time | rules file l.3 *Written 2026-10-05T23:15Z*; `GATES.md` l.6 repeats "(23:15Z)" and l.21 dates gate 1 from 23:14:52Z; `raw/gate1-calls.jsonl` call starts 23:14:49Z, 23:14:52Z, 23:14:55Z | yes | Reviewer's text, plus one sentence: `GATES.md` dates gate 1 from 23:14:52Z, the start of the second call |
| LOW-2, declared noise property | rules file l.66 (99/100, Wilson [0.9455; 0.9982]) and l.74-78 (0.99^150 ≈ 22%, "can fail on noise alone", Wilson reported for that reason); 1 − 0.99^150 = 0.7785; point estimates 47/50 = 0.94 and 46/50 = 0.92 < 0.9455 | yes | Reviewer's text, made exact: the 150 pairs are all three families together (each provider has 50), and "fails … about 78% of the time" holds *if each pair truly agreed with probability 0.99* |
| LOW-3, "drifted" | §7; `GATES.md` gate-1 caveat (an id is an alias, no fingerprint) | yes | Reviewer's text, plus "and no interval includes that variation (§4.1.2)". Sweep: no other "drift" in the body (before the working list); the rc12 changelog item 138 is history and stays |
| LOW-4, `RESULTADO-v3.md` "no within-stratum contrast is estimable" | manuscript §4 reports +0.01867 and +0.43543 per hour (descriptive, no interval, H1c not contrastable) since rc11 | yes | Sentence corrected in `RESULTADO-v3.md`, dated, old text quoted, "no number changed". No sha256 of that file is recorded anywhere (searched the repository for the prefix `f3c73483`), so the edit breaks no record; parity pins the pre-rc13 bytes and checks that reverting the sentence gives them back. Appendix B row annotated |
| LOW-5, "Thirteen" | Appendix A list: 13 bullets, one struck since rc10 (boundary-straddling) → 12 live; "Twelve" in rc10 also counted the struck item; rc11 added the census item | yes | "~~Thirteen~~ Twelve (the struck item below is no longer a deviation)"; parity counts the unstruck items |

Nothing rejected.

## `B-censo/`: personal paths removed

| file | line(s) before → after |
|---|---|
| `census_tools.py`, `gate_harness.py` | `P2 = Path("<absolute>")` → `P2 = Path(__file__).resolve().parents[2]` |
| `compare_gate2.py` | `sys.path.insert(0, "<absolute>")` → `sys.path.insert(0, str(Path(__file__).resolve().parents[2]))` |
| `run_census.sh` | `B=<absolute>` / `R=<absolute>` → `B=$(cd "$(dirname "$0")" && pwd)` / `R=$(cd "$B/../.." && pwd)` |

`grep -rn "/Users/" B-censo --exclude-dir=raw` is empty. A `B-censo/__pycache__/` that my own
import test created (20:40) held the absolute path in bytecode and was removed; it is gitignored,
and parity skips `__pycache__/`.

Behaviour, old (copies of the rc12 bytes in the session scratchpad) against new, no API:
- `compare_gate2.py`, run in scratch trees: both write `gate2-compare.json` byte-identical to the
  registered one (`48e9fdb6…`).
- `census_tools.py`: `--help`, `cost` on `raw/gate1-calls.jsonl` and `raw/gate2-calls.jsonl`
  (TOTAL 0.0234 and 1.1552, equal to `raw/cost-gate1.json` / `cost-gate2.json`), `floorless`
  and `retry-sets` on the gate-2 verdicts (into scratch), `secret-scan` exit code: outputs
  identical, old vs new.
- `gate_harness.py`: `--help` identical; `verify_pins()` passes; `P2` resolves to the same
  directory.
- `run_census.sh`, with `HOME` pointed at a scratch directory (so nothing is written under the
  real `~/.paper2-verdicts/`): no `CENSUS_AUTHORIZED` → exit 3; no override → exit 3 (GATES.md
  is FAIL); override with an empty scratch batch directory → exit 4 `PIN MISMATCH (lotes)`,
  which is reached only after `cd "$B"` and a passing `census-pins.sha256`. Same codes old and
  new; also when invoked as `./run_census.sh` from `B-censo/`. `B` and `R` evaluate to the old
  literals. The real census directory still holds only its 48 batches.

Hashes: `census_tools.py` `6f6f9a6d…` → `5f6496b5…`, `gate_harness.py` `3b0a1d4b…` →
`5e81769d…`, `compare_gate2.py` `ba8527c8…` → `2c03b3da…`, `run_census.sh` `97bcaa8a…` →
`3e5748fc…`, `census-pins.sha256` `f8b21d16…` → `a190eae2…`; both sum files verify.
**Not changed: `GATES.md`**, which records `3b0a1d4b…` and `6f6f9a6d…` as the bytes that ran
the gates. Those records stay true of what ran; parity-rc13 check 15(c) proves that each
current script, with its path line put back, has exactly its gate-time sha256 (the path is not
written in the parity script; its sha256 is pinned, and on another checkout the bridge is a
WARN). rc13 Appendix B says this. The manuscript printed no hash of these four files.

## Parity

`python3 B-rc13/parity-rc13.py` → **PASS** (see the run below). 18 hunks, all with an ID (ST,
UNC, COMMIT, CENSUS, LAYERS, REPRO, APPA, APPB, B1, CL). 48 numeric tokens added: 21 from rc12,
23 derived at run time (second call, rules' Wilson bounds and pair count, 0.99^150 and its
complement, the number of panel-outcome changes, the HT weight 5 556 / 800, plus rc12's
census derivations), 3 from `gate2-compare.json`, 1 declared context. CENSUS, LAYERS and B1 are
strict: rc12 alone does not justify their numbers. SHAM-JANELA: 10 blocks byte-identical to
rc12. No quote added; 29 code spans, all resolve. Headings unchanged.

Carried, by importing `B-rc12/parity-rc12.py` (pinned by sha256; it imports rc11's, pinned):
rc11's headlines and locks (a)–(f), its script-integrity check 13; rc12's headlines except the
§7 "drifted" sentence (the justified delta), 4(g) census not run or restored, 4(h) no credential
or credential finding, and check 14 (census record). New: 4(i) no "drift" in the body; 4(j)
abstract and §9 never say two commitments, §4.1.2 never two layers; 4(k) census and attempt in
the abstract and §9; 4(l) the Appendix A count word equals its unstruck items; 15 B-censo paths
(a) no personal path outside `raw/`, (b) `census-pins.sha256` verifies, (c) the gate-time bridge,
(d) the `RESULTADO-v3.md` bridge.

`--self-test`: **35 mutations, all caught**: mutations of the manuscript (lock mutations caught by the claim locks alone),
of the B-censo files and of `RESULTADO-v3.md`, and two carried census-record mutations; each must
be caught, and the unmutated rc13 must pass. `B-rc12/parity-rc12.py` and
`B-rc11/parity-rc11.py` still pass against their own pairs.

## Not done (declared)

- `GATES.md` keeps the `sk-` fragment noted in `APPLY-B-rc12.md` (2 characters of a value);
  not in this task's scope. It should read `sk-…` before `B-censo/` is committed.
- Ballast: `B-censo/` and the rc13 files are not in `MANIFESTO-LASTRO-P2.json` (working list 17).
- Review of rc13 (working list 24).
