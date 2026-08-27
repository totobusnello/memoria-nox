import sqlite3, collections, json
db=sqlite3.connect("file:/root/.openclaw/workspace/tools/nox-mem/nox-mem.db?mode=ro", uri=True)
estudo={r[0] for r in db.execute(
  "SELECT DISTINCT chunk_id FROM p2_verdict WHERE chunk_id IS NOT NULL AND severity IN ('S1','S2')")}
# elegiveis ao pool: mesmo WHERE do fetchFreshCandidates (janela global 30d)
eleg={r[0] for r in db.execute("""
  SELECT id FROM chunks
   WHERE (source_file LIKE 'memory/entities/%' OR source_file LIKE 'memory/lessons.md')
     AND (COALESCE(importance,0) >= 0.7 OR COALESCE(pain,0) >= 0.7)
     AND julianday('now') - julianday(COALESCE(source_date, created_at)) <= 30""")}
print(f"elegiveis={len(eleg)}  do estudo entre eles={len(eleg & estudo)}")
print()
print("=== composicao dos grupos de last_served, RECONSTRUIDA por dia ===")
print(f"{'corte':<12} {'grupos':>7} {'puro-est':>9} {'mistos':>7} {'chunks_est':>11} {'em_puro':>8} {'%puro':>7}")
for corte in ("2026-08-23 23:59:59","2026-08-24 23:59:59","2026-08-25 23:59:59","2026-08-26 19:52:07"):
    ls={}
    for cid, m in db.execute(
        "SELECT chunk_id, MAX(served_at) FROM brief_log WHERE served_at <= ? GROUP BY chunk_id",(corte,)):
        if cid in eleg: ls[cid]=m
    g=collections.defaultdict(list)
    for cid,m in ls.items(): g[m].append(cid)
    puro=mist=0; e_puro=e_mist=0
    for m,v in g.items():
        e=[c for c in v if c in estudo]; n=[c for c in v if c not in estudo]
        if len(v)<2: continue
        if e and n: mist+=1; e_mist+=len(e)
        elif e: puro+=1; e_puro+=len(e)
    tot=e_puro+e_mist
    pct=100*e_puro/tot if tot else 0
    print(f"{corte[:10]:<12} {len(g):>7} {puro:>9} {mist:>7} {tot:>11} {e_puro:>8} {pct:>6.1f}%")
