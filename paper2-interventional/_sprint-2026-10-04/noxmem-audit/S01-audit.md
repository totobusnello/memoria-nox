# S01 audit — title block + Abstract (paper v1.0.3, 2026-10-04)

Escopo: linhas 1–20 de paper/paper-tecnico-nox-mem.md (bloco de título + Abstract). Não há headline box antes do §1.

## Números conferidos (OK)
| claim | artefato | valor lido |
|---|---|---|
| KG-path p50 2.5 ms, $0 | benchmark/latency-cost/results/RESULTS-PRODUCTION-SOTA.json | kg_path_only_n120.p50_ms 2.53; kg_path_only_per_query_usd 0.0 |
| 399 MB RSS | idem, footprint.rss_idle_mb | 399 |
| Mem0 LoCoMo 0.469 vs 0.426 | paper §6.3 tabela (0.4686/0.4263) | OK |
| rc4 LME 0.526/0.406, LoCoMo 0.495/0.441 | §6.3.2 tabela 0.5255/0.4061, 0.4952/0.4407 | OK |
| 5 categorias | §6.4 (single-hop..open-domain, numeric n/a) | OK |
| 4 confounds residuais | §6.3.2 l.1051 (a,b,c,e; d ablacionado) | OK |
| 63.28 / 63.77 / 59.27 / 72.61 | RESULTS-BACKBONE-MATRIX.json gemini-3-flash-preview Overall 63.28; média não ponderada das 9 sub-dim = 573.89/9 = 63.77; arXiv:2602.01313v3 Table 4 (https://arxiv.org/html/2602.01313, cabeçalho "v3 11 Mar 2026"): MemOS Gemini-3-Flash avg 59.27, Full Context 72.61 | OK |
| 18.88% | Table 4 v3, MemOS GPT-4.1-mini col. Multi-hop 18.88±4.8; é o máximo entre sistemas memory-augmented em todas as colunas | OK como "best", mas ver F1 |
| March 14, 2026 | docs/EVOLUTION.md l.136 "v1.0 (Mar 14)"; não aparece no corpo do paper | ver F5 |

## Defeitos
F1 (high) F_MH "same run 3–7%": RESULTS-BACKBONE-MATRIX.json gemini-3-flash-preview F_MH weighted 6.02%, per-batch 4.0/6.0/8.0/6.0/6.12. 3–7% é a faixa da era gpt-4.1-mini (3.21% Phase H v2 .. 7.23% Wave C). E 18.88% é coluna GPT-4.1-mini; MemOS na coluna Gemini-3-Flash = 10.84% (Table 4 v3). O próprio §5.1.10 exige mesmo backbone. Já apontado como "nuance" em REVIEW-noxmem-v103-final.md L1 l.121 e não aplicado.
F2 (high) Abstract omite EverOS > nox-mem: output-2026-09-10/_aggregate.json evermind overall nDCG 0.6455, locomo 0.6585, LME 0.5942 vs nox rc4 0.5013/0.4952/0.5255 (§6.3.3 "EverOS outperforms nox-mem here, on both datasets"). Abstract chama nox-mem/Mem0 de "the two leaders" e lista "three findings cut against our own headline" sem este.
F3 (medium) Hardware: título "4-vCPU / 8 GB"; artefato do §5.7 meta.vcpus 4, ram_total_mb 15987 (~16 GB); §6.5 item 6 diz "8 cores / 16 GB"; HANDOFF l.2011 diz migração para KVM2 2 cores/8 GB. Três specs diferentes.
F4 (medium) "single SQLite file" vs §2.4 l.310 "1,481 chunks across 7 databases", §1.3 "individual agent databases", l.1267 "single SQLite file per agent database".
F5 (low) "since March 14, 2026" sem suporte no corpo (só EVOLUTION.md). 
F6 (low) "later runs over the same corpus and query set": EverOS/Zep usaram o set n=2,482 do rc4 (§6.3.3 l.1068), não o n=100/dataset da canonical.
F7 (low) "operator-assigned severity": §3.4.2 diz que pain também deriva implicitamente; §5.1 l.528 90.67% dos chunks no default 0.2.
