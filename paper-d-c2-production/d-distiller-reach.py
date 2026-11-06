#!/usr/bin/env python3
"""Paper D follow-up (read-only, no LLM): which eligible sessions the production distiller reached,
by week of last event, and what happened to the reached ones since 2026-09-20.

Eligible: last event in [start, end], at least 3,000 characters of cleaned prose once turns starting
with "[cron:", "HEARTBEAT" or "The conversation history before this point" are dropped (production's
input rule), not one of the 20 spent sessions. The "seen" columns model the live roots with
prune-claude-sessions.sh (daily 04:23 UTC: *.jsonl < 50 KiB older than 12 h, and any older than
7 days); that job prunes only /root/.claude/projects, one of the five roots the distiller reads, so
"seen" is an upper bound and is not used in the note. The week split and the sent/skipped split are
read from session_distill_log and are the results. Counts only."""
import argparse, collections, datetime as dt, glob, json, os, sqlite3
exec(open("/var/tmp/paper-d-census/dsel.py").read().split("def main():")[0])  # noqa: S102
DROP = ("[cron:", "HEARTBEAT", "The conversation history before this point")
UTC = dt.timezone.utc

def scan2(p):
    chars, last, ncron = 0, "", 0
    for line in open(p, encoding="utf-8", errors="replace"):
        try: o = json.loads(line)
        except Exception: continue
        ts = o.get("timestamp") or ""
        if isinstance(ts, str) and ts > last: last = ts
        s = turn_text(o)
        if not s: continue
        body = s.split(": ", 1)[1] if ": " in s else s
        if not body.lstrip().startswith(DROP): chars += len(s) + 2
        elif body.lstrip().startswith("[cron:"): ncron += 1
    return chars, last, ncron

def parse(ts):
    return dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(UTC)

def deletion(mtime, size):
    d = mtime.replace(hour=4, minute=23, second=0, microsecond=0)
    if d <= mtime: d += dt.timedelta(days=1)
    small = size < 50 * 1024
    while True:
        age = d - mtime
        if (small and age > dt.timedelta(hours=12)) or age >= dt.timedelta(days=8):
            return d
        d += dt.timedelta(days=1)

def runs_between(a, b, sunday_only):
    d = a.replace(hour=23, minute=0, second=0, microsecond=0)
    if d < a: d += dt.timedelta(days=1)
    n = 0
    while d < b:
        if not sunday_only or d.isoweekday() == 7: n += 1
        d += dt.timedelta(days=1)
    return n

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True); ap.add_argument("--start", required=True); ap.add_argument("--end", required=True)
    ap.add_argument("--spent", default="/root/medicoes/2026-10-26-memory-tax/replay-set.json")
    a = ap.parse_args()
    if not os.path.exists(a.db): raise SystemExit(f"no database at {a.db}")
    spent = {s["uuid"] for s in json.load(open(a.spent))["sessions"]}
    con = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    logged = {}
    for k, mc in con.execute("SELECT session_key, message_count FROM session_distill_log"):
        m = UUID.search(k or "")
        if m: logged[m.group(1)] = max(logged.get(m.group(1), 0), mc or 0)
    best = {}
    for p in glob.glob(os.path.join(ARCHIVE, "*", "*.jsonl")):
        m = UUID.search(os.path.basename(p))
        if m:
            u, sz = m.group(1), os.path.getsize(p)
            if u not in best or sz > best[u][1]: best[u] = (p, sz)
    xt = collections.Counter(); c = collections.Counter()
    for u, (p, sz) in best.items():
        if u in spent: continue
        chars, last, ncron = scan2(p)
        if not last or not (a.start <= last[:10] <= a.end) or chars < 3000: continue
        mt = parse(last); de = deletion(mt, sz)
        c["eligible"] += 1
        c["small_lt_50KiB"] += sz < 50 * 1024
        sun = runs_between(mt, de, True) > 0
        day = runs_between(mt, de, False) > 0
        wk = (mt - dt.timedelta(days=(mt.isoweekday() % 7))).strftime("%Y-%m-%d")
        xt[("week_from_sunday", wk, "logged" if u in logged else "never_logged")] += 1
        if last[:10] >= "2026-09-20" and u in logged:
            xt[("since_2026-09-20", "sent" if logged[u] >= 3 else "skipped_lt3", "with_cron_prompt" if ncron else "no_cron_prompt")] += 1
            if logged[u] < 3: xt[("since_2026-09-20", "skipped_lt3", "logged_message_count", str(logged[u]))] += 1
        xt[f"predicted_{'seen' if sun else 'unseen'}__{'logged' if u in logged else 'never_logged'}"] += 1
        c["seen_sunday_model"] += sun; c["seen_daily_model"] += day
        c["logged"] += u in logged; c["logged_sent"] += logged.get(u, 0) >= 3
    print(json.dumps({"window": [a.start, a.end], "counts": dict(sorted(c.items())),
                      "prediction_vs_log": {" | ".join(k) if isinstance(k, tuple) else k: v for k, v in sorted(xt.items(), key=str)}}, indent=1))

if __name__ == "__main__":
    main()
