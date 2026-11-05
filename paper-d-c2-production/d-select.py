#!/usr/bin/env python3
"""Paper D: select sessions from the transcript archive. Read-only, no LLM, no cost.

Runs on the host that keeps the archive (piped over ssh: `ssh <host> python3 - <args> < d-select.py`).

  python3 - --spent <replay-set.json> --start 2026-08-15 --end 2026-10-29 --n 5 --seed <int>
            [--exclude <file with one uuid per line>] [--min-chars 25000]

Eligible: a session whose LAST event is inside [start, end] (end = freeze date minus 7 days, so the
archive has copied it before the 7-day prune), whose cleaned prose has at least --min-chars, and
that is not one of the 20 sessions spent on 2026-10-26/27 (read from their replay set) nor in
--exclude (the smoke's own sessions, when the main draw runs). The archive can hold the same
session under several directories; the largest copy is kept.

Prints JSON: the eligible count, the seed, and the chosen sessions with path, uuid, last event and
prose size. Prints no transcript text.
"""
import argparse
import glob
import json
import os
import random
import re
import sys

ARCHIVE = "/var/lib/nox-mem/action-archive"
UUID = re.compile(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})")
# envelope cuts, verbatim from audits/2026-10-26-replay-build.py
CUTS = [
    re.compile(r"Conversation info:.*?```json.*?```", re.S),
    re.compile(r"<system-reminder>.*?</system-reminder>", re.S),
    re.compile(r"<command-name>.*?</command-(?:name|message|args)>", re.S),
    re.compile(r"Caveat: The messages below.*?(?=\n\n|\Z)", re.S | re.I),
    re.compile(r"⟦openclaw:ctx⟧"),
    re.compile(r"<local-command-std(?:out|err)>.*?</local-command-std(?:out|err)>", re.S),
]


def turn_text(o):
    t = o.get("type")
    if t not in ("message", "user", "assistant"):
        return None
    msg = o.get("message") or {}
    role = msg.get("role") or (t if t in ("user", "assistant") else o.get("role"))
    c = msg.get("content", o.get("content"))
    if isinstance(c, str):
        blocks = [c]
    elif isinstance(c, list):
        blocks = [b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") in (None, "text")]
    else:
        return None
    s = "\n".join(b for b in blocks if b)
    for rx in CUTS:
        s = rx.sub(" ", s)
    s = re.sub(r"\n{3,}", "\n\n", s).strip()
    return f"{role or 'unknown'}: {s}" if s else None


def scan(path):
    chars, last = 0, ""
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                o = json.loads(line)
            except Exception:
                continue
            ts = o.get("timestamp") or ""
            if isinstance(ts, str) and ts > last:
                last = ts
            s = turn_text(o)
            if s:
                chars += len(s) + 2
    return chars, last[:10]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spent", required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--exclude")
    ap.add_argument("--min-chars", type=int, default=25000)
    a = ap.parse_args()
    spent = {s["uuid"] for s in json.load(open(a.spent))["sessions"]}
    excl = set(open(a.exclude).read().split()) if a.exclude else set()
    best = {}
    for p in glob.glob(os.path.join(ARCHIVE, "*", "*.jsonl")):
        m = UUID.search(os.path.basename(p))
        if not m:
            continue
        u = m.group(1)
        sz = os.path.getsize(p)
        if u not in best or sz > best[u][1]:
            best[u] = (p, sz)
    elig = []
    for u, (p, _) in sorted(best.items()):
        if u in spent or u in excl:
            continue
        chars, last = scan(p)
        if a.start <= last <= a.end and chars >= a.min_chars:
            elig.append({"uuid": u, "path": p, "last_event": last, "prose_chars": chars})
    rng = random.Random(a.seed)
    pick = rng.sample(elig, min(a.n, len(elig)))
    json.dump({"archive_sessions": len(best), "spent_excluded": len(spent & set(best)),
               "eligible": len(elig), "seed": a.seed, "window": [a.start, a.end],
               "min_chars": a.min_chars, "chosen": pick}, sys.stdout, indent=1)
    print()


if __name__ == "__main__":
    main()
