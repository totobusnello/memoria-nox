#!/usr/bin/env bash
# cleanup-worktrees.test.sh — Smoke tests for cleanup-worktrees.sh
#
# Creates a temporary git repository with mock worktrees, runs the cleanup
# script against it, and validates the expected outcomes.
#
# Usage:
#   ./scripts/cleanup-worktrees.test.sh [--verbose]
#
# Requires: git, bash 4+
# Does NOT require the actual memoria-nox repo to be present during testing.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLEANUP_SCRIPT="${SCRIPT_DIR}/cleanup-worktrees.sh"
VERBOSE=0

[[ "${1:-}" == "--verbose" ]] && VERBOSE=1

# --------------------------------------------------------------------------
# Test framework
# --------------------------------------------------------------------------
PASS=0; FAIL=0; SKIP=0
TMPDIR_SUITE="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_SUITE"' EXIT

ok()   { echo -e "\033[0;32m  PASS\033[0m $1"; (( PASS++ )) || true; }
fail() { echo -e "\033[0;31m  FAIL\033[0m $1: $2"; (( FAIL++ )) || true; }
skip() { echo -e "\033[0;90m  SKIP\033[0m $1"; (( SKIP++ )) || true; }

assert_contains() {
  local label="$1" needle="$2" haystack="$3"
  if echo "$haystack" | grep -q "$needle"; then
    ok "$label"
  else
    fail "$label" "expected '${needle}' in output"
    [[ "$VERBOSE" -eq 1 ]] && echo "$haystack" | head -20
  fi
}

assert_not_contains() {
  local label="$1" needle="$2" haystack="$3"
  if ! echo "$haystack" | grep -q "$needle"; then
    ok "$label"
  else
    fail "$label" "did NOT expect '${needle}' in output"
  fi
}

assert_path_exists()     { [[ -d "$2" ]] && ok "$1" || fail "$1" "path should exist: $2"; }
assert_path_not_exists() { [[ ! -d "$2" ]] && ok "$1" || fail "$1" "path should NOT exist: $2"; }

# --------------------------------------------------------------------------
# Setup: create a fake git repo with controlled worktrees
# --------------------------------------------------------------------------
setup_repo() {
  local repo="$1"
  git init -q "$repo"
  git -C "$repo" config user.email "test@example.com"
  git -C "$repo" config user.name "Test"
  echo "root" > "${repo}/README.md"
  git -C "$repo" add .
  git -C "$repo" commit -q -m "initial commit"
  git -C "$repo" branch -M main
  mkdir -p "${repo}/.claude/worktrees"
}

add_agent_worktree() {
  # add_agent_worktree <repo> <agent-id> <branch-name> [--locked]
  local repo="$1" agent_id="$2" branch="$3"
  local lock="${4:-}"
  local wt_path="${repo}/.claude/worktrees/${agent_id}"

  git -C "$repo" checkout -q -b "$branch"
  echo "work in $branch" > "${repo}/work.txt"
  git -C "$repo" add .
  git -C "$repo" commit -q -m "work in $branch"
  git -C "$repo" checkout -q main

  git -C "$repo" worktree add -q -b "wt-${branch}" "$wt_path"
  # Reset worktree branch to point to the branch head
  git -C "$repo" -C "$wt_path" checkout -q "$branch" 2>/dev/null || true

  if [[ "$lock" == "--locked" ]]; then
    git -C "$repo" worktree lock "$wt_path" --reason "claude agent ${agent_id} (pid 12345)"
  fi

  echo "$wt_path"
}

merge_branch() {
  local repo="$1" branch="$2"
  git -C "$repo" checkout -q main
  git -C "$repo" merge -q --no-ff "$branch" -m "Merge ${branch}"
}

# --------------------------------------------------------------------------
# Test 1: Dry-run shows candidates but removes nothing
# --------------------------------------------------------------------------
test_dry_run_removes_nothing() {
  local repo="${TMPDIR_SUITE}/t1"
  setup_repo "$repo"

  local branch="wave-a/2026-05-18/feature"
  add_agent_worktree "$repo" "agent-abc123" "$branch" >/dev/null
  merge_branch "$repo" "$branch"

  local out
  out="$(cd "$repo" && DRY_RUN=1 GIT_MAIN_BRANCH=main WORKTREE_BASE=".claude/worktrees" \
    bash "$CLEANUP_SCRIPT" 2>&1)" || true

  assert_contains  "t1: dry-run mentions WOULD REMOVE" "WOULD REMOVE" "$out"
  assert_path_exists "t1: worktree dir still present after dry-run" \
    "${repo}/.claude/worktrees/agent-abc123"
}

# --------------------------------------------------------------------------
# Test 2: Merged worktree is removed with --force
# --------------------------------------------------------------------------
test_merged_removed_with_force() {
  local repo="${TMPDIR_SUITE}/t2"
  setup_repo "$repo"

  local branch="wave-b/2026-05-18/feature"
  add_agent_worktree "$repo" "agent-def456" "$branch" >/dev/null
  merge_branch "$repo" "$branch"

  local out
  out="$(cd "$repo" && DRY_RUN=0 GIT_MAIN_BRANCH=main WORKTREE_BASE=".claude/worktrees" \
    bash "$CLEANUP_SCRIPT" --force 2>&1)" || true

  assert_contains  "t2: output says REMOVED"         "REMOVED" "$out"
  assert_path_not_exists "t2: worktree dir gone after --force" \
    "${repo}/.claude/worktrees/agent-def456"
}

# --------------------------------------------------------------------------
# Test 3: Unmerged worktree with unique commits is kept
# --------------------------------------------------------------------------
test_unmerged_with_commits_kept() {
  local repo="${TMPDIR_SUITE}/t3"
  setup_repo "$repo"

  local branch="wave-c/2026-05-18/wip"
  add_agent_worktree "$repo" "agent-ghi789" "$branch" >/dev/null
  # Do NOT merge — branch has unique commits ahead of main

  local out
  out="$(cd "$repo" && DRY_RUN=0 GIT_MAIN_BRANCH=main WORKTREE_BASE=".claude/worktrees" \
    bash "$CLEANUP_SCRIPT" --force 2>&1)" || true

  assert_contains     "t3: output shows KEEP for unique commits" \
    "unique commits" "$out"
  assert_path_exists  "t3: worktree still present" \
    "${repo}/.claude/worktrees/agent-ghi789"
}

# --------------------------------------------------------------------------
# Test 4: --merged-only skips clean unmerged worktree
# --------------------------------------------------------------------------
test_merged_only_skips_clean_unmerged() {
  local repo="${TMPDIR_SUITE}/t4"
  setup_repo "$repo"

  local branch="wave-d/2026-05-18/clean-unmerged"
  add_agent_worktree "$repo" "agent-jkl012" "$branch" >/dev/null
  # NOT merged, but would be clean-removable without --merged-only

  local out
  out="$(cd "$repo" && DRY_RUN=0 GIT_MAIN_BRANCH=main WORKTREE_BASE=".claude/worktrees" \
    bash "$CLEANUP_SCRIPT" --force --merged-only 2>&1)" || true

  assert_contains    "t4: output mentions not merged"   "not merged"    "$out"
  assert_path_exists "t4: worktree kept with --merged-only" \
    "${repo}/.claude/worktrees/agent-jkl012"
}

# --------------------------------------------------------------------------
# Test 5: Locked worktree with agent lock is unlocked and removed
# --------------------------------------------------------------------------
test_agent_locked_worktree_removed() {
  local repo="${TMPDIR_SUITE}/t5"
  setup_repo "$repo"

  local branch="wave-e/2026-05-18/locked"
  add_agent_worktree "$repo" "agent-mno345" "$branch" --locked >/dev/null
  merge_branch "$repo" "$branch"

  local out
  out="$(cd "$repo" && DRY_RUN=0 GIT_MAIN_BRANCH=main WORKTREE_BASE=".claude/worktrees" \
    bash "$CLEANUP_SCRIPT" --force 2>&1)" || true

  assert_contains     "t5: merged+locked worktree removed" "REMOVED" "$out"
  assert_path_not_exists "t5: worktree dir gone" \
    "${repo}/.claude/worktrees/agent-mno345"
}

# --------------------------------------------------------------------------
# Test 6: --keep-days filters out recent worktrees
# --------------------------------------------------------------------------
test_keep_days_skips_recent() {
  local repo="${TMPDIR_SUITE}/t6"
  setup_repo "$repo"

  local branch="wave-f/2026-05-18/recent"
  add_agent_worktree "$repo" "agent-pqr678" "$branch" >/dev/null
  merge_branch "$repo" "$branch"

  # KEEP_DAYS=9999 — every commit is "too new"
  local out
  out="$(cd "$repo" && DRY_RUN=0 KEEP_DAYS=9999 GIT_MAIN_BRANCH=main WORKTREE_BASE=".claude/worktrees" \
    bash "$CLEANUP_SCRIPT" --force 2>&1)" || true

  assert_contains    "t6: output says too new"    "too new"   "$out"
  assert_path_exists "t6: worktree kept by age filter" \
    "${repo}/.claude/worktrees/agent-pqr678"
}

# --------------------------------------------------------------------------
# Test 7: Empty worktrees directory exits cleanly
# --------------------------------------------------------------------------
test_empty_worktrees_dir() {
  local repo="${TMPDIR_SUITE}/t7"
  setup_repo "$repo"
  # Do NOT add any agent worktrees

  local out
  out="$(cd "$repo" && DRY_RUN=0 GIT_MAIN_BRANCH=main WORKTREE_BASE=".claude/worktrees" \
    bash "$CLEANUP_SCRIPT" --force 2>&1)" || true

  assert_contains "t7: empty dir reports no worktrees" "No agent worktrees" "$out"
}

# --------------------------------------------------------------------------
# Test 8: Dirty merged worktree is skipped without --force-dirty
# --------------------------------------------------------------------------
test_dirty_merged_skipped_without_force_dirty() {
  local repo="${TMPDIR_SUITE}/t8"
  setup_repo "$repo"

  local branch="wave-g/2026-05-18/dirty"
  wt_path="$(add_agent_worktree "$repo" "agent-stu901" "$branch")"
  merge_branch "$repo" "$branch"

  # Introduce uncommitted changes in the worktree
  echo "dirty work" >> "${wt_path}/dirty.txt"

  local out
  out="$(cd "$repo" && DRY_RUN=0 GIT_MAIN_BRANCH=main WORKTREE_BASE=".claude/worktrees" \
    bash "$CLEANUP_SCRIPT" --force 2>&1)" || true

  assert_contains    "t8: dirty worktree skipped" "SKIP" "$out"
  assert_path_exists "t8: dirty worktree still present" \
    "${repo}/.claude/worktrees/agent-stu901"
}

# --------------------------------------------------------------------------
# Run all tests (each in its own subshell under the suite tmpdir)
# --------------------------------------------------------------------------
echo ""
echo "cleanup-worktrees.test.sh"
echo "========================="
echo ""

( cd "$TMPDIR_SUITE" && test_dry_run_removes_nothing )
( cd "$TMPDIR_SUITE" && test_merged_removed_with_force )
( cd "$TMPDIR_SUITE" && test_unmerged_with_commits_kept )
( cd "$TMPDIR_SUITE" && test_merged_only_skips_clean_unmerged )
( cd "$TMPDIR_SUITE" && test_agent_locked_worktree_removed )
( cd "$TMPDIR_SUITE" && test_keep_days_skips_recent )
( cd "$TMPDIR_SUITE" && test_empty_worktrees_dir )
( cd "$TMPDIR_SUITE" && test_dirty_merged_skipped_without_force_dirty )

echo ""
echo "──────────────────────────────────"
echo -e "  \033[0;32mPASS: ${PASS}\033[0m  \033[0;31mFAIL: ${FAIL}\033[0m  \033[0;90mSKIP: ${SKIP}\033[0m"
echo "──────────────────────────────────"
echo ""

[[ "$FAIL" -eq 0 ]]
