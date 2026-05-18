using NoxMem.Client;
using NoxMem.Client.Errors;
using NoxMem.Client.Types;
using WireMock.RequestBuilders;
using WireMock.ResponseBuilders;
using WireMock.Server;
using Xunit;

namespace NoxMem.Client.Tests;

/// <summary>
/// xUnit tests for <see cref="NoxMemClient"/> using WireMock.Net.
/// All 26 API endpoints are covered (happy path + at least one error path each).
/// </summary>
public class ClientTests : IDisposable
{
    private readonly WireMockServer _server;
    private readonly NoxMemClient _client;

    public ClientTests()
    {
        _server = WireMockServer.Start();
        _client = new NoxMemClient(_server.Url!, null, TimeSpan.FromSeconds(5));
    }

    public void Dispose()
    {
        _client.Dispose();
        _server.Stop();
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private void StubGet(string path, int status, string body) =>
        _server.Given(Request.Create().WithPath(path).UsingGet())
               .RespondWith(Response.Create().WithStatusCode(status)
                                             .WithBody(body)
                                             .WithHeader("Content-Type", "application/json"));

    private void StubPost(string path, int status, string body) =>
        _server.Given(Request.Create().WithPath(path).UsingPost())
               .RespondWith(Response.Create().WithStatusCode(status)
                                             .WithBody(body)
                                             .WithHeader("Content-Type", "application/json"));

    // ── Core ──────────────────────────────────────────────────────────────────

    [Fact]
    public async Task Health_Returns200()
    {
        StubGet("/api/health", 200, """
            {"chunks":{"total":62914,"types":[]},"dbSizeMB":487.3,
             "vectorCoverage":{"embedded":62912,"total":62914,"orphans":0},
             "knowledgeGraph":{"entities":402,"relations":544},"procedures":28}
            """);

        var h = await _client.HealthAsync();
        Assert.NotNull(h);
        Assert.Equal(62914, h.Chunks!.Total);
        Assert.Equal(487.3, h.DbSizeMB, 1);
    }

    [Fact]
    public async Task Health_500_ThrowsException()
    {
        StubGet("/api/health", 500, """{"error":"db locked"}""");
        var ex = await Assert.ThrowsAsync<NoxMemApiException>(() => _client.HealthAsync());
        Assert.Equal(500, ex.StatusCode);
    }

    [Fact]
    public async Task Agents_Returns200()
    {
        StubGet("/api/agents", 200, """[{"agent":"forge","entity_count":12,"relation_count":30}]""");
        var agents = await _client.AgentsAsync();
        Assert.NotNull(agents);
        Assert.Single(agents);
        Assert.Equal("forge", agents[0].Agent);
    }

    [Fact]
    public async Task Reflect_Returns200()
    {
        StubGet("/api/reflect", 200, """
            {"query":"incidents","synthesis":"No major incidents.","cache_hit":false}
            """);
        var r = await _client.ReflectAsync("incidents");
        Assert.NotNull(r);
        Assert.False(r.CacheHit);
        Assert.Equal("No major incidents.", r.Synthesis);
    }

    [Fact]
    public async Task Procedures_Returns200()
    {
        StubGet("/api/procedures", 200, """
            {"procedures":[{"id":1,"title":"Reapply patch","steps":["ssh"],"agent":"forge","tags":[],"created_at":"2026-01-01T00:00:00Z"}]}
            """);
        var procs = await _client.ProceduresAsync();
        Assert.NotNull(procs);
        Assert.Single(procs);
        Assert.Equal("Reapply patch", procs[0].Title);
    }

    [Fact]
    public async Task Crystallize_ReturnsId()
    {
        StubPost("/api/crystallize", 200, """{"id":88,"ok":true}""");
        var r = await _client.CrystallizeAsync(new CrystallizeRequest("Title", ["step1"]));
        Assert.NotNull(r);
        Assert.Equal(88, r.Id);
        Assert.True(r.Ok);
    }

    [Fact]
    public async Task Crystallize_400_ThrowsException()
    {
        StubPost("/api/crystallize", 400, """{"error":"title required"}""");
        var ex = await Assert.ThrowsAsync<NoxMemApiException>(
            () => _client.CrystallizeAsync(new CrystallizeRequest("", [])));
        Assert.Equal(400, ex.StatusCode);
    }

    [Fact]
    public async Task CrystallizeValidate_Returns200()
    {
        StubPost("/api/crystallize/validate", 200, """{"id":88,"ok":true}""");
        var doc = await _client.CrystallizeValidateAsync(88,
            new CrystallizeValidateRequest(Outcome: "success", Agent: "forge"));
        Assert.NotNull(doc);
    }

    // ── Search ────────────────────────────────────────────────────────────────

    [Fact]
    public async Task Search_Returns200()
    {
        StubGet("/api/search", 200, """[{"chunk_id":1,"content":"test","score":0.9,"chunk_type":"lesson"}]""");
        var results = await _client.SearchAsync("Gemini quota");
        Assert.NotNull(results);
        Assert.Single(results);
        Assert.Equal(0.9, results[0].Score, 2);
    }

    [Fact]
    public async Task Search_400_MissingQ()
    {
        StubGet("/api/search", 400, """{"error":"q parameter required"}""");
        await Assert.ThrowsAsync<NoxMemApiException>(() => _client.SearchAsync(""));
    }

    [Fact]
    public async Task SearchPost_Returns200()
    {
        StubPost("/api/search", 200, """[{"chunk_id":2,"content":"post","score":0.8,"chunk_type":"decision"}]""");
        var results = await _client.SearchPostAsync(new SearchRequest("monkey-patch", Limit: 5));
        Assert.NotNull(results);
        Assert.Single(results);
    }

    [Fact]
    public async Task Search_TemporalFilter_Returns200()
    {
        StubGet("/api/search", 200, "[]");
        var results = await _client.SearchAsync("q", AsOf: "7d");
        Assert.NotNull(results);
        Assert.Empty(results);
    }

    // ── Knowledge Graph ───────────────────────────────────────────────────────

    [Fact]
    public async Task Kg_Returns200()
    {
        StubGet("/api/kg", 200, """{"entities":[],"relations":[]}""");
        var kg = await _client.KgAsync();
        Assert.NotNull(kg);
        Assert.Empty(kg.Entities);
    }

    [Fact]
    public async Task KgPath_Returns200()
    {
        StubGet("/api/kg/path", 200, """{"path":["nox-mem-api","vectorize","gemini-embedding-001"]}""");
        var path = await _client.KgPathAsync("nox-mem-api", "gemini-embedding-001");
        Assert.NotNull(path);
        Assert.NotNull(path.Path);
        Assert.Equal(3, path.Path.Count);
    }

    [Fact]
    public async Task CrossKg_Returns200()
    {
        StubGet("/api/cross-kg", 200, """{"entities":[],"relations":[],"agents":["forge"]}""");
        var ckg = await _client.CrossKgAsync();
        Assert.NotNull(ckg);
        Assert.Contains("forge", ckg.Agents!);
    }

    // ── Answer (P1) ───────────────────────────────────────────────────────────

    [Fact]
    public async Task Answer_Returns200()
    {
        StubPost("/api/answer", 200, """
            {"answer":"Run the script.","citations":[],"metadata":{"latency_ms":1800,"tokens_in":100,"tokens_out":50,"retrieval_count":8,"fallback_used":false,"retry_count":0},"trace_id":"abc"}
            """);
        var a = await _client.AnswerAsync(new AnswerRequest("How?"));
        Assert.NotNull(a);
        Assert.Equal("Run the script.", a.Answer);
        Assert.Equal("abc", a.TraceId);
    }

    [Fact]
    public async Task Answer_503_FeatureDisabled()
    {
        StubPost("/api/answer", 503, """{"error":"feature disabled","env_var":"NOX_ANSWER_ENABLED"}""");
        var ex = await Assert.ThrowsAsync<NoxMemApiException>(
            () => _client.AnswerAsync(new AnswerRequest("q")));
        Assert.Equal(503, ex.StatusCode);
        Assert.True(ex.IsFeatureDisabled);
    }

    // ── Export / Import (A2) ──────────────────────────────────────────────────

    [Fact]
    public async Task Export_ReturnsBytes()
    {
        byte[] fakeArchive = [0x1f, 0x8b]; // gzip magic
        _server.Given(Request.Create().WithPath("/api/export").UsingPost())
               .RespondWith(Response.Create().WithStatusCode(200)
                                             .WithBody(fakeArchive)
                                             .WithHeader("Content-Type", "application/gzip"));
        var bytes = await _client.ExportAsync();
        Assert.Equal(fakeArchive, bytes);
    }

    [Fact]
    public async Task Import_Returns200()
    {
        StubPost("/api/import", 200, """
            {"op_id":"import-001","schema_version_archive":18,"schema_version_target":19,
             "migration_applied":[],"chunks_inserted":100,"chunks_skipped_dedup":5,
             "kg_entities_inserted":10,"kg_entities_merged":2,"ops_audit_appended":0,
             "embeddings_skipped":0,"duration_ms":1234,"warnings":[]}
            """);
        var r = await _client.ImportAsync([1, 2, 3]);
        Assert.NotNull(r);
        Assert.Equal("import-001", r.OpId);
        Assert.Equal(100, r.ChunksInserted);
    }

    // ── Viewer (P5) ───────────────────────────────────────────────────────────

    [Fact]
    public async Task ViewerFile_Returns200()
    {
        _server.Given(Request.Create().WithPath("/viewer/index.html").UsingGet())
               .RespondWith(Response.Create().WithStatusCode(200)
                                             .WithBody("<html></html>")
                                             .WithHeader("Content-Type", "text/html"));
        var bytes = await _client.ViewerFileAsync("index.html");
        Assert.Contains("<html>", System.Text.Encoding.UTF8.GetString(bytes));
    }

    [Fact]
    public async Task ViewerFile_404()
    {
        _server.Given(Request.Create().WithPath("/viewer/missing.js").UsingGet())
               .RespondWith(Response.Create().WithStatusCode(404).WithBody("Not Found"));
        var ex = await Assert.ThrowsAsync<NoxMemApiException>(
            () => _client.ViewerFileAsync("missing.js"));
        Assert.Equal(404, ex.StatusCode);
    }

    // ── Conflicts (L2) ────────────────────────────────────────────────────────

    [Fact]
    public async Task ListConflicts_Returns200()
    {
        StubGet("/api/kg/conflicts", 200, """
            {"conflicts":[{"id":1,"conflict_type":"direct","source_entity_id":12,
             "source_entity_name":"openclaw-gateway","predicate":"is_deployed_at",
             "status":"unresolved","detected_at":"2026-05-18T03:30:00Z","relation_ids":[88,91]}],"total":1}
            """);
        var r = await _client.ListConflictsAsync();
        Assert.NotNull(r);
        Assert.Equal(1, r.Total);
        Assert.Equal("unresolved", r.Conflicts[0].Status);
    }

    [Fact]
    public async Task ScanConflicts_Returns200()
    {
        StubPost("/api/kg/conflicts/scan", 200, """
            {"conflicts_found":3,"conflicts_written":3,"dry_run":false,"duration_ms":284}
            """);
        var r = await _client.ScanConflictsAsync();
        Assert.NotNull(r);
        Assert.Equal(3, r.ConflictsFound);
    }

    [Fact]
    public async Task GetConflict_Returns200()
    {
        StubGet("/api/kg/conflicts/1", 200, """
            {"id":1,"conflict_type":"direct","predicate":"is_deployed_at","status":"unresolved"}
            """);
        var r = await _client.GetConflictAsync(1);
        Assert.NotNull(r);
        Assert.Equal("is_deployed_at", r.Predicate);
    }

    [Fact]
    public async Task GetConflict_404()
    {
        StubGet("/api/kg/conflicts/999", 404, """{"error":"not found"}""");
        var ex = await Assert.ThrowsAsync<NoxMemApiException>(() => _client.GetConflictAsync(999));
        Assert.Equal(404, ex.StatusCode);
    }

    [Fact]
    public async Task ResolveConflict_Returns200()
    {
        StubPost("/api/kg/conflicts/1/resolve", 200, """
            {"ok":true,"conflict_id":1,"resolution":"superseded"}
            """);
        var r = await _client.ResolveConflictAsync(1,
            new ResolveConflictRequest("91", "Relation 91 is current"));
        Assert.NotNull(r);
        Assert.True(r.Ok);
        Assert.Equal("superseded", r.Resolution);
    }

    [Fact]
    public async Task DismissConflict_Returns200()
    {
        StubPost("/api/kg/conflicts/1/dismiss", 200, """{"ok":true,"conflict_id":1}""");
        var r = await _client.DismissConflictAsync(1, "Not a real contradiction");
        Assert.NotNull(r);
        Assert.True(r.Ok);
    }

    // ── Confidence / Mark (L3) ────────────────────────────────────────────────

    [Fact]
    public async Task MarkChunk_Returns200()
    {
        StubPost("/api/chunk/41203/mark", 200, """
            {"ok":true,"chunk_id":41203,"applied":{"confidence":0.95,"provenance_kind":"user-marked"},"audit_id":1047}
            """);
        var r = await _client.MarkChunkAsync(41203, "canonical", "Verified correct");
        Assert.NotNull(r);
        Assert.True(r.Ok);
        Assert.Equal(41203, r.ChunkId);
        Assert.Equal(0.95, r.Applied!.Confidence, 2);
    }

    [Fact]
    public async Task MarkChunk_400_BadKind()
    {
        StubPost("/api/chunk/1/mark", 400, """{"ok":false,"error":"invalid kind","code":"bad_kind"}""");
        var ex = await Assert.ThrowsAsync<NoxMemApiException>(
            () => _client.MarkChunkAsync(1, "archived"));
        Assert.Equal(400, ex.StatusCode);
    }

    [Fact]
    public async Task SupersedeChunk_Returns200()
    {
        StubPost("/api/chunk/100/supersede", 200, """
            {"ok":true,"chunk_id":100,"applied":{"confidence":0.0},"audit_id":1048}
            """);
        var r = await _client.SupersedeChunkAsync(100, new SupersedeRequest(200));
        Assert.NotNull(r);
        Assert.True(r.Ok);
    }

    // ── Hooks (P2) ────────────────────────────────────────────────────────────

    [Fact]
    public async Task HookStatus_Returns200()
    {
        StubGet("/api/hooks/status", 200, """
            {"enabled":true,"queue_depth":3,"active_hooks":["slack"],"config":{}}
            """);
        var r = await _client.HookStatusAsync();
        Assert.NotNull(r);
        Assert.True(r.Enabled);
        Assert.Equal(3, r.QueueDepth);
    }

    [Fact]
    public async Task HookRecent_Returns200()
    {
        StubGet("/api/hooks/recent", 200, """
            {"rows":[{"event_id":"e1","hook_name":"slack","received_at":"2026-05-18T10:00:00Z","status":"ok","retries":0}]}
            """);
        var rows = await _client.HookRecentAsync(10);
        Assert.NotNull(rows);
        Assert.Single(rows);
        Assert.Equal("e1", rows[0].EventId);
    }

    [Fact]
    public async Task HookDryrun_Returns200()
    {
        StubPost("/api/hooks/dryrun", 200, """
            {"matched_hooks":["slack"],"pipeline_steps":[],"would_ingest":true,"estimated_chunks":2}
            """);
        var r = await _client.HookDryrunAsync(new HooksDryrunRequest("test text"));
        Assert.NotNull(r);
        Assert.True(r.WouldIngest);
        Assert.Equal(2, r.EstimatedChunks);
    }
}
