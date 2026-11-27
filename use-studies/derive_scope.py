#!/usr/bin/env python3
"""Derive a scope sentence for the nox-mem MCP `instructions` from the memory database alone.

Study S (PREREGISTRATION.md): does a scope sentence built from the user's own store work as well as
one written by hand? This is the derivation, fixed before any run. It reads only `chunks`
(source_file, chunk_text): no LLM, no network, deterministic. Ties are broken alphabetically.

  python3 -I derive_scope.py <db>            # prints the sentence
  python3 -I derive_scope.py <db> --json     # sentence plus the counts behind it

Rule:
  1. names: words written with a capital inside a sentence (after a lower-case letter, digit or
     punctuation and a space), 3+ characters, minus calendar, time-zone and SQL keywords;
     ranked by the number of chunks they occur in; top 12.
  2. identifiers: code spans in backticks that look like code (contain `_`, `-`, `.`, a digit, or
     an inner capital) and are not paths (`/`) or file names (`.md`, `.json`, `.py`, `.sh`);
     ranked the same way; top 8.
  3. documents: the 3 source files that hold the most chunks, by file stem.
  4. sentence: "the notes in this store (<n> passages, most from <d1>, <d2> and <d3>), about
     <names>; recurring identifiers: <identifiers>". The server cuts it at 800 characters.
"""
import collections
import json
import pathlib
import re
import sqlite3
import sys

EXCLUDE = {
    # calendar and time
    "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "BRT", "UTC", "GMT", "EST", "PST",
    # SQL and boolean keywords written in capitals
    "AND", "NOT", "NULL", "SELECT", "INSERT", "UPDATE", "DELETE", "FROM", "WHERE", "JOIN", "TRUE",
    "FALSE", "THE",
}
NAME = re.compile(r"(?<=[a-z0-9,;:)] )([A-Z][A-Za-z0-9]+(?:-[A-Za-z0-9]+)?)")
CODE = re.compile(r"`([A-Za-z][A-Za-z0-9_.\-/]{2,40})`")
FILEEXT = re.compile(r"\.(md|json|py|sh|ts|js|txt|jsonl|db)$", re.I)


def codelike(s):
    return bool(re.search(r"[_\-.0-9]", s) or re.search(r"[a-z][A-Z]", s))


def derive(db):
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    rows = c.execute("SELECT source_file, chunk_text FROM chunks").fetchall()
    c.close()
    names, idents, docs = collections.Counter(), collections.Counter(), collections.Counter()
    for src, text in rows:
        text = text or ""
        docs[pathlib.Path(src).stem] += 1
        names.update({m for m in NAME.findall(text) if len(m) >= 3 and m not in EXCLUDE})
        idents.update({m for m in CODE.findall(text)
                       if codelike(m) and "/" not in m and not FILEEXT.search(m)})

    def top(counter, k):
        return [w for w, _ in sorted(counter.items(), key=lambda x: (-x[1], x[0]))[:k]]

    n, i, d = top(names, 12), top(idents, 8), top(docs, 3)
    sentence = (f"the notes in this store ({len(rows)} passages, most from {d[0]}, {d[1]} and {d[2]}), "
                f"about {', '.join(n)}; recurring identifiers: {', '.join(i)}")
    counts = {"passages": len(rows),
              "names": {w: names[w] for w in n}, "identifiers": {w: idents[w] for w in i},
              "documents": {w: docs[w] for w in d}}
    return sentence, counts


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    s, counts = derive(sys.argv[1])
    print(json.dumps({"scope": s, "chars": len(s), **counts}, ensure_ascii=False, indent=1)
          if "--json" in sys.argv else s)
