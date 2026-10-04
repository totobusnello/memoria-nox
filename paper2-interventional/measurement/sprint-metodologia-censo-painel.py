#!/usr/bin/env python3
"""Read-only census of the 7_problems process artifacts that the methodology paper would cite.

Why this exists (2026-10-03): the methodology outline (PNP_AI/notes/methodology_paper_outline.md)
claims an adversarial multi-family panel, a claim ledger, a gate battery and a call log, and warns
that its own numbers are a 2026-08-09 snapshot. This script re-derives the counts from the
artifacts themselves, without git, without writing anything inside the other repo.

What it counts (each number is printed next to the path it came from):
  * adversary receipts in .remember/: voice x exit code, date range, and how many of the exit-0
    receipts carry a non-empty output (output_bytes > 0). An exit-0 receipt with 0 bytes is
    NOT a delivered verdict.
  * rows of 07_MODEL_CALL_LOG.md (numbered table rows) and the last date in it.
  * rows of PNP_AI/notes/capture_manifest.csv, files in notes/reviews, notes/adjudications.
  * `### E<n>` and `## Padrao` headings of 14_PROCESS_POSTMORTEM.md.
  * numbers.sh gate scripts referenced vs tools/nums_*.py files present.

What it deliberately does NOT do: classify an adversarial output as "true catch" or "false
positive". That needs a human reading the output against the artifact; a keyword count would be
a guess presented as a measurement. The census therefore gives denominators, not catch rates.

Usage: python3 sprint-metodologia-censo-painel.py [REPO_ROOT]   (default: ~/Claude/Projetos/7_problems)
"""
import collections
import csv
import glob
import json
import os
import re
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Claude/Projetos/7_problems")


def p(*a):
    return os.path.join(ROOT, *a)


def parse_receipt(path):
    d = {}
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if ":" not in line:
                continue
            k, v = line.split(":", 1)
            k = k.strip()
            if k in ("voice", "timestamp", "exit", "output_bytes", "duration_s", "model"):
                d.setdefault(k, v.strip())
    return d


out = {"root": ROOT}

# --- receipts --------------------------------------------------------------------------------
files = sorted(glob.glob(p(".remember", "adversary-receipt-*.txt")))
by = collections.Counter()
delivered = collections.Counter()
dates = []
unparsed = 0
for fp in files:
    r = parse_receipt(fp)
    if "voice" not in r or "exit" not in r:
        unparsed += 1
        continue
    by[(r["voice"], r["exit"])] += 1
    ob = int(r.get("output_bytes", "0") or 0)
    if r["exit"] == "0" and ob > 0:
        delivered[r["voice"]] += 1
    m = re.match(r"(\d{4}-\d{2}-\d{2})", r.get("timestamp", ""))
    if m:
        dates.append(m.group(1))
out["receipts"] = {
    "source": ".remember/adversary-receipt-*.txt",
    "files": len(files),
    "unparsed": unparsed,
    "first_date": min(dates) if dates else None,
    "last_date": max(dates) if dates else None,
    "voice_by_exit": {f"{v}|exit={e}": n for (v, e), n in sorted(by.items())},
    "exit0_with_output": dict(delivered),
}

# --- call log --------------------------------------------------------------------------------
cl = p("07_MODEL_CALL_LOG.md")
rows, last = 0, None
with open(cl, encoding="utf-8", errors="replace") as f:
    for line in f:
        m = re.match(r"\|\s*(\d+)\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|", line)
        if m:
            rows += 1
            last = m.group(2)
out["call_log"] = {"source": "07_MODEL_CALL_LOG.md", "numbered_rows": rows, "last_row_date": last}

# --- captures / reviews / adjudications --------------------------------------------------------
with open(p("PNP_AI/notes/capture_manifest.csv"), encoding="utf-8") as f:
    n_cap = sum(1 for _ in csv.DictReader(f))
out["captures"] = {
    "capture_manifest_rows": n_cap,
    "notes_reviews_files": len(os.listdir(p("PNP_AI/notes/reviews"))),
    "notes_adjudications_files": len(os.listdir(p("PNP_AI/notes/adjudications"))),
}

# --- postmortem --------------------------------------------------------------------------------
pm = open(p("14_PROCESS_POSTMORTEM.md"), encoding="utf-8", errors="replace").read()
out["postmortem"] = {
    "source": "14_PROCESS_POSTMORTEM.md",
    "lines": pm.count("\n") + 1,
    "h3_E_entries": len(re.findall(r"^### E\d+", pm, re.M)),
    "h2_Padrao_sections": len(re.findall(r"^## Padr", pm, re.M)),
}

# --- gate battery ------------------------------------------------------------------------------
nums = glob.glob(p("tools", "nums_*.py"))
sh = open(p("tools", "numbers.sh"), encoding="utf-8", errors="replace").read()
ref = set(re.findall(r"tools/(nums_[a-z0-9_]+\.py)", sh))
out["gates"] = {
    "nums_py_files": len(nums),
    "nums_py_referenced_in_numbers_sh": len(ref),
    "present_but_unreferenced": sorted(os.path.basename(x) for x in nums if os.path.basename(x) not in ref),
    "referenced_but_missing": sorted(r for r in ref if not os.path.exists(p("tools", r))),
}

# --- level-2 ladder: any VeriPB proof artifact in the repo? (scoped search, stated) -----------
hits = []
for base in ("PNP_AI", "tools", "verify_repo_stage"):
    for dp, dn, fn in os.walk(p(base)):
        dn[:] = [d for d in dn if d not in (".git", "mathlib", "__pycache__", ".lake")]
        for x in fn:
            if x.endswith((".pbp", ".opb")):
                hits.append(os.path.relpath(os.path.join(dp, x), ROOT))
out["veripb_artifacts"] = {
    "searched": "files named *.pbp or *.opb under PNP_AI/, tools/, verify_repo_stage/ (excl. .git, mathlib, .lake)",
    "found": hits,
}

print(json.dumps(out, indent=2, ensure_ascii=False))
