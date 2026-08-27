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

⚠️ **Discrepância de estado a resolver antes de qualquer coisa.** A decisão de sair de
`shadow` para `active` foi tomada em **24/08** (registrada em
`project_paper2_shadow_exhausted_needs_active`), e em 27/08 o log diz `shadow` em 352 de
352. Ou a transição nunca aconteceu, ou foi revertida. **Isto tem de ser respondido por
estado observável — `NOX_P2_OUTCOME` no ambiente do processo servindo — antes de
declarar a janela do item 2.** Não pelo pressuposto de que a decisão foi executada:
"decidido" e "no ar" são fatos diferentes, e este projeto já pagou por confundi-los (o
drop-in de systemd sem `[Service]` que desligou uma flag em silêncio).

### Harness (a construir DEPOIS de congelar este documento)

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

1. o controle positivo do item 1 não mover nada em nenhum estado (canal inexistente);
2. a taxa de oportunidade for baixa o bastante para `N` estourar o horizonte de
   calendário viável;
3. a distribuição de gap intragrupo não for estacionária na janela — porque escala
   calibrada sobre quantidade não estacionária não transporta;
4. o replay não reproduzir as âncoras publicadas.

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
interrompe se aparecer gap intragrupo **acima da magnitude escolhida** — hoje o máximo
observado é `0,031808734967844865` e a margem contra `0,043` é apenas **1,35×**.

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
| 1 — oportunidade | **especificado** aqui; e o dual-compute **já roda** em `shadow`, logo a taxa já é medida (3,1429%) — resta o replay para as condições 1–4 |
| 2 — janela | mecanismo especificado; datas **a declarar** |
| 3 — reamostragem | especificado (dia, ou epoch se houver dependência) |
| 4 — `N = f(dados)` | mecanismo especificado; script a escrever e commitar antes |
| 5 — no-go | **especificado**, 4 condições |
| 6 — carry-over | **aberto por desenho** — 3 opções, escolha a declarar antes |
| 7 — gatilho | especificado; a implementar |
| 8 — procedência | **especificado**, vale para todo o resto |

**Não desbloqueia nada ainda.** O que desbloqueia é o item 1 rodando com controle
positivo passando, e a escolha do item 6 declarada.

⚠️ **Primeira ação, antes de tudo:** conferir `NOX_P2_OUTCOME` por estado observável no
processo servindo. A decisão de ir para `active` é de 24/08 e o log de 27/08 diz `shadow`
em 352 de 352 — e o protocolo depende de saber qual dos dois é verdade, porque `shadow`
é o que a calibração quer e `active` é o que o estudo exige.
