#!/usr/bin/env python3
"""C2 shadow study, step 2 (SHADOW-PREREGISTRATION.md §2 and §6): the weekly stopping-rule check.

  python3 -I s-count.py --src <shadow directory> --log <counts log>
  python3 -I s-count.py --src <dir> --log <file> --smoke --today YYYY-MM-DD     (tests only)

Run by the author where the shadow files are. Reads every c2-shadow-<date>.jsonl dated from
2026-11-08 to today (UTC), applies the eligible-block rule of §2 (s-common.eligible) and the
exclusion of the three sessions of c2-shadow-2026-11-07.jsonl, and prints, and appends to the log
as one JSON line, ONLY counts: per date, the records, the C2 failures, the eligible blocks and
sessions (that date and cumulative), the exclusions by reason; and whether the stopping rule is
met and the freeze is due.

Privacy (SHADOW-PROTOCOL.md §5): the output is built from a positive list of fields whose values
are integers, booleans, dates or the hash of this script; it is checked against that list before
it is printed or written. No block text, unit text, session key or agent name can reach the
output. An error prints its type only, never its message, which could quote a record.
"""
import argparse
import datetime as dt
import importlib.util
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("scommon", HERE / "s-common.py")
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)

TS_RX = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
HEX_RX = re.compile(r"^[0-9a-f]{64}$")
DAY_KEYS = {"records", "c2_failures", "eligible_blocks", "eligible_sessions", "cum_eligible_blocks",
            "cum_eligible_sessions", "excluded"}
TOP_KEYS = {"smoke", "checked_at", "today", "script_sha256", "per_date", "totals", "other_files",
            "excluded_file", "stopping"}
TOTAL_KEYS = {"records", "c2_failures", "eligible_blocks", "eligible_sessions", "excluded"}
OTHER_KEYS = {"files_before_start", "files_after_window"}
EXCL_FILE_KEYS = {"sessions", "blocks"}
STOP_KEYS = {"reach_date", "threshold_met", "freeze_date", "due", "shortfall", "min_blocks",
             "min_sessions", "earliest", "latest"}


def _count(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def _date(v):
    return isinstance(v, str) and C.DATE_RX.match(v) is not None


def counts_only(o):
    """Refuse anything but the positive list: a field outside it, or a value of the wrong kind."""
    def need(cond, where):
        if not cond:
            raise SystemExit(f"refusing to print: {where} is not a permitted count")

    need(isinstance(o, dict) and set(o) == TOP_KEYS, "the top level")
    need(isinstance(o["smoke"], bool), "smoke")
    need(isinstance(o["checked_at"], str) and TS_RX.match(o["checked_at"]), "checked_at")
    need(_date(o["today"]), "today")
    need(isinstance(o["script_sha256"], str) and HEX_RX.match(o["script_sha256"]), "script_sha256")

    def excl(e, where):
        need(isinstance(e, dict) and set(e) == set(C.REASONS) and all(_count(v) for v in e.values()), where)

    need(isinstance(o["per_date"], dict), "per_date")
    for d, c in o["per_date"].items():
        need(_date(d), "a per_date key")
        need(isinstance(c, dict) and set(c) == DAY_KEYS, f"per_date[{d}]")
        need(all(_count(c[k]) for k in DAY_KEYS - {"excluded"}), f"per_date[{d}] values")
        excl(c["excluded"], f"per_date[{d}].excluded")
    t = o["totals"]
    need(isinstance(t, dict) and set(t) == TOTAL_KEYS and all(_count(t[k]) for k in TOTAL_KEYS - {"excluded"}),
         "totals")
    excl(t["excluded"], "totals.excluded")
    need(isinstance(o["other_files"], dict) and set(o["other_files"]) == OTHER_KEYS
         and all(_count(v) for v in o["other_files"].values()), "other_files")
    need(isinstance(o["excluded_file"], dict) and set(o["excluded_file"]) == EXCL_FILE_KEYS
         and all(_count(v) for v in o["excluded_file"].values()), "excluded_file")
    s = o["stopping"]
    need(isinstance(s, dict) and set(s) == STOP_KEYS, "stopping")
    for k in ("reach_date", "freeze_date"):
        need(s[k] is None or _date(s[k]), f"stopping.{k}")
    for k in ("earliest", "latest"):
        need(_date(s[k]), f"stopping.{k}")
    for k in ("threshold_met", "due", "shortfall"):
        need(isinstance(s[k], bool), f"stopping.{k}")
    for k in ("min_blocks", "min_sessions"):
        need(_count(s[k]), f"stopping.{k}")
    return o


def measure(src, today, smoke):
    excluded = C.excluded_keys(src)
    per, kept, other = C.scan(src, today, excluded)
    seen = set()
    for rows in kept.values():
        seen |= {C.r_session(o) for _, _, o in rows}
    totals = {"records": sum(c["records"] for c in per.values()),
              "c2_failures": sum(c["c2_failures"] for c in per.values()),
              "eligible_blocks": sum(c["eligible_blocks"] for c in per.values()),
              "eligible_sessions": len(seen),
              "excluded": {k: sum(c["excluded"][k] for c in per.values()) for k in C.REASONS}}
    out = {"smoke": bool(smoke),
           "checked_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "today": today, "script_sha256": C.sha_file(HERE / "s-count.py"),
           "per_date": {d: {k: c[k] for k in DAY_KEYS} for d, c in per.items()},
           "totals": totals, "other_files": dict(other),
           "excluded_file": {"sessions": C.EXCLUDED_SESSIONS, "blocks": C.EXCLUDED_BLOCKS},
           "stopping": C.stopping(per, today)}
    return counts_only(out)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--log", required=True)
    ap.add_argument("--today")
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args(argv)
    if a.today and not a.smoke:
        sys.exit("refusing: --today is for smoke runs; the check counts up to today's UTC date")
    today = a.today or C.utc_today()
    if not C.DATE_RX.match(today):
        sys.exit("refusing: --today is not YYYY-MM-DD")
    try:
        out = measure(a.src, today, a.smoke)
    except SystemExit:
        raise
    except Exception as e:                  # the message could quote a record: print the type only
        sys.exit(f"s-count failed: {type(e).__name__}")
    line = json.dumps(out, sort_keys=True)
    with open(a.log, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    print(json.dumps(out, indent=1, sort_keys=True))
    s = out["stopping"]
    print(f"eligible blocks {out['totals']['eligible_blocks']} · sessions {out['totals']['eligible_sessions']} · "
          f"threshold {'met on ' + s['reach_date'] if s['threshold_met'] else 'not met'} · "
          f"freeze {'due, date ' + s['freeze_date'] if s['due'] else 'not due'}"
          + (" · SHORTFALL" if s["shortfall"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
