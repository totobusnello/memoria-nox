#!/usr/bin/env python3
"""Nova VERSÃO (v1.0.6) do registro do nox-mem no Zenodo, a partir da v1.0.5 publicada.
Cria o rascunho da versão, reserva o DOI, sobe o PDF e confere por readback.
NUNCA publica: o botão "Publish" é do Toto.

Lições aplicadas (feedback_rdm_put_silently_drops_legacy_shaped_metadata):
- base de escrita = a versão PUBLICADA lida em RDM e normalizada para o shape de escrita;
- PUT só com {access, files, metadata}; readback campo a campo contra a referência;
- DOI reservado explicitamente (o PUBLISHED.md registra o quase-registro sem DOI).
Token: ZENODO_TOKEN no ambiente (nunca impresso). `.draft-id-v106` retoma o mesmo rascunho.
"""
import hashlib, json, os, pathlib, sys, urllib.request, urllib.error

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
PDF = REPO / "paper/build/paper-tecnico-nox-mem.pdf"
PREV = "23146389"  # v1.0.5 publicada
API = "https://zenodo.org/api"
TOK = os.environ["ZENODO_TOKEN"]
RDM = "application/vnd.inveniordm.v1+json"
VERSION, DATE = "1.0.6", "2026-10-04"
ORCID = "0009-0007-5911-8141"

V106 = """<h3>What changed in v1.0.6 (2026-10-04)</h3>
<ul>
  <li>Scoring correction: repeated retrieved ids now count once; nine Mem0 values in Section 6
      change by at most 0.004 (the largest is the LongMemEval margin, +0.119 to +0.123, as Mem0's
      LongMemEval nDCG@10 goes from 0.4061 to 0.4030), no ranking or sign changes. Section 6.3.2 points to the evidence dataset 10.5281/zenodo.23146656.</li>
  <li>Wording corrections in Section 6.3.2, and in the passages that repeat its conclusions
      (6.5, 6.7, 7.1, 8), after independent reviews. The net effect of the corpus-collision
      confound (e) is stated as not isolated, instead of as running against nox-mem. The
      task-type ablation is described as removing task types from both arms, with nox-mem's lead
      persisting; it no longer claims to rule out or bound the task-type contribution, since the
      generic run also lacked 23 of 2,370 gold chunks and logged 33 dense-search errors. The
      evidence dataset is described as a verifier of 132 Section 6 values plus three arithmetic
      differences, with twelve groups of figures it cannot recompute. No measured result changed
      beyond the scoring correction above.</li>
</ul>

"""


def call(method, path, body=None, ctype="application/json", raw=None):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(API + path, data=data, method=method)
    req.add_header("Authorization", "Bearer " + TOK)
    req.add_header("Accept", RDM)
    if data is not None:
        req.add_header("Content-Type", ctype)
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            t = r.read()
            return json.loads(t) if t else {}
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} em {method} {path}: {e.read()[:800]!r}")


def ids(x):
    return {"id": x["id"]} if isinstance(x, dict) and "id" in x else x


# Frases herdadas da v1.0.2 que a v1.0.3 corrige (CHANGELOG, partes C e E). Cada uma tem de
# aparecer exatamente 1x na descrição publicada; se não, o script para em vez de publicar texto velho.
INHERITED = []  # a v1.0.3 publicada já é a base corrigida

# referência: v1.0.2 publicada, em RDM, normalizada para escrita
ref = call("GET", f"/records/{PREV}")
m0 = ref["metadata"]
desc = m0["description"]
for old, new in INHERITED:
    if desc.count(old) != 1:
        sys.exit(f"esperava 1x a frase herdada {old[:60]!r}, achei {desc.count(old)}")
    desc = desc.replace(old, new)
# Parte G (2026-10-04): "pre-registered" -> "pre-specified" onde a descricao herdada o tiver.
# Contagem livre (0 ou mais) porque a descricao da v1.0.2 nao esta neste repositorio; depois,
# a guarda exige que nenhuma ocorrencia sobreviva, em vez de confiar na troca.
for old, new in (("pre-registered", "pre-specified"), ("pre-register ", "pre-specify "),
                 ("Pre-registered", "Pre-specified"), ("pre-registration", "pre-specification")):
    print(f"troca herdada {old!r}: {desc.count(old)}x")
    desc = desc.replace(old, new)
if "pre-regist" in desc.lower():
    sys.exit("a descricao herdada ainda diz pre-regist*: conferir a mao antes de seguir")
meta = {
    "resource_type": ids(m0["resource_type"]),
    "title": m0["title"],
    "publication_date": DATE,
    "version": VERSION,
    "creators": m0["creators"],
    "rights": [ids(r) for r in m0["rights"]],
    "subjects": m0["subjects"],
    "languages": [ids(l) for l in m0.get("languages", [])],
    "related_identifiers": [
        {**{k: v for k, v in r.items() if k not in ("relation_type", "resource_type")},
         "relation_type": ids(r["relation_type"]),
         **({"resource_type": ids(r["resource_type"])} if "resource_type" in r else {})}
        for r in m0.get("related_identifiers", [])],
    "description": desc.replace("<h3>What changed in v1.0.5", V106 + "<h3>What changed in v1.0.5", 1),
    "publisher": m0.get("publisher", "Zenodo"),
}
if V106 not in meta["description"]:
    sys.exit("âncora 'What changed in v1.0.5' não achada na descrição")
if any(o in meta["description"] or n not in meta["description"] for o, n in INHERITED):
    sys.exit("uma frase herdada da v1.0.2 não foi trocada")
for c in meta["creators"]:
    po = c["person_or_org"]
    if po.get("family_name") == "Busnello" and not po.get("identifiers"):
        po["identifiers"] = [{"scheme": "orcid", "identifier": ORCID}]
    for a in c.get("affiliations", []):
        a.pop("id", None) if not a.get("id") else None

# 1. rascunho da nova versão
idf = HERE / ".draft-id-v106"
if idf.exists():
    rid = idf.read_text().strip()
    print("retomando rascunho", rid)
else:
    rid = call("POST", f"/records/{PREV}/versions")["id"]
    idf.write_text(rid)
    print("rascunho de nova versão criado", rid)
call("PUT", f"/records/{rid}/draft", {"access": ref["access"], "files": {"enabled": True}, "metadata": meta})

# 2. DOI
d = call("GET", f"/records/{rid}/draft")
doi = (d.get("pids") or {}).get("doi", {}).get("identifier")
if not doi:
    doi = call("POST", f"/records/{rid}/draft/pids/doi")["pids"]["doi"]["identifier"]
print("DOI reservado:", doi)

# 3. PDF (só ele; apaga qualquer arquivo herdado)
key = PDF.name
for e in call("GET", f"/records/{rid}/draft/files").get("entries", []):
    call("DELETE", f"/records/{rid}/draft/files/{e['key']}")
call("POST", f"/records/{rid}/draft/files", [{"key": key}])
call("PUT", f"/records/{rid}/draft/files/{key}/content", ctype="application/octet-stream", raw=PDF.read_bytes())
call("POST", f"/records/{rid}/draft/files/{key}/commit")

# 4. readback contra a referência + as mudanças pretendidas
rb = call("GET", f"/records/{rid}/draft")
m = rb["metadata"]
probs = []
for f in ("title", "version", "publication_date", "description", "publisher"):
    if m.get(f) != meta[f]:
        probs.append(f"{f} difere")
if len(m.get("creators", [])) != len(meta["creators"]) or \
   m["creators"][0]["person_or_org"].get("identifiers", [{}])[0].get("identifier") != ORCID:
    probs.append("creators/ORCID difere")
for f in ("rights", "subjects", "languages", "related_identifiers"):
    if len(m.get(f, [])) != len(m0.get(f, [])):
        probs.append(f"{f}: {len(m.get(f, []))} vs {len(m0.get(f, []))} na v1.0.2")
if (m.get("resource_type") or {}).get("id") != m0["resource_type"]["id"]:
    probs.append("resource_type difere")
ents = call("GET", f"/records/{rid}/draft/files").get("entries", [])
md5 = "md5:" + hashlib.md5(PDF.read_bytes()).hexdigest()
if [e["key"] for e in ents] != [key] or ents[0].get("checksum") != md5 or ents[0].get("status") != "completed":
    probs.append(f"arquivos: {[(e['key'], e.get('checksum'), e.get('status')) for e in ents]}")
print("PDF:", key, md5)
print("published:", rb.get("is_published"), "| status:", rb.get("status"))
print("PROBLEMAS:" if probs else "readback OK — nada divergente", *probs, sep="\n  ")
print("rascunho para revisar e publicar: https://zenodo.org/uploads/" + rid)
