import json, collections, hashlib
L="/root/.openclaw/logs/p2-serving.ndjson"
raw=open(L,"rb").read()
rows=[json.loads(l) for l in raw.decode().splitlines() if l.strip()]
CORTE="2026-08-26T19:52:07.775Z"          # janela FECHADA, a mesma do baseline
jan=[r for r in rows if r["ts"]<=CORTE]
def taxa(sub, nome):
    n=len(sub); pos=sum(1 for r in sub if r.get("churn",0)>0); desl=sum(r.get("churn",0) for r in sub)
    print(f"  {nome:<42} n={n:<5} com_churn={pos:<4} ({100*pos/n if n else 0:.4f}%)  deslocamentos={desl}")
    return n,pos,desl
print("=== a janela fechada, 3 bases diferentes ===")
taxa(jan, "TODAS as decisoes (o que eu publiquei)")
posgate=[r for r in jan if r.get("epoch","") >= "2026-08-23"]
taxa(posgate, "POS-GATE (epochs >= 23/08, base da v1.12)")
pregate=[r for r in jan if r.get("epoch","") < "2026-08-23"]
taxa(pregate, "PRE-GATE (epochs < 23/08)")
print()
print("=== a v1.12 diz: 102 de 1.267 = 8,1%, com 111 deslocamentos ===")
print("=== confere com a base pos-gate? ===")
n,pos,desl=taxa(posgate, "recomputado agora")
print()
print(f"sha256 da janela {hashlib.sha256(raw).hexdigest()[:16]}...  (arquivo cresceu desde: total {len(rows)} linhas)")
print(f"epochs distintos na janela: {sorted({r.get('epoch') for r in jan})}")
