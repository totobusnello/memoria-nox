import sqlite3, collections
DB="file:/root/.openclaw/workspace/tools/nox-mem/nox-mem.db?mode=ro"
SONDAS=("473f85e8-43ae-4883-baa2-2d76407af941","c48e8353-cd95-4bd5-997b-dc921e2a0cac",
        "6ff2d9c4-79f2-4526-8eb5-c42d60bbeea6","90a105f5-ef33-4135-8e54-b4e978bbb1ee",
        "66977ec1-2809-44df-91b8-c158ce0e68e8")
db=sqlite3.connect(DB,uri=True)
estudo={r[0] for r in db.execute("SELECT DISTINCT chunk_id FROM p2_verdict WHERE chunk_id IS NOT NULL AND severity IN ('S1','S2')")}
def estado(t_ref, sem_sondas):
    eleg={r[0] for r in db.execute("""SELECT id FROM chunks
       WHERE (source_file LIKE 'memory/entities/%' OR source_file LIKE 'memory/lessons.md')
         AND (COALESCE(importance,0) >= 0.7 OR COALESCE(pain,0) >= 0.7)
         AND julianday(?) - julianday(COALESCE(source_date, created_at)) <= 30""",(t_ref,))}
    cond="AND served_at <= ?"; par=[t_ref]
    if sem_sondas:
        cond += " AND brief_id NOT IN (%s)"%",".join("?"*len(SONDAS)); par += list(SONDAS)
    ls={}
    for cid,m in db.execute("SELECT chunk_id, MAX(served_at) FROM brief_log WHERE 1=1 %s GROUP BY chunk_id"%cond, par):
        if cid in eleg: ls[cid]=m
    g=collections.defaultdict(list)
    for cid,m in ls.items(): g[m].append(cid)
    ordem=sorted(ls.items(), key=lambda kv: kv[1])
    pos=next((i for i,(cid,_) in enumerate(ordem) if cid in estudo), None)
    quali=[]; puro=mist=0; pares=zeros=0
    for m,v in g.items():
        e=[c for c in v if c in estudo]; n=[c for c in v if c not in estudo]
        if len(v)>1:
            if e and n: mist+=1
            elif e: puro+=1
        if e and n and len(v)>2:
            quali.append(min(i for i,(cid,_) in enumerate(ordem) if ls[cid]==m))
    return dict(eleg=len(eleg), chunks=len(ls), grupos=len(g), pos_1o=pos,
                quali=len(quali), menor_pos=min(quali) if quali else None, puros=puro, mistos=mist)
REFS=["2026-08-26 22:00:00","2026-08-27 09:00:00"]
print("%-11s %-11s %6s %7s %7s %7s %6s %10s %6s %7s"%("T_REF","sondas","eleg","chunks","grupos","pos_1o","quali","menor_pos","puros","mistos"))
print("-"*92)
res={}
for t in REFS:
    for ss in (False,True):
        r=estado(t,ss); res[(t,ss)]=r
        print("%-11s %-11s %6d %7d %7d %7s %6d %10s %6d %7d"%(t[5:], "excluidas" if ss else "incluidas",
              r["eleg"],r["chunks"],r["grupos"],r["pos_1o"],r["quali"],r["menor_pos"],r["puros"],r["mistos"]))
print()
for t in REFS:
    a,b=res[(t,False)],res[(t,True)]
    print("efeito SO das sondas em %s: %s"%(t, "NENHUM" if a==b else {k:(a[k],b[k]) for k in a if a[k]!=b[k]}))
a,b=res[(REFS[0],True)],res[(REFS[1],True)]
print("efeito SO do tempo (ambos sem sondas): %s"%({k:(a[k],b[k]) for k in a if a[k]!=b[k]} or "NENHUM"))
