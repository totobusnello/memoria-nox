#!/usr/bin/env python3
"""Paper A: the blind human sample (PREREGISTRATION.md §4, registered and mandatory).

  make:   python3 -I human-sample.py make  --labels <labels.json> --holdout <holdout.jsonl>
              --db <snapshot.db> --out <private>/human-sample.csv
  agree:  python3 -I human-sample.py agree --labels <labels.json> --sheet <private>/human-sample.csv
  commit: python3 -I human-sample.py commit --labels <labels.json> --sheet <graded sheet>
              --holdout <holdout.jsonl> --db <snapshot.db> --score <score.json>
              --out HUMAN-COMMITMENT.json                                 (then push it)

`agree` and `commit` recompute the registered draw from the labels and refuse a sheet that is not
exactly those pairs, once each, all graded. `commit` also checks that each row's question and
passage are the holdout's question and the first 6,000 characters of the chunk in the snapshot,
whitespace-normalised (a spreadsheet program may rewrite line endings), so the human graded what
the judge saw. `--n` other than 60 is accepted only with --smoke.

make draws 60 (query, chunk) pairs uniformly at random from ALL pairs the judge labelled (seed
20261105), and writes a sheet with the question and the first 6,000 characters of the chunk (what
the judge saw), in random order, WITHOUT the judge's probability. The grader fills the column
`relevante` with s or n. A simple random sample, not an equal-per-stratum one: an equal sample
reports agreement rates no population has (measured here on 2026-10-27, where a stratified flip
rate of 20.0% was 4.5% in the census).

agree reports raw agreement, Cohen's kappa between the grader and the judge at p > 0.5, and the
2x2 table. No threshold is registered: the paper reports the figure, and if kappa is below 0.4 it
states that its judge-dependent conclusions are not validated by the grader.

Both outputs are private (questions and corpus text); the script refuses a path inside a git
repository. Only the counts printed by `agree` are published.
"""
import argparse
import csv
import json
import pathlib
import random
import re
import sqlite3
import subprocess
import sys

N, SEED, THRESH, CHARS = 60, 20261105, 0.5, 6000


def inside_repo(p):
    return subprocess.run(["git", "-C", str(pathlib.Path(p).resolve().parent), "rev-parse"],
                          capture_output=True).returncode == 0


def registered_pick(labels_p, n):
    lab = json.load(open(labels_p))["rows"]
    pairs = sorted({(int(r["query_id"]), int(r["chunk_id"])) for r in lab
                    if r.get("prob_contem_resposta") is not None})
    rng = random.Random(SEED)
    pick = rng.sample(pairs, n)
    rng.shuffle(pick)
    return pick, len(pairs)


def check_n(a):
    if a.n != N and not a.smoke:
        sys.exit(f"refusing: the registered sample is {N} pairs; --n {a.n} needs --smoke")


def make(a):
    check_n(a)
    if inside_repo(a.out):
        sys.exit("refusing: --out is inside a git repository")
    pick, npairs = registered_pick(a.labels, a.n)
    pairs = range(npairs)
    q = {int(json.loads(l)["query_id"]): json.loads(l)["query"] for l in open(a.holdout)}
    con = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["item", "query_id", "chunk_id", "pergunta", "trecho", "relevante"])
        for i, (qid, cid) in enumerate(pick, 1):
            t = con.execute("SELECT chunk_text FROM chunks WHERE id = ?", (cid,)).fetchone()[0]
            w.writerow([i, qid, cid, q[qid], t[:CHARS], ""])
    print(f"{a.n} pairs of {npairs} written to the sheet; fill `relevante` with s or n")


def read_sheet(a):
    check_n(a)
    rows = list(csv.DictReader(open(a.sheet, encoding="utf-8")))
    got = [(int(r["query_id"]), int(r["chunk_id"])) for r in rows]
    want, _ = registered_pick(a.labels, a.n)
    if sorted(got) != sorted(want) or len(set(got)) != len(got):
        sys.exit("refusing: the sheet is not exactly the registered draw of pairs")
    if a.mode == "commit":
        if not (a.holdout and a.db and a.score):
            sys.exit("refusing: commit needs --holdout, --db and --score")
        ws = lambda t: re.sub(r"\s+", " ", t).strip()
        q = {int(json.loads(l)["query_id"]): json.loads(l)["query"] for l in open(a.holdout)}
        con = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
        for r in rows:
            t = con.execute("SELECT chunk_text FROM chunks WHERE id = ?",
                            (int(r["chunk_id"]),)).fetchone()
            if ws(r["pergunta"]) != ws(q[int(r["query_id"])]) or t is None \
                    or ws(r["trecho"]) != ws(t[0][:CHARS]):
                sys.exit(f"refusing: item {r['item']}: question or passage is not what the judge saw")
    return rows


def agree(a):
    rows = read_sheet(a)
    P = {(int(r["query_id"]), int(r["chunk_id"])): r["prob_contem_resposta"]
         for r in json.load(open(a.labels))["rows"] if r.get("prob_contem_resposta") is not None}
    t = {(h, j): 0 for h in (1, 0) for j in (1, 0)}
    for r in rows:
        v = r["relevante"].strip().lower()
        if v not in ("s", "n"):
            sys.exit(f"item {r['item']}: `relevante` is {v!r}, expected s or n")
        h = int(v == "s")
        j = int(P[(int(r["query_id"]), int(r["chunk_id"]))] > THRESH)
        t[(h, j)] += 1
    n = len(rows)
    po = (t[(1, 1)] + t[(0, 0)]) / n
    ph, pj = (t[(1, 1)] + t[(1, 0)]) / n, (t[(1, 1)] + t[(0, 1)]) / n
    pe = ph * pj + (1 - ph) * (1 - pj)
    kappa = (po - pe) / (1 - pe) if pe < 1 else float("nan")
    print(f"n {n} · agreement {po:.3f} · kappa {kappa:.3f}")
    print(f"  human yes & judge yes {t[(1, 1)]} · human yes & judge no {t[(1, 0)]} · "
          f"human no & judge yes {t[(0, 1)]} · human no & judge no {t[(0, 0)]}")
    return {"n": n, "agreement": round(po, 4), "kappa": round(kappa, 4),
            "table": {"yes_yes": t[(1, 1)], "yes_no": t[(1, 0)], "no_yes": t[(0, 1)],
                      "no_no": t[(0, 0)]}}


def commit(a):
    import hashlib
    res = agree(a)
    if inside_repo(a.sheet):
        sys.exit("refusing: the graded sheet must stay outside the repository")
    sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
    out = {"smoke": bool(a.smoke), **res, "seed": SEED, "sheet_sha256": sha(a.sheet),
           "labels_sha256": sha(a.labels), "score_sha256": sha(a.score),
           "holdout_sha256": sha(a.holdout)}
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    print(f"wrote {a.out}; push it before read-h-a1.sh")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("make", "agree", "commit"))
    for k in ("--labels", "--holdout", "--db", "--out", "--sheet", "--score"):
        ap.add_argument(k)
    ap.add_argument("--n", type=int, default=N, help="registered: 60; another value needs --smoke")
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    {"make": make, "agree": agree, "commit": commit}[a.mode](a)
