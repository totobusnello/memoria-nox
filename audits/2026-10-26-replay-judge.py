"""Judge both arms of the replay, and separate loss from damage.

Silence is not the whole measurement. An arm that answers and answers WRONG is
worse than one that says NAO SEI: it is served with the same confidence as a
true memory. This repository has the measurement to prove the concern is real --
17.4% of negative queries asserted a non-existent datum as fact, every one of
them with a citation.

Arm A is judged too, for the reason that 95.2% non-abstention is not 95.2%
correct. A positive control whose accuracy was never measured is an assumption.

The judge is OpenAI's Decisions API (gpt-6-luna): a predicate returns a
probability and there is no free-text field, so the defect where the prose
contradicts the boolean cannot occur by construction. It is a different model
family from the answerer (gemini-2.5-flash-lite), which is the point.

Determinism of this judge was measured on 2026-10-26: 540 pairs judged twice in
separate runs produced 0 label changes and a max |delta p| of 0.000.
"""
import collections
import json
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = "/root/medicoes/2026-10-26-memory-tax"
SRC = f"{BASE}/replay-answers.json"
OUT = f"{BASE}/replay-judged.json"
KEY = os.environ["OPENAI_API_KEY"]
MODEL = os.environ.get("JUDGE_MODEL", "gpt-6-luna")
API = "https://api.openai.com/v1/decisions"
WORKERS = int(os.environ.get("JUDGE_WORKERS", "6"))
SMOKE = int(os.environ.get("SMOKE_N", "0"))
THR = float(os.environ.get("THR", "0.5"))

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
    """Extract the judge's answers. The envelope key is "answers".

    An empty extraction must RAISE, never return {}: downstream a missing
    predicate reads as probability 0, i.e. as "the candidate is wrong", so a
    parser bug would print a perfect tax. The first smoke of this script did
    exactly that -- arm A scored 0.0% correct, which is impossible, and that is
    what exposed the wrong key.
    """
    ans = {a["name"]: a for a in d.get("answers", [])}
    if "contem" not in ans or "contradiz" not in ans:
        raise RuntimeError(f"judge envelope without the predicates: keys={list(d)[:6]} "
                           f"answers={list(ans)[:6]}")
    s_ = ans.get("nivel", {})
    return {
        "contem": ans["contem"].get("probability"),
        "contradiz": ans["contradiz"].get("probability"),
        "nivel": s_.get("score"),
        "nivel_conf": s_.get("confidence"),
        "nivel_probs": {x["label"]: x["probability"] for x in s_.get("probabilities", [])},
    }


def main():
    rows = json.load(open(SRC, encoding="utf-8"))
    # the positive control decides who is in the population at all
    pop = [r for r in rows if not r["a_abstained"]
           and "__ERR__" not in (r["arm_a_raw"] or "")
           and "__ERR__" not in (r["arm_b_memory"] or "")]
    print(f"rows {len(rows)} | arm A answered (population) {len(pop)}")
    jobs = [(r, arm) for r in pop for arm in ("a", "b")]
    if SMOKE:
        jobs = jobs[:SMOKE]
    print(f"judgements: {len(jobs)}  model: {MODEL}  workers: {WORKERS}")

    t0, toks = time.time(), 0

    def run(job):
        r, arm = job
        cand = r["arm_a_raw"] if arm == "a" else r["arm_b_memory"]
        try:
            d = decide(r["answer"], cand, r["question"])
            got = pull(d)
            if got["contem"] is None or got["contradiz"] is None:
                raise RuntimeError("predicate without a probability")
            return r, arm, got, (d.get("usage") or {}).get("input_tokens", 0), None
        except Exception as e:
            return r, arm, None, 0, f"{type(e).__name__}: {e}"

    judged = collections.defaultdict(dict)
    errs = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for r, arm, got, tk, err in ex.map(run, jobs):
            toks += tk
            if err:
                errs += 1
                print("  ERR", arm, err[:120])
                continue
            judged[id(r)][arm] = got
            judged[id(r)]["row"] = r

    out = []
    for v in judged.values():
        if "a" not in v or "b" not in v:
            continue
        r = v["row"]
        out.append({k: r.get(k) for k in
                    ("uuid", "stratum", "scope", "category", "question", "answer",
                     "span_chars", "memory_units", "memory_chars",
                     "arm_a_raw", "arm_b_memory", "a_abstained", "b_abstained")}
                   | {"a": v["a"], "b": v["b"]})

    print(f"\nerrors {errs} | judged pairs {len(out)}")

    def rate(rs, arm, pred):
        n = len(rs)
        return (sum(1 for r in rs if (r[arm].get(pred) or 0) > THR), n)

    print(f"\n{'':24s} {'n':>4s} {'certo':>12s} {'errado':>12s} {'calado':>12s}")
    def line(label, rs):
        if not rs:
            return
        n = len(rs)
        for arm in ("a", "b"):
            ok, _ = rate(rs, arm, "contem")
            bad, _ = rate(rs, arm, "contradiz")
            sil = sum(1 for r in rs if r[f"{arm}_abstained"]) if arm == "b" else \
                  sum(1 for r in rs if r["a_abstained"])
            print(f"{label+' ('+arm.upper()+')':24s} {n:4d} {ok:6d} {ok/n:5.1%} "
                  f"{bad:6d} {bad/n:5.1%} {sil:6d} {sil/n:5.1%}")
    line("TODOS", out)
    print()
    for sc in ("local", "distribuido"):
        line(sc, [r for r in out if r.get("scope") == sc])
    print()
    for cat in ("decision", "lesson", "preference", "context"):
        line(cat, [r for r in out if r.get("category") == cat])
    print()
    for lb, lo, hi in (("mem 1-15u", 1, 16), ("mem 16-60u", 16, 61), ("mem 61+u", 61, 1 << 30)):
        line(lb, [r for r in out if lo <= (r.get("memory_units") or 0) < hi])
    print()
    for lb, lo, hi in (("span <2000", 0, 2000), ("span 2000+", 2000, 1 << 30)):
        line(lb, [r for r in out if r.get("span_chars") is not None
                  and lo <= r["span_chars"] < hi])

    a_ok = sum(1 for r in out if (r["a"].get("contem") or 0) > THR)
    b_ok = sum(1 for r in out if (r["b"].get("contem") or 0) > THR)
    n = len(out)
    print(f"\nFAITHFULNESS TAX = A - B = {a_ok/n:.1%} - {b_ok/n:.1%} = "
          f"{(a_ok-b_ok)/n:+.1%} absolute, {1-b_ok/max(a_ok,1):.1%} relative")
    dmg = [r for r in out if (r["b"].get("contradiz") or 0) > THR]
    print(f"DAMAGE (B answers and contradicts): {len(dmg)} = {len(dmg)/n:.1%}")
    for r in dmg[:5]:
        print(f"\n  Q: {r['question'][:150]}")
        print(f"  gold: {r['answer'][:130]}")
        print(f"  B   : {r['arm_b_memory'][:130]}")

    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"\ntokens {toks:,} ~US$ {toks/1e6*0.10:.4f} · {time.time()-t0:.0f}s")
    print("wrote", OUT)


main()
