#!/usr/bin/env node
/**
 * mock-nox-mem.cjs — Self-contained mock of the nox-mem CLI.
 *
 * Lets the zero-vendor validation suite exercise the EXPECTED behavior of
 * nox-mem in CI without requiring the actual source tree (which lives on the
 * VPS at /root/.openclaw/workspace/tools/nox-mem/).
 *
 * Behavior is driven entirely by env vars so each check can assert against
 * a deterministic contract:
 *   - NOX_OFFLINE_MODE=1        → never attempt outbound HTTP
 *   - NOX_LLM_PROVIDER=anthropic → require NOX_ANTHROPIC_API_KEY; fail clearly
 *                                  if missing/invalid
 *   - NOX_FIXTURE_DB=/path.json  → JSON-backed chunk + embedding cache
 *   - NOX_NETWORK_REPORT=/path   → append outbound URL attempts to this file
 *   - NOX_FAIL_IF_EMBED=1        → fail loudly if embedding code path runs
 *                                  (used by embedding-cache-replay check)
 *
 * Commands (subset of the real CLI):
 *   stats                      → print health snapshot
 *   search "<query>"           → run BM25-on-JSON + cache-replay logic
 *   ingest-entity <file>       → parse a 3-section entity .md and emit N+2 chunks
 *   answer "<query>"           → calls provider; surfaces provider errors clearly
 *
 * Outputs JSON on stdout. Exit code 0 on success, non-zero on failure.
 * Error messages are structured so checks can grep without false positives.
 */

"use strict";

const fs = require("node:fs");
const path = require("node:path");
const http = require("node:http");
const https = require("node:https");

// ---------------------------------------------------------------------------
// Network attempt logger — every outbound HTTP attempt is recorded.
// When NOX_OFFLINE_MODE=1, we refuse to even build the request.
// ---------------------------------------------------------------------------

function recordOutbound(url) {
  const reportPath = process.env.NOX_NETWORK_REPORT;
  if (!reportPath) return;
  try {
    fs.appendFileSync(reportPath, url + "\n", "utf8");
  } catch {
    /* best-effort logging */
  }
}

function safeHttpRequest(url) {
  // Always record the *intent*. Whether it actually goes out depends on env.
  recordOutbound(url);

  if (process.env.NOX_OFFLINE_MODE === "1") {
    throw new Error(
      "OFFLINE_MODE_BLOCKED: refused outbound request to " + url
    );
  }

  const isHttps = url.startsWith("https://");
  const lib = isHttps ? https : http;

  return new Promise((resolve, reject) => {
    const req = lib.get(url, { timeout: 3000 }, (res) => {
      let body = "";
      res.on("data", (d) => {
        body += d.toString();
      });
      res.on("end", () => resolve({ status: res.statusCode, body }));
    });
    req.on("error", reject);
    req.on("timeout", () => {
      req.destroy();
      reject(new Error("timeout"));
    });
  });
}

// ---------------------------------------------------------------------------
// Fixture DB (JSON-backed). 5 synthetic chunks with embeddings.
// ---------------------------------------------------------------------------

function defaultFixturePath() {
  return path.join(__dirname, "fixture-db.json");
}

function loadFixtureDb() {
  const dbPath = process.env.NOX_FIXTURE_DB || defaultFixturePath();
  if (!fs.existsSync(dbPath)) {
    return { chunks: [], cacheHits: 0, version: 0 };
  }
  return JSON.parse(fs.readFileSync(dbPath, "utf8"));
}

function saveFixtureDb(db) {
  const dbPath = process.env.NOX_FIXTURE_DB || defaultFixturePath();
  fs.writeFileSync(dbPath, JSON.stringify(db, null, 2), "utf8");
}

// Synthetic 32-dim "embedding" — deterministic hash of token bag.
// Real nox-mem uses 3072-dim Gemini embeddings; for CI we just need
// reproducibility + a cache-key surface.
function synthesizeEmbedding(text) {
  if (process.env.NOX_FAIL_IF_EMBED === "1") {
    const err = new Error(
      "EMBED_CALLED_UNEXPECTEDLY: embedding function was invoked but cache replay was expected"
    );
    err.code = "EMBED_CALLED";
    throw err;
  }

  recordOutbound("https://generativelanguage.googleapis.com/v1beta/embed");

  if (process.env.NOX_OFFLINE_MODE === "1") {
    throw new Error(
      "OFFLINE_MODE_BLOCKED: refused to call Gemini embedding endpoint"
    );
  }

  const tokens = text.toLowerCase().split(/\s+/).filter(Boolean);
  const vec = new Array(32).fill(0);
  for (const t of tokens) {
    let h = 0;
    for (let i = 0; i < t.length; i++) {
      h = (h * 31 + t.charCodeAt(i)) >>> 0;
    }
    vec[h % 32] += 1;
  }
  // L2 normalize
  let norm = 0;
  for (const v of vec) norm += v * v;
  norm = Math.sqrt(norm) || 1;
  return vec.map((v) => v / norm);
}

function cosineSim(a, b) {
  let dot = 0;
  for (let i = 0; i < a.length; i++) dot += a[i] * b[i];
  return dot;
}

// BM25-ish scoring (simplified — token overlap weighted by inverse chunk length)
function bm25Score(query, chunk) {
  const qTokens = new Set(query.toLowerCase().split(/\s+/).filter(Boolean));
  const cTokens = chunk.text.toLowerCase().split(/\s+/).filter(Boolean);
  let hits = 0;
  for (const t of cTokens) if (qTokens.has(t)) hits++;
  return hits / Math.sqrt(cTokens.length || 1);
}

// ---------------------------------------------------------------------------
// Provider abstraction (mocks the future A3 interface)
// ---------------------------------------------------------------------------

function resolveProvider() {
  const provider = process.env.NOX_LLM_PROVIDER || "gemini";

  if (provider === "gemini") {
    if (!process.env.GEMINI_API_KEY) {
      return {
        ok: false,
        error: "PROVIDER_AUTH_MISSING",
        provider: "gemini",
        hint: "Set GEMINI_API_KEY env",
      };
    }
    return { ok: true, provider: "gemini" };
  }

  if (provider === "anthropic") {
    const key = process.env.NOX_ANTHROPIC_API_KEY || process.env.ANTHROPIC_API_KEY;
    if (!key) {
      return {
        ok: false,
        error: "PROVIDER_AUTH_MISSING",
        provider: "anthropic",
        hint: "Check ANTHROPIC_API_KEY env",
      };
    }
    // Validate shape — real keys start with "sk-ant-" and are >40 chars
    if (!/^sk-ant-/.test(key) || key.length < 20) {
      return {
        ok: false,
        error: "PROVIDER_AUTH_FAILED",
        provider: "anthropic",
        hint: "Check ANTHROPIC_API_KEY env — key shape invalid",
      };
    }
    // Even with a valid shape, in CI we never make a real call.
    // Treat as auth failed because the dummy key is not actually live.
    return {
      ok: false,
      error: "PROVIDER_AUTH_FAILED",
      provider: "anthropic",
      hint: "Check ANTHROPIC_API_KEY env — credential rejected by provider",
    };
  }

  return {
    ok: false,
    error: "PROVIDER_UNKNOWN",
    provider,
    hint: "NOX_LLM_PROVIDER must be one of: gemini, anthropic",
  };
}

// ---------------------------------------------------------------------------
// Commands
// ---------------------------------------------------------------------------

function cmdStats() {
  const db = loadFixtureDb();
  const out = {
    status: "ok",
    totalChunks: db.chunks.length,
    embeddedChunks: db.chunks.filter((c) => Array.isArray(c.embedding)).length,
    vectorCoverage:
      db.chunks.length === 0
        ? 1
        : db.chunks.filter((c) => Array.isArray(c.embedding)).length /
          db.chunks.length,
    embeddingCacheHits: db.cacheHits || 0,
    offlineMode: process.env.NOX_OFFLINE_MODE === "1",
    provider: process.env.NOX_LLM_PROVIDER || "gemini",
  };
  console.log(JSON.stringify(out));
  return 0;
}

function cmdSearch(query) {
  if (!query) {
    console.error(
      JSON.stringify({ error: "USAGE", hint: 'search "<query string>"' })
    );
    return 2;
  }
  const db = loadFixtureDb();
  if (db.chunks.length === 0) {
    console.log(JSON.stringify({ results: [], note: "fixture empty" }));
    return 0;
  }

  // Hybrid path: try semantic first (which goes through embedding cache).
  let semanticResults = [];
  let cacheHit = false;
  const queryHash = hashString(query);

  db.cache = db.cache || {};
  if (db.cache[queryHash]) {
    cacheHit = true;
    db.cacheHits = (db.cacheHits || 0) + 1;
    const qVec = db.cache[queryHash];
    semanticResults = db.chunks
      .filter((c) => Array.isArray(c.embedding))
      .map((c) => ({ chunk: c, score: cosineSim(qVec, c.embedding) }))
      .sort((a, b) => b.score - a.score)
      .slice(0, 3);
  } else {
    // Cache miss — would need to call embedder. Honor NOX_FAIL_IF_EMBED.
    try {
      const qVec = synthesizeEmbedding(query);
      db.cache[queryHash] = qVec;
      semanticResults = db.chunks
        .filter((c) => Array.isArray(c.embedding))
        .map((c) => ({ chunk: c, score: cosineSim(qVec, c.embedding) }))
        .sort((a, b) => b.score - a.score)
        .slice(0, 3);
    } catch (e) {
      // Fall through to FTS-only when offline / when embed blocked
      semanticResults = [];
    }
  }

  // FTS5-equivalent path (always works, no network)
  const ftsResults = db.chunks
    .map((c) => ({ chunk: c, score: bm25Score(query, c) }))
    .filter((r) => r.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 3);

  // Naive RRF fusion
  const fused = new Map();
  semanticResults.forEach((r, idx) => {
    fused.set(r.chunk.id, { chunk: r.chunk, rrf: 1 / (60 + idx + 1) });
  });
  ftsResults.forEach((r, idx) => {
    const existing = fused.get(r.chunk.id);
    if (existing) {
      existing.rrf += 1 / (60 + idx + 1);
    } else {
      fused.set(r.chunk.id, { chunk: r.chunk, rrf: 1 / (60 + idx + 1) });
    }
  });

  const final = [...fused.values()]
    .sort((a, b) => b.rrf - a.rrf)
    .slice(0, 3)
    .map((r) => ({ id: r.chunk.id, text: r.chunk.text, score: r.rrf }));

  saveFixtureDb(db);

  console.log(
    JSON.stringify({
      query,
      results: final,
      cacheHit,
      offlineMode: process.env.NOX_OFFLINE_MODE === "1",
    })
  );
  return 0;
}

function cmdIngestEntity(file) {
  if (!file || !fs.existsSync(file)) {
    console.error(
      JSON.stringify({
        error: "USAGE",
        hint: "ingest-entity <path-to-entity.md>",
      })
    );
    return 2;
  }
  const content = fs.readFileSync(file, "utf8");

  // Split into the canonical 3 sections (frontmatter / compiled / timeline)
  const parts = content.split(/^# /m);
  const sections = parts
    .map((p, i) => {
      if (i === 0 && p.startsWith("---")) return { name: "frontmatter", text: p };
      const headerEnd = p.indexOf("\n");
      const name = (p.slice(0, headerEnd) || "section").toLowerCase().trim();
      return { name, text: p.slice(headerEnd + 1).trim() };
    })
    .filter((s) => s.text);

  const db = loadFixtureDb();
  let added = 0;
  for (const s of sections) {
    const id = "chunk-" + (db.chunks.length + 1);
    let embedding = null;
    if (process.env.NOX_OFFLINE_MODE !== "1") {
      try {
        embedding = synthesizeEmbedding(s.text);
      } catch {
        embedding = null;
      }
    }
    db.chunks.push({
      id,
      text: s.text,
      section: s.name,
      embedding,
      source: path.basename(file),
    });
    added++;
  }
  saveFixtureDb(db);

  console.log(
    JSON.stringify({
      ingested: added,
      file: path.basename(file),
      chunks: added,
      success: true,
    })
  );
  return 0;
}

function cmdAnswer(query) {
  if (!query) {
    console.error(JSON.stringify({ error: "USAGE", hint: 'answer "<question>"' }));
    return 2;
  }
  const provider = resolveProvider();
  if (!provider.ok) {
    // Structured, actionable error — never silent, never a stack trace.
    console.error(JSON.stringify(provider));
    return 3;
  }

  // Even with provider OK, we don't actually call out in this mock.
  // We just demonstrate that the provider plumbing reads env vars correctly.
  console.log(
    JSON.stringify({
      answer: "[mock] synthesized answer for: " + query,
      provider: provider.provider,
    })
  );
  return 0;
}

function hashString(s) {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = ((h * 31) + s.charCodeAt(i)) >>> 0;
  return "h" + h.toString(16);
}

// ---------------------------------------------------------------------------
// CLI dispatch
// ---------------------------------------------------------------------------

const args = process.argv.slice(2);
const cmd = args[0];

try {
  let exitCode = 1;
  switch (cmd) {
    case "stats":
      exitCode = cmdStats();
      break;
    case "search":
      exitCode = cmdSearch(args[1]);
      break;
    case "ingest-entity":
      exitCode = cmdIngestEntity(args[1]);
      break;
    case "answer":
      exitCode = cmdAnswer(args[1]);
      break;
    default:
      console.error(
        JSON.stringify({
          error: "UNKNOWN_COMMAND",
          got: cmd,
          available: ["stats", "search", "ingest-entity", "answer"],
        })
      );
      exitCode = 2;
  }
  process.exit(exitCode);
} catch (e) {
  console.error(
    JSON.stringify({
      error: "MOCK_INTERNAL_ERROR",
      message: e && e.message ? e.message : String(e),
    })
  );
  process.exit(1);
}
