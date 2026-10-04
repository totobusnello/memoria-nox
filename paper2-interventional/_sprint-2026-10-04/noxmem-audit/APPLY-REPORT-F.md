# APPLY-REPORT-F — revisão final + fatia S06 aplicadas (v1.0.3, parte F)

Data: 2026-10-04. Escopo: os 12 achados CONFIRMADOS de `REVIEW-FINAL.md` (Kimi k3 + Codex gpt-6-astra) e os
21 achados verificados da S06 (§5.2–§5.4), aplicados a `paper/paper-tecnico-nox-mem.md`, com espelho no
supplement, em `abstract.md`, `arxiv-metadata.txt` e `publication/techrxiv-metadata.md`. Nenhum comando git.
Nada publicado no Zenodo. Ninguém contatado. Backups pré-edição em
`/private/tmp/claude-501/-Users-lab-Claude-Projetos-memoria-nox/de3857d1-533c-4471-8b2a-ae1c53eff923/scratchpad/applyF/`
(script das 45 substituições do manuscrito: `edit_paper.py`, cada uma com contagem exata conferida antes).

## 1. Resultado

| Item | Estado |
|---|---|
| REVIEW-FINAL, 12 confirmados | 12 de 12 aplicados (as duas MEDIUM incluídas) |
| S06, 21 achados | 21 de 21 aplicados (um com variante: FE2H mantido, frase corrigida) |
| `python3 paper/claims_check.py` | `ok — 21 guardas passaram; 6 alegações retratadas` |
| `python3 paper/claims_check_mutation_test.py` | `ok — 49 mutações mordidas com o marcador certo, controle negativo silencioso` |
| Densidade (piso 2,06) | 59 obras / 28.623 palavras = **2,0613** por mil (antes: 28.142 → 2,0965). Folga: 17 palavras |
| `scripts/build-paper.sh` | PDF gerado, **81 páginas** (eram 79), 347.996 bytes, linha 4 = `Version v1.0.3 (2026-10-03) — changelog in paper/CHANGELOG.md`, sem aviso de glifo; `.tex` regenerado com `--tex-only` (PDF intacto) |
| MD5 do PDF | **`05335e7afc3819532cb86278752ef05f`** (antes: `f849896d3aa4373dd3d423a2153e9d36`) |
| Zenodo, rascunho 23130276 | `deposit-v103.py` rodado: `readback OK — nada divergente`, `published: False`, `status: new_version_draft`, checksum `md5:05335e7afc3819532cb86278752ef05f`. Bloco V103 ganhou um item (revisão final) |
| Carta | MD5 trocado nos 5 lugares operativos; `Pages: 81`; uma frase nova no item 4; nota de atualização da parte F; recontagem 1.182 palavras / 7.551 caracteres, sem `*`, `_`, `[]`, `{}`, `|` nem travessão |
| Abstract arXiv (≤ 1.920) | ver §3 |

## 2. O que mudou, por achado

**REVIEW-FINAL (12).**
1. MEDIUM §8 × §6.7: o §8 dizia "is met, but weakly"; agora "is not reported as passed (§6.7) … carries no
   evidential weight".
2. MEDIUM +2,8 pp: removido. No lugar, o mecanismo medido: injeção das datas de sessão, temporal
   28,27% → 44,21% (+15,94 pp; +1,47 pp overall), e o normalizer declarado rejeitado e desligado
   (`RESULTS-LOCOMO-SOTA-PUSH.md`; `temporal_norm_enabled: false`, `n_changed: 0` em
   `results/RESULTS-FULL-SOTA-PUSH-1986q.json`).
3. LightRAG: conferi eu mesmo `lightrag/lightrag.py` (branch `main`, fetch ao vivo 2026-10-04): os quatro
   defaults são `JsonKVStorage`, `NanoVectorDBStorage`, `NetworkXStorage`, `JsonDocStatusStorage`. Tabela 2:
   1 serviço; RAM e cold start "not estimated" (os ~1 GB / ~20 s vinham da hipótese Neo4j e não têm outra
   fonte); frase "Reading the table" e footnote reescritas. A parte do Mem0 não foi verificada (como no review).
4. `withOpAudit()`: tirei consolidate e também crystallize (nenhum `withOpAudit(` em código de crystallize no
   repositório); a lista agora é a dos fontes staged (reindex, compact, kg-merge, graphify-ingest).
5. IterC: linha de custo/latência rotulada "(gate p95 <= 5,000 ms: PASS)" e o veredito diz quais duas passam
   (`RESULTS-Q3-ITERC-POC.md` l.31: 3688 ms, PASS).
6. IterB: Fisher retirado. **McNemar não recalculado, porque o artefato por pergunta não existe**: procurei em
   `eval/evermembench/` (JSON do IterB só tem escores por batch e telemetria por query, sem acerto por pergunta),
   `results/` e Spotlight. O que dá para provar só com os marginais (20 vs 15 de 249, confirmados nos JSONs:
   IterB 4+3+5+4+4; base 2+3+4+3+3): com b − c = 5, o McNemar exato bilateral é **≥ 0,0625 para qualquer
   pareamento** (mínimo em c = 0; c = 1 dá 0,125). O texto diz isso e trata o CI pareado por batch [0,25, 3,76]
   (recalculado: média 2,0075, DP 1,4143, t(4) → [0,2514, 3,7636]).
7. "D73" removido; "D2" também (§3.5); a linha do CHANGELOG (parte A) que dizia "all of them are gone" ganhou
   `[sic: …; removed in part F]`.
8. MAP +4,02 pp: nota de que é contra a baseline não ponderada 3,20% (`RESULTS-PHASEMAP-5BATCH.md` l.40);
   +4,01 contra 3,21%.
9. "ceiling" do hit@10: retirado (ver S06).
10. "$0 … zero marginal retrieval cost": restrito ao KG path; a linha de ingest deixou de dizer $0 para embedding.
11. MemoryBank: esquecimento por item. Conferi o abstract em arXiv:2305.10250**v3** (21 maio 2023): "forget and
    reinforce memory based on time elapsed and the relative significance of the memory".
12. Preâmbulo: "machine-independent" → latência e RSS relativos ao hardware medido; custo por query não.

**S06 (21).** MuSiQue: store por pergunta com os 20 parágrafos dela, não "full corpus"; protocolo igual ao do
Beam; IRCoT open-domain em 139.416 parágrafos (arXiv:2212.10509v2, App. A, linha 505 do texto aberto), então a
margem sobre o IRCoT também reflete o setting; os dois "structural factors" saíram (support_hit@10 99,88%);
dev/test 0,8–5,0 pontos (arXiv:2108.00573v3, Tabelas 4 e 5); EX(SA) não é "a baseline que o Beam melhorou"
(SA 52,3, RoHTmix 63,6, arXiv:2308.08973v2 Tabela 4); quebra por hop (citada como "Section 8.1" do MuSiQue,
porque a guarda `secao_citada_check` lê "§8.1" como seção do próprio paper); não existe quebra por template.
HotPotQA: top_k=5, temp 0, n = 7.405 (3 erros), 10 parágrafos por pergunta; fonte `eval/hotpotqa/RESULTS-HOTPOTQA.md`;
"order of magnitude" retirado; FE2H mantido na tabela e a frase corrigida (rank 4; Beam 85,04 é o topo;
leaderboard lido via firecrawl, cache de 2026-10-02). LoCoMo: 10 conversas de 19–32 sessões, 369–689 turnos,
1.986 QA (contei no `locomo10.json`), não "10-session" nem "dev"; top_k=20 pontuado em 10; três células sem
artefato corrigidas; recall@10 multi-hop 51,59% e retirada da comparação com o EverMemBench; atribuição à
verbosidade e "Mem0 fecha esse gap" substituídas (Mem0 Tabela 1, arXiv:2504.19413v1); §5.3.3 "não medido";
títulos de §5.3 e §5.3.1. §5.4: "100+ conversation turns" substituído pela descrição do próprio paper
(arXiv:2602.01313v3; 0 ocorrências de "100+" no texto aberto); referência do MAP → §5.1.9; `[^mem0]` lista §5.3.2.
Espelhos no próprio manuscrito: caixa de headline (§5.8.6), bullets da §5.8.5, tabela da §5.4.

**Escolhas que você deve conhecer.**
- Troquei os `≥` que eu tinha posto por `>=`: a fonte Latin Modern do build não tem o glifo (o build avisou).
- A caixa de headline do MuSiQue ganhou "(IRCoT retrieves open-domain, §5.2.1)" (+5 palavras), para a margem
  de +22,12 pp não viajar sem a ressalva.
- Densidade ficou em 2,0613, com folga de 17 palavras. Qualquer acréscimo ao manuscrito daqui para frente pede
  corte ou obra nova.

## 3. Abstract ≤ 1.920 caracteres

Um único bloco ASCII, que condensa o abstract do manuscrito sem alegação nova (cada afirmação está no abstract
do manuscrito), colocado nos três lugares:

| Arquivo | Caracteres | Palavras |
|---|---:|---:|
| `paper/abstract.md` §2 | 1.824 | 268 |
| `paper/arxiv-metadata.txt` (bloco ABSTRACT; local, gitignored) | 1.824 | 268 |
| `paper/publication/techrxiv-metadata.md` (bloco indentado, juntado por espaço) | 1.824 | 268 |

Antes: `abstract.md` 2.148+ (acima do limite), `arxiv-metadata.txt` 1.909 mas com o texto antigo
("architecture is the leading explanation", dois sistemas medidos), TechRxiv 2.095. As duas guardas de espelho
(`abs-produziram`, `abs-nao`) continuam verdes. O que ficou de fora por espaço: Table 4's aggregation (+4,50 pp),
o 4 B do cross-encoder, a frase da inotifywait/2 s. As notas de contagem dos três arquivos foram atualizadas.

## 4. Arquivos tocados

`paper/paper-tecnico-nox-mem.md`; `paper/abstract.md`; `paper/arxiv-metadata.txt`;
`paper/publication/techrxiv-metadata.md` (abstract, notas, linha do PDF: 81 páginas, v1.0.3, MD5);
`paper/publication/supplement-wave2-and-cross-backbone.md` (S5.3.3, cópia da §5.4, §5.7.2, §5.8.5, Tabela 2 e
footnote; erratum "part F", itens 13–17); `paper/CHANGELOG.md` (v1.0.3 parte F; "Three parts" → "Parts (A)–(F)";
`[sic]` na linha dos códigos internos); `paper/build/paper-tecnico-nox-mem.pdf` e `.tex`;
`paper/publication/zenodo-paper1/deposit-v103.py` (item novo no bloco V103);
`paper2-interventional/_sprint-2026-10-04/noxmem-apelacao-pacote.md`; `noxmem-audit/NUMBER-PARITY-v103E-to-v103F.md`.
`supplement-operational-appendices.md` não precisou de mudança (nenhuma das frases corrigidas aparece lá).

## 5. Paridade numérica

Tabela completa (v1.0.2 → parte E → parte F, com a fonte lida) em `NUMBER-PARITY-v103E-to-v103F.md`. Mudaram:
LoCoMo single-hop 71,40/84,13 → 80,36/92,03; temporal 68,94/82,31 → 77,96/84,74; overall adj-2 87,10 → 87,44;
+2,8 pp → removido (+15,94 pp temporal da injeção de datas); Fisher p = 0,48 → retirado (McNemar ≥ 0,0625, só
cota); LightRAG 2 serviços / ~1 GB / ~20 s → 1 / não estimado; "11.7 points" → 11,67 e 11,07. Não mudaram: 58,62%,
73,37%, 74,52%, 82,21/92,91, 51,85%, 8,03 vs 6,02, CIs do IterB, 63,28%, 0,6237, 99,86%, nDCG@10 do §6, 399 MB, 2,5 ms.

## 6. Não verificável aqui

- O McNemar exato: falta o acerto por pergunta das duas corridas (IterB Gemini e Backbone Matrix Gemini).
- A parte do Mem0 no achado 3 do review (serviços do Mem0), como já dizia o REVIEW-FINAL.
- "Setup commands ~6" do LightRAG: sem fonte, mantido como estava.
