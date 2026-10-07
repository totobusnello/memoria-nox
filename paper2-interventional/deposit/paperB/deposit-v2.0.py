#!/usr/bin/env python3
"""Paper B v2.0 on Zenodo: NEW-VERSION draft of record 22110203 (v1.12, concept 10.5281/zenodo.21964093).

⛔ This script never publishes. It contains no publish call, and req() refuses any URL with
   /actions/publish. Publishing is manual, irreversible, and the author's, after DRAFT-READBACK.md.

Every step that writes needs its own explicit flag; with no flag the script only prints usage.

  --plan            read-only, no token: reads the public v1.12 record, checks that it is still the
                    latest version of the concept, builds the metadata it would write, checks the
                    local package (SHA256SUMS, MANIFEST, zip members) and prints all of it.
  --create-draft    WRITE: POST /api/records/22110203/versions (a new-version draft; the DOI is
                    reserved, not registered). Stores the id in .draft-id-v2.0 (gitignored).
                    Refuses if .draft-id-v2.0 exists or if v1.12 is no longer the latest version.
  --fill            WRITE: into the draft of .draft-id-v2.0: metadata (PUT, preserving the draft's
                    `pids`), then the six files one key at a time with md5 compared and re-upload on
                    mismatch. Needs --publication-date YYYY-MM-DD. --import-v112-files additionally
                    copies v1.12's 60 files into the draft on the server (files-import); default off.
  --readback        read-only (token): every metadata field and every file checksum, both directions;
                    zip members against MANIFEST-v2.0.json. Exit 1 on any divergence.
Token: ZENODO_TOKEN in the environment, or ~/.config/secrets/ZENODO_TOKEN (write/readback only).
"""
import datetime
import hashlib
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
API = "https://zenodo.org/api"
BASE = "22110203"                      # v1.12
CONCEPT_DOI = "10.5281/zenodo.21964093"
VERSION = "2.0"
SLUG = "registered-horizon-outlived-intervention"
MD, PDF = f"{SLUG}-v{VERSION}.md", f"{SLUG}-v{VERSION}.pdf"
MANIFEST = f"MANIFEST-v{VERSION}.json"
ZIPS = [f"artifacts-v{VERSION}.zip", f"scripts-v{VERSION}.zip"]
NOVOS = [PDF, MD, MANIFEST, *ZIPS, "SHA256SUMS"]
DESC = HERE / f"description-v{VERSION}.html"
DRAFT_ID = HERE / f".draft-id-v{VERSION}"
REPO_URL = "https://github.com/totobusnello/memoria-nox/tree/{tag}/paper2-interventional"
REPO_TAG = "paper2-v2.0"               # the author creates this tag on the deposited commit (READY.md)
# Added to v1.12's related identifiers (author's decision, READY.md): Paper A v1.1, which this manuscript cites.
# `references`, as Paper A's own record uses for its link to the OSF registration (isSupplementedBy is kept for
# the software link, as in v1.12).
PAPER_A = {"identifier": "10.5281/zenodo.23163119", "scheme": "doi", "relation_type": {"id": "references"},
           "resource_type": {"id": "publication-preprint"}}
PLACEHOLDER = "[VERSION-DOI]"
# Creators exactly as v1.12 (record 22110203): one person, no identifier, one affiliation.
CREATORS_V112 = [("Busnello, Luiz Antonio", ["Independent Researcher"], [])]


def token():
    t = os.environ.get("ZENODO_TOKEN", "").strip()
    if not t:
        p = pathlib.Path.home() / ".config/secrets/ZENODO_TOKEN"
        t = p.read_text().strip() if p.exists() else ""
    if not t:
        sys.exit("no ZENODO_TOKEN")
    return t


def req(method, path, body=None, tok=None, ctype="application/json", accept="application/vnd.inveniordm.v1+json"):
    url = path if path.startswith("http") else API + path
    assert "/actions/publish" not in url, "this script does not publish"
    data = None
    if body is not None:
        data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
    r = urllib.request.Request(url, data=data, method=method)
    if tok:
        r.add_header("Authorization", f"Bearer {tok}")
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


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def base_record():
    st, v = req("GET", f"/records/{BASE}")
    assert st == 200 and v.get("is_published"), f"v1.12 not readable: {st}"
    st, latest = req("GET", f"/records/{BASE}/versions/latest")
    lid = str(latest.get("id")) if st == 200 and isinstance(latest, dict) else None
    return v, lid


def creators_of(md):
    return [(c["person_or_org"]["name"], [a.get("name") for a in c.get("affiliations", [])],
             [i["identifier"] for i in c["person_or_org"].get("identifiers", [])]) for c in md.get("creators", [])]


def build_metadata(v112, pub_date):
    m = json.loads(json.dumps(v112["metadata"]))
    assert creators_of(m) == CREATORS_V112, f"v1.12 creators changed: {creators_of(m)}"
    for k in ("rights", "languages"):
        m[k] = [{"id": x["id"]} for x in m.get(k, [])]
    m["resource_type"] = {"id": m["resource_type"]["id"]}
    rel = []
    for x in m.get("related_identifiers", []):
        y = {"identifier": x["identifier"], "scheme": x["scheme"], "relation_type": {"id": x["relation_type"]["id"]}}
        if "resource_type" in x:
            y["resource_type"] = {"id": x["resource_type"]["id"]}
        if "github.com/totobusnello/memoria-nox/tree/" in y["identifier"]:
            y["identifier"] = REPO_URL.format(tag=REPO_TAG)
        rel.append(y)
    assert all(x["identifier"] != PAPER_A["identifier"] for x in rel), "v1.12 already links Paper A?"
    rel.append(json.loads(json.dumps(PAPER_A)))
    title = (HERE / MD).read_text(encoding="utf-8").split("\n", 1)[0].lstrip("# ").strip()
    desc = DESC.read_text(encoding="utf-8")
    m.update({"title": title, "version": VERSION, "description": desc, "languages": [{"id": "eng"}],
              "related_identifiers": rel})
    if pub_date:
        m["publication_date"] = pub_date
    m.pop("doi", None)
    return m


def local_package_checks(final=False, doi=None):
    """final=True (--fill, --readback): the package must be built with the draft's DOI (no dry run,
    no placeholder left in the .md, manifest doi == the draft's DOI)."""
    falhas = []
    sums = {}
    for ln in (HERE / "SHA256SUMS").read_text().splitlines():
        h, n = ln.split("  ", 1)
        sums[n] = h
    for n in NOVOS:
        if n == "SHA256SUMS":
            continue
        if sha256((HERE / n).read_bytes()) != sums.get(n):
            falhas.append(f"SHA256SUMS diverges for {n}")
    man = json.loads((HERE / MANIFEST).read_text(encoding="utf-8"))
    for z in ZIPS:
        dentro = {i["path"]: i["sha256"] for i in man["items"] if i["in"] == z}
        with zipfile.ZipFile(HERE / z) as zf:
            if set(zf.namelist()) != set(dentro):
                falhas.append(f"{z}: members differ from the manifest")
            for p, s in dentro.items():
                if sha256(zf.read(p)) != s:
                    falhas.append(f"{z}: sha256 diverges at {p}")
    for i in man["items"]:
        if i["in"] == "loose" and sha256((HERE / i["path"]).read_bytes()) != i["sha256"]:
            falhas.append(f"loose file diverges from the manifest: {i['path']}")
    if final:
        if man["record"].get("dry_run") or PLACEHOLDER in (HERE / MD).read_text(encoding="utf-8"):
            falhas.append("the package is a --no-doi dry run (placeholder still in the text): rebuild with --doi")
        if doi and man["record"].get("doi") != doi:
            falhas.append(f"the package was built with DOI {man['record'].get('doi')}, the draft reserved {doi}")
    if man["census"]["gaps"] or man["privacy_gate"]["findings"]:
        falhas.append(f"manifest records census gaps {man['census']['gaps']} / privacy findings {man['privacy_gate']['findings']}")
    return falhas, man


def plan():
    v112, lid = base_record()
    print(f"v1.12: {BASE} published; latest version of the concept: {lid}")
    m = build_metadata(v112, None)
    print(json.dumps({k: (v if k != "description" else f"{len(v)} chars") for k, v in m.items()}, ensure_ascii=False, indent=1))
    falhas, man = local_package_checks()
    for n in NOVOS:
        print(f"  {n}  {(HERE / n).stat().st_size} B  md5:{md5(HERE / n)}")
    if lid != BASE:
        falhas.append(f"v1.12 is not the latest version (latest = {lid}); a new version would not follow v1.12")
    print("\n".join("  FAIL " + f for f in falhas) or "plan ok (nothing written)")
    return 1 if falhas else 0


def create_draft():
    if DRAFT_ID.exists():
        sys.exit(f"{DRAFT_ID.name} exists ({DRAFT_ID.read_text().strip()}); refusing to create a second draft")
    falhas, _ = local_package_checks()
    if falhas:
        sys.exit("local package fails its checks: " + "; ".join(falhas))
    tok = token()
    v112, lid = base_record()
    if lid != BASE:
        sys.exit(f"v1.12 is not the latest version (latest = {lid}); stop")
    st, r = req("POST", f"/records/{BASE}/versions", tok=tok)
    assert st in (200, 201), f"new version {st}: {str(r)[:400]}"
    did = str(r["id"])
    DRAFT_ID.write_text(did + "\n")
    st, d = req("GET", f"/records/{did}/draft", tok=tok)
    doi = (d.get("pids", {}).get("doi") or {}).get("identifier")
    if not doi:
        st, d = req("POST", f"/records/{did}/draft/pids/doi", tok=tok)
        doi = (d.get("pids", {}).get("doi") or {}).get("identifier")
    print(f"draft {did} created (NOT published); reserved DOI: {doi}")
    print(f"next: python3 build-package.py --doi {doi}, then --fill")
    return 0


def fill(pub_date, import_v112):
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", pub_date or ""), "--publication-date YYYY-MM-DD is required"
    did = DRAFT_ID.read_text().strip()
    falhas, _ = local_package_checks(final=True, doi=f"10.5281/zenodo.{did}")
    if falhas:
        sys.exit("local package fails its checks: " + "; ".join(falhas))
    tok = token()
    D = f"/records/{did}/draft"
    v112, _ = base_record()
    st, cur = req("GET", D, tok=tok)
    assert st == 200 and cur.get("is_draft"), f"{did} is not a draft: {st}"
    m = build_metadata(v112, pub_date)
    body = {"metadata": m, "pids": cur["pids"], "access": cur.get("access", v112.get("access")), "files": {"enabled": True}}
    (HERE / f".metadata-v{VERSION}.json").write_text(json.dumps(body, ensure_ascii=False, indent=1))
    st, r = req("PUT", D, body, tok=tok)
    assert st == 200, f"PUT metadata {st}: {str(r)[:400]}"
    print(f"1. metadata written (reserved DOI kept: {cur['pids'].get('doi', {}).get('identifier')})")
    if import_v112:
        st, r = req("POST", f"{D}/actions/files-import", tok=tok)
        assert st in (200, 201), f"files-import {st}: {str(r)[:400]}"
        print(f"2. files-import of v1.12: {len(r.get('entries', []))} entries")
    st, ent = req("GET", f"{D}/files", tok=tok)
    tem = {e["key"]: e for e in ent.get("entries", [])}
    for k in NOVOS:
        loc = md5(HERE / k)
        e = tem.get(k)
        if e and e.get("status") == "completed" and e.get("checksum") == f"md5:{loc}":
            print(f"3. ok (already uploaded): {k}")
            continue
        if e:
            req("DELETE", f"{D}/files/{k}", tok=tok)
        st, r = req("POST", f"{D}/files", [{"key": k}], tok=tok)
        assert st in (200, 201), f"init {k} {st}: {str(r)[:300]}"
        st, r = req("PUT", f"{D}/files/{k}/content", (HERE / k).read_bytes(), tok=tok, ctype="application/octet-stream")
        assert st == 200, f"content {k} {st}: {str(r)[:300]}"
        st, r = req("POST", f"{D}/files/{k}/commit", tok=tok)
        assert st == 200, f"commit {k} {st}: {str(r)[:300]}"
        print(f"3. uploaded: {k}")
    return readback(pub_date, import_v112)


def readback(pub_date=None, import_v112=None):
    tok = token()
    did = DRAFT_ID.read_text().strip()
    D = f"/records/{did}/draft"
    v112, _ = base_record()
    st, rb = req("GET", D, tok=tok)
    st2, leg = req("GET", D, tok=tok, accept="application/json")
    assert st == 200, f"draft {did}: {st}"
    (HERE / f".readback-rdm-v{VERSION}.json").write_text(json.dumps(rb, ensure_ascii=False, indent=1))
    (HERE / f".readback-legacy-v{VERSION}.json").write_text(json.dumps(leg, ensure_ascii=False, indent=1))
    md, vm = rb["metadata"], v112["metadata"]
    exp = build_metadata(v112, pub_date or md.get("publication_date"))
    falhas, linhas = [], []

    def campo(nome, got, want):
        ok = got == want
        linhas.append((nome, "ok" if ok else "DIVERGE", got if not isinstance(got, str) or len(got) < 120 else f"{len(got)} chars"))
        if not ok:
            falhas.append(f"{nome}: {got!r} != {want!r}")

    campo("is_draft", rb.get("is_draft"), True)
    campo("is_published", rb.get("is_published"), False)
    campo("pids.doi = 10.5281/zenodo.<draft>", rb["pids"]["doi"]["identifier"], f"10.5281/zenodo.{did}")
    campo("parent (concept) doi", rb["parent"]["pids"]["doi"]["identifier"], CONCEPT_DOI)
    campo("versions.index = v1.12 + 1", rb["versions"]["index"], v112["versions"]["index"] + 1)
    campo("title = line 1 of the manuscript", md.get("title"), exp["title"])
    campo("version", md.get("version"), VERSION)
    campo("publication_date (set by --fill)", bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", md.get("publication_date", ""))), True)
    campo("resource_type", md["resource_type"]["id"], vm["resource_type"]["id"])
    campo("publisher", md.get("publisher"), "Zenodo")
    campo("rights", [x["id"] for x in md.get("rights", [])], [x["id"] for x in vm["rights"]])
    campo("languages", [x["id"] for x in md.get("languages", [])], ["eng"])
    campo("subjects = v1.12", [x["subject"] for x in md.get("subjects", [])], [x["subject"] for x in vm.get("subjects", [])])
    campo("related_identifiers", [(x["identifier"], x["relation_type"]["id"]) for x in md.get("related_identifiers", [])],
          [(x["identifier"], x["relation_type"]["id"]) for x in exp["related_identifiers"]])
    campo("creators = v1.12 exactly", creators_of(md), CREATORS_V112)
    campo("description byte for byte (minus final \\n)", md.get("description", "").rstrip("\n") == exp["description"].rstrip("\n"), True)
    campo("legacy form sees the same record", str(leg.get("id")), str(rb.get("id")))
    campo("legacy form has creators", bool((leg.get("metadata") or {}).get("creators")), True)
    campo("legacy form has license", bool((leg.get("metadata") or {}).get("license")), True)

    st, ent = req("GET", f"{D}/files", tok=tok)
    tem = {e["key"]: e for e in ent.get("entries", [])}
    esperado = {k: f"md5:{md5(HERE / k)}" for k in NOVOS}
    if import_v112 or (import_v112 is None and len(tem) > len(NOVOS)):
        st, vf = req("GET", f"/records/{BASE}/files")
        esperado.update({e["key"]: e["checksum"] for e in vf.get("entries", [])})
    arquivos = []
    for k in sorted(set(esperado) - set(tem)):
        falhas.append(f"MISSING from the draft: {k}")
    for k in sorted(set(tem) - set(esperado)):
        falhas.append(f"EXTRA in the draft: {k}")
    for k in sorted(set(tem) & set(esperado)):
        e = tem[k]
        ok = e.get("status") == "completed" and e.get("checksum") == esperado[k]
        arquivos.append((k, e.get("size"), e.get("checksum"), "new" if k in NOVOS else "v1.12 (import)", "ok" if ok else "DIVERGE"))
        if not ok:
            falhas.append(f"checksum/status diverges: {k} {e.get('status')} {e.get('checksum')} != {esperado[k]}")
    f2, _ = local_package_checks(final=True, doi=f"10.5281/zenodo.{did}")
    falhas += f2
    out = {"draft": did, "fields": linhas, "files": arquivos, "failures": falhas,
           "at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
    (HERE / f".readback-summary-v{VERSION}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    for n, s, v in linhas:
        print(f"   {s:7} {n}: {v}")
    for a in arquivos:
        print(f"   {a[4]:7} {a[0]}  {a[1]} B  {a[2]}  [{a[3]}]")
    if falhas:
        print("\n".join("  FAIL " + f for f in falhas))
        return 1
    print(f"readback ok: {len(linhas)} fields, {len(arquivos)} files, zip members checked")
    print(f"   draft: https://zenodo.org/uploads/{did}  (NOT published)")
    return 0


def main():
    a = sys.argv[1:]
    assert not any("publish" in x for x in a), "this script does not publish"
    pub = next((a[i + 1] for i, x in enumerate(a) if x == "--publication-date" and i + 1 < len(a)), None)
    if "--plan" in a:
        return plan()
    if "--create-draft" in a:
        return create_draft()
    if "--fill" in a:
        return fill(pub, "--import-v112-files" in a)
    if "--readback" in a:
        return readback()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
