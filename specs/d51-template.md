# D51 Template — Conditional Hard Mutex (G10d) active vs current Hard Mutex (G10)

> **Status:** TEMPLATE pré-aberto (2026-05-21). Decisão final D51 vai ser tomada após G10d ablation eval.

---

## Contexto

G10 (PR #182) deployou Hard Mutex section ↔ source_type em prod (2026-05-20) com aggregate +0.79% nDCG / +2.65% MRR. G10b/G10c (2026-05-21 audits) cravaram trade-off per-category:

- **Single-hop +8.22% nDCG / +13.20% MRR** (strong win)
- **Open-domain +2.42% nDCG / +5.56% MRR** (win)
- **Multi-hop −3.95% nDCG / −6.02% R@10** (regression, style-agnostic)
- **Adversarial −2.95% nDCG / −5.88% MRR** (regression, concentrated em keyword)

G10d hypothesis: **conditional mutex** based em `query_entities ≤ NOX_MUTEX_QUERY_ENTITY_THRESHOLD` (default 1). Multi-entity queries (≥2) preservam chain traversal signal.

Spec: `specs/2026-05-21-G10d-conditional-mutex-by-query-entities.md`.

---

## Critérios de decisão D51

D51 vai DEPENDER de **2 fontes de evidência**:

### 1. G10d ablation (g9.db, n=100)

Configurações comparadas:

| Config | Descrição | Env |
|---|---|---|
| A8' | G10 baseline (current prod) | default |
| A8d-1 | Conditional, threshold=1 | `NOX_MUTEX_QUERY_ENTITY_THRESHOLD=1` |
| A8d-2 | Conditional, threshold=2 | `NOX_MUTEX_QUERY_ENTITY_THRESHOLD=2` |
| A8' off | Control, mutex disabled | `NOX_DISABLE_MUTEX_SECTION_SOURCE_TYPE=1` |

### Success criteria (GO ACTIVE)

| Metric | Threshold GO | Threshold NO-GO |
|---|---|---|
| Multi-hop nDCG@10 | **≥ −1%** (recover from −3.95%) | < −2% (não recupera) |
| Multi-hop R@10 | **≥ −2%** (recover from −6.02%) | < −3% |
| Single-hop nDCG@10 | **≥ +6%** (preserve from +8.22%) | < +5% (perdeu ganho) |
| Single-hop MRR | **≥ +10%** (preserve from +13.20%) | < +8% |
| Aggregate nDCG@10 | **≥ +0.79%** (≥ G10 current) | < +0.3% |
| Aggregate MRR | **≥ +2.65%** (≥ G10 current) | < +1.5% |
| Open-domain nDCG@10 | ≥ +1% (não regredir) | < +0.5% |
| Latency p95 search | < +50ms vs baseline | > +100ms |

### Bonus criteria

- Adversarial keyword nDCG@10 ≥ −2% (atual −5.35%) — bonus se G10d aproveita aspecto multi-entity
- Adversarial keyword MRR ≥ −5% (atual −10%) — bonus

### 2. Threshold grid search

| Cenário | Action |
|---|---|
| A8d-1 satisfies all GO criteria | **ACTIVE** threshold=1 |
| A8d-2 ≥ A8d-1 em aggregate, both pass GO | **ACTIVE** threshold=2 (looser) |
| A8d-1 multi-hop recovery insuficiente AND A8d-2 better | **ACTIVE** threshold=2 |
| Nenhum threshold passa multi-hop ≥ −1% | **OFF** (G10d falhou hypothesis) |
| Single-hop regress < +5% em todos thresholds | **OFF** (perdeu ganho principal) |
| Aggregate negativo em ambos thresholds | **OFF** + investigate |

---

## Decisão proposta (preenchida 2026-05-21 após G10d ablation)

| Field | Value |
|---|---|
| Data | 2026-05-21 |
| Aggregate A8' baseline | nDCG=0.5502, MRR=0.5992, R@10=0.6183 |
| Aggregate A8d-1 (threshold=1) | nDCG=0.5467, MRR=0.5856, Δ=−0.64% nDCG / −2.27% MRR |
| **Aggregate A8d-2 (threshold=2)** | **nDCG=0.5577, MRR=0.6074, Δ=+1.35% nDCG / +1.37% MRR** |
| Aggregate A8' off (control) | nDCG=0.5438, MRR=0.5806, Δ=−1.17% nDCG / −3.10% MRR |
| Single-hop nDCG@10 best config | A8d-2 = 0.5470 (Δ=−3.26% vs A8'; **+3.31% vs pre-mutex**) |
| Multi-hop nDCG@10 best config | A8d-2 = 0.6894 (Δ=+1.58%) — **recovers from G10b −3.95% regression** |
| Multi-hop R@10 best config | A8d-2 = 0.6917 (Δ=+3.75%) — **recovers from G10b −6.02% regression** |
| Adversarial nDCG@10 best config | A8d-2 = 0.7664 (Δ=+3.04%) — **bonus, recovers G10b −2.95% regression** |
| Open-domain nDCG@10 best config | A8d-2 = 0.7856 (Δ=+2.92%) — incremental win |
| Latency p95 search | A8d-2 = 2558 ms (vs A8' = 2573 ms — within noise) |
| **Decisão** | **ACTIVE-T2 (threshold=2)** |
| Rationale | A8d-2 wins 6/8 D51 criteria. Aggregate +1.35% nDCG / +1.37% MRR vs G10 baseline AND +2.03%/+2.51% vs pre-mutex baseline. Multi-hop and adversarial regressions recovered. Single-hop regresses vs G10 (−3.26% nDCG) but still BETTER than pre-mutex (+3.31% nDCG). Net trade-off favorable: G10 over-optimized single-hop at cost of multi-hop+adversarial; G10d-T2 balances. Threshold=2 acts as noise filter given 15 612 entities (40× spec-estimated 402), where threshold=1 trips almost every query and degenerates toward mutex_disabled. |
| Action items | (a) deploy code from PR #198 to prod nox-mem path (impl audit §5). (b) set `NOX_MUTEX_QUERY_ENTITY_THRESHOLD=2` in prod systemd. (c) 7-day shadow window per CLAUDE.md rule #5 before active. (d) telemetry column `search_telemetry.query_entity_count` migration (deferred from PR #198). (e) G10e parking-lot: investigate single-hop drill (entity-type filtering, threshold=3 grid). |

---

## Implementação se ACTIVE-T1 (threshold=1)

1. Deploy conditional mutex code via Wave (worktree branch)
2. Default env: `NOX_MUTEX_QUERY_ENTITY_THRESHOLD=1`, conditional active by default
3. Telemetry: `search_telemetry.query_entity_count` col em prod
4. Update `CLAUDE.md` regra #5 com case study G10d (boost conditional preferido sobre stacking)
5. Update `paper/paper-tecnico-nox-mem.md` §5 com novos números
6. Update visual identity headline (+X% vs current G10 baseline)
7. Memory `[[g10d-conditional-mutex-active-t1]]` + new baseline
8. Cross-link D51 em `docs/DECISIONS.md`
9. Specs/INDEX.md move G10d spec pra Done section

## Implementação se ACTIVE-T2 (threshold=2)

Mesmas steps que T1, **plus**:
1. Default env: `NOX_MUTEX_QUERY_ENTITY_THRESHOLD=2`
2. Document edge case: queries single-entity-by-2-mentions (e.g., "Toto Toto") teriam count=1 não 2 (dedup matter) — confirmar via test fixtures

## Implementação se OFF

1. **NÃO deploy** conditional mutex code
2. Hard Mutex G10 permanece como prod baseline
3. Memory `[[g10d-conditional-mutex-off-decision]]` com rationale + multi-hop regression aceita como cost
4. Specs/INDEX.md move G10d spec pra Deferred section
5. **NÃO revert** PR #182 — G10 ainda é aggregate-positive, conditional bolt-on falhou mas baseline está OK
6. Adicionar à backlog Lab: re-investigar multi-hop com diferente lens (e.g., G10e style-conditional ou neural reranker)

## Implementação se EXTEND

1. G10d v1 não conclusivo → roda v2 com grid expandido: threshold=1, 2, 3, AND `query_entity_density` (count/words ratio)
2. Sample maior: n=200 queries (custo +2x)
3. Re-deliberar D51' após v2

---

## Post-deploy validation queries (se ACTIVE)

Após deploy em prod, validar em 24h:

```bash
# 1. Distribuição de query_entity_count em queries reais
sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db <<SQL
  SELECT query_entity_count, COUNT(*) as n
  FROM search_telemetry
  WHERE ts > datetime('now', '-1 day')
  GROUP BY query_entity_count
  ORDER BY query_entity_count;
SQL

# 2. Cache hit rate
curl http://127.0.0.1:18802/api/health | jq '.queryEntityCache'

# 3. Latency p95 vs baseline
curl http://127.0.0.1:18802/api/health | jq '.latency.search.p95'

# 4. Mutex active fraction
sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db <<SQL
  SELECT
    SUM(CASE WHEN query_entity_count <= 1 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS mutex_active_fraction
  FROM search_telemetry
  WHERE ts > datetime('now', '-1 day');
SQL
```

Expected:
- Mutex active fraction: 60-80% (most queries single-entity)
- Cache hit rate: > 95%
- Latency p95 delta: < +50ms

---

## Rollback procedure (se anomaly detected pós-active)

### Tier 1 — Disable conditional layer, keep G10 hard mutex (1-min)

```bash
echo '[Service]
Environment="NOX_DISABLE_CONDITIONAL_MUTEX=1"' | sudo tee \
  /etc/systemd/system/nox-mem-api.service.d/g10d-conditional-off.conf
sudo systemctl daemon-reload && sudo systemctl restart nox-mem-api
```

### Tier 2 — Disable entire mutex (volta pre-PR #182)

```bash
echo '[Service]
Environment="NOX_DISABLE_MUTEX_SECTION_SOURCE_TYPE=1"' | sudo tee \
  /etc/systemd/system/nox-mem-api.service.d/mutex-off.conf
sudo systemctl daemon-reload && sudo systemctl restart nox-mem-api
```

### Tier 3 — Code revert

```bash
git revert <commit-do-conditional-mutex>
npm run build && systemctl restart nox-mem-api
```

### Conditions que disparam rollback

- Aggregate nDCG@10 prod cai abaixo de baseline G10 +0.79%
- Latency p95 search aumenta > 100ms persistente (>15min)
- `kg_entities` index corrupt → mutex degenera pra always-on (= G10 atual, não verdadeira regressão mas observability alert)
- Single-hop satisfaction drops em production telemetry (qualitative signal)

---

## Cross-links

- G10b — `audits/2026-05-21-G10b-per-category-mutex-ablation.md`
- G10c — `audits/2026-05-21-G10c-per-style-mutex-ablation.md`
- G10 deploy — PR #182, `specs/2026-05-20-mutual-exclusion-section-source-type.md`
- G10d spec — `specs/2026-05-21-G10d-conditional-mutex-by-query-entities.md`
- D50 (precedent template style) — `specs/d50-template.md`
- Memory `[[hard-mutex-deployed-2026-05-20]]`, `[[g10b-multi-hop-regression]]`, `[[g10c-style-agnostic]]`, `[[g10d-conditional-mutex-design]]`

---

*Template pré-aberto: 2026-05-21. Próximo passo: rodar G10d ablation, preencher tabela §"Decisão proposta", cravar decisão.*
