# Checklist do depósito no Zenodo (telemetria por fase)

Este arquivo fica fora do upload. O pacote está pronto, mas nada foi reservado, enviado ou
publicado. Todos os caminhos abaixo são relativos a
`paper2-interventional/_sprint-2026-10-04/stanford-deposit/`.

## Antes de começar: decisões que só você toma

Estas decisões vêm do AUDIT.md §8 e continuam em aberto:

- [ ] **Gate do Omri.** Sua decisão registrada em 12/09 é "DOI só quando ele responder". Se ela
      continua valendo, pare aqui.
- [ ] **Acesso.** Público (o default em `zenodo-metadata.json`) ou com embargo. As opções de
      embargo estão em `zenodo-metadata.draft-notes.json`.
- [ ] **Resolução do `timestamp_ms`.** Fica em milissegundos (o pacote atual). Se você quiser
      arredondar para minuto, os CSVs mudam e a auditoria inteira precisa ser refeita.
- [ ] **Relações em `related_identifiers`.** Hoje: `references` para o arXiv:2606.06448 e para o
      Paper 1 v1.0.2 (`10.5281/zenodo.23041503`), e `issupplementedby` para o repositório
      `github.com/totobusnello/memoria-nox`. O README não aponta mais para o repositório (o script
      de verificação agora vai dentro do pacote), então vale decidir se essa terceira relação fica.
- [x] Licença: CC BY 4.0 (decidido por você em 03/10).

## Passo a passo

1. **Conferir o pacote local.**
   ```sh
   cd payload && python3 verify_dataset.py
   ```
   O resultado esperado é `mismatches=0 ... sha256sums_errors=0`, com exit 0.

2. **Criar o rascunho no Zenodo** (New upload), sem subir arquivo nenhum ainda. Preencha os
   campos a partir de `zenodo-metadata.json`: tipo `Dataset`, título, autor com ORCID
   `0009-0007-5911-8141` e afiliação "Independent Researcher", descrição, licença CC BY 4.0,
   palavras-chave, identificadores relacionados, versão `1.0.0`, idioma inglês e a data de
   coleta `2026-08-07/2026-09-07`. A data de publicação fica `<<DATA DE PUBLICAÇÃO>>` no JSON.
   No formulário, use a data do dia em que você publicar. Os campos `_...` estão em
   `zenodo-metadata.draft-notes.json` e não vão para o Zenodo.

3. **Reservar o DOI** ("Reserve DOI") e copiar o DOI reservado (`10.5281/zenodo.NNNNNNNN`). Ele é
   o DOI desta versão.

4. **Preencher `<<DOI>>` no README.** São duas ocorrências: a linha de versão no topo e a
   citação.
   ```sh
   cd payload
   sed -i '' 's#<<DOI>>#10.5281/zenodo.NNNNNNNN#g' README.md
   grep -n '<<' README.md      # não pode sair nada
   ```

5. **Regenerar o `SHA256SUMS` por último**, porque o README mudou no passo 4.
   ```sh
   shasum -a 256 README.md LICENSE.txt verify_dataset.py \
     provider_telemetry_2026-08-07_2026-09-08.csv row_annotations.csv \
     phase_summary.csv daily_phase_summary.csv > SHA256SUMS
   python3 verify_dataset.py   # exit 0, sha256sums_errors=0
   ```
   Os quatro CSVs têm que manter os hashes que já estão no `SHA256SUMS` de hoje. Só as linhas
   do `README.md` podem mudar.

6. **Rodar a varredura de privacidade de novo** (opcional, mas recomendado):
   ```sh
   cd ../../..   # pasta paper2-interventional/
   python3 measurement/sprint-stanford-telemetry-deposit.py --deposit _sprint-2026-10-04/stanford-deposit
   gitleaks detect --no-git --source _sprint-2026-10-04/stanford-deposit/payload
   ```
   O primeiro tem que imprimir `privacy findings=0` e o segundo, `no leaks found`.

7. **Subir apenas os 8 arquivos de `UPLOAD-LIST.txt`**, todos de dentro de `payload/`:
   `README.md`, `LICENSE.txt`, `SHA256SUMS`, `verify_dataset.py` e os quatro CSVs.
   **Não suba** `AUDIT.md`, `_audit/`, `zenodo-metadata.json`,
   `zenodo-metadata.draft-notes.json`, `UPLOAD-LIST.txt` nem este checklist. Esses arquivos
   têm caminhos internos, histórico de correspondência e a lista de nomes que a varredura
   procura.

8. **Conferir no Zenodo antes de publicar:**
   - [ ] a lista mostra exatamente 8 arquivos, com os mesmos nomes do `UPLOAD-LIST.txt`;
   - [ ] o md5 de cada arquivo bate com o local (`md5 -r payload/*`);
   - [ ] o preview padrão é o `README.md` e o DOI aparece nele;
   - [ ] a licença é CC BY 4.0, a versão é 1.0.0 e os identificadores relacionados estão como
         você decidiu;
   - [ ] se você usou a API: releia cada campo no formato RDM depois do PUT, porque um PUT
         descarta em silêncio os campos no formato legado.

9. **Publicar.**

10. **Só depois de publicar**, abra o link do DOI e confirme que ele resolve. Um DOI reservado
    devolve 404 até a publicação. Só então use o link em qualquer mensagem.
