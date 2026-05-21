# D50 Template — Temporal proximity rerank active vs off

> **Status:** TEMPLATE pré-aberto (2026-05-20), enriched 2026-05-21. **Decisão final D50 ETA ~2026-05-27** (7d shadow baseline desde phase 2 ativação 2026-05-20).
>
> **Atual:** NOX_TEMPORAL_PATH=shadow ATIVO em prod via systemd. Cron scrape `/root/.openclaw/workspace/scripts/scrape-temporal-shadow.sh` rodando diariamente meia-noite UTC. journalctl mostra temporal_path events sendo emitidos (signalSource: adverbial/month_year, confidence tiers).

---

## Contexto

D49 (PR #162, 2026-05-20) cravou política shadow-mode opt-in pro temporal proximity rerank deployado em PR #157 (spike) + PR #167 (phase 1 deploy).

Phase 2 (em curso, agent #53): ativar `NOX_TEMPORAL_PATH=shadow` via systemd drop-in + scrape diário por 7 dias. Phase 3: D50 decisão.

Smoke test inicial (PR #161, n=4 queries) mostrou Δ +0.0% por ceiling/drift. Smoke pós-cura Q105-Q110 (em curso, agent #53) vai dar primeiro sinal de magnitude.

---

## Critérios de decisão D50

D50 vai DEPENDER de 3 fontes de evidência:

### 1. Smoke Q105-Q110 (agent #53 em curso)

Resultado smoke vs rerank manual em Q105-Q110 (rank baseline 5-13):

| Metric | Threshold pra GO | Threshold pra NO-GO |
|---|---|---|
| Δ nDCG@10 médio | **≥ +3%** | < +1% |
| Δ MRR médio | **≥ +2%** | < +0.5% |
| Queries com rank melhoria | **≥ 4/6** | ≤ 2/6 |
| Queries com rank regressão | 0 | ≥ 1 |

### 2. Phase 2 baseline 7 dias

`NOX_TEMPORAL_PATH=shadow` ativo em prod por 7 dias. Métricas via scrape diário:

| Metric | Target |
|---|---|
| Queries temporal detected (intent.detected=true) | 5-20% do total queries |
| Hit rate de signalSource | iso_date > 50%, adverbial > 30% |
| Cobertura de anchorIso válido | > 70% das temporal queries |
| Failure rate detector | < 1% (intent.error / total) |

Se métrica saturada (e.g. < 1% queries detected como temporal), **NO-GO** — feature não tem mass.

### 3. Counterfactual eval em g5.db (prod-flavored)

Rodar full ablation pós-shadow (A8 active vs A8 active + temporal rerank ativo) contra g5.db 68k chunks (não entity-eval.db). Sample 100 temporal queries via golden file.

| Cenário | Action |
|---|---|
| Δ nDCG temporal subset ≥ +5% AND Δ overall ≥ 0% | **ACTIVE** (deploy via Wave) |
| Δ temporal +2-5% AND overall ≥ 0% | **OPT-IN** (env keep, default off) |
| Δ overall < 0% (regression) | **OFF** (rollback drop-in) |
| Inconclusivo | **EXTEND shadow** mais 7 dias |

---

## Decisão proposta (preencher após dados)

| Field | Value |
|---|---|
| Data ETA | **2026-05-27** (D+7 desde shadow ativação 2026-05-20) |
| Smoke Q105-Q110 Δ | Δ +10.37% (spike v2 PR #181, pre-deploy) — pós-deploy aguarda shadow data |
| Shadow 7d detect rate | TBD (preliminary day 1 evidence: adverbial/month_year events emitting) |
| Shadow 7d hit rate iso_date | TBD |
| Counterfactual g5.db Δ | TBD |
| **Decisão** | **ACTIVE / OPT-IN / OFF / EXTEND** |
| Rationale | TBD |
| Action items | TBD |

### Pre-flight data collected 2026-05-21

- Service uptime desde shadow ativação: 20+ horas
- Telemetria journalctl: temporal_path events visible
- signalSource distribution preliminary (n<100 events): `adverbial` dominant, `month_year` second, `iso_date` rare
- Confidence tiers funcionando: `keyword_inferred=0.6` (anchor null), `month_year=0.8` (date in query)
- kReranked=0 quando confidence baixo (esperado por design — confidence limita boost)

### D50 pre-fire checklist (run 2026-05-27)

```bash
# 1. Confirm 7d window
ssh root@187.77.234.79 'journalctl -u nox-mem-api --since "2026-05-20 00:00 UTC" --no-pager | grep -c "temporal_path"'

# 2. Run scrape aggregation
ssh root@187.77.234.79 'bash /root/.openclaw/workspace/scripts/scrape-temporal-shadow.sh aggregate 7d'

# 3. Counterfactual eval g5.db (after scrape data confirms detection rate > 5%)
# Spawn agent isolation: worktree, runs A8 active vs A8 active+temporal-rerank em g5.db full

# 4. Decide GO/NO-GO via thresholds in §1.2.3 above

# 5. If GO → deploy via Wave (remove `NOX_TEMPORAL_PATH==='shadow'` condition)
# If NO-GO → systemd drop-in remove + keep code
```

---

## Implementação se ACTIVE

1. Update CLAUDE.md §5 (shadow-mode rule) com case study D49 → D50
2. Remove condition `NOX_TEMPORAL_PATH==='shadow'` em `search.ts` — apply rerank by default
3. Adicionar flag `NOX_DISABLE_TEMPORAL_PATH=1` pra emergency off
4. Atualizar paper §5 com novo Δ
5. Atualizar visual identity (headline +XX% vs G3 baseline)
6. New baseline cravado em HANDOFF + memory

## Implementação se OPT-IN

1. Mantem PR #167 status atual (env opt-in via `NOX_TEMPORAL_PATH=shadow`)
2. Document caso de uso onde ativar (queries temporal-heavy contexts)
3. Não atualizar paper headline

## Implementação se OFF

1. Remove drop-in systemd `/etc/systemd/system/nox-mem-api.service.d/d49-temporal-shadow.conf`
2. Keep code em src/ pra futuro re-experiment
3. Memory `[[d50-temporal-off-decision]]` com rationale

## Implementação se EXTEND

1. Continue shadow ativo
2. Mais 7d baseline com targeted queries (instrumented golden temporal subset)
3. Re-deliberar D50' em 7d

---

## Cross-links

- D49 — `docs/DECISIONS.md` (2026-05-20)
- Spike — PR #157 `staged-temporal-spike/`
- Phase 1 deploy — PR #167 `staged-1.7a/edits/temporal-retrieval.ts`
- Gold cure — PR #168 Q105-Q110
- Smoke test inicial — PR #161 `docs/RESEARCH/2026-05-20-temporal-smoke-test.md`
- Memory `[[temporal-q1-spike-2026-05-20]]`, `[[g7-salience-isolation-2026-05-20]]`
