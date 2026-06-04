# F1 — `GET /api/brief` Implementation Spec

**Status:** ✅ COMPLETO 2026-06-04 — LIVE em prod (PR #1 fac47c74 + v1.1 polish PR #2 e4c794c0)
**Data:** 2026-06-04
**PRD:** `2026-06-04-session-priming-loop.md` (§6 contrato, §9 Fase 1)
**Repo de implementação:** nox-mem na VPS (`/root/.openclaw/workspace/tools/nox-mem/`)

---

## 1. Objetivo

Endpoint de priming: retorna os top-N chunks por **salience** filtrados por escopo, em formato digest compacto (pointer pattern). Read-only, $0/query, sem FTS nem embedding call. Alvo p50 < 100ms.

## 2. Decisões de design

### 2.1 Scope mapping (VALIDADO no T0 — 2026-06-04)

Não existe coluna `project`/`agent` em `chunks` — a coluna de path é **`source_file`** (relativa, não `file_path` como docs sugeriam). T0 confirmou que os prefixos separam escopos de forma **limpa e natural**:

| Namespace (prefixo `source_file`) | Conteúdo | Scope |
|---|---|---|
| `sessions/<persona>/...` | Capturas de sessão por agente (cipher 7.6k, atlas 3.8k...) | `agent=<persona>` |
| `memory/mac-docs/<DOMÍNIO>/...` | Docs do Toto por domínio (NUVIVI, PESSOAL, CONTRATOS, PPR...) | `scope=<domínio>` |
| `shared/imports/Claude/Projetos/<projeto>/...` | Workspace Mac por projeto (memoria-nox etc.) | `scope=<projeto>` |
| `shared/imports/<outros>/...` | Galapagos, skills, agents catalog | `scope=<root do import>` |

**Decisão v1 (confirmada):** mapeamento por prefixo de `source_file`, zero migration. Resolver scope = matching nos 2-3 primeiros segmentos do path. ⚠️ **Correção vs proposta original:** o padrão `/agents/<X>/` do `deriveDbSource()` NÃO serve — na prática casa com o catálogo de agents importado do Mac (`shared/imports/Claude/agents/02-language.../`), não com personas. Personas vivem em `sessions/<persona>/`.

### 2.2 Ranking

`ORDER BY salience DESC` — salience computada server-side da mesma forma que `/api/health.salience` (recency × pain × importance, clamp [0.3, 1.5]). **Independente de `NOX_SALIENCE_MODE`**: o brief não altera ranking de search; consome a fórmula diretamente. T0 confirma o mode ativo em prod (docs divergem: CLAUDE.md diz shadow default; D48/audits dizem salience v2 additive ativa no stack canônico).

⚠️ Regra #5 do repo: este endpoint **não toca** scoring de search. Qualquer ajuste de pesos da fórmula é PR separado `tune(search):`.

### 2.3 Read tracking (REDESENHADO no T0)

⚠️ **T0 finding: tabela `reads_audit` NÃO existe** no DB de prod (só `ops_audit` e `conflict_audit` — a memória sobre A2-P3 descrevia um wrapper, não esta tabela). `access_count`/`last_accessed_at` são colunas diretas de `chunks`.

**Novo design (melhor que o original):** brief **NÃO toca `access_count`** — o sinal orgânico fica 100% puro pro audit do Cipher (item 4 do plano). Tracking do brief vai pra tabela própria:

```sql
CREATE TABLE IF NOT EXISTS brief_log (
  id INTEGER PRIMARY KEY,
  chunk_id INTEGER NOT NULL REFERENCES chunks(id),
  scope TEXT NOT NULL,
  agent TEXT,
  served_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_brief_log_chunk ON brief_log(chunk_id, served_at);
```

Migration mínima (tabela nova, zero ALTER em `chunks`). **Follow-up rate** (métrica §10 do PRD) = chunk em `brief_log` que recebe incremento orgânico de `access_count` em ≤ 24h.

### 2.4 `one_liner`

Primeira linha não-vazia do chunk, strip markdown, cap 140 chars. Chunks de entity com `section='compiled'` usam a primeira linha da seção compiled (já é o sumário curado).

### 2.5 Budget

`format=text`: corta em `n` itens OU ~1.200 tokens estimados (chars/4), o que vier primeiro. `token_estimate` sempre no response JSON.

## 3. Contrato (normativo — copiado do PRD §6)

```
GET /api/brief?scope=<string>&n=<int=10,cap25>&format=<json|text>&since=<dur>&agent=<string>
```

- `scope` obrigatório (projeto/domínio; `global` aceito). `agent` filtro opcional (decisão review Q1: projeto = chave primária, agente = refinamento).
- `since` opcional: compõe com salience — `WHERE updated_at >= now()-since` antes do ORDER BY.
- Response JSON: `{scope, generated_at, items[{id,title,one_liner,type,pain,salience,age_days}], token_estimate}`.
- `format=text`: linhas `[<type>|pain <p>] <title> — <one_liner> (id)`, header 1 linha com scope+data. Pronto pra stdout de hook.
- Erros: 400 scope ausente/inválido; 200 com `items:[]` para scope válido sem chunks (não é erro).

## 4. Non-goals (v1)

- Auth/bind Tailscale → Fase 2 do PRD (hoje API é 127.0.0.1, unauth by design, edge proxy cuida de TLS+auth).
- Composição com KG, dedup semântico entre itens, personalização por histórico → v2 se métricas pedirem.
- Qualquer mudança em scoring de `/api/search`.
- Migrations em `chunks` (v1 = zero ALTER).

## 5. Tasks

### T0 — Validação read-only do schema em prod ✅ EXECUTADO 2026-06-04
> Autorizado por Toto; SSH read-only `root@187.77.234.79`, DB `/root/.openclaw/workspace/tools/nox-mem/nox-mem.db` (1.7GB).
- [x] `PRAGMA table_info(chunks)` — 25 colunas; path = **`source_file`** (não `file_path`); `access_count`, `last_accessed_at`, `importance` (0.5), `pain` (0.2), `confidence` (0.8), `tier`, `memory_type` confirmadas
- [x] Distribuição de prefixos — namespaces limpos (§2.1): `sessions/<persona>/`, `memory/mac-docs/<domínio>/`, `shared/imports/...`
- [x] Padrão `/agents/<X>/` — REFUTADO como sinal de persona (é catálogo importado); personas = `sessions/<persona>/`
- [x] `reads_audit` — NÃO existe; redesign §2.3 (`brief_log` própria, access_count intocado)
- [x] Salience mode em prod = **`active`** (mean 0.4177, median 0.3888) — resolve divergência docs (CLAUDE.md dizia shadow)

#### T0 findings — fatos de prod (2026-06-04)
| Fato | Valor | Implicação |
|---|---|---|
| Corpus | **100.562 chunks** (docs diziam 62.9k) | bench de latência usa 100k+ |
| vectorCoverage | 100.555/100.562 | saudável |
| KG | **15.613 entities / 21.519 relations** (docs: ~402/544 — stale) | docs precisam refresh |
| chunk_type | team 52k, other 34k, distilled 11.9k, daily 1.1k; lesson 17, decision 3 | tipos curados são raros — brief não pode depender só de type |
| tier | peripheral 77.9k / working 17.9k / **core 4.7k** | `tier='core'` é sinal curado utilizável no brief (compor com salience) |
| memory_type | vazio em 100.542 (20 'decision') | coluna efetivamente morta — ignorar |
| access_count | 85.850 zero / 14.712 >0 (máx 2.224) | — |
| **High-pain órfãos** | pain ≥ 0.7: 2.548 chunks, **1.871 nunca acessados (73%)** | valida empiricamente a tese do Forge (item 5 do plano Cipher) — conhecimento crítico dormindo |

### T1 — Route handler ✅
- [x] `GET /api/brief` no server HTTP (mesmo router de `/api/health`)
- [x] Parse + validação de params (400 nos inválidos), defaults (n=10, format=json)

### T2 — Query builder + ranking ✅
- [x] Função `buildBriefQuery(scope, agent?, since?)` → SQL com filtro de scope (§2.1) + salience ORDER BY + LIMIT
- [x] Cálculo de salience reutiliza o módulo existente (mesma função do health endpoint — não duplicar fórmula)
- [x] `one_liner` extractor (§2.4)

### T3 — Read tracking ✅
- [x] Migration: tabela `brief_log` + índice (§2.3) — única mudança de schema do F1
- [x] INSERT em `brief_log` por item servido; `access_count` de chunks **intocado**
- [x] Query de follow-up rate documentada (brief_log ⋈ chunks.last_accessed_at ≤ 24h)

### T4 — Renderer `format=text` ✅
- [x] Template de linha + header; truncation por budget (§2.5)

### T5 — Testes ✅ (20/20 pass; bench prod p50 37–80ms por scope)
- [x] Unit: scope mapping (agente, projeto, global), since, n cap, one_liner edge cases (chunk vazio, só frontmatter)
- [x] Ranking: chunk high-pain recente > chunk antigo low-pain no mesmo scope
- [x] Budget: text nunca excede ~1.200 tokens estimados
- [x] Latência: bench p50 < 100ms com DB prod-size (**100k+ chunks**) — atenção: salience é computada por row; se full-scan estourar, pré-filtrar por prefixo de scope (índice em `source_file` se necessário) antes do ranking
- [x] Read tracking: servir brief insere em brief_log; `access_count` permanece inalterado (assert explícito no teste)

### T6 — Docs ✅
- [x] `docs/PRIMITIVES.md`: seção "Composing: brief" (não é 4º primitivo — é composição salience+temporal empacotada)
- [x] `docs/openapi.yaml`: path + schemas
- [x] `docs/ARCHITECTURE.md`: 1 linha no diagrama da API

### T7 — Deploy + gate Fase 1 ✅ EXECUTADO 2026-06-04
- [x] Deploy na VPS — PR #1 (review Forge ✅) merged fac47c74; pull + tsc + restart nox-mem-api
- [x] Gate manual Toto: **condição B** — aprovado condicionado a v1.1 polish (3 quirks: age_days por updated_at tocado por cron, duplicatas, HTML tags no one_liner)
- [x] v1.1 polish: PR #2 merged e4c794c0 + deployed — 23/23 testes; output pós-fix: idades reais 40–46d, dupes eliminados (slots ganharam itens relevantes), HTML stripped
- [x] `/api/health` pós-deploy (2×): 100.562 chunks / vec 100.555 / salience active — intacto
- [x] Latência prod real: ~58ms end-to-end

## 6. Estimativa

| Task | LOC ~ | Risco |
|---|---|---|
| T0 | 0 (queries) | baixo — read-only |
| T1+T2 | ~150 | médio — scope mapping depende de T0 |
| T3 | ~40 | baixo — wrapper existe |
| T4 | ~50 | baixo |
| T5 | ~200 | baixo |
| T6 | docs | — |

Total ~440 LOC + testes. 1 PR (ou 2: T0 findings + implementação).

## 7. Riscos

| Risco | Mitigação |
|---|---|
| ~~file_path não separa projetos limpo~~ | ✅ RESOLVIDO T0 — namespaces de `source_file` separam limpo (§2.1) |
| ORDER BY salience full-scan lento em **100k** | pré-filtro por prefixo de scope reduz o set antes do ranking; cache 10min por scope como fallback |
| ~~Docs divergem sobre salience mode~~ | ✅ RESOLVIDO T0 — mode `active` em prod; refresh de docs (KG counts também stale) vai no PR do F1 |
| Brief vazio pra scopes novos | 200 + items:[] documentado; hook fail-open ignora |
