// Package noxmem provides a Go client for the memoria-nox HTTP API
// (openapi 1.0.0-wave-d). Zero external dependencies — standard library only.
package noxmem

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"time"
)

// Client is the memoria-nox HTTP API client.
// All methods accept a context.Context for cancellation and deadline propagation.
//
// Usage:
//
//	c := noxmem.New(noxmem.Config{
//	    AuthToken: os.Getenv("NOX_API_TOKEN"),
//	})
//	health, err := c.Health(ctx)
type Client struct {
	baseURL   string
	authToken string
	http      *http.Client
}

// Config holds constructor options for Client.
type Config struct {
	// BaseURL is the API base URL. Default: http://127.0.0.1:18802
	BaseURL string
	// AuthToken is the Bearer token. Required when the server has NOX_API_TOKEN set.
	AuthToken string
	// Timeout is the per-request timeout. Default: 30s.
	Timeout time.Duration
}

// New creates a new Client. Zero values in Config use safe defaults.
func New(cfg Config) *Client {
	if cfg.BaseURL == "" {
		cfg.BaseURL = "http://127.0.0.1:18802"
	}
	if cfg.Timeout == 0 {
		cfg.Timeout = 30 * time.Second
	}
	return &Client{
		baseURL:   strings.TrimRight(cfg.BaseURL, "/"),
		authToken: cfg.AuthToken,
		http:      &http.Client{Timeout: cfg.Timeout},
	}
}

// ── Internal helpers ──────────────────────────────────────────────────────────

func (c *Client) url(path string) string {
	return c.baseURL + path
}

func (c *Client) addAuth(req *http.Request) {
	if c.authToken != "" {
		req.Header.Set("Authorization", "Bearer "+c.authToken)
	}
}

func (c *Client) doJSON(ctx context.Context, method, path string, query url.Values, bodyIn interface{}, out interface{}) error {
	var body io.Reader
	if bodyIn != nil {
		b, err := json.Marshal(bodyIn)
		if err != nil {
			return fmt.Errorf("marshal request: %w", err)
		}
		body = bytes.NewReader(b)
	}

	u := c.url(path)
	if len(query) > 0 {
		u += "?" + query.Encode()
	}

	req, err := http.NewRequestWithContext(ctx, method, u, body)
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/json")
	c.addAuth(req)

	resp, err := c.http.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return c.readAPIError(resp)
	}
	if out != nil {
		return json.NewDecoder(resp.Body).Decode(out)
	}
	return nil
}

func (c *Client) readAPIError(resp *http.Response) error {
	var body map[string]interface{}
	_ = json.NewDecoder(resp.Body).Decode(&body)
	if body == nil {
		body = map[string]interface{}{"error": resp.Status}
	}
	return &APIError{
		StatusCode: resp.StatusCode,
		URL:        resp.Request.URL.String(),
		Body:       body,
	}
}

// ── Core ──────────────────────────────────────────────────────────────────────

// Health calls GET /api/health and returns the system health snapshot.
func (c *Client) Health(ctx context.Context) (*HealthResponse, error) {
	var out HealthResponse
	if err := c.doJSON(ctx, http.MethodGet, "/api/health", nil, nil, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// Agents calls GET /api/agents and returns agent profiles from the cross-agent KG.
func (c *Client) Agents(ctx context.Context) ([]map[string]interface{}, error) {
	var out []map[string]interface{}
	if err := c.doJSON(ctx, http.MethodGet, "/api/agents", nil, nil, &out); err != nil {
		return nil, err
	}
	return out, nil
}

// Reflect calls GET /api/reflect and returns a synthesized reflection.
// Set nocache=true to bypass the reflect cache.
func (c *Client) Reflect(ctx context.Context, q string, nocache bool) (map[string]interface{}, error) {
	qv := url.Values{"q": {q}}
	if nocache {
		qv.Set("nocache", "1")
	}
	var out map[string]interface{}
	if err := c.doJSON(ctx, http.MethodGet, "/api/reflect", qv, nil, &out); err != nil {
		return nil, err
	}
	return out, nil
}

// Procedures calls GET /api/procedures and returns all crystallized procedures.
func (c *Client) Procedures(ctx context.Context) ([]Procedure, error) {
	var wrapper struct {
		Procedures []Procedure `json:"procedures"`
	}
	if err := c.doJSON(ctx, http.MethodGet, "/api/procedures", nil, nil, &wrapper); err != nil {
		return nil, err
	}
	return wrapper.Procedures, nil
}

// Crystallize calls POST /api/crystallize to store a new procedure.
func (c *Client) Crystallize(ctx context.Context, req CrystallizeRequest) (*CrystallizeResult, error) {
	var out CrystallizeResult
	if err := c.doJSON(ctx, http.MethodPost, "/api/crystallize", nil, req, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// CrystallizeValidate calls POST /api/crystallize/validate to record an outcome.
// body may be nil for a bare validation.
func (c *Client) CrystallizeValidate(ctx context.Context, id int64, body *CrystallizeValidateRequest) (map[string]interface{}, error) {
	q := url.Values{"id": {strconv.FormatInt(id, 10)}}
	var out map[string]interface{}
	if err := c.doJSON(ctx, http.MethodPost, "/api/crystallize/validate", q, body, &out); err != nil {
		return nil, err
	}
	return out, nil
}

// ── Search ────────────────────────────────────────────────────────────────────

// SearchOptions holds optional query parameters for Search.
type SearchOptions struct {
	Limit        *int
	AsOf         string
	ChangedSince string
}

// Search calls GET /api/search — hybrid FTS5 + Gemini semantic + RRF.
func (c *Client) Search(ctx context.Context, q string, opts *SearchOptions) ([]SearchResult, error) {
	qv := url.Values{"q": {q}}
	if opts != nil {
		if opts.Limit != nil {
			qv.Set("limit", strconv.Itoa(*opts.Limit))
		}
		if opts.AsOf != "" {
			qv.Set("as_of", opts.AsOf)
		}
		if opts.ChangedSince != "" {
			qv.Set("changed_since", opts.ChangedSince)
		}
	}
	var out []SearchResult
	if err := c.doJSON(ctx, http.MethodGet, "/api/search", qv, nil, &out); err != nil {
		return nil, err
	}
	return out, nil
}

// SearchPost calls POST /api/search — same as Search but via request body.
func (c *Client) SearchPost(ctx context.Context, req SearchRequest) ([]SearchResult, error) {
	var out []SearchResult
	if err := c.doJSON(ctx, http.MethodPost, "/api/search", nil, req, &out); err != nil {
		return nil, err
	}
	return out, nil
}

// ── Knowledge Graph ───────────────────────────────────────────────────────────

// KG calls GET /api/kg and returns the top entities and relations snapshot.
func (c *Client) KG(ctx context.Context) (*KgResponse, error) {
	var out KgResponse
	if err := c.doJSON(ctx, http.MethodGet, "/api/kg", nil, nil, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// KGPath calls GET /api/kg/path and returns the shortest entity path.
// Returns nil slice when no path exists.
func (c *Client) KGPath(ctx context.Context, from, to string) ([]string, error) {
	qv := url.Values{"from": {from}, "to": {to}}
	var wrapper struct {
		Path []string `json:"path"`
	}
	if err := c.doJSON(ctx, http.MethodGet, "/api/kg/path", qv, nil, &wrapper); err != nil {
		return nil, err
	}
	return wrapper.Path, nil
}

// CrossKG calls GET /api/cross-kg and returns the merged cross-agent KG.
func (c *Client) CrossKG(ctx context.Context) (map[string]interface{}, error) {
	var out map[string]interface{}
	if err := c.doJSON(ctx, http.MethodGet, "/api/cross-kg", nil, nil, &out); err != nil {
		return nil, err
	}
	return out, nil
}

// ── Answer (P1) ───────────────────────────────────────────────────────────────

// Answer calls POST /api/answer — RAG Q&A with citations.
// Requires NOX_ANSWER_ENABLED=1 on the server.
func (c *Client) Answer(ctx context.Context, req AnswerRequest) (*AnswerSuccess, error) {
	var out AnswerSuccess
	if err := c.doJSON(ctx, http.MethodPost, "/api/answer", nil, req, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// ── Export / Import (A2) ──────────────────────────────────────────────────────

// Export calls POST /api/export and returns the raw archive bytes.
// Requires NOX_ARCHIVE_ENABLED=1. Pass nil for default options.
// For large corpora use ExportStream to avoid buffering.
func (c *Client) Export(ctx context.Context, req *ExportRequest) ([]byte, http.Header, error) {
	if req == nil {
		req = &ExportRequest{}
	}
	body, err := json.Marshal(req)
	if err != nil {
		return nil, nil, err
	}
	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, c.url("/api/export"), bytes.NewReader(body))
	if err != nil {
		return nil, nil, err
	}
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("Accept", "application/gzip, application/octet-stream")
	c.addAuth(httpReq)

	resp, err := c.http.Do(httpReq)
	if err != nil {
		return nil, nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return nil, nil, c.readAPIError(resp)
	}
	data, err := io.ReadAll(resp.Body)
	return data, resp.Header, err
}

// ExportStream calls POST /api/export and returns the raw response body for
// streaming to disk without buffering. The caller must close the body.
func (c *Client) ExportStream(ctx context.Context, req *ExportRequest) (io.ReadCloser, http.Header, error) {
	if req == nil {
		req = &ExportRequest{}
	}
	body, err := json.Marshal(req)
	if err != nil {
		return nil, nil, err
	}
	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, c.url("/api/export"), bytes.NewReader(body))
	if err != nil {
		return nil, nil, err
	}
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("Accept", "application/gzip, application/octet-stream")
	c.addAuth(httpReq)

	resp, err := c.http.Do(httpReq)
	if err != nil {
		return nil, nil, err
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		defer resp.Body.Close()
		return nil, nil, c.readAPIError(resp)
	}
	return resp.Body, resp.Header, nil
}

// ImportOptions holds optional query parameters for Import.
type ImportOptions struct {
	Mode            ImportMode
	DryRun          bool
	Force           bool
	SkipEmbeddings  bool
}

// Import calls POST /api/import to ingest an archive into the database.
// Requires NOX_ARCHIVE_ENABLED=1.
func (c *Client) Import(ctx context.Context, archive io.Reader, opts *ImportOptions) (*ImportResult, error) {
	qv := url.Values{}
	if opts != nil {
		if opts.Mode != "" {
			qv.Set("mode", string(opts.Mode))
		}
		if opts.DryRun {
			qv.Set("dry_run", "true")
		}
		if opts.Force {
			qv.Set("force", "true")
		}
		if opts.SkipEmbeddings {
			qv.Set("skip_embeddings", "true")
		}
	}

	u := c.url("/api/import")
	if len(qv) > 0 {
		u += "?" + qv.Encode()
	}
	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, u, archive)
	if err != nil {
		return nil, err
	}
	httpReq.Header.Set("Content-Type", "application/gzip")
	httpReq.Header.Set("Accept", "application/json")
	c.addAuth(httpReq)

	resp, err := c.http.Do(httpReq)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return nil, c.readAPIError(resp)
	}
	var out ImportResult
	return &out, json.NewDecoder(resp.Body).Decode(&out)
}

// ── Viewer / SSE (P5) ─────────────────────────────────────────────────────────

// StreamEvents opens GET /api/events/stream (SSE) and returns an SSEReader.
// The caller must call reader.Close() when done.
//
// lastEventID can be 0 to start from the beginning (no Last-Event-ID header).
// Requires NOX_VIEWER_ENABLED=1.
func (c *Client) StreamEvents(ctx context.Context, lastEventID int64) (*SSEReader, error) {
	httpReq, err := http.NewRequestWithContext(ctx, http.MethodGet, c.url("/api/events/stream"), nil)
	if err != nil {
		return nil, err
	}
	httpReq.Header.Set("Accept", "text/event-stream")
	c.addAuth(httpReq)
	if lastEventID > 0 {
		httpReq.Header.Set("Last-Event-ID", strconv.FormatInt(lastEventID, 10))
	}

	// Do NOT set a client timeout for SSE — it's a long-lived connection.
	sseClient := &http.Client{}
	resp, err := sseClient.Do(httpReq)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		defer resp.Body.Close()
		return nil, c.readAPIError(resp)
	}
	return newSSEReader(resp.Body), nil
}

// ── Conflict Detection (L2) ───────────────────────────────────────────────────

// ListConflictsOptions holds optional query parameters for ListConflicts.
type ListConflictsOptions struct {
	Status ConflictStatus
	Type   string // "direct" or "temporal"
	Limit  *int
}

// ListConflicts calls GET /api/kg/conflicts.
// Returns the conflict list and the total count.
func (c *Client) ListConflicts(ctx context.Context, opts *ListConflictsOptions) ([]KgConflict, int64, error) {
	qv := url.Values{}
	if opts != nil {
		if opts.Status != "" {
			qv.Set("status", string(opts.Status))
		}
		if opts.Type != "" {
			qv.Set("type", opts.Type)
		}
		if opts.Limit != nil {
			qv.Set("limit", strconv.Itoa(*opts.Limit))
		}
	}
	var wrapper struct {
		Conflicts []KgConflict `json:"conflicts"`
		Total     int64        `json:"total"`
	}
	if err := c.doJSON(ctx, http.MethodGet, "/api/kg/conflicts", qv, nil, &wrapper); err != nil {
		return nil, 0, err
	}
	return wrapper.Conflicts, wrapper.Total, nil
}

// ScanConflicts calls POST /api/kg/conflicts/scan.
func (c *Client) ScanConflicts(ctx context.Context, subject string, dryRun bool) (map[string]interface{}, error) {
	body := map[string]interface{}{"dry_run": dryRun}
	if subject != "" {
		body["subject"] = subject
	}
	var out map[string]interface{}
	if err := c.doJSON(ctx, http.MethodPost, "/api/kg/conflicts/scan", nil, body, &out); err != nil {
		return nil, err
	}
	return out, nil
}

// GetConflict calls GET /api/kg/conflicts/{id}.
func (c *Client) GetConflict(ctx context.Context, id int64) (map[string]interface{}, error) {
	var out map[string]interface{}
	if err := c.doJSON(ctx, http.MethodGet, fmt.Sprintf("/api/kg/conflicts/%d", id), nil, nil, &out); err != nil {
		return nil, err
	}
	return out, nil
}

// ResolveConflict calls POST /api/kg/conflicts/{id}/resolve.
// keep should be an int64 relation id or the string "both".
func (c *Client) ResolveConflict(ctx context.Context, id int64, keep interface{}, note string) (map[string]interface{}, error) {
	body := map[string]interface{}{"keep": keep}
	if note != "" {
		body["note"] = note
	}
	var out map[string]interface{}
	if err := c.doJSON(ctx, http.MethodPost, fmt.Sprintf("/api/kg/conflicts/%d/resolve", id), nil, body, &out); err != nil {
		return nil, err
	}
	return out, nil
}

// DismissConflict calls POST /api/kg/conflicts/{id}/dismiss.
func (c *Client) DismissConflict(ctx context.Context, id int64, note string) (map[string]interface{}, error) {
	var body interface{}
	if note != "" {
		body = map[string]string{"note": note}
	}
	var out map[string]interface{}
	if err := c.doJSON(ctx, http.MethodPost, fmt.Sprintf("/api/kg/conflicts/%d/dismiss", id), nil, body, &out); err != nil {
		return nil, err
	}
	return out, nil
}

// ── Confidence / Marking (L3) ─────────────────────────────────────────────────

// MarkChunk calls POST /api/chunk/{id}/mark.
func (c *Client) MarkChunk(ctx context.Context, id int64, kind MarkKind, notes string) (*MarkResult, error) {
	req := MarkRequest{Kind: kind, Notes: notes}
	var out MarkResult
	if err := c.doJSON(ctx, http.MethodPost, fmt.Sprintf("/api/chunk/%d/mark", id), nil, req, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// SupersedeChunk calls POST /api/chunk/{id}/supersede.
func (c *Client) SupersedeChunk(ctx context.Context, id int64, req SupersedeRequest) (*MarkResult, error) {
	var out MarkResult
	if err := c.doJSON(ctx, http.MethodPost, fmt.Sprintf("/api/chunk/%d/supersede", id), nil, req, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// ── Hooks (P2) ────────────────────────────────────────────────────────────────

// HooksStatus calls GET /api/hooks/status.
// Requires NOX_HOOKS_ENABLED=1.
func (c *Client) HooksStatus(ctx context.Context) (*HooksStatus, error) {
	var out HooksStatus
	if err := c.doJSON(ctx, http.MethodGet, "/api/hooks/status", nil, nil, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// HooksRecent calls GET /api/hooks/recent. limit <= 0 uses server default (20).
// Requires NOX_HOOKS_ENABLED=1.
func (c *Client) HooksRecent(ctx context.Context, limit int) ([]HookEventMeta, error) {
	qv := url.Values{}
	if limit > 0 {
		qv.Set("limit", strconv.Itoa(limit))
	}
	var wrapper struct {
		Rows []HookEventMeta `json:"rows"`
	}
	if err := c.doJSON(ctx, http.MethodGet, "/api/hooks/recent", qv, nil, &wrapper); err != nil {
		return nil, err
	}
	return wrapper.Rows, nil
}

// HooksDryrun calls POST /api/hooks/dryrun.
// Requires NOX_HOOKS_ENABLED=1.
func (c *Client) HooksDryrun(ctx context.Context, req HooksDryrunRequest) (map[string]interface{}, error) {
	var out map[string]interface{}
	if err := c.doJSON(ctx, http.MethodPost, "/api/hooks/dryrun", nil, req, &out); err != nil {
		return nil, err
	}
	return out, nil
}
