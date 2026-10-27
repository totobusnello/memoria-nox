"""The window factor has no variance in most of the sample, and that cuts both ways.

Found while writing the pre-registration code, which is why the code was written
first. The factorial's window factor is the fraction of the session the builder
saw. On 182 of the 194 eligible sessions that fraction is >= 0.95: the builder
saw essentially everything, so W0 and W1 are the SAME arm and the factor is
inestimable by construction.

In the exploratory run this means two things at once, in opposite directions:

  LIMIT  -- the interaction rests on the 8 sessions where the window varies, not
            on the 20 the audits name. The 200k-1M band rests on 5, and the
            50-200k band on ONE.
  BIAS   -- 43 of the 99 pairs could not show a window effect at all, and they
            were averaged in. So the +4.0 pp main effect of the window is an
            UNDERESTIMATE of the effect where the window actually differs.

This recomputation is post-hoc on data already seen and is labelled as such. It
corrects published numbers in our own audits; it is not confirmation of anything.
"""
import json, statistics
from collections import Counter

BASE = "/root/medicoes/2026-10-26-memory-tax"
SEE = {r["uuid"]: r for r in json.load(open(f"{BASE}/see-once.json"))["rows"]}
ROWS = json.load(open(f"{BASE}/armd-judged.json"))
THR = 0.5
ARMS = ("a", "b", "c_visible", "d_visible", "c_all", "d_full", "d_iso",
        "bm25_iso", "dense_iso")

def hit(r, k):
    return ((r.get(k) or {}).get("contem") or 0) > THR

def frac(r):
    return SEE.get(r["uuid"], {}).get("visible_frac", 1.0)

varies = [r for r in ROWS if frac(r) < 0.95]
flat = [r for r in ROWS if frac(r) >= 0.95]
print(f"pairs {len(ROWS)} from {len(set(r['uuid'] for r in ROWS))} sessions")
print(f"  window VARIES (<95% seen): {len(varies):3d} pairs · "
      f"{len(set(r['uuid'] for r in varies))} sessions")
print(f"  window FLAT  (>=95% seen): {len(flat):3d} pairs · "
      f"{len(set(r['uuid'] for r in flat))} sessions  <- W0 == W1 here, by construction")

def rate(g, k):
    gg = [r for r in g if r.get(k)]
    return (sum(1 for r in gg if hit(r, k)) / len(gg), len(gg)) if gg else (0.0, 0)

print(f"\n{'arm':12s} {'ALL (published)':>17s} {'window VARIES':>15s} {'window FLAT':>13s}")
for k in ARMS:
    a, na = rate(ROWS, k)
    v, nv = rate(varies, k)
    f, nf = rate(flat, k)
    print(f"{k:12s} {a*100:11.1f}% n={na:3d} {v*100:10.1f}% n={nv:2d} "
          f"{f*100:8.1f}% n={nf:2d}")

print("\nCONTROL that must hold: where the window is FLAT, the window factor")
print("cannot act, so C_all must equal C_visible and D_full must equal D_visible.")
for pair in (("c_visible", "c_all"), ("d_visible", "d_full")):
    f0, _ = rate(flat, pair[0])
    f1, _ = rate(flat, pair[1])
    verdict = "ok" if abs(f0 - f1) < 0.06 else f"DIVERGE by {abs(f0-f1)*100:.1f} pp"
    print(f"   {pair[0]:11s} {f0*100:5.1f}%  vs  {pair[1]:9s} {f1*100:5.1f}%   {verdict}")

print("\n--- the decomposition, recomputed on the pairs where the window VARIES ---")
b, _ = rate(varies, "b")
a, _ = rate(varies, "a")
gap = a - b
print(f"  oracle {a*100:.1f}% · memory as built {b*100:.1f}% · gap {gap*100:.1f} pp")
for k, lab in (("c_all", "window alone"), ("d_visible", "criterion alone"),
               ("d_full", "both")):
    v, _ = rate(varies, k)
    print(f"    {lab:17s} {v*100:5.1f}%  recovers {(v-b)*100:+5.1f} pp = "
          f"{(v-b)/gap*100:5.1f}% of the gap")
cw, _ = rate(varies, "c_all")
cc, _ = rate(varies, "d_visible")
cb, _ = rate(varies, "d_full")
print(f"  interaction = ({cb*100:.1f} - {cc*100:.1f}) - ({cw*100:.1f} - {b*100:.1f}) = "
      f"{((cb-cc)-(cw-b))*100:+.1f} pp")

print("\n  published decomposition, for comparison (ALL pairs):")
bA, _ = rate(ROWS, "b"); aA, _ = rate(ROWS, "a")
for k, lab in (("c_all", "window alone"), ("d_visible", "criterion alone"),
               ("d_full", "both")):
    v, _ = rate(ROWS, k)
    print(f"    {lab:17s} {v*100:5.1f}%  recovers {(v-bA)*100:+5.1f} pp = "
          f"{(v-bA)/(aA-bA)*100:5.1f}%")

print("\n--- how many SESSIONS each published figure rests on ---")
BANDS = [("<50k", 0, 50_000), ("50-200k", 50_000, 200_000), ("200k-1M", 200_000, 1 << 40)]
for nm, lo, hi in BANDS:
    g = [r for r in ROWS if lo <= SEE.get(r["uuid"], {}).get("total_chars", 0) < hi]
    print(f"  {nm:9s} {len(g):3d} pairs · {len(set(r['uuid'] for r in g))} sessions")
