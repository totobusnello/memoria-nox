# P2 Implementation Kickoff — Claude Code Hooks Auto-Capture

**Doc type:** Implementation task breakdown (not re-spec)
**Owner:** Engineering executor (post PR #4 review + A1 PR #5 merge)
**Date:** 2026-05-18
**Status:** READY-TO-EXECUTE (after P1 + A2 land per D41 #5 sprint order)
**Sprint:** Third post-merge sprint per D41 #5 ordering
**Tagline:** *Pain-weighted hybrid memory with shadow discipline — yours by design.*

---

## 0. Cross-Reference

| Artifact | Location |
|---|---|
| P2 canonical spec | [PR #4](https://github.com/totobusnello/memoria-nox/pull/4) → `specs/2026-05-17-P2-hooks-autocapture.md` (587 lines, 3,968 words) |
| **A1 privacy filter (HARD DEP)** | [PR #5](https://github.com/totobusnello/memoria-nox/pull/5) — **MERGED 2026-05-18** → `src/privacy/filter.ts` exposes `redact(text)` |
| D41 sprint order | `docs/DECISIONS.md` §2026-05-18 madrugada — item #5 (P1 → A2 → **P2** → P4) |
| P1 kickoff (precedent style) | [PR #18](https://github.com/totobusnello/memoria-nox/pull/18) → `specs/2026-05-18-P1-implementation-kickoff.md` |
| A2 kickoff (parallel-track precedent) | [PR #17](https://github.com/totobusnello/memoria-nox/pull/17) → `specs/2026-05-18-A2-implementation-kickoff.md` |
| Shadow discipline regra crítica | `CLAUDE.md` §regras-críticas #5 (ranking changes ≠ "fix" commits) |
| Precursor spec (different scope) | `specs/2026-04-12-self-evolving-hooks.md` (Mac-local dream/learning hooks, NÃO substitui P2) |
| Plataforma onde a nox-mem API roda | `~/Claude/Projetos/openclaw-vps/infra/CLAUDE.md` |

**Read this doc instead of the 3,968-word spec for execution.** Spec stays canonical for design questions; kickoff is the engineering work order.

---

## 1. Sprint Position — LOCKED (D41 #5)

P2 ships **third** in the post-merge sprint cadence:

```
P1 (answer primitive) → A2 (export/import) ┐
                                            ├──► P2 (hooks) ──► P4 (connect IDE)
                       parallel se capacity ┘
```

**Why third (not first):** P2 captures conversation events, mas sem P1 (`nox-mem answer`) e A2 (export) o pool de events fica em silo — Toto não consegue *queriar* nem *portar* o que foi capturado. P1 + A2 entregam a "leitura"; P2 entrega a "escrita".

**Why before P4:** P4 (`nox-mem connect <ide>`) generaliza o instalador. P2 implementa o `connect claude-code` específico que P4 vai extrair. Build P2 primeiro, refactor pra P4 second.

**A1 dependency status:** **A1 PR #5 já merged.** `src/privacy/filter.ts` exporta `redact(text: string): { text: string, redaction_count: number }`. P2 importa direto — sem mock-swap em produção.

---

## 2. A1 Dependency Strategy (development time only)

Mesmo com A1 merged, T1-T10 **podem ser desenvolvidos com mock** pra permitir paralelização entre executores:

```typescript
// src/lib/events/redact-mock.ts (delete after T11)
export const redact = (s: string) => ({ text: s, redaction_count: 0 });
```

**T11 é o swap mandatory:** substitui import do mock pelo real `import { redact } from 'src/privacy/filter'`. CI gate em T11 garante que o mock não sobrevive em main.

**Por que mock primeiro:** desacopla concerns — engenheiro foca em hook plumbing, schema, async pipeline. A1 wiring é 1 line change em T11. Reduz risco de retrabalho se A1 contract mudar pós-merge (PR #5 docs travam contract, mas defesa em camadas).

---

## 3. Task Breakdown (dependency-ordered)

> **15 tasks.** T1 unblocks T2-T3. T4-T8 podem rodar em paralelo após T2. T9-T10 dependem de T4-T8. T11 swap A1. T12-T15 fecham loop.

### T1 — Schema v11 + migration (`agent_events` table)

**Goal:** Bump schema v10→v11, criar tabela `agent_events` separada de `chunks`/`kg_*`, registrar migration idempotente.

**DoD:**
- [ ] `migrations/011-agent-events.sql` cria tabela + 3 índices conforme spec §6.1
- [ ] `src/db/schema.ts` atualiza `SCHEMA_VERSION = 11`
- [ ] Migration runner detecta v10 → roda 011 → seta `user_version=11`
- [ ] Rollback documentado: `DROP TABLE agent_events; PRAGMA user_version=10`
- [ ] `audits/check-schema-invariants.sh` ganha invariant #5: `agent_events.kind` CHECK enum válido (`tool_use|user_prompt|session_start|session_end|pre_compact`)
- [ ] No backfill — tabela nasce vazia
- [ ] `nox-mem db-migrate` cria tabela em DB fresh + DB v10 existing sem erro
- [ ] `withOpAudit()` **NÃO** wrapping (migration não-destrutiva; lesson 2026-04-25 não se aplica — sem `DELETE` em chunks)

**Est:** 2h

### T2 — `POST /api/ingest-event` endpoint + async queue

**Goal:** Handler HTTP que responde 202 em <10ms, enfileira event em ring buffer in-memory, retorna `event_id` ULID.

**DoD:**
- [ ] `src/api/ingest-event.ts` — Express handler na porta :18802
- [ ] Schema validation via Zod (kind enum, session_id non-empty, timestamp ISO 8601, payload polimórfico)
- [ ] Response 202 + `{ queued: true, event_id, redaction_count: 0 }` em <10ms p95 (medido em T14)
- [ ] Ring buffer in-memory: 10k slots, FIFO, drop-oldest com `queue_overflow_24h` counter
- [ ] 400 em schema inválido; 413 em payload >256KB (truncate + warning header); 503 em queue >80% (Retry-After: 2)
- [ ] Hard-block paths server-side: rejeita 400 + audit log se `payload.tool_input.file_path` match em `~/.ssh/*`, `*.env`, `*credentials.json`, `~/.openclaw/.env`
- [ ] Telemetry counter increment por kind (em-process, flush periódico no T13)
- [ ] Handler NÃO chama `redact()` direto — só enfileira raw + flag pra worker

**Est:** 3h

### T3 — Worker drain loop

**Goal:** Async worker que polla ring buffer, aplica `redact()`, INSERT em `agent_events`, atualiza counters.

**DoD:**
- [ ] `src/lib/events/worker.ts` — setInterval 250ms OR batch 100 events (whichever first)
- [ ] Pipeline: pop event → `redact(payload_strings)` → path scrub layer 2 → INSERT `agent_events`
- [ ] Project routing: `cwd` → `project_slug` via `agent-orchestrator.yaml` lookup; fallback = `basename(cwd)`
- [ ] Graceful shutdown: `process.on('SIGTERM')` flush remaining ring buffer antes de exit (TimeoutStopSec=10s no systemd unit)
- [ ] Worker insert latency <20ms/event p95 (T14 mede)
- [ ] Errors em redact ou INSERT NÃO travam worker — log + skip, increment `worker_errors_24h`
- [ ] **Uses mock redact** (delete in T11)

**Est:** 3h

### T4 — Hook script `postToolUse.sh`

**Goal:** Shell script que lê JSON stdin do Claude Code, transforma pro schema P2, POST async pra `/api/ingest-event`, fallback file se API down.

**DoD:**
- [ ] `hooks/postToolUse.sh` (repo) — POSIX-compatible, sem bashisms exclusivos
- [ ] Lê stdin JSON via `jq -r` (assume `jq` ≥1.6 — preflight em `connect`)
- [ ] Skip se `tool_name` ∈ `NOX_HOOKS_SKIP_TOOLS` CSV
- [ ] Skip se `tool_name` ∈ {`TodoWrite`, `NotebookEdit`}
- [ ] Read `NOX_API_REACHABLE` de `~/.nox-mem/state.env`; se `=0` → direto pro fallback file
- [ ] `curl --max-time 1 -fsSL -X POST` em background com `&` + `disown`
- [ ] Fallback file: append JSONL line em `~/.nox-mem/pending-events.jsonl` se curl preflight falha
- [ ] Wrap completo em `{ ... } 2>>~/.nox-mem/hooks-err.log` + **sempre `exit 0`** (nunca bloquear agente)
- [ ] shellcheck pass clean

**Est:** 2h

### T5 — Hook script `sessionStart.sh`

**Goal:** Preflight health check (1×/sessão), escreve `state.env`, opcional inject context via stdout.

**DoD:**
- [ ] `hooks/sessionStart.sh`
- [ ] `curl --max-time 0.5 :18802/api/health` — 200 → `NOX_API_REACHABLE=1`; fail → `=0`
- [ ] Write `~/.nox-mem/state.env` com `NOX_API_REACHABLE` + `NOX_SESSION_ID` derivado conforme §8.1 da spec
- [ ] State file TTL 10min (timestamp na primeira linha; demais hooks checam mtime)
- [ ] POST event `kind=session_start` async (mesmo padrão T4)
- [ ] **Opcional v1.0:** stdout com top-K chunks via `nox-mem search` (gate por `NOX_HOOKS_INJECT_CONTEXT=1`, default off — reduce risco de poluir contexto CC)
- [ ] shellcheck pass

**Est:** 1.5h

### T6 — Hook script `userPromptSubmit.sh`

**Goal:** Captura intent humano (prompt cru), respeita `NOX_HOOKS_PROMPT_SAMPLE` rate.

**DoD:**
- [ ] `hooks/userPromptSubmit.sh`
- [ ] Sample rate via `$RANDOM` vs `NOX_HOOKS_PROMPT_SAMPLE` (float 0-1 default 1.0)
- [ ] Skip se `user_prompt` ∉ `NOX_HOOKS_KINDS` CSV
- [ ] POST event `kind=user_prompt` com `payload.prompt_text` + `payload.prompt_tokens` (estimado por wc -w × 1.3)
- [ ] shellcheck pass

**Est:** 1h

### T7 — Hook script `stop.sh`

**Goal:** Flush session summary, marca session_end, dispara KG extraction async (out of scope v1 trigger; placeholder).

**DoD:**
- [ ] `hooks/stop.sh`
- [ ] POST event `kind=session_end` com `payload.tool_use_count` (count desde sessionStart via state.env counter) + `duration_total_ms`
- [ ] Clear `~/.nox-mem/state.env` (next session re-bootstraps)
- [ ] shellcheck pass

**Est:** 1h

### T8 — Hook script `preCompact.sh`

**Goal:** Captura snapshot pré-compact (raro mas crítico).

**DoD:**
- [ ] `hooks/preCompact.sh`
- [ ] POST event `kind=pre_compact` com `payload.transcript_excerpt` (truncate 256KB cap server-side T2)
- [ ] `payload.tokens_to_compact` se disponível no stdin JSON
- [ ] shellcheck pass

**Est:** 1h

### T9 — `nox-mem connect claude-code` command

**Goal:** Instala hooks em `~/.claude/settings.json` (ou `--project` em `.claude/settings.json`) com backup + deep merge sem replace.

**DoD:**
- [ ] `src/cli/connect-claude-code.ts` registra subcommand
- [ ] Flags: `--global` (default), `--project`, `--dry-run`, `--force`, `--refresh`
- [ ] Backup atômico antes de mexer: `settings.json.nox-mem-backup-<ts>.json` (perms 0600)
- [ ] Deep merge: append em `hooks.*` arrays com `_owner: "nox-mem"` tag; **nunca** replace user entries
- [ ] Matcher conflito → append novo entry com matcher distinto, deixa user's intacto
- [ ] `--dry-run` imprime diff colorido (`diff -u backup current`)
- [ ] Install scripts: copia `hooks/*.sh` repo → `~/.nox-mem/hooks/` + `chmod +x`
- [ ] Test ping: fake `kind=session_start` POST → verifica 202 → reporta success
- [ ] Confirma interativo (a menos que `--force`)
- [ ] Print reverse command + backup path
- [ ] Idempotent: re-rodar não duplica entries (detect via `_owner: nox-mem` marker)

**Est:** 3h

### T10 — `nox-mem disconnect claude-code` command

**Goal:** Reverte installation; remove só nox-mem entries; deixa scripts pra forensics.

**DoD:**
- [ ] `src/cli/disconnect-claude-code.ts` registra subcommand
- [ ] Lê `settings.json` → remove todo entry com `_owner: "nox-mem"`
- [ ] Backup antes: `.nox-mem-backup-disconnect-<ts>.json`
- [ ] **Não** remove `~/.nox-mem/hooks/` (user roda `rm -rf` se quiser)
- [ ] Flag `--purge` (opt-in) também limpa `~/.nox-mem/` inteiro
- [ ] Print success + restore command (`mv backup back`)

**Est:** 1.5h

### T11 — Replace mock redact with real A1

**Goal:** Swap import do mock pelo real `redact()` da A1 (PR #5 merged).

**DoD:**
- [ ] `src/lib/events/worker.ts` substitui `import { redact } from './redact-mock'` por `import { redact } from 'src/privacy/filter'`
- [ ] `src/lib/events/redact-mock.ts` deletado
- [ ] CI grep gate: `grep -r 'redact-mock' src/ tests/` retorna zero matches
- [ ] Verifica contract: `redact("hello sk-test-12345")` retorna `{ text: "hello <private>", redaction_count: 1 }` (assume A1 redact pattern)
- [ ] Integration test: POST event com known secret → query `agent_events` → `redaction_count > 0` + `payload_json` sem secret
- [ ] Re-runa T2/T3 tests c/ real redact (mock fix anything que assumia 0)

**Est:** 1h (mostly verification)

### T12 — Local fallback file drain

**Goal:** Quando API down, hooks escrevem `~/.nox-mem/pending-events.jsonl`. Cron drena de volta quando API volta.

**DoD:**
- [ ] `src/cli/ingest-events-drain.ts` — comando `nox-mem ingest-events-drain --batch 500`
- [ ] `flock` no file lock pra evitar double-drain
- [ ] Atomic rotate: `tmp + mv` após batch drained
- [ ] Retry 3× per line com exponential backoff
- [ ] Cap 50MB → rotate `.1`, `.2`; alert Discord se total >200MB (signal API quebrada há dias)
- [ ] Cron entry `*/5 * * * *` documented em `docs/CONVENTIONS.md` §cron
- [ ] Test: kill API → 100 events vão pro file → restart API → drain → 100 events em `agent_events`

**Est:** 2h

### T13 — Telemetry per kind/session/project

**Goal:** Exposed em `/api/health.hooks` — counters sem content.

**DoD:**
- [ ] `src/api/health.ts` ganha bloco `hooks` conforme spec §11.1
- [ ] Counters: `events_24h.{kind}`, `events_7d.{kind}`, `redaction_count_24h`, `pending_file_size_bytes`, `queue_depth_now`, `queue_overflow_24h`, `last_event_at`
- [ ] Aggregation query no `agent_events` (24h + 7d window via timestamp BETWEEN)
- [ ] **Zero content** exposed — só counters numéricos
- [ ] Dashboard panel adicionado em `agent-hub-dashboard` (out of scope v1 build — documentar)
- [ ] Test: 10 fake events INSERT → `/api/health.hooks.events_24h.tool_use` retorna 10

**Est:** 1.5h

### T14 — Tests (shellcheck + bats + integration + e2e + privacy regression)

**Goal:** Cobertura completa per spec §12.

**DoD:**
- [ ] **shellcheck CI gate** — todos `hooks/*.sh` pass
- [ ] **bats-core** em `tests/hooks/`:
  - `postToolUse-emits-correct-payload.bats`
  - `fallback-file-on-api-down.bats`
  - `kind-filter-respected.bats`
  - `skip-tools-respected.bats`
  - `health-check-flags-state.bats`
- [ ] **Integration** em `tests/api/ingest-event.test.ts`: schema validation, async queue, hard-block paths, redaction wiring, backpressure header
- [ ] **E2E** em `tests/e2e/claude-code-hooks-flow.sh`: `connect --project --force` em temp dir → headless CC session → 5 scripted prompts → verify DB counts
- [ ] **Performance bench** `scripts/bench-hooks.sh`: 1000× postToolUse fake → p95 <100ms gate
- [ ] **Privacy regression** `tests/privacy/hooks-redact.test.ts`: 20 fixtures known-bad → grep adversarial em `agent_events.payload_json` → zero matches em secret regex
- [ ] CI configurado pra rodar shellcheck + bats + ts tests (e2e gated por `RUN_E2E=1`)

**Est:** 4h

### T15 — Docs

**Goal:** README + CLAUDE.md + HANDOFF refletindo P2 entregue.

**DoD:**
- [ ] `README.md` §Quick Start ganha bloco "Auto-capture conversations" com `nox-mem connect claude-code`
- [ ] `CLAUDE.md` §Interfaces atualizado: 28+ CLI cmds (+connect, +disconnect, +ingest-events-drain); HTTP API ganha `/api/ingest-event` + `/api/health.hooks`
- [ ] `docs/HANDOFF.md` próxima ação: "P2 entregue. Próximo: P4 connect IDE generalizar OR crystallize-events spec"
- [ ] `docs/DECISIONS.md` registra D-P2 (decisões implementation: mock-first, 5 hooks v1, retention 30d)
- [ ] `docs/RUNBOOKS.md` ganha §"P2 hooks debug" — `tail -f hooks-err.log`, query `agent_events`, drain manual
- [ ] `docs/CONVENTIONS.md` §cron adiciona drain `*/5 * * * *`

**Est:** 1.5h

---

## 4. File Structure

```
memoria-nox/
├── hooks/                              # NEW — repo source for hook scripts
│   ├── sessionStart.sh
│   ├── userPromptSubmit.sh
│   ├── postToolUse.sh
│   ├── stop.sh
│   ├── preCompact.sh
│   └── lib/
│       ├── common.sh                   # send_event(), fallback_log()
│       └── session-id.sh               # session_id derivation
│
├── src/
│   ├── api/
│   │   ├── ingest-event.ts             # NEW — POST /api/ingest-event handler
│   │   └── health.ts                   # MODIFIED — add hooks.* block (T13)
│   │
│   ├── lib/events/                     # NEW — server-side events module
│   │   ├── queue.ts                    # in-memory ring buffer (10k slots)
│   │   ├── worker.ts                   # async drain (250ms or batch 100)
│   │   ├── paths.ts                    # path scrub layer 2 + hard-block
│   │   ├── redact-mock.ts              # DELETED in T11
│   │   └── types.ts                    # AgentEvent, EventKind enum
│   │
│   ├── cli/
│   │   ├── connect-claude-code.ts      # NEW — T9
│   │   ├── disconnect-claude-code.ts   # NEW — T10
│   │   └── ingest-events-drain.ts      # NEW — T12
│   │
│   └── db/
│       └── schema.ts                   # MODIFIED — SCHEMA_VERSION = 11
│
├── migrations/
│   └── 011-agent-events.sql            # NEW — T1
│
├── tests/
│   ├── hooks/                          # NEW — bats-core
│   ├── api/ingest-event.test.ts        # NEW
│   ├── e2e/claude-code-hooks-flow.sh   # NEW
│   └── privacy/hooks-redact.test.ts    # NEW
│
├── scripts/
│   └── bench-hooks.sh                  # NEW — T14
│
└── installed at runtime (NOT in repo):
    ~/.nox-mem/
    ├── hooks/                          # copy of repo hooks/ (chmod +x)
    ├── lib/                            # copy of repo hooks/lib/
    ├── pending-events.jsonl            # fallback queue
    ├── state.env                       # session_id + NOX_API_REACHABLE
    ├── config.env                      # user-edited env vars
    └── hooks-err.log                   # error sink
```

---

## 5. Schema v11 Delta — `agent_events` CREATE

`migrations/011-agent-events.sql`:

```sql
-- Schema v10 → v11: agent_events table for P2 hooks auto-capture
-- Separate from chunks/kg_* (no FTS5, no vec) — session-scoped raw signal
-- Retention 30d default; crystallize path documented in spec §6.3 (out of scope v1)

BEGIN;

CREATE TABLE IF NOT EXISTS agent_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_uuid TEXT NOT NULL UNIQUE,                    -- ULID, e.g. "evt_01HXYZ..."
  session_id TEXT NOT NULL,
  project_slug TEXT NOT NULL,
  kind TEXT NOT NULL CHECK(kind IN (
    'tool_use', 'user_prompt', 'session_start', 'session_end', 'pre_compact'
  )),
  timestamp TEXT NOT NULL,                            -- ISO 8601
  cwd TEXT,
  payload_json TEXT NOT NULL,                         -- redacted JSON blob
  redaction_count INTEGER NOT NULL DEFAULT 0,
  ingested_at TEXT NOT NULL DEFAULT (datetime('now')),
  consolidated_chunk_id INTEGER,                      -- FK → chunks.id (after crystallize, v1.1)
  retention_days INTEGER NOT NULL DEFAULT 30
);

CREATE INDEX IF NOT EXISTS idx_agent_events_session
  ON agent_events(session_id, timestamp);

CREATE INDEX IF NOT EXISTS idx_agent_events_project
  ON agent_events(project_slug, kind, timestamp);

-- Partial index for unconsolidated events (crystallize cron query target)
CREATE INDEX IF NOT EXISTS idx_agent_events_consolidation
  ON agent_events(consolidated_chunk_id)
  WHERE consolidated_chunk_id IS NULL;

PRAGMA user_version = 11;

COMMIT;
```

**Rollback (manual; v1 no automated downgrade):**
```sql
BEGIN;
DROP INDEX IF EXISTS idx_agent_events_consolidation;
DROP INDEX IF EXISTS idx_agent_events_project;
DROP INDEX IF EXISTS idx_agent_events_session;
DROP TABLE IF EXISTS agent_events;
PRAGMA user_version = 10;
COMMIT;
```

**Invariant adicionado em `audits/check-schema-invariants.sh` (T1 DoD):**
```sql
-- Invariant #5: agent_events kind enum constraint
SELECT CASE
  WHEN COUNT(*) = 0 THEN 'OK'
  ELSE 'FAIL: invalid kind in agent_events'
END
FROM agent_events
WHERE kind NOT IN ('tool_use','user_prompt','session_start','session_end','pre_compact');
```

---

## 6. Privacy — 5 Layers (Order Matters)

Defesa em camadas. Order is **load-bearing**: failure em uma layer cai pra próxima.

| # | Layer | Where | What it does | When |
|---|---|---|---|---|
| 1 | **A1 `redact()`** | Worker (T3), pre-INSERT | Regex passes em `payload.*_text`, `prompt_text`, `tool_output`, `command`. Substitui matches por `<private>`. Increment `redaction_count` per match. | Async server-side. Fonte única de verdade pra patterns sensíveis. |
| 2 | **Path scrub** | Worker (T3), post-redact | Normaliza `/Users/<user>/` → `~/`, `/root/.openclaw/` → `${OPENCLAW_HOME}/`, UUIDs em paths → `<uuid>`, hostnames internos → `<vps-host>`. | Após A1 redact. Cosmetic/portability, não dependeu de regex de secret. |
| 3 | **Kind-level opt-out** | Hook script (T4-T8), pre-POST | `NOX_HOOKS_KINDS` CSV permite skip de kinds inteiros (ex: drop `user_prompt` se Toto quiser preservar intent crua). | Client-side. Event não chega no servidor. |
| 4 | **Per-tool opt-out** | `postToolUse.sh` (T4), pre-POST | `NOX_HOOKS_SKIP_TOOLS` CSV (ex: `WebFetch,Read`) skip antes do POST. | Client-side. Tool-granular. |
| 5 | **Hard-block paths** | API handler (T2), pre-queue | Rejeita 400 + audit log se `payload.tool_input.file_path` match em `~/.ssh/*`, `~/.aws/*`, `~/.gnupg/*`, `*.env`, `*credentials.json`, `*secrets.{json,yaml,yml}`, `~/.openclaw/.env`. | Server-side last-line defense. Audit log mostra tentativa. |

**Failure modes mapped:**
- L1 falha (regex FN em A1) → L5 ainda bloqueia se path conhecido → audit log alerta
- L2 falha → não-secret leak (path apenas), aceitável
- L3/L4 falham → event chega servidor, L1+L5 ainda aplicam
- L5 falha → secret em DB → mitigação: `nox-mem scrub-events --re-redact` retroativo após A1 update (out of scope v1; documentar em §risks)

---

## 7. Performance Budget

| Métrica | Target | Hard Limit | Onde mede |
|---|---|---|---|
| Hook script duração total | <50ms p95 | 100ms p95 | T14 `bench-hooks.sh` |
| Curl POST fire-forget | <30ms | 1000ms (`--max-time 1`) | Hook fire-and-forget c/ `&` + `disown` |
| API handler 202 response | <10ms p95 | 50ms | T14 integration test |
| Worker redact+INSERT | <20ms/event p95 | n/a (async) | T14 worker bench |
| Ring buffer headroom | <80% | 100% (drop-oldest + Retry-After header) | T13 telemetry |

**Key invariant:** Hook script é **fire-and-forget**. `curl ... &` + `disown` + `exit 0`. Worst case latência percebida = bash startup + jq parse ≈ 20-30ms. Network slow ou API down não bloqueia turn.

**Why API handler <10ms:** 202 deve ser **antes** de qualquer redact/INSERT. Pipeline real (redact, path scrub, INSERT) roda no worker — invisível ao hook.

---

## 8. Session ID Strategy

**Derivação (precedence order, top wins):**

```
session_id = NOX_SESSION                                   # env override (highest)
           OR cc_session_uuid from hook JSON stdin         # native CC session
           OR "${hostname}-${ppid}-$(date +%s)"            # fallback
```

**Prefixo machine:** `lab-` (constante v1) → `lab-<hostname>-<cc_session_uuid>`. v2 abre cross-machine.

**State file pattern** (reuse de lesson `feedback_cli_api_session_id_sync_needs_env_override.md`):

1. `sessionStart.sh` (T5) escreve `session_id` em `~/.nox-mem/state.env` **uma vez** por sessão CC
2. Demais hooks (T4, T6, T7, T8) leem `state.env` **read-only**
3. Sai do parent-shell-dependent derivation — hooks em CC podem rodar em ppid variável

**`NOX_SESSION` override:** documentado pra debug + CI (`NOX_SESSION=test-run-XYZ` força ID determinístico em e2e tests).

---

## 9. Tests Plan + Overall DoD

### 9.1 Test matrix

| Layer | Tool | Coverage target | T# |
|---|---|---|---|
| Shell syntax | shellcheck | 100% scripts | T14 |
| Hook unit | bats-core | 5 scripts × 3+ cases each | T14 |
| API integration | Vitest/Jest | handler, queue, worker, hard-block | T14 |
| End-to-end | bash + headless CC | full flow connect→capture→query | T14 |
| Performance | bench script | p95 <100ms gate | T14 |
| Privacy regression | TS + fixtures | 20 known-bad secrets, zero leak | T14 |

### 9.2 Definition of Done — P2 Implementation Complete

1. **Schema v11 migrated** in fresh DB + DB v10 existing; invariant check #5 passes (T1)
2. **5 hook events ativos** (SessionStart, UserPromptSubmit, PostToolUse, Stop, PreCompact) capturando eventos em `agent_events` com **real A1 `redact()`** wired (T11 verify)
3. **Endpoint `POST /api/ingest-event`** responde 202 em <10ms p95, enfileira async, redacta server-side, INSERT em <20ms p95 (T14 measured)
4. **Fallback file** drena via cron quando API volta; queue overflow não perde eventos; alert Discord se >10MB (T12)
5. **Telemetria `/api/health.hooks`** exposed com counters por kind/session/project, **zero content** (T13)
6. **`nox-mem connect claude-code` reversível** via `disconnect` — backup automático, deep merge sem replace, idempotent (T9 + T10)

**Não DoD (v1.1 backlog):** crystallize automático events→chunks, captura StopFailure, dashboard panel completo, hooks Cursor/Codex (P4 covers).

---

## 10. Risks + Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **Hook failure cascade** (jq bug, syntax error) bloqueia Claude Code | Low | **High** (UX broken) | `exit 0` no fim de TODOS scripts. shellcheck CI gate (T14). Wrap em `{ ... } 2>>hooks-err.log`. |
| **Privacy regex false negative** (A1 deixa secret passar) | Med | **Critical** (key leak) | (a) Hard-block layer 5 server-side; (b) audit log `redaction_count`; (c) regression test 20 fixtures (T14); (d) retroactive `nox-mem scrub-events --re-redact` pós-A1 patch |
| **session_id mismatch** entre hooks → eventos quebrados | Med | Med | State file `~/.nox-mem/state.env` write-once por sessionStart; demais hooks read-only. Pattern validated em CLI+API sync. |
| **API restart drops in-memory queue** | Med | Med | (a) Fallback file kick-in via preflight; (b) graceful shutdown handler flush antes SIGTERM; (c) systemd `TimeoutStopSec=10s` |
| **Settings.json merge corrompe user hooks** | Low | High | Backup atômico pre-merge; deep merge nunca replace, só append c/ `_owner: "nox-mem"` tag; `--dry-run` documentado primeiro install; `disconnect` 100% reversível |
| **Volume explode** (4h session × 500 tool calls × 30d = 60k events/mo) | High | Med | Retention 30d cron cleanup; `agent_events` separa de `chunks` (não polui FTS5/vec); telemetry alerta >500k events |
| **Mock redact stays in main pós-T11** | Med | High | CI grep gate em T11 DoD: `grep -r 'redact-mock' src/ tests/` → zero matches blocks merge |
| **Claude Code muda hook schema** entre versões | Low | High | `nox-mem connect claude-code` faz test ping (T9); `nox-mem doctor --claude-code` reporta CC version + hook compat; BLOCKED.md se Anthropic deprecar `command` hook type |
| **A1 contract muda pós-merge PR #5** | Low | Med | T11 swap re-roda integration tests; defesa via mock-first dev em T1-T10 (mudança = 1-line patch em worker.ts) |

---

## 11. Timeline Estimate

| Phase | Tasks | Hours |
|---|---|---|
| Foundation | T1, T2, T3 | 8h |
| Hook scripts | T4, T5, T6, T7, T8 | 6.5h |
| Install/uninstall | T9, T10 | 4.5h |
| Wire A1 + fallback | T11, T12 | 3h |
| Telemetry + tests | T13, T14 | 5.5h |
| Docs | T15 | 1.5h |
| **Total** | **15 tasks** | **~29h (range 25-30h)** |

**Recommended sprint shapes:**
- **1 engineer sequential:** ~4 working days (8h × 4)
- **Swarm (2-3 executors parallel):** ~2 days
  - After T1: T2 + T3 parallel
  - After T3: T4 + T5 + T6 + T7 + T8 parallel (5 shell scripts independent)
  - T9 + T12 + T13 parallel after T2 lands
  - T14 split: shellcheck/bats parallel from T4-T8 land; integration after T11
- **Conservative buffer:** ~1 week including review + privacy regression iteration

---

## 12. Open Questions (non-blocking; resolve during impl)

1. **Sample rate adaptativo?** Sessão de 4h pode gerar 500 tool_use. `NOX_HOOKS_PROMPT_SAMPLE=1.0` default; degradar via env se barulhento. **Decisão:** ship 1.0 default; ajustar post-telemetry.
2. **PreCompact: transcript inteiro ou só summary?** Tradeoff completude vs 256KB cap. **Recomendação:** transcript truncado a 256KB (let API decidir, hook envia raw).
3. **Project routing auto-create slug?** Match `cwd` contra `agent-orchestrator.yaml` ou auto-create se não bate? **Recomendação:** auto-create slug = basename(cwd); log warning se não bate (visibility sem block).
4. **Crystallize-events v1.1 schedule?** Events em silo até promote. **Recomendação:** spec separada P2-followup, roadmap pós-validação 4 semanas de captura.
5. **Multi-machine sync?** Laptop + VPS hoje captura separado. **Recomendação:** v1 single-machine; v2 sync via export/import (A2 já lands antes — pattern existe).

---

## 13. References

- **P2 spec:** [PR #4](https://github.com/totobusnello/memoria-nox/pull/4) — `specs/2026-05-17-P2-hooks-autocapture.md`
- **A1 privacy filter (HARD DEP, merged):** [PR #5](https://github.com/totobusnello/memoria-nox/pull/5) — `src/privacy/filter.ts`
- **D41 sprint order:** `docs/DECISIONS.md` §2026-05-18 madrugada item #5
- **P1 kickoff (style reference):** [PR #18](https://github.com/totobusnello/memoria-nox/pull/18)
- **A2 kickoff (parallel-track reference):** [PR #17](https://github.com/totobusnello/memoria-nox/pull/17)
- **Shadow discipline:** `CLAUDE.md` §regras-críticas #5
- **Session ID pattern precedent:** `MEMORY.md` — `feedback_cli_api_session_id_sync_needs_env_override.md`
- **Settings.json persistence note:** `MEMORY.md` — `feedback_openclaw_config_set_required_for_persistence.md` (different domain; CC does NOT daemonize overwrite — documentado em §9.3 spec)

---

**End of kickoff doc.** 15 tasks, ~29h estimate. Engineering can execute T1-T15 sequentially or swarm-parallel after T1+T3 land. A1 dependency dispatched via mock-first dev (T1-T10) + mandatory swap (T11). Schema delta concrete. Privacy 5-layer order load-bearing.
