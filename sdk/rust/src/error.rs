use serde_json::Value;
use thiserror::Error;

/// Error returned by all client methods.
#[derive(Debug, Error)]
pub enum NoxMemError {
    /// The server returned a non-2xx HTTP status.
    #[error("NoxMem API error {status} on {url}: {message}")]
    Api {
        status: u16,
        url: String,
        message: String,
        body: Value,
    },

    /// Network or transport error from reqwest.
    #[error("HTTP transport error: {0}")]
    Http(#[from] reqwest::Error),

    /// JSON serialisation/deserialisation error.
    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),

    /// SSE stream ended unexpectedly or contained a malformed event.
    #[error("SSE stream error: {0}")]
    Sse(String),
}

impl NoxMemError {
    /// Returns `true` when the server responded with the
    /// `{"error":"feature disabled","env_var":"…"}` sentinel.
    pub fn is_feature_disabled(&self) -> bool {
        if let NoxMemError::Api { body, .. } = self {
            body.get("error")
                .and_then(Value::as_str)
                .map(|s| s == "feature disabled")
                .unwrap_or(false)
        } else {
            false
        }
    }

    /// Returns `true` for 401 Unauthorized responses.
    pub fn is_unauthorized(&self) -> bool {
        matches!(self, NoxMemError::Api { status: 401, .. })
    }

    /// Returns the HTTP status code if the error originated from a server response.
    pub fn status(&self) -> Option<u16> {
        if let NoxMemError::Api { status, .. } = self {
            Some(*status)
        } else {
            None
        }
    }
}
