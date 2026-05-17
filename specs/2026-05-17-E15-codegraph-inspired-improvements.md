# E15 — CodeGraph-inspired retrieval improvements (3 ideias arquiteturais)

**ID:** E15
**Status:** 📋 QUEUED — pós-R03 ou paralelo a D01 v3
**Owner:** Toto (decisão); Maestro (execução)
**Data:** 2026-05-17
**Origem:** análise do repo [`Jakedismo/codegraph-rust`](https://github.com/Jakedismo/codegraph-rust) (Rust code-knowledge-graph com tree-sitter + LSP + SurrealDB HNSW + agentic tools). 3 ideias arquiteturais aplicáveis ao nosso domínio (memória conversacional/lições) sem trazer tooling code-specific (call chains, AST, etc).

**Cross-link:** `docs/HANDOFF.md` §RETOMADA opção 4; `docs/ROADMAP.md` §Evolution E15.

---

## Resumo executivo

Trazer 3 padrões arquiteturais do CodeGraph que melhoram **qualidade pra cada consumer** + **proteção contra explosão de custo** + **flexibilidade dev/prod**, sem misturar agent reasoning (que é responsabilidade do consumer).

| Sub-feature | Esforço | ROI | Risk |
|---|---|---|---|
| **A. Tier-aware behavior por context window** | 1-2h | Alto | Baixo |
| **B. Context overflow protection multi-layer** | 1-2h | Médio-alto | Baixo |
| **C. Indexing tiers fast/balanced/full** | 2-3h | Médio | Médio (refactor 3 comandos) |
| **Total pacote** | 4-7h | — | — |

**Trade-off arquitetural:** todas 3 são *escala/adaptação*, não amplificação ou pool expansion. Diferente de A1/A2/G (refutadas D39), essas não dependem de FTS5 ter recall.

---

## A. Tier-aware behavior por context window do consumer

### Problema atual

`nox-mem search --limit 5` é fixo. Mas consumers têm context windows muito diferentes:

| Consumer | Model | Context window | Hoje recebe |
|---|---|---|---|
| Boris (Discord) | Haiku 4.5 | 200K | 5 chunks (mesma quantidade que Opus) |
| Atlas (Discord) | Opus 4.7 | 200K-1M | 5 chunks (poderia receber mais) |
| Forge (Discord) | Opus 4.7 (1M) | 1M | 5 chunks |
| CLI manual (Toto) | — | — | 5 chunks |
| Semantic canary | — | — | 5 chunks |

Resultado: Boris às vezes sufoca; Atlas/Forge subutilizam pool dense disponível (top_k *2 = 20 candidates retornados, só 5 surfaced).

### Design

Detectar tier do consumer e escalar 3 parâmetros: `limit`, `dense_top_k`, `spo_top_k`.

**Detection (prioridade):**
1. Env `NOX_CONTEXT_WINDOW` (override absoluto)
2. Header HTTP `X-Context-Window` em `/api/search`
3. CLI flag `--context-window N`
4. Default fallback: 200K (Sonnet)

**Tier table:**

| Tier | Window | `limit` | dense top_k | SPO triples K |
|---|---|---|---|---|
| Small | <50K | 3 | 10 | 4 |
| Medium | 50-150K | 5 (default) | 20 | 8 |
| Large | 150-500K | 8 | 30 | 12 |
| Massive | >500K (Gemini, Grok, Opus 1M) | 12 | 40 | 16 |

**Implementação:**

```typescript
// src/lib/context-tier.ts
export type ContextTier = "small" | "medium" | "large" | "massive";

const TIER_THRESHOLDS: Array<[number, ContextTier]> = [
  [50_000, "small"],
  [150_000, "medium"],
  [500_000, "large"],
  [Infinity, "massive"],
];

export function detectTier(windowTokens?: number): ContextTier {
  const w = windowTokens ?? parseInt(process.env.NOX_CONTEXT_WINDOW ?? "200000", 10);
  return TIER_THRESHOLDS.find(([t]) => w <= t)![1];
}

export const TIER_SCALES = {
  small:   { limit: 3,  denseTopK: 10, spoK: 4  },
  medium:  { limit: 5,  denseTopK: 20, spoK: 8  },
  large:   { limit: 8,  denseTopK: 30, spoK: 12 },
  massive: { limit: 12, denseTopK: 40, spoK: 16 },
};
```

Integração em `searchHybrid` + `getVaultFacts` (E03b).

### Smoke + validação

- Eval por tier (variant=hybrid + override `NOX_CONTEXT_WINDOW`): comparar nDCG@10 entre tiers, ver se ganho marginal compensa custo (mais chunks = mais tokens)
- Per-agente Discord: medir antes/depois subjective utility (Toto avalia)

### NÃO FAZEMOS

- Trazer Rig/ReAct/LATS reasoning (consumers já têm próprio agent)
- Forçar consumer enviar header (env default basta)
- Bootstrap context (overlap com SPO injection)

---

## B. Context overflow protection multi-layer

### Problema atual

`getVaultFacts` tem `TOKEN_BUDGET` hardcoded (balanced=200, deep=250). `/api/search` retorna chunks até `limit` mas sem flag de truncation. Workflows encadeados (search → impact → reflect) acumulam tokens sem guardrail.

Cenário risco: Forge pede `agentic_impact` indireto (5 buscas encadeadas) → 50KB+ tokens acumulados → context overflow Anthropic API → falha cara.

### Design

**3 camadas:**

1. **Per-call truncation flag** — toda response inclui `_truncated: boolean` + bytes count
2. **Cumulative tracking** — header opcional `X-Session-Cumulative-Bytes` retornado pelo `/api/search` (current call bytes + Cumulative = next call's accumulated)
3. **Soft fail** — se `Cumulative > tier_window × 4 × 0.8`, retornar 429-equivalent: `{error: "context_budget_exhausted", suggest_restart: true}`

**Implementação:**

```typescript
// Response shape
type SearchResponse = {
  results: SearchResult[];
  vaultFacts?: string;
  _meta: {
    bytes_this_call: number;
    truncated: boolean;
    cumulative_bytes?: number;  // if X-Session-* header sent
    tier: ContextTier;
    budget_remaining_pct?: number;
  };
};
```

### Smoke + validação

- Stress test: encadear 10 chamadas `/api/search` com `X-Session-Cumulative-Bytes` → verificar fail-fast quando budget esgota
- Validar truncation flag em queries que retornam chunks longos

### NÃO FAZEMOS

- Implementar accumulation tracking SERVER-side (stateless preserved — client envia header)
- Auto-summarization de truncated content (consumer decide)

---

## C. Indexing tiers fast/balanced/full

### Problema atual

`nox-mem reindex` + `vectorize` + `kg-extract` rodam com config fixa. Pra dev local, queremos `fast` (skip kg-extract). Pra prod, queremos `full` (com KG + dual-cosine reflect cache).

Hoje workaround: env vars (`NOX_SEMANTIC_*`, etc) — funcional mas friction.

### Design

Flag `--tier {fast|balanced|full}` (default `balanced`) em 3 comandos:

| Comando | fast | balanced (default) | full |
|---|---|---|---|
| `reindex` | só chunks + FTS5 (skip vec rebuild) | + vec_chunks (sqlite-vec) | + kg-extract incremental |
| `vectorize` | só missing chunks | + lock-step KG cleanup | + dual-cosine reflect cache rebuild |
| `kg-extract` | --limit 50 | --limit 200 | --limit unlimited |

### Implementação

Adicionar `--tier` em cada subcomando, mapear pra env vars existentes (compat).

Linhas modificadas estimadas: ~80 LOC + 3 tests.

### NÃO FAZEMOS

- Mudar default behavior (mantém compat); `balanced` é o que sempre fazemos hoje
- Adicionar 4ª tier "massive" (overkill)

---

## Roadmap E15

| Semana | Ação | Output |
|---|---|---|
| Pós-R03 submit | A. Tier-aware (1-2h) | Smoke per-tier, validate Boris vs Forge subjective improvement |
| +1 dia | B. Overflow protection (1-2h) | Stress test 10-call chain, fail-fast confirmed |
| +1 dia | C. Indexing tiers (2-3h) | Refactor 3 comandos, smoke `reindex --tier fast` em dev |
| +1 sem | Documentar + commit | Spec atualizado, ROADMAP/HANDOFF refletindo |

**Pré-requisito:** R03 submit não-bloqueante (E15 é cosmético arquitetural, não muda nDCG significativamente).

**Gate ACTIVATE A:** eval per-tier mostra ≥1pp delta entre tier extremos (small vs massive) OU subjective utility report dos agentes Discord melhora.

**Gate ACTIVATE B:** stress test confirma fail-fast funcional sem regressão em queries normais.

**Gate ACTIVATE C:** smoke `--tier fast` em dev poupa ≥30% tempo vs `balanced`.

---

## Cruzamento com decisões prévias

- **D33 (Cohere fallback):** E15 NÃO substitui D01 v3. Os 2 são ortogonais — E15 melhora UX/budget; D01 v3 melhora nDCG ceiling.
- **D39 (FTS5 silent):** E15 respeita D39 — não toca em FTS5 ranking.
- **D34 (op-audit patterns):** indexing tiers (C) usa withOpAudit pra snapshot pré-op em `reindex --tier full` (já é regra crítica #6).

---

## Origem da inspiração

CodeGraph-rust ([github.com/Jakedismo/codegraph-rust](https://github.com/Jakedismo/codegraph-rust)) — Rust workspace pra code knowledge graph com tree-sitter + LSP + SurrealDB HNSW. Análise feita 2026-05-17 noite. Tooling code-specific (call chains, dependency graphs, coupling metrics) NÃO foi trazido — fora do escopo memória conversacional.
