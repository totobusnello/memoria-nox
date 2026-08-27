import json, collections
CORTE = "2026-08-26T20:28:00Z"
ESPERADOS = {308216,308218,308222,308230,308238,308240,308256,308264,308270,
             308274,308280,308284,308286,308292,308296,308300,308306,308312,308316}
rows = [json.loads(l) for l in open("/root/.openclaw/logs/p2-serving.ndjson") if l.strip()]
novas = [r for r in rows if r["ts"] > CORTE]
print("linhas_apos_o_drop_in", len(novas))
if not novas:
    print("(nenhum brief servido ainda — aguardar trafego)")
else:
    for r in novas[:3]:
        di = r.get("designated_ids", "<AUSENTE>")
        bb = r.get("boost_by_id", "<AUSENTE>")
        print("  ts=%s churn=%s n_designados=%s boost_by_id=%s" % (
            r["ts"], r.get("churn"), len(di) if isinstance(di, list) else di, bb))
    ok19 = all(set(r.get("designated_ids", [])) == ESPERADOS for r in novas)
    subset = all(set(r.get("boost_by_id", {}).keys()) <= {str(i) for i in ESPERADOS} for r in novas)
    pos = sum(1 for r in novas if r.get("churn", 0) > 0)
    print("designated_ids == os 19 registrados, em TODAS:", ok19)
    print("boost_by_id ⊆ designados, em TODAS:", subset)
    print("churn positivo: %d de %d" % (pos, len(novas)))
