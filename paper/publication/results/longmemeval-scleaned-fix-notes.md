# Q2 LongMemEval `s_cleaned` — UNIQUE constraint fix

**Date:** 2026-05-18
**Branch:** `q-runs/2026-05-18/q2-scleaned-fix`
**Script:** `paper/publication/baselines/longmemeval_hybrid_eval.py`

## Sintoma

`oracle` split rodou limpo (n=100, métricas saturadas em 1.0 — esperado porque oracle tem ~0 distractors). Quando trocou pra `s_cleaned` na VPS:

```
[download] saved: /tmp/longmemeval-s_cleaned.json (277,383,467 bytes)
Traceback (most recent call last):
  File "longmemeval_hybrid_eval.py", line 931, in main
    build_index(corpus)
  File "longmemeval_hybrid_eval.py", line 304, in build_index
    con.executemany("INSERT INTO chunks(chunk_id,...) VALUES(?,?,?,?,?,?)", rows)
sqlite3.IntegrityError: UNIQUE constraint failed: chunks.chunk_id
```

`build_index()` cria `chunks` com `chunk_id TEXT PRIMARY KEY` e tenta `executemany` 100% das linhas geradas por `iter_session_chunks()`. Qualquer colisão de `chunk_id` aborta a transação inteira.

## Root cause

`chunk_id = f"{question_id}::{session_id}"` (linha 264 pré-fix) é único **across questions**, mas NÃO é único **within a question** se `haystack_session_ids` listar o mesmo `session_id` mais de uma vez.

`oracle` split contém só sessões evidência (uma por question) → sem duplicatas → passa.

`s_cleaned` (split headline do paper, ~115k tokens por question, ~40 sessões cada) interleava distractor sessions e **re-cita** algumas pra inflar o haystack. É comportamento esperado do dataset, não corruption. Confirmado por inspeção do shape:

- `haystack_session_ids: ["s_A", "s_B", "s_A", "s_C", "s_B", ...]` — `s_A` aparece 2× dentro da MESMA question.
- Ambos mapeiam pra `chunk_id = "q_id::s_A"` → segunda inserção dispara `UNIQUE constraint failed`.

## Fix escolhido: dedup em Python antes do INSERT (Option C-variant)

Adicionado `seen_sids: set[str]` por-question dentro do loop em `iter_session_chunks()`. Primeira ocorrência de cada `session_id` vira chunk canônico; ocorrências subsequentes são puladas com counter.

**Por que NÃO as outras opções:**

| Opção | Por que rejeitada |
|---|---|
| A. Composite key `f"{qid}::{sid}::{turn_idx}"` | **Quebra gold matching** — `select_queries()` constrói `gold_chunk_ids = [f"{qid}::{sid}" for sid in gold_set]` (linha 441). Mudar formato do chunk_id sem mudar a fórmula gold deixaria recall=0 em todas queries. Mudar AMBOS exigiria duplicar gold por turn_idx (que não existe no dataset). |
| B. `INSERT OR IGNORE` no executemany | Funciona mas **silencia o sinal**. Se um dia colidir por bug real (cross-question chunk_id leak), o teste passa silencioso. Dedup explícito loga warning. |
| D. `ON CONFLICT REPLACE` | Mesmo defeito que B + risco de overwrite com text vazio se o duplicato for malformado. |
| **C. Dedup em Python (escolhida)** | Explícito, logado, preserva primeiro-ganha (canônico), zero impacto em gold matching, zero risco de mascarar bug real. Counter no log distingue "esperado em s_cleaned" de "bug se aparecer em oracle". |

**Lógica preserved:**
- Gold matching: `f"{qid}::{sid}"` permanece intacto. `gold_chunk_ids` em `select_queries()` continua mapeando corretamente porque set-based.
- Per-question scoping: query path em `search_fts5()` / `load_question_dense()` filtra por `question_id = ?` (não muda).
- `is_answer_session` flag: marcado na primeira ocorrência (a canônica).

## Smoke tests (locais, pré-push)

Rodados em `paper/publication/baselines/` com corpus sintético antes do commit:

1. **Synthetic dup case** — 1 question, 5 sids com 2 duplicatas → `iter_session_chunks` emite 3 chunks únicos, `build_index` retorna 3 sem crash, warning logado em stderr.
2. **No-dup regression** — corpus oracle-shape (sem duplicatas) → comportamento idêntico ao pré-fix, zero chunks pulados, zero warning.
3. **Cross-question + intra-question mix** — 2 questions com `s_A` em ambas + dup intra-question em q1 → 4 chunks (`q1::s_A`, `q1::s_B`, `q2::s_A`, `q2::s_C`), FTS5 search isolado por `question_id` (q1 query não vê q2 chunks, gold matching intacto).

Output de exemplo:
```
[chunks] deduped 1 duplicate session_id entries across 1 questions (expected on s_cleaned/m_cleaned)
[index] 4 session-chunks in /tmp/.../test.db
build_index: 4 chunks (expected 4: q1 2 unique + q2 2)
PASS: FTS5 scoped search + per-question isolation + gold matching all intact
```

## Re-run na VPS (concrete commands)

```bash
# 1. Pull fix
ssh root@VPS
cd /root/.openclaw/workspace/tools/memoria-nox
git fetch origin
git checkout q-runs/2026-05-18/q2-scleaned-fix  # or main após merge

# 2. Garantir env (rule #1 do CLAUDE.md memoria-nox)
set -a; source /root/.openclaw/.env; set +a

# 3. Limpar cache do split anterior (DB schema é split-scoped, mas /tmp limpo é seguro)
rm -f /tmp/longmemeval-hybrid-eval-s_cleaned.db
# Manter /tmp/longmemeval-s_cleaned.json se já baixado (277MB) — script detecta cached

# 4. Rodar dentro de tmux (memória — long batches: rule MEMORY.md)
tmux new-session -d -s q2-scleaned "cd paper/publication/baselines &&   python3 longmemeval_hybrid_eval.py full --split s_cleaned 2>&1 |   tee /tmp/q2-scleaned-run-$(date +%Y%m%d-%H%M).log"

# 5. Monitor
tmux attach -t q2-scleaned   # Ctrl+B D pra detach
# OR
tail -f /tmp/q2-scleaned-run-*.log
```

## Output esperado

- **Wall clock:** ~10-15 min (n=100 queries × 2 API calls cada + per-question dense index build).
- **Custo Gemini:** ~\$0.05-0.20 (depende de quantos chunks haystack únicos no n=100 amostrado — estimativa do header do script).
- **Artefatos:**
  - `paper/publication/results/longmemeval-hybrid-results-s_cleaned.jsonl` (per-query metrics)
  - `paper/publication/results/longmemeval-hybrid-summary-s_cleaned.md` (aggregate + per-category breakdown)
- **Métricas esperadas (vs oracle saturado em 1.0):** nDCG@10 sub-1.0 com spread real entre categorias. multi-session e temporal-reasoning devem ser mais difíceis que single-session-*. Estes são os **números publicáveis** pro headline.
- **Stderr warning esperado:** linha `[chunks] deduped N duplicate session_id entries across M questions` — confirma que o fix está ativo. N é o sinal: se N=0 em s_cleaned, algo está estranho no shape do dataset.

## Validação pós-run

1. Conferir `aggregate.n_queries == 100` no `longmemeval-hybrid-summary-s_cleaned.md`.
2. Conferir distribuição por categoria: cada uma das 6 base categories deve ter 16-17 questions (16 + 4 extras round-robin).
3. Spread realista: pelo menos uma categoria deve ter nDCG@10 < 1.0 (se ainda saturar em 1.0 com s_cleaned, root cause é outro — provavelmente bug na seleção do haystack scope).
4. Cross-check com Q1 LoCoMo numbers (`paper/publication/results/locomo-hybrid-summary.md`) — devem ser apples-to-apples comparáveis em magnitude.

## Não é responsabilidade desta PR

- Trigger remoto na VPS — main thread / próxima sessão.
- Update do COMPARISON.md com números s_cleaned — depois do run completar.
- Comparação com baselines BM25/E5 em s_cleaned — separate work item.
