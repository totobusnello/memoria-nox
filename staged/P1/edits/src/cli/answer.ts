/**
 * src/cli/answer.ts — P1 T8: `nox-mem answer "<question>" [flags]`.
 *
 * Thin wrapper over `lib/answer/index.ts`. No business logic here;
 * we only parse argv, invoke answer(), and render to stdout.
 *
 * Flags (mirrors kickoff §T8 DoD + §5 AnswerRequest):
 *   --top-k N            top-K retrieval (1..20, default 8)
 *   --max-tokens N       LLM output budget (default 1500)
 *   --provider X         'gemini' (default) | 'mock'
 *   --model Y            override (default 'gemini-2.5-flash-lite' per D41 #1)
 *   --temperature N      0..1, default 0.2
 *   --cite               include numbered citation block (default ON)
 *   --no-cite            suppress citation block (markers still kept inline)
 *   --no-citations       strip [chunk_N] markers from rendered answer too
 *   --json               machine-readable JSON; suppresses pretty output
 *   --session-id X       passthrough for telemetry correlation
 *   --help, -h           print usage and exit 0
 *
 * Exit codes (kickoff §6 status-code parity, mapped to shell-friendly ints):
 *   0   ok
 *   2   invalid argv (bad flag, missing question)
 *   3   retrieval_empty
 *   4   hallucination_after_retry
 *   5   llm_error / llm_timeout
 *   1   unexpected runtime error
 *
 * Test seams: pass `argv`, `stdout`, `stderr`, `runAnswer`, `telemetryStore`
 * via runCli(opts). The bin shim (`bin/answer.ts` or `src/cli/index.ts`
 * dispatcher) calls runCli(process.argv.slice(2)) with prod defaults.
 */

import { answer as defaultAnswer, AnswerError } from "../lib/answer/index.js";
import type { AnswerOpts, AnswerResult } from "../lib/answer/index.js";
import {
  recordAnswer,
  type TelemetryStore,
} from "../lib/answer/telemetry.js";

// ─── Argv parsing ─────────────────────────────────────────────────────────

export interface ParsedArgs {
  question: string;
  topK?: number;
  maxTokens?: number;
  provider?: string;
  model?: string;
  temperature?: number;
  /** include citation block beneath answer */
  showCitations: boolean;
  /** also strip [chunk_N] markers from the answer text itself */
  stripMarkers: boolean;
  json: boolean;
  sessionId?: string;
  help: boolean;
}

export class CliArgError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "CliArgError";
  }
}

/** Parse argv into ParsedArgs. Pure function — easy to unit-test. */
export function parseArgs(argv: readonly string[]): ParsedArgs {
  const out: ParsedArgs = {
    question: "",
    showCitations: true,
    stripMarkers: false,
    json: false,
    help: false,
  };
  const positionals: string[] = [];

  for (let i = 0; i < argv.length; i++) {
    const tok = argv[i];
    if (tok === undefined) continue;
    switch (tok) {
      case "-h":
      case "--help":
        out.help = true;
        break;
      case "--json":
        out.json = true;
        break;
      case "--cite":
        out.showCitations = true;
        break;
      case "--no-cite":
        out.showCitations = false;
        break;
      case "--no-citations":
        out.showCitations = false;
        out.stripMarkers = true;
        break;
      case "--top-k":
      case "--topk": {
        const v = argv[++i];
        if (v === undefined) throw new CliArgError(`${tok} requires a value`);
        const n = parseInt(v, 10);
        if (!Number.isFinite(n)) {
          throw new CliArgError(`${tok} must be an integer, got '${v}'`);
        }
        out.topK = n;
        break;
      }
      case "--max-tokens": {
        const v = argv[++i];
        if (v === undefined) throw new CliArgError(`${tok} requires a value`);
        const n = parseInt(v, 10);
        if (!Number.isFinite(n)) {
          throw new CliArgError(`${tok} must be an integer, got '${v}'`);
        }
        out.maxTokens = n;
        break;
      }
      case "--provider": {
        const v = argv[++i];
        if (v === undefined) throw new CliArgError(`${tok} requires a value`);
        out.provider = v;
        break;
      }
      case "--model": {
        const v = argv[++i];
        if (v === undefined) throw new CliArgError(`${tok} requires a value`);
        out.model = v;
        break;
      }
      case "--temperature":
      case "--temp": {
        const v = argv[++i];
        if (v === undefined) throw new CliArgError(`${tok} requires a value`);
        const n = parseFloat(v);
        if (!Number.isFinite(n)) {
          throw new CliArgError(`${tok} must be a number, got '${v}'`);
        }
        out.temperature = n;
        break;
      }
      case "--session-id": {
        const v = argv[++i];
        if (v === undefined) throw new CliArgError(`${tok} requires a value`);
        out.sessionId = v;
        break;
      }
      default:
        if (tok.startsWith("--") || (tok.startsWith("-") && tok.length > 1)) {
          throw new CliArgError(`unknown flag: ${tok}`);
        }
        positionals.push(tok);
        break;
    }
  }

  if (out.help) return out;
  if (positionals.length === 0) {
    throw new CliArgError("missing required <question> positional");
  }
  out.question = positionals.join(" ");
  return out;
}

// ─── Help text ────────────────────────────────────────────────────────────

export const HELP_TEXT = `nox-mem answer — answer questions from nox-mem corpus with grounded citations.

Usage:
  nox-mem answer "<question>" [flags]

Flags:
  --top-k N         top-K retrieval (1..20, default 8)
  --max-tokens N    max LLM output tokens (64..8192, default 1500)
  --provider X      'gemini' (default) | 'mock'
  --model Y         model id (default gemini-2.5-flash-lite per D41 #1)
  --temperature N   0..1, default 0.2
  --cite            include numbered citation block (default)
  --no-cite         suppress citation block
  --no-citations    also strip [chunk_N] markers from answer text
  --json            emit AnswerResponse JSON to stdout
  --session-id X    correlation tag (telemetry only)
  -h, --help        show this help and exit

Examples:
  nox-mem answer "What is the salience formula?"
  nox-mem answer "Which retention default for lessons?" --top-k 12 --json
  NOX_ANSWER_MODEL=gemini-2.5-flash nox-mem answer "Provider swap test"

Exit codes: 0 ok | 2 bad argv | 3 retrieval_empty | 4 hallucination_after_retry | 5 llm_error
`;

// ─── Renderer ─────────────────────────────────────────────────────────────

const MARKER_RE = /\s?\[chunk_\d+\]/g;

export function renderHuman(res: AnswerResult, args: ParsedArgs): string {
  const body = args.stripMarkers ? res.answer.replace(MARKER_RE, "") : res.answer;
  const parts: string[] = [body.trimEnd()];
  if (args.showCitations && res.citations.length > 0) {
    parts.push("", "Citations:");
    for (const c of res.citations) {
      const range = c.line_range ? ` ${c.line_range}` : "";
      parts.push(`  [${c.marker_id}] ${c.file_path}${range}`);
      parts.push(`      ${c.snippet}`);
    }
  }
  parts.push("", `(model=${res.metadata.model} latency=${res.metadata.latency_ms}ms ` +
    `retrieved=${res.metadata.retrieval_count} cited=${res.citations.length})`);
  return parts.join("\n");
}

export function renderJson(res: AnswerResult, args: ParsedArgs): string {
  const body = args.stripMarkers ? res.answer.replace(MARKER_RE, "") : res.answer;
  const obj = {
    answer: body,
    citations: res.citations,
    metadata: res.metadata,
  };
  return JSON.stringify(obj);
}

// ─── Run ──────────────────────────────────────────────────────────────────

export interface RunCliOpts {
  argv: readonly string[];
  stdout: (line: string) => void;
  stderr: (line: string) => void;
  /** Test seam: replace answer() with a stub. */
  runAnswer?: (opts: AnswerOpts) => Promise<AnswerResult>;
  /** Test seam: optional telemetry sink. CLI writes one row per call. */
  telemetryStore?: TelemetryStore;
}

export async function runCli(opts: RunCliOpts): Promise<number> {
  let parsed: ParsedArgs;
  try {
    parsed = parseArgs(opts.argv);
  } catch (err) {
    if (err instanceof CliArgError) {
      opts.stderr(`error: ${err.message}\n${HELP_TEXT}`);
      return 2;
    }
    opts.stderr(`unexpected argv error: ${(err as Error).message}`);
    return 1;
  }

  if (parsed.help) {
    opts.stdout(HELP_TEXT);
    return 0;
  }

  const callOpts: AnswerOpts = { question: parsed.question };
  if (parsed.topK !== undefined) callOpts.topK = parsed.topK;
  if (parsed.maxTokens !== undefined) callOpts.maxTokens = parsed.maxTokens;
  if (parsed.provider !== undefined) callOpts.provider = parsed.provider;
  if (parsed.model !== undefined) callOpts.model = parsed.model;
  if (parsed.temperature !== undefined) callOpts.temperature = parsed.temperature;

  const run = opts.runAnswer ?? defaultAnswer;
  try {
    const res = await run(callOpts);

    if (opts.telemetryStore) {
      recordAnswer(opts.telemetryStore, {
        question: parsed.question,
        citationCount: res.citations.length,
        metadata: res.metadata,
        sessionId: parsed.sessionId ?? null,
      });
    }

    opts.stdout(parsed.json ? renderJson(res, parsed) : renderHuman(res, parsed));

    // retrieval_empty surfaces via failed_reason on metadata; map to exit 3.
    if (res.metadata.failed_reason === "retrieval_empty") return 3;
    return 0;
  } catch (err) {
    if (err instanceof AnswerError) {
      if (opts.telemetryStore) {
        recordAnswer(opts.telemetryStore, {
          question: parsed.question,
          citationCount: 0,
          metadata: {
            latency_ms: (err.metadata.latency_ms as number | undefined) ?? 0,
            tokens_in: (err.metadata.tokens_in as number | undefined) ?? 0,
            tokens_out: (err.metadata.tokens_out as number | undefined) ?? 0,
            provider: (err.metadata.provider as string | undefined) ?? "n/a",
            model: (err.metadata.model as string | undefined) ?? "n/a",
            retrieval_count: (err.metadata.retrieval_count as number | undefined) ?? 0,
            fallback_used: (err.metadata.fallback_used as boolean | undefined) ?? false,
            failed_reason: err.reason,
          },
          sessionId: parsed.sessionId ?? null,
        });
      }
      const payload = parsed.json
        ? JSON.stringify({
            error: true,
            reason: err.reason,
            message: err.message,
            metadata: err.metadata,
          })
        : `error: ${err.message} (${err.reason})`;
      opts.stderr(payload);
      switch (err.reason) {
        case "retrieval_empty":
          return 3;
        case "hallucination_after_retry":
        case "hallucinated_citation":
          return 4;
        case "llm_error":
        case "llm_timeout":
          return 5;
        case "invalid_input":
          return 2;
        default:
          return 1;
      }
    }
    opts.stderr(`unexpected: ${(err as Error).message}`);
    return 1;
  }
}
