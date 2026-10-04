# S09 audit — §6.1 / §6.2 / §6.3 (incl. 6.3.1–6.3.4) — 2026-10-04

Fonte: paper/paper-tecnico-nox-mem.md linhas 951–1131. Sem git, sem Zenodo, sem contato.

## Verificado OK (valor no artefato)
- rc4 (output/rc4/_aggregate.md): nox 0.5013/0.4952/0.5255, R@10 0.6656, MRR 0.4749, p50 515.6; mem0 0.4337/0.4407/0.4061, 0.5852/0.4092, p50 349.8. ICs recomputados de output/rc4/*.json com aggregate.ndcg_at_k: ±0.0154/0.0174/0.0331 (nox), ±0.0156/0.0173/0.0358 (mem0) — batem.
- Ablação (output/rc4-ablation/_aggregate.md): 0.4979, LoCoMo 0.4920, LME 0.5215; 5 categorias nox>mem0 (single-hop 0.3924 vs 0.3908). 23/2,370 → 99.03%.
- Colisões: cache/locomo.jsonl+longmemeval.jsonl = 6,830 linhas / 6,822 ids, 8 ids duplicados; 10/2,482 queries com gold em par colidido; 4 chunks com 503 (rc4-run.log l.278–282) afetam 1 query (conv-41::q133). 2,370 gold distintos, 0 fora do corpus.
- cache/rc4-nox-hybrid.db eval_chunks = 6,822; chroma.sqlite3 embeddings = 6,830, chunk_id distintos 6,822, text_lemmatized 6,830 (cópias no scratchpad).
- output-2026-09-10/_aggregate.md: EverOS 0.6455/0.6585/0.5942, 0.7629/0.6403, p50 1591.6; Zep 0.4546/0.4793/0.3567, 0.6108/0.4279, p50 6001.8, p99 11845.5. Diferenças +0.163/+0.069/+0.144; 3.77× ≈ 3.8×; spread Zep 0.1226; Zep start 20:30:57Z → fim 00:43:33Z = 4 h 12 min 36 s (≈4 h 13 min).
- Zep 47 falhas (35/8/4, 46 sessões, 1,265,820 varreduras, 0.0037%): RESULTADOS-Q4-2026-09-10.md §5.5.
- EverOS rerank_n 50 / top_k_cap 100 / hits=50: RESULTADOS §4; config Qwen/Qwen3-Reranker-4B e gemini-embedding-001 3072: everos-config-retrieval-2026-09-10.txt.
- Canonical deltas internos (+0.047, +0.039, +0.042) aritmeticamente corretos.
- EverMemOS 83.00 LongMemEval: arXiv:2601.02163v2 HTML, tabela LongMemEval "Overall 83.00". 93.05 LoCoMo não confirmado no trecho extraído (não verificado).

## Defeitos (ver StructuredOutput para quote/fix)
1. §6.3.4 "Zep has no cross-corpus index" — contradiz RESULTADOS §5.2: /api/v1/collection/{n}/search existe (corpus-wide), nunca populada; o próprio doc diz "não um teto do Zep".
2. Confound (e) "Mem0's Chroma collection retained all 6,830" — os 4 chunks com 503 (log: "6826 ok, 4 errors") têm created_at 15:02:25–27Z no store, depois do fim da corrida mem0 (finished_at 14:57:04Z). Store pontuado tinha 6,826 linhas / 6,818 ids. A réplica (2,375 / 9.83 / 0.4446) foi contra o store pós-backfill; sem artefato do replay (só CHANGELOG).
3. Smoke nDCG@10 = 0.6380: output/nox_mem.json (2026-05-24, n=20, 13/20 gold-hit) pontua 0.4509 com aggregate.py (R@10 0.5958, MRR 0.425). 0.6380 só em docs/handoff, com MRR 0.3700 — não reprodutível.
4. Zep smoke chamado de "500-chunk-cap" — adapters/zep.py sem cap; output/_aggregate.md: "zep / hipporag2 — full corpus"; o cap 500 é MEM0_INGEST_LIMIT.
5. Canonical 2026-06-15: nenhum artefato no repo (grep 0.5234/0.4686/0.2803/0.1587 só em docs/README); CHANGELOG roadmap: "Raws 06-15 NÃO estão locais… pod terminado". Paper não declara.
6. EverOS "rejecting the duplicate id with an explicit error" — RESULTADOS §3: dos 8 ids colididos, 2º write aceito em 4 e recusado em 4.
7. "Versions are locked prior to execution" — spec 2026-05-23 tem "Latest stable / v0.27+ / Latest"; rc4 mem0 rodou 2.0.10 vs tabela 0.1.114.
8. Zep "default config" — compose/zep-config.yaml: extractors desligados por orçamento (escolha do experimentador); "does not rerank — confirmed in zep-config.yaml (extractors disabled)" é non sequitur.
9. Coluna de custo: nox hybrid "$0 (local)" vs §5.7.2 $0.0000015/query e §6.3.3 "one embedding call"; Mem0 "subscription" para a lib OSS; "cost derived from per-system logs" sem números derivados.
10. "confirming the LoCoMo result is a real retrieval gap" — sobreafirma frente a §6.3.2.
11. Cross-ref thread-leak → §6.3.1 (está em §6.9, l.1230), 2 lugares.
12. "a fourth — the embedding task-type asymmetry" → "a fifth".
13. Título §6.3.1 "one system that did not run" vs Letta "runs".
14. Letta "~16 min/query": sem artefato (só handoff arquivado; smoke doc 14,978 ms).
15. "market leader" — linguagem de produto sem fonte.
16. §6.1 "locked … only the tables … receive numbers after the run" — §6.3.1–6.3.4 e §6.5 (latency UNMET) foram escritos depois.
17. §6.3.1 "live EverOS service" vs §6.3.3 "needs no HTTP service" (adapter usa everos.service in-process).
