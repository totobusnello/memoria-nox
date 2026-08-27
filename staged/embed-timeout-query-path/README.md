# staged/embed-timeout-query-path

> **A busca não falha — ela espera.** O caminho semantic degrada pra FTS quando o Gemini dá **erro**, mas o `await embedText(query)` não tem orçamento de tempo, e por baixo dele há uma escada de 4 tentativas com backoff de 1s/2s/4s. Provider lento não vira fallback: vira uma query de 18s que ainda responde `has_semantic=1`.

Patch: `edits/src/embed.patch.md` (3 blocos, só o caminho de query).

## De onde veio

Canário das 14:52 de 2026-08-19: `nox-mem canary: /api/search unreachable on port 18802 (2x consecutivo)`. Não havia queda — serviço up desde 06:56, porta bound, `/api/health` em 0,698s, `/api/search` em 0,857s na triagem. O que havia era latência:

| Medida | Valor |
|---|---|
| `searchTelemetry.p95_latency_ms` (24h) | **18.231** |
| queries > 15s (timeout do canário) | 6 de ~40 (~15%) |
| `has_semantic` nas linhas lentas | **1** — completaram, só demoraram |
| `semantic_ratio` (24h) | 1,0 — o fallback nunca disparou |
| expansão | pulada em 49/49 (`too_short`) — não é ela |

Com ~15% das rodadas passando de 15s, duas falhas consecutivas de canário a cada 30 min era questão de tempo. **O alerta é a cauda de uma distribuição ruim, não um evento.**

## O mecanismo

```
search.ts:488   const queryEmbedding = await embedText(query);
                  └─ embed.ts  embedText → geminiEmbedQuery
                       └─ fetchWithRetry(url, init, "embedQuery")   ← maxAttempts = 4
                            └─ fetch(url, init)                     ← sem signal
```

Três camadas sem orçamento, uma dentro da outra:

1. **`fetch` sem `signal`.** Teto é o default do undici (~300s de headers/body), 20× o timeout do canário.
2. **`fetchWithRetry` com `maxAttempts = 4`** e backoff 1s → 2s → 4s. Numa query interativa isso não é resiliência, é acúmulo: **7s de backoff puro + 4 durações de request**. Um provider a 3s por chamada produz ~19s — precisamente a faixa das linhas de 15–24s.
3. **`searchSemantic` (`search.ts:573`) só cai pra FTS em `catch`.** Como a escada eventualmente *sucede*, o `catch` não roda, o fallback não acontece, e o resultado sai correto e lentíssimo — com `has_semantic=1`, que é como isto passou meses invisível.

Isso deixa a Tier 1 do RB-05 pela metade: *"`src/search.ts` já tem fallback FTS-only quando Gemini API falha"* — para **falha**, sim; para **lentidão**, não.

## O fix

Orçamento explícito no caminho de query (`2500ms`, 1 tentativa, ambos por env), abort terminal em vez de escada, e o `catch` do `searchSemantic` — que já existe e já faz a coisa certa — passa a ser alcançável. Ingest e vectorize ficam intocados: lá esperar e repetir é correto.

Detalhe que vale por si: hoje `recordProviderCost` só grava **depois** que existe `resp`. Fetch que lança (abort, socket, DNS) não deixa linha nenhuma, então a média de `embed.embedQuery` no `provider_cost` **exclui justamente as piores chamadas**. O patch grava `ok=0` no abort.

## ⚠️ O que este patch NÃO prova

Ele conserta um defeito real e verificável por leitura de código. Ele **não está estabelecido como a causa do p95 de 18s** — para isso falta a distribuição por chamada:

```bash
sqlite3 -header -column nox-mem.db \
  "SELECT ts, latency_ms, ok, caller FROM provider_cost
   WHERE caller LIKE 'embed.embedQuery%' ORDER BY rowid DESC LIMIT 40;"
```

- `embedQuery` acompanhando as buscas (2s–24s) ⇒ é este caminho, e o patch resolve.
- `embedQuery` estável em ~1,5s enquanto o search vai a 18s ⇒ o tempo está **depois** do embedding, e o patch apenas impede que a lentidão se disfarce de "unreachable". Os suspeitos, todos encontrados lendo `embed.ts`, viram a próxima investigação:

| Suspeito | Onde | Por que é candidato |
|---|---|---|
| KNN linear do `sqlite-vec` | `semanticSearch` — `WHERE embedding MATCH ? AND k = ?` | 67.024 × 3072 × 4B ≈ **823 MB varridos por query**; `k` não reduz o scan, e o custo cresce com o corpus |
| DDL por requisição | `ensureVecTable()` roda `CREATE VIRTUAL TABLE IF NOT EXISTS` + `CREATE TRIGGER IF NOT EXISTS` **a cada busca** | não é grátis, e nada muda entre queries |
| `loadExtension` repetido | `loadVecSafe()` em `ensureVecTable`, `countEmbedded` e `semanticSearch` | ~3 carregamentos de extensão por query |
| `COUNT(*)` por requisição | `countEmbedded()` sobre `vec_chunk_map` (67k linhas) | roda antes de toda busca só pra testar `=== 0` |

A variância de 20× (1,3s → 24s) com a mesma query voltando em 852ms logo depois favorece cache de página — o que aponta mais pro scan do que pro provider. **Medir antes de mexer.**

### O vizinho de disco, que não é do nox-mem mas disputa a mesma RAM

Medição da sessão `openclaw-vps-de` na mesma KVM (2026-08-19): o `openclaw-agent.sqlite` do agente `main` tem **896 MB**, sendo 446 MB de `memory_embedding_cache` + 338 MB de `memory_index_chunks` — vetores gravados como `embedding TEXT` (JSON: 66 KB onde caberiam 12 KB) num cache que nunca evicta (`pruneEmbeddingCacheIfNeeded()` existe mas é inalcançável; openclaw/openclaw#131089).

Essas tabelas **não são do nox-mem** — schema do OpenClaw, DB diferente. Mas moram no mesmo disco e disputam o mesmo page cache que os ~823 MB de vetores do `vec_chunks`. Se a hipótese do scan se confirmar, a pergunta seguinte não é "por que o scan é lento" e sim "por que ele não fica em cache" — e 896 MB de vizinho passando por ali é candidato direto. `free -m` + o tamanho dos dois DBs decidem.

⚠️ **Não rodar `ANALYZE` como tentativa de cura.** A mesma sessão testou: `sqlite_stat1` estava vazio nos 13 DBs, rodou `ANALYZE` em todos, e o tempo **piorou** (55.933ms → 65.415ms). Hipótese refutada com medição, não confirmada.

## Referências

- `docs/INCIDENTS.md#2026-08-19-1452` — a entrada deste incident
- `docs/RUNBOOKS.md` RB-05 §Mitigação Tier 1 — a promessa de fallback que este patch torna verdadeira
- `staged/health-probe-restart-loop/` — PR #452, defeito irmão: *reiniciar sem critério*; aqui é *esperar sem limite*
- `CLAUDE.md` — lição de sábado: op bloqueante precisa de wrapper de timeout explícito
