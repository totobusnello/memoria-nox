# Paper A v1.1: rascunho no Zenodo (NÃO publicado)

| campo | valor |
|---|---|
| rascunho | `23163119`, em `.draft-id-v1.1` (gitignored) |
| DOI reservado | `10.5281/zenodo.23163119` (só é registrado no DataCite quando alguém pressiona Publish) |
| concept DOI | `10.5281/zenodo.22181414` (versão 2 desse conceito; a v1.0 `22181415` segue `is_latest` até o publish) |
| URL do rascunho | https://zenodo.org/uploads/23163119 |
| criado em | 2026-10-05, via `POST /api/records/22181415/versions` (InvenioRDM) |
| scripts | `build-package.py` (monta os zips, o manifesto e roda o gate de privacidade), `deposit-v1.1.py` (metadata, files-import, upload e readback; não tem chamada de publish), `build/build-pdf.sh` (gera o PDF) |

## Arquivos no rascunho (18), md5 conferido no readback

| key | bytes | md5 | origem |
|---|---:|---|---|
| `MANUSCRIPT-v1.1.pdf` | 285.730 | `039f86d91ca25dccbb9b8037faf5b776` | novo |
| `MANUSCRIPT-v1.1.md` | 200.458 | `b31249215634fe61672097287025f7f2` | novo |
| `MANIFEST-v1.1.json` | 18.507 | `c462ff5cd8ee548a512e03b010297778` | novo |
| `artefatos-v1.1.zip` | 232.473 | `64044b6b0ef0a404e96ad23083c59bd9` | novo, 40 membros |
| `scripts-v1.1.zip` | 109.433 | `8c1c6f0badd7a83e65e36b9b198937ac` | novo, 27 membros |
| `MANUSCRIPT.md` | 126.564 | `a08076709e14b13ecf148c53ffb8f863` | v1.0, files-import |
| `MANIFEST.json` | 24.483 | `6b30ceafbd66332a933c18762cacf148` | v1.0, files-import |
| `claims_check.py` | 117.840 | `76a75af212fb0e9fbcd00b44e8cbc9fe` | v1.0, files-import |
| `DEVIATIONS-FOR-PAPER.md` | 18.933 | `24c64c3c6cf7998db30a91090b2a45ea` | v1.0, files-import |
| `SERVING-CODE-MANIFEST.md` | 6.297 | `b1ff58d7682893d5462f4aa53c5e2a2b` | v1.0, files-import |
| `PROSPECTIVE-ESTIMAND-2026-08-30.md` | 22.376 | `9fe7b06db36bf618ac554b5ab79c4fae` | v1.0, files-import |
| `DESIGN-REVISION-2026-08-30.md` | 14.606 | `9cfc019892bfd34fb4e96c2068936618` | v1.0, files-import |
| `serving-brief-diversity.ts` | 8.712 | `b9762fd24a60d5ed1e34cf45736f3b17` | v1.0, files-import |
| `serving-salience.ts` | 12.553 | `b908155b295e59ba1cb9611bac290525` | v1.0, files-import |
| `serving-search.ts` | 29.622 | `13f58eab59d529bde3887d0338d9e48e` | v1.0, files-import |
| `fig1-capacidade.svg` | 4.988 | `35030f12226156addc578ce9d772950a` | v1.0, files-import |
| `artefatos.zip` | 184.682 | `003960b8be86376958f5fda12767228f` | v1.0, files-import |
| `scripts.zip` | 149.766 | `2f60d64c27ebc5360436ae9d4b1371e9` | v1.0, files-import |

Os 13 da v1.0 foram copiados **no servidor** (`files-import`), não reenviados do disco, e o md5
de cada um bate com o do registro publicado 22181415. Os 5 novos batem com o disco, e cada
membro dos dois zips novos bate (sha256) com `MANIFEST-v1.1.json`.

## Readback campo a campo (forma InvenioRDM + legada): 22 de 22 ok

`is_draft` True · `is_published` False · DOI `10.5281/zenodo.23163119` · concept DOI
`10.5281/zenodo.22181414` · `versions.index` 2 · title = linha 1 do manuscrito · version `1.1` ·
publication_date `2026-10-05` · resource_type `publication-preprint` · publisher `Zenodo` ·
rights `cc-by-4.0` · languages `eng` · subjects iguais aos da v1.0 · related_identifiers iguais
aos da v1.0 · creator `Busnello, Luiz Antonio`, ORCID `0009-0007-5911-8141`, `Independent
Researcher` · description igual byte a byte a `description-v1.1.html` (menos o `\n` final),
começando pela tradução inglesa da description da v1.0 (`description-v1.0-en.html`), sem o
português, e trazendo o bloco "What changed in v1.1" ·
a forma legada vê o mesmo registro.

Para refazer o readback sem mexer em nada: `python3 deposit-v1.1.py` (é idempotente; não reenvia
o que já bate).

## O que o pacote é

- **Manuscrito:** `_sprint-2026-10-04/A-v1.1-rc8.md` com **uma** substituição, no Apêndice D: o
  `[TODO at deposit: …]` virou `Its version DOI is 10.5281/zenodo.23163119, reserved before
  deposit.` O rc8 não foi alterado; o manifesto guarda o sha256 dos dois.
- **PDF:** pandoc 3.9 + xelatex (2 passadas), mesmo preâmbulo do Paper 1 (`paper/preamble.tex`)
  mais 25 glifos mapeados para símbolos matemáticos; **0 "Missing character"** no log. 47
  páginas, Letter. O bloco de título (autor, ORCID, versão, DOI) vem de metadata do pandoc e
  não está no `.md`.
- **Redação:** em 7 arquivos empacotados um caminho local virou marcador (`<HOME>/`,
  `<SCRATCH>/`, `<TMP>`); o manifesto lista quais e guarda o sha256 do original. Gate final
  sobre todo byte empacotado (zips, soltos, texto e bytes do PDF, manifesto): **0** host, IP
  não-loopback ou caminho pessoal. Controle positivo do gate conferido (`/Users/…`, `~/`,
  `srv…`, IP Tailscale e `*.local` são pegos; `127.0.0.1`, `/root/` e `/var/lib/` passam, como
  na v1.0).
- **Fora do pacote** (registrado em `MANIFEST-v1.1.json` → `excluidos`): o `claims_check.py`
  atual, os `.db` de corpus, o log de serving bruto, artefatos não citados e os do Paper B.

## O que você precisa conferir antes de pressionar Publish

1. **Abrir o rascunho** e ver a prévia: description renderizada (o texto da v1.0 traduzido para inglês,
   com as duas erratas, + o bloco v1.1), ORCID no autor, 18 arquivos.
2. **Idioma:** o registro passa de `por` para `eng`. Resolvido em 2026-10-05: a description
   inteira está em inglês; o original em português segue no registro da v1.0.
3. **Bloco de status do manuscrito (linha 10):** resolvido em 2026-10-05 (ver a rodada no fim
   deste arquivo). O que segue continua aberto: o mesmo valia, em grau menor, para o F-5 (*"stays open: no new version has been deposited"*) e
   para o item de Open items que ainda espera o DOI: são histórico, e o Apêndice D já está
   preenchido.
4. **A description herdada** fala de "19 guardas", "58 artefatos" e "53 scripts": isso descreve
   os arquivos da v1.0, que seguem no registro. O bloco novo diz quais frases da v1.0 foram
   superadas e que o `claims_check.py` do pacote verifica o texto da v1.0, não o da v1.1.
5. **Arquivos não versionados:** boa parte do que entrou nos zips está untracked no git
   (`out/*2026-10-05*.json`, scripts `sprint-*`, `_sprint-2026-10-04/…`). O
   `related_identifiers` aponta `issupplementedby` para a árvore do GitHub, que hoje não os tem.
   Commitar antes ou logo depois do publish.
6. **Comando (não rodado):**
   `curl -X POST -H "Authorization: Bearer $ZENODO_TOKEN" https://zenodo.org/api/records/23163119/draft/actions/publish`.
   Descartar o rascunho: `curl -X DELETE … /api/records/23163119/draft` (o DOI reservado não
   chega a ser registrado).

## Achado lateral: o MANIFEST local da v1.0 não é mais o publicado

`deposit/paperA/MANIFEST.json` no disco tem md5 `b139a8ff…` e 22.932 B; o publicado tem md5
`6b30ceaf…` e 24.483 B. O local diz 121 itens e `MANUSCRIPT.md` com 126.563 B; o publicado diz
120 e 126.564 B. O arquivo foi alterado depois do publish (commits #462 e #465), contra a regra
do `POST-PUBLISH.md` de nunca recomputá-lo. Não mexi nele. O publicado entrou intacto na v1.1
por files-import, e `deposit/paperA/` não foi tocado nesta rodada.

## Depois do publish: promover para `MANUSCRIPT.md`? Não por cópia simples

O `claims_check.py` e oito scripts de `measurement/` (os quatro `censo-*`, `densidade-de-avisos.py`,
`coerencia-entre-documentos.py`, `auditoria-da-cadeia.py`, `paridade-de-traducao.py`) leem
`paper2-interventional/MANUSCRIPT.md` por caminho fixo, e quase todos os guardas ancoram em
frases e na notação numérica em português (`583.763`, `2,66%`).

Medido numa cópia descartável da árvore (nada no repositório mudou):

| `MANUSCRIPT.md` = | falhas do `claims_check.py` atual (não commitado) |
|---|---:|
| o atual (texto em português) | 11: 7 do `contrafactual_check`, que falha de propósito até o texto novo ser promovido; 3 em `evermind.json`; 1 de órfãos do `auditoria-da-cadeia` |
| o rc8 | 54: somem as 7 do contrafactual; entram 50, de guardas ancorados em português e do `deposito_check` (9), que compara a `description.html` da v1.0 com o manuscrito |

Recomendação, num PR próprio depois do publish:

1. promover **a cópia depositada** (`deposit/paperA-v1.1/MANUSCRIPT-v1.1.md`, sha256
   `8097bac9…`), não o rc8, para que `MANUSCRIPT.md` seja byte a byte o que o DOI serve;
2. no **mesmo** PR, portar os guardas para o texto em inglês: caminho do manuscrito como
   parâmetro (o `densidade-de-avisos.py` já aceita `--doc`), âncoras em inglês e a normalização
   numérica que o `paridade-de-traducao.py` já implementa, e `deposito_check` apontando para
   `deposit/paperA-v1.1/description-v1.1.html`;
3. critério de merge: o `claims_check` volta a ter só as falhas que já existiam antes da
   promoção (`evermind.json` e órfãos), nenhuma nova; e cada guarda portado com mutação que
   morde;
4. preservar o texto em português com nome datado (o `MANUSCRIPT.md` atual já não é o que a
   v1.0 depositou: 137.417 B hoje contra 126.564 B publicados).

Até isso, `MANUSCRIPT.md` fica como está, e o `claims_check` do pacote verifica a v1.0, como o
bloco da description declara.

## Rodada de 2026-10-05 (tarde): status, description em inglês, scrub

- **Bloco de status (linha 10)** reescrito no rc8 **e** no `MANUSCRIPT-v1.1.md`: agora diz que o
  texto está depositado como v1.1, DOI `10.5281/zenodo.23163119` (versão 2 do conceito
  `10.5281/zenodo.22181414`), 2026-10-05. A única diferença entre os dois segue sendo o Apêndice D.
  PDF refeito: 47 páginas, 0 glifos ausentes. Zips idênticos aos anteriores (determinísticos);
  reenviados só PDF, `.md` e manifesto.
- `_sprint-2026-10-04/A-rc8/parity-rc8.py` (empacotado em `scripts-v1.1.zip`) é o gate
  rc7 → rc8 e passou a sair **PARITY FAILED (2)**: o hunk do status não tinha dono no registro de
  achados e muda tokens numéricos (data e DOIs). Resolvido na rodada seguinte (abaixo).
- **Description:** a parte da v1.0 foi traduzida para inglês (`description-v1.0-en.html`):
  mesmos números (multiconjunto conferido com notação normalizada), mesmos links e mesmas tags,
  mais um `<em>` com a citação original em português do cabeçalho do `dose2.mjs`. O bloco v1.1
  passou a dizer que o texto acima é tradução e a citar as frases superadas em inglês.
  `deposit-v1.1.py` monta a description a partir dessa tradução.
- **Scrub:** os 7 arquivos redigidos no pacote foram sobrescritos no repositório com os bytes
  empacotados; lista e sha256 antigo/novo em `SCRUBBED.txt`.

## Rodada de 2026-10-05 (noite): parity, script do censo, manifesto

- **`parity-rc8.py`:** entrada nova `DEPOSIT-STATUS-2026-10-05` com três âncoras no `REGISTRY`
  (data do cabeçalho, DOI da versão `10.5281/zenodo.23163119`, DOI do conceito
  `10.5281/zenodo.22181414`) e o delta de tokens do hunk fixado em `DEPOSIT_STATUS_DELTA`
  (`04` −1, `05` +2, `2026` +1, `10` +1, `10.5281` +2, `2` +1), somado ao `EXPECTED_DELTA` do rc8
  sem mexer nele. Os números de registro (23163119, 22181414) vêm depois de "." e não são token
  para o `NUM_RE`; quem os prende são as âncoras. Nenhuma outra checagem mudou. Agora sai
  **PARITY OK**; `--selftest` **SELFTEST OK** com 11 mutações (as 8 de antes + 3 novas: outro
  número dentro do hunk do status, outro DOI de versão, outro DOI de conceito), todas mordem.
- **`measurement/sprint-censo-artefatos-paperA.py`:** as 4 linhas de código com
  `expanduser('<HOME>/…')` viraram `os.path.join(os.path.expanduser('~'), …)`. Não usei `~/`
  literal porque o `build-package.py` o redige de novo (R3) e o gate o rejeita: a cópia depositada
  voltaria a quebrar. O docstring mantém `<HOME>/`. Rodado (só leitura, sem `--json`) contra
  `MANUSCRIPT-v1.1.md`: saída byte a byte igual à do original pré-scrub (exit 1 nos dois, que é
  "algum caminho citado não resolve", não falha do instrumento). A cópia quebrada achava 0
  ocorrências no lastro e na árvore de serving; a corrigida acha 7, como o original. Os outros 6
  redigidos são JSON/markdown e ficam com o marcador. Novo sha256 em `SCRUBBED.txt`.
- **`build-package.py`:** tabela `JA_REDIGIDOS` com o sha256 do original e as regras dos 7
  arquivos (conferidos contra `git show HEAD:` e o manifesto anterior); o rebuild mantém
  `redacao` e `sha256_no_repositorio` e acrescenta `redacao_no_repositorio` (e, no script,
  `alteracao_pos_redacao`). Sai com erro se algum dos 7 perder o registro ou se um arquivo já
  redigido voltar a pedir redação.
- **Rebuild:** `artefatos-v1.1.zip` igual ao anterior (md5 `64044b6b…`); em `scripts-v1.1.zip`
  mudaram só os 2 membros acima (mesmos 27 nomes); todo membro dos dois zips bate com o
  manifesto. Gate: **0** ocorrências.
- **Rascunho 23163119:** reenviados só `MANIFEST-v1.1.json` e `scripts-v1.1.zip`. Readback:
  22 de 22 campos ok, 18 de 18 arquivos com md5 conferido (tabela acima atualizada). Não publicado.
