/**
 * src/observability/index.ts — Public barrel for the observability package.
 *
 * Importers should prefer this entry over deep paths. The recording API
 * (`recordSearch`, `recordAnswer`, …) is the only thing 99% of callers need.
 */
export * from "./types.js";
export {
  MetricsRegistry,
  getDefaultRegistry,
  resetDefaultRegistry,
} from "./registry.js";
export type { RegistrySnapshot, AnyMetric } from "./registry.js";
export {
  ALL_METRIC_NAMES,
  type MetricName,
  chunksTotal,
  embeddingsTotal,
  kgEntitiesTotal,
  kgRelationsTotal,
  searchRequestsTotal,
  searchDurationSeconds,
  searchResultsReturned,
  answerRequestsTotal,
  answerDurationSeconds,
  answerTokensTotal,
  providerCallsTotal,
  providerDurationSeconds,
  providerCostUsdTotal,
  providerTokensTotal,
  hooksEventsTotal,
  hooksPipelineDurationSeconds,
  viewerConnections,
  viewerEventsTotal,
  viewerDroppedTotal,
  dbSizeBytes,
  chunksActive,
  chunksStale,
  auditRowsTotal,
  processCpuUserSecondsTotal,
  processCpuSystemSecondsTotal,
  processResidentMemoryBytes,
  processOpenFds,
  nodejsEventloopLagSeconds,
} from "./metrics.js";
export {
  CardinalityGuard,
  getDefaultGuard,
  resetDefaultGuard,
  applyDefaultPolicies,
} from "./cardinality.js";
export {
  sanitizeString,
  sanitizeLabels,
  sanitizeLabelValue,
  guardLabels,
} from "./privacy-guard.js";
export {
  recordSearch,
  recordAnswer,
  recordProviderCall,
  recordChunkIngest,
  recordEmbedding,
  recordKgEntity,
  recordKgRelation,
  recordHookEvent,
  recordViewerConnect,
  recordViewerDisconnect,
  recordViewerEvent,
  recordViewerDropped,
  recordAuditWrite,
  startTimer,
  type SearchMethod,
  type SearchOutcome,
  type AnswerOutcome,
  type AnswerTiming,
  type ProviderKind,
  type ProviderOutcome,
  type ProvenanceKind,
} from "./record.js";
export {
  handle,
  render,
  OPENMETRICS_CONTENT_TYPE,
  PROMETHEUS_CONTENT_TYPE,
  type MetricsRequest,
  type MetricsResponse,
  type ExporterOpts,
} from "./exporter.js";
export {
  startProcessCollector,
  stopProcessCollector,
  collectOnce as collectProcessOnce,
} from "./collectors/process.collector.js";
export {
  startDbStatsCollector,
  stopDbStatsCollector,
  collectDbStats,
} from "./collectors/db-stats.collector.js";
export {
  startSearchTelemetryCollector,
  stopSearchTelemetryCollector,
  drain as drainSearchTelemetry,
} from "./collectors/search-telemetry.collector.js";
export {
  startProviderTelemetryCollector,
  stopProviderTelemetryCollector,
  drain as drainProviderTelemetry,
} from "./collectors/provider-telemetry.collector.js";
export {
  attachEventBusCollector,
  detachEventBusCollector,
  type EventBusLike,
} from "./collectors/eventbus.collector.js";
export {
  withAnswerMetrics,
  type AnswerHandler,
  type AnswerResult,
} from "./adapters/p1-adapter.js";
export {
  instrumentProviderCall,
  classifyProviderError,
  type ProviderCallMeta,
  type ProviderCallResult,
  type ProviderInner,
} from "./adapters/a3-adapter.js";
export {
  wrapBroadcast,
  trackConnection,
  reportBackpressureDrop,
  type BroadcastEvent,
  type BroadcastFn,
  type SocketLike,
} from "./adapters/p5-adapter.js";
