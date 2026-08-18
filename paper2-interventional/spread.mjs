import Database from "/root/.openclaw/workspace/tools/nox-mem/node_modules/better-sqlite3/lib/index.js";
import { buildBriefDiverse, ensureBriefLog } from "/root/.openclaw/workspace/tools/nox-mem/dist/api/brief.js";
const db = new Database(process.argv[2]);
db.loadExtension("/root/.openclaw/workspace/tools/nox-mem/node_modules/sqlite-vec-linux-x64/vec0");
ensureBriefLog(db);
const NOW = Date.now();
const CFG = { freshSlots:2, freshMinImp:0.7, freshMinPain:0.7, freshMaxAgeDays:7,
              freshGlobalMaxAgeDays:30, noveltyPMax:0, noveltyHalfLife:1 };
const out = {};
for (const ag of ["nox","atlas","boris","cipher","forge","lex"]) {
  const r = buildBriefDiverse(db, { scope:"global", agent:ag, n:10 }, CFG, NOW);
  const s = r.alt.items.map(x=>x.salience);
  const gaps = s.slice(1).map((v,i)=>Math.abs(s[i]-v));
  out[ag] = { n:s.length, topo:+s[0].toFixed(6), base:+s[s.length-1].toFixed(6),
              spread_total:+(s[0]-s[s.length-1]).toFixed(6),
              gap_mediano:+gaps.sort((a,b)=>a-b)[Math.floor(gaps.length/2)].toFixed(6) };
}
console.log(JSON.stringify(out,null,1));
