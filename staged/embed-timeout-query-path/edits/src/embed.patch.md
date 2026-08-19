# Integration patch — orçamento de tempo no embedding da query

**Target:** `/root/.openclaw/workspace/tools/nox-mem/src/embed.ts`
**Status:** ⏳ NÃO aplicado. Escrito contra o `embed.ts` lido em prod 2026-08-19.
**Não toca:** caminho de documento (`geminiEmbed`) nem de lote (`embedBatchAPI`) — lá retry generoso é correto.

---

## 1. Constantes (após `const API_BASE = ...`)

```diff
 const API_BASE = "https://generativelanguage.googleapis.com/v1beta";
+
+// Orçamento do caminho de QUERY. Uma busca interativa não pode pagar a escada
+// de 4 tentativas (1s+2s+4s de backoff + 4 durações de request ≈ 19s no pior
+// caso). `searchSemantic` já degrada pra FTS quando isto lança — que é a
+// resposta certa pra provider lento. Ingest/lote seguem com a política atual.
+const QUERY_EMBED_TIMEOUT_MS = Number(process.env.NOX_QUERY_EMBED_TIMEOUT_MS || 2500);
+const QUERY_EMBED_ATTEMPTS = Math.max(1, Number(process.env.NOX_QUERY_EMBED_ATTEMPTS || 1));
```

## 2. `fetchWithRetry` — timeout por tentativa (opt-in)

O default `perAttemptTimeoutMs = 0` preserva o comportamento atual byte a byte para
todos os callers existentes; só quem passa o parâmetro muda de regime.

```diff
 async function fetchWithRetry(
   url: string,
   init: RequestInit,
   label: string,
-  maxAttempts = 4
+  maxAttempts = 4,
+  perAttemptTimeoutMs = 0
 ): Promise<Response> {
   for (let attempt = 0; attempt < maxAttempts; attempt++) {
-    const resp = await fetch(url, init);
+    let resp: Response;
+    try {
+      resp = await fetch(
+        url,
+        perAttemptTimeoutMs > 0
+          ? { ...init, signal: AbortSignal.timeout(perAttemptTimeoutMs) }
+          : init
+      );
+    } catch (err) {
+      const name = (err as Error).name;
+      if (name === "TimeoutError" || name === "AbortError") {
+        // Orçamento gasto. Terminal de propósito: queimar a escada de backoff
+        // é o que transforma provider lento em request de 18s.
+        throw new Error(`[EMBED:${label}] aborted after ${perAttemptTimeoutMs}ms`);
+      }
+      throw err;
+    }
     if (resp.ok) return resp;
```

Resto da função inalterado.

## 3. `geminiEmbedQuery` — usar o orçamento e **contabilizar o abort**

Hoje `recordProviderCost` só roda depois que existe `resp`. Fetch que lança
(socket, DNS, abort) não grava linha nenhuma — a média de latência do
`embed.embedQuery` é enviesada por sobrevivência. Este bloco fecha isso.

```diff
-  const resp = await fetchWithRetry(url, {
-    method: "POST",
-    headers: { "Content-Type": "application/json" },
-    body: JSON.stringify({
-      model: `models/${EMBEDDING_MODEL}`,
-      content: { parts: [{ text: text.substring(0, 2048) }] },
-      taskType: "RETRIEVAL_QUERY",
-    }),
-  }, "embedQuery");
+  let resp: Response;
+  try {
+    resp = await fetchWithRetry(url, {
+      method: "POST",
+      headers: { "Content-Type": "application/json" },
+      body: JSON.stringify({
+        model: `models/${EMBEDDING_MODEL}`,
+        content: { parts: [{ text: text.substring(0, 2048) }] },
+        taskType: "RETRIEVAL_QUERY",
+      }),
+    }, "embedQuery", QUERY_EMBED_ATTEMPTS, QUERY_EMBED_TIMEOUT_MS);
+  } catch (err) {
+    // Abort/rede: sem resposta, mas com custo de tempo. Registrar para que o
+    // provider_cost pare de esconder exatamente as piores chamadas.
+    recordProviderCost({
+      provider: "gemini", model: EMBEDDING_MODEL, op_type: "embed",
+      tokens_in: estimateTokens(billed), tokens_src: "estimated",
+      latency_ms: Date.now() - t0, ok: false, caller: "embed.embedQuery",
+    });
+    throw err;
+  }
```

Resto da função inalterado (o bloco `if (!resp.ok)` e o sucesso já gravam custo).

---

## Efeito

| | antes | depois (default) |
|---|---|---|
| Pior caso do embedding da query | ~19s de escada + até ~300s por tentativa (teto do undici) | **2,5s**, depois FTS |
| Provider lento | busca pendura, `has_semantic=1` | busca responde em FTS-only |
| Abort/rede no `provider_cost` | não gravado | gravado com `ok=0` |
| Ingest / vectorize | 4 tentativas, 1s/2s/4s | **inalterado** |

**Trade-off explícito:** com `QUERY_EMBED_ATTEMPTS=1`, um 429 isolado degrada
*aquela* query para FTS em vez de esperar o backoff. No volume atual (49 queries/24h
contra um teto de 100/min) 429 na query é improvável, e esperar 7s para evitar um
resultado FTS é o negócio errado. Quem discordar: `NOX_QUERY_EMBED_ATTEMPTS=2`
(orçamento total 2,5s + 1s + 2,5s = 6s).

## Deploy

```bash
cd /root/.openclaw/workspace/tools/nox-mem
cp src/embed.ts src/embed.ts.bak-$(date +%F)
# aplicar os 3 blocos acima
npx tsc                      # NÃO `bun build` — este projeto compila com tsc
systemctl restart nox-mem-api && sleep 5
curl -s --noproxy '*' http://127.0.0.1:18802/api/health | jq .vectorCoverage
```

## Verificação

```bash
# 1) Busca normal continua semantic
curl -s --noproxy '*' -G http://127.0.0.1:18802/api/search \
  --data-urlencode 'q=como funciona a memoria persistente' --data-urlencode 'limit=5' \
  --data-urlencode 'track=false' | jq '[.[].match_type] | group_by(.) | map({(.[0]): length}) | add'

# 2) Forçar o orçamento a estourar: budget de 1ms ⇒ tem que cair pra FTS, não pendurar
NOX_QUERY_EMBED_TIMEOUT_MS=1 systemctl restart nox-mem-api   # ou drop-in temporário
# repetir a busca acima: match_type deve virar 100% "fts", em <2s
journalctl -u nox-mem-api -n 20 | grep -i "aborted after\|falling back to FTS"

# 3) Restaurar e conferir que o abort agora aparece na contabilidade
sqlite3 -header -column nox-mem.db \
  "SELECT ts, latency_ms, ok, caller FROM provider_cost WHERE caller='embed.embedQuery' ORDER BY rowid DESC LIMIT 10;"
```

## Rollback

```bash
cp src/embed.ts.bak-<data> src/embed.ts && npx tsc && systemctl restart nox-mem-api
```

Ou, sem rebuild: `NOX_QUERY_EMBED_TIMEOUT_MS=300000` restaura na prática o
comportamento antigo (o `perAttemptTimeoutMs=0` só existe para os outros callers).
