#!/usr/bin/env bash
# Pre-install minimal deps for nox-mem demo Codespace
# Runs once after container creation
set -euo pipefail

echo "=== nox-mem demo setup ==="
echo ""

# Quick deps
echo "Installing Python deps..."
pip install --quiet requests pyyaml || echo "(non-fatal: pip install)"

echo "Installing jq + asciinema..."
sudo apt-get update -qq
sudo apt-get install -y -qq jq asciinema 2>/dev/null || echo "(non-fatal: apt)"

# Verify
echo ""
echo "=== Tool versions ==="
which curl python3 node jq 2>&1 | head -10
python3 --version
node --version

# Smoke test the public VPS
echo ""
echo "=== Public VPS smoke test ==="
if curl -s --max-time 5 "${BASE_URL:-http://187.77.234.79:18802}/api/health" > /dev/null; then
    echo "Public VPS reachable at ${BASE_URL:-http://187.77.234.79:18802}"
else
    echo "WARNING: Public VPS not reachable; demo scripts may not work"
fi

# Welcome banner
cat <<'BANNER'

+------------------------------------------------------------+
|              Welcome to nox-mem demo                       |
|                                                            |
|  Try these commands now:                                   |
|                                                            |
|    bash examples/01-curl-hello.sh           # 30s          |
|    python3 examples/02-python-search.py "your query"      |
|    node examples/03-js-search.js "your query"             |
|    python3 examples/05-rag-loop.py                        |
|                                                            |
|  Full guide: docs/QUICKSTART.md and docs/TUTORIAL.md       |
|  Use cases:  docs/USE-CASES.md                             |
|  FAQ:        docs/FAQ.md                                   |
|                                                            |
|  Public demo URL: http://187.77.234.79:18802               |
+------------------------------------------------------------+

BANNER
