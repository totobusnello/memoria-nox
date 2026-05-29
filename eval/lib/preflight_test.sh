#!/usr/bin/env bash
# eval/lib/preflight_test.sh — smoke tests for preflight.sh
#
# Tests run WITHOUT real API calls (mock curl via wrapper scripts).
# Designed to run in CI with $0 LLM cost.
#
# Usage:
#   bash eval/lib/preflight_test.sh
#
# Exit 0 on all-pass, non-zero on any failure.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

PASS=0
FAIL=0

# ── Mock curl helper ─────────────────────────────────────────────────────────
# Each test creates a temp dir with a fake curl script, then invokes a
# subshell that sources preflight.sh with PATH prepended. The subshell must
# be a fresh bash -c call so the sourced set -euo pipefail doesn't bleed.

_run_preflight_with_mock() {
    local mock_body="$1"
    local provider="$2"
    local key="$3"
    local model="$4"
    local tmpdir
    tmpdir=$(mktemp -d)
    # Write mock curl that echoes the mock body regardless of args
    printf '#!/bin/bash\necho %s\n' "$(printf '%q' "$mock_body")" > "$tmpdir/curl"
    chmod +x "$tmpdir/curl"
    # Run in subshell so set -e in preflight.sh stays contained
    PATH="$tmpdir:$PATH" bash -c \
        "source $(printf '%q' "$SCRIPT_DIR/preflight.sh") && preflight_billing $(printf '%q' "$provider") $(printf '%q' "$key") $(printf '%q' "$model")" \
        2>/dev/null
    local exit_code=$?
    rm -rf "$tmpdir"
    return $exit_code
}

assert_exit() {
    local desc="$1"
    local expected="$2"  # "0" or "nonzero"
    shift 2
    local actual=0
    "$@" 2>/dev/null || actual=$?
    if [ "$expected" = "0" ] && [ "$actual" = "0" ]; then
        echo "  PASS: $desc"
        PASS=$((PASS + 1))
    elif [ "$expected" = "nonzero" ] && [ "$actual" != "0" ]; then
        echo "  PASS: $desc (exit=$actual)"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $desc (expected=${expected}, got=${actual})"
        FAIL=$((FAIL + 1))
    fi
}

GOOD_RESPONSE='{"choices":[{"message":{"content":"OK"},"finish_reason":"stop"}],"usage":{"total_tokens":3}}'
BILLING_ERROR='{"error":{"code":"insufficient_quota","message":"You exceeded your current quota."}}'
CORRUPT_JSON='not-json-at-all'

echo ""
echo "=== preflight_billing tests ==="

# Test 1: valid completion response → exit 0
assert_exit "good response → exit 0" "0" \
    _run_preflight_with_mock "$GOOD_RESPONSE" "https://api.openai.com/v1" "sk-fake" "gpt-4.1-mini"

# Test 2: billing error (no .choices) → exit 1
assert_exit "billing error → exit nonzero" "nonzero" \
    _run_preflight_with_mock "$BILLING_ERROR" "https://api.openai.com/v1" "sk-fake" "gpt-4.1-mini"

# Test 3: corrupt JSON (python parse fails) → exit 1
assert_exit "corrupt JSON → exit nonzero" "nonzero" \
    _run_preflight_with_mock "$CORRUPT_JSON" "https://api.openai.com/v1" "sk-fake" "gpt-4.1-mini"

# Test 4: OpenRouter-shaped good response (same .choices[0] shape)
OR_RESPONSE='{"choices":[{"message":{"content":"ok"},"finish_reason":"stop"}],"usage":{"total_tokens":2}}'
assert_exit "OpenRouter good response → exit 0" "0" \
    _run_preflight_with_mock "$OR_RESPONSE" "https://openrouter.ai/api/v1" "or-fake" "openai/gpt-4.1-mini"

echo ""
echo "Results: ${PASS} passed, ${FAIL} failed"
[ "$FAIL" -eq 0 ]
