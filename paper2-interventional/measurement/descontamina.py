import sqlite3, collections
db=sqlite3.connect("file:/root/.openclaw/workspace/tools/nox-mem/nox-mem.db?mode=ro", uri=True)
estudo={r[0] for r in db.execute("SELECT DISTINCT chunk_id FROM p2_verdict WHERE chunk_id IS NOT NULL AND severity IN ('S1','S2')")}
eleg={r[0] for r in db.execute("""SELECT id FROM chunks
   WHERE (source_file LIKE 'memory/entities/%' OR source_file LIKE 'memory/lessons.md')
     AND (COALESCE(importance,0) >= 0.7 OR COALESCE(pain,0) >= 0.7)
     AND julianday('now') - julianday(COALESCE(source_date, created_at)) <= 30""")}
def estado(excluir_sondas):
    cond = "AND served_at < '2026-08-26 19:58:00'" if excluir_sondas else ""
    ls={}
    for cid,m in db.execute(f"SELECT chunk_id, MAX(served_at) FROM brief_log WHERE 1=1 {cond} GROUP BY chunk_id"):
        if cid in eleg: ls[cid]=m
    g=collections.defaultdict(list)
    for cid,m in ls.items(): g[m].append(cid)
    ordem=sorted(ls.items(), key=lambda kv: kv[1])
    pos_1o_estudo=next((i for i,(cid,_) in enumerate(ordem) if cid in estudo), None)
    quali=[]; puro=mist=0; e_puro=e_mist=0
    for m,v in g.items():
        e=[c for c in v if c in estudo]; n=[c for c in v if c not in estudo]
        if len(v)>1:
            if e and n: mist+=1; e_mist+=len(e)
            elif e: puro+=1; e_puro+=len(e)
        if e and n and len(v)>2: quali.append(min(i for i,(cid,_) in enumerate(ordem) if ls[cid]==m))
    return dict(grupos=len(g), pos_1o_estudo=pos_1o_estudo, qualificaveis=len(quali),
                menor_pos_qualificavel=min(quali) if quali else None,
                puro=puro, mistos=mist, est_em_puro=e_puro, est_em_misto=e_mist)
a=estado(False); b=estado(True)
print(f"{'metrica':<28} {'observado':>12} {'descontaminado':>15} {'muda?':>7}")
for k in a:
    m = "SIM" if a[k]!=b[k] else "-"
    print(f"{k:<28} {str(a[k]):>12} {str(b[k]):>15} {m:>7}")
print()
print("=== as 3 sondas moveram last_served de ~18:07 para 19:58 ===")
for cid in (308222,308280,308284):
    obs=db.execute("SELECT MAX(served_at) FROM brief_log WHERE chunk_id=?",(cid,)).fetchone()[0]
    des=db.execute("SELECT MAX(served_at) FROM brief_log WHERE chunk_id=? AND served_at<'2026-08-26 19:58:00'",(cid,)).fetchone()[0]
    p_obs=next((i for i,(c,_) in enumerate(sorted(((c,m) for c,m in
        ((r[0],r[1]) for r in db.execute("SELECT chunk_id, MAX(served_at) FROM brief_log GROUP BY chunk_id"))
        if c in eleg), key=lambda kv: kv[1])) if c==cid), None)
    print(f"  {cid}: observado={obs}  descontaminado={des}  posicao_obs={p_obs}")
