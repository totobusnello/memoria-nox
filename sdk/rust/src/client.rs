use bytes::Bytes;
use futures_util::StreamExt;
use reqwest::{
    header::{HeaderMap, HeaderValue, ACCEPT, AUTHORIZATION, CONTENT_TYPE},
    Client, Response,
};
use serde::Serialize;
use serde_json::Value;
use std::time::Duration;
use tokio_stream::Stream;

use crate::{
    error::NoxMemError,
    types::*,
};

/// Configuration for [`NoxMemClient`].
#[derive(Debug, Clone)]
pub struct NoxMemClientConfig {
    /// Base URL of the memoria-nox HTTP API.
    /// Default: `http://127.0.0.1:18802`
    pub base_url: String,
    /// Bearer token. Required when the server has `NOX_API_TOKEN` set.
    pub auth_token: Option<String>,
    /// Request timeout. Default: 30 seconds.
    pub timeout: Duration,
}

impl Default for NoxMemClientConfig {
    fn default() -> Self {
        NoxMemClientConfig {
            base_url: "http://127.0.0.1:18802".to_string(),
            auth_token: None,
            timeout: Duration::from_secs(30),
        }
    }
}

/// Async Rust client for the memoria-nox HTTP API (openapi 1.0.0-wave-d).
///
/// All methods are `async` and use `tokio`. The client is cheaply `Clone`able
/// (internally wraps `reqwest::Client` which is an `Arc`).
///
/// # Example
/// ```rust,no_run
/// use nox_mem_client::{NoxMemClient, NoxMemClientConfig};
///
/// #[tokio::main]
/// async fn main() -> Result<(), Box<dyn std::error::Error>> {
///     let client = NoxMemClient::new(NoxMemClientConfig {
///         auth_token: std::env::var("NOX_API_TOKEN").ok(),
///         ..Default::default()
///     });
///     let health = client.health().await?;
///     println!("chunks: {:?}", health.chunks);
///     Ok(())
/// }
/// ```
#[derive(Debug, Clone)]
pub struct NoxMemClient {
    inner: Client,
    base_url: String,
    auth_token: Option<String>,
}

impl NoxMemClient {
    /// Create a new client with the given configuration.
    pub fn new(config: NoxMemClientConfig) -> Self {
        let client = Client::builder()
            .timeout(config.timeout)
            .build()
            .expect("failed to build reqwest client");

        NoxMemClient {
            inner: client,
            base_url: config.base_url.trim_end_matches('/').to_string(),
            auth_token: config.auth_token,
        }
    }

    // ── Internals ─────────────────────────────────────────────────────────────

    fn url(&self, path: &str) -> String {
        format!("{}{}", self.base_url, path)
    }

    fn default_headers(&self) -> HeaderMap {
        let mut headers = HeaderMap::new();
        headers.insert(CONTENT_TYPE, HeaderValue::from_static("application/json"));
        headers.insert(ACCEPT, HeaderValue::from_static("application/json"));
        if let Some(token) = &self.auth_token {
            let value = HeaderValue::from_str(&format!("Bearer {}", token))
                .expect("invalid auth token");
            headers.insert(AUTHORIZATION, value);
        }
        headers
    }

    async fn handle_error(resp: Response) -> NoxMemError {
        let status = resp.status().as_u16();
        let url = resp.url().to_string();
        let body: Value = resp
            .json()
            .await
            .unwrap_or(Value::String("(unparseable body)".to_string()));
        let message = body
            .get("error")
            .and_then(Value::as_str)
            .unwrap_or("unknown error")
            .to_string();
        NoxMemError::Api { status, url, message, body }
    }

    async fn get<T: serde::de::DeserializeOwned>(
        &self,
        path: &str,
        params: &[(&str, &str)],
    ) -> Result<T, NoxMemError> {
        let req = self
            .inner
            .get(self.url(path))
            .headers(self.default_headers())
            .query(params);
        let resp = req.send().await?;
        if !resp.status().is_success() {
            return Err(Self::handle_error(resp).await);
        }
        Ok(resp.json::<T>().await?)
    }

    async fn post<B: Serialize, T: serde::de::DeserializeOwned>(
        &self,
        path: &str,
        body: Option<&B>,
        params: &[(&str, &str)],
    ) -> Result<T, NoxMemError> {
        let mut req = self
            .inner
            .post(self.url(path))
            .headers(self.default_headers())
            .query(params);
        if let Some(b) = body {
            req = req.json(b);
        }
        let resp = req.send().await?;
        if !resp.status().is_success() {
            return Err(Self::handle_error(resp).await);
        }
        Ok(resp.json::<T>().await?)
    }

    // ── Core ──────────────────────────────────────────────────────────────────

    /// `GET /api/health` — system health and telemetry snapshot.
    pub async fn health(&self) -> Result<HealthResponse, NoxMemError> {
        self.get("/api/health", &[]).await
    }

    /// `GET /api/agents` — agent profiles from the cross-agent KG.
    pub async fn agents(&self) -> Result<Vec<AgentProfile>, NoxMemError> {
        self.get("/api/agents", &[]).await
    }

    /// `GET /api/reflect` — synthesize a reflection over memory.
    ///
    /// Pass `nocache: true` to bypass the result cache.
    pub async fn reflect(
        &self,
        q: &str,
        nocache: bool,
    ) -> Result<ReflectResult, NoxMemError> {
        let mut query: Vec<(String, String)> = vec![("q".into(), q.into())];
        if nocache {
            query.push(("nocache".into(), "1".into()));
        }
        let resp = self
            .inner
            .get(self.url("/api/reflect"))
            .headers(self.default_headers())
            .query(&query)
            .send()
            .await?;
        if !resp.status().is_success() {
            return Err(Self::handle_error(resp).await);
        }
        Ok(resp.json().await?)
    }

    /// `GET /api/procedures` — list all crystallized procedures.
    pub async fn procedures(&self) -> Result<Vec<Procedure>, NoxMemError> {
        #[derive(serde::Deserialize)]
        struct Wrapper {
            procedures: Vec<Procedure>,
        }
        let w: Wrapper = self.get("/api/procedures", &[]).await?;
        Ok(w.procedures)
    }

    /// `POST /api/crystallize` — store a new step-by-step procedure.
    pub async fn crystallize(
        &self,
        req: &CrystallizeRequest,
    ) -> Result<CrystallizeResult, NoxMemError> {
        self.post("/api/crystallize", Some(req), &[]).await
    }

    /// `POST /api/crystallize/validate` — record execution outcome of a procedure.
    pub async fn crystallize_validate(
        &self,
        id: i64,
        req: Option<&CrystallizeValidateRequest>,
    ) -> Result<Value, NoxMemError> {
        let id_str = id.to_string();
        let mut builder = self
            .inner
            .post(self.url("/api/crystallize/validate"))
            .headers(self.default_headers())
            .query(&[("id", id_str.as_str())]);
        if let Some(body) = req {
            builder = builder.json(body);
        }
        let resp = builder.send().await?;
        if !resp.status().is_success() {
            return Err(Self::handle_error(resp).await);
        }
        Ok(resp.json().await?)
    }

    // ── Search ────────────────────────────────────────────────────────────────

    /// `GET /api/search` — hybrid search (FTS5 + Gemini semantic + RRF).
    pub async fn search(
        &self,
        q: &str,
        limit: Option<u32>,
        as_of: Option<&str>,
        changed_since: Option<&str>,
    ) -> Result<Vec<SearchResult>, NoxMemError> {
        let mut query: Vec<(String, String)> = vec![("q".into(), q.into())];
        if let Some(l) = limit {
            query.push(("limit".into(), l.to_string()));
        }
        if let Some(v) = as_of {
            query.push(("as_of".into(), v.into()));
        }
        if let Some(v) = changed_since {
            query.push(("changed_since".into(), v.into()));
        }
        let resp = self
            .inner
            .get(self.url("/api/search"))
            .headers(self.default_headers())
            .query(&query)
            .send()
            .await?;
        if !resp.status().is_success() {
            return Err(Self::handle_error(resp).await);
        }
        Ok(resp.json().await?)
    }

    /// `POST /api/search` — hybrid search via POST body.
    pub async fn search_post(
        &self,
        req: &SearchRequest,
    ) -> Result<Vec<SearchResult>, NoxMemError> {
        self.post("/api/search", Some(req), &[]).await
    }

    // ── Knowledge Graph ───────────────────────────────────────────────────────

    /// `GET /api/kg` — KG snapshot: top entities and relations.
    pub async fn kg(&self) -> Result<KgResponse, NoxMemError> {
        self.get("/api/kg", &[]).await
    }

    /// `GET /api/kg/path` — shortest path between two KG entities.
    ///
    /// Returns `None` when no path exists.
    pub async fn kg_path(
        &self,
        from: &str,
        to: &str,
    ) -> Result<Option<Vec<String>>, NoxMemError> {
        #[derive(serde::Deserialize)]
        struct Wrapper {
            path: Option<Vec<String>>,
        }
        let resp = self
            .inner
            .get(self.url("/api/kg/path"))
            .headers(self.default_headers())
            .query(&[("from", from), ("to", to)])
            .send()
            .await?;
        if !resp.status().is_success() {
            return Err(Self::handle_error(resp).await);
        }
        let w: Wrapper = resp.json().await?;
        Ok(w.path)
    }

    /// `GET /api/cross-kg` — merged cross-agent knowledge graph.
    pub async fn cross_kg(&self) -> Result<CrossKgResponse, NoxMemError> {
        self.get("/api/cross-kg", &[]).await
    }

    // ── Answer (P1) ───────────────────────────────────────────────────────────

    /// `POST /api/answer` — RAG-style Q&A with citations.
    ///
    /// Requires `NOX_ANSWER_ENABLED=1` on the server.
    pub async fn answer(&self, req: &AnswerRequest) -> Result<AnswerSuccess, NoxMemError> {
        self.post("/api/answer", Some(req), &[]).await
    }

    // ── Export / Import (A2) ──────────────────────────────────────────────────

    /// `POST /api/export` — export memory to a gzip tar archive.
    ///
    /// Requires `NOX_ARCHIVE_ENABLED=1`. The full response body is buffered
    /// into a `Bytes` value. For streaming, use [`export_stream`].
    pub async fn export(&self, req: Option<&ExportRequest>) -> Result<Bytes, NoxMemError> {
        let empty = ExportRequest::default();
        let body = req.unwrap_or(&empty);
        let resp = self
            .inner
            .post(self.url("/api/export"))
            .headers({
                let mut h = self.default_headers();
                h.insert(
                    ACCEPT,
                    HeaderValue::from_static("application/gzip, application/octet-stream"),
                );
                h
            })
            .json(body)
            .send()
            .await?;
        if !resp.status().is_success() {
            return Err(Self::handle_error(resp).await);
        }
        Ok(resp.bytes().await?)
    }

    /// `POST /api/export` — streaming variant.
    ///
    /// Returns a `Stream<Item = Result<Bytes, NoxMemError>>` for piping to disk
    /// without buffering the full archive.
    pub async fn export_stream(
        &self,
        req: Option<&ExportRequest>,
    ) -> Result<impl Stream<Item = Result<Bytes, NoxMemError>>, NoxMemError> {
        let empty = ExportRequest::default();
        let body = req.unwrap_or(&empty);
        let resp = self
            .inner
            .post(self.url("/api/export"))
            .headers({
                let mut h = self.default_headers();
                h.insert(
                    ACCEPT,
                    HeaderValue::from_static("application/gzip, application/octet-stream"),
                );
                h
            })
            .json(body)
            .send()
            .await?;
        if !resp.status().is_success() {
            return Err(Self::handle_error(resp).await);
        }
        let stream = resp.bytes_stream().map(|r| r.map_err(NoxMemError::Http));
        Ok(stream)
    }

    /// `POST /api/import` — import a gzip tar archive into the database.
    ///
    /// Requires `NOX_ARCHIVE_ENABLED=1`.
    pub async fn import(
        &self,
        archive: Bytes,
        mode: Option<ImportMode>,
        dry_run: Option<bool>,
        force: Option<bool>,
        skip_embeddings: Option<bool>,
    ) -> Result<ImportResult, NoxMemError> {
        let mut query: Vec<(&str, String)> = vec![];
        let mode_str;
        if let Some(m) = mode {
            mode_str = serde_json::to_string(&m)
                .unwrap_or_default()
                .trim_matches('"')
                .to_string();
            query.push(("mode", mode_str));
        }
        let dry_run_str;
        if let Some(d) = dry_run {
            dry_run_str = d.to_string();
            query.push(("dry_run", dry_run_str));
        }
        let force_str;
        if let Some(f) = force {
            force_str = f.to_string();
            query.push(("force", force_str));
        }
        let skip_str;
        if let Some(s) = skip_embeddings {
            skip_str = s.to_string();
            query.push(("skip_embeddings", skip_str));
        }

        let mut headers = self.default_headers();
        headers.insert(
            CONTENT_TYPE,
            HeaderValue::from_static("application/gzip"),
        );
        headers.insert(ACCEPT, HeaderValue::from_static("application/json"));

        let resp = self
            .inner
            .post(self.url("/api/import"))
            .headers(headers)
            .query(&query)
            .body(archive)
            .send()
            .await?;
        if !resp.status().is_success() {
            return Err(Self::handle_error(resp).await);
        }
        Ok(resp.json().await?)
    }

    // ── Viewer / SSE (P5) ─────────────────────────────────────────────────────

    /// `GET /api/events/stream` — SSE stream of internal bus events.
    ///
    /// Requires `NOX_VIEWER_ENABLED=1`. Returns a stream that yields
    /// [`ViewerEvent`] items parsed from the SSE wire format.
    /// Break the stream (drop it) or provide a cancellation token to close.
    pub async fn stream_events(
        &self,
        last_event_id: Option<i64>,
    ) -> Result<impl Stream<Item = Result<ViewerEvent, NoxMemError>>, NoxMemError> {
        let mut builder = self
            .inner
            .get(self.url("/api/events/stream"))
            .header(ACCEPT, "text/event-stream");
        if let Some(token) = &self.auth_token {
            builder = builder.header(AUTHORIZATION, format!("Bearer {}", token));
        }
        if let Some(id) = last_event_id {
            builder = builder.header("Last-Event-ID", id.to_string());
        }
        let resp = builder.send().await?;
        if !resp.status().is_success() {
            return Err(Self::handle_error(resp).await);
        }

        let byte_stream = resp.bytes_stream();
        let event_stream = async_stream::stream! {
            let mut buffer = String::new();
            let mut current_data = String::new();
            let mut current_event: Option<String> = None;

            futures_util::pin_mut!(byte_stream);
            while let Some(chunk) = byte_stream.next().await {
                let chunk = match chunk {
                    Ok(b) => b,
                    Err(e) => {
                        yield Err(NoxMemError::Http(e));
                        return;
                    }
                };
                let text = match std::str::from_utf8(&chunk) {
                    Ok(s) => s.to_string(),
                    Err(e) => {
                        yield Err(NoxMemError::Sse(e.to_string()));
                        return;
                    }
                };
                buffer.push_str(&text);
                loop {
                    if let Some(pos) = buffer.find('\n') {
                        let line = buffer[..pos].trim_end_matches('\r').to_string();
                        buffer = buffer[pos + 1..].to_string();

                        if line.is_empty() {
                            // end of event block
                            if !current_data.is_empty() {
                                match serde_json::from_str::<serde_json::Value>(&current_data) {
                                    Ok(mut v) => {
                                        if let Some(kind) = current_event.take() {
                                            if let Some(obj) = v.as_object_mut() {
                                                obj.insert("kind".into(), kind.into());
                                            }
                                        }
                                        yield Ok(ViewerEvent { kind: v.get("kind").and_then(|k| k.as_str()).map(String::from), payload: v });
                                    }
                                    Err(e) => {
                                        yield Err(NoxMemError::Sse(e.to_string()));
                                    }
                                }
                                current_data.clear();
                            }
                        } else if let Some(data) = line.strip_prefix("data:") {
                            current_data.push_str(data.trim_start());
                        } else if let Some(event) = line.strip_prefix("event:") {
                            current_event = Some(event.trim().to_string());
                        }
                        // skip id: and comment lines (:)
                    } else {
                        break;
                    }
                }
            }
        };

        Ok(event_stream)
    }

    // ── Conflict Detection (L2) ───────────────────────────────────────────────

    /// `GET /api/kg/conflicts` — list KG conflicts.
    ///
    /// Requires `NOX_KG_CONFLICTS_ENABLED=1`.
    pub async fn list_conflicts(
        &self,
        status: Option<ConflictStatus>,
        conflict_type: Option<ConflictType>,
        limit: Option<u32>,
    ) -> Result<(Vec<KgConflict>, i64), NoxMemError> {
        #[derive(serde::Deserialize)]
        struct Wrapper {
            conflicts: Vec<KgConflict>,
            total: i64,
        }

        let mut query: Vec<(String, String)> = vec![];
        if let Some(s) = status {
            let s_str = serde_json::to_string(&s)
                .unwrap_or_default()
                .trim_matches('"')
                .to_string();
            query.push(("status".into(), s_str));
        }
        if let Some(t) = conflict_type {
            let t_str = serde_json::to_string(&t)
                .unwrap_or_default()
                .trim_matches('"')
                .to_string();
            query.push(("type".into(), t_str));
        }
        if let Some(l) = limit {
            query.push(("limit".into(), l.to_string()));
        }

        let resp = self
            .inner
            .get(self.url("/api/kg/conflicts"))
            .headers(self.default_headers())
            .query(&query)
            .send()
            .await?;
        if !resp.status().is_success() {
            return Err(Self::handle_error(resp).await);
        }
        let w: Wrapper = resp.json().await?;
        Ok((w.conflicts, w.total))
    }

    /// `POST /api/kg/conflicts/scan` — trigger a conflict detection scan.
    pub async fn scan_conflicts(
        &self,
        subject: Option<&str>,
        dry_run: bool,
    ) -> Result<Value, NoxMemError> {
        #[derive(Serialize)]
        struct Req<'a> {
            #[serde(skip_serializing_if = "Option::is_none")]
            subject: Option<&'a str>,
            dry_run: bool,
        }
        let body = Req { subject, dry_run };
        self.post("/api/kg/conflicts/scan", Some(&body), &[]).await
    }

    /// `GET /api/kg/conflicts/{id}` — get a single conflict with full hydration.
    pub async fn get_conflict(&self, id: i64) -> Result<KgConflictDetail, NoxMemError> {
        self.get(&format!("/api/kg/conflicts/{}", id), &[]).await
    }

    /// `POST /api/kg/conflicts/{id}/resolve` — resolve a conflict.
    pub async fn resolve_conflict(
        &self,
        id: i64,
        keep: Value,
        note: Option<&str>,
    ) -> Result<Value, NoxMemError> {
        #[derive(Serialize)]
        struct Req<'a> {
            keep: Value,
            #[serde(skip_serializing_if = "Option::is_none")]
            note: Option<&'a str>,
        }
        let body = Req { keep, note };
        self.post(
            &format!("/api/kg/conflicts/{}/resolve", id),
            Some(&body),
            &[],
        )
        .await
    }

    /// `POST /api/kg/conflicts/{id}/dismiss` — dismiss a conflict as false positive.
    pub async fn dismiss_conflict(
        &self,
        id: i64,
        note: Option<&str>,
    ) -> Result<Value, NoxMemError> {
        #[derive(Serialize)]
        struct Req<'a> {
            #[serde(skip_serializing_if = "Option::is_none")]
            note: Option<&'a str>,
        }
        let body = Req { note };
        self.post(
            &format!("/api/kg/conflicts/{}/dismiss", id),
            Some(&body),
            &[],
        )
        .await
    }

    // ── Confidence / Marking (L3) ─────────────────────────────────────────────

    /// `POST /api/chunk/{id}/mark` — mark a chunk as canonical, refuted, or stale.
    pub async fn mark_chunk(
        &self,
        id: i64,
        kind: MarkKind,
        notes: Option<&str>,
    ) -> Result<MarkResult, NoxMemError> {
        let body = MarkRequest {
            kind,
            notes: notes.map(String::from),
        };
        self.post(&format!("/api/chunk/{}/mark", id), Some(&body), &[])
            .await
    }

    /// `POST /api/chunk/{id}/supersede` — mark a chunk as superseded by another.
    pub async fn supersede_chunk(
        &self,
        id: i64,
        by_chunk_id: i64,
        notes: Option<&str>,
        reason: Option<SupersedeReason>,
    ) -> Result<MarkResult, NoxMemError> {
        let body = SupersedeRequest {
            by_chunk_id,
            notes: notes.map(String::from),
            reason,
        };
        self.post(
            &format!("/api/chunk/{}/supersede", id),
            Some(&body),
            &[],
        )
        .await
    }

    // ── Hooks (P2) ────────────────────────────────────────────────────────────

    /// `GET /api/hooks/status` — hooks pipeline configuration and queue depth.
    ///
    /// Requires `NOX_HOOKS_ENABLED=1`.
    pub async fn hooks_status(&self) -> Result<HooksStatus, NoxMemError> {
        self.get("/api/hooks/status", &[]).await
    }

    /// `GET /api/hooks/recent` — recent hook event metadata (no payloads).
    ///
    /// Requires `NOX_HOOKS_ENABLED=1`.
    pub async fn hooks_recent(
        &self,
        limit: Option<u32>,
    ) -> Result<Vec<HookEventMeta>, NoxMemError> {
        #[derive(serde::Deserialize)]
        struct Wrapper {
            rows: Vec<HookEventMeta>,
        }
        let mut query: Vec<(String, String)> = vec![];
        if let Some(l) = limit {
            query.push(("limit".into(), l.to_string()));
        }
        let resp = self
            .inner
            .get(self.url("/api/hooks/recent"))
            .headers(self.default_headers())
            .query(&query)
            .send()
            .await?;
        if !resp.status().is_success() {
            return Err(Self::handle_error(resp).await);
        }
        let w: Wrapper = resp.json().await?;
        Ok(w.rows)
    }

    /// `POST /api/hooks/dryrun` — dry-run text through the hooks pipeline.
    ///
    /// Requires `NOX_HOOKS_ENABLED=1`.
    pub async fn hooks_dryrun(
        &self,
        req: &HooksDryrunRequest,
    ) -> Result<HooksDryrunResponse, NoxMemError> {
        self.post("/api/hooks/dryrun", Some(req), &[]).await
    }
}
