# Paper B v2.0 — rascunho no Zenodo: CRIADO, PREENCHIDO (rc28), readback OK; publicar = manual

| campo | valor |
|---|---|
| rascunho | **23223385** (`.draft-id-v2.0`), nova versão de 22110203 (v1.12); `is_draft` True, `is_published` False |
| DOI reservado | `10.5281/zenodo.23223385` (no .md 2×, no PDF 3×) |
| concept DOI | `10.5281/zenodo.21964093` (não muda); `versions.index` 4 = as 3 publicadas (1.9, 1.11, 1.12) + 1 |
| texto | `_sprint-2026-10-04/B-v2-rc28.md` (`449d4dec…`), título novo (linha 1) |
| preenchido | `deposit-v2.0.py --fill --publication-date 2026-10-07`, 2026-10-07; metadata + 6 arquivos (18.859.392 bytes) |
| readback | `--readback` 2026-10-07T23:59:25Z: **19 campos ok, 6 arquivos ok (md5), membros dos zips ok, 0 falhas** |
| publicar | **pendente, manual**, no navegador, pelo autor (o script não tem essa chamada); antes: leitura de confirmação do rc28 (item 24) |
| scripts | `build/build-pdf.sh` (PDF), `build-package.py` (zips, manifesto, censo, gate), `deposit-v2.0.py` (rascunho, metadata, upload, readback; **sem** chamada de publish) |

Se o texto mudar de novo (rc29): `build-package.py --doi 10.5281/zenodo.23223385` → `--fill` → `--readback`
no **mesmo** rascunho. Nunca `--create-draft` de novo.

## Ordem, cada passo com a sua flag

```
cd paper2-interventional/deposit/paperB
python3 build-package.py --no-doi              # ensaio seco: placeholder mantido, manifesto dry_run; censo 0 lacunas, privacidade 0 achados
python3 deposit-v2.0.py --plan                 # só leitura, sem token: v1.12 ainda é a última versão? metadata que seria gravada
export ZENODO_TOKEN=…                          # deposit:write + deposit:actions
python3 deposit-v2.0.py --create-draft         # ESCREVE: cria o rascunho de nova versão; grava .draft-id-v2.0
python3 build-package.py --doi 10.5281/zenodo.<id>   # troca o placeholder pelo DOI reservado, refaz .md, PDF, zips e manifesto; falha se o placeholder sobrar
python3 deposit-v2.0.py --fill --publication-date AAAA-MM-DD   # ESCREVE: metadata + 6 arquivos, uma chave por vez; termina com readback
python3 deposit-v2.0.py --readback             # só leitura; sai 1 em qualquer divergência
# publicar: manual, no navegador, pelo autor. O script não tem essa chamada.
```

`--import-v112-files` (opcional, no `--fill`) copia os 60 arquivos da v1.12 para o rascunho no servidor.
Por padrão **não** copia: o registro continua na v1.12, e a v2.0 é o relatório.

## O que o readback confere (e por que é duplo)

Forma InvenioRDM **e** forma legada (lição da v1.12: campo ausente da serialização legada é invisível,
não ausente; `publisher` só aparece na RDM).

- `is_draft` True, `is_published` False, DOI = `10.5281/zenodo.<rascunho>`, concept DOI `21964093`,
  `versions.index` = o da v1.12 + 1;
- title = linha 1 do manuscrito; version `2.0`; publication_date preenchida; resource_type, rights,
  publisher `Zenodo`, languages `eng`, subjects iguais aos da v1.12; related_identifiers (OSF `yf7d2` + Paper A `10.5281/zenodo.23163119` (`references`) +
  GitHub no tag `paper2-v2.0`);
- creators **exatamente** os da v1.12 (um nome, uma afiliação, sem identificador);
- description byte a byte igual a `description-v2.0.html`;
- forma legada com o mesmo id, com creators e license;
- arquivos: os 6 novos (md5 local = md5 remoto, status `completed`), nenhum a mais nem a menos (com
  `--import-v112-files`, também os 60 da v1.12 contra os checksums publicados);
- local: `SHA256SUMS` confere, cada membro dos dois zips confere com `MANIFEST-v2.0.json`, e o manifesto
  registra censo 0 lacunas e gate 0 achados.

Saídas locais (gitignored): `.draft-id-v2.0`, `.metadata-v2.0.json`, `.readback-*-v2.0.json`.

## Se algo der errado antes do publish

O rascunho é descartável: `curl -X DELETE -H "Authorization: Bearer $ZENODO_TOKEN"
https://zenodo.org/api/records/<id>/draft`, e apagar `.draft-id-v2.0`. O que **não** é descartável é o publish.
