# Deploy Validator Report — 2026-05-18

**Guide:** `../../docs/DEPLOY-WAVE-B.md`
**Generated:** 2026-05-18T12:40:09.058Z
**Overall:** PASSED

## Summary

| Metric | Count |
|--------|-------|
| Total checks | 112 |
| Pass | 110 |
| Fail | 0 |
| Warning | 2 |
| VPS-only (skipped) | 0 |
| Skip | 0 |

## Results

| Status | Category | Label | Detail |
|--------|----------|-------|--------|
| ok | bash-syntax | L12: TL;DR — Order of operations | Syntax OK |
| ok | bash-syntax | L29: 1. Pre-flight Checklist | Syntax OK |
| ok | bash-syntax | L107: 3. Deployment Order — Dependency DAG | Syntax OK |
| ok | bash-syntax | L131: 4. Step-by-Step Deployment Commands | Syntax OK |
| ok | bash-syntax | L138: Step 1 — Schema v11 | Syntax OK |
| ok | bash-syntax | L171: Step 2 — Schema v19 | Syntax OK |
| ok | bash-syntax | L204: Step 3 — Schema v20 (viewer_telemetry) | Syntax OK |
| ok | bash-syntax | L235: Step 4 — Privacy filter (staged-privacy) | Syntax OK |
| ok | bash-syntax | L269: Step 5 — Provider abstraction (staged-A3) | Syntax OK |
| ok | bash-syntax | L286: Step 6 — Event bus (staged-P5a) | Syntax OK |
| ok | bash-syntax | L305: Step 7 — Answer primitive (staged-P1) | Syntax OK |
| ok | bash-syntax | L333: Step 8 — Archive primitives (staged-A2) | Syntax OK |
| ok | bash-syntax | L350: Step 9 — Regex-first KG extraction (staged-L4) | Syntax OK |
| ok | bash-syntax | L365: Step 10 — Real-time viewer (staged-P5) | Syntax OK |
| ok | bash-syntax | L389: Step 11 — Temporal queries (staged-P3) | Syntax OK |
| ok | bash-syntax | L416: Step 12 — Historical patches (staged-1.6, staged-1 | Syntax OK |
| ok | bash-syntax | L437: Step 13 — Cron scripts + prompts (staged-1.8) | Syntax OK |
| ok | bash-syntax | L456: Step 14 — Build, restart, and validate | Syntax OK |
| ok | bash-syntax | L488: 5. Schema Migration Commands Reference | Syntax OK |
| ok | bash-syntax | L521: 5. Schema Migration Commands Reference | Syntax OK |
| ok | bash-syntax | L537: 6. Post-Deploy Validation | Syntax OK |
| ok | bash-syntax | L663: Schema rollback (v11 only — v19/v20 are forward-on | Syntax OK |
| ok | bash-syntax | L679: Using safeRestore() for schema rollback | Syntax OK |
| ok | bash-syntax | L696: Validation after rollback | Syntax OK |
| ok | bash-syntax | L715: 8.1 L4 Regex-first KG extraction | Syntax OK |
| ok | bash-syntax | L738: 8.2 Salience formula (already in shadow-mode, pre- | Syntax OK |
| ok | bash-syntax | L767: 9.1 Missing env source — silent failure | Syntax OK |
| ok | bash-syntax | L778: 9.2 Wrong port | Syntax OK |
| ok | bash-syntax | L808: 9.6 Schema v19 is NOT idempotent | Syntax OK |
| ok | rsync | rsync -avz staged-migrations/v11.sql $VPS_HOST:${NM}/staged- | dry-run OK |
| ok | rsync | rsync -avz staged-migrations/v11-tests.sql $VPS_HOST:${NM}/s | dry-run OK |
| ok | rsync | rsync -avz staged-migrations/v19.sql $VPS_HOST:${NM}/staged- | dry-run OK |
| ok | rsync | rsync -avz staged-migrations/v19-tests.sql $VPS_HOST:${NM}/s | dry-run OK |
| ok | rsync | rsync -avz  /Users/lab/Claude/Projetos/memoria-nox/.claude/w | dry-run OK |
| ok | rsync | rsync -avz --dry-run staged-privacy/edits/privacy/ $VPS_HOST | dry-run OK |
| ok | rsync | rsync -avz staged-privacy/edits/privacy/ $VPS_HOST:${NM}/src | dry-run OK |
| ok | rsync | rsync -avz --dry-run staged-A3/edits/src/providers/ $VPS_HOS | dry-run OK |
| ok | rsync | rsync -avz staged-A3/edits/src/providers/ $VPS_HOST:${NM}/sr | dry-run OK |
| ok | rsync | rsync -avz --dry-run staged-P5a/edits/src/lib/events/ $VPS_H | dry-run OK |
| ok | rsync | rsync -avz staged-P5a/edits/src/lib/events/ $VPS_HOST:${NM}/ | dry-run OK |
| ok | rsync | rsync -avz --dry-run staged-P1/edits/src/lib/answer/ $VPS_HO | dry-run OK |
| ok | rsync | rsync -avz --dry-run staged-P1/edits/src/api/answer.ts $VPS_ | dry-run OK |
| ok | rsync | rsync -avz --dry-run staged-P1/edits/src/cli/answer.ts $VPS_ | dry-run OK |
| ok | rsync | rsync -avz --dry-run staged-P1/edits/src/mcp/tools/answer.ts | dry-run OK |
| ok | rsync | rsync -avz staged-P1/edits/src/lib/answer/ $VPS_HOST:${NM}/s | dry-run OK |
| ok | rsync | rsync -avz staged-P1/edits/src/api/answer.ts $VPS_HOST:${NM} | dry-run OK |
| ok | rsync | rsync -avz staged-P1/edits/src/cli/answer.ts $VPS_HOST:${NM} | dry-run OK |
| ok | rsync | rsync -avz staged-P1/edits/src/mcp/tools/answer.ts $VPS_HOST | dry-run OK |
| ok | rsync | rsync -avz --dry-run staged-A2/edits/src/lib/archive/ $VPS_H | dry-run OK |
| ok | rsync | rsync -avz staged-A2/edits/src/lib/archive/ $VPS_HOST:${NM}/ | dry-run OK |
| ok | rsync | rsync -avz --dry-run staged-L4/edits/src/lib/regex-extract/  | dry-run OK |
| ok | rsync | rsync -avz staged-L4/edits/src/lib/regex-extract/ $VPS_HOST: | dry-run OK |
| ok | rsync | rsync -avz --dry-run  /Users/lab/Claude/Projetos/memoria-nox | dry-run OK |
| ok | rsync | rsync -avz  /Users/lab/Claude/Projetos/memoria-nox/.claude/w | dry-run OK |
| ok | rsync | rsync -avz --dry-run staged-P3/edits/dates.ts $VPS_HOST:${NM | dry-run OK |
| ok | rsync | rsync -avz --dry-run staged-P3/edits/search.ts $VPS_HOST:${N | dry-run OK |
| ok | rsync | rsync -avz --dry-run staged-P3/edits/index.ts $VPS_HOST:${NM | dry-run OK |
| ok | rsync | rsync -avz --dry-run staged-P3/edits/api-server.ts $VPS_HOST | dry-run OK |
| ok | rsync | rsync -avz --dry-run staged-P3/edits/mcp-search-tool.ts $VPS | dry-run OK |
| ok | rsync | rsync -avz --dry-run staged-P3/tests/temporal.test.ts $VPS_H | dry-run OK |
| ok | rsync | rsync -avz staged-P3/edits/dates.ts $VPS_HOST:${NM}/src/lib/ | dry-run OK |
| ok | rsync | rsync -avz staged-P3/edits/search.ts $VPS_HOST:${NM}/src/sea | dry-run OK |
| ok | rsync | rsync -avz staged-P3/edits/index.ts $VPS_HOST:${NM}/src/inde | dry-run OK |
| ok | rsync | rsync -avz staged-P3/edits/api-server.ts $VPS_HOST:${NM}/src | dry-run OK |
| ok | rsync | rsync -avz staged-P3/edits/mcp-search-tool.ts $VPS_HOST:${NM | dry-run OK |
| ok | rsync | rsync -avz staged-P3/tests/temporal.test.ts $VPS_HOST:${NM}/ | dry-run OK |
| ok | rsync | rsync -avz --dry-run staged-1.7a/edits/generate-user-profile | dry-run OK |
| ok | rsync | rsync -avz staged-1.8/scripts/cipher-weekly-audit.sh $VPS_HO | dry-run OK |
| ok | rsync | rsync -avz staged-1.8/scripts/heartbeat-sync.sh $VPS_HOST:/r | dry-run OK |
| ok | rsync | rsync -avz staged-1.8/scripts/weather-sp.sh $VPS_HOST:/root/ | dry-run OK |
| ok | rsync | rsync -avz staged-1.8/cipher-weekly-prompt.txt $VPS_HOST:/ro | dry-run OK |
| ok | rsync | rsync -avz staged-1.8/daily-briefing-prompt.txt $VPS_HOST:/r | dry-run OK |
| ok | rsync | rsync -avz staged-migrations/v11-rollback.sql $VPS_HOST:${NM | dry-run OK |
| ok | sqlite-migration | v11.sql | user_version=11, tables created: agent_events, answer_telemetry, provider_telemetry |
| ok | sqlite-migration | v19.sql | user_version=19, tables created: none |
| ok | sqlite-migration | v20-viewer-telemetry.sql | user_version=20, tables created: viewer_telemetry |
| ok | path-validator | L12: TL;DR — Order of operations | No path issues |
| ok | path-validator | L29: 1. Pre-flight Checklist | No path issues |
| ok | path-validator | L107: 3. Deployment Order — Dependency DAG | No path issues |
| ok | path-validator | L131: 4. Step-by-Step Deployment Commands | No path issues |
| ok | path-validator | L138: Step 1 — Schema v11 | No path issues |
| ok | path-validator | L171: Step 2 — Schema v19 | No path issues |
| WARN | path-validator | L204: Step 3 — Schema v20 (viewer_telemetry) | [worktree-path-leaked] Worktree-absolute path in command — replace with VPS path or relative path. The DEPLOY-WAVE-B.md  |
| ok | path-validator | L235: Step 4 — Privacy filter (staged-privacy) | No path issues |
| ok | path-validator | L269: Step 5 — Provider abstraction (staged-A3 | No path issues |
| ok | path-validator | L286: Step 6 — Event bus (staged-P5a) | No path issues |
| ok | path-validator | L305: Step 7 — Answer primitive (staged-P1) | No path issues |
| ok | path-validator | L333: Step 8 — Archive primitives (staged-A2) | No path issues |
| ok | path-validator | L350: Step 9 — Regex-first KG extraction (stag | No path issues |
| WARN | path-validator | L365: Step 10 — Real-time viewer (staged-P5) | [worktree-path-leaked] Worktree-absolute path in command — replace with VPS path or relative path. The DEPLOY-WAVE-B.md  |
| ok | path-validator | L389: Step 11 — Temporal queries (staged-P3) | No path issues |
| ok | path-validator | L416: Step 12 — Historical patches (staged-1.6 | No path issues |
| ok | path-validator | L437: Step 13 — Cron scripts + prompts (staged | No path issues |
| ok | path-validator | L456: Step 14 — Build, restart, and validate | No path issues |
| ok | path-validator | L488: 5. Schema Migration Commands Reference | No path issues |
| ok | path-validator | L521: 5. Schema Migration Commands Reference | No path issues |
| ok | path-validator | L537: 6. Post-Deploy Validation | No path issues |
| ok | path-validator | L639: Source rollback (any code step 4–13) | No path issues |
| ok | path-validator | L663: Schema rollback (v11 only — v19/v20 are  | No path issues |
| ok | path-validator | L679: Using safeRestore() for schema rollback | No path issues |
| ok | path-validator | L696: Validation after rollback | No path issues |
| ok | path-validator | L715: 8.1 L4 Regex-first KG extraction | No path issues |
| ok | path-validator | L738: 8.2 Salience formula (already in shadow- | No path issues |
| ok | path-validator | L767: 9.1 Missing env source — silent failure | No path issues |
| ok | path-validator | L778: 9.2 Wrong port | No path issues |
| ok | path-validator | L808: 9.6 Schema v19 is NOT idempotent | No path issues |
| ok | url-validator | L29: http://127.0.0.1:18802/api/health | 2 URL(s) valid |
| ok | url-validator | L171: http://127.0.0.1:18802/api/health | 1 URL(s) valid |
| ok | url-validator | L537: http://127.0.0.1:18802/api/health | 6 URL(s) valid |
| ok | url-validator | L639: http://127.0.0.1:18802/api/health | 1 URL(s) valid |
| ok | url-validator | L738: http://127.0.0.1:18802/api/health | 1 URL(s) valid |
| ok | url-validator | L778: http://127.0.0.1:18802/api/health | 1 URL(s) valid |