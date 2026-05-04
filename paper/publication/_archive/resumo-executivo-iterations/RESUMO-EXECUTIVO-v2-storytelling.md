# The Pain Diary and Shadow Discipline: A Memory System That Learns from Its Own Incidents

---

Era 22:03 de 25 de abril. Um cron job de fim de dia rodou `nox-mem reindex` sem dry-run. Cento e oitenta e três entidades perderam section, retention e section_boost — anos de contexto estruturado, achatados em chunks genéricos em segundos. Nenhum log de erro. Nenhum alarme. O banco simplesmente... obedeceu.

Foi esse o dia em que ficou claro que o problema de memória de agentes não é recuperação de informação. É disciplina.

---

## A tese em uma frase

> **Memória de agente não é problema de retrieval — é problema de disciplina operacional.**

Sistemas falham silenciosamente porque mudanças de ranking entram sem validação, severidade de incidente nunca vira sinal, e múltiplos agentes vivem em silos de contexto que nunca conversam. A solução não é embedding melhor — é arquitetura que codifica disciplina no schema.

---

## A noite que tudo começou

Quatro meses atrás, seis agentes de IA rodavam em produção — Atlas, Boris, Cipher, Forge, Lex e Nox — cada um com memória isolada, cada um reinventando contexto que outro já havia aprendido. As soluções existentes (LangChain Memory, MemGPT, Mem0) ou particionam por `user_id` ou são frameworks genéricos sem qualquer noção de custo operacional. Nenhuma delas pergunta: *esta lição custou um prod-outage ou foi só uma nota de rodapé?*

O sistema nasceu da observação de que lições caras precisam de tratamento diferente de documentação trivial. Não como política editorial — como sinal matemático no retrieval.

E então vieram os incidents. Em 25 de abril, o reindex sem dry-run apagou 183 entities. Em 1 de maio, um `sed -i` acidental corrompeu 1 GB de SQLite mais 8 backups — porque ninguém havia codificado a regra "nunca sed em binário" como proteção automática. Cada catástrofe operacional virou uma linha no schema. Cada cicatriz, uma feature.

Esse é o paper.

---

## 3 ideias que ninguém mais tinha

### Pain-Weighted Salience: o incidente importa mais que a data

A fórmula parece simples depois que alguém a escreve:

```
salience = recency × pain × importance
```

`pain ∈ [0.1, 1.0]` — de nota trivial a prod-outage. O que ninguém havia feito antes era tratar severidade como sinal de *retrieval*, não só de logging. GraphRAG, Mem0, A-MEM, HiRAG e Cognee modelam estrutura e recência. Nenhum pergunta: isso custou quanto?

O resultado é que uma lição de prod-outage de seis meses atrás supera uma documentação atualizada ontem sobre assunto menor. Exatamente como a memória humana funciona. O sistema agora tem 64.180+ chunks com essa dimensão ativa, em shadow-mode validado por telemetria real.

### Shadow Discipline: nenhuma mudança de ranking entra sem sete dias de prova

`NOX_SALIENCE_MODE=shadow` é uma regra arquitetural enforced via cron e `/api/health` — não uma boa prática documentada que alguém pode ignorar. Qualquer mudança que afeta ranking fica em shadow por mínimo 7 dias, comparada contra comportamento anterior, antes de ativar.

A validação de salience (Fase 1.7b-b) rodou 7 dias de telemetria: 191 promoções, 16.608 revisões, 45.743 arquivamentos. Só então ativou. O counterfactual está documentado: o incident de 25 de abril — exatamente o tipo de regressão silenciosa — seria detectado em shadow antes de chegar a prod.

Nenhum paper de memória de agente até hoje codificou essa disciplina como constraint arquitetural. A maioria nem menciona o problema.

### Shared-Canonical Multi-Agent: um corpus, seis agentes, zero federação

MemGPT usa per-agent state. Mem0 usa partição por `user_id`. Os seis agentes deste sistema leem do **mesmo corpus canônico** — sem sincronização, sem merge, sem overhead de federação. Cross-agent intelligence por design, não por gambiarra.

Quando Forge aprende algo sobre uma decisão arquitetural, Atlas pode recuperar esse contexto diretamente na próxima query relevante. Não porque alguém sincronizou — porque nunca houve separação.

---

## Os números que destroem a dúvida

### Hybrid não é otimização — é requisito

| Approach | nDCG@10 |
|---|---|
| FTS5 vanilla (BM25) | 0.000 |
| Hybrid (FTS + Gemini + RRF) | 0.714 |
| Delta | +0.714 |

Queries em linguagem natural completas zeram em BM25-only. Não é artefato de corpus — é constraint estrutural do FTS5. Hybrid é o piso, não o teto.

### Edge typing: de 86% de ruído a 14%

KG extraction com campo opcional e prompt ingênuo produzia 86% de tipo `unknown` nas relações. Após defensive map no código e prompt revisado (n=100): 14% unknown. Ganho de 6× em precisão de blast-radius queries — saber o que foi afetado por uma mudança, não só que algo foi afetado.

### Validação multi-run com Bessel correction

nDCG mean=0.674 com desvio baixo em 3 runs independentes. Não é cherry-picking de resultado único. O eval harness é público: nDCG@10, MRR e Recall@10 com Bessel std, reproduzível por qualquer reviewer.

**Estado técnico atual:** 64.180+ chunks, 99.97% vector coverage (Gemini 3072d), 402 entidades KG, 544 relações com edge typing em 24 categorias, latência p95 < 1s, schema v12 com retention/pain/section typed.

---

## Por que isto precisa entrar na literatura

A lacuna não é de performance — é de vocabulário. A comunidade científica de memória de agentes não tem ainda o conceito de *disciplina operacional como contribuição metodológica*. Este trabalho nomeia e formaliza três dimensões que os sistemas existentes ignoram:

**Severidade como sinal.** Pain-weighted salience é transferível a qualquer sistema de memória persistente. Não é feature do nox-mem — é dimensão que qualquer arquitetura poderia adotar.

**Shadow gates como constraint, não sugestão.** A diferença entre documentar "considere validar em shadow antes de ativar" e codificar isso em cron + health endpoint é a diferença entre uma boa prática e uma garantia.

**Reproducibilidade radical.** Quatro meses de incident log real, telemetria exposta via `/api/health`, eval harness com métricas padrão, repo público. Reviewer pode refutar — ou confirmar — tudo.

**Validação contra strong baselines** (em execução): BM25 Pyserini, BGE-M3 e E5-mistral-7b em BEIR-COVID e StackExchange. Não só corpus interno.

**Construído solo, sem financiamento, em produção real.** Não em benchmark sintético. As cicatrizes estão no incident log — e o incident log está no repo.

A literatura merece conhecer o que acontece quando alguém constrói um sistema de memória de agentes e deixa os próprios erros ensinarem a arquitetura.

---

## Como ler e quando sai

- **arXiv preprint** — 2026-05-19
- **Blog dev.to + Substack** — 2026-05-20
- **Hacker News** — 2026-05-21, 09:00 ET

*Construído solo por um empreendedor nerd em São Paulo. Os incidents estão no log. O log está no schema. O schema está no paper.*
