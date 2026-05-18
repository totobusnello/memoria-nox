# nox-mem-client (Rust)

Type-safe async Rust client for the [memoria-nox](https://github.com/totobusnello/memoria-nox) HTTP API (`openapi 1.0.0-wave-d`).

## Features

- All 26 endpoints: Core, Search, KG, Answer (P1), Export/Import (A2), Viewer/SSE (P5), Conflict Detection (L2), Confidence (L3), Hooks (P2)
- Tokio async — zero blocking calls
- SSE streaming via `tokio_stream::Stream` (backpressure-safe)
- Streaming export (`export_stream`) for large corpora without buffering
- `thiserror`-based error type with `is_feature_disabled()` and `is_unauthorized()` helpers
- Minimal dependencies: `reqwest` + `serde` + `tokio`

## Installation

```toml
[dependencies]
nox-mem-client = "0.1"
tokio = { version = "1", features = ["full"] }
```

## Quick start

```rust
use nox_mem_client::{NoxMemClient, NoxMemClientConfig};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = NoxMemClient::new(NoxMemClientConfig {
        auth_token: std::env::var("NOX_API_TOKEN").ok(),
        ..Default::default()  // base_url: http://127.0.0.1:18802
    });

    // Health check
    let health = client.health().await?;
    println!("chunks: {}", health.chunks.unwrap().total);

    // Hybrid search (FTS5 + Gemini semantic + RRF)
    let results = client.search("Gemini quota exceeded", Some(5), None, None).await?;
    for r in &results {
        println!("[{:.3}] {}", r.score, &r.content[..80.min(r.content.len())]);
    }

    // RAG answer with citations (requires NOX_ANSWER_ENABLED=1)
    let answer = client.answer(&nox_mem_client::AnswerRequest {
        question: "How to reapply monkey-patch after upgrade?".into(),
        top_k: Some(8),
        ..Default::default()
    }).await?;
    println!("{}", answer.answer);

    Ok(())
}
```

## SSE streaming

```rust
use futures_util::StreamExt;

let mut stream = client.stream_events(None).await?;
while let Some(event) = stream.next().await {
    let event = event?;
    println!("{:?}", event.kind);
}
```

## Export streaming (large corpora)

```rust
use futures_util::StreamExt;
use tokio::io::AsyncWriteExt;

let mut stream = client.export_stream(None).await?;
let mut file = tokio::fs::File::create("backup.tar.gz").await?;
while let Some(chunk) = stream.next().await {
    file.write_all(&chunk?).await?;
}
```

## Error handling

```rust
use nox_mem_client::NoxMemError;

match client.answer(&req).await {
    Ok(ans) => println!("{}", ans.answer),
    Err(e) if e.is_feature_disabled() => println!("Set NOX_ANSWER_ENABLED=1"),
    Err(e) if e.is_unauthorized() => println!("Check NOX_API_TOKEN"),
    Err(e) => return Err(e.into()),
}
```

## Configuration

| Field | Default | Description |
|---|---|---|
| `base_url` | `http://127.0.0.1:18802` | API base URL |
| `auth_token` | `None` | Bearer token (`NOX_API_TOKEN`) |
| `timeout` | 30s | Per-request timeout |

## Running tests

```bash
cargo test
```

## License

MIT
