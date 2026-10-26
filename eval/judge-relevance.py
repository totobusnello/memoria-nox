#!/usr/bin/env python3
"""The canonical relevance judge for the PT-BR golden set: bounded, and with no
citation leg.

This replaces the judging contract of `audits/2026-10-22-gold-pooling.py` for
every future pooling pass. Two things change, and the second is the point.

1. IT JUDGES THE WHOLE TOP-K, not a sample. It reads the scorer's own output
   (`run-gold-eval.mjs` writes `rows[].ranked`) and emits one label per
   (query, chunk) pair that any ranking returned, plus the pre-registered gold.
   The first scoring run reported nDCG@10 = 0.2428 with 9.1% of the top-10 ever
   judged, and on the 29 zero-scoring queries 96.9% of the top-10 was unjudged.
   An unjudged result is a don't-know, not a proven miss, and counting
   don't-knows as misses manufactures a low score. Judging the whole list is
   cheap enough that sampling is no longer a defensible economy: 542 pairs cost
   US$ 0.0312 and 12 seconds on 2026-10-26.

2. THERE IS NO SECOND LEG, deliberately. The old label was
   `relevante = trecho_responde AND citacao_confere`, where the second term
   required the first 8 words of the supporting sentence to be a normalised
   substring of the chunk. Measured on 2026-10-26 over 510 pairs, that check
   costs 0.105 of kappa (judge vs judge 0.5458; judge vs judge+check 0.4412),
   and the stratum it REJECTED scores HIGHER on the level scale than the
   stratum it accepted (2.17 against 1.88, n=49 vs n=106). It partitions by
   copyable formatting — markdown table pipes, `<u>` wrapping, an escaped currency sign —
   not by relevance. A mechanical predicate is not disqualified for being
   mechanical: the abstention detector, five substrings wide, agrees with this
   judge at kappa 0.794. It is disqualified for being uncalibrated against the
   property it stands in for.

   The check is NOT retired where the claim it tests is itself about a
   quotation: the two-legged gold oracle (`2026-10-22-gold-oracle.py`) and KG
   faithfulness (`2026-10-23-kg-s1-conferidor-reproduzivel.md`) still use it,
   and should. There the quote is the object of the measurement, not a proxy
   for relevance.

What replaces it. The judge is OpenAI's Decisions API, which has no free-text
field at all, so the defect where the prose contradicts the boolean cannot
occur by construction (measured 2026-10-22: a judge wrote that the premise was
false and set the flag to true; only the flag is read). It returns a calibrated
probability for the predicate and a distribution over four ordered levels whose
criteria each name an observable property of the text — the first draft had
levels that restated the predicate and answered with confidence 0.16.

The threshold is an input, not a constant: p > 0.3 / 0.5 / 0.7 moved nDCG@10
over the same labels to 0.5085 / 0.4764 / 0.4406. Whatever is published states
which one it used.

Isolation. Opens the database read-only, calls no search path, so no telemetry
row is written and no access_count is bumped (access_count feeds salience,
which is part of what any ranking metric scores). Every chunk text is read
SERIALLY before any thread exists: one sqlite3 connection shared across 8
workers died at pair ~300 of 516 on 2026-10-26 after passing a 30-pair smoke.

Usage:
    OPENAI_API_KEY=... python3 eval/judge-relevance.py \
        <score.json from run-gold-eval.mjs> <golden-queries-v2.jsonl> <out.json>

    JUDGE_MODE=smoke (default) judges JUDGE_SMOKE_N pairs first — always run it,
    it is what caught the bad level rubric before any money was spent.
"""
import json, os, sqlite3, sys, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor

SCORE   = sys.argv[1]
GOLD    = sys.argv[2]
OUT     = sys.argv[3]
DB      = os.environ.get("NOX_DB_PATH",
                         "/root/.openclaw/workspace/tools/nox-mem/nox-mem.db")
KEY     = os.environ["OPENAI_API_KEY"]
MODEL   = os.environ.get("JUDGE_MODEL", "gpt-6-luna")
API     = "https://api.openai.com/v1/decisions"
WORKERS = int(os.environ.get("JUDGE_WORKERS", "6"))
MODE    = os.environ.get("JUDGE_MODE", "smoke")
SMOKE_N = int(os.environ.get("JUDGE_SMOKE_N", "30"))
THRESH  = float(os.environ.get("JUDGE_THRESHOLD", "0.5"))
CHARS   = int(os.environ.get("JUDGE_CHUNK_CHARS", "6000"))

# Palavra por palavra a pergunta 1 do pooling de 22/10, para que o rotulo novo
# seja comparavel ao antigo: a entrada tem de ser igual antes de a pergunta ser.
PREDICATE = ("O TRECHO contem a resposta para esta PERGUNTA: {q}\n"
             "Nao basta tratar do mesmo assunto: tem de conter a resposta.")

LEVEL_Q = "Qual destes descreve melhor o TRECHO em relacao a PERGUNTA: {q}"
LEVELS = [
    {"label": "fora",    "description": "O TRECHO nao trata do assunto da PERGUNTA."},
    {"label": "vizinho", "description": "O TRECHO trata do mesmo assunto e usa os mesmos "
                                        "termos, mas nenhuma frase dele responde a PERGUNTA."},
    {"label": "parcial", "description": "Alguma frase do TRECHO responde em parte, faltando "
                                        "um dado que a PERGUNTA pede."},
    {"label": "completo","description": "Alguma frase do TRECHO responde a PERGUNTA por inteiro."},
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
            last = f"HTTP {e.code}: {e.read().decode()[:200]}"
            if e.code in (400, 401, 403, 404):          # nao se resolve repetindo
                break
            time.sleep(2 * (a + 1))
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
            time.sleep(2 * (a + 1))
    raise RuntimeError(str(last))

# ------------------------------------------------- que pares existem para julgar
score = json.load(open(SCORE, encoding="utf-8"))
qtext = {}
for l in open(GOLD, encoding="utf-8"):
    if l.strip():
        g = json.loads(l)
        qtext[g["query_id"]] = g["query"]

pares, origem = [], {}
for r in score.get("rows", []):
    qid = r.get("query_id")
    if qid not in qtext or r.get("skipped") or r.get("error"):
        continue
    for cid in r.get("ranked", []):
        pares.append((qid, cid)); origem.setdefault((qid, cid), set()).add("top_k")
    for cid in r.get("gold_ids", []):
        pares.append((qid, cid)); origem.setdefault((qid, cid), set()).add("gold")
pares = sorted(set(pares))
print(f"pares distintos a julgar: {len(pares)} "
      f"(top-k {sum(1 for p in pares if 'top_k' in origem[p])} · "
      f"gold {sum(1 for p in pares if 'gold' in origem[p])})", flush=True)

if MODE == "smoke":
    pares = pares[:SMOKE_N]
    print(f"modo=smoke · julgando {len(pares)}", flush=True)

# ------------------------------------------------- fase 1, SERIAL: so banco
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
textos = {}
for cid in sorted({c for _, c in pares}):
    row = con.execute("SELECT source_file, chunk_text FROM chunks WHERE id=?", (cid,)).fetchone()
    textos[cid] = None if row is None else (row[0], (row[1] or "")[:CHARS])
con.close()
faltam = [c for c, v in textos.items() if v is None]
print(f"textos lidos: {len(textos)-len(faltam)} de {len(textos)} chunks"
      + (f" · AUSENTES: {len(faltam)} (pontuam 0 e ficam declarados)" if faltam else ""), flush=True)

# ------------------------------------------------- fase 2, PARALELA: so rede
def do(par):
    qid, cid = par
    out = {"query_id": qid, "chunk_id": cid, "origem": sorted(origem[par])}
    got = textos.get(cid)
    if got is None:
        out["erro"] = "chunk ausente no banco"
        return out
    out["source_file"] = got[0]
    try:
        d = decide(got[1], qtext[qid])
    except Exception as e:
        out["erro"] = str(e)[:200]
        return out
    ans = {a["name"]: a for a in d.get("answers", [])}
    p = ans.get("contem_resposta", {}).get("probability")
    s = ans.get("nivel", {})
    out.update({
        "prob_contem_resposta": p,
        "relevante": (None if p is None else p > THRESH),
        "nivel_score": s.get("score"),
        "nivel_confidence": s.get("confidence"),
        "nivel_probs": {x["label"]: x["probability"] for x in s.get("probabilities", [])},
        "input_tokens": (d.get("usage") or {}).get("input_tokens"),
    })
    return out

res, t0 = [], time.time()
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    for i, r in enumerate(ex.map(do, pares), 1):
        res.append(r)
        if i % 50 == 0 or i == len(pares):
            print(f"  {i}/{len(pares)}  {time.time()-t0:.0f}s", flush=True)

ok = [r for r in res if not r.get("erro")]
toks = sum(r.get("input_tokens") or 0 for r in ok)
meta = {"judged_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "judge": MODEL, "threshold": THRESH, "chunk_chars": CHARS,
        "citation_check": False,
        "citation_check_note": "retired as a relevance gate on 2026-10-26: costs 0.105 of kappa "
                               "and partitions by copyable formatting (audits/2026-10-26-bounded-judge.md)",
        "n_pairs": len(res), "n_judged": len(ok), "n_errors": len(res) - len(ok),
        "input_tokens": toks, "usd": round(toks / 1e6 * 0.10, 4),
        "seconds": round(time.time() - t0, 1)}
json.dump({"meta": meta, "rows": res}, open(OUT, "w"), ensure_ascii=False, indent=1)
print("\n" + json.dumps(meta, ensure_ascii=False, indent=1))
rel = [r for r in ok if r["relevante"]]
print(f"\nrelevantes a p>{THRESH}: {len(rel)} de {len(ok)} julgados "
      f"({len(rel)/max(1,len(ok))*100:.1f}%)")
