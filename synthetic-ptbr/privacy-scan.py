#!/usr/bin/env python3
"""Gate «S: privacidade do pacote» (PLANO.md): no run of 8 words of the publication package is
also a run of 8 words of the private corpus.

  python3 -I privacy-scan.py --package <dir> --db <private sqlite> [--min-hits 1]

Run WHERE the private corpus lives (the production host), with the package copied there: the
package is public, the corpus is not, so only public text moves. The private database is opened
read-only (mode=ro) and nothing of it is printed: a match is reported by the PACKAGE side only
(file and the 8 normalised words, which are the package's own words) plus the count of private
chunks that carry it.

Normalisation: lower case, accents stripped, every non-alphanumeric run is a word boundary. The
package scanned is every text file under --package (corpus, plan, prompts, records).

Exit 0 when there is no shared run; 1 when there is (each one has to be read: a stock phrase can
match by chance, and that is for a person to judge, never for this script to excuse); 2 on error.
"""
import argparse
import pathlib
import re
import sqlite3
import sys
import unicodedata

N = 8
TEXT_SUFFIXES = {".md", ".json", ".jsonl", ".txt"}


def words(text):
    t = unicodedata.normalize("NFKD", text.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.findall(r"[a-z0-9]+", t)


def shingles(text, n=N):
    w = words(text)
    return {" ".join(w[i:i + n]) for i in range(len(w) - n + 1)}


def package_shingles(root):
    where = {}
    for p in sorted(pathlib.Path(root).rglob("*")):
        if p.is_file() and p.suffix in TEXT_SUFFIXES:
            for s in shingles(p.read_text(encoding="utf-8", errors="replace")):
                where.setdefault(s, str(p.relative_to(root)))
    return where


def scan(package, db):
    pkg = package_shingles(package)
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    hits = {}
    n_chunks = 0
    for (text,) in con.execute("SELECT chunk_text FROM chunks"):
        n_chunks += 1
        for s in shingles(text or "") & pkg.keys():
            hits[s] = hits.get(s, 0) + 1
    con.close()
    return pkg, n_chunks, hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", required=True)
    ap.add_argument("--db", required=True)
    a = ap.parse_args()
    if not pathlib.Path(a.db).is_file():          # sqlite would create an empty db and say "0 hits"
        print(f"privacy-scan: ERROR no database file at the given path")
        return 2
    try:
        pkg, n_chunks, hits = scan(a.package, a.db)
    except sqlite3.Error as e:
        print(f"privacy-scan: ERROR {type(e).__name__}")
        return 2
    if n_chunks == 0:                              # a scan that read nothing must not read as clean
        print("privacy-scan: ERROR the private database has no chunks; nothing was compared")
        return 2
    print(f"privacy-scan: {len(pkg)} package runs of {N} words x {n_chunks} private chunks")
    for s, n in sorted(hits.items(), key=lambda x: -x[1])[:40]:
        print(f"  ! «{s}» in {pkg[s]} (also in {n} private chunk(s))")
    print(f"privacy-scan: {'FAIL, ' + str(len(hits)) + ' shared run(s)' if hits else 'ok, 0 shared runs'}")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
