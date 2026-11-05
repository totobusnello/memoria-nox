#!/usr/bin/env python3
"""Paper A's manuscript as its own Zenodo record (a NEW record, not a version of another paper).

The Zenodo helpers (token, req, md5, sha256, creators, privacy_scan, agrees) are Paper 3's
(paper3-construction/deposit/deposit.py), imported, so both papers deposit the same way and the
publish refusal lives in one place.

  --plan            read-only, no token: deposit copy, code files, privacy gate, and whether the
                    manuscript is ready (H-A2 written, status line in place).
  --create-draft    WRITE: POST /api/records, reserves the DOI, stores the id in
                    .draft-id-manuscript-v<VERSION> (gitignored). Refuses if it exists.
  --build           local: deposit copy of ../MANUSCRIPT.md (status line only), the PDF with the
                    DOI line, a code-and-data zip, SHA256SUMS, privacy gate. Never edits
                    ../MANUSCRIPT.md.
  --fill            WRITE: metadata and files, md5-checked.
  --readback        read-only (token): every metadata field and every file checksum.

This script never publishes (the imported req refuses any /actions/publish URL). Publishing is
manual and the author's.

It refuses to build a deposit copy while the manuscript still reports H-A2 as pending: the
registered order puts H-A2 on 2026-11-18, and a paper deposited before it would report a test the
pre-registration says will be run.
"""
import importlib.util
import os
import pathlib
import subprocess
import sys
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
PLAN = HERE.parent
ROOT = PLAN.parent
spec = importlib.util.spec_from_file_location("dep", ROOT / "paper3-construction/deposit/deposit.py")
dep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dep)

VERSION = "1.0"
SLUG = "five-ways-the-ruler-misleads"
MD, PDF = f"{SLUG}-v{VERSION}.md", f"{SLUG}-v{VERSION}.pdf"
CODE = f"code-and-data-v{VERSION}.zip"
FILES = [PDF, MD, CODE, "SHA256SUMS"]
DESC = HERE / f"description-manuscript-v{VERSION}.html"
DRAFT_ID = HERE / f".draft-id-manuscript-v{VERSION}"
PUB_DATE = os.environ.get("PUB_DATE", "")
TITLE = "Five ways the ruler misleads: evaluating retrieval on a living Portuguese agent memory"
REPO_COMMIT = os.environ.get("MANUSCRIPT_COMMIT", "")
REPO_TAG = "paper-a-prereg-v1.0"
# everything a reader needs to check the numbers without the corpus: the scripts, the
# pre-registration, the commitments, the printed outputs of the reading, and the provenance file
CODE_FILES = ["PREREGISTRATION.md", "PROVENANCE.json", "quotas.json", "frame-census.txt",
              "HOLDOUT-COMMITMENT.json", "HUMAN-COMMITMENT.json",
              "results/h-a1-2026-11-05.txt", "results/v3-rescore-2026-11-05.txt",
              "results/run-2026-11-05.sha256",
              "strata.py", "derive-quotas.py", "frame-census.py", "holdout-draw.py",
              "holdout-prompt.txt", "holdout-generate.py", "score-holdout.sh", "human-sample.py",
              "read-h-a1.sh", "holdout-analyze.py", "holdout-persistence.py",
              "manuscript-tables.py", "pdf-build/build-manuscript-pdf.sh",
              "deposit/deposit-manuscript.py"]
SUBJECTS = ["agent memory", "retrieval evaluation", "pre-registration", "LLM judge",
            "relevance assessment", "nDCG", "Portuguese", "test collections"]
STATUS_OLD = ("Status: working draft, not deposited, not peer reviewed. H-A2 (§4) is pending until "
              "2026-11-18.\nEvery number in this text has an entry in `PROVENANCE.json`; §9 says how "
              "they are checked.")
PENDING = "### H-A2: pending"


def status_new(doi):
    return (f"Version {VERSION} ({PUB_DATE}), doi:{doi}. Not peer reviewed. Every number in this text "
            "has an entry in `PROVENANCE.json`, in the code-and-data archive of this record; §9 says "
            "how they are checked.")


def metadata():
    rel = [{"identifier": f"https://github.com/totobusnello/memoria-nox/tree/{REPO_TAG}/paper-a-eval-ptbr",
            "scheme": "url", "relation_type": {"id": "isderivedfrom"},
            "resource_type": {"id": "software"}}]
    if REPO_COMMIT:
        rel.append({"identifier": f"https://github.com/totobusnello/memoria-nox/tree/{REPO_COMMIT}/paper-a-eval-ptbr",
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


def readiness(text):
    """Every reason the manuscript is not ready to deposit; empty when it is."""
    why = []
    if PENDING in text:
        why.append("H-A2 is still reported as pending (registered for 2026-11-18)")
    if text.count(STATUS_OLD) != 1:
        why.append("the status anchor is missing or repeated")
    if not PUB_DATE:
        why.append("PUB_DATE is not set")
    return why


def deposit_text(doi="10.5281/zenodo.RESERVED"):
    text = (PLAN / "MANUSCRIPT.md").read_text(encoding="utf-8")
    why = readiness(text)
    assert not why, "not ready to deposit: " + "; ".join(why)
    text = text.replace(STATUS_OLD, status_new(doi))
    assert "not deposited" not in text and "pending" not in text.lower()
    return text


def gates():
    for cmd in (["python3", "-I", "tools/provenance.py", "--check", "paper-a-eval-ptbr"],
                ["python3", "-I", "paper-a-eval-ptbr/manuscript-tables.py", "--check"]):
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        print("  " + (r.stdout.strip() or r.stderr.strip()).splitlines()[-1])
        if r.returncode:
            return False
    return True


def build():
    if not DRAFT_ID.exists():
        sys.exit(f"no {DRAFT_ID.name} — run --create-draft first")
    doi = f"10.5281/zenodo.{DRAFT_ID.read_text().strip()}"
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
            zi = zipfile.ZipInfo(f"paper-a-eval-ptbr/{f}", (2026, 11, 5, 0, 0, 0))
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
    text = (PLAN / "MANUSCRIPT.md").read_text(encoding="utf-8")
    print(f"manuscript: {len(text.split())} words · title: {TITLE}")
    ok_gates = gates()
    why = readiness(text)
    missing = [f for f in CODE_FILES if not (PLAN / f).exists()]
    for f in CODE_FILES:
        print(f"  {'ok ' if f not in missing else 'MISSING'} {f}")
    fnd = dep.privacy_scan("manuscript", text)
    fnd += dep.privacy_scan("description", DESC.read_text()) if DESC.exists() else []
    for f in CODE_FILES:
        if f not in missing:
            fnd += dep.privacy_scan(f, (PLAN / f).read_bytes())
    for f in fnd:
        print("  PRIVACY", f)
    for w in why:
        print("  NOT READY", w)
    print(f"commit for the software link: {REPO_COMMIT or 'NOT SET (MANUSCRIPT_COMMIT)'}")
    print(f"\ngates {'PASS' if ok_gates else 'FAIL'} · privacy {'PASS' if not fnd else 'FAIL'} · "
          f"code files {'PASS' if not missing else 'FAIL'} · description "
          f"{'PASS' if DESC.exists() else 'FAIL'} · ready {'YES' if not why else 'NO'}")
    return 0 if ok_gates and not fnd and not missing and DESC.exists() and not why and REPO_COMMIT else 1


def create_draft():
    if DRAFT_ID.exists():
        sys.exit(f"refusing: {DRAFT_ID.name} already exists ({DRAFT_ID.read_text().strip()})")
    why = readiness((PLAN / "MANUSCRIPT.md").read_text(encoding="utf-8"))
    if why:
        sys.exit("refusing: " + "; ".join(why))
    tok = dep.token()
    st, d = dep.req("POST", "/records", {"metadata": metadata(), "access":
                    {"record": "public", "files": "public"}, "files": {"enabled": True}}, tok)
    assert st in (200, 201), f"draft: {st} {d}"
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
