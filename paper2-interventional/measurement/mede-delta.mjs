import Database from "better-sqlite3";
import { calculateSalience } from "../src/../dist/salience.js";
import { DIVERSITY_DEFAULTS } from "../dist/api/brief-diversity.js";
const db = new Database("/root/.openclaw/workspace/tools/nox-mem/nox-mem.db", { readonly: true });
const cfg = DIVERSITY_DEFAULTS;
const PAT = ["memory/entities/%", "memory/lessons.md"];
const now = Date.now();
const rows = db.prepare(
  `SELECT id, source_file, chunk_text, chunk_type, source_type, tier,
          pain, importance, retention_days, source_date, created_at,
          updated_at, last_accessed_at, access_count,
          (SELECT MAX(bl.served_at) FROM brief_log bl WHERE bl.chunk_id = chunks.id) AS last_served
     FROM chunks
    WHERE (source_file LIKE ? ESCAPE '\\' OR source_file LIKE ? ESCAPE '\\')
      AND (COALESCE(importance,0) >= ? OR COALESCE(pain,0) >= ?)
      AND julianday('now') - julianday(COALESCE(source_date, created_at)) <= ?
    ORDER BY last_served ASC,
             (0.55*COALESCE(importance,0.5) + 0.10*COALESCE(pain,0.2)
              + CASE WHEN COALESCE(access_count,0) > 0 THEN 0.1 ELSE 0 END) DESC
    LIMIT 400`
).all(...PAT, cfg.freshMinImp, cfg.freshMinPain, cfg.freshGlobalMaxAgeDays);
const estudo = new Set(db.prepare(
  "SELECT DISTINCT chunk_id FROM p2_verdict WHERE chunk_id IS NOT NULL AND severity IN ('S1','S2')"
).all().map(r => r.chunk_id));
const cand = rows.map(r => ({
  id: r.id,
  sal: calculateSalience(r, now),
  ls: r.last_served,          // string ou null — a chave de empate EXATA
  estudo: estudo.has(r.id),
}));
console.log(JSON.stringify({
  pool: cand.length,
  do_estudo_no_pool: cand.filter(c => c.estudo).length,
  total_do_estudo: estudo.size,
  cand,
}));
