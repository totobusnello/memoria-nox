import { test } from "node:test";
import assert from "node:assert/strict";
import {
  extractFrontmatterBlock,
  parseFrontmatterFields,
  extractFrontmatterRelations,
  extractFrontmatterRelationsFromObject,
} from "../frontmatter.js";

test("frontmatter: extracts block from --- delimited doc", () => {
  const doc = "---\nagent: atlas\n---\nbody";
  assert.equal(extractFrontmatterBlock(doc), "agent: atlas");
});

test("frontmatter: returns null when no block", () => {
  assert.equal(extractFrontmatterBlock("just prose"), null);
});

test("frontmatter: parses scalar fields", () => {
  const fields = parseFrontmatterFields("agent: atlas\nsupersedes: old_one");
  assert.equal(fields.length, 2);
  assert.equal(fields[0]?.scalar, "atlas");
});

test("frontmatter: parses quoted scalar", () => {
  const fields = parseFrontmatterFields('caused_by: "incident/i1"');
  assert.equal(fields[0]?.scalar, "incident/i1");
});

test("frontmatter: parses flow array", () => {
  const fields = parseFrontmatterFields("references: [a, b, c]");
  assert.deepEqual(fields[0]?.array, ["a", "b", "c"]);
});

test("frontmatter: parses block array", () => {
  const fields = parseFrontmatterFields(
    "references:\n  - feedback/a\n  - feedback/b",
  );
  assert.deepEqual(fields[0]?.array, ["feedback/a", "feedback/b"]);
});

test("relations: agent → is_agent_of", () => {
  const r = extractFrontmatterRelations("---\nagent: atlas\n---");
  assert.equal(r.length, 1);
  assert.equal(r[0]?.relationType, "is_agent_of");
  assert.equal(r[0]?.target, "atlas");
});

test("relations: references array → multiple references rows", () => {
  const r = extractFrontmatterRelations(
    "---\nreferences:\n  - feedback/a\n  - feedback/b\n---",
  );
  assert.equal(r.length, 2);
  assert.equal(r[0]?.relationType, "references");
  assert.equal(r[1]?.target, "feedback/b");
});

test("relations: supersedes scalar", () => {
  const r = extractFrontmatterRelations("---\nsupersedes: decision/old\n---");
  assert.equal(r[0]?.relationType, "supersedes");
});

test("relations: caused_by scalar", () => {
  const r = extractFrontmatterRelations("---\ncaused_by: incident/i7\n---");
  assert.equal(r[0]?.relationType, "caused_by");
});

test("relations: resolves scalar", () => {
  const r = extractFrontmatterRelations("---\nresolves: pending/p3\n---");
  assert.equal(r[0]?.relationType, "resolves");
});

test("relations: decided_by scalar", () => {
  const r = extractFrontmatterRelations("---\ndecided_by: person/toto\n---");
  assert.equal(r[0]?.relationType, "decided_by");
});

test("relations: ignores unknown fields", () => {
  const r = extractFrontmatterRelations(
    "---\ntitle: hello\ncreated: 2026-01-01\n---",
  );
  assert.equal(r.length, 0);
});

test("relations: skips empty scalar", () => {
  const r = extractFrontmatterRelations("---\nagent:\n---");
  assert.equal(r.length, 0);
});

test("relations: from already-parsed object", () => {
  const r = extractFrontmatterRelationsFromObject({
    agent: "atlas",
    references: ["a", "b"],
    title: "ignored",
  });
  assert.equal(r.length, 3);
});

test("relations: mixed scalar + array + unknown", () => {
  const r = extractFrontmatterRelations(
    "---\nagent: atlas\nreferences: [feedback/a, feedback/b]\nother: skip\n---",
  );
  assert.equal(r.length, 3);
});
