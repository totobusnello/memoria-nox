/**
 * benchmark/answer-latency.ts — P1 T14.
 *
 * Runs 50 answer() calls against an in-memory SQLite v11 schema with a
 * mock LLM (canned answer + simulated 100ms LLM latency) and reports:
 *   - total p50 / p95 / p99
 *   - per-phase breakdown (retrieval / prompt / LLM / citation+parse / telemetry)
 *   - budget comparison (retrieval ≤200ms, prompt ≤50ms, LLM ≤4000ms p95,
 *     citation ≤30ms, telemetry ≤10ms = ~4.3s total p95)
 *
 * Output: JSON to stdout + a human-readable summary on stderr. The JSON
 * is the source of truth — the human summary is a courtesy for terminals.
 *
 * Usage:
 *   npm run build && node dist/benchmark/answer-latency.js [--n=50] [--json-only]
 *
 * Env:
 *   NOX_BENCH_LLM_MS  — override the simulated LLM delay (default 100)
 *   NOX_BENCH_N       — override sample count (default 50)
 */

import { performance } from "node:perf_hooks";
import Database from "better-sqlite3";
import type { Database as DatabaseType } from "better-sqlite3";

import {
  answer as realAnswer,
  __setRawSearchForTests,
} from "../src/lib/answer/index.js";
import type { LLMProvider, LLMCallOpts, LLMCallResult } from "../src/lib/answer/provider.js";
import type { RawChunk } from "../src/lib/answer/types.js";
import {
  recordAnswer,
  INSERT_SQL,
  type AnswerTelemetryRow,
  type TelemetryStore,
} from "../src/lib/answer/telemetry.js";

// ─── Config ────────────────────────────────────────────────────────────────

const argv = process.argv.slice(2);
const nFromArg = (() => {
  const m = argv.find((a) => a.startsWith("--n="));
  return m ? parseInt(m.split("=")[1] ?? "50", 10) : undefined;
})();
const JSON_ONLY = argv.includes("--json-only");

const N = nFromArg ?? parseInt(process.env.NOX_BENCH_N ?? "50", 10);
const LLM_MS = parseInt(process.env.NOX_BENCH_LLM_MS ?? "100", 10);

// Budgets — kickoff §T14 + answer primitive spec §8.
const BUDGET = {
  retrieval_ms: 200,
  prompt_ms: 50,
  llm_ms: 4000,
  citation_ms: 30,
  telemetry_ms: 10,
  total_ms: 4300,
};

// ─── Mock provider with controllable delay ────────────────────────────────

class DelayedMockProvider implements LLMProvider {
  public readonly name = "mock";
  constructor(
    private readonly answerText: string,
    private readonly delayMs: number
  ) {}
  public async complete(opts: LLMCallOpts): Promise<LLMCallResult> {
    const t0 = Date.now();
    await new Promise((r) => setTimeout(r, this.delayMs));
    return {
      text: this.answerText,
      tokensIn: Math.ceil((opts.system.length + opts.user.length) / 4),
      tokensOut: Math.ceil(this.answerText.length / 4),
      latencyMs: Date.now() - t0,
    };
  }
}

// ─── Fixture corpus ────────────────────────────────────────────────────────

const FIXTURE: RawChunk[] = [
  {
    chunk_id: 1,
    file_path: "memory/entities/decision/d41.md",
    content: "D41 #1 default model is gemini-2.5-flash-lite.",
    content_hash: "h1",
    score: 0.9,
  },
  {
    chunk_id: 2,
    file_path: "memory/entities/feedback/salience.md",
    content: "Salience = recency × pain × importance.",
    content_hash: "h2",
    score: 0.85,
  },
  {
    chunk_id: 3,
    file_path: "memory/entities/lesson/never-sed.md",
    content: "Never sed -i on .db files; corrupts pages.",
    content_hash: "h3",
    score: 0.7,
  },
];

const QUESTIONS = [
  "What is the default model?",
  "What is salience?",
  "Why no sed on db files?",
  "Which retention default for lesson type?",
  "What is the PT-BR pronoun rule?",
];

// ─── Real SQLite TelemetryStore ────────────────────────────────────────────

const SCHEMA_V11 = `
CREATE TABLE answer_telemetry (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  question_hash TEXT NOT NULL, session_id TEXT,
  timestamp_ms INTEGER NOT NULL, provider TEXT NOT NULL, model TEXT NOT NULL,
  retrieval_count INTEGER NOT NULL, citation_count INTEGER NOT NULL,
  tokens_in INTEGER, tokens_out INTEGER, latency_ms INTEGER NOT NULL,
  fallback_used INTEGER NOT NULL DEFAULT 0, failed_reason TEXT,
  cost_estimate_usd REAL NOT NULL DEFAULT 0,
  CHECK (failed_reason IS NULL OR failed_reason IN
         ('hallucinated_citation', 'provider_down', 'token_budget'))
);
`;

class Sqlite3TelemetryStore implements TelemetryStore {
  private readonly stmt;
  constructor(db: DatabaseType) {
    this.stmt = db.prepare(INSERT_SQL);
  }
  public insert(row: AnswerTelemetryRow): void {
    this.stmt.run(row);
  }
}

// ─── Phase-timed runner ────────────────────────────────────────────────────

interface PhaseSample {
  retrieval_ms: number;
  prompt_ms: number;
  llm_ms: number;
  citation_ms: number;
  telemetry_ms: number;
  total_ms: number;
}

async function runOne(
  store: TelemetryStore,
  provider: LLMProvider,
  question: string
): Promise<PhaseSample> {
  // We measure phases by wrapping retrieve/provider override; full
  // answer() pipeline performs retrieval → prompt → LLM → citation parse.
  // We capture timestamps via wall-clock perf hooks.

  let tRetrieveStart = 0;
  let tRetrieveEnd = 0;
  let tLlmStart = 0;
  let tLlmEnd = 0;

  const wrappedRetrieve = async () => {
    tRetrieveStart = performance.now();
    // Synchronous fixture — emulate dedupe pass.
    const out = FIXTURE.map((c, i) => ({
      chunk_id: c.chunk_id,
      marker_id: `chunk_${i + 1}`,
      file_path: c.file_path,
      content: c.content,
      content_hash: c.content_hash,
      score: c.score,
    }));
    tRetrieveEnd = performance.now();
    return out;
  };

  const timedProvider: LLMProvider = {
    name: provider.name,
    async complete(opts: LLMCallOpts) {
      tLlmStart = performance.now();
      const r = await provider.complete(opts);
      tLlmEnd = performance.now();
      return r;
    },
  };

  const tTotalStart = performance.now();
  const res = await realAnswer({
    question,
    providerOverride: timedProvider,
    retrieveOverride: wrappedRetrieve,
  });
  const tAfterAnswer = performance.now();

  const tTelStart = performance.now();
  recordAnswer(store, {
    question,
    citationCount: res.citations.length,
    metadata: res.metadata,
  });
  const tTelEnd = performance.now();

  const retrieval = tRetrieveEnd - tRetrieveStart;
  const llm = tLlmEnd - tLlmStart;
  // citation+parse = time between provider return and answer() return,
  // less any work after llm in the lib (essentially: parse + format).
  const citation = tAfterAnswer - tLlmEnd;
  const telemetry = tTelEnd - tTelStart;
  // prompt assembly = time between retrieval end and LLM start
  const prompt = tLlmStart - tRetrieveEnd;
  const total = tTelEnd - tTotalStart;

  return {
    retrieval_ms: retrieval,
    prompt_ms: prompt,
    llm_ms: llm,
    citation_ms: citation,
    telemetry_ms: telemetry,
    total_ms: total,
  };
}

// ─── Percentile helpers ────────────────────────────────────────────────────

function percentile(values: number[], p: number): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const idx = Math.min(
    sorted.length - 1,
    Math.floor((p / 100) * sorted.length)
  );
  return sorted[idx]!;
}

function stats(values: number[]) {
  return {
    p50: round(percentile(values, 50)),
    p95: round(percentile(values, 95)),
    p99: round(percentile(values, 99)),
    min: round(Math.min(...values)),
    max: round(Math.max(...values)),
    mean: round(values.reduce((a, b) => a + b, 0) / values.length),
  };
}

function round(n: number): number {
  return Math.round(n * 100) / 100;
}

// ─── Main ──────────────────────────────────────────────────────────────────

async function main() {
  // Setup
  const db = new Database(":memory:");
  db.exec(SCHEMA_V11);
  const store = new Sqlite3TelemetryStore(db);
  const provider = new DelayedMockProvider(
    "Answer text [chunk_1] with [chunk_2] cites.",
    LLM_MS
  );
  __setRawSearchForTests(async () => FIXTURE);

  // Warmup (3 calls — JIT + sqlite cache)
  for (let i = 0; i < 3; i++) {
    await runOne(store, provider, QUESTIONS[0]!);
  }
  // Wipe warmup rows so they don't skew DB row count
  db.exec("DELETE FROM answer_telemetry");

  // Measured run
  const samples: PhaseSample[] = [];
  for (let i = 0; i < N; i++) {
    const q = QUESTIONS[i % QUESTIONS.length]!;
    samples.push(await runOne(store, provider, q));
  }

  const phases = {
    retrieval: stats(samples.map((s) => s.retrieval_ms)),
    prompt: stats(samples.map((s) => s.prompt_ms)),
    llm: stats(samples.map((s) => s.llm_ms)),
    citation: stats(samples.map((s) => s.citation_ms)),
    telemetry: stats(samples.map((s) => s.telemetry_ms)),
    total: stats(samples.map((s) => s.total_ms)),
  };

  const budgetReport = {
    retrieval_p95_ok: phases.retrieval.p95 <= BUDGET.retrieval_ms,
    prompt_p95_ok: phases.prompt.p95 <= BUDGET.prompt_ms,
    llm_p95_ok: phases.llm.p95 <= BUDGET.llm_ms,
    citation_p95_ok: phases.citation.p95 <= BUDGET.citation_ms,
    telemetry_p95_ok: phases.telemetry.p95 <= BUDGET.telemetry_ms,
    total_p95_ok: phases.total.p95 <= BUDGET.total_ms,
  };

  const result = {
    n: N,
    llm_simulated_ms: LLM_MS,
    phases,
    budget: BUDGET,
    budget_report: budgetReport,
    rows_in_telemetry: (
      db.prepare("SELECT COUNT(*) AS c FROM answer_telemetry").get() as {
        c: number;
      }
    ).c,
  };

  // JSON to stdout
  process.stdout.write(JSON.stringify(result, null, 2) + "\n");

  // Human summary to stderr (unless --json-only)
  if (!JSON_ONLY) {
    const lines: string[] = [];
    lines.push("");
    lines.push(`answer-latency benchmark — n=${N} samples`);
    lines.push(`simulated LLM delay: ${LLM_MS}ms per call`);
    lines.push("");
    lines.push(
      "phase              p50       p95       p99       budget   ok?"
    );
    lines.push(
      "----------------- --------- --------- --------- -------- -----"
    );
    const row = (
      name: string,
      st: { p50: number; p95: number; p99: number },
      budget: number,
      ok: boolean
    ) =>
      `${name.padEnd(17)} ${String(st.p50).padStart(7)}ms ` +
      `${String(st.p95).padStart(7)}ms ${String(st.p99).padStart(7)}ms ` +
      `${String(budget).padStart(6)}ms ${ok ? "  OK" : "FAIL"}`;
    lines.push(
      row("retrieval", phases.retrieval, BUDGET.retrieval_ms, budgetReport.retrieval_p95_ok)
    );
    lines.push(row("prompt", phases.prompt, BUDGET.prompt_ms, budgetReport.prompt_p95_ok));
    lines.push(row("llm (sim)", phases.llm, BUDGET.llm_ms, budgetReport.llm_p95_ok));
    lines.push(
      row("citation+parse", phases.citation, BUDGET.citation_ms, budgetReport.citation_p95_ok)
    );
    lines.push(
      row("telemetry", phases.telemetry, BUDGET.telemetry_ms, budgetReport.telemetry_p95_ok)
    );
    lines.push(
      row("TOTAL", phases.total, BUDGET.total_ms, budgetReport.total_p95_ok)
    );
    lines.push("");
    lines.push(`telemetry rows persisted: ${result.rows_in_telemetry}`);
    lines.push("");
    process.stderr.write(lines.join("\n") + "\n");
  }

  db.close();

  // Exit non-zero if total p95 over budget — useful as a CI gate.
  if (!budgetReport.total_p95_ok) {
    process.exit(1);
  }
}

main().catch((err) => {
  process.stderr.write(`bench failed: ${(err as Error).message}\n`);
  process.exit(2);
});
