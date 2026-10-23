# Item 7, pull side: the agent does search — nothing it is asked to do needs the corpus

**2026-10-23.** First measurement of the **pull** side of item 7. Every prior
attempt measured **push** — text placed in the prompt — and all three came back
null: implicit brief use 0 of 9,398 pairs (2026-10-14), R1 rejected on
composition (2026-10-21), and 7b's positive control at 0/10 decisive, which
showed the first action follows the cron prompt and workspace instructions, not
the brief (2026-10-15).

Nobody had ever measured whether an agent *pulls*. The gate on ROADMAP items 4,
6 and 11 is written in those words — "reopens with a real consumer searching" —
so three items were waiting on a question nobody had asked.

## Setup

One agent: **Lex (legal)**. Not a preference — the 2026-10-22 census puts 82.2%
of the graph's evidence and most of the corpus in vault contracts. Lex is the
only agent whose corpus exists; running this with a news or security agent would
test retrieval against an empty corpus and produce an uninterpretable null.

Outcome measured on `search_telemetry.requesting_agent`, not on a transcript:
a tool call either writes a row or it does not. Each step ran in a **fresh
session key**, because the previous turn teaches the agent that the tool exists.

## Steps and result

| step | the prompt | searched? |
|---|---|---|
| **1** capability | names the tool and the MCP server, orders a search | **yes** — 5 results, 2.8 s |
| **1.5** disposition | "look in your memory for X", tool not named | **yes** — 10 results |
| **2A** task needs the corpus | a legal summary of one named matter that exists only in the vault; **no instruction to search** | **yes — 6 searches**, 4–5 results each |
| **2B** control, generic task | explain how an earn-out clause works, in general | **no** — zero tools, answered from its own knowledge |

**The discrimination is clean.** The agent searches when the task requires the
corpus and does not when it does not. That is the correct behaviour, and it is
the opposite of what three null push experiments had made plausible.

## What this re-reads

The zero is real — before this run, `requesting_agent LIKE 'mcp:%'` had **0
rows in the whole table** since the column got a writer on 2026-10-13 — but its
cause was never the one assumed. It is not that the agents cannot search, nor
that they will not. **It is that nothing they are asked to do needs the corpus.**
Lex's heartbeat is 360 min, `lightContext: true`, `target: none`.

> 🔑 Three experiments measured whether memory reaches the agent. None measured
> whether the agent's work has a question in it. A retrieval system with no
> consumer may be failing at the pauta, not at retrieval — and the two are
> indistinguishable from the retrieval side.

This moves item 7 from "does the brief serve?" to a different and answerable
question: **which recurring task of these agents should consult the corpus?**

## Instrument defect found, and it blocks step 3

`requesting_agent` comes back as **`mcp:unknown`** — the surface is recorded,
the agent is not. `mcp-server.ts` already reads `process.env.NOX_AGENT_NAME`,
but the spawned process receives **no** agent, workspace or OpenClaw variable at
all (`/proc/<pid>/environ` checked on all three live processes; `cwd` is `/`),
and the OpenClaw schema accepts `mcp` only at `/properties/mcp`,
`/properties/nodeHost/properties/mcp` and `/properties/commands/properties/mcp`
— **never per agent**. So it cannot be fixed from config.

Consequence: steps 1–2 are safe (one agent, controlled window, timestamp
attributes the rows), but **step 3 — spontaneous traffic across six agents — is
not measurable today**. The route that works is HTTP with `X-Agent-Name`, which
the serving code already reads.

⚠️ Item 2 of the ROADMAP ("telemetry of who searches") is therefore partial: it
separates probe from non-probe, and on the one surface the agents actually use
it can say *MCP* but never *which agent*.

## Limits, declared

- Step 2A names a specific matter the model cannot know, which is the strongest
  possible trigger. It shows the agent searches when the task names something
  only the corpus holds; it does not show it would search for a subtler need.
- One agent, one model (`claude-sonnet-5` via `claude-cli`), one turn per step,
  no replicas. This is a capability and disposition probe, not a rate estimate.
- Every step loaded the tool through `ToolSearch` first, so the tool is deferred
  for these agents. That did not prevent use at any step, but it is untested
  whether it lowers the rate under real load.

Run from `openclaw-vps/infra`; the platform side of the work lives there.
