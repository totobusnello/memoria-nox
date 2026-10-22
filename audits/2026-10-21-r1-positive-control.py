#!/usr/bin/env python3
"""Controle positivo + capacidade do detector do R1 (2026-10-21).

Pergunta que decide se o 0 de 345 significa "nao usa" ou "nao meco":
 1. CAPACIDADE: quantos itens do brief sao detectaveis POR CONSTRUCAO?
 2. CONTROLE POSITIVO: se o agente citasse o item, o detector acenderia?
Read-only.
"""
import glob, json, os, re, sqlite3, random
from bisect import bisect_right
from collections import defaultdict

exec(open("/root/medicoes/2026-10-21-r1/r1-relevance.py").read().split("# ── assistant messages")[0].split('"""', 2)[2])

# re-executa a coleta (identica ao detector) ------------------------------
by_id = {}
for PROJ in PROJ_ROOTS:
  for suffix, agent in DIRS.items():
    d = f"{PROJ}/-root--openclaw-workspace{suffix}"
    if not os.path.isdir(d):
        continue
    for f in glob.glob(f"{d}/**/*.jsonl", recursive=True):
        with open(f, errors="replace") as fh:
            for line in fh:
                if '"type":"assistant"' not in line:
                    continue
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                ts = o.get("timestamp"); m = o.get("message") or {}
                if not ts or not (START <= norm_ts(ts) < END):
                    continue
                parts = [c.get("text", "") for c in m.get("content", []) if isinstance(c, dict) and c.get("type") == "text"]
                if not parts:
                    continue
                key = (agent, m.get("id") or f"{os.path.basename(f)}:{ts}")
                prev = by_id.get(key); txt = "\n".join(parts)
                by_id[key] = (agent, norm_ts(ts), (prev[2] + "\n" + txt) if prev else txt)
msgs = list(by_id.values())
print("mensagens:", len(msgs))

df = defaultdict(int); msg_toks = []
for _, _, t in msgs:
    s = toks(t); msg_toks.append(s)
    for x in s: df[x] += 1
N = max(1, len(msgs))
common = {t for t, c in df.items() if c / N >= 0.05}

shadow = defaultdict(list)
for line in open(SHADOW, errors="replace"):
    line = line.strip()
    if not line: continue
    try: o = json.loads(line)
    except Exception: continue
    ts = norm_ts(o.get("ts", ""))
    if not (START <= ts < END): continue
    shadow[o["agent"]].append((ts, frozenset(o.get("served_ids") or ()), frozenset(o.get("recency_ids") or ())))
for a in shadow: shadow[a].sort()

all_ids = set()
for v in shadow.values():
    for _, s, r in v: all_ids |= s | r
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
info = {}; ids = list(all_ids)
for i in range(0, len(ids), 500):
    part = ids[i:i+500]
    q = "SELECT id, source_file, chunk_text FROM chunks WHERE id IN (%s)" % ",".join("?"*len(part))
    for cid, sf, txt in con.execute(q, part):
        ol = one_liner(txt); st = stem(sf)
        info[cid] = {"stem": st, "ol": ol, "sig": (toks(st) | toks(ol)) - common, "sf": sf}
stem_count = defaultdict(int)
for v in info.values(): stem_count[v["stem"].lower()] += 1
def stem_ok(s): return len(s) >= 8 and stem_count[s] <= 2 and re.search(r"[-_0-9]", s) is not None
def strict_hit(cid, tl):
    v = info.get(cid)
    if not v: return False
    ol = v["ol"].lower().rstrip("…")
    if len(ol) >= 25 and ol in tl: return True
    s = v["stem"].lower()
    return stem_ok(s) and re.search(r"(?<![\w])"+re.escape(s)+r"(?![\w])", tl) is not None
def fuzzy_hit(cid, mt):
    v = info.get(cid)
    if not v or len(v["sig"]) < 4: return False
    return len(v["sig"] & mt) / len(v["sig"]) >= 0.6

# 1. CAPACIDADE ------------------------------------------------------------
served_u, recency_u = set(), set()
for v in shadow.values():
    for _, s, r in v: served_u |= s; recency_u |= r
def cap(ids_, label):
    ids_ = [c for c in ids_ if c in info]
    ol_ok = sum(1 for c in ids_ if len(info[c]["ol"].rstrip("…")) >= 25)
    st_ok = sum(1 for c in ids_ if stem_ok(info[c]["stem"].lower()))
    sig_ok = sum(1 for c in ids_ if len(info[c]["sig"]) >= 4)
    vis = sum(1 for c in ids_ if (len(info[c]["ol"].rstrip("…")) >= 25 or stem_ok(info[c]["stem"].lower())) or len(info[c]["sig"]) >= 4)
    n = len(ids_)
    print(f"  {label:<12} itens={n:>4}  one_liner>=25c={ol_ok:>4} ({ol_ok/n:5.1%})  stem distintivo={st_ok:>4} ({st_ok/n:5.1%})  sig>=4tok={sig_ok:>4} ({sig_ok/n:5.1%})  detectavel por algum={vis} ({vis/n:5.1%})")
print("\n== 1. CAPACIDADE do detector (itens unicos da janela)")
cap(served_u, "served"); cap(recency_u, "recency")

# 2. CONTROLE POSITIVO -----------------------------------------------------
print("\n== 2. CONTROLE POSITIVO: injetar o item no texto da mensagem e re-detectar")
random.seed(21)
pairs = []
for (agent, ts, text), mt in zip(msgs, msg_toks):
    sl = shadow.get(agent)
    if not sl: continue
    k = bisect_right([x[0] for x in sl], ts) - 1
    if k < 0: continue
    for cid in (sl[k][1] | sl[k][2]) & info.keys():
        pairs.append((agent, ts, text, mt, cid))
sample = random.sample(pairs, min(300, len(pairs)))
for mode in ("one_liner", "one_liner+stem", "chunk_text_200c"):
    ok_s = ok_f = 0
    for agent, ts, text, mt, cid in sample:
        v = info[cid]
        if mode == "one_liner": inj = v["ol"]
        elif mode == "one_liner+stem": inj = v["ol"] + " (" + v["stem"] + ")"
        else:
            row = con.execute("SELECT chunk_text FROM chunks WHERE id=?", (cid,)).fetchone()
            inj = (row[0] or "")[:200]
        t2 = text + "\n\nComo o brief lembra: " + inj
        ok_s += strict_hit(cid, t2.lower()); ok_f += fuzzy_hit(cid, toks(t2))
    n = len(sample)
    print(f"  injetando {mode:<16} n={n}  strict acende={ok_s} ({ok_s/n:5.1%})  fuzzy acende={ok_f} ({ok_f/n:5.1%})  qualquer={sum(1 for _ in range(0))if 0 else ''}")

# 3. o que o R1 MUDARIA (independe de relevancia) --------------------------
print("\n== 3. O que o R1 trocaria, e a idade dos dois bracos")
import statistics as st
ov = []; sa = []; ra = []; per_agent = defaultdict(lambda: ([], [], []))
for line in open(SHADOW, errors="replace"):
    line = line.strip()
    if not line: continue
    try: o = json.loads(line)
    except Exception: continue
    if not (START <= norm_ts(o["ts"]) < END): continue
    ov.append(o["overlap"]); sa += o["served_age_days"]; ra += o["recency_age_days"]
    p = per_agent[o["agent"]]; p[0].append(o["overlap"]); p[1].extend(o["served_age_days"]); p[2].extend(o["recency_age_days"])
def q(v, p): 
    v = sorted(v); import math as _m
    return v[min(len(v)-1, int(p*len(v)))]
print(f"  overlap servido x R1: mediana={st.median(ov)}  media={sum(ov)/len(ov):.2f}  de 10  =>  R1 trocaria {10-st.median(ov):.0f}/10 itens")
print(f"  idade servida  (dias): mediana={st.median(sa):6.1f}  p10={q(sa,.10):5} p90={q(sa,.90):5}  max={max(sa)}")
print(f"  idade R1       (dias): mediana={st.median(ra):6.1f}  p10={q(ra,.10):5} p90={q(ra,.90):5}  max={max(ra)}")
print(f"  fracao de itens servidos com mais de 90 dias: {sum(1 for x in sa if x>90)/len(sa):.1%}   R1: {sum(1 for x in ra if x>90)/len(ra):.1%}")
for a in sorted(per_agent):
    o_, s_, r_ = per_agent[a]
    print(f"    {a:<8} overlap med={st.median(o_):.0f}  idade servida med={st.median(s_):6.1f}  idade R1 med={st.median(r_):5.1f}")
