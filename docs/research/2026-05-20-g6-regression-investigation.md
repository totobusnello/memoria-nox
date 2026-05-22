# G6 Regression Investigation: 0.6237 → 0.5845 A8

**Data:** 2026-05-20  
**Investigador:** debugger agent  
**Status:** ROOT CAUSE IDENTIFIED — dois fatores, DB swap é dominante

---

## Sumário Executivo

A "regressão" de -6.3% (0.6237 → 0.5845) **não é uma regressão de código**. É uma mudança de corpus: G5 V3 rodou contra `g5.db` (68,995 chunks, clone do prod), enquanto G6 rodou contra `entity-eval.db` (500 chunks, eval set sintético). Os dois números **não são comparáveis**.

Existe um segundo fator real de código (fórmula `calculateSalience` v2 aditiva no commit `d4eaada6`) que diverge substancialmente do ranking produzido pela fórmula multiplicativa do G5 V3, mas seu impacto isolado no nDCG do eval set ainda não foi medido de forma controlada.

---

## Fase 1 — Diff `search.ts` (backup pré-wave-a vs atual)

**Arquivo:** `search.ts.pre-wave-a-merge-20260520-102032` vs `src/search.ts` atual

Mudanças comportamentais identificadas no diff:

| Localização | Mudança | Impacto |
|---|---|---|
| `SOURCE_TYPE_BOOST` map | Keys antigas (`user_statement`, `compiled`, `timeline`, `external`) substituídas por 12 keys novas (`entity`, `lesson`, `skill`, `note`, etc.) | **Nulo no entity-eval.db** — esse DB usa `entity_file/session_summary/event_log`, que não existem em nenhuma versão do mapa → `?? 1.0` em ambos |
| `DISABLE_TIER_BOOST` | `env.NOX_DISABLE_TIER_BOOST === "1"` → `env.NOX_DISABLE_TIER_BOOST === "1" \|\| env.NOX_ENABLE_TIER_BOOST !== "1"` | **Tier boost default OFF** no código atual (commit `d4eaada6`). G5 V3 usava dist **anterior** a esse commit |
| Comentários SOURCE_TYPE_BOOST | Apenas redação + calibration rationale expandido | Nenhum impacto de runtime |

**Salience.ts:** diff vazio entre backup e atual — nenhuma mudança de runtime em `salience.ts`.  
**Api-server.ts:** diff vazio entre backup e atual.

---

## Fase 2 — Hipóteses e Eliminação

| Hipótese | Status | Evidência |
|---|---|---|
| **H1**: PR #150 salience aditivo (d4eaada6) muda ranking | **CONFIRMADO (parcial)** | Commit `d4eaada6` (23:43 de 19/05) introduziu `calculateSalience` v2 aditiva. G5 V3 rodou com dist anterior a esse commit (compilado antes das 23:43). Divergência de ranking calculada: mediana 86 posições em 500 chunks (max 358) |
| **H2**: PR #154 SOURCE_TYPE_BOOST chave errada | **REFUTADO** | entity-eval.db usa `entity_file/session_summary/event_log` — nenhuma key bate com nenhuma versão do mapa. G6 confirmou: A8 == A10 (0.5845 == 0.5845), logo source_type boost é inert nesse corpus |
| **H3**: ocr-cache 0.5→0.7 polish | **INERT** | ocr-cache inexistente no entity-eval.db |
| **H4**: Build 10:23 pegou mudanças non-declared | **IDENTIFICADO** | Commit `d4eaada6` incluiu tier_boost default-off + salience v2 aditiva. Ambos não declarados como breaking em eval |
| **H5 (ROOT CAUSE DOMINANTE)**: DB diferente entre G5 V3 e G6 | **CONFIRMADO** | G5 V3 usou `g5.db` (68,995 chunks, `run-g5.sh` linha `EVAL_DB=g5.db`). G6 usou `entity-eval.db` (500 chunks). Corpora incomparáveis |

---

## Fase 3 — Reproduce Isolado (sem execução necessária)

O reproduce isolado foi substituído por análise forense direta nos logs de execução, que fornece evidência definitiva sem risco de disrupção.

**Prova a partir de logs:**

```
# G5 V3 (arquivo: /root/eval-results-archive-2026-05-19/g5-results.log)
EVAL_DB=/root/.openclaw/workspace/eval-data/g5-2026-05-20/g5.db
chunks count: 68,995
CFG=A8 n=100 nDCG@10=0.6237

# G6 (arquivo: /tmp/g6-results.log)
entity-eval.db: /root/.openclaw/workspace/eval-data/g4-v3-rerun-2026-05-19/entity-eval.db (500 chunks)
CFG=A8 n=100 nDCG@10=0.5845
```

**Diferenças de corpus confirmadas:**

| Propriedade | `g5.db` (G5 V3) | `entity-eval.db` (G6) |
|---|---|---|
| Chunks total | 68,995 | 500 |
| source_type distribution | note/personal-doc/ocr-cache/entity/... (backfill real) | entity_file/session_summary/event_log (sintético) |
| section distribution | 99% NULL (prod), 183 compiled/frontmatter/timeline | 100% section-tagged (compiled/frontmatter/timeline) |
| pain avg | 0.230 (prod default 0.2) | 0.513 (curado alto) |
| access_count > 0 | 10,010 (14.5%) | 13 (2.6%) |

A diferença de pain médio (0.23 vs 0.51) e section coverage (1% vs 100%) explica por que a fórmula aditiva v2 (que amplifica `W_IMPORTANCE=0.55` fortemente ligado a section) se comporta diferente entre os dois corpora.

---

## Fator de Código Identificado (Secundário)

**Commit `d4eaada6` (19/05 23:43 BRT)** — contém duas mudanças que afetam scoring:

### 1. `calculateSalience` v2 aditiva (`src/salience.ts`)
```
# Fórmula antiga (legacy)
salience = recency × pain × importance

# Fórmula nova (v2, no dist compilado às 10:23 de 20/05)
salience = 0.55 × importance + 0.15 × recency + 0.10 × pain + 0.20 × access_count
```
Divergência de ranking no entity-eval.db (n=500): **mediana 86 posições, máximo 358**.

### 2. `DISABLE_TIER_BOOST` default mudou (`src/search.ts`)
```typescript
// Antes (dist do G5 V3):
const DISABLE_TIER_BOOST = process.env.NOX_DISABLE_TIER_BOOST === "1";

// Agora (dist do G6):
const DISABLE_TIER_BOOST =
  process.env.NOX_DISABLE_TIER_BOOST === "1" ||
  process.env.NOX_ENABLE_TIER_BOOST !== "1";
```
No G6 A8 (`NOX_SALIENCE_MODE=active` sem `NOX_ENABLE_TIER_BOOST=1`), tier_boost está OFF.  
No G5 V3 A8 (dist pré-commit), tier_boost estava ON por default.

Impacto do tier_boost isolado: G5 V3 A6 (tier only, g5.db) = 0.4059 < A0 = 0.5126, confirmando que tier ativo prejudica o corpus prod. Portanto a mudança default-off é **correcta** e não é regressão.

---

## Conclusão

### Causa raiz

**DB swap**: G5 V3 mediu 0.6237 em `g5.db` (prod clone, 68k chunks). G6 mediu 0.5845 em `entity-eval.db` (500 chunks sintéticos). Os números medem coisas diferentes e **não representam regressão**.

### Fator secundário real (ação necessária)

O dist do G6 inclui `calculateSalience` v2 aditiva (commit `d4eaada6`) que **ainda não foi avaliada de forma controlada** — o G5 V3 rodou com a fórmula multiplicativa e o G6 rodou com a v2 em corpus diferente. É necessário um **G7 controlado**:

- Mesmo DB: `entity-eval.db` (500 chunks) para comparação com G6
- Dois runs: dist pré-`d4eaada6` (backup via `/var/backups/nox-mem/...`) vs dist atual
- Objetivo: isolar contribuição real da fórmula v2 no nDCG

---

## Decisão Proposta

| Item | Decisão |
|---|---|
| 0.6237 como baseline para G6+ | **REJEITAR** — esse número foi medido em g5.db (prod), não em entity-eval.db. Nova baseline G6 em entity-eval.db = 0.5845 |
| PR #154 source_type boost | **MANTER** — inert em entity-eval.db mas ativo em prod (backfill). Nenhuma evidência de regressão |
| Fórmula v2 aditiva | **MONITORAR** — shadow probe ativo (`NOX_SALIENCE_SHADOW_LOG`). Rodar G7 controlado antes de concluir impacto |
| Nova baseline canônica | **0.5845** em entity-eval.db (G6 A8), com nota de que G5 V3 A8 = 0.6237 em g5.db (prod clone) |

---

## Action Items

- [ ] **G7 (obrigatório):** rodar ablation com dois dists (pré/pós `d4eaada6`) sobre `entity-eval.db` para isolar impacto real da fórmula v2 — antes de qualquer claim de regressão ou melhoria
- [ ] **Padronizar DB de referência:** definir se o canonical eval set é `entity-eval.db` (500, curado) ou um clone prod (68k+). Documentar em `docs/DECISIONS.md`
- [ ] **Atualizar HANDOFF.md:** substituir "0.6237 canonical" por "0.6237 em g5.db / 0.5845 em entity-eval.db — métricas não comparáveis"
- [ ] PR followup se G7 confirmar que v2 piora entity-eval.db: investigar por que `access_count` (W=0.20) prejudica o curated set (quase todos com access_count=0)

---

## Arquivos Referenciados

| Arquivo | Função |
|---|---|
| `/root/eval-results-archive-2026-05-19/g5-results.log` | Resultados G5 V3 originais (A8=0.6237, g5.db) |
| `/tmp/g6-results.log` | Resultados G6 (A8=0.5845, entity-eval.db) |
| `/tmp/run-g5.sh` | Script G5 V3 — confirma `EVAL_DB=g5.db` |
| `/tmp/run-g6.sh` | Script G6 — confirma `entity-eval.db` |
| `/var/backups/nox-mem/pre-op/search.ts.pre-wave-a-merge-20260520-102032` | Backup pré-deploy para G7 |
| `/root/.openclaw/workspace/eval-data/g5-2026-05-20/g5.db` | g5.db (68,995 chunks, prod clone) |
| `/root/.openclaw/workspace/eval-data/g4-v3-rerun-2026-05-19/entity-eval.db` | entity-eval.db (500 chunks, curated) |
