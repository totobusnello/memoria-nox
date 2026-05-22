# nox-mem Codespace

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/totobusnello/memoria-nox)

Click the button above to open a fully-configured browser environment in ~60 seconds.

## What you get

- Python 3.11 + Node 20 pre-installed
- `curl`, `jq`, `asciinema` available
- `BASE_URL` pre-set to the public demo VPS (`http://187.77.234.79:18802`)
- `requests` and `pyyaml` pip-installed
- Welcome banner with ready-to-run commands

## First thing to run

```bash
bash examples/01-curl-hello.sh
```

Then try:

```bash
python3 examples/02-python-search.py "memory search"
python3 examples/04-python-answer.py "what is nox-mem?"
python3 examples/05-rag-loop.py
```

## Cost

GitHub Codespaces free tier: **60 hours/month** for personal accounts — more than enough to demo and explore.

Paid plans available if you need more. See [github.com/features/codespaces](https://github.com/features/codespaces).

## Limitations

- The public demo VPS is **read-only** — search and answer endpoints work, ingest is not exposed
- No local `nox-mem-api` is running inside the container (that requires the VPS setup)
- For a full local install, follow [`docs/QUICKSTART.md`](../docs/QUICKSTART.md)

## Changing the target instance

If you have your own nox-mem instance running:

```bash
export BASE_URL=http://your-host:18802
bash examples/01-curl-hello.sh
```
