package noxmem

import (
	"bufio"
	"encoding/json"
	"io"
	"strings"
)

// SSEEvent represents a parsed Server-Sent Event from /api/events/stream.
type SSEEvent struct {
	// ID is the sequential integer id from the "id:" SSE field.
	ID string
	// Kind is the event type from the "event:" SSE field
	// (e.g. "chunk.created", "kg.entity.created").
	Kind string
	// Data holds the raw JSON string from the "data:" SSE field.
	Data string
	// Payload is the parsed JSON object. nil for heartbeat comments.
	Payload map[string]interface{}
}

// SSEReader wraps an io.ReadCloser and iterates over SSE events.
// Call Close when done to release the connection.
//
// Usage:
//
//	reader, err := client.StreamEventsRaw(ctx, 0)
//	defer reader.Close()
//	for {
//	    event, err := reader.Next()
//	    if err == io.EOF { break }
//	    if err != nil { ... }
//	    fmt.Println(event.Kind, event.Data)
//	}
type SSEReader struct {
	body    io.ReadCloser
	scanner *bufio.Scanner
	id      string
	kind    string
	data    strings.Builder
}

// newSSEReader wraps the given body in an SSEReader.
func newSSEReader(body io.ReadCloser) *SSEReader {
	return &SSEReader{
		body:    body,
		scanner: bufio.NewScanner(body),
	}
}

// Close closes the underlying HTTP response body.
func (r *SSEReader) Close() error {
	return r.body.Close()
}

// Next returns the next fully-parsed SSE event.
// Returns io.EOF when the stream ends.
// Heartbeat comments (lines starting with ":") are skipped transparently.
func (r *SSEReader) Next() (*SSEEvent, error) {
	for r.scanner.Scan() {
		line := r.scanner.Text()

		if line == "" {
			// Empty line = end of event block
			if r.data.Len() > 0 {
				raw := r.data.String()
				r.data.Reset()
				ev := &SSEEvent{
					ID:   r.id,
					Kind: r.kind,
					Data: raw,
				}
				r.kind = ""
				// Parse payload
				var payload map[string]interface{}
				if err := json.Unmarshal([]byte(raw), &payload); err == nil {
					ev.Payload = payload
				}
				return ev, nil
			}
			continue
		}

		// SSE comment — heartbeat or other server annotation
		if strings.HasPrefix(line, ":") {
			continue
		}

		if after, ok := strings.CutPrefix(line, "data:"); ok {
			r.data.WriteString(strings.TrimPrefix(after, " "))
		} else if after, ok := strings.CutPrefix(line, "event:"); ok {
			r.kind = strings.TrimSpace(after)
		} else if after, ok := strings.CutPrefix(line, "id:"); ok {
			r.id = strings.TrimSpace(after)
		}
		// retry: lines are intentionally ignored (reconnect managed by caller)
	}

	if err := r.scanner.Err(); err != nil {
		return nil, err
	}
	return nil, io.EOF
}
