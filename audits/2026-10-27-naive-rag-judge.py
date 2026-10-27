"""Judge the four naive-RAG arms with the SAME judge as the replay.

Predicates, levels, wording and threshold are copied verbatim from
2026-10-26-replay-judge.py. A different prompt would make the new arms
unreadable against the stored A and B, which is the whole point of running them.

Arm A and arm B are not re-judged: on 2026-10-26 this judge was shown
deterministic on this corpus (540 pairs, zero label changes, max |delta p|
0.000), so their labels are read from replay-judged.json.
"""
import json, os, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = "/root/medicoes/2026-10-26-memory-tax"
SRC = f"{BASE}/rag-answers.json"
JUD = f"{BASE}/replay-judged.json"
OUT = f"{BASE}/rag-judged.json"
KEY = os.environ["OPENAI_API_KEY"]
MODEL = os.environ.get("JUDGE_MODEL", "gpt-6-luna")
API = "https://api.openai.com/v1/decisions"
WORKERS = int(os.environ.get("JUDGE_WORKERS", "8"))
SMOKE = int(os.environ.get("SMOKE_N", "0"))
THR = float(os.environ.get("THR", "0.5"))
ARMS = ("bm25_iso", "bm25_k10", "dense_iso", "dense_k10")

CONTEM = ("A RESPOSTA DO CANDIDATO transmite o mesmo fato que a RESPOSTA DE REFERENCIA, "
          "para esta pergunta: {q}\nRedacao diferente, mais detalhe ou caminho completo em "
          "vez de nome de arquivo contam como o mesmo fato. Omitir o fato pedido ou dizer "
          "que nao sabe NAO conta.")
CONTRADIZ = ("A RESPOSTA DO CANDIDATO afirma algo INCOMPATIVEL com a RESPOSTA DE REFERENCIA "
             "para esta pergunta: {q}\nConta como incompativel: valor, nome, numero, horario "
             "ou decisao diferente apresentado como correto. NAO conta: dizer que nao sabe, "
             "nem omitir parte do fato, nem dar menos detalhe.")
LEVELS = [
    {"label": "nao_responde", "description": "O CANDIDATO nao apresenta resposta: diz que nao "
                                             "sabe, que a informacao nao esta disponivel, ou "
                                             "nada diz sobre o que foi perguntado."},
    {"label": "responde_errado", "description": "O CANDIDATO apresenta uma resposta, e ela "
                                                "afirma um valor, nome ou decisao diferente do "
                                                "da REFERENCIA."},
    {"label": "responde_parcial", "description": "O CANDIDATO apresenta parte do fato da "
                                                 "REFERENCIA e deixa faltar outra parte, sem "
                                                 "afirmar nada que a contradiga."},
    {"label": "responde_certo", "description": "O CANDIDATO apresenta o fato da REFERENCIA por "
                                               "inteiro, com qualquer redacao."},
]

def decide(ref, cand, q):
    body = {"model": MODEL,
            "input": f"RESPOSTA DE REFERENCIA:\n---\n{ref}\n---\n\n"
                     f"RESPOSTA DO CANDIDATO:\n---\n{cand}\n---",
            "questions": [
                {"type": "predicate", "name": "contem", "instructions": CONTEM.format(q=q)},
                {"type": "predicate", "name": "contradiz", "instructions": CONTRADIZ.format(q=q)},
                {"type": "score", "name": "nivel",
                 "instructions": f"Qual destes descreve melhor a RESPOSTA DO CANDIDATO, "
                                 f"dada a pergunta: {q}", "levels": LEVELS}]}
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
            if e.code in (400, 401, 403, 404):
                break
            time.sleep(2 * (a + 1))
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
            time.sleep(2 * (a + 1))
    raise RuntimeError(str(last))

def pull(d):
    """Must RAISE on an empty extraction, never return {}.

    A missing predicate reads downstream as probability 0, i.e. "the candidate
    is wrong", so a parser bug prints a perfect tax. The first smoke of the
    replay judge did exactly that -- arm A at 0.0%, impossible by construction.
    """
    ans = {a["name"]: a for a in d.get("answers", [])}
    if "contem" not in ans or "contradiz" not in ans:
        raise RuntimeError(f"judge envelope without the predicates: keys={list(d)[:6]} "
                           f"answers={list(ans)[:6]}")
    s_ = ans.get("nivel", {})
    return {"contem": ans["contem"].get("probability"),
            "contradiz": ans["contradiz"].get("probability"),
            "nivel": s_.get("score"), "nivel_conf": s_.get("confidence"),
            "nivel_probs": {x["label"]: x["probability"] for x in s_.get("probabilities", [])},
            "tokens": (d.get("usage") or {}).get("input_tokens", 0)}

rows = json.load(open(SRC, encoding="utf-8"))
old = {(r["uuid"], r["question"]): r for r in json.load(open(JUD, encoding="utf-8"))}
pop = [r for r in rows if (r["uuid"], r["question"]) in old and not r.get("erro")]
print(f"rows {len(rows)} · in the judged population {len(pop)}")

jobs = [(r, arm) for r in pop for arm in ARMS if r.get(f"{arm}_text") is not None]
if SMOKE:
    jobs = jobs[:SMOKE]
print(f"judgements: {len(jobs)} · model {MODEL} · workers {WORKERS}", flush=True)

t0 = time.time()
def run(job):
    r, arm = job
    try:
        return (r["uuid"], r["question"], arm, pull(decide(r["answer"], r[f"{arm}_text"],
                                                           r["question"])))
    except Exception as e:
        return (r["uuid"], r["question"], arm, {"erro": str(e)[:200]})

got, toks, n = {}, 0, 0
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    for u, q, arm, d in ex.map(run, jobs):
        got[(u, q, arm)] = d
        toks += d.get("tokens") or 0
        n += 1
        if n % 50 == 0 or n == len(jobs):
            print(f"  {n}/{len(jobs)}  {time.time()-t0:.0f}s", flush=True)

out = []
for r in pop:
    k = (r["uuid"], r["question"])
    o = dict(r)
    o["a"] = old[k]["a"]
    o["b"] = old[k]["b"]
    o["a_abstained"] = old[k]["a_abstained"]
    o["b_abstained"] = old[k]["b_abstained"]
    for arm in ARMS:
        o[arm] = got.get((r["uuid"], r["question"], arm))
    out.append(o)
json.dump(out, open(OUT, "w"), ensure_ascii=False)

errs = sum(1 for v in got.values() if "erro" in v)
print(f"\n{len(got)} judged · {errs} errors · {toks} input tokens "
      f"(~US$ {toks/1e6*0.10:.4f}) · {time.time()-t0:.0f}s")
if errs:
    for k, v in list(got.items())[:3]:
        if "erro" in v:
            print("  ", k[2], v["erro"][:140])

def hit(r, key):
    d = r.get(key) or {}
    return (d.get("contem") or 0) > THR
def contra(r, key):
    d = r.get(key) or {}
    return (d.get("contradiz") or 0) > THR

print(f"\n{'arm':12s} {'n':>4s} {'correct':>9s} {'contradicts':>12s} {'silent':>8s} {'recall':>8s}")
for key, lab in [("a", "A oracle"), ("b", "B memory")] + [(a, a) for a in ARMS]:
    g = [r for r in out if r.get(key)]
    if not g:
        continue
    rc = [r for r in g if r.get(f"{key}_recall") is not None]
    rcs = (f"{sum(1 for r in rc if r[f'{key}_recall'])/len(rc)*100:7.1f}%" if rc else "      --")
    sil = sum(1 for r in g if (r.get(key) or {}).get("nivel_probs", {}).get("nao_responde", 0) > 0.5
              or r.get(f"{key}_abstained"))
    print(f"{lab:12s} {len(g):4d} {sum(1 for r in g if hit(r,key))/len(g)*100:8.1f}% "
          f"{sum(1 for r in g if contra(r,key))/len(g)*100:11.1f}% {sil/len(g)*100:7.1f}% {rcs}")

a_rate = sum(1 for r in out if hit(r, "a")) / len(out)
print(f"\nTAX against the oracle arm (A = {a_rate*100:.1f}%):")
for key in ["b"] + list(ARMS):
    g = [r for r in out if r.get(key)]
    v = sum(1 for r in g if hit(r, key)) / len(g)
    print(f"  {key:10s} {v*100:5.1f}%  tax {(a_rate-v)/a_rate*100:6.1f}%")

print("\nTHE COMPARISON THE PAPER ASKS: memory against naive RAG at equal budget")
b = sum(1 for r in out if hit(r, "b")) / len(out)
for key in ("bm25_iso", "dense_iso"):
    g = [r for r in out if r.get(key)]
    v = sum(1 for r in g if hit(r, key)) / len(g)
    print(f"  B {b*100:.1f}% vs {key} {v*100:.1f}%  -> net value of memory "
          f"{(b-v)*100:+.1f} pp")

print("\nretrieval recall by FINAL transcript size (the k10 100% is trivial on small ones)")
BANDS = [("<50k", 0, 50_000), ("50-200k", 50_000, 200_000),
         ("200k-1M", 200_000, 1_000_000)]
idx = json.load(open(f"{BASE}/rag-index.json"))
size = {u: v["prose_chars"] for u, v in idx["sessions"].items()}
for nm, lo, hi in BANDS:
    g = [r for r in out if lo <= size.get(r["uuid"], 0) < hi]
    if not g:
        continue
    line = f"  {nm:9s} n={len(g):3d}"
    for arm in ARMS:
        rc = [r for r in g if r.get(f"{arm}_recall") is not None]
        if rc:
            line += f"  {arm}={sum(1 for r in rc if r[f'{arm}_recall'])/len(rc)*100:5.1f}%"
    print(line)
