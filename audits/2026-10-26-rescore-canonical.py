#!/usr/bin/env python3
"""nDCG under a denominator that was also judged — and what that does to today's number.

The bounded-judge run reported earlier today compared three arms whose IDEALS
were not built the same way, which makes the comparison unfair in a direction
that favours the new arm:

    strict      ideal = |gold|                       truncated to K
    pooled      ideal = |gold| + pooled relevants in the ranking
    bounded     ideal = |relevants inside the ranking|

The third one cannot see a relevant document the system failed to retrieve. A
query with one relevant item, returned at rank 1, scores 1.0 even if the corpus
holds five. So the bounded arm measures ORDERING, while the two published arms
measure ordering plus part of the recall. The 0.5114 -> 0.4764 drop was
therefore an UNDERSTATEMENT of the gap.

Now that `eval/judge-relevance.py` has labelled 609 of the 615 pairs in
(top-10 union gold), the relevant set for each query is known from both sides
and the ideal can be built the same way for every arm: the relevants the judge
confirms anywhere — in the gold, in the ranking, or in both — truncated to K.

Two controls run before any new number is printed, and the script exits 1 if
either fails:
  1. the published pair, 0.2428 / 0.5114, from the OLD labels;
  2. today's own bounded number, 0.4764, from the old ideal — because a
     recomputation that cannot reproduce what it is correcting is not a
     correction.

And one free measurement that needs no extra call: 548 pairs were judged twice
today by the same bounded judge, in two separate runs. The agreement between
those runs is the judge's own reproducibility, which no amount of cross-family
comparison establishes.
"""
import json, math, os, sys

K = 10
GOLD_SCORE = sys.argv[1]      # eval-result.json (run-gold-eval.mjs)
OLD_POOL   = sys.argv[2]      # pooling.json (juiz de prosa, 22/10)
RUN_A      = sys.argv[3]      # full.json,gold-judged.json (1a corrida de hoje, em partes)
RUN_B      = sys.argv[4]      # canonical-full.json (eval/judge-relevance.py)
OUT        = sys.argv[5]
THR        = float(os.environ.get("JUDGE_THRESHOLD", "0.5"))

sc   = json.load(open(GOLD_SCORE, encoding="utf-8"))
rows = [r for r in sc["rows"] if not r.get("skipped") and not r.get("error")]
goldid = {r["query_id"]: set(r.get("gold_ids", [])) for r in rows}

old = {(r["query_id"], r["chunk_id"]): r for r in json.load(open(OLD_POOL, encoding="utf-8"))}
# A 1a corrida gravou o top-10 e os pares gold em arquivos SEPARADOS. Carregar
# so um deixa 30 pares sem rotulo, que contam zero e derrubam o nDCG para
# 0,3579 — foi o que o controle 2 pegou na primeira execucao deste script.
A = {}
for parte in RUN_A.split(","):
    for r in json.load(open(parte.strip(), encoding="utf-8")):
        A[(r["query_id"], r["chunk_id"])] = r
B   = {(r["query_id"], r["chunk_id"]): r for r in json.load(open(RUN_B, encoding="utf-8"))["rows"]}

dcg = lambda g: sum(x / math.log2(i + 2) for i, x in enumerate(g))

def score(relfn, idealfn):
    acc, mrr, n, zero, rel_top = 0.0, 0.0, 0, 0, 0
    for r in rows:
        qid, ranked = r["query_id"], r["ranked"]
        gains = [relfn(qid, c) for c in ranked]
        ideal = idealfn(qid, ranked)
        v = dcg(gains) / dcg(ideal) if ideal and dcg(ideal) > 0 else 0.0
        acc += v; n += 1
        # O MRR nao depende do ideal: e 1/rank do primeiro relevante. Entra aqui
        # para a tabela do audit nao misturar duas corridas.
        pos = next((i for i, g in enumerate(gains) if g > 0), None)
        mrr += 0.0 if pos is None else 1.0 / (pos + 1)
        if pos is None:
            zero += 1
        rel_top += sum(1 for g in gains if g > 0)
    return {"ndcg_at_10": round(acc / n, 4), "mrr": round(mrr / n, 4), "n": n,
            "zero_hit": zero, "relevantes_no_top10": rel_top}

# ----------------------------------------------------------- controle 1
rel_strict  = lambda q, c: 1.0 if c in goldid.get(q, set()) else 0.0
ideal_strict= lambda q, rk: [1.0] * min(len(goldid.get(q, set())), K)
def rel_pool_old(q, c):
    if c in goldid.get(q, set()):
        return 1.0
    return 1.0 if old.get((q, c), {}).get("relevante") else 0.0
def ideal_pool_old(q, rk):
    n = len(goldid.get(q, set())) + sum(
        1 for c in rk if c not in goldid.get(q, set()) and old.get((q, c), {}).get("relevante"))
    return [1.0] * min(n, K)

c1 = score(rel_strict, ideal_strict)
c2 = score(rel_pool_old, ideal_pool_old)

# ----------------------------------------------------------- controle 2
pA = lambda q, c: A.get((q, c), {}).get("prob_contem_resposta")
relA = lambda q, c: 1.0 if (pA(q, c) is not None and pA(q, c) > THR) else 0.0
idealA_antigo = lambda q, rk: [1.0] * min(sum(1 for c in rk if relA(q, c) > 0), K)
c3 = score(relA, idealA_antigo)

falhas = []
for got, want, nome in ((c1["ndcg_at_10"], 0.2428, "strict"),
                        (c2["ndcg_at_10"], 0.5114, "pooled (juiz de prosa)"),
                        (c3["ndcg_at_10"], 0.4764, "delimitado p>0,5 (ideal antigo)")):
    print(f"controle · {nome:34s} recomputado {got}  publicado {want}")
    if abs(got - want) > 0.0005:
        falhas.append(f"{nome}: {got} != {want}")
if falhas:
    print("\n*** CONTROLE FALHOU:")
    for f in falhas:
        print("   ", f)
    print("Nenhum numero novo e interpretavel enquanto isto nao fecha.")
    sys.exit(1)
print("  controle OK nos tres.\n")

# ----------------------------------------------------------- o denominador certo
pB = lambda q, c: B.get((q, c), {}).get("prob_contem_resposta")
relB = lambda q, c: 1.0 if (pB(q, c) is not None and pB(q, c) > THR) else 0.0

# relevantes conhecidos para a query, de qualquer fonte julgada
conhecidos = {}
for (q, c), r in B.items():
    p = r.get("prob_contem_resposta")
    if p is not None and p > THR:
        conhecidos.setdefault(q, set()).add(c)
ideal_justo = lambda q, rk: [1.0] * min(len(conhecidos.get(q, set())), K)

# A mesma regra aplicada aos rotulos ANTIGOS, senao a comparacao troca a
# aritmetica junto com os rotulos e nao se sabe qual dos dois moveu o numero.
# Para os rotulos antigos o gold entra por DECRETO (era a premissa do braco
# strict) e o pooling so julgou o ranked, logo o conjunto conhecido e
# gold union {ranked julgado relevante}.
conhecidos_old = {}
for r in rows:
    q = r["query_id"]
    s_ = set(goldid.get(q, set()))
    for c in r["ranked"]:
        if old.get((q, c), {}).get("relevante"):
            s_.add(c)
    conhecidos_old[q] = s_
ideal_justo_old = lambda q, rk: [1.0] * min(len(conhecidos_old.get(q, set())), K)
pooled_justo = score(rel_pool_old, ideal_justo_old)

novo = score(relB, ideal_justo)
# e o mesmo com o ideal antigo, para isolar o efeito do denominador
mesmo_rotulo_ideal_antigo = score(relB, lambda q, rk: [1.0] * min(
    sum(1 for c in rk if relB(q, c) > 0), K))

print("=== o efeito do DENOMINADOR, com os mesmos rotulos ===")
print(f" ideal = relevantes dentro do top-10 (o que reportei hoje): "
      f"{mesmo_rotulo_ideal_antigo['ndcg_at_10']}")
print(f" ideal = relevantes conhecidos em (top-10 uniao gold):      "
      f"{novo['ndcg_at_10']}  <- o comparavel")
print(f" delta: {novo['ndcg_at_10'] - mesmo_rotulo_ideal_antigo['ndcg_at_10']:+.4f}")
print(f" zero-hit {novo['zero_hit']} · relevantes no top-10 {novo['relevantes_no_top10']}")

print("\n=== os dois conjuntos de rotulos sob a MESMA regra de ideal ===")
print(f" juiz de prosa (22/10):  {pooled_justo['ndcg_at_10']}  "
      f"zero_hit {pooled_justo['zero_hit']}  (publicado 0.5114 sob a regra antiga)")
print(f" juiz delimitado:        {novo['ndcg_at_10']}  zero_hit {novo['zero_hit']}")
print(f" o que a troca de JUIZ custa, isolada: "
      f"{novo['ndcg_at_10'] - pooled_justo['ndcg_at_10']:+.4f} "
      f"({(novo['ndcg_at_10']/pooled_justo['ndcg_at_10']-1)*100:+.1f}%)")

# ----------------------------------------------------------- o gold, inteiro
gold_pares = [(q, c) for q in goldid for c in goldid[q]]
jg = [(q, c) for q, c in gold_pares if pB(q, c) is not None]
gold_ok = [(q, c) for q, c in jg if pB(q, c) > THR]
no_top = {(q, c) for q, c in gold_pares if c in set(next(
    (r["ranked"] for r in rows if r["query_id"] == q), []))}
print("\n=== os tres limiares sob o denominador justo ===")
limiares = {}
for thr in (0.3, 0.5, 0.7):
    relt = lambda q, c, t=thr: 1.0 if (pB(q, c) is not None and pB(q, c) > t) else 0.0
    conh = {}
    for (q, c), r in B.items():
        pv = r.get("prob_contem_resposta")
        if pv is not None and pv > thr:
            conh.setdefault(q, set()).add(c)
    st = score(relt, lambda q, rk, cc=conh: [1.0] * min(len(cc.get(q, set())), K))
    limiares[str(thr)] = st
    print(f" p>{thr}:  nDCG={st['ndcg_at_10']}  mrr={st['mrr']}  zero_hit={st['zero_hit']}  "
          f"relevantes={st['relevantes_no_top10']}")

print(f"\n=== o GOLD pre-registrado sob o juiz delimitado ===")
print(f" gold ids: {len(gold_pares)} · julgados {len(jg)} · confirmados {len(gold_ok)} "
      f"({len(gold_ok)/max(1,len(jg))*100:.1f}%)")
for sub, nome in ((no_top, "aparece no top-10"), (set(gold_pares) - no_top, "fora do top-10")):
    s = [(q, c) for q, c in sub if pB(q, c) is not None]
    o = [(q, c) for q, c in s if pB(q, c) > THR]
    if s:
        print(f"   {nome:20s} {len(o)}/{len(s)} = {len(o)/len(s)*100:.1f}% confirmados")

# ----------------------------------------------------------- reprodutibilidade
comum = [(q, c) for (q, c) in A if (q, c) in B
         and A[(q, c)].get("prob_contem_resposta") is not None
         and B[(q, c)].get("prob_contem_resposta") is not None]
flips = [(q, c) for q, c in comum
         if (A[(q, c)]["prob_contem_resposta"] > THR) != (B[(q, c)]["prob_contem_resposta"] > THR)]
dif = [abs(A[(q, c)]["prob_contem_resposta"] - B[(q, c)]["prob_contem_resposta"]) for q, c in comum]
print(f"\n=== o MESMO juiz, duas corridas (n={len(comum)}) ===")
print(f" rotulo binario muda em {len(flips)} pares = {len(flips)/max(1,len(comum))*100:.2f}%")
print(f" |delta p| medio {sum(dif)/len(dif):.4f} · maximo {max(dif):.3f} · "
      f">0,2 em {sum(1 for x in dif if x > 0.2)}")

json.dump({"controle": {"strict": c1, "pooled_prose": c2, "bounded_ideal_antigo": c3},
           "bounded_ideal_justo": novo,
           "bounded_mesmos_rotulos_ideal_antigo": mesmo_rotulo_ideal_antigo,
           "pooled_prose_ideal_justo": pooled_justo,
           "gold": {"n": len(gold_pares), "julgados": len(jg), "confirmados": len(gold_ok)},
           "reprodutibilidade": {"n": len(comum), "flips": len(flips),
                                 "delta_p_medio": round(sum(dif)/len(dif), 4),
                                 "delta_p_max": round(max(dif), 3)},
           "limiares_ideal_justo": limiares, "threshold": THR}, open(OUT, "w"), ensure_ascii=False, indent=1)
