/** Opção 1 vs 2: o que o pool de cobertura vira se o padrão incluir os
 *  agregados planos onde a memória de fato vive hoje. Read-only em cópia. */
import Database from "/root/.openclaw/workspace/tools/nox-mem/node_modules/better-sqlite3/lib/index.js";
import { fetchFreshCandidates, ensureBriefLog } from "/root/.openclaw/workspace/tools/nox-mem/dist/api/brief.js";
const db = new Database(process.argv[2]);
db.loadExtension("/root/.openclaw/workspace/tools/nox-mem/node_modules/sqlite-vec-linux-x64/vec0");
ensureBriefLog(db);
const NOW = Date.now();
const CFG = { freshSlots:2, freshMinImp:0.7, freshMinPain:0.7, freshMaxAgeDays:7,
              freshGlobalMaxAgeDays:30, noveltyPMax:0, noveltyHalfLife:1 };
const G = { ...CFG, freshMaxAgeDays: 30 };

const cenarios = {
  "opcao 1 — atual":            ["memory/entities/%"],
  "opcao 2a — + lessons.md":    ["memory/entities/%", "memory/lessons.md"],
  "opcao 2b — + todo memory/%": ["memory/entities/%", "memory/%.md"],
};
const out = {};
for (const [rot, pats] of Object.entries(cenarios)) {
  const c = fetchFreshCandidates(db, pats, G, NOW);
  const s = c.map(x => x.salience).sort((a,b) => b-a);
  out[rot] = { n: c.length, slot1: s[0] ?? null, slot2: s[1] ?? null, slot3: s[2] ?? null,
               tipos: [...new Set(c.slice(0,20).map(x => x.chunk_type))].slice(0,5) };
}
console.log(JSON.stringify(out, null, 1));
