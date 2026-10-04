#!/usr/bin/env python3
"""
sprint-desagrega-filtros-pool-principal.py — per-filter attrition of the MAIN POOL
(8 of the 10 brief slots), the decomposition §4.3.1 gives the coverage channel and
the main pool never received (open item 6 of MANUSCRIPT.md, from the 2026-09-21
Codex review: "the seven serial filters are not disaggregated").

WHAT IT REIMPLEMENTS (read from the deposited serving code, not from memory):

  serving-brief.ts      fetchRankedPool  :359-398   SQL proxy pre-rank + LIMIT 500 + exact re-rank
                        scopePatterns    :202-215   scope=global -> no path filter; agent -> sessions/<a>/%
                        buildPools       :521-539   agent pool quota ceil(n/2), scope pool quota floor(n/2)
                        pickDedup        :406-485   pinned (phase 0) -> quotas (1) -> backfill (2) -> fresh (3) -> backfill (4)
                        buildBriefDiverse:759-863   current brief -> pinned = current items with pain >= painFloor
                        renderBriefText  :867-881   TOKEN_BUDGET 1200 cut on the text the agent reads
  serving-brief-diversity.ts  DIVERSITY_DEFAULTS :53-63  freshSlots 2, painFloor 0.9
  serving-salience.ts   calculateSalience :246-263  additive v2 (0.55 imp + 0.15 rec + 0.10 pain + 0.20 access)

  Production caller (openclaw-vps/infra/docs/session-priming-f3.md):
      GET /api/brief?scope=global&agent=<p>&format=text&n=10   (no `since`)
  confirmed by the trial serving log: every line has scope "global", 10 ids
  (5 lines with agent=null and 5 ids are reported, not used).

THE SEVEN SERIAL FILTERS of the main pool (scope=global, agent=a, n=10, freshSlots=2):

  F1 scope routing      agent sub-pool sees only sessions/<a>/%; scope sub-pool (global) sees all
  F2 `since` window     updated_at >= now - since        (INACTIVE in production: no `since`)
  F3 proxy LIMIT 500    SQL proxy (0.55 imp + 0.10 pain + 0.1·[access>0]) DESC, updated_at DESC, LIMIT 500 per sub-pool
  F4 exact re-rank      calculateSalience(row, nowMs) re-sorts the 500 (stable)
  F5 dedup              exact id / exact (title|one_liner) key / near-dup containment >= 0.6 vs already picked
  F6 quota + mainTarget agent quota 5, scope quota 5, both capped by mainTarget = n - freshSlots = 8
  F7 pinned floor       items of the no-fresh "current" brief with pain >= 0.9 are picked first

  (F8, post-log: renderBriefText drops lines beyond TOKEN_BUDGET. brief_log records the
   10 ids BEFORE this cut, so it is outside the exposure the paper counts; measured here
   only so the claim "the agent reads what brief_log records" is checked, not assumed.)

WHAT IT MEASURES, per epoch of the trial serving log:

  1. fidelity: reconstructed main slots vs served (ids_controle minus fresh_added).
     Without this nothing below is about production.
  2. series attrition: corpus -> after each filter, as DISTINCT chunks over the epoch.
  3. each filter alone: pass count of that predicate on the whole corpus.
  4. leave-one-out: lift ONE filter, keep the other six, recompute every brief; report
     distinct main-pool chunks per epoch and how many briefs change. This is the test
     that says which filter BINDS — a filter whose removal changes nothing is not what
     limits exposure, however much it "removes" in the series table.
  5. capacity: main slots per epoch vs distinct chunks served there.

COPY-FIRST: --db must be a COPY (a WAL database grows -wal/-shm even when opened
read-only). The script opens it with mode=ro and refuses a path under
/var/backups or /var/lib/nox-mem.

Usage:
  sprint-desagrega-filtros-pool-principal.py --log-only p2-serving.ndjson OUT.json
  sprint-desagrega-filtros-pool-principal.py --db COPY.db --serving p2-serving.ndjson \
      --epochs 2026-08-26,2026-08-27 --label ord0826 --out OUT.json [--tz-offset-hours 0]
"""
import argparse
import bisect
import json
import math
import re
import sqlite3
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta

import numpy as np

# ── constants, verbatim from the deposited serving code ─────────────────────────
DEFAULT_N = 10
CANDIDATE_POOL = 500          # brief.ts:104
FRESH_SLOTS = 2               # brief-diversity.ts:58
PAIN_FLOOR = 0.9              # brief-diversity.ts:57
NEAR_DUP_CONTAINMENT = 0.6    # brief.ts:228
MIN_SIG_TOKENS = 3            # brief.ts:229
ONE_LINER_MAX = 140           # brief.ts:138
TOKEN_BUDGET = 1200           # brief.ts:137

W_IMPORTANCE, W_RECENCY, W_PAIN, W_ACCESS = 0.55, 0.15, 0.10, 0.20   # salience.ts:220-223
IMPORTANCE_BY_TYPE = {"decision": 0.95, "lesson": 0.90, "person": 0.85, "project": 0.80,
                      "pending": 0.75, "feedback": 0.70, "team": 0.60, "daily": 0.50,
                      "graph_node": 0.45}
FALLBACK_IMPORTANCE = 0.40
DEFAULT_RETENTION_BY_TYPE = {"feedback": 0, "person": 0, "lesson": 180, "decision": 365,
                             "project": 365, "team": 120, "daily": 90, "pending": 30,
                             "graph_node": 60}
FALLBACK_RETENTION = 90

COLS_NOTEXT = ("id, source_file, chunk_type, source_type, tier, pain, importance, "
               "retention_days, source_date, created_at, updated_at, last_accessed_at, "
               "access_count")
PROXY_EXPR = ("(0.55 * COALESCE(importance, 0.5) + 0.10 * COALESCE(pain, 0.2) "
              "+ CASE WHEN COALESCE(access_count, 0) > 0 THEN 0.1 ELSE 0 END)")
ORDER = f"ORDER BY {PROXY_EXPR} DESC, updated_at DESC"


def clamp01(x):
    if x is None or not math.isfinite(x):
        return 0.0
    return 0.0 if x < 0 else (1.0 if x > 1 else x)


# ── Date.parse with V8 semantics for the formats present in the corpus ──────────
RE_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
RE_ISO_TZ = re.compile(r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2})(?:\.(\d+))?)?(Z|[+-]\d{2}:\d{2})$")
RE_LOCAL = re.compile(r"^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2})(?:\.(\d+))?)?$")
_PARSE_FAIL = Counter()


def js_date_parse_ms(s, tz_off_h):
    """date-only => UTC; date-time without zone => LOCAL (V8); with zone => as given."""
    if s is None:
        return None
    m = RE_DATE.match(s)
    if m:
        return datetime(int(m[1]), int(m[2]), int(m[3]), tzinfo=timezone.utc).timestamp() * 1000
    m = RE_ISO_TZ.match(s)
    if m:
        frac = int((m[7] or "0")[:3].ljust(3, "0"))
        dt = datetime(int(m[1]), int(m[2]), int(m[3]), int(m[4]), int(m[5]), int(m[6] or 0),
                      tzinfo=timezone.utc)
        ms = dt.timestamp() * 1000 + frac
        z = m[8]
        if z != "Z":
            sign = 1 if z[0] == "+" else -1
            ms -= sign * (int(z[1:3]) * 60 + int(z[4:6])) * 60000
        return ms
    m = RE_LOCAL.match(s)
    if m:
        frac = int((m[7] or "0")[:3].ljust(3, "0"))
        dt = datetime(int(m[1]), int(m[2]), int(m[3]), int(m[4]), int(m[5]), int(m[6] or 0),
                      tzinfo=timezone.utc)
        return dt.timestamp() * 1000 + frac - tz_off_h * 3600_000
    _PARSE_FAIL[s[:12]] += 1
    return float("nan")


def parse_db_date_ms(s):
    """brief.ts:270 parseDbDateMs — space => ISO+Z (UTC), else Date.parse."""
    if " " in s:
        return js_date_parse_ms(s.replace(" ", "T", 1) + "Z", 0)
    return js_date_parse_ms(s, 0)


# ── salience.ts, scalar ─────────────────────────────────────────────────────────
class Row:
    __slots__ = ("id", "source_file", "chunk_type", "pain", "importance", "retention_days",
                 "source_date", "created_at", "updated_at", "last_accessed_at", "access_count",
                 "proxy", "_imp", "_ret", "_refms", "_acc", "_pain")

    def __init__(self, r, tz_off_h):
        (self.id, self.source_file, self.chunk_type, _st, _tier, self.pain, self.importance,
         self.retention_days, self.source_date, self.created_at, self.updated_at,
         self.last_accessed_at, self.access_count) = r
        imp = self.importance
        if imp is not None and isinstance(imp, (int, float)) and math.isfinite(imp):
            self._imp = clamp01(float(imp))
        else:
            self._imp = IMPORTANCE_BY_TYPE.get(self.chunk_type, FALLBACK_IMPORTANCE)
        rd = self.retention_days
        if rd is not None and isinstance(rd, (int, float)) and math.isfinite(rd):
            self._ret = float(rd)
        elif rd is None:
            self._ret = 0.0                      # NULL = explicit never-decay (salience.ts:69-71)
        else:
            self._ret = DEFAULT_RETENTION_BY_TYPE.get(self.chunk_type, FALLBACK_RETENTION)
        p = self.pain
        self._pain = 0.2 if (p is None or not math.isfinite(p)) else clamp01(float(p))
        ac = self.access_count
        self._acc = 0.0 if (ac is None or not math.isfinite(ac) or ac <= 0) else clamp01(math.log1p(ac) / math.log(1000))
        sd = self.source_date if self.source_date is not None else self.created_at
        ref = self.last_accessed_at if self.last_accessed_at is not None else sd
        self._refms = js_date_parse_ms(ref, tz_off_h) if ref is not None else None
        self.proxy = (0.55 * (self.importance if self.importance is not None else 0.5)
                      + 0.10 * (self.pain if self.pain is not None else 0.2)
                      + (0.1 if (self.access_count or 0) > 0 else 0))

    def salience(self, now_ms):
        if self._ret <= 0:
            rec = 1.0
        elif self._refms is None or not math.isfinite(self._refms):
            rec = 0.5
        else:
            age = (now_ms - self._refms) / 86_400_000
            rec = 1.0 if age <= 0 else math.pow(2, -age / self._ret)
        return clamp01(W_IMPORTANCE * self._imp + W_RECENCY * rec + W_PAIN * self._pain
                       + W_ACCESS * self._acc)


# ── one-liner / title / signature (brief.ts:231-279) ────────────────────────────
RE_TAG = re.compile(r"<[^>]*>")
RE_WS = re.compile(r"\s+")
RE_H = re.compile(r"^#{1,6}\s+")
RE_LIST = re.compile(r"^[-*>]\s+")
RE_EXT = re.compile(r"\.(md|txt|json|jsonl)$", re.I)


def u16len(s):
    return len(s.encode("utf-16-le", "surrogatepass")) // 2


def u16slice(s, n):
    return s.encode("utf-16-le", "surrogatepass")[: 2 * n].decode("utf-16-le", "surrogatepass")


def extract_one_liner(text):
    if not text:
        return ""
    for raw in text.split("\n"):
        line = RE_WS.sub(" ", RE_TAG.sub(" ", raw)).strip()
        if not line or line == "---" or line == "```":
            continue
        cleaned = RE_LIST.sub("", RE_H.sub("", line)).replace("**", "").strip()
        if not cleaned:
            continue
        return u16slice(cleaned, ONE_LINER_MAX - 1) + "…" if u16len(cleaned) > ONE_LINER_MAX else cleaned
    return ""


def title_from_source_file(sf):
    if not sf:
        return "(sem origem)"
    base = sf.split("/")[-1] or sf
    return RE_EXT.sub("", base)


def token_signature(title, one_liner):
    s = f"{title} {one_liner}".lower()
    toks, cur = [], []
    for ch in s:
        if ch == "." or unicodedata.category(ch)[0] in ("L", "N"):
            cur.append(ch)
        else:
            if cur:
                toks.append("".join(cur))
                cur = []
    if cur:
        toks.append("".join(cur))
    return frozenset(t for t in toks if u16len(t) >= 4)


def is_near_dup(a, b):
    if len(a) < MIN_SIG_TOKENS or len(b) < MIN_SIG_TOKENS:
        return False
    inter = len(a & b)
    return inter / min(len(a), len(b)) >= NEAR_DUP_CONTAINMENT


class TextCache:
    """chunk_text is fetched lazily — the full corpus text is not needed for the picks."""

    def __init__(self, con):
        self.con, self.d = con, {}

    def meta(self, row):
        m = self.d.get(row.id)
        if m is None:
            t = self.con.execute("SELECT chunk_text FROM chunks WHERE id=?", (row.id,)).fetchone()
            text = t[0] if t else None
            title = title_from_source_file(row.source_file)
            ol = extract_one_liner(text)
            m = (title, ol, f"{title}|{ol}", token_signature(title, ol))
            self.d[row.id] = m
        return m

    def prefetch(self, rows):
        need = [r for r in rows if r.id not in self.d]
        for i in range(0, len(need), 500):
            lote = need[i:i + 500]
            q = ",".join("?" * len(lote))
            texts = dict(self.con.execute(f"SELECT id, chunk_text FROM chunks WHERE id IN ({q})",
                                          [r.id for r in lote]))
            for r in lote:
                title = title_from_source_file(r.source_file)
                ol = extract_one_liner(texts.get(r.id))
                self.d[r.id] = (title, ol, f"{title}|{ol}", token_signature(title, ol))


# ── pickDedup (brief.ts:406-485), instrumented ──────────────────────────────────
def pick_dedup(pools, quotas, n, tc, fresh_slots=0, pinned=frozenset(), dedup=True,
               main_only=True, rej=None):
    """pools: list of lists of (row, score), each already sorted by score DESC (stable).
    Returns list of (row, score, phase). With main_only, phases 3-4 (fresh + backfill)
    are not run: the fresh pool is the coverage channel, out of scope here."""
    picked, seen_ids, seen_keys, seen_sigs = [], set(), set(), []

    def try_pick(row, sc, phase):
        if row.id in seen_ids:
            if rej is not None:
                rej["id"].add(row.id)
            return False
        title, ol, key, sig = tc.meta(row)
        if dedup:
            if key in seen_keys:
                if rej is not None:
                    rej["key"].add(row.id)
                return False
            for s in seen_sigs:
                if is_near_dup(s, sig):
                    if rej is not None:
                        rej["neardup"].add(row.id)
                    return False
        seen_ids.add(row.id)
        seen_keys.add(key)
        seen_sigs.append(sig)
        picked.append((row, sc, phase))
        return True

    main_target = max(0, n - fresh_slots)
    flat = [x for p in pools for x in p]
    if pinned:
        pc = sorted([x for x in flat if x[0].id in pinned], key=lambda x: -x[1])
        for row, sc in pc:
            if len(picked) >= n:
                break
            try_pick(row, sc, 0)
    for i, pool in enumerate(pools):
        got = 0
        for row, sc in pool:
            if got >= quotas[i] or len(picked) >= main_target:
                break
            if try_pick(row, sc, 1):
                got += 1
    if len(picked) < main_target:
        for row, sc in sorted(flat, key=lambda x: -x[1]):
            if len(picked) >= main_target:
                break
            try_pick(row, sc, 2)
    if not main_only and len(picked) < n:
        for row, sc in sorted(flat, key=lambda x: -x[1]):
            if len(picked) >= n:
                break
            try_pick(row, sc, 4)
    return picked


# ── corpus access ───────────────────────────────────────────────────────────────
def fetch(con, patterns, limit, tz):
    where, args = "", []
    if patterns:
        where = "WHERE (" + " OR ".join(["source_file LIKE ? ESCAPE '\\'"] * len(patterns)) + ")"
        args = list(patterns)
    lim = f" LIMIT {limit}" if limit else ""
    rows = con.execute(f"SELECT {COLS_NOTEXT} FROM chunks {where} {ORDER}{lim}", args).fetchall()
    return [Row(r, tz) for r in rows]


def esc_like(s):
    return re.sub(r"([\\%_])", r"\\\1", s)


def ranked(rows, now_ms):
    """map -> calculateSalience -> stable sort DESC (brief.ts:392-397)."""
    sc = [(r, r.salience(now_ms)) for r in rows]
    sc.sort(key=lambda x: -x[1])
    return sc


def by_proxy(rows):
    """F4 lifted: the SQL proxy order itself is the ranking (score = -position)."""
    return [(r, -i) for i, r in enumerate(rows)]


class FullPool:
    """F3 lifted: the whole sub-pool, exact salience, without the LIMIT. Vectorised to
    shortlist, then rescored with the scalar function so the ranking is the same one."""

    def __init__(self, rows):
        self.rows = rows
        self.imp = np.array([r._imp for r in rows])
        self.ret = np.array([r._ret for r in rows])
        self.pain = np.array([r._pain for r in rows])
        self.acc = np.array([r._acc for r in rows])
        self.ref = np.array([np.nan if (r._refms is None) else r._refms for r in rows], dtype=float)

    def top(self, now_ms, k=3000):
        age = (now_ms - self.ref) / 86_400_000
        with np.errstate(invalid="ignore", over="ignore"):
            rec = np.where(self.ret <= 0, 1.0,
                           np.where(np.isnan(self.ref), 0.5,
                                    np.where(age <= 0, 1.0, np.power(2.0, -age / np.where(self.ret > 0, self.ret, 1)))))
        s = np.clip(W_IMPORTANCE * self.imp + W_RECENCY * rec + W_PAIN * self.pain + W_ACCESS * self.acc, 0, 1)
        k = min(k, len(s))
        # k >= len(s): keep every row. (A first version used -inf here, which kept NONE
        # and silently emptied every agent sub-pool smaller than k — caught by inspecting
        # the picks, not by any guard; the guard below now makes it impossible.)
        cut = np.partition(-s, k - 1)[k - 1] if k < len(s) else np.inf
        idx = np.nonzero(-s <= cut + 1e-12)[0]
        if len(s) and len(idx) < min(k, len(s)):
            raise RuntimeError(f"FullPool.top shortlisted {len(idx)} of {len(s)} rows (k={k})")
        sc = [(i, self.rows[i].salience(now_ms)) for i in idx]
        sc.sort(key=lambda x: (-x[1], x[0]))
        return [(self.rows[i], v) for i, v in sc], int(len(s))


# ── text render cut (brief.ts:867-881), on the served brief ─────────────────────
def render_cut(served_ids, rows_by_id, tc, agent, ts_iso, now_ms):
    items = []
    for cid in served_ids:
        r = rows_by_id.get(cid)
        if r is None:
            return None
        title, ol, _, _ = tc.meta(r)
        ref = r.source_date or r.created_at or r.updated_at
        refms = parse_db_date_ms(ref) if ref else float("nan")
        age = max(0, math.floor((now_ms - refms) / 86_400_000)) if math.isfinite(refms) else 0
        pain = r.pain if r.pain is not None else 0.2
        items.append(f"[{r.chunk_type if r.chunk_type is not None else '?'}|pain {pain:.1f}|{age}d] "
                     f"{title} — {ol} (chk {cid})")
    head = f"# nox-mem brief — scope=global agent={agent} — {ts_iso} — {len(items)} items"
    budget = TOKEN_BUDGET - math.ceil(u16len(head) / 4)
    shown = 0
    for line in items:
        cost = math.ceil(u16len(line) / 4)
        if cost > budget:
            break
        shown += 1
        budget -= cost
    return len(items) - shown


# ── observation-only census (no database) ───────────────────────────────────────
def log_only(serving, out):
    """Distinct main-slot chunks per epoch straight from the serving log, no corpus.
    Main slots of a brief = ids_controle minus fresh_added, kept ONLY when that leaves
    exactly 8 ids: fresh_added is logged from the treated composition, so a brief whose
    control fresh picks differ would leak a coverage id into the count. Epochs whose
    lines carry fresh_added = null (control epochs after the 2026-09-03 logging fix) are
    counted as NOT MEASURABLE here, never as zero."""
    per = defaultdict(lambda: {"briefs": 0, "fresh_added_null": 0, "briefs_with_8": 0,
                               "ids": set(), "all10": set(), "agent": defaultdict(set)})
    for ln in open(serving):
        try:
            d = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if not d.get("agent") or len(d.get("ids_controle") or []) != DEFAULT_N:
            continue
        e = per[d["epoch"]]
        e["briefs"] += 1
        e["all10"] |= set(d["ids_controle"])
        fa = d.get("fresh_added")
        if fa is None:
            e["fresh_added_null"] += 1
            continue
        m = set(d["ids_controle"]) - set(fa)
        if len(m) == DEFAULT_N - FRESH_SLOTS:
            e["briefs_with_8"] += 1
            e["ids"] |= m
            e["agent"][d["agent"]] |= m
    union = set()
    res = {}
    for ep in sorted(per):
        e = per[ep]
        union |= e["ids"]
        res[ep] = {"briefs": e["briefs"], "fresh_added_null": e["fresh_added_null"],
                   "briefs_with_8_main": e["briefs_with_8"],
                   "distinct_main": len(e["ids"]) if e["briefs_with_8"] else "NOT MEASURABLE",
                   "distinct_main_per_agent": {a: len(x) for a, x in sorted(e["agent"].items())},
                   "distinct_all_10_slots": len(e["all10"]),
                   "main_ids": sorted(e["ids"])}
    out_d = {"generated_by": "measurement/sprint-desagrega-filtros-pool-principal.py --log-only",
             "generated_at": datetime.now(timezone.utc).isoformat(),
             "serving_log": serving, "per_epoch": res,
             "union_main_all_measurable_epochs": len(union), "union_main_ids": sorted(union)}
    with open(out, "w") as f:
        json.dump(out_d, f, indent=1)
    print(f"→ {out}", file=sys.stderr)
    return 0


# ── main ────────────────────────────────────────────────────────────────────────
def main():
    if "--log-only" in sys.argv:
        i = sys.argv.index("--log-only")
        return log_only(sys.argv[i + 1], sys.argv[i + 2])
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--serving", required=True)
    ap.add_argument("--epochs", required=True, help="comma list of epoch labels in the log")
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tz-offset-hours", type=float, default=0.0,
                    help="offset of the SERVING host's local time (V8 parses zone-less "
                         "date-times as local). 0 = UTC.")
    ap.add_argument("--max-briefs-per-epoch", type=int, default=0,
                    help="0 = all briefs. A cap is reported in the output, never silent.")
    a = ap.parse_args()

    if a.db.startswith("/var/backups") or a.db.startswith("/var/lib/nox-mem"):
        print("⛔ --db points at an original; copy it first (WAL grows -wal/-shm even read-only).",
              file=sys.stderr)
        return 2
    t0 = time.time()
    con = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    tz = a.tz_offset_hours
    tc = TextCache(con)
    epochs = a.epochs.split(",")

    # serving log, restricted to the epochs asked for
    briefs = defaultdict(list)
    n_lines = 0
    for ln in open(a.serving):
        try:
            d = json.loads(ln)
        except json.JSONDecodeError:
            continue
        n_lines += 1
        if d.get("epoch") in epochs and d.get("agent") and len(d.get("ids_controle") or []) == DEFAULT_N:
            briefs[d["epoch"]].append(d)
    agents = sorted({d["agent"] for e in briefs.values() for d in e})
    if not agents:
        print("⛔ no brief in the requested epochs — nothing measured.", file=sys.stderr)
        return 1

    corpus_n = con.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    max_created = con.execute("SELECT MAX(created_at) FROM chunks").fetchone()[0]

    # ── sub-pools (state of the corpus is fixed within the copy) ────────────────
    agent_pat = {ag: [f"sessions/{esc_like(ag)}/%"] for ag in agents}
    lim_agent = {ag: fetch(con, agent_pat[ag], CANDIDATE_POOL, tz) for ag in agents}
    lim_global = fetch(con, [], CANDIDATE_POOL, tz)
    full_agent = {ag: FullPool(fetch(con, agent_pat[ag], 0, tz)) for ag in agents}
    full_global = FullPool(fetch(con, [], 0, tz))
    rows_by_id = {r.id: r for r in full_global.rows}

    # ── "alone" pass counts on the whole corpus ─────────────────────────────────
    alone = {}
    sess = {ag: len(full_agent[ag].rows) for ag in agents}
    alone["F1_scope_routing"] = {
        "agent_subpool_source_sizes": sess,
        "agent_subpools_union": sum(sess.values()),
        "scope_subpool_source": corpus_n,
        "union_passes": corpus_n,
        "note": "scope=global returns no path pattern (brief.ts:204), so the scope sub-pool "
                "sees the whole corpus; F1 alone excludes nothing from the UNION — it only "
                "routes 5 of the 8 main slots to sessions/<agent>/%."}
    alone["F2_since"] = {"passes": corpus_n,
                         "note": "inactive: production caller sends no `since` (session-priming-f3.md)"}
    lim_union = set(r.id for r in lim_global) | set(r.id for ag in agents for r in lim_agent[ag])
    alone["F3_proxy_limit_500"] = {"per_subpool": CANDIDATE_POOL,
                                   "subpools": 1 + len(agents),
                                   "union_distinct": len(lim_union),
                                   "removed_from_corpus": corpus_n - len(lim_union)}
    alone["F4_exact_rerank"] = {"passes": corpus_n, "note": "reorders, removes nothing"}
    pain_floor_n = con.execute("SELECT COUNT(*) FROM chunks WHERE COALESCE(pain,0.2) >= ?",
                               (PAIN_FLOOR,)).fetchone()[0]
    alone["F7_pinned_floor"] = {"pain_ge_0.9_in_corpus": pain_floor_n,
                                "note": "pinnable only if already in the no-fresh current brief"}

    # F5 alone, exact-key part: greedy over the whole corpus in salience order at the
    # first brief of the first epoch (the near-dup part is relational and quadratic: NOT MEASURED)
    first_ts = min(d["ts"] for e in briefs.values() for d in e)
    now0 = js_date_parse_ms(first_ts, 0)
    allr = sorted(full_global.rows, key=lambda r: -r.salience(now0))
    tc.prefetch(allr)
    seen, dupk = set(), 0
    for r in allr:
        k = tc.d[r.id][2]
        if k in seen:
            dupk += 1
        seen.add(k)
    alone["F5_dedup"] = {"exact_key_duplicates_in_corpus": dupk,
                         "distinct_keys": len(seen),
                         "at": first_ts,
                         "near_dup_alone": "NOT MEASURED — greedy containment over 67k signatures "
                                           "is quadratic and only defined relative to the picked set"}
    alone["F6_quota_mainTarget"] = {"main_slots_per_brief": DEFAULT_N - FRESH_SLOTS,
                                    "agent_quota": math.ceil(DEFAULT_N / 2),
                                    "scope_quota_effective": DEFAULT_N - FRESH_SLOTS - math.ceil(DEFAULT_N / 2)}

    # ── per epoch: baseline + leave-one-out ─────────────────────────────────────
    VARIANTS = ["baseline", "lift_F1_scope_routing", "lift_F3_limit500", "lift_F4_exact_rerank",
                "lift_F5_dedup", "lift_F6_quota_split", "lift_F7_pinned"]
    per_epoch = {}
    for ep in epochs:
        bl = sorted(briefs.get(ep, []), key=lambda d: d["ts"])
        capped = False
        if a.max_briefs_per_epoch and len(bl) > a.max_briefs_per_epoch:
            step = len(bl) / a.max_briefs_per_epoch
            bl = [bl[int(i * step)] for i in range(a.max_briefs_per_epoch)]
            capped = True
        if not bl:
            per_epoch[ep] = {"briefs": 0, "note": "no brief in log"}
            continue
        distinct = {v: set() for v in VARIANTS}
        changed = Counter()
        jacc = defaultdict(list)
        fid_exact = fid_inter = fid_recon = fid_served = 0
        fid_subset_plus2 = 0      # recon (8) inside the 10 served ids, leaving exactly the 2 fresh slots
        fid_fresh_mismatch = 0    # briefs whose served-minus-fresh_added has != 8 ids
        served_main_distinct = set()
        rej = {"id": set(), "key": set(), "neardup": set()}
        scanned = set()
        pinned_n, pinned_displacing = Counter(), 0
        phase_ct = Counter()
        render_drop = Counter()
        subpool_of_pick = Counter()
        full_sizes = {}
        pinned_seen = set()
        by_agent = defaultdict(set)
        for d in bl:
            ag, now = d["agent"], js_date_parse_ms(d["ts"], 0)
            pa, pg = ranked(lim_agent[ag], now), ranked(lim_global, now)
            pools, quotas = [pa, pg], [math.ceil(DEFAULT_N / 2), DEFAULT_N // 2]
            # current brief (no fresh) -> pinned set (brief.ts:783, 819-821)
            cur = pick_dedup(pools, quotas, DEFAULT_N, tc, 0, frozenset(), True, main_only=False)
            pinned = frozenset(r.id for r, _, _ in cur
                               if (r.pain if r.pain is not None else 0.2) >= PAIN_FLOOR)
            for r, _ in pa + pg:
                scanned.add(r.id)
            base = pick_dedup(pools, quotas, DEFAULT_N, tc, FRESH_SLOTS, pinned, True, rej=rej)
            bset = {r.id for r, _, _ in base}
            for r, _, ph in base:
                phase_ct[ph] += 1
            agent_ids = {r.id for r, _ in pa}
            for r, _, _ in base:
                subpool_of_pick["agent" if r.id in agent_ids else "scope"] += 1
            pinned_n[len(pinned)] += 1
            pinned_seen |= pinned
            by_agent[ag] |= bset
            # did pinning displace anyone? compare with the no-pinned pick
            nop = {r.id for r, _, _ in pick_dedup(pools, quotas, DEFAULT_N, tc, FRESH_SLOTS, frozenset(), True)}
            if nop != bset:
                pinned_displacing += 1
            # fidelity vs served
            served_main = set(d["ids_controle"]) - set(d.get("fresh_added") or [])
            served_main_distinct |= served_main
            inter = len(bset & served_main)
            fid_inter += inter
            fid_recon += len(bset)
            fid_served += len(served_main)
            fid_exact += int(bset == served_main)
            ctrl = set(d["ids_controle"])
            fid_subset_plus2 += int(bset <= ctrl and len(ctrl - bset) == FRESH_SLOTS)
            fid_fresh_mismatch += int(len(served_main) != DEFAULT_N - FRESH_SLOTS)
            # text-render cut on the SERVED brief (10 ids as logged)
            rd = render_cut(d["ids_controle"], rows_by_id, tc, ag, d["ts"], now)
            render_drop["missing_row" if rd is None else rd] += 1

            res = {"baseline": bset}
            # F1 lifted: no agent routing — single scope pool takes all main slots
            res["lift_F1_scope_routing"] = {r.id for r, _, _ in
                                            pick_dedup([pg], [DEFAULT_N], DEFAULT_N, tc, FRESH_SLOTS, pinned, True)}
            # F3 lifted: no LIMIT 500 in either sub-pool
            fa, na = full_agent[ag].top(now)
            fg, ng = full_global.top(now)
            full_sizes[ag] = na
            full_sizes["global"] = ng
            res["lift_F3_limit500"] = {r.id for r, _, _ in
                                       pick_dedup([fa, fg], quotas, DEFAULT_N, tc, FRESH_SLOTS, pinned, True)}
            # F4 lifted: proxy order is the ranking
            res["lift_F4_exact_rerank"] = {r.id for r, _, _ in
                                           pick_dedup([by_proxy(lim_agent[ag]), by_proxy(lim_global)], quotas,
                                                      DEFAULT_N, tc, FRESH_SLOTS, pinned, True)}
            # F5 lifted: id-dedup only
            res["lift_F5_dedup"] = {r.id for r, _, _ in
                                    pick_dedup(pools, quotas, DEFAULT_N, tc, FRESH_SLOTS, pinned, False)}
            # F6 lifted: one merged pool, ordered by salience, mainTarget kept
            merged = sorted(pa + pg, key=lambda x: -x[1])
            res["lift_F6_quota_split"] = {r.id for r, _, _ in
                                          pick_dedup([merged], [DEFAULT_N], DEFAULT_N, tc, FRESH_SLOTS, pinned, True)}
            res["lift_F7_pinned"] = nop
            for v in VARIANTS:
                distinct[v] |= res[v]
                if v != "baseline":
                    changed[v] += int(res[v] != bset)
                    u = res[v] | bset
                    jacc[v].append(len(res[v] & bset) / len(u) if u else 1.0)
        nb = len(bl)
        slots = nb * (DEFAULT_N - FRESH_SLOTS)
        per_epoch[ep] = {
            "briefs": nb, "capped_sample": capped,
            "briefs_per_agent": dict(Counter(d["agent"] for d in bl)),
            "fidelity": {
                "briefs_main_set_exact": fid_exact,
                "share_exact": round(fid_exact / nb, 4),
                "recon_slots": fid_recon, "served_main_slots": fid_served,
                "recon_in_served": fid_inter,
                "share_recon_in_served": round(fid_inter / fid_recon, 4) if fid_recon else None,
                "briefs_recon_subset_of_served_leaving_2": fid_subset_plus2,
                "share_recon_subset_of_served_leaving_2": round(fid_subset_plus2 / nb, 4),
                "briefs_where_served_minus_fresh_added_is_not_8": fid_fresh_mismatch,
                "note": "fresh_added is logged from the TREATED composition (diffP2, brief.ts:855-859); "
                        "when the control's fresh picks differ, ids_controle minus fresh_added keeps a "
                        "control-fresh id and has 9 ids. That is the whole of the non-exact cases iff "
                        "briefs_main_set_exact + briefs_where_..._not_8 == briefs.",
            },
            "observed_from_log": {
                "caveat": "upper bound: contaminated by control-fresh ids where fresh_added (treated) differs",
                "main_slots": fid_served,
                "distinct_main_chunks": len(served_main_distinct),
                "slots_per_distinct": round(fid_served / len(served_main_distinct), 1) if served_main_distinct else None,
            },
            "series": {
                "S0_corpus": corpus_n,
                "S1_after_F1_scope_routing_union": corpus_n,
                "S2_after_F2_since": corpus_n,
                "S3_after_F3_limit500_union": len(lim_union),
                "S4_after_F4_rerank": len(lim_union),
                "S5_scanned_before_quotas_filled_distinct": len(scanned),
                "F5_rejected_distinct": {k: len(v) for k, v in rej.items()},
                "S6_after_F6_F7_picked_distinct": len(distinct["baseline"]),
                "note_S5": "every candidate of both sorted sub-pools is 'scanned' only in the "
                           "sense of being ranked; the pick loop stops at the quota",
            },
            "picks": {
                "by_phase": {str(k): v for k, v in sorted(phase_ct.items())},
                "by_subpool": dict(subpool_of_pick),
                "pinned_per_brief_hist": {str(k): v for k, v in sorted(pinned_n.items())},
                "briefs_where_pinning_changed_main_set": pinned_displacing,
            },
            "leave_one_out": {
                v: {"distinct_main_chunks": len(distinct[v]),
                    "briefs_changed_vs_baseline": changed[v] if v != "baseline" else 0,
                    "mean_jaccard_vs_baseline": round(sum(jacc[v]) / len(jacc[v]), 4) if v != "baseline" else 1.0}
                for v in VARIANTS},
            "full_subpool_sizes_when_F3_lifted": full_sizes,
            "ids": {v: sorted(distinct[v]) for v in VARIANTS},
            "pinned_ids_seen": sorted(pinned_seen),
            "ids_by_agent_baseline": {g: sorted(x) for g, x in sorted(by_agent.items())},
            "capacity": {
                "main_slots": slots,
                "distinct_main_chunks_recon": len(distinct["baseline"]),
                "share_of_slot_capacity_used_for_distinct": round(len(distinct["baseline"]) / slots, 5),
                "max_distinct_if_rotated_arith": min(slots, corpus_n),
                "max_share_of_corpus_if_rotated_arith": round(min(slots, corpus_n) / corpus_n, 4),
            },
            "render_cut_lines_dropped_hist": {str(k): v for k, v in sorted(render_drop.items(), key=lambda x: str(x[0]))},
        }
        print(f"[{a.label}] {ep}: briefs={nb} exact={fid_exact} distinct_base={len(distinct['baseline'])} "
              f"observed={len(served_main_distinct)} ({time.time()-t0:.0f}s)", file=sys.stderr)

    out = {
        "generated_by": "measurement/sprint-desagrega-filtros-pool-principal.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "label": a.label, "db_copy": a.db, "serving_log": a.serving, "serving_log_lines": n_lines,
        "corpus_chunks": corpus_n, "corpus_max_created_at": max_created,
        "tz_offset_hours_assumed": tz,
        "date_parse_failures": dict(_PARSE_FAIL),
        "agents": agents, "epochs": epochs,
        "filters": {
            "F1": "scope routing: agent sub-pool sessions/<a>/% (quota 5); scope=global sub-pool unfiltered (brief.ts:202-215,521-539)",
            "F2": "`since` window on updated_at (brief.ts:371-374) — inactive in production",
            "F3": "SQL proxy pre-rank + LIMIT 500 per sub-pool (brief.ts:377-390)",
            "F4": "exact calculateSalience re-rank (brief.ts:392-397)",
            "F5": "dedup: id / exact title|one_liner / near-dup containment>=0.6 (brief.ts:420-434)",
            "F6": "quota 5+5 capped by mainTarget = n - freshSlots = 8 (brief.ts:436-468)",
            "F7": "pinned floor: current-brief items with pain>=0.9 picked first (brief.ts:442-451,819-821)",
            "F8_post_log": "renderBriefText TOKEN_BUDGET 1200 (brief.ts:867-881) — after brief_log",
        },
        "alone": alone,
        "per_epoch": per_epoch,
        "runtime_s": round(time.time() - t0, 1),
    }
    with open(a.out, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"→ {a.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
