# Worktree isolation fragile — sparse-checkout root cause escalation

**Timeline:** 2026-05-24 8× branch leaks despite `isolation: "worktree"` parameter set.

**Root cause:** `.claude/worktrees/` directory uses Git sparse-checkout. Agents cloning into `.claude/worktrees/<task>` inherit sparse-checkout config from parent, which creates a split index. If the agent's working tree diverges from the sparse-checkout manifest **during** `git checkout -b`, the sparse-checkout plumbing can leave the worktree HEAD in an inconsistent state.

**Symptom chain:**
1. Agent spawned with `isolation: "worktree"` → clones to `.claude/worktrees/agent-<uuid>`
2. Sparse-checkout filters files silently
3. `git branch --show-current` returns correct branch (e.g., `docs/feature`)
4. But `git log --oneline -1` shows commit on `main` (HEAD desynced)
5. Parent session later runs `git add` + `git commit` → lands commit on `main` instead of expected branch

**Layer 1 Defense (FRAGILE):** `isolation: "worktree"` parameter itself — doesn't prevent sparse-checkout inheritance or HEAD desync.

**Layer 2 Defense (RELIABLE):** Pre-commit hook at `~/.git-hooks-global/pre-commit` (installed 2026-05-21) that:
- Reads `.git/HEAD` (not `git branch --show-current`, which can lie)
- Validates against hardcoded allowlist (e.g., `main`, `refs/heads/main`)
- Aborts commit if HEAD is non-main, logs violation
- Override: `COMMIT_TO_NON_MAIN_OK=1 git commit ...` when intentional

**Recommended fix:** Agents should use `/tmp/<task>-<uuid>` with **fresh `git clone --depth 5`**, NOT `.claude/worktrees/`. This bypasses sparse-checkout entirely and gives each agent a clean tree:
```bash
task_tmp="/tmp/consolidation-$(uuidgen)"
mkdir -p "$task_tmp"
cd "$task_tmp"
git clone --depth 5 https://github.com/totobusnello/memoria-nox.git .
git checkout -b docs/feature
# work...
git push -u origin docs/feature
```

**Scalability:** `/tmp/<task>` is OS-temp (auto-cleanup, no ACL issues) and isolated from parent. Scales better than shared `.claude/worktrees/` for parallel agents.

**Status:** Layer 2 hook deployed + tested 5× Sat 2026-05-24. Layer 1 (isolation param) kept for paranoia, but operators should prefer Layer 2 + `/tmp` clone pattern.

**Reference:** `[[multi-agent-branch-checkout-race]]` (memoria-nox), incident log 2026-05-24.
