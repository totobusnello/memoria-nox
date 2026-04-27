# Merge do "Claude Memory Setup" paper com nox-mem v3.6d

**Data:** 2026-04-21
**Fonte externa:** `/Users/lab/Desktop/claude-memory-setup copy.pdf` — arquitetura de memória file-based tiered com salience scoring + compiled truth + typed retention
**Status:** Backlog — 3 propostas priorizadas pra Fase 1.7b/2.x sem desviar do plano atual (IM → Fase 2 → ...)

---

## TL;DR

O paper tem 3 ideias que resolvem problemas reais do nosso sistema:

| # | Ideia | Problema que resolve | Esforço | Impacto | Ordem recomendada |
|---|-------|----------------------|---------|---------|-------------------|
| 1 | **Typed source retention matrix** | Feedbacks expiram como daily; lessons decay rápido demais; research antiga polui FTS | **2h** | 🔥 Alto | **1º** (quick win) |
| 2 | **Salience formula formal** (`recency × pain × importance`) | `tiers evaluate` é opaco, sem fórmula auditável; ranking de search não considera dor/importância | **4h** | 🔥 Alto | **2º** |
| 3 | **Compiled truth + timeline append-only** page format | CLAUDE.md drift; fatos contraditórios coexistem; nada "recompila" verdade corrente | **1-2 dias** | 🔥🔥 Muito Alto (arquitetural) | **3º** (depois do IM) |

**Valor total estimado:** redução de custo de consolidation + melhor ranking + zero drift entre sessões. Alinha nox-mem com best practices do campo sem grande refactor.

---

## Proposta 1 — Typed Source Retention Matrix (2h)

### Problema hoje
Todos os chunks têm mesma política de TTL implícita. Na última `tiers evaluate` (2026-04-20), 42 chunks foram promovidos sem critério documentado. Feedbacks de usuário podem virar `peripheral` e eventualmente serem considerados pra archive. Lessons de falhas reais decay igual a daily session notes.

Também temos no DB: 17 feedbacks (nunca deveriam expirar), 38 lessons (mistakes caros — valem 180d+), 610 daily entries (decay natural 90d). Sem diferenciação, todos são tratados como recency-based apenas.

### O que o paper propõe

| Type | Retention |
|------|-----------|
| implementation | 90d |
| **failure** | **180d** (mistakes caros) |
| **user-feedback** | **Never auto-decay** |
| **research** | 60d (market data stale) |
| code-review | 90d |
| git-history | 90d |
| session | 90d |
| consolidation | follows parent |

Personal tier (user rules/credentials) = nunca auto-decay.

### Design de merge com nosso sistema

**Schema change** (migration v8):
```sql
ALTER TABLE chunks ADD COLUMN retention_days INTEGER;  -- NULL = never-decay
ALTER TABLE chunks ADD COLUMN expires_at TEXT GENERATED ALWAYS AS
  (CASE WHEN retention_days IS NULL THEN NULL
        ELSE datetime(created_at, '+' || retention_days || ' days')
   END) VIRTUAL;
CREATE INDEX idx_chunks_expires_at ON chunks(expires_at) WHERE expires_at IS NOT NULL;
```

**Mapping `chunk_type` → `retention_days`** (populated via migration + default no ingest):
```javascript
const RETENTION_BY_TYPE = {
  feedback:      null,   // never auto-decay (17 chunks)
  lesson:        180,    // 180d — mistakes caros (38 chunks)
  decision:      365,    // decisions têm lifespan longo (135 chunks)
  project:       365,    // projetos duram (15 chunks)
  person:        null,   // pessoas não "expiram" (6 chunks)
  daily:         90,     // session notes (610 chunks)
  team:          120,    // team state evolui (961 chunks)
  digest:        180,    // digest consolida várias sessões (7 chunks)
  pending:       30,     // se 30d sem resolver, escala pra review
  other:         90,     // default
};
```

**Ingest side** (`ingest.ts` + `graphify-ingest.ts`):
- Ao inserir chunk, computar `retention_days = RETENTION_BY_TYPE[chunk_type] ?? 90`
- User pode override via comment no .md: `<!-- retention: never -->` ou `<!-- retention: 365 -->`

**Consolidation/tier evaluation side** (`tiers evaluate` + nightly Phase):
- Query `SELECT id FROM chunks WHERE expires_at < datetime('now') AND tier != 'core'`
- Esses candidatos vão pra **archive** (soft-delete com entry em `dedup_log`)
- Core tier sempre preservado (user-declared importance)

**Backfill** pros 2073 chunks existentes:
```sql
UPDATE chunks SET retention_days = CASE chunk_type
  WHEN 'feedback' THEN NULL
  WHEN 'lesson' THEN 180
  WHEN 'decision' THEN 365
  ...
END WHERE retention_days IS NULL;
```

### Métricas de sucesso
- `SELECT COUNT(*) FROM chunks WHERE retention_days IS NULL GROUP BY chunk_type` → feedback+person nunca expira
- `nox-mem stats --retention` mostra distribuição de expiração (quantos chunks vão expirar nos próximos 30d, 90d, etc)
- Zero feedback arquivado inadvertidamente

### Esforço
- 2h: 30min schema migration, 1h mapping + ingest logic, 30min backfill + testes

---

## Proposta 2 — Salience Formula Formal (4h)

### Problema hoje
`tiers evaluate` promoveu 42 chunks em 2026-04-20 sem fórmula visível. Nosso search hybrid faz FTS BM25 + semantic cosine + RRF fusion, mas **não considera age/importance/pain** do chunk. Um chunk "falhou o deploy em produção" tem o mesmo weight que um "rodei npm install".

Campos que JÁ temos em `chunks`:
- `last_accessed_at` ✅
- `access_count` ✅
- `importance REAL` ✅ (mas mal populado)
- `tier` (core/working/peripheral) ✅
- FALTA: `pain` (severity da experiência — crash vs trivial)

### O que o paper propõe

```
salience = recency × pain × importance     (cada 0-1)

recency    = max(0, 1 - days_since_last_use / tier_decay_threshold)
             personal skipa (always 1.0)
pain       = 0.1 trivial → 1.0 prod-outage / data-loss
             dominates retention for mistake_* / incident entries
importance = 0.2 project-only → 1.0 user-declared rule
             dominates retention for personal/ entries
```

Thresholds:
- ≥ 0.7 → Promote (episodic → semantic, working → core)
- 0.4 - 0.7 → Retain current tier
- 0.15 - 0.4 → Review on next consolidation (flag)
- < 0.15 → Archive

### Design de merge

**Schema change** (migration v9):
```sql
ALTER TABLE chunks ADD COLUMN pain REAL DEFAULT 0.2;  -- 0.1-1.0
```

**Heuristic populator para `pain`** (run once no backfill + novo default no ingest):
```javascript
function inferPain(chunk) {
  const text = chunk.chunk_text.toLowerCase();
  if (chunk.chunk_type === 'lesson') return 0.8;  // lessons = post-mortem
  if (/(crash|outage|data.loss|prod.broken|revert|rollback)/.test(text)) return 1.0;
  if (/(bug|error|fail|timeout|regress)/.test(text)) return 0.5;
  if (/(warn|deprec|slow)/.test(text)) return 0.3;
  return 0.2;
}
```

**Heuristic populator para `importance`** (já existe mas mal populado):
```javascript
function inferImportance(chunk) {
  if (chunk.chunk_type === 'feedback') return 1.0;       // user-declared
  if (chunk.chunk_type === 'decision') return 0.8;
  if (chunk.source_type === 'user_statement') return 0.9; // V7 field
  if (chunk.chunk_type === 'lesson') return 0.7;
  if (chunk.chunk_type === 'daily') return 0.3;
  return 0.4;
}
```

**Salience function** em `src/salience.ts`:
```typescript
export function calculateSalience(chunk: Chunk, now = Date.now()): number {
  // Personal tier never decays by recency
  if (chunk.chunk_type === 'feedback' || chunk.chunk_type === 'person') {
    return chunk.importance * (chunk.pain ?? 0.2);  // no recency factor
  }
  const days = (now - new Date(chunk.last_accessed_at ?? chunk.created_at).getTime()) / 86400000;
  const threshold = chunk.retention_days ?? 90;
  const recency = Math.max(0, 1 - days / threshold);
  return recency * (chunk.pain ?? 0.2) * (chunk.importance ?? 0.4);
}
```

**Hooks de uso**:

1. **`tiers evaluate`** — novo algoritmo:
   ```
   score ≥ 0.7 + tier='peripheral' → promote to working
   score ≥ 0.7 + tier='working'    → promote to core
   0.4 ≤ score < 0.7               → retain
   0.15 ≤ score < 0.4              → flag needs_review in a new review_queue table
   score < 0.15 + tier != 'core'   → archive (move to archive/ + dedup_log entry)
   ```

2. **Hybrid search ranking** — multiplicar por salience:
   ```typescript
   // em search.ts:
   // hoje: finalScore = RRF(fts, semantic) * TIER_BOOST * recency_boost
   // proposto: finalScore = RRF(fts, semantic) * calculateSalience(chunk)
   //           substitui TIER+recency+importance boosts redundantes
   ```
   (Atenção: evita stacking multiplicativo — lição v3.4. Se preciso manter TIER_BOOST, fazer aditivo ou normalizar)

3. **`/api/health`** — expor distribuição de salience:
   ```json
   "salienceDistribution": {
     "promote_candidates": 42,   // >= 0.7 not in core
     "archive_candidates": 156,  // < 0.15 not in core
     "review_needed": 87
   }
   ```

### Métricas de sucesso
- Ranking de search: mesma query antes/depois — top-3 muda? (A/B com 5 queries típicas)
- `tiers evaluate` output bate com thresholds (auditável)
- Zero regression no canary semantic

### Esforço
- 4h: 30min schema + pain field, 1h populators + backfill, 1h função + tests, 1h integration em tiers evaluate, 30min no `/api/health`

### Risco
- Médio — pode mudar ranking existente. Mitigação: rodar em shadow-mode (calcula salience mas não aplica no ranking) por 1 semana, comparar com ranking atual, ativar depois.

---

## Proposta 3 — Compiled Truth + Timeline Append-Only (1-2 dias)

### Problema hoje (maior ganho potencial)
Arquivos em `memory/*.md` são estruturas flat. `memory/projects.md` tem 15+ projetos num único arquivo. `memory/decisions.md` tem 135 decisions cronológicas. Resultado:
- **Drift de fatos**: "Nox chief of staff" aparece 3x em contextos diferentes — qual é a versão atual?
- **Nada "recompila"** a verdade corrente — agente sempre lê timeline inteiro e pode pegar info desatualizada
- **Search retorna entries antigas**: query "qual status do projeto X?" pode retornar decision de 3 meses atrás antes de decision recente

CLAUDE.md do próprio memoria-nox é exemplo: cresceu de 40 pra 224 linhas em 1 mês, misturando estado atual com histórico.

### O que o paper propõe

Cada entidade tem UM arquivo com este formato:

```markdown
---
name: Nox
description: Chief of Staff & COO do time de 6 agentes
type: reference
---

{Compiled truth — CURRENT best understanding. REWRITTEN as evidence changes.
3-10 lines covering the actionable state.}

- Role: Chief of Staff & COO, delega pros 5 especialistas
- SessionKey: `agent:nox:discord:channel:1480051272508772372`
- Model: `anthropic/claude-sonnet-4-6` via RelayPlane
- Heartbeat: `*/15min` com `lightContext: true`

---

## Timeline

- **2026-04-21** — [user-feedback] Toto confirmou delegação Nox→Atlas validada (D3)
- **2026-04-20** — [implementation] Heartbeat `to` format migrado (channelId → to)
- **2026-04-18** — [failure] Semantic layer morta — canary detectou
- **2026-03-31** — [implementation] Duplicate bot telegram eliminated (v3.2)
```

**Regras**:
- Compiled truth é **REWRITTEN** quando entendimento muda (não append)
- Timeline é **APPEND-ONLY**, reverse-chronological — nunca editado
- Contradictions entre compiled e timeline são **flagged explicitly**

### Design de merge

**Novo diretório**:
```
memory/entities/
├── agents/
│   ├── nox.md
│   ├── atlas.md
│   ├── boris.md
│   ├── cipher.md
│   ├── forge.md
│   └── lex.md
├── projects/
│   ├── granix-app.md
│   ├── frooty.md
│   ├── galapagos.md
│   └── ...
├── systems/
│   ├── nox-mem.md       ← substitui grande parte do CLAUDE.md
│   ├── relayplane.md
│   ├── openclaw-gateway.md
│   └── graph-memory-plugin.md
└── people/
    ├── toto.md
    └── ...
```

**Schema change** (migration v10):
```sql
-- Novo campo pra distinguir tipo de seção dentro do chunk
ALTER TABLE chunks ADD COLUMN section TEXT;  -- 'compiled' | 'timeline' | 'frontmatter'
-- Score boost pra compiled truth em search
-- (aditivo pra evitar stacking — lição v3.4)
ALTER TABLE chunks ADD COLUMN section_boost REAL DEFAULT 1.0;
```

Ingest pipeline novo (`ingest-entity.ts`):
```
read memory/entities/<type>/<entity>.md
parse frontmatter (name, description, type)
split in 3 sections:
  - frontmatter → 1 chunk (section='frontmatter', boost=1.5)
  - compiled_truth → 1 chunk (section='compiled', boost=2.0)
  - timeline entries → N chunks (section='timeline', boost=0.8)
```

**Search behavior muda**:
- Pergunta "qual status atual do projeto X?" → top result é `compiled` chunk do X
- Pergunta "o que aconteceu com X em Mar?" → filtra section='timeline' + date range
- Hoje: 2 queries diferentes podem retornar mesmo chunk timeline antigo — ruim

**Migração do existente** (1 script automatizado):
- Parse `memory/projects.md` → quebra em `memory/entities/projects/<slug>.md`
- Parse `memory/decisions.md` → agrupa por entidade mencionada → adiciona a `memory/entities/<type>/<entity>.md#timeline`
- Parse CLAUDE.md v3.6d → extrai componentes pra `memory/entities/systems/*.md`
- Dry-run primeiro, validação manual de 2-3 entities, depois batch

**Hook novo — `/memory-recompile`** (skill):
- Lê timeline de uma entity
- Usa Gemini Flash-Lite pra reescrever compiled truth refletindo timeline recente
- Flagsa contradictions (ex: timeline diz "model=Sonnet" mas compiled diz "model=Haiku" → warning)
- Commita alteração

**Ou automático** — rodar `/memory-recompile <entity>` quando timeline ganha ≥ 3 novas entries desde último recompile.

### Benefícios
1. **Zero drift**: compiled truth é source-of-truth auditável, timeline é evidência
2. **Search preciso**: "status atual" bate em compiled, "história" bate em timeline
3. **Agentes entram na sessão mais rápido**: ler `memory/entities/<project>.md` = contexto completo em 100 linhas
4. **Graph-memory bate perfeito**: já trabalha com entities/turns — compiled truth é "summary", timeline é "turn history"
5. **CLAUDE.md do memoria-nox vira pointer**: ao invés de 300 linhas, aponta pra `memory/entities/systems/nox-mem.md`

### Esforço real
- **Dia 1 (8h)**: schema + ingest-entity.ts + migração do memory/projects.md (piloto, 15 projetos)
- **Dia 2 (4-6h)**: /memory-recompile skill + extend pra decisions + lessons + people + commit

### Risco
- **Alto** — é arquitetural. Mitigação: fazer em branch `feat/entity-format`, rodar paralelo ao sistema atual por 1 semana, validar que search não regrediu, merge depois.

### Como fica **super afiado**

Se combinado com propostas 1 e 2:
- Cada `memory/entities/<entity>.md` tem `retention_days` via frontmatter (proposta 1)
- `compiled_truth` chunk ganha salience boost automático (proposta 2) — é rewritten = recency=1.0, é user-declared = importance=0.9
- `timeline` chunks decay natural, `compiled` persiste

Triple compounding: **retention correto + ranking correto + estrutura correta**.

---

## Ordem de rollout recomendada

### Agora — NÃO (desvia do plano)
Toto foi claro: plano operacional primeiro. IM (import repos) → Fase 2 Graphify scale → 1.7b. Essas 3 propostas **não devem atrapalhar isso**.

### Quando incluir no roadmap

**Fase 1.7b (Memory Quality advanced)** — hoje está BLOCKED by Fase 2. Quando destravar:
- **Semana 1 da 1.7b**: Propostas 1 + 2 (typed retention + salience formula) — 6h total, baixo risco
- **Semana 2 da 1.7b**: Proposta 3 (compiled truth + timeline) — 1-2 dias, arquitetural

Ou então: se o Toto quiser **adiantar a proposta 1 (typed retention)** — é quick-win de 2h pode entrar entre fases sem desviar.

### Atualização proposta do Roadmap v1.3

Adicionar ao `2026-04-19-unified-evolution-roadmap.md`:

```
| 1.7b-a | Typed retention matrix            | ⏳ READY (2h)   | IM   | retention_days por chunk_type; feedback+person never-decay |
| 1.7b-b | Salience formula formal           | ⏳ READY (4h)   | 1.7b-a | recency × pain × importance ; tiers + search ranking |
| 1.7b-c | Compiled truth + timeline format  | 🔒 BLOCKED (1-2d) | 1.7b-b | memory/entities/<type>/<entity>.md ; /memory-recompile skill |
```

---

## Decisões pra Toto revisar

1. **Adicionar essas 3 propostas ao roadmap como 1.7b-a/b/c?** Vai.
2. **Adiantar 1.7b-a (typed retention)** pra antes do IM? Risco zero, 2h, alto impacto. **Minha recomendação: sim**, fazer junto com o IM porque os novos repos importados já entram com retention correto.
3. **Proposta 3 (compiled truth)** fazer só depois do IM + Fase 2 estável? **Sim** — depende de dados vivos pra validar benefício real.

---

## Se fizer, o que muda no sistema?

Depois das 3 propostas integradas:

| Métrica | Antes (v3.6d) | Depois (v3.7?) |
|---------|---------------|----------------|
| Search: "status atual de X" | retorna timeline antigo misturado | retorna `compiled` chunk (fresco, atual) |
| Feedback retention | decay natural como daily | never-decay (preservado) |
| Ranking auditável | heurística implícita | fórmula documentada (recency × pain × importance) |
| CLAUDE.md drift | 300+ linhas por sistema | arquivos entity curtos, CLAUDE.md é pointer |
| Consolidation efficiency | varre tudo | só considera chunks com `expires_at < now` |
| Novo agente no boot | lê memory/*.md inteiro | lê `memory/entities/<role>.md` = 100 linhas curtas |

**Resumo**: passamos de "monte de memória textual" pra "knowledge base estruturado com auditabilidade e ranking determinístico". Mesma quantidade de dados, infinitamente mais navegável.

---

*Gerado 2026-04-21 pós-análise do paper Claude Memory Setup. Plano pra Fase 1.7b — não executar agora, deixa IM e Fase 2 destravar primeiro.*
