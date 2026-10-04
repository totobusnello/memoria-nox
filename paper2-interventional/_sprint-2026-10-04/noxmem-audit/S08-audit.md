# S08 audit — §5.7 Operational characteristics + §5.8 Methodology (paper-tecnico-nox-mem.md, linhas 854–950)

Data: 2026-10-04. Sem git, sem Zenodo, sem contato externo. Fonte única de leitura: arquivos do repo + 1 scrape ao vivo de mem0.ai/pricing.

## Artefatos lidos
- benchmark/latency-cost/results/RESULTS-PRODUCTION-SOTA.json (meta, latency_ms, footprint, cost_usd, competitor_comparison, honest_gaps)
- paper/publication/results/latency-benchmark-summary.json (corrida 2026-05-18, n=95, por categoria)
- eval/evermembench/RESULTS-PHASEG.md (linhas 20–22, 348–351), RESULTS-PHASEG-5BATCH.md (36–124, 125–175, 265–300)
- eval/evermembench/RESULTS-PHASEH-v2-5BATCH.md (14–72, 156–158)
- eval/evermembench/RESULTS-PHASEKG-5BATCH.md (30, 64, 122, 199)
- eval/evermembench/INVESTIGATION.md §11 (transcrição da Table 4, arXiv:2602.01313 — arXiv NÃO reaberto nesta rodada)
- eval/evermembench/aggregate_phaseKGMAP_5batch.py:95-104, aggregate_phaseTriple_5batch.py:138-146 (z=1.96, pstdev), eval/lib/aggregate_5batch.py (t=2.776)
- paper/publication/supplement-wave2-and-cross-backbone.md (S5.5.5, 98-132)
- docs/DECISIONS.md:736-761 (deploy G10d 2026-05-21 via systemd drop-in — confere)
- https://mem0.ai/pricing (scrape ao vivo 2026-10-04, maxAge 0)

## Conferidos e OK
- KG path p50/p95/p99 2.53/6.14/7.87 ms, n=120 → 2.5/6.1/7.9 ✓
- Hybrid 529.21/697.7/744.24 ms n=100, warmup 10, corpus 69,135 ✓
- Earlier run p50 939.755 / p95 2341.955 / p99 2523.367 n=95 ✓; per-category decision 977 / procedure 1105 / incident 990 / architecture 1004 ✓ ("~900–1,100")
- short 578 vs 505, entity 504 vs 603 ✓
- $0.15/1M × 10 tokens = $1.5e-6; 0.001/1.5e-6 = 666.7 → 667× ✓ (aritmética)
- Mem0 free 1,000 retrieval/mês, Starter $19, Pro $249 ✓ (live page); sem overage publicado ✓ (artefato de 05-29 dizia $0.001 overage — artefato desatualizado, o paper está certo)
- Footprint 399 MB idle ✓
- 5 batches 626+610+623+633+629 = 3,121 ✓; t crit 2.776 em eval/lib/aggregate_5batch.py ✓
- Phase G: +8.00 → +1.61 (5.0×), F_TP +11.67 → +2.00 (5.8×) ✓; F_MH σ 2.30 ✓; batch 004 +1.4σ ✓
- Phase H v2: +11.60 → +9.13 (1.27×), σ 1.45, +1.70σ ✓
- MA composite GPT-4.1-mini 73.34 vs 55.68 (+17.66) ✓; Gemini-3 +1.72 ✓; +20.73 = 9.13 + 11.60 ✓; +32.74 = 17.66 + 15.08 ✓
- Transfer 0%/40%/34%, 24% agregado (§5.5.5 + supplement S5.5.5) ✓
- §5.5.2 traz o teste por questão (Fisher p=0.48) como §5.8.1 promete ✓
- Batch 004 n=49 do capstone (supplement:211) ✓
- 2,733 vs 2,400 (§5.1.10) ✓

## Defeitos (ver StructuredOutput para quote/fix exatos)
1. HIGH — "GPT-4.1-mini is the only tested backbone where all memory systems gain vs Full Context": na Table 4 (transcrição INVESTIGATION.md §11.1) MemoBase −3.18 e Mem0 −0.36 vs Full Context em GPT-4.1-mini; só Zep +2.52 e MemOS +5.11 ganham. E no Llama-4-Scout MemOS também ganha (+2.27).
2. HIGH — linha "Lab Q1 #4 | +6.78 pp (batch 004)": RESULTS-PHASEKG-5BATCH.md:199 calcula +6.79 = KG batch 004 (10.00%) − média 5-batch do baseline (3.21%). O baseline Phase H v2 no batch 004 também era 10.00% (RESULTS-PHASEH-v2-5BATCH.md, linha F_MH) ⇒ Δ pareado de batch único = 0.00 pp. A linha não mede o que um gate de batch único teria mostrado (teria SUBestimado). Também 6.78 ≠ 6.79.
3. MEDIUM — título "overstate effects 3–6×" vs tabela 1.27×–5.8×.
4. MEDIUM — "F_HL sigma ~ 5 pp, MA_C/P/U sigma ~ 3 pp": Phase G não reporta σ por batch para F_HL nem MA; Phase H v2: F_HL 4.07, MA_C 2.88, MA_P 6.07, MA_U 9.54.
5. MEDIUM — regra "Δ abaixo de ~2σ é ruído": σ é o DP do nível por batch de um braço, não do Δ pareado; o próprio +8.00 é ~3.5σ (8/2.30) e mesmo assim foi superestimado 5×; e um desvio de +1.4σ é chamado "outlier" sob uma regra de 2σ.
6. MEDIUM — contradição §5.8.2 ("batch 004 already had the lowest MA performance… (selection bias)") × §5.8.3 ("MA was not measured in the initial single-batch run"); artefato: MA "(n/a at batch 004)". "Selection bias" é o rótulo errado.
7. MEDIUM — "on the categories both runs share the gap stays within ~100 ms": "long" está nas duas corridas: 1,016.7 ms (05-18) vs 624.0 ms (05-29), gap 393 ms.
8. MEDIUM — faixa 100–500 ms atribuída a docs de Mem0 Cloud e MemOS: artefato registra Mem0 "<200ms" (docs) e MemOS "not published".
9. MEDIUM — "eliminates network and IPC overhead entirely": a medição é HTTP via loopback (meta.methodology; http_overhead 1–3 ms).
10. MEDIUM — "a Feb-2026 increase from $0.13/1M": artefato de 2026-05-29 leu $0.13/1M em ai.google.dev/pricing NAQUELE dia; incompatível com aumento em fev/2026. Preço atual não verificado ao vivo. "re-confirmed 2026-06-15" se apoia na corrida não arquivada que a correção v1.0.2 removeu.
11. MEDIUM — "+15 MB (= ~414 MB)": artefato rss_under_10_concurrent_mb = 423 e competitor_comparison.ram.rss_peak_10c_mb = 423; campo delta 15 é inconsistente com 423−399=24.
12. HIGH — "Mem0 / Zep / Letta canonical deployments require >=3 services … combined RSS typically in the 1.5–3 GB range": sem fonte; o próprio artefato diz Mem0 OSS = um processo Python (~50–200 MB estimado), Zep combinado "not published", Postgres adiciona 200–500 MB.
13. MEDIUM — "$5/month VPS tier": host medido tem 4 vCPU / 15,987 MB RAM; artefato honest_gaps: "nox-mem requires VPS (~$12/mo)". Nenhuma medição num tier de $5.
14. LOW — header "Mem0 Cloud (published pricing)" com valores estimados (o próprio texto diz que não é preço cotado). Planos ao vivo implicam ~$0.0038–0.0050/retrieval (19/5,000; 249/50,000).
15. LOW — linha rerank "+3,700 ms p50 … no archived artifact": RESULTS-PHASEG.md:351 registra "+3.7 s / query" (overhead, não p50; batch 004, p50 total 4,783 ms na linha 348).
16. LOW — "Zep <100 ms p50 claim is published in marketing": artefato registra "<100ms", "unverified percentile" — o percentil p50 é nosso, não da Zep.
17. LOW — "KG path, MAP, MQ, adaptive classifier, and Q3 IterC … combined effects measured in Wave B/C (§5.1.9)": §5.1.9 só combina KG, MQ, MAP.
18. LOW — jargão interno não definido: "F10 observability layer (Phase A…/Phase B…)", "G3→G10d", "merged adapter pattern", "Lab Q1 #4", "NO-REPLICATE", "Wave A knob". Título §5.8.4 "Search error rate monitoring" não descreve o conteúdo (incidente de contaminação).

## Não verificável nesta rodada
- Preço atual do gemini-embedding-001 (não reaberto ao vivo).
- Table 4 do arXiv 2602.01313v3 reaberta: NÃO; usei a transcrição do repo (INVESTIGATION.md §11, que diz ter sido cross-checada com PR #368).
- Incidente de contaminação do batch 010 (§5.8.4): não procurado em artefato.
