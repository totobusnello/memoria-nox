"""Answer the 99 questions from arm D, with arm C_visible as the clean baseline.

The comparison that carries the claim is D_visible against C_visible: identical
input (the prose the live builder actually had), identical pipeline, identical
model and filter, ONE paragraph of difference in the prompt. Everything else is
context.

Arms judged here:
  c_visible -- old prompt, visible prose      <- the baseline of the A/B
  d_visible -- NEW prompt, visible prose      <- the A/B
  d_full    -- NEW prompt, whole session      <- new prompt + fixed window
  d_iso     -- NEW prompt, whole session, truncated to arm B's characters
Stored labels are reused for a, b, c_all, c_iso and the four RAG arms: the judge
was shown deterministic on this corpus (540 pairs, zero label changes).
"""
import json, os, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = "/root/medicoes/2026-10-26-memory-tax"
D = json.load(open(f"{BASE}/armd-units.json"))
C = json.load(open(f"{BASE}/armc-units.json"))
PREV = {(r["uuid"], r["question"]): r for r in json.load(open(f"{BASE}/armc-judged.json"))}
JUD = json.load(open(f"{BASE}/replay-judged.json"))
OUT = f"{BASE}/armd-judged.json"
GKEY = os.environ["GEMINI_API_KEY"]
OKEY = os.environ["OPENAI_API_KEY"]
GMODEL = "gemini-2.5-flash-lite"
JMODEL = os.environ.get("JUDGE_MODEL", "gpt-6-luna")
WORKERS = int(os.environ.get("WORKERS", "8"))
SMOKE = int(os.environ.get("SMOKE_N", "0"))
THR = 0.5
NEW = ("c_visible", "d_visible", "d_full", "d_iso")
OLD = ("a", "b", "c_iso", "c_all", "bm25_iso", "dense_iso", "bm25_k10", "dense_k10")

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

def byimp(units):
    return sorted(units, key=lambda m: -(m.get("importance") or 0))
src = {
    "c_visible": {u.rsplit("|", 1)[0]: byimp(v) for u, v in C["units"].items()
                  if u.endswith("|visible")},
    "d_visible": {u.rsplit("|", 1)[0]: byimp(v) for u, v in D["units"].items()
                  if u.endswith("|visible")},
    "d_full": {u.rsplit("|", 1)[0]: byimp(v) for u, v in D["units"].items()
               if u.endswith("|full")},
}
src["d_iso"] = src["d_full"]

tasks = JUD[:SMOKE] if SMOKE else JUD
print(f"pairs {len(tasks)} · new arms {len(NEW)}", flush=True)

def do(j):
    u, q = j["uuid"], j["question"]
    prev = PREV.get((u, q), {})
    out = {k: j[k] for k in ("uuid", "stratum", "scope", "category", "question",
                             "answer", "span_chars", "memory_units", "memory_chars")}
    for k in OLD:
        out[k] = j[k] if k in ("a", "b") else prev.get(k)
        if f"{k}_abstained" in prev:
            out[f"{k}_abstained"] = prev[f"{k}_abstained"]
    budget = max(1, j.get("memory_chars") or 2000)
    for arm in NEW:
        us = src[arm].get(u, [])
        if arm == "d_iso":
            picked, used = [], 0
            for m in us:
                if used + len(m["text"]) + 1 > budget:
                    continue
                picked.append(m["text"])
                used += len(m["text"]) + 1
            mat = "\n".join(picked) if picked else (us[0]["text"][:budget] if us else "")
        else:
            mat = "\n".join(m["text"] for m in us)
        out[f"{arm}_chars"] = len(mat)
        out[f"{arm}_units"] = len(us)
        try:
            txt, _ = answer(mat, q)
        except Exception as e:
            out[f"{arm}_erro"] = str(e)[:140]
            continue
        out[f"{arm}_text"] = txt
        out[f"{arm}_abstained"] = abstained(txt)
        try:
            out[arm] = judge(j["answer"], txt, q)
        except Exception as e:
            out[f"{arm}_judge_erro"] = str(e)[:140]
    return out

res, t0 = [], time.time()
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    for i, r in enumerate(ex.map(do, tasks), 1):
        res.append(r)
        if i % 10 == 0 or i == len(tasks):
            print(f"  {i}/{len(tasks)}  {time.time()-t0:.0f}s", flush=True)
json.dump(res, open(OUT, "w"), ensure_ascii=False)
jt = sum((r.get(a) or {}).get("tokens", 0) for r in res for a in NEW)
print(f"\njudge {jt} tok (~US$ {jt/1e6*0.10:.4f}) · {time.time()-t0:.0f}s · "
      f"errors {sum(1 for r in res if any(k.endswith('_erro') for k in r))}")

def hit(r, k):
    return ((r.get(k) or {}).get("contem") or 0) > THR
def contra(r, k):
    return ((r.get(k) or {}).get("contradiz") or 0) > THR
def sil(r, k):
    return bool(r.get(f"{k}_abstained")) or \
        ((r.get(k) or {}).get("nivel_probs", {}).get("nao_responde", 0) > 0.5)

print("\nCONTROL · d_iso budget against arm B's characters")
g = [r for r in res if r.get("d_iso_chars")]
print(f"  aggregate {sum(r['d_iso_chars'] for r in g)/sum(r['memory_chars'] for r in g):.3f} "
      f"· over budget {sum(1 for r in g if r['d_iso_chars'] > r['memory_chars'])}")

print(f"\n{'arm':12s} {'n':>4s} {'correct':>9s} {'silent':>8s} {'contra':>8s}  input / prompt")
LBL = [("a", "A oracle", "raw window / —"), ("b", "B real", "visible / OLD"),
       ("c_visible", "C visible", "visible / OLD (my re-impl)"),
       ("d_visible", "D visible", "visible / NEW"),
       ("c_all", "C all", "whole / OLD"), ("d_full", "D full", "whole / NEW"),
       ("d_iso", "D iso", "whole, B's budget / NEW"),
       ("bm25_iso", "bm25_iso", "raw chunks, B's budget")]
for k, lab, note in LBL:
    gg = [r for r in res if r.get(k)]
    if not gg:
        continue
    print(f"{lab:12s} {len(gg):4d} {sum(1 for r in gg if hit(r,k))/len(gg)*100:8.1f}% "
          f"{sum(1 for r in gg if sil(r,k))/len(gg)*100:7.1f}% "
          f"{sum(1 for r in gg if contra(r,k))/len(gg)*100:7.1f}%  {note}")

print("\nTHE A/B · same input, same pipeline, ONE paragraph of prompt")
cv = sum(1 for r in res if hit(r, "c_visible")) / len(res)
dv = sum(1 for r in res if hit(r, "d_visible")) / len(res)
ca = sum(1 for r in res if hit(r, "c_all")) / len(res)
df = sum(1 for r in res if hit(r, "d_full")) / len(res)
a = sum(1 for r in res if hit(r, "a")) / len(res)
b = sum(1 for r in res if hit(r, "b")) / len(res)
print(f"  visible prose : C {cv*100:5.1f}% -> D {dv*100:5.1f}%  = {(dv-cv)*100:+5.1f} pp")
print(f"  whole prose   : C {ca*100:5.1f}% -> D {df*100:5.1f}%  = {(df-ca)*100:+5.1f} pp")
print(f"\n  gap to close (A {a*100:.1f}% - B {b*100:.1f}%) = {(a-b)*100:.1f} pp")
for k, lab in (("c_all", "window alone"), ("d_visible", "prompt alone"),
               ("d_full", "prompt + window")):
    v = sum(1 for r in res if hit(r, k)) / len(res)
    print(f"    {lab:17s} {v*100:5.1f}%  recovers {(v-b)*100:+5.1f} pp = "
          f"{(v-b)/(a-b)*100:5.1f}% of the gap")
bm = sum(1 for r in res if hit(r, "bm25_iso")) / len(res)
print(f"\n  net value against naive RAG ({bm*100:.1f}%): "
      f"B {(b-bm)*100:+.1f} pp · D_iso "
      f"{(sum(1 for r in res if hit(r,'d_iso'))/len(res)-bm)*100:+.1f} pp · D_full "
      f"{(df-bm)*100:+.1f} pp")

print("\nBY CATEGORY · the cell the new prompt was written for")
for cat in ("context", "decision", "lesson"):
    gg = [r for r in res if r["category"] == cat]
    if not gg:
        continue
    cells = "  ".join(f"{lab}={sum(1 for r in gg if hit(r,k))/len(gg)*100:5.1f}%"
                      for k, lab in (("a", "A"), ("b", "B"), ("c_visible", "Cv"),
                                     ("d_visible", "Dv"), ("c_all", "Ca"), ("d_full", "Df"),
                                     ("bm25_iso", "RAG")))
    print(f"  {cat:9s} n={len(gg):3d}  {cells}")

print("\nBY FINAL TRANSCRIPT SIZE")
SZ = {r["uuid"]: r for r in json.load(open(f"{BASE}/see-once.json"))["rows"]}
for nm, lo, hi in (("<50k", 0, 50_000), ("50-200k", 50_000, 200_000),
                   ("200k-1M", 200_000, 1 << 40)):
    gg = [r for r in res if lo <= SZ.get(r["uuid"], {}).get("total_chars", 0) < hi]
    if not gg:
        continue
    cells = "  ".join(f"{lab}={sum(1 for r in gg if hit(r,k))/len(gg)*100:5.1f}%"
                      for k, lab in (("a", "A"), ("b", "B"), ("d_visible", "Dv"),
                                     ("d_full", "Df"), ("bm25_iso", "RAG")))
    print(f"  {nm:9s} n={len(gg):3d}  {cells}")
