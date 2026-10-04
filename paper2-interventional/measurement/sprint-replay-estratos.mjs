#!/usr/bin/env node
/**
 * sprint-replay-estratos.mjs — sprint 2026-10-04, task "B-replay-fidelity".
 *
 * Tests the hypothesis declared (unmeasured) in docs/HANDOFF.md 2026-09-23:
 *
 *   "the serve-state derived today does not reproduce the TIES in last_served that
 *    existed at the time, so the strata become singletons and the subordinate
 *    coordinate (where the bonus enters) never decides, for any dose."
 *
 * What it does, per state (one `p2_outcome` line of p2-serving.ndjson):
 *   - builds the GLOBAL coverage pool with the REAL `fetchFreshCandidates` imported
 *     from the serving `dist` (same call `replay-oportunidade.mjs` makes in
 *     `poolGlobal`), against a given corpus and a serve-state cut from a given
 *     `brief_log`;
 *   - recovers each pool member's `last_served` with the SAME query the code uses
 *     (`MAX(served_at)`), because `ordenarCobertura` drops `lastServedMs`;
 *   - reports the stratum structure the comparator sees: run-lengths of identical
 *     `last_served` in pool order, the NULL (never-served) stratum, the stratum at
 *     the fresh-slot boundary, and how many DESIGNATED chunks sit in it (only those
 *     can be moved by an additive bonus — Proposition 1 of §5);
 *   - for the ids production recorded as `would_enter` / `would_leave`, their
 *     `last_served` and whether they TIE (Prop. 1 requires it for production's churn).
 *
 * Three serve-state cuts, all from the same `brief_log` (append-only; no DELETE on
 * brief_log anywhere in src/ — checked 2026-10-04):
 *   rowid      `id < min(id of this brief's own rows)` — the exact state production
 *              saw (the brief composes BEFORE inserting its rows);
 *   estrito    `served_at < second(ts)`;
 *   inclusivo  `served_at <= second(ts)` — what sonda2/sonda3 and roda-sham.sh use.
 *
 * Nothing here is a reimplementation of selection: pool order comes from the real
 * code; only the stratum KEY is re-read, with the code's own query.
 *
 * Usage (research VPS, on COPIES only):
 *   node sprint-replay-estratos.mjs --raiz <nox-mem root with dist/ src/> \
 *     --corpus <corpus copy> --brief-log <db copy holding brief_log> \
 *     --log-campo p2-serving.ndjson --so-ts-file ts.txt \
 *     --designacao DESIGNATION-2026-08-26.json --out out.json
 */
import Database from "better-sqlite3";
import { readFileSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";

const A = {};
for (let i = 2; i < process.argv.length; i++) {
  const k = process.argv[i].replace(/^--/, "");
  A[k] = process.argv[++i];
}
for (const k of ["raiz", "corpus", "brief-log", "log-campo", "so-ts-file", "designacao"]) {
  if (!A[k]) { console.error(`missing --${k} (no defaults)`); process.exit(2); }
}
const RAIZ = resolve(A.raiz);
const brief = await import(join(RAIZ, "dist", "api", "brief.js"));
const div = await import(join(RAIZ, "dist", "api", "brief-diversity.js"));

// Same guard as replay-oportunidade.mjs: the copied literal must equal the source.
const FONTE = readFileSync(join(RAIZ, "src", "api", "brief.ts"), "utf8");
const GLOBAL_FRESH_PATTERNS = ["memory/entities/%", "memory/lessons.md"];
const m = FONTE.match(/const GLOBAL_FRESH_PATTERNS = (\[[^\]]*\]);/);
if (!m || JSON.parse(m[1].replace(/'/g, '"')).join("|") !== GLOBAL_FRESH_PATTERNS.join("|")) {
  console.error("GLOBAL_FRESH_PATTERNS diverged from source"); process.exit(2);
}

const designados = new Set(Object.values(JSON.parse(readFileSync(resolve(A.designacao), "utf8")).designados));
if (designados.size !== 19) { console.error(`expected 19 designated, got ${designados.size}`); process.exit(2); }

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
const maxBl = bl.prepare("SELECT MAX(served_at) m FROM brief_log").get().m;

// Locate the brief's own rows: group by brief_id within (agent, second .. +2 s)
// whose chunk set equals the SERVED set (treated when servido=tratado).
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

/** In-memory serve-state for one cut. Same schema/index as the replay's. */
function serveState(cut, r, idProprio) {
  const d = new Database(":memory:");
  d.exec(`CREATE TABLE brief_log (id INTEGER PRIMARY KEY, chunk_id INTEGER NOT NULL, scope TEXT,
            agent TEXT, served_at TEXT NOT NULL, brief_id TEXT);
          CREATE INDEX idx_brief_log_chunk ON brief_log(chunk_id, served_at);`);
  const s = seg(msDe(r.ts));
  const rows = cut === "rowid"
    ? bl.prepare("SELECT id, chunk_id, scope, agent, served_at, brief_id FROM brief_log WHERE id < ?").all(idProprio)
    : bl.prepare(`SELECT id, chunk_id, scope, agent, served_at, brief_id FROM brief_log WHERE served_at ${cut === "inclusivo" ? "<=" : "<"} ?`).all(s);
  const ins = d.prepare("INSERT INTO brief_log VALUES (?,?,?,?,?,?)");
  d.transaction(() => { for (const x of rows) ins.run(x.id, x.chunk_id, x.scope, x.agent, x.served_at, x.brief_id); })();
  return { d, linhas: rows.length };
}

const res = [];
for (const r of estados) {
  const tRef = msDe(r.ts);
  const idProprio = rowidProprio(r);
  const cfg = cfgEm(tRef);
  const porCorte = {};
  for (const cut of ["rowid", "estrito", "inclusivo"]) {
    if (cut === "rowid" && idProprio === null) { porCorte[cut] = { erro: "brief not located in brief_log" }; continue; }
    if (seg(tRef) > maxBl) { porCorte[cut] = { erro: `brief_log ends ${maxBl}, state is later` }; continue; }
    const { d, linhas } = serveState(cut, r, idProprio);
    const ls = d.prepare("SELECT MAX(served_at) m FROM brief_log WHERE chunk_id = ?");
    const key = (id) => ls.get(id).m ?? null;
    const pool = brief.fetchFreshCandidates(corpus, GLOBAL_FRESH_PATTERNS,
      { ...cfg, freshMaxAgeDays: cfg.freshGlobalMaxAgeDays }, tRef, d, undefined);
    const ks = pool.map((c) => key(c.row.id));
    // run-lengths of identical last_served in pool order = the strata the comparator sees
    const runs = [];
    for (const k of ks) { if (runs.length && runs.at(-1).k === k) runs.at(-1).n++; else runs.push({ k, n: 1 }); }
    const slots = cfg.freshSlots;
    const kBoundary = ks[slots - 1] ?? null;
    const boundaryRun = runs.find((x) => x.k === kBoundary);
    const desigNoPool = pool.filter((c) => designados.has(c.row.id));
    const desigNaFronteira = pool.filter((c, i) => designados.has(c.row.id) && ks[i] === kBoundary);
    const hist = {};
    for (const x of runs) hist[x.n] = (hist[x.n] ?? 0) + 1;
    const enter = (r.would_enter ?? []).map((id) => ({ id, last_served: key(id), designado: designados.has(id) }));
    const leave = (r.would_leave ?? []).map((id) => ({ id, last_served: key(id) }));
    const leaveKeys = new Set(leave.map((x) => x.last_served));
    porCorte[cut] = {
      serve_state_linhas: linhas,
      pool: pool.length,
      nunca_servidos: ks.filter((k) => k === null).length,
      estratos: runs.length,
      estratos_singleton: runs.filter((x) => x.n === 1).length,
      histograma_tamanho_estrato: hist,
      fresh_slots: slots,
      topo_ids: pool.slice(0, slots).map((c) => c.row.id),
      topo_last_served: ks.slice(0, slots),
      topo_contido_no_controle_producao: pool.slice(0, slots).every((c) => r.ids_controle.includes(c.row.id)),
      estrato_fronteira: { last_served: kBoundary, tamanho: boundaryRun?.n ?? 0 },
      designados_no_pool: desigNoPool.length,
      designados_no_estrato_fronteira: desigNaFronteira.length,
      posicao_primeiro_designado: pool.findIndex((c) => designados.has(c.row.id)),
      producao_entra: enter,
      producao_sai: leave,
      entra_empata_com_sai: enter.length > 0 && enter.every((x) => leaveKeys.has(x.last_served)),
    };
    d.close();
  }
  res.push({ ts: r.ts, agent: r.agent, servido: r.servido, churn_producao: r.churn,
             fresh_added_producao: r.fresh_added, rowid_proprio: idProprio, por_corte: porCorte });
}

const out = {
  procedencia: {
    gerado_em: new Date().toISOString(), corpus: resolve(A.corpus), brief_log: resolve(A["brief-log"]),
    brief_log_max_served_at: maxBl, estados: res.length,
    fonte_brief_ts_sha256: (await import("node:crypto")).createHash("sha256").update(FONTE).digest("hex"),
  },
  detalhe: res,
};
const json = JSON.stringify(out, null, 2);
if (A.out) writeFileSync(resolve(A.out), json + "\n"); else console.log(json);
