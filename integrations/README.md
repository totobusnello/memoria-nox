# integrations/

Integration guides and setup templates for memoria-nox (nox-mem).

nox-mem exposes three surfaces that integrate with external tools:

| Surface | What it is | Primary audience |
|---|---|---|
| **MCP server** | 16+ tools via JSON-RPC 2.0 stdio | IDE agents, Claude Code, Cursor, any MCP-compatible client |
| **HTTP API** | REST endpoints on port 18802 | Scripts, dashboards, ChatGPT actions, custom tooling |
| **CLI** | 26+ subcommands (`nox-mem ...`) | Shell scripts, cron jobs, CI, local automation |

---

## Directory map

```
integrations/
├── README.md                  ← you are here
├── ide/
│   ├── README.md             # IDE overview + Tier A/B definitions
│   ├── claude-code.md        # Tier A — deep MCP + P2 hooks + persona
│   ├── cursor.md             # Tier A
│   ├── codex.md              # Tier A
│   ├── cline.md              # Tier B
│   ├── gemini-cli.md         # Tier B
│   ├── opencode.md           # Tier B
│   ├── goose.md              # Tier B
│   ├── windsurf.md           # Tier B
│   ├── continue.md           # Tier B
│   ├── aider.md              # Tier B
│   ├── roo-code.md           # Tier B
│   ├── zed.md                # Tier B
│   └── jetbrains-ai.md       # Tier B
├── mcp/
│   ├── README.md             # MCP install walkthrough
│   ├── tools-reference.md    # All MCP tools documented
│   ├── claude-desktop.md     # MCP setup for Claude Desktop
│   ├── claude-code.md        # MCP setup for Claude Code CLI
│   └── compatible-clients.md # Full compatibility matrix
└── cli/
    ├── README.md             # CLI usage overview
    ├── recipes.md            # 10 common workflows
    └── scripting.md          # Bash/zsh patterns, cron, systemd
```

---

## Quick orientation

**I want to connect my IDE** — start at [`ide/README.md`](ide/README.md). Run `nox-mem connect <ide>` once P4 ships (est. 28–32h impl, spec in `specs/2026-05-18-P4-implementation-kickoff.md`).

**I want to register nox-mem as an MCP server** — start at [`mcp/README.md`](mcp/README.md). Works today with Claude Code, Claude Desktop, and any MCP-compatible client.

**I want CLI recipes** — start at [`cli/recipes.md`](cli/recipes.md) for common workflows, or [`cli/scripting.md`](cli/scripting.md) for cron/systemd templates.

---

## Implementation status

| Area | Status |
|---|---|
| MCP server (16 tools) | Operational |
| HTTP API (`/api/*`) | Operational |
| CLI (26+ commands) | Operational |
| `nox-mem connect <ide>` P4 | Spec ready, implementation pending — est. 28–32h |
| `nox-mem answer` P1 | Implemented (p95 = 101.74ms) |
| Archive export/import A2 | Implemented |
| Real-time viewer P5 | Spec ready, P5a event bus pending |

---

## Minimum requirements

- Node 20+
- `npm install -g nox-mem`
- `GEMINI_API_KEY` set (or swap to OpenAI/local via `NOX_EMBED_PROVIDER`)
- nox-mem-api running: `nox-mem serve` (listens on `NOX_API_PORT`, default 18802)
