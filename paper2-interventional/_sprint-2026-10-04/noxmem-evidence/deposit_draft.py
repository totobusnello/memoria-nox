#!/usr/bin/env python3
"""Cria (ou retoma) o RASCUNHO do depósito do dataset de evidência do §6 no Zenodo,
reserva o DOI, empacota, sobe o allowlist e confere tudo por readback.
NUNCA publica: o botão "Publish" é do Toto.

Padrão de stanford-deposit/deposit_draft.py, com duas diferenças:
- o payload tem subdiretórios, então vai num zip determinístico (datas fixas, ordem fixa);
  README.md e LICENSE.txt sobem também soltos, para o preview;
- verify_dataset.py roda duas vezes: no payload e na cópia extraída do zip (prova que
  o zip sozinho basta), e a primeira com --manuscript (confere as citações no §6).

Lições aplicadas: só API InvenioRDM (`/api/records`), readback com
`Accept: application/vnd.inveniordm.v1+json` campo a campo, `publisher` obrigatório.
Token: ZENODO_TOKEN no ambiente (nunca impresso).
Uso: python3 deposit_draft.py [AAAA-MM-DD]
"""
import hashlib, json, os, pathlib, shutil, subprocess, sys, tempfile, urllib.error, urllib.request, zipfile

HERE = pathlib.Path(__file__).resolve().parent
PAY = HERE / "payload"
REPO = HERE.parents[2]
MANUSCRIPT = REPO / "paper" / "paper-tecnico-nox-mem.md"
API = "https://zenodo.org/api"
TOK = os.environ["ZENODO_TOKEN"]
RDM = "application/vnd.inveniordm.v1+json"
PUB_DATE = sys.argv[1] if len(sys.argv) > 1 else "2026-10-04"
VERSION = "1.0.0"
TOP = f"nox-mem-section6-evidence-{VERSION}"
ZIP = HERE / f"{TOP}.zip"
UPLOAD = {"README.md": PAY / "README.md", "LICENSE.txt": PAY / "LICENSE.txt", ZIP.name: ZIP}


def call(method, path, body=None, ctype="application/json", accept=RDM, raw=None):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(API + path, data=data, method=method)
    req.add_header("Authorization", "Bearer " + TOK)
    req.add_header("Accept", accept)
    if data is not None:
        req.add_header("Content-Type", ctype)
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            txt = r.read()
            return json.loads(txt) if txt else {}
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} em {method} {path}: {e.read()[:800]!r}")


def payload_files():
    return sorted(p for p in PAY.rglob("*") if p.is_file() and "__pycache__" not in p.parts
                  and p.name != ".DS_Store")


def verify(cwd, *extra):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    v = subprocess.run([sys.executable, "verify_dataset.py", *extra], cwd=cwd, capture_output=True, text=True, env=env)
    last = v.stdout.strip().splitlines()[-1] if v.stdout.strip() else v.stderr[-400:]
    return v.returncode, last


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

# 3. DOI no README, SHA256SUMS regenerado, verificação no payload
readme = PAY / "README.md"
txt = readme.read_text()
if "<<DOI>>" in txt:
    readme.write_text(txt.replace("<<DOI>>", doi))
if "<<DOI>>" in readme.read_text() or doi not in readme.read_text():
    sys.exit("README sem o DOI — nada foi enviado")
for c in PAY.rglob("__pycache__"):
    shutil.rmtree(c)
sums = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(PAY)}"
        for p in payload_files() if p.name != "SHA256SUMS"]
(PAY / "SHA256SUMS").write_text("\n".join(sums) + "\n")
rc, last = verify(PAY, "--manuscript", str(MANUSCRIPT))
print("verify_dataset (payload + manuscrito):", last)
if rc != 0:
    sys.exit("verify_dataset falhou — nada foi enviado")

# 4. zip determinístico + verificação na cópia extraída
with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for p in payload_files():
        zi = zipfile.ZipInfo(f"{TOP}/{p.relative_to(PAY)}", date_time=(2026, 10, 4, 0, 0, 0))
        zi.external_attr = 0o644 << 16
        zi.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(zi, p.read_bytes(), compresslevel=9)
with tempfile.TemporaryDirectory() as td:
    with zipfile.ZipFile(ZIP) as z:
        z.extractall(td)
    rc, last = verify(pathlib.Path(td) / TOP)
print("verify_dataset (zip extraído):", last)
if rc != 0:
    sys.exit("verify_dataset falhou no zip extraído — nada foi enviado")
print(f"zip: {ZIP.name} {ZIP.stat().st_size} bytes sha256 {hashlib.sha256(ZIP.read_bytes()).hexdigest()}")

# 5. arquivos (substitui o que já existir com o mesmo nome; remove o que estiver fora do allowlist)
have = {e["key"] for e in call("GET", f"/records/{rid}/draft/files").get("entries", [])}
for k in sorted(have - set(UPLOAD)):
    call("DELETE", f"/records/{rid}/draft/files/{k}")
for k, p in UPLOAD.items():
    if k in have:
        call("DELETE", f"/records/{rid}/draft/files/{k}")
    call("POST", f"/records/{rid}/draft/files", [{"key": k}])
    call("PUT", f"/records/{rid}/draft/files/{k}/content", ctype="application/octet-stream", raw=p.read_bytes())
    call("POST", f"/records/{rid}/draft/files/{k}/commit")

# 5b. preview padrão (só existe depois do upload)
payload["files"] = {"enabled": True, "default_preview": "README.md"}
call("PUT", f"/records/{rid}/draft", payload)

# 6. readback
rb = call("GET", f"/records/{rid}/draft")
m = rb["metadata"]
probs = []
for f in ("title", "version", "publication_date", "description", "publisher"):
    if m.get(f) != meta.get(f):
        probs.append(f"metadata.{f} difere")
if [c["person_or_org"]["name"] for c in m.get("creators", [])] != [c["person_or_org"]["name"] for c in meta["creators"]]:
    probs.append("creators difere")
orcid = [i.get("identifier") for c in m.get("creators", []) for i in c["person_or_org"].get("identifiers", [])]
if orcid != ["0009-0007-5911-8141"]:
    probs.append(f"ORCID difere: {orcid}")
if [r.get("id") for r in m.get("rights", [])] != [r["id"] for r in meta["rights"]]:
    probs.append("rights difere")
if (m.get("resource_type") or {}).get("id") != meta["resource_type"]["id"]:
    probs.append("resource_type difere")
if len(m.get("subjects", [])) != len(meta["subjects"]):
    probs.append("subjects difere")
got_rel = sorted((r["identifier"], r["relation_type"]["id"]) for r in m.get("related_identifiers", []))
want_rel = sorted((r["identifier"], r["relation_type"]["id"]) for r in meta["related_identifiers"])
if got_rel != want_rel:
    probs.append(f"related_identifiers difere: {got_rel}")
ents = {e["key"]: e for e in call("GET", f"/records/{rid}/draft/files").get("entries", [])}
for k, p in UPLOAD.items():
    e = ents.get(k)
    md5 = "md5:" + hashlib.md5(p.read_bytes()).hexdigest()
    if not e or e.get("checksum") != md5 or e.get("status") != "completed":
        probs.append(f"arquivo {k}: {'ausente' if not e else (e.get('status'), e.get('checksum'))}")
extra = set(ents) - set(UPLOAD)
if extra:
    probs.append(f"arquivos fora do allowlist no rascunho: {sorted(extra)}")
if (rb.get("pids") or {}).get("doi", {}).get("identifier") != doi:
    probs.append("DOI do rascunho difere do DOI no README")
print("DOI no rascunho:", (rb.get("pids") or {}).get("doi"))
print("relações:", got_rel)
for k in UPLOAD:
    e = ents.get(k) or {}
    print(f"  {k}: {e.get('size')} bytes {e.get('checksum')} {e.get('status')}")
print("arquivos no rascunho:", len(ents), "| allowlist:", len(UPLOAD))
print("published:", rb.get("is_published"), "| status:", rb.get("status"))
print("PROBLEMAS:" if probs else "readback OK — nada divergente", *probs, sep="\n  ")
print("rascunho para revisar e publicar: https://zenodo.org/uploads/" + rid)
