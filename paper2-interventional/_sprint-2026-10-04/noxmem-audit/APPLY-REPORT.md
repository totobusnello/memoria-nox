# APPLY-REPORT — auditoria do paper nox-mem aplicada (v1.0.3, parte E)

Data: 2026-10-04. Escopo: os 203 achados verificados das fatias S01–S13 (sem S06), aplicados a
`paper/paper-tecnico-nox-mem.md`, com espelho em `paper/abstract.md` e
`paper/publication/supplement-wave2-and-cross-backbone.md`. Nenhum comando git. Nada publicado
no Zenodo. Ninguém contatado.

## 1. Resultado

| Item | Estado |
|---|---|
| Achados aplicados ao manuscrito | 203 de 203 (com fusões onde dois achados tocavam a mesma frase) |
| Sub-pedidos não aplicados | 2 (ver §4) |
| `python3 paper/claims_check.py` | `ok — 21 guardas passaram; 6 alegações retratadas` |
| `python3 paper/claims_check_mutation_test.py` | `ok — 49 mutações mordidas com o marcador certo, controle negativo silencioso` |
| Densidade (piso 2,06) | 59 obras / 28.142 palavras = **2,0965** por mil |
| `scripts/build-paper.sh` | PDF gerado, 79 páginas, linha 4 = `Version v1.0.3 (2026-10-03)` |
| MD5 do PDF | `f849896d3aa4373dd3d423a2153e9d36` (antes: `d16f4f423a1d40f220a6c1a804e14ae0`) |
| Zenodo rascunho 23130276 | PDF trocado; readback do script: `readback OK — nada divergente`, `published: False`, `status: new_version_draft`, checksum `md5:f849896d3aa4373dd3d423a2153e9d36` |
| Carta (`noxmem-apelacao-pacote.md`) | MD5 trocado nos 5 lugares operativos; 3 frases da carta atualizadas; contagem recontada (1.141 palavras / 7.285 caracteres) |
| Relatório de paridade numérica | `noxmem-audit/NUMBER-PARITY-v102-to-v103E.md` |

## 2. Arquivos tocados

- `paper/paper-tecnico-nox-mem.md` — 257 substituições exatas (cada uma com contagem conferida antes de
  aplicar) + 3 mudanças estruturais (ver §3).
- `paper/abstract.md` — 4 frases (SQLite por store; "nox-mem and Mem0 split"; frase do EverOS; F_MH
  6,02% vs 10,84%).
- `paper/publication/supplement-wave2-and-cross-backbone.md` — 42 correções in place das mesmas frases
  + nova entrada "Erratum (paper v1.0.3, part E)" com os itens (4)–(12).
- `paper/publication/supplement-operational-appendices.md` — nova seção §S3.5 com os três parágrafos
  de medição da §3.5, sem alteração.
- `paper/CHANGELOG.md` — v1.0.3 **parte (E)**, com cada mudança por seção.
- `paper/refs.bib` — LightRAG (Findings of EMNLP 2025, pp. 10746–10761); Gemini Embedding vira o paper
  arXiv:2503.07891; entradas novas MeMo (2605.15156), HyperMem (2604.08256), Clark & Gardner (1710.10723).
- `paper/bibitem-census.json` — obras 55 → 59 (`clarkgardner`, `hypermem`, `quati`, `gbrain`), com
  registro datado do motivo.
- `paper/q4-corridas-census.json` — template do sítio `titulo-631` acompanha o novo título do §6.3.1.
- `paper/authors-manifest.json` — regenerado por `gen-authors-manifest.py` (56/56 IDs resolvidos,
  controle positivo 1809.09600 OK).
- `paper/claims_check_mutation_test.py` — uma âncora atualizada (a footnote do BM25 mudou de "§3.1"
  para "§1.5 and §2.2"; sem isso a mutação não testava nada).
- `paper/build/paper-tecnico-nox-mem.pdf` (+ `.tex`) — rebuild.
- `paper/publication/zenodo-paper1/deposit-v103.py` — bloco V103 reescrito (inclui a auditoria) e o
  mecanismo de uma frase herdada (`STRICT_OLD`) trocado por uma lista de 6 frases herdadas da descrição
  da v1.0.2 que agora estavam erradas (SQLite único, "operator-assigned", "March 14", comparação
  cross-backbone dos 63,28%, F_MH "3–7% vs 18.88% strict EM", e a frase nova do EverOS). Cada uma
  exige ocorrência 1x, senão o script para.
- `paper2-interventional/_sprint-2026-10-04/noxmem-apelacao-pacote.md` — ver §6.

Backups pré-edição de todos esses arquivos em
`/private/tmp/claude-501/-Users-lab-Claude-Projetos-memoria-nox/de3857d1-533c-4471-8b2a-ae1c53eff923/scratchpad/apply/`.

## 3. Decisões que você deve conhecer

1. **Densidade.** As correções somaram ~2.200 palavras e derrubaram a densidade para 1,972 (abaixo do
   piso 2,06). Fechei por dois caminhos, ambos registrados no CHANGELOG (E):
   - quatro obras de terceiro que o texto passou a citar (ou já citava inline sem footnote) ganharam
     footnote: Clark & Gardner (baseline original do HotpotQA), HyperMem (F4), Quati (F7, já estava no
     `refs.bib`), relatório gbrain-evals (§5.6). 55 → 59;
   - os três parágrafos de medição da §3.5 (diversity term D2, ~850 palavras) foram para
     `supplement-operational-appendices.md` §S3.5, sem alteração; a §3.5 ficou com um resumo de ~190
     palavras com os mesmos números (83 chunks / 46,8k serves, 931, 146 → 67 → 3, **184 of 184**, que a
     §5.1.3 cita). O bloco do smoke com teto de 500 na §6.6 foi comprimido.
   Se você preferir não mover a §3.5, a alternativa é cortar ~1.230 palavras em outro lugar.
2. **Conflitos entre fatias, resolvidos pelo código (S04).** S01 pedia "pain drifting upward with
   repeated retrieval" e S03 "co-occurrence rule", "batch reflect", "crystallize no nightly schedule";
   S04 mostrou no fonte que nada disso existe (`inferPain()` só no ingest; `reflect` não grava em
   `chunks`; `consolidate.ts` não chama reflect/crystallize). Prevaleceu S04 em todas as frases.
3. **Mem0 4 chunks (S09 × S12).** S12 dizia "nenhum chunk perdido" (store final); S09 mostrou pelos
   `created_at` que os 4 foram reinseridos às 15:02 UTC, depois do fim da corrida (14:57:04). Usei S09:
   6.826 linhas no momento da consulta.
4. **RSS da Table 2 (S10/S11 × S12).** S10/S11 mantinham 341 MB corrigindo "6830 chunks"; S12 pedia
   399 MB. Usei 399 MB (2026-05-29, artefato versionado), cabeçalho ~12× → ~10×, e 341 MB fica como
   leitura anterior a ~62k chunks.
5. **Latência do rerank (S05 × S08).** Dois artefatos: `RESULTS-PHASEG-5BATCH.md` ("~3.7 s p50 vs ~1.1 s")
   e `RESULTS-PHASEG.md` (batch 004: 1.109 → 4.783 ms, +3.674). Usei o segundo, que tem os números.
6. **Frase "the two systems of the 2026-06-15 run" (S01).** Estava errada (agentmemory também rodou) e
   disparou a guarda de contagem; ficou "the leaders of the 2026-06-15 run".
7. **Guardas.** Duas frases com o nome de arquivo `RESULTS-PRODUCTION-SOTA.json` + "nox-mem" na mesma
   frase disparavam o `superlativo_check` (casa "SOTA" no nome do arquivo); reescrevi apontando para o
   artefato do §5.7.1.

## 4. Não aplicado

- **S10 (categoria LoCoMo):** o pedido de corrigir `LOCOMO_CATEGORY_MAP` em
  `eval/q4-comparison/lib/category_labeler.py` e regenerar `output/rc4/_aggregate.md` — fora de
  `paper/`, que é o que a tarefa me permite editar. A tabela do §6.4 foi recalculada com o mapa
  corrigido pelo auditor, e o paper agora diz que o labeler do repositório ainda tem o mapa antigo.
- **S12, troca de "Three" por "Four" knobs na §5.1.8:** apliquei a versão S05 da mesma frase (§5.1.9:
  "Lab Q1 standalones (§5.1.8) and a separate MAP run"), que não afirma que o MAP é knob do Lab Q1.

Fora do pedido, deixados como estavam e anotados: `abstract.md` §2 já tinha 2.148 caracteres antes
desta passada (a nota do §4 dele diz 1.909 ≤ 1.920), agora ~2.270; `arxiv-metadata.txt` e
`publication/techrxiv-metadata.md` não foram espelhados.

## 5. Números que mudaram

Tabela completa (antigo → novo → motivo → fonte) em `NUMBER-PARITY-v102-to-v103E.md`, seção 1
(57 linhas); a seção 2 traz o censo mecânico de tokens numéricos v1.0.2 → A–D → E. Os principais:
F_MH 3–7% vs 18,88% → 6,02% vs 10,84% (mesmo backbone); EX(SA) 49,70 → 49,80; IRCoT 35,80 → 36,50;
DPR+FiD 65–72% removido; Mem0 66,88% = J, não F1; CI Phase H v2 [49,88, 53,49] → [49,87, 53,48];
tabela §6.4 recalculada (single-hop 997 / multi-hop 415 / temporal 454 / open-domain 92); smoke
0,6380 → 0,4509 e 0,8569 → 0,1315; mem0@500 LoCoMo-only 0,1315 → 0,2631; RSS 341 → 399 MB, 415 → 399 MB,
~414 → 423 MB; overstatement 3–6× → 1,27–5,8×.

Não mudaram: 63,28% / +4,01 pp, 63,77% / +4,50 pp, 51,68% / +9,13 pp, 88,42% / +1,72 pp, os nDCG@10 do
§6.3 / §6.3.2 / §6.3.3 / §6.3.4, 0,6237, 99,86%, KG path 2,5 ms p50, 399 MB idle.

## 6. Carta

- MD5 `d16f4f…ae0` → `f849896d3aa4373dd3d423a2153e9d36` nas linhas operativas (marcadores da §3.3,
  linha "Attached:", e os passos 6 e 7 do checklist). A nota histórica de 2026-10-04 (madrugada) que
  registra a transição `06490d…` → `d16f…` ficou como estava, porque é registro.
- `Pages: 76` → `Pages: 79` no checklist.
- Frases da carta que citavam algo que mudou: "All memory lives in one SQLite database" → "Each memory
  store is one SQLite database file"; "operator-assigned severity field" → "operator-assignable …,
  otherwise fixed at ingest by a keyword rule"; marcador novo no item 4 ("4 October 2026, audit
  corrections"). A carta continua sem travessões, asteriscos, colchetes, chaves ou `|`.
- As frases do item 3 seguem verdadeiras, medidas agora no corpo do manuscrito: §2–§6 = 19.556 de
  25.361 palavras (77%, "more than two thirds"); §1.4–§1.5 = 2.327 (9,2%, "less than a tenth").
- Nota nova no topo ("Atualização 2026-10-04 (auditoria, parte E)") e contagem recontada.

Atenção: `curl https://zenodo.org/api/records/23130276` responde 404 ("persistent identifier is not
registered") enquanto o rascunho não for publicado, então o último comando do passo 6 só confere
depois do seu clique em Publish. E o aviso do checklist vale: qualquer rebuild muda o MD5.

## 7. Fontes externas que eu mesmo abri nesta passada

- API do arXiv (`https://export.arxiv.org/api/query?id_list=1710.10723,2604.08256,2605.15156,2503.07891`):
  1710.10723v2 *Simple and Effective Multi-Paragraph Reading Comprehension*, Clark & Gardner;
  2604.08256v2 *HyperMem: Hypergraph Memory for Long-Term Conversations*, Yue, Hu, Sheng, Zhou, Zhang,
  Liu, Guo, Deng; 2605.15156v2 *MeMo: Memory as a Model*, Quek … Solar-Lezama; 2503.07891v1 *Gemini
  Embedding: Generalizable Embeddings from Gemini*, Lee, Chen, Dua et al.
- `https://arxiv.org/abs/<id>` para os 56 IDs do manuscrito, via `gen-authors-manifest.py`.
- `https://zenodo.org/api/records/23041503` (descrição publicada da v1.0.2, para achar as frases herdadas).

As demais verificações externas (Tabela 4 do EverMemBench, Mem0 J, MuSiQue/IRCoT/Beam/HotpotQA, Self-Ask,
WebCoach, ReasoningBank, Context-Bench da Letta, tamanho do MiniLM no Hugging Face, gbrain-evals) são as
dos auditores, citadas nos achados; não as reabri. O valor 10,84% (MemOS, F_MH, Gemini-3-Flash) vem do
achado S01, que abriu `arxiv.org/html/2602.01313` (v3).
