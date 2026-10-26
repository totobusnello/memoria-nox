#!/usr/bin/env python3
"""Was the abstention label measuring abstention? A bounded second reader.

Why this exists. The item-8 baseline — abstention 0.6957 on 23 verified
negatives against 0.2000 on 25 positives, gap 0.4957 — is the one number from
2026-10-22 that the inter-judge study never sampled, and it is the only one of
the four whose label was never written by a model at all. `eval/run-abstention.mjs`
decides it mechanically:

    s.includes("i have no memory matches for this question")
      || s.includes("não tenho") || s.includes("nao tenho")
      || s.includes("não há informação") || s.includes("nao ha informacao")

Five substrings standing in for a semantic property. That is the same shape as
the 8-word citation check, which on 2026-10-26 was measured to cost 0.105 of
kappa and to partition by copyable formatting rather than by relevance. A
mechanical predicate is not disqualified by being mechanical — it is
disqualified by not being calibrated, and this one never was.

One failure is already visible by eye in the published rows. For the negative
`tier_decay` the system answered "O `tier_decay` não é explicitamente explicado
no contexto fornecido" — a declared absence, which the detector scored
abstained=false because none of its five substrings appear. So 0.6957 is a
FLOOR on the negatives, not an estimate, and the direction of the error is
known before any model is called.

EQUALISED INPUT, and the control that establishes it. The detector read the
whole answer; the artifact stored `answer_head`, the first 180 characters. 14 of
48 heads sit at that ceiling. Showing a second rater less context than the
first fabricates disagreement asymmetrically (measured 2026-10-22: 5 of 8 "no"
verdicts came from missing text), so the comparison has to prove the input is
equal before it reports a kappa. The proof is free: re-run the detector against
the HEAD. Where it reproduces the stored label, the substring that fired it lies
inside the head and this judge sees the same evidence. Where it does not, the
head is missing what the detector acted on, and that row is reported separately
instead of being folded into the headline number.

What the judge adds that the binary could not. On a negative, "did not abstain"
hides the distinction that matters for the product: the published rows contain
`embed_cache_ttl` answered as "O TTL padrão para o cache de embeddings é de 24
horas [chunk_5]" — a parameter that does not exist, asserted as fact, with a
citation attached. That is the guard-protects-the-citation-not-the-claim defect,
and no abstention flag can see it. So the judge is asked a second predicate
(does the answer assert a concrete datum as recorded fact?) and an ordered level
scale, which together separate a clean refusal from a refusal that volunteers
neighbouring data from an outright fabrication.

Read-only: reads one JSON artifact, calls no search path, touches no database.
"""
import json, os, re, sys, time, unicodedata, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor

SRC     = sys.argv[1]
OUT     = sys.argv[2]
KEY     = os.environ["OPENAI_API_KEY"]
MODEL   = os.environ.get("JUDGE_MODEL", "gpt-6-luna")
API     = "https://api.openai.com/v1/decisions"
WORKERS = int(os.environ.get("JUDGE_WORKERS", "6"))
MODE    = os.environ.get("JUDGE_MODE", "smoke")
SMOKE_N = int(os.environ.get("JUDGE_SMOKE_N", "3"))

# As taxas publicadas em audits/2026-10-22-*.md. O recomputador tem de reproduzi-las
# a partir das linhas antes de qualquer numero novo ser interpretavel.
PUB = {"negative": 0.6957, "positive": 0.2000}

# ---------------------------------------------------------------- o detector
# Replica verbatim o `abstained()` de eval/run-abstention.mjs. Nao "melhorado":
# o objeto da medicao e este predicado, exatamente como rodou.
CANON = "i have no memory matches for this question"
def detector(t):
    s = (t or "").lower()
    return (CANON in s or "não tenho" in s or "nao tenho" in s
            or "não há informação" in s or "nao ha informacao" in s)

# ---------------------------------------------------------------- o juiz
DECLARA = ("A RESPOSTA declara, sobre esta PERGUNTA, que a memoria nao tem a informacao "
           "pedida: {q}\nConta como declarar ausencia qualquer frase que diga que o dado "
           "nao esta no contexto, nao foi encontrado ou nao existe nos registros, com "
           "qualquer redacao.")

AFIRMA  = ("A RESPOSTA apresenta algum dado concreto (numero, nome, prazo, valor, regra) "
           "como se fosse fato registrado na memoria, respondendo a esta PERGUNTA: {q}")

LEVEL_Q = "Qual destes descreve melhor a RESPOSTA, dada a PERGUNTA: {q}"
LEVELS = [
    {"label": "recusa_seca",      "description": "A RESPOSTA diz que a informacao nao esta "
                                                 "disponivel e nao apresenta nenhum dado."},
    {"label": "recusa_com_vizinho","description": "A RESPOSTA diz que a informacao pedida nao "
                                                 "esta disponivel e, alem disso, apresenta dados "
                                                 "de um assunto proximo."},
    {"label": "responde_com_ressalva","description": "A RESPOSTA apresenta dados como resposta a "
                                                 "PERGUNTA e tambem registra que parte do que foi "
                                                 "pedido esta faltando."},
    {"label": "responde_seco",    "description": "A RESPOSTA apresenta dados como resposta a "
                                                 "PERGUNTA sem registrar que falte qualquer "
                                                 "informacao."},
]

def decide(resposta, q):
    body = {"model": MODEL,
            "input": f"RESPOSTA DO SISTEMA:\n---\n{resposta}\n---",
            "questions": [
                {"type": "predicate", "name": "declara_ausencia",
                 "instructions": DECLARA.format(q=q)},
                {"type": "predicate", "name": "afirma_fato",
                 "instructions": AFIRMA.format(q=q)},
                {"type": "score", "name": "nivel",
                 "instructions": LEVEL_Q.format(q=q), "levels": LEVELS}]}
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

# ---------------------------------------------------------------- controle 1
rows = json.load(open(SRC, encoding="utf-8"))["rows"]
pub  = json.load(open(SRC, encoding="utf-8"))["summary"]

falhas = []
for kind, esperado in PUB.items():
    g = [r for r in rows if r["kind"] == kind and not r["error"]]
    got = round(sum(1 for r in g if r["abstained"]) / len(g), 4)
    print(f"controle · {kind}: recomputado {got} vs publicado {esperado}")
    if abs(got - esperado) > 0.0005:
        falhas.append(f"{kind} {got} != {esperado}")
if falhas:
    print("\n*** CONTROLE FALHOU — nao reproduzo a linha de base publicada:")
    for f in falhas:
        print("   ", f)
    print("Nenhum numero novo e interpretavel enquanto isto nao fecha.")
    sys.exit(1)

# ---------------------------------------------------------------- controle 2
# Entrada igualada: o detector reaplicado ao HEAD reproduz o rotulo que ele
# escreveu sobre o texto inteiro?
for r in rows:
    r["det_no_head"] = detector(r["answer_head"])
    r["entrada_igualada"] = (r["det_no_head"] == r["abstained"])
    r["head_no_teto"] = len(r["answer_head"]) >= 179

ig  = [r for r in rows if r["entrada_igualada"]]
nig = [r for r in rows if not r["entrada_igualada"]]
print(f"\nentrada igualada: {len(ig)} de {len(rows)}  ·  nao igualada: {len(nig)}")
for r in nig:
    print(f"   NAO IGUALADA [{r['id']}] gravado={r['abstained']} no_head={r['det_no_head']} "
          f"teto={r['head_no_teto']}")

tasks = rows
if MODE == "smoke":
    sel = []
    for kind in ("negative", "positive"):
        for ab in (True, False):
            g = [r for r in rows if r["kind"] == kind and r["abstained"] == ab]
            sel += g[:SMOKE_N]
    tasks = sel
print(f"\nmodo={MODE} · a julgar: {len(tasks)}", flush=True)

def do(r):
    out = {k: r[k] for k in ("kind", "id", "query", "abstained", "retrieval_count",
                             "citations", "answer_head", "det_no_head",
                             "entrada_igualada", "head_no_teto")}
    try:
        d = decide(r["answer_head"], r["query"])
    except Exception as e:
        out["erro"] = str(e)[:200]
        return out
    ans = {a["name"]: a for a in d.get("answers", [])}
    s = ans.get("nivel", {})
    out.update({
        "prob_declara_ausencia": ans.get("declara_ausencia", {}).get("probability"),
        "prob_afirma_fato": ans.get("afirma_fato", {}).get("probability"),
        "nivel_score": s.get("score"),
        "nivel_confidence": s.get("confidence"),
        "nivel_probs": {x["label"]: x["probability"] for x in s.get("probabilities", [])},
        "input_tokens": (d.get("usage") or {}).get("input_tokens"),
    })
    return out

res, t0 = [], time.time()
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    for i, r in enumerate(ex.map(do, tasks), 1):
        res.append(r)
        if i % 12 == 0 or i == len(tasks):
            print(f"  {i}/{len(tasks)}  {time.time()-t0:.0f}s", flush=True)
json.dump({"publicado": pub, "rows": res}, open(OUT, "w"), ensure_ascii=False, indent=1)

ok = [r for r in res if not r.get("erro")]
toks = sum(r.get("input_tokens") or 0 for r in ok)
print(f"\nCOMPLETO: {len(ok)} julgados · {len(res)-len(ok)} erros · "
      f"{toks} input tokens (~US$ {toks/1e6*0.10:.4f}) · {time.time()-t0:.0f}s")

for kind in ("negative", "positive"):
    g = [r for r in ok if r["kind"] == kind]
    if not g:
        continue
    print(f"\n{kind} (n={len(g)})")
    for lab, key in (("declara ausencia", "prob_declara_ausencia"),
                     ("afirma fato", "prob_afirma_fato")):
        v = [r[key] for r in g if r.get(key) is not None]
        if v:
            print(f"  {lab:18s} media {sum(v)/len(v):.3f} · >0,5 em {sum(1 for x in v if x > 0.5)}/{len(v)}")
    nv = [r["nivel_score"] for r in g if r.get("nivel_score") is not None]
    cf = [r["nivel_confidence"] for r in g if r.get("nivel_confidence") is not None]
    if nv:
        print(f"  nivel medio {sum(nv)/len(nv):.2f} · confidence media {sum(cf)/len(cf):.2f}")
    for r in g:
        if r.get("prob_declara_ausencia") is None:
            continue
        marca = "" if (r["prob_declara_ausencia"] > 0.5) == r["abstained"] else "  <-- DISCORDA"
        print(f"   [{r['id'][:26]:26s}] det={'SIM' if r['abstained'] else 'nao'} "
              f"p_aus={r['prob_declara_ausencia']:.2f} p_fato={r['prob_afirma_fato']:.2f} "
              f"niv={r['nivel_score']:.2f}{marca}")
