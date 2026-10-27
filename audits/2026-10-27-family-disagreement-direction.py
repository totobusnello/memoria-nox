"""Is the second family uniformly more generous, or MORE generous on arm D?

The gap differs by 13.1 pp between families, which is larger than the effect one
of them reports. Two readings are compatible with that and they have opposite
consequences:

  (a) LITERALNESS BIAS — the identifier prompt produces more literal answers and
      the permissive judge rewards them without an equal gain in correctness.
      Then +21.2 pp is inflated and +8.1 is closer to the truth.
  (b) SEVERITY — judge 1 rejects correct answers that judge 2 recognises. Then
      +21.2 pp is the truer number and +8.1 is deflated.

Neither is decidable from the two judges alone; what IS measurable is whether
the extra generosity is SYMMETRIC across arms. Asymmetry toward D is the
signature (a) predicts.
"""
import json
from collections import Counter

res = json.load(open("/root/medicoes/second-family-judge-2026-10-27.json"))
ok = [r for r in res if "j2" in r]
PAIRS = [("c_all", "d_full"), ("c_visible", "d_visible"), ("c_iso", "d_iso")]

print(f"{'arm':12s} {'n':>4s} {'j1=0,j2=1':>10s} {'j1=1,j2=0':>10s} "
      f"{'net j2-j1':>10s}")
cells = {}
for arm in sorted({r["arm"] for r in ok}):
    g = [r for r in ok if r["arm"] == arm]
    a = sum(1 for r in g if not r["j1"] and r["j2"])      # j2 adds
    b = sum(1 for r in g if r["j1"] and not r["j2"])      # j2 removes
    cells[arm] = (a, b, len(g))
    print(f"{arm:12s} {len(g):4d} {a:10d} {b:10d} {a-b:+10d}")

print(f"\nis the extra generosity symmetric across the pair?")
for c, d in PAIRS:
    if c in cells and d in cells:
        ac, bc, nc = cells[c]
        ad, bd, nd = cells[d]
        print(f"  {c} -> j2 adds {ac}/{nc} = {ac/nc:.1%}")
        print(f"  {d} -> j2 adds {ad}/{nd} = {ad/nd:.1%}   "
              f"asymmetry {(ad/nd - ac/nc)*100:+.1f} pp")

print(f"\nand the reverse cell — items judge 1 accepts and judge 2 rejects:")
tot_a = sum(v[0] for v in cells.values())
tot_b = sum(v[1] for v in cells.values())
print(f"  j2 adds {tot_a} · j2 removes {tot_b} · ratio {tot_a/max(tot_b,1):.1f}:1")
print(f"  ⇒ the disagreement is {'almost ONE-DIRECTIONAL' if tot_b <= tot_a*0.2 else 'two-directional'},"
      f" which is what a CALIBRATION difference looks like")

print(f"\nby category, where j2 adds the most (arm d_full):")
g = [r for r in ok if r["arm"] == "d_full"]
cat = {}
for r in g:
    c = cat.setdefault(r.get("category") or "?", [0, 0])
    c[1] += 1
    if not r["j1"] and r["j2"]:
        c[0] += 1
for k, (a, n) in sorted(cat.items(), key=lambda kv: -kv[1][0] / max(kv[1][1], 1)):
    print(f"  {k:12s} {a:3d}/{n:3d} = {a/n:5.1%}")

print("\n⇒ what this cannot settle: which family is RIGHT. A third rater is needed,")
print("  and the only one that is not another LLM is human. The substitution")
print("  measured the problem; it did not remove the need.")
