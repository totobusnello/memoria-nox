/**
 * privacy-br/redact.ts — A1.1 BR PII redaction.
 *
 * Substitui matches detectados por marcadores `[REDACTED:<kind>]`.
 *
 * Modos de substituição:
 *   - default   : `[REDACTED:cpf]` (curto, informativo)
 *   - preserve  : pad com espaços pra manter offsets (length-sensitive contexts)
 *   - hash      : `[REDACTED:cpf:abc123]` com hash dos últimos 6 chars da
 *                  versão normalizada — útil pra dedup downstream sem
 *                  reidentificar.
 *
 * Atenção: o array `matches` é processado da DIREITA pra ESQUERDA pra que
 * a posição dos matches restantes não shifte com a substituição. Crítico
 * pra correctness — bug clássico de "regex offset drift" se feito ASC.
 */

import { detectBrPii } from "./detector.js";
import { BrPatternMatch, BrRedactResult } from "./types.js";

export interface RedactOptions {
  /** Substitution mode (default: 'default') */
  mode?: "default" | "preserve" | "hash";
  /** Confidence threshold — só redacta se >= este valor (default 0.5) */
  minConfidence?: number;
  /** Se true, inclui pix_cpf além de cpf (default false) */
  includePixCpf?: boolean;
  /** Override do marker; default `[REDACTED:<kind>]` */
  formatMarker?: (kind: string) => string;
}

/**
 * Hash curto e estável para dedup — FNV-1a 32-bit em hex (6 chars).
 * NÃO é criptográfico. Único propósito: agrupar redactions equivalentes
 * sem expor o valor original.
 */
function shortHash(s: string): string {
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  // Converte pra unsigned e pega 6 hex chars
  return (h >>> 0).toString(16).padStart(8, "0").slice(0, 6);
}

/**
 * Redacta toda PII brasileira encontrada no texto.
 *
 * @returns objeto { redacted, redactionCount, matches }
 */
export function redactBrPii(
  text: string,
  options: RedactOptions = {},
): BrRedactResult {
  const {
    mode = "default",
    minConfidence = 0.5,
    includePixCpf = false,
    formatMarker,
  } = options;

  if (typeof text !== "string" || text.length === 0) {
    return { redacted: text ?? "", redactionCount: 0, matches: [] };
  }

  const matches = detectBrPii(text, { minConfidence, includePixCpf });

  if (matches.length === 0) {
    return { redacted: text, redactionCount: 0, matches: [] };
  }

  // Process from right to left so positions stay valid as we mutate
  const sorted = [...matches].sort((a, b) => b.position[0] - a.position[0]);

  let redacted = text;
  for (const m of sorted) {
    const marker = renderMarker(m, mode, formatMarker);
    const [start, end] = m.position;
    redacted = redacted.substring(0, start) + marker + redacted.substring(end);
  }

  return {
    redacted,
    redactionCount: matches.length,
    matches,
  };
}

function renderMarker(
  m: BrPatternMatch,
  mode: "default" | "preserve" | "hash",
  formatMarker?: (kind: string) => string,
): string {
  if (formatMarker) return formatMarker(m.kind);

  switch (mode) {
    case "preserve": {
      // Pad to original length pra manter offsets — usa underscores
      const tag = `[REDACTED:${m.kind}]`;
      const origLen = m.position[1] - m.position[0];
      if (tag.length === origLen) return tag;
      if (tag.length < origLen) {
        return tag + "_".repeat(origLen - tag.length);
      }
      // tag maior que original — caller aceita drift; retorna tag
      return tag;
    }
    case "hash": {
      const h = shortHash(m.normalized);
      return `[REDACTED:${m.kind}:${h}]`;
    }
    default:
      return `[REDACTED:${m.kind}]`;
  }
}

/**
 * Helper: estatísticas resumidas pós-redaction. Usado por integração + eval.
 */
export function summarizeMatches(
  matches: BrPatternMatch[],
): {
  total: number;
  byKind: Record<string, number>;
  avgConfidence: number;
  lowConfidenceCount: number;
} {
  const byKind: Record<string, number> = {};
  let totalConf = 0;
  let lowCount = 0;
  for (const m of matches) {
    byKind[m.kind] = (byKind[m.kind] ?? 0) + 1;
    totalConf += m.confidence;
    if (m.confidence < 0.6) lowCount++;
  }
  return {
    total: matches.length,
    byKind,
    avgConfidence: matches.length > 0 ? totalConf / matches.length : 0,
    lowConfidenceCount: lowCount,
  };
}
