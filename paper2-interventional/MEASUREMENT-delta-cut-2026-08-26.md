# `Δ_cut` — medição sob referente novo (item 3 do §5.3)

> 🔴 **SUPERSEDED EM PARTE — 2026-08-27.** Este documento mede com instrumentos que a
> `REMEDIATION-2026-08-27.md` corrigiu, e afirma como fato vivo várias coisas que a
> emenda **retrata**: a auto-extinção como "REFUTADA" (retratação 36), "3 sondas / 15
> linhas" (37), a descontaminação por corte temporal (38), `11/310` de janela aberta
> (39), `132/2.212 = 5,9675%` (40), o rótulo do `8,05%` (41) e a linha de base diluída
> `4,1693%` (34). Fica no pacote **como registro do que foi medido e como**, não como
> fonte de número. Para os números vigentes, ler `REMEDIATION-2026-08-27.md` e a tabela
> de retratações da emenda.

> **Medição, não decisão.** A `AMENDMENT-v1.12.md` §1.5 declara `Δ_cut = 0,043`
> como *pendente de definição operacional e de medição*, e o item 3 do §5.3 pede
> "definir e medir sob referente novo, **ou substituí-lo por quantidade que
> exista**". Este documento mede. A decisão vem depois, com o número na mesa — a
> mesma ordem que funcionou com a dose da opção B.
>
> Tudo aqui foi medido em **2026-08-26, entre 20:35Z e 21:00Z**, sobre o corpus do
> snapshot de epoch `e20260826T060003Z.db` e o estado de serving do DB vivo.

---

## O achado, antes dos números

**`Δ_cut` não pode receber referente porque a quantidade que ele escala é
lexicograficamente dominada.** O comparador do pool de cobertura é
`coverageCompare` (`src/api/brief-diversity.ts:130-140`):

```ts
const al = aLastServedMs ?? Number.NEGATIVE_INFINITY;
const bl = bLastServedMs ?? Number.NEGATIVE_INFINITY;
if (al !== bl) return al - bl;   // last_served ASC — domina
return bSalience - aSalience;    // salience só desempata last_served IDÊNTICO
```

O boost do Paper 2 é aditivo **em `salience`**. Logo ele só pode mudar a ordem
entre dois candidatos cujo `last_served` seja **exatamente igual**. Quando difere,
o comparador devolve `al − bl` e **nunca consulta `salience`** — nenhum valor de
`w · Δ_cut · severidade` atravessa a diferença, por pequena que ela seja.

Não é hipótese. É o estado medido do pool agora:

| posição | `last_served` | `salience` | do estudo? |
|---|---|---|---|
| 0 | `2026-08-26 18:37:05` | 0,682220 | não |
| 1 | `2026-08-26 18:37:05` | 0,682220 | não |
| 2 | `2026-08-26 18:37:05` | 0,682220 | não |
| **3** | **`2026-08-26 18:37:06`** | 0,712751 | **sim** (308220) |

`freshSlots = 2` em produção, logo só as posições 0 e 1 são servidas. O primeiro
chunk do estudo está na posição 3 porque foi servido **um segundo depois**. Um
segundo é uma barreira absoluta: o comparador devolve 1.000 ms e encerra.

Note que o chunk do estudo tem `salience` **mais alta** (0,7128 contra 0,6822) e
perde de todo modo. A ordenação não é por salience — salience é a coordenada
subordinada.

---

## Números

### O pool real

| | |
|---|---|
| candidatos no pool (`LIMIT 400`, mas o `WHERE` corta) | **108** |
| chunks do estudo no pool | **55 de 55** — todos |
| candidatos **nunca-servidos** (`last_served NULL`) | **0** |
| grupos de `last_served` distintos | **44** |
| tamanhos de grupo | 1: 3 · 2: 29 · 3: 1 · **4: 11** |
| candidatos em grupo de tamanho 1 (salience irrelevante) | 3 |
| candidatos em grupo ≥ 2 (salience decide) | 105 |

⚠️ **Zero nunca-servidos** contradiz uma premissa escrita no próprio módulo.
`src/paper2/brief-outcome.ts:17-22` justifica o boost entrar no estágio (b) e não
no pré-rank SQL assim: *"um chunk do estudo é nunca-servido, logo está sempre entre
os 400"*. Os 55 já foram servidos — os três que amostrei tinham **47-48 servings
cada**. A premissa está vencida; a conclusão (estar no pool) segue verdadeira por
outra razão, que é o pool ter 108 candidatos e não 400.

### O que o boost teria de vencer, quando pode agir

Gaps de `salience` entre pares adjacentes **dentro de grupos de empate** que
envolvem pelo menos um chunk do estudo:

| | |
|---|---|
| pares adjacentes envolvendo estudo | 38 |
| gaps **exatamente zero** | **11 (28,9%)** — qualquer boost positivo vence |
| gaps > 0 | 27 |
| mín · p25 · mediana · p75 · **máx** | 0,000930 · 0,004931 · 0,019469 · 0,026530 · **0,031809** |

### A banda registrada contra esses gaps

`W_OUTCOME = w · Δ_cut · severidade`, com `Δ_cut = 0,043`:

| `w` | S1 (sev 0,25) | vence | S2 (sev 0,5) | vence |
|---|---|---|---|---|
| **2,0** | 0,0215 | 16/27 | 0,0430 | **27/27** |
| 4,0 | 0,0430 | **27/27** | 0,0860 | 27/27 |
| 7,5 | 0,0806 | 27/27 | 0,1613 | 27/27 |

**O braço mais baixo da banda já satura para S2.** O maior gap do pool é 0,0318 e
o boost de S2 a `w = 2,0` é 0,0430. A única faixa com discriminação de dose é
**S1 entre `w = 2,0` e `w = 4,0`** — 16/27 contra 27/27. Acima disso, a banda
inteira é indistinguível de si mesma.

### Barredura de dose, dual-compute offline

Corpus = snapshot de epoch, serve-state = vivo, 7 agentes (`nox`, `lex`, `atlas`,
`boris`, `cipher`, `forge`, e sem agente), `n = 10`, `freshSlots = 2`. Provedor
instrumentado para contar chamadas e boosts emitidos:

| `w` | boosts emitidos por brief | `churn` |
|---|---|---|
| 2,0 | 19 (38 sem agente) | **0** em 7/7 |
| 4,0 | 19 | **0** em 7/7 |
| 7,5 | 19 | **0** em 7/7 |
| **1.000** | 19 | **0** em 7/7 |
| **100.000** | 19 | **0** em 7/7 |

Os boosts **são** emitidos — 19 por chamada, os 19 designados. E `churn` é zero
até em `w = 100.000`. É a demonstração direta da dominância lexicográfica.

### Grupos mistos, e onde eles estão

Para o boost mudar o **brief** (não só a ordem), o grupo de empate precisa conter
estudo **e** não-estudo, e estar na fronteira de seleção:

| primeira posição do grupo | `last_served` | tamanho |
|---|---|---|
| **3** | `18:37:06` | 2 |
| 9 | `18:52:03` | 2 |
| 15 | `18:52:08` | 4 |
| 23 | `19:07:04` | 4 |
| 51 | `19:37:04` | 4 |
| 55 | `19:37:05` | 2 |

11 grupos mistos no total; o melhor colocado começa na **posição 3**, e a
fronteira é 0–1. Neste instante, **nenhum** grupo misto alcança a fronteira.

---

## O que isto NÃO prova

⚠️ **Um instante não é uma taxa.** A varredura mediu **um** estado do pool. A
linha de base histórica — janela fechada por `sha256` do NDJSON,
`2026-08-21T22:57:48.194Z` → `2026-08-26T19:52:07.775Z`, 3.166 linhas — tem
`churn` positivo em **132 = 4,1693%**. Zero num instante é perfeitamente
compatível com uma taxa de 4%: é um sorteio de um evento de 4%.

Concluir "o mecanismo é inerte" da varredura seria repetir o erro do `N = 3` de
20:28Z. O que a varredura prova é **estrutural**: *quando não há colisão na
fronteira, dose nenhuma age*. A frequência com que há colisão é uma propriedade da
série temporal, e é ela que os 4,1693% medem.

⚠️ **O controle positivo que vale não é o meu harness.** Montei dois harnesses
offline e ambos deram zero em `w = 100.000`. O primeiro estava genuinamente errado
— usei o DB vivo como corpus **e** como serve-state, quando produção serve o corpus
do snapshot de epoch (`NOX_EPOCH_SNAPSHOT=active`, drop-in P2S1) e o `brief_log` do
vivo, o que ativa um caminho de código diferente. Corrigi. O segundo, no caminho
certo, também deu zero — e aí não era defeito, era o achado.

O controle positivo que **passa** é o teste unitário
`"controle positivo: a w=0 o incumbente ocupa o slot; a w=7.5 o chunk do estudo o
toma"`. Ele constrói dois chunks **nunca-servidos** — logo `last_served` empatado em
`NULL` — e o boost desloca. O mecanismo funciona exatamente onde há empate. Em
produção, empate na fronteira é raro.

---

## Consequências para o registro, e as opções

**A intervenção, como registrada, quase não tem dose.** O que governa a ativação é
**colisão exata de `last_served` na fronteira de seleção**, não a magnitude do
boost. E `served_at` é gravado com resolução de **segundo** (`2026-08-26 18:37:05`),
então "colisão" significa dois chunks servidos no mesmo segundo — o próprio código
comenta esse caso ao justificar o `brief_id` (*"dois briefs no mesmo segundo"*).

Três saídas, e nenhuma é escolha minha:

**(a) Substituir `Δ_cut` por quantidade que existe, e reconhecer que a banda
colapsa.** O referente honesto é o **gap de salience dentro de grupo de empate**,
cuja distribuição está medida acima (máx 0,0318). Sob esse referente, a banda
{2,0 · 4,0 · 7,5} tem no máximo **dois** níveis distinguíveis, e só para S1.
Registrar isso é honesto e barato, mas o desenho perde a resposta-dose.

**(b) Mover o boost para a coordenada dominante.** Em vez de somar em `salience`,
o tratamento deslocaria `last_served` (ex.: tratar como se tivesse sido servido
`k` segundos antes). Aí a dose passa a existir de verdade e é mensurável em
segundos. **Mas isso é intervenção nova, não calibração** — muda o mecanismo que a
emenda declara, e exige registro prospectivo próprio.

**(c) Aceitar a taxa de colisão como o estimando.** Assumir que o tratamento é
"por construção" gated por colisão e que os 4,1693% são a taxa de oportunidade.
O `N` necessário cresce por um fator de ~24, e a dose deixa de ser o fator
manipulado.

**Recomendação:** (a) agora, para desbloquear o registro com honestidade, e (b)
avaliada em separado **com medição antes da decisão** — porque (b) é desenho novo e
merece a mesma disciplina que a opção B teve. (c) é a que eu evitaria: transformar
uma limitação estrutural em estimando é o movimento que a retratação 2 da emenda
condena (*trocar o rótulo e manter a aritmética*).

⚠️ **Isto precede o `T_seed_assign`.** Sortear braço de uma banda que não
discrimina é gastar o sorteio. A ordem tem de ser: resolver `Δ_cut` → registro
prospectivo → `ASSIGNMENT.json` → `active` → Epoch 1.

---

*Proveniência: `src/api/brief-diversity.ts:130-140` (comparador) ·
`src/api/brief.ts:719-748` (SQL do pool, `FRESH_CANDIDATE_POOL = 400`,
`DEFAULT_N = 10`) · `src/api/brief-diversity.ts:53-63` (`freshSlots: 2`) ·
`src/paper2/brief-outcome.ts:17-22` (a premissa vencida) ·
`scripts/mede-delta.mjs`, `scripts/dose2.mjs`, `scripts/controle-positivo.mjs` na
VPS · `DESIGNATION-2026-08-26.json` (os 19 designados) ·
`DECISION-designacao-2026-08-25.md` (linha de base de 4,1693%).*
