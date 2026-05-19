# nox-mem hooks — Auto-capture (P2)

> **Status:** staged — T1-T15 implementation under `staged-P2/`.
> **Spec:** [`specs/2026-05-18-P2-implementation-kickoff.md`](../../specs/2026-05-18-P2-implementation-kickoff.md).
> **Tagline:** *Pain-weighted hybrid memory with shadow discipline — yours by design.*

P2 entrega o lado **escrita** do trio Q/A/P. O sistema observa eventos
de conversa (turns de user/assistant) emitidos pelo OpenClaw (e
opcionalmente CLI/MCP/HTTP), passa cada um por uma pipeline de **5
camadas de privacidade** e, sobrevivendo, persiste no nox-mem com
`provenance=hook`.

A premissa é simples: você **opt-in** com `NOX_HOOKS_ENABLED=1`, e
nada captura sem antes passar por (1) gate de env, (2) allowlist de
fonte, (3) filtro de PII (staged-A1), (4) classificador de conteúdo
e (5) rate-limit + dedup. Cada camada **pode** bloquear o evento
sozinha; a ordem das camadas é **load-bearing** e nunca deve ser
trocada.

---

## Sumário

1. [Visão geral](#visão-geral)
2. [Modelo de 5 camadas](#modelo-de-5-camadas)
3. [Configuração (env vars)](#configuração-env-vars)
4. [Instalação do plugin OpenClaw](#instalação-do-plugin-openclaw)
5. [Uso via CLI](#uso-via-cli)
6. [Uso via HTTP](#uso-via-http)
7. [Uso via MCP](#uso-via-mcp)
8. [Decoradores inline (override explícito)](#decoradores-inline-override-explícito)
9. [Schema de telemetria](#schema-de-telemetria)
10. [Threat model](#threat-model)
11. [FAQ](#faq)

---

## Visão geral

O fluxo end-to-end é:

```
turn ocorre no OpenClaw
       ↓
plugin nox-hooks (afterTurn)
       ↓ enqueue (não bloqueante)
worker queue (10k slots, drop-oldest se cheio)
       ↓ batch drain (250ms / 100 events)
pipeline 5 camadas
       ↓ Layer 1: env gate
       ↓ Layer 2: source allowlist (default: openclaw only)
       ↓ Layer 3: A1 privacy filter (PII redaction)
       ↓ Layer 4: content classifier (signal vs noise)
       ↓ Layer 5: rate-limit + cosine dedup
       ↓
ingestText(text=<redacted>, provenance="hook", ...)
       ↓
nox-mem.db (chunks + FTS5 + vec)
```

**Toda** decisão (passou ou bloqueou) gera UMA linha em `agent_events`
com `{layer, reason}` — **nunca** o conteúdo cru.

---

## Modelo de 5 camadas

### Layer 1 — Env gate

**Onde:** primeira coisa que o pipeline checa.
**Bloqueia se:** `NOX_HOOKS_ENABLED != "1"`.
**Razão:** ergonomia + segurança. Default OFF. Você liga conscientemente.

Toda telemetria carrega `reason=env_disabled` quando barrado aqui. Custo
≈ leitura de uma var de env; eventos rejeitados são essencialmente
gratuitos.

### Layer 2 — Source allowlist

**Onde:** depois do gate.
**Bloqueia se:** `event.source ∉ NOX_HOOK_SOURCES` **ou** `event.role ∉
{user, assistant}`.
**Razão:** atribuição explícita de canal. Eventos com `source=unknown`
**nunca** são aceitos, mesmo que você ponha "unknown" no allowlist. A
ideia é: se o emissor não declarou de onde veio, o evento não passa.

Valores válidos em `NOX_HOOK_SOURCES` (CSV): `openclaw, cli, manual,
mcp, api`. Default = `openclaw` (mais restrito).

Roles aceitos: `user`, `assistant`. `system`, `tool`, `unknown` são
sempre rejeitados — esses não são conversa humana.

### Layer 3 — A1 privacy filter (PII redaction)

**Onde:** depois da allowlist.
**O que faz:** chama `redact(text)` do pacote staged-A1 (13 patterns,
68 testes, FP rate 1.7% medido). Substitui matches por `<private>` e
incrementa `redaction_count`.

**Política:**
- `NOX_HOOK_PII_POLICY=redact` (default) — redacta e continua. O texto
  redacted é o que chega na L4/L5/persistência.
- `NOX_HOOK_PII_POLICY=drop` — se `redaction_count > 0`, descarta o
  evento inteiro. Útil quando você quer "se tem qualquer chance de PII,
  nem captura".

Se `redact()` lançar exceção, o pipeline **falha fechado** (descarta).

**Telemetria:** quando dispara redação, a linha em `agent_events` traz
`{redaction_count, kinds}` mas **nunca** o conteúdo.

### Layer 4 — Content classifier

**Onde:** depois da privacidade (porque você só quer classificar texto
já limpo).
**Heurísticas-first:**

| Sinal | Peso |
|---|---|
| `length ≥ NOX_HOOK_MIN_LENGTH` (default 20) | +0.25 |
| Não é pura URL (≥50% chars em URL → score capado em 0.1) | guard |
| Razão de tokens de código (`{};=<>()`) baixa (<8%) | +0.15 / −0.15 |
| Contém pista de noun-phrase (capitalizadas / conjunções comuns) | +0.20 |
| Contém terminador de frase (`. ! ?`) | +0.15 |
| Mistura maiúsculas+minúsculas | +0.10 |
| Não-puro-whitespace/punctuation | +0.15 |

**Decisão:**
- `score < 0.4` → reject (`classifier_low_signal`)
- `score > 0.6` → accept (`high_signal`)
- `0.4 .. 0.6` → ambíguo:
  - se `NOX_HOOK_LLM_CLASSIFY=1` → chama LLM fallback (flash-lite por padrão)
  - caso contrário → aceita (bias = recall > precision)

LLM fallback é **opt-in** porque acarreta custo + latência; padrão é
heurística pura.

### Layer 5 — Rate-limit + dedup

**Onde:** última camada antes da persistência.

**Rate-limit:** token bucket com capacidade `NOX_HOOK_RATE_LIMIT`
captures/min (default 30). Cada captura consome 1 token; bucket recarrega
proporcional ao tempo decorrido.

**Dedup:** ring buffer dos últimos 10 textos redacted. Se cosine(novo,
qualquer prévio) > `NOX_HOOK_DEDUP_THRESHOLD` (default 0.95), descarta.
Cosine usa char 3-shingle (cheap, sem dep de embedder de rede).

**Importante:** dedup hit **não** consome token de rate-limit. Senão
um loop barulhento gastaria toda a quota só com idênticos.

---

## Configuração (env vars)

Todas as vars têm default seguro (mais restrito ou OFF). Defaults:

| Var | Default | Range/valores válidos |
|---|---|---|
| `NOX_HOOKS_ENABLED` | `0` | `0` ou `1` |
| `NOX_HOOK_SOURCES` | `openclaw` | CSV de `openclaw, cli, manual, mcp, api` |
| `NOX_HOOK_RATE_LIMIT` | `30` | 1 .. 1000 (captures/min) |
| `NOX_HOOK_DEDUP_THRESHOLD` | `0.95` | 0.5 .. 0.999 |
| `NOX_HOOK_LLM_CLASSIFY` | `0` | `0` ou `1` |
| `NOX_HOOK_DRY_RUN` | `0` | `0` ou `1` |
| `NOX_HOOK_QUEUE_SIZE` | `10000` | 100 .. 1_000_000 |
| `NOX_HOOK_MIN_LENGTH` | `20` | chars |
| `NOX_HOOK_PII_POLICY` | `redact` | `redact` ou `drop` |

Coloque no `.env` do OpenClaw (veja
`~/Claude/Projetos/openclaw-vps/infra/CLAUDE.md` regra #1 sobre como
fontes carregam env). Validações inválidas caem em default
silenciosamente — sem crash, mas a config retornada por
`GET /api/hooks/status` mostra o valor real efetivo.

---

## Instalação do plugin OpenClaw

```bash
# 1) Build do staged
cd staged-P2
npm install
npm run build

# 2) Copie o plugin pra dir de plugins do OpenClaw
cp -r dist/src/plugins/nox-hooks ~/.openclaw/plugins/

# 3) Habilite no openclaw.json (via CLI canônica)
openclaw plugin add nox-hooks

# 4) Liga o switch
echo 'NOX_HOOKS_ENABLED=1' >> ~/.openclaw/.env
echo 'NOX_HOOK_SOURCES=openclaw' >> ~/.openclaw/.env

# 5) Restart gateway
systemctl restart openclaw-gateway

# 6) Confirma
curl -s http://127.0.0.1:18802/api/hooks/status | jq .config.enabled
# deve retornar: true
```

O plugin instala 3 handlers: `afterTurn`, `sessionStart`, `sessionEnd`.
**afterTurn** é o que faz o trabalho real — os outros dois mantêm
session_id e fecham worker no shutdown.

---

## Uso via CLI

```bash
# Status (config + queue depth)
nox-mem hooks status

# Últimas 20 capturas (só metadata, sem conteúdo)
nox-mem hooks recent 20

# Dry-run: roda texto pelas 5 camadas, mostra trace, não persiste
nox-mem hooks dryrun "exemplo de texto para testar o pipeline inteiro"

# Stats agregados 24h + 7d
nox-mem hooks stats
```

`dryrun` é a ferramenta principal de debug — você vê exatamente qual
camada bloquearia (ou aceitaria) o evento, sem mexer no DB.

---

## Uso via HTTP

```bash
# Status
curl -s http://127.0.0.1:18802/api/hooks/status | jq

# Recent (metadata only)
curl -s 'http://127.0.0.1:18802/api/hooks/recent?limit=10' | jq

# Dryrun
curl -s -X POST http://127.0.0.1:18802/api/hooks/dryrun \
  -H 'Content-Type: application/json' \
  -d '{"text": "texto de teste", "role": "user", "source": "api"}' | jq
```

---

## Uso via MCP

Os 4 tools expostos pelo servidor MCP do nox-mem:

| Tool | Input | Output |
|---|---|---|
| `nox_hooks_status` | `{}` | `{config, queueDepth, rateLimitTokens}` |
| `nox_hooks_recent` | `{limit?: int}` | `{rows: [...metadata]}` |
| `nox_hooks_dryrun` | `{text: string, role?, source?}` | `{result, trace}` |
| `nox_hooks_stats` | `{}` | `{last_24h, last_7d}` |

Os schemas JSON estão em `src/mcp/tools/hooks.ts` (`HOOK_TOOLS`
exportado). Clientes MCP (Claude Desktop, Claude Code) podem chamar
qualquer um sem ler o conteúdo dos eventos — apenas metadata.

---

## Decoradores inline (override explícito)

Você pode marcar um turn manualmente:

```
// @nox:capture
{ acima é low-signal mas força a captura assim mesmo }
```

```
// @nox:skip
qualquer coisa abaixo é ignorada pelo pipeline
```

Comentários reconhecidos: `//`, `/* */`, `#`, `<!-- -->`. Só são
detectados nas **primeiras 4 linhas** do conteúdo (para não escanear
transcripts gigantes).

**Precedência:** `skip` vence sobre `capture` (defensivo). `@nox:skip`
short-circuita já na camada Decorator — antes mesmo do env gate. Ou
seja, mesmo com `NOX_HOOKS_ENABLED=1`, um turn anotado com `skip` não
é capturado nem aparece em `recent` (mas aparece em telemetria com
`reason=explicit_skip`).

---

## Schema de telemetria

Tabela `agent_events` (v11 — já criada antes do P2 nas migrations do
core schema):

```sql
CREATE TABLE agent_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_uuid TEXT NOT NULL UNIQUE,                -- ULID
  session_id TEXT NOT NULL,
  project_slug TEXT NOT NULL,
  kind TEXT NOT NULL CHECK(kind IN (
    'tool_use', 'user_prompt', 'session_start',
    'session_end', 'pre_compact'
  )),
  timestamp TEXT NOT NULL,                        -- ISO 8601
  payload_json TEXT NOT NULL,                     -- {layer, reason}
  redaction_count INTEGER NOT NULL DEFAULT 0,
  retention_days INTEGER NOT NULL DEFAULT 30
);
```

**Cada** chamada ao pipeline (captura OU rejeição) emite **uma** linha.
`payload_json` é estritamente `{"layer": "<nome>", "reason": "<curto>"}`
— **nunca** conteúdo. Validação automática:

```bash
sqlite3 nox-mem.db "
  SELECT payload_json
  FROM agent_events
  WHERE payload_json LIKE '%senha%'
     OR payload_json LIKE '%password%';
"
# deve retornar zero linhas — invariante de privacidade
```

Retention 30d padrão (consistente com regra geral nox-mem para eventos
não-cristalizados).

---

## Threat model

### Vetores cobertos

| Vetor | Defesa |
|---|---|
| **Vazamento de PII em chunks** | L3 redact (A1, 13 patterns, 1.7% FP) + L3 política `drop` opcional + telemetria sem conteúdo |
| **Source spoofing** | L2 rejeita `unknown` sempre + allowlist opt-in explícita |
| **Captura indevida de system/tool roles** | L2 filtra roles |
| **Inundação de eventos** | L5 rate-limit (token bucket) + L9 worker queue drop-oldest |
| **Captura de loops barulhentos (mesma msg N×)** | L5 cosine dedup ring buffer (não consome token) |
| **Telemetria virando vazamento secundário** | `payload_json` restrito a `{layer, reason}`; testes asseguram `redaction_count` em vez de conteúdo |
| **Pipeline crashando o host** | exceptions em telemetry/ingest engolidas; worker errors contadas mas não propagadas; plugin nunca throws em afterTurn |
| **Bypass via decorador malicioso em conteúdo do usuário** | `@nox:capture` só pula L4, não L1/L2/L3/L5; PII ainda redactada; rate-limit ainda aplica |

### Vetores **NÃO** cobertos (assumidos no escopo do A1, A2 ou roadmap)

- **PII fora dos 13 patterns da A1** — você adiciona ao staged-A1 (não
  ao P2). Lá tem teste-driven addition.
- **Reidentificação por agregação** — múltiplos chunks redacted juntos
  podem voltar a expor identidade. Mitigação: política `drop` se você é
  paranóico.
- **MITM em transporte ingest** — assumimos comm local (loopback) ou
  TLS upstream. Não há crypto neste módulo.
- **Tampering no DB pós-write** — ops_audit + WAL safe restore cobrem
  isso no `src/lib/op-audit.ts` (fora do P2).

---

## FAQ

**Por que default OFF?**
Defesa em camadas começa por consentimento. Você liga quando entendeu.

**Por que ordenar as camadas exatamente assim?**
Cada camada protege a seguinte de fazer trabalho caro/perigoso:
- L1 evita TODO o trabalho se o sistema está desligado.
- L2 evita aplicar regex de redação em eventos de fonte não confiável.
- L3 evita persistir conteúdo cru com PII.
- L4 evita gastar quota com lixo.
- L5 evita o storm de duplicatas.

Reordenar quebra essas garantias. Treat the order as invariante.

**O classificador pode usar LLM em vez de heurística?**
Sim, mas só na faixa ambígua (0.4..0.6) e com `NOX_HOOK_LLM_CLASSIFY=1`.
Default é heurística pura porque é grátis e suficiente em maioria dos
casos. O LLM (flash-lite por D41 #1) entra como tie-breaker, não como
classificador primário.

**Posso ver o que foi capturado?**
Sim — `nox-mem hooks recent`, `/api/hooks/recent`, ou direto na tabela
`chunks` filtrando por `provenance='hook'`. O conteúdo aí é já o
redacted; o original cru **nunca** é persistido.

**E se eu quiser DROP em PII em vez de redact?**
Set `NOX_HOOK_PII_POLICY=drop`. Eventos com qualquer match de A1 são
descartados inteiros, com `reason=pii_detected_skip` na telemetria.

**Funciona offline?**
Heurística sim (default). LLM fallback precisa de Gemini ativo. Dedup
não depende de embedder de rede (usa cosine local de char-shingle).

**Como debugo se está capturando demais / de menos?**
Sequência:
1. `nox-mem hooks status` — confirma config efetiva
2. `nox-mem hooks dryrun "<texto exemplo>"` — vê o trace camada-a-camada
3. `nox-mem hooks stats` — checa `by_reason` agregado 24h
4. `sqlite3 nox-mem.db "SELECT payload_json, COUNT(*) FROM agent_events
   WHERE timestamp > datetime('now','-24 hours') GROUP BY 1;"` — distribuição
   de razões reais

**Por que o worker é assíncrono em vez de processar in-line no afterTurn?**
Porque `afterTurn` do OpenClaw é síncrono e bloqueia o turn. Se o
pipeline gastar 50ms por evento, o usuário sente. Worker async = enqueue
em <1ms, drain em background. O custo é: eventos perdidos se o processo
crashar antes de drain (mitigação: `sessionEnd` chama `worker.stop()`
que faz drain final).

**Posso ter capacity por sessão em vez de global?**
Hoje não. `NOX_HOOK_RATE_LIMIT` é global por processo. Se você precisa
isolar projetos, rode múltiplas instâncias do worker (uma por
project_slug) — o pipeline em si é stateless modulo o RateLimitState que
você thread.

**Como expirar capturas antigas?**
`retention_days` na linha de `agent_events` (default 30d). O cron de
retention do nox-mem já varre e cleanup (out of scope deste módulo, mas
documentado em `docs/CONVENTIONS.md §cron`).

---

**End of HOOKS.md** — qualquer dúvida específica de implementação:
ler o spec (`specs/2026-05-17-P2-hooks-autocapture.md`) e o kickoff
(`specs/2026-05-18-P2-implementation-kickoff.md`).
