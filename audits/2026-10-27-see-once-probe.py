"""Is the construction tax a see-once tax? Read-only, no LLM, no cost.

Why this exists. The 23x spread in chunks-per-block reported on 2026-10-26 was
computed by dividing a transcript's FINAL prose length by BLOCK_SIZE. Three
measurements taken since say that divisor describes a session the distiller
never saw:

  - provider_telemetry over `session-distill.gemini`: 495 calls, 0 failures,
    tokens_in median under 1k and max 19,953, tokens_src='api' on 100% of them.
    So the LLM did not fail silently (the original hypothesis) and the blocks it
    received really are ~2000 chars. 495 blocks is ~1M characters in 79 days.
  - the noise filter cannot be the mechanism: noise-filter.ts rule 2 returns
    false for any text >= 500 chars, and the 240 learned prototypes hold 4 hits
    in total.
  - session-distill.ts:141-144 skips any session already in the log:
    `SELECT id FROM session_distill_log WHERE session_key = ?` -> continue.

That last one is the candidate. A live session is distilled the first time the
cron reaches it, with whatever it held at that instant, and is never revisited
however much it grows afterwards. The archive keeps the FINAL transcript. So
"chunks per block" computed over the final length measures the fraction of the
session the builder was shown, not the productivity of the LLM.

The test. For each session with both a log row and a raw transcript, split the
prose by turn timestamp at processed_at: what existed when it was distilled
against what exists now. The hypothesis predicts a low visible fraction on the
large sessions. It can fail: if the fraction is ~100% everywhere, the see-once
rule costs nothing and the 23x spread needs another explanation.

Controls, all of which can fail:
  1. timestamp coverage per session -- a session whose turns are mostly undated
     cannot be split, and is reported apart instead of counted as loss.
  2. sessions whose LAST turn precedes processed_at must come out at 100%.
     Anything less is a bug in my date handling, so it asserts.
  3. visible chars <= total chars, always.
  4. processed_at is taken as the MAX across agents (the composite key
     <agent>:<uuid> means one uuid can hold several rows -- the defect that
     fabricated 114 losses on 2026-10-26). MAX is the choice that flatters the
     system: it credits the builder with the latest look any agent took.
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
OUT = "/root/medicoes/2026-10-26-memory-tax/see-once.json"
UUID = re.compile(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})")
BLOCK_SIZE = 2000

CUTS = [
    re.compile(r"Conversation info:.*?```json.*?```", re.S),
    re.compile(r"<system-reminder>.*?</system-reminder>", re.S),
    re.compile(r"<command-name>.*?</command-(?:name|message|args)>", re.S),
    re.compile(r"Caveat: The messages below.*?(?=\n\n|\Z)", re.S | re.I),
    re.compile(r"⟦openclaw:ctx⟧"),
    re.compile(r"<local-command-std(?:out|err)>.*?</local-command-std(?:out|err)>", re.S),
]

def turn(o):
    """(timestamp, text) for one event under EITHER schema, envelopes cut.

    Verbatim from 2026-10-26-replay-build.py, plus the timestamp. Envelopes are
    CUT, not used to reject the turn: the user's real message follows the
    "Conversation info" block.
    """
    t = o.get("type")
    if t not in ("message", "user", "assistant"):
        return None
    msg = o.get("message") or {}
    role = msg.get("role") or (t if t in ("user", "assistant") else o.get("role"))
    if role not in ("user", "assistant"):
        return None
    c = msg.get("content", o.get("content"))
    if isinstance(c, str):
        blocks = [c]
    elif isinstance(c, list):
        blocks = [b.get("text", "") for b in c
                  if isinstance(b, dict) and b.get("type") in (None, "text")]
    else:
        return None
    s = "\n".join(b for b in blocks if b)
    for rx in CUTS:
        s = rx.sub(" ", s)
    s = re.sub(r"\n{3,}", "\n\n", s).strip()
    if not s:
        return None
    # The distiller's own heartbeat filter, session-distill.ts:214-222.
    if (s.startswith("[cron:") or s.startswith("HEARTBEAT") or len(s) < 5
            or s.startswith("The conversation history before this point")
            or re.match(r"^heartbeat[_ ]ok\b", s, re.I)):
        return None
    ts = o.get("timestamp") or ""
    # '2026-10-04T06:22:12.998Z' -> '2026-10-04 06:22:12', comparable as a
    # string with the log's datetime('now') format. Both are UTC.
    norm = ts.replace("T", " ")[:19] if len(ts) >= 19 else ""
    return (norm, f"{role}: {s}")

def blocks_of(lines):
    """The distiller's exact blocking, session-distill.ts:402-413.

    Not chars // BLOCK_SIZE: the loop only breaks AFTER exceeding the limit and
    never splits a line, so one long turn is one oversized block. Running the
    real algorithm is what keeps this from repeating the error it investigates.
    """
    out, cur = [], ""
    for line in lines:
        if len(cur) + len(line) > BLOCK_SIZE and cur:
            out.append(cur.strip())
            cur = line + "\n"
        else:
            cur += line + "\n"
    if cur.strip():
        out.append(cur.strip())
    return out

con = sqlite3.connect(DB, uri=True)

log = collections.defaultdict(list)
for sk, ag, pa, ce, mc in con.execute(
        "SELECT session_key, agent, processed_at, chunks_extracted, message_count "
        "FROM session_distill_log"):
    m = UUID.search(sk or "")
    if m:
        log[m.group(1)].append((ag, pa or "", ce or 0, mc or 0))

built = collections.Counter()
for sf, in con.execute("SELECT source_file FROM chunks WHERE source_file LIKE 'sessions/%'"):
    m = UUID.search(sf)
    if m:
        built[m.group(1)] += 1

raw = {}
for p in glob.glob(os.path.join(ARCHIVE, "*", "*.jsonl")):
    m = UUID.search(os.path.basename(p))
    if m:
        raw[m.group(1)] = p

pop = sorted(set(log) & set(raw))
print(f"log uuids {len(log)} · archive {len(raw)} · both {len(pop)}", flush=True)

rows, undated, bad = [], [], []
for i, u in enumerate(pop, 1):
    pa = max(p for _, p, _, _ in log[u])          # control 4: flatters the system
    ce = max(c for _, _, c, _ in log[u])
    turns = []
    try:
        with open(raw[u], encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                t = turn(o)
                if t:
                    turns.append(t)
    except Exception as e:
        bad.append((u, str(e)[:80]))
        continue
    if not turns:
        continue
    dated = [t for t in turns if t[0]]
    cov = len(dated) / len(turns)
    total_chars = sum(len(t[1]) for t in turns)
    if cov < 0.90:
        undated.append({"uuid": u, "coverage": round(cov, 3), "turns": len(turns),
                        "total_chars": total_chars})
        continue
    visible = [t[1] for t in dated if t[0] <= pa]
    vis_chars = sum(len(s) for s in visible)
    assert vis_chars <= total_chars, f"control 3 broken on {u}"
    last_ts = max(t[0] for t in dated)
    ended_before = last_ts <= pa
    frac = vis_chars / total_chars if total_chars else 0.0
    rows.append({
        "uuid": u, "processed_at": pa, "last_turn": last_ts,
        "ended_before_processing": ended_before,
        "turns": len(turns), "ts_coverage": round(cov, 3),
        "total_chars": total_chars, "visible_chars": vis_chars,
        "visible_frac": round(frac, 4),
        "blocks_visible": len(blocks_of(visible)),
        "blocks_final": len(blocks_of([t[1] for t in turns])),
        "chunks_log": ce, "chunks_now": built.get(u, 0),
        "msg_count_log": max(m for _, _, _, m in log[u]),
    })
    if i % 200 == 0:
        print(f"  {i}/{len(pop)}", flush=True)

# ---- control 2: a session that ENDED before it was distilled must be 100%
viol = [r for r in rows
        if r["ended_before_processing"] and r["visible_frac"] < 0.999]
print(f"\ncontrol 2 · ended-before-processing: {sum(1 for r in rows if r['ended_before_processing'])} "
      f"sessions · violations {len(viol)}")
for r in viol[:5]:
    print(f"   VIOLATION {r['uuid'][:8]} frac={r['visible_frac']} "
          f"pa={r['processed_at']} last={r['last_turn']}")
assert not viol, "control 2 failed: my date handling is wrong, no number below is readable"

json.dump({"rows": rows, "undated": undated, "unreadable": bad},
          open(OUT, "w"), ensure_ascii=False)

grew = [r for r in rows if not r["ended_before_processing"]]
print(f"\nreadable {len(rows)} · undated (<90% coverage) {len(undated)} · unreadable {len(bad)}")
print(f"still growing when distilled: {len(grew)} = {len(grew)/len(rows)*100:.1f}%")

fr = sorted(r["visible_frac"] for r in rows)
print(f"\nvisible fraction over all {len(rows)}: median {statistics.median(fr):.3f} · "
      f"mean {statistics.mean(fr):.3f} · <50% in {sum(1 for x in fr if x < 0.5)} · "
      f"<10% in {sum(1 for x in fr if x < 0.1)}")

print("\nby FINAL transcript prose size:")
BANDS = [("a <10k", 0, 10_000), ("b 10-50k", 10_000, 50_000),
         ("c 50-200k", 50_000, 200_000), ("d 200k-1M", 200_000, 1_000_000),
         ("e >1M", 1_000_000, 1 << 40)]
print(f"{'band':11s} {'n':>4s} {'med frac':>9s} {'med total':>10s} {'med vis':>9s} "
      f"{'chunks/blk vis':>15s} {'chunks/blk final':>17s}")
for name, lo, hi in BANDS:
    g = [r for r in rows if lo <= r["total_chars"] < hi]
    if not g:
        continue
    pv = [r["chunks_now"] / r["blocks_visible"] for r in g if r["blocks_visible"]]
    pf = [r["chunks_now"] / r["blocks_final"] for r in g if r["blocks_final"]]
    print(f"{name:11s} {len(g):4d} {statistics.median(r['visible_frac'] for r in g):9.3f} "
          f"{int(statistics.median(r['total_chars'] for r in g)):10d} "
          f"{int(statistics.median(r['visible_chars'] for r in g)):9d} "
          f"{statistics.median(pv) if pv else 0:15.3f} "
          f"{statistics.median(pf) if pf else 0:17.3f}")

print("\nthe two sessions that produced the 23x claim:")
for u in ("9c75f331", "a35348df"):
    for r in rows:
        if r["uuid"].startswith(u):
            print(f"  {u} total={r['total_chars']} visible={r['visible_chars']} "
                  f"frac={r['visible_frac']:.4f} blocks_final={r['blocks_final']} "
                  f"blocks_visible={r['blocks_visible']} chunks={r['chunks_now']} "
                  f"-> per final block {r['chunks_now']/max(r['blocks_final'],1):.3f} "
                  f"· per VISIBLE block {r['chunks_now']/max(r['blocks_visible'],1):.3f}")

print("\nspread of chunks-per-block, both denominators (sessions with chunks>0):")
g = [r for r in rows if r["chunks_now"] > 0 and r["blocks_visible"] and r["blocks_final"]]
for lab, key in (("final  ", "blocks_final"), ("visible", "blocks_visible")):
    v = sorted(r["chunks_now"] / r[key] for r in g)
    print(f"  {lab}: n={len(v)} p10={v[len(v)//10]:.3f} median={statistics.median(v):.3f} "
          f"p90={v[len(v)*9//10]:.3f} spread p90/p10={v[len(v)*9//10]/max(v[len(v)//10],1e-9):.1f}x")
