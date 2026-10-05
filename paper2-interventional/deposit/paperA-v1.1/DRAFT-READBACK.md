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
| `spare-capacity-narrow-surface-v1.1.pdf` | 318.270 | `d864b7cfb136a621f5b45658d80dc5cc` | novo, 53 páginas |
| `spare-capacity-narrow-surface-v1.1.md` | 231.132 | `351a15c18b64e3a93e07f7d523abbd92` | novo, = rc18 byte a byte |
| `MANIFEST-v1.1.json` | 26.161 | `2a8a8ae3490780173c6d868da8f94bb0` | novo |
| `artefatos-v1.1.zip` | 298.309 | `da78be7457cfa6123097900bc815f6e9` | novo, 60 membros |
| `scripts-v1.1.zip` | 200.170 | `fbb925d0fceebeb62b01754e2ede1aa4` | novo, 39 membros |
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

## Readback campo a campo (forma InvenioRDM + legada): 24 de 24 ok

`is_draft` True · `is_published` False · DOI `10.5281/zenodo.23163119` · concept DOI
`10.5281/zenodo.22181414` · `versions.index` 2 · title = linha 1 do manuscrito ("Spare capacity,
narrow surface: the exposure record of a production agent-memory system", desde a rodada rc11) · version `1.1` ·
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

- **Manuscrito:** `_sprint-2026-10-04/A-v1.1-rc18.md`, byte a byte (sha256 `f8b43d23…88d2d1e`;
  o `build-package.py` sai 1 se o depositado divergir da fonte). Até o rc8 havia uma
  substituição no Apêndice D; desde o rc10 o DOI está no próprio rascunho.
- **PDF:** pandoc 3.9 + xelatex (2 passadas), mesmo preâmbulo do Paper 1 (`paper/preamble.tex`)
  mais 25 glifos mapeados para símbolos matemáticos; **0 "Missing character"** no log. 53
  páginas, Letter. O bloco de título (autor, ORCID, versão, DOI) vem de metadata do pandoc e
  não está no `.md`.
- **Redação:** em 8 arquivos empacotados um caminho local virou marcador (`<HOME>/`,
  `<SCRATCH>/`, `<TMP>`); o manifesto lista quais e guarda o sha256 do original (desde o rc15 também o do
  `REVIEW-A-rc12-2026-10-05.md`, redigido antes do primeiro commit; o original desse não está no git). Gate final
  sobre todo byte empacotado (zips, soltos, texto e bytes do PDF, manifesto): **0** host, IP
  não-loopback ou caminho pessoal. Controle positivo do gate conferido (`/Users/…`, `~/`,
  `srv…`, IP Tailscale e `*.local` são pegos; `127.0.0.1`, `/root/` e `/var/lib/` passam, como
  na v1.0).
- **Fora do pacote** (registrado em `MANIFEST-v1.1.json` → `excluidos`): o `claims_check.py`
  atual, os `.db` de corpus (com os nomes de trabalho que o `diag-out.txt` usa), o log de serving
  bruto, artefatos não citados, os do Paper B e o recibo local da voz citado pelo addendum rc8.

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

1. promover **a cópia depositada** (`deposit/paperA-v1.1/spare-capacity-narrow-surface-v1.1.md`, sha256
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

- **Bloco de status (linha 10)** reescrito no rc8 **e** no `spare-capacity-narrow-surface-v1.1.md`: agora diz que o
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
  `spare-capacity-narrow-surface-v1.1.md`: saída byte a byte igual à do original pré-scrub (exit 1 nos dois, que é
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

## Rodada de 2026-10-05 (rc11): revisão Fable do rc10, pacote, censo de citações

- **Texto:** rc10 → rc11 com os 8 achados de `_sprint-2026-10-04/REVIEW-A-rc10-2026-10-05.md`,
  todos conferidos nos artefatos e aplicados com a redação proposta
  (`_sprint-2026-10-04/APPLY-A-rc11.md`). `A-rc11/parity-rc11.py --selftest`: PARITY OK,
  SELFTEST OK (20 mutações; 19 mordem, a de unidade segue como limite documentado). F-5 ganhou o
  "Addendum, rc11". `spare-capacity-narrow-surface-v1.1.md` = rc11 byte a byte.
- **Achado 1 (diag):** `diag-out.txt` entrou em `artefatos-v1.1.zip` e
  `diag-residual-mismatch.py` (quem o produziu: mesmo formato de saída; o cabeçalho do `.txt` o
  chama pelo nome de trabalho `diag.py`) em `scripts-v1.1.zip`. A exclusão foi estreitada para
  `{out-pres0908,out-ord0826-tzm3-0828}.json` + `copies-sha256.txt`, que o manuscrito de fato
  não cita (os dois JSON aparecem só na nota de sprint `A-filters-disaggregation.md`, que entra).
- **Censo de citações** (novo, dentro do `build-package.py`, roda a cada build e barra o
  depósito se houver lacuna; resumo em `MANIFEST-v1.1.json` → `censo_citados`): todo caminho que
  o rc11 cita e que é `_sprint-2026-10-04/…` ou `out/…` (escrito assim ou resolvido assim no
  repositório, inclusive nomes nus como `out-ord0826.json`, chaves e globs expandidos).
  - Antes da correção: **10 lacunas** — `diag-out.txt`, `diag-residual-mismatch.py`,
    `A-rc9/parity-rc9.py` (citado 2×), `A-rc10/parity-rc10.py`, `A-rc11/parity-rc11.py`,
    `APPLY-A-rc9.md`, `APPLY-A-rc10.md`, `APPLY-A-rc11.md`, `REVIEW-A-rc9-2026-10-05.md`,
    `REVIEW-A-rc10-2026-10-05.md` (os registros de revisão citados pelos addenda rc9–rc11 do F-5).
  - Corrigido do mesmo jeito: os 10 entraram no pacote (6 em `artefatos-v1.1.zip`, 4 em `scripts-v1.1.zip`). Nenhum precisou de
    redação (0 ocorrências antes de redigir), então o repositório segue igual ao depositado:
    todo membro dos dois zips é byte a byte o arquivo do repositório; `SCRUBBED.txt` não muda.
  - Depois: **71 caminhos no escopo, 0 lacunas** (42 cobertos pela v1.1, 29 só pela v1.0).
    Controles: tirar `diag-out.txt` e `parity-rc11.py` da lista faz o censo acusar os dois; um
    `out/NAO-EXISTE-2026.json` injetado sai como lacuna.
  - **Fora do escopo, mas corrigido:** o §3.3 diz que as citações de linha de `brief.ts` se referem
    ao módulo "as deposited in `serving-*.ts`", e a v1.0 não depositou `serving-brief.ts` (só
    `-diversity`, `-salience`, `-search`). O arquivo está no git desde 2026-08-27, sha256
    `27dbe996…`, igual ao pin do `SERVING-CODE-MANIFEST.md`; entrou em `scripts-v1.1.zip`.
    Reverter é tirar uma linha de `SCRIPTS`.
  - **Fora do escopo, não empacotado:** `MANUSCRIPT-B.md` (Apêndices A e C citam o Paper B, que
    tem depósito próprio). Sem resolução no repositório, por declaração: os `.db`, `ts-350.txt`,
    `memory/*.md` da produção, `.remember/…` (recibo do Codex no addendum rc8).
- **Achado 6 (Open items 5) conferido:** o censo `measurement/sprint-censo-artefatos-paperA.py`
  rodado sobre o `MANUSCRIPT.md` em português (o detector de Apêndice D dele só casa
  `## Apêndice D`) dá 1 MISSING (`ts-350.txt`) e as entradas do Apêndice D ausentes da v1.0: 9
  arquivos, todos itens do `MANIFEST-v1.1.json`, mais `implantacao/`, que entra como os 9
  arquivos de `measurement/implantacao/`.
- **Gate de privacidade:** 0 ocorrências em todo byte empacotado (zips, soltos, texto e bytes do
  PDF, manifesto), incluindo os 11 arquivos novos.
- **Description:** o bloco "What changed in v1.1" ganhou o parágrafo **Title** (título da v1.0 →
  título da v1.1, e o motivo), e o contrafactual foi alinhado ao rc11: ranks 1, 3 e 4 por
  salience entre os 149 servidos, 44–46 com acesso zerado, dedup não reexecutado; o pin como a
  outra condição, medido como necessário para um chunk (116107). Contagens do pacote
  atualizadas (46/32), e "differs only in Appendix D" virou "byte for byte the final draft
  (rc11)". Segue toda em inglês.
- **Rascunho 23163119:** metadata regravada (title novo) e os 5 arquivos novos reenviados.
  Readback: **22 de 22** campos ok, **18 de 18** arquivos com md5 conferido (13 da v1.0 contra o
  registro 22181415, 5 novos contra o disco), membros dos zips conferidos contra o manifesto
  (tabela acima atualizada). **Não publicado.**

## Rodada de 2026-10-05 (rc12): revisão Fable do rc11, duas exclusões declaradas

- **Texto:** rc11 → rc12 com os achados de `_sprint-2026-10-04/REVIEW-A-rc11-2026-10-05.md`
  (salva verbatim), todos conferidos antes de aplicar (`_sprint-2026-10-04/APPLY-A-rc12.md`):
  - **(2)** §4.3.1: os 3 slots compartilhados são o que `mainTarget` deixa depois da cota do
    agente (8 − 5); como servido, os 3 pinados os ocupam na fase 0; com F7 levantado vão ao top-3
    do sub-pool `scope=global` depois do dedup, e 227328 substitui 116107. Conferido em
    `serving-brief.ts` (l.436 `mainTarget`, l.442-451 fase 0, l.457 break em `mainTarget`, l.531
    `ceil(n/2)` = 5 para o pool do agente, que vem primeiro) e em `out-ord0826.json`
    (`lift_F7_pinned`: 33 ids, baseline − lift = {116107}, lift − baseline = {227328}, Jaccard
    médio 7/9; `pinned_per_brief_hist` = 3 em todo brief; `by_subpool` 672 × 3 / 672 × 5).
  - **(4)** Apêndice D: "the two sprint scripts whose full paths the table gives"; a linha da
    desagregação dá o caminho completo de `diag-residual-mismatch.py` e diz que `diag-out.txt`
    também traz a corrida de 2026-09-08 e o controle de 2026-08-28. §9: dias desde o último acesso
    na ordem dos ranks (42, 90 e 30), conferido em `SALIENCE-COUNTERFACTUAL-PROD-2026-10-05.json`
    (`the_three` e `rounds[0].union_149.prod`).
  - `A-rc12/parity-rc12.py --selftest`: **PARITY OK**, **SELFTEST OK** (19 mutações; 18 mordem,
    a de unidade segue como limite documentado). `withdrawn` carrega as 8 do rc11 e acrescenta 2
    (a frase antiga da l.899 e a ordem antiga do §9). F-5 ganhou o "Addendum, rc12".
    `spare-capacity-narrow-surface-v1.1.md` = rc12 byte a byte.
- **(3) Manifesto:** as duas declarações vivem em `EXCLUIDOS` do `build-package.py` (o rebuild as
  mantém): entrada nova para `.remember/adversary-receipt-codex-2026-10-05T100118-80790.txt`, e a
  entrada dos `.db` termina com "(nomes de trabalho em diag-out.txt: ord-0826.db,
  preservado-0908.db)". `excluidos` tem agora 6 entradas.
- **Pacote:** `FONTE` → rc12; entraram `REVIEW-A-rc11-2026-10-05.md` e `APPLY-A-rc12.md`
  (artefatos, 46 → 48) e `A-rc12/parity-rc12.py` (scripts, 32 → 33), citados pelo addendum rc12.
  **Censo:** 76 caminhos no escopo, **0 lacunas** (47 cobertos pela v1.1, 29 só pela v1.0).
  **Gate de privacidade: 0.** PDF refeito: **49 páginas**, **0 glifos ausentes**.
- **Description:** o bloco "What changed in v1.1" não descrevia os três slots como do floor (diz
  que o pin protege só o que o score já pôs no brief e é necessário para um dos três), então nada
  de conteúdo mudou; foram atualizadas as contagens (48/33), "parity checks of drafts rc8 to
  rc12" e "the final draft (rc12, Appendix F-5)". `description-v1.1.html` md5 `8a12eb81a06a14a04e189e8e271f6138`.
- **Rascunho 23163119:** metadata regravada e os 5 arquivos novos reenviados ao **mesmo**
  rascunho. Readback: **22 de 22** campos ok, **18 de 18** arquivos com md5 conferido (13 da v1.0
  contra o registro 22181415, 5 novos contra o disco), membros dos zips conferidos contra o
  manifesto (tabela acima atualizada). **Não publicado.**

## Rodada de 2026-10-05 (rc13): revisões Codex e DeepSeek do rc12

- **Texto:** rc12 → rc13 com os 8 achados de `_sprint-2026-10-04/REVIEW-A-rc12-2026-10-05.md`
  (as duas saídas verbatim, recuperadas dos transcripts das cascas; recibos Codex
  `…125855-34251` e DeepSeek `…125812-33216`, ambos exit 0), todos conferidos antes de aplicar
  (`_sprint-2026-10-04/APPLY-A-rc13.md`):
  - **C1** §4.3.2: o tráfego de busca rastreado é necessário para os ranks de salience; o pin
    afeta a seleção e é necessário para um dos três (116107). Varredura: Abstract (DS2), §1 (DS6)
    e §9 deixaram de tratar o pin como condição de rank.
  - **C2** §4.3.1: nos dias com `fresh_added` não nulo, o brief que falha o teste estrito deixa
    9 ou 10 ids (ex. 2026-08-24: 672 briefs, 649 exatos, 23 ≠ 8, 5.400 = 5.376 + 24); em
    2026-09-03 e 2026-09-07 ficam os 10.
  - **DS1** §1: nenhum artefato guarda os "cinco dias seguidos com zero itens novos" (a tabela
    da v1.0 vinha de `regime-cobertura.py` sem saída preservada, e a própria tabela mostrava 52
    novos em 20/08, invisíveis ao `JOIN chunks`). Trocado pelo que `BATCH-CYCLE-2026-08-29.json`
    guarda: o lote de 2026-08-21..22 servido a 108 por dia (109 em 08-26), idade mínima subindo
    exatamente +1,00/dia de 0,92 (08-23) a 6,92 (08-29); §4.3.1 e §2 dizem o mesmo com datas.
  - **DS3–DS6:** §2 *no-record* verificável e cota inferior; cabeçalho da tabela de filtros
    "(of a 672-brief day)" + nota de 2026-09-03 (441, 126); §1 nomeia os sub-pools (por agente 0,
    global 108); "three shared main-pool slots".
  - `A-rc13/parity-rc13.py --selftest`: **PARITY OK**, **SELFTEST OK** (24 mutações; 23 mordem,
    a de unidade segue como limite documentado). `withdrawn` carrega as 10 do rc12 e acrescenta
    10. F-5 ganhou o "Addendum, rc13". `spare-capacity-narrow-surface-v1.1.md` = rc13 byte a byte.
- **Pacote:** `FONTE` → rc13; entraram `REVIEW-A-rc12-2026-10-05.md` e `APPLY-A-rc13.md`
  (artefatos, 48 → 50) e `A-rc13/parity-rc13.py` (scripts, 33 → 34). **Censo:** 79 caminhos no
  escopo, **0 lacunas** (50 cobertos pela v1.1, 29 só pela v1.0). **Gate de privacidade: 0**
  (8 arquivos redigidos; o REVIEW novo leva R2 ×2). PDF refeito: **50 páginas**, **0 glifos
  ausentes**, md5 `28808db457959a0f972a32b19f464120`.
- **Description:** o item do bloco "What changed in v1.1" chamava o pin de "the other
  condition" do rank; agora diz que o pin afeta a seleção separadamente, põe os três primeiro em
  todo brief, protege só o que o score já pôs ali e é necessário para um dos três. Contagens
  50/34, "drafts rc8 to rc13", "(rc13, Appendix F-5)", "In eight packaged files".
  `description-v1.1.html` md5 `e77c8be16fcba3e88c25305d063d30e8`.
- **Rascunho 23163119:** metadata regravada e os 5 arquivos novos reenviados ao **mesmo**
  rascunho. Readback: **22 de 22** campos ok, **18 de 18** arquivos com md5 conferido (13 da v1.0
  contra o registro 22181415, 5 novos contra o disco), membros dos zips conferidos contra o
  manifesto (tabela acima atualizada). **Não publicado.**

## Rodada de 2026-10-05 (rc14): revisão Codex do rc13

- **Texto:** rc13 → rc14 com os 2 achados de `_sprint-2026-10-04/REVIEW-A-rc13-2026-10-05.md`
  (verbatim; recibo Codex `…132453-63584`, exit 0), ambos conferidos antes de aplicar
  (`_sprint-2026-10-04/APPLY-A-rc14.md`):
  - **CR1** §1, §4.3.1, §2 e o addendum rc13: `BATCH-CYCLE-2026-08-29.json` vem de
    `ciclo-do-lote.py`, que pega o lote por data de criação e conta serves dos **dois** canais;
    o 109 de 2026-08-26 não é contagem de cobertura (o log dá os mesmos 108 ids do lado da
    cobertura em todo dia de 08-23 a 08-29, 08-26 incluído:
    `A-rc2/COVERAGE-SET-FROM-LOG-2026-10-04.json`). O texto agora separa as duas medições: o
    conjunto de cobertura pelo log e, à parte, o lote nos dois canais (108/dia, exceto 109 em
    08-26; idade mínima de 0,92 a 6,92 em passos de 1,00, a duas casas). "that batch belongs to
    the second" → "the coverage-served portion of that batch belongs to the global sub-pool";
    "the signature of a frozen set" sai.
  - **CR2** Abstract, §1, §9: o pin seleciona os três na fase 0, antes do quota pass; a lista
    escolhida é depois reordenada por score (`serving-brief.ts:483`), então "places them first"
    sai. A necessidade medida para um dos três (116107) fica.
  - **V10** addendum rc13: dizia que a tabela dos "cinco dias" estava no texto da v1.0. Não
    estava: entrou em `MANUSCRIPT.md` no `bcca3a3` (2026-08-28) e saiu no `734e59a`, antes do
    depósito. A v1.0 publicada trazia a afirmação no **§1** (Introdução, item 1 "calendário",
    l.228-232 do `MANUSCRIPT.md` publicado) e um ponteiro no **§2** (Sistema sob medição,
    l.337-338: "o §4.3.1 mostra cinco dias seguidos em que não houve" candidato), sem nada
    correspondente no §4.3.1. A rodada rc13 acima repete o mesmo deslize ("a tabela da v1.0").
  - `A-rc14/parity-rc14.py --selftest`: **PARITY OK**, **SELFTEST OK** (26 mutações; 25 mordem,
    a de unidade segue como limite documentado). `history` exige rc5..rc12 idênticos e o
    addendum rc13 uma vez (ele foi corrigido no lugar, com deltas declarados); `withdrawn`
    carrega as 20 e acrescenta 8, entre elas "places them first". F-5 ganhou o "Addendum, rc14".
    `spare-capacity-narrow-surface-v1.1.md` = rc14 byte a byte.
- **Pacote:** `FONTE` → rc14; entraram `REVIEW-A-rc13-2026-10-05.md` e `APPLY-A-rc14.md`
  (artefatos, 50 → 52) e `A-rc14/parity-rc14.py` (scripts, 34 → 35). **Censo:** 82 caminhos no
  escopo, **0 lacunas** (53 cobertos pela v1.1, 29 só pela v1.0). **Gate de privacidade: 0**
  (8 arquivos redigidos, os mesmos). PDF refeito: **50 páginas**, **0 glifos ausentes**, md5
  `9c31328d7540cb4637c7c70108c22918`.
- **Description:** novo parágrafo "A v1.0 statement withdrawn." depois do "Also narrowed": a
  afirmação estava no §1 da v1.0 (com o ponteiro do §2), a série vinha de um rascunho anterior
  ao depósito sem saída preservada, era falsa como escrita (52 itens de 2026-08-20,
  `RECON-52-e-sondas-2026-10-04.json`), e a v1.1 a troca pelas duas medições separadas. O item
  do pin diz "selects them in phase 0, before the quota pass". Contagens 52/35, "drafts rc8 to
  rc14", "(rc14, Appendix F-5)". `description-v1.1.html` md5 `a4f992fd2285ad571e5df6768bcff209`.
- **Rascunho 23163119:** metadata regravada e os 5 arquivos novos reenviados ao **mesmo**
  rascunho. Readback: **22 de 22** campos ok, **18 de 18** arquivos com md5 conferido (13 da v1.0
  contra o registro 22181415, 5 novos contra o disco), membros dos zips conferidos contra o
  manifesto (tabela acima atualizada). **Não publicado.**

## Renomeação do manuscrito (2026-10-05)

- `MANUSCRIPT-v1.1.pdf` → `spare-capacity-narrow-surface-v1.1.pdf` e `MANUSCRIPT-v1.1.md` →
  `spare-capacity-narrow-surface-v1.1.md`, só no nome: md5 `9c31328d7540cb4637c7c70108c22918` e
  `0e1eb38ee42e4f8d3fa31e5a5881d6a7`, os mesmos de antes. O PDF não grava o próprio nome (sem
  XMP, Info só com Title/Author/Creator/Producer/CreationDate; nenhum dos 77 streams
  descomprimidos traz o nome), então não foi refeito. Neste documento, as menções anteriores
  foram trocadas para o nome novo. O `MANUSCRIPT.md` da v1.0 (files-import) mantém o nome.
- Referências atualizadas: `build-package.py` (`SOLTOS` e rótulos do gate), `deposit-v1.1.py`
  (`NOVOS`, leitura do título e a lista `OBSOLETOS`, que apaga as chaves antigas do rascunho e
  exige no readback que não existam), `build/build-pdf.sh` (entrada, jobname e saída),
  `description-v1.1-block.html` (e, por regeneração, `description-v1.1.html`, md5
  `855aa49c6064d4a71eba74cea8b0b3ea`), `SCRUBBED.txt`, `_sprint-2026-10-04/APPLY-A-rc14.md`, e o
  `DEFAULT_DEPOSIT` de `A-rc10..A-rc14/parity-rc1x.py`. Notas históricas (`APPLY-A-rc9..rc13`,
  `REVIEW-A-rc9`) ficaram com o nome da época.
- `A-rc14/parity-rc14.py --selftest`: **PARITY OK**, **SELFTEST OK**. `build-package.py`:
  **censo 82 no escopo, 0 lacunas**, **gate de privacidade 0**. Mudaram de hash, por conter os
  arquivos editados: `scripts-v1.1.zip` (5 parity + `build-pdf.sh`), `artefatos-v1.1.zip`
  (`APPLY-A-rc14.md`) e o manifesto.
- **Rascunho 23163119:** chaves antigas apagadas, os 2 nomes novos + manifesto + 2 zips enviados,
  metadata regravada. Readback: **24 de 24** campos ok (22 + as 2 chaves antigas ausentes),
  **18 de 18** arquivos com md5 conferido, membros dos zips conferidos. **Não publicado.**

## Rodada de 2026-10-05 (rc15): revisões Fable e Codex do rc14

- **Revisões:** `_sprint-2026-10-04/REVIEW-A-rc14-2026-10-05.md`, verbatim (Fable, passe único,
  só defeitos; Codex, recibo `adversary-receipt-codex-2026-10-05T135649-98273.txt`, exit 0, 437 s).
  Dez achados, os dez conferidos contra código, artefato ou fonte e os dez aplicados; registro em
  `_sprint-2026-10-04/APPLY-A-rc15.md`.
  - **FB1** o conjunto de 108 e a identidade 33 + 108 = 141 são contagens sobre os briefs de 10
    linhas com agente (`coverage-set-from-log.py:24-25`); as 5 sondas de 5 linhas de 2026-08-26
    ficam fora e serviram 5 chunks a mais (`RECON-52-e-sondas-2026-10-04.json`, `por_dia_utc`:
    146 nesse dia). Qualificador "in the agent briefs" no §1, §2, §4.3.1 (×3), Apêndice A, F-4,
    addendum rc14 e description; a exceção nomeada no §4.3.1.
  - **FB2** idade mínima datada: 0,92 em 08-23 a 6,92 em 08-29 (0,72 em 08-22), §1, addendum rc14
    e description.
  - **FB3** opção (a): `REVIEW-A-rc12-2026-10-05.md` entrou no `JA_REDIGIDOS` com o hash do
    original (`9d1abb0f…07ee6e6ce`, `R2 x2`; `redige(original)` = cópia do repositório). O
    original nunca foi commitado (os dois commits já têm a cópia redigida), e o manifesto diz isso
    nesse item; a description mantém "eight", agora verdadeiro (8 itens com `redacao` +
    `sha256_no_repositorio`).
  - **CX1** Tabela 3 do survey (conferida numa cópia local do PDF v4, sha256 `497e9549…`) também
    lista métricas de qualidade de memória, de resposta e de tarefa fim a fim: Abstract, §1 (abertura
    e bullet "gap") e §8.1 reescritos; a frase da description v1.0 ("they evaluate nDCG and recall
    over query sets") listada como superada no bloco v1.1 (a tradução da v1.0 não foi editada).
  - **CX2** §5.6 virou "same-stratum matching check", não falsificador: o dedup do `pickDedup`
    depende da ordem (`serving-brief.ts:420-433`). Linha da tabela "Proposition 1 | survives" →
    "same-stratum matching check | passes".
  - **CX3** teto medido com os rótulos de severidade fixos; independência não estabelecida (§5.1,
    Apêndice C). A citação `serving-brief-outcome.ts:359` não entrou no texto: o módulo não está
    nem na v1.0 nem no pacote v1.1.
  - **CX4** §5.5: 17/350 com elegibilidade, designação e multiplicadores fixos; não é máximo (17 a
    26 com outras designações). Description alinhada.
  - **CX5** §6, última linha: 245 contra 151 (limite inferior) não estabelece quem lidera.
  - **CX6** `churn` = ids só do tratado (`would_enter`), metade da diferença simétrica com
    conjuntos de mesmo tamanho; todos os números de churn foram calculados assim e ficam.
  - **CX7** utilidade do serving uniforme não medida (Abstract, §1, §4.1.1, §9).
  - `A-rc15/parity-rc15.py --selftest`: **PARITY OK**, **SELFTEST OK** (31 mutações; 30 mordem,
    a de unidade segue como limite documentado). `history` exige rc5..rc13 idênticos e o addendum
    rc14 uma vez (corrigido no lugar, deltas declarados); `withdrawn` carrega as 28 e acrescenta
    27; duas linhas de tabela declaradas (CX2, CX5). F-5 ganhou o "Addendum, rc15".
    `spare-capacity-narrow-surface-v1.1.md` = rc15 byte a byte.
- **Pacote:** `FONTE` → rc15; entraram `REVIEW-A-rc14-2026-10-05.md` e `APPLY-A-rc15.md`
  (artefatos, 52 → 54) e `A-rc15/parity-rc15.py` (scripts, 35 → 36). **Censo:** 87 caminhos no
  escopo, **0 lacunas** (58 cobertos pela v1.1, 29 só pela v1.0). **Gate de privacidade: 0**
  (8 arquivos redigidos, agora todos com hash do original). PDF refeito: **51 páginas**, **0
  glifos ausentes**, md5 `31af94c019f0a65446d4d630436c6057`.
- **Description:** bloco v1.1 com o item CX1 (frase da v1.0 superada), o 17/350 estreitado (CX4),
  o parágrafo "A v1.0 statement withdrawn" com o qualificador e as datas (FB1, FB2), contagens
  54/36, "drafts rc8 to rc15", "(rc15, Appendix F-5)". `description-v1.1.html` md5
  `4979a9494f24db66f7d8c2ae6cf09c7b`.
- **Rascunho 23163119:** metadata regravada e os 5 arquivos novos reenviados ao **mesmo**
  rascunho. Readback: **24 de 24** campos ok, **18 de 18** arquivos com md5 conferido (13 da v1.0
  contra o registro 22181415, 5 novos contra o disco), membros dos zips conferidos contra o
  manifesto (tabela no topo atualizada). **Não publicado.**

## Rodada de 2026-10-05 (rc16): revisões Codex e Fable do rc15

- **Revisões:** `_sprint-2026-10-04/REVIEW-A-rc15-2026-10-05.md`, verbatim (Codex, recibo
  `adversary-receipt-codex-2026-10-05T142159-29079.txt`, exit 0, 360 s, NO-GO; Fable, passe único,
  defeitos restantes, GO). Sete achados, os sete conferidos contra código, artefato ou fonte e os
  sete aplicados; registro em `_sprint-2026-10-04/APPLY-A-rc16.md`.
  - **CX-A** §1 chamava o §5.6 de "the test that could have killed it", e o §5.6 diz que não é
    falsificador. Agora: as 20 entradas na saturação tiveram saída no mesmo estrato; checagem
    empírica, não falsificador da Proposição 1 (§5.2, §5.6). **Varredura** (classe "checagem
    chamada de falsificador"): título do §5.6 → "A same-stratum matching check on recorded
    quantities"; linha da tabela do §6 ("The valid test" → "The check that replaced it … is not a
    falsifier"). Description sem frase da classe.
  - **CX-B** F-1 dizia que razão ≈ 1 "would be the *worse* policy": trocado por "whether that
    policy would improve or worsen agent utility was not measured". **Varredura** (classe "política
    melhor/pior sem utilidade medida"): F-1 "including a correct one" ×2 → "whatever its effect on
    agent utility"; nota do título não chama mais o corpus de "starved". Description sem frase da
    classe.
  - **CX-C** §5.7.1: o classificador (`granularidade-do-teto.py:200-213`) rotula
    "inalcançabilidade" só por ausência no controle + churn 0. Contradição confirmada no log
    fechado: no estado 05:37 o último serve de 308284, 308222 e 308240 cai na hora 03; no estado
    07:37, o de 308296, 308222 e 308240 na hora 05; o controle por hora seleciona 308222 e 308240
    (`out/gran3-hora.json`). Virou "loss of sensitivity", com a evidência do log (declarado não
    depositado). Script e `CEILING-GRANULARITY-2026-08-28.json` mantêm o rótulo.
  - **CX-D** §4.3.2: `clamp01` no termo de acesso (`serving-salience.ts:227-234`, mesmo md5 do
    arquivo depositado na v1.0); "non-decreasing and capped at 0.20".
  - **FB-A** o 10.899 de `sessions/%` não está em nenhum artefato (todas as ocorrências são a união
    viva do §4.1); sinalizado no §4.3.1 e no bloco de status.
  - **FB-B** Apêndice D: quatro artefatos de `out/` datados 2026-10-05 citados (a pasta tem seis;
    os dois `C12-*` são do Paper B), não três.
  - **Nit** §4.3.1: 285 → `DEVIATIONS-FOR-PAPER.md` §10.11 (l.1257).
  - `A-rc16/parity-rc16.py --selftest`: **PARITY OK**, **SELFTEST OK** (31 mutações; 30 mordem,
    a de unidade segue como limite documentado). `history` agora exige rc5..rc15 idênticos;
    `withdrawn` carrega as 55 e acrescenta 17; um título e uma linha de tabela declarados (CX-A).
    F-5 ganhou o "Addendum, rc16". `spare-capacity-narrow-surface-v1.1.md` = rc16 byte a byte.
- **Pacote:** `FONTE` → rc16; entraram `REVIEW-A-rc15-2026-10-05.md` e `APPLY-A-rc16.md`
  (artefatos, 54 → 56) e `A-rc16/parity-rc16.py` (scripts, 36 → 37). **Censo:** 91 caminhos no
  escopo, **0 lacunas** (61 cobertos pela v1.1, 30 só pela v1.0; o novo `out/gran3-hora.json` já
  estava na v1.0). **Gate de privacidade: 0** (8 arquivos redigidos). PDF refeito: **52
  páginas**, **0 glifos ausentes**, md5 `c0e6d6d291c64879ea176a4853c7c1bb`.
- **Description:** contagens 56/37, "drafts rc8 to rc16", "(rc16, Appendix F-5)"; nada mais do que
  ela diz muda com o rc16. `description-v1.1.html` md5 `343d2785eef4cd1bc0ad766921c88173`.
- **Rascunho 23163119:** metadata regravada e os 5 arquivos novos reenviados ao **mesmo**
  rascunho. Readback: **24 de 24** campos ok, **18 de 18** arquivos com md5 conferido (13 da v1.0
  contra o registro 22181415, 5 novos contra o disco), membros dos zips conferidos contra o
  manifesto (tabela no topo atualizada). **Não publicado.**

## Rodada de 2026-10-05 (rc17): revisão Codex do rc16

- **Revisão:** `_sprint-2026-10-04/REVIEW-A-rc16-2026-10-05.md`. O recibo
  (`adversary-receipt-codex-2026-10-05T144610-47994.txt`, exit 0, 334 s, NO-GO) não tem
  `output_file`; o stdout inteiro da chamada sobreviveu no tool-result da sessão, e os 438.705 bytes
  da voz batem com o `output_sha256` do recibo (`728ecccd…8e7cc6`). A mensagem final está verbatim
  no REVIEW, junto com o resumo da casca; o output inteiro (com o log de exec) ficou ao lado do
  recibo, em `.remember/adversary-output-codex-2026-10-05T144610-47994.txt`, fora do pacote. Seis
  achados (C17-1..C17-6), os seis conferidos e aplicados; registro em
  `_sprint-2026-10-04/APPLY-A-rc17.md`.
  - **C17-1** §3.1: o `INSERT INTO brief_log` roda sobre `result.items` antes do
    `renderBriefText` (`brief.ts:1081-1104`), que corta linhas no `TOKEN_BUDGET` (`:867-881`, só no
    formato texto). O render check de `out-ord0826.json` dá 0 linhas cortadas em todo brief
    reconstruído de 2026-08-22 a 2026-09-07 (09-02 ausente; 08-21 sem reconstrução). Agora:
    seleções registradas antes da renderização, entrega na janela inteira não verificada, e
    *served* definido como "selected and logged". **Varredura:** Abstract e §1 ("logged 583,763
    selected slots", "They hold 1,635"), §1 bullet, §4.1.1, §4.2, §4.3.1, §9. Limites inferiores de
    não-entrega intactos. Description: o bullet do 1.787 passa a citar "delivered 583,763 slots"
    e "actually receives" da v1.0 como superados.
  - **C17-2** §1 e §8.3: "These terms are absent from this survey's extracted text. This does not
    establish field methods or conventions." **Varredura:** primeira frase do Abstract e do §1,
    "goes unasked", "the benchmarks do not measure", abertura do §8.3 ("in systems CS, it is
    not" e "that precedent"), terceira conclusão do §9. Description: o bullet do survey passa a
    citar "a coordinate the field's benchmarks do not measure" e diz que o survey não é censo do
    campo.
  - **C17-3** §4.3.2: os três constantes ficam no pool principal pela reconstrução do §4.3.1 (fase
    0, pinned), não pela frequência.
  - **C17-4** §4.3.2: "would respond to a score adjustment, and nobody adjusts it", igual ao
    Abstract e ao §9.
  - **C17-5** §4.3.2: com retenção NULL o score não cai com o tempo, mas acessos rastreados ainda
    sobem o termo de acesso até o teto (414/363/911 dão 0,175/0,171/0,197 < 0,20).
  - **C17-6** §4.3.1: "the unit used in this main-pool comparison".
  - `A-rc17/parity-rc17.py --selftest`: **PARITY OK**, **SELFTEST OK** (29 mutações; 28 mordem,
    a de unidade segue como limite documentado). `history` exige rc5..rc16 idênticos; `withdrawn`
    carrega as 72 e acrescenta 25; nenhum título nem linha de tabela muda; um delta de qualificador
    declarado (`phase 0` +1, C17-3). F-5 ganhou o "Addendum, rc17".
    `spare-capacity-narrow-surface-v1.1.md` = rc17 byte a byte.
- **Pacote:** `FONTE` → rc17; entraram `REVIEW-A-rc16-2026-10-05.md` e `APPLY-A-rc17.md`
  (artefatos, 56 → 58) e `A-rc17/parity-rc17.py` (scripts, 37 → 38). **Censo:** 94 caminhos no
  escopo, **0 lacunas** (64 cobertos pela v1.1, 30 só pela v1.0). **Gate de privacidade: 0** (8
  arquivos redigidos). PDF refeito: **53 páginas**, **0 glifos ausentes**, md5
  `ef671f7282fc13ef7c98ad9cec2bc9b0`.
- **Description:** frases das classes C17-1 e C17-2 (acima), contagens 58/38, "drafts rc8 to
  rc17", "(rc17, Appendix F-5)". `description-v1.1.html` md5 `0c66bdba670c64a849007b869846adb8`.
- **Rascunho 23163119:** metadata regravada e os 5 arquivos novos reenviados ao **mesmo**
  rascunho. Readback: **24 de 24** campos ok, **18 de 18** arquivos com md5 conferido (13 da v1.0
  contra o registro 22181415, 5 novos contra o disco), membros dos zips conferidos contra o
  manifesto (tabela no topo atualizada). **Não publicado.**

## Rodada de 2026-10-05 (rc18): revisão Fable do diff rc16 → rc17

- **Revisão:** `_sprint-2026-10-04/REVIEW-A-rc17-2026-10-05.md`, as três notas do Fable verbatim
  (como repassadas), veredito **GO**. Três notas baixas (F18-1..F18-3), as três conferidas e
  aplicadas; registro em `_sprint-2026-10-04/APPLY-A-rc18.md`.
  - **F18-1** §8.3: o título "Pre-registration in systems CS" nomeava um escopo que o corpo não
    trata desde o rc17. Agora "Pre-registration, and what this paper does not claim about it".
    Nenhuma referência cruzada cita o texto do título (fora dos addenda, que são histórico).
  - **F18-2** §1, bullet da lacuna: "how many distinct items a system in production selects for an
    agent, and which ones." **Varredura** (a quantidade medida dita como o que o agente vê ou
    recebe): a pergunta do §1 ("what does the system select for the agent?"), o §5.5 ("To move
    what the brief selects") e o §9 ("what the brief selects for the agent"). Mantidos, com motivo
    no APPLY: a pressuposição do retrieval no §1, "it receives it" no §2, o braço de controle no
    Abstract, o laço condicional não medido (§4.3.2, §8.2), o formato de 10 itens na analogia do
    §8.2, frases cujo sujeito não é o agente, e o Apêndice F.
  - **F18-3** §3.1: conferido em `serving-brief.ts:1081-1101` (= o depositado, md5
    `ffe9d2d0…70bb87b4`): o `INSERT INTO brief_log` está num `try` cujo `catch` só tem o
    comentário "fail-open", sem contador, log ou métrica, e o brief é devolvido depois dele; o
    loop não está numa transação. Frase nova depois da de seleções registradas: a leitura de
    *no-record* como limite inferior também supõe que essa escrita nunca falhou
    (`brief.ts:1099-1101`), e o código não registra falha. Na description, a ressalva entrou no
    bullet do 83,78% (é ele que afirma o limite inferior; o bullet das seleções registradas não
    afirma).
  - `A-rc18/parity-rc18.py --selftest`: **PARITY OK**, **SELFTEST OK** (27 mutações; 26 mordem,
    a de unidade segue como limite documentado). `history` exige rc5..rc17 idênticos (a última
    frase do addendum rc17 é qualificada pelo addendum rc18, não editada); `withdrawn` carrega as
    97 e acrescenta 6; um título declarado (§8.3, F18-1); um delta de qualificador declarado
    (`no-record` +1, F18-3). F-5 ganhou o "Addendum, rc18".
    `spare-capacity-narrow-surface-v1.1.md` = rc18 byte a byte.
- **Pacote:** `FONTE` → rc18; entraram `REVIEW-A-rc17-2026-10-05.md` e `APPLY-A-rc18.md`
  (artefatos, 58 → 60) e `A-rc18/parity-rc18.py` (scripts, 38 → 39). **Censo:** 97 caminhos no
  escopo, **0 lacunas** (67 cobertos pela v1.1, 30 só pela v1.0). **Gate de privacidade: 0** (8
  arquivos redigidos). PDF refeito: **53 páginas**, **0 glifos ausentes**, md5
  `d864b7cfb136a621f5b45658d80dc5cc`.
- **Description:** frase do F18-3 (acima), contagens 60/39, "drafts rc8 to rc18",
  "(rc18, Appendix F-5)". `description-v1.1.html` md5 `fbd6ca4609f837bf8287ce547a026bf9`.
- **Rascunho 23163119:** metadata regravada e os 5 arquivos novos reenviados ao **mesmo**
  rascunho. Readback: **24 de 24** campos ok, **18 de 18** arquivos com md5 conferido (13 da v1.0
  contra o registro 22181415, 5 novos contra o disco), membros dos zips conferidos contra o
  manifesto (tabela no topo atualizada). **Não publicado.**
