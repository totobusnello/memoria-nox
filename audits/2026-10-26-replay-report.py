"""Report the replay from the stored labels, and calibrate the judge on itself.

Arm A answered using the very window the reference answer was extracted from,
so arm A CANNOT genuinely contradict the reference. Its contradiction rate is
therefore a negative control on the `contradiz` predicate: whatever it reports
for A is false-positive rate, and B's rate only means something above it.
This is the discipline the 2026-10-23 audit established -- the verifier needs
calibrating too, and the same data gave 0.700 / 0.833 / 0.913 under three
criteria.
"""
import collections
import json

P = "/root/medicoes/2026-10-26-memory-tax/replay-judged.json"
rows = json.load(open(P, encoding="utf-8"))
THR = 0.5
g = lambda r, arm, k: (r[arm].get(k) or 0) > THR

n = len(rows)
a_ok = sum(1 for r in rows if g(r, "a", "contem"))
b_ok = sum(1 for r in rows if g(r, "b", "contem"))
a_bad = sum(1 for r in rows if g(r, "a", "contradiz"))
b_bad = sum(1 for r in rows if g(r, "b", "contradiz"))
b_sil = sum(1 for r in rows if r["b_abstained"])

print(f"pairs judged: {n}\n")
print(f"{'':16s} {'contem':>14s} {'contradiz':>14s} {'calado':>14s}")
print(f"{'arm A (raw)':16s} {a_ok:5d} {a_ok/n:7.1%} {a_bad:5d} {a_bad/n:7.1%} {0:5d} {0:7.1%}")
print(f"{'arm B (memory)':16s} {b_ok:5d} {b_ok/n:7.1%} {b_bad:5d} {b_bad/n:7.1%} "
      f"{b_sil:5d} {b_sil/n:7.1%}")
print(f"\nFAITHFULNESS TAX: {a_ok/n:.1%} - {b_ok/n:.1%} = {(a_ok-b_ok)/n:+.1f}pp absolute, "
      f"{1-b_ok/a_ok:.1%} relative")

print(f"\n=== NEGATIVE CONTROL on the `contradiz` predicate ===")
print(f"arm A read the window the reference came from, so it cannot truly contradict it.")
print(f"  A flagged as contradicting : {a_bad}/{n} = {a_bad/n:.1%}  <- false-positive floor")
print(f"  B flagged as contradicting : {b_bad}/{n} = {b_bad/n:.1%}")
print(f"  => B is {'BELOW' if b_bad <= a_bad else 'above'} the predicate's own noise; "
      f"{'no evidence of damage' if b_bad <= a_bad else 'damage signal survives'}")
both = sum(1 for r in rows if g(r, "a", "contem") and g(r, "a", "contradiz"))
print(f"  A scored contem AND contradiz simultaneously: {both} "
      f"({both/max(a_bad,1):.0%} of A's flags) -- the predicates are not exclusive")

def block(title, key, buckets):
    print(f"\n=== by {title} ===")
    print(f"{'':14s} {'n':>4s} {'A contem':>12s} {'B contem':>12s} {'tax rel':>9s} {'B calado':>10s}")
    for lb, pred in buckets:
        sub = [r for r in rows if pred(r)]
        if not sub:
            continue
        m = len(sub)
        ao = sum(1 for r in sub if g(r, "a", "contem"))
        bo = sum(1 for r in sub if g(r, "b", "contem"))
        si = sum(1 for r in sub if r["b_abstained"])
        tax = f"{1-bo/ao:7.1%}" if ao else "      --"
        print(f"{lb:14s} {m:4d} {ao:4d} {ao/m:6.1%} {bo:4d} {bo/m:6.1%} {tax} {si:4d} {si/m:5.1%}")

block("category — the four the builder declares it keeps", "category",
      [(c, (lambda c: lambda r: r.get("category") == c)(c))
       for c in ("decision", "preference", "lesson", "context")])
block("scope of the evidence", "scope",
      [(c, (lambda c: lambda r: r.get("scope") == c)(c)) for c in ("local", "distribuido")])
block("evidence span vs the builder's 2000-char block", "span",
      [("< 2000", lambda r: (r.get("span_chars") or 0) < 2000),
       ("2000-4000", lambda r: 2000 <= (r.get("span_chars") or 0) < 4000),
       ("> 4000", lambda r: (r.get("span_chars") or 0) >= 4000)])
block("memory units the session produced", "units",
      [("1-5", lambda r: 1 <= (r.get("memory_units") or 0) < 6),
       ("6-15", lambda r: 6 <= (r.get("memory_units") or 0) < 16),
       ("16-60", lambda r: 16 <= (r.get("memory_units") or 0) < 61),
       ("61+", lambda r: (r.get("memory_units") or 0) >= 61)])
block("session stratum", "stratum",
      [(c, (lambda c: lambda r: r.get("stratum") == c)(c))
       for c in ("few", "median", "many", "top")])

print("\n=== where B is silent and A is right: what the memory simply lacks ===")
lack = [r for r in rows if g(r, "a", "contem") and r["b_abstained"]]
print(f"{len(lack)} of {a_ok} ({len(lack)/a_ok:.1%} of what the raw side answers)")
print("by category:", dict(collections.Counter(r["category"] for r in lack)))
for r in lack[:4]:
    print(f"\n  [{r['category']}|{r['memory_units']}u] {r['question'][:140]}")
    print(f"  raw: {r['arm_a_raw'][:120]}")
