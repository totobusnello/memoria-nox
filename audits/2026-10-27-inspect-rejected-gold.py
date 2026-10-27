"""Hand-check of the gold entries the judge rejected. 60% acceptance could be a
fact about the gold or a fact about the judge, and the controls (1.8% on random
chunks, 100% on gold built today) say it is not blind severity — but a rate is
not a verdict. Six are printed in full for a human call."""
import json, sqlite3

res = json.load(open("/root/medicoes/gold-audit-2026-10-27.json"))
con = sqlite3.connect("file:/root/.openclaw/workspace/tools/nox-mem/nox-mem.db?mode=ro",
                      uri=True)
gold = [r for r in res if r["kind"] == "gold"]
byq = {}
for r in gold:
    byq.setdefault(r["query_id"], []).append(r)
dead = sorted(q for q, v in byq.items()
              if not any((x.get("responde") or 0) > 0.5 for x in v))
print(f"queries with EVERY gold entry rejected: {len(dead)} -> {dead}")
for qid in dead[:6]:
    g = byq[qid][0]
    txt = con.execute("SELECT substr(chunk_text,1,220) FROM chunks WHERE id=?",
                      (g["chunk_id"],)).fetchone()[0]
    print(f"\n=== Q{qid} [{g['category']}] p_responde={g['responde']:.2f}")
    print(f"  Q: {g['query']}")
    print(f"  A: {(g['anchor'] or '')[:110]}")
    print(f"  C: {txt.replace(chr(10), ' ')[:200]}")
