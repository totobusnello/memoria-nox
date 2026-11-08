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

## Fora do escopo

- Publicar texto do corpus privado, queries reais, nomes de arquivo do corpus ou endereço de host.
- Comparação com outros sistemas de memória (Paper 1).
- C2 ativo em produção; e o shadow vivo do D sem protocolo próprio e sem o seu ok.
- Afirmar «não uso» comportamental no C sem uma corrida com controle positivo válido.
- arXiv, salvo pedido seu.

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
| A: âncoras | `python3 eval/resolve-gold-anchors.py --db <snapshot> --gold <arquivo>`, contagem não vazia, ambíguas reportadas | 0 | antes da corrida | apontar um gold para trecho inexistente | | |
| D: não interferência | replay offline: roda C0 e C2 sobre banco de fixture e confere que nenhuma tabela, arquivo ou fila fora do diretório de saída mudou (hash antes e depois) | 0 | todo PR do D | fazer o C2 gravar em qualquer tabela do banco | | |

## Verificações manuais

| Verificação | Quem confere | Evidência | Última vez (data, PR) |
|---|---|---|---|
| Passe avoid-ai-writing antes das vozes e antes do depósito | Claude | diff no PR | |
| Precedência do pré-registro (A, D): push da tag antes da 1ª chamada, e queries do holdout nunca vistas antes | Claude, pelo activity log do GitHub | horários no texto | |
| Amostra humana cega dos pares discordantes (A) | você ou alguém que você indicar | planilha de rótulos fora do repo, só o kappa publicado | |
| O que vai para a Decisions API e onde ficam prompts e respostas | Claude, por escrito no protocolo | seção de dados do protocolo | |
| Preview do card no labf.bio | você | URL do preview | |
| Publicação no Zenodo | você | DOI público + `--readback` | |
| Shadow vivo do D, se houver | você aprova; Claude executa com limite de custo, de tempo e desligamento rápido | log do shadow e `/api/health` | |

## Etapa atual

Etapa: Work (paper A, parte prospectiva): H-A1 lido, H-A2 aguarda 18/11
Próximo passo: H-A2 no primeiro snapshot de 18/11 (cópia até 23/11; lembretes na agenda em 18/11
e 22/11); depois o texto do paper a partir de `paper-a-eval-ptbr/RESULTS.md`. Os itens abertos do README
foram resolvidos em 05/11 (Toto decidiu 1 a 3).
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
regra de parada aprovadas em 07/11; a tag espera o ok.
Último resultado dos gates: 2026-11-07 · `b-test.py` 53 verificações, 0 falhas (mutações no
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
2. **A: holdout.** Escrever queries novas antes de ver qualquer ranking delas; sem isso a parte nova
   se chama «remedição de estabilidade», não confirmação.
3. **A: corpus sintético.** Pequeno, PT-BR, público, só para os testes de método. Os números de
   produção ficam como estudo de caso agregado.
4. **D: o `session-distill.ts` vive só na VPS.** Trazer o runner para um artefato versionado antes
   de qualquer experimento.
5. **Item 2 (GTM Phase 2):** memo separado; inclui tirar «retenção» da fala.

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
| 2026-11-06 | D: tag `paper-d-prereg-v1.0` sem revisão adversarial antes | Toto escolheu «Tag hoje, sem vozes»; o pré-registro registra a ausência de revisão (§10) |

## Vozes

| Data | Ponto | Vozes | Recibo / parecer | O que mudou |
|---|---|---|---|---|
| 2026-11-04 | fim do Plan, challenge | Codex gpt-6-astra (130 s), Kimi k3.1-pro (618 s) | recibos `adversary-receipt-codex-2026-11-04T215237-1793.txt` e `adversary-receipt-kimi-2026-11-04T215241-2301.txt`, `exit 0`, cwd do clone | todos os achados conferidos nos audits e confirmados, menos um: o «−5,8 pp é o contraste errado», das duas, vem de lerem o manuscrito v1.0 do `main`; −5,8 é o comitê da v1.5. Mudaram a tabela inteira de números, a ordem, o recorte de C, o desenho de D e os gates (proveniência, privacidade antes do push, exportação por lista). O Codex achou a exposição de privacidade |
| 2026-11-05 | pré-registro, challenge (1ª passada) | Codex gpt-6-astra, Kimi k3.1-pro | recibos `exit 0`, cwd do clone (cópia untracked, apagada) | as duas contra fixar; quotas por script, gold = id sorteado, contrato de entrada, bootstrap estratificado, n 60→120, H-A2 simétrico, amostra humana obrigatória. Detalhe no §8 do pré-registro |
| 2026-11-05 | pré-registro, review (2ª e 3ª passadas) | Codex gpt-6-astra, DeepSeek v4-pro | idem | contra fixar nas duas; tag executada em vez da árvore, leitura só depois da nota humana, cadeia de commits conferida antes de calcular, score e labels presos ao compromisso humano, H-A2 em dia fixo e por exposição |
| 2026-11-05 | pré-registro, review (4ª passada) | Codex gpt-6-astra, DeepSeek v4-pro | idem | controle que para no limiar exploratório, H-A2 lê o compromisso publicado, banco registrado na amostra humana, tag ≠ compromisso, planilha com BOM ou `;` |
| 2026-11-05 | diff da 4ª, review (5ª passada) | Codex gpt-6-astra | idem | toda falha do controle para a leitura, salvo a registrada; cada compromisso escrito uma vez, depois da tag. Toto: «fixa a tag» (16:51) |

## Lições

| Data | Lição | Para onde foi | Aplicado? |
|---|---|---|---|
| 2026-11-04 | Dois scripts de depósito gravam `SHA256SUMS` no mesmo diretório: build+fill de cada um em sequência | só aqui; vira gate se repetir | não |
| 2026-11-04 | O teste de mutação achou um defeito no próprio teste: sem commit, `git reset` não tira do stage, e do 2º infrator em diante cada caso passava pelo arquivo do anterior | só aqui (comentário no teste) | sim |
| 2026-11-04 | O gate de proveniência reprovou o próprio README do A por citar valores superados como história, e depois achou dois defeitos dele mesmo (trecho compartilhado entre registros; faixa como valor). Contar correções é o assunto do A, então o gate ganhou `history` explícito por registro | só aqui | sim |
| 2026-11-05 | Um audit inverteu a própria tabela («60% das golds não respondem» quando a tabela diz 57 de 95 ACEITAS), e o registro de proveniência herdou a frase, não a tabela. Nenhum gate pega isso: o locator casa com o texto errado. Só apareceu ao ler o audit por inteiro para resolver um item aberto | errata nos dois audits; registro superado | sim |
| 2026-11-05 | A proveniência marcava o número registrado da abstenção como «superado» pelo do juiz, gravando como fato uma interpretação («corrected») que os audits não fazem. Supersessão é decisão de leitura, não só de cronologia | só aqui | sim |
| 2026-11-04 | Plano montado a partir da MEMÓRIA herdou números superados (0,833; 0,44–0,51; 9.398; 523); a memória guarda a 1ª versão e o audit guarda a correção | memória (feedback) | sim |
