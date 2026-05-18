package com.noxmem.client.sse;

import com.noxmem.client.types.Types.ViewerEvent;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;
import java.util.NoSuchElementException;

/**
 * Blocking SSE stream reader. Parses {@code id:}, {@code event:}, and
 * {@code data:} lines, assembles events, and exposes them via
 * {@link Iterator<ViewerEvent>}.
 *
 * <p>Usage:
 * <pre>{@code
 * try (SSEReader reader = new SSEReader(inputStream)) {
 *     for (ViewerEvent event : reader) {
 *         System.out.println(event.kind() + " @ " + event.ts());
 *     }
 * }
 * }</pre>
 *
 * <p>The caller is responsible for closing the underlying {@link InputStream}
 * or using try-with-resources on the reader itself.
 */
public class SSEReader implements Iterable<ViewerEvent>, AutoCloseable {

    private final BufferedReader reader;
    private ViewerEvent next;
    private boolean done;

    public SSEReader(InputStream in) {
        this.reader = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8));
    }

    @Override
    public Iterator<ViewerEvent> iterator() {
        return new Iterator<>() {
            @Override
            public boolean hasNext() {
                if (done) return false;
                if (next != null) return true;
                next = readNextEvent();
                return next != null;
            }

            @Override
            public ViewerEvent next() {
                if (!hasNext()) throw new NoSuchElementException();
                ViewerEvent e = next;
                next = null;
                return e;
            }
        };
    }

    /**
     * Reads lines until a complete SSE event block is assembled. Returns null
     * on EOF or IO error.
     */
    private ViewerEvent readNextEvent() {
        StringBuilder dataBuilder = new StringBuilder();
        String eventKind = "";
        String eventId = "";

        try {
            String line;
            while ((line = reader.readLine()) != null) {
                if (line.startsWith(":")) {
                    // SSE comment (heartbeat) — ignore
                    continue;
                }
                if (line.isEmpty()) {
                    // End of event block
                    String data = dataBuilder.toString().trim();
                    if (!data.isEmpty()) {
                        return parseEvent(data, eventKind, eventId);
                    }
                    // reset accumulators for next event
                    dataBuilder = new StringBuilder();
                    eventKind = "";
                    eventId = "";
                    continue;
                }
                if (line.startsWith("data:")) {
                    if (dataBuilder.length() > 0) dataBuilder.append('\n');
                    dataBuilder.append(line.substring(5).stripLeading());
                } else if (line.startsWith("event:")) {
                    eventKind = line.substring(6).strip();
                } else if (line.startsWith("id:")) {
                    eventId = line.substring(3).strip();
                }
            }
        } catch (IOException e) {
            // Connection closed
        }
        done = true;
        return null;
    }

    /**
     * Minimal JSON parser for SSE data payloads. Extracts {@code kind} and
     * {@code ts} fields from a flat JSON object. Remaining fields are
     * aggregated into {@code payload}.
     *
     * <p>For production use replace with a full JSON library (jackson, gson)
     * in a project that allows runtime dependencies.
     */
    private static ViewerEvent parseEvent(String data, String eventKind, String eventId) {
        // Lightweight extraction of top-level string/number fields
        long ts = 0;
        String kind = eventKind;
        Map<String, Object> payload = new HashMap<>();

        // Strip outer braces
        String inner = data.trim();
        if (inner.startsWith("{")) inner = inner.substring(1);
        if (inner.endsWith("}")) inner = inner.substring(0, inner.length() - 1);

        // Parse key:value pairs (handles strings and numbers, not nested objects)
        int i = 0;
        while (i < inner.length()) {
            // Skip whitespace / commas
            while (i < inner.length() && (inner.charAt(i) == ',' || Character.isWhitespace(inner.charAt(i)))) i++;
            if (i >= inner.length()) break;

            // Read key
            if (inner.charAt(i) != '"') break;
            int keyEnd = inner.indexOf('"', i + 1);
            if (keyEnd < 0) break;
            String key = inner.substring(i + 1, keyEnd);
            i = keyEnd + 1;

            // Skip colon + whitespace
            while (i < inner.length() && (inner.charAt(i) == ':' || Character.isWhitespace(inner.charAt(i)))) i++;
            if (i >= inner.length()) break;

            // Read value
            Object value;
            if (inner.charAt(i) == '"') {
                int valEnd = inner.indexOf('"', i + 1);
                if (valEnd < 0) break;
                value = inner.substring(i + 1, valEnd);
                i = valEnd + 1;
            } else {
                // number or boolean — read until comma or end
                int valEnd = i;
                while (valEnd < inner.length() && inner.charAt(valEnd) != ',' && inner.charAt(valEnd) != '}') valEnd++;
                String raw = inner.substring(i, valEnd).trim();
                try { value = Long.parseLong(raw); } catch (NumberFormatException e1) {
                    try { value = Double.parseDouble(raw); } catch (NumberFormatException e2) {
                        value = raw;
                    }
                }
                i = valEnd;
            }

            switch (key) {
                case "kind" -> kind = value instanceof String s ? s : String.valueOf(value);
                case "ts"   -> ts = value instanceof Long l ? l : ((Number) value).longValue();
                default     -> payload.put(key, value);
            }
        }

        return new ViewerEvent(kind, ts, Map.copyOf(payload));
    }

    @Override
    public void close() throws IOException {
        reader.close();
    }
}
