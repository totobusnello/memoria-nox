# LoCoMo Production-Path Validation — Q1 Runbook

> **Branch:** `research/2026-05-18/q1-production-path`
> **Author:** scientist-high agent
> **Status:** PLAN — not yet executed
> **Companion:** `eval/locomo/run.ts` (existing harness, scaffold)
> **Helper:** `paper/publication/baselines/locomo_to_markdown.py` (this PR)

---

## 1. Problem statement

O número Q1 hoje (n=100 LoCoMo subset) é uma Python re-implementação do
pipeline hybrid: FTS5 + Gemini dense + RRF k=60, rodando em SQLite isolado
(`/tmp/locomo-hybrid-eval.db`). Ela mostra **+18,8% nDCG@10** vs FTS5-only
baseline (E04). Resultado promissor — **mas é Python, não nox-mem prod**.

Pra o paper §5.3 e pra o GTM gate Phase 2 (`docs/VISION.md` v14), precisamos
do mesmo +18,8% rodando contra o **TS pipeline real** (`src/search/hybrid.ts`)
via `/api/search` real. Senão, qualquer reviewer pergunta legítima:
*"a Python re-impl mede a arquitetura ou mede esse script?"* — e a resposta
honesta é "esse script".

Este doc descreve **Option A** (instância secundária `nox-mem-api` em :18803
apontando pra DB isolado de eval) como o caminho de menor risco / maior
fidelidade pra fechar essa lacuna. Decisão analisada contra 3 alternativas.

---

## 2. Decision matrix — por que Option A

| Opção | Resumo | Trade-offs principais | Veredito |
|---|---|---|---|
| **A — 2ª instância `nox-mem-api`** | Sobe 2º processo em :18803 com `NOX_DB_PATH=eval.db`. Eval popula a DB via ingest do nox-mem normal; harness aponta `NOX_API_PORT=18803`. | + Zero mudança em código de produção. + Isolamento total — prod nunca toca eval. + Mesmo binário, mesmo pipeline TS. − Precisa popular eval.db via ingest (~5,882 turns × ingest + vectorize ≈ 30–45min). − ~$0,10–0,20 em embeddings novos (mesmo corpus já embeddado em `/tmp/locomo-hybrid-eval.db`, mas em formato pack BLOB diferente do sqlite-vec). | **ESCOLHIDO** |
| B — Poluir `nox-mem.db` com `chunk_type='eval_locomo'` + filtro | Ingerir LoCoMo turns na DB de produção com flag distintiva; filtrar em search. | − Polui salience/recency/KG real. − Risco de `reindex`/`consolidate` afetar eval rows ou vice-versa. − Cleanup pós-run exige `DELETE … WHERE chunk_type=...` na prod (op destrutiva — exige snapshot withOpAudit, ver CLAUDE.md §6). − Mesmo com filtro de chunk_type, ranking de prod muda enquanto eval rodar. | REJEITADO |
| C — Patch `/api/search` aceitar `db` em payload | Adicionar parâmetro `db` ao handler; substituir conexão singleton por per-request open. | − Refactor grande no `src/api-server.ts` + `src/search/hybrid.ts`. − Quebra cache singleton de better-sqlite3 (re-open por request mata perf). − Test coverage zero pro novo path. − Risco de regressão na search prod. | REJEITADO |
| D — Add `--db --json` à CLI v2.3.0 | Adicionar flags a 26+ subcomandos; mexer no router. | − Mudança ampla numa CLI estável. − Já existe `OPENCLAW_WORKSPACE` que efetivamente faz isso via env var — duplicar como flag é redundante. − Ainda assim, harness `run.ts` em modo `--cli` já depende dessa flag — sem ela, modo CLI quebra. **Subsumido em Option A**: a 2ª instância usa `OPENCLAW_WORKSPACE` pra isolar; CLI fica intacta. | REJEITADO (mas ver §5) |

### Critério de defensabilidade científica

O paper precisa responder: *"o ganho de +18,8% nDCG@10 reproduz quando
rodamos contra o pipeline de produção real?"*. Option A é a única que satisfaz
todos estes critérios simultaneamente:

1. **Mesmo binário compilado** que serve `/api/search` em produção (mesma branch, mesmo build).
2. **Zero contaminação** de salience/recency/KG da DB real.
3. **Reproducível** — qualquer reviewer com SSH pode re-rodar o protocolo.
4. **Reversível** — kill -9 da 2ª API + `rm eval.db` volta ao estado pré-run.

---

## 3. Pre-flight checklist (VPS)

> ⚠️ **Toto-only ops.** Esta seção descreve o runbook. NÃO foi executada.

Antes de qualquer comando:

```bash
ssh root@<vps>

# Toda execução nox-mem CLI carrega o .env (CLAUDE.md §1).
set -a; source /root/.openclaw/.env; set +a

# Verifica que a API de produção está saudável ANTES de mexer.
curl -s http://127.0.0.1:18802/api/health | jq ".vectorCoverage, .sectionDistribution"

# Confirma que a porta 18803 está livre (não-default — Chrome não pega).
ss -ltnp | grep -E "(:18803|:18802)"   # esperado: só :18802 ocupada

# Snapshot pré-run da prod (defesa em camadas — CLAUDE.md §6).
ls -la /var/backups/nox-mem/pre-op/ | head -5
```

**Gates pra prosseguir:**

- ✅ `/api/health.vectorCoverage` mostra `embedded == total` na prod.
- ✅ Porta 18803 livre.
- ✅ `GEMINI_API_KEY` no env (sem ela, vectorize falha silencioso — CLAUDE.md §1).
- ✅ Disk free ≥ 2 GB (eval.db ~500 MB com 5.882 chunks × 3072d vetores).

---

## 4. Execution runbook (Option A)

### 4.1 — Criar eval.db isolado com schema atual

```bash
# Diretório dedicado, fora do workspace de produção.
EVAL_ROOT=/root/.openclaw/eval/locomo-prod-path
mkdir -p "$EVAL_ROOT"
chmod 700 "$EVAL_ROOT"

# Aponta CLI/API pra esse DB via NOX_DB_PATH.
export NOX_DB_PATH="$EVAL_ROOT/eval.db"

# Inicializa schema (mesma versão da prod, V7 + v10 columns).
NOX_DB_PATH="$NOX_DB_PATH" nox-mem migrate

# Sanity: schema_version + invariants.
sqlite3 "$NOX_DB_PATH" "PRAGMA user_version; SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
```

**Expected:** `user_version=10`, tables: `chunks`, `chunks_fts`, `vec_chunks`,
`vec_chunk_map`, `kg_entities`, `kg_relations`, `ops_audit`, `search_telemetry`,
`agents`.

### 4.2 — Converter LoCoMo turns em Markdown ingestível

```bash
# Baixa o dataset se ainda não está em cache.
python3 -c "from paper.publication.baselines.locomo_eval import download; download()"
# OU:
# npx tsx eval/locomo/download.ts

# Converte 5,882 turnos -> markdown com frontmatter (~10–30s).
python3 paper/publication/baselines/locomo_to_markdown.py \
    --input  /tmp/locomo10.json \
    --output /tmp/locomo-md/ \
    --manifest /tmp/locomo-md/manifest.jsonl
```

**Saída esperada:**

```
[ok] wrote 5,882 turns (skipped 0 existing, 0 duplicate chunk_ids) -> /tmp/locomo-md
[ok] manifest: /tmp/locomo-md/manifest.jsonl
```

Cada arquivo é um turn, com frontmatter:

```yaml
---
source: "locomo"
sample_id: "conv_42"
session_id: "session_1"
dia_id: "D1:7"
chunk_id: "conv_42::D1:7"
speaker: "Alice"
chunk_type: "eval_locomo"
retention_days: 0
pain: 0.2
---
Alice: <turn text>
<!-- locomo_chunk_id=conv_42::D1:7 -->
```

### 4.3 — Ingest e vectorize na eval.db

```bash
# Ingest batched (watcher off — não queremos race condition com cron prod).
NOX_DB_PATH="$EVAL_ROOT/eval.db" \
    nox-mem ingest /tmp/locomo-md/

# Vectorize batched (~26 chunks/s estável, ~4 min pra 5,882).
NOX_DB_PATH="$EVAL_ROOT/eval.db" \
    nox-mem vectorize

# Validar estado real (NUNCA confiar na última linha do CLI — CLAUDE.md §2).
sqlite3 "$EVAL_ROOT/eval.db" "SELECT COUNT(*) FROM chunks;"
sqlite3 "$EVAL_ROOT/eval.db" "SELECT COUNT(*) FROM vec_chunk_map;"
```

**Gates pra prosseguir:**

- ✅ `chunks` rows ≈ 5,882 (small drop OK por turns sem `dia_id` ou sem `text`).
- ✅ `vec_chunk_map` rows == `chunks` rows (100% coverage).
- ✅ Sample query manual retorna semantic hits:
  ```bash
  NOX_DB_PATH="$EVAL_ROOT/eval.db" nox-mem search "Alice" --limit 5 --json | jq ".results[].match_type"
  # esperado: presença de "semantic" e "fts5"
  ```

### 4.4 — Subir 2ª instância nox-mem-api em :18803

```bash
# Roda em tmux dedicado (CLAUDE.md regra long-running batch).
tmux new -d -s nox-eval-api
tmux send-keys -t nox-eval-api "set -a; source /root/.openclaw/.env; set +a" Enter
tmux send-keys -t nox-eval-api "NOX_DB_PATH=$EVAL_ROOT/eval.db NOX_API_PORT=18803 node /root/.openclaw/workspace/tools/nox-mem/dist/api-server.js" Enter

# Espera vir up (max 10s).
for i in 1 2 3 4 5; do
  if curl -sf http://127.0.0.1:18803/api/health > /dev/null; then break; fi
  sleep 2
done

# Sanity dual-API:
curl -s http://127.0.0.1:18802/api/health | jq ".totalChunks"   # PROD (~62.9k)
curl -s http://127.0.0.1:18803/api/health | jq ".totalChunks"   # EVAL  (~5.882)
```

**Crítico:** confirmar que `totalChunks` na :18803 é da ordem de 5.882 e não
62.9k. Se vier 62.9k, é prod DB sendo aberta — abort imediato e investigar.

### 4.5 — Rodar harness contra :18803

O harness em `eval/locomo/run.ts` (PR #6) já lê `NOX_API_PORT` do env (linha 132).
Só falta passar a porta de eval:

```bash
# Smoke n=10 primeiro (custa $0; ~30s).
NOX_API_PORT=18803 \
    npx tsx eval/locomo/run.ts --n 10 --seed 42 --api \
    > eval/locomo/prod-path-dry-run.json

# Score do smoke (sanity: alguns hits, nDCG > 0).
npx tsx eval/locomo/score.ts eval/locomo/prod-path-dry-run.json

# Full n=100 stratified (mesma seed=42 do E04 e do Python re-impl).
NOX_API_PORT=18803 \
    npx tsx eval/locomo/run.ts --n 100 --seed 42 --api --full \
    > eval/locomo/prod-path-full-run.json

# Score com binomial CI.
npx tsx eval/locomo/score.ts eval/locomo/prod-path-full-run.json --ci
```

> **NB sobre ID resolution:** o harness coleta `chunk_id` do response e compara
> com `gold_chunk_ids` (formato `sample_id::dia_id`). nox-mem retorna `chunk_id`
> como INTEGER da tabela `chunks`. Pra fazer o match, `score.ts` precisa
> resolver via 1 destas estratégias (em ordem de preferência):
>
> 1. **Match via `file_path` heuristic:** `chunk.file_path` no response =
>    `/tmp/locomo-md/<sample_id>/<dia_id_safe>.md`. Parse de volta pro chunk_id
>    canônico. Determinístico — recomendado.
> 2. **Match via frontmatter `chunk_id`:** se `/api/search` retornar metadata
>    parsed (precisa checar response shape — pode estar em `chunk.metadata.chunk_id`).
> 3. **Match via HTML comment anchor:** scan `chunk.text` por
>    `<!-- locomo_chunk_id=... -->` (último recurso — anchor sempre presente
>    no body por design do converter).
>
> Esta resolução é a maior fonte de risco do plano. Recomendação: validar via
> `n=10 --api` smoke run antes do full, conferindo manualmente que ≥3 das 10
> queries têm `retrieved_chunk_ids` ressolvíveis ao formato `sample_id::dia_id`.

---

## 5. Expected outputs e success criteria

### Sanity-band esperado (n=100)

| Métrica | E04 FTS5-only | Python hybrid re-impl | Prod-path target | Sucesso se… |
|---|---|---|---|---|
| nDCG@10 | 0.281 | 0.334 (+18,8%) | ~0.31–0.36 | dentro de ±5pp do Python re-impl |
| R@5     | 0.16  | ~0.22 (estimado) | ~0.20–0.24 | ≥ 18% (binomial CI lower bound) |
| R@1     | 0.07  | ~0.11 (estimado) | ~0.09–0.13 | ≥ 8% |
| MRR     | 0.13  | ~0.18 (estimado) | ~0.16–0.20 | ≥ 14% |

> Os valores R@5/R@1/MRR do Python re-impl são estimados a partir do delta
> nDCG observado; rodar o re-impl e capturar os números exatos é parte do
> follow-up (ver §7).

### Cenários e interpretação

**Cenário A — Convergência (esperado):** prod-path nDCG dentro de ±5pp do
Python re-impl. Reportar como **principal número do paper §5.3**, com Python
re-impl em apêndice como sanity-check arquitetural.

**Cenário B — Prod beats Python:** prod-path > Python re-impl em >5pp. Não
descartar — pode ser efeito de SECTION_BOOST (re-impl não tem), retention_days
priors, ou diferenças sutis em tokenization FTS5. Investigar via per-category
breakdown antes de declarar vitória.

**Cenário C — Python beats prod:** prod-path < Python re-impl em >5pp. **Sinal
de bug.** Hipóteses prioritárias:

1. RRF k=60 não está aplicado na branch atual (verificar `src/search/hybrid.ts`).
2. Embedding model mismatch (prod usa `gemini-embedding-001`; re-impl idem,
   mas confirmar `outputDimensionality=3072` no payload TS).
3. FTS5 tokenizer diff — re-impl usa `unicode61 remove_diacritics 2`, prod
   também (linha CONVENTIONS.md), mas re-verificar via `PRAGMA table_info` da
   `chunks_fts` na eval.db.
4. Boost multiplicativo herdado de E14 stacking — desabilitar via
   `NOX_RANKING_PRESET=raw_hybrid` e re-rodar.

**Cenário D — Sem hits em vários categories:** retorno vazio sistemático em
`adversarial` (cat 5) é **esperado** — LoCoMo design coloca answers fora do
corpus. Per-category nDCG=0 em cat 5 é normal.

---

## 6. Trade-offs e custos

| Item | Valor | Nota |
|---|---|---|
| Custo Gemini (embeddings 5,882 turns × 3072d) | ~$0,05–0,10 | Mesmo turn embeddado 1× para o eval. Sem retries esperados (corpus pequeno). |
| Custo Gemini (queries 100 × 3072d) | ~$0,001 | Trivial. |
| Wall clock total | ~1h | Ingest 10min + vectorize 5min + dual-API spawn <1min + smoke 2min + full run ~5min + score 1min + margens. |
| Disk eval.db | ~500 MB | 5.882 × (3072d × 4B float32) ≈ 70 MB vetores + chunks + FTS5 ≈ 200–500 MB. |
| Carga adicional na VPS | baixa | 2ª API só é tocada pelo harness; RAM ~80 MB; CPU idle entre queries. |
| Risco prod | quase-zero | DB de prod nunca aberta; só compartilha binário em disco. |

### Riscos não-zero

1. **Compartilhamento de logs:** se a 2ª API loga em `/var/log/nox-mem/*.log`
   (mesmo path da prod), pode haver interleave. Mitigação: `NOX_LOG_FILE=$EVAL_ROOT/eval-api.log`
   no env da tmux session.
2. **WAL contention:** ambas APIs apontam pra DBs distintas, mas se algum
   módulo lê `nox-mem.db` por path hardcoded (deveria não ler — singleton via
   `NOX_DB_PATH`), pode haver SQLITE_BUSY. Mitigação: confirmar `busy_timeout=5000`
   ativo (CONVENTIONS.md) e checar logs após smoke.
3. **Drift de schema:** se a prod estiver em v10 mas o binário compilado for
   v11 (após deploy), `nox-mem migrate` na eval.db levaria pra v11, e o
   pipeline aplicaria features novas que não existem na v3.7 publicada do paper.
   Mitigação: registrar `git rev-parse HEAD` do checkout deployado em
   `prod-path-full-run.json` (sufixo `meta.git_sha`).

---

## 7. Open questions e follow-up

1. **Cleanup vs preservar:** após o run, manter eval.db pra future re-runs
   (ex: ranking change validation) ou nuke? Recomendação: **preservar em**
   `$EVAL_ROOT/eval.db.snapshot-<git_sha>` + `gzip`. Tamanho ~150 MB
   compactado, custo de re-build seria $0,05 + ~10 min.
2. **Métricas Python re-impl exatas:** este doc cita +18,8% nDCG. Os números
   exatos pra R@5/R@1/MRR do re-impl precisam vir do JSON salvo em
   `paper/publication/results/locomo-hybrid-results.jsonl` (gerado pelo
   `locomo_hybrid_eval.py`) — incluir esses números na §5 antes de rodar.
3. **Ablation production-only features:** após convergência confirmada, vale
   rodar variant com `chunk_type=eval_locomo` mas com SECTION_BOOST/retention
   bypassed pra isolar contribuição da arquitetura puro-hybrid vs
   hybrid+SECTION. Coordenar com D40 (boost stacking decision).
4. **CI gate:** quando este número virar oficial, considerar adicionar
   regressão CI (re-run mensal com mesmo seed/n; alarm se nDCG cai >2pp).
   Custo recorrente ~$0,05/mês. Não bloqueia este PR.

---

## 8. Post-run cleanup

```bash
# 1. Kill 2ª API.
tmux kill-session -t nox-eval-api

# 2. Snapshot do eval.db pra reproducibility (opcional, recomendado).
GIT_SHA=$(cd /root/.openclaw/workspace/tools/nox-mem && git rev-parse --short HEAD)
gzip -c "$EVAL_ROOT/eval.db" > "$EVAL_ROOT/eval.db.snapshot-${GIT_SHA}.gz"

# 3. Limpa markdown intermediário (mantém só DB + JSON results).
rm -rf /tmp/locomo-md/

# 4. Confirma que prod NÃO foi tocada.
curl -s http://127.0.0.1:18802/api/health | jq ".totalChunks, .vectorCoverage"
# Esperado: totalChunks ~62.9k (mesmo antes), embedded == total.
```

**Audit trail:** anexar `eval/locomo/prod-path-full-run.json` no PR de
paper-numbers + entry em `docs/INCIDENTS.md` (não é incident — é run log)
OU em `docs/HANDOFF.md` (mais provável).

---

## 9. Quality gates antes de declarar o número oficial

- [ ] `prod-path-full-run.json` tem `meta.git_sha`, `meta.n=100`, `meta.seed=42`,
      `meta.mode=api`.
- [ ] Pelo menos 95 das 100 queries têm `retrieved_chunk_ids` não-vazio (taxa
      de erro <5%).
- [ ] ID resolution funcionou pra ≥99% dos chunks retornados (sem fallback
      no HTML comment anchor).
- [ ] Score JSON inclui binomial 95% CI em R@5 (via `score.ts --ci`).
- [ ] Sanity: prod-path nDCG@10 vs Python re-impl dentro de ±5pp **OU**
      explicação documentada do delta (ver §5 cenários B/C).
- [ ] Diff prod `/api/health.vectorCoverage` antes/depois: idêntico.
- [ ] Re-run do harness com `--n 10` produz mesmas top-K → determinismo OK.

---

## Referências cruzadas

- `specs/2026-05-18-Q1-Q2-Q3-vps-scheduling.md` §2 — autorização operacional Q1.
- `eval/locomo/README.md` — protocolo D1–D7 + isolation guarantees.
- `eval/locomo/run.ts` — harness (já tem `--api` + `NOX_API_PORT` env).
- `paper/publication/baselines/locomo_hybrid_eval.py` — Python re-impl (origem do +18,8%).
- `paper/publication/baselines/locomo_eval.py` — FTS5-only baseline E04.
- `paper/publication/results/locomo-hybrid-vs-fts5-summary.md` — sumário Python re-impl.
- `docs/CONVENTIONS.md` §"Embedding em massa", §"`/api/health.vectorCoverage`".
- `CLAUDE.md` §1 (.env), §2 (validate post-op), §4 (port 18802), §6 (snapshots).

---

*Autoria: scientist-high agent (research/2026-05-18/q1-production-path), 2026-05-18.*
*Status: PLAN — execução supervisionada por Toto, em sessão separada.*
