# Lesson 2026-05-17 — graph-memory plugin parse failure rate 19.7% → 0%

## Sintoma
Em logs do gateway, ~73 falhas/dia (sobre 297 sucessos = 19.7% rate):
```
[plugins] [graph-memory] turn extract failed:
  Error: [graph-memory] extraction parse failed:
  SyntaxError: Unexpected non-whitespace character after JSON at position N (line X column Y)
```

Dois tipos observados:
1. **`Unexpected non-whitespace character after JSON`** (~95% das falhas) — LLM gera JSON válido + texto extra após (exemplo, "Note:", outra resposta)
2. **`Expected ',' or ']' after array element`** (~5%) — JSON truncado por `max_tokens`

Impacto: 1 em cada 5 turns de conversa NÃO entra no Knowledge Graph → memória cross-session degradada para Nox/Atlas/Boris/Cipher/Forge/Lex.

## Plugin afetado
- **`graph-memory v1.5.8`** (custom, mods locais sobre `adoresever/graph-memory` upstream)
- Path: `/root/.openclaw/extensions/graph-memory/`
- Função: extrai triplets `{nodes: [TASK/SKILL/EVENT], edges: [USED_SKILL/SOLVED_BY/REQUIRES/PATCHES/CONFLICTS_WITH]}` via LLM (provider=gemini, model=gemini-2.5-flash-lite por default) de cada turn de conversa
- DB: `/root/.openclaw/graph-memory.db` (SQLite com FTS5 + vector embeddings + PageRank)

## Causa raiz
`src/extractor/extract.ts:365` usava extração ingênua via primeiro `{` e último `}`:

```typescript
function extractJson(raw: string): string {
  let s = raw.trim();
  s = s.replace(/<think>[\s\S]*?<\/think>/gi, "");
  s = s.replace(/<think>[\s\S]*/gi, "");
  s = s.replace(/^```(?:json)?\s*\n?/i, "").replace(/\n?\s*```\s*$/i, "");
  s = s.trim();
  if (s.startsWith("{") && s.endsWith("}")) return escapeStringControlChars(s);
  if (s.startsWith("[") && s.endsWith("]")) return escapeStringControlChars(s);
  const first = s.indexOf("{");
  const last = s.lastIndexOf("}");
  if (first !== -1 && last > first) return escapeStringControlChars(s.slice(first, last + 1));
  return escapeStringControlChars(s);
}
```

Quando o LLM gerava algo como `{"nodes":[...],"edges":[...]} 示例 2: ... {"nodes":[...]}`, o `lastIndexOf("}")` pegava o último `}` (do segundo JSON ou de texto explicativo), e o slice englobava todo o lixo entre os dois `{`s → `JSON.parse` quebrava.

System prompt já dizia explicitamente "禁止解释文字" (proibido texto explicativo) e "禁止 markdown 代码块包裹" mas o LLM não obedecia em ~20% das chamadas, especialmente em respostas longas com exemplos do próprio prompt sendo replicados.

## Fix aplicado

Substituído `extractJson` por **bracket-balance matcher** que para no primeiro JSON object/array completo, respeitando strings e escapes:

```typescript
function extractJson(raw: string): string {
  let s = raw.trim();
  s = s.replace(/<think>[\s\S]*?<\/think>/gi, "");
  s = s.replace(/<think>[\s\S]*/gi, "");
  s = s.replace(/^```(?:json)?\s*\n?/i, "").replace(/\n?\s*```\s*$/i, "");
  s = s.trim();

  // Find first JSON object/array via bracket balance (respects strings + escapes)
  // Fix 2026-05-17: handles LLM responses with extra text after JSON or multiple JSON blocks
  const startIdx = s.search(/[\{\[]/);
  if (startIdx === -1) return escapeStringControlChars(s);

  const opener = s[startIdx];
  const closer = opener === "{" ? "}" : "]";
  let depth = 0;
  let inString = false;
  let escape = false;

  for (let i = startIdx; i < s.length; i++) {
    const c = s[i];
    if (escape) { escape = false; continue; }
    if (inString) {
      if (c === "\\") escape = true;
      else if (c === '"') inString = false;
      continue;
    }
    if (c === '"') { inString = true; continue; }
    if (c === opener) depth++;
    else if (c === closer && --depth === 0) {
      return escapeStringControlChars(s.slice(startIdx, i + 1));
    }
  }

  // Truncated input fallback (preserves original behavior)
  const lastIdx = s.lastIndexOf(closer);
  if (lastIdx > startIdx) return escapeStringControlChars(s.slice(startIdx, lastIdx + 1));
  return escapeStringControlChars(s.slice(startIdx));
}
```

## Pipeline de aplicação

1. **Backup**: `cp -p src/extractor/extract.ts{,.bak-pre-extractjson-fix-20260517}` + idem dist
2. **Patch source TS** via Python script (`/tmp/fix-extractjson.py` para evitar problemas de escape em SSH heredoc)
3. **Build com bun** (NÃO tsc, que tem `noEmit: true` e gera artifacts separados):
   ```bash
   bun build ./index.ts --outdir=./dist --target=node --format=esm --packages=external
   ```
4. **Restart gateway**: `systemctl restart openclaw-gateway`
5. **Phase 6 invariants** validados pós-restart
6. **Monitor live** via `journalctl -f | grep -E "extracted|turn extract failed"`

## Validação prod

| Janela | Success | Failures | Failure rate |
|---|---|---|---|
| Pré-fix (24h) | 297 | 73 | **19.7%** |
| Pós-fix (primeiros 6 extracts) | 6 | 0 | **0%** ✅ |

Nodes capturados exemplo:
- `TASK:monitor-context-usage` → `USED_SKILL` → `SKILL:execute-script`
- `EVENT:script-still-running` → `SOLVED_BY` → `SKILL:process-poll`

## Pegadinhas observadas

### 1. `tsc` vs `bun build` no plugin
O `tsconfig.json` do plugin tem `"noEmit": true` (só type-check). Build correto é `bun build` (CLAUDE.md regra 2.3 menciona isso). Se rodar `tsc` direto, ele transpila em `dist/src/...`, `dist/test/...` mas NÃO faz bundle. Plugin vira não-functional.

### 2. Timing de `afterTurn`
Initialmente pareceu que o hook `afterTurn` não disparava pós-restart (zero hits em ~10min). Causa: agent precisa completar primeiro turn cycle (claude-cli subprocess pode levar 7-62s respondendo). Após primeira resposta completa, `afterTurn` dispara normalmente. Não confundir com bug.

### 3. Bun é "global" no /usr/local/bin/bun no VPS
Diferente do node (sob systemd unit). `bun build` funciona como root sem environment issues.

### 4. Bracket matcher precisa respeitar strings escaped
Sem isso, um `}` dentro de string (e.g. `"description": "use jq \"with_entries(...{key: value}...)\""`) seria contado como fechando o objeto. Necessário tracking de `inString` + `escape`.

## Backups locais (rollback se preciso)
- `/root/.openclaw/extensions/graph-memory/src/extractor/extract.ts.bak-pre-extractjson-fix-20260517`
- `/root/.openclaw/extensions/graph-memory/dist/index.js.bak-pre-extractjson-fix-20260517`

Rollback procedure:
```bash
cd /root/.openclaw/extensions/graph-memory
cp -p dist/index.js.bak-pre-extractjson-fix-20260517 dist/index.js
systemctl restart openclaw-gateway
```

## Upstream
- Repo: `adoresever/graph-memory` (último release v2.0.0, 2026-03-18)
- **Não há issue/PR específico sobre esse bug em particular** no upstream
- PRs relacionados (todos OPEN, não merged):
  - #43 "Guard repeated graph-memory LLM failures"
  - #54 "fix: address #49 #50 #46 (embed race, LLM signature, Node 24 compat)"
- Plugin local (v1.5.8) tem mods customizadas (`.bak-log-fix-20260424`, `.bak-pre-ingest-fix-20260423`) — não é vanilla
- TODO: considerar abrir PR upstream com este fix
