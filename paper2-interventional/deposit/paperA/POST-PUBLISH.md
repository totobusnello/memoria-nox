# Depois de publicado — o que este pacote passou a ser

**O registro está publicado.** DOI `10.5281/zenodo.22181415`, concept DOI
`10.5281/zenodo.22181414`, publicado em **2026-08-30T21:39:24Z**, 13 arquivos.
Verificado por duas vias independentes em 2026-09-07: a API autenticada devolve
`is_published: True` / `is_draft: False`; a API pública de *records* responde 200, e ela
**só serve registro publicado** — o 200 é prova por si.

⇒ **Os arquivos são imutáveis.** Nada que se edite nesta árvore altera um byte do que um
leitor baixa daquele DOI.

## O MANIFEST mudou de função, e isso muda a regra

Antes de publicar, `MANIFEST.json` era **plano de montagem**: divergência contra o disco
significava "o pacote está desatualizado, remonte".

Publicado, ele é **a única prova local do que foi efetivamente depositado** — e é ele
mesmo item publicado (`md5:6b30ceafbd66332a933c18762cacf148`, 24.483 B).

> 🔴 **Nunca recompute um item deste MANIFEST.** Recomputar apaga a prova e deixa a cópia
> local descrevendo um pacote que não existe. O gate do `deposit.sh` passaria a mentir nas
> duas direções: verde sobre bytes que não foram publicados, e sem nenhum sinal de que os
> publicados eram outros.

A mensagem de falha do gate foi corrigida em 2026-09-07 justamente por isso: ela dizia
`"remonte"`, que é a ação danosa.

**Estado em 2026-09-07: 0 de 121 itens divergem.** A árvore ainda *é* o depósito, item por
item, e essa propriedade tem valor — vale mais que qualquer anotação que se possa colar num
dos arquivos.

## Defeito conhecido no pacote publicado

`measurement/dose2.mjs` (1.827 B, `sha256:f47a2daa…`, dentro de `scripts.zip`) está no
depósito como **registro de erro**, e nada no arquivo diz isso.

- **O que ele produz:** `churn` 0 em `w ∈ {2,0 · 4,0 · 7,5}`, com 19 boosts emitidos.
- **O que o pipeline real produz:** **11 / 15 / 17** estados de 350, monótono, com
  saturação em `(4,0 ; 4,4]`.
- **Por quê:** "caminho de produção" ali era o corpus certo com a ordenação
  **reimplementada** — não passa por `interleaveFresh` nem por `pickDedup`. Controle
  positivo sobre pipeline reconstruído não prova nada sobre o pipeline.

⚠️ **O agravante, e é o que distingue este caso de "caveat faltando":** o cabeçalho do
arquivo publicado **afirma** o que foi refutado — *"agora no caminho que prod REALMENTE
usa"* — e as duas linhas seguintes narram um defeito de harness já consertado. O leitor não
encontra um script silencioso; encontra um script que **declara ter aprendido a lição**.

**A ressalva existe e não viajou.** `measurement/README.md:75` marca
`~~dose2.mjs~~` com 🔴 **REFUTADO 27/08** e o número certo — mas o README **não está** no
MANIFEST (zero itens com "README" entre os 121), e os três documentos que citam o script
(`MEASUREMENT-delta-cut`, `REPLAY-OPORTUNIDADE-2026-08-27`, `AMENDMENT-DRAFT`) também estão
ausentes. É a classe do dia: **o artefato viaja, a ressalva fica.**

### O que o defeito NÃO contamina

Nenhum número do paper. `MANUSCRIPT.md:1685` e `DEVIATIONS-FOR-PAPER.md:20` trazem
**11 / 15 / 17**; zero ocorrências do número falso nos textos vivos. O risco é para
**terceiro que reexecute** o script achando-o instrumento.

## As duas vias que alcançam o leitor, e o que cada uma custa

No Zenodo, metadados de registro publicado são editáveis; arquivos não.

| via | alcança quem já tem o DOI | custo | reversível |
|---|---|---|---|
| editar a **description** do registro (o link `draft` existe no registro publicado) | sim, mesmo DOI | nenhum DOI novo | sim — reedita |
| **nova versão** com o arquivo anotado | sim, via concept DOI | **DOI novo, permanente** | não |

Nenhuma das duas fecha o buraco residual: quem já baixou o `scripts.zip` e o lê offline.
Nova versão também não.

**Decisão pendente do Toto.** Nada publicado se move sem ele.

## Cabeçalho preparado, para a nova versão se houver uma

Não aplicado — aplicá-lo hoje quebraria o 121/121 sem alcançar nenhum leitor. Fica aqui
para pegar carona, com custo marginal zero, se um dia houver nova versão por outro motivo.
Ele **substitui** as quatro linhas originais em vez de se anexar acima delas, e as
contradiz nominalmente:

```js
// ⛔ REFUTADO 2026-08-27 — REGISTRO DO ERRO, NÃO INSTRUMENTO.
//
// As quatro linhas abaixo eram o cabeçalho original e as três primeiras são
// FALSAS. Ficam citadas porque a alegação errada faz parte do registro:
//
//   > Dual-compute OFFLINE, agora no caminho que prod REALMENTE usa:
//   > corpus = snapshot de epoch (P2S1 active), serve-state = DB vivo.
//   > A primeira versao usou o vivo como os dois e o controle positivo (w=100000)
//   > deu churn 0 — foi o harness, nao o mecanismo.
//
// 1. "no caminho que prod REALMENTE usa" é falso. Os DBs estão certos, a
//    ORDENAÇÃO não: este script a reimplementa e não passa por `interleaveFresh`
//    nem por `pickDedup`. Corpus certo com pipeline reconstruído não é o caminho
//    de produção.
// 2. "foi o harness, nao o mecanismo" descreve um defeito real já consertado — e
//    por isso induz o leitor a concluir que ESTA versão está sã. Não está: trocou
//    um defeito de harness por outro, e o cabeçalho declara ter aprendido a lição
//    que não aprendeu.
// 3. O número: aqui dá `churn` 0 em w ∈ {2,0 · 4,0 · 7,5}. O pipeline real dá
//    11 / 15 / 17 estados de 350, monótono, saturando em (4,0 ; 4,4].
//
// Números vigentes: MANUSCRIPT.md §5.4, DEVIATIONS-FOR-PAPER.md §1.
// Refutação: REPLAY-OPORTUNIDADE-2026-08-27.md.
//
// ⚠️ Lê `epochs/current.db` — symlink reapontado às 06:01, retenção de 3 dias — e
// não grava procedência alguma. Qualquer saída sua é irrastreável por construção.
```

## Confirmação externa que veio de graça

`artefatos.zip` publicado tem **184.682 B** — exatamente o valor de `envio.bytes` que foi
**revertido** em 2026-09-07 depois de ter sido recomputado como soma-dos-membros
(3.535.811 B, 19× maior). O depósito publicado confirma, por fora, que aquele campo é o
**tamanho do ZIP comprimido**. A reversão estava certa, e o `bytes_nota` descreve o que o
número é.
