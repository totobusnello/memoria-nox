# Per-method Benchmark Phase B — intra-system method-config ablation matrix (Lab Q1)

> **Phase B = nox-mem internal method-config matrix.** Same corpus, same gold, vary only the retrieval method (FTS5-only / vec0-only / hybrid RRF / +salience / +section_boost / +source_type_boost / +hard_mutex / +temporal_spike v2 / +reranker-off). Output: cross-method nDCG@10 / MRR / Recall@10 table + per-category breakdown.
>
> Sister spec to `2026-05-21-per-method-benchmark-comparison.md` (Phase A inter-system Mem0/Zep/EverCore/HyperMem). **Distinct scope, complementary purpose.** Naming kept "per-method" for memory-line continuity; an equally valid name is "method-config ablation matrix v2 (Wave A canonical config validation)".

**Status:** SPEC — implementation pending, gated em D49 phase 2 closure (D50 decision ETA 2026-05-27).
**Data:** 2026-05-24
**ID:** Q4c (parte do pilar Q — Quality; complementa Q4b inter-system).
**Owner:** Toto (decisão); scientist-high (execução planejada Lab Q1).
**Esforço estimado:** ~12-18h (2-3h spec ✅ + 6-10h harness extension + 2-4h exec full run + 2-3h writeup).
**Dependências:**
- D49 phase 2 closed (shadow telemetry off antes do canonical run — evita ruído na config "salience=shadow")
- Wave A merged ✅ (G10/G10b/G10c mutex, temporal_spike v2)
- Q4 harness skeleton ✅ (`eval/q4-comparison/runner.py` adapter pattern)
- Existing ablation tooling ✅ (`paper/publication/baselines/entity_ablation_eval.py` + `run_locomo_ablations.sh`)
- Memory hard rule `[[eval-harness-must-explicit-isolate-db]]` (NOX_DB_PATH guard + port 18803)
**Bloqueia:**
- Paper §6.4 (per-category contribution table)
- Wave A canonical config validation — "which features actually carry the +18.8%"
- Lab Q1 reranker delta measurement (D01 v3) — needs per-method baseline first
**Cross-ref:**
- `specs/2026-05-21-per-method-benchmark-comparison.md` (Phase A, sister inter-system)
- `paper/publication/baselines/entity_ablation_eval.py` — driver to extend
- `paper/publication/baselines/run_locomo_ablations.sh` — orchestrator pattern (env-toggle + port-18803 isolation)
- `eval/q4-comparison/runner.py` + `aggregate.py` — output schema + metric primitives
- `audits/2026-05-21-G10b-per-category-mutex-ablation.md`
- `audits/2026-05-21-G10c-per-style-mutex-ablation.md`
- `docs/DECISIONS.md` D43 (Q4 gate), D48 (mutex canonical), D49 (shadow telemetry)
- Memory: `[[g10-mutex-validated-2026-05-20]]`, `[[g4-wave-a-results-2026-05-19]]`, `[[g8-source-type-boost-live-2026-05-20]]`, `[[temporal-spike-v2-win-2026-05-20]]`, `[[qap-pillars-strategic-decision]]`

---

## 1. Problema

Wave A landed +18.8% nDCG@10 vs G3 baseline. **Qual feature individual carregou esse delta?** G3-G12 ablation series mediu cada knob isoladamente em rolling snapshots distintos — cada audit refletia a corpus + DB state daquele momento. Hoje (pós-Wave A canonical) **não existe medição cross-method em DB único frozen** que valide:

1. Qual é o lift incremental de cada feature ativa quando todas as outras estão em production-default?
2. Quais features são redundantes (lift colapsa quando combinadas)?
3. Onde está a regressão silenciosa? G10/G10b cravou multi-hop -3.95% / adversarial -2.95% — confirmar que G10c per-style mutex aliviou mas não desfaz.
4. Qual config é canonical-defensible no paper §6.4 — "boost stack contributes X% por feature em DB frozen Y"?

**Sem Phase B (per-method matrix):**
- Paper §6.4 fica vago — "Wave A combines section_boost + source_type_boost + hard_mutex + temporal_spike v2" sem desglosse atribuível
- Lab Q1 reranker (D01 v3) não tem baseline limpo — qualquer ganho contaminado por feature stack pré-existente
- Wave A canonical config não é validada — se feature X tem lift 0% no DB atual, podemos drop-ar e simplificar
- D48 close revisita continua aberta — "mutex sozinho canonical" precisa rerun em corpus frozen pós-G10c
- ROADMAP §6 Lab gate aberto — não há "method-config canonical" reference pra GTM (paper §6.4 / blog Q4 release)

**Per-method vs Per-system distinção:**
- Phase A (inter-system, spec 2026-05-21): **nox-mem vs Mem0/Zep/EverCore/HyperMem** — cross-product positioning
- Phase B (intra-system, esta spec): **nox-mem FTS5-only vs nox-mem hybrid vs nox-mem +salience vs ...** — feature attribution
- Ambas usam mesmo dataset (LongMemEval + LoCoMo + entity-eval golden) — comparabilidade entre fases preservada

---

## 2. Objetivo

Gerar tabela 12-config × 3-dataset × 4-metric **+ per-category breakdown** medindo cada method config no MESMO corpus frozen com isolamento total.

| Eixo | Valor |
|---|---|
| **Configs** | 12 method variants (§3 matrix) |
| **Datasets** | LongMemEval (n=500 ou stratified 100), LoCoMo (n=10), entity-eval-golden (n=78 pós-cleanup) |
| **Métricas** | nDCG@10, MRR, Recall@10, P@5 |
| **Breakdowns** | per-category (single-hop, multi-hop, temporal-reasoning, adversarial, abstention, knowledge-update, open-domain, single-session-preference) |
| **Runs** | 3 (mean ± stddev) |
| **Cost** | **zero externo** — só nox-mem self-hosted, Gemini embeddings gratis dentro do quota |
| **Wall-clock** | 30-60min full run (12 configs × 3 datasets × n=~588 × 3 runs ≈ 63k queries; ~50ms avg = ~50min serial) |

**Goal numérico:** publicar tabela 12×3×4 com **valores reais** + **stddev de 3 runs** + **per-category Δ vs baseline** + **Cohen's d significance**. Fechar paper §6.4 e dar baseline limpo pra D01 v3 reranker.

---

## 3. Test matrix — 12 method configs

> Naming convention: `<retrieval-base>+<boost-stack>+<mutex>+<spike>+<reranker>`. Each config maps a specific bundle of NOX_* env toggles. Baseline (M00) = production-canonical config pós-Wave A.

| ID | Config name | FTS5 | vec0 (Gemini) | section_boost | source_type_boost | tier_boost | salience | hard_mutex (G10) | temporal_spike v2 | expansion | semantic_pool | reranker (D01) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **M00** | **prod-canonical (Wave A)** | ✅ | ✅ | ✅ | ✅ | ✅ | shadow | ✅ G10c per-style | ✅ | ✅ | 40 | off |
| **M01** | fts5-only (bm25 raw) | ✅ | ❌ | ❌ | ❌ | ❌ | off | ❌ | ❌ | ❌ | 0 | off |
| **M02** | vec0-only (Gemini dense raw) | ❌ | ✅ | ❌ | ❌ | ❌ | off | ❌ | ❌ | ❌ | 40 | off |
| **M03** | hybrid-rrf-naked (FTS5+vec0+RRF, no boosts/mutex/spike) | ✅ | ✅ | ❌ | ❌ | ❌ | off | ❌ | ❌ | ❌ | 40 | off |
| **M04** | M03+section_boost only | ✅ | ✅ | ✅ | ❌ | ❌ | off | ❌ | ❌ | ❌ | 40 | off |
| **M05** | M03+source_type_boost only | ✅ | ✅ | ❌ | ✅ | ❌ | off | ❌ | ❌ | ❌ | 40 | off |
| **M06** | M03+tier_boost only | ✅ | ✅ | ❌ | ❌ | ✅ | off | ❌ | ❌ | ❌ | 40 | off |
| **M07** | M03+salience active (NOX_SALIENCE_MODE=active) | ✅ | ✅ | ❌ | ❌ | ❌ | active | ❌ | ❌ | ❌ | 40 | off |
| **M08** | M03+all-boosts (section+source_type+tier) NO mutex | ✅ | ✅ | ✅ | ✅ | ✅ | off | ❌ | ❌ | ❌ | 40 | off |
| **M09** | M08+hard_mutex G10 unconditional | ✅ | ✅ | ✅ | ✅ | ✅ | off | ✅ G10 | ❌ | ❌ | 40 | off |
| **M10** | M08+hard_mutex G10c per-style | ✅ | ✅ | ✅ | ✅ | ✅ | off | ✅ G10c | ❌ | ❌ | 40 | off |
| **M11** | M10+temporal_spike v2 (anchor regex+median+confidence-tier) | ✅ | ✅ | ✅ | ✅ | ✅ | off | ✅ G10c | ✅ v2 | ❌ | 40 | off |

**Lift attribution (read column deltas):**
- M01 vs M02 = lexical vs dense retrieval contribution
- M02 vs M03 = RRF fusion lift over dense-only
- M04 vs M03 = section_boost isolated lift
- M05 vs M03 = source_type_boost isolated lift
- M06 vs M03 = tier_boost isolated lift (validate INERT hypothesis from G4)
- M07 vs M03 = salience isolated lift (validate G7 NEUTRAL hypothesis)
- M08 vs M03 = additive boost stack lift (no mutex)
- M09 vs M08 = mutex G10 unconditional contribution
- M10 vs M09 = G10c per-style refinement contribution
- M11 vs M10 = temporal_spike v2 contribution
- **M00 vs M11** = expansion + shadow telemetry overhead (should be ~0; if material, surfaces hidden cost)

**Anti-config notes:**
- Reranker (D01) intentionally OFF in all 12 — Phase B is the **pre-reranker** baseline. Reranker comparison lives em Lab Q1 follow-up spec (`2026-05-21-neural-reranker-design.md`).
- `NOX_DISABLE_EXPANSION=1` in M01-M10 to isolate boost/mutex contribution from query expansion noise. M00 + M11 keep expansion ON to match prod.
- `NOX_RERANKER_MODE=off` everywhere — same reason.

---

## 4. Env-toggle reference (per-config configuration)

> Source of truth: `paper/publication/baselines/run_locomo_ablations.sh` + `entity_ablation_eval.py` already expose all the knobs except mutex/spike (added Wave A). Phase B harness extends the toggle list.

### 4.1 Existing knobs (production code, no new wiring needed)

| Env var | Values | Default | Effect |
|---|---|---|---|
| `NOX_FTS_DISABLE` | `1` / unset | unset | When `1`, skip FTS5 BM25 leg; semantic-only retrieval |
| `NOX_SEMANTIC_DISABLE` | `1` / unset | unset | When `1`, skip vec0 leg; FTS5-only retrieval |
| `NOX_DISABLE_BOOSTS` | `1` / unset | unset | When `1`, kill section_boost + source_type_boost + tier_boost in one flag |
| `NOX_DISABLE_EXPANSION` | `1` / unset | unset | Disable query expansion (synonym/morphology) |
| `NOX_SEMANTIC_POOL_SIZE` | int | 40 | Top-K from vec0 leg before RRF (0 = effectively disable) |
| `NOX_SALIENCE_MODE` | `off` / `shadow` / `active` | `shadow` | Salience multiplier (recency × pain × importance) |
| `NOX_RERANKER_MODE` | `off` / `bge` / `cohere` | `off` | Neural reranker layer (off in Phase B) |
| `NOX_DB_PATH` | path | (prod path) | DB isolation — MANDATORY override for Phase B |
| `NOX_API_PORT` | int | 18802 | 18803 reserved for eval (prevent prod contention) |

### 4.2 Knobs needing per-feature toggle (Phase B harness extension)

These are currently bundled under `NOX_DISABLE_BOOSTS=1`. Phase B requires per-feature granularity. **Action item:** small PR adding the 3 flags below to `src/search/ranker.ts` (estimated <50 LOC).

| Env var | Values | Default | Effect | Needed for |
|---|---|---|---|---|
| `NOX_SECTION_BOOST_DISABLE` | `1` / unset | unset | Disable section_boost (compiled/frontmatter/timeline weights) ONLY | M03, M05, M06, M07 |
| `NOX_SOURCE_TYPE_BOOST_DISABLE` | `1` / unset | unset | Disable source_type_boost ONLY | M03, M04, M06, M07 |
| `NOX_TIER_BOOST_DISABLE` | `1` / unset | unset | Disable tier_boost ONLY | M03, M04, M05, M07 |
| `NOX_MUTEX_MODE` | `off` / `unconditional` / `per-category` / `per-style` | `per-style` | G10 variants (G10 = unconditional, G10b = per-category, G10c = per-style) | M03-M08 (`off`), M09 (`unconditional`), M10/M11 (`per-style`) |
| `NOX_TEMPORAL_SPIKE_V2` | `off` / `on` | `on` | Temporal anchor regex + median + confidence-tier (PR #181) | M00-M10 (`off`), M11 (`on`) |

**Implementation note:** these are pure feature flags — no schema changes, no data migration. Production canonical config = all flags at defaults = M00. Failure mode if PR not merged: harness falls back to coarse `NOX_DISABLE_BOOSTS=1` and M04/M05/M06 collapse into a single "no-boosts" row, losing per-feature attribution (acceptable partial deliverable).

---

## 5. Methodology — non-negotiables

### 5.1 DB isolation (CRITICAL — postmortem 2026-05-19)

Memory `[[eval-harness-must-explicit-isolate-db]]` cravou:
- `NOX_DB_PATH` MUST point to `/tmp/per-method-bench/<config-id>.db` (or similar isolated path)
- `NOX_API_PORT=18803` (not 18802)
- `NOX_EVAL_ISOLATION_OVERRIDE` flag for explicit acknowledgement
- Pre-flight check: `_check_eval_isolation()` from `entity_ablation_eval.py` reused verbatim
- 4-layer defense (config + harness + API + DB filesystem inode check)

### 5.2 DB strategy — frozen snapshot

**Choice:** single frozen DB clone, mutated only by per-config env vars at retrieval time. Embeddings/chunks/entities IDENTICAL across all 12 configs.

```bash
# Snapshot prod DB (or g9.db post-G10 validated state) into isolated bench path
cp -p /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
      /tmp/per-method-bench/frozen-snapshot.db
sha256sum /tmp/per-method-bench/frozen-snapshot.db > /tmp/per-method-bench/SHA256SUMS

# Verify state (chunks count + golden set coverage)
python eval/verify_frozen_snapshot.py \
  --db /tmp/per-method-bench/frozen-snapshot.db \
  --expect-chunks-min 60000 \
  --expect-entities-min 180

# All 12 configs read the SAME DB file. Env vars vary retrieval logic only.
```

**Why frozen snapshot vs separate DBs:** ablation is about **retrieval method**, not about **data state**. Separate DBs would re-introduce G6 fiasco (G5 V3 0.6237 vs G6 0.5845 was 100% DB swap, not code change). Same chunks/embeddings + varying retrieval logic isolates the variable cleanly.

**G6 lesson cravado em memory `[[always-verify-eval-db-and-harness-before-comparing]]`** — sha256 + chunk-count + golden + harness 4-check mandatory antes de comparar.

### 5.3 Golden set strategy

**Three datasets, three golden sources:**

1. **entity-eval-golden (n=78)** — `paper/publication/data/entity-eval-2026-05-19/` — primary attribution dataset (where boost features have signal)
2. **LongMemEval (n=500 ou n=100 stratified)** — `eval/longmemeval/dry-run-sample.json` — primary general-quality dataset
3. **LoCoMo (n=10)** — `eval/locomo/dry-run-sample.json` — secondary multi-hop sanity check

**Why all three:** entity-eval shows where feature stack helps (G4-G12 series); LongMemEval is the GTM-claim dataset (Phase A parity); LoCoMo isolates multi-hop where G10 unconditional regressed.

### 5.4 Sequential execution + 3 runs

Same VPS hardware (current IP per memory `[[vps-ip-change-2026-05-20]]`) or local Mac M-class. No mixing.

**Sequential, not parallel:** each config restarts the API (`pm2 restart nox-mem-eval` ou similar) to ensure env vars rebind in fresh process. Parallel would race PRAGMA + LRU caches.

3 runs per config × 12 configs × 3 datasets = **108 sub-runs**. Mean ± stddev reported per cell.

### 5.5 Significance testing

Multi-comparison correction: 12 configs × 3 datasets × 4 metrics × 8 categories = **1152 cells**. Apply **Benjamini-Hochberg FDR** at α=0.05 only to pre-registered hypotheses:

- H1: M00 ≥ M03 (production canonical beats naked hybrid) — must hold
- H2: M11 ≥ M10 (temporal v2 contributes positively) — confirms PR #181 lift not noise
- H3: M10 ≥ M09 ≥ M08 (per-style mutex > unconditional mutex > no mutex; G10c chain)
- H4: M07 == M03 (salience active vs off — confirm G7 NEUTRAL hypothesis on Wave A corpus)
- H5: M06 == M03 (tier_boost INERT confirmation from G4)
- H6: M04 + M05 ≥ M08 (additive lift; if violated → redundancy detected, motivates mutex)

Effect size: Cohen's d per pairwise comparison. Magnitude small (0.2) / medium (0.5) / large (0.8).

**Pre-register hypotheses in audit doc BEFORE run** (no p-hacking).

---

## 6. Harness design — `eval/per-method-comparison/`

> **Reuse + extend, not greenfield.** The pattern lives in `paper/publication/baselines/run_locomo_ablations.sh` + `entity_ablation_eval.py`. Phase B harness wraps these and emits Q4-runner-compatible output.

### 6.1 Directory layout

```
eval/per-method-comparison/
├── runner.py                  # main entry — adapts Q4 runner pattern
├── method_configs.py          # 12 named configs → env dict mapping
├── aggregate.py               # cross-config + per-category aggregator
├── isolation_guard.py         # _check_eval_isolation() (reused from entity_ablation_eval)
├── verify_frozen_snapshot.py  # SHA256 + chunk count + golden coverage gate
├── adapters/
│   └── nox_mem_method.py      # variant of eval/q4-comparison/adapters/nox_mem.py
│                              # extended w/ config-id parameter
├── output/
│   ├── <config-id>/
│   │   ├── run0.json
│   │   ├── run1.json
│   │   ├── run2.json
│   │   └── aggregate.json
│   ├── _cross_config.json     # cross-method comparison table
│   ├── _cross_config.md       # markdown rendering for paper §6.4
│   └── _significance.json     # FDR-corrected p-values + Cohen's d
└── README.md
```

### 6.2 Adapter interface (variant of Q4 nox_mem adapter)

```python
# eval/per-method-comparison/adapters/nox_mem_method.py (pseudocode)

from eval.q4_comparison.adapters.nox_mem import (
    setup as q4_setup,
    teardown as q4_teardown,
)

NAME = "nox-mem-method"

def setup_with_config(config_id: str, env_overrides: dict[str, str]) -> dict:
    """
    Configure the eval instance for a specific method config.
    
    1. apply env_overrides to os.environ (NOX_FTS_DISABLE, NOX_SALIENCE_MODE, etc.)
    2. restart nox-mem-api process (pm2 restart or subprocess kill + spawn)
    3. wait for /api/health ready
    4. assert isolation guard pass (port 18803, NOX_DB_PATH ≠ prod)
    5. return readiness metadata
    """
    ...

def search(query: str, k: int = 10) -> list[dict]:
    """Same shape as q4 adapter — returns top-k chunks with scores + IDs."""
    ...

def teardown() -> None:
    """Clear env_overrides + restart with defaults (defensive cleanup)."""
    ...
```

### 6.3 method_configs.py — config registry

```python
# eval/per-method-comparison/method_configs.py (pseudocode)

CONFIGS = {
    "M00_prod_canonical": {
        # defaults — empty dict means "use production defaults" (Wave A canonical)
    },
    "M01_fts5_only": {
        "NOX_SEMANTIC_DISABLE": "1",
        "NOX_DISABLE_BOOSTS": "1",
        "NOX_DISABLE_EXPANSION": "1",
        "NOX_SALIENCE_MODE": "off",
        "NOX_MUTEX_MODE": "off",
        "NOX_TEMPORAL_SPIKE_V2": "off",
    },
    "M02_vec0_only": {
        "NOX_FTS_DISABLE": "1",
        "NOX_DISABLE_BOOSTS": "1",
        "NOX_DISABLE_EXPANSION": "1",
        "NOX_SALIENCE_MODE": "off",
        "NOX_MUTEX_MODE": "off",
        "NOX_TEMPORAL_SPIKE_V2": "off",
    },
    "M03_hybrid_rrf_naked": {
        "NOX_DISABLE_BOOSTS": "1",
        "NOX_DISABLE_EXPANSION": "1",
        "NOX_SALIENCE_MODE": "off",
        "NOX_MUTEX_MODE": "off",
        "NOX_TEMPORAL_SPIKE_V2": "off",
    },
    "M04_hybrid_plus_section_boost": {
        "NOX_SOURCE_TYPE_BOOST_DISABLE": "1",
        "NOX_TIER_BOOST_DISABLE": "1",
        "NOX_DISABLE_EXPANSION": "1",
        "NOX_SALIENCE_MODE": "off",
        "NOX_MUTEX_MODE": "off",
        "NOX_TEMPORAL_SPIKE_V2": "off",
    },
    "M05_hybrid_plus_source_type_boost": {
        "NOX_SECTION_BOOST_DISABLE": "1",
        "NOX_TIER_BOOST_DISABLE": "1",
        "NOX_DISABLE_EXPANSION": "1",
        "NOX_SALIENCE_MODE": "off",
        "NOX_MUTEX_MODE": "off",
        "NOX_TEMPORAL_SPIKE_V2": "off",
    },
    "M06_hybrid_plus_tier_boost": {
        "NOX_SECTION_BOOST_DISABLE": "1",
        "NOX_SOURCE_TYPE_BOOST_DISABLE": "1",
        "NOX_DISABLE_EXPANSION": "1",
        "NOX_SALIENCE_MODE": "off",
        "NOX_MUTEX_MODE": "off",
        "NOX_TEMPORAL_SPIKE_V2": "off",
    },
    "M07_hybrid_plus_salience": {
        "NOX_DISABLE_BOOSTS": "1",
        "NOX_DISABLE_EXPANSION": "1",
        "NOX_SALIENCE_MODE": "active",
        "NOX_MUTEX_MODE": "off",
        "NOX_TEMPORAL_SPIKE_V2": "off",
    },
    "M08_hybrid_plus_all_boosts_no_mutex": {
        "NOX_DISABLE_EXPANSION": "1",
        "NOX_SALIENCE_MODE": "off",
        "NOX_MUTEX_MODE": "off",
        "NOX_TEMPORAL_SPIKE_V2": "off",
    },
    "M09_M08_plus_mutex_unconditional": {
        "NOX_DISABLE_EXPANSION": "1",
        "NOX_SALIENCE_MODE": "off",
        "NOX_MUTEX_MODE": "unconditional",
        "NOX_TEMPORAL_SPIKE_V2": "off",
    },
    "M10_M08_plus_mutex_per_style": {
        "NOX_DISABLE_EXPANSION": "1",
        "NOX_SALIENCE_MODE": "off",
        "NOX_MUTEX_MODE": "per-style",
        "NOX_TEMPORAL_SPIKE_V2": "off",
    },
    "M11_M10_plus_temporal_spike_v2": {
        "NOX_DISABLE_EXPANSION": "1",
        "NOX_SALIENCE_MODE": "off",
        "NOX_MUTEX_MODE": "per-style",
        "NOX_TEMPORAL_SPIKE_V2": "on",
    },
}
```

### 6.4 Runner skeleton (extends Q4 runner)

```python
# eval/per-method-comparison/runner.py (pseudocode)

import json, os, time, subprocess
from pathlib import Path
from method_configs import CONFIGS
from adapters.nox_mem_method import setup_with_config, search, teardown

DATASETS = ["entity-eval-golden", "longmemeval", "locomo"]
RUNS = 3
K = 10
FROZEN_DB = "/tmp/per-method-bench/frozen-snapshot.db"
ISOLATED_PORT = 18803

def isolation_preflight():
    """4-layer defense: env vars + port + DB path + filesystem inode."""
    assert os.environ.get("NOX_DB_PATH") == FROZEN_DB
    assert os.environ.get("NOX_API_PORT") == str(ISOLATED_PORT)
    # ... reuse _check_eval_isolation from entity_ablation_eval
    
def restart_api_with_env(env_overrides: dict):
    """Restart nox-mem-api with merged env (defaults + overrides)."""
    # pm2 restart nox-mem-eval --update-env (or subprocess.Popen if no pm2)
    # wait for /api/health 200 OK on port 18803 (timeout 30s)
    ...
    
def run_config(config_id: str, env_overrides: dict):
    isolation_preflight()
    restart_api_with_env(env_overrides)
    
    for dataset in DATASETS:
        for run_idx in range(RUNS):
            results = []
            queries = load_dataset(dataset)
            for q in queries:
                t0 = time.perf_counter()
                retrieved = search(q["query"], k=K)
                latency_ms = (time.perf_counter() - t0) * 1000
                results.append({
                    "query_id": q["id"],
                    "category": q.get("category"),
                    "retrieved": [r["id"] for r in retrieved],
                    "scores": [r["score"] for r in retrieved],
                    "gold": q["gold_chunk_ids"],
                    "latency_ms": latency_ms,
                })
            
            out = Path(f"eval/per-method-comparison/output/{config_id}/{dataset}_run{run_idx}.json")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps({
                "meta": {
                    "config_id": config_id,
                    "dataset": dataset,
                    "run_idx": run_idx,
                    "env_overrides": env_overrides,
                    "frozen_db_sha256": Path("/tmp/per-method-bench/SHA256SUMS").read_text(),
                },
                "results": results,
            }, indent=2))

def main():
    Path(FROZEN_DB).exists() or sys.exit("frozen snapshot missing — run snapshot step first")
    
    for config_id, env_overrides in CONFIGS.items():
        run_config(config_id, env_overrides)
        teardown()  # reset env to defaults
    
    # cross-config aggregation
    subprocess.run(["python", "eval/per-method-comparison/aggregate.py"], check=True)

if __name__ == "__main__":
    main()
```

### 6.5 Aggregator — extends `eval/q4-comparison/aggregate.py`

Reuse `ndcg_at_k`, `recall_at_k`, `reciprocal_rank`, `percentile` from Q4 aggregator. Add:

- **Per-category breakdown** — group queries by `category` field, recompute metrics per group
- **Cross-config table** — emit markdown 12×4 table for paper §6.4
- **Significance** — Welch t-test (scipy) + Cohen's d + Benjamini-Hochberg FDR per pre-registered hypothesis (§5.5)
- **Latency tracking** — p50/p95/p99 per config (some configs may be materially slower; surface that)

---

## 7. Output artifacts

### 7.1 Raw data layout

```
eval/per-method-comparison/output/
├── M00_prod_canonical/
│   ├── entity-eval-golden_run0.json
│   ├── entity-eval-golden_run1.json
│   ├── entity-eval-golden_run2.json
│   ├── longmemeval_run0.json
│   ├── ... (3 runs × 3 datasets = 9 files per config)
│   └── aggregate.json    (mean ± stddev all metrics + per-category)
├── M01_fts5_only/...
├── ... (M00-M11 = 12 dirs)
├── _cross_config.json     (machine-readable comparison)
├── _cross_config.md       (markdown for paper §6.4)
└── _significance.json     (FDR + Cohen's d per H1-H6)
```

### 7.2 Summary audit template

`audits/2026-MM-DD-per-method-benchmark-phase-b.md`:

#### Cross-config nDCG@10 table (entity-eval-golden, mean ± stddev across 3 runs)

| Config | ID | nDCG@10 | MRR | Recall@10 | P@5 | Δ vs M00 nDCG | p-FDR |
|---|---|---|---|---|---|---|---|
| M00 prod-canonical | baseline | _ ± _ | _ ± _ | _ ± _ | _ ± _ | — | — |
| M01 fts5-only | drop -dense | _ ± _ | _ ± _ | _ ± _ | _ ± _ | _ pp | _ |
| M02 vec0-only | drop -lex | _ ± _ | _ ± _ | _ ± _ | _ ± _ | _ pp | _ |
| M03 hybrid-naked | drop -boosts | _ ± _ | _ ± _ | _ ± _ | _ ± _ | _ pp | _ |
| M04 +section_boost | iso boost A | _ ± _ | _ ± _ | _ ± _ | _ ± _ | _ pp | _ |
| M05 +source_type_boost | iso boost B | _ ± _ | _ ± _ | _ ± _ | _ ± _ | _ pp | _ |
| M06 +tier_boost | iso boost C | _ ± _ | _ ± _ | _ ± _ | _ ± _ | _ pp | _ |
| M07 +salience active | iso salience | _ ± _ | _ ± _ | _ ± _ | _ ± _ | _ pp | _ |
| M08 +all-boosts (no mutex) | additive stack | _ ± _ | _ ± _ | _ ± _ | _ ± _ | _ pp | _ |
| M09 +mutex unconditional | G10 | _ ± _ | _ ± _ | _ ± _ | _ ± _ | _ pp | _ |
| M10 +mutex per-style | G10c | _ ± _ | _ ± _ | _ ± _ | _ ± _ | _ pp | _ |
| M11 +temporal_spike v2 | full Wave A | _ ± _ | _ ± _ | _ ± _ | _ ± _ | _ pp | _ |

#### Per-category Δ vs M00 (sample, full table per dataset)

| Category | M01 | M03 | M04 | M08 | M10 | M11 |
|---|---|---|---|---|---|---|
| single-hop | _ pp | _ pp | _ pp | _ pp | _ pp | _ pp |
| multi-hop | _ pp | _ pp | _ pp | _ pp | _ pp | _ pp |
| temporal-reasoning | _ pp | _ pp | _ pp | _ pp | _ pp | _ pp |
| adversarial | _ pp | _ pp | _ pp | _ pp | _ pp | _ pp |
| open-domain | _ pp | _ pp | _ pp | _ pp | _ pp | _ pp |
| abstention | _ pp | _ pp | _ pp | _ pp | _ pp | _ pp |
| knowledge-update | _ pp | _ pp | _ pp | _ pp | _ pp | _ pp |
| single-session-preference | _ pp | _ pp | _ pp | _ pp | _ pp | _ pp |

#### Pre-registered hypothesis verdicts

| H | Claim | Verdict | Cohen's d | p-FDR |
|---|---|---|---|---|
| H1 | M00 ≥ M03 | _ (✅/❌) | _ | _ |
| H2 | M11 ≥ M10 | _ (✅/❌) | _ | _ |
| H3 | M10 ≥ M09 ≥ M08 | _ (✅/❌) | _ | _ |
| H4 | M07 == M03 (NEUTRAL) | _ (✅/❌) | _ | _ |
| H5 | M06 == M03 (INERT) | _ (✅/❌) | _ | _ |
| H6 | M04 + M05 ≥ M08 (additive) | _ (✅/❌) | _ | _ |

#### Honest writeup section (to fill at exec time)

- **Carrying features (large d > 0.5):** [fill — likely M04, M05, M11 per G3-G12 prior]
- **Inert features (d < 0.2):** [fill — confirm/refute G4 tier_boost INERT + G7 salience NEUTRAL]
- **Redundancies (M08 < M04 + M05):** [fill — motivates mutex if confirmed]
- **Per-category regressions:** [fill — multi-hop expected weak per G10b]
- **Latency cost:** [fill — does each added feature add p95?]
- **Wave A canonical config validation:** [fill — M00 vs M11 should be ~0 if expansion + shadow are no-cost]

---

## 8. Risks & mitigations

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Per-feature env toggle PR not merged (M04-M07 collapse) | MEDIUM | MEDIUM | Falls back to coarse `NOX_DISABLE_BOOSTS=1`; M04-M07 merge into single "no-boosts" row; partial deliverable acceptable |
| Shadow telemetry D49 phase 2 contamination | HIGH (if not gated) | HIGH | Hard gate — Phase B starts ONLY after D49 phase 2 closes (D50 decision ~2026-05-27) |
| Process restart between configs leaks state | MEDIUM | MEDIUM | Force `pm2 delete + spawn` (not just restart) per config; verify pid changes |
| Frozen snapshot corruption | LOW | CRITICAL | SHA256 gate pre-run; abort if hash mismatch; backup snapshot in `/tmp/per-method-bench/snapshot.db.bak` |
| LLM cost overrun | LOW | LOW | **Zero LLM in Phase B** — pure retrieval scoring (gold-chunk matching). No judge needed. |
| Per-category n too small (LoCoMo n=10) | HIGH | LOW | Report per-category Δ only when n ≥ 10 in that category; flag "n<10, descriptive only" otherwise |
| Multi-comparison false discovery | MEDIUM | MEDIUM | Pre-register only 6 hypotheses (§5.5); FDR α=0.05 on those; secondary cells reported descriptively |
| Config name confusion w/ Phase A | MEDIUM | LOW | Explicit §1 disambiguation + cross-ref in INDEX.md + audit doc title |
| Latency dominates wall-clock budget | LOW | LOW | 12 configs × 588 queries × 3 runs ≈ 21k queries; @ 50ms avg = 17min; @ 200ms p95 = 70min — within budget |
| `NOX_MUTEX_MODE` not yet ENV-driven (currently boolean) | MEDIUM | MEDIUM | Small PR to convert boolean → enum (4 values); document as Phase B pre-req (~30 LOC) |

---

## 9. Estimated effort

| Phase | Description | Hours |
|---|---|---|
| **A — this spec** | Design + INDEX update + PR | 2-3h ✅ (this PR) |
| **B1 — env-flag PR** | Add `NOX_SECTION_BOOST_DISABLE`, `NOX_SOURCE_TYPE_BOOST_DISABLE`, `NOX_TIER_BOOST_DISABLE`, `NOX_MUTEX_MODE` enum, `NOX_TEMPORAL_SPIKE_V2` to ranker.ts | 2-4h |
| **B2 — harness extension** | `eval/per-method-comparison/{runner,method_configs,aggregate,isolation_guard,verify_frozen_snapshot}.py` + nox_mem_method adapter | 4-6h |
| **C — frozen snapshot + verify** | Clone prod DB, SHA256 gate, golden coverage verify | 1-2h |
| **D — full run × 3 datasets × 12 configs × 3 runs** | Sequential exec on VPS or local Mac M-class | 2-4h wall-clock |
| **E — writeup + paper §6.4** | Aggregate audits + significance tests + paper update | 2-3h |
| **TOTAL** | | **~12-18h** (~50% of Phase A 25-35h, justifies Lab Q1 priority) |

---

## 10. Phasing & gates

```
A — Spec (THIS PR)              ─────[merge → INDEX updated]
                                       │
                                       ▼
B1 — Env-flag PR                ─────[small src change, ~30-50 LOC; can land any time]
                                       │
                                       ▼
   GATE: D49 phase 2 closed (D50 decision ETA 2026-05-27)
                                       │
                                       ▼
B2 — Harness extension          ─────[Lab Q1 work, reuse Q4 + entity_ablation tooling]
                                       │
                                       ▼
C — Frozen snapshot             ─────[~1h, SHA256 + golden coverage verify]
                                       │
                                       ▼
D — Full run                    ─────[2-4h wall-clock, isolated port 18803]
                                       │
                                       ▼
E — Writeup + paper §6.4        ─────[aggregate + significance + paper update]
                                       │
                                       ▼
   (optional) F — Lab Q1 reranker baseline reuse ─── D01 v3 measures Δ vs M11
```

**Hard gates:**
- **B2 start:** D49 phase 2 closed (shadow off) — else M00/M07 metrics contaminated
- **D start:** B1 + B2 merged + C verified — frozen snapshot SHA256 matches expected
- **E publish:** all 12 configs × 3 datasets × 3 runs completed without isolation guard fires

**Cancel criteria:**
- If B1 env-flag PR rejected → fall back to coarse `NOX_DISABLE_BOOSTS=1` partial deliverable (M04-M07 merge); proceed with M00, M01, M02, M03, M08-M11 only
- If frozen snapshot golden coverage drops (chunks count < 60k) → halt + investigate prod drift before snapshot
- If 2+ configs fail isolation guard → escalate harness bugs to Toto before continuing

---

## 11. Success criteria

When fully executed (post-Phase E):

1. **Cross-config table populated** — 12 configs × 3 datasets × 4 metrics + per-category breakdown
2. **Statistical significance** — 6 pre-registered hypotheses verdicts (FDR-corrected)
3. **Raw JSON preserved** in `eval/per-method-comparison/output/` (reproducible)
4. **Paper §6.4 updated** — "Feature attribution: each component contributes X pp" with honest numbers
5. **Wave A canonical validation** — M00 vs M11 Δ ≈ 0 OR motivates simplification PR
6. **Inert feature surface** — if M06 (tier_boost) confirmed INERT on Wave A corpus, queue removal PR
7. **Memory line closed** — `[[g4-wave-a-results-2026-05-19]]` superseded by Phase B audit reference
8. **D01 v3 baseline ready** — M11 = canonical "pre-reranker" config for Lab Q1 reranker delta measurement
9. **Q/A/P pilar Q closure step** — per-method attribution complements Phase A vs-world numbers

---

## 12. Open questions (for Toto resolution before Phase B start)

- [ ] **Frozen snapshot source:** prod nox-mem.db (current state, ~70k chunks) ou g9.db post-G10 validated (69495 chunks, mutex-canonical state)? → **default prod current** (más representative of GTM claim baseline). Override `--snapshot g9` if Toto prefers G10-validated comparison.
- [ ] **Sample sizes:** LongMemEval full n=500 ou stratified n=100 (faster, lower n per category)? → **default n=100 stratified** (3-4x faster, sufficient power for H1-H6); upgrade to n=500 if reviewer asks.
- [ ] **Hardware:** VPS or local Mac M-class? → **default VPS** (isolated port 18803, prod parity); fall back local if VPS busy.
- [ ] **Phase B owner:** scientist-high or executor-high? → **default scientist-high** (analysis-heavy + hypothesis pre-registration discipline).
- [ ] **Reranker (D01) inclusion:** add as 13th config M12 to Phase B? → **default NO** — keep reranker baseline measurement in dedicated Lab Q1 spec; Phase B = pre-reranker reference.
- [ ] **Publish raw data:** mirror `output/` to HF dataset (`nox-mem-evidence/per-method-attribution-2026-05`) for external repro? → **default YES** (Autonomy pillar — transparency).
- [ ] **Run frequency:** one-shot for paper §6.4 OR continuous CI gate (nightly per-method matrix)? → **default one-shot** (post-D49); CI gate is Lab Q2 future scope.

---

## 13. NÃO FAZEMOS (anti-scope)

- ❌ NÃO comparar vs Mem0/Zep/EverCore/HyperMem aqui — that is Phase A inter-system (sister spec)
- ❌ NÃO incluir reranker (D01) — pre-reranker baseline only; reranker delta = Lab Q1 follow-up
- ❌ NÃO normalizar across datasets — entity-eval has boost signal, LongMemEval may not; report per-dataset honestly
- ❌ NÃO usar LLM-judge — Phase B is pure retrieval scoring (gold-chunk matching); zero LLM cost
- ❌ NÃO rodar antes de D49 phase 2 closed — shadow telemetry contaminates M00/M07
- ❌ NÃO testar mais que 12 configs — combinatorial explosion (2^7 = 128 possible); pre-register 12 hypothesis-driven configs
- ❌ NÃO rodar em paralelo — process restart between configs needs serial; race conditions kill comparability
- ❌ NÃO substituir Phase A — Phase B answers "which feature carries the lift internally"; Phase A answers "are we ahead of the world"

---

## 14. References

- `specs/2026-05-21-per-method-benchmark-comparison.md` — Phase A sister spec (inter-system)
- `paper/publication/baselines/entity_ablation_eval.py` — driver to extend (lines 1-100 contain ablation matrix concept; lines 60-100 contain `_check_eval_isolation` guard)
- `paper/publication/baselines/run_locomo_ablations.sh` — orchestrator pattern (env-toggle + port-18803 isolation pattern)
- `eval/q4-comparison/runner.py` + `aggregate.py` — output schema + metric primitives (nDCG/Recall/MRR/percentile)
- `eval/q4-comparison/adapters/nox_mem.py` — adapter pattern to fork
- `audits/2026-05-21-G10b-per-category-mutex-ablation.md` — per-category baseline from G10b
- `audits/2026-05-21-G10c-per-style-mutex-ablation.md` — per-style baseline from G10c
- `docs/DECISIONS.md` — D43 (Q4 gate), D48 (mutex canonical), D49 (shadow telemetry phase 2)
- `docs/ROADMAP.md` §6 — Lab section (Phase B is Lab Q1 work)
- Memory `[[g10-mutex-validated-2026-05-20]]` — mutex validation baseline
- Memory `[[g4-wave-a-results-2026-05-19]]` — feature isolation deltas (entity-eval n=78)
- Memory `[[g8-source-type-boost-live-2026-05-20]]` — source_type_boost prod baseline
- Memory `[[temporal-spike-v2-win-2026-05-20]]` — PR #181 temporal_spike v2 baseline
- Memory `[[g9-redundancy-confirmed-prod-2026-05-20]]` — additive boost redundancy = mutex motivation
- Memory `[[eval-harness-must-explicit-isolate-db]]` — 4-layer DB isolation hard rule
- Memory `[[always-verify-eval-db-and-harness-before-comparing]]` — G6 lesson, SHA256+chunks+golden+harness gate
- Memory `[[qap-pillars-strategic-decision]]` — pilar Q closure dependency

