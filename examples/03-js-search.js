#!/usr/bin/env node
/**
 * 30-second search example in JavaScript.
 * Requires Node 20+ (native fetch — no npm install needed).
 *
 * Usage:
 *   ./examples/03-js-search.js [query]
 *   BASE_URL=http://localhost:18802 node examples/03-js-search.js "my query"
 */

const BASE_URL = (process.env.BASE_URL || "http://187.77.234.79:18802").replace(/\/$/, "");

async function health() {
  const r = await fetch(`${BASE_URL}/api/health`);
  if (!r.ok) throw new Error(`Health failed: ${r.status} ${r.statusText}`);
  return r.json();
}

async function search(query, limit = 5) {
  const params = new URLSearchParams({ q: query, limit: String(limit) });
  const r = await fetch(`${BASE_URL}/api/search?${params}`);
  if (!r.ok) throw new Error(`Search failed: ${r.status} ${r.statusText}`);
  const data = await r.json();
  return data.results || [];
}

(async () => {
  // Health
  const h = await health();
  const vecPct = typeof h.vec_coverage === "number"
    ? `${(h.vec_coverage * 100).toFixed(1)}%`
    : String(h.vec_coverage ?? "?");
  console.log(`DB: ${h.chunks_total ?? "?"} chunks, vec=${vecPct}`);
  console.log(`KG: ${h.kg_entities ?? "?"} entities / ${h.kg_relations ?? "?"} relations`);
  console.log();

  // Search
  const query = process.argv.slice(2).join(" ") || "pain-weighted hybrid memory";
  console.log(`Query: ${JSON.stringify(query)}`);
  console.log("-".repeat(60));

  const results = await search(query, 3);
  if (results.length === 0) {
    console.log("No results returned.");
    return;
  }

  results.forEach((r, i) => {
    const score = r.score != null ? Number(r.score).toFixed(3) : "?";
    const source = r.source_file ?? r.source ?? "?";
    const snippet = (r.snippet ?? "").trim().slice(0, 160);
    console.log(`\n  ${i + 1}. score=${score}`);
    console.log(`     source=${source}`);
    if (snippet) console.log(`     ${snippet}...`);
  });
})().catch((e) => {
  console.error(`Error: ${e.message}`);
  process.exit(1);
});
