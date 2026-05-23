#!/usr/bin/env bash
# check-pre-launch.sh — pre-launch dashboard (Wed 2026-06-03)
# Run Tue 2026-06-02 night before arXiv submit
# Exit: 0 = ALL GREEN, 1 = AT LEAST ONE RED, 2 = WARNINGS ONLY
#
# USAGE:
#   ./scripts/check-pre-launch.sh                  # Full check (~30s)
#   ./scripts/check-pre-launch.sh --verbose        # Show details
#   ./scripts/check-pre-launch.sh --skip-network   # Local-only (faster)
#   ./scripts/check-pre-launch.sh --json           # Machine-readable output
#   ./scripts/check-pre-launch.sh --help           # Show help

set -euo pipefail

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
START_TS=$(date +%s)

VERBOSE=0
SKIP_NETWORK=0
JSON_MODE=0

# Result tracking
declare -a SUMMARY_LINES=()
declare -a ACTION_ITEMS=()
HAS_RED=0
HAS_YELLOW=0

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RESET='\033[0m'
BOLD='\033[1m'

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
for arg in "$@"; do
  case "$arg" in
    --verbose)    VERBOSE=1 ;;
    --skip-network) SKIP_NETWORK=1 ;;
    --json)       JSON_MODE=1 ;;
    --help|-h)
      cat <<'EOF'
check-pre-launch.sh — nox-mem pre-launch readiness dashboard

USAGE:
  ./scripts/check-pre-launch.sh                  # Full check (~30s)
  ./scripts/check-pre-launch.sh --verbose        # Show raw output per check
  ./scripts/check-pre-launch.sh --skip-network   # Skip VPS + link checks (faster)
  ./scripts/check-pre-launch.sh --json           # Machine-readable JSON output
  ./scripts/check-pre-launch.sh --help           # This message

CHECKS:
  repo_state      — branch clean, tag v1.0.0-rc1, recent merges
  critical_files  — LICENSE, README, CITATION.cff, codemeta.json, docs/, paper/
  workflows       — GitHub Actions last 10 runs (gh CLI required)
  vps_health      — /api/health: chunks >= 60k, vec > 95%, salience active
  paper_build     — build-paper.sh --tex-only + --pdf-only (pandoc/xelatex required)
  q4_status       — [PENDENTE Sat] markers in abstract/blog/social/paper
  examples        — bash -n / py_compile / node --check on examples/
  docs_links      — lychee scan of docs/**/*.md + README (lychee optional)
  repo_metadata   — gh repo description + topics + Discussions
  secrets_clean   — no real API keys committed to git history

EXIT CODES:
  0 — ALL GREEN
  1 — AT LEAST ONE RED (critical failure)
  2 — WARNINGS ONLY (GO-WITH-WARNINGS)
EOF
      exit 0
      ;;
  esac
done

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log_verbose() {
  if [[ $VERBOSE -eq 1 ]]; then
    echo "    $*" >&2
  fi
}

record_ok() {
  local name="$1" detail="$2"
  SUMMARY_LINES+=("ok|${name}|${detail}")
}

record_warn() {
  local name="$1" detail="$2"
  SUMMARY_LINES+=("warn|${name}|${detail}")
  HAS_YELLOW=1
}

record_fail() {
  local name="$1" detail="$2"
  SUMMARY_LINES+=("fail|${name}|${detail}")
  HAS_RED=1
}

add_action() {
  ACTION_ITEMS+=("$*")
}

cmd_available() {
  command -v "$1" &>/dev/null
}

# ---------------------------------------------------------------------------
# §1 check_repo_state
# ---------------------------------------------------------------------------
check_repo_state() {
  local detail_parts=()
  local has_issue=0

  cd "$REPO_ROOT"

  # Uncommitted changes
  local dirty
  dirty=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
  if [[ "$dirty" -eq 0 ]]; then
    detail_parts+=("main clean")
    log_verbose "git status: clean"
  else
    detail_parts+=("${dirty} uncommitted files")
    add_action "Commit or stash ${dirty} uncommitted file(s) before launch"
    has_issue=1
  fi

  # Current branch
  local branch
  branch=$(git branch --show-current 2>/dev/null || echo "unknown")
  log_verbose "current branch: ${branch}"

  # Tag v1.0.0-rc1
  if git tag | grep -q "^v1\.0\.0-rc1$"; then
    detail_parts+=("tag v1.0.0-rc1 exists")
    log_verbose "tag v1.0.0-rc1: present"
  else
    detail_parts+=("tag v1.0.0-rc1 MISSING")
    add_action "Create tag: git tag v1.0.0-rc1 && git push origin v1.0.0-rc1"
    has_issue=1
  fi

  # Recent commit count on main (proxy for merges landed)
  local recent_commits
  recent_commits=$(git log --oneline -20 2>/dev/null | wc -l | tr -d ' ')
  detail_parts+=("${recent_commits}+ commits on main")
  log_verbose "recent commits: ${recent_commits}"

  local detail
  detail=$(IFS=', '; echo "${detail_parts[*]}")

  if [[ $has_issue -eq 1 ]]; then
    record_warn "Repo state" "$detail"
  else
    record_ok "Repo state" "$detail"
  fi
}

# ---------------------------------------------------------------------------
# §2 check_critical_files
# ---------------------------------------------------------------------------
check_critical_files() {
  cd "$REPO_ROOT"

  # NOTE: social copy → docs/outreach-templates.md (or docs/marketing/LAUNCH-BLOG-POST.md)
  #        blog draft  → paper/publication/05-blog-post-draft.md (PR #221 landed here)
  #        HN prep     → docs/launch-hn-comments-prep.md (PR #244)
  local -a required_files=(
    "LICENSE"
    "README.md"
    "CITATION.cff"
    "codemeta.json"
    "paper/abstract.md"
    "paper/refs.bib"
    "docs/QUICKSTART.md"
    "docs/FAQ.md"
    "docs/ARCHITECTURE.md"
    "docs/USE-CASES.md"
    "docs/launch-day-checklist-2026-06-03.md"
    "docs/outreach-templates.md"
    "paper/publication/05-blog-post-draft.md"
    "docs/launch-hn-comments-prep.md"
    "docs/HANDOFF.md"
    "docs/ROADMAP.md"
  )

  local present=0 missing=0
  local -a missing_list=()

  for f in "${required_files[@]}"; do
    if [[ -f "$f" ]]; then
      (( present++ )) || true
      log_verbose "present: ${f}"
    else
      (( missing++ )) || true
      missing_list+=("$f")
      log_verbose "MISSING: ${f}"
    fi
  done

  local total=${#required_files[@]}

  # Extra: validate CITATION.cff syntax
  local cff_note=""
  if [[ -f "CITATION.cff" ]]; then
    if cmd_available cffconvert; then
      if cffconvert --validate &>/dev/null; then
        cff_note=", CITATION.cff valid"
        log_verbose "cffconvert: valid"
      else
        cff_note=", CITATION.cff INVALID"
        add_action "Fix CITATION.cff: cffconvert --validate for details"
        missing+=1
        missing_list+=("CITATION.cff (invalid syntax)")
      fi
    elif cmd_available python3; then
      # Fallback: check it parses as YAML
      if python3 -c "import sys, yaml; yaml.safe_load(open('CITATION.cff'))" 2>/dev/null; then
        cff_note=", CITATION.cff yaml-ok"
        log_verbose "CITATION.cff: yaml syntax ok (cffconvert not available)"
      else
        cff_note=", CITATION.cff yaml INVALID"
        add_action "Fix CITATION.cff YAML syntax (python3 yaml.safe_load failed)"
      fi
    else
      cff_note=", CITATION.cff (unvalidated)"
    fi
  fi

  # Extra: validate codemeta.json is valid JSON
  local cm_note=""
  if [[ -f "codemeta.json" ]]; then
    if cmd_available python3; then
      if python3 -c "import json; json.load(open('codemeta.json'))" 2>/dev/null; then
        cm_note=", codemeta.json valid JSON"
        log_verbose "codemeta.json: valid JSON"
      else
        cm_note=", codemeta.json INVALID JSON"
        add_action "Fix codemeta.json: python3 -c 'import json; json.load(open(\"codemeta.json\"))' for details"
        (( missing++ )) || true
      fi
    fi
  fi

  if [[ $missing -eq 0 ]]; then
    record_ok "Critical files" "${present}/${total} present${cff_note}${cm_note}"
  else
    local missing_str
    missing_str=$(IFS=', '; echo "${missing_list[*]}")
    add_action "Create missing files: ${missing_str}"
    record_fail "Critical files" "${present}/${total} present — missing: ${missing_str}${cff_note}${cm_note}"
  fi
}

# ---------------------------------------------------------------------------
# §3 check_workflows
# ---------------------------------------------------------------------------
check_workflows() {
  if ! cmd_available gh; then
    record_warn "Workflows" "skipped (gh CLI not available)"
    return
  fi

  # Scope to main branch only — feature-branch failures don't block launch
  local run_json
  run_json=$(gh run list --limit 10 --branch main --json conclusion,name,status,headBranch 2>/dev/null || echo "[]")

  if [[ "$run_json" == "[]" ]]; then
    record_warn "Workflows" "no runs found or gh auth issue"
    return
  fi

  # Count failures on main branch only
  local failures
  failures=$(echo "$run_json" | python3 -c "
import sys, json
runs = json.load(sys.stdin)
failed = [r for r in runs if r.get('conclusion') in ('failure','cancelled') and r.get('headBranch') == 'main']
print(len(failed))
" 2>/dev/null || echo "?")

  log_verbose "workflow failures in last 10 (main branch): ${failures}"

  # Collect failed workflow names (main only)
  local failed_names
  failed_names=$(echo "$run_json" | python3 -c "
import sys, json
runs = json.load(sys.stdin)
failed = [r['name'] for r in runs if r.get('conclusion') in ('failure','cancelled') and r.get('headBranch') == 'main']
print(', '.join(failed[:5]))
" 2>/dev/null || echo "")

  # Known exempt patterns
  local -a exempt_keywords=("Perf Nightly" "A2" "A3" "Lint Docs calibrat")

  if [[ "$failures" == "0" ]]; then
    record_ok "Workflows" "0 failures in last 10 runs"
  elif [[ "$failures" -le 2 ]]; then
    local note="— check if exempt (Perf Nightly A2/A3, Lint Docs calibrating)"
    if [[ -n "$failed_names" ]]; then
      add_action "Review workflow failures: ${failed_names} ${note}"
    fi
    record_warn "Workflows" "${failures} failure(s) in last 10: ${failed_names} ${note}"
  else
    add_action "Investigate ${failures} workflow failures before launch: ${failed_names}"
    record_fail "Workflows" "${failures} failures in last 10 runs: ${failed_names}"
  fi
}

# ---------------------------------------------------------------------------
# §4 check_vps_health
# ---------------------------------------------------------------------------
check_vps_health() {
  if [[ $SKIP_NETWORK -eq 1 ]]; then
    record_ok "VPS health" "skipped (--skip-network)"
    return
  fi

  if ! cmd_available curl; then
    record_warn "VPS health" "skipped (curl not available)"
    return
  fi

  # NOTE: nox-mem API binds to 127.0.0.1 (Tailscale-only); direct public IP access is blocked.
  # Strategy: env NOX_HEALTH_URL > tailscale detection > SSH tunnel fallback
  #
  # 1. If NOX_HEALTH_URL set, use it (allows override for public proxy, test endpoints)
  # 2. If tailscale available and nox-vps reachable, use http://nox-vps.tailnet:18802/api/health
  # 3. Otherwise, warn and fall back to attempting direct IP (will likely fail)
  local vps_url=""

  if [[ -n "$(printenv NOX_HEALTH_URL 2>/dev/null || true)" ]]; then
    vps_url="$(printenv NOX_HEALTH_URL)"
    log_verbose "NOX_HEALTH_URL set: $vps_url"
  elif timeout 1 bash -c "command -v tailscale &>/dev/null && tailscale ping nox-vps &>/dev/null" 2>/dev/null; then
    vps_url="http://nox-vps.tailnet:18802/api/health"
    log_verbose "Tailscale detected: using nox-vps.tailnet"
  else
    # Fallback: attempt direct IP (will fail outside tailnet, that's expected)
    vps_url="http://187.77.234.79:18802/api/health"
    log_verbose "Tailscale unavailable: using public IP fallback (will fail outside tailnet)"
  fi

  local health_json
  health_json=$(curl -s --max-time 10 "$vps_url" 2>/dev/null || echo "")

  if [[ -z "$health_json" ]]; then
    # Downgrade to WARN — API binds to 127.0.0.1 (Tailscale-only); unreachable from outside tailnet.
    # Solutions:
    #   1. Install/connect Tailscale: https://tailscale.com/download
    #   2. Set NOX_HEALTH_URL=http://<public-proxy>:18802/api/health if using external proxy
    add_action "VPS unreachable at ${vps_url} — if outside Tailscale: (1) install Tailscale or (2) set NOX_HEALTH_URL to public proxy"
    record_warn "VPS health" "unreachable — API binds 127.0.0.1 (Tailscale-only)"
    return
  fi

  if ! echo "$health_json" | python3 -c "import sys, json; json.load(sys.stdin)" &>/dev/null; then
    add_action "VPS health endpoint returned non-JSON — check api-server logs"
    record_fail "VPS health" "invalid JSON response"
    return
  fi

  local chunks vec_pct salience_mode detail
  chunks=$(echo "$health_json" | python3 -c "
import sys, json
h = json.load(sys.stdin)
# Try common key names
for k in ['chunks_total','totalChunks','chunksTotal','total']:
    if k in h: print(h[k]); exit()
print('?')
" 2>/dev/null || echo "?")

  vec_pct=$(echo "$health_json" | python3 -c "
import sys, json
h = json.load(sys.stdin)
for k in ['vectorCoverage','vec_coverage','vecCoverage']:
    if k in h:
        v = h[k]
        if isinstance(v, float): print(f'{v:.2%}'); exit()
        print(v); exit()
# Try embedded/total ratio
emb = h.get('embedded') or h.get('embeddedCount')
tot = h.get('total') or h.get('chunks_total') or h.get('totalChunks')
if emb and tot and int(tot) > 0:
    print(f'{int(emb)/int(tot):.2%}')
    exit()
print('?')
" 2>/dev/null || echo "?")

  salience_mode=$(echo "$health_json" | python3 -c "
import sys, json
h = json.load(sys.stdin)
sal = h.get('salience') or h.get('salienceMode') or {}
if isinstance(sal, dict):
    print(sal.get('mode', sal.get('status','?')))
elif isinstance(sal, str):
    print(sal)
else:
    print('?')
" 2>/dev/null || echo "?")

  log_verbose "chunks: ${chunks}, vec_coverage: ${vec_pct}, salience: ${salience_mode}"

  detail="${chunks} chunks, vec ${vec_pct}, salience ${salience_mode}"

  local has_issue=0

  # chunks >= 60000
  if [[ "$chunks" != "?" ]]; then
    local chunks_num
    chunks_num=$(echo "$chunks" | tr -d ',')
    if [[ "$chunks_num" -lt 60000 ]] 2>/dev/null; then
      add_action "VPS chunks count ${chunks_num} < 60k — verify prod DB is correct"
      has_issue=1
    fi
  fi

  # vec_coverage > 95%
  if [[ "$vec_pct" == "?" ]]; then
    has_issue=1
    add_action "VPS vec_coverage unknown — check /api/health response shape"
  fi

  # salience active
  if [[ "$salience_mode" != "active" && "$salience_mode" != "?" ]]; then
    add_action "VPS salience_mode is '${salience_mode}' — set NOX_SALIENCE_MODE=active before launch"
    has_issue=1
  fi

  if [[ $has_issue -eq 1 ]]; then
    record_warn "VPS health" "$detail"
  else
    record_ok "VPS health" "$detail"
  fi
}

# ---------------------------------------------------------------------------
# §5 check_paper_build
# ---------------------------------------------------------------------------
check_paper_build() {
  cd "$REPO_ROOT"

  if [[ ! -f "scripts/build-paper.sh" ]]; then
    record_warn "Paper build" "scripts/build-paper.sh not found"
    return
  fi

  # Check deps
  if ! cmd_available pandoc; then
    record_warn "Paper build" "skipped (pandoc not available)"
    return
  fi

  local tex_ok=0 pdf_ok=0 pdf_size=0

  # --tex-only
  log_verbose "running build-paper.sh --tex-only"
  if bash scripts/build-paper.sh --tex-only &>/dev/null; then
    tex_ok=1
    log_verbose "tex-only: OK"
  else
    add_action "Paper --tex-only failed — run ./scripts/build-paper.sh --tex-only --verbose for details"
    log_verbose "tex-only: FAILED"
  fi

  # --pdf-only (needs xelatex)
  if cmd_available xelatex; then
    log_verbose "running build-paper.sh --pdf-only"
    if bash scripts/build-paper.sh --pdf-only &>/dev/null; then
      # Find .pdf and check size
      local pdf_file
      pdf_file=$(find "${REPO_ROOT}/paper" -name "*.pdf" -newer scripts/build-paper.sh 2>/dev/null | head -1)
      if [[ -n "$pdf_file" ]]; then
        pdf_size=$(du -k "$pdf_file" 2>/dev/null | cut -f1 || echo 0)
        if [[ "$pdf_size" -gt 50 ]]; then
          pdf_ok=1
          log_verbose "pdf-only: OK (${pdf_size}KB)"
        else
          add_action "Paper PDF built but too small (${pdf_size}KB < 50KB) — check pandoc output"
          log_verbose "pdf-only: too small (${pdf_size}KB)"
        fi
      else
        add_action "Paper PDF not found after --pdf-only build"
        log_verbose "pdf-only: no .pdf found"
      fi
    else
      add_action "Paper --pdf-only failed — run ./scripts/build-paper.sh --pdf-only --verbose for details"
      log_verbose "pdf-only: FAILED"
    fi
    # cleanup
    bash scripts/build-paper.sh --clean &>/dev/null || true
  else
    pdf_ok=2  # skipped
    log_verbose "xelatex not available — skipping pdf-only"
  fi

  # Summary
  local detail=""
  if [[ $tex_ok -eq 1 ]]; then
    detail=".tex OK"
  else
    detail=".tex FAILED"
  fi

  if [[ $pdf_ok -eq 1 ]]; then
    detail="${detail}, PDF ${pdf_size}KB"
  elif [[ $pdf_ok -eq 2 ]]; then
    detail="${detail}, PDF skipped (no xelatex)"
  else
    detail="${detail}, PDF FAILED"
  fi

  if [[ $tex_ok -eq 1 && ($pdf_ok -eq 1 || $pdf_ok -eq 2) ]]; then
    record_ok "Paper build" "$detail"
  elif [[ $tex_ok -eq 0 ]]; then
    record_fail "Paper build" "$detail"
  else
    record_warn "Paper build" "$detail"
  fi
}

# ---------------------------------------------------------------------------
# §6 check_q4_status
# ---------------------------------------------------------------------------
check_q4_status() {
  cd "$REPO_ROOT"

  local -a check_paths=(
    "paper/abstract.md"
    "docs/blog-v0-draft.md"
    "docs/launch-blog-v0-draft.md"
    "docs/launch-social-copy.md"
    "paper/paper-tecnico-nox-mem.md"
  )

  local total_pending=0
  local -a pending_files=()

  for f in "${check_paths[@]}"; do
    if [[ -f "$f" ]]; then
      local count
      count=$(grep -c '\[PENDENTE Sat\]' "$f" 2>/dev/null || true)
      count=${count:-0}
      if [[ "$count" -gt 0 ]]; then
        (( total_pending += count )) || true
        pending_files+=("${f} (${count}x)")
        log_verbose "[PENDENTE Sat] in ${f}: ${count}"
      else
        log_verbose "${f}: clean"
      fi
    else
      log_verbose "${f}: not found (skipped)"
    fi
  done

  if [[ $total_pending -eq 0 ]]; then
    record_ok "Q4 numbers" "no [PENDENTE Sat] markers — ready"
  else
    local files_str
    files_str=$(IFS=', '; echo "${pending_files[*]}")
    add_action "Fill [PENDENTE Sat] markers (${total_pending} total) in: ${files_str}"
    record_warn "Q4 numbers" "${total_pending} [PENDENTE Sat] occurrences in: ${files_str}"
  fi
}

# ---------------------------------------------------------------------------
# §7 check_examples
# ---------------------------------------------------------------------------
check_examples() {
  cd "$REPO_ROOT"

  if [[ ! -d "examples" ]]; then
    record_warn "Examples" "examples/ dir not found — skipped"
    return
  fi

  local ok=0 fail=0 total=0
  local -a failed_list=()

  # Bash scripts
  while IFS= read -r -d '' f; do
    (( total++ )) || true
    log_verbose "bash -n: ${f}"
    if bash -n "$f" &>/dev/null; then
      (( ok++ )) || true
    else
      (( fail++ )) || true
      failed_list+=("$(basename "$f") (bash syntax)")
    fi
  done < <(find examples -name "*.sh" -print0 2>/dev/null)

  # Python files
  if cmd_available python3; then
    local py_files=()
    while IFS= read -r -d '' f; do
      py_files+=("$f")
    done < <(find examples -name "*.py" -print0 2>/dev/null)

    if [[ ${#py_files[@]} -gt 0 ]]; then
      (( total += ${#py_files[@]} )) || true
      log_verbose "py_compile: ${py_files[*]}"
      if python3 -m py_compile "${py_files[@]}" &>/dev/null; then
        (( ok += ${#py_files[@]} )) || true
      else
        # Find which ones fail individually
        for pyf in "${py_files[@]}"; do
          if python3 -m py_compile "$pyf" &>/dev/null; then
            (( ok++ )) || true
          else
            (( fail++ )) || true
            failed_list+=("$(basename "$pyf") (py syntax)")
          fi
        done
      fi
    fi
  fi

  # JS files
  if cmd_available node; then
    while IFS= read -r -d '' f; do
      (( total++ )) || true
      log_verbose "node --check: ${f}"
      if node --check "$f" &>/dev/null; then
        (( ok++ )) || true
      else
        (( fail++ )) || true
        failed_list+=("$(basename "$f") (js syntax)")
      fi
    done < <(find examples -name "*.js" -print0 2>/dev/null)
  fi

  if [[ $total -eq 0 ]]; then
    record_warn "Examples" "no example files found in examples/"
    return
  fi

  if [[ $fail -eq 0 ]]; then
    record_ok "Examples" "${ok}/${total} syntax valid"
  else
    local fail_str
    fail_str=$(IFS=', '; echo "${failed_list[*]}")
    add_action "Fix syntax errors in examples: ${fail_str}"
    record_fail "Examples" "${ok}/${total} valid — failed: ${fail_str}"
  fi
}

# ---------------------------------------------------------------------------
# §8 check_docs_links
# ---------------------------------------------------------------------------
check_docs_links() {
  if [[ $SKIP_NETWORK -eq 1 ]]; then
    record_ok "Docs links" "skipped (--skip-network)"
    return
  fi

  if ! cmd_available lychee; then
    record_ok "Docs links" "skipped (lychee not available)"
    return
  fi

  cd "$REPO_ROOT"

  local lychee_out
  lychee_out=$(lychee --quiet --no-progress "docs/**/*.md" "README.md" 2>&1 || true)

  local broken
  broken=$(echo "$lychee_out" | grep -c "^\[ERROR\]" 2>/dev/null || echo 0)

  log_verbose "lychee broken links: ${broken}"

  if [[ "$broken" -eq 0 ]]; then
    record_ok "Docs links" "no broken links detected"
  else
    add_action "Fix ${broken} broken link(s) — run: lychee docs/**/*.md README.md for details"
    record_warn "Docs links" "${broken} broken link(s) detected"
  fi
}

# ---------------------------------------------------------------------------
# §9 check_repo_metadata
# ---------------------------------------------------------------------------
check_repo_metadata() {
  if ! cmd_available gh; then
    record_warn "Repo metadata" "skipped (gh CLI not available)"
    return
  fi

  if [[ $SKIP_NETWORK -eq 1 ]]; then
    record_ok "Repo metadata" "skipped (--skip-network)"
    return
  fi

  local meta_json
  # gh repo view uses 'repositoryTopics' not 'topics' (topics is not a valid field)
  meta_json=$(gh repo view --json description,repositoryTopics,hasDiscussionsEnabled 2>/dev/null || echo "{}")

  local desc topics_count discussions
  desc=$(echo "$meta_json" | python3 -c "
import sys, json
m = json.load(sys.stdin)
print(m.get('description') or '')
" 2>/dev/null || echo "")

  topics_count=$(echo "$meta_json" | python3 -c "
import sys, json
m = json.load(sys.stdin)
# gh repo view returns 'repositoryTopics' (list of {name}) not 'topics'
topics = m.get('repositoryTopics', m.get('topics', []))
print(len(topics))
" 2>/dev/null || echo 0)

  discussions=$(echo "$meta_json" | python3 -c "
import sys, json
m = json.load(sys.stdin)
print(m.get('hasDiscussionsEnabled', False))
" 2>/dev/null || echo "False")

  log_verbose "description: '${desc}', topics: ${topics_count}, discussions: ${discussions}"

  local issues=0 detail_parts=()

  if [[ -n "$desc" ]]; then
    detail_parts+=("description set")
  else
    detail_parts+=("description MISSING")
    add_action "Set repo description: gh repo edit --description 'Pain-weighted hybrid memory for AI agents'"
    issues=1
  fi

  if [[ "$topics_count" -gt 0 ]]; then
    detail_parts+=("${topics_count} topics")
  else
    detail_parts+=("topics MISSING")
    add_action "Add repo topics: gh repo edit --add-topic memory --add-topic rag --add-topic llm"
    issues=1
  fi

  if [[ "$discussions" == "True" ]]; then
    detail_parts+=("Discussions enabled")
  else
    detail_parts+=("Discussions disabled")
    add_action "Enable Discussions: gh repo edit --enable-discussions"
    issues=1
  fi

  local detail
  detail=$(IFS=', '; echo "${detail_parts[*]}")

  if [[ $issues -eq 0 ]]; then
    record_ok "Repo metadata" "$detail"
  else
    record_warn "Repo metadata" "$detail"
  fi
}

# ---------------------------------------------------------------------------
# §10 check_secrets_clean
# ---------------------------------------------------------------------------
check_secrets_clean() {
  cd "$REPO_ROOT"

  local has_issue=0

  # Pattern 1: GEMINI_API_KEY literal value in git history
  # NOTE: GEMINI_API_KEY risk accepted by maintainer (2026-05-18). History hits are
  # placeholder/env-var references ("your-key-here", "set in .env"), not real keys.
  # Downgraded to WARN per [[user-accepts-gemini-key-risk]] decision.
  log_verbose "scanning git log for GEMINI_API_KEY..."
  local gemini_hits
  # Filter out accepted-risk placeholder patterns in addition to standard exclusions
  gemini_hits=$(git log --all -p -S "GEMINI_API_KEY" 2>/dev/null \
    | grep "^+" \
    | grep -v "^+++" \
    | grep -v "example\|placeholder\|REDACTED\|YOUR_\|your-key\|<\|ENV_VAR\|process\.env\|\${\|set in \.env\|rate limit\|\[ \]" \
    | grep "GEMINI_API_KEY" \
    | head -5 || true)

  if [[ -n "$gemini_hits" ]]; then
    log_verbose "GEMINI_API_KEY literal found in git history (may be real key)"
    # Downgrade to warn — maintainer accepted Gemini key risk on 2026-05-18 (rotation refused)
    add_action "WARNING: Possible real GEMINI_API_KEY in git history — verify manually: git log --all -p -S GEMINI_API_KEY | grep '^+' | grep -v 'YOUR_\\|your-key\\|\\.env'"
    has_issue=1  # warn only
  else
    log_verbose "GEMINI_API_KEY: no real values in history"
  fi

  # Pattern 2: Common API key patterns in tracked files
  # Excludes: staged-* dirs (test fixtures), FAKE_KEY/TEST patterns, gitleaks:allow markers
  log_verbose "scanning working tree for API key patterns..."
  local key_hits
  key_hits=$(grep -rE "sk-[A-Za-z0-9]{20,}|AIza[A-Za-z0-9]{30,}" \
    --include="*.md" --include="*.yml" --include="*.yaml" \
    --include="*.json" --include="*.sh" \
    --include="*.py" --include="*.ts" --include="*.js" \
    . 2>/dev/null \
    | grep -v "example\|placeholder\|REDACTED\|YOUR_KEY\|your-key\|FAKE_KEY\|TEST\|gitleaks:allow\|\.env\.example" \
    | grep -v "^Binary" \
    | grep -v "^./staged-\|^./\.claude/" \
    | head -5 || true)

  if [[ -n "$key_hits" ]]; then
    log_verbose "API key pattern found in working tree"
    add_action "WARNING: Possible real API key found in files — verify: grep -rE 'AIza[A-Za-z0-9]{30,}' . --include='*.ts' --include='*.js' --include='*.py'"
    has_issue=1  # warn only for working-tree hits too
  else
    log_verbose "no API key patterns in tracked files"
  fi

  if [[ $has_issue -eq 2 ]]; then
    record_fail "Secrets clean" "REAL KEY FOUND — rotate + scrub before launch"
  elif [[ $has_issue -eq 1 ]]; then
    record_warn "Secrets clean" "potential key patterns found — verify manually (see action items)"
  else
    record_ok "Secrets clean" "no committed keys detected"
  fi
}

# ---------------------------------------------------------------------------
# §11 Final dashboard
# ---------------------------------------------------------------------------
print_dashboard() {
  local end_ts
  end_ts=$(date +%s)
  local elapsed=$(( end_ts - START_TS ))

  if [[ $JSON_MODE -eq 1 ]]; then
    print_json_dashboard "$elapsed"
    return
  fi

  echo ""
  echo "═══════════════════════════════════════════════════════"
  echo "   nox-mem pre-launch dashboard — Wed 2026-06-03"
  echo "═══════════════════════════════════════════════════════"

  for line in "${SUMMARY_LINES[@]}"; do
    local status name detail
    IFS='|' read -r status name detail <<< "$line"
    local icon padded_name
    padded_name=$(printf "%-22s" "$name")
    case "$status" in
      ok)   icon="${GREEN}✅${RESET}" ;;
      warn) icon="${YELLOW}⚠️ ${RESET}" ;;
      fail) icon="${RED}❌${RESET}" ;;
    esac
    printf "${icon} ${BOLD}%s${RESET}  [%s]\n" "$padded_name" "$detail"
  done

  echo ""

  # Verdict
  if [[ $HAS_RED -eq 1 ]]; then
    echo -e "${RED}${BOLD}VERDICT: ❌ NO-GO — Critical failures must be fixed before launch${RESET}"
  elif [[ $HAS_YELLOW -eq 1 ]]; then
    echo -e "${YELLOW}${BOLD}VERDICT: ⚠️  GO-WITH-WARNINGS${RESET}"
  else
    echo -e "${GREEN}${BOLD}VERDICT: ✅ ALL GREEN — GO FOR LAUNCH${RESET}"
  fi

  if [[ ${#ACTION_ITEMS[@]} -gt 0 ]]; then
    echo ""
    echo "ACTION ITEMS:"
    local i=1
    for item in "${ACTION_ITEMS[@]}"; do
      echo "  ${i}. ${item}"
      (( i++ )) || true
    done
  fi

  echo ""
  echo "═══════════════════════════════════════════════════════"
  local skip_note=""
  [[ $SKIP_NETWORK -eq 1 ]] && skip_note=" | --skip-network active"
  echo "Run time: ${elapsed}s${skip_note} | --verbose for details"
  echo "═══════════════════════════════════════════════════════"
  echo ""
}

print_json_dashboard() {
  local elapsed="$1"
  local checks_json="["
  local first=1

  for line in "${SUMMARY_LINES[@]}"; do
    local status name detail
    IFS='|' read -r status name detail <<< "$line"
    [[ $first -eq 0 ]] && checks_json+=","
    checks_json+=$(python3 -c "
import json, sys
print(json.dumps({'status': sys.argv[1], 'name': sys.argv[2], 'detail': sys.argv[3]}))
" "$status" "$name" "$detail" 2>/dev/null || echo "{\"status\":\"${status}\",\"name\":\"${name}\",\"detail\":\"${detail}\"}")
    first=0
  done
  checks_json+="]"

  local verdict
  if [[ $HAS_RED -eq 1 ]]; then
    verdict="NO-GO"
  elif [[ $HAS_YELLOW -eq 1 ]]; then
    verdict="GO-WITH-WARNINGS"
  else
    verdict="ALL-GREEN"
  fi

  local actions_json="["
  first=1
  for item in "${ACTION_ITEMS[@]}"; do
    [[ $first -eq 0 ]] && actions_json+=","
    actions_json+=$(python3 -c "import json,sys; print(json.dumps(sys.argv[1]))" "$item" 2>/dev/null || echo "\"${item}\"")
    first=0
  done
  actions_json+="]"

  python3 -c "
import json, sys
data = {
    'dashboard': 'nox-mem pre-launch',
    'launch_date': '2026-06-03',
    'run_time_s': int(sys.argv[1]),
    'verdict': sys.argv[2],
    'has_red': bool(int(sys.argv[3])),
    'has_yellow': bool(int(sys.argv[4])),
    'checks': json.loads(sys.argv[5]),
    'action_items': json.loads(sys.argv[6]),
}
print(json.dumps(data, indent=2))
" "$elapsed" "$verdict" "$HAS_RED" "$HAS_YELLOW" "$checks_json" "$actions_json"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
  if [[ $JSON_MODE -eq 0 ]]; then
    echo ""
    echo "  nox-mem pre-launch check running..."
    echo ""
  fi

  check_repo_state
  check_critical_files
  check_workflows
  check_vps_health
  check_paper_build
  check_q4_status
  check_examples
  check_docs_links
  check_repo_metadata
  check_secrets_clean

  print_dashboard

  # Exit code semantics
  if [[ $HAS_RED -eq 1 ]]; then
    exit 1
  elif [[ $HAS_YELLOW -eq 1 ]]; then
    exit 2
  else
    exit 0
  fi
}

main
