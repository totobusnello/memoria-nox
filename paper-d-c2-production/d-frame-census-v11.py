#!/usr/bin/env python3
"""Paper D v1.1 census (read-only, no LLM): the frame under production's input rule.
Same eligibility as d-frame-census.py, but the prose counted is what production's distiller would
send: cleaned turns minus any turn whose text starts with "[cron:", "HEARTBEAT" or "The conversation
history before this point". Splits by distill log status and by message_count >= 3. Counts only."""
import argparse, collections, glob, json, os, sqlite3
exec(open("/var/tmp/paper-d-census/dsel.py").read().split("def main():")[0])  # noqa: S102
DROP = ("[cron:", "HEARTBEAT", "The conversation history before this point")

def prose_and_last(p):
    chars, raw, last, ncron = 0, 0, "", 0
    for line in open(p, encoding="utf-8", errors="replace"):
        try: o = json.loads(line)
        except Exception: continue
        ts = o.get("timestamp") or ""
        if isinstance(ts, str) and ts > last: last = ts
        s = turn_text(o)
        if not s: continue
        raw += len(s) + 2
        body = s.split(": ", 1)[1] if ": " in s else s
        if body.lstrip().startswith(DROP):
            ncron += body.lstrip().startswith("[cron:"); continue
        chars += len(s) + 2
    return chars, raw, last[:10], ncron

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True); ap.add_argument("--start", required=True); ap.add_argument("--end", required=True)
    ap.add_argument("--spent", default="/root/medicoes/2026-10-26-memory-tax/replay-set.json")
    ap.add_argument("--exclude", default="/var/tmp/paper-d-census/exclude.txt")
    a = ap.parse_args()
    if not os.path.exists(a.db): raise SystemExit(f"no database at {a.db}")
    spent = {s["uuid"] for s in json.load(open(a.spent))["sessions"]}
    excl = set(open(a.exclude).read().split())
    con = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    present = collections.Counter()
    for (sf,) in con.execute("SELECT source_file FROM chunks WHERE source_file LIKE 'sessions/%'"):
        m = UUID.search(sf)
        if m: present[m.group(1)] += 1
    msgs = {}
    for k, mc in con.execute("SELECT session_key, message_count FROM session_distill_log"):
        m = UUID.search(k or "")
        if m: msgs[m.group(1)] = max(msgs.get(m.group(1), 0), mc or 0)
    best = {}
    for p in glob.glob(os.path.join(ARCHIVE, "*", "*.jsonl")):
        m = UUID.search(os.path.basename(p))
        if m:
            u, sz = m.group(1), os.path.getsize(p)
            if u not in best or sz > best[u][1]: best[u] = (p, sz)
    c = collections.Counter(); bands = collections.Counter()
    for u, (p, _) in best.items():
        if u in spent or u in excl: c["excluded"] += 1; continue
        chars, raw, last, ncron = prose_and_last(p)
        if not (a.start <= last <= a.end): continue
        if raw >= 3000: c["eligible_v1_rule"] += 1
        if chars < 3000:
            if raw >= 3000: c["lost_by_dropping_cron"] += 1
            continue
        c["eligible_v11"] += 1
        c["eligible_v11_with_cron_prompt"] += ncron > 0
        if u not in msgs: c["v11_never_logged"] += 1; continue
        c["v11_logged"] += 1
        sent = msgs[u] >= 3
        c["v11_logged_sent" if sent else "v11_logged_skipped_lt3"] += 1
        if sent: c["v11_sent_with_units" if present[u] else "v11_sent_zero_units"] += 1
        bands[("sent " if sent else "skipped ") + ("<20k" if chars < 20000 else "20k-50k" if chars < 50000 else ">=50k")] += 1
    print(json.dumps({"window": [a.start, a.end], "counts": dict(sorted(c.items())), "v11_logged_by_band": dict(sorted(bands.items()))}, indent=1))

if __name__ == "__main__":
    main()
