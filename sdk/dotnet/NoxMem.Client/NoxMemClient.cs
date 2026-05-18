using NoxMem.Client.Errors;
using NoxMem.Client.Sse;
using NoxMem.Client.Types;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace NoxMem.Client;

/// <summary>
/// Async C# client for the memoria-nox HTTP API (wave-d).
///
/// <para>Covers all 26 OpenAPI endpoints. Uses <see cref="System.Net.Http.HttpClient"/> —
/// no external NuGet runtime dependencies beyond the .NET 8 BCL.</para>
///
/// <para>Example:</para>
/// <code>
/// using var client = new NoxMemClient();
/// var health = await client.HealthAsync();
/// Console.WriteLine($"Chunks: {health?.Chunks?.Total}");
///
/// var results = await client.SearchAsync("Gemini quota exceeded");
/// foreach (var r in results) Console.WriteLine($"{r.Score:F3} {r.Content}");
/// </code>
///
/// <para>Thread-safe: <see cref="HttpClient"/> is shared and reused.</para>
/// </summary>
public sealed class NoxMemClient : IDisposable
{
    private static readonly string DefaultBaseUrl = "http://127.0.0.1:18802";

    private readonly HttpClient _http;
    private readonly string? _authToken;
    private readonly JsonSerializerOptions _json;

    // ── Constructors ──────────────────────────────────────────────────────────

    /// <summary>Creates a client connecting to the default local server.</summary>
    public NoxMemClient() : this(DefaultBaseUrl, null) { }

    /// <param name="baseUrl">Server base URL (e.g. <c>http://127.0.0.1:18802</c>).</param>
    /// <param name="authToken">Bearer token. Null when <c>NOX_API_TOKEN</c> is not set.</param>
    /// <param name="timeout">HTTP request timeout. Default 30 s.</param>
    public NoxMemClient(string baseUrl, string? authToken, TimeSpan? timeout = null)
    {
        _authToken = authToken;
        _http = new HttpClient
        {
            BaseAddress = new Uri(baseUrl.TrimEnd('/') + "/"),
            Timeout = timeout ?? TimeSpan.FromSeconds(30),
        };
        _http.DefaultRequestHeaders.Add("Accept", "application/json");
        if (authToken is not null)
            _http.DefaultRequestHeaders.Authorization =
                new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", authToken);

        _json = new JsonSerializerOptions
        {
            PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
            DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
            NumberHandling = JsonNumberHandling.AllowReadingFromString,
        };
    }

    public void Dispose() => _http.Dispose();

    // ── Internal helpers ──────────────────────────────────────────────────────

    private async Task<T?> GetJsonAsync<T>(string path, CancellationToken ct = default)
    {
        var res = await _http.GetAsync(path, ct).ConfigureAwait(false);
        await EnsureSuccessAsync(res, path).ConfigureAwait(false);
        return await res.Content.ReadFromJsonAsync<T>(_json, ct).ConfigureAwait(false);
    }

    private async Task<T?> PostJsonAsync<T>(string path, object? body, CancellationToken ct = default)
    {
        HttpContent? content = body is null
            ? null
            : JsonContent.Create(body, options: _json);
        var res = await _http.PostAsync(path, content, ct).ConfigureAwait(false);
        await EnsureSuccessAsync(res, path).ConfigureAwait(false);
        return await res.Content.ReadFromJsonAsync<T>(_json, ct).ConfigureAwait(false);
    }

    private async Task<byte[]> PostBytesAsync(string path, object? body, string accept,
                                               CancellationToken ct = default)
    {
        var req = new HttpRequestMessage(HttpMethod.Post, path)
        {
            Content = body is null
                ? null
                : JsonContent.Create(body, options: _json),
        };
        req.Headers.Add("Accept", accept);
        var res = await _http.SendAsync(req, ct).ConfigureAwait(false);
        await EnsureSuccessAsync(res, path).ConfigureAwait(false);
        return await res.Content.ReadAsByteArrayAsync(ct).ConfigureAwait(false);
    }

    private async Task<T?> PostRawBytesAsync<T>(string path, byte[] bytes, string contentType,
                                                  string queryString, CancellationToken ct = default)
    {
        var req = new HttpRequestMessage(HttpMethod.Post, path + queryString)
        {
            Content = new ByteArrayContent(bytes),
        };
        req.Content.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue(contentType);
        var res = await _http.SendAsync(req, ct).ConfigureAwait(false);
        await EnsureSuccessAsync(res, path).ConfigureAwait(false);
        return await res.Content.ReadFromJsonAsync<T>(_json, ct).ConfigureAwait(false);
    }

    private static async Task EnsureSuccessAsync(HttpResponseMessage res, string path)
    {
        if (res.IsSuccessStatusCode) return;
        string body = await res.Content.ReadAsStringAsync().ConfigureAwait(false);
        throw new NoxMemApiException((int)res.StatusCode, body, path);
    }

    private static string Qs(Dictionary<string, string?> p)
    {
        var parts = p
            .Where(kv => kv.Value is not null)
            .Select(kv => $"{Uri.EscapeDataString(kv.Key)}={Uri.EscapeDataString(kv.Value!)}");
        string joined = string.Join("&", parts);
        return joined.Length == 0 ? string.Empty : "?" + joined;
    }

    // ── Core ──────────────────────────────────────────────────────────────────

    /// <summary>GET /api/health — system health, chunk counts, vector coverage.</summary>
    public Task<HealthResponse?> HealthAsync(CancellationToken ct = default)
        => GetJsonAsync<HealthResponse>("api/health", ct);

    /// <summary>GET /api/agents — agent profiles from cross-agent KG.</summary>
    public Task<List<AgentProfile>?> AgentsAsync(CancellationToken ct = default)
        => GetJsonAsync<List<AgentProfile>>("api/agents", ct);

    /// <summary>
    /// GET /api/reflect — synthesize a reflection over memory.
    /// </summary>
    /// <param name="q">Reflection query.</param>
    /// <param name="nocache">Bypass the reflect cache when true.</param>
    public Task<ReflectResult?> ReflectAsync(string q, bool nocache = false,
                                              CancellationToken ct = default)
    {
        string qs = Qs(new() { ["q"] = q, ["nocache"] = nocache ? "1" : null });
        return GetJsonAsync<ReflectResult>("api/reflect" + qs, ct);
    }

    /// <summary>GET /api/procedures — list all crystallized procedures.</summary>
    public async Task<List<Procedure>?> ProceduresAsync(CancellationToken ct = default)
    {
        var doc = await GetJsonAsync<JsonDocument>("api/procedures", ct).ConfigureAwait(false);
        if (doc is null) return null;
        return doc.RootElement.TryGetProperty("procedures", out var arr)
            ? arr.Deserialize<List<Procedure>>(_json)
            : null;
    }

    /// <summary>POST /api/crystallize — store a new procedure.</summary>
    public Task<CrystallizeResult?> CrystallizeAsync(CrystallizeRequest req,
                                                       CancellationToken ct = default)
        => PostJsonAsync<CrystallizeResult>("api/crystallize", req, ct);

    /// <summary>POST /api/crystallize/validate — record execution outcome.</summary>
    public Task<JsonDocument?> CrystallizeValidateAsync(int id,
                                                          CrystallizeValidateRequest? req = null,
                                                          CancellationToken ct = default)
        => PostJsonAsync<JsonDocument>($"api/crystallize/validate?id={id}", req, ct);

    // ── Search ────────────────────────────────────────────────────────────────

    /// <summary>
    /// GET /api/search — hybrid search (FTS5 + Gemini semantic + RRF).
    /// </summary>
    /// <param name="q">Search query (required).</param>
    /// <param name="limit">Max results (default 10).</param>
    /// <param name="asOf">Return chunks on or before this date (ISO or relative like "7d").</param>
    /// <param name="changedSince">Return chunks updated after this date.</param>
    public Task<List<SearchResult>?> SearchAsync(string q, int? limit = null,
                                                  string? asOf = null, string? changedSince = null,
                                                  CancellationToken ct = default)
    {
        string qs = Qs(new()
        {
            ["q"] = q,
            ["limit"] = limit?.ToString(),
            ["as_of"] = asOf,
            ["changed_since"] = changedSince,
        });
        return GetJsonAsync<List<SearchResult>>("api/search" + qs, ct);
    }

    /// <summary>POST /api/search — hybrid search via POST body.</summary>
    public Task<List<SearchResult>?> SearchPostAsync(SearchRequest req,
                                                      CancellationToken ct = default)
        => PostJsonAsync<List<SearchResult>>("api/search", req, ct);

    // ── Knowledge Graph ───────────────────────────────────────────────────────

    /// <summary>GET /api/kg — KG snapshot: top entities and relations.</summary>
    public Task<KgResponse?> KgAsync(CancellationToken ct = default)
        => GetJsonAsync<KgResponse>("api/kg", ct);

    /// <summary>
    /// GET /api/kg/path — shortest path between two KG entities.
    /// Returns null path when no route exists.
    /// </summary>
    public Task<KgPathResponse?> KgPathAsync(string from, string to,
                                              CancellationToken ct = default)
    {
        string qs = Qs(new() { ["from"] = from, ["to"] = to });
        return GetJsonAsync<KgPathResponse>("api/kg/path" + qs, ct);
    }

    /// <summary>GET /api/cross-kg — merged cross-agent KG.</summary>
    public Task<CrossKgResponse?> CrossKgAsync(CancellationToken ct = default)
        => GetJsonAsync<CrossKgResponse>("api/cross-kg", ct);

    // ── Answer (P1) ───────────────────────────────────────────────────────────

    /// <summary>
    /// POST /api/answer — RAG-style question answering with citations.
    /// Requires <c>NOX_ANSWER_ENABLED=1</c> on the server.
    /// </summary>
    /// <exception cref="NoxMemApiException">
    /// Status 503 when feature is disabled or retrieval returns zero chunks.
    /// </exception>
    public Task<AnswerSuccess?> AnswerAsync(AnswerRequest req, CancellationToken ct = default)
        => PostJsonAsync<AnswerSuccess>("api/answer", req, ct);

    // ── Export / Import (A2) ──────────────────────────────────────────────────

    /// <summary>
    /// POST /api/export — export memory to a portable archive.
    /// Requires <c>NOX_ARCHIVE_ENABLED=1</c>. Returns raw archive bytes.
    /// </summary>
    public Task<byte[]> ExportAsync(ExportRequest? req = null, CancellationToken ct = default)
        => PostBytesAsync("api/export", req ?? new ExportRequest(),
                          "application/gzip, application/octet-stream", ct);

    /// <summary>
    /// POST /api/import — import a portable archive into the database.
    /// Requires <c>NOX_ARCHIVE_ENABLED=1</c>.
    /// </summary>
    /// <param name="archive">Raw archive bytes from <see cref="ExportAsync"/>.</param>
    /// <param name="mode">"merge" (default) or "replace".</param>
    /// <param name="dryRun">Preview without mutation.</param>
    /// <param name="force">Required when mode=replace.</param>
    /// <param name="skipEmbeddings">Skip re-importing embeddings.</param>
    public Task<ImportResult?> ImportAsync(byte[] archive, string mode = "merge",
                                            bool dryRun = false, bool force = false,
                                            bool skipEmbeddings = false,
                                            CancellationToken ct = default)
    {
        string qs = Qs(new()
        {
            ["mode"] = mode,
            ["dry_run"] = dryRun.ToString().ToLowerInvariant(),
            ["force"] = force.ToString().ToLowerInvariant(),
            ["skip_embeddings"] = skipEmbeddings.ToString().ToLowerInvariant(),
        });
        return PostRawBytesAsync<ImportResult>("api/import", archive, "application/gzip", qs, ct);
    }

    // ── Viewer / SSE (P5) ─────────────────────────────────────────────────────

    /// <summary>
    /// GET /api/events/stream — open a Server-Sent Events stream.
    /// Requires <c>NOX_VIEWER_ENABLED=1</c>.
    ///
    /// <para>Example:</para>
    /// <code>
    /// await foreach (var evt in client.StreamEventsAsync(ct))
    /// {
    ///     Console.WriteLine($"{evt.Kind} @ {evt.Ts}");
    /// }
    /// </code>
    /// </summary>
    public async IAsyncEnumerable<ViewerEvent> StreamEventsAsync(
        [System.Runtime.CompilerServices.EnumeratorCancellation] CancellationToken ct = default)
    {
        var req = new HttpRequestMessage(HttpMethod.Get, "api/events/stream");
        req.Headers.Add("Accept", "text/event-stream");
        if (_authToken is not null)
            req.Headers.Authorization =
                new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", _authToken);

        var res = await _http.SendAsync(req, HttpCompletionOption.ResponseHeadersRead, ct)
                             .ConfigureAwait(false);
        await EnsureSuccessAsync(res, "api/events/stream").ConfigureAwait(false);

        await using var stream = await res.Content.ReadAsStreamAsync(ct).ConfigureAwait(false);
        await foreach (var evt in SSEReader.ReadAsync(stream, ct).ConfigureAwait(false))
            yield return evt;
    }

    /// <summary>
    /// GET /viewer/{file} — fetch a static viewer UI file.
    /// Requires <c>NOX_VIEWER_ENABLED=1</c>.
    /// </summary>
    public async Task<byte[]> ViewerFileAsync(string file, CancellationToken ct = default)
    {
        var req = new HttpRequestMessage(HttpMethod.Get,
            "viewer/" + Uri.EscapeDataString(file));
        req.Headers.Add("Accept", "*/*");
        var res = await _http.SendAsync(req, ct).ConfigureAwait(false);
        await EnsureSuccessAsync(res, "viewer/" + file).ConfigureAwait(false);
        return await res.Content.ReadAsByteArrayAsync(ct).ConfigureAwait(false);
    }

    // ── Conflict Detection (L2) ───────────────────────────────────────────────

    /// <summary>
    /// GET /api/kg/conflicts — list KG conflicts.
    /// Requires <c>NOX_KG_CONFLICTS_ENABLED=1</c>.
    /// </summary>
    /// <param name="status">Filter by status. Null defaults to "unresolved".</param>
    /// <param name="type">Filter by type: "direct" or "temporal".</param>
    /// <param name="limit">Max results (default 50, max 200).</param>
    public Task<ConflictsResponse?> ListConflictsAsync(string? status = null,
                                                         string? type = null,
                                                         int? limit = null,
                                                         CancellationToken ct = default)
    {
        string qs = Qs(new()
        {
            ["status"] = status,
            ["type"] = type,
            ["limit"] = limit?.ToString(),
        });
        return GetJsonAsync<ConflictsResponse>("api/kg/conflicts" + qs, ct);
    }

    /// <summary>
    /// POST /api/kg/conflicts/scan — trigger a conflict detection scan.
    /// Requires <c>NOX_KG_CONFLICTS_ENABLED=1</c>.
    /// </summary>
    public Task<ScanConflictsResult?> ScanConflictsAsync(ScanConflictsRequest? req = null,
                                                           CancellationToken ct = default)
        => PostJsonAsync<ScanConflictsResult>("api/kg/conflicts/scan", req, ct);

    /// <summary>
    /// GET /api/kg/conflicts/{id} — get conflict detail with full hydration.
    /// Requires <c>NOX_KG_CONFLICTS_ENABLED=1</c>.
    /// </summary>
    public Task<KgConflictDetail?> GetConflictAsync(int id, CancellationToken ct = default)
        => GetJsonAsync<KgConflictDetail>($"api/kg/conflicts/{id}", ct);

    /// <summary>
    /// POST /api/kg/conflicts/{id}/resolve — resolve a conflict.
    /// Requires <c>NOX_KG_CONFLICTS_ENABLED=1</c>.
    /// </summary>
    public Task<ResolveConflictResult?> ResolveConflictAsync(int id,
                                                               ResolveConflictRequest req,
                                                               CancellationToken ct = default)
        => PostJsonAsync<ResolveConflictResult>($"api/kg/conflicts/{id}/resolve", req, ct);

    /// <summary>
    /// POST /api/kg/conflicts/{id}/dismiss — dismiss a conflict as a false positive.
    /// Requires <c>NOX_KG_CONFLICTS_ENABLED=1</c>.
    /// </summary>
    public Task<DismissConflictResult?> DismissConflictAsync(int id, string? note = null,
                                                               CancellationToken ct = default)
        => PostJsonAsync<DismissConflictResult>($"api/kg/conflicts/{id}/dismiss",
                                                note is null ? null : new { note }, ct);

    // ── Confidence / Mark (L3) ────────────────────────────────────────────────

    /// <summary>
    /// POST /api/chunk/{id}/mark — mark a chunk as canonical, refuted, or stale.
    /// Confidence values affect ranking only when <c>NOX_RANKING_CONFIDENCE=active</c>.
    /// </summary>
    /// <param name="chunkId">Chunk id.</param>
    /// <param name="kind">"canonical", "refuted", or "stale".</param>
    /// <param name="notes">Optional notes.</param>
    public Task<MarkResult?> MarkChunkAsync(int chunkId, string kind, string? notes = null,
                                             CancellationToken ct = default)
        => PostJsonAsync<MarkResult>($"api/chunk/{chunkId}/mark",
                                     new MarkRequest(kind, notes), ct);

    /// <summary>
    /// POST /api/chunk/{id}/supersede — mark a chunk as superseded by another.
    /// </summary>
    public Task<MarkResult?> SupersedeChunkAsync(int chunkId, SupersedeRequest req,
                                                   CancellationToken ct = default)
        => PostJsonAsync<MarkResult>($"api/chunk/{chunkId}/supersede", req, ct);

    // ── Hooks (P2) ────────────────────────────────────────────────────────────

    /// <summary>
    /// GET /api/hooks/status — hooks pipeline config and queue depth.
    /// Requires <c>NOX_HOOKS_ENABLED=1</c>.
    /// </summary>
    public Task<HooksStatus?> HookStatusAsync(CancellationToken ct = default)
        => GetJsonAsync<HooksStatus>("api/hooks/status", ct);

    /// <summary>
    /// GET /api/hooks/recent — recent event metadata (no payloads).
    /// Requires <c>NOX_HOOKS_ENABLED=1</c>.
    /// </summary>
    public async Task<List<HookEventMeta>?> HookRecentAsync(int? limit = null,
                                                              CancellationToken ct = default)
    {
        string qs = Qs(new() { ["limit"] = limit?.ToString() });
        var doc = await GetJsonAsync<JsonDocument>("api/hooks/recent" + qs, ct).ConfigureAwait(false);
        if (doc is null) return null;
        return doc.RootElement.TryGetProperty("rows", out var rows)
            ? rows.Deserialize<List<HookEventMeta>>(_json)
            : null;
    }

    /// <summary>
    /// POST /api/hooks/dryrun — dry-run text through the hooks pipeline.
    /// Requires <c>NOX_HOOKS_ENABLED=1</c>.
    /// </summary>
    public Task<HooksDryrunResult?> HookDryrunAsync(HooksDryrunRequest req,
                                                      CancellationToken ct = default)
        => PostJsonAsync<HooksDryrunResult>("api/hooks/dryrun", req, ct);
}
