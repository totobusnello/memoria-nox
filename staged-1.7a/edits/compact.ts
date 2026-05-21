/**
 * compact.ts — Compress old chunks (>30 days) into summaries
 * Uses Gemini 2.5 Flash (primary), Groq (secondary), first-sentence (fallback)
 * Reduces DB size while preserving knowledge
 */
import { getDb } from "./db.js";
import { withOpAudit } from "./lib/op-audit.js";

const DEFAULT_AGE_DAYS = 30;
const BATCH_SIZE = 20;
const GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent";

interface CompactResult {
  compacted: number;
  deleted: number;
  summaries: number;
}

/** Primary: Gemini 2.5 Flash summary */
async function geminiSummary(chunks: Array<{ chunk_text: string; source_date: string }>, dateRange: string): Promise<string | null> {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) return null;
  const combined = chunks.map((c) => `[${c.source_date}] ${c.chunk_text}`).join("\n\n");
  const prompt = `Você é um compressor de memória de agentes de IA. Resuma os seguintes ${chunks.length} registros (período: ${dateRange}) em 2-3 frases densas em PT-BR. Preserve: decisões, lições, nomes de pessoas/projetos, datas importantes. Descarte: detalhes operacionais repetidos, contexto expirado.\n\nRegistros:\n${combined.substring(0, 8000)}\n\nResumo (2-3 frases):`;
  try {
    const res = await fetch(`${GEMINI_URL}?key=${apiKey}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contents: [{ parts: [{ text: prompt }] }],
        generationConfig: { temperature: 0.1, maxOutputTokens: 512 },
      }),
      signal: AbortSignal.timeout(30_000),
    });
    if (!res.ok) return null;
    const data = await res.json() as { candidates: Array<{ content: { parts: Array<{ text: string }> } }> };
    return data.candidates?.[0]?.content?.parts?.[0]?.text?.trim() || null;
  } catch { return null; }
}

/** Secondary: Groq summary */
async function llmSummary(chunks: Array<{ chunk_text: string; source_date: string }>, dateRange: string): Promise<string | null> {
  const apiKey = process.env.GROQ_API_KEY;
  if (!apiKey) return null;

  const combined = chunks.map((c) => `[${c.source_date}] ${c.chunk_text}`).join("\n\n");
  const prompt = `Você é um compressor de memória de agentes de IA. Resuma os seguintes ${chunks.length} registros de memória (período: ${dateRange}) em 2-3 frases densas em PT-BR. Preserve: decisões, lições, nomes de pessoas/projetos, datas importantes. Descarte: detalhes operacionais repetidos, contexto expirado.\n\nRegistros:\n${combined.substring(0, 3000)}\n\nResumo (2-3 frases):`;

  try {
    const res = await fetch("https://api.groq.com/openai/v1/chat/completions", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": `Bearer ${apiKey}` },
      body: JSON.stringify({
        model: "llama-3.3-70b-versatile",
        messages: [{ role: "user", content: prompt }],
        temperature: 0.1,
        max_tokens: 256,
      }),
      signal: AbortSignal.timeout(20_000),
    });
    if (!res.ok) return null;
    const data = await res.json() as { choices?: Array<{ message?: { content?: string } }> };
    return data.choices?.[0]?.message?.content?.trim() || null;
  } catch {
    return null;
  }
}

/** Fallback: extract first meaningful sentence from each chunk */
function firstSentenceFallback(chunks: Array<{ chunk_text: string; source_date: string }>): string {
  return chunks.map(c => {
    const s = c.chunk_text.split(/[.!?\n]/).filter(s => s.trim().length > 10)[0];
    return s ? s.trim() : c.chunk_text.substring(0, 100);
  }).join("\n");
}

/**
 * Group old chunks by source_file and type, merge into LLM summaries
 */
async function _compactImpl(ageDays: number = DEFAULT_AGE_DAYS, dryRun: boolean = false): Promise<CompactResult> {
  const db = getDb();
  const cutoffDate = new Date(Date.now() - ageDays * 24 * 60 * 60 * 1000)
    .toISOString().split("T")[0];

  // Find old chunks grouped by source_file + chunk_type
  const groups = db.prepare(`
    SELECT source_file, chunk_type, COUNT(*) as cnt,
           GROUP_CONCAT(id) as ids,
           MIN(source_date) as first_date,
           MAX(source_date) as last_date
    FROM chunks
    WHERE source_date < ? AND chunk_type IN ('daily', 'team', 'other')
    GROUP BY source_file, chunk_type
    HAVING cnt >= 3
    ORDER BY cnt DESC
    LIMIT ?
  `).all(cutoffDate, BATCH_SIZE) as Array<{
    source_file: string; chunk_type: string; cnt: number;
    ids: string; first_date: string; last_date: string;
  }>;

  if (groups.length === 0) {
    console.log("[COMPACT] No chunks old enough to compact");
    return { compacted: 0, deleted: 0, summaries: 0 };
  }

  let totalCompacted = 0;
  let totalDeleted = 0;
  let totalSummaries = 0;

  for (const group of groups) {
    const chunkIds = group.ids.split(",").map(Number);

    // Get all chunks in this group
    const placeholders = chunkIds.map(() => "?").join(",");
    const chunks = db.prepare(
      `SELECT id, chunk_text, source_date FROM chunks WHERE id IN (${placeholders}) ORDER BY source_date ASC`
    ).all(...chunkIds) as Array<{ id: number; chunk_text: string; source_date: string }>;

    // Create summary: Gemini (primary) → Groq (secondary) → first-sentence (fallback)
    const dateRange = `${group.first_date}..${group.last_date}`;
    const llmResult = (await geminiSummary(chunks, dateRange)) ?? (await llmSummary(chunks, dateRange));
    const summaryBody = llmResult
      ? llmResult
      : firstSentenceFallback(chunks);

    if (llmResult) {
      console.log(`[COMPACT] LLM summary OK for ${group.source_file}`);
    } else {
      console.log(`[COMPACT] LLM unavailable — using first-sentence fallback for ${group.source_file}`);
    }

    const summaryText = `[Compacted ${chunks.length} entries from ${dateRange}]\n` + summaryBody;

    if (dryRun) {
      console.log(`[DRY-RUN] Would compact ${chunks.length} chunks from ${group.source_file} (${group.chunk_type})`);
      totalCompacted += chunks.length;
      continue;
    }

    // Insert summary chunk
    db.prepare(`
      INSERT INTO chunks (source_file, chunk_text, chunk_type, source_date, is_consolidated, metadata)
      VALUES (?, ?, ?, ?, 1, ?)
    `).run(
      group.source_file,
      summaryText,
      group.chunk_type,
      group.last_date,
      JSON.stringify({ compacted_from: chunkIds.length, date_range: `${group.first_date}..${group.last_date}` })
    );
    totalSummaries++;

    // Delete original chunks
    db.prepare(`DELETE FROM chunks WHERE id IN (${placeholders})`).run(...chunkIds);
    totalDeleted += chunks.length;
    totalCompacted += chunks.length;

    console.log(`[COMPACT] ${group.source_file} (${group.chunk_type}): ${chunks.length} → 1 summary`);
  }

  // Update meta
  db.prepare(
    "INSERT OR REPLACE INTO meta (key, value) VALUES ('last_compaction', datetime('now'))"
  ).run();

  return { compacted: totalCompacted, deleted: totalDeleted, summaries: totalSummaries };
}

// A1 (2026-04-25): wrap mutating compact() with snapshot + audit (CLAUDE.md regra #15).
// dryRun=true skips wrap (no DB mutation, no snapshot needed).
// Issue #3B (2026-05-21): db_source is now explicit — 'main' (prod nox-mem.db).
export async function compact(ageDays: number = 90, dryRun: boolean = false): Promise<CompactResult> {
  if (dryRun) return _compactImpl(ageDays, true);
  return withOpAudit("compact", { db_source: 'main' }, async () => {
    const result = await _compactImpl(ageDays, false);
    return { compacted: result.compacted, deleted: result.deleted, summaries: result.summaries, affected_rows: result.deleted, notes: `${result.summaries} summaries created from ${result.compacted} chunks` };
  }) as unknown as Promise<CompactResult>;
}
