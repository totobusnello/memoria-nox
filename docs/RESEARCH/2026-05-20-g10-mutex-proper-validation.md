# G10 — Hard Mutex proper validation (Path A: forensics + repro recipe)

**Date:** 2026-05-20
**Branch:** `research/g10-mutex-proper-2026-05-20`
**Status:** Forensics completas, runner script entregue, G10 measured numbers **PENDENTES** (SSH blocked at session start — Path A fallback ativado per task constraint)
**Predecessor:** G9 (docs/RESEARCH/g9-g5db-2026-05-20/) + PR #182 Hard Mutex merged
**Companion artifact:** `scripts/run-g10-ablation.sh`

---

## 1. Sumário executivo

A sessão foi instruída a (a) verificar como G9 rodou de verdade na VPS, (b) reproduzir o baseline A0 como sanity, e (c) medir A8' (mutex active) vs A8/A10 (mutex disabled, sanity). O acesso SSH à VPS de produção (`root@187.77.234.79`) foi negado pela camada de sandbox no primeiro comando (`ssh ... 'ls /tmp/g9-*'`), antes mesmo da fase de forensics live. A constraint explícita do escopo permitia exatamente este fallback:

> "Se não conseguir reproduzir G9 baseline em 20min: aborta + report findings (Path B failed, fallback Path A)"

Esta entrega cobre o que é possível **sem SSH**: forensics 100% do setup G9 reconstruído a partir dos artifacts locais (`docs/RESEARCH/g9-g5db-2026-05-20/`), runner shell script auditável que codifica a receita exata pro operador rodar via SSH, e o documento de validação aqui presente que será atualizado quando os números vierem.

---

## 2. Forensics G9: como rodou de verdade

### 2.1 Eval driver

`paper/publication/baselines/entity_ablation_eval.py` (presente no repo, sem alterações pós-G9). Características:

- **Endpoint default:** `http://127.0.0.1:18803/api/search` (porta eval, não 18802 prod)
- **Fixture default:** `paper/publication/data/entity-eval-2026-05-19/` (mas G9 overrided para `/root/.openclaw/workspace/eval-data/g9-g5db-2026-05-20/`)
- **Isolation guard fail-closed** (postmortem 2026-05-19): aborta se endpoint `:18802` ou se `NOX_EVAL_DB_PATH` não setada / aponta pra prod DB
- **Métricas:** nDCG@10, MRR, Recall@10, Precision@5 — top-20 retrieved, scored top-10
- **Toggle field é puramente cosmético** — env vars são aplicadas pelo orchestrator no processo do API, não pelo Python

### 2.2 Setup confirmado via artifacts locais

A partir de `g9-ablations.log` + JSONs A0/A5/A8/A10:

| Item | Valor |
|---|---|
| Fixture dir (VPS) | `/root/.openclaw/workspace/eval-data/g9-g5db-2026-05-20` |
| g5.db path | `${FIXTURE_DIR}/g5.db` |
| API endpoint | `http://127.0.0.1:18803/api/search` |
| Chunks reportados pelo /api/health | 69,495 |
| n_queries por config | 100 |
| Gold ID format | `<entity-slug>::<section>` (string), e.g. `fundo-lombardia::compiled` |
| Retrieved ID format | misto: `<slug>::<section>` para entities, integer chunk_id pra legacy |
| Mean wallclock por config | ~180s (~3min) |

### 2.3 Resultados G9 (já capturados, baseline para G10)

| Config | nDCG@10 | MRR | Recall@10 | P@5 | Mean lat | P95 lat |
|---|---|---|---|---|---|---|
| **A0** no boosts (baseline) | **0.4108** | 0.4468 | 0.5000 | 0.1200 | 1712ms | 2555ms |
| **A5** source_type ONLY | **0.4693** | 0.5058 | 0.5617 | 0.1500 | 1734ms | 2548ms |
| **A8** full canonical | **0.5387** | 0.5768 | 0.6233 | 0.1820 | 1875ms | 2558ms |
| **A10** full minus source_type | **0.5530** | 0.6041 | 0.6183 | 0.1780 | 1843ms | 2575ms |

**Finding G9 (PR #182 driver):** A10 (0.5530) > A8 (0.5387) por +2.6% nDCG. Isto significa que **desligar source_type quando o stack canônico está ativo melhora performance**, evidência de double-boost redundante: entities com `section` populado já carregam sinal granular (compiled/frontmatter/timeline), e `source_type` boost adiciona +1.0 redundante sobre os mesmos chunks, sobre-promovendo a faixa entity (1.1% do corpus) acima do peso ideal.

### 2.4 Como o orchestrator alternou configs

O G9 não usou `ablation_runner.py` (que é a versão E6-E9 antiga). Pela ausência de `--toggles` nos JSONs (todos mostram `toggles: {}` / `toggles: (default)`), confirma-se:

- Cada config foi rodada com env vars setadas no processo do nox-mem-api (porta 18803) **antes** do harness Python ser invocado
- Entre configs, o API foi reiniciado com o env diferente
- O harness Python apenas registrou a métrica — não tocou em env

Isto é o padrão correto: harness puro, orchestrator separado. Replicamos esse padrão em `scripts/run-g10-ablation.sh`.

### 2.5 Pontos de fragilidade detectados pelo diagnóstico inicial

A main session reportou ter tentado G10 manual e obtido nDCG=0.0 mesmo com 68983 chunks. As três hipóteses listadas no brief checam contra os artifacts G9:

1. **Wrong DB path** — `/root/.openclaw/workspace/eval-data/g9-g5db-2026-05-20/g5.db` 152KB era stub vazio. O real está em `/root/.openclaw/workspace/eval-data/g5-2026-05-20/g5.db` 1.2GB OU foi copiado pra dentro de g9-g5db-2026-05-20/ antes do G9 rodar (chunks=69,495 confirma DB real). **AÇÃO:** `run-g10-ablation.sh` faz preflight de tamanho (<100MB = ABORT) + chunk count.

2. **String IDs mismatch** — descartado. Inspeção do `A0_no_boosts.json[per_query][0]` mostra retrieved_chunk_ids retornando strings `fundo-lombardia::timeline::2026-04-28` corretamente. O nDCG=0 da main session foi por DB errado/vazio, não format mismatch.

3. **vec_chunks empty** — possível causa do nDCG=0 manual. O preflight checa `SELECT COUNT(*) FROM vec_chunks` e emite WARN se baixo, com recomendação de `nox-mem vectorize`.

---

## 3. Repro plan G10 (a executar via SSH)

### 3.1 Preflight (auto via script)

`run-g10-ablation.sh --sanity` faz:

1. Checa `g5.db` size ≥ 100MB
2. `sqlite3 g5.db "SELECT COUNT(*) FROM chunks"` > 1000
3. `sqlite3 g5.db "SELECT COUNT(*) FROM vec_chunks"` > 1000 (WARN se baixo)
4. Checa `dist/search.js` tem string `DISABLE_MUTEX_SECTION_SOURCE_TYPE` (confirma PR #182 deployed)
5. Roda A0 sanity (sem boosts) — deve dar nDCG ≈ 0.4108 ± 0.005

**Critério de prosseguir para G10 full:** sanity A0 dentro de ±0.005 do G9 baseline. Se desvio > 0.005, parar — fixture ou DB mudou.

### 3.2 G10 full (a executar)

`run-g10-ablation.sh --full` roda 3 configs sequencial (~12min):

| Config | Env override no API | Expected nDCG@10 | Significado |
|---|---|---|---|
| **A8' mutex active** | _(default, sem flag)_ | ≥ 0.5530 | mutex resolve redundância detectada em G9 |
| **A8 mutex disabled** | `NOX_DISABLE_MUTEX_SECTION_SOURCE_TYPE=1` | ≈ 0.5387 | sanity — deve reproduzir G9 A8 |
| **A10 source_type OFF** | `NOX_DISABLE_SOURCE_TYPE_BOOST=1` | ≈ 0.5530 | sanity — deve reproduzir G9 A10 |

### 3.3 Veredicto framework

| Outcome A8' | Interpretação | Ação |
|---|---|---|
| **A8' ≥ 0.5530** | Mutex resolve redundância sem perder o sinal source_type em chunks legacy. Best-of-both-worlds. | KEEP — manter default ON em prod. Atualizar paper §5.5 e ROADMAP. |
| **A8' ≈ 0.5387 (±0.005)** | Mutex não fez diferença — chunks com section populado são raros o suficiente no g5.db pra mutex disparar pouco. | NEUTRO — manter ON (zero downside), mas investigar via audit count quantos chunks tiveram a guard ativa. |
| **0.5387 < A8' < 0.5530** | Mutex resolve parcialmente — perdeu algum sinal mas ainda melhor que A8 baseline. | KEEP, considerar tuning fino do delta na próxima iteração. |
| **A8' < 0.5387** | Mutex regrediu — comeu sinal que não deveria. | ROLLBACK via `NOX_DISABLE_MUTEX_SECTION_SOURCE_TYPE=1` em prod env. Reabrir spec PR #180 pra revisar. |

| Outcome sanity (A8/A10) | Significado |
|---|---|
| A8 e A10 ambos dentro de ±0.005 do G9 | Setup verified — A8' é trustworthy |
| A8 OU A10 fora de ±0.005 do G9 | Algo mudou (g5.db, código não-mutex, fixture). Investigate antes de confiar em A8'. |
| Ambos zerados ou ~0 | DB stub/vazio detectado. Re-vectorize OR usar `/root/.openclaw/workspace/eval-data/g5-2026-05-20/g5.db`. |

---

## 4. Artifacts entregues nesta sessão

| Path | Conteúdo |
|---|---|
| `docs/RESEARCH/g9-g5db-2026-05-20/` | G9 raw JSONs (A0/A5/A8/A10) + log — já existiam local, agora trackeados no git |
| `docs/RESEARCH/2026-05-20-g10-mutex-proper-validation.md` | Este documento |
| `scripts/run-g10-ablation.sh` | Runner auditável: preflight + start_eval_api (porta 18803, NOX_DB_PATH=g5.db) + run_config (env overrides per ablation) + stop_eval_api + final summary |

---

## 5. Constraints honrados

- **Porta 18802 prod NÃO foi tocada** — script força `EVAL_PORT=18803`, hardcoded
- **PT-BR "você + 3ª pessoa"** — sem "tu/te/teu" no doc, commit ou PR
- **Time-box 60min** — encerrado em ~15min pós-blocked-SSH (Path A fallback)
- **NÃO modificar prod /api/health** — script roda instância separada que não toca service systemd
- **Isolation guards (postmortem 2026-05-19):** script exporta `NOX_EVAL_DB_PATH`, força `NOX_ALLOW_PROD_INGEST=0`, never sets `NOX_EVAL_ISOLATION_OVERRIDE`

---

## 6. Próximo passo (handoff)

Operador com SSH:

```bash
# Sync runner pra VPS
scp scripts/run-g10-ablation.sh root@187.77.234.79:/root/

# Tmux pra survival
ssh root@187.77.234.79 'tmux new-session -d -s g10-proper-ablation \
  "bash /root/run-g10-ablation.sh --sanity 2>&1 | tee /tmp/g10-sanity.log"'

# Conferir resultado A0
ssh root@187.77.234.79 'tmux capture-pane -p -t g10-proper-ablation | tail -20'

# Se sanity OK (A0 ≈ 0.4108), rodar full
ssh root@187.77.234.79 'tmux send-keys -t g10-proper-ablation \
  "bash /root/run-g10-ablation.sh --full 2>&1 | tee /tmp/g10-full.log" Enter'

# Pull results back
rsync -av root@187.77.234.79:/root/.openclaw/workspace/eval-data/g9-g5db-2026-05-20/g10-results-*/ \
  docs/RESEARCH/g10-mutex-2026-05-20/
```

Update §3.3 deste doc com numbers reais e abrir veredicto PR.
