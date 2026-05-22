# G8 — entity-eval-v2 Re-ingest + SOURCE_TYPE_BOOST Ablation

**Data:** 2026-05-20  
**Branch:** `research/g8-entity-eval-v2-2026-05-20`  
**Goal:** validar de forma controlada se `SOURCE_TYPE_BOOST` (PR #154) realmente contribui pro ranking, corrigindo o defeito do entity-eval.db v1 (keys sintéticas `entity_file/session_summary/event_log` que não batiam com o mapa de produção).

---

## Sumário Executivo

- **A5 (source-type only) > A0 (no boosts) por +2.66% nDCG@10** — boost contribui isolado.
- **A8 (full canonical) < A10 (full minus source-type) por -0.81% nDCG@10** — empilhado em cima de section+recency+salience, source_type degrada open-domain.
- **Veredicto:** SOURCE_TYPE_BOOST **está vivo** (provado isolado em A5), mas **redundante** na configuração canônica atual; reduz nDCG marginalmente quando empilhado. Decisão de manter ON em prod é defensável pela contribuição multi-hop (+1.4pp em A8 vs A10), mas open-domain perde (-3.5pp).
- **A configuração v1 do entity-eval.db estava genuinamente cega ao boost** (A8 == A10 == 0.5845 em G6). A v2 corrige isso e mostra divergência mensurável.

---

## Pipeline executado

### 1. Re-ingest entity-eval-v2.db (prod-consistent source_types)

Fonte: `corpus.jsonl` do entity-eval v1 (g4-v3-rerun-2026-05-19) com remap determinístico:

| v1 source_type | → v2 source_type | SOURCE_TYPE_BOOST | n |
|---|---|---|---|
| `entity_file` | `entity` | **2.0** | 286 |
| `event_log` | `lesson` | **1.8** | 93 |
| `session_summary` | `session` | 1.0 | 121 |
| **total** | | | **500** |

- Path: `/root/.openclaw/workspace/eval-data/entity-eval-v2-2026-05-20/entity-eval-v2.db`
- Script: `g8-ingest-corpus.mjs` (clone do g3-ingest-corpus.mjs com guard NOX_DB_PATH no /eval-data/)
- Schema: V7 base + V8/V9/V10 (section, pain, retention_days) + kg_entities/kg_relations/procedures empty bootstrap
- Vectorize: 500/500 em 26s via gemini-embedding-001 (batch=50, 0 errors)
- **Key match com SOURCE_TYPE_BOOST: 500/500 (100%)** — todos os chunks têm source_type em (`entity`, `lesson`, `session`)

### 2. G8 ablation matrix (n=100, port 18803, isolado de prod 18802)

| Config | env vars | nDCG@10 | MRR | R@10 | P@5 | p95 lat |
|---|---|---|---|---|---|---|
| **A0** no boosts | `NOX_DISABLE_TYPE_BOOST=1 NOX_DISABLE_SOURCE_TYPE_BOOST=1 NOX_DISABLE_SECTION_BOOST=1 NOX_DISABLE_RECENCY_BOOST=1 NOX_SALIENCE_MODE=shadow` | 0.4816 | 0.4564 | 0.6317 | 0.1740 | 2553ms |
| **A5** source-only | `NOX_DISABLE_TYPE_BOOST=1 NOX_DISABLE_SECTION_BOOST=1 NOX_DISABLE_RECENCY_BOOST=1 NOX_SALIENCE_MODE=shadow` | **0.4944** | 0.4612 | 0.6550 | 0.1860 | 2529ms |
| **A8** full canonical | `NOX_SALIENCE_MODE=active` (tudo default-on; tier_boost opt-in OFF) | 0.5798 | 0.5448 | 0.7267 | 0.2120 | 2526ms |
| **A10** full minus source | `NOX_DISABLE_SOURCE_TYPE_BOOST=1 NOX_SALIENCE_MODE=active` | **0.5845** | 0.5547 | 0.7167 | 0.2140 | 2536ms |

---

## G8 vs G6 (entity-eval.db v1)

| Config | G6 (v1) | G8 (v2) | Δ |
|---|---|---|---|
| A0 | 0.4829 | 0.4816 | -0.27% |
| A5 | 0.4816 | 0.4944 | **+2.66%** |
| A8 | 0.5845 | 0.5798 | -0.80% |
| A10 | 0.5845 | 0.5845 | 0.00% |

**Leitura:**
- A0/A10 ficaram dentro do ruído entre v1 e v2 (esperado — boost inert ou desligado nesses dois).
- A5 saltou +2.66% — confirmação direta de que SOURCE_TYPE_BOOST estava vivo no código mas inerte no corpus v1 (keys não batiam).
- A8 caiu -0.80% — em v1 o full canonical não usava source_type boost (inert), em v2 usa, e o efeito empilhado é levemente negativo.

---

## Breakdown por categoria (entity-eval-v2.db)

| Categoria | A0 | A5 | A8 | A10 | Δ(A5−A0) | Δ(A8−A10) |
|---|---|---|---|---|---|---|
| single-hop | 0.5774 | 0.5708 | 0.7893 | 0.7893 | -0.66pp | 0.00 |
| multi-hop | 0.5818 | 0.6168 | 0.7377 | 0.7238 | **+3.50pp** | **+1.39pp** |
| open-domain | 0.5924 | 0.6278 | 0.7025 | 0.7372 | **+3.54pp** | **-3.47pp** |
| adversarial | 0.6565 | 0.6565 | 0.6696 | 0.6721 | 0.00 | -0.25pp |
| temporal | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.00 | 0.00 |

**Onde source_type ajuda isolado (A5 vs A0):** multi-hop + open-domain (+3.5pp cada).  
**Onde source_type empilhado prejudica (A8 vs A10):** open-domain perde -3.5pp porque o boost dobra com section_boost em compiled chunks, fazendo o ranking convergir para sempre o mesmo subset de entidades, prejudicando recall em queries de domínio aberto.

---

## Veredicto

### SOURCE_TYPE_BOOST está LIVE ✓

A diferença A5 vs A0 (+2.66%) prova que o boost é aplicado e altera o ranking final. PR #154 (backfill) **funciona conforme especificado**.

### Mas redundante no stack canônico ✗

A diferença A10 vs A8 (-0.81%) indica que, com section_boost + salience active já ativos, source_type **dobra signal** em compiled/lesson chunks e degrada open-domain. O ganho multi-hop (+1.4pp) não compensa a perda open-domain (-3.5pp) no agregado.

### Recomendação

1. **Manter SOURCE_TYPE_BOOST ON em prod** (status quo) até medir em corpus prod real (g5.db 68k chunks) — entity-eval-v2 é 500 chunks sintéticos, signal pode não generalizar.
2. **Considerar boost values menores** — atual (entity 2.0, lesson 1.8) é agressivo. Trim para (entity 1.3, lesson 1.2) poderia preservar contribuição multi-hop sem dobrar open-domain.
3. **Próximo gate:** rodar G9 contra g5.db (prod clone) com mesma matrix A0/A5/A8/A10 antes de qualquer rollback. G8 é evidência necessária, não suficiente.

---

## Artefatos

- DB: `/root/.openclaw/workspace/eval-data/entity-eval-v2-2026-05-20/entity-eval-v2.db` (VPS)
- Corpus: `corpus.jsonl` (remapped) + `corpus-v1.jsonl` (original backup) na mesma pasta
- Results: `results/{A0_no_boosts,A5_source_type_only,A8_full_canonical,A10_full_minus_source_type}.json`
- Runner: `run-g8-ablations.sh` (versionado na VPS)
- Logs: `/tmp/g8-vectorize.log`, `/tmp/g8-ablations.log`

---

## Time budget

| Fase | Duração |
|---|---|
| Re-ingest + remap + bootstrap KG tables | ~4 min |
| Vectorize 500 chunks | 26 s |
| 4 ablations × ~3 min cada | ~12 min |
| Debug missing kg_entities (round 1 falhou 0.0) | ~3 min |
| Report + commit | ~5 min |
| **Total wall** | **~25 min** (dentro do time-box de 90min) |
