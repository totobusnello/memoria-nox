---
title: Cost Model
description: Monthly OPEX breakdown and cost projection for self-hosted memoria-nox.
sidebar:
  order: 2
---

Full source: [`docs/cost-model.md`](https://github.com/totobusnello/memoria-nox/blob/main/docs/cost-model.md)

## Live corpus costs (2026-05-18)

| Component | Cost/month | Notes |
|---|---|---|
| VPS (Hostinger) | ~$7.00 | 4 vCPU, 8GB RAM, 100GB SSD |
| Gemini embeddings | ~$2.50 | `gemini-embedding-001` at $0.00001/1K chars |
| Gemini KG extraction | ~$1.20 | `gemini-2.5-flash` nightly batch |
| Total | **< $11/month** | Live corpus: 69,298 chunks |

## Embedding cost model

Using `gemini-embedding-001`:
- Input: ~1,000 chars/chunk average
- Cost: $0.00001 per 1K chars
- 69,298 chunks × 1K chars = $0.69 one-time ingest
- Nightly delta (~500 new chunks): ~$0.005/day = $0.15/month

## KG extraction cost

Using `gemini-2.5-flash` for nightly KG build:
- ~2M tokens/month for incremental extraction
- At $0.00040/1K tokens output: ~$0.80/month

:::caution[Never use gemini-2.5-flash for embeddings]
`gemini-2.5-flash` exhausts the 3M/day quota at scale. Always use `gemini-embedding-001` for embeddings. Only KG extraction (low volume) can use `gemini-2.5-flash`.
:::

## Cost at scale

| Corpus size | Monthly OPEX |
|---|---|
| 10K chunks | ~$4/month |
| 69K chunks (current) | ~$11/month |
| 200K chunks | ~$18/month |
| 1M chunks | ~$35/month |

The cost scaling is sub-linear because:
- Nightly delta is a small fraction of total corpus
- KG extraction is incremental (only new chunks)
- VPS cost is fixed (scales only at 500K+ chunks)

## Provider cost comparison

Full alt-provider projection: [`runbooks/cost-projection-alt-providers.md`](https://github.com/totobusnello/memoria-nox/blob/main/runbooks/cost-projection-alt-providers.md)

| Provider | Embedding cost (69K chunks) | Notes |
|---|---|---|
| Gemini `embedding-001` | ~$0.69 | Recommended |
| OpenAI `text-embedding-3-small` | ~$1.38 | 2× more expensive |
| OpenAI `text-embedding-3-large` | ~$8.30 | High quality, high cost |
| Local (Ollama `nomic-embed-text`) | $0.00 | No API cost, requires GPU/CPU |
