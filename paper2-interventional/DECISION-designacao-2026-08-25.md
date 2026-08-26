# Decisão — a regra de designação substituta

> ## ✅ DECIDIDO 2026-08-26T14:47Z — **opção B**, sorteio pseudoaleatório com seed declarada
>
> Decisão do Toto, tomada **depois** de a medição do custo estar na mesa (8,8% de
> dose agregada) e **antes** de qualquer linha de código da regra nova. A ordem
> importa: decisão de desenho registrada após a implementação é indistinguível de
> racionalização da implementação.
>
> | | |
> |---|---|
> | Regra | `designado(g) = argmin_{c ∈ g} SHA256( seed ‖ "\|" ‖ chunk_id )` |
> | Custo aceito | **8,8%** de dose agregada (5 dos 19 grupos mudam) |
> | O que se compra | independência da calibração de severidade de **uma** família do painel (`xai` = 72,2% do share de S2) |
> | Satisfaz | R1 total · R2 só colunas imutáveis de `p2_verdict` · R3 sem `CUT_FRESH`/`Δ_cut` · R4 reproduzível de fora · R5 declarada antes do `ASSIGNMENT.json` |
>
> ⚠️ **Esta seed NÃO é o `T_seed_assign`.** São dois sorteios distintos com
> propósitos distintos: esta designa **qual chunk** recebe o boost dentro do
> grupo; o `T_seed_assign` sorteia **qual braço** cada epoch recebe. Precisam de
> nomes distintos no registro e de declarações separadas. Confundi-los seria
> permitir que quem conhece uma inferisse a outra.
>
> ⚠️ **A seed precisa de precedência verificável**, na mesma disciplina do λ: a
> declaração é pushada **antes** de a rodada de aleatoriedade existir
> (`LAMBDA-SEED-2026-08-21.md` foi pushado 22:17:50Z, rodada `31515871` emitida
> 22:22:57Z). Sem isso a seed é escolhível a posteriori e a regra volta a ser
> discricionária — o defeito que esta decisão existe para consertar.
>
> **Estado:** decisão fechada; implementação e declaração de seed pendentes
> (§5.3 da `AMENDMENT-v1.12.md`, itens 1, 2 e 4).
>
> **Por que é decisão e não implementação:** a regra decide **quem recebe
> tratamento** em 7 dos 19 grupos de assinatura (os multi-membro; nos outros 12 há
> um único chunk e não há escolha). Qualquer escolha feita depois de
> olhar o resultado é grau de liberdade do pesquisador. A escolha vem antes do
> `ASSIGNMENT.json`, e o `ASSIGNMENT.json` vem antes do Epoch 1.

---

## O que está quebrado, em três fatos medidos

**1. A regra consome uma constante cujo referente a emenda retrata.**
`w_min = (CUT_FRESH − base) / (Δ_cut · severidade)` com `CUT_FRESH = 0,7342`
(`brief-outcome.ts:235-238`). A retratação 13 estabelece que `0,7342` é o cut do
**slot de cobertura**, não do pool principal — e a retratação 3 estabelece que
**não há limiar** que o `pick` aplique. A designação depende de um número que
descreve algo que o mecanismo não faz.

**2. O desempate registrado nomeia uma coluna que não existe.**
`PREREG-DRAFT.md:535` registra *"lowest `w_min`, then earliest `created_at`, then
lexicographic `chunk_id`"*. O schema de `p2_verdict` é `episode_id, severity,
sig_primary, sig_coarse, chunk_id, source_file, panel_hash, adjudicated_at,
written_at` — **sem `created_at`**. Não é "não implementado": é não-implementável
como escrito. E o código não implementa nível nenhum de desempate — a query não
tem `ORDER BY` e a comparação é `wMin < atual.wMin`, estritamente menor. Em
empate vence a ordem de linhas que o SQLite devolver.

**3. A regra não está congelada — ela deriva de um campo mutável.**
`base` é `calculateSalience` (`src/salience.ts:246`), que inclui
`0,20 · clamp01(log1p(access_count)/log(1000))`. Nos 55 chunks, `access_count`
varia de 1 a 5 e `base` assume **9 valores distintos**.

> ✅ **Verificado, e é a boa notícia:** `access_count` é incrementado **somente**
> por `recordAccess` em `src/search.ts:396`, chamado só pelos caminhos de
> `search`. **O serving de brief não incrementa.** Logo **não existe** o laço
> designação → serving → designação que eu suspeitei. O que existe é uma
> dependência em **tráfego de busca exógeno**: qualquer `/api/search` sem
> `?track=false` move `base` e pode mover o designado. A regra não é
> pós-randomização; é apenas **não congelada**.

---

## Requisitos que a substituta tem de satisfazer

| # | requisito | por quê |
|---|---|---|
| R1 | **Total** — nenhum empate possível | senão a ordem do SQLite decide |
| R2 | Ler **apenas** colunas imutáveis de `p2_verdict` | congelamento verificável; nada de `access_count`, `salience`, `last_served` |
| R3 | Independente de `CUT_FRESH` e de `Δ_cut` | referentes retratados |
| R4 | Reproduzível de fora, a partir dos artefatos publicados | um terceiro tem de poder recomputar a designação |
| R5 | Declarada **antes** de gerar o `ASSIGNMENT.json` | ordem de operações do §8 |

---

## As opções

### A — Severidade máxima, desempate por `chunk_id` lexicográfico

```
designado(g) = argmin_{c ∈ g} ( −severidade(c), chunk_id(c) )
```

- ✅ Satisfaz R1–R5. Uma linha de SQL: `ORDER BY severity DESC, chunk_id ASC`.
- ✅ **Maximiza a dose.** `W_OUTCOME = w · Δ_cut · severidade`, então designar o
  membro mais grave é a designação de maior potência para o mesmo `w`.
- ✅ Aproxima o comportamento observado: nos 7 grupos multi-membro o mínimo de
  `w_min` já caía sobre os membros de severidade máxima.
- 🔴 **Amarra a designação a um único painelista.** Medido em
  `LAMBDA-RESULTS-2026-08-21.md`: o share de S2 nas falhas é 24,2% (moonshot),
  25,9% (zhipu) e **72,2% (xai)**. Os três concordam que houve falha e discordam
  sobre a gravidade. Uma regra que designa por severidade máxima faz a atribuição
  de tratamento herdar a calibração de severidade do xai.

### B — Sorteio pseudoaleatório com seed declarada

```
designado(g) = argmin_{c ∈ g} SHA256( seed ‖ "|" ‖ chunk_id )
```

> ⚠️ **O layout desta linha mudou em 2026-08-26T19:40Z, depois de a opção B já
> estar decidida.** Não é repactuação da decisão — a escolha entre A e B segue de
> pé, com o mesmo custo de 8,8%. É correção do material da chave, e está aqui em
> vez de silenciosa porque a linha anterior foi aprovada como está.
>
> **O que estava escrito:** `SHA256( seed ‖ "|" ‖ sig_primary ‖ "|" ‖ chunk_id )`.
>
> **O defeito:** **todos** os 19 valores de `sig_primary` contêm `|` — o próprio
> separador (`Bash|shell:outro`, `Read|arquivo:doc`). O layout portanto **não é
> injetivo**, e a colisão é concreta, não hipotética: `seed ‖ "Bash|shell:outro" ‖
> 308226` e `seed ‖ "Bash" ‖ "shell:outro|308226"` são a **mesma sequência de
> bytes**. Não é explorável — `sig_primary` vem de `p2_verdict`, cujo conjunto de
> valores é fechado e publicado, não de entrada livre — mas registrar isso como
> "colisão conhecida e aceita" é posição pior do que não ter a colisão, e o custo
> de consertar antes de a seed existir é zero.
>
> **Por que a correção é remover o campo e não trocar o separador:** verificado
> sobre `p2_verdict` que **cada chunk pertence a exatamente um `sig_primary`** (0
> de 55 em mais de um grupo). Pertencimento a grupo já é *função* de `chunk_id`,
> logo `sig_primary` na chave não carrega informação — só ambiguidade. A
> propriedade estatística é idêntica: dentro de cada grupo o argmin segue uniforme,
> e os grupos são disjuntos, logo os sorteios seguem independentes.
>
> **Ganho que não é cosmético:** a chave passa a depender **só de ids congelados**.
> Sob o layout anterior, renomear um `sig_primary` mudaria todo designado daquele
> grupo; sob este, não muda nada. É a mesma classe de mutabilidade que invalidou a
> regra da v1.12 via `access_count`, e vale fechá-la nos dois lugares.
>
> **O que explicitamente NÃO foi argumento:** medi os dois layouts sob a seed de
> teste `ab`×32 (3 dos 19 designados diferem; soma de severidade 6,5000 contra
> 6,7500). Esses números **não** entraram na decisão e não devem entrar em nenhuma
> outra: a seed real não existe ainda, e escolher layout pelo resultado sob uma
> seed disponível é pescaria de seed — o mesmo vício que fez esta decisão preferir
> rodada drand nova a sub-seed rotulada. A escolha é pelo argumento de layout.

- ✅ Satisfaz R1–R5. **Mesma maquinaria já usada e auditada** na amostra de λ
  (`LAMBDA-SEED-2026-08-21.md:66-75`): seed derivada de fonte pública, hex
  minúsculo, separador `|` obrigatório, declarada e pushada antes da rodada.
- ✅ **Remove o confundimento de calibração.** A designação passa a ser
  independente de severidade, logo independente de qual painelista pontuou mais
  duro.
- 🔴 **Perde dose — 8,8% no agregado. MEDIDO 2026-08-26.**

  A dose esperada cai do **máximo** de severidade do grupo para a **média**.
  Sobre `p2_verdict` (19 grupos, 55 chunks; `severity` e `sig_primary` são
  campos congelados desde 2026-08-21T22:51:23, então a medição não envelhece):

  | | soma de severidade sobre os 19 grupos |
  |---|---|
  | A (máximo) | **7,2500** |
  | B (sorteio, esperança) | **6,6134** |
  | **perda** | **8,8%** |

  Só **5 dos 19** grupos diferem — nos outros 14 a severidade é única, e A e B
  designam a mesma dose. Por grupo que difere:

  | grupo | n | composição | A | E[B] | perda |
  |---|---|---|---|---|---|
  | `mcp__openclaw__message\|sem-alvo` | 6 | S1:5 · S2:1 | 0,50 | 0,2917 | 41,7% |
  | `Bash\|shell:outro` | 17 | S1:10 · S2:7 | 0,50 | 0,3529 | 29,4% |
  | `Bash\|fs:mutacao` | 2 | S1:1 · S2:1 | 0,50 | 0,3750 | 25,0% |
  | `mcp__openclaw__web_fetch\|rede` | 8 | S1:3 · S2:5 | 0,50 | 0,4062 | 18,8% |
  | `Bash\|build/run` | 4 | S1:1 · S2:3 | 0,50 | 0,4375 | 12,5% |

  Em `W_OUTCOME = w · Δ_cut · severidade`, com `Δ_cut = 0,043`:

  | `w` | Σ A | Σ E[B] | perda |
  |---|---|---|---|
  | 2,0 | 0,6235 | 0,5687 | 0,0548 |
  | 4,0 | 1,2470 | 1,1375 | 0,1095 |
  | 7,5 | 2,3381 | 2,1328 | 0,2053 |

  🔴 **Retratação da minha própria prosa nesta seção.** A redação de 25/08 dizia
  *"a perda é da ordem de um terço da dose nesses grupos"* e falava de **4**
  grupos empatados. Errado nas duas pontas: os grupos que **diferem em dose** são
  **5** (conjunto diferente dos 4 que empatam em `w_min` — empate e diferença de
  dose não são a mesma condição), e "um terço" descreve a média dos 5 grupos
  isolados (25,5%), não o agregado, que é **8,8%** porque 14 grupos não mudam.
  Estimativa em prosa onde havia medição disponível — a classe de sempre.

  **Leitura da grandeza:** 8,8% é pequeno diante do espaçamento da própria banda
  — o menor passo é 2,0 → 4,0, um aumento de 100%. A perda não move grupo nenhum
  entre doses. ⚠️ E não converto isso em afirmação de poder: o estimando foi
  retirado (retratação 12), então não existe curva de poder vigente contra a qual
  medir. A afirmação é sobre **dose**, não sobre poder.
- 🔴 Exige uma seed nova, declarada antes e ancorada no OSF — mais um artefato
  com precedência a provar.

### C — Uma designação por célula (`sig_primary` × severidade)

- ✅ Elimina o empate por construção dentro da célula, e a severidade deixa de
  competir com a identidade.
- 🔴 **Muda a unidade do desenho.** Hoje a unidade é o grupo de assinatura; isso
  a torna a célula. `N`, o estimando e a razão de designação mudam todos. Não é
  conserto de defeito, é redesenho.

### D — `chunk_id` mais baixo

- ✅ Trivialmente total, uma linha.
- 🔴 `chunk_id` é ordem de inserção, que é ordem de adjudicação. Correlaciona com
  o momento da rodada de painel e possivelmente com o conteúdo. É arbitrariedade
  **não declarada**, que é o defeito atual com outra roupa.

---

## Recomendação

**B**, e a razão é uma só: o defeito que estou consertando é *designação decidida
por acidente*. A opção A troca o acidente da ordem do SQLite pelo **critério de
um painelista** — e a memória do projeto já registra que o estrato S2 repousa numa
única família (`xai` responde por 72,2% do share de S2). Trocar um viés opaco por
um viés nomeado é progresso, mas trocá-lo por **nenhum** é melhor, e o custo é
poder, que se compra com `w` ou com épocas.

**E o preço agora está medido: 8,8%** (tabelas acima). A troca é explícita:

> **8,8% de dose agregada** para remover a dependência da calibração de
> severidade de **um** painelista.

O `xai` responde por **72,2%** do share de S2 contra 24,2% e 25,9% dos outros, e
nos 5 grupos que diferem a opção A designa **S2 em todos os 5** — isto é, a
designação seria decidida, nesses grupos, pela família que pontua mais duro. B
troca isso por 8,8% de dose, e 8,8% cabe folgado dentro de um passo de banda.

Com o número na mesa, a recomendação fica mais firme, não menos.

Se a preferência for A, ela é defensável desde que a dependência da calibração do
xai seja **declarada no registro prospectivo** como limitação, não descoberta
depois.

---

## Fora de escopo desta decisão

- O `Δ_cut` e o `w` — dose, não designação.
- O `T_seed_assign` — é o passo seguinte, e o sorteio de **braço** não se
  confunde com o de **designado**. A opção B introduz uma segunda seed; as duas
  precisam de nomes distintos no registro.

---

*Proveniência: `AMENDMENT-v1.12.md` §5.2, §5.2-bis, §5.3 · `PREREG-DRAFT.md:535`
· `LAMBDA-RESULTS-2026-08-21.md` (shares por família) ·
`LAMBDA-SEED-2026-08-21.md:66-75` (maquinaria de seed) · `src/salience.ts:246` e
`src/search.ts:396` (lidos em 2026-08-25).*
