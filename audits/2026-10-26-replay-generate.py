"""Generate the replay questions from the RAW side only.

The questions must come from the raw transcript and never from the distilled
chunks: anchoring them on what survived would manufacture a null by selection,
which is the defect the PT-BR golden set already paid for.

Three disciplines, each closing a failure this repository has measured:

1. The asking criterion is the builder's OWN declared criterion, copied
   verbatim from DISTILL_SYSTEM in session-distill.ts. A summariser that drops
   89% of the text is working; it only owes an answer about the class of fact
   it promised to keep. Asking about anything else measures my preference.

2. Every citation is verified as a byte-exact substring of the window. An LLM
   claiming VERBATIM and paraphrasing instead was measured at 34.5% in this
   repository, and here the claim IS about a quote, so the check belongs.

3. The question must be self-contained -- it has to name its entities, so that
   arm B is not handicapped by missing context rather than by missing memory.
   Equalising the input before comparing the arms is the rule the 2026-10-22
   agreement study established.

The evidence SPAN (last citation end minus first citation start) is what makes
the result diagnostic: the builder cuts the conversation into BLOCK_SIZE = 2000
character blocks with no overlap, so a fact whose evidence spans more than 2000
characters was never visible whole to any single LLM call.
"""
import json
import os
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

SET = "/root/medicoes/2026-10-26-memory-tax/replay-set.json"
OUT = "/root/medicoes/2026-10-26-memory-tax/replay-questions.json"
MODEL = "gemini-2.5-flash-lite"
KEY = os.environ["GEMINI_API_KEY"]
SMOKE = int(os.environ.get("SMOKE_N", "0"))
WORKERS = int(os.environ.get("WORKERS", "4"))

SYSTEM = """Você recebe um trecho de uma conversa real entre um usuário e agentes de IA.

Extraia fatos que mereçam ser lembrados a longo prazo, EXATAMENTE nestas
categorias (são as que o sistema de memória declara guardar):
- decision: decisões tomadas pelo usuário ou pelo agente
- preference: preferências do usuário (como ele quer as coisas feitas)
- lesson: lições aprendidas (erros, fixes, insights técnicos)
- context: contexto de projeto relevante (nomes, status, detalhes)

Ignore: cumprimentos, confirmações (ok, feito, obrigado), listas de tarefas
genéricas, conteúdo repetido.

Extraia DOIS tipos de fato, e marque cada um em "escopo":

"local" — até 3 fatos. O fato está estabelecido num único ponto do trecho.
  Prefira decision e lesson a context; só use context se não houver decisão,
  preferência ou lição no trecho.

"distribuido" — até 3 fatos. O fato SÓ se estabelece juntando duas ou mais
  partes DISTANTES do trecho. Os casos que interessam:
    - algo que MUDOU: decidiu-se X e depois trocou-se para Y; o valor era A e
      passou a ser B; tentou-se uma abordagem, falhou, e adotou-se outra.
    - algo cuja causa está num ponto e o efeito noutro ponto distante.
  A pergunta deve exigir o estado FINAL ou a relação completa, não uma das
  pontas. Exemplo bom: "para qual horário o cron X terminou movido, depois da
  primeira tentativa?" Exemplo ruim: "qual horário foi escolhido para X?"
  As "citacoes" devem conter as DUAS pontas, cada uma copiada do seu ponto.
  Se o trecho não tiver nenhum fato assim, devolva lista vazia para este
  escopo — NÃO invente e NÃO transforme um fato local em distribuído.

Para cada fato devolva:
- "escopo": "local" ou "distribuido".
- "pergunta": pergunta AUTOCONTIDA. Precisa nomear explicitamente as entidades
  (arquivo, cron, número, pessoa, projeto, comando) para que alguém SEM acesso
  a este trecho entenda o que se pergunta. NUNCA use "isso", "esse arquivo",
  "o horário escolhido", "a decisão acima".
- "resposta": a resposta curta e factual, no máximo 25 palavras.
- "citacoes": trechos VERBATIM deste texto, copiados caractere por caractere
  exatamente como aparecem, que juntos sustentam a resposta. Todos os
  necessários e nenhum a mais. Cada trecho entre 20 e 300 caracteres.
- "categoria": uma das quatro acima.
- "importancia": 0.0 a 1.0 (0.9+ crítico, 0.7-0.9 importante, 0.5-0.7 útil).

Devolva apenas fatos com importancia >= 0.5. Responda SÓ com JSON:
{"fatos":[{"escopo":"...","pergunta":"...","resposta":"...","citacoes":["..."],"categoria":"...","importancia":0.0}]}"""

URL = (f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}"
       f":generateContent?key={KEY}")


def call(window_text):
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM}]},
        "contents": [{"parts": [{"text": window_text}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.0,
                             "maxOutputTokens": 8192},
    }
    req = urllib.request.Request(
        URL, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.loads(r.read())
    cand = (d.get("candidates") or [{}])[0]
    txt = "".join(p.get("text", "") for p in (cand.get("content") or {}).get("parts", []))
    usage = d.get("usageMetadata") or {}
    return txt, usage.get("promptTokenCount", 0), usage.get("candidatesTokenCount", 0)



def parse_fatos(txt):
    """Facts out of the model's reply, tolerating a reply the output ceiling cut.

    Three shapes arrive: {"fatos":[...]}, a bare [...], and either of those
    truncated mid-string. Discarding a truncated reply reads as "this window
    held no fact", which is a fact about the ceiling, so the complete objects
    before the cut are recovered by scanning balanced braces.
    """
    try:
        d = json.loads(txt)
        return d.get("fatos", []) if isinstance(d, dict) else (d if isinstance(d, list) else [])
    except Exception:
        pass
    out, depth, start, instr, esc = [], 0, None, False, False
    for i, ch in enumerate(txt):
        if instr:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                instr = False
            continue
        if ch == '"':
            instr = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    o = json.loads(txt[start:i + 1])
                    if isinstance(o, dict) and o.get("pergunta"):
                        out.append(o)
                except Exception:
                    pass
                start = None
    return out


def norm(s):
    """Whitespace-insensitive comparison: the model reflows newlines even when
    copying byte-exact text, and treating that as a failed quote would reject
    on formatting -- the defect the 8-word citation check was retired for."""
    return re.sub(r"\s+", " ", s or "").strip()


def locate(cit, window):
    """Character offsets of a citation in the window, or None if not verbatim."""
    i = window.find(cit)
    if i >= 0:
        return i, i + len(cit)
    nw, nc = norm(window), norm(cit)
    if not nc or nc not in nw:
        return None
    # map back approximately via a short anchor, so the span stays measurable
    anchor = nc[:40]
    j = nw.find(anchor)
    frac = j / max(len(nw), 1)
    approx = int(frac * len(window))
    return approx, approx + len(cit)


def main():
    data = json.load(open(SET, encoding="utf-8"))
    jobs, vistos = [], set()
    for s_ in data["sessions"]:
        for w in s_["windows"]:
            k = (s_["uuid"], hash(w["text"]))
            if k in vistos:
                continue
            vistos.add(k)
            jobs.append((s_, w))
    if SMOKE:
        jobs = jobs[:SMOKE]
    print(f"windows: {len(jobs)} (duplicadas removidas)  model: {MODEL}  workers: {WORKERS}")

    t0 = time.time()
    out, tin, tout = [], 0, 0

    def run(job):
        s, w = job
        try:
            txt, pi, po = call(w["text"])
            return s, w, parse_fatos(txt), pi, po, None
        except Exception as e:
            return s, w, None, 0, 0, f"{type(e).__name__}: {e}"

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for s, w, parsed, pi, po, err in ex.map(run, jobs):
            tin += pi
            tout += po
            if err:
                print("  ERR", s["uuid"][:8], w["label"], err)
                continue
            fatos, por_escopo = [], {"local": 0, "distribuido": 0}
            for f in (parsed or []):
                sc = f.get("escopo") if f.get("escopo") in por_escopo else "local"
                if por_escopo[sc] >= 3:
                    continue
                por_escopo[sc] += 1
                fatos.append(f)
            for f in fatos:
                cits = [c for c in (f.get("citacoes") or []) if isinstance(c, str)]
                locs = [locate(c, w["text"]) for c in cits]
                ok = [l for l in locs if l]
                rec = {
                    "uuid": s["uuid"], "stratum": s["stratum"], "window": w["label"],
                    "scope": f.get("escopo"), "question": f.get("pergunta"), "answer": f.get("resposta"),
                    "category": f.get("categoria"), "importance": f.get("importancia"),
                    "citations": cits,
                    "citations_verbatim": len(ok), "citations_total": len(cits),
                    "span_chars": (max(e for _, e in ok) - min(b for b, _ in ok)) if ok else None,
                    "evidence_window": None,
                }
                if ok:
                    b, e = min(b for b, _ in ok), max(e for _, e in ok)
                    pad = 1500
                    rec["evidence_window"] = w["text"][max(0, b - pad):min(len(w["text"]), e + pad)]
                out.append(rec)

    # ---- controls, printed before anything is used
    n = len(out)
    allv = sum(1 for r in out if r["citations_total"] and r["citations_verbatim"] == r["citations_total"])
    nonev = sum(1 for r in out if r["citations_verbatim"] == 0)
    selfc = sum(1 for r in out if r["question"] and not re.search(
        r"\b(isso|esse|essa|este|esta|aquilo|acima|mencionad|o horário escolhido)\b",
        r["question"], re.I))
    print(f"\nfacts: {n}")
    print(f"  all citations verbatim : {allv} ({allv/max(n,1):.1%})")
    print(f"  no citation verifiable : {nonev} ({nonev/max(n,1):.1%})  <- dropped")
    print(f"  question self-contained: {selfc} ({selfc/max(n,1):.1%})")
    spans = sorted(r["span_chars"] for r in out if r["span_chars"] is not None)
    if spans:
        print(f"  evidence span: median {spans[len(spans)//2]:,}  "
              f"<2000: {sum(1 for s in spans if s < 2000)}  "
              f"2000-4000: {sum(1 for s in spans if 2000 <= s < 4000)}  "
              f">4000: {sum(1 for s in spans if s >= 4000)}")
    import collections
    print("  by category:", dict(collections.Counter(r["category"] for r in out)))
    print("  by scope   :", dict(collections.Counter(r["scope"] for r in out)))
    for sc in ("local", "distribuido"):
        sp = sorted(r["span_chars"] for r in out
                    if r["scope"] == sc and r["span_chars"] is not None)
        if sp:
            print(f"    {sc:12s} n={len(sp):3d} median span {sp[len(sp)//2]:,}"
                  f"  >2000: {sum(1 for x in sp if x >= 2000)}")
    print(f"\ntokens in {tin:,} out {tout:,} ~US$ {tin/1e6*0.10 + tout/1e6*0.40:.4f}"
          f" · {time.time()-t0:.0f}s")

    if not SMOKE:
        json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
        print("wrote", OUT)
    else:
        print("SMOKE: nothing written")
        for r in out[:3]:
            print(f"\n  [{r['scope']}|{r['category']}|span {r['span_chars']}] {r['question']}")
            print(f"  -> {r['answer']}")


main()
