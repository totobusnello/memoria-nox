# Desvios a reportar no paper — a obrigação que substitui a emenda

> **Decisão do Toto, 2026-08-27T16:52 BRT: não emendar o registro por enquanto.** O
> pré-registro fica **como registrado**, e todo desvio é declarado no paper.
>
> Este arquivo existe porque essa escolha só é honesta se a obrigação sobreviver até o
> paper ser escrito. Em 27/08 não havia manuscrito do Paper 2 nem documento de desvios:
> a obrigação não tinha onde morar. Uma decisão de "reportar depois" sem lugar onde
> ficar registrada é uma decisão de **não reportar**, com atraso.

## O custo aceito, dito sem eufemismo

Enquanto isto não for reportado, o registro público (`10.5281/zenodo.22110203` e OSF
`yf7d2`) afirma três coisas **falsas** e uma **desatualizada**:

| o registro diz | o que se mediu |
|---|---|
| `Δ_cut = 0,043` é *"the measured salience spread at the brief cut"* | não existe cut: o código não aplica limiar. O comparador é lexicográfico e `salience` só desempata `last_served` idêntico |
| a banda `{2,0 · 4,0 · 7,5}` está entre *"what does not move, and could not"* | não é escala calibrada de dose — a unidade em que está expressa não tem referente registrado |
| a alocação é `117/39/39/39` | suspensa junto com a banda |
| *(v1.12 §5)* a designação é defeito **aberto** | **fechada** em 26/08 20:28Z, com precedência verificável de 1.056 s |

⚠️ **A quarta linha é a que mais incomoda:** é a única em que o registro está *pior* que
a realidade. As três primeiras superestimam o desenho; esta subestima o que já foi
consertado, e some sozinha se o paper demorar — porque quem ler vai supor que o defeito
segue aberto.

## O que o paper tem de carregar

Fonte integral: `AMENDMENT-DRAFT-band-collapse-2026-08-26.md` (retratações 29–44) e
`REMEDIATION-2026-08-27.md`. O resumo abaixo é índice, não substituto.

### 1. O achado estrutural, que é dedutivo

`W_OUTCOME = w · Δ_cut · severidade` não define escala de dose. O boost é aditivo em
`salience`, a coordenada **subordinada** de um comparador lexicográfico: quando
`last_served` difere, `salience` nunca é consultada. Controle positivo com `w = 100.000`
dá `churn` **0** com os 19 boosts emitidos — dose absurda sem efeito não é ruído, é
prova de que o parâmetro não está na coordenada que decide.

A quantidade que existe é o **gap de `salience` dentro de estratos de `last_served`
idêntico**: 38 pares adjacentes, 11 exatamente zero, 27 positivos, máximo
0,031808734967844865. A banda mapeia em `{16, 27, 27}` de 27, e o menor `w` que vence
todos em S1 é **2,9590** — logo as duas doses superiores são indistinguíveis por
construção do dado, não por falta de n.

### 2. O que a designação fechou, e como

Sorteio com seed declarada: drand quicknet **31657512** (emissão 20:25:00Z), declaração
pushada **20:07:24Z** — **1.056 s** de precedência, com a rodada devolvendo HTTP 425 na
escrita, e o frame de 55 linhas depositado **antes** da aleatoriedade existir. Um
revisor independente rederivou os 19 designados só com o beacon público e o CSV.

⚠️ **A precedência não depende do depósito** — está no timestamp do GitHub e na rodada
drand. Adiar o registro não a enfraquece. Foi isso que tornou a opção 2 viável.

### 3. As comparações que NÃO identificam nada, e por quê

Na janela fechada `[2026-08-26T20:28:00Z , 2026-08-27T09:00:00Z)`: **11/350 = 3,1429%**
(Wilson [1,76; 5,54]). Último dia da regra anterior: 20/574 = 3,4843%.

| comparação | diferença | Fisher | uso |
|---|---|---|---|
| contra o agregado pós-gate (132/2.226) | −2,79 pp | **p = 0,0326** | ⛔ **não usar** — mede composição de dias |
| contra o último dia | −0,34 pp | p = 0,8523 | a defensável, e subpotente (~7%) |

A série anterior é declinante (13,64% → 7,29% → 3,13% → 3,48%) e 23+24/08 concentram
**69% dos eventos em 44% do n**. A "redução significativa" vem inteira de incluir os
dois primeiros dias. **O paper não pode reportar a agregada como efeito**, e a adjacente
não estabelece aumento, redução nem equivalência.

### 4. Os defeitos que ficam abertos

- **Oportunidade não corresponde ao pipeline.** Nada aqui faz replay de
  `interleaveFresh`, `pickDedup`, `pinned`, near-dup ou o corte do `LIMIT 400`. Mede-se
  **ordenação**, não **seleção**. Os `5/44` grupos qualificáveis não medem a
  oportunidade do código e não sustentam `N`, poder nem estimando.
- **Auto-extinção NÃO testada.** A série reconstruída é toda anterior ao tratamento.
- **`last_served` não é congelado pelo snapshot de epoch** e realimenta: o tratamento em
  `T` altera a estrutura de grupos em `T+1`. Interage com a **F1** (carry-over).
- **Nada é randomizado.** Toda comparação é antes/depois.

### 5. Os defeitos de instrumento — e reportá-los é parte do método

O paper perde a contribuição declarada se omitir isto, porque a contribuição **é o
método**:

- a "descontaminação" fazia rollback temporal: 3.735 linhas removidas para excluir 25;
- eram **cinco** sondas e 25 linhas, não três e 15 — duas delas 55 s depois de o
  mecanismo subir, porque **verificavam** que ele subira;
- `julianday('now')` em três scripts fazia a população elegível mudar a cada execução;
- uma janela ficou **aberta** por cima e o `11/310` publicado envelheceu para 359;
- um commit citado (`0087c918`) **não existia**: o nome morreu numa reconciliação de
  histórico enquanto o conteúdo sobreviveu;
- duas correções que a revisão adversarial me levou a propor estavam **erradas**, e o
  rascunho certo — vinham do rollback, não da exclusão das sondas.

### 6. Procedência, para o paper não repetir o erro que descreve

Toda medição citada precisa de **`T_REF` + caminho do snapshot de corpus + janela
fechada**, e de reprodução de âncora publicada antes de variar qualquer coisa. Sem os
três, a tabela envelhece para falsa — foi o que aconteceu duas vezes aqui.

## Se a decisão mudar

A máquina do depósito está pronta e **não executada**: `deposit/PLAN-v1.13.md` e
`deposit/deposit-v1.13.sh` (99 arquivos, 45 uploads, três gates passando, readback
duplo). Nada foi enviado ao Zenodo. Voltar para a opção 1 (depositar) ou 3 (agrupar com
o protocolo prospectivo) custa o token e um `prepare`.

⚠️ Se o depósito acontecer meses depois, **reconferir os 6 arquivos substituídos por
md5 antes do `prepare`** — `claims_check.py` e a emenda continuarão recebendo edições, e
o `sync` só corrige o que sabe comparar.
