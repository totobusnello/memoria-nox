# ROADMAP v7 — proposta (rascunho para decisão do Toto)

> Rascunho de 2026-11-08. **Não substitui o `docs/ROADMAP.md` (v6) até você aprovar.** Feito a partir de
> três estudos do mesmo dia: inventário de tudo o que está aberto (≈70 itens, 15 contradições entre
> documentos), síntese do que as medições dizem que move resultado (29 alavancas), e o estado do campo
> em 2026 (produtos, literatura, o post da Anthropic de 06/11). Os números abaixo vêm desses estudos e
> dos artefatos que eles citam; os marcados *(via memória)* precisam de releitura do artefato antes de
> irem para qualquer texto público.

---

## 0. Diagnóstico em sete linhas

1. **O valor medido está na construção, não na busca.** No corpus de produção (99 perguntas, 20 sessões),
   consertar só a janela dá +4,0 pp, só o prompt dá +4,0 pp, os dois juntos dão +21,2 pp *(via memória)*.
   No LongMemEval (242), o critério C2 contra o C0 dá +24,8 a +27,3 pp (Paper 3) e +21,1 [+14,8; +27,4]
   com um extrator mais forte (Paper E). **Nada disso está no produto:** o C2 roda em shadow desde 06/11.
2. **A memória como está perde para BM25 no próprio corpus:** 42,4% contra 63,6% com o mesmo orçamento
   (−21,2 pp). Com a construção consertada empata, mas usando 2,41× o contexto *(via memória)*.
3. **O lado do uso foi a segunda alavanca que funcionou, e é texto no protocolo, não ranking:** devolver o
   texto inteiro na busca do MCP levou o braço de 0,28 a 0,75; `instructions` com escopo, +0,46 de acerto
   com +1,7 pp de falso gatilho. Escrita: 0 de 30 em todos os braços.
4. **Ajuste de ranking não tem vitória medida:** pain +0,0065 (n.s.), reranker −0,96 pp, boost temporal
   nunca ligado, KG no ranking −0,01 pp no backbone novo, multi-query +1,21 pp (limítrofe).
5. **Os defeitos mais caros foram silenciosos ou destrutivos:** `compact` levou 10.204 chunks a 210;
   cursor de extração do KG parado desde 16/05 (93% do corpus nunca visto); contador que contava tentativa.
6. **Uso real é ínfimo:** 0 buscas de agente desde 01/09 (só a canária busca); 278 sessões do Claude Code,
   0 buscas antes do T2; npm ~2 downloads/dia fora de picos de release; 1 estrela, 0 issues externas.
7. **O campo** compete em busca, grafo e placar de benchmark que não se reproduz entre harnesses (Mem0
   LongMemEval 94,4 do fornecedor contra 49,0 e 73,8 de terceiros). Quase ninguém publica ablação de
   construção, baseline BM25 nem resultado negativo. O post da Anthropic (06/11) valida "construção e
   manutenção importam", mas diz que **regras fixas atrapalham modelos fortes** ("record only failures":
   −0,234 no Opus 5): é preciso responder com o Paper E, onde a regra que *amplia* o que guardar ganhou.

## 1. Critério de ordenação

**Importância = efeito já medido × chance de chegar a quem usa ÷ custo.** Item sem consumidor real espera,
por melhor que seja no harness. Item que mente (código que o README afirma e não roda, comando que apaga
sem aviso) vai na frente de feature nova, porque custa credibilidade, que é o único ativo que o campo não
tem e nós temos.

## 2. A fila proposta

### AGORA (até 30/11) — segurança, verdade e o maior efeito medido

| # | item | por quê (evidência) | custo | decisão sua? |
|---|---|---|---|---|
| A1 | **`nox-mem compact` no npm apaga os originais.** Em produção está pausado por arquivo-flag (NÃO FAZEMOS #32); no pacote é um comando com descrição "Compress old chunks". Proposta: tirar do CLI ou exigir `--destructive`, e mudar a descrição | apagou 10.204 → 210 em produção; qualquer usuário do npm repete | S | sim: remover ou travar |
| A2 | **Ler o uso real do T2 em 15/11** (relatório automático, regra pré-registrada) | é o portão de todo o lado do uso; base 278 sessões, 0 buscas | S | — |
| A3 | **Construção no produto, em duas metades.** (a) Publicar a tag do pré-registro do shadow do C2 (#673, pronta) e ler o shadow pela regra dele. (b) Pôr o C2 no `session-distill` do npm como opção (`--criterion c2`), sem trocar o padrão, enquanto o shadow corre | maior efeito medido do projeto; o npm já tem `session-distill`; opção não muda nada para quem não liga | M | sim: tag + opção no npm |
| A4 | **Higiene que mente** (um PR por repo): remover o L4 (`lib/regex-extract`, 9 arquivos sem chamador) e tirar seus números do README; remover `lib/reranker.ts` + pré-aquecimento; remover `temporal-detector.ts` e o rerank temporal que só loga; conferir por script/cron e remover os órfãos (`seh-detector`, `events/bus`, `impact`, `detect-changes`, `cost-cap`, `graphify-ingest`); remover o código do Paper 2 encerrado (`epoch-serving`, `paper2/write-path` e a rota interna); zerar as 14 falhas do `npm test` em produção (`.js` órfãos no `dist/`) | código que o discurso afirma e não roda é o mesmo erro que o v6 corrigiu; `npm test` vermelho esconde regressão | S–M | sim: remover L4 (ou ligar e medir) |
| A5 | **Paper A**: H-A2 no snapshot de 18/11, texto, depósito | já pré-registrado e na metade | M | — |
| A6 | **Fechar as contradições de documento que são só texto** (ROADMAP §4 GTM, item 9 e item 7 obsoletos, CLAUDE.md "Estado atual" de maio, NÃO FAZEMOS #8 "16 tools" com 19+ expostas, abstenção marcada ❌ estando em produção desde 27/10) | o v6 nasceu de contradições assim | S | não |

### PRÓXIMO (dezembro) — uso, escrita e lançamento

| # | item | por quê | custo | decisão sua? |
|---|---|---|---|---|
| B1 | **Escopo derivado do banco** para as `instructions` do MCP (quem instala pelo npm não escreve `NOX_MEM_SCOPE`) | T2 só passou com escopo; sem escopo, falso gatilho +32 pp | M | — |
| B2 | **T2 nos agentes do OpenClaw**, pré-registrado (hoje `NOX_MEM_INSTRUCTIONS=off`) | agentes: 0 buscas desde 01/09 | M | sim |
| B3 | **Escrita: achar um braço que faça o agente gravar** (hook que propõe `decision_set`; resultado de tool que pede o registro) | 0/30 em 4 braços; sem escrita, a memória só enche por ingestão | M–L | — |
| B4 | **npm × produção num só código.** Portar o A3 (troca de provider) para produção; **não** portar ao npm o que não tem uso medido (L2 conflito, P5 viewer, hooks, OCR, A2 por HTTP) e declarar isso no README | dois códigos divergentes custam cada auditoria; nada desses tem uso medido | S–M | sim: lista do que fica só em produção |
| B5 | **Lançamento (GTM Phase 2) com o discurso que o pacote sustenta**: um arquivo SQLite, sem serviço externo, provider à escolha, `/api/kg/path` em 2,5 ms sem LLM (medido em produção), e "publicamos onde perdemos" (−21,2 pp para BM25 como construído; −5,8 pp para evidência crua). Antes: auditar `docs/launch-*.md` contra o README corrigido | o campo não publica baseline nem negativo; é a diferença crível | M | sim: data + pricing |
| B6 | **Pricing: uma decisão só.** D44b rejeitou Hotmart (Stripe-first), mas PRICING-STRATEGY, VISION e o D-2026-11-04 ainda falam Hotmart | contradição aberta desde maio | S | sim |

### PESQUISA — linha de papers, por valor

1. **Nota de uso: quando o agente busca** (T2 contra skill; escopo como variável; 200 caracteres contra texto
   inteiro). Dados já existem; custo baixo; fala direto com o achado da Anthropic de que o Sonnet 4.6 não lia a
   própria memória. *Depois de 15/11.*
2. **Shadow do C2 em produção** (continuação do D, sem a falha de fidelidade por construção). Decide a
   "segunda onda" do GTM.
3. **Construção como protocolo**: janela × critério × extrator, com baselines BM25 e evidência crua, calibração
   de juiz e piso de ruído, num benchmark público além do LongMemEval. É a posição que o campo não ocupa, e a
   resposta direta ao "regras fixas atrapalham" do post de 06/11 (a regra que estreita perde; a que amplia
   ganhou, Paper E).
4. **Reparo contra a evidência ("dreaming")** — só com consumidor: o B2 mostrou que o ganho é quase todo
   filtragem (0,913 → 0,990) e que reescrever troca fato certo por outro (retenção 0,650).

### CONGELADO até haver consumidor real buscando

Extração LLM do KG (#4), latência/cache de embedding (#6), rebaixar por retenção (#5), procedimental (#10),
R1 (brief por recência), qualquer knob de ranking (rerank, temporal, KG no ranking, multi-query). Gatilho de
reabertura único: **o relatório de 15/11 ou o B2 mostrar buscas reais**.

### CORTAR (proposta de entrada no NÃO FAZEMOS)

P4 `nox-mem connect`, P6 mobile, P7 extensão de navegador, E15, os dois benchmarks por método, profile-chunk:
nenhum tem demanda medida nem consumidor. Desligar o shadow do R1. Tirar "pain-weighted" do slogan como
diferencial de ranking: o único efeito medido é +0,0065 n.s. (o pain continua como sinal de saliência; o que
sai é a promessa).

## 3. Novo índice: uma porta por pergunta

| pergunta | arquivo | muda o quê |
|---|---|---|
| o que o produto entrega hoje | `docs/ROADMAP.md` §2 | tabela npm × produção vira a verdade única, reconferida a cada release |
| o que vem e em que ordem | `docs/ROADMAP.md` §3 | esta fila (Agora / Próximo / Pesquisa / Congelado / Cortar) |
| por que cada não | `docs/DECISIONS.md` §1 | entram os cortes da §2 acima |
| estado de cada spec | `specs/INDEX.md` | já regerado em 08/11 por estado verificado |
| papers | `PLANO.md` | inalterado; ganha a linha 1 e 3 da Pesquisa acima |
| estado vivo | `docs/HANDOFF.md` | — |
| `CLAUDE.md` | regras operacionais | a seção "Estado atual" (números de maio) sai e vira ponteiro para o ROADMAP §2 |

## 4. Decisões que dependem de você

1. `compact` no npm: **remover do CLI** ou **travar com `--destructive`**?
2. Shadow do C2: **publicar a tag do pré-registro (#673)** agora?
3. C2 como **opção** no `session-distill` do npm, padrão inalterado?
4. L4: **remover** (recomendado) ou **ligar e medir**?
5. Lista do que fica **só em produção** (L2, P5, hooks, OCR, A2 por HTTP) e portar o A3 para produção?
6. Os **cortes** da §2 entram no NÃO FAZEMOS?
7. **Pricing**: Stripe-first (D44b) ou Hotmart? E data-alvo do lançamento?
8. Histórico do repo com trechos do corpus privado: **aceitar** ou **reescrever** (custo: hashes citados nos
   pré-registros e links `tree/<hash>` dos papers mudam)?

## 5. O que esta proposta não resolve

- **Demanda externa não medida.** Os sinais do campo (memória que envelhece em silêncio, custo de tokens da
  memória injetada, portabilidade, agente que não consulta) vêm de fontes secundárias; não lemos issues de
  Mem0, Letta ou Zep.
- **Paper 1 / TMLR**: estado da conta OpenReview desconhecido desde 30/09.
- Os números de produção do item 0.1 e 0.2 repousam em 99 perguntas de um corpus; servem para ordenar, não
  para afirmar em público sem o intervalo.
