# Examples

Quick runnable scripts hitting the public demo VPS at `187.77.234.79:18802`.

| File | Language | What it does | Time |
|------|----------|--------------|------|
| `01-curl-hello.sh` | Bash + curl | Hit /api/health and /api/search | 30s |
| `02-python-search.py` | Python 3 | Search + parse JSON results | 30s |
| `03-js-search.js` | Node 20+ | Same in JS w/ fetch | 30s |
| `04-python-answer.py` | Python 3 | Call /api/answer flagship endpoint | 1min |
| `05-rag-loop.py` | Python 3 | RAG-style: search → build LLM prompt w/ context | 2min |

All scripts use the public demo (read-only). To run against your own instance, set `BASE_URL`:

```sh
export BASE_URL=http://localhost:18802
./examples/01-curl-hello.sh
```

For installation see [`docs/QUICKSTART.md`](../docs/QUICKSTART.md).
For use case patterns see [`docs/USE-CASES.md`](../docs/USE-CASES.md).

## Prerequisites

| Tool | Required by | Install |
|------|------------|---------|
| curl + jq | `01-curl-hello.sh` | `brew install jq` / `apt install jq` |
| Python 3.9+ | `02-python-search.py`, `04-*.py`, `05-*.py` | stdlib only, no pip needed |
| Node 20+ | `03-js-search.js` | [nodejs.org](https://nodejs.org) |

## Expected first-line output (smoke check)

| Script | Expected first line |
|--------|---------------------|
| `01-curl-hello.sh` | `=== Health snapshot ===` |
| `02-python-search.py` | `DB: NNNNN chunks, vec_coverage=XX.XX%` |
| `03-js-search.js` | `DB: NNNNN chunks, vec=XX.X%` |
| `04-python-answer.py` | `Question: <your query or default>` |
| `05-rag-loop.py` | `[1/3] Searching nox-mem for: <query>` |

If you see `Connection refused` or a non-200 status, the demo VPS may be temporarily unavailable — try again in a few minutes.
