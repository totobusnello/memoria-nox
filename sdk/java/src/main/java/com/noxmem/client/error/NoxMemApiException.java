package com.noxmem.client.error;

/**
 * Thrown when the memoria-nox server returns a non-2xx HTTP status.
 */
public class NoxMemApiException extends RuntimeException {

    private final int statusCode;
    private final String responseBody;
    private final String url;

    public NoxMemApiException(int statusCode, String responseBody, String url) {
        super(String.format("NoxMem API error %d on %s: %s", statusCode, url, responseBody));
        this.statusCode = statusCode;
        this.responseBody = responseBody;
        this.url = url;
    }

    public int getStatusCode() { return statusCode; }
    public String getResponseBody() { return responseBody; }
    public String getUrl() { return url; }

    /** True when the server returned 503 with {"error":"feature disabled",...}. */
    public boolean isFeatureDisabled() {
        return statusCode == 503 && responseBody.contains("\"feature disabled\"");
    }

    /** True when the server returned 401 Unauthorized. */
    public boolean isUnauthorized() { return statusCode == 401; }
}
