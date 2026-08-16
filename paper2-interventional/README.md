# Paper 2 — Interventional Memory

> **Status (2026-08-15): pré-registro PRONTO para o OSF.** O último termo indefinido — `linked`, no braço de tratamento — foi travado como **identidade**: o chunk escrito a partir do episódio, com `episode_id`. A escrita acontece nos **dois braços**; só o boost de serving difere. Ver `LINK-FEASIBILITY-2026-08-15.md`. Não é mais planejamento — o piloto rodou, 7.184 pares (episódio, painelista) foram adjudicados, e quatro dos seis `[TO LOCK]` estão fechados. Os dois restantes não esperam análise: `T_seed_assign` se resolve ao registrar; a data-limite, no primeiro epoch randomizado.
>
> **O que ainda não aconteceu:** nenhum epoch randomizado. O estudo não começou. Tudo abaixo é pré-tratamento.

## Em uma frase

Métricas de retrieval (nDCG/recall) medem **representação**, não **decisão** — e a memória de um agente serve para *evitar repetir ações custosas*. Este trabalho mede isso com um **crossover randomizado e pré-registrado sobre tráfego de produção**, não com um benchmark.

⚠️ **A observação não é nossa.** MemoryArena (02/2026) publicou primeiro que retrieval não captura como a memória guia decisões. Nossa contribuição é o **método**. Ver `RELATED-WORK.md` §4 — e nunca escrever o contrário.

---

## Por onde começar

| # | Arquivo | Para quê |
|---|---|---|
| 1 | [`CONCEPT-NOTE.md`](CONCEPT-NOTE.md) | One-pager em EN, pronto para circular. Comece aqui se você é externo. |
| 2 | [`PREREG-DRAFT.md`](PREREG-DRAFT.md) | **O documento central** (124 KB). O registro inteiro: hipóteses, desenho, locks, apêndices. Tudo que decide algo está aqui ou é citado daqui. |
| 3 | [`RELATED-WORK.md`](RELATED-WORK.md) | Onde este trabalho se situa. **Leia antes de escrever qualquer claim de novidade.** |
| 4 | [`SIZING-2026-08-14-v2.md`](SIZING-2026-08-14-v2.md) | Os números que dimensionam o estudo, e o que ainda é incerto neles. |
| 5 | [`OSF-SUBMISSION.md`](OSF-SUBMISSION.md) | Checklist e metadados da submissão — o próximo passo do projeto. |

## O registro — o que está travado, e quando

| Item | Estado |
|---|---|
| Rota do desenho (§0) | ✅ Route 2-lite, 12/07 |
| Epoch 24 h · washout 2 h · τ=S1 · painel · prompt | ✅ 29/07 |
| `α` (dose relativa ao spread) | ✅ 29/07 — `w × Δ_cut`, `w ∈ {0.5, 1.0, 2.0}` |
| `linked` = **identidade** (chunk escrito do episódio) · escrita nos 2 braços | ✅ 15/08 |
| `N_epochs` = **174** · "powered only for effects ≥ 30%" · dimensionado no **limite superior** do ICC | ✅ 15/08 (corrigido no mesmo dia: o primeiro lock, 154 ao ponto, violava o lock (b) de 30/07 — e 154 era 152) |
| `δ` (bound de carry-over) = **36.67** | ✅ 15/08 |
| `p95` do task regret = **7.45 s** / **65 206 tokens** | ✅ 15/08 |
| `T_seed_assign` | ⏳ exige a registração OSF existir |
| Data-limite de calendário | ⏳ exige o primeiro epoch randomizado |

## A cadeia de precedência — seeds declaradas antes de existirem

Cada uma foi commitada e enviada ao repositório **antes** do round de beacon correspondente ser emitido. O histórico do git é o carimbo.

| Arquivo | Governa |
|---|---|
| [`CALIBRATION-SEED.md`](CALIBRATION-SEED.md) | A amostra de calibração de 300 episódios (κ, rubrica) |
| [`EXTENSION-SEED-2026-08-11.md`](EXTENSION-SEED-2026-08-11.md) | 1.576 de 8.194 do estrato B. ⚠️ Continha um defeito de reprodutibilidade (separador `\|` ausente no comando publicado), corrigido em 14/08 |
| [`EXTENSION-2-SEED-2026-08-14.md`](EXTENSION-2-SEED-2026-08-14.md) | 122 de 635, epochs 12–14/08. Declarada 10 min antes do round `31309420` |
| [`CORPUS-FREEZE.md`](CORPUS-FREEZE.md) | Hashes do corpus, do extractor e do prompt de adjudicação |
| `corpus-manifest-*.txt` | SHA-256 de cada arquivo do corpus congelado (3.860 linhas) |

## Medições — o que foi medido, e o que cada uma refutou

| Arquivo | Achado |
|---|---|
| [`PILOT-PROJECTION.md`](PILOT-PROJECTION.md) | O desenho da adjudicação por peças e por que não se faz censo dos 4.577 |
| [`SIZING-2026-08-14.md`](SIZING-2026-08-14.md) | 🔴 **Superado no mesmo dia** — três números errados por um bug no replay. Mantido como registro da retratação |
| [`SIZING-2026-08-14-v2.md`](SIZING-2026-08-14-v2.md) | Sizing válido, 30 clusters. ICC 0.0985 [0.057 ; 0.181] |
| [`DOSE-REACH-2026-08-15.json`](DOSE-REACH-2026-08-15.json) | A dose travada **move o brief** — e expôs a lacuna do `linked` |
| [`LINK-FEASIBILITY-2026-08-15.md`](LINK-FEASIBILITY-2026-08-15.md) | Não há chave de junção. Duas construções caem, uma funciona — em **~30%** dos failures, pelos 2 coverage slots |
| [`STABILITY-TEST.md`](STABILITY-TEST.md) | Estabilidade agregada 99% **esconde** 47.6% de oscilação nos desempates |
| [`WASHOUT-SENSITIVITY-2026-08-14.md`](WASHOUT-SENSITIVITY-2026-08-14.md) | O washout de 2 h está bem calibrado — a borda dura <2 h. Registra também um confundidor de composição em que caí |

## Scripts

Todos determinísticos, stdlib pura salvo nota. Nenhum usa `random` sem seed.

| Script | Papel |
|---|---|
| `extract_episodes.py` | 🔒 **LOCKED** (`c0abe143`, SHA-256 registrado). Define `sig()`. **Não modificar** — importar |
| `run_panel.py` | Adjudicação pelo painel. Grava `model_served` e `stop_reason` desde 14/08 |
| `pilot_replay.py` | Produz `r̂`, `p̂0`, ICC + IC. O harness canônico |
| `sizing.py` | `N_epochs = f(r̂, p̂0, ICC, MDE)`. Travado antes do piloto |
| `task_regret.py` | Distribuição do task regret → o `p95` |
| `delta_carryover.py` | → o `δ` do Apêndice B |
| `stability_sample.py` | Amostra de teste-reteste, seed do beacon |
| `washout_sensitivity.py` | Exploratório — o washout basta? |
| `maturity_sensitivity.py` | Exploratório — ⚠️ o corpus **não é estacionário** |
| `icc_bootstrap.py` | Exploratório — bootstrap de cluster; refutou a ressalva de que Searle estaria estreito |
| `link_feasibility.mjs` | Exploratório — há substrato para `linked`? Read-only |
| `dose_reach.mjs` | Exploratório — alcance de deslocamento nas doses **travadas** (as de 26/07 não eram). Read-only sobre o pool de produção |
| `tests/test_icc_ci.py` | Confronta a F em stdlib contra `scipy` (150 pontos). `scipy` **só aqui** |

**Exploratório** = não pré-especificado, não altera número travado, declarado como tal no cabeçalho do próprio script.

## Tese e histórico

| Arquivo | Conteúdo |
|---|---|
| [`CONCEPT.md`](CONCEPT.md) | A tese em PT — claim, âncora de fronteira, moat |
| [`DECISIONS.md`](DECISIONS.md) | Decisões travadas: framing, título, venue |
| [`METHODOLOGY.md`](METHODOLOGY.md) | Desenho + guardas metodológicas |
| [`REVIEWS.md`](REVIEWS.md) | 3 vozes adversariais sobre a tese (05/07) |
| [`REVIEWS-PREREG.md`](REVIEWS-PREREG.md) | GLM sobre o pré-registro (12/07): 5 FATAL / 7 GRAVE / 10 menor |
| [`PLAN-2-TRILHAS.md`](PLAN-2-TRILHAS.md) | Paralelismo engenharia × decisões (26/07) |
| [`NEXT-STEPS.md`](NEXT-STEPS.md) | Estado vivo e próximo passo |
| `adjudication_prompt.md` | O prompt do painel. Hash em `CORPUS-FREEZE.md` |
| `positive-control.jsonl` | 6 episódios **sintéticos** de controle positivo |

## Dados

**Nenhum episódio real vive neste repo — ele é público.** O corpus fica em `~/.paper2-verdicts/` (Mac) e `/var/lib/nox-mem/action-archive/` (VPS). O que entra aqui são hashes, seeds, scripts e resultados agregados.

## Relação com o resto do repo

O Paper 1 (artefato) está em `paper/`. Quando isto virar draft, migra para lá pela convenção dele. Produtização não vive aqui — vai para o repo `nox-mem`.
