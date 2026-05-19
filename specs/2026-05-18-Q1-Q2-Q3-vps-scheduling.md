# Q1+Q2+Q3 VPS Scheduling — Operational Spec

> **Data:** 2026-05-18
> **Status:** SPEC (pendente execução supervisionada)
> **Gate:** Q4 COMPARISON abre quando Q1+Q2+Q3 produzem números verificados
> **Referência cruzada:** `benchmark/COMPARISON.md` (§5 Gate Decision Logic), `docs/DECISIONS.md`

---

## 1. Goals

O portão GTM Phase 2 (ver `docs/ROADMAP.md` + `docs/VISION.md` v14) permanece fechado até que:

1. **Q1 (LoCoMo):** nox-mem produz R@5, R@1, MRR, nDCG@10 verificados no harness `eval/locomo/` (n≥100, seed=42, corpus 5.882 turns, isolado em `eval.db`).
2. **Q2 (LongMemEval):** nox-mem produz task-accuracy (split `longmemeval_s_cleaned`, n=100, seed=42) julgada por LLM-as-judge (`gpt-4o` para comparabilidade + `gemini-2.5-pro` como secundário), isolado em `eval.db`.
3. **Q3 (Latência):** nox-mem produz p50/p95/p99 para os workloads `search.short`, `search.medium`, `search.long`, `search.kg-heavy`, `ingest.entity-file` no harness `eval/latency/` rodando no VPS real (corpus ~62k chunks, warm cache, n=100 por workload de busca).

Esses três conjuntos de números preenchem os campos `pending` na tabela de `benchmark/COMPARISON.md §1` e desbloqueiam o script `benchmark/generate-comparison.ts` com `GATE_VERIFIED=1`.

**O que NÃO acontece neste PR:** nenhuma execução de benchmark. Esta spec autoriza e descreve as corridas; a execução exige aprovação explícita de Toto + VPS idle + keys de API confirmadas.

---

## 2. Q1 — LoCoMo Run

### Harness
`eval/locomo/` — scaffoldado em PR #6 (`overnight/2026-05-17/Q1-locomo-harness`).

### Metodologia resumida

- **Dataset:** `snap-research/locomo` `data/locomo10.json` (~9 MB). CC BY-NC 4.0 (uso de pesquisa OK; não distribuir dentro do nox-supermem comercial).
- **Ingestion:** por turno (`speaker: text`), `chunk_id = sample_id::dia_id`, tudo em `eval/locomo/eval.db` isolado — **nunca toca `nox-mem.db`**.
- **Embedding:** Gemini `gemini-embedding-001` (3072d). ~5.882 turnos = custo ~$0.05 USD.
- **Busca:** hybrid search via CLI (`nox-mem search "<q>" --json --limit 20 --db eval/locomo/eval.db`) — não contamina logs de produção nem salience.
- **Avaliação:** chunk-ID set match binário contra `evidence` gold. Sem LLM-as-judge. Métricas: R@5 (principal para comparação com agentmemory 95.2%), R@1, MRR, nDCG@10 (comparável ao E04 FTS5-only baseline nDCG=0.281).
- **Sample:** n=100 estratificado (20/categoria × 5 categorias), seed=42. Binomial CI via `score.ts --ci`.
- **Opção full corpus:** n=1.986 (todos os QA pairs) disponível via `--full-corpus`. Decidir com Toto antes do run se vale o custo adicional de CPU (tempo de busca ~10× maior; embedding já pago no corpus completo).

### Duração estimada

| Fase | Duração estimada |
|---|---|
| Download dataset | ~2 min (9 MB) |
| Parse + ingest 5.882 turnos | ~5 min |
| Embedding (5.882 × Gemini API) | ~30–45 min (rate-limit safe com retry) |
| Busca n=100 (CLI subprocess, ~2s/query) | ~3–5 min |
| Score + CI | ~1 min |
| **Total Q1** | **~40–55 min** |

> Estimativa conservadora: **~1–1.5h end-to-end** com margens para retries e rate limits Gemini.

### Custo estimado (Q1)

| Item | Estimativa |
|---|---|
| Embedding 5.882 turnos × 3072d (`gemini-embedding-001`) | ~$0.05 |
| Sem judge LLM (binário) | $0.00 |
| **Total Q1** | **~$0.05** |

### Checkpoint

O harness salva resultados parciais em `eval/locomo/results/partial-<timestamp>.json` a cada 10 queries. Em caso de interrupção SSH, retomar de: `npx tsx eval/locomo/run.ts --resume --checkpoint results/partial-<timestamp>.json`.

---

## 3. Q2 — LongMemEval Run

### Harness
`eval/longmemeval/` — scaffoldado em PR #11 (`overnight/2026-05-17/Q2-longmemeval-harness`).

### Metodologia resumida

- **Dataset:** `xiaowu0162/longmemeval-cleaned` (MIT). Splits necessários: `longmemeval_oracle` (dry-run já feito) + `longmemeval_s_cleaned` (~115k tokens/conversa, ~40 sessões/questão, 500 questões total).
- **Ingestion:** por sessão (NOT por turno — diferença deliberada vs Q1). Header `[session_id=X date=YYYY-MM-DD]` no início de cada chunk para dar contexto temporal ao FTS5 e ao LLM.
- **DB isolation:** `eval/longmemeval/eval.db` criado fresh por run. Flushado entre runs para evitar contaminação de data-aware questions.
- **Pipeline por questão:** ingest haystack → hybrid search (limit=20) → generator LLM → hypotheses armazenadas → judge LLM.
- **Generator LLM:** `gemini-2.5-flash` (não flash-lite para este run — queremos sinal limpo do retrieval, não ruído de geração barato). Configurável via `LONGMEMEVAL_GENERATOR=`.
- **Judge:** dois juízes em paralelo:
  1. `gpt-4o` (paper-standard, comparabilidade com leaderboard) — requer `OPENAI_API_KEY`.
  2. `gemini-2.5-pro` (secundário, custo-efetivo, já keyed no VPS).
  Publicar ambos os números + Cohen's-κ inter-judge agreement.
- **Sample:** n=100 estratificado (split `s_cleaned`), seed=42. 6 strata (colapsando `_abs` variants no parent). Full corpus (n=500) via `--full-corpus` — deferred, custo ~5× maior.
- **Métricas:** task-accuracy overall + por categoria + por `_abs` variant + Wilson 95% CI.

### Duração estimada

| Fase | Duração estimada |
|---|---|
| Download splits (oracle + s_cleaned) | ~5–10 min (HuggingFace, tamanho variável) |
| Parse + ingest haystacks n=100 (40 sessões/q × 100) | ~15–25 min |
| Embedding 4.000 sessões estimadas × 3072d | ~60–90 min (maior custo Q2) |
| Generator LLM n=100 (flash, ~5s/q) | ~8–12 min |
| Judge gpt-4o n=100 (paralelo, ~3s/q) | ~5–10 min |
| Judge gemini-2.5-pro n=100 (paralelo, ~4s/q) | ~6–12 min |
| Score + CI + inter-judge κ | ~2 min |
| **Total Q2** | **~1h45min – 2h30min** |

> Estimativa conservadora: **~3h end-to-end** com margens para rate limits e retries.

### Custo estimado (Q2)

| Item | Estimativa |
|---|---|
| Embedding ~4.000 sessões × 3072d (`gemini-embedding-001`) | ~$0.35 |
| Generator `gemini-2.5-flash` n=100 (~500 tokens/call avg) | ~$0.05 |
| Judge `gpt-4o` n=100 (~800 tokens/call) | ~$0.40 (input) + ~$0.08 (output) = ~$0.48 |
| Judge `gemini-2.5-pro` n=100 (~800 tokens/call) | ~$0.20 |
| **Total Q2** | **~$1.08** |

> Se `OPENAI_API_KEY` não estiver disponível no VPS: rodar somente `gemini-2.5-pro` como judge primário e documentar que o número `gpt-4o` fica pendente. Não bloqueia o gate — desde que metodologia seja explícita.

### Checkpoint

O harness salva `hypotheses/<run-partial>.jsonl` incrementalmente (um append por questão). Em caso de interrupção: `npx tsx eval/longmemeval/run.ts --resume --hypotheses hypotheses/<run-partial>.jsonl`.

---

## 4. Q3 — Latency Baseline Run

### Harness
`eval/latency/` — scaffoldado em PR #12 (`eval/latency/src/`).

### Diferença vs bench P1 (já publicado)

O bench P1 em `staged-P1/` usou **mock LLM (100ms stub)** e **SQLite in-memory**. Esses números validam overhead do pipeline mas NÃO são latência de produção. O Q3 run usa:
- **VPS real** (Hostinger, 4 vCPU, 8GB RAM)
- **`nox-mem.db` real** (~62k chunks, prod DB — snapshot para `eval/latency/eval.db`)
- **Sem mock:** subprocess calls ao `dist/index.js` compilado (CLI real)
- **Cache warm:** 10 warmup iterations descartadas antes de medir
- **`process.hrtime.bigint()`** (ns resolution, não `Date.now()`)

### Workloads a rodar

| Workload | n | Warmup | O que mede |
|---|---|---|---|
| `search.short` | 100 | 10 | Queries 1–3 palavras, surface FTS5 mínima |
| `search.medium` | 100 | 10 | Queries 4–9 palavras (tráfego típico) |
| `search.long` | 100 | 10 | Queries 10+ palavras, BM25+semantic full pipeline |
| `search.kg-heavy` | 50 | 10 | Named entities → KG traversal tax |
| `ingest.entity-file` | 50 | 5 | ~5KB entity Markdown file (warm DB, fresh slug por iteração) |

Workload `ingest.chunk-batch` (n=20) é opcional — rodar se tempo permitir; não bloqueia gate.

**Sem cold-cache run no baseline inicial:** `--cold` é deferred para v2. Documentar explicitamente que os números publicados são warm-cache steady-state.

### Duração estimada

| Fase | Duração estimada |
|---|---|
| Preparar eval.db (snapshot prod) | ~2 min |
| Build harness (`npm run build`) | ~1 min |
| search.short n=100 + 10 warmup | ~4 min (~2.2s/iter subprocess) |
| search.medium n=100 + 10 warmup | ~4 min |
| search.long n=100 + 10 warmup | ~5 min |
| search.kg-heavy n=50 + 10 warmup | ~3 min |
| ingest.entity-file n=50 + 5 warmup | ~3 min |
| Aggregate + summary JSON | ~1 min |
| **Total Q3** | **~23–25 min** |

> Estimativa conservadora: **~45 min end-to-end** com overhead de setup + verificação de resultados.

### Custo estimado (Q3)

Q3 não faz chamadas à Gemini API durante o run (embedding já está no eval.db; busca é FTS5 + sqlite-vec local). Custo = **$0.00 em API**. Custo de CPU VPS é negligenciável (< 0.5h de compute).

---

## 5. Resource Requirements

### VPS baseline (Hostinger)

| Recurso | Disponível | Q1 pico | Q2 pico | Q3 pico |
|---|---|---|---|---|
| CPU | 4 vCPU | 1–2 vCPU (CLI serial) | 2–3 vCPU (generator + judge paralelo) | 1–2 vCPU (subprocess serial) |
| RAM | 8 GB | ~500 MB (Node + sqlite-vec) | ~800 MB (Node + sqlite-vec + LLM client) | ~400 MB (Node + sqlite-vec) |
| Disco — eval DBs | ~40 GB disponível | ~200 MB (eval.db 5.882 turnos + vetores) | ~1.5 GB (eval.db 4k sessões × 3072d) | ~2 GB (snapshot prod ~62k chunks) |
| Disco — logs | — | ~5 MB | ~30 MB | ~10 MB |

### API Quota

| Provider | Limite | Q1 | Q2 | Q3 | Total estimado |
|---|---|---|---|---|---|
| Gemini embedding (`gemini-embedding-001`) | ~10M tokens/dia free tier | ~18M tokens (5.882 turnos × ~100 tokens avg) | ~12M tokens (4k sessões × ~100 tokens avg) | $0 (sem embeddings novos) | ~30M tokens total (2 dias se free tier, ou $2.50 se pago) |
| Gemini generator (`gemini-2.5-flash`) | 3M tokens/dia free tier | N/A | ~50k tokens (100 calls × ~500 tokens) | N/A | ~50k tokens |
| Gemini judge (`gemini-2.5-pro`) | quota paga | N/A | ~80k tokens (100 × 800) | N/A | ~80k tokens |
| OpenAI GPT-4o judge | pago por token | N/A | ~80k tokens | N/A | ~80k tokens |

> **Atenção:** `gemini-embedding-001` com 5.882 + 4.000 = ~9.882 chunks × ~100 tokens = ~988k tokens total de embedding — bem dentro de qualquer plano. Estimativas acima foram conservadoras. Verificar antes com `/api/health.vectorCoverage` para evitar re-embedding.

### Pré-condições antes de iniciar qualquer run

1. `curl -sf http://127.0.0.1:18802/api/health | jq '{status, total, embedded}'` → status=ok, embedded≈total.
2. `df -h /root/` → pelo menos 5 GB livres (Q2 DB é o maior).
3. `set -a; source /root/.openclaw/.env; set +a && echo $GEMINI_API_KEY` → key presente e não vazia.
4. `curl -s "https://generativelanguage.googleapis.com/v1beta/models?key=$GEMINI_API_KEY" | jq '.error.code // "OK"'` → "OK" (quota viva).
5. Para Q2 com judge GPT-4o: `echo $OPENAI_API_KEY` → presente. Verificar saldo na conta OpenAI.
6. Nenhum batch job pesado rodando: `systemctl status nox-mem-api` OK, `top` mostra CPU idle.

---

## 6. Scheduling Strategy

### Ordem de execução: Q3 → Q1 → Q2

| Ordem | Benchmark | Custo API | Duração | Motivo |
|---|---|---|---|---|
| 1 | Q3 Latência | $0 | ~45 min | Mais barato, valida ambiente, sem risk de quota |
| 2 | Q1 LoCoMo | ~$0.05 | ~1–1.5h | Só embedding, sem LLM-as-judge, barato e estável |
| 3 | Q2 LongMemEval | ~$1.08 | ~3h | Mais caro, requer GPT-4o, roda por último |

Razões para essa ordem:
- Q3 valida que o VPS está idle e o harness de latência não há regressão antes de pagar por embeddings.
- Q1 valida que o pipeline de busca funciona corretamente antes de pagar pelo pipeline de geração + judge do Q2.
- Se Q1 mostrar R@5 abaixo de expectativa, pode-se investigar antes de gastar o Q2 budget.

### tmux + nohup para resiliência a disconnect SSH

Cada run deve estar dentro de uma sessão tmux para sobreviver a desconexões SSH. A cadeia de comandos para cada benchmark é encapsulada em um script de shell com redirecionamento de log para arquivo.

```bash
# No VPS, antes de começar:
tmux new -s benchmark

# Dentro do tmux — Q3:
bash scripts/run-q3-latency.sh 2>&1 | tee /var/log/nox-mem/bench/q3-$(date +%Y%m%d-%H%M%S).log

# Detach sem matar: Ctrl+B → D
# Re-attach depois: tmux attach -t benchmark
```

Caso o tmux seja perdido (reboot VPS), os scripts já fazem `exec > logfile 2>&1` no início para garantir que o log persiste mesmo sem terminal.

### Logs em `/var/log/nox-mem/bench/`

```bash
# Criar dir se não existir (uma vez):
mkdir -p /var/log/nox-mem/bench
chmod 700 /var/log/nox-mem/bench
```

Arquivos de log:
- `q3-<timestamp>.log` — saída completa do run Q3
- `q1-<timestamp>.log` — saída completa do run Q1
- `q2-<timestamp>.log` — saída completa do run Q2
- `q2-partial-hypotheses-<timestamp>.jsonl` — hypotheses incrementais Q2 (backup caso crash)

### Opção alternativa: systemd-run --user

Para runs que devem sobreviver logout e não precisam de interatividade:

```bash
systemd-run --user --unit=nox-bench-q1 \
  --setenv=GEMINI_API_KEY="$GEMINI_API_KEY" \
  bash /root/.openclaw/workspace/tools/nox-mem/scripts/run-q1-locomo.sh
```

Monitorar progresso: `journalctl --user -u nox-bench-q1 -f`

> Preferir tmux para runs interativos onde você quer ver o progresso em tempo real. `systemd-run` é melhor quando você vai largar e voltar horas depois.

---

## 7. Cost Cap Protection

**Regra:** `NOX_PROVIDER_DAILY_USD_CAP=20` em todos os runs. Nenhum benchmark deve rodar sem essa variável definida.

O módulo `CostCappedProvider` (A3, PR #39) aborta chamadas quando o cap diário é atingido e retorna `error: "daily_cost_cap_exceeded"`. Em contexto de benchmark, isso resulta em partial results com as questões restantes marcadas como `status: "aborted_cost_cap"` no JSON de saída.

```bash
# Exportar ANTES de qualquer run:
export NOX_PROVIDER_DAILY_USD_CAP=20

# Verificar que está definida:
echo "Cap: $NOX_PROVIDER_DAILY_USD_CAP USD/dia"
```

Para Q2 com GPT-4o (custo maior), o cap de $20/dia é adequado: custo estimado Q2 total ~$1.08, muito abaixo do cap. Se por alguma razão o cap disparar, é sinal de que algo saiu fora do esperado (ex: loop infinito de retry, corpus muito maior que estimado).

### Failsafe adicional: checar custo mid-run

Q2 é o único run com custo significativo. Monitorar via:

```bash
# Em outro terminal tmux:
watch -n 30 'sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
  "SELECT SUM(cost_usd), COUNT(*) FROM provider_telemetry WHERE created_at >= date(\"now\")"'
```

Se custo acumular mais rápido que esperado (~$0.01/min para Q2), interromper e investigar.

---

## 8. Failure Handling

### Interrupção por SSH disconnect

- **tmux:** processo continua rodando. Re-attach com `tmux attach -t benchmark`.
- Logs continuam sendo gravados em `/var/log/nox-mem/bench/`.

### Interrupção por crash de processo

Q1 e Q2 têm checkpoints incrementais:

**Q1 checkpoint:**
```bash
# run.ts salva partial a cada 10 queries:
eval/locomo/results/partial-<timestamp>.json

# Retomar do checkpoint:
npx tsx eval/locomo/run.ts \
  --resume \
  --checkpoint eval/locomo/results/partial-<ts>.json \
  --n 100 --seed 42 --cli
```

**Q2 checkpoint:**
```bash
# run.ts faz append incremental em hypotheses/:
eval/longmemeval/hypotheses/run-<timestamp>-partial.jsonl

# Retomar (pula questions já no arquivo):
LONGMEMEVAL_JUDGE=gpt-4o \
LONGMEMEVAL_GENERATOR=gemini-2.5-flash \
  npx tsx eval/longmemeval/run.ts \
    --split s_cleaned --n 100 --seed 42 \
    --resume --hypotheses hypotheses/run-<timestamp>-partial.jsonl
```

**Q3 checkpoint:** Q3 não tem estado entre workloads. Se interrompido, reiniciar o workload específico (`--workload search.short`, etc.). Cada workload leva ~3–5 min, então restart é barato.

### Rate limit Gemini / OpenAI

O harness deve implementar backoff exponencial (jitter incluído) em qualquer `429`. Se não implementado, wraper manual:

```bash
# retry wrapper simples:
function retry_cmd() {
  local n=0
  until [ $n -ge 5 ]; do
    "$@" && return 0
    n=$((n+1))
    sleep $((2**n + RANDOM%3))
  done
  return 1
}
```

Em caso de quota Gemini esgotada (HTTP 429 persistente após retry): parar o run, esperar renovação de quota (meia-noite UTC) e retomar via checkpoint.

### Q2 sem `OPENAI_API_KEY` disponível

Se `OPENAI_API_KEY` não está no VPS, rodar Q2 somente com judge `gemini-2.5-pro`:

```bash
LONGMEMEVAL_JUDGE=gemini-2.5-pro \
LONGMEMEVAL_GENERATOR=gemini-2.5-flash \
  npx tsx eval/longmemeval/run.ts \
    --split s_cleaned --n 100 --seed 42 --cli \
    > eval/longmemeval/full-run.gemini25pro.json
```

Documentar no resultado JSON que `gpt-4o` judge está pendente. Publicar com nota explícita em `COMPARISON.md §9` (Methodology Notes). O gate Q4 aceita essa variante — desde que a metodologia seja declarada e o número gemini-2.5-pro seja defensável.

### DB de eval corrompido

Se `PRAGMA integrity_check` em `eval.db` retornar algo diferente de `ok`, deletar e recriar:

```bash
rm eval/locomo/eval.db   # ou eval/longmemeval/eval.db
npx tsx eval/locomo/parser.ts --ingest   # reingerir corpus
```

Embedding será re-solicitado à Gemini (custo repetido ~$0.05 para Q1). Custo aceitável; usar `withOpAudit()` wrapper não é necessário aqui pois eval.db é descartável por design.

---

## 9. Result Collection

### Após Q3 (local ou no VPS)

```bash
# No VPS — verificar que resultados existem:
ls eval/latency/results/
# Esperado: search-short.json, search-medium.json, search-long.json,
#           search-kg-heavy.json, ingest-entity-file.json, summary.json

# Copiar para repo local (de volta ao Mac):
scp -r root@<vps-ip>:/root/.openclaw/workspace/tools/nox-mem/eval/latency/results/ \
  eval/latency/results/
```

### Após Q1

```bash
# No VPS:
ls eval/locomo/results/
# Esperado: full-run.json (ou partial-N.json se incompleto)

scp root@<vps-ip>:/root/.openclaw/workspace/tools/nox-mem/eval/locomo/results/full-run.json \
  eval/locomo/results/
```

### Após Q2

```bash
# No VPS (dois arquivos de judge):
ls eval/longmemeval/
# Esperado: full-run.gpt4o.json, full-run.gemini25pro.json

scp root@<vps-ip>:/root/.openclaw/workspace/tools/nox-mem/eval/longmemeval/full-run.*.json \
  eval/longmemeval/
```

### Commit dos resultados

```bash
# Após scp bem-sucedido — do repo local:
git add eval/locomo/results/full-run.json
git add eval/longmemeval/full-run.gpt4o.json
git add eval/longmemeval/full-run.gemini25pro.json
git add eval/latency/results/
git commit -m "data(Q1+Q2+Q3): benchmark results VPS run $(date +%Y-%m-%d)"
```

> **Não commitar:** `eval.db`, dataset caches (`data/*.json`), `hypotheses/*.jsonl`, `dataset.lock.json` — todos listados no `.gitignore`.

### Validação de integridade pós-scp

```bash
# Verificar que o JSON é válido e tem os campos esperados (Q1):
jq '{n_questions: (.results | length), r5: .metrics.r5, ndcg10: .metrics.ndcg10, seed: .seed}' \
  eval/locomo/results/full-run.json

# Q2:
jq '{n: (.results | length), accuracy: .metrics.overall_accuracy, judge: .judge_model}' \
  eval/longmemeval/full-run.gpt4o.json

# Q3 (summary):
jq '.workloads | keys' eval/latency/results/summary.json
```

Se qualquer campo crítico estiver `null` ou ausente, o JSON está incompleto (run abortado — ver checkpoint de retomada).

---

## 10. Q4 Gate Update

Após Q1+Q2+Q3 com resultados válidos localmente, rodar o gate update:

### Verificar readiness

```bash
# Os três arquivos devem existir e ser JSON válidos:
jq '.metrics.r5' eval/locomo/results/full-run.json           # Q1 — não null
jq '.metrics.overall_accuracy' eval/longmemeval/full-run.gpt4o.json   # Q2 — não null
jq '.workloads["search.medium"].p95_ms' eval/latency/results/summary.json  # Q3 — não null
```

### Rodar generate-comparison.ts

```bash
GATE_VERIFIED=1 \
LOCOMO_RESULTS_DIR=eval/locomo/results \
LONGMEMEVAL_RESULTS_DIR=eval/longmemeval \
LATENCY_RESULTS_DIR=eval/latency/results \
  npx tsx benchmark/generate-comparison.ts
```

O script (`benchmark/generate-comparison.ts`) lê os três resultados, preenche as células `pending` em `COMPARISON.md §1`, e grava o arquivo atualizado. Ele recusa executar se `GATE_VERIFIED` não estiver definido ou se qualquer result file estiver ausente.

### Commit do COMPARISON.md atualizado

```bash
git add benchmark/COMPARISON.md
git commit -m "data(Q4-gate): open GTM Phase 2 gate — Q1+Q2+Q3 verified $(date +%Y-%m-%d)"
```

> Este commit **fecha o gate** e autoriza o GTM Phase 2 (ver `docs/ROADMAP.md`). Não commitar sem revisar os números manualmente antes — conferir que os valores nos JSONs fazem sentido (R@5 > 0, accuracy > 0, latência < 5s).

### Se Q4 comparação gerada mostrar nox-mem abaixo de expectativa

Não inventar números, não ajustar metodologia post-hoc. Publicar o que foi medido com disclosure honesta (ver `COMPARISON.md §8 — Onde podemos não vencer`). O gate abre assim mesmo — a condição é "números verificados", não "números maiores que X".

---

## 11. Operational Runbook

### Pré-condições

```bash
# Verificar que VPS está idle
ssh root@<vps-ip>
top -bn1 | head -5   # CPU idle > 70% mínimo

# Verificar saúde do serviço
curl -sf http://127.0.0.1:18802/api/health | jq '{status, total, embedded, schemaVersion}'
# status=ok, embedded=total, schemaVersion>=20

# Verificar disco
df -h /root/ | tail -1   # >= 5 GB livre

# Verificar env
set -a; source /root/.openclaw/.env; set +a
echo "GEMINI_API_KEY: ${GEMINI_API_KEY:0:10}..."    # primeiros 10 chars
echo "OPENAI_API_KEY: ${OPENAI_API_KEY:0:10}..."    # necessário para Q2 judge gpt-4o

# Verificar quota Gemini
curl -s "https://generativelanguage.googleapis.com/v1beta/models?key=$GEMINI_API_KEY" \
  | jq '.error.code // "OK"'

# Criar dir de logs
mkdir -p /var/log/nox-mem/bench && chmod 700 /var/log/nox-mem/bench

# Definir cap de custo
export NOX_PROVIDER_DAILY_USD_CAP=20
```

### Step 1: Abrir sessão tmux

```bash
tmux new -s benchmark
# Ou attach se já existe:
# tmux attach -t benchmark
```

### Step 2: Q3 — Latency run (~45 min)

```bash
# Dentro do tmux (window 0):
set -a; source /root/.openclaw/.env; set +a
export NOX_PROVIDER_DAILY_USD_CAP=20

NM=/root/.openclaw/workspace/tools/nox-mem
LOG=/var/log/nox-mem/bench/q3-$(date +%Y%m%d-%H%M%S).log

cd $NM

# Snapshot prod DB para eval (NÃO modificar nox-mem.db):
cp $NM/nox-mem.db eval/latency/eval.db
echo "eval.db criado: $(du -sh eval/latency/eval.db)"

# Build harness
cd eval/latency && npm install && npm run build

# Rodar todos os workloads
node dist/runner.js --all --output results/full-run.json 2>&1 | tee $LOG

# Agregar
node dist/aggregator.js --input results/full-run.json --output results/summary.json

# Verificar output
jq '.workloads | to_entries | map({workload: .key, p95_ms: .value.p95_ms})' results/summary.json
echo "Q3 DONE — resultados em $NM/eval/latency/results/"
```

### Step 3: Verificar Q3 + esperar VPS esfriar (~5 min)

```bash
# Em outro painel tmux (Ctrl+B → c para novo, Ctrl+B → 0/1 para navegar):
tail -50 /var/log/nox-mem/bench/q3-*.log
jq '.workloads["search.medium"]' eval/latency/results/summary.json
# p95_ms deve estar em range razoável (< 2000ms warm cache em VPS)
sleep 300   # 5 min para VPS esfriar antes de Q1
```

### Step 4: Q1 — LoCoMo run (~1–1.5h)

```bash
# De volta ao window 0:
cd /root/.openclaw/workspace/tools/nox-mem
set -a; source /root/.openclaw/.env; set +a
export NOX_PROVIDER_DAILY_USD_CAP=20

LOG=/var/log/nox-mem/bench/q1-$(date +%Y%m%d-%H%M%S).log
mkdir -p eval/locomo/results

# Download dataset (se ainda não baixado):
npx tsx eval/locomo/download.ts 2>&1 | tee -a $LOG

# Ingest corpus
npx tsx eval/locomo/parser.ts --ingest 2>&1 | tee -a $LOG

# Full run n=100
npx tsx eval/locomo/run.ts \
  --n 100 --seed 42 --cli --full \
  > eval/locomo/results/full-run.json 2>> $LOG

# Score
npx tsx eval/locomo/score.ts eval/locomo/results/full-run.json --ci 2>&1 | tee -a $LOG

# Verificar
jq '{r5: .metrics.r5, r1: .metrics.r1, mrr: .metrics.mrr, ndcg10: .metrics.ndcg10}' \
  eval/locomo/results/full-run.json
echo "Q1 DONE"
```

### Step 5: Verificar Q1 + pausa (~10 min)

```bash
# Verificar quota restante
curl -s "https://generativelanguage.googleapis.com/v1beta/models?key=$GEMINI_API_KEY" \
  | jq '.error.code // "OK"'

# Checar custo acumulado do dia
sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
  "SELECT ROUND(SUM(cost_usd),4) as total_usd, COUNT(*) as calls
   FROM provider_telemetry
   WHERE created_at >= date('now');"

sleep 600   # 10 min antes de Q2
```

### Step 6: Q2 — LongMemEval run (~3h)

```bash
# Window dedicado para Q2 (mais longo, monitorar separado):
cd /root/.openclaw/workspace/tools/nox-mem
set -a; source /root/.openclaw/.env; set +a
export NOX_PROVIDER_DAILY_USD_CAP=20
export LONGMEMEVAL_JUDGE=gpt-4o
export LONGMEMEVAL_GENERATOR=gemini-2.5-flash

LOG=/var/log/nox-mem/bench/q2-$(date +%Y%m%d-%H%M%S).log
mkdir -p eval/longmemeval/hypotheses

# Download splits
npx tsx eval/longmemeval/download.ts --split oracle 2>&1 | tee -a $LOG
npx tsx eval/longmemeval/download.ts --split s_cleaned 2>&1 | tee -a $LOG

# Ingest s_cleaned para eval.db
npx tsx eval/longmemeval/parser.ts --split s_cleaned --ingest 2>&1 | tee -a $LOG

# Run com gpt-4o judge:
npx tsx eval/longmemeval/run.ts \
  --split s_cleaned --n 100 --seed 42 --cli --full \
  > eval/longmemeval/full-run.gpt4o.json 2>> $LOG

npx tsx eval/longmemeval/score.ts eval/longmemeval/full-run.gpt4o.json --ci \
  2>&1 | tee -a $LOG

# Run com gemini-2.5-pro judge (reutiliza mesmo eval.db):
LONGMEMEVAL_JUDGE=gemini-2.5-pro \
  npx tsx eval/longmemeval/run.ts \
    --split s_cleaned --n 100 --seed 42 --cli --full \
    > eval/longmemeval/full-run.gemini25pro.json 2>> $LOG

npx tsx eval/longmemeval/score.ts eval/longmemeval/full-run.gemini25pro.json --ci \
  2>&1 | tee -a $LOG

# Verificar
jq '{accuracy_gpt4o: .metrics.overall_accuracy, judge: .judge_model}' \
  eval/longmemeval/full-run.gpt4o.json
jq '{accuracy_gemini: .metrics.overall_accuracy, judge: .judge_model}' \
  eval/longmemeval/full-run.gemini25pro.json
echo "Q2 DONE"
```

### Step 7: Coletar resultados para o Mac

```bash
# No Mac (fora do VPS):
VPS=root@<vps-ip>
NM=/root/.openclaw/workspace/tools/nox-mem
REPO=/Users/lab/Claude/Projetos/memoria-nox

# Q3
scp -r $VPS:$NM/eval/latency/results/ $REPO/eval/latency/

# Q1
scp $VPS:$NM/eval/locomo/results/full-run.json $REPO/eval/locomo/results/

# Q2
scp $VPS:$NM/eval/longmemeval/full-run.gpt4o.json $REPO/eval/longmemeval/
scp $VPS:$NM/eval/longmemeval/full-run.gemini25pro.json $REPO/eval/longmemeval/

# Verificar integridade
jq '.metrics.r5' $REPO/eval/locomo/results/full-run.json
jq '.metrics.overall_accuracy' $REPO/eval/longmemeval/full-run.gpt4o.json
jq '.workloads["search.medium"].p95_ms' $REPO/eval/latency/results/summary.json
```

### Step 8: Gate update

```bash
cd $REPO
GATE_VERIFIED=1 \
  LOCOMO_RESULTS_DIR=eval/locomo/results \
  LONGMEMEVAL_RESULTS_DIR=eval/longmemeval \
  LATENCY_RESULTS_DIR=eval/latency/results \
  npx tsx benchmark/generate-comparison.ts

# Revisar COMPARISON.md manualmente antes de commitar
# Verificar que nenhuma célula ficou null
grep "pending" benchmark/COMPARISON.md   # deve retornar zero linhas

git add benchmark/COMPARISON.md \
  eval/locomo/results/full-run.json \
  eval/longmemeval/full-run.gpt4o.json \
  eval/longmemeval/full-run.gemini25pro.json \
  eval/latency/results/

git commit -m "data(Q4-gate): Q1+Q2+Q3 VPS results + COMPARISON.md gate opened $(date +%Y-%m-%d)"
git push origin main
```

---

## 12. O que Fica Desbloqueado

### GTM Phase 2

Conforme `docs/ROADMAP.md` e `docs/VISION.md` v14 (tagline "Pain-weighted hybrid memory with shadow discipline — yours by design."):

> GTM Phase 2 é **condicional** em "Q4 COMPARISON winning" — que requer os números Q1+Q2+Q3 verificados.

Com o gate aberto:
- README público pode usar os números reais (não "pending").
- Paper técnico `paper/paper-tecnico-nox-mem.md` pode incluir §5.3 (LoCoMo) e §5.4 (LongMemEval) com dados verificados.
- Comparação honesta com agentmemory (LoCoMo claim 95.2%) e Memanto (LME claim 89.8%) fica disponível.
- nox-supermem GTM assets podem usar os números.

### O que NÃO desbloqueia

- Comparação com mem0, Letta, Zep permanece pendente de bloqueadores B2 (Postgres+Qdrant no VPS) e B3 (OpenAI key budget para esses adapters). Esses competidores ficam como "methodology open for replication" no COMPARISON.md publicado.
- M-split LongMemEval (~500 sessões/questão) permanece deferred — mais caro e não necessário para o gate inicial.
- CI gate automático para regressão de LoCoMo/LME — fica deferred conforme decisão dos harnesses (runs custam dinheiro, não são adequados para CI frequente).

---

## 13. Decision Tree — Quando Rodar

```
Q: O VPS está idle (CPU > 70% idle, disk > 5 GB, nox-mem-api healthy)?
├── NÃO → Aguardar. Verificar cargas: systemctl status, top, df
└── SIM → continuar

Q: GEMINI_API_KEY está válida e com quota?
├── NÃO → Aguardar renovação de quota (meia-noite UTC) ou provisionar nova chave
└── SIM → continuar

Q: Qual benchmark iniciar?
├── Nenhum rodou ainda → começar com Q3 (gratuito, valida ambiente)
├── Q3 OK, Q1 pendente → rodar Q1 (~$0.05, ~1.5h)
├── Q1 OK, Q2 pendente → verificar OPENAI_API_KEY → rodar Q2 (~$1.08, ~3h)
└── Todos OK → rodar gate update → commitar

Q: Q1 mostra R@5 muito abaixo do esperado (< 0.5)?
├── Investigar primeiro: dry-run com n=5 para ver exemplos de retrieval falho
├── Se bug de ingest/search → corrigir, fechar PR, rodar Q1 de novo
└── Se número honesto → publicar assim mesmo com disclosure

Q: Q2 run foi interrompido?
├── hypotheses/run-<ts>-partial.jsonl existe? → retomar com --resume
├── eval.db parece corrompido? → PRAGMA integrity_check → delete + re-ingest
└── Quota esgotada? → aguardar reset, retomar via checkpoint

Q: Gate update script aborta?
├── "Missing result files" → verificar que os 3 arquivos JSON existem e são válidos
├── "GATE_VERIFIED not set" → exportar variável antes de rodar
└── "null metrics" → run estava incompleto; usar checkpoint para completar
```

### Quando SKIPAR a corrida

- Q3 pode ser skipado se números de latência não forem necessários para a decisão de GTM (ex: argumento de autonomia é suficiente). Mas Q3 é o mais barato — recomendado rodar sempre.
- Q2 pode ser parcialmente skipado (só gemini judge, sem gpt-4o) se OPENAI_API_KEY não disponível. Documentar limitação.
- Q1 NÃO pode ser skipado — é o benchmark que diferencia nox-mem de agentmemory na métrica que eles publicaram (R@5 95.2%).

### Quando RETRY

- Rate limit transitório (429) → aguardar 60s + retry (harness tem backoff automático; se não, wrapper manual).
- Disk full → limpar `/var/backups/nox-mem/` dos snapshots mais antigos (apenas os pre-op com > 7d), não tocar nox-mem.db.
- Node.js OOM → reduzir `--n` para n=50 em Q1, aumentar depois em segundo run com checkpoint.
- VPS CPU throttle (Hostinger pode throttle em picos de burst) → aguardar 5 min, verificar com `top`, retomar.

---

## Apêndice A — Variáveis de Ambiente Necessárias

| Variável | Obrigatório para | Fonte |
|---|---|---|
| `GEMINI_API_KEY` | Q1 (embedding), Q2 (embedding + generator + juiz gemini) | `/root/.openclaw/.env` |
| `OPENAI_API_KEY` | Q2 (juiz gpt-4o) — opcional se usar só gemini judge | `/root/.openclaw/.env` |
| `NOX_PROVIDER_DAILY_USD_CAP` | Todos os runs | Definir na sessão: `export NOX_PROVIDER_DAILY_USD_CAP=20` |
| `OPENCLAW_WORKSPACE` | Harnesses usam DB isolado | Definido internamente pelo harness (eval.db path) |
| `NOX_API_PORT` | Opcional (default 18802) | `/root/.openclaw/.env` |
| `LONGMEMEVAL_JUDGE` | Q2 | `gpt-4o` (paper-grade) ou `gemini-2.5-pro` (alternativa) |
| `LONGMEMEVAL_GENERATOR` | Q2 | `gemini-2.5-flash` (headline run) |

---

## Apêndice B — Resumo de Custos e Tempos

| Benchmark | Custo API | Duração estimada | Cap de segurança |
|---|---|---|---|
| Q3 Latência | $0.00 | ~45 min | N/A |
| Q1 LoCoMo | ~$0.05 | ~1.5h | $1 |
| Q2 LongMemEval | ~$1.08 | ~3h | $5 |
| **Total Q1+Q2+Q3** | **~$1.13** | **~5–6h (serial)** | **$20/dia** |

3 runs mínimos para publicação (ver `COMPARISON.md §9 — 3 runs minimum`): total de 3 ciclos completos = ~$3.40 + ~18h de execução serial. Recomendado espaçar ao longo de 3 dias para evitar picos de quota e facilitar revisão de cada run.

---

*Spec criada: 2026-05-18 — Wave M.*
*Referência: `benchmark/COMPARISON.md` (gate §5), `docs/DECISIONS.md`, `eval/locomo/README.md`, `eval/longmemeval/README.md`, `eval/latency/README.md`, `docs/ops/MONITORING.md`.*
*Execução: apenas com aprovação explícita + VPS idle + keys confirmadas.*
