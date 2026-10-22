#!/usr/bin/env python3
"""Second judging pass over the queries whose first-pass quote did not verify.

First pass asked for a free-length verbatim span and 34.5% of the spans were not
in the chunk: they matched for 13-53 characters and drifted into paraphrase. The
hypothesis is that the LENGTH is the problem — a long span invites rewriting.

This pass asks for the FIRST 8 WORDS of the supporting sentence, nothing more,
and verifies the same way. If the short span verifies where the long one did not,
the defect was the span length, not the judge's grounding. If it still fails, the
query is left out: a quote that cannot be produced is not evidence.

Read-only on the database (mode=ro); writes only its own output file.
"""
import json, os, re, sqlite3, sys, time, unicodedata, urllib.request
from concurrent.futures import ThreadPoolExecutor

DB    = os.environ.get("GOLD_DB", "/root/.openclaw/workspace/tools/nox-mem/nox-mem.db")
POOL  = sys.argv[1]
PREV  = sys.argv[2]
OUT   = sys.argv[3]
KEY   = os.environ["GEMINI_API_KEY"]
MODEL = os.environ.get("GOLD_MODEL", "gemini-2.5-flash-lite")
API   = "https://generativelanguage.googleapis.com/v1beta"

def call(prompt):
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.0, "maxOutputTokens": 900,
                                 "responseMimeType": "application/json"}}
    req = urllib.request.Request(f"{API}/models/{MODEL}:generateContent?key={KEY}",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    last = None
    for a in range(5):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.load(r)
            parts = d["candidates"][0]["content"]["parts"]
            t = "".join(p.get("text", "") for p in parts).strip()
            if t:
                return t
            raise RuntimeError("vazio")
        except Exception as e:
            last = e
            time.sleep(2 * (a + 1))
    raise RuntimeError(f"gemini falhou: {last}")

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
def chunk(cid):
    r = con.execute("SELECT id, source_file, chunk_text FROM chunks WHERE id=?", (cid,)).fetchone()
    return None if r is None else {"id": r[0], "source_file": r[1], "text": r[2]}

P = """PERGUNTA: {q}

TRECHO:
---
{t}
---

RESPOSTA SEM FONTE (o que um modelo respondeu sem ver trecho nenhum):
---
{sem}
---

1. O TRECHO contém a resposta para a PERGUNTA?
2. Se sim, copie **apenas as 8 primeiras palavras** da frase do TRECHO que sustenta a resposta.
   Exatamente como aparecem, sem reescrever, sem juntar pedaços de lugares diferentes,
   sem acrescentar reticências. Oito palavras, nada mais.
3. A RESPOSTA SEM FONTE já contém, em substância, a mesma resposta que o TRECHO dá?
   "NAO SEI", resposta vaga ou sobre outra coisa NÃO contam como já contendo.

Devolva JSON:
{{"trecho_responde": true|false, "oito_palavras": "<...>", "sem_fonte_ja_responde": true|false,
  "motivo": "<uma frase>"}}"""

pool = {json.loads(l)["query_id"]: json.loads(l) for l in open(POOL, encoding="utf-8") if l.strip()}
prev = [json.loads(l) for l in open(PREV, encoding="utf-8") if l.strip()]
alvo = [r for r in prev if r["verdict"] == "descartada_citacao_nao_confere"]
print(f"segundo passe em {len(alvo)} queries", flush=True)

def do(r):
    qid = r["query_id"]
    rec = {"query_id": qid, "query": r["query"], "category": r["category"],
           "difficulty": r["difficulty"], "old_expected": r["old_expected"],
           "pool_size": r["pool_size"], "closed_book": r.get("closed_book", ""),
           "judged": [], "gold": [], "error": None, "repass": True}
    try:
        for e in r["judged"]:
            c = chunk(e["chunk_id"])
            if not c:
                continue
            j = jload(call(P.format(q=r["query"], t=(c["text"] or "")[:6000],
                                    sem=rec["closed_book"] or "NAO SEI"))) or {}
            q8 = (j.get("oito_palavras") or "").strip()
            ok = bool(q8) and len(norm(q8)) >= 12 and norm(q8) in norm(c["text"])
            ent = {"chunk_id": c["id"], "source_file": c["source_file"],
                   "trecho_responde": bool(j.get("trecho_responde")),
                   "sem_fonte_ja_responde": bool(j.get("sem_fonte_ja_responde")),
                   "citacao_verbatim": q8[:200], "citacao_confere": ok,
                   "motivo": (j.get("motivo") or "")[:300],
                   "primeira_passagem_falhou": True}
            rec["judged"].append(ent)
            if ent["trecho_responde"] and not ent["sem_fonte_ja_responde"] and ok:
                rec["gold"].append({"chunk_id": c["id"], "source_file": c["source_file"],
                                    "anchor": q8[:200]})
        rec["verdict"] = ("aceita" if rec["gold"]
                          else "descartada_citacao_nao_confere"
                          if any(e["trecho_responde"] and not e["citacao_confere"] for e in rec["judged"])
                          else "sem_fonte_no_pool")
    except Exception as ex:
        rec["error"] = f"{type(ex).__name__}: {ex}"
        rec["verdict"] = "erro"
    return rec

out = open(OUT, "w", encoding="utf-8")
n_ac = 0
with ThreadPoolExecutor(max_workers=5) as ex:
    for rec in ex.map(do, alvo):
        out.write(json.dumps(rec, ensure_ascii=False) + "\n")
        out.flush()
        n_ac += rec["verdict"] == "aceita"
        print(f"  Q{rec['query_id']:<4} {rec['verdict']:<32} gold={len(rec['gold'])}", flush=True)
out.close()
print(f"\nCOMPLETO: {len(alvo)} reprocessadas, {n_ac} agora aceitas")
