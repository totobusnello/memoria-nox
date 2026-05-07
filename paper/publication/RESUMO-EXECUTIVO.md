# The Pain Diary and Shadow Discipline: A Memory System That Learns from Its Own Incidents

---

Era 22:03 de 25 de abril. Um cron job de fim de dia rodou `nox-mem reindex` sem dry-run. Cento e oitenta e três entidades perderam section, retention e section_boost — anos de contexto estruturado, achatados em chunks genéricos em segundos. Nenhum log de erro. Nenhum alarme. O banco simplesmente... obedeceu.

Foi nesse dia que ficou claro: o problema de memória de agentes não é recuperação de informação. É disciplina.

---

## A tese em uma frase

> **Memória de agente não é problema de retrieval — é problema de disciplina operacional.**

Sistemas falham silenciosamente porque mudanças de ranking entram sem validação, severidade de incidente nunca vira sinal, e múltiplos agentes vivem em silos de contexto que nunca conversam. A solução não é embedding melhor — é arquitetura que codifica disciplina no schema.

---

## A noite que tudo começou

Quatro meses atrás, seis agentes de IA rodavam em produção — Atlas, Boris, Cipher, Forge, Lex e Nox — cada um com memória isolada, cada um reinventando contexto que outro já havia aprendido. As soluções existentes (LangChain Memory, MemGPT, Mem0) ou particionam por `user_id` ou são frameworks genéricos sem noção de custo operacional. Nenhuma pergunta: *esta lição custou um prod-outage ou foi só uma nota de rodapé?*

O sistema nasceu da observação de que lições caras precisam de tratamento diferente de documentação trivial. Não como política editorial — como sinal matemático no retrieval.

Então vieram os incidents. Em 25 de abril, o reindex sem dry-run apagou 183 entities. Em 1 de maio, um `sed -i` acidental corrompeu 1 GB de SQLite mais 8 backups — porque ninguém havia codificado a regra "nunca sed em binário" como proteção automática. Cada catástrofe operacional virou uma linha no schema. Cada cicatriz, uma feature.

Esse é o paper.

---

## O que é NOX-Supermem

### Em 5 camadas operacionais

#### 1. Camada de armazenamento

SQLite single-file (~1 GB), 61.257 chunks de markdown/PDF/código indexados. Cada chunk tem metadata typed: `source_file`, `retention_days`, `pain` (severidade de incidente, [0.1, 1.0]), `section` (compiled/frontmatter/timeline). Single-file significa backup atômico via `cp`, replicação trivial, zero ops overhead.

#### 2. Camada de retrieval

Hybrid 3-layer: FTS5 (lexical, BM25, instantâneo) + Gemini 3072d embeddings (semântico, contextual) + RRF k=60 (fusão recíproca). p95 < 1s em 61K chunks em CPU comum. Não é embedding melhor — é layering certo.

#### 3. Camada de conhecimento (KG)

Knowledge graph automatizado: 1.107 relações tipadas em 7 categorias closed-enum (`depends_on`, `derived_from`, `opposes`, `extends`, `replaces`, `mentions`, `unknown`). LLM (Gemini 2.5 Flash) extrai SPO triples; defensive normalize com 24 aliases PT-BR + EN eleva a taxa de cobertura do enum de 14% para 56% (taxa de emissão de valor tipado pelo LLM, não acurácia contra anotação humana). Permite blast-radius queries — sabe *o que* é afetado por uma mudança, não só que algo foi.

#### 4. Camada de governança

- Append-only audit log (`ops_audit`) — toda operação destrutiva snapshotada pre-op via VACUUM INTO atômico
- Shadow-mode obrigatório ≥7 dias antes de qualquer mudança em ranking
- Schema versionado v1→v12 com migrations idempotentes zero-downtime
- Health endpoint `/api/health` expõe distribuição de salience, vector coverage, schema version em tempo real

#### 5. Camada de interface

- **CLI**: 26+ subcomandos (search, ingest, kg-build, reflect, crystallize...)
- **HTTP API**: 12 endpoints em :18802 (`/api/{search,health,kg,kg/path,agents,cross-kg,reflect,procedures}`)
- **MCP server**: 16 tools para agentes Claude/MCP-compatible
- **Telemetria opt-in** (`search_telemetry`) com nDCG/MRR rastreados por query

---

### 10 características distintivas

**Operacionais (4)**

1. **Single-file SQLite** — backup atômico, replicação por `cp`, zero ops overhead
2. **Schema versionado** v1→v12 com migrations idempotentes zero-downtime
3. **Append-only audit log** (`ops_audit`) com snapshot pre-op atômico (VACUUM INTO)
4. **Shadow-mode arquitetural** ≥7d via cron + health endpoint — constraint, não best practice

**Retrieval e conhecimento (4)**

5. **Hybrid 3-layer** com RRF fusion — não single-vector store
6. **Closed-enum edge typing** (7 reasons, 24-alias defensive normalize) — não free-form RDF
7. **Pain-weighted salience** typed no schema — severity de incidente como sinal de retrieval
8. **Cross-agent shared corpus** (99,92% chunks shared) — não per-user partition

**Produção e reproducibilidade (2)**

9. **Production-tested 4 meses** com 6 agentes IA reais (Atlas, Boris, Cipher, Forge, Lex, Nox)
10. **Reproducibility-first** — eval harness com 60 golden queries, incident log público, schema versionado auditável

---

### 3 diferenciais inéditos na literatura

| # | Diferencial | Evidência empírica |
|---|---|---|
| **#1** | **Incident severity como retrieval signal** (`recency × pain × importance`) | Q55 case study Δ=+0.349 (regime semântico empatado); aggregate Δ=+0.0065 NOT_SIGNIFICANT — contribuição metodológica validada, não claim de performance |
| **#2** | **Shadow validation como constraint arquitetural** (≥7d via cron + health endpoint) | Phase 1.7b-b: 7d telemetria → 191 promoções / 16.608 revisões / 45.743 arquivamentos antes de ativar |
| **#3** | **Shared canonical multi-agent** (mesmo corpus, zero federação) | 61.207 / 61.257 chunks compartilhados = 99,92%; contrafactual MemGPT/Mem0 isolado = 0% sharing |

Cobertura na literatura: zero papers de memory systems até hoje codificam **#2 e #3** como constraints arquiteturais; **#1** é metodologia transferível a qualquer sistema persistente.

---

## 3 ideias que ninguém mais tinha

### Pain-Weighted Salience: o incidente importa mais que a data

A fórmula parece simples depois que alguém a escreve:

```
salience = recency × pain × importance
```

`pain ∈ [0.1, 1.0]` — de nota trivial a prod-outage. O que ninguém havia feito antes era tratar severidade como sinal de *retrieval*, não só de logging. GraphRAG, Mem0, A-MEM, HiRAG e Cognee modelam estrutura e recência. Nenhum pergunta: *isso custou quanto?*

O resultado: uma lição de prod-outage de seis meses atrás supera documentação atualizada ontem sobre assunto menor — como a memória humana funciona. O sistema roda 61.257 chunks com essa dimensão ativa, validada por 7 dias de telemetria real.

**Refinamento empírico (2026-05-04).** Ablações isolando pain de semântica mostram efeito direcional mas não significativo em aggregate. Testes diretos de calibração (4 distribuições: real, uniforme, bimodal, log-scale) refutaram a hipótese de que spread insuficiente era o fator limitante — distribuições artificiais todas ficam abaixo da distribuição real. O real root cause identificado: **BM25 recall ceiling** — 92% das queries (55/60) não encontram os chunks gold via busca lexical, independente de calibração de pain. O multiplicador pain não pode re-rankear o que nunca chegou ao pool de candidatos. Trabalho futuro: co-otimizar recall semântico com re-anotação de pain, posicionando pain como re-ranker pós-RRF. A contribuição metodológica — severity como campo tipado no schema com pipeline de anotação operacional — permanece válida independente do resultado empírico de retrieval.

### Shadow Discipline: nenhuma mudança de ranking entra sem sete dias de prova

`NOX_SALIENCE_MODE=shadow` é constraint arquitetural enforced via cron e `/api/health` — não uma boa prática documentada que alguém pode ignorar. Qualquer mudança que afeta ranking fica em shadow por mínimo 7 dias, comparada contra o comportamento anterior, antes de ativar.

A validação de salience (Fase 1.7b-b) rodou 7 dias de telemetria: 191 promoções, 16.608 revisões, 45.743 arquivamentos. Só então ativou. O contrafactual está documentado: o incident de 25 de abril — exatamente o tipo de regressão silenciosa — seria detectado em shadow antes de chegar a prod.

Nenhum paper de memória de agente até hoje codificou esse rigor operacional como constraint arquitetural. A maioria nem menciona o problema.

### Shared-Canonical Multi-Agent: um corpus, seis agentes, zero federação

MemGPT usa per-agent state. Mem0 usa partição por `user_id`. Os seis agentes deste sistema leem do **mesmo corpus canônico** — sem sincronização, sem merge, sem overhead de federação. Cross-agent intelligence por design, não por gambiarra.

Quando Forge aprende algo sobre uma decisão arquitetural, Atlas recupera esse contexto diretamente na próxima query relevante. Não porque alguém sincronizou — porque nunca houve separação.

---

## Os números que destroem a dúvida

### Hybrid não é otimização — é requisito

| Approach | nDCG@10 | Δ vs nox-mem |
|---|---|---|
| FTS5 vanilla (BM25) | 0.0000 | **−58,3 pp** |
| **BM25 Pyserini (Anserini-tuned, n=60)** | **0.1475** | **−43,6 pp** |
| **nox-mem hybrid (FTS + Gemini + RRF)** | **0.5831** | baseline |

*(n=60 queries R01c-v1.1 post-cure; 3-run mean ± std: Hybrid 0.5831 ± 0.0046 (Runs #30/#31/#32), FTS vanilla 0.0000 ± 0.0000 — gap relativo hybrid vs Pyserini: 4,0×. Pré-cura v1.0 numbers preservados em git tag v1.0.0.)*

Queries em linguagem natural completas resultam em nDCG **exatamente zero** em BM25-only sobre o corpus pós-cura — constraint estrutural do FTS5 AND-strict, não artefato de corpus. O BM25 Pyserini (Anserini-tuned, strong baseline de BEIR) eleva o patamar para 0.1475, e nox-mem hybrid ainda entrega **4,0× acima dele**. Hybrid é o piso, não o teto. Validação 3-run (runs #30/#31/#32, E13/E05b held off) com std=0.0046 (0.79% relativo), reproduzível por qualquer reviewer.

### Edge typing: taxa de cobertura do enum de 14% para 56% — ganho 4×

KG extraction com campo opcional e prompt ingênuo produzia apenas **14% de emissões tipadas** — **86% caíam em `unknown`**. Após defensive map no código (24 aliases PT-BR + EN) e prompt revisado (n=100): **56% das relações recebem um valor tipado** do schema closed-enum — ganho de **4× na taxa de cobertura** que viabiliza blast-radius queries. Saber *o que* foi afetado por uma mudança, não só que algo foi afetado. Nota: essa é uma taxa de cobertura auto-reportada pelo LLM (proporção de emissões não-`unknown`), não uma medida de acurácia contra conjunto anotado por humanos.

### nox-mem vs alternatives — paridade de features

A tabela usa 7 eixos arquiteturais e operacionais. O último — escala de corpus acima de 100K — é o único eixo sem cobertura atual. Benchmark de terceiros passou de ❌ para ✅ com LOCOMO (nDCG@10=0.281, n=100, concluído 2026-05-04) e BEIR TREC-COVID (e5-base nDCG@10=0.8335, BM25 FTS5=0.1007, n=50, concluído 2026-05-05). A inclusão do eixo de escala é intencional: comparação honesta exige marcar as lacunas, não só os pontos fortes.

| Sistema | KG nativo | Hybrid retrieval | Eval harness | Multi-agent | Shadow discipline | Escala ≥100K | Benchmark terceiros | **Score** |
|---|---|---|---|---|---|---|---|---|
| **nox-mem (este trabalho)** | ✅ closed-enum 7 reasons (24-entry map) | ✅ FTS5+Gemini+RRF | ✅ nDCG/MRR/Recall | ✅ shared canonical | ✅ enforced ≥7d | ❌ (61K atual) | ✅ LOCOMO 0.281 + BEIR e5 0.8335 | **6/7** |
| GraphRAG | ✅ + community detection | ⚠️ via KG queries | ❌ | ❌ | ❌ | ✅ (1M+ MS-MARCO) | ⚠️ paper-específico | 1.5/7 |
| MemGPT/Letta | ❌ | ⚠️ embedding-first | ❌ | ✅ per-agent | ❌ | ⚠️ varia | ❌ | 1.5/7 |
| Mem0 | ⚠️ optional v2 | ❌ vector-only | ⚠️ LOCOMO only | ⚠️ user_id partition | ❌ | ❌ | ✅ LOCOMO | 1.5/7 |
| A-MEM | ⚠️ Zettelkasten | ⚠️ semantic-first | ❌ | ❌ | ❌ | ❌ | ❌ | 1.0/7 |
| HiRAG | ✅ hierarchical | ✅ multi-level | ⚠️ task-specific | ❌ | ❌ | ⚠️ varia | ✅ multi-task | 2.5/7 |
| Cognee | ✅ ECL pipeline | ✅ hybrid | ⚠️ ad-hoc | ⚠️ optional | ❌ | ⚠️ ad-hoc | ⚠️ parcial | 3.0/7 |
| LangChain Memory | ❌ | ❌ key-value | ❌ | ⚠️ session_id | ❌ | ⚠️ varia | ❌ | 0.5/7 |

**Resumo honesto**: nox-mem cobre **6 de 7 eixos** — os cinco de disciplina operacional/arquitetura mais o eixo de benchmark de terceiros (LOCOMO + BEIR TREC-COVID concluídos). Não cobre o eixo de escala ≥100K (corpus atual: 61K). Essa lacuna está documentada como limitação no paper (§6.3) e como trabalho futuro (§6.5). O sistema mais próximo, Cognee, cobre 3/7. Média dos sete competidores: **1,6/7**. Os dois eixos com cobertura zero na literatura — pain weighting e shadow discipline — são as contribuições de maior novidade.

### Latência em produção real

| Métrica | nox-mem | Threshold típico de papers |
|---|---|---|
| p95 search | **< 1s** em 61K chunks | 1-3s reportado |
| Vector coverage | **99,97%** | 90-95% típico |
| Schema migrations sem downtime | **12 versões** | raro reportar |

Latência sub-segundo em 61.257 chunks com hybrid 3-layer (FTS5 → Gemini 3072d → RRF k=60) — não emulação local, produção real há 4 meses.

### Cross-agent storage — 99,92% sharing

De 61.257 chunks ativos no corpus, **61.207 são canonical shared** — acessíveis por todos os seis agentes sem particionamento, sincronização ou merge. Isso corresponde a **99,92% de sharing efetivo**. O contrafactual MemGPT/Mem0 com isolamento por agent/user_id resultaria em 0% de sharing — diferença arquitetural de **99,92 pp**, não decimal. O diferencial "Shared-Canonical Multi-Agent" agora tem evidência quantitativa: não é claim de design, é medição de prod. (Nota: sharing aqui é de storage e retrieval; cross-agent retrieval-level metrics são future work documentado no paper.)

### Pain baseline — post-incident queries são classe mais difícil

Sobre 6 queries extraídas de incidentes reais (post-incident class), nDCG@10 = **0.2689** — **−0.3142 vs baseline geral de 0.5831 (R01c-v1.1, n=60)**. Post-incident queries são intrinsically harder: linguagem mais técnica, contexto fragmentado, relevância distribuída por chunks de tipos distintos. Esse gap é o sinal que motiva pain-weighted salience: lições de incidente precisam de boost ativo no retrieval porque o retrieval vanilla já as penaliza passivamente. Pain ablation completa (comparar salience=shadow vs salience=off em prod) requer dois reinicios de produção e está documentada como future work no paper — os dados preliminares desta sessão ficam como evidência motivadora.

### §6.4 Perfil de custo e compute (OPEX real)

| Componente | Custo mensal estimado |
|---|---|
| Gemini embeddings (3072d, incrementais) | ~$4-6 |
| Gemini 2.5 Flash KG extraction (nightly) | ~$2-3 |
| SQLite + servidor VPS Hostinger | ~$2 |
| **Total OPEX** | **< $11/mês** |

Comparativo: MemGPT/Letta requer instância dedicada + modelo LLM por agente (≥$50/mês em escala de 6 agentes); GraphRAG implica LLM calls síncronas em cada query (custos variáveis não controlados); Mem0 managed tier começa em $20/mês por workspace. NOX-Supermem com 6 agentes e 61K chunks: **< $11/mês com p95 < 1s**. Custo por query não medido formalmente — future work documentado em §6.5.

### Validação contra strong baselines (W2 — concluída + em curso)

- **BM25 Pyserini** ✅ DONE — nDCG@10 = 0.1475 (n=60), nox-mem 3,5× acima
- **multilingual-e5-base** ✅ DONE — nDCG@10 = 0.3070, MRR=0.3720, Recall@10=0.3708 (n=60); hybrid entrega +0.2143 sobre E5 (1,7× lift). Decisão: NÃO trocar o embedding primário — hybrid ganha em 5/8 categorias, custo/benefício favorece Gemini.
- **LOCOMO (Maharana et al. 2024, snap-research/locomo, CC BY-NC 4.0)** ✅ DONE — FTS5 nDCG@10 = 0.2810 em n=100 stratified. Breakdown por categoria: open-domain 0.375, multi-hop 0.371, temporal 0.289, adversarial 0.253, single-hop 0.118. Ratio LOCOMO vs golden set (0.012): **23×** — confirma que dificuldade lexical é dependente de corpus, validando hybrid especificamente para regimes identifier-dense como o golden.
- **BEIR TREC-COVID** ✅ DONE — multilingual-e5-base nDCG@10=0.8335, MRR=0.8950 (n=50, 50K docs); BM25 (FTS5) nDCG@10=0.1007. Concluído 2026-05-05 01:18 BRT. Confirma que dificuldade lexical é corpus-dependente: e5 sobe 3 ordens de grandeza vs corpus interno (0.3070 → 0.8335).
- **E5-mistral-7b** — deferred para Modal cloud (opcional; não bloqueia submissão)

**Pre-registration:** golden-queries.jsonl git-tracked (commit f75d186), SHA-256 = 9bff8ee7…, 60 queries. Hipótese pré-registrada mantida: hybrid mantém vantagem ≥10% nDCG sobre qualquer dense baseline em corpus operacional. Resultados completos no paper arXiv (2026-05-19).

---

## Por que isto precisa entrar na literatura

A lacuna não é de performance — é de vocabulário. A comunidade científica de memória de agentes ainda não tem o conceito de *disciplina operacional como contribuição metodológica*. Este trabalho nomeia e formaliza três dimensões que os sistemas existentes ignoram:

**Severidade como sinal.** Pain-weighted salience é transferível a qualquer sistema de memória persistente. Não é feature do nox-mem — é dimensão que qualquer arquitetura poderia adotar. **Cobertura na literatura: zero papers.**

**Shadow gates como constraint, não sugestão.** A diferença entre documentar "considere validar em shadow antes de ativar" e codificar isso em cron + health endpoint é a diferença entre uma boa prática e uma garantia. **Cobertura na literatura: zero papers.**

**Reproducibilidade radical.** Quatro meses de incident log real, telemetria exposta via `/api/health`, eval harness com métricas padrão, repo público, schema versionado v1→v12. O reviewer pode refutar — ou confirmar — tudo. **Comparativo: 6 dos 7 sistemas analisados não publicam eval harness reproduzível.**

**Paridade arquitetural: 6/7 eixos cobertos, média dos competidores 1,6/7.** O sistema mais próximo (Cognee) cobre 3/7. nox-mem não cobre escala ≥100K — única lacuna documentada no paper. LOCOMO concluído (nDCG@10 = 0.281, n=100) e BEIR TREC-COVID concluído (e5 0.8335, BM25 0.1007, n=50). Nenhum dos sete competidores cobre as duas dimensões de maior novidade (pain weighting + shadow discipline).

**Construído solo, sem financiamento, em produção real.** Não em benchmark sintético. As cicatrizes estão no incident log — e o incident log está no repo.

A literatura merece conhecer o que acontece quando alguém constrói um sistema de memória de agentes e deixa os próprios erros ensinarem a arquitetura.

---

## Como ler e quando sai

- **arXiv preprint** — *The Pain Diary and Shadow Discipline: A Memory System That Learns from Its Own Incidents* — 2026-05-19
- **Blog dev.to + Substack** — 2026-05-20
- **Hacker News** — 2026-05-21, 09:00 ET

*Construído solo por um empreendedor nerd em São Paulo. Os incidents estão no log. O log está no schema. O schema está no paper.*
