# Census restoration, step 1: gate rules, declared BEFORE any call

Written 2026-10-05T23:15Z, before the first API call of this step. Nothing below was
chosen after seeing a re-adjudicated verdict. Authorization: Toto, 2026-10-05 20:10 BRT
(gates ~US$1; census ~US$75 only if the gates pass; the census is NOT started here).

## Inputs (read-only, sha256 checked against `MANIFESTO-LASTRO-P2.json` where listed)

| artefact | sha256 |
|---|---|
| `~/Backups/paper2-ensaio-2026-09-21/episodios-ensaio-20260921.jsonl` (5 951 eps; 5 556 `is_error=false`) | `bcf45182…689f` (= manifest) |
| `~/Backups/paper2-ensaio-2026-09-21/estrato-b-ids-20260921.txt` (800 ids) | `ab4249f1…e065` |
| `~/.paper2-verdicts/ensaio-20260921-PRIMARIO-3fam.jsonl` (September 3-family verdicts) | `ccff1a14…ff49` (= manifest) |
| `~/.paper2-verdicts/ensaio-20260921-SENSIB-deepseek.jsonl` (September 4th family) | `c7ae6714…33f0` |
| `run_panel.py` (last commit d09b3cb, 2026-08-22; unchanged since; clean in the working tree) | `b2265d12…fb01` |
| `run_panel_deepseek6k.py` (declared substitute, DEVIATIONS §10.30/§10.31) | `0a95b107…ef08` |
| `adjudication_prompt.md` (body hash checked by `run_panel.py`: `5b22f02c…`) | `3767fdb5…9bd7` |
| `pilot_replay.py` (`carregar_verdicts`, the consolidation rule) | `5af42ed3…e63ce2` |

## September settings (read from the code and the run scripts, not assumed)

- `roda-lotes.sh`: `python3 run_panel.py --only zhipu,xai,google --workers 8 --timeout 180`.
- `roda-lotes-deepseek.sh`: `python3 run_panel_deepseek6k.py --only deepseek --workers 8 --timeout 220`.
- In code: temperature 0 everywhere; `max_tokens` 300 (xai), 1500 (zhipu), 6000 (deepseek
  in the 6k copy), Gemini `maxOutputTokens` 4000; one resend (and budget doubling on
  `stop=max_tokens` with empty text); prompt body sha256 `5b22f02c…` enforced.
- September `model_served` per provider (all `ok` rows): zhipu `glm-5.2` (1 195/1 195),
  xai `grok-4.5` (1 195 incl. 7 from `retry-xai`), google `gemini-2.5-pro` (1 195/1 195),
  deepseek `deepseek-v4-pro` (1 195/1 195).

## Gate 1: model identity

One call per provider (zhipu, xai, google through `run_panel.py`; deepseek through
`run_panel_deepseek6k.py`), on the first episode of the gate-2 list, through
`run_panel.julgar` unchanged. A thin harness (`gate_harness.py`) imports the module and only
*observes*: it records the HTTP response headers that carry model/version information and
the `usage` block that `chamar` already returns but `run_panel.py` does not write.
Pass: `model_served` equals the September value above for all four.
Plus: `GET /v1beta/models/gemini-2.5-pro` on the same endpoint answers, and the official
Gemini API deprecations page (URL and access date recorded) shows no shutdown date that
falls before the census would finish.

## Gate 2: test-retest on 50 stratum-B episodes

**Selection rule:** the first 50 lines, in file order, of `estrato-b-ids-20260921.txt`
(the order in which the September hash-ordered sample was written). Independent of any
verdict. List: `gate2-ids.txt`, sha256 `6377c80b4c630b4db2203122821930e47357870595a7aae35ab2675aebb30509`.
The episode rows are taken byte-identical from `lotes/lote-03.jsonl` and `lote-04.jsonl`
(checked: identical to `alvo-painel-20260921.jsonl` and to `episodios-ensaio-20260921.jsonl`).

**Run:** `run_panel.py --only zhipu,xai,google --workers 8 --timeout 180` (September
settings), via the observing harness. If any row ends `quota`/`missing`, ONE retry pass
over those rows only, same code, as September did (`retry-xai.jsonl`); the first `ok`
record per (episode, panelist) is kept.

**Metrics:**
- per provider, *label* = verdict category (`failure` / `not_failure` / `abstain`);
  agreement = identical / pairs where both runs are `ok`. Level (S0–S4) agreement and the
  transition matrix are reported, not gated.
- panel outcome = `pilot_replay.carregar_verdicts` (unchanged): strict majority at τ=S1,
  abstention absent, fewer than 3 substantive verdicts gives `unknown`; computed on the 3
  families only, for both runs. Agreement over the 50, `unknown` counted as its own category.
- abstentions, missing/quota, `model_served` per provider, both runs.

**Threshold (the "known reliability"):** the only measured test-retest of this instrument is
`STABILITY-TEST.md` §7: 99/100 identical verdict categories (Wilson 95% [0.9455; 0.9982]),
2026-08-14, same prompt `5b22f02c…`, panelist `moonshot`. No September inter-run
measurement exists for zhipu, xai or google. Declared now:

- **Per-provider criterion: agreement ≥ 0.99**, as a point comparison (with ≤ 99 compared
  pairs this means zero label changes).
- **Panel-outcome criterion: ≥ 0.90** (the user's fallback, applied in addition, not instead).

⚠️ Declared in advance as a property of this threshold: it is borrowed from a panelist
outside the 3-family panel, and if each pair truly agrees with p = 0.99, the chance that 150
pairs show zero changes is about 0.99^150 ≈ 22%. The per-provider criterion can therefore
fail on noise alone. It is applied as written anyway; the result will also report the Wilson
interval of each provider, so the reader can see whether a failure is compatible with 0.99.

## Overall decision rule (from the authorization, applied as written)

PASS iff (a) all four providers serve the September model id, AND (b) every provider meets
the per-provider criterion AND the panel outcome meets ≥ 0.90, AND (c) `gemini-2.5-pro` is
still served. Otherwise FAIL, with each failing condition named.
