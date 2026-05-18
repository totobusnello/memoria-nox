---
title: Python SDK
description: Official Python client for memoria-nox.
sidebar:
  order: 3
---

Source: [`sdk/python/`](https://github.com/totobusnello/memoria-nox/tree/main/sdk/python)

## Install

```bash
pip install nox-mem-sdk
```

## Basic usage

```python
from nox_mem import NoxMemClient
import asyncio

async def main():
    client = NoxMemClient(base_url="http://127.0.0.1:18802")

    # Hybrid search
    results = await client.search("salience formula", limit=10)
    for r in results:
        print(f"{r.score:.3f}  {r.content[:120]}")

    # Grounded answer
    answer = await client.answer("how does pain affect ranking?")
    print(answer.text)
    print("Sources:", [s.source for s in answer.sources])

    # Corpus stats
    stats = await client.stats()
    print(f"chunks: {stats.total_chunks}, coverage: {stats.vector_coverage:.4f}")

asyncio.run(main())
```

## Synchronous API

```python
from nox_mem import NoxMemClientSync

client = NoxMemClientSync(base_url="http://127.0.0.1:18802")
results = client.search("salience formula")
```

## Pydantic models

```python
from nox_mem.models import SearchResult, AnswerResult, CorpusStats

# All responses are typed Pydantic v2 models
result: SearchResult = results[0]
print(result.chunk_id, result.pain, result.section)
```

## LangChain integration

```python
from nox_mem.integrations.langchain import NoxMemRetriever
from langchain.chains import RetrievalQA

retriever = NoxMemRetriever(base_url="http://127.0.0.1:18802", k=5)
qa_chain = RetrievalQA.from_chain_type(llm=your_llm, retriever=retriever)
```
