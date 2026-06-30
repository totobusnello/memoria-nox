/**
 * search-expansion.ts — Multi-perspective query rewriting via Gemini 2.5 Flash.
 *
 * Fase 1.6 — gera 2 variantes (técnica + paráfrase) além da query original.
 * Queries com <3 palavras, config off, ou Gemini unreachable retornam [query] intacta.
 *
 * Telemetria: retorna também o número de variantes efetivamente usadas para
 * gravar em search_telemetry.variants_count.
 */

import { getDb } from "./db.js";

const GEMINI_API_KEY = process.env.GEMINI_API_KEY || "";
const GEMINI_MODEL = "gemini-2.5-flash";
const API_BASE = "https://generativelanguage.googleapis.com/v1beta";
const TIMEOUT_MS = 2500;

const EXPANSION_PROMPT = `Você reescreve queries de busca para um sistema de memória técnica/executiva (PT-BR + EN misturados). Gere 2 variantes ALÉM da original.

Variante 1 (técnica): use termos técnicos precisos, entidades explícitas, jargão do domínio (ex: "gateway", "systemd", "Gemini", "KG", "nox-mem", "FTS", nomes de projetos/ferramentas).

Variante 2 (paráfrase): reformule em linguagem natural, troque palavras por sinônimos, mantenha a intenção.

Regras: CADA variante deve ter 3-10 palavras. NUNCA repita a query original. NUNCA invente fatos. Se a query for técnica demais para parafrasear (ex: "SQLITE_BUSY"), paráfrase explica o termo em PT-BR.

Query original:
`;

export interface ExpansionResult {
  variants: string[]; // [original, v1, v2] ou [original] se skipped
  skipped: boolean;
  reason?: "too_short" | "disabled" | "gemini_failed" | "no_api_key";
}

/**
 * Lê config `expansion_enabled` da tabela meta. Default = true (plano Fase 1.6).
 * Toggle sem redeploy: UPDATE meta SET value='false' WHERE key='expansion_enabled';
 */
export function isExpansionEnabled(): boolean {
  try {
    const db = getDb();
    const row = db.prepare("SELECT value FROM meta WHERE key = 'expansion_enabled'").get() as { value: string } | undefined;
    if (!row) return true; // default on
    return row.value !== "false" && row.value !== "0";
  } catch {
    return true;
  }
}

export async function expandQuery(query: string): Promise<ExpansionResult> {
  const trimmed = query.trim();
  const wordCount = trimmed.split(/\s+/).filter(Boolean).length;

  if (wordCount < 3) {
    return { variants: [trimmed], skipped: true, reason: "too_short" };
  }
  if (!isExpansionEnabled()) {
    return { variants: [trimmed], skipped: true, reason: "disabled" };
  }
  if (!GEMINI_API_KEY) {
    return { variants: [trimmed], skipped: true, reason: "no_api_key" };
  }

  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

    const url = `${API_BASE}/models/${GEMINI_MODEL}:generateContent?key=${GEMINI_API_KEY}`;
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      body: JSON.stringify({
        contents: [{ parts: [{ text: EXPANSION_PROMPT + trimmed }] }],
        generationConfig: {
          responseMimeType: "application/json",
          responseSchema: {
            type: "OBJECT",
            properties: {
              technical: { type: "STRING" },
              paraphrase: { type: "STRING" },
            },
            required: ["technical", "paraphrase"],
          },
          temperature: 0.2,
          maxOutputTokens: 256,
          thinkingConfig: { thinkingBudget: 0 },
        },
      }),
    }).finally(() => clearTimeout(timer));

    if (!resp.ok) {
      return { variants: [trimmed], skipped: true, reason: "gemini_failed" };
    }

    const data = await resp.json() as { candidates?: Array<{ content?: { parts?: Array<{ text?: string }> } }> };
    const raw = data.candidates?.[0]?.content?.parts?.[0]?.text;
    if (!raw) return { variants: [trimmed], skipped: true, reason: "gemini_failed" };

    const parsed = JSON.parse(raw) as { technical?: string; paraphrase?: string };
    const v1 = (parsed.technical || "").trim();
    const v2 = (parsed.paraphrase || "").trim();

    const variants = [trimmed];
    if (v1 && v1.toLowerCase() !== trimmed.toLowerCase() && v1.split(/\s+/).length >= 2) variants.push(v1);
    if (v2 && v2.toLowerCase() !== trimmed.toLowerCase() && v2.toLowerCase() !== v1.toLowerCase() && v2.split(/\s+/).length >= 2) variants.push(v2);

    return { variants, skipped: variants.length === 1, reason: variants.length === 1 ? "gemini_failed" : undefined };
  } catch {
    return { variants: [trimmed], skipped: true, reason: "gemini_failed" };
  }
}
