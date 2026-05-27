# EverMemBench — Gemini-only LLM stack recipe

> Substitute OpenRouter (gpt-4.1-mini answer + gemini-3-flash-preview judge)
> with Google AI Studio Gemini direct, using the OpenAI-compat shim.
> Saves ~$3/run (no OpenRouter middleman) and removes the OpenRouter API
> key dependency entirely.

**Status:** recipe drafted 2026-05-27 from PR #360 + #361 bootstrap.
First batch run is pending VPS execution (see `RUN-VPS.md` step-by-step).

---

## 1. Why this exists

The upstream EverMemBench harness defaults to:

| Stage | Model | Provider |
|-------|-------|----------|
| Answer (gen) | `openai/gpt-4.1-mini` | OpenRouter (`https://openrouter.ai/api/v1`) |
| Evaluate (judge) | `google/gemini-3-flash-preview` | OpenRouter → Google AI Studio |

Cost per full 5-batch run is ~$1–2 USD via OpenRouter.

For nox-mem's first EverMemBench run we have:
- A Gemini API key on hand (`GEMINI_API_KEY`)
- No OpenRouter key provisioned for memoria-nox
- A directive to use the cheapest credible LLM stack for batch 004 (~$0.67 est)

Gemini exposes an **OpenAI-compatible endpoint** at
`https://generativelanguage.googleapis.com/v1beta/openai/`. The harness
uses `openai.AsyncOpenAI(base_url=..., api_key=...)` so a 3-var swap is
all that's needed.

---

## 2. The 3-variable swap

In `benchmarks/EverMemBench/.env` (cp from `env.template`):

```env
# === Gemini-via-OpenAI-compat shim ===
LLM_API_KEY=<gemini_api_key>
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/

# Other vars stay default (or unset)
```

And in `benchmarks/EverMemBench/eval/config/pipeline.yaml`:

```yaml
answer:
  model: "gemini-2.5-flash"      # was: openai/gpt-4.1-mini
  provider:
    order: ["google-ai-studio"]
    allow_fallbacks: false
  temperature: 0
  max_tokens: 1000
  timeout: 300
  concurrency: 1

evaluate:
  model: "gemini-2.5-flash"      # was: google/gemini-3-flash-preview
  provider:
    order: ["google-ai-studio"]
    allow_fallbacks: false
  concurrency: 20
```

**Rationale for using `gemini-2.5-flash` for both stages:**
- Gemini OpenAI-compat layer does NOT accept OpenRouter-style model names
  (`google/gemini-3-flash-preview`). It expects bare Gemini IDs
  (`gemini-2.5-flash`, `gemini-2.0-flash`, etc).
- Both stages are simple instruction-following (answer gen + judge MC/OE)
  — `gemini-2.5-flash` is comfortably capable for both.
- `gemini-3-flash-preview` is experimental and not yet broadly available via
  OpenAI-compat shim (verify before relying on it).

---

## 3. Honest framing in results

If you publish numbers from this Gemini-only stack, the headline MUST
disclose the methodology deviation:

> **Note:** This run uses `gemini-2.5-flash` for both answer generation
> and OE judgment, substituted for the upstream EverMemBench default
> (`openai/gpt-4.1-mini` answer + `gemini-3-flash-preview` judge via
> OpenRouter). Numbers are **not directly comparable** to EverOS-published
> EverMemBench leaderboard entries. To compare against published numbers
> on the same methodology, re-run with `LLM_API_KEY=sk-or-v1-...` and
> default `pipeline.yaml`.

This callout belongs in:
- `RESULTS-BATCH-004.md` (top, before headline number)
- Any PR description that ships results
- Any paper/blog post comparing nox-mem vs EverOS-published competitors

---

## 4. Cost estimate (Gemini-only, batch 004)

- ~250 questions per batch × 2 LLM calls (answer + judge if OE)
- `gemini-2.5-flash` pricing: ~$0.30 / 1M input tokens, ~$2.50 / 1M output
- Per-question est: ~3k tokens in + ~200 tokens out
- ~250 × (3k × $0.30 + 0.2k × $2.50) / 1M = ~$0.32 + ~$0.12 = **~$0.45**

(Original task estimated ~$0.67; both within the $1.50 cap.)

---

## 5. Verification commands (no key in logs)

```bash
# Set env (do NOT echo the key)
export GEMINI_API_KEY=$(cat /tmp/.gemini-key-98949.txt | tr -d '\n')
export LLM_API_KEY="$GEMINI_API_KEY"
export LLM_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"

# Smoke test the OpenAI-compat shim (one call, no harness)
python -c "
import os, asyncio
from openai import AsyncOpenAI
async def main():
    c = AsyncOpenAI(
        api_key=os.environ['LLM_API_KEY'],
        base_url=os.environ['LLM_BASE_URL'],
    )
    r = await c.chat.completions.create(
        model='gemini-2.5-flash',
        messages=[{'role':'user','content':'reply with exactly: OK'}],
        max_tokens=10,
    )
    print(r.choices[0].message.content)
asyncio.run(main())
"
# Expected: "OK"
```

**Security:** never `echo \$LLM_API_KEY`, never paste it into PRs, never
let it land in subprocess `stderr` that flows to a log file in the repo.
Gemini-on-AI-Studio keys can be rotated at
[aistudio.google.com](https://aistudio.google.com/) → API keys.

---

## 6. Open questions (decide before run)

1. **Judge model — `gemini-2.5-flash` vs `gemini-2.5-pro`?**
   Pro costs ~5× more but is more reliable for OE adjudication.
   Recommendation: start with `gemini-2.5-flash` (this doc default);
   only escalate to pro if first-batch OE accuracy looks anomalously low
   compared to MC subset.

2. **`gemini-2.0-flash` vs `gemini-2.5-flash` answer-side?**
   `2.0-flash` is deprecated June 2026 — DO NOT use for repro runs that
   need stability. `2.5-flash-lite` is the canonical nox-mem internal
   model (per CLAUDE.md §3) but for a benchmark answer we want strict
   non-lite to avoid harming the score.

3. **Concurrency cap for evaluate stage?**
   pipeline.yaml default `evaluate.concurrency: 20`. Gemini AI Studio
   free tier rate-limits at 15 req/min for `gemini-2.5-flash`. Lower
   to `concurrency: 10` and add `sleep(0.2)` between calls if hitting
   429s. Otherwise the run will stall on retries.
