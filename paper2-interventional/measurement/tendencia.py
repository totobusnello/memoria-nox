import json, collections
from math import sqrt
L="/root/.openclaw/logs/p2-serving.ndjson"
REGRA="2026-08-26T20:28:00Z"; T_FIM="2026-08-27T09:00:00Z"; GATE="2026-08-23"
rows=[json.loads(l) for l in open(L,encoding="utf-8") if l.strip()]
def sonda(r):
    a=r.get("agent"); return a is None or a==""
def wilson(k,n,z=1.959963985):
    if n==0: return (0,0)
    p=k/n; d=1+z*z/n; c=p+z*z/(2*n); h=z*sqrt(p*(1-p)/n+z*z/(4*n*n)); return ((c-h)/d,(c+h)/d)
print("=== REGRA VELHA (pos-gate), por DIA, sondas excluidas ===")
por=collections.defaultdict(lambda:[0,0])
for r in rows:
    if r["ts"]>=REGRA or r.get("epoch","")<GATE or sonda(r): continue
    d=r["ts"][:10]; por[d][0]+=1
    if r.get("churn",0)>0: por[d][1]+=1
tn=tk=0
for d in sorted(por):
    n,k=por[d]; tn+=n; tk+=k; lo,hi=wilson(k,n)
    print("  %s  n=%-5d churn=%-4d %7.4f%%  Wilson [%.2f; %.2f]"%(d,n,k,100*k/n,100*lo,100*hi))
print("  SOMA %d/%d = %.4f%%"%(tk,tn,100*tk/tn))
print()
print("=== ultimo dia da regra velha vs regra nova (segmentos ADJACENTES) ===")
ult=sorted(por)[-1]; kv,nv=por[ult][1],por[ult][0]
dep=[r for r in rows if REGRA<=r["ts"]<T_FIM and not sonda(r)]
kn=sum(1 for r in dep if r.get("churn",0)>0); nn=len(dep)
print("  velha, dia %s : %d/%d = %.4f%%"%(ult,kv,nv,100*kv/nv))
print("  nova, janela  : %d/%d = %.4f%%"%(kn,nn,100*kn/nn))
print()
print("=== a nova, por dia ===")
pn=collections.defaultdict(lambda:[0,0])
for r in dep:
    d=r["ts"][:10]; pn[d][0]+=1
    if r.get("churn",0)>0: pn[d][1]+=1
for d in sorted(pn):
    n,k=pn[d]; print("  %s  n=%-5d churn=%-4d %7.4f%%"%(d,n,k,100*k/n))
