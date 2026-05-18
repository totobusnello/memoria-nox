/**
 * privacy-br/detector.ts — A1.1 BR PII detection orchestrator.
 *
 * Roda todos os padrões BR_PATTERNS sobre o texto e devolve matches
 * deduplicados, com overlap resolution (prefer longest match).
 *
 * Estratégia:
 *   1. Para cada pattern do catálogo, coleta todos os matches no texto.
 *   2. Aplica validate() se disponível — ajusta confidence em vez de descartar.
 *   3. Sort por position ASC, depois por length DESC (longer wins ties).
 *   4. Walk linearmente: descarta matches que overlapam com previously-accepted.
 *
 * Performance: O(N * P) onde N = len(text), P = #patterns. Não exec por chunk;
 * é chamado uma vez por documento. Para chunks de 1-5KB e 12 patterns, ~µs.
 */

import { BR_PATTERNS, BR_PATTERN_BY_KIND } from "./patterns.js";
import { BrPatternKind, BrPatternMatch, CONFIDENCE } from "./types.js";

/**
 * Detecta toda PII brasileira no texto.
 *
 * @param text         Texto bruto pra escanear
 * @param options.minConfidence  Filtra matches abaixo deste threshold (default 0)
 * @param options.includePixCpf  Se true, CPF puro também produz match pix_cpf
 *                                além de cpf. Default false (evita dup).
 * @returns Array de matches, ordenado por position ASC.
 */
export function detectBrPii(
  text: string,
  options: {
    minConfidence?: number;
    includePixCpf?: boolean;
  } = {},
): BrPatternMatch[] {
  const { minConfidence = 0, includePixCpf = false } = options;
  if (typeof text !== "string" || text.length === 0) return [];

  const rawMatches: BrPatternMatch[] = [];

  for (const def of BR_PATTERNS) {
    // Skip pix_cpf por default (covered por cpf; só inclui se caller pediu)
    if (def.kind === "pix_cpf" && !includePixCpf) continue;

    const regex = def.getRegex();

    // matchAll é mais seguro que while(exec) — não precisa gerir lastIndex
    // manualmente e funciona com regex /g.
    const iter = text.matchAll(regex);

    for (const m of iter) {
      const raw = m[1] !== undefined ? m[1] : m[0];
      const matchIndex = m.index ?? 0;
      // m.index aponta pro início do MATCH completo, incluindo qualquer
      // lookbehind. Lookbehind é zero-width, então matchIndex já está correto.
      // Mas o capture group (m[1]) pode começar depois (ex: regex com prefixo).
      // Calculamos position real procurando raw a partir de matchIndex.
      let start = matchIndex;
      if (m[0] !== raw) {
        const offset = m[0].indexOf(raw);
        if (offset >= 0) start = matchIndex + offset;
      }
      const end = start + raw.length;

      const normalized = def.normalize(raw);

      let confidence = def.confidenceWhenValid;
      if (def.validate) {
        const ok = def.validate(normalized);
        confidence = ok
          ? def.confidenceWhenValid
          : def.confidenceWhenInvalid ?? CONFIDENCE.VERY_LOW;
      }

      if (confidence < minConfidence) continue;

      rawMatches.push({
        kind: def.kind,
        raw,
        normalized,
        position: [start, end],
        confidence,
      });
    }
  }

  // ── Overlap resolution ─────────────────────────────────────────────────────
  //
  // Sort: position ASC, then length DESC (longer first), then confidence DESC,
  // then catalog order (BR_PATTERNS ordering).
  rawMatches.sort((a, b) => {
    if (a.position[0] !== b.position[0]) return a.position[0] - b.position[0];
    const lenA = a.position[1] - a.position[0];
    const lenB = b.position[1] - b.position[0];
    if (lenA !== lenB) return lenB - lenA;
    if (a.confidence !== b.confidence) return b.confidence - a.confidence;
    // Catalog order — find index in BR_PATTERNS
    const ia = BR_PATTERNS.findIndex((p) => p.kind === a.kind);
    const ib = BR_PATTERNS.findIndex((p) => p.kind === b.kind);
    return ia - ib;
  });

  // Walk + drop overlaps
  const accepted: BrPatternMatch[] = [];
  let lastEnd = -1;
  for (const m of rawMatches) {
    if (m.position[0] >= lastEnd) {
      accepted.push(m);
      lastEnd = m.position[1];
    }
    // else: overlap — descarta (sorted longest-first garante que mantemos o melhor)
  }

  return accepted;
}

/**
 * Variante: detecta apenas matches de tipos específicos.
 * Útil pra integrations que querem só CPF/CNPJ sem PIX/CEP.
 */
export function detectBrPiiByKinds(
  text: string,
  kinds: BrPatternKind[],
  options: { minConfidence?: number } = {},
): BrPatternMatch[] {
  const all = detectBrPii(text, options);
  const set = new Set(kinds);
  return all.filter((m) => set.has(m.kind));
}

/**
 * Helper de debug — agrupa matches por kind, útil pra eval/telemetria.
 */
export function groupMatchesByKind(
  matches: BrPatternMatch[],
): Record<BrPatternKind, BrPatternMatch[]> {
  const out: Partial<Record<BrPatternKind, BrPatternMatch[]>> = {};
  for (const m of matches) {
    if (!out[m.kind]) out[m.kind] = [];
    out[m.kind]!.push(m);
  }
  // Garante todas as keys presentes (mesmo vazias) — facilita iteração
  for (const def of BR_PATTERNS) {
    if (!out[def.kind]) out[def.kind] = [];
  }
  return out as Record<BrPatternKind, BrPatternMatch[]>;
}

// Re-export pra consumidores externos
export { BR_PATTERN_BY_KIND };
