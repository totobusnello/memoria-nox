# Emenda v1.12 — RASCUNHO

**Emenda:** OSF `yf7d2` (registrado 2026-08-18T07:56:44Z) · Zenodo
`10.5281/zenodo.21978476` (concept `10.5281/zenodo.21964093`)
**Status:** rascunho, não depositado. **Uma** emenda, conforme decidido.
**Escrito antes do sorteio de `T_seed_assign`** — que é precisamente por que a
ordem "congela o mecanismo, depois sorteia" foi adotada em 17/08.

---

## 🔴 1. RETRATADO — a intervenção NÃO é nula. O furo veio da designação

**Um rascunho anterior desta emenda (commits `38ee268`, `4eca015`) afirmava que a
intervenção registrada era nula em todos os braços.** Está errado. A revisão
adversarial (Kimi, recibo 2026-08-21T132205, 56.687 bytes) achou o furo e ele
verifica.

### O que eu errei

Argumentei que `W_OUTCOME = w · Δ_cut · severity` é monotônico em `severity`, logo
não reordena as severidades, logo o conjunto servido é idêntico em todo braço.

Isso vale **se todos os chunks forem impulsionados**. A regra de designação
registrada impulsiona **um chunk por grupo de assinatura** (§2:466, *"one
designated chunk per opportunity"*). Portanto o pool de nunca-servidos mistura
**designados (com `w`) e não-designados (sem `w`)** — e aí a dose reordena:

| `w` | S1 **designado** | S2 não-desig. | S3 não-desig. | reordena? |
|---|---|---|---|---|
| 0 | 0,6700 | 0,6950 | 0,7200 | não |
| 2,0 | 0,6915 | 0,6950 | 0,7200 | não |
| **4,0** | **0,7130** | 0,6950 | 0,7200 | **S1d > S2** |
| **7,5** | **0,7506** | 0,6950 | 0,7200 | **S1d > S2, S1d > S3** |

E contra o estoque incumbente de nunca-servidos (barra medida 0,684477), a dose
**vira a entrada**:

| `w` | S1@0d designado | entra? |
|---|---|---|
| 0 | 0,6700 | não |
| **2,0** | **0,6915** | **entra** |
| 4,0 | 0,7130 | entra |
| 7,5 | 0,7506 | entra |

Este é o contraexemplo do Kimi, reproduzido com os números do próprio dossiê.

### O que isso significa — e é notícia boa

**O mecanismo registrado funciona, mas por uma razão diferente da registrada.** Não
por *cruzar um limiar* `CUT_FRESH`; por **vencer o desempate de salience entre
nunca-servidos**. E a estrutura que emerge é justamente a de três platôs que a
banda queria:

- `w = 2,0` — o S1 designado passa a barra do estoque incumbente, mas **não** passa
  um S2 não-designado
- `w = 4,0` — o S1 designado passa o S2 não-designado
- `w = 7,5` — passa também o S3

Dose-resposta com três degraus distintos, saindo do mecanismo real. O estudo está
em melhor forma do que a minha afirmação de nulidade, e melhor do que o próprio
raciocínio do registro.

### Consequência para a proposta de conserto

**A revisão da linha 449 pode ser desnecessária.** O canal existe dentro da
restrição registrada. Retiro a proposta de aplicar o boost no re-rank do pool
principal e o cap de 3/10 — ambos foram desenhados para consertar um problema que
não existe. O que resta a emendar é a **descrição** do mecanismo, não o mecanismo.

⚠️ E retiro a justificativa que dei para revisar o 449 ("os picks de cobertura a
0,7344 já superam o cut principal em 4 dos 6 agentes"). O número é real e medido
em 21/08 — mas em 20/08 os picks eram 0,684477, porque o estoque de nunca-servidos
ainda não havia drenado. Publiquei duas medições de regimes diferentes em
documentos adjacentes sem datar o regime, o que permitiu que o mesmo número
aparecesse em dois papéis opostos. Falha de documentação minha, não do revisor.

## 2. Retratado também: "não depende de λ"

Afirmei que a nulidade não dependia da taxa de chegada. Além de a nulidade ter
caído, a afirmação estava mal fundamentada em si: a competição se dá contra o
**estoque instantâneo de nunca-servidos**, que é a diferença entre taxa de autoria
e taxa de dreno. Ambas variam.

E já errei essa projeção uma vez, no dia anterior: estimei que o estoque de 38
levaria ~3 dias para drenar e ele zerou em **1** (52 primeiros-serves). Uma
dinâmica que eu projetei errado 24 h antes não sustenta um "por construção".

**Enunciado correto:** o efeito da dose é **condicional ao regime** — ao estoque de
nunca-servidos e à sua composição de severidades no instante do brief. Isso é
empírico e datado, não teoremático.

## 2-bis. Defeito de reprodutibilidade a consertar

O Kimi registrou que `src/api/brief.ts` **não existe neste repositório** — o código
que carrega todo o argumento vive na VPS
(`/root/.openclaw/workspace/tools/nox-mem/`) e é inauditável por quem lê o
depósito. A emenda tem de **carregar o trecho de código**, com o hash do commit
servindo, não só o path.

## 2-ter. Achados da segunda voz (Grok) — convergência e três itens novos

O Grok chegou ao **mesmo furo** que o Kimi, por caminho independente: o canal é
*first-admission vs incumbente nunca-servido*, e a dose paga o gap
(`2,0 × 0,043 × 0,25 = 0,0215` contra um gap de `0,0145`). Duas famílias de treino
distintas convergindo no mesmo defeito é o sinal mais forte que essa bateria dá.

Três itens que o Kimi não levantou:

**(i) Erro aritmético meu — 4 de 6, não 5.** `0,7344` supera lex (0,6100), nox
(0,6851), boris (0,6925) e forge (0,7051); **não** supera atlas (0,7613) nem cipher
(0,7922). Corrigido em `ARMS-DISTINGUISHABLE-2026-08-21.md` e aqui.

**(ii) O texto registrado não diz QUAL ranking recebe o boost.** A linha 449 diz
*"in the coverage-slot ranking"* — mas há **dois** estágios:

| estágio | chave | tem recência? |
|---|---|---|
| pré-rank SQL (`LIMIT 400`) | `0.55·imp + 0.10·pain + 0.1·[access>0]` | **não** |
| `ranked.sort` (JS) | `calculateSalience` completa | **sim** |

Toda a aritmética desta emenda usa o segundo. Se o boost entrasse no primeiro, o
degrau de `0,0250` e o span de recência de `0,0164` **não existiriam** — a chave
não tem termo de recência. A emenda tem de **nomear o estágio**, não herdar a
ambiguidade.

**(iii) A composição do pool incumbente, medida.** O Grok acusou que medi *um
arquivo* e chamei de pool. Medido: dos dois padrões elegíveis,

| padrão | chunks elegíveis | dentro da janela de 30 d |
|---|---|---|
| `memory/entities/%` | 190 | **0** |
| `memory/lessons.md` | 52 | **52** |

`memory/entities/%` contribui **zero** — os 190 chunks são todos mais velhos que a
janela, resíduo da migração de formato de julho. Então o pool incumbente **é**
aquele arquivo; não foi recorte, foi o conjunto. ⚠️ Mas isso não vale para os
chunks do estudo: o write path escreve em `memory/entities/lessons/…` com idade 0,
logo **dentro** da janela. No epoch 1 o pool é *chunks do estudo (entities, novos)*
disputando com *o fluxo de `lessons.md`* (~33/dia autorados). É essa a competição
a modelar.

## 2-quater. Terceira voz (DeepSeek): concessão da carga central

A crítica que sustenta as outras: **troquei uma aritmética de nulidade por uma
aritmética de dose-resposta, e nenhuma das duas tem desfecho observado.** Isto é
correto e eu concedo.

Nenhum chunk designado foi servido em `w` nenhum. `p2_verdict` **não existe** no
banco de produção — o write path está no ar e tem zero linhas, porque nenhum
veredito foi postado. Os "três platôs" são identidades de `base(sev,idade)`
avaliadas contra limiares; não são medição de nada.

### Quatro correções concretas

**(a) O terceiro platô atravessa duas classes de severidade.** S1 designado a
`w = 7,5` vale **0,7506** e passa **S3 (0,7200) e S4 (0,7450)**. Descrevi como
"passa também o S3". Não é degrau alinhado a classe.

**(b) As margens estão dentro do ruído.**

| quantidade | valor |
|---|---|
| margem de `w = 2,0` acima da barra | **0,0070** |
| margem de `w = 2,0` abaixo do S2 não-designado | **0,0035** |
| spread do cut principal entre agentes | **0,1822** |

As margens são 2–4% da variação observada. Chamar isso de platô limpo foi
otimismo construído sobre 24 h.

**(c) Escolher `0,684477` como "a barra" é, ela mesma, uma emenda não registrada.**
A barra é **input** do efeito. Substituí o `0,8524` registrado por um valor medido,
escolhido entre seis, sem regra de decisão declarada. É a mesma classe de erro que
motivou a retratação da manhã. A emenda tem de registrar **a regra que escolhe a
barra**, não um valor.

**(d) Retiro a taxa de autoria de "~33/dia".** Não é estimável a partir de
`created_at`, porque re-ingest recria os chunks e reseta o campo. Os "232 em 7
dias" que citei são, muito provavelmente, artefato de re-ingest. Autoria elegível
observada: **52 num único instante (20/08 02:02:03) e 0 nos outros 9 dias**.

### O estimando não está especificado — e isso é o item mais grave

O registro define entrada como **cruzar um limiar**. A dinâmica medida é de
**fila** (buffer 38→0 em um dia, dreno ~600 picks/dia). São estimandos diferentes:

| leitura | estimando |
|---|---|
| limiar | `P(salience_designado > barra)` — precisa de barra fixa |
| fila | `P(designado servido em ≤ k slots)` — hazard, barra pode ser vazia |

A aritmética que publiquei usa o primeiro; o sistema executa o segundo. Em dia de
buffer vazio **até `w = 0` serve**, e o estimando de limiar fica mal-definido
quando o conjunto comparador é vazio ou unitário. A emenda precisa **escolher o
estimando**, declarar o estado da fila em T0, e dar a regra para dias de buffer
vazio (sucesso / censura / exclusão).

### Uma objeção que NÃO procede, verificada

DeepSeek perguntou por que trato como inertes os 190 chunks de
`memory/entities/%`. A `WHERE` de `fetchFreshCandidates` (`brief.ts:605-608`) tem
filtro de idade — `julianday('now') − julianday(COALESCE(source_date, created_at)) <= freshMaxAgeDays`.
Medido: os 190 têm **42,1 a 78,9 dias**, contra janela de 30. São excluídos pela
consulta. Inércia confirmada por medição, não por suposição.

### E um achado novo, pior que o confundimento que eu já havia escrito

O filtro usa `COALESCE(source_date, created_at)`. Os 52 chunks de `lessons.md`
**têm** `source_date` — e todos os 52 carregam a **mesma data, 2026-08-20**, igual
ao `created_at`. Para um arquivo de 200 KB e 1.324 linhas que vem acumulando, 52
chunks compartilharem uma única `source_date` significa que o campo registra **o
evento de ingest, não a proveniência de cada lição**.

Consequência: re-ingest **rejuvenesce o arquivo inteiro** — para elegibilidade
(volta para dentro da janela de 30 d) e para o termo de recência da salience. Não
é só o histórico de serve que é zerado; é a idade. Isso amplia o confundimento da
§1 de `QUEUE-REGIME-2026-08-21.md`.

### O que fica

Não dá para estabelecer dose-resposta por aritmética. Precisa de **desfecho
observado por braço**, que precisa do write path com linhas, que precisa do painel.
**Paro de calcular níveis.** A emenda declara mecanismo, estimando e regras de
decisão; os níveis vêm da medição depois.

## 2-quinquies. A designação exclui 65% dos chunks escritos — medido

Primeira medição com a população real (55 chunks de falha adjudicada, 2026-08-21):

| tamanho do grupo de assinatura | quantos grupos | chunks |
|---|---|---|
| 1 | 12 | 12 |
| 2 | 2 | 4 |
| 4 | 2 | 8 |
| 6 | 1 | 6 |
| 8 | 1 | 8 |
| **17** | **1** | **17** |
| **total** | **19** | **55** |

A regra registrada impulsiona **um chunk por grupo de assinatura**. Logo:

- **19 de 55 chunks (34,5%)** entram na população tratada;
- **36 (65,5%) não recebem boost nenhum** — são escritos, competem no pool, e o
  tratamento não os alcança;
- o maior grupo concentra **17 chunks (31% do total) numa única assinatura**, onde
  16 competem sem boost contra 1 impulsionado.

**Por que isto importa para o estimando.** É exatamente o mecanismo que as duas
vozes adversariais identificaram ao derrubar minha tese de nulidade: o pool mistura
designados e não-designados, e é dessa mistura que a dose extrai efeito. Agora está
quantificado — e a razão 19:36 significa que a maior parte do que o write path
escreve é, do ponto de vista do tratamento, **massa de controle dentro do braço de
tratamento**.

⚠️ Isso não é defeito: a designação foi adotada precisamente para impedir o brief
só-de-lições-de-falha (§2:466, "46% das oportunidades" sob boost-em-todos). Mas a
§2 nunca declarou a **fração** que a regra exclui, e ela é grande.

## 2-sexies. Dois fatos operacionais medidos com a população real

**(a) O gate de cobertura admite um candidato por episódio.** Cada episódio gera 2
chunks (frontmatter + compiled). Medido: os 55 `compiled` têm `importance` 0,90 e
**passam**; os 55 `frontmatter` têm 0,40 e **nenhum passa**. O desenho está correto,
e agora verificado em vez de suposto.

**(b) O write path não embeda.** 110 chunks escritos, 110 sem vetor. O docstring
afirmava embedar; `embedText` nunca foi chamado (corrigido em `nox-workspace#48`).
Benigno para o estudo — o caminho de cobertura é SQL puro e o gate de maturidade
segura o chunk por ≥ 24 h, muito depois do `vectorize` do cron. Mas na janela o
chunk é invisível à busca semântica, e isso é fato sobre o corpus durante o estudo.

## 3. Correções a declarar

Cinco já decididas antes desta rodada:

1. **Não há corte no código.** `pick` fase 3 toma os primeiros `freshSlots` sem
   comparação. `CUT_FRESH` não modela o serving — nem como constante nem como
   quantil.
2. **Escada de severidade:** `0,0250 > 0,0163`, o que sai do lock de campos
   combinado com a janela de 30 d.
3. **O contraste primário é pooled 117 vs 117** (§3:344-351), não controle vs
   `w = 7,5`. A linha 521 está errada e é a fonte do engano.
4. **`CUT_FRESH` não sobrevive como modelo de serving** (item 1 acima, aplicado
   à designação: `argmin (0.7342 − base)/(Δ_cut·sev)` não descreve nada).
5. **`w = 2,0` está na borda** — 1,59-2,35 pelo critério registrado, o oposto de
   platô.

Três novas, desta rodada:

6. **Não há barra em salience.** O critério de entrada na cobertura é **rank por
   `last_served`**, com salience apenas desempatando entre nunca-servidos.
7. **A barra é um estoque, não um parâmetro.** Estoque de nunca-servidos elegíveis:
   38 em 20/08 de manhã, **0** ao fim do mesmo dia (52 primeiros-serves). Todo
   `w` mínimo publicado é condicionado ao estoque na data da medição.
8. **A dose amplifica a escada; não levanta piso.** Como `W_OUTCOME ∝ severity`,
   nenhum `w` reordena severidades — donde a nulidade da §1.

E uma nona, que é o motivo de 3 números terem sido publicados errados:

9. **O cut do slot principal é agente-heterogêneo** (0,610-0,792, span 0,18). Não
   é constante do sistema. A análise tem de ser por agente ou estratificada; o
   `0,8524` registrado no §2:438 é uma medição de um agente só, generalizada.

---

## 4. O que continua bloqueado em λ

Não escrevível sem a rodada do painel: qualquer **porcentagem**, qualquer **`w`
necessário**, o **teto pooled**, "o primário sobrevive", e a banda lida como
platôs. A nulidade da §1 e as correções 1-9 **não** dependem de λ.

---

## 5. Notas de método a carregar na emenda

- **B5** (escolha de δ) — inalterado, carregar por referência.
- **Proveniência do seeding sintético:** `cuts_measure.mjs:28-29` planta
  `max(1, ceil(396·share))`, o que força ≥1 S4/dia onde Poisson daria ~0,32. As
  fotos derivadas dali são **piso**, não estimativa.
- **Enquadramento:** "conclusão **re-estabelecida**, não confirmada". O termo
  **"by construction" fica proibido** no texto da emenda — foi exatamente a
  frase que carregou os dois defeitos de 16/08 e 17/08.
- **Contingência de versão de código:** todo número desta emenda é datado e
  amarrado ao commit servindo em 21/08.
- **Portão do sorteio:** `T_seed_assign` só depois de congelar o mecanismo
  emendado. Esta emenda é pré-requisito do sorteio, não posterior a ele.
- **Redefinição de unidade de `Δ_cut`:** `Δ_cut = 0,043` foi medido como spread
  no cut do brief; sem cut, a unidade precisa de nova definição operacional ou de
  ser substituída por uma quantidade que exista.
- **Unidade das shares:** por-veredito (S1 69,73 / S2 29,62 / S3 0,58 / S4 0,08)
  vs consolidada por-episódio (S1 78,93 / S2 21,07 / S3 0 / S4 0). O registrado
  usa a primeira; a análise usa episódios. Declarar qual vale onde.

---

## 6. Plano de depósito

Uma emenda, na ordem: (i) fechar a proposta da §2 com revisão adversarial;
(ii) implementar e medir o mecanismo emendado; (iii) rodar o painel para λ;
(iv) depositar **uma** versão no Zenodo + emenda no OSF; (v) congelar; (vi)
sortear; (vii) epoch 1.

⚠️ Arquivos no Zenodo são imutáveis — conserto é versão nova. Reler campo a campo
contra a v1.11 publicada, em formato RDM, antes do passo irreversível.
