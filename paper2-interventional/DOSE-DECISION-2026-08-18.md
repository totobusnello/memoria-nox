# A dose, re-derivada do mecanismo medido

> Sucessor de todo cálculo de dose feito contra `CUT_FRESH`. Insumo da emenda v1.12.

## A pergunta que eu tinha formulado errado

Eu disse que a decisão aberta era **dose absoluta vs relativa ao cut do agente**,
porque o cut principal medido varia de 0,6100 (lex) a 0,7922 (cipher).

**A pergunta não existe.** O tratamento age na via de **cobertura**, e o cut
principal é da via **principal**. Medido sob inflow, os dois slots de cobertura
são **idênticos nos seis agentes** — `[0.745, 0.7444]` — porque o sub-pool do
agente está vazio nos seis (`agentFresh = 0`) e tudo vem do sub-pool **global**,
que é compartilhado por construção (`source_file LIKE 'memory/entities/%'`).

A via de cobertura é **agente-independente**. A variação 0,61–0,79 é real e não
toca o mecanismo.

## O que a fila realmente é

Sob o lock de campos do §2 — `compiled` ⇒ `importance = 0.90`, `access_count = 0`,
`retention_days = 180` — a salience do chunk escrito é

```
base(sev, idade) = 0.495 + 0.15·2^(−idade/180) + 0.10·sev
```

Duas quantidades decidem tudo:

| | |
|---|---|
| degrau entre bandas de severidade | **0,0250** |
| spread de recency em **toda** a janela de 30 d | **0,0163** |

**O degrau é maior que o spread inteiro.** Logo idade **nunca** move um chunk
através de uma banda de severidade: a fila de cobertura é uma **escada de
severidade**, com idade desempatando apenas *dentro* da banda.

Isso é estrutura, não acidente do corpus — sai do lock de campos e da janela,
ambos registrados.

## A dose, contra a barra que existe

A barra do slot 2 sob inflow é o **S4 mais fresco** (S4 ≈ 0,08% de ~396/dia ⇒ ~1/dia):
**0,7445** analítico, **0,744818** medido. A dose necessária para passá-lo:

| sev | share das falhas | base @1d | `w` necessário | registrado (vs `CUT_FRESH`) |
|---|---|---|---|---|
| **S1** | 69,73% | 0,6695 | **6,98** | 6,03 |
| **S2** | 29,62% | 0,6945 | **2,33** | 1,85 |
| S3 | 0,58% | 0,7195 | 0,78 | 0,46 |
| S4 | 0,08% | 0,7445 | 0,00 | 0,00 |

### O que isso faz com a banda travada

| braço | admite | alcance |
|---|---|---|
| `w = 2.0` | S3+S4 | **0,66%** |
| `w = 4.0` | S2+S3+S4 | **30,28%** |
| `w = 7.5` | S1+S2+S3+S4 | **100,00%** |

*(registrado: 58,27% / 78,58% / 100,00%)*

**O ponto que decide: S2 precisa de 2,33 e o braço mais baixo é 2,0.** O modelo
morto dizia 1,85 e portanto que `w = 2.0` alcançava S2. Erra por **0,33** unidade
de dose — e essa fração é a diferença entre o braço mais baixo alcançar 30% ou
0,66% das falhas.

Duas derivações independentes deram os mesmos três números: a analítica acima e a
contagem de `INGRESS-INFLOW` (só S4@1d entra sem boost).

## A banda fica

Não recomendo re-centrar. Cada braço continua pousando numa **classe de
severidade distinta**, que é exatamente a regra de leitura dose-resposta que o §2
pré-compromete (*"um degrau em `w = 2.0 → 4.0` concentrado em S2"*). Sob a escada
medida esse degrau é **real e cai onde foi registrado** — o que muda são os
números de alcance, não a banda. E o braço baixo virar quase-nulo (0,66%) é
propriedade útil: vira **comparador ativo**, não braço inerte com rótulo.

## O contraste primário NÃO muda — e eu quase o mudei sem precisar

O §2 diz, em duas linhas (89 e 521):

> *"A testabilidade de H1 repousa inteiramente no teto de 60,18% de `w = 2.0`
> contra um MDE de 30%, então o primário fica intocado."*

**Isso é falso, e já era antes desta auditoria.** O contraste primário registrado
não é contra braço nenhum: §3 (linhas 344-351) aloca **117 controle vs 117
tratamento**, com os três braços *pooled* como tratamento. O GLM-5.3 já tinha
apontado exatamente isto na revisão da v1.10 — *"60,18% é o teto do braço mais
fraco, não do primário pooled (78,6%)"* — e a correção não alcançou as duas
linhas onde a afirmação vive.

Sob o mecanismo medido:

| | alcance pooled | contra MDE 30% |
|---|---|---|
| registrado | 78,95% | folgado |
| **medido** | **43,65%** | **ainda folgado** |

**O primário sobrevive intacto.** Nenhuma mudança de contraste, nenhuma
re-alocação, `r̂`/`p̂0`/ICC/`N_epochs` intocados.

⚠️ **Uma ressalva que não dá para omitir:** 43,65% é *alcance*. A quantidade que
o §2 compara contra o MDE é o **teto sobre o efeito incondicional**, que é outra
conta (a `w = 2.0`: alcance 58,27% → teto 60,18%). O artefato que produzia tetos
— `REACHABILITY-2026-08-16.md` — é do modelo morto. O teto pooled tem de ser
recomputado sob o mecanismo medido antes de "sobrevive" virar afirmação final; a
margem (43,65% vs 30%) é grande o bastante para tornar a inversão improvável, e
pequena o bastante para não ser assumida.

## O teto, recomputado sobre o corpus — a ressalva acima está fechada

O teto tem definição operacional (`REACHABILITY-2026-08-16.md` §8): **`repeats
alcançáveis / repeats totais`**. A recomputação é de **uma constante**:
`w_min` mirava `CUT_FRESH = 0.7342`; a recomputação mira `0.744495`.

⚠️ **Revisão adversarial (Grok 4.6, 2026-08-18) — a identidade que escrevi aqui é
falsa.** Chamei `0.744495` de *"o ocupante do slot 2, medido 0.744818"*. São
coisas diferentes, e na verdade eu usei **três** números como se fossem um:

| valor | o que é de fato |
|---|---|
| `0.744495` | analítico: `base_salience(S4, 1 d)`, o valor da fixture |
| `0.744380` | o ocupante do slot 2 em `CUTS-MEASURED` (`mais_30_dias`) |
| `0.744818` | o ocupante do slot 2 em `queue_spacing` sobre `p2-real.db` |

A conclusão sobrevive — os três exigem de S2 `w` = 2,320 / 2,326 / 2,341, todos
acima de 2,0. Mas **a dispersão entre eles já era a endogeneidade se manifestando**,
e eu a li como ruído de arredondamento. O que entra na emenda é a faixa, nunca um
dos três valores. Pesos, estratos e política de designação ficam idênticos
(`reachable_share_fila.py`, diff de 1 linha).

**Validação antes de acreditar no novo número:** rodado sem a mudança, o script
reproduz `0.5827 / 0.7858 / 1.0` e pooled **78,60%** — exatamente os valores
depositados. O instrumento está certo; o que muda é a barra.

| braço | teto registrado | **teto medido** | o que admite |
|---|---|---|---|
| `w = 2.0` | 60,18% | **0,00%** | nada — **inerte** |
| `w = 4.0` | 75,62% | **75,62%** | S2 |
| `w = 7.5` | 100,00% | **99,81%** | S1 + S2 |
| **pooled (o primário)** | 78,60% | **58,48%** | — |

**O primário sobrevive com folga de quase 2× sobre o MDE de 30%**, sem mudar
contraste, alocação, `r̂`, `p̂0`, ICC ou `N_epochs`.

### A escada tem dois degraus, não quatro

Medido, o chunk **designado** é S1 em 21,42% e S2 em 78,58% das oportunidades —
**S3 e S4 nunca são designados**, por serem raros demais para alguma vez serem o
match mais fácil de alcançar. Então a escada útil é:

```
S2  ->  w = 2,33        S1  ->  w = 6,98
```

E a banda travada cai exatamente em volta dela: `2.0 < 2,33 < 4.0 < 6,98 < 7.5`.

**As duas regras de leitura pré-comprometidas são confirmadas, não quebradas:** o
§2 pré-registra *"um degrau em `w = 2.0 → 4.0` concentrado em S2"* e um segundo
degrau em S1 no topo. Medido, o primeiro degrau é 0% → 75,62% ao cruzar 2,33
(**é** S2) e o segundo é 75,62% → 99,81% ao cruzar 6,98 (**é** S1).

### ⛔ `w = 2.0` NÃO é controle negativo — a barra é endógena e estocástica

*(Esta subseção substitui uma recomendação anterior minha, que dizia para manter
tudo e reenquadrar `w = 2.0` como controle negativo pré-registrado. Estava errada
pelo mesmo motivo que o `CUT_FRESH`: eu troquei uma constante por outra constante,
quando a quantidade é **variável**.)*

A barra do slot 2 é o **S4 mais fresco dentro da janela de 30 d**. S4 é 0,08% das
falhas. Se não houver S4 na janela, a barra desce para o S3 mais fresco. Logo a
barra **não é uma constante** — depende da composição diária do pool, que depende
da taxa de episódios, que **nunca foi medida**.

Pior: a medição que produziu `0.744495` usou seeding sintético com
`Math.max(1, ceil(396 × share))`, o que **forçou ≥ 1 S4 por dia**. A constante saiu
do meu próprio piso artificial.

Quanto a dose que S2 precisa se move com a taxa λ de episódios por epoch:

| λ (episódios/epoch) | S4 esperados em 30 d | P(nenhum S4) | barra | `w` p/ S2 | `w = 2.0` alcança S2? |
|---|---|---|---|---|---|
| **396** (a projeção) | 9,50 | ~0% | 0,7433 | **2,27** | não — por 0,27 |
| 200 | 4,80 | 0,8% | 0,7415 | 2,19 | não |
| 100 | 2,40 | 9,1% | 0,7380 | **2,02** | na navalha |
| 40 | 0,96 | 38,3% | 0,7287 | **1,59** | **sim** |
| sem S4 (barra = S3) | 0 | — | 0,7195 | **1,16** | **sim** |

E mesmo fixando λ = 396, a idade do S4 mais fresco faz a barra oscilar em 0,0163,
o que move a exigência de S2 entre **1,59 e 2,35**.

**`w = 2.0` cai DENTRO dessa faixa.** Não é ativo nem inerte: é estocasticamente
uma coisa ou outra, conforme a composição do pool no dia. Um controle negativo
precisa de teto zero **por construção**, não zero em média — então o reenquadre
não se sustenta. E o §2 (linha 470) trava a banda com o critério oposto:

> *"cada braço fica no MEIO de um platô, então seu alcance é robusto a erro
> pequeno no modelo em vez de empoleirado numa borda."*

`w = 2.0` está empoleirado na borda. Pelo critério do próprio documento, sai.

### Consequência: a emenda não pode ser escrita ainda

A decisão de dose **não é um julgamento** — é uma função de λ, que é exatamente o
que o componente 1 (`nox-workspace#42`) mede e ninguém mediu. Registrar uma banda
agora seria travar um número derivado de uma projeção, que é a classe de defeito
que este documento já corrigiu duas vezes em depósito público.

**Ordem revista:** deploy do #42 → medir λ e a distribuição de severidade
realizada → só então re-centrar a banda e escrever **uma** emenda v1.12.

**O que se escreve SEM λ** — a emenda não fica bloqueada inteira, e dizer que
ficava era excesso de cautela (Grok):

1. o modelo de corte não existe; entrar é vencer fila;
2. a escada de severidade — sai do **lock de campos + janela de 30 d**, não de λ;
3. o contraste primário é pooled, 117 vs 117;
4. `CUT_FRESH` não pode sobreviver como modelo de serving;
5. `w = 2.0` está na borda de uma quantidade que flutua — pelo **critério do
   próprio §2** (arm no meio do platô), a justificativa da banda cai.

**O que NÃO se escreve sem λ:** nenhum percentual, nenhum `w` necessário, o teto
de 58,48%, *"o primário sobrevive"*, e `{2.0, 4.0, 7.5}` como platôs.

⚠️ *Uma versão anterior desta lista dizia que o teto pooled de 58,48% estava
"firme e não dependia de λ" — e o próprio item trazia "a λ = 396" dentro dele.
Contradição literal, apanhada pelo Grok.*

## Revisão adversarial — Grok 4.6, 2026-08-18 (recibo `exit 0`, 2.577 bytes)

⚠️ **Nota de procedimento:** a primeira tentativa foi por casca de agente e ela foi
para idle **sem chamar o provider** — zero recibos naquele dia, em qualquer
diretório. Sondar o wrapper direto separou credencial (boa: `grok-4.6`, `exit 0`,
7 s) de escopo do agente. As duas correções acima e as três abaixo vêm da chamada
verificada por recibo, não da casca.

Além da identidade da constante e da autocontradição do "firme", três achados
que eu não tinha:

### (a) *"A via de cobertura é agente-independente"* é estado contingente, não mecanismo

Registrei como propriedade. É consequência de `agentFresh = 0` nos seis agentes —
e isso vale porque **o armazém parou de escrever** (entities: 749 jun → 6 jul → 0
ago). Se a escrita voltar, os sub-pools por agente se enchem, a janela deles é de
**7** dias (contra 30 do global), e a via passa a ser agente-dependente.

Como registrar: *"hoje o sub-pool por agente está vazio nos seis, então a via de
cobertura é de fato global; isso é estado operacional e pode reverter"* — e a
robustez leave-one-agent-out, que já é pré-registrada, é a defesa.

### (b) O dreno de 672 briefs/dia foi declarado e depois ignorado

Todas as medições de fila são **rank instantâneo**. Mas o pool é consumido: cada
brief servido marca 2 candidatos como servidos e os tira da fila de nunca-servidos.
Ocupação sob dreno ≠ ordenação num instante. Nenhuma medição minha exerceu isso, e
`pool_selfcompetition.py` — que mede exatamente o dreno — não foi religado depois
que o modelo mudou.

### (c) *"S3/S4 nunca são designados"* é artefato do modelo morto

A política de designação `melhor` escolhe por `argmin w_min`, e `w_min` depende da
constante que acabou de ser derrubada. Trocar a barra **muda quem é designado**.
Logo o `{S1 21,42%, S2 78,58%}` que reportei é uma leitura do modelo de corte, não
uma propriedade da fila — e a comparação com o número depositado, que reusa a
mesma política, herda isso.

**Consequência para a emenda:** a distribuição de severidade do designado não
entra como número. O que entra é a **regra** (um chunk por assinatura, o de menor
`w_min`), com a ressalva de que `w_min` precisa de referente novo.

## Revisão adversarial — Kimi K2, 2026-08-18 (recibo `exit 0`, 13.170 bytes)

Rodado em paralelo ao Grok, em eixos disjuntos (coerência e viés, contra
aritmética e premissas). Verificou os números contra a auditoria **antes** de
atacar.

### A omissão que nenhum dos meus eixos nomeou

> *"B5 — sob inflow real, alcance não-impulsionado ~nulo e a dose vira **desempate
> entre os chunks do próprio estudo** — é a descoberta mais relevante para a
> interpretação de H1, e P1–P6 não a mencionam."*

Está certo. Eu achei B5, escrevi na auditoria, e **não o pus na lista do que vai
ser registrado**. Junto com ele: declarar que todo número "com inflow" veio de
pool **semeado sinteticamente por mim**, e comprometer re-medição quando a escrita
orgânica voltar. Emenda que omite o achado central e a proveniência sintética dos
dados nasce incompleta.

### O viés de conveniência, localizado

Kimi **refuta parcialmente** a suspeita: manter o primário pooled (P4) é o que a
evidência manda, não preferência — a lista "o que sobrevive intacto" é conclusão
de medição. O motivated reasoning está em **dois pontos exatos**:

1. **P5** (manter conclusão trocando justificativa) — ver o teste abaixo.
2. **Manter a banda.** B2 mostrou que o argumento que matou a banda **antiga** era
   vazio. Logo a banda atual é uma decisão cuja justificativa registrada **não
   existe**. Escrever "banda mantida" como default neutro é o vício. O honesto é
   registrá-la como **subdeterminada, pendente da medição de λ**, com o critério de
   decisão explícito **antes** do sorteio.

### O teste que separa emenda honesta de racionalização

> *"A conclusão seria alcançada do mecanismo novo sozinho, por quem nunca leu a
> versão publicada?"*

Para P5, sim — 72/72 células. Então a manutenção é legítima, **sob três condições**:

- declarar a justificativa antiga **falsa** e a conclusão **re-estabelecida**,
  nunca "confirmada";
- **proibir a expressão "by construction"** — foi o pecado original;
- registrar a nova justificativa (ordem de seleção em `pick`) como **contingente à
  versão/hash do código**, não como propriedade eterna. Sem isso troco um modelo
  morto por uma conjectura viva sem âncora.

### Correções de redação que mudam o conteúdo

| item | veredito | o que muda |
|---|---|---|
| P1 (não há corte) | **PASS** robusto | propriedade de código |
| P2 (escada de severidade) | PASS **com reescrita** | *"idade **nunca** cruza banda"* é forte demais — vira *"não cruza enquanto os coeficientes atuais valerem"*, verificável em código |
| P3 (agente-independente) | **nasce overclaiming** | como fato medido é artefato (pool vazio é degenerado); como propriedade de código sobrevive **se** a query de cobertura não tiver predicado de agente. Reescrever como propriedade de código + nota de que a medição foi em estado degenerado |
| P4 (primário pooled) | **PASS** | nada no mecanismo toca randomização |
| P5 (nunca os 8 principais) | PASS **condicional** | as três condições acima |
| P6 (re-centrar após λ) | PASS, contaminado | *"396 é projeção"* está certo; a banda tem de ir como subdeterminada |
| `Δ_cut = 0.043` | **FAIL parcial** | congelar o **valor** é ato legítimo do documento; mas as **unidades** de `w` vêm do modelo morto. Congelar sem redefinir o significado é herdar unidades do cadáver — redefinir contra o espaçamento da fila, antes do sorteio |

## Fica em aberto para a v1.12

- *"Um slot, by construction"* foi medido sob o modelo morto. A designação é um
  chunk **por assinatura**; várias assinaturas podem impulsionar ao mesmo tempo, e
  `freshSlots = 2` limita a dois. Precisa ser re-medido, não re-argumentado.
- `Δ_cut = 0.043` continua sendo o multiplicador da dose e **não** é o spread dos
  slots (0,0951–0,2773) nem o gap adjacente (0,0038–0,0157). Como a escada de
  severidade agora dá o referente, `Δ_cut` pode ser reexpresso como fração do
  degrau **0,0250** — `w = 1.0` a S4 move 0,043, isto é **1,72 degraus**.
