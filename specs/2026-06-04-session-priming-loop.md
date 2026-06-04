# PRD — Session Priming Loop (auto-recall + auto-ingest cross-agente)

**Status:** Proposto — aguardando review Toto
**Data:** 2026-06-04
**Origem:** conversa Toto × Forge × Claude sobre simbiose desperdiçada Cipher × nox-mem; ideia do Toto de auto-search no início de sessão para agentes e LLMs.
**Repos envolvidos:** `memoria-nox` (core), `openclaw-vps/infra` (plugin agentes), config local Mac (hooks Claude Code).

---

## 1. Visão

> **Toda sessão nasce contextualizada e morre contribuindo.**

Hoje o nox-mem só trabalha quando alguém lembra de perguntar. O Session Priming Loop fecha o ciclo:

1. **Priming (leitura):** ao iniciar sessão, agente/LLM recebe um *brief* compacto do conhecimento mais saliente pro seu escopo — sem precisar pedir.
2. **Consulta (mid-session):** tools `search`/`answer` disponíveis durante toda a sessão, com política de uso por intenção.
3. **Ingest (escrita):** ao encerrar, a sessão deposita digest tipado de volta — decaível por padrão, promovível por curadoria.

Cobertura: agentes OpenClaw na VPS (Atlas, Boris, Cipher, Forge, Lex), Claude Code no Mac do Toto, e qualquer cliente futuro via MCP/HTTP.

## 2. Problema

| Sintoma | Custo |
|---|---|
| Conhecimento existe mas não é consultado (chunks high-pain com access_count baixo) | Lições de incident re-aprendidas do zero |
| Cada sessão começa "fria" — agente re-descobre contexto que a memória já tem | Tokens + tempo + decisões repetidas (churn) |
| Escrita de volta é manual e inconsistente | Corpus envelhece; simbiose unidirecional |
| Claude Code no Mac não enxerga o que os agentes da VPS aprenderam (e vice-versa) | Conhecimento silado por máquina |

## 3. Relação com trabalho existente

| Artefato | Relação |
|---|---|
| **Spec P2 hooks-autocapture** (`2026-05-17-P2-hooks-autocapture.md`, Proposto, não implementado) | Este PRD **supersede a linha SessionStart** do P2 (que propunha `nox-mem search` top-K cego — rejeitado, ver §4.1). **Reaproveita**: endpoint `POST /api/ingest-event`, privacy layers (dependência A1), schema `agent_events`, contrato de hook scripts (shell + HTTP, timeouts curtos, fail-open). |
| **Plano Cipher × nox-mem** (memória `project-cipher-nox-mem-simbiose-plan-2026-06-04`) | Write-side do steward (formato 3-seções + routeIngest) é pré-requisito do Fluxo D para o Cipher. Item 4 do plano (access_count audit) vira métrica de sucesso deste PRD (§10). |
| **P1 `answer` primitive** (LIVE desde 2026-05-18, PR #114) | Consulta mid-session usa answer para síntese (§7 política). |
| **Salience formula** (Fase 1.7b-b, shadow-mode, `/api/health.salience`) | Motor de ranking do brief (§6). Primeira feature que consome salience como produto — promove de shadow para uso real. |

## 4. Princípios de design

### 4.1 Brief por salience, NÃO search cego
No SessionStart não existe pergunta. Search genérico ("projeto X") injeta chunks irrelevantes que poluem o contexto a sessão inteira. O primitivo correto é **ranking por salience** (`recency × pain × importance`) filtrado por escopo — "o que de mais importante este agente precisa saber agora", não "o que bate com esta string".

### 4.2 nox-mem = store canônico cross-agente/cross-máquina *(atualizado no review — ver §13)*
O Mac do Toto já injeta 3 memórias no startup (core-memory.json, claude-mem, `.remember/`). Decisão de review: nox-mem é o **store canônico de tudo**; as memórias locais viram feeders/caches (§13). A defesa contra redundância é **dedup no ingest**, não filtro por origem na leitura — o brief serve o escopo do projeto inteiro.

### 4.3 Pointer pattern — digest compacto, detalhe sob demanda
O brief injeta **ponteiros** (id + título + 1 linha), não chunks completos. Budget default ≤ ~1.200 tokens. O agente que quiser detalhe puxa via `search`/`get` mid-session. Contexto inicial barato; profundidade opt-in.

### 4.4 Ingest decaível por padrão, promovível por curadoria
Auto-ingest de toda sessão infla o corpus. Digests entram com `retention_days` tipo `daily` (90d, decai sozinho). O `crystallize` nightly promove só o que sobrevive a curadoria. Ingerir bruto é barato; promover é curado.

### 4.5 Fail-open sempre
Hook/plugin que não consegue falar com a API **não bloqueia a sessão**. Timeout curto (≤ 1s no priming), erro silencioso com log local. Memória é aceleradora, nunca dependência dura.

## 5. O que teremos — 4 componentes

| # | Componente | Repo | Descrição |
|---|---|---|---|
| **C1** | `GET /api/brief` | memoria-nox | Endpoint de priming: top-N por salience filtrado por escopo, formato digest compacto. **Destrava todos os outros.** |
| **C2** | MCP remote no Claude Code (Mac) | config local | Registra MCP server do nox-mem via Tailscale → tools `nox_mem_search`/`answer` disponíveis mid-session no Mac. |
| **C3** | Plugin bootstrap OpenClaw | openclaw-vps/infra | No início de sessão de cada agente, injeta brief no system context. `register()` idempotente (gateway re-invoca 3-7×/min). |
| **C4** | Hooks SessionStart/Stop no Mac | config local (`settings.json`) | SessionStart → chama `/api/brief` via Tailscale, injeta como additionalContext. Stop → POST digest (reaproveita `.remember/now.md`) pro ingest. |

## 6. Contrato C1 — `GET /api/brief`

### Request
```
GET /api/brief?scope=<string>&n=<int>&format=<json|text>&since=<dur>
```

| Param | Default | Semântica |
|---|---|---|
| `scope` | obrigatório | Filtro de escopo: slug de agente (`cipher`, `forge`...), projeto (`memoria-nox`) ou `global`. Mapeia para filtro em `source`/`agent_id`/tags — detalhe de mapeamento na spec de implementação. |
| `n` | 10 | Máx. de itens no digest (cap 25). |
| `format` | `json` | `text` = plain text pronto pra stdout de hook (Claude Code agrega ao contexto). |
| `since` | — | Opcional: janela `--changed-since` composta com salience (ex: `30d` prioriza o que mudou recentemente). |

### Response (`json`)
```json
{
  "scope": "cipher",
  "generated_at": "2026-06-04T13:00:00Z",
  "items": [
    {
      "id": "chk_abc123",
      "title": "Incident 2026-04-25 — reindex wipou section/retention",
      "one_liner": "Ops destrutivas em chunks só com --dry-run ou withOpAudit snapshot.",
      "type": "lesson",
      "pain": 0.9,
      "salience": 0.84,
      "age_days": 40
    }
  ],
  "token_estimate": 980
}
```

### Regras
- **Ranking:** `ORDER BY salience DESC` no escopo filtrado. Sem FTS, sem embedding call → **p50 alvo < 100ms**, $0/query.
- **Budget:** response `text` ≤ ~1.200 tokens; trunca em `n` ou no budget, o que vier primeiro.
- **`one_liner`:** primeira linha do chunk ou campo `summary` se existir; nunca o chunk inteiro.
- **Read tracking:** servir um item via brief grava em **tabela própria `brief_log`** (chunk_id, scope, agent, served_at) e **não toca `chunks.access_count`** — sinal orgânico 100% puro pro audit do plano Cipher. *(Design final pós-T0; a versão original previa flag `via=brief` sobre `reads_audit`, que não existe em prod.)*

## 7. Como funciona — fluxos

### Fluxo A — Agente VPS inicia sessão (C3 + C1)
```
OpenClaw bootstrap → plugin chama GET 127.0.0.1:18802/api/brief?scope=<agente>&format=text
→ injeta no system context → agente nasce sabendo lições/decisões/pendências do seu domínio
```

### Fluxo B — Claude Code Mac inicia sessão (C4 + C1)
```
SessionStart hook → curl --max-time 1 http://<tailscale-ip>:18802/api/brief?scope=<projeto-do-cwd>&format=text
→ stdout vira additionalContext → falha = silêncio + log, sessão segue
```

### Fluxo C — Consulta mid-session (C2 + MCP existente)
Política por intenção (documentar em AGENTS.md/SOUL.md na VPS e CLAUDE.md no Mac):

| Intenção | Tool | Custo |
|---|---|---|
| Síntese/diagnóstico ("isso já ocorreu?", "qual decisão sobre X?") | `answer` | ~1.6s + LLM call (quota gemini-2.5-flash-lite) — budget explícito |
| Recall bruto / lookup | `search` | ms, $0 |
| Detalhe de ponteiro do brief | `search` por id/título | ms, $0 |

### Fluxo D — Fim de sessão → ingest (C3/C4 + ingest-event do P2)
```
Stop/SessionEnd → digest da sessão (Mac: reaproveita .remember/now.md; VPS: digest do agente)
→ POST /api/ingest-event  (kind=session_end, via routeIngest)
→ chunk type=daily, retention 90d
→ crystallize nightly promove o que vale (lesson/decision = retenção longa)
```

## 8. Segurança & rede

- API hoje escuta `127.0.0.1:18802` (VPS). Para C2/C4: **bind adicional no IP Tailscale** (estável desde fix healthcheck f43a2d6) ou túnel SSH. **Nunca expor público.**
- Bind além de localhost ⇒ **auth token obrigatório** (header `Authorization: Bearer`, token em `.env` — nunca em git).
- Privacy do ingest: reaproveita layers do P2 (dependência A1 — redaction antes de persistir). `redaction_count` exposto.
- Porta: ler `NOX_API_PORT` do .env, nunca hardcode (regra #4 do repo).

## 9. Fases, entregas e critérios de aceite

### Fase 1 — `/api/brief` (memoria-nox) ← **começa aqui**
> **Spec de implementação:** `2026-06-04-F1-api-brief-implementation.md` (T0–T7). Scope mapping por namespaces de `source_file` (zero ALTER em chunks) + read tracking em `brief_log` própria (`access_count` intocado).
- [x] Endpoint GET com contrato §6 (scope/n/format/since) — PR nox-workspace#1
- [x] Read tracking em `brief_log` própria; `access_count` intocado (design final T0)
- [x] Testes: 20/20 pass; bench prod 100.5k chunks p50 37–80ms
- [x] Doc: `PRIMITIVES.md` + `openapi.yaml` + `ARCHITECTURE.md` (commit 3d6eeaa)
- **Gate:** brief de `scope=cipher` retorna as lições de incident high-pain no top-5; latência ok.

### Fase 2 — MCP remote no Mac (config local)
- [ ] Bind Tailscale + auth token na API
- [ ] Registro do MCP server no Claude Code do Mac
- [ ] Smoke: `nox_mem_search` e `answer` funcionando do Mac
- **Gate:** consulta cross-máquina round-trip < 2s; zero exposição pública (verificar com nmap externo).

### Fase 3 — Plugin bootstrap OpenClaw (openclaw-vps/infra)
- [ ] Plugin com `register()` idempotente chamando brief por agente
- [ ] Política answer/search documentada em AGENTS.md/SOUL.md
- [ ] Fail-open validado (API down ⇒ sessão sobe normal)
- **Gate:** 5 agentes priming sem regressão de startup time (> +1s = fail).

### Fase 4 — Hooks Mac (SessionStart/Stop)
- [ ] SessionStart → brief por projeto (cwd) via Tailscale, `--max-time 1`, fail-open
- [ ] Stop → digest `.remember/now.md` → ingest-event tipo daily
- [ ] Dedup: mesma sessão não ingere 2× (session_id no payload)
- **Gate:** 1 semana de uso real; brief útil (proxy: Toto não desliga 😄) + corpus não inflando (Δ chunks/dia ≤ ~10 do loop).

**Dependência cross-fase:** Fluxo D completo depende do `POST /api/ingest-event` (spec P2 §4) — implementar junto da Fase 3 ou 4, escopo memoria-nox.

## 10. Métricas de sucesso

| Métrica | Alvo | Instrumento |
|---|---|---|
| Latência brief p50 | < 100ms | API timing |
| Tokens injetados por priming | ≤ 1.200 | `token_estimate` |
| **Follow-up rate**: % de sessões em que agente puxou detalhe de um ponteiro do brief | > 20% (proxy de utilidade) | `brief_log` ⋈ acesso orgânico (`last_accessed_at`) ≤ 24h após serving |
| Chunks high-pain órfãos (pain ≥ 0.7, access 0 em 60d) | tendência ↓ após priming | audit mensal (item 4 plano Cipher) |
| Crescimento do corpus pelo loop | ≤ ~10 chunks/dia, decaíveis | type=daily count |
| Churn de decisões (mesma decisão re-tomada) | tendência ↓ | `--changed-since` audit (item 2 plano Cipher) |

> **Nota paper:** cada métrica acima é série temporal pro § self-evolution. Instrumentar desde o dia 1 — cada audit é um dado.

## 11. Riscos & mitigações

| Risco | Mitigação |
|---|---|
| Brief vira ruído (salience mal calibrada pro escopo) | Salience está em shadow-mode — Fase 1 gate valida ranking manualmente antes de qualquer agente consumir; ajuste de pesos é feature work (`tune(search):`, regra #5) |
| Ingest loop infla corpus | type=daily 90d + crystallize + métrica Δ/dia com alarme |
| access_count contaminado por priming automático | brief não escreve em access_count — serving vai pra `brief_log` separada (invariante coberta por teste) |
| API exposta na rede | Tailscale-only + Bearer token + verificação externa no gate Fase 2 |
| Hook trava sessão | fail-open + `--max-time 1` em tudo |
| Redundância com memórias locais do Mac | dedup no ingest (feeders, §13); revisar overlap com claude-mem no gate Fase 4; core-memory.json aposentado |

## 12. Decisões de review (Toto, 2026-06-04)

1. **Granularidade de scope — DECIDIDO: projeto/domínio como chave primária, agente como filtro opcional.** Canais mudam (WhatsApp, Mac, sessão VPS), domínios são estáveis (memoria-nox, granix, galapagos, treviso...). Brief keyed por **o que** se está trabalhando, não **onde** — trans-canal por construção. `GET /api/brief?scope=<projeto>[&agent=<persona>]`.
2. **Brief no Mac — DECIDIDO: tudo do escopo do projeto** (não restrito a origem VPS). Direção estratégica: nox-mem como store canônico de tudo; memórias locais do Mac viram *feeders* (§13). Dedup garante que redundância com claude-mem não infla o brief.
3. **Ingest do Mac — DECIDIDO: só digest.** Prompts crus excluídos por default (`NOX_HOOKS_KINDS` sem `user_prompt`). Qualidade > volume.
4. **Budget answer — DECIDIDO: eficiência com qualidade.** Cap **5/sessão** por agente (configurável via env), backbone `gemini-2.5-flash-lite` (regra #3 do repo), budget esgotado ⇒ degrada pra `search` (fail-open, nunca bloqueia).

## 13. Estratégia de consolidação — memórias do Mac como feeders

Direção (decisão Toto Q2): **nox-mem = store canônico de longo prazo de tudo**. As memórias locais não são substituídas no dia 1 — viram feeders ou caches de curto prazo:

| Memória local | O que faz hoje | Papel no desenho final |
|---|---|---|
| **claude-mem** | Auto-captura observações de sessões Claude Code (searchable, IDs) | **Feeder + cache local.** Mantém recall local rápido; digest diário ingerido no nox-mem (type=daily) pra VPS enxergar trabalho do Mac. |
| **`.remember/`** (now/recent/archive) | Buffer de handoff entre sessões | **Feeder direto do Fluxo D** — `now.md` já é a fonte do Stop hook. Continua como buffer de curtíssimo prazo. |
| **core-memory.json** | Perfil estático injetado no SessionStart | **✅ DESLIGADO 2026-06-04** (hook removido de settings.json; arquivo arquivado `.retired-2026-06-04`). Estava stale — descrevia Toto como "CEO/CFO/CTO/CPO/CMO" (framing corrigido em 2026-05-05). Conteúdo válido migra pra entity `person/toto` no nox-mem na Fase 1. |
| **Claude Code auto-memory** (MEMORY.md por projeto) | Fatos curados por projeto | **Feeder curado.** Sync one-way Mac→nox-mem como entities (formato 3-seções) — qualidade alta, candidato a `compiled`. |

**Princípio 4.2 atualizado:** o brief do Mac serve o escopo do projeto inteiro; a defesa contra redundância passa a ser **dedup no ingest** (feeders não criam chunks duplicados) em vez de filtro por origem na leitura.

---

*Memória relacionada: `project-cipher-nox-mem-simbiose-plan-2026-06-04`. Spec base reaproveitada: `2026-05-17-P2-hooks-autocapture.md`.*
