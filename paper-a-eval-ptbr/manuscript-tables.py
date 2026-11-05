#!/usr/bin/env python3
"""Tables of MANUSCRIPT.md, generated from the versioned artifacts, never typed.

Keyless and read-only. Reads the printed outputs of the registered reading (`results/`) and the
two commitments, and prints each table as markdown.

    python3 -I paper-a-eval-ptbr/manuscript-tables.py           # print the tables
    python3 -I paper-a-eval-ptbr/manuscript-tables.py --check   # exit 1 unless MANUSCRIPT.md
                                                                # carries each table verbatim

The check is the number-parity gate for tables: a figure edited by hand in the manuscript, or a
table left behind after an artifact changes, fails it. Prose numbers are the provenance gate's
(tools/provenance.py); this covers the rows, their order and their labels.
"""
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
RES = HERE / "results"
H = (RES / "h-a1-2026-11-05.txt").read_text(encoding="utf-8")
HUMAN = json.loads((HERE / "HUMAN-COMMITMENT.json").read_text(encoding="utf-8"))
HOLD = json.loads((HERE / "HOLDOUT-COMMITMENT.json").read_text(encoding="utf-8"))


def md(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def terciles():
    rows = []
    for name in ("low", "mid", "high"):
        m = re.search(rf"^\s+{name}\s+n=\s*(\d+) strict ([\d.]+) pooled ([\d.]+)$", H, re.M)
        rows.append((name, m.group(1), m.group(2), m.group(3)))
    return md(("overlap tercile", "n", "strict", "pooled"), rows)


def strata():
    rows = [(m.group(1), m.group(2), m.group(3), m.group(4)) for m in
            re.finditer(r"^\s+([A-F]) n=\s*(\d+) strict ([\d.]+) pooled ([\d.]+)$", H, re.M)]
    assert [r[0] for r in rows] == list("ABCDEF"), "expected strata A..F"
    assert {k: int(r[1]) for k, r in zip("ABCDEF", rows)} == HOLD["per_stratum"], "strata n differ from the commitment"
    return md(("stratum", "n", "strict", "pooled"), rows)


def human():
    t = HUMAN["table"]
    assert sum(t.values()) == HUMAN["n"] == 60
    return md(("", "judge yes", "judge no"),
              (("grader yes", t["yes_yes"], t["yes_no"]), ("grader no", t["no_yes"], t["no_no"])))


TABLES = {"overlap terciles (H-A1, descriptive)": terciles(),
          "strata (H-A1, descriptive)": strata(),
          "human sample against the judge": human()}


def main():
    if "--check" not in sys.argv:
        for k, v in TABLES.items():
            print(f"{k}\n\n{v}\n")
        return 0
    text = (HERE / "MANUSCRIPT.md").read_text(encoding="utf-8")
    bad = [k for k, v in TABLES.items() if v not in text]
    for k in bad:
        print(f"manuscript-tables FAIL: table '{k}' is not in MANUSCRIPT.md as generated", file=sys.stderr)
    print(f"manuscript-tables: {len(TABLES)} tables, {len(bad)} failures")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
