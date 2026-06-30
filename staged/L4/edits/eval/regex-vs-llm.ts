/**
 * T8 — Eval harness: regex vs LLM extraction comparison.
 *
 * Samples up to MAX_FILES=200 markdown files, runs regex extractor over each,
 * and (when GEMINI_API_KEY is set) runs Gemini flash-lite for a head-to-head
 * comparison. Computes precision, recall, F1, cost estimate, and latency.
 *
 * Cost cap: 200 files × 500 tokens × $0.075/MTok ≈ $0.0075 (Gemini flash-lite).
 *
 * Usage:
 *   node --import tsx eval/regex-vs-llm.ts [--corpus <dir>] [--out <dir>]
 *
 * Output files (written to --out or ./eval-out/):
 *   regex-vs-llm-results.csv   — per-file row
 *   regex-vs-llm-summary.json  — aggregate metrics
 *
 * When no real corpus is available, runs synthetic corpus (built-in 20 samples).
 *
 * Spec: specs/2026-05-18-L4-regex-first-extraction.md §10 + T8 task.
 */

import fs from "node:fs";
import path from "node:path";

// ---------------------------------------------------------------------------
// Cost + size caps
// ---------------------------------------------------------------------------

export const MAX_FILES = 200;
export const MAX_TOKENS_PER_FILE = 500; // ~2000 chars (4 chars/token heuristic)
export const CHARS_PER_TOKEN = 4;
export const MAX_CHARS_PER_FILE = MAX_TOKENS_PER_FILE * CHARS_PER_TOKEN;

/** Gemini flash-lite cost: $0.075 per million input tokens. */
export const COST_PER_TOKEN_USD = 0.075 / 1_000_000;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ExtractedRelation {
  targetSlug: string;
  relationType: string;
}

export interface FileSampleResult {
  fileId: string;
  filePath: string;
  contentLength: number;
  /** Relations from regex extractor. */
  regexRelations: ExtractedRelation[];
  /** Relations from LLM (null when LLM not run). */
  llmRelations: ExtractedRelation[] | null;
  /** Metrics computed against LLM ground-truth (null when LLM not run). */
  metrics: SampleMetrics | null;
  /** Latency in milliseconds. */
  latency: { regex: number; llm: number | null };
  /** Estimated LLM cost in USD. */
  estimatedLlmCostUsd: number | null;
  /** Whether LLM was skipped (no API key or cost cap exceeded). */
  llmSkipped: boolean;
  llmSkipReason?: string;
}

export interface SampleMetrics {
  /** Precision = TP / (TP + FP). */
  precision: number;
  /** Recall = TP / (TP + FN). */
  recall: number;
  /** F1 = 2 * P * R / (P + R). */
  f1: number;
  truePositives: number;
  falsePositives: number;
  falseNegatives: number;
}

export interface EvalSummary {
  totalFiles: number;
  filesWithLlm: number;
  /** Macro-averaged precision across files with LLM comparison. */
  macroPrecision: number;
  /** Macro-averaged recall. */
  macroRecall: number;
  /** Macro-averaged F1. */
  macroF1: number;
  /** Total estimated LLM cost (USD). */
  totalLlmCostUsd: number;
  /** Median regex latency (ms). */
  medianRegexLatencyMs: number;
  /** Count of files where regex found ≥1 relation. */
  regexHitCount: number;
  /** Count of files where LLM found ≥1 relation. */
  llmHitCount: number;
  /** Estimated Gemini calls saved (regex-only eligible). */
  geminiCallsSaved: number;
  geminiCallsSavedPct: number;
}

// ---------------------------------------------------------------------------
// Synthetic corpus (used when no real corpus available)
// ---------------------------------------------------------------------------

/** Built-in synthetic markdown samples covering all extraction paths. */
export const SYNTHETIC_SAMPLES: Array<{ id: string; content: string; groundTruth: ExtractedRelation[] }> = [
  {
    id: "syn-001",
    content: "---\nagent: atlas\nreferences: [feedback/no_secrets, decision/d41]\n---\n\n## compiled\n\nSee [[feedback/no_secrets]] for key rule.",
    groundTruth: [
      { targetSlug: "agent/atlas", relationType: "is_agent_of" },
      { targetSlug: "feedback/no_secrets", relationType: "references" },
      { targetSlug: "decision/d41", relationType: "references" },
    ],
  },
  {
    id: "syn-002",
    content: "## Timeline\n\n- 2026-05-17: decided via [[decision/d41|D41 gbrain analysis]]\n- Resolved by [[spec/e15]]\n",
    groundTruth: [
      { targetSlug: "decision/d41", relationType: "references" },
      { targetSlug: "spec/e15", relationType: "references" },
    ],
  },
  {
    id: "syn-003",
    content: "---\nsupersedes: feedback/old-rule\ndecided_by: person/toto\n---\n\nThis replaces the old rule.",
    groundTruth: [
      { targetSlug: "feedback/old-rule", relationType: "supersedes" },
      { targetSlug: "person/toto", relationType: "decided_by" },
    ],
  },
  {
    id: "syn-004",
    content: "Pure prose with no structured references. Just free text discussing how the system works.",
    groundTruth: [],
  },
  {
    id: "syn-005",
    content: "```typescript\n// feedback/no_secrets is NOT an entity ref here\nconst x = 'feedback/ignore_this';\n```\n\nBut [[feedback/real_ref]] is outside the fence.",
    groundTruth: [
      { targetSlug: "feedback/real_ref", relationType: "references" },
    ],
  },
  {
    id: "syn-006",
    content: "The incident was caused by feedback/bad_config deployment. See audit/a1 for details.",
    groundTruth: [
      { targetSlug: "feedback/bad_config", relationType: "references" },
      { targetSlug: "audit/a1", relationType: "references" },
    ],
  },
  {
    id: "syn-007",
    content: "---\ncaused_by: incident/i7\nresolves: pending/p3\n---\n",
    groundTruth: [
      { targetSlug: "incident/i7", relationType: "caused_by" },
      { targetSlug: "pending/p3", relationType: "resolves" },
    ],
  },
  {
    id: "syn-008",
    content: "See [D41 decision](decision/d41) and [E15 spec](spec/e15) for background.",
    groundTruth: [
      { targetSlug: "decision/d41", relationType: "references" },
      { targetSlug: "spec/e15", relationType: "references" },
    ],
  },
  {
    id: "syn-009",
    content: "https://example.com/feedback/not_an_entity — this URL should NOT match.",
    groundTruth: [],
  },
  {
    id: "syn-010",
    content: "[[agent/boris]] is the code-review persona. [[agent/forge]] handles PRs.",
    groundTruth: [
      { targetSlug: "agent/boris", relationType: "references" },
      { targetSlug: "agent/forge", relationType: "references" },
    ],
  },
  {
    id: "syn-011",
    content: "This references src/lib/op-audit.ts:42 for the snapshot logic.",
    groundTruth: [
      { targetSlug: "codepath/src/lib/op-audit.ts:42", relationType: "code_ref" },
    ],
  },
  {
    id: "syn-012",
    content: "---\nreferences:\n  - lesson/l1\n  - lesson/l2\n  - decision/d10\n---\n",
    groundTruth: [
      { targetSlug: "lesson/l1", relationType: "references" },
      { targetSlug: "lesson/l2", relationType: "references" },
      { targetSlug: "decision/d10", relationType: "references" },
    ],
  },
  {
    id: "syn-013",
    content: "the feedback was great (not an entity reference without slash form)",
    groundTruth: [],
  },
  {
    id: "syn-014",
    content: "Inline code `feedback/no_secrets` is suppressed but [[feedback/real]] is live.",
    groundTruth: [
      { targetSlug: "feedback/real", relationType: "references" },
    ],
  },
  {
    id: "syn-015",
    content: "regra é feedback/no_secrets, certo? É a regra mais importante.",
    groundTruth: [
      { targetSlug: "feedback/no_secrets", relationType: "references" },
    ],
  },
  {
    id: "syn-016",
    content: "[[skill/graphify]] extracts KG from free text. See [[reference/obsidian_setup]] for config.",
    groundTruth: [
      { targetSlug: "skill/graphify", relationType: "references" },
      { targetSlug: "reference/obsidian_setup", relationType: "references" },
    ],
  },
  {
    id: "syn-017",
    content: "Daily entry. Worked on pending/p5 today. Will review team/forge-devs setup.",
    groundTruth: [
      { targetSlug: "pending/p5", relationType: "references" },
      { targetSlug: "team/forge-devs", relationType: "references" },
    ],
  },
  {
    id: "syn-018",
    content: "---\nagent: cipher\n---\n\n## compiled\n\nCipher handles security audits. Cross-ref [[audit/sec-2026-05]].",
    groundTruth: [
      { targetSlug: "agent/cipher", relationType: "is_agent_of" },
      { targetSlug: "audit/sec-2026-05", relationType: "references" },
    ],
  },
  {
    id: "syn-019",
    content: "No entity refs at all. Just a freeform conversation log from the morning.",
    groundTruth: [],
  },
  {
    id: "syn-020",
    content: "[[graph_node/n7]] → [[graph_node/n12]] edge with label 'caused_by'.",
    groundTruth: [
      { targetSlug: "graph_node/n7", relationType: "references" },
      { targetSlug: "graph_node/n12", relationType: "references" },
    ],
  },
];

// ---------------------------------------------------------------------------
// Regex extraction adapter
// ---------------------------------------------------------------------------

import {
  extractEntityRefsRegex,
  extractCodeRefs,
} from "../src/lib/regex-extract/extractor.js";
import { extractFrontmatterRelations } from "../src/lib/regex-extract/frontmatter.js";

export function runRegexExtraction(content: string): ExtractedRelation[] {
  const results: ExtractedRelation[] = [];
  for (const ref of extractEntityRefsRegex(content)) {
    results.push({ targetSlug: ref.key, relationType: "references" });
  }
  for (const rel of extractFrontmatterRelations(content)) {
    results.push({ targetSlug: rel.target, relationType: rel.relationType });
  }
  for (const ref of extractCodeRefs(content)) {
    results.push({ targetSlug: ref.key, relationType: "code_ref" });
  }
  // Dedup by (targetSlug, relationType)
  const seen = new Set<string>();
  return results.filter((r) => {
    const k = `${r.targetSlug}|${r.relationType}`;
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });
}

// ---------------------------------------------------------------------------
// Metrics calculation
// ---------------------------------------------------------------------------

/**
 * Compare regex relations against LLM ground-truth using slug-based matching.
 * F1 = harmonic mean of precision (how many regex hits are correct) and
 * recall (how many ground-truth relations were found by regex).
 */
export function computeMetrics(
  regexRelations: ExtractedRelation[],
  groundTruth: ExtractedRelation[],
): SampleMetrics {
  if (groundTruth.length === 0 && regexRelations.length === 0) {
    return { precision: 1.0, recall: 1.0, f1: 1.0, truePositives: 0, falsePositives: 0, falseNegatives: 0 };
  }
  if (groundTruth.length === 0) {
    return { precision: 0.0, recall: 1.0, f1: 0.0, truePositives: 0, falsePositives: regexRelations.length, falseNegatives: 0 };
  }

  // Build ground-truth set by slug (ignore relationType for coverage — slug match is primary).
  const gtSlugs = new Set(groundTruth.map((r) => r.targetSlug.toLowerCase()));
  const regexSlugs = regexRelations.map((r) => r.targetSlug.toLowerCase());

  let tp = 0;
  const seen = new Set<string>();
  for (const slug of regexSlugs) {
    if (gtSlugs.has(slug) && !seen.has(slug)) {
      tp++;
      seen.add(slug);
    }
  }
  const fp = new Set(regexSlugs).size - tp;
  const fn = gtSlugs.size - tp;

  const precision = tp + fp > 0 ? tp / (tp + fp) : 0;
  const recall = tp + fn > 0 ? tp / (tp + fn) : 0;
  const f1 = precision + recall > 0 ? (2 * precision * recall) / (precision + recall) : 0;

  return { precision, recall, f1, truePositives: tp, falsePositives: fp, falseNegatives: fn };
}

// ---------------------------------------------------------------------------
// LLM stub (Gemini flash-lite integration placeholder)
// ---------------------------------------------------------------------------

/**
 * LLM extraction stub. When `GEMINI_API_KEY` is set and the Gemini SDK is
 * available at runtime, this calls Gemini flash-lite. Otherwise returns null.
 *
 * The cost cap (MAX_TOKENS_PER_FILE) is enforced by truncating content.
 *
 * @returns extracted relations or null if LLM is unavailable/skipped.
 */
export async function runLlmExtraction(
  content: string,
  apiKey?: string,
): Promise<{ relations: ExtractedRelation[]; tokensUsed: number } | null> {
  const key = apiKey ?? process.env["GEMINI_API_KEY"];
  if (!key) return null;

  // Truncate to cost cap.
  const truncated = content.slice(0, MAX_CHARS_PER_FILE);
  const estimatedTokens = Math.ceil(truncated.length / CHARS_PER_TOKEN);

  const prompt = `Extract entity references from this markdown content. Return ONLY a JSON array of objects with shape {targetSlug: string, relationType: string}. targetSlug format: "<entityType>/<slug>". entityTypes: feedback, person, lesson, decision, project, team, daily, pending, graph_node, agent, incident, spec, audit, skill, persona, reference. Relation types: references, is_agent_of, supersedes, caused_by, resolves, decided_by. Return [] if none found.\n\nContent:\n${truncated}`;

  try {
    // Dynamic import to avoid hard dep — only needed at runtime.
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const sdk = await import("@google/generative-ai" as any).catch(() => null) as any;
    if (!sdk) return null;

    const genai = new sdk.GoogleGenerativeAI(key);
    const model = genai.getGenerativeModel({ model: "gemini-1.5-flash-8b" });
    const result = await model.generateContent(prompt);
    const text = result.response.text().trim();
    const match = text.match(/\[[\s\S]*\]/);
    if (!match) return { relations: [], tokensUsed: estimatedTokens };
    const parsed = JSON.parse(match[0]) as unknown[];
    const relations: ExtractedRelation[] = [];
    for (const item of parsed) {
      if (
        typeof item === "object" &&
        item !== null &&
        "targetSlug" in item &&
        "relationType" in item
      ) {
        const r = item as Record<string, unknown>;
        if (typeof r["targetSlug"] === "string" && typeof r["relationType"] === "string") {
          relations.push({ targetSlug: r["targetSlug"], relationType: r["relationType"] });
        }
      }
    }
    return { relations, tokensUsed: estimatedTokens };
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// File discovery
// ---------------------------------------------------------------------------

/** Collect up to MAX_FILES markdown files from `corpusDir` recursively. */
export function collectMarkdownFiles(
  corpusDir: string,
  limit = MAX_FILES,
): string[] {
  if (!fs.existsSync(corpusDir)) return [];
  const results: string[] = [];
  const stack = [corpusDir];
  while (stack.length > 0 && results.length < limit) {
    const dir = stack.pop()!;
    let entries: fs.Dirent[];
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const entry of entries) {
      if (results.length >= limit) break;
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        stack.push(fullPath);
      } else if (entry.isFile() && entry.name.endsWith(".md")) {
        results.push(fullPath);
      }
    }
  }
  return results.slice(0, limit);
}

// ---------------------------------------------------------------------------
// CSV + JSON output
// ---------------------------------------------------------------------------

export function formatCsvRow(r: FileSampleResult): string {
  const metrics = r.metrics;
  return [
    r.fileId,
    r.filePath,
    r.contentLength,
    r.regexRelations.length,
    r.llmRelations?.length ?? "",
    metrics?.precision.toFixed(4) ?? "",
    metrics?.recall.toFixed(4) ?? "",
    metrics?.f1.toFixed(4) ?? "",
    r.latency.regex.toFixed(2),
    r.latency.llm?.toFixed(2) ?? "",
    r.estimatedLlmCostUsd?.toFixed(8) ?? "",
    r.llmSkipped ? "1" : "0",
    r.llmSkipReason ?? "",
  ].join(",");
}

export const CSV_HEADER =
  "file_id,file_path,content_length,regex_relations,llm_relations,precision,recall,f1,regex_latency_ms,llm_latency_ms,estimated_llm_cost_usd,llm_skipped,llm_skip_reason";

export function computeSummary(results: FileSampleResult[]): EvalSummary {
  const withLlm = results.filter((r) => r.metrics !== null);
  const macroPrecision =
    withLlm.length > 0
      ? withLlm.reduce((s, r) => s + (r.metrics?.precision ?? 0), 0) / withLlm.length
      : 0;
  const macroRecall =
    withLlm.length > 0
      ? withLlm.reduce((s, r) => s + (r.metrics?.recall ?? 0), 0) / withLlm.length
      : 0;
  const macroF1 =
    withLlm.length > 0
      ? withLlm.reduce((s, r) => s + (r.metrics?.f1 ?? 0), 0) / withLlm.length
      : 0;
  const totalCost = results.reduce((s, r) => s + (r.estimatedLlmCostUsd ?? 0), 0);

  const latencies = results.map((r) => r.latency.regex).sort((a, b) => a - b);
  const mid = Math.floor(latencies.length / 2);
  const medianRegexLatencyMs =
    latencies.length === 0
      ? 0
      : latencies.length % 2 === 0
      ? ((latencies[mid - 1] ?? 0) + (latencies[mid] ?? 0)) / 2
      : (latencies[mid] ?? 0);

  const regexHitCount = results.filter((r) => r.regexRelations.length > 0).length;
  const llmHitCount = results.filter((r) => (r.llmRelations?.length ?? 0) > 0).length;

  // Gemini calls "saved" = files where regex found ≥1 relation AND section was eligible.
  // Approximated here as regexHitCount (conservative — actual rate depends on section).
  const geminiCallsSaved = regexHitCount;
  const geminiCallsSavedPct =
    results.length > 0 ? (geminiCallsSaved / results.length) * 100 : 0;

  return {
    totalFiles: results.length,
    filesWithLlm: withLlm.length,
    macroPrecision,
    macroRecall,
    macroF1,
    totalLlmCostUsd: totalCost,
    medianRegexLatencyMs,
    regexHitCount,
    llmHitCount,
    geminiCallsSaved,
    geminiCallsSavedPct,
  };
}

// ---------------------------------------------------------------------------
// Main eval runner
// ---------------------------------------------------------------------------

export async function runEval(opts: {
  corpusDir?: string;
  outDir?: string;
  useSynthetic?: boolean;
  apiKey?: string;
}): Promise<{ results: FileSampleResult[]; summary: EvalSummary }> {
  const outDir = opts.outDir ?? path.join(process.cwd(), "eval-out");
  fs.mkdirSync(outDir, { recursive: true });

  // Collect samples.
  let samples: Array<{ id: string; content: string; groundTruth: ExtractedRelation[] | null }>;

  if (opts.useSynthetic || !opts.corpusDir) {
    samples = SYNTHETIC_SAMPLES.map((s) => ({
      id: s.id,
      content: s.content,
      groundTruth: s.groundTruth,
    }));
  } else {
    const files = collectMarkdownFiles(opts.corpusDir, MAX_FILES);
    samples = files.map((p, i) => {
      let content = "";
      try {
        content = fs.readFileSync(p, "utf-8").slice(0, MAX_CHARS_PER_FILE);
      } catch {
        content = "";
      }
      return { id: `file-${String(i + 1).padStart(4, "0")}`, content, groundTruth: null };
    });
  }

  const results: FileSampleResult[] = [];

  for (const sample of samples.slice(0, MAX_FILES)) {
    const regexStart = Date.now();
    const regexRelations = runRegexExtraction(sample.content);
    const regexLatency = Date.now() - regexStart;

    let llmRelations: ExtractedRelation[] | null = null;
    let llmLatency: number | null = null;
    let estimatedCost: number | null = null;
    let llmSkipped = false;
    let llmSkipReason: string | undefined;
    let metrics: SampleMetrics | null = null;

    const key = opts.apiKey ?? process.env["GEMINI_API_KEY"];
    if (!key) {
      llmSkipped = true;
      llmSkipReason = "no_api_key";
    } else {
      const llmStart = Date.now();
      const llmResult = await runLlmExtraction(sample.content, key);
      llmLatency = Date.now() - llmStart;
      if (llmResult) {
        llmRelations = llmResult.relations;
        estimatedCost = llmResult.tokensUsed * COST_PER_TOKEN_USD;
      } else {
        llmSkipped = true;
        llmSkipReason = "llm_unavailable";
      }
    }

    // Compute metrics against ground truth (synthetic) or LLM (real corpus).
    const groundTruth = sample.groundTruth ?? llmRelations;
    if (groundTruth !== null) {
      metrics = computeMetrics(regexRelations, groundTruth);
    }

    results.push({
      fileId: sample.id,
      filePath: sample.id,
      contentLength: sample.content.length,
      regexRelations,
      llmRelations,
      metrics,
      latency: { regex: regexLatency, llm: llmLatency },
      estimatedLlmCostUsd: estimatedCost,
      llmSkipped,
      llmSkipReason,
    });
  }

  const summary = computeSummary(results);

  // Write CSV.
  const csvPath = path.join(outDir, "regex-vs-llm-results.csv");
  const csvLines = [CSV_HEADER, ...results.map(formatCsvRow)];
  fs.writeFileSync(csvPath, csvLines.join("\n"), "utf-8");

  // Write summary JSON.
  const summaryPath = path.join(outDir, "regex-vs-llm-summary.json");
  fs.writeFileSync(summaryPath, JSON.stringify(summary, null, 2), "utf-8");

  return { results, summary };
}

// ---------------------------------------------------------------------------
// CLI entry (when run directly)
// ---------------------------------------------------------------------------

const isMain =
  typeof process !== "undefined" &&
  process.argv[1] !== undefined &&
  process.argv[1].endsWith("regex-vs-llm.ts") ||
  (typeof process !== "undefined" &&
    process.argv[1] !== undefined &&
    process.argv[1].endsWith("regex-vs-llm.js"));

if (isMain) {
  const args = process.argv.slice(2);
  const corpusIdx = args.indexOf("--corpus");
  const outIdx = args.indexOf("--out");
  const useSynthetic = args.includes("--synthetic");

  const corpusDir = corpusIdx >= 0 ? args[corpusIdx + 1] : undefined;
  const outDir = outIdx >= 0 ? args[outIdx + 1] : undefined;

  runEval({ corpusDir, outDir, useSynthetic }).then(({ summary }) => {
    console.log("=== regex-vs-llm eval summary ===");
    console.log(`Total files:       ${summary.totalFiles}`);
    console.log(`Files with LLM:    ${summary.filesWithLlm}`);
    console.log(`Macro precision:   ${(summary.macroPrecision * 100).toFixed(1)}%`);
    console.log(`Macro recall:      ${(summary.macroRecall * 100).toFixed(1)}%`);
    console.log(`Macro F1:          ${(summary.macroF1 * 100).toFixed(1)}%`);
    console.log(`Estimated LLM cost: $${summary.totalLlmCostUsd.toFixed(6)}`);
    console.log(`Median regex latency: ${summary.medianRegexLatencyMs.toFixed(2)}ms`);
    console.log(`Regex hit rate:    ${summary.regexHitCount}/${summary.totalFiles} (${((summary.regexHitCount / Math.max(1, summary.totalFiles)) * 100).toFixed(1)}%)`);
    console.log(`Gemini calls saved: ~${summary.geminiCallsSaved} (${summary.geminiCallsSavedPct.toFixed(1)}%)`);
  }).catch((err: unknown) => {
    console.error("Eval failed:", err);
    process.exit(1);
  });
}
