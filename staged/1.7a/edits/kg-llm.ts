/**
 * kg-llm.ts — LLM-powered entity and relation extraction for Knowledge Graph v2
 * Uses Gemini 2.5 Flash Lite (flash-lite, 500 RPM) for rich extraction.
 * Migrated from Ollama llama3.2:3b (2026-04-11) — Ollama was inactive since ~March.
 *
 * Fase 1.7a (2026-04-19):
 *   - Ontology grounding: campos ricos por tipo (project.value_brl, person.whatsapp_number, etc)
 *   - Multi-stage fast-path regex PT-BR: detecta entidades óbvias sem chamar Gemini
 *     (valores R$/US$, CNPJ/CPF, datas BR, telefones +55, emails, URLs)
 *   - Economia esperada: 30-40% de chamadas Gemini em chunks densos
 *
 * L4 hybrid orchestration (2026-05-21):
 *   NOX_KG_EXTRACT_MODE controls the extraction pipeline:
 *   - 'regex_only'     — regex tier only, no Gemini call
 *   - 'gemini_only'    — pre-L4 behavior, Gemini for every chunk
 *   - 'hybrid_shadow'  — BOTH run, diff logged, Gemini result returned (DEFAULT)
 *   - 'hybrid_active'  — regex first; Gemini only when regex insufficient
 *
 * CRITICAL: DEFAULT is 'hybrid_shadow'. Do NOT change to 'hybrid_active' without
 * 7-day shadow validation showing regex coverage ≥85% of Gemini-found entities.
 *
 * SECURITY: GEMINI_API_KEY MUST come from process.env. NEVER hardcode.
 */

import { appendFileSync } from "fs";
import { join } from "path";
import { regexExtract, isAmbiguous, type RegexExtractionResult } from "./regex-extract.js";
import { logExtractDiff, buildDiffEntry } from "./lib/kg-extract-telemetry.js";

// SECURITY: API key from env only — never hardcode.
const GEMINI_API_KEY = process.env["GEMINI_API_KEY"] ?? "";
// CLAUDE.md rule #3: use flash-lite, NOT flash (quota) or 2.0-flash (deprecated).
const GEMINI_MODEL = "gemini-2.5-flash-lite";
const API_BASE = "https://generativelanguage.googleapis.com/v1beta";

// ─── Extraction mode ──────────────────────────────────────────────────────────

/** L4 extraction mode from env. Defaults to hybrid_shadow (shadow-mode mandatory). */
export type KGExtractMode = "regex_only" | "gemini_only" | "hybrid_shadow" | "hybrid_active";

const VALID_MODES: KGExtractMode[] = ["regex_only", "gemini_only", "hybrid_shadow", "hybrid_active"];

function resolveExtractMode(): KGExtractMode {
  const raw = process.env["NOX_KG_EXTRACT_MODE"];
  if (!raw) return "hybrid_shadow"; // safe default
  if (VALID_MODES.includes(raw as KGExtractMode)) return raw as KGExtractMode;
  logKG("WARN", `Unknown NOX_KG_EXTRACT_MODE="${raw}", defaulting to hybrid_shadow`);
  return "hybrid_shadow";
}

// ─── Chunk context passed from ingest router ──────────────────────────────────

export interface ChunkContext {
  chunkId?: string;
  section?: "compiled" | "frontmatter" | "timeline" | "prose" | null;
  type?: "entity" | "spec" | "audit" | "conversation" | "daily_log" | "freeform" | "code" | "other";
}

// ─── Logging ──────────────────────────────────────────────────────────────────

const LOG_PATH = join(process.cwd(), "nox-mem.log");
let consecutiveFailures = 0;

function logKG(level: "INFO" | "WARN" | "ERROR", msg: string): void {
  const ts = new Date().toISOString().replace("T", " ").substring(0, 19);
  const line = `[${ts}] [KG-LLM] ${level}: ${msg}\n`;
  try {
    appendFileSync(LOG_PATH, line);
  } catch {
    // Log write failure must not crash extraction.
  }
  if (level === "ERROR") {
    console.error(`[KG-LLM] ${msg}`);
  }
}

// ─── Types ────────────────────────────────────────────────────────────────────

type EntityType =
  | "person" | "project" | "agent" | "tool" | "concept"
  | "organization" | "technology" | "document" | "decision" | "metric";

interface LLMEntity {
  name: string;
  type: EntityType;
  attributes?: Record<string, string | number | boolean>;
}

// E05 (2026-05-02) — Edge Typing FULL: closed enum 7 values per CLAUDE.md D12/D13.
export type RelationReason =
  | "depends_on" | "derived_from" | "opposes" | "extends"
  | "replaces" | "mentions" | "unknown";

export const VALID_RELATION_REASONS: RelationReason[] = [
  "depends_on", "derived_from", "opposes", "extends", "replaces", "mentions", "unknown",
];

// E05 B1: defensive mapping — recover reason from relation_type literal when Gemini omits it.
const RELATION_TYPE_TO_REASON: Record<string, RelationReason> = {
  depends_on: "depends_on", "depends on": "depends_on", requires: "depends_on", needs: "depends_on",
  blocked_by: "depends_on", "blocked by": "depends_on", uses: "depends_on", consumes: "depends_on",
  mentions: "mentions", mentioned_in: "mentions", "mentioned in": "mentions",
  mentioned_with: "mentions", "mentioned with": "mentions", references: "mentions",
  "referenced by": "mentions", "includes commit": "mentions",
  extends: "extends", enhances: "extends", augments: "extends",
  replaces: "replaces", supersedes: "replaces", migrates_from: "replaces",
  derived_from: "derived_from", "derived from": "derived_from",
  extracted_from: "derived_from", "extracted from": "derived_from", generated_from: "derived_from",
  opposes: "opposes", contradicts: "opposes", blocks: "opposes", conflicts_with: "opposes",
};

export function mapRelationTypeToReason(relationType: string | undefined): RelationReason | null {
  if (typeof relationType !== "string") return null;
  return RELATION_TYPE_TO_REASON[relationType.toLowerCase().trim()] ?? null;
}

export function normalizeRelationReason(raw: unknown, relationType?: string): RelationReason {
  if (typeof raw === "string") {
    const v = raw.toLowerCase().trim();
    if ((VALID_RELATION_REASONS as string[]).includes(v) && v !== "unknown") return v as RelationReason;
  }
  const inferred = mapRelationTypeToReason(relationType);
  if (inferred) return inferred;
  return "unknown";
}

interface LLMRelation {
  source: string;
  relation: string;
  target: string;
  reason?: RelationReason;
}

export interface LLMExtraction {
  entities: LLMEntity[];
  relations: LLMRelation[];
  fast_path_used?: boolean;
  /** L4 extension: regex extraction result when mode != gemini_only. */
  regex_result?: RegexExtractionResult;
  /** L4 extension: extraction mode used for this chunk. */
  extract_mode?: KGExtractMode;
}

// ─── Fast-path regex (PT-BR) ──────────────────────────────────────────────────

const RE_VALUE_BRL = /R\$\s?\d[\d.,]*(?:\s?(?:mil|milh[ãa]o|milh[õo]es|bi|bilh[ãa]o|k|m|b))?/gi;
const RE_VALUE_USD = /US?\$\s?\d[\d.,]*(?:\s?(?:k|m|b|million|thousand|billion))?/gi;
const RE_VALUE_EUR = /€\s?\d[\d.,]*/gi;
const RE_CNPJ = /\b\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}\b/g;
const RE_CPF = /\b\d{3}\.\d{3}\.\d{3}-\d{2}\b/g;
const RE_DATE_BR = /\b\d{1,2}\/\d{1,2}\/\d{2,4}\b/g;
const RE_PHONE_BR = /\+?55[\s-]?\(?\d{2}\)?[\s-]?\d{4,5}[\s-]?\d{4}/g;
const RE_EMAIL = /[\w.+\-]+@[\w\-]+\.[\w\-.]+/g;
const RE_URL = /https?:\/\/[^\s)]+/g;
const RE_PERCENT = /\b\d+(?:[.,]\d+)?\s?%/g;
const RE_PROPER_NOUN = /\b[A-ZÁÉÍÓÚÂÊÎÔÛÀÃÕÇ][a-záéíóúâêîôûàãõç]+(?:\s+(?:de|da|do|das|dos|e)\s+)?(?:\s+[A-ZÁÉÍÓÚÂÊÎÔÛÀÃÕÇ][a-záéíóúâêîôûàãõç]+)+\b/g;

interface FastPathHit {
  kind: "value_brl" | "value_usd" | "value_eur" | "cnpj" | "cpf" | "date" | "phone" | "email" | "url" | "percent" | "proper_noun";
  match: string;
}

export function fastPathExtract(text: string): FastPathHit[] {
  const hits: FastPathHit[] = [];
  const add = (kind: FastPathHit["kind"], re: RegExp) => {
    for (const m of text.match(re) || []) hits.push({ kind, match: m.trim() });
  };
  add("value_brl", RE_VALUE_BRL);
  add("value_usd", RE_VALUE_USD);
  add("value_eur", RE_VALUE_EUR);
  add("cnpj", RE_CNPJ);
  add("cpf", RE_CPF);
  add("date", RE_DATE_BR);
  add("phone", RE_PHONE_BR);
  add("email", RE_EMAIL);
  add("url", RE_URL);
  add("percent", RE_PERCENT);
  add("proper_noun", RE_PROPER_NOUN);
  return hits;
}

// ─── Ontology grounding prompt ────────────────────────────────────────────────

const EXTRACTION_PROMPT = `Extract entities and relationships from this text (PT-BR + EN mixed). Return ONLY valid JSON.

Entity types with RICH attributes (infer from text ONLY — never invent):

- **person**: role, organization, email, whatsapp_number, notes
- **project**: status (prospect|active|closed|paused), value_brl, value_usd, stage, key_person, industry, ebitda_multiple
- **organization**: type (company|fund|institution|government), country, sector, size
- **agent**: owner, purpose, status (active|dormant)
- **document**: doc_type (contract|NDA|MoU|PDF|spreadsheet|termo|aditivo), date, parties, file_path
- **decision**: what, who, date, outcome, rationale
- **metric**: metric_name, value, unit, period
- **tool** / **concept** / **technology**: category, domain

Relation types (free-form, descriptive): works_on, decided, uses, depends_on, blocked_by, reviewed, created, manages, communicates_with, invested_in, negotiated_with, approved, rejected, owns, signed, paid, owes

Relation REASON (closed enum, REQUIRED for every relation — classify the SEMANTIC TYPE):
- **depends_on**: A requires B to exist/work (project depends_on tool; relation verbs: requires, needs, uses, blocked_by)
- **derived_from**: A is created/extracted from B (chunk derived_from document; verbs: extracted_from, generated_from)
- **opposes**: A contradicts/blocks/replaces B (decision opposes prior decision; verbs: contradicts, conflicts_with, blocks)
- **extends**: A adds capability to B (plugin extends platform, v2 extends v1; verbs: extends, enhances, augments)
- **replaces**: A supersedes/migrates from B (Gemini replaces Ollama; verbs: supersedes, migrates_from)
- **mentions**: A references/discusses B without strong dep (document mentions person; verbs: references, mentioned_in, mentioned_with, includes)
- **unknown**: ONLY when relation verb is truly ambiguous. PREFER classifying when verb maps directly to a reason above.

CRITICAL: if your relation verb already matches one of {extends, mentions, depends_on, replaces, derived_from, opposes}, ALWAYS use that as reason.

Rules:
- Entity names: proper nouns or specific identifiers (skip generic "system", "code", "file")
- Attributes: only include fields with clear textual evidence. Omit unknowns. NEVER hallucinate.
- Values: preserve original formatting ("R$ 8.5k", "USD 280K", "10,5%")
- Dates: ISO format when possible (YYYY-MM-DD), or preserve original
- Relations reference entities by exact extracted name
- Max 20 entities and 15 relations per chunk

Text:
`;

// ─── Gemini API call ──────────────────────────────────────────────────────────

async function callGemini(text: string): Promise<LLMExtraction> {
  if (!GEMINI_API_KEY) {
    logKG("ERROR", "GEMINI_API_KEY not set — KG extraction disabled");
    return { entities: [], relations: [] };
  }

  const trimmed = text.substring(0, 8000);
  try {
    const url = `${API_BASE}/models/${GEMINI_MODEL}:generateContent?key=${GEMINI_API_KEY}`;
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contents: [{ parts: [{ text: EXTRACTION_PROMPT + trimmed }] }],
        generationConfig: {
          responseMimeType: "application/json",
          responseSchema: {
            type: "OBJECT",
            properties: {
              entities: {
                type: "ARRAY",
                items: {
                  type: "OBJECT",
                  properties: {
                    name: { type: "STRING" },
                    type: { type: "STRING", enum: ["person", "project", "agent", "tool", "concept", "organization", "technology", "document", "decision", "metric"] },
                    attributes: { type: "OBJECT" },
                  },
                  required: ["name", "type"],
                },
              },
              relations: {
                type: "ARRAY",
                items: {
                  type: "OBJECT",
                  properties: {
                    source: { type: "STRING" },
                    relation: { type: "STRING" },
                    target: { type: "STRING" },
                    reason: { type: "STRING", enum: ["depends_on", "derived_from", "opposes", "extends", "replaces", "mentions", "unknown"] },
                  },
                  required: ["source", "relation", "target"],
                },
              },
            },
            required: ["entities", "relations"],
          },
          temperature: 0.1,
          maxOutputTokens: 4096,
          thinkingConfig: { thinkingBudget: 0 },
        },
      }),
    });

    if (!resp.ok) {
      const errText = await resp.text().catch(() => "unknown");
      throw new Error(`Gemini ${resp.status}: ${errText.substring(0, 200)}`);
    }

    const data = await resp.json() as {
      candidates?: Array<{ content?: { parts?: Array<{ text?: string }> } }>;
    };

    const rawText = data.candidates?.[0]?.content?.parts?.[0]?.text;
    if (!rawText) {
      logKG("WARN", "Gemini returned empty response — skipping chunk");
      return { entities: [], relations: [] };
    }

    const parsed = JSON.parse(rawText) as LLMExtraction;
    if (!Array.isArray(parsed.entities)) parsed.entities = [];
    if (!Array.isArray(parsed.relations)) parsed.relations = [];
    parsed.relations = parsed.relations.map((r) => ({ ...r, reason: normalizeRelationReason(r.reason, r.relation) }));
    parsed.fast_path_used = false;

    if (consecutiveFailures > 0) {
      logKG("INFO", `Recovered after ${consecutiveFailures} consecutive failures`);
      consecutiveFailures = 0;
    }

    return parsed;
  } catch (err: unknown) {
    consecutiveFailures++;
    const msg = err instanceof Error ? err.message : String(err);
    logKG("ERROR", `Extraction failed (${consecutiveFailures}x consecutive): ${msg}`);
    if (consecutiveFailures >= 5) {
      logKG("ERROR", "KG extraction failing repeatedly — check GEMINI_API_KEY and API status");
    }
    return { entities: [], relations: [] };
  }
}

// ─── Fast-path PT-BR (pre-existing, unchanged logic) ─────────────────────────

const FAST_PATH_THRESHOLD = 3;

function runFastPath(text: string): LLMExtraction | null {
  const fastHits = fastPathExtract(text);
  const structuredHits = fastHits.filter((h) => h.kind !== "proper_noun").length;
  if (structuredHits < FAST_PATH_THRESHOLD) return null;

  const entities: LLMEntity[] = [];
  const seen = new Set<string>();

  for (const h of fastHits) {
    const key = `${h.kind}:${h.match}`;
    if (seen.has(key)) continue;
    seen.add(key);

    if (h.kind === "email") {
      entities.push({ name: h.match, type: "person", attributes: { email: h.match } });
    } else if (h.kind === "phone") {
      entities.push({ name: h.match, type: "person", attributes: { whatsapp_number: h.match } });
    } else if (h.kind === "cnpj") {
      entities.push({ name: h.match, type: "organization", attributes: { cnpj: h.match } });
    } else if (h.kind === "cpf") {
      entities.push({ name: h.match, type: "person", attributes: { cpf: h.match } });
    } else if (h.kind === "value_brl" || h.kind === "value_usd" || h.kind === "value_eur") {
      entities.push({ name: h.match, type: "metric", attributes: { metric_name: "value", value: h.match } });
    } else if (h.kind === "url") {
      entities.push({ name: h.match, type: "document", attributes: { doc_type: "url", file_path: h.match } });
    } else if (h.kind === "percent") {
      entities.push({ name: h.match, type: "metric", attributes: { metric_name: "percent", value: h.match } });
    } else if (h.kind === "proper_noun") {
      entities.push({ name: h.match, type: "person" });
    }
    // "date" — skip (low value as isolated entity)
  }

  logKG("INFO", `Fast-path hit: ${structuredHits} structured + ${fastHits.length - structuredHits} nouns — skipped Gemini`);
  return { entities: entities.slice(0, 20), relations: [], fast_path_used: true };
}

// ─── L4 hybrid orchestration ──────────────────────────────────────────────────

/** Determine whether Gemini should run in hybrid_active mode. */
function shouldCallGeminiActive(regexResult: RegexExtractionResult, text: string, ctx: ChunkContext): boolean {
  return isAmbiguous(text, regexResult, ctx.type);
}

/**
 * Core extraction function with L4 hybrid orchestration.
 *
 * @param text    Raw chunk text.
 * @param ctx     Optional chunk context (section, type, chunkId) for telemetry + gating.
 */
export async function extractWithLLM(text: string, ctx: ChunkContext = {}): Promise<LLMExtraction> {
  const mode = resolveExtractMode();

  // ── regex_only: no Gemini call ───────────────────────────────────────────
  if (mode === "regex_only") {
    const t0 = Date.now();
    const regexResult = regexExtract(text);
    logKG("INFO", `[L4 regex_only] chunk=${ctx.chunkId ?? "?"} refs=${regexResult.totalCount} (${Date.now() - t0}ms)`);
    return {
      entities: [],
      relations: [],
      fast_path_used: false,
      regex_result: regexResult,
      extract_mode: "regex_only",
    };
  }

  // ── gemini_only: pre-L4 behavior ─────────────────────────────────────────
  if (mode === "gemini_only") {
    // Keep pre-L4 fast-path PT-BR active.
    const fastResult = runFastPath(text);
    if (fastResult) return { ...fastResult, extract_mode: "gemini_only" };
    const result = await callGemini(text);
    return { ...result, extract_mode: "gemini_only" };
  }

  // ── hybrid_shadow: run BOTH, log diff, return Gemini ─────────────────────
  if (mode === "hybrid_shadow") {
    const t0 = Date.now();
    const regexResult = regexExtract(text);
    const regexElapsed = Date.now() - t0;

    // Pre-L4 fast path still applies (fast-path PT-BR runs before Gemini).
    const fastResult = runFastPath(text);
    let geminiResult: LLMExtraction;
    let geminiElapsed: number;

    if (fastResult) {
      geminiResult = { ...fastResult, extract_mode: "hybrid_shadow" };
      geminiElapsed = 0;
    } else {
      const t1 = Date.now();
      geminiResult = await callGemini(text);
      geminiElapsed = Date.now() - t1;
    }

    // Log shadow diff.
    const diffEntry = buildDiffEntry({
      chunkId: ctx.chunkId ?? "unknown",
      section: ctx.section ?? null,
      mode: "hybrid_shadow",
      regexEntityRefs: regexResult.entityRefs.map((r) => r.key),
      regexFrontmatterRelations: regexResult.frontmatterRelations.map((r) => `${r.relationType}:${r.target}`),
      regexCodeRefs: regexResult.codeRefs.map((r) => r.key),
      geminiEntities: geminiResult.entities.map((e) => e.name),
      geminiRelations: geminiResult.relations.map((r) => `${r.source}→${r.target}`),
      latencyRegexMs: regexElapsed,
      latencyGeminiMs: geminiElapsed || null,
    });
    logExtractDiff(diffEntry);

    logKG("INFO", `[L4 shadow] chunk=${ctx.chunkId ?? "?"} regex=${regexResult.totalCount} gemini_entities=${geminiResult.entities.length} regex_ms=${regexElapsed} gemini_ms=${geminiElapsed}`);

    // Return Gemini result (shadow: Gemini is authoritative, regex is observed).
    return { ...geminiResult, regex_result: regexResult, extract_mode: "hybrid_shadow" };
  }

  // ── hybrid_active: regex first, Gemini only if needed ────────────────────
  // (Mode activated after 7-day shadow validation — NOT the default.)
  {
    const t0 = Date.now();
    const regexResult = regexExtract(text);
    const regexElapsed = Date.now() - t0;

    const needsGemini = shouldCallGeminiActive(regexResult, text, ctx);

    if (!needsGemini) {
      logKG("INFO", `[L4 active] chunk=${ctx.chunkId ?? "?"} regex_only refs=${regexResult.totalCount} (${regexElapsed}ms) — skipped Gemini`);
      // Log diff with null Gemini fields (Gemini skipped).
      logExtractDiff(buildDiffEntry({
        chunkId: ctx.chunkId ?? "unknown",
        section: ctx.section ?? null,
        mode: "hybrid_active",
        regexEntityRefs: regexResult.entityRefs.map((r) => r.key),
        regexFrontmatterRelations: regexResult.frontmatterRelations.map((r) => `${r.relationType}:${r.target}`),
        regexCodeRefs: regexResult.codeRefs.map((r) => r.key),
        geminiEntities: null,
        geminiRelations: null,
        latencyRegexMs: regexElapsed,
        latencyGeminiMs: null,
      }));
      return { entities: [], relations: [], fast_path_used: false, regex_result: regexResult, extract_mode: "hybrid_active" };
    }

    // Regex insufficient — call Gemini.
    const t1 = Date.now();
    const geminiResult = await callGemini(text);
    const geminiElapsed = Date.now() - t1;

    logKG("INFO", `[L4 active+gemini] chunk=${ctx.chunkId ?? "?"} regex=${regexResult.totalCount} gemini_entities=${geminiResult.entities.length} gemini_ms=${geminiElapsed}`);
    logExtractDiff(buildDiffEntry({
      chunkId: ctx.chunkId ?? "unknown",
      section: ctx.section ?? null,
      mode: "hybrid_active",
      regexEntityRefs: regexResult.entityRefs.map((r) => r.key),
      regexFrontmatterRelations: regexResult.frontmatterRelations.map((r) => `${r.relationType}:${r.target}`),
      regexCodeRefs: regexResult.codeRefs.map((r) => r.key),
      geminiEntities: geminiResult.entities.map((e) => e.name),
      geminiRelations: geminiResult.relations.map((r) => `${r.source}→${r.target}`),
      latencyRegexMs: regexElapsed,
      latencyGeminiMs: geminiElapsed,
    }));

    return { ...geminiResult, regex_result: regexResult, extract_mode: "hybrid_active" };
  }
}
