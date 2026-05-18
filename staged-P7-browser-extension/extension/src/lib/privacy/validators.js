/**
 * validators.js — Check-digit validators for BR PII + Luhn for cards.
 *
 * Ported from staged-A1.1/edits/src/lib/privacy-br/patterns.ts to vanilla
 * JS (ESM). NO runtime dependencies. NO TypeScript at runtime — chrome
 * extension classic loader.
 *
 * Each validator returns boolean. Caller (redact.js) maps false → keep
 * original text (avoid false-positive redactions over coincidental digit
 * sequences like timestamps, SKUs, version numbers, etc.).
 */

/**
 * CPF check-digit validation.
 *
 * Algoritmo Receita Federal:
 *   - DV1: pesos [10..2] sobre primeiros 9 dígitos; mod = sum % 11;
 *     dv1 = mod < 2 ? 0 : 11 - mod.
 *   - DV2: pesos [11..2] sobre primeiros 10 dígitos (incluindo dv1); idem.
 *   - Rejeita 11 dígitos idênticos (000...0, 111...1, etc.) — placeholders.
 *
 * @param {string} digits Exatamente 11 dígitos sem pontuação.
 * @returns {boolean}
 */
export function validateCpf(digits) {
  if (!/^\d{11}$/.test(digits)) return false;
  if (/^(\d)\1{10}$/.test(digits)) return false;

  let sum = 0;
  for (let i = 0; i < 9; i++) {
    sum += parseInt(digits[i], 10) * (10 - i);
  }
  let mod = sum % 11;
  const dv1 = mod < 2 ? 0 : 11 - mod;
  if (dv1 !== parseInt(digits[9], 10)) return false;

  sum = 0;
  for (let i = 0; i < 10; i++) {
    sum += parseInt(digits[i], 10) * (11 - i);
  }
  mod = sum % 11;
  const dv2 = mod < 2 ? 0 : 11 - mod;
  return dv2 === parseInt(digits[10], 10);
}

/**
 * CNPJ check-digit validation.
 *
 * Pesos oficiais (diferentes do CPF):
 *   - DV1: [5,4,3,2,9,8,7,6,5,4,3,2] sobre primeiros 12 dígitos.
 *   - DV2: [6,5,4,3,2,9,8,7,6,5,4,3,2] sobre primeiros 13 dígitos.
 *
 * @param {string} digits Exatamente 14 dígitos.
 */
export function validateCnpj(digits) {
  if (!/^\d{14}$/.test(digits)) return false;
  if (/^(\d)\1{13}$/.test(digits)) return false;

  const w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
  const w2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];

  let sum = 0;
  for (let i = 0; i < 12; i++) sum += parseInt(digits[i], 10) * w1[i];
  let mod = sum % 11;
  const dv1 = mod < 2 ? 0 : 11 - mod;
  if (dv1 !== parseInt(digits[12], 10)) return false;

  sum = 0;
  for (let i = 0; i < 13; i++) sum += parseInt(digits[i], 10) * w2[i];
  mod = sum % 11;
  const dv2 = mod < 2 ? 0 : 11 - mod;
  return dv2 === parseInt(digits[13], 10);
}

/**
 * Luhn algorithm para cartões de crédito.
 *
 * @param {string} digits Somente dígitos, 13-19 chars.
 */
export function luhn(digits) {
  if (!/^\d+$/.test(digits)) return false;
  let sum = 0;
  let alt = false;
  for (let i = digits.length - 1; i >= 0; i--) {
    let n = parseInt(digits[i], 10);
    if (alt) {
      n *= 2;
      if (n > 9) n -= 9;
    }
    sum += n;
    alt = !alt;
  }
  return sum % 10 === 0;
}

/**
 * CEP — 8 dígitos. Sem dígito verificador, mas rejeita 00000000 placeholder.
 */
export function validateCep(digits) {
  if (!/^\d{8}$/.test(digits)) return false;
  if (digits === "00000000") return false;
  return true;
}

/**
 * CNH (DETRAN) — 11 dígitos com algoritmo próprio (não Luhn).
 *
 * Ref: https://www.macoratti.net/alg_cnh.htm
 */
export function validateCnh(digits) {
  if (!/^\d{11}$/.test(digits)) return false;
  if (/^(\d)\1{10}$/.test(digits)) return false;

  let sum = 0;
  let dsv = 0;
  for (let i = 0, j = 9; i < 9; i++, j--) {
    sum += parseInt(digits[i], 10) * j;
  }
  let dv1 = sum % 11;
  if (dv1 >= 10) {
    dv1 = 0;
    dsv = 2;
  }
  if (dv1 !== parseInt(digits[9], 10)) return false;

  sum = 0;
  for (let i = 0, j = 1; i < 9; i++, j++) {
    sum += parseInt(digits[i], 10) * j;
  }
  const x = sum % 11;
  let dv2 = x >= 10 ? 0 : x - dsv;
  if (dv2 < 0) dv2 += 11;
  return dv2 === parseInt(digits[10], 10);
}

/**
 * Título de Eleitor (TSE) — 12 dígitos.
 *
 * 8 base + 2 UF + 2 DV. UF válida: 01-28.
 */
export function validateTituloEleitor(digits) {
  if (!/^\d{12}$/.test(digits)) return false;
  if (/^(\d)\1{11}$/.test(digits)) return false;

  const uf = digits.substring(8, 10);
  const ufNum = parseInt(uf, 10);
  if (ufNum < 1 || ufNum > 28) return false;

  const isSpMg = uf === "01" || uf === "02";

  let sum = 0;
  for (let i = 0; i < 8; i++) {
    sum += parseInt(digits[i], 10) * (i + 2);
  }
  let mod = sum % 11;
  let dv1;
  if (mod === 10) dv1 = 0;
  else if (mod === 0 && isSpMg) dv1 = 1;
  else dv1 = mod;
  if (dv1 !== parseInt(digits[10], 10)) return false;

  sum =
    parseInt(digits[8], 10) * 7 +
    parseInt(digits[9], 10) * 8 +
    dv1 * 9;
  mod = sum % 11;
  let dv2;
  if (mod === 10) dv2 = 0;
  else if (mod === 0 && isSpMg) dv2 = 1;
  else dv2 = mod;
  return dv2 === parseInt(digits[11], 10);
}

export const digitsOnly = (s) => String(s).replace(/\D/g, "");
