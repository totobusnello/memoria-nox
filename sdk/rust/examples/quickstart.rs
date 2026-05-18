/// Quickstart example for nox-mem-client.
///
/// Run with:
///   NOX_API_TOKEN=<token> cargo run --example quickstart
use nox_mem_client::{NoxMemClient, NoxMemClientConfig};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = NoxMemClient::new(NoxMemClientConfig {
        base_url: std::env::var("NOX_API_URL")
            .unwrap_or_else(|_| "http://127.0.0.1:18802".to_string()),
        auth_token: std::env::var("NOX_API_TOKEN").ok(),
        ..Default::default()
    });

    // ── Health check ──────────────────────────────────────────────────────────
    let health = client.health().await?;
    if let Some(chunks) = &health.chunks {
        println!("Chunks total: {}", chunks.total);
    }
    if let Some(vc) = &health.vector_coverage {
        println!(
            "Vector coverage: {}/{} (orphans: {})",
            vc.embedded, vc.total, vc.orphans
        );
    }

    // ── Hybrid search ─────────────────────────────────────────────────────────
    let results = client
        .search("Gemini quota exceeded nightly cron", Some(5), None, None)
        .await?;
    println!("\nTop search results:");
    for r in &results {
        println!(
            "  [{:.3}] {} ({})",
            r.score,
            &r.content.chars().take(80).collect::<String>(),
            r.chunk_type.as_deref().unwrap_or("?")
        );
    }

    // ── Knowledge graph ───────────────────────────────────────────────────────
    let kg = client.kg().await?;
    println!(
        "\nKG: {} entities, {} relations",
        kg.entities.len(),
        kg.relations.len()
    );

    // ── Reflect ───────────────────────────────────────────────────────────────
    println!("\nReflection query: 'what are recurring production incidents?'");
    match client
        .reflect("what are recurring production incidents?", false)
        .await
    {
        Ok(r) => println!("Reflect result keys: {:?}", r.as_object().map(|o| o.keys().collect::<Vec<_>>())),
        Err(e) if e.is_feature_disabled() => println!("(reflect feature disabled)"),
        Err(e) => return Err(e.into()),
    }

    println!("\nDone.");
    Ok(())
}
