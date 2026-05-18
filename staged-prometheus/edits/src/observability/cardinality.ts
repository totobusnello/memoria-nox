/**
 * src/observability/cardinality.ts — Cardinality guard (T8).
 *
 * Prevents unbounded label cardinality from blowing up the registry.
 *
 * Failure modes if not enforced:
 *   1. user_id, session_id, query_text in labels → millions of series → OOM
 *   2. Bug: cycled value in label → series count grows forever
 *   3. Adversary input → DoS via metric explosion
 *
 * GUARD STRATEGY:
 *   - Per-metric `maxSeries` cap (default 1000).
 *   - Per-metric label *value* allowlist (optional): only those values may
 *     be reported. Anything else is bucketed as "other".
 *   - On overflow: drop the increment + log once per cooldown window.
 *
 * USAGE:
 *   const guard = new CardinalityGuard();
 *   guard.policy("nox_search_requests_total", {
 *     maxSeries: 50,
 *     labelAllowlist: { method: ["cli", "api", "mcp"] },
 *   });
 *   const safe = guard.guard("nox_search_requests_total", { method: payload });
 *   if (safe) counter.inc(safe);
 */

export interface MetricPolicy {
  /** Max distinct label-tuple series allowed. Default 1000. */
  maxSeries?: number;
  /** Per-label allowlist of values. Unknown values → "other". */
  labelAllowlist?: Record<string, readonly string[]>;
  /** Per-label hard drop list (e.g. "user_id" must never appear). */
  labelDenylist?: readonly string[];
}

const DEFAULT_MAX_SERIES = 1000;
const WARN_COOLDOWN_MS = 60_000; // log dropped overflow at most once per minute per metric

export class CardinalityGuard {
  private readonly policies = new Map<string, Required<MetricPolicy>>();
  private readonly seenSeries = new Map<string, Set<string>>();
  private readonly drops = new Map<string, { count: number; lastWarn: number }>();
  private readonly log: (msg: string) => void;

  constructor(log: (msg: string) => void = (m) => console.warn(m)) {
    this.log = log;
  }

  /** Configure a per-metric policy. */
  policy(metricName: string, p: MetricPolicy): void {
    this.policies.set(metricName, {
      maxSeries: p.maxSeries ?? DEFAULT_MAX_SERIES,
      labelAllowlist: p.labelAllowlist ?? {},
      labelDenylist: p.labelDenylist ?? [],
    });
  }

  /**
   * Validate + normalize a label set for a metric.
   * Returns the (possibly rewritten) labels — or `null` if it must be dropped.
   */
  guard(metricName: string, labels: Record<string, string>): Record<string, string> | null {
    const policy = this.policies.get(metricName);
    const max = policy?.maxSeries ?? DEFAULT_MAX_SERIES;
    const allow = policy?.labelAllowlist ?? {};
    const deny = policy?.labelDenylist ?? [];

    // Strip denylisted labels — never let them through.
    const out: Record<string, string> = {};
    for (const [k, v] of Object.entries(labels)) {
      if (deny.includes(k)) continue;
      const list = allow[k];
      if (list && list.length > 0 && !list.includes(v)) {
        out[k] = "other";
      } else {
        out[k] = v;
      }
    }

    // Compute a stable series key.
    const seriesKey = stringifyLabels(out);

    let seen = this.seenSeries.get(metricName);
    if (!seen) {
      seen = new Set<string>();
      this.seenSeries.set(metricName, seen);
    }

    if (seen.has(seriesKey)) {
      return out; // already counted; safe to emit
    }

    if (seen.size >= max) {
      this.noteDrop(metricName);
      return null;
    }

    seen.add(seriesKey);
    return out;
  }

  /** Current series count for a metric. */
  seriesCount(metricName: string): number {
    return this.seenSeries.get(metricName)?.size ?? 0;
  }

  /** Number of drops for a metric (since process start). */
  dropCount(metricName: string): number {
    return this.drops.get(metricName)?.count ?? 0;
  }

  /** Reset (test-only). */
  reset(): void {
    this.seenSeries.clear();
    this.drops.clear();
  }

  private noteDrop(metricName: string): void {
    const now = Date.now();
    let d = this.drops.get(metricName);
    if (!d) {
      d = { count: 0, lastWarn: 0 };
      this.drops.set(metricName, d);
    }
    d.count += 1;
    if (now - d.lastWarn > WARN_COOLDOWN_MS) {
      d.lastWarn = now;
      this.log(
        `[cardinality] dropped label-set for metric ${metricName} ` +
          `(cap reached; total drops=${d.count})`,
      );
    }
  }
}

function stringifyLabels(labels: Record<string, string>): string {
  const keys = Object.keys(labels).sort();
  if (keys.length === 0) return "";
  return keys.map((k) => `${k}=${labels[k]}`).join("|");
}

// ─── Default process-wide guard ──────────────────────────────────────────────

let _default: CardinalityGuard | undefined;

export function getDefaultGuard(): CardinalityGuard {
  if (!_default) {
    _default = new CardinalityGuard();
    applyDefaultPolicies(_default);
  }
  return _default;
}

export function resetDefaultGuard(): void {
  _default = undefined;
}

/**
 * Apply nox-mem's standard policies. Keep this conservative — anything that
 * could explode (user_id, query_text, paths) must be denylisted everywhere.
 */
export function applyDefaultPolicies(g: CardinalityGuard): void {
  const FORBIDDEN_LABELS = [
    "user_id",
    "session_id",
    "query",
    "query_text",
    "prompt",
    "response",
    "email",
    "ip",
    "path",
    "filename",
    "chunk_id",
    "entity_id",
  ];

  // Apply forbidden-label policy globally by attaching denylist on each metric.
  const ALL = [
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
  ];

  for (const m of ALL) {
    g.policy(m, { labelDenylist: FORBIDDEN_LABELS, maxSeries: 1000 });
  }

  // Tighter caps + allowlists for high-traffic metrics.
  g.policy("nox_search_requests_total", {
    maxSeries: 30,
    labelAllowlist: {
      method: ["cli", "api", "mcp"],
      outcome: ["success", "empty", "error"],
    },
    labelDenylist: FORBIDDEN_LABELS,
  });
  g.policy("nox_search_duration_seconds", {
    maxSeries: 10,
    labelAllowlist: { method: ["cli", "api", "mcp"] },
    labelDenylist: FORBIDDEN_LABELS,
  });
  g.policy("nox_search_results_returned", {
    maxSeries: 10,
    labelAllowlist: { method: ["cli", "api", "mcp"] },
    labelDenylist: FORBIDDEN_LABELS,
  });
  g.policy("nox_answer_requests_total", {
    maxSeries: 10,
    labelAllowlist: {
      failure_reason: [
        "success",
        "no_chunks",
        "llm_failed",
        "hallucination",
        "timeout",
        "cost_cap",
      ],
    },
    labelDenylist: FORBIDDEN_LABELS,
  });
  g.policy("nox_answer_duration_seconds", {
    maxSeries: 10,
    labelAllowlist: {
      phase: ["total", "retrieve", "rerank", "synthesize", "verify"],
    },
    labelDenylist: FORBIDDEN_LABELS,
  });
  g.policy("nox_answer_tokens_total", {
    maxSeries: 4,
    labelAllowlist: { direction: ["input", "output"] },
    labelDenylist: FORBIDDEN_LABELS,
  });
  g.policy("nox_provider_calls_total", {
    maxSeries: 200,
    labelAllowlist: {
      provider: ["gemini", "openai", "anthropic", "voyage", "ollama", "other"],
      outcome: ["success", "rate_limit", "error", "fallback"],
    },
    labelDenylist: FORBIDDEN_LABELS,
  });
  g.policy("nox_provider_duration_seconds", {
    maxSeries: 50,
    labelAllowlist: {
      provider: ["gemini", "openai", "anthropic", "voyage", "ollama", "other"],
      kind: ["embedding", "llm"],
    },
    labelDenylist: FORBIDDEN_LABELS,
  });
  g.policy("nox_provider_cost_usd_total", {
    maxSeries: 200,
    labelAllowlist: {
      provider: ["gemini", "openai", "anthropic", "voyage", "ollama", "other"],
    },
    labelDenylist: FORBIDDEN_LABELS,
  });
  g.policy("nox_provider_tokens_total", {
    maxSeries: 30,
    labelAllowlist: {
      provider: ["gemini", "openai", "anthropic", "voyage", "ollama", "other"],
      direction: ["input", "output"],
    },
    labelDenylist: FORBIDDEN_LABELS,
  });
  g.policy("nox_hooks_events_total", {
    maxSeries: 100,
    labelAllowlist: {
      layer: ["pre-tool", "post-tool", "tool-start", "tool-end", "user-prompt"],
      reason: ["captured", "filtered", "redacted", "error", "dropped"],
    },
    labelDenylist: FORBIDDEN_LABELS,
  });
  g.policy("nox_viewer_events_total", {
    maxSeries: 30,
    labelAllowlist: {
      type: [
        "ingest",
        "search",
        "kg_update",
        "answer",
        "provider_call",
        "audit",
        "hook",
        "other",
      ],
    },
    labelDenylist: FORBIDDEN_LABELS,
  });
  g.policy("nox_viewer_dropped_total", {
    maxSeries: 10,
    labelAllowlist: { reason: ["slow_consumer", "queue_full", "client_gone"] },
    labelDenylist: FORBIDDEN_LABELS,
  });
  g.policy("nox_db_size_bytes", {
    maxSeries: 5,
    labelAllowlist: { component: ["main", "wal", "shm"] },
    labelDenylist: FORBIDDEN_LABELS,
  });
  g.policy("nox_audit_rows_total", {
    maxSeries: 10,
    labelAllowlist: {
      table: [
        "ops_audit",
        "provider_telemetry",
        "search_telemetry",
        "agent_events",
        "answer_telemetry",
      ],
    },
    labelDenylist: FORBIDDEN_LABELS,
  });
}
