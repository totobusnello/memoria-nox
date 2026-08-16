/**
 * link_feasibility.mjs — o termo `linked` do §2 tem substrato?
 *
 * PRE-REGISTERED STATUS: exploratory pre-treatment measurement. Touches no
 * locked number, tests no hypothesis. READ-ONLY on the production DB.
 *
 * §2 defines the treatment as `W_OUTCOME × severity` applied to "chunks linked
 * to adjudicated-failure episodes". "Linked" is never operationally defined
 * (see PREREG-DRAFT.md §9-4). This script measures whether any construction of
 * that link can work, by answering three questions with numbers:
 *
 *   1. Is there a JOIN KEY between episodes and chunks today?
 *   2. If a failure memory were WRITTEN from an episode, would it reach the
 *      brief through the main slots?
 *   3. Would it reach the brief through the coverage (`freshSlots = 2`) slots,
 *      and does the locked dose `w ∈ {0.5, 1.0, 2.0}` decide the outcome there?
 *
 * Run on the VPS, from the nox-mem directory:
 *   set -a; source /root/.openclaw/.env; set +a
 *   node link_feasibility.mjs
 */

import Database from "better-sqlite3";
import { readdirSync, readFileSync } from "node:fs";
import { calculateSalience } from "./dist/salience.js";

const DB = process.env.NOX_DB_PATH ?? "./nox-mem.db";
const EPISODES = process.env.NOX_EPISODES_DIR ?? "/root/paper2-episodes";
const CANDIDATE_POOL = 500; // brief.ts:94
const FRESH_CANDIDATE_POOL = 400; // brief.ts:101
const FRESH_SLOTS = 2; // D3 default
const N = 10; // brief slots
const DELTA_CUT = 0.043; // frozen at the 2026-07-29 lock

// Severity mapping fixed by §4.1. Shares are the 3,812 unique
// (episode, panelist) `failure` verdicts of the frozen pilot corpus.
const SEVERITY = { S1: 0.25, S2: 0.5, S3: 0.75, S4: 1.0 };
const SHARE = { S1: 0.6973, S2: 0.2962, S3: 0.0058, S4: 0.0008 };

const db = new Database(DB, { readonly: true, fileMustExist: true });
const now = Date.now();
const iso = new Date(now).toISOString();

// ── 1. Is there a join key? ──────────────────────────────────────────────────
const epSessions = new Set();
for (const f of readdirSync(EPISODES).filter((f) => f.endsWith(".jsonl"))) {
  for (const ln of readFileSync(`${EPISODES}/${f}`, "utf8").split("\n")) {
    if (!ln.trim()) continue;
    try {
      const s = JSON.parse(ln).session;
      if (s) epSessions.add(s);
    } catch {
      /* skip malformed */
    }
  }
}
const UUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/g;
const chunkUuids = new Set(
  db
    .prepare(`SELECT DISTINCT source_file FROM chunks WHERE source_type='session'`)
    .all()
    .flatMap((r) => r.source_file.match(UUID) ?? []),
);
const overlap = [...epSessions].filter((s) => chunkUuids.has(s)).length;
const fromArchive = db
  .prepare(
    `SELECT COUNT(*) n FROM chunks
      WHERE source_file LIKE '%action-archive%' OR source_file LIKE '%.claude/projects%'`,
  )
  .get().n;
const withEpisodeMeta = db
  .prepare(`SELECT COUNT(*) n FROM chunks WHERE metadata LIKE '%episode%'`)
  .get().n;

console.log("1. JOIN KEY");
console.log(`   sessões distintas nos episódios      ${epSessions.size}`);
console.log(`   UUIDs em source_file de chunks       ${chunkUuids.size}`);
console.log(`   INTERSECTION                         ${overlap}`);
console.log(`   chunks originating in action-archive ${fromArchive}`);
console.log(`   chunks with episode in metadata      ${withEpisodeMeta}`);
console.log(
  `   => ${overlap + fromArchive + withEpisodeMeta === 0 ? "NO join key EXISTS. The link must be CONSTRUCTED." : "there is substrate -- investigate"}`,
);

// ── 2 & 3. Would a written failure memory reach the brief? ───────────────────
const COLS = `id,source_file,chunk_text,chunk_type,source_type,tier,pain,importance,
              retention_days,source_date,created_at,updated_at,last_accessed_at,access_count`;

const mainPool = db
  .prepare(
    `SELECT ${COLS} FROM chunks
      ORDER BY (0.55*COALESCE(importance,0.5) + 0.10*COALESCE(pain,0.2)
              + CASE WHEN COALESCE(access_count,0)>0 THEN 0.1 ELSE 0 END) DESC,
               updated_at DESC
      LIMIT ${CANDIDATE_POOL}`,
  )
  .all()
  .map((r) => calculateSalience(r, now))
  .sort((a, b) => b - a);

// Fresh pool: brief.ts orders never-served first, salience as tiebreak.
const freshPool = db
  .prepare(
    `SELECT ${COLS.replace(/(\w+)/g, "c.$1")},
            (SELECT MAX(bl.served_at) FROM brief_log bl WHERE bl.chunk_id = c.id) AS ls
       FROM chunks c ORDER BY ls ASC, c.updated_at DESC LIMIT ${FRESH_CANDIDATE_POOL}`,
  )
  .all()
  .filter((r) => !r.ls)
  .map((r) => calculateSalience(r, now))
  .sort((a, b) => b - a);

const cutMain = mainPool[N - 1];
const cutFresh = freshPool[FRESH_SLOTS - 1];

console.log("\n2/3. ALCANCE DE UMA MEMÓRIA DE FALHA RECÉM-ESCRITA");
console.log(`   corte do slot ${N} principal   ${cutMain.toFixed(4)}`);
console.log(`   corte do fresh slot ${FRESH_SLOTS}       ${cutFresh.toFixed(4)}`);
console.log(
  `\n   chunk_type='lesson' => importance 0.90 (IMPORTANCE_BY_TYPE), access_count=0, pain=severidade`,
);
console.log(
  "   sev  share    base      w=0.5     w=1.0     w=2.0   | entra nos fresh slots?   w mínimo",
);

for (const [lvl, sev] of Object.entries(SEVERITY)) {
  const chunk = {
    chunk_type: "lesson",
    source_type: "lesson",
    tier: null,
    pain: sev,
    importance: null, // let the per-type table decide -- that is what the ingest does
    retention_days: 180,
    source_date: iso,
    created_at: iso,
    updated_at: iso,
    last_accessed_at: null,
    access_count: 0,
  };
  const base = calculateSalience(chunk, now);
  const doses = [0.5, 1.0, 2.0].map((w) => base + w * DELTA_CUT * sev);
  const gap = cutFresh - base;
  const wMin = gap <= 0 ? 0 : gap / (DELTA_CUT * sev);
  console.log(
    `   ${lvl}   ${(SHARE[lvl] * 100).toFixed(2).padStart(5)}%  ${base.toFixed(4)}   ` +
      doses.map((d) => d.toFixed(4)).join("    ") +
      `  | ${doses.map((d) => (d >= cutFresh ? "SIM" : "não")).join(" ")}` +
      `   ${wMin === 0 ? "já entra" : wMin.toFixed(1)}`,
  );
}
console.log(
  `\n   Nenhuma dose alcança o slot principal: o melhor caso fica ${(cutMain - calculateSalience({ chunk_type: "lesson", pain: 1, importance: null, retention_days: 180, source_date: iso, created_at: iso, updated_at: iso, access_count: 0 }, now) - 2 * DELTA_CUT).toFixed(4)} abaixo do corte.`,
);
db.close();
