# Paper B v2.0 — pacote de depósito: ENSAIO SECO (`--no-doi`), nada enviado

Atualizado 2026-10-07 (rc27). Nenhuma chamada à API do Zenodo, nenhum rascunho, nenhuma escrita git, nenhuma voz,
nenhuma VPS. Tudo o que foi escrito está em `deposit/paperB/` e em `_sprint-2026-10-04/` (rc27, `B-rc27/`).

⚠️ O pacote atual é **ensaio seco**: o texto e o PDF ainda levam o placeholder `[VERSION-DOI]` (2×: cabeçalho e item 8 da lista de trabalho), e o manifesto diz
`dry_run: true`. **Não é para depositar.** Depois de `--create-draft`: `python3 build-package.py --doi 10.5281/zenodo.<id>`
(troca o placeholder, refaz .md, PDF, zips, manifesto e SHA256SUMS; troca **toda** ocorrência; sai 1 se o placeholder sobrar no .md ou no PDF, ou se o DOI não
aparecer exatamente 2× no .md e 3× no texto do PDF).
`deposit-v2.0.py --fill`/`--readback` recusam pacote seco ou feito com DOI diferente do reservado.

## Decisões do autor (tomadas pela sessão principal em nome do autor, 2026-10-07)

1. **rc26 = só o cabeçalho.** O texto depositado não diz mais "STATUS: DRAFT", "has not been reviewed" nem "still not
   done: deposit": diz que é a versão 2.0 do registro do pré-registro (concept DOI do snapshot da v1.12), que o texto foi
   lido inteiro por duas famílias de modelo com GO (Fable no rc23 e no diff rc23→rc24; Codex no rc23, recibo em
   `receipts/`), e o DOI da versão como placeholder `[VERSION-DOI]`. Nada mais muda no texto; changelog item 207.
1b. **rc27 = só a lista de trabalho** (+ changelog 208–210). Fechada como a lista fecha itens: título riscado, histórico
   mantido, nota datada rc27. Item 8 → "deposited as version 2.0 of the registration record, version DOI
   `[VERSION-DOI]`" (o **mesmo** token; o build troca as 2 ocorrências). Item 24 → rc24 teve o diff check do Fable (GO);
   rc25 (redação) e rc26 (cabeçalho) sem leitura própria, cada um com parity; "The deposited package gets a final read
   by Grok, Codex and Fable before publication" (**planejada, não feita**). Outras linhas que liam como abertas: 21
   (revisão do rc9) fechado como superado pelas leituras do rc10; 11 (§4.7) fechado como lacuna declarada (9.991 sem
   artefato, §4.7/B.1); 13 (M10, perna sem os três parciais) fechado como não computado (§4.6, §5); notas em 6, 7
   (Behnam & Wang / MemoryArena v2: **não feitos**, são para submissão, não para este depósito), 14, 16 e 19.
2. **related_identifiers:** acrescentado o Paper A v1.1 `10.5281/zenodo.23163119`, relação `references`
   (`resource_type` publication-preprint). Escolha: o registro do próprio Paper A usa `references` para o link ao OSF, e
   `isSupplementedBy` fica, como na v1.12, para o link de software. Creators, ORCID (nenhum) e keywords = v1.12.
3. **Arquivos da v1.12:** não importados (padrão mantido).
4. **Descrição:** diz que esta versão é também a emenda agrupada do registro (declara todo desvio, Apêndice A, e o
   resultado, num registro só); a frase "It does not amend the registration" saiu. Cita o Paper A.
5. **Vereditos do painel:** cópia derivada sem `reason` e sem `detail` (os dois campos de texto livre), em
   `_derived/panel-verdicts/` do `artifacts-v2.0.zip`; mantidos episode_id, panelist, family, model, model_served,
   verdict, level, status, stop_reason, attempts. **As linhas de origem não têm timestamp**, então não há timestamp a
   manter. Só no MANIFEST e na descrição; o manuscrito não mudou por isso.
6. `p2-serving.ndjson` fica; `~/` fica como está.

## Texto

| | |
|---|---|
| fonte | `_sprint-2026-10-04/B-v2-rc27.md`, sha256 `cb38c5cf…` (fixado no `build-package.py`, com `PLACEHOLDER_COUNT = 2`) |
| depositado | `registered-horizon-outlived-intervention-v2.0.md` = rc27 byte a byte no modo `--no-doi`; com `--doi`, rc27 com as 2 ocorrências do placeholder trocadas (única diferença, registrada no manifesto) |
| parity rc26→rc27 | `B-rc27/parity-rc27.py` **PASS**; self-test **20/20** mutações pegas, cada uma pela própria perna; rc27 sem mutação passa; `parity-rc26.py` e `parity-rc25.py` ainda passam |
| o que a parity rc27 prova | (A) rc27 sem a lista de trabalho e sem o bloco rc27 é **byte a byte** o rc26 (cabeçalho e corpo intocados); (H) na lista, rc26→rc27 é **só inserção** (tirando os `~~`), e toda inserção é nota datada rc27; (B) o check inteiro do rc26 (sha fixado) rodado rc24/rc25→rc27 dá **exatamente** as 20 falhas declaradas; (C) placeholder 2× = `PLACEHOLDER_COUNT` do build (1 no cabeçalho, 1 no item 8, 0 no changelog), item 8 com a versão do build, item 24 com as frases exigidas e **sem** afirmar a leitura final como feita, todo título riscado, nenhuma linha lendo como aberta sem fechamento, e controle positivo: o detector acha no rc26 exatamente os itens 6, 7, 8, 11, 13, 14, 16, 19, 21, 24; (D) changelog 149..210 |
| o que a parity rc26 prova | (A) rc26 sem o cabeçalho e sem o bloco rc26 é **byte a byte** o rc25; (B) o check inteiro do rc25 (sha fixado) rodado rc24→rc26 dá **exatamente** as 54 falhas declaradas, todas do cabeçalho reescrito ou do item 207, nenhuma a mais nem a menos; (C) cabeçalho: placeholder 1×, sem DRAFT/not done/not been reviewed, DOIs = snapshot da v1.12, recibo Codex `exit: 0`, veredito GO, versão = `VERSION` do build, fatos herdados (9.991, 11.812 estados, `job-janela2`, 21/21); (D) changelog 149..207 |
| PDF | **74 páginas**, 0 glifos ausentes, 90 trechos riscados, figuras B1 e B2 embutidas |

## O que vai para o Zenodo (6 arquivos, 18.820.556 bytes ≈ 17,9 MiB)

| arquivo | bytes | conteúdo |
|---|---:|---|
| `…-v2.0.md` | 334.847 | o manuscrito (= rc27) |
| `…-v2.0.pdf` | 902.762 | o mesmo texto em PDF |
| `artifacts-v2.0.zip` | 17.076.754 | 303 membros: os 300 de antes + `_derived/panel-verdicts/` (2 JSONL sem texto livre, 3.592 + 1.195 linhas, e `SANITIZED.json` com sha256 de origem e derivado e contagem de rótulos) |
| `scripts-v2.0.zip` | 374.130 | 66 membros: os 63 de antes + `B-rc26/parity-rc26.py` + `B-rc27/parity-rc27.py` + `deposit-paperB/sanitize-verdicts.py` |
| `MANIFEST-v2.0.json` | 131.579 | como antes, mais `record.doi`/`dry_run`, `manuscript.placeholder`/`placeholder_count`, `derived` |
| `SHA256SUMS` | 484 | sha256 dos outros 5 |

## Gates (rodados de novo no rc27)

- **Censo: 291 citados, 0 lacunas** (272 no pacote — os 3 novos são as parity rc25/26/27 que o item 24 cita —, 2 só no repositório público, 17 declarados com motivo).
- **Privacidade: 0 achados** em todo byte empacotado, incluindo os 3 arquivos derivados. Controle positivo 25/25 e 5/5;
  11 coincidências liberadas por já estarem em `origin/main`.
- **Redação:** 27 cópias, como antes (`SCRUBBED.txt`).
- **Placeholder:** no modo seco, 2× no .md e 2× no texto do PDF (o build exige exatamente `PLACEHOLDER_COUNT`); no teste
  com DOI falso `10.5281/zenodo.99999999` o build trocou as 2 no .md, 0 sobraram, o PDF trouxe o DOI 3× (cabeçalho, item 8
  e linha de data), gates verdes, `dry_run: false`; depois o pacote foi refeito em `--no-doi`.

## Ainda abertas (suas)

1. **Leitura final do pacote depositado por Grok, Codex e Fable** — o item 24 a declara como planejada, antes da
   publicação; ainda não rodou. rc25, rc26 e rc27 seguem sem leitura própria (só parity).
2. **Cabeçalho não foi tocado no rc27** (pedido: só lista + changelog): ele ainda diz "rc3 to rc26" e "rc26 changes only
   this header", e não menciona o rc27. Verdadeiro, mas incompleto; se você quiser "rc3 to rc27", é um rc28 só de cabeçalho.
3. **Tag `paper2-v2.0`** do link GitHub ainda não existe: PR + tag no commit depositado (escrita git, sua). Tudo do B
   depois do rc22 segue *untracked*.
4. **Lastro:** rc24–rc27, `parity-rc25/26/27.py`, os derivados e o pacote não estão no manifesto do lastro.
5. Cosmético conhecido: overfull boxes em tabelas largas; legendas "Figure 1: Figure B1".

## Ordem do depósito

`build-package.py --no-doi` (feito) → `deposit-v2.0.py --plan` → `--create-draft` → `build-package.py --doi <reservado>`
→ `--fill --publication-date AAAA-MM-DD` → `--readback` → publicar à mão. Detalhe em `DRAFT-READBACK.md`.
