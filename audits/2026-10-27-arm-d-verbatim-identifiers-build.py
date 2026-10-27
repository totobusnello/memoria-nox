"""Arm D: one sentence added to DISTILL_SYSTEM, nothing else changed.

Every number from arm C points here. Shown the WHOLE conversation, the builder
left `context` at 26.2% and `decision` at 48.3% -- not one point of movement --
while `lesson` went 60.7 -> 75.0%. It reads the turn and does not keep the file
name. So the lever is the extraction criterion, and the only way to say that is
to change the criterion and nothing else.

ONE VARIABLE. The prompt below is `DISTILL_SYSTEM` verbatim with a single
paragraph inserted. Blocking, model, temperature, `responseMimeType`, the
`importance >= 0.5` filter and the 10-item ceiling are untouched -- including
the ceiling, which is a candidate of its own and stays fixed so that whatever
moves is attributable to this paragraph.

Two inputs, giving two controlled pairs:
  visible prose -- against arm C_visible, which is the SAME pipeline with the
                   old prompt on the same text. This is the clean A/B, and the
                   input is what the live builder actually had.
  full prose    -- against arm C_all.

MECHANICAL CONTROL, independent of any judge: the rate at which identifiers in
the source block survive verbatim into the extracted units. The prompt's claim
is testable by string matching, so it is tested that way before a model is asked
anything. If the rate does not move, the prompt did not do what it says and no
accuracy difference below is attributable to it.
"""
import collections, glob, json, os, re, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = "/root/medicoes/2026-10-26-memory-tax"
ARCHIVE = "/var/lib/nox-mem/action-archive"
SET = json.load(open(f"{BASE}/replay-set.json"))
SEE = {r["uuid"]: r for r in json.load(open(f"{BASE}/see-once.json"))["rows"]}
C = json.load(open(f"{BASE}/armc-units.json"))
OUT = f"{BASE}/armd-units.json"
GKEY = os.environ["GEMINI_API_KEY"]
GMODEL = "gemini-2.5-flash-lite"
BLOCK_SIZE = 2000
WORKERS = int(os.environ.get("WORKERS", "8"))
SMOKE = os.environ.get("SMOKE", "")
UUID = re.compile(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})")

# ---- the inserted paragraph is the ONLY difference from src/session-distill.ts
DISTILL_SYSTEM_V2 = """Você é um extrator de memória de conversas de IA.
Analise a conversa e extraia APENAS informações que merecem ser lembradas a longo prazo:
- Decisões tomadas pelo usuário ou pelo agente
- Preferências do usuário (como ele quer as coisas feitas)
- Lições aprendidas (erros, fixes, insights técnicos)
- Contexto de projetos relevantes (nomes, status, detalhes)

Ignore: cumprimentos, confirmações (ok, feito, obrigado), listas de tarefas genéricas, conteúdo repetido.

OBRIGATÓRIO: todo identificador que aparecer na conversa tem de ser copiado LETRA POR LETRA no texto da memória — nome de arquivo, caminho, comando, nome de tabela ou de coluna, chave de configuração, número de porta, URL, nome de canal, versão, valor numérico. Nunca trocar por descrição ("o arquivo de tarefas"), nunca abreviar, nunca traduzir. Uma memória que diz o que foi decidido mas não diz sobre qual arquivo, comando ou valor não serve para nada: ou carrega o identificador, ou não vale ser extraída.

Responda APENAS com JSON válido:
{"memories": [{"text": "...", "category": "decision|preference|lesson|context|project", "importance": 0.0-1.0}]}

Importância: 0.9+ = crítico, 0.7-0.9 = importante, 0.5-0.7 = útil, <0.5 = ignorar.
Retorne [] se não houver nada relevante. Máximo 10 itens."""

GURL = (f"https://generativelanguage.googleapis.com/v1beta/models/{GMODEL}"
        f":generateContent?key={GKEY}")

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
    return ((ts.replace("T", " ")[:19] if len(ts) >= 19 else ""), role or "unknown", s)

def heartbeat(s):
    return (s.startswith("[cron:") or s.startswith("HEARTBEAT")
            or s.startswith("The conversation history before this point")
            or len(s) < 5 or re.match(r"^heartbeat[_ ]ok\b", s, re.I) is not None)

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
    body = {"contents": [{"role": "user",
                          "parts": [{"text": DISTILL_SYSTEM_V2 + "\n\nConversa:\n" + block}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1}}
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
            return ([m for m in mem if (m.get("importance") or 0) >= 0.5], False,
                    d.get("usageMetadata") or {})
        except Exception as e:
            last = f"{type(e).__name__}: {str(e)[:120]}"
            time.sleep(2 * (a + 1))
    return [], True, {"error": last}

# ---- the mechanical control: identifiers, and whether they survive verbatim
IDENT = re.compile(
    r"(?:"
    r"[\w./-]+\.(?:md|ts|js|mjs|py|json|sh|yml|yaml|db|sql|jsonl|txt|env|toml)\b"  # file
    r"|/(?:[\w.-]+/){1,}[\w.-]+"                                                   # path
    r"|\b[a-z][a-z0-9]*(?:_[a-z0-9]+){1,}\b"                                       # snake_case
    r"|\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+){1,}\b"                                       # CONST_CASE
    r"|\bv?\d+\.\d+(?:\.\d+)?\b"                                                   # version
    r"|\bhttps?://\S+"                                                             # url
    r"|\b\d{4,}\b"                                                                 # port / big number
    r")")
STOP = {"session_distill_log", "chunk_text", "source_file"}   # appear in the prompt itself? no, kept

def idents(text):
    return {m.group(0) for m in IDENT.finditer(text or "")}

raw = {m.group(1): p for p in glob.glob(os.path.join(ARCHIVE, "*", "*.jsonl"))
       if (m := UUID.search(os.path.basename(p)))}

jobs, meta, blocktext = [], {}, {}
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
               "blocks_visible": len(visible), "units_real": len(s["units"])}
    for kind, bl in (("full", full), ("visible", visible)):
        for i, b in enumerate(bl):
            jobs.append((u, kind, i, b))
            blocktext[(u, kind, i)] = b

print(f"blocks: full {sum(1 for j in jobs if j[1]=='full')} · "
      f"visible {sum(1 for j in jobs if j[1]=='visible')}", flush=True)
if SMOKE:
    jobs = [j for j in jobs if j[0] == SET["sessions"][-1]["uuid"]][:12]
    print(f"SMOKE: {len(jobs)} blocks", flush=True)

res = collections.defaultdict(list)
fails = collections.Counter()
tin = tout = done = 0
t0 = time.time()
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    for u, kind, i, mem, failed, usage in ex.map(
            lambda j: (j[0], j[1], j[2], *distill(j[3])), jobs):
        if failed:
            fails[kind] += 1
        tin += usage.get("promptTokenCount", 0) or 0
        tout += (usage.get("candidatesTokenCount", 0) or 0) + (usage.get("thoughtsTokenCount", 0) or 0)
        for m in mem:
            res[(u, kind)].append({
                "text": f"[{m.get('category')}|{meta[u]['agent']}] {m.get('text','')}",
                "category": m.get("category"), "importance": m.get("importance"), "block": i})
        done += 1
        if done % 100 == 0 or done == len(jobs):
            print(f"  {done}/{len(jobs)}  {time.time()-t0:.0f}s", flush=True)

cost = tin / 1e6 * 0.10 + tout / 1e6 * 0.40
print(f"\n{done} blocks · empty-or-failed: full {fails['full']} visible {fails['visible']} "
      f"· {tin} in / {tout} out (~US$ {cost:.4f}) · {time.time()-t0:.0f}s")

json.dump({"prompt": "DISTILL_SYSTEM_V2", "meta": meta,
           "units": {f"{u}|{k}": v for (u, k), v in res.items()}},
          open(OUT, "w"), ensure_ascii=False)

# ---- MECHANICAL CONTROL, per block, D against C on the identical input
print("\nMECHANICAL CONTROL · identifiers of the source block surviving verbatim into the units")
print("(no judge involved: the prompt's claim is a string-matching claim)")
cu = collections.defaultdict(list)
for k, v in C["units"].items():
    u, kind = k.rsplit("|", 1)
    for m in v:
        cu[(u, kind, m["block"])].append(m["text"])
du = collections.defaultdict(list)
for (u, kind), v in res.items():
    for m in v:
        du[(u, kind, m["block"])].append(m["text"])

print(f"{'input':9s} {'blocks':>7s} {'src idents':>11s} "
      f"{'C kept':>9s} {'D kept':>9s} {'C rate':>8s} {'D rate':>8s} {'delta':>7s}")
for kind in ("visible", "full"):
    keys = [k for k in blocktext if k[1] == kind and (k in cu or k in du)]
    if SMOKE:
        keys = [k for k in keys if k in du]
    if not keys:
        continue
    si = ck = dk = 0
    for k in keys:
        src = idents(blocktext[k])
        if not src:
            continue
        si += len(src)
        ctxt = " ".join(cu.get(k, []))
        dtxt = " ".join(du.get(k, []))
        ck += sum(1 for x in src if x in ctxt)
        dk += sum(1 for x in src if x in dtxt)
    if si:
        print(f"{kind:9s} {len(keys):7d} {si:11d} {ck:9d} {dk:9d} "
              f"{ck/si*100:7.1f}% {dk/si*100:7.1f}% {(dk-ck)/si*100:+6.1f}")

print("\nvolume and shape of the units")
print(f"{'input':9s} {'C units':>8s} {'D units':>8s} {'C chars/u':>10s} {'D chars/u':>10s}")
for kind in ("visible", "full"):
    cn = sum(len(v) for k, v in C["units"].items() if k.endswith(f"|{kind}"))
    dn = sum(len(v) for (u, k), v in res.items() if k == kind)
    cc = [len(m["text"]) for k, v in C["units"].items() if k.endswith(f"|{kind}") for m in v]
    dc = [len(m["text"]) for (u, k), v in res.items() if k == kind for m in v]
    if dc:
        print(f"{kind:9s} {cn:8d} {dn:8d} {sum(cc)/max(len(cc),1):10.0f} "
              f"{sum(dc)/len(dc):10.0f}")
print("\ncategory mix (D, full)")
cm = collections.Counter(m["category"] for (u, k), v in res.items() if k == "full" for m in v)
cmc = collections.Counter(m["category"] for k, v in C["units"].items() if k.endswith("|full")
                          for m in v)
for cat in set(cm) | set(cmc):
    print(f"   {str(cat):12s} C {cmc.get(cat,0):5d}  D {cm.get(cat,0):5d}")
