#!/usr/bin/env python3
"""The confirmatory RESULT of Paper 3's v1.3 pre-registration, as its own Zenodo record.

A result is a different work from the plan it tests, so it is a NEW record, not a new version of
the pre-registration (concept 10.5281/zenodo.23716612). It references the published plan
(10.5281/zenodo.23934489), which was public before the run started.

Same commands and gates as deposit.py, whose helpers it imports rather than copies:

  --plan            read-only, no token: metadata, file list, privacy gate.
  --create-draft    WRITE: POST /api/records (a new draft), then reserves its DOI. Stores the id in
                    .draft-id-result (gitignored). Refuses if that file exists.
  --build           local: deposit copy of ../CONFIRM-RESULT.md with the reserved DOI, PDF, data
                    zip, SHA256SUMS, privacy gate. Never edits ../CONFIRM-RESULT.md.
  --fill            WRITE: metadata and files, md5-checked.
  --readback        read-only (token): every metadata field and every file checksum.

This script never publishes (deposit.req refuses any /actions/publish URL). Publishing is manual,
irreversible, and the author's.
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
SLUG = "construction-interaction-confirm"
MD, PDF = f"{SLUG}-v{VERSION}.md", f"{SLUG}-v{VERSION}.pdf"
DATA = f"data-v{VERSION}.zip"
FILES = [PDF, MD, DATA, "SHA256SUMS"]
DESC = HERE / f"description-confirm-v{VERSION}.html"
DRAFT_ID = HERE / ".draft-id-result"
PUB_DATE = "2026-11-04"
PREREG_DOI = "10.5281/zenodo.23934489"
# The commit that versioned the run (PR #631). A commit URL is immutable, so no tag is needed.
REPO_COMMIT = "6695c60"
RUN = "runs/confirm-2026-11-04"
DATA_FILES = ["CONFIRM-RESULT.md", "README.md",
              f"{RUN}/receipt.json", f"{RUN}/rows.ndjson",
              f"{RUN}/analysis.txt", f"{RUN}/analysis.json",
              f"{RUN}/spend/20261104T021231Z-10178.json",
              f"{RUN}/spend/20261104T030743Z-87138.json",
              f"{RUN}/spend/20261104T094932Z-80027.json",
              # what produced and what reads the rows; v13-manifest.py imports stage1-manifest.py
              "lme-run.py", "lme-analyze.py", "v13-manifest.py", "v13-manifest.json",
              "v12-manifest.json", "stage1-manifest.py", "stage1-manifest.json",
              "deposit/deposit.py", "deposit/deposit-result.py"]
SUBJECTS = ["confirmatory result", "pre-registration", "agent memory", "memory construction",
            "write path", "factorial design", "LongMemEval", "judge agreement"]
TITLE = ("Construction before search: confirmatory result of the pre-registered test "
         "of a repaired extraction criterion for LLM-extracted agent memory")

EDITS = [
    ("# Confirmatory run of v1.3 (2026-11-04)", f"# {TITLE}"),
    ("Run: `runs/confirm-2026-11-04/`\n(rows, receipt, analysis, per-process spend).",
     "Run: `runs/confirm-2026-11-04/` in `data-v1.0.zip`\n(rows, receipt, analysis, per-process spend)."),
]


def metadata():
    return {
        "resource_type": {"id": "publication-report"},
        "title": TITLE,
        "publication_date": PUB_DATE,
        "creators": dep.creators(),
        "description": DESC.read_text(encoding="utf-8"),
        "version": VERSION,
        "publisher": "Zenodo",
        "languages": [{"id": "eng"}],
        "rights": [{"id": "cc-by-4.0"}],
        "subjects": [{"subject": s} for s in SUBJECTS],
        "related_identifiers": [
            {"identifier": PREREG_DOI, "scheme": "doi",
             "relation_type": {"id": "references"},
             "resource_type": {"id": "publication-preprint"}},
            {"identifier": f"https://github.com/totobusnello/memoria-nox/tree/{REPO_COMMIT}/paper3-construction",
             "scheme": "url", "relation_type": {"id": "issupplementedby"},
             "resource_type": {"id": "software"}},
        ],
    }


def deposit_text():
    text = (PLAN / "CONFIRM-RESULT.md").read_text(encoding="utf-8")
    for old, new in EDITS:
        assert old in text, f"EDITS anchor missing: {old[:60]!r}"
        text = text.replace(old, new)
    return text


def draft_doi():
    if not DRAFT_ID.exists():
        sys.exit("no .draft-id-result — run --create-draft first")
    return f"10.5281/zenodo.{DRAFT_ID.read_text().strip()}"


def build():
    doi = draft_doi()
    (HERE / MD).write_text(deposit_text(), encoding="utf-8")
    env = dict(os.environ, PREREG_DOI=doi, PREREG_MD=str(HERE / MD),
               PREREG_VER=f"Version {VERSION}")
    r = subprocess.run(["bash", str(PLAN / "pdf-build/build-pdf.sh")], env=env,
                       capture_output=True, text=True)
    print(r.stdout.strip() or r.stderr.strip()[-600:])
    assert r.returncode == 0, "pdf build failed"
    (PLAN / "pdf-build/PREREGISTRATION.pdf").replace(HERE / PDF)
    pdftext = subprocess.run(["pdftotext", "-enc", "UTF-8", str(HERE / PDF), "-"],
                             capture_output=True).stdout.decode()
    assert doi in pdftext and PREREG_DOI in pdftext, "a DOI is missing from the PDF text"
    with zipfile.ZipFile(HERE / DATA, "w", zipfile.ZIP_DEFLATED) as z:
        for f in DATA_FILES:
            zi = zipfile.ZipInfo(f"paper3-construction/{f}", (2026, 11, 4, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, (PLAN / f).read_bytes())
    (HERE / "SHA256SUMS").write_text(
        "\n".join(f"{dep.sha256((HERE / n).read_bytes())}  {n}" for n in (PDF, MD, DATA)) + "\n")
    findings = dep.privacy_scan(MD, (HERE / MD).read_bytes())
    findings += dep.privacy_scan(PDF + " (text)", pdftext)
    findings += dep.privacy_scan(PDF + " (bytes)", (HERE / PDF).read_bytes().decode("latin-1"))
    with zipfile.ZipFile(HERE / DATA) as z:
        for n in z.namelist():
            findings += dep.privacy_scan(f"{DATA}:{n}", z.read(n))
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
    print(f"deposit copy: {len(txt)} chars · title: {txt.splitlines()[0].lstrip('# ')}")
    print(f"version {VERSION} · {PUB_DATE} · cc-by-4.0 · references {PREREG_DOI}")
    missing = [f for f in DATA_FILES if not (PLAN / f).exists()]
    for f in DATA_FILES:
        print(f"  {'ok ' if f not in missing else 'MISSING'} {f}")
    fnd = dep.privacy_scan("deposit copy", txt)
    fnd += dep.privacy_scan("description", DESC.read_text()) if DESC.exists() else []
    for f in fnd:
        print("  PRIVACY", f)
    ok = not fnd and not missing and DESC.exists()
    print(f"\nprivacy {'PASS' if not fnd else 'FAIL'} · data files {'PASS' if not missing else 'FAIL'}"
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
