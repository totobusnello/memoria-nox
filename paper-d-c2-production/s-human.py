#!/usr/bin/env python3
"""C2 shadow study, step 6 (SHADOW-PREREGISTRATION.md §5.3 and §6): Paper D's blind human sample.

  python3 -I s-human.py make   --private <dir> --repo <clone> --refs <freeze>,<questions>,<results>
  python3 -I s-human.py agree  --private <dir> --repo <clone> --refs <freeze>,<questions>,<results>
  python3 -I s-human.py commit --private <dir> --repo <clone> --refs <freeze>,<questions>,<results>
  (smoke: --smoke instead of --refs; --n other than 60 needs --smoke)

Paper D's §5.4, unchanged, run by Paper D's own d-human.py: `make` draws 60 rows uniformly from
the (primary question, arm) pairs with arm C0 or C2 in <dir>/run/results.json and writes them in
random order with the question, the reference and the candidate answer only (no arm, no judge
output); `agree` and `commit` recompute the draw, refuse a sheet that is not exactly those rows
with the texts `make` wrote, and refuse an ungraded row. The draw's seed is this study's (§3).

Every mode refuses unless the freeze, questions and results commitments are on the public main
branch in order after the tag, each byte-equal to its private copy, and results.json and
questions.jsonl are the committed ones. `commit` writes <dir>/SHADOW-HUMAN-COMMITMENT.json;
push it before s-read.py.
"""
import argparse
import importlib.util
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("scommon", HERE / "s-common.py")
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)
H = C.load("dhuman_shadow", HERE / "d-human.py")      # Paper D's sheet: make, read_sheet, agree


def checks(a):
    P = C.private(a.private)
    refs = (a.refs or "").split(",") if a.refs else [None, None, None]
    if not a.smoke and len(refs) != 3:
        sys.exit("--refs needs the freeze, questions and results commits")
    got = C.chain(a.repo, P, list(zip(C.COMMITS[:3], refs)), a.smoke)
    fc, qc, rc = (got[n][1] for n in C.COMMITS[:3])
    if not a.smoke:
        C.same_as_tag(a.repo)
    if rc["questions_commitment_sha256"] != C.sha_bytes(got["SHADOW-QUESTIONS"][0]) or \
            rc["freeze_commitment_sha256"] != C.sha_bytes(got["SHADOW-FREEZE"][0]):
        sys.exit("refusing: the results commitment names other freeze or questions commitments")
    if C.sha_file(P / "run" / "results.json") != rc["results_sha256"]:
        sys.exit("refusing: results.json is not the committed one")
    if C.sha_file(P / "questions.jsonl") != qc["questions_sha256"]:
        sys.exit("refusing: questions.jsonl is not the committed one")
    H.C.SEED = fc["seed"]                 # Paper D's draw, under this study's seed
    return P, got


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("make", "agree", "commit"))
    ap.add_argument("--private", required=True)
    ap.add_argument("--repo", default=str(C.ROOT))
    ap.add_argument("--refs")
    ap.add_argument("--n", type=int, default=C.N_HUMAN)
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args(argv)
    if a.n != C.N_HUMAN and not a.smoke:
        sys.exit(f"refusing: the registered sample is {C.N_HUMAN} rows; --n {a.n} needs --smoke")
    if not a.smoke and not a.refs:
        sys.exit("--refs is required (or --smoke)")
    P, got = checks(a)
    if a.mode == "make":
        H.make(a)
        C.lock_down(P)
        return 0
    if a.mode == "agree":
        H.agree(a)
        return 0
    _, res = H.agree(a)
    out = {"smoke": bool(a.smoke), **res, "seed": H.C.SEED,
           "sheet_sha256": C.sha_file(P / "human-sample.csv"),
           "results_sha256": C.sha_file(P / "run" / "results.json"),
           "questions_sha256": C.sha_file(P / "questions.jsonl"),
           "results_commitment_sha256": C.sha_bytes(got["SHADOW-RESULTS"][0]),
           "script_sha256": {f: C.sha_file(HERE / f) for f in ("s-human.py", "s-common.py", "d-human.py")}}
    C.write_private(P / "SHADOW-HUMAN-COMMITMENT.json", json.dumps(out, indent=1) + "\n")
    C.lock_down(P)
    print(f"wrote {P / 'SHADOW-HUMAN-COMMITMENT.json'}; copy it into {C.D}/, commit, push, then s-read.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
