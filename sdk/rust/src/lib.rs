//! # nox-mem-client
//!
//! Type-safe async Rust client for the **memoria-nox** HTTP API
//! (`openapi 1.0.0-wave-d`).
//!
//! ## Features
//! - All 26 endpoints across Core, Search, KG, Answer (P1), Export/Import (A2),
//!   Viewer/SSE (P5), Conflict Detection (L2), Confidence/Marking (L3), Hooks (P2)
//! - Tokio async throughout
//! - SSE streaming via `tokio_stream::Stream`
//! - `thiserror`-based error type with `is_feature_disabled()` and
//!   `is_unauthorized()` helpers
//!
//! ## Quick start
//! ```rust,no_run
//! use nox_mem_client::{NoxMemClient, NoxMemClientConfig};
//!
//! #[tokio::main]
//! async fn main() -> Result<(), Box<dyn std::error::Error>> {
//!     let client = NoxMemClient::new(NoxMemClientConfig {
//!         auth_token: std::env::var("NOX_API_TOKEN").ok(),
//!         ..Default::default()
//!     });
//!     let results = client.search("Gemini quota exceeded", Some(5), None, None).await?;
//!     for r in &results {
//!         println!("{:.3}  {}", r.score, r.content);
//!     }
//!     Ok(())
//! }
//! ```

pub mod client;
pub mod error;
pub mod types;

pub use client::{NoxMemClient, NoxMemClientConfig};
pub use error::NoxMemError;
pub use types::*;
