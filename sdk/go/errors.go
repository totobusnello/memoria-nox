package noxmem

import "fmt"

// APIError is returned when the memoria-nox server responds with a non-2xx
// status code.
type APIError struct {
	StatusCode int
	URL        string
	Body       map[string]interface{}
}

func (e *APIError) Error() string {
	msg := "unknown error"
	if v, ok := e.Body["error"]; ok {
		msg = fmt.Sprintf("%v", v)
	}
	return fmt.Sprintf("NoxMem API error %d on %s: %s", e.StatusCode, e.URL, msg)
}

// IsFeatureDisabled returns true when the server returned the
// {"error":"feature disabled","env_var":"..."} sentinel (HTTP 503).
func (e *APIError) IsFeatureDisabled() bool {
	v, ok := e.Body["error"]
	if !ok {
		return false
	}
	s, ok := v.(string)
	return ok && s == "feature disabled"
}

// IsUnauthorized returns true for HTTP 401 responses.
func (e *APIError) IsUnauthorized() bool {
	return e.StatusCode == 401
}
