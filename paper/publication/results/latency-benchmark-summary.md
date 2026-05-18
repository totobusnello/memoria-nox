# Q3 latency benchmark — pendente execução na VPS

**Status:** harness + queries prontos, **execução pendente** na VPS de produção.

**Por quê pendente:** o endpoint `/api/search` do nox-mem-api escuta em
`127.0.0.1:18802` (apenas loopback, por design). Como o agente que produziu
este PR não tem acesso SSH direto, a coleta de números reais precisa rodar
de dentro da VPS — ver instruções abaixo.

## Artefatos prontos

| Arquivo | Conteúdo |
|---|---|
| `paper/publication/baselines/latency_benchmark.py` | Harness Python stdlib + `requests`, 337 linhas, self-contained |
| `paper/publication/data/latency-queries-100.jsonl` | 100 queries reais nox-mem, 10 por categoria |
| `paper/publication/results/latency-benchmark-results.jsonl` | (gerado pela execução, ainda ausente) |
| `paper/publication/results/latency-benchmark-summary.json` | (gerado pela execução, ainda ausente) |

## Distribuição das 100 queries

| Categoria | n | Exemplos |
|---|---|---|
| `short` | 10 | "memoria", "salience", "RRF" |
| `entity` | 10 | "Toto Busnello", "Granix", "Nuvini" |
| `decision` | 10 | "qual modelo Gemini padrão", "BRL ou USD pricing" |
| `procedure` | 10 | "como aplicar migration", "como rotacionar Gemini key" |
| `incident` | 10 | "graph-memory parse failure 19.7", "sed corrompeu nox-mem.db" |
| `architecture` | 10 | "schema v22 confidence", "FTS5 BM25 RRF fusion" |
| `temporal` | 10 | "incidents 2026-05", "wave B 2026-05-18 delivered" |
| `conceptual` | 10 | "shadow mode", "withOpAudit", "vendor lock-in autonomy" |
| `long` | 10 | NL completa, 15-25 palavras |
| `code` | 10 | `ingestFile()`, `/api/health`, `src/lib/op-audit.ts` |

## Como executar (na VPS)

```bash
# 1. SSH no host
ssh root@<vps>

# 2. Pull do repo (assume worktree limpo em /root/Claude/Projetos/memoria-nox)
cd /root/Claude/Projetos/memoria-nox
git fetch origin
git checkout q-runs/2026-05-18/latency-benchmark

# 3. Carrega env (regra crítica do CLAUDE.md)
set -a; source /root/.openclaw/.env; set +a

# 4. Garante requests instalado
python3 -m pip install --user requests

# 5. Executa (warmup=5 descarta primeiras 5 queries do summary)
python3 paper/publication/baselines/latency_benchmark.py \
  --queries paper/publication/data/latency-queries-100.jsonl \
  --endpoint "http://127.0.0.1:${NOX_API_PORT:-18802}/api/search" \
  --output paper/publication/results/latency-benchmark-results.jsonl \
  --summary paper/publication/results/latency-benchmark-summary.json \
  --warmup 5 --limit 10

# 6. Commit dos resultados
git add paper/publication/results/latency-benchmark-results.jsonl \
        paper/publication/results/latency-benchmark-summary.json
git commit -m "eval(q3): latency benchmark — resultados de produção VPS"
git push
```

## Alternativa — SSH tunnel a partir do laptop

```bash
# Terminal 1
ssh -L 18802:127.0.0.1:18802 root@<vps>

# Terminal 2 (laptop)
NOX_API_ENDPOINT=http://127.0.0.1:18802/api/search \
  python3 paper/publication/baselines/latency_benchmark.py
```

## Métricas alvo (Q3 acceptance)

A coleta deve preencher esta tabela com números reais:

| Métrica | Alvo razoável | Observado |
|---|---|---|
| `p50_ms` (aggregate) | < 200 ms | pendente |
| `p95_ms` (aggregate) | < 800 ms | pendente |
| `p99_ms` (aggregate) | < 1500 ms | pendente |
| `errors` | 0 | pendente |
| `p95_ms` (`short` cat) | < 150 ms | pendente |
| `p95_ms` (`long` cat) | < 1000 ms | pendente |

Alvos preliminares; revisar após primeira coleta com base no perfil real do
sistema (FTS5 + sqlite-vec + Gemini embedding cache).

## Notas metodológicas

- **Wall-clock via `time.perf_counter()`** cobre o ciclo completo (TCP + server
  + body). Em loopback, overhead de rede é sub-ms, então é proxy fiel do
  server-side.
- **Serial, concorrência 1** — perfil realista pra single-agent hoje. Subir
  concorrência testaria cenário fora do escopo Q3.
- **Percentis nearest-rank** (NIST) — apropriado para n=100.
- **Warmup recomendado:** 5 queries (descarta cache cold do `vec_chunks` mmap
  + embedding cache do Gemini).
- **No retry, no backoff** — quero ver falha real; retry mascararia transient
  errors do upstream Gemini quando o cache miss.

## Próximos passos

1. Trigger manual na VPS (instruções acima).
2. Commit dos `*.jsonl` + `*.json` no mesmo branch.
3. Atualizar este `.md` com os números reais + interpretação.
4. Linkar do paper sec 4 (latency results) quando p50/p95/p99 estiverem
   confirmados.

---

*Gerado por agente Q3 em 2026-05-18. Branch: `q-runs/2026-05-18/latency-benchmark`.*
