/**
 * privacy/patterns.ts — Regex patterns for secret/credential redaction.
 *
 * Each pattern covers a distinct secret type. The order matters:
 * - PEM blocks first (multiline, greedy — must match before base64 checks)
 * - Specific prefixed tokens before generic base64 matchers
 * - Credit card last (requires Luhn validation, most expensive)
 *
 * Replacement format: `[REDACTED:<name>]`
 *
 * NOTE: example values below are SYNTHETIC TEST FIXTURES, not real secrets.
 * gitleaks:allow — this file is the pattern library, not a credential store.
 */

export interface RedactionPattern {
  /** Short name used in telemetry kinds[] and replacement string */
  name: string;
  /** Regex — must have no capturing groups that interfere with replace() */
  regex: RegExp;
  /** Replacement string. Use `[REDACTED:<name>]` convention. */
  replacement: string;
  /** Safe synthetic examples (for tests — NOT real secrets) */
  examples: string[];
}

/**
 * Luhn algorithm check for credit card numbers.
 * Returns true if number passes (likely a real CC, not a random 16-digit string).
 */
export function luhn(digits: string): boolean {
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

export const REDACTION_PATTERNS: RedactionPattern[] = [
  // ── PEM private key block (multiline) ──────────────────────────────────────
  {
    name: "pem-private-key",
    regex: /-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----/g,
    replacement: "[REDACTED:pem-private-key]",
    examples: [
      "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----", // gitleaks:allow
      "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqh...\n-----END PRIVATE KEY-----", // gitleaks:allow
      "-----BEGIN EC PRIVATE KEY-----\nMHQCAQEEI...\n-----END EC PRIVATE KEY-----",
    ],
  },

  // ── AWS access key id ──────────────────────────────────────────────────────
  {
    name: "aws-access-key-id",
    regex: /\bAKIA[0-9A-Z]{16}\b/g,
    replacement: "[REDACTED:aws-access-key-id]",
    examples: ["AKIAIOSFODNN7EXAMPLE", "AKIAI44QH8DHBEXAMPLE"],
  },

  // ── AWS secret access key (value after env var name) ─────────────────────
  {
    name: "aws-secret-key",
    regex: /(?:aws_secret_access_key|AWS_SECRET_ACCESS_KEY)\s*[=:]\s*["']?([A-Za-z0-9/+]{40})["']?/gi,
    replacement: "[REDACTED:aws-secret-key]",
    examples: [
      "aws_secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
      "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    ],
  },

  // ── Anthropic API key ──────────────────────────────────────────────────────
  {
    name: "anthropic-key",
    regex: /\bsk-ant-(?:api\d+-)?[a-zA-Z0-9_-]{20,}\b/g,
    replacement: "[REDACTED:anthropic-key]",
    examples: [
      "sk-ant-test-EXAMPLEKEY1234567890abcdefghij",
      "sk-ant-api03-EXAMPLEKEY1234567890abcdefghijklmnopqr",
    ],
  },

  // ── OpenAI API key ────────────────────────────────────────────────────────
  {
    name: "openai-key",
    regex: /\bsk-(?!ant-)[a-zA-Z0-9_-]{20,}\b/g,
    replacement: "[REDACTED:openai-key]",
    examples: [
      "sk-EXAMPLEKEY1234567890abcdefghij",
      "sk-proj-EXAMPLEKEY1234567890abcde",
    ],
  },

  // ── Gemini / Google API key ───────────────────────────────────────────────
  {
    name: "gemini-key",
    regex: /\bAIza[0-9A-Za-z_-]{35}\b/g,
    replacement: "[REDACTED:gemini-key]",
    examples: [
      "AIzaSyEXAMPLEKEY1234567890abcdefghij123", // gitleaks:allow
    ],
  },

  // ── GitHub tokens ──────────────────────────────────────────────────────────
  {
    name: "github-token",
    regex: /\b(?:ghp_|gho_|ghs_|ghu_|github_pat_)[a-zA-Z0-9_]{20,}\b/g,
    replacement: "[REDACTED:github-token]",
    examples: [
      "ghp_EXAMPLETOKEN1234567890abcdefghij",
      "gho_EXAMPLETOKEN1234567890abcdefghij",
      "ghs_EXAMPLETOKEN1234567890abcdefghij",
      "ghu_EXAMPLETOKEN1234567890abcdefghij",
      "github_pat_EXAMPLETOKEN1234567890abcdef",
    ],
  },

  // ── Slack tokens ─────────────────────────────────────────────────────────
  {
    name: "slack-token",
    regex: /\bxox[bpoa]-[0-9A-Za-z-]{10,}\b/g,
    replacement: "[REDACTED:slack-token]",
    examples: [
      "xoxb-EXAMPLE-TOKEN-1234567890",
      "xoxp-EXAMPLE-TOKEN-1234567890abcdef",
      "xoxa-EXAMPLE-TOKEN-1234567890",
    ],
  },

  // ── Discord bot tokens ────────────────────────────────────────────────────
  {
    name: "discord-token",
    regex: /\bM[\w-]{23}\.[\w-]{6}\.[\w-]{27}\b/g,
    replacement: "[REDACTED:discord-token]",
    examples: [
      // M + 23 word chars (=24 total) + '.' + 6 chars + '.' + 27 chars
      "Mkkkkkkkkkkkkkkkkkkkkkkk.AAAAAA.BBBBBBBBBBBBBBBBBBBBBBBBBBB",
    ],
  },

  // ── JWT tokens ────────────────────────────────────────────────────────────
  // eyJ header (base64url JSON) followed by claims + signature
  {
    name: "jwt",
    regex: /\beyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b/g,
    replacement: "[REDACTED:jwt]",
    examples: [
      "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c", // gitleaks:allow
    ],
  },

  // ── Bearer / Basic auth header values ────────────────────────────────────
  {
    name: "auth-header",
    regex: /Authorization\s*:\s*(?:Bearer|Basic|Token)\s+[A-Za-z0-9_\-+/=.]{8,}/gi,
    replacement: "Authorization: [REDACTED:auth-header]",
    examples: [
      "Authorization: Bearer eyJhbGciOiJSUzI1NiJ9.EXAMPLE",
      "Authorization: Basic dXNlcjpFWEFNUExFUEFTU1dPUkQ=",
      "Authorization: Token EXAMPLETOKEN1234567890abcdef",
    ],
  },

  // ── .env-style assignments ─────────────────────────────────────────────────
  // Matches: PASSWORD=..., SECRET=..., TOKEN=..., API_KEY=..., PRIVATE_KEY=..., ACCESS_KEY=...
  // Stops at newline. Handles quoted and unquoted values.
  {
    name: "env-secret",
    regex: /^(?:export\s+)?(?:[A-Z0-9_]*(?:PASSWORD|SECRET|TOKEN|API_KEY|PRIVATE_KEY|ACCESS_KEY)[A-Z0-9_]*)\s*=\s*["']?(?:[^\s"'\r\n]{4,})["']?/gm,
    replacement: "[REDACTED:env-secret]",
    examples: [
      "PASSWORD=s3cr3tP@ssw0rd!", // gitleaks:allow
      "API_KEY=AIzaSyEXAMPLEKEY1234567890abcdefghij123", // gitleaks:allow
      "ANTHROPIC_API_KEY=sk-ant-test-EXAMPLEKEY", // gitleaks:allow
      "export SECRET=mysecretvalue123", // gitleaks:allow
      "DB_PASSWORD=\"my-secret-db-pass\"", // gitleaks:allow
      "PRIVATE_KEY='-----BEGIN RSA...'", // gitleaks:allow
    ],
  },

  // ── Credit card (16-digit, Luhn-validated) ────────────────────────────────
  // NOTE: Luhn check is applied in filter.ts after regex match to reduce false positives.
  // Matches Visa/MC/Amex-style numbers with optional spaces/hyphens between groups.
  // The regex itself just finds candidates; filter.ts calls luhn() to confirm.
  {
    name: "credit-card",
    // 4 groups of 4 digits (with optional separators), or plain 16 digits
    regex: /\b(?:\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}|\d{16})\b/g,
    replacement: "[REDACTED:credit-card]",
    examples: [
      "4532015112830366",       // Visa (Luhn-valid test number)
      "4532 0151 1283 0366",    // formatted
      "5425233430109903",       // Mastercard test
      "371449635398431",        // Amex — won't match (15 digits, pattern excluded)
    ],
  },
];
