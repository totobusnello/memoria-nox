# nox-mem ROADMAP v7 — integridade, quem usa, e só então o que aprender

> **v7, 2026-11-08, aprovada pelo Toto** («ok segue tuas sugestões»). Feita a partir de três estudos do
> mesmo dia (inventário de ≈70 itens abertos e 15 contradições; síntese de 29 alavancas medidas; estado do
> campo em 2026, com o post da Anthropic de 06/11) e revista pelas vozes Codex e Kimi, que recusaram a
> primeira versão (o que mudou está no fim). O v6 está intacto em `docs/_archive/ROADMAP-v6-pre-v7-2026-11-08.md`.
>
> Estado vivo e próxima ação: `docs/HANDOFF.md`. Porquês e NÃO FAZEMOS: `docs/DECISIONS.md`.
> Estado verificado de cada spec: `specs/INDEX.md`.

---

## 0. Princípios (valem para todo item abaixo)

1. **O roadmap descreve o que o usuário instala.** Uma feature só é "no produto" quando a flag ou
   o código existe no src de produção **e** no pacote npm. Conferir com `grep`, nunca de memória.
   O que só roda num harness de eval é **resultado de pesquisa**, e é chamado assim.
2. **O índice aponta para o original, nunca o substitui.** Resumo, entidade e relação do KG são
   endereços para a evidência bruta, que continua no banco (NÃO FAZEMOS #32; EnSIMem, 2026).
3. **Esquecer é rebaixar com métrica, nunca apagar sem medida.** Deleção só por decisão
   explícita, com dry-run, snapshot e validação pós-op (regra 6 do `CLAUDE.md`).
4. **Um contador conta efeito, não tentativa.** O `kg-build` logava "Built: 705 relations" e
   inseria zero. Guarda que conta tentativa é guarda que mente (catálogo "como um guarda mente").
5. **Acurácia nunca sai sozinha:** todo número de qualidade vem com custo e latência ao lado.
6. **Gate de ranking:** shadow ≥ 7 d, 5 batches com IC 95%, **mais uma rodada A/A** para medir o
   chão de ruído antes de ler qualquer diferença (Recuris, 2026: A/A mexeu ±7 pontos).

---

## 1. Estado medido (2026-10-14, fim do dia; não reconferido em bloco desde então)

| o quê | valor | fonte |
|---|---|---|
| chunks | **52.928** (43.284 antes das restaurações de 14/10: +182 arquivos em disco, +27 arquivos de backup) | `/api/health` |
| vetores | 52.928/52.928, 0 órfãos, **todos `RETRIEVAL_DOCUMENT`** (919 trocados) | `/api/health`, `ops_audit` 356 |
| entity sections | `compiled == frontmatter == 239` | `/api/health` |
| chunks sem tipo (`other`) | ~67% do corpus | `/api/health` (13/10) |
| KG | 15.620 entidades / 17.753 relações; extração LLM parada desde 16/05 → cobre ~7% do corpus | D-2026-10-14 |
| KG — de onde vem a evidência (22/10) | **vault 82,2%** · `memory/` outros 9,0% · `shared/` 8,3% · sem evidência 0,5% | censo em `kg_relations ⨝ chunks` |
| KG — fidelidade (22–23/10, n=150) | **0,900** [0,842 · 0,938] com os quatro princípios aplicados; o 0,907 da manhã não tinha P1/P3, o 0,833 de 22/10 era predicado não versionado | `audits/2026-10-23-kg-s1-quatro-principios.md` |
| buscas | 681 em 14 dias, média **1.081 ms**, sem cache de embedding da query | `search_telemetry` |
| quem busca | `requesting_agent` gravado desde 14/10 (`<superfície>:<agente>`, `probe:*`); os agentes ainda não se identificam → `*:unknown` | nox-workspace#55 |
| `compact` | **pausado** (`/root/.openclaw/DISABLE_COMPACT`); 1 resumo restante (waiver da Nuvini, sem backup anterior) | openclaw-vps#45 |
| npm | **`nox-mem@3.9.1` = latest** (08/11: `instructions` do MCP só com `NOX_MEM_SCOPE`); 3.7.0 de 15/10 trouxe o embedding do chunk inteiro e chunks ≤ 4.000 | nox-mem#57, nox-mem#51 |

---

## 2. O que o produto tem (verdade única, reconferida a cada release)

| item | produção (`nox-workspace`) | npm `nox-mem@3.9.1` (tabela reconferida em 08/11, `specs/INDEX.md`) | v5 dizia |
|---|---|---|---|
| busca híbrida FTS5 + Gemini + RRF, boost stack, salience v2 | ✅ | ✅ | ✅ |
| `/api/brief`, `/api/answer` com citação, privacy filter no ingest | ✅ | ✅ | ✅ |
| KG path, multi-query, MA-protection, classificador adaptativo, RRF por idioma, IterB, Self-Ask | ❌ (só `eval/evermembench/`) | ❌ | "SHIPPED opt-in" |
| `NOX_TEMPORAL_BOOST_MODE` | removida do `.env` em 14/10 (módulo só importado pelo teste) | ❌ | ativo |
| `NOX_TEMPORAL_PATH=active` | existe, mas não muda o ranking (`search.ts:722`) | — | D49/D50 → NÃO FAZEMOS #33 (D-2026-10-14b) |
| troca de provider de embedding (A3) | ❌ (Gemini direto no `embed.ts`) | ✅ `NOX_EMBEDDING_PROVIDER` | ✅ |
| A2 export/import | ✅ só HTTP (`POST /api/export` e `/api/import`, conferido na VPS em 08/11; sem CLI) | ❌ | staged / spec |
| P4 `nox-mem connect` | ❌ | ❌ | staged / spec |
| L2 conflito no KG, P5 viewer, hooks (P2 parcial), OCR (E12) | ✅ | ❌ | — |
| L4 extração regex-first | código presente, sem chamador (`NOX_L4_REGEX_ENABLED` sem efeito) | removido na 3.10.0 (nox-mem#60) | «95,8% P/R, 80% menos Gemini» |
| `compact` (troca chunks por resumo e apaga os originais) | pausado por `DISABLE_COMPACT` | recusa sem `--destructive` a partir da 3.10.0 (nox-mem#60) | «compress» |
| abstenção quando a resposta não tem citação (`model_abstained`) | ✅ desde 27/10 (DECISIONS, 2026-10-27) | não conferido | S2 gated |
| piso de suficiência da evidência no `/api/answer` (item 8) | ❌ | ❌ | S2 gated |

README, `CONFIGURATION.md`, `COMPARISON.md` e `COMPETITIVE-POSITIONING.md` corrigidos em 14/10
(memoria-nox#577): os números de eval continuam lá, rotulados como do harness de pesquisa.

---

## 3. Critério de ordenação

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

---

## 4. A fila

### AGORA (até 30/11)

Decisões do Toto em 08/11 (§9): todas as sugeridas foram aceitas, menos a do histórico privado (A2), que depende de uma resposta sobre o cofre.

| # | classe | item | para quem / resultado | custo | decisão |
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

| # | classe | item | por quê | custo | decisão |
|---|---|---|---|---|---|
| B1 | benefício | **Onboarding observado:** instalar pelo npm do zero, primeira tarefa útil, configurar o escopo à mão; anotar onde trava | ninguém mediu se a barreira é instalação; cortar `connect` sem isso perpetua a falta de uso | S | — |
| B2 | benefício | **Escopo derivado do banco** para as `instructions` do MCP, com comparação derivado × manual em mais de um modelo e cliente antes de virar padrão | T2 passou com frase escrita à mão; derivar não foi testado | M–L | — |
| B3 | aprendizado | **T2 nos agentes do OpenClaw**, pré-registrado (hoje `NOX_MEM_INSTRUCTIONS=off`) | o arranjo deles é o de menos uso | M | sim |
| B4 | aprendizado | **Escrita:** achar um braço que faça o agente gravar | 0/30 em 4 braços | M–L | — |
| B5 | integridade | **Remoção estrutural do código inerte**, com orçamento limitado: L4 (`lib/regex-extract`, sem chamador), `lib/reranker.ts` + pré-aquecimento, `temporal-detector.ts` e o rerank temporal que só loga, código do Paper 2 encerrado; os demais órfãos só depois de conferir script/cron | código que o discurso não pode citar; menos superfície a auditar | S–M | sim (remover L4 ou ligar e medir) |
| B6 | benefício | **npm × produção:** portar o A3 (troca de provider) para produção; declarar no README o que fica só em produção (L2 conflito, P5 viewer, hooks, OCR, A2 por HTTP) | dois códigos divergentes custam cada auditoria | S–M | sim (lista) |
| B7 | benefício | **Decidir entre três caminhos de construção**, depois da leitura do shadow: entregar janela + C2; dar acesso à evidência crua (as unidades C2 ainda perdem 5,8 pp para o cru); ou investir no uso | é a escolha que a evidência ainda não faz sozinha | S (decisão) | sim |
| B8 | benefício | **Pricing, uma decisão só** (D44b Stripe-first contra Hotmart em PRICING-STRATEGY, VISION e D-2026-11-04) e, depois de A2 e de auditar os `docs/launch-*.md` (ainda trazem «language-aware weights», saliência multiplicativa, +78,8% e «16 tools»), **o lançamento** com o que o pacote sustenta: um arquivo SQLite, sem serviço externo, provider à escolha, `/api/kg/path` a 2,5 ms p50 (n=120, 29/05, no host anterior de 4 vCPU/16 GB, a remedir no atual), e onde perdemos, com intervalo e rótulo de exploratório | GTM | M | sim |

## 5. Pesquisa — uma pergunta nova por vez, com orçamento e condição de parada

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

---

## 6. Congelado, cada um com o seu gatilho

| item | reabre quando |
|---|---|
| extração LLM do KG (#4) | consumidor **e** corpus-alvo declarado antes (o relatório de prazos sobre contratos é candidato) |
| rerank temporal implícito | fração relevante de buscas temporais **e** um gold em que o rerank vence `--as-of/--changed-since` |
| `confidence`/`provenance` no ranking | consumidor buscando **e** o gold PT-BR do item 9 |
| rebaixar por retenção (#5) | depois de A3(a), com shadow de 7 dias e A/A |
| latência / cache de embedding (#6) | tráfego real (não a canária) acima de um limiar a definir |
| procedimental (#10), R1, demais knobs de ranking | consumidor que busca e uma pergunta medível |

O relatório de 15/11 autoriza diagnóstico, não implementação em bloco.

---

## 7. Cortado (NÃO FAZEMOS #35 a #40, D-2026-11-08b)

P6 mobile, P7 extensão de navegador, E15, os dois benchmarks por método, profile-chunk: nenhum tem demanda
medida nem consumidor. Desligar o shadow do R1. Tirar «pain-weighted» do slogan como diferencial de ranking
(efeito medido +0,0065 n.s.; o pain segue como sinal de saliência). **P4 `connect` não é cortado:** a
implementação espera B1 dizer se a instalação é a barreira.

### Saiu do roadmap em 14/10 (fica como registro de pesquisa)

IterB e Self-Ask (Q3 iterative retrieval), matriz de backbones, capstone da Wave 2 (D76),
E15 CodeGraph (L1), reranker no caminho default (D-2026-09-21c), Docker (removido em 29/09),
MMR na `/api/search` (o `search-dedup` já tem 4 camadas, incluindo Jaccard). Os números
continuam válidos onde foram publicados (Paper 1, `COMPARISON.md` como eval), só não são
features do produto.

---

## 8. O que este roadmap não resolve

- **Demanda externa não medida.** Os sinais do campo vêm de fontes secundárias; não lemos issues de Mem0,
  Letta ou Zep, nem sabemos quem baixa o pacote. B1 é o primeiro passo barato.
- **Custo de oportunidade da pesquisa:** a linha de papers consumiu a maior parte do esforço de outubro e
  novembro com uso interno pequeno; a regra «uma pergunta nova por vez, com orçamento» é a contenção
  proposta, não uma solução.

---

## 9. Decisões do Toto em 08/11

| # | decisão | escolha |
|---|---|---|
| 1 | `compact` no npm | exigir `--destructive` (feito: nox-mem#60, 3.10.0) |
| 2 | histórico com trechos do corpus privado | **pendente**: aceitar e registrar se o cofre não tem dado de terceiro sob sigilo; reescrever se tiver |
| 3 | canal do relatório de prazos | dentro do morning report, uma linha por obrigação dos próximos 14 dias; teste de duas semanas |
| 4 | shadow do C2 | tag do pré-registro agora; opção experimental (janela + C2) só depois de versionar o runner e consertar fallback e seletor |
| 5 | OpenReview / TMLR | conferir a conta agora; antes de submeter, passar o manuscrito do Paper 1 contra a auditoria de 08/11 |
| 6 | L4 e código inerte | remover L4 e reranker (feito no npm: nox-mem#60); os demais na B5; L2, P5, hooks, OCR e A2 por HTTP ficam só em produção, declarados; A3 portado para produção |
| 7 | cortes | aceitos (NÃO FAZEMOS #35 a #40); P4 espera B1 |
| 8 | pricing e lançamento | pricing suspenso até haver uso externo medido (pacote MIT gratuito); lançamento na primeira quinzena de dezembro, terça ou quinta, depois de A1–A3 e da auditoria dos `docs/launch-*.md` |

---

## 10. Ponteiros

| conteúdo | arquivo |
|---|---|
| estado vivo + próxima ação | `docs/HANDOFF.md` |
| decisões + NÃO FAZEMOS | `docs/DECISIONS.md` |
| estado de cada spec | `specs/INDEX.md` |
| papers | `PLANO.md` |
| regras operacionais | `CLAUDE.md` |
| visão de longo prazo | `docs/VISION.md` |
| rastreabilidade do inventário de 08/11 | a gerar (cada ID do inventário → destino → razão → gatilho) |
| roadmaps anteriores | `docs/_archive/ROADMAP-v6-pre-v7-2026-11-08.md`, `docs/_archive/ROADMAP-v5-pre-v6-2026-10-14.md` |

---

## Como esta versão foi feita

## Diagnóstico de 08/11

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


### O que as vozes mudaram (Codex e Kimi, 08/11)

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
