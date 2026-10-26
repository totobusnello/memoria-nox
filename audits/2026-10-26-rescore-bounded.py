#!/usr/bin/env python3
"""What the bounded judge's labels do to nDCG@10.

The published claim is an INTERVAL: nDCG@10 in [0.2428, 0.5114], the lower bound
from pre-registered gold only and the upper from pooling judged by
`gemini-2.5-flash-lite`. This recomputes the same rankings under the bounded
judge's labels (OpenAI Decisions, `gpt-6-luna`), which is the same arithmetic on
a different label set.

CONTROL FIRST. The script recomputes the two PUBLISHED numbers from the
published labels before reporting anything new. A recomputation that cannot
reproduce 0.2428 and 0.5114 is a broken instrument, and its new figure would be
a fact about the bug. Both are asserted, not printed and eyeballed.

Threshold. A predicate returns a probability, so the binary cut is a choice, not
a measurement. Three cuts are reported (0.3 / 0.5 / 0.7) so the reader sees how
much the number owes to that choice.

The graded arm is NOT comparable to the binary arms — different gain, different
ideal ranking. It is reported for the shape of the ordering, not to be put
beside 0.2428.
"""
import json, math, os, sys

EVAL   = sys.argv[1]   # eval-result.json  (os rankings de 22/10)
GOLDID = sys.argv[2]   # gold-ids-eval.json
OLD    = sys.argv[3]   # pooling.json       (labels do juiz de prosa)
NEW    = sys.argv[4]   # full.json          (juiz delimitado, pares do pooling)
NEWG   = sys.argv[5]   # gold-judged.json   (juiz delimitado, pares gold do top-10)
K      = 10

ev     = json.load(open(EVAL, encoding="utf-8"))
goldid = {int(k): set(v) for k, v in json.load(open(GOLDID, encoding="utf-8")).items()}
old    = {(r["query_id"], r["chunk_id"]): r for r in json.load(open(OLD, encoding="utf-8"))}
new    = {(r["query_id"], r["chunk_id"]): r for r in json.load(open(NEW, encoding="utf-8"))}
new.update({(r["query_id"], r["chunk_id"]): r for r in json.load(open(NEWG, encoding="utf-8"))})

rows = [r for r in ev["rows"] if r.get("ndcg") is not None]

def dcg(gains):
    return sum(g / math.log2(i + 2) for i, g in enumerate(gains))

def score(relfn, idealfn=None):
    """relfn(qid, cid) -> ganho. idealfn(qid, ranked) -> lista de ganhos ideais."""
    acc = {"ndcg": [], "recall": [], "mrr": [], "zero": 0, "judged_rel": 0}
    for r in rows:
        qid = r["query_id"]
        gains = [relfn(qid, c) for c in r["ranked"][:K]]
        ideal = (idealfn(qid, r["ranked"]) if idealfn
                 else [1.0] * min(sum(1 for g in gains if g > 0) or 0, K))
        acc["judged_rel"] += sum(1 for g in gains if g > 0)
        n = dcg(gains) / dcg(ideal) if ideal and dcg(ideal) > 0 else 0.0
        acc["ndcg"].append(n)
        hit = [i for i, g in enumerate(gains) if g > 0]
        acc["mrr"].append(1 / (hit[0] + 1) if hit else 0.0)
        if not hit:
            acc["zero"] += 1
    m = lambda a: round(sum(a) / len(a), 4)
    return {"n_queries": len(rows), "ndcg_at_10": m(acc["ndcg"]), "mrr": m(acc["mrr"]),
            "zero_hit": acc["zero"], "relevantes_no_top10": acc["judged_rel"]}

# --- CONTROLE: reproduzir os dois numeros publicados ---------------------
def rel_strict(qid, cid):
    return 1.0 if cid in goldid.get(qid, set()) else 0.0

def ideal_strict(qid, ranked):
    return [1.0] * min(len(goldid.get(qid, set())), K)

def rel_pooled_old(qid, cid):
    if cid in goldid.get(qid, set()):
        return 1.0
    return 1.0 if old.get((qid, cid), {}).get("relevante") else 0.0

def ideal_pooled_old(qid, ranked):
    n = len(goldid.get(qid, set())) + sum(
        1 for c in ranked if c not in goldid.get(qid, set())
        and old.get((qid, c), {}).get("relevante"))
    return [1.0] * min(n, K)

ctl_strict = score(rel_strict, ideal_strict)
ctl_pooled = score(rel_pooled_old, ideal_pooled_old)
print("=== CONTROLE: reproduzir o publicado ===")
print(f" strict  recomputado {ctl_strict['ndcg_at_10']}  publicado 0.2428  "
      f"zero_hit {ctl_strict['zero_hit']} (publicado 29)")
print(f" pooled  recomputado {ctl_pooled['ndcg_at_10']}  publicado 0.5114  "
      f"zero_hit {ctl_pooled['zero_hit']} (publicado 5)")
falhas = []
if abs(ctl_strict["ndcg_at_10"] - 0.2428) > 0.0005:
    falhas.append(f"strict {ctl_strict['ndcg_at_10']} != 0.2428")
if abs(ctl_pooled["ndcg_at_10"] - 0.5114) > 0.0005:
    falhas.append(f"pooled {ctl_pooled['ndcg_at_10']} != 0.5114")
if falhas:
    print("\n*** CONTROLE FALHOU — o recomputador nao reproduz o publicado:")
    for f in falhas:
        print("   ", f)
    print("Nenhum numero novo e interpretavel enquanto isto nao fecha.")
    sys.exit(1)
print(" controle OK: a aritmetica e a mesma, so os rotulos mudam.\n")

# --- juiz delimitado, binario por limiar ---------------------------------
out = {"control": {"strict": ctl_strict, "pooled_prose_judge": ctl_pooled},
       "bounded_binary": {}, "bounded_graded": None, "label_flips": {}}

for thr in (0.3, 0.5, 0.7):
    def relf(qid, cid, thr=thr):
        p = new.get((qid, cid), {}).get("prob_contem_resposta")
        return 1.0 if (p is not None and p > thr) else 0.0
    def idealf(qid, ranked, thr=thr):
        n = sum(1 for c in ranked if relf(qid, c, thr) > 0)
        return [1.0] * min(n, K)
    out["bounded_binary"][str(thr)] = score(relf, idealf)
    s = out["bounded_binary"][str(thr)]
    print(f" bounded p>{thr}:  nDCG={s['ndcg_at_10']}  mrr={s['mrr']}  "
          f"zero_hit={s['zero_hit']}  relevantes={s['relevantes_no_top10']}")

# --- juiz delimitado, graduado (NAO comparavel ao binario) ---------------
def relg(qid, cid):
    v = new.get((qid, cid), {}).get("nivel_score")
    return float(v) if v is not None else 0.0

def idealg(qid, ranked):
    return sorted((relg(qid, c) for c in ranked), reverse=True)[:K]

out["bounded_graded"] = score(relg, idealg)
print(f"\n graduado (ganho 0..3, NAO comparavel): nDCG={out['bounded_graded']['ndcg_at_10']}")

# --- onde os dois juizes discordam --------------------------------------
pares = [(qid, cid) for (qid, cid) in old if (qid, cid) in new
         and new[(qid, cid)].get("prob_contem_resposta") is not None]
def cell(cond):
    return sum(1 for k in pares if cond(old[k], new[k]))
P = lambda n: new[n]
flips = {
 "n_pares_comparaveis": len(pares),
 "old_relevante_&_new_sim":  cell(lambda o, n: o.get("relevante") and n["prob_contem_resposta"] > 0.5),
 "old_relevante_&_new_nao":  cell(lambda o, n: o.get("relevante") and n["prob_contem_resposta"] <= 0.5),
 "old_nao_rel_&_new_sim":    cell(lambda o, n: not o.get("relevante") and n["prob_contem_resposta"] > 0.5),
 "old_nao_rel_&_new_nao":    cell(lambda o, n: not o.get("relevante") and n["prob_contem_resposta"] <= 0.5),
 # juiz contra juiz, sem o check de citacao no caminho
 "old_responde_&_new_sim":   cell(lambda o, n: o.get("trecho_responde") and n["prob_contem_resposta"] > 0.5),
 "old_responde_&_new_nao":   cell(lambda o, n: o.get("trecho_responde") and n["prob_contem_resposta"] <= 0.5),
 "old_nao_resp_&_new_sim":   cell(lambda o, n: not o.get("trecho_responde") and n["prob_contem_resposta"] > 0.5),
 "old_nao_resp_&_new_nao":   cell(lambda o, n: not o.get("trecho_responde") and n["prob_contem_resposta"] <= 0.5),
}
def kappa(a, b, c, d):
    n = a + b + c + d
    po = (a + d) / n
    pe = ((a + b) * (a + c) + (c + d) * (b + d)) / (n * n)
    return round((po - pe) / (1 - pe), 4) if pe < 1 else None
flips["kappa_vs_relevante_publicado"] = kappa(
    flips["old_relevante_&_new_sim"], flips["old_relevante_&_new_nao"],
    flips["old_nao_rel_&_new_sim"], flips["old_nao_rel_&_new_nao"])
flips["kappa_vs_trecho_responde"] = kappa(
    flips["old_responde_&_new_sim"], flips["old_responde_&_new_nao"],
    flips["old_nao_resp_&_new_sim"], flips["old_nao_resp_&_new_nao"])
out["label_flips"] = flips
print("\n=== concordancia entre juizes, nos 100% dos pares ===")
print(json.dumps(flips, indent=1))

json.dump(out, open(os.environ.get("RESCORE_OUT", "rescore.json"), "w"),
          ensure_ascii=False, indent=1)
