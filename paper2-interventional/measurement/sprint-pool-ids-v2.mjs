#!/usr/bin/env node
/**
 * sprint-pool-ids-v2.mjs — sprint 2026-10-04, task "B-sham-v2".
 *
 * Dumps, per state, the ids of the GLOBAL coverage pool as the REAL serving code
 * builds it (`fetchFreshCandidates` from the serving `dist`, same call as
 * `replay-oportunidade.mjs` `poolGlobal`), on a given corpus, with the exact
 * `rowid` serve-state cut. Nothing about selection is reimplemented.
 *
 * Why it exists: `sprint-gera-shams-v2.py` draws shams from "the pool". The old
 * generator derived that pool with its own SQL and checked only the COUNT against
 * the replay (115 = 115). A count can agree while the sets differ. This dump gives
 * the generator the SET the mechanism sees, so it can assert set equality between
 * two independent routes (its SQL predicate and this real-code pool).
 *
 * Output: { procedencia, estados: [{ts, agent, rowid_proprio, pool_ids:[...]}],
 *           uniao_ids, intersecao_ids }.
 *
 * Usage (research VPS, on COPIES only):
 *   node sprint-pool-ids-v2.mjs --raiz <nox-mem root with dist/ src/> \
 *     --corpus <corpus copy> --brief-log <db copy holding brief_log> \
 *     --log-campo p2-serving.ndjson --so-ts-file ts.txt --out pool.json
 */
import Database from "better-sqlite3";
import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";

const A = {};
for (let i = 2; i < process.argv.length; i++) {
  const k = process.argv[i].replace(/^--/, "");
  A[k] = process.argv[++i];
}
for (const k of ["raiz", "corpus", "brief-log", "log-campo", "so-ts-file", "out"]) {
  if (!A[k]) { console.error(`missing --${k} (no defaults)`); process.exit(2); }
}
const RAIZ = resolve(A.raiz);
const brief = await import(join(RAIZ, "dist", "api", "brief.js"));
const div = await import(join(RAIZ, "dist", "api", "brief-diversity.js"));

// Same guard as replay-oportunidade.mjs / sprint-replay-estratos.mjs: the copied
// literal must equal the source, or abort.
const FONTE = readFileSync(join(RAIZ, "src", "api", "brief.ts"), "utf8");
const GLOBAL_FRESH_PATTERNS = ["memory/entities/%", "memory/lessons.md"];
const m = FONTE.match(/const GLOBAL_FRESH_PATTERNS = (\[[^\]]*\]);/);
if (!m || JSON.parse(m[1].replace(/'/g, '"')).join("|") !== GLOBAL_FRESH_PATTERNS.join("|")) {
  console.error("GLOBAL_FRESH_PATTERNS diverged from source"); process.exit(2);
}

const msDe = (iso) => Date.parse(iso.includes("T") ? iso : iso.replace(" ", "T") + "Z");
const seg = (ms) => new Date(ms).toISOString().slice(0, 19).replace("T", " ");
/** Identical to replay-oportunidade.mjs `cfgEm`: translate the age cut to tRef. */
function cfgEm(tRefMs) {
  const base = { ...div.DIVERSITY_DEFAULTS, mode: "active" };
  const desloc = (Date.now() - tRefMs) / 86400000;
  return { ...base, freshMaxAgeDays: base.freshMaxAgeDays + desloc,
           freshGlobalMaxAgeDays: base.freshGlobalMaxAgeDays + desloc };
}

const corpus = new Database(resolve(A.corpus), { readonly: true, fileMustExist: true });
const bl = new Database(resolve(A["brief-log"]), { readonly: true, fileMustExist: true });

const set = new Set(readFileSync(resolve(A["so-ts-file"]), "utf8").split("\n").map((s) => s.trim()).filter(Boolean));
const estados = readFileSync(resolve(A["log-campo"]), "utf8").split("\n").filter((l) => l.trim())
  .map((l) => JSON.parse(l))
  .filter((r) => r.tag === "p2_outcome" && r.ids_controle?.length === 10 && set.has(r.ts));
if (estados.length !== set.size) {
  console.error(`--so-ts-file lists ${set.size} ts, ${estados.length} matched`); process.exit(2);
}

const grupos = bl.prepare(`SELECT brief_id, MIN(id) mi, GROUP_CONCAT(chunk_id) ids FROM brief_log
  WHERE served_at IN (?,?,?) AND COALESCE(agent,'') = ? AND brief_id IS NOT NULL GROUP BY brief_id`);
function rowidProprio(r) {
  const ids = (r.servido === "tratado" && Array.isArray(r.ids_tratado)) ? r.ids_tratado : r.ids_controle;
  const alvo = ids.slice().sort((a, b) => a - b).join(",");
  const t = msDe(r.ts);
  const c = grupos.all(seg(t), seg(t + 1000), seg(t + 2000), r.agent ?? "")
    .filter((g) => String(g.ids).split(",").map(Number).sort((a, b) => a - b).join(",") === alvo);
  return c.length === 1 ? c[0].mi : null;
}

const res = [];
let uniao = null, inter = null;
for (const r of estados) {
  const tRef = msDe(r.ts);
  const idp = rowidProprio(r);
  if (idp === null) { res.push({ ts: r.ts, agent: r.agent, erro: "brief not located (rowid cut impossible)" }); continue; }
  const d = new Database(":memory:");
  d.exec(`CREATE TABLE brief_log (id INTEGER PRIMARY KEY, chunk_id INTEGER NOT NULL, scope TEXT,
            agent TEXT, served_at TEXT NOT NULL, brief_id TEXT);
          CREATE INDEX idx_brief_log_chunk ON brief_log(chunk_id, served_at);`);
  const rows = bl.prepare("SELECT id, chunk_id, scope, agent, served_at, brief_id FROM brief_log WHERE id < ?").all(idp);
  const ins = d.prepare("INSERT INTO brief_log VALUES (?,?,?,?,?,?)");
  d.transaction(() => { for (const x of rows) ins.run(x.id, x.chunk_id, x.scope, x.agent, x.served_at, x.brief_id); })();
  const cfg = cfgEm(tRef);
  const pool = brief.fetchFreshCandidates(corpus, GLOBAL_FRESH_PATTERNS,
    { ...cfg, freshMaxAgeDays: cfg.freshGlobalMaxAgeDays }, tRef, d, undefined);
  const ids = pool.map((c) => c.row.id).sort((a, b) => a - b);
  d.close();
  res.push({ ts: r.ts, agent: r.agent, rowid_proprio: idp, pool: ids.length, pool_ids: ids });
  const s = new Set(ids);
  uniao = uniao ? new Set([...uniao, ...s]) : s;
  inter = inter ? new Set([...inter].filter((x) => s.has(x))) : new Set(s);
}

const out = {
  procedencia: {
    gerado_em: new Date().toISOString(), corpus: resolve(A.corpus), brief_log: resolve(A["brief-log"]),
    estados: res.length, erros: res.filter((x) => x.erro).length,
    fonte_brief_ts_sha256: createHash("sha256").update(FONTE).digest("hex"),
  },
  uniao_ids: [...(uniao ?? [])].sort((a, b) => a - b),
  intersecao_ids: [...(inter ?? [])].sort((a, b) => a - b),
  estados: res,
};
writeFileSync(resolve(A.out), JSON.stringify(out, null, 1) + "\n");
console.error(`estados=${res.length} erros=${out.procedencia.erros} uniao=${out.uniao_ids.length} intersecao=${out.intersecao_ids.length}`);
