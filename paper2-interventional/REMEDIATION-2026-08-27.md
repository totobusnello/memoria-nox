# Remediação de 2026-08-27 — as três medições que a 3ª rodada adversarial obrigou a refazer

O Codex (gpt-5.6-sol, saída e recibo em `receipts/`) apontou três defeitos de
instrumento na `AMENDMENT-DRAFT-band-collapse-2026-08-26.md`. Verifiquei os três no
código: **procedem, e são meus.** Este documento registra o que a remediação mediu.

Duas conclusões incômodas antes do detalhe:

1. **Duas das "correções" que eu ia aplicar ao rascunho estavam erradas.** O rascunho
   estava certo e minha correção, não. Aplicá-las teria degradado o documento.
2. **A remediação encontrou um defeito que nenhuma das quatro vozes achou:** eram
   **cinco** sondas, não três — e duas delas foram disparadas *55 segundos depois* de a
   regra nova entrar no ar, porque foram elas que eu usei para verificar que ela
   entrara.

---

## 1. A "descontaminação" era um rollback temporal de 148×

`measurement/descontamina.py:9`:

```python
cond = "AND served_at < '2026-08-26 19:58:00'" if excluir_sondas else ""
```

Isto não exclui as sondas. Exclui **tudo** o que foi servido depois das 19:58 —
**3.735 linhas de `brief_log`** para remover 25 de sonda. O README de `measurement/`
afirmava que o script "reconstrói o estado excluindo as 15 linhas das minhas sondas";
**era falso** em duas contas: no mecanismo (corte de tempo, não exclusão de sonda) e
no número (25 linhas, não 15).

### As sondas são exatamente identificáveis — e são cinco

`brief_log` tem `brief_id` e `agent`. Todo brief orgânico tem nome de agent
(`nox`/`atlas`/`boris`/`cipher`/`lex`/`forge`) e **10** linhas; as sondas via `curl`
não passaram agent e trouxeram **5**. Varrendo por assinatura desde 25/08 — 1.603
briefs de 10 linhas, e exatamente 5 fora do padrão:

| `brief_id` | linhas | quando |
|---|---|---|
| `473f85e8-43ae-4883-baa2-2d76407af941` | 5 | 2026-08-26 19:58:17 |
| `c48e8353-cd95-4bd5-997b-dc921e2a0cac` | 5 | 2026-08-26 19:58:17 |
| `6ff2d9c4-79f2-4526-8eb5-c42d60bbeea6` | 5 | 2026-08-26 19:58:18 |
| `90a105f5-ef33-4135-8e54-b4e978bbb1ee` | 5 | **2026-08-26 20:28:55** |
| `66977ec1-2809-44df-91b8-c158ce0e68e8` | 5 | **2026-08-26 20:28:56** |

As duas últimas caem **dentro** da janela pós-regra (a regra entrou às 20:28:00Z).
São as sondas de *verificação* — o ato de confirmar que o mecanismo subiu escreveu no
primeiro minuto da série cuja taxa é o número do §4.1-bis.

⚠️ `agent IS NULL` **não** serve como marcador de sonda: são 15.569 linhas em 5.889
briefs desde 2026-06-04, resíduo histórico de antes do campo. O discriminador tem de
ser o conjunto enumerado de `brief_id`.

### O que a descontaminação correta muda

Corpus = snapshot de epoch `e20260826T060003Z.db` (o que produção serve),
serve-state = `brief_log` vivo limitado a `T_REF = 2026-08-26 20:35:00Z`,
`now` do `calculateSalience` = o mesmo `T_REF`. Script: `measurement/gap-defs.mjs`.

| métrica | observado | descontaminado | muda? |
|---|---|---|---|
| `pool` | 108 | 108 | — |
| `grupos_last_served` | 44 | 43 | sim |
| `posicao_primeiro_estudo` | **3** | **0** | sim |
| pares adjacentes no grupo | 38 | 38 | — |
| `gaps_exatamente_zero` | 11 | 11 | — |
| gaps positivos | 27 | 27 | — |
| `gap_maximo` | 0,031808734967844865 | 0,031808734967844865 | — |

**Logo:** a posição do primeiro chunk do estudo era contaminada (3 → 0), e **nenhuma
estatística de gap era.** Minhas duas "correções" pendentes — trocar `16/27` por
`19/27` e `38 pares / 11 zeros` por `40 / 13` — **estavam erradas**; vinham do
rollback, não das sondas. Os números publicados estão corretos.

---

## 2. A harness estava validada contra âncora nenhuma — agora está

O descasamento entre a minha primeira tentativa de remedição e os números publicados
não era deriva: era **definição**. Três definições plausíveis de "par", no mesmo
instante e corpus:

| definição | pares | zeros | positivos | `gap_max` |
|---|---|---|---|---|
| adjacentes na ordenação global | 67 | 15 | 52 | 0,05680873 |
| **adjacentes DENTRO do grupo de empate** | **38** | **11** | **27** | **0,031808734967844865** |
| todos os pares dentro do grupo | 60 | 12 | 48 | 0,05553096 |

A segunda reproduz o `DELTA-CUT-MEASUREMENT-2026-08-26.json` na **9ª decimal**
(`gap_maximo = 0.031808735`) e é a semanticamente certa: `salience` só decide
**dentro** de empate de `last_served`. Seis âncoras publicadas reproduzem exatas —
`pool = 108`, `estudo_no_pool = 55`, `grupos_last_served = 44`,
`nunca_servidos = 0`, `posicao_primeiro_estudo = 3`, `tamanhos_de_grupo` com chaves
{1,2,3,4}.

Antes disso eu havia rodado uma remedição contra o **DB vivo como corpus** e obtido
27 pares, 0 zeros, máximo 0,0463 — e quase reportei isso como correção. Produção
serve o corpus do **snapshot de epoch**, não do vivo. É o mesmo defeito da primeira
harness offline desta linha de trabalho, repetido: a harness precisa exercitar o
caminho de produção, e a prova de que exercita é **reproduzir âncora publicada antes
de variar qualquer coisa**.

### Saturação: confirmada e agora recomputável

Recomputando as contagens de vitória a partir dos 27 gaps depositados
(`limiar = w · Δ_cut · severidade`, `Δ_cut = 0,043`):

| `w` | limiar S1 | vence S1 | limiar S2 | vence S2 |
|---|---|---|---|---|
| 2,0 | 0,021500 | **16 / 27** | 0,043000 | 27 / 27 |
| 4,0 | 0,043000 | 27 / 27 | 0,086000 | 27 / 27 |
| 7,5 | 0,080625 | 27 / 27 | 0,161250 | 27 / 27 |
| 100.000 | 1075 | 27 / 27 | 2150 | 27 / 27 |

O menor `w` que vence todos os 27 em S1 é **2,9590**. Acima dele nenhuma dose muda
nada. A banda registrada `{2,0 · 4,0 · 7,5}` mapeia em `{16, 27, 27}`: as duas doses
superiores são **indistinguíveis por construção do próprio dado**, não por falta de n.

⚠️ Um detalhe que o rascunho apresenta como achado e não é: nenhum dos 38 pares tem
gap negativo. Isso é **verdadeiro por construção** — a ordenação é `salience DESC`
dentro do empate, então a diferença entre adjacentes é ≥ 0 necessariamente. Não é
evidência de nada.

---

## 3. `julianday('now')`: a população elegível dependia do instante da execução

`descontamina.py:7`, `autoextincao.py:10` e `mede-delta.mjs:16`:

```sql
AND julianday('now') - julianday(COALESCE(source_date, created_at)) <= 30
```

Quem rodar amanhã obtém conjunto elegível diferente. Não é hipótese — medido, com
`T_REF` fixado nos dois instantes e sondas excluídas nos dois:

| `T_REF` | grupos | qualificáveis | menor posição qualificável | puros | mistos |
|---|---|---|---|---|---|
| 2026-08-26 22:00Z | 45 | 5 | 24 | 15 | 17 |
| 2026-08-27 09:00Z | 41 | 7 | 44 | 14 | 13 |

Onze horas movem `menor_pos` de 24 para 44. **Efeito só das sondas em 27/08 09:00Z:
nenhum** — doze horas de tráfego orgânico lavaram a contaminação inteira.

Consequência para o §2 do rascunho: a tabela ilustrativa não descreve propriedade do
desenho, e sim **observação num instante**. Sem o instante declarado ela envelhece
para falsa, e o instante tem de vir com **três** coisas, não uma: `T_REF`, o arquivo
de snapshot do corpus, e o estado do `brief_log`.

⚠️ Achado colateral: produção resolve o corpus pelo snapshot **mais recente**
(`resolveCorpus` → `epochsDir()`). Hoje isso é `e20260827T060001Z.db`, não o
`e20260826T060003Z.db` que o JSON declara. Um terceiro que rodar "o mesmo script"
amanhã usa **outro corpus** sem receber aviso nenhum. O caminho do snapshot é
parâmetro obrigatório, não default.

---

## 4. A janela aberta: `n = 310` já era 359 quando fui conferir

`pos-regra.py:9` — `depois = [r for r in rows if r["ts"] >= REGRA]`, sem teto. O
`11/310` do rascunho é aberto por cima; o arquivo cresceu para 359 linhas pós-regra
até 2026-08-27T09:07:06Z.

Janela **fechada e declarada**: `[2026-08-26T20:28:00Z , 2026-08-27T09:00:00Z)`,
`sha256` do NDJSON `ca7ff52a7242bb031e5661fcab9d37a130a1f3b8331826175abf6ff0b382310a`,
3.542 linhas, 1.571.982 bytes. Sondas excluídas (2 decisões sem `agent` na janela;
o NDJSON **não** tem `brief_id`, então o discriminador ali é `agent` ausente).

| segmento | churn | Wilson 95% |
|---|---|---|
| regra nova, janela fechada | **11 / 350 = 3,1429%** | [1,76 ; 5,54] |
| regra velha, pós-gate, tudo | 132 / 2226 = 5,9299% | [5,02 ; 6,99] |

A soma das 13 horas fecha em 11/350, idêntica ao bloco — conferido no script.

### A comparação agregada fabrica significância a partir da tendência

A regra velha **não é estacionária**:

| dia | churn | taxa | Wilson 95% |
|---|---|---|---|
| 2026-08-23 | 42 / 308 | 13,6364% | [10,25 ; 17,92] |
| 2026-08-24 | 49 / 672 | 7,2917% | [5,56 ; 9,51] |
| 2026-08-25 | 21 / 672 | 3,1250% | [2,05 ; 4,73] |
| 2026-08-26 | 20 / 574 | 3,4843% | [2,27 ; 5,32] |

23 e 24/08 concentram **69% dos eventos em 44% do n**. Daí:

| comparação | diferença | Newcombe IC95 | Fisher exato |
|---|---|---|---|
| nova vs pós-gate **agregado** | −2,7871 pp | [−4,53 ; −0,22] | **p = 0,0326** |
| nova vs **último dia** da velha | −0,3415 pp | [−2,64 ; +2,35] | p = 0,8523 |
| nova (3,1429%) vs segmento **plano** 25+26/08 (3,2905%) | −0,1476 pp | — | — |

A "redução significativa" existe **só** contra o agregado, e vem inteira de incluir
os dois primeiros dias de uma série declinante. Contra o segmento estacionário, as
taxas são indistinguíveis.

**Portanto as duas leituras anteriores estavam erradas em direções opostas:** a minha
("não move", com `8/268` contra `20/560`) por comparar com um segmento adjacente
escolhido a dedo e subpotente; e a agregada por confundir tendência com efeito.
Nenhuma das duas identifica nada. Enunciado defensável, e nada além dele:

> Na janela fechada `[2026-08-26T20:28:00Z , 2026-08-27T09:00:00Z)`, sob a regra
> nova, observaram-se 11 ativações em 350 decisões (3,1429%; Wilson [1,76; 5,54]).
> No último dia da regra anterior, 20 em 574 (3,4843%). A comparação não é
> randomizada, os segmentos são temporalmente confundidos, a série anterior é
> declinante e não estacionária, e o n é insuficiente: não se estabelece aumento,
> redução nem equivalência, e nada aqui identifica o gargalo. A comparação contra a
> base agregada pós-gate (`p = 0,0326`) **não deve ser usada** — mede composição de
> dias, não efeito.

Números do rascunho que caem: `8/268`, `20/560`, `11/310`, `2.212`, `2,9851%`,
`3,5714%` e a diferença `−0,023 pp` com `z = −0,018`. Substituídos pelos acima.

---

## Scripts

Os originais ficam versionados como registro do erro. Os novos são determinísticos —
`T_REF` e caminho de snapshot são **parâmetros obrigatórios**, sem default:

| novo | substitui | o que corrige |
|---|---|---|
| `measurement/gap-defs.mjs` | `mede-delta.mjs` | corpus = snapshot explícito; `T_REF` no `calculateSalience`, na elegibilidade e no serve-state; sondas por `brief_id`; as 3 definições de par lado a lado |
| `measurement/remedia-descontamina.py` | `descontamina.py` | exclusão por `brief_id` em vez de corte temporal; mostra as 3.735 linhas que o corte removia |
| `measurement/asof-sonda-vs-tempo.py` | — | 2×2 que separa efeito de sonda de efeito de tempo |
| `measurement/remedia-serie.py` | `pos-regra.py` | janela fechada; `sha256` + bytes + linhas; soma das horas conferida contra o total |
| `measurement/tendencia.py` | `serie.py` | série diária com Wilson, sondas excluídas, para expor a não estacionariedade |

## O que esta remediação NÃO resolve

Continua valendo o que o Codex disse e a medição não toca: nada aqui faz **replay do
pipeline completo** (`interleaveFresh`, `pickDedup`, `pinned`, near-dup, corte do
`LIMIT 400`), logo "posição no pool" segue sendo **aproximação** de oportunidade, não
oportunidade. E nada aqui é randomizado: as comparações são antes/depois. O replay é
o item 1 do protocolo prospectivo, e a identificação causal só vem do sorteio.
