# Resolução: as duas questões abertas se dissolvem, e uma terceira aparece

**Data:** 2026-08-21 · **Fecha:** `AMENDMENT-v1.12-DRAFT.md` §2-quater, itens
"qual estimando" e "qual regra escolhe a barra".

## 1. Eu tinha confundido mecanismo com estimando

Formulei a questão como *"limiar ou hazard de fila?"*. Errado: **o estimando
primário nunca estava em jogo.** §4.1 define o desfecho como **falha repetida** —
uma ação executada cuja falha reincide — analisado ITT, pooled 117 vs 117 (§3:344-351).
Isso não menciona serving, barra, nem slot.

O que dependia da barra era outra coisa: as figuras de **alcance**, o argumento de
**potência/MDE**, e a regra de leitura dose-resposta. São quantidades de
**mecanismo**, não o estimando.

Corrigida a pergunta, ela fica: *como o tratamento é aplicado, e como o alcance é
reportado, dado que ele é dependente de estado?*

## 2. A resposta já está no código: dual-compute

`buildBriefDiverse` (`src/api/brief.ts:726-783`) **já devolve
`{ current, alt, diff }`** — computa dois rankings e os diffa. Linha 739:
*"Brief atual (baseline, score = salience) — o que está em prod hoje."*

O tratamento entra assim:

| papel | conteúdo |
|---|---|
| `current` | ranking de **controle** — salience sem boost |
| `alt` | ranking de **tratamento** — salience com `W_OUTCOME` |
| `diff` | o **deslocamento**, por brief |

Serve-se o ranking do braço designado; logam-se **os dois**.

### Isso resolve as duas questões de uma vez

**Não é preciso barra nenhuma.** O comparador não é uma constante escolhida entre
seis medições — é o **ranking de controle do mesmo brief**. A pergunta "o chunk
designado teria entrado sem o boost?" passa a ter resposta por brief, medida.

**Alcance deixa de ser projeção.** Vira quantidade medida por epoch: a fração de
briefs em que `alt ≠ current`. Não precisa de `CUT_FRESH`, de `Δ_cut` como unidade,
nem de extrapolar 24 h.

**Fica bem-definido com buffer vazio.** Se não há competidor, os dois rankings são
idênticos, `diff` é vazio, e isso é registrado como **zero medido** — não como
censura nem exclusão.

## 3. Qual estágio recebe o boost: **(b)**, e por quê

| estágio | chave | tem recência? | papel |
|---|---|---|---|
| (a) pré-rank SQL, `LIMIT 400` | `0.55·imp + 0.10·pain + 0.1·[access>0]` | não | **pertinência ao pool** |
| (b) `ranked.sort` (JS) | `calculateSalience` completa | sim | **ordem dentro do pool** |

**Decisão: (b)**, com a justificativa registrada — e ela não é estética. (a) ordena
`last_served ASC` primeiro, e um chunk do estudo é **nunca-servido**, logo está
sempre entre os 400. **(a) não é vinculante para a população do estudo**, então
aplicar o boost lá não mudaria pertinência e sim ordem, duplicando (b).

⚠️ Registrar também o que isso implica: a aritmética de severidade só existe em
(b). Se algum dia o boost migrar para (a), o degrau de severidade e o span de
recência deixam de existir — a grandeza não estaria lá.

## 4. Epochs sem ativação: ITT preservado, ativação reportada

Três opções e por que duas caem:

| opção | veredito |
|---|---|
| excluir epochs não-ativados | ❌ quebra a randomização |
| redefinir epoch como "ativado" | ❌ muda o quadro amostral, reabre `N` |
| **ITT com todos, ativação reportada** | ✅ |

**Decisão: ITT com todos os epochs.** Um epoch de tratamento sem deslocamento
contribui com ativação zero, o que **enviesa para o nulo** — e por isso a fração
de ativação passa a ser quantidade **pré-comprometida de reporte** (análoga a
aderência), com sensibilidade per-protocol pré-registrada. Mesmo tratamento que o
plano já dá para "falha de resolução de braço ⇒ boost zero".

## 5. A terceira questão, que aparece ao resolver as duas

Se o alcance é medido em vez de projetado, ele pode ser medido **antes** de gastar
234 epochs — e sem sortear braço nenhum:

```
painel (λ) → write path recebe linhas → dual-compute em SHADOW mede a
fração de ativação com chunks REAIS, sem tratamento servido → só então
decidir banda/N/prosseguir → congelar → sortear → epoch 1
```

O período de medição pré-tratamento não consome epoch de estudo, não exige
`T_seed_assign`, e responde a pergunta que nenhuma das minhas aritméticas de hoje
respondeu: **o mecanismo desloca algo, e com que frequência?**

⚠️ E ele **depende do painel**: sem falhas adjudicadas não há chunk do estudo, e
sem chunk do estudo o dual-compute não tem o que deslocar. Medir com chunk
sintético é exatamente o "seeding sintético" que as três vozes marcaram como
projeção.

**Consequência de sequenciamento:** a rodada do painel deixa de ser o último passo
antes do sorteio e passa a ser o **primeiro** passo da medição que decide o
desenho.

---

## 6. Decisão do Toto — 2026-08-21

| questão | decisão |
|---|---|
| rodada do painel agora | **não** |
| medição de ativação pré-tratamento antes do sorteio | **sim** |

**Dependência que isso cria, declarada:** a medição de ativação exige chunks reais
do estudo → exige falhas adjudicadas → exige o painel. Com o painel parado, a
**fração de ativação não é mensurável**. O passo aprovado fica armado e esperando.

**O que avança sem o painel:**

1. **Componente 2 — wiring do dual-compute.** `current` = controle (sem boost),
   `alt` = tratamento (boost em estágio (b)), `diff` = deslocamento. Flag-gated,
   boost zero quando controle, um único call site. Verificável **sem** chunk do
   estudo: o teste golden prova invariância do caminho de controle.
2. **Instrumentação do log de ativação** — para que a coleta comece no instante em
   que o primeiro veredito chegar, em vez de depois.
3. **Seções da emenda já fechadas** — esclarecimento do estimando, ausência de
   barra, estágio (b), ITT + reporte de ativação. Nenhuma depende de λ.

**Meio-caminho disponível, não solicitado:** uma rodada de painel **reduzida** (~30
episódios em vez de ~325, ~1/10 da quota) não dá λ com precisão, mas produz
chunks reais suficientes para uma estimativa grosseira de ativação — que é uma
pergunta binária ("desloca ou não") antes de ser uma pergunta de magnitude. Fica
registrado como opção, não adotado.
