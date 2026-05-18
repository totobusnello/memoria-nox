/**
 * privacy-br/types.ts — A1.1 BR PII pattern type definitions.
 *
 * Cobre PII brasileiro: CPF, CNPJ, chaves PIX (4 formatos), CEP, RG,
 * CNH, Título de Eleitor, telefone BR, cartão de crédito BR.
 *
 * Cada match carrega `confidence` derivada de:
 *   - High (> 0.9) : dígitos verificadores validados (CPF/CNPJ/cartão Luhn)
 *   - Medium (0.6-0.9) : formato bate sem possibilidade de validar
 *   - Low (< 0.6)   : padrão amplo, alto risco de falso positivo (UUID, RG)
 *
 * Confiança numérica explícita (não enum) pra permitir comparações finas
 * em scoring downstream (ex: redactor que só age se >= 0.7).
 */

/** Categorias de PII brasileiro suportadas pelo A1.1 */
export type BrPatternKind =
  | "cpf"
  | "cnpj"
  | "pix_email"
  | "pix_phone"
  | "pix_cpf"
  | "pix_uuid"
  | "cep"
  | "rg"
  | "cnh"
  | "titulo_eleitor"
  | "telefone_br"
  | "cartao_br";

/**
 * Match individual produzido pelo detector.
 *
 * - `raw`        : substring exatamente como apareceu no texto original
 * - `normalized` : forma canônica (só dígitos, lowercase email, etc.)
 *                  útil pra dedup, telemetria e compare semântico
 * - `position`   : [start, end] indices do match no texto original
 *                  (end exclusivo, padrão JS String slice)
 * - `confidence` : 0.0–1.0, ver buckets High/Medium/Low acima
 */
export interface BrPatternMatch {
  kind: BrPatternKind;
  raw: string;
  normalized: string;
  position: [number, number];
  confidence: number;
}

/**
 * Resultado da redação A1.1.
 */
export interface BrRedactResult {
  /** Texto após substituição dos matches por marcadores `[REDACTED:<kind>]` */
  redacted: string;
  /** Quantidade total de redações aplicadas */
  redactionCount: number;
  /** Matches detectados (ordenados por position) — útil pra telemetria */
  matches: BrPatternMatch[];
}

/**
 * Buckets de confiança usados em thresholding downstream.
 */
export const CONFIDENCE = {
  HIGH: 0.95,
  MEDIUM_HIGH: 0.85,
  MEDIUM: 0.75,
  MEDIUM_LOW: 0.65,
  LOW: 0.5,
  VERY_LOW: 0.3,
} as const;
