#!/usr/bin/env python3
"""Stage 2 of the PT-BR golden-set repair: the ORACLE FILTER.

A query earns its place only if the answer is in the corpus and not already in
the model's head:

    accept chunk c as gold for query q  iff  answer(q | c) is correct
                                        and  answer(q | nothing) is NOT correct

Without the second leg a golden set scores retrieval on questions the model
answers from general knowledge, and the retriever gets credit for nothing.

Per query: one closed-book answer, one triage call over the deep pool, then one
judgement per shortlisted candidate. The judge must quote the supporting span
VERBATIM from the chunk, and the quote is checked mechanically (normalised
substring) — a judgement whose quote is not in the chunk is DISCARDED, not
trusted. That check is the positive control on the judge itself.

Read-only: reads pool.jsonl and the database in mode=ro, writes only its output.
"""
import json, os, re, sqlite3, sys, time, unicodedata, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor

DB    = os.environ.get("GOLD_DB", "/root/.openclaw/workspace/tools/nox-mem/nox-mem.db")
POOL  = sys.argv[1]
OUT   = sys.argv[2]
KEY   = os.environ["GEMINI_API_KEY"]
MODEL = os.environ.get("GOLD_MODEL", "gemini-2.5-flash-lite")
API   = "https://generativelanguage.googleapis.com/v1beta"
TRIAGE_N  = int(os.environ.get("GOLD_TRIAGE_N", "12"))   # candidatos mostrados na triagem
SHORT_N   = int(os.environ.get("GOLD_SHORT_N", "3"))     # candidatos julgados por query
WORKERS   = int(os.environ.get("GOLD_WORKERS", "6"))

def call(prompt, want_json=True, temp=0.0, max_tokens=1200):
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temp, "maxOutputTokens": max_tokens}}
    if want_json:
        body["generationConfig"]["responseMimeType"] = "application/json"
    data = json.dumps(body).encode()
    req = urllib.request.Request(f"{API}/models/{MODEL}:generateContent?key={KEY}",
                                 data=data, headers={"Content-Type": "application/json"})
    last = None
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.load(r)
            cands = d.get("candidates") or []
            if not cands:
                raise RuntimeError(f"sem candidates: {json.dumps(d)[:200]}")
            parts = cands[0].get("content", {}).get("parts") or []
            txt = "".join(p.get("text", "") for p in parts).strip()
            if not txt:
                raise RuntimeError(f"resposta vazia (finishReason={cands[0].get('finishReason')})")
            return txt
        except Exception as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"gemini falhou 5x: {last}")

def jload(txt):
    """Tolerante de proposito. Os 6 erros da primeira passagem foram TODOS de parsing,
    nao do modelo recusar: caractere de controle cru dentro de string, um segundo
    objeto JSON colado depois do primeiro ("Extra data"), escape invalido, e uma
    lista no lugar de um objeto. Nenhum deles e resposta ruim, sao formas que o
    json.loads estrito nao aceita."""
    def fix(o):
        if isinstance(o, list):
            for x in o:
                if isinstance(x, dict):
                    return x
            return None
        return o if isinstance(o, dict) else None
    for attempt in (txt, re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", txt)):
        try:
            return fix(json.loads(attempt, strict=False))
        except Exception:
            pass
        try:                                   # primeiro objeto, ignora o que vier depois
            return fix(json.JSONDecoder(strict=False).raw_decode(attempt.lstrip())[0])
        except Exception:
            pass
        m = re.search(r"[\{\[].*[\}\]]", attempt, re.S)
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
    r = con.execute("SELECT id, source_file, chunk_type, chunk_text FROM chunks WHERE id=?",
                    (cid,)).fetchone()
    return None if r is None else {"id": r[0], "source_file": r[1], "type": r[2], "text": r[3]}

CLOSED = """Responda à pergunta abaixo com o que você já sabe. Não há documento nenhum.
Se não souber, ou se a resposta depender de um sistema interno específico que você não conhece,
responda exatamente NAO SEI.

PERGUNTA: {q}

Devolva JSON: {{"resposta": "<sua resposta ou NAO SEI>"}}"""

TRIAGE = """Abaixo há uma PERGUNTA e TRECHOS numerados de uma base de memória interna.
Diga quais trechos contêm, de fato, a informação que responde à pergunta.
Não escolha trecho que só fale do mesmo assunto: tem de conter a resposta.
Se nenhum contiver, devolva lista vazia.

PERGUNTA: {q}

{trechos}

Devolva JSON: {{"ids": [<id>, ...]}} com no máximo {n} ids, do melhor para o pior."""

JUDGE = """Você está auditando uma pergunta candidata a entrar num conjunto de avaliação.

PERGUNTA: {q}

TRECHO (única fonte permitida):
---
{texto}
---

RESPOSTA SEM FONTE (o que um modelo respondeu sem ver trecho nenhum):
---
{sem}
---

Faça três coisas:
1. Responda à pergunta usando APENAS o TRECHO.
2. Copie, VERBATIM e sem alterar um caractere, o pedaço do TRECHO que sustenta a sua resposta.
   Se o TRECHO não sustenta resposta nenhuma, deixe a citação vazia.
3. Diga se a RESPOSTA SEM FONTE já contém, em substância, a mesma resposta que o TRECHO dá.
   "NAO SEI", resposta vaga, ou resposta sobre outra coisa NÃO contam como já contendo.

Devolva JSON:
{{"resposta_com_fonte": "<...>",
  "citacao_verbatim": "<trecho copiado ou string vazia>",
  "trecho_responde": true|false,
  "sem_fonte_ja_responde": true|false,
  "motivo": "<uma frase>"}}"""

rows = [json.loads(l) for l in open(POOL, encoding="utf-8") if l.strip()]
done = set()
if os.path.exists(OUT):
    for l in open(OUT, encoding="utf-8"):
        try:
            done.add(json.loads(l)["query_id"])
        except Exception:
            pass
rows = [r for r in rows if r["query_id"] not in done]
print(f"a processar: {len(rows)} queries ({len(done)} já feitas)", flush=True)

def do_query(r):
    qid, q = r["query_id"], r["query"]
    rec = {"query_id": qid, "query": q, "category": r.get("category"),
           "difficulty": r.get("difficulty"), "old_expected": r.get("old_expected"),
           "pool_size": len(r["pool"]), "judged": [], "gold": [], "error": None}
    try:
        sem = (jload(call(CLOSED.format(q=q))) or {}).get("resposta", "").strip()
        rec["closed_book"] = sem

        cands = [c for c in (chunk(i) for i in r["pool"][:TRIAGE_N]) if c]
        trechos = "\n\n".join(
            f"[{c['id']}] ({c['source_file']})\n{(c['text'] or '')[:700]}" for c in cands)
        tri = jload(call(TRIAGE.format(q=q, trechos=trechos, n=SHORT_N))) or {}
        short = [i for i in (tri.get("ids") or []) if any(c["id"] == i for c in cands)][:SHORT_N]
        rec["triage_ids"] = short
        if not short:
            rec["verdict"] = "sem_fonte_no_pool"
            return rec

        for cid in short:
            c = chunk(cid)
            j = jload(call(JUDGE.format(q=q, texto=(c["text"] or "")[:6000], sem=sem or "NAO SEI"))) or {}
            quote = (j.get("citacao_verbatim") or "").strip()
            # controle do juiz: a citação tem de estar MESMO no trecho
            quote_ok = bool(quote) and norm(quote)[:160] in norm(c["text"])
            entry = {"chunk_id": cid, "source_file": c["source_file"],
                     "trecho_responde": bool(j.get("trecho_responde")),
                     "sem_fonte_ja_responde": bool(j.get("sem_fonte_ja_responde")),
                     "citacao_verbatim": quote[:400], "citacao_confere": quote_ok,
                     "motivo": (j.get("motivo") or "")[:300]}
            rec["judged"].append(entry)
            if entry["trecho_responde"] and not entry["sem_fonte_ja_responde"] and quote_ok:
                rec["gold"].append({"chunk_id": cid, "source_file": c["source_file"],
                                    "anchor": quote[:400]})
        if rec["gold"]:
            rec["verdict"] = "aceita"
        elif any(e["sem_fonte_ja_responde"] for e in rec["judged"]):
            rec["verdict"] = "rejeitada_modelo_ja_sabe"
        elif any(e["trecho_responde"] and not e["citacao_confere"] for e in rec["judged"]):
            rec["verdict"] = "descartada_citacao_nao_confere"
        else:
            rec["verdict"] = "sem_fonte_no_pool"
    except Exception as e:
        rec["error"] = f"{type(e).__name__}: {e}"
        rec["verdict"] = "erro"
    return rec

out = open(OUT, "a", encoding="utf-8")
n = 0
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    for rec in ex.map(do_query, rows):
        out.write(json.dumps(rec, ensure_ascii=False) + "\n")
        out.flush()
        n += 1
        print(f"[{n}/{len(rows)}] Q{rec['query_id']:<4} {rec['verdict']:<32} gold={len(rec['gold'])}",
              flush=True)
out.close()
print(f"\nCOMPLETO: {n} de {len(rows)} processadas nesta execução")
