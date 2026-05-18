/**
 * workloads.ts — Benchmark workload definitions for nox-mem latency harness.
 *
 * Each workload declares:
 *  - id: unique identifier used in output JSON
 *  - description: human-readable label
 *  - type: "search" | "ingest" | "answer"
 *  - cacheMode: "warm" | "cold" | "both"
 *  - n: number of measured iterations (after warmup)
 *  - warmup: number of warmup iterations (discarded)
 *  - queries / payloads: data source
 *
 * NOTE: nox-mem does not expose an importable module from this repo —
 * the compiled binary lives on VPS at dist/index.js. All workloads
 * are executed as child_process subprocesses. Subprocess startup is
 * absorbed in warmup iterations; post-warmup spawns include shell
 * startup overhead (~5–15ms) that is measured and NOT hidden.
 *
 * If a future PR exposes HTTP :18802 or an importable module, update
 * WorkloadExecutor in runner.ts and document the latency delta.
 */

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type WorkloadType = "search" | "ingest" | "answer";
export type CacheMode = "warm" | "cold";

export interface SearchQuery {
  query_id: number;
  query: string;
  category: string;
  difficulty: string;
}

export interface WorkloadDefinition {
  id: string;
  description: string;
  type: WorkloadType;
  cacheMode: CacheMode;
  /** Number of measured iterations (after warmup). */
  n: number;
  /** Number of warmup iterations (results discarded). */
  warmup: number;
  /** For search workloads: array of query strings to cycle through. */
  queries?: string[];
  /** For ingest workloads: path to fixture file or synthetic payload. */
  fixturePath?: string;
  /** True if the workload is a placeholder (not runnable yet). */
  placeholder?: boolean;
  placeholderReason?: string;
}

// ---------------------------------------------------------------------------
// Query sources
// ---------------------------------------------------------------------------

/**
 * Load golden queries from eval/golden-queries.jsonl.
 * Path is relative to the repo root — adjust NOX_REPO_ROOT env var if needed.
 */
function loadGoldenQueries(): SearchQuery[] {
  const repoRoot =
    process.env.NOX_REPO_ROOT ?? join(__dirname, "..", "..", "..");
  const path = join(repoRoot, "eval", "golden-queries.jsonl");
  try {
    const raw = readFileSync(path, "utf8");
    return raw
      .split("\n")
      .filter((l) => l.trim())
      .map((l) => JSON.parse(l) as SearchQuery);
  } catch {
    console.warn(`[workloads] Could not load golden queries from ${path}`);
    return [];
  }
}

/**
 * Pad or trim an array to exactly `target` length by cycling.
 */
function padToLength<T>(arr: T[], target: number): T[] {
  if (arr.length === 0) return arr;
  const result: T[] = [];
  while (result.length < target) {
    result.push(...arr);
  }
  return result.slice(0, target);
}

// ---------------------------------------------------------------------------
// Synthetic query generators
// ---------------------------------------------------------------------------

/** Short (1–3 word) synthetic queries to pad search.short to n=100. */
const SYNTHETIC_SHORT: string[] = [
  "nox-mem",
  "salience",
  "chunk",
  "FTS5",
  "sqlite-vec",
  "embeddings",
  "KG entities",
  "retention",
  "pain score",
  "hybrid search",
  "ingest",
  "crystallize",
  "section boost",
  "withOpAudit",
  "dry-run",
  "vectorize",
  "reindex",
  "gemini flash",
  "op-audit",
  "kg-extract",
];

/** Long (10+ word) NL synthetic queries to pad search.long to n=100. */
const SYNTHETIC_LONG: string[] = [
  "como funciona o processo completo de ingestão de arquivos de entidade no nox-mem",
  "qual é a diferença entre BM25 e busca semântica no pipeline híbrido de search",
  "por que o campo pain foi adicionado ao schema e como ele afeta o ranking",
  "como o withOpAudit protege operações destrutivas e quais são seus limites",
  "o que acontece quando o processo de vectorize encontra um erro de API do Gemini",
  "como configurar o nox-mem para usar um modelo diferente do gemini-2.5-flash-lite",
  "quais são as diferenças entre os modos cold cache e warm cache para benchmark",
  "como o RRF combina scores do BM25 e da busca semântica no resultado final",
  "qual é o processo correto para adicionar novos tipos de entidade ao knowledge graph",
  "como funciona o mecanismo de retenção diferenciada por tipo de chunk no schema v10",
];

/** Named-entity queries for KG-heavy workload. */
const SYNTHETIC_KG: string[] = [
  "Atlas agent memory capabilities",
  "Boris agent knowledge graph",
  "Forge code review integration",
  "Nox secretary daily briefing",
  "Cipher security agent role",
  "OpenClaw gateway monkey-patch",
  "Hostinger VPS configuration",
  "Gemini embedding model migration",
  "nox-mem-api port 18802",
  "FII Treviso project memory",
];

// ---------------------------------------------------------------------------
// Build workloads
// ---------------------------------------------------------------------------

export function buildWorkloads(): WorkloadDefinition[] {
  const golden = loadGoldenQueries();

  // --- search.short: queries with 1–3 words ---
  const shortFromGolden = golden
    .filter((q) => q.query.split(" ").length <= 3)
    .map((q) => q.query);
  const shortQueries = padToLength(
    [...shortFromGolden, ...SYNTHETIC_SHORT],
    100,
  );

  // --- search.medium: queries with 4–9 words ---
  const mediumFromGolden = golden
    .filter((q) => {
      const w = q.query.split(" ").length;
      return w >= 4 && w <= 9;
    })
    .map((q) => q.query);
  const mediumQueries = padToLength([...mediumFromGolden, ...SYNTHETIC_SHORT.map(s => `o que é ${s} no nox-mem`)], 100);

  // --- search.long: queries with 10+ words ---
  const longFromGolden = golden
    .filter((q) => q.query.split(" ").length >= 10)
    .map((q) => q.query);
  const longQueries = padToLength(
    [...longFromGolden, ...SYNTHETIC_LONG],
    100,
  );

  // --- search.kg-heavy: entity category queries ---
  const kgFromGolden = golden
    .filter((q) => q.category === "entity")
    .map((q) => q.query);
  const kgQueries = padToLength([...kgFromGolden, ...SYNTHETIC_KG], 50);

  // --- fixture paths ---
  const fixtureDir = join(__dirname, "..", "fixtures");

  return [
    // ------------------------------------------------------------------
    // Search workloads
    // ------------------------------------------------------------------
    {
      id: "search.short",
      description: "1–3 word queries — minimal FTS5 + semantic surface area",
      type: "search",
      cacheMode: "warm",
      n: 100,
      warmup: 10,
      queries: shortQueries,
    },
    {
      id: "search.medium",
      description: "4–9 word conversational queries — typical production traffic",
      type: "search",
      cacheMode: "warm",
      n: 100,
      warmup: 10,
      queries: mediumQueries,
    },
    {
      id: "search.long",
      description: "10+ word NL queries — full BM25+semantic pipeline",
      type: "search",
      cacheMode: "warm",
      n: 100,
      warmup: 10,
      queries: longQueries,
    },
    {
      id: "search.kg-heavy",
      description: "Named-entity queries triggering KG traversal",
      type: "search",
      cacheMode: "warm",
      n: 50,
      warmup: 10,
      queries: kgQueries,
    },

    // ------------------------------------------------------------------
    // Ingest workloads
    // ------------------------------------------------------------------
    {
      id: "ingest.entity-file",
      description:
        "Ingest a ~5KB entity Markdown file (frontmatter + compiled + timeline). Warm DB.",
      type: "ingest",
      cacheMode: "warm",
      n: 50,
      warmup: 5,
      fixturePath: join(fixtureDir, "entity-fixture.md"),
    },
    {
      id: "ingest.chunk-batch",
      description: "Batch insert 100 synthetic raw text chunks",
      type: "ingest",
      cacheMode: "warm",
      n: 20,
      warmup: 3,
      fixturePath: join(fixtureDir, "chunk-batch-fixture.jsonl"),
    },

    // ------------------------------------------------------------------
    // Answer workload (placeholder — P1 not yet shipped)
    // ------------------------------------------------------------------
    {
      id: "answer.placeholder",
      description:
        "Stub for P1 Answer primitive. Records NOT_YET for all metrics.",
      type: "answer",
      cacheMode: "warm",
      n: 0,
      warmup: 0,
      placeholder: true,
      placeholderReason:
        "P1 Answer primitive not yet shipped. See specs/answer/ for interface spec.",
    },
  ];
}

/** Convenience: get a single workload by id. */
export function getWorkload(id: string): WorkloadDefinition | undefined {
  return buildWorkloads().find((w) => w.id === id);
}
