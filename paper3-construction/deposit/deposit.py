#!/usr/bin/env python3
"""Paper 3's pre-registration on Zenodo: a NEW record (not a version of another one).

Same shape as datanote-telemetry/deposit/deposit.py, which is the house pattern:

  --plan            read-only, no token: prints the metadata it would write and checks the package.
  --create-draft    WRITE: POST /api/records (a new draft), then reserves its DOI. Stores the id in
                    .draft-id (gitignored). Refuses if .draft-id exists.
  --build           local: with the reserved DOI, writes the deposit copy of the plan, builds the
                    PDF with the DOI line, zips the code, writes SHA256SUMS, runs the privacy gate.
                    Never edits ../PREREGISTRATION-DRAFT.md.
  --fill            WRITE: metadata (PUT, keeping the reserved DOI) and the files, md5-checked.
  --readback        read-only (token): every metadata field and every file checksum. Exit 1 on divergence.

This script never publishes. It has no publish call, and req() refuses any URL with
/actions/publish. Publishing is manual, irreversible, and the author's.

⚠️ A pre-registration deposited AFTER its run is not a pre-registration. --fill prints the
reminder; the ordering is the author's to honour.

Token: ZENODO_TOKEN in the environment, or ~/.config/secrets/ZENODO_TOKEN.
"""
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
PLAN = HERE.parent
API = "https://zenodo.org/api"
VERSION = "1.0"
SLUG = "construction-interaction-prereg"
MD, PDF = f"{SLUG}-v{VERSION}.md", f"{SLUG}-v{VERSION}.pdf"
CODE = f"code-v{VERSION}.zip"
FILES = [PDF, MD, CODE, "SHA256SUMS"]
DESC = HERE / f"description-v{VERSION}.html"
DRAFT_ID = HERE / ".draft-id"
# creators are copied from an already-published record so authorship stays identical
# across deposits rather than being retyped here.
CREATORS_FROM = "23041503"          # Paper 1 v1.0.2
PUB_DATE = "2026-10-27"
REPO_TAG = "paper3-prereg-v1.0"
CODE_FILES = ["lme-census.py", "lme-independence.py", "lme-answer-overlap.py",
              "power-additive.py", "see-once-denominator.py",
              "pdf-build/build-pdf.sh", "pdf-build/preamble-prereg.tex",
              "deposit/deposit.py", "README.md"]
SUBJECTS = ["pre-registration", "agent memory", "memory construction", "write path",
            "factorial design", "LongMemEval", "retrieval evaluation", "judge agreement"]

# The deposit copy differs from the repository draft in two ways, both declared:
#   1. status wording — the draft says "DRAFT for approval, not deposited";
#   2. emoji -> textual labels, because the paper preamble's fonts carry no emoji
#      and the build gate requires zero missing glyphs. The labels preserve the
#      distinction the emoji carried (defect / limit / closed / key finding).
EDITS = [
    ("# Pre-registration plan — the construction interaction. DRAFT for approval, not deposited.",
     "# Pre-registration plan — the construction interaction"),
    ("> 📌 **DEPOSIT CANDIDATE — §11 is the active design; §4 is kept as the blocked first attempt.**",
     "> **Status.** Version 1.0. §11 is the active design; §4 is kept as the blocked first attempt. "
     "Not peer reviewed."),
]
EMOJI = {"\U0001F534": "[defect] ", "⚠️": "[limit] ", "⚠": "[limit] ",
         "✅": "[closed] ", "\U0001F511": "[key] ", "\U0001F4CC": "[status] ",
         "\U0001F525": "[result] ", "⏸️": "[held] ", "⏸": "[held] ",
         "⛔": "[never] ", "ℹ️": "[note] ", "ⓘ": "[note] "}

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


def req(method, path, body=None, tok=None, ctype="application/json",
        accept="application/vnd.inveniordm.v1+json"):
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
    if not DRAFT_ID.exists():
        sys.exit("no .draft-id — run --create-draft first")
    return f"10.5281/zenodo.{DRAFT_ID.read_text().strip()}"


def creators():
    st, d = req("GET", f"/records/{CREATORS_FROM}")
    assert st == 200, f"source record for creators returned {st}"
    out = []
    for c in d["metadata"]["creators"]:
        p = c["person_or_org"]
        out.append({"person_or_org": {k: p[k] for k in
                                      ("type", "name", "given_name", "family_name", "identifiers")
                                      if k in p},
                    "affiliations": [{"name": a["name"]} for a in c.get("affiliations", [])]})
    return out


def metadata():
    src = HERE / MD if (HERE / MD).exists() else PLAN / "PREREGISTRATION-DRAFT.md"
    title = src.read_text(encoding="utf-8").split("\n", 1)[0].lstrip("# ").strip()
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
            {"identifier": "10.5281/zenodo.23041503", "scheme": "doi",
             "relation_type": {"id": "references"},
             "resource_type": {"id": "publication-preprint"}},
            {"identifier": "10.5281/zenodo.23354363", "scheme": "doi",
             "relation_type": {"id": "references"},
             "resource_type": {"id": "publication-preprint"}},
            {"identifier": f"https://github.com/totobusnello/memoria-nox/tree/{REPO_TAG}/paper3-construction",
             "scheme": "url", "relation_type": {"id": "issupplementedby"},
             "resource_type": {"id": "software"}},
        ],
    }


def privacy_scan(name, data):
    txt = data.decode("utf-8", "replace") if isinstance(data, bytes) else data
    hits = [(name, p) for p in PRIVATE if re.search(p, txt, flags=re.I)]
    for w in set(re.findall(r"[\w.@-]+", txt.lower())):
        for cand in {w, w.split("@")[-1].split(".")[0]}:
            h = hashlib.sha256(cand.encode()).hexdigest()
            if h[:16] in PRIVATE_WORD_SHA:
                hits.append((name, "private word (hash " + h[:8] + ")"))
    return hits


def deposit_text():
    text = (PLAN / "PREREGISTRATION-DRAFT.md").read_text(encoding="utf-8")
    for old, new in EDITS:
        assert old in text, f"EDITS anchor missing: {old[:60]!r}"
        text = text.replace(old, new)
    for e, lab in EMOJI.items():
        text = text.replace(e + " ", lab).replace(e, lab)
    # Allow the typographic and mathematical symbols the PDF build has already
    # shown it renders (the test build reported missing glyphs for emoji only).
    # The gate exists for PICTOGRAPHS, which the fonts do not carry — not for
    # mathematics, which the document legitimately uses.
    # Allowed by CODEPOINT, not by typing the glyph: the first attempt wrote a
    # hyphen where it meant U+2212 MINUS SIGN and the gate kept rejecting a
    # character the allowlist appeared to contain.
    OK_SYMBOLS = "".join(chr(c) for c in (
        0x2013, 0x2014, 0x2018, 0x2019, 0x201C, 0x201D, 0x2026,   # – — ‘ ’ “ ” …
        0x2190, 0x2192, 0x2194, 0x21D2,                           # ← → ↔ ⇒
        0x2208, 0x2209, 0x2212, 0x2213, 0x221A, 0x221E,           # ∈ ∉ − ∓ √ ∞
        0x2211, 0x220F, 0x2205, 0x2282, 0x2286, 0x222A, 0x2229,   # ∑ ∏ ∅ ⊂ ⊆ ∪ ∩
        0x2248, 0x2260, 0x2264, 0x2265, 0x00D7, 0x00B1, 0x00B0,   # ≈ ≠ ≤ ≥ × ± °
        0x00B7, 0x2022, 0x00A7, 0x00B6, 0x2020, 0x2021, 0x2030,   # · • § ¶ † ‡ ‰
        0x0394, 0x03C1, 0x03C3, 0x03B1, 0x03B2, 0x03B3, 0x03BB,   # Δ ρ σ α β γ λ
        0x00B5, 0x2032, 0x2033,                                    # µ ′ ″
    ))
    left = [c for c in set(text) if ord(c) > 0x2100 and c not in OK_SYMBOLS]
    assert not left, (f"pictographs left in the deposit copy: "
                      f"{[(c, hex(ord(c))) for c in left]} — add them to EMOJI")
    assert "not deposited" not in text, "pre-deposit wording left in the deposit copy"
    return text


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
    assert doi in pdftext, "the DOI is not in the PDF text"
    with zipfile.ZipFile(HERE / CODE, "w", zipfile.ZIP_DEFLATED) as z:
        for f in CODE_FILES:
            zi = zipfile.ZipInfo(f"paper3-construction/{f}", (2026, 10, 27, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, (PLAN / f).read_bytes())
    (HERE / "SHA256SUMS").write_text(
        "\n".join(f"{sha256((HERE / n).read_bytes())}  {n}" for n in (PDF, MD, CODE)) + "\n")
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
    print(f"build ok with DOI {doi}")
    return 0


def plan():
    txt = deposit_text()
    print(f"deposit copy: {len(txt)} chars, {len(txt.splitlines())} lines")
    print(f"title: {txt.splitlines()[0].lstrip('# ').strip()}")
    print(f"version {VERSION} · {PUB_DATE} · cc-by-4.0 · {len(SUBJECTS)} subjects")
    print(f"files it would upload: {FILES}")
    print(f"code zip would carry {len(CODE_FILES)} files:")
    for f in CODE_FILES:
        q = PLAN / f
        print(f"  {'ok ' if q.exists() else 'MISSING'} {f}")
    missing = [f for f in CODE_FILES if not (PLAN / f).exists()]
    print(f"description: {'ok, ' + str(len(DESC.read_text())) + ' chars' if DESC.exists() else 'MISSING'}")
    fnd = privacy_scan("deposit copy", txt) + (privacy_scan("description", DESC.read_text())
                                               if DESC.exists() else [])
    for f in fnd:
        print("  PRIVACY", f)
    print(f"\nprivacy gate: {'PASS' if not fnd else 'FAIL'} · "
          f"code files: {'PASS' if not missing else 'FAIL ' + str(missing)} · "
          f"description: {'PASS' if DESC.exists() else 'FAIL'}")
    return 0 if not fnd and not missing and DESC.exists() else 1


def create_draft():
    if DRAFT_ID.exists():
        sys.exit(f"refusing: .draft-id already exists ({DRAFT_ID.read_text().strip()})")
    tok = token()
    st, d = req("POST", "/records", {"metadata": metadata(), "access":
                {"record": "public", "files": "public"}, "files": {"enabled": True}}, tok)
    assert st in (200, 201), f"create draft: {st} {d}"
    rid = d["id"]
    DRAFT_ID.write_text(str(rid) + "\n")
    st2, d2 = req("POST", f"/records/{rid}/draft/pids/doi", {}, tok)
    print(f"draft {rid} · reserve doi {st2} · {d2.get('pids', {}).get('doi', {}).get('identifier')}")
    return 0


def fill():
    tok, rid = token(), DRAFT_ID.read_text().strip()
    st, _ = req("PUT", f"/records/{rid}/draft", {"metadata": metadata()}, tok)
    assert st == 200, f"metadata PUT: {st}"
    for n in FILES:
        req("DELETE", f"/records/{rid}/draft/files/{n}", None, tok)
    st, _ = req("POST", f"/records/{rid}/draft/files", [{"key": n} for n in FILES], tok)
    assert st in (200, 201), f"file init: {st}"
    for n in FILES:
        b = (HERE / n).read_bytes()
        st, _ = req("PUT", f"/records/{rid}/draft/files/{n}/content", b, tok,
                    ctype="application/octet-stream")
        assert st in (200, 201), f"upload {n}: {st}"
        st, d = req("POST", f"/records/{rid}/draft/files/{n}/commit", {}, tok)
        assert st == 200, f"commit {n}: {st}"
        assert d["checksum"] == f"md5:{md5(HERE / n)}", f"checksum mismatch on {n}"
        print(f"  {n} ok {d['size']} B")
    print("\n⚠️  A pre-registration deposited AFTER its run is not a pre-registration.")
    print("   Publish BEFORE the run, from the Zenodo UI. This script does not publish.")
    return 0


def readback():
    tok, rid = token(), DRAFT_ID.read_text().strip()
    st, d = req("GET", f"/records/{rid}/draft", None, tok)
    assert st == 200, f"readback: {st}"
    want, got, bad = metadata(), d["metadata"], []
    for k, v in want.items():
        if got.get(k) != v:
            bad.append(k)
    st, f = req("GET", f"/records/{rid}/draft/files", None, tok)
    remote = {e["key"]: e.get("checksum") for e in f.get("entries", [])}
    for n in FILES:
        if remote.get(n) != f"md5:{md5(HERE / n)}":
            bad.append(f"file:{n}")
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
