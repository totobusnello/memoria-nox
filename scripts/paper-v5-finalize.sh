#!/usr/bin/env bash
# paper-v5-finalize.sh — commit §5 v5, build PDF+TEX, push to PR #427 branch
# Run from repo root: bash scripts/paper-v5-finalize.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "=== [1/5] branch check ==="
BRANCH=$(git branch --show-current)
echo "current branch: $BRANCH"
if [[ "$BRANCH" != "docs/sun-closure-2026-05-31" ]]; then
  echo "ERROR: expected docs/sun-closure-2026-05-31, got $BRANCH" >&2
  exit 1
fi

echo "=== [2/5] git commit ==="
git add paper/paper-tecnico-nox-mem.md
COMMIT_TO_NON_MAIN_OK=1 git commit \
  -m "docs(paper): §5 fifth revision — Wave 2 closure honest reframe (D75 + D76 + architectural lock)"
echo "commit hash: $(git log --oneline -1)"

echo "=== [3/5] build PDF ==="
bash scripts/build-paper.sh --pdf-only 2>&1
ls -lh paper/build/paper-tecnico-nox-mem.pdf 2>/dev/null || echo "PDF not found in build/"

echo "=== [4/5] build TEX (arXiv) ==="
bash scripts/build-paper.sh --tex-only 2>&1
ls -lh paper/build/paper-tecnico-nox-mem.tex 2>/dev/null || echo "TEX not found in build/"

echo "=== [5/5] git add build artifacts + push ==="
git add paper/build/paper-tecnico-nox-mem.pdf paper/build/paper-tecnico-nox-mem.tex 2>/dev/null || true
if ! git diff --cached --quiet 2>/dev/null; then
  COMMIT_TO_NON_MAIN_OK=1 git commit -m "build(paper): PDF + TEX artifacts §5 v5"
  echo "build artifacts commit: $(git log --oneline -1)"
fi
git push origin docs/sun-closure-2026-05-31
echo ""
echo "=== DONE ==="
echo "PR #427 branch updated: docs/sun-closure-2026-05-31"
echo "Final commit: $(git log --oneline -1)"
