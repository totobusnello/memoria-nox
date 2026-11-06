#!/usr/bin/env python3
"""Paper D, step 5 (PREREGISTRATION.md §5.4, decision D8): the blind human sample.

  python3 -I d-human.py make   --private <dir>         writes <dir>/human-sample.csv
  python3 -I d-human.py agree  --private <dir>         prints agreement and kappa with judge 1
  python3 -I d-human.py commit --private <dir>         writes <dir>/HUMAN-COMMITMENT.json

`make` draws 60 rows uniformly from the (primary question, arm) pairs with arm C0 or C2 in
<dir>/run/results.json (seed 20261106) and writes them in random order with the question, the
reference answer and the candidate answer, and nothing else: no arm, no judge output. The grader
fills the last column with s or n; its header states the predicate. `agree` and `commit` recompute
the draw, refuse a sheet that is not exactly those rows with the texts `make` wrote, and refuse an
ungraded row. `commit` records the sheet's sha256, the counts and the sha256 of the results and
questions it was drawn from; push it before d-read.sh. --n other than 60 needs --smoke.
"""
import argparse
import csv
import importlib.util
import json
import pathlib
import random
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dcommon", HERE / "d-common.py")
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)
N = 60
GRADE = "contem: s se a resposta contém o fato da referência / n se não contém (NAO SEI = n)"
COLS = ["item", "pergunta", "referencia", "resposta", GRADE]


def ws(t):
    return re.sub(r"\s+", " ", t or "").strip()


def load(a):
    if a.n != N and not a.smoke:
        sys.exit(f"refusing: the registered sample is {N} rows; --n {a.n} needs --smoke")
    P = C.private(a.private)
    res = json.loads((P / "run" / "results.json").read_text(encoding="utf-8"))
    if res["meta"]["smoke"] is not bool(a.smoke):
        sys.exit(f"refusing: the results say smoke={res['meta']['smoke']}")
    qs = {q["qid"]: q for q in map(json.loads, open(P / "questions.jsonl", encoding="utf-8"))}
    rows = {(r["qid"], r["arm"]): r for r in res["rows"]}
    pairs = sorted(k for k in rows if k[1] in ("C0", "C2") and qs[k[0]]["set"] == "primary")
    rng = random.Random(C.SEED)
    pick = rng.sample(pairs, a.n)
    rng.shuffle(pick)
    return P, qs, rows, pick, len(pairs)


def make(a):
    P, qs, rows, pick, npairs = load(a)
    out = P / "human-sample.csv"
    if out.exists():
        sys.exit(f"refusing: {out} exists; the sheet is made once")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(COLS)
        for i, k in enumerate(pick, 1):
            q = qs[k[0]]
            w.writerow([i, q["question"], q["ref"], rows[k]["answer"], ""])
    print(f"{a.n} rows of {npairs} written to {out}; fill the last column with s or n")


def read_sheet(a):
    P, qs, rows, pick, _ = load(a)
    text = open(P / "human-sample.csv", encoding="utf-8-sig", newline="").read()
    first = text.split("\n", 1)[0]
    delim = ";" if first.count(";") > first.count(",") else ","
    got = list(csv.DictReader(text.splitlines(keepends=True), delimiter=delim))
    if not got or set(COLS[:4]) - set(got[0]) or not any(c.startswith("contem") for c in got[0]):
        sys.exit("refusing: the sheet does not have the columns make wrote")
    gcol = next(c for c in got[0] if c.startswith("contem"))
    if sorted(int(r["item"]) for r in got) != list(range(1, len(pick) + 1)):
        sys.exit("refusing: the sheet's items are not the registered draw")
    graded = []
    for r in got:
        k = pick[int(r["item"]) - 1]
        q = qs[k[0]]
        if (ws(r["pergunta"]), ws(r["referencia"]), ws(r["resposta"])) != \
                (ws(q["question"]), ws(q["ref"]), ws(rows[k]["answer"])):
            sys.exit(f"refusing: item {r['item']}: the texts are not what make wrote")
        v = (r[gcol] or "").strip().lower()
        if v not in ("s", "n"):
            sys.exit(f"refusing: item {r['item']} is graded {v!r}, expected s or n")
        graded.append((int(v == "s"), int(bool(rows[k]["j1"]))))
    return P, graded


def agree(a):
    P, g = read_sheet(a)
    t = {(h, j): sum(1 for x in g if x == (h, j)) for h in (1, 0) for j in (1, 0)}
    n = len(g)
    po = (t[(1, 1)] + t[(0, 0)]) / n
    ph, pj = (t[(1, 1)] + t[(1, 0)]) / n, (t[(1, 1)] + t[(0, 1)]) / n
    pe = ph * pj + (1 - ph) * (1 - pj)
    kappa = (po - pe) / (1 - pe) if pe < 1 else float("nan")
    print(f"n {n} · agreement {po:.3f} · kappa {kappa:.3f} · human yes & judge yes {t[(1, 1)]} · "
          f"human yes & judge no {t[(1, 0)]} · human no & judge yes {t[(0, 1)]} · "
          f"human no & judge no {t[(0, 0)]}")
    return P, {"n": n, "agreement": round(po, 4), "kappa": round(kappa, 4),
               "table": {"yes_yes": t[(1, 1)], "yes_no": t[(1, 0)], "no_yes": t[(0, 1)],
                         "no_no": t[(0, 0)]}}


def commit(a):
    P, res = agree(a)
    out = {"smoke": bool(a.smoke), **res, "seed": C.SEED,
           "sheet_sha256": C.sha_file(P / "human-sample.csv"),
           "results_sha256": C.sha_file(P / "run" / "results.json"),
           "questions_sha256": C.sha_file(P / "questions.jsonl")}
    (P / "HUMAN-COMMITMENT.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {P / 'HUMAN-COMMITMENT.json'}; copy it into {C.D}/, commit, push, then d-read.sh")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("make", "agree", "commit"))
    ap.add_argument("--private", required=True)
    ap.add_argument("--n", type=int, default=N)
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    {"make": make, "agree": agree, "commit": commit}[a.mode](a)
