#!/usr/bin/env python3
"""A BOUNDED judge for the pooled relevance labels, and what it does to nDCG.

Why this exists. Every relevance label behind the published interval
nDCG@10 in [0.2428, 0.5114] was written by `gemini-2.5-flash-lite` asked for
prose plus a boolean. Two defects of that shape are measured, not suspected:
the prose and the field can disagree and only the field is read
(`2026-10-22` negatives), and 34.5% of the spans it called VERBATIM were not in
the chunk. Inter-judge agreement on the pooled cell was kappa +0.400 over 20
items — moderate at best, and it over-marks relevance (6/10 of its YES
confirmed). So the interval rests on labels one reader in two would redo, and
that was established on a SAMPLE of 20 of the 518 pairs.

What changes here. The same 518 (query, chunk) pairs are re-judged by a judge
that cannot write prose at all: OpenAI's Decisions API (`gpt-6-luna`), which
returns a probability for a predicate and a distribution over ordered levels.
There is no free-text field, so the class of defect where the sentence
contradicts the field cannot occur by construction.

EQUALISED INPUT, which is the whole point. The first judge saw
`chunk_text[:6000]`; so does this one, from the same ids, with the same
question wording. Showing a second rater less context than the first fabricates
disagreement asymmetrically, in the direction of "unsupported" — measured on
2026-10-22, where 5 of 8 "no" verdicts were produced by missing text.

WHAT IS AND IS NOT COMPARABLE. The old published label is
`relevante = trecho_responde AND citacao_confere`: a model judgement AND a
mechanical substring check. This judge produces no quote, so it has no second
leg. It is therefore comparable to `trecho_responde` (judge vs judge) and NOT
to `relevante` (judge vs judge+check). Both comparisons are reported, because
the difference between them is the check's contribution — and on the KG audit
the check, not the model, was what rejected 8 of 9 disagreements.

Levels. The first smoke used three levels whose adjacent criteria were not
distinct ("contains the answer" restated the predicate) and the model answered
with confidence 0.16 while the predicate said 1.0. Rewritten so each level
names an observable property of the text.

Read-only: opens the live database in mode=ro, calls no search path (so no
telemetry row, no access_count bump), writes only its own output file.

One sqlite3 connection shared across worker threads died with
`InterfaceError: bad parameter or other API misuse` at pair ~300 of 516 — and
passed the 30-pair smoke, which is how that class of bug survives. The fix is
not a per-thread connection: the two phases have nothing to do with each other.
Every chunk text is read SERIALLY up front (438 distinct chunks, ~2.6 MB), and
only the network calls fan out.
"""
import json, os, re, sqlite3, sys, time, unicodedata, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor

DB      = os.environ.get("GOLD_DB", "/root/.openclaw/workspace/tools/nox-mem/nox-mem.db")
POOLING = sys.argv[1]
OUT     = sys.argv[2]
KEY     = os.environ["OPENAI_API_KEY"]
MODEL   = os.environ.get("JUDGE_MODEL", "gpt-6-luna")
API     = "https://api.openai.com/v1/decisions"
WORKERS = int(os.environ.get("JUDGE_WORKERS", "6"))
MODE    = os.environ.get("JUDGE_MODE", "smoke")        # smoke | full
SMOKE_N = int(os.environ.get("JUDGE_SMOKE_N", "10"))   # por estrato

# Identica, palavra por palavra, a pergunta 1 do gold-pooling.py de 22/10.
PREDICATE = ("O TRECHO contem a resposta para esta PERGUNTA: {q}\n"
             "Nao basta tratar do mesmo assunto: tem de conter a resposta.")

LEVEL_Q = "Qual destes descreve melhor o TRECHO em relacao a PERGUNTA: {q}"
LEVELS = [
    {"label": "fora",     "description": "O TRECHO nao trata do assunto da PERGUNTA."},
    {"label": "vizinho",  "description": "O TRECHO trata do mesmo assunto e usa os mesmos termos, "
                                         "mas nenhuma frase dele responde a PERGUNTA."},
    {"label": "parcial",  "description": "Alguma frase do TRECHO responde em parte, faltando um "
                                         "dado que a PERGUNTA pede."},
    {"label": "completo", "description": "Alguma frase do TRECHO responde a PERGUNTA por inteiro."},
]

def decide(texto, q):
    body = {"model": MODEL, "input": texto, "questions": [
        {"type": "predicate", "name": "contem_resposta",
         "instructions": PREDICATE.format(q=q)},
        {"type": "score", "name": "nivel", "instructions": LEVEL_Q.format(q=q),
         "levels": LEVELS}]}
    req = urllib.request.Request(API, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {KEY}"})
    last = None
    for a in range(5):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            detail = e.read().decode()[:200]
            last = f"HTTP {e.code}: {detail}"
            if e.code in (400, 401, 403, 404):      # nao se resolve repetindo
                break
            time.sleep(2 * (a + 1))
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
            time.sleep(2 * (a + 1))
    raise RuntimeError(str(last))

def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()

# Sem check_same_thread=False de proposito: a conexao nunca sai da thread principal.
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)

pairs = json.load(open(POOLING, encoding="utf-8"))
# A query vem do golden set, nao do pooling.json (que so guarda o id).
GOLD = os.environ.get("GOLD_FILE", "/root/medicoes/2026-10-22-gold/golden-queries-v2.jsonl")
qtext = {}
for l in open(GOLD, encoding="utf-8"):
    if l.strip():
        g = json.loads(l)
        qtext[g["query_id"]] = g["query"]

def stratum(r):
    if r.get("erro"):                                        return "erro_antigo"
    if r.get("relevante"):                                   return "A_relevante"
    if r.get("trecho_responde"):                             return "B_responde_citacao_falhou"
    return "C_nao_responde"

tasks = []
for r in pairs:
    if r["query_id"] not in qtext or r.get("erro"):
        continue
    tasks.append(r)

if MODE == "smoke":
    by = {}
    for r in tasks:
        by.setdefault(stratum(r), []).append(r)
    sel = []
    for k in sorted(by):
        sel += sorted(by[k], key=lambda r: (r["query_id"], r["chunk_id"]))[:SMOKE_N]
    tasks = sel

print(f"modo={MODE} · pares a julgar: {len(tasks)}", flush=True)
for k in sorted({stratum(r) for r in tasks}):
    print(f"  {k}: {sum(1 for r in tasks if stratum(r) == k)}", flush=True)

# Fase 1, SERIAL: todo o banco sai daqui, antes de qualquer thread existir.
textos = {}
for cid in sorted({r["chunk_id"] for r in tasks}):
    row = con.execute("SELECT source_file, chunk_text FROM chunks WHERE id=?", (cid,)).fetchone()
    textos[cid] = None if row is None else (row[0], (row[1] or "")[:6000])
con.close()
print(f"textos lidos: {sum(1 for v in textos.values() if v)} de {len(textos)} chunks", flush=True)

# Fase 2, PARALELA: so rede.
def do(r):
    cid = r["chunk_id"]
    got = textos.get(cid)
    out = {"query_id": r["query_id"], "chunk_id": cid, "stratum": stratum(r),
           "old_trecho_responde": bool(r.get("trecho_responde")),
           "old_citacao_confere": bool(r.get("citacao_confere")),
           "old_relevante": bool(r.get("relevante"))}
    if got is None:
        out["erro"] = "chunk ausente no banco de hoje"
        return out
    sf, texto = got
    if r.get("source_file") and sf != r["source_file"]:
        out["erro"] = f"source_file divergiu: {sf}"
        return out
    try:
        d = decide(texto, qtext[r["query_id"]])
    except Exception as e:
        out["erro"] = str(e)[:200]
        return out
    ans = {a["name"]: a for a in d.get("answers", [])}
    p = ans.get("contem_resposta", {})
    s = ans.get("nivel", {})
    out.update({
        "prob_contem_resposta": p.get("probability"),
        "nivel_score": s.get("score"),
        "nivel_confidence": s.get("confidence"),
        "nivel_probs": {x["label"]: x["probability"] for x in s.get("probabilities", [])},
        "input_tokens": (d.get("usage") or {}).get("input_tokens"),
    })
    return out

res = []
t0 = time.time()
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    for i, r in enumerate(ex.map(do, tasks), 1):
        res.append(r)
        if i % 25 == 0 or i == len(tasks):
            print(f"  {i}/{len(tasks)}  {time.time()-t0:.0f}s", flush=True)
json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1)

ok = [r for r in res if not r.get("erro")]
toks = sum(r.get("input_tokens") or 0 for r in ok)
print(f"\nCOMPLETO: {len(ok)} julgados · {len(res)-len(ok)} erros · "
      f"{toks} input tokens (~US$ {toks/1e6*0.10:.4f}) · {time.time()-t0:.0f}s")
for k in sorted({r["stratum"] for r in ok}):
    g = [r for r in ok if r["stratum"] == k]
    pr = [r["prob_contem_resposta"] for r in g if r["prob_contem_resposta"] is not None]
    nv = [r["nivel_score"] for r in g if r["nivel_score"] is not None]
    cf = [r["nivel_confidence"] for r in g if r["nivel_confidence"] is not None]
    med = lambda a: sorted(a)[len(a)//2] if a else None
    print(f"  {k:<28} n={len(g):<4} prob>0.5: {sum(1 for x in pr if x > 0.5)}/{len(pr)}"
          f"  prob_mediana={med(pr)}  nivel_mediano={med(nv)}  conf_mediana={med(cf)}")
