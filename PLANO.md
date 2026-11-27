# PLANO — papers-memoria

> Gerado pelo `dev-flow` em 2026-11-04 22h (BRT). Fonte de verdade do projeto entre sessões.
> Revisado em 2026-11-04 22h10 depois das vozes Codex e Kimi (seção Vozes).

## Objetivo

- **Problema:** o memoria-nox já mediu muito sobre memória de agente que não está publicado:
  como a régua de busca em PT-BR engana, o que o KG de fato guarda, e que a memória empurrada pelo
  brief não deixa traço no que os agentes escrevem. Essas medições vivem em `audits/`, com várias
  gerações de números, algumas superadas. Publicar exige primeiro dizer qual número vale e de onde
  ele vem. O Paper 3 deixou também uma pergunta aberta: o critério C2 muda o que a destilação
  produz no corpus de produção que o motivou?
- **Para quem:** quem avalia ou constrói memória de agente, e o roadmap do nox-mem, que decide gasto
  (extração de KG, busca, brief) por esses números.
- **Entrega mínima (critério de aceite):** o paper A depositado no Zenodo com DOI, com manifesto de
  proveniência e gates de paridade e de privacidade verdes, e card no labf.bio. Zenodo dá
  arquivamento e DOI, não revisão por pares; o paper diz isso.

## Os quatro papers

| | objeto | formato | o que já está medido, na versão que vale | o que falta |
|---|---|---|---|---|
| **A** | Avaliar busca numa memória viva em PT-BR | paper completo | gold por chunk id apodrece (61 de 85 ids mortos, 71,8%); gold v2 ancorado por trecho: 95 âncoras, 91 exatas, 4 ambíguas, 0 não resolvidas; juiz chamou de verbatim 48 de 139 citações que não estavam no chunk (34,5%); juiz não sustenta negativa; cobertura inicial do top-10 de 9,1% (50/548); régua v3 com top-10 inteiro julgado (57 queries): strict 0,2567, pooled 0,4394; o check de citação de 8 palavras custa 0,105 de kappa (0,5458 → 0,4412, 510 pares); ideal montado só com o que o ranking devolveu superestimava o nDCG do juiz delimitado (queda de −6,8% era −15,6%) | separar o que é retrospectivo do que é novo; queries novas reservadas (holdout) para a parte confirmatória; amostra humana cega; um corpus sintético pequeno em PT-BR para os testes de método (reingest, troca de id, edição, exclusão) |
| **B** | O que um KG extraído por LLM guarda | nota de dados, descritiva | fidelidade 0,900 (135/150, Wilson [0,842; 0,938]), com a ressalva de que a amostra foi gasta para definir os critérios; 59 das 150 relações amostradas usam predicado hapax (39,3%); 82,2% da evidência do grafo vem do cofre de documentos (14.592 de 17.753; 74,7% na amostra); 98,7% das relações nascidas em julho | censo atual; amostra nova, adjudicada de forma independente, se a nota for afirmar fidelidade |
| **C** | Nenhum traço textual da memória empurrada | nota de dados, estreita e datada | 7a: 0 de 12.782 pares expostos com traço (1.524 mensagens, três raízes de transcript); R1: 0 de 574 mensagens nos dois braços, detector com controle positivo de 287/300 e 300/300; 337 de 382 buscas eram a sonda canária e nenhuma era de agente (até 21/10); 7b: controle positivo 0/10, fase principal não rodou, valor plantado aparece na ação em 3 de 28 | nada obrigatório; a nota afirma «não detectamos traço textual nem mudança da primeira ação nestes protocolos», e cita o 23/10, em que um agente com tarefa que exigia busca fez 11 e 6 buscas por conta própria |
| **D** | Paper 3b: C2 no corpus de produção | a decidir com o resultado | Paper 3: C2 contra C0 na janela cheia, +24,8 a +27,3 pp entre juízes nas 242; H4 (manuscrito v1.1, §6.7): comitê de 4 juízes −5,8 pp [−10,4, −1,2] contra a evidência crua | estimando: C0 contra C2 nas MESMAS sessões, pareado; começa por replay offline de sessões congeladas, sem deploy; shadow vivo só se a pergunta exigir custo ou deriva em produção |

**Ordem.**
1. **Base comum:** resolver a exposição de privacidade, montar o manifesto de proveniência, definir
   os estimandos.
2. **A**, com holdout novo e a faixa de nDCG apresentada como sensibilidade ao protocolo.
3. **C**, estreita e datada.
4. **B**, depois de C: a leitura de «grafo de contrato» depende de qual consumidor existe, e o único
   consumidor medido (23/10) era uma tarefa sobre contratos.
5. **D**, em paralelo desde já, mas só como replay offline até haver protocolo escrito.

## Objetivo (2026-11-07): B2 e E

Motivação: o post da Anthropic «The components of agent memory» (06/11) afirma, com uma corrida
por braço e 24–25 perguntas, que um passe offline contra a fonte («dreaming») corrige notas, e
que regra fixa sobre o que escrever ajuda modelo fraco e atrapalha modelo forte (registrar só
falhas: −0,234 do ganho no Opus 5). Nenhuma das duas afirmações vem com controle ou intervalo.
Temos a infraestrutura para medir as duas com pré-registro.

| | objeto | formato | base que já existe | o que falta |
|---|---|---|---|---|
| **B2** | Passe de reparo do KG contra o trecho de evidência: manter, reescrever ou apagar cada relação | nota, rota Zenodo | as 300 relações congeladas do B (`FREEZE-COMMITMENT.json`, semente 3335023133), os dois juízes, o conferidor de citação e a nota humana | pré-registro com tag ANTES do `b-read.py` do B; reparador Claude Opus 5.5 (família distinta dos dois juízes); medidas: B_F depois × antes, pareado, e perda (relações sustentadas que o reparo apagou); controle positivo com relações sabidamente erradas; nota humana nas reescritas |
| **E** | Critério de escrita × força do extrator | paper, rota Zenodo | Paper 3 v1.3: C2 contra C0 +24,8 a +27,3 pp, sempre com extrator `gemini-2.5-flash-lite`, que o manuscrito declara como limite; leitor R3 e juízes calibrados | fatorial critério {C0, C2, P "só propósito"} × extrator {`gemini-2.5-flash-lite`, `gemini-2.5-flash` sem raciocínio}, nas 242 do confirmatório do Paper 3 com todas as células refeitas; tag `paper-e-prereg-v1.0` após Codex e Kimi (#703, #704). LIDO 08/11 (`paper-e-extractor/RESULT.md`): controles passam; interação −4,1 pp [−12,3; +4,1], inconclusiva (juiz 2 −5,0); vantagem do C2 com o flash +21,1 pp [+14,8; +27,4]; P bate C0 nos dois extratores (+13 a +17 pp) e fica 3,7 pp abaixo do C2 com o flash; US$ 150,55. Nota após Codex e Kimi (#706, #707, #709) PUBLICADA no Zenodo em 08/11: doi:10.5281/zenodo.24057928 |

O ablation de saliência no ranking ficou de fora: o G7 (20/05) mediu a fórmula v2 ligada contra
desligada, nDCG 0,5845 × 0,5872 (n=100), e `pain` é tópico e degenerado (62.425 chunks em 0,2).

## Objetivo (2026-11-25): corpus sintético PT-BR público

- **Problema:** o Paper A (doi:10.5281/zenodo.24400444) declara o corpus privado e publica só
  contagens, hashes e código; ninguém de fora roda os testes de método. A Pendência 3 prometia um
  corpus pequeno, PT-BR e público para isso, e ficou sem fazer e sem ser declarada fora. Além disso,
  o §3 do A admite que, sem referência independente, a concordância entre juízes «não diz nada sobre
  precisão»: num corpus com gabarito plantado, essa referência existe.
- **Para quem:** quem quiser rodar os testes de método do A, ou aplicar a mesma régua a outro
  sistema de memória.
- **O que a nota afirma, e só isso** (revisto em 25/11 depois de Codex e Kimi): «num corpus público
  construído, com versões fixadas do pacote, estes mecanismos produzem (ou não) estas falhas da
  régua». É uma suíte pública e executável dos mecanismos de falha do §3, **não** uma reprodução
  independente dos achados empíricos, nem medida de qualidade de busca (valores únicos favorecem o
  BM25), nem benchmark não contaminado (é público: fixture aberta de regressão).
- **Entrega mínima (critério de aceite):** dataset no Zenodo (CC BY 4.0, ligado ao A por related
  identifier) com corpus, verdade latente, rótulos observados, scripts e uma nota curta em inglês com
  os resultados da etapa 1; card no labf.bio. Gates do corpus, pós-ingest, do resolvedor, de
  privacidade e de reanálise verdes.

| etapa | testes do A | LLM | custo |
|---|---|---|---|
| **1** | achado 1 como **matriz de operações × duas versões fixadas do `nox-mem`** (antes e depois de nox-supermem#42, 14/10); achado 2 com **verdade latente separada dos rótulos observados**; achado 4 em frequência e magnitude | só para escrever o texto | teto US$ 5 |
| **2** | achados 3 e 5 contra o gabarito plantado, com população, modelos, repetições e regra de parada fixados antes da 1ª chamada (pré-registro próprio) | juízes | teto US$ 20; começa só depois da etapa 1 publicada |

**Desenho da etapa 1.**

- *Achado 1, âncora × id.* Matriz pré-registrada, cada célula com os dois resultados possíveis:
  reingest sem mudança; edição fora do trecho; edição dentro do trecho (o valor muda); renomear com
  reingest; renomear sem reingest; excluir. Cada operação roda contra duas versões fixadas do pacote:
  a **3.5.2** (última com o ingest antigo: `DELETE FROM chunks WHERE source_file = ?` e reinsere o
  arquivo inteiro, conferido no tarball em 25/11; publicada 14/10 03:03 UTC, antes do merge do #42 às
  14:33) e a **3.11.1** (atual, preserva o id do chunk inalterado desde a 3.6.0). Para cada célula e cada referência (id, âncora): alcança o **trecho
  correto**? Publica-se o que sair, inclusive id ganhando de âncora (o H-A2 do A já viu 119 × 117 por
  uma renomeação) e nenhum id mudando no pacote atual. Troca de id injetada por script fica fora: é
  tautologia.
- *Achado 2, rótulo não julgado ≠ erro.* Três conjuntos por query sobre o **mesmo** ranking BM25
  congelado: verdade latente completa (T); rótulos registrados (R), obtidos de T por mascaramento
  mecânico com semente fixado antes de rodar o BM25; e pooled (P) = R mais os positivos de T no
  top-10. Publicam-se nDCG@10 em T, R e P e quantas queries sobem, empatam e caem. Controle de
  encanamento: zerar só as adições de P faz P coincidir com R (substitui o «inverter todos os
  rótulos», que pode virar negativo em positivo).
- *Achado 4, ideal.* A direção é matemática (ganho binário, mesmo numerador). Fixtures calculadas à
  mão antes: 1 relevante no topo e 4 ausentes; todos recuperados; nenhum recuperado; query sem
  resposta (regra explícita para ideal zero). Nas queries do corpus, mede-se só com que frequência e
  por quanto a escolha do ideal muda o escore, inclusive zero.
- *Matriz de cobertura das ~50 queries, fixada antes da geração:* quantas com vários relevantes, com
  positivo parafraseado (forma alternativa do valor: «duas semanas» × «14 dias», «25/11» × «25 de
  novembro»), com valor em contexto que **não** responde (negado, proposta rejeitada, outra entidade),
  com duplicata exata, com par de entidade, com premissa falsa, e alvo de cada operação da matriz.

**Corpus.** Pasta `synthetic-ptbr/`. Uma equipe fictícia de agentes de uma editora independente,
~200 arquivos nas formas do corpus real (notas diárias, decisões, lições, arquivos de entidade com
frontmatter/compiled/timeline). Um script com semente planeja arquivos, fatos, variantes e
negativos; o Claude escreve cada arquivo em volta das frases que lhe são dadas e é instruído a não
restatar os fatos; positivos parafraseados, negativos de contexto, duplicatas e cópias são escritos
pelo script, não pelo modelo. Ingestão pelo pacote `nox-mem` fixado, num banco isolado (`NOX_DB_PATH`
e `GOLD_DB` explícitos); ranker BM25 (`--no-hybrid`). O texto gerado não é reproduzível; o corpus
congelado é o artefato, e prompt, semente, id do modelo e custo ficam registrados. Paráfrase
espontânea do gerador que nenhum gate textual pega fica declarada como hipótese auditada por amostra
cega (leitura de pares fora das frases plantadas), não como completude.

**Geração isolada (privacidade antes da chamada externa).** `claude -p` roda num diretório vazio do
scratchpad, sem ferramentas, sem `CLAUDE.md` nem configurações herdadas, só com os insumos fictícios
do planejador; o prompt efetivamente enviado de cada arquivo é gravado e publicado. Antes de qualquer
push, o pacote exato de publicação (corpus, prompts, queries, rótulos, rankings, banco) passa pela
comparação local por trechos de 8 palavras contra os backups privados, a mesma técnica da varredura
de 08/11, além do gate de privacidade existente. Infrator: uma frase-canário sem nome, host ou
caminho, plantada numa fixture privada de teste.

**PRs previstos:** (1) PLANO, planejador com semente e matriz de cobertura, gates do corpus,
pós-ingest e do resolvedor com seus infratores, fixtures do achado 4, tudo offline e sem custo;
(2) geração paga isolada, varredura por trechos e corpus congelado; (3) matriz de operações nas duas
versões, T/R/P e resultados; (4) nota, vozes se você pedir, depósito e card.

## Objetivo (2026-11-26): o agente consulta e escreve? (quatro estudos)

Pedido do Toto em 26/11: «evoluir 10 a 13». Os papers publicados medem a **construção** da memória;
o que está aberto é o **uso**: o agente busca sozinho, e grava? Hoje a evidência diz que não
(nenhuma busca de agente da VPS até 21/10; T2 no Claude Code: +0,46 na avaliação, 2 de 38 sessões no campo;
escrita 0 de 30 em todos os braços). Ordem proposta: o 12 e o 11 rodam no harness local que já
existe (`~/nox-skill-eval`, fora do repo, com corpus e juiz calibrado, kappa 0,89 com o Toto); o
10 mexe em produção e espera um sim; o 13 só abre depois da delimitação da novidade.

| # | estudo | pergunta | desenho mínimo | custo | decisão pendente do Toto |
|---|---|---|---|---|---|
| 10 | T2 nos agentes do OpenClaw (ROADMAP B3) | O texto T2 com escopo faz os 6 agentes da VPS buscarem no nox-mem? | Pré-registrado. Linha de base medida até 21/10 (0 de 382 buscas eram de agente; 337 eram a sonda canária); remedir antes de ligar. Ligar `NOX_MEM_INSTRUCTIONS` com uma frase de escopo **por agente**, alternando ligado/desligado em blocos de dias (6 agentes são poucos para sortear entre agentes). Desfecho: fração de sessões de agente com ≥1 busca; falso gatilho = busca fora do escopo do agente; 10 buscas lidas à mão. Os transcripts são podados a 7 dias: a coleta precisa de cópia diária antes de começar | tokens do próprio agente; M de trabalho | é produção: ligar instruções nos agentes; quem escreve a frase de escopo de cada um |
| 11 | Escopo derivado do banco (ROADMAP B2) | Uma frase de escopo gerada a partir do próprio banco funciona tão bem quanto a escrita à mão? | Função determinística que monta a frase das fontes e entidades mais frequentes do banco; braços T2-mão × T2-derivado × S0 nas tarefas K e G do harness; dois modelos e dois clientes (Claude Code e Codex CLI; Cursor se der para automatizar). Critério igual ao do T2: ganho em K e falso gatilho em G ≤ 15 pp | US$ 100–300 | teto de gasto; quais clientes |
| 12 | Escrita (ROADMAP B4) | Existe uma condição em que o agente grava uma decisão quando a tarefa pede? | Três braços novos contra o T2: (a) o resultado da busca, quando não acha nada, sugere registrar; (b) hook de fim de sessão que propõe o `decision_set` com o texto pronto; (c) ferramenta de escrita citada nas `instructions` com o critério de quando gravar. Desfecho W+ (grava quando devia, 30 tarefas por braço) e W− (grava sem motivo, nas tarefas G). Para cedo: um braço com W+ ≥ 10 de 30 e W− ≤ 15 pp responde a pergunta | ~US$ 10–20 por braço (o T2 custou US$ 16 em 180 corridas) | ok para pré-registrar e rodar no harness local |
| 13 | Construção como protocolo (ROADMAP pesquisa 3) | O que um construtor de memória deve escrever, medido pelo que o agente consegue responder depois? | Janela × critério × extrator, com BM25 e evidência crua como controles, juiz calibrado e piso de ruído, num benchmark além do LongMemEval. Antes: delimitar a novidade frente aos trabalhos mais próximos (em andamento em 26/11) | o E custou US$ 150,55; teto a fixar | teto; abrir ou não depois da delimitação |

**Decidido em 26/11, 20h55–21h00 (Toto: «ok 30 fecha, pode seguir com o resto»):**
- 12 e 11 pré-registrados juntos em `use-studies/PREREGISTRATION.md`, tag `use-studies-prereg-v1.0`
  (`62728791`, 26/11 21h07, antes de qualquer corrida do banco). O 11 com teto de US$ 30 em gasto
  real, só a frase derivada, comparada com as corridas de 07/11 no mesmo build (fase 2 no Codex
  CLI só se a fase 1 passar). Corridas disparadas em 26/11 21h08 (W: 240, S: 180).
- 10: a coleta diária já existe (`nox-archive-transcripts.sh`, 4×/dia, 3.424 sessões desde 15/08,
  sem poda); ligar as instruções nos agentes espera o sim do Toto e as frases de escopo por agente.
- 13: não abre agora; volta depois da leitura do shadow do C2 (dezembro), com piloto de até US$ 30
  antes de fixar teto. Delimitação de novidade feita em 26/11 (o mais próximo: Yang et al., nov/2026).
- Paper 1: IP&M pela rota sem taxa, alphaXiv fora por ora; plano em
  `paper/publication/ipm-submission-plan.md` (revisão duplamente anônima, resumo ≤ 250 palavras,
  corte de ~28 mil para ~11 mil palavras, título sem «Pain-Weighted», decidido pelo Toto em 26/11 21h19).
  **27/11 noite:** vozes Codex + Grok (escolha do Toto) sobre o manuscrito contra o S1; todos os achados
  eram frases mais fortes que o relatório, reescritas sem número novo (`ipm/voices/`, checklist).
  **27/11, 20h30:** a sessão encheu antes de montar o S4. O S4 é o código anonimizado em zip, que vai como
  material suplementar. O escopo dele está no item 1 de Left do checklist; montar o S4 é o próximo passo,
  e depois o Toto submete.
  **27/11, 21h:** S4 montado (`ipm/build_s4_code.py`, zip de 4,85 MB; testes do engine iguais ao original,
  verificador 135/135). Falta só o Toto submeter.
  **27/11:** rascunho anônimo em `paper/publication/ipm/manuscript.md` (8.335 palavras, resumo de 249),
  gate de proveniência (212 números, todos na v1.0.6, teste negativo feito), related work 2025–2026
  conferido na API do arXiv. **27/11 tarde:** Toto leu e manteve o nome; related work relido no texto
  dos papers (26 de 31 sustentados, 5 frases ajustadas); Figura 1 redesenhada sem nomes de agentes;
  suplementos S1–S3 anônimos com gate; PDF no LaTeX CAS com gate de números; carta pronta. Falta só o
  link anônimo de código (opcional) e a submissão pelo Toto; ver
  `paper/publication/ipm/SUBMISSION-CHECKLIST.md`. README do `nox-mem` alinhado aos números do
  relatório (nox-mem#71).
- GTM: pricing adiado; antes vem o B1 (onboarding observado).

**Resultado de 12 e 11, 26/11 22h37 (`use-studies/RESULTS.md`):** todos os gates passaram, 0 falha
de conexão em 420 corridas. **12:** o gancho de fim de sessão (WH) grava a decisão em 30 de 30 (W0:
1 de 30), +0,967 [0,900; 1,000], sem gravar nada nas tarefas W−; o lembrete no resultado das tools
(WN) não tem efeito detectável. **11:** a frase derivada (SD) passa na regra do T2: K pass 0,579 contra
0,528 do T2, SD − T2 +0,056 [−0,046; 0,167]; falso gatilho 8 de 60 (T2: 1 de 60), +0,133 contra o
limite de 0,15, todos em três tarefas G de infraestrutura. Comparação não concorrente (corridas de
07/11). Uma leitura mais estrita da trava 4 derruba o 11 só no falso gatilho (sensibilidade no
RESULTS). Gasto real só Gemini, estimado em poucos dólares. A fase 2 (Codex CLI) fica liberada pelo
pré-registro e espera o sim do Toto e um pré-registro próprio.

Gates: os mesmos do eval do T2 (instrumentos, modelo devolvido, conexão), proveniência em toda nota,
e voz só se o Toto pedir. O 10 começa pelo script de coleta diária dos transcripts e pelo
pré-registro; nada liga em produção antes do sim.

## Fora do escopo

- Publicar texto do corpus privado, queries reais, nomes de arquivo do corpus ou endereço de host.
- Comparação com outros sistemas de memória (Paper 1).
- C2 ativo em produção; e o shadow vivo do D sem protocolo próprio e sem o seu ok.
- Afirmar «não uso» comportamental no C sem uma corrida com controle positivo válido.
- arXiv, salvo pedido seu.
- Corpus sintético: condicionar a geração em qualquer trecho do corpus privado; rodar o pipeline
  H-A1 nele (o H-A1 é afirmação sobre o sistema de produção, não sobre a régua).

## Intake

| Pergunta | Resposta |
|---|---|
| Tipo | pesquisa |
| Onde nasce | repo existente |
| Repo e caminho | `totobusnello/memoria-nox` (PÚBLICO) · `~/Claude/Projetos/memoria-nox`, uma pasta por paper (`paper-a-eval-ptbr/`, `datanote-kg/`, `datanote-pushed-memory/`, `paper3b-production/`) |
| Gerenciador | nenhum na raiz; Python 3 stdlib (`python3 -I`) e Node do nox-mem |
| Toca produção/cliente | `sim`, só pelo D, e só se o shadow vivo for aprovado; o replay offline não toca |
| Threat model | `não` para propriedade intelectual. Os riscos reais são **privacidade do corpus** (repo público, juiz externo) e **interferência em produção** (D), tratados como gates bloqueantes |
| O que sai | A: paper com números; B e C: notas descritivas; D: a decidir com o resultado |
| Ferramenta | Python e SQLite sobre backup `daily-main` descomprimido ou cópia `VACUUM INTO`; juiz pela Decisions API |
| Rota de publicação | Zenodo (scripts no padrão do Paper 3, publicação manual sua) + card no labf.bio com preview antes do merge |

## Gates

Cada um fica pronto quando passa no estado válido e reprova o infrator da coluna. Proveniência e
privacidade provados em 2026-11-04: os 12 testes passam com os gates intactos e os 12 casos de
infrator falham com os gates sabotados para sempre sair 0 (teste de mutação). Os outros se provam
no Setup de cada paper.

| Gate | Comando | rc esperado | Quando | Teste negativo: infrator | rc observado | Data |
|---|---|---|---|---|---|---|
| Proveniência | `python3 -I tools/provenance.py --check <pasta>`: cada número do texto tem entrada (afirmação, população, data, artefato, commit, `superseded_by`); falha se a fonte foi superada ou não existe | 0 | todo PR | citar 0,833 com `superseded_by`; número sem entrada; locator ausente; commit inexistente (`tools/tests/test_gates.py`) | 1 nos quatro | 2026-11-04 |
| Paridade | `python3 -I <pasta>/numbers.py --check`: recomputa cada número a partir de contagens | 0 | todo PR | trocar um número do texto | | |
| Privacidade antes do commit | `python3 -I tools/privacy-gate.py --staged`, chamado por `tools/hooks/pre-commit` (o hook global delega): linhas adicionadas de texto e blobs binários inteiros (PDF, membros de zip); arquivo concreto do cofre, do log de eventos do Mac ou de entidade de pessoa, host `srv`+6 dígitos, prefixo da tailnet, e 180 termos privados por hash (lista local, fora do repo) | 0 | todo commit, hook | um infrator de cada classe, cada um num repositório novo, mais zip e escape sem motivo (`tools/tests/test_gates.py`); e o JSON do KG que vazou: 116 bloqueios | 1 em todos | 2026-11-04 |
| Exportação por lista | os artefatos públicos saem só por `export.py`, com lista explícita de campos permitidos e ids aleatórios (nunca hash de query) | 0 | todo PR | acrescentar um campo de texto ao registro exportado | | |
| PDF | build + `check-layout.py`, zero glifos faltando | 0 | todo PR | inserir δ na fonte | | |
| Reanálise sem chave | `<runner>.py --analyze` reproduz o `.txt`; checksum de cada artefato no manifesto | 0 | todo PR | editar uma linha que muda o resultado | | |
| A: âncoras | `GOLD_DB=<snapshot> python3 -I eval/resolve-gold-anchors.py <arquivo>` (o script lê o banco de `GOLD_DB` e o gold do 1º argumento posicional; corrigido em 25/11, a linha antiga dizia `--db`/`--gold`), contagem não vazia, ambíguas reportadas | 0 | antes da corrida | apontar um gold para trecho inexistente | | |
| S: corpus | `python3 -I synthetic-ptbr/check-corpus.py --corpus <dir>`: arquivos = os do plano; cada item plantado aparece no arquivo e na seção registrados, `count` vezes, e em nenhum outro; toda forma de todo valor só dentro de item daquele valor; **nenhum dígito no texto livre** (só em item, frontmatter, título e data da timeline); nenhum par de valores colide | 0 | todo PR do S | 9 infratores em `test-synthetic.py` (frase tirada; valor em arquivo não rotulado; variante por extenso fora de T; valor de negativo em outro arquivo; duplicata desfeita; dígito solto; item de entidade fora da seção; arquivo a mais; arquivo a menos) e 4 sabotagens do gate | 1 nos 9; teste reprova as 4 sabotagens | 2026-11-25 |
| S: pós-ingest | `python3 -I synthetic-ptbr/check-ingest.py --db <banco isolado>`: todo item plantado inteiro em chunk (count 1 → 1 chunk; primária duplicada → 2 chunks byte a byte iguais); arquivo de operação com 2+ chunks e o fato num só; negativo nunca no chunk de um positivo do mesmo fato; chunks só de arquivos do plano | 0 | todo PR do S, a partir do (3) | 6 infratores na parte F do teste (frase cortada, duplicata fundida, duplicata diferente, arquivo de operação com 1 chunk, negativo com positivo, arquivo fora do plano) | 1 nos 6; nas duas versões do pacote: 851 chunks, ok | 2026-11-25 |
| S: resolvedor | contrato rodado de verdade (`GOLD_DB=<fixture>`, parte C de `test-synthetic.py`): duplicata exata → `ambiguous_duplicate`, os dois ids, rc 0; par frontmatter+compiled → aceito, rc 0; dois textos distintos com o mesmo trecho → `ambiguous`, rc 1; renomeado sem reingest → `unresolved`; com o prefixo default de 160 uma conclusão trocada ainda resolve (risco documentado), com `ANCHOR_PREFIX=100000` não resolve | conforme cada caso | todo PR do S | cada caso com o estado esperado trocado | 9 casos conforme | 2026-11-25 |
| S: achado 4 | `python3 -I synthetic-ptbr/metrics.py --fixtures`: 5 fixtures calculadas à mão (1 no topo + 4 ausentes; todos recuperados; nenhum recuperado; sem resposta; 1 de 1 na posição 2) × 2 ideais, mais o controle do pooled | 0 | todo PR do S | ideal do ranking no lugar do gold; ideal zero contado como 1 | 1 nos dois | 2026-11-25 |
| S: reanálise | `python3 -I synthetic-ptbr/method-tests.py --analyze --check`: `results/etapa1.txt` é o que os artefatos congelados dão, sem rede. A reconstrução a partir dos Markdown é o próprio `--run` (instala as versões fixadas, ingere, busca, opera) | 0 | todo PR do S, a partir do (3) | uma linha de ranking congelado trocada (parte F do teste) | 1 | 2026-11-25 |
| S: remontagem | `python3 -I synthetic-ptbr/generate.py --reassemble --check --out synthetic-ptbr/corpus --raw synthetic-ptbr/generation`: o corpus commitado é exatamente a remontagem dos registros de geração, sem chamada ao modelo | 0 | todo PR do S, a partir do (3) | um arquivo do corpus editado à mão | 1 | 2026-11-25 |
| S: plano fixo | `python3 -I synthetic-ptbr/plan.py --check`: o plano regenerado pela semente é byte a byte o commitado | 0 | todo PR do S | outra semente; plano com arquivo de operação compartilhado; premissa falsa plantada | 1 nos três | 2026-11-25 |
| S: privacidade do pacote | `python3 -I synthetic-ptbr/privacy-scan.py --package synthetic-ptbr --db <banco vivo>`, rodado NA VPS de produção (só o pacote público sobe; banco em `mode=ro`; nada privado é impresso): nenhum trecho de 8 palavras do pacote existe num chunk privado. Referência = o corpus privado inteiro, não os backups (os de 04/11 e 08/11 não existem mais, ver Pendências) | 0 | antes de todo push do (2) em diante | offline: frase-canário num banco de fixture (pega, sem texto privado no relatório); banco inexistente e banco vazio dão erro, nunca «limpo». Na VPS: um chunk privado sorteado plantado numa cópia do pacote | offline 1 e 2; VPS: pacote real 0 trechos em 74.742 × 65.206 chunks, controle positivo rc 1 com 90 trechos | 2026-11-25 |
| D: não interferência | replay offline: roda C0 e C2 sobre banco de fixture e confere que nenhuma tabela, arquivo ou fila fora do diretório de saída mudou (hash antes e depois) | 0 | todo PR do D | fazer o C2 gravar em qualquer tabela do banco | | |

## Verificações manuais

| Verificação | Quem confere | Evidência | Última vez (data, PR) |
|---|---|---|---|
| Passe avoid-ai-writing antes das vozes e antes do depósito | Claude | diff no PR | 2026-11-25, PR (4): nota do corpus sintético (negrito, 2 negações-contraste, 1 intensificador; números iguais antes e depois). 2026-11-25 12h, 2º passe na nota revista, a pedido do Toto («ja passa ai writing e vozes?»): 3 negações-contraste, 1 «exactly», 1 frase vaga no resumo; números iguais. 2026-11-26, nota v1.1 (texto novo da etapa 2), a pedido do Toto («passamos qi writing e o vozes?»): o passe NÃO tinha rodado antes das vozes desta rodada; feito depois delas e antes do depósito: 6 rótulos em negrito da §5 viraram subtítulos `###` (o estilo da §4), 1 contraste de auxiliar solto reescrito («the decoys found 12»), 1 antropomorfismo no resumo («tempted»); números iguais, mais um «12» que já estava no texto |
| Precedência do pré-registro (A, D): push da tag antes da 1ª chamada, e queries do holdout nunca vistas antes | Claude, pelo activity log do GitHub | horários no texto | |
| Amostra humana cega dos pares discordantes (A) | você ou alguém que você indicar | planilha de rótulos fora do repo, só o kappa publicado | |
| O que vai para a Decisions API e onde ficam prompts e respostas | Claude, por escrito no protocolo | seção de dados do protocolo | |
| Preview do card no labf.bio | você | URL do preview | |
| Publicação no Zenodo | você | DOI público + `--readback` | |
| Corpus sintético: leitura de 10 arquivos sorteados (PT-BR natural, nenhum nome real) e leitura cega de pares fora das frases plantadas (paráfrase espontânea do gerador) | Claude sorteia e lê; você confere 3. Não substitui o gate de privacidade do pacote, que é o que cobre o corpus privado | lista dos sorteados e veredito no PR (2) | 2026-11-25, PR (2): 10 lidos pelo Claude (semente `leitura-amostra-2026-11-25`), aprovados com 4 marcas declaradas no README; busca de número por extenso no texto livre: 0. Os 3 do Toto lidos em 25/11 10:32 («li os 3, pode fazer o merge») |
| Shadow vivo do D, se houver | você aprova; Claude executa com limite de custo, de tempo e desligamento rápido | log do shadow e `/api/health` | |

## Etapa atual

**Corpus sintético, etapa 2: ENCERRADA.** v1.1 publicada pelo Toto em 26/11, doi:10.5281/zenodo.24570881 (concept 24535847, versão anterior 24535848), software `7ba30a12` (#759), nota `c66f2311` (#758). Varredura de privacidade no host antes do fill: 14 trechos em comum, todos sem conteúdo (índices do `pairs.json` e «não» repetido). Readback sem divergência. Card labf.bio atualizado (site-labf#79, squash `f44cea91`, preview aprovado pelo Toto antes do merge). Worktrees da etapa 2 fechadas. Pendente, sem prazo: checagem de commit-na-main no `tools/provenance.py`. Histórico da etapa abaixo. Antes, PR (8) = corridas e resultados. Cronologia: tag `synthetic-ptbr-stage2-prereg` em `c7001146` (25/11 ~17:20, «Tag agora», sem 2ª rodada de vozes); anotações cegas do Toto commitadas antes de qualquer chamada (#753, 29 C, 1 P, 15 D, 37 M, 18 F, nenhum «?»); corridas em 25/11 20:30–20:46 UTC; parada no J-pool por 329/555 ausentes → emenda 1 (#754: `null` na citação de um «não» é string vazia, como na fonte; reparse sem chamada nova; 172 chamadas da rerodagem interrompida ficam no ledger) → J-pool 1/555 ausente, sem rerodagem. Ledger total US$ 0,20. `analyze.py` rodado; resultados em `synthetic-ptbr/stage2/results/stage2.txt`, `analyze.py --check` no `guarda-lastro`. Números do analisador (sem interpretação ainda): leitura do Toto discorda de T em 1/100 (ponderado 0,0053); recall 1,0 em todos os juízes contra T (J-gold 88/89); precisão contra T: oráculo 0,6096, pool 0,8318, reg 0,8641, envelope 0,89, gold 0,88; J-gold aceita 12/15 golds errados (valor rejeitado/superado), 0/50 aleatórios, 59/59 corretos; perna de citação tira 1 par, kappa com J-reg 0,906 → 0,9115 (P2 não visto); J-reg × J-reg-2 0 mudanças, × envelope 9/555. Próximo: PR (9), seção da etapa 2 na nota (v1.1), avoid-ai-writing, vozes se o Toto pedir, depósito como nova versão, card. Worktree desta fase (`synthetic-ptbr-stage2-runs`) fechada em 26/11.

Antes (Plan, 25/11): pré-registro revisto depois de Codex + Kimi (ambos «não congelar»; seção Vozes) e scripts escritos: `pairs.py`/`pairs.json`, folha cega `human/SHEET.md` (100 pares), `prompts.py` (extraídos das fontes por código), `judges.py`, `run.py` (ledger, teto, retries), `analyze.py`, fixtures de citação, `test-stage2.py` (todos passam; sabotagem pega 12) e passo no `guarda-lastro`. Próximo: PR (7) mergeado → o Toto lê a folha e preenche `human/annotations.tsv` → commit das anotações → tag → smoke → corridas. PRs previstos: (7) pré-registro + `pairs.py`/`pairs.json` + `judges.py` + runner com ledger + testes offline, depois tag `synthetic-ptbr-stage2-prereg`; (8) corridas, folha cega das lacunas de T e resultados; (9) nota v1.1, vozes se o Toto pedir, depósito como nova versão e card atualizado. Worktree: `~/Claude-worktrees/memoria-nox/synthetic-ptbr-stage2-prereg`. Card da etapa 1 no ar em 25/11 (site-labf#77, `da9aa170`).

**Corpus sintético (objetivo de 25/11):** etapa 1 **publicada** pelo Toto em 25/11, doi:10.5281/zenodo.24535848 (concept doi:10.5281/zenodo.24535847), v1.0, software link `70c82859`; md5 dos 4 arquivos do registro iguais aos do build local, DOI e link do código respondem 200. Antes da publicação: rascunho refeito do commit final `70c82859`, varredura de privacidade do arquivo final contra o banco vivo (104.132 trechos × 65.212 chunks, 0 em comum), readback sem divergência, zip descompactado passa nos 42 testes e no `--analyze --check`. Card no labf.bio no ar em 25/11 (site-labf#77), preview aprovado pelo Toto antes do merge. Antes, 2ª rodada de vozes aplicada (PR #749). Antes, PR (6) #746: pacote de depósito (status na nota, build do PDF,
`deposit/deposit-note.py`, descrição). Toto aprovou a nota em 25/11 11:48 («otima nota segue»). Depois do merge:
rascunho no Zenodo pelo commit da `main`, build, fill, readback; o Toto publica; card no labf.bio.
PR (5) #744: nota revista depois das vozes Codex + Kimi
(seção Vozes), ~2.650 palavras, proveniência 12 afirmações / 0 falhas; analisador corrigido (média
sem arredondamento duplo, rc do resolvedor); só `mean_strict` mudou (0,7542 → 0,7543). Próximo: o Toto
lê a nota; depois pacote de depósito (o Toto publica) e card no labf.bio (preview antes do merge).
PR (4) #743 (rascunho) mergeado em 25/11 (`4196290`). PR (3) #742 mergeado em 25/11 (`1fde4c1`).
Antes: PRs (1) #740 e (2) #741 mergeados em 25/11.
PR (3): corpus em seções `##` (remontado dos registros, sem chamada nova), gate pós-ingest, runner da
etapa 1 commitado antes de rodar (`88b1f02`, 10:39), corrida nas versões 3.5.2 e 3.11.1 e análise.
Resultado (`synthetic-ptbr/results/etapa1.txt`): achado 1 — reingest e edição fora do trecho matam o
id na 3.5.2 (5/5) e o preservam na 3.11.1 (5/5); renomear com reingest deixa o id vivo e a âncora
sem resolver na 3.11.1 (5/5), e as duas referências presas no resto do caminho velho na 3.5.2;
excluir deixa as duas referências «stale» nas duas versões (o chunk fica, com ou sem tombstone).
Achado 2 — nenhuma query com strict zero (o mecanismo do §3 não aparece neste corpus); strict
erra a verdade nos dois sentidos (12 acima, 8 abaixo); pooled nunca abaixo da verdade, por
aritmética, e acima em 5 de 45. Achado 4 — o ideal do ranking muda 5 de 45 queries, +0,2033 em média.
Varredura de privacidade de novo: 0 trechos (99.999 × 65.208). Próximo: PR (4), a nota.
Worktree: `~/Claude-worktrees/memoria-nox/synthetic-ptbr-doi` (registro do DOI). Card: worktree no `site-labf`.

Etapa: Deploy (paper A): **publicado** pelo Toto em 20/11, doi:10.5281/zenodo.24400444 (concept
doi:10.5281/zenodo.24400443), v1.0, software link `baf4b80`, checksums do registro iguais aos do build
Card no labf.bio no ar em 20/11 (site-labf#69, `8924f8b`), preview aprovado pelo Toto antes do merge.
Nota #723 («the memory the agent does not consult»): **publicada** pelo Toto em 20/11, doi:10.5281/zenodo.24408079
(concept doi:10.5281/zenodo.24408078), v1.0, software link `1a793c7`; checksums do registro iguais aos do build.
Card da nota no labf.bio no ar em 20/11 (site-labf#71, `c3e5a29`), preview aprovado pelo Toto antes do merge.
Próximo passo (21/11): fila no topo do HANDOFF; recomendado começar pelo corpus sintético PT-BR público
(Compromissos, item 3), que o Paper A deixou em aberto. Depois: shadow do C2 em 01/12; T2 nos agentes; alphaXiv.
Feito de 18 a 20/11: H-A2 not tested (#724); emenda para 2027-05-18 (#725); H-A2R pré-registrada e
lida, primária sustentada (#726, #727); passe avoid-ai-writing (#728); proveniência de A a E
remapeada para os commits pós-reescrita, com gate que exige ancestralidade e job na CI (#729); duas
rodadas de Codex e Kimi no manuscrito (#730, #731); pacote de depósito e build do PDF (#731, #732);
rascunho criado, preenchido e conferido por `--readback` (0 divergências), com software link em `0b38f08`.
Hashes abaixo são os de antes da reescrita de 08/11 (mapa em `docs/history-rewrite-2026-11-08-commit-map.txt`).
Feito em 05/11: tag `6c6879b` → `HOLDOUT-COMMITMENT.json` `54048e4` → score na VPS → amostra
humana → `HUMAN-COMMITMENT.json` `31d90b2` → leitura (saídas em `6120a37`). H-A1 se sustenta,
+0,1933 [+0,1421, +0,2464]; kappa humano × juiz 0,038, então o pooled não fica validado pelo
avaliador (§4).
Em paralelo desde 05/11 (Toto: «em paralelo os 2»): C, nota de dados em
`paper-c-pushed-memory/NOTE.md` (rascunho, proveniência 16 registros, 0 falhas), e o protocolo do D
(`paper-d-c2-production/`): decisões D1–D9 tomadas, smoke pago de 5 sessões (US$ 0,02), e o
pré-registro em rascunho (`PREREGISTRATION.md`, 05/11; revisto em 06/11 com os scripts). O censo
do enquadramento mostrou 414 sessões alcançadas pelo destilador (126 com unidades, 288 sem nenhuma),
não as 634 do pool do smoke; o censo de 06/11 mostrou que 287 das 288 sem unidade nunca foram
mandadas ao modelo (menos de 3 mensagens quando o destilador as viu), o que restringiu o controle
de fidelidade às sessões que produção destilou. Os scripts (`d-freeze.py`, `d-generate.py`,
`d-run.sh`, `d-human.py`, `d-read.sh`, mais `d-common.py`) estão escritos e passam o teste offline
`d-test.py` (50 verificações, sem rede). Em 06/11 o Toto manteve o enquadramento de 414 e escolheu a
tag sem vozes. Tag `paper-d-prereg-v1.0` publicada em 06/11 01:53 UTC (`5307a6f`); congelamento no
mesmo dia, 03:05 UTC, sobre o snapshot de 06/11: enquadramento 418 (janela até 30/10; o censo de
414 ia até 29/10), 290 sem unidade, 120 sessões copiadas, C0 em produção igual ao do Paper 3;
`FREEZE-COMMITMENT.json` publicado (`edbfda4`). Perguntas escritas em 06/11 com o ok dele («pode
seguir»): 80 sessões, sem extensão, 255 primárias (alvo 232) e 221 secundárias, 162 chamadas ao
glm-5.3; descartes 67 primárias e 16 secundárias (citação não literal é o maior motivo, 48).
`QUESTIONS-COMMITMENT.json` publicado (`07caa54`). Braços rodados em 06/11 com o ok dele («pode
rodar o passo a passo»): US$ 0,73, 2.856 linhas de resposta + 60 contrafactuais, 7 blocos de
destilação sem texto (6 no C2, 3 no C2-cut, 0 no C0; contados, não refeitos, §4). Amostra humana de
60 avaliada por ele às cegas: concordância 0,850, kappa 0,692 com o juiz 1 (o juiz nunca aceitou o
que ele recusou; recusou 9 que ele aceitou). `HUMAN-COMMITMENT.json` publicado (`b0e740b`).
Leitura em 06/11: **falha de instrumento**. Teto, positivo e contrafactual passam; a fidelidade
reprova (P 0,248 × V 0,438 nas 30 sessões que produção mandou ao modelo), então H-D1 e H-D2 não
são interpretados. Diagnóstico (`d-fidelity-diagnosis.py`, posterior ao resultado): produção
descarta a mensagem que começa com `[cron:` (o prompt do job agendado) antes de destilar; o
replay não descarta. Nas 30 sessões, 82% do texto de V é esse prompt (301 mil de 367 mil
caracteres); sem ele, V teria 60 mil contra 66 mil de produção. E 68 das 80 sessões têm o prompt,
com 138 das 255 perguntas primárias citando só ele: o D mediu, em boa parte, memória das
instruções dos crons, que produção não destila por desenho. Censo v1.1 (`ece0727`): sem o prompt,
223 sessões elegíveis fora da amostra, 19 mandadas ao modelo por produção (8,5%). Em 06/11 o Toto
concordou («concordo c vc»): o D fecha como nota (`NOTE.md`, #659) e a cobertura seria trabalho de
produto. Ao preparar essa proposta («pode»), a divisão por semana (#660) desfez o diagnóstico de
cobertura: 118 dos 145 não alcançados terminaram na semana de 23/08, antes da correção do endereço
do destilador em 08/09, um backlog que o cap de 50 deixou sair do lookback; desde 20/09 ele registrou
65 e perdeu 6. Das 47 puladas por < 3 mensagens, 40 têm 2 e são invocações de tarefa por script
(99,2% do texto é prompt): a regra está certa. Nota corrigida (proveniência 35 números, 0 falhas).
Não há mudança de agenda a propor; o único risco é um novo backlog depois de uma pane (remédio
aplicado em 06/11, abaixo).
Em 06/11 à tarde, com o ok do Toto («pode segue e apaga», «faca de 4 a 7»): referências do A
conferidas (#662: Zobel 1998 e Gienapp 2026 reescritos). D: passe final e pacote de depósito
(#663), com uma frase corrigida (falhas por braço: C2 6 blocos, C2-cut 3, C0 0); o destilador roda
em dois lugares, semanal aos domingos e diário no `end-of-day` com lookback de 1 dia, e a nota foi
corrigida (#664, `DISTILLER-SCHEDULE-2026-11-06.json`). Destilador em produção: ordem da mais
antiga para a mais nova e linha de backlog no log (host `db47dae0`); C2 em shadow ao lado dele,
gravando bloco, C0 e C2 num arquivo privado no host, sem tocar o banco (host `ac642951`, protocolo
`paper-d-c2-production/SHADOW-PROTOCOL.md`, ligado em 06/11 17:26 UTC, desliga sozinho em
2027-01-11). Incidente causado por mim no mesmo trabalho: um `git stash` no repo do workspace da
VPS separou os `.sqlite` de quatro agentes do que o gateway tinha aberto; restaurado do inode
antigo, gateway reiniciado com o ok do Toto, `quick_check` ok nos cinco. B começou: censo
estrutural sem LLM (`paper-b-kg/CENSUS-2026-11-06.json`), o grafo não cresce desde julho.
Depósitos em 06/11 16:22: C, «No textual match to a pushed memory brief in agent replies»,
doi:10.5281/zenodo.24017459, e D, doi:10.5281/zenodo.24017487, publicados pelo Toto depois do
avoid-ai-writing (#666) e de vozes Codex e Kimi (1ª rodada, #668) e Codex (2ª rodada, #670). O
ORCID passou a sair nos depósitos (#667), e a sessão site-labf pôs o ORCID nos 14 registros
antigos sem ele e cadastrou 11 trabalhos no Scholar (6 → 17); C e D entram em seguida.
B, 07/11: o Toto escolheu a versão completa (fidelidade); rascunho do pré-registro (#669) revisto
com os scripts `b-freeze`/`b-judge`/`b-human`/`b-read`, testados offline em `b-test.py` (52
verificações, sem sorteio nem chamada paga). Cópia privada do snapshot tirada em 07/11 com sha256
conferido, então o congelamento não depende mais da retenção do host. Decidido pelo Toto
em 07/11: juiz 2 = `gpt-5.6-sol` e marcadores no trecho (~130–150 linhas para graduar); o teto
sobe de US$ 1 para US$ 10 pelo preço do juiz 2; teto e tag aprovados em 07/11 08:22 («pode subir e
taguea»), tag `paper-b-prereg-v1.0`. Em 07/11: congelamento (#676, semente 3335023133), juízes (#679,
660 vereditos, US$ 4,49; desvios 1 e 2 no §10, #677/#678), planilha cega de 173 linhas (#680:
76 divergências, 37 marcadores, 60 sorteadas) em `~/Backups/paper-b-freeze-2026-11-07/`.
Em 07/11 à noite: B lido (#688, B-F 0,913 [0,876; 0,940], controles passam, kappa 0,155). B2: vozes Codex e DeepSeek antes da tag (Codex pediu bloquear; retenção redefinida, universo fixo, fluxo sem reescritas), tag `paper-b2-prereg-v1.0` (#687), reparo pelo `claude -p` (#689, US$ 7,93 a preço de lista), juízes nas 106 reescritas (#690), planilha de 60 (#691), desvio 1 (três trechos vazios no .xlsx, regraduados; #692), notas (#693), leitura (#694): precisão 0,913 → 0,990, retenção estrita 0,650, só filtrando 0,989. Nota do B e do B2 em `paper-b-kg/NOTE.md` (#695); vozes Codex e Kimi na nota a pedido do Toto (Codex: revisões maiores, achados aceitos — filtro dito como comparação de subconjuntos, controle negativo testa o conferidor, kappa só nas linhas em que os juízes concordam, post da Anthropic compara condições, impacto da regraduação; Kimi: aprovado, denominador do §1), sensibilidade da regraduação (#696: precisão depois 0,979 com as primeiras notas), proveniência 42 registros, 0 falhas; avoid-ai-writing nos trechos novos (#698). Publicada no Zenodo em 07/11: doi:10.5281/zenodo.24046282. Estudo do
shadow do C2: rascunho do pré-registro (#673) com o redator GLM sob exceção ao §3 do protocolo e a
regra de parada aprovadas em 07/11; tag posta em 08/11 (`paper-d-shadow-prereg-v1.0`; vale a `-v1.1`,
com a semente). Contagem semanal na VPS (domingo 12:31 UTC, só contagens): 15/11 38 sessões / 165 blocos;
22/11 66 / 313 (meta 100 / 300; blocos já passaram, faltam sessões). Leitura não antes de 01/12 e só com
as duas metas cumpridas; próxima contagem em 29/11.
Último resultado dos gates: 2026-11-25 · S (corpus sintético): `test-synthetic.py` 27 ok, 0 falhas;
sabotagens do `check-corpus` (sempre verde, sem dígito, sem forma, sem contagem) reprovam o teste;
`plan.py --check` ok; `metrics.py --fixtures` ok. 2026-11-07 · `b-test.py` 53 verificações, 0 falhas (mutações no
conferidor, na seleção da planilha e no sorteio reprovam); 2026-11-06 · `d-test.py` 50 verificações, 0 falhas (cada recusa testada
com o infrator correspondente); 2026-11-05 · proveniência do A 197 registros, 89 números, 0 falhas
(mutação: um número trocado no RESULTS reprova)

## Pendências

1. **BLOQUEANTE: há dados do corpus privado no repo público.** Conferido em 04/11:
   `audits/out/kg-s1-precision-2026-10-22.json` (desde `abf46ee`, 22/10) tem as 150 triplas da
   amostra, com nomes de entidades, citações literais e 112 caminhos para 82 documentos do cofre
   jurídico. `eval/golden-queries-v2.jsonl` (e v1, v3) tem as 66 queries com trechos literais do
   corpus e caminhos. **Feito em 04/11 (sua escolha «Tirar do main já»): PR #636, merge `379d64e`**,
   8 arquivos fora do `main`, no `.gitignore`, de volta ao disco local e com backup verificado em
   `~/Backups/memoria-nox-privado-2026-11-04/`. O v1 do golden set ficou (pré-registro do Paper 1).
   **Em aberto:** o histórico ainda os contém (reescrever é decisão sua), e o texto dos `audits/*.md`
   não foi varrido: isso é trabalho do gate de privacidade da base comum.
   **Achado no censo do gate (04/11):** o repo cita arquivos concretos de entidades de pessoas
   (`memory/entities/people/<slug>`, 76 menções) e, em 10 arquivos, caminhos concretos do cofre,
   do log de eventos do Mac ou nomes de host. O gate impede menções novas; as existentes ficam
   para a mesma decisão do histórico.
   **Varredura de 08/11** (todo o histórico, os 712 PRs por clone espelho, e as 174 versões de
   arquivo dos 13 registros de memória no Zenodo, contra o backup de 04/11 por trechos de 8 palavras
   e contra os padrões do gate; controle positivo passa, inclusive dentro de zip): Zenodo limpo,
   0 forks, os refs de PR não trazem nada além do histórico do `main`. Achado no `main`: 6 audits de
   26-27/10 com âncoras literais do corpus, respostas do sistema e caminhos privados, que o gate não
   via (procura caminho e nome, não texto). **Feito em 08/11 (sua escolha «tira»): PR #713**, os 6
   fora do `main`, no `.gitignore`, backup em `~/Backups/memoria-nox-privado-2026-11-08/`; os 22
   registros do Paper A que os citam viraram `artifact_private` com o sha256 do arquivo no commit.
   Ficam no `main`, de baixa sensibilidade: nomes de arquivos de notas diárias (E10, maio), texto
   das perguntas, 26 IPs da tailnet num plano de 14/10 e nomes de host. Reescrever o histórico
   troca o hash dos commits citados pelos pré-registros e pelos links `tree/<hash>` dos papers, e
   não apaga os refs de PR sem pedido ao suporte do GitHub.
   **Decidido em 26/11 (Toto: «nao ligo deixa como esta»):** o histórico e as menções antigas de
   baixa sensibilidade ficam como estão; o gate de privacidade continua barrando menção nova.
2. **A: holdout.** Escrever queries novas antes de ver qualquer ranking delas; sem isso a parte nova
   se chama «remedição de estabilidade», não confirmação.
3. **A: corpus sintético.** Pequeno, PT-BR, público, só para os testes de método. Os números de
   produção ficam como estudo de caso agregado. **Aberto como objetivo próprio em 25/11** (seção
   «Objetivo (2026-11-25)»).
4. **D: o `session-distill.ts` vive só na VPS.** Trazer o runner para um artefato versionado antes
   de qualquer experimento. **Feito em 26/11 (Toto: «8 - faz»):** a versão de produção já estava
   versionada no repo privado do workspace (`9ec24c39`, sem mudança pendente) e a versão
   generalizada no pacote público `nox-mem` (`e4035e5`); a cópia fixa da de produção e do shadow
   do C2, com sha256 e as quatro mudanças posteriores ao shadow (nenhuma no prompt), está em
   `paper-d-c2-production/distiller-snapshot/` (#762).
5. **Item 2 (GTM Phase 2):** memo separado; inclui tirar «retenção» da fala. A parte da «retenção»
   já saiu do discurso em 08/11 (ROADMAP A3(a)); o resto coincide com o B8 do ROADMAP.
6. **Backups privados sumiram (achado de 25/11).** `~/Backups/memoria-nox-privado-2026-11-04/` e
   `-2026-11-08/`, citados no item 1 como «backup verificado», não existem mais em lugar nenhum da
   home. Os arquivos privados retirados do repo (golden v2/v3, KG S1, os 6 audits de 27/10) existem
   hoje numa cópia só: ignorados dentro do clone, onde um `git clean -X` os apagaria. Refazer o
   backup é decisão do Toto (onde guardar, com hash). **Feito em 26/11 (Toto: «pode fazer o 3»):**
   os 13 arquivos ignorados (6 audits de 22 e 27/10, 3 saídas de `audits/out/`, golden queries
   v2/v3 e negatives v1/v2) em duas cópias com `SHA256SUMS`: `~/Backups/memoria-nox-privado-2026-11-26/`
   no Mac e `/var/backups/nox-mem/memoria-nox-privado-2026-11-26/` na VPS Pesquisa, os 13 hashes
   conferidos no destino, permissões só do dono.

## Decisões

| Data | Decisão | Por quê |
|---|---|---|
| 2026-11-04 | Os quatro papers, A primeiro | sua escolha na ideação |
| 2026-11-04 | B e C como notas descritivas | as vozes mostraram que nenhum dos dois sustenta afirmação mais forte com o que existe |
| 2026-11-04 | C passa a afirmar ausência de traço textual, datada; não «não uso» | 7a e R1 medem texto; 7b falhou o controle e teve sinal em 3/28; em 23/10 houve busca de agente |
| 2026-11-04 | Faixa de nDCG do A = v3 [0,2567 · 0,4394], descrita como sensibilidade ao protocolo de anotação | o plano anterior misturava piso da v2 com teto de outra versão, e nenhum dos dois é limite demonstrado |
| 2026-11-04 | D começa por replay offline pareado C0 × C2 | não toca produção e responde a mesma pergunta sobre o que a destilação produz |
| 2026-11-05 | D: só C0 × C2 (sem C1, sem C0 como construído); amostra humana cega de 60 obrigatória; pré-registro com tag antes do sorteio das sessões | escolha do Toto; o resultado decide a segunda onda do GTM, e o kappa 0,038 do A mostrou que juiz LLM sozinho não basta |
| 2026-11-05 | D: perguntas pelo critério do C0 (classes do C2 como secundário), redator glm-5.3; congela na data da tag, sessões de 15/08 a tag − 7 dias; leitor de produção; limiares teto ≥ 0,70, positivo ≤ 0,10, contrafactual ≤ 10%, fidelidade ±5 pp; smoke pago < US$ 1 | aprovação em bloco do Toto |
| 2026-11-05 | D: 80 sessões (D4); teto do braço A lido sob o juiz 1, como no Paper 3 (D7) | smoke de 5 sessões: discordância C0 × C2 de 2 em 17, teto 0,765 no juiz 1 e 0,529 no juiz 2; escolha do Toto |
| 2026-11-04 | Zenodo + labf.bio | precedente dos Papers 1–3 |
| 2026-11-06 | D: enquadramento fica nas 414 sessões registradas pelo destilador; as 127 que produção mandou ao modelo saem como descrição | Toto: «vamos seguir suas recomendacoes»; C0 e C2 leem a sessão inteira, então o contraste vale para as 287 que produção pulou, e restringir faria o sorteio de 80 consumir quase todas as 127 |
| 2026-11-07 | Abrir B2 (reparo do KG) e E (critério × extrator) | Toto: «o ponto 3 pode virar um paper interessante! e vamos seguir sua recomendacao», depois do post da Anthropic de 06/11 |
| 2026-11-07 | E = fatorial critério × extrator, não ablation de saliência no ranking | escolha do Toto; o G7 já mediu a saliência no ranking como neutra, e a regra fixa que move o resultado no nosso sistema é o critério de escrita |
| 2026-11-07 | B2: reparador Claude Opus 5.5 | escolha do Toto; família distinta dos dois juízes do B, e é o «dreaming» como o post o descreve |
| 2026-11-07 | B2 pré-registrado com tag antes do `b-read.py` do B | escolha do Toto; o desenho do reparo não pode conhecer o resultado do B. Atrasa a leitura do B em um a dois dias |
| 2026-11-25 | Abrir o corpus sintético PT-BR público (Pendência 3) | Toto: «segue vamos comecar», depois da fila recomendada |
| 2026-11-25 | Etapa 1 = âncora × id + strict × pooled + ideal; etapa 2 = juiz contra gabarito plantado (teto US$ 20); H-A1 fora | Toto: «Fechar assim»; a etapa 1 é determinística e de custo ~zero, a 2 dá ao juiz a referência independente que o A não teve |
| 2026-11-25 | Texto por LLM (Claude via `claude -p`), memória fictícia; ~200 arquivos, ~50 queries; CC BY 4.0; dataset + nota curta; Zenodo + card | escolhas do Toto em 25/11. Descartados: Wikipédia PT (forma não é de memória; BY-SA obrigatória), templates (texto artificial), 50 ou 1.000 arquivos |
| 2026-11-25 | Ranker BM25; fatos com valor inventado e único; domínio fictício = editora independente | do Claude, para o Toto revisar: a etapa mede a régua, não o sistema, e assim a reanálise não precisa de chave; valor único torna «o chunk responde» um teste exato de texto; o domínio não encosta em negócio do Toto |
| 2026-11-25 | Corpus sintético reenquadrado: suíte pública dos mecanismos de falha, não reprodução; achado 1 como matriz de operações × duas versões do pacote; achado 2 com T/R/P; achado 4 em frequência e magnitude; geração isolada e varredura por trechos antes do push | Codex e Kimi, independentes, convergiram: o desenho de 09:24 tirava o resultado da construção (troca de id injetada; rótulos completos por construção; ideal com direção matemática) e contradizia o resolvedor (duplicata exata é aceita, não recusada) |
| 2026-11-25 | Gerador = `claude -p` pela assinatura, isolado; o e-mail da conta entra no contexto e fica, com gate | Toto: «Aceitar com gate». Sondado em 25/11: sem CLAUDE.md, brief, memória ou MCP com `--setting-sources "" --tools "" --strict-mcp-config` e system prompt próprio; o bloco do e-mail não sai com flag nenhuma, e com HOME vazio o CLI perde o login; não há chave de API guardada |
| 2026-11-25 | Corpus mantido apesar de 4 marcas de estilo (bordão «semana seguinte» em 181/200, que veio do exemplo do meu prompt; 3 ecos do prompt; 12 títulos repetidos; primeiros nomes inventados) | do Claude, para o Toto revisar: nenhuma toca os testes de método; regerar custaria ~US$ 2 e outra varredura |
| 2026-11-25 | Corpus remontado em seções `##`, sem regerar | medido na 1ª ingestão: o `chunkMarkdown` (igual nas duas versões, salvo um teto de tamanho na 3.11.1) só divide em `##`/`###`, e os arquivos sem subtítulo viravam 1 chunk cada; editar fora do trecho mudaria o chunk do fato e o achado 1 sairia como artefato. O texto do modelo estava nos registros, então o conserto foi no montador |
| 2026-11-25 | Etapa 2 depois das vozes: leitura de citação limitada a este corpus + fixtures offline dos formatos do A; T validado por amostra humana cega de 100 pares (30 T+, 15 negativos de contexto, 10 de premissa falsa, 45 outros), lida só pelo Toto e commitada antes da 1ª chamada | Toto, 25/11 ~17:10, escolheu as duas opções recomendadas depois de Codex e Kimi mostrarem que o corpus não exercita a falha de citação do A e que T é chave de evidência, não verdade semântica |
| 2026-11-25 | Etapa 2: juízes do A (oráculo `gemini-2.5-flash-lite` que cita + `gpt-6-luna` Decisions), escopo achados 3 e 5 + estabilidade, entrega como v1.1 do mesmo registro (concept 24535847) | Toto, 25/11 ~15:35, escolheu as três opções recomendadas; os dois modelos conferidos como servidos na listagem (custo zero). O prompt de checagem de premissa do A nunca foi commitado: entra reconstruído e declarado |
| 2026-11-06 | D: tag `paper-d-prereg-v1.0` sem revisão adversarial antes | Toto escolheu «Tag hoje, sem vozes»; o pré-registro registra a ausência de revisão (§10) |

## Vozes

| Data | Ponto | Vozes | Recibo / parecer | O que mudou |
|---|---|---|---|---|
| 2026-11-04 | fim do Plan, challenge | Codex gpt-6-astra (130 s), Kimi k3.1-pro (618 s) | recibos `adversary-receipt-codex-2026-11-04T215237-1793.txt` e `adversary-receipt-kimi-2026-11-04T215241-2301.txt`, `exit 0`, cwd do clone | todos os achados conferidos nos audits e confirmados, menos um: o «−5,8 pp é o contraste errado», das duas, vem de lerem o manuscrito v1.0 do `main`; −5,8 é o comitê da v1.5. Mudaram a tabela inteira de números, a ordem, o recorte de C, o desenho de D e os gates (proveniência, privacidade antes do push, exportação por lista). O Codex achou a exposição de privacidade |
| 2026-11-05 | pré-registro, challenge (1ª passada) | Codex gpt-6-astra, Kimi k3.1-pro | recibos `exit 0`, cwd do clone (cópia untracked, apagada) | as duas contra fixar; quotas por script, gold = id sorteado, contrato de entrada, bootstrap estratificado, n 60→120, H-A2 simétrico, amostra humana obrigatória. Detalhe no §8 do pré-registro |
| 2026-11-05 | pré-registro, review (2ª e 3ª passadas) | Codex gpt-6-astra, DeepSeek v4-pro | idem | contra fixar nas duas; tag executada em vez da árvore, leitura só depois da nota humana, cadeia de commits conferida antes de calcular, score e labels presos ao compromisso humano, H-A2 em dia fixo e por exposição |
| 2026-11-05 | pré-registro, review (4ª passada) | Codex gpt-6-astra, DeepSeek v4-pro | idem | controle que para no limiar exploratório, H-A2 lê o compromisso publicado, banco registrado na amostra humana, tag ≠ compromisso, planilha com BOM ou `;` |
| 2026-11-05 | diff da 4ª, review (5ª passada) | Codex gpt-6-astra | idem | toda falha do controle para a leitura, salvo a registrada; cada compromisso escrito uma vez, depois da tag. Toto: «fixa a tag» (16:51) |
| 2026-11-20 | manuscrito, challenge (1ª rodada) | Codex gpt-6-astra (96 s), Kimi k3.1-pro (307 s) | recibos `adversary-receipt-codex-2026-11-20T115537-68692.txt` e `adversary-receipt-kimi-2026-11-20T115539-69052.txt`, `exit 0`, cwd do clone | Codex: revisão maior (11 achados); Kimi: rejeição como está (10). Nenhum número divergente. Aplicados todos (#730): «interval»/«ceiling» fora, 38 rejeições atribuídas ao juiz, H-A2R num §5 retrospectivo com desenho informado, H-A2 sem «re-chunked nothing», emenda citada, 4 limitações |
| 2026-11-20 | diff do #730, review (2ª rodada) | Codex gpt-6-astra (153 s), Kimi k3.1-pro (321 s) | `adversary-receipt-codex-2026-11-20T121103-8117.txt`, `adversary-receipt-kimi-2026-11-20T121157-9490.txt`, `exit 0` | as duas: revisão menor, sem 3ª rodada. Aplicados (#731): unidades do reparo (38 entradas em 28 perguntas; errata no audit de 27/10), «still scored low», strict pelo gold registrado, ressalva de data dos commits reescritos |
| 2026-11-20 | descrição do Zenodo + diff do #731, review (3ª rodada) | Codex gpt-6-astra (58 s), Kimi k3.1-pro (253 s) | `adversary-receipt-codex-2026-11-20T140419-93847.txt`, `adversary-receipt-kimi-2026-11-20T140430-94363.txt`, `exit 0`, cwd do clone | as duas: revisão menor, segurar só até os ajustes. Aplicados (#733): PROVENANCE em queries (6 de 28; 22 e 21 queries), população do «10 of 14» nomeada, ressalva da reescrita na descrição. Rascunho refeito em `baf4b80`, readback sem divergência |
| 2026-11-20 | nota #723 inteira + descrição + diff desde o rascunho, review | Codex gpt-6-astra (229 s), Kimi k3.1-pro (856 s) | `adversary-receipt-codex-2026-11-20T190455-80669.txt`, `adversary-receipt-kimi-2026-11-20T190458-81042.txt`, `exit 0`, cwd do clone | Codex: rodada curta de correções (9 achados, nenhum alto); Kimi: NO-GO editorial, não dos dados (1 alto: T2 não é «uma frase»). Aplicados (#736): T2 como revisão de escopo, S1 0,63, escrita, contraste, registro interno com horários, recontagem por timestamp (14 chamadas, todas pós-deploy), disponibilidade pública × privada |
| 2026-11-25 | plano do corpus sintético, challenge | Codex gpt-6.2-astra (113 s), Kimi k3.1-pro (363 s; subiu na 4ª tentativa, ver Lições) | `adversary-receipt-codex-2026-11-25T092603-29153.txt`, `adversary-receipt-kimi-2026-11-25T092945-33434.txt`, `exit 0`, cwd do clone; pareceres copiados para `~/Claude/logs/adversary-outputs/` | Codex: revisão maior antes da geração paga (9 achados, 5 altos); Kimi: suíte de mecanismos, não reprodução (17). Conferidos no código e no manuscrito: duplicata exata aceita pelo resolvedor e exigida pelo selftest; CLI `--db`/`--gold` inexistente; ids preservados desde 14/10 (§4, linhas 345–354); 119 × 117 no H-A2. Todos aplicados no desenho |
| 2026-11-25 | rascunho da nota do corpus sintético (#743), challenge | Codex gpt-6.2-astra (175 s; subiu na 3ª tentativa, o hook voz-arranque-guard fechou os 2 panes mortos), Kimi k3.1-pro (439 s) | `adversary-receipt-codex-2026-11-25T105332-91623.txt`, `adversary-receipt-kimi-2026-11-25T105230-89276.txt`; pareceres em `~/Claude/logs/adversary-outputs/{codex-2026-11-25T105332-sintetico-nota,parecer-kimi-nota-synthetic-ptbr-2026-11-25}.out` | as duas: revisão maior, números transcritos certo, interpretação não. Testado e aceito: explicação do sinal de strict errada (7 das 12 acima tinham todo T no top 10); 20/20 perguntas com R incompleto mudaram de nota; rename sem reingest não passa pelo watcher; `none` definido largo (nos dados, id ausente + âncora sem chunk); controle 45/45 tautológico (fixture ganhou as notas à mão); R sempre guarda a primária (nota dizia 0,25 para as duas); média strict 0,7542 → 0,7543 (arredondamento duplo, analisador corrigido); pooled = ideal do ranking em 45/45 (achados 2 e 4 são as mesmas 5 perguntas); deleção invisível só porque os resolvedores ignoram o tombstone; resolvedor sem conferência de rc. Datas 3.5.2/3.6.0 conferidas no npm (14/10). Nota reescrita em #744 |
| 2026-11-26 | nota v1.1 (§5 da etapa 2, #756), challenge, a pedido do Toto («pode passar as vozes kimi e codex», 11:54) | Codex gpt-6.2-astra (192 s), Kimi k3.1-pro (434 s), as duas de primeira | `adversary-receipt-codex-2026-11-26T115545-83169.txt`, `adversary-receipt-kimi-2026-11-26T115559-84040.txt`, `exit 0`, cwd do clone; pareceres em `~/Claude/logs/adversary-outputs/{codex-2026-11-26T115545,kimi-2026-11-26T115558}-note-v11.out` | Codex «revisaria antes do depósito», Kimi «números reproduzíveis, qualificar». Conferido e aceito: leituras registradas que o `analyze.py` congelado não imprimia (oráculo pela regra integral 0,6268, juiz × humano por estrato, ausentes por estrato, premissa nos 25 negativos, kappas no top-10) → suplemento datado `stage2/supplement.py` (#757), mesmos rótulos, sem chamada; quantificadores: «errors were acceptances» (o J-gold tem 1 FN), «mostly» (56/112 = metade), «which every judge passed» (oráculo aceitou 2 aleatórios, envelope 1), «direction Paper A could not test» (cortado), «err alike or not at all» (cortado); nDCG por pergunta sobe 6 / cai 5 / empata 34 contra o pool perfeito → frase restrita à média neste ranking; emenda 1 resumida na §5 com 329/555 e as 172 tentativas; kappa gold~T nos 554 pares comuns (0,9171); fidelidade = requisição, não procedimento; decoys plantados declarados junto do primeiro «errors». Recusado por mim: a frase «os outros FPs do oráculo são sobretudo menção» que eu tinha acabado de escrever, sem base (amostra: 2 M, 2 F, 1 P) |
| 2026-11-25 | pré-registro da etapa 2 (rascunho #751), challenge, a pedido do Toto («Sim, Codex + Kimi (Recomendado)», 16:52) | Codex gpt-6.2-astra (173 s), Kimi k3.1-pro (453 s; subiu na 3ª tentativa) | `adversary-receipt-codex-2026-11-25T165432-7925.txt`, `adversary-receipt-kimi-2026-11-25T165530-10459.txt`, `exit 0`, cwd do clone; pareceres em `~/Claude/logs/adversary-outputs/{codex-2026-11-25T165432,kimi-2026-11-25T165530}-stage2-prereg.out` | as duas: não congelar. Conferido e aceito: corpus não exercita a falha de citação do A (frases de 43–95 caracteres, chunk máximo 924, sem `|`/`<u>`/`\R$`) → leitura limitada ao corpus + fixtures offline (escolha do Toto); T é chave de evidência plantada, não verdade semântica → amostra humana cega de 100 pares, lida pelo Toto antes de qualquer chamada (escolha do Toto); negativos descritos errado (8 rejeitados + 7 superados, 0 com o valor correto); folha da §6 escolhida pelos juízes; populações, denominadores, kappa na interseção, rótulo inválido ≠ `false`, `bool(quote)`, rerodagem, smoke, ledger com reserva, nDCG nas 45 de fato; controle aleatório na regra do A; J-reword virou J-envelope; premissa exploratória; previsões com contagens. Contagens da §2 re-derivadas pelo Kimi: batem |
| 2026-11-25 | nota revista (#747, 2ª rodada), challenge, a pedido do Toto («ja passa ai writing e vozes?», 12:13) | Codex gpt-6.2-astra (139 s; subiu na 3ª tentativa), Kimi k3.1-pro (420 s) | `adversary-receipt-codex-2026-11-25T121759-59925.txt`, `adversary-receipt-kimi-2026-11-25T121656-57640.txt`; pareceres em `~/Claude/logs/adversary-outputs/{codex-2026-11-25T121759-nota-r2,parecer-kimi-nota-synthetic-ptbr-r2-2026-11-25}.out` | as duas: revisão menor, correções da 1ª rodada feitas, nenhum experimento novo. Aceito e testado: frase do `none` conjunta (separada por referência); varredura de privacidade de um pacote que mudou depois (refeita no dia sobre o material gerado: 99.165 trechos × 65.211 chunks, 0 em comum, #748); deleção alcançável só se o ingest guarda os chunks; edição «de fora» caiu no bloco de abertura, não em outra seção `##` (5/5 em `operations.json`); 119/117 do Paper A com as duas causas; sinal de strict pela fração do ganho, não só pela posição; README desatualizado; resumo e descrição restritos a reingest/edição fora. Parcial: «181» está certo para «semana seguinte», o rótulo «na semana seguinte» (115) é que estava errado. Pacote do Zenodo será refeito do commit final |
| 2026-11-20 | nota #723 corrigida + diff do #736, review | DeepSeek v4-pro (159 s) | `adversary-receipt-deepseek-2026-11-20T194434-57083.txt`, `exit 0`, attach 121.998 | 3 achados (59 vs 54 corridas: o 59 conta qualquer chamada de memória; fontes de AFTER/BEFORE; PR #89 no texto). Aplicados (#737) |

## Lições

| Data | Lição | Para onde foi | Aplicado? |
|---|---|---|---|
| 2026-11-04 | Dois scripts de depósito gravam `SHA256SUMS` no mesmo diretório: build+fill de cada um em sequência | só aqui; vira gate se repetir | não |
| 2026-11-04 | O teste de mutação achou um defeito no próprio teste: sem commit, `git reset` não tira do stage, e do 2º infrator em diante cada caso passava pelo arquivo do anterior | só aqui (comentário no teste) | sim |
| 2026-11-04 | O gate de proveniência reprovou o próprio README do A por citar valores superados como história, e depois achou dois defeitos dele mesmo (trecho compartilhado entre registros; faixa como valor). Contar correções é o assunto do A, então o gate ganhou `history` explícito por registro | só aqui | sim |
| 2026-11-05 | Um audit inverteu a própria tabela («60% das golds não respondem» quando a tabela diz 57 de 95 ACEITAS), e o registro de proveniência herdou a frase, não a tabela. Nenhum gate pega isso: o locator casa com o texto errado. Só apareceu ao ler o audit por inteiro para resolver um item aberto | errata nos dois audits; registro superado | sim |
| 2026-11-05 | A proveniência marcava o número registrado da abstenção como «superado» pelo do juiz, gravando como fato uma interpretação («corrected») que os audits não fazem. Supersessão é decisão de leitura, não só de cronologia | só aqui | sim |
| 2026-11-25 | Escrevi um gate («duplicata exata sai ≠ 0») sem abrir o resolvedor, cujo selftest exige o contrário; as duas vozes pegaram. Gate novo sobre código existente: ler o código e o selftest antes de escrever o rc esperado | só aqui | sim (gate S: resolvedor) |
| 2026-11-25 | Kimi não arrancou 3× (linha cortada em 1.024 bytes); a regra manual não bastou. Virou hook `voz-arranque-guard` (Claude#181) | `~/.claude/CLAUDE.md` + skill `painel-adversarial` | PR aberto |
| 2026-11-25 | Exemplo dentro do prompt vira bordão do corpus: «escreva "na semana seguinte"» apareceu em 181 de 200 arquivos. Prompt de geração não dá exemplo de frase, só a regra | só aqui (README do corpus) | não |
| 2026-11-25 | A chamada de CONTROLE (sem isolamento) do `claude -p` reportou `total_cost_usd` 3,78 com 0 tokens e `refusal`, acima do `--max-budget-usd 0.30`; não guardei o JSON. Toda chamada paga grava a resposta inteira antes de ser lida | só aqui | sim (generate.py grava cada tentativa) |
| 2026-11-25 | O PR (1) testou o gate do corpus num corpus falso, mas não passou esse corpus pelo chunker do pacote; a granularidade (1 chunk por arquivo) só apareceu na 1ª ingestão real, depois da geração paga. O gate pós-ingest agora existe; corpus de teste passa pelo pacote antes de gastar | só aqui | sim (gate S: pós-ingest) |
| 2026-11-25 | Presumi o nome da tabela de tombstone (`file_tombstones`); o certo era `chunk_tombstones`, e o erro faria «stale» virar «live» em silêncio. Pego antes da 1ª corrida por ler o código; nome de tabela vem do código, nunca da memória | só aqui | sim |
| 2026-11-25 | No #744 ancorei 3 afirmações do `PROVENANCE.json` no commit da branch (`eb44723a`). O CI do PR passou, porque ali o commit está na história; o squash-merge o apagou e a `main` ficou vermelha no `guarda-lastro` até o #745 (apontar para `ac548ddb`). Afirmação nova só pode citar commit que já está na `main`: artefato produzido no PR é citado pelo commit do squash, num PR seguinte | o `deposit-note.py` da nota sintética recusa `NOTE_COMMIT` fora de `origin/main` (provado: recusou o commit da branch). Proposta ao Toto: o mesmo teste no `tools/provenance.py` quando roda em PR | parcial |
| 2026-11-04 | Plano montado a partir da MEMÓRIA herdou números superados (0,833; 0,44–0,51; 9.398; 523); a memória guarda a 1ª versão e o audit guarda a correção | memória (feedback) | sim |
