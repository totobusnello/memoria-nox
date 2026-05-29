#!/usr/bin/env bash
# eval/lib/preflight.sh — billing-path preflight helpers for EverMemBench runs.
#
# Lesson codified: [[preflight-must-exercise-billing-path]]
#   Phase H v1 (PR #368) routed via OpenRouter. `/v1/models` returned 200 OK on
#   auth but the real chat/completions call 402'd on credits — wasting setup time
#   and triggering a key-rotation round-trip. Auth check != billing path check.
#   A tiny real completion (5 tokens) exercises auth + model access + credits in
#   one shot for ~$0.0001 (gpt-4.1-mini) or free (Gemini quota).
#
# Usage (source in any run-batch-*.sh):
#
#   source "$(dirname "$0")/../lib/preflight.sh"
#
#   # OpenAI direct
#   preflight_billing "https://api.openai.com/v1" "$OPENAI_API_KEY" "gpt-4.1-mini" || exit 1
#
#   # Gemini (OpenAI-compat endpoint)
#   preflight_billing "https://generativelanguage.googleapis.com/v1beta/openai" \
#       "$GEMINI_API_KEY" "gemini-2.5-flash" || exit 1
#
#   # OpenRouter (guard against $0 balance 402)
#   preflight_billing "https://openrouter.ai/api/v1" "$OPENROUTER_API_KEY" \
#       "openai/gpt-4.1-mini" || exit 1
#
# Returns 0 on success, non-zero on failure. Never silently swallows errors.

set -euo pipefail

# preflight_billing <provider_url> <api_key> <model>
#
# Sends a minimal chat completion (max_tokens=5, temperature=0) to the provider
# and verifies that `.choices[0]` exists in the JSON response. Prints a
# one-line OK / FAILED banner to stdout/stderr respectively.
#
# Args:
#   provider_url  — Base URL without trailing slash, e.g.
#                   https://api.openai.com/v1
#                   https://generativelanguage.googleapis.com/v1beta/openai
#                   https://openrouter.ai/api/v1
#   api_key       — Bearer token for the provider.
#   model         — Model id to exercise (must be a billing-path model, not a
#                   free-tier embedding-only model).
#
# Exit codes:
#   0  — preflight passed (billing path reachable)
#   1  — curl failed or response lacks .choices[0] (auth / billing error)
preflight_billing() {
    local provider_url="${1:?preflight_billing: provider_url required}"
    local api_key="${2:?preflight_billing: api_key required}"
    local model="${3:?preflight_billing: model required}"

    local endpoint="${provider_url%/}/chat/completions"
    local payload
    payload=$(
        printf '{"model":"%s","messages":[{"role":"user","content":"ok"}],"max_tokens":5,"temperature":0}' \
            "$model"
    )

    local response
    response=$(
        curl -s --max-time 30 \
            -X POST "$endpoint" \
            -H "Authorization: Bearer $api_key" \
            -H "Content-Type: application/json" \
            -d "$payload" \
            2>/dev/null
    ) || {
        echo "[preflight] FAILED: curl error on $endpoint" >&2
        return 1
    }

    if echo "$response" | python3 -c 'import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get("choices") else 1)' 2>/dev/null; then
        local total_tokens
        total_tokens=$(
            echo "$response" | \
            python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("usage",{}).get("total_tokens","?"))' \
            2>/dev/null || echo "?"
        )
        echo "[preflight] OK (${provider_url} / ${model}, tokens=${total_tokens})"
        return 0
    else
        echo "[preflight] FAILED: no .choices[0] in response from ${provider_url}" >&2
        # Print first 600 chars to help diagnose 402 / 429 / model-not-found
        echo "$response" | head -c 600 >&2
        return 1
    fi
}
