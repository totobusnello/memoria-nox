# eval/lib — EverMemBench Efficiency Library

Reusable infra codifying Phase F+G+H lessons. Each module encodes a specific
lesson that cost $0.80–$3 in wasted runs before it was crystallised.

---

## Modules

### `preflight.sh` — billing path verifier

**Lesson:** `[[preflight-must-exercise-billing-path]]`

Phase H v1 (PR #368) routed via OpenRouter. `/v1/models` returned 200 OK on
auth, but the real `chat/completions` call 402'd on credits. A tiny real
completion (5 tokens, ~$0.0001) exercises auth + model access + billing
in one shot.

**Usage in `run-batch-*.sh`:**

```bash
source "$(dirname "$0")/../lib/preflight.sh"
preflight_billing "https://api.openai.com/v1" "$OPENAI_API_KEY" "gpt-4.1-mini" || exit 1
```

**Tests:** `eval/lib/preflight_test.sh` (no real API calls — mocks curl via PATH override).

---

### `harness_fresh.sh` — auto-purge wrapper for EverMemBench harness

**Lesson:** `[[evermembench-eval-gotchas-2026-05-28]]`

EverMemBench harness silently resumes from `answer_results_<batch>.json` if it
exists. This caused Phase G batch 004 to short-circuit the answer stage and
reuse stale Phase D answers — inflating scores by ~3–6 pp. The fix is to
unconditionally delete both `answer_results` and `evaluation_results` before
every run.

**Usage:**

```bash
source "$(dirname "$0")/../lib/harness_fresh.sh"
harness_run_fresh \
    --batch     "004" \
    --adapter   "nox_mem" \
    --eval-dir  "$EVAL" \
    --stages    "search answer evaluate" \
    --top-k     20
```

**Dry-run (no eval.cli call, only shows what would be deleted):**

```bash
HARNESS_DRY_RUN=1 harness_run_fresh --batch 004 --adapter nox_mem --eval-dir "$EVAL"
```

---

### `aggregate_5batch.py` — 5-batch CI computation

**Lesson:** `[[single-batch-gates-unreliable-5x-overstate]]`

Phase G batch 004 showed F_MH = 10.00% (+8 pp). 5-batch confirmation revealed
the true mean was 6.83% with 95% CI [3.97%, 9.69%]. The single-batch result
overstated the rerank benefit by ~3–4× in absolute terms. Any gate should use
the 95% CI lower bound, not the point estimate.

**Usage:**

```python
from eval.lib.aggregate_5batch import aggregate_5batch, gate_5batch

per_batch = {
    "004": {"F_MH": 10.00, "overall": 59.74, "MA_C": 68.00},
    "005": {"F_MH":  4.00, "overall": 63.44, "MA_C": 85.00},
    ...
}
agg = aggregate_5batch(per_batch)
# agg["F_MH"] == {mean: 6.83, stdev: 2.30, ci_lower_95: 3.97, ci_upper_95: 9.69, ...}

gate = gate_5batch(agg, baseline={"F_MH": 5.22, "overall": 62.22})
# gate["F_MH"]["verdict"] == "REJECT"  (ci_lower_95=3.97 < baseline=5.22)
```

**Tests:** `eval/lib/test_aggregate_5batch.py` — validates all Phase G 5-batch
numbers from `RESULTS-PHASEG-5BATCH.md`.

```bash
python eval/lib/test_aggregate_5batch.py
# or
python -m pytest eval/lib/test_aggregate_5batch.py -v
```

**Gate rule (both conditions required for SHIP):**
1. `mean - baseline > gate_threshold`
2. `ci_lower_95 - baseline > gate_threshold`

---

### `report_template.py` — MA-aware markdown report generator

**Lesson:** `[[memory-awareness-dimension-must-be-audited]]`

MA_C / MA_P / MA_U regressions were invisible at Phase G batch 004 (it was
already the worst MA batch). They only surfaced at 5-batch. Reports MUST
include all three MA sub-dims as mandatory rows.

`generate_report()` raises `ValueError` if any required dimension is absent
from the input — fail loudly rather than silently omit.

**Usage:**

```python
from eval.lib.report_template import generate_report

results = {
    "batch_id": "phaseH-v2-5batch",
    "per_batch": {
        "004": {"overall": 54.15, "F_MH": 10.00, "MA_C": 88.00,
                "MA_P": 64.00, "MA_U": 68.97, "F_SH": 89.80,
                "F_TP": 11.67, "F_HL": 24.36,
                "P_Style": 40.54, "P_Skill": 55.56, "P_Title": 65.31},
        ...
    },
}
baselines = {
    "Phase D (5-batch)":  {"overall": 62.22, "F_MH": 5.22, "MA_C": 81.40, ...},
    "MemOS GPT-4.1-mini": {"overall": 42.55, "F_MH": 18.88, "MA_C": 69.90, ...},
}
md = generate_report(results, baselines, phase_label="Phase H v2")
# Pass output_path= to write to disk
```

**Required dims:** `overall`, `F_SH`, `F_MH`, `F_TP`, `MA_C`, `MA_P`, `MA_U`,
`P_Style`, `P_Skill`, `P_Title`. `F_HL` is optional (shown as `—` if absent).

---

## Memory references (cristalizadas)

| memory | lesson |
|---|---|
| `[[preflight-must-exercise-billing-path]]` | Auth check != billing path |
| `[[evermembench-eval-gotchas-2026-05-28]]` | Harness resumes silently from prior JSON |
| `[[single-batch-gates-unreliable-5x-overstate]]` | Single-batch gates overstate 3–6× |
| `[[memory-awareness-dimension-must-be-audited]]` | MA regressions invisible in single batch |
