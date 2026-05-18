# nox-mem (Go SDK)

Zero-dependency Go client for the [memoria-nox](https://github.com/totobusnello/memoria-nox) HTTP API (`openapi 1.0.0-wave-d`).

## Features

- All 26 endpoints: Core, Search, KG, Answer (P1), Export/Import (A2), Viewer/SSE (P5), Conflict Detection (L2), Confidence (L3), Hooks (P2)
- `context.Context` throughout — cancellable at every call
- SSE streaming via `SSEReader.Next()` iterator
- Streaming export via `ExportStream` — no buffering for large corpora
- Zero external dependencies — standard library `net/http` + `encoding/json`
- `*APIError` with `IsFeatureDisabled()` and `IsUnauthorized()` helpers

## Installation

```bash
go get github.com/totobusnello/memoria-nox/sdk/go
```

## Quick start

```go
package main

import (
    "context"
    "fmt"
    "os"

    noxmem "github.com/totobusnello/memoria-nox/sdk/go"
)

func main() {
    ctx := context.Background()
    c := noxmem.New(noxmem.Config{
        AuthToken: os.Getenv("NOX_API_TOKEN"),
        // BaseURL defaults to http://127.0.0.1:18802
    })

    // Health check
    health, err := c.Health(ctx)
    if err != nil { panic(err) }
    fmt.Println("chunks:", health.Chunks.Total)

    // Hybrid search (FTS5 + Gemini semantic + RRF)
    limit := 5
    results, err := c.Search(ctx, "Gemini quota exceeded", &noxmem.SearchOptions{Limit: &limit})
    if err != nil { panic(err) }
    for _, r := range results {
        fmt.Printf("[%.3f] %s\n", r.Score, r.Content[:min(80, len(r.Content))])
    }

    // RAG answer with citations (requires NOX_ANSWER_ENABLED=1)
    topK := 8
    ans, err := c.Answer(ctx, noxmem.AnswerRequest{
        Question: "How to reapply monkey-patch after upgrade?",
        TopK:     &topK,
    })
    if err != nil { panic(err) }
    fmt.Println(ans.Answer)
}
```

## SSE streaming

```go
reader, err := client.StreamEvents(ctx, 0) // 0 = no Last-Event-ID
if err != nil { panic(err) }
defer reader.Close()

for {
    ev, err := reader.Next()
    if err == io.EOF { break }
    if err != nil { panic(err) }
    fmt.Println(ev.Kind, ev.ID, ev.Data)
}
```

## Export streaming (large corpora)

```go
body, headers, err := client.ExportStream(ctx, nil)
if err != nil { panic(err) }
defer body.Close()
f, _ := os.Create("backup.tar.gz")
io.Copy(f, body)
fmt.Println("chunks:", headers.Get("X-Nox-Export-Chunks-Count"))
```

## Error handling

```go
_, err := client.Answer(ctx, req)
if err != nil {
    if apiErr, ok := err.(*noxmem.APIError); ok {
        switch {
        case apiErr.IsFeatureDisabled():
            fmt.Println("Set NOX_ANSWER_ENABLED=1")
        case apiErr.IsUnauthorized():
            fmt.Println("Check NOX_API_TOKEN")
        default:
            fmt.Println("HTTP", apiErr.StatusCode, apiErr.Error())
        }
    }
}
```

## Configuration

| Field | Default | Description |
|---|---|---|
| `BaseURL` | `http://127.0.0.1:18802` | API base URL |
| `AuthToken` | `""` | Bearer token (`NOX_API_TOKEN`) |
| `Timeout` | `30s` | Per-request timeout (not applied to SSE stream) |

## Running tests

```bash
go test ./...
```

## License

MIT
