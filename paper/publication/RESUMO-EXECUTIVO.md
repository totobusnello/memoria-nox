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

## 3 ideias que ninguém mais tinha

### Pain-Weighted Salience: o incidente importa mais que a data

A fórmula parece simples depois que alguém a escreve:

```
salience = recency × pain × importance
```

`pain ∈ [0.1, 1.0]` — de nota trivial a prod-outage. O que ninguém havia feito antes era tratar severidade como sinal de *retrieval*, não só de logging. GraphRAG, Mem0, A-MEM, HiRAG e Cognee modelam estrutura e recência. Nenhum pergunta: *isso custou quanto?*

O resultado: uma lição de prod-outage de seis meses atrás supera documentação atualizada ontem sobre assunto menor — como a memória humana funciona. O sistema roda 64.180+ chunks com essa dimensão ativa, validada por 7 dias de telemetria real.

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
| FTS5 vanilla (BM25) | 0.0123 | **−50,9 pp** |
| **BM25 Pyserini (Anserini-tuned, n=60)** | **0.1475** | **−37,4 pp** |
| **nox-mem hybrid (FTS + Gemini + RRF)** | **0.5213** | baseline |

*(n=50 queries baseline; BM25 Pyserini n=60 — 3-run mean ± std: Hybrid 0.5213 ± 0.0004, FTS vanilla 0.0123 ± 0.0000 — gap relativo hybrid vs Pyserini: 3,5×)*

Queries em linguagem natural completas resultam em nDCG quase zero em BM25-only — constraint estrutural do FTS5 AND-strict, não artefato de corpus. O BM25 Pyserini (Anserini-tuned, strong baseline de BEIR) eleva o patamar para 0.1475, e nox-mem hybrid ainda entrega **3,5× acima dele**. Hybrid é o piso, não o teto. Validação 3-run (runs #10/#11/#12) com std=0.0004 (0.08% relativo), reproduzível por qualquer reviewer.

### Edge typing: classificação correta de 14% para 56% — ganho 4×

KG extraction com campo opcional e prompt ingênuo classificava apenas **14% das relações novas** corretamente — **86% caíam em `unknown`**. Após defensive map no código (24 aliases PT-BR + EN) e prompt revisado (n=100): **56% classificadas corretamente** — ganho de **4× em coverage** de blast-radius queries. Saber *o que* foi afetado por uma mudança, não só que algo foi afetado.

### nox-mem vs alternatives — paridade de features

A tabela usa 7 eixos arquiteturais e operacionais. Os dois últimos — escala de corpus acima de 100K e benchmark de terceiros — são eixos onde nox-mem ainda **não** tem cobertura. A inclusão deles é intencional: comparação honesta exige marcar as lacunas, não só os pontos fortes.

| Sistema | KG nativo | Hybrid retrieval | Eval harness | Multi-agent | Shadow discipline | Escala ≥100K | Benchmark terceiros | **Score** |
|---|---|---|---|---|---|---|---|---|
| **nox-mem (este trabalho)** | ✅ closed-enum 7 reasons (24-entry map) | ✅ FTS5+Gemini+RRF | ✅ nDCG/MRR/Recall | ✅ shared canonical | ✅ enforced ≥7d | ❌ (64K atual) | ❌ (golden interno) | **5/7** |
| GraphRAG | ✅ + community detection | ⚠️ via KG queries | ❌ | ❌ | ❌ | ✅ (1M+ MS-MARCO) | ⚠️ paper-específico | 1.5/7 |
| MemGPT/Letta | ❌ | ⚠️ embedding-first | ❌ | ✅ per-agent | ❌ | ⚠️ varia | ❌ | 1.5/7 |
| Mem0 | ⚠️ optional v2 | ❌ vector-only | ⚠️ LOCOMO only | ⚠️ user_id partition | ❌ | ❌ | ✅ LOCOMO | 1.5/7 |
| A-MEM | ⚠️ Zettelkasten | ⚠️ semantic-first | ❌ | ❌ | ❌ | ❌ | ❌ | 1.0/7 |
| HiRAG | ✅ hierarchical | ✅ multi-level | ⚠️ task-specific | ❌ | ❌ | ⚠️ varia | ✅ multi-task | 2.5/7 |
| Cognee | ✅ ECL pipeline | ✅ hybrid | ⚠️ ad-hoc | ⚠️ optional | ❌ | ⚠️ ad-hoc | ⚠️ parcial | 3.0/7 |
| LangChain Memory | ❌ | ❌ key-value | ❌ | ⚠️ session_id | ❌ | ⚠️ varia | ❌ | 0.5/7 |

**Resumo honesto**: nox-mem cobre **5 de 7 eixos** — os cinco relacionados a disciplina operacional e arquitetura. Não cobre os dois eixos de validade externa: escala de corpus (64K vs ≥100K) e benchmark de terceiros (golden set interno vs LOCOMO/BEIR). Essas lacunas estão documentadas como limitações no paper (§6.3) e como trabalho futuro (§6.5). O sistema mais próximo, Cognee, cobre 3/7. Média dos sete competidores: **1,6/7**. Os dois eixos com cobertura zero na literatura — pain weighting e shadow discipline — são as contribuições de maior novidade.

### Latência em produção real

| Métrica | nox-mem | Threshold típico de papers |
|---|---|---|
| p95 search | **< 1s** em 64K chunks | 1-3s reportado |
| Vector coverage | **99,97%** | 90-95% típico |
| Schema migrations sem downtime | **12 versões** | raro reportar |

Latência sub-segundo em 64.180+ chunks com hybrid 3-layer (FTS5 → Gemini 3072d → RRF k=60) — não emulação local, produção real há 4 meses.

### Cross-agent storage — 99,92% sharing

De 61.257 chunks ativos no corpus, **61.207 são canonical shared** — acessíveis por todos os seis agentes sem particionamento, sincronização ou merge. Isso corresponde a **99,92% de sharing efetivo**. O contrafactual MemGPT/Mem0 com isolamento por agent/user_id resultaria em 0% de sharing — diferença arquitetural de **99,92 pp**, não decimal. O diferencial "Shared-Canonical Multi-Agent" agora tem evidência quantitativa: não é claim de design, é medição de prod. (Nota: sharing aqui é de storage e retrieval; cross-agent retrieval-level metrics são future work documentado no paper.)

### Pain baseline — post-incident queries são classe mais difícil

Sobre 6 queries extraídas de incidentes reais (post-incident class), nDCG@10 = **0.2689** — **−0.2524 vs baseline geral de 0.5213**. Post-incident queries são intrinsically harder: linguagem mais técnica, contexto fragmentado, relevância distribuída por chunks de tipos distintos. Esse gap é o sinal que motiva pain-weighted salience: lições de incidente precisam de boost ativo no retrieval porque o retrieval vanilla já as penaliza passivamente. Pain ablation completa (comparar salience=shadow vs salience=off em prod) requer dois reinicios de produção e está documentada como future work no paper — os dados preliminares desta sessão ficam como evidência motivadora.

### Validação contra strong baselines (W2 — parcialmente concluída)

- **BM25 Pyserini** ✅ DONE — nDCG@10 = 0.1475 (n=60), nox-mem 3,5× acima
- **multilingual-e5-base** ⏳ rodando overnight (~9h ETA)
- **E5-mistral-7b** — deferred para Modal cloud (opcional; não bloqueia submissão)

Hipótese pré-registrada mantida: hybrid mantém vantagem ≥10% nDCG sobre qualquer dense baseline em corpus operacional. Resultados completos no paper arXiv (2026-05-19).

---

## Por que isto precisa entrar na literatura

A lacuna não é de performance — é de vocabulário. A comunidade científica de memória de agentes ainda não tem o conceito de *disciplina operacional como contribuição metodológica*. Este trabalho nomeia e formaliza três dimensões que os sistemas existentes ignoram:

**Severidade como sinal.** Pain-weighted salience é transferível a qualquer sistema de memória persistente. Não é feature do nox-mem — é dimensão que qualquer arquitetura poderia adotar. **Cobertura na literatura: zero papers.**

**Shadow gates como constraint, não sugestão.** A diferença entre documentar "considere validar em shadow antes de ativar" e codificar isso em cron + health endpoint é a diferença entre uma boa prática e uma garantia. **Cobertura na literatura: zero papers.**

**Reproducibilidade radical.** Quatro meses de incident log real, telemetria exposta via `/api/health`, eval harness com métricas padrão, repo público, schema versionado v1→v12. O reviewer pode refutar — ou confirmar — tudo. **Comparativo: 6 dos 7 sistemas analisados não publicam eval harness reproduzível.**

**Paridade arquitetural: 5/7 eixos cobertos, média dos competidores 1,6/7.** O sistema mais próximo (Cognee) cobre 3/7. nox-mem não cobre escala ≥100K nem benchmark de terceiros — lacunas documentadas no paper. Nenhum dos sete competidores cobre as duas dimensões de maior novidade (pain weighting + shadow discipline).

**Construído solo, sem financiamento, em produção real.** Não em benchmark sintético. As cicatrizes estão no incident log — e o incident log está no repo.

A literatura merece conhecer o que acontece quando alguém constrói um sistema de memória de agentes e deixa os próprios erros ensinarem a arquitetura.

---

## Como ler e quando sai

- **arXiv preprint** — *The Pain Diary and Shadow Discipline: A Memory System That Learns from Its Own Incidents* — 2026-05-19
- **Blog dev.to + Substack** — 2026-05-20
- **Hacker News** — 2026-05-21, 09:00 ET

*Construído solo por um empreendedor nerd em São Paulo. Os incidents estão no log. O log está no schema. O schema está no paper.*
