/**
 * privacy-br — A1.1 BR PII filter, public API.
 *
 * Uso típico:
 *
 *   import { redactBrPii } from "./lib/privacy-br";
 *   const r = redactBrPii("CPF do João: 111.444.777-35");
 *   // r.redacted === "CPF do João: [REDACTED:cpf]"
 *
 * Integração com A1 (US):
 *
 *   import { redact as redactUs } from "../privacy/filter.js";
 *   import { redactAll } from "./lib/privacy-br";
 *   const r = redactAll(text, redactUs);
 */

export * from "./types.js";
export {
  validateCpf,
  validateCnpj,
  validateCnh,
  validateTituloEleitor,
  validateCep,
  luhn,
  BR_PATTERNS,
  BR_PATTERN_BY_KIND,
} from "./patterns.js";
export { detectBrPii, detectBrPiiByKinds, groupMatchesByKind } from "./detector.js";
export { redactBrPii, summarizeMatches } from "./redact.js";
export {
  redactAll,
  redactBrOnly,
  noopUsRedactor,
  type CombinedRedactResult,
  type UsRedactorFn,
} from "./integration.js";
