# Próximos passos — Paper 2

> ⚠️ **REESCRITO 2026-09-21 — pela TERCEIRA vez pelo mesmo motivo.** A versão de 01/09
> declarava *"O próximo passo: **registrar no OSF**"*, e o registro `yf7d2` existia desde
> **2026-08-18T07:56:44Z** (`OSF-SUBMISSION.md`) — onze dias **antes**. Não envelheceu:
> nasceu errado. As duas reescritas anteriores (15/08 e 01/09) foram pelo mesmo defeito —
> o documento afirmando o oposto do estado real. Histórico: `git log -- NEXT-STEPS.md`.
>
> 🔑 **A lição que a terceira repetição impõe:** este documento não deve reafirmar estado
> que vive noutro lugar. O estado do depósito está em `OSF-SUBMISSION.md`; o do ensaio,
> em `DEVIATIONS-FOR-PAPER.md`; o do manuscrito, na lista dele. Aqui fica **só a ordem**,
> com ponteiro para quem sabe.

## Onde estamos — 2026-09-21

| frente | estado | fonte da verdade |
|---|---|---|
| pré-registro | ✅ OSF `yf7d2` (18/08) + Zenodo v1.12 `10.5281/zenodo.22110203` | `OSF-SUBMISSION.md` |
| **ensaio interventivo** | ✅ **CORRIDO E FECHADO** — 01/09 10:25:39Z a 20/09; 20 epochs designados, 19 servidos | `DEVIATIONS-FOR-PAPER.md` §10.29 |
| **análise ITT** | ✅ **FECHADA 21/09** — 7/7 reportáveis do `SPEC-ANALISE-2026-09-10 §6` | `DEVIATIONS` §10.32–§10.34 |
| Paper A (superfície) | manuscrito completo; faltam revisão adversarial, varredura de frases envelhecidas e depósito | lista no fim de `MANUSCRIPT.md` |
| **Paper B (interventivo)** | ❌ **não existe como documento** | — |

**Resultado principal do ensaio:** H1c dá −0,0199 (IC95 [−0,0560; +0,0086]) — **não
detectável**, como o §3 da spec previa com MDE saturado. H1b é **inavaliável** por colisão
de locks. H1 exclui zero mas foi rebaixada de primária em 30/08 por exigir 955% de efeito.

## O próximo passo, e por que é este

**Escrever o Paper B.** O split de 28/08 decidiu que o interventivo é trabalho próprio, e
a medição dele acabou em 21/09 — os números existem, verificados, e vivem hoje num log de
desvios, que não é onde um resultado se publica. Tudo o mais está feito ou depende disto.

⚠️ **O Paper B não pode ser escrito a partir deste documento nem de memória.** A matéria
é `DEVIATIONS-FOR-PAPER.md` §10.29–§10.34 e a `SPEC-ANALISE-2026-09-10`, que pré-comprometeu
o que é reportável — inclusive as pernas de sensibilidade, declaradas dez dias antes do
fecho da janela. Escolher o conjunto primário depois de ver número é a jogada que aquela
spec existe para impedir.

---

<details>
<summary>Histórico — o texto de 01/09, preservado</summary>

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


</details>
