/**
 * react-hook.tsx
 *
 * Custom React hooks wrapping the NoxMemClient.
 * Requires: React 18+, @nox-mem/client
 *
 * Usage:
 *   const { results, loading, error } = useNoxSearch("Gemini quota");
 *   const { answer, loading, error } = useNoxAnswer("What is the daily quota?");
 *   const { events } = useNoxStream();
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { NoxMemClient, NoxMemApiError } from "@nox-mem/client";
import type { SearchResult, AnswerSuccess, ViewerEvent } from "@nox-mem/client";

// ─── Singleton client (configure once at app level) ──────────────────────────

let _client: NoxMemClient | null = null;

export function getNoxClient(config?: { baseUrl?: string; authToken?: string }): NoxMemClient {
  if (!_client) {
    _client = new NoxMemClient({
      baseUrl: config?.baseUrl ?? "http://127.0.0.1:18802",
      authToken: config?.authToken ?? import.meta.env?.VITE_NOX_API_TOKEN,
    });
  }
  return _client;
}

// ─── useNoxSearch ─────────────────────────────────────────────────────────────

export interface UseNoxSearchResult {
  results: SearchResult[];
  loading: boolean;
  error: string | null;
  search: (q: string, opts?: { limit?: number }) => void;
}

export function useNoxSearch(initialQuery?: string): UseNoxSearchResult {
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const client = getNoxClient();

  const search = useCallback(
    async (q: string, opts?: { limit?: number }) => {
      if (!q.trim()) return;
      setLoading(true);
      setError(null);
      try {
        const res = await client.search(q, opts);
        setResults(res);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Search failed");
      } finally {
        setLoading(false);
      }
    },
    [client],
  );

  useEffect(() => {
    if (initialQuery) search(initialQuery);
  }, [initialQuery, search]);

  return { results, loading, error, search };
}

// ─── useNoxAnswer ─────────────────────────────────────────────────────────────

export interface UseNoxAnswerResult {
  data: AnswerSuccess | null;
  loading: boolean;
  error: string | null;
  featureDisabled: boolean;
  ask: (question: string, opts?: { top_k?: number }) => void;
}

export function useNoxAnswer(): UseNoxAnswerResult {
  const [data, setData] = useState<AnswerSuccess | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [featureDisabled, setFeatureDisabled] = useState(false);
  const client = getNoxClient();

  const ask = useCallback(
    async (question: string, opts?: { top_k?: number }) => {
      setLoading(true);
      setError(null);
      setFeatureDisabled(false);
      try {
        const res = await client.answer(question, opts);
        setData(res);
      } catch (e) {
        if (e instanceof NoxMemApiError && e.isFeatureDisabled) {
          setFeatureDisabled(true);
        } else {
          setError(e instanceof Error ? e.message : "Answer failed");
        }
      } finally {
        setLoading(false);
      }
    },
    [client],
  );

  return { data, loading, error, featureDisabled, ask };
}

// ─── useNoxStream ─────────────────────────────────────────────────────────────

export interface UseNoxStreamResult {
  events: ViewerEvent[];
  connected: boolean;
  error: string | null;
  featureDisabled: boolean;
  start: () => void;
  stop: () => void;
}

export function useNoxStream(maxEvents = 100): UseNoxStreamResult {
  const [events, setEvents] = useState<ViewerEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [featureDisabled, setFeatureDisabled] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const client = getNoxClient();

  const start = useCallback(() => {
    if (abortRef.current) return; // already running
    const controller = new AbortController();
    abortRef.current = controller;
    setConnected(true);
    setError(null);
    setFeatureDisabled(false);

    (async () => {
      try {
        for await (const event of client.streamEvents(controller.signal)) {
          setEvents((prev) => [event, ...prev].slice(0, maxEvents));
        }
      } catch (e) {
        if ((e as Error).name === "AbortError") {
          // Normal stop
        } else if (e instanceof NoxMemApiError && e.isFeatureDisabled) {
          setFeatureDisabled(true);
        } else {
          setError(e instanceof Error ? e.message : "Stream error");
        }
      } finally {
        setConnected(false);
        abortRef.current = null;
      }
    })();
  }, [client, maxEvents]);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
  }, []);

  // Clean up on unmount
  useEffect(() => () => stop(), [stop]);

  return { events, connected, error, featureDisabled, start, stop };
}

// ─── Example component ────────────────────────────────────────────────────────

export function NoxSearchWidget() {
  const [query, setQuery] = useState("");
  const { results, loading, error, search } = useNoxSearch();

  return (
    <div style={{ fontFamily: "monospace", padding: 16 }}>
      <h2>nox-mem search</h2>
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && search(query)}
        placeholder="Search memory..."
        style={{ width: 400, padding: 8 }}
      />
      <button onClick={() => search(query)} disabled={loading} style={{ marginLeft: 8 }}>
        {loading ? "..." : "Search"}
      </button>
      {error && <p style={{ color: "red" }}>{error}</p>}
      <ul>
        {results.map((r) => (
          <li key={r.chunk_id}>
            <strong>[{r.score?.toFixed(3)}]</strong> {r.content?.slice(0, 120)}
            {r.source_path && <em> — {r.source_path}</em>}
          </li>
        ))}
      </ul>
    </div>
  );
}
