/**
 * privacy-br/integration.ts — combina A1 (US) + A1.1 (BR) em pipeline único.
 *
 * Ordem:
 *   1. A1.1 BR primeiro — padrões mais específicos (CNPJ 14 dig, CEP hífenado).
 *      Se rodássemos A1 antes, o pattern genérico `credit-card` poderia
 *      engolir 16 dígitos que na verdade são parte de cartão BR + CNPJ
 *      adjacente (raro mas possível em logs CSV).
 *   2. A1 US depois — padrões genéricos (env vars, JWT, AWS, etc).
 *
 * Como A1 lives em `staged-privacy/` (sibling), o consumidor deve importar
 * a função `redact` de lá e passar como argumento. Mantemos `combineRedactors`
 * agnostic da implementação A1 — facilita testar em isolamento.
 *
 * Contrato esperado do A1: função (text) => { text, redactionCount, kinds }
 */

import { redactBrPii } from "./redact.js";
import type { BrPatternMatch } from "./types.js";

/**
 * Resultado agregado A1 + A1.1.
 */
export interface CombinedRedactResult {
  /** Texto final, após BR e US redaction */
  text: string;
  /** Total de redações (BR + US) */
  redactionCount: number;
  /** Breakdown por source */
  bySource: {
    br: { count: number; kinds: string[] };
    us: { count: number; kinds: string[] };
  };
  /** Matches BR detalhados — útil pra telemetria/audit */
  brMatches: BrPatternMatch[];
}

/**
 * Tipo do redactor A1 (US) — assinatura do `redact` em
 * `staged-privacy/edits/privacy/filter.ts`.
 */
export type UsRedactorFn = (text: string) => {
  text: string;
  redactionCount: number;
  kinds: string[];
};

/**
 * Roda BR (A1.1) seguido de US (A1) sobre o mesmo texto.
 *
 * @param text       Texto bruto
 * @param usRedactor Função A1 importada do staged-privacy
 * @param options    Override de confidence threshold (default 0.5) e mode
 */
export function redactAll(
  text: string,
  usRedactor: UsRedactorFn,
  options: { minConfidence?: number; mode?: "default" | "preserve" | "hash" } = {},
): CombinedRedactResult {
  const { minConfidence = 0.5, mode = "default" } = options;

  if (typeof text !== "string" || text.length === 0) {
    return {
      text: text ?? "",
      redactionCount: 0,
      bySource: { br: { count: 0, kinds: [] }, us: { count: 0, kinds: [] } },
      brMatches: [],
    };
  }

  // Phase 1: BR
  const br = redactBrPii(text, { minConfidence, mode });
  const brKinds = Array.from(new Set(br.matches.map((m) => m.kind)));

  // Phase 2: US (sobre texto já redactado com BR)
  const us = usRedactor(br.redacted);

  return {
    text: us.text,
    redactionCount: br.redactionCount + us.redactionCount,
    bySource: {
      br: { count: br.redactionCount, kinds: brKinds },
      us: { count: us.redactionCount, kinds: us.kinds },
    },
    brMatches: br.matches,
  };
}

/**
 * Versão standalone (só BR) — útil quando A1 não está disponível ou
 * quando o caller só quer testar o A1.1.
 */
export function redactBrOnly(
  text: string,
  options: { minConfidence?: number; mode?: "default" | "preserve" | "hash" } = {},
): CombinedRedactResult {
  const br = redactBrPii(text, options);
  const brKinds = Array.from(new Set(br.matches.map((m) => m.kind)));
  return {
    text: br.redacted,
    redactionCount: br.redactionCount,
    bySource: {
      br: { count: br.redactionCount, kinds: brKinds },
      us: { count: 0, kinds: [] },
    },
    brMatches: br.matches,
  };
}

/**
 * No-op US redactor (pra testes que só rodam BR).
 */
export const noopUsRedactor: UsRedactorFn = (text) => ({
  text,
  redactionCount: 0,
  kinds: [],
});
