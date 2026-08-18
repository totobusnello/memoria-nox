#!/usr/bin/env python3
"""Reach of the coverage path against the pool THE STUDY ITSELF CREATES.

WHY THIS FILE EXISTS.  The registered reach numbers (58.27% / 78.58% / 100.00%,
`reachable_share.py`) model entry into a coverage slot as a THRESHOLD: a written
chunk enters iff its boosted salience clears `CUT_FRESH = 0.7342`, the salience
of the second-ranked fresh candidate measured on the historical pool.  Reading
production on 2026-08-18 showed that is not the mechanism, and that the pool is
not that pool.

WHAT PRODUCTION ACTUALLY DOES (`src/api/brief.ts`, read 2026-08-18):

  1. `fetchFreshCandidates` selects eligible rows -- `source_file LIKE` pattern,
     `importance >= 0.7 OR pain >= 0.7`, and age on COALESCE(source_date,
     created_at) within a window (7 d for the agent sub-pool, 30 d for the
     global one) -- ordered `last_served ASC, proxy DESC LIMIT 400`.
  2. The result is re-sorted by `coverageCompare`, which maps never-served to
     -infinity so ALL never-served tie, broken by FULL salience descending.
  3. `pick` phase 3 walks that list and takes the first `freshSlots` entries.
     THERE IS NO THRESHOLD ANYWHERE.  `CUT_FRESH` is a description of what rank
     2 happened to be, not a cut the code applies.
  4. `interleaveFresh(agent, global)` round-robins, so with freshSlots = 2 the
     picks are rank 1 of the agent sub-pool and rank 1 of the global sub-pool.
     The registration locks the written chunk under `memory/entities/`, so it
     competes for exactly ONE slot per brief, in the global sub-pool.

So entry is decided by RANK, not by a cut.  And rank only matters if demand for
the slot is scarcer than supply of never-served chunks.  It is not:

  - measured 2026-08-18: 672 briefs/day (6 720 brief_log rows at 10 chunks each)
  - registered: ~396 adjudicated-failure episodes per 24 h epoch, one chunk each,
    written in BOTH arms

Each brief consumes the current rank-1 never-served chunk, which then carries a
`brief_log` row and is no longer never-served.  So up to 672 DISTINCT
never-served chunks are consumed per day against 396 created.  The coverage path
is SUPPLY-limited, not selection-limited.

WHAT THAT IMPLIES, and it is the point of this file: the dose cannot change
WHETHER a written chunk reaches a brief -- only the hour of the day at which it
does.  The registered Opportunity requires the chunk to have been written at
least one epoch length before the epoch in which the action occurs, so the hour
within the writing day is outside the estimand.

This script computes the numbers rather than asserting them, and prints the one
inequality the conclusion rests on so a reader can attack it directly.

LIMITS, stated because they are real:
  - The study's write path does not exist yet, so the 396/epoch inflow is the
    registered projection, not a measurement.  Every conclusion here is
    conditional on it.
  - 672 briefs/day is measured over 2026-08-09..17 and is treated as constant.
  - It models the GLOBAL sub-pool only.  A chunk written under a session scope
    would compete in the agent sub-pool, which is scoped and much smaller; that
    is a different design and is not what is registered.
  - It assumes one `brief_log` row per served chunk per brief, which is what the
    schema does, and that serving is what removes a chunk from the never-served
    class, which is what `coverageCompare` reads.
"""

from __future__ import annotations
import argparse, json, math

# ---- measured on production 2026-08-18 --------------------------------------
BRIEFS_PER_DAY = 672          # 6 720 brief_log rows / 10 chunks per brief
GLOBAL_SLOTS_PER_BRIEF = 1    # interleaveFresh gives the global sub-pool one of freshSlots=2
ENTITY_ELIGIBLE_TODAY = 0     # rows passing the global gate + 30 d window, 2026-08-18
ENTITY_NEWEST_AGE_DAYS = 38.9 # newest memory/entities row that passes the imp/pain gate
SQL_CANDIDATE_CAP = 400       # FRESH_CANDIDATE_POOL

# ---- registered -------------------------------------------------------------
EPISODES_PER_EPOCH = 396      # PREREG-DRAFT.md, adjudication-volume subsection
GLOBAL_WINDOW_DAYS = 30       # freshGlobalMaxAgeDays
IMPORTANCE_LESSON = 0.90
RETENTION_LESSON = 180
DELTA_CUT = 0.043
BAND = (2.0, 4.0, 7.5)
SEVERITY = {"S1": 0.25, "S2": 0.50, "S3": 0.75, "S4": 1.00}
SHARE = {"S1": 0.6973, "S2": 0.2962, "S3": 0.0058, "S4": 0.0008}
W_IMP, W_REC, W_PAIN, W_ACC = 0.55, 0.15, 0.10, 0.20


def salience(sev: float, age_days: float, w: float = 0.0) -> float:
    """Salience v2 (additive), access_count = 0, plus the outcome boost."""
    rec = 2.0 ** (-age_days / RETENTION_LESSON)
    return W_IMP * IMPORTANCE_LESSON + W_REC * rec + W_PAIN * sev + w * DELTA_CUT


def proxy(sev: float) -> float:
    """The cheap proxy the SQL ORDER BY uses. access_count = 0 for never-served."""
    return 0.55 * IMPORTANCE_LESSON + 0.10 * sev


def report() -> dict:
    slots = BRIEFS_PER_DAY * GLOBAL_SLOTS_PER_BRIEF
    inflow = EPISODES_PER_EPOCH
    supply_limited = slots > inflow

    # never-served stock at any instant, if every chunk is consumed the day it
    # is written: bounded by one day's inflow.
    stock = min(inflow, slots)
    cap_binds = stock > SQL_CANDIDATE_CAP

    # composition of one day's inflow by severity
    per_day = {k: EPISODES_PER_EPOCH * SHARE[k] for k in SHARE}

    # rank-1 competition: who wins the slot on a given day, per arm
    def winner(w_by_sev):
        best, who = -1.0, None
        for k, sev in SEVERITY.items():
            if per_day[k] < 1:      # fewer than one such chunk per day
                continue
            s = salience(sev, 0.0, w_by_sev.get(k, 0.0))
            if s > best:
                best, who = s, k
        return who, best

    ctrl_who, ctrl_s = winner({})
    doses = {}
    for w in BAND:
        # worst case for dose-dependence: the boost is applied to the designated
        # chunk, and the designation rule picks the easiest to reach, so compare
        # a boosted S1 against an unboosted S4 -- the strongest competitor that
        # occurs at least once a day.
        s1_boosted = salience(SEVERITY["S1"], 0.0, w)
        s4_plain = salience(SEVERITY["S4"], 0.0, 0.0)
        doses[f"w={w}"] = {
            "S1_boosted": round(s1_boosted, 6),
            "S4_unboosted": round(s4_plain, 6),
            "boosted_S1_outranks_plain_S4": s1_boosted > s4_plain,
        }

    return {
        "supply_vs_demand": {
            "global_slots_per_day": slots,
            "chunks_written_per_day": inflow,
            "supply_limited": supply_limited,
            "ratio_slots_to_inflow": round(slots / inflow, 3),
            "conclusion": (
                "every written chunk is served the day it is written, so the dose "
                "cannot change WHETHER it reaches a brief"
                if supply_limited else
                "demand exceeds supply -- rank matters and the dose can gate entry"
            ),
        },
        "never_served_stock": {
            "instantaneous_stock": round(stock, 1),
            "sql_candidate_cap": SQL_CANDIDATE_CAP,
            "cap_binds": cap_binds,
            "note": "if the cap does not bind, no chunk is crowded out of the candidate set",
        },
        "pool_today": {
            "eligible_global_rows": ENTITY_ELIGIBLE_TODAY,
            "newest_gate_passing_age_days": ENTITY_NEWEST_AGE_DAYS,
            "window_days": GLOBAL_WINDOW_DAYS,
            "note": "the pool the registration locks the chunk into is EMPTY pre-study; "
                    "it is populated by the study's own write path, not by the historical store",
        },
        "daily_inflow_by_severity": {k: round(v, 2) for k, v in per_day.items()},
        "rank1_control": {"winner": ctrl_who, "salience": round(ctrl_s, 6)},
        "rank1_by_dose": doses,
        "cut_fresh_status": (
            "NOT APPLICABLE: production applies no threshold; CUT_FRESH described "
            "rank 2 of a historical pool that the study replaces"
        ),
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    r = report()
    print(json.dumps(r, indent=2))
