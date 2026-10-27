"""Was the FILE wrong, or did my report compare the wrong field?

The corpus-wide pass printed `was: <gold[0].source_file>` — the FIRST gold entry
of the query, not the REJECTED one it was repairing. A query with several gold
entries can have one rejected and another accepted, pointing at different files,
so four rows showing an identical `was:` may mean the file was right all along
and my print was comparing the wrong thing. That distinction decides whether the
claim "the file was wrong" survives, so it is measured against the rejected
entry's own source_file.
"""
import json
from collections import Counter

audit = json.load(open("/root/medicoes/gold-audit-2026-10-27.json"))
resel = json.load(open("/root/medicoes/v3-reselect-2026-10-27.json"))
wide = json.load(open("/root/medicoes/v3-corpuswide-2026-10-27.json"))
THR = 0.5

# the source_file(s) the FILE-LEVEL pass actually tested, per query
tested = {}
for r in resel:
    if r["kind"] == "candidate":
        tested.setdefault(r["query_id"], set()).add(r["source_file"])

best = {}
for r in wide:
    if r["kind"] != "candidate" or "responde" not in r:
        continue
    if (r["responde"] or 0) > THR:
        b = best.get(r["query_id"])
        if b is None or r["responde"] > b["responde"]:
            best[r["query_id"]] = r

same, diff = [], []
for q, b in sorted(best.items()):
    t = tested.get(q, set())
    (same if b["source_file"] in t else diff).append((q, b, t))

print(f"queries repaired corpus-wide: {len(best)}")
print(f"  found in a file the file-level pass DID test : {len(same)}  <- contradiction")
print(f"  found in a file it did NOT test              : {len(diff)}  <- the file was wrong")

if same:
    print("\nCONTRADICTIONS — same (query, file) judged twice with different outcomes:")
    for q, b, t in same:
        prior = [r for r in resel if r["kind"] == "candidate"
                 and r["query_id"] == q and r["chunk_id"] == b["chunk_id"]]
        p0 = prior[0]["responde"] if prior else None
        print(f"  Q{q:<4d} chunk {b['chunk_id']}  wide p={b['responde']:.2f}  "
              f"file-level p={p0 if p0 is None else format(p0, '.2f')}  "
              f"{'SAME CHUNK, judge flipped' if prior else 'chunk not in the file-level batch'}")
        print(f"        {b['source_file'][:72]}")

print(f"\nso the attribution that survives: the FILE was wrong in {len(diff)} of "
      f"{len(best)} repairs")
cats = Counter()
for q, b, t in diff:
    cats[b["source_file"].split("/")[0]] += 1
print(f"  where the real answer lives, by top-level dir: {dict(cats)}")
