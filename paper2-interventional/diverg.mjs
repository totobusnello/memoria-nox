/** Divergência que o flip shadow->active produziria HOJE: brief do snapshot de
 *  epoch vs brief do live, por agente. Reproduzível (não é ring buffer). */
import Database from "/root/.openclaw/workspace/tools/nox-mem/node_modules/better-sqlite3/lib/index.js";
import { buildBriefDiverse, ensureBriefLog } from "/root/.openclaw/workspace/tools/nox-mem/dist/api/brief.js";
const VEC = "/root/.openclaw/workspace/tools/nox-mem/node_modules/sqlite-vec-linux-x64/vec0";
const abrir = (p) => { const d = new Database(p, { readonly: false }); d.loadExtension(VEC); ensureBriefLog(d); return d; };

const live = abrir(process.env.NOX_DB_PATH);
const snap = abrir("/var/lib/nox-mem/epochs/current.db");
const NOW = Date.now();
const CFG = { freshSlots:2, freshMinImp:0.7, freshMinPain:0.7, freshMaxAgeDays:7,
              freshGlobalMaxAgeDays:30, noveltyPMax:0, noveltyHalfLife:1 };
const ids = (db, ag) => buildBriefDiverse(db, { scope:"global", agent:ag, n:10 }, CFG, NOW).alt.items.map(x=>x.id);

console.log("agente    n_live n_snap  idênticos  itens_diferentes");
let totDif = 0, totItens = 0;
for (const ag of ["nox","atlas","boris","cipher","forge","lex"]) {
  const a = ids(live, ag), b = ids(snap, ag);
  const dif = a.filter((x,i) => b[i] !== x).length;
  const setDif = a.filter(x => !b.includes(x)).length;
  totDif += setDif; totItens += a.length;
  console.log(`${ag.padEnd(9)} ${String(a.length).padEnd(6)} ${String(b.length).padEnd(6)} `
    + `${a.join(",")===b.join(",") ? "SIM" : "não"}        ${setDif}/${a.length} (posição: ${dif})`);
}
console.log(`\nitens que mudariam ao virar active: ${totDif}/${totItens} (${(100*totDif/totItens).toFixed(1)}%)`);
console.log("snapshot:", "/var/lib/nox-mem/epochs/current.db");
