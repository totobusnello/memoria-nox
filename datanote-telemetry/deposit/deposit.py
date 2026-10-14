#!/usr/bin/env python3
"""Data note v1.0 on Zenodo: a NEW record (not a version of another one).

This script never publishes. It has no publish call, and req() refuses any URL with
/actions/publish. Publishing is manual, irreversible, and the author's.

  --plan            read-only, no token: prints the metadata it would write and checks the package.
  --create-draft    WRITE: POST /api/records (a new draft), then reserves its DOI. Stores the id in
                    .draft-id (gitignored). Refuses if .draft-id exists.
  --build           local: with the reserved DOI, writes the deposit copy of the note, builds the PDF
                    with the DOI line, runs parity.py (census + selftest), zips the code, writes
                    SHA256SUMS and runs the privacy gate. Never edits ../DATA-NOTE.md.
  --fill            WRITE: metadata (PUT, keeping the reserved DOI) and the four files, md5-checked.
  --readback        read-only (token): every metadata field and every file checksum. Exit 1 on divergence.

Token: ZENODO_TOKEN in the environment, or ~/.config/secrets/ZENODO_TOKEN.
"""
import datetime
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
NOTE = HERE.parent
API = "https://zenodo.org/api"
VERSION = "1.0"
SLUG = "expensive-writes-noisy-reads"
MD, PDF = f"{SLUG}-v{VERSION}.md", f"{SLUG}-v{VERSION}.pdf"
CODE = f"code-v{VERSION}.zip"
FILES = [PDF, MD, CODE, "SHA256SUMS"]
DESC = HERE / "description-v1.0.html"
DRAFT_ID = HERE / ".draft-id"
DATASET = "23130191"
PUB_DATE = "2026-10-13"
REPO_TAG = "datanote-v1.0"
CODE_FILES = ["analysis.py", "parity.py", "figure.py", "numbers.json", "figure1.pdf", "figure1.png",
              "pdf-build/build-pdf.sh", "pdf-build/preamble-datanote.tex",
              "REVIEW-rc2-grok-codex-2026-10-13.md", "reviews/codex-rc1-full-read-2026-10-13.md",
              "reviews/kimi-rc2-full-read-2026-10-13.md", "deposit/deposit.py"]
SUBJECTS = ["agent memory", "memory construction cost", "phase-attributed telemetry", "production measurement",
            "LLM provider cost", "instrument defects", "data note"]
# Text of the deposit copy that differs from the draft in the repository (status and availability).
EDITS = [
    ("> **Status (2026-10-13).** Draft rc2 of a data note, not peer reviewed and not yet deposited.",
     "> **Status (2026-10-13).** Version 1.0 of a data note, not peer reviewed."),
    ("will be deposited with this note and is\nalso in",
     f"is deposited with this note as `{CODE}` and is\nalso in"),
]
# Privacy gate. Path and host patterns are assembled from pieces, and private words are matched
# by hash, so that this file (which ships in the code zip) does not contain what it looks for.
PRIVATE = ["/" + "Users/", "Users" + "-lab", "claude" + r"-\d{3}", "srv" + r"\d{6,}", "100" + r"\.92\."]
PRIVATE_WORD_SHA = {"5b236b92db0e1d67", "e6118d6a9141084f", "4036df1daeec8306", "49d8a128508040d6"}


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


def draft_doi():
    return f"10.5281/zenodo.{DRAFT_ID.read_text().strip()}"


def creators():
    st, d = req("GET", f"/records/{DATASET}")
    assert st == 200, f"dataset record {st}"
    out = []
    for c in d["metadata"]["creators"]:
        p = c["person_or_org"]
        out.append({"person_or_org": {k: p[k] for k in ("type", "name", "given_name", "family_name", "identifiers")
                                      if k in p},
                    "affiliations": [{"name": a["name"]} for a in c.get("affiliations", [])]})
    return out


def metadata():
    title = (HERE / MD if (HERE / MD).exists() else NOTE / "DATA-NOTE.md").read_text().split("\n", 1)[0].lstrip("# ").strip()
    return {
        "resource_type": {"id": "publication-preprint"},
        "title": title,
        "publication_date": PUB_DATE,
        "creators": creators(),
        "description": DESC.read_text(encoding="utf-8"),
        "version": VERSION,
        "publisher": "Zenodo",
        "languages": [{"id": "eng"}],
        "rights": [{"id": "cc-by-4.0"}],
        "subjects": [{"subject": s} for s in SUBJECTS],
        "related_identifiers": [
            {"identifier": f"10.5281/zenodo.{DATASET}", "scheme": "doi", "relation_type": {"id": "describes"},
             "resource_type": {"id": "dataset"}},
            {"identifier": "arXiv:2606.06448", "scheme": "arxiv", "relation_type": {"id": "references"},
             "resource_type": {"id": "publication-preprint"}},
            {"identifier": "10.5281/zenodo.23147633", "scheme": "doi", "relation_type": {"id": "references"},
             "resource_type": {"id": "publication-preprint"}},
            {"identifier": f"https://github.com/totobusnello/memoria-nox/tree/{REPO_TAG}/datanote-telemetry",
             "scheme": "url", "relation_type": {"id": "issupplementedby"}, "resource_type": {"id": "software"}},
        ],
    }


def privacy_scan(name, data):
    txt = data.decode("utf-8", "replace") if isinstance(data, bytes) else data
    hits = [(name, p) for p in PRIVATE if re.search(p, txt, flags=re.I)]
    for w in set(re.findall(r"[\w.@-]+", txt.lower())):
        for cand in {w, w.split("@")[-1].split(".")[0]}:
            if hashlib.sha256(cand.encode()).hexdigest()[:16] in PRIVATE_WORD_SHA:
                hits.append((name, "private word (hash " + hashlib.sha256(cand.encode()).hexdigest()[:8] + ")"))
    return hits


def build():
    doi = draft_doi()
    text = (NOTE / "DATA-NOTE.md").read_text(encoding="utf-8")
    for old, new in EDITS:
        if old in text:
            text = text.replace(old, new)
    assert "not yet deposited" not in text and "will be deposited" not in text, "pre-deposit wording left"
    (HERE / MD).write_text(text, encoding="utf-8")
    # census on the deposit copy, then the selftest
    for args in (["numbers.json", str(HERE / MD)], ["--selftest", "numbers.json", str(HERE / MD)]):
        r = subprocess.run([sys.executable, "-I", "parity.py", *args], cwd=NOTE, capture_output=True, text=True)
        print("parity:", r.stdout.strip().splitlines()[0] if r.stdout.strip() else r.stderr.strip())
        assert r.returncode == 0, r.stdout + r.stderr
    # PDF with the DOI line, built from the deposit copy
    env = dict(os.environ, DATANOTE_DOI=doi, DATANOTE_MD=str(HERE / MD))
    r = subprocess.run(["bash", str(NOTE / "pdf-build/build-pdf.sh")], env=env, capture_output=True, text=True)
    print(r.stdout.strip())
    assert r.returncode == 0, r.stdout + r.stderr
    (NOTE / "pdf-build/DATA-NOTE.pdf").replace(HERE / PDF)
    pdftext = subprocess.run(["pdftotext", "-enc", "UTF-8", str(HERE / PDF), "-"], capture_output=True).stdout.decode()
    assert doi in pdftext, "the DOI is not in the PDF text"
    # code zip, fixed timestamps
    with zipfile.ZipFile(HERE / CODE, "w", zipfile.ZIP_DEFLATED) as z:
        for f in CODE_FILES:
            zi = zipfile.ZipInfo(f"datanote-telemetry/{f}", (2026, 10, 13, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, (NOTE / f).read_bytes())
    sums = [f"{sha256((HERE / n).read_bytes())}  {n}" for n in (PDF, MD, CODE)]
    (HERE / "SHA256SUMS").write_text("\n".join(sums) + "\n")
    findings = privacy_scan(MD, (HERE / MD).read_bytes()) + privacy_scan(PDF + " (text)", pdftext)
    findings += privacy_scan(PDF + " (bytes)", (HERE / PDF).read_bytes().decode("latin-1"))
    with zipfile.ZipFile(HERE / CODE) as z:
        for n in z.namelist():
            findings += privacy_scan(f"{CODE}:{n}", z.read(n))
    findings += privacy_scan("description", DESC.read_text())
    for f in findings:
        print("  PRIVACY", f)
    assert not findings, "privacy gate failed"
    for n in FILES:
        print(f"  {n}  {(HERE / n).stat().st_size} B  md5:{md5(HERE / n)}")
    print(f"build ok with DOI {doi}; pages: " +
          re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", str(HERE / PDF)], capture_output=True,
                                                       text=True).stdout).group(1))
    return 0


def plan():
    m = metadata()
    print(json.dumps({k: (v if k != "description" else f"{len(v)} chars") for k, v in m.items()},
                     ensure_ascii=False, indent=1))
    return 0


def create_draft():
    if DRAFT_ID.exists():
        sys.exit(f".draft-id exists ({DRAFT_ID.read_text().strip()}); refusing to create a second draft")
    tok = token()
    st, r = req("POST", "/records", {"metadata": {"resource_type": {"id": "publication-preprint"}},
                                     "files": {"enabled": True},
                                     "access": {"record": "public", "files": "public"}}, tok=tok)
    assert st in (200, 201), f"create {st}: {str(r)[:400]}"
    did = str(r["id"])
    DRAFT_ID.write_text(did + "\n")
    st, d = req("POST", f"/records/{did}/draft/pids/doi", tok=tok)
    doi = (d.get("pids", {}).get("doi") or {}).get("identifier") if isinstance(d, dict) else None
    print(f"draft {did} created (NOT published); reserved DOI: {doi} (status {st})")
    return 0 if doi == f"10.5281/zenodo.{did}" else 1


def fill():
    did = DRAFT_ID.read_text().strip()
    tok = token()
    D = f"/records/{did}/draft"
    st, cur = req("GET", D, tok=tok)
    assert st == 200 and cur.get("is_draft"), f"{did} is not a draft: {st}"
    sums = dict(reversed(ln.split("  ", 1)) for ln in (HERE / "SHA256SUMS").read_text().splitlines())
    for n in (PDF, MD, CODE):
        assert sha256((HERE / n).read_bytes()) == sums[n], f"SHA256SUMS diverges for {n}: run --build"
    body = {"metadata": metadata(), "pids": cur["pids"], "access": {"record": "public", "files": "public"},
            "files": {"enabled": True}}
    (HERE / ".metadata.json").write_text(json.dumps(body, ensure_ascii=False, indent=1))
    st, r = req("PUT", D, body, tok=tok)
    assert st == 200, f"PUT metadata {st}: {str(r)[:600]}"
    if r.get("errors"):
        print("  metadata warnings:", json.dumps(r["errors"])[:600])
    print("1. metadata written")
    st, ent = req("GET", f"{D}/files", tok=tok)
    have = {e["key"]: e for e in ent.get("entries", [])}
    for k in FILES:
        loc = md5(HERE / k)
        e = have.get(k)
        if e and e.get("status") == "completed" and e.get("checksum") == f"md5:{loc}":
            print(f"2. ok (already uploaded): {k}")
            continue
        if e:
            req("DELETE", f"{D}/files/{k}", tok=tok)
        st, r = req("POST", f"{D}/files", [{"key": k}], tok=tok)
        assert st in (200, 201), f"init {k} {st}: {str(r)[:300]}"
        st, r = req("PUT", f"{D}/files/{k}/content", (HERE / k).read_bytes(), tok=tok, ctype="application/octet-stream")
        assert st == 200, f"content {k} {st}: {str(r)[:300]}"
        st, r = req("POST", f"{D}/files/{k}/commit", tok=tok)
        assert st == 200, f"commit {k} {st}: {str(r)[:300]}"
        print(f"2. uploaded: {k}")
    return readback()


def readback():
    tok = token()
    did = DRAFT_ID.read_text().strip()
    D = f"/records/{did}/draft"
    st, rb = req("GET", D, tok=tok)
    assert st == 200, f"draft {did}: {st}"
    (HERE / ".readback.json").write_text(json.dumps(rb, ensure_ascii=False, indent=1))
    md, exp = rb["metadata"], metadata()
    fails, lines = [], []

    def field(name, got, want):
        ok = got == want
        lines.append((name, "ok" if ok else "DIVERGE", got if not isinstance(got, str) or len(got) < 110 else f"{len(got)} chars"))
        if not ok:
            fails.append(f"{name}: {got!r} != {want!r}")

    field("is_draft", rb.get("is_draft"), True)
    field("is_published", rb.get("is_published"), False)
    field("pids.doi", rb["pids"]["doi"]["identifier"], f"10.5281/zenodo.{did}")
    field("title = line 1 of the note", md.get("title"), exp["title"])
    field("version", md.get("version"), VERSION)
    field("publication_date", md.get("publication_date"), PUB_DATE)
    field("resource_type", md["resource_type"]["id"], "publication-preprint")
    field("rights", [x["id"] for x in md.get("rights", [])], ["cc-by-4.0"])
    field("languages", [x["id"] for x in md.get("languages", [])], ["eng"])
    field("subjects", [x["subject"] for x in md.get("subjects", [])], SUBJECTS)
    field("creators (name, ORCID, affiliation)",
          [(c["person_or_org"]["name"], [i["identifier"] for i in c["person_or_org"].get("identifiers", [])],
            [a["name"] for a in c.get("affiliations", [])]) for c in md["creators"]],
          [(c["person_or_org"]["name"], [i["identifier"] for i in c["person_or_org"].get("identifiers", [])],
            [a["name"] for a in c["affiliations"]]) for c in exp["creators"]])
    field("related_identifiers", [(x["identifier"], x["relation_type"]["id"]) for x in md.get("related_identifiers", [])],
          [(x["identifier"], x["relation_type"]["id"]) for x in exp["related_identifiers"]])
    field("description byte for byte", md.get("description", "").rstrip("\n") == exp["description"].rstrip("\n"), True)
    field("access", (rb["access"]["record"], rb["access"]["files"]), ("public", "public"))
    st, ent = req("GET", f"{D}/files", tok=tok)
    have = {e["key"]: e for e in ent.get("entries", [])}
    files = []
    for k in sorted(set(FILES) | set(have)):
        e = have.get(k)
        if k not in FILES:
            fails.append(f"EXTRA in the draft: {k}")
            continue
        if not e:
            fails.append(f"MISSING from the draft: {k}")
            continue
        ok = e.get("status") == "completed" and e.get("checksum") == f"md5:{md5(HERE / k)}"
        files.append((k, e.get("size"), e.get("checksum"), "ok" if ok else "DIVERGE"))
        if not ok:
            fails.append(f"checksum/status diverges: {k}")
    pdftext = subprocess.run(["pdftotext", "-enc", "UTF-8", str(HERE / PDF), "-"], capture_output=True).stdout.decode()
    field("PDF carries the draft DOI", f"10.5281/zenodo.{did}" in pdftext, True)
    out = {"draft": did, "fields": lines, "files": files, "failures": fails,
           "at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
    (HERE / ".readback-summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    for n, s, v in lines:
        print(f"   {s:7} {n}: {v}")
    for a in files:
        print(f"   {a[3]:7} {a[0]}  {a[1]} B  {a[2]}")
    if fails:
        print("\n".join("  FAIL " + f for f in fails))
        return 1
    print(f"readback ok: {len(lines)} fields, {len(files)} files")
    print(f"   draft: https://zenodo.org/uploads/{did}  (NOT published)")
    return 0


def main():
    a = sys.argv[1:]
    assert not any("publish" in x for x in a), "this script does not publish"
    for flag, fn in (("--plan", plan), ("--create-draft", create_draft), ("--build", build),
                     ("--fill", fill), ("--readback", readback)):
        if flag in a:
            return fn()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
