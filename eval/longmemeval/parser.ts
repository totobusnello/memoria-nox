/**
 * parser.ts — parse LongMemEval splits into eval-ready records.
 *
 * Two outputs:
 *   1. Question records  → (question_id, question_type, question, answer,
 *                           question_date, haystack_session_ids, haystack_dates,
 *                           answer_session_ids)
 *   2. Session chunks    → (chunk_id, question_id, session_id, session_date,
 *                           text)   — one per haystack session (D4: per-session
 *                           granularity)
 *
 * Schema source: huggingface.co/datasets/xiaowu0162/longmemeval-cleaned (verified
 * 2026-05-17, commit 98d7416...). Each split is a JSON list[]. Per-question:
 *
 *   {
 *     "question_id":           "<uuid-like>",
 *     "question_type":         "single-session-user" | ... ("_abs" suffix possible),
 *     "question":              str,
 *     "answer":                str,   (ground truth)
 *     "question_date":         "YYYY/MM/DD..."   (when the user asks),
 *     "haystack_session_ids":  [str, ...],
 *     "haystack_dates":        [str, ...]        (aligned with haystack_session_ids),
 *     "haystack_sessions":     [[{role,content,has_answer?:bool}, ...], ...]
 *                              (aligned with haystack_session_ids),
 *     "answer_session_ids":    [str, ...]        (subset of haystack_session_ids
 *                                                 marked as containing the answer)
 *   }
 *
 * Categories (paper §3):
 *   single-session-user, single-session-assistant, single-session-preference,
 *   temporal-reasoning, knowledge-update, multi-session.
 *
 * Abstention variants: in `longmemeval-cleaned`, abstention is signalled by
 * the **question_id** suffix `_abs` (NOT by question_type — verified against
 * commit 98d7416c, 2026-05-17: question_type stays as the base category, only
 * 30 / 500 records have `_abs` on question_id). The assistant should refuse
 * to answer ("I don't know"). Parser preserves the raw question_type and
 * exposes `is_abstention` from the question_id suffix; score.ts distinguishes.
 *
 * Usage:
 *   npx tsx eval/longmemeval/parser.ts --split oracle --questions
 *   npx tsx eval/longmemeval/parser.ts --split oracle --chunks
 *   npx tsx eval/longmemeval/parser.ts --split oracle --ingest
 *   npx tsx eval/longmemeval/parser.ts --split oracle --ingest --embed
 *
 * Embedding is OFF by default; pass --embed to call nox-mem vectorize against
 * the eval.db (requires GEMINI_API_KEY).
 */

import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const HERE = dirname(__filename);
const DATA_DIR = resolve(HERE, "data");
const EVAL_DB = resolve(HERE, "eval.db");

const VALID_SPLITS = new Set(["oracle", "s_cleaned", "m_cleaned"]);

// 6 base categories; `_abs` variants are folded into their parent for
// stratification but tracked separately for scoring.
const BASE_CATEGORIES = [
  "single-session-user",
  "single-session-assistant",
  "single-session-preference",
  "temporal-reasoning",
  "knowledge-update",
  "multi-session",
] as const;

export type BaseCategory = (typeof BASE_CATEGORIES)[number];

export interface SessionTurn {
  role: string;            // "user" | "assistant"
  content: string;
  has_answer?: boolean;    // gold-evidence marker on individual turns
}

export interface SessionChunk {
  chunk_id: string;                // `${question_id}::${session_id}`
  question_id: string;
  session_id: string;
  session_date: string;
  text: string;                    // newline-joined "role: content" with header
  has_answer_turns: number[];      // indices of turns marked has_answer=true (diagnostic)
  is_answer_session: boolean;      // session_id ∈ answer_session_ids
}

export interface QARecord {
  question_id: string;
  question_type: string;           // raw, with possible "_abs" suffix
  base_category: BaseCategory;     // _abs stripped
  is_abstention: boolean;
  question: string;
  answer: string;                  // ground truth
  question_date: string;
  haystack_session_ids: string[];
  haystack_dates: string[];        // aligned with haystack_session_ids
  answer_session_ids: string[];
}

interface RawTurn {
  role?: string;
  content?: string;
  has_answer?: boolean;
}

interface RawQuestion {
  question_id?: string;
  question_type?: string;
  question?: string;
  answer?: string;
  question_date?: string;
  haystack_session_ids?: string[];
  haystack_dates?: string[];
  haystack_sessions?: RawTurn[][];
  answer_session_ids?: string[];
}

function deriveBaseCategory(question_type: string, question_id: string): { base: BaseCategory; is_abs: boolean } {
  // In longmemeval-cleaned, abstention is signalled by question_id ending with
  // `_abs`. question_type stays as the base category in this split. We accept
  // either source for forward compat with future re-splits.
  const is_abs = question_id.endsWith("_abs") || question_type.endsWith("_abs");
  const stripped = question_type.endsWith("_abs") ? question_type.slice(0, -"_abs".length) : question_type;
  const base = stripped as BaseCategory;
  if (!BASE_CATEGORIES.includes(base)) {
    return { base: base as BaseCategory, is_abs };
  }
  return { base, is_abs };
}

export async function loadSplit(split: string): Promise<RawQuestion[]> {
  if (!VALID_SPLITS.has(split)) {
    throw new Error(`unknown split "${split}"; expected one of: ${[...VALID_SPLITS].join(", ")}`);
  }
  const file = resolve(DATA_DIR, `longmemeval_${split}.json`);
  const txt = await readFile(file, "utf8");
  const j = JSON.parse(txt);
  if (!Array.isArray(j)) throw new Error(`Expected top-level JSON array in ${file}`);
  return j as RawQuestion[];
}

export function extractQuestions(raw: RawQuestion[]): QARecord[] {
  const out: QARecord[] = [];
  for (const r of raw) {
    if (!r.question_id || !r.question_type || !r.question || r.answer === undefined) continue;
    const { base, is_abs } = deriveBaseCategory(r.question_type, r.question_id);
    out.push({
      question_id: r.question_id,
      question_type: r.question_type,
      base_category: base,
      is_abstention: is_abs,
      question: r.question,
      answer: String(r.answer),
      question_date: r.question_date ?? "",
      haystack_session_ids: r.haystack_session_ids ?? [],
      haystack_dates: r.haystack_dates ?? [],
      answer_session_ids: r.answer_session_ids ?? [],
    });
  }
  return out;
}

export function extractSessionChunks(raw: RawQuestion[]): SessionChunk[] {
  const out: SessionChunk[] = [];
  for (const r of raw) {
    if (!r.question_id || !Array.isArray(r.haystack_session_ids) || !Array.isArray(r.haystack_sessions)) {
      continue;
    }
    const sids = r.haystack_session_ids;
    const dates = r.haystack_dates ?? [];
    const sessions = r.haystack_sessions;
    const answerSet = new Set(r.answer_session_ids ?? []);
    const n = Math.min(sids.length, sessions.length);
    for (let i = 0; i < n; i++) {
      const sid = sids[i];
      const date = dates[i] ?? "";
      const turns = sessions[i] ?? [];
      const lines: string[] = [];
      const evidenceIdx: number[] = [];
      lines.push(`[session_id=${sid} date=${date}]`);
      turns.forEach((t, idx) => {
        if (!t || typeof t !== "object") return;
        const role = String(t.role ?? "");
        const content = String(t.content ?? "").replace(/\r?\n/g, " ");
        lines.push(`${role}: ${content}`);
        if (t.has_answer === true) evidenceIdx.push(idx);
      });
      out.push({
        chunk_id: `${r.question_id}::${sid}`,
        question_id: r.question_id,
        session_id: sid,
        session_date: date,
        text: lines.join("\n"),
        has_answer_turns: evidenceIdx,
        is_answer_session: answerSet.has(sid),
      });
    }
  }
  return out;
}

/**
 * Ingest session chunks into eval.db using the nox-mem CLI.
 *
 * SAFEGUARD: refuse if eval.db path resolves to anything containing
 * "nox-mem.db" (production DB). Belt-and-braces — the CLI's own
 * OPENCLAW_WORKSPACE should already isolate.
 *
 * SCAFFOLD NOTE: like Q1 LoCoMo, the actual ingest path is wired in a
 * follow-up commit so the dry-run can validate parser correctness in
 * isolation first. We emit ingest-ready JSONL on stdout (first 5 rows
 * for sanity) so a separate tool can pipe into nox-mem.
 */
async function ingest(chunks: SessionChunk[], opts: { embed: boolean }): Promise<void> {
  if (EVAL_DB.includes("nox-mem.db") || EVAL_DB === "/root/.openclaw/workspace/tools/nox-mem/nox-mem.db") {
    throw new Error(`refuse to write to production DB: ${EVAL_DB}`);
  }
  console.error(`[ingest] target: ${EVAL_DB}`);
  console.error(`[ingest] session chunks: ${chunks.length}`);
  console.error("[ingest] NOTE: this scaffold *describes* ingestion; full ingest path is");
  console.error("[ingest]       deferred to a follow-up so the dry-run can validate");
  console.error("[ingest]       the question/chunk parsing in isolation first.");
  console.error("[ingest] To wire the actual ingest, write tmp markdown per session or");
  console.error("[ingest] use the nox-mem CLI batch-ingest path with --db=<eval.db>.");

  if (opts.embed) {
    console.error("[ingest] --embed requested — would call:");
    console.error(`[ingest]   nox-mem vectorize --db ${EVAL_DB}`);
  }

  for (const c of chunks.slice(0, 5)) {
    process.stdout.write(JSON.stringify(c) + "\n");
  }
  if (chunks.length > 5) {
    console.error(`[ingest] (only first 5 emitted to stdout for sanity; ${chunks.length} total parsed)`);
  }
}

function arg(name: string, fallback?: string): string | undefined {
  const i = process.argv.indexOf(name);
  if (i < 0) return fallback;
  return process.argv[i + 1] ?? fallback;
}

async function main(): Promise<void> {
  const split = arg("--split");
  if (!split || !VALID_SPLITS.has(split)) {
    console.error(`Usage: parser.ts --split (oracle|s_cleaned|m_cleaned) (--questions|--chunks|--ingest [--embed])`);
    process.exit(2);
  }
  const mode =
    process.argv.includes("--questions") ? "questions"
    : process.argv.includes("--chunks") ? "chunks"
    : process.argv.includes("--ingest") ? "ingest"
    : null;
  if (!mode) {
    console.error(`Usage: parser.ts --split <split> (--questions|--chunks|--ingest [--embed])`);
    process.exit(2);
  }

  const raw = await loadSplit(split);
  const questions = extractQuestions(raw);
  const chunks = extractSessionChunks(raw);

  console.error(`[parser] split:    ${split}`);
  console.error(`[parser] qs:       ${questions.length}`);
  console.error(`[parser] chunks:   ${chunks.length}`);
  const byCat = new Map<string, number>();
  for (const q of questions) {
    const k = q.is_abstention ? `${q.base_category}_abs` : q.base_category;
    byCat.set(k, (byCat.get(k) ?? 0) + 1);
  }
  console.error(`[parser] by type:  ${JSON.stringify(Object.fromEntries(byCat))}`);

  if (mode === "questions") {
    for (const q of questions) process.stdout.write(JSON.stringify(q) + "\n");
  } else if (mode === "chunks") {
    for (const c of chunks) process.stdout.write(JSON.stringify(c) + "\n");
  } else if (mode === "ingest") {
    await ingest(chunks, { embed: process.argv.includes("--embed") });
  }
}

if (process.argv[1] && resolve(process.argv[1]) === __filename) {
  main().catch((e) => {
    console.error("[parser] ERROR:", e instanceof Error ? e.message : e);
    process.exit(1);
  });
}
