package noxmem_test

import (
	"context"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	noxmem "github.com/totobusnello/memoria-nox/sdk/go"
)

// helper — spin up a test server with a fixed JSON response.
func testServer(t *testing.T, method, path string, status int, body interface{}) (*httptest.Server, *noxmem.Client) {
	t.Helper()
	var bodyBytes []byte
	switch v := body.(type) {
	case string:
		bodyBytes = []byte(v)
	default:
		var err error
		bodyBytes, err = json.Marshal(v)
		if err != nil {
			t.Fatalf("marshal test body: %v", err)
		}
	}
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != method || r.URL.Path != path {
			http.Error(w, "unexpected request: "+r.Method+" "+r.URL.Path, 500)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(status)
		_, _ = w.Write(bodyBytes)
	}))
	client := noxmem.New(noxmem.Config{BaseURL: srv.URL})
	return srv, client
}

func ctx() context.Context { return context.Background() }

// ── Core ──────────────────────────────────────────────────────────────────────

func TestHealth(t *testing.T) {
	srv, client := testServer(t, http.MethodGet, "/api/health", 200, map[string]interface{}{
		"chunks":          map[string]interface{}{"total": float64(62914), "types": []interface{}{}},
		"vectorCoverage":  map[string]interface{}{"embedded": float64(62912), "total": float64(62914), "orphans": float64(0)},
		"knowledgeGraph":  map[string]interface{}{"entities": float64(402), "relations": float64(544)},
		"dbSizeMB":        487.3,
		"services":        map[string]interface{}{"openclaw-gateway": true},
	})
	defer srv.Close()

	health, err := client.Health(ctx())
	if err != nil {
		t.Fatalf("Health: %v", err)
	}
	if health.Chunks == nil || health.Chunks.Total != 62914 {
		t.Errorf("expected 62914 chunks, got %v", health.Chunks)
	}
	if health.KnowledgeGraph == nil || health.KnowledgeGraph.Entities != 402 {
		t.Errorf("expected 402 entities, got %v", health.KnowledgeGraph)
	}
}

func TestAgents(t *testing.T) {
	srv, client := testServer(t, http.MethodGet, "/api/agents", 200,
		[]interface{}{map[string]interface{}{"name": "forge", "kg_size": 12}},
	)
	defer srv.Close()

	agents, err := client.Agents(ctx())
	if err != nil {
		t.Fatalf("Agents: %v", err)
	}
	if len(agents) != 1 {
		t.Errorf("expected 1 agent, got %d", len(agents))
	}
}

func TestReflect(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/reflect" {
			http.Error(w, "unexpected", 500)
			return
		}
		q := r.URL.Query().Get("q")
		if q == "" {
			http.Error(w, "missing q", 400)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"synthesis": "summary for: " + q})
	}))
	defer srv.Close()
	client := noxmem.New(noxmem.Config{BaseURL: srv.URL})

	result, err := client.Reflect(ctx(), "recurring incidents", false)
	if err != nil {
		t.Fatalf("Reflect: %v", err)
	}
	if result["synthesis"] == nil {
		t.Error("expected synthesis key")
	}
}

func TestProcedures(t *testing.T) {
	srv, client := testServer(t, http.MethodGet, "/api/procedures", 200, map[string]interface{}{
		"procedures": []interface{}{
			map[string]interface{}{"id": float64(88), "title": "Reapply monkey-patch", "steps": []interface{}{"SSH in", "Run script"}, "tags": []interface{}{}},
		},
	})
	defer srv.Close()

	procs, err := client.Procedures(ctx())
	if err != nil {
		t.Fatalf("Procedures: %v", err)
	}
	if len(procs) != 1 || procs[0].Title != "Reapply monkey-patch" {
		t.Errorf("unexpected procedures: %v", procs)
	}
}

func TestCrystallize(t *testing.T) {
	srv, client := testServer(t, http.MethodPost, "/api/crystallize", 200,
		map[string]interface{}{"id": float64(99), "ok": true},
	)
	defer srv.Close()

	result, err := client.Crystallize(ctx(), noxmem.CrystallizeRequest{
		Title: "Test procedure",
		Steps: []string{"Step 1"},
	})
	if err != nil {
		t.Fatalf("Crystallize: %v", err)
	}
	if result.ID != 99 || !result.OK {
		t.Errorf("unexpected result: %+v", result)
	}
}

// ── Search ────────────────────────────────────────────────────────────────────

func TestSearch(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/search" {
			http.Error(w, "unexpected", 500)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode([]noxmem.SearchResult{
			{ChunkID: 41203, Content: "Gemini 2.5 Flash Lite is the default", Score: 0.913, ChunkType: "decision"},
		})
	}))
	defer srv.Close()
	client := noxmem.New(noxmem.Config{BaseURL: srv.URL})

	results, err := client.Search(ctx(), "gemini quota", nil)
	if err != nil {
		t.Fatalf("Search: %v", err)
	}
	if len(results) != 1 || results[0].ChunkID != 41203 {
		t.Errorf("unexpected results: %v", results)
	}
}

func TestSearchPost(t *testing.T) {
	srv, client := testServer(t, http.MethodPost, "/api/search", 200, []interface{}{})
	defer srv.Close()

	limit := 3
	results, err := client.SearchPost(ctx(), noxmem.SearchRequest{Q: "monkey patch", Limit: &limit})
	if err != nil {
		t.Fatalf("SearchPost: %v", err)
	}
	if len(results) != 0 {
		t.Errorf("expected empty, got %d", len(results))
	}
}

// ── KG ────────────────────────────────────────────────────────────────────────

func TestKG(t *testing.T) {
	srv, client := testServer(t, http.MethodGet, "/api/kg", 200, map[string]interface{}{
		"entities":  []interface{}{map[string]interface{}{"id": float64(1), "name": "openclaw-gateway", "type": "service", "mentions": float64(100)}},
		"relations": []interface{}{},
	})
	defer srv.Close()

	kg, err := client.KG(ctx())
	if err != nil {
		t.Fatalf("KG: %v", err)
	}
	if len(kg.Entities) != 1 || kg.Entities[0].Name != "openclaw-gateway" {
		t.Errorf("unexpected KG: %v", kg)
	}
}

func TestKGPath(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"path": []string{"nox-mem-api", "vectorize", "gemini-embedding-001"},
		})
	}))
	defer srv.Close()
	client := noxmem.New(noxmem.Config{BaseURL: srv.URL})

	path, err := client.KGPath(ctx(), "nox-mem-api", "gemini-embedding-001")
	if err != nil {
		t.Fatalf("KGPath: %v", err)
	}
	if len(path) != 3 {
		t.Errorf("expected 3 hops, got %d", len(path))
	}
}

func TestKGPathNull(t *testing.T) {
	srv, client := testServer(t, http.MethodGet, "/api/kg/path", 200, map[string]interface{}{"path": nil})
	defer srv.Close()

	path, err := client.KGPath(ctx(), "a", "z")
	if err != nil {
		t.Fatalf("KGPath: %v", err)
	}
	if path != nil {
		t.Errorf("expected nil path, got %v", path)
	}
}

func TestCrossKG(t *testing.T) {
	srv, client := testServer(t, http.MethodGet, "/api/cross-kg", 200,
		map[string]interface{}{"entities": []interface{}{}, "agent_count": float64(3)},
	)
	defer srv.Close()

	result, err := client.CrossKG(ctx())
	if err != nil {
		t.Fatalf("CrossKG: %v", err)
	}
	if result["agent_count"] != float64(3) {
		t.Errorf("expected agent_count=3, got %v", result["agent_count"])
	}
}

// ── Answer (P1) ───────────────────────────────────────────────────────────────

func TestAnswer(t *testing.T) {
	srv, client := testServer(t, http.MethodPost, "/api/answer", 200, map[string]interface{}{
		"answer":    "Reapply via /root/reapply-monkey-patch.sh [chunk_1]",
		"citations": []interface{}{map[string]interface{}{"chunk_id": float64(41203), "marker_id": "chunk_1", "file_path": "memory/entities/lesson/openclaw-upgrade.md", "snippet": "Run the script"}},
		"metadata":  map[string]interface{}{"latency_ms": float64(1847), "tokens_in": float64(100), "tokens_out": float64(50), "provider": "gemini", "model": "gemini-2.5-flash-lite", "retrieval_count": float64(8), "fallback_used": false, "retry_count": float64(0)},
		"trace_id":  "abc-123",
	})
	defer srv.Close()

	topK := 8
	ans, err := client.Answer(ctx(), noxmem.AnswerRequest{Question: "How to reapply monkey patch?", TopK: &topK})
	if err != nil {
		t.Fatalf("Answer: %v", err)
	}
	if len(ans.Citations) != 1 || ans.TraceID != "abc-123" {
		t.Errorf("unexpected answer: %+v", ans)
	}
}

func TestAnswerFeatureDisabled(t *testing.T) {
	srv, client := testServer(t, http.MethodPost, "/api/answer", 503,
		map[string]interface{}{"error": "feature disabled", "env_var": "NOX_ANSWER_ENABLED"},
	)
	defer srv.Close()

	_, err := client.Answer(ctx(), noxmem.AnswerRequest{Question: "test?"})
	if err == nil {
		t.Fatal("expected error")
	}
	apiErr, ok := err.(*noxmem.APIError)
	if !ok {
		t.Fatalf("expected *APIError, got %T", err)
	}
	if !apiErr.IsFeatureDisabled() {
		t.Error("expected IsFeatureDisabled")
	}
}

// ── Confidence / Marking (L3) ─────────────────────────────────────────────────

func TestMarkChunk(t *testing.T) {
	srv, client := testServer(t, http.MethodPost, "/api/chunk/41203/mark", 200, map[string]interface{}{
		"ok":       true,
		"chunk_id": float64(41203),
		"applied":  map[string]interface{}{"confidence": 0.95, "provenance_kind": "user-marked"},
		"audit_id": float64(1047),
	})
	defer srv.Close()

	result, err := client.MarkChunk(ctx(), 41203, noxmem.MarkKindCanonical, "Verified")
	if err != nil {
		t.Fatalf("MarkChunk: %v", err)
	}
	if !result.OK || result.ChunkID != 41203 {
		t.Errorf("unexpected result: %+v", result)
	}
}

func TestSupersedeChunk(t *testing.T) {
	srv, client := testServer(t, http.MethodPost, "/api/chunk/40123/supersede", 200, map[string]interface{}{
		"ok":       true,
		"chunk_id": float64(40123),
		"applied":  map[string]interface{}{"confidence": 0.1, "provenance_kind": "user-marked", "superseded_by": float64(41203)},
		"audit_id": float64(1048),
	})
	defer srv.Close()

	result, err := client.SupersedeChunk(ctx(), 40123, noxmem.SupersedeRequest{
		ByChunkID: 41203,
		Notes:     "Newer decision supersedes this",
	})
	if err != nil {
		t.Fatalf("SupersedeChunk: %v", err)
	}
	if !result.OK {
		t.Error("expected ok=true")
	}
}

// ── Conflict Detection (L2) ───────────────────────────────────────────────────

func TestListConflicts(t *testing.T) {
	srv, client := testServer(t, http.MethodGet, "/api/kg/conflicts", 200, map[string]interface{}{
		"total": float64(1),
		"conflicts": []interface{}{
			map[string]interface{}{
				"id": float64(1), "conflict_type": "direct", "status": "unresolved",
				"source_entity_id": float64(12), "source_entity_name": "openclaw-gateway",
				"predicate": "is_deployed_at", "detected_at": "2026-05-18T03:30:00Z",
				"relation_ids": []interface{}{float64(88), float64(91)},
			},
		},
	})
	defer srv.Close()

	conflicts, total, err := client.ListConflicts(ctx(), nil)
	if err != nil {
		t.Fatalf("ListConflicts: %v", err)
	}
	if total != 1 || len(conflicts) != 1 || conflicts[0].ID != 1 {
		t.Errorf("unexpected conflicts: total=%d, list=%v", total, conflicts)
	}
}

func TestScanConflicts(t *testing.T) {
	srv, client := testServer(t, http.MethodPost, "/api/kg/conflicts/scan", 200,
		map[string]interface{}{"conflicts_found": float64(3), "conflicts_written": float64(3), "dry_run": false, "duration_ms": float64(284)},
	)
	defer srv.Close()

	result, err := client.ScanConflicts(ctx(), "", false)
	if err != nil {
		t.Fatalf("ScanConflicts: %v", err)
	}
	if result["conflicts_found"] != float64(3) {
		t.Errorf("unexpected result: %v", result)
	}
}

// ── Hooks (P2) ────────────────────────────────────────────────────────────────

func TestHooksStatus(t *testing.T) {
	srv, client := testServer(t, http.MethodGet, "/api/hooks/status", 200,
		map[string]interface{}{"queueDepth": float64(3), "rateLimitTokens": float64(47)},
	)
	defer srv.Close()

	status, err := client.HooksStatus(ctx())
	if err != nil {
		t.Fatalf("HooksStatus: %v", err)
	}
	if status.QueueDepth != 3 {
		t.Errorf("expected queueDepth=3, got %d", status.QueueDepth)
	}
}

func TestHooksRecent(t *testing.T) {
	srv, client := testServer(t, http.MethodGet, "/api/hooks/recent", 200,
		map[string]interface{}{"rows": []interface{}{
			map[string]interface{}{"event_uuid": "abc", "session_id": "sess1", "project_slug": "memoria-nox", "kind": "message_captured", "timestamp": "2026-05-18T08:14:22Z", "redaction_count": float64(0)},
		}},
	)
	defer srv.Close()

	rows, err := client.HooksRecent(ctx(), 10)
	if err != nil {
		t.Fatalf("HooksRecent: %v", err)
	}
	if len(rows) != 1 || rows[0].EventUUID != "abc" {
		t.Errorf("unexpected rows: %v", rows)
	}
}

func TestHooksDryrun(t *testing.T) {
	srv, client := testServer(t, http.MethodPost, "/api/hooks/dryrun", 200,
		map[string]interface{}{"result": map[string]interface{}{"accepted": true, "content": "[PERSON] from Nuvini", "redacted": true}, "trace": []interface{}{}},
	)
	defer srv.Close()

	result, err := client.HooksDryrun(ctx(), noxmem.HooksDryrunRequest{
		Text:   "John Smith from Nuvini",
		Source: "api",
		Role:   "user",
	})
	if err != nil {
		t.Fatalf("HooksDryrun: %v", err)
	}
	inner, _ := result["result"].(map[string]interface{})
	if inner["accepted"] != true {
		t.Error("expected accepted=true")
	}
}

// ── Error handling ────────────────────────────────────────────────────────────

func TestUnauthorized(t *testing.T) {
	srv, client := testServer(t, http.MethodGet, "/api/health", 401,
		map[string]interface{}{"error": "unauthorized"},
	)
	defer srv.Close()

	_, err := client.Health(ctx())
	if err == nil {
		t.Fatal("expected error")
	}
	apiErr, ok := err.(*noxmem.APIError)
	if !ok {
		t.Fatalf("expected *APIError, got %T", err)
	}
	if !apiErr.IsUnauthorized() {
		t.Error("expected IsUnauthorized")
	}
}

// ── SSE ───────────────────────────────────────────────────────────────────────

func TestSSEReader(t *testing.T) {
	sseData := `: connected

id: 1
event: chunk.created
data: {"chunk_id":62915,"type":"lesson"}

: heartbeat 2026-05-18T08:30:15.000Z ring=128 clients=1

id: 2
event: kg.entity.created
data: {"entity_id":403,"name":"new-entity"}

`
	body := io.NopCloser(strings.NewReader(sseData))
	// Import SSEReader directly via a test HTTP server
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/event-stream")
		w.WriteHeader(200)
		_, _ = io.WriteString(w, sseData)
	}))
	defer srv.Close()
	_ = body

	client := noxmem.New(noxmem.Config{BaseURL: srv.URL})
	reader, err := client.StreamEvents(ctx(), 0)
	if err != nil {
		t.Fatalf("StreamEvents: %v", err)
	}
	defer reader.Close()

	ev1, err := reader.Next()
	if err != nil {
		t.Fatalf("Next() event 1: %v", err)
	}
	if ev1.Kind != "chunk.created" {
		t.Errorf("expected chunk.created, got %q", ev1.Kind)
	}

	ev2, err := reader.Next()
	if err != nil {
		t.Fatalf("Next() event 2: %v", err)
	}
	if ev2.Kind != "kg.entity.created" {
		t.Errorf("expected kg.entity.created, got %q", ev2.Kind)
	}
}
