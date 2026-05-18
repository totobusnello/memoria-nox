---
title: Rust SDK
description: Official Rust client for memoria-nox.
sidebar:
  order: 4
---

Source: [`sdk/rust/`](https://github.com/totobusnello/memoria-nox/tree/main/sdk/rust)

## Add to Cargo.toml

```toml
[dependencies]
nox-mem-sdk = "0.1"
tokio = { version = "1", features = ["full"] }
```

## Basic usage

```rust
use nox_mem_sdk::NoxMemClient;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let client = NoxMemClient::new("http://127.0.0.1:18802");

    // Hybrid search
    let results = client.search("salience formula", Default::default()).await?;
    for r in &results {
        println!("{:.3}  {}", r.score, &r.content[..r.content.len().min(120)]);
    }

    // Grounded answer
    let answer = client.answer("how does pain affect ranking?").await?;
    println!("{}", answer.text);

    // Stats
    let stats = client.stats().await?;
    println!("chunks: {}, coverage: {:.4}", stats.total_chunks, stats.vector_coverage);

    Ok(())
}
```

## Types

```rust
pub struct SearchResult {
    pub chunk_id: i64,
    pub score: f64,
    pub content: String,
    pub source: String,
    pub section: Option<String>,
    pub pain: f64,
}

pub struct SearchOptions {
    pub limit: Option<usize>,         // default 10
    pub no_hybrid: Option<bool>,      // default false
    pub min_score: Option<f64>,
}
```
