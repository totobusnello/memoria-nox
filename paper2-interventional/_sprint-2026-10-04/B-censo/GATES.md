# Paper B census restoration, step 1: gates (2026-10-05)

VERDICT: FAIL

The census was **not** started. The rules were written before any call, in
`GATE-RULES-PREDECLARED.md` (23:15Z), and they are applied here as written.

| condition | result | pass? |
|---|---|---|
| (a) every provider serves the September model id | zhipu `glm-5.2`, xai `grok-4.5`, google `gemini-2.5-pro`, deepseek `deepseek-v4-pro`: all identical to September | yes |
| (b1) per-provider label agreement ≥ 0.99 (only known test-retest: `STABILITY-TEST.md` §7) | xai **50/50 = 1.00** · google **47/50 = 0.94** · zhipu **46/50 = 0.92** | **no** (google, zhipu) |
| (b2) panel-outcome agreement ≥ 0.90 | **46/50 = 0.92** (Wilson 95% [0.81; 0.97]) | yes |
| (c) `gemini-2.5-pro` still served | served, `GET models/gemini-2.5-pro` 200, no shutdown date announced | yes |

**Why it fails:** the September labels do not reproduce for `zhipu` and `google`. This is
not a borderline case where one random flip sinks a strict threshold. The 95% Wilson
intervals are zhipu [0.81; 0.97] and google [0.84; 0.98]. Both exclude 0.99. Both point
estimates also sit below the *lower* bound (0.9455) of the only measured test-retest of
this instrument.

## Gate 1: model identity (2026-10-05 23:14:52–23:15:11Z)

One call per provider, on the first gate-2 episode, through `run_panel.julgar` unchanged
(deepseek through `run_panel_deepseek6k.py`, the declared substitute). All four `ok`,
all four `not_failure/S0`.

| provider | requested | served (Oct) | served (Sept, all ok rows) | version metadata available |
|---|---|---|---|---|
| zhipu | glm-5.2 | glm-5.2 | glm-5.2 (1 195/1 195) | headers carry no model/version field |
| xai | grok-4.5 | grok-4.5 | grok-4.5 (1 195) | `GET /v1/language-models/grok-4.5`: `version 1.0`, `fingerprint fp_5a824b3f8b`, aliases `grok-4.5-latest`, `grok-build-latest` |
| google | gemini-2.5-pro | gemini-2.5-pro | gemini-2.5-pro (1 195/1 195) | `GET /v1beta/models/gemini-2.5-pro`: `version 2.5`, *"Stable release (June 17th, 2025)"* |
| deepseek | deepseek-v4-pro | deepseek-v4-pro | deepseek-v4-pro (1 195/1 195) | pricing page maps the alias to `DeepSeek-V4-Pro-0813` |

⚠️ Matching ids are the criterion that was declared, and it passes. But an id is an
**alias**, and September recorded only the alias. September has no fingerprint and no
snapshot field, so a silent weight update under the same alias cannot be ruled out from
the record. Gate 2 cannot separate "same model, non-deterministic" from "different model,
same name" either.

**Gemini retirement check:** <https://ai.google.dev/gemini-api/docs/deprecations>, read
2026-10-05 (page "Last updated 2026-10-01 UTC"). Row: `gemini-2.5-pro` · released
June 17, 2025 · **"No shutdown date announced"**. The model GET on the same endpoint we use
(`generativelanguage.googleapis.com/v1beta`) returned 200 at 23:15:11Z.

Side observation, low confidence: a scrape of <https://docs.x.ai/developers/models> did not
find `grok-4.5` among the "current" models. The API still serves it and prices it. This is
not a gate condition, but it is a retirement risk for a 5–6 h census.

## Gate 2: test-retest on 50 stratum-B episodes (23:15:21–23:17:36Z)

- **Selection** (declared first): the first 50 lines of `estrato-b-ids-20260921.txt`, in
  file order. → `gate2-ids.txt` (sha256 `6377c80b…0509`). The rows are byte-identical to
  September's input (`lotes/lote-03`, `lote-04`).
- **Run:** `run_panel.py --only zhipu,xai,google --workers 8 --timeout 180`, the September
  command (`roda-lotes.sh`). Prompt `5b22f02c…` was verified by the runner. Temperature 0;
  max_tokens 1500 (zhipu) and 300 (xai) as observed in the log; Gemini 4000 in code.
  150/150 `ok`, 0 quota, 0 missing, so no retry pass was needed.
- **Comparison:** `compare_gate2.py` → `gate2-compare.json`.

| provider | label agreement | Wilson 95% | level agreement | abstain Sept → Oct | label changes (Sept → Oct) |
|---|---|---|---|---|---|
| xai | **50/50 (1.00)** | [0.93; 1.00] | 50/50 | 0 → 0 | none |
| google | **47/50 (0.94)** | [0.84; 0.98] | 46/50 | 0 → 1 | `5d16a63d` nf→F/S2 · `aba030bb` nf→F/S3 · `d39172d6` F/S2→abstain |
| zhipu | **46/50 (0.92)** | [0.81; 0.97] | 46/50 | 1 → 0 | `ebb8c907` abstain→F/S1 · `5802f9bc` F/S1→nf · `5972b9a5` nf→F/S3 · `2ddadc73` F/S1→nf |

`model_served`: 50/50 identical to September for all three providers.

**Panel outcome** (`pilot_replay.carregar_verdicts`: τ=S1, strict majority, abstention
absent, fewer than 3 substantive verdicts gives `unknown`, 3 families): **46/50 agree**.
Sept {nf 47, F 2, unknown 1} → Oct {nf 46, F 3, unknown 1}. The 4 changes:
`ebb8c907` unknown→F · `5972b9a5` nf→F · `2ddadc73` F→nf · `d39172d6` nf→unknown.

What this means for the estimate: each stratum-B failure carries Horvitz-Thompson weight
6.945. Two of the four outcome changes are F↔nf flips, and they go in **both** directions.
So in these 50, the stratum-B failure count is not reproducible run to run at the
single-episode level. In this sample the zhipu flips sit at the S0/S1 boundary, the one τ
does not absorb (DEVIATIONS §10.31 (5)). That is an observation from n=4, not a finding.

## Cost actually spent (from the `usage` blocks, provider list prices read 2026-10-05)

| | calls | USD |
|---|---:|---:|
| google gemini-2.5-pro | 51 | 0.7977 |
| xai grok-4.5 | 51 | 0.2646 |
| zhipu glm-5.2 | 51 | 0.1135 |
| deepseek v4-pro (gate 1 only) | 1 | 0.0028 |
| **total** | **154** | **≈ US$ 1.18** |

The figures are upper bounds: DeepSeek is priced at peak, and xAI cached tokens are billed
on top of `input_tokens`. Prices and sources are listed in `census_tools.py`. Plus 2 free
metadata GETs (Gemini, xAI) and 6 Firecrawl page reads.

⚠️ **Census cost projection, from the measured gate-2 usage:** US$0.0231 per episode ×
4 756 ≈ **US$110** for the three families. Census episodes average 1 942 excerpt chars,
against 1 866 in gate 2. Retry and the DeepSeek substitute pass (~1–3% of episodes) add
< US$2. That is **~45% over the ~US$75 authorized**. Gemini is 68% of the cost, because it
spends ~1 400 thinking tokens per call.

## 🔴 Blocker outside the gates: credentials inside the census episodes

The pre-finish key scan (below) found credential-like strings **inside the locked corpus
episodes**. The `extract_episodes.py` redaction did not catch them. Only prefix and length
were read; no value was printed or copied anywhere new.

| where | episodes | string |
|---|---|---|
| census set (would be sent) | `2c134e64`, `c021451b`, `b0df13ab`, `3f4a8bdd` (Bash, agents-forge) | Slack `xoxp-…`, **79 chars (full-length user token)** |
| census set (would be sent) | `b559df4c`, `66b22c09` (agents-boris) | `sk-……`, 35 chars |
| already sent in September | `66803f88` (Bash, agents-forge) | `xoxp-…`, 20 chars (truncated) |

Running the census as prepared would send a full Slack user token to xAI, Zhipu and Google.
`run_census.sh` therefore runs `census_tools.py secret-scan` first and **refuses (exit 5)**
unless `CENSUS_SECRETS_DECISION='<decision>'` is set. The options are the author's to pick:
rotate the token, redact those 6 episodes in the batch copy (a declared deviation, and the
batch pins then change), or exclude them.

## Census: prepared, not run

| file | sha256 | role |
|---|---|---|
| `census-ids.txt` | `46c5ad6030c8bb2553628bcea6ce3a4dc3ac65129e2af3393cedf7b1b72d2f8c` | the 4 756 ids |
| `census-lotes.sha256` | `61f4eb85e1875149726139211f482d81b6d0fe5877d86008104dfe54440ec083` | 48 input batches in `~/.paper2-verdicts/censo-B-20261005/lotes/` (outside the public repo) |
| `census-pins.sha256` | see `SHA256SUMS` | pins runner, substitute, prompt, `pilot_replay.py`, harness, tools, ids, batches |
| `run_census.sh` | see `SHA256SUMS` | the wrapper |
| `gate_harness.py` | `3b0a1d4b9e2c992c52b1259034958e172973a557c995aeda56970cc3b1254bf6` | observes `run_panel` (headers + usage), changes nothing |
| `census_tools.py` | `6f6f9a6d4d9358f67ebac068362f24c87a33bdc8518b954304cb8889556a1fa6` | cost, retry sets, floorless set, secret scan |

**ID rule:** `is_error == false` in `episodios-ensaio-20260921.jsonl` (sha256 `bcf45182…`,
= manifest) **and** `episode_id ∉ estrato-b-ids-20260921.txt`, in corpus file order. Gives
5 556 − 800 = 4 756, with 0 duplicates. No verdict enters the rule.

**Wrapper** (`run_census.sh`):
- re-execs itself under `caffeinate -ims`;
- refuses unless `CENSUS_AUTHORIZED=1`, and refuses while this file says FAIL unless
  `CENSUS_GATE_OVERRIDE='<who/when/why>'` is set (it is logged verbatim);
- checks every pin before any call;
- writes **only** to `~/.paper2-verdicts/censo-B-20261005/`, never to an
  `ensaio-20260921-*` file;
- is resumable: each batch is written to `.partial` and renamed on success, a done batch
  is skipped, and the run stops at the first failed batch.

Phases:
1. 3 families × 48 batches;
2. ONE retry pass for quota/missing, per panelist (as September's `retry-xai`);
3. DeepSeek only on episodes without the 3-verdict floor (DEVIATIONS §10.31);
4. `censo-B-PRIMARIO-3fam.jsonl` + `SHA256SUMS` + `COST.json`.

Command (only after the author decides what to do about the FAIL, the credentials and the
~US$110 cost):

```sh
CENSUS_AUTHORIZED=1 CENSUS_GATE_OVERRIDE='<who/when/why>' CENSUS_SECRETS_DECISION='<decision>' \
  ~/Claude/Projetos/memoria-nox/paper2-interventional/_sprint-2026-10-04/B-censo/run_census.sh
```

Guards were tested without any API call: no `CENSUS_AUTHORIZED` gives exit 3; the pins
verify; `secret-scan` gives exit 1 with 6/4 756; `floorless`/`retry-sets` were dry-run on
the gate-2 data (1 floorless, which matches the 1 `unknown`).

## Files

- `GATE-RULES-PREDECLARED.md`: rules, written before the first call.
- `gate2-ids.txt`, `gate2-compare.json`, `compare_gate2.py`.
- `raw/` (has its own `.gitignore`, because it holds episode excerpts and panelist reasons,
  and this repo is public): `gate1-results.jsonl`, `gate1-calls.jsonl`,
  `gate2-episodes.jsonl`, `gate2-verdicts.jsonl`, `gate2-calls.jsonl`, `gate2-run.log`,
  `cost-gate{1,2}.json`. All were scanned for credentials (see `SHA256SUMS`).
