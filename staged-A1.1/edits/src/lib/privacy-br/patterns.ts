/**
 * privacy-br/patterns.ts — A1.1 BR PII regex catalog + validators.
 *
 * Padrões com:
 *   - Boundaries Unicode-safe via lookbehind/lookahead (NUNCA \b — falha em ç/ã/ê).
 *     Ref: feedback_js_regex_unicode_word_boundary_fails (CLAUDE.md memory).
 *   - Validação de dígito verificador onde aplicável (CPF, CNPJ, cartão Luhn).
 *   - Confidence assignada por tipo + por resultado de validação.
 *
 * Performance: regex compiladas uma vez no module-load (não dentro de loop).
 * Cada `getPattern()` retorna instância fresh com lastIndex=0 pra uso em
 * `String.matchAll` sem state leak entre chamadas concorrentes.
 *
 * Ordem do catálogo importa pra detector — mais específico/longo primeiro
 * (CNPJ antes de CPF, telefone BR antes de CEP).
 */

import { BrPatternKind, CONFIDENCE } from "./types.js";

// ─── Validators ───────────────────────────────────────────────────────────────

/**
 * CPF check-digit validation.
 *
 * Algoritmo oficial Receita Federal:
 *   - Pega primeiros 9 dígitos; multiplica cada um pelos pesos [10..2]; soma.
 *   - mod = sum % 11; dv1 = mod < 2 ? 0 : 11 - mod.
 *   - Pega primeiros 10 dígitos (incl dv1); pesos [11..2]; soma; dv2 idem.
 *   - Rejeita sequências triviais (00000000000, 11111111111, ...) — são
 *     formalmente válidos mas usados como placeholders. Causa FP em docs.
 *
 * @param digits Exatamente 11 dígitos, só números (sem pontuação).
 * @returns true se dígitos verificadores batem E não é sequência trivial.
 */
export function validateCpf(digits: string): boolean {
  if (!/^\d{11}$/.test(digits)) return false;

  // Rejeita 11 dígitos idênticos (000...0, 111...1, ..., 999...9)
  if (/^(\d)\1{10}$/.test(digits)) return false;

  // DV1
  let sum = 0;
  for (let i = 0; i < 9; i++) {
    sum += parseInt(digits[i], 10) * (10 - i);
  }
  let mod = sum % 11;
  const dv1 = mod < 2 ? 0 : 11 - mod;
  if (dv1 !== parseInt(digits[9], 10)) return false;

  // DV2
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
 * Pesos diferentes do CPF, conforme spec Receita Federal:
 *   - DV1: weights [5,4,3,2,9,8,7,6,5,4,3,2] sobre primeiros 12 dígitos.
 *   - DV2: weights [6,5,4,3,2,9,8,7,6,5,4,3,2] sobre primeiros 13 dígitos.
 *   - Rejeita 14 dígitos idênticos (placeholder).
 *
 * @param digits Exatamente 14 dígitos, só números.
 */
export function validateCnpj(digits: string): boolean {
  if (!/^\d{14}$/.test(digits)) return false;
  if (/^(\d)\1{13}$/.test(digits)) return false;

  const w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
  const w2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];

  let sum = 0;
  for (let i = 0; i < 12; i++) {
    sum += parseInt(digits[i], 10) * w1[i];
  }
  let mod = sum % 11;
  const dv1 = mod < 2 ? 0 : 11 - mod;
  if (dv1 !== parseInt(digits[12], 10)) return false;

  sum = 0;
  for (let i = 0; i < 13; i++) {
    sum += parseInt(digits[i], 10) * w2[i];
  }
  mod = sum % 11;
  const dv2 = mod < 2 ? 0 : 11 - mod;
  return dv2 === parseInt(digits[13], 10);
}

/**
 * Luhn algorithm para cartões de crédito (igual A1 US, replicado aqui pra
 * desacoplar A1.1 do staged-privacy original).
 */
export function luhn(digits: string): boolean {
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
 * CEP validation — formato 5+3 dígitos.
 * Não tem dígito verificador oficial; aceita 8 dígitos exatos com
 * faixa de prefixos plausíveis (00000-999 = inválidos por convenção
 * Correios pra alguns ranges, mas mantemos permissivo).
 *
 * Range válido: 01000-000 a 99999-999. Os Correios usam 00000-000 só
 * como placeholder; tratamos como inválido.
 */
export function validateCep(digits: string): boolean {
  if (!/^\d{8}$/.test(digits)) return false;
  // Reject placeholder 00000000
  if (digits === "00000000") return false;
  return true;
}

// ─── Pattern definitions ──────────────────────────────────────────────────────

/**
 * Interface interna do catálogo. Cada entry define:
 *   - kind            : tag canônica
 *   - getRegex()      : factory fresh com lastIndex=0
 *   - validate?       : função opcional sobre normalized; se retorna false,
 *                       confidence é rebaixada (não descartado — o detector
 *                       pode aceitar matches low-confidence com flag).
 *   - confidenceWhenValid    : confiança quando validate=true OU sem validate
 *   - confidenceWhenInvalid? : confiança quando validate=false (default: rebaixa)
 *   - normalize       : produz a `normalized` string a partir do raw match
 */
export interface BrPatternDef {
  kind: BrPatternKind;
  getRegex: () => RegExp;
  validate?: (normalized: string) => boolean;
  confidenceWhenValid: number;
  confidenceWhenInvalid?: number;
  normalize: (raw: string) => string;
}

/**
 * Boundary helpers — Unicode-safe.
 *
 * `\b` falha em pt-BR (não considera ç/ã/ê como word chars), e mesmo
 * com flag /u o problema persiste pra caracteres não-ASCII.
 *
 * Usamos lookbehind/lookahead com whitespace + pontuação + start/end:
 *   START: (?<=^|[\s(,;:./])
 *   END  : (?=[\s),;:.!?]|$)
 *
 * Cobre os cenários reais: começo de linha, depois de espaço, dentro de
 * parênteses, após dois-pontos, no fim de frase. Suporta context PT-BR.
 */
// Inclui = e " e ' e [ e < pra cobrir cenários comuns:
//   cpf=12345678901
//   "cpf": "..."
//   <cpf>...</cpf>
// Não inclui letras/dígitos — esses são word chars que devem barrar match
// (ex: SKU12345678901XYZ não deve matchar CPF interno).
const SOL = "(?<=^|[\\s(,;:./=\"'\\[<>])"; // start-of-token
const EOL = "(?=[\\s),;:.!?/=\"'\\]>-]|$)"; // end-of-token

/**
 * Helper: produz só os dígitos de uma string (remove pontuação/espaço/etc).
 */
function digitsOnly(s: string): string {
  return s.replace(/\D/g, "");
}

/**
 * Catálogo principal. Ordem importa pra resolução de overlap:
 *   CNPJ (14 dig) > telefone BR (11 dig) > CPF (11 dig) > cartão (13-19) > resto.
 *
 * O detector usa essa ordem como tiebreaker quando dois matches começam
 * na mesma posição.
 */
export const BR_PATTERNS: BrPatternDef[] = [
  // ── CNPJ ─────────────────────────────────────────────────────────────────────
  // Formatos: XX.XXX.XXX/XXXX-XX  ou  XXXXXXXXXXXXXX (14 dígitos puros)
  {
    kind: "cnpj",
    // Aceita formatado OU 14 dígitos puros (sem ambiguidade — CPF tem 11)
    getRegex: () =>
      new RegExp(
        `${SOL}(\\d{2}\\.\\d{3}\\.\\d{3}/\\d{4}-\\d{2}|\\d{14})${EOL}`,
        "g",
      ),
    validate: validateCnpj,
    confidenceWhenValid: CONFIDENCE.HIGH,
    confidenceWhenInvalid: CONFIDENCE.MEDIUM_LOW, // formato bate mas dv falha
    normalize: digitsOnly,
  },

  // ── PIX UUID (chave aleatória) ───────────────────────────────────────────────
  // Formato UUID v4: 8-4-4-4-12 hex, case-insensitive. PIX usa qualquer UUID
  // RFC 4122 v4 (variant bits 10).
  // Vem ANTES de cartão_br pra não ser engolido por padrão menos específico.
  {
    kind: "pix_uuid",
    getRegex: () =>
      new RegExp(
        `${SOL}([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12})${EOL}`,
        "g",
      ),
    // UUID v4 não tem checksum; confidence medium (formato muito específico, baixo FP)
    confidenceWhenValid: CONFIDENCE.MEDIUM_HIGH,
    normalize: (s) => s.toLowerCase(),
  },

  // ── CPF ──────────────────────────────────────────────────────────────────────
  // Formatos: XXX.XXX.XXX-XX  ou  XXXXXXXXXXX (11 dígitos puros)
  {
    kind: "cpf",
    getRegex: () =>
      new RegExp(
        `${SOL}(\\d{3}\\.\\d{3}\\.\\d{3}-\\d{2}|\\d{11})${EOL}`,
        "g",
      ),
    validate: validateCpf,
    confidenceWhenValid: CONFIDENCE.HIGH,
    confidenceWhenInvalid: CONFIDENCE.VERY_LOW, // 11 dígitos podem ser muita coisa
    normalize: digitsOnly,
  },

  // ── Cartão de crédito BR (Luhn) ──────────────────────────────────────────────
  // Cobre Visa(4), MC(5), Elo (varios), Hipercard (38/60), Amex (37/34, 15 dig).
  // 13-19 dígitos com separadores opcionais.
  {
    kind: "cartao_br",
    getRegex: () =>
      new RegExp(
        `${SOL}(\\d{4}[\\s-]?\\d{4}[\\s-]?\\d{4}[\\s-]?\\d{1,7}|\\d{13,19})${EOL}`,
        "g",
      ),
    // Reject all-same-digit sequences (e.g. 0000... passes Luhn but isn't a real card)
    validate: (n) =>
      luhn(n) &&
      n.length >= 13 &&
      n.length <= 19 &&
      !/^(\d)\1+$/.test(n),
    confidenceWhenValid: CONFIDENCE.HIGH,
    confidenceWhenInvalid: CONFIDENCE.VERY_LOW,
    normalize: digitsOnly,
  },

  // ── Telefone BR (com +55, com/sem DDD em parênteses) ─────────────────────────
  // Formatos suportados:
  //   +55 11 99999-9999
  //   +55 (11) 99999-9999
  //   (11) 99999-9999
  //   11 99999-9999
  //   (11) 9999-9999  (fixo, 8 dígitos)
  //   11999999999     (11 dígitos puros — móvel)
  // Móvel: 9 dígitos (começa com 9). Fixo: 8 dígitos.
  // DDD: 11-99 (todos válidos).
  {
    kind: "telefone_br",
    getRegex: () =>
      new RegExp(
        `${SOL}(?:\\+?55[\\s-]?)?(?:\\(?[1-9][0-9]\\)?[\\s-]?)?9?\\d{4}[\\s-]?\\d{4}${EOL}`,
        "g",
      ),
    validate: (n) => {
      // Aceita 8 (fixo sem DDD), 9 (móvel sem DDD), 10 (fixo+DDD),
      // 11 (móvel+DDD), 12 (móvel+DDD+55), 13 (móvel+DDD+55 country code)
      const len = n.length;
      if (len < 8 || len > 13) return false;
      // Se tem 13, deve começar com 55
      if (len === 13 && !n.startsWith("55")) return false;
      // Se tem 12, deve começar com 55 (fixo+DDD+55)
      if (len === 12 && !n.startsWith("55")) return false;
      // Móvel: dígito 9 deve estar na posição esperada
      // Se tem 11 (DDD+móvel): pos 2 = '9'
      if (len === 11 && n[2] !== "9") return false;
      return true;
    },
    confidenceWhenValid: CONFIDENCE.MEDIUM_HIGH,
    confidenceWhenInvalid: CONFIDENCE.LOW,
    normalize: digitsOnly,
  },

  // ── PIX telefone (+55 obrigatório no formato chave PIX) ──────────────────────
  // PIX requer +55DDD + número. É um subset do telefone_br MAS com
  // prefixo +55 OBRIGATÓRIO (do contrário não é chave PIX).
  // Vem APÓS telefone_br no catálogo — overlap resolution favorece o primeiro
  // a matchar. Pra forçar pix_phone quando aplica, detector trata como caso especial.
  {
    kind: "pix_phone",
    getRegex: () =>
      new RegExp(`${SOL}(\\+55[1-9][0-9]9\\d{8})${EOL}`, "g"),
    validate: (n) => /^55[1-9][0-9]9\d{8}$/.test(n),
    confidenceWhenValid: CONFIDENCE.HIGH,
    confidenceWhenInvalid: CONFIDENCE.MEDIUM_LOW,
    normalize: digitsOnly,
  },

  // ── PIX email ────────────────────────────────────────────────────────────────
  // Email padrão (RFC 5322 simplificada — não cobrir 100% do RFC vale o
  // trade-off; emails com quoted-string ou IP literal são raros em chunks).
  {
    kind: "pix_email",
    getRegex: () =>
      new RegExp(
        `${SOL}([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})${EOL}`,
        "g",
      ),
    // Não há "validation" formal pra email num contexto PII; mas
    // emails curtos com TLD válido têm alta confiança como chave PIX/contato.
    confidenceWhenValid: CONFIDENCE.MEDIUM_HIGH,
    normalize: (s) => s.toLowerCase(),
  },

  // ── PIX CPF (CPF não-formatado usado como chave PIX) ─────────────────────────
  // Mesmo regex de CPF "puro" (11 dígitos). Diferenciação só por context
  // (palavra "PIX" próxima) — feita downstream se desejado. Por default
  // tratamos como CPF (kind: "cpf"). pix_cpf existe pra quando o caller
  // sabe que é uma chave (via tag ou contexto) e quer marcar especificamente.
  //
  // Convenção: detector NÃO produz pix_cpf automaticamente — só via
  // chamada explícita. CPF puro vira `kind: "cpf"`.
  {
    kind: "pix_cpf",
    getRegex: () => new RegExp(`${SOL}(\\d{11})${EOL}`, "g"),
    validate: validateCpf,
    confidenceWhenValid: CONFIDENCE.HIGH,
    confidenceWhenInvalid: CONFIDENCE.VERY_LOW,
    normalize: digitsOnly,
  },

  // ── CEP ──────────────────────────────────────────────────────────────────────
  // Formato XXXXX-XXX (com hífen) ou XXXXXXXX (8 dígitos puros).
  // CUIDADO: 8 dígitos puros podem colidir com prefixo de CPF/CNPJ/telefone.
  // Aceitamos só formato hífenado por padrão pra evitar FP catastrófico.
  {
    kind: "cep",
    getRegex: () => new RegExp(`${SOL}(\\d{5}-\\d{3})${EOL}`, "g"),
    validate: validateCep,
    confidenceWhenValid: CONFIDENCE.MEDIUM_HIGH,
    confidenceWhenInvalid: CONFIDENCE.VERY_LOW,
    normalize: digitsOnly,
  },

  // ── RG ───────────────────────────────────────────────────────────────────────
  // Varia drasticamente por estado. SP usa 9 chars (8 dig + dv que pode ser X).
  // Padrão amplo: 7-9 dígitos com pontos opcionais e dígito final opcional X.
  //
  // FP risk: alto (qualquer sequência de 7-9 dígitos bate). Por isso
  // confidence ≤ MEDIUM_LOW e exige contexto explícito "RG" próximo
  // (verificado no detector).
  {
    kind: "rg",
    getRegex: () =>
      new RegExp(
        `${SOL}(\\d{1,2}\\.\\d{3}\\.\\d{3}-[\\dxX]|\\d{7,9}[\\dxX]?)${EOL}`,
        "g",
      ),
    confidenceWhenValid: CONFIDENCE.MEDIUM_LOW, // sem checksum oficial padronizado
    normalize: (s) => s.replace(/[.\-]/g, "").toUpperCase(),
  },

  // ── CNH ──────────────────────────────────────────────────────────────────────
  // 11 dígitos, sem formatação padrão. Tem dígito verificador mod 10 com
  // pesos 9..1 (não Luhn). Alta colisão com CPF — confidence só fica alta
  // se contexto "CNH" estiver próximo.
  {
    kind: "cnh",
    getRegex: () => new RegExp(`${SOL}(\\d{11})${EOL}`, "g"),
    // CNH usa algoritmo próprio — implementado em validateCnh()
    validate: (n) => validateCnh(n),
    confidenceWhenValid: CONFIDENCE.MEDIUM,
    confidenceWhenInvalid: CONFIDENCE.VERY_LOW,
    normalize: digitsOnly,
  },

  // ── Título de Eleitor ────────────────────────────────────────────────────────
  // 12 dígitos, com 2 dígitos verificadores no fim.
  // Algoritmo: pesos diferentes; ver validateTituloEleitor().
  {
    kind: "titulo_eleitor",
    getRegex: () => new RegExp(`${SOL}(\\d{12})${EOL}`, "g"),
    validate: (n) => validateTituloEleitor(n),
    confidenceWhenValid: CONFIDENCE.HIGH,
    confidenceWhenInvalid: CONFIDENCE.VERY_LOW,
    normalize: digitsOnly,
  },
];

/**
 * CNH check-digit validation.
 *
 * Algoritmo DETRAN:
 *   - DV1: pesos [9,8,7,6,5,4,3,2,1] sobre primeiros 9 dígitos. soma % 11.
 *          Se soma % 11 >= 10, dv1 = 0; senão dv1 = soma % 11.
 *          Se houve resíduo (mais de 1 dv invertido), aplica delta — ver código.
 *   - DV2: pesos [1,2,3,4,5,6,7,8,9] sobre primeiros 9 dígitos. soma % 11
 *          ajustada com dsv (delta da DV1) e fórmula similar.
 *
 * Ref: https://www.macoratti.net/alg_cnh.htm (algoritmo público DETRAN)
 *
 * @param digits 11 dígitos puros
 */
export function validateCnh(digits: string): boolean {
  if (!/^\d{11}$/.test(digits)) return false;
  if (/^(\d)\1{10}$/.test(digits)) return false;

  // DV1
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

  // DV2
  sum = 0;
  for (let i = 0, j = 1; i < 9; i++, j++) {
    sum += parseInt(digits[i], 10) * j;
  }
  let x = sum % 11;
  let dv2 = x >= 10 ? 0 : x - dsv;
  if (dv2 < 0) dv2 += 11;
  return dv2 === parseInt(digits[10], 10);
}

/**
 * Título de Eleitor check-digit validation.
 *
 * Algoritmo TSE:
 *   - 12 dígitos: 8 base + 2 estado (UF) + 2 DV.
 *   - DV1: pesos [2..9] sobre primeiros 8 dígitos. mod = sum % 11.
 *          Se mod == 10, dv1 = 0; senão dv1 = mod.
 *          Casos especiais: SP/MG (UF=01/02) — se mod == 0 e UF nesses estados, dv1 = 1.
 *   - DV2: pesos [7..9] sobre dígitos 9,10 (UF) + dv1. mod = sum % 11.
 *          Mesmo tratamento SP/MG.
 *
 * @param digits 12 dígitos puros
 */
export function validateTituloEleitor(digits: string): boolean {
  if (!/^\d{12}$/.test(digits)) return false;
  if (/^(\d)\1{11}$/.test(digits)) return false;

  const uf = digits.substring(8, 10);
  const ufNum = parseInt(uf, 10);
  // UF válida: 01 (SP) a 28 (Exterior). Valores fora desta faixa = inválido.
  if (ufNum < 1 || ufNum > 28) return false;

  const isSpMg = uf === "01" || uf === "02";

  // DV1: pesos 2..9 sobre primeiros 8 dígitos
  let sum = 0;
  for (let i = 0; i < 8; i++) {
    sum += parseInt(digits[i], 10) * (i + 2);
  }
  let mod = sum % 11;
  let dv1: number;
  if (mod === 10) dv1 = 0;
  else if (mod === 0 && isSpMg) dv1 = 1;
  else dv1 = mod;
  if (dv1 !== parseInt(digits[10], 10)) return false;

  // DV2: pesos 7,8,9 sobre dígitos 8,9 (UF) e DV1
  sum =
    parseInt(digits[8], 10) * 7 +
    parseInt(digits[9], 10) * 8 +
    dv1 * 9;
  mod = sum % 11;
  let dv2: number;
  if (mod === 10) dv2 = 0;
  else if (mod === 0 && isSpMg) dv2 = 1;
  else dv2 = mod;
  return dv2 === parseInt(digits[11], 10);
}

/**
 * Lookup map por kind — útil pra detector.
 */
export const BR_PATTERN_BY_KIND: Map<BrPatternKind, BrPatternDef> = new Map(
  BR_PATTERNS.map((p) => [p.kind, p]),
);
