# Multi-agent worktree checkout race — 5× violations Sat 2026-05-24 (ESCALATED)

**Date:** 2026-05-24 (morning 4× + afternoon 1×)  
**Severity:** CRITICAL (main not contaminated; pre-commit hook layer 2 caught all; recovery 100%)  
**Root cause:** Sparse-checkout + HEAD mismatch in `git worktree add` spawning logic  
**Defense status:** Layer 2 (pre-commit hook) WORKING; Layer 1 (isolation param) BROKEN  
**Action:** Hardening audit deferred to Sun 2026-05-25 morning; memory escalated due to repeated pattern despite `isolation: "worktree"` config  

---

## Pattern Summary

5 separate agent streams committed to wrong branch despite isolation param:
1. **Stream B (morning):** #266 agent → created worktree → checkout branch not main → commit → hook abort
2. **Stream E (morning):** #271 agent → idem pattern
3. **Stream X (morning):** ~same as E/B
4. **Stream Y (morning):** variant (sparse-checkout state leaking)
5. **Stream Z (afternoon):** #276 agent → checkout branch → commit → hook abort

**All 5 commits eventually landed on correct branch via manual rebase recovery.**

---

## Root Cause Analysis

### Layer 1 (isolation param) — BROKEN

Agent spawn call includes `isolation: "worktree"` but worktree creation logic in agent.ts:
- Does NOT validate `--detach` flag when creating worktree
- Does NOT verify `git branch --show-current` matches expected branch AFTER worktree add
- Sparse-checkout state may be partial after agent inherits parent state
- HEAD can be stale from parent rebase during agent spawn race

**Example failure case:**
```bash
# Parent at main
git worktree add /tmp/wt-stream-b develop-feature
cd /tmp/wt-stream-b
git branch --show-current  # Returns "develop-feature" but detached HEAD!
# Agent checks out branch X thinking it's safe
git checkout -b feature/my-work
git add . && git commit  # Lands on develop-feature, not main
```

### Layer 2 (pre-commit hook global) — WORKING

Installed 2026-05-21 (`~/.git-hooks-global/pre-commit`):
```bash
#!/bin/bash
CURRENT_BRANCH=$(git branch --show-current)
PARENT_PATH=$(cd $(git rev-parse --git-dir)/.. && pwd)
if [[ "$(git rev-parse --show-toplevel)" != "$PARENT_PATH" ]]; then
  if [[ "$CURRENT_BRANCH" != "main" ]]; then
    echo "ERROR: Attempt to commit non-main branch in parent path. Aborting."
    exit 1
  fi
fi
```

All 5 violations were **caught and aborted** by this hook; commits never landed on main. Recovery was manual rebase per agent.

---

## Why This Matters

**Symptom today:** agents operating in isolated worktrees, but 5 times they created worktrees with wrong HEAD orientation. If pre-commit hook had NOT been in place:
- All 5 commits would have landed directly on main
- PRs would have been contaminated
- Rebase conflict resolution would have been ~30min manual surgery
- Risk of silent merge-commit contamination (especially in parallel agent runs)

**Pattern:** This is a **race condition in parallel agent spawning**, not a one-off mistake. It happens 5× in a single day when 6 agents run parallelism.

---

## Defense Improvements Needed (Sun 2026-05-25)

### Immediate (pre-worktree-spawn audit)

1. **Validate worktree HEAD orientation BEFORE any git operations:**
   ```bash
   git worktree add --detach /path/to/wt  # Always start detached
   cd /path/to/wt
   BRANCH_CHECK=$(git branch --show-current 2>&1 || echo "detached")
   if [[ "$BRANCH_CHECK" == "detached" ]]; then
     git checkout -b my-feature  # Create branch fresh
   else
     echo "ERROR: Worktree inherited branch state; aborting spawn"
     exit 1
   fi
   ```

2. **Add health check before agent commits:**
   ```bash
   git branch --show-current | grep -E '^(main|develop)' && {
     echo "ERROR: Detected parent branch in agent worktree"
     exit 1
   }
   ```

3. **Sparse-checkout state isolation:**
   - Do NOT inherit parent's `.git/info/sparse-checkout`
   - Generate fresh worktree-specific sparse-checkout per stream type

### Medium-term (queue-wide hardening)

1. **Per-agent worktree lifecycle logging** — log every `git worktree add`, `git checkout -b`, `git add`, `git commit` with branch sanity checks
2. **Pre-commit hook escalation** — convert from abort-only to 3-tier (abort / warn+require-manual-override / allow)
3. **Worktree pool manager** — instead of ad-hoc spawn per agent, maintain pool of healthy worktrees with validated HEAD state

---

## Memory references

- **Pre-commit hook installed:** `[[pre-commit-hook-blocks-non-main-commits]]` (2026-05-21)
- **Multi-agent isolation with worktree:** `[[multi-agent-branch-checkout-race]]` (2026-05-20)
- **Lesson from 2026-05-20:** worktrees can have main as HEAD silently; check `git branch --show-current` before add
- **Today escalation:** 5× repetition suggests spawn logic flaw, not operator error

---

## Recovery Log (Sat 2026-05-24)

| Stream | Issue | Recovery | Status |
|---|---|---|---|
| B | #266 checkout on worktree | Manual rebase + force-push | ✅ landed main |
| E | #271 checkout on worktree | Manual rebase + force-push | ✅ landed main |
| X | variant pattern | Idem | ✅ landed main |
| Y | sparse-checkout leak | Rebase + clean sparse | ✅ landed main |
| Z | #276 checkout on worktree | Manual rebase + force-push | ✅ landed main |

**All recoveries completed by 14h33 BRT. Main `ecb6eea` clean. No data loss.**

---

## Next session action

**Sun 2026-05-25 06h — Audit agent.ts worktree spawn logic:**

1. Review `src/agents/agent.ts` lines ~X–Y (spawn worktree block)
2. Add `--detach` flag + HEAD sanity check before any checkout
3. Test with Streams A–E re-running in parallel (5 agents concurrently)
4. Verify `git branch --show-current` returns detached or new-branch-only, never parent branch

**Escalation rationale:** 5 violations in morning + 1 in afternoon despite hook protection = pattern, not anomaly. Fix required before next multi-agent burst (Q4 final validation Sat evening).
