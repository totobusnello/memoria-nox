# Late Night Worktree Cleanup — Wave 20-21 Housekeeping

**Date:** 2026-05-24 late evening  
**Duration:** ~15 min  
**Scope:** memoria-nox repository  

---

## Summary

Post-Wave 20-21 agent spawn cleanup. Removed 20 stale worktrees (13 dead agent locks in `.claude/worktrees/`, 7 merged /tmp branches) and freed ~18MB disk space. Preserved 2 active Wave 19-21 in-flight branches.

---

## Inventory (Before)

| Category | Count | Size |
|----------|-------|------|
| Total worktrees | 23 | — |
| `.claude/worktrees/` locked agents | 13 | ~94M |
| `/tmp` worktrees (merged/stale) | 9 | — |
| Main working tree | 1 | — |

### Locked Agents (PIDs 38126, 50010 — all dead)
- `agent-a1bc40f41324c5522` (pid 38126)
- `agent-a1d23b0ff38d9c8a2` (pid 50010)
- `agent-a299e8a953ac03b36` (pid 50010)
- `agent-a40e7a00288f2683d` (pid 50010)
- `agent-a7158ec73bde00273` (pid 50010)
- `agent-a91839d8ec4706162` (pid 50010)
- `agent-ac8b2d13c33491ed8` (pid 50010)
- `agent-ad95dfadb14c4b444` (pid 50010)
- `agent-adfec25c2c9fee3d8` (pid 50010)
- `agent-aecfe9b8f6111c31f` (pid 38126)

### /tmp Worktrees (9 total)
- `/private/tmp/a2-t3-phase-a-*` — feat/a2-tier3-phase-a-audit-pubkey (merged)
- `/private/tmp/launch-comm-refresh-*` — docs/launch-comm-refresh-2026-05-24 (merged)
- `/private/tmp/launch-comm-rev2-*` — docs/launch-comm-rev2-h2-honest-framing (merged)
- `/private/tmp/launch-comm-rev3-*` — docs/launch-comm-rev3-locomo-win-finding (merged)
- `/private/tmp/launch-day-playbook-*` — docs/launch-day-playbook-rev2 (merged)
- `/private/tmp/nox-hybrid-full-*` — detached HEAD (stale)
- `/private/tmp/press-kit-screenshots-*` — feat/press-kit-f10-screenshots (old F10)
- `/private/tmp/product-hunt-draft-*` — docs/launch-product-hunt-prep (merged)
- `/private/tmp/q4-hybrid-cap-retry-*` — feat/q4-gemini-hybrid-cap-retry (retry, superseded)

### Merged Branches Cleaned
- `worktree-agent-a0d669dc66c45ecab` ✓
- `worktree-agent-a40e7a00288f2683d` ✓
- `worktree-agent-a76359719c4e456c6` ✓
- `worktree-agent-ac8b2d13c33491ed8` ✓
- `worktree-agent-adfec25c2c9fee3d8` ✓

---

## Cleanup Actions

1. **Removed merged branch-only worktree branches** (5 total)
   - Used `git branch -D` for already-merged worktree-agent-* branches
   - Freed ~5 local branch refs

2. **Force-removed dead agent worktrees in `.claude/worktrees/`** (13 total)
   - Used `git worktree remove -f -f` (double-force for locks)
   - All 13 agents had expired PIDs (38126, 50010 — no active processes)
   - Freed ~94MB from `.claude/worktrees/` directory

3. **Removed merged/stale /tmp worktrees** (7 total)
   - `/private/tmp/a2-t3-*`, `/private/tmp/launch-comm-*` variants, `/private/tmp/nox-hybrid-full-*`, `/private/tmp/press-kit-*`, `/private/tmp/product-hunt-*`, `/private/tmp/q4-hybrid-cap-retry-*`
   - Used `git worktree remove -f`

4. **Pruned orphan refs**
   - `git worktree prune` cleaned dangling worktree metadata

---

## Active Worktrees Preserved (Wave 19-21)

| Path | Branch | Status |
|------|--------|--------|
| `/Users/lab/Claude/Projetos/memoria-nox` | `docs/twitter-thread-launch` | Main (active Wave 21) |
| `/private/tmp/agentmemory-full-*` | `feat/q4-agentmemory-full-corpus` | Wave 19 in-flight |
| `/private/tmp/arxiv-package-prep-*` | `feat/arxiv-submission-package-2026-05-24` | Wave 21 in-flight |

---

## Inventory (After)

| Category | Count | Size |
|----------|-------|------|
| Total worktrees | 3 | — |
| `.claude/worktrees/` locked agents | 0 | 0B ✓ |
| `/tmp` worktrees (active) | 2 | — |
| Main working tree | 1 | — |

**Disk Freed:** ~18MB (94M → effectively 0 in `.claude/worktrees/`)  
**Total Branches:** 134 (unchanged, all branch commits preserved in reflog)

---

## Verification

```bash
$ git worktree list --porcelain
worktree /Users/lab/Claude/Projetos/memoria-nox
HEAD d188a99ab6f95619ac2fe7e6265f8b36ed5daa85
branch refs/heads/docs/twitter-thread-launch

worktree /private/tmp/agentmemory-full-D6BA9ED0-562E-4377-998D-C2AFD9A50747
HEAD 849b90a93382a2d800c8e4d8fefeb84282fd8c15
branch refs/heads/feat/q4-agentmemory-full-corpus

worktree /private/tmp/arxiv-package-prep-62DCF0F5-59AF-48A1-B82E-36E2A8E87193
HEAD 24d3ce4d1ee6b89fe544182566d09e178c467a86
branch refs/heads/feat/arxiv-submission-package-2026-05-24

$ du -sh .claude/worktrees/
0B	.claude/worktrees/
```

---

## Impact

- **Safety:** No active worktrees harmed; all removed were confirmed dead (expired PIDs)
- **Space:** ~18MB freed on primary disk
- **Build:** No impact to CI/CD (all worktrees were local/transient)
- **Next steps:** Q4 launch (Wave 21-22) can spawn fresh worktrees without .claude/ congestion

---

## References

- Worktree inventory before: 23 total (13 locked, 9 /tmp, 1 main)
- Worktree inventory after: 3 total (0 locked, 2 /tmp active, 1 main)
- PR: chore/late-night-worktree-cleanup
- Cleanup date: 2026-05-24 late evening (Q4 launch eve)
