/**
 * parser.ts — parse LoCoMo dataset into eval-ready tuples.
 *
 * Two outputs:
 *   1. Question records  → (question_id, sample_id, category, question, gold_chunk_ids[])
 *   2. Turn records      → (chunk_id, sample_id, dia_id, session_id, speaker, text)
 *
 * Schema source: snap-research/locomo data/locomo10.json (verified 2026-05-04).
 * Each entry of the top-level list has:
 *   sample_id        : string
 *   qa               : [{question, answer | adversarial_answer, evidence:["D1:3",...], category:int}]
 *   conversation     : { speaker_a, speaker_b, session_N:[{speaker, dia_id, text}], session_N_date_time:str }
 *
 * Categories: 1=single-hop, 2=multi-hop, 3=temporal, 4=open-domain, 5=adversarial.
 *
 * Usage:
 *   npx tsx eval/locomo/parser.ts --questions          # dump questions JSONL
 *   npx tsx eval/locomo/parser.ts --turns              # dump turns JSONL
 *   npx tsx eval/locomo/parser.ts --ingest             # populate eval.db (chunks + FTS5)
 *   npx tsx eval/locomo/parser.ts --ingest --embed     # also vectorize via Gemini
 *
 * Embedding is OFF by default; pass --embed to call nox-mem vectorize against
 * the eval.db (requires GEMINI_API_KEY env).
 */

import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const __filename = fileURLToPath(import.meta.url);
const HERE = dirname(__filename);
const DATA_FILE = resolve(HERE, "data", "locomo10.json");
const EVAL_DB = resolve(HERE, "eval.db");

const CATEGORY_NAMES: Record<number, string> = {
  1: "single-hop",
  2: "multi-hop",
  3: "temporal",
  4: "open-domain",
  5: "adversarial",
};

export interface Turn {
  chunk_id: string;       // `${sample_id}::${dia_id}` — namespaced to avoid collision
  sample_id: string;
  session_id: string;     // e.g. "session_1"
  dia_id: string;
  speaker: string;
  text: string;
}

export interface QARecord {
  question_id: string;    // `${sample_id}::q${idx}`
  sample_id: string;
  category: number;
  category_name: string;
  question: string;
  answer: string;
  gold_chunk_ids: string[];   // resolved into chunk-id namespace
}

interface RawTurn {
  speaker?: string;
  dia_id?: string;
  text?: string;
}

interface RawQA {
  question: string;
  answer?: string;
  adversarial_answer?: string;
  evidence?: string[];
  category?: number;
}

interface RawConversation {
  sample_id: string;
  conversation: Record<string, unknown>;
  qa?: RawQA[];
}

export async function loadCorpus(path = DATA_FILE): Promise<RawConversation[]> {
  const txt = await readFile(path, "utf8");
  const j = JSON.parse(txt);
  if (!Array.isArray(j)) throw new Error("Expected top-level JSON array (list of conversations)");
  return j as RawConversation[];
}

export function extractTurns(corpus: RawConversation[]): Turn[] {
  const out: Turn[] = [];
  for (const conv of corpus) {
    const sid = conv.sample_id;
    for (const [k, v] of Object.entries(conv.conversation)) {
      if (!k.startsWith("session_")) continue;
      if (k.endsWith("_date_time")) continue;
      if (!Array.isArray(v)) continue;
      for (const t of v as RawTurn[]) {
        if (!t || typeof t !== "object") continue;
        const dia = t.dia_id;
        const text = t.text;
        if (!dia || !text) continue;
        out.push({
          chunk_id: `${sid}::${dia}`,
          sample_id: sid,
          session_id: k,
          dia_id: dia,
          speaker: t.speaker ?? "",
          text: text,
        });
      }
    }
  }
  return out;
}

export function extractQuestions(corpus: RawConversation[]): QARecord[] {
  const out: QARecord[] = [];
  for (const conv of corpus) {
    const sid = conv.sample_id;
    const qa = conv.qa ?? [];
    qa.forEach((q, i) => {
      const cat = q.category;
      if (!cat || !CATEGORY_NAMES[cat]) return;
      const ev = q.evidence;
      if (!Array.isArray(ev) || ev.length === 0) return;
      const gold = ev.filter((e) => typeof e === "string").map((e) => `${sid}::${e}`);
      if (gold.length === 0) return;
      out.push({
        question_id: `${sid}::q${i}`,
        sample_id: sid,
        category: cat,
        category_name: CATEGORY_NAMES[cat],
        question: q.question,
        answer: String(q.answer ?? q.adversarial_answer ?? ""),
        gold_chunk_ids: gold,
      });
    });
  }
  return out;
}

/**
 * Ingest turns into eval.db using the nox-mem CLI.
 *
 * SAFEGUARD: refuse if eval.db path resolves to anything containing
 * "nox-mem.db" (production DB). Belt-and-braces — the CLI's own
 * OPENCLAW_WORKSPACE should already isolate, but we double-check.
 */
async function ingest(turns: Turn[], opts: { embed: boolean }): Promise<void> {
  if (EVAL_DB.includes("nox-mem.db") || EVAL_DB === "/root/.openclaw/workspace/tools/nox-mem/nox-mem.db") {
    throw new Error(`refuse to write to production DB: ${EVAL_DB}`);
  }
  console.error(`[ingest] target: ${EVAL_DB}`);
  console.error(`[ingest] turns: ${turns.length}`);
  console.error("[ingest] NOTE: this scaffold *describes* ingestion; full ingest path is");
  console.error("[ingest]       deferred to a follow-up commit so the dry-run can validate");
  console.error("[ingest]       the question/turn parsing in isolation first.");
  console.error("[ingest] To wire the actual ingest, write a tmp markdown file per turn or");
  console.error("[ingest] use the nox-mem CLI's batch-ingest path with --db=<eval.db>.");

  if (opts.embed) {
    console.error("[ingest] --embed requested — would call:");
    console.error(`[ingest]   nox-mem vectorize --db ${EVAL_DB}`);
  }

  // The minimal stub: emit ingest-ready JSONL on stdout so a separate tool can
  // pipe it into nox-mem. This is enough to validate parser correctness.
  for (const t of turns.slice(0, 5)) {
    process.stdout.write(JSON.stringify(t) + "\n");
  }
  if (turns.length > 5) {
    console.error(`[ingest] (only first 5 emitted to stdout for sanity; ${turns.length} total parsed)`);
  }
}

async function main(): Promise<void> {
  const argv = process.argv.slice(2);
  const mode =
    argv.includes("--questions") ? "questions"
    : argv.includes("--turns") ? "turns"
    : argv.includes("--ingest") ? "ingest"
    : null;
  if (!mode) {
    console.error("Usage: parser.ts [--questions | --turns | --ingest [--embed]]");
    process.exit(2);
  }

  const corpus = await loadCorpus();
  const turns = extractTurns(corpus);
  const questions = extractQuestions(corpus);

  console.error(`[parser] corpus: ${corpus.length} conversations`);
  console.error(`[parser] turns:  ${turns.length}`);
  console.error(`[parser] qas:    ${questions.length}`);
  const byCat = new Map<string, number>();
  for (const q of questions) {
    byCat.set(q.category_name, (byCat.get(q.category_name) ?? 0) + 1);
  }
  console.error(`[parser] by category: ${JSON.stringify(Object.fromEntries(byCat))}`);

  if (mode === "questions") {
    for (const q of questions) process.stdout.write(JSON.stringify(q) + "\n");
  } else if (mode === "turns") {
    for (const t of turns) process.stdout.write(JSON.stringify(t) + "\n");
  } else if (mode === "ingest") {
    await ingest(turns, { embed: argv.includes("--embed") });
  }
}

// Only run if invoked directly (not when imported by run.ts).
if (process.argv[1] && resolve(process.argv[1]) === __filename) {
  main().catch((e) => {
    console.error("[parser] ERROR:", e instanceof Error ? e.message : e);
    process.exit(1);
  });
}
