# R01a — Eval Harness Skeleton

> Schema v11 + tabela `eval_queries` + métricas nDCG@10/MRR/Recall@k + CLI + JSONL output.
> Foundation pra medir delta de qualquer mudança de ranking (E05, E10, D01) cientificamente — baseline-first.

**Status:** Proposto (design spec, impl scheduled pós-G03 05-02)
**Data:** 2026-04-27
**ID novo:** R01a (parte do split R01a/R01b/R01c — ver `docs/ROADMAP.md §4`)
**ID antigo:** W2.1 (Wave 2.1 do plano v1.6)
**Vision §:** §11 Wave 2
**Esforço estimado:** 4-6h (greenfield 0.7×)
**Dependências:** F01 corpus ready (✅ DONE)
**Bloqueia:** R01b curadoria + R01c baseline + E05 ranking active + E10 candidate
**Cross-ref:** `docs/ROADMAP.md` (R01a row), `docs/DECISIONS.md` (baseline-first principle), `docs/VISION.md §11`

---

## Problema

Atualmente medimos qualidade de busca por **smoke tests manuais** (`nox-mem search "query" --hybrid`) e por **olhômetro** (top-3 batem com expectativa). Quando E05 ativar edge typing FULL, ou E10 aplicar consolidation merge, ou eventualmente D01 plugar cross-encoder reranker, **não temos como medir delta de qualidade objetivamente**.

Sem harness:
- "ficou melhor" vira opinião — não mensurável
- Regressões silenciosas passam (uma mudança pode subir recall em 5 queries e baixar em 8 sem ninguém notar)
- Paper v2 (R02) precisa de números reais — sem harness, não escreve
- Trigger D01 (Q5 reranker) é "nDCG≥0.6" — sem harness, nunca dispara

**Baseline-first** (princípio arquitetural em DECISIONS.md): qualquer mudança que afete ranking deve ter baseline mensurada **antes** de ser aplicada. R01a destrava esse princípio operacionalmente.

---

## Solução: 3 camadas

### Arquitetura

```
INPUTS
─────────────────────────────────────────────────────────
  golden_queries.jsonl     →  CLI `nox-mem eval golden import`
  (50 queries curadas         (R01b — curadoria humana, spread Jun-Jul)
   por R01b)
       │
       ▼
  ┌────────────────────────────────────────────┐
  │  eval_queries (schema v12)                  │
  │  ──────────────────────────────             │
  │  id INTEGER PK                              │
  │  query TEXT NOT NULL                        │
  │  expected_chunk_ids TEXT NOT NULL (JSON[])  │  ← gold standard
  │  difficulty TEXT (easy/medium/hard)         │
  │  category TEXT (entity/concept/temporal/…)  │
  │  added_at TEXT, added_by TEXT               │
  │  notes TEXT                                 │
  └────────────────────────────────────────────┘
       │
       ▼
RUN (CLI: `nox-mem eval run --variant=hybrid|fts|vector|rrf-only`)
─────────────────────────────────────────────────────────
  Para cada query em eval_queries:
    1. Executa search() com variant especificado
    2. Compara ranking com expected_chunk_ids
    3. Calcula nDCG@10, MRR, Recall@10, Precision@5
       │
       ▼
  ┌────────────────────────────────────────────┐
  │  eval_runs (schema v12)                     │
  │  ──────────────────────────────             │
  │  id INTEGER PK                              │
  │  variant TEXT (hybrid/fts/vector/rrf-only)  │
  │  ran_at TEXT NOT NULL                       │
  │  git_sha TEXT (versão do código)            │
  │  schema_version INTEGER                      │
  │  query_count INTEGER                        │
  │  total_duration_ms INTEGER                  │
  │  notes TEXT (e.g., "post-E05-shadow")       │
  └────────────────────────────────────────────┘

  ┌────────────────────────────────────────────┐
  │  eval_results (schema v12)                  │
  │  ──────────────────────────────             │
  │  run_id INTEGER FK eval_runs                │
  │  query_id INTEGER FK eval_queries           │
  │  retrieved_chunk_ids TEXT (JSON[])          │  ← top-10 atual
  │  retrieved_scores TEXT (JSON[])             │
  │  ndcg_at_10 REAL                            │
  │  mrr REAL                                   │
  │  recall_at_10 REAL                          │
  │  precision_at_5 REAL                        │
  │  duration_ms INTEGER                        │
  │  PRIMARY KEY (run_id, query_id)             │
  └────────────────────────────────────────────┘
       │
       ▼
OUTPUT
─────────────────────────────────────────────────────────
  reports/eval/<run_id>-<variant>-<timestamp>.jsonl
  /api/health.evalMetrics  (publica último run de cada variant)
  CLI summary (markdown table) com delta vs baseline
```

---

## Schema v12 (DDL completa)

```sql
-- migrations/0012_eval_harness.sql

CREATE TABLE eval_queries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  query TEXT NOT NULL,
  expected_chunk_ids TEXT NOT NULL,         -- JSON array of chunk IDs
  difficulty TEXT CHECK(difficulty IN ('easy','medium','hard')) DEFAULT 'medium',
  category TEXT,                            -- 'entity', 'concept', 'temporal', 'cross-agent'
  added_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  added_by TEXT,
  notes TEXT,
  UNIQUE(query)
);

CREATE INDEX idx_eval_queries_difficulty ON eval_queries(difficulty);
CREATE INDEX idx_eval_queries_category ON eval_queries(category);

CREATE TABLE eval_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  variant TEXT NOT NULL CHECK(variant IN ('hybrid','fts','vector','rrf-only','custom')),
  ran_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  git_sha TEXT,
  schema_version INTEGER,
  query_count INTEGER NOT NULL,
  total_duration_ms INTEGER,
  notes TEXT
);

CREATE INDEX idx_eval_runs_variant_ran ON eval_runs(variant, ran_at DESC);

CREATE TABLE eval_results (
  run_id INTEGER NOT NULL REFERENCES eval_runs(id) ON DELETE CASCADE,
  query_id INTEGER NOT NULL REFERENCES eval_queries(id) ON DELETE CASCADE,
  retrieved_chunk_ids TEXT NOT NULL,        -- JSON array, top-10
  retrieved_scores TEXT NOT NULL,           -- JSON array of floats
  ndcg_at_10 REAL NOT NULL,
  mrr REAL NOT NULL,
  recall_at_10 REAL NOT NULL,
  precision_at_5 REAL NOT NULL,
  duration_ms INTEGER NOT NULL,
  PRIMARY KEY (run_id, query_id)
);

PRAGMA user_version = 11;
```

**Notas operacionais:**
- `eval_queries` é write-mostly via R01b (humano), read-only no `eval run`
- `eval_runs` + `eval_results` crescem ~50 rows por run; com 1 run/dia = 18.250/ano = trivial
- ON DELETE CASCADE pra runs limpa results órfãos
- Sem `withOpAudit()` — eval não é destrutivo (write-only append)
- **Versão schema:** R01a = v11 (prod alinhado em v10 desde 2026-05-01 PRAGMA bump). v12 reservado pra E05 edge typing FULL se rodar antes de R01a.

---

## CLI design (subcomandos novos)

### `nox-mem eval init`

```bash
nox-mem eval init
# Cria schema v12 (idempotente — usa CREATE IF NOT EXISTS)
# Imprime: "Schema v12 ready. Use 'eval golden import' to seed queries."
```

### `nox-mem eval golden import <file>`

```bash
nox-mem eval golden import golden_queries.jsonl
# Lê JSONL, faz INSERT OR IGNORE em eval_queries
# Imprime: "Imported 5 new, skipped 0 duplicates. Total: 5 golden queries."
```

**JSONL format (`golden_queries.jsonl`):**
```jsonl
{"query":"como funciona o monkey-patch do Issue 62028","expected_chunk_ids":[1234,5678],"difficulty":"hard","category":"entity","notes":"Critical operational knowledge"}
{"query":"qual modelo Gemini usar pra KG extraction","expected_chunk_ids":[890],"difficulty":"easy","category":"decision","notes":"flash-lite default"}
{"query":"o que faz withOpAudit","expected_chunk_ids":[2345,2346,2347],"difficulty":"medium","category":"entity","notes":"audit log + atomic snapshot"}
```

### `nox-mem eval run [--variant=hybrid] [--git-sha=auto] [--note="..."]`

```bash
nox-mem eval run --variant=hybrid --note="post-E05-shadow-2026-05-15"
# Para cada query em eval_queries:
#   1. Executa search(query, variant=hybrid, k=10)
#   2. Calcula nDCG@10, MRR, Recall@10, Precision@5
#   3. INSERT em eval_runs + eval_results
# Imprime tabela markdown:
#
#   ## Eval Run #42 (variant=hybrid)
#   - Ran: 2026-05-15 14:32:01
#   - Git: abc1234
#   - Queries: 50
#   - Duration: 12.3s
#
#   | Metric | Value | Δ vs prev hybrid |
#   |---|---|---|
#   | nDCG@10  | 0.621 | +0.043 |
#   | MRR      | 0.587 | +0.021 |
#   | Recall@10| 0.812 | +0.018 |
#   | Prec@5   | 0.534 | +0.012 |
#
#   By difficulty: easy=0.78, medium=0.61, hard=0.43
#   By category: entity=0.71, concept=0.55, temporal=0.49
#
# Exporta JSONL: reports/eval/42-hybrid-2026-05-15T14:32:01.jsonl
```

### `nox-mem eval compare <run_id_a> <run_id_b>`

```bash
nox-mem eval compare 41 42
# Diff entre dois runs (mesmo variant ou diferentes)
# Imprime queries que melhoraram + queries que regrediram
# Útil pra "vale a pena ativar E05?" decision
```

### `nox-mem eval list [--variant=hybrid] [--limit=10]`

```bash
nox-mem eval list --variant=hybrid --limit=5
# Tail dos últimos N runs
# Mostra: id, ran_at, git_sha, ndcg_at_10 médio, recall_at_10 médio
```

---

## HTTP API endpoint

`GET /api/health.evalMetrics` retorna:

```json
{
  "evalMetrics": {
    "lastRun": {
      "id": 42,
      "variant": "hybrid",
      "ran_at": "2026-05-15T14:32:01.000Z",
      "git_sha": "abc1234",
      "ndcg_at_10": 0.621,
      "mrr": 0.587,
      "recall_at_10": 0.812,
      "precision_at_5": 0.534,
      "query_count": 50
    },
    "byVariant": {
      "hybrid":  { "ndcg_at_10": 0.621, "ran_at": "2026-05-15T14:32:01Z" },
      "fts":     { "ndcg_at_10": 0.418, "ran_at": "2026-05-15T14:30:12Z" },
      "vector":  { "ndcg_at_10": 0.502, "ran_at": "2026-05-15T14:31:45Z" }
    },
    "delta24h": {
      "hybrid": { "ndcg_at_10_delta": +0.012 }
    }
  }
}
```

Dashboard agent-hub-dashboard pode plotar trend via polling esse endpoint.

---

## Métricas (formulações exatas)

### nDCG@10 (Normalized Discounted Cumulative Gain)

Para query `q`, ranking retornado `R = [r1..r10]`, gold standard `G = expected_chunk_ids`:

```
DCG@10  = Σ (i=1..10) [ rel(ri) / log2(i+1) ]
IDCG@10 = Σ (i=1..min(|G|, 10)) [ 1 / log2(i+1) ]   (assume rel binária)
nDCG@10 = DCG@10 / IDCG@10   (clamped to [0,1])

rel(ri) = 1 if ri ∈ G else 0
```

### MRR (Mean Reciprocal Rank)

```
For first ri ∈ G in R:
  RR = 1 / rank(ri)
If no gold in R:
  RR = 0
MRR = mean over all queries
```

### Recall@10

```
Recall@10 = |{ri ∈ R[0..10] : ri ∈ G}| / |G|
```

### Precision@5

```
Precision@5 = |{ri ∈ R[0..5] : ri ∈ G}| / 5
```

---

## 5 seed golden queries (committed na R01a, não esperar R01b)

Estas 5 ficam em `seed_queries.jsonl` no repo, importadas no init:

```jsonl
{"query":"como funciona monkey-patch do Issue 62028 do OpenClaw","expected_chunk_ids":[],"difficulty":"hard","category":"entity","notes":"Hard: requer lookup multi-arquivo CLAUDE.md + INCIDENTS"}
{"query":"qual modelo Gemini usar como default no nox-mem","expected_chunk_ids":[],"difficulty":"easy","category":"decision","notes":"flash-lite — regra crítica 4 do CLAUDE.md"}
{"query":"o que faz withOpAudit e quando usar","expected_chunk_ids":[],"difficulty":"medium","category":"entity","notes":"src/lib/op-audit.ts wrapper VACUUM INTO snapshot"}
{"query":"como ativar salience em produção","expected_chunk_ids":[],"difficulty":"medium","category":"procedure","notes":"G01 gate, scripts/activate-salience.sh"}
{"query":"qual a diferença entre graphify e nox-mem KG","expected_chunk_ids":[],"difficulty":"hard","category":"concept","notes":"VISION.md §1 — graphify extrai, nox-mem armazena"}
```

`expected_chunk_ids: []` = curador R01b vai preencher após R01a init. R01a apenas garante schema + format. R01b validation: rodar `nox-mem search` e selecionar manualmente os top-3 chunks corretos pra cada query.

---

## Migração + safety

- **Idempotente:** `eval init` usa `CREATE TABLE IF NOT EXISTS` — re-rodar não quebra
- **Sem op destrutiva:** `withOpAudit()` não necessário (write-only append a 3 tabelas novas)
- **Backup:** snapshot diário 02:00 já cobre (eval_runs/eval_results em mesmo `nox-mem.db`)
- **Schema invariant canary novo (F05 extension):** `SELECT user_version FROM pragma_user_version` deve ser `>= 11` após migration; se cair pra `< 11` Discord alert
- **Rollback path:** `DROP TABLE eval_results; DROP TABLE eval_runs; DROP TABLE eval_queries; PRAGMA user_version = 10;` — destrutivo mas low-risk (dados sintéticos eval, não memória core)

---

## Critérios de aceitação (R01a entregue)

- [ ] Schema v11 deployado em produção (`PRAGMA user_version = 11`)
- [ ] 3 tabelas criadas com CHECK constraints + FKs
- [ ] CLI subcomandos `eval init`, `eval golden import`, `eval run`, `eval compare`, `eval list` funcionais
- [ ] Métricas nDCG@10/MRR/Recall@10/Precision@5 testadas com 5 seed queries (manualmente curadas)
- [ ] `/api/health.evalMetrics` retorna JSON conforme spec
- [ ] JSONL output em `reports/eval/<run_id>-<variant>-<timestamp>.jsonl`
- [ ] Unit tests pra cálculo de nDCG (3 casos: perfect ranking, reverse ranking, partial overlap)
- [ ] CLI help atualizado (`nox-mem eval --help`)
- [ ] Documentação em `docs/ARCHITECTURE.md` (seção Eval Harness adicionada)
- [ ] Schema v12 documentado em `CLAUDE.md` (regra crítica nova ou append em existing)
- [ ] Audit final via `code-reviewer` agent (sem CRITICAL/HIGH novos)

**Não inclui (escopo R01b/R01c):**
- ❌ Curadoria de 50 golden queries reais com expected_chunk_ids preenchidos (= R01b, 8-10h)
- ❌ Baseline FTS-only vs hybrid + publish (= R01c, 1-2h pós-curadoria)
- ❌ Cross-encoder reranker (= D01, gated nDCG≥0.6)
- ❌ A/B testing infrastructure (futuro, não Wave 2)

---

## Estimativa por etapa

| Etapa | Esforço | Notas |
|---|---|---|
| Schema migration v12 + DDL | 0.5h | trivial via better-sqlite3 |
| CLI scaffolding (`eval` subcommand router) | 0.5h | match existing `kg-build`, `cross-search` patterns |
| `eval init` + `eval golden import` | 0.5h | INSERT OR IGNORE simples |
| `eval run` (busca + métricas) | 1.5h | core do trabalho |
| Métricas (nDCG/MRR/Recall/Precision) | 0.5h | + 3 unit tests |
| `eval compare` + `eval list` | 0.5h | reads simples |
| HTTP endpoint `/api/health.evalMetrics` | 0.3h | append a /api/health response |
| JSONL export | 0.2h | trivial |
| Unit tests (nDCG/MRR edge cases) | 0.3h | node:test |
| Docs (ARCHITECTURE + CLAUDE.md) | 0.5h | |
| Smoke test + code-review | 0.5h | |
| **TOTAL** | **~5h** | encaixa em 4-6h estimate ROADMAP |

---

## Dependencies & next steps

**Dependências (todas DONE):**
- F01 query logging (search_telemetry table) — DONE 2026-04-25
- F03 ingest-router (chunks canonical) — DONE 2026-04-26
- F05 canary invariants (schema version check) — DONE 2026-04-26

**Destravar após R01a:**
- R01b curadoria 50 golden queries (8-10h spread Jun-Jul)
- R01c baseline FTS-only vs hybrid (1-2h pós-R01b)
- E05 ranking active (precisa baseline pra medir delta)
- E10 candidate consolidation (gated nDCG≥0.6)
- D01 trigger antecipado (2 PRs mal-rankeadas registráveis)

**Ordem de execução pós-G03 (05-02):**
1. R01a impl (4-6h) — Maio
2. R01b curadoria (paralela, spread Jun-Jul)
3. E05 edge typing (8-10h Maio-Jun, gated em R01a baseline)
4. R01c baseline publish (Jul)
5. R02 paper v2 (Ago)

---

## Risks & mitigations

| Risco | Mitigação |
|---|---|
| nDCG cálculo wrong (sutil em log2) | 3 unit tests com casos canônicos (perfect/reverse/partial) |
| `eval run` lento (50 queries × hybrid search) | Hybrid p95 ~150ms → 50 × 150 = 7.5s aceitável; se >30s, paralelizar com Promise.all batch=10 |
| `expected_chunk_ids` ficam stale após reindex | R01b curadoria documenta processo de reset (e.g., `eval golden refresh-ids` future feature) |
| Schema v12 conflita com schema v11+ futuro | Hoje schema é v10, v11 reservado pra E05 (kg_relations). v12 reservado aqui. Coordenar antes de mergear |
| 5 seed queries não cobrem corner cases | OK — seed apenas valida pipeline, R01b traz cobertura real |
| Eval rodando durante reindex causa false-low metrics | `eval run` checa `/api/health.indexing == false` antes de iniciar; aborta com erro se indexing ativo |

---

## Open questions (decidir antes da impl)

1. **Variant `rrf-only`:** vale ter? RRF já é parte do hybrid; isolá-lo requer flag interno em search engine. **Recomendação:** começar SEM, adicionar se valor empírico aparecer.
2. **Negative queries (queries que devem retornar zero gold):** vale ter category="negative"? **Recomendação:** sim, R01b curadoria pode incluir 5-10 negativos pra validar specificity.
3. **Cross-agent eval:** roda em main DB ou também em personas (nox/atlas/...)? **Recomendação:** main DB only no R01a. Cross-agent é Wave 3 problem.
4. **Time-decay no nDCG:** chunks mais recentes deveriam pesar mais? **Recomendação:** não — rel binária mantém eval limpo; time-decay já está no ranking, eval mede output do ranking.

---

## Cross-refs finais

- **`docs/ROADMAP.md`** §4 (R01a row) — timeline + capacity tracker
- **`docs/DECISIONS.md`** — princípio "baseline-first" + "shadow-mode obrigatório"
- **`docs/VISION.md`** §11 Wave 2 — visão estratégica do harness
- **`docs/ARCHITECTURE.md`** — append seção "Eval Harness" pós-impl
- **`CLAUDE.md`** — append regra crítica nova ou nota em existing rules
- **`plans/_archive/2026-04-25-integration-roadmap-v1.6.md`** §W2.1 — origem histórica do item
