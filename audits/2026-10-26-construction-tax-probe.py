"""The probe, with the two join defects of the first run fixed.

Defect 1 -- the log is keyed by (session_key) and session_key is <agent>:<uuid>,
so the SAME transcript appears under several agents: 2498 rows for 1931
distinct uuids, 567 collisions. Keying a dict by uuid let the last row read win,
which classified a session arbitrarily whenever two agents disagreed on it.
Fixed by aggregating per uuid: a session counts as having produced memory if
ANY agent's run produced a chunk from it.

Defect 2 -- the raw side spans 11 directories, not the 7 that produced chunks,
and the test "name contains agents-" is wrong: -root--openclaw-workspace has no
such substring and is the main agent's own cwd (its 59 built sessions equal
built_by_agent[main] exactly). The directories genuinely outside the
distiller's reach are the four with zero log rows AND zero built chunks.
"""
import collections
import glob
import json
import os
import re
import sqlite3
import statistics

DB = "file:/root/.openclaw/workspace/tools/nox-mem/nox-mem.db?mode=ro"
ARCHIVE = "/var/lib/nox-mem/action-archive"
OUT = "/root/medicoes/2026-10-26-memory-tax/sondagem-v2.json"
UUID = re.compile(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})")

con = sqlite3.connect(DB, uri=True)
r = {"snapshot_utc": con.execute("SELECT datetime('now')").fetchone()[0]}

# ------------------------------------------------------------------ built
built_chunks, built_agent = collections.defaultdict(int), {}
for sf, n in con.execute(
        "SELECT source_file, COUNT(*) FROM chunks WHERE source_file LIKE 'sessions/%' GROUP BY source_file"):
    m = UUID.search(sf)
    if m:
        built_chunks[m.group(1)] += n
        built_agent[m.group(1)] = sf.split("/")[1]
r["built_chunks_total"] = sum(built_chunks.values())
r["built_uuids"] = len(built_chunks)

# ------------------------------------------------------------------- log
log = con.execute(
    "SELECT session_key, agent, chunks_extracted, message_count FROM session_distill_log").fetchall()
r["log_rows"] = len(log)
per_uuid = collections.defaultdict(list)
for sk, ag, ce, mc in log:
    m = UUID.search(sk)
    if m:
        per_uuid[m.group(1)].append((ag, ce, mc))
r["log_uuids"] = len(per_uuid)
r["log_collisions"] = len(log) - len(per_uuid)
r["uuids_logged_under_several_agents"] = sum(1 for v in per_uuid.values() if len(v) > 1)
# a collision where the agents DISAGREE on the outcome is the case the broken
# key silently decided: one agent got chunks, another got zero.
r["collisions_with_disagreement"] = sum(
    1 for v in per_uuid.values() if len(v) > 1 and len({ce > 0 for _, ce, _ in v}) > 1)

best = {u: max(ce for _, ce, _ in v) for u, v in per_uuid.items()}
maxmsg = {u: max(mc for _, _, mc in v) for u, v in per_uuid.items()}
r["log_uuids_zero"] = sum(1 for u in best if best[u] == 0)
MB = [("< 3 msgs", 0, 3), ("3-19", 3, 20), ("20-99", 20, 100), ("100+", 100, 1 << 60)]
r["zero_uuids_by_message_count"] = [
    {"bucket": lb, "n": sum(1 for u in best if best[u] == 0 and lo <= maxmsg[u] < hi)}
    for lb, lo, hi in MB]
nontrivial = [u for u in best if best[u] == 0 and maxmsg[u] >= 3]
r["zero_nontrivial_uuids"] = len(nontrivial)
r["zero_nontrivial_max_messages"] = max((maxmsg[u] for u in nontrivial), default=None)
r["zero_nontrivial_by_agent"] = dict(sorted(collections.Counter(
    per_uuid[u][0][0] for u in nontrivial).items(), key=lambda kv: -kv[1]))

# -------------------------------------------------------------------- raw
by_dir = collections.defaultdict(dict)
for p in glob.glob(os.path.join(ARCHIVE, "*", "*.jsonl")):
    m = UUID.search(os.path.basename(p))
    if m:
        by_dir[os.path.basename(os.path.dirname(p))][m.group(1)] = os.path.getsize(p)
raw = {u: s for d in by_dir for u, s in by_dir[d].items()}
r["archive_uuids"] = len(raw)
r["archive_bytes"] = sum(raw.values())

# A directory is in the distiller's reach if it ever produced a log row or a
# chunk. Judging by the name would have put the main agent's own cwd outside.
reach = {d for d, us in by_dir.items()
         if any(u in per_uuid or u in built_chunks for u in us)}
r["dirs_total"] = len(by_dir)
r["dirs_in_reach"] = sorted(reach)
r["dirs_out_of_reach"] = {d: len(by_dir[d]) for d in sorted(set(by_dir) - reach)}
out_of_reach = {u for d in set(by_dir) - reach for u in by_dir[d]}
r["out_of_reach_transcripts"] = len(out_of_reach)
r["out_of_reach_ever_logged_or_built"] = sum(
    1 for u in out_of_reach if u in per_uuid or u in built_chunks)

in_reach = {u: s for u, s in raw.items() if u not in out_of_reach}
r["in_reach_transcripts"] = len(in_reach)

# ------------------------------------------------------- the three outcomes
never = [u for u in in_reach if u not in per_uuid]
zeroed = [u for u in in_reach if u in per_uuid and best[u] == 0]
yielded = [u for u in in_reach if u in per_uuid and best[u] > 0]
med = lambda us: int(statistics.median([in_reach[u] for u in us])) if us else None
for name, us in (("never_reached_the_log", never), ("logged_and_yielded_nothing", zeroed),
                 ("logged_and_produced_chunks", yielded)):
    r[name] = {"n": len(us), "median_bytes": med(us),
               "over_500kb": sum(1 for u in us if in_reach[u] > 500_000),
               "over_1mb": sum(1 for u in us if in_reach[u] > 1_000_000),
               "max_mb": round(max((in_reach[u] for u in us), default=0) / 1e6, 2)}
r["coverage_check"] = len(never) + len(zeroed) + len(yielded) == len(in_reach)

# the measurable window for the QA replay: both sides present
both = sorted(set(built_chunks) & set(raw))
r["both_sides"] = len(both)
r["both_sides_chunks"] = sum(built_chunks[u] for u in both)
r["both_sides_chunk_share"] = round(sum(built_chunks[u] for u in both) / max(r["built_chunks_total"], 1), 4)
r["built_without_raw"] = len(set(built_chunks) - set(raw))
# control: a session with chunks must also be a session the log says yielded.
r["built_but_log_says_zero"] = sorted(u for u in both if u in best and best[u] == 0)[:5]
r["built_but_log_says_zero_n"] = sum(1 for u in both if u in best and best[u] == 0)

# ------------------------------------------------ per directory, the whole shape
r["by_directory"] = []
for d in sorted(by_dir, key=lambda d: -len(by_dir[d])):
    us = by_dir[d]
    r["by_directory"].append({
        "dir": d, "files": len(us),
        "never_logged": sum(1 for u in us if u not in per_uuid),
        "logged_zero": sum(1 for u in us if u in per_uuid and best[u] == 0),
        "produced": sum(1 for u in us if u in per_uuid and best[u] > 0),
        "built": sum(1 for u in us if u in built_chunks),
        "over_1mb": sum(1 for s in us.values() if s > 1_000_000)})

# --------------------------------------------------- does size predict survival
BUCKETS = [("0-50 KB", 0, 50_000), ("50-200 KB", 50_000, 200_000),
           ("200 KB-1 MB", 200_000, 1_000_000), ("1-5 MB", 1_000_000, 5_000_000),
           ("> 5 MB", 5_000_000, 1 << 60)]
r["survival_by_size"] = []
for label, lo, hi in BUCKETS:
    pop = [u for u in in_reach if lo <= in_reach[u] < hi]
    r["survival_by_size"].append({
        "bucket": label, "n": len(pop),
        "survived": sum(1 for u in pop if u in built_chunks),
        "rate": round(sum(1 for u in pop if u in built_chunks) / len(pop), 4) if pop else None})

os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(r, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(json.dumps(r, ensure_ascii=False, indent=2))
print("\nwrote", OUT)
