#!/usr/bin/env python3
"""Paper 3's manuscript as its own Zenodo record (a NEW record: a paper is a different work from
the plan and from the result records it cites).

Same commands and gates as deposit.py, whose helpers it imports:

  --plan            read-only, no token: metadata, files, privacy gate.
  --create-draft    WRITE: POST /api/records, reserves the DOI, stores the id in
                    .draft-id-manuscript-v<VERSION> (gitignored). Refuses if it exists.
  --build           local: deposit copy of ../MANUSCRIPT.md (status line only), the PDF with the
                    DOI line, a code zip, SHA256SUMS, privacy gate. Never edits ../MANUSCRIPT.md.
  --fill            WRITE: metadata and files, md5-checked.
  --readback        read-only (token): every metadata field and every file checksum.

This script never publishes (deposit.req refuses any /actions/publish URL).
"""
import importlib.util
import os
import pathlib
import subprocess
import sys
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
PLAN = HERE.parent
spec = importlib.util.spec_from_file_location("dep", HERE / "deposit.py")
dep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dep)

VERSION = "1.0"
SLUG = "construction-before-search"
MD, PDF = f"{SLUG}-v{VERSION}.md", f"{SLUG}-v{VERSION}.pdf"
CODE = f"code-v{VERSION}.zip"
FILES = [PDF, MD, CODE, "SHA256SUMS"]
DESC = HERE / f"description-manuscript-v{VERSION}.html"
DRAFT_ID = HERE / f".draft-id-manuscript-v{VERSION}"
PUB_DATE = "2026-11-04"
TITLE = "Construction before search: a pre-registered test of what an LLM memory builder keeps"
REPO_BRANCH_COMMIT = os.environ.get("MANUSCRIPT_COMMIT", "")
CITED = [  # (doi, what) — every record the manuscript's §9 cites
    ("10.5281/zenodo.23934489", "pre-registration v1.3"),
    ("10.5281/zenodo.23964906", "pre-registration v1.4"),
    ("10.5281/zenodo.23949145", "confirmatory result v1.0"),
    ("10.5281/zenodo.23964931", "confirmatory result v1.1, raw-evidence arm"),
]
CODE_FILES = ["manuscript-tables.py", "pdf-build/build-manuscript-pdf.sh",
              "pdf-build/preamble-prereg.tex", "pdf-build/table-widths.py",
              "pdf-build/check-layout.py", "deposit/deposit-manuscript.py"]
SUBJECTS = ["agent memory", "memory construction", "pre-registration", "LongMemEval",
            "LLM extraction", "write path", "factorial design", "judge agreement"]
STATUS_OLD = ("Status: working draft, not deposited, not peer reviewed. Every number in this text comes\n"
              "from a file in this directory. §10 lists the sources.")


def status_new(doi):
    return (f"Version {VERSION} (2026-11-04), doi:{doi}. Not peer reviewed. Every number in this text "
            "comes from a file in the repository directory `paper3-construction/` or in the data "
            "archives of the records in §9; §10 lists the sources.")


def metadata():
    rel = [{"identifier": d, "scheme": "doi", "relation_type": {"id": "references"},
            "resource_type": {"id": "publication-preprint" if "pre-registration" in w
                              else "publication-report"}} for d, w in CITED]
    if REPO_BRANCH_COMMIT:
        rel.append({"identifier": f"https://github.com/totobusnello/memoria-nox/tree/"
                                  f"{REPO_BRANCH_COMMIT}/paper3-construction",
                    "scheme": "url", "relation_type": {"id": "issupplementedby"},
                    "resource_type": {"id": "software"}})
    return {
        "resource_type": {"id": "publication-preprint"},
        "title": TITLE,
        "publication_date": PUB_DATE,
        "creators": dep.creators(),
        "description": DESC.read_text(encoding="utf-8"),
        "version": VERSION,
        "publisher": "Zenodo",
        "languages": [{"id": "eng"}],
        "rights": [{"id": "cc-by-4.0"}],
        "subjects": [{"subject": s} for s in SUBJECTS],
        "related_identifiers": rel,
    }


def draft_doi():
    if not DRAFT_ID.exists():
        sys.exit(f"no {DRAFT_ID.name} — run --create-draft first")
    return f"10.5281/zenodo.{DRAFT_ID.read_text().strip()}"


def deposit_text(doi="10.5281/zenodo.RESERVED"):
    text = (PLAN / "MANUSCRIPT.md").read_text(encoding="utf-8")
    assert text.count(STATUS_OLD) == 1, "status anchor missing"
    text = text.replace(STATUS_OLD, status_new(doi))
    assert "@@" not in text and "not deposited" not in text
    for d, _ in CITED:
        assert d in text, f"{d} not cited in the manuscript"
    return text


def build():
    doi = draft_doi()
    (HERE / MD).write_text(deposit_text(doi), encoding="utf-8")
    env = dict(os.environ, MANUSCRIPT_MD=str(HERE / MD),
               MANUSCRIPT_LINE=f"Version {VERSION} · doi:{doi}")
    r = subprocess.run(["bash", str(PLAN / "pdf-build/build-manuscript-pdf.sh")], env=env,
                       capture_output=True, text=True)
    print(r.stdout.strip() or r.stderr.strip()[-600:])
    assert r.returncode == 0, "pdf build failed"
    (PLAN / "pdf-build/MANUSCRIPT.pdf").replace(HERE / PDF)
    pdftext = subprocess.run(["pdftotext", "-enc", "UTF-8", str(HERE / PDF), "-"],
                             capture_output=True).stdout.decode()
    assert doi in pdftext, "the DOI is not in the PDF text"
    with zipfile.ZipFile(HERE / CODE, "w", zipfile.ZIP_DEFLATED) as z:
        for f in CODE_FILES:
            zi = zipfile.ZipInfo(f"paper3-construction/{f}", (2026, 11, 4, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, (PLAN / f).read_bytes())
    (HERE / "SHA256SUMS").write_text(
        "\n".join(f"{dep.sha256((HERE / n).read_bytes())}  {n}" for n in (PDF, MD, CODE)) + "\n")
    findings = dep.privacy_scan(MD, (HERE / MD).read_bytes())
    findings += dep.privacy_scan(PDF + " (text)", pdftext)
    findings += dep.privacy_scan(PDF + " (bytes)", (HERE / PDF).read_bytes().decode("latin-1"))
    with zipfile.ZipFile(HERE / CODE) as z:
        for n in z.namelist():
            findings += dep.privacy_scan(f"{CODE}:{n}", z.read(n))
    findings += dep.privacy_scan("description", DESC.read_text())
    for f in findings:
        print("  PRIVACY", f)
    assert not findings, "privacy gate failed"
    for n in FILES:
        print(f"  {n}  {(HERE / n).stat().st_size} B  md5:{dep.md5(HERE / n)}")
    print(f"build ok with DOI {doi}")
    return 0


def plan():
    txt = deposit_text()
    print(f"deposit copy: {len(txt)} chars · {len(txt.split())} words · title: {TITLE}")
    missing = [f for f in CODE_FILES if not (PLAN / f).exists()]
    for f in CODE_FILES:
        print(f"  {'ok ' if f not in missing else 'MISSING'} {f}")
    fnd = dep.privacy_scan("deposit copy", txt)
    fnd += dep.privacy_scan("description", DESC.read_text()) if DESC.exists() else []
    for f in fnd:
        print("  PRIVACY", f)
    print(f"commit for the software link: {REPO_BRANCH_COMMIT or 'NOT SET (MANUSCRIPT_COMMIT)'}")
    ok = not fnd and not missing and DESC.exists() and bool(REPO_BRANCH_COMMIT)
    print(f"\nprivacy {'PASS' if not fnd else 'FAIL'} · code files {'PASS' if not missing else 'FAIL'}"
          f" · description {'PASS' if DESC.exists() else 'FAIL'}")
    return 0 if ok else 1


def create_draft():
    if DRAFT_ID.exists():
        sys.exit(f"refusing: {DRAFT_ID.name} already exists ({DRAFT_ID.read_text().strip()})")
    tok = dep.token()
    st, d = dep.req("POST", "/records", {"metadata": metadata(), "access":
                    {"record": "public", "files": "public"}, "files": {"enabled": True}}, tok)
    assert st in (200, 201), f"new draft: {st} {d}"
    rid = d["id"]
    DRAFT_ID.write_text(str(rid) + "\n")
    st2, d2 = dep.req("POST", f"/records/{rid}/draft/pids/doi", {}, tok)
    print(f"draft {rid} · reserve doi {st2} · {d2.get('pids', {}).get('doi', {}).get('identifier')}")
    return 0


def fill():
    tok, rid = dep.token(), DRAFT_ID.read_text().strip()
    st, _ = dep.req("PUT", f"/records/{rid}/draft", {"metadata": metadata()}, tok)
    assert st == 200, f"metadata PUT: {st}"
    for n in FILES:
        dep.req("DELETE", f"/records/{rid}/draft/files/{n}", None, tok)
    st, _ = dep.req("POST", f"/records/{rid}/draft/files", [{"key": n} for n in FILES], tok)
    assert st in (200, 201), f"file init: {st}"
    for n in FILES:
        st, _ = dep.req("PUT", f"/records/{rid}/draft/files/{n}/content",
                        (HERE / n).read_bytes(), tok, ctype="application/octet-stream")
        assert st in (200, 201), f"upload {n}: {st}"
        st, d = dep.req("POST", f"/records/{rid}/draft/files/{n}/commit", {}, tok)
        assert st == 200, f"commit {n}: {st}"
        assert d["checksum"] == f"md5:{dep.md5(HERE / n)}", f"checksum mismatch on {n}"
        print(f"  {n} ok {d['size']} B")
    print("draft filled. This script does not publish.")
    return 0


def readback():
    tok, rid = dep.token(), DRAFT_ID.read_text().strip()
    st, d = dep.req("GET", f"/records/{rid}/draft", None, tok)
    assert st == 200, f"readback: {st}"
    bad = [k for k, v in metadata().items() if not dep.agrees(v, d["metadata"].get(k))]
    st, f = dep.req("GET", f"/records/{rid}/draft/files", None, tok)
    remote = {e["key"]: e.get("checksum") for e in f.get("entries", [])}
    bad += [f"file:{n}" for n in FILES if remote.get(n) != f"md5:{dep.md5(HERE / n)}"]
    print(f"doi: {d.get('pids', {}).get('doi', {}).get('identifier')}")
    print(f"files: {sorted(remote)}")
    print(f"divergent: {bad or 'none'}")
    return 1 if bad else 0


if __name__ == "__main__":
    a = sys.argv[1:] or ["--plan"]
    fn = {"--plan": plan, "--create-draft": create_draft, "--build": build,
          "--fill": fill, "--readback": readback}.get(a[0])
    if not fn:
        sys.exit(__doc__)
    sys.exit(fn())
