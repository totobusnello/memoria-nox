# Q1 LoCoMo Attribution — production-path +112% vs Python re-impl +18.8%

> **Author:** executor-high (research/2026-05-19/q1-attribution)
> **Status:** ACHADO — não atualiza paper §5 (Toto decide o framing)
> **Trigger:** Q1 prod-path measurement (PR #114 era) reportou nDCG@10 = 0.5961
> (+112% vs FTS5 baseline) enquanto a Python re-impl reportou 0.3338 (+18.8%).
> Diferença de ~6× no delta — não compatível com "mesma arquitetura".
> **Datasets analisados:**
> - `paper/publication/results/locomo-production-path-results.json` (n=100, prod TS pipeline via :18803)
> - `paper/publication/results/locomo-hybrid-vs-fts5-summary.md` (n=100, Python re-impl)
> - `paper/publication/results/locomo-fts5-baseline-results.jsonl` (E04 baseline, FTS5 only)

---

## Resumo executivo (3 linhas)

1. **~9 pontos percentuais relativos do gap são apenas metric formula**: prod-path eval usa `idcg = dcg(sorted-rel)` (max possible from retrieved set); Python re-impl usa `idcg = sum(1/log2(i+2) for i in range(|gold|))` (full ideal across all gold). Recomputado, prod cai de 0.5961 → 0.5637.
2. **~60 pontos percentuais relativos vêm de features arquiteturais que a Python re-impl NÃO tem**: query expansion via Gemini (3 FTS5 batches em vez de 1), candidate pool semantic 4× maior, e chunk_text rico (frontmatter + HTML anchor) que dá mais "superfície" pra BM25 casar tokens raros.
3. **Salience e section_boost NÃO contribuem materialmente nesse corpus**: chunks LoCoMo são `chunk_type=eval_locomo` (não está em `BOOST_TYPES`), sem `source_type`, com `section=NULL` (eval files não são entity-format). Logo no scoring multiplicativo ficam neutros (×1.0). A diferença é **arquitetura de retrieval**, não ranking-boost.

---

## 1. Inventário arquitetural — TS prod vs Python re-impl

### 1.1 Pipeline TS produção (`/api/search` :18803)

Cadeia, baseada em `staged-1.6/search-expansion.ts`, `staged-1.7a/edits/search.ts` e `staged-1.6/search-dedup.ts` (snapshot do código que tava na VPS quando o eval rodou em 2026-05-18):

```
query
  │
  ├─ expandQuery() ────► variant 1 (técnica)  + variant 2 (paráfrase)
  │                      via gemini-2.5-flash, JSON schema response
  │                      (timeout 2.5s; falha → só [original])
  │
  ├─ FTS5 batch [original]   bm25(chunks_fts, 1.0, 0.5, 0.5) LIMIT 20
  ├─ FTS5 batch [variant 1]  (mesmo SQL)
  ├─ FTS5 batch [variant 2]  (mesmo SQL)
  ├─ Semantic batch          embedText(query) → sqlite-vec cosine, LIMIT 40
  │                          (perVariantLimit*2 = limit*2*2; limit=20 → 40)
  │
  ├─ RRF fuse(k=60) sobre as 3+1 = 4 batches
  │   score(doc) = Σ 1/(k + rank_i + 1)  per batch
  │
  ├─ Multiplicadores aplicados PRÉ-RRF dentro de cada batch (em search() FTS5
  │   e searchSemantic()):
  │   • BOOST_TYPES chunk_type ∈ {decision,lesson,person,project,pending} → ×2.0
  │   • source_date ≤ 7 dias → ×1.5 (FTS5) ou ×1.2 (semantic)
  │   • TIER_BOOST[tier] (cold/warm/hot/peripheral)
  │   • SOURCE_TYPE_BOOST[source_type] {user_statement:2.0, compiled:1.5, timeline:1.0, external:0.8}
  │
  └─ dedupe(limit) — 4 layers:
      1. max 3 per source_file
      2. Jaccard ≥0.85 prefix-180 char dedup
      3. max 60% por chunk_type
      4. final cap 2 per source_file
```

### 1.2 Pipeline Python re-impl (`locomo_hybrid_eval.py`)

```
query
  │
  ├─ FTS5 batch [original]   bm25(turns_fts) default weights, LIMIT 20
  │                          fts5_escape: OR-join token quotes
  │
  ├─ Semantic batch          embed_one(query, RETRIEVAL_QUERY) → 3072d
  │                          → cosine vs np.stack(corpus_embeddings) L2-normed
  │                          LIMIT 20
  │
  ├─ rrf_fuse(k=60) sobre as 2 batches
  │
  └─ top-10 final
```

### 1.3 Tabela de features matrix

| Feature | TS prod (:18803) | Python re-impl | Impacto esperado no gap |
|---|---|---|---|
| **FTS5 tokenizer** | unicode61 remove_diacritics 2 | unicode61 remove_diacritics 2 | NEUTRO (idem) |
| **BM25 weights** | `bm25(_,1.0,0.5,0.5)` *(args ignorados pra single-col chunks_fts)* | `bm25()` default | NEUTRO (chunks_fts é mono-coluna; pesos extras são no-op) |
| **fts5_escape** | sanitização in-line: strip `[\'"{}()\[\]:*^~&|!]` → tokens livres com espaço | `OR`-join de tokens entre aspas | **DIFERENTE** — produção usa free tokens (implicit AND fts5 default), Python força OR-disjunção. Em queries longas Python recupera *mais* candidatos (recall maior por branch); TS prod fica mais restrito → variant-expansion compensa |
| **Query expansion** | 1 original + 2 variants Gemini → 3 batches FTS5 | nenhum (só original) | **MAJOR** — multiplica chance de bater chunks heterogêneos |
| **Semantic top-K** | `limit*2*2 = 40` (limit=20) | `TOP_K_DENSE = 20` | **MAJOR** — 2× mais candidatos vetoriais antes do RRF |
| **FTS5 top-K** | `limit*2 = 40` por batch (limit=20) | `TOP_K_FTS = 20` | MEDIUM — 2× mais candidatos por batch FTS |
| **RRF k** | 60 | 60 | NEUTRO |
| **RRF #batches** | 4 (3 FTS5 + 1 sem) | 2 (1 FTS5 + 1 sem) | **MAJOR** — 4 batches inflam scores de docs que aparecem em múltiplos rankings |
| **Pre-RRF boost multiplicativo** | Sim (BOOST_TYPES, source_date, TIER_BOOST, SOURCE_TYPE_BOOST) | Não | NULL nesse corpus (eval_locomo não dispara nenhum boost) |
| **Salience formula** (recency × pain × importance) | Shadow-mode default (NÃO aplicada) | N/A | **NULL** — confirmado: NOX_SALIENCE_MODE=shadow |
| **Section_boost** | Aplicado apenas se chunk.section IS NOT NULL | N/A | **NULL** nesse corpus — eval_locomo files não são entity-format, section=NULL |
| **Dedup pós-RRF** | 4-layer (per-file, Jaccard, type-saturation, final-cap) | nenhum | **MEDIUM** — em LoCoMo cada turn é seu próprio source_file (`/tmp/locomo-md/<conv>/<dia>.md`), então per-file cap raramente ativa; Jaccard pode cortar variants near-dup |
| **Chunk text indexed** | Body do .md (excluído frontmatter pelo ingester normal; HTML comment `<!-- locomo_chunk_id=... -->` permanece) | `<speaker>: <text>` puro | MEDIUM — anchor HTML é token raro que ajuda BM25 quando o sample_id aparece na query |
| **Embedding input** | Mesmo body do .md (frontmatter geralmente stripped pelo embed) | Mesmo `<speaker>: <text>` | NEUTRO/baixo |
| **nDCG formula** | `idcg = dcg(sorted-rel-list)` | `idcg = Σ 1/log2(i+2) for i in range(min(|gold|, k))` | **MAJOR métrica** — formula diff explica ~5pp absoluto / ~9% relativo |

---

## 2. Quantificação da diferença de fórmula nDCG

### Diagnóstico (ablation A — só re-aplicar a fórmula da Python re-impl nos mesmos retrieved chunk IDs do prod-path):

| Métrica | Prod-path original | Recomputado c/ locomo_eval formula |
|---|---|---|
| **nDCG@10 agregado**     | 0.5961 | **0.5637** |
| Δ absoluto vs Python (0.3338) | +0.2623 | +0.2299 |
| Δ relativo               | +78.5% | **+68.9%** |

### Per-categoria (mesma transformação):

| Categoria | Prod-path (orig form) | Recomputado (locomo form) | Ratio |
|---|---|---|---|
| single-hop  | 0.6230 | 0.5223 | 0.838 |
| multi-hop   | 0.4609 | 0.4609 | 1.000 |
| temporal    | 0.4662 | 0.4122 | 0.884 |
| open-domain | 0.8462 | 0.8387 | 0.991 |
| adversarial | 0.5842 | 0.5842 | 1.000 |

**Interpretação:**
- multi-hop e adversarial: ratio 1.000 → todas queries dessas categorias tinham `|gold|=1` (formulas convergem)
- single-hop e temporal: ratio ~0.84–0.88 → muitas queries com `|gold|>1`, onde a fórmula prod inflaciona

**Distribuição de gold-set size no eval (n=100):**
- `|gold|=1`: 66 queries (66%) — formulas convergem
- `|gold|≥2`: 34 queries (34%) — onde formulas divergem
- `|gold|` médio: 1.64; mediana: 1

### Onde o gap "real" fica depois da normalização:

| Pipeline | nDCG@10 (locomo formula, n=100) | Δ vs FTS5 baseline (0.2810) |
|---|---|---|
| FTS5 baseline (E04) | 0.2810 | — |
| Python re-impl hybrid | 0.3338 | **+18.8%** |
| Prod-path (recomputado) | **0.5637** | **+100.6%** |

**Conclusão da §2:** mesmo ajustando a fórmula nDCG pra apples-to-apples, prod-path ainda é **+69% relativo acima da Python re-impl**. Logo a fórmula não é o driver dominante — é só ~9pp dos +93pp de diferença relativa.

---

## 3. Decomposição arquitetural — o que realmente explica os ~69% restantes

Os ablations B/C/D (variar TS prod desligando features) **não foram executados** porque exigiriam:
- Rebuild da 2ª instância :18803 com flags experimentais (NOX_RANKING_PRESET=raw_hybrid, NOX_EXPANSION_DISABLED=1, etc — que não existem no código atual)
- Re-rodar 100 queries × ~12s cada = ~20min cada variant × 3+ variants = ~1h VPS budget
- Custo Gemini de re-embed por mudança de chunk_text → fora do orçamento $1

**Análise estática** (leitura do código + impacto teórico, sem rodar):

### 3.1 — Driver primário: **query expansion + RRF multi-batch**

A Python re-impl usa **2 rankings** no RRF. TS prod usa **3 FTS5 + 1 semantic = 4 rankings**.

Mecânica do RRF: `score(doc) = Σ 1/(k + rank_i)`. Um doc que aparece em rank 3 em 3 batches FTS distintos (variantes técnica/paráfrase/original) ganha:
- `3 × 1/(60+3) = 0.0476`

contra Python re-impl onde aparece só no batch original:
- `1 × 1/(60+3) = 0.0159`

A *probabilidade* de um doc aparecer em ≥2 dos 3 FTS5 batches é alta quando as variantes de Gemini são paráfrases (sinônimos preservam matches). Isso constrói uma "votação ponderada": docs que sobrevivem a múltiplas formulações da query sobem.

**Per-categoria:** single-hop e open-domain (queries factuais curtas, vocabulário variado) ganham mais com expansão. Confere com observação:
- single-hop: prod-path 0.6230 vs Python 0.1775 (gap **+251% rel**)
- open-domain: prod-path 0.8462 vs Python 0.4578 (gap **+85% rel**)

Categorias onde a expansão ajuda menos:
- multi-hop: 0.4609 vs 0.4167 (gap só +11%) — porque multi-hop precisa de evidência *distribuída*, expansão de query não compõe inferência cross-turn
- temporal: 0.4662 vs 0.2851 (gap +63%) — Python re-impl tem -1.2% NULL aqui, prod tem ganho real, mas expansão sozinha não resolve queries "quando X aconteceu"

### 3.2 — Driver secundário: **candidate pool 2× maior no semantic**

TS prod chama `searchSemantic(query, perVariantLimit*2)` onde `perVariantLimit = limit*2 = 40`, portanto **80 candidatos semantic** entram no RRF. Python re-impl: 20 candidatos.

Em RRF com k=60, posições 21–80 ainda contribuem `1/(60+21) = 0.0123` até `1/(60+80) = 0.0071` — não trivial. Combinado com FTS5 ranks, isso permite que docs com BM25 fraco mas embedding-cosine forte (paráfrases, sinônimos, conceitos relacionados) "vazem" pra final top-10.

### 3.3 — Driver terciário: **chunk_text rico (HTML anchor) ajuda casamento BM25 raro**

Cada chunk LoCoMo na prod tem `<!-- locomo_chunk_id=conv-26::D9:14 -->` no final. Quando uma query menciona um identificador raro (ex: "conv-26", "D9", número específico), BM25 dispara strongly. Em queries que não mencionam, esse anchor é noise tokenizado neutro.

**Magnitude estimada:** baixa (a maioria das queries LoCoMo é natural-language, sem `conv-X` literal), mas pode adicionar 1-3% relativo em queries adversariais que copiam strings do contexto.

### 3.4 — Drivers NULL nesse corpus

- **`SOURCE_TYPE_BOOST`**: chunks têm `source_type=NULL` → multiplicador = 1.0 (default `?? 1.0`)
- **`BOOST_TYPES` chunk_type**: `eval_locomo` ∉ `{decision,lesson,person,project,pending}` → ×1.0
- **`SECTION_BOOST`** (compiled/frontmatter/timeline): eval_locomo não passa por `ingestEntityFile()`, então `section=NULL` → ×1.0
- **`TIER_BOOST`**: chunks novos default `tier=peripheral` → tipicamente 1.0
- **Salience formula** (`recency × pain × importance`): `NOX_SALIENCE_MODE=shadow` na VPS atual → não aplicada ao ranking, só logada em `/api/health.salience`
- **`source_date ≤ 7 dias`** boost: chunks foram ingeridos 2026-05-18, query rodada 2026-05-18 → todos batem o boost? **Possivelmente sim**, mas todos batem igualmente → não cria diferenciação interna no ranking, só infla scores absolutos uniformemente

**Sanity:** se TIER_BOOST e source_date boost fossem dominantes, o ranking interno ficaria *idêntico* (todos chunks recebem o mesmo multiplicador) → RRF rank seria igual ao do FTS5 puro. Não explica diferenciação.

---

## 4. Tabela de contribuições (estimadas, não rodadas)

> ⚠️ **Caveat:** ablations B/C/D não foram executados. Esta tabela é decomposição *baseada em análise de código + recomputação da formula nDCG no per_query existente*, não medida empírica. Próximos passos §5 listam o que rodar pra confirmar.

| Feature acumulada | nDCG@10 estimado (n=100) | Δ relativo cumulativo vs FTS5 0.2810 | Contribuição absoluta |
|---|---|---|---|
| FTS5 only (E04 baseline) | 0.2810 | — | — |
| + Gemini semantic dense | ~0.32 | +14% | ~+0.04 |
| + RRF k=60 fusion | 0.3338 (Python re-impl medido) | **+18.8%** (medido) | ~+0.01 |
| + Query expansion (3 FTS5 batches) | ~0.45–0.50 (est.) | +60–80% (est.) | ~+0.12–0.17 |
| + Semantic pool 2× (40→80 candidates) | ~0.50–0.55 (est.) | +80–95% (est.) | ~+0.05 |
| + Chunk_text frontmatter/anchor | ~0.51–0.56 (est.) | +82–100% (est.) | ~+0.01–0.02 |
| + Dedup pós-RRF | ~0.51–0.56 (est., neutral em LoCoMo) | idem | ~0 |
| **Prod-path medido (locomo formula)** | **0.5637** | **+100.6%** | — |
| + Métrica formula prod (sorted-IDCG) | 0.5961 | **+112%** (atual paper/HANDOFF claim) | +0.032 |

**Fontes de incerteza nas linhas estimadas:**
- Query expansion contribuição é o item mais especulativo — pode ser +50% como pode ser +20%; depende da qualidade das paráfrases Gemini em PT-BR+EN mixed queries, que LoCoMo (EN-only) não testa robustamente
- Semantic pool 2× é provável marginal (lei do retorno decrescente em ranks 20–80)

---

## 5. Conclusão técnica

### O que mudou (sem speculação)

1. **A formula nDCG é diferente entre Python re-impl e prod-path eval.** Prod usa `idcg = dcg(sorted-rel)` (max from retrieved); Python usa `idcg = sum over ideal `|gold|` positions`. Reaplica a Python formula nos retrieved IDs do prod e os números caem de 0.5961 → 0.5637 (-5.4pp absoluto). Gap relativo vs FTS5 baseline cai de +112% pra **+100.6%**.

2. **Mesmo após normalização da formula, prod-path entrega +69% relativo a mais que a Python re-impl.** Esse delta é atribuível a features arquiteturais que a Python re-impl não tem:
   - Query expansion via Gemini (3 FTS5 batches em vez de 1)
   - Candidate pool semantic 2× maior (80 vs 20)
   - RRF sobre 4 rankings em vez de 2 (multi-batch voting amplifica docs que sobrevivem a múltiplas formulações)

3. **Salience formula e section_boost NÃO são fatores nesse corpus.** Eval_locomo chunks não disparam:
   - `BOOST_TYPES` (chunk_type=`eval_locomo` não está no set)
   - `SOURCE_TYPE_BOOST` (source_type=NULL)
   - `SECTION_BOOST` (section=NULL — eval files não são entity-format)
   - Salience formula (shadow-mode default)

### "Implementation matters" insight

O paper/HANDOFF claim **+112% prod vs +18.8% Python re-impl** está numericamente correto **mas mede coisas diferentes**:

- **Python re-impl** mede a *arquitetura mínima* (FTS5 + dense + RRF) sob a métrica mais conservadora (full-ideal IDCG).
- **Prod-path** mede *toda a stack* (expansion + 4-batch RRF + dedup + larger candidate pools) sob uma métrica mais permissiva (sorted-retrieved IDCG).

A defensibilidade do paper §5 depende de qual claim se quer fazer:

- Claim A — "hybrid retrieval (FTS5 + Gemini + RRF) beats FTS5 by X%": usar Python re-impl ou recomputar prod com locomo formula → ~+19% medido / ~+100% reproduzido em prod
- Claim B — "nox-mem production pipeline beats FTS5 by X%": usar prod-path com formula consistente → **+100.6%** (a "+112%" tem o boost da formula diff)

Reviewer Cenário B (prod > Python) na runbook (`locomo_production_path.md` §5) previu exatamente esse caso e listou hipóteses (SECTION_BOOST, retention_days priors, tokenization diff). A análise estática aqui descarta SECTION_BOOST e retention_days; o driver primário é **query expansion**.

### Recomendação ao Toto pra paper §5 (não aplicada, sugestão only)

1. **Reportar prod-path como número principal**, mas:
   - Citar com formula explícita (`idcg = dcg(sorted-rel)`)
   - Mostrar Python re-impl como ablation "arquitetura mínima sem expansion"
   - Citar a *recomputação* do prod com formula da Python re-impl (0.5637, +100.6%) como sanity-check pra reviewer detectar discrepância
2. **Citar query expansion como feature de produção**, não como otimização ad-hoc — a runbook (`locomo_production_path.md`) menciona "boost stacking decision D40" pra discutir esse desambiguamento explicitamente
3. **Não usar "+112%" sem qualificação** — esse número combina (a) arquitetura ampla e (b) formula benevolente. Separar os dois efeitos honra a defensibilidade científica

---

## 6. Próximos passos sugeridos (não execute neste PR)

> Estes são experimentos que **fechariam** a atribuição definitiva. Estimativa: ~3h VPS budget total + $0.30 Gemini.

### 6.1 — Ablation B: prod TS sem query expansion

```bash
# Na 2ª instância :18803, setar expansion_enabled=false em meta:
sqlite3 $EVAL_ROOT/eval.db \
    "INSERT OR REPLACE INTO meta(key,value) VALUES('expansion_enabled','false');"

# Re-rodar harness (mesma n=100, seed=42):
NOX_API_PORT=18803 python3 paper/publication/baselines/locomo_production_path_eval.py
```

**Expected:** nDCG@10 deve cair pra range ~0.40–0.45 (locomo formula) se expansion é o driver de ~50% do gap. Se ficar acima de 0.50, expansion contribui menos que estimado.

### 6.2 — Ablation C: Python re-impl + query expansion mock

Portar `expandQuery()` pra Python (caching o output Gemini por query pra reduzir custo) e re-rodar `locomo_hybrid_eval.py` com 3 FTS5 batches + 1 semantic batch RRF-fused. Compara com prod-path:

```python
# Em locomo_hybrid_eval.py, após search_fts5() original:
variants = expand_query_gemini(question)  # cache em disk
all_fts = [fts_top]
for v in variants:
    all_fts.append(search_fts5(con, v, k=TOP_K_FTS))
dense_top = search_dense(...)
fused = rrf_fuse(all_fts + [dense_top], k=RRF_K, top=TOP_K_FINAL)
```

**Expected:** Python+expansion deve subir pra range 0.45–0.55 (mesma formula). Se chegar perto de 0.5637, **confirma definitivamente** que expansion é o driver primário.

### 6.3 — Ablation D: medir contribuição do candidate pool 2× isoladamente

Re-rodar Python re-impl com `TOP_K_DENSE = 40` (mesmo que TS prod). Compara delta vs `TOP_K_DENSE = 20` baseline.

**Expected:** delta marginal (~+2–5pp absoluto) confirmaria que pool size é secundário.

### 6.4 — Auditar a formula nDCG no production-path eval

A formula em `locomo_production_path_eval.py:139-144` deveria ser substituída pela mesma de `locomo_eval.py:182-188` pra consistency. PR separado, ortogonal a este achado.

Ou alternativamente: **documentar explicitamente** na linha do helper a escolha (sorted-rel IDCG) e o trade-off — isso vira um sanity-check guide pra reviewer.

### 6.5 — Adicionar nDCG formula assertion no CI

Test invariant: `ndcg_at_k` em `locomo_eval.py` e `locomo_production_path_eval.py` devem retornar mesmo número pra casos `|gold|=1`. Bate hoje, mas garantir que não dá drift em futuras edits.

### 6.6 — Re-rodar com gold-aware sampling

Hoje 66% das queries têm `|gold|=1` (sample seed=42). Re-amostrar com stratificação por `|gold|` (ex: 20 cada de `|gold|=1, 2, 3, 4+`) reduziria sensibilidade da agregada à fórmula. Pode ser valioso pro paper se Toto quiser "robust to metric choice" como sub-claim.

---

## Referências cruzadas

- `paper/publication/baselines/locomo_eval.py` — FTS5-only baseline E04, n=100 seed=42 (origem do 0.2810)
- `paper/publication/baselines/locomo_hybrid_eval.py` — Python re-impl (origem do +18.8% / 0.3338)
- `paper/publication/baselines/locomo_production_path_eval.py` — prod-path harness (origem do +112% / 0.5961)
- `paper/publication/baselines/locomo_production_path.md` — runbook Option A (já previu Cenário B prod > Python)
- `paper/publication/baselines/locomo_to_markdown.py` — converter que produz chunk_text rich (frontmatter + anchor)
- `staged-1.6/search-expansion.ts` — Gemini query expansion (1 + 2 variants)
- `staged-1.6/search-dedup.ts` — 4-layer dedup pós-RRF
- `staged-1.7a/edits/search.ts` — pipeline hybrid TS produção (RRF k=60, 3+1 batches)
- `staged-P3/edits/search.ts` — patch temporal (asOf/changedSince hard filters; ortogonal a este eval)
- `paper/publication/results/locomo-production-path-results.json` — raw per-query data analisada
- `paper/publication/results/locomo-hybrid-vs-fts5-summary.md` — Python re-impl summary

---

*Autoria: executor-high (research/2026-05-19/q1-attribution), 2026-05-19.*
*Status: achado documentado. Toto decide framing pro paper §5 e quais ablations B/C/D rodar.*
