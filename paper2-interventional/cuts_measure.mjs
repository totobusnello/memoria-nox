/** Incumbent salience at each brief slot, REAL corpus + realistic scope/agent,
 *  before and after the study's own inflow. Throwaway copy; prod untouched. */
import Database from "/root/.openclaw/workspace/tools/nox-mem/node_modules/better-sqlite3/lib/index.js";
import { buildBriefDiverse, fetchFreshCandidates, ensureBriefLog }
  from "/root/.openclaw/workspace/tools/nox-mem/dist/api/brief.js";
import { calculateSalience } from "/root/.openclaw/workspace/tools/nox-mem/dist/salience.js";

const db = new Database("/tmp/p2-real.db");
ensureBriefLog(db);
const NOW = Date.now();
const iso = (d) => new Date(NOW - d * 86400000).toISOString().slice(0, 19).replace("T", " ");
const SEV = { S1: 0.25, S2: 0.50, S3: 0.75, S4: 1.00 };
const SHARE = { S1: 0.6973, S2: 0.2962, S3: 0.0058, S4: 0.0008 };
const CFG = { freshSlots: 2, freshMinImp: 0.7, freshMinPain: 0.7,
              freshMaxAgeDays: 7, freshGlobalMaxAgeDays: 30,
              noveltyPMax: 0, noveltyHalfLife: 1 };
const AGENTES = ["nox", "atlas", "boris", "cipher", "forge", "lex"];
const ins = db.prepare(
  `INSERT INTO chunks (source_file, chunk_text, chunk_type, source_date, created_at,
     updated_at, importance, pain, access_count, retention_days)
   VALUES (?,?,?,?,?,?,0.90,?,0,180)`);

function seed(dias) {
  let n = 0;
  const tx = db.transaction(() => {
    for (let d = 0; d < dias; d++)
      for (const [k, sev] of Object.entries(SEV)) {
        // ceil, not round: round(396*0.0008)=0 would delete the S4 stratum entirely
        const q = Math.max(1, Math.ceil(396 * SHARE[k]));
        for (let i = 0; i < q; i++) {
          ins.run(`memory/entities/lessons/study-d${d}-${k}-${i}.md`,
                  `study ${d} ${k} ${i}`, "lesson", iso(d + 0.2), iso(d + 0.2), iso(d + 0.2), sev);
          n++;
        }
      }
  });
  tx();
  return n;
}

function medir(rotulo) {
  const g = fetchFreshCandidates(db, ["memory/entities/%"], { ...CFG, freshMaxAgeDays: 30 }, NOW);
  const porAgente = AGENTES.map((ag) => {
    const a = fetchFreshCandidates(db, [`sessions/${ag}/%`], CFG, NOW);
    const r = buildBriefDiverse(db, { scope: "global", agent: ag, n: 10 }, CFG, NOW);
    const fresh = new Set(r.diff.fresh_added.filter((x) => x != null));
    const sals = r.alt.items.map((x) => ({ id: x.id, s: x.salience, fresh: fresh.has(x.id) }));
    const principais = sals.filter((x) => !x.fresh).map((x) => x.s);
    return { agente: ag, agentFresh: a.length,
      n_principais: principais.length,
      cut_principal: principais.length ? Number(Math.min(...principais).toFixed(6)) : null,
      slots_cobertura: sals.filter((x) => x.fresh).map((x) => Number(x.s.toFixed(6))) };
  });
  return { rotulo, globalFresh: g.length,
    topo_global: g.slice(0, 3).map((c) => Number(c.salience.toFixed(6))),
    por_agente: porAgente };
}

const out = { now: new Date(NOW).toISOString(), cenarios: [] };
out.cenarios.push(medir("corpus_real_sem_inflow"));
out.inflow_1d = seed(1);
out.cenarios.push(medir("mais_1_dia"));
out.inflow_mais_29d = seed(30);
out.cenarios.push(medir("mais_30_dias"));
console.log(JSON.stringify(out, null, 1));
