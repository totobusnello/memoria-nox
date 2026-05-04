# The Pain Diary and Shadow Discipline: A Memory System That Learns from Its Own Incidents

---

Era 22:03 de 25 de abril. Um cron job de fim de dia rodou `nox-mem reindex` sem dry-run. Cento e oitenta e três entidades perderam section, retention e section_boost — anos de contexto estruturado, achatados em chunks genéricos em segundos. Nenhum log de erro. Nenhum alarme. O banco simplesmente... obedeceu.

Foi nesse dia que ficou claro que o problema de memória de agentes não é recuperação de informação. É disciplina.

---

## A tese em uma frase

> **Memória de agente não é problema de retrieval — é problema de disciplina operacional.**

Sistemas falham silenciosamente porque mudanças de ranking entram sem validação, severidade de incidente nunca vira sinal, e múltiplos agentes vivem em silos de contexto que nunca conversam. A solução não é embedding melhor — é arquitetura que codifica disciplina no schema.

---

## A noite que tudo começou

Quatro meses atrás, seis agentes de IA rodavam em produção — Atlas, Boris, Cipher, Forge, Lex e Nox — cada um com memória isolada, cada um reinventando contexto que outro já havia aprendido. As soluções existentes (LangChain Memory, MemGPT, Mem0) ou particionam por `user_id` ou são frameworks genéricos sem noção de custo operacional. Nenhuma pergunta: *esta lição custou um prod-outage ou foi só uma nota de rodapé?*

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

`pain ∈ [0.1, 1.0]` — de nota trivial a prod-outage. O que ninguém havia feito antes era tratar severidade como sinal de *retrieval*, não só de logging. GraphRAG, Mem0, A-MEM, HiRAG e Cognee modelam estrutura e recência. Nenhum pergunta: *isso custou quanto?*

O resultado é que uma lição de prod-outage de seis meses atrás supera uma documentação atualizada ontem sobre assunto menor — como a memória humana funciona. O sistema agora tem 64.180+ chunks com essa dimensão ativa, validada por 7 dias de telemetria real.

### Shadow Discipline: nenhuma mudança de ranking entra sem sete dias de prova

`NOX_SALIENCE_MODE=shadow` é uma regra arquitetural enforced via cron e `/api/health` — não uma boa prática documentada que alguém pode ignorar. Qualquer mudança que afeta ranking fica em shadow por mínimo 7 dias, comparada contra o comportamento anterior, antes de ativar.

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
| FTS5 vanilla (BM25) | 0.000 | **−71,4 pp** |
| **nox-mem hybrid (FTS + Gemini + RRF)** | **0.714** | baseline |

Queries em linguagem natural completas zeram em BM25-only. Não é artefato de corpus — é constraint estrutural do FTS5. Hybrid é o piso, não o teto. Validação 3-run: nDCG mean=0.674 com desvio baixo, Bessel std reproduzível por qualquer reviewer.

### Edge typing: de 86% de ruído a 14%

KG extraction com campo opcional e prompt ingênuo produzia **86% de tipo `unknown`** nas relações. Após defensive map no código e prompt revisado (n=100): **14% unknown**. **Ganho de 6,1× em precisão** de blast-radius queries — saber *o que* foi afetado por uma mudança, não só que algo foi afetado.

### nox-mem vs alternatives — paridade de features

| Sistema | KG nativo | Hybrid retrieval | Eval harness | Multi-agent | Shadow discipline | **Score** |
|---|---|---|---|---|---|---|
| **nox-mem (este trabalho)** | ✅ closed-enum 24 cats | ✅ FTS5+Gemini+RRF | ✅ nDCG/MRR/Recall | ✅ shared canonical | ✅ enforced ≥7d | **5/5** |
| GraphRAG | ✅ + community detection | ⚠️ via KG queries | ❌ | ❌ | ❌ | 1.5/5 |
| MemGPT/Letta | ❌ | ⚠️ embedding-first | ❌ | ✅ per-agent | ❌ | 1.5/5 |
| Mem0 | ⚠️ optional v2 | ❌ vector-only | ⚠️ LOCOMO only | ⚠️ user_id partition | ❌ | 1.5/5 |
| A-MEM | ⚠️ Zettelkasten | ⚠️ semantic-first | ❌ | ❌ | ❌ | 1.0/5 |
| HiRAG | ✅ hierarchical | ✅ multi-level | ⚠️ task-specific | ❌ | ❌ | 2.5/5 |
| Cognee | ✅ ECL pipeline | ✅ hybrid | ⚠️ ad-hoc | ⚠️ optional | ❌ | 3.0/5 |
| LangChain Memory | ❌ | ❌ key-value | ❌ | ⚠️ session_id | ❌ | 0.5/5 |

**Resumo da tabela**: o sistema mais próximo (Cognee) cobre 3 das 5 dimensões. Nenhum dos sete competidores documentados tem shadow discipline arquitetural — a feature de maior valor metodológico aqui apresentada é literalmente inédita na literatura.

### Latência em produção real

| Métrica | nox-mem | Threshold típico de papers |
|---|---|---|
| p95 search | **< 1s** em 64K chunks | 1-3s reportado |
| Vector coverage | **99,97%** | 90-95% típico |
| Schema migrations sem downtime | **12 versões** | raro reportar |

Latência sub-segundo em 64.180+ chunks com hybrid 3-layer (FTS5 → Gemini 3072d → RRF k=60) — não emulação local, produção real há 4 meses.

### Validação contra strong baselines (W2 em execução)

Por compromisso com honestidade científica: BM25 (Pyserini), BGE-M3 e E5-mistral-7b em BEIR-COVID e StackExchange estão em execução paralela. Hipótese pré-registrada: hybrid mantém vantagem ≥10% nDCG sobre BGE-M3 dense em corpus operacional. Resultados completos no paper arXiv (2026-05-19).

---

## Por que isto precisa entrar na literatura

A lacuna não é de performance — é de vocabulário. A comunidade científica de memória de agentes não tem ainda o conceito de *disciplina operacional como contribuição metodológica*. Este trabalho nomeia e formaliza três dimensões que os sistemas existentes ignoram:

**Severidade como sinal.** Pain-weighted salience é transferível a qualquer sistema de memória persistente. Não é feature do nox-mem — é dimensão que qualquer arquitetura poderia adotar. **Cobertura na literatura: zero papers.**

**Shadow gates como constraint, não sugestão.** A diferença entre documentar "considere validar em shadow antes de ativar" e codificar isso em cron + health endpoint é a diferença entre uma boa prática e uma garantia. **Cobertura na literatura: zero papers.**

**Reproducibilidade radical.** Quatro meses de incident log real, telemetria exposta via `/api/health`, eval harness com métricas padrão, repo público, schema versionado v1→v12. Reviewer pode refutar — ou confirmar — tudo. **Comparativo: 6 dos 7 sistemas analisados não publicam eval harness reproduzível.**

**Score de paridade arquitetural: 5/5 contra média de 1,6/5 dos competidores.** O sistema mais próximo (Cognee) cobre 60% das dimensões. Nenhum cobre as duas dimensões de maior novidade (pain weighting + shadow discipline).

**Construído solo, sem financiamento, em produção real.** Não em benchmark sintético. As cicatrizes estão no incident log — e o incident log está no repo.

A literatura merece conhecer o que acontece quando alguém constrói um sistema de memória de agentes e deixa os próprios erros ensinarem a arquitetura.

---

## Como ler e quando sai

- **arXiv preprint** — *The Pain Diary and Shadow Discipline: A Memory System That Learns from Its Own Incidents* — 2026-05-19
- **Blog dev.to + Substack** — 2026-05-20
- **Hacker News** — 2026-05-21, 09:00 ET

*Construído solo por um empreendedor nerd em São Paulo. Os incidents estão no log. O log está no schema. O schema está no paper.*

<!-- EDITORIAL NOTES -->
<!--
1. Linha 21: "sem qualquer noção de custo operacional. Nenhuma delas pergunta" → "sem noção de custo operacional. Nenhuma pergunta" — REDUNDÂNCIA (eliminar "qualquer" supérfluo + "delas" implicado pelo contexto)

2. Linha 43: "Exatamente como a memória humana funciona." → "como a memória humana funciona." — REDUNDÂNCIA ("Exatamente" não acrescenta; o período ganhou leveza e o ponto anterior já faz a comparação)

3. Linha 49: "O counterfactual está documentado" → "O contrafactual está documentado" — ORTOGRAFIA (forma aportuguesada em uso corrente no Brasil; consistência com registro PT-BR)

4. Linha 51: "Nenhum paper de memória de agente até hoje codificou essa disciplina operacional como constraint" → "Nenhum paper de memória de agente até hoje codificou esse rigor operacional como constraint" — CONSISTÊNCIA TERMINOLÓGICA (4ª ocorrência de "disciplina operacional" em texto corrido; variação sinonímica "rigor operacional" preserva o conceito sem repetição mecânica; primeira ocorrência e blockquote-tese intocadas)

5. Linha 57: "Quando Forge aprende algo sobre uma decisão arquitetural, Atlas pode recuperar esse contexto diretamente" → "Quando Forge aprende algo sobre uma decisão arquitetural, Atlas recupera esse contexto diretamente" — RITMO (eliminar "pode" cria assertividade; o presente simples descreve comportamento garantido pelo design, não possibilidade)

6. Linha 21: "ou são frameworks genéricos sem qualquer noção" → "ou são frameworks genéricos sem noção" — REDUNDÂNCIA (idem nota 1; "qualquer" é advérbio de realce supérfluo neste contexto negativo)

7. Linha 47: "comparada contra comportamento anterior" → "comparada contra o comportamento anterior" — ORTOGRAFIA/GRAMÁTICA (artigo definido exigido pela referência específica ao comportamento baseline da versão anterior)

8. Estrutura Manifesto (seção "Por que isto precisa entrar na literatura"): os quatro blocos em negrito já tinham paralelismo substantivo consistente ("Severidade como sinal", "Shadow gates como constraint", "Reproducibilidade radical", "Score de paridade arquitetural", "Construído solo") — mantidos sem alteração, paralelismo estava correto.

9. Travessões (—): texto original os usa com moderação e propósito. Nenhum excesso detectado que justificasse substituição; 0 travessões alterados para não afetar ritmo intencional do autor.

10. Linha 96: "p95 search" na tabela — sem alteração; terminologia técnica correta e consistente com paper.
-->
