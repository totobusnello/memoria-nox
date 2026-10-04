# S12 — Cross-section consistency (paper-tecnico-nox-mem.md v1.0.3)

Escopo: números/claims com múltiplas ocorrências (abstract, §5 headline box, §5.x, §6.x, §7, §8, footnotes) + cross-refs §x.y.
Método: script Python listando todas as ocorrências de 26 quantidades-chave (abstract → corpo); leitura integral de §6, §7.1, §8, §5.1, §5.4, §5.7, §5.8; checagem aritmética; artefatos abertos abaixo.

## Concordam (verificado)
- 63.28 / 59.27 / +4.01; 63.77 / +4.50; 72.61; 42.55 / +20.73 / +21.22; 51.68 / +9.13; 51.65 / +9.10; 11.60 / 12.12 / 16.72; MA 88.42 / 86.70 / +1.72 / 55.68 / +32.74 / +15.08 / +17.66 (73.34) — abstract, headline box, §5.1.5, §5.1.6, §5.1.10, §5.8.5 consistentes; decomposição 9.13+11.60=20.73 e 17.66+15.08=32.74 exatas.
- Contagens 2,733 / 2,400 / F_HL 388 / 3,121 somam.
- Batch stats §5.1.6: média 51.678, sd 1.453, +1.70σ, 1.27× — ok.
- Wave A: 0.6237/0.3488 = +78.8%; /0.5702 = +9.4%; 0.6228 = 99.86%; A11 −9.5%; A7 +1.3% — ok (abstract §5.1.3 ref ok, conclusão ok).
- Wave B/C: 3.21 baseline; 6.42 / 6.83 / 10.44 predicted; 25.8% gap — ok. Phase G 11.8% gap — ok.
- §6.3 canonical: 0.4686/0.4263 (+0.042), 0.5234/0.4764 (+0.047, MRR +0.039) — ok; abstract arredondamentos ok.
- rc4: 0.5255/0.4061 (+0.119), 0.4952/0.4407 (+0.055), 0.5013/0.4337 (0.068) — ok. Ablation 0.4979, 0.4920, 0.5215 — ok (principle 5 "≥+0.05" ok: 0.0513).
- §6.3.3/§6.3.4: +0.163/+0.069/+0.144; 0.123; 3.8×; 2,482×510 = 1,265,820; 0.0037%; 4B/22M ≈ 182 — ok.
- §6.4 categorias somam 2,482.
- §6.9 Letta ordens de grandeza: 960,000 ms / 2.5 = 10^5.58; /529..940 ≈ 10^3 — ok.
- §5.7.1 KG p50 2.53 ms, hybrid 529/698 ms: benchmark/latency-cost/results/RESULTS-PRODUCTION-SOTA.json — ok; §6.6 / L7 / §6.3 repetem igual.
- §5.7.2 custo: 0.15/1M × 10 tok = 1.5e-6; 667× — ok.

## Defeitos (detalhe na saída estruturada)
1. Abstract chama nox-mem e Mem0 de "the two leaders" e diz que nox-mem "leads on both datasets", omitindo que EverOS (mesmo corpus, mesmas 2,482 queries) supera nox-mem em ambos (§6.3.3: 0.6455 vs 0.5013). A lista "Three findings cut against our own headline" também omite. HIGH.
2. Conclusão §8 resume §6 só com canonical+rc4 ("6 systems: 3 produced numbers, 3 documented gaps"), sem EverOS/Zep; contradiz abstract (4 produziram números) e §6.3.3–6.3.4. HIGH.
3. §6.5 princ. 6 "Same VPS (Hostinger 8 cores / 16 GB RAM)" contradiz front matter (4 vCPU/8 GB; hosting omitido), §6.3 (RunPod pod dedicado), §6.3.3/6.3.4 (outro host com Docker). HIGH.
4. §6.4 "open-domain is likewise LongMemEval-only" — artefato eval/q4-comparison/docs/rc2-per-category-mapping.md: open-domain = LoCoMo category 4, n=841; LME "No native open-domain field — n/a" (l.64,125). Também 841 > 500 (LME total). HIGH.
5. §6.7 mem0 smoke "nDCG@10=0.8569 ... gold-hit 3/20" — impossível (média nDCG ≤ 3/20 = 0.15); recomputado de eval/q4-comparison/output/mem0.json: 0.1315, gold-hit 3/20 (bate com tabela §6.6 mem0@500 = 0.1315). Também "populated the first row of §6.3" e "interpretation ... in §6.3" desatualizados (§6.3 declara o smoke superseded). MEDIUM-HIGH. (nox-mem 0.6380 não reproduzido: output/nox_mem.json dá 0.4509 13/20 com mesmo cálculo — arquivo pode ter sido sobrescrito; NÃO VERIFICÁVEL, não reportado.)
6. §6.3.2 "Mem0 dropped 4 of 6,822 chunks on ingest" / "(The 4 chunks Mem0 dropped to transient 503s affect one query...)" vs (e) "Mem0's Chroma collection retained all 6,830". rc4-run.log tem 4 erros 503 (conv-41::D27:9, conv-41::D31:8, conv-42::D2:21, conv-42::D6:1), mas os 4 chunk_id estão presentes no .mem0-chroma-rc4/chroma.sqlite3 (cópia: embeddings=6,830, distinct chunk_id=6,822, cada um dos 4 com 1 linha). MEDIUM.
7. §6.3.2 "four residual confounds are declared below, and a fourth — the embedding task-type asymmetry" → deve ser "a fifth" (l.1049 diz "a fifth"); L6 "its fourth potential confound" idem. MEDIUM-LOW.
8. §1.4 Table 1 caption: "we did not deploy the other six systems ... only two of them (Mem0 and agentmemory) could be brought to a same-corpus comparison" — agentmemory não está na Tabela 1; Zep e EverOS (na tabela) foram comparados no mesmo corpus (§6.3.3–6.3.4); Mem0, Zep, EverOS e Letta foram deployados em §6. MEDIUM.
9. §5.7.3 "Mem0 / Zep / Letta canonical deployments require >=3 services ... 1.5–3 GB" vs Table 2 (§6.8): mem0 2 services ~800 MB; Zep 2 ~1.2 GB; Letta 3 ~1.5 GB. MEDIUM.
10. RSS: abstract/§5.7.3 399 MB (artefato RESULTS-PRODUCTION-SOTA.json footprint.rss_idle_mb=399, 2026-05-29, chunk_count 69,135) vs Table 2/footnote ~341 MB (2026-05-24) usado no headline "~12×" vs §6.9 415 MB (2026-06-15, sem artefato achado por grep em paper/ audits/ docs/; §5.7.1 Correction v1.0.2 removeu números da mesma re-checagem não arquivada). Footnote diz "6830 chunks live" no VPS de produção, mas o próprio artefato note_341mb_paper diz "62k → 69k chunks" e L2 diz ~69k em 2026-05-24: 6,830 é o corpus de eval. MEDIUM.
11. §5.7.3 "+15 MB (= ~414 MB)" vs artefato rss_under_10_concurrent_mb = 423 (o campo rss_delta_under_load_mb=15 é inconsistente com 423−399=24). LOW-MEDIUM.
12. §5.1.11–5.1.12: "the conclusion ... that the EverMemBench F_MH gap is retrieval-bound rather than a reasoning deficit — is stated in §5.4 and used in §7" — §5.4 não diz "retrieval-bound" (task setup = leading, not established, account; §5.1.9 "not an established ceiling of the retrieval stage"); §7 não usa. MEDIUM.
13. §5.4 heading "paradox — resolved" vs fecho "refined rather than dissolved" e abstract "leading, not established"; e fecho "largely a structural property of ... all-or-nothing scoring" contradiz o parágrafo anterior (oracle runs apontam retrieval, "not at the scoring rule"). MEDIUM.
14. §5.1.8 "Three retrieval-augmentation knobs" vs §5.1.9 "four orthogonal mechanisms" (MAP é o quarto; e "orthogonal" é contradito pelo achado de overlap). LOW-MEDIUM.
15. Rótulo "Wave A" usado para knobs Lab Q1 (headline l.476, §5.8.5, §5.8.6) enquanto §5.1.1 define Wave A como a série de ablação section/tier/salience. LOW (jargão).
16. L6 "reported in §6.3.3" para EverOS e Zep — Zep é §6.3.4. LOW.
17. L8 "See §5.7." — §5.7 é operacional; nada de pain ablation lá. LOW.
18. §1.4 "address provenance (§3.3)" — §3.3 é Deduplication (dedup_log); ops_audit/withOpAudit só aparecem em §1.4 e §7.1 L4. LOW.
19. §6.6 "LongMemEval n=100 + LoCoMo full" — canonical LoCoMo é n=100 (§6.3). MEDIUM-LOW.
20. F5 apresenta cross-encoder post-RRF como trabalho futuro e "stack terminates at RRF"; §5.1.7 e §5.7.1 documentam reranker cross-encoder MiniLM já existente opt-in (NOX_RERANKER_ENABLED=1). LOW-MEDIUM.
21. F4 atribui 83%/93% a "EverCore"; §6.3.3 e [^everos] atribuem 93.05/83.00 a EverMemOS. LOW. (não verifiquei a fonte externa.)
22. §5.4 tabela: linhas LoCoMo/EverMemBench com 5 células num header de 6 → verdict cai na coluna SOTA. LOW.

Não verificável / não reportado: nox-mem smoke 0.6380 (arquivo atual dá 0.4509); L2 "~69k chunks em 2026-05-24" vs artefato "62k" na mesma data (indício, não conclusivo); §6.9 70.7k em 06-15 vs F6 ~95k em 06-04 (F6 já declara não-reverificável).
