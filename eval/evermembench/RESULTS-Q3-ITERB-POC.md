# Q3 IterB POC — ReAct 5-batch Results

**Status:** harness ready — pending VPS 5-batch run.

This file is a placeholder produced by the POC PR (`feat/q3-iterB-poc-react`).
Final headline numbers + Set E (per-query rounds/overlap/cost) + 4-gate
verdict are emitted by `aggregate_phaseIterB_5batch.py` on the VPS after
the 5 sequential batches (004, 005, 010, 011, 016) complete against the
Phase H v2 pre-warmed DBs.

## Reference mechanism (Yao et al. 2022, arxiv:2210.03629)

ReAct loops up to `NOX_ITERB_MAX_ROUNDS` (default 5). Each round:

1. Orchestrator LLM (default `gpt-4.1-mini`) emits JSON with either:
   - `{"thought": "...", "action": "retrieve", "query": "..."}`
   - `{"thought": "...", "action": "answer", "answer": "..."}`
2. `retrieve` → hits `/api/search` with `top_k=10` (NOX_ITERB_PER_ROUND_TOPK)
3. Observation (top-3 chunk snippets) fed back into the scratchpad
4. Terminates on explicit `answer`, `max_rounds`, `cost_ceiling`
   (NOX_ITERB_COST_CEILING_USD, default $0.01), or `error`
5. Final context = scratchpad + RRF-merged union of all retrieve rounds

## 4-Gate criteria (per task spec)

| Gate | Threshold | Rationale |
|---|---|---|
| 1. F_MH lift | ≥ +3.00pp vs Phase H v2 (3.21% → ≥6.21%) | Primary canonical F_MH ceiling break |
| 2. Overall regression | ≥ -3.00pp | Allow some cost for orchestration |
| 3. MA composite | ≥ -3.00pp | Tolerance band |
| 4. Cost per query | ≤ $0.01 | Orchestration ceiling cap |

- **4/4 PASS** → SHIP DEFAULT candidate
- **3/4 PASS** → SHIP OPT-IN canonical F_MH ceiling break
- **≤2/4 PASS** → REJECT — Wave A/B/C ceiling holds, document insight

## Cheap orchestrator variant

Also tested via `NOX_ITERB_ORCHESTRATOR_LLM=gemini-2.5-flash-lite` (or
`gemini-3-flash` if billing path validated). Predicted further F_MH lift
if Backbone Matrix finding (nox-mem 1.6× more portable than MemOS across
backbones) generalizes to orchestration-stage too.

## Reference

- PR #393 — Q3 Iterative Retrieval spec
- PR #406 — Q3 IterC POC Self-Ask (sibling, wrong class for F_MH — 2/4 gates)
- PR #395 — D69 cravada (Wave A/B/C F_MH ceiling 7.25%)
- D72 — F_MH gap reframe as EverMemBench-structural (still worth empirical refute)
