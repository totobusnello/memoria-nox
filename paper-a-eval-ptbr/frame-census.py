#!/usr/bin/env python3
"""Census of the holdout frame (PREREGISTRATION.md §3): counts only, no text, no file names.

  python3 -I frame-census.py --db <snapshot.db> > frame-census.txt

Prints, for chunks with superseded_by IS NULL and at least MIN_CHARS characters, the number of
source files and chunks in each stratum of holdout-draw.py, and the two directories left outside
the frame. Uses strata.py, the stratum function the draw uses, so the census and the draw cannot disagree.
"""
import argparse
import importlib.util
import pathlib
import sqlite3

HERE = pathlib.Path(__file__).resolve().parent
import json
import sys
sys.path.insert(0, str(HERE))
from strata import MIN_CHARS, stratum  # noqa: E402
QUOTA = json.loads((HERE / "quotas.json").read_text())["quota"]

ap = argparse.ArgumentParser()
ap.add_argument("--db", required=True)
a = ap.parse_args()
con = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
rows = con.execute("SELECT source_file, COUNT(*) FROM chunks WHERE superseded_by IS NULL "
                   "AND length(chunk_text) >= ? GROUP BY source_file", (MIN_CHARS,)).fetchall()
files, chunks = {}, {}
for f, n in rows:
    s = stratum(f)
    if s is None:
        s = ("out: private document vault" if f.startswith("memory/" + "mac-docs/") else
             "out: nox-mem source tree" if f.startswith("tools/nox-mem/") else "out: other")
    files[s] = files.get(s, 0) + 1
    chunks[s] = chunks.get(s, 0) + n
print(f"frame census · min_chars {MIN_CHARS} · superseded excluded")
for s in sorted(files):
    q = QUOTA.get(s)
    print(f"  {s:32s} files {files[s]:5d}  chunks {chunks[s]:6d}" + (f"  quota {q}" if q else ""))
