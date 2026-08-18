# §2 — auditoria claim-por-claim do caminho de serving

**Escopo.** Todas as afirmações falsificáveis de `PREREG-DRAFT.md` linhas 312–631
(§2 Design Plan) que descrevem **como a produção serve um brief**. O escopo
exclui de propósito a camada de desenho — randomização, `N = 234`, ICC, painel,
adjudicação, calendário, `assign_arms.py` — que não é tocada por nada aqui.

**Autoridade.** O código, não a reconstrução. Cada veredito abaixo aponta para um
de **seis** artefatos:

| artefato | o que é |
|---|---|
| `FIXTURE-SERVING-2026-08-18.json` | gerada dirigindo `dist/api/brief.js` + `dist/salience.js` na VPS; 56 casos |
| `serving_model.py` | porte Python, `--check` **56/56 bit-idêntico** à fixture |
| `CUTS-MEASURED-2026-08-18.json` | corpus real (67.013 chunks), `scope="global"` × 6 agentes, antes/depois do inflow |
| `INGRESS-CLEAN-2026-08-18.json` | 12 casos × 6 agentes, corpus de hoje — via de ingresso do chunk escrito |
| `INGRESS-INFLOW-2026-08-18.json` | idem, sob 30 dias do inflow do próprio estudo |
| `SPREAD-SLOTS-2026-08-18.json` | espaçamento de salience entre os 10 slots, por agente |

⚠️ `reachable_share.py` e `link_feasibility.mjs` passam a **artefato histórico**.
Eles produziram todo número de alcance publicado e modelam um limiar que a
produção não aplica.

---

## O defeito de raiz, uma frase

O §2 modela a entrada no brief como **cruzar um corte de salience**
(`CUT_FRESH = 0.7342`), e derivou dose, banda, alcance, teto e testabilidade de
H1 desse modelo. A produção **não aplica corte nenhum** na via de cobertura:
`pick` fase 3 toma os primeiros `freshSlots = 2` candidatos nunca-servidos, na
ordem de `coverageCompare`, sem limiar. Entrar não é cruzar uma barra — é **ficar
entre os dois primeiros de uma fila**.

Toda afirmação abaixo marcada 🔴 descende dessa única troca.

---

## Tabela

Legenda: ✅ verdadeiro · 🔴 falso · 🟡 verdadeiro pelo motivo errado · ⚪ incompleto

### A. O modelo de corte

| # | linha | claim | | substituta medida |
|---|---|---|---|---|
| A1 | 438 | *"contra um main-pool cut de 0.8524 e um coverage-slot cut de 0.7342"* | 🔴 | **Nenhum dos dois existe no caminho servido.** O cut principal medido é **0,6100–0,7922** por agente (`CUTS-MEASURED`), nunca 0,8524. O cut de cobertura não existe: não há limiar. |
| A2 | 442-445 | coluna *"`w` needed"* = 5,97 / 1,82 / 0,44 / 0 | 🔴 | Medido, **todas as quatro severidades entram a `w = 0`** nas idades 1 d e 7 d, nos 6 agentes (`INGRESS-CLEAN`, 48 células). A 30 d, nenhuma entra — a janela de idade, não o corte, decide. |
| A3 | 568 | *"`w_min = (0.7342 − base) / (0.043 × sev)`"* | 🔴 | A aritmética reproduz; a fórmula é **inaplicável**. Mesma classe de [[feedback_correct_arithmetic_can_come_from_an_inapplicable_formula]]: 11 versões conferiram o valor, ninguém perguntou o que a expressão pressupõe. |
| A4 | 525 | *"`CUT_FRESH = 0.7342` é FROZEN … a designação é `argmin (0.7342 − base)/(Δ_cut×sev)`"* | ⚪ | Congelar é ato do documento e vale. Mas a constante **não tem contraparte no código**: sobrevive apenas como regra interna de designação, não como modelo da produção. Precisa ser redeclarada nesses termos. |

### B. Alcance, teto, banda

| # | linha | claim | | substituta medida |
|---|---|---|---|---|
| B1 | 450, 474-476 | alcance **58,27% / 78,58% / 100%**, tetos 60,18% / 75,62% / 100% | 🔴 | **No corpus de hoje o alcance é 100% dentro da janela a qualquer dose, `w = 0` incluído, e 0% fora.** A função-escada de três platôs não tem contraparte. |
| B2 | 478 | *"`w = 0.5` e `w = 1.0` alcançam exatamente zero"* — o argumento que matou a banda antiga | 🔴 | Alcançam o mesmo que `w = 0`: tudo, dentro da janela. **O argumento é vazio.** A troca de banda em si é inócua; a justificativa registrada não. |
| B3 | 521 | *"a testabilidade de H1 repousa no teto de 60,18% de `w = 2.0` contra um MDE de 30%, então o desfecho primário fica intocado por esta correção"* | 🔴 | A frase é falsa **duas vezes**: o primário não é `w = 2.0`, é o pooled (§3:344-351); e 60,18% é o teto do braço mais fraco. ⚠️ *Correção 2026-08-19 (Kimi K2): a redação anterior concluía daí que **"o desfecho primário NÃO fica intocado — é exatamente o oposto"**. Isso é **non sequitur** — premissa caída não torna a conclusão falsa. Recomputado sobre o corpus, o primário pooled sobrevive. O que cai é a **justificativa**, não o desfecho.* |
| B4 | 519, 565 | tabela ajustada pela janela (88,06%, 60,13%) | 🔴 | Mesmo modelo, mesma sorte. |
| B5 | — | *(não registrado, e é o achado)* | 🆕 | **Sob 30 dias do inflow do próprio estudo, só S4@1d entra** — todo o resto é expulso pelos chunks do próprio estudo (`INGRESS-INFLOW`). S4 é **0,08% das falhas**. No regime em que o estudo roda, o alcance não-impulsionado é ~nulo, e a dose passa a agir como **desempate entre os chunks do estudo**, não como limiar contra incumbentes. Mecanismo coerente — só não é o registrado. Depende do volume de escrita, que é a medição que ainda falta. |

### C. Quais slots

| # | linha | claim | | veredito |
|---|---|---|---|---|
| C1 | 449 | *"o tratamento age pelos 2 slots de cobertura e nunca pelos 8 principais — BY CONSTRUCTION"* | 🟡 | **Conclusão verdadeira, mecanismo falso.** Medido: em 72 células agente×caso, o chunk nunca entrou como `principal`. Mas o motivo é a ordem em `pick` (fresh é tomado primeiro), **não** uma margem contra um corte. A frase é verdadeira por acidente, e o "0.2151 acima do cut principal a `w = 7.5`" que ela refuta também é do modelo morto. |
| C2 | 466 | *"0% — um slot, by construction"* | ✅ | Consistente: `freshSlots = 2` limita a dois e a designação a um. |
| C3 | 497 | *"access_count 0 … chega ao brief **somente** pelos dois `freshSlots`"* | ✅ | Confirmado nas 72 células: via cobertura ou não entra. |

### D. Os campos do chunk escrito

| # | linha | claim | | substituta medida |
|---|---|---|---|---|
| D1 | 493, 509 | *"`chunk_type = 'lesson'` fixa `importance = 0.90` via `IMPORTANCE_BY_TYPE`"* / o gate *"**passa**"* | 🔴 | **Existem duas implementações da mesma regra, e o caminho de entities usa a que não tem o caso.** `ingest.ts:detectChunkType` casa `memory/entities/lessons/` → `lesson`; mas `ingestEntityFile()` chama `ingest-entity.ts:inferChunkTypeFromPath` (linha 244), que só conhece `agents/`, `projects/`, `people/`, `systems/` e cai em **`other`** → `FALLBACK_IMPORTANCE = 0.40` → o gate `>= 0.7` **reprova**. Medido nos 168 chunks reais sob `memory/entities/lessons/%`: `chunk_type = 'other'` em **100%**, e só as **42** seções `compiled` passam (importance 0,90, vindo de `compiledImportance = max(importance, 0.9)`, **não** da tabela por tipo); as 42 `frontmatter` e as 84 `timeline` carregam 0,40 e reprovam — **126 de 168**. Em todo `memory/entities/%`: **190 de 755** passam. Mesmo perigo de duas implementações que o spec do componente 1 já proíbe para `sig()`. ⚠️ *Os nomes `inferChunkTypeFromPath`/`inferImportance` na linha 509 apontam para o módulo certo por acidente: são os do `ingest-entity.ts`, e é justamente o que reprova.* |
| D2 | 495 | *"`pain` = a severidade adjudicada … é o carrier do tratamento"* | 🔴 | O ingest escreve `pain` por **regex de palavra-chave sobre o texto** ([[feedback_pain_column_is_topical_not_episodic]]). Sem override explícito o carrier do tratamento é ruído tópico. Já endereçado no spec do componente 1. |
| D3 | 499, 511 | `source_file` sob `memory/entities/` → sub-pool global, janela de 30 d | ✅ | Verificado no `WHERE` e confirmado na medição: 29 d entra, 31 d não. ⚠️ Mas o sub-pool global **está vazio hoje** — o chunk que passa o gate mais novo tem 38,9 d, e a escrita de entities caiu 749 (jun) → 6 (jul) → **0 (ago)**. A janela que salva os números é a de um armazém que parou. |
| D4 | 546-548 | timestamps no instante da escrita, `last_accessed_at = null` | ✅ | E o decaimento medido bate. ⚠️ Achado colateral: `recencyComponent` chama `Date.parse()` cru sobre datetime UTC ingênuo enquanto `parseDbDateMs()` acrescenta `"Z"` — em host UTC−3 isso **infla a recency em ~7,2e-5**. Defeito de produção, declarado e não consertado no meio da semana. |

### E. `Δ_cut`

| # | linha | claim | | substituta medida |
|---|---|---|---|---|
| E1 | 599 | *"`Δ_cut = 0.043`, o spread entre os 10 slots"* | 🔴 | Medido, o spread **total** é **0,0951 (cipher) – 0,2773 (lex)** — 2,2× a 6,4× maior. |
| E2 | 599 | *"`w = 1.0` desloca aproximadamente uma posição de fronteira"* | 🔴 | **Subestima, não superestima.** O gap adjacente **mediano** é 0,0038–0,0157, então um `Δ_cut` atravessa de **3 a 11 posições** (nox: 0,043 / 0,0074 ≈ 6). `Δ_cut` não é nem o spread total nem o gap adjacente; é uma terceira coisa sem referente. A dose registrada é **mais agressiva** do que o documento afirma. |
| E3 | 601 | `Δ_cut` congelado pré-tratamento, não recomputado por epoch | ✅ | O raciocínio (quantidade pós-randomização) está certo e independe do valor. |

### F. Coerência interna

| # | linha | claim | | veredito |
|---|---|---|---|---|
| F1 | 576 | pool de candidatos = `ORDER BY (proxy) DESC, updated_at DESC LIMIT 500` | ⚪ | Verdadeiro para o pool **principal**. A via de cobertura — por onde o tratamento age — usa **outra query**: `ORDER BY last_served ASC, proxy DESC LIMIT 400`, com `coverageCompare` tratando nunca-servido como `-Infinity`. O documento nunca a enuncia. |
| F2 | 577 vs 546 | *"`access` é um sinal **binário**"* | 🔴 | A linha 546 já se autocorrigiu para graduado (`clamp01(log1p(n)/log(1000))`) e a 577 continua dizendo binário, **duas linhas de distância**. Nenhum número move (o desafiante nasce em 0), mas é [[feedback_a_defect_class_does_not_stay_fixed_where_it_was_found]] outra vez, dentro da mesma seção. |

---

## Uma nota de método, porque ela quase entrou como defeito

O achado D1 chegou a esta auditoria em segunda mão, como *"`inferChunkTypeFromPath`
não tem caso `lessons/`"*. Reconferido antes de commitar: `detectChunkType`
**tem** o caso, na linha 24 do `ingest.ts`. A afirmação herdada estava **certa no
efeito e errada na causa** — e a causa certa (duas implementações, e o router de
entities usa a sem o caso) é mais grave do que a errada, porque é a mesma classe
de defeito que o spec do componente 1 já proíbe em outro lugar.

Se eu tivesse propagado a versão herdada, a emenda v1.12 registraria um defeito
inexistente como corrigido e deixaria o real de pé. Vale para toda linha desta
tabela: nenhuma sobreviveu sem apontar para um artefato desta data.

**Dois requisitos do spec do componente 1 saem validados por medição**, não por
argumento: a seção `compiled` garantida (é a única que passa o gate) e o override
explícito de `pain` (o ingest escreve regex tópico).

## O que sobrevive intacto

Vale dizer explicitamente, porque a lista acima é longa e o leitor pode concluir
mais do que ela diz:

- toda a camada de desenho — randomização por epoch, beacon, `N = 234`, DE, ICC,
  alocação 117/39/39/39, washout, calendário, painel, α ordinal, `assign_arms.py`;
- o estimando, o snapshot de serving, o argumento de carry-over;
- o allowlist de escopo e a exclusão analítica;
- as travas de **método**: designação independente da dose, `Δ_cut` pré-tratamento,
  um chunk por assinatura, a proibição de recomputar constantes por epoch.

Nada aqui vem de olhar dados de braço — não existem. Tudo é propriedade do
mecanismo, medida antes do sorteio, que é a ordem que o Toto fixou em 17/08.

## ⚠️ Correção pós-revisão adversarial (Grok 4.6, 2026-08-18)

A auditoria trata a **independência de agente** da via de cobertura como achado
medido. É medido, mas **não é propriedade do mecanismo**: vale porque
`agentFresh = 0` nos seis agentes, e isso porque a escrita de entities parou
(749 jun → 6 jul → 0 ago). Se voltar, os sub-pools por agente enchem, e a janela
deles é de **7 dias** contra 30 do global — a via vira agente-dependente.

Vale para toda linha desta tabela medida sobre o pool vazio de hoje: é o estado do
armazém, não a construção. As linhas que **não** dependem disso são as que saem do
código (`pick` sem limiar, as duas implementações de inferência de tipo, `pain`
por regex) e do lock de campos (a escada de severidade).

## O que a auditoria não resolve

1. **A taxa real de episódios adjudicados por epoch.** Todo corte medido depende
   de `~396/dia`, que é **projeção**. Só o write path do componente 1 mede.
2. **A dose, redefinida.** Se entrar não é cruzar barra e sim vencer fila, `w`
   tem de ser expresso contra o **espaçamento da fila** — e o espaçamento é
   por-agente (0,0951–0,2773). Absoluto ou relativo ao agente é decisão de
   desenho, e precisa ser registrada antes do sorteio.
3. **Por que a escrita de entities parou em agosto** — operacional, e é ela que
   torna o sub-pool global vazio.

## Destino

Uma emenda **v1.12** única (Zenodo + segundo registro OSF), cobrindo a tabela
inteira de uma vez. Não nove conversas por achado. O depósito v1.11
(`10.5281/zenodo.21978476`) e o registro OSF `yf7d2` ficam como estão — são
imutáveis, e a emenda é o mecanismo previsto para isso.
