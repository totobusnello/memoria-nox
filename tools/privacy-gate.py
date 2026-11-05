#!/usr/bin/env python3
"""Privacy gate for this PUBLIC repository: blocks private-corpus content before it is committed.

Why it exists. On 2026-11-04 an adversarial review found corpus content tracked on the public
`main` since 2026-10-22: a 150-triple sample of the knowledge graph with verbatim citations and
paths of 62 documents of the private document vault, and gold sets with verbatim corpus anchors.
The deposit scripts already scanned what went to Zenodo; nothing scanned what went to git.

  --staged          scan what `git commit` would record (pre-commit hook). Text files: only the
                    ADDED lines, so content committed before this gate existed does not block new
                    work. Binary files (pdf, zip): the whole staged blob.
  --files P [P..]   scan whole files (deposit packages, CI on a PR's changed files).

Exit 1 on any BLOCK finding; WARN findings print and exit 0.

What it blocks:
  * a concrete file under the private vault or the Mac event log (a directory mention is fine);
  * a concrete people-entity file (its slug is a person's name);
  * a host name of the `srv` + 6 digits form, and the private tailnet prefix;
  * any word or 2-4 word phrase whose sha256 is in the local private-term list
    (~/.config/memoria-nox/private-terms.sha256, never versioned; built by
    tools/build-private-terms.py from the private files themselves).
What it only warns about: absolute home paths (87 tracked files already carry them).

What it cannot see: a paraphrase, or a verbatim corpus passage made of words that are not in the
private-term list. It is a detector of known identifiers, not of private text in general.

Escape hatch, with a trail: PRIVACY_GATE_OK="<reason>" git commit ... prints the reason and the
findings and lets the commit through.
"""
import hashlib
import io
import os
import pathlib
import re
import subprocess
import sys
import zipfile

TERMS_FILE = pathlib.Path(os.environ.get(
    "PRIVACY_TERMS_FILE", pathlib.Path.home() / ".config/memoria-nox/private-terms.sha256"))
# Patterns are assembled from pieces so this file does not match itself.
_F = r"[A-Za-z0-9][A-Za-z0-9._ -]*\.[A-Za-z0-9]{1,5}"
BLOCK = [
    ("private vault file", "memory/" + "mac-docs/" + _F),
    ("mac event log file", "events/" + "mac/" + _F),
    ("people entity file", "memory/" + "entities/" + "people/" + r"[A-Za-z0-9][A-Za-z0-9_-]*"),
    ("host name", r"\b" + "srv" + r"\d{6,}\b"),
    ("tailnet address", r"\b100\." + r"92\.\d{1,3}\.\d{1,3}\b"),
]
WARN = [("home path", "/" + "Users/" + r"[a-z][a-z0-9_-]*/")]
BINARY_EXT = {".pdf", ".zip", ".gz", ".png", ".jpg", ".jpeg", ".db", ".sqlite", ".sqlite3"}


def load_terms():
    if not TERMS_FILE.exists():
        return set()
    return {l.split()[0] for l in TERMS_FILE.read_text().splitlines()
            if l.strip() and not l.startswith("#")}


def term_hash(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def phrases(text):
    words = re.findall(r"[\w@.-]+", text.lower())
    words = [w.strip(".-") for w in words if w.strip(".-")]
    for n in (1, 2, 3, 4):
        for i in range(len(words) - n + 1):
            yield " ".join(words[i:i + n])


def scan_text(name, text, terms):
    out = []
    for label, pat in BLOCK:
        for m in re.finditer(pat, text):
            out.append(("BLOCK", name, label, m.group(0)[:12] + "…"))
    for label, pat in WARN:
        if re.search(pat, text):
            out.append(("WARN", name, label, ""))
    if terms:
        seen = set()
        for p in phrases(text):
            h = term_hash(p)
            if h in terms and h not in seen:
                seen.add(h)
                out.append(("BLOCK", name, "private term", "hash " + h[:8]))
    return out


def blob_texts(name, data):
    """Text views of a binary blob: zip members one by one, anything else as latin-1."""
    if name.lower().endswith(".zip"):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                for n in z.namelist():
                    yield f"{name}:{n}", z.read(n).decode("utf-8", "replace")
            return
        except zipfile.BadZipFile:
            pass
    yield name, data.decode("latin-1")


def git(*a):
    return subprocess.run(["git", *a], capture_output=True, check=True).stdout


def staged(terms):
    names = git("diff", "--cached", "--name-only", "--diff-filter=AM", "-z").decode().split("\0")
    out = []
    for n in filter(None, names):
        if pathlib.PurePath(n).suffix.lower() in BINARY_EXT:
            for nm, t in blob_texts(n, git("show", f":{n}")):
                out += scan_text(nm, t, terms)
            continue
        diff = git("diff", "--cached", "-U0", "--no-color", "--", n).decode("utf-8", "replace")
        added = "\n".join(l[1:] for l in diff.splitlines()
                          if l.startswith("+") and not l.startswith("+++"))
        out += scan_text(n, added, terms)
    return out


def files(paths, terms):
    out = []
    for p in paths:
        data = pathlib.Path(p).read_bytes()
        if pathlib.PurePath(p).suffix.lower() in BINARY_EXT:
            for nm, t in blob_texts(p, data):
                out += scan_text(nm, t, terms)
        else:
            out += scan_text(p, data.decode("utf-8", "replace"), terms)
    return out


def main(argv):
    if not argv or argv[0] not in ("--staged", "--files"):
        sys.exit(__doc__)
    terms = load_terms()
    found = staged(terms) if argv[0] == "--staged" else files(argv[1:], terms)
    blocks = [f for f in found if f[0] == "BLOCK"]
    for kind, name, label, hint in found:
        print(f"privacy-gate {kind}: {name}: {label} {hint}".rstrip(), file=sys.stderr)
    if not terms:
        print("privacy-gate WARN: no private-term list at " + TERMS_FILE.name
              + "; only the path and host patterns ran", file=sys.stderr)
    if blocks:
        reason = os.environ.get("PRIVACY_GATE_OK", "").strip()
        if reason:
            print(f"privacy-gate: {len(blocks)} block(s) let through by PRIVACY_GATE_OK: {reason}",
                  file=sys.stderr)
            return 0
        print(f"privacy-gate: {len(blocks)} block(s). The repository is public. Remove the content, "
              "or set PRIVACY_GATE_OK=\"<reason>\" if it is not private.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
