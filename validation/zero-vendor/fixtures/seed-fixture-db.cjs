#!/usr/bin/env node
/**
 * seed-fixture-db.cjs — Pre-populate the JSON fixture DB with 5 chunks plus
 * a primed embedding cache. Used by embedding-cache-replay and offline-mode
 * checks to exercise cache-hit paths without ever calling Gemini.
 *
 * Usage:
 *   node seed-fixture-db.cjs [/path/to/output.json]
 *
 * Idempotent: overwrites the target file each run.
 */

"use strict";

const fs = require("node:fs");
const path = require("node:path");

const OUT = process.argv[2] || path.join(__dirname, "fixture-db.json");

function synthesize(text) {
  const tokens = text.toLowerCase().split(/\s+/).filter(Boolean);
  const vec = new Array(32).fill(0);
  for (const t of tokens) {
    let h = 0;
    for (let i = 0; i < t.length; i++) h = ((h * 31) + t.charCodeAt(i)) >>> 0;
    vec[h % 32] += 1;
  }
  let norm = 0;
  for (const v of vec) norm += v * v;
  norm = Math.sqrt(norm) || 1;
  return vec.map((v) => v / norm);
}

function hashString(s) {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = ((h * 31) + s.charCodeAt(i)) >>> 0;
  return "h" + h.toString(16);
}

const CHUNKS = [
  {
    id: "chunk-1",
    section: "compiled",
    text: "nox-mem is a hybrid memory system built on standard SQLite with no proprietary runtime dependencies.",
  },
  {
    id: "chunk-2",
    section: "compiled",
    text: "Hybrid search combines FTS5 BM25 with Gemini semantic embeddings fused via RRF.",
  },
  {
    id: "chunk-3",
    section: "frontmatter",
    text: "type: concept slug: zero-vendor-autonomy importance: 0.9 retention_days: null",
  },
  {
    id: "chunk-4",
    section: "timeline",
    text: "2026-05-17 created as offline test fixture for the zero-vendor validation suite.",
  },
  {
    id: "chunk-5",
    section: "compiled",
    text: "No background daemon is required to read the memory database from disk.",
  },
];

// Pre-seed embeddings on every chunk.
for (const c of CHUNKS) c.embedding = synthesize(c.text);

// Pre-seed the query cache for the canonical search queries used by checks.
const PRIMED_QUERIES = [
  "zero vendor sqlite offline",
  "hybrid memory autonomy",
  "no daemon required",
  "test cached embedding",
];

const cache = {};
for (const q of PRIMED_QUERIES) {
  cache[hashString(q)] = synthesize(q);
}

const db = {
  chunks: CHUNKS,
  cache,
  cacheHits: 0,
  version: 1,
  seeded: new Date().toISOString(),
};

fs.writeFileSync(OUT, JSON.stringify(db, null, 2), "utf8");
console.log(
  JSON.stringify({
    seeded: OUT,
    chunks: CHUNKS.length,
    primedQueries: PRIMED_QUERIES.length,
  })
);
