# Reempacotar o índice vec0 vale a pena? — medido

> **2026-08-28.** O Toto disse "vamos fazer" e isto é a **medição**, não o rebuild.
> Produção não foi tocada: tudo sobre cópia via `.backup` em `/var/tmp`, depois
> apagada.
>
> Harness: `measurement/bench-vec0-reempacotamento.mjs` · log
> `measurement/out/bench-vec0-2026-08-28.json`.

---

## 1. O que se sabia, e o que era só hipótese

O vec0 aloca a shadow table em **chunks fixos de 1024 vetores** (12.582.912 B
exatos = 1024 × 3072 × 4). No nox-mem, medido em conjunto com a sessão
`openclaw-vps-de`:

| | |
|---|---|
| chunks alocados | **103** |
| vetores válidos | **69.261** |
| slots alocados | 105.472 ⇒ **34% vazios** |
| chunks necessários | **68** |

⚠️ **A hipótese "34% de slots vazios ⇒ −34% de I/O por busca" era plausível e NÃO
medida.** Slot vazio tem bit zerado no `validity` e **não** custa cálculo de
distância; a pergunta aberta era se os bytes ainda são lidos. Nenhum de nós dois
quis afirmar ganho a partir de aritmética de tamanho.

## 2. O reempacotamento funciona, e a aritmética fechou ao chunk

`INSERT` sequencial numa `vec0` nova preenche cada chunk antes de abrir o próximo:

| | antes | depois |
|---|---|---|
| chunks | 103 | **68** |
| MB alocados | 1.236 | **816** |
| vetores | 69.261 | 69.261 |

Exatamente os 68 previstos. Custo: **19,5 s** para 69.261 vetores.

## 3. E o ganho de latência é real: **33,1%**

| braço | mediana | n | min | max |
|---|---|---|---|---|
| fragmentado (`vec_chunks`) | **668,2 ms** | 60 | 588,9 | 3.803,1 |
| reempacotado (`vec_packed`) | **446,8 ms** | 60 | 393,7 | 5.283,9 |

**−221 ms por busca semântica, 33,1%** — contra ~34% previstos pela aritmética de
tamanho. Isso **não** é cosmético, e contradiz a leitura a que nós dois havíamos
chegado antes de medir ("é só 1,7% de disco").

**Confundidores que o desenho fecha:**

1. as duas tabelas vivem no **mesmo arquivo** — mesma page cache, mesmo processo.
   Comparar dois arquivos mediria qual deles o SO cacheou;
2. A/B **intercalado**, com ordem **alternada por repetição**: a VPS é
   compartilhada, e deriva de carga afeta os dois braços em vez de premiar quem
   rodou no minuto calmo;
3. **aquecimento descartado** — o primeiro KNN custou 1.356 ms contra ~650 estável;
4. **mediana**, não média: os dois braços têm outlier de segundos (3,8 s e 5,3 s),
   que é pausa de scheduler, não sinal.

⚠️ Steal time deste host medido em **0–6%** no mesmo período, então o ganho não é
artefato de vCPU roubado (o host vizinho tem `st=71%`; este não).

## 4. As duas sondas que divergiram — e por que são benignas

10 de 12 sondas devolveram resposta **idêntica**. As 2 que não, eu fui medir antes
de reportar o ganho, porque *ganho que muda o resultado não é ganho*.

As duas divergências são **inteiramente dentro de blocos de empate exato**:
distância `0,000000` nos dois braços. Contando os vizinhos a distância zero por
sonda, a correspondência é exata:

| sonda | empatados em distância 0 | divergiu? |
|---|---|---|
| 2 | **130** | sim |
| 3 | **15** | sim |
| as outras 10 | 1 a 6 | não |

Só divergem as sondas cujo bloco de empate **excede o `LIMIT 10`**. Onde há 130
chunks a distância exatamente zero, *qualquer* 10 deles é uma resposta correta e o
desempate é a ordem de varredura. Logo o reempacotamento **não altera o resultado
da busca** em nenhum sentido semântico.

📌 **Achado colateral que interessa ao paper:** existe consulta com **130
duplicatas exatas** no corpus — o top-10 é arbitrário ali. Casa com os 29,2% de
texto duplicado já medidos, e reforça a manchete: o que o agente recebe é decidido
por capacidade e estrutura, não por relevância.

## 5. ✅ EXECUTADO em produção (2026-08-28 22:30–22:35 UTC)

O Toto autorizou (*"faz o rebuild"*). Envelope da D77 cumprido integralmente.

| | |
|---|---|
| chunks do índice | 103 → **66** |
| shadow alocada | 1.236 → **792 MB** |
| **arquivo do DB** | 1.637,8 → **1.189,8 MB** (**−448 MB**) |
| vetores | 69.261 → **67.187** (os 2.074 sem map descartados) |
| **latência medida em produção** | **409,3 ms** (n=6) ⇒ **−38,7%** sobre os 668,2 |
| duração | 42,6 s de repack + 13,6 s de `VACUUM` |

**O ganho ficou MAIOR que os 33,1% previstos** — 38,7% — porque o rebuild também
descartou os 2.074 vetores sem linha de map, que eram varridos pelo `MATCH` e só
então jogados fora pelo `JOIN vec_chunk_map`. Pagavam I/O e distância para nunca
poder retornar nada.

**Verificação, por estado observável:** `quick_check = ok` · índice = map = chunks =
**67.187** · discrepância **0** · `/api/health` devolve
`{"orphans": 0, "indexOnly": 0}` · zero órfãos map-side · zero tabelas residuais
`_reb` · busca real pelo endpoint devolve 5 resultados `semantic` · `ops_audit`
registra `rebuild-vec0-index | success | affected=67187` no `db_path` correto.

⚠️ **Duas coisas que só a execução ensinou.**

1. **`ALTER TABLE ... RENAME` numa tabela vec0 retorna sucesso e DESTRÓI o índice.**
   Renomeia só a entrada da virtual table; as shadow tables ficam com o nome antigo
   (`vec_x_chunks`, `vec_x_rowids`, …) e a tabela nova fica ilegível
   (`Error preparing rowid scan: no such table`). Descoberto em **cópia**, antes de
   produção. Por isso o caminho é duplo-copy: nova → drop original → recria com o
   nome original → copia de volta.
2. **`VACUUM` É necessário DEPOIS, e isto não contradiz o §1.** O `DROP` liberou
   317.209 páginas e o SQLite não as devolve ao SO: o arquivo **cresceu** para
   2.432 MB. `VACUUM` não recupera o vazio *dentro* do blob (só o repack faz isso) —
   mas recupera as páginas livres, e sem ele o ganho de espaço não se realiza e os
   backups diários passariam a copiar 2,4 GB.

**A evidência dos 2.074 está preservada** no snapshot pré-op de 1.635 MB
(`/var/backups/nox-mem/pre-op/rebuild-vec0-index-main-20260827223038-*.db`),
retention 7 d. Origem deles segue **não identificada** — o descarte não a investigou.

Script: `measurement/rebuild-vec0-index.mjs`, que exige `--executar` para mutar e
`--op-audit` para tocar produção.

## 6. Recomendação (histórico, antes da execução)

O rebuild passa a ter **dois** argumentos medidos, não zero:

| argumento | tamanho | estado |
|---|---|---|
| latência de busca semântica | **−33,1% (−221 ms)** | **medido** |
| espaço | 420 MB na shadow · 1,64 GB somando o vivo e 3 backups | medido |
| limpeza dos 2.074 vetores fora do map | ~25 MB, mas alcança classe que **nenhuma** ferramenta atual vê | medido |

⚠️ **E o risco não mudou:** o vec0 é a **única** cópia dos embeddings de chunk
neste sistema — varri por tipo `BLOB` e só existem as shadow tables e
`reflect_cache.query_embedding`, que é cache de *query*. O OpenClaw tem
`memory_index_chunks.embedding` como rede de reconstrução; **o nox-mem não tem**.
Um rebuild que dê errado custa 69.261 embeddings, que só voltam pagando Gemini.

**Logo:** o rebuild é **defensável agora**, com snapshot atômico via `withOpAudit()`
(regra 6) e conferência pós-op por `/api/health.vectorCoverage`. Mas segue sendo
decisão do Toto, e a execução não foi feita.
