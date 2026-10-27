"""Decompose yesterday's 52.3% faithfulness tax against the see-once rule.

The defect this measures is mine. The replay generated its questions from
windows cut out of the FINAL prose in the archive, and asked the memory units to
answer them. But session-distill.ts:141-144 skips any session already in the
log, so the units were built from whatever the transcript held at processed_at
-- 3.01% of it in one of the sampled sessions. A question whose evidence arrived
after that instant cannot be answered from memory however faithful the
extraction is, and counting it as faithfulness tax charges construction for a
window it never saw.

Method. Each generated fact carries verbatim `citations` from the raw prose. A
citation that appears in the VISIBLE prose (turns timestamped at or before
processed_at) was available to the builder; one that appears only in the final
prose was not. Comparison ignores whitespace, the same `norm` the generator used
to verify the quotes, so formatting does not decide it.

Controls:
  - Arm A reads a window of the FINAL prose either way, so its accuracy must NOT
    differ much between the two populations. If it collapses on one of them, the
    split is tracking something else and the decomposition is void.
  - every citation is re-verified against the final prose first: a fact whose
    quote is not even in the final text cannot be placed, and is reported apart
    rather than assigned to either side.
"""
import collections, json, re, statistics

SEE = json.load(open("/root/medicoes/2026-10-26-memory-tax/see-once.json"))
ANS = json.load(open("/root/medicoes/2026-10-26-memory-tax/replay-answers.json"))
JUD = json.load(open("/root/medicoes/2026-10-26-memory-tax/replay-judged.json"))
SET = json.load(open("/root/medicoes/2026-10-26-memory-tax/replay-set.json"))

def norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip().lower()

see = {r["uuid"]: r for r in SEE["rows"]}
# The replay set holds the final prose per session; rebuild the visible prefix
# the same way see-once.py did, from the session's own row.
sess = {s["uuid"]: s for s in SET["sessions"]}
print("sampled sessions:", len(sess), "· with a see-once row:", sum(1 for u in sess if u in see))

# Visible prose per sampled session, recomputed here from the archive so the
# membership test runs against text rather than against a character count.
import glob, os
ARCHIVE = "/var/lib/nox-mem/action-archive"
UUID = re.compile(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})")
raw = {m.group(1): p for p in glob.glob(os.path.join(ARCHIVE, "*", "*.jsonl"))
       if (m := UUID.search(os.path.basename(p)))}
CUTS = [
    re.compile(r"Conversation info:.*?```json.*?```", re.S),
    re.compile(r"<system-reminder>.*?</system-reminder>", re.S),
    re.compile(r"<command-name>.*?</command-(?:name|message|args)>", re.S),
    re.compile(r"Caveat: The messages below.*?(?=\n\n|\Z)", re.S | re.I),
    re.compile(r"⟦openclaw:ctx⟧"),
    re.compile(r"<local-command-std(?:out|err)>.*?</local-command-std(?:out|err)>", re.S),
]
def turns(path):
    out = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                o = json.loads(line)
            except Exception:
                continue
            if o.get("type") not in ("message", "user", "assistant"):
                continue
            msg = o.get("message") or {}
            role = msg.get("role") or o.get("role")
            if role not in ("user", "assistant"):
                continue
            c = msg.get("content", o.get("content"))
            if isinstance(c, str):
                blocks = [c]
            elif isinstance(c, list):
                blocks = [b.get("text", "") for b in c
                          if isinstance(b, dict) and b.get("type") in (None, "text")]
            else:
                continue
            s = "\n".join(b for b in blocks if b)
            for rx in CUTS:
                s = rx.sub(" ", s)
            s = re.sub(r"\n{3,}", "\n\n", s).strip()
            if not s or len(s) < 5 or s.startswith("[cron:") or s.startswith("HEARTBEAT"):
                continue
            ts = o.get("timestamp") or ""
            out.append((ts.replace("T", " ")[:19] if len(ts) >= 19 else "", f"{role}: {s}"))
    return out

vis_norm, fin_norm = {}, {}
for u in sess:
    if u not in see or u not in raw:
        continue
    pa = see[u]["processed_at"]
    ts = turns(raw[u])
    fin_norm[u] = norm("\n".join(t[1] for t in ts))
    vis_norm[u] = norm("\n".join(t[1] for t in ts if t[0] and t[0] <= pa))
print("sessions with visible/final prose rebuilt:", len(vis_norm))

# Join answers -> judged by (uuid, question)
jud = {(r["uuid"], r["question"]): r for r in JUD}
rows = []
unplaceable = 0
for a in ANS:
    k = (a["uuid"], a["question"])
    if k not in jud:
        continue
    j = jud[k]
    u = a["uuid"]
    cites = [c for c in (a.get("citations") or []) if c]
    if u not in fin_norm or not cites:
        unplaceable += 1
        continue
    in_final = [c for c in cites if norm(c) in fin_norm[u]]
    if not in_final:
        unplaceable += 1
        continue
    # Available to the builder if ANY verified citation sits in the visible prose
    # -- the generous reading, which under-counts the operational share.
    avail = any(norm(c) in vis_norm.get(u, "") for c in in_final)
    rows.append({**j, "available": avail, "visible_frac": see[u]["visible_frac"]})

print(f"\njudged pairs placed: {len(rows)} of {len(JUD)} · unplaceable {unplaceable}")

def rate(g, key):
    if not g:
        return 0.0
    return sum(1 for r in g if (r[key] or {}).get("contem", 0) > 0.5) / len(g)
def silent(g, key):
    if not g:
        return 0.0
    return sum(1 for r in g if (r[key] or {}).get("nivel_label") == "nao_responde"
               or ((r[key] or {}).get("nivel_score") or 9) < 0.5) / len(g)

print(f"\n{'population':34s} {'n':>4s} {'arm A':>7s} {'arm B':>7s} {'tax':>8s}")
for lab, g in (("ALL (yesterday's headline)", rows),
               ("evidence VISIBLE to builder", [r for r in rows if r["available"]]),
               ("evidence arrived AFTER see-once", [r for r in rows if not r["available"]])):
    a, b = rate(g, "a"), rate(g, "b")
    tax = (a - b) / a if a else 0
    print(f"{lab:34s} {len(g):4d} {a*100:6.1f}% {b*100:6.1f}% {tax*100:7.1f}%")

print("\nCONTROL · arm A must not differ much between the two populations")
ga = [r for r in rows if r["available"]]
gn = [r for r in rows if not r["available"]]
print(f"  arm A visible={rate(ga,'a')*100:.1f}%  after={rate(gn,'a')*100:.1f}%  "
      f"delta={abs(rate(ga,'a')-rate(gn,'a'))*100:.1f} pp")

print("\nby category, on the VISIBLE population only (the honest faithfulness cell):")
for cat in ("context", "decision", "lesson", "preference"):
    g = [r for r in ga if r["category"] == cat]
    if not g:
        continue
    a, b = rate(g, "a"), rate(g, "b")
    print(f"  {cat:11s} n={len(g):3d}  A {a*100:5.1f}%  B {b*100:5.1f}%  "
          f"tax {((a-b)/a*100 if a else 0):5.1f}%")

json.dump(rows, open("/root/medicoes/2026-10-26-memory-tax/decomposed.json", "w"),
          ensure_ascii=False)
