#!/usr/bin/env python3
"""Paper A, H-A2: the reading fixed by AMENDMENT-H-A2.md (later snapshot of 2027-05-18).

  python3 -I h-a2-amendment-run.py --frozen-db <2026-11-04 snapshot.db> \
      --later-gz <daily-main-main-20270518…db.gz, the first snapshot of 2027-05-18> \
      --listing <listing of the daily-main directory taken in the session of the copy> \
      --workdir <private directory outside the repository> \
      --holdout <holdout.jsonl> --commitment <commit that pushed HOLDOUT-COMMITMENT.json>

1. The registered reading. holdout-persistence.py is loaded unchanged from this directory and run
   with its date constant set to 2027-05-18. Nothing else differs from the run of 2026-11-18: the
   frozen database and its hash, the commitment checks, the listing rule, the criterion, the
   precondition and the prediction are that script's.
2. Descriptive, no threshold (AMENDMENT-H-A2.md §3), printed after the reading and computed on the
   same decompressed snapshot:
   - persists by a path-free anchor: any active chunk of the whole snapshot whose text contains
     the evidence span (more than one is reported as ambiguous);
   - for every query where the id and the registered anchor disagree, or that is exposed, the
     cause, from paths and counts only: the gold id's chunk moved to another path; the path has no
     active chunk left; or the path is still there and the gold chunk's text changed or is gone.
   Counts only. No chunk text, question or evidence span is printed.

Refuses unless the tag paper-a-h-a2-amendment-v1.0 exists on origin and this file and
holdout-persistence.py are byte-identical to the tag's.

Keyless, read-only.
"""
import importlib.util
import json
import pathlib
import subprocess
import sys

DATE = "20270518"
TAG = "paper-a-h-a2-amendment-v1.0"
here = pathlib.Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def check_tag(smoke):
    repo = str(here.parent)
    subprocess.run(["git", "-C", repo, "fetch", "-q", "--tags", "origin"], check=True)
    for f in ("h-a2-amendment-run.py", "holdout-persistence.py"):
        tagged = subprocess.run(["git", "-C", repo, "show", f"refs/tags/{TAG}:paper-a-eval-ptbr/{f}"],
                                capture_output=True)
        if tagged.returncode != 0:
            if smoke:
                print(f"smoke: tag {TAG} not found; continuing")
                return
            sys.exit(f"refusing: tag {TAG} not found on origin")
        if tagged.stdout != (here / f).read_bytes():
            sys.exit(f"refusing: {f} differs from the tag {TAG}")


def descriptive(workdir, frozen_db, holdout_path):
    hp = load("persistence", here / "holdout-persistence.py")
    fz, lt = hp.ro(frozen_db), hp.ro(str(pathlib.Path(workdir) / "later.db"))
    hold = [json.loads(l) for l in open(holdout_path, encoding="utf-8")]
    active = [hp.ws(t) for (t,) in lt.execute("SELECT chunk_text FROM chunks WHERE superseded_by IS NULL")]
    free = free_amb = 0
    causes = {"id moved to another path": 0, "path has no active chunk": 0,
              "path present, gold chunk changed or gone": 0}
    for h in hold:
        g = h["gold"][0]
        ev, sf = hp.ws(g["anchor"]), g["source_file"]
        n_free = sum(ev in t for t in active)
        free += n_free > 0
        free_amb += n_free > 1
        r = lt.execute("SELECT chunk_text, source_file FROM chunks WHERE id = ? AND superseded_by IS NULL",
                       (g["chunk_id"],)).fetchone()
        by_id = r is not None and ev in hp.ws(r[0])
        frozen = fz.execute("SELECT chunk_text FROM chunks WHERE id = ?", (g["chunk_id"],)).fetchone()[0]
        exposed = r is None or r[0] != frozen
        by_anchor = any(ev in hp.ws(t) for (t,) in lt.execute(
            "SELECT chunk_text FROM chunks WHERE source_file = ? AND superseded_by IS NULL", (sf,)))
        if not (exposed or by_id != by_anchor):
            continue
        at_path = lt.execute("SELECT COUNT(*) FROM chunks WHERE source_file = ? AND superseded_by IS NULL",
                             (sf,)).fetchone()[0]
        if r is not None and r[1] != sf:
            causes["id moved to another path"] += 1
        elif at_path == 0:
            causes["path has no active chunk"] += 1
        else:
            causes["path present, gold chunk changed or gone"] += 1
    n = len(hold)
    print(f"descriptive: persists by path-free anchor {free}/{n} (ambiguous {free_amb})")
    for k, v in causes.items():
        print(f"descriptive: exposed or id/anchor disagreement, cause '{k}': {v}")


def main():
    smoke = "--smoke" in sys.argv
    check_tag(smoke)
    hp = load("persistence", here / "holdout-persistence.py")
    hp.FIRST_DATE = DATE
    print(f"AMENDMENT-H-A2: registered reading on the snapshot of {DATE}")
    rc = hp.main()
    if rc:
        return rc
    arg = lambda k: sys.argv[sys.argv.index(k) + 1]
    descriptive(arg("--workdir"), arg("--frozen-db"), arg("--holdout"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
