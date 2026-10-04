import importlib.util, json, sys, math, collections
spec = importlib.util.spec_from_file_location("m", "/var/tmp/sprint-filtros-pp/sprint-desagrega-filtros-pool-principal.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
import sqlite3
db, ep = sys.argv[1], sys.argv[2]
con = sqlite3.connect(f"file:{db}?mode=ro", uri=True); tc = m.TextCache(con)
bl=[json.loads(l) for l in open('/var/tmp/sprint-filtros-pp/p2-serving.ndjson')]
bl=[d for d in bl if d.get('epoch')==ep and d.get('agent') and len(d['ids_controle'])==10]
agents=sorted({d['agent'] for d in bl})
la={a:m.fetch(con,[f"sessions/{a}/%"],500,0) for a in agents}; lg=m.fetch(con,[],500,0)
mis=collections.Counter(); ex={}
for d in bl:
    a=d['agent']; now=m.js_date_parse_ms(d['ts'],0)
    pa,pg=m.ranked(la[a],now),m.ranked(lg,now)
    cur=m.pick_dedup([pa,pg],[5,5],10,tc,0,frozenset(),True,main_only=False)
    pin=frozenset(r.id for r,_,_ in cur if (r.pain if r.pain is not None else 0.2)>=0.9)
    b={r.id for r,_,_ in m.pick_dedup([pa,pg],[5,5],10,tc,2,pin,True)}
    ctrl=set(d['ids_controle'])
    if not (b<=ctrl and len(ctrl-b)==2):
        mis[a]+=1
        if a not in ex:
            only_r=b-ctrl; only_s=ctrl-b-set(d.get('fresh_added') or [])
            info={}
            for i in list(only_r)+list(only_s):
                row=con.execute("SELECT id,source_file,chunk_type,importance,pain,access_count,last_accessed_at,source_date,created_at,retention_days FROM chunks WHERE id=?",(i,)).fetchone()
                info[i]=row
            sal={r.id:round(s,5) for r,s in pa+pg}
            ex[a]={'ts':d['ts'],'recon_only':sorted(only_r),'served_only_nonfresh':sorted(only_s),'rows':info,'sal':{i:sal.get(i) for i in info},'pinned':sorted(pin),'served':d['ids_controle'],'fresh_added':d.get('fresh_added')}
print(dict(mis)); print(json.dumps(ex,indent=1,default=str)[:6000])
