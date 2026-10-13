#!/usr/bin/env python3
"""Cria (ou retoma) o RASCUNHO do depósito no Zenodo, reserva o DOI, sobe o allowlist
e confere tudo por readback. NUNCA publica: o botão "Publish" é do Toto.

Lições aplicadas (memória feedback_rdm_put_silently_drops_legacy_shaped_metadata):
- só API InvenioRDM (`/api/records`), nunca a legada;
- readback com `Accept: application/vnd.inveniordm.v1+json` e comparação campo a campo;
- `publisher` obrigatório para registrar o DOI.
Token: variável de ambiente ZENODO_TOKEN (nunca impresso).
"""
import hashlib, json, os, pathlib, subprocess, sys, urllib.request, urllib.error

HERE = pathlib.Path(__file__).resolve().parent
PAY = HERE / "payload"
API = "https://zenodo.org/api"
TOK = os.environ["ZENODO_TOKEN"]
RDM = "application/vnd.inveniordm.v1+json"
PUB_DATE = sys.argv[1] if len(sys.argv) > 1 else "2026-10-04"


def call(method, path, body=None, ctype="application/json", accept=RDM, raw=None):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(API + path, data=data, method=method)
    req.add_header("Authorization", "Bearer " + TOK)
    req.add_header("Accept", accept)
    if data is not None:
        req.add_header("Content-Type", ctype)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            txt = r.read()
            return json.loads(txt) if txt else {}
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} em {method} {path}: {e.read()[:800]!r}")


meta_doc = json.loads((HERE / "zenodo-metadata.json").read_text())
meta = meta_doc["metadata"]
meta["publication_date"] = PUB_DATE
payload = {"access": meta_doc["access"], "files": {"enabled": True}, "metadata": meta}

# 1. rascunho
idf = HERE / ".draft-id"
if idf.exists():
    rid = idf.read_text().strip()
    print("retomando rascunho", rid)
    call("PUT", f"/records/{rid}/draft", payload)
else:
    rec = call("POST", "/records", payload)
    rid = rec["id"]
    idf.write_text(rid)
    print("rascunho criado", rid)

# 2. DOI reservado
d = call("GET", f"/records/{rid}/draft")
doi = (d.get("pids") or {}).get("doi", {}).get("identifier")
if not doi:
    d = call("POST", f"/records/{rid}/draft/pids/doi")
    doi = d["pids"]["doi"]["identifier"]
print("DOI reservado:", doi)

# 3. DOI no README, SHA256SUMS regenerado, verificação
readme = PAY / "README.md"
txt = readme.read_text()
if "<<DOI>>" in txt:
    readme.write_text(txt.replace("<<DOI>>", doi))
upload = [l.strip() for l in (HERE / "UPLOAD-LIST.txt").read_text().splitlines() if l.strip()]
sums = []
for k in upload:
    if k == "SHA256SUMS":
        continue
    sums.append(f"{hashlib.sha256((PAY / k).read_bytes()).hexdigest()}  {k}")
(PAY / "SHA256SUMS").write_text("\n".join(sums) + "\n")
v = subprocess.run([sys.executable, "verify_dataset.py"], cwd=PAY, capture_output=True, text=True)
print("verify_dataset:", v.stdout.strip().splitlines()[-1] if v.stdout.strip() else v.stderr[-400:])
if v.returncode != 0:
    sys.exit("verify_dataset falhou — nada foi enviado")

# 4. arquivos (substitui o que já existir com o mesmo nome)
have = {e["key"] for e in call("GET", f"/records/{rid}/draft/files").get("entries", [])}
for k in upload:
    if k in have:
        call("DELETE", f"/records/{rid}/draft/files/{k}")
    call("POST", f"/records/{rid}/draft/files", [{"key": k}])
    call("PUT", f"/records/{rid}/draft/files/{k}/content", ctype="application/octet-stream",
         raw=(PAY / k).read_bytes())
    call("POST", f"/records/{rid}/draft/files/{k}/commit")

# 5. readback
rb = call("GET", f"/records/{rid}/draft")
m = rb["metadata"]
probs = []
for f in ("title", "version", "publication_date", "description", "publisher"):
    if m.get(f) != meta.get(f):
        probs.append(f"metadata.{f} difere")
if [c["person_or_org"]["name"] for c in m.get("creators", [])] != [c["person_or_org"]["name"] for c in meta["creators"]]:
    probs.append("creators difere")
if [r.get("id") for r in m.get("rights", [])] != [r["id"] for r in meta["rights"]]:
    probs.append("rights difere")
if (m.get("resource_type") or {}).get("id") != meta["resource_type"]["id"]:
    probs.append("resource_type difere")
if len(m.get("subjects", [])) != len(meta["subjects"]):
    probs.append("subjects difere")
if len(m.get("related_identifiers", [])) != len(meta["related_identifiers"]):
    probs.append("related_identifiers difere")
ents = {e["key"]: e for e in call("GET", f"/records/{rid}/draft/files").get("entries", [])}
for k in upload:
    e = ents.get(k)
    md5 = "md5:" + hashlib.md5((PAY / k).read_bytes()).hexdigest()
    if not e or e.get("checksum") != md5 or e.get("status") != "completed":
        probs.append(f"arquivo {k}: {'ausente' if not e else (e.get('status'), e.get('checksum'))}")
extra = set(ents) - set(upload)
if extra:
    probs.append(f"arquivos fora do allowlist no rascunho: {sorted(extra)}")
print("arquivos no rascunho:", len(ents), "| allowlist:", len(upload))
print("published:", rb.get("is_published"), "| status:", rb.get("status"))
print("PROBLEMAS:" if probs else "readback OK — nada divergente", *probs, sep="\n  ")
print("rascunho para revisar e publicar: https://zenodo.org/uploads/" + rid)
