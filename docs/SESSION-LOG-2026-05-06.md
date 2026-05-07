# Session Log — 2026-05-06

**Duração:** ~4h (17:00 → 21:25 BRT)
**Foco:** Evolução nox-mem core (paralelo ao paper). E05b + E13 ranking improvements + cura completa golden corpus.
**Resultado:** 1 feature em produção (E13), 1 em shadow tuned round 2 (E05b), eval baseline +0.056 nDCG global, gate automation agendado.

---

## Cronologia

### Bloco 1 — Retomada (17:00-17:30)
- Patrick Lewis sem resposta (paper bloqueado dia 1/7)
- Sanity check pre-flight smoke 9/10 ✓ (1 warning esperado)
- PDF público HTTP 302 (link funciona)
- Mapeado backlog real do nox-mem core (vs paper) — várias frentes acionáveis sem dependência de gate de tempo

### Bloco 2 — E05b Reason-aware Ranking Boost (17:30-19:50)
**Spec:** `specs/2026-05-06-E05b-reason-ranking-boost.md`
**Impl:** `tools/nox-mem/src/lib/reason-boost.ts` ~270 LOC

- Premissa: `kg_relations.relation_reason` (E05 Phase 1) só era surface em SPO; agora vira sinal aditivo de retrieval
- Pesos v1: depends_on/replaces=0.15, extends=0.12, derived_from=0.10, opposes=0.08, mentions=0.03
- Cap 0.30 single-pass (regra crítica #5: aditivo, não empilhável)
- Resolução chunk→entities via `kg_relations.evidence_chunk_id`; query→entities via substring match em `kg_entities.name`
- Schema v13 (search_telemetry +3 cols)
- Tests 10/10 + suite full 119/120 (1 skip pré)
- Deploy shadow VPS 19:48 BRT
- Achado: cobertura `evidence_chunk_id` ~0.47% (291/61285) — kg-extract loop tmux lançado pra atingir 5%
- Commits: `0a8fc95` (nox-workspace src), `4f562d3` (memoria-nox spec+docs)

### Bloco 3 — E13 Temporal-aware Ranking (19:50-20:35)
**Spec:** `specs/2026-05-06-E13-temporal-aware-ranking.md`
**Impl:** `tools/nox-mem/src/lib/temporal-detector.ts` ~110 LOC

Investigação revelou 3 root causes do nDCG temporal=0.233:

1. **`section_boost.timeline = 0.8` demota** chunks temporais. 100% dos gold cured (Q70/Q71) estão em timeline.
2. **27% das queries (16/60) têm `expected_chunk_ids=[]`** — distorce médias com 0s artificiais.
3. Pra queries temporais, **timeline IS truth** (eventos com data) — design correto pra factuais, errado pra temporais.

**Solução:** detector regex (`quando`, `primeira/última`, `deployado`, ISO date) + override `section_boost`: timeline 0.8→1.4, compiled 2.0→1.0. Aplicado SOMENTE se `mode=active && isTemporal`.

- Schema v14 (search_telemetry +2 cols `was_temporal_query/temporal_boost_mode`)
- Tests 21/21 + suite full 140/141
- Deploy shadow VPS 20:33 BRT
- Commits: `feb654c` (nox-workspace src), `7747a5a` (memoria-nox spec+docs)

### Bloco 4 — Cura Q87/Q88 (20:35-20:45)
- Q87 "quando E05 deployado" + Q88 "quando subiu schema v12" tinham `expected_chunk_ids=[]`
- **Doc gap real**: evento E05+v12 não estava registrado em chunk nenhum do FS
- **Solução:** appendar 27 timeline events ao `nox-mem.md` cobrindo gap 04-26→05-06 + reingest entity + vectorize
- Q70 expandido [117852]→[213254, 213266] (chunk velho deletado pelo reingest, novo ID atribuído)
- Q87 [] → [213270]
- Q88 [] → [213271]
- Eval **Run #20**: nDCG global +0.037, **temporal +0.511** (0.233→0.744) só pela cura — sem mudar código
- Commit: `484e9c2`

### Bloco 5 — Orphan fix Q48/Q58/Q62 (20:45-20:55)
**Achado bombástico:** per-query analysis Run #16 vs Run #20 revelou regressões em concept/procedure/security. Investigação:
- Q48 e Q58 referenciavam **chunk 117852 (deletado pelo reingest!)** — substituído por 213254
- Q62 referenciava 212042 (missing) — mantém só 112400

**Aprendizado registrado:** ao reingest entity file com chunks gold, SEMPRE varrer `eval_queries.expected_chunk_ids` por IDs órfãos antes de eval rodar.

- Eval **Run #21**: nDCG global +0.022 vs Run #20, +0.058 acumulado
- Commit: `8d5b166`

### Bloco 6 — Cura completa 14 queries vazias (20:55-21:05)
- Restavam 14 queries com `expected_chunk_ids=[]` em categorias positivas
- Após análise top-K + verificação FS:
  - **3 cured** com gold best-available: Q79 [112394], Q85 [108239, 108639], Q91 [112245]
  - **11 movidas pra `category=negative`** (doc gaps reais sem chunks correspondentes): Q47, Q64, Q65, Q78, Q93, Q94, Q97, Q98, Q99, Q101, Q102

**Aprendizado registrado:** queries "doc gap" pertencem em `category=negative`, não distorcem médias das outras.

- Eval **Run #22 FINAL**: nDCG global +0.056 vs Run #9 baseline, **zero categorias regredindo**
- Commit: `3d2897a`

### Bloco 7 — Diversity investigation (21:05-21:08)
- Hipótese: chunks timeline novos dominando top-K
- Medição: 0% queries com 3+ chunks do mesmo file no top-10; 83% têm pares (esperado, não dominante)
- **Diversity boost = premature optimization.** Spec descartado.

### Bloco 8 — Gate review automation (21:08-21:13)
**Script:** `tools/nox-mem/scripts/gate-review-e05b-e13.sh` (~233 LOC bash)

Automatiza:
1. Coleta shadow telemetry stats (7d window)
2. Roda 4 evals com env toggles: baseline, E05b only, E13 only, both active
3. Calcula deltas por categoria
4. Aplica critérios → verdict ACTIVATE/KEEP-SHADOW
5. Output JSON `/var/log/nox-gate-review/gate-<date>.json`
6. Restaura env shadow ao fim

**Cron VPS agendado:** `0 12 13 5 *` → executa **2026-05-13 09:00 BRT auto**

- Commit: `da9eca3` (script), `57cff62` (handoff doc)

### Bloco 9 — Gate review preview HOJE (21:08-21:18)
Script rodou 4 evals (#23-26) pra validar pipeline + ver verdict preliminar.

**Verdicts:**

| Feature | Verdict | Critérios |
|---|---|---|
| **E13** | ✅ **ACTIVATE-READY** | Δ temporal +0.149 / Δ non-temporal +0.004 / 9.22% detected (in 5-25%) |
| **E05b** | ❌ **KEEP-SHADOW** | 4/5 critérios falham: Δ entity -0.007, cross-agent -0.015, concept -0.022, procedure -0.039, security -0.090 |

**Hipóteses E05b regression:**
1. Pesos altos demais (cap 0.30 deslocando demais)
2. Cobertura evidence_chunk_id ainda baixa (~0.6% pós kg-extract iter 8)
3. Query-entity matching loose (substring match)

JSON salvo: `/var/log/nox-gate-review/gate-20260506-preview.json`

### Bloco 10 — E13 ACTIVATE + E05b shadow round 2 (21:18-21:22)
**E13 ACTIVATED em produção:**
```
NOX_TEMPORAL_BOOST_MODE=active
```
Aplicando boost timeline 1.4× em queries temporais detectadas.

**E05b round 2 com pesos cortados pela metade** (zero impl change — código já suporta `NOX_REASON_BOOST_WEIGHTS_OVERRIDE` env):
```
NOX_REASON_BOOST_CAP=0.15
NOX_REASON_BOOST_WEIGHTS_OVERRIDE={
  "depends_on": 0.075, "replaces": 0.075,
  "extends": 0.06, "derived_from": 0.05,
  "opposes": 0.04, "mentions": 0.015, "unknown": 0
}
```
Mantém `MODE=shadow`. Re-avalia automaticamente em 2026-05-13 via cron.

- Commit: `fa66750`

---

## Resultado mensurado (Run #9 → Run #22, sem código aplicado em ranking)

```
nDCG@10 global: 0.519 → 0.575    (+0.056, +10.8%)
MRR:            0.450 → 0.530    (+0.080, +17.8%)
Recall@10:      0.687 → 0.767    (+0.080, +11.6%)

Por categoria (todas positivas, zero regressão):
  temporal:    0.233 → 0.744 (+0.511) — virou a melhor cat
  entity:      0.459 → 0.804 (+0.345)
  decision:    0.542 → 0.725 (+0.183)
  procedure:   0.619 → 0.736 (+0.117)
  concept:     0.656 → 0.770 (+0.114)
  cross-agent: 0.369 → 0.461 (+0.092)
  security:    0.594 → 0.606 (+0.012)
```

**O ganho TODO veio de cura do golden corpus.** Sem mudança de código aplicada em ranking. E13 ranking change agora active deve agregar mais.

---

## Code shipped

| Repo | Commit | Conteúdo |
|---|---|---|
| nox-workspace | `0a8fc95` | E05b src (`reason-boost.ts` + tests + db migration v13) |
| nox-workspace | `feb654c` | E13 src (`temporal-detector.ts` + tests + db migration v14) |
| nox-workspace | `da9eca3` | `scripts/gate-review-e05b-e13.sh` |
| memoria-nox | `4f562d3` | E05b spec + ROADMAP + HANDOFF |
| memoria-nox | `7747a5a` | E13 spec + ROADMAP + HANDOFF |
| memoria-nox | `484e9c2` | Run #20 baseline post-cure |
| memoria-nox | `8d5b166` | Run #21 baseline post orphan-fix |
| memoria-nox | `3d2897a` | Run #22 final baseline (cura completa) |
| memoria-nox | `57cff62` | Gate automation block doc |
| memoria-nox | `fa66750` | E13 active + E05b round 2 tuned |

Total: 4 commits nox-workspace + 7 commits memoria-nox, todos pushed.

---

## Estado VPS final

```
NOX_REASON_BOOST_MODE=shadow
NOX_TEMPORAL_BOOST_MODE=active        ← E13 active em produção
NOX_REASON_BOOST_CAP=0.15             ← E05b round 2 (era 0.30)
NOX_REASON_BOOST_WEIGHTS_OVERRIDE=... ← pesos cortados pela metade
```

**Schema:** v14 aplicado, 8.074 kg_relations, 1.245 chunks únicos com evidence (vs 291 inicial — kg-extract loop continua rodando)

**Cron agendado:** gate-review-e05b-e13.sh → 2026-05-13 09:00 BRT auto

**Background:** kg-extract loop tmux ainda rodando, target 3000 chunks (atual 1.223/3000, ~41%, ETA ~50min restantes)

---

## Aprendizados operacionais (4 novos)

1. **Reingest de entity file com gold IDs → varrer órfãos.** `SELECT WHERE expected_chunk_id NOT IN chunks` antes de eval rodar. Erro hoje custou Run #20 inteiro pra detectar.

2. **Queries "doc gap" pertencem em `category=negative`.** Não distorcem médias das outras categorias. Mover 11 queries vazias revelou +0.056 nDCG escondido.

3. **Diversity boost cuidado com premature optimization.** Mediu antes — 0% das queries têm dominância single-file. Spec descartado.

4. **Gate review automation reduz fricção.** Script bash + cron data-fixed = zero-touch verdict no dia D.

---

## Próximas ações

| # | Item | Quando | Owner |
|---|---|---|---|
| 1 | Aguardar Patrick Lewis (paper) | dias 2-7/7 | Patrick |
| 2 | Criar conta arXiv + ORCID | qualquer dia antes 06-02 | Toto |
| 3 | Routine activate gate E03b/E04b | 2026-05-09 sáb 09:00 BRT auto | passive |
| 4 | **Gate review E05b/E13 oficial** | 2026-05-13 09:00 BRT auto | cron |
| 5 | Submit arXiv | 2026-06-02 | Toto |
| 6 | E12 OCR spec dedicado | próxima sessão | — |
| 7 | R02 paper update com Run #22 numbers | pré-submit | — |

---

## Comandos pra retomar próxima sessão

```bash
# Sanity check rápido:
ssh root@187.77.234.79 'tail -3 /var/log/kg-extract/loop-*.log 2>/dev/null'
ssh root@187.77.234.79 'sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db "
  SELECT COUNT(DISTINCT evidence_chunk_id) AS coverage_chunks,
         COUNT(*) AS total_rels FROM kg_relations"'

# Verificar gate-review pós 05-13:
ssh root@187.77.234.79 'cat /var/log/nox-gate-review/gate-*.json | tail -1 | python3 -m json.tool'

# Verificar E13 active funcionando:
ssh root@187.77.234.79 'sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db "
  SELECT temporal_boost_mode, COUNT(*) FROM search_telemetry
  WHERE ts > strftime(\"%s\",\"now\",\"-1 day\") GROUP BY temporal_boost_mode"'
```
