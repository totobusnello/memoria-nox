namespace NoxMem.Client.Errors;

/// <summary>
/// Thrown when the memoria-nox server returns a non-2xx HTTP response.
/// </summary>
public class NoxMemApiException : HttpRequestException
{
    /// <summary>HTTP status code returned by the server.</summary>
    public int StatusCode { get; }

    /// <summary>Raw response body from the server.</summary>
    public string ResponseBody { get; }

    /// <summary>Request URL that triggered the error.</summary>
    public string Url { get; }

    public NoxMemApiException(int statusCode, string responseBody, string url)
        : base($"NoxMem API error {statusCode} on {url}: {responseBody}")
    {
        StatusCode = statusCode;
        ResponseBody = responseBody;
        Url = url;
    }

    /// <summary>
    /// True when the server returned 503 with
    /// <c>{"error":"feature disabled","env_var":"NOX_*"}</c>.
    /// </summary>
    public bool IsFeatureDisabled =>
        StatusCode == 503 && ResponseBody.Contains("\"feature disabled\"");

    /// <summary>True when the server returned 401 Unauthorized.</summary>
    public bool IsUnauthorized => StatusCode == 401;
}
