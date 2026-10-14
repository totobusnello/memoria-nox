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
COLUMNS = ("id", "timestamp_ms", "provider", "model", "op_type", "tokens_in", "tokens_out",
           "cost_estimate_usd", "latency_ms", "success", "caller", "phase", "tokens_src")


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
    m["clean_usd_per_construction_call"] = clean["construction_cost"] / clean["construction_calls"]
    m["clean_usd_per_query_call"] = clean["query_cost"] / clean["query_calls"]
    m["clean_construction_to_query_cost_ratio"] = (m["clean_usd_per_construction_call"]
                                                   / m["clean_usd_per_query_call"])
    m["flagged_usd_per_query_call"] = ((raw["query_cost"] - clean["query_cost"])
                                       / (raw["query_calls"] - clean["query_calls"]))
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
    # Longest run of calendar days (all 32, with or without rows) that has no
    # construction or maintenance row.
    cal = [datetime.fromtimestamp((WIN_START + i * DAY_MS) / 1000, timezone.utc).date().isoformat()
           for i in range(32)]
    best, run = (0, None, None), []
    for d in cal:
        s = days.get(d, set())
        if "construction" in s or "maintenance" in s:
            run = []
            continue
        run.append(d)
        if len(run) > best[0]:
            best = (len(run), run[0], run[-1])
    m["write_silent_days"], m["write_silent_first"], m["write_silent_last"] = best
    in_silent = [r for r in rows if best[1] <= datetime.fromtimestamp(r["ts"] / 1000, timezone.utc).date().isoformat() <= best[2]]
    m["write_silent_rows"] = len(in_silent)
    m["write_silent_query_rows"] = sum(1 for r in in_silent if r["phase"] == "query")
    m["write_silent_canary_pct"] = 100 * sum(1 for r in in_silent if r["canary"]) / m["write_silent_query_rows"]
    m["first_row_date"] = datetime.fromtimestamp(rows[0]["ts"] / 1000, timezone.utc).date().isoformat()
    m["columns"] = len([k for k in rows[0] if k in COLUMNS])
    m["first_day_hours"] = (rows[0]["ts"] - WIN_START) / 3_600_000
    m["first_day_hours_covered"] = 24 - m["first_day_hours"]

    # Phase re-derived from caller, by the rule the note states.
    def rule(c):
        if c in ("embed.embedQuery", "search-expansion.expand"):
            return "query"
        if c in ("compact.gemini", "consolidate.gemini"):
            return "maintenance"
        return "construction"
    m["phase_rule_mismatches"] = sum(1 for r in rows if rule(r["caller"]) != r["phase"])

    m["failed_calls"] = sum(1 for r in rows if not r["ok"])
    m["failed_dates"] = len({datetime.fromtimestamp(r["ts"] / 1000, timezone.utc).date()
                             for r in rows if not r["ok"]})
    m["failed_not_query_embed"] = sum(1 for r in rows if not r["ok"] and r["caller"] != "embed.embedQuery")
    m["models"] = len({r["model"] for r in rows})
    m["callers"] = len({r["caller"] for r in rows})
    m["kg_extract_rows"] = sum(1 for r in rows if r["caller"] == "kg-llm.extract")
    m["kg_extract_non_smoke"] = sum(1 for r in rows if r["caller"] == "kg-llm.extract" and not r["smoke"])
    m["tokens_estimated_pct"] = 100 * sum(1 for r in rows if r["tokens_src"] == "estimated") / len(rows)
    m["smoke_rows"] = sum(1 for r in rows if r["smoke"])
    m["query_embed_calls"] = sum(1 for r in qry if r["op_type"] == "embed")
    m["input_token_ratio"] = m["mean_tin_construction"] / m["mean_tin_query"]
    top3 = sorted(rows, key=lambda r: r["cost"], reverse=True)[:3]
    m["top3_digest_calls"] = sum(1 for r in top3 if r["caller"] == "digest.gemini")

    # Construction cost by day: days above 10 milli-USD and their share.
    cday = {}
    for r in cons:
        d = datetime.fromtimestamp(r["ts"] / 1000, timezone.utc).date()
        cday[d] = cday.get(d, 0.0) + r["cost"]
    tall = [v for v in cday.values() if v > 0.010]
    m["construction_days_over_10musd"] = len(tall)
    m["construction_cost_pct_on_those_days"] = 100 * sum(tall) / raw["construction_cost"]

    # 2026-08-10 window: the 02:00-02:03Z burst and the rest.
    b0 = WIN_START + 3 * DAY_MS + 2 * 3_600_000
    aug = [r for r in rows if r["aug10"]]
    m["aug10_burst_rows"] = sum(1 for r in aug if b0 <= r["ts"] < b0 + 3 * 60_000)
    m["aug10_other_rows"] = len(aug) - m["aug10_burst_rows"]

    # Unflagged query rows in 02:00-02:59Z on dates whose 02:00 hour also has maintenance rows.
    def hour2(r):
        t = datetime.fromtimestamp(r["ts"] / 1000, timezone.utc)
        return t.date() if t.hour == 2 else None
    mdates = {hour2(r) for r in rows if r["phase"] == "maintenance"} - {None}
    night = [r for r in qry if not r["annotated"] and hour2(r) in mdates]
    m["nightly_unflagged_query_rows"] = len(night)
    m["nightly_dates"] = len({hour2(r) for r in night})

    # Gaps between consecutive rows (minutes): how many exceed 32 minutes, and the largest other gap.
    gaps = [(b["ts"] - a["ts"]) / 60_000 for a, b in zip(rows, rows[1:])]
    m["gaps_over_32min"] = sum(1 for g in gaps if g > 32.0)
    m["max_gap_otherwise_min"] = max(g for g in gaps if g <= 32.0)
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
