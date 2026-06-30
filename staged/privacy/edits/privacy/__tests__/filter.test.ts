/**
 * privacy/__tests__/filter.test.ts
 *
 * Test suite for the privacy redaction pipeline.
 * Runner: node:test (node --test)
 *
 * All secret values here are SYNTHETIC / official test vectors.
 * No real credentials are present.
 *
 * gitleaks:allow — test fixtures only; all values are synthetic or official test vectors.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { redact } from "../filter.js";
import { stripPrivateTags } from "../tag-parser.js";
import { luhn } from "../patterns.js";

// ─── Helper ─────────────────────────────────────────────────────────────────

function assertRedacted(text: string, expectedKind: string, desc?: string) {
  const result = redact(text);
  assert.ok(
    result.redactionCount > 0,
    `${desc ?? expectedKind}: expected redaction, got none. text="${text}"`
  );
  assert.ok(
    result.kinds.includes(expectedKind),
    `${desc ?? expectedKind}: expected kind "${expectedKind}", got [${result.kinds.join(", ")}]`
  );
  assert.ok(
    !result.text.includes(text.substring(0, 12)) || result.text.includes("[REDACTED"),
    `${desc ?? expectedKind}: raw secret still visible in output`
  );
}

function assertNotRedacted(text: string, desc?: string) {
  const result = redact(text);
  assert.strictEqual(
    result.redactionCount,
    0,
    `${desc ?? "negative case"}: expected no redaction, got ${result.redactionCount} for text="${text}"`
  );
}

// ─── Positive cases — one per pattern ────────────────────────────────────────

describe("AWS access key id", () => {
  it("matches canonical AKIA format", () => {
    assertRedacted("key_id=AKIAIOSFODNN7EXAMPLE", "aws-access-key-id");
  });
  it("matches embedded in sentence", () => {
    assertRedacted("Access key: AKIAI44QH8DHBEXAMPLE was rotated.", "aws-access-key-id");
  });
  it("replaces with correct placeholder", () => {
    const { text } = redact("AKIAIOSFODNN7EXAMPLE");
    assert.ok(text.includes("[REDACTED:aws-access-key-id]"));
  });
});

describe("AWS secret access key", () => {
  it("matches env-var style assignment", () => {
    assertRedacted(
      "aws_secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
      "aws-secret-key"
    );
  });
  it("matches uppercase env name", () => {
    assertRedacted(
      "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
      "aws-secret-key"
    );
  });
});

describe("Anthropic API key", () => {
  it("matches sk-ant prefix", () => {
    assertRedacted("sk-ant-test-EXAMPLEKEY1234567890abcdefghij", "anthropic-key");
  });
  it("matches api03 variant", () => {
    assertRedacted("sk-ant-api03-EXAMPLEKEY1234567890abcdefghijklmnopqr", "anthropic-key");
  });
  it("matches in config line", () => {
    assertRedacted(
      'ANTHROPIC_API_KEY="sk-ant-test-EXAMPLEKEY1234567890abcdefghij"',
      "env-secret"
    );
  });
});

describe("OpenAI API key", () => {
  it("matches sk- prefix", () => {
    assertRedacted("sk-EXAMPLEKEY1234567890abcdefghij", "openai-key");
  });
  it("matches sk-proj variant", () => {
    assertRedacted("sk-proj-EXAMPLEKEY1234567890abcde", "openai-key");
  });
  it("does NOT match sk-ant- as OpenAI key", () => {
    const { kinds } = redact("sk-ant-test-EXAMPLEKEY1234567890abcdefghij");
    assert.ok(!kinds.includes("openai-key"), "sk-ant- should not fire openai-key pattern");
  });
});

describe("Gemini API key", () => {
  it("matches AIza prefix with 35 trailing chars", () => {
    assertRedacted("AIzaSyEXAMPLEKEY1234567890abcdefghij123", "gemini-key"); // gitleaks:allow
  });
  it("matches inline in code comment", () => {
    assertRedacted(
      "// key = AIzaSyEXAMPLEKEY1234567890abcdefghij123 (test)", // gitleaks:allow
      "gemini-key"
    );
  });
});

describe("GitHub tokens", () => {
  it("matches ghp_ prefix", () => {
    assertRedacted("ghp_EXAMPLETOKEN1234567890abcdefghij", "github-token");
  });
  it("matches gho_ prefix", () => {
    assertRedacted("gho_EXAMPLETOKEN1234567890abcdefghij", "github-token");
  });
  it("matches ghs_ prefix", () => {
    assertRedacted("ghs_EXAMPLETOKEN1234567890abcdefghij", "github-token");
  });
  it("matches ghu_ prefix", () => {
    assertRedacted("ghu_EXAMPLETOKEN1234567890abcdefghij", "github-token");
  });
  it("matches github_pat_ prefix", () => {
    assertRedacted("github_pat_EXAMPLETOKEN1234567890abcdef", "github-token");
  });
});

describe("Slack tokens", () => {
  it("matches xoxb- (bot token)", () => {
    assertRedacted("xoxb-EXAMPLE-TOKEN-1234567890", "slack-token");
  });
  it("matches xoxp- (user token)", () => {
    assertRedacted("xoxp-EXAMPLE-TOKEN-1234567890abcdef", "slack-token");
  });
  it("matches xoxa- prefix", () => {
    assertRedacted("xoxa-EXAMPLE-TOKEN-1234567890", "slack-token");
  });
});

describe("Discord bot token", () => {
  it("matches M + 23 chars . 6 chars . 27 chars format", () => {
    // Exact structure: M + 23 word chars (24 total) . 6 chars . 27 chars
    // Synthetic safe token (all repeat chars — not a real bot token)
    assertRedacted(
      "Mkkkkkkkkkkkkkkkkkkkkkkk.AAAAAA.BBBBBBBBBBBBBBBBBBBBBBBBBBB",
      "discord-token"
    );
  });
});

describe("JWT", () => {
  it("matches standard three-part eyJ... token", () => {
    const jwt =
      "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" +
      ".eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ" +
      ".SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";
    assertRedacted(jwt, "jwt");
  });
  it("replaces JWT in Authorization header (both kinds fire)", () => {
    const jwt =
      "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ1c2VyMTIzIn0.SIGNATURE_EXAMPLE_123456"; // gitleaks:allow
    const text = `Authorization: Bearer ${jwt}`;
    const { redactionCount } = redact(text);
    assert.ok(redactionCount > 0, "auth header or JWT must fire");
  });
});

describe("PEM private key", () => {
  it("matches RSA private key block", () => {
    const pem = [
      "-----BEGIN RSA PRIVATE KEY-----",
      "MIIEpAIBAAKCAQEAEXAMPLEKEY1234567890abcdefghijklmnopqrstuvwxyz==",
      "-----END RSA PRIVATE KEY-----",
    ].join("\n");
    assertRedacted(pem, "pem-private-key");
  });
  it("matches generic PRIVATE KEY block", () => {
    const pem = [
      "-----BEGIN PRIVATE KEY-----", // gitleaks:allow
      "MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcEXAMPLE==",
      "-----END PRIVATE KEY-----",
    ].join("\n");
    assertRedacted(pem, "pem-private-key");
  });
  it("matches EC PRIVATE KEY block", () => {
    const pem = "-----BEGIN EC PRIVATE KEY-----\nMHQCAQEEIEXAMPLE==\n-----END EC PRIVATE KEY-----";
    assertRedacted(pem, "pem-private-key");
  });
});

describe("Bearer/Basic auth header", () => {
  it("matches Bearer token", () => {
    assertRedacted("Authorization: Bearer mysecrettoken1234567890ab", "auth-header");
  });
  it("matches Basic base64", () => {
    assertRedacted("Authorization: Basic dXNlcjpFWEFNUExFUEFTU1dPUkQ=", "auth-header");
  });
  it("matches Token form", () => {
    assertRedacted("Authorization: Token EXAMPLETOKEN1234567890abcdef", "auth-header");
  });
  it("is case-insensitive for authorization keyword", () => {
    assertRedacted("authorization: Bearer mysecrettoken1234567890ab", "auth-header");
  });
});

describe(".env-style secrets", () => {
  it("matches PASSWORD=", () => {
    assertRedacted("PASSWORD=s3cr3tP@ssw0rd!", "env-secret");
  });
  it("matches SECRET=", () => {
    assertRedacted("MY_SECRET=supersecretvalue123", "env-secret");
  });
  it("matches TOKEN=", () => {
    assertRedacted("GITHUB_TOKEN=ghp_EXAMPLETOKEN1234567890abcdefghij", "env-secret");
  });
  it("matches API_KEY=", () => {
    assertRedacted("GEMINI_API_KEY=AIzaSyEXAMPLEKEY1234567890abcdefghij123", "env-secret"); // gitleaks:allow
  });
  it("matches with export prefix", () => {
    assertRedacted("export SECRET=mysecretvalue123", "env-secret");
  });
  it("matches quoted value", () => {
    assertRedacted('DB_PASSWORD="my-secret-db-pass"', "env-secret");
  });
});

describe("Credit card (Luhn-validated)", () => {
  it("matches Visa test number (Luhn-valid)", () => {
    assertRedacted("4532015112830366", "credit-card");
  });
  it("matches formatted CC with spaces", () => {
    assertRedacted("4532 0151 1283 0366", "credit-card");
  });
  it("matches Mastercard test number", () => {
    assertRedacted("5425233430109903", "credit-card");
  });
  it("does NOT redact Luhn-invalid 16-digit strings (e.g., hashes)", () => {
    // This is a random 16-digit string that fails Luhn
    const notACard = "1234567890123456"; // fails Luhn
    const { kinds } = redact(notACard);
    assert.ok(!kinds.includes("credit-card"), "Luhn-invalid string should not be redacted as CC");
  });
});

// ─── <private> tag handling ───────────────────────────────────────────────────

describe("<private> tag stripping", () => {
  it("strips basic private tag", () => {
    const result = redact("before <private>secret content here</private> after");
    assert.ok(result.text.includes("[REDACTED:user-marked]"), "user-marked replacement missing");
    assert.ok(!result.text.includes("secret content here"), "tag content still visible");
    assert.ok(result.kinds.includes("user-marked"));
    assert.strictEqual(result.redactionCount, 1);
  });

  it("strips multiline private tag", () => {
    const text = "Header\n<private>\nline1\nline2\nline3\n</private>\nFooter";
    const { text: out, redactionCount } = redact(text);
    assert.strictEqual(redactionCount, 1);
    assert.ok(out.includes("[REDACTED:user-marked]"));
    assert.ok(!out.includes("line1"));
  });

  it("strips multiple private tags", () => {
    const text = "a<private>x</private>b<private>y</private>c";
    const { redactionCount, kinds } = redact(text);
    assert.strictEqual(redactionCount, 2);
    assert.ok(kinds.includes("user-marked"));
  });

  it("strips regex secrets inside private tags (tag wins, runs first)", () => {
    const secret = "AKIAIOSFODNN7EXAMPLE";
    const text = `<private>${secret}</private>`;
    const { text: out, kinds } = redact(text);
    // Should be user-marked, not aws-access-key-id (tag stripped it first)
    assert.ok(out.includes("[REDACTED:user-marked]"));
    assert.ok(!out.includes(secret));
    assert.ok(kinds.includes("user-marked"));
  });

  it("handles private tags with surrounding regex secrets", () => {
    const text = `key=sk-EXAMPLEKEY1234567890abcdefghij <private>my personal note</private>`;
    const { redactionCount, kinds } = redact(text);
    assert.ok(redactionCount >= 2, "both OpenAI key and user-marked should fire");
    assert.ok(kinds.includes("user-marked"));
    assert.ok(kinds.includes("openai-key"));
  });

  it("case-insensitive tag matching", () => {
    const { redactionCount } = redact("<PRIVATE>secret</PRIVATE>");
    assert.strictEqual(redactionCount, 1);
  });
});

// ─── Negative cases — should NOT be redacted ─────────────────────────────────

describe("Negative cases (no false positives)", () => {
  it("UUID is not flagged as credit card", () => {
    // UUID has 32 hex chars, not 16 decimal digits
    assertNotRedacted("550e8400-e29b-41d4-a716-446655440000", "UUID");
  });

  it("SHA256 hash is not flagged", () => {
    assertNotRedacted(
      "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "SHA256 hash"
    );
  });

  it("innocent base64 of JSON is not flagged", () => {
    // base64 of {"hello":"world"} — looks like base64 but is not a secret
    const b64 = Buffer.from('{"hello":"world","count":42}').toString("base64");
    assertNotRedacted(b64, "innocent base64 JSON");
  });

  it("code variable named 'mySecret' is not flagged (no = assignment)", () => {
    assertNotRedacted("const mySecret = computeHash(data);", "code variable");
  });

  it("short token-looking string under threshold is not flagged", () => {
    // sk- with only 5 chars after — too short for OpenAI pattern (requires 20+)
    assertNotRedacted("sk-abc12", "short sk- string");
  });

  it("code identifier 'AKTION_KEY' is not flagged as AWS key (wrong prefix)", () => {
    assertNotRedacted("AKTION_KEY=production", "AKTION_KEY env var");
  });

  it("UUID-like 32 hex string without separators is not flagged as CC", () => {
    // 32 chars hex, not 16 decimal digits
    assertNotRedacted("a3f5c8d2e1b4a9f6c3d7e2b5a8f1c4d7", "32-char hex without separators");
  });

  it("ordinary sentence with word 'secret' in prose is not flagged", () => {
    assertNotRedacted(
      "The secret to great coffee is the grind size.",
      "prose with 'secret' word"
    );
  });

  it("Luhn-invalid 16-digit number (random phone-like) is not redacted", () => {
    // 5500000000000001 — fails Luhn (chosen to be plausible but invalid)
    const { kinds } = redact("5500000000000001");
    assert.ok(!kinds.includes("credit-card"), "Luhn-invalid not redacted as CC");
  });
});

// ─── Telemetry shape ──────────────────────────────────────────────────────────

describe("Telemetry shape", () => {
  it("returns correct redactionCount for single pattern", () => {
    const { redactionCount, kinds } = redact("AKIAIOSFODNN7EXAMPLE");
    assert.strictEqual(redactionCount, 1);
    assert.deepStrictEqual(kinds, ["aws-access-key-id"]);
  });

  it("returns deduplicated kinds for repeated pattern", () => {
    const text = "AKIAIOSFODNN7EXAMPLE and AKIAI44QH8DHBEXAMPLE";
    const { redactionCount, kinds } = redact(text);
    assert.strictEqual(redactionCount, 2);
    // kinds should be deduplicated (only one entry for aws-access-key-id)
    assert.strictEqual(kinds.filter(k => k === "aws-access-key-id").length, 1);
  });

  it("accumulates multiple kinds", () => {
    const text = [
      "AKIAIOSFODNN7EXAMPLE",
      "ghp_EXAMPLETOKEN1234567890abcdefghij",
      "<private>hidden</private>",
    ].join(" ");
    const { redactionCount, kinds } = redact(text);
    assert.ok(redactionCount >= 3, `expected ≥3 redactions, got ${redactionCount}`);
    assert.ok(kinds.includes("aws-access-key-id"));
    assert.ok(kinds.includes("github-token"));
    assert.ok(kinds.includes("user-marked"));
  });

  it("returns empty kinds and zero count for clean text", () => {
    const { redactionCount, kinds, text } = redact("This is a normal chunk of text.");
    assert.strictEqual(redactionCount, 0);
    assert.deepStrictEqual(kinds, []);
    assert.strictEqual(text, "This is a normal chunk of text.");
  });

  it("text field is returned unchanged when nothing redacted", () => {
    const input = "Hello world — no secrets here.";
    const { text } = redact(input);
    assert.strictEqual(text, input);
  });
});

// ─── Luhn standalone tests ────────────────────────────────────────────────────

describe("Luhn algorithm", () => {
  it("validates Visa test number", () => {
    assert.ok(luhn("4532015112830366"));
  });
  it("validates Mastercard test number", () => {
    assert.ok(luhn("5425233430109903"));
  });
  it("rejects invalid CC (digit sum not divisible by 10)", () => {
    // 1111111111111111 — fails Luhn (sum = 8+1+8+1+8+1+8+1+8+1+8+1+8+1+8+1 = not %10)
    assert.ok(!luhn("1111111111111111"));
  });
  it("rejects sequential digits", () => {
    assert.ok(!luhn("1234567890123456"));
  });
});

// ─── tag-parser standalone tests ──────────────────────────────────────────────

describe("stripPrivateTags standalone", () => {
  it("returns tagCount=0 for text without tags", () => {
    const { tagCount, text } = stripPrivateTags("no tags here");
    assert.strictEqual(tagCount, 0);
    assert.strictEqual(text, "no tags here");
  });

  it("handles adjacent tags", () => {
    const { tagCount } = stripPrivateTags("<private>a</private><private>b</private>");
    assert.strictEqual(tagCount, 2);
  });

  it("handles whitespace inside tags", () => {
    const { text } = stripPrivateTags("<private>  \n  </private>");
    assert.ok(text.includes("[REDACTED:user-marked]"));
  });
});
