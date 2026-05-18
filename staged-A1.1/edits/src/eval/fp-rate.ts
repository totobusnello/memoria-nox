/**
 * eval/fp-rate.ts — A1.1 False Positive rate measurement.
 *
 * Roda detectBrPii sobre corpus de texto NÃO-PII (lorem ipsum, código,
 * docs internos, hashes, builds). Conta:
 *   - matches confidence-high (>= 0.9)    — esses contam como FP "duros"
 *   - matches medium (0.6 - 0.9)          — FP "moderados"
 *   - matches low (< 0.6)                 — esperado (regex casual)
 *
 * Target: ≤2% per pattern type, ≤5% aggregate medindo high+medium juntos
 * sobre número de "blocos" de texto.
 *
 * Métrica: blocos de ~500 chars (chunk size típico nox-mem).
 * FP rate = blocos_com_match_HIGH / total_blocos.
 *
 * Saída: tabela markdown + JSON com per-kind breakdown.
 */

import { detectBrPii } from "../lib/privacy-br/detector.js";
import { BrPatternKind } from "../lib/privacy-br/types.js";
import { NON_PII_CORPUS } from "../lib/privacy-br/__tests__/corpus.js";
import { BR_PATTERNS } from "../lib/privacy-br/patterns.js";

/**
 * Extra corpus — lorem ipsum + code + docs gerados in-line.
 * Pra eval mais robusto, idealmente carregar do disco — mas pra staging
 * worktree mantemos in-source (sem deps externas).
 */
const EXTRA_CORPUS = [
  `
The quick brown fox jumps over the lazy dog. Lorem ipsum dolor sit amet,
consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore
et dolore magna aliqua. The build number 12345678 was deployed at
timestamp 1717000000 (unix epoch seconds).
`,
  `
function calculateLuhn(digits) {
  let sum = 0;
  for (let i = digits.length - 1; i >= 0; i--) {
    sum += parseInt(digits[i], 10);
  }
  return sum % 10 === 0;
}
const TEST_ID = "550e8400-e29b-11d4-a716-446655440000";  // v1 UUID, not v4
const BUILD = "v1.2.3.4567";
`,
  `
# Roadmap Q2 2025
- Sprint 1: build phase 12345 (250 hours)
- Sprint 2: deploy 67890 to staging
- Sprint 3: release 11111 to production
Versão: 1.2.3 (commit a1b2c3d4e5f60718293a4b5c6d7e8f9012345678)
ISBN do livro de referência: 9781234567890.
Preço base: 1234567 unidades vendidas.
`,
  `
Random hex blobs from cryptographic operations:
deadbeefcafebabe1234567890abcdef00000000000000000000000000000000
abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789
SHA256 of "hello world": b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9
`,
  `
Reunião do board em 2025-01-15. Participantes: Toto, Atlas, Boris, Cipher.
Discutimos a alocação de 40% da capacity pra research (Lab) e 60% pra
product. KPI: nDCG ≥ 0.75 ao final do Q1. Budget Q1: R$ 100.000,00.
Próxima review: 31/03/2025. Status: green.
`,
  `
Internal SKU registry: 9876543210, 1234567890, 5555666677.
Item codes follow format SKU-XXXXXXX (7 digits).
Build #999888 was rejected due to flaky tests in chunk_search.test.ts.
Timestamp epoch: 1700000000. Memory usage: 12345 KB peak.
`,
  `
Lorem ipsum dolor sit amet. Sequência numérica aleatória pra teste:
11122233344, 55566677788, 99988877766. Nenhum deve ser tratado como
informação pessoal — são apenas números sem contexto.
`,
];

/**
 * Quebra texto em blocos de ~chunkSize chars, respeitando boundary de linha.
 */
function chunkText(text: string, chunkSize = 500): string[] {
  const blocks: string[] = [];
  let current = "";
  for (const line of text.split("\n")) {
    if (current.length + line.length > chunkSize && current.length > 0) {
      blocks.push(current);
      current = line + "\n";
    } else {
      current += line + "\n";
    }
  }
  if (current.trim().length > 0) blocks.push(current);
  return blocks;
}

interface KindStats {
  total: number;
  highConf: number;
  mediumConf: number;
  lowConf: number;
}

function emptyStats(): KindStats {
  return { total: 0, highConf: 0, mediumConf: 0, lowConf: 0 };
}

interface FpReport {
  totalBlocks: number;
  blocksWithAnyHighConfHit: number;
  aggregateFpRateHighConf: number; // % blocos com pelo menos 1 high-conf
  byKind: Record<BrPatternKind, KindStats & { fpRate: number }>;
  examples: Array<{ kind: BrPatternKind; raw: string; context: string; confidence: number }>;
}

export function measureFpRate(corpus: string[]): FpReport {
  const allBlocks: string[] = [];
  for (const text of corpus) {
    for (const block of chunkText(text)) allBlocks.push(block);
  }
  const totalBlocks = allBlocks.length;

  const byKindRaw: Record<string, KindStats> = {};
  for (const def of BR_PATTERNS) {
    byKindRaw[def.kind] = emptyStats();
  }

  const examples: FpReport["examples"] = [];
  let blocksWithAnyHighConf = 0;

  for (const block of allBlocks) {
    const matches = detectBrPii(block);
    let blockHasHighConf = false;
    for (const m of matches) {
      const s = byKindRaw[m.kind] ?? emptyStats();
      s.total++;
      if (m.confidence >= 0.9) s.highConf++;
      else if (m.confidence >= 0.6) s.mediumConf++;
      else s.lowConf++;
      byKindRaw[m.kind] = s;

      if (m.confidence >= 0.9) {
        blockHasHighConf = true;
        if (examples.length < 20) {
          const start = Math.max(0, m.position[0] - 20);
          const end = Math.min(block.length, m.position[1] + 20);
          examples.push({
            kind: m.kind,
            raw: m.raw,
            context: block.substring(start, end).replace(/\n/g, " "),
            confidence: m.confidence,
          });
        }
      }
    }
    if (blockHasHighConf) blocksWithAnyHighConf++;
  }

  const byKind: FpReport["byKind"] = {} as FpReport["byKind"];
  for (const def of BR_PATTERNS) {
    const s = byKindRaw[def.kind];
    byKind[def.kind] = {
      ...s,
      fpRate: totalBlocks > 0 ? s.highConf / totalBlocks : 0,
    };
  }

  return {
    totalBlocks,
    blocksWithAnyHighConfHit: blocksWithAnyHighConf,
    aggregateFpRateHighConf:
      totalBlocks > 0 ? blocksWithAnyHighConf / totalBlocks : 0,
    byKind,
    examples,
  };
}

function renderMarkdown(report: FpReport): string {
  const lines: string[] = [];
  lines.push("# A1.1 BR PII — False Positive Rate Report");
  lines.push("");
  lines.push(`- Total blocks (~500 chars each): **${report.totalBlocks}**`);
  lines.push(
    `- Blocks with ≥1 HIGH-conf hit: **${report.blocksWithAnyHighConfHit}** (${(report.aggregateFpRateHighConf * 100).toFixed(2)}%)`,
  );
  lines.push("");
  lines.push("## Per-kind breakdown");
  lines.push("");
  lines.push("| kind | total | high | medium | low | FP rate (high-conf) |");
  lines.push("|------|-------|------|--------|-----|---------------------|");
  for (const def of BR_PATTERNS) {
    const s = report.byKind[def.kind];
    lines.push(
      `| ${def.kind} | ${s.total} | ${s.highConf} | ${s.mediumConf} | ${s.lowConf} | ${(s.fpRate * 100).toFixed(2)}% |`,
    );
  }
  lines.push("");
  if (report.examples.length > 0) {
    lines.push("## High-confidence FP examples");
    lines.push("");
    for (const ex of report.examples) {
      lines.push(`- **${ex.kind}** \`${ex.raw}\` (conf=${ex.confidence})`);
      lines.push(`  > ...${ex.context.trim()}...`);
    }
  } else {
    lines.push("## No high-confidence false positives detected.");
  }
  return lines.join("\n");
}

// ─── CLI entry ────────────────────────────────────────────────────────────────

function main() {
  const corpus = [NON_PII_CORPUS, ...EXTRA_CORPUS];
  const report = measureFpRate(corpus);

  const md = renderMarkdown(report);
  console.log(md);
  console.log("");
  console.log("---");
  console.log("JSON:");
  console.log(JSON.stringify(report, null, 2));

  // Gate: fail process se aggregate FP rate > 5%
  const aggregatePct = report.aggregateFpRateHighConf * 100;
  if (aggregatePct > 5) {
    console.error(`\nFAIL: aggregate FP rate ${aggregatePct.toFixed(2)}% > 5%`);
    process.exit(1);
  }

  // Per-kind gate: <=2% per kind (high-conf)
  let perKindFail = false;
  for (const def of BR_PATTERNS) {
    const r = report.byKind[def.kind].fpRate * 100;
    if (r > 2) {
      console.error(`FAIL: ${def.kind} FP rate ${r.toFixed(2)}% > 2%`);
      perKindFail = true;
    }
  }
  if (perKindFail) process.exit(1);

  console.log("\nPASS — FP rate within targets (≤2% per kind, ≤5% aggregate)");
}

// Only run main if invoked as script (not when imported by tests)
const isMain =
  import.meta.url === `file://${process.argv[1]}` ||
  process.argv[1]?.endsWith("fp-rate.js");
if (isMain) {
  main();
}
