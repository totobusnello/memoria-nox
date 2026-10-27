"""Separate the 371 never-logged transcripts without touching the live DB.

The planned route was to run isNoise() against a copy, because isNoise writes
to noise_prototypes. It is not needed to separate the two causes. The code path
is: if the noise filter empties the conversation, session-distill.ts:397 does
`continue` WITHOUT writing a log row; otherwise a row is always written. So a
transcript holding real user/assistant prose cannot have been emptied by the
filter -- if it had been seen, there would be a row. No row + real prose =
never reached, which is the operational component (window x prune x
maxSessionsPerRun), not a content decision.

Counting the prose is therefore the whole test, and it is free: read the
jsonl, keep only role user/assistant text blocks, drop tool results and the
reminder envelopes the filter also drops.
"""
import collections
import glob
import json
import os
import re
import statistics

ARCHIVE = "/var/lib/nox-mem/action-archive"
UUID = re.compile(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})")
import sqlite3
con = sqlite3.connect("file:/root/.openclaw/workspace/tools/nox-mem/nox-mem.db?mode=ro", uri=True)
logged = set()
for (sk,) in con.execute("SELECT session_key FROM session_distill_log"):
    m = UUID.search(sk)
    if m:
        logged.add(m.group(1))
built = set()
for (sf,) in con.execute("SELECT DISTINCT source_file FROM chunks WHERE source_file LIKE 'sessions/%'"):
    m = UUID.search(sf)
    if m:
        built.add(m.group(1))

by_dir = collections.defaultdict(dict)
for p in glob.glob(os.path.join(ARCHIVE, "*", "*.jsonl")):
    m = UUID.search(os.path.basename(p))
    if m:
        by_dir[os.path.basename(os.path.dirname(p))][m.group(1)] = p
reach = {d for d, us in by_dir.items() if any(u in logged or u in built for u in us)}
never = {u: p for d in reach for u, p in by_dir[d].items() if u not in logged}
print("never reached the log, inside reachable directories:", len(never))

NOISE = re.compile(r"<system-reminder|<command-name>|caveat: the messages below|"
                   r"^\s*(ok|sim|yes|continue?)\s*[.!]?\s*$", re.I)

def prose(path):
    """Characters of real user/assistant prose, tool output and envelopes out."""
    chars = turns = 0
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                o = json.loads(line)
            except Exception:
                continue
            msg = o.get("message") or {}
            role = msg.get("role")
            if role not in ("user", "assistant"):
                continue
            c = msg.get("content")
            if isinstance(c, str):
                blocks = [c]
            elif isinstance(c, list):
                blocks = [b.get("text", "") for b in c
                          if isinstance(b, dict) and b.get("type") == "text"]
            else:
                continue
            txt = "\n".join(b for b in blocks if b and not NOISE.search(b)).strip()
            if txt:
                chars += len(txt)
                turns += 1
    return chars, turns

res = {}
for u, p in never.items():
    res[u] = (os.path.getsize(p), *prose(p))

big = sorted(((s, c, t, u) for u, (s, c, t) in res.items() if s > 1_000_000), reverse=True)
print(f"\n=== the 16 over 1 MB: do they hold real prose? ===")
print(f"{'uuid':10s} {'file MB':>8s} {'prose chars':>12s} {'turns':>6s} {'prose/file':>11s}")
for s, c, t, u in big:
    print(f"{u[:8]:10s} {s/1e6:8.2f} {c:12d} {t:6d} {c/s:11.3%}")

SUB = 2000  # 2 kB of prose is roughly a page: well above anything the filter empties
buckets = [("0-50 KB", 0, 50_000), ("50-200 KB", 50_000, 200_000),
           ("200 KB-1 MB", 200_000, 1_000_000), ("> 1 MB", 1_000_000, 1 << 60)]
print(f"\n=== the whole 371, by file size ===")
print(f"{'bucket':14s} {'n':>5s} {'with >2kB prose':>16s} {'median prose':>13s}")
for lb, lo, hi in buckets:
    pop = [u for u in res if lo <= res[u][0] < hi]
    sub = [u for u in pop if res[u][1] >= SUB]
    m = int(statistics.median([res[u][1] for u in pop])) if pop else 0
    print(f"{lb:14s} {len(pop):5d} {len(sub):16d} {m:13d}")

subst = [u for u in res if res[u][1] >= SUB]
print(f"\nnever logged WITH substantive prose (>= {SUB} chars): {len(subst)} of {len(res)}"
      f" = {len(subst)/len(res):.1%}")
print("their total prose:", f"{sum(res[u][1] for u in subst):,}", "chars")
print("their file bytes: ", f"{sum(res[u][0] for u in subst):,}")
print("\nby directory:")
d_of = {u: d for d in reach for u in by_dir[d]}
for d, n in collections.Counter(d_of[u] for u in subst).most_common():
    tot = sum(1 for u in never if d_of[u] == d)
    print(f"  {d:48s} {n:4d} of {tot:4d} never-logged")
json.dump({u: {"bytes": res[u][0], "prose": res[u][1], "turns": res[u][2]} for u in res},
          open("/root/medicoes/2026-10-26-memory-tax/never-logged-371.json", "w"), indent=1)
