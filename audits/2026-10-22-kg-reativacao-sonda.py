import json, subprocess, urllib.parse
qs = json.load(open("/root/medicoes/2026-10-22-kg-serve/gold-queries-55.json"))
alvo = [q for q in qs if q["id"] in (92, 91, 55, 63)]
for item in alvo:
    url = ("http://127.0.0.1:18802/api/search?track=false&limit=10&q="
           + urllib.parse.quote(item["q"]))
    out = subprocess.run(["curl", "-s", "-m", "30", "-H", "X-Agent-Name: probe-reativacao", url],
                         capture_output=True, text=True).stdout
    d = json.loads(out)
    res = d.get("results") if isinstance(d, dict) else d
    vf = d.get("vaultFacts") if isinstance(d, dict) else None
    corp = {}
    for r in (res or []):
        f = r.get("source_file") or ""
        c = "VAULT" if f.startswith("memory/mac-docs/") else "workspace"
        corp[c] = corp.get(c, 0) + 1
    n = 0 if not vf else len([l for l in vf.splitlines() if l and not l.startswith("<")])
    qid = item["id"]
    print("query %3d | busca: %-32s | triplas servidas: %d" % (qid, corp, n))
