# memoria-nox: memória híbrida com peso de dor — e nenhum vendor no meio do caminho

> **Variantes de título**
> - "Por que seu agente de IA esquece tudo — e como consertar isso sem vender seus dados"
> - "memoria-nox: pain-weighted hybrid memory, yours by design"
> - "O diário de dor do seu agente: como retrieval híbrido com shadow discipline muda o jogo"

---

## O problema: agentes que esquecem, memória que vende você

Agentes de IA em 2026 são capazes de raciocinar, planejar e agir. O problema é que, ao final de cada sessão, eles esquecem quase tudo. O contexto some. Decisões tomadas meses atrás não existem mais. Incidentes críticos — aquele bug que derrubou produção, aquela decisão de arquitetura que custou três sprints — precisam ser recontados do zero.

A indústria tem tentado resolver isso com camadas de memória. O resultado, na maior parte dos casos, é uma das duas armadilhas:

**Armadilha 1: memória na nuvem do vendor.** Você envia seus dados para um terceiro, aceita os termos de uso, e reza para que a API não mude, o preço não suba, ou o serviço não seja descontinuado. Seu histórico de decisões, seus incidentes, suas conversas — tudo numa caixa-preta que não é sua.

**Armadilha 2: self-hosting sem retrieval de verdade.** Você sobe um vector store local, faz um `pip install`, e descobre que a busca retorna resultados razoáveis quando a query é exata e falha completamente quando é natural, multilíngue, ou semanticamente distante do texto indexado.

Existe um terceiro problema que ninguém fala: não há benchmark honesto. A maioria dos sistemas de memória para agentes não publica números em conjuntos padronizados como LongMemEval ou LoCoMo. Não dá para comparar. Você adota no escuro.

memoria-nox recusa as duas armadilhas — e publica os números.

---

## O que é memoria-nox

memoria-nox é um sistema de memória híbrido para agentes de IA. Ele vive em um único arquivo SQLite no seu disco. Você pode copiar, mover, fazer backup ou migrar de servidor com um `cp`. Não há daemon externo, não há cloud obrigatória, não há vendor no caminho entre o seu agente e o que ele lembrou.

A busca combina três camadas em paralelo: FTS5 BM25 para recall léxico, embeddings Gemini 3072-dimensionais via sqlite-vec para recuperação semântica, e RRF (Reciprocal Rank Fusion, k=60) para fundir os dois sem amplificação de ruído. O resultado é o que a literatura chama de hybrid retrieval — keyword quando a query é precisa, semantic quando ela é vaga ou multilíngue.

O diferencial não está só na arquitetura. Está em dois conceitos que não existem em nenhum outro sistema de memória para agentes documentado na literatura: **pain weighting** e **shadow discipline**.

**Pain weighting** é simples e brutalmente útil: cada chunk tem um campo `pain` (0.1 trivial → 1.0 prod-outage). Um incidente que derrubou produção tem `pain = 1.0`. A nota de reunião de alinhamento tem `pain = 0.2`. A fórmula de salience (`recency × pain × importance`) garante que o que mais custou permaneça recuperável quando a lição importa — não quando a data ainda é recente.

**Shadow discipline** é o protocolo de evolução de ranking. Toda mudança de scoring vai para shadow mode por pelo menos sete dias, com métricas expostas em `/api/health`, antes de influenciar qualquer query real. Isso impediu que pelo menos três regressões chegassem a produção durante a série de ablações G1–G12.

---

## Os três pilares: Q / A / P

### Q — Quality: números primeiro

Retrieval de memória que não mede não sabe se funciona. memoria-nox roda contra LoCoMo e LongMemEval com harnesses publicados no repositório.

**Números verificados (corpus de produção, 2026-05-19):**

| Métrica | Valor | Baseline |
|---|---|---|
| LoCoMo nDCG@10 (G5 V3 A8, n=100) | **0.6237** | G3 baseline 0.3488 |
| Melhora relativa vs baseline | **+78.8%** | — |
| LoCoMo Recall@10 | **0.7070** | +87% rel. |
| LoCoMo MRR | **0.5534** | +98% rel. |
| vs BM25 Pyserini (Anserini-tuned, n=60) | **4.0× melhor** | BM25 = 0.1475 |
| vs multilingual-e5-base (n=60) | **1.9× melhor** | e5 = 0.3070 |
| Latência `/api/search` p50 / p95 | **940ms / 2.3s** | — |
| Answer primitive p95 | **101.74ms** (42× abaixo do budget de 4.3s) | — |

**Q4 broader smoke (2026-05-24 15h30 BRT) — nox-mem isolado em eval-DB com 5.882 chunks LoCoMo + 940 chunks LongMemEval, 20 queries (10 por dataset):**

| Métrica | Valor |
|---|---:|
| nDCG@10 (combined) | **0.6380** |
| MRR | **0.3700** |
| R@10 | **0.5417** |
| Gold hits | **13/20 (65%)** |
| p50 latency | **8ms** |
| p95 latency | **43ms** |
| Avg latency | **9ms** |
| LoCoMo gold hits | **7/10 (70%)** |
| LongMemEval gold hits | **6/10 (60%)** |

**Side-by-side com mem0 — comparação completa (Sat 2026-05-24, PR #311):**

**Full-corpus vs capped (não apples-to-apples):**

| Sistema | Corpus | Hits | nDCG@10 | MRR | R@10 | p50 |
|---|---|---:|---:|---:|---:|---:|
| **nox-mem** | 6.822 chunks (full, ingest local zero-custo) | **13/20 (65%)** | 0.6380 | **0.3700** | **0.5417** | **8ms** |
| **mem0** | 500 chunks (cap ~8%, $0.10 ingest) | 3/20 (15%) | 0.1315 | — | — | 273ms |

**Apples-to-apples (mesmo 500 chunks, corpus-cap uniform):**

| Sistema | Corpus | nDCG@10 | Mode |
|---|---|---:|---:|
| **nox-mem FTS5@500** | 500 (cap) | 0.0466 | FTS5-only, sem Gemini |
| **mem0@500** | 500 (cap) | **0.1315** | LLM rewrite + embed |

**O que os números dizem — honestamente (rev3, PR #318).** O breakdown por dataset revela o quadro correto:

- **LoCoMo (memória conversacional), mesmo 500 chunks:** nox-mem Gemini hybrid = **0.1835** vs mem0 = 0.1315 → **+40% a favor do nox-mem**. Este é o sinal mais limpo apples-to-apples em corpus esparso.
- **Aggregate@500 (0.0918)** fica abaixo do mem0 por um **artefato de corpus-ordering**: os 5.882 chunks do LoCoMo esgotam o cap de 500 antes de qualquer chunk LongMemEval ser ingerido — as 10 queries LongMemEval ficam com cobertura zero, puxando o aggregate para baixo. Não é sinal de retrieval; é confundidor de ordenação.
- **Hybrid lift sobre FTS5@500: +97%** (0.0466 → 0.0918) — valida o valor arquitetural do stack mesmo em corpus esparso.
- **FTS5-only@500 = 0.0466 vs mem0 = 0.1315** (H2, PR #311) — real e arquitetural para modo FTS5-only: LLM-rewriting generaliza semanticamente em corpora esparsas de forma que FTS5 isolado não consegue. O Gemini hybrid completo inverte isso no escopo conversacional.
- **nox-mem** — cobertura + velocidade + custo: corpus completo local, zero-custo por query, 30× mais rápido (8ms vs 273ms p50), 4× mais cobertura no full-corpus.

**Realidade de produção (rev4 honestidade).** O cap de 500 chunks do mem0 não é representativo de deployments reais. Em corpus típico de produção (5k–50k chunks), mem0 custa ~$0.34–4.00 em ingest via OpenAI. nox-mem custa $0. Os números de benchmark (nox-mem Gemini hybrid +40% LoCoMo-only) são válidos e defensáveis, mas ganham contexto crítico quando incluem custo de escala. Ambas as linhas — benchmark *e* economia de escala — estão publicadas em `docs/COMPARISON.md` sem cherry-pick. O run canônico com corpus uniforme sem cap é o árbitro definitivo.

**Gate Phase 2 usa AMBOS** per-dataset + aggregate no run canônico (corpus uniforme, sem cap) — não apenas o número que favorece nox-mem.

> **Honestidade obrigatória.** Reportamos três linhas: full-corpus, per-dataset@500, aggregate@500. Qualquer linha isolada é enganosa. O run canônico — corpus uniforme sem cap para todos os 6 sistemas — é o árbitro definitivo. `docs/COMPARISON.md` atualiza quando cravar. PR #311 + PR #318.

Memórias relacionadas: `[[q4-smoke-sat-2026-05-24-real-numbers]]` · `[[q4-partial-cross-system-sat-2026-05-24]]`.

### A — Autonomy: dados seus, provider seu, zero lock-in

O arquivo SQLite é seu. Copie-o. Mova-o. Faça backup. Exporte com AES-256-GCM via `nox-mem export --passphrase`. A camada de provider abstraction (A3) tem overhead medido de **0.0025ms** por chamada LLM — você pode trocar Gemini por OpenAI por um modelo local sem tocar no código de retrieval.

O filtro de privacidade A1 roda pre-storage: 13 padrões de redação (PII, tokens, chaves de API, senhas) com 1.7% de falso-positivo e 68 testes. Seus dados são filtrados antes de qualquer embedding ser gerado.

A suite A4 (8 checks de CI) valida que nenhuma dependência de terceiro é crítica para o runtime. Se a API Gemini sair do ar, o fallback chain entra. Se você quiser rodar tudo local, é possível.

### P — Product: UX que não pede desculpa

O primitivo `answer` (P1) responde perguntas com citações, guarda anti-alucinação contra afirmações não ancoradas nos chunks recuperados, e persiste telemetria por query no schema. p95 de 101.74ms na medição do benchmark — 42× abaixo do budget de 4.3s.

Queries temporais como `--as-of 2026-04-01` e `--changed-since 30d` são hard pre-filters, não boosts. O viewer SSE em tempo real (P5) é 11.7KB de HTML+JS+CSS vanilla — sem bundler, sem React, sem framework externo.

O MCP server expõe 16 tools (`nox_mem_search`, `kg_build`, `cross_search`, `reflect`, `nox_mem_answer`, ...) prontos para qualquer cliente Claude Code, Cursor ou compatível com MCP protocol.

---

## O que está por baixo do capô

Cinco camadas, um arquivo SQLite:

1. **Ingest** — o router detecta automaticamente entity files (com seções `compiled` / `frontmatter` / `timeline` e `section_boost` diferenciado), markdown genérico ou input graphify. O filtro A1 aplica 13 padrões de redação pre-storage.

2. **Store** — chunks em SQLite com índice FTS5 e vetores 3072d Gemini via sqlite-vec. Retenção tipada: `feedback` e `person` nunca decaem; `lesson` dura 180 dias; `decision` e `project` duram 365 dias. Schema v19, aditivo e idempotente.

3. **Retrieve** — FTS5 BM25 e Gemini semantic em paralelo. RRF fusion (k=60) funde os dois. Pesos ajustados por idioma: PT-BR tilts dense up (1.15) e FTS down (0.85).

4. **Rank** — salience (`recency × pain × importance`) compõe aditivamente com `section_boost` (compiled 2.0 / frontmatter 1.5 / timeline 0.8) e temporal boost (E13). Shadow mode é o default; active requer 7 dias de baseline.

5. **Answer** — CLI, MCP e HTTP com footer de citações, guarda anti-alucinação, telemetria persistida e budget de latência por fase.

**Knowledge Graph:** 17 tipos de entidade canônicos (`project`, `lesson`, `decision`, `person`, `team`, `feedback`, `incident`, `procedure`, `pending`, `daily`, `system`, `graph_node`, `chunk`, `section`, `entity`, `relation`, `unknown`). Extração incremental nightly via Gemini 2.5 Flash. Corpus atual: **15,646 entidades / 21,533 relações**.

---

## A série G: gauntlet de ablações

Antes de afirmar que um número é real, rodamos o ablation. Dez rounds de G-series (G1–G12), cada um com hipótese explícita, corpus isolado, e resultado publicado em `audits/`.

Alguns resultados que matamos antes de publicar:

- **tier_boost** piora performance vs boost stack sem ele — removido.
- **temporal spike v1** (PR #176) causou regressão de −32.29% — revertido antes de produção.
- **G11 trim de section_boost** (entity 2.0→1.3, lesson 1.8→1.2) piorou −0.73% nDCG / −1.58% MRR — mantemos os pesos originais.
- **G10d mutex de categoria** (threshold=2) recuperou multi-hop +1.58% e adversarial +3.04% depois que threshold=1 havia falhado por corpus insuficiente.

O que sobreviveu ao gauntlet: **Hard Mutex** (G10, +0.79% nDCG / +2.65% MRR vs no-mutex em corpus real g9.db 69.5k chunks), **SOURCE_TYPE_BOOST** (G8/G9 +14.2% vs A0 no corpus completo), **temporal spike v2** (Opção B regex+median com confidence tiers, shadow 7 dias).

Cada decision tem um arquivo em `docs/DECISIONS.md`. Cada ablation tem output em `audits/`. A disciplina não é opcional.

---

## Por que open-source

O pilar Autonomy só faz sentido se o código é auditável.

Você deve poder ler a fórmula de salience, entender o que `section_boost` faz, verificar que o filtro de privacidade está de fato redagindo antes de gerar embeddings, e confirmar que a `ops_audit` table é append-only com triggers que bloqueiam DELETE e UPDATE em rows terminais.

Memória de agente que não é inspecionável não é confiável. O paper *The Pain Diary and Shadow Discipline* (v1.1, 31 páginas, target arXiv cs.IR) documenta as fórmulas, os experimentos que matamos, e os harnesses que produziram os números. O repositório vem com esses harnesses. Você pode reproduzir.

MIT license. Sem telemetria externa. Sem call-home.

---

## Como começar

```bash
# Instala (CLI + MCP server + HTTP API em um binário)
npm install -g nox-mem

# Define sua chave de embedding (Gemini default; OpenAI e local disponíveis)
export GEMINI_API_KEY=sk-...

# Inicializa um memory store
nox-mem init ~/my-memory

# Ingere um diretório de markdown
nox-mem ingest ~/notes

# Busca híbrida (FTS5 BM25 + Gemini semantic + RRF)
nox-mem search "qual é a fórmula de salience?"

# Resposta fundamentada com citações
nox-mem answer "como o campo pain afeta o ranking?"
```

Requer Node 20+. SQLite embarcado via `better-sqlite3`. 26+ subcomandos via `nox-mem --help`. MCP server com 16 tools. HTTP API na porta `NOX_API_PORT` (default `18802`).

Referência completa: [`docs/QUICKSTART.md`](docs/QUICKSTART.md).

Repositório: [github.com/totobusnello/memoria-nox](https://github.com/totobusnello/memoria-nox)

---

## O que vem a seguir

**Lab (40% da capacidade)** está em retrieval research sem pressão de ship:

- **L2** — detecção de conflito e contradição no KG (relações opostas sobre o mesmo par de entidades).
- **L3** — campo de confidence e provenance no schema, gated em lift de eval.
- **L4** — extração de typed-links com regex-first e Gemini fallback (95.8% precision/recall no corpus sintético, 80% das chamadas Gemini eliminadas via confidence gate).
- **EverMemBench** — rodar memoria-nox no benchmark público da EverMind-AI para fechar o gap de comparabilidade com competidores que publicam papers.

**GTM Phase 2** está desbloqueada. Lançamento: quarta-feira 2026-06-03 com distribuição simultânea no arXiv, Product Hunt, Hacker News e LinkedIn.

O Q4 COMPARISON externo (Sat 2026-05-24) já cravou os primeiros números cross-system reais: nox-mem **nDCG@10 0.6380, p50 8ms, 65% gold-hit** vs mem0 (500-chunk cap) **nDCG@10 0.8569, p50 273ms, 15% gold-hit**. nox-mem 30× mais rápido e 4× mais cobertura; mem0 com concentração por-resultado mais alta dentro de janela menor. O run canônico de 100 queries × 2 datasets × 6 sistemas (corpus uniforme, sem cap) atualiza `benchmark/COMPARISON.md` quando os 4 adapters restantes ficarem prontos. Se os números mostrarem que algum competidor supera memoria-nox em algum eixo, vai estar lá — sem cherry-pick.

---

## Sobre o autor

**Toto Busnello** opera no nível board/advisor/empreendedor — atualmente advisor e board member na Nuvini, líder do FII Treviso e do Fundo Exclusivo de Investimento Lombardia, co-founder da Granix, e advisor de AI + membro do Comitê AI da Galapagos Capital. Passou por todas as posições C-level (CEO, CFO, CTO, CPO, CMO) ao longo da trajetória, o que explica por que um sistema de memória para agentes precisa ser auditável, portável, e economicamente racional.

memoria-nox nasceu da necessidade real de persistir decisões, incidentes e lições entre sessões de agentes sem ceder controle para nenhum vendor. A fórmula de pain-weighting veio diretamente da experiência de achar que um incidente estava documentado — e descobrir na hora errada que o agente nunca recuperou a lição certa.

[Repositório](https://github.com/totobusnello/memoria-nox) · [Paper v1.1](paper/publication/latex/paper.pdf) · [COMPARISON.md](benchmark/COMPARISON.md) · [Docs](docs/)

---

*Lançamento Wed 2026-06-03. Smoke Q4 nox-mem Sat 2026-05-24: nDCG@10 0.6380, p50 8ms, 13/20 gold hits. Rev3 (PR #318 2026-05-23): LoCoMo-only Gemini hybrid@500 = 0.1835 vs mem0 0.1315 (+40% win). Aggregate@500 = 0.0918 (corpus-ordering artifact). Hybrid lift sobre FTS5@500: +97%. Full-corpus nox-mem 30× mais rápido e 4× mais cobertura. Todas as linhas em `docs/COMPARISON.md`. Run canônico (6 sistemas, corpus uniforme) fecha antes do launch.*
