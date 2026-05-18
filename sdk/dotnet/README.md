# NoxMem.Client — .NET SDK

C# / .NET 8.0 client for the [memoria-nox](https://github.com/totobusnello/memoria-nox) HTTP API.

Covers all 26 OpenAPI endpoints (wave-d). Uses `System.Net.Http.HttpClient` and `System.Text.Json` — both ship with .NET 8, no extra NuGet packages required.

## Requirements

- .NET 8.0 LTS

## Quick start

```csharp
using var client = new NoxMemClient();

// Health check
var health = await client.HealthAsync();
Console.WriteLine($"Chunks: {health?.Chunks?.Total}");

// Hybrid search
var results = await client.SearchAsync("Gemini quota exceeded", limit: 10);
foreach (var r in results ?? [])
    Console.WriteLine($"[{r.Score:F3}] {r.Content}");

// RAG answer (requires NOX_ANSWER_ENABLED=1)
var answer = await client.AnswerAsync(new AnswerRequest(
    "How do I reapply the monkey-patch?",
    TopK: 8
));
Console.WriteLine(answer?.Answer);
```

## Configuration

```csharp
// Default: http://127.0.0.1:18802, no auth, 30 s timeout
using var client = new NoxMemClient();

// Custom URL + auth token + timeout
using var client = new NoxMemClient(
    baseUrl: Environment.GetEnvironmentVariable("NOX_API_URL")!,
    authToken: Environment.GetEnvironmentVariable("NOX_API_TOKEN"),
    timeout: TimeSpan.FromSeconds(60)
);
```

## Endpoints

All 26 endpoints from `openapi.yaml` 1.0.0-wave-d:

| Group | Method | Path | C# method |
|-------|--------|------|-----------|
| Core | GET | `/api/health` | `HealthAsync()` |
| Core | GET | `/api/agents` | `AgentsAsync()` |
| Core | GET | `/api/reflect` | `ReflectAsync(q, nocache)` |
| Core | GET | `/api/procedures` | `ProceduresAsync()` |
| Core | POST | `/api/crystallize` | `CrystallizeAsync(req)` |
| Core | POST | `/api/crystallize/validate` | `CrystallizeValidateAsync(id, req)` |
| Search | GET | `/api/search` | `SearchAsync(q, limit, asOf, changedSince)` |
| Search | POST | `/api/search` | `SearchPostAsync(req)` |
| KG | GET | `/api/kg` | `KgAsync()` |
| KG | GET | `/api/kg/path` | `KgPathAsync(from, to)` |
| KG | GET | `/api/cross-kg` | `CrossKgAsync()` |
| Answer (P1) | POST | `/api/answer` | `AnswerAsync(req)` |
| Export/Import (A2) | POST | `/api/export` | `ExportAsync(req?)` |
| Export/Import (A2) | POST | `/api/import` | `ImportAsync(bytes, mode, ...)` |
| Viewer (P5) | GET | `/api/events/stream` | `StreamEventsAsync()` → `IAsyncEnumerable<ViewerEvent>` |
| Viewer (P5) | GET | `/viewer/{file}` | `ViewerFileAsync(file)` |
| Conflicts (L2) | GET | `/api/kg/conflicts` | `ListConflictsAsync(status, type, limit)` |
| Conflicts (L2) | POST | `/api/kg/conflicts/scan` | `ScanConflictsAsync(req?)` |
| Conflicts (L2) | GET | `/api/kg/conflicts/{id}` | `GetConflictAsync(id)` |
| Conflicts (L2) | POST | `/api/kg/conflicts/{id}/resolve` | `ResolveConflictAsync(id, req)` |
| Conflicts (L2) | POST | `/api/kg/conflicts/{id}/dismiss` | `DismissConflictAsync(id, note?)` |
| Confidence (L3) | POST | `/api/chunk/{id}/mark` | `MarkChunkAsync(chunkId, kind, notes?)` |
| Confidence (L3) | POST | `/api/chunk/{id}/supersede` | `SupersedeChunkAsync(chunkId, req)` |
| Hooks (P2) | GET | `/api/hooks/status` | `HookStatusAsync()` |
| Hooks (P2) | GET | `/api/hooks/recent` | `HookRecentAsync(limit?)` |
| Hooks (P2) | POST | `/api/hooks/dryrun` | `HookDryrunAsync(req)` |

## Error handling

```csharp
try
{
    var answer = await client.AnswerAsync(new AnswerRequest("q"));
}
catch (NoxMemApiException ex) when (ex.IsFeatureDisabled)
{
    // 503 {"error":"feature disabled","env_var":"NOX_ANSWER_ENABLED"}
}
catch (NoxMemApiException ex) when (ex.IsUnauthorized)
{
    // 401 — check NOX_API_TOKEN
}
catch (NoxMemApiException ex)
{
    Console.Error.WriteLine($"Status {ex.StatusCode}: {ex.ResponseBody}");
}
```

## SSE streaming

```csharp
var cts = new CancellationTokenSource(TimeSpan.FromMinutes(5));
await foreach (var evt in client.StreamEventsAsync(cts.Token))
{
    Console.WriteLine($"{evt.Kind} @ {evt.Ts}");
    foreach (var (k, v) in evt.Payload ?? [])
        Console.WriteLine($"  {k}={v}");
}
```

## Build and test

```bash
# Build
dotnet build

# Test (from sdk/dotnet/)
dotnet test

# Run example
cd examples/QuickStart
dotnet run
```

## Design notes

- **No extra NuGet packages**: `System.Net.Http.HttpClient` + `System.Text.Json` (BCL)
- **Records everywhere**: all types use C# `record` for immutability
- **Nullable reference types**: enabled project-wide (`<Nullable>enable</Nullable>`)
- **async/await throughout**: all methods are `Task<T>` or `IAsyncEnumerable<T>`
- **SSEReader**: `IAsyncEnumerable<ViewerEvent>` parser with `System.Text.Json`, skips heartbeat comments
- **CancellationToken**: all methods accept an optional CT (last parameter, default)
