"""Build the replay set. No LLM, no cost, read-only.

Per sampled session: the raw prose (source of the gold raw turns), windows wide
enough to span several of the distiller's 2000-char blocks, and the distilled
chunks the builder actually produced (the memory units).

Why windows of 20k: the distiller cuts the conversation into BLOCK_SIZE = 2000
character blocks with NO overlap (session-distill.ts:375, 402-413), so each LLM
call sees one block and nothing else. A window of 20k spans ten of them, which
is what makes it possible to ask for facts whose evidence crosses a boundary.

Sampling is stratified by how much memory the session produced, because the
median session yields 7 chunks and the top yields 242: a flat sample would be
all small sessions and would say nothing about the large ones.
"""
import collections
import glob
import json
import os
import random
import re
import sqlite3

DB = "file:/root/.openclaw/workspace/tools/nox-mem/nox-mem.db?mode=ro"
ARCHIVE = "/var/lib/nox-mem/action-archive"
OUT = "/root/medicoes/2026-10-26-memory-tax/replay-set.json"
UUID = re.compile(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})")
WINDOW = 20_000
PER_STRATUM = 8
SEED = 20261026

con = sqlite3.connect(DB, uri=True)
built = collections.defaultdict(list)
for sf, cid, txt, cat, imp in con.execute(
        "SELECT source_file, id, chunk_text, memory_type, importance FROM chunks "
        "WHERE source_file LIKE 'sessions/%'"):
    m = UUID.search(sf)
    if m:
        built[m.group(1)].append({"id": cid, "text": txt or "", "type": cat, "importance": imp})
raw = {}
for p in glob.glob(os.path.join(ARCHIVE, "*", "*.jsonl")):
    m = UUID.search(os.path.basename(p))
    if m:
        raw[m.group(1)] = p
both = sorted(set(built) & set(raw))

CUTS = [
    re.compile(r"Conversation info:.*?```json.*?```", re.S),
    re.compile(r"<system-reminder>.*?</system-reminder>", re.S),
    re.compile(r"<command-name>.*?</command-(?:name|message|args)>", re.S),
    re.compile(r"Caveat: The messages below.*?(?=\n\n|\Z)", re.S | re.I),
    re.compile(r"\u29fatos_placeholder"),
    re.compile(r"<local-command-std(?:out|err)>.*?</local-command-std(?:out|err)>", re.S),
]
CUTS[4] = re.compile(r"\u27e6openclaw:ctx\u27e7")

def turn_text(o):
    """Text of one jsonl event under EITHER schema, envelopes removed.

    session-distill.ts:190 accepts event.type of "message" (legacy OpenClaw)
    as well as "user"/"assistant" (Claude CLI). Accepting only the latter lost
    whole legacy transcripts. And envelopes are CUT rather than used to reject
    the turn: the user's real message follows the "Conversation info" block, so
    rejecting on the prefix dropped 315,527 of 361,603 chars in one session.
    """
    t = o.get("type")
    if t not in ("message", "user", "assistant"):
        return None
    msg = o.get("message") or {}
    role = msg.get("role") or (t if t in ("user", "assistant") else o.get("role"))
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
    return f"{role or 'unknown'}: {s}" if s else None

def prose(path):
    out = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                o = json.loads(line)
            except Exception:
                continue
            s = turn_text(o)
            if s:
                out.append(s)
    return out

# ---- stratify by produced memory, sample inside each stratum
STRATA = [("few", 1, 5), ("median", 5, 15), ("many", 15, 60), ("top", 60, 1 << 30)]
rng = random.Random(SEED)
sample, strata_report = [], []
for name, lo, hi in STRATA:
    pool = [u for u in both if lo <= len(built[u]) < hi]
    pick = rng.sample(pool, min(PER_STRATUM, len(pool)))
    strata_report.append({"stratum": name, "pool": len(pool), "picked": len(pick)})
    for u in pick:
        sample.append((name, u))

out = {"seed": SEED, "window_chars": WINDOW, "block_size_of_the_builder": 2000,
       "strata": strata_report, "sessions": []}
for name, u in sample:
    turns = prose(raw[u])
    full = "\n\n".join(turns)
    if len(full) < 3000:          # nothing to ask about
        continue
    # one window from the middle, one from the start: the start carries the
    # task setup, the middle carries the work. Both span >= 10 builder blocks.
    wins = []
    for label, start in (("start", 0), ("middle", max(0, len(full) // 2 - WINDOW // 2))):
        w = full[start:start + WINDOW]
        if len(w) >= 3000:
            wins.append({"label": label, "offset": start, "text": w})
    out["sessions"].append({
        "uuid": u, "stratum": name, "agent": None,
        "prose_chars": len(full), "prose_turns": len(turns),
        "builder_blocks_est": max(1, len(full) // 2000),
        "windows": wins,
        "units": built[u],
        "units_chars": sum(len(c["text"]) for c in built[u])})

os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
print("sessions in set:", len(out["sessions"]))
print("strata:", json.dumps(strata_report, ensure_ascii=False))
print(f"{'stratum':8s} {'uuid':10s} {'prose':>9s} {'turns':>6s} {'blocks':>7s} {'units':>6s} {'unit chars':>11s} {'compr':>7s}")
for s in out["sessions"]:
    print(f"{s['stratum']:8s} {s['uuid'][:8]:10s} {s['prose_chars']:9,d} {s['prose_turns']:6d} "
          f"{s['builder_blocks_est']:7d} {len(s['units']):6d} {s['units_chars']:11,d} "
          f"{s['units_chars']/s['prose_chars']:7.1%}")
ruins = [s["uuid"][:8] for s in out["sessions"] if s["units_chars"] > s["prose_chars"]]
assert not ruins, f"CONTROLE: unidades > prosa em {ruins} -- o extrator perde cru"
print("\ncontrole units<=prose: OK em", len(out["sessions"]), "sessoes")
print("windows total:", sum(len(s["windows"]) for s in out["sessions"]))
print("wrote", OUT, os.path.getsize(OUT), "bytes")
