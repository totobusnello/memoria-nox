#!/usr/bin/env python3
"""
irmaos-no-segundo.py — mede quantos briefs dividem o SEGUNDO de `served_at` com
outro brief. É a EXPOSIÇÃO ao defeito 3.2 de REPLAY-OPORTUNIDADE-2026-08-27.md
(resolução de segundo em `brief_log.served_at`), não a taxa de erro: o dano só
se materializa quando os picks do irmão intersectam o pool de cobertura.
"""
import collections, json, sys

f = sys.argv[1]
rows = [json.loads(l) for l in open(f) if l.strip()]
rows = [r for r in rows if r.get("tag") == "p2_outcome" and len(r.get("ids_controle", [])) == 10]
seg = collections.Counter(r["ts"][:19] for r in rows)
irmaos = [r for r in rows if seg[r["ts"][:19]] > 1]
ch = [r for r in rows if r["churn"] > 0]
print(json.dumps({
    "briefs": len(rows),
    "dividem_o_segundo": len(irmaos),
    "pct": round(100 * len(irmaos) / len(rows), 1),
    "com_churn": len(ch),
    "com_churn_que_dividem": len([r for r in ch if seg[r["ts"][:19]] > 1]),
    "por_agente": dict(collections.Counter(r["agent"] for r in irmaos)),
}, indent=2, ensure_ascii=False))
