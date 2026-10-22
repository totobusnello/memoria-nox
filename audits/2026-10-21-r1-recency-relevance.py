#!/usr/bin/env python3
"""Item 7 / R1 (2026-10-21): would a recency-ordered brief be more relevant than
the one actually served?

R1 has run in shadow since 2026-10-14 22:13 UTC: on every brief the server also
computes what a recency-ordered brief WOULD have contained, and logs both id
lists side by side without changing what the agent receives.

Unit: one assistant message. For each message we take the last shadow record of
that agent before it, which gives two arms measured on the SAME message:

  served_now   the 10 items that were actually in the prompt (causal exposure)
  recency_now  the 10 items R1 would have chosen instead (counterfactual)

Each arm also gets past/future controls (items that were in that arm at another
moment of the window but not at this one). The future control is the discount
for topic continuity: the conversation itself pushes material into later briefs,
and recency-ordered briefs are made of exactly that material.

The two arms are NOT symmetric and the asymmetry runs in opposite directions:
served_now can be copied from the prompt (only it can produce real use), while
recency_now is favoured by topic continuity (recent items are about what just
happened). So this measures RELEVANCE, not use; a served_now hit may be use, a
recency_now hit cannot be.

Detectors are the ones from audit 7a (2026-10-14), unchanged: strict (one-liner
>= 25 chars verbatim, or a distinctive file stem on word boundaries) and fuzzy
(>= 60% of the item's distinctive tokens, min 4). Distinctive = token >= 4 chars
present in < 5% of the assistant messages.

Paired test: because both arms come from the same shadow record at the same
instant, McNemar on "message has >= 1 hit" is the right statistic; per-pair
rates are reported too but pairs within a message are not independent.

Read-only: sqlite opened with mode=ro; transcripts and the ndjson only read.
"""
import glob, json, math, os, re, sqlite3, random
from bisect import bisect_right
from collections import defaultdict

DB = "/root/.openclaw/workspace/tools/nox-mem/nox-mem.db"
# DUAS raízes de transcript, descobertas em 21/10 ao notar que atlas e lex não
# tinham diretório na primeira. Não é só atlas/lex: TODO agente tem sessões nas
# duas, e a segunda raiz carrega 179 das 524 mensagens da janela (cipher passa
# de 3 para 42). Medir só a primeira cobria 66%.
# 2026-10-22: a THIRD root. `prune-claude-sessions.sh` deletes transcripts
# older than 7 days (and small ones older than 12 h) from /root/.claude/projects,
# and `nox-archive-transcripts.sh` copies every root to the archive below four
# times a day. The archive is therefore the only place the pruned sessions
# survive, and reading only the live roots measures a substrate that shrinks
# daily. On audit 7a this took the base from 1,120 to 1,524 messages.
PROJ_ROOTS = os.environ.get(
    "PROJ_ROOTS",
    "/root/.claude-nuvini-team/projects:/root/.claude/projects"
    ":/var/lib/nox-mem/action-archive",
).split(":")
SHADOW = "/root/.openclaw/logs/brief-recency-shadow.ndjson"
START = os.environ.get("R1_START", "2026-10-14 22:13:20")
END = os.environ.get("R1_END", "2026-10-22 01:00:00")
ONE_LINER_MAX = int(os.environ.get("ONE_LINER_MAX", "140"))  # src/api/brief.ts
DIRS = {"": "nox", "-agents-boris": "boris", "-agents-forge": "forge",
        "-agents-cipher": "cipher", "-agents-nox": "nox", "-agents-atlas": "atlas",
        "-agents-lex": "lex"}
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


def norm_ts(ts):
    return ts[:19].replace("T", " ")


# ── assistant messages ────────────────────────────────────────────────────────
by_id = {}  # (agent, message id) -> row; dedupes a session present in BOTH roots
seen_dirs = []
for PROJ in PROJ_ROOTS:
  for suffix, agent in DIRS.items():
    d = f"{PROJ}/-root--openclaw-workspace{suffix}"
    if not os.path.isdir(d):
        continue
    seen_dirs.append(d)
    for f in glob.glob(f"{d}/**/*.jsonl", recursive=True):
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
                parts = [c.get("text", "") for c in m.get("content", [])
                         if isinstance(c, dict) and c.get("type") == "text"]
                if not parts:
                    continue
                key = (agent, m.get("id") or f"{os.path.basename(f)}:{ts}")
                prev = by_id.get(key)
                txt = "\n".join(parts)
                by_id[key] = (agent, norm_ts(ts), (prev[2] + "\n" + txt) if prev else txt)
msgs = list(by_id.values())
print(f"transcript dirs read: {len(seen_dirs)}")
print(f"assistant messages with text in window: {len(msgs)}")
by_agent_n = defaultdict(int)
for a, _, _ in msgs:
    by_agent_n[a] += 1
print("by brief agent:", dict(by_agent_n))

df = defaultdict(int)
msg_toks = []
for _, _, t in msgs:
    s = toks(t)
    msg_toks.append(s)
    for x in s:
        df[x] += 1
N = max(1, len(msgs))
common = {t for t, c in df.items() if c / N >= 0.05}

# ── shadow records ────────────────────────────────────────────────────────────
shadow = defaultdict(list)  # agent -> [(ts, served frozenset, recency frozenset)]
nrec = 0
with open(SHADOW, errors="replace") as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        ts = norm_ts(o.get("ts", ""))
        if not (START <= ts < END):
            continue
        nrec += 1
        shadow[o["agent"]].append((ts, frozenset(o.get("served_ids") or ()),
                                   frozenset(o.get("recency_ids") or ())))
for a in shadow:
    shadow[a].sort()
print(f"shadow records in window: {nrec}", {a: len(v) for a, v in shadow.items()})

all_ids = set()
for v in shadow.values():
    for _, s, r in v:
        all_ids |= s | r
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
info = {}
ids = list(all_ids)
for i in range(0, len(ids), 500):
    part = ids[i:i + 500]
    q = "SELECT id, source_file, chunk_text FROM chunks WHERE id IN (%s)" % ",".join("?" * len(part))
    for cid, sf, txt in con.execute(q, part):
        ol = one_liner(txt)
        st = stem(sf)
        info[cid] = {"stem": st, "ol": ol, "sig": (toks(st) | toks(ol)) - common, "sf": sf}
print(f"distinct brief items: {len(all_ids)}, resolvable in chunks: {len(info)}")

stem_count = defaultdict(int)
for v in info.values():
    stem_count[v["stem"].lower()] += 1


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


ARMS = ("served_now", "recency_now", "served_only", "recency_only", "both",
        "served_past", "served_future", "recency_past", "recency_future")

res = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))   # agent -> arm -> [pairs, strict, fuzzy]
msg_hit = defaultdict(lambda: defaultdict(lambda: [0, 0]))  # agent -> arm -> [msgs, msgs with >=1 hit]
paired = defaultdict(int)  # (served_hit, recency_hit) -> n messages, for McNemar
samples = defaultdict(list)
skipped = 0

for (agent, ts, text), mt in zip(msgs, msg_toks):
    sl = shadow.get(agent)
    if not sl:
        skipped += 1
        continue
    times = [x[0] for x in sl]
    k = bisect_right(times, ts) - 1
    if k < 0:
        skipped += 1
        continue
    s_now, r_now = sl[k][1], sl[k][2]
    s_past = set().union(*[x[1] for x in sl[:k]]) - s_now if k > 0 else set()
    r_past = set().union(*[x[2] for x in sl[:k]]) - r_now if k > 0 else set()
    s_fut = (set().union(*[x[1] for x in sl[k + 1:]]) - s_now - s_past) if k + 1 < len(sl) else set()
    r_fut = (set().union(*[x[2] for x in sl[k + 1:]]) - r_now - r_past) if k + 1 < len(sl) else set()
    arms = {"served_now": s_now, "recency_now": r_now,
            "served_only": s_now - r_now, "recency_only": r_now - s_now,
            "both": s_now & r_now,
            "served_past": s_past, "served_future": s_fut,
            "recency_past": r_past, "recency_future": r_fut}
    tl = text.lower()
    per_arm_any = {}
    for arm, ids_ in arms.items():
        ids_ = ids_ & info.keys()
        r = res[agent][arm]
        any_hit = False
        for cid in ids_:
            r[0] += 1
            s, f = strict_hit(cid, tl), fuzzy_hit(cid, mt)
            r[1] += s
            r[2] += f
            if s or f:
                any_hit = True
                if len(samples[arm]) < 400:
                    samples[arm].append((agent, ts, cid, "S" if s else "F"))
        m = msg_hit[agent][arm]
        m[0] += 1
        m[1] += any_hit
        per_arm_any[arm] = any_hit
    paired[(per_arm_any["served_now"], per_arm_any["recency_now"])] += 1

print(f"messages skipped (no shadow record before them): {skipped}")


def fmt(r):
    p, s, f = r
    return (f"pairs={p:>6}  strict={s:>4} ({(s / p * 1e4 if p else 0):7.2f}/10k)"
            f"  fuzzy={f:>4} ({(f / p * 1e4 if p else 0):7.2f}/10k)")


tot = defaultdict(lambda: [0, 0, 0])
tot_msg = defaultdict(lambda: [0, 0])
for agent in sorted(res):
    print(f"\n== {agent}")
    for arm in ARMS:
        r = res[agent][arm]
        m = msg_hit[agent][arm]
        print(f"  {arm:<15} {fmt(r)}   msgs_with_hit={m[1]}/{m[0]}")
        for i in range(3):
            tot[arm][i] += r[i]
        tot_msg[arm][0] += m[0]
        tot_msg[arm][1] += m[1]
print("\n== ALL")
for arm in ARMS:
    m = tot_msg[arm]
    print(f"  {arm:<15} {fmt(tot[arm])}   msgs_with_hit={m[1]}/{m[0]}")

# McNemar, paired on the message: served_now vs recency_now
b = paired[(True, False)]   # served hits, recency does not
c = paired[(False, True)]   # recency hits, served does not
both_y = paired[(True, True)]
neither = paired[(False, False)]
print("\n== McNemar (unit = message; served_now vs recency_now, hit = strict or fuzzy)")
print(f"  both hit: {both_y}   served only: {b}   recency only: {c}   neither: {neither}")
if b + c == 0:
    print("  discordant pairs = 0 -> no evidence either way (test has no information)")
else:
    chi = (abs(b - c) - 1) ** 2 / (b + c)  # continuity-corrected
    p = math.erfc(math.sqrt(chi / 2))
    print(f"  discordant={b + c}  chi2_cc={chi:.3f}  p~{p:.4f}")

random.seed(21)
for arm in ("served_now", "recency_now", "recency_future"):
    s = samples[arm]
    print(f"\n== sample hits ({arm}) for manual precision check  [{len(s)} total]")
    for agent, ts, cid, kind in random.sample(s, min(10, len(s))):
        v = info[cid]
        print(f"  {kind} {agent} {ts} chk {cid} stem={v['stem'][:38]!r} ol={v['ol'][:66]!r}")
