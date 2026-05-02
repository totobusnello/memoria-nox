# E03a — Entity-Facts SPO Injection (`<vault-facts>` block)

> Read-only KG → context surface. Bloco `<vault-facts>` injetado no prompt com top-K SPO triples relevantes à query, derivados de `kg_entities` + `kg_relations` existentes.
> Implementação v1 minimal: top-K simples, sem confidence filter.

**Status:** Design spec (CANDIDATE)
**Data:** 2026-05-01
**ID novo:** E03a (parte do split E03a/E03b — ver `docs/ROADMAP.md §4`)
**ID antigo:** A6 (Section 9 v1.6) / Q1 (ClawMem analysis)
**Vision §:** ClawMem Q1 (cross-ref)
**Esforço estimado:** 1.5h (greenfield 0.7×, mas escopo enxuto)
**Dependências:** ≥G03 ✅ (archive 3 source files), KG populado (✅ 402 entities + 544 relations), MCP server v3.7+
**Bloqueia:** E03b (activate após 7d subjective utility report)
**Cross-ref:** `docs/ROADMAP.md` (E03a/b row), `plans/_archive/2026-04-26-clawmem-analysis.md` §5 (Q1), `docs/DECISIONS.md` (shadow-mode discipline)

---

## Problema

Hoje o KG (`kg_entities` 402 + `kg_relations` 544) é consultado **só sob demanda** via:
- CLI: `nox-mem kg-path <entity>`, `nox-mem cross-kg`
- MCP: `kg_build`, `cross_search`
- HTTP: `/api/kg`, `/api/kg/path`

O agente (Maestro/persona) **não vê SPO triples no contexto** ao processar uma turn do usuário. Resultado: agente faz busca FTS+semantic mesmo quando a resposta direta tá numa relação `(Toto, prefere, "você" sobre "tu")` ou `(nox-mem, depende, sqlite-vec)` já modelada no KG.

**Dor concreta observada:**
- Toto pergunta "qual modelo Gemini default?" — agente busca em chunks, lê CLAUDE.md, monta resposta. KG já tem `(nox-mem, default_model, "gemini-2.5-flash-lite")` — 0 latência se injetado.
- Persona Atlas processa turn sobre projeto X — não enxerga relações já curadas `(X, status, "active")`, `(X, owner, "Toto")`.

---

## Solução: SPO Injection minimal

### Conceito

A cada turn, **antes** de o LLM responder, injetar um bloco `<vault-facts>` no system prompt contendo top-K triples SPO relevantes à query do usuário.

```
<vault-facts>
nox-mem default_model "gemini-2.5-flash-lite"
nox-mem depends_on sqlite-vec
nox-mem depends_on FTS5
schema_v10 introduced retention_days
schema_v10 introduced pain
</vault-facts>
```

### Arquitetura

```
USER TURN
   │
   ▼
┌──────────────────────────────────────────┐
│ 1. Extract candidate entities from query │  (regex/NER lightweight)
│    "qual modelo gemini do nox-mem?"      │
│    → entities: [nox-mem, gemini]         │
└──────────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────┐
│ 2. KG lookup top-K relations             │  SQL: SELECT * FROM kg_relations
│    WHERE subject IN (entities)           │  WHERE subject IN (?, ?)
│    OR object IN (entities)               │  OR object IN (?, ?)
│    LIMIT K=8                             │  ORDER BY confidence DESC NULLS LAST
└──────────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────┐
│ 3. Format as SPO triples                 │  "<subject> <relation> <object>"
│    Apply token budget                    │  bimodal: 200 balanced / 250 deep
└──────────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────┐
│ 4. Inject as <vault-facts> system block  │  pre-pended to system prompt
│    XML-like tags pra parseability        │
└──────────────────────────────────────────┘
   │
   ▼
LLM RESPONSE
```

### Componentes

#### 4.1 Entity extraction (lightweight)

**v1 simples:** match query contra `kg_entities.name` (LIKE/lower) + tokens conhecidos do vocabulário entity. Sem NER cloud.

```typescript
// dist/lib/spo-injection.ts (~80 LOC)
function extractCandidateEntities(query: string): string[] {
  const tokens = query.toLowerCase().split(/\s+/);
  const stmt = db.prepare(`
    SELECT name FROM kg_entities
    WHERE LOWER(name) IN (${tokens.map(() => '?').join(',')})
  `);
  return stmt.all(...tokens).map(r => r.name);
}
```

#### 4.2 KG top-K lookup

```sql
SELECT subject, relation, object, confidence, source_chunk_id
FROM kg_relations
WHERE subject IN (:entities) OR object IN (:entities)
ORDER BY
  CASE WHEN confidence IS NULL THEN 1 ELSE 0 END,  -- NULL last
  confidence DESC,
  updated_at DESC
LIMIT :k;
```

**v1:** K=8 (cobre token budget 200 com folga; ~25 tokens por triple)
**v2 (E03b se ativado):** K dinâmico baseado em token budget; confidence filter ≥0.5

#### 4.3 Format SPO

```typescript
function formatVaultFacts(rels: Relation[]): string {
  const lines = rels.map(r => `${r.subject} ${r.relation} ${r.object}`);
  return `<vault-facts>\n${lines.join('\n')}\n</vault-facts>`;
}
```

#### 4.4 Token budget bimodal

```typescript
const TOKEN_BUDGET = {
  balanced: 200,   // default
  deep: 250        // when query has "explicar", "como funciona", "por quê"
};

function pickBudget(query: string): number {
  const deepMarkers = /\b(explicar?|como funciona|por qu[eê]|deep dive|detalh)\b/i;
  return deepMarkers.test(query) ? TOKEN_BUDGET.deep : TOKEN_BUDGET.balanced;
}
```

#### 4.5 Injection point

**Opção A (preferida):** MCP tool novo `vault_facts` que o agent chama explicitamente.
**Opção B:** Hook no `nox-mem search` que retorna chunks + `vaultFacts` field anexado ao response.

**Decisão v1: Opção B** (zero mudança no agent contract; surface aparece naturalmente em respostas de search).

```typescript
// Modify search() return shape:
interface SearchResponse {
  results: Chunk[];
  vaultFacts?: string;  // novo campo opcional
}
```

---

## Implementação

### Arquivos novos

| Arquivo | LOC | Descrição |
|---|---|---|
| `src/lib/spo-injection.ts` | ~80 | extract + lookup + format + budget |
| `src/__tests__/spo-injection.test.ts` | ~60 | unit tests (5 cenários) |

### Arquivos modificados

| Arquivo | Mudança |
|---|---|
| `src/search.ts` | Anexar `vaultFacts` no return se `NOX_VAULT_FACTS_MODE=active\|shadow` |
| `src/api.ts` | Surface `vaultFacts` em `/api/search` response |
| `src/mcp.ts` | (opcional v2) Tool `vault_facts(query)` standalone |

### Env vars

```bash
NOX_VAULT_FACTS_MODE=shadow      # shadow (compute+log) | active (surface) | off
NOX_VAULT_FACTS_LOG=1            # log [vault-facts] events para telemetria
NOX_VAULT_FACTS_K=8              # top-K override
```

**Default v1:** `shadow` (per regra `feedback_shadow_mode_for_ranking_changes.md`).
**E03b activate:** flip para `active` após 7d subjective utility report ✅.

### Schema mudanças

**Nenhuma.** v1 usa apenas `kg_entities` + `kg_relations` existentes. Tabelas read-only.

(v2 opcional E03b+: nova tabela `vault_facts_telemetry` se quisermos métrica objetiva. Não em v1.)

---

## Critério de ativação E03b (7d shadow)

Após E03a deployado em `shadow` por **7 dias wall-clock**, decisão de ativar via:

### Métrica subjective (primary)
- Toto reporta utility ≥7/10 em pelo menos 3 turns onde `<vault-facts>` foi gerado
- "Senti diferença positiva" / "ajudou ver fato direto sem busca"

### Métrica objective (secondary, observacional)
- Volume: ≥50 turns geraram `<vault-facts>` em 7d (frequência uso real)
- KG hit rate: ≥30% das queries que tocaram entities tiveram ≥1 relation match
- Token cost: budget bimodal 200/250 respeitado em 95% dos casos
- Zero regressão em latência search (`/api/health.searchTelemetry.p50`)

### Kill switches
- LLM ignora ou contradiz `<vault-facts>` em ≥2 turns observados → revisitar formato
- Token blow >300 em qualquer caso → bug em budget logic
- Toto reporta "atrapalhou" / "ruído" / "irrelevante" em ≥2 turns → desativar (mode=off)

---

## Riscos + mitigação

| Risco | Probabilidade | Mitigação |
|---|---|---|
| KG entities não cobrem query → bloco vazio | Alta | v1: emitir `<vault-facts>` só se K≥1 match; senão omit |
| Triples com confidence baixa poluem (LLM acredita em fato fraco) | Média | v1 sem filter mas K=8 limit + ORDER BY confidence DESC; v2 (E03b) adiciona threshold ≥0.5 |
| Token budget estoura em queries com muitas entities | Baixa | hard limit K=8 + truncate triples >40 chars |
| Surface `vaultFacts` quebra clients existentes (HTTP/MCP) | Baixa | Campo é optional; clients antigos ignoram |
| Latência adicional p95 search >50ms | Baixa | KG lookup é índice em `kg_relations(subject)`; ~5ms |

---

## Plano de execução (1.5h)

### Phase 1 — Implementação (45min)
- [ ] Criar `src/lib/spo-injection.ts` com 4 funções (extract, lookup, format, budget)
- [ ] Modificar `src/search.ts` para chamar `getVaultFacts()` quando `NOX_VAULT_FACTS_MODE !== off`
- [ ] Surface `vaultFacts` no return de `search()` + `/api/search`
- [ ] Adicionar 3 env vars no `.env.example`

### Phase 2 — Testes (30min)
- [ ] `src/__tests__/spo-injection.test.ts` cobrindo:
  - extract entities (match exato, lower-case, sem match)
  - lookup top-K (8 results, NULLS last, order by confidence)
  - format output (triples válidos, escape quotes)
  - token budget (balanced 200, deep 250 trigger)
  - shadow vs active vs off modes

### Phase 3 — Deploy + monitor (15min)
- [ ] Build TS → dist/
- [ ] rsync para VPS `/root/.openclaw/workspace/tools/nox-mem/`
- [ ] Adicionar `NOX_VAULT_FACTS_MODE=shadow` + `NOX_VAULT_FACTS_LOG=1` ao `/root/.openclaw/.env`
- [ ] `systemctl restart nox-mem-api`
- [ ] Smoke search hitting entity (ex: `nox-mem`, `Toto`) → confirma `<vault-facts>` aparece em response (campo `vaultFacts`)
- [ ] Tail journalctl `[vault-facts]` log lines

---

## Telemetria shadow (7d)

```bash
# Shadow log format:
# [vault-facts] mode=shadow query="..." entities=N triples=K tokens=T budget=200|250

# Aggregate:
journalctl -u nox-mem-api --since "7 days ago" \
  | grep -E "\[vault-facts\]" \
  | python3 /root/.openclaw/scripts/analyze-vault-facts-telemetry.py
```

Script `analyze-vault-facts-telemetry.py` (criar como parte de E03b activation):
- Total events
- Distribuição entities/triples/tokens
- Frequência hit rate (% queries com ≥1 triple)
- Top-N relations mais surfaced
- Output JSON pra `/var/log/nox-vault-facts-daily.log`

---

## Out-of-scope (v1)

- ❌ Confidence filter (≥0.5) — adiciona em v2 se shadow mostrar ruído
- ❌ NER cloud (Gemini) pra entity extraction — v1 usa lookup contra `kg_entities.name`
- ❌ Multi-hop traversal (1-hop only) — futuro E07 (`impact`) cobre
- ❌ Frontmatter facts (já capturados via `section=frontmatter` + section_boost ativo desde 2026-05-01)
- ❌ Telemetry table dedicada — v1 só journalctl logs (cheap)

---

## Cross-reference

| Item | Onde |
|---|---|
| Decision shadow-mode 7d obrigatório | `MEMORY.md:feedback_shadow_mode_for_ranking_changes.md` |
| ClawMem Q1 origem da ideia | `plans/_archive/2026-04-26-clawmem-analysis.md` linha 53 |
| KG schema (`kg_entities`, `kg_relations`) | `docs/ARCHITECTURE.md` |
| Token budget bimodal racional | `plans/_archive/2026-04-26-clawmem-analysis.md` linha 37 |
| Roadmap split implement/activate | `docs/ROADMAP.md §4` E03a + E03b rows |
| Validação features via DB state | `MEMORY.md:feedback_validate_features_with_db_not_logs.md` |

---

**Próximo passo:** revisar com Toto (essa spec) → se aprovado, abrir branch `feat/E03a-spo-injection` e executar Phase 1-3 em 1.5h.
