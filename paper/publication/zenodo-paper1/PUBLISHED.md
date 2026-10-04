# Paper 1 — publicado no Zenodo em 2026-09-07

> **Versão atual: v1.0.2**, DOI [`10.5281/zenodo.23041503`](https://doi.org/10.5281/zenodo.23041503),
> publicada em 2026-09-29 (registro <https://zenodo.org/records/23041503>). Conferido pela API
> logo após o publish: `is_published` true, `is_latest` true, versão 1.0.2, PDF
> `md5:0d4059bf07363980f0de71dde830f149` (332.314 B, igual ao `paper/build/` em `ca83841`),
> único related identifier = o repo memoria-nox. O resto deste arquivo descreve a v1.0.

**DOI: [`10.5281/zenodo.22649269`](https://doi.org/10.5281/zenodo.22649269)**
Concept DOI (sempre a última versão): [`10.5281/zenodo.22649268`](https://doi.org/10.5281/zenodo.22649268)
Registro: <https://zenodo.org/records/22649269>

Conferido **por fora**, não pela tela, logo após o publish:

| checagem | resultado |
|---|---|
| `is_published` / `is_draft` | `True` / `False` |
| provider do DOI | `datacite` — foi cunhado pelo Zenodo |
| `doi.org` resolve | HTTP 302 → Zenodo |
| PDF baixado da URL pública | 353.686 B, `sha256:a984c187…de9e` — **byte a byte igual ao local** |
| data · versão · licença · idioma | 2026-09-07 · 1.0 · CC BY 4.0 · `eng` |
| description | 5.215 B, íntegra, com os seis limitadores |

## 🔴 O defeito que quase publicou um registro SEM DOI

O formulário estava em **"Yes, I already have one"** (`radioGroup=unmanaged`) com o campo
de DOI externo **vazio**. Nesse estado o Zenodo não cunha DOI — o registro sairia sem
identificador, que é exatamente o único propósito do depósito.

Duas lições, e a segunda é a que se repete:

1. **O gate do `deposit.sh` conferia tudo menos a coisa que o depósito existe para
   produzir.** Título, autor, licença, publisher, description, idioma, arquivo e checksum:
   todos verificados. Se um DOI seria emitido: não verificado. Guarda escrito para o
   acessório, cego para o essencial.
2. **Clique executado não é campo alterado.** O primeiro clique foi no `<input>` do radio
   e o React ignorou; o estado continuou `unmanaged`. Só o clique no `<label>` pegou. Se a
   confirmação tivesse sido "cliquei, então está resolvido" em vez de reler o DOM, o
   defeito teria sobrevivido à própria correção.

⚠️ E o diagnóstico foi obtido lendo o rótulo **ligado a cada radio pelo DOM**, não a
captura de tela: em 1456×812 os dois radios ficam no rodapé, cortados, e a bolinha marcada
é indistinguível a olho. Pixel não é estado.

⚠️ Nota honesta sobre o que **não** foi possível provar antes: `pids` no rascunho
permanecia `{}` mesmo depois da correção, porque o DOI só é cunhado no publish. A
correção eliminou o estado em que ele certamente **não** sairia; que ele sairia só ficou
provado depois, pelo readback acima.

## Reabrir para corrigir metadados

Arquivos são imutáveis. Metadados não:

    TOK=$(tr -d '\r\n' < ~/.config/secrets/ZENODO_TOKEN)
    # cria/abre o rascunho de EDIÇÃO do registro publicado (não é versão nova)
    curl -X POST -H "Authorization: Bearer $TOK" \
      https://zenodo.org/api/records/22649269/draft

Depois um `PUT` no mesmo endpoint e um `POST .../draft/actions/publish`. **Não** cria DOI
novo. Para trocar o **arquivo** seria preciso versão nova — e versão nova é DOI novo e
permanente.

## O que este DOI não resolve

O arXiv **não aceitou** o manuscrito em 2026-09-03, e a condição que invocou é endosso de
*journal*. **Nenhum DOI de repositório satisfaz aquela condição.** A apelação é ativo de
uso único e, negada, é permanente — não gastar com este DOI na mão. O caminho é o §6 como
paper próprio para a TMLR.

## v1.0.3 — publicada 2026-10-04

- Registro **23130276**, DOI da versão **`10.5281/zenodo.23130276`** (conceito `10.5281/zenodo.22649268`, que agora resolve para ela).
- Arquivo único `paper-tecnico-nox-mem.pdf`, 73 páginas, `md5:c18493679afd999c698c2f3492a5bcbb`, conferido pela API pública depois do publish; `doi.org` responde 200.
- Rascunho criado e preenchido por `deposit-v103.py` (nova versão a partir da v1.0.2 publicada, metadados normalizados para o shape RDM, ORCID no autor, bloco "What changed in v1.0.3"); o botão Publish foi do Toto.
- Conteúdo: partes A–G do `paper/CHANGELOG.md` (declaração de uso de IA generativa, retirada da linguagem de produto, correções verificadas contra artefatos e fontes, auditoria completa, revisão Fable, revisão de regressão do Codex). Nenhum resultado de manchete mudou.

**Atualização da nota abaixo (2026-10-04):** o Toto decidiu usar a apelação do arXiv com esta versão, porque a rota TMLR ficou bloqueada (sem acesso). A carta está fora do repositório público.
