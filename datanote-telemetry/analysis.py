#!/usr/bin/env python3
"""Recompute every number the data note cites, from the published dataset.

Dataset: 10.5281/zenodo.23130191 (v1.0.0). Standard library only.

    python3 analysis.py --dir <folder with the dataset files> [--json out.json]
    python3 analysis.py --fetch <empty folder>   # downloads the record, checks SHA256SUMS

The script reads the raw table and row_annotations.csv and prints a flat
key -> value map. DATA-NOTE.md cites only keys from this map; parity.py checks
that every number in the note matches one of them at the note's rounding.
"""
import argparse
import csv
import hashlib
import json
import os
import statistics
import sys
import urllib.request
from datetime import datetime, timezone

RECORD = "23130191"
RAW = "provider_telemetry_2026-08-07_2026-09-08.csv"
ANN = "row_annotations.csv"
WIN_START = 1786060800000  # 2026-08-07T00:00Z
WIN_END = 1788825600000    # 2026-09-08T00:00Z
DAY_MS = 86_400_000
PHASES = ("construction", "query", "maintenance")


def fetch(dest):
    os.makedirs(dest, exist_ok=True)
    with urllib.request.urlopen(f"https://zenodo.org/api/records/{RECORD}") as r:
        rec = json.load(r)
    for f in rec["files"]:
        path = os.path.join(dest, f["key"])
        with urllib.request.urlopen(f["links"]["self"]) as r, open(path, "wb") as out:
            out.write(r.read())
        algo, want = f["checksum"].split(":")
        got = hashlib.new(algo, open(path, "rb").read()).hexdigest()
        if got != want:
            sys.exit(f"checksum mismatch: {f['key']}")
    check_sums(dest)


def check_sums(d):
    for line in open(os.path.join(d, "SHA256SUMS")):
        want, name = line.split()
        got = hashlib.sha256(open(os.path.join(d, name.lstrip("*")), "rb").read()).hexdigest()
        if got != want:
            sys.exit(f"SHA256SUMS mismatch: {name}")


def load(d):
    rows = list(csv.DictReader(open(os.path.join(d, RAW), newline="")))
    for r in rows:
        r["id"] = int(r["id"])
        r["ts"] = int(r["timestamp_ms"])
        r["cost"] = float(r["cost_estimate_usd"])
        r["tin"] = int(r["tokens_in"])
        r["lat"] = int(r["latency_ms"])
        r["ok"] = int(r["success"])
    ann = {int(a["id"]): a for a in csv.DictReader(open(os.path.join(d, ANN), newline=""))}
    for r in rows:
        a = ann[r["id"]]
        r["annotated"] = any(int(a[k]) for k in ("smoke_test", "canary_signature", "aug10_burst_window"))
        r["canary"] = int(a["canary_signature"]) == 1
        r["aug10"] = int(a["aug10_burst_window"]) == 1
        r["smoke"] = int(a["smoke_test"]) == 1
    return rows


def shares(rows):
    n = len(rows)
    c = sum(r["cost"] for r in rows)
    out = {"calls": n, "cost": c}
    for p in PHASES:
        sub = [r for r in rows if r["phase"] == p]
        out[f"{p}_calls"] = len(sub)
        out[f"{p}_cost"] = sum(r["cost"] for r in sub)
        out[f"{p}_pct_calls"] = 100 * len(sub) / n
        out[f"{p}_pct_cost"] = 100 * out[f"{p}_cost"] / c
    return out


def measure(rows):
    m = {}
    raw = shares(rows)
    m.update({f"raw_{k}": v for k, v in raw.items()})
    clean = shares([r for r in rows if not r["annotated"]])
    m.update({f"clean_{k}": v for k, v in clean.items()})

    # Absolute scale.
    m["usd_per_day"] = raw["cost"] / 32
    m["usd_per_day_clean"] = clean["cost"] / 32

    # Per-call cost ratio: one construction call vs one query call.
    cons = [r for r in rows if r["phase"] == "construction"]
    qry = [r for r in rows if r["phase"] == "query"]
    m["usd_per_construction_call"] = raw["construction_cost"] / len(cons)
    m["usd_per_query_call"] = raw["query_cost"] / len(qry)
    m["construction_to_query_cost_ratio"] = m["usd_per_construction_call"] / m["usd_per_query_call"]
    m["mean_tin_construction"] = statistics.mean(r["tin"] for r in cons)
    m["mean_tin_query"] = statistics.mean(r["tin"] for r in qry)

    # Concentration: smallest number of calls holding half of total cost.
    costs = sorted((r["cost"] for r in rows), reverse=True)
    acc, k = 0.0, 0
    while acc < raw["cost"] / 2:
        acc += costs[k]
        k += 1
    m["calls_for_half_cost"] = k
    m["pct_calls_for_half_cost"] = 100 * k / len(rows)
    m["top3_pct_cost"] = 100 * sum(costs[:3]) / raw["cost"]
    no_top3 = sorted(rows, key=lambda r: r["cost"], reverse=True)[3:]
    m["construction_pct_cost_without_top3"] = shares(no_top3)["construction_pct_cost"]

    # Amortization: construction cost per query call, by 7-day block of the window
    # (blocks 1-4 are 7 days, block 5 is the remaining 4 days).
    def block(ts):
        return min((ts - WIN_START) // (7 * DAY_MS), 4)

    for label, sel in (("raw", rows), ("clean", [r for r in rows if not r["annotated"]])):
        vals = []
        for b in range(5):
            sub = [r for r in sel if block(r["ts"]) == b]
            cc = sum(r["cost"] for r in sub if r["phase"] == "construction")
            nq = sum(1 for r in sub if r["phase"] == "query")
            v = cc / nq if nq else None
            m[f"amort_{label}_block{b + 1}"] = v
            m[f"amort_{label}_block{b + 1}_queries"] = nq
            if v is not None:
                vals.append(v)
        m[f"amort_{label}_min"] = min(vals)
        m[f"amort_{label}_max"] = max(vals)
        m[f"amort_{label}_zero_blocks"] = sum(1 for v in vals if v == 0)

    # What the log contains.
    m["query_annotated"] = sum(1 for r in qry if r["annotated"])
    m["query_unannotated"] = len(qry) - m["query_annotated"]
    for key in ("canary", "aug10", "smoke"):
        m[f"query_{key}"] = sum(1 for r in qry if r[key])
        m[f"query_{key}_pct"] = 100 * m[f"query_{key}"] / len(qry)
    m["query_unannotated_pct"] = 100 * m["query_unannotated"] / len(qry)
    m["query_annotated_pct"] = 100 * m["query_annotated"] / len(qry)
    m["annotated_rows"] = sum(1 for r in rows if r["annotated"])
    m["annotated_cost_pct"] = 100 * sum(r["cost"] for r in rows if r["annotated"]) / raw["cost"]

    days = {}
    for r in rows:
        d = datetime.fromtimestamp(r["ts"] / 1000, timezone.utc).date().isoformat()
        days.setdefault(d, set()).add(r["phase"])
    m["days_with_rows"] = len(days)
    for p in PHASES:
        m[f"days_{p}"] = sum(1 for s in days.values() if p in s)
    write_silent = [d for d, s in sorted(days.items())
                    if "construction" not in s and "maintenance" not in s and d >= "2026-08-25"]
    m["write_silent_first"] = write_silent[0]
    m["write_silent_days"] = sum(1 for d in write_silent if d <= "2026-09-06")

    m["failed_calls"] = sum(1 for r in rows if not r["ok"])
    m["models"] = len({r["model"] for r in rows})
    m["callers"] = len({r["caller"] for r in rows})
    m["kg_extract_rows"] = sum(1 for r in rows if r["caller"] == "kg-llm.extract")
    m["tokens_estimated_pct"] = 100 * sum(1 for r in rows if r["tokens_src"] == "estimated") / len(rows)
    return m


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dir")
    g.add_argument("--fetch")
    ap.add_argument("--json")
    a = ap.parse_args()
    d = a.dir
    if a.fetch:
        fetch(a.fetch)
        d = a.fetch
    check_sums(d)
    rows = [r for r in load(d) if WIN_START <= r["ts"] < WIN_END]
    m = measure(rows)
    if a.json:
        json.dump(m, open(a.json, "w"), indent=1, sort_keys=True)
    for k in sorted(m):
        print(f"{k} = {m[k]}")


if __name__ == "__main__":
    main()
