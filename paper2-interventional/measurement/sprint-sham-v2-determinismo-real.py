#!/usr/bin/env python3
"""sprint-sham-v2-determinismo-real.py — item 4 do diagnostico do aborto do sham v2 (2026-10-04):
o REAL do job (`job/runs/REAL.json`) tem de ter `dose.detalhe` IGUAL ao da calibracao (`cal/REAL-w4.json`).
Medido 2026-10-04 ~10:55Z: detalhe igual True, 5292 = 2646 x 2 doses, sha 4116ae5964cc4d27; procedencia difere so em gerado_em."""
import json, hashlib
a=json.load(open("/var/tmp/sprint-sham-v2-w/job/runs/REAL.json"))
b=json.load(open("/var/tmp/sprint-sham-v2-w/cal/REAL-w4.json"))
da, db = a["dose"]["detalhe"], b["dose"]["detalhe"]
h=lambda x: hashlib.sha256(json.dumps(x, sort_keys=True).encode()).hexdigest()[:16]
print("detalhe igual:", da == db, "n", len(da), len(db), "sha", h(da), h(db))
print("tabela igual:", a["dose"].get("tabela") == b["dose"].get("tabela"))
ka = {k for k in a["dose"] if k != "detalhe"}
print("chaves dose iguais:", ka == {k for k in b["dose"] if k != "detalhe"}, "diferem:", [k for k in ka if a["dose"].get(k) != b["dose"].get(k)])
pa, pb = a["procedencia"], b["procedencia"]
print("procedencia difere em:", sorted(k for k in set(pa)|set(pb) if pa.get(k) != pb.get(k)))
