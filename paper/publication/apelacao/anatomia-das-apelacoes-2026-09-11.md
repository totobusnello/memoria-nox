# O que faz uma apelação dar certo — pesquisa de 2026-09-11

> Pedido do Toto: *"usar appeals que tiveram sucesso como guia para ver o que faremos"*.
> Fonte: busca web em 2026-09-11 (Perplexity search; a corrida de *research* profundo
> estourou o timeout de 300 s e não entrou aqui). Tudo abaixo é citação de fonte
> localizável, com a data da fonte. **Nada inferido.**

## 1. 🔴 O achado que reordena o plano

A única anatomia quantificada de apelação que existe publicamente é da **Nature Human
Behaviour** (`10.1038/s41562-021-01174-w`, 2021-07-21) — *"How (not) to appeal"*.
⚠️ **É de um journal, não do arXiv.** Não é dado sobre moderação do arXiv, e não vou
tratá-lo como se fosse. Mas é a melhor descrição documentada do mecanismo, e os números
são explícitos:

| dado | valor |
|---|---|
| apelações de recusa **editorial** (sem peer review) bem-sucedidas, 2020 | **12%** |
| apelações **pós-review** bem-sucedidas, 2020 | **32%** |

E o motivo da reversão, na palavra deles:

> "in the vast majority of cases the reversal of the original decision was motivated by
> **the addition of data or analyses that strengthened support for the authors'
> conclusions** or — less frequently — instances of **genuine editorial error**"

Os três antipadrões que eles nomeiam, cada um com um espelho exato no nosso caso:

| o que eles dizem que NÃO funciona | espelho no nosso plano |
|---|---|
| "**'Cosmetic' changes** to your manuscript will not lead editors to overturn a decision" | 🔴 **o corte para 1,2× é cosmético** |
| "**Status is irrelevant** … we also do not take into consideration **endorsements by notable colleagues**" | o endorser famoso não entra na carta |
| "**Don't ask to speak to the manager** … Asking for a different editor will not alter the decision" | 🔴 **a via Section Chair é exatamente isto** |

⇒ **Inversão de prioridade.** O que temos de substantivo **não é o corte**: são as
**duas colunas de competidor medidas depois da recusa** (EverOS 0,6455 e Zep 0,4546,
n=2.482 cada), que são literalmente *"addition of data that strengthened support for the
conclusions"*. O corte é higiene; a medição é o argumento.

## 2. Casos reais de apelação no arXiv — o censo, com desfecho

| caso | data | o que levou | desfecho |
|---|---|---|---|
| **Abel C. H. Chen** | 2023-24 | DOI de conferência IEEE `10.1109/ICSSES58299.2023.10201083` | ✅ **aceito** → `arXiv:2402.16002` |
| **Jian Pei** | 2022 | só argumentação, sem evidência nova | ❌ mesma resposta; foi ao SSRN |
| **`yueliusd`** | 2025-09-09 | apelou **e** resubmeteu | ❌ negado + **aviso de perda de privilégio** |
| **Bashinsky** | 2015 → 2018 | apelação **com endorsement** de Valery Rubakov | ⏳ **3,5 anos sem resolução nenhuma** |
| **Reddit `r/AskAcademia`** | 2025-06-17 | apelou | ❌ *"only generic responses that echoed the initial rejection"* |
| **Franck Dernoncourt** | 2025 | — | 166 papers no arXiv e recebeu o **mesmo template** |

🔴 **Continua sendo UMA vitória documentada em seis casos, e ela tinha peer review.**
A busca de hoje não achou nenhuma reversão sem peer review. O caso Bashinsky reforça o
antipadrão da Nature por via independente: endorsement de físico eminente **não move**.

## 3. 🔴 Fato novo que fecha uma porta que a minha própria memória tinha aberto

O registro deste projeto tinha marcado como 🟢 a rota *"TMLR aceita → submeter o artigo
como **submissão nova**"*. A carta do `yueliusd`, lida hoje, traz o texto que o arXiv
manda nesse caso:

> "This appears to be a submission of a work that was previously rejected. **arXiv does
> not accept resubmission of previously rejected content.** … Further attempts to submit
> this work will result in a **temporary loss of your submission privileges**."

E, na recusa original dele: *"Attempts to resubmit this manuscript to arXiv will be
rejected and **may result in loss of submission privileges**."*

⇒ A rota "submissão nova" **não é neutra**: é o comportamento que gerou o único aviso de
punição do censo. Fica **fechada**.

## 4. Diferença textual entre a recusa dele e a nossa — hipótese, não fato

| | `yueliusd` (2025) | nossa (`MOD-103264`, 2026-09-03) |
|---|---|---|
| juízo | "does not contain **sufficient original or substantive scholarly research** and is **not of interest** to arXiv" | "would benefit from **additional review and revision** that is outside of the services we provide" |
| condição | "We will consider an appeal **if and only if** … accepted for publication in a peer reviewed journal" | "will reconsider this material **via appeal if** it is published in a conventional journal" |
| aviso de punição | **sim**, explícito | **não** |

⚠️ **Isto é leitura de duas strings, não conhecimento do processo deles.** Mas a nossa
carta é a **mais branda das duas** nos três eixos: não nega originalidade, não diz "not
of interest", não ameaça privilégio, e não traz "if and only if". **Verificável** —
reler o email em `MOD-103264` e conferir palavra por palavra antes de qualquer uso na
apelação.

## 5. O que o arXiv **exige** da apelação, literal (`info.arxiv.org/help/moderation/appeals.html`)

- canal: **user support portal** — *"Appeals will only be considered if they are made
  through the appropriate channels"* e *"**Please do not attempt to contact moderators
  directly.**"*
- conteúdo obrigatório: *"all relevant details, such as submission or arXiv identifiers,
  former correspondence"* **+** *"your rationale … including a **detailed description of
  the research content** of your article, and **how the content of your paper directly
  applies to your requested category**"*
- **PDF anexo**: *"For declined submissions, please include a pdf copy of your work"*
- prazo: *"Most appeals are resolved within a two week period"*; sem resposta em 4
  semanas, pode-se pedir status
- finalidade: *"When an appeal is denied by appellate moderators, **no further appeal is
  possible**"*, sem devolutiva
- **Section Chair**: existe, mas sob o cabeçalho *"What if my appeal is denied?"* — é
  posterior à negativa e *"they will review procedural issues"*

## 6. Consequência para o que fazemos

**O eixo da carta passa a ser a categoria, não o tamanho.** A política pede
explicitamente *"how the content of your paper directly applies to your requested
category"* — e é exatamente onde temos medição:

| o que a carta afirma | a medida que sustenta |
|---|---|
| não é survey nem position paper | `we argue` **0** · `call for` **0** · `we believe` **0** · `we advocate` **0**; related work **9,1%**; **55** obras (surveys de CS têm 100–300) |
| é artigo de medição de sistema | experimentos §5+§6 = **55,3%**; método próprio = **12,5%**; razão contribuição:alheio = **7,5:1** |
| há dado novo desde a recusa | competidores com número **2 → 4** (EverOS 0,6455; Zep 0,4546; n=2.482 cada), footnotes **20 → 69**, arXiv IDs **11 → 52** |
| a forma foi corrigida | **114** referências a artefatos internos do repo (64 a PR/issue em 41 ids distintos, 25 a `docs/*.md`, 20 a `src|dist|staged/`, 11 a `eval/`) → removidas |

⚠️ **E o que a carta NÃO deve fazer**, por evidência das fontes acima: liderar pelo
corte de palavras (cosmético), citar endorser (irrelevante e documentadamente inerte),
ou pedir Section Chair (é "speak to the manager", e é posterior).
