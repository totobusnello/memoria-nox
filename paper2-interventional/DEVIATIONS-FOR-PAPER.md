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
`yf7d2`) afirma coisas **falsas** — e, em **duas** linhas, está *pior* que a realidade
(seta ⬇). Atualizado 27/08 com o replay do pipeline real:

| o registro diz | o que se mediu | |
|---|---|---|
| `Δ_cut = 0,043` é *"the measured salience spread at the brief cut"* | não existe cut: o código não aplica limiar. O comparador é lexicográfico e `salience` só desempata `last_served` idêntico | ⬆ |
| a banda `{2,0 · 4,0 · 7,5}` está entre *"what does not move, and could not"* | **move**: 11 / 15 / 17 estados de 350, monótono. A unidade segue sem referente registrado, mas a banda **não** é vazia — e sua dose superior está **acima** da saturação, que fica em `(4,0 ; 4,4]` | ⬇ |
| a alocação é `117/39/39/39` | suspensa junto com a banda — e a razão de suspender mudou: não é que as doses sejam indistinguíveis, é que a escala não tem referente | ⬆ |
| *(v1.12 §5)* a designação é defeito **aberto** | **fechada** em 26/08 20:28Z, com precedência verificável de 1.056 s | ⬇ |

⚠️ **As duas linhas ⬇ são as que mais incomodam,** e são as que o tempo não conserta.
As ⬆ superestimam o desenho: quem ler vai achar o estudo mais forte do que é, e a
correção só melhora a percepção do rigor. As ⬇ fazem o contrário — o registro afirma
que o parâmetro não tem efeito quando tem, e que um defeito está aberto quando foi
fechado. Quem ler daqui a um ano vai acreditar nas duas.

⚠️ E a linha da banda mudou de status **por causa de um defeito de instrumento meu**,
não por dado novo: o controle positivo que produziu o "não move" rodava sobre um pool
reimplementado. Isso é matéria do §5, não nota de rodapé.

## O que o paper tem de carregar

Fonte integral: `AMENDMENT-DRAFT-band-collapse-2026-08-26.md` (retratações 29–44) e
`REMEDIATION-2026-08-27.md`. O resumo abaixo é índice, não substituto.

### 1. O achado estrutural — 🔴 PARCIALMENTE REVERTIDO em 27/08

> ⚠️ **O que estava escrito aqui vinha de um controle positivo rodado sobre um pool
> REIMPLEMENTADO.** O replay do pipeline real
> (`REPLAY-OPORTUNIDADE-2026-08-27.md`, fidelidade 350/350 contra a produção)
> mediu o contrário em três pontos. O texto original fica abaixo, riscado, porque
> retratação apagada não é retratação.

**O que sobrevive, e é dedutivo:** o boost é aditivo em `salience`, a coordenada
**subordinada** de um comparador lexicográfico — quando `last_served` difere,
`salience` nunca é consultada. Isso é verdade, é o que produz a **saturação**, e é
o que impede o parâmetro de ter alcance ilimitado.

**O que cai:**

| ~~o registro e a emenda dizem~~ | medido no pipeline real (9 doses × 350 estados) |
|---|---|
| ~~`w = 100.000` dá `churn` **0**~~ | churn **20**, em **17 de 350** estados |
| ~~"o parâmetro não está na coordenada que decide"~~ | decide **dentro** do estrato — e é lá que a medida de desfecho vive |
| ~~as duas doses superiores são "indistinguíveis por construção do dado"~~ | `2,0 → 11`, `4,0 → 15`, `7,5 → 17` estados: **distinguíveis** |

A resposta é **monótona** — e monótona em cada um dos 350 estados, não só no
agregado (0 → 5 → 8 → 11 → 15 → 17 estados para `w = 0 / 0,5 / 1 / 2 / 4 / 7,5`) —
e **satura**. O teto do canal é **17/350 = 4,86%**. E `w = 2` reproduz o
`11/350 = 3,1429%` publicado: o replay é fiel também no agregado.

⚠️ **O ponto de saturação está em `(4,0 ; 4,4]`, não em 7,5.** Com grid de 23 doses
sobre os 17 estados, o maior limiar individual é `w_min = 4,4` (mediana 1,7, mínimo
0,02 — espalhamento de 220×). O "7,5" era o ponto seguinte de um grid grosso, e a
aparente coincidência com o topo da banda registrada era o instrumento, não o
sistema. **A banda registrada tem, portanto, a dose superior ACIMA da saturação** —
`7,5` e qualquer valor maior são indistinguíveis entre si, mas `4,0` e `7,5`
continuam distinguíveis (15 vs 17 estados).

⚠️ **Isto é a segunda linha em que o registro público está PIOR que a realidade** —
afirma que o parâmetro não tem efeito quando tem. Como a designação (§2), não se
conserta com o tempo: quem ler vai supor que o canal é vazio.

**A quantidade de gap intra-estrato segue publicada e foi CONFIRMADA** — 38 pares
adjacentes, 11 zeros, 27 positivos, máximo 0,031808734967844865, reproduzidos exatos
pela harness nova. Mas o paper **não pode** usá-la para argumentar sobre a banda, por
duas razões medidas em 27/08:

1. aquele máximo é da coluna **filtrada** (só pares em que ao menos um chunk é do
   estudo). Sem filtro, no mesmo pool e instante, é **0,05272**. O boost move o
   designado para além de quem estiver acima dele, seja do estudo ou não;
2. e nenhuma das duas colunas **cota** o mecanismo: o maior `w_min` (4,4) vale boost
   `0,0946` em S1, **1,79×** o maior passo adjacente do pool. A grandeza que governa é
   a **distância** até os 2 slots de cobertura, não o **passo** até o vizinho.

⚠️ E a hipótese de que os gaps maiores viessem do sub-pool do **agente** está
**refutada**: em `T_REF` o sub-pool do agente é **vazio** — 265/6.001/3.011 chunks de
`sessions/<agente>/%` passam o piso de importance e **zero** passam a janela de 7 dias.
`interleaveFresh([], global) === global`: todo o canal é o sub-pool global. Isso é fato
sobre aquele instante, e uma rajada de sessões muda a composição do canal sob os pés do
estudo — o que o paper tem de declarar como ameaça.

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

- ✅ **FECHADO 27/08 — oportunidade agora corresponde ao pipeline.**
  `measurement/replay-oportunidade.mjs` importa `buildBriefDiverse` do `dist` e
  reproduz a produção em **350 de 350** briefs da janela fechada (composição do
  controle, `churn`, `would_enter`, `would_leave`; zero inventado, zero perdido).
  Os `5/44` grupos qualificáveis seguem **não** sendo a oportunidade do código —
  a do código é `11/350` em `w = 2` e tem teto de `17/350`. Detalhe em
  `REPLAY-OPORTUNIDADE-2026-08-27.md`.
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
- **no serving, `julianday('now')` decide a população elegível** apesar de a função
  receber `nowMs` por argumento: o brief não é função pura de (corpus, serve-state,
  `nowMs`);
- **`brief_log.served_at` tem resolução de segundo** e 46,9% dos briefs dividem o segundo
  com outro. Nenhum corte temporal reproduz o estado; sob corte estrito o replay inventa
  churn 3× e perde 1×, e a contagem de desfecho sai **14 em vez de 12**. O corte tem de
  ser por `brief_log.id` (`AUTOINCREMENT`);
- **`ordenarCobertura` descarta `lastServedMs` do que devolve**, então agrupar pela chave
  que ordenou o pool dá um grupo só, em silêncio;
- **o controle positivo publicado media o instrumento, não o sistema** — e produziu o
  número que virou a retratação central. Ver §1;
- **grid grosso produziu um ponto de saturação neat demais.** Um salto de `w = 4` para
  `7,5` fez a saturação *parecer* cair exatamente no topo da banda registrada. Com 23
  doses ela está em `(4,0 ; 4,4]`. Eu sinalizei a coincidência como suspeita antes de
  saber a razão, e a razão era a mais chata possível: resolução do meu grid;
- **o gatilho de saturação do item 7 vigia a grandeza errada.** Foi calibrado sobre gap
  entre **adjacentes** (`0,0318`, "margem 1,35× contra `Δ_cut`"), mas o mecanismo exige
  vencer a **distância** até os 2 slots de cobertura: o maior `w_min` observado vale
  1,79× o maior passo adjacente do pool. O gatilho pode ficar verde enquanto o canal
  satura;
- **a composição do canal não está vigiada por nada.** O sub-pool do agente está vazio
  por idade em `T_REF`; se voltar a encher, `interleaveFresh` deixa de ser função-zero e
  a escala de dose muda sem que nenhum alarme dispare.

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
