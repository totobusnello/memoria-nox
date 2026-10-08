# Paper B v2.0 — pacote de depósito: rc28, no rascunho 23223385 (DOI reservado), readback OK; publicar = manual

Atualizado 2026-10-07 (rc28). Rascunho Zenodo **23223385** criado (DOI reservado `10.5281/zenodo.23223385`), preenchido
com o pacote do rc28 (`--fill --publication-date 2026-10-07`) e conferido (`--readback`: 19 campos, 6 arquivos, 0 falhas,
2026-10-07T23:59:25Z). **Não publicado**: publicar é manual, no navegador, pelo autor. Nenhuma escrita git, nenhuma voz,
nenhuma VPS nesta rodada; no Zenodo só `--fill`/`--readback` no rascunho existente e GETs públicos.

O pacote atual é **final** (não seco): placeholder trocado nas 2 ocorrências, DOI 2× no .md e 3× no PDF, manifesto
`dry_run: false`.

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
7. **rc28 = achados das leituras finais do pacote rc27** (Grok NO-GO, recibo `adversary-receipt-grok-2026-10-07T181540-7884.txt`;
   Fable NO-GO, agente sem recibo; Codex não rodou, exit 1, sem créditos). Todos verificados contra texto, artefatos e API
   pública do Zenodo; aplicados no rc28 e na descrição (`APPLY-B-rc28.md`). Título novo (decisão do autor): *"A registered
   horizon that outlived the intervention the trial ran: …"*. Versões publicadas do concept (API): **1.9** (21964094,
   2026-08-17), **1.11** (21978476, 2026-08-17; a 1.10 nunca foi depositada), **1.12** (22110203, 2026-08-26); snapshot em
   `B-rc28/zenodo-21964093-versions.json`.


## Texto

| | |
|---|---|
| fonte | `_sprint-2026-10-04/B-v2-rc28.md`, sha256 `449d4dec…` (fixado no `build-package.py`, `PLACEHOLDER_COUNT = 2`) |
| depositado | `registered-horizon-outlived-intervention-v2.0.md` = rc28 com as 2 ocorrências do placeholder trocadas por `10.5281/zenodo.23223385` (única diferença, registrada no manifesto) |
| parity rc27→rc28 | `B-rc28/parity-rc28.py` **PASS**; self-test **21/21** mutações pegas, cada uma pela própria perna; rc28 sem mutação passa |
| o que a parity rc28 prova | (A) rc28 com os 16 hunks declarados revertidos e sem o bloco rc28 é **byte a byte** o rc27; (N) todo número novo declarado e achado na fonte; (B) o check inteiro do rc27 (sha fixado) dá **exatamente** as 82 falhas declaradas; (C) título, versões do cabeçalho = snapshot da API, sham da janela como contrafactual `w = 4`, nenhuma redação rc27 que punha a janela em "what was served", item 8 sem data, item 24 sem leitura Codex alegada, recibos presentes e limpos, placeholder 2× = build, build aponta o rc28; (E) a descrição; (D) changelog 149..222 |
| efeito colateral | `parity-rc24/25/26/27.py`, rodados sozinhos, agora falham **só** no lock ambiental S24/X5 (`receipts/` tem 25, não 23: os 2 recibos desta rodada) |
| PDF | **77 páginas**, 0 glifos ausentes, 91 trechos riscados, figuras B1 e B2 |

## O que está no rascunho (6 arquivos, 18.859.392 bytes)

| arquivo | bytes |
|---|---:|
| `…-v2.0.md` | 342.244 |
| `…-v2.0.pdf` | 912.759 |
| `artifacts-v2.0.zip` | 17.082.846 (307 membros: + `APPLY-B-rc28.md`, os 2 recibos novos, `B-rc28/zenodo-21964093-versions.json`) |
| `scripts-v2.0.zip` | 387.600 (67 membros: + `B-rc28/parity-rc28.py`) |
| `MANIFEST-v2.0.json` | 133.459 |
| `SHA256SUMS` | 484 |

## Gates (rodados no rc28, com `--doi 10.5281/zenodo.23223385`)

- **Censo: 296 citados, 0 lacunas** (277 no pacote, 2 só no repositório público, 17 declarados).
- **Privacidade: 0 achados** em todo byte empacotado; 11 coincidências liberadas por já estarem em `origin/main`.
- **Redação:** 27 cópias (`SCRUBBED.txt`); os recibos novos já entram limpos (host e caminho de home redigidos).
- **Placeholder:** 0 sobrando; DOI 2× no .md, 3× no texto do PDF.
- **Readback:** 19 campos ok (título de 145 caracteres = linha 1), 6 arquivos md5 ok, membros dos zips ok.

## Ainda abertas (suas)

1. **Leitura de confirmação do rc28** — o item 24 e o cabeçalho a declaram planejada antes da publicação; não rodou.
   Codex não leu nenhuma versão do pacote (sem créditos).
2. **Publicar** à mão (`https://zenodo.org/uploads/23223385`). Se o texto mudar: rc29 → `build-package.py --doi
   10.5281/zenodo.23223385` → `--fill` → `--readback` no mesmo rascunho.
3. **Tag `paper2-v2.0`** do link GitHub ainda não existe: PR + tag no commit depositado (escrita git, sua).
4. **Lastro:** rc24–rc28, `parity-rc25..28.py`, os derivados e o pacote não estão no manifesto do lastro.
5. Cosmético conhecido: overfull boxes em tabelas largas; legendas "Figure 1: Figure B1".
