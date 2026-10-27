"""Does the retention_days omission change what the system serves? Read-only, free.

The question was left open on 2026-10-27: session-distill's INSERT lists neither
memory_type nor retention_days, so all 6,898 distilled chunks are NULL, and NULL
resolves to never-decay (salience.ts:69-71 -> recencyComponent returns 1.0). The
codebase also holds the opposite intent (db.ts:437-452 backfills ELSE 90).

Rather than choose on taste, measure. NOX_SALIENCE_MODE is `active` in the
serving process's own environment (read from /proc/<pid>/environ, not from the
.env, which is intent), so salience really does move the ranking: search.ts:442
adds `salienceDelta` to boostSum, and salience=0 maps to -0.5.

Both scenarios are computed with the formula and the component functions copied
from src/salience.ts, and the comparison reports what a reader would notice: the
delta applied to the score, and the class boundaries that the tier manager and
the brief act on (promote/retain/review/archive at 0.7/0.4/0.15).

Control that can fail: the no-change scenario must reproduce exactly what
production computes today, i.e. recency = 1.0 for every distilled chunk. If any
distilled chunk comes out with recency != 1.0 under the NULL scenario, the
replica is wrong and nothing below is readable.
"""
import math, sqlite3, statistics
from collections import Counter

DB = "file:/root/.openclaw/workspace/tools/nox-mem/nox-mem.db?mode=ro"
TODAY_MS = None   # set from the DB clock below, so the probe does not depend on this host

W_IMPORTANCE, W_RECENCY, W_PAIN, W_ACCESS = 0.55, 0.15, 0.10, 0.20
FALLBACK_IMPORTANCE = 0.5
FALLBACK_RETENTION = 90

def clamp01(x):
    if x is None or not math.isfinite(x):
        return 0.0
    return 0.0 if x < 0 else (1.0 if x > 1 else x)

def recency(source_date, last_accessed, retention_days, now_ms):
    """recencyComponent, salience.ts:78-98. retention_days <= 0 -> 1.0."""
    if retention_days is None or retention_days <= 0:
        return 1.0
    ref = last_accessed or source_date
    if not ref:
        return 0.5
    try:
        import datetime
        s = str(ref).replace("T", " ")[:19]
        dt = datetime.datetime.strptime(s, "%Y-%m-%d %H:%M:%S") if len(s) > 10 \
            else datetime.datetime.strptime(s[:10], "%Y-%m-%d")
        ref_ms = dt.replace(tzinfo=datetime.timezone.utc).timestamp() * 1000
    except Exception:
        return 0.5
    age = (now_ms - ref_ms) / 86400000.0
    if age <= 0:
        return 1.0
    return math.pow(2, -age / retention_days)

def importance_c(chunk_type, explicit):
    if explicit is not None and math.isfinite(explicit):
        return clamp01(explicit)
    return FALLBACK_IMPORTANCE

def pain_c(p):
    return 0.2 if p is None or not math.isfinite(p) else clamp01(p)

def access_c(a):
    if a is None or not math.isfinite(a) or a <= 0:
        return 0.0
    return clamp01(math.log1p(a) / math.log(1000))

def salience(imp, rec, pn, acc):
    return clamp01(W_IMPORTANCE * imp + W_RECENCY * rec + W_PAIN * pn + W_ACCESS * acc)

def klass(s):
    return ("promote" if s >= 0.7 else "retain" if s >= 0.4
            else "review" if s >= 0.15 else "archive")

con = sqlite3.connect(DB, uri=True)
now_ms = con.execute("SELECT strftime('%s','now')*1000").fetchone()[0]
dbclock = con.execute("SELECT datetime('now')").fetchone()[0]
print(f"DB clock: {dbclock} UTC")

rows = con.execute(
    "SELECT id, chunk_type, importance, pain, access_count, source_date, "
    "last_accessed_at, retention_days, source_file "
    "FROM chunks").fetchall()
print(f"chunks: {len(rows)}")

dist = [r for r in rows if (r[8] or "").startswith("sessions/")]
print(f"distilled (sessions/%): {len(dist)} · with retention_days NULL: "
      f"{sum(1 for r in dist if r[7] is None)}")

# ---- control: under the NULL scenario every distilled chunk must get recency 1.0
bad = [r[0] for r in dist
       if r[7] is None and recency(r[5], r[6], r[7], now_ms) != 1.0]
print(f"\nCONTROL · distilled chunks whose NULL recency != 1.0: {len(bad)} "
      f"({'ok' if not bad else 'REPLICA WRONG — stop'})")
assert not bad

# ---- two scenarios, on the distilled chunks only (nothing else changes)
moved, deltas, cls_now, cls_90 = [], [], Counter(), Counter()
for cid, ct, imp, pn, acc, sd, la, rd, sf in dist:
    i_, p_, a_ = importance_c(ct, imp), pain_c(pn), access_c(acc)
    s_now = salience(i_, 1.0, p_, a_)                                   # NULL -> never decay
    s_90 = salience(i_, recency(sd, la, 90, now_ms), p_, a_)            # the backfill's intent
    deltas.append(s_now - s_90)
    k1, k2 = klass(s_now), klass(s_90)
    cls_now[k1] += 1
    cls_90[k2] += 1
    if k1 != k2:
        moved.append((cid, k1, k2, s_now, s_90, sd))

d = sorted(deltas)
print(f"\nsalience drop if retention_days became 90 (per distilled chunk)")
print(f"  median {statistics.median(d):.4f} · mean {statistics.mean(d):.4f} · "
      f"min {d[0]:.4f} · max {d[-1]:.4f}")
print(f"  drop > 0.05 in {sum(1 for x in d if x > 0.05)} · "
      f"> 0.10 in {sum(1 for x in d if x > 0.10)} of {len(d)}")

print(f"\nthe delta the search path actually adds (salience - 0.5, bounded):")
print(f"  mean |change| in the applied delta = {statistics.mean(abs(x) for x in d):.4f} "
      f"on a scale where the whole delta spans 1.0")

print(f"\nclass distribution (what the tier manager and the brief act on)")
print(f"{'class':9s} {'NULL (today)':>13s} {'90 days':>9s} {'change':>8s}")
for k in ("promote", "retain", "review", "archive"):
    print(f"{k:9s} {cls_now[k]:13d} {cls_90[k]:9d} {cls_90[k]-cls_now[k]:+8d}")
print(f"\nchunks that CHANGE class: {len(moved)} of {len(dist)} = "
      f"{len(moved)/len(dist)*100:.1f}%")
if moved:
    mv = Counter((a, b) for _, a, b, _, _, _ in moved)
    for (a, b), n in mv.most_common():
        print(f"   {a} -> {b}: {n}")
    print("  examples:")
    for cid, a, b, s1, s2, sd in moved[:5]:
        print(f"   id={cid} {a}->{b}  {s1:.3f} -> {s2:.3f}  source_date={sd}")

# ---- and the question that decides whether any of this reaches a reader:
# do distilled chunks compete with the rest of the corpus, or are they a class apart?
other = [r for r in rows if not (r[8] or "").startswith("sessions/")]
os_ = [salience(importance_c(r[1], r[2]), recency(r[5], r[6], r[7], now_ms),
                pain_c(r[3]), access_c(r[4])) for r in other]
ds_now = [salience(importance_c(r[1], r[2]), 1.0, pain_c(r[3]), access_c(r[4])) for r in dist]
ds_90 = [salience(importance_c(r[1], r[2]), recency(r[5], r[6], 90, now_ms),
                  pain_c(r[3]), access_c(r[4])) for r in dist]
print(f"\nsalience of the rest of the corpus (n={len(os_)}): "
      f"median {statistics.median(os_):.3f}")
print(f"  distilled today        : median {statistics.median(ds_now):.3f}")
print(f"  distilled at 90 days   : median {statistics.median(ds_90):.3f}")
# how much of the corpus a distilled chunk outranks, in each scenario
os_sorted = sorted(os_)
import bisect
def pct(v):
    return bisect.bisect_left(os_sorted, v) / len(os_sorted) * 100
print(f"  percentile of the median distilled chunk against the rest: "
      f"{pct(statistics.median(ds_now)):.1f}% today -> "
      f"{pct(statistics.median(ds_90)):.1f}% at 90 days")
