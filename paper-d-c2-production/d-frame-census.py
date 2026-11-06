#!/usr/bin/env python3
"""Paper D: census of the session frame. Read-only, no LLM, no cost. Counts only.

Runs on the host that keeps the archive, with d-select.py and d-common.py in /var/tmp/paper-d-census (not /tmp: tmpfs):

  scp d-select.py <host>:/var/tmp/paper-d-census/dsel.py && scp d-common.py <host>:/var/tmp/paper-d-census/dcommon.py
  scp <exclude file> <host>:/var/tmp/paper-d-census/d-exclude.txt
  ssh <host> python3 - --db <path to a database> --start 2026-08-15 --end 2026-10-29 < d-frame-census.py

Applies d-select.py's eligibility (last event inside [start, end], cleaned prose >= 3,000 chars,
not one of the 20 sessions spent on 2026-10-26/27, not in the exclude file) and splits the eligible
sessions by what the production distiller did with them, read from the database given:

  logged, with units   a row in session_distill_log and >= 1 chunk under sessions/
  logged, zero units   a row in session_distill_log and no chunk under sessions/
  never logged         no row in session_distill_log (the distiller never reached it)

and, for the logged ones, by prose band. It also reports the sum of chunks_extracted against the
chunks still present, so a unit lost after extraction would show. Since 2026-11-06 it also splits
the logged sessions by the message_count production recorded (fewer than 3: production's rule
skips the session without calling the model), and recounts that number from the transcript with
production's parser up to processed_at (d-common.py prod_messages): a check of how well the
visible prefix is reconstructed. Arm V takes the rule from the log's message_count. Prints no id
and no text.
"""
import argparse
import collections
import json
import os
import sqlite3

exec(open("/var/tmp/paper-d-census/dsel.py").read().split("def main():")[0])  # noqa: S102  (ARCHIVE, UUID, scan, glob)
import importlib.util  # noqa: E402
_s = importlib.util.spec_from_file_location("dcommon", "/var/tmp/paper-d-census/dcommon.py")
DC = importlib.util.module_from_spec(_s)
_s.loader.exec_module(DC)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--min-chars", type=int, default=3000)
    ap.add_argument("--spent", default="/root/medicoes/2026-10-26-memory-tax/replay-set.json")
    ap.add_argument("--exclude", default="/var/tmp/paper-d-census/d-exclude.txt")
    a = ap.parse_args()
    if not os.path.exists(a.db):
        raise SystemExit(f"no database at {a.db}")          # sqlite3 would create an empty one
    spent = {s["uuid"] for s in json.load(open(a.spent))["sessions"]}
    excl = set(open(a.exclude).read().split()) if os.path.exists(a.exclude) else set()
    con = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    present = collections.Counter()
    for (sf,) in con.execute("SELECT source_file FROM chunks WHERE source_file LIKE 'sessions/%'"):
        m = UUID.search(sf)
        if m:
            present[m.group(1)] += 1
    extracted, msgs, pat = collections.defaultdict(int), collections.defaultdict(int), {}
    for k, ce, mc, pa in con.execute(
            "SELECT session_key, chunks_extracted, message_count, processed_at FROM session_distill_log"):
        m = UUID.search(k or "")
        if m:
            u = m.group(1)
            extracted[u] += ce or 0
            msgs[u] = max(msgs[u], mc or 0)
            pat[u] = max(pat.get(u, ""), pa or "")
    best = {}
    for p in glob.glob(os.path.join(ARCHIVE, "*", "*.jsonl")):
        m = UUID.search(os.path.basename(p))
        if m:
            u, sz = m.group(1), os.path.getsize(p)
            if u not in best or sz > best[u][1]:
                best[u] = (p, sz)
    c, bands, never_dirs = collections.Counter(), collections.Counter(), collections.Counter()
    c["archive_sessions"] = len(best)
    for u, (p, _) in best.items():
        if u in spent:
            c["excluded_spent"] += 1
            continue
        if u in excl:
            c["excluded_listed"] += 1
            continue
        chars, last = scan(p)
        if not (a.start <= last <= a.end and chars >= a.min_chars):
            continue
        c["eligible"] += 1
        if u not in extracted:
            c["never_logged"] += 1
            never_dirs[os.path.basename(os.path.dirname(p))] += 1
            continue
        c["logged"] += 1
        c["logged_with_units" if present[u] else "logged_zero_units"] += 1
        sent = msgs[u] >= 3
        c[f"logged_{'with_units' if present[u] else 'zero_units'}_{'sent' if sent else 'skipped_lt3_messages'}"] += 1
        c["recount_equals_log" if DC.visible_count(DC.prod_messages(p), pat[u]) == msgs[u]
          else "recount_differs_from_log"] += 1
        c["chunks_extracted_sum"] += extracted[u]
        c["chunks_present_sum"] += present[u]
        bands["<50k" if chars < 50_000 else "50k-200k" if chars < 200_000 else ">=200k"] += 1
    print(json.dumps({"window": [a.start, a.end], "min_chars": a.min_chars, "counts": dict(c),
                      "logged_by_prose_band": dict(bands),
                      "never_logged_by_directory": dict(never_dirs.most_common())}, indent=1))


if __name__ == "__main__":
    main()
