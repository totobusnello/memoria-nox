# CORS — Configuração e modelo de ameaça

> **Módulo:** `src/api/cors.ts`
> **Contexto:** nox-mem HTTP API (porta 18802)
> **Motivação:** Desbloqueia P7 browser extension (PR #96) — sem esse patch, o
> Chrome/Firefox bloqueia toda chamada da extensão para `http://127.0.0.1:18802`.

---

## O que este módulo resolve

A API do nox-mem roda em `http://127.0.0.1:18802`. A extensão de browser P7
(`staged-P7-browser-extension/`) precisa fazer chamadas XHR/fetch para essa URL.

Quando uma extensão de browser faz uma requisição cross-origin, o browser envia
automaticamente um cabeçalho `Origin: chrome-extension://<id>`. Se o servidor não
responder com o cabeçalho `Access-Control-Allow-Origin` correspondente, o browser
bloqueia a resposta — mesmo que o servidor já tenha processado a requisição.

Resultado sem esse patch:

```
Access to fetch at 'http://127.0.0.1:18802/api/health' from origin
'chrome-extension://abcde...' has been blocked by CORS policy:
No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

---

## Política de allowlist padrão

Por padrão, apenas extensões de browser são permitidas:

| Pattern | Formato | Exemplo |
|---|---|---|
| Chrome Extension | `chrome-extension://` + 32 chars `[a-z]` | `chrome-extension://abcdefghijklmnopqrstuvwxyzabcdef` |
| Firefox Extension | `moz-extension://` + UUID `[0-9a-f-]` | `moz-extension://12345678-1234-1234-1234-1234567890ab` |

**Não permitidos por padrão:**
- `https://localhost:*` — requer env opt-in
- `https://example.com` — requer env opt-in
- Qualquer outro origin — bloqueado

---

## Configuração via env

O operador pode adicionar origens extras via variável de ambiente no VPS:

```bash
# Em /root/.openclaw/.env
NOX_CORS_EXTRA_ORIGINS=https://localhost:\d+,https://seu-dominio.com
```

Formato: string de regex separadas por vírgula. Cada string é compilada como
`new RegExp(pattern)` em JavaScript.

Exemplos:

```bash
# Permitir qualquer porta localhost (desenvolvimento local)
NOX_CORS_EXTRA_ORIGINS=^https://localhost:\d+$

# Permitir um domínio específico (Tailscale ou VPN interna)
NOX_CORS_EXTRA_ORIGINS=^https://memoria\.nox\.internal$

# Múltiplas origens
NOX_CORS_EXTRA_ORIGINS=^https://localhost:\d+$,^https://memoria\.nox\.internal$
```

**Atenção:** Patterns inválidos geram `console.warn` e são ignorados silenciosamente —
o servidor não trava em caso de env mal formado.

Após editar `.env`, reiniciar a API:

```bash
systemctl restart nox-mem-api
```

---

## Cabeçalhos emitidos

Para origens na allowlist, o módulo emite:

```http
Access-Control-Allow-Origin: <origin>   ← echo do origin, nunca "*"
Vary: Origin
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
Access-Control-Max-Age: 86400
```

O cabeçalho `Access-Control-Allow-Credentials: true` só é emitido se você
chamar `applyCorsHeaders(req, res, { allowCredentials: true })` explicitamente.
Extensões P7 não precisam de credentials — não está habilitado no patch padrão.

---

## Fluxo de preflight (OPTIONS)

```
Browser (extensão)                    nox-mem API
──────────────────                    ───────────
OPTIONS /api/health HTTP/1.1 ──────►
  Origin: chrome-extension://abc...
  Access-Control-Request-Method: GET

                              ◄──────  HTTP/1.1 204 No Content
                                        Access-Control-Allow-Origin: chrome-extension://abc...
                                        Vary: Origin
                                        Access-Control-Allow-Methods: GET, POST, OPTIONS
                                        Access-Control-Allow-Headers: Content-Type, Authorization
                                        Access-Control-Max-Age: 86400

GET /api/health HTTP/1.1 ──────────►
  Origin: chrome-extension://abc...

                              ◄──────  HTTP/1.1 200 OK
                                        Access-Control-Allow-Origin: chrome-extension://abc...
                                        Vary: Origin
                                        Content-Type: application/json
                                        ...
```

---

## Modelo de ameaça

### O que os cabeçalhos CORS protegem

CORS é uma política do **browser** — não do servidor. O servidor ainda processa a
requisição. CORS protege contra:

- Páginas maliciosas lendo respostas de APIs privadas via XHR/fetch
- Cross-site request forgery em APIs que dependem de cookies de sessão

### O que CORS **não** protege

- Chamadas diretas via `curl`, Postman, scripts externos — esses não enviam `Origin`
- Ataques SSRF do lado servidor
- Acesso direto na mesma máquina (a API já fica em `127.0.0.1` = localhost-only)

### Por que **não** usar `Access-Control-Allow-Origin: *`

1. Permite que **qualquer** página web leia respostas da API se ela rodar num port forwarding
2. É incompatível com `Access-Control-Allow-Credentials: true`
3. Viola o princípio de menor privilégio — a extensão sabe seu próprio ID

### Por que echo do origin + Vary: Origin

O header `Vary: Origin` informa proxies e CDNs que a resposta pode variar por origin.
Sem ele, um proxy poderia cachear uma resposta com `Allow-Origin: chrome-extension://A`
e servir para a extensão B, que então receberia o cabeçalho errado e seria bloqueada.

### Regex strictness

Os patterns default são **anchored** (`^` e `$`):

```
/^chrome-extension:\/\/[a-z]{32}$/
```

Sem âncoras, um origin como `chrome-extension://aaaa...aaaa.evil.com` poderia
passar. A versão ancorada garante que o origin é EXATAMENTE o formato esperado.

### IDs de extensão Chrome

IDs do Chrome são derivados do hash da chave pública do pacote CRX. Na prática,
são sempre 32 letras minúsculas `[a-z]`. Dígitos não aparecem em IDs legítimos —
a regex usa `[a-z]` não `[a-z0-9]` propositalmente.

### Ports no localhost

A API escuta em `127.0.0.1:18802`. Extensões com `host_permissions` para
`http://127.0.0.1:18802/*` (como a P7) já têm permissão do browser para acessar
essa URL — o CORS é uma camada adicional de confirmação do servidor.

---

## API do módulo

```typescript
// Verifica se um origin está na allowlist
isOriginAllowed(origin: string, extraOrigins?: RegExp[]): boolean

// Aplica cabeçalhos CORS à resposta (no-op se origin não está na allowlist)
applyCorsHeaders(req, res, opts?: { extraOrigins?: RegExp[]; allowCredentials?: boolean }): void

// Trata requisição OPTIONS → 204 + headers, retorna true para short-circuit
// Retorna false se não é OPTIONS (caller continua roteamento normalmente)
handlePreflight(req, res, opts?: CorsOptions): boolean
```

---

## Integração em api-server.ts

Ver `staged-cors/edits/src/api-server.patch.md` para instruções de deploy.

Resumo do patch (3 linhas):

```typescript
import { applyCorsHeaders, handlePreflight } from "./api/cors.js";

async function handleRequest(req, res) {
  if (handlePreflight(req, res)) return;  // OPTIONS → 204, short-circuit
  applyCorsHeaders(req, res);             // demais métodos: injeta headers
  // ... routing existente ...
}
```

---

## Testes

```bash
# Na VPS, após deploy:
cd /root/.openclaw/workspace/tools/nox-mem

# Preflight Chrome
curl -si -X OPTIONS http://127.0.0.1:18802/api/health \
  -H "Origin: chrome-extension://abcdefghijklmnopqrstuvwxyzabcdef" \
  -H "Access-Control-Request-Method: GET"
# Esperado: 204 + Access-Control-Allow-Origin: chrome-extension://...

# Preflight Firefox
curl -si -X OPTIONS http://127.0.0.1:18802/api/health \
  -H "Origin: moz-extension://12345678-1234-1234-1234-1234567890ab" \
  -H "Access-Control-Request-Method: GET"
# Esperado: 204 + Access-Control-Allow-Origin: moz-extension://...

# GET com origin válido
curl -si http://127.0.0.1:18802/api/health \
  -H "Origin: chrome-extension://abcdefghijklmnopqrstuvwxyzabcdef"
# Esperado: 200 + Access-Control-Allow-Origin: chrome-extension://...

# Origin inválido — sem header CORS
curl -si http://127.0.0.1:18802/api/health \
  -H "Origin: https://evil.com" | grep -i access-control
# Esperado: sem output (nenhum header CORS)

# Unit tests
node --experimental-vm-modules src/api/__tests__/cors.test.ts
# Esperado: 18 testes passando
```

---

## Histórico

| Data | Mudança |
|---|---|
| 2026-05-18 | Módulo criado — Wave P, PR #97. Unblocks P7 (#96). |
