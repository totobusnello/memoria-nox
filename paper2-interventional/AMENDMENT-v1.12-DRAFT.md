# Emenda v1.12 — RASCUNHO

**Emenda:** OSF `yf7d2` (registrado 2026-08-18T07:56:44Z) · Zenodo
`10.5281/zenodo.21978476` (concept `10.5281/zenodo.21964093`)
**Status:** rascunho, não depositado. **Uma** emenda, conforme decidido.
**Escrito antes do sorteio de `T_seed_assign`** — que é precisamente por que a
ordem "congela o mecanismo, depois sorteia" foi adotada em 17/08.

---

## 🔴 1. O achado que ordena todo o resto: a intervenção registrada é nula por construção

O §2, linha 449, **trava** o mecanismo:

> *"Locked instead: the boost is applied only in the coverage-slot ranking, never
> in the main-pool re-rank."*

A restrição foi adotada em boa-fé, para impedir que o braço de topo enchesse os 8
slots principais de lições de falha. Medido o caminho de cobertura, ela fecha o
único canal do tratamento. Três premissas, todas verificadas:

**(A) O caminho de cobertura não ordena por salience.**
`fetchFreshCandidates` (`src/api/brief.ts:698-701`) ordena
`ORDER BY last_served ASC, <proxy> DESC LIMIT 400`, e o `ranked.sort` seguinte
repete a hierarquia. Um chunk **nunca-servido** passa à frente de todo já-servido,
qualquer que seja a salience dos dois. Salience só desempata **entre**
nunca-servidos. (Ver `BAR-RETRACTION-2026-08-20.md`.)

**(B) Todo chunk de falha adjudicada é nunca-servido no instante em que age.**
Por construção do write path: é escrito na adjudicação e servido depois. Logo
entra nos 2 slots de cobertura **a `w = 0`**, sem precisar de dose.

**(C) A dose não pode reordenar as severidades.**
`W_OUTCOME = w · Δ_cut · severity` **escala com** a severidade, então é
monotônica nela. Verificado em toda a banda:

| `w` | S1 | S2 | S3 | S4 | ordem |
|---|---|---|---|---|---|
| 0 | 0,6700 | 0,6950 | 0,7200 | 0,7450 | S1<S2<S3<S4 |
| 2,0 | 0,6915 | 0,7380 | 0,7845 | 0,8310 | S1<S2<S3<S4 |
| 4,0 | 0,7130 | 0,7810 | 0,8490 | 0,9170 | S1<S2<S3<S4 |
| 7,5 | 0,7506 | 0,8563 | 0,9619 | 1,0675 | S1<S2<S3<S4 |

E a idade não inverte: o degrau de severidade a `w = 0` é **0,0250**, contra um
span de recência de **0,0164** em toda a janela de 30 dias. Um S2 recém-escrito
perde para um S3 de 30 dias, em `w = 0` e em `w = 7,5`.

**Conclusão.** Se há ≤ 2 chunks do estudo disputando, todos entram a `w = 0`. Se
há > 2, entram os 2 de maior severidade — e `w` preserva essa ordem. Em qualquer
cenário, **o conjunto servido é idêntico em todos os braços.**

⚠️ **A nulidade não depende de λ.** Vale para qualquer taxa de chegada. Portanto
este achado **não espera a rodada do painel** — e muda o que a rodada do painel é
para.

### Dois trechos do próprio registro que CORROBORAM a nulidade

O censo mecânico procurou furo e achou reforço.

**§3:705 — o controle positivo de julho já mediu este mecanismo.**

> *"a synthetic chunk inserted into the live store after a boundary at `pain = 1.0`,
> `importance = 1.0` — the ceiling of both dimensions — entered **1 of 10** briefs
> and was then crowded out, **because being served made it no longer
> never-served**."*

Um chunk no **teto das duas dimensões** entrou uma vez e saiu. Sob um modelo de
limiar isso é inexplicável (teto de salience deveria entrar sempre); sob o
mecanismo medido é exatamente o previsto: entrou por ser nunca-servido, e perdeu
a elegibilidade ao ser servido. A medição de 2026-07-26 já continha a resposta —
faltava a leitura.

**§3:705 — o segundo canal existe, e é insensível à dose.** A mesma linha declara
que conteúdo novo alcança o brief *"through the coverage slots, or by displacing a
primary slot on salience alone"*. O segundo caminho está aberto — mas como o 449
proíbe aplicar o boost no re-rank principal, a salience que compete lá é a
**`base`, sem `w`**. Canal aberto, dose-independente. A nulidade sobrevive.

**§2:466 — a designação fecha o resto.** *"0% — one slot, by construction"*: com
uma única correspondência designada por grupo de assinatura, no máximo **1** slot
carrega chunk impulsionado. E a designação é `argmin (0.7342 − base)/(Δ_cut·sev)`,
que **não depende de `w`** — o próprio documento registra isso. Logo a dose não
escolhe nem *qual* chunk é designado, nem *se* ele entra.

### Por que os números registrados não expuseram isso

A tabela do §2:440 mede `w` contra `CUT_FRESH = 0.7342`, tratando a entrada na
cobertura como **cruzar um limiar**. `reachable_share.py` faz o mesmo
(`w_min = (0.7342 − base)/(Δ_cut·sev)`). Não existe esse limiar: `pick` fase 3
toma os primeiros `freshSlots` **sem comparação**. Todos os números de alcance
publicados são propriedades de um modelo que a produção não executa.

---

## 2. Mecanismo emendado — proposta

O canal tem de ser reaberto, e a restrição do 449 revista. O que a medição
sustenta:

**Aplicar `W_OUTCOME` no re-rank do pool principal**, exatamente o que o 449
proíbe — porque é o único ponto do caminho de serviço em que salience decide algo
e a dose pode mover.

Medido ao vivo em 21/08, o cut do slot principal **por agente**:

| agente | lex | nox | boris | forge | atlas | cipher |
|---|---|---|---|---|---|---|
| cut principal | 0,6100 | 0,6851 | 0,6925 | 0,7051 | 0,7613 | 0,7922 |

Cruzamentos de agente×severidade alcançados, com as severidades que de fato
ocorrem (S1 78,93% / S2 21,07% / **S3 e S4 zero em 707 episódios**):

| braço | via S1 | via S2 | total | Δ vs controle |
|---|---|---|---|---|
| controle (`w=0`) | 1/6 | 3/6 | 4 | — |
| `w = 2,0` | 2/6 | 4/6 | 6 | **+2** |
| `w = 4,0` | 4/6 | 5/6 | 9 | **+5** |
| `w = 7,5` | 4/6 | 6/6 | 10 | **+6** |

**Os três braços passam a ser distinguíveis, com dose-resposta monótona e
saturante** (+2, +5, +6 — o topo compra um agente a mais que o meio).

### E a saturação que o 449 queria evitar

A preocupação era colocar lições de falha nos slots principais. Medido hoje: os
picks de cobertura estão a **0,7344**, **acima do cut principal em 5 dos 6
agentes**. Lições de falha já ocupam posições acima do cut principal pelo caminho
de cobertura, sem tratamento nenhum. A fronteira que o 449 protege **já está
cruzada pelo status quo**; o que resta a controlar é a *contagem*, não o *tipo*.

**Proposta:** bound numérico em vez de proibição — **no máximo 3 dos 10 itens do
brief podem ser chunks de falha adjudicada**, cap avaliado na composição,
idêntico nos dois braços, registrado antes do sorteio. Isso preserva o canal e
limita a saturação por um número verificável, em vez de fechá-la por decreto.

---

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
