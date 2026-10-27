"""Build a naive-RAG index over the RAW transcripts, so the raw side of the
replay stops being an oracle.

Why. Yesterday's arm A received the window around the evidence, which makes it
an upper bound on what naive RAG over the transcript would achieve. That is the
stated reason the 52.3% was published as a floor with no known ceiling, and it
is the one thing that keeps the number from being comparable to the paper's,
which compares a memory system against naive RAG. This supplies the missing
side.

Chunking is a fixed 2000-character window with a HARD cut, which is what naive
RAG does and is deliberately NOT what the builder does: session-distill.ts:
402-413 never splits a line, so one long turn becomes one oversized block (the
error that made me divide final prose by 2000 and report a 23x spread). A hard
cut also keeps every chunk inside gemini-embedding-001's 2048-token input limit,
which this repository has already been bitten by applying as a character cut.

Two retrievers, because they fail differently and the gap between them is itself
the finding: BM25 (deterministic, free, the system's own layer 1) and dense
embeddings (gemini-embedding-001 at 3072d, the system's own layer 2).

CONTROL. The prose is rebuilt from the archive with `turn_text` copied verbatim
from 2026-10-26-replay-build.py, and the rebuilt length is asserted against the
`prose_chars` that script recorded. Indexing a text that differs from the one
the questions were generated from would measure the extractor, not the
retriever -- and the extractor is exactly where the last four defects were.
"""
import glob, json, os, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = "/root/medicoes/2026-10-26-memory-tax"
ARCHIVE = "/var/lib/nox-mem/action-archive"
SET = json.load(open(f"{BASE}/replay-set.json"))
OUT = f"{BASE}/rag-index.json"
GKEY = os.environ["GEMINI_API_KEY"]
EMODEL = "gemini-embedding-001"
CHUNK = 2000
WORKERS = 6
UUID = re.compile(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})")
EURL = (f"https://generativelanguage.googleapis.com/v1beta/models/{EMODEL}"
        f":batchEmbedContents?key={GKEY}")

# ---- extractor, verbatim from 2026-10-26-replay-build.py
CUTS = [
    re.compile(r"Conversation info:.*?```json.*?```", re.S),
    re.compile(r"<system-reminder>.*?</system-reminder>", re.S),
    re.compile(r"<command-name>.*?</command-(?:name|message|args)>", re.S),
    re.compile(r"Caveat: The messages below.*?(?=\n\n|\Z)", re.S | re.I),
    re.compile(r"⟦openclaw:ctx⟧"),
    re.compile(r"<local-command-std(?:out|err)>.*?</local-command-std(?:out|err)>", re.S),
]

def turn_text(o):
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

def hard_chunks(text, size=CHUNK):
    out, i = [], 0
    while i < len(text):
        j = min(i + size, len(text))
        if j < len(text):
            k = text.rfind(" ", i + size - 200, j)
            if k > i:
                j = k
        out.append(text[i:j])
        i = j
    return out

raw = {m.group(1): p for p in glob.glob(os.path.join(ARCHIVE, "*", "*.jsonl"))
       if (m := UUID.search(os.path.basename(p)))}

sessions, mismatch = {}, []
for s in SET["sessions"]:
    u = s["uuid"]
    txt = "\n\n".join(prose(raw[u]))   # separator verbatim from replay-build.py:113
    if abs(len(txt) - s["prose_chars"]) > 2:
        mismatch.append((u[:8], len(txt), s["prose_chars"]))
    ch = hard_chunks(txt)
    assert sum(len(c) for c in ch) >= len(txt) * 0.99, f"chunking lost text on {u[:8]}"
    sessions[u] = {"chunks": ch, "units_chars": s["units_chars"], "prose_chars": len(txt)}

print(f"CONTROL · rebuilt prose vs replay-build's prose_chars: "
      f"{len(SET['sessions']) - len(mismatch)}/{len(SET['sessions'])} exact")
for m in mismatch:
    print(f"   MISMATCH {m[0]} rebuilt={m[1]} recorded={m[2]}")
assert not mismatch, "the indexed text differs from the text the questions came from"

tot = sum(len(v["chunks"]) for v in sessions.values())
print(f"{len(sessions)} sessions · {tot} chunks of <= {CHUNK} chars", flush=True)

def embed_batch(texts):
    body = {"requests": [{"model": f"models/{EMODEL}",
                          "content": {"parts": [{"text": t}]},
                          "taskType": "RETRIEVAL_DOCUMENT"} for t in texts]}
    req = urllib.request.Request(EURL, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    last = None
    for a in range(5):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                d = json.load(r)
            return [e["values"] for e in d["embeddings"]]
        except Exception as e:
            last = f"{type(e).__name__}: {str(e)[:160]}"
            time.sleep(2 * (a + 1))
    raise RuntimeError(last)

jobs = [(u, i, v["chunks"][i:i + 20])
        for u, v in sessions.items() for i in range(0, len(v["chunks"]), 20)]
print(f"{len(jobs)} embed batches", flush=True)

vecs = {u: [None] * len(v["chunks"]) for u, v in sessions.items()}
t0, done = time.time(), 0
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    for u, i, es in ex.map(lambda j: (j[0], j[1], embed_batch(j[2])), jobs):
        for n, e in enumerate(es):
            vecs[u][i + n] = e
        done += 1
        if done % 10 == 0 or done == len(jobs):
            print(f"  {done}/{len(jobs)}  {time.time()-t0:.0f}s", flush=True)

for u, v in vecs.items():
    miss = sum(1 for x in v if x is None)
    assert miss == 0, f"{u[:8]} has {miss} chunks without a vector"
print(f"\nall {tot} chunks embedded · dims {{{len(next(iter(vecs.values()))[0])}}}")

json.dump({"chunk_size": CHUNK, "model": EMODEL,
           "sessions": {u: {**v, "vecs": vecs[u]} for u, v in sessions.items()}},
          open(OUT, "w"))
print(f"wrote {OUT} ({os.path.getsize(OUT)/1e6:.1f} MB)")
