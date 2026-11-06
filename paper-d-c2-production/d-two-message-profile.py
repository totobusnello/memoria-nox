#!/usr/bin/env python3
"""Paper D follow-up (read-only, no LLM): the sessions production logged with exactly 2 messages
(skipped by its rule of fewer than 3) whose last event is in [2026-09-20, 2026-10-30] and which have
at least 3,000 characters under production's input rule. Splits their characters between the user
turn and the assistant turn. Runs on the archive host with d-select.py at
/var/tmp/paper-d-census/dsel.py. Counts only."""
import collections, glob, json, os, sqlite3, statistics
exec(open("/var/tmp/paper-d-census/dsel.py").read().split("def main():")[0])  # noqa: S102
DROP = ("[cron:", "HEARTBEAT", "The conversation history before this point")
con = sqlite3.connect("file:/root/.openclaw/workspace/tools/nox-mem/nox-mem.db?mode=ro", uri=True)
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
uc, ac, starts, dirs = [], [], collections.Counter(), collections.Counter()
for u, (p, _) in best.items():
    if logged.get(u, -1) != 2: continue
    user = asst = 0; last = ""; first = None
    for line in open(p, encoding="utf-8", errors="replace"):
        try: o = json.loads(line)
        except Exception: continue
        ts = o.get("timestamp") or ""
        if isinstance(ts, str) and ts > last: last = ts
        s = turn_text(o)
        if not s: continue
        role, _, body = s.partition(": ")
        if body.lstrip().startswith(DROP): continue
        if role == "user":
            user += len(body)
            if first is None: first = body.lstrip()[:14]
        else: asst += len(body)
    if not ("2026-09-20" <= last[:10] <= "2026-10-30") or user + asst < 3000: continue
    uc.append(user); ac.append(asst); dirs[os.path.basename(os.path.dirname(p))] += 1
    starts["starts_with_bracket" if (first or "").startswith("[") else "other"] += 1
print({"sessions": len(uc), "user_chars_median": statistics.median(uc), "assistant_chars_median": statistics.median(ac),
       "user_share_of_chars": round(sum(uc) / (sum(uc) + sum(ac)), 3), "first_user_text": dict(starts), "dirs": dict(dirs)})
