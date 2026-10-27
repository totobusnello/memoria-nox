"""Can a STRUCTURAL predicate replace the five-substring abstention detector?

The detector in eval/run-abstention.mjs decides abstention by five substrings,
and its own header says the durable fix is for abstention to emit the canonical
string deterministically rather than asking the LLM to write it. Measured on
2026-10-26 against a bounded judge over the same 48 items, with equalised input
proved (48/48 label reproduction on the head): kappa 0.7938, and the detector
never over-marks — it MISSES five, two of them to a number inflection
("informação" is not a substring of "informações").

Before touching serving code, test the candidate predicate on the rows already
on disk. The serving path already extracts `[chunk_N]` citations, and its own
prompt requires every factual claim to carry one. So:

    citations == 0  =>  nothing in the answer is anchored in the context

That is a structural signal, free, and immune to wording. The question is
whether it recovers the five the substrings miss without over-marking — because
an abstention detector that over-marks turns a useful answer into a refusal and
would be worse than the one in place.

Reference labels are the bounded judge's `prob_declara_ausencia > 0.5`, which is
the calibrated reading from 2026-10-26, not the detector's own output.
"""
import json

D = json.load(open("/root/medicoes/2026-10-26-judge/abst-full.json"))
rows = [r for r in D["rows"] if r.get("prob_declara_ausencia") is not None]
print(f"rows with a judge label: {len(rows)} of {len(D['rows'])}")

def judge(r):
    return (r["prob_declara_ausencia"] or 0) > 0.5
def substr(r):
    return bool(r["abstained"])
def ncites(r):
    """`citations` in this artifact is a COUNT, not a list — len() threw on it."""
    c = r.get("citations")
    return c if isinstance(c, int) else len(c or [])
def struct(r):
    return ncites(r) == 0
def either(r):
    return substr(r) or struct(r)

def cm(pred, name):
    tp = sum(1 for r in rows if pred(r) and judge(r))
    fp = sum(1 for r in rows if pred(r) and not judge(r))
    fn = sum(1 for r in rows if not pred(r) and judge(r))
    tn = sum(1 for r in rows if not pred(r) and not judge(r))
    acc = (tp + tn) / len(rows)
    po = acc
    pe = ((tp + fp) * (tp + fn) + (fn + tn) * (fp + tn)) / len(rows) ** 2
    k = (po - pe) / (1 - pe) if pe < 1 else 0.0
    print(f"{name:28s} TP={tp:2d} FP={fp:2d} FN={fn:2d} TN={tn:2d} "
          f"acc={acc:.3f} kappa={k:.4f}")
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "kappa": k}

print(f"\njudge says abstained: {sum(1 for r in rows if judge(r))} of {len(rows)}")
print(f"{'predicate':28s} {'confusion against the bounded judge':>20s}")
a = cm(substr, "five substrings (current)")
b = cm(struct, "citations == 0 (structural)")
c = cm(either, "substrings OR citations==0")

print("\nthe five the substrings MISS — does the structural predicate see them?")
missed = [r for r in rows if judge(r) and not substr(r)]
for r in missed:
    print(f"  [{r['kind'][:3]}] {r['id'][:22]:22s} cites={ncites(r)} "
          f"struct={'YES' if struct(r) else 'no '}  {r['answer_head'][:72]!r}")

print("\nand where the structural predicate would OVER-mark (judge says not abstained):")
over = [r for r in rows if struct(r) and not judge(r)]
for r in over:
    print(f"  [{r['kind'][:3]}] {r['id'][:22]:22s} p_aus={r['prob_declara_ausencia']:.2f} "
          f"{r['answer_head'][:72]!r}")
if not over:
    print("  none")

print("\nwhat it would do to the published baseline (0.7826 neg / 0.3200 pos):")
for name, pred in (("substrings", substr), ("citations==0", struct),
                   ("OR", either), ("judge (reference)", judge)):
    for kind in ("negative", "positive"):
        g = [r for r in rows if r["kind"] == kind]
        print(f"  {name:18s} {kind:9s} {sum(1 for r in g if pred(r))}/{len(g)} = "
              f"{sum(1 for r in g if pred(r))/len(g):.4f}")
    gn = [r for r in rows if r["kind"] == "negative"]
    gp = [r for r in rows if r["kind"] == "positive"]
    gap = sum(1 for r in gn if pred(r))/len(gn) - sum(1 for r in gp if pred(r))/len(gp)
    print(f"  {name:18s} GAP      {gap:+.4f}")
