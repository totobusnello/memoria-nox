# Number parity — paper v1.0.2 → v1.0.3 part E → v1.0.3 part F (2026-10-04)

Bases: v1.0.2 = `scratchpad/v102/paper-tecnico-nox-mem.md`; part E = backup taken before this pass
(`scratchpad/applyF/paper-tecnico-nox-mem.md`); now = `paper/paper-tecnico-nox-mem.md`. Only numbers
touched by part F are listed. "—" = the number did not exist in that version.

## 1. Every number changed in part F

| Where | v1.0.2 | part E | part F | Source read |
|---|---|---|---|---|
| §5.3.1 table, single-hop retrieval@10 strict / adj-2 | 71.40% / 84.13% | 71.40% / 84.13% | **80.36% / 92.03%** | `eval/locomo/RESULTS-LOCOMO.md` per-category table; `results/RESULTS-FULL-1986q.json` single_hop evidence_hit_at_10 0.80357 |
| §5.3.1 table, temporal retrieval@10 strict / adj-2 | 68.94% / 82.31% | 68.94% / 82.31% | **77.96% / 84.74%** | same; temporal 0.77955 |
| §5.3.1 table, overall adjacency-2 | 87.10% | 87.10% | **87.44%** | `RESULTS-LOCOMO.md` "evidence_hit@10 (adj-2) 87.44%" |
| §5.3.2 date knob | +2.8 pp (normalization) | +2.8 pp | **removed**; session-date injection: temporal 28.27% → 44.21% (+15.94 pp), overall +1.47 pp | `eval/locomo/RESULTS-LOCOMO-SOTA-PUSH.md` per-category table; `results/RESULTS-FULL-SOTA-PUSH-1986q.json` `temporal_norm_enabled: false`, `n_changed: 0` |
| §5.3.1 (new) | — | — | adversarial F1 65.78% vs hit@10 60.18%; multi-hop recall@10 51.59% | `RESULTS-FULL-SOTA-PUSH-1986q.json` adversarial mean_f1_sota 0.657848; `RESULTS-FULL-1986q.json` adversarial hit 0.60181, multi_hop recall 0.51586 |
| §5.3.2 (new) | — | — | constrained prompt 34.90% → 50.38%; Mem0 F1 per category 28.64–48.93, Mem0^g 24.32–51.55 | `RESULTS-LOCOMO.md` l.28–29; arXiv:2504.19413v1 Table 1 (scratchpad `mem0.html`) |
| §5.3 intro, config (new) | "10-session"; top_k=10 | same | 10 conversations, 19–32 sessions, 369–689 turns, 1,986 QA; top_k=20 scored at 10; 1,966 with gold evidence | count over `eval/q4-comparison/cache/raw/locomo10.json`; `RESULTS-LOCOMO.md` "top_k: 20", "n_retrieval_scored 1966" |
| §5.2.1 config/protocol (new) | — | — | n=2,417; support_hit@20 99.96%, @10 99.88% | `eval/musique/RESULTS-MUSIQUE.md` l.18, 30–31 |
| §5.2.1 IRCoT corpus (new) | — | — | 139,416 paragraphs | arXiv:2212.10509v2 App. A (scratchpad `2212.10509v2.txt` l.505) |
| §5.2.1 dev/test | "on the order of one point" | same | 0.8 (EX(SA) 49.8 → 49.0) to 5.0 (SA 47.3 → 52.3) | arXiv:2108.00573v3 Tables 4 and 5 (`2108.00573v3.txt` l.398/416, 483/493) |
| §5.2.1 EX(SA) framing | "49.0 → 69.2" | same | SA 52.3, RoHTmix 63.6, Beam 69.2 | arXiv:2308.08973v2 Table 4 (`2308.08973v2.txt`) |
| §5.2.1 per-hop (new) | — | — | 2-hop 59.42 vs 57.9; 3-hop 52.93–64.27 vs 47.9; 4-hop 47.84–52.35 vs 28.1 | `RESULTS-MUSIQUE.md` l.38–43; arXiv:2108.00573v3 §8.1 (l.457) |
| §5.2.2 config | "same config as §5.2.1" (top_k=20 implied) | same | top_k=5, temperature 0, n=7,405, 3 errors, 10 paragraphs (2 gold + 8) | `eval/hotpotqa/adapter_nox_mem.py` l.5, l.83; `RESULTS-HOTPOTQA.md` l.40–43 |
| §5.2.2 text | "roughly 11.7 points below the leading entries" | same | 11.67 below Beam (85.04%), 11.07 below FE2H (84.44%, rank 4) | hotpotqa.github.io (firecrawl, cache 2026-10-02): 1 Beam 85.04, 2 PipNet 84.86, 3 Smoothing R3 84.34, 4 FE2H 84.44 |
| §5.1.9 MAP | +4.02 pp vs ~7.23% row | +4.02 pp | +4.02 pp kept, with note: vs unweighted 3.20%; +4.01 pp vs weighted 3.21% | `eval/evermembench/RESULTS-PHASEMAP-5BATCH.md` l.40 (Phase H v2 mean 3.20%, Δ +4.02) |
| §5.5.1 table, latency gate | — | p95 3,688 ms (no gate label) | gate p95 <= 5,000 ms: PASS | `RESULTS-Q3-ITERC-POC.md` l.31 |
| §5.5.2 IterB test | CI [1.06, 9.39] | Fisher exact p = 0.48 | Fisher withdrawn; exact McNemar p ≥ 0.0625 (bound from marginals); per-batch diffs +4, 0, +2, +2, +2.04 pp | `RESULTS-Q3-ITERB-POC-GEMINI.json` per_batch F_MH 8, 6, 10, 8, 8.16 (= 4, 3, 5, 4, 4 of 50/50/50/50/49 → 20); `RESULTS-BACKBONE-MATRIX.json` gemini-3-flash F_MH correct 2, 3, 4, 3, 3 = 15 of 249. Bound: b − c = 5, min over c of 2·P(Bin(5+2c, ½) ≤ c) = 0.0625 at c = 0 (c = 1: 0.125; c = 2: 0.1797). Per-question pairing **not archived** (searched `eval/evermembench/`, `results/`, Spotlight); no McNemar p-value is reported |
| §6.8 Table 2, LightRAG | 2 services, ~1 GB, ~20 s | same | 1 service, RAM and cold start not estimated | `lightrag/lightrag.py` (`main`, live fetch 2026-10-04): kv `JsonKVStorage`, vector `NanoVectorDBStorage`, graph `NetworkXStorage`, doc status `JsonDocStatusStorage` |
| Headline (§5.8.6 box), MuSiQue line | — | — | qualifier "(IRCoT retrieves open-domain, §5.2.1)"; numbers unchanged | — |

## 2. Numbers deliberately unchanged

58.62% (MuSiQue), 73.37% (HotPotQA), 74.52% strict and 82.21% / 92.91% multi-hop (LoCoMo), 51.85% token-F1,
+2.01 pp IterB (8.03% vs 6.02%), CI [6.27, 9.79] and paired [0.25, 3.76] (recomputed here:
mean 2.0075, SD 1.4143, t(4) → [0.2514, 3.7636]), 7.22% / 7.25% / 7.23% MAP rows, 63.28%, 0.6237, 99.86%,
nDCG@10 values of §6, 399 MB, 2.5 ms.

## 3. Mechanical census of numeric tokens, part E → part F

Regex over numeric tokens (with %, pp, ms, MB, GB, × suffixes). Section numbers, dates and arXiv ids are
included, so not every entry is a result.

**Manuscript.** Removed (14): `+2.8 pp`×1, `-4.1`×1, `1 GB`×1, `11.7`×1, `5.1.8`×1, `5.4`×1, `5.5`×1,
`5.8.1`×1, `68.94%`×1, `71.40%`×1, `73`×1, `82.31%`×1, `84.13%`×1, `87.10%`×1.
Added (132): `+1.47 pp`, `+15.94 pp`, `+2.04 pp`, `+4.01 pp`, `+4.02 pp`, `0.0625`, `0.8`, `1,966`,
`1,986`×2, `11.07`, `11.67`, `139,416`, `2,417`, `24.32`, `28.1`, `28.27%`, `28.64`, `3.20%`, `3.21%`,
`34.90%`, `369`, `44.21%`, `47.3`, `47.84`, `47.9`, `48.93`, `49.8`, `5,000 ms`, `5.0`, `50.38%`,
`51.55`, `51.59%`×2, `52.3`×2, `52.35`, `52.93`, `57.9`, `59.42`, `60.18%`, `63.6`, `64.27`, `65.78%`,
`689`, `7,405`, `77.96%`, `80.36%`, `84.44%`, `84.74%`, `85.04%`, `87.44%`, `92.03%`, `99.88%`,
`99.96%`, plus section numbers, arXiv ids, file-name digits and small integers.
(`73` is the removed D73 code; `-4.1` is one `GPT-4.1-mini` mention in the replaced Mem0 sentence of §5.3.2;
`5.1.8`/`5.5`/`5.8.1` are cross-references that moved.)

**Supplement (`supplement-wave2-and-cross-backbone.md`).** Removed: `5.3.2`, `5.5`×2 (cross-refs) and
two small integers. Added: `51.59%`×2, `60.18%`, `65.78%`, `74.52%` (erratum F), `2602.01313`×2,
cross-references and erratum numbering.
