/**
 * run-api.ts — programmatic API wrapper for run.ts + score.ts
 *
 * Exports `runQuestions()` — the callable function version of the per-question
 * pipeline. cli-adapter.ts does a dynamic import of this file to avoid
 * process.argv coupling with the scaffold standalone entrypoints.
 *
 * STAGED (Q2.1): deploy to eval/longmemeval/run-api.ts on VPS.
 *
 * Architecture:
 *   cli-adapter.ts → runQuestions() → searchCli/searchApi (from run.ts)
 *                                   → generate (from run.ts)
 *                                   → callJudge (from score.ts)
 *
 * All protocol logic stays in run.ts / score.ts (DO NOT modify them).
 * This wrapper only adds the interface and bridges the two scaffold files.
 */

import { spawn } from "node:child_process";
import { type QARecord, type SessionChunk } from "./parser.js";
import type { PerQuestionResult } from "./cli-adapter.js";

// ---------------------------------------------------------------------------
// Internal types mirrored from run.ts (kept in sync — do not diverge)
// ---------------------------------------------------------------------------

interface SearchHit {
  chunk_id: number | string;
  score?: number;
  match_type?: string;
  text?: string;
}

interface RunApiOptions {
  db: string;
  judge: string;
  topK: number;
  keywordOnly: boolean;
  retrievalOnly: boolean;
  expansion: boolean;
  seed: number;
  verbose: boolean;
}

// ---------------------------------------------------------------------------
// Safety guard (mirrors run.ts refuseIfProdDb)
// ---------------------------------------------------------------------------

function refuseIfProdDb(db: string): void {
  const { resolve } = require("node:path") as typeof import("node:path");
  const norm = resolve(db);
  if (
    norm.endsWith("/nox-mem.db") &&
    !norm.includes("/eval/longmemeval/") &&
    !norm.includes("/.workspace/")
  ) {
    throw new Error(`refuse to query production DB: ${norm}`);
  }
}

// ---------------------------------------------------------------------------
// Search (CLI mode — default, isolated from prod API logs)
// ---------------------------------------------------------------------------

async function searchCli(
  query: string,
  db: string,
  limit: number,
  keywordOnly: boolean,
  expansion: boolean,
): Promise<{ hits: SearchHit[]; ms: number }> {
  refuseIfProdDb(db);
  const t0 = Date.now();
  return new Promise((res, rej) => {
    const cmd = process.env.NOX_MEM_BIN ?? "nox-mem";
    const args = ["search", query, "--json", "--limit", String(limit), "--db", db];
    if (keywordOnly) args.push("--no-hybrid");
    if (expansion) args.push("--expansion");
    const child = spawn(cmd, args, { env: process.env });
    let out = "";
    let err = "";
    child.stdout.on("data", (b: Buffer) => (out += b.toString()));
    child.stderr.on("data", (b: Buffer) => (err += b.toString()));
    child.on("error", (e: Error) => rej(e));
    child.on("close", (code: number | null) => {
      const ms = Date.now() - t0;
      if (code !== 0) {
        return rej(new Error(`nox-mem search exit ${code}: ${err.slice(0, 300)}`));
      }
      try {
        const j = JSON.parse(out);
        const hits = (j.results ?? j.hits ?? j) as SearchHit[];
        res({ hits, ms });
      } catch (e) {
        rej(new Error(`nox-mem JSON parse: ${(e as Error).message}; raw=${out.slice(0, 200)}`));
      }
    });
  });
}

// ---------------------------------------------------------------------------
// Generator (Gemini default, OpenAI optional) — mirrors run.ts
// ---------------------------------------------------------------------------

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
    method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body),
  });
  const ms = Date.now() - t0;
  if (!r.ok) throw new Error(`Gemini HTTP ${r.status}: ${(await r.text()).slice(0, 300)}`);
  const j = (await r.json()) as { candidates?: Array<{ content?: { parts?: Array<{ text?: string }> } }> };
  const text = j.candidates?.[0]?.content?.parts?.map((p) => p.text ?? "").join("") ?? "";
  return { text: text.trim(), ms };
}

async function callOpenAiGenerator(prompt: string, model: string): Promise<{ text: string; ms: number }> {
  const key = process.env.OPENAI_API_KEY;
  if (!key) throw new Error("OPENAI_API_KEY not set");
  const body = {
    model, temperature: 0, max_tokens: 256,
    messages: [{ role: "user", content: prompt }],
  };
  const t0 = Date.now();
  const r = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: { "content-type": "application/json", authorization: `Bearer ${key}` },
    body: JSON.stringify(body),
  });
  const ms = Date.now() - t0;
  if (!r.ok) throw new Error(`OpenAI HTTP ${r.status}: ${(await r.text()).slice(0, 300)}`);
  const j = (await r.json()) as { choices?: Array<{ message?: { content?: string } }> };
  return { text: (j.choices?.[0]?.message?.content ?? "").trim(), ms };
}

// ---------------------------------------------------------------------------
// Judge — mirrors score.ts judge logic
// ---------------------------------------------------------------------------

function judgePrompt(q: QARecord, generatedAnswer: string): string {
  if (q.is_abstention) {
    return [
      `You are evaluating whether a chat assistant correctly REFUSED to answer a question`,
      `for which the long-term memory does not contain enough information.`,
      ``,
      `Question: ${q.question}`,
      `Gold answer (what an honest refusal looks like): "${q.answer}"`,
      `Assistant's generated answer: "${generatedAnswer}"`,
      ``,
      `Reply with a JSON object: {"correct": true|false, "rationale": "<1 sentence>"}.`,
      `"correct": true iff the assistant clearly refused to answer.`,
    ].join("\n");
  }
  return [
    `You are evaluating whether a chat assistant's answer is correct given a gold answer.`,
    `Be lenient on phrasing, but strict on factual content.`,
    ``,
    `Question: ${q.question}`,
    `Gold answer: "${q.answer}"`,
    `Assistant's generated answer: "${generatedAnswer}"`,
    ``,
    `Reply with a JSON object: {"correct": true|false, "rationale": "<1 sentence>"}.`,
    `"correct": true iff the answer is factually equivalent to the gold.`,
  ].join("\n");
}

function parseJudgeRaw(raw: string, ms: number): { correct: boolean | null; rationale?: string; ms: number } {
  try {
    const cleaned = raw.replace(/^```(?:json)?\s*/i, "").replace(/```\s*$/i, "").trim();
    const obj = JSON.parse(cleaned) as { correct?: unknown; rationale?: string };
    if (typeof obj.correct === "boolean") return { correct: obj.correct, rationale: obj.rationale, ms };
    return { correct: null, ms };
  } catch {
    const m = raw.match(/"correct"\s*:\s*(true|false)/i);
    if (m) return { correct: m[1].toLowerCase() === "true", ms };
    return { correct: null, ms };
  }
}

async function callJudge(
  q: QARecord,
  generatedAnswer: string,
  judgeModel: string,
): Promise<{ correct: boolean | null; rationale?: string; ms: number }> {
  const prompt = judgePrompt(q, generatedAnswer);
  if (/^gpt-/i.test(judgeModel)) {
    const key = process.env.OPENAI_API_KEY;
    if (!key) throw new Error("OPENAI_API_KEY not set for judge");
    const body = {
      model: judgeModel, temperature: 0, max_tokens: 256,
      response_format: { type: "json_object" as const },
      messages: [{ role: "user", content: prompt }],
    };
    const t0 = Date.now();
    const r = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: { "content-type": "application/json", authorization: `Bearer ${key}` },
      body: JSON.stringify(body),
    });
    const ms = Date.now() - t0;
    if (!r.ok) return { correct: null, ms };
    const j = (await r.json()) as { choices?: Array<{ message?: { content?: string } }> };
    return parseJudgeRaw(j.choices?.[0]?.message?.content ?? "", ms);
  }
  // Gemini judge
  const key = process.env.GEMINI_API_KEY ?? process.env.GOOGLE_API_KEY;
  if (!key) throw new Error("GEMINI_API_KEY not set for judge");
  const m = judgeModel.replace(/^gemini\//, "");
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(m)}:generateContent?key=${encodeURIComponent(key)}`;
  const body = {
    contents: [{ role: "user", parts: [{ text: prompt }] }],
    generationConfig: { temperature: 0.0, responseMimeType: "application/json", maxOutputTokens: 256 },
  };
  const t0 = Date.now();
  const r = await fetch(url, {
    method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body),
  });
  const ms = Date.now() - t0;
  if (!r.ok) return { correct: null, ms };
  const j = (await r.json()) as { candidates?: Array<{ content?: { parts?: Array<{ text?: string }> } }> };
  const raw = j.candidates?.[0]?.content?.parts?.map((p) => p.text ?? "").join("") ?? "";
  return parseJudgeRaw(raw, ms);
}

// ---------------------------------------------------------------------------
// Session ID extraction (chunk_id = `${question_id}::${session_id}`)
// ---------------------------------------------------------------------------

function sessionIdFromChunk(chunk_id: string): string {
  const idx = chunk_id.indexOf("::");
  return idx >= 0 ? chunk_id.slice(idx + 2) : chunk_id;
}

// ---------------------------------------------------------------------------
// Main exported function
// ---------------------------------------------------------------------------

/**
 * Run the per-question pipeline for all questions in `questions`.
 *
 * Per-question pipeline:
 *   1. Ingest haystack sessions into eval DB (CLI bridge; stub during dry-run).
 *   2. Hybrid search (FTS5 + semantic + RRF via nox-mem CLI).
 *   3. Generate answer (Gemini flash-lite default, or judge-model family).
 *   4. Judge (LLM-as-judge, binary correct/incorrect).
 *
 * Returns per-question results for cli-adapter.ts to aggregate.
 */
export async function runQuestions(
  questions: QARecord[],
  chunksByQ: Map<string, SessionChunk[]>,
  opts: RunApiOptions,
): Promise<PerQuestionResult[]> {
  const generatorModel = process.env.LONGMEMEVAL_GENERATOR ?? "gemini-2.5-flash-lite";
  const results: PerQuestionResult[] = [];

  for (const q of questions) {
    const rec: PerQuestionResult = {
      question_id: q.question_id,
      question_type: q.question_type,
      base_category: q.base_category,
      is_abstention: q.is_abstention,
      verdict: "skip",
      retrieval_session_hit: false,
      retrieval_ms: 0,
      generation_ms: 0,
      judge_ms: 0,
    };

    try {
      // 1. Ingest haystack (best-effort; eval DB set up by caller or download.ts)
      // The actual ingest is handled by the VPS-side nox-mem ingest CLI
      // before running this; this function focuses on retrieve-generate-judge.

      // 2. Search
      const { hits, ms: rms } = await searchCli(
        q.question, opts.db, opts.topK,
        opts.keywordOnly, opts.expansion,
      );
      rec.retrieval_ms = rms;
      const retrievedSessionIds = hits.map((h) => sessionIdFromChunk(String(h.chunk_id)));
      const answerSet = new Set(q.answer_session_ids);
      rec.retrieval_session_hit = retrievedSessionIds.some((s) => answerSet.has(s));

      if (opts.verbose) {
        process.stderr.write(
          `[run-api] q=${q.question_id} retrieved=${hits.length} hit=${rec.retrieval_session_hit} rms=${rms}\n`
        );
      }

      if (opts.retrievalOnly) {
        // Skip generation + judge; record retrieval hit as proxy verdict.
        rec.verdict = rec.retrieval_session_hit ? "correct" : "incorrect";
        rec.judge_rationale = "--retrieval-only: verdict = session hit";
        results.push(rec);
        continue;
      }

      // 3. Generate
      const prompt = buildPrompt(q, hits);
      const t0gen = Date.now();
      let generatedAnswer: string;
      if (/^gpt-/i.test(generatorModel)) {
        const { text } = await callOpenAiGenerator(prompt, generatorModel);
        generatedAnswer = text;
      } else {
        const { text } = await callGeminiGenerator(prompt, generatorModel);
        generatedAnswer = text;
      }
      rec.generation_ms = Date.now() - t0gen;

      // 4. Judge
      const jr = await callJudge(q, generatedAnswer, opts.judge);
      rec.judge_ms = jr.ms;
      rec.judge_rationale = jr.rationale;
      rec.verdict = jr.correct === null ? "judge_error"
        : jr.correct ? "correct" : "incorrect";

      if (opts.verbose) {
        process.stderr.write(
          `[run-api] q=${q.question_id} verdict=${rec.verdict} gms=${rec.generation_ms} jms=${rec.judge_ms}\n`
        );
      }
    } catch (e) {
      rec.error = e instanceof Error ? e.message : String(e);
      rec.verdict = "judge_error";
      process.stderr.write(`[run-api] error q=${q.question_id}: ${rec.error}\n`);
    }

    results.push(rec);
  }

  return results;
}

export default { runQuestions };
