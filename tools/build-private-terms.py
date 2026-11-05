#!/usr/bin/env python3
"""Builds the private-term hash list that tools/privacy-gate.py reads.

Reads private files given on the command line (they live OUTSIDE this repository, e.g. the backup
of the files removed from `main` on 2026-11-04) and writes sha256 prefixes of the identifiers they
carry to ~/.config/memoria-nox/private-terms.sha256. Only hashes are written; the terms never
enter the repository.

Which terms: entity names (`source`, `target`) of knowledge-graph rows, and the base names of
private documents (`source_file` under the vault or the Mac event log, and people entities).
A term that already occurs anywhere in the tracked repository is dropped: the gate checks only
ADDED lines, and a term the repository already uses legitimately would block ordinary work.
Terms shorter than 4 characters are dropped for the same reason.

  python3 tools/build-private-terms.py <private.json|jsonl> [...]
"""
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys

OUT = pathlib.Path(os.environ.get(
    "PRIVACY_TERMS_FILE", pathlib.Path.home() / ".config/memoria-nox/private-terms.sha256"))
PRIVATE_PREFIXES = ("memory/" + "mac-docs/", "events/" + "mac/", "memory/" + "entities/" + "people/")


def records(path):
    txt = pathlib.Path(path).read_text(encoding="utf-8")
    try:
        obj = json.loads(txt)
        objs = [obj]
    except json.JSONDecodeError:
        objs = [json.loads(l) for l in txt.splitlines() if l.strip()]
    stack = list(objs)
    while stack:
        o = stack.pop()
        if isinstance(o, dict):
            yield o
            stack.extend(o.values())
        elif isinstance(o, list):
            stack.extend(o)


def candidates(paths):
    for p in paths:
        for r in records(p):
            for k in ("source", "target"):
                if isinstance(r.get(k), str):
                    yield r[k]
            sf = r.get("source_file")
            if isinstance(sf, str) and sf.startswith(PRIVATE_PREFIXES):
                stem = pathlib.PurePath(sf).stem
                yield stem
                yield re.sub(r"[-_]+", " ", stem)


def norm(s):
    words = [w.strip(".-") for w in re.findall(r"[\w@.-]+", s.lower())]
    return " ".join(w for w in words if w)


def main(paths):
    if not paths:
        sys.exit(__doc__)
    terms = {norm(c) for c in candidates(paths)}
    terms = {t for t in terms if len(t) >= 4 and 1 <= len(t.split()) <= 4}
    kept = []
    for t in sorted(terms):
        r = subprocess.run(["git", "grep", "-qiF", "--", t], capture_output=True)
        if r.returncode == 1:          # not in the tracked repository
            kept.append(hashlib.sha256(t.encode("utf-8")).hexdigest()[:16])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("# sha256[:16] of private terms; built by tools/build-private-terms.py\n"
                   + "\n".join(sorted(set(kept))) + "\n")
    os.chmod(OUT, 0o600)
    print(f"{len(terms)} candidate terms, {len(kept)} kept (absent from the tracked repository)"
          f" -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
