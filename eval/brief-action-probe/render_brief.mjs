#!/usr/bin/env node
// Renders a brief from chunk ids with the PRODUCTION formatter (spec §3, §4.1).
// toItems() is not exported by src/api/brief.ts; the mapping below mirrors it, and the §4.1 gate
// (scripts/fidelity_gate.py) is what proves the mirror reproduces served briefs byte for byte.
import { createRequire } from "node:module";
import { createInterface } from "node:readline";
import { pathToFileURL } from "node:url";

const dir = process.env.NOX_MEM_DIR;
if (!dir) { console.error("NOX_MEM_DIR is required"); process.exit(2); }
const require = createRequire(`${dir}/package.json`);
const Database = require("better-sqlite3");
const brief = await import(pathToFileURL(`${dir}/dist/api/brief.js`).href);
const db = new Database(process.env.NOX_MEM_DB ?? `${dir}/nox-mem.db`, { readonly: true, fileMustExist: true });
const get = db.prepare(
  "SELECT id, source_file, chunk_text, chunk_type, pain, source_date, created_at, updated_at FROM chunks WHERE id = ?",
);

for await (const line of createInterface({ input: process.stdin })) {
  if (!line.trim()) continue;
  const req = JSON.parse(line);
  const items = [];
  const missing = [];
  for (const id of req.chunk_ids) {
    const row = get.get(id);
    if (!row) { missing.push(id); continue; }
    const ref = row.source_date ?? row.created_at ?? row.updated_at;
    const refMs = ref ? brief.parseDbDateMs(ref) : NaN;
    items.push({
      id: row.id,
      title: brief.titleFromSourceFile(row.source_file),
      one_liner: brief.extractOneLiner(row.chunk_text),
      type: row.chunk_type,
      pain: row.pain ?? 0.2,
      salience: 0,
      age_days: Number.isFinite(refMs) ? Math.max(0, Math.floor((req.now_ms - refMs) / 86_400_000)) : 0,
    });
  }
  const result = {
    scope: req.scope ?? "global",
    ...(req.agent ? { agent: req.agent } : {}),
    generated_at: new Date(req.now_ms).toISOString(),
    items,
    token_estimate: 0,
  };
  process.stdout.write(JSON.stringify({
    text: brief.renderBriefText(result),
    items: items.map((i) => ({ id: i.id, title: i.title, one_liner: i.one_liner })),
    missing,
  }) + "\n");
}
