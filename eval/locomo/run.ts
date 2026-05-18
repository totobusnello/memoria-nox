/**
 * run.ts — issue LoCoMo questions against memoria-nox and collect top-K chunks.
 *
 * Modes:
 *   --cli   : shell out to `nox-mem search "<q>" --json --limit 20 --db <eval.db>`
 *   --api   : POST http://127.0.0.1:${NOX_API_PORT}/api/search   {query, limit, db}
 *
 * Sampling: stratified per category, seed=42. Default n=10 (dry-run).
 *
 * Output: JSON array of { question_id, question, category, gold_chunk_ids,
 *                         retrieved_chunk_ids, retrieved_scores, retrieval_ms,
 *                         timestamp_iso }.
 *
 * SAFETY:
 *   - Refuses to run if the resolved DB path looks like the production nox-mem.db.
 *   - Default mode is --cli (does not touch the prod HTTP API).
 *   - Embedding / search invokes the real Gemini API; do not run --full without
 *     a key + budget confirmation.
 */

import { spawn } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { extractQuestions, loadCorpus, type QARecord } from "./parser.js";

const __filename = fileURLToPath(import.meta.url);
const HERE = dirname(__filename);
const EVAL_DB = resolve(HERE, "eval.db");

interface SearchHit {
  chunk_id: number | string;
  score?: number;
  match_type?: string;
  text?: string;
}

interface RunRecord {
  question_id: string;
  sample_id: string;
  category: number;
  category_name: string;
  question: string;
  gold_chunk_ids: string[];
  retrieved_chunk_ids: string[];
  retrieved_scores: number[];
  retrieval_ms: number;
  mode: "cli" | "api";
  timestamp_iso: string;
  error?: string;
}

// ------------------------------------------------------------------
// Sampling — deterministic stratified per category
// ------------------------------------------------------------------

function seededShuffle<T>(arr: T[], seed: number): T[] {
  // Linear congruential generator. Fine for shuffle determinism.
  const out = arr.slice();
  let s = seed >>> 0;
  for (let i = out.length - 1; i > 0; i--) {
    s = (s * 1664525 + 1013904223) >>> 0;
    const j = s % (i + 1);
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

function stratifiedSample(questions: QARecord[], n: number, seed = 42): QARecord[] {
  const byCat = new Map<number, QARecord[]>();
  for (const q of questions) {
    if (!byCat.has(q.category)) byCat.set(q.category, []);
    byCat.get(q.category)!.push(q);
  }
  const cats = Array.from(byCat.keys()).sort((a, b) => a - b);
  const perCat = Math.max(1, Math.floor(n / cats.length));
  const out: QARecord[] = [];
  for (const c of cats) {
    const pool = seededShuffle(byCat.get(c)!, seed + c);
    out.push(...pool.slice(0, perCat));
  }
  return out.slice(0, n);
}

// ------------------------------------------------------------------
// Search adapters
// ------------------------------------------------------------------

function refuseIfProdDb(db: string): void {
  const norm = resolve(db);
  if (
    norm.endsWith("/nox-mem.db") &&
    !norm.includes("/eval/locomo/") &&
    !norm.includes("/.workspace/")
  ) {
    throw new Error(`refuse to query production DB: ${norm}`);
  }
}

async function searchCli(query: string, db: string, limit: number): Promise<{ hits: SearchHit[]; ms: number }> {
  refuseIfProdDb(db);
  const t0 = Date.now();
  return new Promise((resolveP, rejectP) => {
    // The harness assumes a `nox-mem` binary is on PATH (npm-installed bin →
    // dist/index.js). For a fully isolated dev box, swap to:
    //   const cmd = "node"; const args = ["/abs/path/to/dist/index.js", "search", ...];
    const cmd = process.env.NOX_MEM_BIN ?? "nox-mem";
    const args = ["search", query, "--json", "--limit", String(limit), "--db", db];
    const child = spawn(cmd, args, { env: process.env });
    let out = "";
    let err = "";
    child.stdout.on("data", (b) => (out += b.toString()));
    child.stderr.on("data", (b) => (err += b.toString()));
    child.on("error", (e) => rejectP(e));
    child.on("close", (code) => {
      const ms = Date.now() - t0;
      if (code !== 0) {
        return rejectP(new Error(`nox-mem exit ${code}: ${err.slice(0, 400)}`));
      }
      try {
        const j = JSON.parse(out);
        const hits = (j.results ?? j.hits ?? j) as SearchHit[];
        resolveP({ hits, ms });
      } catch (e) {
        rejectP(new Error(`nox-mem JSON parse failed: ${(e as Error).message}; raw=${out.slice(0, 200)}`));
      }
    });
  });
}

async function searchApi(query: string, db: string, limit: number): Promise<{ hits: SearchHit[]; ms: number }> {
  refuseIfProdDb(db);
  const port = process.env.NOX_API_PORT ?? "18802";
  const url = `http://127.0.0.1:${port}/api/search`;
  const t0 = Date.now();
  const r = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ query, limit, db }),
  });
  const ms = Date.now() - t0;
  if (!r.ok) {
    throw new Error(`HTTP ${r.status} ${url}: ${await r.text()}`);
  }
  const j = (await r.json()) as { results?: SearchHit[]; hits?: SearchHit[] };
  return { hits: j.results ?? j.hits ?? [], ms };
}

// ------------------------------------------------------------------
// Main
// ------------------------------------------------------------------

function arg(name: string, fallback?: string): string | undefined {
  const i = process.argv.indexOf(name);
  if (i < 0) return fallback;
  return process.argv[i + 1] ?? fallback;
}

async function main(): Promise<void> {
  const n = parseInt(arg("--n", "10")!, 10);
  const seed = parseInt(arg("--seed", "42")!, 10);
  const mode: "cli" | "api" = process.argv.includes("--api") ? "api" : "cli";
  const db = arg("--db", EVAL_DB)!;
  const isFull = process.argv.includes("--full");
  const dryRun = !isFull;   // dry-run is the default; --full opts in to a real measurement

  console.error(`[run] n=${n} seed=${seed} mode=${mode} db=${db} dryRun=${dryRun}`);

  const corpus = await loadCorpus();
  const questions = extractQuestions(corpus);
  const sample = stratifiedSample(questions, n, seed);
  console.error(`[run] sampled ${sample.length} questions`);

  const records: RunRecord[] = [];
  for (const q of sample) {
    const rec: RunRecord = {
      question_id: q.question_id,
      sample_id: q.sample_id,
      category: q.category,
      category_name: q.category_name,
      question: q.question,
      gold_chunk_ids: q.gold_chunk_ids,
      retrieved_chunk_ids: [],
      retrieved_scores: [],
      retrieval_ms: 0,
      mode,
      timestamp_iso: new Date().toISOString(),
    };
    try {
      const { hits, ms } = mode === "cli"
        ? await searchCli(q.question, db, 20)
        : await searchApi(q.question, db, 20);
      rec.retrieved_chunk_ids = hits.map((h) => String(h.chunk_id));
      rec.retrieved_scores = hits.map((h) => h.score ?? 0);
      rec.retrieval_ms = ms;
    } catch (e) {
      rec.error = e instanceof Error ? e.message : String(e);
      console.error(`[run] error on ${q.question_id}: ${rec.error}`);
    }
    records.push(rec);
  }

  process.stdout.write(JSON.stringify({ meta: { n, seed, mode, dryRun }, records }, null, 2));
}

if (process.argv[1] && resolve(process.argv[1]) === __filename) {
  main().catch((e) => {
    console.error("[run] FATAL:", e instanceof Error ? e.message : e);
    process.exit(1);
  });
}
