# Validation: Claude CLI Backend Re-Attempt — 3 Proposals vs OpenClaw 2026.4.15

Date: 2026-04-22 | Scope: READ-ONLY | Issue ref: openclaw/openclaw#70279

## TL;DR

**All 3 user proposals are redundant.** OpenClaw 2026.4.15 **ships a built-in `claude-cli` backend** (`buildAnthropicCliBackend`) that is auto-registered when a `claude-cli/*` model is used. Declaring `agents.defaults.cliBackends["claude-cli"]` is only necessary to **override** specific fields — and most overrides get **silently mutated** by `normalizeClaudeBackendConfig`.

Recommendation: **Do nothing in config. Just set `model.primary`.** If override is needed, use **Proposal 4** below.

---

## 1. Flag validation table (Claude CLI 2.1.88, empirical)

| Flag | Exists | Notes |
|---|---|---|
| `-p / --print` | yes | "Workspace trust dialog skipped" — known |
| `--output-format {text,json,stream-json}` | yes | Built-in backend uses **`stream-json`** (with `--include-partial-messages --verbose`), NOT `json`. Proposal 1/2/3 use plain `json` — legal per schema but **diverges from built-in** and loses partial-message streaming. |
| `--session-id <uuid>` | yes | **Hard UUID requirement**: `claude --session-id not-a-uuid -p x` → `Error: Invalid session ID. Must be a valid UUID.` OpenClaw generates UUIDs for sessions, so OK — but any human-set session arg **must** be UUID. |
| `--model <alias\|full>` | yes | Accepts both `sonnet` and `claude-sonnet-4-6` per `--help`. Empirically `--model claude-opus-4-7` is **NOT rejected by the CLI** (passes through) but the CLI's known list (`cli.js` grep) stops at `claude-opus-4-6`. OpenClaw's alias map **normalizes `claude-opus-4-7` → `opus`** before passing, so the full string never hits the CLI. |
| `--permission-mode {acceptEdits,bypassPermissions,default,dontAsk,plan,auto}` | yes | **Injected unconditionally** by `normalizeClaudePermissionArgs` if user omits it — hard-coded to `bypassPermissions`. `--dangerously-skip-permissions` (legacy) is **stripped**. |
| `--setting-sources user` | yes | **Force-injected** by `normalizeClaudeSettingSourcesArgs`. Any user-supplied value is overwritten to `user`. |

## 2. Schema alignment — what's redundant / missing / wrong

Built-in `config` (from `/usr/lib/node_modules/openclaw/dist/cli-backend-Sl9e48XC.js`):

```
command: "claude"
args: ["-p","--output-format","stream-json","--include-partial-messages","--verbose",
       "--setting-sources","user","--permission-mode","bypassPermissions"]
resumeArgs: [... + "--resume","{sessionId}"]
output: "jsonl"          # NOT "json"
input: "stdin"           # NOT "arg"
modelArg: "--model"
modelAliases: CLAUDE_CLI_MODEL_ALIASES   # opus/sonnet/haiku, incl claude-opus-4-7
sessionArg: "--session-id"
sessionMode: "always"     # NOT "existing"
sessionIdFields: ["session_id","sessionId","conversation_id","conversationId"]
systemPromptArg: "--append-system-prompt"
systemPromptMode: "append"
systemPromptWhen: "first"
clearEnv: [ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, ANTHROPIC_OAUTH_TOKEN, +others]
serialize: true
```

| Proposal field | Built-in default | Verdict |
|---|---|---|
| `command: "/usr/bin/claude"` | `"claude"` | **OK**, pins absolute path (good). |
| `args: ["-p","--output-format","json"]` | stream-json + perms + sources | **Wrong** — loses partial streaming. Also missing `--permission-mode` / `--setting-sources` will be auto-injected, so end-args differ from what you wrote. |
| `input: "arg"` | `"stdin"` | **Diverges** from built-in. `arg` has `maxPromptArgChars` limit (schema field exists, unset → ARG_MAX risk for long prompts). stdin is safer. |
| `output: "json"` | `"jsonl"` | Built-in parses **jsonl stream-json**. If you switch to `output:"json"`, OpenClaw expects single JSON blob, not stream — **parser mismatch**. |
| `serialize: true` | `true` | Same, redundant. |
| P2: `sessionMode: "existing"` + explicit `sessionArg` | `"always"` + same sessionArg | **"existing" is for Codex**. Claude built-in uses `"always"` (create-or-resume). "existing" may skip creating new sessions and fail on first call. |
| P3: `modelAliases: {claude-sonnet-4-6: "sonnet", claude-opus-4-6: "opus", claude-opus-4-7: "opus"}` | Already in `CLAUDE_CLI_MODEL_ALIASES` | **100% redundant** — all three are already mapped. |
| `workspace` under `agents.defaults` | Set to `/root/.openclaw/workspace` | **Not a `cliBackend` field**; it's OpenClaw workspace root, not CLI cwd. CLI inherits cwd from OpenClaw process. |

**Defaults if omitted**: schema does **not** enforce defaults at JSON-schema layer — defaults live in `buildAnthropicCliBackend()`. User override merges on top, so omitting a field = built-in value is used.

## 3. Risk per proposal vs known failure modes

- **P1 (minimal)**: **Breaks output parsing** (`json` vs `jsonl` stream-json). Dodges session bugs by using `sessionMode` default (`"always"`) only because it omits the field. Still hits root/bypass + sessions.json fallback (config alone doesn't fix those). **Verdict: will fail at first response parse.**
- **P2 (session)**: Adds `sessionMode: "existing"` — **regresses** vs built-in `"always"`, likely reproduces the "silent skip in resolveCooldownDecision" because session creation path is disabled. Worst option.
- **P3 (model mapping)**: Redundant aliases. `claude-opus-4-7` already maps to `opus`; writing it again is a no-op. Does **not** solve any known failure mode.

None of P1–P3 address: (a) root/non-root execution, (b) `sessions.json` rewrite to fallback, (c) `resolveCooldownDecision` silent skip. Those are code-path / env issues, not config.

## 4. Recommended config — Proposal 4

**Option A (recommended): no cliBackends block at all.** Just add the model ref allowlist entry (already present) and flip primary:

```json
{
  "agents": {
    "defaults": {
      "model": { "primary": "claude-cli/claude-sonnet-4-6" },
      "models": {
        "claude-cli/claude-sonnet-4-6": {},
        "claude-cli/claude-opus-4-6": {},
        "claude-cli/claude-opus-4-7": {}
      }
    }
  }
}
```

**Option B (only if command path needs pinning)**: minimal override:

```json
{
  "agents": {
    "defaults": {
      "cliBackends": {
        "claude-cli": { "command": "/usr/bin/claude" }
      },
      "model": { "primary": "claude-cli/claude-sonnet-4-6" }
    }
  }
}
```

Rationale: `normalizeClaudeBackendConfig` + merge semantics use built-in for every omitted field. Anything else we specify we risk misaligning with the jsonl stream-json parser, the `"always"` sessionMode, or the forced `--setting-sources user` / `--permission-mode bypassPermissions` post-normalization.

## 5. What config alone cannot solve (blockers for re-attempt)

1. **Root execution**: `bypassPermissions` is auto-injected, but Claude CLI still refuses to run as root without `IS_SANDBOX=1` env or running as non-root user. Decide one: (a) systemd unit sets `IS_SANDBOX=1`, or (b) create `openclaw` user. Document in the systemd unit, not openclaw.json.
2. **`clearEnv` wipes RelayPlane routing**: built-in `CLAUDE_CLI_CLEAR_ENV` deletes `ANTHROPIC_BASE_URL` and all `ANTHROPIC_*` tokens before exec. This means **RelayPlane proxy (:4100) will NOT be used for claude-cli calls** — the CLI will talk to Anthropic directly via its own OAuth/credentials file. Confirm that is intended (it should be, since claude-cli is the point of the migration) and re-verify RelayPlane still handles non-cli providers.
3. **sessions.json fallback behavior**: needs runtime fix (not config). Add regression test that verifies `sessions.json` is not rewritten with anthropic fallback when claude-cli errors.
4. **`resolveCooldownDecision` silent skip**: needs log instrumentation before retry — add DEBUG logging branch, don't attempt without observability.
5. **`claude-opus-4-7` availability**: CLI's `cli.js` string table lists up to `claude-opus-4-6` only. Alias maps it to `"opus"`, so whatever "latest opus" is server-side gets used. Acceptable but **document that `claude-opus-4-7` is a virtual ref resolving to opus-latest**, not a pinned version.

---

## Evidence sources (VPS paths)

- `/usr/lib/node_modules/openclaw/dist/cli-backend-Sl9e48XC.js` — anthropic backend definition
- `/usr/lib/node_modules/openclaw/dist/cli-backend-gBOMQFPa.js` — codex backend (for comparison, uses sessionMode "existing")
- `/usr/lib/node_modules/openclaw/dist/cli-shared-D-OMKlVw.js` — aliases, clearEnv, permission normalizer
- `/usr/lib/node_modules/openclaw/dist/runtime-schema-BpoRdXIq.js:3940+` — cliBackends JSON schema
- `/usr/lib/node_modules/@anthropic-ai/claude-code/cli.js` — CLI model string table
- `claude --help` (2.1.88) — flag enumeration, session-id UUID requirement
