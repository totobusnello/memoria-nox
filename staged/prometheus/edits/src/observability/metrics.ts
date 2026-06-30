/**
 * src/observability/metrics.ts — Standard metric catalog (T3).
 *
 * Single source of truth for every metric exported by nox-mem. Each metric is
 * defined as a singleton attached to the default registry on first import.
 *
 * Naming convention (Prometheus + OpenMetrics best practices):
 *   - snake_case
 *   - prefix `nox_` for nox-mem metrics, `process_` / `nodejs_` for runtime
 *   - `_total` suffix for Counter
 *   - `_seconds` / `_bytes` for unit-bearing observations
 *
 * Cardinality budget per metric is conservative — see ./cardinality.ts.
 *
 * NOTE: Importing this module is a side-effect: it registers metrics into the
 * default registry. Tests using a fresh `new MetricsRegistry()` must either
 * import this and use the same singletons, or define their own metrics.
 */
import {
  Counter,
  Gauge,
  Histogram,
  DURATION_BUCKETS_SECONDS,
  RESULT_COUNT_BUCKETS,
} from "./types.js";
import { getDefaultRegistry } from "./registry.js";

const R = getDefaultRegistry();

// ─── Pipeline metrics ────────────────────────────────────────────────────────

export const chunksTotal = R.register(
  new Counter({
    name: "nox_chunks_total",
    help: "Total chunks ingested (cumulative).",
    labelKeys: ["provenance_kind"],
  }),
);

export const embeddingsTotal = R.register(
  new Counter({
    name: "nox_embeddings_total",
    help: "Total embeddings created (cumulative).",
    labelKeys: ["provider", "outcome"],
  }),
);

export const kgEntitiesTotal = R.register(
  new Counter({
    name: "nox_kg_entities_total",
    help: "Total KG entities created (cumulative).",
    labelKeys: ["type"],
  }),
);

export const kgRelationsTotal = R.register(
  new Counter({
    name: "nox_kg_relations_total",
    help: "Total KG relations created (cumulative).",
    labelKeys: ["predicate"],
  }),
);

// ─── Search metrics ──────────────────────────────────────────────────────────

export const searchRequestsTotal = R.register(
  new Counter({
    name: "nox_search_requests_total",
    help: "Total search requests handled.",
    labelKeys: ["method", "outcome"],
  }),
);

export const searchDurationSeconds = R.register(
  new Histogram(
    {
      name: "nox_search_duration_seconds",
      help: "End-to-end search latency in seconds.",
      labelKeys: ["method"],
      unit: "seconds",
    },
    DURATION_BUCKETS_SECONDS,
  ),
);

export const searchResultsReturned = R.register(
  new Histogram(
    {
      name: "nox_search_results_returned",
      help: "Distribution of result counts returned per search.",
      labelKeys: ["method"],
    },
    RESULT_COUNT_BUCKETS,
  ),
);

// ─── Answer (P1) metrics ─────────────────────────────────────────────────────

export const answerRequestsTotal = R.register(
  new Counter({
    name: "nox_answer_requests_total",
    help: "Total /api/answer requests by failure reason.",
    labelKeys: ["failure_reason"], // success | no_chunks | llm_failed | hallucination
  }),
);

export const answerDurationSeconds = R.register(
  new Histogram(
    {
      name: "nox_answer_duration_seconds",
      help: "Answer latency by phase (total | retrieve | rerank | synthesize | verify).",
      labelKeys: ["phase"],
      unit: "seconds",
    },
    DURATION_BUCKETS_SECONDS,
  ),
);

export const answerTokensTotal = R.register(
  new Counter({
    name: "nox_answer_tokens_total",
    help: "Total tokens consumed by /api/answer (cumulative).",
    labelKeys: ["direction"], // input | output
  }),
);

// ─── Provider (A3) metrics ───────────────────────────────────────────────────

export const providerCallsTotal = R.register(
  new Counter({
    name: "nox_provider_calls_total",
    help: "Total LLM/embedding provider calls.",
    labelKeys: ["provider", "model", "outcome"], // outcome: success | rate_limit | error | fallback
  }),
);

export const providerDurationSeconds = R.register(
  new Histogram(
    {
      name: "nox_provider_duration_seconds",
      help: "Provider call latency in seconds.",
      labelKeys: ["provider", "kind"], // kind: embedding | llm
      unit: "seconds",
    },
    DURATION_BUCKETS_SECONDS,
  ),
);

export const providerCostUsdTotal = R.register(
  new Counter({
    name: "nox_provider_cost_usd_total",
    help: "Cumulative provider cost in USD.",
    labelKeys: ["provider", "model"],
  }),
);

export const providerTokensTotal = R.register(
  new Counter({
    name: "nox_provider_tokens_total",
    help: "Cumulative provider tokens by direction.",
    labelKeys: ["provider", "direction"], // direction: input | output
  }),
);

// ─── Hooks (P2) metrics ──────────────────────────────────────────────────────

export const hooksEventsTotal = R.register(
  new Counter({
    name: "nox_hooks_events_total",
    help: "Total auto-capture hook events by layer + reason.",
    labelKeys: ["layer", "reason"], // reason: captured | filtered | redacted | error
  }),
);

export const hooksPipelineDurationSeconds = R.register(
  new Histogram(
    {
      name: "nox_hooks_pipeline_duration_seconds",
      help: "Hooks capture pipeline latency in seconds.",
      labelKeys: ["layer"],
      unit: "seconds",
    },
    DURATION_BUCKETS_SECONDS,
  ),
);

// ─── Viewer (P5) metrics ─────────────────────────────────────────────────────

export const viewerConnections = R.register(
  new Gauge({
    name: "nox_viewer_connections",
    help: "Current count of open viewer SSE connections.",
    labelKeys: [],
  }),
);

export const viewerEventsTotal = R.register(
  new Counter({
    name: "nox_viewer_events_total",
    help: "Total viewer events broadcast by type.",
    labelKeys: ["type"],
  }),
);

export const viewerDroppedTotal = R.register(
  new Counter({
    name: "nox_viewer_dropped_total",
    help: "Total viewer events dropped due to backpressure.",
    labelKeys: ["reason"], // reason: slow_consumer | queue_full | client_gone
  }),
);

// ─── System metrics ──────────────────────────────────────────────────────────

export const dbSizeBytes = R.register(
  new Gauge({
    name: "nox_db_size_bytes",
    help: "Size of the SQLite DB file in bytes (main + WAL).",
    labelKeys: ["component"], // component: main | wal | shm
    unit: "bytes",
  }),
);

export const chunksActive = R.register(
  new Gauge({
    name: "nox_chunks_active",
    help: "Active chunks (provenance_kind != stale).",
    labelKeys: [],
  }),
);

export const chunksStale = R.register(
  new Gauge({
    name: "nox_chunks_stale",
    help: "Stale chunks (provenance_kind == stale).",
    labelKeys: [],
  }),
);

export const auditRowsTotal = R.register(
  new Counter({
    name: "nox_audit_rows_total",
    help: "Total audit rows written by table.",
    labelKeys: ["table"], // table: ops_audit | provider_telemetry | search_telemetry | agent_events
  }),
);

// ─── Process / runtime metrics ───────────────────────────────────────────────

export const processCpuUserSecondsTotal = R.register(
  new Counter({
    name: "process_cpu_user_seconds_total",
    help: "Total user CPU time in seconds (cumulative).",
    labelKeys: [],
    unit: "seconds",
  }),
);

export const processCpuSystemSecondsTotal = R.register(
  new Counter({
    name: "process_cpu_system_seconds_total",
    help: "Total system CPU time in seconds (cumulative).",
    labelKeys: [],
    unit: "seconds",
  }),
);

export const processResidentMemoryBytes = R.register(
  new Gauge({
    name: "process_resident_memory_bytes",
    help: "Resident memory in bytes (RSS).",
    labelKeys: [],
    unit: "bytes",
  }),
);

export const processOpenFds = R.register(
  new Gauge({
    name: "process_open_fds",
    help: "Number of open file descriptors (best-effort).",
    labelKeys: [],
  }),
);

export const nodejsEventloopLagSeconds = R.register(
  new Gauge({
    name: "nodejs_eventloop_lag_seconds",
    help: "Event loop lag in seconds (last sample).",
    labelKeys: [],
    unit: "seconds",
  }),
);

// ─── Catalog summary (for docs / tests / cardinality budgeting) ─────────────

/**
 * Names of every metric registered by this module.
 * Order: same as registration order above.
 */
export const ALL_METRIC_NAMES = Object.freeze([
  "nox_chunks_total",
  "nox_embeddings_total",
  "nox_kg_entities_total",
  "nox_kg_relations_total",
  "nox_search_requests_total",
  "nox_search_duration_seconds",
  "nox_search_results_returned",
  "nox_answer_requests_total",
  "nox_answer_duration_seconds",
  "nox_answer_tokens_total",
  "nox_provider_calls_total",
  "nox_provider_duration_seconds",
  "nox_provider_cost_usd_total",
  "nox_provider_tokens_total",
  "nox_hooks_events_total",
  "nox_hooks_pipeline_duration_seconds",
  "nox_viewer_connections",
  "nox_viewer_events_total",
  "nox_viewer_dropped_total",
  "nox_db_size_bytes",
  "nox_chunks_active",
  "nox_chunks_stale",
  "nox_audit_rows_total",
  "process_cpu_user_seconds_total",
  "process_cpu_system_seconds_total",
  "process_resident_memory_bytes",
  "process_open_fds",
  "nodejs_eventloop_lag_seconds",
] as const);

export type MetricName = (typeof ALL_METRIC_NAMES)[number];
