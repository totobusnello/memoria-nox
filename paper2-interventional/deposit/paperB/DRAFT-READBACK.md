# Paper B v2.0 — procedimento do rascunho no Zenodo (NADA criado ainda)

| campo | valor |
|---|---|
| base | record **22110203** (v1.12, publicado 2026-08-26T12:01Z) — `POST /api/records/22110203/versions` |
| concept DOI | `10.5281/zenodo.21964093` (não muda) |
| versão proposta | `2.0` (ver READY.md, decisão 1) |
| DOI | reservado só quando o rascunho for criado; não existe ainda |
| scripts | `build/build-pdf.sh` (PDF), `build-package.py` (zips, manifesto, censo, gate), `deposit-v2.0.py` (rascunho, metadata, upload, readback; **sem** chamada de publish) |

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
