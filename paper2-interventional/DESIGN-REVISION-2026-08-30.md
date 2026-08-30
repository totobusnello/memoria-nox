# Revisão de desenho — Paper 2

> **Decisão do Toto, 2026-08-30:** a pré-condição do §2 do registro prospectivo foi lida
> **pela substância**, não pela letra. Faixa `<3×` ⇒ **revisar o desenho antes de
> começar**. `T_seed_assign` não foi declarado, `NOX_P2_OUTCOME` continua ausente do
> ambiente, e **nenhum epoch randomizado existe**. Tudo abaixo é pré-tratamento.

---

## 1. O que a medição estabeleceu

| dose | concentração nominal | share da maior assinatura | **sem ela** |
|---|---:|---:|---:|
| `w = 2,0` — a que testa H1 | 12,74× | 93,8% | **0,79×** |
| `w = 7,5` — a máxima do estudo | 14,85× | 80,5% | **2,9×** |
| `w = 100.000` — dose absurda | *idem `w=7,5`* | — | — |

**Nenhuma dose corrige.** No teto absoluto do mecanismo — dose infinita, 12 dos 19
designados entrando — a concentração informativa é **2,9×**, dentro da faixa que manda
revisar. E não há para onde subir: `w = 7,5` e `w = 100.000` produzem **o mesmo conjunto**
de 12 chunks e a mesma fração de 4,86% dos briefs.

A assinatura que carrega o resultado é `Bash|shell:outro`, o **balde** do esquema — tudo
que a taxonomia não classifica, ~27% do corpus, e a razão pela qual a amostragem de
calibração precisou ser estratificada. Uma lição rotulada assim é fraca exatamente onde a
intervenção precisa ser forte.

📌 **Isto não contradiz o teto de 60,18% travado em 2026-08-16 — é ortogonal a ele.**
Aquele número saiu de `reachable_share.py`, que modela alcance por **severidade e idade**.
Nenhuma das duas medições olhou *quais assinaturas*. Composto por assinatura, o alcance
que resta é o do balde. As duas coisas podem ser verdadeiras ao mesmo tempo, e são.

⚠️ **Limite da minha própria medição.** As oportunidades vêm do archive **vivo** e as
assinaturas promovidas vêm de `p2_verdict`, derivado do corpus **congelado**. Os dois
conjuntos de episódios são disjuntos (§2). A comparação é válida no nível da
**assinatura** — o esquema `sig()` é o mesmo, com `sha256` idêntico — que é o nível em
que o mecanismo opera; não seria válida no nível do episódio.

---

## 2. 🔴 O corpus congelado não existe, e isso fecha a via mais promissora

`CORPUS-FREEZE.md` declara `action-archive-20260729T094609Z.tar.gz` (107 MB, 5.547
episódios, `sha256 ba5fcc81…`) em `/var/backups/nox-mem/paper2-corpus/`, modo `0400`, e
afirma que *"quem reproduzir a partir deste snapshot obtém 5.547 episódios"*.

Procurado em 2026-08-30 por **nome**, por **tamanho** e por **`sha256`** em toda a
máquina: **não existe**, nem o diretório.

E a consequência é pior do que a perda de reprodutibilidade:

> **Dos 280 episódios adjudicados em `p2_verdict`, ZERO estão no archive vivo.**

O painel adjudicou 280 episódios que hoje **ninguém pode ler**. As 55 lições e os 19
grupos de designação existem como *veredito sem evidência*: `sig_primary`, `severity` e
`chunk_id` sobreviveram na tabela; o texto que os justificava, não.

**O que sobreviveu** é a `sig()` — `extract_episodes.py` com `sha256 e860357bd9f1fc06…`,
idêntico ao congelado. A taxonomia é reproduzível; o corpus sobre o qual foi derivada e o
material que o painel julgou, não.

⚠️ Terceira ocorrência da mesma classe em três dias: o corpus do teto (rotacionado), os
três `.ts` pinados por hash de commit (recuperados), e agora este. **Pinar o identificador
de um artefato não o preserva.** A lição operacional para tudo o que vier: depositar o
**blob**, não o hash.

---

## 3. As opções, com o que cada uma custa e o que exige medir

A via que eu tentaria primeiro está **bloqueada**, e vale dizer por quê antes das outras:
refinar a chave de matching de `sig_primary` (74 níveis, com o balde) para `sig_fine`
(168 níveis, que desmembra o balde) desmontaria exatamente o problema medido.
`p2_verdict` **não tem a coluna** `sig_fine`, e recuperá-la pelos `episode_id` é
impossível — nenhum dos 280 existe mais. A opção sobrevive apenas dentro da **A**.

| # | opção | o que custa | o que precisa ser medido antes |
|---|---|---|---|
| **A** | **Recongelar corpus + re-adjudicar com `sig_fine` como chave** | painel novo (pago), nova calibração de τ, novo `CALIBRATION-SEED`; semanas | a distribuição de `sig_fine` no corpus novo — se o balde se desmembra em assinaturas com **massa suficiente** para casar oportunidades, ou se apenas se pulveriza |
| **B** | **Mudar o canal**: boost no pool principal (8 slots) em vez do canal de cobertura (2) | o teto de 4,86% é **do canal de cobertura**; o pool principal é outro ordenador | se um bônus aditivo compete lá. O Paper A mediu que o topo é ocupado por 3 chunks omnipresentes cujo componente de acesso **determina** as posições — um boost teria de vencer isso |
| **C** | **Promover H1a–c a primária** — o efeito **condicional a oportunidade**, já registrado como família co-primária | H1 incondicional era a tese do estudo: *"o que o agente de fato recebe"*. Condicional responde uma pergunta menor | a potência de H1c no `N` disponível, que nunca foi calculada para ela como primária |
| **D** | **Não fazer o estudo interventivo** | perde-se o Paper B | nada — é a opção que o material já sustenta |

⚠️ **A opção C merece um cuidado que ela não aparenta.** Promover a família condicional
depois de ver que a incondicional não tem alcance é, formalmente, trocar a hipótese
primária à luz de uma medição. Só é legítimo porque (i) H1a–c **já estão registradas**
desde a correção de 2026-08-16, (ii) nenhum dado de braço existe, e (iii) a troca está
sendo declarada aqui, antes. Se qualquer uma das três falhasse, seria *outcome switching*.

📌 **A opção B é a única que ataca a causa em vez do sintoma**, e é também a que o Paper A
já instrumentou: sabemos exatamente por que o pool principal congela, e é um mecanismo
diferente do que congela o canal de cobertura. Mas ela muda o objeto do estudo — passa a
testar uma intervenção no ranking principal, não no canal de cobertura — e isso é um
pré-registro novo, não uma emenda.

---

## 3-bis. Medido em 2026-08-30: o teto do pool principal

`out/MAIN-POOL-CEILING-2026-08-30.json`, sobre os **mesmos 350 estados**, usando a query
de candidatos do código e `calculateSalience` do `dist`.

⚠️ **É contrafactual sobre código que não existe.** A produção aplica o boost apenas no
ranking de cobertura; não há pipeline real a replicar. O que se mediu é o **ordenador**:
onde os designados caem no pool principal e quanto de boost os levaria ao top-8. Vale na
direção *"se nem assim alcança, não alcança"*.

| | valor |
|---|---|
| estados com designado no pool de 500 | **350 de 350** |
| já no top-8 sem boost | **0** |
| melhor posição do designado | **243** — idêntica nos 350 estados |
| boost necessário para o top-8 | **0,1313 – 0,1319** (mediana **0,1316**) |

📌 A posição 243 e o boost necessário **não variam** ao longo de 12,5 horas. O topo do
pool principal é estático na janela — o que é o mesmo achado do Paper A visto de outro
ângulo: o componente de acesso não decai, então quem está no topo permanece.

**Quanto de boost as doses produzem** (`w × 0,043 × severidade`, severidades
`S1 = 0,25`, `S2 = 0,5`):

| dose | S1 | S2 | alcança? |
|---:|---:|---:|---|
| `w = 2,0` — testa H1 | 0,0215 | 0,0430 | **não**, nenhuma |
| `w = 4,0` | 0,0430 | 0,0860 | **não**, nenhuma |
| `w = 7,5` — máxima | 0,0806 | **0,1612** | **só S2** |

Dose mínima: **S2 ⇒ `w ≥ 6,12`**; **S1 ⇒ `w ≥ 12,24`**, acima de toda a banda registrada.

E a severidade dos 19 designados é **10 S1 (53%) e 9 S2 (47%)** — **nenhum S3 ou S4**.

### O que isto decide

**O pool principal é ~20× mais permeável que o canal de cobertura** — um designado que
alcança o top-8 entra em praticamente *todos* os briefs, contra 4,86% no canal. A opção B
não morre pelo motivo que mataria o canal.

🔴 **Mas ela morre por outro, e o defeito é conhecido.** Sob `w = 7,5`, os **9** designados
S2 alcançam o top-8 **simultaneamente** — e o pool principal tem **8** slots. Isso é
saturação, exatamente o defeito que a correção de 2026-08-16 evitou no outro canal ao
travar *"um designado por oportunidade"*: lá, medido, *"boostar todos os matches poria
nove ou mais chunks num brief de dez slots em 46% das oportunidades"*.

A opção B, na forma direta, **reintroduz no pool principal o defeito que foi corrigido no
canal de cobertura**. Ela só sobrevive com uma regra de admissão que a correção de 16/08
já teve de inventar uma vez — e essa regra, no pool principal, não é *"um por
oportunidade"*: as oportunidades não são o ordenador do pool principal, então a regra
teria de ser desenhada do zero.

⚠️ E há uma assimetria que muda o caráter da intervenção: no canal de cobertura o boost
altera **4,86%** dos briefs; no pool principal alteraria **quase todos**. Deixa de ser uma
intervenção marginal num canal reservado e passa a ser uma mudança do que a frota inteira
recebe, o tempo todo. Isso é defensável como estudo, mas é **outro estudo** — com outro
perfil de risco e outra regra de aborto.

---

## 3-ter. ✅ Decidido: opção C — H1c passa a primária

**Decisão do Toto, 2026-08-30.** A família co-primária H1a–c, registrada desde
2026-08-16, é promovida a primária. `T_seed_assign` segue não declarado; nenhum epoch
randomizado existe.

**A legitimidade depende de três condições, e as três valem:** (i) H1a–c **já estão
registradas** — não são hipóteses inventadas agora; (ii) **nenhum dado de braço existe**;
(iii) a troca está declarada **antes**, aqui. Se qualquer uma falhasse, isto seria
*outcome switching*.

### A potência, calculada pela primeira vez

`out/H1C-POWER-2026-08-30.json` (`measurement/potencia-h1c.py`). H1c é
`falhas repetidas / oportunidade` — proporção, binomial logit, denominador =
oportunidades, tudo já travado no PREREG §5.

Medido no archive vivo: `p0 = 0,0963` (o PREREG registra `p̂0 = 0,1118` — concordância
independente razoável) e **191 oportunidades/dia**.

| | valor |
|---|---|
| oportunidades por braço, bruto | 22.347 |
| *design effect* (m=191, ICC=0,0985) | 19,7 |
| **N efetivo por braço** | **1.133** |
| MDE relativo em H1c | **33,2%** |

📌 33,2% é praticamente o mesmo MDE que H1 tinha (30%). **Trocar o denominador não
comprou potência estatística** — comprou outra coisa, que é o que importa:

| hipótese | cobertura | efeito necessário **nas cobertas** | |
|---|---:|---:|---|
| H1 incondicional | 3,1% | **955%** | 🔴 impossível por construção |
| **H1c**, cenário otimista | 40,0% | **83%** | ✅ **exigente, mas possível** |
| H1c, só assinaturas informativas | 2,5% | **1.328%** | 🔴 impossível |

**É essa a diferença que sustenta C.** H1 pedia um efeito acima de 100% — não havia
resultado possível, nem em princípio. H1c pede 83%, que é alto e alcançável.

🔴 **E a terceira linha é a ressalva que não pode sumir.** Os 40% de cobertura são, em
93,8%, a assinatura-balde `Bash|shell:outro`. Se as lições genéricas **não** funcionarem
— e é plausível que não, porque uma lição rotulada "shell, outro" mal identifica o que
repetir —, a cobertura efetiva é 2,5% e H1c volta a ser impossível.

**Pré-comprometimento, antes de qualquer dado:** o resultado de H1c será reportado
**junto** com a decomposição da cobertura por assinatura. Um efeito nulo em H1c **não
distingue** "o mecanismo não funciona" de "as lições que ele promove são genéricas demais
para funcionar", e essa indistinção vai no abstract, não em nota de rodapé. Um efeito
positivo, por sua vez, terá de ser checado contra a hipótese de que veio das ~6% de
oportunidades cobertas por assinaturas específicas.

⚠️ **Três aproximações no cálculo**, e nenhuma se cancela com as outras: o ICC vem do
PREREG e foi estimado para densidade por *session-hour*, não para proporção por
oportunidade; `p0` e as oportunidades/dia vêm do archive vivo, já que o congelado não
existe; e `is_error` é proxy do veredito do painel a τ=S1. O resultado é ordem de
grandeza, não número de dimensionamento — e é suficiente para a decisão que ele informa,
que é binária.

---

## 4. Recomendação

**B, e não porque é a mais barata — é a mais cara depois de A.** É a única em que o
mecanismo tem espaço físico para produzir o efeito que o desenho quer medir. As demais
ou aceitam medir menos (C), ou apostam que um corpus novo se comporta melhor sem razão
para crer que sim (A), ou desistem (D).

⚠️ **Mas B não deve ser iniciada sem uma medição de viabilidade**, e ela é barata: o
equivalente do teto de 4,86% para o **pool principal**. O replay já existe e já sabe rodar
sobre estados reais; o que muda é onde o bônus entra. Se o teto do pool principal também
for de poucos por cento, B morre pelo mesmo motivo que o canal de cobertura, e a decisão
real passa a ser entre **C** e **D** — que é uma escolha honesta e pequena, não um projeto.

**Ordem proposta:**

1. medir o teto do pool principal (replay, mesmo instrumento, outro ponto de aplicação);
2. com esse número, decidir entre **B** e a dupla **C/D**;
3. só então tocar em seed, `ASSIGNMENT.json` ou ambiente.

⚠️ **E, independentemente da opção escolhida:** o Paper A precisa reportar que o corpus
congelado do Paper B não existe mais. Não é detalhe operacional — é uma alegação de
reprodutibilidade publicada que não pode ser cumprida, e o paper que discute disciplina de
verificação não pode omitir a sua própria falha dessa disciplina.

---

**Escrito 2026-08-30. Zero epochs randomizados. Nenhuma seed de atribuição declarada.**
