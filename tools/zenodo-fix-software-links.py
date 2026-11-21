#!/usr/bin/env python3
"""Point the software links of published Zenodo records at the commits that replaced them.

Why it exists. The history rewrite of 2026-11-08 (docs/HISTORY-REWRITE-2026-11-08.md) gave new
hashes to the commits after the first bad one. Five records deposited before or around that date
link their code with `isSupplementedBy` to a `tree/<old hash>/<dir>` URL, and GitHub now answers
404 for each. The fix is a metadata edit of the published record: same DOI, same files, only the
link changes. labf.bio was fixed the same way in site-labf#67.

  --plan       read-only, no token: current link, new link, the directory at the new commit, and
               the new URL on GitHub (must answer 200).
  --edit       WRITE: opens the edit draft of each published record (POST /records/<id>/draft) and
               replaces the old URL by the new one in related_identifiers; nothing else changes.
  --readback   read-only (token): each edit draft against its published record; the only allowed
               difference is the link.

This script never publishes (the imported req refuses any /actions/publish URL). Publishing each
edit is manual and the author's, from https://zenodo.org/uploads/<id>.

Mapping. Four old hashes come from docs/history-rewrite-2026-11-08-commit-map.txt. `d987dd4` is not
in it: it was a branch commit of #635, squashed into 4b8be1d, which the rewrite mapped to e96ad23.
`paper3-construction/` is identical at both, except that e96ad23 also holds the deposit copy
`deposit/construction-before-search-v1.1.md`.
"""
import copy
import importlib.util
import json
import pathlib
import subprocess
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("dep", ROOT / "paper3-construction/deposit/deposit.py")
dep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dep)

GH = "https://github.com/totobusnello/memoria-nox/tree/"
OLD_TO_NEW = {
    "a7903e6a8cadb9e07b4facbc1b9ee924d876cc74": "d2b71ed40a488d164dced7952b8e8f3cb86c02dc",
    "5185bf4cfdb936da12cff5c94503537c3ed26fd2": "47fdb4bb8af40dab26825625fb9eec5c3dc8e354",
    "ca7c85b514d7fcb552f792b8c50a8d06d3084689": "5d9342ae52bce779449368860613c48a2e16c2c2",
    "d987dd4": "e96ad2347d198ec9692a1bfedbeb96726a6b76aa",
}
RECORDS = ["24017459", "24017487", "24046282", "24057928", "23966758"]


def new_url(url):
    if not url.startswith(GH):
        return None
    ref, _, path = url[len(GH):].partition("/")
    return GH + OLD_TO_NEW[ref] + ("/" + path if path else "") if ref in OLD_TO_NEW else None


def http_status(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def fixed(related):
    out, n = [], 0
    for r in related:
        r = copy.deepcopy(r)
        nu = new_url(r.get("identifier", ""))
        if nu:
            r["identifier"], n = nu, n + 1
        out.append(r)
    return out, n


def plan():
    bad = 0
    for rid in RECORDS:
        st, d = dep.req("GET", f"/records/{rid}")
        assert st == 200, f"{rid}: {st}"
        print(f"{rid} v{d['metadata'].get('version')}  {d['metadata']['title'][:60]}")
        for r in d["metadata"].get("related_identifiers", []):
            nu = new_url(r["identifier"])
            if not nu:
                continue
            ref, _, path = nu[len(GH):].partition("/")
            exists = subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", f"{ref}:{path}"],
                                    capture_output=True).returncode == 0
            old_st, new_st = http_status(r["identifier"]), http_status(nu)
            ok = exists and new_st == 200
            bad += not ok
            print(f"   {r['identifier'][len(GH):][:20]}… ({old_st}) -> {ref[:7]}/{path} "
                  f"(dir {'ok' if exists else 'MISSING'}, GitHub {new_st})")
    print(f"\nplan {'PASS' if not bad else 'FAIL'}")
    return 1 if bad else 0


def edit():
    tok = dep.token()
    for rid in RECORDS:
        st, d = dep.req("POST", f"/records/{rid}/draft", {}, tok)
        assert st in (200, 201), f"{rid} edit draft: {st} {d}"
        rel, n = fixed(d["metadata"].get("related_identifiers", []))
        assert n >= 1, f"{rid}: no link to fix"
        body = {"metadata": dict(d["metadata"], related_identifiers=rel), "access": d["access"],
                "files": {"enabled": d["files"]["enabled"]}}
        if d.get("pids"):
            body["pids"] = d["pids"]
        st, d2 = dep.req("PUT", f"/records/{rid}/draft", body, tok)
        assert st == 200, f"{rid} PUT: {st} {d2}"
        print(f"{rid}: {n} link(s) replaced in the edit draft (not published)")
    return 0


def readback():
    tok, bad = dep.token(), 0
    for rid in RECORDS:
        st, pub = dep.req("GET", f"/records/{rid}", None, tok)
        st2, dr = dep.req("GET", f"/records/{rid}/draft", None, tok)
        assert st == 200 and st2 == 200, f"{rid}: {st} {st2}"
        want, _ = fixed(pub["metadata"].get("related_identifiers", []))
        got = dr["metadata"].get("related_identifiers", [])
        others = [k for k in set(pub["metadata"]) | set(dr["metadata"])
                  if k != "related_identifiers" and pub["metadata"].get(k) != dr["metadata"].get(k)]
        links_ok = [r["identifier"] for r in want] == [r["identifier"] for r in got]
        fine = links_ok and not others
        bad += not fine
        print(f"{rid}: links {'ok' if links_ok else 'DIFFER'}; other fields changed: {others or 'none'}")
    print(f"\nreadback {'PASS' if not bad else 'FAIL'}")
    return 1 if bad else 0


if __name__ == "__main__":
    fn = {"--plan": plan, "--edit": edit, "--readback": readback}.get((sys.argv[1:] or ["--plan"])[0])
    if not fn:
        sys.exit(__doc__)
    sys.exit(fn())
