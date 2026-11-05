#!/usr/bin/env python3
"""Paper A: the blind human sample (PREREGISTRATION.md §4, registered and mandatory).

  make:   python3 -I human-sample.py make  --labels <labels.json> --holdout <holdout.jsonl>
              --db <snapshot.db> --out <private>/human-sample.csv
  agree:  python3 -I human-sample.py agree --labels <labels.json> --sheet <private>/human-sample.csv

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
import sqlite3
import subprocess
import sys

N, SEED, THRESH, CHARS = 60, 20261105, 0.5, 6000


def inside_repo(p):
    return subprocess.run(["git", "-C", str(pathlib.Path(p).resolve().parent), "rev-parse"],
                          capture_output=True).returncode == 0


def make(a):
    if inside_repo(a.out):
        sys.exit("refusing: --out is inside a git repository")
    lab = json.load(open(a.labels))["rows"]
    pairs = sorted({(int(r["query_id"]), int(r["chunk_id"])) for r in lab
                    if r.get("prob_contem_resposta") is not None})
    rng = random.Random(SEED)
    pick = rng.sample(pairs, N)
    rng.shuffle(pick)
    q = {int(json.loads(l)["query_id"]): json.loads(l)["query"] for l in open(a.holdout)}
    con = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["item", "query_id", "chunk_id", "pergunta", "trecho", "relevante"])
        for i, (qid, cid) in enumerate(pick, 1):
            t = con.execute("SELECT chunk_text FROM chunks WHERE id = ?", (cid,)).fetchone()[0]
            w.writerow([i, qid, cid, q[qid], t[:CHARS], ""])
    print(f"{N} pairs of {len(pairs)} written to the sheet; fill `relevante` with s or n")


def agree(a):
    P = {(int(r["query_id"]), int(r["chunk_id"])): r["prob_contem_resposta"]
         for r in json.load(open(a.labels))["rows"] if r.get("prob_contem_resposta") is not None}
    rows = list(csv.DictReader(open(a.sheet, encoding="utf-8")))
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


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("make", "agree"))
    for k in ("--labels", "--holdout", "--db", "--out", "--sheet"):
        ap.add_argument(k)
    a = ap.parse_args()
    sys.exit((make if a.mode == "make" else agree)(a))
