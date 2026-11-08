#!/usr/bin/env python3
"""Sensitivity of the B2 reading to deviation 1 (PREREGISTRATION.md §10), computed after the reading
and not registered.

Sheet items 39, 40 and 55 were first graded "n" by the author without seeing their chunk (the
spreadsheet application had emptied those cells), then regraded "s" from plain text; the committed
grades are the second ones. This script reruns the registered reading twice through `b2.py read`'s
own checks (every commitment, the selection and the grades must match), once with the committed
grades and once with those three items set back to their first grade, and writes counts only.

  python3 -I b2-regrade-sensitivity.py read --private <P2> --b-private <PB> --b-refs ... --refs ...
"""
import datetime
import importlib.util
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("b2", HERE / "b2.py")
X = importlib.util.module_from_spec(spec)
spec.loader.exec_module(X)
ITEMS = (39, 40, 55)
FIRST_GRADE = 0          # all three were "n" before the regrade
_reading = X.reading


def summary(out):
    r = out["reported_not_interpreted"]
    return {"precision_after": out["B2_P"]["precision_after"],
            "difference": out["B2_P"]["difference"],
            "difference_bootstrap95": out["B2_P"]["difference_bootstrap95"],
            "retention_strict": out["B2_R"],
            "retention_lenient": r["supported_output_retention_lenient"],
            "correction_on_paper_b_unsupported": r["correction_rate_on_paper_b_unsupported"],
            "damage_on_paper_b_supported": r["damage_rate_on_paper_b_supported"],
            "transitions_from_paper_b_supported": r["transitions_from_paper_b_supported"],
            "transitions_from_paper_b_unsupported": r["transitions_from_paper_b_unsupported"]}


def both(fz, fin_b, ctl_b, rep, rw, res, graded, seed, cost=None):
    sel = X.select(rw, res, seed)
    ids = {sel[k - 1][0]: k for k in ITEMS}
    first = [(i, o, FIRST_GRADE if i in ids else g) for i, o, g in graded]
    items = sorted(({"item": ids[i], "sheet_origin": o, "committed_grade": g,
                     "first_grade": FIRST_GRADE, "paper_b_label": fin_b[i][0]}
                    for i, o, g in graded if i in ids), key=lambda d: d["item"])
    out = {"what": "B2 reading with the committed grades and with items 39, 40, 55 at their first grade",
           "registered": False, "deviation": "paper-b2-kg-repair/PREREGISTRATION.md §10, deviation 1",
           "items": items,
           "committed_grades": summary(_reading(fz, fin_b, ctl_b, rep, rw, res, graded, seed, cost)),
           "first_grades": summary(_reading(fz, fin_b, ctl_b, rep, rw, res, first, seed, cost))}
    X.B.write_public(HERE / f"REGRADE-SENSITIVITY-{datetime.date.today().isoformat()}.json", out)
    print(json.dumps({k: out[k]["precision_after"] for k in ("committed_grades", "first_grades")}))
    sys.exit(0)


X.reading = both
X.main(sys.argv[1:])
