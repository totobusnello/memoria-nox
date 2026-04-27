# OpenClaw Issue Draft — CLI backend fails silently on root systemd gateway

**Repo:** `openclaw/openclaw`
**Labels (suggested):** `bug`, `cli-backend`, `auth`, `linux-systemd`
**Title:** `claude-cli backend silently skipped on systemd-managed root gateway, never spawns subprocess`

---

## Summary

On a Linux VPS where the OpenClaw gateway runs as `root` under `systemd`, the bundled `claude-cli` CLI backend is listed as primary model but is **silently skipped by the fallback planner** with no `[agent/cli-backend] cli exec` event, no error log, and no actionable diagnostic. Traffic goes straight to `agents.defaults.model.fallbacks[0]`.

Following Ziwen's setup guide (Twitter [2046679352977580437](https://x.com/ziwenxu_/status/2046679352977580437)) and the docs at `/gateway/cli-backends` and `/providers/anthropic` does not produce a working state on this topology.

## Environment

- OpenClaw: `2026.4.15 (041266a)` (global npm install at `/usr/lib/node_modules/openclaw/`)
- Node: `v22.22.2` (wrapper with `--no-warnings`)
- OS: Ubuntu 24.04 (KVM VPS, Hostinger)
- Gateway: systemd service running as `User=root`
- Claude CLI: `2.1.88` at `/usr/bin/claude`, `claude auth status` → `{"loggedIn":true,"authMethod":"oauth_token"}` with `CLAUDE_CODE_OAUTH_TOKEN` env exported
- `/root/.claude/.credentials.json` present (555 bytes, `claudeAiOauth` key)

## Expected

Following the Ziwen video and `/gateway/cli-backends` beginner quickstart, a message in Discord should trigger `[agent/cli-backend] cli exec: provider=claude-cli` and return a response from the local Claude CLI subscription.

## Actual

1. `openclaw models status --json` correctly shows:
   - `providersWithOAuth: ["anthropic (1)", "claude-cli (1)", "openai-codex (2)"]`
   - `allowed` includes all `claude-cli/*` models
   - `default: "claude-cli/claude-sonnet-4-6"`

2. Any agent turn (Discord or `openclaw agent -m "..." --agent main`) produces this fallback decision chain **without** any `[agent/cli-backend]` event:
   ```
   [model-fallback/decision] decision=candidate_failed requested=claude-cli/claude-sonnet-4-6
                             candidate=openai-codex/gpt-5.4 reason=rate_limit
   ```
   Notice: `requested=claude-cli/...` but `candidate=openai-codex/...` — the primary is never attempted.

3. When I briefly got the CLI to *actually spawn* (before adding `IS_SANDBOX=1`), the failure surfaced in logs as:
   ```
   decision=candidate_failed requested=claude-cli/claude-sonnet-4-6
     detail=--dangerously-skip-permissions cannot be used with root/sudo privileges for security reasons
   ```

4. `sessions.json` under `agents/main/sessions/` had cached per-channel `model` values from previous fallbacks (e.g. `gemini-2.5-pro` for a Discord channel) that **override** `agents.defaults.model.primary` silently on subsequent turns. Resetting the file does not survive — the gateway re-writes each session's `model` to whatever candidate `candidate_succeeded` for that turn (so Anthropic fallback re-cements gemini).

## Steps to reproduce

1. Install OpenClaw 2026.4.15 on a Linux host; run as `root` via systemd.
2. Install Claude Code CLI; `claude auth login` with a Pro/Max subscription.
3. Export `CLAUDE_CODE_OAUTH_TOKEN` in the gateway's environment file.
4. In `openclaw.json`, add `agents.defaults.cliBackends.claude-cli` per the quickstart and set `agents.defaults.model.primary = "claude-cli/claude-sonnet-4-6"`.
5. `systemctl restart openclaw-gateway`.
6. Send a message on any channel → agent responds using a fallback model, never the CLI.

## What I tried (none worked)

| Attempt | Outcome |
|---|---|
| Exact config from Ziwen video (`sessionMode: "existing"`, etc.) | Silent skip, no CLI event |
| Add `--allow-dangerously-skip-permissions` to `cliBackends.args` | Silent skip |
| `sessionMode: "always"` / `"none"` | Silent skip |
| Create `anthropic:claude-cli` OAuth profile manually in `auth-profiles.json` (type=oauth, provider=claude-cli) | `claude-cli` shows up in `providersWithOAuth`, still silent skip |
| `Environment=IS_SANDBOX=1` + `Environment=OPENCLAW_LIVE_CLI_BACKEND_PRESERVE_ENV=CLAUDE_CODE_OAUTH_TOKEN` via systemd drop-in | One `cli exec` fired once (spawned `/usr/bin/claude -p --output-format json`), no conclusion log, never repeated |
| Reset `sessions.json` to `{}` | Gateway re-populates with fallback model after each turn |

## Hypothesis

The silent skip is happening in `resolveCooldownDecision` at `dist/model-selection-*.js` (the subagent I delegated to found `:72722-72740` on a nearby hash). When the `claude-cli` candidate is evaluated, something — possibly the root-detection propagated from the Claude CLI failure mode, or a session-level model cache invalidation — causes `type:"skip"` without emitting a user-visible log. The lack of `[agent/cli-backend]` in this path makes operator-side diagnosis impossible.

## Request

1. **Add an `info`-level log** when a CLI backend is skipped pre-dispatch: `[cli-backend/skipped] provider=<> reason=<auth|cooldown|root_detected|...>`.
2. **Document the root/systemd constraint** in `/gateway/cli-backends` — readers running `openclaw gateway` under systemd as root will hit this and have no hint. Suggest either "run as non-root user" or a supported bypass env var.
3. **Stop re-writing `sessions.json` with the fallback model** when the primary isn't even attempted — at minimum gate that write behind `candidate_succeeded` on the primary ref.
4. (Optional) Expose `cliBackends.allowRoot: true` (or similar) that adds the correct flags to the child process so operators can opt-in.

## Logs snippet (sanitized)

```
2026-04-22T12:00:00 [cron] payload.model 'gemini/gemini-2.5-flash-lite' not allowed, falling back to agent defaults
2026-04-22T12:00:00 [agent/cli-backend] cli exec: provider=claude-cli model=sonnet promptChars=381
(no further claude-cli log; ~68s later graph-memory recall runs as if turn finished via another provider)

2026-04-22T12:00:22 [model-fallback/decision] decision=candidate_failed requested=claude-cli/claude-sonnet-4-6
                     candidate=openai-codex/gpt-5.4 reason=rate_limit detail=...
```

Happy to share more logs or run diagnostic commands — please file a triage path.

---

**cc:** @steipete (OpenClaw maintainer)
