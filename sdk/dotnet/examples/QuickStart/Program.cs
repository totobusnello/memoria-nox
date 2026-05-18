using NoxMem.Client;
using NoxMem.Client.Errors;
using NoxMem.Client.Types;

// Quick-start example for the NoxMem.Client .NET SDK
// Run: dotnet run (from sdk/dotnet/examples/QuickStart/)
//
// Environment variables:
//   NOX_API_URL   - base URL (default http://127.0.0.1:18802)
//   NOX_API_TOKEN - Bearer token (only if server has NOX_API_TOKEN set)

var baseUrl = Environment.GetEnvironmentVariable("NOX_API_URL") ?? "http://127.0.0.1:18802";
var token   = Environment.GetEnvironmentVariable("NOX_API_TOKEN");

using var client = new NoxMemClient(baseUrl, token);

// ── 1. Health check ──────────────────────────────────────────────────────────
var health = await client.HealthAsync();
Console.WriteLine($"Chunks: {health?.Chunks?.Total} | DB: {health?.DbSizeMB:F1} MB");

// ── 2. Hybrid search ─────────────────────────────────────────────────────────
var results = await client.SearchAsync("Gemini quota exceeded nightly cron", limit: 5);
Console.WriteLine($"Search returned {results?.Count ?? 0} results");
if (results is not null)
{
    foreach (var r in results)
        Console.WriteLine($"  [{r.Score:F3}] {r.Content[..Math.Min(80, r.Content.Length)]}");
}

// ── 3. Reflect ───────────────────────────────────────────────────────────────
var reflect = await client.ReflectAsync("what are my recurring production incidents?");
Console.WriteLine($"Reflection (cache_hit={reflect?.CacheHit}): {reflect?.Synthesis}");

// ── 4. Crystallize a procedure ───────────────────────────────────────────────
var cr = await client.CrystallizeAsync(new CrystallizeRequest(
    "Example procedure via .NET SDK",
    ["Step 1: verify env", "Step 2: run script"],
    Agent: "forge",
    Tags: ["example"]
));
Console.WriteLine($"Crystallized id={cr?.Id} ok={cr?.Ok}");

// ── 5. Mark a chunk (L3) ────────────────────────────────────────────────────
// var mark = await client.MarkChunkAsync(41203, "canonical", "Verified correct");
// Console.WriteLine($"Mark: ok={mark?.Ok}");

// ── 6. Answer (P1) — requires NOX_ANSWER_ENABLED=1 ──────────────────────────
try
{
    var answer = await client.AnswerAsync(new AnswerRequest(
        "How do I reapply the monkey-patch after upgrading OpenClaw?",
        TopK: 8
    ));
    Console.WriteLine($"Answer: {answer?.Answer?[..Math.Min(120, answer.Answer.Length)]}...");
}
catch (NoxMemApiException ex) when (ex.IsFeatureDisabled)
{
    Console.WriteLine("Answer feature not enabled (NOX_ANSWER_ENABLED=1 required)");
}

// ── 7. SSE stream (P5) — requires NOX_VIEWER_ENABLED=1 ──────────────────────
// var cts = new CancellationTokenSource(TimeSpan.FromSeconds(5));
// try
// {
//     int count = 0;
//     await foreach (var evt in client.StreamEventsAsync(cts.Token))
//     {
//         Console.WriteLine($"Event: {evt.Kind} @ {evt.Ts}");
//         if (++count >= 3) break;
//     }
// }
// catch (NoxMemApiException ex) when (ex.IsFeatureDisabled)
// {
//     Console.WriteLine("Viewer not enabled (NOX_VIEWER_ENABLED=1 required)");
// }
