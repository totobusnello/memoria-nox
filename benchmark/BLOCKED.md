# BLOCKED — what we cannot run on this dev box

This file enumerates the dependencies that prevent `benchmark/generate-comparison.ts`
from producing a live, publishable `COMPARISON.md` from the current local
environment. Each blocker has an explicit unblock action and an interim
fallback.

> **Status (2026-05-18):** scaffold only. No LIVE results yet. Default
> `collect-competitor-data.ts` runs are stubs (no API quota used).

---

## Blocker tree (top → leaf)

### B1. Q1 + Q2 + Q3 numeric outputs must exist

| dep | status | unblock |
|---|---|---|
| `eval/locomo/results/*.json` | scaffolded (PR #6); not yet run live | run on VPS with GEMINI key + budget |
| `eval/longmemeval/results/*.json` | scaffolded (PR #11); not yet run live | run on VPS with GEMINI key + budget |
| `eval/latency/results/*.json` | scaffolded (PR #12); not yet run live | run on VPS to remove dev-box CPU noise |

**Fallback:** none. Without our own numbers, there is no comparison to publish.

### B2. VPS environment for competitor installs

Several competitors require systems that this dev box does not run:

| competitor | what it needs | where |
|---|---|---|
| agentmemory | proprietary `iii-engine` daemon | ssh root@VPS, docker |
| mem0 | Python 3.11 + optional Qdrant | ssh root@VPS, docker |
| Letta / MemGPT | Postgres + Qdrant + Docker compose | ssh root@VPS, docker |
| Zep | Postgres + Docker compose | ssh root@VPS, docker |
| Memanto | Python 3.11 + Moorcheh API key | dev box can hit if budget approved |
| `MEMORY.md` | Claude Code installed | already on dev box |
| nox-mem | local + Gemini key | already on dev box |

**Unblock:** provision these services on the existing Hostinger VPS (path
`/root/.openclaw/workspace/benchmarks/`) with their docker-compose stacks.
Keep them firewalled from the production gateway and DB.

**Fallback:**
- For Memanto: if budget never approved, cite the upstream README's R@5
  claim and disclose it in the **Honest caveats** section as
  "vendor-reported, not independently measured".
- For agentmemory iii-engine: if license blocks, fall back to the
  vendor-reported 95.2% R@5, with the same disclosure.
- Do **not** publish a vendor-reported number as if we measured it.

### B3. API keys + budget

| key | needed for | budget guard |
|---|---|---|
| GEMINI_API_KEY | nox-mem ingest + retrieve + LongMemEval judge | already provisioned (flash-lite) |
| OPENAI_API_KEY | mem0, Letta default embedders | new spend; set NOX_BENCHMARK_BUDGET_USD |
| ANTHROPIC_API_KEY | optional alternative composer | optional |
| MOORCHEH_API_KEY | Memanto SaaS | requires account + budget |
| ZEP_API_KEY | optional Zep Cloud measurement | optional |

**Unblock:**
1. Decide budget cap. Suggested: $50 for full run (mostly OpenAI embeddings
   for mem0 + Letta and Gemini judge calls for LongMemEval).
2. Set `NOX_BENCHMARK_BUDGET_USD=<cap>` and `NOX_BENCHMARK_LIVE=1` in the
   VPS env.
3. Provision the keys above into `/root/.openclaw/.env`.

### B4. Per-competitor adapters

`benchmark/collect-competitor-data.ts` LIVE mode dispatches to
per-competitor adapter scripts (`benchmark/adapters/<name>.ts`). These do
not yet exist. Scaffold only.

| adapter | locomo | longmemeval | latency |
|---|---|---|---|
| nox-mem | wire to existing `eval/locomo/run.ts` (`--cli` mode) | wire to existing `eval/longmemeval/run.ts` | wire to `eval/latency/src/runner.ts` |
| agentmemory | new Python adapter | new Python adapter | new Node subprocess wrapper |
| mem0 | new Python adapter | new Python adapter | new Python subprocess wrapper |
| Memanto | new Python adapter | new Python adapter | new Python subprocess wrapper |
| Letta | new HTTP adapter | new HTTP adapter | new HTTP wrapper |
| Zep | new Python adapter (Zep SDK) | new Python adapter | new SDK wrapper |
| MEMORY.md | new filesystem adapter | new filesystem adapter | new filesystem wrapper |

**Unblock:** implement adapters one-by-one. nox-mem first (it already has
the runner). Then mem0 (most widely used competitor). Then Letta + Zep.
Then agentmemory + Memanto (depend on B2/B3).

### B5. Statistical power for the gate

The publication gate requires:

- LoCoMo R@5: nox-mem ≥ best competitor − 0.5pp.
- LongMemEval acc: nox-mem ≥ best competitor − 0.5pp.
- p95 latency search.medium: nox-mem ≤ best competitor + 5ms.

At our default sample sizes (LoCoMo n≈50/cat, LongMemEval n=80, latency
n=100), the 95% CI on accuracy is ≈ ±5pp and on p95 latency ≈ ±3.9ms.
**Differences within those bands are not statistically meaningful.**

If the live run produces nox-mem within the CI band of a competitor, the
template will reflect "tied". This is by design — see **Honest caveats**
in the template.

**Unblock for tighter CI:** run with n=200 per LoCoMo category and n=400
for LongMemEval. Cost ~4x.

---

## Interim publication policy

While the above remain blocked:

1. **Do NOT generate `COMPARISON.md`.** The `generate-comparison.ts` script
   refuses without `GATE_VERIFIED=1` + ≥1 live result.
2. **Do NOT publish dry-run-derived numbers anywhere** — README, blog, paper.
   Dry-run output is for harness validation only.
3. **Do publish progress reports** in `docs/HANDOFF.md` showing which
   blockers have been cleared.

---

## What is *not* blocked

These things work on the dev box today (no VPS needed):

- `npx tsx benchmark/collect-competitor-data.ts --competitor <name> --dataset <ds> --dry-run`
- `cat benchmark/competitor-configs.json | jq '.competitors[] | .name'`
- `npx tsx benchmark/generate-comparison.ts` (prints gate status, exits 1)
- Editing the templates and configs without producing publishable output

---

## Handoff state (live)

See `docs/HANDOFF.md` for the current blocker-clearing priority.
The owner of clearing B1 is the team running Q1/Q2/Q3 harnesses
(scaffolded in PRs #6, #11, #12). Clearing B2/B3 is an ops action,
not an engineering one.
