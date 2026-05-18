# AUTH-MODEL.md — nox-mem-api Authentication & Access Control

> **Ref:** THREAT-MODEL.md §3.3, G6 (default-allow auth review).
> **Status:** Implemented — Wave F, 2026-05-18.
> **Idioma:** EN para termos técnicos; narrativa PT-BR (São Paulo register).

---

## 1. Filosofia: localhost-default

O `nox-mem-api` escuta na porta `18802` na interface `127.0.0.1` por padrão.
Isso significa que **apenas processos no mesmo host** conseguem fazer requests —
a principal linha de defesa é o isolamento de rede, não autenticação por token.

Esta escolha é intencional:

- **Data autonomy:** o dado fica na sua VPS, sem tráfego externo.
- **Superfície de ataque reduzida:** sem binding em `0.0.0.0`, atacantes
  externos não chegam nem a negociar TCP.
- **Simplicidade operacional:** sem PKI, sem certificate rotation.

A desvantagem: qualquer processo local pode acessar a API sem autenticação.
Para VPS single-user (modelo atual), isso é aceitável.

---

## 2. Variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `NOX_API_BIND_HOST` | `127.0.0.1` | Interface de bind do servidor HTTP. Mudar pra `0.0.0.0` expõe externamente. |
| `NOX_API_PORT` | `18802` | Porta. Nunca hardcode — ler sempre do `.env`. |
| `NOX_API_BEARER_TOKEN` | _(não set)_ | Token Bearer para acesso remoto. Requerido se `NOX_API_BIND_HOST != 127.0.0.1`. |
| `NOX_API_ALLOW_PUBLIC` | _(não set)_ | Se `1`, suprime o warning de binding público sem token. Usar SÓ com documentação clara do risco. |

### Configuração em `/root/.openclaw/.env`

```env
# Binding — padrão seguro
NOX_API_BIND_HOST=127.0.0.1
NOX_API_PORT=18802

# Token (só se precisar de acesso remoto)
# NOX_API_BEARER_TOKEN=<gere com: openssl rand -hex 32>
```

---

## 3. Middleware: `requireLocalhost`

Implementado em `src/lib/auth/localhost-guard.ts`.

### Lógica

```
request chega
  ↓
extractClientIp(req) → IP do socket (não X-Forwarded-For)
  ↓
isLocalhostIp(ip)?
  → SIM → allow (return false)
  → NÃO → NOX_API_BEARER_TOKEN configurado?
              → SIM → token válido no Authorization: Bearer?
                          → SIM → allow (return false)
                          → NÃO → 403 forbidden
              → NÃO → 403 forbidden (localhost-only mode)
```

### Por que socket IP e não X-Forwarded-For?

`X-Forwarded-For` pode ser forjado pelo cliente. Se um reverse proxy na mesma
máquina encaminhar requests externos com `X-Forwarded-For: 127.0.0.1`, a
verificação seria bypassada. Usar `req.socket.remoteAddress` garante o IP
real da conexão TCP.

### Exceção: reverse proxy local

Se você usa nginx/caddy no mesmo host fazendo proxy para `:18802`, o IP do
socket será `127.0.0.1` mesmo para requests externos — isso quebra a proteção.
Nesse cenário, você **deve** configurar `NOX_API_BEARER_TOKEN` e validar o
token no reverse proxy ou usar a validação Bearer no handler.

---

## 4. Endpoints e cobertura de auth

| Endpoint | Método | Auth aplicada | Observações |
|---|---|---|---|
| `/api/health` | GET | `requireLocalhost` | Health probe; localhost-only. |
| `/api/search` | POST | `requireLocalhost` | Conteúdo sensível. |
| `/api/answer` | POST | `requireLocalhost` | LLM + chunk retrieval. |
| `/api/kg` | GET/POST | `requireLocalhost` | KG entities. |
| `/api/kg/path` | GET | `requireLocalhost` | KG relations path. |
| `/api/agents` | GET | `requireLocalhost` | Agent registry. |
| `/api/cross-kg` | POST | `requireLocalhost` | Cross-entity KG. |
| `/api/reflect` | POST | `requireLocalhost` | Salience reflect. |
| `/api/procedures` | GET | `requireLocalhost` | Procedure list. |
| `/api/crystallize` | POST | `requireLocalhost` | Destrutivo — requer localhost. |
| `/api/crystallize/validate` | POST | `requireLocalhost` | Preview dry-run. |
| `/api/chunk/:id/mark` | POST | `requireLocalhost` | Confidence mark. |

**Nenhum endpoint é público por design.** Todos requerem localhost ou Bearer.

---

## 5. Acesso remoto (opcional)

Se você precisar acessar a API de fora da VPS (ex: dashboard externo):

### 5.1 Via SSH tunnel (recomendado)

```bash
# No seu cliente local:
ssh -L 18802:127.0.0.1:18802 root@sua-vps.example.com

# Agora acesse localmente:
curl http://127.0.0.1:18802/api/health
```

Sem mudar nada na VPS, sem expor porta externamente. **Esta é a opção preferida.**

### 5.2 Via Bearer token (se SSH tunnel não for viável)

1. Gere um token forte:
   ```bash
   openssl rand -hex 32
   # exemplo de saída: <64-hex-chars>
   ```

2. Adicione no `.env`:
   ```env
   NOX_API_BIND_HOST=0.0.0.0
   NOX_API_BEARER_TOKEN=<token-gerado-acima>
   ```

3. Configure firewall para só aceitar requests da sua origem:
   ```bash
   ufw allow from <sua-ip> to any port 18802
   ufw deny 18802
   ```

4. Nos requests:
   ```bash
   curl -H "Authorization: Bearer <seu-token>" \
     http://sua-vps.example.com:18802/api/health
   ```

**Aviso:** sem TLS, o token trafega em claro. Use apenas em redes confiáveis
ou adicione um reverse proxy com HTTPS + certificado Let's Encrypt.

---

## 6. Token security

- **Geração:** `openssl rand -hex 32` (256 bits de entropia).
- **Armazenamento:** `.env` com `chmod 600`. Nunca em git.
- **Comparação:** `timingSafeEqual` via sha256 digest — sem timing attack.
- **Rotação:** trocar em `.env` e reiniciar `nox-mem-api`. Não há sessões persistentes.
- **Sem RBAC:** token único pra todos os endpoints. Se precisar RBAC,
  abrir issue pra Wave G (fora do escopo atual single-tenant).

---

## 7. Gaps residuais documentados

| Gap | Severidade | Status |
|---|---|---|
| Sem rate limit explícito em handlers | Médio | Aberto — G4 endereça top_k; rate limit global em roadmap Wave G |
| Sem TLS nativo | Médio | Mitigado via SSH tunnel; HTTPS via reverse proxy recomendado |
| Token único (sem RBAC) | Baixo | Aceitável em single-tenant; GTM multi-tenant requer revisão |
| Bearer token em X-Forwarded-For bypass se reverse proxy local | Médio | Documentado §3 acima; mitigado com nota explícita |

---

## 8. Verificação operacional

```bash
# 1. Confirmar bind em 127.0.0.1
ss -tlnp | grep 18802
# Esperado: 127.0.0.1:18802

# 2. Confirmar que request externo é negado (sem token)
curl -v http://0.0.0.0:18802/api/health 2>&1 | grep -E "< HTTP|forbidden"
# Esperado: 403 forbidden

# 3. Confirmar que localhost funciona
curl http://127.0.0.1:18802/api/health | jq .status
# Esperado: "ok"

# 4. Se token configurado, testar Bearer
curl -H "Authorization: Bearer $NOX_API_BEARER_TOKEN" \
  http://127.0.0.1:18802/api/health | jq .status
```

---

*Maintainer: Toto Busnello. Próxima revisão: quando Wave B endpoints (P5/L2/P2) forem shipped.*
*Ref: THREAT-MODEL.md §7. Implementado em staged-G6/edits/src/lib/auth/localhost-guard.ts.*
