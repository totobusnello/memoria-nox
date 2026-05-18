---
title: Go SDK
description: Official Go client for memoria-nox.
sidebar:
  order: 5
---

Source: [`sdk/go/`](https://github.com/totobusnello/memoria-nox/tree/main/sdk/go)

## Install

```bash
go get github.com/totobusnello/memoria-nox/sdk/go@latest
```

## Basic usage

```go
package main

import (
    "context"
    "fmt"
    noxmem "github.com/totobusnello/memoria-nox/sdk/go"
)

func main() {
    client := noxmem.NewClient("http://127.0.0.1:18802")
    ctx := context.Background()

    // Hybrid search
    results, err := client.Search(ctx, "salience formula", noxmem.SearchOptions{Limit: 10})
    if err != nil {
        panic(err)
    }
    for _, r := range results {
        fmt.Printf("%.3f  %s\n", r.Score, r.Content[:min(120, len(r.Content))])
    }

    // Stats
    stats, err := client.Stats(ctx)
    if err != nil {
        panic(err)
    }
    fmt.Printf("chunks: %d, coverage: %.4f\n", stats.TotalChunks, stats.VectorCoverage)
}
```

## Types

```go
type SearchResult struct {
    ChunkID int64   `json:"chunkId"`
    Score   float64 `json:"score"`
    Content string  `json:"content"`
    Source  string  `json:"source"`
    Section *string `json:"section"`
    Pain    float64 `json:"pain"`
}

type SearchOptions struct {
    Limit    int
    NoHybrid bool
    MinScore float64
}
```
