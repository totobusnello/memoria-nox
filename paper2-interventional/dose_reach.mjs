/**
 * dose_reach.mjs — quanto do brief a dose TRAVADA consegue mover?
 *
 * PRE-REGISTERED STATUS: exploratory pre-treatment measurement. Does not touch
 * any locked number and does not test H1-H3. It answers one question that the
 * registration currently leaves open (§3, "the ceiling argument cuts both ways"):
 *
 *   the 2026-07-26 measurement covered W_OUTCOME in {0.10, 0.15, 0.20};
 *   the 2026-07-29 lock re-expressed the dose as `w * Delta_cut` with
 *   Delta_cut = 0.043 and w in {0.5, 1.0, 2.0}, i.e. W_OUTCOME in
 *   {0.0215, 0.043, 0.086}.
 *
 * EVERY LOCKED DOSE IS BELOW THE LOWEST VALUE EVER MEASURED. This script
 * measures reach at the doses that will actually run.
 *
 * ────────────────────────────────────────────────────────────────────────────
 * ⚠️ SUPERSEDED BAND — read this before reading the numbers below.
 *
 * The band `w ∈ {0.5, 1.0, 2.0}` written throughout this file, and the label
 * `(LOCKED)` on those three doses, were true from 2026-07-29 to 2026-08-16.
 * They are NOT the registered band any more. §2 of PREREG-DRAFT.md replaced it
 * with `w ∈ {2.0, 4.0, 7.5}` on 2026-08-16, because measurement showed that
 * `w = 0.5` and `w = 1.0` reach EXACTLY ZERO opportunities — two of the three
 * arms were structurally inert.
 *
 * The band is deliberately NOT updated here. This file is the instrument that
 * produced `DOSE-REACH-2026-08-15.json`, which dated documents already cite;
 * changing the doses would make the script disagree with its own published
 * output. Same reasoning as OUTPUT-KEYS.md gives for not renaming the JSON
 * keys: a glossary is cheap, a divergence between artifact and document is the
 * defect this study exists to avoid.
 *
 * To measure the CURRENT band, edit DOSES below — which is also how the
 * candidate doses `w ∈ {2.0, 6.0, 8.0}` reported in
 * `REACHABILITY-2026-08-16.md` §7-bis were produced. That run's raw output is
 * deposited as `DISPLACEMENT-2026-08-16.txt`; this script takes no dose flag.
 * ────────────────────────────────────────────────────────────────────────────
 *
 * READ-ONLY. Opens the production DB read-only, runs the same candidate-pool
 * query as `src/api/brief.ts::fetchRankedPool`, re-ranks with the real
 * `calculateSalience`, and reports displacement reach. It writes nothing.
 *
 * Usage (runs against a live nox-mem store; it writes nothing):
 *   NOX_SALIENCE_MODULE=<path to dist/salience.js> \
 *   NOX_DB_PATH=<path to nox-mem.db> node dose_reach.mjs [--n 10] [--json]
 *
 * Both paths are required and neither is defaulted to a host path: this script
 * is deposited publicly and reads a production store, so the location of that
 * store is the operator's to supply, not this file's to publish.
 */

import Database from "better-sqlite3";
const SALIENCE_MODULE = process.env.NOX_SALIENCE_MODULE;
if (!SALIENCE_MODULE) {
  console.error("NOX_SALIENCE_MODULE is required: path to the nox-mem build's dist/salience.js");
  process.exit(2);
}
const { calculateSalience } = await import(SALIENCE_MODULE);

const CANDIDATE_POOL = 500; // brief.ts:94 — do not change, this mirrors production
const DB = process.env.NOX_DB_PATH;
if (!DB) {
  console.error("NOX_DB_PATH is required: path to nox-mem.db (read-only)");
  process.exit(2);
}

const argv = process.argv.slice(2);
const N = Number(argv[argv.indexOf("--n") + 1]) || 10; // brief slots
const asJson = argv.includes("--json");

// Severity mapping is FIXED by the registration (§4.1): S0..S4 -> 0 .. 1.0.
//
// The two `emp_*` entries are NOT levels — they are the severity actually
// observed in the 3,812 unique (episode, panelist) `failure` verdicts of the
// frozen pilot corpus: S1 69.73% / S2 29.62% / S3 0.58% / S4 0.08%, giving
// median 0.25 and mean 0.3275. The 2026-07-26 measurement reported only the
// severity = 1.0 ceiling, which the corpus reaches in 3 verdicts out of 3,812.
const SEVERITY = {
  S1: 0.25,
  S2: 0.5,
  S3: 0.75,
  S4: 1.0,
  "emp_median(S1)": 0.25,
  emp_mean: 0.3275,
};

// The doses. `historical` reproduce the 2026-07-26 numbers so the two
// measurements can be compared on one scale.
//
// ⚠️ The `(LOCKED)` labels and the `locked: true` flag below are FROZEN AT THE
// 2026-07-29 STATE and are wrong as a description of the current registration:
// the band became `w ∈ {2.0, 4.0, 7.5}` on 2026-08-16. They are kept verbatim
// because this file must keep producing `DOSE-REACH-2026-08-15.json` byte for
// byte. Read `locked` as "locked when this ran", never as "locked now"; §2 of
// PREREG-DRAFT.md is the only authority on the current band.
const DELTA_CUT = 0.043; // frozen pre-treatment at the 2026-07-29 lock
const DOSES = [
  { label: "w=0.5  (LOCKED)", w: 0.5, W: 0.5 * DELTA_CUT, locked: true },
  { label: "w=1.0  (LOCKED)", w: 1.0, W: 1.0 * DELTA_CUT, locked: true },
  { label: "w=2.0  (LOCKED)", w: 2.0, W: 2.0 * DELTA_CUT, locked: true },
  { label: "W=0.10 (historical)", w: null, W: 0.1, locked: false },
  { label: "W=0.15 (historical)", w: null, W: 0.15, locked: false },
  { label: "W=0.20 (historical)", w: null, W: 0.2, locked: false },
];

const db = new Database(DB, { readonly: true, fileMustExist: true });
const nowMs = Date.now();

const rows = db
  .prepare(
    `SELECT id, source_file, chunk_text, chunk_type, source_type, tier,
            pain, importance, retention_days, source_date, created_at,
            updated_at, last_accessed_at, access_count
       FROM chunks
      ORDER BY (0.55 * COALESCE(importance, 0.5)
              + 0.10 * COALESCE(pain, 0.2)
              + CASE WHEN COALESCE(access_count, 0) > 0 THEN 0.1 ELSE 0 END) DESC,
               updated_at DESC
      LIMIT ${CANDIDATE_POOL}`,
  )
  .all();

const pool = rows
  .map((r) => ({ id: r.id, salience: calculateSalience(r, nowMs) }))
  .sort((a, b) => b.salience - a.salience);

const top = pool.slice(0, N);
const cut = top[N - 1].salience; // salience of the last incumbent slot
const spread = top[0].salience - cut; // this is what Delta_cut measures
const gapLast = top[N - 2].salience - cut; // rank N-1 -> N gap

/**
 * Reach, at a given dose `W` and severity `sev`:
 *  - `reaches`: how many chunks BELOW the cut would clear it if boosted
 *  - `displaceable`: how many of the N incumbents sit within the boost of the
 *    cut, i.e. could be pushed out by a boosted challenger
 * The two are different questions and the 2026-07-26 note reported both.
 */
function reach(W, sev) {
  const boost = W * sev;
  const below = pool.slice(N);
  const reaches = below.filter((c) => c.salience + boost >= cut).length;
  const displaceable = top.filter((c) => c.salience - cut <= boost).length;
  return { boost, reaches, displaceable };
}

const out = {
  db: "<supplied via NOX_DB_PATH>",
  measured_at: new Date(nowMs).toISOString(),
  candidate_pool: CANDIDATE_POOL,
  brief_slots: N,
  pool_span: { max: pool[0].salience, min: pool[pool.length - 1].salience },
  cut,
  top_n_spread: spread,
  delta_cut_locked: DELTA_CUT,
  delta_cut_drift: spread - DELTA_CUT,
  gap_rank_n_minus_1_to_n: gapLast,
  by_dose: {},
};

for (const d of DOSES) {
  out.by_dose[d.label] = {
    W_OUTCOME: d.W,
    locked: d.locked,
    at_severity: Object.fromEntries(
      Object.entries(SEVERITY).map(([k, v]) => [k, reach(d.W, v)]),
    ),
  };
}

if (asJson) {
  console.log(JSON.stringify(out, null, 2));
} else {
  console.log(`DB            ${DB}`);
  console.log(`pool          ${CANDIDATE_POOL} rows, ${N} brief slots`);
  console.log(
    `salience      ${pool[0].salience.toFixed(4)} -> ${pool[pool.length - 1].salience.toFixed(4)}`,
  );
  console.log(
    `top-${N} spread  ${spread.toFixed(4)}   (Delta_cut locked at ${DELTA_CUT}, drift ${(spread - DELTA_CUT >= 0 ? "+" : "") + (spread - DELTA_CUT).toFixed(4)})`,
  );
  console.log(`rank ${N - 1}->${N} gap  ${gapLast.toFixed(4)}`);
  console.log("");
  console.log(
    "dose                 W_OUT    sev              boost   reaches  displaceable",
  );
  for (const d of DOSES) {
    for (const [lvl, sev] of Object.entries(SEVERITY)) {
      const r = reach(d.W, sev);
      console.log(
        `${d.label.padEnd(20)} ${d.W.toFixed(4)}  ${lvl.padEnd(15)}  ${r.boost.toFixed(4)}  ${String(r.reaches).padStart(7)}  ${String(r.displaceable).padStart(12)}`,
      );
    }
    console.log("");
  }
}
db.close();
