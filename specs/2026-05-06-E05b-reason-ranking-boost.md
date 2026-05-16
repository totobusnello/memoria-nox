# E05b — Reason-aware Ranking Boost

> Phase 2 do edge typing: usa `kg_relations.relation_reason` (já populado pela Phase 1) como sinal aditivo de ranking. Chunks ligados a entities via relations estruturais (`depends_on`, `replaces`, `extends`) ganham boost; relations fracas (`mentions`) contribuem pouco; `unknown` é ignorado. Aditivo, com cap, shadow-mode obrigatório.

**Status:** Design spec (CANDIDATE)
**Data:** 2026-05-06
**ID:** E05b (Phase 2 do split E05 Phase 1 ✅ DONE 2026-05-02 / Phase 2 = este spec)
**ID antigo:** parte de W1.1 (Edge typing FULL)
**Vision §:** §11 Wave 1 + §8 Affective Ranking (extension)
**Esforço estimado:** 30min spec + 1.5h impl + 30min tests + 7d shadow wall + 0.3h activate
**Dependências:**
- ✅ E05 Phase 1 (`relation_reason` populado em `kg_relations`, Gemini 4-tupla classifica novos)
- ✅ G02 section_boost active (pipeline com aditivos comprovado)
- ✅ R01c baseline Run #9 (nDCG 0.519, weak cats mapeadas)
**Bloqueia:**
- Lift em weak categories `entity` (0.459) e `cross-agent` (0.369)
- Possível destrava do D01 cross-encoder (gated nDCG≥0.6) se E05b subir baseline
**Cross-ref:**
- `docs/ROADMAP.md` E05 row + §10 "Wave 1 restante"
- `docs/HANDOFF.md` linha 1068 ("ainda só surface no `<vault-facts>` block; não influencia ranking ainda")
- Regra crítica `CLAUDE.md` #5: boost aditivo, nunca multiplicativo empilhável
- `MEMORY.md:feedback_shadow_mode_for_ranking_changes.md`

---

## Problema

R01c Run #9 (n=50 hybrid) por categoria:

| Category | nDCG@10 | Δ vs target 0.6 |
|---|---|---|
| concept | 0.656 | ✅ |
| procedure | 0.619 | ✅ |
| security | 0.594 | -0.006 |
| decision | 0.542 | -0.058 |
| **entity** | **0.459** | **-0.141** ⚠️ |
| **cross-agent** | **0.369** | **-0.231** ⚠️ |
| **temporal** | **0.233** | **-0.367** ⚠️ |

Entity-bound queries falham porque ranking atual (RRF + salience + section_boost) trata todas as relations chunk↔entity como iguais. `kg_relations.relation_reason` já distingue 7 tipos desde Phase 1, mas o sinal só aparece como anotação `[reason]` no `<vault-facts>` block — **não chega ao scoring**.

D01 cross-encoder reranker (Qwen3 local) resolveria, mas está bloqueado pelo próprio gate nDCG≥0.6 (galinha-e-ovo). E05b é o caminho barato pra subir nDCG sem D01: reusa metadata já classificada, sem novo modelo, sem latência cross-encoder.

---

## Solução: reason boost aditivo com cap

### Fórmula

```
Hoje:    score = RRF(BM25, semantic) × salience × section_boost
E05b:    score = RRF(BM25, semantic) × salience × section_boost
                + min(reason_boost(chunk, query), CAP)        ← aditivo
```

`reason_boost` soma pesos das relations que conectam **entities do chunk** ↔ **entities da query**.

### Pesos por reason (v1)

| reason | weight | racional |
|---|---|---|
| `depends_on` | 0.15 | dependência estrutural — sinal forte (A depende de B → A relevante quando B na query) |
| `replaces` | 0.15 | substituição — sinal forte (A replaces B → A é o canônico atual) |
| `extends` | 0.12 | extensão — sinal médio-forte (A extends B → A inclui B+) |
| `derived_from` | 0.10 | derivação — sinal médio |
| `opposes` | 0.08 | contraste — útil em queries comparativas |
| `mentions` | 0.03 | menção solta — sinal fraco mas não-zero |
| `unknown` | 0.00 | ignorar (não classificado) |

**CAP = 0.30** (~30% do range típico de score normalizado pós-RRF). Evita runaway em entities super-conectadas (ex: "Toto" tem >50 relations).

Pesos são **constants em código** v1; override via `NOX_REASON_BOOST_WEIGHTS_OVERRIDE` (JSON env var) pra calibração shadow.

### Match logic

```typescript
// src/lib/reason-boost.ts
export function reasonBoost(
  chunkId: number,
  query: string,
  cfg: ReasonBoostConfig
): { boost: number; relations_used: number } {
  if (cfg.mode === 'disabled') return { boost: 0, relations_used: 0 };

  // 1. Entities do chunk: índice chunk_entities (já existe via kg ingest)
  const chunkEntities = getChunkEntities(chunkId);  // [entity_id, ...]
  if (chunkEntities.length === 0) return { boost: 0, relations_used: 0 };

  // 2. Entities da query: NER simples (substring match contra kg_entities.name)
  const queryEntities = resolveQueryEntities(query);
  if (queryEntities.length === 0) return { boost: 0, relations_used: 0 };

  // 3. Relations conectando os dois conjuntos (bidirectional)
  const rels = db.prepare(`
    SELECT relation_reason
    FROM kg_relations
    WHERE (source_entity_id IN (?) AND target_entity_id IN (?))
       OR (target_entity_id IN (?) AND source_entity_id IN (?))
  `).all(chunkEntities, queryEntities, chunkEntities, queryEntities);

  // 4. Soma pesos com cap
  const raw = rels.reduce((sum, r) => sum + (cfg.weights[r.relation_reason] ?? 0), 0);
  const boost = Math.min(raw, cfg.cap);

  return { boost, relations_used: rels.length };
}
```

**v1 query-entity resolution = substring match** (`SELECT id FROM kg_entities WHERE LOWER(?) LIKE '%' || LOWER(name) || '%'`). v2 (futuro): NER + alias table.

### Pipeline integration

```typescript
// src/search.ts (após RRF + salience + section_boost)
const cfg = readReasonBoostConfig();  // env vars
const { boost, relations_used } = reasonBoost(chunk.id, query, cfg);

// Score final
let finalScore = baseScore;  // já inclui salience × section_boost
if (cfg.mode === 'active') {
  finalScore = baseScore + boost;
}

// Telemetry sempre logado (shadow + active)
logTelemetry({
  ...,
  reason_boost_applied: boost,
  reason_relations_used: relations_used,
  reason_boost_mode: cfg.mode,
});
```

Em **shadow-mode**: telemetry registra o boost que **seria** aplicado, mas `finalScore = baseScore` (sem mudança visível ao usuário). Permite comparar nDCG hipotético pós-boost vs atual.

---

## Env vars

| Var | Default | Valores |
|---|---|---|
| `NOX_REASON_BOOST_MODE` | `disabled` | `disabled` / `shadow` / `active` |
| `NOX_REASON_BOOST_CAP` | `0.30` | float ≥ 0 |
| `NOX_REASON_BOOST_WEIGHTS_OVERRIDE` | unset | JSON `{"depends_on": 0.20, ...}` |

Validação: parse falho → fail-open (usa defaults), warn em log.

---

## Schema migration v13

`search_telemetry` ganha 2 colunas (additive, defaults seguros):

```sql
ALTER TABLE search_telemetry ADD COLUMN reason_boost_applied REAL DEFAULT 0;
ALTER TABLE search_telemetry ADD COLUMN reason_relations_used INTEGER DEFAULT 0;
-- reason_boost_mode já capturado via env_snapshot (existing column)
```

`PRAGMA user_version = 13` + `meta.schema_version = 13` (alignment regra db.ts).

---

## CLI

Sem subcomando novo. Tudo via env. Inspect via:

```bash
$ nox-mem search "schema v11" --debug
[reason-boost] mode=shadow boost=0.18 relations=3 reasons=[depends_on,extends,mentions]
 #1: ...
```

Flag `--debug` faz `console.error()` do payload de boost por chunk top-K.

---

## Telemetria & análise shadow

Após 7d shadow (~2026-05-13):

```sql
-- Distribuição de boost aplicado
SELECT
  ROUND(reason_boost_applied, 2) AS boost_bucket,
  COUNT(*) AS hits
FROM search_telemetry
WHERE reason_boost_mode = 'shadow'
  AND ts > strftime('%s', 'now', '-7 days')
GROUP BY boost_bucket
ORDER BY boost_bucket DESC;

-- % de queries com boost ≠ 0
SELECT
  100.0 * SUM(CASE WHEN reason_boost_applied > 0 THEN 1 ELSE 0 END) / COUNT(*) AS pct_boosted
FROM search_telemetry
WHERE reason_boost_mode = 'shadow';

-- Avg relations_used por query (sanity check NER simples)
SELECT AVG(reason_relations_used), MAX(reason_relations_used)
FROM search_telemetry WHERE reason_boost_mode = 'shadow';
```

Roda **R01c shadow** (eval batch n=50 com `NOX_REASON_BOOST_MODE=shadow` + flag preview):

```bash
nox-mem eval run --variant=hybrid --reason-boost=preview --note="E05b shadow review"
nox-mem eval compare 9 <new_run_id>  # delta por categoria
```

---

## Activate gate

7d wall + critérios:

| Critério | Threshold | Origem |
|---|---|---|
| Δ nDCG@10 entity | ≥ +0.03 | weak cat alvo |
| Δ nDCG@10 cross-agent | ≥ +0.03 | weak cat alvo |
| Δ nDCG@10 concept (strong) | ≥ -0.01 | no regressão |
| Δ nDCG@10 procedure (strong) | ≥ -0.01 | no regressão |
| Δ Recall@10 global | ≥ -0.01 | no regressão |
| % queries com boost ≠ 0 | ≥ 20% | sinal não é dead code |
| 0 search timeouts | sempre | hard gate |

**Pass:** flip `NOX_REASON_BOOST_MODE=active` + restart `nox-mem-api` + R01c re-baseline + commit telemetria.

**Fail:** keep shadow, ajustar pesos via `WEIGHTS_OVERRIDE`, novo round 7d.

**Catastrophic** (qualquer strong cat -3pp+): rollback imediato `MODE=disabled`, investigar.

---

## Tests

`test/reason-boost.test.ts` (~10 cases):

1. `reasonBoost()` retorna 0 se mode=disabled
2. Soma de pesos respeita CAP (3× depends_on = 0.45 → cap 0.30)
3. Override via JSON env var aplica
4. Override com JSON inválido → fail-open warn (defaults)
5. Chunk sem entities → boost 0
6. Query sem entities → boost 0
7. Relation `unknown` contribui 0 mesmo se presente
8. Bidirectional match (chunk_entity como source OU target)
9. Telemetry logged em shadow + active
10. Mode=shadow não muda finalScore

`test/eval.test.ts` extensão: smoke 1 query entity-bound, valida boost ≠ 0 em shadow log.

---

## Performance

- `getChunkEntities(chunkId)` — índice `chunk_entities(chunk_id)` se existir; senão SELECT em `kg_relations` é O(rels per entity). Cap chunks top-K = 10, então ~10 calls por search.
- `resolveQueryEntities(query)` — 1 SELECT por query (FTS5 sobre `kg_entities.name` ou substring scan ~400 entities).
- Esperado: <5ms overhead por search (validar via EXPLAIN QUERY PLAN + benchmark shadow).

Se latência p95 sobe >10ms: backout shadow, otimizar (LUT em memória, prepared statements cached).

---

## Risk register

| # | Risco | Probabilidade | Mitigação |
|---|---|---|---|
| 1 | NER simples (substring) tem falsos positivos pra entities curtas (ex: "Q5", "v3") | médio | exclude min length 3 chars; alias table v2 |
| 2 | Pesos arbitrários não calibrados | alto | shadow 7d + grid search via WEIGHTS_OVERRIDE; R01c por categoria |
| 3 | Strong cats regridem por dominância de boost | baixo (cap 0.30) | gate hard regression -1pp |
| 4 | Queries temporais não melhoram (não bound a entities) | alto (esperado) | E05b cobre entity/cross-agent only; temporal precisa outra solução |
| 5 | 464 relations ainda 'unknown' (Gemini não rodou ainda em todas) | médio | rodar `kg-build incremental` antes do shadow começar; 'unknown' não contribui mas reduz cobertura |
| 6 | DB lock em SELECT pesado durante search | baixo | índices preparados; PRAGMA journal_mode=WAL já ativo |

---

## Rollout

| Step | Esforço | Owner | Quando |
|---|---|---|---|
| 1. Spec review (este doc) | ~10min | Toto | hoje |
| 2. `kg-build incremental` para classificar 464 unknown residuais | ~30min (Gemini call) | Claude | pré-impl |
| 3. Impl `src/lib/reason-boost.ts` + plug em `src/search.ts` | ~1.5h | Claude | sessão de impl |
| 4. Schema migration v13 (search_telemetry +2 cols) | ~15min | Claude | mesma sessão |
| 5. Tests (`test/reason-boost.test.ts` ~10 cases) | ~30min | Claude | mesma sessão |
| 6. Deploy shadow VPS + smoke 5 queries entity-bound | ~10min | Claude | mesma sessão |
| 7. Wait 7d (~2026-05-13) | passive | — | — |
| 8. Run R01c shadow + análise telemetria + activate decision | ~30min | Claude+Toto | 2026-05-13 |
| 9. Activate (se gate pass) + R01c re-baseline + commit | ~15min | Claude | 2026-05-13 |

**Total esforço ativo: ~3h** + 7d wall.

---

## Out of scope (deferred)

- **NER avançado pra query** (alias table, embeddings) — v2 ou D01 territory
- **Pesos por categoria** (depends_on em concept ≠ depends_on em entity) — explorar pós-shadow se gate falhar
- **Boost negativo pra relations contraditórias** (`opposes` como demote) — risco semântico, deferred
- **Multi-hop reasoning** (chunk → entity_A → relation → entity_B → query) — D01/E10 territory
- **Per-tenant pesos** — P01 multi-tenancy

---

## Cruzamento com regras críticas

- ✅ Regra #5: aditivo (não multiplicativo empilhável)
- ✅ Regra `feedback_shadow_mode_for_ranking_changes`: ≥7d shadow obrigatório
- ✅ Regra `feedback_validate_features_with_db_not_logs`: telemetry em search_telemetry, não só logs
- ✅ Regra `feedback_audit_critical_modules_same_session`: code-reviewer + security-reviewer ANTES de fechar sessão de impl

---

## Definition of Done (Phase 2)

- [ ] Spec aprovado por Toto
- [ ] `src/lib/reason-boost.ts` impl + tests 10/10 pass
- [ ] Schema v13 aligned (PRAGMA + meta)
- [ ] Telemetry rodando shadow VPS, ≥100 queries logged
- [ ] R01c shadow run com delta por categoria
- [ ] Activate gate avaliado em 2026-05-13
- [ ] Decisão registrada em `docs/DECISIONS.md`
- [ ] Update `docs/ROADMAP.md` E05 row → `✅ DONE Phase 2` ou `⏸ KEPT-SHADOW`

---

## Gate review history

### 2026-05-06 preview (Round 1) — KEEP-SHADOW

Boost regrediu em 4/6 categorias. Pesos originais agressivos. Decisão: cortar pesos pela metade, Round 2.

### 2026-05-13 auto-cron — **SILENT FAIL**

Cron `0 12 13 5 *` rodou mas script faltava bit executável (`-rw-r--r--`). `Permission denied` foi mascarado por `>> log 2>&1` no cron. 3 dias de silent fail descobertos em 2026-05-16.

**Fixes aplicados 2026-05-16:**
- `chmod +x scripts/gate-review-e05b-e13.sh`
- Bug parser: `json_object(...) GROUP BY` retornava múltiplas linhas → trocado por `json_group_object(...)` (objeto agregado correto)
- Discord alert trap: `trap 'on_error $LINENO' ERR` dispara webhook se exit≠0 (evita silent fail futuro)

### 2026-05-16 manual rerun (Round 2 + post kg-extract focado) — KEEP-SHADOW

**Run #1 (pré kg-extract):**

| Categoria | Δ | Critério | Status |
|---|---|---|---|
| entity | +0.0305 | ≥+0.030 | ✅ margem mínima |
| cross-agent | **-0.0506** | ≥+0.030 | ❌ FAIL |
| concept | -0.0043 | ≥-0.010 | ✅ |
| procedure | +0.0146 | ≥-0.010 | ✅ |
| pct_boosted | 67.07% | ≥20% | ✅ |

Verdict: **KEEP-SHADOW (cross-agent Δ=-0.0506)**.

**Forense cross-agent qid-by-qid (n=4):**

| qid | query | Δ |
|---|---|---|
| 72 | cross-search entre agentes | 0 |
| **76** | **Atlas/Boris comunicam** | **-0.2023** |
| 85 | Lex/Cipher incidents | 0 |
| 86 | workflow Forge code review | 0 |

1 query sozinha (qid=76) carrega -5pp da categoria. Investigação dos top-10 chunks de qid=76:
- Gold chunks `shared/agent-expertise.md` (112536) e `shared/agent-map.md` (112544) com **0 kg_relations** cada
- Chunks não-gold que subiram: 108606 (24 relations), 108639 (5), 108598 (7), 111953 (12)
- **Diagnóstico:** reason_boost amplifica chunks COM relations. Gold sem KG coverage **sempre perde**. Não é bias de pesos — é falta de cobertura.

**Intervenção:** kg-extract focado --limit 100 (cobre cursor 112421 → 112556, incluindo os 16 chunks gold). Custo Gemini: 95 LLM calls + 5 fast-path. +538 relations, +305 entities. ~3min44s.

**Run #2 (pós kg-extract):**

| Categoria | Δ | Critério | Status |
|---|---|---|---|
| **cross-agent** | **+0.0765** | ≥+0.030 | **✅ resolveu** (era -0.0506) |
| entity | +0.0142 | ≥+0.030 | ❌ era +0.0305 (caiu pra +0.014) |
| concept | -0.0128 | ≥-0.010 | ❌ era -0.0043 |
| **procedure** | **-0.0503** | ≥-0.010 | ❌ regrediu (era +0.0146) |

**Verdict: KEEP-SHADOW (procedure Δ=-0.0503)** — o problema migrou de cross-agent → procedure.

**Forense procedure (n=9):**
- qid=52 "como rodar nox-mem reindex com segurança": 1.0 → 0.6309 (**-37pp sozinha**)
- 7 queries iguais, 0 ganhos
- Padrão: kg-extract trouxe chunks competitivos que deslocaram o topo (1.0) que já estava ótimo

### Conclusão definitiva (Round 2, post-forense + post-kg-extract)

**O problema raiz não é `reason_boost` nem pesos — é falta de poder estatístico no golden set.**

Sample n=4 em cross-agent, n=9 em procedure: 1 query oscilando desloca média 5-20pp. Cada kg-extract focado MOVE qual categoria regride, mas não resolve globalmente (regression-to-mean).

**Decisão arquitetural:**
- ❌ Não tunar pesos (é otimização de ruído)
- ❌ Não rodar mais kg-extract focado (efeito ricochet)
- ✅ **Aguardar golden set expansion n≥30** (pré-req E14, semana 20-23/05)
- ✅ Re-rodar gate review com sample válido em **~2 semanas** (semana 27 mai)
- ✅ Manter KEEP-SHADOW Round 2 (pesos cortados pela metade) até lá

**Side-effect positivo:** 538 relations novas + 305 entities novas no DB. KG coverage 4.92% → ~5.5% após o batch focado. Trabalho não desperdiçado — chunks ficam permanentemente cobertos pro futuro.

### Próxima decisão (auto-trigger semana 27/05)

Re-rodar gate review com golden set expandido (≥30 queries, ≥10 cross-language). Aplicar decision matrix:

| Cenário pós-n≥30 | Decisão |
|---|---|
| Gate passa (todos critérios verdes) | ACTIVATE |
| Gate falha mas distribuição uniforme (sem 1 query carregando) | SHADOW Round 3 com tuning informed por evidência |
| Gate falha com mesmo padrão regression-to-mean | CUT (E14 multi-alavanca substitui) |
