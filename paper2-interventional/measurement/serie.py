import json, collections
L="/root/.openclaw/logs/p2-serving.ndjson"
rows=[json.loads(l) for l in open(L) if l.strip()]
CORTE="2026-08-26T19:52:07.775Z"
jan=[r for r in rows if r["ts"]<=CORTE and r.get("epoch","")>="2026-08-23"]
print("=== ACHADO 3 do GLM: a taxa e estacionaria? (base POS-GATE) ===")
por=collections.defaultdict(lambda:[0,0,0])
for r in jan:
    d=r["ts"][:10]; por[d][0]+=1
    if r.get("churn",0)>0: por[d][1]+=1
    por[d][2]+=r.get("churn",0)
print(f"  {'dia':<12} {'n':>6} {'com_churn':>10} {'taxa':>9} {'deslocs':>8}")
for d in sorted(por):
    n,pos,desl=por[d]
    print(f"  {d:<12} {n:>6} {pos:>10} {100*pos/n:>8.4f}% {desl:>8}")
n=sum(v[0] for v in por.values()); p=sum(v[1] for v in por.values())
print(f"  {'TOTAL':<12} {n:>6} {p:>10} {100*p/n:>8.4f}% {sum(v[2] for v in por.values()):>8}")
print()
print("  a v1.12 (janela ate 25/08) publicou 102 de 1.267 = 8,05%")
ate25=[r for r in jan if r["ts"][:10] <= "2026-08-25"]
p25=sum(1 for r in ate25 if r.get("churn",0)>0)
print(f"  recomputado ate 25/08 inclusive: {p25} de {len(ate25)} = {100*p25/len(ate25):.4f}%")
