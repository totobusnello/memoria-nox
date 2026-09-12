# Evening Worktree Cleanup — 2026-05-24

## Inventory & Analysis

**Before:** 64 worktrees, .git/worktrees/ = 2.2M
**After:** 14 worktrees, .git/worktrees/ = 2.6M (still locked by active agents)

### Active Worktrees (KEPT)

**Wave 4 Feature Branches** (spawned Sat 2026-05-24, in-flight):
- `/private/tmp/q4-a2-p1-db-keyopen` → `feat/a2-tier3-p1-db-keyopen` (HEAD 65ad502a)
- `/private/tmp/q4-a2-p2-migration` → `feat/a2-tier3-p2-migration-script` (HEAD 7fa6f3e = main)
- `/private/tmp/q4-aggregate` → `feat/q4-aggregator-comparison-skeleton` (HEAD bcdae111)
- `/private/tmp/q4-f10-phase-c-phase2` → `feat/f10-phase-c-phase2-answer-wireup` (HEAD 7fa6f3e = main)
- `/private/tmp/q4-ingest-letta` → `feat/q4-ingest-letta-agentmemory-evermind` (HEAD 54b62188)

**Core/Agent Worktrees** (locked by active agents, PID 50010/38126):
- `.claude/worktrees/agent-a40e7a00288f2683d` → `feat/q4-corpus-loader-shared-lib` ✓
- `.claude/worktrees/agent-ac8b2d13c33491ed8` → `feat/q4-ingest-nox-mem` ✓
- `.claude/worktrees/agent-adfec25c2c9fee3d8` → `recon/a2-tier3-crypto-audit-2026-05-24` ✓

**Orphan Artifact Branches** (still locked, to remove when agents finish):
- `worktree-agent-a1bc40f41324c5522` (no real feature branch, PID 38126 stale, HEAD 41984676)
- `worktree-agent-a55a4cd3d4f213c13` (empty, HEAD = main)
- `worktree-agent-a60db6d9884eb32a7` (new leak post-list, HEAD = main)
- `worktree-agent-a81620ca92c6ea08e` (empty, HEAD = main)
- `worktree-agent-ad542fc594da77677` (empty, HEAD = main)
- `worktree-agent-aecfe9b8f6111c31f` (orphan, HEAD 2c163754, PID 38126 stale)

### Branches Deleted (51 total)

**Agent Artifact Branches** (wave 3 stale):
```
worktree-agent-a00142ba210227f70 ← a0b60116 ... af2c1b01a1492c7aa (51 branches total)
```
All deleted via `git branch -D <name>`.

**Merged Feature Branches** (Wave 3, PR #269-#272):
- `feat/q4-ingest-mem0` (PR #269, merged into main)
- `feat/q4-ingest-zep` (PR #272, merged into main)

## Disk Impact

- `.git/worktrees/` remains 2.6M because 6 locked worktrees still held by active agent processes (PIDs 50010, 38126)
- Once agents finish + release locks, `git worktree prune` will reclaim ~1.8-2.2M
- Branch deletions freed immediate ref storage (~5-8 KB total)

## Cleanup Blockers

**Cannot remove while locked:**
- Agent processes holding locks must finish first (graceful release or timeout)
- Stale PIDs (38126 in 2 worktrees) may be zombie processes — next prune will detect + cleanup

**Deployment gates:**
- Wave 4 branches are active — do NOT touch
- Do NOT force-remove `.claude/worktrees/agent-*` while locked (corrupts shared state)

## Post-Cleanup Checklist

- [ ] Monitor for stale PID 38126 (may require manual `rm -rf` after timeout)
- [ ] Run `git worktree prune` again tomorrow after agents finish (will reclaim locked dirs)
- [ ] Verify no new orphan branches created in next Wave 5 spawn

## Incident Prevention

**Root cause:** Wave 3 + Wave 4 agent spawns left artifact branches + worktrees orphaned post-merge:
1. Agent spawned → created `worktree-agent-XXX` branch + worktree
2. PR merged → branch no longer needed, but worktree still locked
3. Next agent spawn creates new worktree instead of reusing → pile-up

**Fix deployed:** `.claude/worktrees/` sparse-checkout disabled (per defense memo 2026-05-23). All new Wave 4 spawns use `/private/tmp/q4-*` naming scheme → avoid .claude path lock conflict.

---
**Audit Date:** 2026-05-24 evening
**Auditor:** Executor (Haiku)
**Parent branch:** main (7fa6f3e)
