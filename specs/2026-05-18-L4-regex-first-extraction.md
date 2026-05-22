# L4 — Regex-first typed-link extraction with Gemini fallback (gbrain-inspired)

**ID:** L4
**Status:** 📋 SPEC — implementation-ready, shadow-mode default
**Owner:** Toto (decisão); Maestro (execução)
**Data:** 2026-05-18
**Lab:** L4 (próximo após L3)
**Tagline:** *Pain-weighted hybrid memory with shadow discipline — yours by design.*
**Cross-link:** `docs/DECISIONS.md` D41 (gbrain analysis), `docs/ROADMAP.md` §Lab evolution, CLAUDE.md §regra 5 (shadow-mode mandatory pra ranking/extraction changes).
**Origem:** análise do repo [`gbrain`](https://github.com/garry-tan/gbrain) (16.6k★ MIT, Garry Tan) — sistema de memória LLM-agnóstico que extrai typed-link KG com **zero chamadas LLM**, via regex + frontmatter convention. P@5 saltou 22.1% → 49.1% em v0.12 tornando typed-link extract THE load-bearing factor.

---

## Resumo executivo

Trazer **um pedaço cirúrgico** do gbrain: regex-first typed-link extraction como **primeira camada** do KG extract, mantendo Gemini como fallback para conteúdo não-estruturado.

| Métrica | Hoje (Gemini-only) | Pós-L4 (hybrid) | Ganho esperado |
|---|---|---|---|
| OPEX Gemini KG/mês | $5-10 | $2-4 | -40% a -60% |
| Latência p95 entity file ingest | ~1.5s | <100ms (regex-only path) | -93% |
| Latência p95 prose ingest | ~1.5s | ~1.5s (fallback Gemini) | sem regressão |
| Cobertura KG | 100% (Gemini lê tudo) | ≥100% (regex + Gemini complementares) | igual ou maior |
| Retrieval nDCG@10 | 0.6813 (E14 Wave 1) | =0.6813 ± 0.0 | zero regressão (DoD) |

**Filosofia:** gbrain força convention de authoring (wikilinks + frontmatter obrigatórios) e atinge zero-LLM. Nós **NÃO forçamos convention** — aceitamos as duas formas (regex onde estruturado, Gemini onde prosa). Esse é o nuance hybrid que muda o jogo no nosso domínio mixed.

---

## 1. Motivação

### gbrain's mechanical pattern
O insight central do gbrain v0.12: **typed link extraction é o single load-bearing factor** que catapultou P@5 de 22.1% → 49.1%. E o método é mecânico — `[Name](path/to/slug)` + `[[slug]]` + frontmatter YAML extraído por regex puro. Zero LLM em hot path. Fonte: `src/core/link-extraction.ts` (~500 LOC, MIT).

A premissa do gbrain é **enforced authoring convention** — wikilinks e frontmatter são obrigatórios; sem eles, P@5 cai pro chão. Funciona porque o domínio é narrowly controlado (pessoa única authoring memórias com convention strict).

### Nuance do nosso domínio (mixed)
Nosso corpus é heterogêneo:
- **Entity files** (compiled/timeline/frontmatter sections) — altamente estruturados, ideal pra regex
- **Daily logs + conversation captures** — prose livre, sem convention enforced
- **Code snippets em specs** — refs `src/foo.ts:42` triviais pra regex
- **Specs + audits + paper** — markdown estruturado com links explícitos

Conclusão: **híbrido é o caminho**. Regex pega o low-hanging fruit (chunks structured → 60-70% do corpus); Gemini cobre o resíduo (prose livre, conversation logs).

### Por que agora
- Volume KG cresceu pra ~15.6k entities + ~21.5k relations
- Gemini KG extract custa $5-10/mês e latência 500ms-2s/chunk em hot path de ingest
- 62.9k+ chunks ativos; cada reindex paga Gemini KG na conta toda → R$ acumula
- gbrain provou que regex sozinho consegue 49.1% P@5 quando convention enforced — nosso teto upper-bound de ganho é maior porque adicionamos Gemini fallback

---

## 2. Estado atual

| Aspecto | Hoje |
|---|---|
| Pipeline | Gemini 2.5-flash em **todo chunk** durante ingest/reindex |
| Custo mensal | ~$5-10 (estimativa cron diário + ad-hoc) |
| Latência p50 KG extract | ~500ms-2s por chunk (Gemini API) |
| Cobertura | 100% (Gemini lê tudo, incluindo trivial entity refs) |
| Quality | Boa, mas paga premium em chunks que regex resolveria em <5ms |
| Storage | `kg_entities` (~15.6k) + `kg_relations` (~21.5k) — FK `source_entity_id`/`target_entity_id` INTEGER (não strings inline; ref MEMORY.md `kg_relations usa FK ids`) |
| Auditoria | `relation_reason` enum: hoje só `'gemini_extracted'` + `'manual'` |

**Inefficiency claim concreta:** entity file `memory/entities/feedback/use_voce_not_tu.md` tem 6 wikilinks no compiled section + 3 cross-refs frontmatter. Hoje Gemini lê tudo, chama API, retorna ~9 relations. Mesma extração via regex = <5ms, $0.0000.

---

## 3. Hybrid architecture proposed

### Pipeline novo

```
INGEST CHUNK
    │
    ▼
┌─────────────────────────────────────────────────────┐
│ 1. Ingest router classifica chunk type              │
│    ∈ {entity_compiled, entity_timeline,             │
│       entity_frontmatter, code, prose, daily_log}   │
└─────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────┐
│ 2. extractEntityRefsRegex(text)                     │
│    - DIR_PATTERN whitelist (17 entity types, §4.5)  │
│    - Markdown [Name](path/to/slug)                  │
│    - Obsidian [[slug]] + [[entity_type/slug]]       │
│    - Bare path refs `entity/slug`                   │
│    - Code-fence stripping (skip ``` blocks)         │
│    - Within-chunk dedup                             │
└─────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────┐
│ 3. extractFrontmatterRelations(yaml)                │
│    Typed inference per 6 rules (table §5)           │
└─────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────┐
│ 4. extractCodeRefs(text)                            │
│    - src/foo.ts:42 + specs/X.md + audits/Y.md       │
│    - Stripped from code fences (avoid recursion)    │
└─────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────┐
│ 5. SKIP-GEMINI gate (§7)                            │
│    IF section ∈ {compiled, frontmatter, timeline}   │
│       AND regex relations ≥ 1                       │
│    THEN skip Gemini                                 │
│    ELSE call Gemini KG extract                      │
└─────────────────────────────────────────────────────┘
    │                              │
    ▼ (regex-only)                 ▼ (Gemini fallback)
┌──────────────────┐    ┌────────────────────────────┐
│ relation_reason: │    │ relation_reason:           │
│ regex_extracted  │    │ gemini_extracted           │
└──────────────────┘    └────────────────────────────┘
    │                              │
    ▼                              ▼
┌─────────────────────────────────────────────────────┐
│ 6. Merge → kg_relations table                       │
│    (de-dupe por (src_id, tgt_id, relation_type))    │
│    extraction_method telemetry logged               │
└─────────────────────────────────────────────────────┘
```

---

## 4. DIR_PATTERN adapted pro nosso domain

Baseado nos entity types existentes (canonical lista do schema v10 + entity files reais em produção):

```typescript
// src/lib/regex-extract/dir-pattern.ts
export const NOX_ENTITY_TYPES = [
  'feedback',      // user feedback, hard rules
  'person',        // pessoa-entity (never-decay)
  'lesson',        // lições operacionais (180d retention)
  'decision',      // decisões arquiteturais (365d)
  'project',       // project rollups (365d)
  'team',          // team entities (120d)
  'daily',         // daily logs (90d)
  'pending',       // open items (30d)
  'graph_node',    // KG nodes (60d)
  'agent',         // agent personas (Atlas, Boris, Cipher, Forge, Lex)
  'incident',      // incident reports
  'spec',          // technical specs
  'audit',         // audit reports
  'skill',         // skill definitions
  'persona',       // user-level personas
  'reference',     // reference docs
  'system',        // system-level entities (added D52, 2026-05-21) — 17th type
] as const;

export const DIR_PATTERN = `(?:${NOX_ENTITY_TYPES.join('|')})`;
```

> **Nota:** lista acima reflete estado pós-D52 (17 types). Spec original listava 16 types; `'system'` adicionado em 2026-05-21 — ver §4.5 abaixo.

**Validação pré-implementação (T0 — antes do código):**
- Rodar `ls /root/.openclaw/workspace/tools/nox-mem/memory/entities/` na VPS, comparar contra lista acima
- Se houver entity type novo não-listado → adicionar ao DIR_PATTERN + abrir item pra `docs/DECISIONS.md`
- Se houver entity type aqui não existindo em memory/entities/ → remover do whitelist (false positive risk)
- Se entity files schema fundamentalmente incompatível → escrever `BLOCKED.md` e parar

---

## 4.5 Plural Filesystem Normalisation (D52 — 2026-05-21)

> **Emenda ao spec original (2026-05-18).** Implementada via PR #214. Decisão registrada em `docs/DECISIONS.md` §D52.

### 4.5.1 Motivação

O filesystem de produção usa **diretórios no plural** para cinco tipos de entidade:

```
memory/entities/
  agents/          ← plural no disco
  decisions/       ← plural no disco
  lessons/         ← plural no disco
  projects/        ← plural no disco
  systems/         ← plural no disco
```

Porém `kg_entities.entity_type` e o `DIR_PATTERN` original usam formas **singulares** (`agent`, `decision`, `lesson`, `project`, `system`). Um wikilink que espelha o caminho do filesystem — por exemplo `[[agents/nox]]` — não fazia match no `WIKILINK_RE` original e era silenciosamente descartado. A divergência existia desde o início mas só foi descoberta durante o cleanup do PR #210.

### 4.5.2 Implementação

A solução normaliza plural → singular **na camada de extração**, preservando a forma canônica singular em todo o pipeline downstream.

```typescript
// src/lib/regex-extract/dir-pattern.ts

/** Diretórios no filesystem que usam plural */
export const NOX_ENTITY_DIRS_PLURAL = [
  'agents',
  'decisions',
  'lessons',
  'projects',
  'systems',
] as const;

/** Mapa de normalização plural → singular */
export const PLURAL_TO_SINGULAR: Record<string, string> = {
  agents:    'agent',
  decisions: 'decision',
  lessons:   'lesson',
  projects:  'project',
  systems:   'system',
};

/**
 * Resolve um token de dir (singular ou plural) para o entity type
 * canônico (sempre singular). Retorna null se não reconhecido.
 */
export function asEntityType(dirToken: string): string | null {
  if (PLURAL_TO_SINGULAR[dirToken]) return PLURAL_TO_SINGULAR[dirToken];
  const singular = dirToken as string;
  return (NOX_ENTITY_TYPES as readonly string[]).includes(singular)
    ? singular
    : null;
}
```

O `DIR_PATTERN` é atualizado para aceitar ambas as formas:

```typescript
const allForms = [
  ...NOX_ENTITY_TYPES,
  ...NOX_ENTITY_DIRS_PLURAL,
];
// dedup (systems já está em NOX_ENTITY_TYPES como 'system')
export const DIR_PATTERN = `(?:${[...new Set(allForms)].join('|')})`;
```

Após o match de qualquer regex (`WIKILINK_RE`, `MARKDOWN_LINK_RE`, `BARE_REF_RE`), o token capturado é sempre passado por `asEntityType()` antes de ser gravado em `EntityRef.entityType`. O campo `key` (`<entityType>/<slug>`) também usa a forma singular canônica.

### 4.5.3 Adição de `'system'` como 17º tipo canônico

O diretório `memory/entities/systems/` existia em produção mas `system` não constava em `NOX_ENTITY_TYPES`. Isso causava dois problemas:

1. `ingest-entity` não reconhecia o type → chunks sem `section_boost` correto
2. `DIR_PATTERN` não capturava refs `[[system/nox-mem-api]]`

A decisão foi adicionar `'system'` como 17º membro de `NOX_ENTITY_TYPES` (estava implícito no dado; faltava só a declaração formal). Nenhuma migration de DB é necessária: `entity_type` é TEXT livre, linhas antigas com `system` já existiam corretamente.

### 4.5.4 Compatibilidade retroativa

Ambas as formas continuam sendo aceitas indefinidamente:

| Input wikilink | `asEntityType()` retorna | `EntityRef.key` |
|---|---|---|
| `[[agent/nox]]` | `'agent'` | `agent/nox` |
| `[[agents/nox]]` | `'agent'` | `agent/nox` |
| `[[decision/d52]]` | `'decision'` | `decision/d52` |
| `[[decisions/d52]]` | `'decision'` | `decision/d52` |

- Singular continua funcionando sem alteração
- Plural agora faz match e normaliza
- Nenhum arquivo de entidade precisa ser renomeado
- Nenhuma migration de DB: entity_type sempre foi singular nos dados reais

### 4.5.5 Tabela de exemplos

| Input (wikilink ou bare ref) | Dir token capturado | `asEntityType()` | `EntityRef.key` |
|---|---|---|---|
| `[[agents/nox]]` | `agents` | `agent` | `agent/nox` |
| `[[decisions/d41]]` | `decisions` | `decision` | `decision/d41` |
| `[[lessons/use-voce-not-tu]]` | `lessons` | `lesson` | `lesson/use-voce-not-tu` |
| `[[projects/memoria-nox]]` | `projects` | `project` | `project/memoria-nox` |
| `[[systems/nox-mem-api]]` | `systems` | `system` | `system/nox-mem-api` |
| `[[system/nox-mem-api]]` | `system` | `system` | `system/nox-mem-api` |
| `[[agent/atlas]]` | `agent` | `agent` | `agent/atlas` |
| `[[feedback/no-secrets]]` | `feedback` | `feedback` | `feedback/no-secrets` |
| `[[unknown/foo]]` | `unknown` | `null` → descartado | — |

### 4.5.6 Cobertura de testes

PR #214 adicionou 10 novos test cases ao suite existente:
- 8 casos de plural variants (`agents/`, `decisions/`, `lessons/`, `projects/`, `systems/` via wikilink e bare ref)
- 2 casos de `system` canonical type
- Suite completo: **57/57 passing** pós-PR

### 4.5.7 Cross-referências

- Decisão: `docs/DECISIONS.md` §D52 (2026-05-21)
- PR de implementação: PR #214
- PR de cleanup que surfou a divergência: PR #210
- PR de audit: PR #211 (confirmou `kg_relations.extraction_method` NULL em 21 518 rows — L4 nunca rodou em prod até 2026-05-24)
- Memory: `[[late-evening-2026-05-21-f10b-deployed-l4-plural]]`
- Primeiro cron L4 em prod: Sunday 2026-05-24 (agendado)

---

## 5. Frontmatter typed inference rules

Tabela canônica — implementação direta em `extractFrontmatterRelations(yaml)`:

| Frontmatter field | On chunk section | Edge type (kg_relations.relation_type) | Direction | Notas |
|---|---|---|---|---|
| `agent: <slug>` | any | `is_agent_of` | chunk_entity → agent_entity | matched contra `agent/<slug>.md` |
| `references: [a, b, c]` (array) | any | `references` | chunk_entity → target_entity per item | array iterado, uma relation por item |
| `supersedes: <slug>` | any | `supersedes` | chunk_entity → target_entity | + marca target com `superseded_at = now()` |
| `caused_by: <incident_slug>` | incident | `caused_by` | chunk_entity → incident_entity | resolved via `incident/<slug>` |
| `resolves: <issue_slug>` | spec, decision | `resolves` | chunk_entity → target_entity | bidirecional implícito (target.resolved_by computed view) |
| `decided_by: <person_slug>` | decision | `decided_by` | chunk_entity → person_entity | typed link pra accountability |
| `incident_date: <YYYY-MM-DD>` | incident | — (typed property, NOT relation) | — | grava em `kg_entities.props_json.incident_date` |

**Resolução de slug:** se frontmatter field value é `feedback/no_secrets`, resolve direto. Se é apenas `no_secrets`, tenta resolver no entity type implícito pela section (incident_date só faz sentido em incident files etc); senão, deferred pra Gemini.

**Edge case:** valor frontmatter inexistente em `kg_entities` → cria entity stub com `is_stub=true` + `created_via='regex_l4_forward_ref'` (Gemini run posterior pode hidratar).

---

## 6. Regex implementation reference (port gbrain)

**Source:** `gbrain/src/core/link-extraction.ts` (MIT, ~500 LOC). Port direto com 3 adaptações:

### 6.1 `stripCodeBlocks(text)` — port direto
Remove fenced code blocks (```...```) e inline code (\`...\`) pra evitar match em exemplos. Mantém line numbers via placeholder pra preservar offsets.

### 6.2 `extractEntityRefs(text)` — adaptado
Após `stripCodeBlocks`, run 3 regex em paralelo:
- **MARKDOWN_LINK_RE**: `/\[([^\]]+)\]\(\s*([^)]+?)\s*\)/g` — captura `[Name](path/to/slug)`. Filtra paths contendo `DIR_PATTERN` no path component.
- **WIKILINK_RE** (NOSSA adaptação): `/\[\[(?:(entities)\/)?(${DIR_PATTERN})\/([a-z0-9_-]+)\]\]/g` — aceita 2 formatos:
  - `[[entities/feedback/no_secrets]]` (recommended, future)
  - `[[feedback/no_secrets]]` (legacy fallback)
- **BARE_REF_RE**: `/(?:^|\s)(${DIR_PATTERN})\/([a-z0-9_-]+)(?=\s|[.,?!]|$)/g` — bare slugs sem brackets, common em conversation logs

Dedup intra-chunk via `Set<\`${entity_type}/${slug}\`>`.

### 6.3 `extractCodeRefs(text)` — adaptado pro nosso domain
```typescript
const CODE_REF_RE = /(?:^|[\s\(])(src|specs|audits|eval|validation|memory|paper|docs|runbooks|scripts|lessons)\/([a-z0-9_\-\/\.]+\.(ts|js|md|sh|json|yaml|yml|sql|py))(?::(\d+))?/g;
```

Captura paths nossos (e.g. `src/lib/op-audit.ts:42`, `specs/2026-05-17-E15-codegraph-inspired-improvements.md`). Resolve pra entity virtual `codepath/<normalized_path>` (cria stub se necessário).

### 6.4 Edge cases (testes obrigatórios)
- URL com query string contendo slash: `https://example.com/feedback/foo` — `BARE_REF_RE` deve ignorar (lookbehind `[\s(]` excluindo `/`)
- Markdown link com tooltip: `[Name](path "tooltip")` — strip tooltip
- Multi-line frontmatter `references` (YAML block style)
- Aspas curly Unicode em wikilinks: `[[feedback/foo]]` ≠ `[[feedback/foo]]` (smart quotes)
- Negative case: `[[file.md]]` (genérico, sem entity_type) → ignora

---

## 7. Gemini fallback gating

### Decisão de skip
Skip Gemini KG extract IFF **TODAS** condições:
1. Chunk section ∈ {compiled, frontmatter, timeline}
2. AND `regex_relations.length ≥ 1`
3. AND chunk_type NOT IN {conversation, daily_log, freeform_note}

### Decisão de run Gemini
Run Gemini IFF qualquer:
- Section ∉ {compiled, frontmatter, timeline} (e.g. prose body)
- OR chunk has 0 regex matches AND chunk_size > 50 chars (significant content)
- OR chunk_type ∈ {conversation, daily_log, freeform_note}

### Decisão de run AMBOS (regex_primary_gemini_secondary)
Run both IFF:
- Section ∈ {compiled, timeline}
- AND regex matches ≥ 3 (rich structure)
- AND chunk has prose body adjacent (mixed structured+unstructured)

Nesse caso: regex relations escritas com `relation_reason='regex_extracted'`; Gemini complementa relations não-capturadas via regex.

### Telemetry
Log per-chunk:
```typescript
{
  chunk_id: string;
  section: 'compiled' | 'frontmatter' | 'timeline' | 'prose' | null;
  extraction_method:
    | 'regex_only'
    | 'gemini_only'
    | 'regex_primary_gemini_secondary'
    | 'gemini_only_after_regex_zero';
  regex_relations_count: number;
  gemini_relations_count: number;
  gemini_call_skipped: boolean;
  latency_ms: { regex: number; gemini: number | null; total: number };
}
```

Agregado consultável via `/api/health.kgExtraction` (telemetry endpoint).

---

## 8. Stale-link reconciliation

Quando entity file é editado (detected via watcher mtime change):

1. Read prev chunks `kg_relations` WHERE `source_entity_id = entity.id` AND `relation_reason='regex_extracted'`
2. Re-run regex extraction sobre new content
3. Diff prev_set vs new_set:
   - **Added**: insert novas rows (relation_reason='regex_extracted', created_at=now())
   - **Removed**: NÃO deletar — marcar `superseded_at = now()`, `superseded_reason = 'stale_link_reconciliation'`
   - **Unchanged**: no-op
4. Audit log via `withOpAudit('regex-reconcile-<entity_slug>', ...)` (CLAUDE.md regra 6)

**Por que não delete:** audit trail (ref CLAUDE.md regra 6 `ops_audit` append-only pattern). Filter na API: `WHERE superseded_at IS NULL` para active view.

**Gemini relations side-effect:** se Gemini relations existem (relation_reason='gemini_extracted') referenciando link agora stale, **NÃO** auto-supersede — esse é dominio Gemini, deferred pra próximo Gemini run agendado.

---

## 9. Schema impact (zero migration)

### Novos valores em enum existente
`kg_relations.relation_reason` enum atual: `'gemini_extracted' | 'manual' | 'crystallized' | ...`
**Add:** `'regex_extracted'` (new variant)

### Optional telemetry field
`kg_relations.extraction_method` TEXT NULL (opcional, telemetry-only, no logic dependency):
- Values: 'regex_only' | 'gemini_only' | 'regex_primary_gemini_secondary' | 'gemini_only_after_regex_zero'
- Backfill: NULL pra rows pré-L4 (não fazemos backfill retroativo — too expensive)

### Stub entity flag
`kg_entities.is_stub` BOOLEAN DEFAULT 0 — marca entities criadas via forward-ref antes de hidratação.
`kg_entities.created_via` TEXT — 'regex_l4_forward_ref' | 'gemini_extract' | 'manual' | 'crystallize'

**Migration:** UMA migration adicionando os 2 fields. Idempotent. <50 LOC.

---

## 10. Eval methodology

### A/B comparison setup
- **Baseline**: Gemini-only extract atual (snapshot pre-L4 DB)
- **Hybrid**: nova pipeline regex-first + Gemini fallback
- **Sample**: 1000 chunks aleatórios stratified por section (250 compiled, 250 timeline, 250 prose, 250 daily/conversation)

### Métricas
| Métrica | Acceptance |
|---|---|
| **Precision regex** (% regex relations corretas vs Gemini ground-truth) | ≥95% (DoD #1) |
| **Recall regex vs Gemini** (% Gemini relations que regex também captura, em chunks structured) | ≥80% (informational, não DoD blocker) |
| **Latência p50 entity file ingest** | <50ms |
| **Latência p95 entity file ingest** | <100ms (DoD #3) |
| **Gemini calls saved** | ≥40% (DoD #2) — measured over 7d real cron runs |
| **Retrieval nDCG@10** (shadow eval) | =baseline ± 0.0 (DoD #4) — zero regressão |
| **False positive rate em prose** | ≤2% (não-DoD; informational) |

### Golden set
- 100 entity files cherry-picked + manual ground-truth annotation (relations correct/incorrect/missing)
- Stored em `eval/golden-l4-regex-extract.jsonl`
- Re-validated pre-prod via `nox-mem eval --golden l4`

### Telemetry-driven decision
Após 7d shadow:
- Gemini cost delta (real $ saved)
- Retrieval nDCG@10 delta (shadow eval roda diário)
- False positive incidents (manual triage Toto)

---

## 11. Implementation tasks

**Total estimado: ~15-18h.** Numeradas em ordem de dependência:

| ID | Task | Effort | Dependência |
|---|---|---|---|
| T0 | Validação entity types real (ls VPS memory/entities/ → diff vs DIR_PATTERN proposed) | 0.5h | — |
| T1 | Port `stripCodeBlocks` + helpers (offset preservation) | 2h | T0 |
| T2 | DIR_PATTERN + ENTITY_REF_RE + WIKILINK_RE + BARE_REF_RE | 2h | T1 |
| T3 | `extractEntityRefsRegex` impl + 30+ test cases (positive, negative, edge, Unicode) | 3h | T2 |
| T4 | `extractFrontmatterRelations` impl + 6 typed rules table validation | 2h | T2 |
| T5 | `extractCodeRefs` (port direto, ajustar paths nossos) | 1h | T1 |
| T6 | Ingest router integration — pre-Gemini regex pass + skip-decision logic + telemetry log | 3h | T3, T4, T5 |
| T7 | Stale-link reconciliation on entity file update (watcher integration + withOpAudit wrap) | 2h | T6 |
| T8 | Eval harness A/B sample 1000 chunks + golden set 100 entity files | 3h | T6 |
| T9 | Documentation (CLAUDE.md L4 section) + telemetry queries (`/api/health.kgExtraction`) | 1-2h | T8 |

**Sub-totais:** 0.5 + 2 + 2 + 3 + 2 + 1 + 3 + 2 + 3 + 1.5 = **20h pessimista**, ~15h otimista (T1+T5 são port direto). Stop-after-T6 mínimo viável shadow.

---

## 12. DoD (Definition of Done)

Six numbered criteria — todos must pass:

1. **Regex extraction precision ≥95%** em golden set (100 entity files annotated manually)
2. **OPEX reduction Gemini KG ≥40%** measured over 7d (Gemini API calls count vs baseline pre-L4)
3. **Latência p95 entity file ingest <100ms** (vs current ~1.5s with Gemini) — measured via `/api/health.kgExtraction.latency_p95`
4. **Retrieval nDCG@10 zero regression** (shadow ≥7d via `nox-mem eval --golden`) — baseline 0.6813 (E14 Wave 1)
5. **Frontmatter typed relations populate kg_relations correctly** per 6 rules (§5) — validated via spot-check 20 entity files manualmente
6. **Stale-link reconciliation** removes superseded refs on entity file edit — validated via integration test (edit entity, verify `superseded_at` populated, no DELETE rows)

---

## 13. NÃO-fazemos (v1)

| Item | Razão |
|---|---|
| NÃO eliminamos Gemini KG extract | Hybrid é o ponto — Gemini stays como fallback obrigatório pra prose |
| NÃO forçamos convention de authoring nas nossas entity files | gbrain força (enforced markdown rules); nós aceitamos as duas formas. Mudar authoring convention é breaking change pra todo agente. |
| NÃO mudamos schema relations (FK structure) | `kg_relations` JOIN dual já é canônico (MEMORY.md `kg_relations usa FK ids, NÃO strings inline`); só adicionamos enum value + optional telemetry field |
| NÃO suportamos qualified wikilinks `[[source-id:slug]]` em v1 | gbrain has it pra multi-source; nosso domain single-source pra agora; defer pra L4.1 se needed |
| NÃO fazemos retroactive backfill | Pre-L4 rows ficam com `extraction_method=NULL`; forward-only |
| NÃO removemos `gemini_extracted` relations existentes | Coexistem com `regex_extracted`; dedup via UNIQUE INDEX (src, tgt, type) prefere mais recente |

---

## 14. Riscos + mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Regex precision <95% pra nossas entity files | Médio | Alto (rollback) | 30+ test cases (T3) + eval real corpus (T8) + opt-in via env `NOX_L4_REGEX_ENABLED=1` inicial |
| False positives em prose mencionando slug-like words (e.g. "feedback/" no meio de prose) | Médio | Médio (KG noise) | `stripCodeBlocks` + DIR_PATTERN whitelist + `BARE_REF_RE` lookbehind exigindo whitespace/start; eval mede FP rate |
| Gemini removida onde deveria estar (skip gate agressivo) | Médio | Alto (recall loss) | Shadow run 7d antes de ativar (regra CLAUDE.md #5); telemetry mede `gemini_call_skipped` rate per section |
| Drift entre regex e Gemini output formats | Baixo | Médio | `relation_reason` enum + `extraction_method` telemetry tracking origem; dedup UNIQUE INDEX previne duplicate rows |
| JS regex Unicode boundary fails em PT acentos (`feedback/atenção_português`) | Médio | Médio (slug naming) | Test cases T3 inclui Unicode; usar pattern `(?<=^|\s)...(?=\s|[.,?!]|$)` (MEMORY.md `JS regex \b falha em Unicode`) em vez de `\b` |
| Watcher race condition durante stale-link reconciliation | Baixo | Médio (corruption) | Wrap em `withOpAudit()` (CLAUDE.md regra 6); snapshot pre-op atomico; recovery via `safeRestore()` |
| Forward-ref entity stubs proliferam (Gemini nunca roda pra hidratá-los) | Baixo | Baixo (cosmetic) | Cron nightly: `kg-hydrate-stubs` roda Gemini só nos stubs is_stub=1 mais recentes (limit 100/dia) |

---

## 15. Shadow rollout plan (CLAUDE.md regra #5)

### Week 1 — Implementation + shadow
- T0-T9 complete
- Feature flag: `NOX_L4_REGEX_ENABLED=1` (default off)
- Regex pipeline roda em **shadow**: escreve em `kg_relations` com `relation_reason='regex_extracted'` MAS Gemini também roda (no skip gate active yet)
- Result: rows duplicadas (regex+gemini) detectable via `extraction_method` field, dedup UNIQUE INDEX previne corruption
- Telemetry collected daily via `/api/health.kgExtraction`

### Week 2 — A/B eval
- Run `nox-mem eval --golden l4` daily (telemetry-driven)
- Compare:
  - Regex relations vs Gemini relations (precision/recall por section)
  - Retrieval nDCG@10 com vs sem `relation_reason='regex_extracted'` rows (shadow eval)
  - Gemini cost real (DoD #2) — projection from shadow data
- Toto reviews telemetry mid-week; mid-course correction se needed

### Week 3 — Decisão go/no-go
Baseado em DoD #1-6:
- **All pass**: enable skip gate em prod (`NOX_L4_SKIP_GEMINI=1`), Gemini cost cap monitora savings real over 7d
- **Some fail**: feature stays como `regex_extracted` annotation only — relations escritas mas Gemini também roda; revisita em L4.1
- **Critical fail (regression nDCG)**: rollback skip gate, mantém regex extraction pra audit/telemetry only

### Week 4+ — Steady state
- `relation_reason='regex_extracted'` é canonical pra structured content
- Stale-link reconciliation runs em watcher events
- Quarterly review: ajustar DIR_PATTERN se entity types novos surgirem; revisitar gating thresholds

---

## 16. Cross-references

### Licença + atribuição
gbrain license **MIT** permite port direto da regex logic. Atribuição:
- Citar em CLAUDE.md §L4 section: "Regex-first extraction port inspired by gbrain (Garry Tan, MIT, 16.6k★)"
- Citar em paper técnico futuro: §Related Work nova subseção "Mechanical KG extraction (gbrain)"
- Header em `src/lib/regex-extract/link-extraction.ts`: comment block "Adapted from gbrain/src/core/link-extraction.ts (MIT)"

### Specs relacionadas
- `docs/DECISIONS.md` D41 (gbrain analysis — esta sessão)
- `specs/2026-05-17-E15-codegraph-inspired-improvements.md` (tier-aware retrieval; complementar, não conflito)
- `specs/2026-05-10-E14-retrieval-evolution.md` (Wave 1 baseline nDCG 0.6813)
- CLAUDE.md regra #5 (shadow-mode mandatory)
- CLAUDE.md regra #6 (op-audit + snapshot pre-destructive)
- MEMORY.md `kg_relations usa FK ids, NÃO strings inline` (schema constraint)
- MEMORY.md `JS regex \b falha em Unicode` (Unicode boundary handling)
- MEMORY.md `Ship ranking changes in shadow-mode first` (rollout discipline)

### Refs futuras
- L4.1: qualified wikilinks `[[source-id:slug]]` (multi-source support, defer)
- L4.2: extractor pra inline citations `(per [feedback/no_secrets])` em prose (próximo nível regex)
- L5: KG embeddings — usar `regex_extracted` relations como anchor pra dense KG embedding training set

---

## Open questions pra Toto

1. **DIR_PATTERN final**: ~~aceito a lista de 15 entity types proposta em §4~~ RESOLVIDO — lista final tem 17 types (incluindo `system` como 17º, D52, PR #214). Plural filesystem forms (`agents/`, `decisions/`, `lessons/`, `projects/`, `systems/`) aceitas via normalisation (§4.5). T0 dispensado para este item.
2. **Stub policy**: forward-ref stubs (entity criada via regex antes de existir em `kg_entities`) deve criar entity stub automaticamente, ou só logar warning e skip? Proposta = create stub. Alternative = warning-only mais conservador.
3. **Skip gate vs annotation-only inicial**: começar com skip gate em shadow (default off), ou começar mais conservador com regex-as-annotation (escreve relations mas Gemini sempre roda) por 2 weeks antes de testar skip? Proposta atual = shadow com skip gate testado em Week 2.
4. **Eval golden set ownership**: quem anota os 100 entity files manualmente em T8? Toto direto ou agent designate (Atlas com review Toto)? Annotation quality is DoD-blocking.

---

**Status final do spec:** READY pra implementation. Bloqueio único: T0 (validação entity types real na VPS) — se houver schema mismatch fundamental, abrir `BLOCKED.md` antes de T1.
