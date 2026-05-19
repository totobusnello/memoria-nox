# L3 — Confidence + Provenance Field

> **Status:** SCHEMA + WRITE-PATHS + MARK WORKFLOW + TELEMETRY shipped (DoD-A). Ranking integration GATED (DoD-B) — defaults `disabled`.
>
> **Tagline:** _"Pain-weighted hybrid memory with shadow discipline — yours by design."_
>
> **Spec:** `specs/2026-05-17-L3-confidence-field.md`

---

## 1. Overview

Cada chunk em nox-mem agora carrega dois novos sinais ortogonais a tudo que existia antes (pain / importance / retention / section):

- **`confidence` ∈ [0,1]** — quão certo você está de que o fato é verdadeiro
- **`provenance_kind`** — de onde o fato veio (observed / declared / inferred / derived / user-marked)

E mais um campo de cadeia de substituição:

- **`superseded_by` INTEGER FK** — aponta pra um chunk mais novo que substitui este

Esses três sinais respondem perguntas que `pain` + `importance` não respondiam:

| Pergunta | Antes (sem L3) | Depois (com L3) |
|---|---|---|
| "Esse fato é confiável?" | Não distinguia LLM-extracted de observed | `confidence` + `provenance_kind` |
| "Esse fato continua válido?" | Sem mecanismo | `superseded_by` + mark stale |
| "Toto já revisou esse fato?" | Sem mecanismo | `provenance_kind='user-marked'` |
| "É consolidado ou primário?" | Sem mecanismo | `provenance_kind ∈ {observed, derived}` |

---

## 2. Spec reference

Documento canônico: [`specs/2026-05-17-L3-confidence-field.md`](../specs/2026-05-17-L3-confidence-field.md).

Cross-links:
- [`docs/DECISIONS.md`](DECISIONS.md) — salience formula multiplicativa
- [`docs/HANDOFF.md`](HANDOFF.md) — estado vivo
- [`CLAUDE.md`](../CLAUDE.md) regra #5 — nenhuma mudança em ranking sem eval lift ≥+1.0pp
- [`CLAUDE.md`](../CLAUDE.md) regra #6 — ops_audit append-only

Schema v19 (já mergeado em `staged-migrations/v19.sql`) adicionou os campos. Esta camada L3 implementa o que **usa** esses campos.

---

## 3. Os seis tipos de provenance

A taxonomia tem 5 valores no schema (`observed`, `declared`, `inferred`, `derived`, `user-marked`) e o CLI/HTTP expõe 3 sub-variantes de `user-marked` (canonical / refuted / stale).

### 3.1 `observed` — testemunhado, gravado

**Default confidence:** `0.95` (configurável via `NOX_CONFIDENCE_OBSERVED`).

**Exemplos:**
- Linha em entity timeline section: `"2026-05-12 — Toto rejeitou F09 na call com Cipher"`
- Snippet de conversa capturado verbatim em WhatsApp/Slack
- Output de comando executado: `git log --oneline | tail -5`

**Quando aparece:** `ingest-entity` na seção `timeline`, captura de mensagem direta.

**Pode decair?** Não. `observed` é histórico — você viu acontecer. Pode ficar stale (não vale mais), mas não vira errado.

### 3.2 `declared` — verdade compilada, autor humano

**Default confidence:** `0.9` (configurável via `NOX_CONFIDENCE_DECLARED`).

**Exemplos:**
- Frontmatter YAML de entity file (`type: feedback`, `tags: [hard-rule]`)
- Seção `compiled` de entity file (o "single source of truth" curado)
- Linhas de `CLAUDE.md`, `DECISIONS.md`
- Linhas de spec

**Quando aparece:** `ingest-entity` nas seções `frontmatter` e `compiled`.

**Pode decair?** Sim — autor humano com possibilidade de staleness (não erro). Decay opt-in via `nox-mem confidence decay --apply`.

### 3.3 `inferred` — extraído por LLM, sujeito a erro

**Default confidence:** `0.65` (configurável via `NOX_CONFIDENCE_INFERRED`).

**Exemplos:**
- KG relations extraídas pelo `kg-extract` (Gemini)
- Síntese semântica onde a fonte original existe mas o LLM produziu a afirmação
- Reconciliação de aliases via LLM

**Quando aparece:** Pipeline `kg-extract`, transformações Gemini sobre chunks.

**Pode decair?** Sim — taxa de erro do LLM (E05 mediu 14%→56% pós-prompt-rev). 0.65 reflete confiança modesta.

### 3.4 `derived` — consolidado, agregado, sintético

**Default confidence:** `0.75` (configurável via `NOX_CONFIDENCE_DERIVED`).

**Exemplos:**
- Output de `consolidate` (agglomeração de N chunks similares)
- Output de `crystallize` (sumarização de truth section)
- Multi-chunk fusion

**Quando aparece:** Comandos `consolidate`, `crystallize`, pipeline graphify.

**Pode decair?** Sim — herda o weakest link da cadeia de origem.

### 3.5 `user-marked` — Toto explicitamente afirmou ou negou

**Confidence variável** dependendo do mark kind:

| Mark kind | confidence | Semântica |
|---|---|---|
| `canonical` | `1.0` (configurável via `NOX_CONFIDENCE_USER_CANONICAL`) | "este fato é canônico, prefira este" |
| `refuted` | `0.05` (configurável via `NOX_CONFIDENCE_USER_REFUTED`) | "este fato está errado — mantenha pra auditoria" |
| `stale` | inalterado | "este fato já foi verdade, hoje não é mais" |

**Quando aparece:** CLI `nox-mem mark`, HTTP `POST /api/chunk/:id/mark`, MCP `chunk_mark`.

**Pode decair?** Não. Override do operador é final até o operador re-marcar.

### 3.6 `NULL` — sem comprometimento

**Default confidence:** `0.8` (legacy baseline).

**Quando aparece:** Markdown genérico sem entity file, chunks pre-v19 (já existem no corpus).

**Pode decair?** Sim — opt-in via decay sweep, tratado como `inferred` para fins de decay.

---

## 4. Tabela de defaults (referência rápida)

| Path de ingest | `confidence` | `provenance_kind` |
|---|---|---|
| `ingest-entity` section=compiled | 0.9 | `declared` |
| `ingest-entity` section=frontmatter | 0.9 | `declared` |
| `ingest-entity` section=timeline | 0.95 | `observed` |
| `ingest` markdown genérico | 0.8 | `NULL` |
| `graphify` | 0.7 | `derived` |
| `kg-extract` (Gemini) | 0.65 | `inferred` |
| `kg-extract` (regex_only) | 0.85 | `observed` |
| `kg-extract` (frontmatter direct) | 0.9 | `declared` |
| `kg-extract` (manual) | 1.0 | `observed` |
| `consolidate` | 0.75 | `derived` |
| `crystallize` | 0.85 | `derived` |
| CLI `ingest --confidence X --kind Y` | explícito | explícito |
| CLI `mark --canonical` | 1.0 | `user-marked` |
| CLI `mark --refuted` | 0.05 | `user-marked` |
| CLI `mark --stale` | inalterado | `user-marked` |

Todos os defaults override-áveis via env vars (ver §6).

---

## 5. Mark workflow (CLI / HTTP / MCP)

### 5.1 CLI

```bash
# Marcar um chunk como canônico (Toto afirma — confidence vai pra 1.0)
nox-mem mark 12345 --canonical

# Marcar como refutado (Toto nega — confidence vai pra 0.05, fica auditável)
nox-mem mark 12345 --refuted --notes "deprecated 2026-05-18"

# Marcar como stale (não mais verdade, mas mantém confidence atual)
nox-mem mark 12345 --stale

# Supersession: chunk 100 substitui chunk 50
nox-mem mark 50 --supersede-by 100 --notes "v2 do mesmo fato"

# Combinar supersession com canonical (mark stale + canonize replacement)
nox-mem mark 50 --supersede-by 100 --canonical --notes "promove novo, demove antigo"
```

Saída: JSON com `applied.{confidence,provenance_kind,superseded_by}` + `audit_id`.

### 5.2 HTTP API

```bash
# POST /api/chunk/<id>/mark
curl -X POST http://127.0.0.1:18802/api/chunk/12345/mark \
  -H 'Content-Type: application/json' \
  -d '{"kind": "canonical", "notes": "validated by Toto 2026-05-18"}'

# POST /api/chunk/<id>/supersede
curl -X POST http://127.0.0.1:18802/api/chunk/50/supersede \
  -H 'Content-Type: application/json' \
  -d '{"by_chunk_id": 100, "reason": "manual_resolution"}'
```

Status codes:
- `200` — sucesso
- `400` — body inválido (kind desconhecido, id não-numérico)
- `404` — chunk não existe
- `500` — erro inesperado

### 5.3 MCP

Duas tools novas registradas:

```typescript
// chunk_mark(id, kind, notes?)
{
  "name": "chunk_mark",
  "inputSchema": {
    "type": "object",
    "properties": {
      "id":    { "type": "number" },
      "kind":  { "type": "string", "enum": ["canonical", "refuted", "stale"] },
      "notes": { "type": "string" }
    },
    "required": ["id", "kind"]
  }
}

// chunk_supersede(id, by_id, notes?, reason?)
{
  "name": "chunk_supersede",
  "inputSchema": {
    "type": "object",
    "properties": {
      "id":     { "type": "number" },
      "by_id":  { "type": "number" },
      "notes":  { "type": "string" },
      "reason": {
        "type": "string",
        "enum": ["auto_supersede_temporal", "manual_resolution",
                 "stale_link_reconciliation", "dismiss"]
      }
    },
    "required": ["id", "by_id"]
  }
}
```

### 5.4 Audit trail

Toda operação de mark/supersede emite uma row em `ops_audit` com:

- `op` = `confidence-mark-canonical` / `confidence-mark-refuted` / `confidence-mark-stale` / `confidence-supersede`
- `status` = `success` ou `failed`
- `details` = JSON com `chunk_id`, `kind`, `before`/`after` deltas, `notes`
- `started_at` = ISO timestamp

`ops_audit` é append-only por CLAUDE.md regra #6 — DELETE e UPDATE bloqueados por triggers do schema. Você pode auditar histórico completo de mark operations:

```bash
nox-mem mark-log --since 2026-05-01 --kind canonical
# ou direto via SQL:
sqlite3 nox-mem.db "SELECT op, started_at, details FROM ops_audit WHERE op LIKE 'confidence-%' ORDER BY id DESC LIMIT 20"
```

---

## 6. Configuração via env vars

| Env var | Default | Propósito |
|---|---|---|
| `NOX_CONFIDENCE_OBSERVED` | `0.95` | Default para chunks `observed` |
| `NOX_CONFIDENCE_DECLARED` | `0.90` | Default para chunks `declared` |
| `NOX_CONFIDENCE_INFERRED` | `0.65` | Default para chunks `inferred` |
| `NOX_CONFIDENCE_DERIVED` | `0.75` | Default para chunks `derived` |
| `NOX_CONFIDENCE_GRAPHIFY` | `0.70` | Default para graphify pipeline |
| `NOX_CONFIDENCE_USER_CANONICAL` | `1.00` | Confidence aplicado em mark --canonical |
| `NOX_CONFIDENCE_USER_REFUTED` | `0.05` | Confidence aplicado em mark --refuted |
| `NOX_CONFIDENCE_ACTIVE_FLOOR` | `0.30` | Floor para skip em mode active |
| `NOX_RANKING_CONFIDENCE` | `disabled` | `disabled` / `shadow` / `active` |
| `NOX_CONFIDENCE_DECAY_HALFLIFE_DAYS` | `-1` (off) | Half-life de decay (v2 feature) |

Valores fora de [0,1] são clampados (DB CHECK constraint é guard final).

---

## 7. Ranking integration (GATED)

### 7.1 Por que está gated

CLAUDE.md regra #5 — _"Nunca introduzir ranking/scoring change em commit de 'fix'. Boost multiplicativo empilhável é veneno."_

L3 ranking integration multiplica `confidence` no salience. Isso É uma mudança de ranking. Por isso ela só ativa após:

1. Eval ablation completar (variantes A/B/C/D) com **n≥200 queries**
2. Best variant delta **≥ +1.0pp nDCG@10**
3. **Significância estatística** (paired bootstrap, p<0.05)
4. **7 dias de shadow mode** sem regressões
5. Forge/Maestro sign-off
6. **Toto explícito GO**

Até lá, `NOX_RANKING_CONFIDENCE=disabled` (default). Schema + writes + telemetry + mark workflow tudo ativo; ranking inalterado.

### 7.2 Modos

```bash
NOX_RANKING_CONFIDENCE=disabled  # default. confidence ignorado em ranking.
NOX_RANKING_CONFIDENCE=shadow    # delta computado + logado, NÃO aplicado.
NOX_RANKING_CONFIDENCE=active    # multiplicado no salience + skip rules.
```

### 7.3 Fórmula (active mode)

```
salience' = salience × confidence
if superseded_by IS NOT NULL: salience' *= 0.5
salience' clamp to [0.3, 1.5]

if (confidence < active_floor):                              SKIP
if (provenance_kind='user-marked' AND confidence < floor):   SKIP
```

### 7.4 Eval gate (DoD-B)

Os 4 variantes ablation rodam via `eval/confidence-eval.ts`:

| Variant | Formula |
|---|---|
| A (baseline) | `recency × pain × importance` |
| B (conf alone) | `... × confidence` |
| C (conf + section) | `... × confidence × section_boost` |
| D (full + decay) | `... × confidence(decayed) × section_boost` |

Decision matrix:

| Resultado | Ação |
|---|---|
| Todos variantes ≥+1.0pp, p<0.05 | **GO** — escolhe melhor variante, ativa em shadow primeiro |
| Só D ≥+1.0pp | GO com decay enabled |
| Só B ≥+1.0pp | GO sem decay |
| Best <+1.0pp BUT ≥0 | **ANNOTATION ONLY** — schema fica, ranking não muda |
| Qualquer <0 | **CUT ranking** — anotação pura |
| Insignificante (p>0.05) | ANNOTATION ONLY + extend shadow 14d, re-eval |

---

## 8. Telemetry

### 8.1 /api/health.confidence

Live distribution + ranking mode:

```json
{
  "confidence": {
    "ranking_mode": "shadow",
    "provenance": {
      "observed": 1234,
      "declared": 5678,
      "inferred": 4321,
      "derived": 2345,
      "user-marked": 12,
      "null": 49405
    },
    "confidence_distribution": {
      "mean": 0.81,
      "p25": 0.7,
      "p50": 0.8,
      "p75": 0.9,
      "p95": 0.95,
      "stddev": 0.12
    },
    "superseded_count": 89
  }
}
```

### 8.2 Telemetry queries úteis

```bash
# Distribuição por kind
curl -s http://127.0.0.1:18802/api/health | jq '.confidence.provenance'

# Override rate (canonical + refuted no último 7d)
sqlite3 nox-mem.db <<SQL
SELECT op, COUNT(*) FROM ops_audit
WHERE op LIKE 'confidence-mark-%'
  AND started_at > datetime('now', '-7 days')
GROUP BY op;
SQL

# Top 10 chunks com lowest confidence (audit candidates)
sqlite3 nox-mem.db <<SQL
SELECT id, confidence, provenance_kind, substr(content, 1, 60)
FROM chunks
ORDER BY confidence ASC NULLS LAST
LIMIT 10;
SQL

# Superseded chunks (não devem aparecer em search se ranking active)
sqlite3 nox-mem.db <<SQL
SELECT id, superseded_by, provenance_kind FROM chunks
WHERE superseded_by IS NOT NULL;
SQL
```

### 8.3 Discord alerts (P2-level)

- `provenance.inferred.mean < 0.5` por 24h → suspeitar regressão em kg-extract
- `decay --apply` afetaria >10% do corpus em uma run → exigir `--force` flag
- Mark canonical/refuted rate > 100/dia → possível script malicioso

---

## 9. Shadow-mode rollout plan

### Semana 1 — Schema + writes + CLI ativos (DoD-A)

- **Dia 1:** PR review + merge migração v19 + write-hooks + mark CLI
- **Dia 2:** Deploy schema migration (com `withOpAudit` snapshot)
- **Dia 3-7:** Validar distribuição por kind, override rate, zero regressões em `/api/health`
- **Gate:** 0 schema-related alerts × 5 dias consecutivos

### Semana 2 — Ablation eval

- **Dia 8:** Run R01a harness variantes A/B/C/D em n=200 queries
- **Dia 9-10:** Análise estatística, p-values, intervalos de confiança do lift
- **Dia 11:** Maestro draft verdict; Forge code review
- **Dia 12-14:** Toto revisa, pergunta adversarial, assina

### Semana 3 — Decisão

- **Dia 15:** GO ou NO-GO em `docs/DECISIONS.md`
- Se **GO**:
  - Dia 16: `NOX_RANKING_CONFIDENCE=shadow` flip (métricas live, sem behavior change)
  - Dia 16-22: 7d shadow validation (live métricas batem offline ±20%)
  - Dia 23: `NOX_RANKING_CONFIDENCE=active` flip; 7d monitoring window
- Se **NO-GO**:
  - Annotation-only mode permanente
  - Decay cron NÃO instalado
  - Telemetry continua coletando

### Rollback path

Qualquer regressão pós-activation:

1. `NOX_RANKING_CONFIDENCE=disabled` (instant, sem mudança de DB)
2. Investigar via telemetry + ops_audit
3. Schema FICA — annotation continua funcionando
4. Re-eval antes de re-flip

---

## 10. Não-fazemos (v1)

1. **Sem LLM-based confidence scoring** — Gemini não estima confidence. Confidence vem do **path of origin** (deterministic per ingest), não de meta-inference. Auditável.

2. **Sem KG-propagation de confidence** — relation confidence ≠ entity confidence ≠ chunk confidence. Cross-propagation é segunda ordem; defer pra L4+.

3. **Sem time-weighted model além de monthly multiply** — decay é 1 regra (180d + 0.95 monthly); sem half-life curves, sem per-tenant tuning.

4. **Sem per-tenant baselines** — confidence é global. Multi-tenant fora de escopo.

5. **Sem boost automático em re-access** — `last_accessed_at` atualiza mas NÃO aumenta confidence. Ler algo não torna verdade.

6. **Sem retroactive backfill** — chunks pre-v19 default 0.8/NULL até user marcar.

---

## 11. Diferenciação vs memanto

memanto markets _"Confidence + provenance metadata on every memory"_ como Six Gaps #3. Nossa implementação ganha em quatro eixos:

| Aspecto | memanto | nox-mem L3 |
|---|---|---|
| Provenance enum | implícito | explícito 5 valores + 3 sub-variantes user-marked |
| Decay model | (provável time-weighted) | 1 regra, 180d, monthly 0.95, gated por pain |
| Ranking integration | (provável default-on) | GATED em eval lift ≥+1.0pp |
| Shadow discipline | unclear | mandatório 7d (CLAUDE.md regra #5) |
| Pain coupling | N/A (sem pain field) | sim — pain=1.0 → zero decay |
| LLM-based scoring | provável | NÃO — determinístico per path |
| Ablation eval | unclear | R01a harness mandatório |
| Annotation-only fallback | unclear | first-class — ships mesmo se ranking falhar |
| Auditability | unclear | `confidence_set_at` + `ops_audit` append-only |

**Resumo:** memanto talvez tenha melhor algoritmo de scoring (LLM-based); nosso edge é **determinismo + auditability + gate disciplinado**. Você pode reproduzir exatamente porque um chunk recebeu 0.65 (porque veio do `kg-extract`), pode auditar todo override que Toto fez, pode reverter ranking change sem schema rollback.

---

## 12. Arquivos relevantes

| Arquivo | Função |
|---|---|
| `staged-migrations/v19.sql` | Schema delta (já mergeado) |
| `staged-L3/edits/migrations/v22-confidence-eval-log.sql` | Tabela `confidence_eval_log` para ablation runs |
| `staged-L3/edits/src/lib/confidence/types.ts` | Public type surface |
| `staged-L3/edits/src/lib/confidence/config.ts` | Env override + defaults |
| `staged-L3/edits/src/lib/confidence/write-hooks.ts` | applyConfidence + applyConfidenceToRelation |
| `staged-L3/edits/src/lib/confidence/mark.ts` | Core mark/supersede DB writes |
| `staged-L3/edits/src/lib/confidence/ranking.ts` | Gated ranking integration |
| `staged-L3/edits/src/lib/confidence/search-filter.ts` | --min-confidence filter |
| `staged-L3/edits/src/cli/mark.ts` | CLI `nox-mem mark` |
| `staged-L3/edits/src/api/mark.ts` | HTTP `/api/chunk/:id/mark` + `/supersede` |
| `staged-L3/edits/src/api/health-confidence.ts` | `/api/health.confidence` slice |
| `staged-L3/edits/src/mcp/tools/mark.ts` | MCP `chunk_mark` + `chunk_supersede` |
| `staged-L3/edits/eval/confidence-eval.ts` | Ablation scaffold (variants A/B/C/D) |
| `staged-L3/edits/src/lib/confidence/__tests__/` | 75+ unit + integration tests |

---

## 13. Próximos passos

1. Code review em ambos PRs (este L3 + v19 já mergeado)
2. Deploy schema migration via `withOpAudit` snapshot
3. Wire write-hooks no `ingest-router.ts` real (production-wire patch)
4. Run R01a ablation eval em n=200 queries
5. Decision em `docs/DECISIONS.md`: GO / NO-GO / EXTEND-SHADOW
6. Se GO: flip `NOX_RANKING_CONFIDENCE=shadow` por 7d
7. Se ainda GO: flip pra `active`
8. Monitor /api/health.confidence semanal

**Estado atual desta sessão:** T1-T13 completos. Ranking integration GATED. Você precisa rodar o ablation eval pra decidir activate/refuted.

---

_Doc gerado pela implementação L3 T1-T13 — 2026-05-18._
