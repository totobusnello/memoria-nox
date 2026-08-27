import json, collections, hashlib
L = "/root/.openclaw/logs/p2-serving.ndjson"
raw = open(L, "rb").read()
rows = [json.loads(l) for l in raw.decode().splitlines() if l.strip()]
c = collections.Counter(r.get("churn", 0) for r in rows)
nz = sum(v for k, v in c.items() if k > 0)
out = {
    "arquivo": L,
    "sha256_do_arquivo": hashlib.sha256(raw).hexdigest(),
    "bytes": len(raw),
    "total_linhas": len(rows),
    "primeira_ts": rows[0]["ts"],
    "ultima_ts": rows[-1]["ts"],
    "churn_dist": dict(sorted(c.items())),
    "churn_positivo": nz,
    "churn_positivo_pct": round(100 * nz / len(rows), 4),
    "soma_partes_igual_total": sum(c.values()) == len(rows),
    "w_dist": dict(collections.Counter(r.get("w") for r in rows)),
    "servido_dist": dict(collections.Counter(r.get("servido") for r in rows)),
    "linhas_com_designated_ids": sum(1 for r in rows if "designated_ids" in r),
}
print(json.dumps(out, ensure_ascii=False, indent=2))
