# Perf Regression Gate — Guia para contribuidores

> Último update: 2026-05-18 (Wave L)

## O que é

O nox-mem mantém um baseline de métricas de performance em `benchmark/baseline-2026-05-18.json`. Toda PR que toca os diretórios `staged-P1`, `staged-A2`, `staged-A3` ou `staged-L4` aciona automaticamente o detector de regressão, que:

1. Executa os benchmarks relevantes (somente os que têm `reproduce` command válido)
2. Compara os resultados contra o baseline
3. Posta um comentário na PR com a tabela de drift por métrica
4. **Falha a PR** se qualquer métrica regredir além do threshold (padrão: ±10%)
5. **Passa a PR** se o drift for positivo (melhoria) — mas emite um aviso para considerar atualizar o baseline

Regressão = performance piorou (ex: latência aumentou). Melhoria = performance melhorou (ex: latência caiu).

---

## Como funciona o gate

### Threshold

O threshold padrão é **±10%** por métrica. Você pode:

- Alterar para um PR específico via `workflow_dispatch` com input `threshold`
- Alterar permanentemente no repositório via a variável de repositório `NOX_DRIFT_THRESHOLD_PCT`

O threshold de **10% foi escolhido deliberadamente largo** para evitar falsos positivos causados por variance de hardware no runner GitHub-hosted. Se você ver falhas ruidosas em semanas consecutivas em métricas sub-ms (P1.answer.phase.retrieval), considere abrir um issue para ajustar o threshold desse métrica específico.

### Direção do drift

Para métricas de latência (`_ms`): drift positivo = mais lento = regressão.
Para métricas de qualidade (`nDCG`, `accuracy`): drift negativo = pior = regressão.

O `regression-detector.ts` usa a convenção `((measured - baseline) / baseline) × 100`:
- `+5%` em latência = 5% mais lento
- `-3%` em nDCG = 3% de queda de qualidade

### Métricas mensuráveis vs. baseline-only

Nem todas as métricas do baseline são executadas em CI. As mensuráveis requerem `staged-P1`, `staged-A2` ou `staged-A3` presentes:

| Prefixo | Fonte | Status em CI |
|---------|-------|-------------|
| `P1.*` | `staged-P1/benchmark/answer-latency.ts` | Executado se `staged-P1/` presente |
| `A2.*` | `staged-A2/benchmark/export-import-bench.ts` | Executado se `staged-A2/` presente |
| `A3.*` | `staged-A3/benchmark/provider-overhead.ts` | Executado se `staged-A3/` presente |
| `L4.*` | Estimativas de design-time | `BASELINE_ONLY` — não executado |
| `SEARCH.*`, `MONITORING.*`, `PROMETHEUS.*` | Métricas estáticas | `BASELINE_ONLY` — não executado |

---

## Como atualizar o baseline

### Quando atualizar

- Você fez uma melhoria intencional de performance (ex: otimizou o pipeline de retrieval)
- Uma mudança arquitetural mudou os números de forma legítima (ex: novo provider com overhead diferente)
- O baseline está desatualizado após muitos meses sem ajuste

### Como atualizar

```bash
# 1. Garanta que os staged dirs estão buildados:
cd staged-P1 && npm install && npm run build && cd ..
cd staged-A2 && npm install && npm run build && cd ..
cd staged-A3 && npm install && npm run build && cd ..

# 2. Execute o detector localmente e capture os números:
npx tsx benchmark/regression-detector.ts > /tmp/current-report.json 2>&1

# 3. Revise os resultados:
node -e "
  const r = JSON.parse(require('fs').readFileSync('/tmp/current-report.json', 'utf8'));
  r.results.filter(x => x.measured !== null).forEach(x =>
    console.log(x.metric_key, x.baseline, '->', x.measured, '(drift:', x.drift_pct?.toFixed(2)+'%)')
  );
"

# 4. Edite benchmark/baseline-2026-05-18.json:
#    Atualize APENAS as métricas que mudaram intencionalmente.
#    Não misture updates de baseline com mudanças de feature no mesmo commit.

# 5. Commit com prefixo claro:
git add benchmark/baseline-2026-05-18.json
git commit -m "tune(bench): update P1 latency baseline after retrieval optimization"
```

### O que NÃO fazer

- Não atualize o baseline para silenciar uma regressão real — investigue a causa
- Não misture `tune(bench)` com `fix(...)` ou `feat(...)` no mesmo commit
- Não edite os valores `pending_metrics` do baseline sem uma justificativa no commit message

---

## Como suprimir falsos positivos

### Opção 1: Ampliar o threshold temporariamente

Via `workflow_dispatch` na aba Actions, acione `Perf Regression Gate` com `threshold=25`. Isso não afeta PRs — é manual only.

### Opção 2: Marcação no PR

Se você sabe que um benchmark vai flutuar (ex: hardware do runner tem alta variance para aquele metric), adicione ao corpo da PR:

```
<!-- nox-perf-suppress: A3.provider_overhead.embed.p95_abs_ms reason="sub-microsecond timer noise on ubuntu-latest" -->
```

O gate atual não lê essa marcação ainda (é um stub para futura implementação). Por enquanto, documente a supressão no PR description e mencione no review.

### Opção 3: Métricas com baseline zero

Métricas cujo baseline é `0` (ex: `L4.extraction.regex.latency_p50_ms`) são tratadas como "drift infinito" se o valor medido for qualquer coisa diferente de 0. Elas estão listadas como `BASELINE_ONLY` e nunca executadas em CI — mas se você mover alguma para o conjunto runnable, ajuste o baseline com um valor não-zero primeiro.

---

## Como ler o dashboard

O nightly cron salva cada run em `benchmark/history/YYYY-MM-DD.json` no branch `benchmark-history`. O script `benchmark/scripts/accumulate-history.ts` agrega esses arquivos em:

- `benchmark/history/TIMESERIES.md` — tabela markdown com rolling 30 dias
- `benchmark/history/timeseries.json` — dados para charts do Grafana

### Grafana

O spec do dashboard está em `benchmark/DASHBOARD-SPEC.md`. Os painéis cobrem:

- Pipeline total p50/p95/p99 (trend line)
- Drift diário por métrica (heat map)
- Step changes automáticos (anotações no gráfico)
- Pass/Fail count por dia

### Alertas

O nightly falha o workflow se qualquer métrica regredir além de **25%** (threshold mais largo que o PR gate de 10% porque runners noturnos podem ter mais variance). Se o nightly falhar repetidamente, investigue:

1. Verifique o artefato `perf-nightly-YYYY-MM-DD-<run_id>.json` em Actions → Artifacts
2. Compare com o dia anterior via `benchmark/history/`
3. Correlacione com merges recentes no branch `main`

---

## Executar localmente

```bash
# Run completo (executa benchmarks + compara):
npx tsx benchmark/regression-detector.ts

# Dry-run (compara baseline vs baseline — sempre PASS, útil para testar o script):
npx tsx benchmark/regression-detector.ts --dry-run

# Com threshold customizado:
npx tsx benchmark/regression-detector.ts --threshold=5

# JSON-only para parsing:
npx tsx benchmark/regression-detector.ts --json-only | jq '.overall_status'

# Acumular histórico local (gera TIMESERIES.md + timeseries.json):
npx tsx benchmark/scripts/accumulate-history.ts
npx tsx benchmark/scripts/accumulate-history.ts --window=60 --step-change-threshold=15
```

---

## Referências

- Baseline: `benchmark/baseline-2026-05-18.json`
- Detector: `benchmark/regression-detector.ts`
- PR gate workflow: `.github/workflows/perf-regression.yml`
- Nightly workflow: `.github/workflows/perf-nightly.yml`
- History accumulator: `benchmark/scripts/accumulate-history.ts`
- Dashboard spec: `benchmark/DASHBOARD-SPEC.md`
