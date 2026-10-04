# S07 audit — §5.5 (Q3 orchestration) + §5.6 (LongMemEval cross-bench)

Paper: paper/paper-tecnico-nox-mem.md lines 768–852 (2026-10-04 working tree). Abstract + §1 read for context.

## Artifacts opened
- eval/evermembench/RESULTS-Q3-ITERC-POC.md / .json (gates dict: F_MH_lift −0.402, overall +1.454, MA_composite −4.356 FAIL, verdict DOCUMENTED_INSUFFICIENT; ship rec "DOCUMENT + DEFER")
- eval/evermembench/RESULTS-Q3-ITERB-POC-GEMINI.md / .json (per-batch F_MH 8/6/10/8/8.16; judge gemini-2.5-flash "unchanged"; vs bare: Overall −0.58, MA comp −3.53)
- eval/evermembench/RESULTS-BACKBONE-MATRIX.json (gemini-3-flash F_MH per batch 2/50,3/50,4/50,3/50,3/49 = 15/249; gemini-3.1-flash-lite F_HL weighted 60.82 vs gpt-4.1-mini 22.68)
- eval/evermembench/results/RESULTS-REBASELINE-MQ-GEMINI3FLASH.md (F_MH CI [4.99,9.48] contains 6.02; MA_U +3.10 CI [85.84,92.54] contains base 86.09; MA comp +0.12 CI [86.78,91.08] contains 88.81)
- eval/evermembench/RESULTS-PHASEMQ-5BATCH.md (gpt MA −1.38 ✓; MA_U −1.94)
- eval/evermembench/adapter_nox_mem.py (flags NOX_ITERC_ENABLED / NOX_ITERB_ENABLED; IterC docstring: 1 decomposer + N sub-answer + 1 final call ≈2× answer cost (estimate); guards iterb_used_path at MQ/KG/rerank lines 2939/3251/3408 in current file — supplement line numbers 2736/2906/3063 are stale but that is supplement scope)
- paper/publication/supplement-wave2-and-cross-backbone.md §S5.5.2–S5.5.8
- eval/longmemeval/RESULTS-CROSSBENCH-2026-05-29.md
- docs/DECISIONS.md D73 (IterC ship opt-in via NOX_ITERATIVE_RETRIEVAL=self-ask); docs/ROADMAP.md line 258
- External: https://arxiv.org/abs/2210.03350v3 (Self-Ask abstract); search excerpt github.com/garrytan/gbrain-evals/blob/main/docs/benchmarks/2026-05-07-longmemeval-s.md ("August 31: correcting the May score", gbrain-hybrid recall_all@5 83.40%, recall_any@5 97.66%)

## Recomputed (pass)
- IterB t-CI [6.27, 9.79] ✓; paired diff CI [0.25, 3.76] ✓ (diffs 4,0,2,2,2.04); Fisher 20/249 vs 15/249 p=0.4837 ✓
- 3-knob: −0.01+0.81+1.21 = 2.01 ✓; 2.81+2.01+3.61 = 8.43 ✓; 2.01/8.43 = 23.8% ✓; 0.81/2.01 = 40.3% ✓; 1.21/3.61 = 33.5% ✓
- IterC F_HL 58.52 vs 22.68 = +35.84 ✓; F_MH −0.40 ✓
- LME: 68.16% Wilson [0.6143,0.7421] ✓; per-category 87.10/86.67/82.05/82.61/55.81/54.76/31.25 (n=16) ✓; 1.0000−0.9126 = 8.74 pp, 9.58% rel ✓
- 5.5.8 date/48 h/51–97% ✓ vs supplement S5.5.8
- gbrain numbers ✓ (search excerpt); but no citation in paper

## Defects (see StructuredOutput for quotes/fixes)
H1 §5.6 fingerprint paragraph: retrieval saturated at 1.0000 in every category (artifact per-category table), so category spread cannot be a retrieval-architecture property; artifact itself calls it "generator + judge limitations"; judge is gemini-2.5-flash on both benches and generator gpt-4.1-mini on both → "different judges" false; "identical" overclaims a qualitative mapping.
H2 §5.5.1 table: "~ baseline"/"mixed" hide 2.81% and 53.13% (+1.45); F_SH −10.08 and MA composite −4.36 (gate FAIL) omitted; "PASS" on F_HL has no gate; artifact verdict DOCUMENTED_INSUFFICIENT (2/4).
H3 §5.6 "win claim": no comparator in §5.6; artifact caveat 6 "No competitor re-run".
M4 §5.6 task accuracy: single batch (seed 42), 96 judge errors (32% of 297) + 3 generator 429s not disclosed; artifact says absolute 68.16% needs 5-batch + gpt-4o judge before paper claim.
M5 flag NOX_Q3_ITERC_ENABLED exists nowhere in repo except paper.
M6 "validated in §5.5.2" vs directional/not significant.
M7 §5.5 intro: IterB-stacked composition is INDETERMINATE (§5.5.8), not measured in §5.5.4.
M8 §5.5.4 3-knob "aggregate" = arithmetic sum of standalone knobs, none distinguishable from baseline.
M9 §5.5.6 "flips sign"/MA_U gain inside CI noise.
M10 §5.5.2 omits MA composite −3.53 / Overall −0.58 vs bare baseline (reason for opt-in).
M11 Self-Ask attribution: designed for multi-hop compositional questions (abstract), i.e. the F_MH class where IterC did not lift; IterC is upfront decomposition (adapter docstring), not Self-Ask's ask-then-answer follow-ups.
L12 Wilson LB 0.9872 is for session_hit@10, n=297 scored, not nDCG@10.
L13 "largest single-mechanism F_HL" — backbone swap gives +38.14 pp; qualify fixed backbone.
L14 "$0.0015/q" not in IterC artifacts; call count 1+N+1.
L15 gbrain uncited.
L16 abstention row overlaps categories.
L17 jargon "Q2 baseline" undefined.

Not re-reported (fixed in CHANGELOG v1.0.3): IterB CI/Fisher (B.1), gbrain number (B.6), transfer wording (B.7).
