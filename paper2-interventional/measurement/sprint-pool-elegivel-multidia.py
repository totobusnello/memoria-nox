#!/usr/bin/env python3
"""
sprint-pool-elegivel-multidia.py — re-measure the coverage-channel eligible pool
(§4.3.1) for SEVERAL days from a preserved trial DB, after the epochs were pruned.

Why this exists: the manuscript says the pool was exhausted "on 26, 27, 28 and 29/08",
but `POOL-ELEGIVEL-2026-08-28.json` only covers 28/08. The other three days were
measured with `pool-elegivel.py` and not preserved. This script reproduces the same
predicate on a preserved copy, for every requested day, in two variants:

  * `as_script` — the queries of `pool-elegivel.py` VERBATIM (same predicate, same
    "never served" over the whole brief_log, same `substr(served_at,1,10)` day key).
    On a DB taken AFTER the measured day this variant can differ from what the original
    run saw, because (a) brief_log contains serves after the day and (b) chunks created
    after the day have negative age and pass `age <= 30`.
  * `time_bounded` — the same predicate plus two bounds that make a later DB answer the
    question as of the end of the measured day: chunk date <= reference instant, and
    "never served" counted only over brief_log rows with served_at <= reference instant.

Positive control: running this on a DB whose chunk table is the one that existed on
28/08 must reproduce `POOL-ELEGIVEL-2026-08-28.json` (108 / 0 / 108 / 672 briefs).
If it does not, the DB is not a valid stand-in and the other days must not be reported.

Limits this script CANNOT remove (stated in the output, never silently):
  * `importance`/`pain` are read as they are in the copy, not as they were on the day.
    Cross-DB agreement (same pool ids in DBs frozen on different dates) is the evidence
    that they did not move; it is not proof for the instant itself.
  * The day key is the UTC calendar date prefix of `served_at`, identical to the
    original script.

Usage:
  sprint-pool-elegivel-multidia.py --db COPY.db --label serv0903 \
      --dias 2026-08-26 2026-08-27 2026-08-28 2026-08-29 > out.json

Never point --db at an original: open copies only (WAL/SHM side files).
"""
import argparse
import hashlib
import json
import sqlite3
import sys

# Same constants as measurement/pool-elegivel.py (verbatim from brief.ts / brief-diversity.ts
# as of 2026-08-29).
GLOBAL_FRESH_PATTERNS = ["memory/entities/%", "memory/lessons.md"]
FRESH_GLOBAL_MAX_AGE_DAYS = 30
FRESH_MIN_IMP = 0.7
FRESH_MIN_PAIN = 0.7
FRESH_SLOTS = 2
AGENT_FRESH_PATTERN = "sessions/%"
FRESH_MAX_AGE_DAYS = 7
PARTIAL_DAY_BRIEFS = 400  # same threshold as pool-elegivel.py


def ids_hash(ids):
    return hashlib.sha256(",".join(str(i) for i in sorted(ids)).encode()).hexdigest()[:16]


def measure(c, dia):
    ref = f"{dia} 23:59:59"
    pat = " OR ".join(["source_file LIKE ?"] * len(GLOBAL_FRESH_PATTERNS))
    base = (f"julianday(?) - julianday(COALESCE(source_date, created_at)) <= ? "
            f"AND (COALESCE(importance,0) >= ? OR COALESCE(pain,0) >= ?) "
            f"AND ({pat})")
    args = [ref, FRESH_GLOBAL_MAX_AGE_DAYS, FRESH_MIN_IMP, FRESH_MIN_PAIN,
            *GLOBAL_FRESH_PATTERNS]
    bound = "julianday(COALESCE(source_date, created_at)) <= julianday(?)"

    briefs = c.execute(
        "SELECT COUNT(DISTINCT brief_id) FROM brief_log WHERE substr(served_at,1,10)=?",
        (dia,)).fetchone()[0]
    brief_rows = c.execute(
        "SELECT COUNT(*) FROM brief_log WHERE substr(served_at,1,10)=?",
        (dia,)).fetchone()[0]
    first_last = c.execute(
        "SELECT MIN(served_at), MAX(served_at) FROM brief_log WHERE substr(served_at,1,10)=?",
        (dia,)).fetchone()
    corpus = c.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    corpus_asof = c.execute(
        f"SELECT COUNT(*) FROM chunks WHERE {bound}", (ref,)).fetchone()[0]

    out = {"dia": dia, "briefs_no_dia": briefs, "brief_log_rows_no_dia": brief_rows,
           "served_at_first": first_last[0], "served_at_last": first_last[1],
           "dia_parcial": briefs < PARTIAL_DAY_BRIEFS,
           "corpus_in_copy": corpus, "corpus_dated_le_ref": corpus_asof}

    for variant in ("as_script", "time_bounded"):
        w = base + (f" AND {bound}" if variant == "time_bounded" else "")
        a = args + ([ref] if variant == "time_bounded" else [])
        pool_ids = [r[0] for r in c.execute(f"SELECT id FROM chunks WHERE {w}", a)]
        bl_scope = ("SELECT chunk_id FROM brief_log WHERE served_at <= ?"
                    if variant == "time_bounded" else "SELECT chunk_id FROM brief_log")
        bl_args = [ref] if variant == "time_bounded" else []
        nunca = c.execute(
            f"SELECT COUNT(*) FROM chunks WHERE {w} AND id NOT IN ({bl_scope})",
            a + bl_args).fetchone()[0]
        servidos = c.execute(
            f"SELECT COUNT(*) FROM chunks WHERE {w} AND id IN "
            f"(SELECT chunk_id FROM brief_log WHERE substr(served_at,1,10) = ?)",
            a + [dia]).fetchone()[0]
        agent_w = ("julianday(?) - julianday(COALESCE(source_date, created_at)) <= ? "
                   "AND (COALESCE(importance,0) >= ? OR COALESCE(pain,0) >= ?) "
                   "AND source_file LIKE ?")
        agent_a = [ref, FRESH_MAX_AGE_DAYS, FRESH_MIN_IMP, FRESH_MIN_PAIN, AGENT_FRESH_PATTERN]
        if variant == "time_bounded":
            agent_w += f" AND {bound}"
            agent_a += [ref]
        agente = c.execute(f"SELECT COUNT(*) FROM chunks WHERE {agent_w}",
                           agent_a).fetchone()[0]
        pool = len(pool_ids)
        tot = pool + agente
        slots = briefs * FRESH_SLOTS
        out[variant] = {
            "sub_pool_global": pool,
            "sub_pool_por_agente": agente,
            "pool_elegivel": tot,
            "pct_do_corpus": round(100 * tot / corpus, 3) if corpus else None,
            "nunca_servidos_no_pool": nunca,
            "servidos_no_dia": servidos,
            "cobertura_do_pool_no_dia": round(100 * servidos / pool, 1) if pool else None,
            "slots_de_cobertura_no_dia": slots,
            "slots_por_candidato": round(slots / tot, 1) if tot else None,
            "pool_ids_sha16": ids_hash(pool_ids),
            "guard_served_le_pool": servidos <= pool,
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--dias", nargs="+", required=True)
    a = ap.parse_args()
    c = sqlite3.connect(f"file:{a.db}?mode=ro&immutable=1", uri=True)
    meta = {
        "label": a.label,
        "db_copy": a.db,
        "brief_log_range": list(c.execute(
            "SELECT MIN(served_at), MAX(served_at), COUNT(*) FROM brief_log").fetchone()),
        "chunks_max_created_at": c.execute("SELECT MAX(created_at) FROM chunks").fetchone()[0],
        "chunks_max_source_date": c.execute("SELECT MAX(source_date) FROM chunks").fetchone()[0],
        "predicate": {"patterns": GLOBAL_FRESH_PATTERNS,
                      "global_max_age_days": FRESH_GLOBAL_MAX_AGE_DAYS,
                      "agent_pattern": AGENT_FRESH_PATTERN,
                      "agent_max_age_days": FRESH_MAX_AGE_DAYS,
                      "floor": f"importance >= {FRESH_MIN_IMP} OR pain >= {FRESH_MIN_PAIN}",
                      "fresh_slots_per_brief": FRESH_SLOTS},
        "days": [measure(c, d) for d in a.dias],
    }
    rc = 0
    for d in meta["days"]:
        for v in ("as_script", "time_bounded"):
            if not d[v]["guard_served_le_pool"]:
                print(f"GUARD {a.label} {d['dia']} {v}: served > pool — predicate diverged",
                      file=sys.stderr)
                rc = 1
        if d["briefs_no_dia"] == 0:
            print(f"GUARD {a.label} {d['dia']}: no briefs — no measurement", file=sys.stderr)
            rc = 1
    print(json.dumps(meta, indent=2, ensure_ascii=False))
    return rc


if __name__ == "__main__":
    sys.exit(main())
