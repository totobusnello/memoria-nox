# S06 audit v2 — §5.2 / §5.3 / §5.4 (paper-tecnico-nox-mem.md, linhas 659–758 no estado de 2026-10-04)

Sem git, sem Zenodo, sem contato. Notas da v1 (`S06-audit.md`) relidas como pistas; tudo reverificado.
Itens já corrigidos no CHANGELOG v1.0.3 partes A–E foram descartados (EX(SA) 49.80, IRCoT 36.50,
Beam Table 3 dev retrieval, DPR+FiD, Clark & Gardner 58.28, Mem0 66.88 = J, ranking LoCoMo retirado,
tabela §5.4 com 6 colunas, F_MH por backbone, oráculo Tables 4/5, "all-or-nothing" no fecho).

## Fontes abertas (versão)
- eval/musique/RESULTS-MUSIQUE.md + .json; adapter_nox_mem.py (docstring l.1-30: corpus de 20 parágrafos POR PERGUNTA; DEFAULT_TOP_K=20)
- eval/hotpotqa/RESULTS-HOTPOTQA.md + .json; adapter_nox_mem.py (l.5: distractor 10 parágrafos/pergunta; l.83 DEFAULT_TOP_K=5)
- eval/locomo/RESULTS-LOCOMO.md, RESULTS-LOCOMO-SOTA-PUSH.md, results/RESULTS-FULL-1986q.json,
  results/RESULTS-FULL-SOTA-PUSH-1986q.json, lib/scorer.py (`_evidence_hit_at_k` = any-hit)
- eval/q4-comparison/cache/raw/locomo10.json (contagem local de sessões/turnos)
- eval/evermembench/RESULTS-Q3-ITERB-POC-GEMINI.json, RESULTS-BACKBONE-MATRIX.json
- paper/publication/supplement-wave2-and-cross-backbone.md §S5.3.3, §5.1.8.3
- arXiv HTML baixado em 2026-10-04 (idêntico em bytes ao cache s13src/): 2602.01313v3, 2308.08973v2,
  2108.00573v3, 2212.10509v2, 1809.09600v1; 2504.19413v1 (Mem0) via firecrawl; 2402.17753v1 abs;
  hotpotqa.github.io (leaderboard distractor, cache firecrawl 2026-10-02).

## Verificados e OK (sem achado)
- Mem0 Table 2 J: 66.88 / 68.44 / Zep 65.99 / LangMem 58.10 / OpenAI 52.90 / full context 72.90. Table 1 só F1 por categoria.
- EverMemBench v3: MemOS F_MH 18.88 (GPT-4.1-mini), 10.84 (Gemini-3-Flash); full context Gemini 26.51; oráculo 2.41 → 97.99 (Table 5, §5 texto).
- Beam Table 4 test 69.2; Table 5 blind test 85.04, FE2H 84.44; Table 3 dev 77.37/89.77, 79.31/90.51.
- MuSiQue Table 4 (validation): EX(SA) 49.8; Table 5 (test): EX(SA) 49.0 (l.334: "Table 5 reports test set numbers").
- IRCoT Table 4: GPT3 CoT reader, IRCoT QA, MuSiQue 36.5 ± 1.2.
- IterB Gemini F_MH 8.032 (5 batches); baseline Gemini 6.024; gpt-4.1-mini 3.21; gaps 15.67 / 4.82.
- Nota: o abstract do v3 diz "multi-hop reasoning collapses ... even with oracle evidence (26% accuracy)", em tensão com a própria Table 5 (97.99 GPT-4.1-mini). O paper cita Table 5 corretamente; nenhum achado.

## Achados confirmados (ver StructuredOutput para quote/fix exatos)
1. HIGH MuSiQue: "full paragraph corpus" é falso; corpus por pergunta (20 parágrafos), top_k=20 devolve quase tudo (support_hit@20 99.96%). IRCoT é open-domain (139,416 parágrafos, IRCoT App. A). Os "dois fatores estruturais" (recall/RRF) não são testados por esse setup.
2. HIGH HotPotQA: "same config as §5.2.1" falso (top_k=5 vs 20); "full corpus" = 10 parágrafos por pergunta.
3. HIGH LoCoMo tabela: single-hop 71.40/84.13, temporal 68.94/82.31, overall adj-2 87.10 sem artefato; artefato 80.36/92.03, 77.96/84.74, 87.44.
4. HIGH "+2.8 pp date-normalization": normalizador desligado no run cheio (`temporal_norm_enabled: false`, `n_changed: 0`); ganho veio de session-date injection (+15.94 pp temporal, +1.47 pp overall).
5. MEDIUM "verbosity gap" + "Mem0 closes this gap": push já usa prompt de 1–5 palavras; artefato diz que composição também é gargalo; F1 por categoria do Mem0 (Table 1) ≤ 48.93 (Mem0) / ≤ 51.55 (Mem0^g).
6. MEDIUM "retrieval ceiling": hit@10 não limita F1 (adversarial F1 65.78% > hit@10 60.18%).
7. MEDIUM §5.3.3 rota ≥55% "not a retrieval change": não medido em LoCoMo; o artefato diz o contrário.
8. MEDIUM multi-hop LoCoMo 82.21% é any-hit; recall@10 multi-hop 51.59% (o menor depois de commonsense); "structurally easier than on EverMemBench" compara métricas que o EverMemBench não tem.
9. LOW-MED "10-session dialogues" (19–32 sessões, 369–689 turnos por conversa; LoCoMo: até 35 sessões, ~300 turnos) e "dev corpus" (locomo10.json, sem split dev).
10. LOW-MED Dev/test "on the order of one point": SA 47.3 dev vs 52.3 test (5.0 pt) no próprio MuSiQue.
11. LOW-MED "49.0 → 69.2 ... the baseline Beam improved upon": Beam Table 4 lista SA 52.3 e RoHTmix 63.6 acima de EX(SA).
12. LOW HotPotQA "order of magnitude" sem fonte para diferença dev/test.
13. LOW "100+ conversation turns" ausente do v3.
14. LOW MAP "of the Lab Q1 knob series (§5.1.8)" contradiz §5.1.8/§5.1.9 do próprio manuscrito ("separate MAP (section-bypass) run").
15. LOW "per-type breakdowns": artefato só tem per-hop.
16. LOW cabeçalho §5.3 "F1 constrained competitive" vs "We do not rank it".
17. LOW fonte da linha nox-mem HotPotQA aponta `audits/` (não existe arquivo HotPotQA lá).
18. LOW FE2H não é o 2º do leaderboard (PipNet 84.86 é).
19. LOW [^mem0] "Used in" omite §5.3.2.
20. LOW §5.2.3 "corpus structure is friendly to ... hybrid retrieval": é RC por pergunta.

## Descartados na reverificação adversarial
- "LoCoMo generation used top_k=20, not 10": o push de 51.85% usa `default_top_n: 10` (RESULTS-FULL-SOTA-PUSH-1986q.json); só o run constrained/naive usou 20. Mantido apenas o ajuste do Config (o run de retrieval pediu top_k=20 e pontuou @10), dentro do achado 9.
- "intrinsically hard" vs oráculo: o abstract do v3 sustenta leitura de dificuldade intrínseca (26%); não fixável por evidência limpa.
- "MemOS optimises for memory-vs-retrieval": não verificado (MemOS paper não aberto) — "não verificável".
- Per-hop "gain is broad": per-hop sustenta (EX(SA) 57.9/47.9/28.1 por hop, MuSiQue §7); só a parte "per-type" cai (achado 15).
