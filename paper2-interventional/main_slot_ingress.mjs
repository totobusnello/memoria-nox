/** Does the written chunk enter the 8 MAIN slots, per agent, unboosted?
 *  §2 claim (i) says never, "by construction". This measures it.
 *  Throwaway copies; prod untouched. */
import Database from "/root/.openclaw/workspace/tools/nox-mem/node_modules/better-sqlite3/lib/index.js";
import { buildBriefDiverse, ensureBriefLog }
  from "/root/.openclaw/workspace/tools/nox-mem/dist/api/brief.js";

const DB_PATH = process.argv[2];
const db = new Database(DB_PATH);
db.loadExtension("/root/.openclaw/workspace/tools/nox-mem/node_modules/sqlite-vec-linux-x64/vec0");
ensureBriefLog(db);
const NOW = Date.now();
const iso = (d) => new Date(NOW - d * 86400000).toISOString().slice(0, 19).replace("T", " ");
const SEV = { S1: 0.25, S2: 0.50, S3: 0.75, S4: 1.00 };
const IDADES = [1, 7, 30];
const CFG = { freshSlots: 2, freshMinImp: 0.7, freshMinPain: 0.7,
              freshMaxAgeDays: 7, freshGlobalMaxAgeDays: 30,
              noveltyPMax: 0, noveltyHalfLife: 1 };
const AGENTES = ["nox", "atlas", "boris", "cipher", "forge", "lex"];

const ins = db.prepare(
  `INSERT INTO chunks (source_file, chunk_text, chunk_type, source_date, created_at,
     updated_at, importance, pain, access_count, retention_days)
   VALUES (?,?,?,?,?,?,0.90,?,0,180)`);
const del = db.prepare(`DELETE FROM chunks WHERE id = ?`);

const out = { db: DB_PATH, now: new Date(NOW).toISOString(), casos: {} };
for (const [k, sev] of Object.entries(SEV)) {
  for (const idade of IDADES) {
    const t = iso(idade);
    const info = ins.run(`memory/entities/lessons/probe-${k}-${idade}d.md`,
                         `probe ${k} ${idade}`, "lesson", t, t, t, sev);
    const id = Number(info.lastInsertRowid);
    const linha = {};
    for (const ag of AGENTES) {
      const r = buildBriefDiverse(db, { scope: "global", agent: ag, n: 10 }, CFG, NOW);
      const fresh = new Set(r.diff.fresh_added.filter((x) => x != null));
      const item = r.alt.items.find((x) => x.id === id);
      const base = r.current.items.some((x) => x.id === id);
      linha[ag] = item
        ? { servido: true, via: fresh.has(id) ? "cobertura" : "principal",
            salience: Number(item.salience.toFixed(6)), no_baseline: base }
        : { servido: false, via: null, no_baseline: base };
    }
    out.casos[`${k}@${idade}d`] = linha;
    del.run(id);
  }
}
console.log(JSON.stringify(out, null, 1));
