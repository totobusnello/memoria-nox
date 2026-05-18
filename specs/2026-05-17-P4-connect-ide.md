# P4 — `nox-mem connect <ide>` — Multi-IDE Bridge

> **Status:** SPEC (não-implementado)
> **Branch:** `overnight/2026-05-17/P4-connect-ide-spec`
> **Pillar Q/A/P:** P4 — Multi-IDE Convergence
> **Tagline:** *"Memória deep pro stack que você usa de verdade, não memória pra qualquer IDE."*
> **Depende de:** P2 (hooks auto-capture spec, Tier A), L3 (cross-agent coordination primitives — leases/signals), A1 (privacy filter)
> **Data:** 2026-05-17

---

## 1. Motivação

O mercado de "memória de agente" convergiu pro padrão MCP nos últimos 6 meses — Cursor, Codex, Claude Code, Cline, Gemini CLI, OpenCode, Goose, Windsurf todos consomem servers MCP. Concorrente direto (agentmemory) reduziu o onboarding a um comando: `agentmemory connect claude-code` faz auto-merge do bloco MCP no settings file do IDE-alvo.

Nox-mem precisa **mirror dessa UX de onboarding** (custo de fricção é tablestakes) **sem commoditizar a proposta de valor**. A diferenciação fica explícita em **duas tiers**:

- **Tier A (premium)** — Claude Code, Cursor, Codex. Integração deep: 16 MCP tools + hooks auto-capture + agent-persona awareness (Atlas/Boris/Cipher/Forge/Lex) + project profile injection + cross-agent leases. Esses 3 IDEs são onde o Toto e o nicho-alvo (engineers usando agentes seriamente) gastam horas/dia.
- **Tier B (basic)** — qualquer IDE MCP-compatible (Cline, Gemini CLI, OpenCode, Goose, Windsurf, Continue, Aider, Roo Code, Zed, JetBrains AI). Só os 16 MCP tools. Sem hooks, sem persona, sem cross-agent. Mensagem: "funciona, mas você não tá no stack que a gente otimiza."

A mensagem comercial fica honesta: **o ROI de nox-mem cresce monotônico com profundidade de integração**. Tier A vale o preço. Tier B é cortesia + funil pra subir tier.

---

## 2. Tier Definitions

### Tier A (premium)

| Capability | Claude Code | Cursor | Codex |
|---|---|---|---|
| MCP server (16 tools) | sim | sim | sim |
| Auto-capture hooks (P2 spec) | 5 lifecycle events (SessionStart, UserPromptSubmit, PostToolUse, Stop, SessionEnd) | equivalent via Cursor Rules + workspace events (a investigar; fallback: hook bridge externo) | 6 hooks (session.start, session.end, user.message, agent.response, tool.before, tool.after) |
| Agent-persona awareness | session_id metadata roteado pra Atlas/Boris/Cipher/Forge/Lex via header `X-Nox-Agent` | mesmo | mesmo |
| Project profile injection | SessionStart hook chama `/api/profile?cwd=<project>` → top concepts/files/KG entities → injetado no system prompt | Cursor Rule auto-load equivalent | Codex session.start hook |
| Cross-agent leases (L3) | `nox_mem_lease` tool reserva recurso (file/concept), broadcasts via signal channel | mesmo | mesmo |
| Persona auto-selection | hint: cwd + branch + recent files → infere persona; user override via `--agent atlas` | mesmo | mesmo |

> **Dependência crítica:** Tier A pressupõe P2 (hooks spec) e L3 (coordination primitives) já mergeados. Se P2/L3 atrasarem, Tier A IDEs caem temporariamente pra "Tier A-shallow" (MCP-only, sem hooks/personas) até o gate fechar.

### Tier B (basic)

| Capability | Tier B |
|---|---|
| MCP server (16 tools) | sim |
| Hooks | **não** |
| Persona awareness | **não** (todas as sessions roteadas pro persona default `nox`) |
| Project profile injection | **não** (user precisa chamar `nox_mem_recall` manual) |
| Cross-agent leases | **não** |

**IDEs Tier B suportados v1:**
- Cline (VS Code extension)
- Gemini CLI
- OpenCode
- Goose
- Windsurf
- Continue (VS Code/JetBrains extension)
- Aider
- Roo Code
- Zed
- JetBrains AI Assistant (via MCP plugin, se disponível na release v1)

---

## 3. CLI Shape

```
nox-mem connect <ide> [--dry-run] [--force] [--scope global|project] [--agent <persona>]
nox-mem connect --list
nox-mem disconnect <ide> [--scope global|project] [--force]
nox-mem connect --verify <ide>     # re-check connection + drift
```

### 3.1 `connect <ide>`

Fluxo:
1. **Detect** — busca o config file do IDE (paths na §4).
2. **Probe** — `localhost:18802/api/health` responde? (sandboxed-client check, §9).
3. **Load** — lê config existente; parseia (JSON/TOML/YAML conforme IDE).
4. **Backup** — escreve `<config>.nox-mem-backup-<ISO8601>.json` (sempre formato JSON normalizado, independente do formato source — facilita diff). **Se backup write falhar, aborta.**
5. **Merge** — deep-merge do bloco `mcpServers` (ou equivalente, §4) + (Tier A) bloco `hooks`.
6. **Confirm** — mostra diff colorido + pede `[y/N]` (skip se `--force`).
7. **Write** — escreve config atualizado (formato preservado).
8. **Manifest** — atualiza `~/.nox-mem/connections.json` (§7).
9. **Health-check** — se IDE rodando, sugere restart; alguns IDEs (Claude Desktop, Cursor) requerem restart obrigatório.

### 3.2 `connect --list`

Output:

```
IDE              Tier   Config Path                                  Connected   Last Sync
---              ----   -----------                                  ---------   ---------
claude-code      A      ~/.config/claude/claude_desktop_config.json  yes         2026-05-17 14:32
cursor           A      ~/.cursor/mcp.json                           yes         2026-05-15 09:11
codex            A      ~/.codex/config.toml                         no          —
cline            B      ~/.vscode/cline_mcp_settings.json            no          —
gemini-cli       B      ~/.gemini/settings.json                      no          —
opencode         B      ~/.config/opencode/opencode.json             no          —
goose            B      ~/.config/goose/config.yaml                  no          —
windsurf         B      ~/.codeium/windsurf/mcp_config.json          no          —
...
```

### 3.3 `disconnect <ide>`

Fluxo:
1. **Load manifest** — pega último backup path + hash.
2. **Drift check** — compara hash atual do config file vs hash registrado. Se divergiu (user editou manual): **diff vs backup + pergunta** se quer restaurar backup (perderia edits) ou só remover bloco nox-mem.
3. **Default action (no drift)** — restaura do backup.
4. **Custom action (drift)** — remove só as chaves `nox-mem` do `mcpServers` e `hooks`, preserva outras edits.
5. **Manifest** — marca disconnected.

### 3.4 `--dry-run`

Mostra diff colorido + paths que seriam escritos. Não muta. Não cria backup.

### 3.5 `--force`

Skip confirmação interativa. Pra automação (scripts de onboarding, instalador Supermem).

### 3.6 `--scope global|project`

Default: `global` (config no home dir). `project` escreve no config local (ex: `<repo>/.cursor/mcp.json`, `<repo>/.codex/config.toml`). Nem todos IDEs suportam project-scoped — `--list` deve mostrar quais (§4 column "Scope").

### 3.7 `--agent <persona>`

(Tier A only) Hard-set persona default da connection. Sem flag, persona é hint-based runtime.

---

## 4. IDE-Specific Configs

### Tier A

| IDE | Config Path (global) | Config Path (project) | Format | MCP Block Key | Hooks Block | Quirks |
|---|---|---|---|---|---|---|
| **claude-code** | `~/.config/claude/claude_desktop_config.json` (Linux) / `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) | n/a (global only) | JSON | `mcpServers` | `hooks` (P2 spec: 5 events) | Restart required. Path differs Linux/macOS/Windows — detect via OS. |
| **cursor** | `~/.cursor/mcp.json` | `<repo>/.cursor/mcp.json` | JSON | `mcpServers` | Cursor Rules (`.cursorrules`) + workspace events — hooks bridge needed (Tier A-shallow se não mergeado) | Restart required. |
| **codex** | `~/.codex/config.toml` | `<repo>/.codex/config.toml` | TOML | `[mcp_servers.nox-mem]` | `[hooks]` table com 6 events | TOML quirks: nested tables, no comments preservation guaranteed (tomlkit recommended). |

### Tier B

| IDE | Config Path (global) | Config Path (project) | Format | MCP Block Key | Quirks |
|---|---|---|---|---|---|
| **cline** | `~/.vscode/cline_mcp_settings.json` (or extension-specific) | n/a | JSON | `mcpServers` | VS Code restart. |
| **gemini-cli** | `~/.gemini/settings.json` | `<repo>/.gemini/settings.json` | JSON | `mcpServers` | Tem CLI próprio `gemini mcp add` — usar SE disponível, fallback file edit. |
| **opencode** | `~/.config/opencode/opencode.json` | `<repo>/opencode.json` | JSON | `mcp` (singular) | Schema versionado — pin compatible version. |
| **goose** | `~/.config/goose/config.yaml` | n/a | YAML | `extensions.nox-mem` | YAML formatting — `ruamel.yaml` round-trip preserve comments. |
| **windsurf** | `~/.codeium/windsurf/mcp_config.json` | n/a | JSON | `mcpServers` | Restart required. |
| **continue** | `~/.continue/config.json` | `<repo>/.continue/config.json` | JSON | `mcpServers` | Schema v2 (2026) — verify version. |
| **aider** | n/a (CLI-based, MCP via `.aider.conf.yml`) | `<repo>/.aider.conf.yml` | YAML | `mcp_servers` | No global; per-project only. |
| **roo-code** | `~/.vscode/roo_mcp_settings.json` | n/a | JSON | `mcpServers` | VS Code fork. |
| **zed** | `~/.config/zed/settings.json` | `<repo>/.zed/settings.json` | JSON (with comments — JSONC) | `context_servers` | JSONC parser required. |
| **jetbrains-ai** | `~/.config/JetBrains/ai-assistant/mcp.json` (tentative — verify v1 release) | n/a | JSON | `mcpServers` | If plugin unavailable v1, mark "experimental". |

> **Bloco MCP shape padrão (JSON):**
> ```json
> {
>   "mcpServers": {
>     "nox-mem": {
>       "command": "nox-mem",
>       "args": ["mcp"],
>       "env": {
>         "NOX_API_PORT": "18802",
>         "NOX_MEM_AGENT_HINT": "auto"
>       }
>     }
>   }
> }
> ```
>
> **TOML equivalent (Codex):**
> ```toml
> [mcp_servers.nox-mem]
> command = "nox-mem"
> args = ["mcp"]
> env = { NOX_API_PORT = "18802", NOX_MEM_AGENT_HINT = "auto" }
> ```
>
> **YAML equivalent (Goose):**
> ```yaml
> extensions:
>   nox-mem:
>     command: nox-mem
>     args: [mcp]
>     env:
>       NOX_API_PORT: "18802"
>       NOX_MEM_AGENT_HINT: auto
> ```

---

## 5. Merge Strategy

**Invariantes:**
1. **NEVER replace whole file.** Sempre deep-merge dentro da key `mcpServers` (ou equivalente).
2. **Backup-first.** Backup write FALHOU → aborta merge. Sem exceção.
3. **Preserve formatting.** JSON: pretty-print 2-space (detect existing indent). TOML: `tomlkit` round-trip. YAML: `ruamel.yaml` round-trip. JSONC (Zed): `jsonc-parser` preserve comments.
4. **Idempotente.** Rodar `connect` 2× não duplica entry. Se `nox-mem` já existe em `mcpServers`, faz overwrite das chaves nox-mem (não merge interno) — assume nova versão é source-of-truth.
5. **Atomic write.** Escreve em `<config>.tmp`, fsync, rename. Nunca write-in-place.

**Per-IDE merger module pattern (futura extensão):**

```
src/connect/
  ├── index.ts              # CLI entry + orchestration
  ├── manifest.ts           # ~/.nox-mem/connections.json
  ├── mergers/
  │   ├── json.ts           # generic JSON merger
  │   ├── jsonc.ts          # Zed (preserve comments)
  │   ├── toml.ts           # Codex
  │   ├── yaml.ts           # Goose, Aider
  │   └── claude-code.ts    # IDE-specific: hooks block + persona env
  ├── detectors/
  │   └── <ide>.ts          # path resolution per IDE
  └── ides.ts               # IDE registry (tier, paths, format, merger)
```

Adicionar novo IDE = adicionar entry em `ides.ts` + (se formato novo) merger module. Sem refactor central.

---

## 6. Detection

`connect --list` probes pra cada IDE registrado:

1. **Config file exists?** — stat path (resolve `~`, `$XDG_CONFIG_HOME`, OS-specific paths).
2. **Already connected?** — parse config, check `mcpServers.nox-mem` (ou equivalent).
3. **Last connect timestamp** — lookup em manifest (§7).
4. **Drift?** — hash atual do config vs hash registrado no manifest. Se diferente: flag `drift` em output.

Concorrência: `--list` é read-only, sem locks.

---

## 7. Local Manifest

**Path:** `~/.nox-mem/connections.json`

**Schema:**

```json
{
  "version": 1,
  "connections": {
    "claude-code": {
      "tier": "A",
      "scope": "global",
      "config_path": "/Users/lab/Library/Application Support/Claude/claude_desktop_config.json",
      "backup_path": "/Users/lab/Library/Application Support/Claude/claude_desktop_config.json.nox-mem-backup-2026-05-17T14:32:11Z.json",
      "connected_at": "2026-05-17T14:32:11Z",
      "last_verified_at": "2026-05-17T20:00:00Z",
      "config_hash_at_connect": "sha256:abc123...",
      "nox_mem_version": "3.7.2",
      "agent_default": "auto"
    }
  }
}
```

**Source-of-truth para `disconnect`:** manifest aponta pro backup file. Se manifest perdido, `disconnect` cai pra "best-effort key removal" (remove `nox-mem` key from `mcpServers`, sem restaurar formatting pristine).

**Drift detection:** `last_verified_at` cron diário (opt-in) re-hash config. Se mudou + diff afeta blocos nox-mem → alert console na próxima sessão CLI.

**Concurrency:** flock no manifest durante write. Multi-IDE connect paralelo é raro mas seguro.

---

## 8. Project vs Global Scope

Default: `global`.

`--scope project` escreve no config project-local. Aplicação:
- **Codex:** `<cwd>/.codex/config.toml`
- **Cursor:** `<cwd>/.cursor/mcp.json`
- **Continue:** `<cwd>/.continue/config.json`
- **OpenCode:** `<cwd>/opencode.json`
- **Aider:** `<cwd>/.aider.conf.yml` (project-only, sem global)
- **Zed:** `<cwd>/.zed/settings.json`
- **Gemini-CLI:** `<cwd>/.gemini/settings.json`

IDEs sem suporte project-scope: erro claro `IDE does not support --scope project, falling back to --scope global; abort?`.

Manifest registra `scope` per-IDE per-project (key: `<ide>@<cwd-hash>`).

---

## 9. Sandboxed Clients

**Problema:** Cursor (Flatpak/Snap), Claude Desktop AppImage, alguns VS Code instalações isoladas — não alcançam `localhost:18802` por sandbox network policy.

**Detection:**
1. Após merge, se IDE running, chamar `nox-mem connect --verify <ide>` (ou pedir user re-prompt manualmente).
2. Verify dispara `nox_mem_health` via MCP from IDE side. Se falhar (timeout 5s) → sandboxed.

**Workarounds sugeridos (output do `--verify`):**
- **`NOX_API_HOST=192.168.X.X`** — usar LAN IP da máquina host (não localhost).
- **Flatpak override:** `flatpak override --user --share=network com.cursor.Cursor`.
- **Force proxy mode:** `NOX_MEM_FORCE_PROXY=1` env — futuro spec, fallback HTTP via STDIO proxy embedded no MCP server.

**Documentação:** errors de probe linkam pra `docs/connect-sandbox-troubleshooting.md` (criar junto com implementação).

---

## 10. Telemetry

**O que captura (opt-in via `NOX_TELEMETRY=1`):**
- `connect.success` — IDE, tier, scope, version. Sem path, sem hash.
- `connect.failure` — IDE, error class (backup_failed/merge_conflict/probe_failed). Sem stacktrace.
- `disconnect` — IDE, scope.
- `drift.detected` — IDE.

**Nunca captura:** content do config, secrets, project paths absolutos.

**Storage:** `~/.nox-mem/telemetry.jsonl` local; opt-in upload futuro (não v1).

---

## 11. Tests Plan

**Fixtures per format** em `tests/fixtures/connect/`:
- `claude-code.empty.json` — config sem nada nox-mem
- `claude-code.with-other-mcp.json` — config com outros MCP servers (ex: filesystem, github)
- `claude-code.already-connected.json` — config com nox-mem v3.6 (testa idempotência + upgrade)
- `codex.empty.toml`, `codex.with-other-mcp.toml`, `codex.with-comments.toml`
- `goose.empty.yaml`, `goose.with-comments.yaml`
- `zed.with-jsonc-comments.jsonc`

**Test matrix:**

| Test | Coverage |
|---|---|
| `connect <ide>` em fixture vazia | merge writes valid config + manifest entry |
| `connect <ide>` em fixture com outro MCP | preserves outros MCPs, adds nox-mem |
| `connect <ide>` 2× (idempotência) | second run no-op ou clean overwrite |
| `disconnect <ide>` sem drift | restaura byte-exact do backup |
| `disconnect <ide>` com drift | preserves user edits, removes nox-mem keys |
| `disconnect <ide>` sem manifest | best-effort key removal funciona |
| `connect --dry-run` | nunca toca disk |
| `connect --scope project` | escreve project path, manifest registra @cwd |
| `connect <ide>` com backup write fail | aborta atomic, config original intacto |
| Format preservation: TOML | comments preservados, indentation match |
| Format preservation: YAML | comments preservados, flow vs block style match |
| Format preservation: JSONC | comments preservados (Zed) |
| Sandboxed probe | `--verify` detecta + sugere workaround |

**Round-trip property test:** randomized fixture → connect → disconnect → byte-compare original. Aceita whitespace diff dentro do bloco nox-mem (idealmente 0 diff fora dele).

---

## 12. Definition of Done (DoD)

1. **Tier A 3-IDE happy path:** `nox-mem connect claude-code && nox-mem connect cursor && nox-mem connect codex` succeeds sem intervenção manual, cada um produz MCP probe verde + (Tier A) hooks registrados.
2. **Disconnect clean:** `nox-mem disconnect <ide>` em qualquer IDE sem drift restaura byte-exact do backup (verificado via `cmp` em CI).
3. **Drift safety:** user manualmente edita config + `disconnect` preserva edits (não restaura backup destrutivamente; pergunta antes).
4. **Sandboxed-client probe:** `--verify` detecta Flatpak Cursor / AppImage Claude Desktop + output mostra workaround correto (LAN IP ou flatpak override command).
5. **Format preservation:** round-trip property test passa em 100% das fixtures (JSON, JSONC, TOML, YAML).

---

## 13. NÃO-fazemos (v1)

- **No auto-update em IDE config schema change.** Se Cursor renomeia `mcpServers` → `mcp_servers` numa release, nós shippamos nova `nox-mem` com merger patched. **NÃO** auto-detectamos schema migration.
- **No Slack/Discord/Telegram "connect"** — esses são chat clients, não IDEs com MCP. Out of scope.
- **No Vim/Emacs/Sublime first-class.** Sem MCP-native plugin maduro v1. Documentar em `docs/connect-manual-mcp.md` como configurar à mão com exemplo de bloco MCP — sem CLI assist.
- **No Windows-specific paths v1.** macOS + Linux only. Windows backlog v1.1 (Claude Desktop Windows config path conhecido, mas WSL vs native quirks merecem session dedicada).
- **No interactive TUI wizard.** Apenas CLI flags. TUI fica P-future.
- **No remote nox-mem connect.** Assume nox-mem local. Connect a remote nox-mem (ex: Toto's VPS) é spec separado (`connect --remote https://...` futuro).

---

## 14. Riscos & Mitigations

| Risco | Severity | Mitigation |
|---|---|---|
| IDE config schema muda (ex: Cursor renomeia chave) | HIGH | Per-IDE merger module isolado em `src/connect/mergers/`. Patch é arquivo único + bump version. CI test fixture per IDE detecta regressão. |
| User edita config manual + `disconnect` apaga edits | HIGH | Drift detection + diff-before-restore + confirmação interativa. `--force` skip risk loga warning. |
| Backup write succeeds mas merge write falha mid-flight | MEDIUM | Atomic write (tmp + rename). Manifest só atualiza após rename success. Se crash entre tmp e rename, original intacto. |
| 2 IDEs com mesmo config path (ex: VS Code + Cline + Roo Code em mesma instância) | MEDIUM | Manifest key inclui IDE name, não só path. Multi-IDE same-path testado em fixture. |
| Sandboxed client falha probe mas user só descobre depois | MEDIUM | `connect` chama `--verify` automaticamente no fim (skip via `--no-verify`). Não-bloqueante (warning, não error). |
| TOML/YAML round-trip lib bug corrompe formatting | LOW | Pin lib versions, snapshot tests em CI, fallback opt-out `--no-preserve-formatting` que escreve canonical format. |
| Manifest corrompido | LOW | Schema versionado (`version: 1`). Reparse-falha → backup manifest + start fresh + log. |
| Persona auto-selection misroute (Atlas em projeto Forge) | LOW (Tier A only) | Hint-based, com user override `--agent`. P2 spec define o algoritmo de hint. |

---

## 15. Open Questions (block-or-defer)

1. **Cursor hooks equivalent** — Cursor não tem hooks API formal (a investigar release notes 2026). Se confirmar ausência: Tier A-shallow pra Cursor (MCP+persona via env, sem auto-capture). Não-bloqueante v1.
2. **JetBrains AI MCP plugin v1 maturity** — checar gate antes do release. Se beta, marcar `experimental` em `--list`.
3. **OpenCode schema version pin** — qual version range suportamos v1? Decidir junto com OpenCode mantenedor (eles têm Discord).
4. **Project-scope manifest key collision** — `<cwd-hash>` é estável se user move repo? Provavelmente não. Aceitar trade-off (drift cria nova entry, antiga marcada stale após 30d).

Nenhum bloqueador. Não criar `BLOCKED.md`.

---

## 16. Sequência de implementação sugerida

1. **Foundation** — `src/connect/ides.ts` registry + manifest module + JSON merger + Claude Code happy path.
2. **Tier A completion** — Cursor + Codex (TOML merger).
3. **Tier B fan-out** — Cline, Gemini-CLI, OpenCode, Goose (YAML merger), Windsurf, Continue, Aider, Roo Code, Zed (JSONC merger).
4. **Verify + sandboxed probe.**
5. **Drift detection cron + `--verify` flag.**
6. **Tests + property tests.**
7. **Docs:** `docs/connect-quickstart.md`, `docs/connect-sandbox-troubleshooting.md`, `docs/connect-manual-mcp.md` (Vim/Emacs).

Estimativa total: 5-7 dias dev (1 dev), distribuído sob gate Tier A first (2 dias) → Tier B opcional incremental.

---

## 17. Referências

- agentmemory README (competitor pattern reference para `connect <ide>` UX)
- P2 spec — hooks lifecycle (dependency)
- L3 spec — cross-agent coordination primitives (dependency)
- A1 spec — privacy filter (dependency)
- `docs/DECISIONS.md` — adicionar entry "P4 Tier A/B split" após merge
- MCP spec: `https://spec.modelcontextprotocol.io/`

---

*FIM SPEC P4. Implementation-ready. NÃO implementar antes de gate P2+L3 merged.*
