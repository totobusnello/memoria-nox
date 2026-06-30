/**
 * privacy/index.js — public API surface for A1 + A1.1 in extension scope.
 *
 * Importação preferida em todos os componentes (background, content,
 * popup, options). Mantém um único ponto de entrada — facilita futuro
 * port pra Web Worker ou WASM se for o caso.
 */

export { redactAll, scanRedactions } from "./redact.js";
export {
  ALL_PATTERNS,
  PATTERN_BY_KIND,
  PATTERN_COUNT,
  CONFIDENCE,
} from "./patterns.js";
export {
  validateCpf,
  validateCnpj,
  validateCep,
  validateCnh,
  validateTituloEleitor,
  luhn,
  digitsOnly,
} from "./validators.js";
