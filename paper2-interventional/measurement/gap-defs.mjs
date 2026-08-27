import Database from "better-sqlite3";
import { calculateSalience } from "../src/../dist/salience.js";
import { DIVERSITY_DEFAULTS } from "../dist/api/brief-diversity.js";
const [, , SNAP, T_REF, MODO] = process.argv;
const SEM = MODO === "sem-sondas";
const SONDAS = ["473f85e8-43ae-4883-baa2-2d76407af941","c48e8353-cd95-4bd5-997b-dc921e2a0cac",
  "6ff2d9c4-79f2-4526-8eb5-c42d60bbeea6","90a105f5-ef33-4135-8e54-b4e978bbb1ee",
  "66977ec1-2809-44df-91b8-c158ce0e68e8"];
const corpus = new Database(SNAP, { readonly: true, fileMustExist: true });
const live = new Database("/root/.openclaw/workspace/tools/nox-mem/nox-mem.db", { readonly: true });
const cfg = DIVERSITY_DEFAULTS, PAT = ["memory/entities/%", "memory/lessons.md"];
const now = Date.parse(T_REF.replace(" ", "T") + "Z");
const base = corpus.prepare(
  `SELECT id, source_file, chunk_text, chunk_type, source_type, tier, pain, importance,
          retention_days, source_date, created_at, updated_at, last_accessed_at, access_count
     FROM chunks
    WHERE (source_file LIKE ? ESCAPE '\\' OR source_file LIKE ? ESCAPE '\\')
      AND (COALESCE(importance,0) >= ? OR COALESCE(pain,0) >= ?)
      AND julianday(?) - julianday(COALESCE(source_date, created_at)) <= ?`
).all(...PAT, cfg.freshMinImp, cfg.freshMinPain, T_REF, cfg.freshGlobalMaxAgeDays);
const filtro = SEM ? `AND brief_id NOT IN (${SONDAS.map(() => "?").join(",")})` : "";
const lsStmt = live.prepare(`SELECT MAX(served_at) AS m FROM brief_log
   WHERE chunk_id = ? AND served_at <= ? ${filtro}`);
const estudo = new Set(live.prepare(
  "SELECT DISTINCT chunk_id FROM p2_verdict WHERE chunk_id IS NOT NULL AND severity IN ('S1','S2')"
).all().map(r => r.chunk_id));
let cand = base.map(r => ({ id: r.id, sal: calculateSalience(r, now),
  ls: lsStmt.get(r.id, T_REF, ...(SEM ? SONDAS : [])).m, estudo: estudo.has(r.id) }));
cand.sort((a, b) => {
  const al = a.ls === null ? "" : a.ls, bl = b.ls === null ? "" : b.ls;
  if (al !== bl) return al < bl ? -1 : 1;
  return b.sal - a.sal;
});
cand = cand.slice(0, 400);
const grupos = new Map();
for (const c of cand) { const k = String(c.ls); if (!grupos.has(k)) grupos.set(k, []); grupos.get(k).push(c); }
const defs = { adjacente_global: [], adjacente_no_grupo: [], todos_no_grupo: [] };
const z = { adjacente_global: 0, adjacente_no_grupo: 0, todos_no_grupo: 0 };
const nn = { adjacente_global: 0, adjacente_no_grupo: 0, todos_no_grupo: 0 };
function reg(k, a, b) { nn[k]++; const d = Math.abs(a.sal - b.sal); if (d < 1e-12) z[k]++; else defs[k].push(d); }
for (let i = 0; i + 1 < cand.length; i++) {
  const a = cand[i], b = cand[i + 1];
  if (!a.estudo && !b.estudo) continue;
  reg("adjacente_global", a, b);
  if (String(a.ls) === String(b.ls)) reg("adjacente_no_grupo", a, b);
}
for (const [, v] of grupos) for (let i = 0; i < v.length; i++) for (let j = i + 1; j < v.length; j++)
  if (v[i].estudo || v[j].estudo) reg("todos_no_grupo", v[i], v[j]);
const saida = {};
for (const k of Object.keys(defs)) { defs[k].sort((x, y) => x - y);
  saida[k] = { pares: nn[k], zeros: z[k], positivos: defs[k].length,
               gap_min: defs[k][0] ?? null, gap_max: defs[k].at(-1) ?? null }; }
console.log(JSON.stringify({ T_REF, sem_sondas: SEM, pool: cand.length, grupos: grupos.size,
  posicao_primeiro_estudo: cand.findIndex(c => c.estudo), defs: saida }));
