/**
 * patterns.js — A1 US secrets + A1.1 BR PII pattern catalog (vanilla JS).
 *
 * Ported from:
 *   - staged/privacy/edits/privacy/patterns.ts (13 US secret patterns)
 *   - staged/A1.1/edits/src/lib/privacy-br/patterns.ts (12 BR PII patterns)
 *
 * Key conventions:
 *   - Unicode-safe boundaries via lookbehind/lookahead (NUNCA \b — falha em
 *     ç/ã/ê). Ref: feedback_js_regex_unicode_word_boundary_fails.
 *   - Cada call a `getRegex()` retorna instância fresh com lastIndex=0 pra
 *     uso em matchAll/replace sem state leak.
 *   - Ordem importa pra resolução de overlap: mais específico primeiro
 *     (CNPJ antes de CPF, telefone BR antes de CEP, etc.).
 *
 * Replacement format:
 *   - US/secrets : `[REDACTED:<name>]`
 *   - BR/PII     : `[REDACTED:<kind>]`
 *
 * Tudo confluente com servidor (A1 hooks pipeline) — defense-in-depth.
 *
 * NOTE: All `examples` arrays are SYNTHETIC TEST FIXTURES, not real secrets.
 * gitleaks:allow — this file is the pattern library, not a credential store.
 */

import {
  validateCpf,
  validateCnpj,
  validateCep,
  validateCnh,
  validateTituloEleitor,
  luhn,
  digitsOnly,
} from "./validators.js";

// ─── Boundary helpers (Unicode-safe) ─────────────────────────────────────────
// Ver patterns.ts A1.1: \b falha em pt-BR; usamos lookbehind/lookahead com
// whitespace + pontuação + start/end. Inclui caracteres comuns em context:
//   =, ", ', [, <, > (cobre `cpf=...`, `"cpf": "..."`, `<cpf>...</cpf>`).
const SOL = "(?<=^|[\\s(,;:./=\"'\\[<>])";
const EOL = "(?=[\\s),;:.!?/=\"'\\]>-]|$)";

// ─── Confidence buckets (informativo — A1 redact unconditional) ──────────────
export const CONFIDENCE = Object.freeze({
  HIGH: 0.95,
  MEDIUM_HIGH: 0.85,
  MEDIUM: 0.75,
  MEDIUM_LOW: 0.65,
  LOW: 0.5,
  VERY_LOW: 0.3,
});

/**
 * Pattern entry. Each:
 *   - kind            : tag canônica (usada em replacement)
 *   - getRegex()      : factory fresh; sempre /g
 *   - validate?       : função opcional sobre `normalized`. Se retornar
 *                       false, o match é DESCARTADO (não redatado).
 *                       Padrões sem validate sempre redatam.
 *   - normalize       : produz forma canônica a partir do raw match
 *   - confidence      : informativo (não bloqueia redação no MVP)
 *   - examples        : amostras pra testes (NUNCA secrets reais)
 *
 * Replacement string sempre `[REDACTED:${kind}]`.
 */

// ════════════════════════════════════════════════════════════════════════════
//   A1 — US secrets (13 padrões)
// ════════════════════════════════════════════════════════════════════════════

const US_PATTERNS = [
  // ── PEM private key block (multiline) ──────────────────────────────────────
  {
    kind: "pem-private-key",
    getRegex: () =>
      /-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----/g,
    confidence: CONFIDENCE.HIGH,
    normalize: (s) => s,
    examples: [
      // gitleaks:allow
      "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----",
      // gitleaks:allow
      "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADAN...\n-----END PRIVATE KEY-----",
    ],
  },

  // ── AWS access key id ──────────────────────────────────────────────────────
  {
    kind: "aws-access-key-id",
    getRegex: () => /\bAKIA[0-9A-Z]{16}\b/g,
    confidence: CONFIDENCE.HIGH,
    normalize: (s) => s,
    examples: ["AKIAIOSFODNN7EXAMPLE", "AKIAI44QH8DHBEXAMPLE"],
  },

  // ── AWS secret access key (env-style) ─────────────────────────────────────
  {
    kind: "aws-secret-key",
    getRegex: () =>
      /(?:aws_secret_access_key|AWS_SECRET_ACCESS_KEY)\s*[=:]\s*["']?([A-Za-z0-9/+]{40})["']?/gi,
    confidence: CONFIDENCE.HIGH,
    normalize: (s) => s,
    examples: [
      // gitleaks:allow
      "aws_secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
      // gitleaks:allow
      "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    ],
  },

  // ── Anthropic API key ─────────────────────────────────────────────────────
  {
    kind: "anthropic-key",
    getRegex: () => /\bsk-ant-(?:api\d+-)?[a-zA-Z0-9_-]{20,}\b/g,
    confidence: CONFIDENCE.HIGH,
    normalize: (s) => s,
    // gitleaks:allow
    examples: ["sk-ant-api03-EXAMPLEKEY1234567890abcdefghijklmnopqr"],
  },

  // ── OpenAI API key (não sk-ant) ───────────────────────────────────────────
  {
    kind: "openai-key",
    getRegex: () => /\bsk-(?!ant-)[a-zA-Z0-9_-]{20,}\b/g,
    confidence: CONFIDENCE.HIGH,
    normalize: (s) => s,
    // gitleaks:allow
    examples: ["sk-EXAMPLEKEY1234567890abcdefghij"],
  },

  // ── Gemini / Google API key ───────────────────────────────────────────────
  {
    kind: "gemini-key",
    getRegex: () => /\bAIza[0-9A-Za-z_-]{35}\b/g,
    confidence: CONFIDENCE.HIGH,
    normalize: (s) => s,
    // gitleaks:allow
    examples: ["AIzaSyEXAMPLEKEY1234567890abcdefghij123"],
  },

  // ── GitHub tokens ─────────────────────────────────────────────────────────
  {
    kind: "github-token",
    getRegex: () => /\b(?:ghp_|gho_|ghs_|ghu_|github_pat_)[a-zA-Z0-9_]{20,}\b/g,
    confidence: CONFIDENCE.HIGH,
    normalize: (s) => s,
    examples: [
      // gitleaks:allow
      "ghp_EXAMPLETOKEN1234567890abcdefghij",
      // gitleaks:allow
      "github_pat_EXAMPLETOKEN1234567890abcdef",
    ],
  },

  // ── Slack tokens ──────────────────────────────────────────────────────────
  {
    kind: "slack-token",
    getRegex: () => /\bxox[bpoa]-[0-9A-Za-z-]{10,}\b/g,
    confidence: CONFIDENCE.HIGH,
    normalize: (s) => s,
    examples: ["xoxb-EXAMPLE-TOKEN-1234567890"],
  },

  // ── Discord bot tokens ────────────────────────────────────────────────────
  {
    kind: "discord-token",
    getRegex: () => /\bM[\w-]{23}\.[\w-]{6}\.[\w-]{27}\b/g,
    confidence: CONFIDENCE.HIGH,
    normalize: (s) => s,
    examples: [
      "Mkkkkkkkkkkkkkkkkkkkkkkk.AAAAAA.BBBBBBBBBBBBBBBBBBBBBBBBBBB",
    ],
  },

  // ── JWT tokens ────────────────────────────────────────────────────────────
  {
    kind: "jwt",
    getRegex: () => /\beyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b/g,
    confidence: CONFIDENCE.HIGH,
    normalize: (s) => s,
    examples: [
      // gitleaks:allow
      "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
    ],
  },

  // ── Bearer / Basic auth header ────────────────────────────────────────────
  {
    kind: "auth-header",
    getRegex: () =>
      /Authorization\s*:\s*(?:Bearer|Basic|Token)\s+[A-Za-z0-9_\-+/=.]{8,}/gi,
    confidence: CONFIDENCE.HIGH,
    normalize: (s) => s,
    examples: ["Authorization: Bearer eyJhbGciOiJSUzI1NiJ9.EXAMPLE"],
  },

  // ── .env-style secret assignments ─────────────────────────────────────────
  {
    kind: "env-secret",
    getRegex: () =>
      /^(?:export\s+)?(?:[A-Z0-9_]*(?:PASSWORD|SECRET|TOKEN|API_KEY|PRIVATE_KEY|ACCESS_KEY)[A-Z0-9_]*)\s*=\s*["']?(?:[^\s"'\r\n]{4,})["']?/gm,
    confidence: CONFIDENCE.HIGH,
    normalize: (s) => s,
    // gitleaks:allow
    examples: ["API_KEY=AIzaSyEXAMPLEKEY1234567890abcdefghij123"],
  },

  // ── Credit card (Luhn-validated) ──────────────────────────────────────────
  {
    kind: "credit-card",
    getRegex: () => /\b(?:\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}|\d{16})\b/g,
    validate: (n) => {
      const d = digitsOnly(n);
      return d.length === 16 && luhn(d);
    },
    confidence: CONFIDENCE.HIGH,
    normalize: digitsOnly,
    examples: ["4532015112830366", "4532 0151 1283 0366"],
  },
];

// ════════════════════════════════════════════════════════════════════════════
//   A1.1 — BR PII (12 padrões)
// ════════════════════════════════════════════════════════════════════════════

const BR_PATTERNS = [
  // ── CNPJ (14 dig — vem ANTES de CPF) ─────────────────────────────────────
  {
    kind: "cnpj",
    getRegex: () =>
      new RegExp(
        `${SOL}(\\d{2}\\.\\d{3}\\.\\d{3}/\\d{4}-\\d{2}|\\d{14})${EOL}`,
        "g",
      ),
    validate: (n) => validateCnpj(digitsOnly(n)),
    confidence: CONFIDENCE.HIGH,
    normalize: digitsOnly,
    examples: ["12.345.678/0001-95", "11444777000161"],
  },

  // ── PIX UUID v4 (vem antes de cartão pra não ser engolido) ────────────────
  {
    kind: "pix_uuid",
    getRegex: () =>
      new RegExp(
        `${SOL}([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12})${EOL}`,
        "g",
      ),
    confidence: CONFIDENCE.MEDIUM_HIGH,
    normalize: (s) => s.toLowerCase(),
    examples: ["550e8400-e29b-41d4-a716-446655440000"],
  },

  // ── Telefone BR (com/sem +55, DDD, 8 ou 9 dígitos) ───────────────────────
  // Vem antes de CPF puro (11 dig) pra resolver overlap em formatos típicos.
  {
    kind: "telefone_br",
    getRegex: () =>
      new RegExp(
        `${SOL}(?:\\+?55[\\s-]?)?(?:\\(?[1-9][0-9]\\)?[\\s-]?)?9?\\d{4}[\\s-]?\\d{4}${EOL}`,
        "g",
      ),
    validate: (raw) => {
      const n = digitsOnly(raw);
      const len = n.length;
      if (len < 8 || len > 13) return false;
      if (len === 13 && !n.startsWith("55")) return false;
      if (len === 12 && !n.startsWith("55")) return false;
      // Móvel com DDD (11): pos 2 = '9'
      if (len === 11 && n[2] !== "9") return false;
      return true;
    },
    confidence: CONFIDENCE.MEDIUM_HIGH,
    normalize: digitsOnly,
    examples: ["+55 11 99999-9999", "(11) 99999-9999", "11 9999-9999"],
  },

  // ── CPF (11 dig formatado ou puro) ───────────────────────────────────────
  {
    kind: "cpf",
    getRegex: () =>
      new RegExp(`${SOL}(\\d{3}\\.\\d{3}\\.\\d{3}-\\d{2}|\\d{11})${EOL}`, "g"),
    validate: (n) => validateCpf(digitsOnly(n)),
    confidence: CONFIDENCE.HIGH,
    normalize: digitsOnly,
    examples: ["123.456.789-09", "12345678909"],
  },

  // ── Cartão de crédito BR (Luhn) ──────────────────────────────────────────
  {
    kind: "cartao_br",
    getRegex: () =>
      new RegExp(
        `${SOL}(\\d{4}[\\s-]?\\d{4}[\\s-]?\\d{4}[\\s-]?\\d{1,7}|\\d{13,19})${EOL}`,
        "g",
      ),
    validate: (raw) => {
      const n = digitsOnly(raw);
      return (
        n.length >= 13 &&
        n.length <= 19 &&
        !/^(\d)\1+$/.test(n) &&
        luhn(n)
      );
    },
    confidence: CONFIDENCE.HIGH,
    normalize: digitsOnly,
    examples: ["4532 0151 1283 0366", "5425233430109903"],
  },

  // ── PIX telefone (+55 obrigatório) ───────────────────────────────────────
  {
    kind: "pix_phone",
    getRegex: () => new RegExp(`${SOL}(\\+55[1-9][0-9]9\\d{8})${EOL}`, "g"),
    validate: (raw) => /^55[1-9][0-9]9\d{8}$/.test(digitsOnly(raw)),
    confidence: CONFIDENCE.HIGH,
    normalize: digitsOnly,
    examples: ["+5511999998888"],
  },

  // ── PIX email ────────────────────────────────────────────────────────────
  // Cobre também emails em qualquer contexto (não só PIX).
  {
    kind: "pix_email",
    getRegex: () =>
      new RegExp(
        `${SOL}([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})${EOL}`,
        "g",
      ),
    confidence: CONFIDENCE.MEDIUM_HIGH,
    normalize: (s) => s.toLowerCase(),
    examples: ["user@example.com", "toto.busnello@gmail.com"],
  },

  // ── CEP (formato hífenado obrigatório, evita FP catastrófico) ────────────
  {
    kind: "cep",
    getRegex: () => new RegExp(`${SOL}(\\d{5}-\\d{3})${EOL}`, "g"),
    validate: (n) => validateCep(digitsOnly(n)),
    confidence: CONFIDENCE.MEDIUM_HIGH,
    normalize: digitsOnly,
    examples: ["01310-100", "04567-890"],
  },

  // ── PIX CPF (CPF puro usado como chave PIX — alias semântico) ────────────
  // Mesmo regex que CPF puro mas catalog entry separada pra detector que
  // quer marcar contexto PIX explicitamente (não acionado automaticamente
  // em v0.1 — o CPF acima já cobre o caso). Mantém parity com A1.1 (12 BR).
  // Em prática, esse padrão raramente dispara porque o CPF anterior consome
  // antes — está aqui pra completude do catálogo.
  {
    kind: "pix_cpf",
    getRegex: () => new RegExp(`${SOL}(\\d{11})${EOL}`, "g"),
    validate: (n) => validateCpf(digitsOnly(n)),
    confidence: CONFIDENCE.HIGH,
    normalize: digitsOnly,
    examples: ["12345678909"],
  },

  // ── Título de Eleitor (12 dig com DV) ────────────────────────────────────
  {
    kind: "titulo_eleitor",
    getRegex: () => new RegExp(`${SOL}(\\d{12})${EOL}`, "g"),
    validate: (n) => validateTituloEleitor(digitsOnly(n)),
    confidence: CONFIDENCE.HIGH,
    normalize: digitsOnly,
    examples: ["123456789012"],
  },

  // ── CNH (11 dig com DV próprio) ──────────────────────────────────────────
  // NOTA: colide com CPF puro (também 11 dig). A regex aqui só matcha em
  // strings que NÃO casam com CPF — o detector aplica em ordem.
  // No MVP, ambos rodam; quem matchar primeiro vence.
  {
    kind: "cnh",
    getRegex: () => new RegExp(`${SOL}(\\d{11})${EOL}`, "g"),
    validate: (n) => validateCnh(digitsOnly(n)),
    confidence: CONFIDENCE.MEDIUM,
    normalize: digitsOnly,
    examples: ["12345678900"],
  },

  // ── RG (formato amplo — confidence baixa) ────────────────────────────────
  {
    kind: "rg",
    getRegex: () =>
      new RegExp(`${SOL}(\\d{1,2}\\.\\d{3}\\.\\d{3}-[\\dxX])${EOL}`, "g"),
    confidence: CONFIDENCE.MEDIUM_LOW,
    normalize: (s) => s.replace(/[.\-]/g, "").toUpperCase(),
    examples: ["12.345.678-9", "1.234.567-X"],
  },
];

// ════════════════════════════════════════════════════════════════════════════
//   Combined catalog — order matters
// ════════════════════════════════════════════════════════════════════════════

/**
 * Ordem de aplicação:
 *  1. US patterns first (mais específicos: tokens, keys, headers).
 *     Reduz risco de credentials viajarem como "telefone" ou "CPF" inválido.
 *  2. BR PII (mais longo → mais curto): CNPJ → PIX UUID → telefone → CPF →
 *     cartão → PIX phone → email → CEP → título → CNH → RG.
 *
 * Cada padrão consome o texto antes do próximo rodar — overlap natural.
 */
export const ALL_PATTERNS = Object.freeze([...US_PATTERNS, ...BR_PATTERNS]);

/**
 * Lookup por kind — utilitário pra testes e debugging.
 */
export const PATTERN_BY_KIND = new Map(ALL_PATTERNS.map((p) => [p.kind, p]));

/**
 * Soma total de padrões — sanity check (esperado: 25 = 13 US + 12 BR).
 */
export const PATTERN_COUNT = ALL_PATTERNS.length;
