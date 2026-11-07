#!/usr/bin/env python3
"""Paper B, after the reading (not registered): on the sheet rows where the two judges disagreed,
which judge accepted and what the human graded. Counts only.

  python3 -I b-disagreement-direction.py --private <dir> --freeze-ref <c> --judges-ref <c> --sheet-ref <c> --human-ref <c>

Uses b-read.py's own checks of the four commitments and the private files, then writes
DISAGREEMENT-DIRECTION-<date>.json next to this script.
"""
import argparse
import collections
import datetime
import importlib.util
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("bcommon", HERE / "b-common.py")
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)
H = C.load("bhuman", HERE / "b-human.py")


def main():
    ap = argparse.ArgumentParser()
    for k in ("private", "freeze-ref", "judges-ref", "sheet-ref", "human-ref"):
        ap.add_argument(f"--{k}", required=True)
    a = ap.parse_args()
    P = C.private(a.private)
    com = C.ordered(C.ROOT, [("FREEZE", a.freeze_ref), ("JUDGES", a.judges_ref),
                             ("SHEET", a.sheet_ref), ("HUMAN", a.human_ref)])
    C.same_private(com["FREEZE"], "freeze_json_sha256", P / "freeze.json")
    C.same_private(com["JUDGES"], "judges_json_sha256", P / "judges.json")
    C.same_private(com["HUMAN"], "graded_sheet_sha256", P / "human-sheet.csv")
    fz = json.loads((P / "freeze.json").read_text(encoding="utf-8"))
    res = json.loads((P / "judges.json").read_text(encoding="utf-8"))
    sel = H.select(fz, res, fz["seed"])
    if C.sha_json(sel) != com["SHEET"]["selection_sha256"]:
        sys.exit("refusing: the recomputed selection is not the committed one")
    graded = H.read_sheet(P / "human-sheet.csv", fz, sel)
    j1 = res["judge1"]["primary"]
    c = collections.defaultdict(lambda: {"human_supported": 0, "human_unsupported": 0})
    for i, origin, g in graded:
        if origin != "disagree":
            continue
        k = "only_judge1_accepted" if j1[str(i)]["verified"] else "only_judge2_accepted"
        c[k]["human_supported" if g else "human_unsupported"] += 1
    out = {"what": "Paper B disagreement rows by which judge accepted, against the human grade; "
                   "computed after the reading, not registered",
           "rows": dict(sorted(c.items())),
           "commits": {n: com[n]["_commit"] for n in C.COMMITS}}
    C.write_public(HERE / f"DISAGREEMENT-DIRECTION-{datetime.date.today().isoformat()}.json", out)
    print(json.dumps(out["rows"]))


if __name__ == "__main__":
    main()
