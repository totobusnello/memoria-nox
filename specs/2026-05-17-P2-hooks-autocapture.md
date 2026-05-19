# P2 — Auto-capture de conversas via Claude Code hooks (zero manual ingest)

**ID:** P2
**Pilar:** **P2 — Captura passiva sem fricção** (Q/A/P framework: Quality/Autonomy/Passivity)
**Status:** Proposto — spec implementation-ready
**Owner:** Toto (decisão); Maestro/Forge (execução); coordena com A1 (privacy filter)
**Data:** 2026-05-17
**Origem:** gap competitivo vs `rohitg00/agentmemory` (12 hooks lifecycle → zero `add()` manual); evolução natural pós-A1 privacy filter

**Cross-link:**
- `specs/2026-04-12-self-evolving-hooks.md` (precursor — hooks Mac local pra dream/learning, escopo diferente)
- A1 privacy filter spec (paralelo, pré-requisito hard de v1)
- `docs/HANDOFF.md` §captura passiva (próxima ação)
- `~/Claude/Projetos/openclaw-vps/infra/CLAUDE.md` (plataforma onde o nox-mem API roda)

> **Tagline norteador:** *"Pain-weighted hybrid memory with shadow discipline — yours by design."* — P2 ativa **captura passiva** (sem fricção pro usuário) sem comprometer disciplina shadow (eventos são armazenados; ranking continua intocado até validação posterior).

---

## 1. Motivação

### 1.1 Estado atual (gap)

Ingestão hoje em nox-mem é **100% file-based**:

| Caminho atual | Mecanismo | Fricção |
|---|---|---|
| Entity files (`memory/entities/<type>/<slug>.md`) | inotifywait + `ingestEntityFile()` | médio (Toto edita manualmente) |
| Markdown drops (`memory/raw/*.md`) | watch + `ingestFile()` genérico | médio |
| Manual `nox-mem ingest <file>` | CLI | alto (lembrança humana) |
| Conversas Claude Code (live) | **NÃO CAPTURA** | total — sinal mais rico, zero ingest |

Resultado: o sistema sabe sobre o **estado finalizado** (entity files compilados), mas perde **o processo** — tool calls, raciocínio, erro→correção, decisão→revisão. O sinal de maior valor pra memória organizacional fica de fora.

### 1.2 Gap competitivo: `rohitg00/agentmemory`

Concorrente direto. Pillar central: 12 hooks Claude Code que capturam todo tool call **automaticamente** via `memory.add()` server-side. Resultado: zero linha de código do usuário, conversa inteira em DB.

| Eixo | agentmemory | nox-mem hoje | nox-mem pós-P2 |
|---|---|---|---|
| Captura passiva | ✅ 12 hooks | ❌ zero | ✅ 5 hooks |
| Privacy pre-storage | ❌ "store everything raw" | ✅ A1 filter (em build) | ✅ A1 redact() integrado |
| KG-aware ingestion | ❌ flat blob storage | ✅ entity routing | ✅ session→KG extraction |
| Pain weighting | ❌ não tem | ✅ shadow-mode | ✅ events herdam pain |
| Privacy override | ❌ store everything | n/a | ✅ NOX_HOOKS_KINDS opt-out granular |

**Posicionamento:** nox-mem entrega **paridade UX** de captura passiva, mas com **disciplina arquitetural** que agentmemory não tem (redação obrigatória, retenção tipada, salience-aware, KG downstream). É o diferencial "by design" da tagline.

### 1.3 Por que agora

1. A1 privacy filter já em build → pré-requisito hard atendido em paralelo.
2. HTTP API :18802 já estável (3 meses prod, gateway-drift fix 2026-05-01).
3. Schema v10 com `retention_days` + `section` permite separar eventos (30d) de truth crystallized (entity files).
4. Sem captura passiva, o pool de chunks **tech process** segue dependendo de Toto curar manualmente — não escala.

---

## 2. Escopo de hooks (Claude Code lifecycle)

Claude Code expõe ~12 hooks. Subscrevemos **5** em v1, com critérios explícitos pra cada um.

### 2.1 Matriz de decisão

| Hook | Capturamos? | Sensibilidade privacy | Valor mnemônico | Justificativa |
|---|---|---|---|---|
| **SessionStart** | ✅ sim | Baixa (só metadata) | Médio (injeção de contexto bidirecional) | Carregar perfil do projeto via `nox-mem search` + retornar top-K chunks como stdout (Claude Code agrega ao contexto). Sinal: começo do trabalho. |
| **UserPromptSubmit** | ✅ sim | **Alta** (prompt cru = intent humano) | Alto (queries, dúvidas, decisões verbais) | Captura intent. Redaction obrigatória + amostragem opcional (`NOX_HOOKS_PROMPT_SAMPLE`). |
| **PostToolUse** | ✅ sim (sinal principal) | **Alta** (Read pode trazer .env, Bash pode trazer secrets) | **Crítico** | Bash output, Edit diffs, Read snippets — o trabalho real do agente. Filter por matcher (excluir leituras de `.env`, `.ssh/*`, etc). |
| **Stop** | ✅ sim | Baixa (summary já redacted) | Alto (sessão completa) | Flush session summary + dispara KG extraction async. Fecha sessão lógica. |
| **PreCompact** | ✅ sim | Média | **Crítico** (raro) | Captura snapshot ANTES do compact destruir contexto histórico. Inversa da motivação do hook: salvar o que ia se perder. |
| PreToolUse | ❌ não em v1 | n/a | Baixo (intent já vem via UserPromptSubmit) | Evitar 2× ingest do mesmo signal. Reservado pra v2. |
| Notification | ❌ não | n/a | Nenhum | UI signal, sem valor mnemônico. |
| SessionEnd | ❌ não em v1 | n/a | Redundante com Stop | Stop já cobre cleanup. |
| SubagentStop | ❌ não em v1 | n/a | Redundante | Stop pai cobre. |
| StopFailure | ❌ não em v1 | Média | Alto (erros são sinal forte!) | **TODO v2** — capturar falhas é informação rica, fica fora de v1 só pra reduzir escopo. |
| (outros) | ❌ não | — | — | Fora de escopo. |

**Volume estimado** (sessão típica Toto, 2h): ~150 PostToolUse + ~20 UserPromptSubmit + 1 SessionStart + 1 Stop + 0-1 PreCompact ≈ **170 eventos/sessão**.

### 2.2 Matcher patterns (PostToolUse)

`PostToolUse.matcher` filtra qual tool dispara. Capturamos amplo, redactamos no servidor.

```
"PostToolUse": [{
  "matcher": "Bash|Edit|Write|Read|Glob|Grep|Task|WebFetch|WebSearch",
  "hooks": [{ "type": "command", "command": "~/.nox-mem/hooks/postToolUse.sh" }]
}]
```

**Skip explícito:** `TodoWrite` (interno UI), `NotebookEdit` (raro, escopo v2).

---

## 3. Arquitetura dos hook scripts

### 3.1 Decisão: shell scripts + HTTP POST (não CLI direto)

| Opção | Latência | Concorrência | CWD-safe | Veredito |
|---|---|---|---|---|
| `nox-mem ingest-event` CLI direto | 800-1500ms (node cold start) | conflito sqlite WAL multi-proc | depende de cwd | ❌ |
| Shell + curl HTTP POST :18802 | **15-40ms** | API queue absorve | independente | ✅ |
| Direct sqlite write em-process | crítico (lock) | sequência crítica | n/a | ❌ |

Trade-off explícito: hooks executam **fora do agente** mas **dentro do turno** — se passam de ~100ms começam a degradar UX. Curl c/ `--max-time 1` ganha por larga margem.

### 3.2 Contrato do hook script

**Input:** JSON via stdin (Claude Code injeta).

**Pipeline:**
1. Ler stdin → JSON parse minimal (jq ou bash + heredoc — sem node).
2. Transformar pro schema `{kind, session_id, timestamp, payload}`.
3. POST async pra `http://${NOX_API_URL}/api/ingest-event` com `curl --max-time 1 -fsSL` em background (`&`).
4. Se HTTP fail OU API down → append linha JSONL em `~/.nox-mem/pending-events.jsonl` (drain async via cron, ver §7.2).
5. Exit 0 (NUNCA bloquear o agente, mesmo em erro).

**Não fazer:**
- Não validar schema no hook (servidor valida — hook é "dumb pipe").
- Não redactar no hook (`redact()` é server-side — fonte única).
- Não logar stdout (Claude Code agrega ao contexto e poluiria; só SessionStart pode usar stdout intencionalmente).

### 3.3 Layout de arquivos

```
~/.nox-mem/
├── hooks/
│   ├── sessionStart.sh
│   ├── userPromptSubmit.sh
│   ├── postToolUse.sh
│   ├── stop.sh
│   └── preCompact.sh
├── lib/
│   ├── common.sh           # helpers: send_event(), fallback_log()
│   └── session-id.sh       # session_id derivation
├── pending-events.jsonl    # fallback queue
└── config.env              # NOX_API_URL, NOX_HOOKS_ENABLED, NOX_HOOKS_KINDS
```

Repo path (não-instalado): `hooks/` na raiz do `memoria-nox/`.

---

## 4. Novo endpoint HTTP — `POST /api/ingest-event`

### 4.1 Request schema

```json
{
  "kind": "tool_use" | "user_prompt" | "session_start" | "session_end" | "pre_compact",
  "session_id": "lab-<hostname>-<cc_session_uuid>",
  "timestamp": "2026-05-17T22:14:31.842Z",
  "cwd": "/Users/lab/Claude/Projetos/memoria-nox",
  "project_slug": "memoria-nox",
  "payload": {
    "tool_name": "Bash",
    "tool_input": { "command": "ls -la" },
    "tool_output": "...",
    "duration_ms": 142
  }
}
```

**`payload` é polimórfico por `kind`:**

| kind | payload obrigatório |
|---|---|
| `tool_use` | `tool_name`, `tool_input`, `tool_output`, `duration_ms` |
| `user_prompt` | `prompt_text`, `prompt_tokens` |
| `session_start` | `model`, `cc_version`, `prior_session_id?` |
| `session_end` | `summary?`, `tool_use_count`, `duration_total_ms` |
| `pre_compact` | `transcript_excerpt`, `tokens_to_compact` |

### 4.2 Response

```
HTTP/1.1 202 Accepted
Content-Type: application/json

{ "queued": true, "event_id": "evt_01HXYZ...", "redaction_count": 2 }
```

**Sempre 202 imediato** — processamento real é async (queue interna in-memory + flush sqlite). Cliente nunca bloqueia em IO.

**Erros:**
- 400 — schema inválido (hook bug)
- 413 — payload >256KB (truncamos no servidor, retornamos warning header)
- 503 — queue cheia (>10k pendentes) → fallback file kick-in
- 500 — bug servidor (log + alert)

### 4.3 Async pipeline server-side

```
HTTP handler (202) ──► in-memory ring buffer (10k slots)
                         │
                         └─► worker (interval 250ms or batch 100):
                              1. redact(payload) via A1 filter
                              2. Project routing (cwd → project_slug)
                              3. INSERT INTO agent_events
                              4. Update telemetry counters
```

Backpressure: se ring buffer >80% → response inclui `Retry-After: 2`. Hooks ignoram (fire-forget), mas fica no header pra debugging.

---

## 5. Privacy (DEPENDÊNCIA HARD em A1)

### 5.1 Layers de defesa

**Layer 1 — `redact(text)` da A1:**
Todo `payload.*_text`, `prompt_text`, `tool_output`, `command` passa por `import { redact } from 'src/privacy/filter.ts'` antes de hit em sqlite. Sem A1 mergeado, P2 não vai pra prod.

**Layer 2 — Path scrub session-level:**
Pós-redact, normalizar paths sensíveis:

| Pattern | Substituição |
|---|---|
| `/Users/<user>/...` | `~/...` |
| `/root/.openclaw/...` | `${OPENCLAW_HOME}/...` |
| Hostnames internos (`vps.openclaw.lab`) | `<vps-host>` |
| UUIDs em paths | `<uuid>` |

**Layer 3 — Kind-level opt-out:**
`NOX_HOOKS_KINDS="tool_use,session_start"` (default `all`) permite Toto excluir `user_prompt` se quiser preservar intent crua dele.

**Layer 4 — Per-tool opt-out (PostToolUse):**
Env var `NOX_HOOKS_SKIP_TOOLS="WebFetch,Read"` no hook script — skip antes do POST.

**Layer 5 — Hard-block paths:**
Servidor rejeita (return 400 + log) qualquer `tool_input.file_path` que match em:
- `~/.ssh/*`, `~/.aws/*`, `~/.gnupg/*`
- `*.env`, `*credentials.json`, `*secrets.{json,yaml,yml}`
- `~/.openclaw/.env` (literal)

### 5.2 Métrica `redaction_count`

Cada `agent_events` row guarda quantos matches redact() fez. Permite eval qualidade A1 com sinal real (não golden set sintético).

---

## 6. Storage layer

### 6.1 Schema novo — `agent_events`

```sql
CREATE TABLE agent_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_uuid TEXT NOT NULL UNIQUE,           -- evt_01H... (ULID)
  session_id TEXT NOT NULL,
  project_slug TEXT NOT NULL,
  kind TEXT NOT NULL CHECK(kind IN ('tool_use','user_prompt','session_start','session_end','pre_compact')),
  timestamp TEXT NOT NULL,                    -- ISO 8601
  cwd TEXT,
  payload_json TEXT NOT NULL,                 -- redacted JSON blob
  redaction_count INTEGER NOT NULL DEFAULT 0,
  ingested_at TEXT NOT NULL DEFAULT (datetime('now')),
  consolidated_chunk_id INTEGER,              -- FK → chunks.id (após crystallize)
  retention_days INTEGER NOT NULL DEFAULT 30
);

CREATE INDEX idx_agent_events_session ON agent_events(session_id, timestamp);
CREATE INDEX idx_agent_events_project ON agent_events(project_slug, kind, timestamp);
CREATE INDEX idx_agent_events_consolidation ON agent_events(consolidated_chunk_id) WHERE consolidated_chunk_id IS NULL;
```

**Separação proposital de `chunks`:**
- `chunks` = truth indexada, FTS5 + vec, retention tipada.
- `agent_events` = sinal cru session-scoped, retention 30d default, sem FTS5, sem vec.
- Crystallize/consolidate (manual ou cron) **promove** subset de events → chunks (com section, pain, retention apropriada).

### 6.2 Migration

- Schema bump v10 → v11.
- Migration: `migrations/011-agent-events.sql`.
- Backfill: nenhum (tabela nova).
- Rollback: DROP TABLE (sem dependências externas em v1).

### 6.3 Crystallize path (out of scope v1, documentado)

```
agent_events (30d retention)
    │
    ├─► [cron diário 02:30] consolidate-events.ts
    │       agrupa por (session_id, kind=user_prompt)
    │       summariza via Gemini flash-lite (1 prompt/session)
    │       gera chunk em chunks com section='timeline', retention=90d
    │
    └─► [cron semanal] kg-extract-from-events.ts
            extrai entities/relations das tool_use payloads
            merge incremental em kg_entities
```

**v1 entrega só a captura.** Crystallize é P2-followup (deixar event raw 30d permite Toto inspecionar antes de promover).

---

## 7. Performance & resiliência

### 7.1 Budget rígido

| Métrica | Target | Hard limit |
|---|---|---|
| Hook script duração total | <50ms | 100ms |
| Curl POST (fire-forget) | <30ms | 1000ms (--max-time) |
| Servidor handler 202 response | <10ms | 50ms |
| Server worker redact+insert | <20ms/event | n/a (async) |

Hook script é **fire-and-forget**:

```bash
curl -fsSL --max-time 1 \
  -X POST "${NOX_API_URL}/api/ingest-event" \
  -H 'Content-Type: application/json' \
  -d "$payload" \
  > /dev/null 2>&1 &
disown
exit 0
```

`&` + `disown` = shell volta imediato, agente continua. Worst case latência percebida = startup do bash + jq parse ≈ 20-30ms.

### 7.2 Fallback file (API down)

Se `curl` retornar não-zero (preflight check separado, ver §7.3) → escrever linha JSONL em `~/.nox-mem/pending-events.jsonl`.

Drain cron (`*/5 * * * *`):
```bash
nox-mem ingest-events-drain --batch 500
```

Lê linha por linha, POST com retry 3×, remove linhas drenadas via `tmp + mv atomic`. File-locked via `flock` pra evitar double-drain.

Cap: 50MB → rotate pra `.1`, `.2`. Se total >200MB → alert Discord (signal de API quebrada há dias).

### 7.3 Preflight health check (1×/sessão)

`sessionStart.sh` faz UM `curl --max-time 0.5 :18802/api/health`:
- 200 → exporta `NOX_API_REACHABLE=1` em arquivo de estado `~/.nox-mem/state.env`
- fail → flag `NOX_API_REACHABLE=0`, demais hooks pulam HTTP e vão direto pro fallback file. Evita stalling 1s × 170 hooks/sessão (~3min de overhead).

Refresh: state file TTL 10min, se >10min sessionStart refaz.

---

## 8. Session bridge

### 8.1 Derivação do `session_id`

Reusa pattern documentado em `~/.claude/projects/.../MEMORY.md` ("CLI+API session_id sync via env override"):

```
session_id = NOX_SESSION (env override, se setado)
           OR claude_code_session_uuid (vem no JSON do hook)
           OR fallback: "${hostname}-${ppid}-$(date +%s)"
```

Prefixado com `lab-` (machine prefix) pra cross-machine future:
```
lab-<hostname>-<cc_session_uuid>
```

Stop hook escreve `session_id` em `~/.nox-mem/state.env` → todos hooks subsequentes (mesma sessão CC) lêem dali. Sai do shell parent dependence.

### 8.2 Project slug

Derivado em ordem de prioridade:
1. Env `NOX_PROJECT_SLUG` (override absoluto)
2. `cwd` (do hook JSON) → match contra `agent-orchestrator.yaml` projects list
3. `cwd` basename como fallback

Project routing é informativo (telemetria + filtros futuros), não particiona DB em v1.

---

## 9. Installation — `nox-mem connect claude-code`

### 9.1 Command spec

```
nox-mem connect claude-code [--global|--project] [--dry-run] [--force]
```

**Default:** `--global` (mexe em `~/.claude/settings.json`).
**`--project`:** mexe em `.claude/settings.json` no cwd (precedência maior em CC).
**`--dry-run`:** imprime diff, não escreve.
**`--force`:** pula confirmação interativa.

### 9.2 Pipeline de execução

1. **Detect** `~/.claude/settings.json` (ou cria com `{}` se não existir).
2. **Backup atômico:** copy pra `settings.json.nox-mem-backup-<ts>.json` (perms 0600). NUNCA escrever sem backup.
3. **Deep merge** do bloco de hooks nox-mem em `settings.hooks.*`, preservando hooks existentes do usuário (append em arrays, nunca replace). Algoritmo:
   - Pra cada hook event (PostToolUse, etc), se já existe um entry com `matcher` que conflita: **append** novo entry com matcher próprio (`nox-mem|...`), NÃO mexer no existente.
   - Tag cada hook nox-mem com `"_owner": "nox-mem"` (custom field, CC ignora) pra disconnect saber o que remover.
4. **Confirm interativo** com diff colorido (a menos que `--force`).
5. **Install scripts** em `~/.nox-mem/hooks/` (copia de `hooks/` no repo + chmod +x).
6. **Test ping** — fake event POST pra `/api/ingest-event` com `kind=session_start`, verifica 202.
7. **Print success** + comando reverse.

### 9.3 `nox-mem disconnect claude-code`

1. Lê `~/.claude/settings.json`.
2. Remove todo entry com `_owner: "nox-mem"`.
3. Backup antes (`.nox-mem-backup-disconnect-<ts>`).
4. NÃO remove `~/.nox-mem/hooks/` (deixa scripts pra forensics; user roda `rm -rf` manual se quiser).

**Validar:** A1 docs (`feedback_openclaw_config_set_required_for_persistence.md`) ensina que escrever JSON manualmente em alguns sistemas é override por daemon. Pra Claude Code settings esse risco NÃO existe (CC lê settings on session start, não daemoniza overwrite). Documentar explicitamente pra futuro confusion.

---

## 10. Configuração — env vars

| Env var | Default | Função |
|---|---|---|
| `NOX_API_URL` | `http://127.0.0.1:18802` | Endpoint nox-mem-api. Read do hook script. |
| `NOX_HOOKS_ENABLED` | `true` | Kill switch. `false` → todos hooks viram no-op exit 0. |
| `NOX_HOOKS_KINDS` | `all` | CSV: `tool_use,user_prompt,session_start,session_end,pre_compact`. Filter no hook script antes do POST. |
| `NOX_HOOKS_SKIP_TOOLS` | `` | CSV de tool_name a pular em PostToolUse (ex: `WebFetch,Read`). |
| `NOX_HOOKS_VERBOSE` | `0` | `1` → log em `~/.nox-mem/hooks.log` (debug). |
| `NOX_HOOKS_PROMPT_SAMPLE` | `1.0` | Float 0-1, sample rate UserPromptSubmit. Permite reduzir volume sem tirar 100%. |
| `NOX_SESSION` | (auto) | Override session_id (compartilha CLI+API; ver §8.1). |
| `NOX_PROJECT_SLUG` | (auto) | Override project routing. |

Config file `~/.nox-mem/config.env` carregado por `common.sh` em todos hooks. User edita ali, sem precisar tocar `.zshrc`.

---

## 11. Telemetria

### 11.1 Métricas exposed em `/api/health.hooks`

```json
{
  "hooks": {
    "enabled": true,
    "events_24h": { "tool_use": 2841, "user_prompt": 312, "session_start": 18, "session_end": 17, "pre_compact": 2 },
    "events_7d": { ... },
    "redaction_count_24h": 47,
    "pending_file_size_bytes": 0,
    "queue_depth_now": 12,
    "queue_overflow_24h": 0,
    "last_event_at": "2026-05-17T22:14:31Z"
  }
}
```

**Sem content** — só counters por kind/session/project. Permite Toto debugar "estou capturando?" sem ler payloads.

### 11.2 Dashboard hook

Adicionar 1 página em `agent-hub-dashboard` (já tem 4 pra nox-mem):
- Events/dia por kind, stacked bar
- Redaction rate (% events com redaction_count >0)
- Pending file size (alert visual >10MB)

---

## 12. Plan de testes

### 12.1 Unit (hook scripts)

- **shellcheck** em todos `*.sh` (CI gate).
- **bats-core** harness em `tests/hooks/`:
  - `postToolUse-emits-correct-payload.bats` — feed fake stdin, mock curl, verify payload shape.
  - `fallback-file-on-api-down.bats` — mock curl fail, verify line appended a `pending-events.jsonl`.
  - `kind-filter-respected.bats` — `NOX_HOOKS_KINDS=tool_use` skip user_prompt.
  - `skip-tools-respected.bats` — `NOX_HOOKS_SKIP_TOOLS=Read` skip Read events.
  - `health-check-flags-state.bats` — sessionStart writes state.env corretamente.

### 12.2 Integration (server-side)

- `tests/api/ingest-event.test.ts`:
  - Schema validation (400 em payload malformado).
  - Async queue → DB insert em <250ms.
  - Hard-block paths (`.env`, `.ssh/*`) → 400 + audit log.
  - Redaction wired (mock A1, verify call).
  - Backpressure: encher queue, verificar Retry-After header.

### 12.3 End-to-end

`tests/e2e/claude-code-hooks-flow.sh`:
1. `nox-mem connect claude-code --project --force` em diretório temp.
2. Spawn Claude Code session via headless mode (`claude --print --headless`).
3. Run scripted conversation (5 prompts, alguns invocando Bash/Read/Edit).
4. Stop session.
5. Query DB: `SELECT kind, COUNT(*) FROM agent_events WHERE session_id LIKE 'lab-%' GROUP BY kind`.
6. Verify counts: >=1 session_start, >=5 user_prompt, >=10 tool_use, >=1 session_end.
7. Verify `redaction_count > 0` em pelo menos 1 row (testa wiring A1).

### 12.4 Performance benchmark

`scripts/bench-hooks.sh`:
- Loop 1000× chamando `postToolUse.sh` com fake JSON.
- Mede p50/p95/p99 wall-clock.
- Gate: p95 <100ms.

### 12.5 Privacy regression

`tests/privacy/hooks-redact.test.ts`:
- 20 fixtures de tool outputs com secrets known-bad (API keys, paths sensíveis, tokens).
- Após ingest, query DB: `SELECT payload_json FROM agent_events`.
- grep adversarial: zero matches em regex de secret patterns.

---

## 13. DoD (Definition of Done)

Numerado pra rastreio:

1. **Hooks configurados** em `~/.claude/settings.json` via `nox-mem connect claude-code`, com backup automático (`.nox-mem-backup-<ts>.json`) e disconnect funcional reversível.
2. **5 hook events ativos** (SessionStart, UserPromptSubmit, PostToolUse, Stop, PreCompact) capturando eventos em `agent_events` (schema v11) com redaction wired via A1 `redact()`.
3. **Endpoint `POST /api/ingest-event`** responde 202 em <50ms (p95), enfileira async, redacta server-side, indexa em <250ms (p95).
4. **Fallback file** (`~/.nox-mem/pending-events.jsonl`) drena via cron quando API volta; queue overflow não perde eventos (alert se size >10MB).
5. **Telemetria `/api/health.hooks`** exposed (counters por kind/session/project, sem content), dashboard panel adicionado.

**Não DoD (v2 backlog):** crystallize automático events→chunks, captura de StopFailure, hooks pra Cursor/Codex.

---

## 14. NÃO-fazemos (v1)

Decisões explícitas de escopo:

- **Não mudamos ranking** — eventos vão pra `agent_events`, NÃO pra `chunks`. Hybrid search retorna mesmos resultados pré-P2. Disciplina shadow preservada (regra crítica #5 do CLAUDE.md).
- **Não fazemos crystallize automático** — promover events → chunks é manual via cron ou comando (`nox-mem crystallize-events`). Razão: deixar Toto inspecionar 30d antes de comprometer pool. Risk de poluir DB com noise se auto.
- **Não capturamos diff estruturado** — Edit payload é raw (old_string + new_string), sem AST diff. Mais simples, suficiente pra v1. v2 pode add `diff --unified` derivado server-side.
- **Não fazemos Cursor/Codex hooks** em v1 — escopo Claude Code only. Cursor/Codex são P4 no roadmap (lifecycle hooks diferem, custo de generalização não justificado antes de validar UX em CC).
- **Não capturamos PreToolUse** em v1 — UserPromptSubmit cobre intent; PreToolUse seria 2× signal pro mesmo turno. Reservado pra v2 caso precise capturar intent **por tool** (ex: catch antes do agente rodar `rm`).
- **Não fazemos KG extraction inline** no PostToolUse — async batch via cron diário (custo Gemini bound). Latência hot path zero.
- **Não suportamos hot-reload de config** — alterações em `~/.nox-mem/config.env` requerem `nox-mem connect claude-code --refresh` (re-roda parte 6 da install pipeline).
- **Não capturamos `Notification`, `SubagentStop`, `SessionEnd`** — `Stop` cobre cleanup, demais sem valor mnemônico em v1.

---

## 15. Riscos & mitigations

| Risco | Probabilidade | Impacto | Mitigation |
|---|---|---|---|
| **Hook script crashea** (jq bug, syntax error) → bloqueia Claude Code | Baixa | **Alto** (UX broken) | `exit 0` no fim de TODOS scripts independente de erro. shellcheck CI gate. Wrap em `{ ... } 2>>~/.nox-mem/hooks-err.log` + sempre exit 0. |
| **Privacy regex false negative** (A1 deixa secret passar) | Média | **Crítico** (key leak em DB) | (a) A1 hard-block layer no servidor pra paths conhecidos sensíveis; (b) audit log `redaction_count`; (c) regression test 20 fixtures secrets known-bad; (d) `nox-mem scrub-events --re-redact` retroativo pós-A1 upgrade. |
| **`session_id` mismatch** entre hooks (mesma sessão vira 2 IDs) | Média | Médio (eventos quebrados) | State file `~/.nox-mem/state.env` write-once por sessionStart; demais hooks read-only. Pattern já validado em CLI+API sync. |
| **API restart drops queue** (in-memory ring buffer) | Média | Médio (eventos perdidos) | (a) Fallback file kick-in via preflight check; (b) graceful shutdown handler em nox-mem-api flush pendentes antes de SIGTERM; (c) systemd `ExecStop` envia SIGTERM com `TimeoutStopSec=10s`. |
| **Curl --max-time 1 estoura** em network glitch → hook lento | Baixa | Baixo | --max-time 1 é hard cap. Fire-forget em background, hook script já saiu antes do timeout. |
| **Volume explode** (sessão Toto 4h c/ 500 tool calls × 30 dias = 60k events/mês) | Alta | Médio (DB grows) | (a) retention 30d default + cron diário cleanup; (b) `agent_events` separa de `chunks` (não polui FTS5/vec); (c) telemetry alerta se >500k events; (d) future: tiered storage (events >7d → compress JSON). |
| **Settings.json merge corrompe user hooks** | Baixa | Alto | (a) Backup atômico ANTES de mexer; (b) deep merge nunca substitui, só append com `_owner: "nox-mem"`; (c) `disconnect` 100% reversível via backup; (d) `--dry-run` obrigatório em primeira instalação documentada. |
| **A1 privacy filter atrasa** → P2 fica blocked | Média | Alto | Build P2 em paralelo (server, schema, hooks) com mock `redact = (s) => s`. Não merge pra main até A1 ready. Permite paralelizar 80% do trabalho. |
| **Claude Code muda hook schema** entre versões | Baixa | Alto | (a) Validar hook contract on `nox-mem connect claude-code` (test event); (b) BLOCKED.md se Anthropic deprecar `command` hook type; (c) version-pin support: `nox-mem doctor --claude-code` reporta versão CC + hook compat. |
| **Hostname-based session_id quebra cross-machine** (Toto laptop + VPS) | Baixa | Baixo | session_id já prefixado com hostname; cross-machine é v2 (sync events file → API remoto). Documentado como limitação v1. |

---

## 16. Plano de execução (estimativa)

| Fase | Esforço | Bloqueia próximo |
|---|---|---|
| **F1** — Schema v11 + migration + endpoint `/api/ingest-event` + worker async | 4-6h | F2 |
| **F2** — 5 hook scripts + common.sh + session-id.sh | 3-4h | F3 |
| **F3** — `nox-mem connect/disconnect claude-code` command | 2-3h | F4 |
| **F4** — Wire A1 `redact()` + hard-block paths layer | 1-2h (depende A1 ready) | F5 |
| **F5** — Tests (unit + integration + e2e + privacy regression) | 4-5h | F6 |
| **F6** — Telemetria `/api/health.hooks` + dashboard panel | 1-2h | DoD |
| **Total** | **15-22h** | — |

Sequência: F1 → F2 → F3 em paralelo com F4 (mockando redact). F5/F6 último.

---

## 17. Aprovação pendente

- **Toto** — decisão go/no-go após review desta spec; aprovação do escopo v1 (5 hooks) e exclusões v1 (PreToolUse, StopFailure, Cursor/Codex).
- **A1 owner** — confirmar API `redact(text: string): { text: string, redaction_count: number }` antes de F4.
- **VPS infra** — aprovar nova route `/api/ingest-event` no nox-mem-api (sem mudança de porta).

---

## 18. Open questions

1. **Sample rate adaptativo?** Sessão de 4h Toto pode gerar 500 tool_use. Vale começar com `NOX_HOOKS_PROMPT_SAMPLE=1.0` e degradar se ficar barulhento?
2. **PreCompact: capturar transcript inteiro ou só summary?** Tradeoff: completude vs payload size (>256KB cap).
3. **Project routing pre-defined?** Match `cwd` contra lista fixa de projetos (agent-orchestrator.yaml) ou auto-cria slug novo se cwd não bate?
4. **Crystallize-events v1.1 quando?** É bottleneck pra valor real (events ficam em silo até promover). Schedule no roadmap pós-P2 v1?
5. **Multi-machine sync?** Toto roda Claude Code em laptop + VPS. v1 captura por máquina separado. v2 deveria sync laptop→VPS API? Risk: laptop offline → backlog.

---

*Spec aderente ao formato Superpowers (checkbox tasks, chunk boundaries). Implementation-ready — não implementar antes da decisão Toto + A1 confirmation.*
