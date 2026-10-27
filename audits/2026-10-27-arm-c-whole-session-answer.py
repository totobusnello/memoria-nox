"""Answer the same 99 questions from arm C, and judge it with the same judge.

Two C arms, because "more memory" and "better memory" are different claims and
the first smoke of the RAG arm already showed what an unequal budget does:

  c_all -- every unit the re-distilled whole session produced. This is the
           system as it WOULD be: the builder that returns produces more memory,
           and arm B likewise received all of its own units. 2.46x the volume.
  c_iso -- the same units truncated to the SAME characters arm B received,
           taken in descending importance (what a salience-ordered memory would
           serve under a budget). If c_iso lands on B, C's gain is volume alone.

Arm A and B labels are read from the stored run: the judge was shown
deterministic on this corpus (540 pairs, zero label changes).
"""
import json, math, os, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = "/root/medicoes/2026-10-26-memory-tax"
C = json.load(open(f"{BASE}/armc-units.json"))
JUD = json.load(open(f"{BASE}/replay-judged.json"))
RAG = {(r["uuid"], r["question"]): r for r in json.load(open(f"{BASE}/rag-judged.json"))}
OUT = f"{BASE}/armc-judged.json"
GKEY = os.environ["GEMINI_API_KEY"]
OKEY = os.environ["OPENAI_API_KEY"]
GMODEL = "gemini-2.5-flash-lite"
JMODEL = os.environ.get("JUDGE_MODEL", "gpt-6-luna")
WORKERS = int(os.environ.get("WORKERS", "8"))
SMOKE = int(os.environ.get("SMOKE_N", "0"))
THR = 0.5

ANSWER_SYSTEM = """Você responde perguntas usando APENAS o material fornecido.

Regras:
- Se o material contém a resposta, responda em no máximo 25 palavras.
- Se o material NÃO contém a resposta, responda exatamente: NAO SEI
- Nunca use conhecimento próprio. Nunca especule. Nunca complete lacuna.
- Se o material trouxer duas informações conflitantes, responda com a que o
  material indicar como final e diga que houve mudança. Se não houver como
  saber qual é a final, responda as duas e diga que o material não resolve."""

CANON = "i have no memory matches for this question"
def abstained(t):
    s = (t or "").lower()
    return (CANON in s or "nao sei" in s or "não sei" in s or "não tenho" in s
            or "nao tenho" in s or "não há informação" in s or "nao ha informacao" in s)

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

def post(url, body, hdr, timeout=120):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=hdr)
    last = None
    for a in range(5):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read().decode()[:200]}"
            if e.code in (400, 401, 403, 404):
                break
            time.sleep(2 * (a + 1))
        except Exception as e:
            last = f"{type(e).__name__}: {str(e)[:160]}"
            time.sleep(2 * (a + 1))
    raise RuntimeError(str(last))

GURL = (f"https://generativelanguage.googleapis.com/v1beta/models/{GMODEL}"
        f":generateContent?key={GKEY}")
def answer(material, question):
    d = post(GURL, {
        "systemInstruction": {"parts": [{"text": ANSWER_SYSTEM}]},
        "contents": [{"parts": [{"text": f"MATERIAL:\n{material}\n\nPERGUNTA: {question}"}]}],
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": 200}},
        {"Content-Type": "application/json"})
    c = (d.get("candidates") or [{}])[0]
    txt = "".join(p.get("text", "") for p in (c.get("content") or {}).get("parts") or [])
    return txt.strip(), (d.get("usageMetadata") or {}).get("promptTokenCount", 0)

def judge(ref, cand, q):
    d = post("https://api.openai.com/v1/decisions", {
        "model": JMODEL,
        "input": f"RESPOSTA DE REFERENCIA:\n---\n{ref}\n---\n\n"
                 f"RESPOSTA DO CANDIDATO:\n---\n{cand}\n---",
        "questions": [
            {"type": "predicate", "name": "contem", "instructions": CONTEM.format(q=q)},
            {"type": "predicate", "name": "contradiz", "instructions": CONTRADIZ.format(q=q)},
            {"type": "score", "name": "nivel",
             "instructions": f"Qual destes descreve melhor a RESPOSTA DO CANDIDATO, "
                             f"dada a pergunta: {q}", "levels": LEVELS}]},
        {"Content-Type": "application/json", "Authorization": f"Bearer {OKEY}"})
    ans = {a["name"]: a for a in d.get("answers", [])}
    if "contem" not in ans or "contradiz" not in ans:
        raise RuntimeError(f"judge envelope without the predicates: keys={list(d)[:6]}")
    s_ = ans.get("nivel", {})
    return {"contem": ans["contem"].get("probability"),
            "contradiz": ans["contradiz"].get("probability"),
            "nivel": s_.get("score"),
            "nivel_probs": {x["label"]: x["probability"] for x in s_.get("probabilities", [])},
            "tokens": (d.get("usage") or {}).get("input_tokens", 0)}

units = {}
for k, v in C["units"].items():
    u, kind = k.rsplit("|", 1)
    if kind == "full":
        units[u] = sorted(v, key=lambda m: -(m.get("importance") or 0))

tasks = JUD[:SMOKE] if SMOKE else JUD
print(f"pairs: {len(tasks)} · 2 C arms", flush=True)

def do(j):
    u, q = j["uuid"], j["question"]
    us = units.get(u, [])
    out = {k: j[k] for k in ("uuid", "stratum", "scope", "category", "question",
                             "answer", "span_chars", "memory_units", "memory_chars")}
    out["c_units_total"] = len(us)
    all_txt = "\n".join(m["text"] for m in us)
    budget = max(1, j.get("memory_chars") or 2000)
    iso, used = [], 0
    for m in us:
        if used + len(m["text"]) + 1 > budget:
            continue
        iso.append(m["text"])
        used += len(m["text"]) + 1
    iso_txt = "\n".join(iso) if iso else (us[0]["text"][:budget] if us else "")
    for arm, mat in (("c_all", all_txt), ("c_iso", iso_txt)):
        out[f"{arm}_chars"] = len(mat)
        out[f"{arm}_units"] = len(us) if arm == "c_all" else len(iso)
        try:
            txt, toks = answer(mat, q)
        except Exception as e:
            out[f"{arm}_erro"] = str(e)[:140]
            continue
        out[f"{arm}_text"] = txt
        out[f"{arm}_abstained"] = abstained(txt)
        out[f"{arm}_tokens"] = toks
        try:
            out[arm] = judge(j["answer"], txt, q)
        except Exception as e:
            out[f"{arm}_judge_erro"] = str(e)[:140]
    r = RAG.get((u, q))
    for k in ("a", "b", "bm25_iso", "dense_iso", "bm25_k10", "dense_k10"):
        out[k] = (r or {}).get(k) if k not in ("a", "b") else j[k]
    return out

res, t0 = [], time.time()
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    for i, r in enumerate(ex.map(do, tasks), 1):
        res.append(r)
        if i % 10 == 0 or i == len(tasks):
            print(f"  {i}/{len(tasks)}  {time.time()-t0:.0f}s", flush=True)
json.dump(res, open(OUT, "w"), ensure_ascii=False)

atok = sum(r.get("c_all_tokens", 0) + r.get("c_iso_tokens", 0) for r in res)
jtok = sum((r.get(a) or {}).get("tokens", 0) for r in res for a in ("c_all", "c_iso"))
print(f"\n{len(res)} pairs · answers {atok} tok (~US$ {atok/1e6*0.10:.4f}) · "
      f"judge {jtok} tok (~US$ {jtok/1e6*0.10:.4f}) · {time.time()-t0:.0f}s")
errs = [r for r in res if any(k.endswith("_erro") for k in r)]
print(f"errors: {len(errs)}")

def hit(r, k):
    return ((r.get(k) or {}).get("contem") or 0) > THR
def contra(r, k):
    return ((r.get(k) or {}).get("contradiz") or 0) > THR

print("\nCONTROL · budget of c_iso against arm B's characters")
g = [r for r in res if r.get("c_iso_chars")]
print(f"  aggregate retrieved/memory = "
      f"{sum(r['c_iso_chars'] for r in g)/sum(r['memory_chars'] for r in g):.3f} · "
      f"over budget: {sum(1 for r in g if r['c_iso_chars'] > r['memory_chars'])}")
print(f"  c_all mean chars {sum(r['c_all_chars'] for r in res)/len(res):.0f} "
      f"vs arm B mean {sum(r['memory_chars'] for r in res)/len(res):.0f} "
      f"({sum(r['c_all_chars'] for r in res)/sum(r['memory_chars'] for r in res):.2f}x)")

print(f"\n{'arm':12s} {'n':>4s} {'correct':>9s} {'silent':>8s} {'contra':>8s}")
for k, lab in (("a", "A oracle"), ("b", "B memory"), ("c_iso", "C iso"),
               ("c_all", "C all"), ("bm25_iso", "bm25_iso"), ("dense_iso", "dense_iso"),
               ("bm25_k10", "bm25_k10"), ("dense_k10", "dense_k10")):
    gg = [r for r in res if r.get(k)]
    if not gg:
        continue
    sil = sum(1 for r in gg if r.get(f"{k}_abstained")
              or (r.get(k) or {}).get("nivel_probs", {}).get("nao_responde", 0) > 0.5)
    print(f"{lab:12s} {len(gg):4d} {sum(1 for r in gg if hit(r,k))/len(gg)*100:8.1f}% "
          f"{sil/len(gg)*100:7.1f}% {sum(1 for r in gg if contra(r,k))/len(gg)*100:7.1f}%")

b = sum(1 for r in res if hit(r, "b")) / len(res)
a = sum(1 for r in res if hit(r, "a")) / len(res)
print(f"\nWHAT THE WINDOW COSTS (A oracle {a*100:.1f}%, B as built {b*100:.1f}%)")
for k in ("c_iso", "c_all"):
    gg = [r for r in res if r.get(k)]
    v = sum(1 for r in gg if hit(r, k)) / len(gg)
    print(f"  {k:6s} {v*100:5.1f}%  recovers {(v-b)*100:+5.1f} pp of the "
          f"{(a-b)*100:.1f} pp gap = {(v-b)/(a-b)*100:5.1f}%  · residual tax "
          f"{(a-v)/a*100:.1f}%")
print("\nAND AGAINST NAIVE RAG at equal budget (the net-value claim)")
for k in ("bm25_iso", "dense_iso"):
    gg = [r for r in res if r.get(k)]
    v = sum(1 for r in gg if hit(r, k)) / len(gg)
    ci = sum(1 for r in res if hit(r, "c_iso")) / len(res)
    ca = sum(1 for r in res if hit(r, "c_all")) / len(res)
    print(f"  {k:10s} {v*100:5.1f}%  ·  B {b*100:.1f}% ({(b-v)*100:+.1f} pp)  "
          f"·  C_iso {ci*100:.1f}% ({(ci-v)*100:+.1f} pp)  "
          f"·  C_all {ca*100:.1f}% ({(ca-v)*100:+.1f} pp)")

print("\nby category")
for cat in ("context", "decision", "lesson"):
    gg = [r for r in res if r["category"] == cat]
    if not gg:
        continue
    cells = " ".join(f"{k}={sum(1 for r in gg if hit(r,k))/len(gg)*100:5.1f}%"
                     for k in ("a", "b", "c_iso", "c_all", "bm25_iso"))
    print(f"  {cat:9s} n={len(gg):3d}  {cells}")

print("\nby final transcript size (the band where see-once bites)")
SZ = {r["uuid"]: r for r in json.load(open(f"{BASE}/see-once.json"))["rows"]}
for nm, lo, hi in (("<50k", 0, 50_000), ("50-200k", 50_000, 200_000),
                   ("200k-1M", 200_000, 1 << 40)):
    gg = [r for r in res if lo <= SZ.get(r["uuid"], {}).get("total_chars", 0) < hi]
    if not gg:
        continue
    cells = " ".join(f"{k}={sum(1 for r in gg if hit(r,k))/len(gg)*100:5.1f}%"
                     for k in ("a", "b", "c_iso", "c_all", "bm25_iso"))
    print(f"  {nm:9s} n={len(gg):3d}  {cells}")
