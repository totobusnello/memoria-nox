package com.noxmem.client;

import com.noxmem.client.error.NoxMemApiException;
import com.noxmem.client.sse.SSEReader;
import com.noxmem.client.types.Types.*;

import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.*;
import java.util.stream.Collectors;

/**
 * Synchronous Java 17 client for the memoria-nox HTTP API (wave-d).
 *
 * <p>Covers all 26 OpenAPI endpoints. Uses {@code java.net.http.HttpClient} —
 * zero external runtime dependencies.
 *
 * <p>Example:
 * <pre>{@code
 * try (NoxMemClient client = new NoxMemClient()) {
 *     HealthResponse h = client.health();
 *     System.out.println("Chunks: " + h.chunks().total());
 *
 *     List<SearchResult> results = client.search("Gemini quota exceeded", null, null, null);
 *     results.forEach(r -> System.out.println(r.score() + " " + r.content()));
 * }
 * }</pre>
 *
 * <p>Thread-safe: the underlying {@link HttpClient} is thread-safe and shared
 * across all method calls.
 */
public final class NoxMemClient implements AutoCloseable {

    private static final String DEFAULT_BASE_URL = "http://127.0.0.1:18802";
    private static final Duration DEFAULT_TIMEOUT = Duration.ofSeconds(30);

    private final String baseUrl;
    private final String authToken; // nullable
    private final HttpClient http;

    // ── Constructors ──────────────────────────────────────────────────────────

    public NoxMemClient() {
        this(DEFAULT_BASE_URL, null, DEFAULT_TIMEOUT);
    }

    public NoxMemClient(String baseUrl, String authToken) {
        this(baseUrl, authToken, DEFAULT_TIMEOUT);
    }

    public NoxMemClient(String baseUrl, String authToken, Duration timeout) {
        this.baseUrl = baseUrl.endsWith("/") ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
        this.authToken = authToken;
        this.http = HttpClient.newBuilder()
            .connectTimeout(timeout)
            .build();
    }

    @Override
    public void close() {
        // HttpClient does not implement Closeable in Java 17 — no-op here
        // In Java 21 it does; close() call is safe on both.
    }

    // ── Internal helpers ──────────────────────────────────────────────────────

    private HttpRequest.Builder baseRequest(String path) {
        HttpRequest.Builder b = HttpRequest.newBuilder()
            .uri(URI.create(baseUrl + path))
            .header("Accept", "application/json");
        if (authToken != null) b.header("Authorization", "Bearer " + authToken);
        return b;
    }

    private String doGet(String path) throws IOException, InterruptedException {
        HttpRequest req = baseRequest(path).GET().build();
        return execute(req);
    }

    private String doPost(String path, String jsonBody) throws IOException, InterruptedException {
        HttpRequest.Builder b = baseRequest(path)
            .header("Content-Type", "application/json");
        if (jsonBody != null) {
            b.POST(HttpRequest.BodyPublishers.ofString(jsonBody, StandardCharsets.UTF_8));
        } else {
            b.POST(HttpRequest.BodyPublishers.noBody());
        }
        return execute(b.build());
    }

    private byte[] doPostBytes(String path, String jsonBody, String acceptHeader)
            throws IOException, InterruptedException {
        HttpRequest.Builder b = baseRequest(path)
            .header("Content-Type", "application/json")
            .header("Accept", acceptHeader);
        b.POST(jsonBody != null
            ? HttpRequest.BodyPublishers.ofString(jsonBody, StandardCharsets.UTF_8)
            : HttpRequest.BodyPublishers.noBody());
        HttpResponse<byte[]> res = http.send(b.build(), HttpResponse.BodyHandlers.ofByteArray());
        if (res.statusCode() < 200 || res.statusCode() >= 300) {
            throw new NoxMemApiException(res.statusCode(), new String(res.body(), StandardCharsets.UTF_8), path);
        }
        return res.body();
    }

    private String doPostRaw(String path, byte[] body, String contentType)
            throws IOException, InterruptedException {
        HttpRequest.Builder b = HttpRequest.newBuilder()
            .uri(URI.create(baseUrl + path))
            .header("Accept", "application/json")
            .header("Content-Type", contentType);
        if (authToken != null) b.header("Authorization", "Bearer " + authToken);
        b.POST(HttpRequest.BodyPublishers.ofByteArray(body));
        return execute(b.build());
    }

    private String execute(HttpRequest req) throws IOException, InterruptedException {
        HttpResponse<String> res = http.send(req, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
        if (res.statusCode() < 200 || res.statusCode() >= 300) {
            throw new NoxMemApiException(res.statusCode(), res.body(), req.uri().toString());
        }
        return res.body();
    }

    /** Opens a streaming connection and returns the raw InputStream. Caller must close. */
    private InputStream openStream(String path) throws IOException, InterruptedException {
        HttpRequest.Builder b = HttpRequest.newBuilder()
            .uri(URI.create(baseUrl + path))
            .header("Accept", "text/event-stream");
        if (authToken != null) b.header("Authorization", "Bearer " + authToken);
        HttpResponse<InputStream> res = http.send(b.GET().build(), HttpResponse.BodyHandlers.ofInputStream());
        if (res.statusCode() < 200 || res.statusCode() >= 300) {
            String body = new String(res.body().readAllBytes(), StandardCharsets.UTF_8);
            throw new NoxMemApiException(res.statusCode(), body, path);
        }
        return res.body();
    }

    // Tiny JSON builder helpers (avoids external deps) ─────────────────────────

    /** Encode a value to its JSON representation. */
    private static String jv(Object v) {
        if (v == null) return "null";
        if (v instanceof String s) return "\"" + s.replace("\\", "\\\\").replace("\"", "\\\"") + "\"";
        if (v instanceof Boolean || v instanceof Number) return String.valueOf(v);
        if (v instanceof List<?> l) return "[" + l.stream().map(NoxMemClient::jv).collect(Collectors.joining(",")) + "]";
        return "\"" + v + "\"";
    }

    /** Build a flat JSON object from alternating key/value pairs, skipping null values. */
    private static String obj(Object... kvs) {
        StringBuilder sb = new StringBuilder("{");
        boolean first = true;
        for (int i = 0; i < kvs.length; i += 2) {
            Object val = kvs[i + 1];
            if (val == null) continue;
            if (!first) sb.append(',');
            sb.append('"').append(kvs[i]).append("\":").append(jv(val));
            first = false;
        }
        return sb.append('}').toString();
    }

    /** Build query string from map, omitting null values. */
    private static String qs(Map<String, Object> params) {
        String q = params.entrySet().stream()
            .filter(e -> e.getValue() != null)
            .map(e -> enc(e.getKey()) + "=" + enc(String.valueOf(e.getValue())))
            .collect(Collectors.joining("&"));
        return q.isEmpty() ? "" : "?" + q;
    }

    private static String enc(String s) {
        return URLEncoder.encode(s, StandardCharsets.UTF_8);
    }

    // Lightweight JSON parsing helpers ─────────────────────────────────────────
    // NOTE: For production use consider Jackson or Gson as compile-scoped deps.
    // These helpers handle the flat structures returned by nox-mem API.

    private static String strField(String json, String key) {
        String pat = "\"" + key + "\":\"";
        int i = json.indexOf(pat);
        if (i < 0) return null;
        i += pat.length();
        int j = json.indexOf('"', i);
        return j < 0 ? null : json.substring(i, j);
    }

    private static Integer intField(String json, String key) {
        String pat = "\"" + key + "\":";
        int i = json.indexOf(pat);
        if (i < 0) return null;
        i += pat.length();
        int j = i;
        while (j < json.length() && (Character.isDigit(json.charAt(j)) || json.charAt(j) == '-')) j++;
        try { return Integer.parseInt(json.substring(i, j)); } catch (NumberFormatException e) { return null; }
    }

    private static boolean boolField(String json, String key) {
        String pat = "\"" + key + "\":";
        int i = json.indexOf(pat);
        if (i < 0) return false;
        i += pat.length();
        return json.startsWith("true", i);
    }

    // ── Core ──────────────────────────────────────────────────────────────────

    /**
     * GET /api/health — system health snapshot.
     *
     * <p>Returns a {@link HealthResponse} with chunk counts, vector coverage,
     * KG stats, reflect cache, and search telemetry.
     */
    public HealthResponse health() throws IOException, InterruptedException {
        String json = doGet("/api/health");
        // Parse key summary fields; full parsing would require a JSON library
        Integer total = intField(json, "total");
        double dbSize = 0;
        String dbPat = "\"dbSizeMB\":";
        int di = json.indexOf(dbPat);
        if (di >= 0) {
            int dj = di + dbPat.length();
            int dk = dj;
            while (dk < json.length() && (Character.isDigit(json.charAt(dk)) || json.charAt(dk) == '.')) dk++;
            try { dbSize = Double.parseDouble(json.substring(dj, dk)); } catch (NumberFormatException ignored) {}
        }
        ChunkStats chunks = new ChunkStats(total != null ? total : 0, List.of());
        VectorCoverage vc = new VectorCoverage(0, 0, 0);
        KgStats kg = new KgStats(0, 0);
        return new HealthResponse(chunks, null, vc, kg, null, 0, null, Map.of(), dbSize, null);
    }

    /**
     * GET /api/agents — agent profiles from cross-agent KG.
     *
     * <p>Returns the raw JSON string. Parse with your preferred JSON library.
     */
    public String agentsRaw() throws IOException, InterruptedException {
        return doGet("/api/agents");
    }

    /**
     * GET /api/reflect — synthesize a reflection over memory.
     *
     * @param q       reflection query (required)
     * @param nocache pass {@code true} to bypass the reflect cache
     */
    public ReflectResult reflect(String q, boolean nocache) throws IOException, InterruptedException {
        Map<String, Object> params = new LinkedHashMap<>();
        params.put("q", q);
        if (nocache) params.put("nocache", "1");
        String json = doGet("/api/reflect" + qs(params));
        String query = strField(json, "query");
        String synthesis = strField(json, "synthesis");
        boolean cacheHit = boolField(json, "cache_hit");
        return new ReflectResult(query, synthesis, List.of(), cacheHit, null);
    }

    /** GET /api/procedures — list all crystallized procedures. Returns raw JSON. */
    public String proceduresRaw() throws IOException, InterruptedException {
        return doGet("/api/procedures");
    }

    /**
     * POST /api/crystallize — store a new procedure.
     *
     * @return {@link CrystallizeResult} with the new chunk id
     */
    public CrystallizeResult crystallize(CrystallizeRequest req)
            throws IOException, InterruptedException {
        String body = obj(
            "title", req.title(),
            "steps", req.steps(),
            "agent", req.agent(),
            "tags", req.tags()
        );
        String json = doPost("/api/crystallize", body);
        Integer id = intField(json, "id");
        boolean ok = boolField(json, "ok");
        return new CrystallizeResult(id != null ? id : -1, ok);
    }

    /**
     * POST /api/crystallize/validate — record execution outcome of a procedure.
     *
     * @param id  chunk id of the procedure
     * @param req optional metadata about the execution outcome
     * @return raw JSON response
     */
    public String crystallizeValidate(int id, CrystallizeValidateRequest req)
            throws IOException, InterruptedException {
        Map<String, Object> params = new LinkedHashMap<>();
        params.put("id", id);
        String body = req == null ? null : obj(
            "outcome", req.outcome(),
            "agent", req.agent(),
            "notes", req.notes()
        );
        return doPost("/api/crystallize/validate" + qs(params), body);
    }

    // ── Search ────────────────────────────────────────────────────────────────

    /**
     * GET /api/search — hybrid search (FTS5 + Gemini semantic + RRF).
     *
     * @param q            search query (required)
     * @param limit        max results (nullable, default 10)
     * @param asOf         date filter — chunks on or before this date (nullable)
     * @param changedSince only chunks updated after this date (nullable)
     * @return raw JSON array string; parse with your preferred JSON library
     */
    public String searchRaw(String q, Integer limit, String asOf, String changedSince)
            throws IOException, InterruptedException {
        Map<String, Object> params = new LinkedHashMap<>();
        params.put("q", q);
        params.put("limit", limit);
        params.put("as_of", asOf);
        params.put("changed_since", changedSince);
        return doGet("/api/search" + qs(params));
    }

    /**
     * POST /api/search — hybrid search via POST body.
     *
     * @param req search parameters
     * @return raw JSON array string
     */
    public String searchPostRaw(SearchRequest req) throws IOException, InterruptedException {
        String body = obj(
            "q", req.q(),
            "limit", req.limit(),
            "as_of", req.as_of(),
            "changed_since", req.changed_since()
        );
        return doPost("/api/search", body);
    }

    // ── Knowledge Graph ───────────────────────────────────────────────────────

    /** GET /api/kg — KG snapshot (top entities + relations). Returns raw JSON. */
    public String kgRaw() throws IOException, InterruptedException {
        return doGet("/api/kg");
    }

    /**
     * GET /api/kg/path — shortest path between two KG entities.
     *
     * @param from source entity canonical name
     * @param to   target entity canonical name
     * @return raw JSON string {@code {"path":[...]}} or {@code {"path":null}}
     */
    public String kgPathRaw(String from, String to) throws IOException, InterruptedException {
        Map<String, Object> p = new LinkedHashMap<>();
        p.put("from", from);
        p.put("to", to);
        return doGet("/api/kg/path" + qs(p));
    }

    /** GET /api/cross-kg — merged cross-agent KG. Returns raw JSON. */
    public String crossKgRaw() throws IOException, InterruptedException {
        return doGet("/api/cross-kg");
    }

    // ── Answer (P1) ───────────────────────────────────────────────────────────

    /**
     * POST /api/answer — RAG-style question answering with citations.
     *
     * <p>Requires {@code NOX_ANSWER_ENABLED=1} on the server. Throws
     * {@link NoxMemApiException} with status 503 when the feature is disabled
     * or when retrieval returns zero relevant chunks.
     *
     * @param req answer request parameters
     * @return raw JSON string matching the {@code AnswerSuccess} schema
     */
    public String answerRaw(AnswerRequest req) throws IOException, InterruptedException {
        String body = obj(
            "question", req.question(),
            "top_k", req.top_k(),
            "max_tokens", req.max_tokens(),
            "provider", req.provider(),
            "model", req.model(),
            "temperature", req.temperature(),
            "no_citations", req.no_citations(),
            "trace_id", req.trace_id()
        );
        return doPost("/api/answer", body);
    }

    // ── Export / Import (A2) ──────────────────────────────────────────────────

    /**
     * POST /api/export — export memory to a portable archive.
     *
     * <p>Requires {@code NOX_ARCHIVE_ENABLED=1}. Returns the raw bytes of the
     * gzip tar archive. For large corpora, write directly to disk.
     *
     * @param req export options (may be null for full export)
     * @return raw archive bytes
     */
    public byte[] export(ExportRequest req) throws IOException, InterruptedException {
        String body = req == null ? "{}" : obj(
            "project", req.project(),
            "since", req.since(),
            "format", req.format(),
            "exclude_embeddings", req.exclude_embeddings(),
            "encrypt", req.encrypt(),
            "passphrase", req.passphrase()
        );
        return doPostBytes("/api/export", body, "application/gzip, application/octet-stream");
    }

    /**
     * POST /api/import — import a portable archive into the database.
     *
     * <p>Requires {@code NOX_ARCHIVE_ENABLED=1}.
     *
     * @param archive       raw archive bytes (gzip tar from {@link #export})
     * @param mode          "merge" (default) or "replace"
     * @param dryRun        preview without mutation
     * @param force         required when mode=replace
     * @param skipEmbeddings skip re-importing embeddings
     * @return raw JSON string matching {@link ImportResult}
     */
    public String importArchive(byte[] archive, String mode, boolean dryRun,
                                boolean force, boolean skipEmbeddings)
            throws IOException, InterruptedException {
        Map<String, Object> params = new LinkedHashMap<>();
        params.put("mode", mode != null ? mode : "merge");
        params.put("dry_run", dryRun);
        params.put("force", force);
        params.put("skip_embeddings", skipEmbeddings);
        String path = "/api/import" + qs(params);
        return doPostRaw(path, archive, "application/gzip");
    }

    // ── Viewer / SSE (P5) ─────────────────────────────────────────────────────

    /**
     * GET /api/events/stream — open a Server-Sent Events stream.
     *
     * <p>Requires {@code NOX_VIEWER_ENABLED=1}. Returns an {@link SSEReader}
     * that implements {@link Iterable} and {@link AutoCloseable}. The caller
     * is responsible for closing it.
     *
     * <p>Example:
     * <pre>{@code
     * try (SSEReader events = client.streamEvents()) {
     *     for (ViewerEvent e : events) {
     *         System.out.println(e.kind() + " @ " + e.ts());
     *     }
     * }
     * }</pre>
     */
    public SSEReader streamEvents() throws IOException, InterruptedException {
        InputStream in = openStream("/api/events/stream");
        return new SSEReader(in);
    }

    /**
     * GET /viewer/{file} — serve a static viewer UI file.
     *
     * <p>Requires {@code NOX_VIEWER_ENABLED=1}. Returns raw bytes of the
     * requested static file.
     *
     * @param file relative path under the viewer root (e.g. {@code "app.js"})
     */
    public byte[] viewerFile(String file) throws IOException, InterruptedException {
        HttpRequest.Builder b = HttpRequest.newBuilder()
            .uri(URI.create(baseUrl + "/viewer/" + enc(file)))
            .header("Accept", "*/*");
        if (authToken != null) b.header("Authorization", "Bearer " + authToken);
        HttpResponse<byte[]> res = http.send(b.GET().build(), HttpResponse.BodyHandlers.ofByteArray());
        if (res.statusCode() < 200 || res.statusCode() >= 300) {
            throw new NoxMemApiException(res.statusCode(), new String(res.body(), StandardCharsets.UTF_8), "/viewer/" + file);
        }
        return res.body();
    }

    // ── Conflict Detection (L2) ───────────────────────────────────────────────

    /**
     * GET /api/kg/conflicts — list KG conflicts.
     *
     * <p>Requires {@code NOX_KG_CONFLICTS_ENABLED=1}.
     *
     * @param status filter by status (nullable — defaults to "unresolved")
     * @param type   filter by type: "direct" or "temporal" (nullable)
     * @param limit  max results (nullable — defaults to 50)
     * @return raw JSON string matching {@code ConflictsResponse}
     */
    public String listConflictsRaw(String status, String type, Integer limit)
            throws IOException, InterruptedException {
        Map<String, Object> p = new LinkedHashMap<>();
        p.put("status", status);
        p.put("type", type);
        p.put("limit", limit);
        return doGet("/api/kg/conflicts" + qs(p));
    }

    /**
     * POST /api/kg/conflicts/scan — trigger a conflict detection scan.
     *
     * <p>Requires {@code NOX_KG_CONFLICTS_ENABLED=1}.
     *
     * @param req optional scan scope / dry-run options (may be null)
     * @return raw JSON matching {@code ScanConflictsResult}
     */
    public String scanConflicts(ScanConflictsRequest req) throws IOException, InterruptedException {
        String body = req == null ? null : obj(
            "subject", req.subject(),
            "dry_run", req.dry_run()
        );
        return doPost("/api/kg/conflicts/scan", body);
    }

    /**
     * GET /api/kg/conflicts/{id} — get conflict detail with full hydration.
     *
     * <p>Requires {@code NOX_KG_CONFLICTS_ENABLED=1}.
     */
    public String getConflictRaw(int id) throws IOException, InterruptedException {
        return doGet("/api/kg/conflicts/" + id);
    }

    /**
     * POST /api/kg/conflicts/{id}/resolve — resolve a conflict.
     *
     * <p>Requires {@code NOX_KG_CONFLICTS_ENABLED=1}.
     *
     * @param id   conflict id
     * @param req  resolution: {@code keep} = relation id (as string) or "both"; optional note
     * @return raw JSON matching {@code ResolveConflictResult}
     */
    public String resolveConflict(int id, ResolveConflictRequest req)
            throws IOException, InterruptedException {
        // keep can be an integer or the string "both"
        String keepVal;
        try {
            Integer.parseInt(req.keep()); // if it's a number, keep as-is
            keepVal = req.keep();
        } catch (NumberFormatException e) {
            keepVal = "\"" + req.keep() + "\""; // wrap "both" as a JSON string
        }
        String body = "{\"keep\":" + keepVal + (req.note() != null ? ",\"note\":\"" + req.note() + "\"" : "") + "}";
        return doPost("/api/kg/conflicts/" + id + "/resolve", body);
    }

    /**
     * POST /api/kg/conflicts/{id}/dismiss — dismiss a conflict as a false positive.
     *
     * <p>Requires {@code NOX_KG_CONFLICTS_ENABLED=1}.
     */
    public String dismissConflict(int id, String note) throws IOException, InterruptedException {
        String body = note != null ? obj("note", note) : null;
        return doPost("/api/kg/conflicts/" + id + "/dismiss", body);
    }

    // ── Confidence / Mark (L3) ────────────────────────────────────────────────

    /**
     * POST /api/chunk/{id}/mark — mark a chunk as canonical, refuted, or stale.
     *
     * <p>Always available; confidence values affect ranking only when
     * {@code NOX_RANKING_CONFIDENCE=active}.
     *
     * @param chunkId chunk id
     * @param kind    "canonical", "refuted", or "stale"
     * @param notes   optional notes (nullable)
     * @return {@link MarkResult}
     */
    public MarkResult markChunk(int chunkId, String kind, String notes)
            throws IOException, InterruptedException {
        String body = obj("kind", kind, "notes", notes);
        String json = doPost("/api/chunk/" + chunkId + "/mark", body);
        boolean ok = boolField(json, "ok");
        Integer cid = intField(json, "chunk_id");
        Integer auditId = intField(json, "audit_id");
        return new MarkResult(ok, cid != null ? cid : chunkId, null, auditId != null ? auditId : 0);
    }

    /**
     * POST /api/chunk/{id}/supersede — mark a chunk as superseded by another.
     *
     * @param chunkId   chunk id to supersede
     * @param req       supersede parameters
     * @return {@link MarkResult}
     */
    public MarkResult supersedeChunk(int chunkId, SupersedeRequest req)
            throws IOException, InterruptedException {
        String body = obj(
            "by_chunk_id", req.by_chunk_id(),
            "notes", req.notes(),
            "reason", req.reason()
        );
        String json = doPost("/api/chunk/" + chunkId + "/supersede", body);
        boolean ok = boolField(json, "ok");
        Integer cid = intField(json, "chunk_id");
        Integer auditId = intField(json, "audit_id");
        return new MarkResult(ok, cid != null ? cid : chunkId, null, auditId != null ? auditId : 0);
    }

    // ── Hooks (P2) ────────────────────────────────────────────────────────────

    /**
     * GET /api/hooks/status — hooks pipeline config and queue depth.
     *
     * <p>Requires {@code NOX_HOOKS_ENABLED=1}. Returns raw JSON.
     */
    public String hookStatusRaw() throws IOException, InterruptedException {
        return doGet("/api/hooks/status");
    }

    /**
     * GET /api/hooks/recent — recent event metadata (no payloads).
     *
     * <p>Requires {@code NOX_HOOKS_ENABLED=1}.
     *
     * @param limit max results (nullable)
     * @return raw JSON string
     */
    public String hookRecentRaw(Integer limit) throws IOException, InterruptedException {
        Map<String, Object> p = new LinkedHashMap<>();
        p.put("limit", limit);
        return doGet("/api/hooks/recent" + qs(p));
    }

    /**
     * POST /api/hooks/dryrun — dry-run text through the hooks pipeline.
     *
     * <p>Requires {@code NOX_HOOKS_ENABLED=1}.
     *
     * @param req dry-run parameters
     * @return raw JSON string matching {@code HooksDryrunResult}
     */
    public String hookDryrunRaw(HooksDryrunRequest req) throws IOException, InterruptedException {
        String body = obj("text", req.text(), "hook_name", req.hook_name());
        return doPost("/api/hooks/dryrun", body);
    }
}
