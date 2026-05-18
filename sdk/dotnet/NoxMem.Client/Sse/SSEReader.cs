using NoxMem.Client.Types;
using System.Runtime.CompilerServices;
using System.Text.Json;

namespace NoxMem.Client.Sse;

/// <summary>
/// Async SSE stream reader. Parses <c>id:</c>, <c>event:</c>, and <c>data:</c>
/// lines and yields <see cref="ViewerEvent"/> objects.
///
/// <para>Usage:</para>
/// <code>
/// await foreach (var evt in SSEReader.ReadAsync(stream, cancellationToken))
/// {
///     Console.WriteLine($"{evt.Kind} @ {evt.Ts}");
/// }
/// </code>
/// </summary>
public static class SSEReader
{
    /// <summary>
    /// Asynchronously yields <see cref="ViewerEvent"/> objects from an SSE stream.
    /// </summary>
    /// <param name="stream">SSE response stream.</param>
    /// <param name="ct">Cancellation token.</param>
    public static async IAsyncEnumerable<ViewerEvent> ReadAsync(
        Stream stream,
        [EnumeratorCancellation] CancellationToken ct = default)
    {
        using var reader = new StreamReader(stream);

        var dataBuilder = new System.Text.StringBuilder();
        string eventKind = string.Empty;

        while (!ct.IsCancellationRequested)
        {
            string? line;
            try
            {
                line = await reader.ReadLineAsync(ct).ConfigureAwait(false);
            }
            catch (OperationCanceledException)
            {
                yield break;
            }
            catch (IOException)
            {
                yield break;
            }

            if (line is null)
                yield break; // EOF

            if (line.StartsWith(':'))
            {
                // SSE comment / heartbeat — ignore
                continue;
            }

            if (line.Length == 0)
            {
                // End of event block
                string data = dataBuilder.ToString().Trim();
                if (data.Length > 0)
                {
                    var evt = ParseEvent(data, eventKind);
                    if (evt is not null) yield return evt;
                }
                dataBuilder.Clear();
                eventKind = string.Empty;
                continue;
            }

            if (line.StartsWith("data:", StringComparison.Ordinal))
            {
                if (dataBuilder.Length > 0) dataBuilder.Append('\n');
                dataBuilder.Append(line.Length > 5 ? line[5..].TrimStart() : string.Empty);
            }
            else if (line.StartsWith("event:", StringComparison.Ordinal))
            {
                eventKind = line[6..].Trim();
            }
        }
    }

    private static ViewerEvent? ParseEvent(string data, string eventKind)
    {
        try
        {
            using var doc = JsonDocument.Parse(data);
            var root = doc.RootElement;

            string kind = eventKind;
            long ts = 0;
            Dictionary<string, object?> payload = new();

            foreach (var prop in root.EnumerateObject())
            {
                switch (prop.Name)
                {
                    case "kind":
                        kind = prop.Value.GetString() ?? eventKind;
                        break;
                    case "ts":
                        ts = prop.Value.ValueKind == JsonValueKind.Number
                            ? prop.Value.GetInt64()
                            : 0;
                        break;
                    default:
                        payload[prop.Name] = prop.Value.ValueKind switch
                        {
                            JsonValueKind.String => prop.Value.GetString(),
                            JsonValueKind.Number => prop.Value.TryGetInt64(out var l) ? (object?)l : prop.Value.GetDouble(),
                            JsonValueKind.True => true,
                            JsonValueKind.False => false,
                            _ => prop.Value.ToString()
                        };
                        break;
                }
            }

            return new ViewerEvent(kind, ts, payload);
        }
        catch (JsonException)
        {
            return null; // skip malformed events
        }
    }
}
