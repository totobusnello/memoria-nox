import json, collections, hashlib
L="/root/.openclaw/logs/p2-serving.ndjson"
raw=open(L,"rb").read()
rows=[json.loads(l) for l in raw.decode().splitlines() if l.strip()]
REGRA="2026-08-26T20:28:00Z"   # drop-in da designacao entrou
print(f"arquivo: {len(rows)} linhas  sha256 {hashlib.sha256(raw).hexdigest()[:16]}...")
print(f"ultima ts: {rows[-1]['ts']}")
antes=[r for r in rows if r["ts"]<REGRA and r.get("epoch","")>="2026-08-23"]
depois=[r for r in rows if r["ts"]>=REGRA]
def bloco(sub,nome):
    if not sub: print(f"  {nome}: vazio"); return
    n=len(sub); pos=sum(1 for r in sub if r.get("churn",0)>0); desl=sum(r.get("churn",0) for r in sub)
    di=[r for r in sub if "designated_ids" in r]
    bb=sum(1 for r in sub if r.get("boost_by_id"))
    print(f"  {nome:<34} n={n:<5} com_churn={pos:<4} ({100*pos/n:.4f}%) desl={desl:<4} com_designated_ids={len(di)} com_boost={bb}")
    return n,pos
print()
print("=== REGRA VELHA (pos-gate, ate 20:28Z) vs REGRA NOVA ===")
bloco(antes,  "velha (w_min, pos-gate)")
bloco(depois, "NOVA (sorteio com seed)")
print()
print("=== a nova, por hora ===")
por=collections.defaultdict(lambda:[0,0])
for r in depois:
    h=r["ts"][:13]; por[h][0]+=1
    if r.get("churn",0)>0: por[h][1]+=1
for h in sorted(por):
    n,p=por[h]; print(f"  {h}Z  n={n:<4} com_churn={p:<3} {100*p/n:6.2f}%")
print()
d=[r for r in depois if "designated_ids" in r]
if d:
    tam=collections.Counter(len(r["designated_ids"]) for r in d)
    nb=collections.Counter(len(r.get("boost_by_id",{})) for r in d)
    print(f"=== integridade: designated_ids sempre 19? {dict(tam)}")
    print(f"=== boost_by_id (quantos designados no pool E maduros): {dict(sorted(nb.items()))}")
