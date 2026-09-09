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
  satura. *Substituído 27/08 por uma identidade — `churn(w_servido) == churn(w_absurdo)` —
  e estendido a `active` em 28/08, quando a dose passa a vir do `ASSIGNMENT.json`;*
- **um gatilho de braço único não distingue controle sorteado de resolução falhada.**
  `resolverBraco` devolve controle em *toda* falha, por desenho — o que é a escolha
  certa para servir e a errada para vigiar: enviesa o estudo para o nulo e não deixa
  rastro. Só se resolve **cruzando** o `ASSIGNMENT` com o log de serving, e essa
  conferência não existia até 28/08;
- **a composição do canal não está vigiada por nada.** O sub-pool do agente está vazio
  por idade em `T_REF`; se voltar a encher, `interleaveFresh` deixa de ser função-zero e
  a escala de dose muda sem que nenhum alarme dispare.

### 6. Procedência, para o paper não repetir o erro que descreve

Toda medição citada precisa de **`T_REF` + caminho do snapshot de corpus + janela
fechada**, e de reprodução de âncora publicada antes de variar qualquer coisa. Sem os
três, a tabela envelhece para falsa — foi o que aconteceu duas vezes aqui.

### 7. Alegações retiradas em 2026-08-29, e por quê

Três, todas no Paper A (o diagnóstico observacional), todas achadas por revisão
adversarial ou por recomputar o que estava em prosa. **Nenhuma foi retirada por ter sido
refutada por dado novo** — as três foram retiradas por *não estarem estabelecidas pelo
dado que existia*, que é uma classe diferente e mais incômoda.

| alegação retirada | por quê | o que ficou no lugar |
|---|---|---|
| `β = −0,961 ⇒ ×0,38 por década de tamanho` | o eixo de tamanho tem um vazio: **zero** tipos entre n=53 e n=1.046, 32,1% da amplitude sem um único ponto. "Por década" convida à leitura pontual numa faixa sem observação | o contraste entre as duas nuvens — 5 tipos grandes em 10,7–27,0%, 8 dos 10 pequenos acima de 32,5% |
| "o teste **separa** curadoria de tamanho" (§4.2) | não separa. As parciais controlam idade, importância média e comprimento de texto; **nenhuma é curadoria**, e o corpus não tem variável que a meça | declaração explícita de que os dois seguem confundidos por construção |
| "8.928 fragmentos de sessão de **205** caracteres" | os 205 são a média de **todos os 14.456 `distilled` do corpus**, não a dos 8.928 que a frase nomeia — que é **232**. Número certo, população errada | o número do subconjunto, com a população nomeada e artefato |

⚠️ **A terceira merece nota de método**, porque é a que o paper descreve acontecendo com
outros: a frase vinha de consulta *ad hoc* de 27/08 que não deixou artefato, e sobreviveu
a três revisões adversariais — nenhuma das quais tinha como recomputá-la. Só apareceu
quando o número virou script, dois dias depois, por outro motivo. **Prosa que afirma
resultado calculado é cache sem invalidação**, e a demonstração é esta.

Em contrapartida, uma alegação foi **promovida** no mesmo dia, e o desvio é simétrico:
"dos 13.388 chunks que passam o piso de relevância do próprio sistema, 10.008 = 74,75%
nunca foram expostos" estava enterrada num aviso e virou co-manchete do §4.1. A objeção
que a motivou (a taxa é incondicional; chunks jovens não tiveram oportunidade) foi medida
e **aponta para o lado oposto**: a coorte com oportunidade máxima é a mais não-exposta.
Corrigir pela censura temporal aumentaria a taxa reportada.

### 8. Uma afirmação de completude falsa no manifesto da v1.12 (achada em 30/08)

`SERVING-CODE-MANIFEST.md` argumenta — corretamente — que hash de commit não sobrevive
a uma reconciliação de histórico, e conclui: *"é por isso que **toda linha acima**
carrega o sha256 dos bytes do arquivo — esse pino sobrevive a qualquer reescrita, e é o
que um leitor pode conferir contra o blob depositado sem acesso ao repositório
privado."*

**Três das seis linhas não carregavam sha256.** As da segunda tabela traziam só o hash
de commit — o pino que o próprio parágrafo acabara de declarar instável. O leitor que
aceitasse a promessa e fosse conferir `serving-brief-diversity.ts` contra o blob
depositado não teria contra o que conferir, e precisaria exatamente do acesso que a
frase promete dispensar.

O arquivo mais exposto pela lacuna é o mais citado: `serving-brief-diversity.ts` carrega
o `DIVERSITY_DEFAULTS`, de onde sai o piso 0,7/0,7 de uma das duas manchetes.

**Remediação, sem tocar no registro.** Os três `sha256` foram computados sobre os blobs
da tag `paper2-v1.12` — byte a byte idênticos aos arquivos em disco, conferido por
`git show paper2-v1.12:… | shasum -a 256` — e acrescentados ao manifesto no repositório:

| arquivo | bytes | sha256 |
|---|---|---|
| `serving-brief-diversity.ts` | 8712 | `34c9aee5f80311c8aff5c0ae35f37dd6dbf52f31a9f940b01cdb8d205c69e7a2` |
| `serving-salience.ts` | 12553 | `083399fc190920ff8f2a590bd74876e25b1f95552515977920edb64025924684` |
| `serving-search.ts` | 29622 | `d76034e2b7796744ae5836af02c5a1155ddc5750f0fa2d94875f63b9b1b723d3` |

A v1.12 depositada permanece como está. Os valores acima pinam os mesmos bytes, então
quem for conferir o depósito consegue.

⚠️ **Por que nenhuma das seis revisões adversariais pegou.** Todas leram o parágrafo
como argumento, e o argumento está certo — hash de commit realmente não é pino estável.
O defeito não estava na tese, e sim no **alcance do quantificador**: "toda linha acima"
foi escrito olhando a primeira tabela e passou a quantificar as duas. É uma classe que
revisão não vê, porque exige contar linhas de tabela contra uma palavra, e nova para
este catálogo: as anteriores eram rótulo divergindo do predicado, não quantificador
divergindo do escopo.

### 9. O corpus congelado do Paper 2 não existe — e os episódios adjudicados também não

`CORPUS-FREEZE.md` declara que a reprodução roda contra
`action-archive-20260729T094609Z.tar.gz` (107 MB, 5.547 episódios, `sha256 ba5fcc81…`),
em `/var/backups/nox-mem/paper2-corpus/` com modo `0400`, e afirma: *"quem reproduzir a
partir deste snapshot obtém 5.547 episódios"*.

Procurado em 2026-08-30 por **nome**, por **tamanho** (~107 MB) e por **`sha256`** em
toda a máquina de serving: não existe, e o diretório também não.

🔴 **E a consequência é maior que a perda de reprodutibilidade:** dos **280** episódios
adjudicados em `p2_verdict`, **zero** estão no archive vivo. O painel julgou 280
episódios que hoje ninguém pode ler. As 55 lições e os 19 grupos de designação existem
como veredito sem evidência — `sig_primary`, `severity` e `chunk_id` sobreviveram na
tabela; o material que os justificava, não.

**O que sobreviveu:** a `sig()`. `extract_episodes.py` tem `sha256 e860357bd9f1fc06…`,
idêntico ao congelado no pré-registro. A taxonomia é reproduzível; o corpus sobre o qual
foi derivada, e o material que o painel viu, não são.

⚠️ **Por que isto entra no paper e não numa nota operacional.** É a **terceira** ocorrência
da mesma classe em três dias — o corpus do teto (rotacionado, §5.7.2), os três `.ts`
pinados por hash de commit (recuperados, §8) e este. Um paper cuja tese metodológica é
que a verificação precisa ser mecânica não pode omitir que a sua própria disciplina de
congelamento falhou três vezes, e sempre do mesmo modo: **pinar o identificador de um
artefato não o preserva**. A regra que sai disto, e que vale para todo depósito futuro, é
depositar o **blob**, não o hash.

### 10. O Epoch 1 é heterogêneo, e o braço de controle não deixa rastro (2026-09-01/03)

Dois desvios que só apareceram com o ensaio no ar. O primeiro é de execução; o segundo
é de instrumento e o mais consequente dos dois.

#### 10.1 O Epoch 1 tem 42 briefs servidos como CONTROLE dentro de um epoch de tratamento

A fronteira do epoch é **09:00 UTC** (`epochInicioISO`, `brief-outcome.ts`), e a
ativação aconteceu às **10:25:39Z** — uma hora e vinte e cinco minutos depois de o
epoch abrir. Nesse intervalo o serving ainda estava em `shadow`, e os briefs foram
servidos como controle. Medido no log:

| epoch | n | modo | w | servido |
|---|---:|---|---|---|
| 2026-08-29 | 672 | `shadow` 672 | 2 | controle 672 |
| 2026-08-30 | 672 | `shadow` 672 | 2 | controle 672 |
| 2026-08-31 | 672 | `shadow` 672 | 2 | controle 672 |
| **2026-09-01** | **672** | **`shadow` 42 · `active` 630** | **2 e 4** | **controle 42 · tratado 630** |

**6,25% do Epoch 1 recebeu o braço errado.** O gatilho `p2-saturacao-da-dose` acusou
corretamente em 09-02 09:12Z: `modo-no-log=['active','shadow'] != active`.

⚠️ **A ativação não foi tardia por descuido — foi adiada de propósito, e o adiamento
evitou um defeito pior.** Às 07:08Z o epoch corrente era `2026-08-31`, data ausente da
sequência de atribuição; ligar ali faria `resolverBraco` devolver
`epoch ... ausente da sequência` e servir controle em **todo** brief por 1h52, com
`systemctl is-active` dizendo `active`. Esperar até depois das 09:00Z era o certo. O que
faltou foi ligar **na** fronteira, não depois dela.

##### A escolha de análise, FECHADA em 2026-09-04 sem que desfecho algum fosse consultado

> **Precedência.** Decidido em **2026-09-04**, com o ensaio no seu quarto epoch. Nenhum
> desfecho foi computado, consultado ou estimado antes desta decisão — nem por mim nem a
> pedido meu. O que foi medido para decidir é **exclusivamente estrutura de exposição**:
> quantos briefs, em que braço, em que instante, lidos do log de serving. A densidade de
> falhas repetidas, que é o desfecho, não foi tocada. Quem auditar pode conferir pelo
> `git log` que este parágrafo antecede qualquer artefato de desfecho no repositório.

✅ **A decisão usa a estrutura que o registro JÁ tem, em vez de criar uma paralela.**
`PREREG-DRAFT.md` §"Mandatory ITT co-estimate" determina que *"the primary is reported
alongside an intention-to-treat estimate over all post-washout epochs with no coverage
exclusion whatsoever. Agreement between the two is the strength of the claim; divergence
is reported as-is and is not adjudicated in favour of either."* A disciplina de reportar
duas análises, tratar concordância como força e divergência como achado não-adjudicado,
portanto, **é registrada, não inventada agora**.

> ⚠️ A primeira redação desta seção dizia "primária: ITT", o que **renomeava** a
> estrutura registrada — ali o *primary* é distinto do co-estimador ITT. Corrigido no
> mesmo dia, ao reler o §1042. Registrado porque descrever errado o próprio plano de
> análise é o defeito que este documento existe para não cometer.

**A decisão, então, é de inclusão e não de estrutura:** o Epoch 1 **não é excluído** nem
do *primary* nem do co-estimador ITT. Os seus 672 briefs entram no braço `w = 4,0`
conforme designado, incluindo os 42 servidos como controle.

**Acrescenta-se uma terceira análise, pré-especificada aqui:** o mesmo par de estimativas
com o Epoch 1 excluído, reportado sob a mesma regra do §1042 — concordância é força,
divergência é reportada como está e não é adjudicada a favor de nenhuma das duas.

**Por que ITT e não descartar.** O custo estatístico de descartar é desprezível — a
alocação é `117/39/39/39`, o Epoch 1 é `w = 4,0`, logo seria 1 de 39, e com o *design
effect* de 21,9 (ICC 0,0985) o epoch é a unidade efetiva: o erro-padrão inflaria
`√(39/38)` = **1,3%**. A decisão, portanto, **não é sobre poder**.

O que decide é outra coisa: a lista registrada de eventos intercorrentes tem **três**
entradas — epochs anulados pela regra de aborto, *downtime* da frota, e epochs sobrepostos
a intervenção manual de memória em `ops_audit` (PREREG §5). **Contaminação parcial de
braço não está entre elas.** Descartar o Epoch 1 significaria criar critério de exclusão
novo com o ensaio já em curso, que é precisamente o grau de liberdade que o pré-registro
existe para eliminar. Pagar 1,3% de intervalo por manter a lista intacta é troca boa.

E a direção do viés é conhecida: 6,25% de um epoch de tratamento recebeu controle, o que
**atenua** a diferença medida. Se houver efeito, a contaminação não o fabricou; se não
houver, ela está declarada entre as razões. ITT é conservadora nas duas pontas — e é por
isso que a sensibilidade importa: se as duas análises concordam, a contaminação é
irrelevante e isso fica demonstrado; se divergem, a divergência é o achado, e foi
pré-especificada antes de ser vista.

**Por que os 42 não são reatribuídos ao controle.** Seria análise *per-protocol*, e
quebraria a randomização: esses 42 não são um subconjunto aleatório do controle, são a
primeira hora e meia de um dia específico. A designação do braço vem do sorteio, não do
que o serving fez.

⚠️ **O epoch contaminado não está no braço que carrega a hipótese principal.** `w = 4,0`
é a dose intermediária; a condição de detectabilidade (§2 do registro prospectivo) mostra
que a dose que testa H1 é `w = 2,0`, onde apenas **3,14%** dos briefs mudam de composição.
Isso enfraquece ainda mais o caso para descartar, e é observação de desenho, não de
resultado.

**Para os 233 epochs restantes o problema não se repete:** a transição de modo já
aconteceu e não há outra prevista. Um reinício do serviço no meio de um epoch **não**
recria o defeito — o modo vem do drop-in e a designação do `ASSIGNMENT-SERVING.json`.

#### 10.2 O braço de controle não produz nenhuma linha de log

Os epochs `2026-09-02` e `2026-09-03` são `control`/`w=0` por sorteio, e o log de
serving não tem **uma única linha** deles. Não é falha: é o que o código faz.

```ts
if (provedorDeBoost && cfg.freshSlots > 0) { … altBoosted = … }   // brief.ts:836
if (logDiff && diffP2 && altBoosted) { logarDecisaoDeServing({…}) }   // brief.ts:980
```

Sem boost não há `provedorDeBoost`; sem ele não há `altBoosted`; sem `altBoosted` não há
linha. Consequências, em ordem de gravidade:

1. **o `n` do braço de controle não é observável** — 117 dos 234 epochs são controle, e
   nenhum deles deixa registro de quantos briefs serviu;
2. **não se pode auditar que o controle foi servido corretamente** — a ausência de linha
   é compatível com "serviu controle como devia" e com "não serviu nada";
3. **"epoch de controle" é indistinguível de "serving parado"** — foi a primeira leitura
   ao ver o log parar em 09-02T08:52Z, e foram necessárias três medições para descartar.

É a mesma classe da regra 9 do `CLAUDE.md`: o gatilho que mede a janela precisa do dado,
e o dado não existe em controle.

⚠️ **O crédito de o silêncio não ter sido total é do `YELLOW n=0`.** O gatilho tem uma
perna que alarma quando a janela vem vazia — `janela-com-n-insuficiente n=0 minimo=30`,
disparada em 09-03 09:12Z. Sem ela, 117 epochs de controle passariam calados e o silêncio
pareceria saúde.

**Correção classificada como instrumentação, não emenda**, e a razão é verificável: a
linha nova registra o que **já** é servido, não altera designação, dose, ordenação nem
composição. Nenhum braço muda de conteúdo. O que muda é haver registro do que antes não
tinha. Declarado aqui em vez de emendado no registro, pela decisão do item 7.

#### 10.3 O morning report lê um status escrito 21 horas antes

`morning-report.sh` roda **06:30** e `run-saturacao.sh` roda **09:12**. O report de um
dia lê o status gravado às 09:12 do dia **anterior** — o RED de 09-02 apareceu no report
de 09-03, quando o estado corrente já era YELLOW. Não é dado errado, é dado velho
apresentado como corrente, que na prática dá no mesmo para quem lê o alerta.

#### 10.4 O gatilho de saturação descartava exatamente os briefs em que a dose mordeu

Nos dois primeiros epochs de tratamento medidos em `active`, o gatilho `p2-saturacao-da-dose`
reportou **RED `dose-servida-inerte: nenhum estado se move`**. Os dois vereditos ficam
preservados aqui com a procedência de cada janela, porque o que este item registra é um
alarme **diagnosticado**, não um alarme silenciado:

| epoch | janela | `sha256` do recorte | `n_janela` | `estados` | `mexem_servido` | `mexem_absurdo` |
|---|---|---|---|---|---|---|
| 2026-09-04 | `[09-04T09:00Z, 09-05T09:00Z)` | `64da3be2…20d59e` | 672 | 638 | 0 | 11 |
| 2026-09-05 | `[09-05T09:00Z, 09-06T09:00Z)` | `a17ceafd…d84c7027` | 672 | 640 | 0 | 14 |

**A leitura natural — e errada — é "a dose servida saturou".** O log de serving, que é
independente do replay, diz o contrário na mesma janela: no epoch de controle `w = 0`,
**0 de 441** briefs têm `churn > 0`; nos dois de tratamento `w = 2,0`, **35 de 672** e
**33 de 672**.

**Causa raiz.** O replay localiza cada brief no `brief_log` pela assinatura
`(agente, segundo, conjunto dos 10 `chunk_id`)`, e a assinatura que ele usa é
`ids_controle` (`replay-oportunidade.mjs:549`). Em `active`/tratamento o conjunto
**servido** é o **tratado**. Logo, em todo brief no qual o boost mudou a composição, a
assinatura procurada não existe no `brief_log`: `cands.length === 0`, o item vira `erro`
e o `continue` de `:561` o remove **antes** do laço de doses (`:622`). Na agregação, itens
com `erro` não entram no `estados` da tabela.

Medido sobre a janela do epoch 09-05, casando o `brief_log` inteiro da janela em memória:

| grupo | n | casa por `ids_controle` | casa por `ids_tratado` |
|---|---|---|---|
| `churn > 0` | 33 | **1** | 33 |
| `churn = 0` | 639 | 634 | 634 |

`33 − 1 = 32`, exatamente o `672 − 640` da tabela acima. A interseção é exata: das 33 com
churn, 32 falham e **1** casa (`2026-09-05T21:52:02.445Z`, `nox`, `churn = 2`); falhas
entre as sem churn: **0**.

Confirmação por rota independente, que não usa o campo em que a correção se apoia:
reconstruindo o servido a partir do próprio log como
`(ids_controle − would_leave) ∪ would_enter`, o casamento vai de **640/672** (regra atual)
para **672/672**. Como subproduto, isso é uma âncora nova: `would_enter`/`would_leave` do
log de serving são exatamente consistentes com o que o `brief_log` registra como servido,
nos 672.

**O defeito é puramente de seleção — não há ponta a montante.** Rodado o harness em
modo de fidelidade (`--modo campo`, que compara o controle reconstruído com o que a
produção gravou) sobre a mesma janela: `bate_controle` **640/640**, `bate_churn`
**639/640**, `erros` **32**. Ou seja, o pipeline reproduz a produção em tudo que
consegue alcançar; o que falha é só *quais* briefs ele alcança.

⚠️ E o próprio número da fidelidade tem de ser citado sobre a população **pretendida**,
não sobre a que sobrou: `639/640` é 99,8% de uma população já encolhida pelo defeito, e
sobre os 672 da janela é **639/672 = 95,1%**, com 32 briefs sem resposta nenhuma. Citar
o primeiro seria medir a fidelidade no denominador que o defeito produziu — a mesma
armadilha de população que este documento registra em outra unidade.

> ⚠️ **O viés é anticorrelacionado com o efeito que o instrumento mede.** Quanto mais a
> dose funciona, mais briefs saem da população, e mais perto de zero fica o resultado. É
> um erro de seleção que se disfarça precisamente de resultado nulo — a mesma forma do
> classificador de SOTA que usava "menciona um baseline" como prova de ser de terceiro.

**Por que não foi visto por dois dias.** O gatilho carregava os dois números lado a lado
na própria linha de status — `n_janela=672` e `estados=640` — e **nenhum predicado os
comparava**. Não é a família "guarda calado por não ter o dado" (regra 9 do `CLAUDE.md`):
é o agravante dela, guarda que **tem** o dado e não pergunta.

**Alcance do dano, e o limite honesto da varredura.** O defeito é exclusivo do modo
`active`: em `shadow` o servido *era* o controle, a assinatura casava, e `estados ==
n_janela == 672` nas **seis** rodadas shadow — a série mostra o descolamento aparecendo
só nas duas rodadas `active`. Todo número derivado de replay já escrito rastreia para a
calibração de **2026-08-27** (`11/350 = 3,1429%`, `15`, `17`, teto `17/350 = 4,86%`,
`w_min = 4,4`, saturação em `(4,0 ; 4,4]`), cuja janela `[2026-08-26T20:28Z,
2026-08-27T09:00Z)` é anterior à ativação — portanto não contaminada. Único consumidor
automático do replay é o próprio gatilho de saturação. A varredura cobre os artefatos
versionados e os consumidores automáticos; **não** cobre uma rodada ad-hoc cujo número
tenha ido direto para prosa sem deixar arquivo.

**Correções, classificadas como instrumentação e não emenda**, pelo mesmo critério do
§10.2 — nenhuma toca designação, dose, ordenação ou composição; o que muda é o que o
instrumento consegue enxergar:

1. `idDoBrief` passa a chavear pelo conjunto **efetivamente servido**, usando o campo
   `servido` que o log já grava (`ids_tratado` quando `servido == "tratado"`, senão
   `ids_controle`). Nada é reconstruído.
2. Perna nova no gatilho: `estados != n_janela ⇒ RED erros-no-replay=N`. Independente da
   correção 1, e é a que impede a próxima confusão desta família.
3. Teste de regressão que morde **este** defeito: sobre janela de epoch tratado, exigir
   `erros == 0`. Hoje ele falha; depois da correção 1, passa. Sem ele a correção fica sem
   nada que a proteja — ausência deliberada precisa de teste que a defenda.

**Adendo de 2026-09-07 — a perna nova era estrita demais, e custou um sinal no dia
seguinte.** Na primeira versão ela abortava, e no epoch `2026-09-06` **um** brief com
escrita incompleta no `brief_log` (1 linha de 10, em `23:07:02.425Z`) suprimiu um
veredito substantivo: `w = 7,5` e `w = 100000` produziram resultado **idêntico**
(`mexeu = 38`, `churn_total = 44`, `folga = 1,0`), isto é **`saturado`** — na dose mais
alta do desenho, subir `w` não muda mais nada.

A lição que motivou a perna era "não medir sobre população reduzida **em silêncio**", não
"nunca medir". Descartar o veredito por 1 em 672 transforma o guarda em ruído que suprime
sinal — a fadiga de alarme que ele existia para evitar. Corrigido para **emitir os dois**:
o estado continua `RED` (o *morning report* tem de ver), e o veredito de dose viaja junto
com a população explícita. A linha, verificada rodando o próprio bloco de decisão do
script implantado sobre os números reais do epoch:

```
RED|motivo=erros-no-replay: a janela nao foi respondida inteira faltam=1;
veredito_dose=RED:SATURADO: dose servida == dose absurda; a dose nao esta identificada
populacao_do_veredito=671/672 … mexem_servido=38 mexem_absurdo=38 folga=1.0 n_janela=672
```

⚠️ E um erro de contagem **meu** no diagnóstico desse `faltam=1`, registrado porque a
causa é transferível: minha reconstrução independente acusou **4** briefs não
respondidos contra o **1** do gatilho, e o gatilho estava certo. O código faz
`GROUP BY brief_id` sobre a janela de 3 s; eu agrupei **por segundo**, e três dos quatro
briefs têm os 10 chunks atravessando a fronteira do segundo (10 linhas, 2 `served_at`
distintos), então meu agrupamento os partia em 5 + 5 e nenhum casava a assinatura. É
invariante verificado sobre o conjunto errado.

**Controle positivo da correção — o critério foi o número, não o verde.** Rodado o
mesmo `--modo dose` sobre a mesma janela (`sha256` conferido idêntico ao do veredito
RED), com o `idDoBrief` corrigido:

| | antes | depois |
|---|---|---|
| `estados` | 640 | **672** |
| `erros` | 32 | **0** |
| `mexeu` (w = 2,0) | 0 | **33** |
| `churn_total` (w = 2,0) | 0 | **35** |
| `mexeu` (w = 100000) | 14 | 47 |

Os dois números da dose servida — **33** e **35** — reproduzem exatamente o que o log
de serving registrou de forma independente para o epoch, e é isso que valida a
correção: um veredito GREEN por si não distinguiria "consertado" de "quebrado de
outro jeito". A folga passa a `33/47 = 0,70`, dentro da faixa responsiva.

⚠️ **Uma comparação que este item NÃO faz.** Os `35/672` são *briefs com churn*; os
`3,14%` da condição de detectabilidade foram medidos como *estados que movem* (`11/350`).
Denominador e unidade diferentes; dizer "acima do previsto" antes de casar a unidade
repetiria o defeito "número certo, população errada" já registrado neste documento. O que
se afirma aqui é só o contraste interno, mesma fonte e mesma unidade: `0/441` no controle
contra `35/672` e `33/672` no tratamento.

**Procedência.** Divergência notada em 2026-09-06 ao conferir a série viva do ensaio.
Duas explicações minhas foram levantadas e **falsificadas** antes desta: (i) "ponto fixo
— em `active` o boost já está aplicado, reaplicar não move nada", incompatível com o
código, já que a linha de base do replay é o controle reconstruído (`out.alt`, comparado
a `ids_controle` em `:745`); (ii) "o snapshot de corpus deixou de cobrir a janela após a
mudança de fronteira de 28/08", falsificada por medição — dos 141 `chunk_id` distintos da
janela, **zero** ausentes no corpus, e os 84 registros posteriores ao snapshot não batem
com o gap de 32 nem em contagem nem em direção. O sítio do descarte e a perna
`estados != n_janela` foram localizados em paralelo pela sessão vizinha; a conferência por
reconstrução do servido e a varredura de contaminação são dela.

#### 10.5 O corpus esteve congelado durante os seis primeiros epochs — por defeito

`MAX(created_at)` em `chunks` esteve cravado em **2026-08-24 01:06:35** até
**2026-09-07T14:06:13Z**. A série diária não declina: **corta**.

| dia | chunks com `created_at` nesse dia |
|---|---|
| 2026-08-21 | 118 |
| 2026-08-22 | 15 |
| 2026-08-23 | 57 |
| 2026-08-24 | 40 |
| 2026-08-25 … 2026-09-06 | **0** (14 dias) |
| 2026-09-07 | 182 |

Causa: `nox-mem-watch.sh:52` invocava `/usr/local/bin/nox-mem ingest`, binário
ausente há ~15 dias — o mesmo que havia quebrado o *nightly*. O journal do watcher
registra `No such file or directory`. As **buscas nunca pararam** (`updated_at`
seguia andando); só a ingestão.

⚠️ **Discrepância de contagem que fica declarada em vez de resolvida por escolha.**
O total foi de 67.187 para 67.224 (**+37 líquidos**), e há **182** linhas com
`created_at` de 2026-09-07 — logo ~145 substituíram versões existentes. O relatório
do próprio *catch-up* diz **124** chunks em 13 arquivos. Os 58 de diferença entre
124 e 182 não estão explicados; "criados", "tocados" e "reingeridos" são três
grandezas e aqui divergem.

**O congelamento não alcança o alvo da intervenção.** Os **19** chunks designados
foram todos criados no mesmo instante — `2026-08-21 22:51:23`, lote único —, todos
anteriores ao congelamento: **zero** designados com `created_at` posterior a
2026-08-24. O conjunto que recebe boost nunca ia mudar.

**O que o congelamento alcança é contra quem o boost compete.** Chunks passando o
piso do canal fresco (`importance ≥ 0,7` e `pain ≥ 0,7`) são **17** para
`created_at ≥ 2026-08-24`, **17** para `≥ 2026-08-31` e **17** para `≥ 2026-09-07`
— os três contam os **mesmos 17**, todos criados em 2026-09-07. Ou seja o pool
fresco esteve **vazio o ensaio inteiro** até 14:06 daquele dia, o que também
explica os **246** registros horários do gatilho de composição reportando
`agent_fresh_elegiveis=0` para os seis agentes desde 2026-08-27 — número que até
então estava sem causa nomeada.

Epochs afetados: `2026-09-01` (w = 4,0), `09-02` e `09-03` (controle), `09-04` e
`09-05` (w = 2,0), `09-06` (w = 7,5) — **6 de 234**.

**Decisão: nota de limitação com a fronteira cravada, sem alterar a análise.** Três
razões, todas medidas e não retóricas:

1. o alvo da intervenção é fixo e anterior ao congelamento (acima), logo o
   congelamento não muda quem é tratado;
2. o congelamento é propriedade do **tempo de calendário**, e o braço é sorteado
   sobre o calendário ⇒ é covariável **balanceada em expectativa**, não
   confundidor. Ele estreita a validade **externa** (o ensaio mediu um ambiente de
   ordenação estático), não a interna;
3. são 6 de 234 epochs.

⚠️ **Por que não virar dois regimes com regime como fator.** Seria decisão de
análise tomada **depois** de os dados existirem — exatamente o grau de liberdade que
o pré-registro existe para eliminar. Uma escolha reaberta com dados na mesa vale
zero mesmo chegando à mesma conclusão, porque o leitor não pode distinguir "decidiu
antes" de "decidiu e diz que decidiu antes". É o mesmo argumento do §10.1.

**Isto é o inverso de um fato registrado antes**, e a contradição é aparente, não
real: em 2026-08-15 foi medido que o corpus do piloto **não** era estacionário. Era
verdade então; o congelamento é posterior e tem causa operacional. Série viva citada
como instante envelhece para falsa — aqui a fronteira fica cravada por isso.

#### 10.6 Um script DEPOSITADO dependia de um insumo fora do depósito, em caminho volátil

`measurement/ordem.mjs` é o **item 115** de `deposit/paperA/MANIFEST.json` — script
publicado, que um terceiro deveria conseguir executar. Ele abria, por **caminho
fixo**, `/var/tmp/p2-ord-ro.db`: **1,6 GB**, e o MANIFEST não contém **nenhum**
`.db`. O resultado que ele sustenta está citado em `measurement/README.md:69` —
*28 casos, 0 com ordem diferente*, que é o que **refuta o canal de reordenação**.

O arquivo quase foi apagado num varrimento de espaço em disco em 2026-09-07. E
**naquele mesmo dia deixou de ser recriável**: o descongelamento do §10.5, às
14:06:13Z, fez o `main` deixar de ser o de 2026-08-26. Até 14:06 "recriar a partir
do `main`" ainda era caminho; depois, não.

Isto é literalmente o defeito que o texto do próprio depósito declara já ter
cometido: *"um corpus pinado por identificador já foi perdido neste mesmo trabalho,
levando 280 episódios adjudicados junto"*.

**Correção aplicada.** Movido para
`/var/lib/nox-mem/p2/corpus/p2-ord-ro-2026-08-26.db`, com `sha256` conferido
**antes** de remover a fonte e `mtime` preservado; verificado depois por terceiro:
`PRAGMA quick_check` **ok**, **67.187** chunks, `MAX(created_at)` =
**2026-08-24 01:06:35** — o estado congelado exato. O `-wal` órfão tinha **0
bytes**, logo não havia transação pendente. O caminho passou a ser parametrizável
por `NOX_P2_ORD_LIVE`, com o novo local como default.

⚠️ **Uma premissa que foi medida e caiu, e fica registrada porque enfraquece a
urgência que eu alegava:** não existe regra de idade para `/var/tmp` neste sistema
(`systemd-tmpfiles --cat-config` só traz `x /var/tmp/systemd-private-%b-*` e
`X …/tmp`). O arquivo **não** estava com prazo correndo. A correção se justifica por
caminho volátil por convenção, por dependência publicada fora do depósito e por um
agente de faxina que perguntou mas podia não ter perguntado — **não** por deleção
iminente.

**Resolução, e ela falsificou a minha própria proposta.** Eu havia sugerido "depositar
o recorte de 28 casos em vez do corpus de 1,6 GB". Ao executar, dois fatos derrubaram
isso:

1. **não havia recorte a depositar, porque não havia artefato nenhum.** A alegação vivia
   só em prosa, em três lugares (`measurement/README.md:69`,
   `AMENDMENT-DRAFT-band-collapse-2026-08-26.md:862` e este documento). É a classe já
   catalogada no §6 — *um valor citado em vários lugares sem nenhum artefato que o
   contivesse*;
2. **e o recorte não seria recortável:** `ordem.mjs` passa o handle do DB **para dentro**
   do código de produção (`boostsParaCandidatos`, `buildBriefDiverse`), então "só as
   linhas de que ele precisa" exigiria reimplementar o que a produção lê — a
   reconstrução que este trabalho já pagou para não fazer.

⚠️ **Pior: a rodada de 2026-08-26 não é mais reproduzível, e não por causa do arquivo que
eu salvei.** O par de insumos é `live` + `corpus`. O `live` está preservado; o `corpus`
apontava para `/var/lib/nox-mem/epochs/current.db`, e os snapshots de epoch de 08-24 a
09-02 **foram podados** — restam apenas os `*.manifest.json`. Salvei metade do insumo.

**O que ficou feito:** a comparação foi **reestabelecida** num par preservado e pinado, e
gravada como `out/ORDEM-SEQUENCIAS-2026-09-07.json` (5,4 KB — não 1,6 GB), com
`sha256` dos dois insumos, o resumo e os 28 resultados. Resultado: **`mesmaOrdem` = true
em 28 de 28**, `mesmoConjunto` = true em 28 de 28. O artefato entra no MANIFEST (item
121), e o `sha256` do próprio `ordem.mjs` foi recomputado ali, porque a edição do caminho
o havia desatualizado — o gate 0 do `deposit.sh` teria falhado, corretamente.

⚠️ **Este artefato NÃO reproduz a rodada de 26/08** — reestabelece a alegação em outro
par de insumos, e diz isso no próprio campo `procedencia.porque`. O `README.md:69` foi
alterado para carregar a ressalva junto do número, em vez de apresentá-lo como se fosse a
medição original.

⚠️ **Ressalva de poder, declarada no artefato em vez de silenciada.** `mesmoConjunto =
true` nos 28 é a **pré-condição** do teste, não defeito: a objeção que ele responde é *"se
`churn = 0`, um boost que **reordena** dentro do conjunto fica invisível"*. Mas o artefato
**não registra se um boost foi de fato emitido** em cada estado, então a refutação vale
condicionada a isso e o poder do teste fica sem medida. Fechar essa ponta exige gravar
`boosts_emitidos` por caso — trabalho declarado, não feito.

#### 10.7 O canal de tratamento mudou de composição no meio do ensaio — por conserto

> 🔴 **CORRIGIDO PELO §10.10, no mesmo dia.** O `agentFresh = 219` é real no corpus que
> o *gatilho* lê e **falso** no canal que o *serving* usa: o processo serve de um snapshot
> aberto por *file descriptor* em 03/09, onde `agentFresh = 0`. Não houve mudança de
> composição no canal servido, e os 7 epochs listados abaixo **não foram afetados**. O
> item fica no registro porque a medição, o mecanismo do `interleave` e a regra de
> tratamento continuam corretos *como raciocínio* — e porque um item retirado esconde o
> erro em vez de o mostrar.

O gatilho de composição (item 7(b)) virou `RED` em **2026-09-08T06:09:04.208Z**, com
`agent_fresh_elegiveis = 219` (`nox:0 atlas:0 boris:205 cipher:8 forge:6 lex:0`). A
transição é **única e limpa**: desde a primeira linha do gatilho
(`2026-08-27T17:55:21.650Z`) todas as execuções horárias anteriores reportaram `0` para
os seis agentes, sem uma exceção. Este é o alarme que o item 7(b) foi escrito para dar, e
ele deu — a ameaça que ele vigia é *"a única que muda a escala de dose **durante** o
estudo, em silêncio"*.

**Não é rajada de trabalho dos agentes. É ingest em bloco.** Os 219 chunks foram criados
numa janela de **18 minutos**, `2026-09-08 02:19:44` → `02:37:23` (UTC), e a série diária
de `chunks` com `source_file LIKE 'sessions/%'` no banco vivo mostra corte e volta:

| dia | chunks `sessions/%` criados | passam o piso do canal |
|---|---:|---:|
| 2026-08-01 … 08-10 | 67 · 105 · 143 · 55 · 39 · 77 | 44 · 81 · 102 · 39 · 21 · 54 |
| 2026-08-11 … 09-07 | **0** (28 dias) | **0** |
| 2026-09-08 | **382** | **253** |

**Causa: o conserto do `session-distill` em 2026-09-07** — a migração da VPS havia movido
o endereço *e* o schema dos transcripts, e o cron reportava `ok` com `exit 0` por 28 dias
imprimindo `No unprocessed sessions found`. Consertado o parser, o distill foi rodado
**à mão** naquela noite. **Não existe entrada de cron para ele** — conferido no
`crontab -l` completo da VPS, onde estão os 30 jobs de manutenção e os dois gatilhos do
P2, e nenhum `distill`.

Este é o **segundo passo** do descongelamento descrito em §10.5, e não o mesmo. Lá o
conserto de `nox-mem-watch.sh` (2026-09-07T14:06:13Z) reencheu o sub-pool **global**
(`memory/entities/%`, `lessons.md`) — e o gatilho de composição seguiu reportando `0`,
porque ele mede `sessions/<agente>/%`, que é a outra perna. O `agentFresh` só deixou de
ser vazio com o distill, ~12 h depois.

##### Por que isto atinge o desenho, e não só o corpus

`interleaveFresh(agentFresh, globalFresh)` era **função-zero** — `interleaveFresh([], g)
=== g`, todo o canal era o sub-pool global. Toda a calibração de dose de 27/08 (a
distribuição de `w_min`, o teto de 17/350) foi medida **nesse** regime. Com `agentFresh`
povoado, `interleaveFresh` passa a intercalar de fato, e o `w_min` de qualquer estado
afetado deixa de valer. Não é ruído a tolerar: é a premissa da calibração caindo, que é
exatamente o texto que o gatilho imprime como ação.

E a mudança não pegou um epoch de controle:

| fato | valor | fonte |
|---|---|---|
| epoch de **2026-09-08** | **`treatment`, `w = 2,0`** | `ASSIGNMENT-SERVING.json` |
| abertura do epoch | `09:00Z` | fronteira `epochInicioISO` |
| entrada dos chunks | `02:19Z`–`02:37Z` | `created_at` |
| snapshot que os capturou | `e20260908T060004Z.db` (`06:00Z`) | `current.db` |

Isto é, o epoch de hoje é o **primeiro epoch de tratamento servido com o canal
intercalado**, e ele foi servido inteiro nesse regime — a ordem dos três horários não
deixa ambiguidade.

##### O regime é transitório, e a data de saída está cravada

`freshMaxAgeDays = 7`, e os **253** chunks elegíveis de `sessions/%` têm todos
`source_date = '2026-09-08'` ⇒ deixam de passar o predicado em **2026-09-15 00:00:00Z**,
todos no mesmo instante. Sem cron para o distill, `agentFresh` volta a vazio ali.

⚠️ **A primeira versão deste parágrafo errou o conjunto de epochs**, e o erro tem forma
reconhecível: derivei a expiração com `date(…, '+7 days')`, que devolve **2026-09-15**, e
tratei o dia como se o epoch daquela data estivesse dentro. O predicado é
`julianday('now') − julianday(source_date) <= 7` — **com hora** —, `source_date` é
meia-noite, e os epochs abrem às **09:00Z**. Logo o epoch `09-15`
(`[09-15T09:00Z, 09-16T09:00Z)`) começa **9 h depois** da expiração e está **inteiro** no
regime antigo. Resolução de dia contra fronteira de nove horas: mesma família de
"número certo, população errada".

Medido corretamente, o regime `[2026-09-08T02:19Z, 2026-09-15T00:00Z)` cobre:

| epoch | braço | dose | cobertura pelo regime novo |
|---|---|---:|---|
| 2026-09-08 | treatment | 2,0 | inteiro |
| 2026-09-09 | treatment | 2,0 | inteiro |
| 2026-09-10 | control | 0 | inteiro |
| 2026-09-11 | control | 0 | inteiro |
| 2026-09-12 | treatment | 4,0 | inteiro |
| 2026-09-13 | control | 0 | inteiro |
| 2026-09-14 | treatment | 4,0 | **parcial** — 15 h de 24 |
| 2026-09-15 | treatment | 4,0 | **nenhuma** |

São **7 epochs de 234**: 3 de tratamento inteiros, 1 de tratamento **atravessado pela
fronteira** e 3 de controle. O `09-14` é heterogêneo por dentro, como o Epoch 1 (§10.1) e
o `09-03` (§10), e herda a mesma questão de tratamento.

⚠️ **E o regime novo não exercita a dose alta.** As doses cobertas são `{2,0; 2,0; 4,0}`
inteiras mais `{4,0}` parcial — **nenhum epoch de `w = 7,5`** cai dentro. A curva
dose-resposta no regime novo tem, no máximo, **dois** pontos de dose, e o teto do desenho
não é tocado. Qualquer afirmação sobre "a dose no regime intercalado" fica limitada a
`w ∈ {2,0; 4,0}`.

⚠️ **Um dos números começou como reconstrução minha e foi remedido contra o fonte.** Os
`219` são do gatilho, que lê os limiares de `DIVERSITY_DEFAULTS` no `dist` e confere as
duas cláusulas do predicado contra `src/api/brief.ts` antes de medir — e o valor que eu
havia reconstruído à mão para os seis agentes bate com ele, o que valida os patterns de
sessão. Para o sub-pool global eu errei **duas** coisas. O pattern: escrevi `%lessons.md`, e o
literal é `GLOBAL_FRESH_PATTERNS = ["memory/entities/%", "memory/lessons.md"]` — que o
`replay-oportunidade.mjs` **extrai do fonte e aborta se divergir**, em vez de confiar na
cópia. E a **janela de idade**: usei os 7 dias de `freshMaxAgeDays`, mas o segundo
`fetchFreshCandidates` é chamado com `{ ...cfg, freshMaxAgeDays: cfg.freshGlobalMaxAgeDays }`
⇒ o sub-pool global usa **30 dias**, não 7.

Com pattern e janela corretos o global dá **108** no corpus que o serving usa e **115** no
snapshot de hoje — não 60. E os **108** batem exatamente com o número que o cabeçalho do
`gatilho-composicao.mjs` documenta (*"108 candidatos de `memory/entities/%` + `memory/lessons.md`"*),
o que é a conferência que eu devia ter feito antes de publicar um número reconstruído.

⚠️ **A janela errada quase produziu uma conclusão invertida.** Com 7 dias, os 19
designados — do lote de `2026-08-21`, portanto com 17 dias — **não** passariam, e o pool
fresco apareceria como *inteiro vazio*: eu cheguei a escrever que o canal de cobertura
estava inerte e que o boost não teria onde agir. Com os 30 dias reais, os 19 estão **todos**
no pool nos dois corpora, o mecanismo funciona, e o `mexeu = 38` medido no epoch 09-06
deixa de ser contraditório. Quarta ocorrência da classe *reconstrução que modela regra que
o código não aplica* — e a primeira em que o parâmetro errado apontava para "o ensaio não
mede nada".

Um terceiro número que o gatilho **não** conta e que não é defeito dele: **34** chunks
elegíveis em `sessions/main/%`. `main` não é um dos seis agentes do ensaio, e o gatilho
vigia os seis.

##### O mecanismo é derivável do código, e a direção não é a intuitiva

`interleaveFresh(a, b)` é alternância estrita — `a[0], b[0], a[1], b[1], …`, com
deduplicação por `row.id` —, `a` é o `agentFresh` e `b` o `globalFresh`. Duas
consequências caem direto disso:

1. **Nada é cortado por teto.** `FRESH_CANDIDATE_POOL = 400` e o canal passou de `0 + 60`
   para `219 + 60 = 279`. O pool continua cabendo inteiro; o que mudou não é *quem entra*.
2. **A posição de cada candidato global no `freshPool` passou de `i` para `2i + 1`.** Com
   `agentFresh` vazio, `interleaveFresh([], b) === b` e o i-ésimo global ficava na posição
   `i`. Com 219 à frente na alternância, ele vai para `2i + 1` — a distância até os
   `freshSlots` **dobra**.

⚠️ **E os 19 chunks designados são todos do sub-pool global** (`memory/entities/%`,
criados no lote único de `2026-08-21 22:51:23`). Logo a derivação prevê que a mesma dose
alcance **menos**, não mais: o boost tem o dobro de distância para cobrir. Se essa
previsão se confirmar, a mudança de canal **reduz** a exposição do tratamento — o
contrário do que "o canal ficou mais rico" sugere.

Isto está escrito como **derivação sobre o código, não como resultado**. A posição na
ordem de entrada do `freshPool` não é necessariamente a grandeza que decide o pick, e
"reconstrução que modela regra que o código nunca aplica" é defeito já cometido três vezes
neste projeto. A medição que decide está descrita abaixo.

##### A medição, e o que dela ficou impossível

⚠️ **A âncora de 27/08 não é reproduzível.** A distribuição publicada (`w_min` mín 0,02 ·
mediana 1,7 · máx 4,4, espalhamento 220×; teto 17/350 = 4,86%) foi medida sobre o snapshot
de corpus daquele dia, e `/var/lib/nox-mem/epochs/` tem hoje **16 manifests e 3 `.db`** —
os snapshots antigos foram podados, como já ocorreu no §10.6. Logo **não existe** a
comparação "mesma janela, corpus de 27/08 contra corpus de hoje": qualquer diferença
contra aquele número confundiria mudança de corpus com mudança de janela.

O que ainda é possível, e é mais limpo que o delta histórico, é um **contraste interno com
a janela fixa**:

| corpus | `agentFresh` | `globalFresh` | chunks de sessão |
|---|---:|---:|---:|
| **C3** — produção, `e20260908T060004Z.db` | **219** | 60 | 14.838 |
| **C2** — C3 menos os 382 ingeridos em 08/09 | **0** | 60 | 14.456 |

C2 não é um snapshot antigo: é C3 com os 382 chunks removidos, e por isso difere de C3
**apenas** naquilo que se quer isolar. Duas conferências antes de rodar: `14.838 − 382 =
14.456` é **exatamente** a contagem de sessões do snapshot real de 2026-09-07, o que prova
que os 382 são todos novos e **nenhum substituiu** versão anterior; e `global_elegivel`
fica em 60 nos dois, `quick_check = ok`.

⚠️ **Por que o snapshot real de 07/09 NÃO serve como braço de comparação.** Ele é de
`06:00Z`, anterior ao conserto do watcher das `14:06Z`, e tem `global_elegivel = 0`.
Usá-lo misturaria o reenchimento do pool global (§10.5) com o do `agentFresh` (este item)
— dois fatores num contraste de dois pontos, que é a forma de não medir nenhum dos dois.

A rodada usa o próprio gatilho de saturação (que já carrega o `sha256` do recorte e o
cruzamento designado × servido), com `--epoch 2026-09-06` e a janela
`[2026-09-06T09:00:00Z, 2026-09-07T09:00:00Z)`, `n_janela = 672` — reproduzido, igual ao
que o gatilho publicou. **Grava em arquivos próprios**, nunca no
`status-saturacao.txt` nem no `gatilhos.ndjson` de produção: rodada de medição
contaminando a série de vigilância é o defeito que este repositório já carrega no nome de
`p2-write-path.CONTAMINADO-por-verificacao-20260818.ndjson`.

##### A regra de tratamento, FECHADA em 2026-09-08 sem que desfecho algum fosse consultado

> **Precedência.** Decidida em **2026-09-08**, no oitavo epoch do ensaio. Nenhum desfecho
> foi computado, consultado ou estimado antes desta decisão. O que foi medido para decidir
> é **exclusivamente estrutura de exposição** — contagens de candidatos elegíveis por
> sub-pool, posição na ordem do `freshPool`, e quantos estados **mudam de conteúdo** no
> brief (`mexeu`/`churn_total`) sob doses contrafactuais. A densidade de falhas repetidas,
> que é o desfecho, **não foi tocada**. Confere-se pelo `git log` que este parágrafo
> antecede qualquer artefato de desfecho no repositório.

✅ **A decisão reusa a estrutura já registrada, em vez de criar uma paralela** — o mesmo
fundamento que fechou o Epoch 1 (§10.1). O `PREREG-DRAFT.md` §"Mandatory ITT co-estimate"
determina que o *primary* seja reportado ao lado de um co-estimador ITT sobre todos os
epochs pós-washout **sem exclusão de cobertura alguma**, com concordância como força da
alegação e divergência reportada como está, não adjudicada a favor de nenhuma das duas.

**Nenhum epoch sai.** Os 7 epochs do regime intercalado entram no *primary* e no
co-estimador ITT, no braço e na dose designados. **Acrescenta-se uma terceira análise,
pré-especificada aqui:** o mesmo par de estimativas com os epochs do regime novo
excluídos, sob a mesma regra do §1042.

**Por que não descartar — e a razão é viés, não poder.** Duas coisas, medidas:

1. **Excluir seria seleção correlacionada com o mecanismo.** A derivação acima prevê que
   no regime intercalado a mesma dose alcance **menos**. Se ela se confirmar, os epochs
   afetados são os de **menor** efeito, e removê-los **infla** a estimativa. É a mesma
   classe de defeito do §10.4 — onde o replay descartava justamente os briefs em que a
   dose mordeu — com o sinal trocado. Filtrar por uma variável que o efeito move é vício
   independentemente da direção.
2. **O custo estatístico de descartar é desprezível**, logo não compra nada em troca. Com
   a alocação `117/39/39/39`, os afetados são 2 de 39 em `w = 2,0` e 1 inteiro + 1 parcial
   de 39 em `w = 4,0`; o erro-padrão inflaria `√(39/37)` = **2,7%**. Como no Epoch 1, a
   decisão não é sobre poder.

E não há viés a remover em troca: o regime é propriedade do **tempo de calendário** e o
braço é sorteado sobre o calendário ⇒ covariável balanceada em expectativa, não
confundidor. É o mesmo argumento que o §10.5 aceitou para o corpus congelado, e ele
estreita a validade **externa**, não a interna.

##### O indicador de regime é MECÂNICO, não uma lista de datas

O regime entra na análise como indicador por epoch, definido por **medição** e não por
data escrita à mão: `agent_fresh_elegiveis > 0` na linha
`p2_gatilho_composicao` do NDJSON, que roda a cada hora e persiste. Para o epoch
atravessado, a **fração de horas** cobertas.

⚠️ **Isto não é preciosismo: a primeira versão desta seção errou a lista de datas** —
`date(…, '+7 days')` devolveu `2026-09-15` e eu incluí o epoch daquele dia, que abre 9 h
**depois** da expiração. Uma lista de datas escrita à mão também não sobrevive ao distill
rodar de novo; o predicado medido sobrevive. Mesma disciplina do estado vivo que só se lê
por comando, nunca por lista transcrita.

##### O que fica em aberto, e é decisão operacional, não de análise

Pôr o distill em cron estabiliza o canal no regime intercalado pelos 227 epochs
restantes; não pôr deixa o canal oscilar por ação manual não registrada, que é pior que
congelado. A escolha tem **gatilho quantitativo**: se `w = 2,0` continua movendo estados
no regime intercalado, estabilizar é preferível a oscilar; se `w = 2,0` fica **inerte**,
estabilizar tornaria um terço dos epochs de tratamento não-informativos pelo resto do
ensaio, e aí o certo é preservar o regime da calibração até o fim ou emendar as doses —
o que exigiria a emenda ao pré-registro que hoje está preparada e **não** executada.

#### 10.8 Dois defeitos no gatilho de saturação, achados ao ler o RED de hoje

**(a) `emitir()` não grava o NDJSON — e é por onde saem os alarmes mais valiosos.** A
função escreve `stdout` e o arquivo de `--status`, e nunca o `--ndjson`. Só o caminho
normal (o bloco `python3` do veredito) persiste linha. Logo todo veredito que sai por
atalho — `log-de-serving-ausente`, `assignment-nao-existe`, `assignment-sha256-divergente`,
`janela-com-n-insuficiente`, `log-diverge-do-assignment`, `epoch-de-controle`,
`replay-falhou` — fica **apenas** no arquivo de status, que é **sobrescrito** na execução
seguinte. É perda permanente, não atraso.

Medido: `/var/log/nox-p2-gatilhos.log` tem **12** execuções de `p2-saturacao-da-dose`
contra **9** linhas `p2_gatilho_saturacao` no `gatilhos.ndjson`, e o NDJSON **não tem
nenhuma linha de 2026-09-07 nem de 2026-09-08**, embora as duas existam no log e a de
09-08 esteja no status agora. Entre os motivos que existem só no log de texto está
`log-diverge-do-assignment` — que o próprio comentário do script chama de *"o alarme mais
valioso deste script … a única coisa aqui que compara o que devia ser servido com o que
foi"*. O alarme mais valioso é o que não deixa rastro estruturado.

**Consertado em 2026-09-08, com mutação.** `emitir()` e `morte_por_sinal()` passam a
gravar uma linha de atalho; a escrita dupla no caminho normal é impedida por uma
**sentinela** em `$TMP` que o bloco de veredito cria depois de gravar — e não por contagem
de linhas, porque o `gatilho-composicao.mjs` escreve no **mesmo** NDJSON a cada hora e uma
rodada de saturação leva ~15 min, de modo que a linha do outro gatilho entraria no meio e
seria lida como *"já gravei"*.

O registro de atalho **não finge ter os campos do veredito**: `servido`, `absurdo` e
`folga` saem `null`, com `via: "atalho"` dizendo por quê. Preenchê-los com zero fabricaria
`mexeu = 0`, isto é `dose-servida-inerte` — precisamente o veredito errado que o §10.4
documenta ter custado dois dias de RED com o motivo trocado.

Cobertura: `teste-gatilho-active.sh` vai de 12 para **15** casos (T12 atalho grava com
`via=atalho` e sem campos fabricados; T13 o caminho normal grava **uma** linha com os
campos reais; T14 o `log-diverge-do-assignment` persiste). **Duas mutações confirmam que
os casos mordem, e em pontos distintos:** contra a versão pré-patch falham T12 (`n=0`),
T13 (`via=None`) e T14 (`n=0`), e os 12 antigos seguem verdes; removendo **só** a
sentinela, falha **apenas** T13, com `n=2 vias=['veredito-de-dose','atalho']`. Produção e
repo no mesmo `sha256` (`61b56d69aeec…`), 15/15 verdes contra o script implantado; a
versão anterior ficou em `gatilho-saturacao.sh.pre-ndjson-2026-09-08`.

⚠️ **O que o conserto NÃO recupera.** As linhas dos atalhos já ocorridos estão perdidas —
o arquivo de status foi sobrescrito. O log de texto (`/var/log/nox-p2-gatilhos.log`)
guarda as linhas cruas dessas execuções e é a única fonte para elas; qualquer análise da
série de vereditos anterior a 2026-09-08 tem de ler o log, não o NDJSON, e sabendo que o
log não é estruturado nem tem garantia de retenção.

**(b) O patch de 2026-09-07 ainda não foi exercitado em produção.** A perna que
*alarma e preserva* o veredito (§10.4, adendo) entrou em `gatilho-saturacao.sh` às
**2026-09-07T14:30:14Z** — **5 h depois** do `RED` das `09:12` daquele dia. Aquele `RED`
saiu da versão anterior, a que **abortava**, e é por isso que ele não carrega
`veredito_dose=`, `mexem_*` nem `folga=` na linha, e que não há linha dele no NDJSON. Da
implantação até agora o gatilho rodou **uma** vez, em `2026-09-08T09:12:01Z`, sobre o
epoch `2026-09-07` de **controle** — que sai por atalho, antes do bloco que a perna nova
habita.

⚠️ **Consequência de leitura, e ela é a armadilha:** o `RED` de 09-07 saiu do morning
report de hoje substituído por um `GREEN`, e o `GREEN` é
`motivo=epoch-de-controle-sem-dose-a-saturar semantica=pergunta-indefinida-nao-verificada`
— isto é, **verde por pergunta indefinida, não por defeito resolvido**. O `faltam=1` de
09-06 (o brief com 1 linha de 10 em `2026-09-06T23:07:02.425Z`) e o veredito `SATURADO`
que ele encobria continuam onde estavam. Um epoch de controle limpando um `RED` de
tratamento do painel é a mesma família do guarda que fica calado por não ter o dado.

#### 10.9 Reingestão por arquivo mata a identidade dos chunks servidos — a auditoria de janela tem meia-vida

> 🔴 **PARCIALMENTE CORRIGIDO PELO §10.10.** Os 53 ids não estão mortos *para o serving*:
> eles vivem no snapshot que o processo tem aberto. A irreprodutibilidade medida é
> **desalinhamento** entre o corpus do serving e o corpus que o replay recebe, e não
> perda de dados — o que a torna consertável. A reingestão por arquivo **existe** e mata
> ids de verdade no banco vivo; o guarda dos designados segue justificado por isso.

Achado em 2026-09-08 ao conferir se o corpus cobria a janela **antes** de rodar a medição
do §10.7. Ele a cancelou, e vale mais que ela.

**Medido.** Dos **141** `chunk_id` distintos que o canal serviu na janela do epoch
`2026-09-07`, **53** já não existem no banco vivo — todos de `memory/lessons.md`, ids
**contíguos** `308444..308496`, todos com `created_at 2026-08-22 02:01:58`. O arquivo
reaparece com **60** chunks em ids **novos**, `309034..309093`,
`created_at 2026-09-07 23:01:36`.

| snapshot | `memory/lessons.md` | ids |
|---|---:|---|
| `e20260906T060001Z` | 53 | `308444..308496` |
| `e20260907T060001Z` | 53 | `308444..308496` |
| `e20260908T060004Z` | **60** | **`309034..309093`** |
| banco vivo (agora) | 60 | `309034..309093` |

Isto é **reingestão de arquivo**, não perda de dados: o conteúdo permanece, a
**identidade** muda. O ingest apaga os chunks daquele `source_file` e cria outros. Uma
única reingestão em 16 dias — a taxa é baixa, o evento é destrutivo para a auditoria.

##### O efeito é sobre o que se pode REPRODUZIR, e ele é grande

O replay localiza cada estado pelos ids que o log de serving registrou. Ids mortos ⇒
estados não localizáveis ⇒ o brief vira `erro` e **sai da população antes do laço de
doses**:

| janela | briefs | com ao menos um id morto |
|---|---:|---:|
| epoch 2026-09-05 | 672 | **400 (59,5%)** |
| epoch 2026-09-06 | 672 | **436 (64,9%)** |
| epoch 2026-09-07 | 672 | **440 (65,5%)** |

⚠️ **Por isso a medição do §10.7 foi abortada em vez de concluída.** Ela ia gastar ~30 min
para produzir um veredito de dose sobre ~35% da população, com a perda concentrada
justamente nos estados que a dose alcança — o viés anticorrelacionado com o efeito que o
§10.4 documenta. Um número assim é pior que nenhum: parece resultado.

**A consequência de método, e ela vai ao paper:** a auditoria de uma janela tem **meia-vida
curta**. O `gatilho-saturacao.sh` roda 09:12Z, 12 min após o fecho do epoch, e é por isso
que ele funciona; **re-análise retroativa de uma janela é impossível** depois da primeira
reingestão dos arquivos do canal. O `run-saturacao.sh` já declara uma aproximação vizinha
("um dia UTC atravessa DOIS corpora e este replay usa um só"), mas essa nota é sobre
**qual** corpus escolher, não sobre o corpus **deixar de conter** o que a janela referencia.

##### Uma causa registrada neste documento que a medição NÃO reproduz

O §10.4 atribui o `faltam=1` do epoch `2026-09-06` a *"UM brief com escrita incompleta no
`brief_log` (1 linha de 10, em `2026-09-06T23:07:02.425Z`)"*. Medido agora, **não se
sustenta**:

- agrupando por **`brief_id`** — a chave certa —, a janela tem **672 briefs, todos com
  exatamente 10 linhas**, zero `brief_id` nulo, zero fora de 10;
- os dois contadores que a perna `estados != n_janela` compara **não** divergem por
  critério: `p2_outcome` na janela = **672**, e com `ids_controle.length == 10` = **672**;
- e a reingestão de `lessons.md` (23:01:36 de 07/09) é **14 h posterior** ao gatilho que
  emitiu o `faltam=1` (09:12Z de 07/09) — no snapshot que ele usou, os 141 ids estavam
  **todos** presentes (0 ausentes, conferido).

Fica **sem causa confirmada**, e é assim que entra no registro. Trocar uma hipótese não
verificada por outra minha seria o mesmo defeito com outro nome.

⚠️ **Armadilha de medição no caminho, que quase virou um número falso.** Agrupei
primeiro por `served_at` e obtive uma distribuição com 12 grupos "anômalos" (n = 1, 2, 11,
12, 18, 19). Não há anomalia alguma: `served_at` tem resolução de **segundo** e colide
entre briefs distintos. A chave é `brief_id`, que existe na tabela. Chave de agrupamento
errada fabrica anomalia.

##### O risco que isto expôs, e que não tinha guarda nenhum

Os **19 designados estão íntegros** — conferido em quatro corpora, 19/19 em vivo, 06/09,
07/09 e 08/09. Eles vivem em **19 arquivos DISTINTOS** de `memory/entities/lessons/`, um
chunk designado por arquivo, todos do lote `2026-08-21 22:51:23`, **nunca reingeridos**.

Mas a reingestão é **por arquivo**. Editar um daqueles 19 mata aquele designado, e a
designação — sorteada uma vez, com semente pública, e que **não se refaz** — quebra **em
silêncio**. Nada vigiava isso.

**Implantado 2026-09-08: `gatilho-designados.mjs`**, cadência horária no minuto `:24`, lido
pelo `morning-report.sh` com teto de 3 h. Duas pernas, porque uma não cobre a outra:

1. **ausência** de um id ⇒ `RED` com a lista — é o que a reingestão produz;
2. **deriva** com id vivo (`sha256` do `chunk_text`, ou o `source_file`, diferente do
   baseline) ⇒ `YELLOW` — um `UPDATE` no mesmo id altera o alvo e deixa a perna 1 calada,
   que é a forma de defeito da regra 9 do `CLAUDE.md`.

O **baseline é imutável**: o guarda cria se não existir e **nunca** sobrescreve — uma
referência reescrita pelo próprio guarda o faria comparar o estado corrompido consigo
mesmo e dizer `GREEN` para sempre. Baseline criado em `2026-09-08T14:51:49Z`, 19/19,
`sha256 = e43fbc9076fdd91f2d24a5fe8b008aca1eb3a5f61b31724529d90312bdfedeaa`. Trocá-lo
exige ação humana explícita.

Cobertura: `teste-gatilho-designados.sh`, **12** casos, com quatro mutações conferidas
(ausência, deriva, imutabilidade do baseline, conferência de `sha256` do DESIGNATION).

⚠️ **Uma delas corrigiu o próprio teste.** A mutação "baseline passa a ser sobrescrito"
deixava `T3b` e `T7b` **verdes** — os dois casos que eu havia escrito justamente para
proteger a imutabilidade. Motivo: nos dois há **ausência**, e o bloco de criação recusa
criar sobre estado quebrado, então o baseline fica intacto de qualquer forma. O caso que
prova a imutabilidade é outro — deriva detectada e **segunda** execução ainda `YELLOW`
(`T10`) —, e com ele a mutação passa a derrubar 5 casos. Teste que morde a mutação **pelo
motivo errado** não protege o que se pensa.

##### E uma regra de calibração que estava invertida no `morning-report.sh`

O comentário que fixa o teto de idade dizia *"Se der < 1, o guarda esta CEGO"*, e
**contradiz os dois exemplos que ele mesmo dá três linhas abaixo**. Computado:

| gatilho | teto | idade normal | intervalo | `rodadas_toleradas` | 1 falha | o comentário chama de |
|---|---:|---:|---:|---:|---|---|
| saturação 09:12Z | 30 h | 21,3 h | 24 h | **0,36** | 45,3 h ⇒ dispara | OK |
| saturação 05:41Z | 30 h | 0,8 h | 24 h | **1,22** | 24,8 h ⇒ silêncio | CEGO |

Cego ⟺ `rodadas_toleradas ≥ 1`, o inverso do que estava escrito. Quem calibrasse pela
regra, e não pelos exemplos, escolheria o teto ao contrário. Corrigido no mesmo dia.

#### 10.10 🔴 O serving lê um snapshot congelado por *file descriptor* — e isso reescreve §10.7

> ⚠️ **A DATA deste item foi corrigida pelo §10.11 (2026-09-09).** O achado, a
> delimitação dos snapshots equivalentes e a validade dos vereditos até o epoch 09-06
> seguem de pé. O que caiu foi a justificativa aritmética de `2026-09-15`: ela supunha
> que nada mais entra no pool, e a ingestão de sessões é por *hook* dirigido por
> atividade de agente. Data vigente: **`2026-09-10 09:00Z`**.

Achado em 2026-09-08, ao investigar por que o log de serving registrava ids que **não
existem** no banco. Domina os dois itens anteriores e corrige uma conclusão do §10.5.

**Medido.** `nox-mem-api` está no ar desde `2026-09-03 17:23:30 UTC` e roda com
`NOX_EPOCH_SNAPSHOT=active`, isto é, serve de um snapshot de epoch. O caminho é o symlink
`/var/lib/nox-mem/epochs/current.db`, que o cron reaponta às 06:00Z todo dia.

| o quê | inode |
|---|---|
| `current.db` → `e20260908T060004Z.db` (hoje) | **524930** |
| fd 26 do processo: `e20260903T060001Z.db` **(deleted)** | **553124** |

O processo **resolveu o symlink uma vez**, em 03/09 17:30, abriu o arquivo apontado então e
nunca reabriu. O symlink mudou cinco vezes desde aí e os snapshots antigos foram podados
do disco — o arquivo que o serving lê **só existe pelo descriptor**.

⚠️ **Recuperado antes de qualquer restart**, via `cat /proc/<pid>/fd/26`, em
`/var/lib/nox-mem/p2/corpus-SERVING-REAL-e20260903-recuperado.db` (1.197 MB,
`quick_check = ok`). Era a única cópia do corpus que serviu 5 dias de ensaio; um restart a
teria apagado para sempre.

##### O que o corpus do serving realmente contém

| medida | valor |
|---|---|
| total de `chunks` | **67.187** |
| `MAX(created_at)` | **2026-08-24 01:06:35** |
| os 53 ids "mortos" do §10.9 | **presentes** |
| chunks de sessão de 08/09 | **0** |
| `agentFresh` elegível | **0** |

##### 🔴 Correção do §10.7: o canal NÃO mudou de composição para o serving

O `gatilho-composicao.mjs` lê `current.db` e resolve o symlink **a cada execução horária**;
o serving lê o inode de 03/09. Hoje os dois divergiram pela primeira vez: o gatilho vê
**219** candidatos de `agentFresh`, o serving vê **0**.

Logo o `RED` de `2026-09-08T06:09:04Z` é **verdadeiro sobre o corpus do gatilho e falso
sobre o canal que o ensaio serve**. `interleaveFresh` continua sendo função-zero. **Não
existe "regime intercalado"**, e os 7 epochs que o §10.7 lista como afetados **não foram
afetados**. A decisão de tratamento registrada ali (nenhum epoch sai) fica **sem objeto**
— e não é revogada, porque não havia o que tratar.

⚠️ **O gatilho funcionou por coincidência até hoje.** Os dois corpora concordavam em
`agentFresh = 0` porque o banco estava congelado (§10.5) — não porque o gatilho vigiasse a
grandeza certa. Vigiar o corpus **do symlink** quando o serving tem um **fd** é a mesma
família de "monitor que reimplementa o predicado do código": ele mede uma coisa parecida,
que coincide até deixar de coincidir.

##### 🔴 Correção do §10.5: o congelamento não terminou em 07/09 — está em curso

O §10.5 mediu que o corpus estava congelado em `2026-08-24 01:06:35` por defeito do
watcher, e datou o conserto em `2026-09-07T14:06:13Z`. O conserto descongelou o **banco
vivo** e os **snapshots** seguintes. Não descongelou o **serving**: para ele
`MAX(created_at)` segue `2026-08-24`, e seguirá até o processo reabrir o arquivo.

Os "6 de 234 epochs afetados" do §10.5 estão portanto **subcontados**: o congelamento
alcança todo epoch servido por este processo, do `2026-09-01` em diante e **sem fim
declarado**.

##### O que este achado NÃO explica — delimitado por medição, não por suposição

| snapshot | total | `MAX(created_at)` | `agentFresh` |
|---|---:|---|---:|
| serving real (03/09) | 67.187 | 2026-08-24 01:06:35 | 0 |
| `e20260906T060001Z` | 67.187 | 2026-08-24 01:06:35 | 0 |
| `e20260907T060001Z` | 67.187 | 2026-08-24 01:06:35 | 0 |
| `e20260908T060004Z` | **67.606** | **2026-09-08 02:37:34** | **253** |

Os snapshots de 03/09 a 07/09 são **equivalentes em conteúdo** — o banco esteve congelado
desde 24/08, então qual deles se usa era **inerte**. A divergência começa **exatamente** no
snapshot de `2026-09-08 06:00Z`. Consequências:

- os vereditos de dose até o epoch `2026-09-06` foram medidos em 07/09 09:12Z com o
  snapshot de 07/09 ⇒ corpus **equivalente** ao do serving ⇒ **não** são invalidados por
  este achado;
- o `faltam=1` do §10.9 e o `dose-servida-inerte` de 09-04/09-05 **não** se explicam pelo
  fd, pelo mesmo motivo. O primeiro segue sem causa confirmada;
- o que este achado invalida é o `RED` de composição de hoje e a medição do §10.7 —
  ambos posteriores a 08/09 06:00Z.

⚠️ Registro deste raciocínio porque a tentação era atribuir **tudo** ao fd, que é uma
causa vistosa e recém-achada. Três dos quatro sintomas do dia são anteriores à divergência
e continuam com as suas próprias causas.

##### A decisão que isto abre, e ela não é minha

Reiniciar o `nox-mem-api` realinha o corpus — e faz o canal do serving pular de 67.187
para 67.606 chunks e de `agentFresh = 0` para 253, **de uma vez, no meio do ensaio**. Não
reiniciar mantém o ambiente estável e consistente com os epochs já servidos, ao custo de
uma validade externa presa a 24/08 pelo resto do estudo. As duas escolhas precisam ser
declaradas, e a fronteira do restart — se houver — tem de cair numa fronteira de epoch,
não no meio de um.

E há um **fix de código** por trás: o serving deveria reabrir o snapshot na virada de
epoch, ou seguir o symlink em vez de manter o descriptor. Implementá-lo **muda o
comportamento do ensaio**, e por isso não é conserto rotineiro.

#### 10.11 🔴 A data do realinhamento era premissa falsa: `agentFresh` **não** volta a zero

**Registrado em 2026-09-09, antes de qualquer ação e antes de consultar qualquer
desfecho.** O que foi medido para decidir é **exclusivamente** a proveniência do fluxo
de ingestão e a distribuição temporal do pool. Nenhum resultado do ensaio foi
computado, consultado ou estimado.

O §10.10 fixou o realinhamento em `2026-09-15 09:00Z` sob a premissa de que os 253
chunks de sessão de 08/09 sairiam da janela de 7 dias às `2026-09-15 00:00:00Z` e
`agentFresh` **voltaria a 0 por expiração**, tornando o restart uma pura atualização de
corpus. A premissa supõe que **nada mais entra**. Está falsa.

**Medido em 2026-09-09:**

| fato | medição |
|---|---|
| elegíveis na janela | **285** = 219 (`source_date` 08/09) + **66 (09/09)** |
| entrada dos 66 | `created_at` 01:01:00 → 01:02:13, **3 arquivos** `sessions/boris/*` |
| cron responsável | **nenhum** — a ingestão é por *hook* (`nox-mem-ingest.sh`), disparada por **atividade de agente** |
| `session-distill` do nightly | **`Phase 4: Sunday`** — próximo domingo é **2026-09-13** |
| histórico de ingestão de sessão (60 d) | rajadas em jul/ago, **nada de 11/08 a 07/09** (28 d), retomada em 08/09 |

Duas consequências, e a segunda é mais importante que a primeira.

**(a) O script abortaria para sempre.** A pré-condição 3 exigia `agentFresh == 0`. Com
`session-distill` rodando domingo 13/09 e o *hook* injetando a cada sessão de agente, a
condição não se satisfaz em 15/09 — nem depois. Um script de ação cujo predicado exige
um estado que não retorna não falha: **fica calado**. É a regra 9 do `CLAUDE.md`
(*guarda cujo predicado exige o dado que falta não cobre a falta do dado*) aplicada a um
caminho de **ação**, onde o silêncio é indistinguível de "ainda não chegou a hora".

**(b) O regime da calibração era o regime QUEBRADO.** O buraco de 28 dias na ingestão de
sessões coincide com a migração que moveu endereço e schema das sessões, consertada em
07/09. A medição de `agentFresh` **vazio** de 26/08 — que fundamenta a escala de dose de
27/08 — foi feita **dentro** desse buraco. Não existe "voltar ao regime da calibração"
sem quebrar a ingestão de novo. O canal com `agentFresh` não-vazio é o comportamento
**correto** do sistema; o outro era o defeito.

⇒ Esperar a expiração não é conservador, é **indefinido**. E cada dia de espera é um dia
em que o serving expõe a partir de um corpus congelado em `MAX(created_at) = 2026-08-24`.

**Delimitação honesta do custo de esperar.** O congelamento atinge **os dois braços
igualmente** — é o mesmo corpus para tratamento e controle. Ele **não** enviesa a
comparação interna; degrada **validade externa** (o ensaio mede sobre um corpus que
envelhece). Já a composição do canal muda a **posição** dos designados no `interleave`,
o que afeta a **dose efetiva** — e essa é interna. Portanto a pressa não se justifica
pelo congelamento; o que se justifica é **não esperar por um evento que não vem**.

### Decisão

**Realinhar em `2026-09-10 09:00Z`** (quinta), não em 15/09. Escolha da fronteira:

| epoch | dia | arm | por que importa |
|---|---|---|---|
| 2026-09-09 | qua | treatment `w=2.0` | **em curso** — não se corta epoch no meio |
| **2026-09-10** | **qui** | **control `w=0`** | ⬅️ **fronteira escolhida** |
| 2026-09-11 | sex | control `w=0` | 2º epoch de controle limpo no regime novo |
| 2026-09-12 | sáb | treatment `w=4.0` | 1º tratamento **inteiramente** dentro do regime novo |

O regime novo estreia em **controle**, com dois epochs de controle antes do primeiro
epoch de tratamento — o contraste dentro do regime começa sem dose, e o primeiro
tratamento nasce inteiro. Estrear numa fronteira de tratamento faria o regime novo
começar já sob dose.

**A pré-condição 3 muda de natureza:** deixa de exigir `agentFresh == 0` e passa a
**medir e registrar** `agentFresh`/`globalFresh` no `ndjson`, abortando apenas se a
**medição** falhar. As outras quatro seguem intactas e abortivas: fronteira de epoch,
guarda de alinhamento em RED, 19/19 designados presentes, recuperação do corpus antigo
com `quick_check = ok`.

**Regra de tratamento — inalterada.** A análise já pré-especificada no §10.7 é o
instrumento para isto e não precisa de emenda: *primary* + co-estimador ITT com todos os
epochs, **mais** o mesmo par com os epochs do regime intercalado excluídos. O que o
§10.11 acrescenta é que a fronteira do regime novo passa a ser **`2026-09-10 09:00Z`**, e
que o conjunto "regime intercalado" é `{09-08 … 09-09}` do canal congelado mais tudo a
partir de `09-10` no canal realinhado — a serem enumerados a partir do `ndjson` dos
guardas, não de contagem à mão.

⚠️ **Isto não retira nada do §10.10.** O achado do *file descriptor*, a delimitação dos
snapshots equivalentes (03/09–07/09) e a validade dos vereditos de dose até o epoch
09-06 continuam de pé. O que muda é **só a data** e o **predicado da pré-condição 3** —
e muda porque a justificativa aritmética da data supunha um mundo sem ingestão.


#### 10.12 A causa do `faltam=1`: o replay descarta briefs **lentos**

**Medido em 2026-09-09.** Fecha o item que o §10.4 deixava aberto e que o HANDOFF
registrava como "sem causa estabelecida". Nenhum desfecho foi consultado: o que se mediu
é o **mecanismo de casamento** entre o log de serving e o `brief_log`.

Distribuição de `cands.length` em `idDoBrief()` sobre a janela de 09-06: **`{0: 1, 1: 671}`**
— reproduz `estados=671 / n_janela=672 / faltam=1` exato. O único descartado é
`ts=2026-09-06T23:07:02.425Z`, `agent=nox`, `churn=0`.

O `brief_id=a1ebbe3f-3567-4169-a6c5-84e601bd0aa7` tem as **dez** linhas. O que se
espalha é o `served_at`:

| `id` | `served_at` | `chunk_id` |
|---|---|---|
| 647955 | `2026-09-06 23:07:02` | 116467 |
| 647956 … 647964 | `2026-09-06 23:07:09` | os outros nove |

`idDoBrief()` casa por `served_at IN (t, t+1s, t+2s)`. As nove de `:09` ficam **fora**, o
`GROUP_CONCAT` devolve **um** id, não casa com os dez do ndjson, `cands.length === 0`, e o
estado sai por `continue`.

**Span por brief na janela:** 670 com span 0 s, 1 com 1 s, **1 com 7 s**. Um outlier, e é ele.

### Três afirmações anteriores que isto corrige

1. **O comentário do `gatilho-saturacao.sh`** atribuía o descarte a *"escrita incompleta
   no `brief_log` (1 linha de 10)"*. **Errado na causa, certo no alvo:** o brief tem as
   dez linhas; "1 linha de 10" é o que se **vê** de dentro da janela de 3 s. Sintoma
   lido como causa. Corrigido no próprio arquivo, com o mecanismo.
2. **A medição por `brief_id` de 08/09** (672 briefs, dez linhas cada, zero incompletos)
   está **certa** e refuta *incompletude* — mas não localiza o defeito, e concluir dali
   que "a explicação está falsificada, logo não há defeito ali" inverte o sentido. As
   duas medições são verdadeiras sobre **populações diferentes**: a janela do epoch
   inteira contra uma janela de 3 s.
3. **A hipótese de ambiguidade** (`cands.length > 1`, plausível porque `served_at` tem
   resolução de segundo e colide entre briefs) está **morta**: deu 0, não 2.

### Por que é viés, e não ruído

O critério de exclusão não é composição do brief — é **latência de escrita**. Latência
não é independente de carga, e carga não é independente de quanto trabalho o brief deu.
⇒ O descarte é potencialmente **correlacionado ao que se mede**. É a mesma classe do
`estados=640` (`672 − 32`) do §10.4 — *regra que exclui em vez de atribuir* — na versão
de tamanho 1, com um critério novo.

Com `n=1` e `churn=0`, o dano **neste** epoch é nulo, e o veredito de 09-06 segue
utilizável. A classe é que fica registrada.

### O que o conserto **não** é

Casar por `brief_id`: o `p2_outcome` do ndjson **não tem** esse campo — medido, 0/672. Os
campos são `ts, tag, epoch, modo, w, servido, scope, agent, ids_controle, ids_tratado,
churn, would_enter, would_leave, fresh_added, designated_ids, boost_by_id`. A
reconstrução por (agent, segundo, ids) é hoje necessária.

Duas frentes, nenhuma executada nesta entrada:

- **histórico** — alargar a janela de casamento e desambiguar pelos ids. Exige medir o
  custo em ambiguidade **antes**: alargar aumenta `cands.length > 1`, que é a *outra*
  saída para `null`. Trocar um descarte por outro não é conserto.
- **raiz** — emitir `brief_id` no `p2_outcome`, eliminando a reconstrução para frente.

⚠️ Enquanto nenhuma das duas estiver feita, todo `faltam=N` do gatilho deve ser lido como
**"N briefs cuja escrita atravessou a janela de casamento"**, e não como perda de dado.


#### 10.13 🔴 Dois defeitos que o desenho não previa: o canal perde capacidade no corpus atual, e os designados saem do pool em 2026-09-20

**Registrado em 2026-09-09, antes de qualquer ação e sem consultar desfecho.** O que se
mediu é **capacidade do canal** e **elegibilidade dos alvos** — nunca resultado.

### (A) O RED de produção é artefato de instrumento — e o número inverte para o lado ruim

O `run-saturacao.sh` passa `--corpus /var/lib/nox-mem/epochs/current.db`. O serving **não
lê** esse corpus desde 03/09 (§10.10). Rodando o **mesmo** gatilho, **mesmo** log
(`sha256 d5ba483d…`), **mesmo** `estados=672`, **mesma** janela, variando **só** o corpus:

| corpus | veredito | `mexem_servido` | `mexem_absurdo` | folga |
|---|---|---:|---:|---:|
| o que o serving **leu** (recuperado do `fd`, `agentFresh=0`) | **GREEN** dose responsiva | **20** | **37** | **0,5405** |
| `current.db` (produção usou, `agentFresh=285`) | RED sem capacidade | **0** | **0** | — |

⇒ **A intervenção está viva no epoch 09-08.** O par utilizável é `20 / 37 / 0,5405`, do
corpus servido. O RED diário do gatilho é **falso positivo** enquanto o `fd` estiver
pinado, e conta no `red=` do morning report.

⚠️ **E a dose não conserta.** A corrida de produção testou `w = 100 000`: `mexem_absurdo=0`.
Boost é **aditivo** (regra 5 do `CLAUDE.md`); se a dose absurda não move, **nenhum `w`
move**. Isto **não** é falha de calibração — é falta de capacidade do canal. Recalibrar
`w` sobre o corpus novo não recupera nada.

**Mecanismo NÃO estabelecido, e o candidato do `agentFresh` está FALSIFICADO**
(2026-09-09, sessão `memoria-nox-21`): 384 de 672 briefs são de agentes com sub-pool
vazio nos **dois** corpora, para quem o freshPool é estruturalmente idêntico, e `mexeu`
é 0 sobre os 672. Ver §10.14. Outro candidato lido no código, **não verificado**: a Fase 0 de
`pickDedup` reserva `pinned` (high-pain já presentes no brief) que *"entram primeiro e
nunca são expulsos pelo freshness slot"*, e *"pinned excedente come dos fresh slots"* —
com `freshSlots = 2`, dois pinned zeram o canal. Não meço isso aqui, e **não atribuo**:
os dois corpora diferem em `agentFresh` (0 → 285), `globalFresh` (108 → 115) e 419
chunks. Atribuir a `agentFresh` seria inferência sobre o `interleaveFresh`, e a classe
*reconstrução modela regra que o código nunca aplica* já apareceu **cinco vezes** neste
repo.

### (B) Os alvos saem do pool em 2026-09-20, e o desenho não fecha

Os 19 designados têm **`source_date` = NULL**; o `2026-08-21 22:51:23` é o
**`created_at`**, e é um **único** valor para os 19 — eles saem da janela **juntos**.
(Medi com `COALESCE(source_date, created_at)` e reportei como `source_date`; a
desambiguação é da sessão `memoria-nox-21`, e **fortalece** a conclusão: caindo no
`created_at`, o predicado não se renova nem por reingestão parcial — só criando chunk
novo, que é exatamente o que troca o id.) A janela do sub-pool global é
`freshGlobalMaxAgeDays = 30` (default; nenhum `NOX_BRIEF_DIV_FRESH_*` no env do unit)
⇒ saem em **2026-09-20 22:51:23**. Depois disso **nenhuma
dose os alcança, em nenhum corpus** — não é questão de capacidade, é elegibilidade.

| | |
|---|---|
| epoch 1 no ar | 2026-09-01 |
| alvos elegíveis até | **2026-09-20** |
| último epoch previsto | 2027-04-22 |
| ⇒ fração do ensaio **com alvo alcançável** | **8,2 %** (19 dias de 232) |

Um ensaio de 234 epochs com alvos fixos é **incompatível** com um pool que só admite os
últimos 30 dias. É inconsistência **interna** do desenho, descoberta agora — não mudança
de circunstância.

**E o `source_date` não pode ser renovado.** Os **19 de 19** arquivos-fonte
(`memory/entities/lessons/<hash>.md`) estão **apagados do disco**, **nunca foram
versionados** (`git log --all --diff-filter=AD` vazio; `git ls-files` devolve 42, que são
os que existem) e **não estão nos checkpoints** (0 arquivos em `entities/lessons/`).
Renovar exigiria reingestão, que **troca os ids** e mata a designação (§10.9).

⇒ Os 19 chunks no banco são a **única cópia** do ativo. Salvos em
`/var/lib/nox-mem/p2/DESIGNADOS-CONTEUDO-20260909T103409Z.json` (19/19, `sha256 92060a9f…`,
modo 600).

⚠️ **O guarda de designados diz GREEN 19/19 e está certo pelo seu predicado** — ele lê o
**banco**, onde os chunks estão. É cego para "o arquivo-fonte não existe", que é a regra 9
do `CLAUDE.md` reaparecendo **dentro do guarda escrito em 08/09 para proteger este
ativo**. Perna nova é necessária.

### Decisão do Toto (2026-09-09) e a dependência que a condiciona

Escolhido: **alargar a janela do pool global** e **manter o cron do realinhamento
desarmado**.

> ⚠️ **A primeira metade desta decisão foi REVERTIDA no mesmo dia — ver §10.14.** O que a
> reverteu: o corpus congelado não protege da expiração (o predicado usa o relógio de
> **request**), logo alargar não prolonga o ensaio, prolonga o registro de um ensaio
> inerte. O cron segue desarmado.

Alargar resolve **(B)**. Medido, sobre o corpus atual:

| janela | pool global | designados em 21/09 | cobre 22/04/2027 |
|---|---:|---|---|
| 30 d (atual) | 115 | **0/19** | não |
| 90 d | **116** | 19/19 | não — só até 19/11/2026 |
| ≥ 244 d | **305** | 19/19 | sim |

Cobrir o ensaio inteiro **triplica** o pool (115 → 305). Não existe valor que cubra
abril/2027 sem esse salto: ele acontece entre 90 d e 180 d, e o mínimo necessário é 244 d.

🔴 **A dependência:** `diversityConfigFromEnv()` é chamado **por request**
(`dist/api/brief.js:819`) mas lê `process.env`, e o env de um processo em execução **só
muda com restart**. Logo alargar a janela **exige o restart** que a segunda decisão mantém
desarmado — e o restart traz o corpus atual, que é onde **(A)** vale. As duas decisões,
como escolhidas, são **incompatíveis** sem resolver (A) primeiro.

### Delimitação: o instrumento **não** expira; o ensaio expira

O harness de replay compensa a idade (`cfgEm` soma `desloc` a
`freshGlobalMaxAgeDays`), como o cabeçalho promete. Depois de 2026-09-20 o replay
**continua respondendo certo** — quem deixa de morder é a **produção**. Sem esta
delimitação, o item acima se leria como se a medição também fosse expirar.

### Dois defeitos do instrumento, achados ao investigar (A) — consertos pendentes

**(i) O recibo não registra o corpus.** Os campos gravados são `absurdo, estado, folga,
janela, motivo, n_janela, semantica, servido, sha256_janela, tag, ts, via, w_servido`.
Há `sha256` **do log** e **nada** do corpus. Consequência medida: o GREEN `20/37` e o RED
`0/0` têm o **mesmo** `sha256_janela = d5ba483d…`, a mesma janela e o mesmo
`estados=672` — **dois vereditos opostos com recibos indistinguíveis**. Enquanto
existirem três corpora em jogo (o `fd` pinado, o symlink que anda, os snapshots), nenhum
veredito de saturação é interpretável. Conserto: gravar `corpus_path` **e**
`corpus_sha256` no ndjson e no status.

**(ii) `--corpus current.db` é um symlink que anda.** O relink acontece às 06:02, então o
gatilho replaya o epoch **fechado de 08/09** contra o snapshot de **09/09**, e o alvo
troca sozinho todo dia. Conserto: apontar para o snapshot do epoch que fechou. É a lição
do cabeçalho do próprio harness (*"a primeira remediação usou o DB vivo como corpus
quando a produção serve o snapshot de epoch"*) reaparecida na **fiação do wrapper**.

### Evidência independente do instrumento

Medido **direto do `p2-serving.ndjson`**, sem replay (sessão `memoria-nox-21`):

| epoch | n | w | servido | `churn>0` | desig. controle → tratado |
|---|---:|---|---|---:|---|
| 2026-09-06 | 672 | 7,5 | tratado | **38** | 124 → 144 |
| 2026-09-07 | 672 | 0 | controle | 0 | 175 → 0 |
| **2026-09-08** | **672** | **2** | **tratado** | **20** | **172 → 187** |

`churn > 0` em **20** de 672 (2,98%, contra 3,74% da era shadow) — **o mesmo 20** do
`mexem_servido`. Duas vias independentes, e esta **não depende de escolher corpus**, que
é justamente o parâmetro que estragou a outra. ⇒ O mecanismo **mordeu em produção** no
epoch 09-08.

**Nada foi aplicado.** O que está feito: ativo salvo, cron desarmado, medições acima.


#### 10.14 Decisão revisada (2026-09-09, tarde): **não alargar a janela**. O ensaio termina em 2026-09-20

**Registrado antes de qualquer ação e sem consultar desfecho.**

A decisão de manhã (§10.13) foi *alargar `freshGlobalMaxAgeDays`*. Ela está **revertida**,
e o que a reverteu é uma medição que faltava: **o corpus congelado não protege da
expiração.**

O predicado do sub-pool usa `julianday('now')` (`dist/api/brief.js:470`) — relógio de
**request**. O `fd` pinado congela os **dados**, não o **tempo**. Medido no próprio
corpus servido (o recuperado):

| data | designados no `globalFresh` |
|---|---|
| 2026-09-09 | 19/19 |
| 2026-09-15 | 19/19 |
| 2026-09-20 | 19/19 |
| **2026-09-21** | **0/19** |

⇒ Os dois cenários terminam no **mesmo dia**:

| cenário | epochs úteis |
|---|---|
| **não alargar** | **até 2026-09-20**, ~20 epochs, com canal medidamente ativo (`churn>0` em 20/672 no epoch 09-08) |
| alargar | os mesmos ~20 **mais** 214 epochs cujo valor **não está estabelecido**, ao custo de triplicar o pool |

⚠️ **O que eu NÃO posso afirmar, e quase afirmei.** A primeira versão desta seção dizia
que alargar daria *"214 epochs de zero"*, apoiada no `mexem_absurdo = 0` sobre o
`current.db`. Isso **não** se sustenta, e a refutação veio da sessão `memoria-nox-21`:

- **A hipótese do `agentFresh` está falsificada.** **384 de 672 briefs (57,1%)** são de
  agentes com sub-pool **vazio nos dois corpora** (`nox:0, atlas:0, lex:0`), para quem
  `interleaveFresh([], globalFresh) === globalFresh` — freshPool estruturalmente
  idêntico. Se o deslocamento fosse a causa, esses 384 continuariam se movendo. `mexeu`
  é 0 sobre os **672**.
- **O replay rastreava a produção até 01/09 e parou quando o corpus divergiu.** Em 29/08:
  `mexeu(2) = 30` contra `churn>0 = 30`. Os três REDs (05, 06 e 09/09) são os três dias
  em que deixou de rastrear, e o `fd` pinado tem mtime `2026-09-03 17:30`.

⚠️ **E a correção da correção (mesma tarde).** Eu havia concluído daí que *"`mexeu = 0`
aparece quando o corpus do replay não é o que serviu"* — e **retirei uma afirmação
verdadeira**. `mexeu` é **interno ao corpus**, verificado no código:

```js
// dist/api/brief.js:628
diffP2 = diffBriefs(alt.items.map(i=>i.id), altBoosted.items.map(i=>i.id), …)
```

`alt` (sem boost) e `altBoosted` (com boost) saem **ambos** de
`buildBriefDiverse(corpus, …)`, o **mesmo** banco; e o replay lê `churn: out.diffP2.churn`.
Logo `mexeu` conta estados em que a dose muda a saída **contra a saída sem dose no mesmo
corpus** — não depende de casar com o corpus servido.

⇒ **`mexem_absurdo = 0` é afirmação verdadeira sobre o `current.db`.** O par que rodei é
contraste isolado com **uma** variável (mesma janela `sha256 d5ba483d…`, mesmo
`estados=672`, mesmo serve-state, mesmos `t_ref`):

| corpus | `mexeu(2)` | `mexeu(10⁵)` | leitura |
|---|---:|---:|---|
| recuperado (o que **serviu**) | **20** | **37** | canal existe e responde |
| `current.db` (realinhado) | **0** | **0** | canal ausente |

E o **20** bate exato com o `churn>0 = 20` que a produção registrou, por via independente
do replay ⇒ **validação externa**: no corpus que serviu, o harness reproduz o mundo.

**Conclusão que os dois números sustentam:** não é que o replay falhe no corpus novo — é
que **o corpus novo mata o mecanismo**, medido até em dose absurda. O que fica
indecidível é a **magnitude sob serving real**, não o **sinal**. (E a "quebra de
rastreamento" a partir de 05/09 é compatível: o harness sempre calcula certo sobre o
corpus que **recebe**; o que mudou é que o corpus recebido deixou de ser o servido.)

**Então o fundamento é mais forte do que eu havia escrito.** Alargar a janela exige
restart; o restart faz o serving abrir um snapshot construído do vivo **realinhado** — a
família medida com `mexeu(10⁵) = 0`. Não são 214 epochs de valor *desconhecido*: há
medição apontando para valor **nulo**. Somado a:

1. A expiração de 2026-09-20 encerra o ensaio **nos dois cenários** — o corpus congelado
   congela dados, não o tempo.
2. Cobrir abril/2027 exige janela ≥ 244 d, que **triplica** o pool global (115 → 305),
   mudando a composição do canal para **todos** os candidatos, em ensaio pré-registrado.
3. O que se compraria são 214 epochs num corpus onde o canal **não responde nem a dose
   absurda**, contra um custo conhecido de mudança de desenho.

⚠️ O que **não** está estabelecido: **por que** o corpus realinhado mata o mecanismo.
`agentFresh` está **excluído** (os 384 briefs de sub-pool vazio); sobram `globalFresh`
108 → 115 e a deriva de +537 chunks no pool principal, e nenhuma das duas foi medida. E
não se sabe se um epoch **servido** do corpus novo se comportaria como o replay dele —
isso exigiria o restart.

Trocar composição de pool sob incerteza sobre o resultado é o oposto do que um
pré-registro serve para prevenir.

### O que fica decidido

1. **Nada é alargado.** `freshGlobalMaxAgeDays` permanece em 30 (default).
2. **O cron de realinhamento permanece desarmado.** Reiniciar antecipa a inércia sem
   comprar nada.
3. **O ensaio encerra em `2026-09-20 22:51Z`**, por expiração dos alvos, com os epochs
   de `2026-09-01` a `2026-09-20`. O que se reporta é o que esses epochs contêm, com a
   limitação declarada — não os 234 pré-registrados.
4. **Os 11 dias restantes vão para os consertos de instrumento**, que não tocam o
   serving: `corpus_path`/`corpus_sha256` no recibo, e `--corpus` apontando para snapshot
   de epoch fechado em vez do symlink que anda (§10.13, i e ii).

### O que o ensaio entrega, dito sem eufemismo

**~20 epochs de 234 (8,5%).** A potência cai proporcionalmente e a alocação `117/39/39/39`
não se realiza — o que existe é o prefixo dela. A causa é **defeito de desenho**, não
circunstância: alvos fixos designados sobre um pool que só admite os últimos 30 dias
nunca poderiam sustentar 8 meses, e isso era verdade desde a designação de 2026-08-26.

⚠️ **O que NÃO é conclusão sobre a intervenção.** O mecanismo **funcionou** onde pôde
agir: `churn>0` em 20 de 672 no epoch 09-08 e 38 de 672 no 09-06, por duas vias
independentes (log de produção e replay sobre o corpus servido). A limitação é de
**duração**, não de efeito — e escrever "a intervenção não se sustentou" seria a conclusão
nula tirada de um prazo, que é a classe que este documento persegue desde o §10.4.

### Se um ensaio futuro for desenhado

O erro a não repetir: **designação por id fixo é incompatível com pool por janela de
recência.** Ou a designação acompanha uma coorte rotativa, ou o alvo tem de estar num
pool sem janela. E o guarda tem de vigiar **elegibilidade**, não só presença — o
`gatilho-designados.mjs` dizia GREEN 19/19 todos os dias enquanto o prazo corria, e
estava **certo** pelo seu predicado.


## Se a decisão mudar

A máquina do depósito está pronta e **não executada**: `deposit/PLAN-v1.13.md` e
`deposit/deposit-v1.13.sh` (99 arquivos, 45 uploads, três gates passando, readback
duplo). Nada foi enviado ao Zenodo. Voltar para a opção 1 (depositar) ou 3 (agrupar com
o protocolo prospectivo) custa o token e um `prepare`.

⚠️ Se o depósito acontecer meses depois, **reconferir os 6 arquivos substituídos por
md5 antes do `prepare`** — `claims_check.py` e a emenda continuarão recebendo edições, e
o `sync` só corrige o que sabe comparar.
