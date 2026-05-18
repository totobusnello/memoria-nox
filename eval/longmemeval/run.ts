/**
 * run.ts — drive LongMemEval questions end-to-end against memoria-nox.
 *
 * Pipeline per question:
 *   1. Ingest haystack_sessions into an isolated eval.db (one chunk per session).
 *   2. Issue the question against nox-mem hybrid search (FTS5 + Gemini semantic + RRF).
 *      Default --cli (shell out, isolated env). Optional --api for HTTP.
 *   3. Format a prompt = top-K retrieved chunks + question_date + question.
 *   4. Call the generator LLM (default gemini-2.5-flash-lite per CLAUDE.md §3;
 *      override via LONGMEMEVAL_GENERATOR=gemini-2.5-flash|gpt-4o|...).
 *   5. Record hypothesis: {question_id, gold_answer, generated_answer,
 *      retrieved_chunk_ids, retrieval_ms, generation_ms, ...}.
 *
 * Scoring (LLM-as-judge) happens in score.ts on the recorded hypotheses.
 *
 * Modes:
 *   --cli    : shell out to `nox-mem search "<q>" --json --limit K --db <eval.db>` (default)
 *   --api    : POST http://127.0.0.1:${NOX_API_PORT}/api/search {query, limit, db}
 *
 * Sampling: stratified per (base_category, _abs?) cell, seed=42. Default n=10 (dry-run).
 *
 * Output (JSON to stdout): { meta:{...}, records:[{...}] }
 *
 * SAFETY:
 *   - Refuses if resolved DB path looks like the production nox-mem.db.
 *   - --cli is the default (does not touch the prod HTTP API logs).
 *   - Embedding + generator hit live APIs. Do not run --full without an env
 *     check and a budget confirmation.
 *
 * SCAFFOLD NOTES (mirrors Q1 LoCoMo):
 *   - Ingest path emits a stub for the dry-run (validates plumbing only).
 *   - Generator call has a `--no-llm` flag that skips the actual LLM call and
 *     records a placeholder. Useful for testing the parser+sampler+IO pipeline
 *     in a sandbox without burning Gemini quota.
 *   - The real generator wiring (Gemini / OpenAI) reads env keys; ENOENT or
 *     missing key is captured per record (not fatal).
 */

import { spawn } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { extractQuestions, extractSessionChunks, loadSplit, type QARecord, type SessionChunk } from "./parser.js";

const __filename = fileURLToPath(import.meta.url);
const HERE = dirname(__filename);
const EVAL_DB = resolve(HERE, "eval.db");

const DEFAULT_GENERATOR = "gemini-2.5-flash-lite";

interface SearchHit {
  chunk_id: number | string;
  score?: number;
  match_type?: string;
  text?: string;
}

interface RunRecord {
  question_id: string;
  question_type: string;
  base_category: string;
  is_abstention: boolean;
  question: string;
  gold_answer: string;
  question_date: string;
  haystack_session_count: number;
  answer_session_ids: string[];
  retrieved_chunk_ids: string[];
  retrieved_scores: number[];
  retrieved_session_ids: string[];   // parsed back from chunk_id
  retrieval_ms: number;
  generated_answer: string;
  generator_model: string;
  generation_ms: number;
  mode: "cli" | "api";
  timestamp_iso: string;
  error?: string;
}

// ------------------------------------------------------------------
// Sampling — deterministic stratified per (base_category, _abs?) cell
// ------------------------------------------------------------------

function seededShuffle<T>(arr: T[], seed: number): T[] {
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
  const byCell = new Map<string, QARecord[]>();
  for (const q of questions) {
    const cell = `${q.base_category}${q.is_abstention ? "_abs" : ""}`;
    if (!byCell.has(cell)) byCell.set(cell, []);
    byCell.get(cell)!.push(q);
  }
  const cells = Array.from(byCell.keys()).sort();
  const perCell = Math.max(1, Math.floor(n / cells.length));
  const out: QARecord[] = [];
  cells.forEach((c, idx) => {
    const pool = seededShuffle(byCell.get(c)!, seed + idx + 1);
    out.push(...pool.slice(0, perCell));
  });
  // If rounding left us short, fill from the remaining pool deterministically.
  if (out.length < n) {
    const seen = new Set(out.map((q) => q.question_id));
    const allShuffled = seededShuffle(questions, seed);
    for (const q of allShuffled) {
      if (out.length >= n) break;
      if (!seen.has(q.question_id)) {
        out.push(q);
        seen.add(q.question_id);
      }
    }
  }
  return out.slice(0, n);
}

// ------------------------------------------------------------------
// Safety
// ------------------------------------------------------------------

function refuseIfProdDb(db: string): void {
  const norm = resolve(db);
  if (
    norm.endsWith("/nox-mem.db") &&
    !norm.includes("/eval/longmemeval/") &&
    !norm.includes("/.workspace/")
  ) {
    throw new Error(`refuse to query production DB: ${norm}`);
  }
}

// ------------------------------------------------------------------
// Ingest per-question (isolated, transient) — SCAFFOLD STUB
// ------------------------------------------------------------------

async function ingestHaystackForQuestion(
  chunks: SessionChunk[],
  opts: { db: string; embed: boolean }
): Promise<void> {
  refuseIfProdDb(opts.db);
  // Real implementation:
  //   1. Open eval.db (better-sqlite3) with FTS5 + sqlite-vec loaded.
  //   2. UPSERT chunks (chunk_id, text) into chunks table.
  //   3. If opts.embed: shell out `nox-mem vectorize --db <eval.db>` after
  //      all batch chunks are in (single call, not per-question, to avoid
  //      Gemini RPS waste). The harness today batches by RUN, not by
  //      question — so this stub is intentionally a no-op during dry-run.
  // For scaffold we just log the intent.
  if (process.env.LONGMEMEVAL_VERBOSE === "1") {
    console.error(`[ingest] q=${chunks[0]?.question_id ?? "?"} chunks=${chunks.length} embed=${opts.embed}`);
  }
}

// ------------------------------------------------------------------
// Search adapters (CLI / HTTP) — same shape as Q1 LoCoMo
// ------------------------------------------------------------------

async function searchCli(query: string, db: string, limit: number): Promise<{ hits: SearchHit[]; ms: number }> {
  refuseIfProdDb(db);
  const t0 = Date.now();
  return new Promise((resolveP, rejectP) => {
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
  if (!r.ok) throw new Error(`HTTP ${r.status} ${url}: ${await r.text()}`);
  const j = (await r.json()) as { results?: SearchHit[]; hits?: SearchHit[] };
  return { hits: j.results ?? j.hits ?? [], ms };
}

// ------------------------------------------------------------------
// Generator LLM (Gemini default, OpenAI optional)
// ------------------------------------------------------------------

function buildPrompt(q: QARecord, hits: SearchHit[]): string {
  const ctx = hits
    .slice(0, 10)
    .map((h, i) => `--- chunk ${i + 1} (score=${(h.score ?? 0).toFixed(4)}) ---\n${h.text ?? "[no text]"}`)
    .join("\n\n");
  const abstainHint = q.is_abstention
    ? `\nIMPORTANT: if the retrieved context does not contain a confident answer, reply with exactly: I don't know.`
    : "";
  return [
    `You are answering a question based ONLY on the retrieved long-term memory context below.`,
    `Today's date (the user is asking on this date): ${q.question_date}`,
    abstainHint,
    "",
    `Retrieved context:`,
    ctx || "[no context retrieved]",
    "",
    `Question: ${q.question}`,
    `Answer concisely:`,
  ].join("\n");
}

async function callGeminiGenerator(prompt: string, model: string): Promise<{ text: string; ms: number }> {
  const key = process.env.GEMINI_API_KEY ?? process.env.GOOGLE_API_KEY;
  if (!key) throw new Error("GEMINI_API_KEY / GOOGLE_API_KEY not set");
  const m = model.replace(/^gemini\//, "");
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(m)}:generateContent?key=${encodeURIComponent(key)}`;
  const body = {
    contents: [{ role: "user", parts: [{ text: prompt }] }],
    generationConfig: { temperature: 0.0, maxOutputTokens: 256 },
  };
  const t0 = Date.now();
  const r = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const ms = Date.now() - t0;
  if (!r.ok) throw new Error(`Gemini HTTP ${r.status}: ${(await r.text()).slice(0, 300)}`);
  const j = (await r.json()) as {
    candidates?: Array<{ content?: { parts?: Array<{ text?: string }> } }>;
  };
  const text = j.candidates?.[0]?.content?.parts?.map((p) => p.text ?? "").join("") ?? "";
  return { text: text.trim(), ms };
}

async function callOpenAiGenerator(prompt: string, model: string): Promise<{ text: string; ms: number }> {
  const key = process.env.OPENAI_API_KEY;
  if (!key) throw new Error("OPENAI_API_KEY not set");
  const url = "https://api.openai.com/v1/chat/completions";
  const body = {
    model,
    temperature: 0,
    max_tokens: 256,
    messages: [{ role: "user", content: prompt }],
  };
  const t0 = Date.now();
  const r = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json", authorization: `Bearer ${key}` },
    body: JSON.stringify(body),
  });
  const ms = Date.now() - t0;
  if (!r.ok) throw new Error(`OpenAI HTTP ${r.status}: ${(await r.text()).slice(0, 300)}`);
  const j = (await r.json()) as { choices?: Array<{ message?: { content?: string } }> };
  const text = j.choices?.[0]?.message?.content ?? "";
  return { text: text.trim(), ms };
}

async function generate(prompt: string, model: string): Promise<{ text: string; ms: number }> {
  if (/^gpt-/i.test(model)) return callOpenAiGenerator(prompt, model);
  return callGeminiGenerator(prompt, model);
}

// ------------------------------------------------------------------
// Main
// ------------------------------------------------------------------

function arg(name: string, fallback?: string): string | undefined {
  const i = process.argv.indexOf(name);
  if (i < 0) return fallback;
  return process.argv[i + 1] ?? fallback;
}

function sessionIdFromChunk(chunk_id: string): string {
  // chunk_id format = `${question_id}::${session_id}`. Take everything after first "::".
  const idx = chunk_id.indexOf("::");
  return idx >= 0 ? chunk_id.slice(idx + 2) : chunk_id;
}

async function main(): Promise<void> {
  const split = arg("--split", "oracle")!;
  const n = parseInt(arg("--n", "10")!, 10);
  const seed = parseInt(arg("--seed", "42")!, 10);
  const mode: "cli" | "api" = process.argv.includes("--api") ? "api" : "cli";
  const db = arg("--db", EVAL_DB)!;
  const isFull = process.argv.includes("--full");
  const dryRun = !isFull;
  const skipLlm = process.argv.includes("--no-llm");
  const generator = process.env.LONGMEMEVAL_GENERATOR ?? DEFAULT_GENERATOR;
  const limit = parseInt(arg("--limit", "20")!, 10);

  console.error(`[run] split=${split} n=${n} seed=${seed} mode=${mode} db=${db} dryRun=${dryRun} generator=${generator} skipLlm=${skipLlm}`);

  const raw = await loadSplit(split);
  const questions = extractQuestions(raw);
  const chunksAll = extractSessionChunks(raw);
  const chunksByQ = new Map<string, SessionChunk[]>();
  for (const c of chunksAll) {
    if (!chunksByQ.has(c.question_id)) chunksByQ.set(c.question_id, []);
    chunksByQ.get(c.question_id)!.push(c);
  }

  const sample = stratifiedSample(questions, n, seed);
  console.error(`[run] sampled ${sample.length} questions`);

  const records: RunRecord[] = [];
  for (const q of sample) {
    const t0 = new Date().toISOString();
    const rec: RunRecord = {
      question_id: q.question_id,
      question_type: q.question_type,
      base_category: q.base_category,
      is_abstention: q.is_abstention,
      question: q.question,
      gold_answer: q.answer,
      question_date: q.question_date,
      haystack_session_count: q.haystack_session_ids.length,
      answer_session_ids: q.answer_session_ids,
      retrieved_chunk_ids: [],
      retrieved_scores: [],
      retrieved_session_ids: [],
      retrieval_ms: 0,
      generated_answer: "",
      generator_model: generator,
      generation_ms: 0,
      mode,
      timestamp_iso: t0,
    };
    try {
      // 1. Ingest haystack for this question (stub during scaffold).
      await ingestHaystackForQuestion(chunksByQ.get(q.question_id) ?? [], {
        db,
        embed: !dryRun && !skipLlm,
      });

      // 2. Hybrid search.
      const { hits, ms } = mode === "cli"
        ? await searchCli(q.question, db, limit)
        : await searchApi(q.question, db, limit);
      rec.retrieved_chunk_ids = hits.map((h) => String(h.chunk_id));
      rec.retrieved_scores = hits.map((h) => h.score ?? 0);
      rec.retrieved_session_ids = rec.retrieved_chunk_ids.map(sessionIdFromChunk);
      rec.retrieval_ms = ms;

      // 3. Generate.
      if (skipLlm) {
        rec.generated_answer = "[--no-llm placeholder]";
        rec.generation_ms = 0;
      } else {
        const prompt = buildPrompt(q, hits);
        const { text, ms: gms } = await generate(prompt, generator);
        rec.generated_answer = text;
        rec.generation_ms = gms;
      }
    } catch (e) {
      rec.error = e instanceof Error ? e.message : String(e);
      console.error(`[run] error on ${q.question_id}: ${rec.error}`);
    }
    records.push(rec);
  }

  process.stdout.write(JSON.stringify({
    meta: { split, n, seed, mode, dryRun, generator, limit, skipLlm },
    records,
  }, null, 2));
}

if (process.argv[1] && resolve(process.argv[1]) === __filename) {
  main().catch((e) => {
    console.error("[run] FATAL:", e instanceof Error ? e.message : e);
    process.exit(1);
  });
}
