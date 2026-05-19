# Wave A — Boost Stack Wiring Deployment Guide

> **What this does**: makes `section_boost`, `pain`, `BOOST_TYPES`, `TIER_BOOST`, and the corpus-correct `SOURCE_TYPE_BOOST` map **actually affect retrieval ranking** in nox-mem hybrid search. G3 ablation (PR #146, 2026-05-19) proved all of these were INERT in the deployed `search.ts`. Salience stays gated by `NOX_SALIENCE_MODE` per the shadow-discipline architectural constraint.

> **Do not deploy without a `withOpAudit` snapshot.** Even though this is a pure search-path change (no schema mutation), it changes the score formula for every query — that is a ranking change and falls under CLAUDE.md rule #5.

---

## Files to deploy

| Source (in this repo)                  | VPS destination                                |
|----------------------------------------|------------------------------------------------|
| `staged-1.7a/edits/search.ts`          | `/root/.openclaw/workspace/tools/nox-mem/src/search.ts` |
| `staged-1.7a/edits/salience.ts`        | `/root/.openclaw/workspace/tools/nox-mem/src/salience.ts` (alongside existing `src/lib/salience.ts` — the VPS already has a `src/lib/salience.ts`; if you keep both, prefer the lib path and re-import. Otherwise drop this in as the canonical module.) |

> The VPS already has `src/lib/salience.ts` per CLAUDE.md §"Schema v10". If that file already exports `computeSalience` with the same signature, you can drop our `edits/salience.ts` and instead patch `edits/search.ts`'s import from `./salience.js` → `./lib/salience.js`. The shipped `edits/salience.ts` is a drop-in that works either way.

---

## Pre-flight (on the VPS)

```bash
ssh root@srv1465941.hstgr.cloud
cd /root/.openclaw/workspace/tools/nox-mem

# 1. Load env so withOpAudit + Gemini work.
set -a; source /root/.openclaw/.env; set +a

# 2. Confirm the API is healthy BEFORE touching anything.
curl -s http://127.0.0.1:18802/api/health | jq '.vectorCoverage, .schemaVersion'

# 3. Confirm baseline G3 numbers (from research/G3-rerun) are reproducible.
#    The G3 harness in scripts/g3-ablation.ts is the canonical baseline.
node dist/scripts/g3-ablation.js --record-baseline > /tmp/g3-pre.json
jq '.byVariant[] | {variant, ndcg_at_10}' /tmp/g3-pre.json

# 4. Snapshot the prod DB via withOpAudit BEFORE the deploy.
node -e "import('./dist/lib/op-audit.js').then(m => m.snapshotForOp('a-boost-stack-wiring'))"
ls -lh /var/backups/nox-mem/pre-op/ | head -3
```

## Deploy

```bash
# From your laptop, in the worktree:
WORKTREE=/Users/lab/Claude/Projetos/memoria-nox/.claude/worktrees/agent-aeedc4980f9a7e1ff
VPS=/root/.openclaw/workspace/tools/nox-mem

scp "$WORKTREE/staged-1.7a/edits/salience.ts" \
    root@srv1465941.hstgr.cloud:$VPS/src/salience.ts
scp "$WORKTREE/staged-1.7a/edits/search.ts" \
    root@srv1465941.hstgr.cloud:$VPS/src/search.ts

# On the VPS:
ssh root@srv1465941.hstgr.cloud
cd /root/.openclaw/workspace/tools/nox-mem

# Type-check and build.
npx tsc -p tsconfig.json 2>&1 | tail
ls -lh dist/search.js dist/salience.js

# Restart the API systemd unit.
systemctl restart nox-mem-api
sleep 2
curl -s http://127.0.0.1:18802/api/health | jq '.uptime_seconds'
```

## Validate post-deploy

```bash
# 1. Smoke search — make sure no regression on a trivial query.
curl -s "http://127.0.0.1:18802/api/search?q=stripe" | jq '.results | length, .[0]'

# 2. Confirm boost-stack columns are now in the SearchResult payload.
curl -s "http://127.0.0.1:18802/api/search?q=stripe" | \
  jq '.results[0] | {section, pain, importance, source_type, tier}'
# Expected: those 5 fields are present (not undefined) — proves the new SELECT works.

# 3. Re-run G3 ablation with the new code AND with NOX_SALIENCE_MODE=shadow.
node dist/scripts/g3-ablation.js > /tmp/g3-post.json
jq '.byVariant[] | {variant, ndcg_at_10}' /tmp/g3-post.json

# 4. Compute delta vs baseline.
node -e "
  const pre = require('/tmp/g3-pre.json');
  const post = require('/tmp/g3-post.json');
  for (const v of pre.byVariant) {
    const p = post.byVariant.find(x => x.variant === v.variant);
    console.log(v.variant.padEnd(20),
      'pre=', v.ndcg_at_10.toFixed(4),
      'post=', p?.ndcg_at_10.toFixed(4),
      'Δ=', (p ? p.ndcg_at_10 - v.ndcg_at_10 : NaN).toFixed(4));
  }
"
```

### Expected nDCG@10 delta (estimate)

| Ablation                                       | Pre (G3 #146) | Post estimate | Δ      |
|------------------------------------------------|---------------|---------------|--------|
| `A1` (semantic-alone)                          | 0.572         | ≈0.572        | ~0     |
| `A8` (full prod, shadow salience)              | 0.573         | **0.59–0.62** | +0.02–0.05 |
| `A8 + NOX_SALIENCE_MODE=active`                | n/a           | **0.62–0.66** | +0.05–0.09 |
| `A8 + NOX_DISABLE_SECTION_BOOST=1` (ablation)  | n/a           | ≈A1           | should fall back |

Rationale: G3 measured Δ(A8 − A1) = +0.0010 because no boost was actually applied. With the wiring corrected, the +0.5 / +1.0 / +2.0 deltas land on every entity-format chunk (n=749 sections in prod) and on every `external` chunk (n=1,046). Even a small fraction of golden-set queries hitting those rows shifts nDCG by 0.02–0.05.

Numbers above are forward-looking estimates — final nDCG to be measured against the canonical golden set after deploy.

## Rollback

```bash
ssh root@srv1465941.hstgr.cloud
cd /root/.openclaw/workspace/tools/nox-mem

# Restore the pre-op snapshot if anything looks broken.
LATEST=$(ls -t /var/backups/nox-mem/pre-op/a-boost-stack-wiring-*.db | head -1)
node -e "import('./dist/lib/op-audit.js').then(m => m.safeRestore('$LATEST'))"

# Or revert just the source files via git (the staged patch lives in the agent repo,
# not the VPS deployment, so a clean rollback is `git checkout HEAD~1 -- src/search.ts src/salience.ts && npm run build && systemctl restart nox-mem-api`).
```

## Env toggles (post-deploy ablation experiments)

All boosts default to ACTIVE. To ablate any single boost in production, set the env var in `/root/.openclaw/.env` and restart `nox-mem-api`:

```ini
# Disable individually — no rebuild needed
NOX_DISABLE_TYPE_BOOST=1
NOX_DISABLE_TIER_BOOST=1
NOX_DISABLE_SOURCE_TYPE_BOOST=1
NOX_DISABLE_SECTION_BOOST=1
NOX_DISABLE_RECENCY_BOOST=1

# Salience mode — defaults to "shadow"; flip to "active" to apply, "off" to ablate
NOX_SALIENCE_MODE=shadow
```

After flipping any of these, re-run the G3 ablation against the deployed code to measure the delta. This is how we audit each boost's individual contribution to nDCG@10.

## Test plan (local)

```bash
cd /Users/lab/Claude/Projetos/memoria-nox/.claude/worktrees/agent-aeedc4980f9a7e1ff/staged-1.7a
npm install
npm run check        # salience.ts typecheck
npm run check:search # search.ts typecheck (with stubs for VPS deps)
npm test             # 31 boost-stack tests must pass
```

## Files in this patch

| File                                              | Purpose                                                                 |
|---------------------------------------------------|-------------------------------------------------------------------------|
| `edits/search.ts`                                 | Rewrites `search()` and `searchSemantic()` to apply ADDITIVE boost stack with env toggles |
| `edits/salience.ts`                               | Drop-in salience helper: `calculateSalience` + `getSalienceMode`         |
| `tests/search-boost-stack.test.ts`                | 31 tests covering section/pain/type/tier/source_type + mode gating + additive stacking |
| `_stubs/deps.d.ts`                                | Type-only shims for `db.js`/`tier-manager.js`/etc. so `tsc --noEmit` works without the VPS module graph |
| `tsconfig.json`                                   | Build config — emits `salience.ts` only (search.ts is a patch, not a buildable unit here) |
| `tsconfig.search.json`                            | Standalone typecheck of `search.ts` using stub declarations            |
| `tsconfig.tests.json`                             | Test build config                                                       |
| `package.json`                                    | npm scripts: `check`, `check:search`, `check:tests`, `test`            |

## Behavioural contract (what the tests pin)

1. **Boost reading**: section / pain / importance / source_type / source_date / tier / chunk_type / retention_days / created_at / last_accessed_at are all SELECTed into both FTS and semantic paths.
2. **Additive stacking** (CLAUDE.md rule #5): `score = base × (1 + Σdeltas)`, never `Πfactors`.
3. **SOURCE_TYPE_BOOST corpus-correct**: `external` (delta −0.2) now actually applies. Legacy keys (`user_statement`, `compiled`, `timeline`) preserved for forward-compat.
4. **Section_boost wires up V10**: `compiled +1.0`, `frontmatter +0.5`, `timeline −0.2`, fallback to `section_boost` column.
5. **Salience mode-gated**: `NOX_SALIENCE_MODE=active` applies salience delta in [−0.5, +0.5]. `shadow` (DEFAULT) and `off` contribute 0.
6. **All 5 disable toggles** zero out their respective contribution; with all 5 disabled + `MODE=off`, the score equals the base FTS rank (no regression possible).
