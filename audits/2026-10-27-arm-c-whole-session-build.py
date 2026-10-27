"""Arm C: what the memory would hold if the builder saw each session WHOLE.

The question this settles. Yesterday's net value of -21.2 pp against BM25 has
two candidate causes, and publishing before separating them would sell an
implementation defect as a property of the field:

  (a) EXTRACTION -- the distiller's prompt and 10-item ceiling lose the fact
      even when shown the text. Then the finding is the field's.
  (b) THE WINDOW -- session-distill.ts:141-144 skips any session already in the
      log, so 76% of the prose in the large sessions was never offered. Then the
      finding is ours, the fix is a few lines, and the paper becomes a
      before/after instead of a complaint.

Arm C re-distils the SAME 20 sessions from their complete prose, with the
builder's own prompt, blocking, model, temperature and importance filter, and
hands the result to the same 99 questions. C minus B is what the window costs.

FIDELITY CONTROL, which is the reason this is interpretable at all. The same
re-implementation is also run over the VISIBLE prefix -- the text the builder
actually saw. That arm must reproduce the real arm B in volume and in content
overlap. If re-distilling what the builder saw does not look like what the
builder produced, then C is a fact about my re-implementation and not about the
window, and nothing below can be read.

What is NOT reproduced, and why it favours C (so the conclusion survives it):
  - the embedding dedup (`isDuplicate`) needs the live database. Without it C
    keeps near-duplicates, i.e. MORE units.
  - the learned noise prototypes are skipped: `isNoise` writes to
    noise_prototypes, so it cannot be run against production. Only the static
    rules are applied (<=10 chars is noise, >=500 chars is never noise, the
    regex patterns). Measured justification: the 240 learned prototypes hold 4
    hits in total.
  - the 1 call/sec rate limit is dropped; this is a measurement, not the cron.
"""
import collections, glob, json, os, re, sys, time, unicodedata, urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = "/root/medicoes/2026-10-26-memory-tax"
ARCHIVE = "/var/lib/nox-mem/action-archive"
SET = json.load(open(f"{BASE}/replay-set.json"))
SEE = {r["uuid"]: r for r in json.load(open(f"{BASE}/see-once.json"))["rows"]}
OUT = f"{BASE}/armc-units.json"
GKEY = os.environ["GEMINI_API_KEY"]
GMODEL = "gemini-2.5-flash-lite"
BLOCK_SIZE = 2000
WORKERS = int(os.environ.get("WORKERS", "8"))
SMOKE = os.environ.get("SMOKE", "")
UUID = re.compile(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})")

# ---- DISTILL_SYSTEM, verbatim from src/session-distill.ts
DISTILL_SYSTEM = """Você é um extrator de memória de conversas de IA.
Analise a conversa e extraia APENAS informações que merecem ser lembradas a longo prazo:
- Decisões tomadas pelo usuário ou pelo agente
- Preferências do usuário (como ele quer as coisas feitas)
- Lições aprendidas (erros, fixes, insights técnicos)
- Contexto de projetos relevantes (nomes, status, detalhes)

Ignore: cumprimentos, confirmações (ok, feito, obrigado), listas de tarefas genéricas, conteúdo repetido.

Responda APENAS com JSON válido:
{"memories": [{"text": "...", "category": "decision|preference|lesson|context|project", "importance": 0.0-1.0}]}

Importância: 0.9+ = crítico, 0.7-0.9 = importante, 0.5-0.7 = útil, <0.5 = ignorar.
Retorne [] se não houver nada relevante. Máximo 10 itens."""

GURL = (f"https://generativelanguage.googleapis.com/v1beta/models/{GMODEL}"
        f":generateContent?key={GKEY}")

# ---- extractor, verbatim from replay-build.py, plus the timestamp
CUTS = [
    re.compile(r"Conversation info:.*?```json.*?```", re.S),
    re.compile(r"<system-reminder>.*?</system-reminder>", re.S),
    re.compile(r"<command-name>.*?</command-(?:name|message|args)>", re.S),
    re.compile(r"Caveat: The messages below.*?(?=\n\n|\Z)", re.S | re.I),
    re.compile(r"⟦openclaw:ctx⟧"),
    re.compile(r"<local-command-std(?:out|err)>.*?</local-command-std(?:out|err)>", re.S),
]

def turn(o):
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
    if not s:
        return None
    ts = o.get("timestamp") or ""
    return ((ts.replace("T", " ")[:19] if len(ts) >= 19 else ""),
            role or "unknown", s)

# ---- the distiller's own heartbeat filter, session-distill.ts:214-222
def heartbeat(s):
    return (s.startswith("[cron:") or s.startswith("HEARTBEAT")
            or s.startswith("The conversation history before this point")
            or len(s) < 5 or re.match(r"^heartbeat[_ ]ok\b", s, re.I) is not None)

# ---- isNoise static rules only, noise-filter.ts
NOISE_PATTERNS = [
    re.compile(r"^\s*[\U0001F44D\U0001F44C✅\U0001F64F❤️\U0001F44F\U0001F60A\U0001F91D\U0001F4AA\U0001F525]+\s*$"),
    re.compile(r"^\s*[\.\-_,;:!?]+\s*$"),
    re.compile(r"^\s*\d+\s*$"),
    re.compile(r"^(ok|sim|não|nao|yes|no|yep|nope)\.?\s*$", re.I),
]
def is_noise_static(text):
    t = text.strip()
    if len(t) <= 10:
        return True
    if len(t) >= 500:
        return False
    return any(rx.match(t) for rx in NOISE_PATTERNS)

# ---- blocking, verbatim algorithm from session-distill.ts:402-413
def blocks_of(lines):
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

def distill(block):
    """distillWithGemini, verbatim config. Returns (memories, failed)."""
    body = {"contents": [{"role": "user",
                          "parts": [{"text": DISTILL_SYSTEM + "\n\nConversa:\n" + block}]}],
            "generationConfig": {"responseMimeType": "application/json",
                                 "temperature": 0.1}}
    req = urllib.request.Request(GURL, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    last = None
    for a in range(5):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.load(r)
            txt = "".join(p.get("text", "") for p in
                          ((d.get("candidates") or [{}])[0].get("content") or {}).get("parts") or [])
            if not txt:
                return [], True, d.get("usageMetadata") or {}
            mem = (json.loads(txt).get("memories") or [])
            # importance filter, session-distill.ts:280 / 427
            return ([m for m in mem if (m.get("importance") or 0) >= 0.5], False,
                    d.get("usageMetadata") or {})
        except Exception as e:
            last = f"{type(e).__name__}: {str(e)[:120]}"
            time.sleep(2 * (a + 1))
    return [], True, {"error": last}

raw = {m.group(1): p for p in glob.glob(os.path.join(ARCHIVE, "*", "*.jsonl"))
       if (m := UUID.search(os.path.basename(p)))}

jobs, meta = [], {}
for s in SET["sessions"]:
    u = s["uuid"]
    pa = SEE[u]["processed_at"]
    ts = [t for t in (turn(o) for o in
                      (json.loads(l) for l in open(raw[u], encoding="utf-8", errors="replace")
                       if l.strip() and l.lstrip().startswith("{"))) if t]
    keep = [(t[0], f"[{t[1].upper()}]: {t[2]}") for t in ts
            if not heartbeat(t[2]) and not is_noise_static(t[2])]
    full = blocks_of([x[1] for x in keep])
    visible = blocks_of([x[1] for x in keep if x[0] and x[0] <= pa])
    meta[u] = {"agent": s.get("agent"), "blocks_full": len(full),
               "blocks_visible": len(visible), "units_real": len(s["units"]),
               "prose_chars": s["prose_chars"]}
    for i, b in enumerate(full):
        jobs.append((u, "full", i, b))
    for i, b in enumerate(visible):
        jobs.append((u, "visible", i, b))

nf = sum(1 for j in jobs if j[1] == "full")
nv = len(jobs) - nf
print(f"{len(SET['sessions'])} sessions · blocks: full {nf} · visible {nv} "
      f"(fidelity control)", flush=True)
if SMOKE:
    jobs = [j for j in jobs if j[0] == SET["sessions"][0]["uuid"]]
    print(f"SMOKE: {len(jobs)} blocks of one session", flush=True)

res = collections.defaultdict(list)
fails = collections.Counter()
tin = tout = 0
t0, done = time.time(), 0
def run(j):
    u, kind, i, b = j
    mem, failed, usage = distill(b)
    return u, kind, i, mem, failed, usage, len(b)
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    for u, kind, i, mem, failed, usage, blen in ex.map(run, jobs):
        if failed:
            fails[kind] += 1
        tin += usage.get("promptTokenCount", 0) or 0
        tout += (usage.get("candidatesTokenCount", 0) or 0) + (usage.get("thoughtsTokenCount", 0) or 0)
        for m in mem:
            # the INSERT's own text shape, session-distill.ts:459
            res[(u, kind)].append({
                "text": f"[{m.get('category')}|{meta[u]['agent']}] {m.get('text','')}",
                "category": m.get("category"), "importance": m.get("importance"),
                "block": i})
        done += 1
        if done % 100 == 0 or done == len(jobs):
            print(f"  {done}/{len(jobs)}  {time.time()-t0:.0f}s", flush=True)

cost = tin / 1e6 * 0.10 + tout / 1e6 * 0.40
print(f"\n{done} blocks distilled · empty-or-failed: full {fails['full']} "
      f"visible {fails['visible']} · {tin} in / {tout} out tokens "
      f"(~US$ {cost:.4f}) · {time.time()-t0:.0f}s")

json.dump({"meta": meta,
           "units": {f"{u}|{k}": v for (u, k), v in res.items()}},
          open(OUT, "w"), ensure_ascii=False)

print("\nFIDELITY CONTROL · re-distilling what the builder SAW against what it produced")
print(f"{'session':10s} {'blocks vis':>10s} {'units real':>11s} {'units mine':>11s} "
      f"{'ratio':>7s} {'blocks full':>12s} {'units full':>11s}")
rows = []
for u, m in meta.items():
    mine = len(res.get((u, "visible"), []))
    full = len(res.get((u, "full"), []))
    if SMOKE and u != SET["sessions"][0]["uuid"]:
        continue
    r = mine / m["units_real"] if m["units_real"] else 0
    rows.append(r)
    print(f"{u[:8]:10s} {m['blocks_visible']:10d} {m['units_real']:11d} {mine:11d} "
          f"{r:7.2f} {m['blocks_full']:12d} {full:11d}")
if rows:
    rows.sort()
    print(f"\nratio mine/real: median {rows[len(rows)//2]:.2f} · "
          f"min {rows[0]:.2f} · max {rows[-1]:.2f}")
    print("A median far from 1.0 means arm C measures my re-implementation, not the window.")
tot_real = sum(m["units_real"] for m in meta.values())
tot_full = sum(len(res.get((u, "full"), [])) for u in meta)
print(f"\nunits: real {tot_real} · re-distilled from FULL prose {tot_full} "
      f"({tot_full/max(tot_real,1):.2f}x)")
