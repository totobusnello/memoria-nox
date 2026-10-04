#!/usr/bin/env python3
"""Recomputes the numbers REVIEW-B-rc2-2026-10-04.md cites that are not in the manuscript.
Reads only the local ballast ~/Backups/paper2-ensaio-2026-09-21/. Writes nothing."""
import json, os
B = os.path.expanduser("~/Backups/paper2-ensaio-2026-09-21/")
itt = json.load(open(B + "ITT-2026-09-21.json"))
c = itt["primario"]["por_braco"]["control"]["H1_densidade"]
t = itt["primario"]["por_braco"]["treatment"]["H1_densidade"]
ts = itt["sensibilidade"]["por_braco"]["treatment"]["H1_densidade"]
for nome, tt in (("locked", t), ("post-hoc sem 09-14", ts)):
    rel = 1 - tt / c
    print(f"H1 {nome}: control {c:.3f} treatment {tt:.3f} relative reduction {rel:.4f}"
          f" | /0.0314 = {rel/0.0314:.2f}x | /0.0685 = {rel/0.0685:.2f}x")
h1c_c = itt["primario"]["por_braco"]["control"]["H1c_prop"]
h1c_t = itt["primario"]["por_braco"]["treatment"]["H1c_prop"]
print(f"H1c relative difference {(h1c_t-h1c_c)/h1c_c:.4f}")
D = set(json.load(open(B + "DESIGNATION-2026-08-26.json"))["designados_ids"])
pre = post = dpre = dpost = 0
for line in open(B + "p2-serving.ndjson"):
    r = json.loads(line)
    if r.get("epoch") != "2026-09-20" or r.get("tag") != "p2_outcome":
        continue
    ids = r.get("ids_tratado") if r.get("servido") == "tratado" else r.get("ids_controle")
    hit = bool(D & set(ids or []))
    if r["ts"] < "2026-09-20T22:51:23":
        pre += 1; dpre += hit
    else:
        post += 1; dpost += hit
print(f"09-20 briefs before expiry {pre} (with designated {dpre}, {dpre/pre:.4f});"
      f" after expiry {post} (with designated {dpost}); all {(dpre+dpost)/(pre+post):.4f}")
