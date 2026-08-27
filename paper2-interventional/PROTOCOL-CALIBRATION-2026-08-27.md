# Protocolo prospectivo de calibração — os 8 itens do §5

> **Escrito 2026-08-27, a partir do CÓDIGO e de nada mais.** Nenhum dado de desfecho foi
> consultado para escrever este documento. A distinção é o ponto: definir oportunidade
> lendo o pipeline é exercício **dedutivo**; definir oportunidade olhando a série de
> `churn` seria pós-observacional, e é a classe da **F3** (`REVIEWS-PREREG.md:10`), que
> este projeto já reabriu por acidente uma vez.
>
> ⚠️ **Ordem obrigatória:** este documento é **congelado por commit** antes de a harness
> do item 1 rodar sobre dado real. Se a ordem se invertesse, o item 1 seria calibrado
> contra o resultado que ele deveria medir.
>
> Base: `AMENDMENT-DRAFT-band-collapse-2026-08-26.md` §5 (os 8 itens) e
> `DEVIATIONS-FOR-PAPER.md`. Fontes de código: `serving-brief.ts` (blob depositado,
> `sha256 27dbe996…`) e `serving-brief-diversity.ts`, ambos byte-idênticos ao que serve.

---

## Item 1 — Oportunidade, definida pelo pipeline e não por censo de pool

Este é o item que desbloqueia os outros. Ler o caminho de seleção mudou a resposta.

### O canal causal do boost é UM, e é estreito

Rastreado no código:

```
provedorDeBoost
  → ordenarCobertura        // usa o boost SÓ dentro de coverageCompare, em eff()
  → devolve candidatos com `salience` INALTERADA
  → agentFresh / globalFresh
  → interleaveFresh(a, b)   // alterna as duas listas POR ÍNDICE
  → freshPool
  → pickDedup, FASE 3 apenas, com freshSlots = 2
```

E dentro de `pickDedup`, `scoreOf` é `(c) => c.salience` — a salience **crua**. Logo:

| fase de `pickDedup` | o boost age? |
|---|---|
| 0 — pinned (high-pain já no brief) | **não** |
| 1 — cotas por pool | **não** |
| 2 — backfill até `mainTarget = n − freshSlots = 8` | **não** |
| **3 — freshness slots (≤ 2)** | **SIM, e só aqui** |
| 4 — backfill final até `n = 10` | **não** |
| `picked.sort(scoreOf DESC)` final | **não** |

**Enunciado:** o tratamento só pode alterar **quais candidatos ocupam os ≤ 2 fresh
slots**. Não altera membresia via cotas, nem o backfill, nem a ordem final do brief.

### Três consequências que nenhum documento anterior registra

**(A) `interleaveFresh` destrói a monotonicidade da "posição no pool".** Ele alterna duas
listas por índice, então mover um chunk de 3→0 em `globalFresh` o move de ~6→1 no pool
interleaved. **Toda medição de "posição no pool" feita até aqui — inclusive a tabela
ilustrativa do §2 da emenda — mede a posição na lista errada.** Não é a posição que
`pickDedup` consome.

**(B) Um chunk já escolhido nas fases 0–2 NÃO PODE ser tratado.** `tryPick` começa com
`if (seenIds.has(cand.row.id)) return false;`. Se o chunk entrou por pinned ou por cota,
a fase 3 o rejeita e o fresh slot vai para outro. **Salience alta o bastante para vencer
uma cota principal REMOVE o chunk do conjunto tratável.** A intuição está invertida: o
tratamento só age sobre chunks que **não** são bons o suficiente para os slots
principais.

**(C) Ser servido NÃO é evidência de tratamento.** `tryPick` também rejeita por dedup
exato (`title|oneLiner`) e por near-dup (`isNearDup`). Um candidato à frente pode ser
descartado por isso, **promovendo o designado sem boost nenhum**. Logo qualquer desfecho
do tipo "o designado foi servido" é confundido por rejeição alheia.

### Definição a pré-registrar

> **Oportunidade** para o chunk designado `c` numa decisão de brief é a conjunção,
> avaliada por **replay do pipeline completo** sobre o estado daquela decisão:
>
> 1. `c` está no pool de cobertura (`fetchFreshCandidates`, após `WHERE` e
>    `LIMIT FRESH_CANDIDATE_POOL = 400`);
> 2. `c` **não** foi selecionado nas fases 0–2 (senão `seenIds` o bloqueia na fase 3);
> 3. `c` sobrevive a `tryPick` no estado em que a fase 3 o encontra — não é dup exato
>    nem near-dup de nada já escolhido;
> 4. a fase 3 é alcançada com `picked.length < n`, e há fresh slot livre;
> 5. **e o contrafactual difere:** o conjunto servido com boost `w` ≠ o conjunto servido
>    com `w = 0`, no **mesmo** estado. É este item que faz a definição ser de
>    oportunidade de *tratamento* e não de *elegibilidade*.

⚠️ O item 5 é dual-compute, não observação: exige rodar o pipeline **duas vezes** sobre
o mesmo estado, com e sem boost. Sem ele, "oportunidade" é elegibilidade, e elegibilidade
não é o que a dose escala.

### 🟢 O dual-compute JÁ RODA em produção — e isso simplifica o item 1

Descoberto ao ler o caminho de serving, e confirmado no arquivo depositado:
`buildBriefDiverse` computa **os dois braços por desenho** — `alt` (sem boost) e
`altBoosted` (com boost) — e devolve `diffP2`, a diferença entre eles. A linha 1027
escolhe qual servir: `return servirTratado && altBoosted ? altBoosted : alt`.

Na janela fechada `[20:28:00Z , 09:00:00Z)`: **`modo: shadow` e `servido: controle` em
352 de 352**. Ou seja, **nenhum tratamento foi entregue**, e ainda assim o contrafactual
foi computado e logado em todas as 352 decisões.

**Consequência para este protocolo, e é boa:** o item 5 da definição acima — *"o
conjunto servido com boost `w` ≠ o conjunto com `w = 0`, no mesmo estado"* — **é
exatamente o `diffP2` que produção já emite**. A calibração **não precisa** que o
tratamento seja entregue. `shadow` é o instrumento de calibração ideal: mede a
oportunidade sem consumir amostra e sem alterar o estado que mede.

Então a taxa de oportunidade **já está sendo medida**: 11/350 = 3,1429% na janela, e é
contrafactual, não efeito.

⚠️ **O que `shadow` NÃO dá:** desfecho. Sem tratamento entregue não há efeito a estimar
— por construção, e não por falta de n. `active` é requisito do **estudo**, não da
calibração, e a ordem correta é calibrar em `shadow` e só então ativar.

### ✅ Discrepância de estado RESOLVIDA — 27/08, por observação

Duas fontes independentes concordando:

| fonte | diz |
|---|---|
| drop-in `p2s2-shadow.conf` | `NOX_P2_OUTCOME=shadow`, `NOX_P2_SHADOW_W=2.0` — **com** cabeçalho `[Service]`, logo válido |
| log da janela fechada | `modo: shadow` e `servido: controle` em **352 de 352**, `w=2` em todas |

**A transição para `active`, decidida em 24/08, nunca foi executada.** Não é falha
silenciosa: o drop-in está correto e declara `shadow` deliberadamente. O que havia era
uma **decisão registrada em memória como se fosse estado** — e "decidido" não é "no ar".

Isto **não bloqueia** a calibração; ao contrário, é a configuração que ela quer. Bloqueia
o **estudo**, e a ativação passa a ser passo explícito depois do no-go do item 5.

*(Registro anterior desta seção, mantido porque a dúvida era legítima:)*

⚠️ **Discrepância de estado a resolver antes de qualquer coisa.** A decisão de sair de
`shadow` para `active` foi tomada em **24/08** (registrada em
`project_paper2_shadow_exhausted_needs_active`), e em 27/08 o log diz `shadow` em 352 de
352. Ou a transição nunca aconteceu, ou foi revertida. **Isto tem de ser respondido por
estado observável — `NOX_P2_OUTCOME` no ambiente do processo servindo — antes de
declarar a janela do item 2.** Não pelo pressuposto de que a decisão foi executada:
"decidido" e "no ar" são fatos diferentes, e este projeto já pagou por confundi-los (o
drop-in de systemd sem `[Service]` que desligou uma flag em silêncio).

### ✅ Harness CONSTRUÍDA E RODADA — 27/08

`measurement/replay-oportunidade.mjs`. Resultado integral em
**`REPLAY-OPORTUNIDADE-2026-08-27.md`**; artefatos em `measurement/out/`.

**Fidelidade: 350 de 350 briefs da janela fechada** reproduzem a produção —
composição do controle, `churn`, `would_enter` e `would_leave` — com zero churn
inventado e zero perdido. O defeito do §4 de `DEVIATIONS-FOR-PAPER.md`
("oportunidade não corresponde ao pipeline") está **fechado**.

Três correções que esta seção do protocolo precisa receber, porque a rodada as
produziu:

1. **A âncora exigida abaixo é internamente inconsistente.** "44 grupos" é a
   figura **contaminada**, que vem junto com **posição 3**; descontaminada é
   `43 / 0`. Exigir `44 grupos` **e** exclusão de sondas pede um estado que
   nenhuma configuração produz. As duas colunas estão declaradas na harness e as
   duas reproduzem exatas.
2. **"serve-state limitado a `T_REF`" é insuficiente, e não por descuido de
   redação.** `brief_log.served_at` tem resolução de **segundo** e 46,9% dos
   briefs dividem o segundo com outro. Existem estados verdadeiros que nenhum
   corte temporal expressa. O corte tem de ser por **`brief_log.id`**
   (`AUTOINCREMENT` = ordem de inserção). Sob corte temporal estrito a contagem
   de desfecho sai **14 em vez de 12**.
3. **"sondas excluídas por `brief_id`" está certo para o estimando e errado para
   validar contra a produção** — a produção *viu* as 25 linhas de sonda. São dois
   serve-states diferentes para duas perguntas diferentes, e a harness aceita os
   dois por argumento.

### Obrigações da harness (as originais, mantidas para registro)

`replay-oportunidade.mjs`, com estas obrigações, todas herdadas de erro já cometido:

- corpus = **snapshot de epoch por caminho explícito**; serve-state = `brief_log` vivo
  limitado a `T_REF`. Sem default para nenhum dos dois;
- exercita `fetchRankedPool`, `fetchFreshCandidates`, `interleaveFresh` e `pickDedup`
  **reais**, importados — não reimplementados. Reimplementar é a classe
  "reconstrução modela regra que o código nunca aplica";
- **reproduz âncora publicada antes de variar qualquer coisa** (pool 108, 55/55 do
  estudo, 44 grupos, nunca-servidos 0, em `T_REF = 2026-08-26 20:35:00Z` com
  `e20260826T060003Z.db`);
- sondas excluídas por **`brief_id` enumerado**, nunca por corte de tempo;
- **controle positivo obrigatório:** `w = 100.000` tem de mover algo em algum estado. Se
  não move em nenhum, o canal não existe e o estudo morre aqui — o que é um resultado.

---

## Item 2 — Janela de calendário, declarada antes de olhar

- `T_início` e `T_fim` **declarados neste documento antes de a janela abrir**, em UTC, com
  o `sha256` do NDJSON no fechamento.
- Sondas excluídas por `brief_id` enumerado. **Sensibilidade publicada nos dois estados**
  (com e sem sondas), sempre — não só quando conveniente.
- ⚠️ **Nenhuma sonda via `/api/brief` durante a janela.** `/api/brief` não tem
  `?track=false`: sondar escreve `brief_log`, que define `last_served`, que ordena o pool.
  Em 26/08 duas sondas de *verificação* caíram 55 s depois do marco, dentro da janela
  medida. Verificação durante a janela usa **o log**, nunca o endpoint.

**A declarar quando a calibração for autorizada** *(deixado em branco de propósito —
preencher é ato de pré-registro, não de redação)*:

| | |
|---|---|
| `T_início` | *a declarar* |
| `T_fim` | *a declarar* |
| duração | *a declarar, em dias inteiros* |

---

## Item 3 — Unidade de reamostragem = dia ou epoch

Nunca par-de-gap. Os 38 pares do §2 vêm de 44 grupos num único instante, compartilham
grupos e repetem valores: tratá-los como independentes é **pseudorreplicação**, e foi sob
essa hipótese "generosa e provavelmente falsa" que saiu o bound de ~10,5%.

Bootstrap por **dia**. Se a série mostrar dependência intra-epoch, por **epoch**.

---

## Item 4 — `N = f(dados)` como script executável, commitado antes de rodar

É a **F5**. O script recebe a janela fechada e devolve `N`; commitado **antes** de a
janela abrir, e o `sha256` dele declarado aqui.

⚠️ **Horizonte fixo em calendário/blocos, nunca em contagem de oportunidades.** É a
**F3**: parar em "N oportunidades" é optional stopping disfarçado, porque a contagem de
oportunidades é pós-tratamento — o item 1 acima **prova** isso, já que a oportunidade
depende de `seenIds`, que depende do que foi servido.

---

## Item 5 — Regra de no-go explícita

O estudo **não começa** se, ao fim da janela:

1. ~~o controle positivo do item 1 não mover nada em nenhum estado (canal inexistente)~~
   → ✅ **RESPONDIDA 27/08: PASSA.** `w = 100.000` move 17 de 350 estados, e a resposta é
   monótona de `w = 0` (0 estados) até saturar em **`(4,0 ; 4,4]`** com 17 estados —
   grid de 23 doses; o "7,5" de um grid mais grosso era artefato de resolução. O canal
   existe. Esta condição **não** dispara;
2. a taxa de oportunidade for baixa o bastante para `N` estourar o horizonte de
   calendário viável;
3. a distribuição de gap intragrupo não for estacionária na janela — porque escala
   calibrada sobre quantidade não estacionária não transporta;
4. ~~o replay não reproduzir as âncoras publicadas~~ → ✅ **RESPONDIDA: reproduz.** As
   duas configurações de sonda reproduzem exatas, e o replay bate com a produção em
   **350 de 350** briefs. Restam abertas as condições **2** (taxa vs. horizonte) e **3**
   (estacionariedade do gap intragrupo).

⛔ **Proibido parar quando "houver oportunidades suficientes".** O horizonte é a janela.

---

## Item 6 — Carry-over de `last_served` através das fronteiras de epoch

O snapshot de epoch congela o **corpus**; `brief_log` vive no DB **vivo**. Logo a
coordenada **dominante** da ordenação nunca é congelada, e o tratamento em `T` altera a
estrutura de grupos em `T+1`. Interage com a **F1** (SUTVA/carry-over).

A tratar no protocolo, e nenhuma opção é gratuita: (a) washout entre epochs, com o custo
de amostra; (b) modelar a dependência explicitamente; (c) declarar o estimando como
efeito **na presença** de carry-over, o que muda o que o paper pode afirmar. **A escolha
é de desenho e precisa ser declarada antes, não escolhida depois de ver a série.**

---

## Item 7 — Gatilho de monitoramento para falha de saturação

Com braço único, uma falha de saturação é **indetectável** sem gatilho. Dispara e
interrompe se aparecer gap intragrupo **acima da magnitude escolhida**.

🔴 **A calibração deste gatilho está INVÁLIDA — e não pelo número, pela GRANDEZA.**

O texto original dizia: *"hoje o máximo observado é `0,031808734967844865` e a margem
contra `0,043` é apenas 1,35×"*. Medido em 27/08 com a harness do item 1:

1. aquele `0,0318` é a coluna **filtrada** (só pares em que um dos dois chunks é do
   estudo). Sem filtro, mesmo pool e instante, o máximo é **0,05272**. A harness
   reproduz **as duas** exatas — a filtrada é a quarta âncora publicada que ela recupera;
2. **e nenhuma das duas cota o mecanismo.** O maior limiar por estado é `w_min = 4,4`,
   que em S1 vale boost **0,0946** — **1,79×** o maior passo adjacente do pool inteiro.
   Boost maior que qualquer passo entre vizinhos e ainda insuficiente só pode significar
   que o designado atravessa **várias posições** até os 2 slots de cobertura. A grandeza
   é **distância acumulada**, não passo. **O gatilho pode ficar verde enquanto o canal
   satura.**

⚠️ E a hipótese que motivou este pré-requisito — "existem gaps maiores no sub-pool do
agente" — está **refutada**: em `T_REF` o sub-pool do agente é **vazio**. 265 (nox),
6.001 (cipher) e 3.011 (atlas) chunks de `sessions/<agente>/%` passam o piso de
importance e **zero** passam a janela de `freshMaxAgeDays = 7`. Logo
`interleaveFresh([], global) === global` e todo o canal é o sub-pool global.

### ✅ Item 7 REDESENHADO E NO AR — 27/08

Fonte em `measurement/`; implantado em `/root/.openclaw/scripts/p2/` (que carrega
`PROCEDENCIA.md` dizendo que é cópia, não fonte). Status em `/var/lib/nox-mem/p2/`,
lido pelo `morning-report.sh` às 06:30Z.

**(a) `gatilho-saturacao.sh` — diário, 05:41Z.** A operacionalização é uma
**identidade**, não um limiar arbitrário:

> saturado ⟺ `churn(w_servido) == churn(w_absurdo)`

Se a dose servida já produz tudo que qualquer dose produziria, a dose não está
identificada. Isso custa **duas** doses de replay, não 23: não é preciso localizar
`w_min`, só comparar as pontas. Reporta a **folga** `mexem(servido)/mexem(absurdo)`;
`≥ 0,9` é YELLOW, igualdade é RED, `mexem(absurdo) == 0` é RED (canal sem capacidade).

Primeira rodada real, dia UTC de 26/08 inteiro: 677 briefs, 672 estados,
`w=2` move 25 · `w=100.000` move 52 · folga **0,4808** → **GREEN**.

⚠️ **Rótulo obrigatório na saída (`semantica=`).** `mexem_servido` **não** é "quantas
oportunidades ocorreram na janela": o replay aplica a designação **atual** aos estados
de ontem. Numa janela que atravessa troca de regra — 26/08 atravessa a de 20:28Z — os
dois números divergem, e um seria lido como o outro.

**(b) `gatilho-composicao.mjs` — horário, :09.** `RED` no **primeiro** chunk elegível
para `agentFresh`, sem faixa amarela: a escala de dose de 27/08 pressupõe `agentFresh`
vazio, e um único candidato entrando já muda `interleaveFresh` de função-zero para
intercalação real. Os limiares vêm de `DIVERSITY_DEFAULTS` no `dist`, **não digitados** —
e o script confere as cláusulas do `WHERE` no fonte e **aborta** se mudarem, em vez de
vigiar o predicado velho.

**Quatro propriedades que os dois têm, e cada uma é dívida paga:**

| propriedade | erro que a originou |
|---|---|
| não sondam `/api/brief` — leem log e corpus | o endpoint **escreve** em `brief_log` o estado que mede (5 sondas, 25 linhas) |
| janela **fechada** nos dois extremos + `sha256` do recorte | uma janela aberta por cima fez um `11/310` envelhecer para 359 |
| chamam a harness canônica em vez de reimplementar | o controle positivo publicado media o instrumento, não o sistema |
| status **velho** conta YELLOW, ilegível conta RED, e o gatilho reporta a **própria morte** por sinal | silêncio não é sucesso: gatilho parado é indistinguível de gatilho sem achado |

**Testado por mutação, 6/6 mordidas:** corpus sintético com 1 chunk de sessão recente →
RED · `--w-servido 15` (que sabemos igual a 100.000) → RED SATURADO com folga 1,0 ·
janela vazia → YELLOW · cláusula do fonte alterada → aborta · status RED no arquivo →
report vira RED (exit 2) · status com 10 h → YELLOW, não GREEN.

⚠️ **O que fica declarado como aproximação:** `current.db` roda às 06:00Z, então um dia
UTC inteiro atravessa **dois** corpora e o replay usa um. Medido em 27/08: para os 11
eventos da janela conhecida, os snapshots de 26/08 e 27/08 dão resultado **idêntico** —
a escolha foi inerte. Inerte não é garantido, e a aproximação vai em cada linha do
NDJSON.

⚠️ **E o (a) se recusa a rodar em `active`:** ali a dose vem do braço resolvido no
`ASSIGNMENT.json`, não de `NOX_P2_SHADOW_W`. Vigiar com a dose errada é pior que não
vigiar — reportaria GREEN sobre outra grandeza. Sai YELLOW com o motivo, e isso é um
item a implementar **antes** da ativação.

### O desenho, para registro

- **(a)** gatilho de saturação sobre a dose servida vs. dose absurda, não sobre gap
  adjacente — a distribuição de `w_min` (mín 0,02 · mediana 1,7 · máx 4,4, espalhamento
  220×) é o que dá contexto ao veredito;
- **(b)** gatilho de composição do canal: o sub-pool do agente estar vazio é fato sobre
  um instante, não propriedade.

O gatilho lê o log, **não sonda o endpoint** (item 2).

---

## Item 8 — Procedência obrigatória em toda medição

Toda tabela do protocolo carrega, sob pena de ser inválida:

1. **`T_REF`** — o instante;
2. **caminho do snapshot de corpus** — `resolveCorpus` pega o *mais recente*, então
   omitir o caminho troca o corpus em silêncio;
3. **janela fechada** nos dois extremos, com `sha256` do arquivo;
4. **reprodução de âncora publicada** antes de variar qualquer coisa.

O item 4 não é zelo: em 27/08 uma reconstrução discordou dos números publicados **por
definição, não por deriva** (38/11/27 contra 67/15/52 no mesmo dado), e sem âncora eu
teria trocado o número certo pelo errado "consertando" o documento.

---

## Estado deste protocolo

| item | estado |
|---|---|
| 1 — oportunidade | ✅ **FECHADO 27/08** — replay reproduz a produção em 350/350; controle positivo **PASSA**; teto do canal = 17/350 = 4,86% |
| 2 — janela | mecanismo especificado; datas **a declarar** |
| 3 — reamostragem | especificado (dia, ou epoch se houver dependência) |
| 4 — `N = f(dados)` | mecanismo especificado; script a escrever e commitar antes |
| 5 — no-go | condições **1 e 4 respondidas** (não disparam); **2 e 3 abertas** |
| 6 — carry-over | **aberto por desenho** — 3 opções, escolha a declarar antes |
| 7 — gatilho | ✅ **redesenhado e NO AR** — (a) diário 05:41Z e (b) horário :09, status lido pelo morning report; 6/6 mutações mordem. Pendência: (a) recusa `active` até a dose vir do `ASSIGNMENT` |
| 8 — procedência | **especificado**, vale para todo o resto |

**Não desbloqueia nada ainda.** O que desbloqueia é o item 1 rodando com controle
positivo passando, e a escolha do item 6 declarada.

✅ **Primeira ação FEITA:** `NOX_P2_OUTCOME=shadow`, confirmado por drop-in **e** por
log. É a configuração que a calibração quer. A ativação vira passo explícito **depois**
do no-go do item 5, não antes.

~~**Próxima ação (27/08, depois do item 1):** medir a distribuição de gap intra-estrato no
sub-pool do agente~~ → ✅ **FEITA, e refutou a própria hipótese:** o sub-pool do agente é
**vazio** por idade, e a grandeza que governa é distância, não passo. Ver item 7 acima.

~~**Próxima ação:** implementar o item 7 redesenhado~~ → ✅ **FEITO**, os dois no ar.

**Próxima ação:** os itens que restam são **decisões**, não medições — e é onde eu paro:
o **item 2** (declarar `T_início`/`T_fim` antes de a janela abrir), o **item 6**
(carry-over: washout · modelar a dependência · estimando na presença de carry-over) e o
**item 4** (o script de `N = f(dados)`, que depende da escolha do 6). Nenhum deles é
meu para escolher sozinho.
