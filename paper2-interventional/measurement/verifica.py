import json, collections
CORTE = "2026-08-26T19:52:07.775Z"
rows = [json.loads(l) for l in open("/root/.openclaw/logs/p2-serving.ndjson") if l.strip()]
novas = [r for r in rows if r["ts"] > CORTE]
print("linhas_novas", len(novas))
for r in novas[:4]:
    print("  ts=%s churn=%s designated_ids=%r boost_by_id=%r" % (
        r["ts"], r.get("churn"),
        r.get("designated_ids", "<AUSENTE>"), r.get("boost_by_id", "<AUSENTE>")))
if novas:
    pos = sum(1 for r in novas if r.get("churn", 0) > 0)
    tem_di = sum(1 for r in novas if "designated_ids" in r)
    tem_bb = sum(1 for r in novas if "boost_by_id" in r)
    print("churn_positivo %d de %d" % (pos, len(novas)))
    print("com_designated_ids %d de %d" % (tem_di, len(novas)))
    print("com_boost_by_id %d de %d" % (tem_bb, len(novas)))
    print("VEREDITO", "OK" if pos == 0 and tem_di == len(novas) and tem_bb == len(novas) else "DIVERGENTE")
