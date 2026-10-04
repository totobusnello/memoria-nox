# S05 audit — §5 preamble + §5.1 (EverMemBench + Wave A)

Escopo: paper/paper-tecnico-nox-mem.md linhas 472–653 (+ Abstract/§1 para contexto). Sem git, sem Zenodo.

## Verificado OK (valor no artefato)
- BACKBONE-MATRIX.json: Overall gpt 51.68 / gemini-3-flash-preview 63.28; MA_C/P/U 84.60/65.40/70.03 e 89.20/90.00/86.06; MA composite 73.34 / 88.42; F_MH 3.21 / 6.02. Todos os deltas da tabela §5.1.10 conferem (+4.01, +20.73, +11.60, +1.72, +32.74, +15.08, 7.36, 2.41, −4.61, 19.30, 38.01, 40.91, 4.60, 24.60, 16.03).
- Agregação Table 4 (média não ponderada das 9 sub-dims) recomputada: gemini 63.766, gpt 51.647, Phase D 59.211 (de results/analysis-phase{D,3}-batch-*.txt). Contagens 2,733 / 2,400 conferem.
- arXiv 2602.01313v3 (https://arxiv.org/html/2602.01313v3, Table 4): MemOS GPT-4.1-mini 42.55, F_MH 18.88, MA_C 69.90, MA_P 51.99, MA_U 45.15; MemOS Gemini-3-Flash 59.27 (−13.34 ⇒ full context 72.61), MA 81.84/87.59/90.67. OK. Nota: MemOS F_MH em Gemini-3-Flash = 10.84.
- Phase D 62.22 = 1942/3121. Phase G (RESULTS-PHASEG-5BATCH.md): 61.26, F_MH 5.22→6.83, MA −4.00/−2.80/−3.84, MC −2.63, 11.8%, 2.3×.
- Phase H v2 outlier: 54.15, σ 1.45, +1.70σ, 1.27× (11.60/9.13). 7/9 WIN (F_TP 15.00 vs 15.67).
- Wave B/C: KG+MQ 8.02, 90.8/99.3/91.4 (RESULTS-WAVE-B-KG-MQ.md l.76); KG+MAP 7.248, MA −5.016, gate1 fail (JSON); Wave C 7.232, pop-SD z CI [2.20,12.27]; t CI com SD amostral 6.424 = [−0.74, 15.21] OK.
- Wave A números (handoffs/_archive/HANDOFF-2026-04-28-a-2026-06-14.md l.2166–2181): 0.6237, 0.6228, 0.6155, 0.5646, 0.5702, 0.3488; razões +78.8/+63.5/+9.4/99.86/−9.5/+1.3 OK. Salience audit (docs/audits/2026-05-19-salience-distribution-audit.md): 99.7%, 90.67%, 99.76% OK. Censo 865/239/184/3.62 (paper/measurement/out/censo-corpus-2026-09-09.json) OK.
- `iterb_used_path` guards: adapter_nox_mem.py l.2939, 3251, 3408 OK.

## Defeitos
1. HIGH — Atribuição "section domina o lift" / "decompõe +78.8%" vs matriz G5: A0/A2 hybrid no-boost = 0.5126 (mesmo handoff). Remover section (A11 0.5646) mantém 0.2158 dos 0.2749 de ganho G3→A8 (79%); section responde por 21.5% (leave-one-out). "Majority" só vale contra o baseline sem boost do G5 (A0→A3 = 0.1102 de 0.1111). G3 é outra geração (tier_boost ligado, multiplicativo; A6 tier-only = 0.4059 < 0.5126).
2. HIGH — Phase G "significant regression" MA e "−0.96 real across all 5 batches": diferenças pareadas por batch (Phase D vs G): Overall −2.24,+2.13,−3.05,−0.63,−0.96 (batch 005 melhora; t pareado CI ≈ [−3.4,+1.5]); MA_C −12,+3,−6,−4,−1 (CI ≈ [−11.0,+3.0]); MA_U CI ≈ [−8.8,+1.4]; MA_P CI ≈ [−5.5,−0.1]. A CI do próprio Phase G overall [59.34,63.21] contém 62.22.
3. MEDIUM — "invisible in the single-batch gate due to selection bias — batch 004 already had the lowest MA": batch 004 tem a MAIOR queda de MA_C (80→68, −12); o gate não reportou MA ("n/a at batch 004", RESULTS-PHASEG-5BATCH.md l.163–165).
4. MEDIUM — "single-batch overstates effects 3–6×": o próprio §5.1 mede 1.27× (H v2), 2.33× (G overall), ~5× (G F_MH +8 vs +1.61).
5. MEDIUM — Matriz G5 "archived under audits/": não existe em audits/ nem docs/audits; só em handoffs/_archive/HANDOFF-2026-04-28-a-2026-06-14.md.
6. MEDIUM — DB do Wave A: paper diz `entity-eval.db` "curated from production usage"; handoff 05-20 (G6 forensics) diz G5 V3 = g5.db (68,995 chunks, clone prod) e entity-eval.db = 500 chunks sintético; tools/eval/run-g5.sh default EVAL_DB=g5.db. Registros conflitam — não verificável.
7. MEDIUM — Mecanismo do Claim 1: o audit atribui a concentração a dados (pain sem rating, idade homogênea pós-restore), não à forma do produto; com pain/recency ~constantes nenhuma forma "preserva sinal de pain spikes". +1.3% (Δ 0.0082, n=100, 1 run, sem teste).
8. MEDIUM — "four orthogonal mechanisms with overlapping" vs §5.1.8 "Three ... knobs"; MAP não aparece no §5.1.8; "orthogonal" contradiz item 1 ("overlap").
9. LOW — Phase G F_MH CI [3.97, 9.69] é do nível 6.83%, não do Δ.
10. LOW — Latência: artefato l.136 "~3.7 s p50 (vs ~1.1 s baseline)" ⇒ incremento ~2.6 s, não "+3.7 s".
11. LOW — §5.1.6 F_MH "~3–5%"/"−13 to −16 pp": artefato 3.21% (CI [−1.64, 8.04]), Δ −15.67 pp.
12. LOW — CI [49.88, 53.49]: artefato (t-dist per-batch) [49.87, 53.48]; 49.88 é "weighted" no próprio md.
13. LOW — source_type estava INERTE no G5 (A5 = A0 = 0.5126; A10 = A8 = 0.6237), mas §5.1.1 lista o backfill como parte das condições sem dizer.
14. LOW — "(draft)" no headline do Capstone.
