"""Addendum to see-once.py: close the partition, then reconcile blocks against
the provider's own call count.

The first run reported 684 readable of 1,186 sessions in both sides and listed 0
undated and 0 unreadable, which leaves 502 sessions in no bucket at all. That is
the same shape as the defect the construction probe caught with its
coverage_check: a partition that does not add up hides whichever class fell
through. Here the missing class is a transcript holding no prose turn at all
(queue/tool events only), and it has to be counted, not skipped.

The reconciliation is the independent check on my blocking. provider_telemetry
recorded 495 `session-distill.gemini` calls since 2026-08-09, one per block, with
tokens_in from the provider. If my re-implementation of the blocking is right,
the blocks I compute as VISIBLE for sessions distilled inside that window should
land near 495. If it is far off, every block number above is unreadable -- and
the direction of the miss says which way.
"""
import collections, glob, json, os, re, sqlite3, statistics

DB = "file:/root/.openclaw/workspace/tools/nox-mem/nox-mem.db?mode=ro"
ARCHIVE = "/var/lib/nox-mem/action-archive"
SEE = json.load(open("/root/medicoes/2026-10-26-memory-tax/see-once.json"))
UUID = re.compile(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})")
TELEMETRY_START = "2026-08-09 01:00:21"

con = sqlite3.connect(DB, uri=True)
log = collections.defaultdict(list)
for sk, pa in con.execute("SELECT session_key, processed_at FROM session_distill_log"):
    m = UUID.search(sk or "")
    if m:
        log[m.group(1)].append(pa or "")
raw = {}
for p in glob.glob(os.path.join(ARCHIVE, "*", "*.jsonl")):
    m = UUID.search(os.path.basename(p))
    if m:
        raw[m.group(1)] = p
both = set(log) & set(raw)

rows = {r["uuid"]: r for r in SEE["rows"]}
accounted = set(rows) | {r["uuid"] for r in SEE["undated"]} | {u for u, _ in SEE["unreadable"]}
missing = sorted(both - accounted)
print(f"both {len(both)} · accounted {len(accounted)} · unaccounted {len(missing)}")

# What are they? Count the lines and the event types of a sample, then assert
# the whole class really holds no prose turn.
kinds = collections.Counter()
sizes = []
for u in missing:
    n = 0
    try:
        with open(raw[u], encoding="utf-8", errors="replace") as f:
            for line in f:
                n += 1
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                kinds[o.get("type", "?")] += 1
    except Exception:
        kinds["UNREADABLE"] += 1
    sizes.append((os.path.getsize(raw[u]), n))
print(f"unaccounted: median file {int(statistics.median(s for s, _ in sizes))} B · "
      f"median lines {int(statistics.median(n for _, n in sizes))}")
print("event types across the unaccounted class:")
for k, v in kinds.most_common(8):
    print(f"   {k:24s} {v}")
prose_kinds = sum(v for k, v in kinds.items() if k in ("message", "user", "assistant"))
print(f"-> events of a prose-bearing type: {prose_kinds} "
      f"({'consistent with the class definition' if prose_kinds == 0 else 'NOT ZERO -- the class is mislabelled'})")

print(f"\nPARTITION: {len(rows)} readable + {len(SEE['undated'])} undated + "
      f"{len(SEE['unreadable'])} unreadable + {len(missing)} no-prose = "
      f"{len(rows)+len(SEE['undated'])+len(SEE['unreadable'])+len(missing)} of {len(both)} -> "
      f"{len(rows)+len(SEE['undated'])+len(SEE['unreadable'])+len(missing) == len(both)}")

# ---- reconciliation against the provider's own call count
calls = con.execute(
    "SELECT COUNT(*), CAST(AVG(tokens_in) AS INT) FROM provider_telemetry "
    "WHERE caller='session-distill.gemini' AND timestamp_ms >= "
    "(strftime('%s','2026-08-09 01:00:00')*1000)").fetchone()
inwin = [r for r in rows.values() if r["processed_at"] >= TELEMETRY_START]
mine = sum(r["blocks_visible"] for r in inwin)
print(f"\nRECONCILIATION over the telemetry window ({TELEMETRY_START} ->)")
print(f"  provider calls recorded        : {calls[0]}  (mean tokens_in {calls[1]})")
print(f"  sessions distilled in window   : {len(inwin)} of {len(rows)} readable")
print(f"  blocks I compute as visible    : {mine}")
print(f"  ratio mine/calls               : {mine/calls[0]:.2f}")
# Sessions with <3 messages never reach the LLM at all (session-distill.ts:379),
# so they must be excluded before the counts can be compared.
reach = [r for r in inwin if r["msg_count_log"] >= 3]
mine_reach = sum(r["blocks_visible"] for r in reach)
print(f"  excluding msg_count < 3        : {len(reach)} sessions, {mine_reach} blocks "
      f"· ratio {mine_reach/calls[0]:.2f}")
