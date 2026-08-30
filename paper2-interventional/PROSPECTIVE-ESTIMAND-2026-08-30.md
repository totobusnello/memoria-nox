# Registro prospectivo do estimando — Paper 2

> **Precedência.** Este documento é escrito **antes** de `T_seed_assign`, antes da
> existência de qualquer epoch randomizado e antes de qualquer dado de braço. Nada aqui
> foi informado por um resultado, porque nenhum resultado existe: o estudo não começou.
>
> **O que ele NÃO é.** Não é emenda ao registro OSF `yf7d2` nem à v1.12
> (`10.5281/zenodo.22110203`). Aqueles ficam como estão — a decisão de 2026-08-27 foi
> **não emendar**, e desvios vão no paper. Este documento declara **prospectivamente** o
> desenho vigente para o Epoch 1 e nomeia, um a um, os pontos em que ele difere do que o
> registro público diz. Quem auditar deve poder reconstruir a diferença sem confiar em
> mim.

---

## 1. O estimando, nos cinco atributos

Escrito na forma do ICH E9(R1) porque os componentes existem espalhados pelo pré-registro
e nunca foram reunidos — e um estimando que não cabe numa página é um estimando que
ninguém vai conferir.

| atributo | valor | onde já estava travado |
|---|---|---|
| **População** | epochs de 24 h da frota (7 agentes nomeados + raiz do workspace), pós-*washout* de 2 h, com cobertura de `brief_log` ≥ 95% | PREREG §3, §5 |
| **Tratamento** | bônus aditivo `w × Δ_cut × severidade` no ranking **do canal de cobertura apenas**, aplicado ao chunk designado do grupo de assinatura. Braços `w ∈ {2,0; 4,0; 7,5}`; controle `w = 0` | PREREG §2; v1.12 §1 |
| **Desfecho** | **falhas repetidas por sessão-hora analisada** (densidade incondicional). Falha repetida = ação executada cuja assinatura `sig()` já constava do snapshot como *episódio de falha* escrito ≥ 1 epoch antes, e cujo novo veredito binário do painel é falha | PREREG §4.1 |
| **Eventos intercorrentes** | epochs anulados pela regra de aborto mecânica; *downtime* da frota; epochs sobrepostos a intervenções manuais de memória em `ops_audit` (removidos **dos dois braços**, por timestamp) | PREREG §5 |
| **Sumário populacional** | diferença de densidades entre braços, agregada por epoch; IC por *bootstrap* BCa de 10.000 reamostras estratificado por braço; teste do nulo agudo por permutação de 10.000 sobre o desfecho residualizado por tendência | PREREG §5 |

τ = **S1** (travado 2026-07-29, do conjunto de calibração: κ de Fleiss 0,874, `Pa` 0,952).
`sig()` no nível **primary** (74 assinaturas), implementação congelada por `sha256` em
`CORPUS-FREEZE.md`.

---

## 2. 🔴 A condição de detectabilidade, que nunca foi escrita

Este é o motivo pelo qual vale escrever este documento em vez de apenas ligar a seed.

O dimensionamento fixa **N = 234 epochs**, alocação `117/39/39/39` (controle · três doses) contra um **MDE de
30%** na densidade do desfecho. Isso foi derivado da variância e do ICC. Mas há uma
segunda restrição, que vem do **mecanismo** e não da amostra, e que o dimensionamento não
podia enxergar porque foi medida depois — no Paper A:

| grandeza | valor | o que mede |
|---|---|---|
| *reach* em `w = 2,0` | 58,27% | dos episódios escritos, quantos **podem** alcançar um slot de cobertura |
| teto do canal | 4,86% | dos briefs, quantos mudam de composição sob dose **absurda** (`w = 100.000`) |
| **`w = 2,0`, a dose que testa H1** | **11/350 = 3,14%** | dos briefs, quantos mudam de composição **no braço primário** |

As duas primeiras não são a mesma coisa e **se compõem**: o *reach* diz que a lição entra
na disputa pelo slot; o teto diz em que fração dos briefs entrar muda o que é entregue.
O estudo estava dimensionado contra o primeiro e nunca contra o segundo.

**A consequência, dita como desigualdade e não como opinião.** Se o efeito só pode operar
através de briefs cuja composição difere entre os braços, então

```
efeito global  ≤  (fração de briefs alterados)  ×  (efeito condicional nos alterados)
              ≤  3,14%  ×  100%  =  3,14%
```

sob a hipótese de que as oportunidades de falha repetida se distribuem uniformemente
entre briefs. **3,14% está uma ordem de grandeza abaixo do MDE de 30%.**

⚠️ **A hipótese de uniformidade é o ponto fraco do argumento, e é ela que decide.** O
mecanismo não sorteia qual brief altera: altera exatamente aquele cujo grupo de
assinatura tem uma lição de falha designada — isto é, **os briefs alterados são, por
construção, os mais próximos das oportunidades de repetição**. A concentração pode ser
favorável, e nesse caso o limite acima não vale.

Isso transforma a questão numa **condição declarável**, e é ela que este documento
registra, antes de qualquer dado:

> **Condição de detectabilidade (H1).** Para que uma redução de 30% na densidade global
> seja alcançável, é necessário que os ~3,14% de briefs que a dose `w = 2,0` altera
> contenham **pelo menos 30% de todas as oportunidades de falha repetida** — ou seja, uma
> concentração de aproximadamente **10×** em relação à uniformidade — **e** que a
> intervenção elimine essencialmente todas elas.

Nenhuma das duas metades é implausível a priori, e nenhuma foi medida.

**Pré-comprometimento, para que o resultado seja interpretável nos dois sentidos.** A
concentração é uma quantidade **pré-tratamento**: depende de onde as oportunidades de
repetição caem em relação aos briefs alterados, e é computável no corpus congelado sem
olhar braço nenhum. Fica registrado que ela será medida **antes do Epoch 1** e publicada
como `CONCENTRATION-<data>.json`, com três consequências fixadas agora:

1. concentração medida **≥ 10×** ⇒ o desenho segue como está;
2. concentração **entre 3× e 10×** ⇒ o estudo roda, e o MDE de 30% é reportado como
   **provavelmente inalcançável**, com o MDE implicado pela concentração medida declarado
   ao lado. O resultado nulo, se ocorrer, **não distingue** mecanismo ausente de estudo
   sub-dimensionado, e isso é dito no abstract, não numa nota de rodapé;
3. concentração **< 3×** ⇒ o desenho é **revisado antes de começar**, não depois. As
   opções não são livres: subir a dose primária de `w = 2,0` (que altera 3,14%) para
   `w = 7,5` (que altera 4,86%) compra muito pouco, porque o **teto do canal é 4,86%** e
   nenhuma dose o ultrapassa. A revisão teria de mudar o **canal**, não a dose — o que é
   outro estudo, e seria registrado como tal.

### 2-bis. Medida em 2026-08-30 — e o número passa pela razão errada

`out/CONCENTRATION-2026-08-30.json`, gerado por
`measurement/concentracao-de-oportunidades.py`. **Nenhum epoch randomizado existe.**

| | valor |
|---|---|
| oportunidades no corpus | 1.526 |
| cobertas por assinatura que a dose promove | 611 — **40,0%** |
| fração de briefs alterada | 3,14% (recomputada do artefato de dose) |
| **concentração, limite superior** | **12,74×** |
| faixa nominal | ≥10× — *"o desenho segue"* |

Nominalmente o desenho passa. **Ele não passa.**

🔴 **93,8% da cobertura vem de uma única assinatura.**

| oportunidades | % das cobertas | assinatura |
|---:|---:|---|
| **573** | **93,8%** | `Bash\|shell:outro` |
| 25 | 4,1% | `mcp__openclaw__memory_search\|consulta` |
| 12 | 2,0% | `mcp__openclaw__memory_get\|arquivo:doc` |
| 1 | 0,2% | `mcp__openclaw__web_fetch\|rede` |

Removida ela, a cobertura cai de 40,0% para **2,5%** e a concentração para **0,79×** —
*abaixo* da uniformidade, isto é, as demais assinaturas promovidas caem em oportunidades
**menos** do que o acaso daria.

⚠️ **E `Bash|shell:outro` é a pior assinatura possível para carregar esse peso.** É o
balde de menor especificidade do esquema — tudo que a taxonomia não classifica — e o
próprio pré-registro observa que ela sozinha é ~27% do corpus, motivo pelo qual a
amostragem de calibração precisou ser estratificada para não ser dominada por ela. Uma
lição de falha rotulada *"Bash, shell, outro"* é fraca exatamente onde a intervenção
precisa ser forte: prevenir **uma** repetição específica. A concentração que faz o
desenho passar é concentração sobre a assinatura que menos informa.

📌 **Três das sete assinaturas que a dose promove não aparecem em oportunidade nenhuma**
— `Bash|fs:mutacao`, `mcp__openclaw__terminal|shell:outro` e o `ctx_batch_execute`.
Quase metade do que a dose consegue promover é inerte no corpus.

**Leitura, e ela é uma decisão de desenho, não de cálculo.** A faixa pré-registrada foi
escrita supondo um agregado; o agregado medido repousa num estrato. As três faixas do §2
não previram esse caso — e não prever não é o mesmo que autorizar a leitura conveniente.
Duas leituras defensáveis:

1. **pela letra**, 12,74× ⇒ faixa ≥10× ⇒ segue;
2. **pela substância**, a concentração informativa é 0,79× ⇒ faixa <3× ⇒ revisar antes de
   começar.

⚠️ Registro que **a segunda é a minha leitura**, e a razão é que a faixa existe para
responder *"o efeito tem por onde aparecer?"*. Um efeito que só pode aparecer através de
lições rotuladas "shell, outro" tem por onde aparecer no papel e não no mecanismo. Mas a
escolha entre as duas é do responsável pelo estudo, e fica registrada aqui **antes** de
qualquer dado de braço para que não possa ser feita depois, à luz de um resultado.

⚠️ **Duas limitações que valem para os dois lados.** (a) O corpus congelado do
pré-registro **não existe mais** (§2-ter), então isto corre sobre o archive vivo, 1.843
episódios contra os 5.547 declarados. (b) O número é um **limite superior**: supõe que
promover a assinatura certa sempre acerta a sessão certa. Um teto que reprova é
conclusivo; um teto que aprova não é — e este aprova por 12,74× de teto sobre um
mecanismo cuja parte informativa dá 0,79×.

### 2-ter. 🔴 O corpus congelado do pré-registro não existe

`CORPUS-FREEZE.md` declara que a reprodução roda contra
`action-archive-20260729T094609Z.tar.gz` (107 MB, 5.547 episódios,
`sha256 ba5fcc81…`), em `/var/backups/nox-mem/paper2-corpus/` com modo `0400`, e que
*"quem reproduzir a partir deste snapshot obtém 5.547 episódios"*.

Procurado em 2026-08-30 por **nome**, por **tamanho** (~107 MB) e por **`sha256`** em
toda a máquina: não existe, e o diretório também não. É a terceira ocorrência da mesma
classe em três dias — depois do corpus do teto (rotacionado) e dos três `.ts` pinados por
hash de commit (recuperados). **Pinar o identificador de um artefato não o preserva.**

O que sobreviveu é a `sig()`: `extract_episodes.py` tem `sha256` `e860357bd9f1fc06…`,
idêntico ao congelado. A taxonomia é reproduzível; o corpus sobre o qual foi derivada não
é. A alegação de reprodutibilidade do §4.1 do pré-registro **não pode ser cumprida por um
terceiro**, e isso entra no paper.

---

📌 O item 3 é a razão de este documento existir antes da seed e não depois. Descobrir
isso no mês 8 de um estudo de 234 dias custaria o estudo inteiro; descobri-lo agora custa
uma medição sobre dados que já estão congelados.

---

## 3. O que difere do registro público, ponto a ponto

| # | o registro diz | o que vale para o Epoch 1 | por quê |
|---|---|---|---|
| 1 | v1.12 §5: *"a designação não está validamente congelada"* — **defeito aberto** | a designação **está** congelada: sorteio com seed declarada, drand `31657512`, `sha256` do conjunto `e549420907cd…`, 19 designados, TS × Python concordando | resolvido em 2026-08-26 (`DESIGNATION-SEED-2026-08-26.md`); a v1.12 foi depositada **antes** e não foi emendada, por decisão |
| 2 | desempate por `created_at` (PREREG:535) | **não existe** — sob sorteio total o desempate é dispensável, e a coluna nunca existiu em `p2_verdict` | v1.12 retratação; era não-implementável, não apenas não-implementado |
| 3 | `CUT_FRESH = 0,7342` como limiar consumido pela regra | o código **não aplica limiar nenhum**; `Δ_cut` perdeu referente | v1.12 §1.5 e retratações 3, 4, 13 |
| 4 | `T_seed_assign` — `[TO LOCK: data/hora UTC]` | declarado no §4 abaixo | é o último `[TO LOCK]` do registro |
| 5 | dimensionamento contra o *reach* | o teto do canal (§2 acima) é uma segunda restrição, medida depois do lock | Paper A, `out/CEILING-*.json` |

⚠️ **O item 1 é o mais delicado e não deve ser lido como "já está resolvido, siga".** O
registro público continua declarando o defeito, e quem auditar a v1.12 vai encontrá-lo
aberto. A resolução vive **fora** do registro, neste documento e nos artefatos que ele
cita. Isso é uma consequência aceita da decisão de não emendar, e o paper tem de dizê-la
com todas as letras — está em `DEVIATIONS-FOR-PAPER.md`.

---

## 4. `T_seed_assign` — a regra, e a ordem que ela impõe

`T_seed_assign` é o instante que define qual rodada drand fixa a **atribuição de braços**.
Ele é estritamente posterior ao registro OSF (`yf7d2`, 2026-08-18) e estritamente anterior
ao primeiro epoch de tratamento.

⚠️ **Esta é a segunda seed, e a distinção é substantiva, não burocrática.** A seed de
2026-08-26 escolhe **qual chunk** de cada grupo recebe o bônus; `T_seed_assign` escolhe
**qual braço** cada epoch recebe. O escopo negativo do `DESIGNATION-SEED-2026-08-26.md`
declara isso explicitamente. Reutilizar a primeira para a segunda seria pescaria de
rótulo com aparência de derivação: a `randomness` daquela rodada **já é pública**, então
o resultado de qualquer atribuição derivada dela seria computável offline antes de ser
declarada.

**Ordem, e cada passo trava o seguinte:**

1. medir a concentração (§2) e publicar `CONCENTRATION-<data>.json` — **é o que decide se
   os passos seguintes fazem sentido**;
2. declarar `T_seed_assign` num documento com ≥ 5 min de folga sobre a rodada, no mesmo
   protocolo dos quatro `*-SEED-*.md` existentes; empurrar **antes** de a rodada existir;
3. esperar, derivar, conferir a sequência de atribuição TS × Python por `sha256`;
4. publicar `ASSIGNMENT.json` + a data de fim de calendário
   (`primeiro epoch + 323 dias`) no OSF, antes do primeiro epoch de tratamento;
5. ligar `NOX_P2_DESIGNATION_SEED`, `NOX_P2_ASSIGNMENT`, `NOX_P2_ASSIGNMENT_SHA256`,
   `NOX_P2_OUTCOME=active`;
6. Epoch 1.

⚠️ **A declarar antes do passo 5, para que ninguém leia o efeito como defeito:** hoje o
`churn` do *shadow* é **zero**, e é zero porque sem seed no ambiente o mapa de boost sai
vazio — o mecanismo está inerte por construção, não quebrado. Ligar a seed faz o número
sair de zero. Essa transição é o mecanismo funcionando.

---

## 5. Escopo negativo

Este documento **não**:

- altera o desfecho, τ, `sig()`, o estimador, o MDE, `N`, a regra de aborto ou qualquer
  quantidade travada no PREREG ou na v1.12 — as tabelas do §1 são **transcrição**, e
  divergência entre elas e a fonte é defeito deste documento, não mudança de desenho;
- fixa `T_seed_assign` como data — fixa a **regra** e a ordem; a data vai no documento
  de seed do passo 2, que ainda não existe;
- fecha o defeito do registro público. Ele descreve o que vale para o Epoch 1 e diz onde
  as duas coisas divergem;
- autoriza o Epoch 1. A concentração do §2 é pré-condição, e o passo 1 pode reprovar o
  desenho.

**Escrito 2026-08-30, com zero epochs randomizados existentes.**
