#!/usr/bin/env python3
"""Provenance gate: every number a paper prints must come from a named, current source.

Why it exists. On 2026-11-04 the plan for four papers quoted four figures that the repository's own
audits had already corrected (a fidelity of 0.833 revised to 0.900; an nDCG range replaced by a
fully judged one; two counts re-based on a wider transcript root). Each came from a note written
on the day of the first measurement. A parity check would have passed: the stale numbers matched
their stale JSON exactly. What was missing was the link from a number to the current source.

  python3 tools/provenance.py --check <dir>

<dir>/PROVENANCE.json:
  {"text": ["PAPER.md"],                    # files whose numbers are checked
   "ignore": ["2026", "1.0"],               # tokens that are not measurements (years, versions)
   "claims": [
     {"id": "kg-fidelity", "value": "0.900", # exactly as printed in the text
      "population": "150 relations, uniform over live evidence, seed 20261022",
      "date": "2026-10-23",
      "artifact": "audits/2026-10-23-kg-s1-quatro-principios.md",
      "locator": "0.900",                    # a string that must occur in the artifact
      "commit": "abf46ee",                   # the commit that holds the artifact
      "superseded_by": null}]}               # id of the claim that replaces this one, or null

Fails (exit 1) when:
  * a decimal number or percentage in a text file is neither a claim's value nor ignored;
  * a claim's value is printed in the text while its `superseded_by` is set;
  * a claim's artifact does not exist in the repository, or its locator is not in it;
  * a claim's commit does not exist, or the artifact is not in that commit;
  * `superseded_by` names a claim id that does not exist;
  * a `history` fragment (below) is not in the text, or does not contain its claim's value.

A superseded value may be printed only as history, and only where declared: a claim's optional
"history": ["<exact fragment of the text>", ...] lists the passages that cite it as a value that
was later corrected. Those fragments are removed before the text's numbers are checked, so the
same value printed anywhere else still fails. A value may hold several numbers ("[0.427 · 0.439]");
each number in it counts.
An artifact that is private (kept outside the repository) is declared with "artifact_private":
true and a "sha256" of the file; the gate then checks only that the claim is not superseded, and
says the artifact was not verified.
"""
import json
import pathlib
import re
import subprocess
import sys

NUM = re.compile(r"(?<![\w.])[−+-]?\d+(?:[.,]\d+)+%?|(?<![\w.])\d+%")


def numbers(text):
    # strip inline code and fenced code: identifiers and commands are not measurements
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`[^`]*`", " ", text)
    return {m.group(0).lstrip("−+-") for m in NUM.finditer(text)}


def git_ok(*a):
    return subprocess.run(["git", *a], capture_output=True).returncode == 0


def check(d):
    d = pathlib.Path(d)
    root = pathlib.Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True,
                                       text=True, cwd=d).stdout.strip())
    man = json.loads((d / "PROVENANCE.json").read_text(encoding="utf-8"))
    claims = {c["id"]: c for c in man["claims"]}
    ignore = set(man.get("ignore", []))
    errs, notes = [], []
    original = {t: (d / t).read_text(encoding="utf-8") for t in man["text"]}
    texts = dict(original)
    # every fragment is checked against the ORIGINAL text, then all are removed: two claims may
    # declare the same passage, and removing it for the first must not fail the second
    for cid, c in claims.items():
        for frag in c.get("history", []):
            if not any(frag in body for body in original.values()):
                errs.append(f"{cid}: history fragment not in the text: {frag[:50]!r}")
            elif not numbers(c["value"]) <= numbers(frag):
                errs.append(f"{cid}: history fragment does not contain the value {c['value']!r}")
    for c in claims.values():
        for frag in c.get("history", []):
            for t in texts:
                texts[t] = texts[t].replace(frag, " ")
    printed = set()
    for body in texts.values():
        printed |= numbers(body)
    current = set().union(*[numbers(c["value"]) or {c["value"]} for c in claims.values()
                            if not c.get("superseded_by")])
    stale = {n: c["id"] for c in claims.values() if c.get("superseded_by")
             for n in (numbers(c["value"]) or {c["value"]})}
    for n in sorted(printed):
        if n in stale and n not in current:
            errs.append(f"{n}: printed, but claim '{stale[n]}' is superseded by "
                        f"'{claims[stale[n]]['superseded_by']}'")
        elif n not in current and n not in ignore and n not in stale:
            errs.append(f"{n}: printed with no claim in PROVENANCE.json")
    for cid, c in claims.items():
        sb = c.get("superseded_by")
        if sb and sb not in claims:
            errs.append(f"{cid}: superseded_by '{sb}' is not a claim id")
        if c.get("artifact_private"):
            notes.append(f"{cid}: private artifact, not verified here (sha256 {c.get('sha256', '?')[:12]})")
            continue
        art = root / c["artifact"]
        if not art.exists():
            errs.append(f"{cid}: artifact {c['artifact']} does not exist")
            continue
        if c["locator"] not in art.read_text(encoding="utf-8", errors="replace"):
            errs.append(f"{cid}: locator {c['locator']!r} not found in {c['artifact']}")
        if not git_ok("-C", str(root), "cat-file", "-e", f"{c['commit']}^{{commit}}"):
            errs.append(f"{cid}: commit {c['commit']} does not exist")
        elif not git_ok("-C", str(root), "cat-file", "-e", f"{c['commit']}:{c['artifact']}"):
            errs.append(f"{cid}: {c['artifact']} is not in commit {c['commit']}")
    for n in notes:
        print("provenance NOTE:", n, file=sys.stderr)
    for e in errs:
        print("provenance FAIL:", e, file=sys.stderr)
    print(f"provenance: {len(claims)} claims, {len(printed)} numbers printed, {len(errs)} failures")
    return 1 if errs else 0


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "--check":
        sys.exit(__doc__)
    sys.exit(check(sys.argv[2]))
