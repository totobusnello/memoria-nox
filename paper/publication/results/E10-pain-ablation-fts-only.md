# E10 Pain Ablation — FTS-Only Mode

> Generated: 2026-05-04 11:51 UTC | Runtime: 0s
> Script: `paper/publication/baselines/pain_ablation_fts_only.py`

## Hypothesis

Pain dimension shows significant effect when isolated from semantic Gemini layer.

## Setup

| Parameter | Value |
|---|---|
| Mode | FTS5 BM25 × pain multiplier ONLY (no Gemini embeddings, no RRF) |
| Scoring | composite = (−bm25_score) × pain |
| pain_real DB | `nox-mem-snapshot-20260504-0616.db` |
| pain_uniform DB | `nox-mem-pain-uniform-fts.db` (pain = 1.0 for ALL chunks) |
| Queries | `golden-queries.jsonl` |
| Bootstrap | 10,000 resamples, seed=42 |
| Significance threshold | Δ ≥ 0.05 AND CI excludes 0 |
| Directional threshold | Δ ≥ 0.02 |

**Comparison baseline:** Hybrid run E10 Δ = +0.0065 (n=31, Gemini semantic dominant)

## Results n=31 — post-incident subset (comparable to hybrid run)

| Q | Query (truncated 55 chars) | Category | Gold pain (mean) | FTS hits | nDCG real | nDCG uniform | Δ nDCG |
|---|---|---|---|---|---|---|---|
| Q46 | qual modelo Gemini usar como default no nox-mem | decision | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q47 | o que faz withOpAudit e quando usar | entity | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q48 | como ativar salience em produção | procedure | 0.73 | 0 | 0.000 | 0.000 | +0.000 |
| Q52 | como rodar nox-mem reindex com segurança | procedure | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q55 | como fazer backup pre-op atomico | procedure | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q56 | qual modelo embedding usar | decision | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q57 | como gerar entity file no formato compiled+timeline | procedure | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q61 | como ativar section_boost | procedure | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q63 | qual a estratégia de retention por tipo | decision | 0.50 | 0 | 0.000 | 0.000 | +0.000 |
| Q64 | como funciona o cron quarterly DR drill | procedure | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q66 | como migrar Gemini Flash pra Flash-Lite | procedure | 0.23 | 0 | 0.000 | 0.000 | +0.000 |
| Q67 | qual a regra sobre rsync delete | decision | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q70 | quando o salience foi ativado | temporal | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q71 | qual a primeira lição do incident reindex 2026-04-25 | temporal | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q74 | onde estão as creds Gemini | security | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q75 | qual a regra sobre commitar secrets | security | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q77 | qual o uso de chattr +i no .credentials.json | security | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q78 | como rodar smoke test completo | procedure | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q80 | como debugar gateway fratricide | procedure | 0.75 | 0 | 0.000 | 0.000 | +0.000 |
| Q83 | como o KG é populado | procedure | 0.20 | 1 | 0.000 | 0.000 | +0.000 |
| Q85 | como Lex e Cipher se complementam em incidents | cross-agent | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q87 | quando o E05 edge typing foi deployado | temporal | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q88 | quando subiu o schema v12 | temporal | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q89 | como rotacionar a key Slack sem downtime | security | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q90 | qual a regra sobre sed em arquivos binários | security | 0.35 | 0 | 0.000 | 0.000 | +0.000 |
| Q91 | por que F09 off-site backup foi rejeitado | decision | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q92 | qual foi a decisão sobre fallback chain após v.26 | decision | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q97 | como adicionar um novo agente ao sistema | procedure | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q100 | como exportar a memória pra outro lugar | procedure | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q101 | o que acontece se o disco enche | procedure | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q102 | como auditar quem acessou o que | security | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| **Mean** | | | | | **0.000** | **0.000** | **+0.000** |

### Aggregate statistics

| Metric | Value |
|---|---|
| N queries | 31 |
| Mean Δ nDCG@10 (real − uniform) | +0.0000 |
| Queries improved (Δ > 0) | 0 / 31 |
| Queries degraded (Δ < 0) | 0 / 31 |
| Queries unchanged (Δ ≈ 0) | 31 / 31 |
| Zero-recall queries (FTS hits = 0) | 30 / 31 |
| Bootstrap 95% CI | [+0.0000, +0.0000] |
| CI excludes zero | NO |

**Verdict (n=31): INSIGNIFICANT**

Δ=+0.0000 — absolute effect below 0.02 threshold. FTS-only pain signal is too weak to discriminate.  This confirms the paper §5.5 framing: pain is a secondary signal, not a standalone retrieval mechanism.

## Results n=60 — all queries

| Q | Query (truncated 55 chars) | Category | Gold pain (mean) | FTS hits | nDCG real | nDCG uniform | Δ nDCG |
|---|---|---|---|---|---|---|---|
| Q62 | quem é o Toto | entity | 0.60 | 10 | 0.613 | 0.177 | **+0.436** |
| Q73 | o que é graph-memory plugin | entity | 0.20 | 10 | 0.277 | 0.349 | **-0.072** |
| Q45 | como funciona monkey-patch do Issue 62028 do OpenClaw | entity | 0.30 | 3 | 0.000 | 0.000 | +0.000 |
| Q46 | qual modelo Gemini usar como default no nox-mem | decision | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q47 | o que faz withOpAudit e quando usar | entity | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q48 | como ativar salience em produção | procedure | 0.73 | 0 | 0.000 | 0.000 | +0.000 |
| Q49 | qual a diferença entre graphify e nox-mem KG | concept | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q50 | qual a porta da nox-mem-api | entity | 0.35 | 0 | 0.000 | 0.000 | +0.000 |
| Q51 | o que é monkey-patch fratricide | concept | 0.30 | 10 | 0.000 | 0.000 | +0.000 |
| Q52 | como rodar nox-mem reindex com segurança | procedure | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q53 | qual o trigger de cascade delete em chunks | entity | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q54 | diferença entre tier core warm peripheral | concept | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q55 | como fazer backup pre-op atomico | procedure | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q56 | qual modelo embedding usar | decision | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q57 | como gerar entity file no formato compiled+timeline | procedure | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q58 | o que é shadow-mode e por quê obrigatório | concept | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q59 | como o RRF funciona no hybrid search | concept | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q60 | qual a diferença entre salience e tier | concept | 0.73 | 0 | 0.000 | 0.000 | +0.000 |
| Q61 | como ativar section_boost | procedure | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q63 | qual a estratégia de retention por tipo | decision | 0.50 | 0 | 0.000 | 0.000 | +0.000 |
| Q64 | como funciona o cron quarterly DR drill | procedure | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q65 | o que faz o ingest-router routeIngest | entity | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q66 | como migrar Gemini Flash pra Flash-Lite | procedure | 0.23 | 0 | 0.000 | 0.000 | +0.000 |
| Q67 | qual a regra sobre rsync delete | decision | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q68 | como resolver Sentence Transformer Issue 62028 | negative | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q69 | qual versão do schema atual | entity | 0.35 | 0 | 0.000 | 0.000 | +0.000 |
| Q70 | quando o salience foi ativado | temporal | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q71 | qual a primeira lição do incident reindex 2026-04-25 | temporal | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q72 | como cross-search funciona entre agentes | cross-agent | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q74 | onde estão as creds Gemini | security | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q75 | qual a regra sobre commitar secrets | security | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q76 | como Atlas e Boris se comunicam | cross-agent | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q77 | qual o uso de chattr +i no .credentials.json | security | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q78 | como rodar smoke test completo | procedure | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q79 | qual a versão atual do OpenClaw | entity | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q80 | como debugar gateway fratricide | procedure | 0.75 | 0 | 0.000 | 0.000 | +0.000 |
| Q81 | o que faz o reflect cache | concept | 0.47 | 0 | 0.000 | 0.000 | +0.000 |
| Q82 | qual a estratégia de 7 agentes | concept | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q83 | como o KG é populado | procedure | 0.20 | 1 | 0.000 | 0.000 | +0.000 |
| Q84 | qual o risco de boost stacking | concept | 0.47 | 0 | 0.000 | 0.000 | +0.000 |
| Q85 | como Lex e Cipher se complementam em incidents | cross-agent | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q86 | qual workflow Forge usa pra code review | cross-agent | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q87 | quando o E05 edge typing foi deployado | temporal | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q88 | quando subiu o schema v12 | temporal | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q89 | como rotacionar a key Slack sem downtime | security | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q90 | qual a regra sobre sed em arquivos binários | security | 0.35 | 0 | 0.000 | 0.000 | +0.000 |
| Q91 | por que F09 off-site backup foi rejeitado | decision | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q92 | qual foi a decisão sobre fallback chain após v.26 | decision | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q93 | o que faz o subcomando kg-reclassify | entity | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q94 | como funciona o RELATION_TYPE_TO_REASON map | concept | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q95 | como o sistema lida com chunks duplicados | concept | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q96 | qual a diferença entre memória de curto e longo prazo a | concept | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q97 | como adicionar um novo agente ao sistema | procedure | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q98 | o sistema funciona offline | concept | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q99 | qual o limite máximo de chunks armazenáveis | concept | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q100 | como exportar a memória pra outro lugar | procedure | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q101 | o que acontece se o disco enche | procedure | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q102 | como auditar quem acessou o que | security | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q103 | qual modelo de IA é usado pra busca | entity | 0.20 | 0 | 0.000 | 0.000 | +0.000 |
| Q104 | como medir se a busca está boa | concept | 0.50 | 0 | 0.000 | 0.000 | +0.000 |
| **Mean** | | | | | **0.015** | **0.009** | **+0.006** |

### Aggregate statistics

| Metric | Value |
|---|---|
| N queries | 60 |
| Mean Δ nDCG@10 (real − uniform) | +0.0061 |
| Queries improved (Δ > 0) | 1 / 60 |
| Queries degraded (Δ < 0) | 1 / 60 |
| Queries unchanged (Δ ≈ 0) | 58 / 60 |
| Zero-recall queries (FTS hits = 0) | 55 / 60 |
| Bootstrap 95% CI | [-0.0036, +0.0218] |
| CI excludes zero | NO |

**Verdict (n=60): INSIGNIFICANT**

Δ=+0.0061 — absolute effect below 0.02 threshold. FTS-only pain signal is too weak to discriminate.  This confirms the paper §5.5 framing: pain is a secondary signal, not a standalone retrieval mechanism.

## Per-query breakdown — top 10 by |Δ| (n=60)

| Q | Query | Category | Gold pain | FTS hits | nDCG real | nDCG uniform | Δ |
|---|---|---|---|---|---|---|---|
| Q62 | quem é o Toto | entity | 0.60 | 10 | 0.613 | 0.177 | **+0.436** |
| Q73 | o que é graph-memory plugin | entity | 0.20 | 10 | 0.277 | 0.349 | **-0.072** |
| Q45 | como funciona monkey-patch do Issue 62028 do OpenClaw | entity | 0.30 | 3 | 0.000 | 0.000 | **+0.000** |
| Q46 | qual modelo Gemini usar como default no nox-mem | decision | 0.20 | 0 | 0.000 | 0.000 | **+0.000** |
| Q47 | o que faz withOpAudit e quando usar | entity | 0.20 | 0 | 0.000 | 0.000 | **+0.000** |
| Q48 | como ativar salience em produção | procedure | 0.73 | 0 | 0.000 | 0.000 | **+0.000** |
| Q49 | qual a diferença entre graphify e nox-mem KG | concept | 0.20 | 0 | 0.000 | 0.000 | **+0.000** |
| Q50 | qual a porta da nox-mem-api | entity | 0.35 | 0 | 0.000 | 0.000 | **+0.000** |
| Q51 | o que é monkey-patch fratricide | concept | 0.30 | 10 | 0.000 | 0.000 | **+0.000** |
| Q52 | como rodar nox-mem reindex com segurança | procedure | 0.20 | 0 | 0.000 | 0.000 | **+0.000** |

## Comparison: FTS-only vs Hybrid

| Metric | FTS-only (n=31) | FTS-only (n=60) | Hybrid (n=31) |
|---|---|---|---|
| Mean Δ nDCG@10 | +0.0000 | +0.0061 | +0.0065 |
| 95% CI lower | +0.0000 | -0.0036 | — |
| 95% CI upper | +0.0000 | +0.0218 | — |
| CI excludes 0 | NO | NO | NO |
| Verdict | INSIGNIFICANT | INSIGNIFICANT | DIRECTIONAL |

## Verdict

**n=31: INSIGNIFICANT** — Δ=+0.0000 — absolute effect below 0.02 threshold. FTS-only pain signal is too weak to discriminate.  This confirms the paper §5.5 framing: pain is a secondary signal, not a standalone retrieval mechanism.

**n=60: INSIGNIFICANT** — Δ=+0.0061 — absolute effect below 0.02 threshold. FTS-only pain signal is too weak to discriminate.  This confirms the paper §5.5 framing: pain is a secondary signal, not a standalone retrieval mechanism.

## Interpretation for paper §5.5

FTS-only Δ is effectively zero — pain does not move the needle in FTS-only mode.  Two possible explanations:

1. **Pain range is too narrow** (0.1–1.0, mostly 0.2):  54,794 of 61,257 chunks have pain=0.2 (default).  With ~89% of the corpus at the same value, the discriminating power is minimal.

2. **FTS recall is zero for most queries** (gold chunks not retrieved by BM25):  If FTS cannot surface the gold chunks at all, pain cannot influence their ranking.  Check the `FTS hits` column — queries with 0 hits are unrescuable by pain.

Recommended §5.5 revision: *'Pain calibration (current range: 0.2–1.0, median 0.2) is insufficient to produce measurable retrieval gains.  The pain dimension requires wider calibration or a normalized log-scale to serve as an effective fallback discriminator.'*

---

**Safety note:** Prod DB was not modified.  Real snapshot is read-only.  Uniform-pain DB is a caller-created temp copy (deleted if --cleanup passed).

**Runtime:** 0s total for both N variants.
