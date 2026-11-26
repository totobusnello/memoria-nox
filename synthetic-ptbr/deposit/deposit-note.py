#!/usr/bin/env python3
"""The synthetic PT-BR corpus and its note, as one Zenodo record (resource type dataset). v1.0 was a new
record (24535848, concept 24535847); v1.1 adds the step 2 section and is a new version of it.

The Zenodo helpers (token, req, md5, sha256, creators, privacy_scan, agrees) are Paper 3's
(paper3-construction/deposit/deposit.py), imported, so every deposit goes the same way and the
publish refusal lives in one place.

  --plan            read-only, no token: archive file list, gates, privacy gate, and whether the
                    note is ready (status line in place, PUB_DATE and NOTE_COMMIT set).
  --create-draft    WRITE: POST /api/records/<PREV>/versions (refuses unless PREV is the latest
                    published version), reserves the DOI, stores the id in .draft-id-note-v<VERSION>
                    (gitignored). Refuses if it exists. Files are uploaded fresh, never imported.
  --build           local: deposit copy of ../NOTE.md (status line only), the PDF with the
                    DOI line, the dataset archive, SHA256SUMS, privacy gate. Never edits ../NOTE.md.
  --fill            WRITE: metadata and files, md5-checked.
  --readback        read-only (token): every metadata field and every file checksum.

This script never publishes (the imported req refuses any /actions/publish URL). Publishing is
manual and the author's.

The archive holds every file under synthetic-ptbr/ that git tracks at NOTE_COMMIT (corpus, plan,
generation records, frozen results, code, tests, this script), the anchor resolver the full run
calls (eval/resolve-gold-anchors.py), the provenance gate (tools/provenance.py) and the repository
LICENSE, under their repository paths. Files are read from that commit, not from the working tree,
so the archive is exactly what the software link points at.
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

VERSION = "1.1"
PREV = "24535848"  # v1.0, published 2026-11-25
SLUG = "memory-ruler-failure-mechanisms-synthetic-ptbr"
MD, PDF = f"{SLUG}-v{VERSION}.md", f"{SLUG}-v{VERSION}.pdf"
CODE = f"synthetic-ptbr-corpus-and-code-v{VERSION}.zip"
FILES = [PDF, MD, CODE, "SHA256SUMS"]
DESC = HERE / f"description-note-v{VERSION}.html"
DRAFT_ID = HERE / f".draft-id-note-v{VERSION}"
PUB_DATE = os.environ.get("PUB_DATE", "")
TITLE = ("Running a memory ruler's failure mechanisms in public: a synthetic Portuguese corpus and "
         "two versions of nox-mem")
REPO_COMMIT = os.environ.get("NOTE_COMMIT", "")
EXTRA = ["eval/resolve-gold-anchors.py", "tools/provenance.py", "LICENSE"]
SUBJECTS = ["agent memory", "retrieval evaluation", "synthetic corpus", "Brazilian Portuguese",
            "nDCG", "incomplete relevance judgments", "gold references", "reproducibility", "dataset",
            "LLM judges", "pre-registration"]
STATUS_OLD = ("Status: working draft, not deposited, not peer reviewed. A dataset with a short note: the corpus was\n"
              "generated, both versions were run and Paper A's judges were re-run on it on 2026-11-25. "
              "`PROVENANCE.json` holds the source of every\n"
              "decimal number and percentage in this note, and a gate checks each one against it.")


def status_new(doi):
    return (f"Version {VERSION} ({PUB_DATE}), doi:{doi}. Not peer reviewed. A dataset with a short note: "
            "the corpus was generated, both versions were run and Paper A's judges were re-run on it on "
            "2026-11-25. Version 1.1 adds section 5 (step 2); version 1.0 is doi:10.5281/zenodo.24535848. "
            "`PROVENANCE.json`, in the archive of this record, holds the source of every decimal number and "
            "percentage in this note, and a gate checks each one against it. The archive carries everything "
            "section 8 lists.")


def archive_files():
    """Paths at NOTE_COMMIT: every tracked file under synthetic-ptbr/, plus EXTRA."""
    out = subprocess.run(["git", "ls-tree", "-r", "--name-only", REPO_COMMIT, "synthetic-ptbr/"],
                         cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    return sorted(out) + EXTRA


def at_commit(path):
    return subprocess.run(["git", "show", f"{REPO_COMMIT}:{path}"], cwd=ROOT,
                          capture_output=True, check=True).stdout


def metadata():
    rel = []
    if REPO_COMMIT:
        rel.append({"identifier": f"https://github.com/totobusnello/memoria-nox/tree/{REPO_COMMIT}/synthetic-ptbr",
                    "scheme": "url", "relation_type": {"id": "issupplementedby"},
                    "resource_type": {"id": "software"}})
    rel.append({"identifier": "10.5281/zenodo.24400444", "scheme": "doi",
                "relation_type": {"id": "references"}, "resource_type": {"id": "publication-preprint"}})
    return {
        "resource_type": {"id": "dataset"},
        "title": TITLE,
        "publication_date": PUB_DATE,
        "creators": dep.creators(),
        "description": DESC.read_text(encoding="utf-8"),
        "version": VERSION,
        "publisher": "Zenodo",
        "languages": [{"id": "eng"}, {"id": "por"}],
        "rights": [{"id": "cc-by-4.0"}, {"id": "mit"}],
        "subjects": [{"subject": s} for s in SUBJECTS],
        "related_identifiers": rel,
    }


def readiness(text):
    """Every reason the note is not ready to deposit; empty when it is."""
    why = []
    if text.count(STATUS_OLD) != 1:
        why.append("the status anchor is missing or repeated")
    if not PUB_DATE:
        why.append("PUB_DATE is not set")
    if not REPO_COMMIT:
        why.append("NOTE_COMMIT is not set")
    elif subprocess.run(["git", "merge-base", "--is-ancestor", REPO_COMMIT, "origin/main"], cwd=ROOT).returncode:
        # a branch commit vanishes at squash-merge: the software link would point at nothing
        why.append(f"NOTE_COMMIT {REPO_COMMIT} is not on origin/main")
    return why


def deposit_text(doi="10.5281/zenodo.RESERVED"):
    text = at_commit("synthetic-ptbr/NOTE.md").decode("utf-8")
    why = readiness(text)
    assert not why, "not ready to deposit: " + "; ".join(why)
    text = text.replace(STATUS_OLD, status_new(doi))
    assert "not deposited" not in text
    return text


def gates():
    ok = True
    for cmd in (["python3", "-I", "tools/provenance.py", "--check", "synthetic-ptbr"],
                ["python3", "-I", "synthetic-ptbr/test-synthetic.py"],
                ["python3", "-I", "synthetic-ptbr/method-tests.py", "--analyze", "--check"],
                ["python3", "-I", "synthetic-ptbr/stage2/pairs.py", "--check"],
                ["python3", "-I", "synthetic-ptbr/stage2/test-stage2.py"],
                ["python3", "-I", "synthetic-ptbr/stage2/analyze.py", "--check"],
                ["python3", "-I", "synthetic-ptbr/stage2/supplement.py", "--check"]):
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        print("  " + (r.stdout.strip() or r.stderr.strip()).splitlines()[-1])
        ok = ok and r.returncode == 0
    return ok


def build():
    if not DRAFT_ID.exists():
        sys.exit(f"no {DRAFT_ID.name} — run --create-draft first")
    doi = f"10.5281/zenodo.{DRAFT_ID.read_text().strip()}"
    (HERE / MD).write_text(deposit_text(doi), encoding="utf-8")
    env = dict(os.environ, NOTE_MD=str(HERE / MD), NOTE_LINE=f"Version {VERSION} · doi:{doi}")
    r = subprocess.run(["bash", str(PLAN / "pdf-build/build-note-pdf.sh")], env=env,
                       capture_output=True, text=True)
    print(r.stdout.strip() or r.stderr.strip()[-600:])
    assert r.returncode == 0, "pdf build failed"
    (PLAN / "pdf-build/NOTE.pdf").replace(HERE / PDF)
    pdftext = subprocess.run(["pdftotext", "-enc", "UTF-8", str(HERE / PDF), "-"],
                             capture_output=True).stdout.decode()
    assert doi in pdftext, "the DOI is not in the PDF text"
    names = archive_files()
    with zipfile.ZipFile(HERE / CODE, "w", zipfile.ZIP_DEFLATED) as z:
        for f in names:
            zi = zipfile.ZipInfo(f, (2026, 11, 25, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, at_commit(f))
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
    print(f"  archive: {len(names)} files")
    for n in FILES:
        print(f"  {n}  {(HERE / n).stat().st_size} B  md5:{dep.md5(HERE / n)}")
    print(f"build ok with DOI {doi}")
    return 0


def plan():
    print(f"title: {TITLE}")
    ok_gates = gates()
    fnd = dep.privacy_scan("description", DESC.read_text()) if DESC.exists() else []
    why, names = [], []
    if REPO_COMMIT:
        names = archive_files()
        text = at_commit("synthetic-ptbr/NOTE.md").decode("utf-8")
        print(f"note at {REPO_COMMIT}: {len(text.split())} words · archive: {len(names)} files")
        fnd += dep.privacy_scan("note", text)
        for f in names:
            fnd += dep.privacy_scan(f, at_commit(f))
        why = readiness(text)
    else:
        why = readiness((PLAN / "NOTE.md").read_text(encoding="utf-8"))
    for f in fnd:
        print("  PRIVACY", f)
    for w in why:
        print("  NOT READY", w)
    print(f"\ngates {'PASS' if ok_gates else 'FAIL'} · privacy {'PASS' if not fnd else 'FAIL'} · "
          f"description {'PASS' if DESC.exists() else 'FAIL'} · ready {'YES' if not why else 'NO'}")
    return 0 if ok_gates and not fnd and DESC.exists() and not why else 1


def create_draft():
    if DRAFT_ID.exists():
        sys.exit(f"refusing: {DRAFT_ID.name} already exists ({DRAFT_ID.read_text().strip()})")
    why = readiness(at_commit("synthetic-ptbr/NOTE.md").decode("utf-8") if REPO_COMMIT
                    else (PLAN / "NOTE.md").read_text(encoding="utf-8"))
    if why:
        sys.exit("refusing: " + "; ".join(why))
    tok = dep.token()
    st, latest = dep.req("GET", f"/records/{PREV}/versions/latest", None, tok)
    lid = str(latest.get("id")) if st == 200 and isinstance(latest, dict) else None
    if lid != PREV:
        sys.exit(f"refusing: v1.0 ({PREV}) is not the latest version (latest = {lid})")
    st, d = dep.req("POST", f"/records/{PREV}/versions", None, tok)
    assert st in (200, 201), f"new version: {st} {str(d)[:400]}"
    rid = str(d["id"])
    DRAFT_ID.write_text(rid + "\n")
    st, _ = dep.req("PUT", f"/records/{rid}/draft", {"metadata": metadata()}, tok)
    assert st == 200, f"metadata PUT: {st}"
    st2, d2 = dep.req("POST", f"/records/{rid}/draft/pids/doi", {}, tok)
    print(f"draft {rid} (new version of {PREV}, NOT published) · reserve doi {st2} · "
          f"{d2.get('pids', {}).get('doi', {}).get('identifier')}")
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
