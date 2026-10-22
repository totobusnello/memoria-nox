#!/usr/bin/env python3
"""Pooling pass: judge what the system actually returned.

The first scoring run produced nDCG@10 = 0.2428 — and 9.1% of the returned
results had ever been judged. On the 29 queries that scored zero, 96.9% of the
top-10 was unjudged. An unjudged result is not a proven miss; it is a don't-know,
and counting don't-knows as misses manufactures a low score the same way a
too-shallow pool manufactures a high one.

Standard IR practice is to pool judgements over system output. With a SINGLE
system that pooling is biased IN FAVOUR of the system: anything it returns that
looks plausible can become gold. So this produces a SECOND number, not a
replacement — the strict score (pre-registered gold only) is a lower bound, the
pooled score an upper bound, and the honest claim is the interval.

Judge contract is the one that survived the first pass: the supporting evidence
must be the FIRST 8 WORDS of a sentence, copied exactly, verified by substring.

Read-only on the evaluation copy; writes only its own output.
"""
import json, os, re, sqlite3, sys, time, unicodedata, urllib.request
from concurrent.futures import ThreadPoolExecutor

DB    = os.environ.get("GOLD_DB", "/root/medicoes/2026-10-22-gold/eval.db")
EVAL  = sys.argv[1]
GOLD  = sys.argv[2]
OUT   = sys.argv[3]
KEY   = os.environ["GEMINI_API_KEY"]
MODEL = os.environ.get("GOLD_MODEL", "gemini-2.5-flash-lite")
API   = "https://generativelanguage.googleapis.com/v1beta"
WORKERS = int(os.environ.get("GOLD_WORKERS", "6"))

def call(prompt):
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.0, "maxOutputTokens": 700,
                                 "responseMimeType": "application/json"}}
    req = urllib.request.Request(f"{API}/models/{MODEL}:generateContent?key={KEY}",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    last = None
    for a in range(5):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.load(r)
            t = "".join(p.get("text", "") for p in d["candidates"][0]["content"]["parts"]).strip()
            if t:
                return t
            raise RuntimeError("vazio")
        except Exception as e:
            last = e
            time.sleep(1.5 * (a + 1))
    raise RuntimeError(str(last))

def jload(txt):
    def fix(o):
        if isinstance(o, list):
            return next((x for x in o if isinstance(x, dict)), None)
        return o if isinstance(o, dict) else None
    for att in (txt, re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", txt)):
        for f in (lambda s: json.loads(s, strict=False),
                  lambda s: json.JSONDecoder(strict=False).raw_decode(s.lstrip())[0]):
            try:
                return fix(f(att))
            except Exception:
                pass
        m = re.search(r"[\{\[].*[\}\]]", att, re.S)
        if m:
            try:
                return fix(json.loads(m.group(0), strict=False))
            except Exception:
                pass
    return None

def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()

con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, check_same_thread=False)

P = """PERGUNTA: {q}

TRECHO:
---
{t}
---

1. O TRECHO contém a resposta para a PERGUNTA? Não basta tratar do mesmo assunto.
2. Se sim, copie **apenas as 8 primeiras palavras** da frase do TRECHO que sustenta a resposta,
   exatamente como aparecem, sem reescrever e sem juntar pedaços de lugares diferentes.

Devolva JSON: {{"trecho_responde": true|false, "oito_palavras": "<...>", "motivo": "<uma frase>"}}"""

ev = json.load(open(EVAL, encoding="utf-8"))
gold = {str(g["query_id"]): g for g in
        (json.loads(l) for l in open(GOLD, encoding="utf-8") if l.strip())}
ja = json.load(open(os.environ["GOLD_IDS_EVAL"], encoding="utf-8"))

tarefas = []
for r in ev["rows"]:
    if r.get("ndcg") is None:
        continue
    conhecidos = set(ja.get(str(r["query_id"]), []))
    for cid in r["ranked"]:
        if cid not in conhecidos:
            tarefas.append((r["query_id"], r["query"], cid))
print(f"a julgar: {len(tarefas)} pares (query, chunk) ainda não julgados", flush=True)

def do(t):
    qid, q, cid = t
    row = con.execute("SELECT source_file, chunk_text FROM chunks WHERE id=?", (cid,)).fetchone()
    if not row:
        return {"query_id": qid, "chunk_id": cid, "relevante": False, "motivo": "chunk ausente"}
    try:
        j = jload(call(P.format(q=q, t=(row[1] or "")[:6000]))) or {}
    except Exception as e:
        return {"query_id": qid, "chunk_id": cid, "relevante": False, "erro": str(e)[:120]}
    q8 = (j.get("oito_palavras") or "").strip()
    ok = bool(q8) and len(norm(q8)) >= 12 and norm(q8) in norm(row[1] or "")
    return {"query_id": qid, "chunk_id": cid, "source_file": row[0],
            "trecho_responde": bool(j.get("trecho_responde")), "citacao_confere": ok,
            "relevante": bool(j.get("trecho_responde")) and ok,
            "ancora": q8[:200], "motivo": (j.get("motivo") or "")[:200]}

res = []
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    for i, r in enumerate(ex.map(do, tarefas), 1):
        res.append(r)
        if i % 50 == 0:
            print(f"  {i}/{len(tarefas)}", flush=True)
json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1)
rel = sum(1 for r in res if r.get("relevante"))
err = sum(1 for r in res if r.get("erro"))
naoconf = sum(1 for r in res if r.get("trecho_responde") and not r.get("citacao_confere"))
print(f"\nCOMPLETO: {len(res)} julgados · relevantes {rel} ({100*rel/len(res):.1f}%) · "
      f"disseram que responde mas citação não confere {naoconf} · erros {err}")
