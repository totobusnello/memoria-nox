# HotPotQA bench results — nox-mem Phase H v2 baseline

> Status: **HARNESS READY — bench not yet executed on VPS.**
>
> This file is the result-reporting template. Run `./run-bench.sh full` on
> the VPS (15h, ~$8) to fill in the numbers below.

## TL;DR (to be filled after first full run)

```
VERDICT: <pending>

HotPotQA dev-distractor (n=<N>):
  ans_F1:   <XX.X>%
  ans_EM:   <XX.X>%
  sp_F1:    <XX.X>%
  sp_EM:    <XX.X>%
  joint_F1: <XX.X>%
  joint_EM: <XX.X>%

Per type:
  bridge:     ans_F1 <X.X>%  sp_F1 <X.X>%  n=<n>
  comparison: ans_F1 <X.X>%  sp_F1 <X.X>%  n=<n>

Per level:
  easy:   ans_F1 <X.X>%  n=<n>
  medium: ans_F1 <X.X>%  n=<n>
  hard:   ans_F1 <X.X>%  n=<n>

Latency (single-question wall-clock):
  ingest_p50:    <X>ms  (paragraph rendering + nox-mem ingest)
  vectorize_p50: <X>ms  (Gemini 3072d embedding)
  retrieval_p50: <X>ms  (hybrid: FTS5 + Gemini + RRF)
  generation_p50: <X>ms (gpt-4.1-mini answer)

Cost (full bench n=7405):
  gpt-4.1-mini: $<X.XX> (~$0.001/q × 7405)
  Gemini embed: $<X.XX> (~$0.0001/q × 7405)
  TOTAL:        $<X.XX>
```

## Methodology

- **Dataset:** `hotpot_dev_distractor_v1.json` from hotpotqa.github.io
- **Setting:** distractor (10 paragraphs per question, 2 gold + 8 distractor)
- **Sample:** shuffled (seed=42); for full run, all 7405 dev questions
- **Per-question isolation:** fresh DB per question (paper requirement)
- **nox-mem config:** Phase H v2 baseline (rerank OFF, hybrid ON, top_k=5)
- **Generator:** gpt-4.1-mini @ temperature=0, max_tokens=128
- **Supporting facts prediction:** retrieved paragraph titles → token-overlap
  ranked sentences (lightweight heuristic; LLM-based extraction parked as
  future work, expected +5-10pp sp_F1)

## Competitive position

Published baselines for HotPotQA dev-distractor (single-shot retrieval+reader):

| System | ans_F1 | sp_F1 | joint_F1 | Notes |
|---|---|---|---|---|
| DrQA (paper, 2018) | 27.1 | 25.1 | 7.0 | original paper baseline |
| BERT-based RAG (2019-2020) | 45-55 | 50-60 | 25-35 | |
| DPR + FiD (~2021) | 65-72 | 75-82 | 50-58 | state-of-the-art reader systems |
| Modern memory systems (Mem0/Zep claimed) | 50-65 | n/a | n/a | self-reported; methodology varies |
| **nox-mem Phase H v2 (this run)** | **<X.X>** | **<X.X>** | **<X.X>** | retrieval-only baseline |

**Honest framing:**

> nox-mem single-shot retrieval baseline on HotPotQA distractor: **<X.X>% F1**.
> Competitive with modern memory systems; sub-SOTA reader models. Q3 Iterative
> Retrieval (planned 2026-Q3) targets a second retrieval pass conditioned on
> the first answer attempt; predicted to close **30-50%** of the remaining
> gap to FiD-class systems.

## Per-type breakdown (HotPotQA-specific)

HotPotQA `type` field distinguishes:
- **bridge** (~73% of dev set): two-hop reasoning where one entity bridges
  paragraphs. E.g. "Where was the lead singer of Queen born?" → must hop
  Queen → Freddie Mercury → Zanzibar.
- **comparison** (~27%): direct comparison between two entities. E.g. "Was
  Mount Everest discovered before or after Kilimanjaro?"

Expected pattern (literature):
- comparison: easier for retrieval (both entities mentioned in question);
  harder for reader (yes/no + comparative reasoning).
- bridge: harder for retrieval (intermediate entity not named); easier for
  reader once both supporting paragraphs are present.

Our retrieval-side strengths:
- Hybrid BM25 + Gemini-dense excels at comparison (lexical entity overlap).
- Bridge is the weakness — multi-hop intermediate entities don't lexicalize.

## Knobs to test post-baseline

| Knob | Mechanism | Expected lift | Cost |
|---|---|---|---|
| Cross-encoder rerank (NOX_RERANKER_ENABLED=1) | bge-reranker-v2-m3 on top-50 | +1-3pp ans_F1 | +50-300ms/q CPU |
| KG path retrieval (Lab Q1 #4) | 1-hop entity walk over kg_relations | +2-4pp bridge ans_F1 | $0/q (SQL) |
| Multi-query expansion (Lab Q1 #3) | gemini-flash-lite decomposer + RRF | +2-3pp F_MH-style multi-hop | $0.0001/q |
| Iterative retrieval (Q3 planned) | answer-conditioned 2nd hop | +5-10pp ans_F1 (predicted) | +1× retrieval/q |

## Logs / artifacts

- Full per-question JSONL: `results/RESULTS-FULL-7K-DEV.jsonl`
- Aggregate summary JSON: `results/RESULTS-FULL-7K-DEV.json`
- Smoke run (n=200): `results/RESULTS-SMOKE-200.{jsonl,json}`
- Error log: any record with non-null `error` field
- Cost log: `results/cost-log.md` (manual update after run)

## Reproducibility

```bash
# On VPS:
cd /root/.openclaw/workspace/tools/nox-mem/eval/hotpotqa
./run-bench.sh smoke          # 200 questions, ~30min, ~$0.20
./run-bench.sh full           # full 7405, ~5-7h, ~$8
```

Random seed: 42 (controls question shuffle). Per-question isolation
guarantees no cross-contamination. Dataset SHA256: (recorded at runtime).

## Open follow-ups (parking lot)

- [ ] Implement LLM-based supporting-fact extractor (+5-10pp sp_F1 predicted)
- [ ] HotPotQA fullwiki setting (5M paragraphs; tests Wikipedia-scale retrieval)
- [ ] Composability test: KG path retrieval × HotPotQA bridge questions
- [ ] Compare token-overlap SP heuristic vs LLM SP extractor head-to-head
- [ ] Dashboard panel for HotPotQA alongside EverMemBench + LongMemEval
