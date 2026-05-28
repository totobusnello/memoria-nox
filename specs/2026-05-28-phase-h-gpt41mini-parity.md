# Phase H — EverMemBench GPT-4.1-mini Backbone Parity

**Status:** SPEC (não dispatched) — gated em Phase G completion
**Author:** Toto (via auto-mode session 2026-05-28)
**Predecessors:** Phase D (PR #365, 5-batch 62.22% vs MemOS 59.27% on Gemini-2.5-flash)

## Goal

Reproduzir setup Phase D mas trocando backbone para **GPT-4.1-mini** para obter direct apples-to-apples comparison contra coluna GPT-4.1-mini do MemOS paper Table 4 (arxiv 2602.01313 §4.2).

**Hipótese:** se Phase D win (+2.95pp overall) é estrutural (adapter + top_k=20) e não específico a Gemini-2.5-flash, deve replicar em GPT-4.1-mini.

## Why now (após Phase G)

Phase G resolve (ou confirma) ceiling em multi-hop dimensão.
Phase H resolve cross-backbone generalidade dimensão.

Ambas alimentam paper §5 narrative:
- §5.1: "We beat MemOS on Gemini-2.5-flash" (Phase D)
- §5.2: "We beat MemOS on GPT-4.1-mini too" (Phase H — se win)
- §5.3: "Multi-hop attack: <conclusão Phase G>"
- §5.4: "Structural advantage is the adapter, not the backbone"

## Config

| Param | Value | Source |
|---|---|---|
| Adapter mode | `phaseB` (default em PR #364) | Phase D config |
| `top_k` | 20 | Phase D config |
| Backbone | `gpt-4.1-mini` (was `gemini-2.5-flash`) | NEW |
| API: nox-mem-api | isolated port (e.g. 18816) | mesmo padrão Phase G |
| DB: nox-mem.db copy | `/tmp/evermembench-phaseH-<ts>.db` | mesmo padrão Phase G |
| Batches | 004 single first; 5-batch gated | conservar budget |
| Reranker | OFF (Phase G decides ON/OFF separately) | isolar variável |

## Budget

- Single batch 004: ~$1.00 (GPT-4.1-mini ~$0.40/1M in + $1.60/1M out; ~626 queries × ~3k tokens avg)
- 5-batch: ~$5.00 total
- Available pós-G: $10 cap − (~$0.80 Phase F + Phase G actual) = ~$8 sobra ANTES de H

**Decision gate batch 004:**
- ✅ Overall ≥ MemOS GPT-4.1-mini Table 4 column → run 5-batch
- ❌ Overall < MemOS column → STOP, document parity failure, paper §5 narrative ajusta

## Prereq — MemOS Table 4 numbers

Antes de dispatch, **agente deve extrair** os números exatos da Table 4 para coluna GPT-4.1-mini:
- MemOS overall %
- MemOS MC %
- MemOS OE %
- MemOS MH %

Source: arxiv 2602.01313 §4.2, Table 4. Already cached em `eval/evermembench/INVESTIGATION.md` (se sim use direto; senão refetch via `mcp__plugin_context-mode_context-mode__ctx_fetch_and_index`).

## Prereq — API key

Confirmar `OPENAI_API_KEY` em `/root/.openclaw/.env` na VPS (provavelmente já existe para outros adapters Q4).

## Plan (agente executor-high)

1. **MemOS numbers extract:** ler `eval/evermembench/INVESTIGATION.md` para coluna GPT-4.1-mini; se ausente, fetch arxiv PDF
2. **VPS setup:** `/tmp/evermembench-phaseH-<uuidgen>/` work dir, copy DB
3. **Start eval nox-mem-api:** isolated port 18816, NOX_RERANKER_MODE=off (isolar de Phase G), NOX_DB_PATH explicit
4. **Smoke test:** 3 queries via /api/search, confirm api healthy
5. **Verify OPENAI_API_KEY:** `echo $OPENAI_API_KEY | head -c 10` (não logar full key)
6. **Run batch 004 with backbone=gpt-4.1-mini**
7. **Compare results** to MemOS Table 4 GPT-4.1-mini column
8. **Gate decision:** 5-batch ou stop
9. **PR:** RESULTS-PHASEH.md + commit + push + open
10. **Cleanup:** `rm -rf $WORK_DIR`, kill eval api

## Anti-patterns (mesmo set Phase G)

- ❌ `.env` global override → SEMPRE set `NOX_DB_PATH` explicit
- ❌ Trust env var presence → verify api healthy + backbone correctly configured antes de queries
- ❌ Run 5-batch sem gate batch 004 → desperdiça $4
- ❌ `--no-verify` em commits; use `COMMIT_TO_NON_MAIN_OK=1`
- ❌ "tu/te/vc" em PT-BR docs

## Closure

PR title: `feat(eval): Phase H GPT-4.1-mini parity batch 004 — <result>`
PR body: results table (batch 004 + 5-batch se aplicável), MemOS column comparison, paper §5 narrative recommendation.

## Não-objetivos

- Mudar adapter logic — fixa em phaseB (Phase D config)
- Mudar reranker config — isola de Phase G
- Mudar outras dims (chunking, retrieval) — só backbone swap
- Testar outros OpenAI models (gpt-4o, gpt-4o-mini, gpt-4.1) — escopo é parity exato com MemOS Table 4

## Dependencies

- Phase G completion (libera budget mental + decide reranker variável)
- Phase G result NÃO precisa ser positivo — Phase H é independente

## Reference docs

- `eval/evermembench/INVESTIGATION.md` — MemOS paper extraction
- `eval/evermembench/RESULTS-PHASED.md` (em PR #365) — Phase D config exato
- `eval/evermembench/RESULTS-PHASEF.md` (em PR #366) — Phase F failure modes para evitar
- `eval/evermembench/RESULTS-PHASEG.md` (em PR Phase G) — reranker decision context
