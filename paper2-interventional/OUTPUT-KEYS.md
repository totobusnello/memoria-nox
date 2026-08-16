# Output keys — glossary

The scripts in this directory emit JSON whose **keys are in Portuguese**. This
file translates them.

## Why the keys were not translated

They are the names under which every number already published in this repository
was recorded — in `SIZING-2026-08-14-v2.md`, `WASHOUT-SENSITIVITY-2026-08-14.md`,
`STABILITY-TEST.md`, `DOSE-REACH-2026-08-15.json`, and in the verdict files held
outside the repository. Renaming them now would mean that a reader running the
scripts obtains output that does not match the documents, and that any external
tool reading those files breaks silently. The cost of the mismatch is
asymmetric: a glossary is cheap, a divergence between artifact and document is
the kind of defect this study exists to avoid.

**Two keys reach the pre-registration itself** — `p0_hat` and `r_hat` — and both
are already in English.

## Study design and sizing (`sizing.py`, `pilot_replay.py`)

| Key | Meaning |
|---|---|
| `desenho` | design — `estratificado-HT` = stratified, Horvitz–Thompson weighted |
| `epochs_analisaveis` | analysable epochs (clusters with usable sessions) |
| `epochs_fora_do_icc` | epochs excluded from the ICC (fewer than 2 sessions ⇒ no within variance) |
| `epochs_por_braco` | epochs per arm (K) |
| `N_epochs_total` | total epochs = 2K |
| `curva_de_poder` | power curve — power at each true relative effect |
| `intermediarios` | intermediates, exposed for auditing |
| `design_effect` | design effect `1 + (m̄ − 1)·ICC` |
| `k_bruto` | raw K, before rounding up to an integer |
| `regra_desfecho` | outcome rule (`maioria estrita (>50%); empate => not_failure` = strict majority; tie ⇒ not_failure) |
| `corte` / `tau` | severity cut τ |
| `hours_per_epoch`, `session_hours_per_epoch` | exposure quantities per epoch |
| `lambda_0`, `lambda_1` | event rate under control / under treatment |
| `eventos_esperados_controle` / `..._tratamento` | expected events, control / treatment |
| `log_rate_ratio` | log of the rate ratio |

## Estimates and intervals

| Key | Meaning |
|---|---|
| `r_hat` | estimated opportunities per unit of exposure |
| `p0_hat` | estimated failure rate per opportunity under control |
| `p0_bruto` | unweighted (raw) p₀, before HT weighting |
| `icc`, `icc_ponto` | intraclass correlation — point estimate |
| `icc_anova` | the one-way ANOVA that produces it |
| `ms_between`, `ms_within` | mean squares, between / within clusters |
| `gl_between`, `gl_within` | degrees of freedom (*graus de liberdade*) |
| `f` | F statistic |
| `m_bar` | m̄, mean cluster size |
| `ic`, `ic_low`, `ic_high`, `ic_alfa` | confidence interval, lower bound, upper bound, α |
| `ic_searle`, `ic_bootstrap_percentil` | Searle's analytic CI / percentile bootstrap CI |
| `largura_searle`, `largura_bootstrap` | width of each interval |
| `razao_larguras_boot_sobre_searle` | ratio of widths, bootstrap over Searle |
| `reamostras` | bootstrap resamples |
| `reamostras_degeneradas` | degenerate resamples (no within variance) |
| `fracao_reamostras_com_icc_zero` | fraction of resamples with ICC clamped to 0 |

## Coverage and adjudication

| Key | Meaning |
|---|---|
| `cobertura_adjudicacao` | adjudication coverage |
| `com_veredito` | episodes carrying a consolidated verdict |
| `episodios_total` | total episodes in the universe |
| `pct` | percentage |
| `oportunidades` | opportunities |
| `oportunidades_com_desfecho_unknown` | opportunities whose outcome resolved to `unknown` |
| `por_painelista` | per panelist |
| `por_estrato` | per stratum |
| `repeats`, `repeats_bruto` | repeat events, weighted / raw |
| `n_bruto` | raw (unweighted) n |
| `descartados_sem_timestamp` | discarded for lacking a timestamp |
| `pares_tool_use_result` | `tool_use` / `tool_result` pairs |
| `assinaturas_coarse`, `assinaturas_primary`, `assinaturas_fine` | signature counts at each taxonomy level |
| `assinaturas_com_failure_conhecido` | signatures with a known best-case outcome |
| `assinaturas_descartadas_por_n_baixo` | signatures dropped for too few episodes |
| `min_por_assinatura` | minimum episodes per signature |

## Washout and epoch boundary (`washout_sensitivity.py`, `delta_carryover.py`)

| Key | Meaning |
|---|---|
| `comparacao` | which comparison this row reports |
| `diferenca`, `ic_diferenca` | difference in proportions and its CI |
| `cruza_zero` | whether the CI crosses zero |
| `zona_descartada_0_2h` | the discarded 0–2 h zone (the washout) |
| `zona_analisada_2h_em_diante` | the analysed zone, 2 h onward |
| `logo_apos_washout_2_6h` | just after the washout, 2–6 h |
| `restante_6h_em_diante` | remainder, 6 h onward |
| `incidencia_de_erro_no_universo` | error incidence over the whole universe (census) |
| `corpus_inteiro`, `corpus_total` | the full corpus |
| `washout_h`, `gap_h`, `bin_h`, `inicio_h` | hours: washout length, gap, bin width, start |
| `transicoes_adjacentes_usadas` | adjacent epoch transitions used |
| `transicoes_descartadas_por_salto` | transitions discarded for a gap in the timeline |
| `n_transicoes`, `saltos` | transition count, gaps |
| `densidade_por_epoch`, `densidade_media_por_epoch` | density per epoch, mean density |
| `delta_relativo_a_densidade_media` | delta relative to the mean density |
| `dif_min`, `dif_max`, `dif_mediana`, `abs_dif` | difference: min, max, median, absolute |

## Maturity and stock (`maturity_sensitivity.py`)

| Key | Meaning |
|---|---|
| `metade_jovem`, `metade_madura` | the young half / the mature half of the corpus |
| `estoque_por_epoch`, `estoque_min`, `estoque_max` | signature stock per epoch, min, max |
| `metodo` | method |
| `definicao` | definition |

## Panel execution (`run_panel.py`)

| Key | Meaning |
|---|---|
| `verdict`, `failure`, `abstain`, `unknown` | the verdict and its values |
| `panelist`, `family` | the panelist and its provider family |
| `model`, `model_served`, `served` | model requested / model the provider actually served |
| `status` | `ok`, `missing`, `quota` |
| `pendentes_por_cota` | calls pending because the provider's quota closed |
| `detail`, `reason` | failure detail, refusal reason |
| `stop`, `stop_reason`, `blocos` | stop reason and the response's block types |
| `chamadas`, `attempts`, `emitidos` | calls, attempts, emitted |
| `prompt_sha256` | SHA-256 of the adjudication prompt body |
| `dur_s`, `tokens`, `usage` | duration in seconds, tokens, usage |
| `sig`, `coarse`, `primary`, `fine` | the action signature at each taxonomy level |
| `is_error` | the runtime's error flag (never shown to the panel) |

## Dose reach (`dose_reach.mjs`)

| Key | Meaning |
|---|---|
| `zona`, `componente`, `componentes` | zone, component, components |
| `consulta` | query |
| `perfil` | profile |
| `taxa` | rate |
| `razao_p99_p95` | ratio of the 99th to the 95th percentile |
| `delta_p95` | delta at the 95th percentile |
