# Lab L3 — Confidence + provenance field (schema v19 candidate)

**ID:** Lab L3 (memanto-inspired Six Gaps #3 — "Confidence + provenance metadata on every memory")
**Status:** 📋 SPEC — implementation-ready, ranking integration GATED
**Owner:** Toto (decisão); Maestro (execução)
**Data:** 2026-05-17
**Branch:** `overnight/2026-05-17/L3-confidence-field-spec`
**Tagline:** _"Pain-weighted hybrid memory with shadow discipline — yours by design."_

> **Disambiguation:** Lab L3 = experimental memanto-inspired feature (this spec). NOT to be confused with cache-tier L3 (cold/Obsidian view, `docs/VISION.md` §Cache Hierarchy). "Lab" = Six Gaps lab series (L1 = ..., L2 = conflict detection, L3 = this).

**Cross-link:** `docs/HANDOFF.md`; `docs/DECISIONS.md` §Salience formula multiplicativa; `docs/ROADMAP.md` §Lab series.

---

## 1. Motivação

memanto markets _"Confidence + provenance metadata on every memory"_ como Six Gaps #3. Hoje nox-mem distingue chunks só por `pain` (severity), `importance` (peso afetivo), `retention_days` (tipo de memória) — todos relacionados ao **valor** da memória, nenhum à **certeza** dela.

### Problema concreto

Três tipos de fato hoje convivem indistinguíveis no mesmo schema:

| Tipo | Exemplo | Hoje rankeia como… |
|---|---|---|
| **Observed** (testemunhado, gravado) | "Toto disse na call 2026-05-12: rejeito F09" | igual ao resto |
| **Inferred** (extraído por LLM, sujeito a erro) | KG relation `gemini-flash-lite uses gemini/gemini-2.5-flash-lite` (extraído por kg-extract) | igual ao observado |
| **Derived** (consolidado, agregado, sintético) | "consolidate gerou: padrão recorrente de problemas em monkey-patch" | igual ao observado |
| **Stale** (verdadeiro 6 meses atrás, agora?) | "uso opus-3 como primary" (era verdade até 2026-04, hoje falso) | igual ao recente |
| **User-marked** (Toto explicitamente afirmou ou negou) | "esse fato está errado" / "esse fato é canônico" | sem mecanismo |

Resultado: search retorna inferred com mesmo peso que observed; chunks velhos derivados competem com truth crystallized.

### Why we can do this better than memanto

1. **Pain × confidence interaction** — pain alto modera o decay de confidence (incident em prod permanece relevante mesmo "antigo")
2. **KG provenance** — relations já têm `source_entity_id` e `extraction_metadata` (campos para `extracted_by`, `extracted_at`); confidence amarra ao mesmo pipeline
3. **Shadow discipline** — regra crítica #5 (`CLAUDE.md`): nenhuma mudança em ranking sem 7d shadow validation
4. **Ablation discipline** — R01a eval harness mede deltas reais vs golden set, não promete

### Constraint herdada: regra crítica #5

`CLAUDE.md` regra #5 — "Nunca introduzir ranking/scoring change em commit de 'fix'. Boost multiplicativo empilhável é veneno." Esta spec respeita: confidence entra como **um único multiplicador clampado** (não empilha com pain stacking), e ranking ativação é GATED em eval lift.

---

## 2. Schema delta (v18 → v19)

```sql
-- Migration v18 → v19 (specs/migrations/v19-confidence.sql)
ALTER TABLE chunks ADD COLUMN confidence REAL DEFAULT 0.8 NOT NULL
  CHECK (confidence BETWEEN 0 AND 1);
ALTER TABLE chunks ADD COLUMN provenance_kind TEXT;
ALTER TABLE chunks ADD COLUMN confidence_set_at TEXT;        -- ISO 8601, NULL = default
ALTER TABLE chunks ADD COLUMN confidence_set_by TEXT;        -- 'ingest' | 'cli' | 'consolidate' | 'kg-extract' | 'decay'
ALTER TABLE chunks ADD COLUMN last_accessed_at TEXT;         -- updated on retrieval (for decay)

-- Enum constraint via CHECK
-- provenance_kind ∈ NULL | 'observed' | 'declared' | 'inferred' | 'derived' | 'user-marked'

-- Index for decay sweep
CREATE INDEX idx_chunks_decay ON chunks(last_accessed_at, confidence_set_at)
  WHERE confidence < 1.0 AND provenance_kind IN ('inferred', 'derived');

-- meta.schema_version bumps 18 → 19
UPDATE meta SET value='19' WHERE key='schema_version';
-- PRAGMA user_version = 19 (via migrate-v19 wrapper)
```

### Wrapper: `migrateToV19(db)`

Standard `withOpAudit('migrate-v19')` wrapper:
1. VACUUM INTO snapshot pre-migration
2. ALTER TABLE chunks (4 columns)
3. CREATE INDEX
4. UPDATE meta + PRAGMA user_version
5. Backfill: `UPDATE chunks SET confidence = 0.8, provenance_kind = NULL` (idempotent — DEFAULT já cobre new chunks)
6. Optional backfill per kind (see §4) — opt-in via `--backfill-by-source`

**Reversibility:** `migrateToV19Revert(db)` — DROP INDEX, ALTER DROP COLUMN (SQLite >=3.35). Snapshot retém pre-state 7d.

---

## 3. Provenance taxonomy

| `provenance_kind` | Default `confidence` | Source / semantic |
|---|---|---|
| `observed` | **1.0** | Direct user input via CLI ingest of canonical entity file; conversation snippet captured verbatim; explicit `ingest --source=observed` |
| `declared` | **0.9** | Frontmatter `compiled` truth section em entity files; CLAUDE.md / decisions docs ingested |
| `inferred` | **0.7** | KG relations extracted by `kg-extract` (Gemini); semantic synthesis where source chunk(s) exist but LLM produced the assertion |
| `derived` | **0.5** | `consolidate` agglomeration; `crystallize` summarization; multi-chunk fusion |
| `user-marked` | variable (CLI sets) | Toto explicitly sets confidence via CLI; can be 0.0 ("known wrong, kept for audit") to 1.0 ("canonical") |
| `NULL` | 0.8 (legacy backfill) | Pre-v19 chunks; default for ambiguous ingest paths |

### Rationale (each anchor)

- **observed 1.0** — provenance é o chunk em si, not interpretation
- **declared 0.9** — autor humano com possibility of staleness, not error
- **inferred 0.7** — LLM extraction error rate em E05 kg-extract was 14% baseline → 56% post-prompt-rev (n=100). 0.7 = 1.0 × (1 - 0.30) middle estimate of remaining error
- **derived 0.5** — consolidate inherits weakest link em cadeia; 0.5 reflete 2-hop semantic distance
- **user-marked variable** — Toto's call. CLI prompts for explicit value

---

## 4. How confidence enters chunks

### 4a. Defaults per ingest kind

Tabela de routing (em `ingest-router.ts:routeIngest()`):

| Ingest path | `confidence` default | `provenance_kind` default |
|---|---|---|
| `ingestEntityFile()` section=compiled | 0.9 | declared |
| `ingestEntityFile()` section=frontmatter | 0.9 | declared |
| `ingestEntityFile()` section=timeline | 0.8 | observed |
| `ingestFile()` markdown genérico | 0.8 | NULL |
| `ingestGraphify()` | 0.7 | derived |
| `kg-extract` relations → reified as chunks (opt-in) | 0.7 | inferred |
| `consolidate` output | 0.5 | derived |
| `crystallize` output | 0.6 | derived |
| CLI `ingest --confidence X --kind Y` | explicit | explicit |

### 4b. CLI: `nox-mem confidence`

```
nox-mem confidence set <chunk_id> <value> [--kind <kind>] [--reason "..."]
nox-mem confidence get <chunk_id>
nox-mem confidence list --kind inferred --below 0.5
nox-mem confidence stats             # distribution per kind
nox-mem confidence decay --dry-run   # preview decay sweep
nox-mem confidence decay --apply     # apply monthly decay
```

`set` writes `confidence_set_at = now()`, `confidence_set_by = 'cli'`. Audit row em `ops_audit` (op=`confidence-set`, status=`success`).

### 4c. Decay rule

**Single rule, conservative, never auto-applied:**

```
IF (last_accessed_at < NOW - 180d)
AND (provenance_kind IN ('inferred', 'derived'))
AND (confidence > 0.3)
THEN confidence *= 0.95 (once per calendar month)
```

Rationale:
- 180d window — gives consolidation/crystallize artifacts a long warm period
- Only `inferred`/`derived` — `observed`/`declared` never decay (you wrote them; staleness is not error)
- 0.3 floor — preserves audit trail; chunks below 0.3 still searchable, just deeply de-prioritized
- 0.95 monthly = ~46% retention after 1 year of total non-access

**Decay is opt-in via cron:**
- `nox-mem confidence decay --apply` runs in `withOpAudit` wrapper
- Suggested cron: `0 4 1 * *` (1st of month 04:00 BRT)
- NOT enabled in v1 deploy — operator decision per environment

### 4d. Pain × confidence interaction (FIRST-CLASS)

Pain alto suppresses decay:

```
effective_decay = 0.95 ^ (1 - pain)
# pain=1.0 (prod outage)    → 0.95^0 = 1.00 (zero decay, NEVER forget)
# pain=0.5 (medium)         → 0.95^0.5 ≈ 0.975 (half decay)
# pain=0.2 (default trivial)→ 0.95^0.8 ≈ 0.960 (near full decay)
```

This is the **memanto-beat** — single most important design choice in this spec. memanto has confidence but no pain; we couple them so prod-critical knowledge resists decay.

---

## 5. How confidence enters ranking (GATED)

### Candidate formula

```
salience = recency × pain × importance × confidence
clamp [0.3, 1.5]   # SAME clamp envelope as current G01 salience
```

- Multiplicative single-factor (no stacking)
- Clamp prevents pathological zeros from killing search results entirely
- Default confidence=0.8 means most chunks unchanged vs pre-v19 (0.8 × everything ≈ 0.8 floor shift baked into clamp)

### Activation modes (mirror G01 / NOX_SALIENCE_MODE pattern)

```
NOX_CONFIDENCE_MODE=off       # default; ignored in ranking
NOX_CONFIDENCE_MODE=shadow    # logged via /api/health, NOT applied
NOX_CONFIDENCE_MODE=active    # multiplied into salience
```

**Default ships as `off`**. `shadow` after schema lands. `active` ONLY after gate met (§6).

### Annotation-only fallback

If gate fails: `confidence` and `provenance_kind` STILL surfaced in `/api/search` response JSON (consumer can filter client-side), STILL exposed in `/api/health` distributions, but NEVER multiplied into salience.

---

## 6. Eval methodology (THE GATE)

### Methodology

**A/B ablation matrix** via R01a harness:

| Variant | Formula | Hypothesis |
|---|---|---|
| **A: baseline** | `recency × pain × importance` | current G01 |
| **B: confidence alone** | `recency × pain × importance × confidence` | does conf alone help? |
| **C: confidence + section** | `... × confidence × section_boost` | does it stack with existing section? |
| **D: full + decay** | `... × confidence(decayed) × section_boost` | does decay add value? |

### Gate threshold

```
MIN_LIFT = +1.0pp nDCG@10  (vs baseline A)
SIGNIFICANCE = paired bootstrap, p < 0.05, n ≥ 200 queries
SHADOW_DURATION = 7d MIN (regra crítica #5)
```

### Decision matrix

| Result B,C,D vs A | Action |
|---|---|
| All variants ≥+1.0pp, p<0.05 | **GO** — pick highest variant, activate via `NOX_CONFIDENCE_MODE=active` + 7d more monitoring |
| Only D ≥+1.0pp | GO with full decay enabled |
| Only B ≥+1.0pp | GO without decay (skip §4c apply) |
| Best variant <+1.0pp BUT ≥0 | **ANNOTATION ONLY** — ship schema, ship CLI, ship API exposure; DO NOT activate ranking; document in `docs/DECISIONS.md` as refuted ranking signal |
| Any variant <0 | **CUT ranking** — pure annotation; consider revert decay cron |
| Insignificant (p>0.05) | ANNOTATION ONLY + extend shadow to 14d, re-eval |

### Eval artifacts

`eval/2026-05-XX-L3-confidence-ablation/`:
- `golden-set.jsonl` — same 200+ queries as R01a, with `expected_chunk_ids`
- `runs/{A,B,C,D}-results.jsonl`
- `analysis.ipynb` (or `analysis.md`)
- `verdict.md` — Maestro signs off, Toto approves

---

## 7. CLI / API / MCP exposure

### CLI

- `nox-mem search <query> --with-confidence` — JSON includes per-result `confidence` + `provenance_kind`
- `nox-mem search <query> --min-confidence 0.7` — filter (server-side query)
- `nox-mem confidence ...` — sub-commands per §4b

### HTTP API

**`/api/search` response (always includes, regardless of mode):**

```json
{
  "results": [
    {
      "chunk_id": 12345,
      "text": "...",
      "score": 0.84,
      "salience": 0.91,
      "confidence": 0.7,
      "provenance_kind": "inferred",
      "confidence_set_at": "2026-04-25T12:00:00Z",
      "confidence_set_by": "kg-extract"
    }
  ]
}
```

**`/api/health.confidence` (new section):**

```json
{
  "confidence": {
    "mode": "shadow",
    "distribution_by_kind": {
      "observed": {"count": 1234, "mean": 0.98, "p50": 1.0, "p10": 0.85},
      "declared": {"count": 5678, "mean": 0.89, "p50": 0.9, "p10": 0.7},
      "inferred": {"count": 4321, "mean": 0.68, "p50": 0.7, "p10": 0.4},
      "derived": {"count": 2345, "mean": 0.48, "p50": 0.5, "p10": 0.3},
      "user-marked": {"count": 12, "mean": 0.6}
    },
    "decay_stats": {
      "eligible_for_decay": 1500,
      "last_decay_run_at": null,
      "decayed_chunks_total": 0
    },
    "override_rate": {
      "user_marked_per_week": 2.5
    }
  }
}
```

### MCP

`nox_mem_search` already returns full chunk metadata; add `confidence` + `provenance_kind` to default fields. New tool:

- `nox_mem_confidence_set(chunk_id, value, reason)` — writes via op-audit

---

## 8. Telemetry

Metrics emitted to `search_telemetry` and `/api/health`:

| Metric | Cadence | Purpose |
|---|---|---|
| Distribution per kind (count + p10/p50/p90) | Real-time `/api/health` | Spot drift (e.g., 80% inferred = kg-extract overrun) |
| `confidence` per query top-k (mean) | Per query → aggregated daily | Detect ranking dominance shifts |
| Decay sweep delta (chunks affected, mean shift) | Per `decay --apply` run | Audit non-trivial decay events |
| User override rate (cli set / week) | Daily | Track operator engagement; if zero forever, kill the feature |
| Decay/access correlation | Weekly | Validate 180d threshold is correct |

Discord alerts (P2-level):
- `distribution.inferred.mean < 0.5` for 24h → suspicion that kg-extract is producing low-quality output
- `decay --apply` would affect >10% of corpus in one run → require manual `--force` flag

---

## 9. Tests plan

### Unit tests (`__tests__/confidence.test.ts`)

1. **Defaults per ingest kind** — each path (entity-compiled, markdown, graphify, kg-extract, consolidate, crystallize) inserts with correct default
2. **CHECK constraint** — INSERT confidence=1.5 fails; -0.1 fails; "abc" fails
3. **CLI set/get** — `nox-mem confidence set 1 0.3` → DB row matches + ops_audit row created
4. **Decay computation** — pain=1.0 case yields exactly 1.0 multiplier (no decay)
5. **Decay sweep dry-run vs apply** — dry-run produces same chunk list as apply, NO DB mutation
6. **180d threshold boundary** — chunk last_accessed_at = exactly 180d ago not decayed; 180d + 1s decayed
7. **Provenance enum validation** — invalid string rejected at CLI layer

### Integration tests

8. **Ablation suite scaffold** — runner reads `golden-set.jsonl`, executes variants A/B/C/D, dumps `runs/*.jsonl`, fails fast if any chunk_id mismatch in corpus
9. **Ranking neutrality** — with `UPDATE chunks SET confidence = 1.0` corpus-wide, variant B output == variant A output (byte-identical scores); proves clamp + multiplier are no-op at unity
10. **Migration roundtrip** — v18 → v19 → v18 revert preserves all rows, no data loss

### Property tests

11. **Decay monotonic** — repeated decay calls never INCREASE confidence
12. **Clamp idempotent** — clamping pre-vs-post multiply yields same result for confidence ∈ [0, 1]

### Shadow simulation test

13. **Mode=off vs mode=shadow byte-equal** — search results in `off` mode identical to `shadow` mode (only telemetry differs)

---

## 10. Definition of Done (GATED)

### DoD-A — schema + ingest + CLI + API exposure (ALWAYS SHIPS)

- [ ] Migration v18 → v19 wrapper + revert wrapper
- [ ] 4 columns + 1 index landed; `meta.schema_version=19` + `PRAGMA user_version=19`
- [ ] `routeIngest()` writes correct defaults per kind (table §4a)
- [ ] CLI `confidence {set,get,list,stats,decay}` all working
- [ ] `/api/search` response includes `confidence` + `provenance_kind` (regardless of mode)
- [ ] `/api/health.confidence` section live with distributions
- [ ] MCP `nox_mem_search` returns confidence; `nox_mem_confidence_set` tool exposed
- [ ] Tests 1-7 + 10-13 passing
- [ ] Mode defaults to `off`; ranking unchanged
- [ ] Doc: `docs/DECISIONS.md` entry — "v19 schema landed, ranking gated by L3 ablation"
- [ ] Audit log: snapshot pre-migration present

### DoD-B — ranking integration (GATED on §6 eval)

- [ ] R01a ablation run (variants A/B/C/D) complete on n≥200 queries
- [ ] Statistical significance (paired bootstrap, p<0.05)
- [ ] Best variant lift ≥+1.0pp nDCG@10
- [ ] 7d shadow mode metrics collected (matches offline eval predictions ±20%)
- [ ] Forge/Maestro sign-off on eval verdict
- [ ] Toto explicit GO/NO-GO decision documented
- [ ] If GO: `NOX_CONFIDENCE_MODE=active` flipped in env; 7d post-activation monitoring
- [ ] If NO-GO: variant decision recorded in `docs/DECISIONS.md` as ANNOTATION-ONLY

### DoD-B fallback (NO-GO path)

- [ ] Schema + CLI + API STAY shipped (DoD-A unchanged)
- [ ] Decay cron NOT installed (or removed if pre-installed)
- [ ] `docs/DECISIONS.md` updated with refuted lift verdict + ablation reference
- [ ] Telemetry continues collecting (low cost; preserves option to revisit)

---

## 11. NÃO-fazemos (v1)

1. **No LLM-based confidence scoring** — Gemini não é convocado a estimar confidence. Confidence vem do **path of origin** (deterministic per ingest), não de meta-inference. memanto pode estar fazendo LLM scoring; nossa diferenciação é determinismo + auditability.

2. **No KG-propagation of confidence** — relation confidence ≠ entity confidence ≠ chunk confidence. Cross-propagation é segunda ordem complexity; defer pra L4+ se ROI provar.

3. **No time-weighted model beyond monthly multiply** — decay é 1 regra (180d + 0.95 monthly); no half-life curves, no per-tenant tuning, no Bayesian update. Keep simple, audit later.

4. **No per-tenant baselines** — confidence is global, not per-agent. (Maestro vs Forge não têm calibração diferente). Multi-tenant é fora de scope.

5. **No automatic confidence boost on re-access** — `last_accessed_at` updates but does NOT raise confidence. Reading something doesn't make it true.

6. **No retroactive backfill** — pre-v19 chunks default to 0.8/NULL forever, unless user manually sets. Migration não inventa.

---

## 12. Riscos

### R1 — "Magic knob" risk (D38/D36 lesson)

**Anti-pattern:** adding tuning parameters that nobody ever revisits, contaminating signal.

**Mitigation:**
- Single multiplier (no per-feature confidence weighting)
- Gate ABSOLUTE on eval lift — não passa, vira annotation
- Telemetry `override_rate=0` for 60d → alert + reconsider
- Decay cron OPT-IN (defaults off)

### R2 — Decay suppressing important-but-old (e.g., Toto's foundational decisions)

**Mitigation:**
- Pain × confidence coupling: pain=1.0 → zero decay (§4d)
- Only `inferred`/`derived` decay; `observed`/`declared` immune
- Floor 0.3 — never falls below searchable threshold
- 180d window is long; reconsider if false-negative reports come in

### R3 — Eval insignificant

**Mitigation:**
- Pre-committed path (DoD-B fallback) — ship as annotation, no ranking change
- Decision recorded as refuted, not hidden
- Telemetry retained → option to revisit in 6 months with bigger corpus

### R4 — Schema migration corruption (v18 → v19)

**Mitigation:**
- Standard `withOpAudit` wrapper (pre-op snapshot 7d retention)
- `migrateToV19Revert()` tested in CI
- Idempotent migration (re-running is no-op)
- DR drill quarterly already covers this class

### R5 — Inferred bucket fills with garbage (kg-extract regression)

**Mitigation:**
- `distribution.inferred.mean < 0.5` Discord alert (§8)
- E05b kg-extract has its own quality gate
- User can `confidence list --kind inferred --below 0.3` to audit any time

### R6 — User confusion: "what does 0.7 mean?"

**Mitigation:**
- CLI `confidence stats` prints anchor table (observed=1.0, declared=0.9, ...) on every invocation
- Docs `docs/CONVENTIONS.md` adds confidence taxonomy section
- API response includes `provenance_kind` (semantic label) alongside numeric

---

## 13. Shadow rollout plan

### Week 1 — Schema + ingest + CLI (no ranking touch)

- Day 1: PR review + merge `migrateToV19` + ingest defaults + CLI subcommands
- Day 2: Deploy schema migration (via cron pre-op snapshot)
- Day 3-7: Validate distribution by kind, override rate, no regressions in `/api/health`
- Gate: 0 schema-related alerts × 5 consecutive days

### Week 2 — Offline ablation

- Day 8: Run R01a harness variants A/B/C/D on n=200 queries
- Day 9-10: Statistical analysis, p-values, lift confidence intervals
- Day 11: Maestro drafts verdict; Forge code review
- Day 12-14: Toto reviews, asks adversarial questions, signs

### Week 3 — Decide go/no-go

- Day 15: GO or NO-GO documented in `docs/DECISIONS.md`
- If GO:
  - Day 16: `NOX_CONFIDENCE_MODE=shadow` flipped (live metrics, no behavior change)
  - Day 16-22: 7d shadow validation (live metrics match offline within ±20%)
  - Day 23: `NOX_CONFIDENCE_MODE=active` flipped; 7d post-activation monitoring window opens
- If NO-GO:
  - Annotation-only mode permanent
  - Decay cron NOT installed
  - Telemetry continues for future revisit

### Rollback path

Any post-activation regression (e.g., `/api/health.search.p95 > 1.5s`, eval lift inversion, user complaint):
1. `NOX_CONFIDENCE_MODE=off` (instant, no DB change)
2. Investigate via telemetry + ops_audit
3. Schema STAYS — annotation continues to work
4. Re-eval before re-flipping

---

## Appendix A — Comparison vs memanto Six Gaps #3

| Aspect | memanto | nox-mem L3 |
|---|---|---|
| Confidence field | yes | yes |
| Provenance kind | implicit | explicit enum (5 values) |
| Decay model | (likely time-weighted) | 1 rule, 180d, monthly 0.95, gated by pain |
| Ranking integration | (likely default-on) | GATED on eval lift ≥+1.0pp |
| Shadow discipline | unclear | mandatory 7d |
| Pain coupling | no (no pain field) | yes — pain=1.0 zero decay |
| LLM-based scoring | (likely) | no — deterministic per ingest path |
| Ablation eval | unclear | R01a harness mandatory |
| Annotation-only fallback | unclear | first-class — ships even if ranking fails |
| Auditability | unclear | confidence_set_at + ops_audit |

---

## Appendix B — Open questions (for Pre-Generation Metis consultation)

These are deferred decisions that DO NOT block DoD-A but should be answered before DoD-B activation:

1. **Default kind for legacy backfill** — keep NULL (no commitment) or backfill all to `observed` (assume good faith)? Spec ships NULL; revisit if `/api/search` consumers complain.

2. **CLI `confidence set` should require `--reason` text?** — auditability vs friction. Current spec: optional `--reason`. Revisit if ops_audit shows zero reasons logged.

3. **Cap on `user-marked` count?** — could a malicious script flood overrides? Current spec: no cap. Audit log captures; alert on >100 sets/day.

4. **Display in dashboard?** — `agent-hub-dashboard` would need a "Confidence Distribution" panel for §8 telemetry. Defer to dashboard team post-DoD-A.

5. **Interaction with `crystallize`** — crystallize already produces "compiled" sections (declared=0.9). Should crystallize bump confidence on validated chunks? Current spec: no (separation of concerns). Revisit.

6. **Reified KG relations as chunks?** — §4a row "kg-extract relations reified as chunks (opt-in)" is currently theoretical; depends on KG-as-corpus decision (not made). Spec accepts confidence default if it ever lands; doesn't require it now.

---

## Appendix C — File touch list (estimate for DoD-A)

| File | Change | Est LOC |
|---|---|---|
| `src/migrations/v19-confidence.ts` | new | 80 |
| `src/lib/op-audit.ts` | safeRestore + schema validate | +10 |
| `src/lib/ingest-router.ts` | per-kind defaults | +40 |
| `src/lib/confidence.ts` | new — CLI logic, decay, validation | 200 |
| `src/cli/confidence.ts` | new — subcommands | 150 |
| `src/api/search.ts` | response shape | +20 |
| `src/api/health.ts` | new section | +60 |
| `src/mcp/tools/confidence_set.ts` | new | 60 |
| `__tests__/confidence.test.ts` | new | 400 |
| `__tests__/migration-v19.test.ts` | new | 150 |
| `docs/CONVENTIONS.md` | taxonomy section | +50 |
| `docs/DECISIONS.md` | v19 entry | +20 |
| **Total DoD-A estimate** | | **~1240 LOC** |

DoD-B (ranking integration): +50 LOC (multiplier in salience formula) + eval harness extension (~200 LOC scaffolding).

---

**End of spec. Awaiting Maestro/Toto review.**
