# noxmem-client — Java SDK

Java 17 client for the [memoria-nox](https://github.com/totobusnello/memoria-nox) HTTP API.

Covers all 26 OpenAPI endpoints (wave-d). Zero external runtime dependencies — uses `java.net.http.HttpClient` from the JDK.

## Requirements

- Java 17+
- Maven 3.8+

## Quick start

```java
try (NoxMemClient client = new NoxMemClient()) {
    // Health check
    HealthResponse health = client.health();
    System.out.printf("Chunks: %d%n", health.chunks().total());

    // Hybrid search
    String results = client.searchRaw("Gemini quota exceeded", 10, null, null);

    // RAG answer (requires NOX_ANSWER_ENABLED=1)
    String answer = client.answerRaw(new AnswerRequest(
        "How do I reapply the monkey-patch?",
        8, null, null, null, null, null, null
    ));
}
```

## Configuration

```java
// Default: http://127.0.0.1:18802, no auth, 30s timeout
NoxMemClient client = new NoxMemClient();

// Custom URL + auth token
NoxMemClient client = new NoxMemClient(
    System.getenv("NOX_API_URL"),
    System.getenv("NOX_API_TOKEN"),
    Duration.ofSeconds(60)
);
```

## Endpoints

All 26 endpoints from `openapi.yaml` 1.0.0-wave-d:

| Group | Method | Path | Java method |
|-------|--------|------|-------------|
| Core | GET | `/api/health` | `health()` |
| Core | GET | `/api/agents` | `agentsRaw()` |
| Core | GET | `/api/reflect` | `reflect(q, nocache)` |
| Core | GET | `/api/procedures` | `proceduresRaw()` |
| Core | POST | `/api/crystallize` | `crystallize(req)` |
| Core | POST | `/api/crystallize/validate` | `crystallizeValidate(id, req)` |
| Search | GET | `/api/search` | `searchRaw(q, limit, asOf, changedSince)` |
| Search | POST | `/api/search` | `searchPostRaw(req)` |
| KG | GET | `/api/kg` | `kgRaw()` |
| KG | GET | `/api/kg/path` | `kgPathRaw(from, to)` |
| KG | GET | `/api/cross-kg` | `crossKgRaw()` |
| Answer (P1) | POST | `/api/answer` | `answerRaw(req)` |
| Export/Import (A2) | POST | `/api/export` | `export(req)` |
| Export/Import (A2) | POST | `/api/import` | `importArchive(bytes, mode, dryRun, force, skipEmbeddings)` |
| Viewer (P5) | GET | `/api/events/stream` | `streamEvents()` → `SSEReader` |
| Viewer (P5) | GET | `/viewer/{file}` | `viewerFile(file)` |
| Conflicts (L2) | GET | `/api/kg/conflicts` | `listConflictsRaw(status, type, limit)` |
| Conflicts (L2) | POST | `/api/kg/conflicts/scan` | `scanConflicts(req)` |
| Conflicts (L2) | GET | `/api/kg/conflicts/{id}` | `getConflictRaw(id)` |
| Conflicts (L2) | POST | `/api/kg/conflicts/{id}/resolve` | `resolveConflict(id, req)` |
| Conflicts (L2) | POST | `/api/kg/conflicts/{id}/dismiss` | `dismissConflict(id, note)` |
| Confidence (L3) | POST | `/api/chunk/{id}/mark` | `markChunk(chunkId, kind, notes)` |
| Confidence (L3) | POST | `/api/chunk/{id}/supersede` | `supersedeChunk(chunkId, req)` |
| Hooks (P2) | GET | `/api/hooks/status` | `hookStatusRaw()` |
| Hooks (P2) | GET | `/api/hooks/recent` | `hookRecentRaw(limit)` |
| Hooks (P2) | POST | `/api/hooks/dryrun` | `hookDryrunRaw(req)` |

## Error handling

```java
try {
    String raw = client.answerRaw(req);
} catch (NoxMemApiException e) {
    if (e.isFeatureDisabled()) {
        // Server returned 503 with {"error":"feature disabled","env_var":"NOX_ANSWER_ENABLED"}
    } else if (e.isUnauthorized()) {
        // 401 — check NOX_API_TOKEN
    } else {
        System.err.println("Status " + e.getStatusCode() + ": " + e.getResponseBody());
    }
}
```

## SSE streaming

```java
try (SSEReader events = client.streamEvents()) {
    for (ViewerEvent event : events) {
        System.out.println(event.kind() + " @ " + event.ts());
        System.out.println(event.payload());
    }
}
```

## Build

```bash
mvn compile
mvn test
mvn package
```

## Design notes

- **Zero runtime deps**: `java.net.http.HttpClient` (JDK 11+, stable in 17)
- **Records**: all types use Java 17 `record` for immutability
- **Sealed exceptions**: `NoxMemApiException` carries `statusCode`, `responseBody`, `url`
- **Raw JSON returns**: most endpoints return raw JSON strings; plug in Jackson/Gson in your app layer if needed
- **SSEReader**: blocking iterator over SSE stream, handles heartbeat comments, auto-closes with try-with-resources
