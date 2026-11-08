# ROADMAP v7 — proposta (rascunho para decisão do Toto)

> Rascunho de 2026-11-08, **revisão 2** depois das vozes Codex (`gpt-6-astra`) e Kimi, pedidas pelo Toto às
> 16h51 («roda as vozes codex e kimi»). As duas recusaram a revisão 1 como estava; o que mudou está na §6.
> **Não substitui o `docs/ROADMAP.md` (v6) até você aprovar.** Base: três estudos do mesmo dia
> (inventário de ≈70 itens abertos e 15 contradições; síntese de 29 alavancas medidas; estado do campo em
> 2026, com o post da Anthropic de 06/11), conferidos contra os artefatos citados pelas vozes.

---

## 0. Diagnóstico

1. **O maior efeito medido está na construção.** No LongMemEval (242 instâncias), o critério C2 contra o C0
   dá de +24,8 a +27,3 pp (Paper 3, contrastes condicionais, não testes confirmatórios isolados) e
   +21,1 [+14,8; +27,4] com um extrator mais forte (Paper E; as mesmas 242, então extensão pareada, não
   confirmação independente). Um prompt que só diz para que serve a memória (P) também ganha: +17,4 pp sobre o
   C0 com o flash, 3,7 pp abaixo do C2 com intervalo [−9,4; +1,9]. **O C2 roda em shadow desde 06/11; o
   produto ainda serve o C0**, embora parte da cobertura do destilador já tenha sido consertada.
2. **No corpus de produção o sinal é exploratório.** Consertar janela e prompt juntos deu +21,2 pp e cada um
   sozinho +4,0 pp; a memória como construída fez 42,4% contra 63,6% do BM25 com o mesmo orçamento. Mas o
   agregado repousa em 17 sessões, a interação em 8, a reanálise é pós-hoc e os +4,0 pp estão na borda do
   ruído (`audits/2026-10-27-neither-cause-explains-it-alone.md`, correção do mesmo dia). Serve para ordenar
   trabalho; **não vai a público sem intervalo agrupado por sessão e o rótulo de exploratório**. Com orçamento
   estritamente igual, o conserto faz 48,5%, não empata.
3. **O uso foi a segunda alavanca que funcionou, e é texto no protocolo:** devolver o texto inteiro na busca
   do MCP levou o braço de 0,28 a 0,75; `instructions` com escopo, +0,46 de acerto com +1,7 pp de falso
   gatilho. Escrita: 0 de 30 em todos os braços.
4. **Ajuste de ranking não tem vitória medida:** pain +0,0065 (n.s.), reranker −0,96 pp, boost temporal nunca
   ligado, KG no ranking −0,01 pp no backbone novo, multi-query +1,21 pp (limítrofe).
5. **Os defeitos mais caros foram silenciosos ou destrutivos** (`compact` 10.204 → 210 chunks; cursor do KG
   parado desde 16/05; contador que contava tentativa). E o `compact` destrutivo **ainda está no CLI do npm**.
6. **Uso real é pequeno, mas não zero:** zero `nox_mem_search` atribuídas por MCP antes do T2, telemetria
   dominada pela canária; houve 5 buscas em 30 dias fora da canária e das sondas, e 11 + 6 buscas espontâneas
   na tarefa de prazos (atribuídas por janela de tempo). O relatório de prazos nunca teve a leitura
   verificada. Externamente: ~2 downloads/dia no npm fora de picos de release, 1 estrela, nenhuma issue aberta
   (não medimos o histórico de issues nem quem baixa).
7. **No campo**, são raras as ablações públicas de construção com baseline BM25 e evidência crua, incluindo
   resultado negativo de produção; há trabalho próximo em política de escrita (*What Deserves Memory*, ACL
   2026) e ablação de construção no EverMemOS, e alguns fornecedores publicam baseline de contexto cheio.
   A novidade de uma comparação janela × critério × extrator precisa ser delimitada frente a eles.
   **O post da Anthropic é compatível com o Paper E, não oposto:** a regra que perdeu lá foi «registre só
   falhas» num benchmark de tarefas, e o mesmo post mostra uma mudança de construção de wiki (uma página por contrato, termos
   copiados palavra por palavra, em vez de quatro agentes escrevendo na mesma página) levando os fatos
   preservados de 41 de 57 a 57 de 57. Não sabemos qual propriedade das políticas explica a diferença; a
   leitura «a regra que estreita perde, a que amplia ganha» é hipótese.

## 1. Critério de ordenação

A revisão 1 usava uma fórmula (efeito × alcance ÷ custo) sem unidades comparáveis; ela justificava a ordem
em vez de produzi-la. Esta revisão separa **três classes, nesta precedência**:

1. **Integridade**: o que pode destruir dados, expor dado privado ou afirmar o que o código não faz.
2. **Benefício a quem usa**: o que chega a um consumidor identificado (o Claude Code do Toto, os agentes do
   OpenClaw, o relatório de prazos, quem instala pelo npm).
3. **Aprendizado que muda uma decisão**: estudo com pergunta, orçamento e condição de parada, e só um novo
   por vez.

Cada item da fila diz: para quem, resultado esperado, evidência que o sustenta, custo, dependência e quando
para. Compromissos com data (snapshot de 18/11, relatório de 15/11) entram pela data, não por estarem «na
metade».

## 2. A fila

### AGORA (até 30/11)

| # | classe | item | para quem / resultado | custo | sua decisão? |
|---|---|---|---|---|---|
| A1 | integridade | **`nox-mem compact` no npm apaga os originais** (`compact.ts:155`), com descrição "Compress old chunks". Tirar do CLI ou exigir `--destructive` e mudar a descrição | quem instala pelo npm; impede repetir o 10.204 → 210 | S | sim |
| A2 | integridade | **Privacidade do histórico público:** registrar a decisão (aceitar ou reescrever) **antes de qualquer divulgação**. O PLANO marca como BLOQUEANTE; reescrever muda os hashes citados nos pré-registros e os links `tree/<hash>` | quem lê o repo público | S para decidir; M para reescrever | sim |
| A3 | integridade | **Afirmações e dados que mentem, só o que tem efeito:** (a) retenção — tirar «retenção/esquecimento» do discurso e aplicar o `NULL` explícito + tirar `distilled` do `ELSE 90` (decidido em `DECISIONS.md:16-18`); (b) separar abstenção em «`model_abstained` em produção desde 27/10» e «piso de suficiência da evidência, ainda aberto»; (c) zerar as 14 falhas do `npm test` em produção (`.js` órfãos no `dist/`); (d) as 22 notas que ainda têm o bloco falso do `create-daily-notes.sh` e podem recriar chunks; (e) números do L4 fora do README | todo leitor e o próprio teste de regressão | S | não |
| A4 | benefício | **Relatório de prazos: verificar se é lido e escolher o canal de entrega.** É o único consumidor com busca recorrente e consequência real | Toto; decide se o lado pull tem consumidor | S | sim (canal) |
| A5 | benefício | **Ler o uso real do T2 em 15/11** pela regra pré-registrada, com as 10 buscas lidas à mão | Claude Code do Toto | S | — |
| A6 | aprendizado → benefício | **Construção, preparada direito:** versionar o `session-distill.ts` que vive só na VPS; consertar o fallback Groq (13/13 falhas) e o seletor que confunde cinco causas; publicar a tag do pré-registro do shadow do C2 (#673) e acompanhar só contagens até a leitura permitida a partir de **01/12**; preparar **janela (see-once) + C2 juntos** como opção experimental no npm, padrão inalterado. Não herda os +21,2 pp até o shadow responder | agentes do OpenClaw; depois quem usa `session-distill` | M | sim (tag; opção experimental) |
| A7 | benefício | **Alcance barato:** conferir a conta do OpenReview e, se liberada, submeter o Paper 1 ao TMLR (pacote de 48 p. pronto) | leitores do Paper 1 | S | sim (submeter) |
| A8 | aprendizado | **Paper A:** H-A2 no snapshot de 18/11 (a cópia some em 23/11). Escrever e depositar é decisão separada | — | S (coleta) | — |

### PRÓXIMO (dezembro)

| # | classe | item | por quê | custo | sua decisão? |
|---|---|---|---|---|---|
| B1 | benefício | **Onboarding observado:** instalar pelo npm do zero, primeira tarefa útil, configurar o escopo à mão; anotar onde trava | ninguém mediu se a barreira é instalação; cortar `connect` sem isso perpetua a falta de uso | S | — |
| B2 | benefício | **Escopo derivado do banco** para as `instructions` do MCP, com comparação derivado × manual em mais de um modelo e cliente antes de virar padrão | T2 passou com frase escrita à mão; derivar não foi testado | M–L | — |
| B3 | aprendizado | **T2 nos agentes do OpenClaw**, pré-registrado (hoje `NOX_MEM_INSTRUCTIONS=off`) | o arranjo deles é o de menos uso | M | sim |
| B4 | aprendizado | **Escrita:** achar um braço que faça o agente gravar | 0/30 em 4 braços | M–L | — |
| B5 | integridade | **Remoção estrutural do código inerte**, com orçamento limitado: L4 (`lib/regex-extract`, sem chamador), `lib/reranker.ts` + pré-aquecimento, `temporal-detector.ts` e o rerank temporal que só loga, código do Paper 2 encerrado; os demais órfãos só depois de conferir script/cron | código que o discurso não pode citar; menos superfície a auditar | S–M | sim (remover L4 ou ligar e medir) |
| B6 | benefício | **npm × produção:** portar o A3 (troca de provider) para produção; declarar no README o que fica só em produção (L2 conflito, P5 viewer, hooks, OCR, A2 por HTTP) | dois códigos divergentes custam cada auditoria | S–M | sim (lista) |
| B7 | benefício | **Decidir entre três caminhos de construção**, depois da leitura do shadow: entregar janela + C2; dar acesso à evidência crua (as unidades C2 ainda perdem 5,8 pp para o cru); ou investir no uso | é a escolha que a evidência ainda não faz sozinha | S (decisão) | sim |
| B8 | benefício | **Pricing, uma decisão só** (D44b Stripe-first contra Hotmart em PRICING-STRATEGY, VISION e D-2026-11-04) e, depois de A2 e de auditar os `docs/launch-*.md` (ainda trazem «language-aware weights», saliência multiplicativa, +78,8% e «16 tools»), **o lançamento** com o que o pacote sustenta: um arquivo SQLite, sem serviço externo, provider à escolha, `/api/kg/path` a 2,5 ms p50 (n=120, 29/05, no host anterior de 4 vCPU/16 GB, a remedir no atual), e onde perdemos, com intervalo e rótulo de exploratório | GTM | M | sim |

### PESQUISA — uma pergunta nova por vez, com orçamento e condição de parada

1. **Nota de uso: quando o agente busca** (T2 contra skill; escopo; 200 caracteres contra texto inteiro).
   Dados existem. Depois de 15/11.
2. **Shadow do C2 em produção** (continuação do D). Alimenta B7.
3. **Construção como protocolo** (janela × critério × extrator, com BM25 e evidência crua, calibração de juiz e
   piso de ruído, num benchmark além do LongMemEval). Antes de abrir: delimitar a novidade frente a *What
   Deserves Memory*, EverMemOS e ao próprio post da Anthropic, e fixar orçamento (o E custou US$ 150,55).
4. **Reparo contra a evidência ("dreaming")**, só com consumidor. O B2 não teve braço independente de
   só-filtrar: «o ganho é quase todo filtragem» descreve os subconjuntos da corrida, não uma política.

Os compromissos do PLANO que seguem valendo: holdout do Paper A (já feito, `paper-a-eval-ptbr/README.md`),
corpus sintético PT-BR público para testes de método (incluir no aceite do A ou declarar fora), e o braço com
retrieval real sobre o cru da frente 2.

### CONGELADO, cada um com o seu gatilho

| item | reabre quando |
|---|---|
| extração LLM do KG (#4) | consumidor **e** corpus-alvo declarado antes (o relatório de prazos sobre contratos é candidato) |
| rerank temporal implícito | fração relevante de buscas temporais **e** um gold em que o rerank vence `--as-of/--changed-since` |
| `confidence`/`provenance` no ranking | consumidor buscando **e** o gold PT-BR do item 9 |
| rebaixar por retenção (#5) | depois de A3(a), com shadow de 7 dias e A/A |
| latência / cache de embedding (#6) | tráfego real (não a canária) acima de um limiar a definir |
| procedimental (#10), R1, demais knobs de ranking | consumidor que busca e uma pergunta medível |

O relatório de 15/11 autoriza diagnóstico, não implementação em bloco.

### CORTAR (proposta de entrada no NÃO FAZEMOS)

P6 mobile, P7 extensão de navegador, E15, os dois benchmarks por método, profile-chunk: nenhum tem demanda
medida nem consumidor. Desligar o shadow do R1. Tirar «pain-weighted» do slogan como diferencial de ranking
(efeito medido +0,0065 n.s.; o pain segue como sinal de saliência). **P4 `connect` não é cortado:** a
implementação espera B1 dizer se a instalação é a barreira.

## 3. Novo índice

| pergunta | arquivo | muda o quê |
|---|---|---|
| o que o produto entrega hoje | `docs/ROADMAP.md` §2 | tabela npm × produção como verdade única, reconferida a cada release |
| o que vem e em que ordem | `docs/ROADMAP.md` §3 | esta fila |
| onde foi parar cada item aberto | `docs/ROADMAP.md` anexo | **rastreabilidade item a item**: ID do inventário → destino → razão → gatilho de reabertura (a ser gerado do inventário quando a fila for aprovada, para nenhuma obrigação sumir sem decisão) |
| por que cada não | `docs/DECISIONS.md` §1 | entram os cortes acima |
| estado de cada spec | `specs/INDEX.md` | regerado em 08/11 por estado verificado |
| papers | `PLANO.md` | ganha as linhas 1 e 3 da Pesquisa |
| regras operacionais | `CLAUDE.md` | a seção «Estado atual» (números de maio) vira ponteiro para o ROADMAP §2 |

## 4. Decisões que dependem de você

1. `compact` no npm: **remover do CLI** ou **exigir `--destructive`**?
2. Histórico com trechos do corpus privado: **aceitar** (registrado) ou **reescrever**?
3. Relatório de prazos: **canal de entrega** (Discord, e-mail, ponteiro no morning report)?
4. Shadow do C2: **publicar a tag** (#673) agora; e **janela + C2 como opção experimental** no npm?
5. OpenReview: conferir a conta e **submeter ao TMLR** se liberada?
6. L4: **remover** (recomendado) ou ligar e medir? E a **lista do que fica só em produção**?
7. Os **cortes** acima entram no NÃO FAZEMOS?
8. **Pricing** (Stripe-first ou Hotmart) e data-alvo do lançamento, depois de A2?

## 5. O que esta proposta não resolve

- **Demanda externa não medida.** Os sinais do campo vêm de fontes secundárias; não lemos issues de Mem0,
  Letta ou Zep, nem sabemos quem baixa o pacote. B1 é o primeiro passo barato.
- **Custo de oportunidade da pesquisa:** a linha de papers consumiu a maior parte do esforço de outubro e
  novembro com uso interno pequeno; a regra «uma pergunta nova por vez, com orçamento» é a contenção
  proposta, não uma solução.

## 6. O que mudou da revisão 1 para a 2 (vozes Codex e Kimi, 08/11)

| achado | quem | o que mudou |
|---|---|---|
| números de produção sem a correção de 17/8 sessões e pós-hoc; contradição entre «não vai a público sem intervalo» e o lançamento | ambas | §0.2 reescrito; B8 exige intervalo e rótulo |
| «0 buscas de agente» desatualizado | Kimi | §0.6 com as 5 + 17 buscas e a ressalva de atribuição |
| consumidor de prazos sumido da fila | ambas | A4 |
| construção opt-in só com o C2 não entrega a intervenção medida; runner, fallback e seletor sumidos; leitura do shadow só a partir de 01/12 | ambas | A6 |
| privacidade fora da fila | ambas | A2 |
| retenção, `NULL`, abstenção misturada, 22 notas falsas | ambas | A3 |
| OpenReview sem dono | ambas | A7 |
| limpeza extensa à frente de defeito vivo | Codex | A3 (efeito agora) × B5 (remoção depois) |
| gatilho único de reabertura | Codex | tabela de gatilhos por item |
| fórmula não operacional; uso interno como demanda; custo de oportunidade | Codex | §1 em três classes; B1; regra de uma pergunta por vez |
| cortar `connect` antes de medir a barreira de instalação | Codex | P4 sai de CORTAR; B1 |
| leitura do post da Anthropic como explicação estabelecida; braço P omitido; exemplo da wiki omitido | ambas | §0.7 |
| «o campo não publica baseline nem negativo» absoluto; «credibilidade é o único ativo» | ambas | §0.7 e §1 |
| 2,5 ms: Codex pediu para tirar; Kimi achou defensável com n, data e host | ambas | mantido com n=120, 29/05 e host anterior (`paper/paper-tecnico-nox-mem.md:833-849`); remedir no host atual |
| escopo derivado é M–L e precisa de comparação | Kimi | B2 |
| B2 sem braço só-filtrar | Kimi | Pesquisa 4 |

Não aceito sem ressalva: o Codex pediu retirar os 2,5 ms do discurso porque o estudo B os chamava de número
de harness; o estudo B estava errado nesse ponto (a rota `GET /api/kg/path` está no npm e foi medida na VPS de
produção, conforme o paper), e o Kimi conferiu o mesmo. O que vale do Codex é a exigência de dizer código,
data, host e n, adotada em B8.
