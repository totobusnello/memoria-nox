/**
 * score.ts — score LongMemEval run.ts output via LLM-as-judge → task accuracy.
 *
 * Metric model (paper §4.2):
 *   For each question, an LLM judge sees (question, gold_answer, generated_answer)
 *   and returns a binary verdict {correct: true|false}. Per-question accuracy is
 *   that verdict; overall accuracy is the mean.
 *
 *   Abstention questions (`_abs` suffix): judge prompt is swapped so it scores
 *   "correct iff the model refused to answer" (matches "I don't know" / "no info"
 *   patterns rather than the gold answer string).
 *
 * Aggregation:
 *   - Overall accuracy (mean across questions, errors excluded with a note).
 *   - Per base_category accuracy.
 *   - Per `_abs` variant accuracy (separately, since semantics differ).
 *   - Wilson 95% binomial CI (--ci flag) — same formula as Q1 LoCoMo.
 *   - Diagnostic: retrieval_session_hit = is any retrieved_session_id in
 *     answer_session_ids? Useful for separating retrieval vs generation failures.
 *
 * Judge selection via env:
 *   LONGMEMEVAL_JUDGE=gpt-4o          (paper-default, OPENAI_API_KEY)
 *   LONGMEMEVAL_JUDGE=gemini-2.5-pro  (secondary)
 *   LONGMEMEVAL_JUDGE=gemini-2.5-flash (dry-run default — cheapest)
 *
 * Usage:
 *   npx tsx eval/longmemeval/score.ts eval/longmemeval/dry-run-sample.json
 *   npx tsx eval/longmemeval/score.ts full-run.gpt4o.json --ci
 *   npx tsx eval/longmemeval/score.ts run.json --dry-judge   # no LLM call, mark all unknown (for plumbing tests)
 *
 * SCAFFOLD NOTE: like Q1's score.ts, when the run was produced with --no-llm
 * (generated_answer == "[--no-llm placeholder]"), score.ts marks the verdict as
 * "skip" (not correct, not incorrect, excluded from accuracy denominator).
 */

import { readFile } from "node:fs/promises";

const DEFAULT_JUDGE = "gemini-2.5-flash";

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
  retrieved_session_ids: string[];
  retrieved_scores: number[];
  retrieval_ms: number;
  generated_answer: string;
  generator_model: string;
  generation_ms: number;
  mode: string;
  timestamp_iso: string;
  error?: string;
}

interface RunFile {
  meta: { split: string; n: number; seed: number; mode: string; dryRun: boolean; generator: string; limit: number; skipLlm: boolean };
  records: RunRecord[];
}

interface ScoredRecord extends RunRecord {
  verdict: "correct" | "incorrect" | "skip" | "judge_error";
  judge_model: string;
  judge_rationale?: string;
  judge_ms: number;
  retrieval_session_hit: boolean;
}

// ------------------------------------------------------------------
// Judge prompt (paper-aligned)
// ------------------------------------------------------------------

function judgePrompt(rec: RunRecord): string {
  if (rec.is_abstention) {
    return [
      `You are evaluating whether a chat assistant correctly REFUSED to answer a question`,
      `for which the long-term memory does not contain enough information.`,
      ``,
      `Question: ${rec.question}`,
      `Gold answer (what an honest refusal looks like): "${rec.gold_answer}"`,
      `Assistant's generated answer: "${rec.generated_answer}"`,
      ``,
      `Reply with a JSON object: {"correct": true|false, "rationale": "<1 sentence>"}.`,
      `"correct": true iff the assistant clearly refused to answer (e.g. "I don't know",`,
      `"no information about that in memory", a clear non-commitment). "correct": false`,
      `if the assistant fabricated a specific answer.`,
    ].join("\n");
  }
  return [
    `You are evaluating whether a chat assistant's answer is correct given a gold answer.`,
    `Be lenient on phrasing, but strict on factual content.`,
    ``,
    `Question: ${rec.question}`,
    `Gold answer: "${rec.gold_answer}"`,
    `Assistant's generated answer: "${rec.generated_answer}"`,
    ``,
    `Reply with a JSON object: {"correct": true|false, "rationale": "<1 sentence>"}.`,
    `"correct": true iff the assistant's answer is factually equivalent to the gold answer.`,
  ].join("\n");
}

// ------------------------------------------------------------------
// Judge LLM call (Gemini or OpenAI)
// ------------------------------------------------------------------

interface JudgeResult { correct: boolean | null; rationale?: string; ms: number; raw: string; }

async function callGeminiJudge(prompt: string, model: string): Promise<JudgeResult> {
  const key = process.env.GEMINI_API_KEY ?? process.env.GOOGLE_API_KEY;
  if (!key) throw new Error("GEMINI_API_KEY / GOOGLE_API_KEY not set for judge");
  const m = model.replace(/^gemini\//, "");
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(m)}:generateContent?key=${encodeURIComponent(key)}`;
  const body = {
    contents: [{ role: "user", parts: [{ text: prompt }] }],
    generationConfig: { temperature: 0.0, responseMimeType: "application/json", maxOutputTokens: 256 },
  };
  const t0 = Date.now();
  const r = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const ms = Date.now() - t0;
  if (!r.ok) {
    const txt = (await r.text()).slice(0, 300);
    return { correct: null, ms, raw: `HTTP ${r.status}: ${txt}` };
  }
  const j = (await r.json()) as { candidates?: Array<{ content?: { parts?: Array<{ text?: string }> } }> };
  const raw = j.candidates?.[0]?.content?.parts?.map((p) => p.text ?? "").join("") ?? "";
  return parseJudgeRaw(raw, ms);
}

async function callOpenAiJudge(prompt: string, model: string): Promise<JudgeResult> {
  const key = process.env.OPENAI_API_KEY;
  if (!key) throw new Error("OPENAI_API_KEY not set for judge");
  const url = "https://api.openai.com/v1/chat/completions";
  const body = {
    model,
    temperature: 0,
    max_tokens: 256,
    response_format: { type: "json_object" as const },
    messages: [{ role: "user", content: prompt }],
  };
  const t0 = Date.now();
  const r = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json", authorization: `Bearer ${key}` },
    body: JSON.stringify(body),
  });
  const ms = Date.now() - t0;
  if (!r.ok) {
    const txt = (await r.text()).slice(0, 300);
    return { correct: null, ms, raw: `HTTP ${r.status}: ${txt}` };
  }
  const j = (await r.json()) as { choices?: Array<{ message?: { content?: string } }> };
  const raw = j.choices?.[0]?.message?.content ?? "";
  return parseJudgeRaw(raw, ms);
}

function parseJudgeRaw(raw: string, ms: number): JudgeResult {
  try {
    // Strip code fences if any.
    const cleaned = raw.replace(/^```(?:json)?\s*/i, "").replace(/```\s*$/i, "").trim();
    const obj = JSON.parse(cleaned) as { correct?: unknown; rationale?: string };
    if (typeof obj.correct === "boolean") {
      return { correct: obj.correct, rationale: obj.rationale, ms, raw };
    }
    return { correct: null, ms, raw };
  } catch {
    // Heuristic fallback — extract "correct": true|false anywhere.
    const m = raw.match(/"correct"\s*:\s*(true|false)/i);
    if (m) return { correct: m[1].toLowerCase() === "true", ms, raw };
    return { correct: null, ms, raw };
  }
}

async function callJudge(rec: RunRecord, model: string): Promise<JudgeResult> {
  const prompt = judgePrompt(rec);
  if (/^gpt-/i.test(model)) return callOpenAiJudge(prompt, model);
  return callGeminiJudge(prompt, model);
}

// ------------------------------------------------------------------
// Metrics
// ------------------------------------------------------------------

function wilsonCi(p: number, n: number, z = 1.96): [number, number] {
  if (n === 0) return [0, 0];
  const denom = 1 + (z * z) / n;
  const centre = p + (z * z) / (2 * n);
  const margin = z * Math.sqrt((p * (1 - p)) / n + (z * z) / (4 * n * n));
  return [(centre - margin) / denom, (centre + margin) / denom];
}

function mean(xs: number[]): number {
  if (xs.length === 0) return 0;
  return xs.reduce((a, b) => a + b, 0) / xs.length;
}

interface MetricSet {
  n: number;
  accuracy: number;
  retrieval_session_hit_rate: number;
  ci?: [number, number];
}

function metricsFor(records: ScoredRecord[], withCi: boolean): MetricSet {
  const ok: number[] = [];
  const hit: number[] = [];
  for (const r of records) {
    if (r.verdict === "skip" || r.verdict === "judge_error") continue;
    ok.push(r.verdict === "correct" ? 1 : 0);
    hit.push(r.retrieval_session_hit ? 1 : 0);
  }
  const m: MetricSet = {
    n: ok.length,
    accuracy: mean(ok),
    retrieval_session_hit_rate: mean(hit),
  };
  if (withCi) m.ci = wilsonCi(m.accuracy, m.n);
  return m;
}

// ------------------------------------------------------------------
// Main
// ------------------------------------------------------------------

async function main(): Promise<void> {
  const file = process.argv[2];
  const withCi = process.argv.includes("--ci");
  const dryJudge = process.argv.includes("--dry-judge");
  if (!file) {
    console.error("Usage: score.ts <run-output.json> [--ci] [--dry-judge]");
    process.exit(2);
  }
  const judgeModel = process.env.LONGMEMEVAL_JUDGE ?? DEFAULT_JUDGE;
  const data: RunFile = JSON.parse(await readFile(file, "utf8"));

  console.error(`[score] judge=${judgeModel} n=${data.records.length} dryJudge=${dryJudge}`);

  const scored: ScoredRecord[] = [];
  for (const rec of data.records) {
    const answerSet = new Set(rec.answer_session_ids ?? []);
    const retrieval_session_hit = (rec.retrieved_session_ids ?? []).some((s) => answerSet.has(s));

    if (rec.error) {
      scored.push({
        ...rec,
        verdict: "judge_error",
        judge_model: judgeModel,
        judge_rationale: `upstream error: ${rec.error}`,
        judge_ms: 0,
        retrieval_session_hit,
      });
      continue;
    }
    if (rec.generated_answer === "[--no-llm placeholder]") {
      scored.push({
        ...rec,
        verdict: "skip",
        judge_model: judgeModel,
        judge_rationale: "--no-llm placeholder",
        judge_ms: 0,
        retrieval_session_hit,
      });
      continue;
    }
    if (dryJudge) {
      scored.push({
        ...rec,
        verdict: "skip",
        judge_model: judgeModel,
        judge_rationale: "--dry-judge (LLM call skipped)",
        judge_ms: 0,
        retrieval_session_hit,
      });
      continue;
    }

    try {
      const jr = await callJudge(rec, judgeModel);
      scored.push({
        ...rec,
        verdict: jr.correct === null ? "judge_error" : jr.correct ? "correct" : "incorrect",
        judge_model: judgeModel,
        judge_rationale: jr.rationale ?? jr.raw.slice(0, 200),
        judge_ms: jr.ms,
        retrieval_session_hit,
      });
    } catch (e) {
      scored.push({
        ...rec,
        verdict: "judge_error",
        judge_model: judgeModel,
        judge_rationale: e instanceof Error ? e.message : String(e),
        judge_ms: 0,
        retrieval_session_hit,
      });
    }
  }

  const overall = metricsFor(scored, withCi);

  const byBase = new Map<string, ScoredRecord[]>();
  const byCell = new Map<string, ScoredRecord[]>();
  for (const r of scored) {
    if (!byBase.has(r.base_category)) byBase.set(r.base_category, []);
    byBase.get(r.base_category)!.push(r);
    const cell = r.is_abstention ? `${r.base_category}_abs` : r.base_category;
    if (!byCell.has(cell)) byCell.set(cell, []);
    byCell.get(cell)!.push(r);
  }
  const perBaseCategory: Record<string, MetricSet> = {};
  for (const [k, rs] of byBase) perBaseCategory[k] = metricsFor(rs, withCi);
  const perCell: Record<string, MetricSet> = {};
  for (const [k, rs] of byCell) perCell[k] = metricsFor(rs, withCi);

  const skips = scored.filter((r) => r.verdict === "skip").length;
  const judgeErrors = scored.filter((r) => r.verdict === "judge_error").length;

  const summary = {
    meta: { ...data.meta, judge: judgeModel, dryJudge },
    overall,
    per_base_category: perBaseCategory,
    per_cell: perCell,
    skips,
    judge_errors: judgeErrors,
    notes: data.meta.dryRun
      ? "DRY-RUN — sample too small for statistical inference. Numbers validate plumbing only."
      : "Full run. Accuracy is the headline metric.",
    generated_at: new Date().toISOString(),
  };

  process.stdout.write(JSON.stringify(summary, null, 2) + "\n");

  console.error(`[score] overall: n=${overall.n} acc=${overall.accuracy.toFixed(4)}  retrieval_hit=${overall.retrieval_session_hit_rate.toFixed(4)}  skips=${skips}  judge_errors=${judgeErrors}`);
  if (overall.ci) console.error(`[score] overall CI95: [${overall.ci[0].toFixed(4)}, ${overall.ci[1].toFixed(4)}]`);
  for (const [k, m] of Object.entries(perCell)) {
    console.error(`[score]   ${k}: n=${m.n}  acc=${m.accuracy.toFixed(4)}  hit=${m.retrieval_session_hit_rate.toFixed(4)}`);
  }
  if (data.meta.dryRun) console.error("[score] DRY-RUN — do not publish.");
}

main().catch((e) => {
  console.error("[score] ERROR:", e instanceof Error ? e.message : e);
  process.exit(1);
});
