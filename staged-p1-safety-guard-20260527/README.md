# P1 + P2 — op-audit.ts workspace consistency fix

> **Tasks #20 (P1) + #21 (P2) combined** — addresses 2026-05-25 incident root cause.

## What this fixes

The 2026-05-25 23:00 BRT incident (Mon, RECORRÊNCIA #4) wiped ~69k main-DB chunks to 756 because:

1. **op-audit.ts had its own `DB_PATH` constant** (historical line 39) that only read `NOX_DB_PATH` or fell back to hardcoded `/root/.openclaw/workspace/tools/nox-mem/nox-mem.db` (MAIN).
2. **db.ts respects `OPENCLAW_WORKSPACE`** and resolves DB path accordingly.
3. **Inconsistency:** when `nightly-maintenance.sh` Phase 2 set `OPENCLAW_WORKSPACE=/root/.openclaw/agents/atlas` (without `NOX_DB_PATH`), the two modules disagreed:
   - op-audit's DB_PATH → MAIN (`/root/.openclaw/workspace/tools/nox-mem/nox-mem.db`)
   - db.ts's DB_PATH → atlas (`/root/.openclaw/agents/atlas/tools/nox-mem/nox-mem.db`)
4. **Forensic proof:** the pre-op snapshot `reindex-atlas-20260526020006-...db` was **1.2 GB** (= MAIN size), while other agents' snapshots from the same run were 64 MB each. The atlas snapshot was a backup of MAIN, not atlas.

## Files changed

### `edits/src/lib/op-audit.ts` (full replacement)

Two changes:

#### P2 fix (#21) — root cause elimination

Replaces module-load `DB_PATH` constant with `resolveDbPath()` function that matches db.ts's resolution order:

```typescript
// OLD (historical line 39):
const DB_PATH = process.env.NOX_DB_PATH || '/root/.openclaw/workspace/tools/nox-mem/nox-mem.db';

// NEW:
function resolveDbPath(): string {
  if (process.env.NOX_DB_PATH) return resolve(process.env.NOX_DB_PATH);
  const ws = process.env.OPENCLAW_WORKSPACE;
  if (ws) return resolve(ws, 'tools', 'nox-mem', 'nox-mem.db');
  return '/root/.openclaw/workspace/tools/nox-mem/nox-mem.db';
}
const DB_PATH = resolveDbPath();
```

Resolution priority matches db.ts exactly: `NOX_DB_PATH` → `OPENCLAW_WORKSPACE`-derived → hardcoded main.

#### P1 guard (#20) — belt-and-suspenders defense

New exported function `assertDbPathConsistency(opName)` re-derives the expected path at op-time and compares with op-audit's module-load DB_PATH. If they disagree, throws a clear error with full context (env vars, expected vs actual, incident reference). Called at top of `withOpAudit()` and `safeRestore()`.

**Bypass:** `NOX_OP_AUDIT_SKIP_WORKSPACE_GUARD=1` (emergency only, NOT for production).

## Deploy steps (VPS)

1. **Validate flag is in place** before deploy (P0 mitigation still required for the deploy itself):
   ```bash
   ssh root@187.77.234.79 'ls -la /root/.openclaw/DISABLE_AGENT_REINDEX'
   # Should show file with timestamp 2026-05-27 15:51 BRT or later.
   ```

2. **Copy modified op-audit.ts to VPS:**
   ```bash
   scp staged-p1-safety-guard-20260527/edits/src/lib/op-audit.ts \
     root@187.77.234.79:/root/.openclaw/workspace/tools/nox-mem/src/lib/op-audit.ts
   ```

3. **Backup current dist + rebuild on VPS:**
   ```bash
   ssh root@187.77.234.79 'cd /root/.openclaw/workspace/tools/nox-mem && \
     cp dist/lib/op-audit.js dist/lib/op-audit.js.bak-pre-p1p2-20260527 && \
     npx tsc'
   ```

4. **Validate dist updated:**
   ```bash
   ssh root@187.77.234.79 'grep -c "assertDbPathConsistency\|resolveDbPath" \
     /root/.openclaw/workspace/tools/nox-mem/dist/lib/op-audit.js'
   # Should print >= 2 (function definitions + call sites)
   ```

5. **Restart services:**
   ```bash
   ssh root@187.77.234.79 'systemctl restart nox-mem-api nox-mem-watch && \
     sleep 5 && \
     curl -s http://127.0.0.1:18802/api/health | jq .chunks.total'
   # Should print 69135 (or current valid count)
   ```

6. **Smoke test with intentional env mismatch:**
   ```bash
   ssh root@187.77.234.79 'set -a; source /root/.openclaw/.env; set +a; \
     OPENCLAW_WORKSPACE=/root/.openclaw/agents/atlas \
     /usr/local/bin/nox-mem stats 2>&1 | head -10'
   # Stats should now show atlas DB chunks (~64), not main (69k).
   # Snapshot path in audit logs should also reflect atlas, not main.
   ```

7. **Once validated, remove the P0 flag:**
   ```bash
   ssh root@187.77.234.79 'rm /root/.openclaw/DISABLE_AGENT_REINDEX'
   # Tonight 23:00 BRT cron will re-enable Phase 2 with the fix in place.
   ```

## Tests pendentes

- Unit tests for `resolveDbPath()` and `assertDbPathConsistency()` — defer to follow-up PR.
- Integration test: simulate Phase 2 invocation with `OPENCLAW_WORKSPACE=/root/.openclaw/agents/atlas` and verify snapshot path matches atlas DB (not main).
- Regression test: run after P2 deploy to confirm no daily-main backups are affected.

## Bypass risks

`NOX_OP_AUDIT_SKIP_WORKSPACE_GUARD=1` should ONLY be used:

- During recovery from a DB corruption event where forced restore is needed across DB paths
- For controlled migration scenarios (e.g., moving a DB from agent path to main)
- Never in regular cron, scripts, or nightly-maintenance

If bypassed, the 2026-05-25 incident pattern CAN recur. Document any use of the bypass in `docs/INCIDENTS.md`.

## References

- `docs/INCIDENTS.md#2026-05-26` — current incident entry
- Task #18 — root cause investigation (completed 2026-05-27)
- Task #20 — P1 safety guard (this PR)
- Task #21 — P2 OPENCLAW_WORKSPACE root fix (this PR, combined)
- Memory: `feedback_reindex_bypasses_openclaw_workspace_hits_main`
