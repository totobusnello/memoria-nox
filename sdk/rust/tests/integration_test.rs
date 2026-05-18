/// Integration tests for nox-mem-client using mockito.
///
/// Each test spins up a mock server, exercises the client method, and asserts
/// the correct HTTP call was made and the response deserialised correctly.
use mockito::{Matcher, Server};
use nox_mem_client::{
    AnswerRequest, ConflictStatus, CrystallizeRequest, ExportRequest, HooksDryrunRequest,
    MarkKind, NoxMemClient, NoxMemClientConfig, SupersedeRequest,
};
use serde_json::json;

fn client_for(server: &Server) -> NoxMemClient {
    NoxMemClient::new(NoxMemClientConfig {
        base_url: server.url(),
        auth_token: None,
        ..Default::default()
    })
}

// ── Core ──────────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_health() {
    let mut server = Server::new_async().await;
    let mock = server
        .mock("GET", "/api/health")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(
            json!({
                "chunks": {"total": 62914, "types": []},
                "vectorCoverage": {"embedded": 62912, "total": 62914, "orphans": 0},
                "knowledgeGraph": {"entities": 402, "relations": 544},
                "dbSizeMB": 487.3,
                "services": {"openclaw-gateway": true}
            })
            .to_string(),
        )
        .create_async()
        .await;

    let client = client_for(&server);
    let health = client.health().await.unwrap();
    assert_eq!(health.chunks.unwrap().total, 62914);
    assert_eq!(health.knowledge_graph.unwrap().entities, 402);
    mock.assert_async().await;
}

#[tokio::test]
async fn test_agents() {
    let mut server = Server::new_async().await;
    let mock = server
        .mock("GET", "/api/agents")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(json!([{"name": "forge", "kg_size": 12}]).to_string())
        .create_async()
        .await;

    let client = client_for(&server);
    let agents = client.agents().await.unwrap();
    assert_eq!(agents.len(), 1);
    mock.assert_async().await;
}

#[tokio::test]
async fn test_reflect() {
    let mut server = Server::new_async().await;
    let mock = server
        .mock("GET", "/api/reflect")
        .match_query(Matcher::AllOf(vec![
            Matcher::UrlEncoded("q".into(), "recurring incidents".into()),
        ]))
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(json!({"synthesis": "Gateway crashes cluster around 22:00 BRT"}).to_string())
        .create_async()
        .await;

    let client = client_for(&server);
    let result = client.reflect("recurring incidents", false).await.unwrap();
    assert!(result.get("synthesis").is_some());
    mock.assert_async().await;
}

#[tokio::test]
async fn test_procedures() {
    let mut server = Server::new_async().await;
    let mock = server
        .mock("GET", "/api/procedures")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(
            json!({
                "procedures": [
                    {"id": 88, "title": "Reapply monkey-patch", "steps": ["SSH in", "Run script"], "tags": []}
                ]
            })
            .to_string(),
        )
        .create_async()
        .await;

    let client = client_for(&server);
    let procs = client.procedures().await.unwrap();
    assert_eq!(procs.len(), 1);
    assert_eq!(procs[0].title, "Reapply monkey-patch");
    mock.assert_async().await;
}

#[tokio::test]
async fn test_crystallize() {
    let mut server = Server::new_async().await;
    let mock = server
        .mock("POST", "/api/crystallize")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(json!({"id": 99, "ok": true}).to_string())
        .create_async()
        .await;

    let client = client_for(&server);
    let req = CrystallizeRequest {
        title: "Test procedure".into(),
        steps: vec!["Step 1".into()],
        agent: None,
        tags: None,
        preconditions: None,
    };
    let result = client.crystallize(&req).await.unwrap();
    assert_eq!(result.id, 99);
    assert!(result.ok);
    mock.assert_async().await;
}

// ── Search ────────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_search_get() {
    let mut server = Server::new_async().await;
    let mock = server
        .mock("GET", "/api/search")
        .match_query(Matcher::AllOf(vec![Matcher::UrlEncoded(
            "q".into(),
            "gemini quota".into(),
        )]))
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(
            json!([{
                "chunk_id": 41203,
                "content": "Gemini 2.5 Flash Lite is the default model",
                "score": 0.913,
                "chunk_type": "decision"
            }])
            .to_string(),
        )
        .create_async()
        .await;

    let client = client_for(&server);
    let results = client.search("gemini quota", Some(5), None, None).await.unwrap();
    assert_eq!(results.len(), 1);
    assert_eq!(results[0].chunk_id, 41203);
    mock.assert_async().await;
}

#[tokio::test]
async fn test_search_post() {
    let mut server = Server::new_async().await;
    let mock = server
        .mock("POST", "/api/search")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(json!([]).to_string())
        .create_async()
        .await;

    let client = client_for(&server);
    let req = nox_mem_client::SearchRequest {
        q: "monkey patch".into(),
        limit: Some(3),
        as_of: None,
        changed_since: None,
    };
    let results = client.search_post(&req).await.unwrap();
    assert!(results.is_empty());
    mock.assert_async().await;
}

// ── KG ────────────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_kg() {
    let mut server = Server::new_async().await;
    let mock = server
        .mock("GET", "/api/kg")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(
            json!({
                "entities": [{"id": 1, "name": "openclaw-gateway", "type": "service", "mentions": 100}],
                "relations": []
            })
            .to_string(),
        )
        .create_async()
        .await;

    let client = client_for(&server);
    let kg = client.kg().await.unwrap();
    assert_eq!(kg.entities.len(), 1);
    assert_eq!(kg.entities[0].name, "openclaw-gateway");
    mock.assert_async().await;
}

#[tokio::test]
async fn test_kg_path() {
    let mut server = Server::new_async().await;
    let mock = server
        .mock("GET", "/api/kg/path")
        .match_query(Matcher::AllOf(vec![
            Matcher::UrlEncoded("from".into(), "nox-mem-api".into()),
            Matcher::UrlEncoded("to".into(), "gemini-embedding-001".into()),
        ]))
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(
            json!({"path": ["nox-mem-api", "vectorize", "gemini-embedding-001"]}).to_string(),
        )
        .create_async()
        .await;

    let client = client_for(&server);
    let path = client.kg_path("nox-mem-api", "gemini-embedding-001").await.unwrap();
    assert_eq!(path.unwrap().len(), 3);
    mock.assert_async().await;
}

#[tokio::test]
async fn test_kg_path_null() {
    let mut server = Server::new_async().await;
    let _mock = server
        .mock("GET", "/api/kg/path")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(json!({"path": null}).to_string())
        .create_async()
        .await;

    let client = client_for(&server);
    let path = client.kg_path("a", "z").await.unwrap();
    assert!(path.is_none());
}

// ── Answer (P1) ───────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_answer() {
    let mut server = Server::new_async().await;
    let mock = server
        .mock("POST", "/api/answer")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(
            json!({
                "answer": "Reapply via /root/reapply-monkey-patch.sh [chunk_1]",
                "citations": [{"chunk_id": 41203, "marker_id": "chunk_1", "file_path": "memory/entities/lesson/openclaw-upgrade.md", "snippet": "Run the script"}],
                "metadata": {"latency_ms": 1847, "tokens_in": 100, "tokens_out": 50, "provider": "gemini", "model": "gemini-2.5-flash-lite", "retrieval_count": 8, "fallback_used": false, "retry_count": 0},
                "trace_id": "abc-123"
            })
            .to_string(),
        )
        .create_async()
        .await;

    let client = client_for(&server);
    let req = AnswerRequest {
        question: "How to reapply monkey patch?".into(),
        top_k: Some(8),
        ..Default::default()
    };
    let ans = client.answer(&req).await.unwrap();
    assert_eq!(ans.citations.len(), 1);
    assert_eq!(ans.trace_id, "abc-123");
    mock.assert_async().await;
}

#[tokio::test]
async fn test_answer_feature_disabled() {
    let mut server = Server::new_async().await;
    let _mock = server
        .mock("POST", "/api/answer")
        .with_status(503)
        .with_header("content-type", "application/json")
        .with_body(json!({"error": "feature disabled", "env_var": "NOX_ANSWER_ENABLED"}).to_string())
        .create_async()
        .await;

    let client = client_for(&server);
    let req = AnswerRequest {
        question: "test?".into(),
        ..Default::default()
    };
    let err = client.answer(&req).await.unwrap_err();
    assert!(err.is_feature_disabled());
    assert_eq!(err.status(), Some(503));
}

// ── Confidence / Marking (L3) ─────────────────────────────────────────────────

#[tokio::test]
async fn test_mark_chunk() {
    let mut server = Server::new_async().await;
    let mock = server
        .mock("POST", "/api/chunk/41203/mark")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(
            json!({
                "ok": true,
                "chunk_id": 41203,
                "applied": {"confidence": 0.95, "provenance_kind": "user-marked"},
                "audit_id": 1047
            })
            .to_string(),
        )
        .create_async()
        .await;

    let client = client_for(&server);
    let result = client.mark_chunk(41203, MarkKind::Canonical, Some("Verified")).await.unwrap();
    assert!(result.ok);
    assert_eq!(result.chunk_id, 41203);
    mock.assert_async().await;
}

#[tokio::test]
async fn test_supersede_chunk() {
    let mut server = Server::new_async().await;
    let mock = server
        .mock("POST", "/api/chunk/40123/supersede")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(
            json!({
                "ok": true,
                "chunk_id": 40123,
                "applied": {"confidence": 0.1, "provenance_kind": "user-marked", "superseded_by": 41203},
                "audit_id": 1048
            })
            .to_string(),
        )
        .create_async()
        .await;

    let client = client_for(&server);
    let result = client
        .supersede_chunk(40123, 41203, Some("Newer decision supersedes this"), None)
        .await
        .unwrap();
    assert!(result.ok);
    mock.assert_async().await;
}

// ── Conflict Detection (L2) ───────────────────────────────────────────────────

#[tokio::test]
async fn test_list_conflicts() {
    let mut server = Server::new_async().await;
    let mock = server
        .mock("GET", "/api/kg/conflicts")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(
            json!({
                "total": 1,
                "conflicts": [{"id": 1, "conflict_type": "direct", "status": "unresolved", "source_entity_id": 12, "source_entity_name": "openclaw-gateway", "predicate": "is_deployed_at", "detected_at": "2026-05-18T03:30:00Z", "relation_ids": [88, 91]}]
            })
            .to_string(),
        )
        .create_async()
        .await;

    let client = client_for(&server);
    let (conflicts, total) = client.list_conflicts(None, None, None).await.unwrap();
    assert_eq!(total, 1);
    assert_eq!(conflicts[0].id, 1);
    mock.assert_async().await;
}

#[tokio::test]
async fn test_scan_conflicts() {
    let mut server = Server::new_async().await;
    let mock = server
        .mock("POST", "/api/kg/conflicts/scan")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(json!({"conflicts_found": 3, "conflicts_written": 3, "dry_run": false, "duration_ms": 284}).to_string())
        .create_async()
        .await;

    let client = client_for(&server);
    let result = client.scan_conflicts(None, false).await.unwrap();
    assert_eq!(result["conflicts_found"], 3);
    mock.assert_async().await;
}

// ── Hooks (P2) ────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_hooks_status() {
    let mut server = Server::new_async().await;
    let mock = server
        .mock("GET", "/api/hooks/status")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(json!({"queueDepth": 3, "rateLimitTokens": 47}).to_string())
        .create_async()
        .await;

    let client = client_for(&server);
    let status = client.hooks_status().await.unwrap();
    assert_eq!(status.queue_depth, 3);
    mock.assert_async().await;
}

#[tokio::test]
async fn test_hooks_recent() {
    let mut server = Server::new_async().await;
    let mock = server
        .mock("GET", "/api/hooks/recent")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(
            json!({"rows": [{"event_uuid": "abc", "session_id": "sess1", "project_slug": "memoria-nox", "kind": "message_captured", "timestamp": "2026-05-18T08:14:22Z", "redaction_count": 0}]})
            .to_string(),
        )
        .create_async()
        .await;

    let client = client_for(&server);
    let rows = client.hooks_recent(Some(10)).await.unwrap();
    assert_eq!(rows.len(), 1);
    mock.assert_async().await;
}

#[tokio::test]
async fn test_hooks_dryrun() {
    let mut server = Server::new_async().await;
    let mock = server
        .mock("POST", "/api/hooks/dryrun")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(json!({"result": {"accepted": true, "content": "[PERSON] from Nuvini", "redacted": true}, "trace": []}).to_string())
        .create_async()
        .await;

    let client = client_for(&server);
    let req = HooksDryrunRequest {
        text: "John Smith from Nuvini".into(),
        source: Some("api".into()),
        role: Some("user".into()),
    };
    let result = client.hooks_dryrun(&req).await.unwrap();
    assert!(result["result"]["accepted"].as_bool().unwrap());
    mock.assert_async().await;
}

// ── Error handling ────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_unauthorized() {
    let mut server = Server::new_async().await;
    let _mock = server
        .mock("GET", "/api/health")
        .with_status(401)
        .with_header("content-type", "application/json")
        .with_body(json!({"error": "unauthorized"}).to_string())
        .create_async()
        .await;

    let client = client_for(&server);
    let err = client.health().await.unwrap_err();
    assert!(err.is_unauthorized());
    assert_eq!(err.status(), Some(401));
}

#[tokio::test]
async fn test_cross_kg() {
    let mut server = Server::new_async().await;
    let mock = server
        .mock("GET", "/api/cross-kg")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(json!({"entities": [], "relations": [], "agent_count": 3}).to_string())
        .create_async()
        .await;

    let client = client_for(&server);
    let result = client.cross_kg().await.unwrap();
    assert_eq!(result["agent_count"], 3);
    mock.assert_async().await;
}
