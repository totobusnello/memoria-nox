# Próximos passos — Paper 2

> **Reescrito 2026-08-15.** A versão anterior abria com *"Nada de execução do Paper 2 começa antes de o Paper 1 sair do hold"* — e a execução tinha começado: o piloto rodou, 7.184 pares foram adjudicados, quatro locks fecharam. O documento afirmava o oposto do estado real, que é a pior coisa que um documento de estado pode fazer. Histórico dos gates originais: `git log -- NEXT-STEPS.md`.

## Onde estamos

O **pré-registro está pronto para o OSF** (v1.11). Nenhum `[TO LOCK]` espera análise. Em 15/08 medir a dose expôs e fechou um termo indefinido no braço de tratamento (`linked`) — ver `LINK-FEASIBILITY-2026-08-15.md`. ~~O estudo **não começou**~~ — ⚠️ **superado em 2026-09-01: começou.** Epoch 1 no ar desde
10:25:39Z (`treatment`, `w = 4.0`); ver `TRIAL-START-2026-09-01.md`. O que foi medido **até
30/08** é pré-tratamento, sobre corpus histórico sem atribuição de braço — e essa parte segue
valendo. Este documento já foi reescrito uma vez, em 15/08, exatamente por afirmar o oposto do
estado real; a segunda vez custou 7 horas em vez de semanas porque um guarda passou a olhar.

O gate do arXiv ID do Paper 1 **não bloqueia mais o Paper 2**. Ele bloqueava a *publicação*; o pré-registro e o piloto seguiram sem ele, e o moderador respondeu em 13/08 que o atraso é volume — sem ação nossa. Não recontatar.

## ✅ PUBLICADO no Zenodo — 17/08/2026

**DOI do conceito** `10.5281/zenodo.21964093` — resolve sempre para a última
versão, e é o único que se cita. **v1.9** foi publicada em 17/08 sob o DOI de
versão `10.5281/zenodo.21964094`, com 38 arquivos, CC-BY-4.0. O carimbo público
existe e é anterior a qualquer epoch, que é a propriedade que o desenho precisa.

**v1.11 é uma versão nova**, com 39 arquivos: as quatro afirmações do §2 que
ficaram obsoletas quando a banda mudou, os três portões do fresh pool, os quatro
travamentos que faltavam, e `claims_check.py` — o guarda que recomputa cada
afirmação dependente da banda e varre o pacote atrás das frases superadas. Ela
recebe DOI de versão próprio na publicação; anotar aqui quando sair.

⚠️ **Os arquivos ficaram imutáveis.** Qualquer conserto daqui em diante é uma
versão nova, nunca uma edição — o custo de um defeito subiu, e a auditoria
arquivo-a-arquivo passa a ser pré-requisito de cada versão. A v1.10 foi a primeira
prova disso: ela existe porque a v1.9 saiu com uma frase falsa na linha 306.

⚠️ **Ainda falta o OSF, e não é formalidade.** O pré-registro nomeia OSF 15
vezes, incluindo *"becomes binding only when registered on OSF with a public
timestamp"*, e o `T_seed_assign` está definido como *"strictly after the OSF
registration timestamp"*. Sem o registro no OSF esse âncora não tem a que se
prender, e um revisor que lê "OSF" e acha só um preprint no Zenodo tem uma
pergunta sobre procedimento — a pior de responder. Registrar no OSF apontando
para o DOI do Zenodo resolve, sem desfazer nada: o carimbo do Zenodo é anterior e
só reforça a precedência.

## O próximo passo, e por que é este

**Registrar no OSF.** O Zenodo já transformou o documento em ativo público datado — o que falta é o registro no registro que o próprio documento nomeia (ver acima). Sem ele, `T_seed_assign` não tem âncora e a cláusula de vinculação não é literalmente verdadeira.

Registrar dispara, em ordem: `T_seed_assign` fica declarável (deve ser posterior ao timestamp OSF e anterior ao primeiro epoch de tratamento) → primeiro epoch randomizado → data-limite de calendário. Os dois `[TO LOCK]` restantes caem por consequência.

## Depois disso

| | O quê | Nota |
|---|---|---|
| 1 | ~~Fixar o operacional da escrita~~ | ✅ 16/08 — os três itens (quem escreve e se recorrência insere ou atualiza; texto livre; instante dentro do epoch) travados no §2. **Insert, nunca update** era o que a condição 4 exigia para a tabela de dose continuar válida |
| 2 | Executar o estudo — **234 epochs** | ~7,7 meses (2026-09-01 → 2027-04-22), cap de 323 dias. Sem análise interina, sem parada opcional |
| 3 | ~~Ler InterruptBench~~ | ✅ 15/08 — `RELATED-WORK.md` §4.2 |
| 4 | ~~Resolver "hypotree"~~ | ✅ 15/08 — era um **MCP server**, não um paper. §4.3 |

## O que 16/08 fechou, e o que ele reordenou

O script de alocação **não existia** — o §2 o registrava como artefato pré-hoc "com o hash do commit", e o Apêndice B falava dele no presente. Escrito como `assign_arms.py`, testado em 7.300 casos.

Isso **reordena o plano**: o registro carimba o hash do commit do script, então o script precisa estar commitado *antes* de registrar no OSF. Não depois.

Escrevê-lo forçou para fora três coisas que nenhuma lista de `[TO LOCK]` continha:

1. **A alocação das doses nunca foi escrita.** Agora registrada: **117 controle / 39 por dose** (era 87/29 sob o `N` = 174 superado em 17/08). O primário continua 117×117 — nenhum número travado se move por causa da alocação — mas a regra de leitura dose-resposta roda a **39 por dose**, e isso está dito antes de existir resultado.
2. **O esquema e a tolerância.** Randomização em blocos estratificados (metade-de-calendário × dia-útil/fim-de-semana), arredondamento controlado bidirecional, tolerância `< 1` por célula.
3. **A mesma rotina serve o teste de permutação** do §5 — um teste que sorteia de distribuição diferente da que atribuiu não é um nulo válido.

Junto foram fechados os buracos do plano de análise que o Codex listou: bootstrap (10.000, BCa, reamostragem por epoch estratificada por braço), família do modelo (binomial negativa para taxa, binomial-logit para proporção, sem escolha adaptativa), forma do lag-1 (indicador binário), definição do H1b (`H1c ⊆ H1b ⊆ H1a`) e a fórmula da data-limite (`primeiro epoch + 240 dias`).

## Aberto, e não é trabalho nosso

- **Para quem escrever no Stanford** (`docs/STANFORD-OUTREACH.md`): correspondência do 2606.06448 é da Omri; o cluster que liga ao MemoryArena é He/Pentland. Decisão do Toto.
- **arXiv ID do Paper 1**: sem ação possível.

## Previsões registradas — cobrar depois

Ambas ficaram no registro **antes** do primeiro epoch, e existem para serem verificadas contra o que acontecer, não para serem lembradas seletivamente:

1. **`N = 234` (emendado 17/08; era 174) e a nota abaixo agora corta nos dois sentidos.** ⚠️ A dispersão de tamanho de cluster que forçou a fórmula de cluster desigual (`cv²` = 0,3833) e a deriva descrita aqui são **a mesma não-estacionariedade** — as sessões por epoch caem cerca de dez vezes ao longo do piloto. A nota estabelece que a janela do piloto é heterogênea, e heterogeneidade é exatamente a condição sob a qual a fórmula de cluster igual é inválida. Preservada como escrita:

1. **`N = 174` provavelmente é conservador.** Os parâmetros do regime maduro do corpus dariam N=46 a MDE 25% (106 no limite superior do ICC) — e o lock é mais folgado ainda, por dimensionar a 30% no limite superior. Se estiver certo, o estudo chega ao horizonte com mais poder que o planejado. Ver `PREREG-DRAFT.md`, Apêndice B, nota de não-estacionariedade.
2. **O painel não pode provar que julgou com glm-5.2** nos 3.348 vereditos anteriores a 14/08. `model_served` passou a ser gravado, mas não é retroativo. Se a composição do painel virar questão de revisão, esta é a resposta honesta.
