# Especificação de análise — Paper 2

> **Escrita em 2026-09-10, dez dias antes do fecho da janela** (`2026-09-20 22:51:23Z`).
> A data importa mais que o conteúdo: uma especificação de análise redigida **depois** do
> fecho é post-hoc por construção, e nenhuma redação a salva. Tudo aqui é anterior a
> qualquer desfecho adjudicado.

## 0. O que este documento NÃO decide

O **enquadramento já está decidido** — instrução do Toto em 2026-09-09 16:01 BRT,
registrada em `ENQUADRAMENTO-2026-09-09.md`: *o método vira a manchete; o contraste
pré-registrado entra como piloto subdimensionado declarado, com intervalo à vista e a
frase explícita de que não é evidência de ausência de efeito.*

Este documento não reabre isso. Ele especifica **o que exactamente será computado e
reportado** sob esse enquadramento, e o que fica proibido.

---

## 1. Conjunto de análise — medido, não estimado

Artefato: `measurement/out/JANELA-ELEGIVEL-2026-09-10.json`, com censo de entrega de
procedência declarada (`out/CENSO-SERVIDO-2026-09-10.json`: host `srv1826603`, log
sha256 `03de9eb714dc6c39…`, 12.173 linhas, 0 divergências entre as duas chaves de epoch).

**Janela elegível: 20 epochs de 234 pré-registrados (8,5%).** A restrição não é escolha —
os 19 designados têm `created_at` idêntico e a janela global de frescor é de 30 d.

| unidade | n | epochs |
|---|---:|---|
| **inteira** (relógio inteiro **e** entrega cheia) | 15* | `09-04`…`09-09`, `09-11`…`09-19` |
| **parcial por relógio** | 2 | `09-01` (22,38 h/24), `09-20` (13,86 h/24) |
| **parcial por volume** | 1 | `09-03` (441 de 672 briefs) |
| **vazia** | 1 | `09-02` — **0 briefs, epoch nunca abriu** |

\* 6 confirmadas em 10/09; as 9 de `09-11`…`09-19` são projeção sob entrega cheia e serão
reclassificadas pelo censo no fecho. O artefato marca-as `futuro`, não `inteira` — não
projeta.

### `09-01` — errata da própria spec, 2026-09-10

A primeira versão deste documento chamou `09-01` de **"exposição MISTA"**, e isso
sobrestima o problema. Medido depois, e a medição muda a regra:

| fase | n | de | até |
|---|---:|---|---|
| `shadow` (w=2,0) | 42 | `09:07:01.808Z` | `10:22:05.961Z` |
| `active` (w=4,0) | 630 | `10:37:01.943Z` | `2026-09-02T08:52:06.139Z` |

**Zero sobreposição nos dois sentidos** (`shadow` após o 1º `active`: 0; `active` antes do
último `shadow`: 0). Não é exposição intercalada — é **sequencial**, e a distinção decide
a regra: intercalada invalidaria o offset, sequencial torna-o exato.

E as duas quantidades que eu tratava como problemas separados são **o mesmo fato medido
por duas vias, e concordam**: `630/672 = 93,75%` de briefs contra `22,38/24 = 93,25%` de
relógio — 0,5 pp de diferença. `09-01` tem **um** defeito (arranque tardio), não dois.

⚠️ O rótulo veio de eu ver dois modos no mesmo epoch e escrever a palavra que implica
intercalação, sem conferir se havia sobreposição. O número (dois modos) estava certo; a
palavra afirmava mais do que o número. Família de
`feedback_a_correct_number_carried_by_a_wrong_sentence`.

**Nota sobre o que a fase `shadow` é:** em `shadow` o contrafactual é computado e o brief
**servido é o de controle**. Logo os 42 briefs são **exposição de controle dentro de um
epoch designado tratamento** — 6,25% de diluição **na direção do nulo**, isto é,
conservadora contra a hipótese. Isso é declarado, não corrigido.

### Composição de braços — realizada contra desenhada

| dose | desenho (234) | alocado na janela (20) | **servido** |
|---|---:|---:|---:|
| controle w=0 | 117 | 9 | **8** |
| w=2,0 | 39 | 6 | 6 |
| w=4,0 | 39 | 4 | 4 |
| **w=7,5** | 39 | **1** | **1** |

**11 tratamento / 8 controle servidos.** A diferença é 3 epochs, **≤ 5**, logo o gatilho
pré-comprometido do PREREG §5 (*"se os tamanhos realizados diferirem em mais de 5 epochs,
o intervalo estratificado é reportado **ao lado** de um não-estratificado"*) **não dispara**
— o bootstrap estratificado permanece o primário. Isto é o desfecho de um ramo já
registrado, não uma escolha nova.

---

## 2. Regras para os parciais e o vazio — pré-comprometidas

| epoch | classe | regra | por quê |
|---|---|---|---|
| `09-02` | vazia | **excluída do conjunto de análise**, contada e reportada | zero exposição e zero desfecho. Não é dado ausente, é unidade não realizada. É controle, logo excluí-la **piora** o desbalanço (9→8) e isso é declarado, não compensado |
| `09-03` | parcial por volume | **incluída, com offset**; e a cobertura do PREREG §5 é computada e reportada **antes** de qualquer decisão de exclusão | `441/672` mede *uptime de serving*, **não** a cobertura de `brief_log` do prereg. São grandezas diferentes e a segunda é que governa o piso de 95% |
| `09-01` | parcial por relógio (arranque tardio, fases **sequenciais**) | **incluída no ITT** pelo braço designado, com offset sobre a exposição tratada (630 briefs / 22,38 h); a sensibilidade que a remove é reportada ao lado | ITT respeita a randomização, e excluir por causa do que aconteceu **depois** dela é conditioning pós-tratamento — o mesmo erro que o PREREG §5 já pré-comprometeu contra no caso da cobertura. As fases não se intercalam, logo o offset é exato e não há contaminação a remover; a diluição de 6,25% aponta para o nulo |
| `09-20` | parcial por relógio | **incluída, com offset** | truncamento puro; o corte cai **dentro** do epoch, às 22:51:23Z |

**Nenhum parcial é arredondado para dentro ou para fora.** Os três entram declarados, e a
sensibilidade que os remove é reportada ao lado — divergência entre as duas é reportada
como está, nunca adjudicada em favor de uma.

---

## 3. 🔴 Potência realizada: H1c não tem resultado possível

Artefato: `out/H1C-POWER-REALIZADO-2026-09-10.json` (`measurement/potencia-h1c.py`,
estendido para braços desbalanceados via **média harmónica** dos N efetivos — a
aritmética sobrestimaria, e `epochs//2` inventaria simetria que o desenho perdeu).

**Controle positivo do próprio script:** re-executado no desenho de 234 balanceados,
reproduz o artefato de 2026-08-30 nos quatro valores — `n_efetivo 1139`, `DE 21,87`,
`MDE 0,3668`, `oportunidades 24.921`. A extensão não moveu a via balanceada.

| | desenho (117/117) | **realizado (11/8)** |
|---|---:|---:|
| N efetivo por braço | 1.139 | **90** |
| MDE relativo em H1c | 36,7% | **saturado em 100%** |
| detectável no limite (p1 = 0) | sim | **não** |
| efeito necessário nas cobertas (cenário ótimo, 40%) | 91,7% | **250%** |

**Leitura — e ela é CONDICIONAL, corrigida em 2026-09-10 após a sessão par medir a
margem.** A primeira versão afirmava categoricamente *"não existe efeito detectável"*.
Isso não se sustenta, e o motivo está na lista de aproximações do próprio script.

`n_efetivo` **crítico** para `p1 = 0` ser detectável a 80%: **95,26**. Os três recortes
defensáveis:

| recorte | epochs-equivalentes | `n_ef` | fator que falta | **ICC crítico** | queda que vira o veredito |
|---|---|---:|---:|---:|---:|
| exposição **fracionária** (o honesto) | 10,938 T / 7,234 C | 84,8 | 1,123× | 0,087133 | **11,5%** |
| epochs inteiros (1ª versão) | 11 T / 8 C | 90,2 | 1,056× | 0,092987 | **5,6%** |
| `09-03` excluído pelo piso | 11 T / 7 C | 83,3 | 1,143× | 0,085523 | **13,1%** |

⚠️ **Por que a margem importa:** o ICC vem do PREREG e foi estimado para **densidade por
session-hour**, não para proporção por oportunidade — é a aproximação nº 1 da lista do
script. Margem estreita num parâmetro declaradamente estimado *para outra grandeza* não
sustenta afirmação categórica.

**Enunciado que fica pré-comprometido, e diz a mesma coisa de forma defensável:**

> Sob o critério de inclusão realizado e `ICC = 0,0985`, **nem a eliminação total das
> falhas repetidas é detectável a 80% de potência**. O veredito viraria com uma queda de
> **11,5%** no ICC sob a contagem fracionária (5,6% sob a contagem por epochs inteiros).
> Nenhum critério de inclusão defensável o inverte.

Três coisas sustentam o "nenhum":

1. **A contagem por epochs inteiros era generosa.** Somar 1 por epoch atribui exposição que
   não houve — `09-01` entregou 630/672, `09-03` 441/672, `09-20` entrega 13,86/24. A
   contagem fracionária **dobra a margem**, de 5,6% para 11,5%. O script passou a aceitar
   fração.
2. **A média harmónica também é generosa.** Ela é a substituição exata para o termo de
   variância agrupada (`2/n_eff = 1/n_t + 1/n_c`), mas na forma implementada
   (`pb` não ponderado) sobrestima o poder em ~0,09 de `z` contra o cálculo de dois grupos
   desiguais em forma geral. Um revisor que refaça pela forma geral encontra o veredito
   **mais** firme. Declarado no artefato.
3. **O recorte que inverteria exige contar `09-02`.** Um cenário `9` epochs de controle
   daria `n_ef = 96,4` e `z = 0,8587` ⇒ detectável. Mas só **8** epochs de controle foram
   servidos: os 9 alocados incluem `2026-09-02`, que entregou **0 briefs**. Um epoch com
   zero oportunidades não adiciona oportunidades, logo **não existe regra de inclusão que
   alcance 9**. As duas decisões abertas do §9 movem entre 7 e 8, e os dois extremos dão
   `não detectável`.

É a mesma razão que retirou H1 de primária em 2026-08-30 (exigia 955%), agora aplicada a
H1c pelo encurtamento da janela.

> Uma perna própria foi acrescentada ao script para isto: `mde()` bissecta em `[0, p0]`,
> logo o MDE relativo **satura em 1,0 por construção** e *"MDE = 100%"* ficava
> indistinguível de *"nem eliminar tudo é detectável"*. São estados diferentes do mundo, e
> o segundo lê-se como "precisa de efeito enorme" em vez de "não há resultado possível".
> O campo `detectavel_no_limite_p1_igual_zero` separa os dois.

⚠️ **E o artefato passou a ser emitido ANTES dos guardas do script.** Os guardas devolvem
`1` quando H1c é inalcançável e, na versão anterior, retornavam **antes** do `--out`: o
veredito mais importante era o único que não deixava lastro. Em 2026-08-30 o guarda barrava
uma *decisão de desenho* e abortar era certo; hoje o mesmo predicado é um **achado** que
precisa de evidência. Mesmo conselho, ação oposta. Contrato agora: **o código de saída
carrega o veredito, o artefato carrega a evidência.**

---

## 4. Re-randomização: redesenhar os 234, nunca permutar dentro dos 20

O PREREG §5 trava **10.000 permutações** sobre o desfecho residualizado por tendência.
Com a janela truncada há uma armadilha que invalidaria o teste:

> A randomização foi feita sobre **234 epochs**, com estratos `metade-de-calendário ×
> dia-útil/fim-de-semana` e apportionment por maior resto. Permutar os braços **entre os 20**
> não reproduz essa distribuição — os 20 caem todos na primeira metade de calendário, onde
> a estratificação colapsa a dia-útil/fim-de-semana.

**Pré-comprometido:** cada réplica re-executa `assign_arms.py assign --seed <novo>
--start 2026-09-01` sobre os 234 epochs e **restringe** a realização à janela de análise.
A distribuição de referência é a do desenho, não a de uma permutação conveniente.

**Medido em 300 sementes** (17,9 s ⇒ 10.000 ≈ 10 min, viável):

- **300 padrões distintos em 300 corridas, zero colisões** ⇒ o espaço **não é enumerável**;
  as 10.000 réplicas do prereg continuam a ser a implementação correta, não um exato.
- **`n_tratamento = 11` é típico:** a moda é 10 e o 11 ocorre em 47/300.
- 🔴 **`n` de `w=7,5` igual a 1 está na cauda esquerda:** ocorre em **23/300 = 7,7%**,
  contra moda 3-4. O braço de dose máxima ficou com n=1 **por sorteio infeliz somado ao
  truncamento**, e essa decomposição vai no relato — não é "o desenho é ruim".

---

## 5. Controles — o positivo passa; o negativo estava mal enunciado

Artefato: `out/CONTROLES-2026-09-10.json`. Semântica declarada: `mexeu` compara
`ids_tratado` com `ids_controle` por **pertencimento** (`set`), não por lista — a
comparação de lista mistura reordenação com entrada/saída e no epoch `09-08` dá **48**
contra **20** (errata da sessão par, reproduzida aqui por via independente: 20).

**Controle positivo — PASSA em 6 de 6 epochs de tratamento servidos.** A dose alterou o
conjunto servido em todos: 2,83% · 2,98% · 3,57% · 4,91% · 5,21% · 5,65%. Se algum epoch
de tratamento tivesse dado 0, o nulo seria do **instrumento** e não do efeito.

🔴 **Controle negativo: o enunciado óbvio é inválido.** Eu ia pré-comprometer *"epoch de
controle tem `mexeu == 0`"*. Nos epochs de controle os campos `ids_controle`/`ids_tratado`
**não existem** — `sem_ids == n` em `09-03` (441/441), `09-07` (672/672) e `09-10`
(140/140). Logo `mexeu == 0` é indistinguível de *"o campo nunca foi escrito"*, que é a
**regra 9** do `CLAUDE.md`: predicado que exige o dado que falta não cobre a falta do dado.

**Enunciado válido, e é o que fica pré-comprometido:** *epoch de controle tem
`sem_ids == n`* — o dual-compute **não corre** onde `w=0`, que é o que o desenho prevê.
Verificável, e **passa em 3 de 3**.

⚠️ **Não existe controle negativo intra-braço no log — confirmado por três vias**, e a
proposta óbvia falha de duas formas distintas:

| candidato | resultado medido | por que não serve |
|---|---|---|
| `mexeu == 0` nos epochs de **controle** | passa 3/3 | os campos `ids_*` **não existem** em `w=0` ⇒ regra 9 |
| condicionar em *"designado presente no conjunto **servido**"* | 0 movimentos em 2.908 briefs | **tautológico**: "servido" é `ids_tratado`, que é **pós-dose** — o churn *cria* a presença, logo churn-sem-presença é impossível **por construção** |
| condicionar em *"designado presente no conjunto de **controle**"* (independente da dose) | **119 movimentos** em 3.027 briefs sem presença | não é falha de instrumento — é **o mecanismo**: a dose age promovendo chunk que **não** estava no baseline. Ausência do controle é onde ela tem **mais** o que fazer |
| `boost_by_id` vazio ⇒ `mexeu` deve ser 0 | `sem_boost = 0` em **3.990** briefs | o estrato é **vazio**: o boost sempre aplica a algo |

⚠️ **A terceira linha inverte a premissa da segunda**, e é o achado: condicionar em
presença **pós-dose** não é um controle, e condicionar em presença **pré-dose** mede o
mecanismo em vez de o negar. O `mexeu | ausente-do-controle` por epoch: 13 · 26 · 26 · 20 ·
15 · 19.

**Pré-comprometido:** a especificidade vem do **replay com designação-sham** — 19 chunks
aleatórios **não** designados, mesmo `w` — e o argumento que o valida é da sessão par: o
viés do replay é **anticorrelacionado com o efeito** (descarta os briefs em que a dose
agiu), logo **sob a nula ele desaparece**. Isso torna o replay válido como **teste de
especificidade** sem quebrar a proibição do §7, que continua a valer para o **estimador**.
A distinção é: o replay não pode *medir* o efeito, mas pode *falsificar* a especificidade.

---

## 6. O que será reportado

1. **Ponto estimado com intervalo e `n` por braço na mesma linha.** O número entra —
   esconder é o outro jeito de mentir sobre ele.
2. **A declaração de subdimensionamento com o artefato**, incluindo `MDE saturado` e
   `detectavel_no_limite = false`, e a frase de que ausência de significância **não é**
   evidência de ausência de efeito. No abstract, não em nota.
3. **A decomposição da cobertura por assinatura**, já pré-comprometida em
   `DESIGN-REVISION-2026-08-30.md`: um nulo em H1c **não distingue** *"o mecanismo não
   funciona"* de *"as lições que ele promove são genéricas demais"* — 93,8% da cobertura
   é a assinatura-balde `Bash|shell:outro`.
4. **O ITT sobre todos os epochs pós-washout sem exclusão de cobertura**, ao lado do
   primário (PREREG §5, obrigatório porque cobertura é pós-randomização).
5. **A correlação braço-cobertura com IC, incondicionalmente** (M10).
6. **`09-01` com as duas fases declaradas** (42 `shadow` até 10:22Z, 630 `active` desde
   10:37Z, sem sobreposição) e a sensibilidade que o remove.
7. **A decomposição sorteio × truncamento** do `n=1` no `w=7,5` (7,7% da distribuição).

## 7. O que fica PROIBIDO

- **Promover qualquer subgrupo a primária.** Com 19 unidades, procurar o recorte que
  atinge significância é garantia de o encontrar.
- **Fundir doses para comprar `n`.** `w=2,0`, `w=4,0` e `w=7,5` são níveis desenhados;
  colapsá-los em "tratamento" para uma alegação de **dose-resposta** é a alegação a
  destruir a sua própria premissa. Para o contraste binário ITT o pool é legítimo e está
  registrado — a proibição é sobre dose-resposta.
- **Ler dose-resposta.** O topo (5,65%, n=1) fica acima do topo do braço `w=2` (5,21%),
  mas com n=1 no topo e sobreposição em 2,83–5,21 **não há gradiente a ler**. Fechado em
  `ENQUADRAMENTO-2026-09-09.md`.
- **Apoiar o estimador no replay.** Medição da sessão par: o replay descarta **100% do
  sinal registrado do braço `w=7,5`** (38 de 672). Um estimador que dependa dele mede o
  controle e chama-o de tratamento.
- **Arredondar parcial para inteiro.** Nem para dentro, nem para fora.
- **Reportar um nulo sem os itens 2 e 3 do §6.** Nulo subdimensionado apresentado como
  resultado é a exata família de defeito que este trabalho passou oito semanas a
  documentar.

## 8. Regras pré-registradas que ficam INAVALIÁVEIS

Declaradas aqui, antes do fecho, para que a sua ausência no paper não pareça omissão:

| regra (PREREG §5) | por que não é avaliável | o que fica no lugar |
|---|---|---|
| **TOST braço×cobertura** a `\|r\| ≤ 0,15` | trava exige **K ≥ 30** epochs analisados; teremos ≤ 19 | a correlação e o IC são reportados incondicionalmente (M10). O relato é *"não avaliável no K realizado"*, que **não** é o mesmo que *"equivalência não estabelecida"* |
| **dose-resposta / H3** | `n=1` no topo | efeito por dose com `n` na mesma linha, sem gradiente |
| **leave-one-agent-out** | 6 agentes sobre 19 epochs | reportado como exploratório, sem inferência |
| **primeira vs segunda metade de calendário** | os 20 epochs caem **todos** na primeira metade | inavaliável por construção do recorte |

## 9. ✅ DECIDIDO pelo Toto — 2026-09-10 11:21 BRT

> **Frase literal:** *"aprovo"*, em resposta às duas recomendações abaixo apresentadas
> juntas. É aprovação explícita das duas, não inferência a partir de silêncio nem de
> pergunta retórica — a distinção que o §10.14 do `DEVIATIONS` custou a aprender.

Medido antes da decisão, e por isso ela é sobre um efeito conhecido: **nenhuma das duas
inverte o veredito de potência do §3.**

1. ✅ **`09-01` entra no ITT** pelo braço designado, com offset sobre a exposição tratada, e
   **sem** sensibilidade de contaminação — porque as fases são sequenciais e não há
   contaminação (ver errata do §1). Excluir seria conditioning pós-randomização, o mesmo
   erro que o PREREG §5 já pré-comprometeu contra no caso da cobertura; e a diluição de
   6,25% aponta para o **nulo**, logo incluir não pode fabricar efeito. Fica só a
   sensibilidade padrão que remove **todos** os parciais em bloco.
2. ✅ **O ITT sem exclusão de cobertura é a estimativa de manchete**, com o conjunto do piso
   de 95% como sensibilidade — invertendo a ordem default. Justificação no próprio PREREG
   §5, que diz que o papel do piso é *"precisão, não identificação"*: com o MDE saturado
   **não há precisão a proteger**, e `09-03` é **controle** (excluí-lo leva o controle de 8
   a 7). ⚠️ Isto tem de ser fixado **antes** de computar a cobertura — `441/672` é *uptime
   de serving*, não a cobertura do prereg (denominador em **sessões**), e escolher o
   conjunto primário depois de ver o número é a jogada post-hoc que esta spec existe para
   impedir.

**A medição que sustentou a decisão.** Os extremos são `11T/8C`
(`09-03` dentro, ICC crítico a 5,6%) e `11T/7C` (`09-03` fora, 13,1%), e ambos dão
`não detectável`. O único recorte que inverteria precisa de **9** epochs de controle, o que
exige contar `2026-09-02` — zero briefs entregues.

---

*Nada neste documento depende de desfecho adjudicado. As medições que o sustentam são de
serving, alocação e potência — todas anteriores à adjudicação, e todas com artefato.*
