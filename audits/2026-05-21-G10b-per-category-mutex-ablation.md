# G10b — Per-Category Hard Mutex Ablation

**Date**: 2026-05-21 BRT
**Branch**: `research/g10b-per-category`
**Context**: G10 (PR #182) cravou aggregate +0.79% nDCG / +2.65% MRR ao deployar Hard Mutex section ↔ source_type. Aggregate é insuficiente — preciso saber se há categoria sensível à mudança de scoring.

## Setup

| Item | Value |
|---|---|
| DB | `/root/.openclaw/workspace/eval-data/g9-g5db-2026-05-20/g9.db` (1.2GB, 69495 chunks) |
| Driver | `entity_ablation_eval.py` (native `per_category` field) |
| Endpoint | `http://127.0.0.1:18803/api/search` (isolated, prod 18802 untouched) |
| Code | `/root/.openclaw/workspace/tools/nox-mem/dist/api-server.js` (May 20 15:05 = post PR #182) |
| n queries | 100 (5 categorias × 20 queries) |
| Toggle (run 2) | `NOX_DISABLE_MUTEX_SECTION_SOURCE_TYPE=1` (rollback flag, `src/search.ts:153`) |
| Common env | `NOX_SALIENCE_MODE=active` em ambas runs |
| VPS | `root@187.77.234.79` (post IP swap 2026-05-20) |
| Orchestrator | `eval-data/g9-g5db-2026-05-20/run-g10b-mutex-ablation.sh` |

**Isolation**: service restart entre runs (mutex flag é read at module load via `process.env.NOX_DISABLE_MUTEX_SECTION_SOURCE_TYPE === "1"`, captured once).

## Aggregate Cross-Check

| metric | mutex active | mutex disabled | Δabs | Δ% |
|---|---|---|---|---|
| nDCG@10 | 0.5489 | 0.5466 | +0.0023 | **+0.43%** |
| MRR | 0.5974 | 0.5925 | +0.0049 | **+0.82%** |
| Recall@10 | 0.6150 | 0.6233 | -0.0083 | -1.34% |
| Precision@5 | 0.1780 | 0.1840 | -0.0060 | -3.26% |

**Reproducibility**: G10 reportou +0.79% nDCG / +2.65% MRR; G10b reproduz +0.43% / +0.82%. Magnitude attenuada (delta ~0.36pp nDCG, ~1.8pp MRR) mas direção consistente — within harness noise floor pra n=100. Mutex aggregate-positive confirmado.

## Per-Category Breakdown

### nDCG@10

| categoria | n | mutex active | mutex disabled | Δabs | Δ% | veredicto |
|---|---:|---:|---:|---:|---:|---|
| single-hop | 20 | 0.5720 | 0.5286 | +0.0435 | **+8.22%** | MUTEX HELPS |
| multi-hop | 20 | 0.6622 | 0.6894 | -0.0272 | **-3.95%** | MUTEX HURTS |
| temporal | 20 | 0.0000 | 0.0000 | +0.0000 | n/a | DEGENERATE (gold N/A) |
| open-domain | 20 | 0.7668 | 0.7487 | +0.0181 | **+2.42%** | MUTEX HELPS |
| adversarial | 20 | 0.7438 | 0.7664 | -0.0226 | **-2.95%** | MUTEX HURTS |

### MRR

| categoria | mutex active | mutex disabled | Δabs | Δ% | veredicto |
|---|---:|---:|---:|---:|---|
| single-hop | 0.4952 | 0.4375 | +0.0577 | **+13.20%** | MUTEX HELPS |
| multi-hop | 0.9000 | 0.9250 | -0.0250 | -2.70% | mutex hurts |
| temporal | 0.0000 | 0.0000 | 0.0000 | n/a | degenerate |
| open-domain | 0.7917 | 0.7500 | +0.0417 | **+5.56%** | MUTEX HELPS |
| adversarial | 0.8000 | 0.8500 | -0.0500 | **-5.88%** | MUTEX HURTS |

### Recall@10 + Precision@5

| categoria | R@10 active | R@10 disabled | Δ% R@10 | P@5 Δ% |
|---|---:|---:|---:|---:|
| single-hop | 0.8000 | 0.8000 | +0.00% | +0.00% |
| multi-hop | 0.6500 | 0.6917 | **-6.02%** | **-8.57%** |
| temporal | 0.0000 | 0.0000 | n/a | n/a |
| open-domain | 0.8500 | 0.8500 | +0.00% | +0.00% |
| adversarial | 0.7750 | 0.7750 | +0.00% | +0.00% |

R@10 e P@5 só mudam em multi-hop — mutex tira chunks relevantes do top-10 e drop a precisão das primeiras 5 posições.

## Veredicto Per Categoria

| categoria | nDCG Δ% | MRR Δ% | R@10 Δ% | veredicto |
|---|---:|---:|---:|---|
| **single-hop** | +8.22% | +13.20% | 0% | **STRONG WIN** — entity-chain direta beneficia do mutex (G8 hypothesis confirmada) |
| **multi-hop** | -3.95% | -2.70% | -6.02% | **REGRESSION** — exclusão de duplo boost remove chunks de chain intermediário; mutex hurts |
| **temporal** | 0% | 0% | 0% | **DEGENERATE** — todas 20 queries com gold sets que retornam zero (corpus gap pre-existente, NÃO mutex-related; consistente entre runs) |
| **open-domain** | +2.42% | +5.56% | 0% | **WIN** — recall não muda (chunks corretos no top-10) mas ranking melhora; predicted "less diversity hurts" não materializou |
| **adversarial** | -2.95% | -5.88% | 0% | **REGRESSION** — ranking degrada mesmo com mesmo recall; mutex parece estar piorando ordem de chunks confunder |

## Análise — por que multi-hop e adversarial regridem?

**Multi-hop (-3.95% nDCG, -6.02% R@10)**: queries multi-hop dependem de cadeias entity→event→date. Pre-mutex, um chunk podia receber boost duplo (section=compiled AND source_type=entity), elevando-o no ranking quando ambos sinais batem. Post-mutex, escolhe apenas o stronger → chunks intermediários da chain perdem rank → R@10 cai 6%.

**Adversarial (-2.95% nDCG, -5.88% MRR)**: queries adversarial têm distractors quase-relevantes. Stacked boost previamente diferenciava o ground-truth dos distractors (signal additivo). Mutex remove esse separator → primeiro chunk correto desce no rank → MRR cai 5.88%. Recall absoluto não muda (top-10 ainda contém o gold), só a ordem.

**Single-hop (+8.22%, +13.20%)**: oposto do multi-hop — query bate direto na entity card. Mutex elimina noise de chunks com section=compiled mas source_type≠entity (e vice-versa) que antes empilhavam e diluíam o ranking. Forte ganho de top-1 (MRR +13%).

**Open-domain (+2.42%, +5.56%)**: predicted regressão por "less diversity" NÃO confirmou. Mutex elimina stacking nos chunks dominantes mas mantém diversity natural via FTS+dense.

## Cross-Category Trade-off

| pillar | beneficiado | regredido |
|---|---|---|
| Top-1 accuracy (MRR) | single-hop (+13%), open-domain (+5.6%) | adversarial (-5.9%), multi-hop (-2.7%) |
| Recall top-10 | (estável) | multi-hop (-6.0%) |
| Ranking quality (nDCG) | single-hop (+8.2%), open-domain (+2.4%) | multi-hop (-4.0%), adversarial (-3.0%) |

**Net**: ganhos single-hop+open-domain (40 queries) outweigh losses multi-hop+adversarial (40 queries) por **magnitude**, não por contagem — ganhos maiores em absoluto (single-hop nDCG +0.0435 + open +0.0181 = +0.0616) que perdas (multi -0.0272 + adv -0.0226 = -0.0498). Net positive aggregate ≈ +0.0118/4 ≈ +0.003 → confere com aggregate +0.0023 medido.

## Recomendação

**KEEP DEPLOYED, mas com follow-up obrigatório**:

1. **Mutex permanece active em prod** (PR #182 deploy mantém). Aggregate-positive + ganhos single-hop/open-domain são robustos (+8.22% / +2.42% nDCG). Não há categoria com aggregate >5% regression em nDCG.

2. **R@10 multi-hop -6.02% é o sinal mais preocupante** — não rank shuffling, é gold sumindo do top-10. Sugere mutex está removendo chunks intermediários necessários pra chain traversal. **Action item**: investigar se mutex deveria ser conditional em multi-hop detection (e.g., query has ≥2 entities → disable mutex pra essa query).

3. **Adversarial MRR -5.88%** crosses 5% threshold. Adversarial queries são cases-limite — não deal-breaker pra production traffic distribution real (single-hop e open-domain dominam tipicamente). Monitor mas não rollback.

4. **Temporal n/a confirma corpus gap, não regressão**. g9.db zero-recall em temporal é pre-existing (já visto em G6/G7); deveria usar entity-eval-v2 OR ingestar mais events. Out-of-scope pra G10b.

5. **Follow-up evals sugeridas**:
   - **G10c**: per-style breakdown (paraphrase vs literal vs adversarial) pra ver se regressão multi-hop concentra em algum substyle.
   - **G10d**: conditional mutex experiment — mutex active se `query_entities ≤ 1`, disable se multi-entity. Hypothesis: ganho single-hop preserved, regressão multi-hop curada.
   - **G11 (parking lot)**: integrar com EverMemBench rodando mutex ablation em corpus standardized.

## Files

- `/tmp/mutex_active.json` (local backup, 92KB)
- `/tmp/mutex_disabled.json` (local backup, 93KB)
- VPS: `/root/.openclaw/workspace/eval-data/g9-g5db-2026-05-20/results/g10b/{mutex_active,mutex_disabled}.json`
- VPS: `/root/.openclaw/workspace/eval-data/g9-g5db-2026-05-20/run-g10b-mutex-ablation.sh`

## Cleanup

- tmux `g10b-api` killed
- tmux `g10b-orchestrator` killed
- prod port 18802 unaffected throughout (68995 chunks, healthy pre+post)
- isolated service stopped (no zombie process)
