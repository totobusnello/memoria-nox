# Backbone Matrix — Claude (Sonnet 4.6 / Opus 4.7) — TEMPLATE PRÉ-RUN

> **Status:** PENDENTE — run não executado. Preencher após 5-batch completo.
> **Pré-requisito bloqueante:** `ANTHROPIC_API_KEY` ausente em `/root/.openclaw/.env`
> (ver §Auth & custo abaixo — solução: provisionar via Anthropic Console billing).

---

## Metodologia

Idêntica à backbone matrix original (PR que gerou `RESULTS-BACKBONE-MATRIX.md`):

| Parâmetro | Valor |
|---|---|
| Pipeline base | Phase H v2 frozen (search → retrieve → rerank-OFF → answer → evaluate) |
| DBs | Phase B pré-warmed (batches 004/005/010/011/016, sha igual cross-backbone) |
| top_k | 20 |
| Rerank | OFF (`NOX_RERANKER_ENABLED=0`) |
| Adapter mode | phaseB (sem Wave A/B/C knobs) |
| Knob variável | **Somente answer backbone** — tudo mais constante |
| Judge | gemini-2.5-flash (constante cross-backbone para comparabilidade) |
| Gate canônico | **5-batch (n≈626/batch = 3121 total) + 95% CI** |
| Gate secundário 4-gate | Overall ≥+3pp AND MA ≥+5pp AND F_MH ≥+5pp AND F_HL ≥+3pp vs baseline |

> **NOTA single-batch:** conforme `[[single-batch-gates-unreliable-5x-overstate]]`, single-batch
> overstata resultado em 3-6×. Usar 5-batch obrigatoriamente para gate canônico.

### Batches + portas

| Batch | DB pré-warmed | Porta |
|---|---|---|
| 004 | `/root/.openclaw/evermembench-runs/phaseB-004-1779988559/nox-mem.db` | 18830 |
| 005 | `/root/.openclaw/evermembench-runs/phaseB-005-1779990311/nox-mem.db` | 18831 |
| 010 | `/root/.openclaw/evermembench-runs/phaseB-010-1779990316/nox-mem.db` | 18832 |
| 011 | `/root/.openclaw/evermembench-runs/phaseB-011-1779990322/nox-mem.db` | 18833 |
| 016 | `/root/.openclaw/evermembench-runs/phaseB-016-1779990327/nox-mem.db` | 18834 |

---

## Headline (preencher pós-run)

| Backbone | n (5-batch) | Overall | F_MH | F_MH lift vs baseline | F_MH closure of MemOS gap | F_HL | F_TP | MA composite | 4-gate | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| gpt-4.1-mini (baseline, PR #377) | 3121 | 51.68% | 3.21% | +0.00pp | 0.0% | 22.68% | 15.00% | 73.34% | 3/4 | reference |
| gemini-3-flash-preview | 3121 | 63.28% | 6.02% | +2.81pp | 18.0% | 26.03% | 34.33% | 88.42% | 3/4 | ship opt-in |
| gemini-3.1-flash-lite-preview | 3121 | 62.29% | 6.02% | +2.81pp | 18.0% | 60.82% | 12.00% | 82.82% | 3/4 | ship opt-in |
| **claude-sonnet-4-6** | **—** | **—** | **—** | **—** | **—** | **—** | **—** | **—** | **—** | **PENDENTE** |
| claude-opus-4-7 (opcional) | — | — | — | — | — | — | — | — | — | PENDENTE |

MemOS anchor (arXiv 2602.01313 Table 4, GPT-4.1-mini backbone): Overall 42.55%, F_MH 18.88%

---

## Auth & custo

### Veredito de auth: NÃO dá pra rodar Claude a $0

**Evidência primária:** `eval/evermembench/RESULTS-BACKBONE-MATRIX.md` linhas 154–157:

```
Status: ANTHROPIC_API_KEY missing from /root/.openclaw/.env.
Only ANTHROPIC_MAX_API_KEY (Claude MAX subscription OAuth session token, sk-ant-oat01-...)
present. Policy boundary: Using MAX OAuth token to drive thousands of automated bench API
calls = account-policy violation (programmatic batch ≠ interactive Claude Code session).
Platform classifier correctly blocked this attempt during preflight.
```

O token `ANTHROPIC_MAX_API_KEY` (`sk-ant-oat01-...`) é credencial OAuth de sessão do
Claude Code — não uma API key de billing. O platform classifier **bloqueou** o uso para
batch automatizado. Não tentar contornar via env var aliases ou wrappers.

**Único caminho viável:** provisionar `ANTHROPIC_API_KEY` standard:
1. Acessar https://console.anthropic.com/ → API Keys → Create Key
2. Adicionar em `/root/.openclaw/.env`: `ANTHROPIC_API_KEY=sk-ant-api03-...`
3. Verificar que a conta tem saldo suficiente (~$40–50 para 5-batch Sonnet)

### Incerteza crítica: base_url + formato do endpoint

O harness usa **OpenAI Python SDK** com `base_url` + `api_key` do pipeline.yaml.
Chama `POST {base_url}/chat/completions` com `Authorization: Bearer {api_key}`.

Anthropic nativo:
- Endpoint: `https://api.anthropic.com/v1/messages` (NÃO `chat/completions`)
- Auth header: `x-api-key: {key}` (NÃO `Authorization: Bearer`)

Dois caminhos documentados no `pipeline-backbone-claude.yaml`:

**Hipótese A — Anthropic direto** (`base_url: "https://api.anthropic.com/v1/"`):
- Intenção original per RESULTS-BACKBONE-MATRIX.md ("Anthropic API supports max_tokens +
  temperature natively, no patch needed")
- Risco: 404 ou auth mismatch se Anthropic não expõe `/v1/chat/completions` para OAuth Bearer
- Verificar antes do 5-batch:
  ```bash
  curl -s "https://api.anthropic.com/v1/chat/completions" \
    -H "Authorization: Bearer $ANTHROPIC_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"model":"claude-sonnet-4-6","messages":[{"role":"user","content":"OK"}],"max_tokens":5}' \
    | head -c 200
  ```
  Se retornar `{"content":[...]}` → Hipótese A OK. Se retornar 404 ou 401 → usar B.

**Hipótese B — OpenRouter** (fallback garantido):
- `model: "anthropic/claude-sonnet-4-6"` (prefixo `anthropic/` obrigatório)
- `api_key: "${OPENROUTER_API_KEY}"` (chave diferente de ANTHROPIC_API_KEY)
- `base_url: "https://openrouter.ai/api/v1"`
- Harness usou OpenRouter em fases iniciais (INVESTIGATION.md §3: "All inference routed
  via OpenRouter")
- Custo similar; OpenRouter cobra o mesmo preço que Anthropic direto

**Recomendação:** smoke test em batch único (`BATCHES_ENV="004"`) antes do 5-batch completo.

### Estimativa de custo — Claude Sonnet 4.6 (5-batch)

> Preços estimados; verificar https://anthropic.com/pricing antes do run.

| Estágio | Modelo | Input tokens/q | Output tokens/q | n (5-batch) | Custo/1M in | Custo/1M out | Total est. |
|---|---|---:|---:|---:|---:|---:|---:|
| Answer | claude-sonnet-4-6 | ~3 300 | ~200 | 3 121 | ~$3 | ~$15 | ~$41 |
| Evaluate (OE judge) | gemini-2.5-flash | ~500 | ~100 | ~1 560 | $0.30 | $2.50 | ~$1 |
| **Total** | | | | | | | **~$42** |

Claude Opus 4.7 (se rodar full 5-batch): Answer ~$195 (~$15/$75 por 1M tokens).
Sugestão: smoke test Opus em batch único (004) antes de comprometer o budget.

---

## Per-batch detail (preencher pós-run)

### claude-sonnet-4-6 — 5-batch (n=TBD)

| dimension | n_batches | sum_total | sum_correct | weighted | mean | stdev | 95% CI |
|---|---:|---:|---:|---:|---:|---:|---|
| Overall | — | — | — | — | — | — | — |
| F_SH | — | — | — | — | — | — | — |
| F_MH | — | — | — | — | — | — | — |
| F_TP | — | — | — | — | — | — | — |
| F_HL | — | — | — | — | — | — | — |
| MA_C | — | — | — | — | — | — | — |
| MA_P | — | — | — | — | — | — | — |
| MA_U | — | — | — | — | — | — | — |
| P_Style | — | — | — | — | — | — | — |
| P_Skill | — | — | — | — | — | — | — |
| P_Title | — | — | — | — | — | — | — |

### claude-opus-4-7 — single-batch smoke (n=TBD, batch 004)

| dimension | n (1 batch) | correct | accuracy | Note |
|---|---:|---:|---:|---|
| Overall | — | — | — | Sample only; run full 5-batch se smoke OK |
| F_MH | — | — | — | Indicador chave |

---

## Comando de disparo (quando ANTHROPIC_API_KEY disponível)

```bash
# Rodar em tmux na VPS (lição: long-running batch = tmux + script em arquivo)

# 1. Criar WORK dir e copiar artefatos
WORK=/root/.openclaw/backbone-matrix-claude-$(date +%s)
mkdir -p "$WORK"

# 2. Copiar yamls + scripts do repo local para WORK
cp /path/to/repo/eval/evermembench/pipeline-backbone-claude.yaml "$WORK/"
cp /path/to/repo/eval/evermembench/run-batch-backbone-claude.sh "$WORK/"
cp /path/to/repo/eval/evermembench/aggregate_backbone_matrix.py "$WORK/"

# 3. Linkar harness pré-instalado
ln -sf /root/.openclaw/evermembench-phaseB-1779978778/everos "$WORK/everos"

# 4. Smoke test PRIMEIRO (1 batch, 5min, ~$8):
#    WORK="$WORK" BATCHES_ENV="004" bash "$WORK/run-batch-backbone-claude.sh"
#    Verificar $WORK/stream.log e RUN_DIR/analysis.txt antes de prosseguir.

# 5. Se smoke OK: 5-batch canônico em tmux
tmux new-session -d -s bb-claude "WORK=$WORK bash $WORK/run-batch-backbone-claude.sh 2>&1 | tee $WORK/bb-claude.log"
tmux attach -t bb-claude
# Wallclock esperado: ~5-8min (Sonnet 4.6). Monitorar eval.log de cada batch.

# 6. Agregar (pós-run)
python3 "$WORK/aggregate_backbone_matrix.py" \
    --json "$WORK/RESULTS-BACKBONE-CLAUDE.json" \
    --md "$WORK/RESULTS-BACKBONE-CLAUDE.md"
```

---

## Framing para o paper

Hipótese testada: "nox-mem é backbone-agnostic — Claude deve performar comparável
a Gemini-3 na mesma retrieval pipeline frozen."

Honest framing obrigatório (lição da backbone matrix):
- Judge = gemini-2.5-flash para TODOS os backbones → homogeneity bias existe para
  Gemini entries, mas NÃO para Claude. Isso é uma VANTAGEM para o Claude entry:
  Claude + Gemini judge é cross-family (menos suspeito que Gemini → Gemini).
- Se Claude supera Gemini-3 com juiz Gemini, o resultado é mais credível (juiz não
  é da mesma família do modelo avaliado).
- F_MH gap é estruturalmente retrieval-bound (82% per backbone matrix § F_MH gap
  analysis) — Claude backbone não deve fechar isso sozinho.

---

## Incertezas não resolvidas

1. **`/v1/chat/completions` compat (CRÍTICA):** confirmar antes do 5-batch se
   `https://api.anthropic.com/v1/chat/completions` aceita `Authorization: Bearer`
   via OpenAI SDK. Se não, trocar para OpenRouter (Hipótese B no yaml).

2. **Preflight vs harness auth gap:** o script de preflight usa `x-api-key` (nativo
   Anthropic) mas o harness usa `Authorization: Bearer` (OpenAI SDK). Um pode passar
   e o outro falhar — fazer o curl de smoke test do endpoint `/chat/completions`
   explicitamente antes de confiar no preflight.

3. **Opus 4.7 thinking + concurrency:** similar ao gemini-2.5-pro (hung 38min).
   Reducer para `concurrency: 2` no yaml antes de qualquer Opus run.

4. **OPENROUTER_API_KEY disponibilidade:** se Hipótese A falhar, verificar se
   `OPENROUTER_API_KEY` está presente em `/root/.openclaw/.env` (usado nas fases
   iniciais; pode ter expirado ou sido removido).

5. **Custo real:** estimativa ~$42 para Sonnet 5-batch. Verificar saldo Anthropic
   Console ANTES de disparar o run.
