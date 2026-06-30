/**
 * Tests for src/observability/privacy-guard.ts (T9 — 6 tests).
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  sanitizeString,
  sanitizeLabels,
  sanitizeLabelValue,
  guardLabels,
} from "../privacy-guard.js";
import { CardinalityGuard, applyDefaultPolicies } from "../cardinality.js";

test("T9.1 sanitizeString strips emails, keys, IPs, CPF, CNPJ", () => {
  const inp =
    "contact alice@example.com from 10.0.0.5 sk-abcdef1234567890XYZAB cpf 123.456.789-09 cnpj 11.222.333/0001-44 cep 01310-100";
  const out = sanitizeString(inp);
  assert.match(out, /<redacted-email>/);
  assert.match(out, /<redacted-ip>/);
  assert.match(out, /<redacted-key>/);
  assert.match(out, /<redacted-cpf>/);
  assert.match(out, /<redacted-cnpj>/);
  assert.match(out, /<redacted-cep>/);
  assert.doesNotMatch(out, /alice@/);
  assert.doesNotMatch(out, /sk-abc/);
});

test("T9.2 sanitizeLabelValue redacts forbidden-name hints", () => {
  assert.equal(sanitizeLabelValue("query", "hello"), "<redacted>");
  assert.equal(sanitizeLabelValue("query_text", "anything"), "<redacted>");
  assert.equal(sanitizeLabelValue("user_id", "42"), "<redacted>");
  assert.equal(sanitizeLabelValue("prompt", "foo"), "<redacted>");
  assert.equal(sanitizeLabelValue("file_path", "/tmp/x"), "<redacted>");
});

test("T9.3 sanitizeLabelValue accepts safe enums", () => {
  assert.equal(sanitizeLabelValue("method", "cli"), "cli");
  assert.equal(sanitizeLabelValue("outcome", "success"), "success");
  assert.equal(sanitizeLabelValue("provider", "gemini"), "gemini");
  assert.equal(sanitizeLabelValue("model", "gemini-2.5-flash-lite"), "gemini-2.5-flash-lite");
});

test("T9.4 sanitizeLabelValue redacts overlong / unsafe values", () => {
  const long = "a".repeat(200);
  assert.equal(sanitizeLabelValue("method", long), "<redacted>");
  assert.equal(sanitizeLabelValue("method", "has spaces"), "<redacted>");
  assert.equal(sanitizeLabelValue("method", "sql; drop table"), "<redacted>");
});

test("T9.5 sanitizeLabels rewrites a full labels object", () => {
  const out = sanitizeLabels({
    method: "api",
    user_id: "1234",
    outcome: "success",
    query: "find me X",
  });
  assert.equal(out.method, "api");
  assert.equal(out.outcome, "success");
  assert.equal(out.user_id, "<redacted>");
  assert.equal(out.query, "<redacted>");
});

test("T9.6 guardLabels composes privacy + cardinality + default policy", () => {
  const card = new CardinalityGuard(() => {});
  applyDefaultPolicies(card);
  const ok = guardLabels(
    "nox_search_requests_total",
    { method: "api", user_id: "leak", outcome: "success" },
    card,
  );
  // user_id stripped by cardinality denylist
  assert.equal(ok.labels?.user_id, undefined);
  assert.equal(ok.labels?.method, "api");
  assert.equal(ok.labels?.outcome, "success");
});
