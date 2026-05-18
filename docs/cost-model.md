# nox-mem — Cost Model

> Decomposição de custo por operação, por perfil de uso e por provedor.
> Referência para decisões de pricing do Nox-Supermem e para controle interno de gastos.
>
> **Status:** 2026-05-18 (Wave H — pré-GTM)
> **Cross-links:** `docs/gtm/PRICING-STRATEGY.md` · `docs/COMPETITIVE-POSITIONING.md` · `docs/gtm/ROI-CALCULATOR.md`
>
> **Disclaimer:** preços de provedores são públicos e verificáveis (Gemini AI Studio pricing, OpenAI pricing page, Anthropic pricing page). Projeções de volume são **ilustrativas** — labels explícitos indicam onde.

---

## Índice

1. [Premissas e fontes](#1-premissas-e-fontes)
2. [Embedding cost (Gemini gemini-embedding-001)](#2-embedding-cost)
3. [LLM cost (gemini-2.5-flash-lite default)](#3-llm-cost)
4. [KG extraction cost](#4-kg-extraction-cost)
5. [Storage cost (SQLite local/VPS)](#5-storage-cost)
6. [CPU cost (scrypt KDF — export/import)](#6-cpu-cost)
7. [Price table — todos provedores suportados](#7-price-table)
8. [Cost cap mechanism (NOX_PROVIDER_DAILY_USD_CAP)](#8-cost-cap-mechanism)
9. [Perfis de uso — projeções ilustrativas](#9-perfis-de-uso)
10. [Cost comparison vs competidores](#10-cost-comparison-vs-competidores)
11. [Sensibilidade a volume e otimizações](#11-sensibilidade-e-otimizacoes)
12. [Perguntas abertas para Toto decidir](#12-perguntas-abertas)

---

## 1. Premissas e fontes

### Preços de referência (público, 2026-05)

| Provider | Modelo | Input (USD/MTok) | Output (USD/MTok) | Fonte |
|---|---|---|---|---|
| Google | gemini-embedding-001 | $0.10 | N/A | ai.google.dev/pricing |
| Google | gemini-2.5-flash-lite | $0.10 | $0.40 | ai.google.dev/pricing |
| Google | gemini-2.5-flash | $0.30 | $2.50 | ai.google.dev/pricing |
| Google | gemini-2.5-pro | $1.25 | $10.00 | ai.google.dev/pricing |
| OpenAI | gpt-4o-mini | $0.15 | $0.60 | platform.openai.com/pricing |
| OpenAI | gpt-4o | $2.50 | $10.00 | platform.openai.com/pricing |
| Anthropic | claude-3-5-haiku | $0.80 | $4.00 | anthropic.com/pricing |
| Anthropic | claude-3-5-sonnet | $3.00 | $15.00 | anthropic.com/pricing |

Preços retirados de `staged-A3/edits/src/lib/cost-cap.ts` (price table em código — fonte: `PRICE_TABLE_USD_PER_1M_INPUT` / `PRICE_TABLE_USD_PER_1M_OUTPUT`). Reconciliar vs invoice mensalmente, conforme comentário inline no código.

### Unidades de base

- **1 chunk = ~500 tokens** (average observado no corpus de 62.9k chunks)
- **1 embedding call = 1 chunk** (gemini-embedding-001, 3072d)
- **1 query = ~500 tokens input + ~100 tokens output** (estimativa conservadora para hybrid search + LLM answer)
- **KG extraction = ~1.5k tokens input + ~300 tokens output por chunk** (estimativa para Gemini 2.5 Flash via kg-extract)
- **Scrypt N=2^17**: ~0.5–1.0s em laptop moderno; ~1.5–3.0s em VPS shared core

---

## 2. Embedding Cost

**Modelo padrão:** `gemini-embedding-001` via `GEMINI_API_KEY`
**Preço:** $0.10/MTok input (embeddings só têm input; output é o vetor, não tokens de texto)

### Cálculo por unidade

```
1 chunk = 500 tokens
1 chunk embedding = 500 / 1.000.000 × $0.10 = $0.00005

1k chunks = $0.05
10k chunks = $0.50
100k chunks = $5.00
1M chunks = $50.00
```

### Notas operacionais

- Embedding é custo **one-time por chunk**: ingerido uma vez, vetorizado uma vez, reutilizado em todas as queries
- Re-ingest por mudança de schema **não re-embeds** chunks inalterados (chunkhash + dirty-check no reindex)
- `nox-mem vectorize` roda batch; vectorização incremental roda inline no ingest (comportamento padrão)
- Coverage atual: 99.97% dos 62.9k+ chunks têm vetor — gap de 0.03% são chunks recentes pré-vectorize batch

### Impacto do provider swap (A3)

Voyage AI embeddings têm preço comparável ao Gemini embedding-001 — ambos na faixa de $0.10/MTok. OpenAI text-embedding-3-large é ~$0.13/MTok (1.3× mais caro). A escolha de embedding provider tem impacto menor no custo total do que a escolha de LLM.

---

## 3. LLM Cost

**Modelo padrão:** `gemini-2.5-flash-lite` (CLAUDE.md regra #3)
**Preço:** $0.10/MTok input, $0.40/MTok output

### Cálculo por query

```
1 query: 500 tokens input + 100 tokens output
= (500/1M × $0.10) + (100/1M × $0.40)
= $0.00005 + $0.00004
= $0.000090 por query
```

Arredondando para $0.0001/query (margem de segurança), a matemática de volume fica:

| Volume diário | Custo diário | Custo mensal | Custo anual |
|---|---|---|---|
| 10 queries | $0.001 | $0.03 | $0.36 |
| 100 queries | $0.009 | $0.27 | $3.29 |
| 500 queries | $0.045 | $1.35 | $16.44 |
| 1.000 queries | $0.090 | $2.70 | $32.85 |
| 5.000 queries | $0.450 | $13.50 | $164.25 |
| 10.000 queries | $0.900 | $27.00 | $328.50 |
| 50.000 queries | $4.50 | $135.00 | $1.642,50 |

### Context window e SPO injection

O SPO injection (E03b, ativo em prod) prepende um bloco de triplas KG ao resultado (~7 triplas, ~91 tokens extras). Isso aumenta o custo de input em ~18% por query de KG. Para queries sem KG match, o overhead é zero.

Custo efetivo com SPO: ~$0.00011/query (vs $0.000090 sem SPO) — diferença irrelevante em escala pessoal; relevante apenas em enterprise (>50k queries/dia).

### Comparação com gemini-2.5-flash (upgrade)

Se a rule #3 for relaxada temporariamente (ex: para KG extraction em volume baixo):

```
gemini-2.5-flash: $0.30 input + $2.50 output
1 query: (500/1M × $0.30) + (100/1M × $2.50)
= $0.00015 + $0.00025 = $0.00040/query
```

Flash full é **4.4× mais caro** que flash-lite por query. Justificável apenas para operações que exigem maior qualidade de raciocínio (crystallize, kg-extract em corpus não-estruturado).

---

## 4. KG Extraction Cost

### Path sem regex-first (L4 não ativo)

**Modelo:** `gemini-2.5-flash` (qualidade necessária para extração estruturada)
**Input:** ~1.500 tokens por chunk (chunk + instrução de extração + schema)
**Output:** ~300 tokens por chunk (JSON com entidades + relações)

```
1 chunk KG extraction (sem L4):
= (1500/1M × $0.30) + (300/1M × $2.50)
= $0.00045 + $0.00075
= $0.00120 por chunk
```

### Path com regex-first (L4 ativo — Wave 1 E-lite-2)

L4 regex-first captura ~80% dos chunks estruturados (markdown com frontmatter, código, entities) sem chamar o LLM. Apenas ~20% do corpus cai no fallback LLM.

```
100 chunks com L4 ativo:
= 80 chunks × $0 (regex) + 20 chunks × $0.00120 (LLM)
= $0.024 por 100 chunks (vs $0.12 sem L4)
= 80% de redução de custo de extração
```

### Impacto em indexação de corpus completo

| Corpus | Sem L4 | Com L4 (80% regex) | Economia |
|---|---|---|---|
| 10k chunks | $12.00 | $2.40 | $9.60 |
| 62.9k chunks (prod atual) | $75.48 | $15.10 | $60.38 |
| 100k chunks | $120.00 | $24.00 | $96.00 |
| 1M chunks | $1.200,00 | $240.00 | $960.00 |

KG extraction é **custo de indexação** (one-time ou incremental nightly para chunks novos). O nightly KG build processa apenas chunks novos desde o último run — não reprocessa o corpus inteiro. Para um corpus estável de 62.9k chunks, o custo diário incremental é proporcional ao volume de ingest diário (não ao corpus total).

### KG coverage atual e custo recorrente

KG coverage: ~5.5% do corpus (15.6k entities, 21.5k relations extraídos de 62.9k chunks).
Crescimento diário médio: ~500–1.000 chunks novos/dia (estimativa baseada em corpus growth history).

```
Custo diário KG incremental (1k chunks, com L4):
= 1.000 × 0.20 × $0.00120
= $0.24/dia = $7.20/mês
```

---

## 5. Storage Cost

### SQLite local (self-hosted)

SQLite não tem custo de storage per se. O custo é o VPS ou disco local onde o arquivo reside.

| Corpus | DB Size (estimativa) | Notes |
|---|---|---|
| 10k chunks | ~20MB | chunks + FTS5 shadow tables + vec index |
| 62.9k chunks (prod) | ~200–300MB | observado em produção |
| 100k chunks | ~400MB | |
| 500k chunks | ~2GB | |
| 1M chunks | ~4GB | ponto de inflexão para VACUUM ANALYZE periódico |

### VPS Hostinger Brasil (referência de custo)

Tiers VPS Hostinger (valores aproximados, BRL):
- KVM 1 (1 vCPU, 4GB RAM, 50GB SSD): ~R$ 30/mês (~$6/mês)
- KVM 2 (2 vCPU, 8GB RAM, 100GB SSD): ~R$ 55/mês (~$11/mês)

Para corpus de 100k chunks (~400MB), KVM 1 é mais que suficiente para storage. O gargalo é RAM para operações de vectorize em batch, não disco.

### Custo marginal de storage

Para efeito de pricing de hosted tiers: storage é negligível até ~1M chunks (~4GB). Em um VPS de 50GB, você hospeda 12+ usuários power-user (100k chunks/usuário) antes de chegar no limite de disco.

---

## 6. CPU Cost (scrypt KDF — export/import A2)

### Parâmetros do A2 encryption (D41 #2, locked)

```
Algorithm: AES-256-GCM
KDF: scrypt N=2^17 (131072), r=8, p=1
Key derivation time: ~0.5–1.0s laptop / ~1.5–3.0s VPS shared core
Salt: 16 bytes random per archive
Nonce: 12 bytes random per file
```

**Fonte:** `staged-A2/edits/src/lib/archive/encryption.ts`, constantes `SCRYPT_N=131072`, `SCRYPT_R=8`, `SCRYPT_P=1`.

### Impacto em custo real

- Uma operação de export/import = 1 scrypt derivation = ~2s em VPS
- Custo de CPU em VPS shared: negligível (centavos/milhão de operações ao preço de eletricidade AWS)
- Relevante apenas se você rodar milhares de exports/dia (não é o caso de uso esperado)
- O custo real do export A2 é o Gemini embedding round-trip para validate round-trip nDCG ±0.001, não o scrypt

---

## 7. Price Table — Todos Provedores Suportados

Extraída diretamente do código (`staged-A3/edits/src/lib/cost-cap.ts`):

### Input pricing (USD por 1M tokens)

| Modelo | Input USD/MTok | Relativo ao flash-lite |
|---|---|---|
| gemini-2.5-flash-lite | $0.10 | baseline (1.0×) |
| gemini-2.5-flash | $0.30 | 3.0× |
| gemini-2.5-pro | $1.25 | 12.5× |
| gpt-4o-mini | $0.15 | 1.5× |
| gpt-4o | $2.50 | 25.0× |
| claude-3-5-haiku | $0.80 | 8.0× |
| claude-3-5-sonnet | $3.00 | 30.0× |

### Output pricing (USD por 1M tokens)

| Modelo | Output USD/MTok | Relativo ao flash-lite |
|---|---|---|
| gemini-2.5-flash-lite | $0.40 | baseline (1.0×) |
| gemini-2.5-flash | $2.50 | 6.25× |
| gemini-2.5-pro | $10.00 | 25.0× |
| gpt-4o-mini | $0.60 | 1.5× |
| gpt-4o | $10.00 | 25.0× |
| claude-3-5-haiku | $4.00 | 10.0× |
| claude-3-5-sonnet | $15.00 | 37.5× |

### Custo por query (500 input + 100 output tokens)

| Modelo | Custo/query | Custo 1k queries | Custo 100k queries/mês |
|---|---|---|---|
| gemini-2.5-flash-lite | $0.000090 | $0.09 | $9.00 |
| gemini-2.5-flash | $0.000400 | $0.40 | $40.00 |
| gemini-2.5-pro | $0.001625 | $1.63 | $162.50 |
| gpt-4o-mini | $0.000135 | $0.14 | $13.50 |
| gpt-4o | $0.002250 | $2.25 | $225.00 |
| claude-3-5-haiku | $0.000800 | $0.80 | $80.00 |
| claude-3-5-sonnet | $0.003000 | $3.00 | $300.00 |

**Conclusão:** flash-lite é 1.5× mais barato que gpt-4o-mini, 8.9× mais barato que haiku, e 33× mais barato que sonnet para workload de queries. Para uso pessoal (100–500 queries/dia), a diferença entre provedores é sub-$10/mês. Para enterprise (50k+ queries/dia), a diferença chega a centenas de dólares/mês.

---

## 8. Cost Cap Mechanism

### Implementação (A3 — staged)

**Env var:** `NOX_PROVIDER_DAILY_USD_CAP` (default: `$50.00`)
**Bypass:** `NOX_PROVIDER_DAILY_USD_CAP_BYPASS=1` (audit-logged, nunca silencioso)
**Reset:** UTC midnight (janela rolling de 24h)
**Error type:** `CostCapExceededError` — sem conteúdo de prompt no erro (privacy-safe)

**Fonte:** `staged-A3/edits/src/lib/cost-cap.ts`, `CostCappedProvider` class.

```typescript
// Behavior quando cap é excedido:
throw new CostCapExceededError(capUsd, spentUsd, resetAtUtcISOString);
// Error msg: "CostCapExceededError: daily spend cap of $50.0000 USD exceeded
//             (accumulated: $50.0023 USD). Cap resets at 2026-05-19T00:00:00Z UTC.
//             Set NOX_PROVIDER_DAILY_USD_CAP_BYPASS=1 to override (logged to ops_audit)."
```

### Recomendações de cap por perfil

| Perfil | Cap diário recomendado | Justificativa |
|---|---|---|
| Usuário pessoal (100k chunks, 500 queries/dia) | $2.00–$5.00 | Custo real ~$0.13/dia; cap conservador protege contra bug de loop |
| Power user (10k chunks ingest/dia + 5k queries) | $5.00–$15.00 | Custo real ~$4/dia; margem para spikes |
| Team (100k ingest/dia, 50k queries) | $50.00 (default) | Custo real ~$40/dia; default adequado |
| Enterprise | $200.00–$500.00 | Custo real ~$400/dia; cap por SLA |

O cap padrão de $50/dia foi escolhido para ser conservador o suficiente para detectar loops acidentais (ex: bug que chama vectorize em loop) sem bloquear uso legítimo de power users.

---

## 9. Perfis de Uso — Projeções Ilustrativas

> Labels "ilustrativas" — não são compromissos. São inputs para decisões de pricing.

### Perfil 1 — Usuário Pessoal

**Cenário:** Desenvolvedor individual, usa nox-mem para capturar notas técnicas, decisões de projetos, feedback de agentes.

| Operação | Volume/dia | Custo/dia |
|---|---|---|
| Ingest (embedding) | 100 chunks novos | $0.005 |
| Search (LLM query) | 50 queries | $0.005 |
| KG extraction (incremental, com L4) | 20 chunks | $0.005 |
| **Total diário** | | **$0.015** |
| **Total mensal** | | **~$0.45** |
| **Total anual** | | **~$5.40** |

### Perfil 2 — Power User

**Cenário:** Pesquisador ou engenheiro sênior, ingere transcrições de reuniões, documentos técnicos, código. Usa search extensivamente.

| Operação | Volume/dia | Custo/dia |
|---|---|---|
| Ingest (embedding) | 1.000 chunks novos | $0.05 |
| Search (LLM query) | 500 queries | $0.045 |
| KG extraction (incremental, com L4) | 200 chunks | $0.048 |
| **Total diário** | | **$0.143** |
| **Total mensal** | | **~$4.30** |
| **Total anual** | | **~$52.00** |

### Perfil 3 — Team (5 usuários)

**Cenário:** Time de produto compartilhando memória de projeto. Ingest de reuniões, documentos, decisões técnicas.

| Operação | Volume/dia | Custo/dia |
|---|---|---|
| Ingest (embedding) | 5.000 chunks novos | $0.25 |
| Search (LLM query) | 2.500 queries | $0.225 |
| KG extraction (incremental, com L4) | 1.000 chunks | $0.24 |
| **Total diário** | | **$0.715** |
| **Total mensal** | | **~$21.45** |
| **Total anual** | | **~$257.40** |

### Perfil 4 — Enterprise (50 usuários + automações)

**Cenário:** Organização com múltiplos agentes e pipelines de ingest automatizados (CI/CD, transcrições, CRM).

| Operação | Volume/dia | Custo/dia |
|---|---|---|
| Ingest (embedding) | 50.000 chunks novos | $2.50 |
| Search (LLM query) | 25.000 queries | $2.25 |
| KG extraction (incremental, com L4) | 10.000 chunks | $2.40 |
| **Total diário** | | **$7.15** |
| **Total mensal** | | **~$214.50** |
| **Total anual** | | **~$2.574** |

### Resumo consolidado (ilustrativo)

| Perfil | Custo/mês (provedor) | Custo/mês (VPS) | Total/mês |
|---|---|---|---|
| Pessoal | ~$0.45 | $6 (VPS KVM 1) | **~$6.45** |
| Power User | ~$4.30 | $6 (VPS KVM 1) | **~$10.30** |
| Team (5 users) | ~$21.45 | $11 (VPS KVM 2) | **~$32.45** |
| Enterprise (50 users) | ~$214.50 | $30 (VPS KVM 4) | **~$244.50** |

---

## 10. Cost Comparison vs Competidores

### Estrutura de custo — nox-mem vs memanto vs agentmemory

| Dimensão | memanto (SaaS) | agentmemory (iii-engine) | nox-mem (self-hosted) |
|---|---|---|---|
| Modelo de cobrança | Subscription SaaS | Subscription ou usage (iii-engine) | Pay-as-you-go ao provedor direto |
| Controle de custo | Zero — preço deles | Parcial — via pricing tier | Total — cap + provider swap |
| Transparência | Opaco (backend fechado) | Parcial | Total — price table em código |
| Custo de storage | Incluído no SaaS | Incluído no iii-engine | $6/mês VPS |
| Custo de embedding | Incluído (Moorcheh gerencia) | Incluído (iii-managed) | $0.10/MTok direto ao Google |
| Custo de LLM query | Incluído | Incluído | $0.10/MTok input direto |
| Portabilidade de dados | ❌ lock-in | ❌ iii-engine lock-in | ✅ SQLite file, export A2 |
| Vendor risk | Alto (startup SaaS) | Alto (iii-engine proprietary) | Baixo (Google/Anthropic/OpenAI direct) |

### Estimativa de preço memanto (pesquisa pública 2026-05)

Memanto (Moorcheh AI) não tem pricing público no site em 2026-05 — modelo atual parece ser early access / waitlist. Estimativas de mercado para produtos comparáveis (SaaS memory layer):

- Tier pessoal: $10–$20/mês (comparável ao Notion AI, ChatGPT Plus)
- Tier pro: $30–$50/mês
- Enterprise: custom ($500–$2.000/mês)

**Nota:** sem pricing público confirmado, essas estimativas são referências de mercado, não fatos sobre memanto.

### Estimativa de preço agentmemory (iii-engine)

agentmemory é MIT open source (wrapper). O custo real vem do iii-engine runtime — não público em 2026-05. O modelo de lock-in sugere que o custo de saída (migração) será alto quando/se eles introduzirem pricing no iii-engine.

### Vantagem estrutural nox-mem

Para o power user ($10/mês de custo real) vs memanto ($20–$30/mês hipotético):
- nox-mem é 2–3× mais barato no cenário self-hosted
- O custo hosted (Nox-Supermem) pode ser mais caro que self-hosted mas comparável a memanto

A proposição de valor não é ser o mais barato — é ser o mais transparente e autonômo. O usuário que quer pagar menos pode self-host a $6–$10/mês. O usuário que quer conveniência pode pagar por hosted.

---

## 11. Sensibilidade e Otimizações

### Alavancas de redução de custo (em ordem de impacto)

1. **L4 regex-first KG extraction**: 80% redução em custo de KG. Ativo desde Wave 1 E-lite-2.
2. **gemini-2.5-flash-lite vs flash full**: 3× redução de custo de LLM. Default já correto.
3. **Deduplicação de embedding**: chunkhash evita re-embed de chunks inalterados. Ativo.
4. **NOX_PROVIDER_DAILY_USD_CAP**: cap diário previne runaway cost em bugs de loop. Default $50.
5. **FTS5 fallback sem LLM**: queries simples (exatas, identificadores) usam FTS5 BM25 puro sem Gemini call. Zero custo LLM.
6. **Cache de embedding**: vetores persistidos no SQLite — um chunk embeddado uma vez nunca é re-embeddado (exceto se o texto mudar).
7. **Batch vectorize vs inline**: vectorize em batch é mais eficiente para corpus grandes (reduz overhead de API round-trips).

### Tipping points de custo

| Evento | Impacto | Mitigation |
|---|---|---|
| Bug de loop em ingest (ex: watcher reprocessa o mesmo arquivo) | Embedding cost × N (pode ser $0.05/loop × 1000 = $50) | NOX_PROVIDER_DAILY_USD_CAP=$2 para dev |
| crystallize rodando sobre corpus completo ao invés de incremento | LLM cost × 62.9k chunks = ~$5 | --dry-run antes de crystallize |
| kg-extract sem L4 ativo em corpus completo | $75 one-time | L4 está ativo; verificar antes de rebuild |
| Provider acidental (ex: flash full no lugar de flash-lite) | 3× custo LLM | NOX_PROVIDER env var explícita; cap diário |

---

## 12. Perguntas Abertas

Para Toto decidir (não são decisões deste documento):

| ID | Pergunta | Contexto |
|---|---|---|
| C1 | Cap padrão de $50/dia é adequado para todos os tiers de hosted, ou cada tier deve ter seu próprio cap? | Default no código; pode ser por-user em A3.2 |
| C2 | O custo de KG extraction deve ser repassado ao usuário hosted ou absorvido na margem do tier? | KG é feature diferenciadora; absorver pode ser vantagem competitiva |
| C3 | Qual a estratégia de provider para usuários hosted: Gemini-only ou multi-provider desde o início? | A3 specced; implementação Q3 2026 |
| C4 | Existe alguma restrição de LGPD ou regulatória em repassar dados de usuários para Google (Gemini) no contexto de hosted Nox-Supermem? | Relevante para compliance BR |
| C5 | O custo de export (scrypt KDF + Gemini embedding validate) deve ser limitado por plano? | A2 A3 ainda em staging |

---

*Documento gerado 2026-05-18 (Wave H). Update trigger: mudança em preços de provedores, novo perfil de uso identificado, ou gate A3 implementado.*

*Cross-links: `docs/gtm/PRICING-STRATEGY.md` · `docs/gtm/ROI-CALCULATOR.md` · `docs/COMPETITIVE-POSITIONING.md`*
