#!/usr/bin/env python3
"""Build PROVENANCE.json for the IP&M manuscript: every number must be a number of the published report.

The IP&M article is a condensation of the technical report (paper/paper-tecnico-nox-mem.md, the text
deposited as v1.0.6). It reports no new measurement. So the claim this gate can make, and the only
one, is: every decimal number or percentage printed in manuscript.md occurs verbatim in the report as
it stands on the base branch. For each number the locator is the report line fragment around its first
occurrence, so `tools/provenance.py --check` re-verifies it against the artifact at that commit.

What this does NOT prove: that a number is used in the same sense as in the report (a value can occur
there in another context). That is checked by reading, and by a reviewer; this gate stops a number that
was mistyped, rounded differently or invented during the condensation.

  python3 paper/publication/ipm/build_provenance.py          # write PROVENANCE.json
  python3 paper/publication/ipm/build_provenance.py --check  # exit 1 if it would change, or a number is unsourced
"""
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from provenance import numbers  # noqa: E402  same tokenizer as the gate

SOURCE = "paper/paper-tecnico-nox-mem.md"
BASE = "origin/main"
TEXT = "manuscript.md"


def git(*a):
    return subprocess.run(["git", "-C", str(ROOT), *a], check=True, capture_output=True, text=True).stdout


def main():
    commit = git("log", "-1", "--format=%H", BASE, "--", SOURCE).strip()
    if not commit:
        sys.exit(f"no commit on {BASE} touches {SOURCE}")
    src = git("show", f"{commit}:{SOURCE}")
    src_nums_text = src.replace("−", "-")
    text = (HERE / TEXT).read_text()
    # arXiv identifiers in citations are identifiers, not measurements: ignored, each one named
    ignore = sorted(set(re.findall(r"arXiv:(\d{4}\.\d{4,5})", text)))
    claims, missing = [], []
    for n in sorted(numbers(text) - set(ignore)):
        i = src.find(n)
        if i < 0:
            # the report writes minus as U+2212 in places; the tokenizer strips the sign either way
            i = src_nums_text.find(n)
        if i < 0:
            missing.append(n)
            continue
        a, b = max(0, i - 24), min(len(src), i + len(n) + 24)
        frag = src[a:b]
        # a locator must be a plain substring of the artifact: cut at line breaks around the number
        lo = frag.rfind("\n", 0, i - a) + 1
        hi = frag.find("\n", i - a)
        frag = frag[lo:hi if hi >= 0 else len(frag)]
        claims.append({
            "id": "n-" + n.replace("%", "pct").replace(",", "_"),
            "value": n,
            "population": "carried verbatim from the technical report v1.0.6 (condensation; no new measurement)",
            "date": "2026-11-27",
            "artifact": SOURCE,
            "locator": frag,
            "commit": commit[:12],
            "superseded_by": None,
        })
    if missing:
        print("numbers in the manuscript that the report does not contain:", ", ".join(missing))
    out = {"text": [TEXT], "ignore": ignore, "claims": claims}
    path = HERE / "PROVENANCE.json"
    new = json.dumps(out, indent=1, ensure_ascii=False) + "\n"
    if "--check" in sys.argv:
        old = path.read_text() if path.exists() else ""
        if old != new or missing:
            sys.exit("PROVENANCE.json is stale or a number is unsourced; run build_provenance.py")
        print(f"ok: {len(claims)} numbers, all in {SOURCE}@{commit[:12]}")
        return
    path.write_text(new)
    print(f"wrote {len(claims)} claims; {len(missing)} unsourced")
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
