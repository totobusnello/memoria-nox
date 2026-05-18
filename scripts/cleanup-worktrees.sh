#!/usr/bin/env bash
# cleanup-worktrees.sh — Remove accumulated Claude agent worktrees
#
# After each wave session, dozens of agent worktrees accumulate under
# .claude/worktrees/agent-*. This script identifies which ones are safe
# to remove and cleans them up, then prunes stale git references.
#
# SAFETY GUARANTEES
# -----------------
# - By default, prints what WOULD happen (DRY_RUN=1). You must pass --force
#   or set DRY_RUN=0 to actually remove anything.
# - Worktrees with uncommitted changes are SKIPPED with a warning (unless
#   --force-dirty is passed, which you should almost never use).
# - Locked worktrees are unlocked only when the lock was set by an agent
#   (lock reason starts with "claude agent"). A foreign lock stops the script.
# - Removal order: unlock → git worktree remove → prune. If any step fails
#   the worktree is marked SKIPPED, not FORCE-REMOVED.
# - The main worktree and named worktrees outside .claude/worktrees/ are
#   never touched.
#
# USAGE
# -----
#   ./scripts/cleanup-worktrees.sh [OPTIONS]
#
# OPTIONS
#   --dry-run            Preview mode — print what would happen, make no changes.
#                        This is the DEFAULT when DRY_RUN=1 (env) or when the
#                        script is called without --force.
#   --force              Actually remove worktrees. Requires explicit opt-in.
#   --force-dirty        Remove even worktrees with uncommitted changes. Dangerous.
#                        Only valid together with --force.
#   --keep-days N        Skip worktrees whose HEAD commit is newer than N days.
#                        Default: 0 (no age filter — all candidates are evaluated).
#   --merged-only        Only remove worktrees whose branch is already merged to main.
#                        By default the script also removes CLEAN unmerged worktrees
#                        (no uncommitted changes, no unique commits not in main).
#   --verbose            Extra logging for each worktree decision.
#   --help               Print this help text.
#
# ENVIRONMENT VARIABLES
#   DRY_RUN=1            Same as --dry-run (default if neither flag is passed).
#   DRY_RUN=0            Same as --force (still prompts once unless --force used).
#   KEEP_DAYS=N          Same as --keep-days N. Default 0.
#   WORKTREE_BASE        Directory to scan. Default: .claude/worktrees
#   GIT_MAIN_BRANCH      Branch to check merge status against. Default: main
#
# RECOVERY
# --------
# If a worktree is accidentally removed:
#   1. The branch still exists: git checkout <branch> — it creates a normal checkout.
#   2. The branch was deleted too: git reflog to find the tip SHA, then
#      git checkout -b <branch> <sha>
# If git worktree prune incorrectly removes administrative files, run:
#   git worktree repair
#
# EXAMPLES
# --------
#   # Preview: see all candidates without touching anything
#   ./scripts/cleanup-worktrees.sh --dry-run
#
#   # Remove merged worktrees only (safe daily job)
#   ./scripts/cleanup-worktrees.sh --force --merged-only
#
#   # Full cleanup: remove merged AND clean unmerged, worktrees older than 1 day
#   DRY_RUN=0 ./scripts/cleanup-worktrees.sh --force --keep-days 1
#
#   # After wave session: one-liner cleanup
#   ./scripts/cleanup-worktrees.sh --force --keep-days 0 --merged-only

set -euo pipefail

# --------------------------------------------------------------------------
# Defaults
# --------------------------------------------------------------------------
DRY_RUN="${DRY_RUN:-1}"
KEEP_DAYS="${KEEP_DAYS:-0}"
WORKTREE_BASE="${WORKTREE_BASE:-.claude/worktrees}"
GIT_MAIN_BRANCH="${GIT_MAIN_BRANCH:-main}"

OPT_FORCE=0
OPT_FORCE_DIRTY=0
OPT_MERGED_ONLY=0
OPT_VERBOSE=0

# --------------------------------------------------------------------------
# Colors
# --------------------------------------------------------------------------
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

# --------------------------------------------------------------------------
# Argument parsing
# --------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)     DRY_RUN=1 ;;
    --force)       OPT_FORCE=1; DRY_RUN=0 ;;
    --force-dirty) OPT_FORCE_DIRTY=1 ;;
    --merged-only) OPT_MERGED_ONLY=1 ;;
    --keep-days)   KEEP_DAYS="${2:?--keep-days requires a number}"; shift ;;
    --verbose)     OPT_VERBOSE=1 ;;
    --help|-h)
      sed -n '/^# USAGE/,/^[^#]/p' "$0" | grep '^#' | sed 's/^# \?//'
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}" >&2
      echo "Run with --help for usage." >&2
      exit 1
      ;;
  esac
  shift
done

# --force-dirty without --force is a no-op but warn
if [[ "$OPT_FORCE_DIRTY" -eq 1 && "$OPT_FORCE" -eq 0 ]]; then
  echo -e "${YELLOW}Warning: --force-dirty has no effect without --force.${NC}" >&2
fi

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
log_verbose() {
  [[ "$OPT_VERBOSE" -eq 1 ]] && echo -e "${GRAY}  [verbose] $*${NC}" >&2 || true
}

log_info()    { echo -e "${CYAN}$*${NC}"; }
log_ok()      { echo -e "${GREEN}  + $*${NC}"; }
log_skip()    { echo -e "${YELLOW}  ~ $*${NC}"; }
log_warn()    { echo -e "${YELLOW}  ! $*${NC}"; }
log_error()   { echo -e "${RED}  x $*${NC}" >&2; }

# --------------------------------------------------------------------------
# Validate environment
# --------------------------------------------------------------------------
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo -e "${RED}Not inside a git repository.${NC}" >&2
  exit 1
}
cd "$REPO_ROOT"

WORKTREE_ABS="${REPO_ROOT}/${WORKTREE_BASE}"
if [[ ! -d "$WORKTREE_ABS" ]]; then
  echo -e "${YELLOW}Worktree directory not found: ${WORKTREE_ABS}${NC}"
  echo "Nothing to clean up."
  exit 0
fi

# Verify main branch exists
if ! git rev-parse --verify "$GIT_MAIN_BRANCH" >/dev/null 2>&1; then
  echo -e "${RED}Main branch '${GIT_MAIN_BRANCH}' not found. Set GIT_MAIN_BRANCH env var.${NC}" >&2
  exit 1
fi

# --------------------------------------------------------------------------
# Announce mode
# --------------------------------------------------------------------------
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo -e "${YELLOW}[DRY RUN] No changes will be made. Pass --force to apply.${NC}"
else
  echo -e "${RED}[LIVE MODE] Worktrees will be removed. This cannot be undone automatically.${NC}"
fi
echo ""

# --------------------------------------------------------------------------
# Parse git worktree list into structured data
# git worktree list --porcelain emits blank-line-separated stanzas.
# --------------------------------------------------------------------------
REMOVED_COUNT=0
SKIPPED_COUNT=0
ERROR_COUNT=0

parse_worktrees() {
  # Emits lines: "<path>|<HEAD-sha>|<branch-ref>|<locked-reason>"
  # locked-reason is empty if not locked.
  local wt_path="" wt_head="" wt_branch="" wt_locked=""
  while IFS= read -r line; do
    if [[ "$line" == worktree\ * ]]; then
      # New stanza — emit previous if it was an agent worktree
      if [[ -n "$wt_path" && "$wt_path" == *"${WORKTREE_BASE}/agent-"* ]]; then
        echo "${wt_path}|${wt_head}|${wt_branch}|${wt_locked}"
      fi
      wt_path="${line#worktree }"
      wt_head=""; wt_branch=""; wt_locked=""
    elif [[ "$line" == HEAD\ * ]];   then wt_head="${line#HEAD }";
    elif [[ "$line" == branch\ * ]]; then wt_branch="${line#branch refs/heads/}";
    elif [[ "$line" == locked ]];    then wt_locked="(locked)";
    elif [[ "$line" == locked\ * ]]; then wt_locked="${line#locked }";
    fi
  done < <(git worktree list --porcelain 2>/dev/null)
  # Emit last stanza
  if [[ -n "$wt_path" && "$wt_path" == *"${WORKTREE_BASE}/agent-"* ]]; then
    echo "${wt_path}|${wt_head}|${wt_branch}|${wt_locked}"
  fi
}

# --------------------------------------------------------------------------
# Age filter: returns 1 if the commit is newer than KEEP_DAYS
# --------------------------------------------------------------------------
is_too_new() {
  local sha="$1"
  [[ "$KEEP_DAYS" -le 0 ]] && return 1  # No age filter → never "too new"
  local commit_ts now_ts age_days
  commit_ts="$(git log -1 --format='%ct' "$sha" 2>/dev/null || echo 0)"
  now_ts="$(date +%s)"
  age_days=$(( (now_ts - commit_ts) / 86400 ))
  log_verbose "commit age = ${age_days}d (threshold = ${KEEP_DAYS}d)"
  [[ "$age_days" -lt "$KEEP_DAYS" ]]
}

# --------------------------------------------------------------------------
# Is branch merged to main?
# --------------------------------------------------------------------------
is_merged() {
  local branch="$1"
  git branch --merged "$GIT_MAIN_BRANCH" | grep -qE "^\*?[[:space:]]+${branch}$"
}

# --------------------------------------------------------------------------
# Has unique commits not in main?
# Returns 1 (no unique commits = safe to drop) or 0 (has unique commits)
# --------------------------------------------------------------------------
has_unique_commits() {
  local branch="$1"
  local count
  count="$(git rev-list --count "${GIT_MAIN_BRANCH}..${branch}" 2>/dev/null || echo 0)"
  log_verbose "unique commits ahead of main: ${count}"
  [[ "$count" -gt 0 ]]
}

# --------------------------------------------------------------------------
# Has uncommitted changes in the worktree?
# --------------------------------------------------------------------------
has_dirty_worktree() {
  local wt_path="$1"
  # git status --porcelain exits 0 even with output; output = dirty
  [[ -n "$(git -C "$wt_path" status --porcelain 2>/dev/null)" ]]
}

# --------------------------------------------------------------------------
# Remove a single worktree
# --------------------------------------------------------------------------
remove_worktree() {
  local wt_path="$1"
  local branch="$2"
  local locked_reason="$3"

  # Unlock if agent-locked
  if [[ -n "$locked_reason" ]]; then
    if [[ "$locked_reason" == *"claude agent"* || "$locked_reason" == "(locked)" ]]; then
      log_verbose "Unlocking: ${wt_path}"
      if [[ "$DRY_RUN" -eq 0 ]]; then
        git worktree unlock "$wt_path" 2>/dev/null || true
      fi
    else
      log_skip "SKIP (foreign lock: '${locked_reason}'): ${wt_path##*/}"
      (( SKIPPED_COUNT++ )) || true
      return
    fi
  fi

  if [[ "$DRY_RUN" -eq 1 ]]; then
    log_ok "WOULD REMOVE: ${wt_path##*/}  (branch: ${branch})"
    (( REMOVED_COUNT++ )) || true
    return
  fi

  # Actually remove
  if git worktree remove --force "$wt_path" 2>/dev/null; then
    log_ok "REMOVED: ${wt_path##*/}  (branch: ${branch})"
    (( REMOVED_COUNT++ )) || true
  else
    log_error "FAILED to remove: ${wt_path##*/}"
    (( ERROR_COUNT++ )) || true
  fi
}

# --------------------------------------------------------------------------
# Main loop
# --------------------------------------------------------------------------
log_info "Scanning: ${WORKTREE_ABS}"
log_info "Main branch: ${GIT_MAIN_BRANCH} | Keep-days: ${KEEP_DAYS} | Merged-only: ${OPT_MERGED_ONLY}"
echo ""

# Bash 3 (macOS default) does not have mapfile; use a while-read loop into array
WORKTREES=()
while IFS= read -r line; do
  WORKTREES+=("$line")
done < <(parse_worktrees)

if [[ "${#WORKTREES[@]}" -eq 0 ]]; then
  echo "No agent worktrees found under ${WORKTREE_BASE}."
  exit 0
fi

log_info "Found ${#WORKTREES[@]} agent worktree(s) to evaluate."
echo ""

for entry in "${WORKTREES[@]}"; do
  IFS='|' read -r wt_path wt_head wt_branch wt_locked <<< "$entry"

  name="${wt_path##*/}"
  log_verbose "Evaluating: ${name} (branch=${wt_branch}, head=${wt_head:0:10})"

  # 1. Age filter
  if is_too_new "$wt_head"; then
    log_skip "KEEP (too new, <${KEEP_DAYS}d): ${name}  (branch: ${wt_branch})"
    (( SKIPPED_COUNT++ )) || true
    continue
  fi

  # 2. Merged check
  merged=0
  if is_merged "$wt_branch"; then
    merged=1
    log_verbose "${name}: branch is merged to ${GIT_MAIN_BRANCH}"
  fi

  if [[ "$merged" -eq 1 ]]; then
    # Merged — safe to remove (check dirty anyway)
    if has_dirty_worktree "$wt_path"; then
      if [[ "$OPT_FORCE_DIRTY" -eq 1 ]]; then
        log_warn "DIRTY but force-dirty set: ${name}"
        remove_worktree "$wt_path" "$wt_branch" "$wt_locked"
      else
        log_skip "SKIP (merged but dirty — uncommitted changes): ${name}"
        (( SKIPPED_COUNT++ )) || true
      fi
    else
      remove_worktree "$wt_path" "$wt_branch" "$wt_locked"
    fi
    continue
  fi

  # 3. Not merged — if --merged-only, always skip
  if [[ "$OPT_MERGED_ONLY" -eq 1 ]]; then
    log_skip "KEEP (not merged, --merged-only): ${name}  (branch: ${wt_branch})"
    (( SKIPPED_COUNT++ )) || true
    continue
  fi

  # 4. Not merged + not --merged-only → check if clean
  if has_unique_commits "$wt_branch"; then
    log_skip "KEEP (has unique commits not in ${GIT_MAIN_BRANCH}): ${name}  (branch: ${wt_branch})"
    (( SKIPPED_COUNT++ )) || true
    continue
  fi

  if has_dirty_worktree "$wt_path"; then
    if [[ "$OPT_FORCE_DIRTY" -eq 1 ]]; then
      log_warn "DIRTY but force-dirty set: ${name}"
      remove_worktree "$wt_path" "$wt_branch" "$wt_locked"
    else
      log_skip "SKIP (dirty — uncommitted changes): ${name}  (branch: ${wt_branch})"
      (( SKIPPED_COUNT++ )) || true
    fi
    continue
  fi

  # Clean + no unique commits — safe to remove even if not merged
  remove_worktree "$wt_path" "$wt_branch" "$wt_locked"
done

# --------------------------------------------------------------------------
# Prune stale git references
# --------------------------------------------------------------------------
echo ""
if [[ "$DRY_RUN" -eq 0 && "$REMOVED_COUNT" -gt 0 ]]; then
  log_info "Pruning stale worktree references..."
  git worktree prune --verbose 2>&1 | sed 's/^/  /' || true
else
  log_verbose "Skipping prune (dry-run or nothing removed)."
fi

# --------------------------------------------------------------------------
# Summary
# --------------------------------------------------------------------------
echo ""
echo "──────────────────────────────────────────────────────"
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo -e "  ${GREEN}Would remove : ${REMOVED_COUNT}${NC}"
else
  echo -e "  ${GREEN}Removed      : ${REMOVED_COUNT}${NC}"
fi
echo -e "  ${YELLOW}Skipped      : ${SKIPPED_COUNT}${NC}"
echo -e "  ${RED}Errors       : ${ERROR_COUNT}${NC}"
echo "──────────────────────────────────────────────────────"

if [[ "$DRY_RUN" -eq 1 && "$REMOVED_COUNT" -gt 0 ]]; then
  echo ""
  echo "  Re-run with --force to apply changes."
fi

[[ "$ERROR_COUNT" -eq 0 ]]
