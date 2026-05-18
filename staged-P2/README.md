# staged-P2 — Hooks Auto-Capture (T1-T15)

> Staged patch. Not yet merged into `src/`. Lives in `staged-P2/edits/`
> mirroring final tree layout for atomic move on green CI.

## Quick start

```bash
cd staged-P2
npm install
npm run build
npm test
```

## Layout

```
staged-P2/
├── package.json                 # nox-mem-hooks-autocapture v0.1.0-P2-T1-T15
├── tsconfig.json
└── edits/
    ├── docs/HOOKS.md            # T15 — operator docs (5 layers, env, FAQ)
    └── src/
        ├── lib/hooks/
        │   ├── types.ts                       # T1
        │   ├── config.ts                      # T7
        │   ├── source-allowlist.ts            # T2 (Layer 2)
        │   ├── privacy-filter-adapter.ts      # T3 (Layer 3)
        │   ├── classifier.ts                  # T4 (Layer 4)
        │   ├── rate-limit.ts                  # T5 (Layer 5)
        │   ├── decorators.ts                  # T10
        │   ├── pipeline.ts                    # T6 (orchestrator)
        │   ├── worker.ts                      # T9 (queue)
        │   └── __tests__/                     # all test files
        ├── plugins/nox-hooks/
        │   ├── index.ts                       # T8 (OpenClaw plugin)
        │   └── openclaw.plugin.json
        ├── cli/hooks.ts                       # T11
        ├── api/hooks.ts                       # T12
        └── mcp/tools/hooks.ts                 # T13
```

## Architecture

```
HookEvent
   ↓
Layer 1: env gate           ← NOX_HOOKS_ENABLED=1
   ↓
Layer 2: source allowlist   ← NOX_HOOK_SOURCES (default: openclaw)
   ↓
Layer 3: A1 privacy filter  ← staged-A1 redact()
   ↓
Layer 4: content classifier ← heuristics + (opt) LLM fallback
   ↓
Layer 5: rate-limit + dedup ← token bucket + cosine ring buffer
   ↓
ingestText({provenance: "hook", ...})
```

## Spec

- `specs/2026-05-17-P2-hooks-autocapture.md` (canonical)
- `specs/2026-05-18-P2-implementation-kickoff.md` (engineering plan)
