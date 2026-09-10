# As 14 referências que faltam vêm do survey canônico — mineradas, não escolhidas

> Medido 2026-09-10 sobre `arXiv:2602.06052v4`, *A Survey of Agent Memory in the Second
> Half* (TMLR), o mapa canônico da área. Artefato:
> `data/candidatas-survey-2026-09-10.json`. O alvo de **14** vem do
> `regua-do-nosso-lado-2026-09-10.md`, que recontou o nosso numerador com o método
> declarado dos dois lados.

---

## 1. O achado que vem antes das candidatas

**Das 535 obras que o survey cita, nós citamos 17.** As duas bibliografias são quase
disjuntas. Metade disso é escopo legítimo — o survey trata de agentes auto-evolutivos e
horizonte longo, nós tratamos de recuperação e retenção num sistema em produção. A outra
metade é o que um revisor lê: o survey canônico da área cita 535 obras, e o nosso trabalho
compartilha 17 delas.

Entre as ausentes está *A Survey on the Memory Mechanism of Large Language Model based
Agents* (ACM TOIS), citada em **seis** seções do próprio survey. É o levantamento do nosso
tema exato, e não o citávamos.

## 2. Método, e os dois controles

Centralidade não vem do meu mapeamento posicional — vem do `Cited by: §7.1, §7.2.1` que o
LaTeXML **embute em cada bibitem**; 483 dos 535 o trazem. Conta seções distintas.

Presença verificada contra os nossos 35 arXiv IDs **e** contra os títulos canônicos do
`authors-manifest.json` (não contra os que eu digitei). O classificador só foi reportável
depois de:

- **controle positivo**, 5 obras que citamos e o survey também: `mem0` e `zep` casaram por
  id; *Generative Agents*, *LongMemEval* e *HippoRAG* casaram por título — as três têm
  `arXiv: None` no bibitem do survey, que as cita pelo venue. Um classificador só por id
  reportaria 6 de 535 em vez de 17;
- **controle negativo**, obra inventada com id inexistente, que sai como não citada.

A primeira versão deste controle acusou *Generative Agents* como falso negativo. Era o
controle que estava errado: o fragmento `generative agents` casa **quatro** bibitems e o
primeiro é outro trabalho. Um controle que localiza o alvo por fragmento ambíguo testa a
obra errada — agora ele exige casamento único e falha se o fragmento for ambíguo.

Corte em **≥4 seções**: 21 ausentes. Admissibilidade decidida contra o que o nosso texto
**discute**, não contra a centralidade no survey.

## 3. Grupo A — entram primeiro (6)

A vizinhança direta, onde a discussão já existe no nosso texto e falta a referência.

| obra | seções | localizador | onde encaixa, e contra o quê |
|---|---:|---|---|
| A survey of self-evolving agents: on path to artificial super intelligence | 6 | `arXiv:2507.21046` | auto-evolucao — nosso crystallize/reflect |
| A survey on the memory mechanism of large language model-based agents . AC | 6 | `arXiv:2404.13501` | survey do nosso proprio tema; §1.5 Related Work |
| Reasoningbank: scaling agent self-evolving with reasoning memory | 5 | `arXiv:2509.25140` | destila estrategia de experiencia = analogo do nosso crystallize |
| Beyond goldfish memory: long-term open-domain conversation | 4 | `arXiv:2107.07567` | antecessor direto do LoCoMo/LongMemEval que usamos no §6 |
| From isolated conversations to hierarchical schemas: dynamic tree memory r | 4 | `arXiv:2410.14052` | memoria hierarquica de conversa vs. nosso entity/section |
| Mirix: multi-agent memory system for llm-based agents | 4 | `arXiv:2507.07957` | memoria multi-agente — nosso cross_search entre 6 agentes |

## 4. Grupo B — uma frase de contraste cada (7)

Todas contrastam com uma escolha nossa que o paper já defende: fórmula fixa de salience,
retenção tipada, `reflect`, recuperação agêntica. O contraste é o conteúdo — não é
citação decorativa.

| obra | seções | localizador | onde encaixa, e contra o quê |
|---|---:|---|---|
| Mem- α \alpha : learning memory construction via reinforcement learning | 5 | `arXiv:2509.25911` | RL aprende a construir memoria vs. nossa formula fixa de salience |
| MemAgent: reshaping long-context llm with multi-conv rl-based memory agent | 5 | `arXiv:2507.02259` | long-context via memoria |
| In prospect and retrospect: reflective memory management for long-term per | 4 | `arXiv:2503.08026` | reflexao prospectiva/retrospectiva — nosso reflect |
| MEM1: learning to synergize memory and reasoning for efficient long-horizo | 4 | `arXiv:2506.15841` | idem, com consolidacao |
| Memory as action: autonomous context curation for long-horizon agentic tas | 4 | `arXiv:2510.12635` | curadoria de contexto vs. nosso retention tipado |
| Memory-r1: enhancing large language model agents to manage and utilize mem | 4 | `arXiv:2508.19828` | RL para operacoes de memoria — mesmo contraste |
| When not to trust language models: investigating effectiveness of parametr | 4 | `arXiv:2212.10511` | quando recuperar vs. parametrico — §1.4 |

## 5. Grupo C — marginais (2)

| obra | seções | localizador | onde encaixa, e contra o quê |
|---|---:|---|---|
| WebCoach: self-evolving web agents with cross-session memory guidance | 5 | `arXiv:2511.12997` | memoria cross-session, mas em agente web (fora do nosso setup) |
| MemSearcher: training llms to reason, search and manage memory via end-to- | 4 | `arXiv:2511.02805` | agentic retrieval, ao lado de IRCoT/Self-Ask que ja citamos |

## 6. As 6 que eu RECUSEI, e por quê

Densidade comprada com citação decorativa é o mesmo defeito de forma que este trabalho
existe para consertar, com o sinal trocado — e é detectável por qualquer revisor que
procure a menção no corpo.

| obra | seções | localizador | onde encaixa, e contra o quê |
|---|---:|---|---|
| WebArena: a realistic web environment for building autonomous agents | 6 | `arXiv:None` | benchmark de agente web — nao medimos |
| SWE-bench: can language models resolve real-world github issues? | 5 | `arXiv:None` | benchmark de codigo — nao medimos |
| Voyager: an open-ended embodied agent with large language models | 5 | `arXiv:None` | agente embodied — fora |
| Efficient memory management for large language model serving with pagedatt | 4 | `arXiv:None` | PagedAttention: 'memoria' de KV cache, HOMONIMO |
| Learning on the job: an experience-driven self-evolving agent for long-hor | 4 | `arXiv:2510.08002` | conducao autonoma — fora |
| Osworld: benchmarking multimodal agents for open-ended tasks in real compu | 4 | `arXiv:None` | benchmark de SO — nao medimos |

O caso do PagedAttention merece nome: *Efficient Memory Management for LLM Serving* é
citada em quatro seções do survey e a palavra «memória» aparece no título, mas ali ela
significa **KV cache**, não memória de agente. Citá-la porque o termo casa é o homônimo
tomado por vizinho.

## 7. Contagem

**A (6) + B (7) = 13**, e com uma de C fecha **14** — o alvo do ponto fixo. Sobram as duas
de C e as 337 ausentes de citação única do survey como folga, sem precisar de nenhuma
das 6 recusadas.

Cada uma das 15 admissíveis tem localizador `arXiv` resolvido: 10 vinham no próprio
bibitem; **5 foram resolvidas pela API do arXiv**, com controle positivo de dois IDs que já
conhecíamos antes de aceitar qualquer resultado — a autoria devolvida casa a que o survey
imprime nos cinco casos.

⚠️ **Nenhuma entra sem discussão no texto**, e o `claims_check.py` prende as duas pontas:
footnote definida e nunca citada é enchimento (falha), e footnote nova sem classificação no
`bibitem-census.json` também (falha).
