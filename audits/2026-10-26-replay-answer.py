"""Replay the QA with gold raw turns (arm A) against memory units (arm B).

Arm A is the positive control, not a result: a question the raw evidence cannot
answer is a bad question, and the pair is dropped. Without it a low B is
indistinguishable from a badly generated question -- the failure the null-result
rule in this repository was written for.

Arm B receives ALL of the session's distilled chunks, with no retrieval step at
all. That is deliberately generous: it removes accessibility tax by
construction, so whatever gap remains is construction tax and is a FLOOR, not
an estimate.

Both arms may answer "NAO SEI". Forcing an answer manufactures fabrication,
which this corpus already measured at 17.4% on negatives, all of it cited.

The judge then separates two outcomes that an aggregate hides:
  silence     -- the memory does not contain the fact (loss)
  contradiction -- the memory answers, and answers WRONG (damage)
A builder that cuts the conversation into 2000-char blocks with no overlap
keeps "we chose X" from one block and "we switched to Y" from another, with
nothing recording which won. That produces contradiction, not silence, and it
is the worse failure: it is served with the same confidence as a true memory.
"""
import collections
import json
import os
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = "/root/medicoes/2026-10-26-memory-tax"
QS = f"{BASE}/replay-questions.json"
SET = f"{BASE}/replay-set.json"
OUT = f"{BASE}/replay-answers.json"
GKEY = os.environ["GEMINI_API_KEY"]
GMODEL = "gemini-2.5-flash-lite"
SMOKE = int(os.environ.get("SMOKE_N", "0"))
WORKERS = int(os.environ.get("WORKERS", "6"))

ANSWER_SYSTEM = """Você responde perguntas usando APENAS o material fornecido.

Regras:
- Se o material contém a resposta, responda em no máximo 25 palavras.
- Se o material NÃO contém a resposta, responda exatamente: NAO SEI
- Nunca use conhecimento próprio. Nunca especule. Nunca complete lacuna.
- Se o material trouxer duas informações conflitantes, responda com a que o
  material indicar como final e diga que houve mudança. Se não houver como
  saber qual é a final, responda as duas e diga que o material não resolve."""

GURL = (f"https://generativelanguage.googleapis.com/v1beta/models/{GMODEL}"
        f":generateContent?key={GKEY}")


def gemini(material, question):
    body = {
        "systemInstruction": {"parts": [{"text": ANSWER_SYSTEM}]},
        "contents": [{"parts": [{"text": f"MATERIAL:\n{material}\n\nPERGUNTA: {question}"}]}],
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": 200},
    }
    req = urllib.request.Request(
        GURL, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.loads(r.read())
    cand = (d.get("candidates") or [{}])[0]
    txt = "".join(p.get("text", "") for p in (cand.get("content") or {}).get("parts", []))
    u = d.get("usageMetadata") or {}
    return txt.strip(), u.get("promptTokenCount", 0), u.get("candidatesTokenCount", 0)


# the abstention detector, copied VERBATIM from eval/run-abstention.mjs so the
# two measurements share one predicate rather than two lookalikes
CANON = "i have no memory matches for this question"
def abstained(t):
    s = (t or "").lower()
    return (CANON in s or "nao sei" in s or "não sei" in s or "não tenho" in s
            or "nao tenho" in s or "não há informação" in s or "nao ha informacao" in s)


def main():
    qs = json.load(open(QS, encoding="utf-8"))
    data = json.load(open(SET, encoding="utf-8"))
    units = {s["uuid"]: s["units"] for s in data["sessions"]}

    qs = [q for q in qs if q.get("evidence_window") and q.get("question")]
    if SMOKE:
        qs = qs[:SMOKE]
    print(f"questions: {len(qs)}  workers: {WORKERS}")

    t0, tin, tout = time.time(), 0, 0

    def run(q):
        rec = dict(q)
        mem = "\n\n".join(f"[{c.get('type') or 'memory'}] {c['text']}"
                          for c in units.get(q["uuid"], []))
        try:
            a, i1, o1 = gemini(q["evidence_window"], q["question"])
        except Exception as e:
            a, i1, o1 = f"__ERR__ {type(e).__name__}", 0, 0
        try:
            b, i2, o2 = gemini(mem or "(vazio)", q["question"])
        except Exception as e:
            b, i2, o2 = f"__ERR__ {type(e).__name__}", 0, 0
        rec.update({"arm_a_raw": a, "arm_b_memory": b,
                    "a_abstained": abstained(a), "b_abstained": abstained(b),
                    "memory_chars": len(mem), "memory_units": len(units.get(q["uuid"], [])),
                    "tokens": i1 + i2 + o1 + o2})
        rec.pop("evidence_window", None) if SMOKE else None
        return rec, i1 + i2, o1 + o2

    out = []
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for rec, i, o in ex.map(run, qs):
            tin += i
            tout += o
            out.append(rec)

    errs = sum(1 for r in out if "__ERR__" in (r["arm_a_raw"] or "")
               or "__ERR__" in (r["arm_b_memory"] or ""))
    good = [r for r in out if "__ERR__" not in (r["arm_a_raw"] or "")
            and "__ERR__" not in (r["arm_b_memory"] or "")]
    a_ok = [r for r in good if not r["a_abstained"]]
    print(f"\nerrors: {errs}")
    print(f"ARM A (positive control): answered {len(a_ok)}/{len(good)} = "
          f"{len(a_ok)/max(len(good),1):.1%}  <- pairs where A abstains are DROPPED")
    if a_ok:
        b_sil = sum(1 for r in a_ok if r["b_abstained"])
        print(f"ARM B on those {len(a_ok)}: silent {b_sil} = {b_sil/len(a_ok):.1%}, "
              f"answered {len(a_ok)-b_sil}")
        for sc in ("local", "distribuido"):
            sub = [r for r in a_ok if r.get("scope") == sc]
            if sub:
                s2 = sum(1 for r in sub if r["b_abstained"])
                print(f"  {sc:12s} n={len(sub):3d}  B silent {s2:3d} = {s2/len(sub):.1%}")
        # stratified by how much memory the session produced: if B fails the same
        # in a session with 4 units and one with 242, the loss is by design; if it
        # fails less where there are more units, the loss tracks compression.
        print("  by memory the session produced:")
        for lb, lo, hi in (("1-5 units", 1, 6), ("6-15", 6, 16), ("16-60", 16, 61), ("61+", 61, 1 << 30)):
            sub = [r for r in a_ok if lo <= r["memory_units"] < hi]
            if sub:
                s2 = sum(1 for r in sub if r["b_abstained"])
                print(f"    {lb:10s} n={len(sub):3d}  B silent {s2:3d} = {s2/len(sub):5.1%}"
                      f"  (median {sorted(r['memory_chars'] for r in sub)[len(sub)//2]:,} chars of memory)")
        print("  by evidence span (the builder's block is 2000 chars):")
        for lb, lo, hi in (("< 2000", 0, 2000), ("2000-4000", 2000, 4000), ("> 4000", 4000, 1 << 30)):
            sub = [r for r in a_ok if r.get("span_chars") is not None and lo <= r["span_chars"] < hi]
            if sub:
                s2 = sum(1 for r in sub if r["b_abstained"])
                print(f"    {lb:10s} n={len(sub):3d}  B silent {s2:3d} = {s2/len(sub):5.1%}")
    print(f"\ntokens in {tin:,} out {tout:,} ~US$ {tin/1e6*0.10+tout/1e6*0.40:.4f}"
          f" · {time.time()-t0:.0f}s")
    if not SMOKE:
        json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
        print("wrote", OUT)
    else:
        for r in good[:4]:
            print(f"\n[{r.get('scope')}|{r.get('category')}] {r['question']}")
            print(f"  gold: {r['answer']}")
            print(f"  A   : {r['arm_a_raw'][:160]}")
            print(f"  B   : {r['arm_b_memory'][:160]}")


main()
