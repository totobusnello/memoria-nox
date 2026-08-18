#!/usr/bin/env python3
"""Python port of the production serving path, VALIDATED against code-generated truth.

WHY THIS FILE EXISTS.  Every reach number in the registration was derived from
`reachable_share.py`, whose `w_min` treats `CUT_FRESH = 0.7342` as a threshold the
serving code applies.  Reading `src/api/brief.ts` on 2026-08-18 showed production
applies NO threshold: `pick` phase 3 takes the first `freshSlots` entries of a
list ordered by `coverageCompare` (never-served first, full salience as tiebreak).
Entry is a RANK, and the rank is against whatever else is in the pool.

So this file ports the real formula and asserts it against
`FIXTURE-SERVING-2026-08-18.json`, which was produced by driving
`dist/api/brief.js` + `dist/salience.js` themselves.  If the port drifts from the
code, `--check` fails.  That is the property `reachable_share.py` never had.

WHAT IS PORTED EXACTLY (and asserted):
    resolveRetentionDays / recencyComponent / importanceComponent /
    painComponent / accessCountComponent / clamp01 / calculateSalience

WHAT IS MODELLED, NOT PORTED, because it does not exist in the code yet:
    the outcome boost.  §2 line 495 registers `W_OUTCOME = w * Delta_cut * severity`
    -- the SEVERITY FACTOR IS PART OF THE REGISTERED FORMULA.  Two consequences
    are declared rather than assumed silently:

      (a) WHERE THE BOOST ENTERS RELATIVE TO clamp01 IS NOT REGISTERED.  This file
          applies it pre-clamp, which is the reading that keeps the dose monotone.
          Post-clamp, doses whose raw score exceeds 1.0 tie at exactly 1.0.
      (b) The boost does not touch the SQL proxy (`0.55*importance + 0.10*pain +
          0.1*[access>0]`), which decides the LIMIT 400 pre-cut.  Verified by
          reading the query: the proxy reads columns, and the boost is applied at
          brief-composition time (§2 item 2).

LIMITS OF THE FIXTURE THIS VALIDATES AGAINST, stated because they bound every
conclusion drawn from it:
  - It was generated with `scope="global"` and no agent, so `scopePatterns`
    returns an EMPTY pattern list and the "agent" sub-pool is not restricted by
    `source_file` at all.  Real briefs are scoped per agent.  The competitor set
    is therefore optimistic about how much of the pool our chunk competes with,
    and pessimistic about the agent sub-pool being narrow.
  - The competitor set is one epoch of the study's own projected inflow (396
    episodes at the registered severity shares).  The write path does not exist,
    so that inflow is a projection.
  - It is a single brief with a static pool: it measures INSTANTANEOUS rank, not
    the daily drain (672 briefs/day against 396 writes/day).  Both matter and they
    answer different questions; the estimand asks about a specific brief.
"""

from __future__ import annotations
import argparse, json, math, sys
from pathlib import Path

# ── constants, from src/salience.ts ──────────────────────────────────────────
W_IMPORTANCE, W_RECENCY, W_PAIN, W_ACCESS = 0.55, 0.15, 0.10, 0.20
RETENTION_BY_TYPE = {"feedback": 0, "person": 0, "lesson": 180, "decision": 365,
                     "project": 365, "team": 120, "daily": 90, "pending": 30,
                     "graph_node": 60}
FALLBACK_RETENTION = 90
IMPORTANCE_BY_TYPE = {"decision": 0.95, "lesson": 0.90, "person": 0.85,
                      "project": 0.80, "pending": 0.75, "feedback": 0.70,
                      "team": 0.60, "daily": 0.50, "graph_node": 0.45}
FALLBACK_IMPORTANCE = 0.40

# ── registered ───────────────────────────────────────────────────────────────
DELTA_CUT = 0.043
BAND = (2.0, 4.0, 7.5)
SEV = {"S1": 0.25, "S2": 0.50, "S3": 0.75, "S4": 1.00}
SHARE = {"S1": 0.6973, "S2": 0.2962, "S3": 0.0058, "S4": 0.0008}


def clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)


def resolve_retention_days(retention_days, chunk_type) -> float:
    if retention_days is not None and math.isfinite(retention_days):
        return float(retention_days)
    if retention_days is None:
        return 0.0
    if chunk_type in RETENTION_BY_TYPE:
        return float(RETENTION_BY_TYPE[chunk_type])
    return float(FALLBACK_RETENTION)


# ⚠️ PRODUCTION TIMEZONE DEFECT, measured 2026-08-18. `datetime('now')` in SQLite
# writes NAIVE UTC ("2026-08-17 12:00:00"). `brief.ts` has `parseDbDateMs()`,
# which appends "Z" before parsing and is therefore correct -- but
# `salience.ts:recencyComponent` calls `Date.parse(refStr)` RAW. Node parses a
# space-separated naive string as LOCAL time, and the VPS runs America/Sao_Paulo
# (UTC-3), so every chunk's reference instant is read 3 h LATER than it is, and
# every age is 3 h SMALLER. Recency, and hence salience, is systematically
# inflated.
#
# MAGNITUDE: 3 h against a 180-day retention inflates recency by ~0.048%, i.e.
# ~7.2e-5 on salience -- 0.17% of ONE dose unit (Delta_cut = 0.043). It cannot
# flip a ranking except in an exact tie. It is declared rather than fixed:
# changing it would alter serving behaviour, and this is the wrong week to change
# serving behaviour. The port reproduces the CODE, defect included, because the
# code is what will actually run the study.
TZ_OFFSET_HOURS = -3.0  # America/Sao_Paulo, measured on the VPS 2026-08-18


def recency_component(age_days: float, retention_days: float,
                      tz_offset_hours: float = TZ_OFFSET_HOURS) -> float:
    """NOTE: production reads `last_accessed_at ?? source_date`. Serving a brief
    is read-only on `chunks` (brief.ts), so a brief-served chunk keeps
    last_accessed_at NULL and ages by source_date. Only search.ts bumps it."""
    if retention_days <= 0:
        return 1.0
    # the defect above: the naive UTC string is read as local, so the age shrinks
    # by the offset's magnitude.
    efetiva = age_days + tz_offset_hours / 24.0
    if efetiva <= 0:
        return 1.0
    return 2.0 ** (-efetiva / retention_days)


def importance_component(chunk_type, explicit) -> float:
    if explicit is not None and math.isfinite(explicit):
        return clamp01(explicit)
    if chunk_type in IMPORTANCE_BY_TYPE:
        return IMPORTANCE_BY_TYPE[chunk_type]
    return FALLBACK_IMPORTANCE


def pain_component(pain) -> float:
    if pain is None or not math.isfinite(pain):
        return 0.2
    return clamp01(pain)


def access_component(access_count) -> float:
    if access_count is None or not math.isfinite(access_count) or access_count <= 0:
        return 0.0
    return clamp01(math.log1p(access_count) / math.log(1000))


def salience(sev: float, age_days: float, *, chunk_type="lesson", importance=0.90,
             access_count=0, retention_days=180, w: float = 0.0) -> float:
    """calculateSalience + the registered boost `w * Delta_cut * severity`.

    The boost is applied PRE-clamp; see the docstring, (a). w = 0 reproduces the
    code exactly and is what `--check` asserts."""
    ret = resolve_retention_days(retention_days, chunk_type)
    raw = (W_IMPORTANCE * importance_component(chunk_type, importance)
           + W_RECENCY * recency_component(age_days, ret)
           + W_PAIN * pain_component(sev)
           + W_ACCESS * access_component(access_count)
           + w * DELTA_CUT * sev)
    return clamp01(raw)


def w_min_para_superar(sev: float, age_days: float, alvo: float) -> float:
    """Dose needed for a chunk to outrank a competitor sitting at `alvo`.

    This replaces `reachable_share.w_min`, which compared against CUT_FRESH as if
    it were a threshold. `alvo` here is the salience of the incumbent our chunk
    has to pass, which is a property of the POOL, not a constant of the design."""
    gap = alvo - salience(sev, age_days)
    if gap <= 0:
        return 0.0
    return gap / (DELTA_CUT * sev)


# ── validation against the code-generated fixture ────────────────────────────
def check(fixture: Path) -> int:
    d = json.loads(fixture.read_text())
    falhas = []
    n = 0
    for cenario, casos in d["cenarios"].items():
        for caso, r in casos.items():
            if "salience" not in r:
                continue
            sev_key, age = caso.split("@")
            age_days = float(age.rstrip("d"))
            mine = salience(SEV[sev_key], age_days)
            n += 1
            if abs(mine - r["salience"]) > 1e-9:
                falhas.append(f"{cenario}/{caso}: porto {mine:.9f} != codigo {r['salience']:.9f}")
    if falhas:
        print(f"FALHA — {len(falhas)} de {n} divergem do codigo:")
        for f in falhas[:20]:
            print("  ", f)
        return 1
    print(f"ok — {n} valores de salience reproduzem o codigo bit a bit")
    return 0


def alcance(fixture: Path) -> dict:
    """Reach per dose against the incumbent the fixture actually measured."""
    d = json.loads(fixture.read_text())
    est = d["cenarios"]["pool_do_estudo"]
    # incumbent = the top never-served competitor, which the fixture shows is the
    # S4-at-age-0 cohort of the study's own inflow.
    alvo = est["S4@0d"]["salience"]
    out = {"incumbente_salience": alvo, "por_severidade": {}, "alcance_por_dose": {}}
    for k, sev in SEV.items():
        w = w_min_para_superar(sev, 0.0, alvo)
        out["por_severidade"][k] = {
            "base": round(salience(sev, 0.0), 6),
            "w_min": round(w, 4),
            "doses_que_alcancam": [x for x in BAND if x >= w],
            "share": SHARE[k],
        }
    for x in BAND:
        s = sum(SHARE[k] for k, v in out["por_severidade"].items() if x >= v["w_min"])
        out["alcance_por_dose"][f"w={x}"] = round(s, 6)
    out["publicado_v1_11"] = {"w=2.0": 0.5827, "w=4.0": 0.7858, "w=7.5": 1.0}
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fixture", default="FIXTURE-SERVING-2026-08-18.json")
    ap.add_argument("--check", action="store_true", help="assert the port against the code")
    ap.add_argument("--alcance", action="store_true", help="reach per dose under the real pool")
    a = ap.parse_args()
    f = Path(a.fixture)
    if a.check:
        sys.exit(check(f))
    if a.alcance:
        print(json.dumps(alcance(f), indent=2))
        sys.exit(0)
    sys.exit(check(f))
