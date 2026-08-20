/** O conteúdo do caller é parseável e produz compiled com importance 0.90? */
import Database from "/root/.openclaw/workspace/tools/nox-mem/node_modules/better-sqlite3/lib/index.js";
import { ingestEntityContentSync, parseEntityFile }
  from "/root/.openclaw/workspace/tools/nox-mem/dist/ingest-entity.js";
import { readFileSync } from "fs";
const conteudo = readFileSync("/tmp/amostra-conteudo.txt", "utf-8");

const p = parseEntityFile(conteudo);
console.log("parseEntityFile:", p ? "OK" : "NULL (não casaria o formato!)");
if (p) console.log("  seções: frontmatter=sim compiled=" + (p.compiled ? "sim" : "NÃO") +
                   " timeline=" + p.timeline.length + " entradas");

const db = new Database("/tmp/p2-parse.db");
db.loadExtension("/root/.openclaw/workspace/tools/nox-mem/node_modules/sqlite-vec-linux-x64/vec0");
const rel = "memory/entities/lessons/0025ff3d6d1265c2.md";
const r = db.transaction(() => ingestEntityContentSync(conteudo, rel, db, {
  pain: 0.50,
  metadataExtra: { p2: { episode_id: "0025ff3d6d1265c2", sig_primary: "mcp__openclaw__message|sem-arg", severity: "S2" } },
}))();
console.log("ingest:", JSON.stringify(r));

const rows = db.prepare(
  `SELECT section, importance, pain, chunk_type, length(chunk_text) len,
          json_extract(metadata,'$.p2.severity') sev
   FROM chunks WHERE source_file = ? ORDER BY id`).all(rel);
console.log("\nchunks gravados:");
for (const x of rows) console.log("  " + JSON.stringify(x));
const comp = rows.find(x => x.section === "compiled");
console.log("\ngate de cobertura (importance>=0.7 OR pain>=0.7):",
  comp && (comp.importance >= 0.7 || comp.pain >= 0.7) ? "PASSA ✅" : "REPROVA ❌");
console.log("texto do compiled é exatamente as 3 linhas:",
  comp && comp.len === 108 ? "conferir abaixo" : `len=${comp?.len}`);
console.log(JSON.stringify(db.prepare(`SELECT chunk_text FROM chunks WHERE source_file=? AND section='compiled'`).get(rel)));
