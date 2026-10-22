#!/usr/bin/env python3
"""Item 7a (2026-10-14): do agents use the brief that reaches their system prompt?

Unit: one assistant message. Exposed arm: items of the brief that was in the
prompt at that moment (latest brief generated for the agent before the message).
Control arms: items that were in this agent's brief at another moment of the
window but not at this one; split into 'past' (left before) and 'future' (enter
later), because the conversation itself can push an item into a later brief.

Detectors: strict (one-liner >= 25 chars, or a distinctive file stem, verbatim)
and fuzzy (>= 60% of the item's distinctive tokens, min 4). Distinctive = token
>= 4 chars present in < 5% of the assistant messages.

Read-only: sqlite opened with mode=ro; transcripts only read. Prints aggregates
and a small sample of hits for manual precision checking.

2026-10-22 fix. Transcripts live under TWO roots and this script read one. The
same hole was found in the R1 audit on 2026-10-21, where reading a single root
covered 345 of 523 messages (66%) and `cipher` went from 3 to 42; the numbers
published from this script on 2026-10-14 are understated by that mechanism.
Both roots are read now, deduped by `(agent, message id)` because a session can
appear under both. Set PROJ_ROOTS to re-run the old single-root configuration
and attribute the delta to the roots alone.
"""
import glob, json, os, re, sqlite3, sys, random
from bisect import bisect_right
from collections import defaultdict

DB = "/root/.openclaw/workspace/tools/nox-mem/nox-mem.db"
PROJ_ROOTS = os.environ.get(
    "PROJ_ROOTS", "/root/.claude-nuvini-team/projects:/root/.claude/projects"
).split(":")
START, END = "2026-09-21 00:00:00", "2026-10-15 00:00:00"
ONE_LINER_MAX = int(os.environ.get("ONE_LINER_MAX", "140"))  # src/api/brief.ts
# transcript dir suffix -> brief_log.agent (main uses agent=nox in the cron)
DIRS = {"": "nox", "-agents-boris": "boris", "-agents-forge": "forge",
        "-agents-cipher": "cipher", "-agents-nox": "nox", "-agents-atlas": "atlas", "-agents-lex": "lex"}
TOK = re.compile(r"[^\w.]+", re.U)

def toks(s):
    return {t for t in TOK.split(s.lower()) if len(t) >= 4}

def one_liner(text):
    for raw in (text or "").split("\n"):
        line = re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", raw)).strip()
        if not line or line in ("---", "```"):
            continue
        c = re.sub(r"^#{1,6}\s+", "", line)
        c = re.sub(r"^[-*>]\s+", "", c).replace("**", "").strip()
        if c:
            return c[: ONE_LINER_MAX - 1] if len(c) > ONE_LINER_MAX else c
    return ""

def stem(sf):
    b = (sf or "").split("/")[-1]
    return re.sub(r"\.(md|txt|json|jsonl)$", "", b, flags=re.I)

def norm_ts(ts):  # transcript ISO "2026-10-01T12:00:00.000Z" -> sqlite "2026-10-01 12:00:00"
    return ts[:19].replace("T", " ")

# ── assistant messages ────────────────────────────────────────────────────────
# Keyed by (agent, message id) across BOTH roots: a session present in each
# would otherwise be counted twice. The fallback key uses the basename, not the
# full path, for the same reason.
by_id = {}
seen_dirs = []
for PROJ in PROJ_ROOTS:
  for suffix, agent in DIRS.items():
    d = f"{PROJ}/-root--openclaw-workspace{suffix}"
    if not os.path.isdir(d):
        continue
    seen_dirs.append(d)
    for f in glob.glob(f"{d}/**/*.jsonl", recursive=True):
        if os.path.getmtime(f) < 1758412800:  # 2026-09-21
            continue
        with open(f, errors="replace") as fh:
            for line in fh:
                if '"type":"assistant"' not in line:
                    continue
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                ts = o.get("timestamp")
                m = o.get("message") or {}
                if not ts or not (START <= norm_ts(ts) < END):
                    continue
                parts = [c.get("text", "") for c in m.get("content", []) if isinstance(c, dict) and c.get("type") == "text"]
                if not parts:
                    continue
                key = (agent, m.get("id") or f"{os.path.basename(f)}:{ts}")
                prev = by_id.get(key)
                txt = "\n".join(parts)
                by_id[key] = (agent, norm_ts(ts), (prev[2] + "\n" + txt) if prev else txt)
msgs = list(by_id.values())
print(f"transcript roots: {PROJ_ROOTS}")
print(f"transcript dirs read: {len(seen_dirs)}")
print(f"assistant messages with text in window: {len(msgs)}")
by_agent_n = defaultdict(int)
for a, _, _ in msgs:
    by_agent_n[a] += 1
print("by brief agent:", dict(by_agent_n))

# document frequency over messages -> distinctive tokens
df = defaultdict(int)
msg_toks = []
for _, _, t in msgs:
    s = toks(t)
    msg_toks.append(s)
    for x in s:
        df[x] += 1
N = max(1, len(msgs))
common = {t for t, c in df.items() if c / N >= 0.05}

# ── briefs ────────────────────────────────────────────────────────────────────
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
rows = con.execute(
    "SELECT agent, brief_id, MIN(served_at), group_concat(chunk_id) FROM brief_log "
    "WHERE agent IS NOT NULL AND brief_id IS NOT NULL AND served_at >= ? AND served_at < ? "
    "GROUP BY agent, brief_id ORDER BY 3", (START, END)).fetchall()
briefs = defaultdict(list)  # agent -> [(ts, frozenset(ids))]
for agent, _bid, ts, ids in rows:
    briefs[agent].append((ts, frozenset(int(x) for x in ids.split(","))))
for a in briefs:
    briefs[a].sort()
print("briefs per agent:", {a: len(v) for a, v in briefs.items()})

all_ids = set().union(*[s for v in briefs.values() for _, s in v]) if briefs else set()
info = {}
q = "SELECT id, source_file, chunk_text FROM chunks WHERE id IN (%s)"
ids = list(all_ids)
for i in range(0, len(ids), 500):
    part = ids[i:i + 500]
    for cid, sf, txt in con.execute(q % ",".join("?" * len(part)), part):
        ol = one_liner(txt)
        st = stem(sf)
        sig = (toks(st) | toks(ol)) - common
        info[cid] = {"stem": st, "ol": ol, "sig": sig, "sf": sf}
print(f"distinct brief items: {len(all_ids)}, resolvable in chunks: {len(info)}")

# stems shared by many items (MEMORY, lessons, decisions...) are not distinctive
stem_count = defaultdict(int)
for v in info.values():
    stem_count[v["stem"].lower()] += 1

# v2: a stem counts only if distinctive (has '-', '_' or a digit; one dictionary
# word like EVOLUTION matched "Marginal Revolution" as a substring in v1) and only
# on word boundaries.
def stem_ok(s):
    return len(s) >= 8 and stem_count[s] <= 2 and re.search(r"[-_0-9]", s) is not None

def strict_hit(cid, text_lower):
    v = info.get(cid)
    if not v:
        return False
    ol = v["ol"].lower().rstrip("…")
    if len(ol) >= 25 and ol in text_lower:
        return True
    s = v["stem"].lower()
    return stem_ok(s) and re.search(r"(?<![\w])" + re.escape(s) + r"(?![\w])", text_lower) is not None

def fuzzy_hit(cid, mtoks):
    v = info.get(cid)
    if not v or len(v["sig"]) < 4:
        return False
    return len(v["sig"] & mtoks) / len(v["sig"]) >= 0.6

# ── pairs ─────────────────────────────────────────────────────────────────────
res = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))  # agent -> arm -> [pairs, strict, fuzzy]
samples = defaultdict(list)
for (agent, ts, text), mt in zip(msgs, msg_toks):
    bl = briefs.get(agent)
    if not bl:
        continue
    times = [b[0] for b in bl]
    k = bisect_right(times, ts) - 1
    if k < 0:
        continue
    cur = bl[k][1]
    past = set().union(*[s for _, s in bl[:k]]) - cur if k > 0 else set()
    future = set().union(*[s for _, s in bl[k + 1:]]) - cur - past if k + 1 < len(bl) else set()
    tl = text.lower()
    cur, past, future = (x & info.keys() for x in (cur, past, future))
    for arm, ids_ in (("exposed", cur), ("ctrl_past", past), ("ctrl_future", future)):
        r = res[agent][arm]
        for cid in ids_:
            r[0] += 1
            s, f = strict_hit(cid, tl), fuzzy_hit(cid, mt)
            r[1] += s
            r[2] += f
            if (s or f) and len(samples[arm]) < 400:
                samples[arm].append((agent, ts, cid, "S" if s else "F"))

def fmt(r):
    p, s, f = r
    return f"pairs={p:>8}  strict={s:>5} ({(s / p * 1e4 if p else 0):6.2f}/10k)  fuzzy={f:>5} ({(f / p * 1e4 if p else 0):6.2f}/10k)"

tot = defaultdict(lambda: [0, 0, 0])
for agent in sorted(res):
    print(f"\n== {agent}")
    for arm in ("exposed", "ctrl_past", "ctrl_future"):
        r = res[agent][arm]
        print(f"  {arm:<12} {fmt(r)}")
        for i in range(3):
            tot[arm][i] += r[i]
print("\n== ALL")
for arm in ("exposed", "ctrl_past", "ctrl_future"):
    print(f"  {arm:<12} {fmt(tot[arm])}")

random.seed(14)
print("\n== sample hits (exposed) for manual precision check")
for agent, ts, cid, kind in random.sample(samples["exposed"], min(12, len(samples["exposed"]))):
    v = info[cid]
    print(f"  {kind} {agent} {ts} chk {cid} stem={v['stem'][:40]!r} ol={v['ol'][:70]!r}")
print("\n== sample hits (ctrl_past)")
for agent, ts, cid, kind in random.sample(samples["ctrl_past"], min(6, len(samples["ctrl_past"]))) + [("--future--", "", None, "")] + random.sample(samples["ctrl_future"], min(6, len(samples["ctrl_future"]))):
    if cid is None:
        print("  == sample hits (ctrl_future)"); continue
    v = info[cid]
    print(f"  {kind} {agent} {ts} chk {cid} stem={v['stem'][:40]!r} ol={v['ol'][:70]!r}")
