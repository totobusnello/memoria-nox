#!/usr/bin/env python3
"""Preenche o RASCUNHO da v1.1 do Paper A no Zenodo e confere tudo por readback.

⛔ Este script NÃO publica e não contém a chamada de publish. Publicar é manual,
irreversível, e cabe ao autor depois de ler DRAFT-READBACK.md.

Pré-condição: o rascunho já existe (POST /api/records/22181415/versions) e o DOI
foi reservado; o id está em .draft-id-v1.1 (gitignored).

Passos, todos idempotentes:
  1. metadata (InvenioRDM, PUT /draft) a partir da metadata PUBLICADA da v1.0,
     preservando o bloco `pids` do rascunho (sem ele o DOI reservado se perderia);
  2. files-import: os 13 arquivos da v1.0 copiados no servidor, byte a byte;
  3. os 5 arquivos novos, uma chave por vez (em lote dá 400), com md5 comparado
     e reenvio se divergir;
  4. readback campo a campo e md5 de CADA arquivo, nas duas direções; os zips
     são abertos e cada membro conferido contra MANIFEST-v1.1.json.
Sai 1 em qualquer divergência.
"""
import hashlib
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
API = "https://zenodo.org/api"
V10 = "22181415"
ORCID = "0009-0007-5911-8141"
NOVOS = ["spare-capacity-narrow-surface-v1.1.pdf", "spare-capacity-narrow-surface-v1.1.md", "MANIFEST-v1.1.json",
         "artefatos-v1.1.zip", "scripts-v1.1.zip"]
# Chaves com o nome antigo do manuscrito (renomeado em 2026-10-05, mesmos bytes). Saem do
# rascunho no passo 3 e o readback exige que não existam mais.
OBSOLETOS = ["MANUSCRIPT-v1.1.pdf", "MANUSCRIPT-v1.1.md"]


def token():
    t = os.environ.get("ZENODO_TOKEN", "").strip()
    if not t:
        p = pathlib.Path.home() / ".config/secrets/ZENODO_TOKEN"
        t = p.read_text().strip() if p.exists() else ""
    if not t:
        sys.exit("sem ZENODO_TOKEN")
    return t


TOK = token()


def req(method, path, body=None, ctype="application/json", accept="application/vnd.inveniordm.v1+json"):
    url = path if path.startswith("http") else API + path
    data = None
    if body is not None:
        data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Authorization", f"Bearer {TOK}")
    r.add_header("Accept", accept)
    if data is not None:
        r.add_header("Content-Type", ctype)
    try:
        with urllib.request.urlopen(r, timeout=300) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw and raw[:1] in b"{[" else raw)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw[:500]


def md5(p):
    return hashlib.md5(pathlib.Path(p).read_bytes()).hexdigest()


def main():
    assert not any("publish" in a for a in sys.argv), "este script não publica"
    draft = (HERE / ".draft-id-v1.1").read_text().strip()
    D = f"/records/{draft}/draft"

    # --- 0. a v1.0 publicada é a fonte da metadata e dos checksums importados ----
    st, v10 = req("GET", f"/records/{V10}")
    assert st == 200 and v10.get("is_published"), f"v1.0 não legível: {st}"
    v10_files = {k: e["checksum"] for k, e in v10["files"]["entries"].items()}

    # --- 1. metadata -------------------------------------------------------------
    st, cur = req("GET", D)
    assert st == 200 and cur.get("is_draft"), f"rascunho {draft} não é rascunho: {st}"
    doi = cur["pids"]["doi"]["identifier"]
    assert doi == f"10.5281/zenodo.{draft}", doi
    bloco = (HERE / "description-v1.1-block.html").read_text(encoding="utf-8")
    # v1.0 description translated to English (2026-10-05); the Portuguese original stays on 22181415
    en10 = (HERE / "description-v1.0-en.html").read_text(encoding="utf-8")
    desc = en10.rstrip("\n") + "\n\n" + bloco.rstrip("\n")
    (HERE / "description-v1.1.html").write_text(desc + "\n", encoding="utf-8")
    m = json.loads(json.dumps(v10["metadata"]))
    for c in m["creators"]:
        po = c["person_or_org"]
        po.pop("identifiers", None)
        po["identifiers"] = [{"scheme": "orcid", "identifier": ORCID}]
    rc8 = (HERE / "spare-capacity-narrow-surface-v1.1.md").read_text(encoding="utf-8")
    titulo = rc8.split("\n", 1)[0].lstrip("# ").strip()
    m.update({"title": titulo, "version": "1.1", "publication_date": "2026-10-05",
              "description": desc, "languages": [{"id": "eng"}]})
    m.pop("doi", None)
    body = {"metadata": m, "pids": cur["pids"], "access": cur.get("access", v10.get("access")),
            "files": {"enabled": True}}
    (HERE / ".metadata-final.json").write_text(json.dumps(body, ensure_ascii=False, indent=1))
    st, r = req("PUT", D, body)
    assert st == 200, f"PUT metadata {st}: {str(r)[:400]}"
    print(f"1. metadata gravada (DOI reservado preservado: {doi})")

    # --- 2. files-import dos 13 da v1.0 -----------------------------------------
    st, ent = req("GET", f"{D}/files")
    tem = {e["key"]: e for e in ent.get("entries", [])}
    if not set(v10_files) <= set(tem):
        st, r = req("POST", f"{D}/actions/files-import")
        assert st in (200, 201), f"files-import {st}: {str(r)[:400]}"
        print(f"2. files-import: {len(r.get('entries', []))} entradas")
    else:
        print("2. files-import: já presente")

    # --- 3. arquivos novos, uma chave por vez ------------------------------------
    st, ent = req("GET", f"{D}/files")
    tem = {e["key"]: e for e in ent.get("entries", [])}
    for k in OBSOLETOS:
        if k in tem:
            st, r = req("DELETE", f"{D}/files/{k}")
            assert st == 204, f"DELETE {k} {st}: {str(r)[:300]}"
            print(f"3. removido (nome antigo): {k}")
    for k in NOVOS:
        loc = md5(HERE / k)
        e = tem.get(k)
        if e and e.get("status") == "completed" and e.get("checksum") == f"md5:{loc}":
            print(f"3. ok (já enviado): {k}")
            continue
        if e:
            req("DELETE", f"{D}/files/{k}")
        st, r = req("POST", f"{D}/files", [{"key": k}])
        assert st in (200, 201), f"init {k} {st}: {str(r)[:300]}"
        st, r = req("PUT", f"{D}/files/{k}/content", (HERE / k).read_bytes(), ctype="application/octet-stream")
        assert st == 200, f"content {k} {st}: {str(r)[:300]}"
        st, r = req("POST", f"{D}/files/{k}/commit")
        assert st == 200, f"commit {k} {st}: {str(r)[:300]}"
        print(f"3. enviado: {k}")

    # --- 4. readback -------------------------------------------------------------
    st, rb = req("GET", D)
    st2, leg = req("GET", D, accept="application/json")
    (HERE / ".readback-rdm.json").write_text(json.dumps(rb, ensure_ascii=False, indent=1))
    (HERE / ".readback-legacy.json").write_text(json.dumps(leg, ensure_ascii=False, indent=1))
    falhas, linhas = [], []
    md = rb["metadata"]

    def campo(nome, got, exp):
        ok = got == exp
        linhas.append((nome, "ok" if ok else "DIVERGE", got if not isinstance(got, str) or len(got) < 120 else f"{len(got)} chars"))
        if not ok:
            falhas.append(f"{nome}: {got!r} != {exp!r}")

    campo("is_draft", rb.get("is_draft"), True)
    campo("is_published", rb.get("is_published"), False)
    campo("pids.doi", rb["pids"]["doi"]["identifier"], doi)
    campo("parent (concept) doi", rb["parent"]["pids"]["doi"]["identifier"], "10.5281/zenodo.22181414")
    campo("versions.index", rb["versions"]["index"], 2)
    campo("title", md.get("title"), titulo)
    campo("version", md.get("version"), "1.1")
    campo("publication_date", md.get("publication_date"), "2026-10-05")
    campo("resource_type", md["resource_type"]["id"], v10["metadata"]["resource_type"]["id"])
    campo("publisher", md.get("publisher"), "Zenodo")
    campo("rights", [x["id"] for x in md.get("rights", [])], [x["id"] for x in v10["metadata"]["rights"]])
    campo("languages", [x["id"] for x in md.get("languages", [])], ["eng"])
    campo("subjects", [x["subject"] for x in md.get("subjects", [])], [x["subject"] for x in v10["metadata"]["subjects"]])
    campo("related_identifiers", [(x["identifier"], x["relation_type"]["id"]) for x in md.get("related_identifiers", [])],
          [(x["identifier"], x["relation_type"]["id"]) for x in v10["metadata"]["related_identifiers"]])
    cr = md.get("creators", [])
    campo("creators.name", [c["person_or_org"]["name"] for c in cr], ["Busnello, Luiz Antonio"])
    campo("creators.orcid", [[i["identifier"] for i in c["person_or_org"].get("identifiers", []) if i["scheme"] == "orcid"] for c in cr], [[ORCID]])
    campo("creators.affiliation", [[a.get("name") for a in c.get("affiliations", [])] for c in cr], [["Independent Researcher"]])
    remoto = md.get("description", "")
    campo("description (byte a byte, menos o \\n final)", remoto.rstrip("\n") == desc.rstrip("\n"), True)
    campo("description começa pela tradução inglesa da v1.0", remoto.startswith(en10.rstrip("\n")), True)
    campo("description sem o português da v1.0", v10["metadata"]["description"][:80] in remoto, False)
    campo("description traz o bloco v1.1", "What changed in v1.1" in remoto, True)
    campo("legacy vê o mesmo registro", str(leg.get("id")), str(rb.get("id")))

    st, ent = req("GET", f"{D}/files")
    tem = {e["key"]: e for e in ent.get("entries", [])}
    esperado = dict(v10_files)
    esperado.update({k: f"md5:{md5(HERE / k)}" for k in NOVOS})
    arquivos = []
    for k in sorted(set(esperado) - set(tem)):
        falhas.append(f"FALTA no rascunho: {k}")
    for k in sorted(set(tem) - set(esperado)):
        falhas.append(f"SOBRA no rascunho: {k}")
    for k in OBSOLETOS:
        campo(f"chave antiga ausente: {k}", k in tem, False)
    for k in sorted(set(tem) & set(esperado)):
        e = tem[k]
        ok = e.get("status") == "completed" and e.get("checksum") == esperado[k]
        origem = "v1.0 (import)" if k in v10_files else "novo"
        arquivos.append((k, e.get("size"), e.get("checksum"), origem, "ok" if ok else "DIVERGE"))
        if not ok:
            falhas.append(f"checksum/status diverge: {k} {e.get('status')} {e.get('checksum')} != {esperado[k]}")

    man = json.loads((HERE / "MANIFEST-v1.1.json").read_text(encoding="utf-8"))
    for nome in ("artefatos-v1.1.zip", "scripts-v1.1.zip"):
        dentro = {i["path"]: i["sha256"] for i in man["itens"] if i["no_deposito"] == nome}
        with zipfile.ZipFile(HERE / nome) as z:
            if set(z.namelist()) != set(dentro):
                falhas.append(f"{nome}: membros diferem do manifesto")
            for p, s in dentro.items():
                if hashlib.sha256(z.read(p)).hexdigest() != s:
                    falhas.append(f"{nome}: sha256 diverge em {p}")
    for i in man["itens"]:
        if i["no_deposito"] == "solto" and hashlib.sha256((HERE / i["path"]).read_bytes()).hexdigest() != i["sha256"]:
            falhas.append(f"solto diverge do manifesto: {i['path']}")

    out = {"draft": draft, "doi": doi, "campos": linhas, "arquivos": arquivos, "falhas": falhas}
    (HERE / ".readback-resumo.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    for n, s, v in linhas:
        print(f"   {s:7} {n}: {v}")
    for a in arquivos:
        print(f"   {a[4]:7} {a[0]}  {a[1]} B  {a[2]}  [{a[3]}]")
    if falhas:
        print("\n".join("  🔴 " + f for f in falhas))
        return 1
    print(f"4. readback ok: {len(linhas)} campos, {len(arquivos)} arquivos, membros dos zips conferidos")
    print(f"   rascunho: https://zenodo.org/uploads/{draft}  (NÃO publicado)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
